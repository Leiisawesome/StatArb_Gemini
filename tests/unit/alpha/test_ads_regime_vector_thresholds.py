import math

from core_engine.alpha.ads_regime_vector import ADSRegimeVector, compute_erar_gamma, compute_sms_tau


def test_from_regime_context_none_defaults_are_conservative_and_flagged():
    r, diag = ADSRegimeVector.from_regime_context(None)
    assert "regime_context_missing" in (diag.get("used") or [])
    assert math.isclose(r.volatility, 0.5)
    assert math.isclose(r.trend, 0.0)
    assert 0.0 <= r.liquidity <= 1.0
    assert 0.0 <= r.microstructure <= 1.0


def test_from_regime_context_with_volatility_regimes():
    """Test different volatility regime mappings."""
    # High volatility
    class MockRegime:
        def __init__(self, vol_regime):
            self.volatility_regime = vol_regime
            self.regime_confidence = 0.8

    r_high, _ = ADSRegimeVector.from_regime_context(MockRegime("high_volatility"))
    assert math.isclose(r_high.volatility, 0.8)

    r_extreme, _ = ADSRegimeVector.from_regime_context(MockRegime("extreme_volatility"))
    assert math.isclose(r_extreme.volatility, 1.0)

    r_crisis, _ = ADSRegimeVector.from_regime_context(MockRegime("crisis"))
    assert math.isclose(r_crisis.volatility, 1.0)

    r_low, _ = ADSRegimeVector.from_regime_context(MockRegime("low_volatility"))
    assert math.isclose(r_low.volatility, 0.2)

    r_normal, _ = ADSRegimeVector.from_regime_context(MockRegime("normal_volatility"))
    assert math.isclose(r_normal.volatility, 0.5)


def test_from_regime_context_with_trend_regimes():
    """Test different trend regime mappings."""
    class MockRegime:
        def __init__(self, trend_regime):
            self.trend_regime = trend_regime
            self.regime_confidence = 0.8

    r_strong_up, _ = ADSRegimeVector.from_regime_context(MockRegime("strong_up"))
    assert math.isclose(r_strong_up.trend, 1.0)

    r_weak_up, _ = ADSRegimeVector.from_regime_context(MockRegime("weak_up"))
    assert math.isclose(r_weak_up.trend, 0.5)

    r_strong_down, _ = ADSRegimeVector.from_regime_context(MockRegime("strong_down"))
    assert math.isclose(r_strong_down.trend, -1.0)

    r_weak_down, _ = ADSRegimeVector.from_regime_context(MockRegime("weak_down"))
    assert math.isclose(r_weak_down.trend, -0.5)

    r_sideways, _ = ADSRegimeVector.from_regime_context(MockRegime("sideways"))
    assert math.isclose(r_sideways.trend, 0.0)


def test_from_regime_context_with_liquidity_and_microstructure():
    """Test liquidity and microstructure parameter handling."""
    class MockRegime:
        def __init__(self):
            self.regime_confidence = 0.8

    r, diag = ADSRegimeVector.from_regime_context(MockRegime(), liquidity=0.3, microstructure=0.7)
    assert math.isclose(r.liquidity, 0.3)
    assert math.isclose(r.microstructure, 0.7)
    assert "liquidity_missing_defaulted" not in diag.get("used", [])
    assert "microstructure_missing_defaulted" not in diag.get("used", [])


def test_from_regime_context_missing_liquidity_defaults():
    """Test default values when liquidity/microstructure not provided."""
    class MockRegime:
        def __init__(self):
            self.regime_confidence = 0.8

    r, diag = ADSRegimeVector.from_regime_context(MockRegime())
    assert math.isclose(r.liquidity, 0.6)
    assert math.isclose(r.microstructure, 0.6)
    assert "liquidity_missing_defaulted" in diag.get("used", [])
    assert "microstructure_missing_defaulted" in diag.get("used", [])


def test_from_regime_context_with_previous_vector():
    """Test velocity calculations with previous vector."""
    class MockRegime:
        def __init__(self):
            self.regime_confidence = 0.8
            self.volatility_regime = "high_volatility"

    prev = ADSRegimeVector(volatility=0.5, trend=0.0, liquidity=0.6, microstructure=0.6)
    curr, _ = ADSRegimeVector.from_regime_context(MockRegime(), prev=prev, ewma_alpha=0.3)

    # Should have velocity components
    assert hasattr(curr, 'd_volatility')
    assert hasattr(curr, 'd_trend')
    assert hasattr(curr, 'd_liquidity')
    assert hasattr(curr, 'd_microstructure')

    # Volatility should have increased (0.5 -> 0.8), so d_volatility should be positive
    assert curr.d_volatility > 0


def test_from_regime_context_missing_confidence():
    """Test handling of missing confidence."""
    class MockRegime:
        def __init__(self):
            self.volatility_regime = "normal_volatility"
            self.regime_confidence = None  # explicitly None to trigger fallback

    r, diag = ADSRegimeVector.from_regime_context(MockRegime())
    assert math.isclose(r.confidence, 0.5)  # default
    assert "regime_confidence_missing" in diag.get("used", [])


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

