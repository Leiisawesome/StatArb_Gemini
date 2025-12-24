import pytest
import asyncio
import pandas as pd
from unittest.mock import MagicMock, AsyncMock, PropertyMock, ANY, patch
from datetime import datetime, timezone, timedelta
from core_engine.paper.engine import PaperTradingEngine, PaperTradingState
from core_engine.type_definitions import SignalType, OrderSide

@pytest.fixture
def config():
    mock_config = MagicMock()
    mock_config.session_id = "test-session-v3"
    mock_config.symbols = ["AAPL"]
    mock_config.eod_close_time = "16:00"
    mock_config.enable_eod_liquidation = True
    mock_config.initial_cash = 1000000.0
    return mock_config

@pytest.fixture
def engine(config):
    return PaperTradingEngine(config)

@pytest.mark.asyncio
async def test_init_no_session_id():
    # 111-112
    mock_config = MagicMock()
    mock_config.session_id = None
    eng = PaperTradingEngine(mock_config)
    assert eng._session_id is not None

@pytest.mark.asyncio
async def test_process_fill_event_v3(engine):
    # 459
    event = MagicMock()
    event.event_type = "FILL"
    event.event_id = "fill-1"
    
    engine._process_fill = AsyncMock()
    await engine._process_event(event)
    assert engine._process_fill.called

@pytest.mark.asyncio
async def test_process_bar_missing_fields(engine):
    # 483-484
    event = MagicMock()
    event.event_type = "BAR"
    event.symbol = None
    await engine._process_bar(event)
    
    event.symbol = "AAPL"
    event.market_timestamp = None
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_process_bar_missing_components(engine):
    # 507, 529, 535, 545, 549, 553, 579, 591, 614
    event = MagicMock()
    event.event_type = "BAR"
    event.symbol = "AAPL"
    event.market_timestamp = datetime.now()
    event.payload = {"open": 100.0, "close": 101.0}
    
    # All components are None by default
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_check_eod_liquidation_missing_components(engine):
    # 691, 704
    await engine._check_eod_liquidation(datetime.now(), {})
    
    engine._paper_broker = MagicMock()
    await engine._check_eod_liquidation(datetime.now(), {})

@pytest.mark.asyncio
async def test_check_eod_liquidation_exception(engine):
    # 714-720
    # Use a time that is definitely EOD in NY (e.g., 10 PM UTC)
    ts = datetime(2023, 1, 1, 22, 5, tzinfo=timezone.utc)
    engine._paper_broker = MagicMock()
    engine._paper_broker.get_all_positions = MagicMock(side_effect=Exception("Broker error"))
    
    await engine._check_eod_liquidation(ts, {})

@pytest.mark.asyncio
async def test_normalize_signal_missing_risk(engine):
    # 763
    sig = MagicMock()
    sig.symbol = "AAPL"
    res = engine._normalize_strategy_signal(sig, datetime.now())
    assert res is None

@pytest.mark.asyncio
async def test_normalize_signal_exception(engine):
    # 776-781, 784
    engine._risk_manager = MagicMock()
    # Trigger exception in normalization by using PERCENTAGE and mocking PV to fail
    type(engine._risk_manager).portfolio_value = PropertyMock(side_effect=Exception("Risk error"))
    
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type = SignalType.LONG_ENTRY
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = 0.1
    
    res = engine._normalize_strategy_signal(sig, datetime.now())
    assert res is None

@pytest.mark.asyncio
async def test_submit_signal_missing_components(engine):
    # 793, 873, 884
    sig = {"symbol": "AAPL"}
    await engine.submit_signal(sig)

@pytest.mark.asyncio
async def test_execute_pending_missing_components(engine):
    # 967, 980, 1024, 1030, 1044, 1050
    await engine._execute_pending_signals_for_symbol("AAPL", {}, datetime.now())

@pytest.mark.asyncio
async def test_process_fill_missing_components(engine):
    # 1096, 1110
    fill = MagicMock()
    await engine._process_fill(fill)

@pytest.mark.asyncio
async def test_state_manager_missing_v3(engine):
    # 1154, 1215
    await engine.restore_from_checkpoint("test")
    
    # stop() hits create_checkpoint (via on_shutdown)
    engine.stop()

@pytest.mark.asyncio
async def test_lifecycle_v3(engine):
    engine._state = PaperTradingState.RUNNING
    engine.pause()
    assert engine._state == PaperTradingState.PAUSED
    engine.resume()
    assert engine._state == PaperTradingState.RUNNING
    engine.stop()
    assert engine._state == PaperTradingState.STOPPED

@pytest.mark.asyncio
async def test_submit_signal_v3_fixed(engine):
    mock_risk = MagicMock()
    mock_risk.current_positions = {"AAPL": 0.0}
    mock_risk.portfolio_value = 1000000.0
    # Use AsyncMock for awaited methods
    mock_risk.authorize_signal_6gate = AsyncMock(return_value={
        "authorized": True, 
        "authorized_quantity": 100.0,
        "gate_passed": "G6"
    })
    engine.setup_risk_manager(mock_risk)
    
    mock_sig_mgr = MagicMock()
    mock_sig_mgr.submit_signal.return_value = "sig-123"
    engine.setup_signal_manager(mock_sig_mgr)
    
    mock_exec = MagicMock()
    mock_exec.execute_with_mode_routing = AsyncMock()
    engine.setup_execution_engine(mock_exec)
    
    mock_oms = MagicMock()
    mock_oms.submit_order = AsyncMock()
    engine.setup_oms(mock_oms)
    
    sig = {
        "symbol": "AAPL",
        "side": "buy",
        "requested_quantity": 100,
        "price": 10.0
    }
    
    res = await engine.submit_signal(sig)
    assert res == "sig-123"
    assert mock_sig_mgr.submit_signal.called

@pytest.mark.asyncio
async def test_submit_signal_unauthorized(engine):
    # 1185-1186
    mock_risk = MagicMock()
    mock_risk.current_positions = {"AAPL": 0.0}
    mock_risk.portfolio_value = 1000000.0
    mock_risk.authorize_signal_6gate = AsyncMock(return_value={
        "authorized": False,
        "rejection_reason": "Risk limit exceeded"
    })
    engine.setup_risk_manager(mock_risk)
    
    sig = {"symbol": "AAPL", "side": "buy", "requested_quantity": 100}
    res = await engine.submit_signal(sig)
    assert res is None

@pytest.mark.asyncio
async def test_get_state_stats_v3(engine):
    # 1229, 1247, 1251-1252, 1256
    assert engine.get_state() == PaperTradingState.INITIALIZING
    
    # get_stats
    stats = engine.get_stats()
    assert isinstance(stats, dict)
    assert stats["state"] == "INITIALIZING"

@pytest.mark.asyncio
async def test_restore_from_checkpoint_success_v3(engine):
    # 1286-1295
    mock_state = MagicMock()
    mock_state.restore_checkpoint.return_value = True
    mock_state.get_last_event_info.return_value = {"bars_processed": 42}
    engine.setup_state_manager(mock_state)
    
    success = await engine.restore_from_checkpoint("cp1")
    assert success is True
    assert engine._stats["bars_processed"] == 42
    assert engine._state == PaperTradingState.RUNNING

@pytest.mark.asyncio
async def test_process_bar_comprehensive_v3_fixed(engine):
    event = MagicMock()
    event.event_type = "BAR"
    event.symbol = "AAPL"
    event.market_timestamp = datetime.now()
    event.payload = {
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 102.0,
        "volume": 1000
    }
    event.event_id = "evt-1"
    event.sequence_number = 1
    
    mock_state = MagicMock()
    engine.setup_state_manager(mock_state)
    
    engine.config.symbols = ["AAPL"]
    engine._expected_symbols = ["AAPL"]
    
    await engine._process_bar(event)
    assert mock_state.update_event_tracking.called

@pytest.mark.asyncio
async def test_check_eod_liquidation_v3_fixed(engine):
    # Use a time that is definitely EOD in NY (e.g., 10 PM UTC)
    ts = datetime(2023, 1, 1, 22, 5, tzinfo=timezone.utc)
    
    mock_broker = MagicMock()
    pos = MagicMock()
    pos.symbol = "AAPL"
    pos.quantity = 100
    mock_broker.get_all_positions.return_value = [pos]
    mock_broker.get_position.return_value = pos
    engine.setup_paper_broker(mock_broker)
    
    engine.submit_signal = AsyncMock()
    
    await engine._check_eod_liquidation(ts, {})
    assert engine.submit_signal.called

@pytest.mark.asyncio
async def test_initialize_comprehensive_v3(engine):
    """Test initialize with all components to hit missing branches."""
    mock_time = MagicMock()
    mock_buffer = MagicMock()
    mock_signal = MagicMock()
    mock_broker = MagicMock()
    mock_risk = MagicMock()
    mock_exec = MagicMock()
    mock_state = MagicMock()
    mock_journal = MagicMock()
    mock_watchdog = MagicMock()
    mock_idempotency = MagicMock()
    mock_regime = MagicMock()
    mock_budget = MagicMock()
    
    engine.setup_time_source(mock_time)
    engine.setup_buffer_manager(mock_buffer)
    engine.setup_signal_manager(mock_signal)
    engine.setup_paper_broker(mock_broker)
    engine.setup_risk_manager(mock_risk)
    engine.setup_execution_engine(mock_exec)
    engine.setup_state_manager(mock_state)
    engine.setup_event_journal(mock_journal)
    engine.setup_watchdog(mock_watchdog)
    engine.setup_idempotency_tracker(mock_idempotency)
    engine.setup_regime_engine(mock_regime)
    engine.setup_risk_budget(mock_budget)
    engine.setup_session_gate(MagicMock())
    
    # Mock replay adapter with symbols
    mock_adapter = MagicMock()
    mock_adapter.replay_config.symbols = ["AAPL", "MSFT"]
    engine.setup_replay_adapter(mock_adapter)
    
    success = await engine.initialize()
    assert success is True
    assert engine._expected_symbols == ["AAPL", "MSFT"]
    
    mock_exec.set_execution_mode.assert_called_with('PAPER')
    mock_state.register_component.assert_any_call('buffer_manager', mock_buffer)
    mock_state.register_component.assert_any_call('regime_engine', mock_regime)
    mock_state.register_component.assert_any_call('risk_budget', mock_budget)
    mock_state.register_component.assert_any_call('idempotency_tracker', mock_idempotency)
    mock_watchdog.set_callbacks.assert_called_once()
    mock_journal.log_system.assert_called_with('engine_initialized', ANY)

@pytest.mark.asyncio
async def test_warmup_with_data_v3(engine):
    """Test warmup with actual data to hit missing branches."""
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = False
    engine.setup_buffer_manager(mock_buffer)
    
    mock_adapter = AsyncMock()
    import pandas as pd
    mock_adapter.get_warmup_data.return_value = pd.DataFrame({"close": [100, 101]})
    engine.setup_replay_adapter(mock_adapter)
    
    success = await engine.warmup(["AAPL"])
    assert success is True
    mock_buffer.load_warmup_data.assert_called_once()

@pytest.mark.asyncio
async def test_process_bar_fills_and_indicators_v3(engine):
    """Test _process_bar with fills and indicators to hit missing branches."""
    engine._state = PaperTradingState.RUNNING
    
    # 1. Setup components
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = True
    engine.setup_buffer_manager(mock_buffer)
    
    mock_journal = MagicMock()
    engine.setup_event_journal(mock_journal)
    
    mock_signal = MagicMock()
    mock_signal.on_bar_open.return_value = []
    engine.setup_signal_manager(mock_signal)
    
    # 2. Setup dispatcher for fills
    mock_dispatcher = MagicMock()
    fill_event = MagicMock()
    fill_event.event_type.name = "FILL"
    fill_event.market_timestamp = datetime.now(timezone.utc)
    fill_event.payload = {"fill_id": "f1", "quantity": 10, "price": 100, "side": "buy"}
    
    future_fill = MagicMock()
    future_fill.event_type.name = "FILL"
    future_fill.market_timestamp = fill_event.market_timestamp + timedelta(minutes=1)
    
    # peek_next returns fill, then future_fill
    mock_dispatcher.peek_next.side_effect = [fill_event, future_fill]
    mock_dispatcher.process_next.side_effect = [fill_event, None] # 535: break when fev is None
    engine.setup_dispatcher(mock_dispatcher)
    
    # 3. Setup indicators
    mock_ind = MagicMock()
    import pandas as pd
    ind_df = pd.DataFrame({"timestamp": [fill_event.market_timestamp], "rsi": [50.0]})
    mock_ind.compute_batch.return_value = ind_df
    engine.setup_indicator_adapter(mock_ind)
    
    # 4. Setup features
    mock_feat = MagicMock()
    mock_feat.transform_single.side_effect = RuntimeError("Scalers not loaded") # 591: except RuntimeError
    engine.setup_feature_adapter(mock_feat)
    
    # 5. Run _process_bar
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"symbol": "AAPL", "close": 100.0, "open": 99.0}
    event.market_timestamp = fill_event.market_timestamp
    
    await engine._process_bar(event)
    
    # Verify
    mock_journal.log_fill.assert_called()
    mock_journal.log_bar.assert_called()
    mock_signal.on_bar_close.assert_called() # 553

@pytest.mark.asyncio
async def test_normalize_signal_comprehensive_v3(engine):
    """Test _normalize_strategy_signal with all branches."""
    mock_risk = MagicMock()
    mock_risk.portfolio_value = 0.0 # 873: rm_pv <= 0
    mock_risk.current_positions = {"AAPL": 100.0}
    engine.setup_risk_manager(mock_risk)
    
    mock_broker = MagicMock()
    mock_broker.get_account_info.return_value = MagicMock(portfolio_value=1000000.0)
    mock_broker.get_latest_quote.return_value = {"last_price": 105.0}
    engine.setup_paper_broker(mock_broker)
    
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type = SignalType.LONG_ENTRY
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = 0.1
    sig.signal_price = 0.0 # 880: px <= 0
    sig.price = 0.0 # 882: px <= 0
    
    # 1. Test with rm_pv <= 0 and price fallback to quote
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), bar_close_price=0.0)
    assert res["requested_quantity"] > 0
    
    # 2. Test with rm_pv > 0 (874)
    mock_risk.portfolio_value = 1200000.0
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), bar_close_price=100.0)
    assert res["requested_quantity"] == 1200.0 # (0.1 * 1.2M) / 100

@pytest.mark.asyncio
async def test_execute_pending_signals_comprehensive_v3(engine):
    """Test _execute_pending_signals_for_symbol with all branches."""
    mock_sig = MagicMock()
    mock_sig.symbol = "AAPL"
    mock_sig.side = "buy"
    mock_sig.requested_quantity = 100
    mock_sig.metadata = {"authorization_id": "auth-1", "arrival_price": 100.0}
    
    engine._pending_open_signals = [mock_sig]
    
    mock_oms = AsyncMock()
    mock_oms.create_order.return_value = MagicMock(order_id="o1")
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    engine.setup_execution_engine(mock_exec)
    
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    mock_regime = MagicMock()
    # 1044-1045: rc with __dict__
    class MockRegimeContext:
        def __init__(self):
            self.regime = "bull"
    mock_regime.get_current_regime_context.return_value = MockRegimeContext()
    engine.setup_regime_engine(mock_regime)
    
    engine._execution_count = 1 # Not first exec
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 101.0}, datetime.now(timezone.utc))
    
    # Verify regime context from __dict__
    args, kwargs = mock_exec.execute_with_mode_routing.call_args
    assert args[0].strategy_context["regime_context"] == {"regime": "bull"}

@pytest.mark.asyncio
async def test_process_fill_idempotency_v3(engine):
    """Test _process_fill with idempotency hit."""
    mock_idempotency = MagicMock()
    mock_idempotency.check_and_mark.return_value = True # 1096: Duplicate
    engine.setup_idempotency_tracker(mock_idempotency)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"fill_id": "f1"}
    
    await engine._process_fill(event)
    assert engine._stats["fills_received"] == 1

@pytest.mark.asyncio
async def test_submit_signal_metadata_v3(engine):
    """Test submit_signal with metadata and gate_passed."""
    mock_risk = AsyncMock()
    mock_risk.authorize_signal_6gate.return_value = {
        "authorized": True,
        "authorized_quantity": 100.0,
        "gate_passed": "G3",
        "max_loss_estimate": 500.0,
        "estimated_fill_price": 102.0
    }
    engine.setup_risk_manager(mock_risk)
    
    mock_sig_mgr = MagicMock()
    mock_sig_mgr.submit_signal.return_value = "sig-1"
    engine.setup_signal_manager(mock_sig_mgr)
    
    sig = {"symbol": "AAPL", "side": "buy", "requested_quantity": 100}
    await engine.submit_signal(sig)
    
    # Verify metadata (1215-1216)
    args, kwargs = mock_sig_mgr.submit_signal.call_args
    enhanced_sig = args[0]
    assert enhanced_sig.metadata["gate_passed"] == "G3"
    assert enhanced_sig.metadata["max_loss_estimate"] == 500.0
    assert enhanced_sig.metadata["estimated_fill_price"] == 102.0

@pytest.mark.asyncio
async def test_process_bar_indicators_comprehensive_v3(engine):
    """Test _process_bar indicators and features branches."""
    engine._state = PaperTradingState.RUNNING
    engine._expected_symbols = ["AAPL"]
    
    # 1. Setup components
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = True
    mock_buffer.get_buffer.return_value = [MagicMock()]
    engine.setup_buffer_manager(mock_buffer)
    
    mock_ind = MagicMock()
    import pandas as pd
    # 579-580: val is not None
    ind_df = pd.DataFrame({
        "timestamp": [datetime.now(timezone.utc)],
        "rsi": [50.0],
        "other": [None], # Should be skipped
        "close": [100.0]
    })
    mock_ind.compute_indicators_batch.return_value = ind_df
    engine.setup_indicator_adapter(mock_ind)
    
    mock_feat = MagicMock()
    # 614-615: k not in enriched_df.columns
    mock_feat.transform_single.return_value = {"feature_1": 1.23}
    engine.setup_feature_adapter(mock_feat)
    
    mock_strat = AsyncMock()
    # 691-692: sig_price is None
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type = "long_entry"
    sig.quantity_type = "ABSOLUTE"
    sig.quantity = 100
    mock_strat.generate_signals.return_value = [sig]
    engine.setup_strategy_manager(mock_strat)
    
    # 2. Run _process_bar
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"symbol": "AAPL", "bar": {"close": 100.0}}
    event.market_timestamp = datetime.now(timezone.utc)
    
    engine.submit_signal = AsyncMock()
    
    await engine._process_bar(event)
    
    # Verify
    assert engine.submit_signal.called
