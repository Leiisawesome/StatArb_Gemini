from __future__ import annotations

import time
from pathlib import Path

import pytest
from dotenv import dotenv_values

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.config import FrameworkConfig
from l1_microstructure.datasets import PipelineTransitionDatasetBuilder
from l1_microstructure.ingest import LiveSubscriptionRequest
from l1_microstructure.live import IBKRBrokerOrderRouter, RoutedLiveTradingRunner, RunnerConfig
from l1_microstructure.monitoring import RuntimeMonitor
from l1_microstructure.training import EmpiricalTransitionTrainer
from tests.unit.l1_state_machine.support import FixtureMarketDataSource


pytestmark = [pytest.mark.integration, pytest.mark.external]


def _payloads() -> list[dict[str, object]]:
    return [
        {"ev": "Q", "sym": "AAPL", "t": 1710163800000000000, "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": 1710163801000000000, "bp": 100.01, "ap": 100.02, "bs": 400, "as": 50},
        {"ev": "T", "sym": "AAPL", "t": 1710163802000000000, "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163804000000000, "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "T", "sym": "AAPL", "t": 1710163805000000000, "p": 100.04, "s": 500, "side": "sell"},
        {"ev": "Q", "sym": "AAPL", "t": 1710163807000000000, "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
        {"ev": "T", "sym": "AAPL", "t": 1710163808000000000, "p": 100.08, "s": 350, "side": "buy"},
    ]


def _framework_config() -> FrameworkConfig:
    config = FrameworkConfig()
    config.transition.mahalanobis_threshold = 0.0
    config.transition.min_edge_observations = 1
    config.transition.min_edge_training_sessions = 0
    config.transition.min_directional_consensus = 0.0
    config.transition.min_cross_session_hit_rate = 0.0
    config.transition.min_cross_session_hit_consensus = 0.0
    config.decision.min_alpha_score = 0.0
    config.decision.entry_probability_threshold = 0.5
    config.decision.transaction_cost_bps = 0.0
    config.decision.risk_premium_bps = 0.0
    config.risk.max_position_fraction = 0.0002
    config.risk.confidence_size_floor = 1.0
    return config


class _StopAfterFirstOrderSource(FixtureMarketDataSource):
    def __init__(self, payloads, router: IBKRBrokerOrderRouter):
        super().__init__(payloads)
        self.router = router

    def subscribe_live(self, request):
        for event in super().subscribe_live(request):
            if self.router.open_order_ids():
                break
            yield event


def _runtime_artifacts(config: FrameworkConfig) -> RuntimeArtifactBundle:
    source = FixtureMarketDataSource(_payloads())
    events = list(source.subscribe_live(LiveSubscriptionRequest(symbols=("AAPL",))))
    builder = PipelineTransitionDatasetBuilder(events, config=config)
    trainer = EmpiricalTransitionTrainer()
    trainer.fit(
        trainer.samples_from_frame(builder.build_transition_panel("AAPL").frame),
        runtime_horizon_ns=config.transition.drift_horizon_ns,
    )
    return RuntimeArtifactBundle(transition_model=trainer.last_payload)


def _isolated_broker_env_file(tmp_path: Path) -> str:
    values = {key: str(value) for key, value in dotenv_values("broker.paper.env").items() if value is not None}
    values["IBKR_CLIENT_ID"] = "91313"
    env_file = tmp_path / "ibkr_routed_live_smoke.env"
    env_file.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
    return str(env_file)


def test_ibkr_router_can_drive_bounded_routed_live_cancel_cycle(tmp_path: Path) -> None:
    config = _framework_config()
    router = None
    runner = None
    try:
        try:
            router = IBKRBrokerOrderRouter.from_env(
                _isolated_broker_env_file(tmp_path),
                prefer_limit_orders=True,
                limit_price_offset_bps=-10.0,
            )
        except Exception as exc:
            pytest.skip(f"IBKR routed-live smoke unavailable: {exc}")

        health = router.health_check()
        if not health.get("connected"):
            pytest.skip(f"IBKR routed-live smoke requires a healthy broker connection: {health}")

        runner = RoutedLiveTradingRunner(
            source=_StopAfterFirstOrderSource(_payloads(), router),
            router=router,
            framework_config=config,
            runtime_artifacts=_runtime_artifacts(config),
        )
        result = runner.run_live(
            LiveSubscriptionRequest(symbols=("AAPL",)),
            RunnerConfig(symbols=("AAPL",), mode="live", latency_ms=config.execution.latency_ms),
        )

        assert result.route_acknowledgements
        assert len(result.route_acknowledgements) == 1
        assert any(ack.status == "accepted" for ack in result.route_acknowledgements)
        assert all(
            request.quantity == 1
            for update in result.updates
            for request in update.submitted_requests
        )

        open_order_ids = result.open_route_order_ids()
        assert open_order_ids, "expected at least one open routed IBKR order to cancel"
        for order_id in open_order_ids:
            assert result.cancel_route_order(order_id) is True

        if result.machine is not None:
            monitor = RuntimeMonitor(result.monitoring_sink)
            for _ in range(8):
                time.sleep(0.5)
                result._ingest_router_reports(result.machine, ("AAPL",), monitor)
                if not result.open_route_order_ids():
                    break

        assert any(report.status == "cancelled" for report in result.execution_reports)
        final_health = result.router_health()
        assert final_health is not None
        assert final_health["connected"] is True
        assert final_health["open_order_count"] == 0
    finally:
        if runner is not None:
            runner.stop()
        elif router is not None:
            router.stop()
