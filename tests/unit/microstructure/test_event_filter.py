"""
Tests for EventLevelFilter and InventoryTracker.

Build Plan: v4-FINAL, Step 2
"""

from __future__ import annotations

from datetime import date

import pytest

from core_engine.microstructure.shadow.constants import (
    CLIP_SIZE,
    ENTRY_DELAY_MS,
    NET_INVENTORY_CAP_BPS,
)
from core_engine.microstructure.shadow.event_filter import (
    EventLevelFilter,
    InventoryTracker,
)
from core_engine.microstructure.shadow.types import (
    ImbalanceEvent,
    Quote,
    SubStrategy,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_event(
    symbol: str = "MSFT",
    imbalance: float = 0.9,
    bid: float = 99.0,
    ask: float = 101.0,
    ts_ns: int = 1_700_000_000_000_000_000,
) -> ImbalanceEvent:
    return ImbalanceEvent(
        symbol=symbol,
        bucket_id=1,
        event_timestamp_ns=ts_ns,
        flow_imbalance=imbalance,
        bucket_volume=1000,
        num_trades=50,
        vwap=100.0,
        bid_at_end=bid,
        ask_at_end=ask,
        median_spread_bps=2.0,
        classification_confidence=0.95,
        tick_rule_fallback_pct=0.05,
        bucket_date=date.today(),
    )


def _make_quote(
    symbol: str = "MSFT",
    bid: float = 99.0,
    ask: float = 101.0,
    ts_ns: int = 1_700_000_000_000_200_000,
    bid_size: int = 500,
    ask_size: int = 500,
) -> Quote:
    return Quote(
        symbol=symbol,
        timestamp_ns=ts_ns,
        bid_price=bid,
        ask_price=ask,
        bid_size=bid_size,
        ask_size=ask_size,
    )


def _make_filter(portfolio_value: float = 200_000.0) -> tuple[EventLevelFilter, InventoryTracker]:
    tracker = InventoryTracker(portfolio_value)
    f = EventLevelFilter(tracker)
    # Realistic baseline spreads (dollars): MSFT ~2 cents, NVDA ~1 cent
    f.set_baseline_spread("MSFT", 0.02)
    f.set_baseline_spread("NVDA", 0.01)
    return f, tracker


# ============================================================================
# InventoryTracker tests
# ============================================================================

class TestInventoryTracker:

    def test_empty_inventory(self):
        tracker = InventoryTracker(200_000.0)
        assert tracker.get_net_inventory_bps() == 0.0

    def test_single_long_position(self):
        tracker = InventoryTracker(200_000.0)
        tracker.add_position("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        assert abs(tracker.get_net_inventory_bps() - 2.0) < 0.01

    def test_opposing_positions_cancel(self):
        tracker = InventoryTracker(200_000.0)
        tracker.add_position("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        tracker.add_position("NVDA", "SELL", 100, 400.0, spread_bps=2.0)
        assert abs(tracker.get_net_inventory_bps()) < 0.01

    def test_would_breach_cap(self):
        tracker = InventoryTracker(200_000.0)
        # Spread of 7 bps exceeds ±6 bps cap
        result = tracker.would_breach_cap("MSFT", "BUY", 100, 400.0, spread_bps=7.0)
        assert result is True

    def test_small_position_no_breach(self):
        tracker = InventoryTracker(200_000.0)
        # Spread of 2 bps is within ±6 bps cap
        result = tracker.would_breach_cap("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        assert result is False

    def test_has_open_position(self):
        tracker = InventoryTracker(200_000.0)
        assert not tracker.has_open_position("MSFT")
        tracker.add_position("MSFT", "BUY", 100, 400.0)
        assert tracker.has_open_position("MSFT")

    def test_remove_position(self):
        tracker = InventoryTracker(200_000.0)
        tracker.add_position("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        tracker.remove_position("MSFT", "BUY")
        assert not tracker.has_open_position("MSFT")
        assert tracker.get_net_inventory_bps() == 0.0

    def test_cumulative_breach(self):
        """Multiple same-direction positions should accumulate toward cap."""
        tracker = InventoryTracker(200_000.0)
        tracker.add_position("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        tracker.add_position("NVDA", "BUY", 100, 800.0, spread_bps=1.5)
        tracker.add_position("TSLA", "BUY", 100, 200.0, spread_bps=3.0)
        # Net = 2.0 + 1.5 + 3.0 = 6.5 bps
        assert tracker.get_net_inventory_bps() > NET_INVENTORY_CAP_BPS


# ============================================================================
# EventLevelFilter tests
# ============================================================================

class TestEventLevelFilter:

    def test_competitive_entry_accepted(self):
        """spread_ratio < 1.0 should be accepted as competitive."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        # baseline_spread = 0.02, current_spread = 0.015 => ratio = 0.75 < 1.0
        quote = _make_quote(bid=99.9925, ask=100.0075)  # spread = 0.015
        for i in range(3):
            q = _make_quote(bid=99.9925, ask=100.0075,
                            ts_ns=event.event_timestamp_ns + i * 50_000_000)
            f.record_quote(q)

        signal = f.evaluate(event, quote)
        assert signal is not None
        assert signal.sub_strategy == SubStrategy.COMPETITIVE
        assert signal.spread_ratio < 1.0

    def test_shock_entry_accepted(self):
        """spread_ratio > 2.0 should be accepted as shock."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        # baseline_spread = 0.02, current_spread = 0.05 => ratio = 2.5 > 2.0
        quote = _make_quote(bid=99.975, ask=100.025)  # spread = 0.05
        for i in range(3):
            q = _make_quote(bid=99.975, ask=100.025,
                            ts_ns=event.event_timestamp_ns + i * 50_000_000)
            f.record_quote(q)

        signal = f.evaluate(event, quote)
        assert signal is not None
        assert signal.sub_strategy == SubStrategy.SHOCK
        assert signal.spread_ratio > 2.0

    def test_dead_zone_rejected(self):
        """spread_ratio in [1.0, 2.0] should be rejected."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        # baseline_spread = 0.02, current_spread = 0.03 => ratio = 1.5
        quote = _make_quote(bid=99.985, ask=100.015)  # spread = 0.03
        for i in range(3):
            q = _make_quote(bid=99.985, ask=100.015,
                            ts_ns=event.event_timestamp_ns + i * 50_000_000)
            f.record_quote(q)

        signal = f.evaluate(event, quote)
        assert signal is None
        assert f.rejection_counts["rejected_deadzone"] == 1

    def test_locked_market_rejected(self):
        """Locked market (bid >= ask) should be rejected."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        quote = _make_quote(bid=100.0, ask=100.0)  # locked
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is None
        assert f.rejection_counts["rejected_nbbo"] >= 1

    def test_crossed_market_rejected(self):
        """Crossed market (bid > ask) should be rejected."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        quote = _make_quote(bid=100.01, ask=99.99)  # crossed
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is None

    def test_stale_quote_rejected(self):
        """Quote older than QUOTE_STALENESS_MAX_MS should be rejected."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        stale_ts = event.event_timestamp_ns - 500_000_000_000  # 500ms before event
        quote = _make_quote(bid=99.9925, ask=100.0075, ts_ns=stale_ts)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is None
        assert f.rejection_counts["rejected_staleness"] >= 1

    def test_flickering_rejected(self):
        """Too few quote updates in 200ms window should be rejected."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        quote = _make_quote(bid=99.9925, ask=100.0075)
        # No recorded quotes in the window -> flickering check fails

        signal = f.evaluate(event, quote)
        assert signal is None
        assert f.rejection_counts["rejected_nbbo"] >= 1

    def test_position_limit_rejected(self):
        """If symbol already has an open position, reject."""
        f, tracker = _make_filter()
        tracker.add_position("MSFT", "BUY", 100, 400.0, spread_bps=2.0)
        event = _make_event(bid=99.99, ask=100.01)
        quote = _make_quote(bid=99.9925, ask=100.0075)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is None
        assert f.rejection_counts["rejected_position"] == 1

    def test_inventory_cap_rejected(self):
        """If adding position would breach ±6 bps cap, reject."""
        f, tracker = _make_filter(portfolio_value=200_000.0)
        # Add existing positions that saturate the cap in SELL direction
        tracker.add_position("NVDA", "SELL", 100, 500.0, spread_bps=4.0)
        tracker.add_position("TSLA", "SELL", 100, 200.0, spread_bps=3.0)
        # Net = -4.0 + -3.0 = -7.0 bps (already > 6)

        event = _make_event(bid=99.99, ask=100.01)
        # Competitive spread
        quote = _make_quote(bid=99.9925, ask=100.0075)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        # imbalance > 0 -> side = SELL -> would push more negative
        signal = f.evaluate(event, quote)
        assert signal is None

    def test_side_determination_positive_imbalance(self):
        """Positive imbalance (buy pressure) -> SELL to provide liquidity."""
        f, _ = _make_filter()
        event = _make_event(imbalance=0.9, bid=99.99, ask=100.01)
        # Competitive: spread < baseline (0.015 < 0.02 -> ratio 0.75)
        quote = _make_quote(bid=99.9925, ask=100.0075)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is not None
        assert signal.side == "SELL"
        assert signal.limit_price == 100.0075

    def test_side_determination_negative_imbalance(self):
        """Negative imbalance (sell pressure) -> BUY to provide liquidity."""
        f, _ = _make_filter()
        event = _make_event(imbalance=-0.9, bid=99.99, ask=100.01)
        quote = _make_quote(bid=99.9925, ask=100.0075)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        signal = f.evaluate(event, quote)
        assert signal is not None
        assert signal.side == "BUY"
        assert signal.limit_price == 99.9925

    def test_nbbo_integrity_report(self):
        """NBBO integrity stats should aggregate correctly."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)
        locked_quote = _make_quote(bid=100.0, ask=100.0)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.9925, ask=100.0075,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))

        f.evaluate(event, locked_quote)
        f.evaluate(event, locked_quote)

        report = f.get_nbbo_integrity_stats()
        assert report.locked_crossed_rate > 0.0

    def test_rejection_counts_accumulate(self):
        """Multiple rejections should accumulate correctly."""
        f, _ = _make_filter()
        event = _make_event(bid=99.99, ask=100.01)

        # Dead zone rejection: spread 0.03, baseline 0.02 -> ratio 1.5
        dz_quote = _make_quote(bid=99.985, ask=100.015)
        for i in range(3):
            f.record_quote(_make_quote(bid=99.985, ask=100.015,
                                       ts_ns=event.event_timestamp_ns + i * 50_000_000))
        f.evaluate(event, dz_quote)

        # Locked rejection
        f.evaluate(event, _make_quote(bid=100.0, ask=100.0))

        counts = f.rejection_counts
        assert counts["total_events"] == 2
        assert counts["accepted"] == 0
        assert counts["rejected_deadzone"] == 1
        assert counts["rejected_nbbo"] >= 1
