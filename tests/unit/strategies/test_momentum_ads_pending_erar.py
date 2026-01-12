import pytest
import pandas as pd

from core_engine.config import MomentumConfig
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.type_definitions.strategy import SignalType


def _make_df(n: int = 60) -> pd.DataFrame:
    # Simple trending series with required columns for momentum ADS logic
    prices = [100.0 + i * 0.2 for i in range(n)]
    idx = pd.date_range("2024-01-01 09:30:00", periods=n, freq="1min")
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.001 for p in prices],
            "low": [p * 0.999 for p in prices],
            "close": prices,
            "volume": [1_000_000] * n,
            "atr": [0.5] * n,
            "adx": [30.0] * n,
            "rsi": [55.0] * n,
            "volume_ratio": [1.2] * n,
            "composite_z": [0.6] * n,
            "composite_pct": [75.0] * n,
            # minimal SMA columns referenced by validator in some paths
            "sma_20": pd.Series(prices).rolling(20).mean().bfill(),
            "sma_50": pd.Series(prices).rolling(50).mean().bfill(),
            "macd": pd.Series(prices).diff().fillna(0),
        },
        index=idx,
    )
    return df


def _seed_indicators(strat: EnhancedMomentumStrategy, symbol: str, df: pd.DataFrame) -> None:
    # _evaluate_bar_at_index reads from strat.indicators[symbol] series
    strat.indicators[symbol] = {
        "adx": df["adx"],
        "volume_ratio": df["volume_ratio"],
        "trend_strength": pd.Series([0.01] * len(df), index=df.index),
    }


@pytest.mark.asyncio
async def test_momentum_enqueues_pending_and_stales_out():
    cfg = MomentumConfig(
        symbols=["TEST"],
        long_period=20,
        scan_all_bars=False,
        sms_max_pending=1,  # very short for test
        tau_0=0.80,  # high tau to force pending
        enable_ads_gates=True,
        erar_gamma=0.0,  # allow
        erar_tail_lambda=0.0,  # remove tail penalty so ERAR doesn't fail safe in this unit test
    )
    strat = EnhancedMomentumStrategy(cfg)

    df = _make_df()
    strat.market_data["TEST"] = df
    _seed_indicators(strat, "TEST", df)

    # Force entry condition true so ADS pending path is exercised deterministically
    strat._check_composite_entry = lambda *args, **kwargs: (True, SignalType.BUY)  # noqa: SLF001

    sig = await strat._evaluate_bar_at_index("TEST", -1)  # noqa: SLF001
    assert sig is None

    # The call should have enqueued pending BUY
    assert strat.pending_signals.get("TEST", "BUY") is not None

    # Tick once - still pending (max_pending=1)
    m1 = strat._try_emit_matured_pending("TEST", df, -1)  # noqa: SLF001
    assert m1 is None
    assert strat.pending_signals.get("TEST", "BUY") is not None

    # Tick again - should stale and be removed
    m2 = strat._try_emit_matured_pending("TEST", df, -1)  # noqa: SLF001
    assert m2 is None
    assert strat.pending_signals.get("TEST", "BUY") is None


@pytest.mark.asyncio
async def test_momentum_erar_gate_blocks_emission():
    cfg = MomentumConfig(
        symbols=["TEST"],
        long_period=20,
        scan_all_bars=False,
        sms_max_pending=50,
        tau_0=0.35,  # low tau so SMS will likely pass
        enable_ads_gates=True,
        erar_gamma=10.0,  # unrealistically high => block
    )
    strat = EnhancedMomentumStrategy(cfg)

    df = _make_df()
    # Make the setup very strong so SMS passes; ERAR still blocks due to gamma
    df["composite_z"] = 2.0
    df["composite_pct"] = 95.0
    df["volume_ratio"] = 2.0
    strat.market_data["TEST"] = df
    _seed_indicators(strat, "TEST", df)

    strat._check_composite_entry = lambda *args, **kwargs: (True, SignalType.BUY)  # noqa: SLF001

    sig = await strat._evaluate_bar_at_index("TEST", -1)  # noqa: SLF001
    assert sig is None
    assert strat.pending_signals.get("TEST", "BUY") is None

