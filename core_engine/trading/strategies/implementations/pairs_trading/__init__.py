"""
Pairs Trading Strategies
=========================

Pairs trading strategies that exploit relative price movements between correlated
assets. These strategies identify deviations from historical price relationships
and trade the spread between the two assets.

Available Strategies:
- EnhancedPairsTradingStrategy: Legacy implementation using Z-score based entry/exit
- SESPairsTradingStrategy: Advanced implementation using Spread Exhaustion Scoring (SES)

SES Framework (v2.0):
The SES strategy applies sophisticated mean-reversion analysis to the spread series,
treating it as a synthetic mean-reverting asset. It uses 6 dimensions:
1. Spread Dislocation Quality (25%)
2. Individual Stock Analysis (20%)
3. Regime Compatibility (15%)
4. Volume Confirmation (15%)
5. Mean Reversion Speed (15%) - Half-life, Hurst, EWMA Z-score
6. Lead-Lag Exploitation (10%)
"""

from .enhanced_pairs_trading import EnhancedPairsTradingStrategy
from .ses_pairs_trading import (
    SESPairsTradingStrategy,
    SpreadExhaustionScorer,
    MeanReversionCore,
    PairMetrics,
    SESScoreBreakdown,
    PairStatus,
    SpreadDirection
)

__all__ = [
    # Legacy Strategy
    'EnhancedPairsTradingStrategy',
    
    # SES Strategy (v2.0)
    'SESPairsTradingStrategy',
    'SpreadExhaustionScorer',
    'MeanReversionCore',
    
    # Data Classes
    'PairMetrics',
    'SESScoreBreakdown',
    'PairStatus',
    'SpreadDirection',
]