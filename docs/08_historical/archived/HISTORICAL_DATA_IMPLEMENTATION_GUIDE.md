# 📊 Priority 3: Historical Data Implementation Guide

**Goal:** Add historical bar data fetching to AlpacaAdapter for backtesting, analysis, and strategy validation.

**Time Required:** 1-2 hours  
**Difficulty:** Medium  
**Value:** High - Essential for backtesting and strategy development

---

## 🎯 What You'll Get

After implementation, you'll be able to:

```python
# Get 1-minute bars for the last hour
bars = adapter.get_historical_bars(
    symbol="SPY",
    timeframe="1Min",
    limit=60
)

# Get 5-minute bars for the last trading day
bars = adapter.get_historical_bars(
    symbol="AAPL",
    timeframe="5Min",
    start=datetime.now() - timedelta(days=1),
    end=datetime.now()
)

# Get daily bars for the last 3 months
bars = adapter.get_historical_bars(
    symbol="TSLA",
    timeframe="1Day",
    limit=90
)
```

Each bar contains:
- `timestamp` - When the bar started
- `open` - Opening price
- `high` - Highest price
- `low` - Lowest price  
- `close` - Closing price
- `volume` - Total volume
- `vwap` - Volume-weighted average price
- `trade_count` - Number of trades (if available)

---

## 📝 Step 1: Add Imports (2 minutes)

Add these imports to the top of `alpaca_adapter.py`:

```python
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
```

**Location:** Around line 24, after existing imports

**Current imports section:**
```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockLatestQuoteRequest  # ← Add after this line
```

**Add these two lines:**
```python
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
```

---

## 📝 Step 2: Add Method to AlpacaAdapter (20 minutes)

Add this method to the `AlpacaAdapter` class, ideally in the **"ENHANCED FEATURES - Market Data"** section (around line 600).

```python
def get_historical_bars(
    self,
    symbol: str,
    timeframe: str = "1Min",
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get historical OHLCV bar data for a symbol.
    
    This is essential for:
    - Backtesting strategies
    - Calculating technical indicators
    - Analyzing historical patterns
    - Strategy validation
    
    Args:
        symbol: Stock symbol (e.g., "SPY", "AAPL")
        timeframe: Bar timeframe. Supported values:
            - "1Min", "5Min", "15Min", "30Min" - Minute bars
            - "1Hour", "2Hour", "4Hour" - Hour bars
            - "1Day" - Daily bars
        start: Start datetime (default: 7 days ago for intraday, 1 year for daily)
        end: End datetime (default: now)
        limit: Maximum number of bars to return (max 10,000)
    
    Returns:
        List of bar dictionaries, each containing:
        - timestamp: Bar start time (datetime)
        - open: Opening price (float)
        - high: Highest price (float)
        - low: Lowest price (float)
        - close: Closing price (float)
        - volume: Total volume (int)
        - vwap: Volume-weighted average price (float)
        - trade_count: Number of trades (int, if available)
    
    Example:
        # Get last 100 1-minute bars
        bars = adapter.get_historical_bars("SPY", "1Min", limit=100)
        
        # Get specific date range
        start = datetime(2025, 10, 1)
        end = datetime(2025, 10, 13)
        bars = adapter.get_historical_bars("AAPL", "1Day", start=start, end=end)
        
        # Calculate returns
        if len(bars) >= 2:
            returns = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open']
            print(f"Return: {returns * 100:.2f}%")
    
    Note:
        - Alpaca provides free historical data for all US equities
        - Intraday data available for ~1 year back
        - Daily data available for ~5+ years back
        - Rate limit: ~200 requests/minute
    """
    if not self.is_connected():
        logger.error("Not connected to broker")
        return []
    
    try:
        # Map timeframe string to Alpaca TimeFrame object
        timeframe_map = {
            # Minute bars
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "30Min": TimeFrame(30, TimeFrameUnit.Minute),
            
            # Hour bars
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "2Hour": TimeFrame(2, TimeFrameUnit.Hour),
            "4Hour": TimeFrame(4, TimeFrameUnit.Hour),
            
            # Daily bars
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Invalid timeframe: {timeframe}. Supported: {list(timeframe_map.keys())}")
            return []
        
        tf = timeframe_map[timeframe]
        
        # Set default date ranges based on timeframe
        if start is None:
            if "Day" in timeframe:
                # Daily data: default to 1 year back
                start = datetime.now() - timedelta(days=365)
            else:
                # Intraday data: default to 7 days back
                start = datetime.now() - timedelta(days=7)
        
        if end is None:
            end = datetime.now()
        
        # Validate date range
        if start >= end:
            logger.error(f"Invalid date range: start ({start}) >= end ({end})")
            return []
        
        # Build request
        request_params = {
            'symbol_or_symbols': symbol,
            'timeframe': tf,
            'start': start,
            'end': end
        }
        
        if limit is not None:
            request_params['limit'] = min(limit, 10000)  # Alpaca max is 10,000
        
        request = StockBarsRequest(**request_params)
        
        # Fetch bars from Alpaca
        logger.info(f"Fetching {timeframe} bars for {symbol} from {start} to {end}")
        bars_response = self._data_client.get_stock_bars(request)
        
        # Check if symbol exists in response
        if symbol not in bars_response:
            logger.warning(f"No bar data returned for {symbol}")
            return []
        
        # Convert to list of dictionaries
        bars = []
        for bar in bars_response[symbol]:
            bar_dict = {
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume),
                'vwap': float(bar.vwap) if bar.vwap else None,
                'trade_count': int(bar.trade_count) if hasattr(bar, 'trade_count') else None
            }
            bars.append(bar_dict)
        
        logger.info(f"✅ Retrieved {len(bars)} {timeframe} bars for {symbol}")
        
        # Log sample data for debugging
        if bars:
            logger.debug(f"First bar: {bars[0]['timestamp']} OHLC: {bars[0]['open']:.2f}/{bars[0]['high']:.2f}/{bars[0]['low']:.2f}/{bars[0]['close']:.2f}")
            logger.debug(f"Last bar: {bars[-1]['timestamp']} OHLC: {bars[-1]['open']:.2f}/{bars[-1]['high']:.2f}/{bars[-1]['low']:.2f}/{bars[-1]['close']:.2f}")
        
        return bars
        
    except Exception as e:
        logger.error(f"Failed to get historical bars for {symbol}: {e}")
        logger.exception("Full traceback:")
        return []
```

---

## 📝 Step 3: Create Test File (15 minutes)

Create `tests/broker_integration/test_historical_data.py`:

```python
"""
Test historical data retrieval from Alpaca.
Tests OHLCV bar data fetching for backtesting and analysis.
"""

import pytest
from datetime import datetime, timedelta
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config


def test_get_1min_bars():
    """Test retrieving 1-minute bars."""
    print("\n" + "="*80)
    print("TEST: Get 1-Minute Historical Bars for SPY")
    print("="*80)
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
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
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
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
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
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
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
    
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
    
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
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
```

---

## 📝 Step 4: Run Tests (5 minutes)

```bash
# Method 1: Run as pytest
pytest tests/broker_integration/test_historical_data.py -v -s

# Method 2: Run directly (more verbose output)
python tests/broker_integration/test_historical_data.py
```

**Expected output:**
```
Retrieved 100 1-minute bars for SPY
First bar (2025-10-11 14:30:00+00:00):
  Open:   $638.50
  High:   $638.75
  Low:    $638.45
  Close:  $638.60
  Volume: 125,432

Last bar (2025-10-11 16:00:00+00:00):
  Open:   $639.20
  High:   $639.45
  Low:    $639.10
  Close:  $639.30
  Volume: 89,567

Return over period: 0.12%
```

---

## 🚀 Step 5: Practical Usage Examples

### Example 1: Backtest a Simple Strategy

```python
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config
from datetime import datetime, timedelta

# Connect
config = load_broker_config()
adapter = AlpacaAdapter(config.alpaca)
adapter.connect()

# Get 1 week of 5-minute bars
bars = adapter.get_historical_bars(
    symbol="SPY",
    timeframe="5Min",
    start=datetime.now() - timedelta(days=7),
    end=datetime.now()
)

# Simple moving average crossover strategy
def calculate_sma(bars, period):
    """Calculate simple moving average."""
    if len(bars) < period:
        return None
    closes = [b['close'] for b in bars[-period:]]
    return sum(closes) / period

# Backtest
wins = 0
losses = 0
position = None

for i in range(50, len(bars)):
    window = bars[:i]
    
    sma_20 = calculate_sma(window, 20)
    sma_50 = calculate_sma(window, 50)
    current_price = bars[i]['close']
    
    if sma_20 and sma_50:
        # Buy signal: 20 crosses above 50
        if sma_20 > sma_50 and position is None:
            position = current_price
            print(f"BUY at ${current_price:.2f}")
        
        # Sell signal: 20 crosses below 50
        elif sma_20 < sma_50 and position is not None:
            pnl = current_price - position
            if pnl > 0:
                wins += 1
            else:
                losses += 1
            print(f"SELL at ${current_price:.2f} | P&L: ${pnl:.2f}")
            position = None

print(f"\nBacktest Results:")
print(f"Wins: {wins}, Losses: {losses}")
print(f"Win Rate: {wins / (wins + losses) * 100:.1f}%")

adapter.disconnect()
```

### Example 2: Calculate Technical Indicators

```python
# Get daily data for analysis
bars = adapter.get_historical_bars("AAPL", "1Day", limit=100)

# Calculate daily returns
returns = []
for i in range(1, len(bars)):
    ret = (bars[i]['close'] - bars[i-1]['close']) / bars[i-1]['close']
    returns.append(ret)

# Calculate volatility (standard deviation of returns)
mean_return = sum(returns) / len(returns)
variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
volatility = variance ** 0.5

print(f"AAPL 100-day volatility: {volatility * 100:.2f}%")
```

### Example 3: Find Best Performing Stock

```python
symbols = ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL"]
performances = {}

for symbol in symbols:
    bars = adapter.get_historical_bars(symbol, "1Day", limit=30)
    if bars:
        return_pct = (bars[-1]['close'] - bars[0]['open']) / bars[0]['open'] * 100
        performances[symbol] = return_pct
        print(f"{symbol}: {return_pct:+.2f}%")

best_symbol = max(performances, key=performances.get)
print(f"\nBest performer: {best_symbol} ({performances[best_symbol]:+.2f}%)")
```

---

## 🎯 Why This Is Valuable

### 1. **Strategy Backtesting**
- Test strategies on historical data before risking real money
- Validate signal generation logic
- Optimize parameters

### 2. **Market Analysis**
- Identify patterns and trends
- Calculate technical indicators (SMA, EMA, RSI, MACD)
- Analyze correlations between symbols

### 3. **Risk Assessment**
- Calculate historical volatility
- Identify support/resistance levels
- Analyze drawdowns

### 4. **Performance Validation**
- Compare strategy performance to buy-and-hold
- Benchmark against market indices
- Calculate Sharpe ratios and other metrics

---

## ✅ Verification Checklist

After implementation, verify:

- [ ] Imports added to `alpaca_adapter.py`
- [ ] `get_historical_bars()` method added to `AlpacaAdapter` class
- [ ] Test file created: `tests/broker_integration/test_historical_data.py`
- [ ] Tests pass: `pytest tests/broker_integration/test_historical_data.py -v`
- [ ] Can fetch 1-minute bars
- [ ] Can fetch daily bars
- [ ] Can specify date ranges
- [ ] Multiple timeframes work
- [ ] Error handling works (invalid symbols, timeframes)

---

## 🐛 Troubleshooting

### Issue: "No bar data returned"
**Solution:** Market might be closed. Try requesting daily bars which are always available:
```python
bars = adapter.get_historical_bars("SPY", "1Day", limit=10)
```

### Issue: "TimeFrame not found"
**Solution:** Ensure you imported `TimeFrameUnit`:
```python
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
```

### Issue: Rate limit errors
**Solution:** Add delays between requests:
```python
import time
for symbol in symbols:
    bars = adapter.get_historical_bars(symbol, "1Day", limit=30)
    time.sleep(0.3)  # 300ms delay
```

---

## 📊 Expected Performance

- **1-minute bars:** ~200-500ms for 100 bars
- **Daily bars:** ~150-300ms for 100 bars
- **Rate limit:** ~200 requests/minute
- **Data availability:** 
  - Intraday: ~1 year back
  - Daily: ~5+ years back

---

## 🚀 Next Steps After Implementation

1. **Create a backtesting framework** using the historical data
2. **Build technical indicator library** (SMA, RSI, MACD, etc.)
3. **Analyze your strategy signals** against historical data
4. **Create performance reports** with charts and statistics

---

**Ready to implement? Let me know and I'll help you add it step by step!** 🚀
