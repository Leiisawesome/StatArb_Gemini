"""Normalized top-of-book events for the L1 state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import TypeAlias


class EventKind(str, Enum):
    QUOTE = "quote"
    TRADE = "trade"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class QuoteEvent:
    symbol: str
    timestamp_ns: int
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    exchange: str | None = None
    sequence_number: int | None = None

    def __post_init__(self) -> None:
        _validate_common_event_fields(self.symbol, self.timestamp_ns, self.sequence_number)
        if not isfinite(self.bid_price) or not isfinite(self.ask_price):
            raise ValueError("quote prices must be finite")
        if self.bid_price <= 0.0 or self.ask_price <= 0.0:
            raise ValueError("quote prices must be positive")
        if self.ask_price < self.bid_price:
            raise ValueError("quote ask price cannot be below bid price")
        if self.bid_size < 0 or self.ask_size < 0:
            raise ValueError("quote sizes cannot be negative")
        if self.bid_size + self.ask_size <= 0:
            raise ValueError("quote must contain positive displayed size")

    @property
    def kind(self) -> EventKind:
        return EventKind.QUOTE


@dataclass(frozen=True, slots=True)
class TradeEvent:
    symbol: str
    timestamp_ns: int
    price: float
    size: int
    side: TradeSide = TradeSide.UNKNOWN
    exchange: str | None = None
    sequence_number: int | None = None

    def __post_init__(self) -> None:
        _validate_common_event_fields(self.symbol, self.timestamp_ns, self.sequence_number)
        if not isfinite(self.price) or self.price <= 0.0:
            raise ValueError("trade price must be finite and positive")
        if self.size <= 0:
            raise ValueError("trade size must be positive")

    @property
    def kind(self) -> EventKind:
        return EventKind.TRADE


MarketEvent: TypeAlias = QuoteEvent | TradeEvent


def _validate_common_event_fields(symbol: str, timestamp_ns: int, sequence_number: int | None) -> None:
    if not symbol or not symbol.strip():
        raise ValueError("market-event symbol cannot be empty")
    if timestamp_ns < 0:
        raise ValueError("market-event timestamp cannot be negative")
    if sequence_number is not None and sequence_number < 0:
        raise ValueError("market-event sequence number cannot be negative")


def event_sort_key(event: MarketEvent) -> tuple[int, int, int]:
    """Return the deterministic, vendor-neutral ordering key for market events."""
    sequence_number = event.sequence_number if event.sequence_number is not None else (2**31 - 1)
    event_priority = 0 if isinstance(event, QuoteEvent) else 1
    return event.timestamp_ns, sequence_number, event_priority


@dataclass(frozen=True, slots=True)
class BookSnapshot:
    symbol: str
    timestamp_ns: int
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int

    def __post_init__(self) -> None:
        _validate_common_event_fields(self.symbol, self.timestamp_ns, None)
        if not isfinite(self.bid_price) or not isfinite(self.ask_price):
            raise ValueError("book prices must be finite")
        if self.bid_price <= 0.0 or self.ask_price <= 0.0:
            raise ValueError("book prices must be positive")
        if self.ask_price < self.bid_price:
            raise ValueError("book ask price cannot be below bid price")
        if self.bid_size < 0 or self.ask_size < 0 or self.bid_size + self.ask_size <= 0:
            raise ValueError("book must contain non-negative, positive-total size")

    @property
    def spread(self) -> float:
        return self.ask_price - self.bid_price

    @property
    def midpoint(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0

    @property
    def microprice(self) -> float:
        total_size = max(self.bid_size + self.ask_size, 1)
        return (self.bid_price * self.ask_size + self.ask_price * self.bid_size) / total_size

    @classmethod
    def from_quote(cls, quote: QuoteEvent) -> "BookSnapshot":
        return cls(
            symbol=quote.symbol,
            timestamp_ns=quote.timestamp_ns,
            bid_price=quote.bid_price,
            ask_price=quote.ask_price,
            bid_size=quote.bid_size,
            ask_size=quote.ask_size,
        )


def infer_trade_side(trade: TradeEvent, book: BookSnapshot | None) -> TradeSide:
    if trade.side is not TradeSide.UNKNOWN:
        return trade.side
    if book is None:
        return TradeSide.UNKNOWN
    if trade.price >= book.ask_price:
        return TradeSide.BUY
    if trade.price <= book.bid_price:
        return TradeSide.SELL
    if trade.price >= book.midpoint:
        return TradeSide.BUY
    return TradeSide.SELL
