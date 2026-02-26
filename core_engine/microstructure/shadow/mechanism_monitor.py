"""
Mechanism monitor for shadow trading system.

Tracks all 10 KPIs (M1-M10) from filled trades and market data.
Implements horizon-aligned kill conditions: per-trade for acute risk,
daily-close for structural risk.

M9 (v1.8): Event frequency collapse monitor — alerts when opportunity
flow drops >50% from 20-day average AND P&L decays. Operational pause
signal, not an automatic kill.

M10 (v1.8): Cross-symbol correlation — rolling 5-day pairwise P&L
correlation inside the universe. Alerts if >0.50 (correlated stop-loss
days become systemic risk).

Rolling 30-day P&L kill is COMPOUND (v1.8 per quant review):
Kill only when ALL hold: P&L negative AND M1 degraded AND frequency
NOT collapsed. Mechanism degradation leads, P&L confirms.

Spec: v1.8-SHADOW-SHOCK
Build Plan: v4-FINAL, Step 4
"""

from __future__ import annotations

import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Deque, Dict, List, Optional, Tuple

from core_engine.microstructure.shadow.constants import (
    FILL_OPTIMISM_RATIO_ALERT,
    INGEST_P95_CAP_MS,
    CANCEL_ACK_MEDIAN_CAP_MS,
    CROSS_SYMBOL_CORR_ALERT,
    CROSS_SYMBOL_CORR_WINDOW,
    EVENT_FREQ_BASELINE_DAYS,
    EVENT_FREQ_COLLAPSE_PCT,
    KILL_CORRELATION_MAX,
    KILL_CORRELATION_SUSTAINED_DAYS,
    KILL_DRAWDOWN_5D_MAX_BPS,
    KILL_FILL_RATE_MIN_PCT_OF_BASELINE,
    KILL_HALFLIFE_DRIFT_PCT,
    KILL_HALFLIFE_SUSTAINED_DAYS,
    KILL_ROLLING_30D_PNL_MIN_BPS,
    LOSS_VELOCITY_THRESHOLD_BPS,
    M1_DEGRADATION_THRESHOLD_PCT,
    M1_PAUSE_MIN_DEGRADED,
    M1_REVIEW_MIN_DEGRADED,
    M6_Q5_DROP_ALERT_PCT,
    M6_Q12_DROP_ALERT_PCT,
    NET_INVENTORY_CAP_BPS,
    ORDER_RTT_P95_CAP_MS,
    RESEARCH_QUINTILE_BOUNDARIES,
    SHADOW_CONSTANTS_VERSION,
    SHOCK_CLUSTER_MIN_SYMBOLS,
    SLIPPAGE_DRIFT_ALERT_PCT,
    SPREAD_RATIO_SHOCK_MIN,
    SPY_BETA_ALERT_THRESHOLD,
    SYMBOLS,
    DAILY_LOSS_STOP_BPS,
    BASELINE_FILL_RATE,
)
from core_engine.microstructure.shadow.types import (
    DailyReport,
    ExitReason,
    KillConditionType,
    KillEvent,
    MechanismHealthSurface,
    NBBOIntegrityReport,
    SlippageReport,
    SpreadRatioDistribution,
    SubStrategy,
    TradeOutcome,
    WeeklyReport,
)

logger = logging.getLogger(__name__)


@dataclass
class _ResearchBaselines:
    """Frozen baselines from research (or Step 7 backtest)."""
    m1_amplitude: float = 2.0
    m1_normalization_ms: float = 1300.0
    m1_event_frequency: float = 5.0
    fill_rate: float = 0.77
    mean_pnl_bps: float = 1.18
    hit_rate: float = 0.54
    q1_pct: float = 0.20
    q2_pct: float = 0.20
    q5_pct: float = 0.20
    entry_slippage_bps: float = 0.0
    exit_slippage_bps: float = 0.0
    cancel_delay_ms: float = 0.0


class MechanismMonitor:
    """Tracks M1-M10 KPIs and enforces kill conditions.

    Kill conditions are horizon-aligned:
    - Per-trade: inventory breach, latency breach, intraday loss
    - Daily-close: M1 health, compound rolling PnL, fill rate, drawdown
    - Alerts (operational, not auto-kill): M9 freq collapse, M10 cross-corr
    """

    def __init__(
        self,
        baselines: Optional[_ResearchBaselines] = None,
        drawdown_5d_limit: Optional[float] = None,
        rolling_30d_pnl_min: Optional[float] = None,
    ) -> None:
        self._baselines = baselines or _ResearchBaselines()
        self._drawdown_5d_limit = (
            drawdown_5d_limit if drawdown_5d_limit is not None
            else KILL_DRAWDOWN_5D_MAX_BPS
        )
        self._rolling_30d_min = (
            rolling_30d_pnl_min if rolling_30d_pnl_min is not None
            else KILL_ROLLING_30D_PNL_MIN_BPS
        )

        # Trade history (rolling windows)
        self._recent_trades: Deque[TradeOutcome] = deque(maxlen=5000)
        self._daily_pnl_history: List[float] = []

        # M1: mechanism health surface
        self._spread_amplitudes: Deque[float] = deque(maxlen=500)
        self._normalization_times: Deque[float] = deque(maxlen=500)
        self._daily_event_counts: Deque[float] = deque(maxlen=30)

        # M2: sub-strategy tracking
        self._competitive_trades: List[TradeOutcome] = []
        self._shock_trades: List[TradeOutcome] = []

        # M3: fill accounting
        self._paper_fill_count: int = 0
        self._model_fill_count: int = 0
        self._paper_order_count: int = 0

        # M4: SPY beta (daily values)
        self._spy_betas: Deque[float] = deque(maxlen=20)

        # M5: throughput
        self._daily_fill_count: int = 0
        self._daily_event_count: int = 0

        # M6: spread ratio distribution
        self._spread_ratios: Deque[float] = deque(maxlen=1000)

        # M10: cross-symbol correlation
        self._symbol_daily_pnl: Dict[str, float] = {s: 0.0 for s in SYMBOLS}
        self._symbol_pnl_history: Dict[str, List[float]] = {s: [] for s in SYMBOLS}

        # M10b: shock event clustering (forward-looking)
        self._daily_shock_symbols: set = set()

        # Loss velocity tracking (rolling intraday P&L with timestamps)
        self._intraday_pnl_entries: List[Tuple[float, float]] = []

        # Kill condition tracking
        self._consecutive_halflife_drift_days: int = 0
        self._consecutive_correlation_days: int = 0
        self._kill_triggered: bool = False
        self._kill_event: Optional[KillEvent] = None

    def on_trade_complete(self, outcome: TradeOutcome) -> None:
        """Process a completed trade for all monitors."""
        self._recent_trades.append(outcome)

        # M1: track amplitude and normalization
        self._spread_amplitudes.append(outcome.entry_spread_ratio)
        if outcome.exit_reason == ExitReason.SPREAD_NORMALIZATION:
            self._normalization_times.append(outcome.hold_time_ms)

        # M2: sub-strategy split
        if outcome.sub_strategy == SubStrategy.COMPETITIVE:
            self._competitive_trades.append(outcome)
        else:
            self._shock_trades.append(outcome)

        # M3: fill accounting
        self._paper_fill_count += 1
        if outcome.model_fill:
            self._model_fill_count += 1

        # M5: throughput
        self._daily_fill_count += 1

        # M6: spread ratio
        self._spread_ratios.append(outcome.entry_spread_ratio)

        # M10: per-symbol daily P&L
        sym = outcome.symbol
        if sym in self._symbol_daily_pnl:
            self._symbol_daily_pnl[sym] += outcome.pnl_bps

        # Loss velocity: record timestamp + cumulative intraday P&L
        cumulative = sum(e[1] for e in self._intraday_pnl_entries) + outcome.pnl_bps
        self._intraday_pnl_entries.append((outcome.hold_time_ms, outcome.pnl_bps))

    def on_event_detected(self, symbol: str = "", spread_ratio: float = 0.0) -> None:
        """Track event detection for throughput (M5) and shock clustering (M10b)."""
        self._daily_event_count += 1
        if spread_ratio >= SPREAD_RATIO_SHOCK_MIN and symbol:
            self._daily_shock_symbols.add(symbol)

    def on_order_placed(self) -> None:
        """Track order placement for fill accounting (M3)."""
        self._paper_order_count += 1

    def record_spy_beta(self, beta: float) -> None:
        """Record daily SPY beta for M4."""
        self._spy_betas.append(beta)

    # ── Per-trade kill checks (acute risk) ──────────────────────────

    def check_per_trade_kills(
        self,
        net_inventory_bps: float,
        ingest_p95_ms: float,
        order_rtt_p95_ms: float,
        cancel_ack_median_ms: float,
        daily_pnl_bps: float,
    ) -> Optional[KillEvent]:
        """Check acute kill conditions on every trade completion."""
        now = datetime.now()

        if abs(net_inventory_bps) > NET_INVENTORY_CAP_BPS:
            return KillEvent(
                condition=KillConditionType.INVENTORY_BREACH,
                triggered_at=now,
                metric_value=net_inventory_bps,
                threshold=NET_INVENTORY_CAP_BPS,
                detail=f"Net inventory {net_inventory_bps:.2f} bps > ±{NET_INVENTORY_CAP_BPS}",
                horizon="per_trade",
            )

        if ingest_p95_ms > INGEST_P95_CAP_MS:
            return KillEvent(
                condition=KillConditionType.LATENCY_BREACH,
                triggered_at=now,
                metric_value=ingest_p95_ms,
                threshold=INGEST_P95_CAP_MS,
                detail=f"Ingest p95 {ingest_p95_ms:.0f}ms > {INGEST_P95_CAP_MS}ms",
                horizon="per_trade",
            )

        if order_rtt_p95_ms > ORDER_RTT_P95_CAP_MS:
            return KillEvent(
                condition=KillConditionType.LATENCY_BREACH,
                triggered_at=now,
                metric_value=order_rtt_p95_ms,
                threshold=ORDER_RTT_P95_CAP_MS,
                detail=f"Order RTT p95 {order_rtt_p95_ms:.0f}ms > {ORDER_RTT_P95_CAP_MS}ms",
                horizon="per_trade",
            )

        if cancel_ack_median_ms > CANCEL_ACK_MEDIAN_CAP_MS:
            return KillEvent(
                condition=KillConditionType.LATENCY_BREACH,
                triggered_at=now,
                metric_value=cancel_ack_median_ms,
                threshold=CANCEL_ACK_MEDIAN_CAP_MS,
                detail=f"Cancel ack median {cancel_ack_median_ms:.0f}ms > {CANCEL_ACK_MEDIAN_CAP_MS}ms",
                horizon="per_trade",
            )

        if daily_pnl_bps < DAILY_LOSS_STOP_BPS:
            return KillEvent(
                condition=KillConditionType.INTRADAY_LOSS,
                triggered_at=now,
                metric_value=daily_pnl_bps,
                threshold=DAILY_LOSS_STOP_BPS,
                detail=f"Intraday loss {daily_pnl_bps:.2f} bps < {DAILY_LOSS_STOP_BPS}",
                horizon="per_trade",
            )

        return None

    # ── Daily close kill checks (structural risk) ───────────────────

    def check_daily_close_kills(self, daily_pnl_bps: float) -> Optional[KillEvent]:
        """Check structural kill conditions at end of day."""
        self._daily_pnl_history.append(daily_pnl_bps)
        self._daily_event_counts.append(self._daily_event_count)
        now = datetime.now()

        # M1: mechanism health surface
        health = self.get_mechanism_health()
        if health.degraded_count >= M1_PAUSE_MIN_DEGRADED:
            return KillEvent(
                condition=KillConditionType.M1_MECHANISM_PAUSE,
                triggered_at=now,
                metric_value=float(health.degraded_count),
                threshold=float(M1_PAUSE_MIN_DEGRADED),
                detail=f"M1: {health.degraded_count}/3 dimensions degraded > {M1_DEGRADATION_THRESHOLD_PCT:.0%}",
                horizon="daily_close",
            )

        # Rolling 30-day mean PnL — COMPOUND condition (v1.8-FINAL):
        # Three paths to kill:
        # A) P&L negative + M1 degraded + frequency active → structural decay
        # B) P&L negative + frequency collapsed + Q5 distribution shifted → regime death
        # C) P&L negative but frequency collapsed with stable Q5 → seasonal, no kill
        #
        # Frequency collapse alone is NOT benign (quant review):
        # Holiday compression with stable Q5 is seasonal.
        # Frequency collapse with Q5 shifting lower is structural liquidity change.
        if len(self._daily_pnl_history) >= 30:
            rolling_30d = statistics.mean(self._daily_pnl_history[-30:])
            if rolling_30d < self._rolling_30d_min:
                m1_degraded = health.degraded_count >= 1
                freq_collapsed = False
                if len(self._daily_event_counts) >= EVENT_FREQ_BASELINE_DAYS:
                    recent_freq = list(self._daily_event_counts)[-EVENT_FREQ_BASELINE_DAYS:]
                    avg_freq = statistics.mean(recent_freq)
                    if avg_freq > 0:
                        current_freq = self._daily_event_count
                        freq_collapsed = (1.0 - current_freq / avg_freq) >= EVENT_FREQ_COLLAPSE_PCT

                # Path A: mechanism degraded + market still active
                if m1_degraded and not freq_collapsed:
                    return KillEvent(
                        condition=KillConditionType.ROLLING_PNL_LOW,
                        triggered_at=now,
                        metric_value=rolling_30d,
                        threshold=self._rolling_30d_min,
                        detail=(
                            f"COMPOUND KILL (path A): Rolling 30d PnL {rolling_30d:.2f} bps "
                            f"+ M1 degraded ({health.degraded_count}/3) + frequency active"
                        ),
                        horizon="daily_close",
                    )

                # Path B: frequency collapsed — check if Q5 distribution shifted
                if freq_collapsed:
                    q5_structural = False
                    dist = self.get_spread_ratio_distribution()
                    if self._baselines.q5_pct > 0:
                        q5_drop = 1.0 - dist.q5_pct / self._baselines.q5_pct
                        if q5_drop >= M6_Q5_DROP_ALERT_PCT:
                            q5_structural = True

                    if q5_structural:
                        return KillEvent(
                            condition=KillConditionType.ROLLING_PNL_LOW,
                            triggered_at=now,
                            metric_value=rolling_30d,
                            threshold=self._rolling_30d_min,
                            detail=(
                                f"COMPOUND KILL (path B): Rolling 30d PnL {rolling_30d:.2f} bps "
                                f"+ frequency collapsed + Q5 shifted (structural regime death)"
                            ),
                            horizon="daily_close",
                        )

                    reason = "frequency collapsed, Q5 stable (seasonal)"
                    logger.info(
                        "Rolling 30d PnL %.2f bps < %.1f but %s — no kill",
                        rolling_30d, self._rolling_30d_min, reason,
                    )
                elif not m1_degraded:
                    logger.info(
                        "Rolling 30d PnL %.2f bps < %.1f but M1 healthy — no kill",
                        rolling_30d, self._rolling_30d_min,
                    )

        # Fill rate vs baseline
        if self._paper_order_count > 0:
            fill_rate = self._paper_fill_count / self._paper_order_count
            min_rate = BASELINE_FILL_RATE * KILL_FILL_RATE_MIN_PCT_OF_BASELINE
            if fill_rate < min_rate and self._paper_order_count >= 20:
                return KillEvent(
                    condition=KillConditionType.FILL_RATE_LOW,
                    triggered_at=now,
                    metric_value=fill_rate,
                    threshold=min_rate,
                    detail=f"Fill rate {fill_rate:.2%} < {min_rate:.2%}",
                    horizon="daily_close",
                )

        # Rolling 5-day drawdown
        if len(self._daily_pnl_history) >= 5:
            cumulative = []
            running = 0.0
            for p in self._daily_pnl_history[-5:]:
                running += p
                cumulative.append(running)
            peak = max(cumulative)
            trough = min(cumulative)
            drawdown = peak - trough
            if drawdown > self._drawdown_5d_limit:
                return KillEvent(
                    condition=KillConditionType.DRAWDOWN_5D,
                    triggered_at=now,
                    metric_value=drawdown,
                    threshold=self._drawdown_5d_limit,
                    detail=f"5-day peak-to-trough {drawdown:.2f} bps > {self._drawdown_5d_limit}",
                    horizon="daily_close",
                )

        return None

    # ── Monitor accessors ───────────────────────────────────────────

    def get_mechanism_health(self) -> MechanismHealthSurface:
        """M1: Three-variable mechanism health surface."""
        b = self._baselines

        amplitude = (
            statistics.median(self._spread_amplitudes)
            if self._spread_amplitudes else b.m1_amplitude
        )
        norm_ms = (
            statistics.median(self._normalization_times)
            if self._normalization_times else b.m1_normalization_ms
        )
        freq = (
            statistics.mean(self._daily_event_counts)
            if self._daily_event_counts else b.m1_event_frequency
        )

        amp_degraded = (
            abs(amplitude - b.m1_amplitude) / b.m1_amplitude > M1_DEGRADATION_THRESHOLD_PCT
            if b.m1_amplitude > 0 else False
        )
        speed_degraded = (
            abs(norm_ms - b.m1_normalization_ms) / b.m1_normalization_ms > M1_DEGRADATION_THRESHOLD_PCT
            if b.m1_normalization_ms > 0 else False
        )
        freq_degraded = (
            abs(freq - b.m1_event_frequency) / b.m1_event_frequency > M1_DEGRADATION_THRESHOLD_PCT
            if b.m1_event_frequency > 0 else False
        )

        return MechanismHealthSurface(
            median_spread_amplitude=amplitude,
            median_time_to_normalization_ms=norm_ms,
            events_per_symbol_per_day=freq,
            baseline_amplitude=b.m1_amplitude,
            baseline_normalization_ms=b.m1_normalization_ms,
            baseline_event_frequency=b.m1_event_frequency,
            amplitude_degraded=amp_degraded,
            speed_degraded=speed_degraded,
            frequency_degraded=freq_degraded,
        )

    def get_substrategy_split(self) -> Dict[str, Dict[str, float]]:
        """M2: Sub-strategy P&L split."""
        def _stats(trades: List[TradeOutcome]) -> Dict[str, float]:
            if not trades:
                return {"pnl_bps": 0.0, "hit_rate": 0.0, "count": 0}
            pnls = [t.pnl_bps for t in trades]
            return {
                "pnl_bps": statistics.mean(pnls),
                "hit_rate": sum(1 for p in pnls if p > 0) / len(pnls),
                "count": len(trades),
            }
        return {
            "competitive": _stats(self._competitive_trades),
            "shock": _stats(self._shock_trades),
        }

    def get_fill_accounting(self) -> Dict[str, float]:
        """M3: Dual fill rate accounting."""
        paper_rate = (
            self._paper_fill_count / self._paper_order_count
            if self._paper_order_count > 0 else 0.0
        )
        model_rate = (
            self._model_fill_count / self._paper_order_count
            if self._paper_order_count > 0 else 0.0
        )
        optimism = paper_rate / model_rate if model_rate > 0 else 0.0
        return {
            "paper_fill_rate": paper_rate,
            "model_fill_rate": model_rate,
            "fill_optimism_ratio": optimism,
            "paper_fills": self._paper_fill_count,
            "model_fills": self._model_fill_count,
            "orders": self._paper_order_count,
        }

    def get_spread_ratio_distribution(self) -> SpreadRatioDistribution:
        """M6: Spread ratio distribution against frozen quintile boundaries."""
        if not self._spread_ratios:
            return SpreadRatioDistribution(
                q1_pct=0, q2_pct=0, q3_pct=0, q4_pct=0, q5_pct=0,
            )

        total = len(self._spread_ratios)
        # Use generic quintile boundaries
        bounds = [0.8, 1.0, 1.5, 2.0]
        q1 = sum(1 for r in self._spread_ratios if r < bounds[0]) / total
        q2 = sum(1 for r in self._spread_ratios if bounds[0] <= r < bounds[1]) / total
        q3 = sum(1 for r in self._spread_ratios if bounds[1] <= r < bounds[2]) / total
        q4 = sum(1 for r in self._spread_ratios if bounds[2] <= r < bounds[3]) / total
        q5 = sum(1 for r in self._spread_ratios if r >= bounds[3]) / total

        return SpreadRatioDistribution(
            q1_pct=q1, q2_pct=q2, q3_pct=q3, q4_pct=q4, q5_pct=q5,
            baseline_q1_pct=self._baselines.q1_pct,
            baseline_q2_pct=self._baselines.q2_pct,
            baseline_q5_pct=self._baselines.q5_pct,
        )

    def get_slippage_report(self) -> SlippageReport:
        """M7: Slippage decomposition summary."""
        if not self._recent_trades:
            return SlippageReport(
                rolling_mean_entry_slippage_bps=0,
                rolling_mean_exit_slippage_bps=0,
                rolling_mean_cancel_delay_ms=0,
                rolling_mean_partial_fill_ratio=1.0,
            )

        trades = list(self._recent_trades)[-100:]
        return SlippageReport(
            rolling_mean_entry_slippage_bps=statistics.mean(
                t.slippage.entry_slippage_bps for t in trades
            ),
            rolling_mean_exit_slippage_bps=statistics.mean(
                t.slippage.exit_slippage_bps for t in trades
            ),
            rolling_mean_cancel_delay_ms=statistics.mean(
                t.slippage.cancel_delay_ms for t in trades
            ),
            rolling_mean_partial_fill_ratio=statistics.mean(
                t.slippage.partial_fill_ratio for t in trades
            ),
            baseline_entry_slippage_bps=self._baselines.entry_slippage_bps,
            baseline_exit_slippage_bps=self._baselines.exit_slippage_bps,
            baseline_cancel_delay_ms=self._baselines.cancel_delay_ms,
        )

    def check_cross_symbol_correlation(self) -> Optional[Dict[str, float]]:
        """M10: Rolling cross-symbol P&L correlation.

        Computes average pairwise correlation of per-symbol daily P&L
        over the last CROSS_SYMBOL_CORR_WINDOW days. If >0.50, correlated
        stop-loss days become systemic risk.

        Returns alert dict or None.
        """
        window = CROSS_SYMBOL_CORR_WINDOW
        active = [
            s for s in SYMBOLS
            if len(self._symbol_pnl_history.get(s, [])) >= window
        ]
        if len(active) < 2:
            return None

        correlations = []
        for i, s1 in enumerate(active):
            for s2 in active[i + 1:]:
                series1 = self._symbol_pnl_history[s1][-window:]
                series2 = self._symbol_pnl_history[s2][-window:]
                if all(v == series1[0] for v in series1) or all(v == series2[0] for v in series2):
                    continue
                try:
                    corr = statistics.correlation(series1, series2)
                    correlations.append(corr)
                except (statistics.StatisticsError, ZeroDivisionError):
                    continue

        if not correlations:
            return None

        avg_corr = statistics.mean(correlations)
        if avg_corr > CROSS_SYMBOL_CORR_ALERT:
            alert = {
                "avg_pairwise_correlation": avg_corr,
                "num_pairs": len(correlations),
                "window_days": window,
            }
            logger.warning(
                "M10 cross-symbol correlation alert: avg=%.3f > %.2f (%d pairs, %d-day window)",
                avg_corr, CROSS_SYMBOL_CORR_ALERT, len(correlations), window,
            )
            return alert
        return None

    def check_loss_velocity(self) -> Optional[Dict[str, float]]:
        """Loss velocity monitor: fast structural break detection.

        Checks if cumulative intraday P&L dropped >25 bps. In the live
        engine this checks within 30 minutes; in the backtest it checks
        intraday P&L accumulation. Returns investigation flag (red alert,
        not auto-kill) if triggered.
        """
        if len(self._intraday_pnl_entries) < 3:
            return None

        cumulative = 0.0
        min_cumulative = 0.0
        max_cumulative = 0.0
        for _, pnl in self._intraday_pnl_entries:
            cumulative += pnl
            min_cumulative = min(min_cumulative, cumulative)
            max_cumulative = max(max_cumulative, cumulative)

        intraday_drawdown = max_cumulative - min_cumulative
        if intraday_drawdown > LOSS_VELOCITY_THRESHOLD_BPS:
            health = self.get_mechanism_health()
            alert = {
                "intraday_drawdown_bps": intraday_drawdown,
                "m1_degraded_count": health.degraded_count,
                "trades_today": len(self._intraday_pnl_entries),
            }
            if health.degraded_count >= 1:
                logger.warning(
                    "LOSS VELOCITY RED ALERT: %.1f bps intraday drawdown "
                    "+ M1 degraded (%d/3) — investigate immediately",
                    intraday_drawdown, health.degraded_count,
                )
            else:
                logger.warning(
                    "LOSS VELOCITY ALERT: %.1f bps intraday drawdown "
                    "(M1 healthy — likely variance, not structural)",
                    intraday_drawdown,
                )
            return alert
        return None

    def check_shock_clustering(self) -> Optional[Dict[str, object]]:
        """M10b: Forward-looking shock event clustering.

        Tracks how many distinct symbols fired shock events today.
        If >= SHOCK_CLUSTER_MIN_SYMBOLS, alerts before P&L correlation
        materializes. Inventory cap protects per-symbol stacking but not
        correlated cross-symbol shock stacking.
        """
        n_symbols = len(self._daily_shock_symbols)
        if n_symbols >= SHOCK_CLUSTER_MIN_SYMBOLS:
            alert = {
                "shock_symbols": sorted(self._daily_shock_symbols),
                "count": n_symbols,
                "total_symbols": len(SYMBOLS),
            }
            logger.warning(
                "M10b SHOCK CLUSTER: %d/%d symbols fired shocks today (%s) — "
                "correlated exposure risk elevated",
                n_symbols, len(SYMBOLS),
                ", ".join(sorted(self._daily_shock_symbols)),
            )
            return alert
        return None

    def check_event_frequency_alert(
        self, daily_pnl_bps: float,
    ) -> Optional[Dict[str, float]]:
        """M9: Compound alert — event frequency collapse AND P&L decay.

        Returns alert dict if BOTH conditions hold:
        1. Today's event count < (1 - EVENT_FREQ_COLLAPSE_PCT) × 20-day average
        2. daily_pnl_bps < 0

        This is an operational pause signal, not an automatic kill.
        The operator decides whether to reduce exposure or wait.
        """
        if len(self._daily_event_counts) < EVENT_FREQ_BASELINE_DAYS:
            return None

        recent = list(self._daily_event_counts)[-EVENT_FREQ_BASELINE_DAYS:]
        avg_20d = statistics.mean(recent)

        if avg_20d <= 0:
            return None

        current = self._daily_event_count
        decline_pct = 1.0 - (current / avg_20d)

        if decline_pct > EVENT_FREQ_COLLAPSE_PCT and daily_pnl_bps < 0:
            alert = {
                "current_events": float(current),
                "avg_20d_events": avg_20d,
                "decline_pct": decline_pct,
                "daily_pnl_bps": daily_pnl_bps,
            }
            logger.warning(
                "M9 event frequency collapse: %d events vs %.1f 20d avg "
                "(%.0f%% drop), P&L=%.2f bps",
                current, avg_20d, decline_pct * 100, daily_pnl_bps,
            )
            return alert

        return None

    def reset_daily(self) -> None:
        """Reset daily-scoped counters and archive per-symbol P&L."""
        for sym in SYMBOLS:
            self._symbol_pnl_history[sym].append(self._symbol_daily_pnl.get(sym, 0.0))
            self._symbol_daily_pnl[sym] = 0.0
        self._daily_fill_count = 0
        self._daily_event_count = 0
        self._daily_shock_symbols.clear()
        self._intraday_pnl_entries.clear()
        self._competitive_trades.clear()
        self._shock_trades.clear()

    @property
    def is_killed(self) -> bool:
        return self._kill_triggered

    @property
    def kill_event(self) -> Optional[KillEvent]:
        return self._kill_event
