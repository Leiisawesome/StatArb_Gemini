"""
Backtest Validation Utilities
==============================

Validation helpers for backtest data integrity.

Following the principle: "Validate data BEFORE use, fail explicitly on invalid data."

Author: StatArb_Gemini Backtest System
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import logging

from backtest.exceptions import (
    BacktestDataError,
    BacktestValidationError,
    format_backtest_error
)

logger = logging.getLogger(__name__)

def validate_market_data_bar(
    bar: Dict[str, Any],
    symbol: str,
    bar_index: int,
    required_fields: Optional[List[str]] = None
) -> None:
    """
    Validate that market data bar contains all required fields with valid values

    This is CRITICAL for backtest integrity. Missing or invalid market data
    means execution simulation will be incorrect.

    Args:
        bar: Market data bar dictionary
        symbol: Trading symbol
        bar_index: Current bar index in backtest
        required_fields: List of required fields (uses defaults if None)

    Raises:
        BacktestDataError: If any required field is missing or invalid

    Example:
        >>> validate_market_data_bar(bar, 'AAPL', 100)
        # Raises BacktestDataError if 'close' is missing
    """
    if required_fields is None:
        required_fields = ['close', 'volume', 'volatility', 'high', 'low', 'timestamp']

    # Check for missing fields
    missing_fields = [f for f in required_fields if f not in bar]
    if missing_fields:
        error_msg = format_backtest_error(
            error_type="Missing Market Data Fields",
            message=f"Market data for {symbol} at bar {bar_index} is incomplete.",
            context={
                'symbol': symbol,
                'bar_index': bar_index,
                'missing_fields': ', '.join(missing_fields),
                'available_fields': ', '.join(bar.keys()) if bar else 'None'
            },
            suggestion=(
                "Ensure historical data source provides all required fields. "
                "Check data loading pipeline and data provider API."
            )
        )
        raise BacktestDataError(error_msg)

    # Check for None values
    none_fields = [f for f in required_fields if bar[f] is None]
    if none_fields:
        error_msg = format_backtest_error(
            error_type="Null Market Data Values",
            message=f"Market data for {symbol} at bar {bar_index} contains null values.",
            context={
                'symbol': symbol,
                'bar_index': bar_index,
                'null_fields': ', '.join(none_fields),
                'bar_data': str(bar)
            },
            suggestion=(
                "Fill or interpolate missing values in historical data. "
                "Consider excluding bars with null values from backtest period."
            )
        )
        raise BacktestDataError(error_msg)

    # Validate field types and ranges
    validation_errors = []

    # Price validations
    for price_field in ['close', 'high', 'low']:
        if price_field in bar:
            value = bar[price_field]
            if not isinstance(value, (int, float)):
                validation_errors.append(f"{price_field}: wrong type (expected number, got {type(value).__name__})")
            elif value <= 0:
                validation_errors.append(f"{price_field}: invalid value ({value} <= 0)")

    # Volume validation
    if 'volume' in bar:
        volume = bar['volume']
        if not isinstance(volume, (int, float)):
            validation_errors.append(f"volume: wrong type (expected number, got {type(volume).__name__})")
        elif volume < 0:
            validation_errors.append(f"volume: invalid value ({volume} < 0)")

    # Volatility validation
    if 'volatility' in bar:
        volatility = bar['volatility']
        if not isinstance(volatility, (int, float)):
            validation_errors.append(f"volatility: wrong type (expected number, got {type(volatility).__name__})")
        elif volatility < 0:
            # Only reject negative volatility; realized vol > 100% is legitimate for
            # crypto and distressed equities (M10 fix — was 0 < vol < 1).
            validation_errors.append(f"volatility: invalid value ({volatility} < 0)")

    # Timestamp validation
    if 'timestamp' in bar:
        timestamp = bar['timestamp']
        if not isinstance(timestamp, (datetime, pd.Timestamp)):
            validation_errors.append(f"timestamp: wrong type (expected datetime, got {type(timestamp).__name__})")

    # Price consistency checks
    if 'high' in bar and 'low' in bar and 'close' in bar:
        high = bar['high']
        low = bar['low']
        close = bar['close']

        if high < low:
            validation_errors.append(f"price inconsistency: high ({high}) < low ({low})")

        if close > high or close < low:
            validation_errors.append(f"price inconsistency: close ({close}) outside high-low range [{low}, {high}]")

    if validation_errors:
        error_msg = format_backtest_error(
            error_type="Invalid Market Data Values",
            message=f"Market data for {symbol} at bar {bar_index} contains invalid values.",
            context={
                'symbol': symbol,
                'bar_index': bar_index,
                'validation_errors': validation_errors,
                'bar_data': str(bar)
            },
            suggestion=(
                "Fix data quality issues in historical data source. "
                "Verify data extraction and transformation pipeline."
            )
        )
        raise BacktestDataError(error_msg)

def validate_signal(
    signal: Dict[str, Any],
    bar_index: int,
    required_fields: Optional[List[str]] = None
) -> None:
    """
    Validate that signal contains all required fields with valid values

    Signals MUST be explicit and complete. No defaults or fallbacks allowed.

    Args:
        signal: Signal dictionary
        bar_index: Current bar index in backtest
        required_fields: List of required fields (uses defaults if None)

    Raises:
        BacktestValidationError: If signal is invalid

    Example:
        >>> validate_signal(signal, 100)
        # Raises BacktestValidationError if 'target_weight' is missing
    """
    if required_fields is None:
        required_fields = ['symbol', 'signal', 'confidence', 'target_weight']

    # Check for missing fields
    missing_fields = [f for f in required_fields if f not in signal]
    if missing_fields:
        error_msg = format_backtest_error(
            error_type="Incomplete Signal",
            message=f"Signal at bar {bar_index} is missing required fields.",
            context={
                'bar_index': bar_index,
                'missing_fields': ', '.join(missing_fields),
                'available_fields': ', '.join(signal.keys()) if signal else 'None',
                'signal_data': str(signal)
            },
            suggestion=(
                "Ensure strategy generates complete signals with all required fields. "
                "Review strategy signal generation logic."
            )
        )
        raise BacktestValidationError(error_msg)

    # Validate field types
    validation_errors = []

    if 'symbol' in signal and not isinstance(signal['symbol'], str):
        validation_errors.append(f"symbol: wrong type (expected str, got {type(signal['symbol']).__name__})")

    if 'signal' in signal and not isinstance(signal['signal'], str):
        validation_errors.append(f"signal: wrong type (expected str, got {type(signal['signal']).__name__})")

    if 'confidence' in signal:
        confidence = signal['confidence']
        if not isinstance(confidence, (int, float)):
            validation_errors.append(f"confidence: wrong type (expected number, got {type(confidence).__name__})")
        elif not (0.0 <= confidence <= 1.0):
            validation_errors.append(f"confidence: out of range ({confidence} not in [0.0, 1.0])")

    if 'target_weight' in signal:
        target_weight = signal['target_weight']
        if not isinstance(target_weight, (int, float)):
            validation_errors.append(f"target_weight: wrong type (expected number, got {type(target_weight).__name__})")
        elif not (-1.0 <= target_weight <= 1.0):
            # Allow negative weights for short signals (M10 fix — was [0, 1])
            validation_errors.append(f"target_weight: out of range ({target_weight} not in [-1.0, 1.0])")

    # Validate signal type (M10 fix + R3 fix: case-insensitive, full signal type set)
    if 'signal' in signal:
        valid_signals = {
            'buy', 'sell', 'hold', 'close',
            'long_entry', 'long_exit', 'short_entry', 'short_exit',
            'short_sell', 'short', 'cover', 'flatten',
            'close_long', 'close_short',
        }
        sig_lower = str(signal['signal']).lower()
        if sig_lower not in valid_signals:
            validation_errors.append(f"signal: invalid value ('{signal['signal']}' not in {sorted(valid_signals)})")

    if validation_errors:
        error_msg = format_backtest_error(
            error_type="Invalid Signal Values",
            message=f"Signal at bar {bar_index} contains invalid values.",
            context={
                'bar_index': bar_index,
                'validation_errors': validation_errors,
                'signal_data': str(signal)
            },
            suggestion=(
                "Fix signal generation logic to produce valid values. "
                "Add validation in strategy signal generation."
            )
        )
        raise BacktestValidationError(error_msg)

def validate_regime_context(
    regime_context: Dict[str, Any],
    bar_index: int,
    min_confidence: float = 0.5
) -> None:
    """
    Validate regime context is complete and reliable

    Per Rule 2 (Regime-First), regime context MUST be valid at all times.

    Args:
        regime_context: Regime context dictionary
        bar_index: Current bar index in backtest
        min_confidence: Minimum required confidence (default: 0.5)

    Raises:
        BacktestDataError: If regime context is invalid

    Example:
        >>> validate_regime_context(regime_context, 100)
        # Raises BacktestDataError if confidence < 0.5
    """
    if not regime_context:
        error_msg = format_backtest_error(
            error_type="Missing Regime Context",
            message=f"Regime context is None or empty at bar {bar_index}.",
            context={
                'bar_index': bar_index,
                'regime_context': 'None' if regime_context is None else 'Empty dict'
            },
            suggestion=(
                "Ensure RegimeEngine is initialized and running (Rule 2 - Regime-First). "
                "Check regime detection is enabled in backtest configuration."
            )
        )
        raise BacktestDataError(error_msg)

    # Check for required fields
    required_fields = ['primary_regime', 'confidence', 'volatility_regime']
    missing_fields = [f for f in required_fields if f not in regime_context]

    if missing_fields:
        error_msg = format_backtest_error(
            error_type="Incomplete Regime Context",
            message=f"Regime context at bar {bar_index} is missing required fields.",
            context={
                'bar_index': bar_index,
                'missing_fields': ', '.join(missing_fields),
                'available_fields': ', '.join(regime_context.keys()),
                'regime_context': str(regime_context)
            },
            suggestion=(
                "Ensure RegimeEngine returns complete regime context. "
                "Check regime detection algorithm implementation."
            )
        )
        raise BacktestDataError(error_msg)

    # Validate confidence level
    confidence = regime_context.get('confidence', 0.0)
    if confidence < min_confidence:
        error_msg = format_backtest_error(
            error_type="Low Regime Confidence",
            message=f"Regime confidence ({confidence:.2%}) below minimum ({min_confidence:.2%}) at bar {bar_index}.",
            context={
                'bar_index': bar_index,
                'confidence': confidence,
                'min_confidence': min_confidence,
                'primary_regime': regime_context.get('primary_regime', 'unknown')
            },
            suggestion=(
                f"Cannot run backtest with unreliable regime detection. Options:\n"
                f"  1. Lower min_confidence threshold (not recommended)\n"
                f"  2. Improve regime detection algorithm\n"
                f"  3. Use longer lookback period for regime detection"
            )
        )
        raise BacktestDataError(error_msg)

    # Validate regime values
    valid_regimes = ['low_volatility', 'normal_volatility', 'high_volatility', 'extreme_volatility', 'crisis']
    primary_regime = regime_context.get('primary_regime', '')

    if primary_regime not in valid_regimes:
        logger.warning(
            f"⚠️  Unknown primary_regime '{primary_regime}' at bar {bar_index}. "
            f"Valid regimes: {', '.join(valid_regimes)}"
        )

def validate_component_initialized(
    component: Any,
    component_name: str,
    operation: str
) -> None:
    """
    Validate that a required component is initialized

    Args:
        component: Component instance to check
        component_name: Name of component for error message
        operation: Operation that requires the component

    Raises:
        BacktestConfigurationError: If component is None or not initialized

    Example:
        >>> validate_component_initialized(self.strategy_manager, 'StrategyManager', 'signal generation')
        # Raises BacktestConfigurationError if StrategyManager is None
    """
    if component is None:
        error_msg = format_backtest_error(
            error_type="Missing Required Component",
            message=f"{component_name} is required for {operation} but is None.",
            context={
                'component_name': component_name,
                'operation': operation,
                'component_value': 'None'
            },
            suggestion=(
                f"Ensure {component_name} is initialized during backtest setup. "
                f"Check component initialization order and configuration."
            )
        )
        from backtest.exceptions import BacktestConfigurationError
        raise BacktestConfigurationError(error_msg)

    # Check if component has is_initialized attribute
    if hasattr(component, 'is_initialized') and not component.is_initialized:
        error_msg = format_backtest_error(
            error_type="Component Not Initialized",
            message=f"{component_name} is not initialized but required for {operation}.",
            context={
                'component_name': component_name,
                'operation': operation,
                'is_initialized': False
            },
            suggestion=(
                f"Call await {component_name}.initialize() before use. "
                f"Check component lifecycle management."
            )
        )
        from backtest.exceptions import BacktestConfigurationError
        raise BacktestConfigurationError(error_msg)

def validate_price_positive(
    price: float,
    field_name: str,
    symbol: str,
    bar_index: int
) -> None:
    """
    Validate that a price value is positive

    Args:
        price: Price value to validate
        field_name: Name of price field (e.g., 'close', 'fill_price')
        symbol: Trading symbol
        bar_index: Current bar index

    Raises:
        BacktestDataError: If price is <= 0 or None
    """
    if price is None:
        error_msg = format_backtest_error(
            error_type="Missing Price Data",
            message=f"{field_name} is None for {symbol} at bar {bar_index}.",
            context={
                'symbol': symbol,
                'bar_index': bar_index,
                'field_name': field_name,
                'value': 'None'
            },
            suggestion=(
                f"Ensure {field_name} is available in market data. "
                f"Check data provider and data loading pipeline."
            )
        )
        raise BacktestDataError(error_msg)

    if price <= 0:
        error_msg = format_backtest_error(
            error_type="Invalid Price Data",
            message=f"{field_name} is invalid ({price}) for {symbol} at bar {bar_index}.",
            context={
                'symbol': symbol,
                'bar_index': bar_index,
                'field_name': field_name,
                'value': price
            },
            suggestion=(
                f"Price must be positive. Check data quality and fix invalid values."
            )
        )
        raise BacktestDataError(error_msg)

