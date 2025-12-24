"""
LivePaperBrokerFacade (IBKR paper)
=================================

`core_engine.paper.engine.PaperTradingEngine` expects a `_paper_broker` object
for:

- `set_price(symbol, price)` and optionally `set_market_data(symbol, bar, ts)`
- `get_latest_quote(symbol)` (used as a lightweight price cache)
- `get_account_info()` / `get_position(symbol)` (used by risk/monitoring paths)

In live paper, **execution is routed via UnifiedExecutionEngine (LIVE)** to the
real broker (`IBKRAdapter`). This facade exists to provide:

- A fast, non-blocking price cache driven by Polygon events
- Cached account/position snapshots sourced from IBKR via explicit refresh calls
- Optional PositionBook MTM updates (internal SSOT convergence)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple, List

from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
from core_engine.type_definitions.broker_types import AccountInfo, Position
from core_engine.trading.position_book import IPositionBook


@dataclass(frozen=True)
class CachePolicy:
    account_ttl_seconds: float = 10.0
    positions_ttl_seconds: float = 10.0


class LivePaperBrokerFacade:
    """
    Thread-safe facade: fast reads inside engine loop; slow broker calls happen
    via explicit `refresh_*` methods called from background tasks.
    """

    def __init__(
        self,
        ibkr: IBKRAdapter,
        cache_policy: Optional[CachePolicy] = None,
        position_book: Optional[IPositionBook] = None,
    ):
        self._ibkr = ibkr
        self._policy = cache_policy or CachePolicy()
        self._position_book = position_book

        self._lock = threading.RLock()

        # Price cache from Polygon
        self._last_price: Dict[str, float] = {}
        self._last_price_ts: Dict[str, datetime] = {}

        # Optional last bar snapshot (for debugging/execution context)
        self._last_bar: Dict[str, Dict[str, Any]] = {}
        self._last_bar_ts: Dict[str, datetime] = {}

        # IBKR snapshots (cached)
        self._account: Optional[AccountInfo] = None
        self._account_ts: Optional[datetime] = None
        self._positions: Dict[str, Position] = {}
        self._positions_ts: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Polygon-driven pricing cache (fast path)
    # ------------------------------------------------------------------

    def set_price(self, symbol: str, price: float) -> None:
        sym = (symbol or "").upper()
        if not sym:
            return
        try:
            px = float(price)
        except Exception:
            return
        if px <= 0:
            return

        now = datetime.now(timezone.utc)
        with self._lock:
            self._last_price[sym] = px
            self._last_price_ts[sym] = now

        # Update PositionBook MTM (internal SSOT), best-effort.
        if self._position_book is not None:
            try:
                self._position_book.on_price_update({sym: Decimal(str(px))})
            except Exception:
                pass

    def set_market_data(self, symbol: str, bar: Dict[str, Any], market_timestamp: datetime) -> None:
        sym = (symbol or "").upper()
        if not sym:
            return
        ts = market_timestamp
        if ts is None:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        with self._lock:
            self._last_bar[sym] = dict(bar or {})
            self._last_bar_ts[sym] = ts

    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Return latest cached quote-like dict.

        Engine reads `last_price` and uses it for arrival/decision prices.
        """
        sym = (symbol or "").upper()
        if not sym:
            return None
        with self._lock:
            px = self._last_price.get(sym)
            ts = self._last_price_ts.get(sym)
        if px is None:
            return None
        return {
            "symbol": sym,
            "bid_price": 0.0,
            "ask_price": 0.0,
            "bid_size": 0.0,
            "ask_size": 0.0,
            "last_price": float(px),
            "timestamp": ts or datetime.now(timezone.utc),
        }

    def get_price_age_seconds(self, symbol: str) -> Optional[float]:
        sym = (symbol or "").upper()
        with self._lock:
            ts = self._last_price_ts.get(sym)
        if ts is None:
            return None
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds()

    # ------------------------------------------------------------------
    # IBKR snapshot cache (slow path via explicit refresh)
    # ------------------------------------------------------------------

    def refresh_account_info(self) -> AccountInfo:
        """
        Blocking call. Run it off the event loop (e.g., asyncio.to_thread()).
        """
        acc = self._ibkr.get_account_info()
        now = datetime.now(timezone.utc)
        with self._lock:
            self._account = acc
            self._account_ts = now
        return acc

    def refresh_positions(self) -> List[Position]:
        """
        Blocking call. Run it off the event loop (e.g., asyncio.to_thread()).
        """
        positions = self._ibkr.get_positions()
        now = datetime.now(timezone.utc)
        with self._lock:
            self._positions = {p.symbol.upper(): p for p in positions if p and p.symbol}
            self._positions_ts = now
        return positions

    def get_account_info(self) -> AccountInfo:
        """
        Fast path: return cached snapshot if present; otherwise trigger a blocking fetch.

        Note: In production runner, a background task should refresh periodically so
        the engine loop never blocks.
        """
        with self._lock:
            acc = self._account
        if acc is not None:
            return acc
        # Fallback: best-effort blocking fetch
        return self.refresh_account_info()

    def get_position(self, symbol: str) -> Optional[Position]:
        sym = (symbol or "").upper()
        if not sym:
            return None
        with self._lock:
            return self._positions.get(sym)

    def get_all_positions(self) -> Dict[str, Position]:
        with self._lock:
            return dict(self._positions)

    def snapshot_timestamps(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Returns (account_ts, positions_ts).
        """
        with self._lock:
            return self._account_ts, self._positions_ts


