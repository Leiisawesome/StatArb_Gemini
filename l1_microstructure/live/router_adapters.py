"""Native IBKR order-router adapter for successor-package live shells."""

from __future__ import annotations

import asyncio
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import dotenv_values
from threading import Thread
from typing import Any

from l1_microstructure.decision import TradeAction
from l1_microstructure.execution import ExecutionReport, ExecutionRequest

from ._ibkr_native import IBKRNativeBrokerSession
from .broker_models import BrokerOrderSide, BrokerOrderType, IBKRConnectionConfig
from .interfaces import RouteAcknowledgement


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _load_ibkr_connection_config(env_file: str | None) -> IBKRConnectionConfig:
    loaded: dict[str, str] = {}
    if env_file is not None:
        loaded.update({key: str(value) for key, value in dotenv_values(env_file).items() if value is not None})
    for key, value in os.environ.items():
        loaded.setdefault(key, value)

    active_broker = str(loaded.get("ACTIVE_BROKER", loaded.get("BROKER_TYPE", "interactive_brokers"))).strip().lower()
    if active_broker not in {"interactive_brokers", "ibkr"}:
        raise ValueError("broker configuration does not select interactive_brokers as the active broker")

    return IBKRConnectionConfig(
        host=str(loaded.get("IBKR_HOST", "127.0.0.1")),
        port=int(loaded.get("IBKR_PORT", 4002)),
        client_id=int(loaded.get("IBKR_CLIENT_ID", 1)),
        account_id=loaded.get("IBKR_ACCOUNT_ID") or loaded.get("IBKR_ACCOUNT"),
        paper_trading=_parse_bool(loaded.get("IBKR_PAPER_TRADING"), default=True),
        outside_regular_trading_hours=_parse_bool(loaded.get("IBKR_OUTSIDE_RTH"), default=False),
    )


@dataclass(frozen=True, slots=True)
class BrokerOpenOrderRecovery:
    external_order_id: str
    request: ExecutionRequest
    filled_quantity: float = 0.0


@dataclass(frozen=True, slots=True)
class BrokerRouterRecoveryState:
    open_orders: list[BrokerOpenOrderRecovery]


@dataclass(slots=True)
class IBKRBrokerOrderRouter:
    ibkr_config: IBKRConnectionConfig
    broker: Any | None = None
    prefer_limit_orders: bool = False
    limit_price_offset_bps: float = 0.0
    auto_connect: bool = True
    disconnect_on_stop: bool = True
    cancel_open_orders_on_stop: bool = True
    _submission_count: int = field(default=0, init=False)
    _connected: bool = field(default=False, init=False)
    _open_requests: dict[str, ExecutionRequest] = field(default_factory=dict, init=False)
    _filled_quantities: dict[str, float] = field(default_factory=dict, init=False)
    _pending_terminal_reports: list[ExecutionReport] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.broker = self.broker if self.broker is not None else self._build_broker(self.ibkr_config)

    def submit(self, request: ExecutionRequest) -> RouteAcknowledgement:
        self._submission_count += 1
        try:
            self._ensure_connected()
            order = self._submit_order(request)
            order_id = str(order.order_id)
            immediate_reports, terminal = self._reports_from_order(order, request, order_id)
            self._pending_terminal_reports.extend(immediate_reports)
            if terminal:
                self._open_requests.pop(order_id, None)
                self._filled_quantities.pop(order_id, None)
            else:
                self._open_requests[order_id] = request
                self._filled_quantities.setdefault(order_id, 0.0)
            return RouteAcknowledgement(
                external_order_id=order_id,
                status="accepted",
                metadata={"adapter": "ibkr-native", "broker": self._broker_name()},
            )
        except Exception as exc:
            self._pending_terminal_reports.append(self._error_report(request, str(exc)))
            return RouteAcknowledgement(
                external_order_id=f"broker-error-{self._submission_count}",
                status="rejected",
                reason=str(exc),
                metadata={"adapter": "ibkr-native", "broker": self._broker_name()},
            )

    def poll(self, symbols: tuple[str, ...]) -> list[ExecutionReport]:
        ready = [report for report in self._pending_terminal_reports if report.symbol in symbols]
        self._pending_terminal_reports = [report for report in self._pending_terminal_reports if report.symbol not in symbols]

        for order_id, request in list(self._open_requests.items()):
            if request.symbol not in symbols:
                continue
            order = self._run_async(self.broker.get_order(order_id))
            if order is None:
                continue
            reports, terminal = self._reports_from_order(order, request, order_id)
            ready.extend(reports)
            if terminal:
                self._open_requests.pop(order_id, None)
                self._filled_quantities.pop(order_id, None)
        return ready

    def stop(self) -> None:
        if self.cancel_open_orders_on_stop:
            for order_id in list(self._open_requests):
                self.cancel(order_id)
        if self.disconnect_on_stop and self._connected:
            self._run_async(self.broker.disconnect())
        self._connected = False
        self._open_requests = {}
        self._filled_quantities = {}
        self._pending_terminal_reports = []

    def cancel(self, order_id: str) -> bool:
        cancel_order = getattr(self.broker, "cancel_order", None)
        if not callable(cancel_order):
            return False
        return bool(self._run_async(cancel_order(order_id)))

    def open_order_ids(self) -> list[str]:
        return list(self._open_requests)

    def snapshot_recovery_state(self) -> BrokerRouterRecoveryState:
        return BrokerRouterRecoveryState(
            open_orders=[
                BrokerOpenOrderRecovery(
                    external_order_id=order_id,
                    request=request,
                    filled_quantity=float(self._filled_quantities.get(order_id, 0.0)),
                )
                for order_id, request in self._open_requests.items()
            ]
        )

    def restore_recovery_state(self, recovery_state: BrokerRouterRecoveryState | None) -> None:
        self._open_requests = {}
        self._filled_quantities = {}
        self._pending_terminal_reports = []
        if recovery_state is None:
            return

        self._ensure_connected()
        open_orders_by_id = self._broker_open_orders_by_id()
        for recovered in recovery_state.open_orders:
            order_id = recovered.external_order_id
            self._filled_quantities[order_id] = float(recovered.filled_quantity)
            order = open_orders_by_id.get(order_id)
            if order is None:
                order = self._run_async(self.broker.get_order(order_id))
            if order is None:
                self._filled_quantities.pop(order_id, None)
                continue

            reports, terminal = self._reports_from_order(order, recovered.request, order_id)
            self._pending_terminal_reports.extend(reports)
            if terminal:
                self._filled_quantities.pop(order_id, None)
                continue
            self._open_requests[order_id] = recovered.request

    def health_check(self) -> dict[str, Any]:
        try:
            self._ensure_connected()
        except Exception as exc:
            return {
                "connected": False,
                "status": "disconnected",
                "broker": self._broker_name(),
                "open_order_count": len(self._open_requests),
                "error": str(exc),
            }
        check_health = getattr(self.broker, "check_health", None)
        if callable(check_health):
            health = self._run_async(check_health())
            if isinstance(health, dict):
                normalized_health = dict(health)
                broker_open_order_count = normalized_health.get("open_order_count")
                normalized_health["open_order_count"] = len(self._open_requests)
                if broker_open_order_count != normalized_health["open_order_count"]:
                    normalized_health["broker_open_order_count"] = broker_open_order_count
                return normalized_health
        is_connected = getattr(self.broker, "is_connected", None)
        connected = bool(is_connected()) if callable(is_connected) else self._connected
        return {
            "connected": connected,
            "status": "healthy" if connected else "disconnected",
            "broker": self._broker_name(),
            "open_order_count": len(self._open_requests),
        }

    def _broker_open_orders_by_id(self) -> dict[str, Any]:
        get_orders = getattr(self.broker, "get_orders", None)
        if not callable(get_orders):
            adapter = getattr(self.broker, "adapter", None)
            get_orders = getattr(adapter, "get_orders", None)
        if not callable(get_orders):
            return {}
        try:
            orders = self._run_async(get_orders(status="open"))
        except Exception:
            return {}
        if not isinstance(orders, list):
            return {}
        return {
            str(getattr(order, "order_id", "")): order
            for order in orders
            if getattr(order, "order_id", None) is not None
        }

    def _ensure_connected(self) -> None:
        if not self.auto_connect:
            return
        is_connected = getattr(self.broker, "is_connected", None)
        if callable(is_connected) and is_connected():
            self._connected = True
            return
        connected = bool(self._run_async(self.broker.connect()))
        if not connected:
            raise RuntimeError("broker connection failed")
        self._connected = True

    def _submit_order(self, request: ExecutionRequest) -> Any:
        side = BrokerOrderSide.BUY if request.action == TradeAction.BUY else BrokerOrderSide.SELL
        order_type = BrokerOrderType.LIMIT if self.prefer_limit_orders else BrokerOrderType.MARKET
        limit_price = self._limit_price(request) if order_type is BrokerOrderType.LIMIT else None
        return self._run_async(
            self.broker.submit_order(
                request.symbol,
                float(request.quantity),
                side,
                order_type=order_type,
                limit_price=limit_price,
            )
        )

    def _reports_from_order(self, order: Any, request: ExecutionRequest, order_id: str) -> tuple[list[ExecutionReport], bool]:
        status = self._order_status_value(getattr(order, "status", None))
        reports: list[ExecutionReport] = []
        total_quantity = float(getattr(order, "quantity", request.quantity) or request.quantity)
        filled_quantity = float(getattr(order, "filled_quantity", 0.0) or 0.0)
        seen_quantity = self._filled_quantities.get(order_id, 0.0)
        newly_filled = max(filled_quantity - seen_quantity, 0.0)
        timestamp = getattr(order, "timestamp", None)
        timestamp_ns = self._timestamp_ns(timestamp, request.executable_timestamp_ns)

        if newly_filled > 0.0:
            fill_price = float(getattr(order, "average_price", None) or getattr(order, "price", None) or self._touch_price(request))
            reports.append(
                ExecutionReport(
                    symbol=request.symbol,
                    action=request.action,
                    status="filled",
                    quantity=int(round(newly_filled)),
                    fill_price=fill_price,
                    alignment_probability=1.0,
                    fill_probability=1.0,
                    slippage_bps=self._slippage_bps(fill_price, request),
                    reason="broker reported partial fill" if filled_quantity < total_quantity else "broker reported fill",
                    timestamp_ns=timestamp_ns,
                )
            )
            self._filled_quantities[order_id] = filled_quantity

        terminal = False
        if status in {"cancelled", "rejected"}:
            reports.append(
                ExecutionReport(
                    symbol=request.symbol,
                    action=request.action,
                    status=status,
                    quantity=0,
                    fill_price=None,
                    alignment_probability=0.0,
                    fill_probability=0.0,
                    slippage_bps=0.0,
                    reason=f"broker order {status}",
                    timestamp_ns=timestamp_ns,
                )
            )
            terminal = True
        elif status == "filled" and filled_quantity >= total_quantity:
            terminal = True

        return reports, terminal

    def _error_report(self, request: ExecutionRequest, reason: str) -> ExecutionReport:
        return ExecutionReport(
            symbol=request.symbol,
            action=request.action,
            status="rejected",
            quantity=0,
            fill_price=None,
            alignment_probability=0.0,
            fill_probability=0.0,
            slippage_bps=0.0,
            reason=reason,
            timestamp_ns=request.executable_timestamp_ns,
        )

    def _limit_price(self, request: ExecutionRequest) -> float:
        touch = self._touch_price(request)
        offset_multiplier = self.limit_price_offset_bps / 10_000.0
        tick_size = 0.01 if touch >= 1.0 else 0.0001
        if request.action == TradeAction.BUY:
            raw_price = float(touch * (1.0 + offset_multiplier))
            return float(math.floor(raw_price / tick_size) * tick_size)
        raw_price = float(touch * (1.0 - offset_multiplier))
        return float(math.ceil(raw_price / tick_size) * tick_size)

    def _touch_price(self, request: ExecutionRequest) -> float:
        if request.action == TradeAction.BUY:
            return float(request.expected_state.book.ask_price)
        return float(request.expected_state.book.bid_price)

    def _broker_name(self) -> str:
        broker_name = getattr(self.broker, "broker_name", None)
        if callable(broker_name):
            return str(broker_name())
        if broker_name is not None:
            return str(broker_name)
        return type(self.broker).__name__

    @staticmethod
    def _order_status_value(status: Any) -> str:
        if status is None:
            return "pending"
        return str(getattr(status, "value", status)).lower()

    @staticmethod
    def _timestamp_ns(timestamp: Any, fallback: int) -> int:
        if isinstance(timestamp, datetime):
            return int(timestamp.timestamp() * 1_000_000_000)
        return int(fallback)

    def _slippage_bps(self, fill_price: float, request: ExecutionRequest) -> float:
        touch = self._touch_price(request)
        if touch <= 0:
            return 0.0
        direction = 1.0 if request.action == TradeAction.BUY else -1.0
        return float(direction * ((fill_price - touch) / touch) * 10_000.0)

    @staticmethod
    def _run_async(coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                result["value"] = loop.run_until_complete(coroutine)
            except BaseException as exc:  # pragma: no cover - propagated immediately after join
                error["value"] = exc
            finally:
                loop.close()
                asyncio.set_event_loop(None)

        thread = Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()
        if "value" in error:
            raise error["value"]
        return result.get("value")

    @staticmethod
    def _build_broker(ibkr_config: IBKRConnectionConfig) -> Any:
        return IBKRNativeBrokerSession(ibkr_config)

    @classmethod
    def from_env(
        cls,
        env_file: str | None = None,
        *,
        prefer_limit_orders: bool = False,
        limit_price_offset_bps: float = 0.0,
        auto_connect: bool = True,
        disconnect_on_stop: bool = True,
        cancel_open_orders_on_stop: bool = True,
        require_paper: bool = True,
    ) -> "IBKRBrokerOrderRouter":
        ibkr_config = _load_ibkr_connection_config(env_file)
        if require_paper and not ibkr_config.paper_trading:
            raise ValueError("ibkr-live router requires paper trading configuration unless explicitly overridden")
        return cls(
            ibkr_config=ibkr_config,
            prefer_limit_orders=prefer_limit_orders,
            limit_price_offset_bps=limit_price_offset_bps,
            auto_connect=auto_connect,
            disconnect_on_stop=disconnect_on_stop,
            cancel_open_orders_on_stop=cancel_open_orders_on_stop,
        )