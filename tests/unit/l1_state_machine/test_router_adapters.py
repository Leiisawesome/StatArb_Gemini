from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import patch

from core_engine.type_definitions.orders import Order, OrderSide, OrderStatus, OrderType

from l1_microstructure.cli import _router_from_args
from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live import BrokerBackedOrderRouter, IBKRBrokerOrderRouter
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

    async def submit_order(self, symbol, quantity, side, order_type=OrderType.MARKET, limit_price=None):
        self.last_submission = {
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "order_type": order_type,
            "limit_price": limit_price,
        }
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=limit_price,
            status=OrderStatus.SUBMITTED,
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
            if order.status not in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}
        ]

    async def cancel_order(self, order_id: str) -> bool:
        self.cancelled_order_ids.append(order_id)
        order = self.orders.get(order_id)
        if order is None:
            return False
        order.status = OrderStatus.CANCELLED
        return True

    def broker_name(self) -> str:
        return "fake-broker"


def test_broker_backed_router_translates_terminal_broker_fill() -> None:
    broker = FakeAsyncBrokerFacade()
    router = BrokerBackedOrderRouter(broker=broker)
    request = _request(quantity=17)

    acknowledgement = router.submit(request)

    assert acknowledgement.status == "accepted"
    order = broker.orders[acknowledgement.external_order_id]
    order.status = OrderStatus.FILLED
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
    router = BrokerBackedOrderRouter(broker=broker, prefer_limit_orders=True)

    acknowledgement = router.submit(_request(quantity=10))

    assert acknowledgement.status == "accepted"
    assert broker.last_submission is not None
    assert broker.last_submission["side"] is OrderSide.BUY
    assert broker.last_submission["order_type"] is OrderType.LIMIT
    assert broker.last_submission["limit_price"] == 100.02


def test_broker_backed_router_emits_incremental_partial_fill_then_cancel() -> None:
    broker = FakeAsyncBrokerFacade()
    router = BrokerBackedOrderRouter(broker=broker)

    acknowledgement = router.submit(_request(quantity=20))
    order = broker.orders[acknowledgement.external_order_id]
    order.status = OrderStatus.PARTIAL_FILLED
    order.filled_quantity = 7
    order.average_price = 100.025
    order.timestamp = datetime.now(timezone.utc)

    first_reports = router.poll(("AAPL",))

    assert len(first_reports) == 1
    assert first_reports[0].status == "filled"
    assert first_reports[0].quantity == 7

    order.status = OrderStatus.CANCELLED
    second_reports = router.poll(("AAPL",))

    assert len(second_reports) == 1
    assert second_reports[0].status == "cancelled"


def test_broker_backed_router_cancels_open_orders_on_stop() -> None:
    broker = FakeAsyncBrokerFacade()
    router = BrokerBackedOrderRouter(broker=broker)

    acknowledgement = router.submit(_request(quantity=11))
    order_id = acknowledgement.external_order_id

    router.stop()

    assert order_id in broker.cancelled_order_ids


def test_broker_backed_router_restores_open_orders_into_fresh_router() -> None:
    broker = FakeAsyncBrokerFacade()
    first_router = BrokerBackedOrderRouter(broker=broker)

    acknowledgement = first_router.submit(_request(quantity=12))
    recovery_state = first_router.snapshot_recovery_state()

    recovered_router = BrokerBackedOrderRouter(broker=broker)
    recovered_router.restore_recovery_state(recovery_state)

    assert recovered_router.open_order_ids() == [acknowledgement.external_order_id]

    order = broker.orders[acknowledgement.external_order_id]
    order.status = OrderStatus.PARTIAL_FILLED
    order.filled_quantity = 5
    order.average_price = 100.025
    first_reports = recovered_router.poll(("AAPL",))

    assert len(first_reports) == 1
    assert first_reports[0].status == "filled"
    assert first_reports[0].quantity == 5

    order.status = OrderStatus.FILLED
    order.filled_quantity = 12
    order.average_price = 100.03
    second_reports = recovered_router.poll(("AAPL",))

    assert len(second_reports) == 1
    assert second_reports[0].status == "filled"
    assert second_reports[0].quantity == 7
    assert recovered_router.open_order_ids() == []


def test_cli_router_factory_supports_ibkr_live_router() -> None:
    args = Namespace(
        router_type="ibkr-live",
        broker_env_file="tests.env",
        router_poll_delay=1,
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
    fake_ibkr_config = type("FakeIBKRConfig", (), {"paper_trading": True})()
    fake_broker_config = type(
        "FakeBrokerConfig",
        (),
        {"active_broker": __import__("core_engine.config.broker_config", fromlist=["BrokerType"]).BrokerType.INTERACTIVE_BROKERS, "interactive_brokers": fake_ibkr_config},
    )()

    with patch("core_engine.config.broker_config.BrokerConfigLoader.load_from_env", return_value=fake_broker_config), patch(
        "core_engine.broker.adapters.ibkr_adapter.IBKRAdapter", return_value="ibkr-adapter"
    ) as ibkr_cls, patch("core_engine.broker.broker_adapter.BrokerAdapter", return_value="broker-facade") as broker_cls:
        router = IBKRBrokerOrderRouter.from_env("broker.env", auto_connect=False)

    assert isinstance(router, IBKRBrokerOrderRouter)
    assert router.broker == "broker-facade"
    ibkr_cls.assert_called_once_with(fake_ibkr_config)
    broker_cls.assert_called_once_with("ibkr-adapter")


def test_ibkr_broker_order_router_from_env_rejects_live_config_by_default() -> None:
    broker_type = __import__("core_engine.config.broker_config", fromlist=["BrokerType"]).BrokerType
    fake_live_ibkr_config = type("FakeLiveIBKRConfig", (), {"paper_trading": False})()
    fake_broker_config = type(
        "FakeBrokerConfig",
        (),
        {"active_broker": broker_type.INTERACTIVE_BROKERS, "interactive_brokers": fake_live_ibkr_config},
    )()

    with patch("core_engine.config.broker_config.BrokerConfigLoader.load_from_env", return_value=fake_broker_config):
        try:
            IBKRBrokerOrderRouter.from_env("broker.env")
        except ValueError as exc:
            assert "paper trading" in str(exc)
        else:
            raise AssertionError("expected paper-trading guard to reject live IBKR config")