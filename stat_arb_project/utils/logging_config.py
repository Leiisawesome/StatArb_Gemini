"""
Logging configuration for production-ready logging.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s") -> logging.Logger:
    """
    Setup comprehensive logging configuration for production use.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
        log_format: Format string for log messages
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels for noisy libraries
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Create and return main logger
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if log_file:
        logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_performance_metrics(logger: logging.Logger, metrics: dict, strategy_name: str = "Strategy"):
    """
    Log performance metrics in a structured format.
    
    Args:
        logger: Logger instance
        metrics: Dictionary of performance metrics
        strategy_name: Name of the strategy for logging
    """
    logger.info(f"=== {strategy_name} Performance Metrics ===")
    for metric, value in metrics.items():
        if isinstance(value, float):
            logger.info(f"{metric.replace('_', ' ').title()}: {value:.4f}")
        else:
            logger.info(f"{metric.replace('_', ' ').title()}: {value}")
    logger.info("=" * 50)

def log_trade_execution(logger: logging.Logger, trade: dict):
    """
    Log trade execution details.
    
    Args:
        logger: Logger instance
        trade: Trade dictionary with execution details
    """
    logger.info(f"Trade executed: {trade['action']} {trade['position_type']} "
                f"at {trade.get('price', 'N/A')} (strength: {trade.get('strength', 'N/A')})")

def log_error_with_context(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Log errors with additional context information.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context information
    """
    logger.error(f"Error in {context}: {str(error)}", exc_info=True) 