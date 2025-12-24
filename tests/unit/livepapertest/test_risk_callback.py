import pytest
from unittest.mock import MagicMock, AsyncMock
from livepapertest.execution.risk_manager_position_callback import RiskManagerPositionCallback

@pytest.mark.asyncio
async def test_risk_callback_update_position():
    mock_rm = AsyncMock()
    mock_journal = MagicMock()
    
    callback = RiskManagerPositionCallback(risk_manager=mock_rm, journal=mock_journal)
    
    await callback.update_position("AAPL", "buy", 100.0, 150.0)
    
    # Verify risk manager update
    mock_rm.update_position.assert_called_once_with(
        symbol="AAPL", side="buy", quantity=100.0, price=150.0
    )
    
    # Verify journal logging
    mock_journal.log_fill.assert_called_once()
    args, kwargs = mock_journal.log_fill.call_args
    assert kwargs["symbol"] == "AAPL"
    assert kwargs["side"] == "buy"
    assert kwargs["quantity"] == 100.0
    assert kwargs["price"] == 150.0
    assert kwargs["fill_id"].startswith("livefill:AAPL:buy:")

@pytest.mark.asyncio
async def test_risk_callback_no_journal():
    mock_rm = AsyncMock()
    callback = RiskManagerPositionCallback(risk_manager=mock_rm, journal=None)
    
    await callback.update_position("AAPL", "buy", 100.0, 150.0)
    
    mock_rm.update_position.assert_called_once()
    # No crash without journal

@pytest.mark.asyncio
async def test_risk_callback_journal_error():
    mock_rm = AsyncMock()
    mock_journal = MagicMock()
    mock_journal.log_fill.side_effect = Exception("Journal error")
    
    callback = RiskManagerPositionCallback(risk_manager=mock_rm, journal=mock_journal)
    
    # Should not raise exception
    await callback.update_position("AAPL", "buy", 100.0, 150.0)
    
    mock_rm.update_position.assert_called_once()
    mock_journal.log_fill.assert_called_once()
