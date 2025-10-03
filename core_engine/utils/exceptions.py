"""
Exception Hierarchy - Core Engine
================================

Comprehensive exception hierarchy for core_engine components.
Provides structured error handling with proper inheritance and context.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ErrorContext:
    """Error context information"""
    component: str
    operation: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    user_message: Optional[str] = None
    system_message: Optional[str] = None
    stack_trace: Optional[str] = None

class CoreEngineError(Exception):
    """Base exception for all core_engine errors"""

    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        super().__init__(message)
        self.context = context or ErrorContext(
            component="unknown",
            operation="unknown"
        )
        self.message = message

    def __str__(self):
        return f"[{self.context.component}:{self.context.operation}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "error_message": self.message,
            "component": self.context.component,
            "operation": self.context.operation,
            "parameters": self.context.parameters,
            "user_message": self.context.user_message,
            "system_message": self.context.system_message,
            "stack_trace": self.context.stack_trace
        }

# Configuration Errors
class ConfigurationError(CoreEngineError):
    """Configuration-related errors"""

class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file not found"""

class ConfigValidationError(ConfigurationError):
    """Configuration validation error"""

class ConfigMergeError(ConfigurationError):
    """Configuration merge error"""

# Data Management Errors
class DataError(CoreEngineError):
    """Data-related errors"""

class DataSourceError(DataError):
    """Data source connection/access error"""

class DataValidationError(DataError):
    """Data validation error"""

class DataNotFoundError(DataError):
    """Requested data not found"""

# Trading Errors
class TradingError(CoreEngineError):
    """Trading-related errors"""

class OrderError(TradingError):
    """Order-related errors"""

class OrderValidationError(OrderError):
    """Order validation error"""

class OrderSubmissionError(OrderError):
    """Order submission error"""

class ExecutionError(TradingError):
    """Trade execution errors"""

class InsufficientFundsError(ExecutionError):
    """Insufficient funds for trade"""

class MarketDataError(TradingError):
    """Market data errors"""

# Risk Management Errors
class RiskError(CoreEngineError):
    """Risk management errors"""

class RiskLimitExceededError(RiskError):
    """Risk limit exceeded"""

class RiskCalculationError(RiskError):
    """Risk calculation error"""

class RiskValidationError(RiskError):
    """Risk validation error"""

# Strategy Errors
class StrategyError(CoreEngineError):
    """Strategy-related errors"""

class StrategyInitializationError(StrategyError):
    """Strategy initialization error"""

class StrategyExecutionError(StrategyError):
    """Strategy execution error"""

class SignalGenerationError(StrategyError):
    """Signal generation error"""

# Analytics Errors
class AnalyticsError(CoreEngineError):
    """Analytics-related errors"""

class PerformanceCalculationError(AnalyticsError):
    """Performance calculation error"""

class AttributionError(AnalyticsError):
    """Attribution calculation error"""

class ReportGenerationError(AnalyticsError):
    """Report generation error"""

# Broker Integration Errors
class BrokerError(CoreEngineError):
    """Broker integration errors"""

class BrokerConnectionError(BrokerError):
    """Broker connection error"""

class BrokerAuthenticationError(BrokerError):
    """Broker authentication error"""

class BrokerAPIError(BrokerError):
    """Broker API error"""

# System Errors
class SystemError(CoreEngineError):
    """System-level errors"""

class ComponentInitializationError(SystemError):
    """Component initialization error"""

class ComponentCommunicationError(SystemError):
    """Component communication error"""

class ResourceExhaustionError(SystemError):
    """Resource exhaustion error"""

# Regime Detection Errors
class RegimeError(CoreEngineError):
    """Regime detection errors"""

class RegimeCalculationError(RegimeError):
    """Regime calculation error"""

class RegimeClassificationError(RegimeError):
    """Regime classification error"""

# Portfolio Management Errors
class PortfolioError(CoreEngineError):
    """Portfolio management errors"""

class PortfolioCalculationError(PortfolioError):
    """Portfolio calculation error"""

class PositionError(PortfolioError):
    """Position-related error"""

# Utility functions for error handling
def create_error_context(component: str, operation: str, **kwargs) -> ErrorContext:
    """Create error context"""
    return ErrorContext(
        component=component,
        operation=operation,
        parameters=kwargs
    )

def handle_error(error: Exception, context: Optional[ErrorContext] = None,
                log_error: bool = True, re_raise: bool = True) -> Optional[CoreEngineError]:
    """
    Handle an exception with proper logging and context

    Args:
        error: The exception to handle
        context: Error context information
        log_error: Whether to log the error
        re_raise: Whether to re-raise as CoreEngineError

    Returns:
        CoreEngineError instance if re_raise is False, None otherwise
    """
    if isinstance(error, CoreEngineError):
        core_error = error
    else:
        # Wrap non-core errors
        message = str(error)
        core_error = CoreEngineError(message, context)

    if log_error:
        logger.error(f"Error in {core_error.context.component}:{core_error.context.operation}",
                    extra=core_error.to_dict())

    if re_raise:
        raise core_error
    else:
        return core_error

def safe_execute(func, *args, context: Optional[ErrorContext] = None, **kwargs):
    """
    Safely execute a function with error handling

    Args:
        func: Function to execute
        context: Error context for error reporting
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result or None if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_error(e, context, re_raise=False)
        return None