#!/usr/bin/env python3
"""
Test suite for core_engine.trading.execution.engine
===================================================

Comprehensive tests for the Execution Engine (ACTION Component).
Target: 60%+ coverage on engine.py (265 lines, currently 0%)

Tests cover:
- Enums and dataclasses
- Initialization and lifecycle
- Order execution
- Authorization validation
- Broker routing
- Error handling
- Monitoring and status

Author: StatArb_Gemini Test Suite
Version: 1.0.0
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from core_engine.trading.execution.execution_engine import (
    ExecutionEngine,
    ExecutionStatus,
    ExecutionUrgency as ExecutionPriority,
    ExecutionRequest,
    ExecutionResult as ExecutionReport,
    ExecutionConfig as ExecutionEngineConfig
)
from core_engine.type_definitions.orders import (
    Order, OrderType, OrderSide
)


class TestEnums:
    """Test enum definitions"""
    
    def test_execution_status_enum(self):
        """Test ExecutionStatus enum values"""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.WORKING.value == "working"
        assert ExecutionStatus.PARTIALLY_FILLED.value == "partially_filled"
        assert ExecutionStatus.FILLED.value == "filled"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
        assert ExecutionStatus.REJECTED.value == "rejected"
        assert ExecutionStatus.FAILED.value == "failed"
        
        # Verify all statuses are unique
        statuses = [s.value for s in ExecutionStatus]
        assert len(statuses) == len(set(statuses))
    
    def test_execution_priority_enum(self):
        """Test ExecutionPriority enum values"""
        assert ExecutionPriority.LOW.value == "low"
        assert ExecutionPriority.NORMAL.value == "normal"
        assert ExecutionPriority.HIGH.value == "high"
        assert ExecutionPriority.URGENT.value == "urgent"
        
        # Verify all priorities are unique
        priorities = [p.value for p in ExecutionPriority]
        assert len(priorities) == len(set(priorities))


class TestDataClasses:
    """Test dataclass definitions"""
    
    def test_execution_request_creation(self):
        """Test ExecutionRequest dataclass creation"""
        request = ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="test_token_123",
            broker_preference="IBKR"
        )
        
        assert request.request_id == "req_001"
        assert request.plan_id == "plan_001"
        assert request.symbol == "AAPL"
        assert request.side == "BUY"
        assert request.quantity == 100
        assert request.order_type == OrderType.MARKET
        assert request.price == 150.0
        assert request.time_in_force == "DAY"
        assert request.priority == ExecutionPriority.NORMAL
        assert request.auth_token == "test_token_123"
        assert request.broker_preference == "IBKR"
        assert isinstance(request.created_at, datetime)
    
    def test_execution_request_defaults(self):
        """Test ExecutionRequest default values"""
        request = ExecutionRequest(
            request_id="req_002",
            plan_id="plan_002",
            symbol="TSLA",
            side="SELL",
            quantity=50,
            order_type=OrderType.LIMIT,
            price=200.0,
            time_in_force="GTC",
            priority=ExecutionPriority.HIGH,
            auth_token="token_456"
        )
        
        assert request.broker_preference is None
        assert request.execution_conditions == []
        assert isinstance(request.created_at, datetime)
    
    def test_execution_report_creation(self):
        """Test ExecutionReport dataclass creation"""
        report = ExecutionReport(
            execution_id="exec_001",
            request_id="req_001",
            symbol="AAPL",
            side="BUY",
            requested_quantity=100,
            executed_quantity=100,
            average_price=150.50,
            status=ExecutionStatus.FILLED,
            broker="IBKR",
            commission=15.05,
            execution_time=datetime.now(),
            fills=[{"quantity": 100, "price": 150.50}],
            error_message=None
        )
        
        assert report.execution_id == "exec_001"
        assert report.request_id == "req_001"
        assert report.symbol == "AAPL"
        assert report.status == ExecutionStatus.FILLED
        assert report.executed_quantity == 100
        assert report.average_price == 150.50
        assert report.broker == "IBKR"
        assert report.commission == 15.05
        assert len(report.fills) == 1
        assert report.error_message is None
    
    def test_execution_engine_config_defaults(self):
        """Test ExecutionEngineConfig default values"""
        config = ExecutionEngineConfig()
        
        assert config.default_broker == "IBKR"
        assert config.max_retry_attempts == 3
        assert config.execution_timeout == 300
        assert config.enable_smart_routing is True
        assert config.enable_dark_pools is True
        assert config.min_fill_size == 1.0
        assert config.max_order_size == 10000.0
        assert config.commission_rate == 0.001
    
    def test_execution_engine_config_custom(self):
        """Test ExecutionEngineConfig with custom values"""
        config = ExecutionEngineConfig(
            default_broker="Alpaca",
            max_retry_attempts=5,
            execution_timeout=600,
            enable_smart_routing=False,
            commission_rate=0.002
        )
        
        assert config.default_broker == "Alpaca"
        assert config.max_retry_attempts == 5
        assert config.execution_timeout == 600
        assert config.enable_smart_routing is False
        assert config.commission_rate == 0.002


class TestExecutionEngineLifecycle:
    """Test execution engine lifecycle methods"""
    
    @pytest.fixture
    def engine_config(self):
        """Create test engine config"""
        return {
            'default_broker': 'IBKR',
            'max_retry_attempts': 3,
            'execution_timeout': 300
        }
    
    @pytest.fixture
    def engine(self, engine_config):
        """Create test execution engine"""
        return ExecutionEngine(engine_config)
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.config.default_broker == 'IBKR'
        assert engine.active_executions == {}
        assert engine.execution_reports == {}
        assert engine.pending_orders == {}
        assert engine.broker_connections == {}
        assert engine.subscribers == []
        assert engine.is_initialized is False
        assert engine.is_running is False
        assert engine.monitoring_task is None
    
    @pytest.mark.asyncio
    async def test_engine_initialize_method(self, engine):
        """Test engine initialize() method"""
        with patch.object(engine, '_initialize_broker_connections', new_callable=AsyncMock) as mock_init:
            result = await engine.initialize()
            
            assert result is True
            assert engine.is_initialized is True
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_engine_start_method(self, engine):
        """Test engine start() method"""
        # Initialize first
        await engine.initialize()
        
        # Start engine
        with patch.object(engine, '_run_execution_monitoring', new_callable=AsyncMock):
            result = await engine.start()
            
            assert result is True
            assert engine.is_running is True
            assert engine.monitoring_task is not None
    
    @pytest.mark.asyncio
    async def test_engine_start_without_initialization(self, engine):
        """Test engine start() without initialization fails"""
        with pytest.raises(RuntimeError, match="not initialized"):
            await engine.start()
    
    @pytest.mark.asyncio
    async def test_engine_stop_method(self, engine):
        """Test engine stop() method"""
        # Initialize and start
        await engine.initialize()
        await engine.start()
        
        # Stop engine
        with patch.object(engine, '_cancel_all_active_orders', new_callable=AsyncMock):
            result = await engine.stop()
            
            assert result is True
            assert engine.is_running is False


class TestComponentIntegration:
    """Test component integration methods"""
    
    @pytest.fixture
    def engine(self):
        """Create test execution engine"""
        return ExecutionEngine({})
    
    def test_set_risk_manager(self, engine):
        """Test setting risk manager reference"""
        mock_risk_manager = Mock()
        engine.set_risk_manager(mock_risk_manager)
        
        assert engine.risk_manager == mock_risk_manager
    
    def test_set_trading_engine(self, engine):
        """Test setting trading engine reference"""
        mock_trading_engine = Mock()
        engine.set_trading_engine(mock_trading_engine)
        
        assert engine.trading_engine == mock_trading_engine
    
    def test_set_broker_manager(self, engine):
        """Test setting broker manager reference"""
        mock_broker_manager = Mock()
        engine.set_broker_manager(mock_broker_manager)
        
        assert engine.broker_manager == mock_broker_manager
    
    def test_subscribe_to_events(self, engine):
        """Test subscribing to execution events"""
        mock_subscriber = Mock(spec=IExecutionSubscriber)
        engine.subscribe(mock_subscriber)
        
        assert len(engine.subscribers) == 1
        assert engine.subscribers[0] == mock_subscriber
    
    def test_multiple_subscribers(self, engine):
        """Test multiple subscribers"""
        subscriber1 = Mock(spec=IExecutionSubscriber)
        subscriber2 = Mock(spec=IExecutionSubscriber)
        
        engine.subscribe(subscriber1)
        engine.subscribe(subscriber2)
        
        assert len(engine.subscribers) == 2


class TestOrderExecution:
    """Test order execution methods"""
    
    @pytest.fixture
    def engine(self):
        """Create and initialize test execution engine"""
        engine = ExecutionEngine({'default_broker': 'IBKR'})
        return engine
    
    @pytest.fixture
    def execution_request(self):
        """Create test execution request"""
        return ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="valid_token"
        )
    
    @pytest.mark.asyncio
    async def test_execute_order_successful(self, engine, execution_request):
        """Test successful order execution"""
        # Mock authorization and execution
        with patch.object(engine, '_validate_authorization', return_value=True), \
             patch.object(engine, '_determine_broker', return_value='IBKR'), \
             patch.object(engine, '_execute_through_broker', return_value={
                 'status': 'filled',
                 'executed_quantity': 100,
                 'average_price': 150.0,
                 'commission': 15.0,
                 'fills': [{'quantity': 100, 'price': 150.0}],
                 'error_message': None
             }):
            
            report = await engine.execute_order(execution_request)
            
            assert report.status == ExecutionStatus.FILLED
            assert report.executed_quantity == 100
            assert report.average_price == 150.0
            assert report.symbol == "AAPL"
            assert report.broker == "IBKR"
    
    @pytest.mark.asyncio
    async def test_execute_order_invalid_authorization(self, engine, execution_request):
        """Test order execution with invalid authorization"""
        with patch.object(engine, '_validate_authorization', return_value=False):
            report = await engine.execute_order(execution_request)
            
            assert report.status == ExecutionStatus.FAILED
            assert report.executed_quantity == 0
            assert "Invalid authorization" in report.error_message
    
    @pytest.mark.asyncio
    async def test_execute_order_broker_failure(self, engine, execution_request):
        """Test order execution with broker failure"""
        with patch.object(engine, '_validate_authorization', return_value=True), \
             patch.object(engine, '_determine_broker', return_value='IBKR'), \
             patch.object(engine, '_execute_through_broker', side_effect=Exception("Broker error")):
            
            report = await engine.execute_order(execution_request)
            
            assert report.status == ExecutionStatus.FAILED
            assert "Broker error" in report.error_message
    
    @pytest.mark.asyncio
    async def test_cancel_order_successful(self, engine):
        """Test successful order cancellation"""
        # Add active execution
        execution_id = "exec_001"
        engine.active_executions[execution_id] = Mock()
        
        # Add pending order
        order = Mock()
        order.order_id = execution_id
        engine.pending_orders[execution_id] = order
        
        # Mock advanced order manager
        engine.advanced_order_manager = Mock()
        engine.advanced_order_manager.cancel_order = AsyncMock(return_value=True)
        
        result = await engine.cancel_order(execution_id)
        
        assert result is True
        assert execution_id not in engine.pending_orders
    
    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, engine):
        """Test cancelling non-existent order"""
        result = await engine.cancel_order("non_existent_id")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, engine):
        """Test getting execution status"""
        # Add execution report
        execution_id = "exec_001"
        report = ExecutionReport(
            execution_id=execution_id,
            request_id="req_001",
            symbol="AAPL",
            side="BUY",
            requested_quantity=100,
            executed_quantity=100,
            average_price=150.0,
            status=ExecutionStatus.FILLED,
            broker="IBKR",
            commission=15.0,
            execution_time=datetime.now()
        )
        engine.execution_reports[execution_id] = report
        
        result = await engine.get_execution_status(execution_id)
        
        assert result == report
        assert result.execution_id == execution_id
    
    @pytest.mark.asyncio
    async def test_get_active_executions(self, engine):
        """Test getting active executions"""
        # Add active executions
        request1 = Mock()
        request2 = Mock()
        engine.active_executions["exec_001"] = request1
        engine.active_executions["exec_002"] = request2
        
        result = await engine.get_active_executions()
        
        assert len(result) == 2
        assert request1 in result
        assert request2 in result


class TestAuthorizationAndRouting:
    """Test authorization validation and broker routing"""
    
    @pytest.fixture
    def engine(self):
        """Create test execution engine"""
        return ExecutionEngine({'enable_smart_routing': True})
    
    @pytest.fixture
    def execution_request(self):
        """Create test execution request"""
        return ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="test_token"
        )
    
    @pytest.mark.asyncio
    async def test_validate_authorization_with_risk_manager(self, engine, execution_request):
        """Test authorization validation with risk manager"""
        mock_risk_manager = Mock()
        mock_risk_manager.validate_execution = AsyncMock(return_value=True)
        engine.set_risk_manager(mock_risk_manager)
        
        result = await engine._validate_authorization("valid_token", execution_request)
        
        assert result is True
        mock_risk_manager.validate_execution.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_authorization_without_risk_manager(self, engine, execution_request):
        """Test authorization validation without risk manager"""
        result = await engine._validate_authorization("any_token", execution_request)
        
        # Should return True as fallback
        assert result is True
    
    @pytest.mark.asyncio
    async def test_determine_broker_with_preference(self, engine, execution_request):
        """Test broker determination with preference"""
        execution_request.broker_preference = "Alpaca"
        
        broker = await engine._determine_broker(execution_request)
        
        assert broker == "Alpaca"
    
    @pytest.mark.asyncio
    async def test_determine_broker_smart_routing_large_order(self, engine, execution_request):
        """Test smart routing for large orders"""
        execution_request.quantity = 6000  # Large order
        execution_request.broker_preference = None
        
        broker = await engine._determine_broker(execution_request)
        
        assert broker == "IBKR"
    
    @pytest.mark.asyncio
    async def test_determine_broker_smart_routing_small_order(self, engine, execution_request):
        """Test smart routing for small orders"""
        execution_request.quantity = 100  # Small order
        execution_request.broker_preference = None
        
        broker = await engine._determine_broker(execution_request)
        
        assert broker == "Alpaca"
    
    @pytest.mark.asyncio
    async def test_determine_broker_default(self, engine, execution_request):
        """Test default broker selection"""
        engine.config.enable_smart_routing = False
        execution_request.broker_preference = None
        
        broker = await engine._determine_broker(execution_request)
        
        assert broker == engine.config.default_broker


class TestExecutionMethods:
    """Test execution implementation methods"""
    
    @pytest.fixture
    def engine(self):
        """Create test execution engine"""
        return ExecutionEngine({})
    
    @pytest.fixture
    def order(self):
        """Create test order"""
        return Order(
            order_id="order_001",
            symbol="AAPL",
            quantity=100,
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            price=150.0
        )
    
    @pytest.mark.asyncio
    async def test_mock_execution(self, engine, order):
        """Test mock execution"""
        result = await engine._mock_execution(order)
        
        assert result['status'] == 'filled'
        assert result['executed_quantity'] == 100
        assert result['average_price'] == 150.0
        assert result['commission'] > 0
        assert len(result['fills']) == 1
        assert result['error_message'] is None
    
    @pytest.mark.asyncio
    async def test_check_order_status(self, engine, order):
        """Test checking order status"""
        result = await engine._check_order_status(order)
        
        # Mock implementation always returns False
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_fill(self, engine, order):
        """Test processing order fill"""
        mock_subscriber = Mock(spec=IExecutionSubscriber)
        mock_subscriber.on_fill_received = AsyncMock()
        engine.subscribe(mock_subscriber)
        
        await engine._process_fill(order)
        
        mock_subscriber.on_fill_received.assert_called_once()
    
    def test_create_error_report(self, engine):
        """Test creating error report"""
        request = ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="test_token"
        )
        
        report = engine._create_error_report(request, "Test error")
        
        assert report.status == ExecutionStatus.FAILED
        assert report.executed_quantity == 0
        assert report.error_message == "Test error"
        assert report.symbol == "AAPL"


class TestStatusAndMonitoring:
    """Test status and monitoring methods"""
    
    @pytest.fixture
    def engine(self):
        """Create test execution engine"""
        return ExecutionEngine({})
    
    def test_get_execution_status_summary_initial(self, engine):
        """Test getting execution status summary initially"""
        summary = engine.get_execution_status_summary()
        
        assert summary['initialized'] is False
        assert summary['running'] is False
        assert summary['active_executions'] == 0
        assert summary['total_executions'] == 0
        assert summary['pending_orders'] == 0
        assert summary['successful_executions'] == 0
        assert summary['failed_executions'] == 0
    
    @pytest.mark.asyncio
    async def test_get_execution_status_summary_after_initialization(self, engine):
        """Test getting execution status summary after initialization"""
        await engine.initialize()
        
        summary = engine.get_execution_status_summary()
        
        assert summary['initialized'] is True
        assert summary['running'] is False
    
    def test_get_execution_status_summary_with_executions(self, engine):
        """Test execution status summary with executions"""
        # Add some execution reports
        report1 = ExecutionReport(
            execution_id="exec_001",
            request_id="req_001",
            symbol="AAPL",
            side="BUY",
            requested_quantity=100,
            executed_quantity=100,
            average_price=150.0,
            status=ExecutionStatus.FILLED,
            broker="IBKR",
            commission=15.0,
            execution_time=datetime.now()
        )
        
        report2 = ExecutionReport(
            execution_id="exec_002",
            request_id="req_002",
            symbol="TSLA",
            side="SELL",
            requested_quantity=50,
            executed_quantity=0,
            average_price=0,
            status=ExecutionStatus.FAILED,
            broker="IBKR",
            commission=0,
            execution_time=datetime.now(),
            error_message="Test error"
        )
        
        engine.execution_reports["exec_001"] = report1
        engine.execution_reports["exec_002"] = report2
        
        summary = engine.get_execution_status_summary()
        
        assert summary['total_executions'] == 2
        assert summary['successful_executions'] == 1
        assert summary['failed_executions'] == 1
    
    def test_component_links_in_summary(self, engine):
        """Test component links in status summary"""
        mock_risk_manager = Mock()
        mock_trading_engine = Mock()
        
        engine.set_risk_manager(mock_risk_manager)
        engine.set_trading_engine(mock_trading_engine)
        
        summary = engine.get_execution_status_summary()
        
        assert summary['components_linked']['risk_manager'] is True
        assert summary['components_linked']['trading_engine'] is True
        assert summary['components_linked']['broker_manager'] is False


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def engine(self):
        """Create test execution engine"""
        return ExecutionEngine({})
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, engine):
        """Test initialization failure"""
        with patch.object(engine, '_initialize_broker_connections', 
                         side_effect=Exception("Init error")):
            with pytest.raises(Exception, match="Init error"):
                await engine.initialize()
    
    @pytest.mark.asyncio
    async def test_start_failure(self, engine):
        """Test start failure"""
        await engine.initialize()
        
        with patch('asyncio.create_task', side_effect=Exception("Start error")):
            with pytest.raises(Exception, match="Start error"):
                await engine.start()
    
    @pytest.mark.asyncio
    async def test_cancel_order_exception(self, engine):
        """Test cancel order exception handling"""
        execution_id = "exec_001"
        engine.active_executions[execution_id] = Mock()
        
        with patch.object(engine, 'advanced_order_manager', None):
            result = await engine.cancel_order(execution_id)
            
            # Should handle gracefully
            assert result is False


class TestIntegration:
    """Test integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_execution_lifecycle(self):
        """Test full execution lifecycle"""
        # Create engine
        engine = ExecutionEngine({'default_broker': 'IBKR'})
        
        # Initialize
        await engine.initialize()
        assert engine.is_initialized is True
        
        # Create request
        request = ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="valid_token"
        )
        
        # Execute order
        with patch.object(engine, '_validate_authorization', return_value=True), \
             patch.object(engine, '_execute_through_broker', return_value={
                 'status': 'filled',
                 'executed_quantity': 100,
                 'average_price': 150.0,
                 'commission': 15.0,
                 'fills': [{'quantity': 100, 'price': 150.0}],
                 'error_message': None
             }):
            
            report = await engine.execute_order(request)
            
            assert report.status == ExecutionStatus.FILLED
            assert len(engine.execution_reports) == 1
        
        # Get status
        status = await engine.get_execution_status(report.execution_id)
        assert status == report
        
        # Get summary
        summary = engine.get_execution_status_summary()
        assert summary['total_executions'] == 1
        assert summary['successful_executions'] == 1
    
    @pytest.mark.asyncio
    async def test_subscriber_notifications(self):
        """Test subscriber notifications"""
        engine = ExecutionEngine({})
        
        # Create mock subscriber
        mock_subscriber = Mock(spec=IExecutionSubscriber)
        mock_subscriber.on_execution_update = AsyncMock()
        engine.subscribe(mock_subscriber)
        
        # Create request and execute
        request = ExecutionRequest(
            request_id="req_001",
            plan_id="plan_001",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0,
            time_in_force="DAY",
            priority=ExecutionPriority.NORMAL,
            auth_token="valid_token"
        )
        
        with patch.object(engine, '_validate_authorization', return_value=True), \
             patch.object(engine, '_execute_through_broker', return_value={
                 'status': 'filled',
                 'executed_quantity': 100,
                 'average_price': 150.0,
                 'commission': 15.0,
                 'fills': [],
                 'error_message': None
             }):
            
            await engine.execute_order(request)
            
            # Verify subscriber was notified
            mock_subscriber.on_execution_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
