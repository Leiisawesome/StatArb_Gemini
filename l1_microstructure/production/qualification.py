"""Deterministic, offline safety drills for the supervised production runtime."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time_ns
from types import SimpleNamespace
from typing import Any

from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent
from l1_microstructure.execution import ExecutionSimulator
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live import RouteAcknowledgement
from l1_microstructure.monitoring import OperationalAlert
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.risk import OpenPosition
from l1_microstructure.transitions import EdgeKey

from .config import ProductionConfig
from .lifecycle import LifecycleState
from .runtime import ProductionRuntime

QUALIFICATION_SUCCESS_EXIT_CODE = 0
QUALIFICATION_FAILURE_EXIT_CODE = 2


@dataclass(frozen=True, slots=True)
class QualificationCheck:
    code: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "passed": self.passed,
            "message": self.message,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True, slots=True)
class QualificationScenarioResult:
    name: str
    checks: tuple[QualificationCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": "passed" if self.passed else "failed",
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(frozen=True, slots=True)
class ProductionQualificationReport:
    scenarios: tuple[QualificationScenarioResult, ...]
    schema_version: int = 1

    @property
    def passed(self) -> bool:
        return bool(self.scenarios) and all(scenario.passed for scenario in self.scenarios)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": "passed" if self.passed else "failed",
            "scenario_count": len(self.scenarios),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
        }


class _SilentAlertSink:
    def publish_alert(self, _alert: OperationalAlert) -> None:
        return None


class _QualificationSource:
    def load_historical(self, _request):
        return []

    def subscribe_live(self, _request):
        return []


class _QualificationRouter:
    def __init__(self, *, acknowledgement_status: str = "accepted") -> None:
        self.connected = True
        self.acknowledgement_status = acknowledgement_status
        self.positions: dict[str, dict[str, float]] = {}
        self.open_orders: list[str] = []
        self.submissions: list[Any] = []
        self.stopped = False

    def health_check(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "status": "healthy" if self.connected else "disconnected",
            "net_liquidation": 100_000.0,
        }

    def reconciliation_snapshot(self) -> dict[str, Any]:
        return {
            **self.health_check(),
            "positions": dict(self.positions),
            "open_order_ids": list(self.open_orders),
        }

    def snapshot_recovery_state(self):
        return None

    def validate_recovery_state(self, state, _symbols=None) -> None:
        if state is not None:
            raise TypeError("qualification router does not support recovery state")

    def restore_recovery_state(self, state) -> None:
        self.validate_recovery_state(state)

    def recovery_reconciliations(self) -> list[Any]:
        return []

    def open_order_ids(self) -> list[str]:
        return list(self.open_orders)

    def submit(self, request) -> RouteAcknowledgement:
        self.submissions.append(request)
        order_id = f"qualification-{len(self.submissions)}"
        return RouteAcknowledgement(
            external_order_id=order_id,
            status=self.acknowledgement_status,
            reason="qualification rejection" if self.acknowledgement_status != "accepted" else "accepted",
        )

    def poll(self, _symbols):
        return []

    def cancel(self, order_id: str) -> bool:
        if order_id in self.open_orders:
            self.open_orders.remove(order_id)
        return True

    def stop(self) -> None:
        self.stopped = True


class _QualificationMachine:
    def __init__(self) -> None:
        self.events: list[Any] = []
        self.open_positions: dict[str, OpenPosition] = {}
        self.previous_state = None
        self.risk_engine = SimpleNamespace(halted=False)

    def on_event(self, event):
        self.events.append(event)
        return None

    def ingest_execution_report(self, _report) -> None:
        return None


class _QualificationRuntime(ProductionRuntime):
    def _load_machines(self) -> None:
        self.machines = {symbol: _QualificationMachine() for symbol in self.config.symbols}


def _qualification_request():
    state = FeatureEngine().update(QuoteEvent("AAPL", time_ns(), 100.0, 100.01, 100, 100))
    if state is None:
        raise RuntimeError("qualification quote did not produce state")
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey(state.label, state.label, MicrostructureRegime.EXECUTION_FLOW),
        posterior=PosteriorEstimate(1.0, 1.0, 0.75, 0.25, 0.0, 1),
        expected_holding_time_ns=1_000_000_000,
        reason="qualification rejection",
    )
    return ExecutionSimulator().build_request(intent, state, 1)


Scenario = Callable[[Path], QualificationScenarioResult]


class ProductionQualification:
    SCENARIO_NAMES = (
        "restart_fail_closed",
        "broker_disconnect_halt",
        "stale_feed_halt",
        "order_rejection_halt",
        "flatten_timeout_halt",
    )

    def __init__(self, scenarios: Mapping[str, Scenario] | None = None) -> None:
        self._scenarios = dict(scenarios or self._default_scenarios())

    def run(self, selected: Sequence[str] | None = None) -> ProductionQualificationReport:
        names = tuple(dict.fromkeys(selected or self.SCENARIO_NAMES))
        unknown = [name for name in names if name not in self._scenarios]
        if unknown:
            raise ValueError(f"unknown qualification scenarios: {unknown}")
        results: list[QualificationScenarioResult] = []
        with TemporaryDirectory(prefix="statarb-qualification-") as temporary_directory:
            root = Path(temporary_directory)
            for name in names:
                scenario_root = root / name
                scenario_root.mkdir()
                try:
                    results.append(self._scenarios[name](scenario_root))
                except Exception as exc:
                    results.append(
                        QualificationScenarioResult(
                            name,
                            (
                                QualificationCheck(
                                    "scenario.completed",
                                    False,
                                    "qualification scenario raised an exception",
                                    {"error_type": type(exc).__name__},
                                ),
                            ),
                        )
                    )
        return ProductionQualificationReport(tuple(results))

    def _default_scenarios(self) -> Mapping[str, Scenario]:
        return {
            "restart_fail_closed": self._restart_fail_closed,
            "broker_disconnect_halt": self._broker_disconnect_halt,
            "stale_feed_halt": self._stale_feed_halt,
            "order_rejection_halt": self._order_rejection_halt,
            "flatten_timeout_halt": self._flatten_timeout_halt,
        }

    def _restart_fail_closed(self, root: Path) -> QualificationScenarioResult:
        database_path = root / "runtime.sqlite3"
        first_router = _QualificationRouter()
        first = self._runtime(database_path, first_router)
        try:
            first.start()
            first.halt("qualification restart drill")
        finally:
            first_router.stop()
            first.ledger.close()

        second_router = _QualificationRouter()
        second = self._runtime(database_path, second_router)
        try:
            restored_halted = second.lifecycle.state is LifecycleState.HALTED
            restored_alert = any(alert["code"] == "operator_kill_switch" for alert in second.recent_alerts())
            second.start()
            checks = (
                QualificationCheck("restart.lifecycle_restored", restored_halted, "halted lifecycle survives restart"),
                QualificationCheck("restart.alert_history_restored", restored_alert, "alert history survives restart"),
                QualificationCheck(
                    "restart.kill_switch_enforced",
                    second.lifecycle.state is LifecycleState.HALTED
                    and bool(second.ledger.get_state("kill_switch", False)),
                    "persistent kill switch prevents automatic restart",
                ),
                QualificationCheck(
                    "restart.no_order_submission",
                    not second_router.submissions,
                    "restart drill submits no orders",
                ),
                self._incident_check(second, "reconciliation_failed"),
            )
            return QualificationScenarioResult("restart_fail_closed", checks)
        finally:
            self._close(second)

    def _broker_disconnect_halt(self, root: Path) -> QualificationScenarioResult:
        router = _QualificationRouter()
        runtime = self._runtime(root / "runtime.sqlite3", router)
        try:
            runtime.start()
            router.connected = False
            runtime._poll_reports()
            return QualificationScenarioResult(
                "broker_disconnect_halt", self._halt_checks(runtime, "broker_disconnected")
            )
        finally:
            self._close(runtime)

    def _stale_feed_halt(self, root: Path) -> QualificationScenarioResult:
        router = _QualificationRouter()
        runtime = self._runtime(root / "runtime.sqlite3", router)
        try:
            runtime.start()
            now_ns = time_ns()
            runtime.process_event(QuoteEvent("AAPL", now_ns - 2_000_000_000, 100.0, 100.01, 100, 100))
            return QualificationScenarioResult("stale_feed_halt", self._halt_checks(runtime, "stale_market_data"))
        finally:
            self._close(runtime)

    def _order_rejection_halt(self, root: Path) -> QualificationScenarioResult:
        router = _QualificationRouter(acknowledgement_status="rejected")
        runtime = self._runtime(root / "runtime.sqlite3", router)
        try:
            runtime.start()
            runtime._route(_qualification_request())
            checks = (
                *self._halt_checks(runtime, "order_rejected"),
                QualificationCheck(
                    "order_rejection.single_submission",
                    len(router.submissions) == 1,
                    "rejected order is submitted exactly once",
                    {"submission_count": len(router.submissions)},
                ),
            )
            return QualificationScenarioResult("order_rejection_halt", checks)
        finally:
            self._close(runtime)

    def _flatten_timeout_halt(self, root: Path) -> QualificationScenarioResult:
        router = _QualificationRouter()
        runtime = self._runtime(root / "runtime.sqlite3", router)
        try:
            runtime.start()
            now_ns = time_ns()
            runtime.machines["AAPL"].open_positions["AAPL"] = OpenPosition(
                symbol="AAPL",
                side=TradeAction.BUY,
                quantity=1,
                entry_price=100.0,
                entry_timestamp_ns=now_ns,
            )
            runtime._transition(LifecycleState.FLATTENING, "qualification flatten drill")
            runtime._flatten_started_at_ns = now_ns - 2_000_000_000
            runtime._flatten_submitted_symbols = {"AAPL"}
            runtime.process_event(QuoteEvent("AAPL", now_ns, 100.0, 100.01, 100, 100))
            checks = (
                *self._halt_checks(runtime, "flatten_timeout"),
                QualificationCheck(
                    "flatten.position_unresolved",
                    "AAPL" in runtime.machines["AAPL"].open_positions,
                    "flatten timeout preserves unresolved position evidence",
                ),
            )
            return QualificationScenarioResult("flatten_timeout_halt", checks)
        finally:
            self._close(runtime)

    @staticmethod
    def _runtime(database_path: Path, router: _QualificationRouter) -> _QualificationRuntime:
        config = ProductionConfig(
            symbols=("AAPL",),
            artifact_root=database_path.parent / "artifacts",
            promoted_run_ids={"AAPL": "qualification-v1"},
            database_path=database_path,
            event_stale_after_seconds=1.0,
            warmup_seconds=0.0,
            flatten_timeout_seconds=1.0,
        )
        return _QualificationRuntime(
            config,
            source=_QualificationSource(),
            router=router,
            alert_sink=_SilentAlertSink(),
        )

    @classmethod
    def _halt_checks(cls, runtime: ProductionRuntime, alert_code: str) -> tuple[QualificationCheck, ...]:
        return (
            QualificationCheck(
                f"{alert_code}.lifecycle_halted",
                runtime.lifecycle.state is LifecycleState.HALTED,
                "runtime enters the halted lifecycle",
            ),
            QualificationCheck(
                f"{alert_code}.typed_alert",
                any(alert["code"] == alert_code for alert in runtime.recent_alerts()),
                "runtime emits the expected typed alert",
            ),
            cls._incident_check(runtime, alert_code),
        )

    @staticmethod
    def _incident_check(runtime: ProductionRuntime, alert_code: str) -> QualificationCheck:
        incidents = runtime.ledger.recent_events(100, category="incident", event_type="runtime_halted")
        recorded = any((event["payload"].get("alert") or {}).get("code") == alert_code for event in incidents)
        return QualificationCheck(
            f"{alert_code}.incident_recorded",
            recorded,
            "halt incident is durably recorded",
        )

    @staticmethod
    def _close(runtime: ProductionRuntime) -> None:
        try:
            runtime.stop()
        finally:
            runtime.ledger.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic offline production safety drills")
    parser.add_argument(
        "--scenario",
        action="append",
        choices=ProductionQualification.SCENARIO_NAMES,
        help="Run only the selected scenario; repeat to select multiple scenarios",
    )
    args = parser.parse_args(argv)
    try:
        report = ProductionQualification().run(args.scenario)
    except Exception as exc:
        report = ProductionQualificationReport(
            (
                QualificationScenarioResult(
                    "qualification_runtime",
                    (
                        QualificationCheck(
                            "qualification.completed",
                            False,
                            "qualification harness failed",
                            {"error_type": type(exc).__name__},
                        ),
                    ),
                ),
            )
        )
    print(json.dumps(report.to_dict(), sort_keys=True))
    return QUALIFICATION_SUCCESS_EXIT_CODE if report.passed else QUALIFICATION_FAILURE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
