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

