"""
Tests for core_engine.trading.execution.order_executor

Focused tests covering the core functionality of the order execution system.
"""

import pytest
from datetime import datetime

from core_engine.trading.execution.order_executor import (
    OrderType,
    TimeInForce,
    OrderStatus,
    ExecutionQuality,
    OrderExecutionConfig,
    OrderRequest,
    Fill,
    OrderState,
    MarketMicrostructureAnalyzer,
    VenueSelector,
    OrderLifecycleManager,
    OrderExecutor,
)


@pytest.fixture
def default_config():
    return OrderExecutionConfig()


@pytest.fixture
def sample_order_request():
    return OrderRequest(
        order_id="TEST001",
        symbol="AAPL",
        side="BUY",
        quantity=1000.0,
        order_type=OrderType.LIMIT,
        limit_price=150.00,
        time_in_force=TimeInForce.DAY,
    )


@pytest.fixture
def sample_fill():
    return Fill(
        fill_id="FILL001",
        order_id="TEST001",
        symbol="AAPL",
        side="BUY",
        fill_quantity=100.0,
        fill_price=150.05,
        fill_time=datetime.now(),
        venue="NYSE",
    )


@pytest.fixture
def order_executor(default_config):
    return OrderExecutor(default_config)


class TestOrderExecutionConfig:
    def test_default_config(self, default_config):
        assert default_config.default_order_type == OrderType.LIMIT
        assert default_config.default_time_in_force == TimeInForce.DAY
        assert default_config.max_order_lifetime == 3600
    
    def test_custom_config(self):
        config = OrderExecutionConfig(
            default_order_type=OrderType.MARKET,
            max_order_lifetime=1800,
        )
        assert config.default_order_type == OrderType.MARKET


class TestOrderRequest:
    def test_basic_order_request(self, sample_order_request):
        assert sample_order_request.order_id == "TEST001"
        assert sample_order_request.symbol == "AAPL"
        assert sample_order_request.quantity == 1000.0
    
    def test_market_order(self):
        request = OrderRequest(
            order_id="MKT001",
            symbol="TSLA",
            side="SELL",
            quantity=500.0,
            order_type=OrderType.MARKET,
        )
        assert request.order_type == OrderType.MARKET


class TestFill:
    def test_basic_fill(self, sample_fill):
        assert sample_fill.fill_id == "FILL001"
        assert sample_fill.fill_quantity == 100.0
        assert sample_fill.fill_price == 150.05


class TestOrderState:
    def test_new_order_state(self, sample_order_request):
        state = OrderState(request=sample_order_request)
        assert state.status == OrderStatus.PENDING_NEW
        assert state.filled_quantity == 0.0


class TestMarketMicrostructureAnalyzer:
    def test_analyzer_initialization(self, default_config):
        analyzer = MarketMicrostructureAnalyzer(default_config)
        assert analyzer.config is not None
    
    def test_calculate_optimal_price(self, default_config):
        analyzer = MarketMicrostructureAnalyzer(default_config)
        result = analyzer.calculate_optimal_price(
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            quality=ExecutionQuality.NORMAL
        )
        assert 'optimal_price' in result


class TestVenueSelector:
    def test_venue_selector_initialization(self, default_config):
        selector = VenueSelector(default_config)
        assert selector.config is not None
        assert hasattr(selector, '_venue_performance')
    
    def test_select_execution_venues(self, default_config):
        selector = VenueSelector(default_config)
        venues = selector.select_execution_venues(
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            quality=ExecutionQuality.NORMAL
        )
        assert isinstance(venues, list)


class TestOrderLifecycleManager:
    def test_lifecycle_manager_initialization(self, default_config):
        manager = OrderLifecycleManager(default_config)
        assert manager.config is not None
    
    def test_create_order_state(self, default_config, sample_order_request):
        manager = OrderLifecycleManager(default_config)
        state = manager.create_order_state(sample_order_request)
        assert state.request == sample_order_request


class TestOrderExecutor:
    def test_executor_initialization(self, order_executor):
        assert order_executor.config is not None
        assert hasattr(order_executor, "microstructure_analyzer")
    
    @pytest.mark.asyncio
    async def test_execute_order_basic(self, order_executor, sample_order_request):
        order_id = await order_executor.execute_order(sample_order_request)
        assert order_id == sample_order_request.order_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
