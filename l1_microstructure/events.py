"""Normalized top-of-book events for the L1 state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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

    @property
    def kind(self) -> EventKind:
        return EventKind.TRADE


MarketEvent: TypeAlias = QuoteEvent | TradeEvent


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

    @property
    def spread(self) -> float:
        return max(self.ask_price - self.bid_price, 0.0)

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
