"""
Centralized strategy fixtures for testing.

Provides reusable fixtures for strategy testing to avoid duplication
across test files.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Strategy imports
from core_engine.trading.strategies.enhanced_arbitrage import EnhancedArbitrageStrategy
from core_engine.trading.strategies.enhanced_breakout import EnhancedBreakoutStrategy
from core_engine.trading.strategies.enhanced_factor import EnhancedFactorStrategy
from core_engine.trading.strategies.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.trading.strategies.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.trading.strategies.enhanced_multi_asset import EnhancedMultiAssetStrategy
from core_engine.trading.strategies.enhanced_pairs_trading import EnhancedPairsTradingStrategy
from core_engine.trading.strategies.enhanced_statistical_arbitrage import EnhancedStatisticalArbitrageStrategy
from core_engine.trading.strategies.enhanced_trend_following import EnhancedTrendFollowingStrategy


@pytest.fixture
def sample_market_data():
    """
    Create sample market data for strategy testing.
    
    Consolidated fixture used across all strategy tests.
    Returns 200 days of synthetic market data with realistic characteristics.
    """
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    # Generate price series with trend and volatility
    returns = np.random.normal(0.0005, 0.02, 200)  # 0.05% daily return, 2% vol
    prices = 100 * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': ['AAPL'] * 200,
        'open': prices * (1 + np.random.uniform(-0.002, 0.002, 200)),
        'high': prices * (1 + np.random.uniform(0.001, 0.01, 200)),
        'low': prices * (1 + np.random.uniform(-0.01, -0.001, 200)),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 200),
        'returns': returns,
        'volatility': np.random.uniform(0.015, 0.025, 200)
    })
    
    return data


@pytest.fixture
def pairs_trading_strategy():
    """Create a configured EnhancedPairsTradingStrategy instance."""
    config = {
        'pair_symbols': ['AAPL', 'MSFT'],
        'lookback_period': 60,
        'entry_threshold': 2.0,
        'exit_threshold': 0.5,
        'stop_loss': 0.05,
        'max_position_size': 0.1,
        'hedge_ratio_window': 30,
    }
    
    strategy = EnhancedPairsTradingStrategy(config)
    return strategy


@pytest.fixture
def momentum_strategy():
    """Create a configured EnhancedMomentumStrategy instance."""
    config = {
        'lookback_period': 20,
        'momentum_threshold': 0.05,
        'signal_strength_threshold': 0.6,
        'position_size': 0.02,
        'stop_loss': 0.05,
        'take_profit': 0.10,
    }
    
    strategy = EnhancedMomentumStrategy(config)
    return strategy


@pytest.fixture
def mean_reversion_strategy():
    """Create a configured EnhancedMeanReversionStrategy instance."""
    config = {
        'lookback_period': 20,
        'entry_z_score': 2.0,
        'exit_z_score': 0.5,
        'position_size': 0.02,
        'stop_loss': 0.05,
    }
    
    strategy = EnhancedMeanReversionStrategy(config)
    return strategy


@pytest.fixture
def trend_following_strategy():
    """Create a configured EnhancedTrendFollowingStrategy instance."""
    config = {
        'fast_period': 10,
        'slow_period': 30,
        'signal_period': 9,
        'atr_period': 14,
        'position_size': 0.02,
        'stop_loss_multiplier': 2.0,
    }
    
    strategy = EnhancedTrendFollowingStrategy(config)
    return strategy


@pytest.fixture
def breakout_strategy():
    """Create a configured EnhancedBreakoutStrategy instance."""
    config = {
        'lookback_period': 20,
        'breakout_threshold': 0.02,
        'volume_confirmation': True,
        'position_size': 0.02,
        'stop_loss': 0.05,
    }
    
    strategy = EnhancedBreakoutStrategy(config)
    return strategy


@pytest.fixture
def factor_strategy():
    """Create a configured EnhancedFactorStrategy instance."""
    config = {
        'factors': ['value', 'momentum', 'quality'],
        'rebalance_frequency': 'monthly',
        'n_assets': 10,
        'position_size': 0.1,
    }
    
    strategy = EnhancedFactorStrategy(config)
    return strategy


@pytest.fixture
def multi_asset_strategy():
    """Create a configured EnhancedMultiAssetStrategy instance."""
    config = {
        'asset_classes': ['equity', 'fixed_income', 'commodity'],
        'allocation_method': 'risk_parity',
        'rebalance_frequency': 'monthly',
        'target_volatility': 0.10,
    }
    
    strategy = EnhancedMultiAssetStrategy(config)
    return strategy


@pytest.fixture
def arbitrage_strategy():
    """Create a configured EnhancedArbitrageStrategy instance."""
    config = {
        'symbols': ['AAPL', 'AAPL.L'],  # US and London listings
        'min_spread': 0.005,
        'transaction_cost': 0.001,
        'position_size': 0.05,
    }
    
    strategy = EnhancedArbitrageStrategy(config)
    return strategy


@pytest.fixture
def statistical_arbitrage_strategy():
    """Create a configured EnhancedStatisticalArbitrageStrategy instance."""
    config = {
        'universe': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],
        'lookback_period': 60,
        'entry_threshold': 2.0,
        'exit_threshold': 0.5,
        'max_pairs': 5,
    }
    
    strategy = EnhancedStatisticalArbitrageStrategy(config)
    return strategy


@pytest.fixture
def mock_risk_manager():
    """Create a mock risk manager for strategy testing."""
    mock_rm = Mock()
    mock_rm.check_position_limit = Mock(return_value=True)
    mock_rm.check_concentration_limit = Mock(return_value=True)
    mock_rm.calculate_position_size = Mock(return_value=0.02)
    mock_rm.get_portfolio_risk = Mock(return_value={'var': 0.02, 'sharpe': 1.5})
    return mock_rm


@pytest.fixture
def mock_execution_engine():
    """Create a mock execution engine for strategy testing."""
    mock_engine = AsyncMock()
    mock_engine.execute_order = AsyncMock(return_value={
        'status': 'filled',
        'fill_price': 100.0,
        'filled_quantity': 100,
        'timestamp': datetime.now()
    })
    mock_engine.cancel_order = AsyncMock(return_value=True)
    mock_engine.get_order_status = AsyncMock(return_value='filled')
    return mock_engine


@pytest.fixture
def mock_data_manager():
    """Create a mock data manager for strategy testing."""
    mock_dm = AsyncMock()
    
    # Default market data
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    
    default_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, 200)
    })
    
    mock_dm.get_historical_data = AsyncMock(return_value=default_data)
    mock_dm.get_latest_price = AsyncMock(return_value=100.0)
    mock_dm.get_market_data = AsyncMock(return_value=default_data)
    
    return mock_dm


@pytest.fixture
def strategy_test_config():
    """
    Provide a generic strategy configuration for testing.
    
    Can be customized per test as needed.
    """
    return {
        'lookback_period': 20,
        'signal_threshold': 0.5,
        'position_size': 0.02,
        'stop_loss': 0.05,
        'take_profit': 0.10,
        'max_positions': 10,
        'rebalance_frequency': 'daily',
        'enable_risk_management': True,
    }


@pytest.fixture
def multi_asset_market_data():
    """Create market data for multiple assets."""
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    data = {}
    
    for asset in assets:
        returns = np.random.normal(0.0005, 0.02, 200)
        prices = 100 * np.exp(np.cumsum(returns))
        
        data[asset] = pd.DataFrame({
            'timestamp': dates,
            'symbol': asset,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 200)
        })
    
    return data


@pytest.fixture
def correlated_pair_data():
    """Create correlated market data for pairs trading."""
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    np.random.seed(42)
    
    # Create correlated returns
    common_factor = np.random.randn(200) * 0.015
    idiosyncratic1 = np.random.randn(200) * 0.005
    idiosyncratic2 = np.random.randn(200) * 0.005
    
    returns1 = common_factor + idiosyncratic1
    returns2 = common_factor + idiosyncratic2
    
    prices1 = 100 * np.exp(np.cumsum(returns1))
    prices2 = 150 * np.exp(np.cumsum(returns2))
    
    return {
        'asset1': pd.DataFrame({
            'timestamp': dates,
            'symbol': 'AAPL',
            'close': prices1
        }),
        'asset2': pd.DataFrame({
            'timestamp': dates,
            'symbol': 'MSFT',
            'close': prices2
        })
    }
