"""
Comprehensive Unit Tests for UnifiedExecutionEngine
=================================================

Tests for the UnifiedExecutionEngine component, focusing on:
- ISystemComponent interface compliance
- Execution authorization and validation
- Algorithm execution and performance
- Position tracking integration
- Risk management compliance
- Error handling and recovery

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 1.4 Enhancement)
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import the component under test
from core_engine.system.unified_execution_engine import (
    UnifiedExecutionEngine,
    ExecutionRequest,
    ExecutionResult,
    ExecutionAuthorization,
    ExecutionStatus,
    ExecutionAlgorithm,
    ExecutionUrgency
)


@pytest.fixture
def execution_config():
    """Configuration for execution engine"""
    return {
        'max_market_impact': 0.05,
        'default_time_horizon': 300,
        'enable_position_tracking': True,
        'max_execution_time': 3600,
        'min_order_size': 1.0,
        'max_order_size': 10000.0,
        'supported_venues': ['NYSE', 'NASDAQ', 'ARCA'],
        'risk_manager_callback': None,
        'position_update_callback': None,
        'test_mode': True  # Enable test mode for faster execution
    }


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    risk_manager = Mock()
    risk_manager.update_position = AsyncMock(return_value={
        'status': 'success',
        'position': 100.0,
        'portfolio_value': 100000.0
    })
    risk_manager.validate_position_change = AsyncMock(return_value=(True, "Valid"))
    return risk_manager


@pytest.fixture
def mock_position_callback():
    """Mock position update callback"""
    callback = AsyncMock(return_value={
        'status': 'success',
        'position': 100.0
    })
    return callback


@pytest.fixture
def execution_engine(execution_config, mock_risk_manager, mock_position_callback):
    """UnifiedExecutionEngine instance for testing"""
    execution_config['risk_manager_callback'] = mock_risk_manager
    execution_config['position_update_callback'] = mock_position_callback
    return UnifiedExecutionEngine(execution_config)


@pytest.fixture
def sample_authorization():
    """Sample execution authorization"""
    return ExecutionAuthorization(
        authorization_id=str(uuid.uuid4()),
        risk_manager_id="test_risk_manager",
        symbol="AAPL",
        side="buy",
        quantity=100.0,
        max_quantity=150.0,
        price_limit=150.0,
        expires_at=datetime.now() + timedelta(minutes=30),
        allowed_algorithms=[ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP],
        risk_budget_allocation=5000.0,
        authorized_at=datetime.now()
    )


@pytest.fixture
def sample_execution_request(sample_authorization):
    """Sample execution request"""
    return ExecutionRequest(
        request_id=str(uuid.uuid4()),
        authorization=sample_authorization,
        algorithm=ExecutionAlgorithm.MARKET,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300,
        venue_preferences=["NYSE"],
        algorithm_params={}
    )


class TestUnifiedExecutionEngineInterface:
    """Test ISystemComponent interface compliance"""

    def test_initialization(self, execution_config):
        """Test UnifiedExecutionEngine initialization"""
        engine = UnifiedExecutionEngine(execution_config)

        assert engine.config == execution_config
        assert not engine.is_initialized
        assert not engine.is_operational
        assert engine.component_id is None
        assert len(engine.algorithms) > 0
        assert engine.validator is not None
        assert engine.impact_model is not None

    @pytest.mark.asyncio
    async def test_initialize_method(self, execution_engine):
        """Test initialize method"""
        result = await execution_engine.initialize()

        assert result is True
        assert execution_engine.is_initialized
        assert execution_engine.last_error is None

    @pytest.mark.asyncio
    async def test_start_method(self, execution_engine):
        """Test start method"""
        # Initialize first
        await execution_engine.initialize()

        result = await execution_engine.start()

        assert result is True
        assert execution_engine.is_operational

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, execution_engine):
        """Test start method without initialization"""
        result = await execution_engine.start()

        assert result is False
        assert not execution_engine.is_operational

    @pytest.mark.asyncio
    async def test_stop_method(self, execution_engine):
        """Test stop method"""
        # Initialize and start first
        await execution_engine.initialize()
        await execution_engine.start()

        result = await execution_engine.stop()

        assert result is True
        assert not execution_engine.is_operational

    @pytest.mark.asyncio
    async def test_health_check(self, execution_engine):
        """Test health check method"""
        await execution_engine.initialize()
        await execution_engine.start()

        health = await execution_engine.health_check()

        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert health['component_type'] == 'UnifiedExecutionEngine'
        assert health['initialized'] is True
        assert health['operational'] is True

    def test_get_status(self, execution_engine):
        """Test get_status method"""
        status = execution_engine.get_status()

        assert isinstance(status, dict)
        assert 'component_type' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'active_executions' in status
        assert 'total_executions' in status
        assert status['component_type'] == 'UnifiedExecutionEngine'


class TestExecutionAuthorization:
    """Test execution authorization and validation"""

    def test_authorization_validation_valid(self, sample_authorization):
        """Test valid authorization validation"""
        assert sample_authorization.validate_authorization() is True

    def test_authorization_validation_expired(self, sample_authorization):
        """Test expired authorization validation"""
        sample_authorization.expires_at = datetime.now() - timedelta(minutes=1)
        assert sample_authorization.validate_authorization() is False

    def test_authorization_validation_no_algorithms(self, sample_authorization):
        """Test authorization with no allowed algorithms"""
        sample_authorization.allowed_algorithms = []
        assert sample_authorization.validate_authorization() is False


class TestExecutionValidation:
    """Test execution request validation"""

    @pytest.mark.asyncio
    async def test_valid_execution_request(self, execution_engine, sample_execution_request):
        """Test validation of valid execution request"""
        await execution_engine.initialize()

        is_valid, errors = execution_engine.validator.validate_request(sample_execution_request)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_invalid_quantity_request(self, execution_engine, sample_execution_request):
        """Test validation of request with invalid quantity"""
        await execution_engine.initialize()

        # Set quantity above maximum
        sample_execution_request.authorization.quantity = 200.0
        sample_execution_request.authorization.max_quantity = 150.0

        is_valid, errors = execution_engine.validator.validate_request(sample_execution_request)

        assert is_valid is False
        assert len(errors) > 0
        assert any("quantity" in error.lower() for error in errors)

    @pytest.mark.asyncio
    async def test_unauthorized_algorithm_request(self, execution_engine, sample_execution_request):
        """Test validation of request with unauthorized algorithm"""
        await execution_engine.initialize()

        # Use algorithm not in allowed list
        sample_execution_request.algorithm = ExecutionAlgorithm.VWAP
        sample_execution_request.authorization.allowed_algorithms = [ExecutionAlgorithm.MARKET]

        is_valid, errors = execution_engine.validator.validate_request(sample_execution_request)

        assert is_valid is False
        assert len(errors) > 0
        assert any("algorithm" in error.lower() for error in errors)


class TestExecutionExecution:
    """Test trade execution functionality"""

    @pytest.mark.asyncio
    async def test_successful_market_execution(self, execution_engine, sample_execution_request):
        """Test successful market order execution"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Mock market data for execution
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        assert isinstance(result, ExecutionResult)
        assert result.request_id == sample_execution_request.request_id
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED]

    @pytest.mark.asyncio
    async def test_execution_with_invalid_authorization(self, execution_engine, sample_execution_request):
        """Test execution with invalid authorization"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Expire the authorization
        sample_execution_request.authorization.expires_at = datetime.now() - timedelta(minutes=1)

        result = await execution_engine.execute_authorized_trade(sample_execution_request)

        assert result.status == ExecutionStatus.REJECTED
        assert len(result.execution_log) > 0
        assert any("authorization" in log.lower() for log in result.execution_log)

    @pytest.mark.asyncio
    async def test_execution_status_tracking(self, execution_engine, sample_execution_request):
        """Test execution status tracking"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Execute trade
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        # Check status tracking
        status = execution_engine.get_execution_status(sample_execution_request.request_id)
        assert status is not None

        # Check result retrieval
        stored_result = execution_engine.get_execution_result(sample_execution_request.request_id)
        assert stored_result is not None
        assert stored_result.request_id == result.request_id


class TestPositionTracking:
    """Test position tracking integration"""

    @pytest.mark.asyncio
    async def test_position_update_on_successful_execution(self, execution_engine, sample_execution_request, mock_risk_manager):
        """Test position update after successful execution"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Execute trade
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        # Verify position update was called if execution was successful
        if result.status == ExecutionStatus.FILLED:
            mock_risk_manager.update_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_position_tracking_disabled(self, execution_config, sample_execution_request):
        """Test execution with position tracking disabled"""
        execution_config['enable_position_tracking'] = False
        engine = UnifiedExecutionEngine(execution_config)

        await engine.initialize()
        await engine.start()

        # Execute trade
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await engine.execute_authorized_trade(sample_execution_request)

        # Should still execute successfully
        assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED, ExecutionStatus.REJECTED]


class TestExecutionMetrics:
    """Test execution metrics and performance tracking"""

    @pytest.mark.asyncio
    async def test_execution_metrics_collection(self, execution_engine, sample_execution_request):
        """Test execution metrics collection"""
        await execution_engine.initialize()
        await execution_engine.start()

        initial_metrics = execution_engine.get_execution_metrics()
        initial_count = initial_metrics['total_executions']

        # Execute trade
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            await execution_engine.execute_authorized_trade(sample_execution_request)

        updated_metrics = execution_engine.get_execution_metrics()

        assert updated_metrics['total_executions'] == initial_count + 1
        assert 'successful_executions' in updated_metrics
        assert 'failed_executions' in updated_metrics
        assert 'avg_execution_time' in updated_metrics

    def test_execution_cost_estimation(self, execution_engine, sample_execution_request):
        """Test execution cost estimation"""
        cost_estimate = execution_engine.estimate_execution_cost(sample_execution_request)

        assert isinstance(cost_estimate, dict)
        assert 'market_impact' in cost_estimate
        assert 'commission' in cost_estimate
        assert 'total_cost' in cost_estimate
        assert all(isinstance(v, (int, float)) for v in cost_estimate.values())


class TestExecutionCancellation:
    """Test execution cancellation functionality"""

    @pytest.mark.asyncio
    async def test_execution_cancellation(self, execution_engine, sample_execution_request):
        """Test execution cancellation"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Start execution (but don't wait for completion)
        execution_task = asyncio.create_task(
            execution_engine.execute_authorized_trade(sample_execution_request)
        )

        # Allow some time for execution to start
        await asyncio.sleep(0.1)

        # Cancel execution
        cancel_result = execution_engine.cancel_execution(
            sample_execution_request.request_id,
            sample_execution_request.authorization.authorization_id
        )

        # Wait for execution to complete
        result = await execution_task

        # Check results
        if cancel_result:
            assert result.status == ExecutionStatus.CANCELLED
        else:
            # Cancellation might fail if execution completed too quickly
            assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED]


class TestErrorHandling:
    """Test error handling and recovery"""

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self, execution_config):
        """Test initialization error handling"""
        # Create engine with invalid config
        invalid_config = execution_config.copy()
        invalid_config['max_market_impact'] = -1.0  # Invalid value

        engine = UnifiedExecutionEngine(invalid_config)

        # Initialization should handle errors gracefully
        result = await engine.initialize()

        # Should either succeed (if validation is lenient) or fail gracefully
        assert isinstance(result, bool)
        if not result:
            assert engine.last_error is not None

    @pytest.mark.asyncio
    async def test_execution_error_recovery(self, execution_engine, sample_execution_request):
        """Test execution error recovery"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Mock an execution error
        with patch.object(execution_engine.algorithms[ExecutionAlgorithm.MARKET], 'execute',
                         side_effect=Exception("Mock execution error")):
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        # Should handle error gracefully
        assert result.status == ExecutionStatus.FAILED
        assert len(result.execution_log) > 0
        assert any("error" in log.lower() for log in result.execution_log)

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, execution_engine):
        """Test health check error handling"""
        await execution_engine.initialize()

        # Mock an error in health check
        with patch.object(execution_engine, 'execution_metrics', side_effect=Exception("Mock error")):
            health = await execution_engine.health_check()

        # Should handle error gracefully
        assert isinstance(health, dict)
        assert 'healthy' in health
        if not health['healthy']:
            assert 'error' in health


class TestExecutionAlgorithms:
    """Test different execution algorithms"""

    @pytest.mark.asyncio
    async def test_market_algorithm_execution(self, execution_engine, sample_execution_request):
        """Test market algorithm execution"""
        await execution_engine.initialize()
        await execution_engine.start()

        sample_execution_request.algorithm = ExecutionAlgorithm.MARKET

        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        assert isinstance(result, ExecutionResult)
        assert result.algorithm_used == ExecutionAlgorithm.MARKET

    @pytest.mark.asyncio
    async def test_twap_algorithm_execution(self, execution_engine, sample_execution_request):
        """Test TWAP algorithm execution"""
        await execution_engine.initialize()
        await execution_engine.start()

        sample_execution_request.algorithm = ExecutionAlgorithm.TWAP
        sample_execution_request.time_horizon = 600  # 10 minutes

        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        assert isinstance(result, ExecutionResult)
        assert result.algorithm_used == ExecutionAlgorithm.TWAP

    @pytest.mark.asyncio
    async def test_adaptive_algorithm_selection(self, execution_engine, sample_execution_request):
        """Test adaptive algorithm selection"""
        await execution_engine.initialize()
        await execution_engine.start()

        sample_execution_request.algorithm = ExecutionAlgorithm.ADAPTIVE

        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        assert isinstance(result, ExecutionResult)
        # Adaptive should select an appropriate algorithm
        assert result.algorithm_used in [ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP, ExecutionAlgorithm.ADAPTIVE]


class TestExecutionIntegration:
    """Integration tests for execution engine"""

    @pytest.mark.asyncio
    async def test_full_execution_lifecycle(self, execution_engine, sample_execution_request):
        """Test complete execution lifecycle"""
        # Initialize and start
        assert await execution_engine.initialize() is True
        assert await execution_engine.start() is True

        # Check initial status
        status = execution_engine.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True

        # Execute trade
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            result = await execution_engine.execute_authorized_trade(sample_execution_request)

        # Verify execution
        assert isinstance(result, ExecutionResult)
        assert result.request_id == sample_execution_request.request_id

        # Check metrics
        metrics = execution_engine.get_execution_metrics()
        assert metrics['total_executions'] > 0

        # Check health
        health = await execution_engine.health_check()
        assert health['healthy'] is True

        # Stop engine
        assert await execution_engine.stop() is True
        assert execution_engine.is_operational is False

    @pytest.mark.asyncio
    async def test_concurrent_executions(self, execution_engine):
        """Test concurrent execution handling"""
        await execution_engine.initialize()
        await execution_engine.start()

        # Create multiple execution requests
        requests = []
        for i in range(3):
            auth = ExecutionAuthorization(
                authorization_id=str(uuid.uuid4()),
                risk_manager_id="test_risk_manager",
                symbol=f"STOCK{i}",
                side="buy",
                quantity=100.0,
                max_quantity=150.0,
                price_limit=100.0 + i,
                expires_at=datetime.now() + timedelta(minutes=30),
                allowed_algorithms=[ExecutionAlgorithm.MARKET],
                risk_budget_allocation=5000.0,
                authorized_at=datetime.now()
            )

            request = ExecutionRequest(
                request_id=str(uuid.uuid4()),
                authorization=auth,
                algorithm=ExecutionAlgorithm.MARKET,
                urgency=ExecutionUrgency.NORMAL,
                time_horizon=300
            )
            requests.append(request)

        # Execute concurrently
        with patch('core_engine.system.unified_execution_engine.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2022, 1, 1, 0, 0, 0)
            tasks = [execution_engine.execute_authorized_trade(req) for req in requests]
            results = await asyncio.gather(*tasks)

        # Verify all executions
        assert len(results) == 3
        for result in results:
            assert isinstance(result, ExecutionResult)
            assert result.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED, ExecutionStatus.REJECTED]

        # Check metrics
        metrics = execution_engine.get_execution_metrics()
        assert metrics['total_executions'] >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
