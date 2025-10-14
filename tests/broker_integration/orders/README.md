# Order Testing Module

This directory contains tests for order submission, execution, and management functionality.

## Test Files

### `test_market_orders.py` (Day 3)
**Purpose**: Test market order submission and execution  
**What it tests**:
- Market BUY order submission
- Order fill monitoring and confirmation
- Position creation verification
- Market SELL order submission
- Position closure verification
- Account balance reconciliation

**Safety parameters**:
- Symbol: SPY (S&P 500 ETF - highly liquid)
- Quantity: 1 share
- Mode: Paper trading only
- Action: Immediate close after open

**Requirements**:
- Must run during market hours (9:30 AM - 4:00 PM ET)
- Market must be open (Monday-Friday, non-holidays)

**How to run**:
```bash
source ai_integration_env/bin/activate
python tests/broker_integration/orders/test_market_orders.py
```

**Expected output**:
- Order submitted successfully
- Order filled within 30 seconds
- Position created with correct quantity
- Position closed successfully
- Account balance updated correctly

### `test_limit_orders.py` (Day 4 - Coming Soon)
**Purpose**: Test limit order placement and execution  
**What it will test**:
- Limit order submission below market (won't fill)
- Order status tracking
- Order cancellation
- Limit order at market price (should fill)

### `test_order_cancellation.py` (Day 4 - Coming Soon)
**Purpose**: Test order cancellation functionality  
**What it will test**:
- Cancel pending limit orders
- Handle already-filled orders
- Verify cancellation confirmation
- Error handling for invalid cancellations

## Monitoring

During test runs, you can monitor your orders on the Alpaca dashboard:
- Paper Trading: https://app.alpaca.markets/paper/dashboard

## Safety Guidelines

⚠️ **ALWAYS use paper trading for tests**
- Never test with real money
- Keep test quantities small (1 share)
- Close positions immediately after testing
- Monitor tests in real-time

## Troubleshooting

**Order doesn't fill**:
- Check market hours (9:30 AM - 4:00 PM ET)
- Verify market is open (not weekend/holiday)
- Check if symbol is tradable
- Review order status on Alpaca dashboard

**Position not created**:
- Wait a few seconds after order fill
- Check if order was actually filled
- Verify no position limits hit
- Review account buying power

**Order rejected**:
- Check buying power availability
- Verify symbol is supported
- Review risk limits configuration
- Check for pattern day trading restrictions

## Success Criteria

✅ **Day 3 Complete when**:
- Market BUY order submits and fills
- Position created with correct quantity
- Market SELL order submits and fills
- Position closed successfully
- Account balance reconciled

✅ **Day 4 Complete when**:
- Limit orders can be placed
- Orders can be cancelled
- Order status tracked correctly
- Various order scenarios handled

## Next Steps

After completing order tests:
1. Move to position tracking (`../positions/`)
2. Implement P&L calculation tests
3. Test portfolio monitoring
4. Complete Week 1 integration testing
