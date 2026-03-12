"""Native Interactive Brokers session management via the ibapi package."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any

from ibapi.client import EClient
from ibapi.contract import Contract
from ibapi.execution import Execution
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.wrapper import EWrapper

from .broker_models import BrokerOrder, BrokerOrderSide, BrokerOrderStatus, BrokerOrderType, IBKRConnectionConfig


_TERMINAL_STATUSES = {
    BrokerOrderStatus.FILLED,
    BrokerOrderStatus.CANCELLED,
    BrokerOrderStatus.REJECTED,
}

_NON_FATAL_INFO_CODES = {
    2103,
    2104,
    2105,
    2106,
    2107,
    2108,
    2158,
}

_CANCELLED_ERROR_CODES = {
    202,
    10148,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ibkr_status_to_broker_status(status: str | None) -> BrokerOrderStatus:
    normalized = str(status or "").strip().lower()
    if normalized == "filled":
        return BrokerOrderStatus.FILLED
    if normalized in {"cancelled", "apicancelled"}:
        return BrokerOrderStatus.CANCELLED
    if normalized == "inactive":
        return BrokerOrderStatus.REJECTED
    if normalized in {"submitted", "presubmitted", "pendingcancel", "pendingsubmit", "api_pending"}:
        return BrokerOrderStatus.SUBMITTED
    return BrokerOrderStatus.SUBMITTED


class _IBKRApp(EWrapper, EClient):
    def __init__(self, session: "IBKRNativeBrokerSession"):
        EClient.__init__(self, self)
        self._session = session

    def nextValidId(self, orderId: int) -> None:  # noqa: N802
        super().nextValidId(orderId)
        self._session.on_next_valid_id(orderId)

    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = "") -> None:  # noqa: N802
        self._session.on_error(reqId, errorCode, errorString, advancedOrderRejectJson)

    def orderStatus(  # noqa: N802
        self,
        orderId: int,
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float,
    ) -> None:
        super().orderStatus(
            orderId,
            status,
            filled,
            remaining,
            avgFillPrice,
            permId,
            parentId,
            lastFillPrice,
            clientId,
            whyHeld,
            mktCapPrice,
        )
        self._session.on_order_status(orderId, status, filled, remaining, avgFillPrice, lastFillPrice)

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState: OrderState) -> None:  # noqa: N802
        super().openOrder(orderId, contract, order, orderState)
        self._session.on_open_order(orderId, contract, order, orderState)

    def openOrderEnd(self) -> None:  # noqa: N802
        super().openOrderEnd()
        self._session.on_open_order_end()

    def execDetails(self, reqId: int, contract: Contract, execution: Execution) -> None:  # noqa: N802
        super().execDetails(reqId, contract, execution)
        self._session.on_execution_details(contract, execution)

    def connectionClosed(self) -> None:  # noqa: N802
        super().connectionClosed()
        self._session.on_connection_closed()


class IBKRNativeBrokerSession:
    def __init__(self, config: IBKRConnectionConfig):
        self.config = config
        self._lock = Lock()
        self._ready_event = Event()
        self._open_orders_event = Event()
        self._connected = False
        self._app: _IBKRApp | None = None
        self._thread: Thread | None = None
        self._orders: dict[str, BrokerOrder] = {}
        self._next_order_id: int | None = None
        self._last_error: str | None = None

    async def connect(self) -> bool:
        if self.is_connected():
            return True
        self._ready_event.clear()
        self._last_error = None
        self._app = _IBKRApp(self)
        try:
            self._app.connect(self.config.host, self.config.port, self.config.client_id)
        except Exception as exc:
            self._last_error = str(exc)
            raise RuntimeError(f"failed to connect to IBKR gateway: {exc}") from exc

        self._thread = Thread(target=self._app.run, daemon=True)
        self._thread.start()
        if not self._ready_event.wait(timeout=5.0):
            message = self._last_error or "timed out waiting for IBKR connection readiness"
            await self.disconnect()
            raise RuntimeError(message)
        return True

    async def disconnect(self) -> None:
        app = self._app
        if app is None:
            self._connected = False
            return
        try:
            app.disconnect()
        finally:
            thread = self._thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)
            self._connected = False
            self._app = None
            self._thread = None

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    async def submit_order(
        self,
        symbol: str,
        quantity: float,
        side: BrokerOrderSide,
        *,
        order_type: BrokerOrderType = BrokerOrderType.MARKET,
        limit_price: float | None = None,
    ) -> BrokerOrder:
        await self.connect()
        app = self._require_app()
        order_id = self._reserve_order_id()
        broker_order = BrokerOrder(
            symbol=symbol,
            side=side,
            quantity=float(quantity),
            order_type=order_type,
            price=limit_price,
            status=BrokerOrderStatus.SUBMITTED,
            timestamp=_utc_now(),
            order_id=str(order_id),
        )
        with self._lock:
            self._orders[broker_order.order_id] = broker_order
        app.placeOrder(order_id, self._stock_contract(symbol), self._build_order(side, quantity, order_type, limit_price))
        return replace(broker_order)

    async def get_order(self, order_id: str) -> BrokerOrder | None:
        await self.connect()
        self._refresh_open_orders()
        with self._lock:
            order = self._orders.get(str(order_id))
            return replace(order) if order is not None else None

    async def get_orders(self, status: str = "open") -> list[BrokerOrder]:
        await self.connect()
        self._refresh_open_orders()
        with self._lock:
            orders = list(self._orders.values())
        if status == "open":
            orders = [order for order in orders if order.status not in _TERMINAL_STATUSES]
        return [replace(order) for order in orders]

    async def cancel_order(self, order_id: str) -> bool:
        await self.connect()
        app = self._require_app()
        try:
            app.cancelOrder(int(order_id), "")
        except TypeError:
            app.cancelOrder(int(order_id))
        return True

    async def check_health(self) -> dict[str, Any]:
        connected = self.is_connected()
        with self._lock:
            open_order_count = len([order for order in self._orders.values() if order.status not in _TERMINAL_STATUSES])
            last_error = self._last_error
        return {
            "connected": connected,
            "status": "healthy" if connected else "disconnected",
            "broker": self.broker_name(),
            "host": self.config.host,
            "port": self.config.port,
            "client_id": self.config.client_id,
            "open_order_count": open_order_count,
            "last_error": last_error,
        }

    def broker_name(self) -> str:
        return "Interactive Brokers"

    def on_next_valid_id(self, order_id: int) -> None:
        with self._lock:
            self._connected = True
            self._next_order_id = int(order_id)
        self._ready_event.set()

    def on_error(self, req_id: int, error_code: int, error_string: str, advanced_order_reject_json: str = "") -> None:
        if error_code in _NON_FATAL_INFO_CODES:
            return

        message = f"IBKR error {error_code}: {error_string}" if error_string else f"IBKR error {error_code}"
        if advanced_order_reject_json:
            message = f"{message} | reject={advanced_order_reject_json}"
        with self._lock:
            self._last_error = message
            order = self._orders.get(str(req_id))
            if order is not None:
                order.status = BrokerOrderStatus.CANCELLED if error_code in _CANCELLED_ERROR_CODES else BrokerOrderStatus.REJECTED
                order.timestamp = _utc_now()
            connected = self._connected
        if not connected:
            self._ready_event.set()

    def on_order_status(
        self,
        order_id: int,
        status: str,
        filled: float,
        remaining: float,
        avg_fill_price: float,
        last_fill_price: float,
    ) -> None:
        total_quantity = float(filled or 0.0) + float(remaining or 0.0)
        timestamp = _utc_now()
        with self._lock:
            order = self._orders.get(str(order_id))
            if order is None:
                order = BrokerOrder(
                    symbol="",
                    side=BrokerOrderSide.BUY,
                    quantity=total_quantity,
                    order_type=BrokerOrderType.MARKET,
                    status=_ibkr_status_to_broker_status(status),
                    timestamp=timestamp,
                    order_id=str(order_id),
                )
                self._orders[str(order_id)] = order
            order.status = _ibkr_status_to_broker_status(status)
            if total_quantity > 0.0:
                order.quantity = total_quantity
            order.filled_quantity = float(filled or 0.0)
            if avg_fill_price:
                order.average_price = float(avg_fill_price)
            elif last_fill_price:
                order.average_price = float(last_fill_price)
            order.timestamp = timestamp

    def on_open_order(self, order_id: int, contract: Contract, order: Order, order_state: OrderState) -> None:
        quantity = float(order.totalQuantity or 0.0)
        side = BrokerOrderSide.BUY if str(order.action).upper() == "BUY" else BrokerOrderSide.SELL
        order_type = BrokerOrderType.LIMIT if str(order.orderType).upper() == "LMT" else BrokerOrderType.MARKET
        price = float(order.lmtPrice) if order_type is BrokerOrderType.LIMIT and order.lmtPrice is not None else None
        timestamp = _utc_now()
        with self._lock:
            existing = self._orders.get(str(order_id))
            if existing is None:
                existing = BrokerOrder(
                    symbol=str(contract.symbol or ""),
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    price=price,
                    status=_ibkr_status_to_broker_status(getattr(order_state, "status", None)),
                    timestamp=timestamp,
                    order_id=str(order_id),
                )
                self._orders[str(order_id)] = existing
            else:
                existing.symbol = str(contract.symbol or existing.symbol)
                existing.side = side
                if quantity > 0.0:
                    existing.quantity = quantity
                existing.order_type = order_type
                existing.price = price
                existing.status = _ibkr_status_to_broker_status(getattr(order_state, "status", None))
                existing.timestamp = timestamp

    def on_open_order_end(self) -> None:
        self._open_orders_event.set()

    def on_execution_details(self, contract: Contract, execution: Execution) -> None:
        timestamp = _utc_now()
        with self._lock:
            order = self._orders.get(str(execution.orderId))
            if order is None:
                return
            order.symbol = str(contract.symbol or order.symbol)
            order.filled_quantity = max(order.filled_quantity, float(execution.cumQty or 0.0))
            if execution.avgPrice:
                order.average_price = float(execution.avgPrice)
            elif execution.price:
                order.average_price = float(execution.price)
            order.timestamp = timestamp
            if order.filled_quantity >= order.quantity > 0.0:
                order.status = BrokerOrderStatus.FILLED

    def on_connection_closed(self) -> None:
        with self._lock:
            self._connected = False

    def _refresh_open_orders(self) -> None:
        app = self._require_app()
        self._open_orders_event.clear()
        app.reqOpenOrders()
        self._open_orders_event.wait(timeout=1.0)

    def _reserve_order_id(self) -> int:
        with self._lock:
            if self._next_order_id is None:
                raise RuntimeError("IBKR connection is missing next valid order id")
            order_id = self._next_order_id
            self._next_order_id += 1
            return order_id

    def _require_app(self) -> _IBKRApp:
        app = self._app
        if app is None:
            raise RuntimeError("IBKR session is not connected")
        return app

    @staticmethod
    def _stock_contract(symbol: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract

    def _build_order(
        self,
        side: BrokerOrderSide,
        quantity: float,
        order_type: BrokerOrderType,
        limit_price: float | None,
    ) -> Order:
        order = Order()
        order.action = "BUY" if side is BrokerOrderSide.BUY else "SELL"
        order.orderType = "LMT" if order_type is BrokerOrderType.LIMIT else "MKT"
        order.totalQuantity = float(quantity)
        order.transmit = True
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        order.outsideRth = bool(self.config.outside_regular_trading_hours)
        if self.config.account_id:
            order.account = self.config.account_id
        if order_type is BrokerOrderType.LIMIT:
            if limit_price is None:
                raise ValueError("limit price is required for IBKR limit orders")
            order.lmtPrice = float(limit_price)
        return order