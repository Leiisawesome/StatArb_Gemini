"""
Custom assertions for trading system tests.

Provides domain-specific assertions that improve test readability
and provide better error messages for trading-related validations.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from decimal import Decimal


def assert_price_near(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    msg: Optional[str] = None
) -> None:
    """
    Assert that two prices are within a tolerance.
    
    Args:
        actual: Actual price value
        expected: Expected price value
        tolerance: Absolute tolerance (default: 0.01 = 1 cent)
        msg: Optional custom error message
        
    Raises:
        AssertionError: If prices differ by more than tolerance
        
    Example:
        assert_price_near(100.02, 100.00, tolerance=0.05)
    """
    diff = abs(actual - expected)
    if diff > tolerance:
        error_msg = (
            f"Price {actual} not within tolerance of {expected}\n"
            f"Difference: {diff} (tolerance: {tolerance})"
        )
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_percentage_near(
    actual: float,
    expected: float,
    tolerance: float = 0.001,
    msg: Optional[str] = None
) -> None:
    """
    Assert that two percentages/ratios are within tolerance.
    
    Args:
        actual: Actual percentage (0.05 = 5%)
        expected: Expected percentage
        tolerance: Absolute tolerance (default: 0.001 = 0.1%)
        msg: Optional custom error message
        
    Example:
        assert_percentage_near(0.051, 0.05, tolerance=0.01)  # 5.1% vs 5%
    """
    diff = abs(actual - expected)
    if diff > tolerance:
        error_msg = (
            f"Percentage {actual:.4f} ({actual*100:.2f}%) not within tolerance "
            f"of {expected:.4f} ({expected*100:.2f}%)\n"
            f"Difference: {diff:.4f} ({diff*100:.2f}%) (tolerance: {tolerance:.4f})"
        )
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_timestamp_recent(
    timestamp: datetime,
    max_age_seconds: int = 60,
    msg: Optional[str] = None
) -> None:
    """
    Assert that a timestamp is recent (within max_age_seconds of now).
    
    Args:
        timestamp: Timestamp to check
        max_age_seconds: Maximum age in seconds (default: 60)
        msg: Optional custom error message
        
    Example:
        assert_timestamp_recent(order.created_at, max_age_seconds=5)
    """
    now = datetime.now()
    age = (now - timestamp).total_seconds()
    
    if age < 0:
        error_msg = f"Timestamp {timestamp} is in the future (now: {now})"
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)
    
    if age > max_age_seconds:
        error_msg = (
            f"Timestamp {timestamp} is too old\n"
            f"Age: {age:.2f}s (max: {max_age_seconds}s)"
        )
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_valid_order(
    order: Dict[str, Any],
    required_fields: Optional[list] = None
) -> None:
    """
    Assert that an order object has valid structure and values.
    
    Args:
        order: Order dictionary to validate
        required_fields: Optional list of required field names
        
    Example:
        assert_valid_order(order, required_fields=['symbol', 'quantity', 'side'])
    """
    if required_fields is None:
        required_fields = ['symbol', 'quantity', 'side']
    
    # Check required fields exist
    missing_fields = [f for f in required_fields if f not in order]
    if missing_fields:
        raise AssertionError(
            f"Order missing required fields: {missing_fields}\n"
            f"Order keys: {list(order.keys())}"
        )
    
    # Validate quantity is positive
    if 'quantity' in order:
        qty = order['quantity']
        if not isinstance(qty, (int, float, Decimal)) or qty <= 0:
            raise AssertionError(
                f"Invalid order quantity: {qty} (must be positive number)"
            )
    
    # Validate side is valid
    if 'side' in order:
        valid_sides = ['buy', 'sell', 'long', 'short', 'BUY', 'SELL']
        if order['side'] not in valid_sides:
            raise AssertionError(
                f"Invalid order side: {order['side']} (valid: {valid_sides})"
            )


def assert_valid_position(
    position: Dict[str, Any],
    allow_zero: bool = False
) -> None:
    """
    Assert that a position object has valid structure.
    
    Args:
        position: Position dictionary to validate
        allow_zero: Whether zero quantity is allowed (default: False)
        
    Example:
        assert_valid_position(position, allow_zero=True)
    """
    required_fields = ['symbol', 'quantity']
    missing_fields = [f for f in required_fields if f not in position]
    
    if missing_fields:
        raise AssertionError(
            f"Position missing required fields: {missing_fields}"
        )
    
    qty = position['quantity']
    if not allow_zero and qty == 0:
        raise AssertionError(
            f"Position has zero quantity (symbol: {position.get('symbol')})"
        )
    
    if not isinstance(qty, (int, float, Decimal)):
        raise AssertionError(
            f"Invalid position quantity type: {type(qty)} (must be numeric)"
        )


def assert_dict_contains(
    actual: Dict[str, Any],
    expected_subset: Dict[str, Any],
    msg: Optional[str] = None
) -> None:
    """
    Assert that a dictionary contains all key-value pairs from expected_subset.
    
    Args:
        actual: Actual dictionary
        expected_subset: Expected key-value pairs
        msg: Optional custom error message
        
    Example:
        assert_dict_contains(
            result,
            {'status': 'filled', 'symbol': 'AAPL'}
        )
    """
    missing_keys = set(expected_subset.keys()) - set(actual.keys())
    if missing_keys:
        error_msg = f"Missing keys in dict: {missing_keys}"
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)
    
    mismatches = []
    for key, expected_value in expected_subset.items():
        actual_value = actual[key]
        if actual_value != expected_value:
            mismatches.append(
                f"  {key}: expected {expected_value!r}, got {actual_value!r}"
            )
    
    if mismatches:
        error_msg = "Dictionary value mismatches:\n" + "\n".join(mismatches)
        if msg:
            error_msg = f"{msg}\n{error_msg}"
        raise AssertionError(error_msg)


def assert_async_called_with(
    mock_coro,
    *args,
    **kwargs
) -> None:
    """
    Assert that an async mock was called with specific arguments.
    
    Args:
        mock_coro: AsyncMock object
        *args: Expected positional arguments
        **kwargs: Expected keyword arguments
        
    Example:
        await some_async_function(symbol="AAPL", quantity=100)
        assert_async_called_with(
            mock_function,
            symbol="AAPL",
            quantity=100
        )
    """
    try:
        mock_coro.assert_called_with(*args, **kwargs)
    except AssertionError as e:
        # Enhance error message for async context
        raise AssertionError(
            f"Async mock not called with expected arguments\n{str(e)}"
        )
