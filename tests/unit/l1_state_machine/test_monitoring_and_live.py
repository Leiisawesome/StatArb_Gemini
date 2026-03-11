from __future__ import annotations

import json
from pathlib import Path

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.ingest import InMemoryPolygonDataSource, LiveSubscriptionRequest
from l1_microstructure.live import (
    BrokerBackedOrderRouter,
    BrokerOrder,
    BrokerOrderStatus,
    ImmediateFillOrderRouter,
    LatencyBufferedOrderRouter,
    RejectingOrderRouter,
    RouteAcknowledgement,
    RoutedLiveTradingRunner,
    RunnerConfig,
    SimulatorPaperTradingRunner,
)
from l1_microstructure.monitoring import InMemoryMonitoringSink, JsonlMonitoringSink
from l1_microstructure.training import EmpiricalTransitionTrainer


def test_in_memory_monitoring_sink_collects_runtime_snapshots() -> None:
    source = InMemoryPolygonDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
            {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    sink = InMemoryMonitoringSink()
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0

    runner = SimulatorPaperTradingRunner(events=events, framework_config=config, monitoring_sink=sink)
    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))

    frame = runner.monitoring_frame()
    assert not frame.empty
    assert "state_label" in frame.columns
    assert "edge_activation_count" in frame.columns


def test_jsonl_monitoring_sink_writes_snapshots(tmp_path) -> None:
    source = InMemoryPolygonDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    path = Path(tmp_path) / "runtime.jsonl"
    sink = JsonlMonitoringSink(path)
    runner = SimulatorPaperTradingRunner(events=events, monitoring_sink=InMemoryMonitoringSink())

    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))
    for snapshot in runner.monitoring_sink.snapshots:
        sink.publish(snapshot)

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    first_record = json.loads(lines[0])
    assert first_record["state_label"]
    assert "metadata" in first_record


def test_simulator_paper_runner_produces_update_and_execution_summary() -> None:
    source = InMemoryPolygonDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
            {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
            {"ev": "T", "sym": "AAPL", "t": 1710163805000000000, "p": 100.04, "s": 500, "side": "sell"},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    runner = SimulatorPaperTradingRunner(events=events, framework_config=config)

    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))
    summary = runner.execution_summary()

    assert summary["update_count"] > 0.0
    assert summary["fill_count"] >= 0.0


def test_routed_live_runner_submits_requests_and_ingests_external_reports() -> None:
    class FakeRouter:
        def __init__(self) -> None:
            self.submissions = []
            self.pending_reports: list[ExecutionReport] = []
            self.stopped = False

        def submit(self, request):
            self.submissions.append(request)
            self.pending_reports.append(
                ExecutionReport(
                    symbol=request.symbol,
                    action=request.action,
                    status="filled",
                    quantity=request.quantity,
                    fill_price=request.expected_state.book.ask_price,
                    alignment_probability=1.0,
                    fill_probability=1.0,
                    slippage_bps=0.0,
                    reason="fake external fill",
                    timestamp_ns=request.executable_timestamp_ns,
                )
            )
            return RouteAcknowledgement(external_order_id=f"fake-{len(self.submissions)}", status="accepted")

        def poll(self, symbols):
            reports = [report for report in self.pending_reports if report.symbol in symbols]
            self.pending_reports = [report for report in self.pending_reports if report.symbol not in symbols]
            return reports

        def stop(self) -> None:
            self.stopped = True

    source = InMemoryPolygonDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
            {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
            {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
            {"ev": "T", "sym": "AAPL", "t": 1710163805000000000, "p": 100.04, "s": 500, "side": "sell"},
            {"ev": "Q", "sym": "AAPL", "t": 1710163807000000000, "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
        ]
    )
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    transition_panel = builder.build_transition_panel("AAPL").frame
    trainer = EmpiricalTransitionTrainer()
    transition_samples = trainer.samples_from_frame(transition_panel)
    trainer.fit(transition_samples, runtime_horizon_ns=config.transition.drift_horizon_ns)
    router = FakeRouter()
    runner = RoutedLiveTradingRunner(
        source=source,
        router=router,
        framework_config=config,
        runtime_artifacts=RuntimeArtifactBundle(transition_model=trainer.last_payload),
    )

    result = runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )

    summary = result.execution_summary()
    assert router.submissions
    assert summary["route_submission_count"] >= 1.0
    assert summary["fill_count"] >= 1.0
    assert result.monitoring_frame().shape[0] > 0

    result.stop()
    assert router.stopped is True


def test_routed_live_runner_can_resume_from_recovery_snapshot() -> None:
    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "T", "sym": "AAPL", "t": 1710163805000000000, "p": 100.04, "s": 500, "side": "sell"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163807000000000, "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
        {"ev": "T", "sym": "AAPL", "t": 1710163808000000000, "p": 100.08, "s": 350, "side": "buy"},
    ]
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0

    full_source = InMemoryPolygonDataSource(payloads)
    full_events = list(full_source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(full_events, config=config)
    transition_panel = builder.build_transition_panel("AAPL").frame
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(trainer.samples_from_frame(transition_panel), runtime_horizon_ns=config.transition.drift_horizon_ns)
    runtime_artifacts = RuntimeArtifactBundle(transition_model=trainer.last_payload)

    first_runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads[:4]),
        router=ImmediateFillOrderRouter(),
        framework_config=config,
        runtime_artifacts=runtime_artifacts,
    )
    first_runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )
    snapshot = first_runner.snapshot_state()

    resumed_runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads[4:]),
        router=ImmediateFillOrderRouter(),
        framework_config=config,
    )
    resumed_runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
        recovery_snapshot=snapshot,
    )

    assert resumed_runner.execution_summary()["route_submission_count"] >= first_runner.execution_summary()["route_submission_count"]
    assert len(resumed_runner.execution_reports) >= len(snapshot.execution_reports)
    assert resumed_runner.machine is not None
    assert resumed_runner.machine.execution_history


def test_routed_live_runner_supports_latency_buffered_router_adapter() -> None:
    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "Q", "sym": "AAPL", "t": 1710163805000000000, "bp": 100.05, "ap": 100.07, "bs": 240, "as": 120},
    ]
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    events = list(InMemoryPolygonDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads),
        router=LatencyBufferedOrderRouter(poll_delay_cycles=1),
        framework_config=config,
        runtime_artifacts=RuntimeArtifactBundle(transition_model=trainer.last_payload),
    )
    runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )

    summary = runner.execution_summary()
    assert summary["route_submission_count"] >= 1.0
    assert summary["fill_count"] >= 1.0


def test_routed_live_runner_handles_cancelled_router_reports() -> None:
    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
    ]
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    events = list(InMemoryPolygonDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads),
        router=RejectingOrderRouter(),
        framework_config=config,
        runtime_artifacts=RuntimeArtifactBundle(transition_model=trainer.last_payload),
    )
    runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )

    summary = runner.execution_summary()
    assert summary["route_submission_count"] >= 1.0
    assert summary["cancel_count"] >= 1.0


def test_routed_live_runner_reconciles_broker_backed_partial_fill_and_cancel() -> None:
    class FakeBrokerFacade:
        def __init__(self) -> None:
            self.connected = False
            self.orders: dict[str, object] = {}
            self.poll_count = 0
            self.cancelled_order_ids: list[str] = []

        async def connect(self) -> bool:
            self.connected = True
            return True

        async def disconnect(self) -> None:
            self.connected = False

        def is_connected(self) -> bool:
            return self.connected

        async def submit_order(self, symbol, quantity, side, order_type, limit_price=None):
            order = BrokerOrder(symbol=symbol, side=side, quantity=quantity, order_type=order_type, price=limit_price, status=BrokerOrderStatus.SUBMITTED)
            self.orders[order.order_id] = order
            return order

        async def get_order(self, order_id: str):
            self.poll_count += 1
            order = self.orders[order_id]
            if self.poll_count == 1:
                order.status = BrokerOrderStatus.PARTIAL_FILLED
                order.filled_quantity = max(float(order.quantity) / 2.0, 1.0)
                order.average_price = 100.03
            else:
                order.status = BrokerOrderStatus.CANCELLED
            return order

        async def cancel_order(self, order_id: str) -> bool:
            self.cancelled_order_ids.append(order_id)
            return True

        def broker_name(self) -> str:
            return "fake-broker"

    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "Q", "sym": "AAPL", "t": 1710163805000000000, "bp": 100.05, "ap": 100.07, "bs": 220, "as": 120},
    ]
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    events = list(InMemoryPolygonDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads),
        router=BrokerBackedOrderRouter(broker=FakeBrokerFacade()),
        framework_config=config,
        runtime_artifacts=RuntimeArtifactBundle(transition_model=trainer.last_payload),
    )
    runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )

    statuses = [report.status for report in runner.execution_reports]
    assert "filled" in statuses
    assert "cancelled" in statuses
    summary = runner.execution_summary()
    assert summary["fill_count"] >= 1.0
    assert summary["cancel_count"] >= 1.0


def test_routed_live_runner_can_resume_with_open_broker_backed_order() -> None:
    class RecoverableBrokerFacade:
        def __init__(self) -> None:
            self.connected = False
            self.orders: dict[str, object] = {}
            self.order_poll_counts: dict[str, int] = {}

        async def connect(self) -> bool:
            self.connected = True
            return True

        async def disconnect(self) -> None:
            self.connected = False

        def is_connected(self) -> bool:
            return self.connected

        async def submit_order(self, symbol, quantity, side, order_type, limit_price=None):
            order = BrokerOrder(symbol=symbol, side=side, quantity=quantity, order_type=order_type, price=limit_price, status=BrokerOrderStatus.SUBMITTED)
            self.orders[order.order_id] = order
            return order

        async def get_order(self, order_id: str):
            poll_count = self.order_poll_counts.get(order_id, 0) + 1
            self.order_poll_counts[order_id] = poll_count
            order = self.orders[order_id]
            if poll_count <= 2:
                order.status = BrokerOrderStatus.SUBMITTED
            elif poll_count <= 4:
                order.status = BrokerOrderStatus.PARTIAL_FILLED
                order.filled_quantity = max(float(order.quantity) / 2.0, 1.0)
                order.average_price = 100.03
            elif poll_count >= 5:
                order.status = BrokerOrderStatus.FILLED
                order.filled_quantity = float(order.quantity)
                order.average_price = 100.04
            return order

        async def get_orders(self, status: str = "open"):
            if status != "open":
                return list(self.orders.values())
            return [
                order
                for order in self.orders.values()
                if order.status not in {BrokerOrderStatus.FILLED, BrokerOrderStatus.CANCELLED, BrokerOrderStatus.REJECTED}
            ]

        async def cancel_order(self, order_id: str) -> bool:
            return True

        def broker_name(self) -> str:
            return "recoverable-broker"

    payloads = [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "Q", "sym": "AAPL", "t": 1710163805000000000, "bp": 100.05, "ap": 100.07, "bs": 220, "as": 120},
        {"ev": "Q", "sym": "AAPL", "t": 1710163806000000000, "bp": 100.06, "ap": 100.08, "bs": 240, "as": 140},
        {"ev": "Q", "sym": "AAPL", "t": 1710163807000000000, "bp": 100.07, "ap": 100.09, "bs": 260, "as": 160},
        {"ev": "Q", "sym": "AAPL", "t": 1710163808000000000, "bp": 100.08, "ap": 100.10, "bs": 280, "as": 180},
    ]
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    events = list(InMemoryPolygonDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )
    broker = RecoverableBrokerFacade()
    router = BrokerBackedOrderRouter(broker=broker)
    runtime_artifacts = RuntimeArtifactBundle(transition_model=trainer.last_payload)

    first_runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads[:4]),
        router=router,
        framework_config=config,
        runtime_artifacts=runtime_artifacts,
    )
    first_runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )
    snapshot = first_runner.snapshot_state()
    open_order_ids_before_resume = set(first_runner.open_route_order_ids())

    assert open_order_ids_before_resume
    assert snapshot.router_recovery_state is not None

    resumed_router = BrokerBackedOrderRouter(broker=broker)
    resumed_runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource(payloads[4:]),
        router=resumed_router,
        framework_config=config,
        runtime_artifacts=runtime_artifacts,
    )
    resumed_runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
        recovery_snapshot=snapshot,
    )

    statuses = [report.status for report in resumed_runner.execution_reports]
    assert "filled" in statuses
    assert open_order_ids_before_resume.isdisjoint(resumed_runner.open_route_order_ids())


def test_routed_live_runner_exposes_router_controls() -> None:
    class ControllableRouter:
        def __init__(self) -> None:
            self.cancelled: list[str] = []

        def submit(self, request):
            return RouteAcknowledgement(external_order_id="ignored", status="accepted")

        def poll(self, symbols):
            return []

        def stop(self) -> None:
            return None

        def open_order_ids(self) -> list[str]:
            return ["route-1", "route-2"]

        def cancel(self, order_id: str) -> bool:
            self.cancelled.append(order_id)
            return True

        def health_check(self) -> dict[str, object]:
            return {"connected": True, "status": "healthy", "broker": "controllable"}

    runner = RoutedLiveTradingRunner(
        source=InMemoryPolygonDataSource([]),
        router=ControllableRouter(),
        runtime_artifacts=RuntimeArtifactBundle(),
    )

    assert runner.open_route_order_ids() == ["route-1", "route-2"]
    assert runner.cancel_route_order("route-2") is True
    assert runner.router_health() == {"connected": True, "status": "healthy", "broker": "controllable"}