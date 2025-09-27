"""
Structured Logging - Core Engine
================================

Advanced logging system with structured logging, log levels, and multiple handlers.
Supports JSON formatting, log rotation, and component-specific logging.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
import threading

from .exceptions import ErrorContext

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for logs"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName or "<unknown>",
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": threading.current_thread().name
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present and requested
        if self.include_extra and hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ('name', 'msg', 'args', 'levelname', 'levelno',
                             'pathname', 'filename', 'module', 'exc_info',
                             'exc_text', 'stack_info', 'lineno', 'funcName',
                             'created', 'msecs', 'relativeCreated', 'thread',
                             'threadName', 'processName', 'process', 'message'):
                    # Convert non-serializable objects to strings
                    try:
                        json.dumps(value)
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)

        return json.dumps(log_data, default=str, ensure_ascii=False)

class ComponentFilter(logging.Filter):
    """Filter logs by component"""

    def __init__(self, allowed_components: Optional[list] = None):
        super().__init__()
        self.allowed_components = allowed_components or []

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records by component"""
        if not self.allowed_components:
            return True

        # Check if logger name starts with any allowed component
        return any(record.name.startswith(comp) for comp in self.allowed_components)

class LevelFilter(logging.Filter):
    """Filter logs by level"""

    def __init__(self, min_level: int = logging.DEBUG, max_level: Optional[int] = None):
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records by level range"""
        if record.levelno < self.min_level:
            return False
        if self.max_level and record.levelno > self.max_level:
            return False
        return True

@dataclass
class LogConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "structured"  # "structured" or "human"
    file_path: Optional[Path] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    component_filters: list = field(default_factory=list)
    enable_syslog: bool = False
    syslog_address: tuple = ("localhost", 514)

class StructuredLogger:
    """
    Structured logging system for core_engine

    Provides component-specific logging with structured JSON output,
    log rotation, and multiple output destinations.
    """

    def __init__(self, config: LogConfig):
        self.config = config
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()

    def _setup_root_logger(self):
        """Setup the root logger with configured handlers"""
        root_logger = logging.getLogger('core_engine')
        root_logger.setLevel(getattr(logging, self.config.level.upper()))

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self._get_formatter())
            root_logger.addHandler(console_handler)

        # Add file handler with rotation
        if self.config.file_path:
            self.config.file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.file_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count
            )
            file_handler.setFormatter(self._get_formatter())
            root_logger.addHandler(file_handler)

        # Add syslog handler
        if self.config.enable_syslog:
            syslog_handler = logging.handlers.SysLogHandler(
                address=self.config.syslog_address
            )
            syslog_handler.setFormatter(logging.Formatter(
                'core_engine: %(name)s[%(process)d]: %(levelname)s: %(message)s'
            ))
            root_logger.addHandler(syslog_handler)

        # Set as root logger
        self.root_logger = root_logger

    def _get_formatter(self) -> logging.Formatter:
        """Get appropriate formatter based on config"""
        if self.config.format == "structured":
            return StructuredFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

    def get_logger(self, component: str) -> logging.Logger:
        """Get or create a component-specific logger"""
        if component in self._loggers:
            return self._loggers[component]

        logger = logging.getLogger(f'core_engine.{component}')

        # Add component-specific filters
        if self.config.component_filters:
            component_filter = ComponentFilter(self.config.component_filters)
            for handler in logger.handlers:
                handler.addFilter(component_filter)

        self._loggers[component] = logger
        return logger

    def log_error_with_context(self, component: str, operation: str,
                              error: Exception, context: Optional[ErrorContext] = None,
                              level: int = logging.ERROR):
        """Log an error with full context information"""
        logger = self.get_logger(component)

        # Prepare log data
        log_data = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }

        if context:
            log_data.update({
                "component": context.component,
                "operation": context.operation,
                "parameters": context.parameters,
                "user_message": context.user_message,
                "system_message": context.system_message
            })

        logger.log(level, f"Error in {operation}", extra=log_data, exc_info=True)

    def log_performance_metric(self, component: str, metric_name: str,
                              value: Union[int, float], unit: str = "",
                              metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        logger = self.get_logger(component)

        log_data = {
            "metric_type": "performance",
            "metric_name": metric_name,
            "value": value,
            "unit": unit
        }

        if metadata:
            log_data.update(metadata)

        logger.info(f"Performance metric: {metric_name} = {value}{unit}", extra=log_data)

    def log_trade_event(self, component: str, event_type: str,
                       symbol: str, quantity: float, price: float,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log trading events"""
        logger = self.get_logger(component)

        log_data = {
            "event_type": "trade",
            "trade_event": event_type,
            "symbol": symbol,
            "quantity": quantity,
            "price": price
        }

        if metadata:
            log_data.update(metadata)

        logger.info(f"Trade event: {event_type} {symbol} {quantity}@{price}", extra=log_data)

    def set_level(self, level: str):
        """Set logging level for all loggers"""
        self.root_logger.setLevel(getattr(logging, level.upper()))
        self.config.level = level

    def reload_config(self, config: LogConfig):
        """Reload logging configuration"""
        self.config = config
        self._setup_root_logger()
        self._loggers.clear()  # Force recreation of component loggers

# Global logger instance
_logger_instance: Optional[StructuredLogger] = None

def init_logging(config: Optional[LogConfig] = None) -> StructuredLogger:
    """Initialize the global structured logger"""
    global _logger_instance

    if config is None:
        config = LogConfig()

    _logger_instance = StructuredLogger(config)
    return _logger_instance

def get_logger(component: str) -> logging.Logger:
    """Get a component-specific logger"""
    if _logger_instance is None:
        init_logging()
    return _logger_instance.get_logger(component)

def log_error_with_context(component: str, operation: str, error: Exception,
                          context: Optional[ErrorContext] = None):
    """Log an error with context using the global logger"""
    if _logger_instance:
        _logger_instance.log_error_with_context(component, operation, error, context)

def log_performance_metric(component: str, metric_name: str, value: Union[int, float],
                          unit: str = "", metadata: Optional[Dict[str, Any]] = None):
    """Log performance metric using the global logger"""
    if _logger_instance:
        _logger_instance.log_performance_metric(component, metric_name, value, unit, metadata)

def log_trade_event(component: str, event_type: str, symbol: str, quantity: float, price: float,
                   metadata: Optional[Dict[str, Any]] = None):
    """Log trade event using the global logger"""
    if _logger_instance:
        _logger_instance.log_trade_event(component, event_type, symbol, quantity, price, metadata)

# Convenience functions for common logging patterns
def log_component_start(component: str, **metadata):
    """Log component startup"""
    logger = get_logger(component)
    logger.info(f"Component {component} starting", extra={"event": "component_start", **metadata})

def log_component_stop(component: str, **metadata):
    """Log component shutdown"""
    logger = get_logger(component)
    logger.info(f"Component {component} stopping", extra={"event": "component_stop", **metadata})

def log_operation_start(component: str, operation: str, **metadata):
    """Log operation start"""
    logger = get_logger(component)
    logger.debug(f"Operation {operation} started", extra={"event": "operation_start", "operation": operation, **metadata})

def log_operation_end(component: str, operation: str, duration_ms: Optional[float] = None, **metadata):
    """Log operation completion"""
    logger = get_logger(component)
    extra = {"event": "operation_end", "operation": operation, **metadata}
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    logger.debug(f"Operation {operation} completed", extra=extra)

# Backward compatibility
def setup_logger(name: str, level: str = "INFO",
                format_string: Optional[str] = None) -> logging.Logger:
    """Setup logger with consistent formatting (backward compatibility)"""
    if _logger_instance is None:
        config = LogConfig(level=level, format="human")
        init_logging(config)

    return get_logger(name)
