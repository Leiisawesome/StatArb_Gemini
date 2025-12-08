"""
Test historical data retrieval from IBKR.
Tests OHLCV bar data fetching for backtesting and analysis.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
from core_engine.config.broker_config import load_broker_config


def create_ibkr_adapter(client_id: int = 1):
    """Create IBKR adapter with specified client ID"""
    config = load_broker_config()
    # Modify client_id for this test
    config.interactive_brokers.client_id = client_id
    return IBKRAdapter(config.interactive_brokers)


def test_get_1min_bars():
    """Test retrieving 1-minute bars."""
    print("\n" + "="*80)
    print("TEST: Get 1-Minute Historical Bars for SPY")
    print("="*80)

    adapter = create_ibkr_adapter(client_id=1)
    adapter.connect()

    # Get last 100 1-minute bars
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Min",
        limit=100
    )

    # Assertions
    assert bars is not None, "Bars should not be None"
    assert len(bars) > 0, "Should have bars"
    assert len(bars) <= 100, "Should not exceed limit"

    # Check structure of first bar
    first_bar = bars[0]
    assert 'timestamp' in first_bar
    assert 'open' in first_bar
    assert 'high' in first_bar
    assert 'low' in first_bar
    assert 'close' in first_bar
    assert 'volume' in first_bar

    # Validate price relationships
    assert first_bar['high'] >= first_bar['open']
    assert first_bar['high'] >= first_bar['close']
    assert first_bar['low'] <= first_bar['open']
    assert first_bar['low'] <= first_bar['close']
    assert first_bar['high'] >= first_bar['low']

    # Validate positive values
    assert first_bar['open'] > 0
    assert first_bar['volume'] >= 0

    # Display results
    print(f"\n✅ Retrieved {len(bars)} 1-minute bars for SPY")
    print(f"\nFirst bar ({bars[0]['timestamp']}):")
    print(f"  Open:   ${bars[0]['open']:.2f}")
    print(f"  High:   ${bars[0]['high']:.2f}")
    print(f"  Low:    ${bars[0]['low']:.2f}")
    print(f"  Close:  ${bars[0]['close']:.2f}")
    print(f"  Volume: {bars[0]['volume']:,}")

    print(f"\nLast bar ({bars[-1]['timestamp']}):")
    print(f"  Open:   ${bars[-1]['open']:.2f}")
    print(f"  High:   ${bars[-1]['high']:.2f}")
    print(f"  Low:    ${bars[-1]['low']:.2f}")
    print(f"  Close:  ${bars[-1]['close']:.2f}")
    print(f"  Volume: {bars[-1]['volume']:,}")

    # Calculate return
    total_return = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open']
    print(f"\nReturn over period: {total_return * 100:.2f}%")

    adapter.disconnect()


def test_get_daily_bars():
    """Test retrieving daily bars."""
    print("\n" + "="*80)
    print("TEST: Get Daily Historical Bars for AAPL")
    print("="*80)

    adapter = create_ibkr_adapter(client_id=2)
    adapter.connect()

    # Get last 30 daily bars
    bars = adapter.get_historical_bars(
        symbol="AAPL",
        timeframe="1Day",
        limit=30
    )

    # Assertions
    assert bars is not None
    assert len(bars) > 0
    assert len(bars) <= 30

    # Display results
    print(f"\n✅ Retrieved {len(bars)} daily bars for AAPL")
    print(f"\nDate Range: {bars[0]['timestamp'].date()} to {bars[-1]['timestamp'].date()}")

    # Calculate some statistics
    highs = [b['high'] for b in bars]
    lows = [b['low'] for b in bars]
    volumes = [b['volume'] for b in bars]

    print(f"\nStatistics over {len(bars)} days:")
    print(f"  Highest price: ${max(highs):.2f}")
    print(f"  Lowest price:  ${min(lows):.2f}")
    print(f"  Avg volume:    {sum(volumes) // len(volumes):,}")
    print(f"  Total return:  {((bars[-1]['close'] - bars[0]['open']) / bars[0]['open'] * 100):.2f}%")

    adapter.disconnect()


def test_get_bars_with_date_range():
    """Test retrieving bars with specific date range."""
    print("\n" + "="*80)
    print("TEST: Get Bars with Specific Date Range")
    print("="*80)

    adapter = create_ibkr_adapter(client_id=3)
    adapter.connect()

    # Get last 5 trading days
    end = datetime.now()
    start = end - timedelta(days=7)  # 7 calendar days = ~5 trading days

    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Day",
        start=start,
        end=end
    )

    # Assertions
    assert bars is not None
    assert len(bars) > 0

    print(f"\n✅ Retrieved {len(bars)} bars from {start.date()} to {end.date()}")

    # Verify bars are within date range
    for bar in bars:
        assert start <= bar['timestamp'] <= end, f"Bar timestamp {bar['timestamp']} outside range"

    adapter.disconnect()


def test_multiple_timeframes():
    """Test different timeframe options."""
    print("\n" + "="*80)
    print("TEST: Multiple Timeframes for SPY")
    print("="*80)

    adapter = create_ibkr_adapter(client_id=4)
    adapter.connect()

    timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]

    print(f"\nTesting {len(timeframes)} timeframes:")
    for tf in timeframes:
        bars = adapter.get_historical_bars(
            symbol="SPY",
            timeframe=tf,
            limit=10
        )

        assert bars is not None
        assert len(bars) > 0, f"No bars for {tf}"

        print(f"  {tf:6s}: {len(bars):3d} bars | Latest: ${bars[-1]['close']:.2f}")

    print("\n✅ All timeframes working")

    adapter.disconnect()


def test_invalid_inputs():
    """Test error handling for invalid inputs."""
    print("\n" + "="*80)
    print("TEST: Invalid Input Handling")
    print("="*80)

    adapter = create_ibkr_adapter(client_id=5)
    adapter.connect()

    # Invalid timeframe
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="INVALID",
        limit=10
    )
    assert bars == [], "Should return empty list for invalid timeframe"
    print("  ✅ Invalid timeframe handled")

    # Invalid symbol
    bars = adapter.get_historical_bars(
        symbol="INVALID_SYMBOL_XYZ_12345",
        timeframe="1Day",
        limit=10
    )
    assert bars == [], "Should return empty list for invalid symbol"
    print("  ✅ Invalid symbol handled")

    # Invalid date range (start > end)
    end = datetime.now()
    start = end + timedelta(days=1)  # Start in future
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Day",
        start=start,
        end=end
    )
    assert bars == [], "Should return empty list for invalid date range"
    print("  ✅ Invalid date range handled")

    print("\n✅ Error handling working correctly")

    adapter.disconnect()


if __name__ == "__main__":
    # Run tests directly
    print("Running historical data tests...")

    test_get_1min_bars()
    test_get_daily_bars()
    test_get_bars_with_date_range()
    test_multiple_timeframes()
    test_invalid_inputs()

    print("\n" + "="*80)
    print("🎉 ALL TESTS PASSED!")
    print("="*80)
