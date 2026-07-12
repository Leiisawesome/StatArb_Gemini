"""Typed recovery contracts for routed-live and broker state."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from l1_microstructure.artifacts import RuntimeArtifactBundle
from l1_microstructure.execution import ExecutionReport, ExecutionRequest
from l1_microstructure.recovery import StateMachineRecoveryCodec, StateMachineRecoverySnapshot

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
    """Validate broker recovery state without mutating a router."""

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
            if request.symbol != request.expected_state.symbol:
                raise ValueError("broker recovery request symbol does not match its expected state")
            if allowed_symbols and request.symbol not in allowed_symbols:
                raise ValueError(f"broker recovery contains unexpected symbol {request.symbol}")
            if not request.client_order_id or request.client_order_id in client_order_ids:
                raise ValueError("broker recovery contains a missing or duplicate client order id")
            client_order_ids.add(request.client_order_id)

            filled_quantity = float(recovered.filled_quantity)
            if not isfinite(filled_quantity) or filled_quantity < 0.0 or filled_quantity > request.quantity:
                raise ValueError("broker recovery contains an invalid filled quantity")


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
