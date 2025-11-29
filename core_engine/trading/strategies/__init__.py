"""
Strategy Layer - Professional API
=================================

Multi-strategy coordination and management components.

Author: StatArb_Gemini Architecture (Phase 4)
Date: October 23, 2025
Version: 2.0.0
"""

# === POSITION SIZING (Single Source of Truth) ===
from .position_sizing import (
    # Pure functions
    calculate_position_size,
    calculate_fixed_fraction_size,
    calculate_volatility_adjusted_size,
    calculate_kelly_size,
    calculate_atr_based_size,
    calculate_signal_weighted_size,
    # Class-based
    PositionSizer,
    SizingConfig,
    SizingMethod
)

# Strategy Management
from .manager import StrategyManager
from .base_strategy_enhanced import EnhancedBaseStrategy
from .strategy_registry import EnhancedStrategyRegistry
from .strategy_validator import EnhancedStrategyValidator
from .strategy_engine import StrategyExecutionEngine

# Multi-Strategy Coordination
from .multi_strategy_coordinator import (
    MultiStrategySignalAggregator,
    SignalConflictResolver
)

# Strategy Implementations (10 enhanced strategies)
from .implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from .implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from .implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from .implementations.trend_following.enhanced_trend_following import EnhancedTrendFollowingStrategy
from .implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from .implementations.factor.enhanced_factor import EnhancedFactorStrategy
from .implementations.multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy
from .implementations.breakout.enhanced_breakout import EnhancedBreakoutStrategy
from .implementations.volatility.enhanced_volatility import EnhancedVolatilityStrategy
from .implementations.arbitrage.enhanced_arbitrage import EnhancedArbitrageStrategy

__all__ = [
    # Position Sizing (Single Source of Truth)
    'calculate_position_size',
    'calculate_fixed_fraction_size',
    'calculate_volatility_adjusted_size',
    'calculate_kelly_size',
    'calculate_atr_based_size',
    'calculate_signal_weighted_size',
    'PositionSizer',
    'SizingConfig',
    'SizingMethod',
    
    # Core Management
    'StrategyManager',
    'EnhancedBaseStrategy',
    'EnhancedStrategyRegistry',
    'EnhancedStrategyValidator',
    'StrategyExecutionEngine',
    
    # Multi-Strategy Coordination
    'MultiStrategySignalAggregator',
    'SignalConflictResolver',
    
    # Strategy Implementations
    'EnhancedMomentumStrategy',
    'EnhancedMeanReversionStrategy',
    'EnhancedStatisticalArbitrageStrategy',
    'EnhancedTrendFollowingStrategy',
    'EnhancedPairsTradingStrategy',
    'EnhancedFactorStrategy',
    'EnhancedMultiAssetStrategy',
    'EnhancedBreakoutStrategy',
    'EnhancedVolatilityStrategy',
    'EnhancedArbitrageStrategy',
]

__version__ = '2.0.0'
