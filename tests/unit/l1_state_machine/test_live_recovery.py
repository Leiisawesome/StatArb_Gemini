from __future__ import annotations

from dataclasses import replace

import pytest

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.events import QuoteEvent
from l1_microstructure.ingest.interfaces import LiveSubscriptionRequest
from l1_microstructure.live.interfaces import RunnerConfig
from l1_microstructure.live.recovery import RoutedLiveRecoveryCodec, RoutedLiveRecoverySnapshot
from l1_microstructure.live.routed import RoutedLiveTradingRunner
from l1_microstructure.pipeline import L1MicrostructureStateMachine


def _snapshot() -> tuple[L1MicrostructureStateMachine, RoutedLiveRecoverySnapshot]:
    machine = L1MicrostructureStateMachine(route_orders_externally=True)
    machine.on_event(
        QuoteEvent(
            symbol="AAPL",
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            ask_price=100.02,
            bid_size=300,
            ask_size=300,
        )
    )
    snapshot = RoutedLiveRecoverySnapshot(
        machine_snapshot=machine.snapshot_state(),
        runtime_artifacts=RuntimeArtifactBundle(),
        route_acknowledgements=[],
        execution_reports=[],
        symbols=("AAPL",),
    )
    return L1MicrostructureStateMachine(route_orders_externally=True), snapshot


def test_routed_recovery_rejects_unsupported_version_before_router_validation() -> None:
    machine, snapshot = _snapshot()
    router_validation_calls: list[object] = []

    with pytest.raises(ValueError, match="unsupported routed-live recovery version"):
        RoutedLiveRecoveryCodec.validate(
            machine,
            replace(snapshot, version=999),
            ("AAPL",),
            lambda state, _symbols: router_validation_calls.append(state),
        )

    assert router_validation_calls == []
    assert machine.symbol is None


def test_routed_recovery_rejects_requested_symbol_mismatch() -> None:
    machine, snapshot = _snapshot()

    with pytest.raises(ValueError, match="do not match requested symbols"):
        RoutedLiveRecoveryCodec.validate(machine, snapshot, ("MSFT",), lambda _state, _symbols: None)

    assert machine.symbol is None


class _EmptySource:
    def subscribe_live(self, _request):
        return iter(())


class _RecoveryTrackingRouter:
    def __init__(self, *, reject_state: bool = False) -> None:
        self.reject_state = reject_state
        self.restore_calls = 0

    def submit(self, _request):  # pragma: no cover - empty source never submits
        raise AssertionError("unexpected submission")

    def poll(self, _symbols):
        return []

    def stop(self):
        return None

    def validate_recovery_state(self, _state, _symbols):
        if self.reject_state:
            raise ValueError("invalid router recovery state")

    def restore_recovery_state(self, _state):
        self.restore_calls += 1


def test_routed_runner_invalid_machine_snapshot_is_failure_atomic() -> None:
    _, snapshot = _snapshot()
    invalid_snapshot = replace(snapshot, machine_snapshot=replace(snapshot.machine_snapshot, version=999))
    router = _RecoveryTrackingRouter()
    runner = RoutedLiveTradingRunner(source=_EmptySource(), router=router)

    with pytest.raises(ValueError, match="unsupported recovery snapshot version"):
        runner.run_live(
            LiveSubscriptionRequest(symbols=("AAPL",)),
            RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=0),
            recovery_snapshot=invalid_snapshot,
        )

    assert router.restore_calls == 0
    assert runner.machine is None
    assert runner.is_running is False


def test_routed_runner_invalid_router_snapshot_is_failure_atomic() -> None:
    _, snapshot = _snapshot()
    router = _RecoveryTrackingRouter(reject_state=True)
    runner = RoutedLiveTradingRunner(source=_EmptySource(), router=router)

    with pytest.raises(ValueError, match="invalid router recovery state"):
        runner.run_live(
            LiveSubscriptionRequest(symbols=("AAPL",)),
            RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=0),
            recovery_snapshot=replace(snapshot, router_recovery_state={"corrupted": True}),
        )

    assert router.restore_calls == 0
    assert runner.machine is None
    assert runner.is_running is False
