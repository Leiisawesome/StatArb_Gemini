# Phase 9 - Day 1: Environment Setup & Alpaca Integration

**Date**: October 13, 2025  
**Status**: 🚀 STARTING  
**Focus**: Foundation setup, Alpaca REST API integration

---

## Morning Session: Environment Setup (9:00 AM - 12:00 PM)

### 1. Install Required Libraries (30 min)

#### Task List
- [ ] Install Alpaca SDK
- [ ] Install IB API (preparation)
- [ ] Install WebSocket libraries
- [ ] Update requirements.txt

#### Commands
```bash
# Activate virtual environment
cd /Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini
source ai_integration_env/bin/activate

# Install broker APIs
pip install alpaca-py>=0.9.0
pip install alpaca-trade-api>=3.0.0
pip install ibapi>=10.19.2

# WebSocket support
pip install websocket-client>=1.6.0
pip install websockets>=11.0

# Security & configuration
pip install python-dotenv>=1.0.0
pip install cryptography>=41.0.0

# Update requirements
pip freeze > requirements.txt
```

---

### 2. Setup Secure Credential Management (45 min)

#### Create .env File (DO NOT COMMIT)
```bash
# Create .env file
cat > .env << 'EOF'
# Phase 9 Broker Credentials - KEEP SECURE!

# Alpaca (Paper Trading)
ALPACA_PAPER_API_KEY=your_paper_api_key_here
ALPACA_PAPER_SECRET_KEY=your_paper_secret_key_here
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets

# Alpaca Data Feed
ALPACA_DATA_API_KEY=your_data_api_key_here
ALPACA_DATA_SECRET_KEY=your_data_secret_key_here
ALPACA_DATA_FEED_URL=wss://stream.data.alpaca.markets/v2/iex

# Interactive Brokers (Paper Trading)
IB_PAPER_HOST=127.0.0.1
IB_PAPER_PORT=7497
IB_PAPER_CLIENT_ID=1
IB_PAPER_ACCOUNT=DU1234567

# Safety Settings
PHASE_9_PAPER_TRADING_ONLY=true
PHASE_9_ENABLE_KILL_SWITCH=true
PHASE_9_MAX_POSITION_SIZE=100
PHASE_9_MAX_DAILY_LOSS=100.00

EOF

# Ensure .env is in .gitignore
echo ".env" >> .gitignore
```

#### Create Configuration Module
Create: `core_engine/config/phase9_config.py`

---

### 3. Create Phase 9 Configuration (45 min)

#### Task List
- [ ] Create phase9_config.py
- [ ] Implement credential loading
- [ ] Add validation logic
- [ ] Create broker configurations

#### Files to Create
1. `core_engine/config/phase9_config.py` - Main config
2. `core_engine/config/broker_credentials.py` - Credential manager
3. `config/phase9_limits.yaml` - Risk limits

---

### 4. Setup Paper Trading Accounts (60 min)

#### Alpaca Account Setup
1. **Create Alpaca Account**
   - Visit: https://alpaca.markets/
   - Sign up for free account
   - Verify email
   - Enable paper trading

2. **Generate API Keys**
   - Go to: Paper Trading Dashboard
   - Generate API Key & Secret
   - Copy to .env file
   - Test authentication

3. **Verify Account Status**
   - Check account type (paper/live)
   - Verify data subscriptions
   - Check trading permissions

#### Interactive Brokers Setup (Preparation)
1. **Paper Trading Account**
   - If you have IB account: Request paper account
   - If no account: Sign up process takes 1-2 days
   - Note: Can proceed with Alpaca while waiting

2. **IB Gateway Installation**
   - Download from IB website
   - Install for your OS
   - Configure paper trading port (7497)
   - Test manual connection

---

## Afternoon Session: Alpaca REST API Integration (1:00 PM - 5:00 PM)

### 5. Create Alpaca Adapter (90 min)

#### Task: Implement AlpacaAdapter class
Location: `core_engine/broker/adapters/alpaca_adapter.py`

#### Features to Implement
- [ ] Connection management
- [ ] Authentication
- [ ] Account information retrieval
- [ ] Position retrieval
- [ ] Basic error handling

#### Testing
- [ ] Test connection
- [ ] Test authentication
- [ ] Test account info
- [ ] Test error scenarios

---

### 6. Implement Basic Order Submission (90 min)

#### Task: Add order submission to AlpacaAdapter

#### Order Types to Support
- [ ] Market orders (BUY/SELL)
- [ ] Limit orders
- [ ] Order validation
- [ ] Error handling

#### Testing
- [ ] Submit test market order
- [ ] Submit test limit order
- [ ] Test validation errors
- [ ] Verify order appears in Alpaca

---

### 7. Create Integration Tests (60 min)

#### Test File: `tests/integration/broker/test_alpaca_integration.py`

#### Tests to Create
- [ ] `test_alpaca_connection` - Connection works
- [ ] `test_alpaca_authentication` - Auth succeeds
- [ ] `test_get_account_info` - Account data retrieved
- [ ] `test_get_positions` - Positions retrieved
- [ ] `test_submit_market_order` - Market order submission
- [ ] `test_submit_limit_order` - Limit order submission
- [ ] `test_order_validation` - Validation errors caught
- [ ] `test_connection_error_handling` - Errors handled

#### Safety Checks
- [ ] All tests use paper trading
- [ ] Order sizes are minimal (1 share)
- [ ] No real money at risk
- [ ] Tests clean up after themselves

---

## Evening Session: Testing & Documentation (5:00 PM - 7:00 PM)

### 8. Run All Tests (30 min)

```bash
# Run Phase 9 Day 1 tests
pytest tests/integration/broker/test_alpaca_integration.py -v

# Run all integration tests (ensure no regressions)
pytest tests/integration/ -v --tb=short

# Expected results:
# - New Alpaca tests: 8/8 passing
# - Existing tests: 109/109 passing
# - Total: 117/117 passing
```

---

### 9. Create Setup Documentation (60 min)

#### Documents to Create
- [ ] `docs/phase9/ALPACA_SETUP_GUIDE.md` - Setup instructions
- [ ] `docs/phase9/CREDENTIAL_MANAGEMENT.md` - Security guide
- [ ] `docs/phase9/TROUBLESHOOTING.md` - Common issues

---

### 10. Day 1 Summary Report (30 min)

#### Create: `docs/PHASE_9_DAY_1_COMPLETE.md`

#### Content
- Tasks completed
- Tests passing
- Code metrics
- Issues encountered
- Lessons learned
- Day 2 preparation

---

## Success Criteria - Day 1

### Must Complete ✅
- [ ] All libraries installed
- [ ] Credentials securely stored
- [ ] Alpaca paper trading account setup
- [ ] AlpacaAdapter implemented
- [ ] Connection & authentication working
- [ ] Account info retrieval working
- [ ] Basic order submission working
- [ ] 8 integration tests passing
- [ ] All existing tests still passing (109/109)
- [ ] Documentation created

### Metrics
- **New Code**: ~300-500 lines
- **New Tests**: ~200-300 lines
- **Test Pass Rate**: 100% (117/117)
- **Documentation**: 3 new guides
- **Time Estimate**: 8 hours

---

## Risk Mitigation

### Potential Issues

1. **API Rate Limits**
   - Solution: Implement rate limiting in adapter
   - Backup: Use longer delays between tests

2. **Account Approval Delays**
   - Solution: Use mock broker for development
   - Backup: Continue with architecture work

3. **Authentication Failures**
   - Solution: Verify credentials format
   - Backup: Check Alpaca status page

4. **Test Flakiness**
   - Solution: Add retries for network calls
   - Backup: Mark as integration tests with @pytest.mark.slow

---

## Code Structure After Day 1

```
core_engine/
├── broker/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── alpaca_adapter.py          # NEW - Day 1
│   │   └── ib_adapter.py              # Preparation for Day 2
│   ├── broker_adapter.py              # Existing
│   └── broker_manager.py              # Existing
├── config/
│   ├── phase9_config.py               # NEW - Day 1
│   └── broker_credentials.py          # NEW - Day 1

tests/
├── integration/
│   └── broker/
│       ├── __init__.py
│       ├── conftest.py                # Fixtures
│       └── test_alpaca_integration.py # NEW - 8 tests

docs/
├── PHASE_9_PLAN.md                    # Created
├── PHASE_9_DAY_1_PLAN.md             # This file
├── PHASE_9_DAY_1_COMPLETE.md         # To create
└── phase9/
    ├── ALPACA_SETUP_GUIDE.md          # NEW
    ├── CREDENTIAL_MANAGEMENT.md       # NEW
    └── TROUBLESHOOTING.md             # NEW

config/
└── phase9_limits.yaml                 # NEW - Risk limits

.env                                   # NEW - Credentials (not committed)
```

---

## Next Steps - Day 2

### Preview: Interactive Brokers Setup
- Install IB Gateway/TWS
- Configure paper trading
- Implement IB adapter
- Test connection flow
- Create multi-broker manager

---

## Resources

### Alpaca Documentation
- Getting Started: https://alpaca.markets/docs/
- REST API: https://alpaca.markets/docs/api-references/trading-api/
- Python SDK: https://alpaca.markets/docs/python-sdk/
- Paper Trading: https://alpaca.markets/docs/trading/paper-trading/

### Code Examples
- Alpaca GitHub: https://github.com/alpacahq/alpaca-py
- Example Notebooks: Available in Alpaca docs

### Support
- Alpaca Slack: https://alpaca.markets/slack
- Status Page: https://status.alpaca.markets/

---

**Status**: Ready to begin! 🚀  
**Next Action**: Install libraries and create Alpaca account  
**Estimated Time**: Full day (8 hours)  
**End Goal**: Alpaca integration working, tests passing
