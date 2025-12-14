"""
Unit tests for utils module
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

# Import all utils modules
from core_engine.utils.exceptions import (
    ErrorContext
)
from core_engine.utils.logging import (
    StructuredFormatter, ComponentFilter, LevelFilter, LogConfig,
    StructuredLogger, init_logging, get_logger, log_error_with_context,
    log_performance_metric, log_trade_event, log_component_start,
    log_component_stop, log_operation_start, log_operation_end,
    setup_logger
)

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

