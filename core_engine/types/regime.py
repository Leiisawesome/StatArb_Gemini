"""
Core Engine Regime Types

Lightweight market regime detection for standalone core_engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np


class RegimeState(Enum):
    """Market regime states"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


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