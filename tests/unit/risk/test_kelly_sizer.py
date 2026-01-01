from core_engine.risk.position_sizing.kelly_sizer import (
    KellyParams,
    compute_fractional_kelly_fraction_of_capital,
)


def test_kelly_fraction_increases_with_signal_strength():
    pnls = [0.01, -0.005, 0.015, -0.002, 0.01, 0.005, -0.004] * 10  # 70 trades
    params = KellyParams(min_trades=30)

    low = compute_fractional_kelly_fraction_of_capital(
        signal_strength=0.2,
        pnls=pnls,
        liquidity_factor=1.0,
        current_dd=0.0,
        max_dd=0.1,
        regime_factor=1.0,
        params=params,
    )
    high = compute_fractional_kelly_fraction_of_capital(
        signal_strength=0.8,
        pnls=pnls,
        liquidity_factor=1.0,
        current_dd=0.0,
        max_dd=0.1,
        regime_factor=1.0,
        params=params,
    )
    assert 0.0 <= low.target_fraction_of_capital <= 1.0
    assert 0.0 <= high.target_fraction_of_capital <= 1.0
    assert high.target_fraction_of_capital >= low.target_fraction_of_capital


