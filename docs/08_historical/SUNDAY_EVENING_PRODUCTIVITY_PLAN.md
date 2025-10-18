# 🌙 Sunday Evening Productivity Plan

**Current Time:** Sunday, October 13, 2025, 4:46 PM ET  
**Market Opens In:** ~17 hours (Monday 9:30 AM ET)  
**Status:** All broker tests passing, waiting for market validation

---

## 🎯 High-Value Tasks (4-6 hours of work)

### 1. 📊 **Integration Testing with Real Strategies** (2-3 hours)

Connect your actual trading strategies to the broker adapter and test the signal → order flow.

#### Step 1: Review Your Strategy Files
```bash
# Find your strategy implementations
find core_engine/ -name "*strategy*" -type f
```

#### Step 2: Create Strategy-Broker Integration Test
```python
# tests/integration/test_strategy_broker_integration.py

"""
Test that strategies can successfully submit orders through broker adapter.
This tests the FULL pipeline: signal generation → order validation → broker submission.
"""

import pytest
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config
# Import your strategy classes here

def test_strategy_generates_valid_orders():
    """Test that strategy signals produce valid broker orders."""
    # 1. Initialize your strategy
    # 2. Generate a signal
    # 3. Convert signal to order parameters
    # 4. Validate order parameters with broker
    # 5. Assert everything validates correctly
    pass

def test_strategy_order_submission_dry_run():
    """Test order submission without actually executing (dry-run mode)."""
    # Test the full flow but cancel orders before they execute
    pass
```

**Benefits:**
- Catch integration issues before market hours
- Validate your strategy signals produce valid orders
- Test error handling in strategy → broker pipeline

---

### 2. 🔍 **Add Historical Data Analysis** (1-2 hours)

Implement historical bar data fetching for backtesting and analysis.

#### Add to `alpaca_adapter.py`:
```python
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

def get_historical_bars(
    self,
    symbol: str,
    timeframe: str = "1Min",  # 1Min, 5Min, 15Min, 1Hour, 1Day
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get historical bar data for a symbol.
    
    Args:
        symbol: Stock symbol
        timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
        start: Start datetime (defaults to 7 days ago)
        end: End datetime (defaults to now)
        limit: Maximum number of bars to return
    
    Returns:
        List of bar dictionaries with OHLCV data
    """
    try:
        if start is None:
            start = datetime.now() - timedelta(days=7)
        if end is None:
            end = datetime.now()
        
        # Map string timeframe to Alpaca TimeFrame enum
        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, TimeFrame.Unit.Minute),
            "15Min": TimeFrame(15, TimeFrame.Unit.Minute),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day,
        }
        
        tf = timeframe_map.get(timeframe, TimeFrame.Minute)
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit
        )
        
        bars = self._data_client.get_stock_bars(request)
        
        if symbol not in bars:
            return []
        
        result = []
        for bar in bars[symbol]:
            result.append({
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume),
                'vwap': float(bar.vwap) if hasattr(bar, 'vwap') else None,
            })
        
        self.logger.info(f"✅ Retrieved {len(result)} bars for {symbol} ({timeframe})")
        return result
        
    except Exception as e:
        self.logger.error(f"Failed to get historical bars for {symbol}: {e}")
        return []
```

#### Create Test:
```python
# tests/broker_integration/test_historical_data.py

def test_historical_bars():
    """Test historical bar data retrieval."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    # Get 1-minute bars for SPY from last week
    bars = adapter.get_historical_bars(
        symbol="SPY",
        timeframe="1Min",
        limit=100
    )
    
    assert len(bars) > 0
    assert 'timestamp' in bars[0]
    assert 'open' in bars[0]
    assert 'close' in bars[0]
    assert bars[0]['open'] > 0
    
    print(f"\n✅ Retrieved {len(bars)} bars")
    print(f"Latest bar: {bars[-1]}")
    
    adapter.disconnect()
```

**Benefits:**
- Essential for backtesting strategies
- Analyze market conditions before trading
- Calculate technical indicators

---

### 3. 🚨 **Build a Monitoring Dashboard Prototype** (1-2 hours)

Create a simple real-time monitoring system for Monday's trading.

#### Create Monitoring Script:
```python
# core_engine/monitoring/live_monitor.py

"""
Real-time broker monitoring dashboard.
Displays account status, positions, orders, and P&L updates.
"""

import time
from datetime import datetime
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config

class LiveMonitor:
    def __init__(self):
        self.config = load_broker_config()
        self.adapter = AlpacaAdapter(self.config.alpaca)
        self.running = False
    
    def start(self, interval_seconds: int = 5):
        """Start monitoring loop."""
        self.adapter.connect()
        self.running = True
        
        print("=" * 80)
        print("🚀 LIVE BROKER MONITOR STARTED")
        print("=" * 80)
        
        try:
            while self.running:
                self._display_status()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n⚠️  Monitor stopped by user")
        finally:
            self.adapter.disconnect()
    
    def _display_status(self):
        """Display current status."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Clear screen (optional)
        print("\033[H\033[J", end="")  # ANSI escape code to clear screen
        
        print(f"{'=' * 80}")
        print(f"⏰ {now}")
        print(f"{'=' * 80}")
        
        # Market status
        market_open = self.adapter.is_market_open()
        status = "🟢 OPEN" if market_open else "🔴 CLOSED"
        print(f"\n📊 Market Status: {status}")
        
        # Account info
        account = self.adapter.get_account_info()
        print(f"\n💰 Account:")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        
        # Positions
        positions = self.adapter.get_positions()
        print(f"\n📍 Positions ({len(positions)}):")
        if positions:
            for pos in positions:
                pnl = float(pos.unrealized_pl)
                pnl_pct = float(pos.unrealized_plpc) * 100
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                print(f"   {pnl_color} {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f}")
                print(f"      Current: ${float(pos.current_price):.2f} | P&L: ${pnl:,.2f} ({pnl_pct:.2f}%)")
        else:
            print("   (No open positions)")
        
        # Open orders
        orders = self.adapter.get_orders(status="open")
        print(f"\n📋 Open Orders ({len(orders)}):")
        if orders:
            for order in orders:
                print(f"   {order.side.upper()} {order.quantity} {order.symbol} @ {order.order_type.upper()}")
                print(f"      Status: {order.status.upper()} | ID: {order.order_id[:8]}...")
        else:
            print("   (No open orders)")
        
        print(f"\n{'=' * 80}")

if __name__ == "__main__":
    monitor = LiveMonitor()
    monitor.start(interval_seconds=5)  # Update every 5 seconds
```

#### Test It Now:
```bash
python core_engine/monitoring/live_monitor.py
```

**Benefits:**
- Real-time visibility during Monday's trading
- Quick problem detection
- Track P&L as orders execute

---

### 4. 📝 **Add Order Modification Support** (1 hour)

Implement the ability to modify existing orders (useful for limit orders).

#### Add to `alpaca_adapter.py`:
```python
def replace_order(
    self,
    order_id: str,
    quantity: Optional[int] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: Optional[str] = None
) -> SystemOrder:
    """
    Replace an existing order with new parameters.
    
    Only works for orders that haven't been filled yet.
    This is more efficient than cancel + resubmit.
    
    Args:
        order_id: ID of order to replace
        quantity: New quantity (optional)
        limit_price: New limit price (optional)
        stop_price: New stop price (optional)
        time_in_force: New time in force (optional)
    
    Returns:
        New order object after replacement
    """
    try:
        from alpaca.trading.requests import ReplaceOrderRequest
        
        # Build replacement request
        replace_request = ReplaceOrderRequest(
            qty=quantity,
            limit_price=round(limit_price, 2) if limit_price else None,
            stop_price=round(stop_price, 2) if stop_price else None,
            time_in_force=time_in_force
        )
        
        # Replace order
        new_order = self._trading_client.replace_order_by_id(
            order_id=order_id,
            replace_order_data=replace_request
        )
        
        self.logger.info(f"✅ Order replaced: {order_id[:8]}... → {new_order.id[:8]}...")
        return self._convert_alpaca_order(new_order)
        
    except Exception as e:
        self.logger.error(f"Failed to replace order {order_id}: {e}")
        raise
```

**Benefits:**
- Adjust orders without losing queue position
- More efficient than cancel + resubmit
- Critical for limit order strategies

---

### 5. 🧪 **Write Edge Case Tests** (1-2 hours)

Test unusual scenarios that might happen in production.

#### Create `tests/broker_integration/test_edge_cases.py`:
```python
"""
Edge case testing for broker integration.
Tests unusual scenarios that might occur in production.
"""

import pytest
from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.broker_config import load_broker_config

def test_submit_order_when_market_closed():
    """Test that orders can be submitted when market is closed (should queue)."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    # This should work even when market is closed
    order = adapter.submit_limit_order(
        symbol="SPY",
        quantity=1,
        side="buy",
        limit_price=100.00  # Very low price
    )
    
    assert order.order_id is not None
    assert order.status.lower() in ['new', 'accepted', 'pending_new']
    
    # Cleanup
    adapter.cancel_order(order.order_id)
    adapter.disconnect()


def test_very_large_order():
    """Test validation of unrealistically large orders."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    # Try to buy $1 million worth of SPY
    is_valid, error_msg = adapter.validate_order_params(
        symbol="SPY",
        quantity=10000,  # ~$6.4M at current price
        price=640.00,
        side="buy"
    )
    
    # Should fail due to insufficient buying power
    assert not is_valid
    assert "buying power" in error_msg.lower()
    
    adapter.disconnect()


def test_fractional_shares():
    """Test if fractional shares are supported."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    # Alpaca supports fractional shares
    # This test documents the behavior
    try:
        order = adapter.submit_market_order(
            symbol="SPY",
            quantity=0.5,  # Half a share
            side="buy"
        )
        # If we get here, fractional shares are supported
        adapter.cancel_order(order.order_id)
        assert True
    except Exception as e:
        # If error, fractional shares not supported
        assert "fractional" in str(e).lower()
    
    adapter.disconnect()


def test_multiple_orders_same_symbol():
    """Test submitting multiple orders for same symbol simultaneously."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    orders = []
    
    # Submit 3 limit orders at different prices
    for i, price in enumerate([100.00, 200.00, 300.00]):
        order = adapter.submit_limit_order(
            symbol="SPY",
            quantity=1,
            side="buy",
            limit_price=price
        )
        orders.append(order)
    
    # Verify all 3 orders exist
    assert len(orders) == 3
    assert all(o.order_id for o in orders)
    
    # Cleanup
    for order in orders:
        adapter.cancel_order(order.order_id)
    
    adapter.disconnect()


def test_cancel_already_cancelled_order():
    """Test cancelling an order that's already cancelled (idempotency)."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    
    # Submit and cancel an order
    order = adapter.submit_limit_order(
        symbol="SPY",
        quantity=1,
        side="buy",
        limit_price=100.00
    )
    adapter.cancel_order(order.order_id)
    
    # Try to cancel again - should handle gracefully
    try:
        adapter.cancel_order(order.order_id)
        # Should either succeed or raise a specific error
    except Exception as e:
        # Document what error we get
        print(f"Double-cancel error: {e}")
    
    adapter.disconnect()


def test_order_after_disconnect():
    """Test that orders fail gracefully after disconnect."""
    config = load_broker_config()
    adapter = AlpacaAdapter(config.alpaca)
    adapter.connect()
    adapter.disconnect()
    
    # Try to submit order after disconnect
    with pytest.raises(Exception):
        adapter.submit_market_order(
            symbol="SPY",
            quantity=1,
            side="buy"
        )
```

**Benefits:**
- Find bugs before they cause problems in production
- Document expected behavior for edge cases
- Improve error handling

---

### 6. 📈 **Create Performance Tracking** (1 hour)

Track execution performance metrics.

#### Create `core_engine/analytics/execution_tracker.py`:
```python
"""
Track and analyze order execution performance.
"""

from datetime import datetime
from typing import Dict, List
import json

class ExecutionTracker:
    def __init__(self):
        self.executions: List[Dict] = []
    
    def record_execution(
        self,
        symbol: str,
        side: str,
        quantity: int,
        expected_price: float,
        actual_price: float,
        submission_time: datetime,
        fill_time: datetime
    ):
        """Record an order execution."""
        slippage = actual_price - expected_price
        slippage_bps = (slippage / expected_price) * 10000
        latency_ms = (fill_time - submission_time).total_seconds() * 1000
        
        execution = {
            'timestamp': fill_time.isoformat(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'expected_price': expected_price,
            'actual_price': actual_price,
            'slippage': slippage,
            'slippage_bps': slippage_bps,
            'latency_ms': latency_ms,
        }
        
        self.executions.append(execution)
    
    def get_statistics(self) -> Dict:
        """Get execution statistics."""
        if not self.executions:
            return {}
        
        slippages = [e['slippage_bps'] for e in self.executions]
        latencies = [e['latency_ms'] for e in self.executions]
        
        return {
            'total_executions': len(self.executions),
            'avg_slippage_bps': sum(slippages) / len(slippages),
            'max_slippage_bps': max(slippages),
            'avg_latency_ms': sum(latencies) / len(latencies),
            'max_latency_ms': max(latencies),
        }
    
    def save_to_file(self, filepath: str):
        """Save execution history to file."""
        with open(filepath, 'w') as f:
            json.dump(self.executions, f, indent=2)
```

---

## 🎯 Priority Recommendations

**If you have 1-2 hours:** Do task #1 (Strategy Integration Testing)  
**If you have 2-4 hours:** Do tasks #1 + #3 (Strategy Testing + Monitoring)  
**If you have 4-6 hours:** Do tasks #1, #2, #3 (Strategy + Historical Data + Monitoring)  
**If you want maximum test coverage:** Do task #5 (Edge Case Tests)

---

## ✅ Quick Wins (< 30 minutes each)

1. **Review Your Strategy Code**
   ```bash
   # Find all strategy files
   find core_engine/ -name "*.py" | grep -i strategy
   ```

2. **Test Historical Data Retrieval**
   ```python
   # Quick test in Python shell
   from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
   from core_engine.config.broker_config import load_broker_config
   
   config = load_broker_config()
   adapter = AlpacaAdapter(config.alpaca)
   adapter.connect()
   
   # Get latest quote
   quote = adapter.get_latest_quote("SPY")
   print(f"SPY Quote: {quote}")
   ```

3. **Document Your Trading Plan**
   - What symbols will you trade Monday?
   - What's your max position size?
   - What's your stop-loss strategy?
   - What time will you start/stop trading?

4. **Set Up Alerts**
   - Create email/SMS alerts for critical events
   - Test notification system

5. **Prepare Monitoring Terminal**
   ```bash
   # Create a tmux session for Monday
   tmux new -s trading
   
   # Split into panes:
   # 1. Live monitor
   # 2. Test runner
   # 3. Logs
   # 4. Python shell for manual commands
   ```

---

## 📅 Monday Morning Checklist

**Before 9:00 AM ET:**
- [ ] Check market holiday calendar (no surprises!)
- [ ] Verify account has sufficient buying power
- [ ] Test broker connection
- [ ] Start live monitor
- [ ] Review order limits and risk parameters

**At 9:30 AM ET (Market Open):**
- [ ] Run: `pytest tests/broker_integration/orders/test_market_orders.py -v -s`
- [ ] Verify order fills within expected time
- [ ] Check slippage is reasonable
- [ ] Validate P&L calculations

**After Validation:**
- [ ] Start strategy execution (if all tests pass)
- [ ] Monitor for first 15-30 minutes closely
- [ ] Review execution metrics

---

## 🚀 My Recommendation

**Focus on Integration Testing (#1) and Monitoring (#3)** because:

1. **Integration Testing** - Will catch any issues in your strategy → broker pipeline BEFORE market opens
2. **Monitoring Dashboard** - Gives you real-time visibility during Monday's critical first trades
3. Both are **immediately useful** for Monday morning validation

**Then if you have time:**
- Add historical data (#2) - useful for backtesting
- Add edge case tests (#5) - improves reliability

---

**Bottom Line:** You're in great shape! The broker integration is solid. Now's the time to connect it to your actual strategies and prepare for Monday's live validation. 🚀
