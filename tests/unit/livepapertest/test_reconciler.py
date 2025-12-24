import pytest
import asyncio
from unittest.mock import MagicMock, patch, ANY
from livepapertest.ops.reconciler import IBKRReconciler, TradingPauseFlag, _book_positions_to_qty

@pytest.fixture
def mock_facade():
    facade = MagicMock()
    facade.refresh_account_info.return_value = MagicMock(cash=100000.0)
    facade.refresh_positions.return_value = None
    facade.get_all_positions.return_value = {
        "AAPL": MagicMock(quantity=100.0),
        "MSFT": MagicMock(quantity=50.0)
    }
    return facade

@pytest.fixture
def mock_position_book():
    pb = MagicMock()
    pb.get_cash_balance.return_value = 100000.0
    pos_aapl = MagicMock(quantity=100.0)
    pos_msft = MagicMock(quantity=50.0)
    pb.get_all_positions.return_value = {"AAPL": pos_aapl, "MSFT": pos_msft}
    return pb

def test_book_positions_to_qty(mock_position_book):
    qty_map = _book_positions_to_qty(mock_position_book)
    assert qty_map == {"AAPL": 100.0, "MSFT": 50.0}

@pytest.mark.asyncio
async def test_reconcile_positions_once_success(mock_facade, mock_position_book):
    reconciler = IBKRReconciler(facade=mock_facade, position_book=mock_position_book)
    ok, details = await reconciler.reconcile_positions_once()
    
    assert ok is True
    assert details["ok"] is True
    assert len(details["mismatches"]) == 0
    assert details["cash"]["diff"] == 0.0

@pytest.mark.asyncio
async def test_reconcile_positions_once_mismatch(mock_facade, mock_position_book):
    # Change IBKR quantity for AAPL
    mock_facade.get_all_positions.return_value["AAPL"].quantity = 101.0
    
    reconciler = IBKRReconciler(facade=mock_facade, position_book=mock_position_book)
    ok, details = await reconciler.reconcile_positions_once()
    
    assert ok is False
    assert len(details["mismatches"]) == 1
    assert details["mismatches"][0]["symbol"] == "AAPL"
    assert details["mismatches"][0]["position_book_qty"] == 100.0
    assert details["mismatches"][0]["ibkr_qty"] == 101.0

@pytest.mark.asyncio
async def test_reconcile_positions_once_cash_mismatch(mock_facade, mock_position_book):
    # Change IBKR cash
    mock_facade.refresh_account_info.return_value.cash = 99000.0
    
    reconciler = IBKRReconciler(facade=mock_facade, position_book=mock_position_book)
    ok, details = await reconciler.reconcile_positions_once()
    
    assert ok is False
    assert details["cash"]["diff"] == 1000.0

@pytest.mark.asyncio
async def test_reconcile_pause_on_mismatch(mock_facade, mock_position_book):
    mock_facade.get_all_positions.return_value["AAPL"].quantity = 101.0
    pause_flag = TradingPauseFlag()
    mock_journal = MagicMock()
    
    reconciler = IBKRReconciler(
        facade=mock_facade, 
        position_book=mock_position_book,
        pause_flag=pause_flag,
        journal=mock_journal,
        pause_on_mismatch=True
    )
    
    # Run one iteration of the loop (we'll mock sleep to exit)
    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
        try:
            await reconciler.run_positions_loop(interval_sec=0.1)
        except asyncio.CancelledError:
            pass
            
    assert pause_flag.paused is True
    assert pause_flag.reason == "reconcile_mismatch"
    mock_journal.log_system.assert_called_with("reconcile_mismatch", ANY)

@pytest.mark.asyncio
async def test_reconcile_loop_error_handling(mock_facade, mock_position_book):
    mock_facade.refresh_account_info.side_effect = Exception("Reconcile error")
    mock_journal = MagicMock()
    
    reconciler = IBKRReconciler(
        facade=mock_facade, 
        position_book=mock_position_book,
        journal=mock_journal
    )
    
    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
        try:
            await reconciler.run_positions_loop(interval_sec=0.1)
        except asyncio.CancelledError:
            pass
            
    mock_journal.log_system.assert_called_with("reconcile_error", ANY)
