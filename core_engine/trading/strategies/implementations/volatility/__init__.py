"""
Volatility Strategies

Volatility-based strategies that trade on changes in market volatility.
These include strategies that profit from volatility expansion, contraction,
or directional volatility moves using options, futures, or spot instruments.
"""

from .enhanced_volatility import EnhancedVolatilityStrategy, VolatilityConfig

__all__ = [
    'AdvancedVolatilityStrategy',
    'VolatilityStrategyConfig'
]