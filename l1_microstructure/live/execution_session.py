"""Shared order-routing and execution-report coordination."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from l1_microstructure.execution import ExecutionReport, ExecutionRequest

from .interfaces import OrderRouter, RouteAcknowledgement


class ExecutionReportConsumer(Protocol):
    def ingest_execution_report(self, report: ExecutionReport) -> None:
        """Apply a broker execution report to strategy state."""


@dataclass(slots=True)
class RoutedExecutionService:
    """One routing path shared by embedded and supervised runtimes."""

    router: OrderRouter

    def submit(
        self,
        request: ExecutionRequest,
        *,
        before_submit: Callable[[ExecutionRequest], None] | None = None,
        after_submit: Callable[[ExecutionRequest, RouteAcknowledgement], None] | None = None,
    ) -> RouteAcknowledgement:
        if before_submit is not None:
            before_submit(request)
        acknowledgement = self.router.submit(request)
        if after_submit is not None:
            after_submit(request, acknowledgement)
        return acknowledgement

    def submit_all(self, requests: Iterable[ExecutionRequest]) -> list[RouteAcknowledgement]:
        return [self.submit(request) for request in requests]

    def poll(
        self,
        symbols: tuple[str, ...],
        *,
        consumer_for_symbol: Callable[[str], ExecutionReportConsumer | None],
        after_report: Callable[[ExecutionReport], None] | None = None,
    ) -> list[ExecutionReport]:
        reports = list(self.router.poll(symbols))
        for report in reports:
            consumer = consumer_for_symbol(report.symbol)
            if consumer is not None:
                consumer.ingest_execution_report(report)
            if after_report is not None:
                after_report(report)
        return reports

    def stop(self) -> None:
        self.router.stop()

    def cancel(self, order_id: str) -> bool:
        cancel = getattr(self.router, "cancel", None)
        return bool(cancel(order_id)) if callable(cancel) else False

    def open_order_ids(self) -> list[str]:
        open_order_ids = getattr(self.router, "open_order_ids", None)
        return list(open_order_ids()) if callable(open_order_ids) else []

    def health(self) -> dict[str, Any] | None:
        health_check = getattr(self.router, "health_check", None)
        if not callable(health_check):
            return None
        health = health_check()
        return dict(health) if isinstance(health, dict) else None

    def reconciliation_snapshot(self) -> dict[str, Any] | None:
        snapshot = getattr(self.router, "reconciliation_snapshot", None)
        if not callable(snapshot):
            return None
        value = snapshot()
        return dict(value) if isinstance(value, dict) else None

    def snapshot_recovery_state(self) -> Any | None:
        snapshot = getattr(self.router, "snapshot_recovery_state", None)
        return snapshot() if callable(snapshot) else None

    def restore_recovery_state(self, state: Any | None) -> None:
        restore = getattr(self.router, "restore_recovery_state", None)
        if callable(restore):
            restore(state)
