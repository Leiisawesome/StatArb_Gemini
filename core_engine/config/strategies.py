"""
Strategy Configurations
======================

Consolidated strategy configurations for all 10 enhanced strategy types.
Follows composition pattern with reusable sub-configs.

Author: StatArb_Gemini Configuration Consolidation (Phase 4)
Date: October 21, 2025
Version: 2.0.0 (Consolidated Architecture)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Import sub-configs from component_config
try:
    from .component_config import PositionLimits, RiskLimits, TimingConfig
except ImportError:
    # Fallback for development
    from core_engine.config.component_config import PositionLimits, RiskLimits, TimingConfig


# ============================================================================
# STRATEGY TYPE ENUM
# ============================================================================

class StrategyType(Enum):
    """Strategy types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    FACTOR = "factor"
    MULTI_ASSET = "multi_asset"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    PAIRS_TRADING = "pairs_trading"
    VOLATILITY = "volatility"
    ARBITRAGE = "arbitrage"


# ============================================================================
# BASE STRATEGY CONFIG
# ============================================================================

@dataclass
class BaseStrategyConfig:
    """
    Base configuration for all strategies (using composition pattern)
    
    Provides common parameters using reusable sub-configs to eliminate duplication.
    """
    # Identity
    name: str = "strategy"
    """Strategy name"""
    
    strategy_type: Optional[StrategyType] = None
    """Strategy type"""
    
    # Composition - reuse common configs (DRY principle)
    position_limits: PositionLimits = field(default_factory=PositionLimits)
    """Position management limits"""
    
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    """Risk management limits"""
    
    timing: TimingConfig = field(default_factory=TimingConfig)
    """Timing and frequency configuration"""
    
    # Common strategy parameters
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])
    """Symbols to trade. Default: Top 5 tech stocks"""
    
    profit_target_ratio: float = 2.0
    """Profit target as ratio of risk. Default: 2:1 risk/reward"""
    
    # Multi-timeframe
    enable_multi_timeframe: bool = False
    """Enable multi-timeframe analysis. Default: False"""
    
    primary_timeframe: str = '1min'
    """Primary timeframe. Default: '1min'"""
    
    secondary_timeframes: List[str] = field(default_factory=lambda: ['5min', '15min'])
    """Secondary timeframes. Default: ['5min', '15min']"""
    
    # Execution
    execution_timeout: float = 30.0
    """Execution timeout in seconds. Default: 30.0s"""


# ============================================================================
# SPECIFIC STRATEGY CONFIGS
# ============================================================================

@dataclass
class MomentumConfig(BaseStrategyConfig):
    """
    Momentum strategy configuration
    
    Consolidated from: trading/strategies/implementations/momentum/enhanced_momentum.py
    """
    strategy_type: StrategyType = StrategyType.MOMENTUM
    
    # Momentum-specific parameters
    lookback_period: int = 60
    """Momentum lookback period. Default: 60 bars"""
    
    momentum_threshold: float = 0.02
    """Minimum momentum threshold. Default: 2%"""
    
    rsi_period: int = 14
    """RSI period for momentum confirmation. Default: 14"""
    
    rsi_overbought: float = 70.0
    """RSI overbought level. Default: 70"""
    
    rsi_oversold: float = 30.0
    """RSI oversold level. Default: 30"""
    
    adx_period: int = 14
    """ADX period for trend strength. Default: 14"""
    
    adx_threshold: float = 25.0
    """Minimum ADX for trend confirmation. Default: 25"""
    
    def __post_init__(self):
        """Validate momentum configuration parameters"""
        if self.lookback_period <= 0:
            raise ValueError(f"lookback_period must be positive, got {self.lookback_period}")
        if self.rsi_period <= 0:
            raise ValueError(f"rsi_period must be positive, got {self.rsi_period}")
        if self.adx_period <= 0:
            raise ValueError(f"adx_period must be positive, got {self.adx_period}")


@dataclass
class MeanReversionConfig(BaseStrategyConfig):
    """
    Mean reversion strategy configuration
    
    Consolidated from: trading/strategies/implementations/mean_reversion/enhanced_mean_reversion.py
    """
    strategy_type: StrategyType = StrategyType.MEAN_REVERSION
    
    # Mean reversion parameters
    lookback_period: int = 20
    """Lookback for mean calculation. Default: 20 bars"""
    
    entry_zscore_threshold: float = 2.0
    """Z-score threshold for entry. Default: 2.0 std devs"""
    
    exit_zscore_threshold: float = 0.5
    """Z-score threshold for exit. Default: 0.5 std devs"""
    
    bollinger_std: float = 2.0
    """Bollinger Bands standard deviation. Default: 2.0"""
    
    atr_period: int = 14
    """ATR period for volatility. Default: 14"""


@dataclass
class StatisticalArbitrageConfig(BaseStrategyConfig):
    """
    Statistical arbitrage strategy configuration
    
    Consolidated from: trading/strategies/implementations/statistical_arbitrage/enhanced_statistical_arbitrage.py
    """
    strategy_type: StrategyType = StrategyType.STATISTICAL_ARBITRAGE
    
    # Cointegration parameters
    cointegration_lookback: int = 252
    """Cointegration lookback period. Default: 252 days (1 year)"""
    
    cointegration_threshold: float = 0.05
    """Cointegration p-value threshold. Default: 0.05"""
    
    # Entry/exit
    entry_zscore_threshold: float = 2.0
    """Entry z-score threshold. Default: 2.0"""
    
    exit_zscore_threshold: float = 0.5
    """Exit z-score threshold. Default: 0.5"""
    
    # Rebalancing
    rebalance_frequency: str = 'daily'
    """Rebalance frequency. Default: 'daily'"""
    
    hedge_ratio_method: str = 'ols'
    """Hedge ratio calculation method ('ols', 'tls'). Default: 'ols'"""


@dataclass
class FactorConfig(BaseStrategyConfig):
    """
    Factor strategy configuration
    
    Consolidated from: trading/strategies/implementations/factor/enhanced_factor.py
    """
    strategy_type: StrategyType = StrategyType.FACTOR
    
    # Factor parameters
    factors: List[str] = field(default_factory=lambda: ['momentum', 'value', 'quality', 'size'])
    """Factors to use. Default: ['momentum', 'value', 'quality', 'size']"""
    
    factor_weights: Dict[str, float] = field(default_factory=lambda: {
        'momentum': 0.3, 'value': 0.3, 'quality': 0.2, 'size': 0.2
    })
    """Factor weights. Default: Equal-ish weighting"""
    
    rebalance_frequency: int = 20
    """Rebalance every N days. Default: 20 days"""
    
    factor_lookback: int = 252
    """Factor calculation lookback. Default: 252 days"""
    
    min_factor_score: float = 0.5
    """Minimum composite factor score. Default: 0.5"""


@dataclass
class MultiAssetConfig(BaseStrategyConfig):
    """
    Multi-asset strategy configuration
    
    Consolidated from: trading/strategies/implementations/multi_asset/enhanced_multi_asset.py
    """
    strategy_type: StrategyType = StrategyType.MULTI_ASSET
    
    # Asset allocation
    asset_classes: List[str] = field(default_factory=lambda: ['equities', 'bonds', 'commodities'])
    """Asset classes to trade. Default: ['equities', 'bonds', 'commodities']"""
    
    target_allocations: Dict[str, float] = field(default_factory=lambda: {
        'equities': 0.6, 'bonds': 0.3, 'commodities': 0.1
    })
    """Target allocations. Default: 60/30/10"""
    
    rebalance_frequency: int = 10
    """Rebalance every N days. Default: 10 days"""
    
    rebalance_threshold: float = 0.05
    """Rebalance if drift exceeds threshold. Default: 5%"""
    
    correlation_lookback: int = 60
    """Correlation calculation lookback. Default: 60 days"""


@dataclass
class TrendFollowingConfig(BaseStrategyConfig):
    """
    Trend following strategy configuration
    
    Consolidated from: trading/strategies/implementations/trend_following/enhanced_trend_following.py
    """
    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    
    # Trend parameters
    fast_ma_period: int = 50
    """Fast moving average period. Default: 50"""
    
    slow_ma_period: int = 200
    """Slow moving average period. Default: 200"""
    
    adx_period: int = 14
    """ADX period for trend strength. Default: 14"""
    
    adx_threshold: float = 25.0
    """Minimum ADX for strong trend. Default: 25"""
    
    atr_period: int = 14
    """ATR period for stops. Default: 14"""
    
    atr_multiplier: float = 2.0
    """ATR multiplier for stop loss. Default: 2.0"""


@dataclass
class BreakoutConfig(BaseStrategyConfig):
    """
    Breakout strategy configuration
    
    Consolidated from: trading/strategies/implementations/breakout/enhanced_breakout.py
    """
    strategy_type: StrategyType = StrategyType.BREAKOUT
    
    # Breakout parameters
    lookback_period: int = 20
    """Lookback for support/resistance. Default: 20 bars"""
    
    breakout_threshold: float = 0.02
    """Breakout confirmation threshold. Default: 2%"""
    
    volume_confirmation: bool = True
    """Require volume confirmation. Default: True"""
    
    volume_multiplier: float = 1.5
    """Volume must exceed average by this factor. Default: 1.5x"""
    
    consolidation_periods: int = 10
    """Periods for consolidation detection. Default: 10"""


@dataclass
class PairsConfig(BaseStrategyConfig):
    """
    Pairs trading strategy configuration
    
    Consolidated from: trading/strategies/implementations/pairs_trading/enhanced_pairs_trading.py
    """
    strategy_type: StrategyType = StrategyType.PAIRS_TRADING
    
    # Pairs selection
    lookback_period: int = 252
    """Lookback for pair selection. Default: 252 days (1 year)"""
    
    correlation_threshold: float = 0.5
    """Minimum correlation to maintain pair. Default: 0.5"""
    
    cointegration_threshold: float = 0.05
    """Cointegration p-value threshold. Default: 0.05"""
    
    # Entry/exit
    entry_zscore_threshold: float = 2.0
    """Entry z-score threshold. Default: 2.0"""
    
    exit_zscore_threshold: float = 0.5
    """Exit z-score threshold. Default: 0.5"""
    
    # Pair management
    max_pairs: int = 5
    """Maximum concurrent pairs. Default: 5"""
    
    pair_reselection_frequency: int = 20
    """Reselect pairs every N days. Default: 20 days"""


@dataclass
class VolatilityConfig(BaseStrategyConfig):
    """
    Volatility strategy configuration
    
    Consolidated from: trading/strategies/implementations/volatility/enhanced_volatility.py
    """
    strategy_type: StrategyType = StrategyType.VOLATILITY
    
    # Volatility parameters
    volatility_window: int = 20
    """Volatility calculation window. Default: 20 bars"""
    
    volatility_threshold: float = 0.02
    """Volatility threshold for trading. Default: 2%"""
    
    regime_window: int = 60
    """Regime detection window. Default: 60 bars"""
    
    high_vol_threshold: float = 0.03
    """High volatility threshold. Default: 3%"""
    
    low_vol_threshold: float = 0.01
    """Low volatility threshold. Default: 1%"""


@dataclass
class ArbitrageConfig(BaseStrategyConfig):
    """
    Arbitrage strategy configuration
    
    Consolidated from: trading/strategies/implementations/arbitrage/enhanced_arbitrage.py
    """
    strategy_type: StrategyType = StrategyType.ARBITRAGE
    
    # Arbitrage parameters
    min_spread_bps: float = 5.0
    """Minimum spread in basis points. Default: 5 bps"""
    
    max_spread_bps: float = 50.0
    """Maximum spread in basis points. Default: 50 bps"""
    
    confidence_threshold: float = 0.8
    """Minimum confidence for execution. Default: 80%"""
    
    execution_speed: str = 'fast'
    """Execution speed requirement ('fast', 'normal'). Default: 'fast'"""
    
    max_execution_time: float = 5.0
    """Maximum execution time in seconds. Default: 5.0s"""
    
    # Venues
    enable_multi_venue: bool = True
    """Enable multi-venue arbitrage. Default: True"""


# ============================================================================
# STRATEGY FACTORY
# ============================================================================

def create_strategy_config(strategy_type: StrategyType, **kwargs) -> BaseStrategyConfig:
    """
    Factory function to create strategy configs
    
    Args:
        strategy_type: Type of strategy
        **kwargs: Additional configuration parameters
        
    Returns:
        Strategy configuration instance
    """
    config_map = {
        StrategyType.MOMENTUM: MomentumConfig,
        StrategyType.MEAN_REVERSION: MeanReversionConfig,
        StrategyType.STATISTICAL_ARBITRAGE: StatisticalArbitrageConfig,
        StrategyType.FACTOR: FactorConfig,
        StrategyType.MULTI_ASSET: MultiAssetConfig,
        StrategyType.TREND_FOLLOWING: TrendFollowingConfig,
        StrategyType.BREAKOUT: BreakoutConfig,
        StrategyType.PAIRS_TRADING: PairsConfig,
        StrategyType.VOLATILITY: VolatilityConfig,
        StrategyType.ARBITRAGE: ArbitrageConfig,
    }
    
    config_class = config_map.get(strategy_type)
    if not config_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return config_class(**kwargs)


def get_all_strategy_configs() -> Dict[StrategyType, BaseStrategyConfig]:
    """
    Get default configurations for all strategy types
    
    Returns:
        Dictionary mapping strategy types to default configs
    """
    return {
        strategy_type: create_strategy_config(strategy_type)
        for strategy_type in StrategyType
    }


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

# Maintain backward compatibility with old names
StrategyConfig = BaseStrategyConfig

