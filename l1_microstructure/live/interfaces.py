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