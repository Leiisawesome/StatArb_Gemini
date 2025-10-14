# IBKR Professional Account - Enable Real-Time API Data

## Current Issue
Error 10089: "Requested market data requires additional subscription for API"

Even though you have:
- ✅ IBKR Professional account
- ✅ US Securities Snapshot Bundle subscription
- ✅ Market Data API Acknowledgement signed

## The Problem
The subscription needs to be **explicitly enabled for Paper Trading API access**.

---

## Solution: Enable API Access in Client Portal

### Step 1: Log into Client Portal
1. Go to: https://www.interactivebrokers.com/portal
2. Log in with your credentials

### Step 2: Navigate to Market Data Settings
1. Click **User Menu** (top right)
2. Select **Settings**
3. Click **Account Settings**
4. Find **Market Data Subscriptions**

### Step 3: Verify Your Subscription
Look for: **"US Securities Snapshot and Futures Value Bundle"** or **"Professional US Securities Snapshot Bundle"**

Should show:
- Status: **Active**
- Type: **Professional**
- Cost: $10/month

### Step 4: Enable for Paper Trading + API

This is the **critical step** that's missing:

1. Find your subscription in the list
2. Click **"Manage"** or **"Configure"**
3. Look for **"Account Eligibility"** section
4. Make sure these are checked:
   - ☑️ **Enable for Live Account**
   - ☑️ **Enable for Paper Trading** ← CRITICAL!
   - ☑️ **Enable for API/TWS** ← CRITICAL!
   - ☑️ **Enable for API Gateway** ← CRITICAL!

5. Click **"Apply"** or **"Save Changes"**

### Step 5: Verify API Acknowledgement
1. In Market Data Settings, look for **"Non-Professional Agreements"**
2. Find **"API Market Data Acknowledgement"**
3. Should show: **"Signed"** or **"Accepted"**
4. If not signed, click and sign it

### Step 6: Check Specific Exchanges
Some professional data requires exchange permissions:

1. In Market Data Subscriptions
2. Look for **"US Securities - Exchanges"**
3. Verify you have:
   - ☑️ **NASDAQ** (Network C)
   - ☑️ **NYSE** (Network A)
   - ☑️ **AMEX/ARCA** (Network B)

### Step 7: Restart IB Gateway
**Critical:** Restart IB Gateway to refresh permissions

1. Close IB Gateway completely
2. Wait 30 seconds
3. Reopen IB Gateway
4. Log back into Paper Trading

---

## Alternative: Contact IBKR Support

If still not working after above steps, contact IBKR directly:

### Via Phone (Fastest)
- **US/Canada**: +1-877-442-2757
- Say: "I need to enable API market data for paper trading"

### Via Message Center
1. Go to: https://www.interactivebrokers.com/portal
2. Click **Message Center**
3. Click **Compose**
4. Subject: **"Enable API Market Data for Paper Trading"**
5. Message template:

```
Hello,

I have a Professional account with the US Securities Snapshot Bundle 
subscription active. I've signed the Market Data API Acknowledgement.

However, I'm receiving Error 10089 when trying to access market data 
via the API in Paper Trading mode.

Could you please enable API market data access for my paper trading 
account?

Account: [Your Account Number]
Client ID: 2
Gateway Port: 4002 (Paper Trading)

Thank you!
```

---

## Verification Steps

After enabling, test with:

```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
python test_market_data_diagnostic.py
```

**Expected output when working:**
```
[1s] ✅ Got data: {'bid_price': 580.45, 'ask_price': 580.46, ...}
[2s] ✅ Got data: {'bid_price': 580.45, 'ask_price': 580.46, ...}
```

**Still getting Error 10089?**
- Subscription may take up to 24 hours to provision
- IBKR support can expedite it

---

## Common Issues

### "I enabled it but still Error 10089"
**Solution:** 
- Wait 15-30 minutes after enabling
- Restart IB Gateway completely
- If still not working after 1 hour, contact IBKR

### "Paper Trading checkbox not available"
**Solution:**
- Some subscriptions don't show Paper Trading separately
- It should automatically apply to Paper when enabled for Live
- Contact IBKR to verify

### "Professional vs Non-Professional"
**Your account is Professional**, which means:
- ✅ Different pricing structure
- ✅ Lower fees for some data
- ✅ Real-time data included
- ⚠️ Requires proper API enablement

---

## Fallback: Use Delayed Data Temporarily

While waiting for real-time to activate, you can use delayed data:

**In `.env` file:**
```bash
IB_HAS_MARKET_DATA_SUBSCRIPTION=false
```

**Test with:**
```bash
pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_market_data -v
```

Delayed data is 15-20 minutes behind but works immediately without subscription.

---

## Timeline Expectations

| Action | Time to Take Effect |
|--------|-------------------|
| Enable API checkbox | Immediate (after Gateway restart) |
| Sign API acknowledgement | Immediate |
| New subscription activation | Up to 24 hours |
| Permission refresh | 15-30 minutes |

---

## Next Steps

1. ✅ Follow Steps 1-7 above
2. ⏰ If not working after 1 hour → Contact IBKR support
3. 📊 Test during market hours (9:30 AM - 4:00 PM ET)
4. 🚀 Once working, run full test suite

---

## Support Resources

- **IBKR Support**: https://www.interactivebrokers.com/en/support/contact.php
- **Phone**: +1-877-442-2757
- **Message Center**: https://www.interactivebrokers.com/portal (Message Center tab)
- **Knowledge Base**: https://ibkr.info/

Search for: "API market data paper trading"
