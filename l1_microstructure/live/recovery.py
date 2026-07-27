"""Typed recovery contracts for routed-live and broker state."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite, isnan
from typing import Any, Callable

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.decision import PosteriorEstimate, TradeAction, TradeIntent
from l1_microstructure.events import BookSnapshot
from l1_microstructure.execution import ExecutionReport, ExecutionRequest
from l1_microstructure.features import (
    FlickerState,
    ObservedState,
    PressureState,
    SpreadState,
    VolatilityState,
)
from l1_microstructure.regime import MicrostructureRegime
from l1_microstructure.recovery import StateMachineRecoveryCodec, StateMachineRecoverySnapshot
from l1_microstructure.transitions import EdgeKey

from .interfaces import RouteAcknowledgement


BROKER_RECOVERY_VERSION = 1
ROUTED_LIVE_RECOVERY_VERSION = 1


@dataclass(frozen=True, slots=True)
class BrokerOpenOrderRecovery:
    external_order_id: str
    request: ExecutionRequest
    filled_quantity: float = 0.0


@dataclass(frozen=True, slots=True)
class BrokerRouterRecoveryState:
    open_orders: list[BrokerOpenOrderRecovery]
    version: int = BROKER_RECOVERY_VERSION


@dataclass(frozen=True, slots=True)
class BrokerRecoveryReconciliation:
    external_order_id: str
    symbol: str
    status: str
    detail: str


class BrokerRecoveryError(RuntimeError):
    """Raised when broker state cannot be safely reconciled."""

    def __init__(self, message: str, reconciliations: list[BrokerRecoveryReconciliation]):
        super().__init__(message)
        self.reconciliations = tuple(reconciliations)


@dataclass(frozen=True, slots=True)
class RoutedLiveRecoverySnapshot:
    machine_snapshot: StateMachineRecoverySnapshot
    runtime_artifacts: RuntimeArtifactBundle
    route_acknowledgements: list[RouteAcknowledgement]
    execution_reports: list[ExecutionReport]
    symbols: tuple[str, ...]
    router_recovery_state: Any | None = None
    version: int = ROUTED_LIVE_RECOVERY_VERSION


class BrokerRecoveryCodec:
    """Serialize and validate durable broker recovery state."""

    @classmethod
    def to_dict(cls, state: BrokerRouterRecoveryState) -> dict[str, Any]:
        cls.validate(state)
        return {
            "version": state.version,
            "open_orders": [
                {
                    "external_order_id": recovered.external_order_id,
                    "filled_quantity": recovered.filled_quantity,
                    "request": cls.request_to_dict(recovered.request),
                }
                for recovered in state.open_orders
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> BrokerRouterRecoveryState:
        if not isinstance(payload, dict):
            raise TypeError("broker recovery payload must be an object")
        try:
            state = BrokerRouterRecoveryState(
                version=int(payload["version"]),
                open_orders=[
                    BrokerOpenOrderRecovery(
                        external_order_id=str(recovered["external_order_id"]),
                        filled_quantity=float(recovered.get("filled_quantity", 0.0)),
                        request=cls.request_from_dict(recovered["request"]),
                    )
                    for recovered in payload["open_orders"]
                ],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("broker recovery payload is malformed") from exc
        cls.validate(state)
        return state

    @staticmethod
    def validate(state: BrokerRouterRecoveryState | None, symbols: tuple[str, ...] | None = None) -> None:
        if state is None:
            return
        if not isinstance(state, BrokerRouterRecoveryState):
            raise TypeError("broker recovery requires a BrokerRouterRecoveryState")
        if state.version != BROKER_RECOVERY_VERSION:
            raise ValueError(f"unsupported broker recovery version {state.version}; expected {BROKER_RECOVERY_VERSION}")
        if not isinstance(state.open_orders, list):
            raise TypeError("broker recovery open orders must be a list")

        allowed_symbols = set(symbols or ())
        order_ids: set[str] = set()
        client_order_ids: set[str] = set()
        for recovered in state.open_orders:
            if not isinstance(recovered, BrokerOpenOrderRecovery):
                raise TypeError("broker recovery contains an invalid open-order record")
            order_id = recovered.external_order_id.strip()
            if not order_id or order_id in order_ids:
                raise ValueError("broker recovery contains a missing or duplicate external order id")
            order_ids.add(order_id)

            request = recovered.request
            if not isinstance(request, ExecutionRequest):
                raise TypeError("broker recovery contains an invalid execution request")
            if request.quantity <= 0 or request.executable_timestamp_ns < request.decision_timestamp_ns:
                raise ValueError("broker recovery contains an invalid execution request")
            if request.action not in {TradeAction.BUY, TradeAction.SELL} or request.intent.action is not request.action:
                raise ValueError("broker recovery request has an invalid routed action")
            if request.symbol != request.expected_state.symbol:
                raise ValueError("broker recovery request symbol does not match its expected state")
            state = request.expected_state
            if state.book.symbol != request.symbol or state.book.timestamp_ns > state.timestamp_ns:
                raise ValueError("broker recovery request contains inconsistent book state")
            finite_state_values = (
                state.book.bid_price,
                state.book.ask_price,
                state.spread_norm,
                state.quote_pressure,
                state.trade_pressure,
                state.flicker_intensity,
                state.realized_volatility,
            )
            if (
                not all(isfinite(float(value)) for value in finite_state_values)
                or state.book.bid_price <= 0.0
                or state.book.ask_price < state.book.bid_price
                or state.book.bid_size < 0
                or state.book.ask_size < 0
            ):
                raise ValueError("broker recovery request contains invalid observed state")
            if allowed_symbols and request.symbol not in allowed_symbols:
                raise ValueError(f"broker recovery contains unexpected symbol {request.symbol}")
            if not request.client_order_id or request.client_order_id in client_order_ids:
                raise ValueError("broker recovery contains a missing or duplicate client order id")
            client_order_ids.add(request.client_order_id)

            filled_quantity = float(recovered.filled_quantity)
            if not isfinite(filled_quantity) or filled_quantity < 0.0 or filled_quantity > request.quantity:
                raise ValueError("broker recovery contains an invalid filled quantity")

    @classmethod
    def request_to_dict(cls, request: ExecutionRequest) -> dict[str, Any]:
        state = request.expected_state
        intent = request.intent
        return {
            "symbol": request.symbol,
            "action": request.action.value,
            "quantity": request.quantity,
            "decision_timestamp_ns": request.decision_timestamp_ns,
            "executable_timestamp_ns": request.executable_timestamp_ns,
            "client_order_id": request.client_order_id,
            "expected_state": {
                "symbol": state.symbol,
                "timestamp_ns": state.timestamp_ns,
                "book": {
                    "symbol": state.book.symbol,
                    "timestamp_ns": state.book.timestamp_ns,
                    "bid_price": state.book.bid_price,
                    "ask_price": state.book.ask_price,
                    "bid_size": state.book.bid_size,
                    "ask_size": state.book.ask_size,
                },
                "spread_norm": state.spread_norm,
                "quote_pressure": state.quote_pressure,
                "trade_pressure": state.trade_pressure,
                "flicker_intensity": state.flicker_intensity,
                "realized_volatility": state.realized_volatility,
                "spread_state": state.spread_state.value,
                "quote_state": state.quote_state.value,
                "trade_state": state.trade_state.value,
                "flicker_state": state.flicker_state.value,
                "volatility_state": state.volatility_state.value,
            },
            "intent": {
                "action": intent.action.value,
                "edge": {
                    "from_state": intent.edge.from_state,
                    "to_state": intent.edge.to_state,
                    "regime": intent.edge.regime.value,
                },
                "posterior": {
                    "mean_bps": cls._float_to_json(intent.posterior.mean_bps),
                    "std_bps": cls._float_to_json(intent.posterior.std_bps),
                    "probability_up": cls._float_to_json(intent.posterior.probability_up),
                    "probability_down": cls._float_to_json(intent.posterior.probability_down),
                    "threshold_bps": cls._float_to_json(intent.posterior.threshold_bps),
                    "sample_count": intent.posterior.sample_count,
                },
                "expected_holding_time_ns": intent.expected_holding_time_ns,
                "reason": intent.reason,
                "observation_confidence": intent.observation_confidence,
            },
        }

    @classmethod
    def request_from_dict(cls, payload: dict[str, Any]) -> ExecutionRequest:
        state_payload = payload["expected_state"]
        book_payload = state_payload["book"]
        intent_payload = payload["intent"]
        edge_payload = intent_payload["edge"]
        posterior_payload = intent_payload["posterior"]
        state = ObservedState(
            symbol=str(state_payload["symbol"]),
            timestamp_ns=int(state_payload["timestamp_ns"]),
            book=BookSnapshot(
                symbol=str(book_payload["symbol"]),
                timestamp_ns=int(book_payload["timestamp_ns"]),
                bid_price=float(book_payload["bid_price"]),
                ask_price=float(book_payload["ask_price"]),
                bid_size=int(book_payload["bid_size"]),
                ask_size=int(book_payload["ask_size"]),
            ),
            spread_norm=float(state_payload["spread_norm"]),
            quote_pressure=float(state_payload["quote_pressure"]),
            trade_pressure=float(state_payload["trade_pressure"]),
            flicker_intensity=float(state_payload["flicker_intensity"]),
            realized_volatility=float(state_payload["realized_volatility"]),
            spread_state=SpreadState(str(state_payload["spread_state"])),
            quote_state=PressureState(str(state_payload["quote_state"])),
            trade_state=PressureState(str(state_payload["trade_state"])),
            flicker_state=FlickerState(str(state_payload["flicker_state"])),
            volatility_state=VolatilityState(str(state_payload["volatility_state"])),
        )
        intent = TradeIntent(
            action=TradeAction(str(intent_payload["action"])),
            edge=EdgeKey(
                from_state=str(edge_payload["from_state"]),
                to_state=str(edge_payload["to_state"]),
                regime=MicrostructureRegime(str(edge_payload["regime"])),
            ),
            posterior=PosteriorEstimate(
                mean_bps=cls._float_from_json(posterior_payload["mean_bps"]),
                std_bps=cls._float_from_json(posterior_payload["std_bps"]),
                probability_up=cls._float_from_json(posterior_payload["probability_up"]),
                probability_down=cls._float_from_json(posterior_payload["probability_down"]),
                threshold_bps=cls._float_from_json(posterior_payload["threshold_bps"]),
                sample_count=int(posterior_payload["sample_count"]),
            ),
            expected_holding_time_ns=int(intent_payload["expected_holding_time_ns"]),
            reason=str(intent_payload["reason"]),
            observation_confidence=float(intent_payload.get("observation_confidence", 1.0)),
        )
        return ExecutionRequest(
            symbol=str(payload["symbol"]),
            action=TradeAction(str(payload["action"])),
            quantity=int(payload["quantity"]),
            decision_timestamp_ns=int(payload["decision_timestamp_ns"]),
            executable_timestamp_ns=int(payload["executable_timestamp_ns"]),
            expected_state=state,
            intent=intent,
            client_order_id=str(payload["client_order_id"]),
        )

    @staticmethod
    def _float_to_json(value: float) -> float | str:
        number = float(value)
        if isfinite(number):
            return number
        if isnan(number):
            raise ValueError("broker recovery cannot serialize NaN")
        return "Infinity" if number > 0.0 else "-Infinity"

    @staticmethod
    def _float_from_json(value: Any) -> float:
        if value == "Infinity":
            return inf
        if value == "-Infinity":
            return -inf
        if value == "NaN":
            raise ValueError("broker recovery cannot deserialize NaN")
        return float(value)


class RoutedLiveRecoveryCodec:
    """Validate a complete routed-live recovery envelope before restore."""

    @staticmethod
    def validate(
        machine: Any,
        snapshot: RoutedLiveRecoverySnapshot,
        symbols: tuple[str, ...],
        validate_router_state: Callable[[Any | None, tuple[str, ...]], None],
    ) -> None:
        if not isinstance(snapshot, RoutedLiveRecoverySnapshot):
            raise TypeError("routed-live recovery requires a RoutedLiveRecoverySnapshot")
        if snapshot.version != ROUTED_LIVE_RECOVERY_VERSION:
            raise ValueError(
                f"unsupported routed-live recovery version {snapshot.version}; expected {ROUTED_LIVE_RECOVERY_VERSION}"
            )
        if snapshot.symbols != symbols:
            raise ValueError(
                f"routed-live recovery symbols {snapshot.symbols} do not match requested symbols {symbols}"
            )
        if not isinstance(snapshot.runtime_artifacts, RuntimeArtifactBundle):
            raise TypeError("routed-live recovery contains invalid runtime artifacts")
        if not isinstance(snapshot.route_acknowledgements, list) or not all(
            isinstance(acknowledgement, RouteAcknowledgement) and bool(acknowledgement.external_order_id.strip())
            for acknowledgement in snapshot.route_acknowledgements
        ):
            raise TypeError("routed-live recovery contains invalid route acknowledgements")
        if not isinstance(snapshot.execution_reports, list) or not all(
            isinstance(report, ExecutionReport) and report.symbol in symbols for report in snapshot.execution_reports
        ):
            raise TypeError("routed-live recovery contains invalid execution reports")

        StateMachineRecoveryCodec.validate(machine, snapshot.machine_snapshot)
        validate_router_state(snapshot.router_recovery_state, symbols)
