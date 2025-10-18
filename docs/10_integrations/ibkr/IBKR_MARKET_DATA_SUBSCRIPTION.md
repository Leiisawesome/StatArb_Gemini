# 📊 IBKR Market Data Subscription Guide (Paper Trading)

**Date**: October 13, 2025  
**Account Type**: Pro Account  
**Goal**: Enable real-time market data for paper trading account

---

## 🎯 Overview

With an IBKR **Pro Account**, you can subscribe to market data feeds that work for both **live and paper trading** accounts. This will fix the current limitation where quotes return $0.00.

---

## 📝 Subscription Steps

### Step 1: Access Account Management Portal

1. Go to: **https://www.interactivebrokers.com**
2. Click **"Client Portal"** (top right)
3. Login with your IBKR credentials
4. Or directly visit: **https://gdcdyn.interactivebrokers.com/sso/Login**

### Step 2: Navigate to Market Data Subscriptions

**Via Settings:**
1. Click **Settings** (gear icon in top right)
2. Select **Account Settings**
3. Scroll to **Market Data Subscriptions**
4. Click **Manage Subscriptions** or **Configure**

**Via User Menu:**
1. Click your username (top right)
2. Select **Settings**
3. Click **Market Data Subscriptions** in left menu

### Step 3: Subscribe to Market Data Feeds

For **US stocks** (SPY, AAPL, MSFT, etc.), you need these subscriptions:

#### Recommended Subscriptions:

**Option 1: US Securities Snapshot and Futures Value Bundle (Recommended)**
- **Cost**: ~$10/month for non-professionals
- **Includes**: 
  - US Stocks (NYSE, NASDAQ, AMEX)
  - Real-time quotes
  - Level 1 data (bid/ask/last)
- **Good for**: Most trading needs

**Option 2: US Equity and Options Add-On Streaming Bundle**
- **Cost**: ~$4.50/month for non-professionals
- **Includes**:
  - NASDAQ (Network C) - Level 1
  - NYSE (Network A/B) - Level 1
  - Real-time streaming data
- **Good for**: Budget option with full functionality

**Option 3: Individual Exchange Subscriptions**
- **NASDAQ Basic**: $1.50/month
- **NYSE**: $1.50/month  
- **AMEX**: $1.50/month
- **Good for**: Minimal cost, specific exchanges only

#### For API/Algorithmic Trading (Your Use Case):

✅ **Recommended**: **US Securities Snapshot and Futures Value Bundle**

This includes:
- Real-time quotes via API
- Works with paper trading
- No throttling for algo trading
- Comprehensive coverage

### Step 4: Select Subscription

1. Check the box next to your chosen subscription
2. Review the monthly cost
3. Click **Continue** or **Subscribe**

### Step 5: Confirm and Accept Agreement

1. Review the **Market Data Agreement**
2. Confirm you're a **non-professional** subscriber (if applicable)
3. Check the box to accept terms
4. Click **Submit** or **Confirm**

### Step 6: Wait for Activation

- **Activation Time**: Usually **immediate** to **15 minutes**
- **Confirmation**: You'll receive an email confirmation
- **Portal Status**: Subscription will show as "Active" in portal

### Step 7: Verify in IB Gateway

1. **Restart IB Gateway** (important!)
2. Login again
3. Look for market data connection confirmations
4. Should see: "Market data farm connection is OK:usfarm"

---

## 🔧 Apply Changes to Your Paper Trading

### Important: Paper Trading Uses Same Subscriptions

**Good news**: Market data subscriptions apply to **BOTH** your live and paper trading accounts automatically!

Once subscribed:
- ✅ Live account gets data
- ✅ Paper account gets data (same subscription)
- ✅ API access gets data
- ✅ IB Gateway gets data

**You don't need separate subscriptions for paper vs live!**

---

## 🧪 Test After Subscription

Once activated (wait 15 minutes), restart IB Gateway and run:

\`\`\`bash
# Test IBKR market data with subscription active
pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_market_data -v -s
\`\`\`

**Expected Result After Subscription:**
\`\`\`
✅ Connected to IBKR
✅ Got quote for SPY
   Symbol: SPY
   Bid: $580.45 x 100
   Ask: $580.46 x 200
   Last: $580.45
   Spread: $0.01
✅ Quote data valid
PASSED
\`\`\`

---

## 💰 Cost Breakdown (Pro Account)

| Subscription | Monthly Cost | What You Get |
|--------------|--------------|--------------|
| **US Securities Snapshot Bundle** | $10.00 | Full US stocks, real-time, API access |
| **US Equity Add-On Streaming** | $4.50 | NYSE + NASDAQ streaming |
| **NASDAQ Basic (Depth of Book)** | $1.50 | NASDAQ Level 1 only |
| **NYSE (Network A)** | $1.50 | NYSE Level 1 only |

**Recommendation for Your Use Case**: US Securities Snapshot Bundle ($10/month)

### Pro Account Benefits:
- ✅ Lower commissions
- ✅ Better market data rates
- ✅ No minimum balance requirements
- ✅ Full API access
- ✅ Priority support

---

## 🚨 Important Notes

### 1. Non-Professional vs Professional Status

**Non-Professional** (cheaper rates):
- Trading for yourself
- Not using data for business purposes
- Not distributing data to others
- **Most algo traders qualify**

**Professional** (higher rates):
- Registered with exchange
- Trading for a firm
- Distributing market data
- Securities industry employee

**For your project**: You likely qualify as **non-professional**

### 2. Subscription Activation

- **Immediate**: Most subscriptions activate within 5-15 minutes
- **Restart Required**: Must restart IB Gateway after activation
- **Verification**: Check portal shows "Active" status

### 3. Paper Trading Limitations REMOVED

Once subscribed:
- ❌ No more $0.00 quotes
- ✅ Real-time bid/ask/last prices
- ✅ Full Level 1 data
- ✅ Volume, high, low, close
- ✅ API quota increased

---

## 🔗 Direct Links

### IBKR Account Management
- **Login**: https://gdcdyn.interactivebrokers.com/sso/Login
- **Market Data Subscriptions**: Settings → Account Settings → Market Data Subscriptions

### Documentation
- **Market Data Overview**: https://www.interactivebrokers.com/en/index.php?f=14193
- **API Market Data**: https://interactivebrokers.github.io/tws-api/market_data.html
- **Subscription Fees**: https://www.interactivebrokers.com/en/index.php?f=14193

### Support
- **IBKR Support**: https://www.interactivebrokers.com/en/support/general.php
- **Phone**: 877-442-2757 (US)
- **Chat**: Available in Client Portal

---

## ✅ Verification Checklist

After subscribing, verify everything works:

- [ ] Subscription shows "Active" in Client Portal
- [ ] Received confirmation email from IBKR
- [ ] Restarted IB Gateway
- [ ] Can see real-time quotes in TWS/Gateway
- [ ] API test returns bid/ask > $0
- [ ] No "market data not subscribed" errors

---

## 🐛 Troubleshooting

### Issue: Still Getting $0.00 Quotes

**Solutions:**
1. ✅ Wait 15 minutes for activation
2. ✅ Restart IB Gateway (important!)
3. ✅ Check subscription is "Active" in portal
4. ✅ Verify correct account selected in Gateway
5. ✅ Try requesting market data manually in Gateway

### Issue: "Market data not subscribed" Error

**Solutions:**
1. ✅ Confirm subscription is active
2. ✅ Restart IB Gateway
3. ✅ Check exchange is covered by your subscription
4. ✅ Verify you're using correct data type (reqMktData vs reqMarketDataType)

### Issue: Only Seeing Delayed Data

**Solutions:**
1. ✅ Check subscription includes "real-time" not "delayed"
2. ✅ Remove `client.reqMarketDataType(3)` line (forces delayed)
3. ✅ Use `client.reqMarketDataType(1)` for live data
4. ✅ Restart IB Gateway

---

## 🔄 Code Changes After Subscription

### Update Your Adapter for Real-Time Data

Once you have a subscription, modify the connection code:

\`\`\`python
# In ibkr_adapter.py, connect() method:

# BEFORE (delayed data):
if self.config.paper_trading:
    self.client.reqMarketDataType(3)  # 3 = Delayed data

# AFTER (real-time data):
if self.config.paper_trading:
    self.client.reqMarketDataType(1)  # 1 = Real-time data (with subscription)
\`\`\`

**Market Data Types:**
- `1` = Real-time (requires subscription)
- `2` = Frozen (last available)
- `3` = Delayed (15-20 minutes)
- `4` = Delayed frozen

---

## 📊 Expected Performance After Subscription

### Before Subscription:
\`\`\`
Bid: $0.00 x 0
Ask: $0.00 x 0
Last: $0.00
❌ Test fails
\`\`\`

### After Subscription:
\`\`\`
Bid: $580.45 x 100
Ask: $580.46 x 200
Last: $580.45
Spread: $0.01
✅ Test passes
\`\`\`

---

## 🎉 Benefits of Subscription

1. **Real-Time Quotes**: Get actual bid/ask/last prices
2. **Full API Access**: No limitations on market data calls
3. **Better Testing**: Paper trading behaves like live trading
4. **Production Ready**: Same data pipeline for live trading
5. **Better Fills**: More accurate order simulation in paper
6. **Historical Data**: Access to historical price data

---

## 💡 Cost-Saving Tips

1. **Start Small**: Begin with NASDAQ Basic ($1.50/month) if you only trade NASDAQ stocks
2. **Bundle Savings**: US Securities Snapshot bundle ($10) vs individual exchanges ($4.50+)
3. **Cancel Anytime**: No long-term commitment
4. **Free Alternatives**: Use Alpaca for quotes, IBKR only for orders

---

## 🚀 Next Steps

1. **Subscribe Now**: Go to Client Portal → Market Data Subscriptions
2. **Wait 15 min**: Allow activation time
3. **Restart Gateway**: Close and reopen IB Gateway
4. **Update Code**: Change reqMarketDataType from 3 to 1
5. **Test**: Run market data test again
6. **Celebrate**: Enjoy real-time quotes! 🎉

---

**Questions?** IBKR support is very responsive for market data subscription issues!
