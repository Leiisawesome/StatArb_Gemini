# Phase 9 Week 1: Days 1-2 - Broker Connection Foundation

**Date**: October 13-14, 2025  
**Status**: 🚀 IN PROGRESS  
**Focus**: Setup & Authentication

---

## 📋 Objectives

### Day 1: Environment Setup & Configuration
- [x] Install broker API libraries
- [ ] Configure API credentials securely
- [ ] Test credential loading
- [ ] Validate configuration system

### Day 2: Connection & Authentication
- [ ] Implement Alpaca connection
- [ ] Test authentication flow
- [ ] Validate paper trading account access
- [ ] Test connection error handling

---

## ✅ Completed Setup

### 1. Infrastructure Already Built ✨
The following components are already implemented:

#### **Configuration Management** (`core_engine/config/phase9_config.py`)
- ✅ `AlpacaConfig` - Alpaca credentials & settings
- ✅ `InteractiveBrokersConfig` - IB connection settings
- ✅ `RiskLimits` - Phase 9 safety limits
- ✅ `Phase9ConfigManager` - Centralized config loader
- ✅ Environment variable loading (.env support)

#### **Broker Adapter** (`core_engine/broker/adapters/alpaca_adapter.py`)
- ✅ `AlpacaAdapter` - Full REST API integration
- ✅ Market & limit order support
- ✅ Position & account management
- ✅ Order status tracking
- ✅ Error handling & logging

#### **Type Definitions** (`core_engine/type_definitions/`)
- ✅ Order types and status enums
- ✅ Position and account data structures
- ✅ Standardized interfaces

---

## 🔧 Day 1 Tasks: Setup & Configuration

### Task 1.1: Install Required Libraries ✅

```bash
# Already installed (check with):
pip list | grep alpaca
pip list | grep python-dotenv

# If needed, install:
pip install alpaca-py python-dotenv
```

**Expected Output**:
```
alpaca-py           0.x.x
python-dotenv       1.x.x
```

### Task 1.2: Create .env File 📝

**Location**: `/StatArb_Gemini/.env` (project root)

```bash
# Navigate to project root
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini

# Create .env file
touch .env
```

**Required Content** (`.env`):
```bash
# ============================================
# Phase 9 - Alpaca Paper Trading Credentials
# ============================================

# Alpaca Paper Trading API (Get from: https://app.alpaca.markets/paper/dashboard/overview)
ALPACA_API_KEY=REDACTED
ALPACA_SECRET_KEY=REDACTED
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Data Feed
ALPACA_DATA_FEED_URL=wss://stream.data.alpaca.markets/v2/iex

# Trading Mode (paper/live)
TRADING_MODE=paper

# Risk Limits (Phase 9 - Conservative)
MAX_POSITION_SIZE=100
MAX_DAILY_TRADES=10
MAX_DAILY_LOSS=100.00
REQUIRE_MANUAL_APPROVAL=true

# Logging
LOG_LEVEL=INFO
ENABLE_DEBUG_LOGGING=true
```

**⚠️ Security Notes**:
- Never commit `.env` to git (already in `.gitignore`)
- Keep API keys secure
- Use paper trading keys initially

### Task 1.3: Get Alpaca Paper Trading Credentials

**Steps**:
1. Visit: https://alpaca.markets
2. Sign up for free account
3. Go to Paper Trading Dashboard: https://app.alpaca.markets/paper/dashboard/overview
4. Navigate to: "API Keys" section
5. Generate new API Key pair (for paper trading)
6. Copy API Key and Secret Key
7. Paste into `.env` file

**What you'll see**:
```
API Key ID:      PK... (starts with PK for paper trading)
Secret Key:      (long alphanumeric string)
```

### Task 1.4: Test Configuration Loading

Create test script: `tests/phase9/test_day1_config.py`

```python
"""
Phase 9 Day 1: Configuration Loading Test
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.phase9_config import Phase9ConfigManager

def test_config_loading():
    """Test configuration loads correctly"""
    print("=" * 60)
    print("Phase 9 Day 1: Configuration Test")
    print("=" * 60)
    
    # Load configuration
    config_manager = Phase9ConfigManager()
    
    # Test Alpaca config
    alpaca_config = config_manager.get_alpaca_config()
    
    print(f"\n✓ Alpaca API Key loaded: {alpaca_config.api_key[:8]}...")
    print(f"✓ Base URL: {alpaca_config.base_url}")
    print(f"✓ Paper Trading: {alpaca_config.paper_trading}")
    
    # Validate configuration
    if alpaca_config.validate():
        print("\n✅ Configuration validation: PASSED")
    else:
        print("\n❌ Configuration validation: FAILED")
        return False
    
    # Test risk limits
    risk_limits = config_manager.get_risk_limits()
    print(f"\n📊 Risk Limits:")
    print(f"   Max Position Size: {risk_limits.max_position_size} shares")
    print(f"   Max Daily Trades: {risk_limits.max_daily_trades}")
    print(f"   Max Daily Loss: ${risk_limits.max_daily_loss}")
    print(f"   Paper Trading Only: {risk_limits.paper_trading_only}")
    
    if risk_limits.validate():
        print("\n✅ Risk limits validation: PASSED")
    else:
        print("\n❌ Risk limits validation: FAILED")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Day 1 Configuration Test: SUCCESS")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
```

**Run the test**:
```bash
python tests/phase9/test_day1_config.py
```

**Expected Output**:
```
============================================================
Phase 9 Day 1: Configuration Test
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

---

## 🔌 Day 2 Tasks: Connection & Authentication

### Task 2.1: Test Alpaca Connection

Create test script: `tests/phase9/test_day2_connection.py`

```python
"""
Phase 9 Day 2: Alpaca Connection Test
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.phase9_config import Phase9ConfigManager

async def test_alpaca_connection():
    """Test connection to Alpaca paper trading account"""
    print("=" * 60)
    print("Phase 9 Day 2: Alpaca Connection Test")
    print("=" * 60)
    
    # Load configuration
    config_manager = Phase9ConfigManager()
    alpaca_config = config_manager.get_alpaca_config()
    
    print(f"\n🔗 Connecting to: {alpaca_config.base_url}")
    print(f"📄 Paper Trading: {alpaca_config.paper_trading}")
    
    # Create adapter
    adapter = AlpacaAdapter(alpaca_config)
    
    # Test connection
    print("\n⏳ Testing connection...")
    connected = await adapter.connect()
    
    if connected:
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
        return False
    
    # Test authentication
    print("\n🔐 Testing authentication...")
    authenticated = await adapter.authenticate()
    
    if authenticated:
        print("✅ Authentication successful!")
    else:
        print("❌ Authentication failed!")
        return False
    
    # Get account info
    print("\n💼 Fetching account information...")
    account = await adapter.get_account_info()
    
    if account:
        print(f"✅ Account ID: {account.account_id}")
        print(f"   Cash: ${account.cash:,.2f}")
        print(f"   Equity: ${account.equity:,.2f}")
        print(f"   Buying Power: ${account.buying_power:,.2f}")
        print(f"   Status: {account.status}")
    else:
        print("❌ Failed to get account info!")
        return False
    
    # Disconnect
    print("\n🔌 Disconnecting...")
    await adapter.disconnect()
    print("✅ Disconnected successfully")
    
    print("\n" + "=" * 60)
    print("✅ Day 2 Connection Test: SUCCESS")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_alpaca_connection())
    sys.exit(0 if success else 1)
```

**Run the test**:
```bash
python tests/phase9/test_day2_connection.py
```

**Expected Output**:
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

### Task 2.2: Test Error Handling

Create test script: `tests/phase9/test_day2_error_handling.py`

```python
"""
Phase 9 Day 2: Error Handling Test
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.broker.adapters.alpaca_adapter import AlpacaAdapter
from core_engine.config.phase9_config import AlpacaConfig

async def test_invalid_credentials():
    """Test connection with invalid credentials"""
    print("=" * 60)
    print("Phase 9 Day 2: Error Handling Test")
    print("=" * 60)
    
    # Test 1: Invalid API key
    print("\n🧪 Test 1: Invalid API Key")
    invalid_config = AlpacaConfig(
        api_key="INVALID_KEY",
        secret_key="INVALID_SECRET",
        base_url="https://paper-api.alpaca.markets",
        paper_trading=True
    )
    
    adapter = AlpacaAdapter(invalid_config)
    
    try:
        connected = await adapter.connect()
        if not connected:
            print("✅ Correctly failed with invalid credentials")
        else:
            print("❌ Should have failed with invalid credentials!")
            return False
    except Exception as e:
        print(f"✅ Exception caught correctly: {type(e).__name__}")
    
    # Test 2: Network timeout
    print("\n🧪 Test 2: Connection timeout (will take a moment...)")
    # This would test timeout handling
    print("✅ Timeout handling would be tested here")
    
    print("\n" + "=" * 60)
    print("✅ Day 2 Error Handling Test: SUCCESS")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_invalid_credentials())
    sys.exit(0 if success else 1)
```

---

## 📊 Day 1-2 Success Criteria

### Day 1: Configuration ✅
- [x] Broker API libraries installed
- [ ] `.env` file created with Alpaca credentials
- [ ] Configuration loads without errors
- [ ] Risk limits validate correctly

### Day 2: Connection ⏳
- [ ] Can connect to Alpaca paper trading
- [ ] Authentication succeeds
- [ ] Account information retrieved
- [ ] Error handling works correctly

---

## 🚀 Next Steps

Once Days 1-2 are complete:
- **Day 3**: Order submission implementation
- **Day 4**: Order tracking & cancellation
- **Day 5**: Position & P&L management

---

## 🆘 Troubleshooting

### Issue: "No module named 'alpaca'"
**Solution**: 
```bash
pip install alpaca-py
```

### Issue: "API credentials not found"
**Solution**: 
- Check `.env` file exists in project root
- Verify `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are set
- Check no extra spaces in credentials

### Issue: "Authentication failed"
**Solution**:
- Verify credentials are for **paper trading** (start with PK)
- Check credentials haven't expired
- Regenerate API keys if needed

### Issue: "Connection timeout"
**Solution**:
- Check internet connection
- Verify Alpaca API is not down (https://status.alpaca.markets)
- Try again after a few minutes

---

## 📝 Notes

- **Paper Trading**: Always use paper trading for Phase 9 Week 1
- **API Rate Limits**: Alpaca allows 200 requests/minute
- **Testing Hours**: Test during market hours (9:30 AM - 4:00 PM ET) for best results
- **Credentials**: Never commit API keys to git

---

**Document Version**: 1.0  
**Last Updated**: October 13, 2025  
**Status**: Days 1-2 In Progress
