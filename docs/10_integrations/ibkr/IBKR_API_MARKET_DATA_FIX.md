# IBKR API Market Data Activation Fix

## Issue
Error 10089: "Requested market data requires additional subscription for API"

## Root Cause
The market data subscription exists but isn't enabled for **API access** in Paper Trading.

---

## Solution Steps

### 1. Verify Subscription is Active (Client Portal)

1. Log into: https://www.interactivebrokers.com/portal
2. Go to **User Menu → Settings → Account Settings**
3. Click **Market Data Subscriptions**
4. Look for: **"US Securities Snapshot and Futures Value Bundle"**
5. Verify it shows **"Active"**

### 2. Enable API Access for Paper Trading

**CRITICAL:** Paper trading has separate permissions!

1. In **Market Data Subscriptions** page
2. Find your subscription: **"US Securities Snapshot and Futures Value Bundle"**
3. Click **"Manage Subscription"** or **"Edit"**
4. Look for section: **"Access Methods"** or **"API Access"**
5. **Check the box** for: ☑️ **"Enable for API"**
6. **Check the box** for: ☑️ **"Enable for Paper Trading"** (if separate option)
7. Click **"Save"** or **"Apply"**

### 3. Restart IB Gateway

**Important:** Restart to refresh permissions

1. Close IB Gateway completely
2. Wait 10 seconds
3. Reopen IB Gateway
4. Log back in to Paper Trading

### 4. Verify in IB Gateway Settings

Once IB Gateway is running:

1. In IB Gateway, go to **Configure → Settings**
2. Look for **Market Data** section
3. Verify you see your subscription listed
4. Verify **"API"** is enabled

### 5. Test Again

```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
python test_market_data_diagnostic.py
```

Expected output after fix:
```
[1s] ✅ Got data: {'bid_price': 580.45, 'ask_price': 580.46, ...}
[2s] ✅ Got data: {'bid_price': 580.45, 'ask_price': 580.46, ...}
```

---

## Common Issues

### Issue: "Subscription shows active but still Error 10089"

**Solution:** 
- Make sure you enabled for **Paper Trading** specifically
- Live and Paper have separate permissions
- Restart IB Gateway after enabling

### Issue: "Don't see API checkbox"

**Solution:**
- Look for "Access Methods" dropdown
- Or "Connection Type" 
- Sometimes labeled as "Workstation" vs "API"

### Issue: "Enabled but still not working after 30 minutes"

**Solution:**
- Contact IBKR support: https://www.interactivebrokers.com/en/support/contact.php
- Ask them to "enable API market data access for paper trading account"
- Reference your subscription: US Securities Snapshot Bundle

---

## Alternative: Use Delayed Data (Free)

If you want to test without subscription:

1. Edit `.env`:
   ```bash
   IB_HAS_MARKET_DATA_SUBSCRIPTION=false
   ```

2. Code will auto-switch to delayed data:
   ```python
   self.client.reqMarketDataType(3)  # Delayed/Free
   ```

3. Delayed data is 15-20 minutes behind but works immediately

---

## Verification Commands

### Check if subscription is working:
```bash
python test_market_data_diagnostic.py
```

### Run full test suite:
```bash
pytest tests/broker_integration/test_ibkr_connection.py -v
```

### Expected when working:
- No Error 10089
- No Error 10197 (competing session - now fixed!)
- Tick data callbacks within 1-2 seconds

---

## Next Steps

Once market data is working:

1. ✅ Run full IBKR test suite (3/3 tests should pass)
2. ✅ Test order placement during market hours
3. ✅ Document final setup
4. ✅ Begin Phase 9 broker integration

---

## Support

If still not working after 24 hours:
- Your subscription might not be provisioned yet
- Contact IBKR: https://www.interactivebrokers.com/en/support/contact.php
- Mention: "API market data not working for paper trading despite active subscription"
