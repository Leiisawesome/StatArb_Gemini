"""Feature extraction and coarse-grained state projection for L1 data."""

from __future__ import annotations

from bisect import bisect_left, insort
from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import floor, log, sqrt
from typing import Deque, Iterable

import numpy as np

from .calibration.interfaces import StateCalibrationArtifact, StateRegimeSurface
from .config import FeatureConfig
from .events import BookSnapshot, MarketEvent, QuoteEvent, TradeEvent, TradeSide, infer_trade_side


class SpreadState(str, Enum):
    TIGHT = "tight"
    NORMAL = "normal"
    WIDE = "wide"


class PressureState(str, Enum):
    SELL_HEAVY = "sell_heavy"
    NEUTRAL = "neutral"
    BUY_HEAVY = "buy_heavy"


class FlickerState(str, Enum):
    STABLE = "stable"
    COMPETITIVE = "competitive"
    CHAOTIC = "chaotic"


class VolatilityState(str, Enum):
    QUIET = "quiet"
    NORMAL = "normal"
    STRESSED = "stressed"


@dataclass(frozen=True, slots=True)
class ObservedState:
    symbol: str
    timestamp_ns: int
    book: BookSnapshot
    spread_norm: float
    quote_pressure: float
    trade_pressure: float
    flicker_intensity: float
    realized_volatility: float
    spread_state: SpreadState
    quote_state: PressureState
    trade_state: PressureState
    flicker_state: FlickerState
    volatility_state: VolatilityState

    @property
    def vector(self) -> np.ndarray:
        return np.array(
            [
                self.spread_norm,
                self.quote_pressure,
                self.trade_pressure,
                self.flicker_intensity,
                self.realized_volatility,
            ],
            dtype=float,
        )

    @property
    def label(self) -> str:
        return "|".join(
            [
                self.spread_state.value,
                self.quote_state.value,
                self.trade_state.value,
                self.flicker_state.value,
                self.volatility_state.value,
            ]
        )


class FeatureEngine:
    def __init__(self, config: FeatureConfig | None = None, state_calibration: StateCalibrationArtifact | None = None):
        self.config = config or FeatureConfig()
        self.state_calibration = state_calibration
        self.active_regime_hint: str | None = None
        self.current_book: BookSnapshot | None = None
        self.quote_history: Deque[QuoteEvent] = deque(maxlen=self.config.quote_persistence_updates + 1)
        self.microprice_history: Deque[tuple[int, float]] = deque()
        self.trade_pressure_window: Deque[tuple[int, float]] = deque()
        self.spread_norm_history: Deque[float] = deque(maxlen=self.config.quantile_history)
        self.volatility_history: Deque[float] = deque(maxlen=self.config.quantile_history)
        self._microprice_returns: Deque[float] = deque()
        self._microprice_return_sum = 0.0
        self._microprice_return_sum_squares = 0.0
        self._microprice_cache_tail: tuple[int, float] | None = None
        self._trade_pressure_signed_sum = 0.0
        self._trade_pressure_gross_sum = 0.0
        self._trade_pressure_cache_tail: tuple[int, float] | None = None
        self._trade_pressure_cache_count = 0
        self._spread_norm_sorted: list[float] = []
        self._spread_norm_cache_tail: float | None = None
        self._volatility_sorted: list[float] = []
        self._volatility_cache_tail: float | None = None
        self.flicker_baseline = (
            self.state_calibration.flicker_baseline if self.state_calibration is not None else self.config.flicker_baseline_intensity
        )
        self.flicker_intensity: float = self.flicker_baseline
        self.last_quote_ts: int | None = None

    def set_regime_hint(self, regime: str | None) -> None:
        self.active_regime_hint = regime

    def update(self, event: MarketEvent) -> ObservedState | None:
        if isinstance(event, QuoteEvent):
            self._on_quote(event)
        elif isinstance(event, TradeEvent):
            self._on_trade(event)
        else:
            return None

        if self.current_book is None:
            return None

        realized_volatility = self._realized_volatility(event.timestamp_ns)
        spread_norm = self.current_book.spread / max(realized_volatility, self.config.minimum_sigma)
        quote_pressure = self._normalize_quote_pressure(self._quote_pressure_posterior())
        trade_pressure = self._trade_pressure(event.timestamp_ns)
        flicker_intensity = self._current_flicker_intensity(event.timestamp_ns)

        self._append_quantile_value(
            self.spread_norm_history,
            self._spread_norm_sorted,
            spread_norm,
        )
        self._spread_norm_cache_tail = spread_norm
        self._append_quantile_value(
            self.volatility_history,
            self._volatility_sorted,
            realized_volatility,
        )
        self._volatility_cache_tail = realized_volatility

        return ObservedState(
            symbol=self.current_book.symbol,
            timestamp_ns=event.timestamp_ns,
            book=self.current_book,
            spread_norm=spread_norm,
            quote_pressure=quote_pressure,
            trade_pressure=trade_pressure,
            flicker_intensity=flicker_intensity,
            realized_volatility=realized_volatility,
            spread_state=self._spread_state(spread_norm),
            quote_state=self._pressure_state(quote_pressure),
            trade_state=self._pressure_state(trade_pressure),
            flicker_state=self._flicker_state(flicker_intensity),
            volatility_state=self._volatility_state(realized_volatility),
        )

    def _on_quote(self, quote: QuoteEvent) -> None:
        self.current_book = BookSnapshot.from_quote(quote)
        self.quote_history.append(quote)
        self._update_microprice_history(quote.timestamp_ns, self.current_book.microprice)
        self._update_flicker_intensity(quote.timestamp_ns)

    def _on_trade(self, trade: TradeEvent) -> None:
        if self.current_book is None:
            return
        side = infer_trade_side(trade, self.current_book)
        signed_volume = float(trade.size)
        if side is TradeSide.SELL:
            signed_volume *= -1.0
        elif side is TradeSide.UNKNOWN:
            signed_volume = 0.0
        self._ensure_trade_pressure_cache()
        item = (trade.timestamp_ns, signed_volume)
        self.trade_pressure_window.append(item)
        self._trade_pressure_signed_sum += signed_volume
        self._trade_pressure_gross_sum += abs(signed_volume)
        self._trade_pressure_cache_tail = item
        self._prune_trade_pressure(trade.timestamp_ns)

    def _update_microprice_history(self, timestamp_ns: int, microprice: float) -> None:
        self._ensure_microprice_cache()
        if self.microprice_history:
            previous_price = self.microprice_history[-1][1]
            log_return = self._log_price(microprice) - self._log_price(previous_price)
            self._microprice_returns.append(log_return)
            self._microprice_return_sum += log_return
            self._microprice_return_sum_squares += log_return * log_return
        item = (timestamp_ns, microprice)
        self.microprice_history.append(item)
        self._microprice_cache_tail = item
        self._prune_microprices(timestamp_ns)

    def _update_flicker_intensity(self, timestamp_ns: int) -> None:
        if self.last_quote_ts is None:
            self.last_quote_ts = timestamp_ns
            self.flicker_intensity = self.flicker_baseline
            return
        dt_seconds = max((timestamp_ns - self.last_quote_ts) / 1_000_000_000.0, 1e-6)
        mean_reversion = np.exp(-self.config.flicker_mean_reversion * dt_seconds)
        baseline = self.flicker_baseline
        self.flicker_intensity = baseline + (self.flicker_intensity - baseline) * mean_reversion
        self.flicker_intensity += self.config.flicker_jump
        self.last_quote_ts = timestamp_ns

    def _current_flicker_intensity(self, timestamp_ns: int) -> float:
        if self.last_quote_ts is None:
            return self.flicker_baseline
        dt_seconds = max((timestamp_ns - self.last_quote_ts) / 1_000_000_000.0, 0.0)
        return self.flicker_baseline + (
            self.flicker_intensity - self.flicker_baseline
        ) * np.exp(-self.config.flicker_mean_reversion * dt_seconds)

    def _normalize_quote_pressure(self, pressure: float) -> float:
        surface = self._active_surface()
        if surface is None:
            return pressure
        scale = max(surface.quote_pressure_scale, 1e-6)
        return float(np.clip(pressure / scale, -1.0, 1.0))

    def _quote_pressure_posterior(self) -> float:
        history = list(self.quote_history)
        if len(history) < 2:
            return 0.0

        buy_evidence = 1.0
        sell_evidence = 1.0
        for previous, current in zip(history[:-1], history[1:]):
            if current.bid_size >= previous.bid_size:
                buy_evidence += 1.0
            else:
                sell_evidence += 0.5
            if current.ask_size <= previous.ask_size:
                buy_evidence += 1.0
            else:
                sell_evidence += 0.5
            if current.bid_price > previous.bid_price:
                buy_evidence += 2.0
            elif current.bid_price < previous.bid_price:
                sell_evidence += 2.0
            if current.ask_price < previous.ask_price:
                buy_evidence += 2.0
            elif current.ask_price > previous.ask_price:
                sell_evidence += 2.0

        posterior_mean = buy_evidence / (buy_evidence + sell_evidence)
        return float(2.0 * posterior_mean - 1.0)

    def _trade_pressure(self, timestamp_ns: int) -> float:
        self._ensure_trade_pressure_cache()
        self._prune_trade_pressure(timestamp_ns)
        if not self.trade_pressure_window:
            return 0.0
        return (
            float(self._trade_pressure_signed_sum / self._trade_pressure_gross_sum)
            if self._trade_pressure_gross_sum > 0
            else 0.0
        )

    def _realized_volatility(self, timestamp_ns: int) -> float:
        self._ensure_microprice_cache()
        self._prune_microprices(timestamp_ns)
        if len(self.microprice_history) < 3:
            return self.config.minimum_sigma
        count = len(self._microprice_returns)
        if count == 0:
            return self.config.minimum_sigma
        mean = self._microprice_return_sum / count
        variance = max(self._microprice_return_sum_squares / count - mean * mean, 0.0)
        return float(sqrt(variance))

    def _spread_state(self, spread_norm: float) -> SpreadState:
        surface = self._active_surface()
        if surface is not None:
            low, high = surface.spread_quantiles
        else:
            self._ensure_quantile_cache(
                self.spread_norm_history,
                self._spread_norm_sorted,
                "_spread_norm_cache_tail",
            )
            low, high = self._rolling_tertiles_sorted(self._spread_norm_sorted, (0.75, 1.75))
        if spread_norm <= low:
            return SpreadState.TIGHT
        if spread_norm >= high:
            return SpreadState.WIDE
        return SpreadState.NORMAL

    def _pressure_state(self, pressure: float) -> PressureState:
        if pressure >= 0.25:
            return PressureState.BUY_HEAVY
        if pressure <= -0.25:
            return PressureState.SELL_HEAVY
        return PressureState.NEUTRAL

    def _flicker_state(self, flicker_intensity: float) -> FlickerState:
        surface = self._active_surface()
        baseline = surface.flicker_baseline if surface is not None else self.flicker_baseline
        if flicker_intensity <= baseline * 0.9:
            return FlickerState.STABLE
        if flicker_intensity >= baseline * 1.5:
            return FlickerState.CHAOTIC
        return FlickerState.COMPETITIVE

    def _volatility_state(self, realized_volatility: float) -> VolatilityState:
        surface = self._active_surface()
        if surface is not None:
            low, high = surface.volatility_quantiles
        else:
            self._ensure_quantile_cache(
                self.volatility_history,
                self._volatility_sorted,
                "_volatility_cache_tail",
            )
            low, high = self._rolling_tertiles_sorted(self._volatility_sorted, (5e-4, 2e-3))
        if realized_volatility <= low:
            return VolatilityState.QUIET
        if realized_volatility >= high:
            return VolatilityState.STRESSED
        return VolatilityState.NORMAL

    def _active_surface(self) -> StateRegimeSurface | None:
        if self.state_calibration is None:
            return None
        if self.active_regime_hint is not None:
            regime_surface = self.state_calibration.regime_surfaces.get(self.active_regime_hint)
            if regime_surface is not None:
                return regime_surface
        return StateRegimeSurface(
            spread_quantiles=self.state_calibration.spread_quantiles,
            volatility_quantiles=self.state_calibration.volatility_quantiles,
            flicker_baseline=self.state_calibration.flicker_baseline,
            quote_pressure_scale=self.state_calibration.quote_pressure_scale,
            sample_count=0,
        )

    def rebuild_rolling_caches(self) -> None:
        """Rebuild derived rolling state after snapshot recovery or direct restoration."""

        self._rebuild_microprice_cache()
        self._rebuild_trade_pressure_cache()
        self._rebuild_quantile_cache(
            self.spread_norm_history,
            self._spread_norm_sorted,
            "_spread_norm_cache_tail",
        )
        self._rebuild_quantile_cache(
            self.volatility_history,
            self._volatility_sorted,
            "_volatility_cache_tail",
        )

    def _ensure_microprice_cache(self) -> None:
        expected_returns = max(len(self.microprice_history) - 1, 0)
        tail = self.microprice_history[-1] if self.microprice_history else None
        if len(self._microprice_returns) != expected_returns or self._microprice_cache_tail != tail:
            self._rebuild_microprice_cache()

    def _rebuild_microprice_cache(self) -> None:
        self._microprice_returns.clear()
        self._microprice_return_sum = 0.0
        self._microprice_return_sum_squares = 0.0
        previous_price: float | None = None
        for _, price in self.microprice_history:
            if previous_price is not None:
                value = self._log_price(price) - self._log_price(previous_price)
                self._microprice_returns.append(value)
                self._microprice_return_sum += value
                self._microprice_return_sum_squares += value * value
            previous_price = price
        self._microprice_cache_tail = self.microprice_history[-1] if self.microprice_history else None

    def _prune_microprices(self, timestamp_ns: int) -> None:
        threshold_ns = timestamp_ns - int(self.config.micro_vol_window_seconds * 1_000_000_000)
        while self.microprice_history and self.microprice_history[0][0] < threshold_ns:
            self.microprice_history.popleft()
            if self._microprice_returns:
                removed = self._microprice_returns.popleft()
                self._microprice_return_sum -= removed
                self._microprice_return_sum_squares -= removed * removed
        self._microprice_cache_tail = self.microprice_history[-1] if self.microprice_history else None

    def _ensure_trade_pressure_cache(self) -> None:
        tail = self.trade_pressure_window[-1] if self.trade_pressure_window else None
        if (
            self._trade_pressure_cache_count != len(self.trade_pressure_window)
            or self._trade_pressure_cache_tail != tail
        ):
            self._rebuild_trade_pressure_cache()

    def _rebuild_trade_pressure_cache(self) -> None:
        self._trade_pressure_signed_sum = sum(value for _, value in self.trade_pressure_window)
        self._trade_pressure_gross_sum = sum(abs(value) for _, value in self.trade_pressure_window)
        self._trade_pressure_cache_tail = self.trade_pressure_window[-1] if self.trade_pressure_window else None
        self._trade_pressure_cache_count = len(self.trade_pressure_window)

    def _prune_trade_pressure(self, timestamp_ns: int) -> None:
        threshold_ns = timestamp_ns - int(self.config.trade_window_seconds * 1_000_000_000)
        while self.trade_pressure_window and self.trade_pressure_window[0][0] < threshold_ns:
            _, removed = self.trade_pressure_window.popleft()
            self._trade_pressure_signed_sum -= removed
            self._trade_pressure_gross_sum -= abs(removed)
        self._trade_pressure_cache_tail = self.trade_pressure_window[-1] if self.trade_pressure_window else None
        self._trade_pressure_cache_count = len(self.trade_pressure_window)

    def _ensure_quantile_cache(
        self,
        history: Deque[float],
        sorted_values: list[float],
        tail_attribute: str,
    ) -> None:
        tail = history[-1] if history else None
        if len(sorted_values) != len(history) or getattr(self, tail_attribute) != tail:
            self._rebuild_quantile_cache(history, sorted_values, tail_attribute)

    def _rebuild_quantile_cache(
        self,
        history: Deque[float],
        sorted_values: list[float],
        tail_attribute: str,
    ) -> None:
        sorted_values[:] = sorted(history)
        setattr(self, tail_attribute, history[-1] if history else None)

    @staticmethod
    def _append_quantile_value(
        history: Deque[float],
        sorted_values: list[float],
        value: float,
    ) -> None:
        if history.maxlen is not None and len(history) == history.maxlen:
            removed = history[0]
            sorted_values.pop(bisect_left(sorted_values, removed))
        history.append(value)
        insort(sorted_values, value)

    def _log_price(self, price: float) -> float:
        return log(max(price, self.config.minimum_sigma))

    @classmethod
    def _rolling_tertiles_sorted(
        cls,
        sorted_values: list[float],
        fallback: tuple[float, float],
    ) -> tuple[float, float]:
        if len(sorted_values) < 8:
            return fallback
        return cls._linear_quantile(sorted_values, 1.0 / 3.0), cls._linear_quantile(
            sorted_values,
            2.0 / 3.0,
        )

    @staticmethod
    def _linear_quantile(sorted_values: list[float], quantile: float) -> float:
        position = quantile * (len(sorted_values) - 1)
        lower = floor(position)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = position - lower
        return float(sorted_values[lower] + weight * (sorted_values[upper] - sorted_values[lower]))

    @staticmethod
    def _rolling_tertiles(history: Iterable[float], fallback: tuple[float, float]) -> tuple[float, float]:
        values = np.array(list(history), dtype=float)
        if values.size < 8:
            return fallback
        return float(np.quantile(values, 1.0 / 3.0)), float(np.quantile(values, 2.0 / 3.0))
