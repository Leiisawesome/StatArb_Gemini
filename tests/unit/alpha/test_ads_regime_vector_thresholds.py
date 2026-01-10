import math

from core_engine.alpha.ads_regime_vector import ADSRegimeVector, compute_erar_gamma, compute_sms_tau


def test_from_regime_context_none_defaults_are_conservative_and_flagged():
    r, diag = ADSRegimeVector.from_regime_context(None)
    assert "regime_context_missing" in (diag.get("used") or [])
    assert math.isclose(r.volatility, 0.5)
    assert math.isclose(r.trend, 0.0)
    assert 0.0 <= r.liquidity <= 1.0
    assert 0.0 <= r.microstructure <= 1.0


def test_compute_sms_tau_is_bounded():
    r = ADSRegimeVector(
        volatility=1.0,
        trend=-1.0,
        liquidity=0.0,
        microstructure=0.0,
        d_volatility=1.0,
        d_trend=-1.0,
        confidence=0.0,
    )
    tau = compute_sms_tau(r, tau_0=0.50, ofi_proxy_used=True, bb_missing=True, direction="long")
    assert 0.35 <= tau <= 0.80


def test_compute_sms_tau_direction_headwind_only_matters_with_vol_accel():
    # With zero vol acceleration, trend penalties should not bite (selective loosening).
    r = ADSRegimeVector(
        volatility=0.8,
        trend=-1.0,
        liquidity=0.8,
        microstructure=0.8,
        d_volatility=0.0,
        d_trend=-1.0,
        confidence=0.8,
    )
    tau_long = compute_sms_tau(r, tau_0=0.50, direction="long")
    tau_short = compute_sms_tau(r, tau_0=0.50, direction="short")
    assert math.isclose(tau_long, tau_short, rel_tol=1e-9, abs_tol=1e-12)


def test_compute_sms_tau_penalizes_downtrend_for_longs_when_vol_is_accelerating():
    r = ADSRegimeVector(
        volatility=0.8,
        trend=-1.0,        # downtrend headwind for longs
        liquidity=0.8,
        microstructure=0.8,
        d_volatility=0.6,  # acceleration -> penalties active
        d_trend=-1.0,
        confidence=0.8,
    )
    tau_long = compute_sms_tau(r, tau_0=0.50, direction="long")
    tau_short = compute_sms_tau(r, tau_0=0.50, direction="short")
    assert tau_long > tau_short


def test_compute_erar_gamma_is_bounded_and_increases_with_volatility():
    r_low = ADSRegimeVector(
        volatility=0.2,
        trend=0.0,
        liquidity=0.8,
        microstructure=0.8,
        d_volatility=0.0,
        confidence=1.0,
    )
    r_high = ADSRegimeVector(
        volatility=1.0,
        trend=0.0,
        liquidity=0.8,
        microstructure=0.8,
        d_volatility=0.5,
        confidence=1.0,
    )

    g_low = compute_erar_gamma(r_low, gamma_0=0.50, direction="long")
    g_high = compute_erar_gamma(r_high, gamma_0=0.50, direction="long")

    assert 0.30 <= g_low <= 1.20
    assert 0.30 <= g_high <= 1.20
    assert g_high > g_low

