"""
Strategy Implementation Tests - Test Framework
================================================

Comprehensive test framework for all 10 enhanced strategy implementations.

Author: StatArb_Gemini Test Suite
Date: October 23, 2025
Version: 1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Import all strategy configs

# Import type definitions
from core_engine.type_definitions.strategy import TradingSignal
from core_engine.trading.strategies.strategy_engine import StrategyState, SignalType


class StrategyTestFixtures:
    """Common fixtures for strategy testing"""

    @staticmethod
    def create_mock_market_data(
        symbol: str = 'AAPL',
        days: int = 100,
        start_price: float = 100.0,
        trend: str = 'uptrend'
    ) -> pd.DataFrame:
        """Create realistic mock market data"""
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=days),
            end=datetime.now(),
            freq='1min'
        )

        num_points = len(dates)

        if trend == 'uptrend':
            # Upward trending prices with volatility
            trend_component = np.linspace(0, 20, num_points)
            noise = np.random.normal(0, 2, num_points)
            close_prices = start_price + trend_component + noise
        elif trend == 'downtrend':
            # Downward trending prices
            trend_component = np.linspace(0, -20, num_points)
            noise = np.random.normal(0, 2, num_points)
            close_prices = start_price + trend_component + noise
        elif trend == 'sideways':
            # Range-bound prices
            noise = np.random.normal(0, 3, num_points)
            close_prices = start_price + noise
        else:  # random
            close_prices = start_price + np.cumsum(np.random.normal(0, 1, num_points))

        # Ensure positive prices
        close_prices = np.maximum(close_prices, start_price * 0.5)

        # Create OHLCV data
        data = pd.DataFrame({
            'timestamp': dates,
            'symbol': symbol,
            'open': close_prices * (1 + np.random.uniform(-0.01, 0.01, num_points)),
            'high': close_prices * (1 + np.random.uniform(0, 0.02, num_points)),
            'low': close_prices * (1 + np.random.uniform(-0.02, 0, num_points)),
            'close': close_prices,
            'volume': np.random.randint(1000000, 10000000, num_points)
        })

        return data

    @staticmethod
    def create_mock_orchestrator() -> Mock:
        """Create mock orchestrator for testing"""
        orchestrator = Mock()
        orchestrator.register_component = Mock(return_value='test_component_id')
        orchestrator.get_component = Mock(return_value=None)
        return orchestrator

    @staticmethod
    def create_mock_regime_engine() -> Mock:
        """Create mock regime engine"""
        regime_engine = Mock()
        regime_engine.get_current_regime = AsyncMock(return_value={
            'primary_regime': 'normal_volatility',
            'volatility_regime': 'normal',
            'trend_regime': 'trending',
            'confidence': 0.8
        })
        return regime_engine

    @staticmethod
    def create_mock_risk_manager() -> Mock:
        """Create mock risk manager"""
        risk_manager = Mock()
        risk_manager.authorize_trade = AsyncMock(return_value={
            'authorized': True,
            'max_quantity': 100,
            'risk_score': 0.3
        })
        return risk_manager


@pytest.fixture
def market_data_uptrend():
    """Fixture for uptrending market data as Dict[str, DataFrame]

    Strategies expect enriched_data in Dict format: {symbol: DataFrame}
    """
    df = StrategyTestFixtures.create_mock_market_data(trend='uptrend')
    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'AAPL'
    return {symbol: df}


@pytest.fixture
def market_data_downtrend():
    """Fixture for downtrending market data as Dict[str, DataFrame]

    Strategies expect enriched_data in Dict format: {symbol: DataFrame}
    """
    df = StrategyTestFixtures.create_mock_market_data(trend='downtrend')
    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'AAPL'
    return {symbol: df}


@pytest.fixture
def market_data_sideways():
    """Fixture for sideways/range-bound market data as Dict[str, DataFrame]

    Strategies expect enriched_data in Dict format: {symbol: DataFrame}
    """
    df = StrategyTestFixtures.create_mock_market_data(trend='sideways')
    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'AAPL'
    return {symbol: df}


@pytest.fixture
def mock_orchestrator():
    """Fixture for mock orchestrator"""
    return StrategyTestFixtures.create_mock_orchestrator()


@pytest.fixture
def mock_regime_engine():
    """Fixture for mock regime engine"""
    return StrategyTestFixtures.create_mock_regime_engine()


@pytest.fixture
def mock_risk_manager():
    """Fixture for mock risk manager"""
    return StrategyTestFixtures.create_mock_risk_manager()


class BaseStrategyTest:
    """Base class for strategy testing"""

    async def verify_strategy_initialization(self, strategy, config):
        """Common initialization tests"""
        assert strategy is not None
        assert strategy.config == config
        assert strategy.state == StrategyState.INACTIVE
        assert not strategy.is_initialized
        assert not strategy.is_operational

    async def verify_strategy_lifecycle(self, strategy):
        """Test strategy lifecycle management"""
        # Initialize
        result = await strategy.initialize()
        assert result is True
        assert strategy.is_initialized is True

        # Start
        result = await strategy.start()
        assert result is True
        assert strategy.is_operational is True
        assert strategy.state in [StrategyState.ACTIVE, StrategyState.RUNNING]

        # Health check
        health = await strategy.health_check()
        assert health is not None
        assert 'healthy' in health
        assert health['healthy'] is True

        # Status
        status = strategy.get_status()
        assert status is not None
        assert 'state' in status
        assert 'initialized' in status

        # Stop
        result = await strategy.stop()
        assert result is True
        assert strategy.is_operational is False

    async def verify_signal_generation(self, strategy, market_data, expected_signal_type=None):
        """Test signal generation"""
        signals = await strategy.generate_signals(market_data)

        # Verify signals structure
        assert signals is not None
        assert isinstance(signals, list)

        if len(signals) > 0:
            signal = signals[0]
            assert hasattr(signal, 'symbol')
            assert hasattr(signal, 'signal_type')
            assert hasattr(signal, 'confidence')
            assert hasattr(signal, 'timestamp')

            # Verify signal type if expected
            if expected_signal_type:
                assert signal.signal_type == expected_signal_type

            # Verify confidence is in valid range
            assert 0 <= signal.confidence <= 1.0

        return signals

    async def verify_regime_awareness(self, strategy, regime_engine):
        """Test regime awareness"""
        # Set regime engine
        strategy.set_regime_engine(regime_engine)
        assert strategy.regime_engine is not None

        # Verify regime context access
        strategy.get_current_regime_context()
        # May be None initially, which is okay

        # Test regime change handling
        from core_engine.system.interfaces import RegimeContext

        new_regime = RegimeContext(
            primary_regime='high_volatility',
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=10.0
        )

        # Should not raise exception
        await strategy.on_regime_change(new_regime)

        # Verify validation
        is_valid = strategy.validate_regime_dependency()
        assert isinstance(is_valid, bool)


# Helper functions for test assertions
def assert_valid_signal(signal: TradingSignal):
    """Assert signal has valid structure and values"""
    assert signal is not None
    assert signal.symbol is not None
    assert signal.signal_type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    assert 0 <= signal.confidence <= 1.0
    assert signal.timestamp is not None


def assert_strategy_performance_metrics(metrics: Dict[str, Any]):
    """Assert performance metrics are valid"""
    assert 'total_signals' in metrics
    assert 'successful_signals' in metrics
    assert metrics['total_signals'] >= 0
    assert metrics['successful_signals'] >= 0
    assert metrics['successful_signals'] <= metrics['total_signals']

