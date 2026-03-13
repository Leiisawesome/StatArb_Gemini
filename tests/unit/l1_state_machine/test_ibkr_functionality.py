from __future__ import annotations

import json
from unittest.mock import patch

from l1_microstructure.cli import main
from l1_microstructure.decision import TradeAction
from l1_microstructure.events import QuoteEvent
from l1_microstructure.execution import ExecutionReport
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live.broker_models import IBKRConnectionConfig
from l1_microstructure.live.router_adapters import IBKRBrokerOrderRouter, _load_ibkr_connection_config


def _observed_state(symbol: str = "AAPL"):
    state = FeatureEngine().update(
        QuoteEvent(
            symbol=symbol,
            timestamp_ns=1_000_000_000,
            bid_price=100.0,
            ask_price=100.02,
            bid_size=300,
            ask_size=300,
        )
    )
    assert state is not None
    return state


def test_load_ibkr_connection_config_prefers_env_file_and_fills_missing_from_environment(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "broker.env"
    env_file.write_text(
        "ACTIVE_BROKER=interactive_brokers\n"
        "IBKR_HOST=10.0.0.5\n"
        "IBKR_PAPER_TRADING=false\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("IBKR_PORT", "7497")
    monkeypatch.setenv("IBKR_CLIENT_ID", "22")
    monkeypatch.setenv("IBKR_OUTSIDE_RTH", "true")
    monkeypatch.setenv("IBKR_ACCOUNT_ID", "DU999999")

    config = _load_ibkr_connection_config(str(env_file))

    assert config.host == "10.0.0.5"
    assert config.port == 7497
    assert config.client_id == 22
    assert config.account_id == "DU999999"
    assert config.paper_trading is False
    assert config.outside_regular_trading_hours is True


def test_ibkr_broker_order_router_from_env_allows_live_when_explicitly_enabled() -> None:
    fake_live_ibkr_config = IBKRConnectionConfig(paper_trading=False)

    with patch("l1_microstructure.live.router_adapters._load_ibkr_connection_config", return_value=fake_live_ibkr_config), patch(
        "l1_microstructure.live.router_adapters.IBKRBrokerOrderRouter._build_broker", return_value="broker-facade"
    ):
        router = IBKRBrokerOrderRouter.from_env("broker.env", require_paper=False, auto_connect=False)

    assert isinstance(router, IBKRBrokerOrderRouter)
    assert router.ibkr_config.paper_trading is False
    assert router.broker == "broker-facade"


def test_cli_ibkr_live_smoke_can_disable_paper_guard(capsys) -> None:
    class FakeSmokeRouter:
        def health_check(self):
            return {"connected": True, "status": "healthy", "broker": "Interactive Brokers"}

        def open_order_ids(self):
            return []

        def stop(self):
            return None

    with patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value=FakeSmokeRouter()) as factory:
        exit_code = main(["ibkr-live-smoke", "--broker-env-file", "broker.env", "--allow-live-broker-routing"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["health"]["connected"] is True
    factory.assert_called_once_with("broker.env", require_paper=False)


def test_cli_ibkr_live_order_smoke_can_disable_paper_guard_and_use_market_mode(capsys) -> None:
    class FakeOrderSmokeRouter:
        def __init__(self) -> None:
            self.stop_called = False

        def submit(self, request):
            return type(
                "Ack",
                (),
                {
                    "external_order_id": "ibkr-smoke-live-1",
                    "status": "accepted",
                    "reason": "accepted",
                    "metadata": {"adapter": "broker-backed"},
                },
            )()

        def poll(self, symbols):
            return []

        def cancel(self, order_id: str) -> bool:
            return True

        def open_order_ids(self):
            return []

        def health_check(self):
            return {"connected": True, "status": "healthy", "broker": "Interactive Brokers", "open_order_count": 0}

        def stop(self):
            self.stop_called = True

    fake_router = FakeOrderSmokeRouter()
    with (
        patch("l1_microstructure.cli._latest_observed_state_from_rest", return_value=_observed_state("AAPL")),
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
                "--broker-order-mode",
                "market",
                "--poll-attempts",
                "0",
                "--allow-live-broker-routing",
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["router_type"] == "ibkr-live"
    assert payload["acknowledgement"]["external_order_id"] == "ibkr-smoke-live-1"
    assert fake_router.stop_called is True
    factory.assert_called_once_with(
        "broker.env",
        prefer_limit_orders=False,
        limit_price_offset_bps=0.0,
        require_paper=False,
    )


def test_cli_ibkr_live_order_smoke_reports_read_only_api_diagnostic(capsys) -> None:
    class FakeReadOnlyRouter:
        def __init__(self) -> None:
            self.stop_called = False

        def submit(self, request):
            return type(
                "Ack",
                (),
                {
                    "external_order_id": "1",
                    "status": "accepted",
                    "reason": "accepted",
                    "metadata": {"adapter": "ibkr-native"},
                },
            )()

        def poll(self, symbols):
            return [
                ExecutionReport(
                    symbol="AAPL",
                    action=TradeAction.BUY,
                    status="rejected",
                    quantity=0,
                    fill_price=None,
                    alignment_probability=0.0,
                    fill_probability=0.0,
                    slippage_bps=0.0,
                    reason="IBKR error 321: Error validating request.-'ct' : cause - The API interface is currently in Read-Only mode.",
                    timestamp_ns=1,
                )
            ]

        def cancel(self, order_id: str) -> bool:
            return False

        def open_order_ids(self):
            return []

        def health_check(self):
            return {
                "connected": True,
                "status": "healthy",
                "broker": "Interactive Brokers",
                "open_order_count": 0,
                "last_error": "IBKR error 321: Error validating request.-'ct' : cause - The API interface is currently in Read-Only mode.",
            }

        def stop(self):
            self.stop_called = True

    fake_router = FakeReadOnlyRouter()
    with (
        patch("l1_microstructure.cli._latest_observed_state_from_rest", return_value=_observed_state("AAPL")),
        patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value=fake_router),
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
            ]
        )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["diagnostics"]["issue"] == "read_only_api_mode"
    assert "Disable 'Read-Only API'" in payload["diagnostics"]["recommended_action"]
    assert fake_router.stop_called is True