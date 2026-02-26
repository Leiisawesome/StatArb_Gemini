"""
Tests for MechanismMonitor.

Build Plan: v4-FINAL, Step 4
"""

from __future__ import annotations

from datetime import date

import pytest

from core_engine.microstructure.shadow.constants import (
    DAILY_LOSS_STOP_BPS,
    INGEST_P95_CAP_MS,
    KILL_DRAWDOWN_5D_MAX_BPS,
    NET_INVENTORY_CAP_BPS,
)
from core_engine.microstructure.shadow.mechanism_monitor import (
    MechanismMonitor,
    _ResearchBaselines,
)
from core_engine.microstructure.shadow.types import (
    ExitReason,
    KillConditionType,
    SlippageBreakdown,
    SubStrategy,
    TradeOutcome,
)


def _make_outcome(
    pnl_bps: float = 1.0,
    sub_strategy: SubStrategy = SubStrategy.COMPETITIVE,
    spread_ratio: float = 0.75,
    exit_reason: ExitReason = ExitReason.SPREAD_NORMALIZATION,
    hold_time_ms: float = 800.0,
    model_fill: bool = True,
) -> TradeOutcome:
    return TradeOutcome(
        symbol="MSFT",
        trade_date=date.today(),
        sub_strategy=sub_strategy,
        side="SELL",
        entry_time_ns=1_700_000_000_000_000_000,
        entry_price=100.01,
        entry_spread_ratio=spread_ratio,
        entry_imbalance=0.9,
        exit_time_ns=1_700_000_000_001_000_000,
        exit_price=100.005,
        exit_reason=exit_reason,
        hold_time_ms=hold_time_ms,
        pnl_bps=pnl_bps,
        pnl_dollars=pnl_bps / 10_000 * 100 * 100,
        slippage=SlippageBreakdown(
            expected_entry_price=100.0,
            actual_entry_price=100.01,
            entry_slippage_bps=1.0,
            expected_exit_price=100.005,
            actual_exit_price=100.005,
            exit_slippage_bps=0.0,
            cancel_delay_ms=5.0,
            partial_fill_ratio=1.0,
        ),
        nbbo_bid_size=500,
        nbbo_ask_size=500,
        order_depth_ratio=0.2,
        model_fill=model_fill,
        model_pnl_bps=pnl_bps * 0.7,
        spread_at_entry_bps=2.0,
        baseline_spread_bps=2.0,
        classification_confidence=0.95,
        quote_age_at_entry_ms=5.0,
    )


class TestMechanismMonitor:

    def test_m1_no_degradation_initially(self):
        monitor = MechanismMonitor()
        health = monitor.get_mechanism_health()
        assert health.degraded_count == 0

    def test_m1_detects_amplitude_degradation(self):
        baselines = _ResearchBaselines(m1_amplitude=2.0)
        monitor = MechanismMonitor(baselines=baselines)

        for _ in range(50):
            outcome = _make_outcome(spread_ratio=3.5)
            monitor.on_trade_complete(outcome)

        health = monitor.get_mechanism_health()
        assert health.amplitude_degraded is True

    def test_m2_substrategy_split(self):
        monitor = MechanismMonitor()
        for _ in range(5):
            monitor.on_trade_complete(
                _make_outcome(sub_strategy=SubStrategy.COMPETITIVE, pnl_bps=2.0)
            )
        for _ in range(3):
            monitor.on_trade_complete(
                _make_outcome(sub_strategy=SubStrategy.SHOCK, pnl_bps=0.5)
            )

        split = monitor.get_substrategy_split()
        assert split["competitive"]["count"] == 5
        assert split["shock"]["count"] == 3
        assert split["competitive"]["pnl_bps"] > split["shock"]["pnl_bps"]

    def test_m3_fill_accounting(self):
        monitor = MechanismMonitor()
        for _ in range(10):
            monitor.on_order_placed()
        for _ in range(7):
            monitor.on_trade_complete(_make_outcome(model_fill=True))
        for _ in range(3):
            monitor.on_trade_complete(_make_outcome(model_fill=False))

        acct = monitor.get_fill_accounting()
        assert acct["paper_fills"] == 10
        assert acct["model_fills"] == 7
        assert acct["orders"] == 10

    def test_m6_spread_ratio_distribution(self):
        monitor = MechanismMonitor()
        for r in [0.5, 0.6, 0.7, 0.9, 1.2, 1.5, 1.8, 2.1, 2.5, 3.0]:
            monitor.on_trade_complete(_make_outcome(spread_ratio=r))

        dist = monitor.get_spread_ratio_distribution()
        assert dist.q1_pct > 0  # some below 0.8
        assert dist.q5_pct > 0  # some above 2.0

    def test_m7_slippage_report(self):
        monitor = MechanismMonitor()
        for _ in range(5):
            monitor.on_trade_complete(_make_outcome())

        slip = monitor.get_slippage_report()
        assert slip.rolling_mean_entry_slippage_bps == 1.0
        assert slip.rolling_mean_partial_fill_ratio == 1.0

    def test_per_trade_kill_inventory_breach(self):
        monitor = MechanismMonitor()
        kill = monitor.check_per_trade_kills(
            net_inventory_bps=10.0,
            ingest_p95_ms=50.0,
            order_rtt_p95_ms=100.0,
            cancel_ack_median_ms=50.0,
            daily_pnl_bps=0.0,
        )
        assert kill is not None
        assert kill.condition == KillConditionType.INVENTORY_BREACH

    def test_per_trade_kill_latency_breach(self):
        monitor = MechanismMonitor()
        kill = monitor.check_per_trade_kills(
            net_inventory_bps=0.0,
            ingest_p95_ms=300.0,  # > 250ms cap
            order_rtt_p95_ms=100.0,
            cancel_ack_median_ms=50.0,
            daily_pnl_bps=0.0,
        )
        assert kill is not None
        assert kill.condition == KillConditionType.LATENCY_BREACH

    def test_per_trade_kill_intraday_loss(self):
        monitor = MechanismMonitor()
        kill = monitor.check_per_trade_kills(
            net_inventory_bps=0.0,
            ingest_p95_ms=50.0,
            order_rtt_p95_ms=100.0,
            cancel_ack_median_ms=50.0,
            daily_pnl_bps=-30.0,  # < -25 bps
        )
        assert kill is not None
        assert kill.condition == KillConditionType.INTRADAY_LOSS

    def test_per_trade_no_kill_normal(self):
        monitor = MechanismMonitor()
        kill = monitor.check_per_trade_kills(
            net_inventory_bps=2.0,
            ingest_p95_ms=50.0,
            order_rtt_p95_ms=100.0,
            cancel_ack_median_ms=50.0,
            daily_pnl_bps=5.0,
        )
        assert kill is None

    def test_daily_close_drawdown_kill(self):
        monitor = MechanismMonitor()
        # Simulate 5 days: big positive then big negatives
        for pnl in [20.0, -30.0, -25.0, -10.0, -10.0]:
            kill = monitor.check_daily_close_kills(pnl)
            if kill is not None:
                break

        # 5-day cumulative: 20, -10, -35, -45, -55
        # peak=20, trough=-55, drawdown=75 > 50 bps
        assert kill is not None
        assert kill.condition == KillConditionType.DRAWDOWN_5D

    def test_daily_close_no_kill_normal(self):
        monitor = MechanismMonitor()
        for pnl in [5.0, 3.0, 7.0, 2.0, 4.0]:
            kill = monitor.check_daily_close_kills(pnl)
        assert kill is None

    def test_reset_daily(self):
        monitor = MechanismMonitor()
        for _ in range(5):
            monitor.on_trade_complete(_make_outcome())
            monitor.on_event_detected()

        monitor.reset_daily()
        split = monitor.get_substrategy_split()
        assert split["competitive"]["count"] == 0
