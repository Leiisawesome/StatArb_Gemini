import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timezone
import pandas as pd
from core_engine.paper.engine import PaperTradingEngine, PaperTradingState
from core_engine.system.unified_execution_engine import ExecutionRequest, ExecutionAlgorithm

@pytest.mark.asyncio
async def test_surgical_coverage_v6():
    config = MagicMock()
    config.session_id = "test_session_v6"
    config.initial_cash = 100000.0
    
    engine = PaperTradingEngine(config)
    
    # 1. Trigger line 1229 (pause with state_manager)
    engine._state = PaperTradingState.RUNNING
    engine._state_manager = MagicMock()
    engine.pause()
    engine._state_manager.on_pause.assert_called_once()
    
    # 2. Trigger lines 1247, 1251-1252, 1256 (stop with components)
    engine._event_journal = MagicMock()
    engine._watchdog = MagicMock()
    engine.stop()
    engine._state_manager.on_shutdown.assert_called_once()
    engine._event_journal.log_system.assert_called_once()
    engine._event_journal.close.assert_called_once()
    engine._watchdog.stop.assert_called_once()

    # 3. Trigger line 1110 (pass in _process_fill with risk_budget)
    engine._risk_budget = MagicMock()
    fill_event = MagicMock()
    fill_event.payload = {"symbol": "AAPL", "quantity": 100, "price": 150.0, "side": "BUY"}
    await engine._process_fill(fill_event)
    # Line 1110 is just 'pass', so we just ensure it runs.

    # 4. Trigger line 1154 (submit_signal with quote fallback)
    engine._paper_broker = MagicMock()
    engine._paper_broker.get_latest_quote.return_value = {"last_price": 155.0}
    signal = {"symbol": "AAPL", "arrival_price": 0}
    # We need to mock _normalize_strategy_signal to return something
    engine._normalize_strategy_signal = MagicMock(return_value={"symbol": "AAPL", "quantity": 10})
    engine._oms = AsyncMock()
    await engine.submit_signal(signal)
    engine._paper_broker.get_latest_quote.assert_called_with("AAPL")

    # 5. Trigger line 886 (px = 100.0 fallback in _normalize_strategy_signal)
    # We need to call the real _normalize_strategy_signal
    # First, remove the mock
    engine._normalize_strategy_signal = PaperTradingEngine._normalize_strategy_signal.__get__(engine, PaperTradingEngine)
    
    engine._paper_broker.get_latest_quote.return_value = None
    s = MagicMock()
    s.symbol = "AAPL"
    s.weight = 0.1
    s.price = 0
    # Ensure portfolio_value > 0
    engine._risk_manager = MagicMock()
    engine._risk_manager.current_positions = {}
    res = engine._normalize_strategy_signal(s, datetime.now(timezone.utc))
    assert res is not None
    # If px was 100, and weight 0.1, portfolio 100000, qty = (0.1 * 100000) / 100 = 100
    assert res['quantity'] == 100

    # 6. Trigger lines 1024-1025, 1030-1031, 1050-1053 (exceptions in _execute_pending_signals_for_symbol)
    engine._execution_engine = AsyncMock()
    engine._oms = AsyncMock()
    engine._oms.create_order.return_value = MagicMock()
    
    class BadMetadata:
        def __contains__(self, key):
            raise Exception("Bad metadata")
    
    sig = MagicMock()
    sig.symbol = "AAPL"
    sig.metadata = BadMetadata()
    
    engine._execution_count = 1 # skip_regime_for_first_exec = False
    
    class BadRegimeEngine:
        @property
        def current_regime(self):
            raise Exception("Bad regime")
        def get_current_regime_context(self):
            raise Exception("Bad context")

    engine._regime_engine = BadRegimeEngine()
    
    # We need to pass a list of signals
    engine._pending_open_signals = {"AAPL": [sig]}
    await engine._execute_pending_signals_for_symbol("AAPL", {}, datetime.now(timezone.utc))
    # Check that it proceeded to execute
    engine._execution_engine.execute_with_mode_routing.assert_called()

    # 7. Trigger line 507 (await _execute_pending_signals_for_symbol in _process_bar)
    engine._pending_open_signals = {"AAPL": [MagicMock()]}
    engine._execution_engine = AsyncMock()
    engine._oms = AsyncMock()
    engine._paper_broker = MagicMock()
    event = MagicMock()
    event.payload = {"symbol": "AAPL", "bar": {"close": 150.0}}
    event.market_timestamp = datetime.now(timezone.utc)
    
    # Mock _execute_pending_signals_for_symbol to avoid deep recursion/errors
    engine._execute_pending_signals_for_symbol = AsyncMock()
    # Ensure it doesn't return early
    engine._buffer_manager = None 
    await engine._process_bar(event)
    engine._execute_pending_signals_for_symbol.assert_called_once()

    # 8. Trigger line 535 (break when fev is None in fill draining)
    engine._dispatcher = MagicMock()
    engine._dispatcher.peek_next.side_effect = [MagicMock(event_type=MagicMock(name="FILL"), market_timestamp=event.market_timestamp), None]
    engine._dispatcher.process_next.side_effect = [None] # Trigger line 535
    await engine._process_bar(event)
    
    # 9. Trigger lines 579-580, 591, 614-615
    engine._indicator_adapter = MagicMock()
    
    # Make it fail on access
    class BadSeries:
        def __getitem__(self, key):
            raise Exception("Bad series")
    
    # This is tricky because iloc[-1] returns a Series.
    # Let's mock the DataFrame to return a BadSeries on iloc[-1]
    mock_df = MagicMock(spec=pd.DataFrame)
    mock_df.columns = ["val"]
    mock_df.iloc = MagicMock()
    mock_df.iloc.__getitem__.return_value = BadSeries()
    mock_df.empty = False
    
    engine._indicator_adapter.get_indicators.return_value = mock_df
    engine._event_journal = MagicMock()
    engine._feature_adapter = MagicMock()
    engine._feature_adapter.transform_single.return_value = {"feat": 1.0}
    
    # For 614-615, we need enriched_df.at[...] = ... to fail
    # Let's just use a MagicMock for enriched_df
    mock_enriched = MagicMock(spec=pd.DataFrame)
    mock_enriched.columns = ["feat"]
    mock_enriched.index = [0]
    mock_at = MagicMock()
    mock_at.__setitem__.side_effect = Exception("Bad at")
    mock_enriched.at = mock_at

    # We need to get to line 600
    engine._strategy_manager = MagicMock()
    engine._expected_symbols = ["AAPL"]
    
    # We need to pass the check at line 544
    engine._buffer_manager = MagicMock()
    engine._buffer_manager.is_warmed_up.return_value = True
    
    # We need to pass the check at line 570
    # enriched_df = ind_df
    # So we need ind_df to be our mock_enriched
    engine._indicator_adapter.get_indicators.return_value = mock_enriched
    
    await engine._process_bar(event)
    engine._event_journal.log_features.assert_called() # Line 591

    # 10. Trigger lines 691-692 (sig_price is None)
    # This happens in the batch processing block
    engine._bar_batch_symbols = {"AAPL"}
    engine._bar_batch_market_data = {"AAPL": mock_enriched}
    # s.symbol = "MSFT" (not in batch)
    s2 = MagicMock()
    s2.symbol = "MSFT"
    engine._strategy_manager.generate_signals.return_value = [s2]
    engine._normalize_strategy_signal = MagicMock()
    
    # event.payload['bar'] has close
    event.payload = {"symbol": "AAPL", "bar": {"close": 200.0}}
    await engine._process_bar(event)
    # Check if _normalize_strategy_signal was called with bar_close_price=200.0
    engine._normalize_strategy_signal.assert_called()
    args, kwargs = engine._normalize_strategy_signal.call_args
    assert kwargs['bar_close_price'] == 200.0

    # 11. Trigger line 691-692 with bar.get('close_price')
    event.payload = {"symbol": "AAPL", "bar": {"close_price": 210.0}}
    await engine._process_bar(event)
    args, kwargs = engine._normalize_strategy_signal.call_args
    assert kwargs['bar_close_price'] == 210.0
