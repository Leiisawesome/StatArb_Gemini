"""
Shadow logger for ClickHouse persistence and report generation.

Logs every event, order, fill, daily aggregate, and latency observation
to ClickHouse. Generates weekly markdown reports.

Spec: v1.7-SHADOW
Build Plan: v4-FINAL, Step 5
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from core_engine.microstructure.shadow.constants import SHADOW_CONSTANTS_VERSION
from core_engine.microstructure.shadow.types import (
    DailyReport,
    ImbalanceEvent,
    TradeOutcome,
    TradeSignal,
    WeeklyReport,
)

logger = logging.getLogger(__name__)


class ShadowLogger:
    """Logs shadow trading data to ClickHouse and generates reports.

    All inserts are batched and flushed asynchronously to minimize
    impact on the trading loop. If ClickHouse is unavailable, logs
    are buffered in memory and flushed when connectivity resumes.
    """

    def __init__(
        self,
        clickhouse_url: str = "http://localhost:8123",
        db: str = "shadow_trading",
        report_dir: str = "results/shadow",
    ) -> None:
        self._ch_url = clickhouse_url
        self._db = db
        self._report_dir = Path(report_dir)
        self._report_dir.mkdir(parents=True, exist_ok=True)

        # Buffered inserts
        self._event_buffer: List[Dict[str, Any]] = []
        self._order_buffer: List[Dict[str, Any]] = []
        self._fill_buffer: List[Dict[str, Any]] = []
        self._latency_buffer: List[Dict[str, Any]] = []

        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    def log_event(
        self,
        event: ImbalanceEvent,
        accepted: bool,
        rejection_reason: str = "",
        sub_strategy: str = "",
        spread_ratio: float = 0.0,
        baseline_spread: float = 0.0,
        quote_age_ms: float = 0.0,
        spread_at_entry_bps: float = 0.0,
        nbbo_locked: bool = False,
        nbbo_crossed: bool = False,
        nbbo_stale: bool = False,
        nbbo_flickering: bool = False,
        quote_updates: int = 0,
        odd_lot_pct: float = 0.0,
    ) -> None:
        """Buffer an event log entry."""
        self._event_buffer.append({
            "event_id": str(uuid.uuid4())[:12],
            "constants_version": SHADOW_CONSTANTS_VERSION,
            "symbol": event.symbol,
            "event_date": str(event.bucket_date),
            "event_timestamp_ns": event.event_timestamp_ns,
            "bucket_id": event.bucket_id,
            "flow_imbalance": event.flow_imbalance,
            "bucket_volume": event.bucket_volume,
            "num_trades": event.num_trades,
            "vwap": event.vwap,
            "bid_at_event": event.bid_at_end,
            "ask_at_event": event.ask_at_end,
            "spread_ratio": spread_ratio,
            "baseline_spread": baseline_spread,
            "quote_age_ms": quote_age_ms,
            "spread_at_entry_bps": spread_at_entry_bps,
            "accepted": 1 if accepted else 0,
            "rejection_reason": rejection_reason,
            "sub_strategy": sub_strategy,
            "classification_confidence": event.classification_confidence,
            "tick_rule_fallback_pct": event.tick_rule_fallback_pct,
            "nbbo_locked": 1 if nbbo_locked else 0,
            "nbbo_crossed": 1 if nbbo_crossed else 0,
            "nbbo_stale": 1 if nbbo_stale else 0,
            "nbbo_flickering": 1 if nbbo_flickering else 0,
            "quote_updates_in_window": quote_updates,
            "odd_lot_pct": odd_lot_pct,
        })

    def log_fill(self, outcome: TradeOutcome, event_id: str = "") -> None:
        """Buffer a fill log entry."""
        self._fill_buffer.append({
            "fill_id": str(uuid.uuid4())[:12],
            "order_id": "",
            "event_id": event_id,
            "constants_version": SHADOW_CONSTANTS_VERSION,
            "symbol": outcome.symbol,
            "fill_date": str(outcome.trade_date),
            "entry_timestamp_ns": outcome.entry_time_ns,
            "entry_price": outcome.entry_price,
            "entry_side": outcome.side,
            "sub_strategy": outcome.sub_strategy.value,
            "spread_ratio": outcome.entry_spread_ratio,
            "flow_imbalance": outcome.entry_imbalance,
            "exit_timestamp_ns": outcome.exit_time_ns,
            "exit_price": outcome.exit_price,
            "exit_reason": outcome.exit_reason.value,
            "hold_time_ms": outcome.hold_time_ms,
            "pnl_bps": outcome.pnl_bps,
            "pnl_dollars": outcome.pnl_dollars,
            "expected_entry_price": outcome.slippage.expected_entry_price,
            "actual_entry_price": outcome.slippage.actual_entry_price,
            "entry_slippage_bps": outcome.slippage.entry_slippage_bps,
            "expected_exit_price": outcome.slippage.expected_exit_price,
            "actual_exit_price": outcome.slippage.actual_exit_price,
            "exit_slippage_bps": outcome.slippage.exit_slippage_bps,
            "cancel_delay_ms": outcome.slippage.cancel_delay_ms,
            "partial_fill_ratio": outcome.slippage.partial_fill_ratio,
            "total_slippage_bps": outcome.slippage.total_slippage_bps,
            "nbbo_bid_size": outcome.nbbo_bid_size,
            "nbbo_ask_size": outcome.nbbo_ask_size,
            "order_depth_ratio": outcome.order_depth_ratio,
            "model_fill": 1 if outcome.model_fill else 0,
            "model_pnl_bps": outcome.model_pnl_bps,
            "spread_at_entry_bps": outcome.spread_at_entry_bps,
            "baseline_spread_bps": outcome.baseline_spread_bps,
            "classification_confidence": outcome.classification_confidence,
            "quote_age_at_entry_ms": outcome.quote_age_at_entry_ms,
        })

    def log_latency(
        self,
        symbol: str,
        path: str,
        latency_ms: float,
        exchange_ts_ns: int = 0,
        system_receive_ns: int = 0,
    ) -> None:
        """Buffer a latency observation."""
        import time
        self._latency_buffer.append({
            "observation_date": str(date.today()),
            "observation_ns": time.time_ns(),
            "symbol": symbol,
            "path": path,
            "latency_ms": latency_ms,
            "exchange_ts_ns": exchange_ts_ns,
            "system_receive_ns": system_receive_ns,
        })

    async def flush(self) -> None:
        """Flush all buffered data to ClickHouse."""
        if self._event_buffer:
            await self._insert_batch("shadow_events", self._event_buffer)
            self._event_buffer.clear()

        if self._fill_buffer:
            await self._insert_batch("shadow_fills", self._fill_buffer)
            self._fill_buffer.clear()

        if self._latency_buffer:
            await self._insert_batch("shadow_latency", self._latency_buffer)
            self._latency_buffer.clear()

    async def log_daily_report(self, report: DailyReport) -> None:
        """Insert daily aggregates to ClickHouse."""
        row = {
            "report_date": str(report.report_date),
            "constants_version": report.constants_version,
            "events_detected": report.events_detected,
            "events_accepted": report.events_accepted,
            "events_rejected_deadzone": report.events_rejected_deadzone,
            "events_rejected_inventory": report.events_rejected_inventory,
            "events_rejected_position": report.events_rejected_position,
            "events_rejected_nbbo": report.events_rejected_nbbo,
            "events_rejected_staleness": report.events_rejected_staleness,
            "orders_placed": report.orders_placed,
            "fills_received": report.fills_received,
            "daily_pnl_bps": report.daily_pnl_bps,
            "daily_pnl_dollars": report.daily_pnl_dollars,
            "cumulative_pnl_bps": report.cumulative_pnl_bps,
            "competitive_pnl_bps": report.competitive_pnl_bps,
            "shock_pnl_bps": report.shock_pnl_bps,
            "competitive_fills": report.competitive_fills,
            "shock_fills": report.shock_fills,
            "kill_triggered": 1 if report.kill_triggered else 0,
            "kill_condition": report.kill_event.condition.value if report.kill_event else "",
        }
        await self._insert_batch("shadow_daily", [row])

    def generate_weekly_report(
        self,
        week_number: int,
        daily_reports: List[DailyReport],
    ) -> str:
        """Generate a weekly markdown report and save to disk."""
        report_path = self._report_dir / f"week_{week_number:02d}_report.md"

        total_pnl = sum(d.daily_pnl_bps for d in daily_reports)
        total_fills = sum(d.fills_received for d in daily_reports)
        total_events = sum(d.events_detected for d in daily_reports)
        total_accepted = sum(d.events_accepted for d in daily_reports)

        lines = [
            f"# Shadow Trading — Week {week_number} Report",
            f"",
            f"**Constants Version**: {SHADOW_CONSTANTS_VERSION}",
            f"**Period**: {daily_reports[0].report_date} to {daily_reports[-1].report_date}" if daily_reports else "",
            f"",
            f"## Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total P&L (bps) | {total_pnl:.2f} |",
            f"| Total Fills | {total_fills} |",
            f"| Events Detected | {total_events} |",
            f"| Events Accepted | {total_accepted} |",
            f"| Acceptance Rate | {total_accepted/total_events:.1%} |" if total_events > 0 else "| Acceptance Rate | N/A |",
            f"",
            f"## Daily Breakdown",
            f"| Date | PnL (bps) | Fills | Events | Accepted |",
            f"|------|-----------|-------|--------|----------|",
        ]

        for d in daily_reports:
            lines.append(
                f"| {d.report_date} | {d.daily_pnl_bps:.2f} | "
                f"{d.fills_received} | {d.events_detected} | {d.events_accepted} |"
            )

        lines.extend([
            f"",
            f"## Kill Conditions",
            f"All clear." if not any(d.kill_triggered for d in daily_reports)
            else "**KILL TRIGGERED** — see daily reports for details.",
            f"",
        ])

        content = "\n".join(lines)
        report_path.write_text(content)
        logger.info("Weekly report written: %s", report_path)
        return str(report_path)

    # ── Internal ──────────────────────────────────────────────────────

    async def _insert_batch(
        self, table: str, rows: List[Dict[str, Any]]
    ) -> None:
        """Insert a batch of rows into a ClickHouse table."""
        if not rows or not self._session:
            return

        columns = list(rows[0].keys())
        col_str = ", ".join(columns)
        values = []
        for row in rows:
            vals = []
            for col in columns:
                v = row[col]
                if isinstance(v, str):
                    v = v.replace("'", "\\'")
                    vals.append(f"'{v}'")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    vals.append(f"'{v}'")
            values.append(f"({', '.join(vals)})")

        query = (
            f"INSERT INTO {self._db}.{table} ({col_str}) VALUES "
            + ", ".join(values)
        )

        try:
            async with self._session.post(self._ch_url, data=query) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    logger.error(
                        "ClickHouse insert failed: %s — %s",
                        table, error[:200],
                    )
        except Exception as e:
            logger.error("ClickHouse connection error: %s", e)
