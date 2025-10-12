"""
Test utilities package for StatArb_Gemini.

Provides reusable test utilities, assertions, builders, and helpers
for consistent and maintainable test code across the suite.
"""

from tests.utils.assertions import (
    assert_price_near,
    assert_percentage_near,
    assert_timestamp_recent,
    assert_valid_order,
    assert_valid_position,
    assert_dict_contains,
    assert_async_called_with,
)

from tests.utils.builders import (
    MarketDataBuilder,
    OrderBuilder,
    PositionBuilder,
    PortfolioBuilder,
    SignalBuilder,
)

from tests.utils.helpers import (
    generate_random_prices,
    generate_returns_series,
    create_mock_async_context,
    wait_for_condition,
    capture_logs,
)

__all__ = [
    # Assertions
    "assert_price_near",
    "assert_percentage_near",
    "assert_timestamp_recent",
    "assert_valid_order",
    "assert_valid_position",
    "assert_dict_contains",
    "assert_async_called_with",
    # Builders
    "MarketDataBuilder",
    "OrderBuilder",
    "PositionBuilder",
    "PortfolioBuilder",
    "SignalBuilder",
    # Helpers
    "generate_random_prices",
    "generate_returns_series",
    "create_mock_async_context",
    "wait_for_condition",
    "capture_logs",
]
