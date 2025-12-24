import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from livepapertest.broker.ibkr_paper_facade import LivePaperBrokerFacade, CachePolicy
from core_engine.type_definitions.broker_types import AccountInfo, Position

@pytest.fixture
def mock_ibkr():
    ibkr = MagicMock()
    ibkr.get_account_info.return_value = AccountInfo(
        account_id="DU123",
        cash=100000.0,
        buying_power=400000.0,
        portfolio_value=100000.0,
        equity=100000.0,
        timestamp=datetime.now(timezone.utc)
    )
    ibkr.get_positions.return_value = [
        Position(
            symbol="AAPL", 
            quantity=100.0, 
            avg_entry_price=150.0, 
            market_value=15500.0, 
            unrealized_pl=500.0, 
            unrealized_plpc=0.03, 
            current_price=155.0, 
            side="long", 
            cost_basis=15000.0,
            timestamp=datetime.now(timezone.utc)
        )
    ]
    return ibkr

@pytest.fixture
def mock_position_book():
    return MagicMock()

def test_facade_set_price(mock_ibkr, mock_position_book):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr, position_book=mock_position_book)
    
    # Valid price
    facade.set_price("AAPL", 150.5)
    quote = facade.get_latest_quote("AAPL")
    assert quote["last_price"] == 150.5
    mock_position_book.on_price_update.assert_called_with({"AAPL": Decimal("150.5")})
    
    # Invalid price (zero/negative)
    facade.set_price("MSFT", 0)
    assert facade.get_latest_quote("MSFT") is None
    
    # Invalid symbol
    facade.set_price("", 100)
    assert facade.get_latest_quote("") is None

def test_facade_set_market_data(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    bar = {"open": 100, "close": 101}
    ts = datetime.now(timezone.utc)
    
    facade.set_market_data("AAPL", bar, ts)
    with facade._lock:
        assert facade._last_bar["AAPL"] == bar
        assert facade._last_bar_ts["AAPL"] == ts

def test_facade_get_price_age(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    facade.set_price("AAPL", 150.0)
    
    age = facade.get_price_age_seconds("AAPL")
    assert age >= 0
    assert facade.get_price_age_seconds("NON_EXISTENT") is None

def test_facade_refresh_account(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    acc = facade.refresh_account_info()
    
    assert acc.account_id == "DU123"
    assert facade.get_account_info() == acc
    
    ts1, _ = facade.snapshot_timestamps()
    assert ts1 is not None

def test_facade_refresh_positions(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    positions = facade.refresh_positions()
    
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert facade.get_position("AAPL") == positions[0]
    assert len(facade.get_all_positions()) == 1
    
    _, ts2 = facade.snapshot_timestamps()
    assert ts2 is not None

def test_facade_get_account_info_fallback(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    # Should trigger refresh_account_info if cache is empty
    acc = facade.get_account_info()
    assert acc.account_id == "DU123"
    mock_ibkr.get_account_info.assert_called_once()

def test_facade_get_position_invalid(mock_ibkr):
    facade = LivePaperBrokerFacade(ibkr=mock_ibkr)
    assert facade.get_position("") is None
    assert facade.get_position(None) is None
