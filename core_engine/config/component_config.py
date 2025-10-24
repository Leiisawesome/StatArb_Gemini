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
    
    position_concentration_limit: float = 0.15
    """Maximum concentration per position. Default: 15%"""
    
    var_percentile: float = 95.0
    """VaR percentile. Default: 95.0"""
    
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
    
    # Backward compatibility properties
    @property
    def max_position_size(self) -> float:
        """Backward compatibility: access position_limits.max_position_size"""
        return self.position_limits.max_position_size
    
    @property
    def max_daily_var(self) -> float:
        """Backward compatibility: access risk_limits.max_daily_var"""
        return self.risk_limits.max_daily_var
    
    @property
    def max_positions(self) -> int:
        """Backward compatibility: access position_limits.max_positions"""
        return self.position_limits.max_positions
    
    @property
    def position_concentration_limit(self) -> float:
        """Backward compatibility: access risk_limits.position_concentration_limit"""
        return self.risk_limits.position_concentration_limit
    
    @property
    def confidence_level(self) -> float:
        """Backward compatibility: access risk_limits.confidence_level"""
        return self.risk_limits.confidence_level
    
    @property
    def var_percentile(self) -> float:
        """Backward compatibility: access risk_limits.var_percentile"""
        return self.risk_limits.var_percentile
    
    @property
    def stop_loss_pct(self) -> float:
        """Backward compatibility: access risk_limits.stop_loss_pct"""
        return self.risk_limits.stop_loss_pct
    
    @property
    def real_time_monitoring(self) -> bool:
        """Backward compatibility: access enable_real_time_risk"""
        return self.enable_real_time_risk
    
    @property
    def monitoring_frequency(self) -> int:
        """Backward compatibility: monitoring frequency in seconds. Default: 60"""
        return 60  # Default monitoring frequency
    
    @property
    def regime_risk_multipliers(self) -> dict:
        """Backward compatibility: regime risk multipliers"""
        return {
            'low_volatility': 0.8,
            'normal_volatility': 1.0,
            'high_volatility': 1.3,
            'extreme_volatility': 1.8
        }
    
    @property
    def strategy_allocation_limit(self) -> float:
        """Backward compatibility: strategy allocation limit. Default: 0.33 (33%)"""
        return 0.33


@dataclass
class ExposureConfig:
    """
    Exposure calculator configuration
    
    Centralized from core_engine/risk/exposure_calculator.py
    Parameters for portfolio exposure tracking and limit monitoring.
    """
    cache_ttl_seconds: int = 300
    """Cache time-to-live in seconds. Default: 300 (5 minutes)"""
    
    include_derivatives: bool = True
    """Include derivatives in exposure calculations. Default: True"""
    
    include_cash: bool = True
    """Include cash positions in exposure calculations. Default: True"""
    
    base_currency: str = 'USD'
    """Base currency for exposure calculations. Default: 'USD'"""
    
    # Exposure limits
    max_net_exposure: float = 1.0
    """Maximum net exposure as % of portfolio. Default: 100%"""
    
    max_gross_exposure: float = 2.0
    """Maximum gross exposure as % of portfolio. Default: 200%"""
    
    max_sector_exposure: float = 0.30
    """Maximum sector exposure as % of portfolio. Default: 30%"""
    
    max_single_position: float = 0.15
    """Maximum single position as % of portfolio. Default: 15%"""


@dataclass
class VarConfig:
    """
    VaR calculator configuration
    
    Centralized from core_engine/risk/var_calculator.py
    Parameters for Value at Risk calculations.
    """
    default_confidence: float = 0.95
    """Default confidence level for VaR. Default: 95%"""
    
    default_method: str = 'historical'
    """Default VaR method ('historical', 'parametric', 'monte_carlo'). Default: 'historical'"""
    
    monte_carlo_simulations: int = 10000
    """Number of Monte Carlo simulations. Default: 10,000"""
    
    historical_window: int = 252
    """Historical lookback window in days. Default: 252 (1 year)"""
    
    parametric_distribution: str = 'normal'
    """Distribution for parametric VaR ('normal', 'student_t'). Default: 'normal'"""
    
    enable_cvar: bool = True
    """Enable Conditional VaR (Expected Shortfall) calculation. Default: True"""
    
    cache_results: bool = True
    """Enable result caching. Default: True"""
    
    cache_ttl_seconds: int = 300
    """Cache time-to-live in seconds. Default: 300 (5 minutes)"""


@dataclass
class StressTestConfig:
    """
    Stress tester configuration
    
    Centralized from core_engine/risk/stress_tester.py
    Parameters for portfolio stress testing.
    """
    enable_market_crash: bool = True
    """Enable market crash scenario. Default: True"""
    
    enable_volatility_spike: bool = True
    """Enable volatility spike scenario. Default: True"""
    
    enable_correlation_breakdown: bool = True
    """Enable correlation breakdown scenario. Default: True"""
    
    enable_liquidity_crisis: bool = True
    """Enable liquidity crisis scenario. Default: True"""
    
    # Shock magnitudes (in standard deviations or percentage moves)
    market_crash_shock: float = -0.20
    """Market crash shock magnitude. Default: -20%"""
    
    volatility_spike_multiplier: float = 3.0
    """Volatility spike multiplier. Default: 3x normal"""
    
    correlation_increase: float = 0.50
    """Correlation increase in stress. Default: +50%"""
    
    liquidity_reduction: float = 0.70
    """Liquidity reduction in crisis. Default: -70%"""
    
    # Execution
    parallel_scenarios: bool = True
    """Run scenarios in parallel. Default: True"""
    
    max_workers: int = 4
    """Maximum parallel workers. Default: 4"""


@dataclass
class LimitConfig:
    """
    Limit monitor configuration
    
    Centralized from core_engine/risk/limit_monitor.py
    Parameters for risk limit monitoring and alerting.
    """
    # Alert settings
    enable_alerts: bool = True
    """Enable alert notifications. Default: True"""
    
    alert_cooldown_seconds: int = 300
    """Cooldown period between repeated alerts. Default: 300 (5 minutes)"""
    
    max_alerts_per_hour: int = 20
    """Maximum alerts per hour to prevent spam. Default: 20"""
    
    # Monitoring frequency
    check_frequency_seconds: int = 60
    """Frequency of limit checks in seconds. Default: 60 (1 minute)"""
    
    enable_real_time_monitoring: bool = True
    """Enable continuous real-time monitoring. Default: True"""
    
    # Limit breach thresholds
    warning_threshold: float = 0.80
    """Warning threshold (% of limit). Default: 80%"""
    
    critical_threshold: float = 0.95
    """Critical threshold (% of limit). Default: 95%"""
    
    emergency_threshold: float = 1.00
    """Emergency threshold (% of limit). Default: 100%"""
    
    # Breach tracking
    track_breach_history: bool = True
    """Track history of limit breaches. Default: True"""
    
    max_breach_history: int = 1000
    """Maximum breach history records. Default: 1000"""


@dataclass
class CorrelationConfig:
    """
    Correlation analyzer configuration
    
    Centralized from core_engine/risk/correlation_analyzer.py
    Parameters for correlation analysis and regime detection.
    """
    default_method: str = 'pearson'
    """Default correlation method ('pearson', 'spearman', 'kendall'). Default: 'pearson'"""
    
    rolling_window: int = 60
    """Rolling correlation window in periods. Default: 60"""
    
    min_periods: int = 30
    """Minimum periods for valid correlation. Default: 30"""
    
    # Regime detection
    enable_regime_detection: bool = True
    """Enable correlation regime detection. Default: True"""
    
    regime_detection_method: str = 'hmm'
    """Regime detection method ('hmm', 'clustering'). Default: 'hmm'"""
    
    n_regimes: int = 3
    """Number of correlation regimes. Default: 3"""
    
    # Tail dependence
    enable_tail_dependence: bool = True
    """Enable tail dependence analysis. Default: True"""
    
    tail_threshold: float = 0.05
    """Tail threshold for dependence analysis. Default: 5%"""
    
    # Performance
    enable_caching: bool = True
    """Enable correlation matrix caching. Default: True"""
    
    cache_ttl_seconds: int = 600
    """Cache time-to-live in seconds. Default: 600 (10 minutes)"""
    
    parallel_computation: bool = True
    """Enable parallel correlation computation. Default: True"""


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
    
    stoch_k_period: int = 14
    """Stochastic K period. Default: 14"""
    
    stoch_d_period: int = 3
    """Stochastic D period. Default: 3"""
    
    williams_r_period: int = 14
    """Williams %R period. Default: 14"""
    
    aroon_period: int = 25
    """Aroon period. Default: 25"""
    
    volume_sma_period: int = 20
    """Volume SMA period. Default: 20"""
    
    bb_period: int = 20
    """Bollinger Bands period (alias). Default: 20"""
    
    bb_std: float = 2.0
    """Bollinger Bands standard deviation (alias). Default: 2.0"""
    
    # Backward compatibility properties
    @property
    def enable_caching(self) -> bool:
        """Backward compatibility: access performance.enable_caching"""
        return self.performance.enable_caching if hasattr(self, 'performance') else True
    
    @property
    def parallel_processing(self) -> bool:
        """Backward compatibility: parallel processing support"""
        return False  # Default value
    
    @property
    def include_signals(self) -> bool:
        """Backward compatibility: include signals in output"""
        return True  # Default value
    
    @property
    def normalize_values(self) -> bool:
        """Backward compatibility: normalize indicator values"""
        return False  # Default value
    
    @property
    def timeframes(self) -> List[str]:
        """Backward compatibility: multi-timeframe list"""
        return ["5min", "1H", "1D", "1W"] if self.enable_multi_timeframe else []
    
    @property
    def enable_macro_indicators(self) -> bool:
        """Backward compatibility: enable macro indicators"""
        return False  # Default value
    
    @property
    def macro_symbols(self) -> List[str]:
        """Backward compatibility: macro symbol list"""
        return ["VIX", "DXY", "TNX", "TLT", "GLD", "USO", "HYG", "LQD", "EEM", "IWM"]


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
    Consolidated Regime Detection Configuration (Rule 1, Section 7)
    
    Single source of truth for ALL regime-related configuration parameters.
    Consolidates parameters from 7 previously scattered configs:
    - RegimeEngineConfig (engine.py)
    - RegimeAnalysisConfig (internal)
    - RegimeDetectionConfig (internal)
    - RegimeManagerConfig (regime_manager.py)
    - ClassificationConfig (regime_classifier.py)
    - IndicatorConfig (regime_indicators.py)
    - TransitionPredictionConfig (regime_transition_manager.py)
    
    Migration Note: Eliminates ~220 lines of duplicate configuration.
    """
    
    # ========================================================================
    # DETECTION PARAMETERS
    # ========================================================================
    
    lookback_window: int = 60
    """
    Lookback window for regime detection.
    Range: [20, 252]
    Default: 60 periods (3 months of daily data)
    Rationale: Balance between responsiveness and stability
    Migration: Was 'lookback_period' in some configs
    """
    
    lookback_period: int = 252
    """
    Long-term lookback period for historical analysis.
    Range: [60, 1260]
    Default: 252 (1 year of trading days)
    Rationale: Capture full market cycles
    Migration: Used in RegimeManagerConfig, RegimeDetectorConfig
    """
    
    detection_window: int = 60
    """
    Detection window for regime identification.
    Range: [20, 120]
    Default: 60 periods
    Rationale: Short-term regime changes
    """
    
    volatility_window: int = 20
    """
    Volatility calculation window.
    Range: [10, 60]
    Default: 20 periods
    Rationale: Standard volatility measurement period
    """
    
    trend_threshold: float = 0.02
    """
    Trend detection threshold.
    Range: [0.01, 0.05]
    Default: 0.02 (2%)
    Rationale: Minimum trend strength to be considered significant
    Migration: Was 'min_trend_threshold' in ClassificationConfig
    """
    
    regime_change_threshold: float = 0.7
    """
    Regime change confidence threshold.
    Range: [0.5, 0.9]
    Default: 0.7 (70%)
    Rationale: High confidence required for regime transitions
    """
    
    confidence_threshold: float = 0.6
    """
    Minimum confidence for regime classification.
    Range: [0.5, 0.9]
    Default: 0.6 (60%)
    Rationale: Acceptable confidence level for classification
    Migration: Was 'min_confidence_threshold' in various configs
    """
    
    # ========================================================================
    # UPDATE & TIMING PARAMETERS
    # ========================================================================
    
    update_frequency: int = 300
    """
    Regime update frequency in seconds.
    Range: [60, 3600]
    Default: 300 (5 minutes)
    Rationale: Balance between real-time and computational cost
    Migration: Was string 'daily'/'hourly' in old config, now int seconds
    """
    
    update_frequency_hours: int = 1
    """
    Update frequency in hours for manager-level operations.
    Range: [1, 24]
    Default: 1 hour
    Rationale: Manager coordination frequency
    Migration: From RegimeManagerConfig
    """
    
    # ========================================================================
    # PERSISTENCE & STABILITY PARAMETERS
    # ========================================================================
    
    regime_persistence: float = 0.8
    """
    Regime persistence threshold (stability indicator).
    Range: [0.5, 0.95]
    Default: 0.8
    Rationale: High persistence indicates stable regime
    """
    
    regime_persistence_threshold: int = 3
    """
    Minimum days a regime must persist to be considered stable.
    Range: [1, 10]
    Default: 3 days
    Rationale: Filter out noise and false signals
    Migration: From RegimeManagerConfig
    """
    
    min_regime_duration: int = 5
    """
    Minimum regime duration in periods.
    Range: [3, 20]
    Default: 5 periods
    Rationale: Avoid frequent regime switching
    """
    
    min_samples: int = 30
    """
    Minimum samples required for reliable regime detection.
    Range: [20, 60]
    Default: 30
    Rationale: Statistical significance
    """
    
    # ========================================================================
    # CORRELATION & THRESHOLDS
    # ========================================================================
    
    correlation_threshold: float = 0.7
    """
    Correlation threshold for regime analysis.
    Range: [0.5, 0.9]
    Default: 0.7
    Rationale: Strong correlation indicator
    """
    
    volatility_threshold: float = 0.015
    """
    Volatility threshold for regime classification.
    Range: [0.01, 0.05]
    Default: 0.015 (1.5%)
    Rationale: Distinguishes low/normal/high vol regimes
    Migration: From multiple configs with conflicts resolved
    """
    
    vol_percentile_threshold: float = 0.75
    """
    Volatility percentile threshold for regime categorization.
    Range: [0.6, 0.9]
    Default: 0.75 (75th percentile)
    Rationale: High volatility definition
    Migration: From IndicatorConfig
    """
    
    # ========================================================================
    # ML & CLASSIFICATION PARAMETERS
    # ========================================================================
    
    enable_enhanced_detection: bool = True
    """
    Enable enhanced multi-factor regime detection.
    Default: True
    Rationale: Improves detection accuracy
    """
    
    enable_transition_prediction: bool = True
    """
    Enable ML-based regime transition prediction.
    Default: True
    Rationale: Provides forward-looking regime insights
    """
    
    enable_ml_predictions: bool = True
    """
    Enable ML model predictions for regime classification.
    Default: True
    Rationale: Enhances classification with machine learning
    """
    
    model_retrain_frequency: int = 30
    """
    Model retraining frequency in days.
    Range: [7, 90]
    Default: 30 days
    Rationale: Monthly model updates to adapt to market changes
    Migration: From ClassificationConfig
    """
    
    ensemble_voting: str = "soft"
    """
    Ensemble model voting strategy.
    Options: 'soft', 'hard'
    Default: 'soft'
    Rationale: Weighted probabilities provide nuanced predictions
    Migration: From ClassificationConfig
    """
    
    # ========================================================================
    # INDICATOR CONFIGURATION
    # ========================================================================
    
    rsi_period: int = 14
    """
    RSI indicator period.
    Range: [10, 30]
    Default: 14
    Rationale: Standard RSI period
    """
    
    atr_period: int = 14
    """
    ATR indicator period.
    Range: [10, 30]
    Default: 14
    Rationale: Standard ATR period
    """
    
    momentum_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    """
    Momentum calculation periods for multi-timeframe analysis.
    Default: [5, 10, 20, 60] periods
    Rationale: Cover short to medium-term momentum
    Migration: From IndicatorConfig
    """
    
    vol_lookback_periods: List[int] = field(default_factory=lambda: [10, 20, 60, 252])
    """
    Volatility lookback periods for regime indicators.
    Default: [10, 20, 60, 252] periods
    Rationale: Multi-timeframe volatility analysis
    Migration: From IndicatorConfig
    """
    
    # ========================================================================
    # TRANSITION PREDICTION CONFIGURATION
    # ========================================================================
    
    prediction_horizon_days: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    """
    Prediction horizons for regime transitions.
    Default: [5, 10, 20, 60] days
    Rationale: Multiple forward-looking timeframes
    Migration: From TransitionPredictionConfig
    """
    
    feature_lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 252])
    """
    Feature engineering lookback periods.
    Default: [5, 10, 20, 60, 252] periods
    Rationale: Capture features across multiple timeframes
    Migration: From TransitionPredictionConfig
    """
    
    # ========================================================================
    # ADAPTATION & RISK PARAMETERS
    # ========================================================================
    
    max_portfolio_change: float = 0.25
    """
    Maximum portfolio change on regime transition.
    Range: [0.1, 0.5]
    Default: 0.25 (25%)
    Rationale: Limit drastic portfolio changes
    Migration: From RegimeManagerConfig
    """
    
    adaptation_speed: float = 0.5
    """
    Adaptation speed on regime changes (0-1 scale).
    Range: [0.1, 1.0]
    Default: 0.5
    Rationale: Moderate adaptation speed
    Migration: From RegimeManagerConfig
    """
    
    max_regime_risk_multiplier: float = 2.0
    """
    Maximum risk multiplier based on regime.
    Range: [1.0, 3.0]
    Default: 2.0
    Rationale: Allow risk increase in favorable regimes
    Migration: From RegimeManagerConfig
    """
    
    # ========================================================================
    # PERFORMANCE & MONITORING
    # ========================================================================
    
    performance_attribution_window: int = 252
    """
    Performance attribution window in days.
    Range: [60, 504]
    Default: 252 (1 year)
    Rationale: Full year performance tracking
    Migration: From RegimeManagerConfig
    """
    
    max_history_length: int = 1000
    """
    Maximum regime history to maintain (days).
    Range: [252, 2520]
    Default: 1000 days (~4 years)
    Rationale: Sufficient historical context
    Migration: From RegimeManagerConfig
    """
    
    # ========================================================================
    # PROCESSING CONFIGURATION
    # ========================================================================
    
    max_workers: int = 4
    """
    Maximum worker threads for parallel processing.
    Range: [1, 16]
    Default: 4
    Rationale: Balance parallelism and resource usage
    Migration: From RegimeManagerConfig
    """
    
    async_processing: bool = True
    """
    Enable asynchronous processing.
    Default: True
    Rationale: Non-blocking regime updates
    Migration: From RegimeManagerConfig
    """
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if not 20 <= self.lookback_window <= 252:
            raise ValueError(f"lookback_window must be [20, 252], got {self.lookback_window}")
        
        if not 0.5 <= self.confidence_threshold <= 0.9:
            raise ValueError(f"confidence_threshold must be [0.5, 0.9], got {self.confidence_threshold}")
        
        if not 0.01 <= self.trend_threshold <= 0.05:
            raise ValueError(f"trend_threshold must be [0.01, 0.05], got {self.trend_threshold}")
        
        if not 60 <= self.update_frequency <= 3600:
            raise ValueError(f"update_frequency must be [60, 3600] seconds, got {self.update_frequency}")
        
        if not 0.1 <= self.max_portfolio_change <= 0.5:
            raise ValueError(f"max_portfolio_change must be [0.1, 0.5], got {self.max_portfolio_change}")
        
        if not 1 <= self.max_workers <= 16:
            raise ValueError(f"max_workers must be [1, 16], got {self.max_workers}")


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


# ============================================================================
# DATA BRICK CONFIGURATIONS
# ============================================================================
# Consolidated from 4 scattered configs in data brick (Phase 1)
# Analysis: docs/03_compliance_audits/2025-10-21_data_config_analysis.md
# ============================================================================

@dataclass
class ConnectionConfig:
    """
    Database and connection configuration
    
    Consolidated from ClickHouseDataConfig and DataEngineConfig.
    """
    clickhouse_host: str = "localhost"
    """ClickHouse server host"""
    
    clickhouse_port: int = 8123
    """ClickHouse HTTP port (default: 8123)"""
    
    clickhouse_database: str = "polygon_data"
    """ClickHouse database name"""
    
    connect_timeout: float = 30.0
    """Connection timeout in seconds"""
    
    read_timeout: float = 10.0
    """Read timeout in seconds"""
    
    max_retry_attempts: int = 3
    """Maximum retry attempts for failed operations"""
    
    retry_delay_seconds: float = 1.0
    """Delay between retry attempts"""
    
    enable_circuit_breaker: bool = True
    """Enable circuit breaker for connection failures"""
    
    def __post_init__(self):
        """Validate connection configuration"""
        if self.connect_timeout <= 0:
            raise ValueError(f"connect_timeout must be positive, got {self.connect_timeout}")
        if self.read_timeout <= 0:
            raise ValueError(f"read_timeout must be positive, got {self.read_timeout}")
        if self.max_retry_attempts < 0:
            raise ValueError(f"max_retry_attempts must be non-negative, got {self.max_retry_attempts}")


@dataclass
class CachingConfig:
    """
    Caching configuration
    
    Consolidated from ClickHouseDataConfig and DataEngineConfig.
    """
    enable_caching: bool = True
    """Enable data caching"""
    
    cache_ttl: int = 300
    """Cache time-to-live in seconds (default: 5 minutes)"""
    
    max_cache_size: int = 1000
    """Maximum number of cached items"""
    
    cache_config: Optional[Dict[str, Any]] = None
    """Additional cache configuration (for advanced use)"""
    
    def __post_init__(self):
        """Validate caching configuration"""
        if self.cache_ttl < 0:
            raise ValueError(f"cache_ttl must be non-negative, got {self.cache_ttl}")
        if self.max_cache_size <= 0:
            raise ValueError(f"max_cache_size must be positive, got {self.max_cache_size}")


@dataclass
class DataValidationConfig:
    """
    Data validation configuration
    
    Consolidated from ValidationConfiguration and DataEngineConfig.
    """
    enable_data_validation: bool = True
    """Enable data validation"""
    
    quality_threshold: float = 0.95
    """Data quality threshold (0.0-1.0)"""
    
    # Price validation
    min_price: Optional[float] = None
    """Minimum valid price"""
    
    max_price: Optional[float] = None
    """Maximum valid price"""
    
    max_price_change_pct: float = 20.0
    """Maximum price change percentage"""
    
    # Spread validation
    max_spread_pct: float = 5.0
    """Maximum spread percentage"""
    
    max_spread_bps: float = 500.0
    """Maximum spread in basis points"""
    
    # Volume validation
    min_volume: float = 0
    """Minimum valid volume"""
    
    max_volume_spike_factor: float = 10.0
    """Maximum volume spike factor"""
    
    # Statistical validation
    outlier_threshold_std: float = 3.0
    """Outlier threshold in standard deviations"""
    
    moving_average_window: int = 20
    """Moving average window for validation"""
    
    # Timing validation
    max_data_age_seconds: float = 30.0
    """Maximum data age in seconds"""
    
    required_update_frequency_seconds: float = 1.0
    """Required update frequency"""
    
    # Completeness validation
    min_completeness_pct: float = 95.0
    """Minimum data completeness percentage"""
    
    # Cross-validation
    enable_cross_validation: bool = True
    """Enable cross-validation across sources"""
    
    max_cross_validation_diff_pct: float = 2.0
    """Maximum difference for cross-validation"""
    
    def __post_init__(self):
        """Validate data validation configuration"""
        if not 0 <= self.quality_threshold <= 1:
            raise ValueError(f"quality_threshold must be [0, 1], got {self.quality_threshold}")
        if self.max_price_change_pct < 0:
            raise ValueError(f"max_price_change_pct must be non-negative")
        if self.outlier_threshold_std <= 0:
            raise ValueError(f"outlier_threshold_std must be positive")


@dataclass
class FeedManagementConfig:
    """
    Feed management configuration
    
    Consolidated from FeedConfiguration.
    """
    enable_feed_management: bool = True
    """Enable feed management"""
    
    max_concurrent_requests: int = 10
    """Maximum concurrent requests per feed"""
    
    buffer_size: int = 10000
    """Buffer size for feed data"""
    
    max_message_size: int = 1048576
    """Maximum message size in bytes (default: 1MB)"""
    
    # Connection parameters
    heartbeat_interval: float = 30.0
    """Heartbeat interval in seconds"""
    
    reconnect_interval: float = 5.0
    """Reconnection interval in seconds"""
    
    max_reconnect_attempts: int = 10
    """Maximum reconnection attempts"""
    
    # Authentication (optional, per-feed)
    api_key: Optional[str] = None
    """API key for feed authentication"""
    
    secret_key: Optional[str] = None
    """Secret key for feed authentication"""
    
    # Quality settings
    enable_sequence_check: bool = True
    """Enable sequence number checking"""
    
    enable_timestamp_validation: bool = True
    """Enable timestamp validation"""
    
    def __post_init__(self):
        """Validate feed management configuration"""
        if self.max_concurrent_requests <= 0:
            raise ValueError(f"max_concurrent_requests must be positive")
        if self.buffer_size <= 0:
            raise ValueError(f"buffer_size must be positive")
        if self.heartbeat_interval <= 0:
            raise ValueError(f"heartbeat_interval must be positive")


@dataclass
class DataPerformanceConfig:
    """
    Performance and monitoring configuration
    
    Consolidated from DataEngineConfig.
    """
    max_concurrent_requests: int = 100
    """Maximum concurrent requests for data engine"""
    
    request_timeout_seconds: float = 30.0
    """Request timeout in seconds"""
    
    enable_performance_monitoring: bool = True
    """Enable performance monitoring"""
    
    monitoring_interval_seconds: float = 60.0
    """Performance monitoring interval"""
    
    enable_compression: bool = True
    """Enable data compression"""
    
    data_retention_days: int = 365
    """Data retention period in days"""
    
    def __post_init__(self):
        """Validate performance configuration"""
        if self.max_concurrent_requests <= 0:
            raise ValueError(f"max_concurrent_requests must be positive")
        if self.request_timeout_seconds <= 0:
            raise ValueError(f"request_timeout_seconds must be positive")
        if self.data_retention_days <= 0:
            raise ValueError(f"data_retention_days must be positive")


@dataclass
class DataConfig:
    """
    Centralized data configuration using composition pattern
    
    Consolidates 4 scattered configs from data brick:
    1. ClickHouseDataConfig (manager.py:126)
    2. DataEngineConfig (sources/clickhouse.py:53)
    3. FeedConfiguration (feeds/manager.py:72)
    4. ValidationConfiguration (validation/validator.py:116)
    
    Total parameters: 87 consolidated into 6 sub-configs + core params.
    Zero duplication (DRY principle enforced).
    
    Usage:
        from core_engine.config import DataConfig
        
        # Use with defaults
        config = DataConfig()
        
        # Customize sub-configs
        config = DataConfig(
            connection=ConnectionConfig(clickhouse_host="prod-db"),
            validation=DataValidationConfig(quality_threshold=0.98)
        )
    """
    
    # Sub-configurations (composition pattern - proven in regime brick)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    """Database connection configuration"""
    
    caching: CachingConfig = field(default_factory=CachingConfig)
    """Data caching configuration"""
    
    validation: DataValidationConfig = field(default_factory=DataValidationConfig)
    """Data validation configuration"""
    
    feeds: FeedManagementConfig = field(default_factory=FeedManagementConfig)
    """Feed management configuration"""
    
    performance: DataPerformanceConfig = field(default_factory=DataPerformanceConfig)
    """Performance and monitoring configuration"""
    
    # Core data parameters
    symbols: List[str] = field(default_factory=lambda: ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ'])
    """
    Symbols to trade/analyze.
    Default: Top liquid symbols from ClickHouse data.
    """
    
    start_date: Optional[str] = None
    """
    Start date for data range (YYYY-MM-DD format).
    If None, uses single date or real-time data.
    """
    
    end_date: Optional[str] = None
    """
    End date for data range (YYYY-MM-DD format).
    If None, uses start_date as single date.
    """
    
    interval: str = "1min"
    """
    Data interval/timeframe.
    Valid: '1min', '5min', '15min', '30min', '1h', '1D'
    """
    
    # Data engine mode
    mode: str = "live"
    """
    Data engine mode: 'live', 'backtest', 'simulation'
    """
    
    # Feature flags
    enable_market_data: bool = True
    """Enable market data processing"""
    
    enable_alternative_data: bool = True
    """Enable alternative data sources"""
    
    enable_data_lineage: bool = True
    """Enable data lineage tracking"""
    
    enable_audit_trail: bool = True
    """Enable audit trail logging"""
    
    enable_data_quality_monitoring: bool = True
    """Enable data quality monitoring"""
    
    # Storage
    enable_persistence: bool = True
    """Enable data persistence"""
    
    storage_path: Optional[str] = None
    """Storage path for persisted data"""
    
    # Backward compatibility (deprecated)
    target_date: Optional[str] = None
    """
    DEPRECATED: Use start_date/end_date instead.
    Single target date for backward compatibility.
    """
    
    def __post_init__(self):
        """Validate data configuration"""
        # Validate date ranges
        if self.start_date and self.end_date:
            from datetime import datetime
            try:
                start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
                if start_dt > end_dt:
                    raise ValueError(f"start_date ({self.start_date}) must be <= end_date ({self.end_date})")
            except ValueError as e:
                if "does not match format" in str(e):
                    raise ValueError(f"Dates must be in YYYY-MM-DD format. Error: {e}")
                raise
        
        # Handle deprecated target_date
        if self.target_date and not (self.start_date or self.end_date):
            warnings.warn(
                "target_date is deprecated. Use start_date/end_date instead.",
                DeprecationWarning,
                stacklevel=2
            )
            self.start_date = self.target_date
            self.end_date = self.target_date
        
        # Validate interval
        valid_intervals = ['1min', '5min', '15min', '30min', '1h', '4h', '1D', '1W', '1M']
        if self.interval not in valid_intervals:
            raise ValueError(f"interval must be one of {valid_intervals}, got {self.interval}")
        
        # Validate mode
        valid_modes = ['live', 'backtest', 'simulation', 'replay']
        if self.mode not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}, got {self.mode}")
        
        # Validate storage path if persistence enabled
        if self.enable_persistence and self.storage_path:
            import os
            if not os.path.isabs(self.storage_path):
                warnings.warn(
                    f"storage_path '{self.storage_path}' is relative. Consider using absolute path.",
                    UserWarning,
                    stacklevel=2
                )


# ============================================================================
# ANALYTICS BRICK CONFIGURATIONS (Phase 5 - Analytics Enhancement)
# ============================================================================

@dataclass
class PerformanceAnalyticsConfig:
    """
    Performance analytics configuration
    
    Consolidated from: analytics/performance_analyzer.py PerformanceConfig
    Professional performance analysis with institutional metrics.
    """
    # Risk-free rate
    risk_free_rate: float = 0.02
    """Annual risk-free rate for Sharpe/Sortino calculations. Default: 2%"""
    
    # Calculation parameters
    annualization_factor: int = 252
    """Trading days per year for annualization. Default: 252"""
    
    var_confidence_level: float = 0.95
    """Value at Risk confidence level. Default: 95%"""
    
    cvar_confidence_level: float = 0.95
    """Conditional VaR confidence level. Default: 95%"""
    
    # Rolling window settings
    rolling_window_days: int = 60
    """Rolling window for metrics calculation (days). Default: 60"""
    
    min_periods: int = 30
    """Minimum periods required for calculations. Default: 30"""
    
    # Analysis toggles
    enable_risk_adjusted_metrics: bool = True
    """Enable Sharpe, Sortino, Calmar calculations. Default: True"""
    
    enable_drawdown_analysis: bool = True
    """Enable drawdown tracking and analysis. Default: True"""
    
    enable_tail_risk_analysis: bool = True
    """Enable VaR, CVaR, tail risk metrics. Default: True"""
    
    enable_distribution_analysis: bool = True
    """Enable skewness, kurtosis analysis. Default: True"""
    
    # Performance thresholds
    min_sharpe_ratio: float = 0.5
    """Minimum acceptable Sharpe ratio. Default: 0.5"""
    
    max_drawdown_tolerance: float = 0.20
    """Maximum tolerable drawdown (%). Default: 20%"""
    
    def __post_init__(self):
        """Validate performance analytics configuration"""
        if not 0.0 <= self.risk_free_rate <= 0.10:
            raise ValueError(f"risk_free_rate must be [0, 0.10], got {self.risk_free_rate}")
        
        if not 200 <= self.annualization_factor <= 365:
            raise ValueError(f"annualization_factor must be [200, 365], got {self.annualization_factor}")
        
        if not 0.0 < self.var_confidence_level < 1.0:
            raise ValueError(f"var_confidence_level must be (0, 1), got {self.var_confidence_level}")


@dataclass
class MetricsCalculatorConfig:
    """
    Metrics calculator configuration
    
    Consolidated from: analytics/metrics_calculator.py MetricConfig
    Advanced metrics calculation with regime awareness.
    """
    # Risk-free rate
    risk_free_rate: float = 0.02
    """Annual risk-free rate. Default: 2%"""
    
    # Calculation parameters
    var_confidence_level: float = 0.95
    """VaR confidence level. Default: 95%"""
    
    var_method: str = "historical"
    """VaR calculation method: 'historical', 'parametric', 'monte_carlo'. Default: historical"""
    
    rolling_window: int = 60
    """Rolling window for calculations. Default: 60"""
    
    min_observations: int = 30
    """Minimum observations required. Default: 30"""
    
    # Metric categories to enable
    enable_return_metrics: bool = True
    """Enable return-based metrics. Default: True"""
    
    enable_risk_metrics: bool = True
    """Enable risk metrics. Default: True"""
    
    enable_risk_adjusted_metrics: bool = True
    """Enable risk-adjusted metrics. Default: True"""
    
    enable_drawdown_metrics: bool = True
    """Enable drawdown metrics. Default: True"""
    
    enable_distribution_metrics: bool = True
    """Enable distribution metrics. Default: True"""
    
    enable_trading_metrics: bool = True
    """Enable trading-specific metrics. Default: True"""
    
    # Performance settings
    enable_caching: bool = True
    """Enable metric caching. Default: True"""
    
    cache_ttl_seconds: int = 300
    """Cache TTL in seconds. Default: 300 (5 minutes)"""
    
    parallel_calculation: bool = True
    """Enable parallel metric calculation. Default: True"""
    
    max_workers: int = 4
    """Max parallel workers. Default: 4"""
    
    def __post_init__(self):
        """Validate metrics calculator configuration"""
        valid_var_methods = ['historical', 'parametric', 'monte_carlo']
        if self.var_method not in valid_var_methods:
            raise ValueError(f"var_method must be one of {valid_var_methods}, got {self.var_method}")
        
        if not 0.0 < self.var_confidence_level < 1.0:
            raise ValueError(f"var_confidence_level must be (0, 1), got {self.var_confidence_level}")


@dataclass
class AttributionAnalyticsConfig:
    """
    Attribution analytics configuration
    
    Consolidated from: analytics/attribution_analyzer.py AttributionConfig
    Performance attribution analysis configuration.
    """
    # Attribution methods
    enable_brinson_attribution: bool = True
    """Enable Brinson attribution (allocation, selection, interaction). Default: True"""
    
    enable_factor_attribution: bool = True
    """Enable factor-based attribution. Default: True"""
    
    enable_strategy_attribution: bool = True
    """Enable strategy-level attribution. Default: True"""
    
    # Analysis settings
    attribution_frequency: str = "daily"
    """Attribution calculation frequency: 'daily', 'weekly', 'monthly'. Default: daily"""
    
    min_attribution_periods: int = 20
    """Minimum periods for attribution. Default: 20"""
    
    # Factor settings
    factor_model: str = "fama_french_3"
    """Factor model: 'fama_french_3', 'fama_french_5', 'carhart_4'. Default: fama_french_3"""
    
    custom_factors: List[str] = field(default_factory=list)
    """Custom factor names. Default: []"""
    
    def __post_init__(self):
        """Validate attribution configuration"""
        valid_frequencies = ['daily', 'weekly', 'monthly', 'quarterly']
        if self.attribution_frequency not in valid_frequencies:
            raise ValueError(f"attribution_frequency must be one of {valid_frequencies}")
        
        valid_factor_models = ['fama_french_3', 'fama_french_5', 'carhart_4', 'custom']
        if self.factor_model not in valid_factor_models:
            raise ValueError(f"factor_model must be one of {valid_factor_models}")


@dataclass
class BenchmarkAnalyticsConfig:
    """
    Benchmark analytics configuration
    
    Consolidated from: analytics/benchmark_analyzer.py BenchmarkConfig
    Benchmark comparison and analysis configuration.
    """
    # Default benchmarks
    default_benchmarks: List[str] = field(default_factory=lambda: ["SPY", "QQQ"])
    """Default benchmark symbols. Default: ['SPY', 'QQQ']"""
    
    # Comparison settings
    enable_tracking_error: bool = True
    """Calculate tracking error. Default: True"""
    
    enable_information_ratio: bool = True
    """Calculate information ratio. Default: True"""
    
    enable_beta_analysis: bool = True
    """Calculate beta vs benchmarks. Default: True"""
    
    enable_correlation_analysis: bool = True
    """Calculate correlation analysis. Default: True"""
    
    # Calculation parameters
    rolling_window: int = 60
    """Rolling window for calculations. Default: 60"""
    
    min_correlation_periods: int = 30
    """Minimum periods for correlation. Default: 30"""
    
    def __post_init__(self):
        """Validate benchmark configuration"""
        if not self.default_benchmarks:
            warnings.warn("No default benchmarks configured", UserWarning, stacklevel=2)


@dataclass
class ReportGenerationConfig:
    """
    Report generation configuration
    
    Consolidated from: analytics/report_generator.py ReportConfig
    Analytics report generation and formatting.
    """
    # Report formats
    default_format: str = "html"
    """Default report format: 'html', 'pdf', 'json', 'excel'. Default: html"""
    
    enable_charts: bool = True
    """Include charts in reports. Default: True"""
    
    enable_tables: bool = True
    """Include tables in reports. Default: True"""
    
    # Report sections
    include_executive_summary: bool = True
    """Include executive summary. Default: True"""
    
    include_performance_metrics: bool = True
    """Include performance metrics. Default: True"""
    
    include_risk_metrics: bool = True
    """Include risk metrics. Default: True"""
    
    include_attribution_analysis: bool = True
    """Include attribution analysis. Default: True"""
    
    include_benchmark_comparison: bool = True
    """Include benchmark comparison. Default: True"""
    
    # Output settings
    output_directory: str = "analytics_reports"
    """Output directory for reports. Default: analytics_reports"""
    
    filename_template: str = "report_{timestamp}"
    """Report filename template. Default: report_{timestamp}"""
    
    auto_archive: bool = True
    """Auto-archive old reports. Default: True"""
    
    max_archive_days: int = 90
    """Keep reports for N days. Default: 90"""
    
    def __post_init__(self):
        """Validate report configuration"""
        valid_formats = ['html', 'pdf', 'json', 'excel', 'csv']
        if self.default_format not in valid_formats:
            raise ValueError(f"default_format must be one of {valid_formats}")


@dataclass
class AnalyticsConfig:
    """
    Centralized analytics configuration
    
    Consolidated from: analytics/manager_enhanced.py AnalyticsConfig
    Main configuration for the entire analytics system.
    
    **Rule 1 Section 7 Compliance:** Centralized analytics configuration.
    """
    # System settings
    mode: str = "realtime"
    """Analytics mode: 'realtime', 'batch', 'scheduled', 'on_demand'. Default: realtime"""
    
    max_workers: int = 4
    """Maximum parallel workers. Default: 4"""
    
    enable_caching: bool = True
    """Enable result caching. Default: True"""
    
    cache_ttl_hours: int = 24
    """Cache TTL in hours. Default: 24"""
    
    # Component configurations (composition pattern)
    performance: PerformanceAnalyticsConfig = field(default_factory=PerformanceAnalyticsConfig)
    """Performance analytics configuration"""
    
    metrics: MetricsCalculatorConfig = field(default_factory=MetricsCalculatorConfig)
    """Metrics calculator configuration"""
    
    attribution: AttributionAnalyticsConfig = field(default_factory=AttributionAnalyticsConfig)
    """Attribution analytics configuration"""
    
    benchmark: BenchmarkAnalyticsConfig = field(default_factory=BenchmarkAnalyticsConfig)
    """Benchmark analytics configuration"""
    
    reporting: ReportGenerationConfig = field(default_factory=ReportGenerationConfig)
    """Report generation configuration"""
    
    # Data settings
    min_data_points: int = 30
    """Minimum data points for analysis. Default: 30"""
    
    max_data_points: int = 50000
    """Maximum data points to process. Default: 50,000"""
    
    data_quality_threshold: float = 0.7
    """Minimum data quality score. Default: 0.7"""
    
    # Analysis toggles
    enable_performance_analysis: bool = True
    """Enable performance analysis. Default: True"""
    
    enable_attribution_analysis: bool = True
    """Enable attribution analysis. Default: True"""
    
    enable_benchmark_analysis: bool = True
    """Enable benchmark analysis. Default: True"""
    
    enable_factor_analysis: bool = True
    """Enable factor analysis. Default: True"""
    
    enable_risk_analysis: bool = True
    """Enable risk analysis. Default: True"""
    
    # Reporting settings
    auto_generate_reports: bool = True
    """Auto-generate reports. Default: True"""
    
    report_frequency: str = "daily"
    """Report frequency: 'daily', 'weekly', 'monthly'. Default: daily"""
    
    # Alert settings
    enable_alerts: bool = True
    """Enable performance alerts. Default: True"""
    
    performance_alert_threshold: float = -0.05
    """Performance alert threshold (%). Default: -5%"""
    
    risk_alert_threshold: float = 0.25
    """Risk alert threshold (VaR %). Default: 25%"""
    
    # Storage settings
    output_directory: str = "analytics_output"
    """Main output directory. Default: analytics_output"""
    
    archive_old_results: bool = True
    """Archive old results. Default: True"""
    
    max_archive_days: int = 90
    """Keep results for N days. Default: 90"""
    
    # Backward compatibility properties (for components expecting direct access)
    @property
    def risk_free_rate(self) -> float:
        """Backward compatibility: access performance.risk_free_rate"""
        return self.performance.risk_free_rate
    
    @property
    def var_confidence_level(self) -> float:
        """Backward compatibility: access metrics.var_confidence_level"""
        return self.metrics.var_confidence_level
    
    @property
    def rolling_window(self) -> int:
        """Backward compatibility: access metrics.rolling_window"""
        return self.metrics.rolling_window
    
    def __post_init__(self):
        """Validate analytics configuration"""
        valid_modes = ['realtime', 'batch', 'scheduled', 'on_demand']
        if self.mode not in valid_modes:
            raise ValueError(f"mode must be one of {valid_modes}, got {self.mode}")
        
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if self.report_frequency not in valid_frequencies:
            raise ValueError(f"report_frequency must be one of {valid_frequencies}")
        
        if not 0.0 < self.data_quality_threshold <= 1.0:
            raise ValueError(f"data_quality_threshold must be (0, 1.0], got {self.data_quality_threshold}")


# ============================================================================
# BROKER BRICK CONFIGURATIONS (Phase 6 - Broker Enhancement)
# ============================================================================

@dataclass
class BrokerConnectionConfig:
    """
    Broker connection configuration
    
    Consolidated from: broker/connection_manager.py ConnectionConfig
    Connection pooling and health management for broker connections.
    """
    # Connection parameters
    max_connections: int = 10
    """Maximum concurrent connections. Default: 10"""
    
    connection_timeout: float = 30.0
    """Connection timeout in seconds. Default: 30"""
    
    heartbeat_interval: float = 30.0
    """Heartbeat interval in seconds. Default: 30"""
    
    # Retry settings
    max_retry_attempts: int = 3
    """Maximum retry attempts. Default: 3"""
    
    retry_delay: float = 1.0
    """Initial retry delay in seconds. Default: 1.0"""
    
    backoff_multiplier: float = 2.0
    """Exponential backoff multiplier. Default: 2.0"""
    
    # Health check settings
    health_check_interval: float = 60.0
    """Health check interval in seconds. Default: 60"""
    
    health_timeout: float = 10.0
    """Health check timeout in seconds. Default: 10"""
    
    # Pool settings
    min_pool_size: int = 1
    """Minimum connection pool size. Default: 1"""
    
    max_pool_size: int = 5
    """Maximum connection pool size. Default: 5"""
    
    idle_timeout: float = 300.0
    """Idle connection timeout in seconds. Default: 300 (5 minutes)"""
    
    # Monitoring
    enable_monitoring: bool = True
    """Enable connection monitoring. Default: True"""
    
    metric_window: int = 100
    """Number of recent operations to track. Default: 100"""
    
    def __post_init__(self):
        """Validate broker connection configuration"""
        if self.max_connections < 1:
            raise ValueError(f"max_connections must be >= 1, got {self.max_connections}")
        
        if self.connection_timeout <= 0:
            raise ValueError(f"connection_timeout must be > 0, got {self.connection_timeout}")
        
        if self.min_pool_size > self.max_pool_size:
            raise ValueError(f"min_pool_size ({self.min_pool_size}) > max_pool_size ({self.max_pool_size})")


@dataclass
class BrokerSessionConfig:
    """
    Broker session configuration
    
    Consolidated from: broker/session_manager.py SessionConfig
    Session management and authentication configuration.
    """
    # Session settings
    session_timeout: float = 3600.0
    """Session timeout in seconds. Default: 3600 (1 hour)"""
    
    idle_timeout: float = 1800.0
    """Idle session timeout in seconds. Default: 1800 (30 minutes)"""
    
    max_sessions_per_user: int = 5
    """Maximum sessions per user. Default: 5"""
    
    # Security
    encrypt_session_data: bool = True
    """Encrypt session data. Default: True"""
    
    session_token_length: int = 32
    """Session token length. Default: 32"""
    
    require_ssl: bool = True
    """Require SSL/TLS. Default: True"""
    
    # Heartbeat
    heartbeat_interval: float = 30.0
    """Session heartbeat interval in seconds. Default: 30"""
    
    max_missed_heartbeats: int = 3
    """Maximum missed heartbeats before timeout. Default: 3"""
    
    # Recovery
    enable_session_recovery: bool = True
    """Enable session recovery. Default: True"""
    
    recovery_timeout: float = 300.0
    """Session recovery timeout in seconds. Default: 300 (5 minutes)"""
    
    # Monitoring
    log_session_events: bool = True
    """Log session events. Default: True"""
    
    track_session_metrics: bool = True
    """Track session metrics. Default: True"""
    
    def __post_init__(self):
        """Validate broker session configuration"""
        if self.session_timeout <= 0:
            raise ValueError(f"session_timeout must be > 0, got {self.session_timeout}")
        
        if self.idle_timeout > self.session_timeout:
            raise ValueError(f"idle_timeout ({self.idle_timeout}) > session_timeout ({self.session_timeout})")


@dataclass
class BrokerConfig:
    """
    Centralized broker configuration
    
    Consolidated from: broker/broker_manager.py BrokerConfig
    Main configuration for the entire broker system.
    
    **Rule 1 Section 7 Compliance:** Centralized broker configuration.
    """
    # Component configurations (composition pattern)
    connection: BrokerConnectionConfig = field(default_factory=BrokerConnectionConfig)
    """Broker connection configuration"""
    
    session: BrokerSessionConfig = field(default_factory=BrokerSessionConfig)
    """Broker session configuration"""
    
    # Execution settings
    default_venue: str = "smart_routing"
    """Default execution venue. Default: smart_routing"""
    
    enable_smart_routing: bool = True
    """Enable smart order routing. Default: True"""
    
    enable_order_aggregation: bool = True
    """Enable order aggregation. Default: True"""
    
    # Risk settings
    enable_pre_trade_risk: bool = True
    """Enable pre-trade risk checks. Default: True"""
    
    enable_real_time_risk: bool = True
    """Enable real-time risk monitoring. Default: True"""
    
    position_limit_check: bool = True
    """Enable position limit checking. Default: True"""
    
    # Monitoring
    enable_performance_monitoring: bool = True
    """Enable performance monitoring. Default: True"""
    
    enable_latency_monitoring: bool = True
    """Enable latency monitoring. Default: True"""
    
    metrics_collection_interval: float = 60.0
    """Metrics collection interval in seconds. Default: 60"""
    
    # Failover
    enable_automatic_failover: bool = True
    """Enable automatic failover. Default: True"""
    
    failover_threshold: float = 0.1
    """Failover error rate threshold. Default: 0.1 (10%)"""
    
    recovery_check_interval: float = 300.0
    """Recovery check interval in seconds. Default: 300 (5 minutes)"""
    
    # Backward compatibility properties
    @property
    def connection_config(self) -> BrokerConnectionConfig:
        """Backward compatibility: access connection sub-config"""
        return self.connection
    
    @property
    def session_config(self) -> BrokerSessionConfig:
        """Backward compatibility: access session sub-config"""
        return self.session
    
    @property
    def max_connections(self) -> int:
        """Backward compatibility: access connection.max_connections"""
        return self.connection.max_connections
    
    @property
    def connection_timeout(self) -> float:
        """Backward compatibility: access connection.connection_timeout"""
        return self.connection.connection_timeout
    
    def __post_init__(self):
        """Validate broker configuration"""
        valid_venues = ['smart_routing', 'primary', 'secondary', 'dark_pool', 'ecn']
        if self.default_venue not in valid_venues:
            raise ValueError(f"default_venue must be one of {valid_venues}, got {self.default_venue}")
        
        if not 0.0 < self.failover_threshold <= 1.0:
            raise ValueError(f"failover_threshold must be (0, 1.0], got {self.failover_threshold}")


# Export data configs
__all__ = [
    # ... existing exports ...
    # Data brick configs
    'ConnectionConfig',
    'CachingConfig',
    'DataValidationConfig',
    'FeedManagementConfig',
    'DataPerformanceConfig',
    'DataConfig',
    # Analytics brick configs (Phase 5 - Analytics Enhancement)
    'PerformanceAnalyticsConfig',
    'MetricsCalculatorConfig',
    'AttributionAnalyticsConfig',
    'BenchmarkAnalyticsConfig',
    'ReportGenerationConfig',
    'AnalyticsConfig',
    # Broker brick configs (Phase 6 - Broker Enhancement)
    'BrokerConnectionConfig',
    'BrokerSessionConfig',
    'BrokerConfig',
]
