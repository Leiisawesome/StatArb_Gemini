"""
Trading Configuration for StatArb Trading System

This module provides trading-specific configuration classes for strategies,
execution, portfolio management, and market data.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from datetime import time
from .base_config import BaseConfig


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
    enable_overnight: bool = False
    
    # Market holidays
    observe_market_holidays: bool = True
    custom_trading_holidays: List[str] = field(default_factory=list)
    
    # Circuit breakers
    level_1_threshold: float = 0.07  # 7% decline
    level_2_threshold: float = 0.13  # 13% decline
    level_3_threshold: float = 0.20  # 20% decline
    
    # Market data settings
    quote_currency: str = "USD"
    price_precision: int = 4
    quantity_precision: int = 0
    
    def validate(self) -> None:
        """Validate market configuration"""
        if not self.market_name:
            raise ValueError("Market name is required")
        
        if not self.exchange_timezone:
            raise ValueError("Exchange timezone is required")
        
        if self.market_open >= self.market_close:
            raise ValueError("Market open must be before market close")
        
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
    max_order_value: Decimal = Decimal("1000000")
    max_position_concentration: float = 0.05  # 5% of portfolio
    enable_fat_finger_check: bool = True
    fat_finger_threshold: float = 2.0  # 2x average order size
    
    # Slippage and costs
    expected_slippage_bps: float = 2.0
    commission_per_share: Decimal = Decimal("0.005")
    sec_fee_rate: float = 0.0000278  # SEC fee rate
    
    def validate(self) -> None:
        """Validate execution configuration"""
        if not self.primary_venue:
            raise ValueError("Primary venue is required")
        
        if self.order_timeout_seconds <= 0:
            raise ValueError("Order timeout must be positive")
        
        if self.fill_timeout_seconds <= 0:
            raise ValueError("Fill timeout must be positive")
        
        if self.min_order_size <= 0:
            raise ValueError("Min order size must be positive")
        
        if self.max_order_size <= self.min_order_size:
            raise ValueError("Max order size must be greater than min order size")
        
        if not 0 < self.max_participation_rate <= 1:
            raise ValueError("Max participation rate must be between 0 and 1")
        
        if self.max_position_concentration <= 0 or self.max_position_concentration > 1:
            raise ValueError("Max position concentration must be between 0 and 1")


@dataclass
class StrategyConfig(BaseConfig):
    """Statistical arbitrage strategy configuration"""
    
    # Strategy identification
    strategy_name: str = "StatArb_Pairs"
    strategy_version: str = "1.0.0"
    
    # Universe selection
    universe_size: int = 500
    min_market_cap: Decimal = Decimal("1000000000")  # $1B
    min_avg_volume: int = 1000000  # 1M shares
    exclude_sectors: List[str] = field(default_factory=lambda: ["REIT", "Utilities"])
    
    # Pair selection
    correlation_window: int = 252  # trading days
    min_correlation: float = 0.7
    max_correlation: float = 0.95
    cointegration_pvalue_threshold: float = 0.05
    
    # Signal generation
    lookback_window: int = 20  # trading days
    z_score_entry_threshold: float = 2.0
    z_score_exit_threshold: float = 0.5
    stop_loss_threshold: float = 3.0
    
    # Position sizing
    max_pairs: int = 50
    target_leverage: float = 1.0
    position_sizing_method: str = "equal_weight"  # equal_weight, volatility_adjusted, kelly
    volatility_target: float = 0.15  # 15% annualized
    
    # Risk management
    max_drawdown: float = 0.10  # 10%
    var_confidence: float = 0.05  # 5% VaR
    max_correlation_exposure: float = 0.20  # 20% to any sector
    
    # Rebalancing
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    turnover_target: float = 2.0  # 200% annual turnover
    min_holding_period_hours: int = 4
    
    # Model parameters
    half_life_days: int = 5
    mean_reversion_speed: float = 0.1
    regime_detection_enabled: bool = True
    ml_models_enabled: bool = True
    
    def validate(self) -> None:
        """Validate strategy configuration"""
        if not self.strategy_name:
            raise ValueError("Strategy name is required")
        
        if self.universe_size <= 0:
            raise ValueError("Universe size must be positive")
        
        if self.min_market_cap <= 0:
            raise ValueError("Min market cap must be positive")
        
        if self.correlation_window <= 0:
            raise ValueError("Correlation window must be positive")
        
        if not 0 <= self.min_correlation <= 1:
            raise ValueError("Min correlation must be between 0 and 1")
        
        if not 0 <= self.max_correlation <= 1:
            raise ValueError("Max correlation must be between 0 and 1")
        
        if self.min_correlation >= self.max_correlation:
            raise ValueError("Min correlation must be less than max correlation")
        
        if self.z_score_entry_threshold <= 0:
            raise ValueError("Z-score entry threshold must be positive")
        
        if self.max_pairs <= 0:
            raise ValueError("Max pairs must be positive")
        
        if self.target_leverage <= 0:
            raise ValueError("Target leverage must be positive")


@dataclass
class PortfolioConfig(BaseConfig):
    """Portfolio management configuration"""
    
    # Portfolio identification
    portfolio_name: str = "StatArb_Main"
    base_currency: str = "USD"
    
    # Capital allocation
    initial_capital: Decimal = Decimal("10000000")  # $10M
    max_capital_utilization: float = 0.95  # 95%
    cash_buffer: float = 0.05  # 5% cash buffer
    
    # Position limits
    max_position_size: Decimal = Decimal("1000000")  # $1M per position
    max_sector_exposure: float = 0.30  # 30% per sector
    max_single_stock_weight: float = 0.05  # 5% per stock
    
    # Risk budgeting
    risk_budget_allocation: Dict[str, float] = field(default_factory=lambda: {
        "momentum": 0.30,
        "mean_reversion": 0.40,
        "carry": 0.20,
        "other": 0.10
    })
    
    # Rebalancing
    rebalance_threshold: float = 0.05  # 5% deviation
    max_turnover_per_day: float = 0.20  # 20% daily turnover
    transaction_cost_threshold: float = 0.005  # 0.5% transaction cost
    
    # Performance tracking
    benchmark: str = "SPY"
    performance_fee_rate: float = 0.20  # 20% performance fee
    management_fee_rate: float = 0.02  # 2% management fee
    hurdle_rate: float = 0.05  # 5% hurdle rate
    
    # Margin and leverage
    margin_requirement: float = 0.50  # 50% margin
    max_gross_leverage: float = 2.0   # 2x gross leverage
    max_net_leverage: float = 1.0     # 1x net leverage
    
    def validate(self) -> None:
        """Validate portfolio configuration"""
        if not self.portfolio_name:
            raise ValueError("Portfolio name is required")
        
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if not 0 < self.max_capital_utilization <= 1:
            raise ValueError("Max capital utilization must be between 0 and 1")
        
        if not 0 <= self.cash_buffer <= 1:
            raise ValueError("Cash buffer must be between 0 and 1")
        
        if self.max_capital_utilization + self.cash_buffer > 1:
            raise ValueError("Capital utilization + cash buffer cannot exceed 100%")
        
        if self.max_position_size <= 0:
            raise ValueError("Max position size must be positive")
        
        if not 0 < self.max_sector_exposure <= 1:
            raise ValueError("Max sector exposure must be between 0 and 1")
        
        if self.max_gross_leverage <= 0:
            raise ValueError("Max gross leverage must be positive")
        
        # Validate risk budget allocation
        if abs(sum(self.risk_budget_allocation.values()) - 1.0) > 0.01:
            raise ValueError("Risk budget allocation must sum to 1.0")


@dataclass
class TradingConfig(BaseConfig):
    """Combined trading configuration"""
    
    # Sub-configurations
    market: MarketConfig = field(default_factory=MarketConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    
    # Global trading settings
    trading_enabled: bool = True
    paper_trading: bool = False
    simulation_mode: bool = False
    
    # Data feeds
    primary_data_feed: str = "POLYGON"
    backup_data_feeds: List[str] = field(default_factory=lambda: ["ALPHA_VANTAGE", "IEX"])
    real_time_data: bool = True
    
    # Latency settings
    max_acceptable_latency_ms: int = 100
    data_staleness_threshold_seconds: int = 5
    
    # Emergency controls
    kill_switch_enabled: bool = True
    max_daily_loss: Decimal = Decimal("100000")  # $100K
    max_daily_volume: Decimal = Decimal("10000000")  # $10M
    
    def validate(self) -> None:
        """Validate trading configuration"""
        # Validate sub-configurations
        self.market.validate()
        self.execution.validate()
        self.strategy.validate()
        self.portfolio.validate()
        
        # Validate global settings
        if not self.primary_data_feed:
            raise ValueError("Primary data feed is required")
        
        if self.max_acceptable_latency_ms <= 0:
            raise ValueError("Max acceptable latency must be positive")
        
        if self.data_staleness_threshold_seconds <= 0:
            raise ValueError("Data staleness threshold must be positive")
        
        if self.max_daily_loss <= 0:
            raise ValueError("Max daily loss must be positive")
        
        if self.max_daily_volume <= 0:
            raise ValueError("Max daily volume must be positive")
    
    def get_trading_hours(self) -> Dict[str, time]:
        """Get trading hours configuration"""
        return {
            "market_open": self.market.market_open,
            "market_close": self.market.market_close,
            "pre_market_start": self.market.pre_market_start,
            "after_market_end": self.market.after_market_end
        }
    
    def is_trading_enabled(self) -> bool:
        """Check if trading is enabled"""
        return self.trading_enabled and not self.simulation_mode
    
    def get_execution_settings(self) -> Dict[str, Any]:
        """Get execution configuration as dictionary"""
        return {
            "primary_venue": self.execution.primary_venue,
            "backup_venues": self.execution.backup_venues,
            "order_timeout": self.execution.order_timeout_seconds,
            "max_participation_rate": self.execution.max_participation_rate,
            "enable_price_improvement": self.execution.enable_price_improvement
        }
