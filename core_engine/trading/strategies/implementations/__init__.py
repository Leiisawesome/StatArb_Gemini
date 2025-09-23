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
from .momentum.advanced_momentum import AdvancedMomentumStrategy, MomentumConfig

# Mean Reversion Strategies
from .mean_reversion.advanced_mean_reversion import AdvancedMeanReversionStrategy, MeanReversionConfig

# Statistical Arbitrage Strategies
from .statistical_arbitrage.advanced_statistical_arbitrage import AdvancedStatisticalArbitrageStrategy, StatisticalArbitrageConfig

# Factor-based Strategies
from .factor.advanced_factor import AdvancedFactorStrategy, FactorConfig

# Multi-asset Strategies
from .multi_asset.advanced_multi_asset import AdvancedMultiAssetStrategy, MultiAssetConfig

# Trend Following Strategies
from .trend_following.advanced_trend_following import AdvancedTrendFollowingStrategy, TrendFollowingConfig

# Breakout Strategies
from .breakout.advanced_breakout import AdvancedBreakoutStrategy, BreakoutConfig

# Pairs Trading Strategies
from .pairs_trading.advanced_pairs_trading import AdvancedPairsTradingStrategy, PairsTradingConfig

# Volatility Strategies
from .volatility.advanced_volatility import AdvancedVolatilityStrategy, VolatilityStrategyConfig

# Arbitrage Strategies
from .arbitrage.advanced_arbitrage import AdvancedArbitrageStrategy, ArbitrageStrategyConfig

# Import statements will be added as more implementations are created
# Currently empty - implementations will be migrated from scattered locations
__all__ = [
    'AdvancedMomentumStrategy',
    'MomentumConfig',
    'AdvancedMeanReversionStrategy',
    'MeanReversionConfig',
    'AdvancedStatisticalArbitrageStrategy',
    'StatisticalArbitrageConfig',
    'AdvancedFactorStrategy',
    'FactorConfig',
    'AdvancedMultiAssetStrategy',
    'MultiAssetConfig',
    'AdvancedTrendFollowingStrategy',
    'TrendFollowingConfig',
    'AdvancedBreakoutStrategy',
    'BreakoutConfig',
    'AdvancedPairsTradingStrategy',
    'PairsTradingConfig',
    'AdvancedVolatilityStrategy',
    'VolatilityStrategyConfig',
    'AdvancedArbitrageStrategy',
    'ArbitrageStrategyConfig'
]
