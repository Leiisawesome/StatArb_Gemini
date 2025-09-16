import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_structure.analytics.research_analytics import ResearchAnalyticsEngine, BacktestMode


def simple_momentum_strategy(data: pd.DataFrame, threshold: float = 0.0):
    # Simple strategy: go long when close > previous close, else neutral
    returns = data['close'].pct_change().fillna(0)
    signals = (returns > threshold).astype(int)
    return signals


@pytest.mark.asyncio
async def test_generate_signals_and_vectorized_backtest():
    engine = ResearchAnalyticsEngine(enable_ai_insights=False)

    # Create sample price data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='B')
    prices = np.linspace(100, 120, len(dates)) + np.random.normal(0, 1, len(dates))
    data = pd.DataFrame({'close': prices}, index=dates)

    # Test signal generation
    signals = await engine._generate_signals(simple_momentum_strategy, data, {})
    assert isinstance(signals, pd.Series)
    assert len(signals) == len(data)

    # Run a small vectorized backtest
    result = await engine._run_vectorized_backtest(signals, data, capital=100000, strategy_name='SM', params={})
    assert result.total_trades >= 0
    assert isinstance(result.total_return, float)
    assert isinstance(result.sharpe_ratio, float)
    assert result.final_value >= 0
