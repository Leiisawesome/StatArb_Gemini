"""Feature extraction and coarse-grained state projection for L1 data."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
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

        self.spread_norm_history.append(spread_norm)
        self.volatility_history.append(realized_volatility)

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
        self.trade_pressure_window.append((trade.timestamp_ns, signed_volume))
        self._prune(self.trade_pressure_window, trade.timestamp_ns, self.config.trade_window_seconds)

    def _update_microprice_history(self, timestamp_ns: int, microprice: float) -> None:
        self.microprice_history.append((timestamp_ns, microprice))
        self._prune(self.microprice_history, timestamp_ns, self.config.micro_vol_window_seconds)

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
        self._prune(self.trade_pressure_window, timestamp_ns, self.config.trade_window_seconds)
        if not self.trade_pressure_window:
            return 0.0
        signed = sum(volume for _, volume in self.trade_pressure_window)
        gross = sum(abs(volume) for _, volume in self.trade_pressure_window)
        return float(signed / gross) if gross > 0 else 0.0

    def _realized_volatility(self, timestamp_ns: int) -> float:
        self._prune(self.microprice_history, timestamp_ns, self.config.micro_vol_window_seconds)
        if len(self.microprice_history) < 3:
            return self.config.minimum_sigma
        prices = np.array([price for _, price in self.microprice_history], dtype=float)
        log_returns = np.diff(np.log(np.maximum(prices, self.config.minimum_sigma)))
        if log_returns.size == 0:
            return self.config.minimum_sigma
        return float(np.std(log_returns))

    def _spread_state(self, spread_norm: float) -> SpreadState:
        surface = self._active_surface()
        if surface is not None:
            low, high = surface.spread_quantiles
        else:
            low, high = self._rolling_tertiles(self.spread_norm_history, (0.75, 1.75))
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
            low, high = self._rolling_tertiles(self.volatility_history, (5e-4, 2e-3))
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

    @staticmethod
    def _prune(window: Deque[tuple[int, float]] | Deque[tuple[int, float] | tuple[int, int]] | Deque[tuple[int, float] | tuple[int, int] | tuple[int, float]], timestamp_ns: int, horizon_seconds: float) -> None:
        threshold_ns = timestamp_ns - int(horizon_seconds * 1_000_000_000)
        while window and window[0][0] < threshold_ns:
            window.popleft()

    @staticmethod
    def _rolling_tertiles(history: Iterable[float], fallback: tuple[float, float]) -> tuple[float, float]:
        values = np.array(list(history), dtype=float)
        if values.size < 8:
            return fallback
        return float(np.quantile(values, 1.0 / 3.0)), float(np.quantile(values, 2.0 / 3.0))