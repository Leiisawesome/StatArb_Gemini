"""
Strategy Layer - Professional API
=================================

Multi-strategy coordination and management components.

Author: StatArb_Gemini Architecture (Phase 4)
Date: October 23, 2025
Version: 2.1.0

Note: Position sizing has been moved to Risk Manager (core_engine/risk/).
      Strategies should only generate signals, not size positions.
"""

# Strategy Management
from .manager import StrategyManager
from .base_strategy_enhanced import EnhancedBaseStrategy
from .strategy_registry import EnhancedStrategyRegistry
from .strategy_validator import EnhancedStrategyValidator
from .contracts import StrategySignal, StrategyState

# Multi-Strategy Coordination
from .multi_strategy_coordinator import (
    MultiStrategySignalAggregator,
    SignalConflictResolver
)

# Strategy Implementations
from .implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from .implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from .implementations.statistical_arbitrage.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from .implementations.pairs_trading.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from .implementations.factor.enhanced_factor import EnhancedFactorStrategy
from .implementations.multi_asset.enhanced_multi_asset import EnhancedMultiAssetStrategy
from .implementations.volatility.enhanced_volatility import EnhancedVolatilityStrategy
from .implementations.arbitrage.enhanced_arbitrage import EnhancedArbitrageStrategy

__all__ = [
    # Core Management
    'StrategyManager',
    'EnhancedBaseStrategy',
    'EnhancedStrategyRegistry',
    'EnhancedStrategyValidator',
    'StrategySignal',
    'StrategyState',

    # Multi-Strategy Coordination
    'MultiStrategySignalAggregator',
    'SignalConflictResolver',

    # Strategy Implementations
    'EnhancedMomentumStrategy',
    'EnhancedMeanReversionStrategy',
    'EnhancedStatisticalArbitrageStrategy',
    'EnhancedPairsTradingStrategy',
    'EnhancedFactorStrategy',
    'EnhancedMultiAssetStrategy',
    'EnhancedVolatilityStrategy',
    'EnhancedArbitrageStrategy',
]

__version__ = '2.1.0'
