# Broker Integration Tests

**Purpose**: Test real broker connectivity, live trading operations, and data feeds  
**Status**: ✅ Operational  
**Broker**: Alpaca Markets (Paper Trading)

---

## 📋 Test Suite Overview

### Configuration Testing
**File**: `test_broker_config_loading.py`  
**Purpose**: Validate configuration loading, credential management, and risk limits

**What it tests**:
- Environment variable loading from .env
- Alpaca API credential validation
- Risk limit configuration
- Trading mode verification
- Paper trading enforcement

### Connection Testing
**File**: `test_alpaca_connection.py`  
**Purpose**: Verify broker API connectivity and authentication

**What it tests**:
- Connection to Alpaca paper trading API
- API authentication
- Account information retrieval
- Position tracking
- Connection health monitoring
- Graceful disconnection

### Error Handling Testing
**File**: `test_connection_error_handling.py`  
**Purpose**: Validate error detection and handling mechanisms

**What it tests**:
- Invalid credential rejection
- Empty credential detection
- URL/mode mismatch detection
- Timeout handling
- Rate limiting awareness

---

## 🚀 Quick Start

### Prerequisites
```bash
# 1. Activate virtual environment
source ai_integration_env/bin/activate

# 2. Ensure .env file exists with Alpaca credentials
cp .env.example .env
# Edit .env with your Alpaca paper trading API keys
```

### Running Tests

**Run all tests**:
```bash
# From project root
python tests/broker_integration/test_broker_config_loading.py
python tests/broker_integration/test_alpaca_connection.py
python tests/broker_integration/test_connection_error_handling.py
```

**Run individual test**:
```bash
# Configuration only
python tests/broker_integration/test_broker_config_loading.py

# Connection only
python tests/broker_integration/test_alpaca_connection.py

# Error handling only
python tests/broker_integration/test_connection_error_handling.py
```

---

## ✅ Expected Results

All three tests should pass with green checkmarks ✅:

**Test 1**: Configuration loads from .env  
**Test 2**: Connects to Alpaca, retrieves account ($100K paper money)  
**Test 3**: Error handling works correctly

---

## � Safety Features

### Built-in Protections
- ✅ **Paper Trading Only**: Must use paper trading initially
- ✅ **Position Limits**: Max $1,000 per position
- ✅ **Trade Limits**: Max 10 trades/day
- ✅ **Loss Limits**: Max $100 daily loss
- ✅ **Manual Approval**: Trades require confirmation
- ✅ **Kill Switch**: Emergency stop available

---

## 📊 Test Output Examples

### Configuration Test
```
============================================================
Broker Integration: Configuration Loading Test
============================================================

✓ Alpaca API Key loaded: PKxxxxxx...
✓ Base URL: https://paper-api.alpaca.markets
✓ Paper Trading: True

✅ Configuration validation: PASSED
✅ Risk limits validation: PASSED

Result: SUCCESS ✅
```

### Connection Test
```
============================================================
Broker Integration: Alpaca Connection Test
============================================================

✅ Connection established successfully
✅ Authentication successful
✅ Account information retrieved
   Account ID: PA3AYMYZ1EFR
   Cash: $100,000.00
   Buying Power: $200,000.00
   Status: ACTIVE

Result: SUCCESS ✅
```

---

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'alpaca'"
**Solution**:
```bash
source ai_integration_env/bin/activate
pip install alpaca-py
```

### ".env file not found"
**Solution**:
```bash
cp .env.example .env
nano .env  # Add your credentials
```

### "Authentication failed"
**Checklist**:
1. ✓ Using paper trading keys (start with `PK`)
2. ✓ No extra spaces in .env file
3. ✓ Keys haven't expired
4. ✓ Correct base URL: `https://paper-api.alpaca.markets`

### "Connection timeout"
**Possible causes**:
1. Internet connection issue
2. Alpaca API temporarily down (check https://status.alpaca.markets)
3. Firewall blocking WebSocket connections

---

## 📁 File Structure

```
tests/broker_integration/
├── __init__.py                          # Module initialization
├── README.md                            # This file
├── test_broker_config_loading.py        # Configuration tests
├── test_alpaca_connection.py            # Connection tests
└── test_connection_error_handling.py    # Error handling tests
```

---

## 🔗 Related Files

**Configuration**:
- `core_engine/config/broker_config.py` - Broker configuration management
- `.env` - Your credentials (not in git)
- `.env.example` - Configuration template

**Broker Adapters**:
- `core_engine/broker/adapters/alpaca_adapter.py` - Alpaca integration

**Documentation**:
- `docs/BROKER_INTEGRATION_QUICK_START.md` - Quick setup guide
- `docs/NAMING_CONVENTION_MIGRATION_COMPLETE.md` - Migration details

---

## 🎯 Next Steps After Tests Pass

1. **Understand order management** (Days 3-5)
   - Market order submission
   - Limit order submission
   - Order tracking and cancellation
   - Position management

2. **Explore live data feeds** (Week 2)
   - Real-time market data
   - WebSocket streaming
   - Price feed integration

3. **Monitor your account**
   - Visit: https://app.alpaca.markets/paper/dashboard/overview
   - Watch paper trading activity
   - Track test trades

---

## 📚 Additional Resources

### Alpaca Documentation
- Paper Trading: https://alpaca.markets/docs/trading/paper-trading/
- API Reference: https://docs.alpaca.markets/reference/
- Python SDK: https://github.com/alpacahq/alpaca-py

### Our Documentation
- Quick Start: `docs/BROKER_INTEGRATION_QUICK_START.md`
- Architecture: `docs/TradeDesk Architecture.md`
- Component Mapping: `docs/10_COMPONENT_MAPPING.md`

---

**Test Suite Status**: ✅ **ALL PASSING (3/3)**  
**Last Updated**: October 13, 2025  
**Ready for**: Order Management Testing

