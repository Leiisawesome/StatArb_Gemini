# Test Writing Guide - StatArb_Gemini

**Version:** 1.0  
**Date:** October 10, 2025  
**Status:** Official Guidelines

---

## Table of Contents

1. [Introduction](#introduction)
2. [Test Organization](#test-organization)
3. [Naming Conventions](#naming-conventions)
4. [Fixture Usage](#fixture-usage)
5. [Test Utilities](#test-utilities)
6. [Assertion Patterns](#assertion-patterns)
7. [Async Testing](#async-testing)
8. [Best Practices](#best-practices)
9. [Common Patterns](#common-patterns)
10. [Examples](#examples)

---

## Introduction

This guide establishes standards for writing tests in the StatArb_Gemini trading system. Following these conventions ensures:

- **Consistency** across the test suite
- **Maintainability** for future developers
- **Readability** for code reviews
- **Reliability** in CI/CD pipelines

### Philosophy

- Tests are documentation - they show how code should be used
- Tests should be easy to read and understand
- Tests should be independent and isolated
- Tests should be fast and deterministic

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                    # Component isolation tests
│   ├── analytics/          # Analytics component tests
│   ├── broker/             # Broker integration tests
│   ├── config/             # Configuration tests
│   ├── data/               # Data management tests
│   ├── execution/          # Order execution tests
│   ├── processing/         # Signal processing tests
│   ├── regime/             # Market regime tests
│   ├── risk/               # Risk management tests
│   ├── strategies/         # Trading strategy tests
│   ├── system/             # System orchestration tests
│   ├── trading/            # Trade management tests
│   └── utils/              # Utility tests
│
├── integration/            # Multi-component tests
│   ├── workflows/          # End-to-end workflows
│   ├── system/             # Full system tests
│   └── components/         # 2-3 component integration
│
├── fixtures/               # Centralized fixtures
│   ├── core_fixtures.py
│   ├── data_fixtures.py
│   ├── strategy_fixtures.py
│   └── integration_fixtures.py
│
├── utils/                  # Test utilities
│   ├── assertions.py       # Custom assertions
│   ├── builders.py         # Test data builders
│   └── helpers.py          # Helper functions
│
├── performance/            # Performance benchmarks
├── production/             # Production readiness tests
└── conftest.py            # Global pytest configuration
```

### When to Create New Files

**Create a new file when:**
- File exceeds 800 lines
- Adding tests for a new component
- Natural logical boundary exists

**Don't create a new file when:**
- Adding 1-2 related tests to existing file
- File under 500 lines with same component focus

---

## Naming Conventions

### File Names

```python
# Unit tests
test_<component>_<subcomponent>.py
test_regime_detector.py
test_risk_manager.py

# Integration tests
test_<workflow>_integration.py
test_data_flow_integration.py
test_e2e_trading.py
```

### Test Function Names

```python
# Pattern: test_<what>_<condition>_<expected>
def test_order_execution_valid_order_returns_filled():
    """Execute valid order and expect filled status."""
    pass

def test_position_calculation_zero_quantity_raises_error():
    """Calculate position with zero quantity and expect ValueError."""
    pass

# For async tests
async def test_data_fetch_timeout_raises_timeout_error():
    """Fetch data with timeout and expect TimeoutError."""
    pass
```

### Class Names

```python
# Pattern: Test<ComponentName>
class TestRegimeDetector:
    """Tests for RegimeDetector class."""
    pass

class TestOrderExecution:
    """Tests for order execution functionality."""
    pass
```

---

## Fixture Usage

### Using Centralized Fixtures

**Always prefer centralized fixtures over inline fixtures:**

```python
# ❌ BAD: Inline fixture
class TestStrategy:
    @pytest.fixture
    def sample_market_data(self):
        dates = pd.date_range('2023-01-01', periods=200)
        # ... data generation code ...
        return data

# ✅ GOOD: Use centralized fixture
class TestStrategy:
    def test_strategy_signal(self, sample_market_data):
        """Test using centralized fixture from fixtures/."""
        signal = strategy.generate_signal(sample_market_data)
        assert signal is not None
```

### Common Centralized Fixtures

**From `tests/fixtures/`:**

```python
# Market Data
sample_market_data          # 200 days of synthetic OHLCV data
multi_asset_market_data     # Data for multiple assets
correlated_pair_data        # Correlated pairs for pairs trading

# Strategies
pairs_trading_strategy      # Configured pairs trading strategy
momentum_strategy           # Configured momentum strategy
mean_reversion_strategy     # Configured mean reversion strategy
trend_following_strategy    # Configured trend following strategy
breakout_strategy           # Configured breakout strategy
factor_strategy             # Configured factor strategy

# Mocks
mock_risk_manager          # Mock risk manager
mock_execution_engine      # Mock execution engine
mock_data_manager          # Mock data manager

# Configuration
strategy_test_config       # Generic strategy configuration
```

### Custom Fixtures

**Only create custom fixtures when:**
- Specific to one test file
- Not reusable across tests
- Requires special setup/teardown

```python
# Custom fixture scope
@pytest.fixture(scope="function")  # New instance per test
@pytest.fixture(scope="class")     # Shared within test class
@pytest.fixture(scope="module")    # Shared within test file
@pytest.fixture(scope="session")   # Shared across entire test session
```

---

## Test Utilities

### Custom Assertions

**Use domain-specific assertions from `tests/utils/assertions.py`:**

```python
from tests.utils.assertions import (
    assert_price_near,
    assert_percentage_near,
    assert_valid_order,
    assert_valid_position,
    assert_dict_contains,
)

def test_order_price(self):
    # ❌ BAD: Manual assertion
    assert abs(order.price - 100.0) < 0.01
    
    # ✅ GOOD: Domain-specific assertion with better error messages
    assert_price_near(order.price, 100.0, tolerance=0.01)
```

### Test Data Builders

**Use builders from `tests/utils/builders.py` for fluent test data creation:**

```python
from tests.utils.builders import (
    MarketDataBuilder,
    OrderBuilder,
    PositionBuilder,
)

def test_order_execution(self):
    # ✅ Fluent builder pattern
    order = (OrderBuilder()
             .with_symbol('AAPL')
             .with_quantity(100)
             .buy()
             .at_limit(150.0)
             .build())
    
    result = engine.execute(order)
    assert_valid_order(result)
```

### Helper Functions

**Use helpers from `tests/utils/helpers.py` for common operations:**

```python
from tests.utils.helpers import (
    generate_random_prices,
    wait_for_condition,
    capture_logs,
)

async def test_order_fills_eventually(self):
    order = await engine.submit_order(order_data)
    
    # Wait for condition with timeout
    await wait_for_condition(
        lambda: order.status == 'filled',
        timeout=5.0,
        error_msg="Order did not fill within 5 seconds"
    )

def test_logging_output(self):
    # Capture logs for testing
    with capture_logs('my_module') as logs:
        my_function()
        
        assert len(logs) == 1
        assert 'success' in logs[0].message.lower()
```

---

## Assertion Patterns

### Standard Assertions

```python
# Equality
assert actual == expected

# Identity
assert actual is None
assert actual is not None

# Membership
assert item in collection
assert key in dictionary

# Type checking
assert isinstance(result, ExpectedType)

# Boolean
assert condition
assert not condition
```

### Trading-Specific Assertions

```python
# Price comparison
assert_price_near(fill_price, 100.0, tolerance=0.05)

# Percentage comparison
assert_percentage_near(returns, 0.05, tolerance=0.001)  # 5%

# Timestamp validation
assert_timestamp_recent(order.created_at, max_age_seconds=60)

# Order validation
assert_valid_order(order, required_fields=['symbol', 'quantity', 'side'])

# Position validation
assert_valid_position(position, allow_zero=False)

# Dictionary subset
assert_dict_contains(result, {
    'status': 'filled',
    'symbol': 'AAPL'
})
```

### Error Assertions

```python
# Expecting exceptions
with pytest.raises(ValueError):
    invalid_operation()

# With error message matching
with pytest.raises(ValueError, match="Invalid quantity"):
    order_with_negative_quantity()

# Async exceptions
with pytest.raises(asyncio.TimeoutError):
    await slow_operation()
```

---

## Async Testing

### Async Test Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation."""
    result = await async_function()
    assert result is not None
```

### Async Fixtures

```python
@pytest.fixture
async def async_resource():
    """Provide async resource."""
    resource = await create_resource()
    yield resource
    await resource.cleanup()
```

### Async Mocking

```python
from unittest.mock import AsyncMock

async def test_with_async_mock():
    mock_service = AsyncMock()
    mock_service.fetch_data = AsyncMock(return_value={'data': [1, 2, 3]})
    
    result = await service_using_mock(mock_service)
    
    mock_service.fetch_data.assert_called_once()
    assert len(result['data']) == 3
```

### Async Waiting

```python
from tests.utils.helpers import wait_for_condition

async def test_eventual_consistency():
    await trigger_operation()
    
    # Wait for condition to become true
    await wait_for_condition(
        lambda: system.state == 'ready',
        timeout=10.0,
        check_interval=0.5
    )
```

---

## Best Practices

### 1. Test Independence

**❌ BAD: Tests depend on each other**

```python
class TestPortfolio:
    def test_add_position(self):
        self.portfolio.add_position('AAPL', 100)
        
    def test_remove_position(self):
        # Depends on test_add_position running first!
        self.portfolio.remove_position('AAPL')
```

**✅ GOOD: Tests are independent**

```python
class TestPortfolio:
    def test_add_position(self, portfolio):
        portfolio.add_position('AAPL', 100)
        assert portfolio.has_position('AAPL')
        
    def test_remove_position(self, portfolio):
        # Set up state explicitly
        portfolio.add_position('AAPL', 100)
        portfolio.remove_position('AAPL')
        assert not portfolio.has_position('AAPL')
```

### 2. Descriptive Test Names

```python
# ❌ BAD: Vague names
def test_order():
def test_position():
def test_1():

# ✅ GOOD: Descriptive names
def test_order_execution_with_valid_params_returns_filled():
def test_position_calculation_with_zero_quantity_raises_value_error():
def test_risk_check_exceeding_limit_blocks_order():
```

### 3. One Assertion Per Concept

```python
# ❌ BAD: Testing multiple unrelated things
def test_order_processing(self):
    order = process_order(data)
    assert order.status == 'filled'
    assert portfolio.cash == 99000  # Different concept
    assert risk_metrics.var < 0.05  # Different concept

# ✅ GOOD: One concept per test
def test_order_processing_returns_filled_status(self):
    order = process_order(data)
    assert order.status == 'filled'

def test_order_processing_updates_portfolio_cash(self):
    process_order(data)
    assert portfolio.cash == 99000

def test_order_processing_maintains_risk_limits(self):
    process_order(data)
    assert risk_metrics.var < 0.05
```

### 4. Use Arrange-Act-Assert Pattern

```python
def test_signal_generation(self):
    # Arrange: Set up test data
    strategy = MomentumStrategy(config)
    market_data = generate_test_data()
    
    # Act: Execute the operation
    signal = strategy.generate_signal(market_data)
    
    # Assert: Verify the result
    assert signal.direction == 'buy'
    assert signal.strength > 0.5
```

### 5. Mock External Dependencies

```python
# ✅ GOOD: Mock external services
@patch('external_api.get_market_data')
def test_data_fetch(self, mock_api):
    mock_api.return_value = sample_data
    
    result = strategy.fetch_and_analyze()
    
    assert result is not None
    mock_api.assert_called_once()
```

---

## Common Patterns

### Testing Strategy Signals

```python
def test_strategy_generates_buy_signal(self, momentum_strategy, sample_market_data):
    """Test strategy generates buy signal with strong momentum."""
    # Arrange: Add upward momentum to data
    data = sample_market_data.copy()
    data['returns'] = 0.02  # Strong positive returns
    
    # Act
    signal = momentum_strategy.generate_signal(data)
    
    # Assert
    assert signal.direction == 'buy'
    assert_percentage_near(signal.strength, 0.8, tolerance=0.1)
```

### Testing Risk Management

```python
def test_risk_manager_blocks_oversized_position(self, risk_manager):
    """Test risk manager blocks position exceeding size limit."""
    # Arrange
    large_order = OrderBuilder().with_quantity(10000).build()
    
    # Act & Assert
    with pytest.raises(RiskLimitExceeded):
        risk_manager.validate_order(large_order)
```

### Testing Data Processing

```python
def test_data_pipeline_handles_missing_values(self):
    """Test pipeline handles missing data gracefully."""
    # Arrange
    data_with_nans = sample_data.copy()
    data_with_nans.loc[10:20, 'close'] = np.nan
    
    # Act
    processed = pipeline.process(data_with_nans)
    
    # Assert
    assert not processed['close'].isna().any()
    assert len(processed) > 0
```

### Testing Async Operations

```python
@pytest.mark.asyncio
async def test_async_order_execution(self, mock_execution_engine):
    """Test async order execution completes successfully."""
    # Arrange
    order = OrderBuilder().buy().at_market().build()
    
    # Act
    result = await mock_execution_engine.execute_order(order)
    
    # Assert
    assert result['status'] == 'filled'
    mock_execution_engine.execute_order.assert_awaited_once()
```

---

## Examples

### Complete Test File Example

```python
"""
Unit tests for momentum strategy.

Tests momentum signal generation, position sizing, and risk management
for the enhanced momentum trading strategy.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_engine.trading.strategies.enhanced_momentum import EnhancedMomentumStrategy
from tests.utils.assertions import assert_percentage_near, assert_valid_order
from tests.utils.builders import MarketDataBuilder, OrderBuilder


class TestMomentumStrategy:
    """Test EnhancedMomentumStrategy class."""
    
    def test_initialization_with_valid_config(self, strategy_test_config):
        """Test strategy initializes with valid configuration."""
        strategy = EnhancedMomentumStrategy(strategy_test_config)
        
        assert strategy.config == strategy_test_config
        assert strategy.lookback_period == 20
    
    def test_signal_generation_strong_uptrend_returns_buy(self, momentum_strategy):
        """Test signal generation with strong uptrend returns buy signal."""
        # Arrange: Create data with strong upward trend
        market_data = (MarketDataBuilder()
                       .with_days(50)
                       .with_trend(0.01)  # 1% daily growth
                       .build())
        
        # Act
        signal = momentum_strategy.generate_signal(market_data)
        
        # Assert
        assert signal.direction == 'buy'
        assert signal.strength > 0.7
        assert_percentage_near(signal.confidence, 0.8, tolerance=0.1)
    
    def test_position_sizing_respects_risk_limits(self, momentum_strategy, mock_risk_manager):
        """Test position sizing respects configured risk limits."""
        # Arrange
        signal = SignalBuilder().buy().with_strength(0.8).build()
        
        # Act
        position_size = momentum_strategy.calculate_position_size(
            signal,
            risk_manager=mock_risk_manager
        )
        
        # Assert
        assert 0 < position_size <= 0.02  # Max 2% per position
        mock_risk_manager.calculate_position_size.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_signal_update(self, momentum_strategy, sample_market_data):
        """Test async signal update mechanism."""
        # Act
        await momentum_strategy.update_signal(sample_market_data)
        
        # Assert
        assert momentum_strategy.last_signal is not None
        assert_timestamp_recent(momentum_strategy.last_update, max_age_seconds=5)
```

---

## Checklist

Before submitting tests, verify:

- [ ] Tests follow naming conventions
- [ ] Tests use centralized fixtures where possible
- [ ] Tests use custom assertions for trading concepts
- [ ] Tests are independent (can run in any order)
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] External dependencies are mocked
- [ ] Test names clearly describe what is tested
- [ ] Module has descriptive docstring
- [ ] File is under 800 lines
- [ ] All tests pass locally

---

## Resources

- **Pytest Documentation:** https://docs.pytest.org/
- **Async Testing Guide:** https://pytest-asyncio.readthedocs.io/
- **Mocking Guide:** https://docs.python.org/3/library/unittest.mock.html

---

**Maintained by:** Trading Systems Team  
**Last Updated:** October 10, 2025  
**Version:** 1.0
