"""
Unit tests for the performance metrics calculation logic.
"""
import pytest
import pandas as pd
import numpy as np
from evaluation.metrics import calculate_metrics
from structs import Config

@pytest.fixture
def sample_config():
    """Provides a sample config object for tests."""
    from config import CONFIG_DICT
    test_config = CONFIG_DICT.copy()
    test_config['data_interval'] = '5m'
    return Config(**test_config)

def test_metrics_no_trades(sample_config):
    """Tests metrics calculation with an empty trade log."""
    trade_log = pd.DataFrame(columns=['pnl', 'entry_date', 'exit_date'])
    metrics = calculate_metrics(trade_log, sample_config)
    assert metrics['Total Trades'] == 0
    assert metrics['Total PnL'] == 0
    assert metrics['Annualized Sharpe Ratio'] == 0

def test_metrics_all_wins(sample_config):
    """Tests metrics with only winning trades."""
    trades = [
        {'pnl': 100, 'entry_date': '2023-01-02T09:30:00', 'exit_date': '2023-01-02T10:30:00'},
        {'pnl': 200, 'entry_date': '2023-01-03T11:00:00', 'exit_date': '2023-01-03T12:00:00'},
    ]
    trade_log = pd.DataFrame(trades)
    trade_log['entry_date'] = pd.to_datetime(trade_log['entry_date'])
    trade_log['exit_date'] = pd.to_datetime(trade_log['exit_date'])
    
    metrics = calculate_metrics(trade_log, sample_config)
    assert metrics['Total Trades'] == 2
    assert metrics['Total PnL'] == pytest.approx(300)
    assert metrics['Win Rate'] == 1.0
    assert metrics['Profit Factor'] == np.inf
    assert metrics['Max Drawdown'] == 0

def test_metrics_mixed_trades(sample_config):
    """Tests metrics with a mix of winning and losing trades."""
    trades = [
        {'pnl': 150, 'entry_date': '2023-01-02T09:30:00', 'exit_date': '2023-01-02T10:30:00'},
        {'pnl': -50, 'entry_date': '2023-01-03T11:00:00', 'exit_date': '2023-01-03T12:00:00'},
        {'pnl': 200, 'entry_date': '2023-01-04T13:00:00', 'exit_date': '2023-01-04T14:00:00'},
        {'pnl': -100, 'entry_date': '2023-01-05T15:00:00', 'exit_date': '2023-01-05T16:00:00'},
    ]
    trade_log = pd.DataFrame(trades)
    trade_log['entry_date'] = pd.to_datetime(trade_log['entry_date'])
    trade_log['exit_date'] = pd.to_datetime(trade_log['exit_date'])
    
    metrics = calculate_metrics(trade_log, sample_config)
    assert metrics['Total Trades'] == 4
    assert metrics['Total PnL'] == pytest.approx(200)
    assert metrics['Win Rate'] == 0.5
    assert metrics['Profit Factor'] == pytest.approx(350 / 150) # 2.33
    assert metrics['Max Drawdown'] == pytest.approx(100)
    assert metrics['Calmar Ratio'] == pytest.approx(200 / 100) 