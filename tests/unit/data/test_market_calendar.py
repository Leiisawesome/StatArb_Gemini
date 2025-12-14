"""
Tests for market_calendar.py

This module tests the MarketCalendar class which manages trading hours
and sessions for different asset classes (US_EQUITY, CRYPTO, FOREX).
"""

import pytest
from datetime import datetime, time, timezone
from core_engine.data.market_calendar import MarketCalendar, AssetClass, MarketSession

class TestAssetClass:
    """Test AssetClass enum values."""

    def test_asset_class_values(self):
        """Test that AssetClass enum has expected values."""
        assert AssetClass.US_EQUITY.value == "us_equity"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.FOREX.value == "forex"
        assert AssetClass.FUTURES.value == "futures"
        assert AssetClass.INTL_EQUITY.value == "intl_equity"

    def test_asset_class_members(self):
        """Test that all expected asset classes are present."""
        expected_classes = {"us_equity", "crypto", "forex", "futures", "intl_equity"}
        actual_classes = {cls.value for cls in AssetClass}
        assert actual_classes == expected_classes

class TestMarketSession:
    """Test MarketSession dataclass."""

    def test_market_session_creation(self):
        """Test creating a MarketSession instance."""
        session = MarketSession(
            open_time=time(9, 30),
            close_time=time(16, 0),
            timezone="America/New_York"
        )
        assert session.open_time == time(9, 30)
        assert session.close_time == time(16, 0)
        assert session.timezone == "America/New_York"

    def test_market_session_equality(self):
        """Test MarketSession equality comparison."""
        session1 = MarketSession(
            open_time=time(9, 30),
            close_time=time(16, 0),
            timezone="America/New_York"
        )
        session2 = MarketSession(
            open_time=time(9, 30),
            close_time=time(16, 0),
            timezone="America/New_York"
        )
        assert session1 == session2

class TestMarketCalendar:
    """Test MarketCalendar class functionality."""

    def test_initialization(self):
        """Test MarketCalendar initialization."""
        calendar = MarketCalendar()
        assert calendar is not None
        assert isinstance(calendar, MarketCalendar)

    @pytest.mark.parametrize("symbol,expected_asset_class", [
        ("AAPL", AssetClass.US_EQUITY),
        ("SPY", AssetClass.US_EQUITY),
        ("BTC-USD", AssetClass.CRYPTO),
        ("ETH-USD", AssetClass.CRYPTO),
        ("BTC", AssetClass.CRYPTO),
        ("ETH", AssetClass.CRYPTO),
        ("EUR/USD", AssetClass.FOREX),
        ("GBP/USD", AssetClass.FOREX),
        ("USD/JPY", AssetClass.FOREX),
        ("UNKNOWN", AssetClass.US_EQUITY),  # Default fallback
    ])
    def test_get_asset_class(self, symbol, expected_asset_class):
        """Test asset class detection for various symbols."""
        calendar = MarketCalendar()
        assert calendar.get_asset_class(symbol) == expected_asset_class

    def test_get_session_times_us_equity_weekday(self):
        """Test US equity session times on a weekday."""
        calendar = MarketCalendar()

        # Test Monday (weekday)
        monday = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)  # Monday
        open_dt, close_dt = calendar.get_session_times(monday, AssetClass.US_EQUITY)

        # US Equity: 9:30 AM - 4:00 PM ET
        # In UTC: 9:30 AM ET = 13:30 UTC, 4:00 PM ET = 20:00 UTC
        expected_open = monday.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = monday.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_us_equity_weekend(self):
        """Test US equity session times on a weekend."""
        calendar = MarketCalendar()

        # Test Saturday
        saturday = datetime(2023, 10, 7, 12, 0, tzinfo=timezone.utc)  # Saturday
        open_dt, close_dt = calendar.get_session_times(saturday, AssetClass.US_EQUITY)

        # Should still return session times even on weekend
        expected_open = saturday.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = saturday.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_crypto(self):
        """Test crypto session times (24/7)."""
        calendar = MarketCalendar()

        # Test Monday
        monday = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(monday, AssetClass.CRYPTO)

        expected_open = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_close = monday.replace(hour=23, minute=59, second=59, microsecond=999999)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_forex(self):
        """Test forex session times (24/5)."""
        calendar = MarketCalendar()

        # Test weekday
        monday = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(monday, AssetClass.FOREX)

        expected_open = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        expected_close = monday.replace(hour=23, minute=59, second=59, microsecond=999999)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_holidays(self):
        """Test session times on US holidays."""
        calendar = MarketCalendar()

        # Test Christmas Day 2023 (Monday)
        christmas = datetime(2023, 12, 25, 12, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(christmas, AssetClass.US_EQUITY)

        # Should still return regular session times (holiday logic not implemented yet)
        expected_open = christmas.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = christmas.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_pre_market_hours(self):
        """Test session times during pre-market hours."""
        calendar = MarketCalendar()

        # 6:00 AM ET on Monday (pre-market)
        pre_market = datetime(2023, 10, 2, 11, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(pre_market, AssetClass.US_EQUITY)

        # Should return regular session times for that day
        expected_open = pre_market.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = pre_market.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_after_hours(self):
        """Test session times after market close."""
        calendar = MarketCalendar()

        # 8:00 PM ET on Monday (after hours)
        after_hours = datetime(2023, 10, 2, 23, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(after_hours, AssetClass.US_EQUITY)

        # Should return regular session times for that day
        expected_open = after_hours.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = after_hours.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close

    def test_get_session_times_unknown_asset_class(self):
        """Test session times for unknown asset class (should default to US equity)."""
        calendar = MarketCalendar()

        # Test with FUTURES asset class (which has no session defined)
        monday = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)
        open_dt, close_dt = calendar.get_session_times(monday, AssetClass.FUTURES)

        # Should default to US equity session times
        expected_open = monday.replace(hour=9, minute=30, second=0, microsecond=0)
        expected_close = monday.replace(hour=16, minute=0, second=0, microsecond=0)

        assert open_dt == expected_open
        assert close_dt == expected_close