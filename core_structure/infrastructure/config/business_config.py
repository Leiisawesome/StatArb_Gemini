"""
Business Configuration System for StatArb Trading System
=======================================================

This module consolidates business logic configurations including trading,
risk management, and AI/ML systems into a unified business configuration system.

Consolidated from:
- trading_config.py (363 lines) - Trading strategies and execution
- risk_config.py (346 lines) - Risk management parameters  
- ai_config.py (353 lines) - AI/ML model configurations
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from datetime import time, datetime, timedelta
from pathlib import Path
from .core_config import BaseConfig

# =============================================================================
# Trading Configuration System
# =============================================================================

@dataclass
class MarketConfig(BaseConfig):
    """Market and trading hours configuration"""
    
    # Market identification
    market_name: str = "US_EQUITY"
    exchange_timezone: str = "America/New_York"
    
    # Trading hours
    market_open: time = time(9, 30)  # 9:30 AM
    market_close: time = time(16, 0)  # 4:00 PM
    pre_market_start: time = time(4, 0)  # 4:00 AM
    after_market_end: time = time(20, 0)  # 8:00 PM
    
    # Trading sessions
    enable_pre_market: bool = False
    enable_after_market: bool = False
    extended_hours_risk_factor: float = 1.5
    
    # Market data
    data_feed_providers: List[str] = field(default_factory=lambda: ["polygon", "iex"])
    quote_precision: int = 4
    price_precision: int = 2
    quantity_precision: int = 0
    
    # Circuit breakers
    enable_circuit_breakers: bool = True
    level_1_threshold: float = 0.07  # 7%
    level_2_threshold: float = 0.13  # 13%
    level_3_threshold: float = 0.20  # 20%
    
    def validate(self) -> None:
        """Validate market configuration"""
        if self.market_open >= self.market_close:
            raise ValueError("Market close must be after market open")
        
        if self.price_precision < 0:
            raise ValueError("Price precision cannot be negative")
        
        if self.quantity_precision < 0:
            raise ValueError("Quantity precision cannot be negative")


@dataclass
class ExecutionConfig(BaseConfig):
    """Order execution configuration"""
    
    # Order routing
    primary_venue: str = "IEX"
    backup_venues: List[str] = field(default_factory=lambda: ["NYSE", "NASDAQ"])
    smart_order_routing: bool = True
    
    # Order types
    default_order_type: str = "LIMIT"
    allowed_order_types: List[str] = field(default_factory=lambda: ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"])
    
    # Execution timing
    order_timeout_seconds: int = 300  # 5 minutes
    fill_timeout_seconds: int = 600   # 10 minutes
    cancel_timeout_seconds: int = 30  # 30 seconds
    
    # Price improvement
    enable_price_improvement: bool = True
    max_price_improvement_bps: int = 5  # 5 basis points
    aggressive_timing_threshold: float = 0.8  # 80% of session remaining
    
    # Position sizing
    min_order_size: Decimal = Decimal("1")
    max_order_size: Decimal = Decimal("1000000")
    default_order_size: Decimal = Decimal("100")
    
    # Market impact
    enable_market_impact_model: bool = True
    max_participation_rate: float = 0.10  # 10% of volume
    twap_slice_minutes: int = 5
    vwap_lookback_minutes: int = 20
    
    # Risk controls
    enable_pre_trade_risk: bool = True
    enable_real_time_risk: bool = True
    max_order_value: Decimal = Decimal("1000000")
    max_daily_orders: int = 10000
    
    def validate(self) -> None:
        """Validate execution configuration"""
        if self.order_timeout_seconds <= 0:
            raise ValueError("Order timeout must be positive")
        
        if self.max_participation_rate <= 0 or self.max_participation_rate > 1:
            raise ValueError("Participation rate must be between 0 and 1")
        
        if self.min_order_size <= 0:
            raise ValueError("Minimum order size must be positive")


@dataclass
class StrategyConfig(BaseConfig):
    """Trading strategy configuration"""
    
    # Strategy identification
    strategy_name: str = ""
    strategy_version: str = "1.0.0"
    strategy_type: str = "statistical_arbitrage"
    
    # Universe selection
    universe_size: int = 500
    market_cap_min: Decimal = Decimal("1000000000")  # $1B
    volume_min: Decimal = Decimal("1000000")  # $1M daily
    price_min: Decimal = Decimal("5.00")
    
    # Strategy parameters
    lookback_window: int = 252  # 1 year
    rebalance_frequency: str = "daily"
    signal_decay_half_life: int = 5  # days
    
    # Pair selection
    correlation_threshold: float = 0.7
    cointegration_pvalue: float = 0.05
    min_pairs: int = 10
    max_pairs: int = 100
    
    # Signal generation
    z_score_entry: float = 2.0
    z_score_exit: float = 0.5
    z_score_stop: float = 4.0
    momentum_weight: float = 0.3
    mean_reversion_weight: float = 0.7
    
    # Position management
    target_gross_exposure: float = 1.0
    max_gross_exposure: float = 1.5
    target_net_exposure: float = 0.0
    max_net_exposure: float = 0.2
    
    def validate(self) -> None:
        """Validate strategy configuration"""
        if not self.strategy_name:
            raise ValueError("Strategy name is required")
        
        if self.universe_size <= 0:
            raise ValueError("Universe size must be positive")
        
        if self.correlation_threshold < 0 or self.correlation_threshold > 1:
            raise ValueError("Correlation threshold must be between 0 and 1")


@dataclass
class PortfolioConfig(BaseConfig):
    """Portfolio management configuration"""
    
    # Portfolio sizing
    initial_capital: Decimal = Decimal("10000000")  # $10M
    max_leverage: float = 2.0
    cash_buffer: float = 0.05  # 5%
    
    # Risk budgeting
    var_confidence: float = 0.95
    var_horizon_days: int = 1
    expected_volatility: float = 0.15  # 15% annual
    
    # Diversification
    max_sector_weight: float = 0.25  # 25%
    max_single_position: float = 0.05  # 5%
    min_position_weight: float = 0.001  # 0.1%
    
    # Rebalancing
    rebalance_threshold: float = 0.02  # 2%
    rebalance_frequency: str = "daily"
    min_trade_size: Decimal = Decimal("1000")
    
    def validate(self) -> None:
        """Validate portfolio configuration"""
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if self.max_leverage < 1:
            raise ValueError("Max leverage must be >= 1")
        
        if self.cash_buffer < 0 or self.cash_buffer > 1:
            raise ValueError("Cash buffer must be between 0 and 1")


# =============================================================================
# Risk Management Configuration System
# =============================================================================

@dataclass
class PositionRiskConfig(BaseConfig):
    """Position-level risk management configuration"""
    
    # Position size limits
    max_position_value: Decimal = Decimal("1000000")  # $1M per position
    max_position_weight: float = 0.05  # 5% of portfolio
    min_position_value: Decimal = Decimal("1000")  # $1K minimum
    
    # Concentration limits
    max_single_stock_weight: float = 0.05  # 5% per stock
    max_sector_weight: float = 0.25  # 25% per sector
    max_industry_weight: float = 0.15  # 15% per industry
    max_country_weight: float = 0.50  # 50% per country
    
    # Liquidity requirements
    min_daily_volume: Decimal = Decimal("1000000")  # $1M
    max_adv_percentage: float = 0.05  # 5% of average daily volume
    liquidity_horizon_days: int = 5
    
    # Stop loss settings
    enable_stop_loss: bool = True
    stop_loss_percentage: float = 0.05  # 5%
    trailing_stop: bool = False
    trailing_stop_percentage: float = 0.02  # 2%
    
    def validate(self) -> None:
        """Validate position risk configuration"""
        if self.max_position_weight <= 0 or self.max_position_weight > 1:
            raise ValueError("Max position weight must be between 0 and 1")
        
        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage > 1:
            raise ValueError("Stop loss percentage must be between 0 and 1")


@dataclass
class PortfolioRiskConfig(BaseConfig):
    """Portfolio-level risk management configuration"""
    
    # Portfolio limits
    max_gross_exposure: float = 2.0  # 200%
    max_net_exposure: float = 0.2   # 20%
    max_leverage: float = 2.0
    
    # Drawdown controls
    max_daily_drawdown: float = 0.02  # 2%
    max_monthly_drawdown: float = 0.05  # 5%
    max_annual_drawdown: float = 0.15  # 15%
    
    # VaR limits
    daily_var_limit: float = 0.02  # 2%
    var_confidence_level: float = 0.95  # 95%
    var_calculation_method: str = "historical"  # historical, parametric, monte_carlo
    var_lookback_days: int = 252
    
    # Stress testing
    enable_stress_testing: bool = True
    stress_scenarios: List[str] = field(default_factory=lambda: ["market_crash", "liquidity_crisis", "rate_shock"])
    max_stress_loss: float = 0.10  # 10%
    
    # Correlation limits
    max_correlation_exposure: float = 0.3  # 30% to any single factor
    correlation_lookback_days: int = 63  # ~3 months
    
    def validate(self) -> None:
        """Validate portfolio risk configuration"""
        if self.max_leverage < 1:
            raise ValueError("Max leverage must be >= 1")
        
        if self.daily_var_limit <= 0 or self.daily_var_limit > 1:
            raise ValueError("Daily VaR limit must be between 0 and 1")


@dataclass
class MarketRiskConfig(BaseConfig):
    """Market-wide risk management configuration"""
    
    # Market conditions
    volatility_threshold: float = 0.25  # 25% implied volatility
    correlation_threshold: float = 0.8   # Market correlation
    liquidity_threshold: float = 0.5     # Relative to normal
    
    # Circuit breakers
    enable_volatility_circuit_breaker: bool = True
    volatility_circuit_breaker_threshold: float = 0.30  # 30%
    
    enable_correlation_circuit_breaker: bool = True
    correlation_circuit_breaker_threshold: float = 0.85  # 85%
    
    enable_drawdown_circuit_breaker: bool = True
    drawdown_circuit_breaker_threshold: float = 0.05  # 5%
    
    # Risk factors
    track_interest_rate_risk: bool = True
    track_currency_risk: bool = True
    track_sector_rotation_risk: bool = True
    track_momentum_risk: bool = True
    
    def validate(self) -> None:
        """Validate market risk configuration"""
        if self.volatility_threshold <= 0:
            raise ValueError("Volatility threshold must be positive")
        
        if self.correlation_threshold < 0 or self.correlation_threshold > 1:
            raise ValueError("Correlation threshold must be between 0 and 1")


# =============================================================================
# AI/ML Configuration System
# =============================================================================

@dataclass
class ModelConfig(BaseConfig):
    """Configuration for individual ML models"""
    
    # Model identification
    model_id: str = ""
    model_name: str = ""
    model_version: str = "1.0.0"
    model_type: str = ""  # regression, classification, clustering, etc.
    
    # Model artifacts
    model_path: str = ""
    weights_path: Optional[str] = None
    config_path: Optional[str] = None
    metadata_path: Optional[str] = None
    
    # Model parameters
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_names: List[str] = field(default_factory=list)
    target_names: List[str] = field(default_factory=list)
    
    # Training information
    training_start_date: Optional[datetime] = None
    training_end_date: Optional[datetime] = None
    training_samples: int = 0
    validation_score: float = 0.0
    test_score: float = 0.0
    
    # Performance metrics
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_score: Optional[float] = None
    
    # Model lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deployed_at: Optional[datetime] = None
    status: str = "training"  # training, validation, deployed, deprecated
    
    # Resource requirements
    memory_requirement_mb: int = 1024  # 1GB default
    cpu_cores: int = 1
    gpu_required: bool = False
    inference_latency_ms: int = 100
    
    def validate(self) -> None:
        """Validate model configuration"""
        # Only validate if model is actually configured for use
        if self.model_id or self.model_name or self.model_path:
            if not self.model_id:
                raise ValueError("Model ID is required")
            
            if not self.model_name:
                raise ValueError("Model name is required")
            
            if not self.model_type:
                raise ValueError("Model type is required")
            
            if self.memory_requirement_mb <= 0:
                raise ValueError("Memory requirement must be positive")
            
            if self.cpu_cores <= 0:
                raise ValueError("CPU cores must be positive")
            
            if self.inference_latency_ms <= 0:
                raise ValueError("Inference latency must be positive")


@dataclass
class LLMConfig(BaseConfig):
    """Large Language Model configuration"""
    
    # Provider settings
    provider: str = "openai"  # openai, anthropic, huggingface, local
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    
    # Model parameters
    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 40000
    max_retries: int = 3
    retry_delay_seconds: int = 1
    
    # Context management
    max_context_length: int = 32000
    context_window_overlap: int = 500
    enable_context_compression: bool = True
    
    def validate(self) -> None:
        """Validate LLM configuration"""
        # Only validate if LLM is actually configured for use
        if self.provider != "openai" or self.model_name != "gpt-4" or self.api_key:
            if not self.provider:
                raise ValueError("Provider is required")
            
            if not self.model_name:
                raise ValueError("Model name is required")
            
            if self.temperature < 0 or self.temperature > 2:
                raise ValueError("Temperature must be between 0 and 2")
            
            if self.max_tokens <= 0:
                raise ValueError("Max tokens must be positive")


@dataclass
class MLPipelineConfig(BaseConfig):
    """Machine learning pipeline configuration"""
    
    # Data pipeline
    feature_engineering_steps: List[str] = field(default_factory=list)
    data_preprocessing_steps: List[str] = field(default_factory=list)
    data_validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    # Training configuration
    train_test_split: float = 0.8
    validation_split: float = 0.2
    cross_validation_folds: int = 5
    random_state: int = 42
    
    # Model selection
    model_selection_metric: str = "sharpe_ratio"
    model_selection_direction: str = "maximize"  # maximize or minimize
    hyperparameter_optimization: str = "bayesian"  # grid, random, bayesian
    
    # Training settings
    max_training_time_hours: int = 24
    early_stopping_patience: int = 10
    learning_rate_schedule: str = "adaptive"
    batch_size: int = 32
    
    # Model ensemble
    enable_ensemble: bool = True
    ensemble_method: str = "voting"  # voting, stacking, bagging
    ensemble_size: int = 5
    
    def validate(self) -> None:
        """Validate ML pipeline configuration"""
        if self.train_test_split <= 0 or self.train_test_split >= 1:
            raise ValueError("Train test split must be between 0 and 1")
        
        if self.validation_split <= 0 or self.validation_split >= 1:
            raise ValueError("Validation split must be between 0 and 1")
        
        if self.cross_validation_folds < 2:
            raise ValueError("Cross validation folds must be >= 2")


@dataclass
class AIAgentConfig(BaseConfig):
    """AI agent configuration for autonomous trading decisions"""
    
    # Agent settings
    agent_name: str = "StatArb_AI_Agent"
    agent_version: str = "1.0.0"
    enable_autonomous_mode: bool = False
    human_approval_required: bool = True
    
    # Decision making
    confidence_threshold: float = 0.8
    risk_tolerance: str = "moderate"  # conservative, moderate, aggressive
    decision_frequency: str = "hourly"  # minute, hourly, daily
    
    # Learning settings
    enable_online_learning: bool = True
    learning_rate: float = 0.001
    experience_buffer_size: int = 10000
    update_frequency: int = 100
    
    # Safety settings
    enable_kill_switch: bool = True
    max_daily_trades: int = 100
    max_position_size: float = 0.05  # 5% of portfolio
    
    def validate(self) -> None:
        """Validate AI agent configuration"""
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        
        if self.learning_rate <= 0:
            raise ValueError("Learning rate must be positive")
        
        if self.max_position_size <= 0 or self.max_position_size > 1:
            raise ValueError("Max position size must be between 0 and 1")


# =============================================================================
# Consolidated Business Configuration
# =============================================================================

@dataclass
class BusinessConfig(BaseConfig):
    """Consolidated business configuration containing all business logic configs"""
    
    # Trading configurations
    market: MarketConfig = field(default_factory=MarketConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    
    # Risk configurations
    position_risk: PositionRiskConfig = field(default_factory=PositionRiskConfig)
    portfolio_risk: PortfolioRiskConfig = field(default_factory=PortfolioRiskConfig)
    market_risk: MarketRiskConfig = field(default_factory=MarketRiskConfig)
    
    # AI/ML configurations
    model: ModelConfig = field(default_factory=ModelConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ml_pipeline: MLPipelineConfig = field(default_factory=MLPipelineConfig)
    ai_agent: AIAgentConfig = field(default_factory=AIAgentConfig)
    
    def validate(self) -> None:
        """Validate all business configurations"""
        # Only validate if strategy name is set
        if self.strategy.strategy_name:
            self.strategy.validate()
        
        self.market.validate()
        self.execution.validate()
        self.portfolio.validate()
        self.position_risk.validate()
        self.portfolio_risk.validate()
        self.market_risk.validate()
        
        # Only validate AI configs if they have required fields
        if self.model.model_id:
            self.model.validate()
        if self.llm.provider:
            self.llm.validate()
        if self.ml_pipeline.model_selection_metric:
            self.ml_pipeline.validate()
        if self.ai_agent.agent_name:
            self.ai_agent.validate()


# =============================================================================
# Business Configuration Factory
# =============================================================================

class BusinessConfigFactory:
    """Factory for creating business configurations"""
    
    @staticmethod
    def create_default_config() -> BusinessConfig:
        """Create default business configuration"""
        # Create strategy config with required name first
        strategy = StrategyConfig(strategy_name="Default_Statistical_Arbitrage")
        
        # Create business config with pre-configured strategy
        config = BusinessConfig(strategy=strategy)
        
        return config
    
    @staticmethod
    def create_conservative_config() -> BusinessConfig:
        """Create conservative risk configuration"""
        config = BusinessConfig()
        
        # Conservative strategy settings
        config.strategy.z_score_entry = 2.5
        config.strategy.z_score_stop = 3.0
        config.strategy.target_gross_exposure = 0.8
        
        # Conservative risk settings
        config.position_risk.max_position_weight = 0.03  # 3%
        config.portfolio_risk.max_gross_exposure = 1.5
        config.portfolio_risk.max_daily_drawdown = 0.015  # 1.5%
        
        # Conservative AI settings
        config.ai_agent.risk_tolerance = "conservative"
        config.ai_agent.confidence_threshold = 0.9
        
        return config
    
    @staticmethod
    def create_aggressive_config() -> BusinessConfig:
        """Create aggressive risk configuration"""
        config = BusinessConfig()
        
        # Aggressive strategy settings
        config.strategy.z_score_entry = 1.5
        config.strategy.z_score_stop = 5.0
        config.strategy.target_gross_exposure = 1.5
        
        # Aggressive risk settings
        config.position_risk.max_position_weight = 0.08  # 8%
        config.portfolio_risk.max_gross_exposure = 2.5
        config.portfolio_risk.max_daily_drawdown = 0.03  # 3%
        
        # Aggressive AI settings
        config.ai_agent.risk_tolerance = "aggressive"
        config.ai_agent.confidence_threshold = 0.7
        
        return config


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Trading configurations
    'MarketConfig',
    'ExecutionConfig',
    'StrategyConfig',
    'PortfolioConfig',
    
    # Risk configurations
    'PositionRiskConfig',
    'PortfolioRiskConfig',
    'MarketRiskConfig',
    
    # AI/ML configurations
    'ModelConfig',
    'LLMConfig',
    'MLPipelineConfig',
    'AIAgentConfig',
    
    # Consolidated configuration
    'BusinessConfig',
    'BusinessConfigFactory'
]
