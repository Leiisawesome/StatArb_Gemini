"""Protocols for forward drift and censoring labels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol

from l1_microstructure.events import MarketEvent


@dataclass(frozen=True, slots=True)
class HorizonLabelRequest:
    symbol: str
    horizon_ns: int
    start_timestamp_ns: int
    reference_price: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DriftLabel:
    symbol: str
    start_timestamp_ns: int
    end_timestamp_ns: int
    realized_drift_bps: float
    censored: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class OutcomeLabeler(Protocol):
    def label(self, request: HorizonLabelRequest, events: Iterable[MarketEvent]) -> DriftLabel:
        """Resolve a forward drift label for a research horizon."""