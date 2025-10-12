"""
Unit tests for utils module
"""

import pytest

# Import all utils modules
from core_engine.utils.exceptions import (
    ErrorContext, CoreEngineError, ConfigurationError, ConfigFileNotFoundError,
    ConfigValidationError, ConfigMergeError, DataError, DataSourceError,
    DataValidationError, DataNotFoundError, TradingError, OrderError,
    OrderValidationError, OrderSubmissionError, ExecutionError, InsufficientFundsError,
    MarketDataError, RiskError, RiskLimitExceededError, RiskCalculationError,
    RiskValidationError, StrategyError, StrategyInitializationError,
    StrategyExecutionError, SignalGenerationError, AnalyticsError,
    PerformanceCalculationError, AttributionError, ReportGenerationError,
    BrokerError, BrokerConnectionError, BrokerAuthenticationError,
    BrokerAPIError, SystemError, ComponentInitializationError,
    ComponentCommunicationError, ResourceExhaustionError, RegimeError,
    RegimeCalculationError, RegimeClassificationError, PortfolioError,
    PortfolioCalculationError, PositionError, create_error_context,
    handle_error, safe_execute
)


class TestExceptions:
    """Test exception hierarchy and utilities"""

    def test_error_context_creation(self):
        """Test ErrorContext dataclass creation"""
        context = ErrorContext(
            component="test_component",
            operation="test_operation",
            parameters={"key": "value"},
            user_message="User-friendly message",
            system_message="System details",
            stack_trace="stack trace here"
        )

        assert context.component == "test_component"
        assert context.operation == "test_operation"
        assert context.parameters["key"] == "value"
        assert context.user_message == "User-friendly message"
        assert context.system_message == "System details"
        assert context.stack_trace == "stack trace here"

    def test_core_engine_error_creation(self):
        """Test CoreEngineError creation and string representation"""
        context = ErrorContext(component="test", operation="test_op")
        error = CoreEngineError("Test error message", context)

        assert error.message == "Test error message"
        assert error.context == context
        assert str(error) == "[test:test_op] Test error message"

    def test_core_engine_error_to_dict(self):
        """Test CoreEngineError to_dict method"""
        context = ErrorContext(
            component="test",
            operation="test_op",
            parameters={"param": "value"},
            user_message="User message",
            system_message="System message"
        )
        error = CoreEngineError("Test error", context)

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "CoreEngineError"
        assert error_dict["error_message"] == "Test error"
        assert error_dict["component"] == "test"
        assert error_dict["operation"] == "test_op"
        assert error_dict["parameters"]["param"] == "value"
        assert error_dict["user_message"] == "User message"
        assert error_dict["system_message"] == "System message"

    def test_exception_hierarchy(self):
        """Test that all exception classes inherit from CoreEngineError"""
        exceptions = [
            ConfigurationError, ConfigFileNotFoundError, ConfigValidationError,
            ConfigMergeError, DataError, DataSourceError, DataValidationError,
            DataNotFoundError, TradingError, OrderError, OrderValidationError,
            OrderSubmissionError, ExecutionError, InsufficientFundsError,
            MarketDataError, RiskError, RiskLimitExceededError, RiskCalculationError,
            RiskValidationError, StrategyError, StrategyInitializationError,
            StrategyExecutionError, SignalGenerationError, AnalyticsError,
            PerformanceCalculationError, AttributionError, ReportGenerationError,
            BrokerError, BrokerConnectionError, BrokerAuthenticationError,
            BrokerAPIError, SystemError, ComponentInitializationError,
            ComponentCommunicationError, ResourceExhaustionError, RegimeError,
            RegimeCalculationError, RegimeClassificationError, PortfolioError,
            PortfolioCalculationError, PositionError
        ]

        for exception_class in exceptions:
            assert issubclass(exception_class, CoreEngineError)

    def test_create_error_context(self):
        """Test create_error_context utility function"""
        context = create_error_context("component", "operation", param1="value1", param2="value2")

        assert context.component == "component"
        assert context.operation == "operation"
        assert context.parameters["param1"] == "value1"
        assert context.parameters["param2"] == "value2"

    def test_handle_error_with_core_error(self):
        """Test handle_error with CoreEngineError"""
        context = ErrorContext(component="test", operation="test")
        error = CoreEngineError("Test error", context)

        # Should re-raise
        with pytest.raises(CoreEngineError) as exc_info:
            handle_error(error, context, log_error=False, re_raise=True)

        assert exc_info.value == error

    def test_handle_error_with_regular_exception(self):
        """Test handle_error with regular exception"""
        context = ErrorContext(component="test", operation="test")
        error = ValueError("Regular error")

        # Should wrap and re-raise
        with pytest.raises(CoreEngineError) as exc_info:
            handle_error(error, context, log_error=False, re_raise=True)

        assert isinstance(exc_info.value, CoreEngineError)
        assert exc_info.value.context == context

    def test_handle_error_no_re_raise(self):
        """Test handle_error with re_raise=False"""
        context = ErrorContext(component="test", operation="test")
        error = ValueError("Test error")

        result = handle_error(error, context, log_error=False, re_raise=False)

        assert isinstance(result, CoreEngineError)
        assert result.context == context

    def test_safe_execute_success(self):
        """Test safe_execute with successful function"""
        def test_func():
            return "success"

        result = safe_execute(test_func)
        assert result == "success"

    def test_safe_execute_failure(self):
        """Test safe_execute with failing function"""
        def failing_func():
            raise ValueError("Test failure")

        result = safe_execute(failing_func)
        assert result is None


