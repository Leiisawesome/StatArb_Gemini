# 🚀 IBKR Market Data Subscription - Quick Start

## ⚡ 5-Minute Setup

### Step 1: Subscribe (5 minutes)
1. Go to: https://gdcdyn.interactivebrokers.com/sso/Login
2. Settings → Account Settings → **Market Data Subscriptions**
3. Subscribe to: **US Securities Snapshot Bundle** ($10/month)
4. Accept terms and confirm

### Step 2: Wait & Restart (15 minutes)
1. Wait 15 minutes for activation
2. Close IB Gateway completely
3. Reopen IB Gateway and login
4. Verify connection shows "Market data farm is OK"

### Step 3: Update .env File (1 minute)
Open `.env` and change this line:
```bash
# BEFORE:
IB_HAS_MARKET_DATA_SUBSCRIPTION=false

# AFTER:
IB_HAS_MARKET_DATA_SUBSCRIPTION=true
```

### Step 4: Test (1 minute)
```bash
pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_market_data -v -s
```

**Expected Result:**
```
✅ Symbol: SPY
✅ Bid: $580.45 x 100
✅ Ask: $580.46 x 200
✅ Test PASSED
```

---

## 💰 Cost Comparison

| Option | Cost/Month | What You Get |
|--------|-----------|--------------|
| **No Subscription** (Current) | $0 | ❌ No quotes ($0.00) |
| **NASDAQ Basic** | $1.50 | ✅ NASDAQ stocks only |
| **US Equity Bundle** | $4.50 | ✅ NYSE + NASDAQ streaming |
| **US Securities Snapshot** (Recommended) | $10 | ✅ All US stocks, full API |

---

## 🎯 Recommended for You

**US Securities Snapshot and Futures Value Bundle** - $10/month

✅ All US exchanges (NYSE, NASDAQ, AMEX)  
✅ Real-time quotes via API  
✅ Works with paper trading  
✅ No API throttling  
✅ Perfect for algo trading  

---

## 🔗 Quick Links

- **Subscribe**: https://gdcdyn.interactivebrokers.com/sso/Login → Settings → Market Data
- **Guide**: `docs/IBKR_MARKET_DATA_SUBSCRIPTION.md` (complete instructions)
- **Support**: 877-442-2757 (US) or chat in Client Portal

---

## ✅ After Subscription Checklist

- [ ] Subscription shows "Active" in Client Portal
- [ ] Waited 15 minutes
- [ ] Restarted IB Gateway
- [ ] Updated `.env`: `IB_HAS_MARKET_DATA_SUBSCRIPTION=true`
- [ ] Tested and quotes show real prices (not $0.00)

---

## 🐛 Still Getting $0.00 Quotes?

1. ✅ Check subscription is "Active" (not "Pending")
2. ✅ Restart IB Gateway (close completely, not just disconnect)
3. ✅ Verify `.env` has `IB_HAS_MARKET_DATA_SUBSCRIPTION=true`
4. ✅ Wait full 15 minutes from subscription time
5. ✅ Try manually requesting quote in IB Gateway to verify

---

**That's it!** Subscribe → Wait 15 min → Update .env → Test 🎉
