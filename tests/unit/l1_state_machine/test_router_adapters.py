from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import patch

from l1_microstructure.cli import _router_from_args
from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live import IBKRBrokerOrderRouter
from l1_microstructure.live.broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderStatus, BrokerOrderType, IBKRConnectionConfig
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.transitions import EdgeKey


def _request(quantity: int = 25):
    state = FeatureEngine().update(
        QuoteEvent(symbol="AAPL", timestamp_ns=1_000_000_000, bid_price=100.0, ask_price=100.02, bid_size=300, ask_size=300)
    )
    assert state is not None
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey("tight|neutral|neutral|stable|quiet", "wide|buy_heavy|buy_heavy|chaotic|stressed", MicrostructureRegime.EXECUTION_FLOW),
        posterior=PosteriorEstimate(
            mean_bps=3.0,
            std_bps=1.0,
            probability_up=0.75,
            probability_down=0.25,
            threshold_bps=1.0,
            sample_count=12,
        ),
        expected_holding_time_ns=1_000_000_000,
        reason="router-test",
    )
    from l1_microstructure.execution import ExecutionSimulator

    return ExecutionSimulator().build_request(intent, state, quantity)


class FakeAsyncBrokerFacade:
    def __init__(self) -> None:
        self.connected = False
        self.orders: dict[str, Order] = {}
        self.last_submission: dict[str, object] | None = None
        self.cancelled_order_ids: list[str] = []

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def disconnect(self) -> None:
        self.connected = False

    def is_connected(self) -> bool:
        return self.connected

    async def submit_order(self, symbol, quantity, side, order_type=BrokerOrderType.MARKET, limit_price=None):
        self.last_submission = {
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "limit_price": limit_price,
        }
        order = BrokerOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=limit_price,
            status=BrokerOrderStatus.SUBMITTED,
        )
        self.orders[order.order_id] = order
        return order

    async def get_order(self, order_id: str):
        return self.orders.get(order_id)

    async def get_orders(self, status="open"):
        if status != "open":
            return list(self.orders.values())
        return [
            order
            for order in self.orders.values()
            if order.status not in {BrokerOrderStatus.FILLED, BrokerOrderStatus.CANCELLED, BrokerOrderStatus.REJECTED}
        ]

    async def cancel_order(self, order_id: str) -> bool:
        self.cancelled_order_ids.append(order_id)
        order = self.orders.get(order_id)
        if order is None:
            return False
        order.status = BrokerOrderStatus.CANCELLED
        return True

    def broker_name(self) -> str:
        return "fake-broker"

    async def check_health(self):
        return {
            "connected": self.connected,
            "status": "healthy" if self.connected else "disconnected",
            "broker": self.broker_name(),
            "open_order_count": len(self.orders),
            "last_error": None,
        }


def test_broker_backed_router_translates_terminal_broker_fill() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    request = _request(quantity=17)

    acknowledgement = router.submit(request)

    assert acknowledgement.status == "accepted"
    order = broker.orders[acknowledgement.external_order_id]
    order.status = BrokerOrderStatus.FILLED
    order.filled_quantity = 17
    order.average_price = 100.03
    order.timestamp = datetime.now(timezone.utc)

    reports = router.poll(("AAPL",))

    assert len(reports) == 1
    assert reports[0].status == "filled"
    assert reports[0].quantity == 17
    assert reports[0].fill_price == 100.03


def test_broker_backed_router_can_submit_limit_orders_at_touch() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker, prefer_limit_orders=True)

    acknowledgement = router.submit(_request(quantity=10))

    assert acknowledgement.status == "accepted"
    assert broker.last_submission is not None
    assert broker.last_submission["side"] is BrokerOrderSide.BUY
    assert broker.last_submission["order_type"] is BrokerOrderType.LIMIT
    assert broker.last_submission["limit_price"] == 100.02


def test_broker_backed_router_emits_incremental_partial_fill_then_cancel() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)

    acknowledgement = router.submit(_request(quantity=20))
    order = broker.orders[acknowledgement.external_order_id]
    order.status = BrokerOrderStatus.PARTIAL_FILLED
    order.filled_quantity = 7
    order.average_price = 100.025
    order.timestamp = datetime.now(timezone.utc)

    first_reports = router.poll(("AAPL",))

    assert len(first_reports) == 1
    assert first_reports[0].status == "filled"
    assert first_reports[0].quantity == 7

    order.status = BrokerOrderStatus.CANCELLED
    second_reports = router.poll(("AAPL",))

    assert len(second_reports) == 1
    assert second_reports[0].status == "cancelled"


def test_broker_backed_router_cancels_open_orders_on_stop() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)

    acknowledgement = router.submit(_request(quantity=11))
    order_id = acknowledgement.external_order_id

    router.stop()

    assert order_id in broker.cancelled_order_ids


def test_broker_backed_router_health_check_uses_tracked_open_orders() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)

    acknowledgement = router.submit(_request(quantity=9))
    health = router.health_check()

    assert health["open_order_count"] == 1
    assert "broker_open_order_count" not in health

    broker.orders[acknowledgement.external_order_id].status = BrokerOrderStatus.CANCELLED
    router.poll(("AAPL",))
    health_after_cancel = router.health_check()

    assert health_after_cancel["open_order_count"] == 0
    assert health_after_cancel["broker_open_order_count"] == 1


def test_broker_backed_router_restores_open_orders_into_fresh_router() -> None:
    broker = FakeAsyncBrokerFacade()
    first_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)

    acknowledgement = first_router.submit(_request(quantity=12))
    recovery_state = first_router.snapshot_recovery_state()

    recovered_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    recovered_router.restore_recovery_state(recovery_state)

    assert recovered_router.open_order_ids() == [acknowledgement.external_order_id]

    order = broker.orders[acknowledgement.external_order_id]
    order.status = BrokerOrderStatus.PARTIAL_FILLED
    order.filled_quantity = 5
    order.average_price = 100.025
    first_reports = recovered_router.poll(("AAPL",))

    assert len(first_reports) == 1
    assert first_reports[0].status == "filled"
    assert first_reports[0].quantity == 5

    order.status = BrokerOrderStatus.FILLED
    order.filled_quantity = 12
    order.average_price = 100.03
    second_reports = recovered_router.poll(("AAPL",))

    assert len(second_reports) == 1
    assert second_reports[0].status == "filled"
    assert second_reports[0].quantity == 7
    assert recovered_router.open_order_ids() == []


def test_cli_router_factory_supports_ibkr_live_router() -> None:
    args = Namespace(
        broker_env_file="tests.env",
        broker_order_mode="limit",
        broker_limit_offset_bps=2.5,
        allow_live_broker_routing=False,
    )

    with patch("l1_microstructure.cli.IBKRBrokerOrderRouter.from_env", return_value="ibkr-router") as factory:
        router = _router_from_args(args)

    assert router == "ibkr-router"
    factory.assert_called_once_with(
        "tests.env",
        prefer_limit_orders=True,
        limit_price_offset_bps=2.5,
        require_paper=True,
    )


def test_ibkr_broker_order_router_from_env_builds_router() -> None:
    fake_ibkr_config = IBKRConnectionConfig(paper_trading=True)

    with patch("l1_microstructure.live.router_adapters._load_ibkr_connection_config", return_value=fake_ibkr_config), patch(
        "l1_microstructure.live.router_adapters.IBKRBrokerOrderRouter._build_broker", return_value="broker-facade"
    ) as build_broker:
        router = IBKRBrokerOrderRouter.from_env("broker.env", auto_connect=False)

    assert isinstance(router, IBKRBrokerOrderRouter)
    assert router.broker == "broker-facade"
    build_broker.assert_called_once_with(fake_ibkr_config)


def test_ibkr_broker_order_router_from_env_rejects_live_config_by_default() -> None:
    fake_live_ibkr_config = IBKRConnectionConfig(paper_trading=False)

    with patch("l1_microstructure.live.router_adapters._load_ibkr_connection_config", return_value=fake_live_ibkr_config):
        try:
            IBKRBrokerOrderRouter.from_env("broker.env")
        except ValueError as exc:
            assert "paper trading" in str(exc)
        else:
            raise AssertionError("expected paper-trading guard to reject live IBKR config")