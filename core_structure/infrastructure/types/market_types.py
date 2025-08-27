"""
Canonical Market Type Definitions
================================

Consolidates 4+ duplicate MarketRegime implementations.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime

class MarketRegime(Enum):
    """
    Canonical market regime types - consolidates all implementations
    
    Combines classifications from:
    - regime_detector.py (RegimeType)
    - technical_indicators.py (MarketRegime) 
    - data_processor.py (MarketRegime class)
    - market_impact.py (MarketRegime)
    """
    # Trend-based regimes
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    TRENDING = "trending"  # General trending (for compatibility)
    SIDEWAYS = "sideways"
    MEAN_REVERTING = "mean_reverting"
    
    # Volatility-based regimes  
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    VOLATILE = "volatile"  # General volatile (for compatibility)
    STABLE = "stable"
    
    # Market condition regimes
    NORMAL = "normal"  # Standard market conditions
    STRESSED = "stressed"  # High stress market conditions
    ILLIQUID = "illiquid"  # Low liquidity conditions
    CRISIS = "crisis"
    RECOVERY = "recovery"
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    MOMENTUM_CRASH = "momentum_crash"  # Academic momentum research (Cooper et al. 2004)
    
    # Special states
    UNKNOWN = "unknown"  # Cannot determine regime

class RegimeConfidence(Enum):
    """Regime confidence levels"""
    VERY_HIGH = 4  # >90%
    HIGH = 3       # 75-90%
    MEDIUM = 2     # 50-75%
    LOW = 1        # 25-50%
    VERY_LOW = 0   # <25%

@dataclass
class RegimeInfo:
    """
    Comprehensive market regime information
    
    Consolidates different regime data structures into one canonical form.
    """
    regime: MarketRegime
    confidence: float
    
    # From data_processor.py compatibility
    regime_id: Optional[int] = None
    regime_name: Optional[str] = None
    probability: Optional[float] = None
    volatility_level: Optional[str] = None  # low, medium, high
    trend_direction: Optional[str] = None   # bullish, bearish, sideways
    
    # From regime_detector.py compatibility
    probability_distribution: Optional[Dict[MarketRegime, float]] = None
    persistence: Optional[int] = None  # Number of periods in current regime
    features: Optional[Dict[str, float]] = None
    
    # Timestamps
    detected_at: Optional[datetime] = None
    last_change: Optional[datetime] = None
    duration: Optional[int] = None
    
    def __post_init__(self):
        """Initialize compatibility fields"""
        if self.regime_name is None:
            self.regime_name = self.regime.value
        if self.probability is None:
            self.probability = self.confidence
        if self.detected_at is None:
            self.detected_at = datetime.now()

# Aliases for backward compatibility
RegimeType = MarketRegime  # For regime_detector.py compatibility
