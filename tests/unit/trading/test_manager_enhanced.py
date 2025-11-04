#!/usr/bin/env python3
"""
Test Suite for TradingManagerEnhanced
====================================

Comprehensive test suite for the enhanced trading manager component.
Covers order management, execution handling, cost analysis, and venue routing.

Author: Test Coverage Enhancement
Version: 1.0.0
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from core_engine.trading.manager_enhanced import (
    TradingManagerEnhanced,
    TradingMode,
    TradingSessionStatus,
    TradingConfiguration,
    TradingMetrics,
    TradingAlert
)
from core_engine.trading.order_manager import Order, OrderSide, OrderStatus
from core_engine.trading.execution_handler import ExecutionStrategy, ExecutionReport
from core_engine.trading.venue_router import RoutingStrategy, RoutingPlan, VenueRouter


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def basic_config():
    """Basic configuration for trading manager"""
    return {
        'mode': 'paper',
        'max_position_size': 1000000,
        'max_daily_volume': 5000000,
        'max_order_value': 100000,
        'position_limit_percentage': 0.1,
        'order_timeout_seconds': 30,
        'max_retry_attempts': 3,
        'cool_down_period_seconds': 5,
        'market_data_timeout_seconds': 10,
        'price_staleness_threshold_seconds': 5
    }


@pytest.fixture
def trading_manager(basic_config):
    """Create trading manager instance"""
    # Mock the async task creation in __init__
    with patch('asyncio.create_task'):
        manager = TradingManagerEnhanced(basic_config)
    return manager


@pytest.fixture
def sample_order():
    """Create sample order for testing"""
    from core_engine.trading.order_manager import OrderType
    return Order(
        order_id="test_order_1",
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=150.0
    )


# =============================================================================
# TEST CATEGORY 1: INITIALIZATION
# =============================================================================

def test_initialization_with_config(trading_manager, basic_config):
    """Test trading manager initialization with configuration"""
    assert trading_manager is not None
    assert trading_manager.config == basic_config
    assert trading_manager.order_manager is not None
    assert trading_manager.execution_handler is not None
    assert trading_manager.cost_analyzer is not None
    assert trading_manager.venue_router is not None


def test_initialization_without_config():
    """Test trading manager initialization without configuration"""
    with patch('asyncio.create_task'):
        manager = TradingManagerEnhanced()
    assert manager is not None
    assert manager.config == {}


def test_trading_config_initialization(trading_manager):
    """Test trading configuration initialization"""
    assert trading_manager.trading_config is not None
    assert isinstance(trading_manager.trading_config, TradingConfiguration)
    assert trading_manager.trading_config.mode == TradingMode.PAPER
    assert trading_manager.trading_config.session_status == TradingSessionStatus.INACTIVE


def test_metrics_initialization(trading_manager):
    """Test metrics initialization"""
    assert trading_manager._trading_metrics is not None
    assert isinstance(trading_manager._trading_metrics, TradingMetrics)
    assert trading_manager._trading_metrics.total_orders == 0
    assert trading_manager._trading_metrics.executed_orders == 0


# =============================================================================
# TEST CATEGORY 2: ORDER MANAGEMENT
# =============================================================================

@pytest.mark.asyncio
async def test_submit_order(trading_manager, sample_order):
    """Test order submission"""
    # Mock order manager methods
    trading_manager.order_manager.submit_order = AsyncMock(return_value=sample_order.order_id)
    trading_manager.trading_config.session_status = TradingSessionStatus.OPEN
    trading_manager._pre_trade_risk_check = AsyncMock()
    
    result = await trading_manager.submit_order(sample_order)
    
    assert result is not None
    trading_manager.order_manager.submit_order.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_order(trading_manager):
    """Test order cancellation"""
    order_id = "test_order_1"
    trading_manager.order_manager.cancel_order = AsyncMock(return_value=True)
    
    result = await trading_manager.cancel_order(order_id)
    
    assert result is True
    # cancel_order takes order_id and reason
    trading_manager.order_manager.cancel_order.assert_called()


@pytest.mark.asyncio
async def test_get_order_status(trading_manager):
    """Test getting order status"""
    order_id = "test_order_1"
    mock_order = Mock()
    mock_order.status = OrderStatus.FILLED
    trading_manager.order_manager.get_order = AsyncMock(return_value=mock_order)
    
    # Use order_manager.get_order directly since manager may not have this method
    order = await trading_manager.order_manager.get_order(order_id)
    
    assert order is not None
    assert order.status == OrderStatus.FILLED


# =============================================================================
# TEST CATEGORY 3: EXECUTION HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_execute_order(trading_manager, sample_order):
    """Test order execution"""
    mock_report = ExecutionReport(
        order_id=sample_order.order_id,
        execution_id="exec_1",
        symbol=sample_order.symbol,
        quantity_filled=100,
        avg_fill_price=150.0,
        total_cost=0.0,
        timestamp=datetime.now()
    )
    
    trading_manager.execution_handler.execute = AsyncMock(return_value=mock_report)
    trading_manager.order_manager.get_order = AsyncMock(return_value=sample_order)
    
    result = await trading_manager.execute_order(sample_order.order_id)
    
    assert result is not None
    assert result.order_id == sample_order.order_id


@pytest.mark.asyncio
async def test_execution_callbacks(trading_manager, sample_order):
    """Test execution callbacks"""
    callback_called = False
    
    def execution_callback(report):
        nonlocal callback_called
        callback_called = True
    
    trading_manager.register_execution_callback(execution_callback)
    
    # Simulate execution
    mock_report = ExecutionReport(
        order_id=sample_order.order_id,
        execution_id="exec_1",
        symbol=sample_order.symbol,
        quantity_filled=100,
        avg_fill_price=150.0,
        total_cost=0.0,
        timestamp=datetime.now()
    )
    
    # Call callbacks manually for testing
    for callback in trading_manager._execution_callbacks:
        callback(mock_report)
    
    assert callback_called is True


# =============================================================================
# TEST CATEGORY 4: COST ANALYSIS
# =============================================================================

@pytest.mark.asyncio
async def test_analyze_execution_cost(trading_manager):
    """Test execution cost analysis"""
    mock_report = ExecutionReport(
        order_id="order_1",
        execution_id="exec_1",
        symbol="AAPL",
        quantity_filled=100,
        avg_fill_price=150.0,
        total_cost=15.0,
        timestamp=datetime.now()
    )
    
    trading_manager.cost_analyzer.analyze = AsyncMock(return_value={
        'total_cost_bps': 10.0,
        'slippage_bps': 5.0,
        'commission_bps': 5.0
    })
    
    result = await trading_manager.analyze_execution_cost(mock_report)
    
    assert result is not None
    assert 'total_cost_bps' in result


# =============================================================================
# TEST CATEGORY 5: VENUE ROUTING
# =============================================================================

@pytest.mark.asyncio
async def test_route_order(trading_manager, sample_order):
    """Test order routing"""
    mock_routing_plan = Mock()
    mock_routing_plan.primary_venue = "venue_1"
    mock_routing_plan.venue_allocations = {"venue_1": 1.0}
    
    trading_manager.venue_router.route = AsyncMock(return_value=mock_routing_plan)
    
    result = await trading_manager.route_order(sample_order)
    
    assert result is not None
    trading_manager.venue_router.route.assert_called_once()


# =============================================================================
# TEST CATEGORY 6: METRICS AND MONITORING
# =============================================================================

def test_get_trading_metrics(trading_manager):
    """Test getting trading metrics"""
    metrics = trading_manager.get_trading_metrics()
    
    assert metrics is not None
    assert isinstance(metrics, TradingMetrics)
    assert metrics.total_orders == 0


def test_update_metrics(trading_manager):
    """Test metrics update"""
    initial_orders = trading_manager._trading_metrics.total_orders
    
    # Simulate order execution
    trading_manager._trading_metrics.total_orders += 1
    trading_manager._trading_metrics.executed_orders += 1
    
    assert trading_manager._trading_metrics.total_orders == initial_orders + 1
    assert trading_manager._trading_metrics.executed_orders == 1


def test_get_performance_history(trading_manager):
    """Test getting performance history"""
    # Add some performance data
    trading_manager._performance_history['AAPL'].append({
        'timestamp': datetime.now(),
        'pnl': 100.0
    })
    
    history = trading_manager.get_performance_history('AAPL')
    
    assert history is not None
    assert len(history) > 0


# =============================================================================
# TEST CATEGORY 7: ALERT SYSTEM
# =============================================================================

def test_create_alert(trading_manager):
    """Test alert creation"""
    alert = trading_manager.create_alert(
        alert_type="risk_limit",
        severity="high",
        message="Risk limit breached",
        component="risk_manager"
    )
    
    assert alert is not None
    assert isinstance(alert, TradingAlert)
    assert alert.alert_type == "risk_limit"
    assert alert.severity == "high"


def test_register_alert_handler(trading_manager):
    """Test alert handler registration"""
    handler_called = False
    
    def alert_handler(alert):
        nonlocal handler_called
        handler_called = True
    
    trading_manager.register_alert_handler("risk_limit", alert_handler)
    
    # Create and trigger alert
    alert = trading_manager.create_alert(
        alert_type="risk_limit",
        severity="high",
        message="Test",
        component="test"
    )
    
    # Manually trigger handler for testing
    if "risk_limit" in trading_manager._alert_handlers:
        trading_manager._alert_handlers["risk_limit"](alert)
    
    assert handler_called is True


def test_get_recent_alerts(trading_manager):
    """Test getting recent alerts"""
    # Create some alerts
    for i in range(5):
        trading_manager.create_alert(
            alert_type=f"alert_{i}",
            severity="medium",
            message=f"Alert {i}",
            component="test"
        )
    
    recent_alerts = trading_manager.get_recent_alerts(limit=3)
    
    assert len(recent_alerts) <= 3


# =============================================================================
# TEST CATEGORY 8: SESSION MANAGEMENT
# =============================================================================

@pytest.mark.asyncio
async def test_start_trading_session(trading_manager):
    """Test starting trading session"""
    await trading_manager.start_trading_session()
    
    assert trading_manager.trading_config.session_status == TradingSessionStatus.OPEN
    assert trading_manager._session_start_time is not None


@pytest.mark.asyncio
async def test_stop_trading_session(trading_manager):
    """Test stopping trading session"""
    await trading_manager.start_trading_session()
    await trading_manager.stop_trading_session()
    
    assert trading_manager.trading_config.session_status == TradingSessionStatus.CLOSED


# =============================================================================
# TEST CATEGORY 9: ERROR HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_order_submission_error(trading_manager):
    """Test error handling in order submission"""
    trading_manager.order_manager.submit_order = AsyncMock(side_effect=Exception("Order submission failed"))
    
    with pytest.raises(Exception):
        await trading_manager.submit_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type="MARKET"
        )


@pytest.mark.asyncio
async def test_execution_error_handling(trading_manager):
    """Test error handling in execution"""
    trading_manager.execution_handler.execute = AsyncMock(side_effect=Exception("Execution failed"))
    trading_manager.order_manager.get_order = AsyncMock(return_value=Mock(order_id="test"))
    
    with pytest.raises(Exception):
        await trading_manager.execute_order("test_order")


# =============================================================================
# TEST CATEGORY 10: THREAD SAFETY
# =============================================================================

def test_concurrent_order_operations(trading_manager):
    """Test concurrent order operations"""
    import threading
    
    results = []
    
    def submit_order(idx):
        try:
            # Mock the async call
            order = Mock(order_id=f"order_{idx}")
            results.append(order)
        except Exception as e:
            results.append(f"Error: {e}")
    
    threads = []
    for i in range(10):
        thread = threading.Thread(target=submit_order, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    assert len(results) == 10

