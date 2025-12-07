# IBKR Paper Trading Account Funding

## Problem
Your Interactive Brokers paper trading account shows $0.00 balance, which prevents placing orders.

## Solution
Paper trading accounts need to be funded with virtual money through IBKR's interface.

## Quick Check
```bash
./utils/check_balance.sh
# or from utils directory:
# ./check_balance.sh
```

## Funding Instructions

### Method 1: Trader Workstation (TWS) - Recommended
1. **Launch TWS**: Open Interactive Brokers Trader Workstation
2. **Login**: Use your paper trading credentials
3. **Configure Display**:
   - Go to: `File → Global Configuration → Display → Ticker Row`
   - Check: "Show Cash Qty"
4. **Fund Account**:
   - Right-click your account number in main window
   - Select: `Transfer & Pay → Transfer Funds`
   - Choose "Deposit"
   - Enter amount (e.g., $100,000)
   - Select "USD" currency
   - Click "Transfer"

### Method 2: IBKR Account Management Website
1. Go to: https://www.ibkr.com
2. Login to Account Management
3. Navigate: `Account → Transfer & Pay`
4. Select your paper trading account
5. Choose "Deposit Funds"
6. Enter amount and confirm

### Method 3: IBKR Mobile App
1. Open IBKR Mobile app
2. Login with paper trading credentials
3. Go to: `Account → Transfer & Pay`
4. Select "Deposit"
5. Enter amount and confirm

## Recommended Funding Amounts
- **Small testing**: $10,000 - $25,000
- **Strategy testing**: $50,000 - $100,000
- **Full portfolio**: $250,000 - $500,000
- **Conservative limit**: $1,000,000

## Verification
After funding, run:
```bash
./utils/check_balance.sh
```

You should see:
```
✅ STATUS: Account is funded and ready for trading
   💰 Available cash: $100,000.00
```

## Important Notes
- ✅ **Virtual money only** - No real funds involved
- ✅ **Persistent** - Funds remain until account reset
- ✅ **Flexible** - Add/remove funds anytime
- ✅ **Realistic** - All commissions and fees simulated
- ⚠️ **Market data** - May be delayed without subscription

## Troubleshooting
If funding doesn't work:
1. Ensure you're logged into the **paper trading** account (not live)
2. Try different funding method
3. Check IBKR account status
4. Contact IBKR support if issues persist

## Next Steps
Once funded, you can run trading tests:
```bash
pytest tests/broker_integration/orders/test_market_orders.py -v
pytest tests/broker_integration/orders/test_limit_orders.py -v
```