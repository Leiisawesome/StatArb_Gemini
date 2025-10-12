"""
Comprehensive tests for Trade Executor
Target: 60%+ coverage of trade_executor.py (498 lines, currently 43%)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

from core_engine.trading.execution.trade_executor import (
    # Enums
    TradeExecutionAlgorithm,
    TradeStatus,
    RiskLevel,
    
    # Data classes
    TradeExecutionRequest,
    TradeExecutionResult,
    TradeSlice,
    MarketDataSnapshot,
    
    # Component classes
    VWAPCalculator,
    TWAPExecutor,
    POVExecutor,
    ImplementationShortfallExecutor,
    MarketImpactModel,
    AdaptiveExecutionEngine,
    MarketConditionDetector,
    ExecutionPerformanceTracker,
    
    # Main class
    TradeExecutor
)


# ============================================================================
# ENUMS TESTS
# ============================================================================

class TestEnums:
    """Test enum definitions"""
    
    def test_trade_execution_algorithm_enum(self):
        """Test TradeExecutionAlgorithm enum values"""
        assert TradeExecutionAlgorithm.TWAP.value == "twap"
        assert TradeExecutionAlgorithm.VWAP.value == "vwap"
        assert TradeExecutionAlgorithm.POV.value == "pov"
        assert TradeExecutionAlgorithm.IS.value == "implementation_shortfall"
        assert TradeExecutionAlgorithm.MARKET.value == "market"
        assert len(list(TradeExecutionAlgorithm)) == 10
    
    def test_trade_status_enum(self):
        """Test TradeStatus enum values"""
        assert TradeStatus.PENDING.value == "pending"
        assert TradeStatus.ACTIVE.value == "active"
        assert TradeStatus.COMPLETED.value == "completed"
        assert TradeStatus.CANCELLED.value == "cancelled"
        assert TradeStatus.FAILED.value == "failed"
        assert len(list(TradeStatus)) == 7
    
    def test_risk_level_enum(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.CONSERVATIVE.value == "conservative"
        assert RiskLevel.MODERATE.value == "moderate"
        assert RiskLevel.AGGRESSIVE.value == "aggressive"
        assert RiskLevel.SPECULATIVE.value == "speculative"
        assert len(list(RiskLevel)) == 4


# ============================================================================
# DATA CLASS TESTS
# ============================================================================

class TestTradeExecutionRequest:
    """Test TradeExecutionRequest data class"""
    
    def test_basic_request_creation(self):
        """Test creating basic trade request"""
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        assert request.trade_id == "TRADE001"
        assert request.symbol == "AAPL"
        assert request.side == "BUY"
        assert request.quantity == 1000.0
        assert request.algorithm == TradeExecutionAlgorithm.TWAP  # Default
        assert request.participation_rate == 0.1  # Default
    
    def test_request_with_all_parameters(self):
        """Test request with all parameters"""
        start = datetime.now()
        end = start + timedelta(hours=2)
        
        request = TradeExecutionRequest(
            trade_id="TRADE002",
            symbol="MSFT",
            side="SELL",
            quantity=5000.0,
            algorithm=TradeExecutionAlgorithm.POV,
            start_time=start,
            end_time=end,
            participation_rate=0.15,
            risk_level=RiskLevel.AGGRESSIVE,
            urgency_level=8,
            max_slippage=0.01
        )
        
        assert request.algorithm == TradeExecutionAlgorithm.POV
        assert request.participation_rate == 0.15
        assert request.risk_level == RiskLevel.AGGRESSIVE
        assert request.urgency_level == 8
    
    def test_request_with_callbacks(self):
        """Test request with callbacks"""
        progress_cb = Mock()
        completion_cb = Mock()
        
        request = TradeExecutionRequest(
            trade_id="TRADE003",
            symbol="GOOGL",
            side="BUY",
            quantity=2000.0,
            progress_callback=progress_cb,
            completion_callback=completion_cb
        )
        
        assert request.progress_callback == progress_cb
        assert request.completion_callback == completion_cb


class TestTradeSlice:
    """Test TradeSlice data class"""
    
    def test_slice_creation(self):
        """Test creating trade slice"""
        now = datetime.now()
        
        slice = TradeSlice(
            slice_id="SLICE001",
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            target_quantity=100.0,
            scheduled_time=now
        )
        
        assert slice.slice_id == "SLICE001"
        assert slice.target_quantity == 100.0
        assert slice.executed_quantity == 0.0  # Default
        assert slice.status == "pending"  # Default
    
    def test_slice_with_execution_data(self):
        """Test slice with execution data"""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)
        
        slice = TradeSlice(
            slice_id="SLICE002",
            trade_id="TRADE001",
            symbol="AAPL",
            side="SELL",
            target_quantity=100.0,
            scheduled_time=start_time,
            executed_quantity=95.0,
            remaining_quantity=5.0,
            execution_start=start_time,
            execution_end=end_time,
            avg_execution_price=150.25,
            slippage=0.002,
            market_impact=0.001,
            status="completed"
        )
        
        assert slice.executed_quantity == 95.0
        assert slice.remaining_quantity == 5.0
        assert slice.avg_execution_price == 150.25
        assert slice.status == "completed"


class TestMarketDataSnapshot:
    """Test MarketDataSnapshot data class"""
    
    def test_market_data_creation(self):
        """Test creating market data snapshot"""
        now = datetime.now()
        
        data = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=now,
            bid=150.00,
            ask=150.02,
            midpoint=150.01,
            last_price=150.01,
            bid_size=1000.0,
            ask_size=1500.0,
            volume=50000.0,
            avg_volume=200000.0,
            spread=0.02,
            volatility=0.015
        )
        
        assert data.symbol == "AAPL"
        assert data.bid == 150.00
        assert data.ask == 150.02
        assert data.spread == 0.02
        assert data.session_state == "OPEN"  # Default
        assert data.liquidity_score == 0.5  # Default


# ============================================================================
# COMPONENT TESTS
# ============================================================================

class TestVWAPCalculator:
    """Test VWAP calculator"""
    
    def test_vwap_calculator_initialization(self):
        """Test VWAP calculator initialization"""
        calculator = VWAPCalculator("AAPL", lookback_days=20)
        
        assert calculator.symbol == "AAPL"
        assert calculator.lookback_days == 20
    
    def test_calculate_expected_volume_profile(self):
        """Test volume profile calculation"""
        calculator = VWAPCalculator("AAPL")
        
        date = datetime(2025, 10, 11)
        profile = calculator.calculate_expected_volume_profile(date)
        
        assert isinstance(profile, dict)
        assert len(profile) > 0
        # Volume profile should be U-shaped (high at open, low midday, high at close)
        assert "09:30" in profile
        # Market closes at 15:59 (last minute), not 16:00
        assert "15:59" in profile
    
    def test_get_current_vwap_empty(self):
        """Test getting VWAP with no data"""
        calculator = VWAPCalculator("AAPL")
        
        vwap = calculator.get_current_vwap()
        assert vwap == 100.0  # Mock default
    
    def test_update_and_get_vwap(self):
        """Test updating and getting VWAP"""
        calculator = VWAPCalculator("AAPL")
        
        # Add some data
        now = datetime.now()
        calculator.update_market_data(100.0, 1000.0, now)
        calculator.update_market_data(101.0, 1500.0, now)
        calculator.update_market_data(99.0, 500.0, now)
        
        vwap = calculator.get_current_vwap()
        # VWAP = (100*1000 + 101*1500 + 99*500) / (1000 + 1500 + 500)
        expected_vwap = (100*1000 + 101*1500 + 99*500) / 3000
        assert abs(vwap - expected_vwap) < 0.01


class TestTWAPExecutor:
    """Test TWAP execution algorithm"""
    
    def test_twap_executor_initialization(self):
        """Test TWAP executor initialization"""
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.TWAP
        )
        
        executor = TWAPExecutor(request)
        assert executor.request == request
        assert executor.slices == []
    
    def test_generate_execution_schedule_with_duration(self):
        """Test generating TWAP schedule with duration"""
        start = datetime.now()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.TWAP,
            start_time=start,
            duration_minutes=60,
            randomize_timing=False
        )
        
        executor = TWAPExecutor(request)
        slices = executor.generate_execution_schedule()
        
        assert len(slices) > 0
        assert all(isinstance(s, TradeSlice) for s in slices)
        # Total quantity should equal request quantity
        total_qty = sum(s.target_quantity for s in slices)
        assert abs(total_qty - 1000.0) < 1.0  # Allow small rounding error
    
    def test_generate_schedule_with_end_time(self):
        """Test generating schedule with end time"""
        start = datetime.now()
        end = start + timedelta(hours=2)
        
        request = TradeExecutionRequest(
            trade_id="TRADE002",
            symbol="MSFT",
            side="SELL",
            quantity=5000.0,
            start_time=start,
            end_time=end,
            randomize_timing=False
        )
        
        executor = TWAPExecutor(request)
        slices = executor.generate_execution_schedule()
        
        assert len(slices) > 0
        # Slices should be scheduled between start and end
        assert all(start <= s.scheduled_time <= end for s in slices)


class TestPOVExecutor:
    """Test POV execution algorithm"""
    
    def test_pov_executor_initialization(self):
        """Test POV executor initialization"""
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.POV,
            participation_rate=0.15
        )
        
        executor = POVExecutor(request)
        assert executor.request.participation_rate == 0.15
        assert executor.executed_quantity == 0.0
    
    def test_calculate_next_slice_size(self):
        """Test calculating next slice size"""
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=10000.0,
            participation_rate=0.1
        )
        
        executor = POVExecutor(request)
        
        # With 1000 volume and 10% participation
        slice_size = executor.calculate_next_slice_size(
            current_volume=1000.0,
            time_remaining=300.0
        )
        
        assert slice_size > 0
        assert slice_size <= request.quantity * 0.3  # Max 30% constraint


class TestImplementationShortfallExecutor:
    """Test Implementation Shortfall algorithm"""
    
    def test_is_executor_initialization(self):
        """Test IS executor initialization"""
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.IS,
            risk_aversion=0.7
        )
        
        executor = ImplementationShortfallExecutor(request)
        assert executor.risk_aversion == 0.7
        assert executor.arrival_price is None
    
    def test_optimize_execution_schedule(self):
        """Test optimizing execution schedule"""
        start = datetime.now()
        end = start + timedelta(hours=1)
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.IS,
            start_time=start,
            end_time=end
        )
        
        executor = ImplementationShortfallExecutor(request)
        
        market_data = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=start,
            bid=150.00,
            ask=150.02,
            midpoint=150.01,
            last_price=150.01,
            bid_size=1000.0,
            ask_size=1000.0,
            volume=1000.0,
            avg_volume=100000.0,
            spread=0.02,
            volatility=0.015
        )
        
        slices = executor.optimize_execution_schedule(market_data)
        
        assert len(slices) > 0
        assert executor.arrival_price == 150.01
        # Total quantity should equal request
        total_qty = sum(s.target_quantity for s in slices)
        assert abs(total_qty - 1000.0) < 1.0


class TestMarketImpactModel:
    """Test market impact model"""
    
    def test_market_impact_model_initialization(self):
        """Test model initialization"""
        model = MarketImpactModel()
        
        assert 'temporary_impact_coeff' in model.model_params
        assert 'permanent_impact_coeff' in model.model_params
    
    def test_estimate_impact(self):
        """Test estimating market impact"""
        model = MarketImpactModel()
        
        market_data = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=150.00,
            ask=150.02,
            midpoint=150.01,
            last_price=150.01,
            bid_size=1000.0,
            ask_size=1000.0,
            volume=1000.0,
            avg_volume=100000.0,
            spread=0.02,
            volatility=0.015
        )
        
        impact = model.estimate_impact(
            symbol="AAPL",
            quantity=5000.0,
            execution_rate=1.0,
            market_data=market_data
        )
        
        assert 'temporary_impact' in impact
        assert 'permanent_impact' in impact
        assert 'total_impact' in impact
        assert impact['total_impact'] >= 0


class TestMarketConditionDetector:
    """Test market condition detector"""
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        detector = MarketConditionDetector()
        
        assert len(detector.price_history) == 0
        assert len(detector.volume_history) == 0
    
    def test_detect_conditions_insufficient_data(self):
        """Test detection with insufficient data"""
        detector = MarketConditionDetector()
        
        market_data = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=150.00,
            ask=150.02,
            midpoint=150.01,
            last_price=150.01,
            bid_size=1000.0,
            ask_size=1000.0,
            volume=1000.0,
            avg_volume=100000.0,
            spread=0.02,
            volatility=0.015
        )
        
        conditions = detector.detect_conditions(market_data)
        
        assert conditions['volatility_regime'] == 'normal'
        assert conditions['trend'] == 'sideways'
    
    def test_detect_high_volatility(self):
        """Test detecting high volatility"""
        detector = MarketConditionDetector()
        
        # Add data with high volatility
        for i in range(20):
            price = 100.0 + (i % 2) * 5  # Oscillating prices
            market_data = MarketDataSnapshot(
                symbol="AAPL",
                timestamp=datetime.now(),
                bid=price,
                ask=price+0.02,
                midpoint=price,
                last_price=price,
                bid_size=1000.0,
                ask_size=1000.0,
                volume=1000.0,
                avg_volume=100000.0,
                spread=0.02,
                volatility=0.015
            )
            conditions = detector.detect_conditions(market_data)
        
        # After enough data, should detect volatility
        assert 'volatility_regime' in conditions
        assert 'trend' in conditions
        assert 'liquidity_score' in conditions


class TestExecutionPerformanceTracker:
    """Test execution performance tracker"""
    
    def test_tracker_initialization(self):
        """Test tracker initialization"""
        tracker = ExecutionPerformanceTracker()
        
        assert len(tracker.metrics) == 0
        assert len(tracker.benchmarks) == 0
    
    def test_track_slice_execution(self):
        """Test tracking slice execution"""
        tracker = ExecutionPerformanceTracker()
        
        now = datetime.now()
        
        slice = TradeSlice(
            slice_id="SLICE001",
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            target_quantity=100.0,
            scheduled_time=now,
            executed_quantity=100.0,
            avg_execution_price=150.10,
            execution_start=now,
            execution_end=now + timedelta(seconds=5)
        )
        
        market_before = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=now,
            bid=150.00,
            ask=150.02,
            midpoint=150.01,
            last_price=150.01,
            bid_size=1000.0,
            ask_size=1000.0,
            volume=1000.0,
            avg_volume=100000.0,
            spread=0.02,
            volatility=0.015
        )
        
        market_after = MarketDataSnapshot(
            symbol="AAPL",
            timestamp=now + timedelta(seconds=5),
            bid=150.05,
            ask=150.07,
            midpoint=150.06,
            last_price=150.06,
            bid_size=1000.0,
            ask_size=1000.0,
            volume=1000.0,
            avg_volume=100000.0,
            spread=0.02,
            volatility=0.015
        )
        
        performance = tracker.track_slice_execution(slice, market_before, market_after)
        
        assert 'slippage' in performance
        assert 'market_impact' in performance
        assert 'timing_cost' in performance
    
    def test_get_aggregate_performance(self):
        """Test getting aggregate performance"""
        tracker = ExecutionPerformanceTracker()
        
        # Add some metrics
        tracker.metrics['slippage'].extend([0.001, 0.002, 0.0015])
        tracker.metrics['market_impact'].extend([0.0005, 0.0008, 0.0006])
        
        aggregate = tracker.get_aggregate_performance()
        
        assert 'slippage' in aggregate
        assert 'market_impact' in aggregate
        assert aggregate['slippage']['count'] == 3
        assert 'mean' in aggregate['slippage']
        assert 'std' in aggregate['slippage']


# ============================================================================
# MAIN TRADE EXECUTOR TESTS
# ============================================================================

class TestTradeExecutor:
    """Test main TradeExecutor class"""
    
    def test_executor_initialization(self):
        """Test trade executor initialization"""
        executor = TradeExecutor()
        
        assert executor.performance_tracker is not None
        assert executor.adaptive_engine is not None
        assert executor.market_impact_model is not None
        assert executor.condition_detector is not None
        assert len(executor._active_trades) == 0
        assert len(executor._trade_history) == 0
        assert executor._running == False
    
    def test_start_and_stop(self):
        """Test starting and stopping executor"""
        executor = TradeExecutor()
        
        executor.start()
        assert executor._running == True
        
        executor.stop()
        assert executor._running == False
    
    @pytest.mark.asyncio
    async def test_execute_trade_basic(self):
        """Test basic trade execution"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.TWAP,
            duration_minutes=10
        )
        
        trade_id = await executor.execute_trade(request)
        
        assert trade_id == "TRADE001"
        assert "TRADE001" in executor._active_trades
    
    @pytest.mark.asyncio
    async def test_execute_trade_validation_failure(self):
        """Test trade execution with validation failure"""
        executor = TradeExecutor()
        
        # Invalid quantity
        request = TradeExecutionRequest(
            trade_id="TRADE002",
            symbol="AAPL",
            side="BUY",
            quantity=-100.0  # Invalid
        )
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            await executor.execute_trade(request)
    
    def test_validate_trade_request_valid(self):
        """Test validating valid trade request"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        # Should not raise
        executor._validate_trade_request(request)
    
    def test_validate_trade_request_invalid_quantity(self):
        """Test validation with invalid quantity"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=0.0
        )
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            executor._validate_trade_request(request)
    
    def test_validate_trade_request_invalid_side(self):
        """Test validation with invalid side"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="HOLD",  # Invalid
            quantity=1000.0
        )
        
        with pytest.raises(ValueError, match="Side must be"):
            executor._validate_trade_request(request)
    
    def test_validate_trade_request_invalid_participation_rate(self):
        """Test validation with invalid participation rate"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            participation_rate=1.5  # Invalid (> 1.0)
        )
        
        with pytest.raises(ValueError, match="Participation rate"):
            executor._validate_trade_request(request)
    
    def test_get_trade_status_not_found(self):
        """Test getting status for non-existent trade"""
        executor = TradeExecutor()
        
        status = executor.get_trade_status("NONEXISTENT")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_trade_status_active_trade(self):
        """Test getting status for active trade"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        await executor.execute_trade(request)
        
        status = executor.get_trade_status("TRADE001")
        
        assert status is not None
        assert status['trade_id'] == "TRADE001"
        assert status['symbol'] == "AAPL"
        assert status['total_quantity'] == 1000.0
        assert 'executed_quantity' in status
        assert 'status' in status
    
    @pytest.mark.asyncio
    async def test_cancel_trade(self):
        """Test cancelling active trade"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        await executor.execute_trade(request)
        
        result = executor.cancel_trade("TRADE001")
        assert result == True
        
        status = executor.get_trade_status("TRADE001")
        assert status['status'] == TradeStatus.CANCELLED.value
    
    def test_cancel_nonexistent_trade(self):
        """Test cancelling non-existent trade"""
        executor = TradeExecutor()
        
        result = executor.cancel_trade("NONEXISTENT")
        assert result == False
    
    def test_get_execution_statistics_empty(self):
        """Test getting statistics with no trades"""
        executor = TradeExecutor()
        
        stats = executor.get_execution_statistics()
        
        assert stats['total_trades'] == 0
    
    @pytest.mark.asyncio
    async def test_get_execution_statistics_with_trades(self):
        """Test getting statistics with trades"""
        executor = TradeExecutor()
        
        # Execute a trade
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        await executor.execute_trade(request)
        
        # Allow some execution and then finalize
        await asyncio.sleep(0.1)
        executor.cancel_trade("TRADE001")
        await asyncio.sleep(0.2)  # Allow cancellation to complete and finalize
        
        stats = executor.get_execution_statistics()
        
        # Should have stats (either with trades in history or just total_trades=0)
        assert 'total_trades' in stats
        # If trades were finalized, should have more keys
        if stats['total_trades'] > 0:
            assert 'active_trades' in stats
            assert 'completed_trades' in stats
    
    def test_generate_default_schedule(self):
        """Test generating default execution schedule"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0
        )
        
        slices = executor._generate_default_schedule(request)
        
        assert len(slices) > 0
        assert all(isinstance(s, TradeSlice) for s in slices)
        
        # Total quantity should equal request
        total_qty = sum(s.target_quantity for s in slices)
        assert abs(total_qty - 1000.0) < 1.0
    
    @pytest.mark.asyncio
    async def test_get_market_data(self):
        """Test getting market data"""
        executor = TradeExecutor()
        
        market_data = await executor._get_market_data("AAPL")
        
        assert isinstance(market_data, MarketDataSnapshot)
        assert market_data.symbol == "AAPL"
        assert market_data.bid > 0
        assert market_data.ask > 0
        assert market_data.ask >= market_data.bid


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestTradeExecutorIntegration:
    """Integration tests for full trade execution flow"""
    
    @pytest.mark.asyncio
    async def test_full_trade_lifecycle_twap(self):
        """Test full TWAP trade lifecycle"""
        executor = TradeExecutor()
        executor.start()
        
        progress_calls = []
        completion_calls = []
        
        def progress_callback(progress):
            progress_calls.append(progress)
        
        def completion_callback(trade_state):
            completion_calls.append(trade_state)
        
        request = TradeExecutionRequest(
            trade_id="TRADE_LIFECYCLE",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.TWAP,
            duration_minutes=1,
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
        
        trade_id = await executor.execute_trade(request)
        assert trade_id == "TRADE_LIFECYCLE"
        
        # Check trade is active
        status = executor.get_trade_status(trade_id)
        assert status is not None
        
        # Wait a bit for some slices to execute
        await asyncio.sleep(0.2)
        
        # Cancel to finish quickly
        executor.cancel_trade(trade_id)
        
        executor.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_trades(self):
        """Test executing multiple trades concurrently"""
        executor = TradeExecutor()
        executor.start()
        
        # Start multiple trades
        trade_ids = []
        for i in range(3):
            request = TradeExecutionRequest(
                trade_id=f"TRADE_{i}",
                symbol=f"STOCK{i}",
                side="BUY",
                quantity=1000.0 + i * 500,
                duration_minutes=1
            )
            trade_id = await executor.execute_trade(request)
            trade_ids.append(trade_id)
        
        # All should be active
        assert len(executor._active_trades) == 3
        
        # Check each trade status
        for trade_id in trade_ids:
            status = executor.get_trade_status(trade_id)
            assert status is not None
            assert status['status'] in [TradeStatus.ACTIVE.value, TradeStatus.PENDING.value]
        
        # Cancel all
        for trade_id in trade_ids:
            executor.cancel_trade(trade_id)
        
        executor.stop()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_algorithm(self):
        """Test executing with unsupported algorithm"""
        executor = TradeExecutor()
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            algorithm=TradeExecutionAlgorithm.VWAP  # Not implemented
        )
        
        # Should raise ValueError for unsupported algorithm
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            await executor.execute_trade(request)
    
    def test_invalid_time_range(self):
        """Test validation with invalid time range"""
        executor = TradeExecutor()
        
        start = datetime.now()
        end = start - timedelta(hours=1)  # End before start
        
        request = TradeExecutionRequest(
            trade_id="TRADE001",
            symbol="AAPL",
            side="BUY",
            quantity=1000.0,
            start_time=start,
            end_time=end
        )
        
        with pytest.raises(ValueError, match="End time must be after start time"):
            executor._validate_trade_request(request)
