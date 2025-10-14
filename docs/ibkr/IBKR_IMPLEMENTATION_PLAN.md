# 🏦 Interactive Brokers (IBKR) Implementation Plan

**Date:** October 13, 2025  
**Phase:** 9 - Broker Integration  
**Status:** Ready to Implement  
**Priority:** HIGH - Primary Broker

---

## 📋 EXECUTIVE SUMMARY

### Why Switch to IBKR Now?

**✅ Perfect Timing:**
1. **Alpaca Validation Complete** - Architecture proven, patterns established
2. **Account Limitations Hit** - Free Alpaca lacks historical data, limited features
3. **IBKR Account Ready** - You already have IBKR setup
4. **Production Focus** - IBKR is more suitable for serious algorithmic trading

**✅ Strategic Benefits:**
1. **Better Data Access** - Free real-time data with IBKR account
2. **More Markets** - Stocks, futures, forex, options (vs Alpaca stocks only)
3. **Lower Costs** - IBKR has lowest commissions in industry
4. **Better API** - More mature, feature-rich TWS API
5. **Professional Platform** - Industry standard for algo trading

**✅ Risk Mitigation:**
- Keep Alpaca as backup broker
- Dual-broker architecture for redundancy
- Proven implementation patterns from Alpaca work
- Paper trading available in TWS/IB Gateway

---

## 🎯 IMPLEMENTATION STRATEGY

### Phase 1: Core IBKR Adapter (Days 1-2)
**Goal:** Basic connection and order management

#### Day 1 Morning: Setup & Connection
- [ ] Install `ibapi` library
- [ ] Create `IBKRAdapter` class structure
- [ ] Implement connection to TWS/IB Gateway
- [ ] Add account authentication
- [ ] Test paper trading connection

#### Day 1 Afternoon: Market Data
- [ ] Implement real-time quote retrieval
- [ ] Add market data subscriptions
- [ ] Test data streaming
- [ ] Validate quote accuracy

#### Day 2 Morning: Order Management
- [ ] Implement market orders
- [ ] Add limit orders
- [ ] Implement stop orders
- [ ] Test order submission

#### Day 2 Afternoon: Positions & Account
- [ ] Add position tracking
- [ ] Implement account info retrieval
- [ ] Add P&L calculations
- [ ] Test position management

---

### Phase 2: Testing & Validation (Day 3)
**Goal:** Market hours validation like Alpaca

#### Comprehensive Test Suite
- [ ] Port all Alpaca tests to IBKR
- [ ] Add IBKR-specific tests
- [ ] Run during market hours
- [ ] Validate 100% pass rate

#### Performance Testing
- [ ] Measure connection stability
- [ ] Test order execution speed
- [ ] Validate data feed reliability
- [ ] Benchmark against Alpaca

---

### Phase 3: Dual-Broker Architecture (Day 4)
**Goal:** Seamless broker switching

#### Broker Manager
- [ ] Create `BrokerManager` class
- [ ] Implement broker failover logic
- [ ] Add automatic broker selection
- [ ] Test hot-swap capability

#### Configuration
- [ ] Update broker_config.py
- [ ] Add IBKR settings to .env
- [ ] Implement broker priority system
- [ ] Test configuration switching

---

## 📊 DETAILED IMPLEMENTATION GUIDE

### 1. Installation & Setup

#### Install IBAPI
```bash
# Activate environment
source ai_integration_env/bin/activate

# Install Interactive Brokers API
pip install ibapi

# Verify installation
python -c "import ibapi; print(f'IBAPI Version: {ibapi.__version__}')"
```

#### TWS/IB Gateway Setup
1. **Download IB Gateway** (lighter than TWS)
   - https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
   - Use "Stable" version for production

2. **Configure Paper Trading**
   - Login with paper trading credentials
   - Enable API connections
   - Set port: 4002 (paper) or 4001 (live)
   - Enable "Download open orders on connection"

3. **API Settings**
   - Settings → API → Settings
   - Enable "ActiveX and Socket Clients"
   - Set "Socket port": 4002
   - Trusted IP: 127.0.0.1
   - Master API client ID: 0

---

### 2. Environment Configuration

#### Add to .env
```bash
# Interactive Brokers Configuration
IB_HOST=127.0.0.1
IB_PORT=4002                    # 4002 for paper, 4001 for live
IB_CLIENT_ID=1                  # Unique client ID (0-32)
IB_ACCOUNT_ID=DU1234567         # Your paper trading account
IB_PAPER_TRADING=true

# Broker Selection
ACTIVE_BROKER=interactive_brokers  # Switch from alpaca
BACKUP_BROKER=alpaca
ENABLE_BROKER_FAILOVER=true
```

---

### 3. Core Architecture

#### File Structure
```
core_engine/
├── broker/
│   ├── adapters/
│   │   ├── alpaca_adapter.py      (existing)
│   │   ├── ibkr_adapter.py        (NEW)
│   │   └── base_adapter.py        (NEW - abstract interface)
│   ├── manager.py                 (NEW - broker manager)
│   └── failover.py                (NEW - failover logic)
```

#### Base Adapter Interface
```python
# base_adapter.py - Abstract interface both adapters implement
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

class BaseBrokerAdapter(ABC):
    """Abstract base class for broker adapters"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to broker"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    def submit_market_order(self, symbol: str, quantity: float, side: OrderSide) -> Order:
        """Submit market order"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """Get account information"""
        pass
    
    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest quote"""
        pass
    
    # ... other required methods
```

---

### 4. IBKR Adapter Implementation

#### Core Structure (ibkr_adapter.py)
```python
"""
Interactive Brokers Adapter
Production-ready broker integration using IB TWS API
"""

import logging
import threading
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order as IBOrder

from core_engine.broker.adapters.base_adapter import BaseBrokerAdapter
from core_engine.type_definitions.orders import Order, OrderSide, OrderType, OrderStatus
from core_engine.type_definitions.positions import Position
from core_engine.type_definitions.account import AccountInfo

logger = logging.getLogger(__name__)


class IBKRWrapper(EWrapper):
    """Callback handler for IB API events"""
    
    def __init__(self):
        super().__init__()
        self.next_order_id = None
        self.positions = {}
        self.account_values = {}
        self.quotes = {}
        self.errors = []
        
    def nextValidId(self, orderId: int):
        """Callback for next valid order ID"""
        logger.info(f"Next valid order ID: {orderId}")
        self.next_order_id = orderId
    
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Callback for errors"""
        error_msg = f"Error {errorCode}: {errorString}"
        logger.error(error_msg)
        self.errors.append({
            'req_id': reqId,
            'code': errorCode,
            'message': errorString,
            'timestamp': datetime.now()
        })
    
    def position(self, account, contract, position, avgCost):
        """Callback for position updates"""
        self.positions[contract.symbol] = {
            'symbol': contract.symbol,
            'position': position,
            'avg_cost': avgCost,
            'account': account
        }
    
    def accountSummary(self, reqId, account, tag, value, currency):
        """Callback for account summary"""
        self.account_values[tag] = {
            'value': value,
            'currency': currency,
            'account': account
        }
    
    def tickPrice(self, reqId, tickType, price, attrib):
        """Callback for price updates"""
        if reqId not in self.quotes:
            self.quotes[reqId] = {}
        
        if tickType == 1:  # BID
            self.quotes[reqId]['bid_price'] = price
        elif tickType == 2:  # ASK
            self.quotes[reqId]['ask_price'] = price
        elif tickType == 4:  # LAST
            self.quotes[reqId]['last_price'] = price
    
    def tickSize(self, reqId, tickType, size):
        """Callback for size updates"""
        if reqId not in self.quotes:
            self.quotes[reqId] = {}
        
        if tickType == 0:  # BID_SIZE
            self.quotes[reqId]['bid_size'] = size
        elif tickType == 3:  # ASK_SIZE
            self.quotes[reqId]['ask_size'] = size
        elif tickType == 5:  # LAST_SIZE
            self.quotes[reqId]['last_size'] = size


class IBKRClient(EClient):
    """IB API client"""
    
    def __init__(self, wrapper):
        super().__init__(wrapper)


class IBKRAdapter(BaseBrokerAdapter):
    """
    Interactive Brokers adapter for live trading
    
    Features:
    - Real-time market data
    - Order management (market, limit, stop)
    - Position tracking
    - Account monitoring
    - Paper and live trading support
    """
    
    def __init__(self, config):
        self.config = config
        self.wrapper = IBKRWrapper()
        self.client = IBKRClient(self.wrapper)
        self._connected = False
        self._thread = None
        self._next_req_id = 1
        
        logger.info(f"Initialized IBKR adapter (paper_trading={config.paper_trading})")
    
    def connect(self) -> bool:
        """Connect to IB Gateway/TWS"""
        try:
            logger.info(f"Connecting to IBKR at {self.config.host}:{self.config.port}...")
            
            # Connect to IB
            self.client.connect(
                self.config.host,
                self.config.port,
                self.config.client_id
            )
            
            # Start message processing thread
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while self.wrapper.next_order_id is None:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Connection timeout")
                time.sleep(0.1)
            
            self._connected = True
            
            # Request account summary
            self.client.reqAccountSummary(9001, "All", "TotalCashValue,AvailableFunds,NetLiquidation")
            
            logger.info(f"✅ Connected to IBKR (client_id={self.config.client_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            return False
    
    def _run_loop(self):
        """Run IB client message loop"""
        self.client.run()
    
    def disconnect(self) -> None:
        """Disconnect from IB"""
        if self._connected:
            self.client.disconnect()
            self._connected = False
            logger.info("✅ Disconnected from IBKR")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.client.isConnected()
    
    def _create_contract(self, symbol: str) -> Contract:
        """Create IB contract for US stocks"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract
    
    def submit_market_order(self, symbol: str, quantity: float, side: OrderSide) -> Order:
        """Submit market order"""
        try:
            # Create contract
            contract = self._create_contract(symbol)
            
            # Create order
            ib_order = IBOrder()
            ib_order.action = "BUY" if side == OrderSide.BUY else "SELL"
            ib_order.orderType = "MKT"
            ib_order.totalQuantity = quantity
            
            # Get order ID
            order_id = self.wrapper.next_order_id
            self.wrapper.next_order_id += 1
            
            # Submit order
            self.client.placeOrder(order_id, contract, ib_order)
            
            # Create our Order object
            order = Order(
                order_id=str(order_id),
                symbol=symbol,
                quantity=quantity,
                side=side,
                type=OrderType.MARKET,
                status=OrderStatus.SUBMITTED,
                submitted_at=datetime.now()
            )
            
            logger.info(f"✅ Market order submitted: {side.value} {quantity} {symbol} (order_id={order_id})")
            return order
            
        except Exception as e:
            logger.error(f"Failed to submit market order: {e}")
            raise
    
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        try:
            # Request positions
            self.client.reqPositions()
            time.sleep(1)  # Wait for response
            
            positions = []
            for symbol, pos_data in self.wrapper.positions.items():
                position = Position(
                    symbol=symbol,
                    quantity=pos_data['position'],
                    avg_entry_price=pos_data['avg_cost'],
                    current_price=pos_data['avg_cost'],  # Will be updated with quote
                    market_value=pos_data['position'] * pos_data['avg_cost'],
                    unrealized_pl=0.0  # Calculate after getting current price
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            # Account values already requested in connect()
            time.sleep(0.5)  # Wait for latest values
            
            cash = float(self.wrapper.account_values.get('TotalCashValue', {}).get('value', 0))
            buying_power = float(self.wrapper.account_values.get('AvailableFunds', {}).get('value', 0))
            portfolio_value = float(self.wrapper.account_values.get('NetLiquidation', {}).get('value', 0))
            
            account = AccountInfo(
                account_id=self.config.account_id or "UNKNOWN",
                cash=cash,
                buying_power=buying_power,
                portfolio_value=portfolio_value,
                equity=portfolio_value
            )
            
            return account
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest quote"""
        try:
            # Create contract
            contract = self._create_contract(symbol)
            
            # Request market data
            req_id = self._next_req_id
            self._next_req_id += 1
            
            self.client.reqMktData(req_id, contract, "", False, False, [])
            
            # Wait for quote
            timeout = 5
            start_time = time.time()
            while req_id not in self.wrapper.quotes:
                if time.time() - start_time > timeout:
                    logger.warning(f"Quote timeout for {symbol}")
                    return None
                time.sleep(0.1)
            
            # Cancel market data
            self.client.cancelMktData(req_id)
            
            quote_data = self.wrapper.quotes[req_id]
            
            return {
                'symbol': symbol,
                'bid_price': quote_data.get('bid_price', 0),
                'ask_price': quote_data.get('ask_price', 0),
                'last_price': quote_data.get('last_price', 0),
                'bid_size': quote_data.get('bid_size', 0),
                'ask_size': quote_data.get('ask_size', 0),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    # ... implement remaining methods (limit orders, stop orders, etc.)
```

---

## 🎯 ADVANTAGES OF IBKR OVER ALPACA

### 1. Data Access
| Feature | Alpaca Free | IBKR |
|---------|------------|------|
| Real-time Quotes | ✅ | ✅ |
| Historical Data | ❌ | ✅ (Free with account) |
| Market Depth | ❌ | ✅ |
| Level 2 Data | ❌ | ✅ (Subscription) |
| News Feed | Limited | ✅ |

### 2. Market Access
| Market | Alpaca | IBKR |
|--------|--------|------|
| US Stocks | ✅ | ✅ |
| Options | ❌ | ✅ |
| Futures | ❌ | ✅ |
| Forex | ❌ | ✅ |
| International | ❌ | ✅ (135 markets) |
| Crypto | ✅ | ✅ |

### 3. Trading Features
| Feature | Alpaca | IBKR |
|---------|--------|------|
| Market Orders | ✅ | ✅ |
| Limit Orders | ✅ | ✅ |
| Stop Orders | ✅ | ✅ |
| Bracket Orders | ✅ | ✅ |
| Algo Orders | Limited | ✅ (Advanced) |
| Short Selling | ✅ | ✅ (Better rates) |
| Margin | ✅ | ✅ (Lower rates) |

### 4. Cost Comparison
| Item | Alpaca | IBKR |
|------|--------|------|
| Commission | $0 | $0 (IBKR Lite) or $0.005/share |
| Data Fees | Free | Free with account activity |
| Platform Fee | $0 | $0 |
| Margin Rates | ~9% | 1.5-6.83% (much better!) |
| Short Fees | Market | Competitive |

### 5. API Quality
| Aspect | Alpaca | IBKR |
|--------|--------|------|
| Documentation | Good | Excellent |
| Reliability | Good | Excellent |
| Features | Basic | Comprehensive |
| Community | Growing | Mature |
| Examples | Limited | Extensive |
| Maturity | 5 years | 20+ years |

---

## 📝 MIGRATION CHECKLIST

### Pre-Migration
- [x] Alpaca architecture validated
- [x] IBKR account setup complete
- [ ] IB Gateway/TWS installed
- [ ] Paper trading configured
- [ ] API access enabled

### Implementation
- [ ] Install ibapi library
- [ ] Create BaseBrokerAdapter interface
- [ ] Implement IBKRAdapter
- [ ] Port Alpaca tests to IBKR
- [ ] Test during market hours
- [ ] Validate 100% pass rate

### Integration
- [ ] Update broker_config.py
- [ ] Add IBKR settings to .env
- [ ] Create BrokerManager class
- [ ] Implement failover logic
- [ ] Test broker switching

### Validation
- [ ] Run full test suite
- [ ] Execute real orders (paper)
- [ ] Monitor for 24 hours
- [ ] Compare with Alpaca
- [ ] Document differences

### Production
- [ ] Set IBKR as primary broker
- [ ] Configure Alpaca as backup
- [ ] Deploy monitoring
- [ ] Test failover mechanism
- [ ] Begin strategy integration

---

## ⏰ TIMELINE

### Aggressive (3-4 Days)
- **Day 1:** Core implementation (connection, orders, positions)
- **Day 2:** Complete all methods, add tests
- **Day 3:** Market hours validation
- **Day 4:** Dual-broker architecture

### Conservative (5-7 Days)
- **Days 1-2:** Core implementation with extensive testing
- **Day 3:** Additional features (historical data, advanced orders)
- **Day 4:** Comprehensive test suite
- **Day 5:** Market hours validation
- **Days 6-7:** Dual-broker system, failover testing

---

## 🎯 RECOMMENDED APPROACH

### Option 1: Full Migration (Recommended)
**Rationale:** You have limitations with Alpaca and IBKR is superior

**Steps:**
1. Implement IBKR adapter (2-3 days)
2. Port all tests to IBKR
3. Market hours validation
4. Switch to IBKR as primary
5. Keep Alpaca as emergency backup

**Timeline:** 3-4 days  
**Risk:** Low (proven architecture)  
**Benefit:** Immediate access to better features

### Option 2: Dual Implementation
**Rationale:** Maximum reliability with two brokers

**Steps:**
1. Create BaseBrokerAdapter interface
2. Refactor AlpacaAdapter to extend base
3. Implement IBKRAdapter extending base
4. Create BrokerManager for switching
5. Test both brokers in parallel

**Timeline:** 5-7 days  
**Risk:** Very Low (redundancy)  
**Benefit:** Production-grade failover system

---

## 🚨 CRITICAL SUCCESS FACTORS

### Must Have
1. **IB Gateway Running** - Keep it running during trading hours
2. **Paper Trading First** - Validate everything before live
3. **Connection Monitoring** - IB API can disconnect, need auto-reconnect
4. **Error Handling** - IB API has more error codes than Alpaca
5. **Threading** - IB API requires proper thread management

### Nice to Have
1. **Dual broker support** - For redundancy
2. **Automatic failover** - Switch brokers on failure
3. **Performance monitoring** - Compare Alpaca vs IBKR
4. **Cost tracking** - IBKR has commissions (even if small)

---

## 💡 RECOMMENDATION

**YES, implement IBKR now!** Here's why:

1. **✅ Perfect Timing**
   - You've validated the architecture
   - You know the patterns that work
   - You've hit Alpaca's limitations
   - IBKR account is ready

2. **✅ Better Foundation**
   - More professional platform
   - Better data access
   - More markets for future
   - Lower costs long-term

3. **✅ Manageable Risk**
   - Copy-paste most patterns from Alpaca
   - Paper trading available
   - Keep Alpaca as backup
   - 3-4 day implementation

4. **✅ Strategic Value**
   - Sets up for futures/options later
   - Industry-standard platform
   - Better for institutional feel
   - More impressive in portfolio

**Suggested Next Steps:**
1. Start tomorrow with IB Gateway setup
2. Implement core IBKRAdapter (2 days)
3. Market hours validation (day 3)
4. Switch to IBKR as primary (day 4)

---

## 📚 RESOURCES

### Documentation
- IBAPI Python: https://interactivebrokers.github.io/tws-api/
- IB Gateway Guide: https://www.interactivebrokers.com/en/index.php?f=16457
- Sample Code: https://github.com/InteractiveBrokers/tws-api-public

### Community
- Reddit r/algotrading - Lots of IBKR users
- Elite Trader forums - IB API section
- QuantConnect - IBKR examples

---

**Ready to implement? Let's start with IB Gateway setup and ibapi installation!** 🚀
