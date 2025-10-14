# 🚀 IB Gateway Setup Guide

**Getting Started with Interactive Brokers API Integration**

---

## 📋 Prerequisites

- ✅ Interactive Brokers account (Paper or Live)
- ✅ macOS (your system)
- ✅ Python environment active
- ✅ ibapi library installed (`pip install ibapi` - already done!)

---

## Step 1: Download IB Gateway

### Why IB Gateway?
- **Lighter than TWS** (Trader Workstation)
- **Same API functionality**
- **Runs in background**
- **Perfect for algo trading**

### Download Link
https://www.interactivebrokers.com/en/trading/ibgateway-stable.php

**Choose:** IB Gateway Stable (Latest)
- Click "Download IB Gateway" for macOS
- Should download file like: `ibgateway-latest-standalone-macos-x64.dmg`

---

## Step 2: Install IB Gateway

1. **Open the DMG file**
   - Double-click downloaded file
   - Wait for it to mount

2. **Run Installer**
   - Double-click "IB Gateway" installer
   - Click through installation prompts
   - Default installation location is fine
   - May need to enter admin password

3. **Installation Complete**
   - IB Gateway will be in `/Applications/`
   - You can eject the DMG now

---

## Step 3: Configure IB Gateway for API Access

### First Launch

1. **Open IB Gateway**
   - Go to `/Applications/`
   - Double-click "IB Gateway"
   - Wait for it to load (can take 30-60 seconds)

2. **Login Credentials**
   - **For Paper Trading:**
     - Username: Your IB paper trading username
     - Password: Your IB paper trading password
   - **For Live Trading (NOT YET!):**
     - Use your real credentials
     - ⚠️ **Start with paper trading first!**

3. **Trading Mode Selection**
   - Choose **"IB API"** (not "TWS")
   - Choose **"Paper Trading"** (for now)

### Enable API Access

1. **Once Logged In:**
   - Look for the gear/settings icon
   - Or go to: **Configure → Settings → API → Settings**

2. **API Settings to Enable:**
   ```
   ✅ Enable ActiveX and Socket Clients
   ✅ Read-Only API: NO (unchecked)
   ✅ Socket port: 4002 (paper trading)
   
   Master API Client ID: 0
   
   Trusted IP Addresses:
   ✅ 127.0.0.1 (localhost)
   ```

3. **Click "OK" or "Apply"**

4. **Important Settings:**
   - **Auto restart:** Enabled (recommended)
   - **Minimize to system tray:** Your preference
   - **Download open orders on connection:** ✅ Enabled

---

## Step 4: Verify IB Gateway is Running

### Check Status

1. **IB Gateway Window Should Show:**
   - Green "Connected" status
   - Your account number (starts with DU for paper)
   - Connection time
   - No error messages

2. **Port Verification:**
   ```bash
   # Run this in terminal to check if port 4002 is listening:
   lsof -i :4002
   ```
   
   Should show something like:
   ```
   COMMAND   PID  USER   FD   TYPE     DEVICE SIZE/OFF NODE NAME
   java    12345  lei    123u  IPv6  0x1234567      0t0  TCP *:4002 (LISTEN)
   ```

---

## Step 5: Update Environment Configuration

### Edit .env File

Add/update these lines in your `.env` file:

```bash
# ============================================
# Interactive Brokers Configuration
# ============================================
IB_HOST=127.0.0.1
IB_PORT=4002                    # 4002 for paper, 4001 for live
IB_CLIENT_ID=1                  # Use 1-10 (0 is reserved for TWS)
IB_ACCOUNT_ID=DU1234567         # Replace with your paper account ID
IB_PAPER_TRADING=true

# Broker Selection
ACTIVE_BROKER=interactive_brokers
```

### Get Your Account ID

1. In IB Gateway window, look for your account number
2. Paper trading accounts start with **DU** (e.g., DU1234567)
3. Live accounts start with **U** (e.g., U1234567)
4. Copy this to `IB_ACCOUNT_ID` in .env

---

## Step 6: Test Connection

### Run Connection Test

```bash
# Activate environment
source ai_integration_env/bin/activate

# Run IBKR connection test
pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_connection -v -s
```

### Expected Output:

```
================================================================================
TEST: IBKR Connection
================================================================================

1. Testing connection...
   ✅ Connected to IBKR

2. Checking connection status...
   ✅ Connection verified

3. Checking connection health...
   Broker: Interactive Brokers
   Host: 127.0.0.1:4002
   Client ID: 1
   Next Order ID: 123
   Paper Trading: True
   ✅ Connection healthy

4. Retrieving account information...
   Account ID: DU1234567
   Cash: $1,000,000.00
   Buying Power: $4,000,000.00
   Portfolio Value: $1,000,000.00
   ✅ Account info retrieved

5. Testing disconnect...
   ✅ Disconnected successfully

================================================================================
✅ IBKR CONNECTION TEST PASSED
================================================================================
```

---

## 🚨 Troubleshooting

### Connection Refused Error

**Problem:** `ConnectionRefusedError: [Errno 61] Connection refused`

**Solutions:**
1. **Is IB Gateway running?**
   - Check if IB Gateway window is open
   - Must show "Connected" status

2. **Correct port?**
   - Paper trading: Port 4002
   - Live trading: Port 4001
   - Check .env file matches

3. **API enabled?**
   - Go to IB Gateway settings
   - Check "Enable ActiveX and Socket Clients" is ✅

4. **Firewall blocking?**
   - Add exception for IB Gateway
   - Allow connections on port 4002

### Authentication Failed

**Problem:** Can't login to IB Gateway

**Solutions:**
1. **Using paper trading credentials?**
   - Paper trading has separate username/password
   - Found at: https://www.interactivebrokers.com/portal

2. **Account active?**
   - Check IB account status
   - Verify no restrictions

3. **2FA enabled?**
   - May need to use IB Key app
   - Or IBKR Mobile for authentication

### Timeout Error

**Problem:** Connection times out after 10 seconds

**Solutions:**
1. **IB Gateway slow to start?**
   - Give it 60 seconds after opening
   - Wait for full login completion

2. **Network issue?**
   - Check internet connection
   - Try restarting IB Gateway

3. **Too many connections?**
   - IB allows limited connections per account
   - Close other IB Gateway/TWS instances
   - Use different client_id

### Invalid Client ID

**Problem:** "Already connected" or "Client ID in use"

**Solutions:**
1. **Change client ID**
   - In .env, try `IB_CLIENT_ID=2` or `IB_CLIENT_ID=3`
   - Each connection needs unique ID

2. **Close other connections**
   - Stop other scripts using IB API
   - Restart IB Gateway

### No Market Data

**Problem:** Quotes return 0 or None

**Solutions:**
1. **Market closed?**
   - Check if US market is open (9:30 AM - 4:00 PM ET)
   - Paper trading works same hours as live

2. **Subscription needed?**
   - Some data requires subscriptions
   - Paper trading should include US stocks
   - Check IB data subscriptions in account settings

3. **Wait longer**
   - First quote can take 2-5 seconds
   - Try increasing timeout in test

---

## 📊 Port Reference

| Mode | Platform | Port | Description |
|------|----------|------|-------------|
| Paper | IB Gateway | 4002 | ✅ Use this for testing |
| Paper | TWS | 7497 | Alternative |
| Live | IB Gateway | 4001 | ⚠️ Real money! |
| Live | TWS | 7496 | ⚠️ Real money! |

---

## ✅ Success Checklist

Before running tests, verify:

- [ ] IB Gateway installed
- [ ] IB Gateway running and logged in
- [ ] Paper trading mode selected
- [ ] API access enabled in settings
- [ ] Socket port: 4002
- [ ] Trusted IP includes 127.0.0.1
- [ ] .env file updated with IB credentials
- [ ] Account ID copied to .env
- [ ] Can see green "Connected" in IB Gateway

---

## 🎯 Next Steps

Once connection test passes:

1. **Test market data:** 
   ```bash
   pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_market_data -v -s
   ```

2. **Test positions:**
   ```bash
   pytest tests/broker_integration/test_ibkr_connection.py::test_ibkr_positions -v -s
   ```

3. **Ready for order testing** (tomorrow during market hours)

---

## 💡 Pro Tips

### Keep IB Gateway Running
- IB Gateway must stay open while trading
- Set it to auto-start if desired
- Minimize to system tray to keep it out of the way

### Multiple Connections
- Can run multiple scripts with different client_ids
- client_id range: 0-32 (0 reserved for TWS)
- Useful for:
  - Development (client_id=1)
  - Production (client_id=2)
  - Monitoring (client_id=3)

### Paper Trading Benefits
- $1,000,000 starting capital
- Reset anytime via IB portal
- Same market data as live
- Same order types as live
- Perfect for testing

### Auto-Reconnect
- IB API can disconnect occasionally
- Implement auto-reconnect in production
- Monitor connection health
- Graceful error handling essential

---

## 📚 Resources

### Official Documentation
- **IB API Guide:** https://interactivebrokers.github.io/tws-api/
- **Python API:** https://interactivebrokers.github.io/tws-api/introduction.html
- **Sample Code:** https://github.com/InteractiveBrokers/tws-api-public

### IB Help
- **Client Portal:** https://www.interactivebrokers.com/portal
- **API Support:** https://www.interactivebrokers.com/en/index.php?f=5041
- **TWS API Forum:** https://groups.io/g/twsapi

### Community
- Reddit: r/algotrading
- Stack Overflow: [ibapi] tag
- GitHub: Search for "ibapi python examples"

---

## 🎊 Ready to Test!

Once IB Gateway is running and showing "Connected":

```bash
# Run the full test suite
pytest tests/broker_integration/test_ibkr_connection.py -v -s
```

**All tests passing?** You're ready to implement order management! 🚀

---

**Created:** October 13, 2025  
**Status:** Ready for Implementation  
**Next:** Run connection tests with IB Gateway
