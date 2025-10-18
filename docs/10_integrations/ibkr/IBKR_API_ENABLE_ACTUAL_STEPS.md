# IBKR Professional Account - API Data Access (Actual Steps)

## Current Issue
Error 10089: "Requested market data requires additional subscription for API"

Your Professional account includes real-time data, but it needs to be enabled for API access.

---

## Solution 1: Enable in Settings > User Settings (Most Common)

### Step 1: Navigate to Trading Permissions
1. Log into: https://www.interactivebrokers.com/portal
2. Click **Settings** (top right menu)
3. Click **User Settings** (not Account Settings!)
4. Scroll down to **Trading Platforms** section
5. Look for **"API Settings"** or **"Trading Permissions"**

### Step 2: Enable API Access
Look for these options:
- ☑️ **Enable API**
- ☑️ **Enable API Market Data**
- ☑️ **Enable Paper Trading API** (if separate)
- **Trusted IPs**: Add `127.0.0.1` or leave as "All"

### Step 3: Save and Restart
1. Click **Save** or **Apply**
2. Close IB Gateway completely
3. Wait 30 seconds
4. Restart IB Gateway
5. Test again

---

## Solution 2: Global Configuration > API Settings

### If you don't see it in User Settings:

1. Go to: https://www.interactivebrokers.com/portal
2. Click **Settings** menu
3. Look for **"Global Configuration"** or **"Security"**
4. Find **"API"** section
5. Enable:
   - ☑️ **Enable ActiveX and Socket Clients**
   - ☑️ **Read-Only API** (uncheck this - you want full access)
   - ☑️ **Download open orders on connection**

---

## Solution 3: IB Gateway Configuration (Most Direct)

### The API settings might need to be enabled in IB Gateway itself:

1. **Open IB Gateway**
2. Click **Configure** menu (top)
3. Click **Settings**
4. Go to **API** section (left sidebar)
5. Look for **"Enable API"** or **"API Settings"**
6. Check:
   - ☑️ **Enable ActiveX and Socket Clients**
   - ☑️ **Socket port**: 4002 (paper trading)
   - ☑️ **Trusted IPs**: `127.0.0.1` (or 0.0.0.0 for all)
   - ☑️ **Master API client ID**: Can be blank or 0
   - ☑️ **Read-Only API**: **UNCHECKED** (you need read/write)
   - ☑️ **Allow connections from localhost only**: **CHECKED** (for security)
7. Click **OK**
8. **Restart IB Gateway**

---

## Solution 4: Market Data Permissions (In IB Gateway)

### Sometimes the permission is in IB Gateway's market data settings:

1. **In IB Gateway**, click **Configure → Settings**
2. Go to **Market Data** section (left sidebar)
3. Look for your subscription listed
4. If you see **"US Securities Snapshot Bundle"** or similar:
   - Should show status: **Active** or **Subscribed**
   - If it shows **"Not Enabled for API"**, there should be a checkbox to enable it
5. Enable any checkboxes related to API access
6. Click **OK** and restart

---

## Solution 5: Check Account Settings > Trading Permissions

### Alternative location in Client Portal:

1. Go to: https://www.interactivebrokers.com/portal
2. Click **Settings**
3. Click **Account Settings** (instead of User Settings)
4. Look for **"Trading Permissions"** or **"Paper Trading"**
5. Find **"API Access"** section
6. Enable:
   - ☑️ **Paper Trading**
   - ☑️ **API Access for Paper Trading**

---

## Solution 6: Contact IBKR Support (Recommended if above don't work)

Your Professional account definitely includes API access - it's just a configuration issue.

### Call IBKR Support (Fastest - 5 minutes):
**Phone**: +1-877-442-2757

**What to say:**
> "I have a Professional account with the US Securities Snapshot Bundle. I need to enable API market data access for paper trading. I'm getting Error 10089 when connecting via the API."

They'll enable it on their side immediately.

### Or Message via Client Portal:
1. Go to: https://www.interactivebrokers.com/portal
2. Click **Inbox** or **Message Center**
3. Click **Compose Message**
4. **To**: Account Management
5. **Subject**: Enable API Market Data for Paper Trading
6. **Message**:

```
Hello,

I have a Professional account with an active US Securities Snapshot 
Bundle subscription. I've signed the Market Data API Acknowledgement.

I'm trying to access market data via the Python API (IB Gateway, 
port 4002) for paper trading, but I receive Error 10089: 
"Requested market data requires additional subscription for API."

Could you please enable API market data access for my paper 
trading account?

Account: [Your Account Number]
Paper Trading Port: 4002
Client ID: 2

Thank you!
```

---

## Verification After Enabling

After enabling any of the above, test with:

```bash
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
python test_market_data_diagnostic.py
```

**Working output:**
```
[1s] ✅ Got data: {'bid_price': 580.45, 'ask_price': 580.46, ...}
```

**Still Error 10089?**
- Try restarting IB Gateway 2-3 times
- Wait 30 minutes for permissions to propagate
- Call IBKR support - they can enable it instantly

---

## What's Happening

Your Professional subscription **includes** real-time market data, but IBKR requires a separate permission flag for **API access**. This is a security feature to prevent unauthorized API usage.

Once enabled, you should get real-time data immediately - no waiting period.

---

## Timeline

| Method | Time to Work |
|--------|-------------|
| Enable in IB Gateway settings | Immediate (after restart) |
| Enable in Client Portal | 5-30 minutes |
| IBKR Support enables it | Immediate |

---

## My Recommendation

**Call IBKR support** - it's the fastest way. They can enable it while you're on the phone and you can test immediately. The automated settings can be confusing to find.

Phone: **+1-877-442-2757**
Say: "Enable API market data for paper trading"

---

## Temporary Workaround

While waiting, you can use delayed data to continue development:

**Edit `.env`:**
```bash
IB_HAS_MARKET_DATA_SUBSCRIPTION=false
```

This will use free delayed data (15-20 min behind) but everything else will work perfectly.
