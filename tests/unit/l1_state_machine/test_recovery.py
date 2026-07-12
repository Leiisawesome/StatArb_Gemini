from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.events import QuoteEvent
from l1_microstructure.pipeline import L1MicrostructureStateMachine
from l1_microstructure.recovery import (
    RECOVERY_SNAPSHOT_VERSION,
    FeatureRecoveryState,
    RegimeRecoveryState,
    RiskRecoveryState,
    TransitionRecoveryState,
)


def _quote(symbol: str, timestamp_ns: int, bid: float, ask: float, bid_size: int, ask_size: int) -> QuoteEvent:
    return QuoteEvent(symbol, timestamp_ns, bid, ask, bid_size, ask_size)


def _machine_with_state() -> L1MicrostructureStateMachine:
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    machine = L1MicrostructureStateMachine(config)
    machine.on_event(_quote("AAPL", 1_000_000_000, 100.0, 100.02, 100, 100))
    machine.on_event(_quote("AAPL", 2_000_000_000, 100.01, 100.03, 300, 50))
    return machine


def test_typed_recovery_snapshot_round_trips_and_resumes() -> None:
    original = _machine_with_state()
    snapshot = original.snapshot_state()

    assert snapshot.version == RECOVERY_SNAPSHOT_VERSION
    assert isinstance(snapshot.risk_state, RiskRecoveryState)
    assert isinstance(snapshot.feature_state, FeatureRecoveryState)
    assert isinstance(snapshot.regime_state, RegimeRecoveryState)
    assert isinstance(snapshot.transition_state, TransitionRecoveryState)

    restored = L1MicrostructureStateMachine(original.config)
    restored.restore_state(snapshot)

    assert restored.symbol == original.symbol
    assert restored.previous_state == original.previous_state
    assert restored.risk_engine.trade_count == original.risk_engine.trade_count
    assert list(restored.feature_engine.quote_history) == list(original.feature_engine.quote_history)
    assert restored.transition_kernel.observation_index == original.transition_kernel.observation_index

    next_event = _quote("AAPL", 3_000_000_000, 100.04, 100.06, 50, 300)
    original_update = original.on_event(next_event)
    restored_update = restored.on_event(next_event)

    assert original_update is not None
    assert restored_update is not None
    assert restored_update.state == original_update.state
    assert restored_update.regime == original_update.regime
    assert restored_update.transition_edge == original_update.transition_edge


def test_recovery_rejects_unsupported_version_before_mutation() -> None:
    snapshot = replace(_machine_with_state().snapshot_state(), version=RECOVERY_SNAPSHOT_VERSION + 1)
    target = L1MicrostructureStateMachine()

    with pytest.raises(ValueError, match="unsupported recovery snapshot version"):
        target.restore_state(snapshot)

    assert target.symbol is None
    assert target.previous_state is None


def test_recovery_rejects_symbol_mismatch() -> None:
    snapshot = _machine_with_state().snapshot_state()
    target = L1MicrostructureStateMachine()
    target.on_event(_quote("MSFT", 1_000_000_000, 200.0, 200.02, 100, 100))

    with pytest.raises(ValueError, match="does not match state machine symbol"):
        target.restore_state(snapshot)

    assert target.symbol == "MSFT"


def test_recovery_rejects_corrupted_risk_state() -> None:
    snapshot = _machine_with_state().snapshot_state()
    corrupted = replace(snapshot, risk_state=replace(snapshot.risk_state, starting_equity=-1.0))

    with pytest.raises(ValueError, match="invalid risk state"):
        L1MicrostructureStateMachine().restore_state(corrupted)

    wrong_type = replace(snapshot, risk_state={})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="risk state has an invalid type"):
        L1MicrostructureStateMachine().restore_state(wrong_type)


def test_recovery_rejects_malformed_transition_increment() -> None:
    snapshot = _machine_with_state().snapshot_state()
    corrupted = replace(
        snapshot,
        transition_state=replace(snapshot.transition_state, increment_history=[np.array([1.0, 2.0])]),
    )

    with pytest.raises(ValueError, match="invalid transition increment"):
        L1MicrostructureStateMachine().restore_state(corrupted)
