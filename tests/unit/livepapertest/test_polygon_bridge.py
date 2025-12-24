import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from livepapertest.engine.polygon_live_bridge import PolygonToDispatcherBridge, BridgeStats
from core_engine.system.event_dispatcher import EventType

@pytest.fixture
def mock_dispatcher():
    dispatcher = MagicMock()
    dispatcher.enqueue.return_value = True
    return dispatcher

@pytest.fixture
def mock_id_gen():
    id_gen = MagicMock()
    id_gen.generate_event_id.return_value = "test_event_id"
    return id_gen

def test_bridge_on_bar_success(mock_dispatcher, mock_id_gen):
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen)
    
    bar = MagicMock()
    bar.timestamp_end = datetime.now(timezone.utc)
    bar.open = 100.0
    bar.high = 101.0
    bar.low = 99.0
    bar.close = 100.5
    bar.volume = 1000.0
    
    bridge.on_bar("AAPL", "minute", bar)
    
    assert bridge.stats["bars_enqueued"] == 1
    mock_dispatcher.enqueue.assert_called_once()
    assert bridge.last_bar_timestamp("AAPL") == bar.timestamp_end

def test_bridge_on_bar_out_of_order(mock_dispatcher, mock_id_gen):
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen)
    
    ts1 = datetime.now(timezone.utc)
    ts2 = ts1 - timedelta(minutes=1)
    
    bar1 = MagicMock(timestamp_end=ts1)
    bar2 = MagicMock(timestamp_end=ts2)
    
    bridge.on_bar("AAPL", "minute", bar1)
    bridge.on_bar("AAPL", "minute", bar2)
    
    assert bridge.stats["bars_enqueued"] == 1
    assert bridge.stats["dropped_out_of_order_bars"] == 1

def test_bridge_min_timestamp_filter(mock_dispatcher, mock_id_gen):
    min_ts = datetime.now(timezone.utc)
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen, min_source_timestamp=min_ts)
    
    old_bar = MagicMock(timestamp_end=min_ts - timedelta(minutes=1))
    bridge.on_bar("AAPL", "minute", old_bar)
    
    assert bridge.stats["bars_enqueued"] == 0
    assert bridge.stats["dropped_before_min_ts"] == 1
    
    # Per-symbol override
    new_min_ts = min_ts + timedelta(hours=1)
    bridge.set_min_source_timestamp(new_min_ts, symbol="MSFT")
    
    bar_msft = MagicMock(timestamp_end=min_ts + timedelta(minutes=30))
    bridge.on_bar("MSFT", "minute", bar_msft)
    assert bridge.stats["dropped_before_min_ts"] == 2

def test_bridge_on_trade_success(mock_dispatcher, mock_id_gen):
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen)
    
    trade = MagicMock()
    trade.timestamp = datetime.now(timezone.utc)
    trade.price = 150.0
    trade.size = 100.0
    
    bridge.on_trade("AAPL", trade)
    
    assert bridge.stats["trades_enqueued"] == 1
    mock_dispatcher.enqueue.assert_called_once()

def test_bridge_enqueue_failure(mock_dispatcher, mock_id_gen):
    mock_dispatcher.enqueue.return_value = False
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen)
    
    bar = MagicMock(timestamp_end=datetime.now(timezone.utc))
    bridge.on_bar("AAPL", "minute", bar)
    
    assert bridge.stats["dropped_enqueue_failed"] == 1

def test_bridge_set_min_ts_none(mock_dispatcher, mock_id_gen):
    bridge = PolygonToDispatcherBridge(dispatcher=mock_dispatcher, id_generator=mock_id_gen)
    bridge.set_min_source_timestamp(datetime.now(timezone.utc), symbol="AAPL")
    assert "AAPL" in bridge._min_ts_by_symbol
    
    bridge.set_min_source_timestamp(None, symbol="AAPL")
    assert "AAPL" not in bridge._min_ts_by_symbol
    
    bridge.set_min_source_timestamp(None, symbol="")
    # Should not crash
