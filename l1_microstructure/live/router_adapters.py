"""Native IBKR order-router adapter for successor-package live shells."""

from __future__ import annotations

import asyncio
import inspect
import math
import os
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import dotenv_values
from random import random
from threading import Thread
from time import sleep, time_ns
from typing import Any, Callable

from l1_microstructure.decision import TradeAction
from l1_microstructure.execution import ExecutionReport, ExecutionRequest
from l1_microstructure.retry import RetryExecutor, RetryPolicy, RetryResult

from ._ibkr_native import IBKRNativeBrokerSession
from .broker_models import BrokerOrderSide, BrokerOrderType, IBKRConnectionConfig
from .interfaces import RouteAcknowledgement
from .recovery import (
    BrokerOpenOrderRecovery,
    BrokerRecoveryCodec,
    BrokerRecoveryError,
    BrokerRecoveryReconciliation,
    BrokerRouterRecoveryState,
)


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


def load_ibkr_connection_config(env_file: str | None) -> IBKRConnectionConfig:
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


_load_ibkr_connection_config = load_ibkr_connection_config


@dataclass(slots=True)
class IBKRBrokerOrderRouter:
    ibkr_config: IBKRConnectionConfig
    broker: Any | None = None
    prefer_limit_orders: bool = False
    limit_price_offset_bps: float = 0.0
    auto_connect: bool = True
    disconnect_on_stop: bool = True
    cancel_open_orders_on_stop: bool = True
    connection_retry_policy: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.5,
            maximum_delay_seconds=5.0,
        )
    )
    read_retry_policy: RetryPolicy = field(
        default_factory=lambda: RetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.25,
            maximum_delay_seconds=2.0,
        )
    )
    retry_wait: Callable[[float], None] = field(default=sleep, repr=False)
    retry_clock: Callable[[], int] = field(default=time_ns, repr=False)
    retry_random_source: Callable[[], float] = field(default=random, repr=False)
    _submission_count: int = field(default=0, init=False)
    _connected: bool = field(default=False, init=False)
    _open_requests: dict[str, ExecutionRequest] = field(default_factory=dict, init=False)
    _filled_quantities: dict[str, float] = field(default_factory=dict, init=False)
    _pending_terminal_reports: list[ExecutionReport] = field(default_factory=list, init=False)
    _recovery_reconciliations: list[BrokerRecoveryReconciliation] = field(default_factory=list, init=False)
    _retry_results: dict[str, RetryResult[Any]] = field(default_factory=dict, init=False)

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
        self._pending_terminal_reports = [
            report for report in self._pending_terminal_reports if report.symbol not in symbols
        ]

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
        self.validate_recovery_state(recovery_state)
        if recovery_state is None:
            self._open_requests = {}
            self._filled_quantities = {}
            self._pending_terminal_reports = []
            self._recovery_reconciliations = []
            return

        self._ensure_connected()
        open_orders_by_id = self._broker_open_orders_by_id(strict=True)
        staged_open_requests: dict[str, ExecutionRequest] = {}
        staged_filled_quantities: dict[str, float] = {}
        staged_reports: list[ExecutionReport] = []
        reconciliations: list[BrokerRecoveryReconciliation] = []
        for recovered in recovery_state.open_orders:
            order_id = recovered.external_order_id
            order = open_orders_by_id.get(order_id)
            if order is None:
                try:
                    order = self._execute_read(
                        "recovery_order_lookup",
                        lambda: self._run_async(self.broker.get_order(order_id)),
                    )
                except Exception as exc:
                    raise BrokerRecoveryError(
                        f"broker lookup failed for recovered order {order_id}: {exc}", reconciliations
                    ) from exc
            if order is None:
                reconciliations.append(
                    BrokerRecoveryReconciliation(
                        order_id, recovered.request.symbol, "missing", "order not found at broker"
                    )
                )
                continue

            mismatch = self._recovery_order_mismatch(order, recovered.request)
            if mismatch is not None:
                reconciliations.append(
                    BrokerRecoveryReconciliation(order_id, recovered.request.symbol, "mismatched", mismatch)
                )
                raise BrokerRecoveryError(
                    f"recovered order {order_id} does not match broker state: {mismatch}", reconciliations
                )

            reports, terminal = self._reports_from_order(
                order,
                recovered.request,
                order_id,
                seen_quantity=float(recovered.filled_quantity),
            )
            staged_reports.extend(reports)
            if terminal:
                reconciliations.append(
                    BrokerRecoveryReconciliation(
                        order_id, recovered.request.symbol, "terminal", "broker order is terminal"
                    )
                )
                continue
            staged_open_requests[order_id] = recovered.request
            staged_filled_quantities[order_id] = max(
                float(recovered.filled_quantity), float(getattr(order, "filled_quantity", 0.0) or 0.0)
            )
            reconciliations.append(
                BrokerRecoveryReconciliation(order_id, recovered.request.symbol, "open", "broker order rehydrated")
            )

        self._open_requests = staged_open_requests
        self._filled_quantities = staged_filled_quantities
        self._pending_terminal_reports = staged_reports
        self._recovery_reconciliations = reconciliations

    def validate_recovery_state(
        self, recovery_state: BrokerRouterRecoveryState | None, symbols: tuple[str, ...] | None = None
    ) -> None:
        BrokerRecoveryCodec.validate(recovery_state, symbols)

    def recovery_reconciliations(self) -> list[BrokerRecoveryReconciliation]:
        return list(self._recovery_reconciliations)

    def health_check(self) -> dict[str, Any]:
        try:
            self._ensure_connected()
        except Exception as exc:
            return self._retry_failure_health("connection_retry_exhausted", exc)
        check_health = getattr(self.broker, "check_health", None)
        if callable(check_health):
            try:
                health = self._execute_read("health_check", lambda: self._run_async(check_health()))
            except Exception as exc:
                return self._retry_failure_health("health_retry_exhausted", exc)
            if isinstance(health, dict):
                normalized_health = dict(health)
                broker_open_order_count = normalized_health.get("open_order_count")
                normalized_health["open_order_count"] = len(self._open_requests)
                if broker_open_order_count != normalized_health["open_order_count"]:
                    normalized_health["broker_open_order_count"] = broker_open_order_count
                normalized_health["retry"] = self.retry_diagnostics()
                return normalized_health
        is_connected = getattr(self.broker, "is_connected", None)
        connected = bool(is_connected()) if callable(is_connected) else self._connected
        return {
            "connected": connected,
            "status": "healthy" if connected else "disconnected",
            "broker": self._broker_name(),
            "open_order_count": len(self._open_requests),
            "retry": self.retry_diagnostics(),
        }

    def reconciliation_snapshot(self) -> dict[str, Any]:
        try:
            self._ensure_connected()
        except Exception as exc:
            return self._retry_failure_health("connection_retry_exhausted", exc)
        reconcile = getattr(self.broker, "reconciliation_snapshot", None)
        if not callable(reconcile):
            return {
                **self.health_check(),
                "positions": {},
                "open_order_ids": list(self._open_requests),
            }
        try:
            snapshot = self._execute_read("reconciliation", lambda: self._run_async(reconcile()))
        except Exception as exc:
            return self._retry_failure_health("reconciliation_retry_exhausted", exc)
        if not isinstance(snapshot, dict):
            raise RuntimeError("broker returned an invalid reconciliation snapshot")
        return {**dict(snapshot), "retry": self.retry_diagnostics()}

    def retry_diagnostics(self) -> dict[str, dict[str, Any]]:
        return {operation: result.to_dict() for operation, result in self._retry_results.items()}

    def _broker_open_orders_by_id(self, *, strict: bool = False) -> dict[str, Any]:
        get_orders = getattr(self.broker, "get_orders", None)
        if not callable(get_orders):
            adapter = getattr(self.broker, "adapter", None)
            get_orders = getattr(adapter, "get_orders", None)
        if not callable(get_orders):
            return {}
        try:
            orders = self._execute_read(
                "open_orders",
                lambda: self._run_async(get_orders(status="open")),
            )
        except Exception as exc:
            if strict:
                raise RuntimeError(f"failed to query broker open orders: {exc}") from exc
            return {}
        if not isinstance(orders, list):
            if strict:
                raise RuntimeError("broker returned an invalid open-order collection")
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

        def connect() -> bool:
            connected = bool(self._run_async(self.broker.connect()))
            if not connected:
                raise ConnectionError("broker connection failed")
            return True

        self._execute_retry("connect", self.connection_retry_policy, connect)
        self._connected = True

    def _execute_read(self, operation: str, callback: Callable[[], Any]) -> Any:
        return self._execute_retry(operation, self.read_retry_policy, callback)

    def _execute_retry(self, operation: str, policy: RetryPolicy, callback: Callable[[], Any]) -> Any:
        result = RetryExecutor(
            policy,
            wait=self.retry_wait,
            clock=self.retry_clock,
            random_source=self.retry_random_source,
        ).execute(callback)
        self._retry_results[operation] = result
        return result.unwrap()

    def _retry_failure_health(self, status: str, error: Exception) -> dict[str, Any]:
        return {
            "connected": False,
            "status": status,
            "broker": self._broker_name(),
            "open_order_count": len(self._open_requests),
            "error": str(error),
            "retry": self.retry_diagnostics(),
        }

    def _submit_order(self, request: ExecutionRequest) -> Any:
        side = BrokerOrderSide.BUY if request.action == TradeAction.BUY else BrokerOrderSide.SELL
        order_type = BrokerOrderType.LIMIT if self.prefer_limit_orders else BrokerOrderType.MARKET
        limit_price = self._limit_price(request) if order_type is BrokerOrderType.LIMIT else None
        submit_order = self.broker.submit_order
        kwargs: dict[str, Any] = {"order_type": order_type, "limit_price": limit_price}
        if "client_order_id" in inspect.signature(submit_order).parameters:
            kwargs["client_order_id"] = request.client_order_id
        return self._run_async(submit_order(request.symbol, float(request.quantity), side, **kwargs))

    def _reports_from_order(
        self,
        order: Any,
        request: ExecutionRequest,
        order_id: str,
        *,
        seen_quantity: float | None = None,
    ) -> tuple[list[ExecutionReport], bool]:
        status = self._order_status_value(getattr(order, "status", None))
        reports: list[ExecutionReport] = []
        total_quantity = float(getattr(order, "quantity", request.quantity) or request.quantity)
        filled_quantity = float(getattr(order, "filled_quantity", 0.0) or 0.0)
        update_live_tracking = seen_quantity is None
        previously_filled = self._filled_quantities.get(order_id, 0.0) if seen_quantity is None else seen_quantity
        newly_filled = max(filled_quantity - previously_filled, 0.0)
        timestamp = getattr(order, "timestamp", None)
        timestamp_ns = self._timestamp_ns(timestamp, request.executable_timestamp_ns)

        if newly_filled > 0.0:
            fill_price = float(
                getattr(order, "average_price", None) or getattr(order, "price", None) or self._touch_price(request)
            )
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
                    reason="broker reported partial fill"
                    if filled_quantity < total_quantity
                    else "broker reported fill",
                    timestamp_ns=timestamp_ns,
                    client_order_id=request.client_order_id,
                    external_order_id=order_id,
                )
            )
            if update_live_tracking:
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
                    client_order_id=request.client_order_id,
                    external_order_id=order_id,
                )
            )
            terminal = True
        elif status == "filled" and filled_quantity >= total_quantity:
            terminal = True

        return reports, terminal

    @staticmethod
    def _recovery_order_mismatch(order: Any, request: ExecutionRequest) -> str | None:
        broker_symbol = str(getattr(order, "symbol", ""))
        if broker_symbol and broker_symbol != request.symbol:
            return f"symbol {broker_symbol} != {request.symbol}"
        broker_quantity = float(getattr(order, "quantity", request.quantity) or request.quantity)
        if not math.isclose(broker_quantity, float(request.quantity)):
            return f"quantity {broker_quantity} != {request.quantity}"
        broker_side = str(getattr(getattr(order, "side", None), "value", getattr(order, "side", ""))).lower()
        expected_side = "buy" if request.action == TradeAction.BUY else "sell"
        if broker_side and broker_side != expected_side:
            return f"side {broker_side} != {expected_side}"
        return None

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
            client_order_id=request.client_order_id,
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
        connection_retry_policy: RetryPolicy | None = None,
        read_retry_policy: RetryPolicy | None = None,
        retry_wait: Callable[[float], None] = sleep,
        retry_clock: Callable[[], int] = time_ns,
        retry_random_source: Callable[[], float] = random,
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
            connection_retry_policy=connection_retry_policy
            or RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0.5,
                maximum_delay_seconds=5.0,
            ),
            read_retry_policy=read_retry_policy
            or RetryPolicy(
                max_attempts=3,
                initial_delay_seconds=0.25,
                maximum_delay_seconds=2.0,
            ),
            retry_wait=retry_wait,
            retry_clock=retry_clock,
            retry_random_source=retry_random_source,
        )
