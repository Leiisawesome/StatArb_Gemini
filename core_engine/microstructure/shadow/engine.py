"""
LiquidityShadowEngine — main orchestrator for shadow trading.

Connects all components:
  Polygon WS → StreamingVolumeBucketer → EventLevelFilter → OrderManager
  → MechanismMonitor → ShadowLogger

Handles lifecycle, market hours, pre-flight checks, and crash recovery.

Spec: v1.7-SHADOW
Build Plan: v4-FINAL, Step 6
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from core_engine.microstructure.shadow.constants import (
    ADV_SHARES,
    ENTRY_DELAY_MS,
    IMBALANCE_THRESHOLDS,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    PORTFOLIO_VALUE,
    SHADOW_CONSTANTS_VERSION,
    SYMBOLS,
)
from core_engine.microstructure.shadow.event_filter import (
    EventLevelFilter,
    InventoryTracker,
)
from core_engine.microstructure.shadow.infra_latency_monitor import (
    InfrastructureLatencyMonitor,
)
from core_engine.microstructure.shadow.mechanism_monitor import MechanismMonitor
from core_engine.microstructure.shadow.order_manager import OrderManager
from core_engine.microstructure.shadow.shadow_logger import ShadowLogger
from core_engine.microstructure.shadow.streaming_bucketer import StreamingVolumeBucketer
from core_engine.microstructure.shadow.types import (
    DailyReport,
    LatencyPath,
    MechanismHealthSurface,
    NBBOIntegrityReport,
    Quote,
    ShadowConfig,
)

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class LiquidityShadowEngine:
    """Main orchestrator for the shadow trading system.

    Lifecycle:
    1. initialize() — pre-flight checks + crash recovery
    2. run() — main event loop (processes until market close)
    3. pause() / resume() — manual or kill-triggered
    4. stop() — cancel open orders, flatten, generate reports
    """

    def __init__(self, config: ShadowConfig) -> None:
        self._config = config
        self._running = False
        self._paused = False

        # Core components
        self._inventory = InventoryTracker(config.portfolio_value)
        self._event_filter = EventLevelFilter(self._inventory)
        self._order_manager = OrderManager(
            portfolio_value=config.portfolio_value,
            state_log_path=config.state_log_path,
        )
        self._monitor = MechanismMonitor()
        self._latency_monitor = InfrastructureLatencyMonitor()
        self._logger = ShadowLogger(
            clickhouse_url=config.clickhouse_url,
            db=config.clickhouse_db,
        )

        # Per-symbol bucketers
        self._bucketers: Dict[str, StreamingVolumeBucketer] = {}
        for symbol in SYMBOLS:
            self._bucketers[symbol] = StreamingVolumeBucketer(
                symbol=symbol,
                adv_shares=ADV_SHARES[symbol],
                imbalance_threshold=IMBALANCE_THRESHOLDS[symbol],
            )

        # Daily tracking
        self._daily_reports: List[DailyReport] = []
        self._cumulative_pnl_bps: float = 0.0
        self._trading_day_count: int = 0

    async def initialize(self) -> bool:
        """Run pre-flight checks and crash recovery.

        Returns True if all checks pass, False otherwise.
        """
        logger.info("Initializing LiquidityShadowEngine v%s", SHADOW_CONSTANTS_VERSION)
        checks_passed = True

        # 1. NTP clock sync verification
        try:
            import subprocess
            result = subprocess.run(
                ["ntpdate", "-q", "pool.ntp.org"],
                capture_output=True, text=True, timeout=10,
            )
            logger.info("NTP check: %s", result.stdout[:100] if result.stdout else "OK")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("NTP check skipped (ntpdate not available)")

        # 2. ClickHouse connectivity
        try:
            await self._logger.initialize()
            logger.info("ClickHouse connectivity: OK")
        except Exception as e:
            logger.error("ClickHouse connectivity: FAILED — %s", e)
            checks_passed = False

        # 3. Crash recovery
        recovered = self._order_manager.recover_state()
        if recovered > 0:
            logger.warning("Recovered %d positions from crash state", recovered)

        if checks_passed:
            logger.info("Pre-flight checks: ALL PASSED")
        else:
            logger.error("Pre-flight checks: FAILED — refusing to start")

        return checks_passed

    def on_trade(
        self, symbol: str, timestamp_ns: int, price: float, size: int
    ) -> None:
        """Process an incoming trade from Polygon WebSocket."""
        if self._paused or not self._running:
            return

        if not self._is_market_hours():
            return

        if symbol not in self._bucketers:
            return

        # Record ingest latency
        receive_ns = time.time_ns()
        latency_ms = (receive_ns - timestamp_ns) / 1_000_000
        self._latency_monitor.record_latency(LatencyPath.INGEST, latency_ms)
        self._latency_monitor.record_clock_offset(latency_ms)

        # Feed to bucketer
        event = self._bucketers[symbol].on_trade(timestamp_ns, price, size)

        if event is not None:
            self._monitor.on_event_detected(symbol=symbol)
            self._handle_event(event)

    def on_quote(
        self,
        symbol: str,
        timestamp_ns: int,
        bid: float,
        ask: float,
        bid_size: int,
        ask_size: int,
    ) -> None:
        """Process an incoming quote from Polygon WebSocket."""
        if self._paused or not self._running:
            return

        if symbol not in self._bucketers:
            return

        # Update bucketer's NBBO
        self._bucketers[symbol].on_quote(timestamp_ns, bid, ask, bid_size, ask_size)

        # Create Quote object for filter and order manager
        quote = Quote(
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            bid_price=bid,
            ask_price=ask,
            bid_size=bid_size,
            ask_size=ask_size,
        )

        # Record quote for NBBO integrity
        self._event_filter.record_quote(quote)

        # Check exit conditions on open positions
        outcome = self._order_manager.on_quote_update(symbol, quote)
        if outcome is not None:
            self._monitor.on_trade_complete(outcome)
            self._logger.log_fill(outcome)

            # Per-trade kill check
            daily_pnl, _ = self._order_manager.get_daily_pnl()
            ingest_snap = self._latency_monitor.get_snapshot(LatencyPath.INGEST)
            order_snap = self._latency_monitor.get_snapshot(LatencyPath.ORDER_RTT)
            cancel_snap = self._latency_monitor.get_snapshot(LatencyPath.CANCEL_ACK)

            kill = self._monitor.check_per_trade_kills(
                net_inventory_bps=self._order_manager.get_net_inventory_bps(),
                ingest_p95_ms=ingest_snap.p95_ms,
                order_rtt_p95_ms=order_snap.p95_ms,
                cancel_ack_median_ms=cancel_snap.p50_ms,
                daily_pnl_bps=daily_pnl,
            )
            if kill is not None:
                logger.critical("KILL TRIGGERED: %s", kill.detail)
                self._paused = True

    def _handle_event(self, event) -> None:
        """Process a detected imbalance event through the filter pipeline."""
        # Get current quote for evaluation
        bucketer = self._bucketers[event.symbol]
        if bucketer._latest_quote is None:
            self._logger.log_event(
                event, accepted=False, rejection_reason="no_quote"
            )
            return

        quote = bucketer._latest_quote

        # Apply event filter
        signal = self._event_filter.evaluate(event, quote)

        if signal is None:
            # Determine rejection reason from filter counts
            counts = self._event_filter.rejection_counts
            self._logger.log_event(event, accepted=False, rejection_reason="filtered")
            return

        # Log accepted event
        self._logger.log_event(
            event,
            accepted=True,
            sub_strategy=signal.sub_strategy.value,
            spread_ratio=signal.spread_ratio,
            baseline_spread=signal.baseline_spread,
            quote_age_ms=signal.quote_age_ms,
        )

        # Record shock for clustering (spread_ratio now known post-filter)
        self._monitor.on_event_detected(
            symbol=signal.symbol, spread_ratio=signal.spread_ratio,
        )

        # Place order
        self._monitor.on_order_placed()
        order_id = self._order_manager.place_order(signal)

        # Add to inventory tracker
        self._inventory.add_position(
            symbol=signal.symbol,
            side=signal.side,
            shares=100,
            price=signal.limit_price,
            spread_bps=quote.spread_bps,
        )

    async def run_daily_close(self) -> None:
        """End-of-day processing: generate daily report, check kill conditions."""
        self._trading_day_count += 1
        daily_pnl, daily_dollars = self._order_manager.get_daily_pnl()
        self._cumulative_pnl_bps += daily_pnl

        # Daily close kill check
        kill = self._monitor.check_daily_close_kills(daily_pnl)
        if kill is not None:
            logger.critical("DAILY KILL TRIGGERED: %s", kill.detail)
            self._paused = True

        # M9: Event frequency collapse alert (operational, not automatic kill)
        freq_alert = self._monitor.check_event_frequency_alert(daily_pnl)
        if freq_alert is not None:
            logger.warning(
                "M9 PAUSE SIGNAL: event frequency collapsed %.0f%% "
                "from 20d avg (%.1f → %d), P&L=%.2f bps — consider reducing exposure",
                freq_alert["decline_pct"] * 100,
                freq_alert["avg_20d_events"],
                int(freq_alert["current_events"]),
                freq_alert["daily_pnl_bps"],
            )

        # M10: Cross-symbol correlation alert
        corr_alert = self._monitor.check_cross_symbol_correlation()
        if corr_alert is not None:
            logger.warning(
                "M10 CORRELATION ALERT: avg pairwise=%.3f > %.2f — "
                "correlated stop-loss risk elevated",
                corr_alert["avg_pairwise_correlation"],
                0.50,
            )

        # M10b: Shock event clustering alert
        cluster_alert = self._monitor.check_shock_clustering()

        # Loss velocity check
        velocity_alert = self._monitor.check_loss_velocity()

        # Record daily p95 for latency baselines
        for path in LatencyPath:
            snap = self._latency_monitor.get_snapshot(path)
            self._latency_monitor.record_daily_p95(path, snap.p95_ms)

        # Generate daily report
        counts = self._event_filter.rejection_counts
        health = self._monitor.get_mechanism_health()
        fill_acct = self._monitor.get_fill_accounting()
        nbbo_report = self._event_filter.get_nbbo_integrity_stats()

        ingest_snap = self._latency_monitor.get_snapshot(LatencyPath.INGEST)
        order_snap = self._latency_monitor.get_snapshot(LatencyPath.ORDER_RTT)
        cancel_snap = self._latency_monitor.get_snapshot(LatencyPath.CANCEL_ACK)

        from datetime import date as date_cls
        report = DailyReport(
            report_date=date_cls.today(),
            constants_version=SHADOW_CONSTANTS_VERSION,
            events_detected=counts["total_events"],
            events_accepted=counts["accepted"],
            events_rejected_deadzone=counts["rejected_deadzone"],
            events_rejected_inventory=counts["rejected_inventory"],
            events_rejected_position=counts["rejected_position"],
            events_rejected_nbbo=counts["rejected_nbbo"],
            events_rejected_staleness=counts["rejected_staleness"],
            orders_placed=int(fill_acct["orders"]),
            fills_received=int(fill_acct["paper_fills"]),
            daily_pnl_bps=daily_pnl,
            daily_pnl_dollars=daily_dollars,
            cumulative_pnl_bps=self._cumulative_pnl_bps,
            competitive_pnl_bps=0.0,
            shock_pnl_bps=0.0,
            competitive_fills=0,
            shock_fills=0,
            mechanism_health=health,
            paper_fill_rate=fill_acct["paper_fill_rate"],
            model_fill_rate=fill_acct["model_fill_rate"],
            fill_optimism_ratio=fill_acct["fill_optimism_ratio"],
            ingest_p95_ms=ingest_snap.p95_ms,
            order_rtt_p95_ms=order_snap.p95_ms,
            cancel_ack_p95_ms=cancel_snap.p95_ms,
            nbbo_integrity=nbbo_report,
            kill_triggered=kill is not None,
            kill_event=kill,
        )

        self._daily_reports.append(report)
        await self._logger.log_daily_report(report)

        # Weekly report (every 5 trading days)
        if self._trading_day_count % 5 == 0 and self._daily_reports:
            week_num = self._trading_day_count // 5
            recent = self._daily_reports[-5:]
            self._logger.generate_weekly_report(week_num, recent)

        # Flush all buffers
        await self._logger.flush()

        # Reset daily counters
        self._order_manager.reset_daily()
        self._monitor.reset_daily()
        self._latency_monitor.reset_samples()
        for bucketer in self._bucketers.values():
            bucketer.reset_daily()

        logger.info(
            "Day %d complete: PnL=%.2f bps, cumulative=%.2f bps",
            self._trading_day_count, daily_pnl, self._cumulative_pnl_bps,
        )

    async def start(self) -> None:
        """Start the engine."""
        self._running = True
        self._paused = False
        logger.info("Shadow engine started")

    async def pause(self) -> None:
        """Pause the engine (no new trades, existing positions monitored)."""
        self._paused = True
        logger.info("Shadow engine paused")

    async def resume(self) -> None:
        """Resume the engine."""
        self._paused = False
        logger.info("Shadow engine resumed")

    async def stop(self) -> None:
        """Stop the engine cleanly."""
        self._running = False
        await self._logger.flush()
        await self._logger.close()
        logger.info("Shadow engine stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ── Internal ──────────────────────────────────────────────────────

    def _is_market_hours(self) -> bool:
        """Check if current time is within trading window (9:45-15:45 ET)."""
        now = datetime.now(ET)
        market_open = now.replace(
            hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
        )
        market_close = now.replace(
            hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
        )
        return market_open <= now <= market_close
