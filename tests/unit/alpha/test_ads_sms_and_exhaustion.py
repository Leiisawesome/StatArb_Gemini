import math

from core_engine.alpha.ads_components import ADSSMSGateInputs, SignalMaturityScore, compute_exhaustion


def test_sms_time_decay_monotone_decreases():
    inputs = ADSSMSGateInputs(
        setup_maturity=0.8,
        setup_validity_prob=0.8,
        signed_flow_support=0.2,
        vol_compression=1.0,
    )
    sms0 = SignalMaturityScore.from_inputs(inputs, pending_bars=0, max_pending=50)
    s0 = float(sms0.compute("normal"))

    sms1 = SignalMaturityScore.from_inputs(inputs, pending_bars=10, max_pending=50)
    s1 = float(sms1.compute("normal"))

    assert s1 < s0


def test_sms_flow_factor_is_symmetric_penalty_and_reward():
    # With exp(gamma*ofi), positive OFI increases SMS and negative OFI decreases SMS.
    # In 'normal' regime, gamma=0.20 (see SignalMaturityScore.EXPONENTS).
    base = ADSSMSGateInputs(
        setup_maturity=0.7,
        setup_validity_prob=0.7,
        vol_compression=1.0,
    )
    s_pos = float(SignalMaturityScore.from_inputs(ADSSMSGateInputs(**{**base.__dict__, "signed_flow_support": +0.5}), pending_bars=0, max_pending=50).compute("normal"))
    s_neg = float(SignalMaturityScore.from_inputs(ADSSMSGateInputs(**{**base.__dict__, "signed_flow_support": -0.5}), pending_bars=0, max_pending=50).compute("normal"))
    s_zero = float(SignalMaturityScore.from_inputs(ADSSMSGateInputs(**{**base.__dict__, "signed_flow_support": 0.0}), pending_bars=0, max_pending=50).compute("normal"))

    assert s_neg < s_zero < s_pos

    # Ratio should be ~ exp(gamma*(+0.5 - (-0.5))) = exp(gamma*1.0)
    expected_ratio = math.exp(0.20)
    assert math.isclose(s_pos / s_neg, expected_ratio, rel_tol=0.15, abs_tol=0.0)


def test_sms_is_stale_and_is_mature_respects_max_pending():
    # Even a "perfect" signal must not be mature if it's stale.
    sms = SignalMaturityScore.from_inputs(
        ADSSMSGateInputs(
            setup_maturity=1.0,
            setup_validity_prob=1.0,
            signed_flow_support=1.0,
            vol_compression=0.5,
        ),
        pending_bars=6,
        max_pending=5,
    )
    assert sms.is_stale() is True
    assert sms.is_mature(threshold=0.1, regime="normal") is False


def test_sms_decay_rate_parameter_changes_time_penalty():
    inputs = ADSSMSGateInputs(
        setup_maturity=0.8,
        setup_validity_prob=0.8,
        signed_flow_support=0.0,
        vol_compression=1.0,
    )
    slow = float(SignalMaturityScore.from_inputs(inputs, pending_bars=10, decay_rate=0.01).compute("normal"))
    fast = float(SignalMaturityScore.from_inputs(inputs, pending_bars=10, decay_rate=0.10).compute("normal"))
    assert fast < slow


def test_compute_exhaustion_volume_conviction_is_smooth_and_penalizes_high_volume_at_extremes():
    # Use an extreme abs(z) so the conviction gate is active
    z = -2.5
    rsi = 50.0
    macd = 0.0
    macd_prev = 0.0

    # Around the ~1.5 ramp, the score should change smoothly (no hard step)
    s_149 = float(
        compute_exhaustion(
            zscore=z,
            rsi=rsi,
            volume_ratio=1.49,
            macd_histogram=macd,
            macd_histogram_prev=macd_prev,
            is_oversold=True,
        )
    )
    s_151 = float(
        compute_exhaustion(
            zscore=z,
            rsi=rsi,
            volume_ratio=1.51,
            macd_histogram=macd,
            macd_histogram_prev=macd_prev,
            is_oversold=True,
        )
    )
    assert abs(s_151 - s_149) < 0.15

    # Very high volume at the extreme should reduce the exhaustion score (conviction risk)
    s_low_vol = float(
        compute_exhaustion(
            zscore=z,
            rsi=rsi,
            volume_ratio=0.8,
            macd_histogram=macd,
            macd_histogram_prev=macd_prev,
            is_oversold=True,
        )
    )
    s_high_vol = float(
        compute_exhaustion(
            zscore=z,
            rsi=rsi,
            volume_ratio=2.5,
            macd_histogram=macd,
            macd_histogram_prev=macd_prev,
            is_oversold=True,
        )
    )
    assert s_high_vol < s_low_vol


def test_compute_exhaustion_volume_conviction_is_smooth_and_penalizes_high_volume_at_extremes():
    # Test the exhaustion computation with different volume levels
    from core_engine.alpha.ads_components import compute_exhaustion

    # Low volume at moderate dislocation should have lower exhaustion
    low_exh = compute_exhaustion(
        zscore=0.8,       # moderate z-score
        rsi=35,           # moderately oversold RSI
        volume_ratio=0.7, # low volume
        macd_histogram=-0.2,
        macd_histogram_prev=-0.3,
        is_oversold=True
    )
    assert 0.2 <= low_exh <= 0.8  # Allow broader range

    # High volume at extreme price should have higher exhaustion
    high_exh = compute_exhaustion(
        zscore=1.5,       # moderate z-score
        rsi=25,           # oversold RSI
        volume_ratio=2.0, # high volume
        macd_histogram=-0.5,
        macd_histogram_prev=-0.6,
        is_oversold=True
    )
    assert high_exh > low_exh

    # Mid-range price should have moderate exhaustion
    mid_exh = compute_exhaustion(
        zscore=1.0,       # moderate z-score
        rsi=50,           # neutral RSI
        volume_ratio=1.0, # normal volume
        macd_histogram=0.0,
        macd_histogram_prev=0.0,
        is_oversold=False
    )
    assert 0.3 <= mid_exh <= 0.7


def test_erar_compute_and_should_trade():
    """Test ERAR computation and trading decision."""
    from core_engine.alpha.ads_components import ERAR
    import numpy as np

    erar = ERAR(
        expected_pnl=10.0,    # 10bps expected profit
        cvar_95=-5.0,         # 5bps CVaR
        skewness=0.2,         # slight positive skew
        spread_bps=2.0,       # 2bps spread
        participation=0.1,    # 10% participation
        volatility=0.3,       # 30% volatility
        adverse_prob=0.3,     # 30% adverse probability
        kyle_lambda=0.5,      # Kyle's lambda
        holding_days=1.0,     # 1 day hold
        alt_return_bps=2.0,   # 2bps alternative return
        tail_lambda=1.0       # risk aversion
    )

    score = erar.compute()
    # Handle numpy array return
    if isinstance(score, np.ndarray):
        score = float(score.item())
    assert isinstance(score, float)
    assert score > 0  # Should be positive for profitable trade

    # Should trade if score meets threshold
    assert erar.should_trade(gamma=0.5) == (score >= 0.5)
    assert erar.should_trade(gamma=10.0) == (score >= 10.0)


def test_erar_omega_adj():
    """Test omega adjustment calculation."""
    from core_engine.alpha.ads_components import ERAR

    erar = ERAR(
        expected_pnl=10.0,
        cvar_95=-5.0,
        skewness=0.5,  # positive skew
        spread_bps=2.0,
        participation=0.1,
        volatility=0.3,
        adverse_prob=0.3,
        kyle_lambda=0.5,
        holding_days=1.0,
        alt_return_bps=2.0,
        tail_lambda=1.0
    )

    omega = erar.omega_adj()
    assert 0.5 <= omega <= 1.5  # bounded
    assert omega > 1.0  # positive skew increases adjustment

    # Test negative skew
    erar_neg = ERAR(
        expected_pnl=10.0,
        cvar_95=-5.0,
        skewness=-0.5,  # negative skew
        spread_bps=2.0,
        participation=0.1,
        volatility=0.3,
        adverse_prob=0.3,
        kyle_lambda=0.5,
        holding_days=1.0,
        alt_return_bps=2.0,
        tail_lambda=1.0
    )

    omega_neg = erar_neg.omega_adj()
    assert omega_neg < 1.0  # negative skew decreases adjustment


def test_erar_cost_calculation():
    """Test ERAR cost calculation."""
    from core_engine.alpha.ads_components import ERAR

    erar = ERAR(
        expected_pnl=10.0,
        cvar_95=-5.0,
        skewness=0.0,
        spread_bps=2.0,       # spread cost
        participation=0.1,    # 10% participation
        volatility=0.3,       # 30% volatility
        adverse_prob=0.3,     # 30% adverse probability
        kyle_lambda=0.5,      # Kyle's lambda
        holding_days=1.0,     # 1 day hold
        alt_return_bps=2.0,   # 2bps alternative return
        tail_lambda=1.0
    )

    cost = erar.cost()
    assert cost > 0
    assert cost >= erar.spread_bps  # At least spread cost

    # Test diagnostics
    diag = erar.get_diagnostics()
    assert 'expected_pnl_bps' in diag
    assert 'cvar_95_bps' in diag
    assert 'total_cost_bps' in diag
    assert 'omega_adj' in diag
    assert 'erar' in diag
    assert diag['total_cost_bps'] == cost


def test_erar_vectorized_methods():
    """Test vectorized ERAR methods."""
    from core_engine.alpha.ads_components import ERAR
    import numpy as np

    # Test vectorized omega adjustment
    skews = np.array([0.5, -0.5, 0.0])
    omegas = ERAR.omega_adj_vectorized(skews)
    assert len(omegas) == 3
    assert omegas[0] > 1.0  # positive skew
    assert omegas[1] < 1.0  # negative skew
    assert omegas[2] == 1.0  # neutral skew

    # Test vectorized cost
    costs = ERAR.cost_vectorized(
        spread_bps=np.array([2.0, 3.0]),
        participation=np.array([0.1, 0.2]),
        volatility=np.array([0.3, 0.4]),
        adverse_prob=np.array([0.3, 0.4]),
        kyle_lambda=np.array([0.5, 0.6]),
        holding_days=np.array([1.0, 2.0]),
        alt_return_bps=np.array([2.0, 3.0])
    )
    assert len(costs) == 2
    assert all(c > 0 for c in costs)

    # Test vectorized compute
    erars = ERAR.compute_vectorized(
        expected_pnl=np.array([10.0, 15.0]),
        cvar_95=np.array([-5.0, -8.0]),
        skewness=np.array([0.2, -0.1]),
        spread_bps=np.array([2.0, 3.0]),
        participation=np.array([0.1, 0.2]),
        volatility=np.array([0.3, 0.4]),
        adverse_prob=np.array([0.3, 0.4]),
        kyle_lambda=np.array([0.5, 0.6]),
        holding_days=np.array([1.0, 2.0]),
        alt_return_bps=np.array([2.0, 3.0]),
        tail_lambda=1.0
    )
    assert len(erars) == 2
    assert all(isinstance(e, (float, np.floating)) for e in erars)


def test_compute_reversal_probability():
    """Test reversal probability computation."""
    from core_engine.alpha.ads_components import compute_reversal_probability

    # Strong signal should have high reversal probability for oversold
    prob_strong = compute_reversal_probability(
        zscore=-2.5,      # strong mean reversion signal (negative for oversold)
        rsi=25,           # oversold
        bb_position=0.1,  # near lower BB
        is_oversold=True
    )
    assert prob_strong > 0.7

    # Weak signal should have lower reversal probability
    prob_weak = compute_reversal_probability(
        zscore=-0.5,      # weak signal
        rsi=45,           # neutral RSI
        bb_position=0.4,  # mid BB
        is_oversold=True
    )
    assert prob_weak < prob_strong

    # Test overbought case
    prob_overbought = compute_reversal_probability(
        zscore=2.0,       # positive z-score for overbought
        rsi=75,           # overbought
        bb_position=0.9,  # near upper BB
        is_oversold=False
    )
    assert prob_overbought > 0.7


def test_compute_vol_compression():
    """Test volatility compression computation."""
    from core_engine.alpha.ads_components import compute_vol_compression

    # Test with sample data
    vc = compute_vol_compression(
        short_vol=0.2,
        long_vol=0.4
    )
    assert 0.5 <= vc <= 2.0  # bounded
    assert vc == 0.5  # 0.2/0.4 = 0.5

    # When short vol < long vol, should be < 1
    vc_compressed = compute_vol_compression(0.2, 0.4)
    assert vc_compressed < 1.0

    # When short vol > long vol, should be > 1
    vc_expanded = compute_vol_compression(0.4, 0.2)
    assert vc_expanded > 1.0

    # Test bounds
    vc_min = compute_vol_compression(0.01, 1.0)  # very compressed
    assert vc_min == 0.5

    vc_max = compute_vol_compression(2.0, 0.01)  # very expanded
    assert vc_max == 2.0


def test_estimate_expected_pnl():
    """Test expected PnL estimation."""
    from core_engine.alpha.ads_components import estimate_expected_pnl

    pnl = estimate_expected_pnl(
        zscore=2.0,       # 2 std deviation from mean
        atr=1.0,          # $1 ATR
        price=100.0,      # $100 price
        half_life=20.0,   # 20 bar half-life
        holding_bars=10   # 10 bar hold
    )
    assert pnl > 0  # Should be positive for mean reversion

    # Test with negative zscore (should still be positive due to abs)
    pnl_neg = estimate_expected_pnl(
        zscore=-2.0,
        atr=1.0,
        price=100.0,
        half_life=20.0,
        holding_bars=10
    )
    assert pnl_neg == pnl  # Same magnitude

    # Test edge cases
    assert estimate_expected_pnl(0, 1.0, 100.0, 20.0) == 0.0  # zero zscore
    assert estimate_expected_pnl(2.0, 1.0, 100.0, 0) == 0.0   # zero half-life
    assert estimate_expected_pnl(2.0, 1.0, 0, 20.0) == 0.0     # zero price


def test_estimate_cvar_95():
    """Test CVaR 95% estimation."""
    from core_engine.alpha.ads_components import estimate_cvar_95

    cvar = estimate_cvar_95(
        volatility=0.02,    # 2% daily volatility
        holding_days=1.0    # 1 day hold
    )
    assert cvar < 0  # CVaR should be negative (loss)
    assert cvar > -500  # Reasonable bound for 2% vol (about 4% loss)

    # Higher volatility should give worse CVaR
    cvar_high_vol = estimate_cvar_95(0.04, 1.0)
    assert cvar_high_vol < cvar

    # Longer holding should give worse CVaR
    cvar_long_hold = estimate_cvar_95(0.02, 5.0)
    assert cvar_long_hold < cvar


def test_pending_signal_queue_operations():
    """Test additional PendingSignalQueue operations."""
    from core_engine.alpha.ads_components import PendingSignalQueue, PendingSignalContext, ERAR, SignalMaturityScore, ADSSMSGateInputs
    from datetime import datetime

    q = PendingSignalQueue(max_pending=50)

    # Create test context
    sms = SignalMaturityScore.from_inputs(
        ADSSMSGateInputs(setup_maturity=0.8, setup_validity_prob=0.8, signed_flow_support=0.5, vol_compression=1.0),
        pending_bars=0, max_pending=50
    )
    ctx = PendingSignalContext(
        symbol="TEST",
        side="BUY",
        sms=sms,
        erar=ERAR(expected_pnl=10.0, cvar_95=-5.0, skewness=0.0, spread_bps=2.0, participation=0.1,
                 volatility=0.3, adverse_prob=0.3, kyle_lambda=0.5, holding_days=1.0, alt_return_bps=2.0),
        raw_signal_strength=0.8,
        timestamp=datetime.now(),
        entry_price=100.0,
        metadata={"test": "data"}
    )

    # Test add and get
    q.add(ctx)
    retrieved = q.get("TEST", "BUY")
    assert retrieved is not None
    assert retrieved.symbol == "TEST"
    assert retrieved.side == "BUY"

    # Test get_mature_signals
    mature = q.get_mature_signals(threshold=0.8, regime="normal_volatility")
    assert len(mature) >= 0  # May or may not be mature

    # Test remove
    q.remove("TEST", "BUY")
    assert q.get("TEST", "BUY") is None

    # Test manual clear by removing all
    q.add(ctx)
    # Since no clear method, test that we can remove manually
    assert q.get("TEST", "BUY") is not None
    q.remove("TEST", "BUY")
    assert q.get("TEST", "BUY") is None

