#!/usr/bin/env python3
"""
Refactored Test Suite for ExecutionEngine
=========================================

Comprehensive unit tests for the Execution Engine (ACTION Component).
This suite covers:
- Enum and Dataclass integrity
- Engine lifecycle management
- Order submission and slicing
- Risk monitoring (pre-trade and real-time)
- Slice execution and simulation
- Execution management (status, cancellation)
- Performance metrics tracking
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from core_engine.trading.execution.execution_engine import (
    ExecutionEngine,
    ExecutionConfig,
    ExecutionRequest,
    ExecutionSlice,
    ExecutionStatus,
    ExecutionUrgency,
    ExecutionAlgorithm,
    ExecutionStyle,
    ExecutionMetrics
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def execution_config():
    """Default execution configuration for testing"""
    return ExecutionConfig(
        max_execution_time=3600,
        slice_interval=30,
        enable_pre_trade_risk=True,
        enable_real_time_risk=True,
        max_order_value=10_000_000
    )

@pytest.fixture
def engine(execution_config):
    """Execution engine instance with test config"""
    return ExecutionEngine(execution_config)

@pytest.fixture
def sample_request():
    """A standard execution request for testing"""
    return ExecutionRequest(
        request_id="REQ_001",
        symbol="AAPL",
        side="BUY",
        quantity=1000,
        order_type="LIMIT",
        limit_price=150.0,
        urgency=ExecutionUrgency.NORMAL,
        algorithm=ExecutionAlgorithm.TWAP
    )

# ============================================================================
# COMPONENT TESTS (Enums & Dataclasses)
# ============================================================================

class TestComponentIntegrity:
    """Test that enums and dataclasses are correctly defined"""

    def test_execution_status_enum(self):
        """Verify ExecutionStatus enum values"""
        assert ExecutionStatus.PENDING.value == "pending"
        assert ExecutionStatus.FILLED.value == "filled"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
        assert ExecutionStatus.ERROR.value == "error"

    def test_execution_urgency_enum(self):
        """Verify ExecutionUrgency enum values"""
        assert ExecutionUrgency.LOW.value == "low"
        assert ExecutionUrgency.URGENT.value == "urgent"

    def test_execution_config_defaults(self):
        """Verify ExecutionConfig default values"""
        config = ExecutionConfig()
        assert config.default_algorithm == ExecutionAlgorithm.TWAP
        assert config.max_participation_rate == 0.20
        assert config.enable_smart_routing is True

    def test_execution_request_creation(self, sample_request):
        """Verify ExecutionRequest initialization"""
        assert sample_request.request_id == "REQ_001"
        assert sample_request.symbol == "AAPL"
        assert sample_request.quantity == 1000
        assert isinstance(sample_request.created_at, datetime)

# ============================================================================
# ENGINE LIFECYCLE TESTS
# ============================================================================

class TestEngineLifecycle:
    """Test engine start, stop, and context management"""

    def test_initialization(self, engine, execution_config):
        """Test engine initializes with correct config"""
        assert engine.config == execution_config
        assert engine._running is False
        assert len(engine._active_requests) == 0

    def test_start_stop(self, engine):
        """Test manual start and stop"""
        engine.start()
        assert engine._running is True
        engine.stop()
        assert engine._running is False

    def test_context_manager(self, execution_config):
        """Test engine as a context manager"""
        with ExecutionEngine(execution_config) as engine:
            assert engine._running is True
        assert engine._running is False

# ============================================================================
# ORDER SUBMISSION & SLICING TESTS
# ============================================================================

class TestOrderSubmission:
    """Test submitting requests and generating slices"""

    @pytest.mark.asyncio
    async def test_submit_request_success(self, engine, sample_request):
        """Test successful request submission and slicing"""
        request_id = await engine.submit_execution_request(sample_request)
        
        assert request_id == "REQ_001"
        assert "REQ_001" in engine._active_requests
        
        request_data = engine._active_requests["REQ_001"]
        assert request_data['status'] == ExecutionStatus.PENDING
        assert len(request_data['slices']) > 0
        assert engine._slice_queue.qsize() > 0

    @pytest.mark.asyncio
    async def test_pre_trade_risk_failure(self, engine):
        """Test submission failure due to risk limits"""
        large_request = ExecutionRequest(
            request_id="REQ_LARGE",
            symbol="AAPL",
            side="BUY",
            quantity=1_000_000,
            limit_price=1000.0  # $1B order, exceeds $10M limit
        )
        
        with pytest.raises(ValueError, match="Pre-trade risk check failed"):
            await engine.submit_execution_request(large_request)

# ============================================================================
# EXECUTION LOGIC TESTS
# ============================================================================

class TestExecutionLogic:
    """Test slice execution and simulation"""

    @pytest.mark.asyncio
    async def test_execute_slice_success(self, engine):
        """Test successful execution of a single slice"""
        test_slice = ExecutionSlice(
            slice_id="SLICE_001",
            parent_request_id="REQ_001",
            symbol="AAPL",
            side="BUY",
            quantity=100.0,
            slice_number=1,
            total_slices=10,
            scheduled_time=datetime.now()
        )

        # Mock market data to ensure predictable results
        with patch.object(engine, '_get_current_market_data', return_value={
            'current_price': 150.0,
            'benchmark_price': 150.0,
            'spread': 0.01
        }):
            # Mock simulation to avoid real sleep
            with patch.object(engine, '_simulate_execution', AsyncMock(return_value={
                'filled_quantity': 100.0,
                'avg_fill_price': 150.05,
                'slippage': 0.0003,
                'market_impact': 0.0001
            })):
                result = await engine.execute_slice(test_slice)
                
                assert result.status == ExecutionStatus.FILLED
                assert result.filled_quantity == 100.0
                assert result.avg_fill_price == 150.05
                assert result.filled_time is not None

    @pytest.mark.asyncio
    async def test_real_time_risk_rejection(self, engine):
        """Test slice rejection due to real-time risk (e.g., price move)"""
        test_slice = ExecutionSlice(
            slice_id="SLICE_001",
            parent_request_id="REQ_001",
            symbol="AAPL",
            side="BUY",
            quantity=100.0,
            slice_number=1,
            total_slices=10,
            scheduled_time=datetime.now()
        )

        # Mock market data with a large price move (10%)
        with patch.object(engine, '_get_current_market_data', return_value={
            'current_price': 165.0,
            'benchmark_price': 150.0,
            'spread': 0.01
        }):
            result = await engine.execute_slice(test_slice)
            
            assert result.status == ExecutionStatus.REJECTED
            assert result.filled_quantity == 0.0

# ============================================================================
# MANAGEMENT & METRICS TESTS
# ============================================================================

class TestExecutionManagement:
    """Test status tracking, cancellation, and metrics"""

    @pytest.mark.asyncio
    async def test_get_execution_status(self, engine, sample_request):
        """Test retrieving status for an active request"""
        await engine.submit_execution_request(sample_request)
        
        status = engine.get_execution_status("REQ_001")
        assert status is not None
        assert status['request_id'] == "REQ_001"
        assert status['status'] == ExecutionStatus.PENDING
        assert status['total_quantity'] == 1000

    @pytest.mark.asyncio
    async def test_cancel_execution(self, engine, sample_request):
        """Test cancelling an active execution request"""
        await engine.submit_execution_request(sample_request)
        
        success = engine.cancel_execution("REQ_001")
        assert success is True
        
        status = engine.get_execution_status("REQ_001")
        assert status['status'] == ExecutionStatus.CANCELLED
        
        # Verify slices are also cancelled
        request_data = engine._active_requests["REQ_001"]
        assert all(s.status == ExecutionStatus.CANCELLED for s in request_data['slices'])

    @pytest.mark.asyncio
    async def test_get_execution_metrics(self, engine, sample_request):
        """Test performance metrics calculation"""
        # Submit and cancel to have some history
        await engine.submit_execution_request(sample_request)
        engine.cancel_execution("REQ_001")
        
        metrics = engine.get_execution_metrics()
        assert isinstance(metrics, ExecutionMetrics)
        assert metrics.total_executions == 1
        assert metrics.completion_rate == 1.0  # Cancelled counts as completed in this implementation

# ============================================================================
# INTEGRATION SCENARIO
# ============================================================================

class TestIntegrationScenario:
    """Test end-to-end flow in a controlled environment"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_flow(self, engine, sample_request):
        """Test submission -> manual slice execution -> status check"""
        engine.start()
        
        # 1. Submit
        await engine.submit_execution_request(sample_request)
        
        # 2. Manually execute one slice from the queue
        _, _, slice_to_exec = engine._slice_queue.get_nowait()
        
        with patch.object(engine, '_get_current_market_data', return_value={
            'current_price': 150.0, 'benchmark_price': 150.0, 'spread': 0.01
        }):
            await engine.execute_slice(slice_to_exec)
        
        # 3. Verify status
        status = engine.get_execution_status("REQ_001")
        assert status['filled_quantity'] > 0
        assert status['slices_completed'] >= 1
        
        engine.stop()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
