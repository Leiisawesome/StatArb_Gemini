from __future__ import annotations

import pytest

from l1_microstructure.events import BookSnapshot
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.transparent import MultiHorizonOutcomeTracker


def _state(timestamp_ns: int, price: float, *, symbol: str = "AAPL") -> ObservedState:
    return ObservedState(
        symbol=symbol,
        timestamp_ns=timestamp_ns,
        book=BookSnapshot(symbol, timestamp_ns, price - 0.01, price + 0.01, 100, 100),
        spread_norm=1.0,
        quote_pressure=0.0,
        trade_pressure=0.0,
        flicker_intensity=4.0,
        realized_volatility=0.001,
        spread_state=SpreadState.NORMAL,
        quote_state=PressureState.NEUTRAL,
        trade_state=PressureState.NEUTRAL,
        flicker_state=FlickerState.COMPETITIVE,
        volatility_state=VolatilityState.NORMAL,
    )


def test_multi_horizon_tracker_resolves_each_horizon_at_first_later_state() -> None:
    tracker = MultiHorizonOutcomeTracker((3, 15, 60))
    tracker.schedule(
        state=_state(100, 100.0),
        from_state="a",
        to_state="b",
        regime="flow",
        holding_time_ns=7,
    )

    assert tracker.resolve(_state(102, 101.0)) == ()
    short = tracker.resolve(_state(104, 101.0))
    medium = tracker.resolve(_state(116, 102.0))
    long = tracker.resolve(_state(170, 103.0))

    assert [item.horizon_ns for item in short + medium + long] == [3, 15, 60]
    assert short[0].target_timestamp_ns == 103
    assert short[0].end_timestamp_ns == 104
    assert short[0].realized_drift_bps == pytest.approx(100.0)
    assert tracker.pending_count == 0


def test_multi_horizon_tracker_does_not_cross_symbols_and_restores_exactly() -> None:
    tracker = MultiHorizonOutcomeTracker((3, 15))
    tracker.schedule(
        state=_state(100, 100.0),
        from_state="a",
        to_state="b",
        regime="flow",
        holding_time_ns=7,
    )
    restored = MultiHorizonOutcomeTracker.restore(tracker.snapshot())

    assert restored.resolve(_state(120, 110.0, symbol="MSFT")) == ()
    resolved = restored.resolve(_state(120, 101.0))
    assert len(resolved) == 2
    assert [item.sequence for item in resolved] == [0, 1]


def test_multi_horizon_recovery_rejects_sequence_collision() -> None:
    tracker = MultiHorizonOutcomeTracker((3,))
    tracker.schedule(
        state=_state(100, 100.0),
        from_state="a",
        to_state="b",
        regime="flow",
        holding_time_ns=7,
    )
    payload = tracker.snapshot()
    payload["next_sequence"] = 0

    with pytest.raises(ValueError, match="next sequence"):
        MultiHorizonOutcomeTracker.restore(payload)


def test_multi_horizon_recovery_rejects_duplicate_pending_sequences() -> None:
    tracker = MultiHorizonOutcomeTracker((3,))
    tracker.schedule(
        state=_state(100, 100.0),
        from_state="a",
        to_state="b",
        regime="flow",
        holding_time_ns=7,
    )
    payload = tracker.snapshot()
    payload["pending"].append(dict(payload["pending"][0]))

    with pytest.raises(ValueError, match="duplicate"):
        MultiHorizonOutcomeTracker.restore(payload)


def test_multi_horizon_tracker_fails_closed_at_pending_memory_bound() -> None:
    tracker = MultiHorizonOutcomeTracker((3, 15), max_pending_outcomes=2)
    tracker.schedule(
        state=_state(100, 100.0),
        from_state="a",
        to_state="b",
        regime="flow",
        holding_time_ns=7,
    )

    with pytest.raises(OverflowError, match="bound"):
        tracker.schedule(
            state=_state(101, 100.0),
            from_state="b",
            to_state="c",
            regime="flow",
            holding_time_ns=1,
        )
