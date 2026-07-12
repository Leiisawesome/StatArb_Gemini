"""External-routing live runner for the successor package."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from l1_microstructure.artifacts import ArtifactBundleSelector, RunQualityGate, RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.ingest.interfaces import LiveSubscriptionRequest, MarketDataSource
from l1_microstructure.monitoring import InMemoryMonitoringSink, RuntimeMonitor
from l1_microstructure.pipeline import FrameworkUpdate, L1MicrostructureStateMachine, StateMachineRecoverySnapshot

from .interfaces import OrderRouter, RouteAcknowledgement, RunnerConfig
from .execution_session import RoutedExecutionService


@dataclass(frozen=True, slots=True)
class RoutedLiveRecoverySnapshot:
    machine_snapshot: StateMachineRecoverySnapshot
    runtime_artifacts: RuntimeArtifactBundle
    route_acknowledgements: list[RouteAcknowledgement]
    execution_reports: list[ExecutionReport]
    router_recovery_state: Any | None = None


@dataclass(slots=True)
class RoutedLiveTradingRunner:
    """Lightweight embedded runner; use ProductionRuntime for operator-facing live trading."""

    source: MarketDataSource
    router: OrderRouter
    framework_config: FrameworkConfig | None = None
    monitoring_sink: InMemoryMonitoringSink | None = None
    bundle_selector: ArtifactBundleSelector | None = None
    runtime_artifacts: RuntimeArtifactBundle | None = None
    require_validation_passed: bool = False
    quality_gate: RunQualityGate | None = None
    is_running: bool = False
    machine: L1MicrostructureStateMachine | None = None
    updates: list[FrameworkUpdate] = field(default_factory=list)
    route_acknowledgements: list[RouteAcknowledgement] = field(default_factory=list)
    execution_reports: list[ExecutionReport] = field(default_factory=list)
    execution_service: RoutedExecutionService = field(init=False)

    def __post_init__(self) -> None:
        self.framework_config = self.framework_config or FrameworkConfig()
        self.monitoring_sink = self.monitoring_sink or InMemoryMonitoringSink()
        self.runtime_artifacts = self.runtime_artifacts or RuntimeArtifactBundle()
        self.execution_service = RoutedExecutionService(self.router)

    def run_live(
        self,
        request: LiveSubscriptionRequest,
        config: RunnerConfig,
        run_id: str | None = None,
        recovery_snapshot: RoutedLiveRecoverySnapshot | None = None,
    ) -> "RoutedLiveTradingRunner":
        self.is_running = True
        self.updates = []
        self.route_acknowledgements = (
            [] if recovery_snapshot is None else deepcopy(recovery_snapshot.route_acknowledgements)
        )
        self.execution_reports = [] if recovery_snapshot is None else deepcopy(recovery_snapshot.execution_reports)
        self.runtime_artifacts = (
            self._resolve_runtime_artifacts(config.symbols, run_id=run_id)
            if recovery_snapshot is None
            else recovery_snapshot.runtime_artifacts
        )
        machine = L1MicrostructureStateMachine(
            self.framework_config,
            runtime_artifacts=self.runtime_artifacts,
            route_orders_externally=True,
        )
        if recovery_snapshot is not None:
            self.execution_service.restore_recovery_state(recovery_snapshot.router_recovery_state)
            machine.restore_state(recovery_snapshot.machine_snapshot)
        self.machine = machine
        monitor = RuntimeMonitor(self.monitoring_sink)
        selected_symbols = set(config.symbols)

        if recovery_snapshot is not None:
            self._ingest_router_reports(machine, config.symbols)

        for event in self.source.subscribe_live(request):
            if not self.is_running:
                break
            self._ingest_router_reports(machine, config.symbols)
            if event.symbol not in selected_symbols:
                continue
            update = machine.on_event(event)
            if update is None:
                continue
            self.route_acknowledgements.extend(self.execution_service.submit_all(update.submitted_requests))
            self._ingest_router_reports(machine, config.symbols)
            self.updates.append(update)
            monitor.publish_update(update, machine)

        self._ingest_router_reports(machine, config.symbols)
        self.is_running = False
        return self

    def snapshot_state(self) -> RoutedLiveRecoverySnapshot:
        if self.machine is None:
            raise ValueError("cannot snapshot routed live runner before it has started")
        return RoutedLiveRecoverySnapshot(
            machine_snapshot=self.machine.snapshot_state(),
            runtime_artifacts=self.runtime_artifacts,
            route_acknowledgements=deepcopy(self.route_acknowledgements),
            execution_reports=deepcopy(self.execution_reports),
            router_recovery_state=deepcopy(self.execution_service.snapshot_recovery_state()),
        )

    def stop(self) -> None:
        self.is_running = False
        self.execution_service.stop()

    def open_route_order_ids(self) -> list[str]:
        return self.execution_service.open_order_ids()

    def cancel_route_order(self, order_id: str) -> bool:
        return self.execution_service.cancel(order_id)

    def router_health(self) -> dict[str, Any] | None:
        return self.execution_service.health()

    def monitoring_frame(self) -> pd.DataFrame:
        return self.monitoring_sink.to_frame()

    def execution_summary(self) -> dict[str, float]:
        fill_count = float(sum(1 for report in self.execution_reports if report.status == "filled"))
        cancel_count = float(sum(1 for report in self.execution_reports if report.status == "cancelled"))
        return {
            "update_count": float(len(self.updates)),
            "fill_count": fill_count,
            "cancel_count": cancel_count,
            "route_submission_count": float(len(self.route_acknowledgements)),
        }

    def _resolve_runtime_artifacts(self, symbols: tuple[str, ...], run_id: str | None) -> RuntimeArtifactBundle:
        if self.bundle_selector is None:
            return self.runtime_artifacts or RuntimeArtifactBundle()
        if len(symbols) != 1:
            raise ValueError("artifact-resolved routed live runner currently supports exactly one symbol")
        symbol = symbols[0]
        if run_id is None:
            if self.require_validation_passed:
                return self.bundle_selector.resolve_latest_passing_for_symbol(symbol, quality_gate=self.quality_gate)
            return self.bundle_selector.resolve_latest_for_symbol(symbol)
        return self.bundle_selector.resolve_by_run_id(symbol=symbol, run_id=run_id)

    def _ingest_router_reports(self, machine: L1MicrostructureStateMachine, symbols: tuple[str, ...]) -> None:
        self.execution_service.poll(
            symbols,
            consumer_for_symbol=lambda _symbol: machine,
            after_report=self.execution_reports.append,
        )
