"""Protocols for runtime monitoring and diagnostics emission."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    BROKER_CONNECTIVITY = "broker_connectivity"
    RECONCILIATION = "reconciliation"
    ORDER_ROUTING = "order_routing"
    MARKET_DATA = "market_data"
    RISK = "risk"
    RUNTIME = "runtime"


@dataclass(frozen=True, slots=True)
class OperationalAlert:
    timestamp_ns: int
    severity: AlertSeverity
    category: AlertCategory
    code: str
    message: str
    symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def deduplication_key(self) -> str:
        return f"{self.category.value}:{self.code}:{self.symbol or '*'}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_ns": self.timestamp_ns,
            "severity": self.severity.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "symbol": self.symbol,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    timestamp_ns: int
    state_label: str
    dominant_regime: str
    entropy: float
    alpha_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MonitoringSink(Protocol):
    def publish(self, snapshot: RuntimeSnapshot) -> None:
        """Emit runtime diagnostics for dashboards, logs, or alerts."""

    def publish_alert(self, alert: OperationalAlert) -> None:
        """Emit a typed operational alert."""


class AlertSink(Protocol):
    def publish_alert(self, alert: OperationalAlert) -> None:
        """Deliver a typed operational alert."""
