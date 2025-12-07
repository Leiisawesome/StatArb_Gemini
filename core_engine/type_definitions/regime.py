"""
Core Engine Regime Types - Canonical Definitions

Single source of truth for all market regime types across the system.
All regime modules should import from here to avoid duplication.

Professional Grade Market Regime Classification System
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
import numpy as np


class MarketRegime(Enum):
    """
    Canonical market regime classifications - Professional Grade

    This is the SINGLE SOURCE OF TRUTH for regime types.
    All other modules should import from here.

    Design Philosophy:
    - Compound states (direction + volatility) for precision
    - Legacy values for backward compatibility
    - Strategy-relevant classifications
    """

    # === DIRECTIONAL + VOLATILITY REGIMES (Primary) ===
    BULL_LOW_VOL = "bull_low_volatility"           # Strong uptrend, calm conditions
    BULL_HIGH_VOL = "bull_high_volatility"         # Strong uptrend, volatile conditions
    BEAR_LOW_VOL = "bear_low_volatility"           # Downtrend, controlled decline
    BEAR_HIGH_VOL = "bear_high_volatility"         # Downtrend, panic conditions

    # === VOLATILITY-ONLY REGIMES ===
    LOW_VOLATILITY = "low_volatility"              # Low vol, no directional bias
    NORMAL_VOLATILITY = "normal_volatility"        # Average market conditions
    HIGH_VOLATILITY = "high_volatility"            # Elevated volatility
    EXTREME_VOLATILITY = "extreme_volatility"      # Crisis-level volatility

    # === TREND REGIMES ===
    STRONG_TRENDING = "strong_trending"            # Clear directional momentum
    WEAK_TRENDING = "weak_trending"                # Mild directional bias
    RANGE_BOUND = "range_bound"                    # Sideways consolidation
    CHOPPY = "choppy"                              # Erratic, no clear direction

    # === MARKET STRESS REGIMES ===
    CRISIS = "crisis"                              # Extreme stress, flight to safety
    RECOVERY = "recovery"                          # Post-crisis stabilization
    EUPHORIA = "euphoria"                          # Excessive optimism, bubble risk

    # === STRATEGY-RELEVANT REGIMES ===
    MEAN_REVERSION = "mean_reversion"              # Mean reversion favorable
    MOMENTUM = "momentum"                          # Momentum favorable

    # === LEGACY COMPATIBILITY (map to compound states) ===
    BULL_MARKET = "bull_market"                    # Alias for general bull
    BEAR_MARKET = "bear_market"                    # Alias for general bear
    SIDEWAYS = "sideways"                          # Alias for range_bound
    TRENDING = "trending"                          # Alias for strong_trending
    UNKNOWN = "unknown"                            # Undetermined regime

    # === ADDITIONAL LEGACY VALUES (for test compatibility) ===
    TRENDING_UP = "trending_up"                    # Legacy: upward trend
    TRENDING_DOWN = "trending_down"                # Legacy: downward trend
    CRISIS_MODE = "crisis_mode"                    # Legacy: alias for CRISIS

    @classmethod
    def from_volatility(cls, vol_level: str) -> 'MarketRegime':
        """Get regime from volatility level string"""
        mapping = {
            'low': cls.LOW_VOLATILITY,
            'normal': cls.NORMAL_VOLATILITY,
            'high': cls.HIGH_VOLATILITY,
            'extreme': cls.EXTREME_VOLATILITY,
            'crisis': cls.CRISIS
        }
        return mapping.get(vol_level.lower(), cls.NORMAL_VOLATILITY)

    @classmethod
    def from_direction_and_vol(cls, direction: str, volatility: str) -> 'MarketRegime':
        """Get compound regime from direction and volatility"""
        if volatility in ('extreme', 'crisis'):
            return cls.CRISIS

        if direction == 'bull':
            return cls.BULL_HIGH_VOL if volatility == 'high' else cls.BULL_LOW_VOL
        elif direction == 'bear':
            return cls.BEAR_HIGH_VOL if volatility == 'high' else cls.BEAR_LOW_VOL
        else:
            return cls.RANGE_BOUND

    def is_high_risk(self) -> bool:
        """Check if regime indicates elevated risk"""
        return self in (
            self.BEAR_HIGH_VOL, self.CRISIS, self.EXTREME_VOLATILITY,
            self.HIGH_VOLATILITY, self.CHOPPY
        )

    def is_trending(self) -> bool:
        """Check if regime favors trend-following"""
        return self in (
            self.BULL_LOW_VOL, self.BULL_HIGH_VOL, self.BEAR_LOW_VOL,
            self.STRONG_TRENDING, self.MOMENTUM, self.TRENDING
        )

    def is_mean_reverting(self) -> bool:
        """Check if regime favors mean reversion"""
        return self in (
            self.RANGE_BOUND, self.SIDEWAYS, self.MEAN_REVERSION,
            self.LOW_VOLATILITY, self.NORMAL_VOLATILITY
        )


# === LEGACY ALIAS for backward compatibility ===
RegimeType = MarketRegime  # Alias for code using RegimeType
RegimeState = MarketRegime  # Alias for code using RegimeState


@dataclass
class RegimeConfig:
    """Regime detection configuration"""
    lookback_window: int = 20  # Days for regime analysis
    volatility_threshold: float = 0.02  # 2% daily volatility threshold
    trend_threshold: float = 0.05  # 5% trend threshold
    regime_persistence: int = 3  # Days to confirm regime change

    # Technical indicators
    use_rsi: bool = True
    rsi_oversold: float = 30
    rsi_overbought: float = 70

    use_bollinger: bool = True
    bollinger_period: int = 20
    bollinger_std: float = 2.0


@dataclass
class RegimeSignal:
    """Regime detection signal"""
    timestamp: datetime
    regime: RegimeState
    confidence: float  # 0-1 confidence score
    indicators: Dict[str, float] = field(default_factory=dict)

    # Supporting data
    volatility: float = 0.0
    trend_strength: float = 0.0
    momentum: float = 0.0


class RegimeEngine:
    """Lightweight regime detection engine"""

    def __init__(self, config: RegimeConfig):
        self.config = config
        self.current_regime = RegimeState.UNKNOWN
        self.regime_history: List[RegimeSignal] = []
        self.confidence = 0.0

    def detect_regime(self, data: pd.DataFrame) -> RegimeSignal:
        """Detect current market regime from price data"""
        if len(data) < self.config.lookback_window:
            return RegimeSignal(
                timestamp=datetime.now(),
                regime=RegimeState.UNKNOWN,
                confidence=0.0
            )

        # Calculate basic metrics
        price_col = 'close' if 'close' in data.columns else 'Close'
        returns = data[price_col].pct_change().dropna()
        recent_returns = returns.tail(self.config.lookback_window)

        # Volatility analysis
        volatility = recent_returns.std() * np.sqrt(252)  # Annualized

        # Trend analysis
        price_change = (data[price_col].iloc[-1] - data[price_col].iloc[-self.config.lookback_window]) / data[price_col].iloc[-self.config.lookback_window]

        # Momentum analysis
        momentum = recent_returns.mean() * 252  # Annualized

        # Regime classification
        regime = self._classify_regime(volatility, price_change, momentum, data)
        confidence = self._calculate_confidence(volatility, price_change, momentum)

        signal = RegimeSignal(
            timestamp=datetime.now(),
            regime=regime,
            confidence=confidence,
            volatility=volatility,
            trend_strength=abs(price_change),
            momentum=momentum
        )

        # Add technical indicators
        if self.config.use_rsi:
            signal.indicators['rsi'] = self._calculate_rsi(data[price_col])

        if self.config.use_bollinger:
            bb_position = self._calculate_bollinger_position(data[price_col])
            signal.indicators['bollinger_position'] = bb_position

        self.regime_history.append(signal)
        self.current_regime = regime
        self.confidence = confidence

        return signal

    def _classify_regime(self, volatility: float, price_change: float, momentum: float, data: pd.DataFrame) -> RegimeState:
        """Classify market regime based on metrics"""

        # High volatility regime
        if volatility > self.config.volatility_threshold * 2:
            return RegimeState.HIGH_VOLATILITY

        # Low volatility regime
        if volatility < self.config.volatility_threshold * 0.5:
            return RegimeState.LOW_VOLATILITY

        # Trend-based classification
        if price_change > self.config.trend_threshold:
            return RegimeState.BULL
        elif price_change < -self.config.trend_threshold:
            return RegimeState.BEAR
        else:
            return RegimeState.SIDEWAYS

    def _calculate_confidence(self, volatility: float, price_change: float, momentum: float) -> float:
        """Calculate confidence score for regime detection"""
        # Base confidence on trend strength and consistency
        trend_confidence = min(abs(price_change) / self.config.trend_threshold, 1.0)
        momentum_confidence = min(abs(momentum) / 0.1, 1.0)  # 10% annualized momentum threshold

        # Penalty for high volatility (less confident)
        volatility_penalty = min(volatility / (self.config.volatility_threshold * 3), 1.0)

        confidence = (trend_confidence + momentum_confidence) / 2 * (1 - volatility_penalty * 0.3)
        return max(0.0, min(1.0, confidence))

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

    def _calculate_bollinger_position(self, prices: pd.Series) -> float:
        """Calculate position within Bollinger Bands"""
        if len(prices) < self.config.bollinger_period:
            return 0.0

        sma = prices.rolling(window=self.config.bollinger_period).mean()
        std = prices.rolling(window=self.config.bollinger_period).std()

        upper_band = sma + (std * self.config.bollinger_std)
        lower_band = sma - (std * self.config.bollinger_std)

        current_price = prices.iloc[-1]
        upper = upper_band.iloc[-1]
        lower = lower_band.iloc[-1]

        if upper == lower:
            return 0.0

        # Position: -1 (lower band) to +1 (upper band)
        position = (current_price - lower) / (upper - lower) * 2 - 1
        return max(-1.0, min(1.0, position))

    def get_regime_summary(self) -> Dict[str, Any]:
        """Get current regime summary"""
        return {
            'current_regime': self.current_regime.value,
            'confidence': self.confidence,
            'regime_count': len(self.regime_history),
            'last_change': self.regime_history[-1].timestamp if self.regime_history else None
        }

    def is_regime_stable(self, min_periods: int = 3) -> bool:
        """Check if current regime has been stable"""
        if len(self.regime_history) < min_periods:
            return False

        recent_regimes = [signal.regime for signal in self.regime_history[-min_periods:]]
        return all(regime == self.current_regime for regime in recent_regimes)