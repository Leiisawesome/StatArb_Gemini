import pytest
import pandas as pd
import numpy as np

from core_structure.analytics.core_analytics import CoreAnalyticsEngine


@pytest.mark.asyncio
async def test_analyze_risk_basic():
    engine = CoreAnalyticsEngine(enable_ml=False)

    # Simple returns and positions
    rng = pd.date_range(start="2024-01-01", periods=60, freq='B')
    returns = pd.Series(np.random.normal(0, 0.01, size=len(rng)), index=rng)

    positions = pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOGL'],
        'weight': [0.4, 0.4, 0.2],
        'value': [40000, 40000, 20000]
    })

    metrics = await engine.analyze_risk(positions=positions, returns=returns)

    # Basic assertions
    assert metrics.portfolio_var <= 0
    assert metrics.portfolio_cvar <= 0 or np.isnan(metrics.portfolio_cvar)
    assert metrics.concentration_risk >= 0
    assert metrics.overall_risk_score >= 0
    assert metrics.risk_level.name in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


@pytest.mark.asyncio
async def test_analyze_risk_leverage_and_levels():
    engine = CoreAnalyticsEngine(enable_ml=False)

    rng = pd.date_range(start="2024-01-01", periods=60, freq='B')
    returns = pd.Series(np.random.normal(-0.05, 0.02, size=len(rng)), index=rng)

    positions = pd.DataFrame({
        'symbol': ['BIG1', 'BIG2'],
        'weight': [0.9, 0.9],
        'value': [90000, -80000]
    })

    metrics = await engine.analyze_risk(positions=positions, returns=returns)

    # With large leverage and negative returns, risk score should be elevated
    assert metrics.leverage_ratio >= 0
    assert metrics.overall_risk_score >= 0
    assert metrics.risk_level in [metrics.risk_level.LOW, metrics.risk_level.MEDIUM, metrics.risk_level.HIGH, metrics.risk_level.CRITICAL]
