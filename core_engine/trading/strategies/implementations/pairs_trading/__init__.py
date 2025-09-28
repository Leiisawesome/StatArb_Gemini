"""
Pairs Trading Strategies

Pairs trading strategies that exploit relative price movements between correlated
assets. These strategies identify deviations from historical price relationships
and trade the spread between the two assets.
"""

from .enhanced_pairs_trading import EnhancedPairsTradingStrategy, PairsConfig

__all__ = [
    'AdvancedPairsTradingStrategy',
    'PairsTradingConfig'
]