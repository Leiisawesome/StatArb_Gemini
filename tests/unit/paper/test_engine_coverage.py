"""
Additional unit tests for PaperTradingEngine to improve coverage.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch, PropertyMock
import pandas as pd
from datetime import datetime, timezone, timedelta

from core_engine.paper.engine import (
    PaperTradingEngine,
    PaperTradingConfig,
    PaperTradingState,
)
from core_engine.system.event_dispatcher import EventType

@pytest.fixture
def config():
    return PaperTradingConfig(session_id="test-session-123")

@pytest.fixture
def engine(config):
    return PaperTradingEngine(config)

def test_setup_replay_adapter_with_symbols(engine):
    """Test setup_replay_adapter infers expected symbols."""
    mock_adapter = MagicMock()
    mock_adapter.replay_config.symbols = ["AAPL", "MSFT"]
    
    engine.setup_replay_adapter(mock_adapter)
    
    assert engine._replay_adapter == mock_adapter
    assert engine._expected_symbols == ["AAPL", "MSFT"]

def test_setup_replay_adapter_exception(engine):
    """Test setup_replay_adapter handles exceptions gracefully."""
    mock_adapter = MagicMock()
    type(mock_adapter).replay_config = PropertyMock(side_effect=Exception("Error"))
    
    # Should not raise
    engine.setup_replay_adapter(mock_adapter)
    assert engine._replay_adapter == mock_adapter
    assert engine._expected_symbols == []

def test_on_stall(engine):
    """Test _on_stall creates a checkpoint."""
    mock_state_manager = MagicMock()
    engine.setup_state_manager(mock_state_manager)
    
    engine._on_stall()
    
    mock_state_manager.create_checkpoint.assert_called_once_with('stall')

@pytest.mark.asyncio
async def test_process_event_quote_trade(engine):
    """Test _process_event handles QUOTE and TRADE events."""
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    # QUOTE event
    quote_event = MagicMock()
    quote_event.event_type = EventType.QUOTE
    quote_event.symbol = 'AAPL'
    quote_event.payload = {'price': 150.0}
    quote_event.event_id = None
    
    await engine._process_event(quote_event)
    mock_broker.set_price.assert_called_with('AAPL', 150.0)
    
    # TRADE event
    trade_event = MagicMock()
    trade_event.event_type = EventType.TRADE
    trade_event.symbol = 'MSFT'
    trade_event.payload = {'last_price': 300.0}
    trade_event.event_id = None
    
    await engine._process_event(trade_event)
    mock_broker.set_price.assert_called_with('MSFT', 300.0)

@pytest.mark.asyncio
async def test_process_bar_data_contamination(engine):
    """Test _process_bar detects data contamination."""
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {'symbol': 'MSFT', 'close': 100.0}
    
    # Should return early
    await engine._process_bar(event)
    assert engine._stats['bars_processed'] == 0

@pytest.mark.asyncio
async def test_process_bar_invalid_data(engine):
    """Test _process_bar handles invalid data from validator."""
    mock_validator = MagicMock()
    mock_validator.validate_bar_dict.return_value = MagicMock(is_valid=False, issues=["Bad data"])
    engine.setup_data_validator(mock_validator)
    
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {'symbol': 'AAPL', 'close': 100.0}
    event.market_timestamp = datetime.now(timezone.utc)
    
    await engine._process_bar(event)
    assert engine._stats['bars_processed'] == 1
    # Should return after validation failure

@pytest.mark.asyncio
async def test_process_bar_fill_draining(engine):
    """Test _process_bar drains fills from dispatcher."""
    engine._state = PaperTradingState.RUNNING
    
    mock_dispatcher = MagicMock()
    
    # Mock events for draining
    fill_event = MagicMock()
    fill_event.event_type = EventType.FILL
    fill_event.market_timestamp = datetime.now(timezone.utc)
    fill_event.payload = {'fill_id': 'f1', 'quantity': 10, 'price': 100}
    fill_event.symbol = 'AAPL'
    
    other_event = MagicMock()
    other_event.event_type = EventType.BAR
    
    # peek_next returns fill, then other
    mock_dispatcher.peek_next.side_effect = [fill_event, other_event]
    mock_dispatcher.process_next.side_effect = [fill_event]
    
    engine.setup_dispatcher(mock_dispatcher)
    
    # Main bar event
    bar_event = MagicMock()
    bar_event.symbol = 'AAPL'
    bar_event.payload = {'symbol': 'AAPL', 'close': 100.0, 'open': 99.0}
    bar_event.market_timestamp = fill_event.market_timestamp
    
    await engine._process_bar(bar_event)
    
    assert engine._stats['fills_received'] == 1

@pytest.mark.asyncio
async def test_check_eod_liquidation_disabled(engine):
    """Test EOD liquidation when disabled."""
    engine.config.enable_eod_liquidation = False
    result = await engine._check_eod_liquidation(datetime.now(timezone.utc), {})
    assert result == 0

@pytest.mark.asyncio
async def test_check_eod_liquidation_success(engine):
    """Test successful EOD liquidation."""
    engine.config.enable_eod_liquidation = True
    engine.config.eod_close_time = "15:55"
    
    # 16:00 NY time
    ts = pd.Timestamp('2024-01-01 16:00:00').tz_localize('America/New_York').tz_convert('UTC')
    
    mock_broker = MagicMock()
    pos = MagicMock()
    pos.symbol = "AAPL"
    pos.quantity = 100
    mock_broker.get_position.return_value = pos
    engine.setup_paper_broker(mock_broker)
    
    mock_book = MagicMock()
    mock_book.get_all_positions.return_value = {"AAPL": pos}
    mock_book.get_position.return_value = pos
    engine.setup_position_book(mock_book)
    
    # Mock submit_signal to avoid full risk check
    engine.submit_signal = AsyncMock(return_value="sig-123")
    
    result = await engine._check_eod_liquidation(ts.to_pydatetime(), {})
    
    assert result == 1
    engine.submit_signal.assert_called_once()
    args = engine.submit_signal.call_args[0][0]
    assert args['symbol'] == 'AAPL'
    assert args['side'] == 'sell'
    assert args['reason'] == 'EOD_LIQUIDATION'

@pytest.mark.asyncio
async def test_check_eod_liquidation_already_done(engine):
    """Test EOD liquidation doesn't run twice for same day."""
    engine.config.enable_eod_liquidation = True
    ts = pd.Timestamp('2024-01-01 16:00:00').tz_localize('America/New_York')
    
    engine._eod_flags[f"eod_liquidated_{ts.date()}"] = True
    
    result = await engine._check_eod_liquidation(ts.to_pydatetime(), {})
    assert result == 0

def test_normalize_strategy_signal_absolute(engine):
    """Test _normalize_strategy_signal with ABSOLUTE quantity."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_ENTRY"
    sig.quantity_type = "ABSOLUTE"
    sig.target_quantity = 100
    sig.strength = 0.9
    sig.confidence = 0.8
    sig.strategy_id = "strat1"
    
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 150.0)
    
    assert res['symbol'] == "AAPL"
    assert res['side'] == "buy"
    assert res['requested_quantity'] == 100.0
    assert res['arrival_price'] == 150.0

def test_normalize_strategy_signal_percentage(engine):
    """Test _normalize_strategy_signal with PERCENTAGE quantity."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_ENTRY"
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = 0.1 # 10%
    
    mock_broker = MagicMock()
    acct = MagicMock()
    acct.portfolio_value = 100000.0
    mock_broker.get_account_info.return_value = acct
    engine.setup_paper_broker(mock_broker)
    
    # 10% of 100k = 10k. At $100/share = 100 shares.
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    
    assert res['requested_quantity'] == 100.0

def test_normalize_strategy_signal_exits(engine):
    """Test _normalize_strategy_signal for exit signals."""
    mock_risk = MagicMock()
    mock_risk.current_positions = {"AAPL": 100, "MSFT": -50}
    engine.setup_risk_manager(mock_risk)
    
    # Long exit
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_EXIT"
    sig.quantity_type = "ABSOLUTE"
    
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "sell"
    assert res['requested_quantity'] == 100.0
    
    # Short exit
    sig.symbol = "MSFT"
    sig.signal_type.value = "SHORT_EXIT"
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "buy"
    assert res['requested_quantity'] == 50.0

@pytest.mark.asyncio
async def test_execute_pending_signals(engine):
    """Test _execute_pending_signals_for_symbol."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 100
    sig.signal_id = "s1"
    sig.arrival_price = 150.0
    
    engine._pending_open_signals = [sig]
    
    mock_oms = AsyncMock()
    order = MagicMock()
    order.order_id = "o1"
    mock_oms.create_order.return_value = order
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    result = MagicMock()
    result.status = "FILLED"
    result.fill_quantity = 100
    result.fill_price = 151.0
    mock_exec.execute_with_mode_routing.return_value = result
    engine.setup_execution_engine(mock_exec)
    
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 151.0}, datetime.now(timezone.utc))
    
    assert len(engine._pending_open_signals) == 0
    mock_oms.create_order.assert_called_once()
    mock_exec.execute_with_mode_routing.assert_called_once()
    mock_oms.record_fill.assert_called_once()
    assert engine._stats['orders_submitted'] == 1

@pytest.mark.asyncio
async def test_submit_signal_with_journal(engine):
    """Test submit_signal logs to journal."""
    mock_journal = MagicMock()
    engine.setup_event_journal(mock_journal)
    
    mock_risk = AsyncMock()
    mock_risk.authorize_signal_6gate.return_value = {
        'authorized': True,
        'authorized_quantity': 100,
        'gate_passed': 'G6'
    }
    engine.setup_risk_manager(mock_risk)
    
    mock_sig_mgr = MagicMock()
    mock_sig_mgr.submit_signal.return_value = "sig-1"
    engine.setup_signal_manager(mock_sig_mgr)
    
    signal = {"symbol": "AAPL", "side": "buy", "requested_quantity": 100}
    
    res = await engine.submit_signal(signal)
    
    assert res == "sig-1"
    mock_journal.log_signal.assert_called_once()
    mock_journal.log_risk_decision.assert_called_once()

@pytest.mark.asyncio
async def test_process_bar_with_strategy_manager(engine):
    """Test _process_bar with StrategyManager and adapters."""
    # Mock components
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = True
    mock_buffer.get_buffer.return_value = pd.DataFrame({'close': [100.0]})
    engine.setup_buffer_manager(mock_buffer)
    
    mock_ind = MagicMock()
    mock_ind.compute_indicators_batch.return_value = pd.DataFrame({
        'close': [100.0],
        'ind1': [1.0],
        'symbol': ['AAPL']
    })
    engine.setup_indicator_adapter(mock_ind)
    
    mock_feat = MagicMock()
    mock_feat.transform_single.return_value = {'feat1': 2.0}
    engine.setup_feature_adapter(mock_feat)
    
    mock_regime = MagicMock()
    engine.setup_regime_engine(mock_regime)
    
    mock_strat = AsyncMock()
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_ENTRY"
    sig.quantity_type = "ABSOLUTE"
    sig.target_quantity = 10
    mock_strat.generate_signals.return_value = [sig]
    engine.setup_strategy_manager(mock_strat)
    
    mock_broker = MagicMock()
    mock_broker.get_position.return_value = None
    mock_broker._prices = {"AAPL": 100.0}
    engine.setup_paper_broker(mock_broker)
    
    # Mock submit_signal
    engine.submit_signal = AsyncMock(return_value="sig-1")
    
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {'symbol': 'AAPL', 'close': 100.0, 'open': 99.0}
    event.market_timestamp = datetime.now(timezone.utc)
    engine._expected_symbols = ["AAPL"]
    
    await engine._process_bar(event)
    
    mock_ind.compute_indicators_batch.assert_called_once()
    mock_feat.transform_single.assert_called_once()
    mock_regime.evaluate_regime_causal.assert_called_once()
    mock_strat.generate_signals.assert_called_once()
    engine.submit_signal.assert_called_once()

def test_normalize_strategy_signal_complex_branches(engine):
    """Test _normalize_strategy_signal remaining branches."""
    mock_risk = MagicMock()
    # Case: SHORT_ENTRY while long -> close long
    mock_risk.current_positions = {"AAPL": 100}
    engine.setup_risk_manager(mock_risk)
    
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "SHORT_ENTRY"
    sig.quantity_type = "ABSOLUTE"
    
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "sell"
    assert res['requested_quantity'] == 100.0
    
    # Case: LONG_ENTRY while short -> cover short
    mock_risk.current_positions = {"AAPL": -50}
    sig.signal_type.value = "LONG_ENTRY"
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "buy"
    assert res['requested_quantity'] == 50.0
    
    # Case: Legacy "sell" while long
    mock_risk.current_positions = {"AAPL": 100}
    sig.signal_type.value = "sell"
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "sell"
    assert res['requested_quantity'] == 100.0
    
    # Case: Legacy "buy" while short
    mock_risk.current_positions = {"AAPL": -50}
    sig.signal_type.value = "buy"
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['side'] == "buy"
    assert res['requested_quantity'] == 50.0

@pytest.mark.asyncio
async def test_execute_pending_signals_regime_context(engine):
    """Test _execute_pending_signals_for_symbol with regime context."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 100
    sig.signal_id = "s1"
    sig.metadata = {"authorization_id": "auth-1"}
    
    engine._pending_open_signals = [sig]
    engine._execution_count = 1 # Not the first execution
    
    mock_oms = AsyncMock()
    order = MagicMock()
    order.order_id = "o1"
    mock_oms.create_order.return_value = order
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    mock_exec.execute_with_mode_routing.return_value = MagicMock(status="FILLED", fill_quantity=100)
    engine.setup_execution_engine(mock_exec)
    
    mock_regime = MagicMock()
    mock_regime.get_current_regime_context.return_value = {"regime": "bull"}
    engine.setup_regime_engine(mock_regime)
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 151.0}, datetime.now(timezone.utc))
    
    mock_exec.execute_with_mode_routing.assert_called_once()
    req = mock_exec.execute_with_mode_routing.call_args[0][0]
    assert req.strategy_context["regime_context"] == {"regime": "bull"}

@pytest.mark.asyncio
async def test_process_fill_idempotency(engine):
    """Test _process_fill with idempotency and risk manager."""
    mock_idempotency = MagicMock()
    mock_idempotency.check_and_mark.return_value = True # Duplicate
    engine.setup_idempotency_tracker(mock_idempotency)
    
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {'fill_id': 'f1'}
    
    await engine._process_fill(event)
    assert engine._stats['fills_received'] == 1
    # Should return early due to duplicate

@pytest.mark.asyncio
async def test_run_loop_watchdog_and_checkpoint(engine):
    """Test run loop with watchdog and checkpointing."""
    engine._state = PaperTradingState.RUNNING
    engine._running = True
    
    mock_dispatcher = MagicMock()
    event = MagicMock()
    event.event_type = EventType.BAR
    event.event_id = None
    mock_dispatcher.process_next.side_effect = [event, None]
    engine.setup_dispatcher(mock_dispatcher)
    
    mock_watchdog = MagicMock()
    mock_watchdog.start_async_monitor.return_value = MagicMock()
    engine.setup_watchdog(mock_watchdog)
    
    mock_state_mgr = MagicMock()
    mock_state_mgr.increment_bars.return_value = True # Trigger checkpoint
    engine.setup_state_manager(mock_state_mgr)
    
    # Mock _process_event to avoid side effects
    engine._process_event = AsyncMock()
    
    # Run loop will process one event then we stop it
    async def stop_soon():
        await asyncio.sleep(0.05)
        engine._running = False
        
    asyncio.create_task(stop_soon())
    await engine.run()
    
    mock_watchdog.on_bar_processed.assert_called_once()
    mock_state_mgr.create_checkpoint.assert_called_with('periodic')

@pytest.mark.asyncio
async def test_process_bar_position_details(engine):
    """Test _process_bar building position details for StrategyManager."""
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = True
    mock_buffer.get_buffer.return_value = pd.DataFrame({'close': [100.0]})
    engine.setup_buffer_manager(mock_buffer)
    
    mock_ind = MagicMock()
    mock_ind.compute_indicators_batch.return_value = pd.DataFrame({'close': [100.0], 'symbol': ['AAPL']})
    engine.setup_indicator_adapter(mock_ind)
    
    mock_strat = AsyncMock()
    engine.setup_strategy_manager(mock_strat)
    
    mock_broker = MagicMock()
    pos = MagicMock()
    pos.quantity = 100
    pos.avg_entry_price = 90.0
    pos.current_price = 100.0
    pos.unrealized_pl = 1000.0
    pos.unrealized_plpc = 0.11
    mock_broker.get_position.return_value = pos
    mock_broker._prices = {"AAPL": 100.0}
    engine.setup_paper_broker(mock_broker)
    
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {'symbol': 'AAPL', 'close': 100.0}
    event.market_timestamp = datetime.now(timezone.utc)
    engine._expected_symbols = ["AAPL"]
    
    await engine._process_bar(event)
    
    mock_strat.generate_signals.assert_called_once()
    call_args = mock_strat.generate_signals.call_args[1]
    assert "AAPL" in call_args["position_details"]
    pos_details = call_args["position_details"]["AAPL"]
    assert pos_details["quantity"] == 100.0
    assert pos_details["unrealized_pnl"] == 1000.0

def test_normalize_strategy_signal_price_fallbacks(engine):
    """Test _normalize_strategy_signal price fallbacks."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_ENTRY"
    sig.quantity_type = "ABSOLUTE"
    sig.target_quantity = 10
    sig.price = 0.0 # No price on signal
    
    mock_broker = MagicMock()
    mock_broker.get_latest_quote.return_value = {"last_price": 155.0}
    engine.setup_paper_broker(mock_broker)
    
    # Should fallback to broker quote
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 0.0)
    assert res['arrival_price'] == 155.0
    
    # Should fallback to 100.0 if everything fails
    mock_broker.get_latest_quote.return_value = None
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 0.0)
    assert res['arrival_price'] == 100.0

@pytest.mark.asyncio
async def test_execute_pending_signals_decision_price_fallbacks(engine):
    """Test _execute_pending_signals_for_symbol decision price fallbacks."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 100
    sig.arrival_price = None
    sig.metadata = {}
    
    engine._pending_open_signals = [sig]
    
    mock_oms = AsyncMock()
    mock_oms.create_order.return_value = MagicMock(order_id="o1")
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    mock_exec.execute_with_mode_routing.return_value = MagicMock(status="FILLED")
    engine.setup_execution_engine(mock_exec)
    
    # Should fallback to open_price
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 152.0}, datetime.now(timezone.utc))
    
    req = mock_exec.execute_with_mode_routing.call_args[0][0]
    assert req.strategy_context["decision_price"] == 152.0

@pytest.mark.asyncio
async def test_submit_signal_risk_details(engine):
    """Test submit_signal with risk authorization details."""
    mock_risk = AsyncMock()
    mock_risk.authorize_signal_6gate.return_value = {
        'authorized': True,
        'authorized_quantity': 50,
        'gate_passed': 'G4',
        'max_loss_estimate': 500.0,
        'estimated_fill_price': 150.0
    }
    engine.setup_risk_manager(mock_risk)
    
    mock_sig_mgr = MagicMock()
    mock_sig_mgr.submit_signal.return_value = "sig-1"
    engine.setup_signal_manager(mock_sig_mgr)
    
    signal = {"symbol": "AAPL", "side": "buy", "requested_quantity": 100}
    
    await engine.submit_signal(signal)
    
    mock_sig_mgr.submit_signal.assert_called_once()
    enhanced_sig = mock_sig_mgr.submit_signal.call_args[0][0]
    assert enhanced_sig.requested_quantity == 50
    assert enhanced_sig.metadata['gate_passed'] == 'G4'
    assert enhanced_sig.metadata['max_loss_estimate'] == 500.0

def test_watchdog_callbacks(engine):
    """Test watchdog callbacks setup in initialize."""
    mock_watchdog = AsyncMock()
    engine.setup_watchdog(mock_watchdog)
    
    mock_state_mgr = AsyncMock()
    engine.setup_state_manager(mock_state_mgr)
    
    # We need to run initialize to set callbacks
    # Mock other required components
    engine.setup_time_source(MagicMock())
    engine.setup_buffer_manager(MagicMock())
    engine.setup_signal_manager(MagicMock())
    engine.setup_paper_broker(MagicMock())
    
    asyncio.run(engine.initialize())
    
    mock_watchdog.set_callbacks.assert_called_once()
    callbacks = mock_watchdog.set_callbacks.call_args[1]
    
    # Test the callbacks
    callbacks['on_warning']()
    callbacks['on_critical']()
    mock_state_mgr.create_checkpoint.assert_called_with('critical')
    
    callbacks['on_stall']()
    mock_state_mgr.create_checkpoint.assert_called_with('stall')

def test_normalize_strategy_signal_percentage_risk_pv(engine):
    """Test _normalize_strategy_signal PERCENTAGE sizing with risk manager PV."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.signal_type.value = "LONG_ENTRY"
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = 0.1
    
    mock_risk = MagicMock()
    mock_risk.portfolio_value = 200000.0
    engine.setup_risk_manager(mock_risk)
    
    mock_broker = MagicMock()
    acct = MagicMock()
    acct.portfolio_value = 100000.0
    mock_broker.get_account_info.return_value = acct
    engine.setup_paper_broker(mock_broker)
    
    # 10% of 200k (from risk mgr) = 20k. At $100/share = 200 shares.
    res = engine._normalize_strategy_signal(sig, datetime.now(timezone.utc), 100.0)
    assert res['requested_quantity'] == 200.0

@pytest.mark.asyncio
async def test_execute_pending_signals_metadata_price(engine):
    """Test _execute_pending_signals_for_symbol with decision price from metadata."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 100
    sig.arrival_price = None
    sig.metadata = {"arrival_price": 153.0}
    
    engine._pending_open_signals = [sig]
    
    mock_oms = AsyncMock()
    mock_oms.create_order.return_value = MagicMock(order_id="o1")
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    mock_exec.execute_with_mode_routing.return_value = MagicMock(status="FILLED")
    engine.setup_execution_engine(mock_exec)
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 152.0}, datetime.now(timezone.utc))
    
    req = mock_exec.execute_with_mode_routing.call_args[0][0]
    assert req.strategy_context["decision_price"] == 153.0

@pytest.mark.asyncio
async def test_execute_pending_signals_current_regime(engine):
    """Test _execute_pending_signals_for_symbol with regime context from current_regime."""
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.side = "buy"
    sig.requested_quantity = 100
    engine._pending_open_signals = [sig]
    engine._execution_count = 1
    
    mock_oms = AsyncMock()
    mock_oms.create_order.return_value = MagicMock(order_id="o1")
    engine.setup_oms(mock_oms)
    
    mock_exec = AsyncMock()
    mock_exec.execute_with_mode_routing.return_value = MagicMock(status="FILLED")
    engine.setup_execution_engine(mock_exec)
    
    mock_regime = MagicMock()
    del mock_regime.get_current_regime_context # Force fallback
    mock_regime.current_regime = {"state": "trending"}
    engine.setup_regime_engine(mock_regime)
    
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 152.0}, datetime.now(timezone.utc))
    
    req = mock_exec.execute_with_mode_routing.call_args[0][0]
    assert req.strategy_context["regime_context"] == {"state": "trending"}

@pytest.mark.asyncio
async def test_process_fill_enum_side(engine):
    """Test _process_fill with Enum side."""
    from enum import Enum
    class Side(Enum):
        BUY = "buy"
    
    mock_risk = AsyncMock()
    engine.setup_risk_manager(mock_risk)
    
    event = MagicMock()
    event.symbol = 'AAPL'
    event.payload = {
        'fill_id': 'f1',
        'quantity': 10,
        'price': 100,
        'side': Side.BUY,
        'timestamp': datetime.now(timezone.utc)
    }
    
    await engine._process_fill(event)
    
    mock_risk.update_position.assert_called_once()
    args = mock_risk.update_position.call_args[1]
    assert args['side'] == "buy"

@pytest.mark.asyncio
async def test_run_loop_heartbeat(engine):
    """Test run loop with heartbeat events."""
    engine._state = PaperTradingState.RUNNING
    engine._running = True
    
    mock_dispatcher = MagicMock()
    event = MagicMock()
    event.event_type = EventType.SYSTEM # Use SYSTEM as heartbeat
    mock_dispatcher.process_next.side_effect = [event, None]
    engine.setup_dispatcher(mock_dispatcher)
    
    mock_watchdog = MagicMock()
    mock_watchdog.start_async_monitor.return_value = MagicMock()
    engine.setup_watchdog(mock_watchdog)
    
    engine._process_event = AsyncMock()
    
    async def stop_soon():
        await asyncio.sleep(0.05)
        engine._running = False
        
    asyncio.create_task(stop_soon())
    await engine.run()
    
    mock_watchdog.on_heartbeat.assert_called_once()

@pytest.mark.asyncio
async def test_warmup_already_warmed(engine):
    """Test warmup when symbols are already warmed up."""
    mock_buffer = MagicMock()
    mock_buffer.is_warmed_up.return_value = True
    engine.setup_buffer_manager(mock_buffer)
    
    result = await engine.warmup(["AAPL"])
    
    assert result is True

@pytest.mark.asyncio
async def test_run_loop_cancelled(engine):
    """Test run loop cancellation."""
    engine._state = PaperTradingState.RUNNING
    mock_dispatcher = MagicMock()
    mock_dispatcher.process_next.return_value = None
    engine.setup_dispatcher(mock_dispatcher)
    
    run_task = asyncio.create_task(engine.run())
    await asyncio.sleep(0.01)
    run_task.cancel()
    
    try:
        await run_task
    except asyncio.CancelledError:
        pass
    
    assert engine._running is False

@pytest.mark.asyncio
async def test_process_event_quote_trade_no_price(engine):
    """Test quote/trade event without price."""
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    event = MagicMock()
    event.event_type = EventType.QUOTE
    event.symbol = "AAPL"
    event.payload = {} # No price
    event.event_id = "q1"
    
    await engine._process_event(event)
    mock_broker.set_price.assert_not_called()

@pytest.mark.asyncio
async def test_process_bar_broker_market_data_exception(engine):
    """Test exception in broker.set_market_data."""
    mock_broker = MagicMock()
    mock_broker.set_market_data.side_effect = Exception("Broker error")
    engine.setup_paper_broker(mock_broker)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    # Should not raise
    await engine._process_bar(event)
    assert engine.get_stats()['bars_processed'] == 1

@pytest.mark.asyncio
async def test_process_bar_fill_draining_exceptions(engine):
    """Test various exceptions during fill draining."""
    mock_dispatcher = MagicMock()
    engine.setup_dispatcher(mock_dispatcher)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    # 1. peek_next exception
    mock_dispatcher.peek_next.side_effect = Exception("Peek error")
    await engine._process_bar(event)
    
    # 2. event_type exception
    fill_event = MagicMock()
    type(fill_event.event_type).name = PropertyMock(side_effect=Exception("Type error"))
    fill_event.event_type.__str__.return_value = "UNKNOWN"
    mock_dispatcher.peek_next.side_effect = [fill_event, None]
    await engine._process_bar(event)
    
    # 3. market_timestamp exception
    fill_event = MagicMock()
    fill_event.event_type = EventType.FILL
    type(fill_event).market_timestamp = PropertyMock(side_effect=Exception("TS error"))
    mock_dispatcher.peek_next.side_effect = [fill_event, None]
    await engine._process_bar(event)

@pytest.mark.asyncio
async def test_indicator_adapter_batch_edge_cases(engine):
    """Test indicator adapter batch edge cases."""
    mock_indicators = MagicMock()
    engine.setup_indicator_adapter(mock_indicators)
    
    # 1. Empty batch
    mock_indicators.compute_indicators_batch.return_value = None
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    await engine._process_bar(event)
    
    # 2. No symbol column, and exception in column processing
    df = pd.DataFrame([{"timestamp": datetime.now(timezone.utc), "close": 105, "ind1": "invalid"}])
    # ind1 is string, float(val) will fail
    mock_indicators.compute_indicators_batch.return_value = df
    
    await engine._process_bar(event)
    # Should not raise

@pytest.mark.asyncio
async def test_feature_adapter_runtime_error(engine):
    """Test feature adapter runtime error."""
    mock_indicators = MagicMock()
    engine.setup_indicator_adapter(mock_indicators)
    mock_features = MagicMock()
    engine.setup_feature_adapter(mock_features)
    
    df = pd.DataFrame([{"timestamp": datetime.now(timezone.utc), "close": 105, "ind1": 1.0}])
    mock_indicators.compute_indicators_batch.return_value = df
    mock_features.transform_single.side_effect = RuntimeError("Scalers not loaded")
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    await engine._process_bar(event)
    # Should not raise

@pytest.mark.asyncio
async def test_process_bar_no_buffer(engine):
    """Test process_bar when buffer is None."""
    mock_buffer = MagicMock()
    mock_buffer.get_buffer.return_value = None
    engine.setup_buffer_manager(mock_buffer)
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    await engine._process_bar(event)
    # Should skip indicator/regime steps

@pytest.mark.asyncio
async def test_process_bar_position_details_exception(engine):
    """Test exception in building position details."""
    mock_broker = MagicMock()
    mock_broker.get_position.side_effect = Exception("Broker error")
    engine.setup_paper_broker(mock_broker)
    
    engine._expected_symbols = ["AAPL"]
    
    mock_indicators = MagicMock()
    engine.setup_indicator_adapter(mock_indicators)
    
    df = pd.DataFrame([{"timestamp": datetime.now(timezone.utc), "close": 105}])
    mock_indicators.compute_indicators_batch.return_value = df
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    await engine._process_bar(event)
    # Should log error and continue with position_details=None

@pytest.mark.asyncio
async def test_strategy_manager_backwards_compat(engine):
    """Test StrategyManager backwards compatibility (TypeError)."""
    engine._expected_symbols = ["AAPL"]
    mock_indicators = MagicMock()
    engine.setup_indicator_adapter(mock_indicators)
    
    mock_buffer = MagicMock()
    mock_buffer.get_buffer.return_value = pd.DataFrame([{"close": 100}])
    engine.setup_buffer_manager(mock_buffer)
    
    df = pd.DataFrame([{"timestamp": datetime.now(timezone.utc), "close": 105}])
    mock_indicators.compute_indicators_batch.return_value = df
    
    mock_strategy = AsyncMock()
    engine.setup_strategy_manager(mock_strategy)
    
    # Mock generate_signals to raise TypeError on first call (with position_details)
    # and succeed on second call (without position_details)
    mock_strategy.generate_signals.side_effect = [
        TypeError("unexpected keyword argument 'position_details'"),
        []
    ]
    
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"close": 105}
    event.market_timestamp = datetime.now(timezone.utc)
    event.event_id = "b1"
    
    await engine._process_bar(event)
    assert mock_strategy.generate_signals.call_count == 2

@pytest.mark.asyncio
async def test_normalize_strategy_signal_edge_cases(engine):
    """Test normalize_strategy_signal edge cases."""
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    mock_risk = MagicMock()
    engine.setup_risk_manager(mock_risk)
    
    # 1. No symbol
    sig = MagicMock()
    sig.symbol = None
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None
    
    # 2. Unknown signal type
    sig.symbol = "AAPL"
    sig.signal_type = "UNKNOWN"
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None
    
    # 3. Percentage without weight
    sig.signal_type = "LONG_ENTRY"
    sig.quantity_type = "PERCENTAGE"
    sig.target_weight = None
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None
    
    # 4. Exception in percentage calculation
    sig.target_weight = 0.1
    mock_broker.get_account_info.side_effect = Exception("Account error")
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None
    
    # 5. Exception in exit sizing
    mock_broker.get_account_info.side_effect = None
    type(mock_risk).current_positions = PropertyMock(side_effect=Exception("Risk error"))
    # Should still return a signal if qty > 0 from other logic, but here it might fail
    # Let's just ensure it doesn't crash
    engine._normalize_strategy_signal(sig, datetime.now(timezone.utc))
    
    # 6. Qty <= 0
    sig.quantity_type = "ABSOLUTE"
    sig.target_quantity = 0
    sig.quantity = 0
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None
    
    # 7. Outer exception
    type(sig).symbol = PropertyMock(side_effect=Exception("Outer error"))
    assert engine._normalize_strategy_signal(sig, datetime.now(timezone.utc)) is None

@pytest.mark.asyncio
async def test_execute_pending_signals_edge_cases(engine):
    """Test execute_pending_signals edge cases."""
    mock_exec = AsyncMock()
    engine.setup_execution_engine(mock_exec)
    mock_regime = MagicMock()
    engine.setup_regime_engine(mock_regime)
    
    # 1. No open price
    sig = MagicMock()
    sig.symbol = "AAPL"
    engine._pending_open_signals = [sig]
    await engine._execute_pending_signals_for_symbol("AAPL", {}, datetime.now(timezone.utc))
    assert len(engine._pending_open_signals) == 1 # Not processed
    
    # 2. Decision price exception
    engine._pending_open_signals = [sig]
    type(sig).arrival_price = PropertyMock(side_effect=Exception("Price error"))
    sig.metadata = {"arrival_price": 100}
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 100}, datetime.now(timezone.utc))
    # Should use metadata price
    
    # 3. Regime exception
    engine._pending_open_signals = [sig]
    engine._execution_count = 1 # Not first
    mock_regime.get_current_regime_context.side_effect = Exception("Regime error")
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 100}, datetime.now(timezone.utc))
    # Should continue with regime_ctx=None
    
    # 4. Execution exception
    engine._pending_open_signals = [sig]
    mock_exec.execute_with_mode_routing.side_effect = Exception("Exec error")
    await engine._execute_pending_signals_for_symbol("AAPL", {"open": 100}, datetime.now(timezone.utc))
    # Should log and continue

@pytest.mark.asyncio
async def test_process_fill_edge_cases(engine):
    """Test process_fill edge cases."""
    mock_risk = AsyncMock()
    engine.setup_risk_manager(mock_risk)
    
    # 1. No fill_id
    event = MagicMock()
    event.symbol = "AAPL"
    event.payload = {"quantity": 10, "price": 100, "side": "buy"}
    await engine._process_fill(event)
    assert engine.get_stats()['fills_received'] == 1
    
    # 2. RiskManager exception
    mock_risk.update_position.side_effect = Exception("Risk error")
    await engine._process_fill(event)
    # Should log and continue

@pytest.mark.asyncio
async def test_submit_signal_edge_cases(engine):
    """Test submit_signal edge cases."""
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    # 1. No price (arrival_price=0, no quote)
    mock_broker.get_latest_quote.return_value = None
    signal = {"symbol": "AAPL", "side": "buy", "requested_quantity": 10}
    await engine.submit_signal(signal)
    # Should use fallback price 100.0
    
    # 2. Metadata exception
    # This happens inside submit_signal when setting metadata on enhanced_signal
    # We need to mock EnhancedTradingSignal or just let it run
    # The code has a try-except around metadata setting
    pass

@pytest.mark.asyncio
async def test_check_eod_liquidation_edge_cases(engine):
    """Test check_eod_liquidation edge cases."""
    mock_broker = MagicMock()
    engine.setup_paper_broker(mock_broker)
    
    # 1. Time parse error
    engine.config.eod_close_time = "invalid"
    ts = datetime(2023, 1, 1, 16, 0, tzinfo=timezone.utc) # 4 PM
    await engine._check_eod_liquidation(ts, {"close": 100})
    # Should use default 15:55 and liquidate
    
    # 2. No broker
    engine._paper_broker = None
    assert await engine._check_eod_liquidation(ts, {"close": 100}) == 0
    
    # 3. Get positions exception
    engine.setup_paper_broker(mock_broker)
    engine._position_book = None
    mock_broker.get_all_positions.side_effect = Exception("Broker error")
    assert await engine._check_eod_liquidation(ts, {"close": 100}) == 0

@pytest.mark.asyncio
async def test_restore_from_checkpoint_no_manager(engine):
    """Test restore_from_checkpoint when state_manager is None."""
    engine._state_manager = None
    assert await engine.restore_from_checkpoint() is False
