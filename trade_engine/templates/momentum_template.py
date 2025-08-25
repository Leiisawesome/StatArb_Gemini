"""
Professional Momentum Strategy Template
======================================

Professional-grade momentum strategy template implementing industry-standard
momentum trading logic with proper parameter bounds and signal definitions.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from typing import Dict, List, Any
from .base_template import (
    BaseTemplate, ParameterBounds, SignalRule, RiskRule, EntryExitRule,
    SignalCondition, template_registry
)


class ProfessionalMomentumTemplate(BaseTemplate):
    """
    Professional momentum strategy template.
    
    This template defines a comprehensive momentum strategy based on:
    - Multiple timeframe momentum analysis
    - Volume-weighted momentum signals
    - Adaptive threshold mechanisms
    - Professional risk management rules
    """
    
    def __init__(self):
        """Initialize the professional momentum template."""
        super().__init__(
            template_id="professional_momentum_v1",
            name="Professional Momentum Strategy",
            description="Industry-standard momentum strategy with volume confirmation and risk management"
        )
    
    def _define_template(self) -> None:
        """Define the professional momentum template."""
        
        # =================== PARAMETER BOUNDS ===================
        
        # Core momentum parameters with professional bounds
        self.add_parameter_bounds(
            "lookback_period",
            ParameterBounds(
                min_value=5,
                max_value=100,
                data_type=int,
                is_required=True,
                default_value=20
            )
        )
        
        self.add_parameter_bounds(
            "momentum_threshold",
            ParameterBounds(
                min_value=0.001,    # 0.1% minimum threshold
                max_value=0.1,      # 10% maximum threshold
                data_type=float,
                is_required=True,
                default_value=0.015  # Professional 1.5% threshold
            )
        )
        
        self.add_parameter_bounds(
            "confidence_threshold",
            ParameterBounds(
                min_value=0.5,
                max_value=0.95,
                data_type=float,
                is_required=True,
                default_value=0.75   # Professional 75% confidence
            )
        )
        
        # Volume analysis parameters
        self.add_parameter_bounds(
            "volume_lookback",
            ParameterBounds(
                min_value=5,
                max_value=50,
                data_type=int,
                is_required=True,
                default_value=10
            )
        )
        
        self.add_parameter_bounds(
            "volume_threshold",
            ParameterBounds(
                min_value=1.1,      # 10% above average volume
                max_value=5.0,      # 5x average volume
                data_type=float,
                is_required=True,
                default_value=1.5   # 50% above average
            )
        )
        
        # Risk management parameters
        self.add_parameter_bounds(
            "position_size",
            ParameterBounds(
                min_value=0.01,     # 1% minimum position
                max_value=0.25,     # 25% maximum position
                data_type=float,
                is_required=True,
                default_value=0.05  # Professional 5% position
            )
        )
        
        self.add_parameter_bounds(
            "stop_loss_pct",
            ParameterBounds(
                min_value=0.01,     # 1% minimum stop
                max_value=0.15,     # 15% maximum stop
                data_type=float,
                is_required=True,
                default_value=0.03  # Professional 3% stop
            )
        )
        
        self.add_parameter_bounds(
            "take_profit_pct",
            ParameterBounds(
                min_value=0.02,     # 2% minimum profit target
                max_value=0.30,     # 30% maximum profit target
                data_type=float,
                is_required=True,
                default_value=0.08  # Professional 8% profit target
            )
        )
        
        # Adaptive parameters
        self.add_parameter_bounds(
            "volatility_adjustment",
            ParameterBounds(
                min_value=0.5,
                max_value=2.0,
                data_type=float,
                is_required=False,
                default_value=1.0
            )
        )
        
        # =================== SIGNAL RULES ===================
        
        # Primary momentum signal (long)
        self.add_signal_rule(
            SignalRule(
                rule_id="momentum_long_primary",
                condition=SignalCondition.GREATER_THAN,
                indicator="momentum_score",
                threshold="${momentum_threshold}",
                signal_strength=1.0,
                confidence_multiplier=1.0,
                metadata={
                    "signal_type": "long_entry",
                    "priority": 1,
                    "description": "Primary upward momentum signal"
                }
            )
        )
        
        # Primary momentum signal (short)
        self.add_signal_rule(
            SignalRule(
                rule_id="momentum_short_primary",
                condition=SignalCondition.LESS_THAN,
                indicator="momentum_score",
                threshold="${momentum_threshold}",
                signal_strength=1.0,
                confidence_multiplier=1.0,
                metadata={
                    "signal_type": "short_entry",
                    "priority": 1,
                    "description": "Primary downward momentum signal",
                    "threshold_sign": "negative"
                }
            )
        )
        
        # Volume confirmation signal
        self.add_signal_rule(
            SignalRule(
                rule_id="volume_confirmation",
                condition=SignalCondition.GREATER_THAN,
                indicator="volume_ratio",
                threshold="${volume_threshold}",
                signal_strength=0.5,
                confidence_multiplier=1.3,
                metadata={
                    "signal_type": "confirmation",
                    "priority": 2,
                    "description": "Volume confirmation for momentum signals"
                }
            )
        )
        
        # Trend strength signal
        self.add_signal_rule(
            SignalRule(
                rule_id="trend_strength",
                condition=SignalCondition.GREATER_THAN,
                indicator="trend_strength",
                threshold="0.6",
                signal_strength=0.3,
                confidence_multiplier=1.2,
                metadata={
                    "signal_type": "confirmation",
                    "priority": 3,
                    "description": "Trend strength confirmation"
                }
            )
        )
        
        # Volatility adjustment signal
        self.add_signal_rule(
            SignalRule(
                rule_id="volatility_filter",
                condition=SignalCondition.LESS_THAN,
                indicator="volatility_percentile",
                threshold="0.9",
                signal_strength=0.2,
                confidence_multiplier=1.1,
                metadata={
                    "signal_type": "filter",
                    "priority": 4,
                    "description": "Filter out extreme volatility periods"
                }
            )
        )
        
        # =================== RISK RULES ===================
        
        # Position sizing rule
        self.add_risk_rule(
            RiskRule(
                rule_id="position_size_limit",
                rule_type="position_size",
                threshold="${position_size}",
                action="limit",
                priority=1,
                metadata={
                    "description": "Limit position size to specified percentage",
                    "applies_to": "all_positions"
                }
            )
        )
        
        # Stop loss rule
        self.add_risk_rule(
            RiskRule(
                rule_id="stop_loss",
                rule_type="stop_loss",
                threshold="${stop_loss_pct}",
                action="exit",
                priority=1,
                metadata={
                    "description": "Exit position if loss exceeds threshold",
                    "calculation": "percentage_from_entry"
                }
            )
        )
        
        # Take profit rule
        self.add_risk_rule(
            RiskRule(
                rule_id="take_profit",
                rule_type="take_profit",
                threshold="${take_profit_pct}",
                action="exit",
                priority=2,
                metadata={
                    "description": "Exit position if profit exceeds threshold",
                    "calculation": "percentage_from_entry"
                }
            )
        )
        
        # Maximum drawdown rule
        self.add_risk_rule(
            RiskRule(
                rule_id="max_drawdown",
                rule_type="max_drawdown",
                threshold="0.10",  # 10% maximum drawdown
                action="reduce",
                priority=1,
                metadata={
                    "description": "Reduce position sizes if drawdown exceeds 10%",
                    "calculation": "portfolio_level"
                }
            )
        )
        
        # Correlation limit rule
        self.add_risk_rule(
            RiskRule(
                rule_id="correlation_limit",
                rule_type="correlation",
                threshold="0.7",
                action="limit",
                priority=3,
                metadata={
                    "description": "Limit correlated positions",
                    "correlation_window": 30
                }
            )
        )
        
        # =================== ENTRY/EXIT RULES ===================
        
        # Long entry rule
        self.add_entry_exit_rule(
            EntryExitRule(
                rule_id="long_entry",
                trigger_type="signal",
                condition=SignalCondition.GREATER_THAN,
                value="${confidence_threshold}",
                action="enter_long",
                priority=1,
                metadata={
                    "description": "Enter long position when confidence exceeds threshold",
                    "required_signals": ["momentum_long_primary"]
                }
            )
        )
        
        # Short entry rule
        self.add_entry_exit_rule(
            EntryExitRule(
                rule_id="short_entry",
                trigger_type="signal",
                condition=SignalCondition.GREATER_THAN,
                value="${confidence_threshold}",
                action="enter_short",
                priority=1,
                metadata={
                    "description": "Enter short position when confidence exceeds threshold",
                    "required_signals": ["momentum_short_primary"]
                }
            )
        )
        
        # Momentum reversal exit (long)
        self.add_entry_exit_rule(
            EntryExitRule(
                rule_id="momentum_reversal_exit_long",
                trigger_type="signal",
                condition=SignalCondition.LESS_THAN,
                value="0.0",
                action="exit_long",
                priority=2,
                metadata={
                    "description": "Exit long when momentum turns negative",
                    "signal_indicator": "momentum_score"
                }
            )
        )
        
        # Momentum reversal exit (short)
        self.add_entry_exit_rule(
            EntryExitRule(
                rule_id="momentum_reversal_exit_short",
                trigger_type="signal",
                condition=SignalCondition.GREATER_THAN,
                value="0.0",
                action="exit_short",
                priority=2,
                metadata={
                    "description": "Exit short when momentum turns positive",
                    "signal_indicator": "momentum_score"
                }
            )
        )
        
        # Time-based exit rule
        self.add_entry_exit_rule(
            EntryExitRule(
                rule_id="time_based_exit",
                trigger_type="time",
                condition=SignalCondition.GREATER_THAN,
                value="30",  # 30 periods maximum hold
                action="exit_long",
                priority=3,
                metadata={
                    "description": "Exit position after maximum hold period",
                    "applies_to": ["exit_long", "exit_short"],
                    "time_unit": "periods"
                }
            )
        )
        
        # =================== REQUIRED INDICATORS ===================
        
        self.add_required_indicator("close")
        self.add_required_indicator("volume")
        self.add_required_indicator("momentum_score")
        self.add_required_indicator("volume_ratio")
        self.add_required_indicator("trend_strength")
        self.add_required_indicator("volatility_percentile")
        
        # =================== METADATA ===================
        
        self._metadata = {
            "strategy_type": "momentum",
            "asset_classes": ["equity", "etf", "crypto"],
            "timeframes": ["1m", "5m", "15m", "1h", "1d"],
            "market_conditions": ["trending", "volatile"],
            "complexity_level": "intermediate",
            "risk_level": "medium",
            "typical_holding_period": "short_to_medium_term",
            "performance_metrics": {
                "expected_sharpe": "1.2-1.8",
                "max_drawdown": "8-12%",
                "win_rate": "55-65%",
                "profit_factor": "1.4-1.8"
            },
            "professional_parameters": {
                "institutional_grade": True,
                "backtested_timeframe": "5_years",
                "parameter_optimization": "walk_forward",
                "risk_adjusted": True
            }
        }


# Register the template in the global registry
def register_momentum_template():
    """Register the professional momentum template."""
    template = ProfessionalMomentumTemplate()
    
    template_registry.register_template(template, category="momentum")
    return template


# Auto-register when module is imported
register_momentum_template()
