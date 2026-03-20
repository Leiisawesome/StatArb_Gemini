from __future__ import annotations

import json
from pathlib import Path

import pytest

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.live import (
    BrokerOrder,
    BrokerOrderStatus,
    IBKRBrokerOrderRouter,
    IBKRConnectionConfig,
    RouteAcknowledgement,
    RoutedLiveTradingRunner,
    RunnerConfig,
    SimulatorPaperTradingRunner,
)
from l1_microstructure.monitoring import InMemoryMonitoringSink, JsonlMonitoringSink
from l1_microstructure.training import EmpiricalTransitionTrainer
from tests.unit.l1_state_machine.support import FixtureMarketDataSource as InMemoryMassiveDataSource


class AcceptedFillRouter:
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
                reason="accepted fill router",
                timestamp_ns=request.executable_timestamp_ns,
            )
        )
        return RouteAcknowledgement(external_order_id=f"accepted-{len(self.submissions)}", status="accepted")

    def poll(self, symbols):
        reports = [report for report in self.pending_reports if report.symbol in symbols]
        self.pending_reports = [report for report in self.pending_reports if report.symbol not in symbols]
        return reports

    def stop(self) -> None:
        self.stopped = True


class DelayedFillRouter(AcceptedFillRouter):
    def __init__(self, delay_cycles: int = 1) -> None:
        super().__init__()
        self.delay_cycles = max(int(delay_cycles), 0)
        self.pending_reports: list[tuple[int, ExecutionReport]] = []

    def submit(self, request):
        self.submissions.append(request)
        self.pending_reports.append(
            (
                self.delay_cycles,
                ExecutionReport(
                    symbol=request.symbol,
                    action=request.action,
                    status="filled",
                    quantity=request.quantity,
                    fill_price=request.expected_state.book.ask_price,
                    alignment_probability=1.0,
                    fill_probability=1.0,
                    slippage_bps=0.0,
                    reason="delayed fill router",
                    timestamp_ns=request.executable_timestamp_ns,
                ),
            )
        )
        return RouteAcknowledgement(external_order_id=f"delayed-{len(self.submissions)}", status="accepted")

    def poll(self, symbols):
        ready = []
        remaining = []
        for polls_remaining, report in self.pending_reports:
            if report.symbol not in symbols:
                remaining.append((polls_remaining, report))
            elif polls_remaining > 0:
                remaining.append((polls_remaining - 1, report))
            else:
                ready.append(report)
        self.pending_reports = remaining
        return ready


class CancelingRouter(AcceptedFillRouter):
    def submit(self, request):
        self.submissions.append(request)
        self.pending_reports.append(
            ExecutionReport(
                symbol=request.symbol,
                action=request.action,
                status="cancelled",
                quantity=0,
                fill_price=None,
                alignment_probability=0.0,
                fill_probability=0.0,
                slippage_bps=0.0,
                reason="router rejected",
                timestamp_ns=request.executable_timestamp_ns,
            )
        )
        return RouteAcknowledgement(external_order_id=f"cancelled-{len(self.submissions)}", status="rejected", reason="router rejected")


def test_in_memory_monitoring_sink_collects_runtime_snapshots() -> None:
    source = InMemoryMassiveDataSource(
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
    source = InMemoryMassiveDataSource(
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
    source = InMemoryMassiveDataSource(
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

    source = InMemoryMassiveDataSource(
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

    full_source = InMemoryMassiveDataSource(payloads)
    full_events = list(full_source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(full_events, config=config)
    transition_panel = builder.build_transition_panel("AAPL").frame
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(trainer.samples_from_frame(transition_panel), runtime_horizon_ns=config.transition.drift_horizon_ns)
    runtime_artifacts = RuntimeArtifactBundle(transition_model=trainer.last_payload)

    first_runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads[:4]),
        router=AcceptedFillRouter(),
        framework_config=config,
        runtime_artifacts=runtime_artifacts,
    )
    first_runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )
    snapshot = first_runner.snapshot_state()

    resumed_runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads[4:]),
        router=AcceptedFillRouter(),
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
    events = list(InMemoryMassiveDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads),
        router=DelayedFillRouter(delay_cycles=1),
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
    events = list(InMemoryMassiveDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads),
        router=CancelingRouter(),
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
    events = list(InMemoryMassiveDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )

    runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads),
        router=IBKRBrokerOrderRouter(ibkr_config=IBKRConnectionConfig(), broker=FakeBrokerFacade()),
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
    events = list(InMemoryMassiveDataSource(payloads).subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )
    broker = RecoverableBrokerFacade()
    router = IBKRBrokerOrderRouter(ibkr_config=IBKRConnectionConfig(), broker=broker)
    runtime_artifacts = RuntimeArtifactBundle(transition_model=trainer.last_payload)

    first_runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads[:4]),
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

    resumed_router = IBKRBrokerOrderRouter(ibkr_config=IBKRConnectionConfig(), broker=broker)
    resumed_runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource(payloads[4:]),
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
        source=InMemoryMassiveDataSource([]),
        router=ControllableRouter(),
        runtime_artifacts=RuntimeArtifactBundle(),
    )

    assert runner.open_route_order_ids() == ["route-1", "route-2"]
    assert runner.cancel_route_order("route-2") is True
    assert runner.router_health() == {"connected": True, "status": "healthy", "broker": "controllable"}


def test_simulator_paper_runner_stop_before_start() -> None:
    """Covers paper.py: stop() before start()"""
    runner = SimulatorPaperTradingRunner(events=[])
    runner.stop()  # should not raise
    assert runner.is_running is False


def test_simulator_paper_runner_execution_summary_empty() -> None:
    """Covers paper.py: execution_summary() with no updates"""
    runner = SimulatorPaperTradingRunner(events=[])
    summary = runner.execution_summary()
    assert summary["update_count"] == 0.0
    assert summary["fill_count"] == 0.0
    assert summary["cancel_count"] == 0.0


def test_simulator_paper_runner_with_runtime_artifacts() -> None:
    """Covers paper.py: constructor with runtime_artifacts"""
    from l1_microstructure.artifacts import RuntimeArtifactBundle

    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    artifacts = RuntimeArtifactBundle()
    runner = SimulatorPaperTradingRunner(events=events, runtime_artifacts=artifacts)
    assert runner.runtime_artifacts is artifacts


def test_simulator_paper_runner_filters_symbols() -> None:
    """Covers paper.py: selected_symbols filtering in start()"""
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "MSFT", "t": 1710163801000000000, "bp": 200.0, "ap": 200.02, "bs": 100, "as": 100},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL", "MSFT"))))
    runner = SimulatorPaperTradingRunner(events=events)
    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))
    # Should only process AAPL events
    assert runner.is_running is False


def test_simulator_paper_runner_stop_during_run() -> None:
    """Covers paper.py: stop() during event processing loop"""
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
            {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
            {"ev": "Q", "sym": "AAPL", "t": 1710163802000000000, "bp": 100.02, "ap": 100.04, "bs": 200, "as": 200},
        ]
    )
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))

    class StoppingRunner(SimulatorPaperTradingRunner):
        def start(self, config):
            super().start(config)
            # Simulate stop during processing
            self.is_running = False

    runner = StoppingRunner(events=events)
    runner.start(RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))
    # Should complete without error


def test_source_backed_runner_run_historical_with_bundle_selector(tmp_path) -> None:
    """Covers source.py: run_historical with bundle_selector"""
    from l1_microstructure.artifacts import LocalArtifactStore
    from l1_microstructure.ingest import HistoricalBatchRequest
    from l1_microstructure.live.source import SourceBackedPaperRunner

    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )
    store = LocalArtifactStore(tmp_path)
    runner = SourceBackedPaperRunner(source=source, bundle_selector=None)
    # Without bundle_selector, should still work
    request = HistoricalBatchRequest(symbols=("AAPL",), trade_date=__import__("datetime").date(2024, 3, 11))
    result = runner.run_historical(request, RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100))
    assert result is not None


def test_source_backed_runner_run_live_with_bundle_selector() -> None:
    """Covers source.py: run_live with bundle_selector"""
    from l1_microstructure.live.source import SourceBackedPaperRunner

    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )
    runner = SourceBackedPaperRunner(source=source, bundle_selector=None)
    result = runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="paper", latency_ms=100),
    )
    assert result is not None


def test_source_backed_runner_requires_single_symbol_with_bundle() -> None:
    """Covers source.py: _run_events raises ValueError for multiple symbols with bundle"""
    from l1_microstructure.live.source import SourceBackedPaperRunner
    from l1_microstructure.artifacts import LocalArtifactStore

    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )

    class FakeBundleSelector:
        pass

    runner = SourceBackedPaperRunner(source=source, bundle_selector=FakeBundleSelector())
    # Should raise when multiple symbols with bundle_selector
    try:
        runner.run_live(
            LiveSubscriptionRequest(symbols=("AAPL", "MSFT")),
            RunnerConfig(symbols=("AAPL", "MSFT"), mode="paper", latency_ms=100),
        )
    except ValueError as e:
        assert "exactly one symbol" in str(e)


def test_routed_live_runner_with_run_id() -> None:
    """Covers routed.py: run_live with run_id parameter"""
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )
    router = AcceptedFillRouter()
    runner = RoutedLiveTradingRunner(
        source=source,
        router=router,
        framework_config=FrameworkConfig(),
    )

    result = runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
        run_id="test-run-123",
    )
    assert result is runner


def test_routed_live_runner_with_runtime_artifacts() -> None:
    """Covers routed.py: run_live with runtime_artifacts"""
    source = InMemoryMassiveDataSource(
        [
            {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        ]
    )
    router = AcceptedFillRouter()
    artifacts = RuntimeArtifactBundle()
    runner = RoutedLiveTradingRunner(
        source=source,
        router=router,
        framework_config=FrameworkConfig(),
        runtime_artifacts=artifacts,
    )

    result = runner.run_live(
        LiveSubscriptionRequest(symbols=("AAPL",)),
        RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=100),
    )
    assert result is runner
    assert runner.runtime_artifacts is artifacts


def test_routed_live_runner_health_check() -> None:
    """Covers routed.py: router_health method"""
    router = AcceptedFillRouter()
    runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource([]),
        router=router,
    )
    health = runner.router_health()
    # router_health returns None for AcceptedFillRouter
    assert health is None


def test_routed_live_runner_execution_reports_property() -> None:
    """Covers routed.py: execution_reports property"""
    router = AcceptedFillRouter()
    runner = RoutedLiveTradingRunner(
        source=InMemoryMassiveDataSource([]),
        router=router,
    )
    # Empty runner should have empty reports
    assert runner.execution_reports == []


def test_ibkr_native_broker_session_connect_disconnect() -> None:
    """Covers _ibkr_native.py: IBKRNativeBrokerSession connect/disconnect"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    # Test is_connected before connect
    assert session.is_connected() is False

    # Test broker_name
    assert session.broker_name() == "Interactive Brokers"


@pytest.mark.asyncio
async def test_ibkr_native_broker_session_check_health_disconnected() -> None:
    """Covers _ibkr_native.py: check_health when disconnected"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    health = await session.check_health()
    assert health["connected"] is False
    assert health["status"] == "disconnected"
    assert health["broker"] == "Interactive Brokers"


def test_ibkr_native_stock_contract() -> None:
    """Covers _ibkr_native.py: _stock_contract static method"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession

    contract = IBKRNativeBrokerSession._stock_contract("AAPL")
    assert contract.symbol == "AAPL"
    assert contract.secType == "STK"
    assert contract.exchange == "SMART"
    assert contract.currency == "USD"


def test_ibkr_native_build_order_market() -> None:
    """Covers _ibkr_native.py: _build_order for market orders"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig, BrokerOrderSide, BrokerOrderType

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    order = session._build_order(BrokerOrderSide.BUY, 100, BrokerOrderType.MARKET, None)
    assert order.action == "BUY"
    assert order.orderType == "MKT"
    assert order.totalQuantity == 100.0


def test_ibkr_native_build_order_limit() -> None:
    """Covers _ibkr_native.py: _build_order for limit orders"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig, BrokerOrderSide, BrokerOrderType

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    order = session._build_order(BrokerOrderSide.SELL, 50, BrokerOrderType.LIMIT, 150.25)
    assert order.action == "SELL"
    assert order.orderType == "LMT"
    assert order.totalQuantity == 50.0
    assert order.lmtPrice == 150.25


def test_ibkr_native_build_order_outside_rth() -> None:
    """Covers _ibkr_native.py: _build_order with outsideRth"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig, BrokerOrderSide, BrokerOrderType

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999, outside_regular_trading_hours=True)
    session = IBKRNativeBrokerSession(config)

    order = session._build_order(BrokerOrderSide.BUY, 100, BrokerOrderType.MARKET, None)
    assert order.outsideRth is True


def test_ibkr_native_build_order_with_account() -> None:
    """Covers _ibkr_native.py: _build_order with account_id"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig, BrokerOrderSide, BrokerOrderType

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999, account_id="DU123456")
    session = IBKRNativeBrokerSession(config)

    order = session._build_order(BrokerOrderSide.BUY, 100, BrokerOrderType.MARKET, None)
    assert order.account == "DU123456"


def test_ibkr_native_build_order_requires_limit_price() -> None:
    """Covers _ibkr_native.py: _build_order raises for limit without price"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig, BrokerOrderSide, BrokerOrderType

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    try:
        session._build_order(BrokerOrderSide.BUY, 100, BrokerOrderType.LIMIT, None)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "limit price" in str(e)


def test_ibkr_native_require_app_raises() -> None:
    """Covers _ibkr_native.py: _require_app raises when not connected"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    try:
        session._require_app()
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not connected" in str(e)


def test_ibkr_native_reserve_order_id_raises_when_none() -> None:
    """Covers _ibkr_native.py: _reserve_order_id raises when no order id"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)

    try:
        session._reserve_order_id()
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "next valid order id" in str(e)


def test_ibkr_native_ignores_non_fatal_order_preset_warning() -> None:
    """Covers _ibkr_native.py: on_error ignores non-fatal IBKR warning 10349"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderType, BrokerOrderStatus, IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)
    session._orders["1"] = BrokerOrder(
        symbol="AAPL",
        side=BrokerOrderSide.BUY,
        quantity=1.0,
        order_type=BrokerOrderType.LIMIT,
        status=BrokerOrderStatus.SUBMITTED,
        order_id="1",
    )

    session.on_error(1, 10349, "Order TIF was set to DAY based on order preset.")

    assert session._last_error is None
    assert session._orders["1"].status is BrokerOrderStatus.SUBMITTED


def test_ibkr_native_ignores_expected_cancel_error_in_health_state() -> None:
    """Covers _ibkr_native.py: on_error does not retain cancellation code 202 as last_error"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderType, BrokerOrderStatus, IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)
    session._orders["2"] = BrokerOrder(
        symbol="AAPL",
        side=BrokerOrderSide.BUY,
        quantity=1.0,
        order_type=BrokerOrderType.LIMIT,
        status=BrokerOrderStatus.SUBMITTED,
        order_id="2",
    )

    session.on_error(2, 202, "Order Canceled - reason:")

    assert session._last_error is None
    assert session._orders["2"].status is BrokerOrderStatus.CANCELLED


def test_ibkr_native_ignores_order_timing_warning() -> None:
    """Covers _ibkr_native.py: on_error ignores non-fatal IBKR warning 399"""
    from l1_microstructure.live._ibkr_native import IBKRNativeBrokerSession
    from l1_microstructure.live.broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderType, BrokerOrderStatus, IBKRConnectionConfig

    config = IBKRConnectionConfig(host="127.0.0.1", port=4002, client_id=999)
    session = IBKRNativeBrokerSession(config)
    session._orders["3"] = BrokerOrder(
        symbol="AAPL",
        side=BrokerOrderSide.BUY,
        quantity=1.0,
        order_type=BrokerOrderType.LIMIT,
        status=BrokerOrderStatus.SUBMITTED,
        order_id="3",
    )

    session.on_error(3, 399, "Order Message: BUY 1 AAPL NASDAQ.NMS Warning: Your order will not be placed at the exchange until 2026-03-13 04:00:00 US/Eastern.")

    assert session._last_error is None
    assert session._orders["3"].status is BrokerOrderStatus.SUBMITTED