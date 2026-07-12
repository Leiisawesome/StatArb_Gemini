from __future__ import annotations

from contextlib import contextmanager
import json
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from l1_microstructure.cli import main
from l1_microstructure.events import MarketEvent
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.features import FeatureEngine
from l1_microstructure.ingest import LiveSubscriptionRequest
from tests.unit.l1_state_machine.support import FixtureMarketDataSource


def _et_ns(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> int:
    timestamp = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo("America/New_York"))
    return int(timestamp.timestamp() * 1_000_000_000)


def _payloads() -> list[dict[str, object]]:
    return [
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 0), "bp": 100.0, "ap": 100.02, "bs": 100, "as": 100},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 1), "bp": 100.01, "ap": 100.02, "bs": 450, "as": 40},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 2), "p": 100.02, "s": 400, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 4), "bp": 100.04, "ap": 100.08, "bs": 40, "as": 300},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 5), "p": 100.05, "s": 300, "side": "buy"},
        {"ev": "Q", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 7), "bp": 100.07, "ap": 100.09, "bs": 420, "as": 60},
        {"ev": "T", "sym": "AAPL", "t": _et_ns(2024, 3, 11, 9, 30, 8), "p": 100.08, "s": 350, "side": "buy"},
        {
            "ev": "Q",
            "sym": "AAPL",
            "t": _et_ns(2024, 3, 11, 9, 30, 10),
            "bp": 100.10,
            "ap": 100.14,
            "bs": 30,
            "as": 260,
        },
    ]


def _fixture_source() -> FixtureMarketDataSource:
    return FixtureMarketDataSource(_payloads())


def _latest_state(symbol: str):
    feature_engine = FeatureEngine()
    latest_state = None
    for event in _fixture_source().subscribe_live(LiveSubscriptionRequest(symbols=(symbol,))):
        if not isinstance(event, MarketEvent):
            continue
        observed_state = feature_engine.update(event)
        if observed_state is not None and observed_state.symbol == symbol:
            latest_state = observed_state
    if latest_state is None:
        raise ValueError(f"fixture source did not produce any observable state for symbol {symbol}")
    return latest_state


@contextmanager
def _patched_cli_sources():
    with (
        patch("l1_microstructure.cli._historical_source", side_effect=lambda: _fixture_source()),
        patch("l1_microstructure.cli._live_source", side_effect=lambda: _fixture_source()),
        patch(
            "l1_microstructure.cli._latest_observed_state_from_rest", side_effect=lambda symbol: _latest_state(symbol)
        ),
    ):
        yield


def test_cli_workflow_command_runs_end_to_end(tmp_path, capsys) -> None:
    with _patched_cli_sources():
        exit_code = main(
            [
                "workflow",
                "--artifact-root",
                str(tmp_path / "artifacts"),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )

    assert exit_code == 0
    stdout = capsys.readouterr().out.strip()
    payload = json.loads(stdout)
    assert payload["symbol"] == "AAPL"
    assert payload["state_panel_rows"] > 0
    assert payload["artifact_ids"]["transition_model_id"]
    assert "validation_failures" in payload


def test_cli_paper_historical_uses_latest_artifacts(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

        exit_code = main(
            [
                "paper-historical",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )

    assert exit_code == 0
    stdout = capsys.readouterr().out.strip()
    payload = json.loads(stdout)
    assert payload["update_count"] > 0
    assert payload["monitoring_rows"] > 0
    assert payload["artifact_bundle"]["transition_model"]


def test_cli_list_runs_reports_manifests(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        workflow_payload = json.loads(capsys.readouterr().out.strip())

    exit_code = main(
        [
            "list-runs",
            "--artifact-root",
            str(artifact_root),
            "--symbol",
            "AAPL",
            "--trade-date",
            "2024-03-11",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["symbol"] == "AAPL"
    assert payload["trade_date"] == "2024-03-11"
    assert payload["run_count"] >= 1
    assert payload["runs"][0]["run_id"] == workflow_payload["run_id"]
    assert "quality_metrics" in payload["runs"][0]
    assert "mean_execution_drift_tracking_error_bps" in payload["runs"][0]["quality_metrics"]


def test_cli_list_runs_can_filter_to_passing_runs(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        workflow_payload = json.loads(capsys.readouterr().out.strip())

    exit_code = main(
        [
            "list-runs",
            "--artifact-root",
            str(artifact_root),
            "--symbol",
            "AAPL",
            "--trade-date",
            "2024-03-11",
            "--passing-only",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["passing_only"] is True
    assert payload["run_count"] >= 1
    assert payload["runs"][0]["run_id"] == workflow_payload["run_id"]


def test_cli_list_runs_can_filter_by_quality_gate(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

    permissive_exit = main(
        [
            "list-runs",
            "--artifact-root",
            str(artifact_root),
            "--symbol",
            "AAPL",
            "--passing-only",
            "--max-drift-tracking-error-bps",
            "3.5",
        ]
    )
    assert permissive_exit == 0
    permissive_payload = json.loads(capsys.readouterr().out.strip())
    assert permissive_payload["quality_gate"]["maximum_drift_tracking_error_bps"] == 3.5
    assert permissive_payload["run_count"] >= 1

    strict_exit = main(
        [
            "list-runs",
            "--artifact-root",
            str(artifact_root),
            "--symbol",
            "AAPL",
            "--passing-only",
            "--min-fill-rate",
            "0.1",
        ]
    )
    assert strict_exit == 0
    strict_payload = json.loads(capsys.readouterr().out.strip())
    assert strict_payload["run_count"] == 0


def test_cli_paper_historical_can_require_validation_passing_bundle(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

        exit_code = main(
            [
                "paper-historical",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
                "--require-validation-passed",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["update_count"] > 0
    assert payload["runtime_metadata"]["run_id"]
    assert "quality_metrics" in payload


def test_cli_paper_historical_accepts_quality_gate(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"
    with _patched_cli_sources():
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

        exit_code = main(
            [
                "paper-historical",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
                "--require-validation-passed",
                "--max-drift-tracking-error-bps",
                "3.5",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["update_count"] > 0
    assert payload["quality_metrics"]["mean_execution_drift_tracking_error_bps"] <= 3.5


def test_cli_live_routed_runs_with_ibkr_router(tmp_path, capsys) -> None:
    artifact_root = tmp_path / "artifacts"

    class FakeLiveRouter:
        def __init__(self) -> None:
            self.pending_reports: list[ExecutionReport] = []

        def submit(self, request):
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
                    reason="fake live router",
                    timestamp_ns=request.executable_timestamp_ns,
                )
            )
            return type(
                "Ack",
                (),
                {"external_order_id": "ibkr-live-1", "status": "accepted", "reason": "accepted", "metadata": {}},
            )()

        def poll(self, symbols):
            ready = [report for report in self.pending_reports if report.symbol in symbols]
            self.pending_reports = [report for report in self.pending_reports if report.symbol not in symbols]
            return ready

        def stop(self):
            return None

    with (
        _patched_cli_sources(),
        patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value=FakeLiveRouter()),
    ):
        workflow_exit = main(
            [
                "workflow",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--trade-date",
                "2024-03-11",
                "--transition-threshold",
                "0.0",
            ]
        )
        assert workflow_exit == 0
        _ = capsys.readouterr()

        exit_code = main(
            [
                "live-routed",
                "--artifact-root",
                str(artifact_root),
                "--symbol",
                "AAPL",
                "--transition-threshold",
                "0.0",
                "--broker-env-file",
                "broker.env",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["update_count"] > 0
    assert payload["artifact_bundle"]["transition_model"]
    assert "route_acknowledgement_count" in payload


def test_cli_ibkr_live_smoke_reports_router_health(capsys) -> None:
    class FakeSmokeRouter:
        def health_check(self):
            return {"connected": True, "status": "healthy", "broker": "Interactive Brokers"}

        def open_order_ids(self):
            return ["ibkr-1"]

        def stop(self):
            return None

    with patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value=FakeSmokeRouter()) as factory:
        exit_code = main(["ibkr-live-smoke", "--broker-env-file", "broker.env"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["router_type"] == "ibkr-live"
    assert payload["health"]["connected"] is True
    assert payload["open_order_ids"] == ["ibkr-1"]
    factory.assert_called_once_with("broker.env", require_paper=True)


def test_cli_lightweight_routed_runner_rejects_live_capital() -> None:
    with pytest.raises(ValueError, match="supervised trading-daemon"):
        main(
            [
                "live-routed",
                "--artifact-root",
                "unused",
                "--symbol",
                "AAPL",
                "--allow-live-broker-routing",
            ]
        )


def test_cli_ibkr_live_order_smoke_submits_and_cancels_open_route(tmp_path, capsys) -> None:
    class FakeOrderSmokeRouter:
        def __init__(self) -> None:
            self.submitted_requests = []
            self.cancelled_order_ids: list[str] = []
            self.is_open = True
            self.stop_called = False

        def submit(self, request):
            self.submitted_requests.append(request)
            return type(
                "Ack",
                (),
                {
                    "external_order_id": "ibkr-smoke-1",
                    "status": "accepted",
                    "reason": "accepted",
                    "metadata": {"adapter": "broker-backed"},
                },
            )()

        def poll(self, symbols):
            if self.cancelled_order_ids and self.is_open:
                self.is_open = False
                request = self.submitted_requests[0]
                return [
                    type(
                        "Report",
                        (),
                        {
                            "symbol": request.symbol,
                            "action": request.action,
                            "status": "cancelled",
                            "quantity": 0,
                            "fill_price": None,
                            "alignment_probability": 0.0,
                            "fill_probability": 0.0,
                            "slippage_bps": 0.0,
                            "reason": "broker order cancelled",
                            "timestamp_ns": request.executable_timestamp_ns,
                        },
                    )()
                ]
            return []

        def cancel(self, order_id: str) -> bool:
            self.cancelled_order_ids.append(order_id)
            return True

        def open_order_ids(self):
            return ["ibkr-smoke-1"] if self.is_open else []

        def health_check(self):
            return {"connected": True, "status": "healthy", "broker": "Interactive Brokers", "open_order_count": 0}

        def stop(self):
            self.stop_called = True

    fake_router = FakeOrderSmokeRouter()
    with (
        _patched_cli_sources(),
        patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value=fake_router) as factory,
    ):
        exit_code = main(
            [
                "ibkr-live-order-smoke",
                "--symbol",
                "AAPL",
                "--quantity",
                "1",
                "--broker-env-file",
                "broker.env",
                "--poll-attempts",
                "1",
                "--poll-interval-ms",
                "0",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["router_type"] == "ibkr-live"
    assert payload["acknowledgement"]["external_order_id"] == "ibkr-smoke-1"
    assert payload["cancel_attempted"] is True
    assert payload["cancel_succeeded"] is True
    assert payload["final_open_order_ids"] == []
    assert fake_router.submitted_requests
    assert fake_router.stop_called is True
    factory.assert_called_once_with(
        "broker.env",
        prefer_limit_orders=True,
        limit_price_offset_bps=0.0,
        require_paper=True,
    )
