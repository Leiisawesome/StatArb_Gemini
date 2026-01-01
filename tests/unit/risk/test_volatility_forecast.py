import math

from core_engine.risk.volatility_forecast import (
    ewma_volatility,
    realized_volatility,
    sigma_eff,
    stop_distance_pct,
    VolStopParams,
)


def test_sigma_eff_is_non_negative_and_max_of_components():
    returns = [0.01, -0.02, 0.015, -0.01, 0.005, 0.0, 0.01]
    s_eff, s_real, s_fcst = sigma_eff(returns, realized_window=5, lambda_=0.94)
    assert s_eff >= 0.0
    assert s_real >= 0.0
    assert s_fcst >= 0.0
    assert s_eff == max(s_real, s_fcst)


def test_stop_distance_pct_behaves_reasonably():
    # With 2% vol, k=2 => ~4% baseline stop (ignoring corr penalty)
    sl = stop_distance_pct(0.02, delta_rho=0.0, params=VolStopParams(k=2.0, kappa=0.5, overnight_mult=1.5))
    assert sl > 0.0
    assert math.isfinite(sl)
    assert 0.02 < sl < 0.10


