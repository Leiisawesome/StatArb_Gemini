import pytest
import asyncio
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
from livepapertest.ops.health import HealthReporter

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.get_stats.return_value = {
        "state": "running",
        "bars_processed": 100,
        "fills_received": 5,
        "orders_submitted": 10
    }
    return engine

@pytest.fixture
def mock_facade():
    facade = MagicMock()
    facade.get_price_age_seconds.return_value = 1.5
    facade.get_latest_quote.return_value = {"last_price": 150.0}
    return facade

@pytest.fixture
def mock_position_book():
    pb = MagicMock()
    snap = MagicMock()
    snap.net_exposure = 5000.0
    snap.cash_balance = 95000.0
    snap.positions = {"AAPL": MagicMock()}
    pb.get_snapshot.return_value = snap
    return pb

@pytest.fixture
def mock_bridge():
    bridge = MagicMock()
    bridge.last_bar_timestamp.return_value = datetime.now(timezone.utc) - timedelta(seconds=10)
    return bridge

def test_health_reporter_emit(mock_engine, mock_facade, mock_position_book, mock_bridge):
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=["AAPL"],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge,
        polygon_service=MagicMock(is_operational=True),
        ibkr_adapter=MagicMock(is_connected=lambda: True)
    )
    
    # Test emit doesn't crash
    reporter.emit()
    
    # Verify calls
    mock_engine.get_stats.assert_called_once()
    mock_facade.get_price_age_seconds.assert_called_with("AAPL")
    mock_position_book.get_snapshot.assert_called_once()

def test_health_reporter_emit_with_journal(mock_engine, mock_facade, mock_position_book, mock_bridge):
    mock_journal = MagicMock()
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=["AAPL"],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge,
        journal=mock_journal
    )
    
    reporter.emit()
    
    # Verify journal logging
    mock_journal.log_system.assert_called_once()
    args, kwargs = mock_journal.log_system.call_args
    assert args[0] == "health"
    assert "ts" in args[1]
    assert args[1]["engine"]["state"] == "running"

def test_health_reporter_emit_error_handling(mock_engine, mock_facade, mock_position_book, mock_bridge):
    # Mock an error in position book
    mock_position_book.get_snapshot.side_effect = Exception("PB Error")
    
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=["AAPL"],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge
    )
    
    # Should not raise exception
    reporter.emit()
    
    # Verify it still called other things
    mock_engine.get_stats.assert_called_once()

@pytest.mark.asyncio
async def test_health_reporter_run(mock_engine, mock_facade, mock_position_book, mock_bridge):
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=["AAPL"],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge
    )
    
    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
        try:
            await reporter.run(interval_sec=0.1)
        except asyncio.CancelledError:
            pass
    
    mock_engine.get_stats.assert_called()

def test_health_reporter_emit_no_stats(mock_engine, mock_facade, mock_position_book, mock_bridge):
    # Test with missing attributes on services
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=["AAPL"],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge,
        polygon_service=object(), # No is_operational
        ibkr_adapter=object() # No is_connected
    )
    
    reporter.emit()
    # Should not crash

def test_health_reporter_connectivity_exceptions(mock_engine, mock_facade, mock_position_book, mock_bridge):
    """Test health reporter when connectivity checks raise exceptions."""
    # Mock services that raise exceptions
    poly_service = MagicMock()
    type(poly_service).is_operational = PropertyMock(side_effect=Exception("Poly error"))
    
    ib_adapter = MagicMock()
    ib_adapter.is_connected.side_effect = Exception("IB error")

    reporter = HealthReporter(
        engine=mock_engine,
        symbols=[],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge,
        polygon_service=poly_service,
        ibkr_adapter=ib_adapter
    )

    reporter.emit()
    # Should not crash

def test_health_reporter_portfolio_exception(mock_engine, mock_facade, mock_position_book, mock_bridge):
    """Test health reporter when position book raises exception."""
    mock_position_book.get_snapshot.side_effect = Exception("Book error")
    mock_position_book.get_cash_balance.side_effect = Exception("Cash error")

    reporter = HealthReporter(
        engine=mock_engine,
        symbols=[],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge
    )

    reporter.emit()
    # Should not crash

@pytest.mark.asyncio
async def test_health_reporter_run_exception_loop(mock_engine, mock_facade, mock_position_book, mock_bridge):
    """Test health reporter run loop handles exceptions in emit."""
    reporter = HealthReporter(
        engine=mock_engine,
        symbols=[],
        facade=mock_facade,
        position_book=mock_position_book,
        bridge=mock_bridge
    )
    
    with patch.object(reporter, 'emit', side_effect=[Exception("Fail"), asyncio.CancelledError()]):
        with patch("asyncio.sleep", return_value=None):
            try:
                await reporter.run(0.01)
            except asyncio.CancelledError:
                pass
        assert reporter.emit.call_count == 2
