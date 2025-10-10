"""
Data Fixtures - Test Data Generators
====================================

Fixtures for generating test market data, signals, positions, and other data structures.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType
from core_engine.system.unified_execution_engine import ExecutionAuthorization, ExecutionRequest, ExecutionAlgorithm, ExecutionUrgency


# ========================================
# MARKET DATA FIXTURES
# ========================================

@pytest.fixture
def sample_market_data() -> Dict[str, pd.DataFrame]:
    """Generate sample market data for testing"""
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    market_data = {}
    
    # Generate 100 days of data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    
    for symbol in symbols:
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 102 + np.random.randn(100).cumsum(),
            'low': 98 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000000, 10000000, 100),
            'symbol': symbol
        })
        data['close'] = data['close'].clip(lower=50)  # Prevent negative prices
        market_data[symbol] = data.set_index('timestamp')
    
    return market_data


@pytest.fixture
def sample_intraday_data() -> pd.DataFrame:
    """Generate sample intraday data"""
    timestamps = pd.date_range(
        start=datetime.now().replace(hour=9, minute=30),
        periods=390,  # Full trading day (6.5 hours)
        freq='1min'
    )
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': 100 + np.random.randn(390).cumsum() * 0.1,
        'high': 100.5 + np.random.randn(390).cumsum() * 0.1,
        'low': 99.5 + np.random.randn(390).cumsum() * 0.1,
        'close': 100 + np.random.randn(390).cumsum() * 0.1,
        'volume': np.random.randint(1000, 50000, 390),
        'symbol': 'AAPL'
    }).set_index('timestamp')


@pytest.fixture
def sample_returns_series() -> pd.Series:
    """Generate sample returns series"""
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')  # 1 year
    returns = np.random.randn(252) * 0.01  # 1% daily volatility
    return pd.Series(returns, index=dates)


# ========================================
# SIGNAL FIXTURES
# ========================================

@pytest.fixture
def sample_signals() -> List[StrategySignal]:
    """Generate sample trading signals"""
    signals = []
    
    for i, symbol in enumerate(['AAPL', 'GOOGL', 'MSFT']):
        signal = StrategySignal(
            signal_id=f'signal_{i}',
            strategy_id='test_strategy',
            timestamp=datetime.now(),
            symbol=symbol,
            signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
            confidence=0.7 + (i * 0.05),
            strength=0.6 + (i * 0.1),
            target_quantity=100.0 * (i + 1),
            position_side='long' if i % 2 == 0 else 'short',
            signal_price=100.0 + i * 10,
            signal_source='test_strategy',
            signal_reason='Test signal generation'
        )
        signals.append(signal)
    
    return signals


@pytest.fixture
def high_confidence_signal() -> StrategySignal:
    """Generate a high-confidence signal"""
    return StrategySignal(
        signal_id='high_conf_signal',
        strategy_id='momentum_strategy',
        timestamp=datetime.now(),
        symbol='AAPL',
        signal_type=SignalType.BUY,
        confidence=0.9,
        strength=0.85,
        target_quantity=200.0,
        position_side='long',
        signal_price=150.0,
        entry_price=150.0,
        stop_loss=145.0,
        take_profit=160.0,
        signal_source='momentum_strategy',
        signal_reason='Strong momentum breakout'
    )


@pytest.fixture
def low_confidence_signal() -> StrategySignal:
    """Generate a low-confidence signal"""
    return StrategySignal(
        signal_id='low_conf_signal',
        strategy_id='mean_reversion_strategy',
        timestamp=datetime.now(),
        symbol='GOOGL',
        signal_type=SignalType.SELL,
        confidence=0.5,
        strength=0.4,
        target_quantity=50.0,
        position_side='short',
        signal_price=120.0,
        signal_source='mean_reversion_strategy',
        signal_reason='Weak mean reversion signal'
    )


# ========================================
# POSITION FIXTURES
# ========================================

@pytest.fixture
def sample_positions() -> Dict[str, Dict[str, Any]]:
    """Generate sample position data"""
    return {
        'AAPL': {
            'symbol': 'AAPL',
            'quantity': 100.0,
            'side': 'long',
            'entry_price': 150.0,
            'current_price': 155.0,
            'unrealized_pnl': 500.0,
            'entry_time': datetime.now() - timedelta(days=5)
        },
        'GOOGL': {
            'symbol': 'GOOGL',
            'quantity': -50.0,
            'side': 'short',
            'entry_price': 120.0,
            'current_price': 118.0,
            'unrealized_pnl': 100.0,
            'entry_time': datetime.now() - timedelta(days=2)
        },
        'MSFT': {
            'symbol': 'MSFT',
            'quantity': 200.0,
            'side': 'long',
            'entry_price': 300.0,
            'current_price': 305.0,
            'unrealized_pnl': 1000.0,
            'entry_time': datetime.now() - timedelta(days=10)
        }
    }


# ========================================
# EXECUTION FIXTURES
# ========================================

@pytest.fixture
def sample_execution_authorization() -> ExecutionAuthorization:
    """Generate sample execution authorization"""
    return ExecutionAuthorization(
        authorization_id='auth_123',
        risk_manager_id='risk_manager_1',
        symbol='AAPL',
        side='buy',
        quantity=100.0,
        max_quantity=150.0,
        price_limit=155.0,
        max_position_impact=0.05,
        max_market_impact=0.01,
        max_execution_time=3600,
        strategy_id='test_strategy',
        risk_budget_allocation=10000.0,
        allowed_algorithms=[ExecutionAlgorithm.TWAP, ExecutionAlgorithm.ADAPTIVE],
        urgency_level=ExecutionUrgency.NORMAL,
        is_valid=True
    )


@pytest.fixture
def sample_execution_request(sample_execution_authorization) -> ExecutionRequest:
    """Generate sample execution request"""
    return ExecutionRequest(
        request_id='req_123',
        authorization=sample_execution_authorization,
        algorithm=ExecutionAlgorithm.TWAP,
        urgency=ExecutionUrgency.NORMAL,
        time_horizon=300,
        max_participation_rate=0.20,
        min_fill_size=10,
        max_slice_size=50
    )


# ========================================
# PERFORMANCE DATA FIXTURES
# ========================================

@pytest.fixture
def sample_performance_data() -> Dict[str, Any]:
    """Generate sample performance metrics"""
    return {
        'returns': pd.Series(np.random.randn(252) * 0.01),
        'total_return': 0.15,
        'annualized_return': 0.12,
        'volatility': 0.15,
        'sharpe_ratio': 1.5,
        'sortino_ratio': 2.0,
        'max_drawdown': -0.10,
        'win_rate': 0.65,
        'profit_factor': 2.5,
        'average_win': 0.02,
        'average_loss': -0.01,
        'total_trades': 100,
        'winning_trades': 65,
        'losing_trades': 35
    }


# ========================================
# RISK DATA FIXTURES
# ========================================

@pytest.fixture
def sample_risk_metrics() -> Dict[str, float]:
    """Generate sample risk metrics"""
    return {
        'portfolio_var': 0.025,
        'portfolio_cvar': 0.035,
        'concentration_risk': 0.15,
        'total_exposure': 0.75,
        'gross_leverage': 1.2,
        'net_leverage': 0.8,
        'beta_to_market': 0.9,
        'correlation_to_spy': 0.75
    }


# ========================================
# REGIME DATA FIXTURES
# ========================================

@pytest.fixture
def sample_regime_data() -> Dict[str, Any]:
    """Generate sample regime data"""
    return {
        'primary_regime': 'normal_volatility',
        'regime_confidence': 0.85,
        'market_volatility': 0.15,
        'trend_direction': 'bullish',
        'regime_stability': 0.8,
        'time_in_regime': 45,  # days
        'regime_history': [
            {'regime': 'low_volatility', 'duration': 30, 'end_date': datetime.now() - timedelta(days=45)},
            {'regime': 'normal_volatility', 'duration': 45, 'end_date': datetime.now()}
        ]
    }


# ========================================
# ORDER BOOK FIXTURES
# ========================================

@pytest.fixture
def sample_order_book() -> Dict[str, List[tuple]]:
    """Generate sample order book data"""
    return {
        'bids': [
            (100.00, 1000),
            (99.95, 2000),
            (99.90, 1500),
            (99.85, 3000),
            (99.80, 2500)
        ],
        'asks': [
            (100.05, 1200),
            (100.10, 1800),
            (100.15, 2200),
            (100.20, 2800),
            (100.25, 2000)
        ],
        'timestamp': datetime.now(),
        'symbol': 'AAPL'
    }
