"""
Trading Strategies - Implementations
====================================

This module contains all concrete trading strategy implementations.
Each strategy inherits from BaseStrategy and implements the required interface.

Strategy Categories:
- Momentum Strategies
- Mean Reversion Strategies
- Statistical Arbitrage Strategies
- Factor-based Strategies
- Multi-asset Strategies
- Trend Following Strategies
- Breakout Strategies
- Pairs Trading Strategies
- Volatility Strategies
- Arbitrage Strategies

All strategies follow the BaseStrategy interface for consistency.
"""

# Momentum Strategies
from .momentum.enhanced_momentum import EnhancedMomentumStrategy, MomentumConfig

# Mean Reversion Strategies
from .mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy, MeanReversionConfig
from .mean_reversion.simplified_mean_reversion import SimplifiedMeanReversionStrategy

# Statistical Arbitrage Strategies
from .statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy

# Factor-based Strategies
from .factor.enhanced_factor import EnhancedFactorStrategy, FactorConfig

# Multi-asset Strategies
from .multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy, MultiAssetConfig

# Trend Following Strategies
from .trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy, TrendFollowingConfig

# Breakout Strategies
from .breakout.enhanced_breakout import EnhancedBreakoutStrategy, BreakoutConfig

# Pairs Trading Strategies
from .pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy, PairsConfig

# Volatility Strategies
from .volatility.enhanced_volatility import EnhancedVolatilityStrategy, VolatilityConfig

# Arbitrage Strategies
from .arbitrage.enhanced_arbitrage import EnhancedArbitrageStrategy, ArbitrageConfig

# Import statements will be added as more implementations are created
# Currently empty - implementations will be migrated from scattered locations
__all__ = [
    'EnhancedMomentumStrategy',
    'MomentumConfig',
    'EnhancedMeanReversionStrategy',
    'MeanReversionConfig',
    'SimplifiedMeanReversionStrategy',  # v5.0 simplified version
    'EnhancedStatisticalArbitrageStrategy',
    'EnhancedFactorStrategy',
    'FactorConfig',
    'EnhancedMultiAssetStrategy',
    'MultiAssetConfig',
    'EnhancedTrendFollowingStrategy',
    'TrendFollowingConfig',
    'EnhancedBreakoutStrategy',
    'BreakoutConfig',
    'EnhancedPairsTradingStrategy',
    'PairsConfig',
    'EnhancedVolatilityStrategy',
    'VolatilityConfig',
    'EnhancedArbitrageStrategy',
    'ArbitrageConfig'
]
