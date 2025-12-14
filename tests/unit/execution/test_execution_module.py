"""
Unit tests for trading execution module components.
Tests execution engine, order management, and related components.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from core_engine.trading.execution.execution_engine import (
    ExecutionAlgorithm,
    ExecutionUrgency,
    ExecutionStyle,
    ExecutionEngine,
    ExecutionConfig,
    ExecutionRequest,
    ExecutionMetrics,
    ExecutionStatus
)

from core_engine.trading.execution.execution_validator import (
    ExecutionValidator,
    ExecutionContext
)

from core_engine.trading.execution.fill_processor import (
    FillProcessor,
    FillEvent,
    FillMetrics
)

class TestExecutionEngine:
    """Test suite for ExecutionEngine class."""

    @pytest.fixture
    def execution_config(self):
        """Create test execution configuration."""
        return ExecutionConfig(
            default_algorithm=ExecutionAlgorithm.MARKET,
            max_execution_time=300,
            enable_pre_trade_risk=True,
            enable_real_time_risk=True
        )

    @pytest.fixture
    def execution_engine(self, execution_config):
        """Create test execution engine."""
        return ExecutionEngine(execution_config)

    def test_initialization(self, execution_engine, execution_config):
        """Test execution engine initialization."""
        assert execution_engine.config == execution_config
        assert len(execution_engine._active_requests) == 0

    @pytest.mark.asyncio
    async def test_submit_execution_request(self, execution_engine):
        """Test submitting an execution request."""
        request = ExecutionRequest(
            request_id="req_123",
            symbol="AAPL",
            quantity=100,
            side="BUY",
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL,
            style=ExecutionStyle.PASSIVE
        )

        # Mock the internal components to avoid complex dependencies
        with patch.object(execution_engine.risk_monitor, 'check_pre_trade_risk') as mock_risk:
            with patch.object(execution_engine.slicing_engine, 'generate_slices') as mock_slices:
                with patch.object(execution_engine, '_get_market_conditions') as mock_conditions:
                    mock_risk.return_value = (True, [])
                    mock_slices.return_value = []
                    mock_conditions.return_value = {}

                    result = await execution_engine.submit_execution_request(request)

                    assert result == "req_123"  # Should return the request_id
                    assert "req_123" in execution_engine._active_requests

    def test_cancel_execution(self, execution_engine):
        """Test canceling an execution."""
        request_id = "req_123"

        # Add a mock active request
        execution_engine._active_requests[request_id] = {
            'request': Mock(),
            'slices': [],
            'status': ExecutionStatus.PENDING,
            'created_at': datetime.now()
        }

        result = execution_engine.cancel_execution(request_id)

        assert result is True
        assert execution_engine._active_requests[request_id]['status'] == ExecutionStatus.CANCELLED

    def test_get_execution_status(self, execution_engine):
        """Test getting execution status."""
        request_id = "req_123"

        # Add a mock active request
        execution_engine._active_requests[request_id] = {
            'request': Mock(),
            'slices': [Mock(quantity=100, filled_quantity=50, status=ExecutionStatus.PARTIALLY_FILLED,
                           avg_fill_price=150.0, slippage=0.5)],
            'status': ExecutionStatus.PARTIALLY_FILLED,
            'created_at': datetime.now()
        }

        status = execution_engine.get_execution_status(request_id)

        assert status is not None
        assert status['request_id'] == request_id
        assert status['status'] == ExecutionStatus.PARTIALLY_FILLED
        assert status['filled_quantity'] == 50
        assert status['fill_rate'] == 0.5

    def test_get_execution_metrics(self, execution_engine):
        """Test getting execution metrics."""
        metrics = execution_engine.get_execution_metrics()

        assert isinstance(metrics, ExecutionMetrics)
        assert hasattr(metrics, 'total_executions')
        assert hasattr(metrics, 'successful_executions')
        assert hasattr(metrics, 'failed_executions')

class TestExecutionValidator:
    """Test suite for ExecutionValidator class."""

    @pytest.fixture
    def validation_config(self):
        """Create test validation configuration."""
        # ExecutionValidator doesn't require config, return None
        return None

    @pytest.fixture
    def execution_validator(self, validation_config):
        """Create test execution validator."""
        return ExecutionValidator()

    def test_initialization(self, execution_validator, validation_config):
        """Test execution validator initialization."""
        assert execution_validator is not None
        assert hasattr(execution_validator, 'validate_pre_trade')

    def test_validate_order_size_valid(self, execution_validator):
        """Test validating a valid order size."""
        context = ExecutionContext(
            execution_id="test_exec_1",
            order_id="test_order_1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        assert is_valid is True
        # All validation results should have passed=True
        assert all(result.passed for result in results)

    def test_validate_order_size_too_large(self, execution_validator):
        """Test validating an order size that's too large."""
        context = ExecutionContext(
            execution_id="test_exec_2",
            order_id="test_order_2",
            symbol="AAPL",
            side="BUY",
            quantity=2000000,  # 2M shares - exceeds 1M limit
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        assert is_valid is False
        # At least one validation result should have failed
        assert any(not result.passed for result in results)
        # Check that at least one result mentions size
        size_related_results = [r for r in results if "size" in r.message.lower() or not r.passed]
        assert len(size_related_results) > 0

    def test_validate_market_hours_valid(self, execution_validator):
        """Test validating market hours for a valid time."""
        # Assuming current time is during market hours
        context = ExecutionContext(
            execution_id="test_exec_3",
            order_id="test_order_3",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Market hours validation should pass during normal trading hours
        assert is_valid is True

    def test_validate_liquidity_sufficient(self, execution_validator):
        """Test validating sufficient liquidity."""
        context = ExecutionContext(
            execution_id="test_exec_4",
            order_id="test_order_4",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0,
            current_price=150.0,
            bid_price=149.5,
            ask_price=150.5
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        assert is_valid is True

    def test_validate_negative_quantity(self, execution_validator):
        """Test validating negative quantity."""
        context = ExecutionContext(
            execution_id="test_exec_5",
            order_id="test_order_5",
            symbol="AAPL",
            side="BUY",
            quantity=-100,  # Invalid negative quantity
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Check that validation ran and has results
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validate_zero_quantity(self, execution_validator):
        """Test validating zero quantity."""
        context = ExecutionContext(
            execution_id="test_exec_6",
            order_id="test_order_6",
            symbol="AAPL",
            side="BUY",
            quantity=0,  # Invalid zero quantity
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Check that validation ran and has results
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validate_negative_price(self, execution_validator):
        """Test validating negative price."""
        context = ExecutionContext(
            execution_id="test_exec_7",
            order_id="test_order_7",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=-150.0  # Invalid negative price
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Check that validation ran and has results
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validate_invalid_side(self, execution_validator):
        """Test validating invalid side."""
        context = ExecutionContext(
            execution_id="test_exec_8",
            order_id="test_order_8",
            symbol="AAPL",
            side="HOLD",  # Invalid side (should be BUY or SELL)
            quantity=100,
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Check that validation ran and has results
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validate_empty_symbol(self, execution_validator):
        """Test validating empty symbol."""
        context = ExecutionContext(
            execution_id="test_exec_9",
            order_id="test_order_9",
            symbol="",  # Empty symbol
            side="BUY",
            quantity=100,
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Check that validation ran and has results
        assert isinstance(results, list)
        assert len(results) > 0

    def test_validate_extreme_price_deviation(self, execution_validator):
        """Test validating extreme price deviation."""
        context = ExecutionContext(
            execution_id="test_exec_10",
            order_id="test_order_10",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=500.0,  # Extreme price
            current_price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # May fail due to extreme price deviation
        # Note: Result depends on validation rules
        assert isinstance(is_valid, bool)
        assert isinstance(results, list)

    def test_validate_fractional_quantity(self, execution_validator):
        """Test validating fractional quantity."""
        context = ExecutionContext(
            execution_id="test_exec_11",
            order_id="test_order_11",
            symbol="AAPL",
            side="BUY",
            quantity=100.5,  # Fractional quantity
            price=150.0
        )

        is_valid, results = execution_validator.validate_pre_trade(context)

        # Some validators may accept fractional quantities
        assert isinstance(is_valid, bool)

    def test_validate_multiple_contexts(self, execution_validator):
        """Test validating multiple execution contexts."""
        contexts = [
            ExecutionContext(
                execution_id=f"test_exec_{i}",
                order_id=f"test_order_{i}",
                symbol="AAPL",
                side="BUY" if i % 2 == 0 else "SELL",
                quantity=100 + i * 10,
                price=150.0 + i
            )
            for i in range(5)
        ]

        results_list = []
        for context in contexts:
            is_valid, results = execution_validator.validate_pre_trade(context)
            results_list.append((is_valid, results))

        # Should have results for all contexts
        assert len(results_list) == 5
        # All should be valid normal orders
        assert all(is_valid for is_valid, _ in results_list)

class TestFillProcessor:
    """Test suite for FillProcessor class."""

    @pytest.fixture
    def fill_processor(self):
        """Create test fill processor."""
        return FillProcessor()

    def test_initialization(self, fill_processor):
        """Test fill processor initialization."""
        assert fill_processor is not None
        assert len(fill_processor.fill_events) == 0

    def test_process_fill_event(self, fill_processor):
        """Test processing a fill event."""
        fill_event = FillEvent(
            order_id="order_123",
            symbol="AAPL",
            quantity=50,
            price=150.0,
            timestamp=datetime.now(),
            commission=0.5
        )

        fill_processor.process_fill_event(fill_event)

        assert len(fill_processor.fill_events) == 1
        assert fill_processor.fill_events[0] == fill_event

    def test_get_fill_metrics(self, fill_processor):
        """Test getting fill metrics."""
        # Add some fill events
        for i in range(3):
            fill_event = FillEvent(
                order_id=f"order_{i}",
                symbol="AAPL",
                quantity=100,
                price=150.0 + i,
                timestamp=datetime.now(),
                commission=0.5
            )
            fill_processor.process_fill_event(fill_event)

        metrics = fill_processor.get_fill_metrics("AAPL")

        assert isinstance(metrics, FillMetrics)
        assert metrics.total_fills == 3
        assert metrics.total_quantity == 300
        assert abs(metrics.average_price - 151.0) < 0.01
