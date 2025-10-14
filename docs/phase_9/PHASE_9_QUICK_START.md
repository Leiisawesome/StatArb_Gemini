# Phase 9 Quick Start Guide

**Status**: Ready to begin testing! ✅  
**Date**: October 13, 2025

---

## 🎯 Overview

Phase 9 integrates real broker connectivity and live data feeds. Week 1 focuses on establishing secure connections and basic trading operations.

**Infrastructure Status**: 
- ✅ All code already implemented (3,000+ lines)
- ✅ All packages installed (alpaca-py, python-dotenv, websockets)
- ⏳ Need to configure credentials and test

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Get Alpaca Credentials

1. Visit https://alpaca.markets and create account
2. Go to paper trading: https://app.alpaca.markets/paper/dashboard/overview
3. Navigate to **API Keys** section
4. Click **Generate New Key**
5. Copy both keys (they start with `PK` for paper trading)

### Step 2: Configure Environment

```bash
# Navigate to project root
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini

# Copy template
cp .env.example .env

# Edit .env file (use nano, vim, or VS Code)
nano .env
```

**Required fields in .env**:
```bash
ALPACA_API_KEY=REDACTED
ALPACA_SECRET_KEY=REDACTED
ALPACA_BASE_URL=https://paper-api.alpaca.markets
TRADING_MODE=paper
```

### Step 3: Run Tests

```bash
# Activate virtual environment
source ai_integration_env/bin/activate

# Test 1: Configuration loading
python tests/phase9/test_day1_config.py

# Test 2: Connection & authentication
python tests/phase9/test_day2_connection.py

# Test 3: Error handling
python tests/phase9/test_day2_error_handling.py
```

---

## 📋 Pre-Flight Checklist

### Prerequisites ✅
- [x] Python 3.11 environment active
- [x] Required packages installed:
  - alpaca-py 0.42.2 ✅
  - alpaca-trade-api 3.2.0 ✅
  - python-dotenv 1.1.1 ✅
  - websocket-client 1.9.0 ✅
  - websockets 15.0.1 ✅

### Configuration Setup
- [ ] Alpaca account created
- [ ] Paper trading API keys generated
- [ ] .env file created from .env.example
- [ ] ALPACA_API_KEY configured
- [ ] ALPACA_SECRET_KEY configured

### Testing
- [ ] Day 1 config test passes
- [ ] Day 2 connection test passes
- [ ] Day 2 error handling test passes

---

## 📁 Key Files

### Configuration
- `core_engine/config/phase9_config.py` - Configuration management
- `.env` - Your credentials (create from .env.example)
- `.env.example` - Template with all options

### Broker Adapters
- `core_engine/broker/adapters/alpaca_adapter.py` - Alpaca integration

### Tests
- `tests/phase9/test_day1_config.py` - Configuration test
- `tests/phase9/test_day2_connection.py` - Connection test
- `tests/phase9/test_day2_error_handling.py` - Error handling test

### Documentation
- `docs/PHASE_9_WEEK_1_DAY_1-2.md` - Detailed Day 1-2 guide

---

## 🔒 Safety Features

Phase 9 has multiple safety layers:

✅ **Paper Trading Lock**: Must use paper trading initially  
✅ **Position Limits**: Max $1,000 per position  
✅ **Daily Trade Limit**: Max 10 trades/day  
✅ **Loss Limit**: Max $100 daily loss  
✅ **Manual Approval**: Trades require confirmation  
✅ **Kill Switch**: Emergency stop available

---

## 📊 Expected Test Output

### Test 1: Configuration
```
============================================================
Phase 9 Day 1: Configuration Loading Test
============================================================

✓ Alpaca API Key loaded: PKxxxxxx...
✓ Base URL: https://paper-api.alpaca.markets
✓ Paper Trading: True

✅ Configuration validation: PASSED

📊 Risk Limits:
   Max Position Size: 100 shares
   Max Daily Trades: 10
   Max Daily Loss: $100.0
   Paper Trading Only: True

✅ Risk limits validation: PASSED
============================================================
✅ Day 1 Configuration Test: SUCCESS
============================================================
```

### Test 2: Connection
```
============================================================
Phase 9 Day 2: Alpaca Connection Test
============================================================

🔗 Connecting to: https://paper-api.alpaca.markets
📄 Paper Trading: True

⏳ Testing connection...
✅ Connection successful!

🔐 Testing authentication...
✅ Authentication successful!

💼 Fetching account information...
✅ Account ID: PA...
   Cash: $100,000.00
   Equity: $100,000.00
   Buying Power: $400,000.00
   Status: ACTIVE

🔌 Disconnecting...
✅ Disconnected successfully
============================================================
✅ Day 2 Connection Test: SUCCESS
============================================================
```

---

## 🆘 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'alpaca'"

**Solution**:
```bash
source ai_integration_env/bin/activate
pip install alpaca-py
```

### Problem: ".env file not found"

**Solution**:
```bash
cp .env.example .env
nano .env  # Add your credentials
```

### Problem: "Authentication failed"

**Checklist**:
1. ✓ Using paper trading keys (start with `PK`)
2. ✓ No extra spaces in .env file
3. ✓ Keys haven't expired
4. ✓ Correct base URL: `https://paper-api.alpaca.markets`

Try regenerating keys if all else fails.

### Problem: "Connection timeout"

**Possible causes**:
1. Internet connection issue
2. Alpaca API temporarily down (check https://status.alpaca.markets)
3. Firewall blocking WebSocket connections

**Solution**: Wait a few minutes and retry.

---

## 📈 Progress Tracking

### Week 1 Schedule

**Days 1-2: Setup & Authentication** ⏳
- [ ] Configure credentials
- [ ] Test configuration loading
- [ ] Test connection
- [ ] Test error handling

**Days 3-4: Order Management** (Next)
- Market orders
- Limit orders
- Order tracking
- Order cancellation

**Day 5: Position Management** (Next)
- Position retrieval
- P&L tracking
- Account monitoring

---

## 🎓 Learning Resources

### Alpaca Documentation
- Paper Trading: https://alpaca.markets/docs/trading/paper-trading/
- API Reference: https://docs.alpaca.markets/reference/
- Python SDK: https://github.com/alpacahq/alpaca-py

### Our Documentation
- Architecture: `docs/TradeDesk Architecture.md`
- Component mapping: `docs/10_COMPONENT_MAPPING.md`
- Phase 9 plan: Search for "Phase 9" in docs/

---

## 🎯 Success Criteria

You're ready for Day 3 when:

✅ All three tests pass  
✅ Connection to Alpaca established  
✅ Account information retrieved  
✅ No authentication errors  
✅ Error handling validated

---

## 📞 Support

If you encounter issues:

1. Check error messages carefully
2. Review troubleshooting section above
3. Verify credentials on Alpaca dashboard
4. Check Alpaca API status
5. Review test output for specific errors

---

## 🚀 Next Steps

Once Days 1-2 tests pass:

1. **Review Day 3-5 documentation**
   - Read `docs/PHASE_9_WEEK_1_DAY_3-5.md` (will be created)

2. **Prepare for order testing**
   - Understand order types
   - Learn position management
   - Review risk limits

3. **Monitor your account**
   - Watch paper trading activity
   - Track test trades
   - Review P&L

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Status**: Ready for Day 1-2 testing!
