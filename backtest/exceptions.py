"""
Backtest Exception Classes
===========================

Custom exceptions for backtest engine failures.

Following the principle: "Backtest should fail cleanly, not silently degrade."

All exceptions provide detailed context about what failed and why.

Author: StatArb_Gemini Backtest System
Version: 1.0.0
"""


class BacktestError(Exception):
    """
    Base exception for all backtest errors

    All backtest exceptions inherit from this base class,
    allowing callers to catch all backtest-related errors
    with a single except clause if desired.
    """


class BacktestDataError(BacktestError):
    """
    Raised when market data is missing, invalid, or incomplete

    Examples:
    - Missing required fields (close, volume, volatility)
    - Invalid values (negative prices, zero volume with trades)
    - Inconsistent data (high < low, close outside high-low range)
    - Stale or missing timestamps

    This exception indicates the historical data is insufficient
    to continue the backtest. The backtest MUST be fixed by:
    1. Obtaining complete historical data
    2. Fixing data quality issues
    3. Adjusting date range to valid data period
    """


class BacktestConfigurationError(BacktestError):
    """
    Raised when backtest configuration is invalid or incomplete

    Examples:
    - Missing required components (StrategyManager, DataManager)
    - Invalid parameter combinations
    - Missing strategy configurations
    - Incompatible component versions

    This exception indicates the backtest setup is incorrect.
    The backtest MUST be fixed by:
    1. Providing complete configuration
    2. Validating all component configurations
    3. Ensuring all dependencies are met
    """


class BacktestExecutionError(BacktestError):
    """
    Raised when backtest execution fails during runtime

    Examples:
    - Strategy signal generation failures
    - Execution simulation failures
    - Component initialization failures
    - Unexpected state transitions

    This exception indicates a runtime failure that prevents
    the backtest from continuing. The backtest MUST be fixed by:
    1. Debugging the failing component
    2. Fixing the underlying issue
    3. Ensuring component robustness
    """


class BacktestValidationError(BacktestError):
    """
    Raised when backtest validation fails

    Examples:
    - Invalid signals (missing fields, wrong types)
    - Invalid authorization requests
    - Invalid trade parameters
    - Data structure validation failures

    This exception indicates data validation failed.
    The backtest MUST be fixed by:
    1. Fixing data generation logic
    2. Ensuring proper data structures
    3. Validating data before processing
    """


class BacktestIntegrityError(BacktestError):
    """
    Raised when backtest integrity is compromised

    Examples:
    - Position reconciliation failures
    - Cash balance inconsistencies
    - P&L calculation errors
    - State corruption

    This exception indicates the backtest state is corrupted
    and results cannot be trusted. The backtest MUST be:
    1. Stopped immediately
    2. Debugged to find root cause
    3. Restarted from clean state
    """


def format_backtest_error(
    error_type: str,
    message: str,
    context: dict = None,
    suggestion: str = None
) -> str:
    """
    Format a detailed backtest error message

    Args:
        error_type: Type of error (e.g., "Missing Market Data")
        message: Main error message
        context: Additional context (symbol, bar_index, etc.)
        suggestion: Suggested fix

    Returns:
        Formatted error message with all details
    """
    lines = [
        "=" * 80,
        f"❌ BACKTEST FAILED: {error_type}",
        "=" * 80,
        "",
        message,
    ]

    if context:
        lines.append("")
        lines.append("Context:")
        for key, value in context.items():
            lines.append(f"  • {key}: {value}")

    if suggestion:
        lines.append("")
        lines.append("Suggested Fix:")
        lines.append(f"  {suggestion}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)

