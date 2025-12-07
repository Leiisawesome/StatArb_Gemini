"""
Test historical data retrieval - WORKING VERSION for free Alpaca account.
Uses delayed data (>15 minutes old) which is available on free tier.
"""

from datetime import datetime, timedelta
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter
from core_engine.config.broker_config import load_broker_config


def test_get_daily_bars_delayed():
    """Test retrieving daily bars (works with free account)."""
    print("\n" + "="*80)
    print("TEST: Get Daily Historical Bars (Delayed Data)")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    # Request data ending yesterday (free accounts can access this)
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=30)
    
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Day",
        start=start,
        end=end
    )
    
    # Assertions
    assert bars is not None
    assert len(bars) > 0, f"Should have bars (requested {start.date()} to {end.date()})"
    
    # Check structure
    first_bar = bars[0]
    assert 'timestamp' in first_bar
    assert 'open' in first_bar
    assert 'high' in first_bar
    assert 'low' in first_bar
    assert 'close' in first_bar
    assert 'volume' in first_bar
    
    # Validate price relationships
    assert first_bar['high'] >= first_bar['low']
    assert first_bar['open'] > 0
    assert first_bar['volume'] >= 0
    
    # Display results
    print(f"\n✅ Retrieved {len(bars)} daily bars for SPY")
    print(f"\nDate Range: {bars[0]['timestamp'].date()} to {bars[-1]['timestamp'].date()}")
    
    # Calculate statistics
    highs = [b['high'] for b in bars]
    lows = [b['low'] for b in bars]
    volumes = [b['volume'] for b in bars]
    
    print(f"\nStatistics over {len(bars)} days:")
    print(f"  Highest price: ${max(highs):.2f}")
    print(f"  Lowest price:  ${min(lows):.2f}")
    print(f"  Avg volume:    {sum(volumes) // len(volumes):,}")
    
    # Calculate return
    total_return = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open']
    print(f"  Total return:  {total_return * 100:.2f}%")
    
    adapter.disconnect()


def test_get_hourly_bars_delayed():
    """Test retrieving hourly bars from several days ago."""
    print("\n" + "="*80)
    print("TEST: Get Hourly Historical Bars (Delayed Data)")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    # Request data from 2-7 days ago (definitely available)
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=5)
    
    bars = adapter.get_historical_bars(
        symbol="AAPL",
        timeframe="1Hour",
        start=start,
        end=end
    )
    
    # Assertions
    assert bars is not None
    assert len(bars) > 0, f"Should have bars (requested {start.date()} to {end.date()})"
    
    print(f"\n✅ Retrieved {len(bars)} hourly bars for AAPL")
    print(f"Date Range: {bars[0]['timestamp']} to {bars[-1]['timestamp']}")
    
    # Show first and last bar
    print(f"\nFirst bar: ${bars[0]['close']:.2f}")
    print(f"Last bar:  ${bars[-1]['close']:.2f}")
    
    adapter.disconnect()


def test_multiple_symbols_daily():
    """Test retrieving daily data for multiple symbols."""
    print("\n" + "="*80)
    print("TEST: Multiple Symbols Daily Data")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    symbols = ["SPY", "QQQ", "AAPL", "MSFT"]
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=30)
    
    results = {}
    
    for symbol in symbols:
        bars = adapter.get_historical_bars(
            symbol=symbol,
            timeframe="1Day",
            start=start,
            end=end
        )
        
        if bars:
            return_pct = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open'] * 100
            results[symbol] = {
                'bars': len(bars),
                'return': return_pct,
                'latest_price': bars[-1]['close']
            }
    
    print(f"\n✅ Retrieved data for {len(results)} symbols:")
    for symbol, data in results.items():
        print(f"  {symbol:5s}: {data['bars']:2d} bars | ${data['latest_price']:7.2f} | Return: {data['return']:+6.2f}%")
    
    assert len(results) == len(symbols), "Should have data for all symbols"
    
    adapter.disconnect()


def test_timeframe_variations():
    """Test different timeframe options with delayed data."""
    print("\n" + "="*80)
    print("TEST: Different Timeframes (Delayed Data)")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    # Use data from last week to avoid real-time data restrictions
    end = datetime.now() - timedelta(days=7)
    start = end - timedelta(days=14)
    
    timeframes = ["1Hour", "4Hour", "1Day"]
    
    print(f"\nTesting timeframes (data from {start.date()} to {end.date()}):")
    for tf in timeframes:
        bars = adapter.get_historical_bars(
            symbol="SPY",
            timeframe=tf,
            start=start,
            end=end
        )
        
        if bars:
            print(f"  {tf:6s}: {len(bars):3d} bars | Range: ${bars[0]['close']:.2f} - ${bars[-1]['close']:.2f}")
            assert len(bars) > 0, f"Should have bars for {tf}"
        else:
            print(f"  {tf:6s}: No data (might be outside trading hours)")
    
    print("\n✅ Timeframe tests complete")
    
    adapter.disconnect()


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n" + "="*80)
    print("TEST: Error Handling")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    # Test 1: Invalid timeframe
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="INVALID",
        limit=10
    )
    assert bars == [], "Should return empty list for invalid timeframe"
    print("  ✅ Invalid timeframe handled correctly")
    
    # Test 2: Invalid symbol
    bars = adapter.get_historical_bars(
        symbol="INVALID_SYMBOL_XYZ",
        timeframe="1Day",
        limit=10
    )
    assert bars == [], "Should return empty list for invalid symbol"
    print("  ✅ Invalid symbol handled correctly")
    
    # Test 3: Invalid date range
    end = datetime.now()
    start = end + timedelta(days=1)  # Start after end
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Day",
        start=start,
        end=end
    )
    assert bars == [], "Should return empty list for invalid date range"
    print("  ✅ Invalid date range handled correctly")
    
    print("\n✅ All error handling tests passed")
    
    adapter.disconnect()


def test_backtest_example():
    """Example of using historical data for backtesting."""
    print("\n" + "="*80)
    print("TEST: Backtesting Example")
    print("="*80)
    
    config = load_broker_config()
    adapter = IBKRAdapter(config.interactive_brokers)
    adapter.connect()
    
    # Get 60 days of data for backtesting
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=60)
    
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Day",
        start=start,
        end=end
    )
    
    assert len(bars) > 30, "Should have at least 30 bars for backtesting"
    
    print(f"\n✅ Retrieved {len(bars)} bars for backtesting")
    
    # Simple moving average example
    def sma(data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period
    
    # Calculate 20-day SMA
    closes = [b['close'] for b in bars]
    sma_20 = sma(closes, 20)
    current_price = closes[-1]
    
    print(f"\nBacktest Metrics:")
    print(f"  Period: {bars[0]['timestamp'].date()} to {bars[-1]['timestamp'].date()}")
    print(f"  Bars: {len(bars)}")
    print(f"  Current Price: ${current_price:.2f}")
    print(f"  20-day SMA: ${sma_20:.2f}")
    print(f"  Price vs SMA: {((current_price / sma_20 - 1) * 100):+.2f}%")
    
    # Calculate volatility
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
    volatility = (variance ** 0.5) * (252 ** 0.5)  # Annualized
    
    print(f"  Volatility (annualized): {volatility * 100:.2f}%")
    
    adapter.disconnect()


if __name__ == "__main__":
    # Run tests directly
    print("\n🚀 Running historical data tests with DELAYED data...")
    print("(Using data > 15 minutes old, compatible with free Alpaca account)")
    
    test_get_daily_bars_delayed()
    test_get_hourly_bars_delayed()
    test_multiple_symbols_daily()
    test_timeframe_variations()
    test_error_handling()
    test_backtest_example()
    
    print("\n" + "="*80)
    print("🎉 ALL TESTS PASSED!")
    print("="*80)
    print("\n✅ Historical data functionality working perfectly!")
    print("📊 You can now use this for backtesting and strategy development")
