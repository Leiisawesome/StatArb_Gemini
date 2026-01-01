import pandas as pd

from core_engine.config.strategies import MeanReversionConfig
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import (
    EnhancedMeanReversionStrategy,
)


def _make_df(n: int = 40) -> pd.DataFrame:
    # Create a stable series then a sharp drop at the end to produce negative z-score
    base = [100.0] * (n - 1) + [90.0]
    df = pd.DataFrame(
        {
            "close": base,
            "sma_20": [100.0] * n,
            "rsi": [50.0] * n,
            "bb_upper": [102.0] * n,
            "bb_lower": [98.0] * n,
            "bb_middle": [100.0] * n,
            "bb_position": [0.5] * n,
            "atr": [1.0] * n,
            "volume_ratio": [1.0] * n,
            "macd_histogram": [0.0] * n,
            "adx": [15.0] * n,
        }
    )
    return df


def test_pending_signal_is_enqueued_and_then_stales_out():
    cfg = MeanReversionConfig(
        symbols=["TEST"],
        lookback_period=20,
        dislocation_minimum=1.0,
        enable_regime_filter=False,
        sms_max_pending=1,  # very short for test
        tau_0=0.50,
        enable_ads_gates=True,
    )
    strat = EnhancedMeanReversionStrategy(cfg)

    df = _make_df()

    # Directly evaluate without full pipeline; should enqueue pending BUY due to high tau(R)
    sig = strat._evaluate_signal_conditions("TEST", df, -1)  # noqa: SLF001
    assert sig is None
    assert strat.pending_signals.get("TEST", "BUY") is not None

    # Tick once - still pending, not yet stale
    m1 = strat._try_emit_matured_pending("TEST", df, -1)  # noqa: SLF001
    assert m1 is None
    assert strat.pending_signals.get("TEST", "BUY") is not None

    # Tick again - should stale and be removed (max_pending=1)
    m2 = strat._try_emit_matured_pending("TEST", df, -1)  # noqa: SLF001
    assert m2 is None
    assert strat.pending_signals.get("TEST", "BUY") is None


