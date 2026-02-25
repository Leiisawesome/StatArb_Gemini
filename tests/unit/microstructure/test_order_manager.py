"""
Tests for OrderManager.

Build Plan: v4-FINAL, Step 3
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from core_engine.microstructure.shadow.constants import (
    MIN_HOLD_MS,
    SPREAD_NORMAL_FACTOR,
    STOP_LOSS_BPS,
    TIMEOUT_S,
)
from core_engine.microstructure.shadow.order_manager import OrderManager
from core_engine.microstructure.shadow.types import (
    ExitReason,
    ImbalanceEvent,
    Quote,
    SubStrategy,
    TradeSignal,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_signal(
    symbol: str = "MSFT",
    side: str = "SELL",
    limit_price: float = 100.01,
    spread_ratio: float = 0.75,
    imbalance: float = 0.9,
    baseline_spread: float = 0.02,
    ts_ns: int = 1_700_000_000_000_000_000,
) -> TradeSignal:
    event = ImbalanceEvent(
        symbol=symbol, bucket_id=1, event_timestamp_ns=ts_ns - 200_000_000,
        flow_imbalance=imbalance, bucket_volume=1000, num_trades=50,
        vwap=100.0, bid_at_end=99.99, ask_at_end=100.01,
        median_spread_bps=2.0, classification_confidence=0.95,
        tick_rule_fallback_pct=0.05, bucket_date=date.today(),
    )
    quote = Quote(
        symbol=symbol, timestamp_ns=ts_ns,
        bid_price=99.99, ask_price=100.01,
        bid_size=500, ask_size=500,
    )
    return TradeSignal(
        symbol=symbol, event=event,
        sub_strategy=SubStrategy.COMPETITIVE if spread_ratio < 1.0 else SubStrategy.SHOCK,
        side=side, limit_price=limit_price,
        spread_ratio=spread_ratio, baseline_spread=baseline_spread,
        quote_at_entry=quote, quote_age_ms=5.0,
        entry_timestamp_ns=ts_ns,
        spread_trajectory=[2.0, 1.8, 1.5],
    )


def _make_quote(
    symbol: str = "MSFT",
    bid: float = 99.99,
    ask: float = 100.01,
    ts_ns: int = 1_700_000_000_001_000_000,
) -> Quote:
    return Quote(
        symbol=symbol, timestamp_ns=ts_ns,
        bid_price=bid, ask_price=ask,
        bid_size=500, ask_size=500,
    )


class TestOrderManager:

    def _make_manager(self) -> OrderManager:
        tmp = tempfile.mktemp(suffix=".json")
        return OrderManager(
            portfolio_value=200_000.0,
            state_log_path=tmp,
        )

    def test_place_order(self):
        mgr = self._make_manager()
        signal = _make_signal()
        order_id = mgr.place_order(signal)
        assert order_id is not None
        assert len(mgr.get_open_positions()) == 1

    def test_fill_callback(self):
        mgr = self._make_manager()
        signal = _make_signal()
        order_id = mgr.place_order(signal)
        mgr.on_fill(order_id, 100.01, 100)

        pos = mgr.get_open_positions()[0]
        assert pos.filled is True
        assert pos.fill_price == 100.01

    def test_spread_normalization_exit(self):
        """Exit when spread <= 105% of baseline."""
        mgr = self._make_manager()
        signal = _make_signal(baseline_spread=0.02)
        order_id = mgr.place_order(signal)

        # Simulate fill
        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Quote with spread <= 0.02 * 1.05 = 0.021
        # spread = 100.01 - 99.99 = 0.02 <= 0.021 -> exit
        exit_quote = _make_quote(
            bid=99.995, ask=100.015,  # spread = 0.02
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.exit_reason == ExitReason.SPREAD_NORMALIZATION

    def test_timeout_exit(self):
        """Exit after 30 seconds."""
        mgr = self._make_manager()
        signal = _make_signal(baseline_spread=0.001)  # very tight baseline -> won't normalize
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Wide spread (won't normalize), past timeout
        exit_quote = _make_quote(
            bid=99.0, ask=101.0,  # wide spread
            ts_ns=fill_ts + (TIMEOUT_S + 1) * 1_000_000_000,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.exit_reason == ExitReason.TIMEOUT

    def test_stop_loss_exit_buy(self):
        """Stop-loss exit when midpoint moves against BUY position > 3 bps."""
        mgr = self._make_manager()
        signal = _make_signal(side="BUY", limit_price=99.99, baseline_spread=0.001)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 99.99, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Midpoint drops: adverse_bps = (99.99 - 99.95) / 99.99 * 10000 = 4 bps > 3
        exit_quote = _make_quote(
            bid=99.90, ask=100.00,  # midpoint = 99.95, wide spread
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.exit_reason == ExitReason.STOP_LOSS

    def test_stop_loss_exit_sell(self):
        """Stop-loss exit when midpoint moves against SELL position > 3 bps."""
        mgr = self._make_manager()
        signal = _make_signal(side="SELL", limit_price=100.01, baseline_spread=0.001)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Midpoint rises: adverse_bps = (100.05 - 100.01) / 100.01 * 10000 = 4 bps > 3
        exit_quote = _make_quote(
            bid=100.00, ask=100.10,  # midpoint = 100.05, wide spread
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.exit_reason == ExitReason.STOP_LOSS

    def test_min_hold_prevents_early_exit(self):
        """No exit before MIN_HOLD_MS even if conditions are met."""
        mgr = self._make_manager()
        signal = _make_signal(baseline_spread=0.02)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Spread normalized but too early
        exit_quote = _make_quote(
            bid=99.995, ask=100.015,
            ts_ns=fill_ts + 100_000_000,  # only 100ms, below MIN_HOLD_MS=500ms
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is None

    def test_pnl_computation_buy(self):
        """P&L should be positive when midpoint rises for BUY."""
        mgr = self._make_manager()
        signal = _make_signal(side="BUY", limit_price=99.99, baseline_spread=0.02)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 99.99, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        # Midpoint rises and spread normalizes
        exit_quote = _make_quote(
            bid=100.02, ask=100.04,  # midpoint = 100.03
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.pnl_bps > 0

    def test_pnl_computation_sell(self):
        """P&L should be positive when midpoint drops for SELL."""
        mgr = self._make_manager()
        signal = _make_signal(side="SELL", limit_price=100.01, baseline_spread=0.02)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        exit_quote = _make_quote(
            bid=99.97, ask=99.99,  # midpoint = 99.98
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.pnl_bps > 0

    def test_daily_pnl_accumulates(self):
        """Daily P&L should accumulate across trades."""
        mgr = self._make_manager()
        for i in range(3):
            signal = _make_signal(baseline_spread=0.02)
            oid = mgr.place_order(signal)
            fill_ts = 1_700_000_000_000_000_000 + i * 100_000_000_000
            mgr.on_fill(oid, 100.01, 100)
            pos = [p for p in mgr.get_open_positions() if p.order_id == oid][0]
            pos.fill_time_ns = fill_ts

            exit_quote = _make_quote(
                bid=99.995, ask=100.015,
                ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
            )
            mgr.on_quote_update("MSFT", exit_quote)

        pnl_bps, pnl_dollars = mgr.get_daily_pnl()
        assert mgr.get_fill_counts()[1] == 3

    def test_slippage_decomposition(self):
        """Slippage fields should be computed correctly."""
        mgr = self._make_manager()
        signal = _make_signal(baseline_spread=0.02)
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.02, 100)  # slight slippage from 100.01
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        exit_quote = _make_quote(
            bid=99.995, ask=100.015,
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.slippage.actual_entry_price == 100.02
        assert outcome.slippage.expected_entry_price > 0

    def test_crash_recovery_state_persisted(self):
        """State log should be written to disk on every transition."""
        tmp = tempfile.mktemp(suffix=".json")
        mgr = OrderManager(portfolio_value=200_000.0, state_log_path=tmp)
        signal = _make_signal()
        order_id = mgr.place_order(signal)

        assert Path(tmp).exists()
        with open(tmp) as f:
            records = json.load(f)
        assert len(records) == 1
        assert records[0]["intent"] == "entry_submitted"

        mgr.on_fill(order_id, 100.01, 100)
        with open(tmp) as f:
            records = json.load(f)
        assert len(records) == 2
        assert records[1]["intent"] == "monitoring_exit"

    def test_unfilled_position_no_exit_check(self):
        """Unfilled positions should not trigger exit checks."""
        mgr = self._make_manager()
        signal = _make_signal()
        mgr.place_order(signal)
        # No fill — exit check should return None
        quote = _make_quote()
        outcome = mgr.on_quote_update("MSFT", quote)
        assert outcome is None

    def test_depth_logging(self):
        """Depth ratio should be recorded in trade outcome."""
        mgr = self._make_manager()
        signal = _make_signal()
        order_id = mgr.place_order(signal)

        fill_ts = 1_700_000_000_000_000_000
        mgr.on_fill(order_id, 100.01, 100)
        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = fill_ts

        exit_quote = _make_quote(
            bid=99.995, ask=100.015,
            ts_ns=fill_ts + MIN_HOLD_MS * 1_000_000 + 1,
        )
        outcome = mgr.on_quote_update("MSFT", exit_quote)
        assert outcome is not None
        assert outcome.nbbo_bid_size == 500
        assert outcome.nbbo_ask_size == 500
        assert outcome.order_depth_ratio > 0

    def test_reset_daily_clears_state(self):
        """reset_daily should clear P&L and fill counts."""
        mgr = self._make_manager()
        signal = _make_signal(baseline_spread=0.02)
        oid = mgr.place_order(signal)
        mgr.on_fill(oid, 100.01, 100)

        pos = mgr.get_open_positions()[0]
        pos.fill_time_ns = 1_700_000_000_000_000_000

        exit_quote = _make_quote(
            bid=99.995, ask=100.015,
            ts_ns=1_700_000_000_000_000_000 + MIN_HOLD_MS * 1_000_000 + 1,
        )
        mgr.on_quote_update("MSFT", exit_quote)
        assert mgr.get_fill_counts()[1] >= 1

        mgr.reset_daily()
        assert mgr.get_daily_pnl() == (0.0, 0.0)
        assert mgr.get_fill_counts() == (0, 0, 0)
