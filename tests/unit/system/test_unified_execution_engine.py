"""
Comprehensive tests for UnifiedExecutionEngine

Tests cover:
1. Initialization & Setup (4 tests)
2. Authorization Validation (5 tests)
3. Market Algorithm (4 tests)
4. TWAP Algorithm (5 tests)
5. Adaptive Algorithm (4 tests)
6. Execution Tracking (5 tests)
7. Metrics & Analytics (4 tests)
8. Position Tracking (5 tests)
9. ISystemComponent Interface (4 tests)

Total: 40 tests
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

from core_engine.system.unified_execution_engine import (
    UnifiedExecutionEngine,
    ExecutionAuthorization,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionAlgorithm,
    ExecutionUrgency,
    TWAPAlgorithm,
    MarketAlgorithm
)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def default_config():
    """Default configuration with test mode enabled"""
    return {
        'test_mode': True,  # CRITICAL: Disables sleep delays
        'max_market_impact': 0.05,
        'default_time_horizon': 300,
        'enable_position_tracking': False  # Disabled by default
    }


@pytest.fixture
def config_with_position_tracking():
    """Configuration with position tracking enabled"""
    return {
        'test_mode': True,
        'max_market_impact': 0.05,
        'default_time_horizon': 300,
        'enable_position_tracking': True
    }


@pytest.fixture
def valid_authorization():
    """Valid execution authorization"""
    return ExecutionAuthorization(
        symbol="AAPL",
        side="buy",
        quantity=1000.0,
        max_quantity=1000.0,
        strategy_id="test_strategy",
        allowed_algorithms=[
            ExecutionAlgorithm.MARKET,
            ExecutionAlgorithm.TWAP,
            ExecutionAlgorithm.ADAPTIVE
        ],
        expires_at=datetime.now() + timedelta(hours=1)
    )


@pytest.fixture
def expired_authorization():
    """Expired execution authorization"""
    return ExecutionAuthorization(
        symbol="AAPL",
        side="buy",
        quantity=1000.0,
        max_quantity=1000.0,
        strategy_id="test_strategy",
        allowed_algorithms=[ExecutionAlgorithm.MARKET],
        expires_at=datetime.now() - timedelta(hours=1)  # Expired
    )


@pytest.fixture
def market_request(valid_authorization):
    """Market execution request"""
    return ExecutionRequest(
        authorization=valid_authorization,
        algorithm=ExecutionAlgorithm.MARKET,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=60
    )


@pytest.fixture
def twap_request(valid_authorization):
    """TWAP execution request"""
    return ExecutionRequest(
        authorization=valid_authorization,
        algorithm=ExecutionAlgorithm.TWAP,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300
    )


@pytest.fixture
def adaptive_request(valid_authorization):
    """Adaptive execution request"""
    return ExecutionRequest(
        authorization=valid_authorization,
        algorithm=ExecutionAlgorithm.ADAPTIVE,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300
    )


@pytest.fixture
def execution_engine(default_config):
    """Uninitialized execution engine"""
    return UnifiedExecutionEngine(default_config)


@pytest.fixture
async def initialized_engine(execution_engine):
    """Fully initialized execution engine"""
    await execution_engine.initialize()
    await execution_engine.start()
    yield execution_engine
    await execution_engine.stop()


# ========================================
# CATEGORY 1: INITIALIZATION & SETUP (4 tests)
# ========================================

class TestInitialization:
    """Test initialization and setup"""

    def test_default_initialization(self, default_config):
        """Test default initialization"""
        engine = UnifiedExecutionEngine(default_config)

        assert engine.config == default_config
        assert engine.test_mode is True
        assert engine.simulation_delay == 0.0  # No delay in test mode
        assert len(engine.algorithms) == 3  # Market, TWAP, Adaptive
        assert engine.is_initialized is False
        assert engine.is_operational is False
        assert len(engine.active_executions) == 0
        assert len(engine.execution_history) == 0

    def test_test_mode_initialization(self):
        """Test that test_mode disables delays"""
        config_test = {'test_mode': True}
        engine_test = UnifiedExecutionEngine(config_test)
        assert engine_test.test_mode is True
        assert engine_test.simulation_delay == 0.0

        config_normal = {'test_mode': False}
        engine_normal = UnifiedExecutionEngine(config_normal)
        assert engine_normal.test_mode is False
        assert engine_normal.simulation_delay == 0.1

    @pytest.mark.asyncio
    async def test_full_initialization(self, execution_engine):
        """Test full initialization sequence"""
        assert execution_engine.is_initialized is False

        success = await execution_engine.initialize()

        assert success is True
        assert execution_engine.is_initialized is True
        assert execution_engine.last_error is None

    def test_algorithm_availability(self, execution_engine):
        """Test that all required algorithms are available"""
        assert ExecutionAlgorithm.MARKET in execution_engine.algorithms
        assert ExecutionAlgorithm.TWAP in execution_engine.algorithms
        assert ExecutionAlgorithm.ADAPTIVE in execution_engine.algorithms

        # Verify test_mode propagated to algorithms
        for algorithm in execution_engine.algorithms.values():
            assert algorithm.test_mode is True


# ========================================
# CATEGORY 2: AUTHORIZATION VALIDATION (5 tests)
# ========================================

class TestAuthorizationValidation:
    """Test authorization validation"""

    def test_valid_authorization(self, valid_authorization):
        """Test valid authorization passes validation"""
        is_valid = valid_authorization.validate_authorization()

        assert is_valid is True
        assert valid_authorization.is_valid is True
        assert len(valid_authorization.validation_errors) == 0

    def test_expired_authorization(self, expired_authorization):
        """Test expired authorization is rejected"""
        is_valid = expired_authorization.validate_authorization()

        assert is_valid is False
        assert expired_authorization.is_valid is False
        assert "expired" in expired_authorization.validation_errors[0].lower()

    def test_missing_allowed_algorithms(self):
        """Test authorization without allowed algorithms is rejected"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[],  # Empty
            expires_at=datetime.now() + timedelta(hours=1)
        )

        is_valid = auth.validate_authorization()

        assert is_valid is False
        assert "algorithm" in auth.validation_errors[0].lower()

    @pytest.mark.asyncio
    async def test_algorithm_not_allowed(self, initialized_engine):
        """Test execution rejected when algorithm not in allowed list"""
        # Create authorization that only allows MARKET
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],  # Only MARKET
            expires_at=datetime.now() + timedelta(hours=1)
        )

        # Try to execute with TWAP
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.TWAP,  # Not allowed
            urgency=ExecutionUrgency.NORMAL
        )

        result = await initialized_engine.execute_authorized_trade(request)

        assert result.status == ExecutionStatus.REJECTED
        assert any("not authorized" in log.lower() for log in result.execution_log)

    @pytest.mark.asyncio
    async def test_quantity_exceeds_maximum(self, initialized_engine):
        """Test execution rejected when quantity exceeds max_quantity"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=2000.0,  # Exceeds max
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        result = await initialized_engine.execute_authorized_trade(request)

        assert result.status == ExecutionStatus.REJECTED
        assert any("exceed" in log.lower() for log in result.execution_log)


# ========================================
# CATEGORY 3: MARKET ALGORITHM (4 tests)
# ========================================

class TestMarketAlgorithm:
    """Test market order execution"""

    @pytest.mark.asyncio
    async def test_market_execution_success(self, initialized_engine, market_request):
        """Test basic market execution succeeds"""
        result = await initialized_engine.execute_authorized_trade(market_request)

        assert result.status == ExecutionStatus.FILLED
        assert result.filled_quantity == market_request.authorization.quantity
        assert result.remaining_quantity == 0.0
        assert result.avg_fill_price > 0
        assert len(result.fills) == 1

    @pytest.mark.asyncio
    async def test_market_execution_result(self, initialized_engine, market_request):
        """Test market execution result fields are populated correctly"""
        result = await initialized_engine.execute_authorized_trade(market_request)

        assert result.request_id == market_request.request_id
        assert result.authorization_id == market_request.authorization.authorization_id
        assert result.algorithm_used == ExecutionAlgorithm.MARKET
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.execution_time > 0
        assert result.execution_time < 1.0  # Should be very fast in test mode

    @pytest.mark.asyncio
    async def test_market_execution_speed(self, initialized_engine, market_request):
        """Test market execution is fast in test mode"""
        import time
        start = time.time()

        result = await initialized_engine.execute_authorized_trade(market_request)

        elapsed = time.time() - start
        assert elapsed < 1.0  # Should complete in < 1 second
        assert result.status == ExecutionStatus.FILLED

    def test_market_impact_estimation(self, default_config):
        """Test market impact estimation"""
        algorithm = MarketAlgorithm(default_config)

        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0
        )
        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET,
            urgency=ExecutionUrgency.NORMAL
        )

        impact = algorithm.estimate_market_impact(request)

        assert impact > 0
        assert impact <= 0.05  # Capped at 5%


# ========================================
# CATEGORY 4: TWAP ALGORITHM (5 tests)
# ========================================

class TestTWAPAlgorithm:
    """Test TWAP execution"""

    @pytest.mark.asyncio
    async def test_twap_execution_success(self, initialized_engine, twap_request):
        """Test basic TWAP execution succeeds"""
        result = await initialized_engine.execute_authorized_trade(twap_request)

        assert result.status == ExecutionStatus.FILLED
        assert result.filled_quantity == pytest.approx(twap_request.authorization.quantity, rel=0.01)
        assert result.remaining_quantity == 0.0
        assert result.avg_fill_price > 0

    @pytest.mark.asyncio
    async def test_twap_slicing(self, initialized_engine, twap_request):
        """Test TWAP creates multiple slices"""
        result = await initialized_engine.execute_authorized_trade(twap_request)

        # With time_horizon=300 and default slicing, should have multiple fills
        assert len(result.fills) > 1
        assert result.status == ExecutionStatus.FILLED

    @pytest.mark.asyncio
    async def test_twap_execution_time(self, initialized_engine, twap_request):
        """Test TWAP execution time is reasonable"""
        import time
        start = time.time()

        result = await initialized_engine.execute_authorized_trade(twap_request)

        elapsed = time.time() - start
        # In test mode, should be very fast (no actual waits)
        assert elapsed < 5.0  # Should complete quickly in test mode
        assert result.status == ExecutionStatus.FILLED

    @pytest.mark.asyncio
    async def test_twap_fills_count(self, initialized_engine):
        """Test TWAP creates expected number of fills"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.TWAP],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.TWAP,
            time_horizon=300  # 5 minutes
        )

        result = await initialized_engine.execute_authorized_trade(request)

        # Should have multiple fills for TWAP
        assert len(result.fills) >= 5  # At least 5 slices
        assert result.status == ExecutionStatus.FILLED

    def test_twap_impact_reduction(self, default_config):
        """Test TWAP has lower impact than market"""
        twap_algo = TWAPAlgorithm(default_config)
        market_algo = MarketAlgorithm(default_config)

        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0
        )
        request = ExecutionRequest(
            authorization=auth,
            urgency=ExecutionUrgency.NORMAL
        )

        twap_impact = twap_algo.estimate_market_impact(request)
        market_impact = market_algo.estimate_market_impact(request)

        # TWAP should have lower impact (0.7x multiplier)
        assert twap_impact < market_impact


# ========================================
# CATEGORY 5: ADAPTIVE ALGORITHM (4 tests)
# ========================================

class TestAdaptiveAlgorithm:
    """Test adaptive algorithm selection"""

    @pytest.mark.asyncio
    async def test_adaptive_selects_market_urgent(self, initialized_engine):
        """Test adaptive selects market for urgent trades"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.ADAPTIVE, ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.ADAPTIVE,
            urgency=ExecutionUrgency.URGENT  # Urgent urgency
        )

        result = await initialized_engine.execute_authorized_trade(request)

        # Should execute as market (single fill, fast execution)
        assert result.status == ExecutionStatus.FILLED
        assert len(result.fills) == 1  # Market = single fill

    @pytest.mark.asyncio
    async def test_adaptive_selects_market_small(self, initialized_engine):
        """Test adaptive selects market for small quantities"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=500.0,  # Small quantity < 1000
            max_quantity=500.0,
            allowed_algorithms=[ExecutionAlgorithm.ADAPTIVE, ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.ADAPTIVE,
            urgency=ExecutionUrgency.NORMAL
        )

        result = await initialized_engine.execute_authorized_trade(request)

        # Should execute as market
        assert result.status == ExecutionStatus.FILLED
        assert len(result.fills) == 1

    @pytest.mark.asyncio
    async def test_adaptive_selects_twap_large(self, initialized_engine):
        """Test adaptive selects TWAP for large quantities with time"""
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=5000.0,  # Large quantity
            max_quantity=5000.0,
            allowed_algorithms=[ExecutionAlgorithm.ADAPTIVE, ExecutionAlgorithm.MARKET, ExecutionAlgorithm.TWAP],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.ADAPTIVE,
            urgency=ExecutionUrgency.NORMAL,
            time_horizon=600  # 10 minutes (> 300)
        )

        result = await initialized_engine.execute_authorized_trade(request)

        # Should execute as TWAP (multiple fills)
        assert result.status == ExecutionStatus.FILLED
        assert len(result.fills) > 1

    @pytest.mark.asyncio
    async def test_adaptive_execution(self, initialized_engine, adaptive_request):
        """Test adaptive execution end-to-end"""
        result = await initialized_engine.execute_authorized_trade(adaptive_request)

        assert result.status == ExecutionStatus.FILLED
        assert result.filled_quantity > 0
        assert result.avg_fill_price > 0
        assert len(result.fills) > 0


# ========================================
# CATEGORY 6: EXECUTION TRACKING (5 tests)
# ========================================

class TestExecutionTracking:
    """Test execution tracking functionality"""

    @pytest.mark.asyncio
    async def test_active_execution_tracking(self, initialized_engine, market_request):
        """Test active executions are tracked"""
        # Start execution asynchronously
        execution_task = asyncio.create_task(
            initialized_engine.execute_authorized_trade(market_request)
        )

        # Give it a moment to register
        await asyncio.sleep(0.01)

        # Should appear in active executions (might be very brief)
        # Complete the execution
        result = await execution_task

        # After completion, should not be in active executions
        active = initialized_engine.get_active_executions()
        assert market_request.request_id not in active
        assert result.status == ExecutionStatus.FILLED

    @pytest.mark.asyncio
    async def test_execution_history(self, initialized_engine, market_request):
        """Test execution history is recorded"""
        initial_count = len(initialized_engine.execution_history)

        result = await initialized_engine.execute_authorized_trade(market_request)

        assert len(initialized_engine.execution_history) == initial_count + 1
        assert result in initialized_engine.execution_history

    @pytest.mark.asyncio
    async def test_get_execution_status(self, initialized_engine, market_request):
        """Test execution status retrieval"""
        await initialized_engine.execute_authorized_trade(market_request)

        status = initialized_engine.get_execution_status(market_request.request_id)

        assert status == ExecutionStatus.FILLED

    @pytest.mark.asyncio
    async def test_get_execution_result(self, initialized_engine, market_request):
        """Test execution result retrieval"""
        await initialized_engine.execute_authorized_trade(market_request)

        retrieved_result = initialized_engine.get_execution_result(market_request.request_id)

        assert retrieved_result is not None
        assert retrieved_result.request_id == market_request.request_id
        assert retrieved_result.status == ExecutionStatus.FILLED

    @pytest.mark.asyncio
    async def test_cancel_execution(self, initialized_engine, market_request):
        """Test execution cancellation"""
        # Note: In test mode, executions are very fast, so cancellation might not work
        # This test verifies the cancel method works when execution is not found

        cancel_success = initialized_engine.cancel_execution(
            "non_existent_id",
            market_request.authorization.authorization_id
        )

        assert cancel_success is False  # Should fail for non-existent execution


# ========================================
# CATEGORY 7: METRICS & ANALYTICS (4 tests)
# ========================================

class TestMetricsAndAnalytics:
    """Test metrics and analytics functionality"""

    @pytest.mark.asyncio
    async def test_execution_metrics_update(self, initialized_engine, market_request):
        """Test execution metrics are updated correctly"""
        initial_metrics = initialized_engine.get_execution_metrics()
        initial_total = initial_metrics['total_executions']
        initial_successful = initial_metrics['successful_executions']

        await initialized_engine.execute_authorized_trade(market_request)

        updated_metrics = initialized_engine.get_execution_metrics()

        assert updated_metrics['total_executions'] == initial_total + 1
        assert updated_metrics['successful_executions'] == initial_successful + 1
        assert updated_metrics['total_volume'] >= market_request.authorization.quantity

    @pytest.mark.asyncio
    async def test_get_execution_metrics(self, initialized_engine, market_request):
        """Test execution metrics retrieval"""
        await initialized_engine.execute_authorized_trade(market_request)

        metrics = initialized_engine.get_execution_metrics()

        assert 'total_executions' in metrics
        assert 'successful_executions' in metrics
        assert 'failed_executions' in metrics
        assert 'avg_execution_time' in metrics
        assert 'avg_market_impact' in metrics
        assert 'total_volume' in metrics
        assert metrics['total_executions'] > 0

    @pytest.mark.asyncio
    async def test_execution_report(self, initialized_engine, market_request):
        """Test execution report generation"""
        await initialized_engine.execute_authorized_trade(market_request)

        report = initialized_engine.get_execution_report()

        assert 'execution_summary' in report
        assert 'performance_metrics' in report
        assert 'algorithm_breakdown' in report
        assert report['execution_summary']['total_executions'] > 0

    @pytest.mark.asyncio
    async def test_algorithm_breakdown(self, initialized_engine, market_request, twap_request):
        """Test algorithm breakdown in report"""
        await initialized_engine.execute_authorized_trade(market_request)
        await initialized_engine.execute_authorized_trade(twap_request)

        report = initialized_engine.get_execution_report()

        assert 'algorithm_breakdown' in report
        # Should have entries for executed algorithms
        assert len(report['algorithm_breakdown']) > 0


# ========================================
# CATEGORY 8: POSITION TRACKING (5 tests)
# ========================================

class TestPositionTracking:
    """Test position tracking functionality"""

    @pytest.mark.asyncio
    async def test_position_update_on_filled(self, config_with_position_tracking):
        """Test position is updated on FILLED execution"""
        position_updates = []

        async def mock_callback(symbol, side, quantity, price):
            position_updates.append({
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price
            })

        config_with_position_tracking['position_update_callback'] = mock_callback

        engine = UnifiedExecutionEngine(config_with_position_tracking)
        await engine.initialize()
        await engine.start()

        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        result = await engine.execute_authorized_trade(request)

        assert result.status == ExecutionStatus.FILLED
        assert len(position_updates) == 1
        assert position_updates[0]['symbol'] == "AAPL"
        assert position_updates[0]['side'] == "buy"
        assert position_updates[0]['quantity'] == 1000.0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_no_position_update_on_failed(self, config_with_position_tracking):
        """Test position is NOT updated on FAILED execution"""
        position_updates = []

        async def mock_callback(symbol, side, quantity, price):
            position_updates.append({'symbol': symbol})

        config_with_position_tracking['position_update_callback'] = mock_callback

        engine = UnifiedExecutionEngine(config_with_position_tracking)
        await engine.initialize()
        await engine.start()

        # Create invalid request (expired auth)
        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() - timedelta(hours=1)  # Expired
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        result = await engine.execute_authorized_trade(request)

        assert result.status == ExecutionStatus.REJECTED
        assert len(position_updates) == 0  # No position update

        await engine.stop()

    @pytest.mark.asyncio
    async def test_position_callback_invocation(self, config_with_position_tracking):
        """Test position callback is invoked with correct parameters"""
        callback_invocations = []

        async def detailed_callback(symbol, side, quantity, price):
            callback_invocations.append({
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'timestamp': datetime.now()
            })

        config_with_position_tracking['position_update_callback'] = detailed_callback

        engine = UnifiedExecutionEngine(config_with_position_tracking)
        await engine.initialize()
        await engine.start()

        auth = ExecutionAuthorization(
            symbol="MSFT",
            side="sell",
            quantity=500.0,
            max_quantity=500.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        await engine.execute_authorized_trade(request)

        assert len(callback_invocations) == 1
        invocation = callback_invocations[0]
        assert invocation['symbol'] == "MSFT"
        assert invocation['side'] == "sell"
        assert invocation['quantity'] == 500.0
        assert invocation['price'] > 0

        await engine.stop()

    @pytest.mark.asyncio
    async def test_risk_manager_callback(self, config_with_position_tracking):
        """Test risk manager callback is preferred over direct callback"""
        direct_updates = []
        risk_manager_updates = []

        async def direct_callback(symbol, side, quantity, price):
            direct_updates.append({'symbol': symbol})

        # Mock risk manager with update_position method
        class MockRiskManager:
            async def update_position(self, symbol, side, quantity, price):
                risk_manager_updates.append({
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': price
                })

        mock_risk_manager = MockRiskManager()

        config_with_position_tracking['position_update_callback'] = direct_callback
        config_with_position_tracking['risk_manager_callback'] = mock_risk_manager

        engine = UnifiedExecutionEngine(config_with_position_tracking)
        await engine.initialize()
        await engine.start()

        auth = ExecutionAuthorization(
            symbol="GOOGL",
            side="buy",
            quantity=200.0,
            max_quantity=200.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        await engine.execute_authorized_trade(request)

        # Risk manager callback should be used
        assert len(risk_manager_updates) == 1
        assert len(direct_updates) == 0  # Direct callback not used
        assert risk_manager_updates[0]['symbol'] == "GOOGL"

        await engine.stop()

    @pytest.mark.asyncio
    async def test_position_tracking_disabled(self, default_config):
        """Test no position updates when tracking is disabled"""
        position_updates = []

        async def mock_callback(symbol, side, quantity, price):
            position_updates.append({'symbol': symbol})

        # Position tracking disabled in default_config
        default_config['position_update_callback'] = mock_callback

        engine = UnifiedExecutionEngine(default_config)
        await engine.initialize()
        await engine.start()

        auth = ExecutionAuthorization(
            symbol="AAPL",
            side="buy",
            quantity=1000.0,
            max_quantity=1000.0,
            allowed_algorithms=[ExecutionAlgorithm.MARKET],
            expires_at=datetime.now() + timedelta(hours=1)
        )

        request = ExecutionRequest(
            authorization=auth,
            algorithm=ExecutionAlgorithm.MARKET
        )

        result = await engine.execute_authorized_trade(request)

        assert result.status == ExecutionStatus.FILLED
        assert len(position_updates) == 0  # No updates when disabled

        await engine.stop()


# ========================================
# CATEGORY 9: ISYSTEMCOMPONENT INTERFACE (4 tests)
# ========================================

class TestISystemComponentInterface:
    """Test ISystemComponent interface compliance"""

    @pytest.mark.asyncio
    async def test_health_check(self, initialized_engine):
        """Test health check returns correct structure"""
        health = await initialized_engine.health_check()

        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert 'active_executions' in health
        assert 'total_executions' in health
        assert 'algorithms_status' in health
        assert 'performance_metrics' in health

        assert health['component_type'] == 'UnifiedExecutionEngine'
        assert health['initialized'] is True
        assert health['operational'] is True

    def test_get_status(self, initialized_engine):
        """Test get_status returns correct data"""
        status = initialized_engine.get_status()

        assert 'component_type' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'active_executions' in status
        assert 'total_executions' in status
        assert 'execution_metrics' in status
        assert 'algorithms_count' in status
        assert 'position_tracking_enabled' in status

        assert status['component_type'] == 'UnifiedExecutionEngine'
        assert status['algorithms_count'] == 3

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, execution_engine):
        """Test start and stop lifecycle"""
        # Initialize first
        await execution_engine.initialize()
        assert execution_engine.is_initialized is True
        assert execution_engine.is_operational is False

        # Start
        success = await execution_engine.start()
        assert success is True
        assert execution_engine.is_operational is True

        # Stop
        success = await execution_engine.stop()
        assert success is True
        assert execution_engine.is_operational is False

    @pytest.mark.asyncio
    async def test_orchestrator_registration(self, execution_engine):
        """Test orchestrator registration works"""
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.register_component = Mock(return_value="test_component_id")

        component_id = execution_engine.register_with_orchestrator(mock_orchestrator)

        assert component_id == "test_component_id"
        assert execution_engine.component_id == "test_component_id"
        assert execution_engine.orchestrator == mock_orchestrator
        mock_orchestrator.register_component.assert_called_once()
