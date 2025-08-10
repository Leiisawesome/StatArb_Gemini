"""
Strategy Validation Module

Strategy validation and backtesting components.

Author: Pro Quant Desk Trader
"""

# Import validation components
from .strategy_validator import (
    StrategyValidator,
    ValidationConfig,
    ValidationResult,
    Trade,
    PortfolioState
)

from .backtesting_validator import (
    BacktestingValidator
)

from .walk_forward_validator import (
    WalkForwardValidator,
    WalkForwardWindow,
    WalkForwardResult
)

from .parameter_validator import (
    ParameterValidator,
    ParameterSensitivity,
    ParameterValidationResult
)

__all__ = [
    # Base classes
    'StrategyValidator',
    'ValidationConfig',
    'ValidationResult',
    'Trade',
    'PortfolioState',
    
    # Validators
    'BacktestingValidator',
    'WalkForwardValidator',
    'WalkForwardWindow',
    'WalkForwardResult',
    'ParameterValidator',
    'ParameterSensitivity',
    'ParameterValidationResult'
]
