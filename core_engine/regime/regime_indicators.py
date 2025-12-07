"""
Regime Detection Engine - Regime-Specific Indicators
Advanced regime-specific technical indicators, early warning signals,
transition indicators, and regime strength measures
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings

# Import centralized configuration (Rule 1, Section 7)

# Import regime components
from .regime_detector import RegimeType

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class IndicatorType(Enum):
    """Regime indicator types"""
    VOLATILITY_REGIME = "volatility_regime"
    MOMENTUM_REGIME = "momentum_regime"
    MEAN_REVERSION = "mean_reversion"
    TREND_STRENGTH = "trend_strength"
    CORRELATION_REGIME = "correlation_regime"
    STRESS_INDICATOR = "stress_indicator"
    TRANSITION_SIGNAL = "transition_signal"
    REGIME_STRENGTH = "regime_strength"
    EARLY_WARNING = "early_warning"


class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class RegimeIndicator:
    """Individual regime indicator"""

    name: str = ""
    indicator_type: IndicatorType = IndicatorType.VOLATILITY_REGIME

    # Current values
    current_value: float = 0.0
    normalized_value: float = 0.0  # 0-1 scale
    signal_strength: SignalStrength = SignalStrength.MODERATE

    # Signal information
    signal_direction: int = 0  # -1, 0, 1
    confidence: float = 0.0
    persistence: int = 0  # How many periods signal has persisted

    # Historical context
    percentile_rank: float = 0.5
    z_score: float = 0.0

    # Metadata
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    lookback_period: int = 20

    # Additional context
    regime_implications: Dict[RegimeType, float] = field(default_factory=dict)
    related_indicators: Dict[str, float] = field(default_factory=dict)


@dataclass
class TransitionSignal:
    """Regime transition signal"""

    signal_name: str = ""

    # Transition information
    from_regime: RegimeType = RegimeType.UNKNOWN
    to_regime: RegimeType = RegimeType.UNKNOWN
    transition_probability: float = 0.0

    # Timing
    estimated_transition_date: Optional[datetime] = None
    confidence_interval_days: int = 5

    # Signal characteristics
    signal_strength: SignalStrength = SignalStrength.MODERATE
    signal_persistence: int = 0
    false_signal_probability: float = 0.3

    # Supporting evidence
    supporting_indicators: List[str] = field(default_factory=list)
    confirming_signals: int = 0
    total_signals: int = 1

    # Risk implications
    risk_increase: float = 0.0  # Expected risk increase during transition
    uncertainty_increase: float = 0.0


@dataclass
class RegimeStrengthMeasure:
    """Measure of current regime strength"""

    regime_type: RegimeType = RegimeType.UNKNOWN

    # Strength metrics
    overall_strength: float = 0.0  # 0-1 scale
    momentum_strength: float = 0.0
    persistence_strength: float = 0.0
    coherence_strength: float = 0.0

    # Stability metrics
    regime_stability: float = 0.0
    expected_duration: int = 0  # Days
    decay_rate: float = 0.0

    # Supporting metrics
    supporting_indicators: int = 0
    conflicting_indicators: int = 0
    neutral_indicators: int = 0

    # Historical context
    typical_duration: int = 0
    historical_strength_percentile: float = 0.5


class VolatilityRegimeIndicators:
    """Volatility regime specific indicators"""

    def __init__(self, config: Any = None):
        self.config = config

        logger.info("Volatility regime indicators initialized")

    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

    def calculate_volatility_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate volatility regime indicators"""

        try:
            indicators = {}
            returns = price_data.pct_change().dropna()

            if returns.empty:
                return indicators

            # Realized volatility indicators
            indicators.update(self._calculate_realized_volatility_indicators(returns))

            # Volatility clustering indicators
            indicators.update(self._calculate_volatility_clustering_indicators(returns))

            # GARCH-like indicators
            indicators.update(self._calculate_garch_indicators(returns))

            # Range-based volatility
            indicators.update(self._calculate_range_volatility_indicators(price_data))

            # Volatility regime classification
            indicators.update(self._calculate_volatility_regime_classification(returns))

            return indicators

        except Exception as e:
            logger.error(f"Error calculating volatility indicators: {e}")
            return {}

    def _calculate_realized_volatility_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate realized volatility indicators"""

        try:
            indicators = {}

            for period in self.config.vol_lookback_periods:
                if len(returns) < period:
                    continue

                # Rolling volatility
                vol = returns.rolling(period).std().iloc[:, 0] * np.sqrt(252)

                # Current volatility level
                current_vol = vol.iloc[-1] if len(vol) > 0 else 0

                # Volatility percentile
                vol_percentile = (vol <= current_vol).mean() if len(vol) > 0 else 0.5

                # Volatility signal
                if vol_percentile > self.config.vol_percentile_threshold:
                    signal_direction = 1  # High volatility regime
                    signal_strength = SignalStrength.STRONG
                elif vol_percentile < (1 - self.config.vol_percentile_threshold):
                    signal_direction = -1  # Low volatility regime
                    signal_strength = SignalStrength.STRONG
                else:
                    signal_direction = 0  # Normal volatility
                    signal_strength = SignalStrength.WEAK

                # Z-score - ensure we work with numeric values
                if len(vol) > 0:
                    vol_values = vol.values if hasattr(vol, 'values') else vol
                    vol_mean = np.mean(vol_values)
                    vol_std = np.std(vol_values)
                else:
                    vol_mean = 0
                    vol_std = 1
                z_score = (current_vol - vol_mean) / vol_std if vol_std > 0 else 0

                indicator = RegimeIndicator(
                    name=f"realized_volatility_{period}d",
                    indicator_type=IndicatorType.VOLATILITY_REGIME,
                    current_value=current_vol,
                    normalized_value=vol_percentile,
                    signal_strength=signal_strength,
                    signal_direction=signal_direction,
                    confidence=abs(vol_percentile - 0.5) * 2,
                    percentile_rank=vol_percentile,
                    z_score=z_score,
                    lookback_period=period
                )

                # Regime implications
                if signal_direction == 1:
                    indicator.regime_implications = {
                        RegimeType.HIGH_VOLATILITY: 0.8,
                        RegimeType.CRISIS: 0.6,
                        RegimeType.BEAR_MARKET: 0.4
                    }
                elif signal_direction == -1:
                    indicator.regime_implications = {
                        RegimeType.LOW_VOLATILITY: 0.8,
                        RegimeType.BULL_MARKET: 0.6,
                        RegimeType.SIDEWAYS: 0.4
                    }

                indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating realized volatility indicators: {e}")
            return {}

    def _calculate_volatility_clustering_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate volatility clustering indicators"""

        try:
            indicators = {}

            # Volatility clustering measure
            vol = returns.rolling(self.config.vol_clustering_window).std().iloc[:, 0]
            vol_changes = vol.diff().abs()

            # Clustering strength
            clustering_strength = vol_changes.rolling(self.config.vol_clustering_window).mean().iloc[-1] if len(vol_changes) > 0 else 0
            clustering_percentile = (vol_changes.rolling(self.config.vol_clustering_window).mean() <= clustering_strength).mean() if len(vol_changes) > 0 else 0.5

            # Signal interpretation
            if clustering_percentile > 0.8:
                signal_direction = 1
                signal_strength = SignalStrength.STRONG
            elif clustering_percentile < 0.2:
                signal_direction = -1
                signal_strength = SignalStrength.STRONG
            else:
                signal_direction = 0
                signal_strength = SignalStrength.WEAK

            indicator = RegimeIndicator(
                name="volatility_clustering",
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                current_value=clustering_strength,
                normalized_value=clustering_percentile,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(clustering_percentile - 0.5) * 2,
                percentile_rank=clustering_percentile,
                lookback_period=self.config.vol_clustering_window
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating volatility clustering indicators: {e}")
            return {}

    def _calculate_garch_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate GARCH-like volatility indicators"""

        try:
            indicators = {}

            # Simple GARCH approximation
            market_returns = returns.iloc[:, 0]
            squared_returns = market_returns ** 2

            # EWMA volatility
            alpha = 0.06  # GARCH parameter approximation
            ewma_var = squared_returns.ewm(alpha=alpha).mean()
            ewma_vol = np.sqrt(ewma_var * 252)

            current_ewma_vol = ewma_vol.iloc[-1] if len(ewma_vol) > 0 else 0
            ewma_percentile = (ewma_vol <= current_ewma_vol).mean() if len(ewma_vol) > 0 else 0.5

            # Signal
            if ewma_percentile > 0.8:
                signal_direction = 1
                signal_strength = SignalStrength.STRONG
            elif ewma_percentile < 0.2:
                signal_direction = -1
                signal_strength = SignalStrength.STRONG
            else:
                signal_direction = 0
                signal_strength = SignalStrength.WEAK

            indicator = RegimeIndicator(
                name="garch_volatility",
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                current_value=current_ewma_vol,
                normalized_value=ewma_percentile,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(ewma_percentile - 0.5) * 2,
                percentile_rank=ewma_percentile
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating GARCH indicators: {e}")
            return {}

    def _calculate_range_volatility_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate range-based volatility indicators"""

        try:
            indicators = {}

            # Use first asset or average if multiple
            if 'high' in price_data.columns and 'low' in price_data.columns:
                high_col = 'high'
                low_col = 'low'
            else:
                # Use price columns as proxy
                numeric_cols = price_data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) >= 2:
                    high_col = numeric_cols[0]
                    low_col = numeric_cols[1]
                else:
                    return indicators

            # True range calculation
            high_prices = price_data[high_col]
            low_prices = price_data[low_col]

            true_range = high_prices - low_prices
            atr = true_range.rolling(14).mean()

            current_atr = atr.iloc[-1] if len(atr) > 0 else 0
            atr_percentile = (atr <= current_atr).mean() if len(atr) > 0 else 0.5

            # Signal
            if atr_percentile > 0.8:
                signal_direction = 1
                signal_strength = SignalStrength.STRONG
            elif atr_percentile < 0.2:
                signal_direction = -1
                signal_strength = SignalStrength.STRONG
            else:
                signal_direction = 0
                signal_strength = SignalStrength.WEAK

            indicator = RegimeIndicator(
                name="average_true_range",
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                current_value=current_atr,
                normalized_value=atr_percentile,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(atr_percentile - 0.5) * 2,
                percentile_rank=atr_percentile,
                lookback_period=14
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating range volatility indicators: {e}")
            return {}

    def _calculate_volatility_regime_classification(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Classify volatility regime"""

        try:
            indicators = {}

            # Multiple timeframe volatility
            short_vol = returns.rolling(20).std().iloc[:, 0] * np.sqrt(252)
            medium_vol = returns.rolling(60).std().iloc[:, 0] * np.sqrt(252) if len(returns) >= 60 else short_vol
            long_vol = returns.rolling(252).std().iloc[:, 0] * np.sqrt(252) if len(returns) >= 252 else medium_vol

            current_short = short_vol.iloc[-1] if len(short_vol) > 0 else 0
            current_medium = medium_vol.iloc[-1] if len(medium_vol) > 0 else 0
            current_long = long_vol.iloc[-1] if len(long_vol) > 0 else 0

            # Volatility regime classification
            if current_short > current_medium * 1.5 and current_medium > current_long * 1.2:
                regime_signal = 2  # Escalating volatility
                signal_strength = SignalStrength.VERY_STRONG
            elif current_short > current_medium * 1.2:
                regime_signal = 1  # Rising volatility
                signal_strength = SignalStrength.STRONG
            elif current_short < current_medium * 0.8 and current_medium < current_long * 0.9:
                regime_signal = -2  # Declining volatility
                signal_strength = SignalStrength.VERY_STRONG
            elif current_short < current_medium * 0.9:
                regime_signal = -1  # Falling volatility
                signal_strength = SignalStrength.STRONG
            else:
                regime_signal = 0  # Stable volatility
                signal_strength = SignalStrength.WEAK

            # Normalized value
            vol_ratio = current_short / current_long if current_long > 0 else 1
            normalized_value = min(1.0, max(0.0, (vol_ratio - 0.5) / 1.5 + 0.5))

            indicator = RegimeIndicator(
                name="volatility_regime_classification",
                indicator_type=IndicatorType.VOLATILITY_REGIME,
                current_value=vol_ratio,
                normalized_value=normalized_value,
                signal_strength=signal_strength,
                signal_direction=np.sign(regime_signal),
                confidence=min(1.0, abs(regime_signal) / 2)
            )

            # Regime implications based on classification
            if regime_signal >= 1:
                indicator.regime_implications = {
                    RegimeType.HIGH_VOLATILITY: 0.9,
                    RegimeType.CRISIS: 0.7,
                    RegimeType.BEAR_MARKET: 0.5
                }
            elif regime_signal <= -1:
                indicator.regime_implications = {
                    RegimeType.LOW_VOLATILITY: 0.9,
                    RegimeType.BULL_MARKET: 0.7,
                    RegimeType.SIDEWAYS: 0.5
                }

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating volatility regime classification: {e}")
            return {}


class MomentumRegimeIndicators:
    """Momentum regime specific indicators"""

    def __init__(self, config: Any = None):
        self.config = config

    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

        logger.info("Momentum regime indicators initialized")

    def calculate_momentum_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate momentum regime indicators"""

        try:
            indicators = {}
            returns = price_data.pct_change().dropna()

            if returns.empty:
                return indicators

            # Trend momentum indicators
            indicators.update(self._calculate_trend_momentum_indicators(returns))

            # Cross-sectional momentum
            indicators.update(self._calculate_cross_sectional_momentum_indicators(returns))

            # Momentum persistence indicators
            indicators.update(self._calculate_momentum_persistence_indicators(returns))

            # Momentum acceleration indicators
            indicators.update(self._calculate_momentum_acceleration_indicators(returns))

            return indicators

        except Exception as e:
            logger.error(f"Error calculating momentum indicators: {e}")
            return {}

    def _calculate_trend_momentum_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate trend momentum indicators"""

        try:
            indicators = {}

            for period in self.config.momentum_periods:
                if len(returns) < period:
                    continue

                # Momentum calculation
                momentum = returns.rolling(period).sum().iloc[:, 0]
                current_momentum = momentum.iloc[-1] if len(momentum) > 0 else 0

                # Smoothed momentum - ensure we work with numeric values
                momentum_values = momentum.values if hasattr(momentum, 'values') else momentum
                smoothed_momentum = pd.Series(momentum_values).rolling(self.config.momentum_smoothing).mean()
                current_smoothed = smoothed_momentum.iloc[-1] if len(smoothed_momentum) > 0 else current_momentum

                # Momentum percentile
                momentum_percentile = (momentum <= current_momentum).mean() if len(momentum) > 0 else 0.5

                # Signal strength based on magnitude and consistency
                momentum_magnitude = abs(current_smoothed)

                if momentum_magnitude > 0.1 and momentum_percentile > 0.8:
                    signal_strength = SignalStrength.VERY_STRONG
                elif momentum_magnitude > 0.05 and momentum_percentile > 0.7:
                    signal_strength = SignalStrength.STRONG
                elif momentum_magnitude > 0.02:
                    signal_strength = SignalStrength.MODERATE
                else:
                    signal_strength = SignalStrength.WEAK

                # Signal direction
                signal_direction = np.sign(current_smoothed)

                indicator = RegimeIndicator(
                    name=f"trend_momentum_{period}d",
                    indicator_type=IndicatorType.MOMENTUM_REGIME,
                    current_value=current_momentum,
                    normalized_value=momentum_percentile,
                    signal_strength=signal_strength,
                    signal_direction=signal_direction,
                    confidence=min(1.0, momentum_magnitude * 10),
                    percentile_rank=momentum_percentile,
                    lookback_period=period
                )

                # Regime implications
                if signal_direction > 0:
                    indicator.regime_implications = {
                        RegimeType.BULL_MARKET: 0.8,
                        RegimeType.MOMENTUM: 0.9,
                        RegimeType.HIGH_VOLATILITY: 0.4
                    }
                elif signal_direction < 0:
                    indicator.regime_implications = {
                        RegimeType.BEAR_MARKET: 0.8,
                        RegimeType.CRISIS: 0.6,
                        RegimeType.HIGH_VOLATILITY: 0.5
                    }

                indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating trend momentum indicators: {e}")
            return {}

    def _calculate_cross_sectional_momentum_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate cross-sectional momentum indicators"""

        try:
            indicators = {}

            if returns.shape[1] < 2:
                return indicators

            # Cross-sectional momentum dispersion
            momentum_20d = returns.rolling(20).sum()
            # Ensure we work with numeric values to avoid DatetimeArray issues
            momentum_20d_numeric = momentum_20d.copy()
            momentum_rank = momentum_20d_numeric.rank(axis=1, pct=True)

            # Momentum dispersion (how spread out momentum is)
            momentum_dispersion = momentum_rank.iloc[:, 0] if momentum_rank.shape[1] > 0 else pd.Series()
            current_dispersion = momentum_dispersion.iloc[-1] if len(momentum_dispersion) > 0 else 0

            dispersion_percentile = (momentum_dispersion <= current_dispersion).mean() if len(momentum_dispersion) > 0 else 0.5

            # High dispersion indicates strong momentum regime
            if dispersion_percentile > 0.8:
                signal_direction = 1
                signal_strength = SignalStrength.STRONG
            elif dispersion_percentile < 0.2:
                signal_direction = -1
                signal_strength = SignalStrength.STRONG
            else:
                signal_direction = 0
                signal_strength = SignalStrength.WEAK

            indicator = RegimeIndicator(
                name="cross_sectional_momentum",
                indicator_type=IndicatorType.MOMENTUM_REGIME,
                current_value=current_dispersion,
                normalized_value=dispersion_percentile,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(dispersion_percentile - 0.5) * 2,
                percentile_rank=dispersion_percentile,
                lookback_period=20
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating cross-sectional momentum indicators: {e}")
            return {}

    def _calculate_momentum_persistence_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate momentum persistence indicators"""

        try:
            indicators = {}

            # Momentum persistence
            momentum_5d = returns.rolling(5).sum().iloc[:, 0]
            momentum_20d = returns.rolling(20).sum().iloc[:, 0]

            # Sign persistence - ensure we work with numeric values
            momentum_sign_5d = np.sign(momentum_5d.values if hasattr(momentum_5d, 'values') else momentum_5d)
            momentum_sign_20d = np.sign(momentum_20d.values if hasattr(momentum_20d, 'values') else momentum_20d)

            # Persistence measure
            sign_agreement = pd.Series(momentum_sign_5d == momentum_sign_20d).rolling(20).mean()
            current_persistence = sign_agreement.iloc[-1] if len(sign_agreement) > 0 else 0.5

            # High persistence indicates strong momentum regime
            if current_persistence > 0.8:
                signal_direction = 1
                signal_strength = SignalStrength.STRONG
            elif current_persistence < 0.2:
                signal_direction = -1
                signal_strength = SignalStrength.STRONG
            else:
                signal_direction = 0
                signal_strength = SignalStrength.WEAK

            indicator = RegimeIndicator(
                name="momentum_persistence",
                indicator_type=IndicatorType.MOMENTUM_REGIME,
                current_value=current_persistence,
                normalized_value=current_persistence,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(current_persistence - 0.5) * 2,
                percentile_rank=current_persistence,
                lookback_period=20
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating momentum persistence indicators: {e}")
            return {}

    def _calculate_momentum_acceleration_indicators(self, returns: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate momentum acceleration indicators"""

        try:
            indicators = {}

            # Momentum acceleration
            momentum_short = returns.rolling(5).sum().iloc[:, 0]
            momentum_medium = returns.rolling(20).sum().iloc[:, 0]

            # Acceleration - ensure we work with numeric values
            acceleration = momentum_short - momentum_medium
            current_acceleration = acceleration.iloc[-1] if len(acceleration) > 0 else 0

            # Acceleration percentile
            if len(acceleration) > 0:
                acceleration_values = acceleration.values if hasattr(acceleration, 'values') else acceleration
                acceleration_percentile = (acceleration_values <= current_acceleration).mean()
            else:
                acceleration_percentile = 0.5

            # Signal interpretation
            acceleration_magnitude = abs(current_acceleration)

            if acceleration_magnitude > 0.05:
                signal_strength = SignalStrength.STRONG
            elif acceleration_magnitude > 0.02:
                signal_strength = SignalStrength.MODERATE
            else:
                signal_strength = SignalStrength.WEAK

            signal_direction = np.sign(current_acceleration)

            indicator = RegimeIndicator(
                name="momentum_acceleration",
                indicator_type=IndicatorType.MOMENTUM_REGIME,
                current_value=current_acceleration,
                normalized_value=acceleration_percentile,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=min(1.0, acceleration_magnitude * 20),
                percentile_rank=acceleration_percentile,
                lookback_period=20
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating momentum acceleration indicators: {e}")
            return {}


class MeanReversionIndicators:
    """Mean reversion regime indicators"""

    def __init__(self, config: Any = None):
        self.config = config

    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

        logger.info("Mean reversion indicators initialized")

    def calculate_mean_reversion_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate mean reversion indicators"""

        try:
            indicators = {}

            # Bollinger Bands indicators
            indicators.update(self._calculate_bollinger_indicators(price_data))

            # RSI indicators
            indicators.update(self._calculate_rsi_indicators(price_data))

            # Mean reversion strength
            indicators.update(self._calculate_mean_reversion_strength(price_data))

            # Oversold/Overbought indicators
            indicators.update(self._calculate_oversold_overbought_indicators(price_data))

            return indicators

        except Exception as e:
            logger.error(f"Error calculating mean reversion indicators: {e}")
            return {}

    def _calculate_bollinger_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate Bollinger Bands indicators"""

        try:
            indicators = {}

            # Use close price or first column
            if 'close' in price_data.columns:
                prices = price_data['close']
            else:
                prices = price_data.iloc[:, 0]

            for period in self.config.mean_reversion_periods:
                if len(prices) < period:
                    continue

                # Bollinger Bands
                sma = prices.rolling(period).mean()
                std = prices.rolling(period).std()

                upper_band = sma + self.config.bollinger_std * std
                lower_band = sma - self.config.bollinger_std * std

                # Bollinger position
                bb_position = (prices - lower_band) / (upper_band - lower_band)
                current_position = bb_position.iloc[-1] if len(bb_position) > 0 else 0.5

                # Signal strength based on extremity
                if current_position > 0.9 or current_position < 0.1:
                    signal_strength = SignalStrength.VERY_STRONG
                elif current_position > 0.8 or current_position < 0.2:
                    signal_strength = SignalStrength.STRONG
                elif current_position > 0.7 or current_position < 0.3:
                    signal_strength = SignalStrength.MODERATE
                else:
                    signal_strength = SignalStrength.WEAK

                # Signal direction (mean reversion signal)
                if current_position > 0.8:
                    signal_direction = -1  # Overbought, expect reversion
                elif current_position < 0.2:
                    signal_direction = 1   # Oversold, expect reversion
                else:
                    signal_direction = 0

                indicator = RegimeIndicator(
                    name=f"bollinger_position_{period}d",
                    indicator_type=IndicatorType.MEAN_REVERSION,
                    current_value=current_position,
                    normalized_value=current_position,
                    signal_strength=signal_strength,
                    signal_direction=signal_direction,
                    confidence=max(0, min(1, abs(current_position - 0.5) * 2)),
                    lookback_period=period
                )

                # Regime implications
                if signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]:
                    indicator.regime_implications = {
                        RegimeType.MEAN_REVERSION: 0.8,
                        RegimeType.SIDEWAYS: 0.6,
                        RegimeType.HIGH_VOLATILITY: 0.4
                    }

                indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating Bollinger indicators: {e}")
            return {}

    def _calculate_rsi_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate RSI indicators"""

        try:
            indicators = {}

            # Use close price or first column
            if 'close' in price_data.columns:
                prices = price_data['close']
            else:
                prices = price_data.iloc[:, 0]

            for period in self.config.rsi_periods:
                if len(prices) < period + 1:
                    continue

                # RSI calculation
                delta = prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

                rs = gain / (loss + 1e-8)
                rsi = 100 - (100 / (1 + rs))

                current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50

                # RSI signal interpretation
                if current_rsi > 80:
                    signal_direction = -1  # Overbought
                    signal_strength = SignalStrength.VERY_STRONG
                elif current_rsi > 70:
                    signal_direction = -1  # Overbought
                    signal_strength = SignalStrength.STRONG
                elif current_rsi < 20:
                    signal_direction = 1   # Oversold
                    signal_strength = SignalStrength.VERY_STRONG
                elif current_rsi < 30:
                    signal_direction = 1   # Oversold
                    signal_strength = SignalStrength.STRONG
                else:
                    signal_direction = 0
                    signal_strength = SignalStrength.WEAK

                # Normalized RSI
                normalized_rsi = current_rsi / 100

                indicator = RegimeIndicator(
                    name=f"rsi_{period}d",
                    indicator_type=IndicatorType.MEAN_REVERSION,
                    current_value=current_rsi,
                    normalized_value=normalized_rsi,
                    signal_strength=signal_strength,
                    signal_direction=signal_direction,
                    confidence=max(0, min(1, abs(current_rsi - 50) / 50)),
                    lookback_period=period
                )

                indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating RSI indicators: {e}")
            return {}

    def _calculate_mean_reversion_strength(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate mean reversion strength"""

        try:
            indicators = {}
            returns = price_data.pct_change().dropna()

            if returns.empty:
                return indicators

            # Half-life of mean reversion
            market_returns = returns.iloc[:, 0] if returns.shape[1] > 0 else pd.Series()

            # Autocorrelation as proxy for mean reversion - ensure we work with numeric values
            if len(market_returns) >= 60:
                # Convert to numeric values to avoid DatetimeArray issues
                numeric_returns = market_returns.values if hasattr(market_returns, 'values') else market_returns
                numeric_series = pd.Series(numeric_returns)
                autocorr = numeric_series.rolling(60).apply(lambda x: x.autocorr(lag=1) if len(x) > 1 else 0).iloc[-1]
            else:
                autocorr = 0

            # Negative autocorrelation indicates mean reversion
            mean_reversion_strength = -autocorr if not np.isnan(autocorr) else 0

            # Normalize to 0-1
            normalized_strength = max(0, min(1, (mean_reversion_strength + 1) / 2))

            # Signal strength
            if abs(autocorr) > 0.3:
                signal_strength = SignalStrength.STRONG
            elif abs(autocorr) > 0.1:
                signal_strength = SignalStrength.MODERATE
            else:
                signal_strength = SignalStrength.WEAK

            signal_direction = 1 if mean_reversion_strength > 0.1 else 0

            indicator = RegimeIndicator(
                name="mean_reversion_strength",
                indicator_type=IndicatorType.MEAN_REVERSION,
                current_value=mean_reversion_strength,
                normalized_value=normalized_strength,
                signal_strength=signal_strength,
                signal_direction=signal_direction,
                confidence=abs(autocorr) if not np.isnan(autocorr) else 0,
                lookback_period=60
            )

            indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating mean reversion strength: {e}")
            return {}

    def _calculate_oversold_overbought_indicators(self, price_data: pd.DataFrame) -> Dict[str, RegimeIndicator]:
        """Calculate oversold/overbought indicators"""

        try:
            indicators = {}

            # Use close price or first column
            if 'close' in price_data.columns:
                prices = price_data['close']
            else:
                prices = price_data.iloc[:, 0]

            # Stochastic oscillator approximation
            lookback = 14
            if len(prices) >= lookback:
                lowest_low = prices.rolling(lookback).min()
                highest_high = prices.rolling(lookback).max()

                stoch_k = ((prices - lowest_low) / (highest_high - lowest_low)) * 100
                current_stoch = stoch_k.iloc[-1] if len(stoch_k) > 0 else 50

                # Signal interpretation
                if current_stoch > 80:
                    signal_direction = -1  # Overbought
                    signal_strength = SignalStrength.STRONG
                elif current_stoch < 20:
                    signal_direction = 1   # Oversold
                    signal_strength = SignalStrength.STRONG
                else:
                    signal_direction = 0
                    signal_strength = SignalStrength.WEAK

                indicator = RegimeIndicator(
                    name="stochastic_oscillator",
                    indicator_type=IndicatorType.MEAN_REVERSION,
                    current_value=current_stoch,
                    normalized_value=current_stoch / 100,
                    signal_strength=signal_strength,
                    signal_direction=signal_direction,
                    confidence=max(0, min(1, abs(current_stoch - 50) / 50)),
                    lookback_period=lookback
                )

                indicators[indicator.name] = indicator

            return indicators

        except Exception as e:
            logger.error(f"Error calculating oversold/overbought indicators: {e}")
            return {}


class TransitionSignalDetector:
    """Detect regime transition signals"""

    def __init__(self, config: Any = None):
        self.config = config

    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

        logger.info("Transition signal detector initialized")

    def detect_transition_signals(self, indicators: Dict[str, RegimeIndicator],
                                historical_regimes: Optional[List[RegimeType]] = None) -> List[TransitionSignal]:
        """Detect regime transition signals"""

        try:
            transition_signals = []

            # Volatility transition signals
            transition_signals.extend(self._detect_volatility_transitions(indicators))

            # Momentum transition signals
            transition_signals.extend(self._detect_momentum_transitions(indicators))

            # Mean reversion transition signals
            transition_signals.extend(self._detect_mean_reversion_transitions(indicators))

            # Multi-indicator transition signals
            transition_signals.extend(self._detect_multi_indicator_transitions(indicators))

            return transition_signals

        except Exception as e:
            logger.error(f"Error detecting transition signals: {e}")
            return []

    def _detect_volatility_transitions(self, indicators: Dict[str, RegimeIndicator]) -> List[TransitionSignal]:
        """Detect volatility regime transitions"""

        try:
            signals = []

            # Find volatility indicators
            vol_indicators = {name: ind for name, ind in indicators.items()
                            if ind.indicator_type == IndicatorType.VOLATILITY_REGIME}

            if not vol_indicators:
                return signals

            # Check for volatility regime change signals
            strong_vol_signals = [ind for ind in vol_indicators.values()
                                if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

            if len(strong_vol_signals) >= 2:
                # Consensus on volatility change
                avg_signal_direction = sum(ind.signal_direction for ind in strong_vol_signals) / len(strong_vol_signals)

                if avg_signal_direction > 0.5:
                    # Transition to high volatility
                    signal = TransitionSignal(
                        signal_name="volatility_regime_transition_high",
                        from_regime=RegimeType.LOW_VOLATILITY,
                        to_regime=RegimeType.HIGH_VOLATILITY,
                        transition_probability=0.7,
                        signal_strength=SignalStrength.STRONG,
                        supporting_indicators=[ind.name for ind in strong_vol_signals],
                        confirming_signals=len(strong_vol_signals),
                        total_signals=len(vol_indicators)
                    )
                    signals.append(signal)

                elif avg_signal_direction < -0.5:
                    # Transition to low volatility
                    signal = TransitionSignal(
                        signal_name="volatility_regime_transition_low",
                        from_regime=RegimeType.HIGH_VOLATILITY,
                        to_regime=RegimeType.LOW_VOLATILITY,
                        transition_probability=0.7,
                        signal_strength=SignalStrength.STRONG,
                        supporting_indicators=[ind.name for ind in strong_vol_signals],
                        confirming_signals=len(strong_vol_signals),
                        total_signals=len(vol_indicators)
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error detecting volatility transitions: {e}")
            return []

    def _detect_momentum_transitions(self, indicators: Dict[str, RegimeIndicator]) -> List[TransitionSignal]:
        """Detect momentum regime transitions"""

        try:
            signals = []

            # Find momentum indicators
            momentum_indicators = {name: ind for name, ind in indicators.items()
                                 if ind.indicator_type == IndicatorType.MOMENTUM_REGIME}

            if not momentum_indicators:
                return signals

            # Check for momentum regime changes
            strong_momentum_signals = [ind for ind in momentum_indicators.values()
                                     if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

            if len(strong_momentum_signals) >= 2:
                avg_signal_direction = sum(ind.signal_direction for ind in strong_momentum_signals) / len(strong_momentum_signals)

                if avg_signal_direction > 0.5:
                    # Transition to bull/momentum regime
                    signal = TransitionSignal(
                        signal_name="momentum_regime_transition_bull",
                        from_regime=RegimeType.SIDEWAYS,
                        to_regime=RegimeType.BULL_MARKET,
                        transition_probability=0.6,
                        signal_strength=SignalStrength.STRONG,
                        supporting_indicators=[ind.name for ind in strong_momentum_signals],
                        confirming_signals=len(strong_momentum_signals),
                        total_signals=len(momentum_indicators)
                    )
                    signals.append(signal)

                elif avg_signal_direction < -0.5:
                    # Transition to bear regime
                    signal = TransitionSignal(
                        signal_name="momentum_regime_transition_bear",
                        from_regime=RegimeType.SIDEWAYS,
                        to_regime=RegimeType.BEAR_MARKET,
                        transition_probability=0.6,
                        signal_strength=SignalStrength.STRONG,
                        supporting_indicators=[ind.name for ind in strong_momentum_signals],
                        confirming_signals=len(strong_momentum_signals),
                        total_signals=len(momentum_indicators)
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error detecting momentum transitions: {e}")
            return []

    def _detect_mean_reversion_transitions(self, indicators: Dict[str, RegimeIndicator]) -> List[TransitionSignal]:
        """Detect mean reversion regime transitions"""

        try:
            signals = []

            # Find mean reversion indicators
            mr_indicators = {name: ind for name, ind in indicators.items()
                           if ind.indicator_type == IndicatorType.MEAN_REVERSION}

            if not mr_indicators:
                return signals

            # Check for mean reversion signals
            strong_mr_signals = [ind for ind in mr_indicators.values()
                               if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

            if len(strong_mr_signals) >= 2:
                # Mean reversion regime typically indicates transition opportunity
                signal = TransitionSignal(
                    signal_name="mean_reversion_transition_opportunity",
                    from_regime=RegimeType.MOMENTUM,
                    to_regime=RegimeType.MEAN_REVERSION,
                    transition_probability=0.5,
                    signal_strength=SignalStrength.MODERATE,
                    supporting_indicators=[ind.name for ind in strong_mr_signals],
                    confirming_signals=len(strong_mr_signals),
                    total_signals=len(mr_indicators)
                )
                signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error detecting mean reversion transitions: {e}")
            return []

    def _detect_multi_indicator_transitions(self, indicators: Dict[str, RegimeIndicator]) -> List[TransitionSignal]:
        """Detect transitions based on multiple indicator types"""

        try:
            signals = []

            # Categorize indicators by type
            indicator_types = {}
            for name, ind in indicators.items():
                ind_type = ind.indicator_type
                if ind_type not in indicator_types:
                    indicator_types[ind_type] = []
                indicator_types[ind_type].append(ind)

            # Look for consensus across different indicator types
            type_signals = {}
            for ind_type, type_indicators in indicator_types.items():
                strong_signals = [ind for ind in type_indicators
                                if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

                if strong_signals:
                    avg_direction = sum(ind.signal_direction for ind in strong_signals) / len(strong_signals)
                    type_signals[ind_type] = (avg_direction, len(strong_signals), len(type_indicators))

            # Check for multi-type consensus
            if len(type_signals) >= 2:
                # Crisis transition signal (multiple types showing stress)
                stress_types = [IndicatorType.VOLATILITY_REGIME, IndicatorType.CORRELATION_REGIME]
                stress_signals = [direction for ind_type, (direction, strong, total) in type_signals.items()
                                if ind_type in stress_types and direction > 0]

                if len(stress_signals) >= 2:
                    signal = TransitionSignal(
                        signal_name="multi_indicator_crisis_transition",
                        from_regime=RegimeType.BULL_MARKET,
                        to_regime=RegimeType.CRISIS,
                        transition_probability=0.8,
                        signal_strength=SignalStrength.VERY_STRONG,
                        supporting_indicators=[f"{ind_type.value}_consensus" for ind_type in stress_types],
                        confirming_signals=len(stress_signals),
                        total_signals=len(type_signals)
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error detecting multi-indicator transitions: {e}")
            return []


class RegimeStrengthCalculator:
    """Calculate regime strength measures"""

    def __init__(self, config: Any = None):
        self.config = config

    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)

        logger.info("Regime strength calculator initialized")

    def calculate_regime_strength(self, current_regime: RegimeType,
                                indicators: Dict[str, RegimeIndicator]) -> RegimeStrengthMeasure:
        """Calculate strength of current regime"""

        try:
            # Find indicators supporting current regime
            supporting_indicators = []
            conflicting_indicators = []
            neutral_indicators = []

            for name, indicator in indicators.items():
                regime_implications = indicator.regime_implications

                if current_regime in regime_implications:
                    support_strength = regime_implications[current_regime]
                    if support_strength > 0.6:
                        supporting_indicators.append((name, support_strength))
                    elif support_strength < 0.3:
                        conflicting_indicators.append((name, 1 - support_strength))
                    else:
                        neutral_indicators.append(name)
                else:
                    neutral_indicators.append(name)

            # Calculate overall strength
            if supporting_indicators:
                overall_strength = sum(strength for _, strength in supporting_indicators) / len(supporting_indicators)
            else:
                overall_strength = 0.0

            # Calculate momentum strength
            momentum_indicators = [ind for ind in indicators.values()
                                 if ind.indicator_type == IndicatorType.MOMENTUM_REGIME]

            if momentum_indicators:
                momentum_strength = sum(ind.confidence for ind in momentum_indicators) / len(momentum_indicators)
            else:
                momentum_strength = 0.5

            # Calculate persistence strength
            strong_indicators = [ind for ind in indicators.values()
                               if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

            if indicators:
                persistence_strength = len(strong_indicators) / len(indicators)
            else:
                persistence_strength = 0.0

            # Calculate coherence strength
            if indicators:
                coherence_strength = len(supporting_indicators) / len(indicators)
            else:
                coherence_strength = 0.0

            # Estimate regime stability
            regime_stability = (overall_strength + persistence_strength + coherence_strength) / 3

            # Estimate expected duration (simplified)
            expected_duration = int(regime_stability * 60)  # 0-60 days based on strength

            return RegimeStrengthMeasure(
                regime_type=current_regime,
                overall_strength=overall_strength,
                momentum_strength=momentum_strength,
                persistence_strength=persistence_strength,
                coherence_strength=coherence_strength,
                regime_stability=regime_stability,
                expected_duration=expected_duration,
                supporting_indicators=len(supporting_indicators),
                conflicting_indicators=len(conflicting_indicators),
                neutral_indicators=len(neutral_indicators)
            )

        except Exception as e:
            logger.error(f"Error calculating regime strength: {e}")
            return RegimeStrengthMeasure(regime_type=current_regime)


class RegimeIndicatorEngine:
    """
    Comprehensive Regime Indicator Engine

    Integrates all regime-specific indicators to provide comprehensive
    regime analysis, transition detection, and strength measurement.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize regime indicator engine with centralized configuration

        Args:
            config: RegimeConfig or dict (for backward compatibility)
        """

        # Use centralized RegimeConfig (Rule 1, Section 7)
        from ..config.component_config import RegimeConfig as CentralizedRegimeConfig

        # Handle different config input types
        if isinstance(config, CentralizedRegimeConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = CentralizedRegimeConfig(**config) if config else CentralizedRegimeConfig()
        elif config is None:
            self.config = CentralizedRegimeConfig()
        else:
            self.config = config

        logger.info("✅ RegimeIndicatorEngine using centralized RegimeConfig (Rule 1, Section 7)")

        # Initialize indicator calculators
        self.volatility_indicators = VolatilityRegimeIndicators(self.config)
        self.momentum_indicators = MomentumRegimeIndicators(self.config)
        self.mean_reversion_indicators = MeanReversionIndicators(self.config)
        self.transition_detector = TransitionSignalDetector(self.config)

        # Indicator history
        self.indicator_history: List[Dict[str, RegimeIndicator]] = []
        self.transition_history: List[TransitionSignal] = []

        logger.info("Regime indicator engine initialized")

    def calculate_all_indicators(self, price_data: pd.DataFrame,
                               volume_data: Optional[pd.DataFrame] = None) -> Dict[str, RegimeIndicator]:
        """Calculate all regime indicators"""

        try:
            logger.info("Calculating comprehensive regime indicators")

            all_indicators = {}

            # Volatility regime indicators
            vol_indicators = self.volatility_indicators.calculate_volatility_indicators(price_data)
            all_indicators.update(vol_indicators)

            # Momentum regime indicators
            momentum_indicators = self.momentum_indicators.calculate_momentum_indicators(price_data)
            all_indicators.update(momentum_indicators)

            # Mean reversion indicators
            mr_indicators = self.mean_reversion_indicators.calculate_mean_reversion_indicators(price_data)
            all_indicators.update(mr_indicators)

            # Store in history
            self.indicator_history.append(all_indicators)

            # Limit history size
            if len(self.indicator_history) > 100:
                self.indicator_history = self.indicator_history[-50:]

            logger.info(f"Calculated {len(all_indicators)} regime indicators")
            return all_indicators

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}

    def detect_regime_transitions(self, indicators: Dict[str, RegimeIndicator]) -> List[TransitionSignal]:
        """Detect regime transition signals"""

        try:
            transition_signals = self.transition_detector.detect_transition_signals(indicators)

            # Store in history
            self.transition_history.extend(transition_signals)

            # Limit history size
            if len(self.transition_history) > 100:
                self.transition_history = self.transition_history[-50:]

            return transition_signals

        except Exception as e:
            logger.error(f"Error detecting transitions: {e}")
            return []

    def calculate_regime_strength(self, current_regime: RegimeType,
                                indicators: Dict[str, RegimeIndicator]) -> RegimeStrengthMeasure:
        """Calculate current regime strength"""

        try:
            return self.strength_calculator.calculate_regime_strength(current_regime, indicators)

        except Exception as e:
            logger.error(f"Error calculating regime strength: {e}")
            return RegimeStrengthMeasure(regime_type=current_regime)

    def get_indicator_summary(self, indicators: Dict[str, RegimeIndicator]) -> Dict[str, Any]:
        """Get summary of current indicators"""

        try:
            summary = {
                'total_indicators': len(indicators),
                'by_type': {},
                'by_strength': {},
                'consensus_signals': {}
            }

            # Group by type
            for indicator in indicators.values():
                ind_type = indicator.indicator_type.value
                if ind_type not in summary['by_type']:
                    summary['by_type'][ind_type] = 0
                summary['by_type'][ind_type] += 1

            # Group by strength
            for indicator in indicators.values():
                strength = indicator.signal_strength.value
                if strength not in summary['by_strength']:
                    summary['by_strength'][strength] = 0
                summary['by_strength'][strength] += 1

            # Consensus signals
            positive_signals = sum(1 for ind in indicators.values() if ind.signal_direction > 0)
            negative_signals = sum(1 for ind in indicators.values() if ind.signal_direction < 0)
            neutral_signals = sum(1 for ind in indicators.values() if ind.signal_direction == 0)

            summary['consensus_signals'] = {
                'positive': positive_signals,
                'negative': negative_signals,
                'neutral': neutral_signals
            }

            # Strong signal consensus
            strong_indicators = [ind for ind in indicators.values()
                               if ind.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]

            if strong_indicators:
                strong_positive = sum(1 for ind in strong_indicators if ind.signal_direction > 0)
                strong_negative = sum(1 for ind in strong_indicators if ind.signal_direction < 0)

                summary['strong_consensus'] = {
                    'positive': strong_positive,
                    'negative': strong_negative,
                    'total_strong': len(strong_indicators)
                }

            return summary

        except Exception as e:
            logger.error(f"Error creating indicator summary: {e}")
            return {}

    def export_indicators(self, indicators: Dict[str, RegimeIndicator],
                        filename: Optional[str] = None) -> str:
        """Export indicators to file"""

        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"regime_indicators_{timestamp}.json"

            # Prepare export data
            export_data = {}

            for name, indicator in indicators.items():
                export_data[name] = {
                    'indicator_type': indicator.indicator_type.value,
                    'current_value': indicator.current_value,
                    'normalized_value': indicator.normalized_value,
                    'signal_strength': indicator.signal_strength.value,
                    'signal_direction': indicator.signal_direction,
                    'confidence': indicator.confidence,
                    'percentile_rank': indicator.percentile_rank,
                    'z_score': indicator.z_score,
                    'lookback_period': indicator.lookback_period,
                    'regime_implications': {regime.value: prob for regime, prob in indicator.regime_implications.items()},
                    'calculation_timestamp': indicator.calculation_timestamp.isoformat()
                }

            # Export to JSON
            import json
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"Indicators exported to {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error exporting indicators: {e}")
            return ""