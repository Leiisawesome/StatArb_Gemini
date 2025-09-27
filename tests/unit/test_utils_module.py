"""
Unit tests for utils module
"""

import pytest
import asyncio
import time
import json
import logging
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional, Callable, Awaitable

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
from core_engine.utils.logging import (
    StructuredFormatter, ComponentFilter, LevelFilter, LogConfig,
    StructuredLogger, init_logging, get_logger, log_error_with_context,
    log_performance_metric, log_trade_event, log_component_start,
    log_component_stop, log_operation_start, log_operation_end,
    setup_logger
)
from core_engine.utils.performance import (
    PerformanceMetric, PerformanceSnapshot, OperationProfile,
    PerformanceMonitor, get_performance_monitor, record_performance_metric,
    profile_function, profile_operation, start_performance_monitoring,
    stop_performance_monitoring, get_performance_metrics
)
from core_engine.utils.health import (
    HealthStatus, HealthCheckResult, HealthCheck, DatabaseHealthCheck,
    BrokerHealthCheck, ComponentHealthCheck, MemoryHealthCheck,
    HealthMonitor, get_health_monitor, add_health_check,
    create_database_health_check, create_broker_health_check,
    create_component_health_check, create_memory_health_check
)
from core_engine.utils.dependency_injection import (
    ComponentScope, ComponentRegistration, DependencyInjectionContainer,
    get_container, register_component, resolve_component, reset_container
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


class TestLogging:
    """Test logging utilities"""

    def test_structured_formatter_format(self):
        """Test StructuredFormatter JSON formatting"""
        formatter = StructuredFormatter()

        # Create a mock log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = 1609459200.0  # 2021-01-01 00:00:00 UTC

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test"
        assert parsed["function"] == "<unknown>"
        assert parsed["line"] == 10
        assert "timestamp" in parsed

    def test_structured_formatter_with_exception(self):
        """Test StructuredFormatter with exception info"""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert "exception" in parsed
        assert parsed["level"] == "ERROR"

    def test_component_filter(self):
        """Test ComponentFilter"""
        filter_obj = ComponentFilter(["component1", "component2"])

        # Matching component
        record1 = logging.LogRecord("component1.module", logging.INFO, "", 0, "", (), None)
        assert filter_obj.filter(record1) is True

        # Non-matching component
        record2 = logging.LogRecord("component3.module", logging.INFO, "", 0, "", (), None)
        assert filter_obj.filter(record2) is False

        # No filter components
        filter_empty = ComponentFilter()
        assert filter_empty.filter(record2) is True

    def test_level_filter(self):
        """Test LevelFilter"""
        filter_obj = LevelFilter(min_level=logging.WARNING, max_level=logging.ERROR)

        # Within range
        record1 = logging.LogRecord("", logging.WARNING, "", 0, "", (), None)
        assert filter_obj.filter(record1) is True

        record2 = logging.LogRecord("", logging.ERROR, "", 0, "", (), None)
        assert filter_obj.filter(record2) is True

        # Below minimum
        record3 = logging.LogRecord("", logging.INFO, "", 0, "", (), None)
        assert filter_obj.filter(record3) is False

        # Above maximum
        record4 = logging.LogRecord("", logging.CRITICAL, "", 0, "", (), None)
        assert filter_obj.filter(record4) is False

    def test_log_config_creation(self):
        """Test LogConfig creation"""
        config = LogConfig(
            level="DEBUG",
            format="structured",
            file_path=Path("/tmp/test.log"),
            max_file_size=5 * 1024 * 1024,
            backup_count=3,
            console_output=False,
            component_filters=["test"],
            enable_syslog=True,
            syslog_address=("localhost", 514)
        )

        assert config.level == "DEBUG"
        assert config.format == "structured"
        assert config.file_path == Path("/tmp/test.log")
        assert config.max_file_size == 5 * 1024 * 1024
        assert config.backup_count == 3
        assert config.console_output is False
        assert config.component_filters == ["test"]
        assert config.enable_syslog is True
        assert config.syslog_address == ("localhost", 514)

    @patch('core_engine.utils.logging.logging')
    def test_structured_logger_initialization(self, mock_logging):
        """Test StructuredLogger initialization"""
        config = LogConfig(level="INFO", console_output=True)
        logger = StructuredLogger(config)

        assert logger.config == config
        assert logger._loggers == {}
        # Verify root logger setup was called
        mock_logging.getLogger.assert_called_with('core_engine')

    def test_structured_logger_get_logger(self):
        """Test StructuredLogger get_logger method"""
        config = LogConfig()
        logger = StructuredLogger(config)

        # Get a component logger
        component_logger = logger.get_logger("test_component")

        assert "test_component" in logger._loggers
        assert component_logger == logger._loggers["test_component"]

        # Get the same logger again (should return cached)
        component_logger2 = logger.get_logger("test_component")
        assert component_logger2 == component_logger

    def test_init_logging(self):
        """Test init_logging function"""
        config = LogConfig(level="DEBUG")
        logger = init_logging(config)

        assert isinstance(logger, StructuredLogger)
        assert logger.config == config

    def test_get_logger(self):
        """Test get_logger function"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "core_engine.test"

    def test_log_error_with_context(self):
        """Test log_error_with_context function"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        context = ErrorContext(component="test", operation="test_op")
        error = ValueError("test error")

        # Should not raise (logger not initialized)
        log_error_with_context("test", "test_op", error, context)

    def test_log_performance_metric(self):
        """Test log_performance_metric function"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        # Should not raise (logger not initialized)
        log_performance_metric("test", "metric", 100.0, "ms")

    def test_log_trade_event(self):
        """Test log_trade_event function"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        # Should not raise (logger not initialized)
        log_trade_event("test", "BUY", "AAPL", 100, 150.0)

    def test_convenience_logging_functions(self):
        """Test convenience logging functions"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        # These should not raise even without initialized logger
        log_component_start("test")
        log_component_stop("test")
        log_operation_start("test", "operation")
        log_operation_end("test", "operation", 100.0)

    def test_setup_logger_backward_compatibility(self):
        """Test setup_logger backward compatibility"""
        # Reset global state
        import core_engine.utils.logging as logging_module
        logging_module._logger_instance = None

        logger = setup_logger("test", "INFO")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "core_engine.test"


class TestPerformance:
    """Test performance monitoring utilities"""

    def test_performance_metric_creation(self):
        """Test PerformanceMetric dataclass"""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="test_metric",
            value=100.5,
            unit="ms",
            timestamp=timestamp,
            metadata={"key": "value"},
            component="test_comp",
            operation="test_op"
        )

        assert metric.name == "test_metric"
        assert metric.value == 100.5
        assert metric.unit == "ms"
        assert metric.timestamp == timestamp
        assert metric.metadata["key"] == "value"
        assert metric.component == "test_comp"
        assert metric.operation == "test_op"

    def test_performance_snapshot_creation(self):
        """Test PerformanceSnapshot dataclass"""
        timestamp = datetime.now()
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            cpu_percent=45.2,
            memory_mb=512.5,
            memory_percent=25.1,
            disk_usage_percent=60.0,
            network_connections=150,
            thread_count=8,
            open_files=45,
            metadata={"note": "test"}
        )

        assert snapshot.timestamp == timestamp
        assert snapshot.cpu_percent == 45.2
        assert snapshot.memory_mb == 512.5
        assert snapshot.memory_percent == 25.1
        assert snapshot.disk_usage_percent == 60.0
        assert snapshot.network_connections == 150
        assert snapshot.thread_count == 8
        assert snapshot.open_files == 45
        assert snapshot.metadata["note"] == "test"

    def test_operation_profile_creation(self):
        """Test OperationProfile dataclass"""
        timestamp = datetime.now()
        profile = OperationProfile(
            operation_name="test_operation",
            call_count=10,
            total_time=5.5,
            avg_time=0.55,
            min_time=0.3,
            max_time=1.2,
            last_called=timestamp,
            error_count=1
        )

        assert profile.operation_name == "test_operation"
        assert profile.call_count == 10
        assert profile.total_time == 5.5
        assert profile.avg_time == 0.55
        assert profile.min_time == 0.3
        assert profile.max_time == 1.2
        assert profile.last_called == timestamp
        assert profile.error_count == 1

    @patch('core_engine.utils.performance.psutil')
    @patch('core_engine.utils.performance.threading.active_count', return_value=12)
    def test_performance_monitor_take_snapshot(self, mock_threading_active_count, mock_psutil):
        """Test PerformanceMonitor take_snapshot"""
        # Mock psutil
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 256 * 1024 * 1024  # 256MB
        mock_process.open_files.return_value = [Mock()] * 10

        mock_psutil.cpu_percent.return_value = 30.5
        mock_psutil.virtual_memory.return_value = Mock(
            used=512 * 1024 * 1024,  # 512MB
            percent=25.6
        )
        mock_psutil.disk_usage.return_value = Mock(percent=45.2)
        mock_psutil.net_connections.return_value = [Mock()] * 20
        mock_psutil.Process.return_value = mock_process

        monitor = PerformanceMonitor()
        snapshot = monitor.take_snapshot()

        assert snapshot.cpu_percent == 30.5
        assert snapshot.memory_mb == 512.0  # 512MB
        assert snapshot.memory_percent == 25.6
        assert snapshot.disk_usage_percent == 45.2
        assert snapshot.network_connections == 20
        assert snapshot.thread_count == 12
        assert snapshot.open_files == 10

    def test_performance_monitor_record_metric(self):
        """Test PerformanceMonitor record_metric"""
        monitor = PerformanceMonitor()

        monitor.record_metric("test_metric", 42.0, "units", "test_comp", "test_op", {"meta": "data"})

        assert len(monitor.metrics) == 1
        metric = monitor.metrics[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.unit == "units"
        assert metric.component == "test_comp"
        assert metric.operation == "test_op"
        assert metric.metadata["meta"] == "data"

    @pytest.mark.asyncio
    async def test_performance_monitor_alerts(self):
        """Test PerformanceMonitor alert system"""
        monitor = PerformanceMonitor()

        # Set alert threshold
        monitor.set_alert_threshold("test_metric", 50.0)

        # Mock alert callback
        alert_calls = []
        async def mock_callback(metric):
            alert_calls.append(metric)

        monitor.add_alert_callback(mock_callback)

        # Record metric that should trigger alert
        monitor.record_metric("test_metric", 75.0)

        # Wait a bit for async alert to be processed
        await asyncio.sleep(0.01)

        assert len(alert_calls) == 1
        assert alert_calls[0].name == "test_metric"
        assert alert_calls[0].value == 75.0

    @patch('core_engine.utils.performance.psutil')
    def test_performance_monitor_profile_operation(self, mock_psutil):
        """Test PerformanceMonitor profile_operation context manager"""
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB initially
        mock_psutil.Process.return_value = mock_process

        monitor = PerformanceMonitor()

        with monitor.profile_operation("test_operation", "test_component"):
            time.sleep(0.01)  # Small delay
            mock_process.memory_info.return_value.rss = 105 * 1024 * 1024  # 105MB after

        # Check that metrics were recorded
        duration_metrics = [m for m in monitor.metrics if "duration" in m.name]
        memory_metrics = [m for m in monitor.metrics if "memory_delta" in m.name]

        assert len(duration_metrics) == 1
        assert len(memory_metrics) == 1

        assert duration_metrics[0].component == "test_component"
        assert duration_metrics[0].operation == "test_operation"
        assert duration_metrics[0].unit == "ms"

        assert memory_metrics[0].component == "test_component"
        assert memory_metrics[0].operation == "test_operation"
        assert memory_metrics[0].unit == "MB"

    def test_performance_monitor_get_operation_profile(self):
        """Test PerformanceMonitor operation profiling"""
        monitor = PerformanceMonitor()

        # Update profile manually
        monitor._update_operation_profile("test_op", 0.1)
        monitor._update_operation_profile("test_op", 0.2)
        monitor._update_operation_profile("test_op", 0.3)

        profile = monitor.get_operation_profile("test_op")

        assert profile.operation_name == "test_op"
        assert profile.call_count == 3
        assert abs(profile.total_time - 0.6) < 0.001  # Use approximate comparison for floating point
        assert abs(profile.avg_time - 0.2) < 0.001
        assert profile.min_time == 0.1
        assert profile.max_time == 0.3

    def test_performance_monitor_memory_tracing(self):
        """Test PerformanceMonitor memory tracing"""
        monitor = PerformanceMonitor()

        # Start memory tracing
        monitor.start_memory_tracing()
        assert monitor.memory_tracing is True

        # Get memory snapshot
        snapshot = monitor.get_memory_snapshot()
        assert "total_blocks" in snapshot
        assert "total_size_mb" in snapshot
        assert "top_allocations" in snapshot

        # Stop memory tracing
        monitor.stop_memory_tracing()
        assert monitor.memory_tracing is False

    def test_performance_monitor_cpu_profiling(self):
        """Test PerformanceMonitor CPU profiling"""
        monitor = PerformanceMonitor()

        # Start CPU profiling
        monitor.start_cpu_profiling()
        assert monitor.cpu_profiling is True

        # Simulate some work
        for i in range(1000):
            _ = i * i

        # Stop CPU profiling
        profile_output = monitor.stop_cpu_profiling()
        assert profile_output is not None
        assert "function calls" in profile_output.lower() or len(profile_output) > 0
        assert monitor.cpu_profiling is False

    def test_global_performance_functions(self):
        """Test global performance monitoring functions"""
        # Test record_performance_metric
        record_performance_metric("global_test", 123.0, "units")

        # Test get_performance_metrics
        metrics = get_performance_metrics()
        assert "current_snapshot" in metrics
        assert "operation_profiles" in metrics
        assert "alert_thresholds" in metrics

    def test_profile_function_decorator(self):
        """Test profile_function decorator"""
        monitor = PerformanceMonitor()

        @monitor.profile_function("test_component")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()
        assert result == "result"

        # Check that metrics were recorded
        duration_metrics = [m for m in monitor.metrics if "duration" in m.name]
        assert len(duration_metrics) >= 1

    def test_profile_operation_context_manager(self):
        """Test profile_operation context manager"""
        with profile_operation("global_test_op", "global_test_comp"):
            time.sleep(0.01)

        # Check that global monitor recorded the operation
        monitor = get_performance_monitor()
        profile = monitor.get_operation_profile("global_test_op")
        assert profile is not None
        assert profile.call_count >= 1


class TestHealth:
    """Test health monitoring utilities"""

    def test_health_status_enum(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation and properties"""
        timestamp = datetime.now()
        result = HealthCheckResult(
            component="test_component",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"metric": "value"},
            timestamp=timestamp,
            response_time_ms=150.5,
            last_success=timestamp,
            consecutive_failures=0
        )

        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details["metric"] == "value"
        assert result.timestamp == timestamp
        assert result.response_time_ms == 150.5
        assert result.last_success == timestamp
        assert result.consecutive_failures == 0
        assert result.is_healthy is True
        assert result.is_degraded is False

    def test_health_check_result_properties(self):
        """Test HealthCheckResult computed properties"""
        healthy_result = HealthCheckResult("comp", HealthStatus.HEALTHY, "ok")
        degraded_result = HealthCheckResult("comp", HealthStatus.DEGRADED, "slow")
        unhealthy_result = HealthCheckResult("comp", HealthStatus.UNHEALTHY, "error")
        unknown_result = HealthCheckResult("comp", HealthStatus.UNKNOWN, "unknown")

        assert healthy_result.is_healthy is True
        assert healthy_result.is_degraded is False

        assert degraded_result.is_healthy is False
        assert degraded_result.is_degraded is True

        assert unhealthy_result.is_healthy is False
        assert unhealthy_result.is_degraded is False

        assert unknown_result.is_healthy is False
        assert unknown_result.is_degraded is False

    @pytest.mark.asyncio
    async def test_database_health_check_success(self):
        """Test DatabaseHealthCheck with successful connection"""
        async def mock_check():
            return True

        check = DatabaseHealthCheck("test_db", mock_check)
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message
        assert result.details["connection_status"] == "connected"
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_database_health_check_failure(self):
        """Test DatabaseHealthCheck with failed connection"""
        async def mock_check():
            return False

        check = DatabaseHealthCheck("test_db", mock_check)
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message
        assert result.details["connection_status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_database_health_check_timeout(self):
        """Test DatabaseHealthCheck with timeout"""
        async def slow_check():
            await asyncio.sleep(2)  # Longer than timeout
            return True

        check = DatabaseHealthCheck("test_db", slow_check, timeout_seconds=1.0)  # Set timeout to 1 second
        result = await check.check()

        assert result.component == "test_db"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message

    @pytest.mark.asyncio
    async def test_broker_health_check(self):
        """Test BrokerHealthCheck"""
        async def mock_check():
            return True

        check = BrokerHealthCheck("test_broker", mock_check)
        result = await check.check()

        assert result.component == "test_broker"
        assert result.status == HealthStatus.HEALTHY
        assert "successful" in result.message

    @pytest.mark.asyncio
    async def test_component_health_check(self):
        """Test ComponentHealthCheck"""
        async def mock_check():
            return {
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 3600
            }

        check = ComponentHealthCheck("test_comp", mock_check)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.HEALTHY
        assert result.details["version"] == "1.0.0"
        assert result.details["uptime"] == 3600

    @pytest.mark.asyncio
    async def test_component_health_check_degraded(self):
        """Test ComponentHealthCheck with degraded status"""
        async def mock_check():
            return {
                "status": "degraded",
                "cpu_usage": 95.0
            }

        check = ComponentHealthCheck("test_comp", mock_check)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.DEGRADED
        assert "degraded" in result.message

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_healthy(self, mock_process_class):
        """Test MemoryHealthCheck healthy state"""
        # Mock process memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 500 * 1024 * 1024  # 500MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.HEALTHY
        assert "normal" in result.message
        assert result.details["memory_mb"] == 500.0
        assert result.details["max_memory_mb"] == 1000.0

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_degraded(self, mock_process_class):
        """Test MemoryHealthCheck degraded state"""
        # Mock high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 900 * 1024 * 1024  # 900MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.DEGRADED
        assert "high" in result.message

    @patch('psutil.Process')
    @pytest.mark.asyncio
    async def test_memory_health_check_unhealthy(self, mock_process_class):
        """Test MemoryHealthCheck unhealthy state"""
        # Mock excessive memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1200 * 1024 * 1024  # 1200MB
        mock_process_class.return_value = mock_process

        check = MemoryHealthCheck("test_comp", max_memory_mb=1000.0)
        result = await check.check()

        assert result.component == "test_comp"
        assert result.status == HealthStatus.UNHEALTHY
        assert "too high" in result.message

    def test_health_monitor_initialization(self):
        """Test HealthMonitor initialization"""
        monitor = HealthMonitor()

        assert monitor.checks == {}
        assert monitor.results == {}
        assert monitor.alert_callbacks == []
        assert monitor.is_monitoring is False
        assert monitor.check_interval == 30.0

    def test_health_monitor_add_check(self):
        """Test HealthMonitor add_check"""
        monitor = HealthMonitor()

        # Create a mock health check
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"

        monitor.add_check(check)

        assert "test_check" in monitor.checks
        assert monitor.checks["test_check"] == check

    def test_health_monitor_remove_check(self):
        """Test HealthMonitor remove_check"""
        monitor = HealthMonitor()

        # Add a check
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"
        monitor.add_check(check)

        # Remove it
        monitor.remove_check("test_check")

        assert "test_check" not in monitor.checks

    @pytest.mark.asyncio
    async def test_health_monitor_run_check(self):
        """Test HealthMonitor run_check"""
        monitor = HealthMonitor()

        # Create a mock check that returns a result
        check = Mock(spec=HealthCheck)
        check.name = "test_check"
        check.component = "test_comp"

        result = HealthCheckResult("test_comp", HealthStatus.HEALTHY, "OK")
        check.check = AsyncMock(return_value=result)

        monitor.add_check(check)

        returned_result = await monitor.run_check("test_check")

        assert returned_result == result
        assert "test_check" in monitor.results
        assert monitor.results["test_check"] == result

    @pytest.mark.asyncio
    async def test_health_monitor_run_all_checks(self):
        """Test HealthMonitor run_all_checks"""
        monitor = HealthMonitor()

        # Add multiple checks
        check1 = Mock(spec=HealthCheck)
        check1.name = "check1"
        check1.component = "comp1"
        check1.check = AsyncMock(return_value=HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK"))

        check2 = Mock(spec=HealthCheck)
        check2.name = "check2"
        check2.component = "comp2"
        check2.check = AsyncMock(return_value=HealthCheckResult("comp2", HealthStatus.DEGRADED, "Slow"))

        monitor.add_check(check1)
        monitor.add_check(check2)

        results = await monitor.run_all_checks()

        assert len(results) == 2
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.DEGRADED

    def test_health_monitor_get_status(self):
        """Test HealthMonitor get_status"""
        monitor = HealthMonitor()

        # No results
        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.UNKNOWN.value
        assert status["total_checks"] == 0

        # Add some results
        monitor.results = {
            "check1": HealthCheckResult("comp1", HealthStatus.HEALTHY, "OK"),
            "check2": HealthCheckResult("comp2", HealthStatus.DEGRADED, "Slow"),
            "check3": HealthCheckResult("comp3", HealthStatus.UNHEALTHY, "Error")
        }

        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.UNHEALTHY.value
        assert status["total_checks"] == 3
        assert status["healthy_checks"] == 1
        assert status["degraded_checks"] == 1
        assert status["unhealthy_checks"] == 1

    def test_health_monitor_get_component_status(self):
        """Test HealthMonitor get_component_status"""
        monitor = HealthMonitor()

        # Add results for different components
        monitor.results = {
            "db_check": HealthCheckResult("database", HealthStatus.HEALTHY, "OK"),
            "api_check": HealthCheckResult("api", HealthStatus.DEGRADED, "Slow"),
            "cache_check": HealthCheckResult("cache", HealthStatus.UNHEALTHY, "Down")
        }

        # Get status for specific component
        db_status = monitor.get_component_status("database")
        assert db_status["status"] == HealthStatus.HEALTHY.value
        assert len(db_status["checks"]) == 1

        # Get status for component with mixed results
        api_status = monitor.get_component_status("api")
        assert api_status["status"] == HealthStatus.DEGRADED.value

        # Get status for unknown component
        unknown_status = monitor.get_component_status("unknown")
        assert unknown_status["status"] == HealthStatus.UNKNOWN.value

    def test_global_health_functions(self):
        """Test global health monitoring functions"""
        # Test get_health_monitor
        monitor = get_health_monitor()
        assert isinstance(monitor, HealthMonitor)

        # Test create functions
        async def mock_db_check():
            return True

        async def mock_broker_check():
            return True

        async def mock_comp_check():
            return {"status": "healthy"}

        db_check = create_database_health_check("test", mock_db_check)
        broker_check = create_broker_health_check("test", mock_broker_check)
        comp_check = create_component_health_check("test", mock_comp_check)
        mem_check = create_memory_health_check("test", 500.0)

        assert isinstance(db_check, DatabaseHealthCheck)
        assert isinstance(broker_check, BrokerHealthCheck)
        assert isinstance(comp_check, ComponentHealthCheck)
        assert isinstance(mem_check, MemoryHealthCheck)

        # Test add_health_check
        add_health_check(db_check)
        assert "database" in get_health_monitor().checks


class TestDependencyInjection:
    """Test dependency injection utilities"""

    def test_component_scope_enum(self):
        """Test ComponentScope enum values"""
        assert ComponentScope.SINGLETON.value == "singleton"
        assert ComponentScope.TRANSIENT.value == "transient"
        assert ComponentScope.SCOPED.value == "scoped"

    def test_component_registration_creation(self):
        """Test ComponentRegistration creation"""
        registration = ComponentRegistration(
            interface=str,
            implementation=str,
            scope=ComponentScope.SINGLETON,
            factory=lambda: "test",
            instance="pre_created"
        )

        assert registration.interface == str
        assert registration.implementation == str
        assert registration.scope == ComponentScope.SINGLETON
        assert registration.factory() == "test"
        assert registration.instance == "pre_created"

    def test_dependency_injection_container_register(self):
        """Test DependencyInjectionContainer register"""
        container = DependencyInjectionContainer()

        # Register a component
        container.register(str, str, ComponentScope.SINGLETON)

        assert str in container._registrations
        reg = container._registrations[str]
        assert reg.interface == str
        assert reg.implementation == str
        assert reg.scope == ComponentScope.SINGLETON

    def test_dependency_injection_container_register_instance(self):
        """Test DependencyInjectionContainer register_instance"""
        container = DependencyInjectionContainer()

        # Register an instance
        container.register_instance(str, "test_instance")

        assert str in container._registrations
        reg = container._registrations[str]
        assert reg.interface == str
        assert reg.implementation == type("test_instance")
        assert reg.scope == ComponentScope.SINGLETON
        assert reg.instance == "test_instance"

    def test_dependency_injection_container_resolve_singleton(self):
        """Test DependencyInjectionContainer resolve singleton"""
        container = DependencyInjectionContainer()

        # Register a simple class
        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.SINGLETON)

        # Resolve multiple times - should get same instance
        instance1 = container.resolve(TestClass)
        instance2 = container.resolve(TestClass)

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is instance2  # Same instance
        assert instance1.value == "test"

    def test_dependency_injection_container_resolve_transient(self):
        """Test DependencyInjectionContainer resolve transient"""
        container = DependencyInjectionContainer()

        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.TRANSIENT)

        # Resolve multiple times - should get different instances
        instance1 = container.resolve(TestClass)
        instance2 = container.resolve(TestClass)

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is not instance2  # Different instances

    def test_dependency_injection_container_resolve_scoped(self):
        """Test DependencyInjectionContainer resolve scoped"""
        container = DependencyInjectionContainer()

        class TestClass:
            def __init__(self):
                self.value = "test"

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Resolve in same scope - should get same instance
        instance1 = container.resolve(TestClass, "scope1")
        instance2 = container.resolve(TestClass, "scope1")

        assert isinstance(instance1, TestClass)
        assert isinstance(instance2, TestClass)
        assert instance1 is instance2  # Same instance in same scope

        # Resolve in different scope - should get different instance
        instance3 = container.resolve(TestClass, "scope2")

        assert isinstance(instance3, TestClass)
        assert instance3 is not instance1  # Different instance in different scope

    def test_dependency_injection_container_resolve_with_dependencies(self):
        """Test DependencyInjectionContainer resolve with dependencies"""
        container = DependencyInjectionContainer()

        class Dependency:
            def __init__(self):
                self.name = "dependency"

        class Dependent:
            def __init__(self, dependency: Dependency):
                self.dependency = dependency

        # Register dependency first
        container.register(Dependency, Dependency, ComponentScope.SINGLETON)
        # Register dependent class
        container.register(Dependent, Dependent, ComponentScope.SINGLETON)

        # Resolve dependent - should inject dependency
        instance = container.resolve(Dependent)

        assert isinstance(instance, Dependent)
        assert isinstance(instance.dependency, Dependency)
        assert instance.dependency.name == "dependency"

    def test_dependency_injection_container_resolve_unregistered(self):
        """Test DependencyInjectionContainer resolve unregistered component"""
        container = DependencyInjectionContainer()

        with pytest.raises(ValueError, match="Component not registered"):
            container.resolve(str)

    def test_dependency_injection_container_clear_scope(self):
        """Test DependencyInjectionContainer clear_scope"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Create scoped instance
        instance1 = container.resolve(TestClass, "test_scope")
        assert "test_scope" in container._scoped_instances
        assert TestClass in container._scoped_instances["test_scope"]

        # Clear scope
        container.clear_scope("test_scope")

        assert "test_scope" not in container._scoped_instances

    def test_dependency_injection_container_clear_all_scopes(self):
        """Test DependencyInjectionContainer clear_all_scopes"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SCOPED)

        # Create instances in multiple scopes
        container.resolve(TestClass, "scope1")
        container.resolve(TestClass, "scope2")

        assert len(container._scoped_instances) == 2

        # Clear all scopes
        container.clear_all_scopes()

        assert len(container._scoped_instances) == 0

    def test_dependency_injection_container_get_registered_components(self):
        """Test DependencyInjectionContainer get_registered_components"""
        container = DependencyInjectionContainer()

        class TestClass:
            pass

        container.register(TestClass, TestClass, ComponentScope.SINGLETON)

        registered = container.get_registered_components()

        assert TestClass in registered
        assert isinstance(registered[TestClass], ComponentRegistration)

    def test_global_dependency_injection_functions(self):
        """Test global dependency injection functions"""
        # Reset container
        reset_container()

        # Test register_component
        class TestClass:
            pass

        register_component(TestClass, TestClass, ComponentScope.SINGLETON)

        # Test resolve_component
        instance = resolve_component(TestClass)

        assert isinstance(instance, TestClass)

        # Test get_container
        container = get_container()
        assert isinstance(container, DependencyInjectionContainer)
