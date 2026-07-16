"""Protocols for successor-package paper and live runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from l1_microstructure.execution import ExecutionReport, ExecutionRequest


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    symbols: tuple[str, ...]
    mode: str
    latency_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.symbols) != 1:
            raise ValueError(
                "legacy runner supports exactly one symbol; use ProductionRuntime for multi-symbol operation"
            )


@dataclass(frozen=True, slots=True)
class RouteAcknowledgement:
    external_order_id: str
    status: str
    reason: str = "accepted"
    metadata: dict[str, Any] = field(default_factory=dict)


class PaperTradingRunner(Protocol):
    def start(self, config: RunnerConfig) -> None:
        """Start a standalone paper or live event loop for the L1 framework."""

    def stop(self) -> None:
        """Stop the standalone paper or live event loop."""


class OrderRouter(Protocol):
    def submit(self, request: ExecutionRequest) -> RouteAcknowledgement:
        """Submit an execution request to an external route boundary."""

    def poll(self, symbols: tuple[str, ...]) -> list[ExecutionReport]:
        """Return newly available execution reports for the tracked symbols."""

    def stop(self) -> None:
        """Stop the route boundary and release any underlying resources."""


class ProductionOrderRouter(OrderRouter, Protocol):
    def cancel(self, order_id: str) -> bool:
        """Cancel an open external order."""

    def open_order_ids(self) -> list[str]:
        """Return every externally open order tracked by the router."""

    def health_check(self) -> dict[str, Any]:
        """Return broker connectivity and account-health information."""

    def reconciliation_snapshot(self) -> dict[str, Any]:
        """Return broker positions and open orders for startup reconciliation."""

    def snapshot_recovery_state(self) -> Any | None:
        """Return the typed state required to recover tracked broker orders."""

    def validate_recovery_state(self, state: Any | None, symbols: tuple[str, ...]) -> None:
        """Validate durable recovery state before it can mutate router tracking."""

    def restore_recovery_state(self, state: Any | None) -> None:
        """Rehydrate tracked broker orders from validated durable state."""

    def recovery_reconciliations(self) -> list[Any]:
        """Return the broker result for each attempted order rehydration."""
