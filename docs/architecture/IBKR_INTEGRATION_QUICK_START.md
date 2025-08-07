# IBKR Integration Quick Start Guide

## **🎯 Current Status: IBKR Account Ready**

Since you already have an IBKR trading account, we can skip the account setup phase and focus on the technical integration. This guide will help you get your system connected to IBKR quickly.

## **📋 Pre-Integration Checklist**

### **1. Account Verification**
- [ ] **Account Type**: Confirm you have IBKR Pro account (not Lite)
- [ ] **API Access**: Verify API access is enabled in your account
- [ ] **Account Permissions**: Ensure you have trading permissions
- [ ] **Market Data**: Confirm you have market data subscriptions for your target symbols

### **2. Technical Setup**
- [ ] **TWS or IB Gateway**: Install and configure
- [ ] **API Credentials**: Note your account ID and connection details
- [ ] **Network Access**: Ensure your system can connect to IBKR servers
- [ ] **Python Environment**: Install required dependencies

## **⚡ Quick Start Implementation**

### **Step 1: Environment Setup (Day 1)**

```bash
# Install IBKR Python SDK
pip install ib_insync

# Install additional dependencies
pip install pandas numpy asyncio logging
```

### **Step 2: Configuration Setup**

Create your IBKR configuration:

```python
# config/ibkr_config.py

import os
from dataclasses import dataclass

@dataclass
class IBKRConfig:
    """Your IBKR Configuration"""
    
    # Connection settings
    host: str = "127.0.0.1"
    port: int = 7497  # Paper Trading (use 7496 for live)
    client_id: int = 1
    account_id: str = "YOUR_ACCOUNT_ID"  # Replace with your actual account ID
    
    # Environment settings
    paper_trading: bool = True  # Start with paper trading
    enable_logging: bool = True
    log_level: str = "INFO"
    
    # Risk settings (adjust based on your account size)
    max_position_size: int = 1000
    max_order_value: float = 10000.0
    max_daily_loss: float = 500.0
    
    # Order settings
    default_order_type: str = "LMT"
    default_time_in_force: str = "DAY"
    enable_smart_routing: bool = True

# Environment variables (optional)
def load_from_env():
    return IBKRConfig(
        host=os.getenv('IBKR_HOST', '127.0.0.1'),
        port=int(os.getenv('IBKR_PORT', '7497')),
        client_id=int(os.getenv('IBKR_CLIENT_ID', '1')),
        account_id=os.getenv('IBKR_ACCOUNT_ID', 'YOUR_ACCOUNT_ID'),
        paper_trading=os.getenv('IBKR_PAPER_TRADING', 'true').lower() == 'true'
    )
```

### **Step 3: Basic Connection Test**

```python
# test_connection.py

import asyncio
from ib_insync import *
from config.ibkr_config import IBKRConfig

async def test_ibkr_connection():
    """Test basic IBKR connection"""
    
    # Load configuration
    config = IBKRConfig()
    
    # Create IB connection
    ib = IB()
    
    try:
        # Connect to IBKR
        print(f"Connecting to IBKR on {config.host}:{config.port}...")
        ib.connect(
            host=config.host,
            port=config.port,
            clientId=config.client_id
        )
        
        # Wait for connection
        await asyncio.sleep(2)
        
        if ib.isConnected():
            print("✅ Successfully connected to IBKR!")
            
            # Get account info
            account_values = ib.accountSummary()
            print(f"Account: {config.account_id}")
            
            # Get current positions
            positions = ib.positions()
            print(f"Current positions: {len(positions)}")
            
            # Test market data
            contract = Stock('AAPL', 'SMART', 'USD')
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if bars:
                print(f"✅ Market data test successful: {len(bars)} bars received")
            
            return True
            
        else:
            print("❌ Failed to connect to IBKR")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("Disconnected from IBKR")

if __name__ == "__main__":
    asyncio.run(test_ibkr_connection())
```

### **Step 4: Quick Integration Test**

```python
# quick_integration_test.py

import asyncio
import pandas as pd
from ib_insync import *
from config.ibkr_config import IBKRConfig

class QuickIBKRIntegration:
    """Quick integration test for IBKR"""
    
    def __init__(self, config: IBKRConfig):
        self.config = config
        self.ib = IB()
        self.connected = False
        
    async def connect(self):
        """Connect to IBKR"""
        try:
            self.ib.connect(
                host=self.config.host,
                port=self.config.port,
                clientId=self.config.client_id
            )
            await asyncio.sleep(2)
            self.connected = self.ib.isConnected()
            return self.connected
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
            
    async def test_market_data(self, symbol: str = 'AAPL'):
        """Test market data retrieval"""
        if not self.connected:
            return None
            
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Get historical data
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if bars:
                df = util.df(bars)
                print(f"✅ Market data for {symbol}: {len(df)} bars")
                print(f"Latest price: ${df['close'].iloc[-1]:.2f}")
                return df
            else:
                print(f"❌ No market data received for {symbol}")
                return None
                
        except Exception as e:
            print(f"Market data error: {e}")
            return None
            
    async def test_account_info(self):
        """Test account information retrieval"""
        if not self.connected:
            return None
            
        try:
            # Get account summary
            account_values = self.ib.accountSummary()
            
            summary = {}
            for value in account_values:
                summary[value.tag] = float(value.value)
                
            print("✅ Account Information:")
            print(f"  Net Liquidation: ${summary.get('NetLiquidation', 0):,.2f}")
            print(f"  Total Cash: ${summary.get('TotalCashValue', 0):,.2f}")
            print(f"  Buying Power: ${summary.get('BuyingPower', 0):,.2f}")
            
            return summary
            
        except Exception as e:
            print(f"Account info error: {e}")
            return None
            
    async def test_paper_order(self, symbol: str = 'AAPL', quantity: int = 1):
        """Test paper trading order placement"""
        if not self.connected:
            return None
            
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Get current market price
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='1 min',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if not bars:
                print("❌ Cannot get market price for order")
                return None
                
            current_price = bars[-1].close
            limit_price = current_price * 0.95  # 5% below market
            
            # Create limit order
            order = LimitOrder('BUY', quantity, limit_price)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            print(f"✅ Paper order placed: {symbol} BUY {quantity} @ ${limit_price:.2f}")
            print(f"Order ID: {trade.order.orderId}")
            
            # Wait a moment and cancel the order
            await asyncio.sleep(2)
            self.ib.cancelOrder(trade.order)
            print("✅ Order cancelled")
            
            return trade
            
        except Exception as e:
            print(f"Order placement error: {e}")
            return None
            
    async def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            print("Disconnected from IBKR")

async def run_quick_test():
    """Run quick integration test"""
    
    config = IBKRConfig()
    integration = QuickIBKRIntegration(config)
    
    print("🚀 Starting IBKR Quick Integration Test")
    print("=" * 50)
    
    # Test connection
    if await integration.connect():
        print("✅ Connection successful")
        
        # Test market data
        await integration.test_market_data('AAPL')
        
        # Test account info
        await integration.test_account_info()
        
        # Test paper order (only if paper trading)
        if config.paper_trading:
            await integration.test_paper_order('AAPL', 1)
        
        # Disconnect
        await integration.disconnect()
        
    else:
        print("❌ Connection failed")

if __name__ == "__main__":
    asyncio.run(run_quick_test())
```

## **🔧 TWS/IB Gateway Setup**

### **Option 1: TWS (Trader Workstation)**
1. Download TWS from IBKR website
2. Install and launch TWS
3. Log in with your credentials
4. Enable API connections in TWS settings
5. Configure API settings for your connection

### **Option 2: IB Gateway (Recommended for Production)**
1. Download IB Gateway from IBKR website
2. Install and configure IB Gateway
3. Set up automated login
4. Configure API settings
5. Test connection

### **API Settings Configuration**
```
File -> Global Configuration -> API -> Settings
- Enable Active X and Socket Clients: ✅
- Socket port: 7497 (paper) or 7496 (live)
- Allow connections from localhost: ✅
- Read-Only API: ❌ (for trading)
```

## **📊 Integration with Your Existing System**

### **1. Connect to Your Execution Engine**

```python
# core_structure/broker_integration/ibkr/ibkr_execution_bridge.py

from core_structure.execution_engine import ExecutionEngine, ExecutionRequest
from ib_insync import *

class IBKRExecutionBridge:
    """Bridge between your execution engine and IBKR"""
    
    def __init__(self, ib_client, config):
        self.ib = ib_client
        self.config = config
        
    async def execute_order(self, request: ExecutionRequest):
        """Execute order through IBKR"""
        
        # Convert your execution request to IBKR order
        contract = Stock(request.symbol, 'SMART', 'USD')
        
        if request.algorithm == 'MARKET':
            order = MarketOrder(request.side, request.quantity)
        elif request.algorithm == 'TWAP':
            order = self._create_twap_order(request)
        else:
            order = LimitOrder(request.side, request.quantity, request.limit_price)
            
        # Place order
        trade = self.ib.placeOrder(contract, order)
        
        return {
            'order_id': trade.order.orderId,
            'status': 'submitted',
            'symbol': request.symbol,
            'quantity': request.quantity,
            'side': request.side
        }
```

### **2. Connect to Your Portfolio Manager**

```python
# core_structure/broker_integration/ibkr/ibkr_portfolio_bridge.py

class IBKRPortfolioBridge:
    """Bridge between your portfolio manager and IBKR"""
    
    def __init__(self, ib_client):
        self.ib = ib_client
        
    async def get_positions(self):
        """Get current positions from IBKR"""
        positions = self.ib.positions()
        
        portfolio_positions = {}
        for pos in positions:
            portfolio_positions[pos.contract.symbol] = {
                'quantity': pos.position,
                'avg_cost': pos.avgCost,
                'market_value': pos.marketValue,
                'unrealized_pnl': pos.unrealizedPNL
            }
            
        return portfolio_positions
        
    async def get_account_summary(self):
        """Get account summary from IBKR"""
        account_values = self.ib.accountSummary()
        
        summary = {}
        for value in account_values:
            summary[value.tag] = float(value.value)
            
        return {
            'net_liquidation': summary.get('NetLiquidation', 0),
            'total_cash': summary.get('TotalCashValue', 0),
            'buying_power': summary.get('BuyingPower', 0),
            'available_funds': summary.get('AvailableFunds', 0)
        }
```

## **🚀 Next Steps After Quick Start**

### **Week 1: Foundation**
- [ ] Run connection test
- [ ] Verify market data access
- [ ] Test account information retrieval
- [ ] Validate paper trading orders

### **Week 2: Integration**
- [ ] Connect to your execution engine
- [ ] Integrate with portfolio manager
- [ ] Set up risk management
- [ ] Test end-to-end flow

### **Week 3: Production Readiness**
- [ ] Switch to live trading (if ready)
- [ ] Implement monitoring and alerting
- [ ] Set up error handling
- [ ] Performance optimization

## **⚠️ Important Notes**

1. **Start with Paper Trading**: Always test with paper trading first
2. **Risk Management**: Set appropriate position and order size limits
3. **Market Hours**: Be aware of market hours and trading sessions
4. **API Limits**: Respect IBKR's API rate limits
5. **Error Handling**: Implement robust error handling for production

## **📞 Support Resources**

- **IBKR API Documentation**: https://interactivebrokers.github.io/tws-api/
- **ib_insync Documentation**: https://ib_insync.readthedocs.io/
- **IBKR Support**: Contact IBKR support for account-specific issues

This quick start guide will get you connected to IBKR and ready to integrate with your existing trading system. Start with the connection test and gradually build up to full integration. 