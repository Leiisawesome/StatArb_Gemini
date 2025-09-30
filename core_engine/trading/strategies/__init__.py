"""
Trading Strategies Module
=========================

Comprehensive trading strategy framework with implementations.

This module provides:
- Strategy execution engine and lifecycle management
- Strategy validation and testing framework  
- Strategy optimization and parameter tuning
- Strategy registry and discovery
- Concrete strategy implementations

Components:
- strategy_engine: Core execution framework
- strategy_registry: Strategy catalog and metadata
- strategy_manager: Lifecycle management with enhanced factory integration
- strategy_validator: Quality assurance and validation
- strategy_optimizer: Parameter optimization
- implementations: 10 enhanced strategy implementations with ISystemComponent integration
"""

# Core framework exports
from .strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition, 
    StrategyMetrics, StrategyState, StrategyType
)

from .strategy_registry import StrategyRegistry, StrategyMetadata
from .strategy_manager import StrategyManager
from .strategy_validator import StrategyValidator
from .strategy_optimizer import StrategyOptimizer

# Strategy implementations
from .implementations import (
    EnhancedMomentumStrategy, MomentumConfig,
    EnhancedMeanReversionStrategy, MeanReversionConfig,
    EnhancedStatisticalArbitrageStrategy,
    EnhancedFactorStrategy, FactorConfig,
    EnhancedMultiAssetStrategy, MultiAssetConfig,
    EnhancedTrendFollowingStrategy, TrendFollowingConfig,
    EnhancedBreakoutStrategy, BreakoutConfig,
    EnhancedPairsTradingStrategy, PairsConfig,
    EnhancedVolatilityStrategy, VolatilityConfig,
    EnhancedArbitrageStrategy, ArbitrageConfig
)

__all__ = [
    # Core framework
    'BaseStrategy', 'StrategyConfig', 'StrategySignal', 'StrategyPosition',
    'StrategyMetrics', 'StrategyState', 'StrategyType',
    'StrategyRegistry', 'StrategyMetadata',
    'StrategyManager', 'StrategyValidator', 'StrategyOptimizer',
    
    # Strategy implementations
    'EnhancedMomentumStrategy', 'MomentumConfig',
    'EnhancedMeanReversionStrategy', 'MeanReversionConfig',
    'EnhancedStatisticalArbitrageStrategy',
    'EnhancedFactorStrategy', 'FactorConfig',
    'EnhancedMultiAssetStrategy', 'MultiAssetConfig',
    'EnhancedTrendFollowingStrategy', 'TrendFollowingConfig',
    'EnhancedBreakoutStrategy', 'BreakoutConfig',
    'EnhancedPairsTradingStrategy', 'PairsConfig',
    'EnhancedVolatilityStrategy', 'VolatilityConfig',
    'EnhancedArbitrageStrategy', 'ArbitrageConfig'
]
