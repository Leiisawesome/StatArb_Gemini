"""
Streaming volume-clock bucketer for real-time trade processing.

Adapts the offline VolumeClockBucketer logic to operate trade-by-trade
with no look-ahead. Maintains per-symbol state and emits ImbalanceEvent
when a completed bucket has |flow_imbalance| exceeding the frozen p95 threshold.

Integer arithmetic for cumulative volume accumulation guarantees
deterministic replay consistency with the offline bucketer.

Spec: v1.7-SHADOW
Build Plan: v4-FINAL, Step 1
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

import numpy as np

from core_engine.microstructure.shadow.constants import (
    SHADOW_CONSTANTS_VERSION,
    TARGET_BUCKETS_PER_DAY,
)
from core_engine.microstructure.shadow.types import ImbalanceEvent, Quote

logger = logging.getLogger(__name__)


@dataclass
class _BucketState:
    """Accumulating state for the current in-progress bucket."""
    bucket_id: int = 0
    cumulative_volume: int = 0
    num_trades: int = 0

    # OHLCV
    open_price: float = 0.0
    high_price: float = -math.inf
    low_price: float = math.inf
    close_price: float = 0.0
    dollar_volume: float = 0.0

    # Flow classification
    buy_volume: int = 0
    sell_volume: int = 0
    indeterminate_volume: int = 0

    # Classification quality tracking
    quote_rule_count: int = 0
    tick_rule_count: int = 0
    indeterminate_count: int = 0

    # Timestamps
    first_trade_ns: int = 0
    last_trade_ns: int = 0

    def reset(self, next_bucket_id: int) -> None:
        self.bucket_id = next_bucket_id
        self.cumulative_volume = 0
        self.num_trades = 0
        self.open_price = 0.0
        self.high_price = -math.inf
        self.low_price = math.inf
        self.close_price = 0.0
        self.dollar_volume = 0.0
        self.buy_volume = 0
        self.sell_volume = 0
        self.indeterminate_volume = 0
        self.quote_rule_count = 0
        self.tick_rule_count = 0
        self.indeterminate_count = 0
        self.first_trade_ns = 0
        self.last_trade_ns = 0


# Lee-Ready classification method constants (matching offline classifier)
_METHOD_QUOTE: int = 0
_METHOD_TICK: int = 1
_METHOD_INDETERMINATE: int = 2


class StreamingLeeReady:
    """Trade-by-trade Lee-Ready classification using latest NBBO.

    Replicates the offline LeeReadyClassifier logic in streaming form:
    1. Quote rule: price > midpoint -> BUY, price < midpoint -> SELL
    2. Tick rule: if at midpoint, compare to last different price
    3. Indeterminate: no quote or no price history
    """

    def __init__(self) -> None:
        self._last_price: Optional[float] = None
        self._last_direction: int = 0  # last known tick direction

    def classify(
        self, price: float, midpoint: float
    ) -> tuple[int, int]:
        """Classify a single trade.

        Args:
            price: trade price
            midpoint: current NBBO midpoint (0 or NaN if no valid quote)

        Returns:
            (sign, method) where sign is -1/0/+1 and method is 0/1/2
        """
        sign = 0
        method = _METHOD_INDETERMINATE

        if midpoint > 0 and math.isfinite(midpoint):
            diff = price - midpoint
            if diff > 1e-10:
                sign = 1
                method = _METHOD_QUOTE
            elif diff < -1e-10:
                sign = -1
                method = _METHOD_QUOTE
            else:
                # At midpoint — apply tick rule
                if self._last_direction != 0:
                    sign = self._last_direction
                    method = _METHOD_TICK

        # Update tick direction for future at-midpoint trades
        if self._last_price is not None:
            price_diff = price - self._last_price
            if price_diff > 1e-10:
                self._last_direction = 1
            elif price_diff < -1e-10:
                self._last_direction = -1
        self._last_price = price

        return sign, method

    def reset(self) -> None:
        self._last_price = None
        self._last_direction = 0


class StreamingVolumeBucketer:
    """Real-time volume-clock bucketing from streaming trades.

    Maintains per-symbol state and emits ImbalanceEvent when a completed
    bucket has |flow_imbalance| exceeding the frozen p95 threshold.

    Integer arithmetic for volume accumulation ensures deterministic
    consistency with the offline VolumeClockBucketer.
    """

    def __init__(
        self,
        symbol: str,
        adv_shares: int,
        imbalance_threshold: float,
    ) -> None:
        self._symbol = symbol
        self._adv_shares = adv_shares
        self._imbalance_threshold = imbalance_threshold
        self._bucket_volume = max(1, adv_shares // TARGET_BUCKETS_PER_DAY)

        self._state = _BucketState()
        self._latest_quote: Optional[Quote] = None
        self._classifier = StreamingLeeReady()

        # Spread tracking across bucket
        self._spread_bps_samples: List[float] = []

        # Daily statistics
        self._daily_bucket_count: int = 0
        self._daily_event_count: int = 0
        self._total_trades_classified: int = 0
        self._total_quote_rule: int = 0
        self._total_tick_rule: int = 0
        self._total_indeterminate: int = 0

        logger.info(
            "StreamingVolumeBucketer init: %s, ADV=%d, bucket_vol=%d, "
            "imbalance_threshold=%.4f",
            symbol, adv_shares, self._bucket_volume, imbalance_threshold,
        )

    def on_trade(
        self,
        timestamp_ns: int,
        price: float,
        size: int,
    ) -> Optional[ImbalanceEvent]:
        """Process a single trade. Returns ImbalanceEvent if bucket completes
        with extreme imbalance.

        Lee-Ready classification is performed internally using the latest NBBO.
        """
        if size <= 0 or price <= 0:
            return None

        # Classify against latest NBBO
        midpoint = 0.0
        if self._latest_quote is not None and not self._latest_quote.is_locked:
            midpoint = self._latest_quote.midpoint

        sign, method = self._classifier.classify(price, midpoint)

        self._total_trades_classified += 1
        if method == _METHOD_QUOTE:
            self._total_quote_rule += 1
        elif method == _METHOD_TICK:
            self._total_tick_rule += 1
        else:
            self._total_indeterminate += 1

        return self._accumulate_trade(timestamp_ns, price, size, sign, method)

    def on_quote(
        self,
        timestamp_ns: int,
        bid: float,
        ask: float,
        bid_size: int,
        ask_size: int,
    ) -> None:
        """Update the latest NBBO quote used for Lee-Ready classification."""
        self._latest_quote = Quote(
            symbol=self._symbol,
            timestamp_ns=timestamp_ns,
            bid_price=bid,
            ask_price=ask,
            bid_size=bid_size,
            ask_size=ask_size,
        )

        # Track spread in current bucket
        if bid > 0 and ask > bid:
            mid = (bid + ask) / 2.0
            spread_bps = (ask - bid) / mid * 10_000
            self._spread_bps_samples.append(spread_bps)

    def get_classification_confidence(self) -> float:
        """Fraction of trades classified as BUY or SELL (not INDETERMINATE)."""
        total = self._total_trades_classified
        if total == 0:
            return 0.0
        classified = self._total_quote_rule + self._total_tick_rule
        return classified / total

    def get_tick_rule_fallback_pct(self) -> float:
        """Fraction of trades classified via tick rule (fallback)."""
        total = self._total_trades_classified
        if total == 0:
            return 0.0
        return self._total_tick_rule / total

    def reset_daily(self) -> None:
        """Reset daily counters. Call at start of each trading day."""
        self._state.reset(0)
        self._classifier.reset()
        self._spread_bps_samples.clear()
        self._daily_bucket_count = 0
        self._daily_event_count = 0
        self._total_trades_classified = 0
        self._total_quote_rule = 0
        self._total_tick_rule = 0
        self._total_indeterminate = 0

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def bucket_volume(self) -> int:
        return self._bucket_volume

    @property
    def daily_bucket_count(self) -> int:
        return self._daily_bucket_count

    @property
    def daily_event_count(self) -> int:
        return self._daily_event_count

    # ── Internal ──────────────────────────────────────────────────────

    def _accumulate_trade(
        self,
        timestamp_ns: int,
        price: float,
        size: int,
        sign: int,
        method: int,
    ) -> Optional[ImbalanceEvent]:
        """Add a classified trade to the current bucket. Returns event if bucket
        completes with extreme imbalance."""
        s = self._state

        if s.num_trades == 0:
            s.open_price = price
            s.first_trade_ns = timestamp_ns

        s.num_trades += 1
        s.cumulative_volume += size
        s.close_price = price
        s.last_trade_ns = timestamp_ns
        s.dollar_volume += price * size

        if price > s.high_price:
            s.high_price = price
        if price < s.low_price:
            s.low_price = price

        if sign > 0:
            s.buy_volume += size
        elif sign < 0:
            s.sell_volume += size
        else:
            s.indeterminate_volume += size

        if method == _METHOD_QUOTE:
            s.quote_rule_count += 1
        elif method == _METHOD_TICK:
            s.tick_rule_count += 1
        else:
            s.indeterminate_count += 1

        # Check if bucket is complete
        if s.cumulative_volume >= self._bucket_volume:
            event = self._finalize_bucket()
            return event

        return None

    def _finalize_bucket(self) -> Optional[ImbalanceEvent]:
        """Finalize the current bucket, compute flow metrics, check threshold.

        Carries over excess volume to the next bucket to match offline bucketer
        behavior (which uses absolute cumulative thresholds).
        """
        s = self._state

        if s.cumulative_volume == 0:
            s.reset(s.bucket_id + 1)
            return None

        unsigned_volume = s.cumulative_volume
        signed_volume = s.buy_volume - s.sell_volume
        flow_imbalance = signed_volume / unsigned_volume

        # VWAP
        vwap = s.dollar_volume / unsigned_volume if unsigned_volume > 0 else s.close_price

        # Classification confidence for this bucket
        classified = s.quote_rule_count + s.tick_rule_count
        total = s.num_trades
        bucket_confidence = classified / total if total > 0 else 0.0
        bucket_tick_pct = s.tick_rule_count / total if total > 0 else 0.0

        # Median spread
        if self._spread_bps_samples:
            sorted_spreads = sorted(self._spread_bps_samples)
            mid_idx = len(sorted_spreads) // 2
            median_spread_bps = sorted_spreads[mid_idx]
        else:
            median_spread_bps = 0.0

        # Quote context
        bid_at_end = self._latest_quote.bid_price if self._latest_quote else 0.0
        ask_at_end = self._latest_quote.ask_price if self._latest_quote else 0.0

        self._daily_bucket_count += 1
        completed_bucket_id = s.bucket_id
        completed_date = date.today()
        bucket_ns = s.last_trade_ns

        # Reset spread samples for next bucket
        self._spread_bps_samples.clear()

        event: Optional[ImbalanceEvent] = None

        # Check extreme imbalance threshold
        if abs(flow_imbalance) >= self._imbalance_threshold:
            self._daily_event_count += 1
            event = ImbalanceEvent(
                symbol=self._symbol,
                bucket_id=completed_bucket_id,
                event_timestamp_ns=bucket_ns,
                flow_imbalance=flow_imbalance,
                bucket_volume=unsigned_volume,
                num_trades=total,
                vwap=vwap,
                bid_at_end=bid_at_end,
                ask_at_end=ask_at_end,
                median_spread_bps=median_spread_bps,
                classification_confidence=bucket_confidence,
                tick_rule_fallback_pct=bucket_tick_pct,
                bucket_date=completed_date,
            )
            logger.info(
                "Extreme imbalance event: %s bucket=%d imb=%.4f "
                "(threshold=%.4f) vol=%d trades=%d",
                self._symbol, completed_bucket_id, flow_imbalance,
                self._imbalance_threshold, unsigned_volume, total,
            )

        # Carry over excess volume to match offline bucketer's absolute thresholds.
        # The trade that crossed the boundary belongs to the completed bucket,
        # but its overshoot gives the next bucket a head start.
        overshoot = unsigned_volume - self._bucket_volume
        s.reset(completed_bucket_id + 1)
        if overshoot > 0:
            s.cumulative_volume = overshoot

        return event
