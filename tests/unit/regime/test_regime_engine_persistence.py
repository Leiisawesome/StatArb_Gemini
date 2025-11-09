from datetime import datetime, timedelta

import pandas as pd
import pytest

from core_engine.config import DataConfig, RegimeConfig
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine


@pytest.mark.asyncio
async def test_regime_engine_persists_bar_by_bar_state():
    # Load real market data via ClickHouseDataManager
    data_manager = ClickHouseDataManager(DataConfig())
    await data_manager.initialize()
    await data_manager.start()

    try:
        symbol = "TSLA"
        start_time = "2024-12-20 09:30:00"
        end_time = "2024-12-20 16:00:00"
        raw_df = data_manager.get_market_data(symbol=symbol, start_time=start_time, end_time=end_time)

        if raw_df is None or raw_df.empty:
            pytest.skip("No market data available from ClickHouse for TSLA 2024-12-20.")

        # Ensure timestamp column exists
        if "timestamp" not in raw_df.columns:
            raw_df = raw_df.reset_index().rename(columns={"index": "timestamp"})

        # Regime engine expects sequential minutes; trim to at least lookback window
        raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)
        if raw_df.shape[0] < 120:
            pytest.skip("Insufficient real market data retrieved for regime persistence test.")

        df = raw_df  # Already ordered and contains the necessary columns
    finally:
        await data_manager.stop()

    engine = EnhancedRegimeEngine(RegimeConfig())

    await engine.initialize()
    await engine.start()

    # Run regime detection over the dataframe (bar-by-bar)
    result = engine.process_market_data(df)

    # The engine should return a regime sequence and keep it internally
    assert result["market_data_processed"] is True
    assert result["regime_sequence"], "Expected a non-empty regime sequence"

    sequence = engine.get_regime_sequence(symbol)
    assert sequence, "Regime sequence should be stored inside the engine"
    assert len(sequence) == len(result["regime_sequence"])

    # Use an exact timestamp from the sequence and request the regime analysis
    mid_entry = sequence[len(sequence) // 2]
    mid_timestamp = mid_entry["timestamp"]

    regime_exact = engine.get_regime_at_timestamp(symbol, mid_timestamp)
    assert regime_exact is not None, "Expected regime analysis for exact timestamp"

    # Ask for a timestamp that does not exist (half-minute later) – engine should
    # return the nearest earlier regime
    later_timestamp = mid_timestamp + timedelta(seconds=30)
    regime_nearest = engine.get_regime_at_timestamp(symbol, later_timestamp)
    assert regime_nearest is not None, "Expected fallback to nearest earlier regime"

    # Verify the convenience wrapper that works off a dataframe row index
    df_reset = df.reset_index(drop=True)
    row_index = mid_entry["bar_index"]
    regime_from_row = engine.get_regime_for_dataframe_row(symbol, row_index, df_reset)
    assert regime_from_row is not None, "Expected regime analysis for dataframe row"
    assert (
        regime_from_row.primary_regime == regime_exact.primary_regime
    ), "Row lookup should match direct timestamp lookup"

    await engine.stop()

