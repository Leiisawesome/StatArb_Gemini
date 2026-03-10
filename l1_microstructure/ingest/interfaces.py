"""Ingestion-side protocols for L1 microstructure data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Protocol

from l1_microstructure.events import MarketEvent


@dataclass(frozen=True, slots=True)
class HistoricalBatchRequest:
    symbols: tuple[str, ...]
    trade_date: date
    include_quotes: bool = True
    include_trades: bool = True
    start_ns: int | None = None
    end_ns: int | None = None


@dataclass(frozen=True, slots=True)
class LiveSubscriptionRequest:
    symbols: tuple[str, ...]
    include_quotes: bool = True
    include_trades: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionFilter(Protocol):
    def accepts(self, symbol: str, timestamp_ns: int) -> bool:
        """Return True when an event belongs to the active research or trading session."""


class EventNormalizer(Protocol):
    def normalize(self, payload: dict[str, Any] | Any) -> MarketEvent | None:
        """Convert a vendor payload into a normalized L1 market event."""


class MarketDataSource(Protocol):
    def load_historical(self, request: HistoricalBatchRequest) -> Iterable[MarketEvent]:
        """Yield historical events in deterministic event-time order."""

    def subscribe_live(self, request: LiveSubscriptionRequest) -> Iterable[MarketEvent]:
        """Yield live events from a streaming L1 source."""