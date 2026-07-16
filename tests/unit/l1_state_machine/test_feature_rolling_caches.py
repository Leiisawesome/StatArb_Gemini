from __future__ import annotations

from collections import deque

import numpy as np
import pytest

from l1_microstructure.config import FeatureConfig
from l1_microstructure.events import QuoteEvent, TradeEvent, TradeSide
from l1_microstructure.features import FeatureEngine


def test_incremental_volatility_matches_numpy_across_window_pruning() -> None:
    engine = FeatureEngine(FeatureConfig(micro_vol_window_seconds=0.004))
    base_timestamp = 1_000_000_000

    for index in range(30):
        timestamp = base_timestamp + index * 1_000_000
        price = 100.0 + ((index * 7) % 11) * 0.001
        engine._update_microprice_history(timestamp, price)

        actual = engine._realized_volatility(timestamp)
        prices = np.array([value for _, value in engine.microprice_history], dtype=float)
        expected = (
            engine.config.minimum_sigma
            if len(prices) < 3
            else float(np.std(np.diff(np.log(np.maximum(prices, engine.config.minimum_sigma)))))
        )
        assert actual == pytest.approx(expected, rel=1e-9, abs=1e-15)


def test_incremental_tertiles_match_numpy_linear_quantiles() -> None:
    engine = FeatureEngine(FeatureConfig(quantile_history=17))

    for index in range(40):
        value = float(((index * 13) % 23) - 11) / 7.0
        engine._append_quantile_value(
            engine.spread_norm_history,
            engine._spread_norm_sorted,
            value,
        )
        engine._spread_norm_cache_tail = value
        if len(engine.spread_norm_history) < 8:
            continue

        expected = tuple(
            float(np.quantile(np.array(engine.spread_norm_history), quantile))
            for quantile in (1.0 / 3.0, 2.0 / 3.0)
        )
        assert engine._rolling_tertiles_sorted(
            engine._spread_norm_sorted,
            (0.75, 1.75),
        ) == pytest.approx(expected)


def test_rebuilt_caches_resume_with_identical_features() -> None:
    config = FeatureConfig(
        trade_window_seconds=0.004,
        micro_vol_window_seconds=0.004,
        quantile_history=16,
    )
    original = FeatureEngine(config)
    base_timestamp = 1_000_000_000
    events = []
    for index in range(12):
        timestamp = base_timestamp + index * 1_000_000
        bid = 100.0 + index * 0.001
        events.extend(
            (
                QuoteEvent("AAPL", timestamp, bid, bid + 0.01, 100 + index, 120 - index),
                TradeEvent(
                    "AAPL",
                    timestamp + 500_000,
                    bid + 0.01,
                    10 + index,
                    TradeSide.BUY if index % 2 else TradeSide.SELL,
                ),
            )
        )
    for event in events:
        original.update(event)

    restored = FeatureEngine(config)
    restored.current_book = original.current_book
    restored.quote_history = deque(original.quote_history, maxlen=original.quote_history.maxlen)
    restored.microprice_history = deque(original.microprice_history)
    restored.trade_pressure_window = deque(original.trade_pressure_window)
    restored.spread_norm_history = deque(
        original.spread_norm_history,
        maxlen=original.spread_norm_history.maxlen,
    )
    restored.volatility_history = deque(
        original.volatility_history,
        maxlen=original.volatility_history.maxlen,
    )
    restored.flicker_baseline = original.flicker_baseline
    restored.flicker_intensity = original.flicker_intensity
    restored.last_quote_ts = original.last_quote_ts
    restored.rebuild_rolling_caches()

    next_event = QuoteEvent("AAPL", base_timestamp + 13_000_000, 100.02, 100.03, 140, 80)
    assert restored.update(next_event) == original.update(next_event)


def test_feature_update_does_not_rebuild_numpy_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FeatureEngine(FeatureConfig(quantile_history=16))
    base_timestamp = 1_000_000_000
    for index in range(20):
        engine.update(
            QuoteEvent(
                "AAPL",
                base_timestamp + index * 1_000_000,
                100.0 + index * 0.001,
                100.01 + index * 0.001,
                100,
                100,
            )
        )

    monkeypatch.setattr(np, "std", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(np, "quantile", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError))

    assert engine.update(
        QuoteEvent("AAPL", base_timestamp + 21_000_000, 100.03, 100.04, 120, 80)
    ) is not None
