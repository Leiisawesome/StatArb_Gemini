"""
Unit tests for trading module components
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass
import pytest_asyncio

# Import actual classes
from core_engine.trading.engine import EnhancedTradingEngine, TradePlan, ExecutionStrategy, TradePriority
from core_engine.trading.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus, OrderExecution
from core_engine.trading.venue_router import VenueRouter, VenueProfile, VenueType, VenueStatus, RoutingStrategy
from core_engine.trading.transaction_cost_analyzer import TransactionCostAnalyzer, BenchmarkType, TransactionCostBreakdown


# Fixtures
@pytest.fixture
def trading_engine():
    """Create TradingEngine instance"""
    config = {
        'default_execution_strategy': 'SMART_ROUTING',
        'max_slice_size': 1000.0,
        'enable_smart_routing': True
    }
    return EnhancedTradingEngine(config)


@pytest_asyncio.fixture
async def venue_router():
    """Create VenueRouter instance"""
    router = VenueRouter()
    # Initialize default venues
    await router._initialize_default_venues()
    return router


@pytest.fixture
def order_manager():
    """Create OrderManager instance"""
    return OrderManager()


@pytest.fixture
def cost_analyzer():
    """Create TransactionCostAnalyzer instance"""
    return TransactionCostAnalyzer()


@pytest.fixture
def sample_trade_request():
    """Sample trade request for testing"""
    return {
        'symbol': 'AAPL',
        'quantity': 1000,
        'side': 'buy',
        'priority': 'NORMAL',
        'execution_strategy': 'SMART_ROUTING',
        'target_price': 150.0,
        'metadata': {'signal_id': 'sig_001', 'confidence': 0.85}
    }


@pytest.fixture
def sample_order():
    """Sample order for testing"""
    return Order(
        order_id='test_order_001',
        symbol='AAPL',
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
        price=None,
        metadata={'signal_id': 'sig_001'}
    )


@pytest.fixture
def sample_venues():
    """Sample venue profiles for testing"""
    return [
        VenueProfile(
            venue_id='NASDAQ',
            name='NASDAQ Exchange',
            venue_type=VenueType.EXCHANGE,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.MARKET, OrderType.LIMIT},
            supported_symbols={'*'},
            min_order_size=1,
            max_order_size=1000000,
            tick_size=0.01,
            typical_depth=50000,
            fill_rate=0.95,
            average_fill_size=2500,
            dark_pool_indicator=False,
            commission_rate=0.002,
            fee_structure={'access_fee': 0.003},
            rebate_rate=0.001,
            access_fee=0.003,
            average_latency_ms=2.5,
            success_rate=0.98,
            rejection_rate=0.02,
            market_impact_factor=1.0,
            trading_hours={'open': '09:30', 'close': '16:00'},
            connectivity_type='FIX',
            api_version='4.4'
        ),
        VenueProfile(
            venue_id='CROSSFINDER',
            name='Credit Suisse CrossFinder',
            venue_type=VenueType.DARK_POOL,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.MARKET, OrderType.LIMIT},
            supported_symbols={'*'},
            min_order_size=100,
            max_order_size=500000,
            tick_size=0.01,
            typical_depth=25000,
            fill_rate=0.65,
            average_fill_size=1800,
            dark_pool_indicator=True,
            commission_rate=0.001,
            fee_structure={'access_fee': 0.001},
            rebate_rate=0.0,
            access_fee=0.001,
            average_latency_ms=15.0,
            success_rate=0.92,
            rejection_rate=0.08,
            market_impact_factor=0.3,
            trading_hours={'open': '09:30', 'close': '16:00'},
            connectivity_type='FIX',
            api_version='4.4'
        )
    ]


@pytest.fixture
def sample_execution():
    """Sample execution for testing"""
    return OrderExecution(
        execution_id='exec_001',
        order_id='order_001',
        symbol='AAPL',
        side=OrderSide.BUY,
        quantity=100,
        price=150.0,
        timestamp=datetime.now(),
        venue='NASDAQ',
        commission=1.5,
        fees=0.0
    )


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        'arrival_price': 149.75,
        'close_price': 150.25,
        'midpoint': 150.0,
        'open_price': 149.5,
        'vwap': 150.1,
        'twap': 150.05,
        'spread_bps': 5.0,
        'volume': 1000000,
        'volatility': 0.02
    }


class TestEnhancedTradingEngine:
    """Test TradingEngine functionality"""

    def test_initialization(self, trading_engine):
        """Test TradingEngine initialization"""
        assert isinstance(trading_engine, EnhancedTradingEngine)
        assert trading_engine.config is not None
        assert hasattr(trading_engine, 'active_plans')
        assert hasattr(trading_engine, 'execution_slices')
        assert isinstance(trading_engine.active_plans, dict)
        assert isinstance(trading_engine.execution_slices, dict)

    @pytest.mark.asyncio
    async def test_plan_execution(self, trading_engine, sample_trade_request):
        """Test trade execution planning"""
        # Mock the internal methods
        with patch.object(trading_engine, '_analyze_market_conditions', return_value={}), \
             patch.object(trading_engine, '_determine_execution_strategy', return_value=ExecutionStrategy.SMART_ROUTING), \
             patch.object(trading_engine, '_calculate_order_slicing', return_value={}), \
             patch.object(trading_engine, '_determine_routing_strategy', return_value={}), \
             patch.object(trading_engine, '_create_execution_slices', return_value=[]):

            plan = await trading_engine.plan_execution(sample_trade_request)

            assert isinstance(plan, TradePlan)
            assert plan.symbol == 'AAPL'
            assert plan.total_quantity == 1000
            assert plan.side == 'buy'
            assert plan.strategy == ExecutionStrategy.SMART_ROUTING
            assert plan.plan_id in trading_engine.active_plans

    def test_execution_strategy_enum(self):
        """Test execution strategy enum values"""
        assert ExecutionStrategy.MARKET.value == 'market'
        assert ExecutionStrategy.LIMIT.value == 'limit'
        assert ExecutionStrategy.TWAP.value == 'twap'
        assert ExecutionStrategy.VWAP.value == 'vwap'
        assert ExecutionStrategy.SMART_ROUTING.value == 'smart_routing'


class TestOrderManager:
    """Test OrderManager functionality"""

    def test_initialization(self, order_manager):
        """Test OrderManager initialization"""
        assert isinstance(order_manager, OrderManager)
        assert hasattr(order_manager, '_orders')
        assert hasattr(order_manager, '_order_history')
        assert isinstance(order_manager._orders, dict)
        assert order_manager.enable_order_validation is True

    @pytest.mark.asyncio
    async def test_create_order(self, order_manager):
        """Test order creation"""
        order = await order_manager.create_order(
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        assert isinstance(order, Order)
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.NEW
        assert order.order_id in order_manager._orders

    @pytest.mark.asyncio
    async def test_submit_order(self, order_manager, sample_order):
        """Test order submission"""
        # Add order to manager first and set correct status
        sample_order.status = OrderStatus.NEW
        order_manager._orders[sample_order.order_id] = sample_order

        result = await order_manager.submit_order(sample_order.order_id)
        assert result is True
        assert sample_order.status == OrderStatus.NEW

    @pytest.mark.asyncio
    async def test_order_cancellation(self, order_manager, sample_order):
        """Test order cancellation"""
        # Add order to manager
        order_manager._orders[sample_order.order_id] = sample_order
        sample_order.status = OrderStatus.NEW

        result = await order_manager.cancel_order(sample_order.order_id)
        assert result is True
        assert sample_order.status == OrderStatus.CANCELED

    def test_order_validation(self, order_manager, sample_order):
        """Test order validation"""
        # Test valid order
        result = asyncio.run(order_manager._validate_order(sample_order))
        assert result.is_valid

        # Test invalid order (zero quantity)
        invalid_order = Order(
            order_id='invalid',
            symbol='AAPL',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0
        )
        result = asyncio.run(order_manager._validate_order(invalid_order))
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_order_status_transitions(self, order_manager, sample_order):
        """Test order status transitions"""
        # Initial status
        assert sample_order.status == OrderStatus.PENDING_NEW

        # Test property methods
        assert not sample_order.is_complete
        assert not sample_order.is_active

        # Change to active status
        sample_order.status = OrderStatus.NEW
        assert sample_order.is_active
        assert not sample_order.is_complete

        # Change to complete status
        sample_order.status = OrderStatus.FILLED
        assert sample_order.is_complete
        assert not sample_order.is_active


class TestVenueRouter:
    """Test VenueRouter functionality"""

    @pytest.mark.asyncio
    async def test_initialization(self, venue_router):
        """Test venue router initialization"""
        assert isinstance(venue_router, VenueRouter)
        assert hasattr(venue_router, '_venues')
        assert isinstance(venue_router._venues, dict)
        # Should have default venues after initialization
        assert len(venue_router._venues) > 0

    @pytest.mark.asyncio
    async def test_venue_registration(self, venue_router, sample_venues):
        """Test venue registration"""
        venue = sample_venues[0]

        await venue_router.register_venue(venue)

        assert venue.venue_id in venue_router._venues
        assert venue_router._venues[venue.venue_id] == venue

    @pytest.mark.asyncio
    async def test_create_routing_plan(self, venue_router, sample_order, sample_venues):
        """Test routing plan creation"""
        # Register venues first
        for venue in sample_venues:
            await venue_router.register_venue(venue)

        # Create routing plan
        plan = await venue_router.create_routing_plan(sample_order)

        assert plan is not None
        assert plan.order_id == sample_order.order_id
        assert plan.symbol == sample_order.symbol
        assert plan.total_quantity == sample_order.quantity

    def test_routing_strategy_enum(self):
        """Test routing strategy enum values"""
        assert RoutingStrategy.BEST_PRICE.value == 'best_price'
        assert RoutingStrategy.LOWEST_COST.value == 'lowest_cost'
        assert RoutingStrategy.BALANCED.value == 'balanced'


class TestTransactionCostAnalyzer:
    """Test TransactionCostAnalyzer functionality"""

    def test_initialization(self, cost_analyzer):
        """Test cost analyzer initialization"""
        assert isinstance(cost_analyzer, TransactionCostAnalyzer)
        assert hasattr(cost_analyzer, '_cost_analyses')
        assert hasattr(cost_analyzer, '_cost_statistics')
        assert cost_analyzer.enable_attribution is True

    @pytest.mark.asyncio
    async def test_analyze_transaction_costs(self, cost_analyzer, sample_execution, sample_market_data):
        """Test transaction cost analysis"""
        # Import ExecutionReport and ExecutionMetrics
        from core_engine.trading.execution_handler import ExecutionReport, ExecutionMetrics
        
        # Create proper ExecutionMetrics
        metrics = ExecutionMetrics(
            order_id='order_001',
            symbol='AAPL',
            side=OrderSide.BUY,
            total_quantity=100,
            executed_quantity=100,
            average_execution_price=150.0,
            benchmark_price=149.75,
            slippage_bps=16.67,
            market_impact_bps=5.0,
            timing_cost_bps=2.0,
            total_cost_bps=23.67,
            execution_time_seconds=1.5,
            venue_breakdown={'NASDAQ': 100.0},
            liquidity_breakdown={'TAKER': 100.0}
        )
        
        # Create proper ExecutionReport
        execution_report = ExecutionReport(
            order_id='order_001',
            executions=[sample_execution],
            metrics=metrics,
            slippage_analysis={'temporary_impact': 5.0, 'permanent_impact': 2.0},
            market_impact_analysis={'price_impact': 3.5, 'volume_impact': 1.2},
            execution_quality_score=85.0,
            recommendations=['Consider using VWAP for large orders']
        )

        # Test that the method exists and can be called
        result = await cost_analyzer.analyze_transaction_costs(
            execution_report,
            sample_market_data,
            BenchmarkType.ARRIVAL_PRICE
        )

        # Just check that we get some result
        assert result is not None

    def test_benchmark_type_enum(self):
        """Test benchmark type enum values"""
        assert BenchmarkType.ARRIVAL_PRICE.value == 'arrival_price'
        assert BenchmarkType.VWAP.value == 'vwap'
        assert BenchmarkType.TWAP.value == 'twap'
        assert BenchmarkType.MIDPOINT.value == 'midpoint'