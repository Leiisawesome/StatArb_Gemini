"""
Risk Management Configuration for StatArb Trading System

This module provides comprehensive risk management configuration classes
for position limits, portfolio risk, market risk, and operational risk.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from datetime import timedelta
from .base_config import BaseConfig


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
    min_avg_daily_volume: int = 1000000  # $1M daily volume
    max_days_to_liquidate: int = 5  # 5 days maximum
    liquidity_buffer_factor: float = 2.0  # 2x buffer
    
    # Correlation limits
    max_correlation_exposure: float = 0.30  # 30% to correlated positions
    correlation_threshold: float = 0.7  # 70% correlation threshold
    correlation_window_days: int = 60  # 60-day correlation window
    
    # Stop loss and profit taking
    stop_loss_percentage: float = 0.10  # 10% stop loss
    profit_target_percentage: float = 0.20  # 20% profit target
    trailing_stop_percentage: float = 0.05  # 5% trailing stop
    
    def validate(self) -> None:
        """Validate position risk configuration"""
        if self.max_position_value <= 0:
            raise ValueError("Max position value must be positive")
        
        if self.min_position_value <= 0:
            raise ValueError("Min position value must be positive")
        
        if self.min_position_value >= self.max_position_value:
            raise ValueError("Min position value must be less than max position value")
        
        if not 0 < self.max_position_weight <= 1:
            raise ValueError("Max position weight must be between 0 and 1")
        
        if not 0 < self.max_sector_weight <= 1:
            raise ValueError("Max sector weight must be between 0 and 1")
        
        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage >= 1:
            raise ValueError("Stop loss percentage must be between 0 and 1")


@dataclass
class PortfolioRiskConfig(BaseConfig):
    """Portfolio-level risk management configuration"""
    
    # Portfolio limits
    max_gross_exposure: Decimal = Decimal("20000000")  # $20M gross
    max_net_exposure: Decimal = Decimal("10000000")   # $10M net
    max_leverage: float = 2.0  # 2x leverage
    
    # Drawdown controls
    max_daily_drawdown: float = 0.02  # 2% daily drawdown
    max_weekly_drawdown: float = 0.05  # 5% weekly drawdown
    max_monthly_drawdown: float = 0.10  # 10% monthly drawdown
    max_portfolio_drawdown: float = 0.15  # 15% portfolio drawdown
    
    # Volatility controls
    target_volatility: float = 0.15  # 15% annualized
    max_volatility: float = 0.25  # 25% annualized
    volatility_window_days: int = 30  # 30-day volatility window
    volatility_scaling_enabled: bool = True
    
    # Value at Risk (VaR)
    var_confidence_level: float = 0.05  # 5% VaR
    var_horizon_days: int = 1  # 1-day VaR
    var_calculation_method: str = "parametric"  # parametric, historical, monte_carlo
    max_var_limit: Decimal = Decimal("500000")  # $500K VaR limit
    
    # Expected Shortfall (ES)
    es_confidence_level: float = 0.05  # 5% Expected Shortfall
    max_es_limit: Decimal = Decimal("750000")  # $750K ES limit
    
    # Stress testing
    stress_test_scenarios: List[str] = field(default_factory=lambda: [
        "market_crash", "interest_rate_shock", "sector_rotation", "liquidity_crisis"
    ])
    max_stress_loss: Decimal = Decimal("1000000")  # $1M stress loss
    
    # Beta and market exposure
    target_beta: float = 0.0  # Market neutral
    max_beta_deviation: float = 0.2  # ±0.2 beta deviation
    beta_calculation_window: int = 252  # 252-day beta window
    
    def validate(self) -> None:
        """Validate portfolio risk configuration"""
        if self.max_gross_exposure <= 0:
            raise ValueError("Max gross exposure must be positive")
        
        if self.max_net_exposure <= 0:
            raise ValueError("Max net exposure must be positive")
        
        if self.max_leverage <= 0:
            raise ValueError("Max leverage must be positive")
        
        if not 0 < self.max_daily_drawdown <= 1:
            raise ValueError("Max daily drawdown must be between 0 and 1")
        
        if not 0 < self.target_volatility <= 1:
            raise ValueError("Target volatility must be between 0 and 1")
        
        if self.target_volatility >= self.max_volatility:
            raise ValueError("Target volatility must be less than max volatility")
        
        if not 0 < self.var_confidence_level < 1:
            raise ValueError("VaR confidence level must be between 0 and 1")
        
        if self.max_var_limit <= 0:
            raise ValueError("Max VaR limit must be positive")


@dataclass
class MarketRiskConfig(BaseConfig):
    """Market risk management configuration"""
    
    # Market conditions
    enable_market_regime_detection: bool = True
    volatility_regime_threshold: float = 0.25  # 25% volatility threshold
    correlation_regime_threshold: float = 0.8  # 80% correlation threshold
    
    # Market stress indicators
    vix_threshold: float = 30.0  # VIX > 30 indicates high volatility
    credit_spread_threshold: float = 200.0  # 200 bps credit spread
    term_structure_inversion_threshold: float = -0.5  # -50 bps inversion
    
    # Circuit breakers
    market_decline_threshold_1: float = 0.07  # 7% market decline
    market_decline_threshold_2: float = 0.13  # 13% market decline
    market_decline_threshold_3: float = 0.20  # 20% market decline
    
    # Trading halts and restrictions
    halt_on_circuit_breaker: bool = True
    reduce_exposure_on_stress: bool = True
    stress_exposure_reduction: float = 0.50  # 50% exposure reduction
    
    # Liquidity risk
    min_market_liquidity_ratio: float = 0.8  # 80% of normal liquidity
    max_market_impact: float = 0.01  # 1% maximum market impact
    
    # News and event risk
    earnings_blackout_enabled: bool = True
    earnings_blackout_days: int = 2  # 2 days before/after earnings
    fed_announcement_halt: bool = True
    
    def validate(self) -> None:
        """Validate market risk configuration"""
        if self.volatility_regime_threshold <= 0:
            raise ValueError("Volatility regime threshold must be positive")
        
        if not 0 < self.correlation_regime_threshold <= 1:
            raise ValueError("Correlation regime threshold must be between 0 and 1")
        
        if self.vix_threshold <= 0:
            raise ValueError("VIX threshold must be positive")
        
        if not 0 < self.stress_exposure_reduction <= 1:
            raise ValueError("Stress exposure reduction must be between 0 and 1")
        
        if not 0 < self.min_market_liquidity_ratio <= 1:
            raise ValueError("Min market liquidity ratio must be between 0 and 1")


@dataclass
class OperationalRiskConfig(BaseConfig):
    """Operational risk management configuration"""
    
    # System monitoring
    max_system_latency_ms: int = 100  # 100ms max latency
    max_data_staleness_seconds: int = 5  # 5 seconds max staleness
    heartbeat_interval_seconds: int = 30  # 30-second heartbeat
    
    # Error handling
    max_consecutive_errors: int = 5  # 5 consecutive errors
    error_cooldown_minutes: int = 15  # 15-minute cooldown
    auto_failover_enabled: bool = True
    
    # Data quality
    price_change_threshold: float = 0.20  # 20% price change threshold
    volume_anomaly_threshold: float = 5.0  # 5x normal volume
    missing_data_tolerance: float = 0.05  # 5% missing data tolerance
    
    # Trading controls
    kill_switch_enabled: bool = True
    manual_override_required: bool = False
    max_orders_per_second: int = 10  # 10 orders per second
    max_daily_trades: int = 10000  # 10,000 daily trades
    
    # Connectivity
    backup_venues_count: int = 2  # 2 backup venues
    connection_timeout_seconds: int = 30  # 30-second timeout
    max_reconnection_attempts: int = 3  # 3 reconnection attempts
    
    # Compliance and audit
    trade_reporting_enabled: bool = True
    audit_trail_retention_days: int = 2555  # 7 years
    regulatory_reporting_enabled: bool = True
    
    def validate(self) -> None:
        """Validate operational risk configuration"""
        if self.max_system_latency_ms <= 0:
            raise ValueError("Max system latency must be positive")
        
        if self.max_data_staleness_seconds <= 0:
            raise ValueError("Max data staleness must be positive")
        
        if self.max_consecutive_errors <= 0:
            raise ValueError("Max consecutive errors must be positive")
        
        if self.error_cooldown_minutes <= 0:
            raise ValueError("Error cooldown must be positive")
        
        if self.max_orders_per_second <= 0:
            raise ValueError("Max orders per second must be positive")
        
        if self.backup_venues_count < 0:
            raise ValueError("Backup venues count cannot be negative")


@dataclass
class RiskConfig(BaseConfig):
    """Enterprise-level comprehensive risk management configuration
    
    Note: For signal-level risk config, see signal_generation/risk_management.py (SignalRiskConfig)
    For portfolio-level risk config, see unified_config_manager.py (PortfolioRiskConfig)
    """
    
    # Sub-configurations
    position: PositionRiskConfig = field(default_factory=PositionRiskConfig)
    portfolio: PortfolioRiskConfig = field(default_factory=PortfolioRiskConfig)
    market: MarketRiskConfig = field(default_factory=MarketRiskConfig)
    operational: OperationalRiskConfig = field(default_factory=OperationalRiskConfig)
    
    # Global risk settings
    risk_management_enabled: bool = True
    real_time_monitoring: bool = True
    risk_reporting_enabled: bool = True
    
    # Risk officer controls
    risk_officer_override: bool = False
    emergency_liquidation_enabled: bool = True
    position_freeze_enabled: bool = True
    
    # Risk metrics calculation
    risk_calculation_frequency_seconds: int = 60  # 1 minute
    risk_report_frequency_minutes: int = 15  # 15 minutes
    
    # Alerts and notifications
    risk_alert_enabled: bool = True
    risk_alert_channels: List[str] = field(default_factory=lambda: ["email", "slack"])
    critical_alert_threshold: float = 0.8  # 80% of limit
    
    # Model risk
    model_validation_enabled: bool = True
    model_performance_threshold: float = 0.05  # 5% performance degradation
    model_drift_detection: bool = True
    
    def validate(self) -> None:
        """Validate risk configuration"""
        # Validate sub-configurations
        self.position.validate()
        self.portfolio.validate()
        self.market.validate()
        self.operational.validate()
        
        # Validate global settings
        if self.risk_calculation_frequency_seconds <= 0:
            raise ValueError("Risk calculation frequency must be positive")
        
        if self.risk_report_frequency_minutes <= 0:
            raise ValueError("Risk report frequency must be positive")
        
        if not 0 < self.critical_alert_threshold <= 1:
            raise ValueError("Critical alert threshold must be between 0 and 1")
        
        if not 0 < self.model_performance_threshold <= 1:
            raise ValueError("Model performance threshold must be between 0 and 1")
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Get all risk limits as a dictionary"""
        return {
            "position": {
                "max_position_value": self.position.max_position_value,
                "max_position_weight": self.position.max_position_weight,
                "stop_loss_percentage": self.position.stop_loss_percentage
            },
            "portfolio": {
                "max_gross_exposure": self.portfolio.max_gross_exposure,
                "max_net_exposure": self.portfolio.max_net_exposure,
                "max_leverage": self.portfolio.max_leverage,
                "max_daily_drawdown": self.portfolio.max_daily_drawdown,
                "max_var_limit": self.portfolio.max_var_limit
            },
            "market": {
                "vix_threshold": self.market.vix_threshold,
                "volatility_regime_threshold": self.market.volatility_regime_threshold
            },
            "operational": {
                "max_system_latency_ms": self.operational.max_system_latency_ms,
                "max_consecutive_errors": self.operational.max_consecutive_errors
            }
        }
    
    def is_risk_check_required(self, action: str) -> bool:
        """Check if risk validation is required for an action"""
        if not self.risk_management_enabled:
            return False
        
        risk_required_actions = [
            "place_order", "modify_position", "portfolio_rebalance",
            "strategy_change", "leverage_change"
        ]
        
        return action in risk_required_actions
    
    def get_emergency_controls(self) -> Dict[str, bool]:
        """Get emergency control settings"""
        return {
            "kill_switch": self.operational.kill_switch_enabled,
            "emergency_liquidation": self.emergency_liquidation_enabled,
            "position_freeze": self.position_freeze_enabled,
            "auto_failover": self.operational.auto_failover_enabled,
            "risk_officer_override": self.risk_officer_override
        }
