import pytest
import asyncio
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from core_engine.paper.engine import PaperTradingEngine, PaperTradingConfig, PaperTradingState
from core_engine.system.event_dispatcher import EventType

@pytest.fixture
def config():
    return PaperTradingConfig(
        session_id="test-session-v2",
        enable_eod_liquidation=True,
        eod_close_time="15:55"
    )

@pytest.fixture
def engine(config):
    return PaperTradingEngine(config)

@pytest.mark.asyncio
async def test_initialize_missing_components(engine):
    # Missing required components
    engine.setup_time_source(None)
    success = await engine.initialize()
    assert success is False
    assert engine.get_state() == PaperTradingState.ERROR

@pytest.mark.asyncio
async def test_initialize_exception(engine):
    # Trigger exception in initialize
    engine.setup_time_source(MagicMock())
    engine.setup_buffer_manager(MagicMock())
    engine.setup_signal_manager(MagicMock())
    engine.setup_paper_broker(MagicMock())
    
    # Mock risk manager to throw on set_session_gate
    mock_risk = MagicMock()
    mock_risk.set_session_gate.side_effect = Exception("Init error")
    engine.setup_risk_manager(mock_risk)
    engine.setup_session_gate(MagicMock())
    
    success = await engine.initialize()
    assert success is False
    assert engine.get_state() == PaperTradingState.ERROR

@pytest.mark.asyncio
async def test_warmup_exception(engine):
    engine.setup_buffer_manager(MagicMock())
    mock_replay = MagicMock()
    # Ensure it's actually called
    mock_replay.get_warmup_data = AsyncMock(side_effect=Exception("Warmup error"))
    engine.setup_replay_adapter(mock_replay)
    
    # Force it to try warming up AAPL
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = False
    engine.setup_buffer_manager(mock_buffer)
    
    success = await engine.warmup(["AAPL"])
    assert success is False

@pytest.mark.asyncio
async def test_run_invalid_state(engine):
    engine._state = PaperTradingState.INITIALIZING
    await engine.run() # Should log error and return

@pytest.mark.asyncio
async def test_run_no_dispatcher(engine):
    engine._state = PaperTradingState.RUNNING
    engine.setup_dispatcher(None)
    
    # Run for a short time
    task = asyncio.create_task(engine.run())
    await asyncio.sleep(0.1)
    engine.stop()
    await task

@pytest.mark.asyncio
async def test_process_event_idempotency(engine):
    mock_tracker = MagicMock()
    mock_tracker.check_and_mark.return_value = True # Duplicate
    engine.setup_idempotency_tracker(mock_tracker)
    
    event = MagicMock()
    event.event_id = "evt1"
    event.event_type = EventType.BAR
    
    await engine._process_event(event)
    # Should return early

@pytest.mark.asyncio
async def test_process_event_exception(engine):
    event = MagicMock()
    event.event_id = "evt1"
    event.event_type = EventType.BAR
    
    with patch.object(engine, '_process_bar', side_effect=Exception("Process error")):
        await engine._process_event(event)
        # Should catch and log

@pytest.mark.asyncio
async def test_process_bar_peek_exceptions(engine):
    engine.setup_buffer_manager(MagicMock())
    mock_dispatcher = MagicMock()
    mock_dispatcher.peek_next.side_effect = Exception("Peek error")
    engine.setup_dispatcher(mock_dispatcher)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"open": 100, "close": 101}
    event.market_timestamp = datetime.now()
    
    await engine._process_bar(event)
    # Should continue despite peek error

@pytest.mark.asyncio
async def test_process_bar_indicator_edge_cases(engine):
    mock_buffer_mgr = MagicMock()
    mock_buffer_mgr.get_buffer.return_value = pd.DataFrame([{"close": 100}])
    mock_buffer_mgr.is_warmed_up.return_value = True
    engine.setup_buffer_manager(mock_buffer_mgr)
    
    mock_ind = MagicMock()
    # Case 1: returns None
    mock_ind.compute_indicators_batch.return_value = None
    engine.setup_indicator_adapter(mock_ind)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"open": 100, "close": 101}
    event.market_timestamp = datetime.now()
    
    await engine._process_bar(event)
    
    # Case 2: symbol not in columns
    mock_ind.compute_indicators_batch.return_value = pd.DataFrame([{"close": 100}])
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_process_bar_feature_exception(engine):
    mock_buffer_mgr = MagicMock()
    mock_buffer_mgr.get_buffer.return_value = pd.DataFrame([{"close": 100}])
    mock_buffer_mgr.is_warmed_up.return_value = True
    engine.setup_buffer_manager(mock_buffer_mgr)
    
    mock_ind = MagicMock()
    mock_ind.compute_indicators_batch.return_value = pd.DataFrame([{"close": 100, "rsi": 50}])
    engine.setup_indicator_adapter(mock_ind)
    
    mock_feat = MagicMock()
    mock_feat.transform_single.side_effect = RuntimeError("Not loaded")
    engine.setup_feature_adapter(mock_feat)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"open": 100, "close": 101}
    event.market_timestamp = datetime.now()
    
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_process_bar_strategy_manager_exceptions(engine):
    engine._expected_symbols = ["AAPL"]
    
    mock_buffer_mgr = MagicMock()
    mock_buffer_mgr.get_buffer.return_value = pd.DataFrame([{"close": 100}])
    mock_buffer_mgr.is_warmed_up.return_value = True
    engine.setup_buffer_manager(mock_buffer_mgr)
    
    mock_ind = MagicMock()
    mock_ind.compute_indicators_batch.return_value = pd.DataFrame([{"close": 100, "rsi": 50}])
    engine.setup_indicator_adapter(mock_ind)
    
    mock_broker = MagicMock()
    mock_broker.get_position.side_effect = Exception("Pos error")
    engine.setup_paper_broker(mock_broker)
    
    mock_strat = MagicMock()
    mock_strat.generate_signals = AsyncMock(return_value=[])
    engine.setup_strategy_manager(mock_strat)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"open": 100, "close": 101}
    event.market_timestamp = datetime.now()
    
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_check_eod_liquidation_time_parsing(engine):
    engine.config.eod_close_time = "invalid"
    ts = datetime(2023, 1, 1, 16, 0, tzinfo=timezone.utc)
    count = await engine._check_eod_liquidation(ts, {})
    assert count == 0 # Should fallback to 15:55 and return 0 if no broker

@pytest.mark.asyncio
async def test_check_eod_liquidation_tz_none(engine):
    engine.config.eod_close_time = "15:00"
    ts = datetime(2023, 1, 1, 16, 0) # No tz
    
    mock_broker = MagicMock()
    mock_broker.get_all_positions.return_value = []
    engine.setup_paper_broker(mock_broker)
    
    count = await engine._check_eod_liquidation(ts, {})
    assert count == 0

@pytest.mark.asyncio
async def test_normalize_strategy_signal_types(engine):
    # Test HOLD/unknown
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type = "HOLD"
    res = engine._normalize_strategy_signal(sig, datetime.now())
    assert res is None
    
    # Test target_weight exception
    sig.signal_type = "LONG_ENTRY"
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = "invalid"
    res = engine._normalize_strategy_signal(sig, datetime.now())
    assert res is None

@pytest.mark.asyncio
async def test_execute_pending_signals_edge_cases_v2(engine):
    # Case: open_price is None
    engine._pending_open_signals = [MagicMock(symbol="AAPL")]
    await engine._execute_pending_signals_for_symbol("AAPL", {}, datetime.now())
    
    # Case: record_fill
    engine.setup_oms(AsyncMock())
    engine.setup_execution_engine(AsyncMock())
    
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 10
    sig.metadata = {"arrival_price": 100}
    engine._pending_open_signals = [sig]
    
    mock_res = MagicMock()
    mock_res.status = "FILLED"
    mock_res.fill_quantity = 10
    mock_res.fill_price = 101
    engine._execution_engine.execute_with_mode_routing.return_value = mock_res
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 101}, datetime.now())
    engine._oms.record_fill.assert_called()

@pytest.mark.asyncio
async def test_process_fill_idempotency_v2(engine):
    mock_tracker = MagicMock()
    mock_tracker.check_and_mark.return_value = True
    engine.setup_idempotency_tracker(mock_tracker)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"fill_id": "f1"}
    
    await engine._process_fill(event)
    # Should return early

@pytest.mark.asyncio
async def test_restore_from_checkpoint_no_manager(engine):
    engine.setup_state_manager(None)
    res = await engine.restore_from_checkpoint()
    assert res is False
