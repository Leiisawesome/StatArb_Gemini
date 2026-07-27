from __future__ import annotations

from argparse import Namespace
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from l1_microstructure.cli import _router_from_args
from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import QuoteEvent
from l1_microstructure.features import FeatureEngine
from l1_microstructure.live import (
    BrokerOpenOrderRecovery,
    BrokerRecoveryError,
    BrokerRouterRecoveryState,
    IBKRBrokerOrderRouter,
)
from l1_microstructure.live.recovery import BrokerRecoveryCodec
from l1_microstructure.live.broker_models import (
    BrokerOrder,
    BrokerOrderSide,
    BrokerOrderStatus,
    BrokerOrderType,
    IBKRConnectionConfig,
)
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.retry import RetryPolicy
from l1_microstructure.transitions import EdgeKey


def _request(quantity: int = 25):
    state = FeatureEngine().update(
        QuoteEvent(
            symbol="AAPL", timestamp_ns=1_000_000_000, bid_price=100.0, ask_price=100.02, bid_size=300, ask_size=300
        )
    )
    assert state is not None
    intent = TradeIntent(
        action=TradeAction.BUY,
        edge=EdgeKey(
            "tight|neutral|neutral|stable|quiet",
            "wide|buy_heavy|buy_heavy|chaotic|stressed",
            MicrostructureRegime.EXECUTION_FLOW,
        ),
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
        self.orders: dict[str, BrokerOrder] = {}
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


def test_broker_connection_retries_before_single_order_submission() -> None:
    class TransientConnectBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.connect_attempts = 0
            self.submission_attempts = 0

        async def connect(self) -> bool:
            self.connect_attempts += 1
            if self.connect_attempts < 3:
                raise TimeoutError("gateway starting")
            self.connected = True
            return True

        async def submit_order(self, *args, **kwargs):
            self.submission_attempts += 1
            return await super().submit_order(*args, **kwargs)

    waits: list[float] = []
    broker = TransientConnectBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        connection_retry_policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.5,
            maximum_delay_seconds=1.0,
        ),
        retry_wait=waits.append,
    )

    acknowledgement = router.submit(_request(quantity=12))

    assert acknowledgement.status == "accepted"
    assert broker.connect_attempts == 3
    assert broker.submission_attempts == 1
    assert waits == [0.5, 1.0]
    assert router.retry_diagnostics()["connect"]["attempts"] == 3


def test_ambiguous_order_submission_is_never_retried() -> None:
    class AmbiguousSubmissionBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.submission_attempts = 0

        async def submit_order(self, *args, **kwargs):
            self.submission_attempts += 1
            raise TimeoutError("submission outcome is unknown")

    waits: list[float] = []
    broker = AmbiguousSubmissionBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        connection_retry_policy=RetryPolicy(max_attempts=3),
        read_retry_policy=RetryPolicy(max_attempts=3),
        retry_wait=waits.append,
    )

    acknowledgement = router.submit(_request(quantity=12))

    assert acknowledgement.status == "rejected"
    assert "outcome is unknown" in acknowledgement.reason
    assert broker.submission_attempts == 1
    assert waits == []


def test_ambiguous_order_cancellation_is_never_retried() -> None:
    class AmbiguousCancellationBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.cancel_attempts = 0

        async def cancel_order(self, order_id: str) -> bool:
            self.cancel_attempts += 1
            raise TimeoutError("cancellation outcome is unknown")

    waits: list[float] = []
    broker = AmbiguousCancellationBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        read_retry_policy=RetryPolicy(max_attempts=3),
        retry_wait=waits.append,
    )

    with pytest.raises(TimeoutError, match="outcome is unknown"):
        router.cancel("order-1")

    assert broker.cancel_attempts == 1
    assert waits == []


def test_broker_health_read_retries_transient_failures() -> None:
    class TransientHealthBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.health_attempts = 0

        async def check_health(self):
            self.health_attempts += 1
            if self.health_attempts < 3:
                raise ConnectionError("health channel unavailable")
            return await super().check_health()

    waits: list[float] = []
    broker = TransientHealthBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        read_retry_policy=RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.25,
            maximum_delay_seconds=0.5,
        ),
        retry_wait=waits.append,
    )

    health = router.health_check()

    assert health["connected"] is True
    assert broker.health_attempts == 3
    assert waits == [0.25, 0.5]
    assert health["retry"]["health_check"]["attempts"] == 3


def test_broker_connection_does_not_retry_permission_failure() -> None:
    class PermissionDeniedBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.connect_attempts = 0

        async def connect(self) -> bool:
            self.connect_attempts += 1
            raise PermissionError("API access denied")

    waits: list[float] = []
    broker = PermissionDeniedBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        connection_retry_policy=RetryPolicy(max_attempts=3),
        retry_wait=waits.append,
    )

    health = router.health_check()

    assert health["connected"] is False
    assert broker.connect_attempts == 1
    assert waits == []
    assert health["retry"]["connect"]["failures"][0]["retryable"] is False


def test_broker_reconciliation_query_retries_transient_failure() -> None:
    class TransientReconciliationBroker(FakeAsyncBrokerFacade):
        def __init__(self) -> None:
            super().__init__()
            self.reconciliation_attempts = 0

        async def reconciliation_snapshot(self):
            self.reconciliation_attempts += 1
            if self.reconciliation_attempts < 2:
                raise TimeoutError("account summary delayed")
            return {
                "connected": True,
                "status": "healthy",
                "positions": {},
                "open_order_ids": [],
                "net_liquidation": 100_000.0,
            }

    waits: list[float] = []
    broker = TransientReconciliationBroker()
    router = IBKRBrokerOrderRouter(
        IBKRConnectionConfig(),
        broker=broker,
        read_retry_policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0.25),
        retry_wait=waits.append,
    )

    snapshot = router.reconciliation_snapshot()

    assert snapshot["connected"] is True
    assert broker.reconciliation_attempts == 2
    assert waits == [0.25]
    assert snapshot["retry"]["reconciliation"]["attempts"] == 2


def test_broker_recovery_rejects_unsupported_version_before_mutation() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    acknowledgement = router.submit(_request(quantity=12))
    invalid_state = replace(router.snapshot_recovery_state(), version=999)

    with pytest.raises(ValueError, match="unsupported broker recovery version"):
        router.restore_recovery_state(invalid_state)

    assert router.open_order_ids() == [acknowledgement.external_order_id]


def test_broker_recovery_codec_round_trips_complete_request() -> None:
    state = BrokerRouterRecoveryState(
        open_orders=[BrokerOpenOrderRecovery(external_order_id="paper-42", request=_request(quantity=12), filled_quantity=5)]
    )

    recovered = BrokerRecoveryCodec.from_dict(BrokerRecoveryCodec.to_dict(state))

    assert recovered == state


def test_broker_recovery_codec_round_trips_infinite_posterior_uncertainty() -> None:
    request = _request(quantity=1)
    request = replace(
        request,
        intent=replace(request.intent, posterior=replace(request.intent.posterior, std_bps=float("inf"))),
    )
    state = BrokerRouterRecoveryState(
        open_orders=[BrokerOpenOrderRecovery(external_order_id="paper-flatten", request=request)]
    )

    payload = BrokerRecoveryCodec.to_dict(state)
    recovered = BrokerRecoveryCodec.from_dict(payload)

    assert payload["open_orders"][0]["request"]["intent"]["posterior"]["std_bps"] == "Infinity"
    assert recovered == state


def test_broker_recovery_codec_rejects_malformed_payload() -> None:
    with pytest.raises(ValueError, match="malformed"):
        BrokerRecoveryCodec.from_dict({"version": 1, "open_orders": [{"external_order_id": "paper-42"}]})


def test_broker_recovery_codec_rejects_nan() -> None:
    request = _request(quantity=1)
    request = replace(
        request,
        intent=replace(request.intent, posterior=replace(request.intent.posterior, std_bps=float("nan"))),
    )

    with pytest.raises(ValueError, match="NaN"):
        BrokerRecoveryCodec.request_to_dict(request)


def test_broker_recovery_rejects_corrupted_order_before_mutation() -> None:
    broker = FakeAsyncBrokerFacade()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    acknowledgement = router.submit(_request(quantity=12))
    current_state = router.snapshot_recovery_state()
    corrupted = BrokerRouterRecoveryState(open_orders=[replace(current_state.open_orders[0], filled_quantity=13.0)])

    with pytest.raises(ValueError, match="invalid filled quantity"):
        router.restore_recovery_state(corrupted)

    assert router.open_order_ids() == [acknowledgement.external_order_id]


def test_broker_recovery_lookup_failure_preserves_existing_tracking() -> None:
    class LookupFailingBroker(FakeAsyncBrokerFacade):
        fail_lookups = False

        async def get_orders(self, status="open"):
            if self.fail_lookups:
                raise TimeoutError("broker timeout")
            return await super().get_orders(status=status)

    broker = LookupFailingBroker()
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    acknowledgement = router.submit(_request(quantity=12))
    recovery_state = router.snapshot_recovery_state()
    broker.fail_lookups = True

    with pytest.raises(RuntimeError, match="failed to query broker open orders"):
        router.restore_recovery_state(recovery_state)

    assert router.open_order_ids() == [acknowledgement.external_order_id]


def test_broker_recovery_reports_only_unseen_partial_fill_delta() -> None:
    broker = FakeAsyncBrokerFacade()
    first_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    acknowledgement = first_router.submit(_request(quantity=12))
    order = broker.orders[acknowledgement.external_order_id]
    order.status = BrokerOrderStatus.PARTIAL_FILLED
    order.filled_quantity = 5
    order.average_price = 100.025
    assert first_router.poll(("AAPL",))[0].quantity == 5
    recovery_state = first_router.snapshot_recovery_state()

    order.filled_quantity = 7
    recovered_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    recovered_router.restore_recovery_state(recovery_state)

    reports = recovered_router.poll(("AAPL",))
    assert [report.quantity for report in reports] == [2]
    assert recovered_router.recovery_reconciliations()[0].status == "open"


def test_broker_recovery_reports_missing_and_rejects_mismatched_orders() -> None:
    broker = FakeAsyncBrokerFacade()
    first_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    acknowledgement = first_router.submit(_request(quantity=12))
    recovery_state = first_router.snapshot_recovery_state()

    terminal_order = broker.orders[acknowledgement.external_order_id]
    terminal_order.status = BrokerOrderStatus.FILLED
    terminal_order.filled_quantity = 12
    terminal_order.average_price = 100.03
    terminal_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    terminal_router.restore_recovery_state(recovery_state)
    assert terminal_router.recovery_reconciliations()[0].status == "terminal"
    assert terminal_router.poll(("AAPL",))[0].quantity == 12

    missing_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    missing_order = broker.orders.pop(acknowledgement.external_order_id)
    missing_router.restore_recovery_state(recovery_state)
    assert missing_router.recovery_reconciliations()[0].status == "missing"
    assert missing_router.open_order_ids() == []

    missing_order.symbol = "MSFT"
    broker.orders[acknowledgement.external_order_id] = missing_order
    mismatched_router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=broker)
    with pytest.raises(BrokerRecoveryError, match="does not match broker state") as exc_info:
        mismatched_router.restore_recovery_state(recovery_state)

    assert exc_info.value.reconciliations[0].status == "mismatched"
    assert mismatched_router.open_order_ids() == []


def test_broker_recovery_rejects_request_symbol_mismatch() -> None:
    request = _request(quantity=12)
    corrupted_request = replace(request, symbol="MSFT")
    state = BrokerRouterRecoveryState(
        open_orders=[BrokerOpenOrderRecovery(external_order_id="order-1", request=corrupted_request)]
    )
    router = IBKRBrokerOrderRouter(IBKRConnectionConfig(), broker=FakeAsyncBrokerFacade())

    with pytest.raises(ValueError, match="request symbol"):
        router.restore_recovery_state(state)


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

    with (
        patch("l1_microstructure.live.router_adapters._load_ibkr_connection_config", return_value=fake_ibkr_config),
        patch(
            "l1_microstructure.live.router_adapters.IBKRBrokerOrderRouter._build_broker", return_value="broker-facade"
        ) as build_broker,
    ):
        router = IBKRBrokerOrderRouter.from_env("broker.env", auto_connect=False)

    assert isinstance(router, IBKRBrokerOrderRouter)
    assert router.broker == "broker-facade"
    build_broker.assert_called_once_with(fake_ibkr_config)


def test_ibkr_broker_order_router_from_env_rejects_live_config_by_default() -> None:
    fake_live_ibkr_config = IBKRConnectionConfig(paper_trading=False)

    with patch(
        "l1_microstructure.live.router_adapters._load_ibkr_connection_config", return_value=fake_live_ibkr_config
    ):
        try:
            IBKRBrokerOrderRouter.from_env("broker.env")
        except ValueError as exc:
            assert "paper trading" in str(exc)
        else:
            raise AssertionError("expected paper-trading guard to reject live IBKR config")
