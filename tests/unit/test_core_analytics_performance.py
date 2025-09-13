import pytest
import pandas as pd
import numpy as np
import asyncio

from core_structure.analytics.core_analytics import CoreAnalyticsEngine


@pytest.mark.asyncio
async def test_analyze_performance_basic_metrics():
    engine = CoreAnalyticsEngine(enable_ml=False)

    # create a simple returns series: 252 business days of small positive returns
    rng = pd.date_range(start="2024-01-01", periods=252, freq='B')
    returns = pd.Series(0.001, index=rng)

    metrics = await engine.analyze_performance(returns)

    # Basic sanity checks
    assert metrics.total_return > 0
    assert metrics.annualized_return > 0
    assert metrics.volatility >= 0
    assert 0 <= metrics.win_rate <= 1
    assert metrics.max_drawdown <= 0

    # Derived metrics
    assert metrics.var_95 <= 0.001


@pytest.mark.asyncio
async def test_analyze_performance_with_benchmark():
    engine = CoreAnalyticsEngine(enable_ml=False)

    rng = pd.date_range(start="2024-01-01", periods=252, freq='B')
    returns = pd.Series(np.random.normal(0.0005, 0.001, size=len(rng)), index=rng)
    benchmark = pd.Series(np.random.normal(0.0003, 0.0012, size=len(rng)), index=rng)

    metrics = await engine.analyze_performance(returns, benchmark_returns=benchmark)

    # beta and alpha should be numeric
    assert isinstance(metrics.beta, float)
    assert isinstance(metrics.alpha, float)
    assert isinstance(metrics.information_ratio, float)
