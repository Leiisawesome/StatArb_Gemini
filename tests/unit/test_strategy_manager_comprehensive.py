"""
Comprehensive Unit Tests for StrategyManager - WORKING VERSION
"""

import pytest
import pytest_asyncio
import uuid
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Dict, List

from core_engine.trading.strategies.manager import (
    StrategyManager, StrategyManagerConfig, TradingSignal,
    SignalType, SignalStrength, StrategyAllocation
)
from core_engine.type_definitions.strategy import StrategyType
from core_engine.trading.strategies.base_strategy_enhanced import EnhancedBaseStrategy
from core_engine.trading.strategies.strategy_engine import StrategyConfig, StrategySignal


class WorkingMomentumStrategy(EnhancedBaseStrategy):
    """Working momentum strategy for testing"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.lookback_period = 20
        self.threshold = 0.02
    
    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        signals = []
        for symbol, data in market_data.items():
            if len(data) < self.lookback_period:
                continue
            
            current_price = data['close'].iloc[-1]
            past_price = data['close'].iloc[-self.lookback_period]
            momentum = (current_price - past_price) / past_price
            
            if abs(momentum) > self.threshold:
                signal_type = SignalType.BUY if momentum > 0 else SignalType.SELL
                signal = StrategySignal(
                    signal_id=str(uuid.uuid4()),
                    strategy_id=self.strategy_id,
                    strategy_type=StrategyType.MOMENTUM,
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=abs(momentum) * 10,
                    confidence=min(abs(momentum) / 0.1, 0.95),
                    expected_return=abs(momentum),
                    risk_score=abs(momentum) * 0.5,
                    quantity=100.0,
                    timestamp=datetime.now()
                )
                signals.append(signal)
        return signals
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        pass
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        return 100.0


@pytest.fixture
def strategy_manager_config():
    return {
        'max_concurrent_strategies': 10,
        'signal_generation_interval': 60,
        'min_confidence_threshold': 0.6,
        'max_strategy_allocation': 0.33,
        'enable_regime_awareness': True,
        'enable_correlation_filtering': True,
        'signal_aggregation_method': 'weighted_average',
        'enable_enhanced_strategies': False,
        'auto_discover_strategies': False,
        'enable_multi_strategy_coordination': True
    }


@pytest.fixture
def realistic_market_data():
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    market_data = {}
    for symbol in symbols:
        dates = pd.date_range(end=datetime.now(), periods=100, freq='1D')
        base_price = 100.0
        trend = np.linspace(0, 20, 100)
        noise = np.random.normal(0, 2, 100)
        close_prices = base_price + trend + noise
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices * 0.995,
            'high': close_prices * 1.01,
            'low': close_prices * 0.99,
            'close': close_prices,
            'volume': np.random.randint(1000000, 5000000, 100)
        })
        market_data[symbol] = df
    return market_data


@pytest.fixture
def mock_risk_manager():
    risk_manager = Mock()
    async def mock_authorize(request):
        authorization = Mock()
        authorization.decision = Mock(value='approve')
        authorization.authorized_quantity = request.quantity * 0.9
        authorization.reason = "Authorized"
        return authorization
    risk_manager.authorize_trade = AsyncMock(side_effect=mock_authorize)
    risk_manager.get_current_risk_metrics = Mock(return_value={'portfolio_var': 0.02})
    return risk_manager


@pytest.fixture
def mock_data_manager():
    data_manager = Mock()
    async def get_market_data(symbols, **kwargs):
        market_data = {}
        for symbol in symbols:
            dates = pd.date_range(end=datetime.now(), periods=50, freq='1D')
            prices = 100 + np.cumsum(np.random.normal(0.1, 1, 50))
            market_data[symbol] = pd.DataFrame({
                'timestamp': dates,
                'close': prices,
                'volume': np.random.randint(100000, 500000, 50)
            })
        return market_data
    data_manager.get_market_data = AsyncMock(side_effect=get_market_data)
    data_manager.get_current_price = Mock(return_value=105.0)
    return data_manager


@pytest.fixture
def mock_regime_engine():
    regime_engine = Mock()
    async def get_current_regime():
        regime = Mock()
        regime.primary_regime = 'normal_volatility'
        regime.confidence = 0.85
        regime.volatility = 0.015
        return regime
    regime_engine.get_current_regime = AsyncMock(side_effect=get_current_regime)
    return regime_engine


@pytest_asyncio.fixture
async def strategy_manager_with_strategies(strategy_manager_config, mock_risk_manager, 
                                          mock_data_manager, mock_regime_engine,
                                          realistic_market_data):
    manager = StrategyManager(strategy_manager_config)
    manager.set_risk_manager(mock_risk_manager)
    manager.set_data_manager(mock_data_manager)
    manager.set_regime_engine(mock_regime_engine)
    await manager.initialize()
    
    momentum_config = StrategyConfig(
        strategy_id="momentum_test",
        strategy_name="Test Momentum Strategy",
        strategy_type=StrategyType.MOMENTUM,
        required_symbols=['AAPL', 'GOOGL', 'MSFT'],
        max_position_size=0.1,
        paper_trading_mode=True
    )
    momentum_strategy = WorkingMomentumStrategy(momentum_config)
    await momentum_strategy.initialize()
    manager.active_strategies["momentum_test"] = momentum_strategy
    
    manager.strategy_allocations["momentum_test"] = StrategyAllocation(
        strategy_name="momentum_test",
        strategy_type=StrategyType.MOMENTUM,
        allocation_pct=0.3,
        max_positions=5,
        risk_limit=10000.0,
        active=True
    )
    
    for symbol, data in realistic_market_data.items():
        for strategy in manager.active_strategies.values():
            if hasattr(strategy, '_market_data'):
                strategy._market_data[symbol] = data
    
    return manager


class TestStrategyManagerLifecycle:
    @pytest.mark.asyncio
    async def test_initialization(self, strategy_manager_config):
        manager = StrategyManager(strategy_manager_config)
        result = await manager.initialize()
        assert result is True
        assert manager.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, strategy_manager_config, mock_risk_manager):
        manager = StrategyManager(strategy_manager_config)
        manager.set_risk_manager(mock_risk_manager)
        assert await manager.initialize() is True
        assert await manager.start() is True
        health = await manager.health_check()
        assert health['healthy'] is True
        assert await manager.stop() is True


class TestSignalGeneration:
    @pytest.mark.asyncio
    async def test_generate_signals(self, strategy_manager_with_strategies, realistic_market_data):
        manager = strategy_manager_with_strategies
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        signals = await manager.generate_signals(symbols=symbols)
        print(f"\n📊 Generated {len(signals)} signals")
        assert isinstance(signals, list)


class TestPerformance:
    @pytest.mark.asyncio
    async def test_signal_generation_speed(self, strategy_manager_with_strategies, realistic_market_data):
        manager = strategy_manager_with_strategies
        start_time = datetime.now()
        signals = await manager.generate_signals(symbols=['AAPL', 'GOOGL', 'MSFT'])
        duration = (datetime.now() - start_time).total_seconds()
        assert duration < 1.0
        print(f"\n⚡ Generated {len(signals)} signals in {duration:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
