"""
Enhanced Component-Specific Configurations
==========================================

Consolidated configuration architecture following Phase 1-3 audit recommendations.
All configurations use canonical parameter definitions with proper validation.

Author: StatArb_Gemini Configuration Consolidation (Phase 4)
Date: October 21, 2025
Version: 2.0.0 (Consolidated Architecture)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import warnings


# ============================================================================
# SUB-CONFIGS: Reusable Configuration Building Blocks
# ============================================================================

@dataclass
class PositionLimits:
    """
    Position management limits (reusable across configs)
    
    Consolidated from 8 scattered configs with canonical defaults from Phase 3 analysis.
    """
    max_position_size: float = 0.10
    """Maximum position size as percentage of portfolio (0.0-1.0). Default: 10%"""
    
    max_position_pct: float = 0.05
    """Maximum position per symbol as percentage. Default: 5%"""
    
    base_position_pct: float = 0.02
    """Base position size for strategies. Default: 2%"""
    
    max_positions: int = 5
    """Maximum concurrent positions. Default: 5"""
    
    max_position_concentration: float = 0.15
    """Maximum concentration in single position. Default: 15%"""
    
    def __post_init__(self):
        """Validate position limits"""
        if not 0 < self.max_position_size <= 1.0:
            raise ValueError(f"max_position_size must be (0, 1.0], got {self.max_position_size}")
        
        if not 0 < self.max_position_pct <= self.max_position_size:
            raise ValueError(f"max_position_pct must be <= max_position_size")
        
        if not 0 < self.base_position_pct <= self.max_position_pct:
            raise ValueError(f"base_position_pct must be <= max_position_pct")
        
        if self.max_positions < 1:
            raise ValueError(f"max_positions must be >= 1, got {self.max_positions}")


@dataclass
class RiskLimits:
    """
    Risk management limits (reusable across configs)
    
    Consolidated from 6 scattered configs with canonical defaults from Phase 3 analysis.
    """
    confidence_level: float = 0.95
    """Statistical confidence level for VaR calculations. Default: 95%"""
    
    max_daily_var: float = 0.05
    """Maximum daily Value at Risk. Default: 5%"""
    
    stop_loss_pct: float = 0.02
    """Stop loss percentage. Default: 2%"""
    
    confidence_threshold: float = 0.6
    """Minimum signal confidence for execution. Default: 60%"""
    
    max_drawdown: float = 0.10
    """Maximum allowable drawdown. Default: 10%"""
    
    risk_free_rate: float = 0.02
    """Risk-free rate for Sharpe ratio calculations. Default: 2% annual"""
    
    def __post_init__(self):
        """Validate risk limits"""
        if not 0 < self.confidence_level < 1.0:
            raise ValueError(f"confidence_level must be (0, 1), got {self.confidence_level}")
        
        if not 0 < self.max_daily_var <= 1.0:
            raise ValueError(f"max_daily_var must be (0, 1.0], got {self.max_daily_var}")
        
        if not 0 <= self.stop_loss_pct <= 1.0:
            raise ValueError(f"stop_loss_pct must be [0, 1.0], got {self.stop_loss_pct}")
        
        if not 0 < self.confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be (0, 1.0], got {self.confidence_threshold}")


@dataclass
class TimingConfig:
    """
    Timing and frequency parameters (reusable across configs)
    
    Consolidated from 5 scattered configs with canonical defaults from Phase 3 analysis.
    """
    health_check_interval: int = 30
    """Health check interval in seconds. Default: 30s"""
    
    update_frequency: str = '1min'
    """Data update frequency ('1min', '5min', '1h', 'daily'). Default: '1min'"""
    
    max_holding_period: int = 20
    """Maximum holding period in days. Default: 20 days"""
    
    rebalance_frequency: str = 'daily'
    """Rebalance frequency ('intraday', 'daily', 'weekly'). Default: 'daily'"""
    
    heartbeat_interval: float = 30.0
    """Heartbeat interval in seconds. Default: 30.0s"""
    
    max_retry_attempts: int = 3
    """Maximum retry attempts for operations. Default: 3"""
    
    retry_delay: int = 5
    """Delay between retries in seconds. Default: 5s"""
    
    def __post_init__(self):
        """Validate timing parameters"""
        if self.health_check_interval < 1:
            raise ValueError(f"health_check_interval must be >= 1, got {self.health_check_interval}")
        
        valid_frequencies = ['1min', '5min', '15min', '30min', '1h', '4h', 'daily', 'weekly']
        if self.update_frequency not in valid_frequencies:
            warnings.warn(f"update_frequency '{self.update_frequency}' not in standard frequencies: {valid_frequencies}")
        
        if self.max_holding_period < 1:
            raise ValueError(f"max_holding_period must be >= 1, got {self.max_holding_period}")


@dataclass
class PerformanceConfig:
    """
    Performance and caching configuration (reusable across configs)
    
    Consolidated from performance-related parameters across multiple configs.
    """
    enable_caching: bool = True
    """Enable caching for performance. Default: True"""
    
    cache_ttl: int = 3600
    """Cache time-to-live in seconds. Default: 1 hour"""
    
    enable_performance_monitoring: bool = True
    """Enable performance monitoring. Default: True"""
    
    max_workers: int = 4
    """Maximum worker threads/processes. Default: 4"""
    
    calculation_threads: int = 2
    """Threads for calculations. Default: 2"""
    
    batch_size: int = 100
    """Batch size for processing. Default: 100"""


# ============================================================================
# DOMAIN CONFIGS: Using Composition Pattern
# ============================================================================

@dataclass
class DataConfig:
    """
    Data management configuration (ENHANCED)
    
    Original config expanded with canonical parameters from consolidation.
    """
    # Data source
    symbols: Optional[List[str]] = None
    """List of symbols to trade. Default: None (all available)"""
    
    target_date: str = "2024-12-20"
    """Target date for data retrieval. Format: YYYY-MM-DD"""
    
    start_date: Optional[str] = None
    """Start date for historical data. Format: YYYY-MM-DD"""
    
    end_date: Optional[str] = None
    """End date for historical data. Format: YYYY-MM-DD"""
    
    # Performance (composition)
    enable_caching: bool = True
    """Enable data caching. Default: True"""
    
    cache_ttl: int = 3600
    """Cache TTL in seconds. Default: 1 hour"""
    
    # Data quality
    enable_validation: bool = True
    """Enable data validation. Default: True"""
    
    min_data_points: int = 100
    """Minimum required data points. Default: 100"""
    
    # Update frequency
    update_frequency: str = '1min'
    """Data update frequency. Default: '1min'"""


@dataclass
class RiskConfig:
    """
    Risk management configuration (ENHANCED)
    
    Original config expanded with composition pattern and canonical parameters.
    """
    # Composition - reuse common configs
    position_limits: PositionLimits = field(default_factory=PositionLimits)
    """Position management limits"""
    
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    """Risk management limits"""
    
    # Risk-specific parameters (original)
    auto_approval_threshold: float = 0.01
    """Auto-approval threshold for low-risk trades. Default: 1%"""
    
    elevated_review_threshold: float = 0.05
    """Elevated review threshold for high-risk trades. Default: 5%"""
    
    emergency_threshold: float = 0.10
    """Emergency threshold for critical risk situations. Default: 10%"""
    
    # Additional risk parameters from consolidation
    enable_real_time_risk: bool = True
    """Enable real-time risk monitoring. Default: True"""
    
    enable_pre_trade_risk: bool = True
    """Enable pre-trade risk checks. Default: True"""


@dataclass
class ProcessingConfig:
    """
    Processing pipeline configuration (ENHANCED)
    
    Original config expanded with parameters from signal/feature/indicator configs.
    """
    # Signal processing (original)
    signal_threshold: float = 0.6
    """Minimum signal confidence threshold. Default: 60%"""
    
    feature_normalization: str = "robust"
    """Feature normalization method ('standard', 'robust', 'minmax'). Default: 'robust'"""
    
    enable_cross_sectional: bool = True
    """Enable cross-sectional analysis. Default: True"""
    
    # Performance
    enable_caching: bool = True
    """Enable processing result caching. Default: True"""
    
    calculation_threads: int = 2
    """Threads for parallel calculations. Default: 2"""
    
    # Signal combination
    min_confidence_threshold: float = 0.6
    """Minimum confidence for signal combination. Default: 60%"""


# ============================================================================
# NEW CONSOLIDATED CONFIGS
# ============================================================================

@dataclass
class IndicatorConfig:
    """
    Technical indicators configuration
    
    Consolidated from core_engine/processing/indicators/engine.py
    All 29+ indicator flags in one place.
    """
    # Performance
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    """Performance and caching settings"""
    
    # Output
    output_format: str = 'dataframe'
    """Output format ('dataframe', 'dict'). Default: 'dataframe'"""
    
    # Multi-timeframe
    enable_multi_timeframe: bool = False
    """Enable multi-timeframe calculations. Default: False"""
    
    primary_timeframe: str = '1min'
    """Primary timeframe for calculations. Default: '1min'"""
    
    # Indicator groups (all enabled by default for backward compatibility)
    enable_trend: bool = True
    """Enable trend indicators (SMA, EMA, MACD, etc.). Default: True"""
    
    enable_momentum: bool = True
    """Enable momentum indicators (RSI, Stochastic, etc.). Default: True"""
    
    enable_volatility: bool = True
    """Enable volatility indicators (BB, ATR, etc.). Default: True"""
    
    enable_volume: bool = True
    """Enable volume indicators (OBV, VWAP, etc.). Default: True"""
    
    # Specific indicator parameters
    sma_periods: List[int] = field(default_factory=lambda: [20, 50, 200])
    """SMA periods. Default: [20, 50, 200]"""
    
    ema_periods: List[int] = field(default_factory=lambda: [12, 26, 50])
    """EMA periods. Default: [12, 26, 50]"""
    
    rsi_period: int = 14
    """RSI period. Default: 14"""
    
    macd_fast: int = 12
    """MACD fast period. Default: 12"""
    
    macd_slow: int = 26
    """MACD slow period. Default: 26"""
    
    macd_signal: int = 9
    """MACD signal period. Default: 9"""
    
    bollinger_period: int = 20
    """Bollinger Bands period. Default: 20"""
    
    bollinger_std: float = 2.0
    """Bollinger Bands standard deviation. Default: 2.0"""
    
    atr_period: int = 14
    """ATR period. Default: 14"""
    
    adx_period: int = 14
    """ADX period. Default: 14"""


@dataclass
class FeatureConfig:
    """
    Feature engineering configuration
    
    Consolidated from core_engine/processing/features/engineer.py
    """
    # Normalization
    use_normalization: bool = True
    """Enable feature normalization. Default: True"""
    
    normalization_method: str = "robust"
    """Normalization method ('standard', 'robust', 'minmax'). Default: 'robust'"""
    
    # Cross-sectional features
    enable_cross_sectional: bool = True
    """Enable cross-sectional feature generation. Default: True"""
    
    cross_sectional_universe: Optional[List[str]] = None
    """Symbols for cross-sectional analysis. Default: None (all symbols)"""
    
    # Feature selection
    max_features: Optional[int] = None
    """Maximum features to select. Default: None (all features)"""
    
    feature_importance_threshold: float = 0.01
    """Minimum feature importance threshold. Default: 0.01"""
    
    # Lag features
    lag_periods: List[int] = field(default_factory=lambda: [1, 2, 3, 5])
    """Lag periods for feature generation. Default: [1, 2, 3, 5]"""
    
    # Lookback
    lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20])
    """Lookback periods for rolling statistics. Default: [5, 10, 20]"""
    
    # Performance
    enable_scaling: bool = True
    """Enable feature scaling. Default: True"""
    
    enable_caching: bool = True
    """Enable feature caching. Default: True"""


@dataclass
class SignalConfig:
    """
    Signal generation configuration
    
    Consolidated from core_engine/processing/signals/generator.py
    """
    # Signal thresholds
    signal_threshold: float = 0.6
    """Minimum signal threshold. Default: 60%"""
    
    confidence_threshold: float = 0.6
    """Minimum confidence threshold. Default: 60%"""
    
    # Risk parameters
    max_position_size: float = 0.10
    """Maximum position size. Default: 10%"""
    
    stop_loss_pct: float = 0.02
    """Stop loss percentage. Default: 2%"""
    
    # Signal processing
    enable_filtering: bool = True
    """Enable signal filtering. Default: True"""
    
    aggregation_method: str = "weighted"
    """Signal aggregation method ('weighted', 'average', 'max'). Default: 'weighted'"""
    
    # Performance
    enable_caching: bool = True
    """Enable signal caching. Default: True"""


@dataclass
class RegimeConfig:
    """
    Regime detection configuration
    
    Consolidated from 7 regime configs:
    - RegimeEngineConfig
    - RegimeAnalysisConfig
    - RegimeDetectionConfig
    - RegimeManagerConfig
    - ClassificationConfig
    - IndicatorConfig (regime)
    - TransitionPredictionConfig
    """
    # Detection parameters
    lookback_window: int = 60
    """Lookback window for regime detection. Default: 60 periods"""
    
    volatility_window: int = 20
    """Volatility calculation window. Default: 20 periods"""
    
    trend_threshold: float = 0.02
    """Trend detection threshold. Default: 2%"""
    
    regime_change_threshold: float = 0.7
    """Regime change confidence threshold. Default: 70%"""
    
    confidence_threshold: float = 0.6
    """Minimum confidence for regime classification. Default: 60%"""
    
    # Update frequency
    update_frequency: str = 'daily'
    """Regime update frequency ('daily', 'hourly', 'realtime'). Default: 'daily'"""
    
    # Persistence
    regime_persistence: float = 0.8
    """Regime persistence threshold. Default: 0.8"""
    
    min_regime_duration: int = 5
    """Minimum regime duration in periods. Default: 5"""
    
    # Correlation analysis
    correlation_threshold: float = 0.7
    """Correlation threshold for regime analysis. Default: 0.7"""
    
    # Enhanced detection
    enable_enhanced_detection: bool = True
    """Enable enhanced multi-factor regime detection. Default: True"""
    
    enable_transition_prediction: bool = True
    """Enable regime transition prediction. Default: True"""


@dataclass
class AnalyticsConfig:
    """
    Analytics configuration
    
    Consolidated from 14 analytics configs:
    - AnalyticsConfig (original)
    - AttributionConfig
    - BenchmarkConfig
    - MetricConfig
    - PerformanceConfig
    - Plus 9 from analytics/performance/
    """
    # Performance tracking
    enable_performance_tracking: bool = True
    """Enable performance tracking. Default: True"""
    
    enable_attribution_analysis: bool = True
    """Enable attribution analysis. Default: True"""
    
    # Risk-adjusted metrics
    confidence_level: float = 0.95
    """Confidence level for VaR/CVaR. Default: 95%"""
    
    risk_free_rate: float = 0.02
    """Risk-free rate for Sharpe ratio. Default: 2% annual"""
    
    # Benchmarking
    default_benchmark: str = 'SPY'
    """Default benchmark symbol. Default: 'SPY'"""
    
    enable_benchmark_tracking: bool = True
    """Enable benchmark tracking. Default: True"""
    
    # Reporting
    report_frequency: str = 'daily'
    """Report generation frequency. Default: 'daily'"""
    
    enable_drawdown_tracking: bool = True
    """Enable drawdown tracking. Default: True"""
    
    # Metrics
    lookback_period: int = 252
    """Lookback period for metrics (trading days). Default: 252 (1 year)"""
    
    enable_metrics: bool = True
    """Enable metrics calculation. Default: True"""
    
    # Performance
    enable_caching: bool = True
    """Enable analytics result caching. Default: True"""
    
    cache_ttl: int = 3600
    """Cache TTL in seconds. Default: 1 hour"""


@dataclass
class ExecutionConfig:
    """
    Execution configuration
    
    Consolidated from 4 execution configs:
    - ExecutionEngineConfig
    - ExecutionConfig (original)
    - ExecutionConfiguration
    - OrderExecutionConfig
    """
    # Composition
    timing: TimingConfig = field(default_factory=TimingConfig)
    """Timing and retry configuration"""
    
    # Execution parameters
    enable_smart_routing: bool = True
    """Enable smart order routing. Default: True"""
    
    enable_dark_pools: bool = False
    """Enable dark pool routing. Default: False"""
    
    # Timeouts
    execution_timeout: float = 30.0
    """Execution timeout in seconds. Default: 30.0s"""
    
    max_execution_time: float = 60.0
    """Maximum execution time in seconds. Default: 60.0s"""
    
    # Slippage
    max_slippage_pct: float = 0.005
    """Maximum acceptable slippage. Default: 0.5%"""
    
    # Algorithms
    default_algorithm: str = 'adaptive'
    """Default execution algorithm. Default: 'adaptive'"""
    
    enable_twap: bool = True
    """Enable TWAP algorithm. Default: True"""
    
    enable_vwap: bool = True
    """Enable VWAP algorithm. Default: True"""
    
    twap_duration_minutes: int = 30
    """TWAP duration in minutes. Default: 30"""
    
    vwap_participation_rate: float = 0.1
    """VWAP participation rate. Default: 10%"""
    
    # Risk checks
    enable_pre_trade_risk: bool = True
    """Enable pre-trade risk checks. Default: True"""


@dataclass
class PortfolioConfig:
    """
    Portfolio management configuration
    
    Consolidated from portfolio-related configs.
    """
    # Composition
    position_limits: PositionLimits = field(default_factory=PositionLimits)
    """Position limits"""
    
    timing: TimingConfig = field(default_factory=TimingConfig)
    """Timing configuration"""
    
    # Portfolio parameters
    initial_cash: float = 100000.0
    """Initial cash. Default: $100,000"""
    
    commission_rate: float = 0.001
    """Commission rate. Default: 0.1%"""
    
    min_cash_reserve: float = 1000.0
    """Minimum cash reserve. Default: $1,000"""
    
    enable_short_selling: bool = False
    """Enable short selling. Default: False"""
    
    # Rebalancing
    rebalance_frequency: str = 'daily'
    """Rebalance frequency. Default: 'daily'"""
    
    rebalance_threshold: float = 0.05
    """Rebalance if allocation drift exceeds threshold. Default: 5%"""


# ============================================================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================================================

# Maintain backward compatibility during transition
LegacyDataConfig = DataConfig
LegacyRiskConfig = RiskConfig
LegacyProcessingConfig = ProcessingConfig


# ============================================================================
# CONFIGURATION FACTORY
# ============================================================================

def create_default_config_set() -> Dict[str, Any]:
    """
    Create a complete set of default configurations
    
    Returns:
        Dictionary of all default configs
    """
    return {
        'data': DataConfig(),
        'risk': RiskConfig(),
        'processing': ProcessingConfig(),
        'indicators': IndicatorConfig(),
        'features': FeatureConfig(),
        'signals': SignalConfig(),
        'regime': RegimeConfig(),
        'analytics': AnalyticsConfig(),
        'execution': ExecutionConfig(),
        'portfolio': PortfolioConfig(),
    }


def validate_config_compatibility(config: Any) -> bool:
    """
    Validate configuration compatibility
    
    Args:
        config: Configuration object to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # All configs should be dataclasses
    if not hasattr(config, '__dataclass_fields__'):
        raise ValueError(f"Config {type(config).__name__} is not a dataclass")
    
    # Configs with sub-configs should have valid composition
    if hasattr(config, 'position_limits'):
        if not isinstance(config.position_limits, PositionLimits):
            raise ValueError("position_limits must be PositionLimits instance")
    
    if hasattr(config, 'risk_limits'):
        if not isinstance(config.risk_limits, RiskLimits):
            raise ValueError("risk_limits must be RiskLimits instance")
    
    if hasattr(config, 'timing'):
        if not isinstance(config.timing, TimingConfig):
            raise ValueError("timing must be TimingConfig instance")
    
    return True
