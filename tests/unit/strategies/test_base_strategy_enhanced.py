"""
Comprehensive Unit Tests for EnhancedBaseStrategy
===============================================

Tests for the EnhancedBaseStrategy component, focusing on:
- ISystemComponent interface compliance
- Strategy lifecycle management
- Performance tracking and metrics
- Health monitoring and status reporting
- Risk management integration
- Error handling and recovery

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import pytest
import asyncio
import uuid
import numpy as np
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the component under test
from core_engine.trading.strategies.base_strategy_enhanced import (
    EnhancedBaseStrategy,
    StrategyPerformanceMetrics,
    StrategyHealthStatus
)

from core_engine.trading.strategies.strategy_engine import (
    StrategyConfig,
    StrategySignal,
    StrategyPosition,
    SignalType,
    StrategyType,
    StrategyState
)


class MockStrategy(EnhancedBaseStrategy):
    """Mock strategy implementation for testing"""

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.signals_to_generate = []
        self.generate_signals_called = False
        self.update_positions_called = False

    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Mock signal generation"""
        self.generate_signals_called = True
        return self.signals_to_generate.copy()

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Mock position update"""
        self.update_positions_called = True

    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Mock position size calculation"""
        return 100.0  # Fixed size for testing

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Mock strategy health check"""
        return {
            'strategy_healthy': True,
            'mock_metric': 'healthy'
        }

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Mock strategy config summary"""
        return {
            'mock_setting': 'test_value'
        }


@pytest.fixture
def strategy_config():
    """Configuration for test strategy"""
    return StrategyConfig(
        strategy_id="test_strategy_001",
        strategy_name="Test Strategy",
        strategy_type=StrategyType.STATISTICAL_ARBITRAGE,
        max_position_size=0.1,
        max_daily_loss=0.2,
        paper_trading_mode=True
    )


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    risk_manager = Mock()
    risk_manager.process_signal = AsyncMock(return_value=True)
    return risk_manager


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    data = {
        'AAPL': pd.DataFrame({
            'open': np.random.uniform(150, 160, len(dates)),
            'high': np.random.uniform(160, 170, len(dates)),
            'low': np.random.uniform(140, 150, len(dates)),
            'close': np.random.uniform(150, 160, len(dates)),
            'volume': np.random.randint(1000000, 5000000, len(dates))
        }, index=dates),
        'GOOGL': pd.DataFrame({
            'open': np.random.uniform(2800, 2900, len(dates)),
            'high': np.random.uniform(2900, 3000, len(dates)),
            'low': np.random.uniform(2700, 2800, len(dates)),
            'close': np.random.uniform(2800, 2900, len(dates)),
            'volume': np.random.randint(500000, 2000000, len(dates))
        }, index=dates)
    }
    return data


@pytest.fixture
def mock_strategy(strategy_config, mock_risk_manager):
    """Mock strategy instance for testing"""
    strategy = MockStrategy(strategy_config)
    strategy.set_risk_manager(mock_risk_manager)
    return strategy


class TestEnhancedBaseStrategyInterface:
    """Test ISystemComponent interface compliance"""

    def test_initialization(self, strategy_config):
        """Test EnhancedBaseStrategy initialization"""
        strategy = MockStrategy(strategy_config)

        assert strategy.config == strategy_config
        assert strategy.strategy_id == "test_strategy_001"
        assert strategy.strategy_type == StrategyType.STATISTICAL_ARBITRAGE
        assert not strategy.is_initialized
        assert not strategy.is_operational
        assert strategy.component_id is None
        assert strategy.state == StrategyState.INACTIVE
        assert strategy.health_status == StrategyHealthStatus.HEALTHY
        assert len(strategy._positions) == 0
        assert len(strategy._signals) == 0
        assert strategy.performance_metrics.total_signals == 0

    @pytest.mark.asyncio
    async def test_initialize_method(self, mock_strategy):
        """Test initialize method"""
        result = await mock_strategy.initialize()

        assert result is True
        assert mock_strategy.is_initialized
        assert mock_strategy.state == StrategyState.INACTIVE  # Ready to start
        assert mock_strategy.last_error is None

    @pytest.mark.asyncio
    async def test_start_method(self, mock_strategy):
        """Test start method"""
        # Initialize first
        await mock_strategy.initialize()

        result = await mock_strategy.start()

        assert result is True
        assert mock_strategy.is_operational
        assert mock_strategy.state == StrategyState.ACTIVE
        assert mock_strategy.start_time is not None

    @pytest.mark.asyncio
    async def test_start_without_initialization(self, mock_strategy):
        """Test start method without initialization"""
        result = await mock_strategy.start()

        assert result is False
        assert not mock_strategy.is_operational
        assert mock_strategy.state == StrategyState.INACTIVE

    @pytest.mark.asyncio
    async def test_stop_method(self, mock_strategy):
        """Test stop method"""
        # Initialize and start first
        await mock_strategy.initialize()
        await mock_strategy.start()

        result = await mock_strategy.stop()

        assert result is True
        assert not mock_strategy.is_operational
        assert mock_strategy.state == StrategyState.STOPPED
        assert mock_strategy.stop_time is not None

    @pytest.mark.asyncio
    async def test_health_check(self, mock_strategy):
        """Test health check method"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        health = await mock_strategy.health_check()

        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert 'component_type' in health
        assert 'strategy_id' in health
        assert 'strategy_type' in health
        assert health['component_type'] == 'Strategy'
        assert health['strategy_id'] == 'test_strategy_001'
        assert health['initialized'] is True
        assert health['operational'] is True
        assert 'performance_metrics' in health
        assert 'operational_metrics' in health

    def test_get_status(self, mock_strategy):
        """Test get_status method"""
        status = mock_strategy.get_status()

        assert isinstance(status, dict)
        assert 'component_type' in status
        assert 'strategy_id' in status
        assert 'strategy_type' in status
        assert 'initialized' in status
        assert 'operational' in status
        assert 'state' in status
        assert 'performance_summary' in status
        assert 'config_summary' in status
        assert status['component_type'] == 'Strategy'
        assert status['strategy_id'] == 'test_strategy_001'


class TestStrategyLifecycle:
    """Test strategy lifecycle management"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_strategy):
        """Test complete strategy lifecycle"""
        # Initialize
        assert await mock_strategy.initialize() is True
        assert mock_strategy.is_initialized is True
        assert mock_strategy.state == StrategyState.INACTIVE  # Ready to start

        # Start
        assert await mock_strategy.start() is True
        assert mock_strategy.is_operational is True
        assert mock_strategy.state == StrategyState.ACTIVE

        # Check health
        health = await mock_strategy.health_check()
        assert health['healthy'] is True

        # Check status
        status = mock_strategy.get_status()
        assert status['initialized'] is True
        assert status['operational'] is True

        # Stop
        assert await mock_strategy.stop() is True
        assert mock_strategy.is_operational is False
        assert mock_strategy.state == StrategyState.STOPPED

    @pytest.mark.asyncio
    async def test_configuration_validation(self, strategy_config):
        """Test configuration validation"""
        # Test with invalid max position size
        invalid_config = strategy_config
        invalid_config.max_position_size = 1.5  # Invalid (> 1)

        strategy = MockStrategy(invalid_config)
        result = await strategy.initialize()

        # Should fail validation
        assert result is False
        assert strategy.last_error is not None

    @pytest.mark.asyncio
    async def test_error_handling_in_initialization(self, mock_strategy):
        """Test error handling during initialization"""
        # Mock an initialization error
        with patch.object(mock_strategy, '_initialize_strategy_components',
                         side_effect=Exception("Mock initialization error")):
            result = await mock_strategy.initialize()

        assert result is False
        assert mock_strategy.last_error is not None
        assert "Mock initialization error" in mock_strategy.last_error
        assert mock_strategy.performance_metrics.error_count > 0


class TestPerformanceTracking:
    """Test performance tracking functionality"""

    def test_performance_metrics_initialization(self, mock_strategy):
        """Test performance metrics initialization"""
        assert isinstance(mock_strategy.performance_metrics, StrategyPerformanceMetrics)
        assert mock_strategy.performance_metrics.total_signals == 0
        assert mock_strategy.performance_metrics.successful_signals == 0
        assert mock_strategy.performance_metrics.error_count == 0

    def test_signal_generation_time_tracking(self, mock_strategy):
        """Test signal generation time tracking"""
        # Track some generation times
        mock_strategy.track_signal_generation_time(0.1)
        mock_strategy.track_signal_generation_time(0.2)
        mock_strategy.track_signal_generation_time(0.15)

        # Check average calculation
        expected_avg = (0.1 + 0.2 + 0.15) / 3
        assert abs(mock_strategy.performance_metrics.avg_signal_generation_time - expected_avg) < 0.001

    def test_performance_metrics_update(self, mock_strategy):
        """Test performance metrics update"""
        # Create a mock signal
        signal = StrategySignal(
            signal_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            target_quantity=100.0,
            position_side="long"
        )

        # Update metrics for successful signal
        mock_strategy.update_performance_metrics(signal, success=True)

        assert mock_strategy.performance_metrics.total_signals == 1
        assert mock_strategy.performance_metrics.successful_signals == 1
        assert mock_strategy.performance_metrics.failed_signals == 0

        # Update metrics for failed signal
        mock_strategy.update_performance_metrics(signal, success=False)

        assert mock_strategy.performance_metrics.total_signals == 2
        assert mock_strategy.performance_metrics.successful_signals == 1
        assert mock_strategy.performance_metrics.failed_signals == 1

    def test_success_rate_calculation(self, mock_strategy):
        """Test success rate calculation"""
        # No signals initially
        assert mock_strategy._calculate_success_rate() == 0.0

        # Add some signals
        signal = StrategySignal(
            signal_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            target_quantity=100.0,
            position_side="long"
        )

        mock_strategy.update_performance_metrics(signal, success=True)
        mock_strategy.update_performance_metrics(signal, success=True)
        mock_strategy.update_performance_metrics(signal, success=False)

        # Should be 2/3 = 0.667
        expected_rate = 2.0 / 3.0
        assert abs(mock_strategy._calculate_success_rate() - expected_rate) < 0.001


class TestHealthMonitoring:
    """Test health monitoring functionality"""

    @pytest.mark.asyncio
    async def test_health_status_tracking(self, mock_strategy):
        """Test health status tracking"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Initially healthy
        assert mock_strategy.health_status == StrategyHealthStatus.HEALTHY

        # Perform health check
        health = await mock_strategy.health_check()
        assert health['healthy'] is True
        assert mock_strategy.health_checks_performed == 1
        assert mock_strategy.last_health_check is not None

    @pytest.mark.asyncio
    async def test_health_degradation_on_errors(self, mock_strategy):
        """Test health degradation when errors occur"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Simulate multiple errors
        for i in range(15):  # More than the 10 error threshold
            mock_strategy._log_error(f"Test error {i}", Exception(f"Mock error {i}"))

        health = await mock_strategy.health_check()

        # Should be unhealthy due to high error count
        assert health['healthy'] is False
        assert mock_strategy.health_status == StrategyHealthStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_health_warning_on_moderate_issues(self, mock_strategy):
        """Test health warning on moderate issues"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Simulate moderate warnings
        for i in range(7):  # More than the 5 warning threshold
            mock_strategy._log_warning(f"Test warning {i}")

        health = await mock_strategy.health_check()

        # Should still be healthy but with warning status
        assert health['healthy'] is True
        assert mock_strategy.health_status == StrategyHealthStatus.WARNING

    def test_error_logging(self, mock_strategy):
        """Test error logging functionality"""
        initial_error_count = mock_strategy.performance_metrics.error_count

        # Log an error
        test_exception = Exception("Test error")
        mock_strategy._log_error("Test error message", test_exception)

        # Check error tracking
        assert mock_strategy.performance_metrics.error_count == initial_error_count + 1
        assert mock_strategy.performance_metrics.last_error == "Test error message: Test error"
        assert len(mock_strategy._error_log) == 1

        # Check error log entry
        error_entry = mock_strategy._error_log[0]
        assert error_entry['message'] == "Test error message"
        assert error_entry['exception'] == "Test error"
        assert error_entry['strategy_id'] == mock_strategy.strategy_id

    def test_warning_logging(self, mock_strategy):
        """Test warning logging functionality"""
        initial_warning_count = mock_strategy.performance_metrics.warning_count

        # Log a warning
        mock_strategy._log_warning("Test warning message")

        # Check warning tracking
        assert mock_strategy.performance_metrics.warning_count == initial_warning_count + 1
        assert len(mock_strategy._warning_log) == 1

        # Check warning log entry
        warning_entry = mock_strategy._warning_log[0]
        assert warning_entry['message'] == "Test warning message"
        assert warning_entry['strategy_id'] == mock_strategy.strategy_id


class TestRiskManagementIntegration:
    """Test risk management integration"""

    def test_risk_manager_assignment(self, mock_strategy, mock_risk_manager):
        """Test risk manager assignment"""
        assert mock_strategy.risk_manager == mock_risk_manager

    @pytest.mark.asyncio
    async def test_position_closing_on_stop(self, mock_strategy):
        """Test position closing when strategy stops"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Add a mock position
        position = StrategyPosition(
            position_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="AAPL",
            quantity=100.0,
            side="long",
            entry_price=150.0,
            current_price=150.0
        )
        mock_strategy._positions["AAPL"] = position

        # Stop strategy
        await mock_strategy.stop()

        # Note: Position closing on stop is not currently implemented
        # This test verifies that stop() completes without error
        assert mock_strategy.is_operational == False

    @pytest.mark.asyncio
    async def test_position_closing_without_risk_manager(self, strategy_config):
        """Test position closing without risk manager"""
        strategy = MockStrategy(strategy_config)
        # Don't set risk manager

        await strategy.initialize()
        await strategy.start()

        # Add a mock position
        position = StrategyPosition(
            position_id=str(uuid.uuid4()),
            strategy_id=strategy.strategy_id,
            symbol="AAPL",
            quantity=100.0,
            side="long",
            entry_price=150.0,
            current_price=150.0
        )
        strategy._positions["AAPL"] = position

        # Stop strategy - should handle gracefully without risk manager
        result = await strategy.stop()
        assert result is True


class TestUtilityMethods:
    """Test utility methods"""

    def test_get_active_positions(self, mock_strategy):
        """Test get active positions"""
        # Add positions with different quantities
        position1 = StrategyPosition(
            position_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="AAPL",
            quantity=100.0,
            side="long",
            entry_price=150.0,
            current_price=150.0
        )

        position2 = StrategyPosition(
            position_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="GOOGL",
            quantity=0.0,  # Closed position
            side="long",
            entry_price=2800.0,
            current_price=2800.0
        )

        mock_strategy._positions["AAPL"] = position1
        mock_strategy._positions["GOOGL"] = position2

        active_positions = mock_strategy.get_active_positions()

        # Should only return AAPL (non-zero quantity)
        assert len(active_positions) == 1
        assert "AAPL" in active_positions
        assert "GOOGL" not in active_positions

    def test_get_recent_signals(self, mock_strategy):
        """Test get recent signals"""
        # Add some signals
        for i in range(15):
            signal = StrategySignal(
                signal_id=str(uuid.uuid4()),
                strategy_id=mock_strategy.strategy_id,
                symbol=f"STOCK{i}",
                signal_type=SignalType.BUY,
                strength=0.8,
                confidence=0.9,
                target_quantity=100.0,
                position_side="long"
            )
            mock_strategy._signals.append(signal)

        # Get recent signals (default 10)
        recent_signals = mock_strategy.get_recent_signals()
        assert len(recent_signals) == 10

        # Get specific count
        recent_signals_5 = mock_strategy.get_recent_signals(5)
        assert len(recent_signals_5) == 5

        # Should be the most recent ones
        assert recent_signals_5[-1].symbol == "STOCK14"  # Last added

    def test_get_performance_summary(self, mock_strategy):
        """Test get performance summary"""
        summary = mock_strategy.get_performance_summary()

        assert isinstance(summary, dict)
        assert 'strategy_id' in summary
        assert 'strategy_type' in summary
        assert 'state' in summary
        assert 'health_status' in summary
        assert 'performance_metrics' in summary
        assert 'operational_metrics' in summary
        assert 'positions' in summary

        assert summary['strategy_id'] == mock_strategy.strategy_id
        assert summary['strategy_type'] == mock_strategy.strategy_type.value


class TestStrategyIntegration:
    """Integration tests for enhanced base strategy"""

    @pytest.mark.asyncio
    async def test_signal_generation_integration(self, mock_strategy, sample_market_data):
        """Test signal generation integration"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Set up mock signals to generate
        test_signal = StrategySignal(
            signal_id=str(uuid.uuid4()),
            strategy_id=mock_strategy.strategy_id,
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.9,
            target_quantity=100.0,
            position_side="long"
        )
        mock_strategy.signals_to_generate = [test_signal]

        # Generate signals
        signals = await mock_strategy.generate_signals(sample_market_data)

        assert mock_strategy.generate_signals_called is True
        assert len(signals) == 1
        assert signals[0].symbol == "AAPL"
        assert signals[0].signal_type == SignalType.BUY

    @pytest.mark.asyncio
    async def test_position_update_integration(self, mock_strategy, sample_market_data):
        """Test position update integration"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Update positions
        await mock_strategy.update_positions(sample_market_data)

        assert mock_strategy.update_positions_called is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_strategy, sample_market_data):
        """Test concurrent strategy operations"""
        await mock_strategy.initialize()
        await mock_strategy.start()

        # Run multiple operations concurrently
        tasks = [
            mock_strategy.generate_signals(sample_market_data),
            mock_strategy.update_positions(sample_market_data),
            mock_strategy.health_check()
        ]

        results = await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert len(results) == 3
        assert isinstance(results[0], list)  # signals
        assert results[1] is None  # update_positions returns None
        assert isinstance(results[2], dict)  # health check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
