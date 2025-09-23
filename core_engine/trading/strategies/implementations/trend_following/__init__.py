"""
Trend Following Strategies

Trend-following strategies that identify and capitalize on market trends.
These strategies aim to capture sustained directional movements in asset prices.
"""

from .advanced_trend_following import AdvancedTrendFollowingStrategy, TrendFollowingConfig, TrendIndicator, MovingAverageType

__all__ = [
    'AdvancedTrendFollowingStrategy',
    'TrendFollowingConfig',
    'TrendIndicator',
    'MovingAverageType'
]