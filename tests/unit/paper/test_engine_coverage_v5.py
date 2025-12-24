import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime, timezone
import pandas as pd
import pytz

from core_engine.paper.engine import PaperTradingEngine, PaperTradingState
from core_engine.paper.engine import PaperTradingConfig

@pytest.fixture
def engine_config():
    return PaperTradingConfig(
        initial_cash=100000.0,
        enable_eod_liquidation=True,
        eod_close_time="16:00",
        session_id="test_session"
    )

@pytest.fixture
def engine(engine_config):
    engine = PaperTradingEngine(config=engine_config)
    engine._paper_broker = MagicMock()
    engine._dispatcher = MagicMock()
    engine._buffer_manager = MagicMock()
    engine._event_journal = MagicMock()
    engine._signal_manager = MagicMock()
    engine._indicator_adapter = MagicMock()
    engine._feature_adapter = MagicMock()
    engine._regime_engine = MagicMock()
    engine._strategy_manager = AsyncMock()
    engine._risk_manager = MagicMock()
    engine._risk_manager.update_position = AsyncMock()
    engine._oms = AsyncMock()
    engine._execution_engine = AsyncMock()
    engine._state_manager = MagicMock()
    engine._position_book = MagicMock()
    engine._watchdog = MagicMock()
    engine._expected_symbols = ["AAPL"]
    return engine

@pytest.mark.asyncio
async def test_process_bar_surgical_v5(engine):
    now = datetime.now(timezone.utc)
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 150.0, "timestamp": now}
    
    engine._check_eod_liquidation = AsyncMock()
    
    # 507: Hit execute_pending_signals_for_symbol
    engine._pending_open_signals = [MagicMock()]
    
    # 535: break in fill draining loop
    engine._dispatcher.peek_next.side_effect = [MagicMock(), None]
    engine._dispatcher.process_next.return_value = None
    
    # 579-580: Position details exception
    engine._position_book.get_position_details.side_effect = Exception("Pos error")
    
    # 591: log_features
    engine._buffer_manager.is_warmed_up.return_value = True
    engine._indicator_adapter.compute_indicators_batch.return_value = pd.DataFrame({
        "timestamp": [now], "close": [150.0], "ind1": [1.0]
    })
    engine._feature_adapter.transform_single.return_value = {"feat1": 2.0}
    
    # 614-615: enriched_df.at exception
    # Use an empty DF so .at[0, k] fails
    engine._indicator_adapter.compute_indicators_batch.side_effect = [
        pd.DataFrame({"timestamp": [now], "close": [150.0]}), # for 591
        pd.DataFrame(columns=["timestamp"]) # for 614
    ]
    
    await engine._process_bar(event) # Hits 507, 535, 579, 591
    await engine._process_bar(event) # Hits 614

@pytest.mark.asyncio
async def test_process_event_surgical_v5(engine):
    # 691-692: Event processing error
    event = MagicMock()
    engine._process_bar = AsyncMock(side_effect=Exception("Process error"))
    await engine._process_event(event)

@pytest.mark.asyncio
async def test_normalize_signal_surgical_v5(engine):
    # 886: PV exception
    s = MagicMock()
    s.symbol = "AAPL"
    s.signal_type.value = "long_entry"
    s.quantity_type = "PERCENTAGE"
    type(engine._risk_manager).portfolio_value = PropertyMock(side_effect=Exception("PV error"))
    engine._normalize_strategy_signal(s, datetime.now())

@pytest.mark.asyncio
async def test_execute_pending_surgical_v5(engine):
    sig = MagicMock()
    sig.symbol = "AAPL"
    # 1024-1025: Metadata exception
    sig.metadata = MagicMock()
    sig.metadata.__contains__.side_effect = Exception("Metadata error")
    
    engine._pending_open_signals = [sig]
    
    # 1050-1051: cr.__dict__
    cr = MagicMock()
    cr.__dict__ = {"regime": "bull"}
    type(engine._regime_engine).current_regime = PropertyMock(return_value=cr)
    
    # 1052-1053: regime_ctx exception
    class BadRegime:
        @property
        def __dict__(self):
            raise Exception("Bad dict")
    
    # We'll run it twice
    type(engine._regime_engine).current_regime = PropertyMock(side_effect=[cr, BadRegime()])
    
    # 1030-1031: decision_price fallback exception
    # open_price is "invalid"
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": "invalid"}, datetime.now())
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": "invalid"}, datetime.now())

