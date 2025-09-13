#!/usr/bin/env python3
"""
IBKR Simple Connection Test
==========================

Simple test to verify IBKR connection and basic functionality.
This test focuses on core IBKR connection without advanced features.

Author: Professional Trading System Architecture
Version: 1.0.0 (Simple IBKR Test)
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core_structure.components.broker_integration import IBKRClient, IBKRConfig, BrokerConfig, Order, OrderSide, OrderType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IBKRSimpleTest:
    """Simple IBKR connection test"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.IBKRSimpleTest")
        self.ibkr_client = None
    
    async def run_simple_test(self):
        """Run simple IBKR connection test"""
        
        self.logger.info("🚀 Starting IBKR Simple Connection Test")
        self.logger.info("=" * 50)
        
        try:
            # Setup connection
            await self._setup_connection()
            
            # Test basic functionality
            await self._test_connection()
            await self._test_account_info()
            await self._test_market_data()
            
            self.logger.info("✅ IBKR Simple Test completed successfully!")
            
        except Exception as e:
            self.logger.error(f"❌ Test failed: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def _setup_connection(self):
        """Setup IBKR connection"""
        
        self.logger.info("📡 Setting up IBKR connection...")
        
        try:
            # Create IBKR configuration
            ibkr_config = IBKRConfig()
            ibkr_config.host = "127.0.0.1"
            ibkr_config.port = 4002  # Paper trading
            ibkr_config.client_id = 1
            ibkr_config.timeout = 30
            
            # Create broker configuration
            broker_config = BrokerConfig(
                broker_name="IBKR_Simple_Test",
                account_id="DU123456",  # Will be updated with real account
                paper_trading=True,
                enable_logging=True,
                connection_timeout=30,
                retry_attempts=3,
                retry_delay=1.0,
                host=ibkr_config.host,
                port=ibkr_config.port,
                client_id=ibkr_config.client_id
            )
            
            # Create IBKR client
            self.ibkr_client = IBKRClient(broker_config)
            
            # Test connection
            self.logger.info("🔌 Attempting to connect to IB Gateway...")
            connection_success = await self.ibkr_client.connect()
            
            if connection_success:
                self.logger.info("✅ Successfully connected to IB Gateway")
            else:
                raise ConnectionError("Failed to connect to IB Gateway")
                
        except Exception as e:
            self.logger.error(f"❌ Connection setup failed: {e}")
            self.logger.error("Please ensure:")
            self.logger.error("1. IB Gateway is running on localhost:4002")
            self.logger.error("2. Paper trading account is active")
            self.logger.error("3. API connections are enabled")
            raise
    
    async def _test_connection(self):
        """Test connection status"""
        
        self.logger.info("🔍 Testing connection status...")
        
        is_connected = await self.ibkr_client.is_connected()
        if is_connected:
            self.logger.info("✅ Connection is active")
        else:
            raise ConnectionError("Connection is not active")
    
    async def _test_account_info(self):
        """Test account information retrieval"""
        
        self.logger.info("📊 Testing account information...")
        
        try:
            # Get account summary
            account_summary = await self.ibkr_client.get_account_summary()
            self.logger.info(f"✅ Account Summary:")
            self.logger.info(f"   Equity: ${account_summary.equity:,.2f}")
            self.logger.info(f"   Buying Power: ${account_summary.buying_power:,.2f}")
            self.logger.info(f"   Cash: ${account_summary.cash:,.2f}")
            
            # Get positions
            positions = await self.ibkr_client.get_positions()
            self.logger.info(f"✅ Positions: {len(positions)} found")
            for symbol, position in positions.items():
                self.logger.info(f"   {symbol}: {position['quantity']} @ ${position['market_price']:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Account info test failed: {e}")
            raise
    
    async def _test_market_data(self):
        """Test market data retrieval"""
        
        self.logger.info("📈 Testing market data...")
        
        test_symbols = ["AAPL", "SPY"]
        
        for symbol in test_symbols:
            try:
                market_data = await self.ibkr_client.get_market_data(symbol)
                self.logger.info(f"✅ {symbol} Market Data:")
                self.logger.info(f"   Bid: ${market_data.bid:.2f}")
                self.logger.info(f"   Ask: ${market_data.ask:.2f}")
                self.logger.info(f"   Last: ${market_data.last:.2f}")
                self.logger.info(f"   Volume: {market_data.volume:,}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Market data failed for {symbol}: {e}")
    
    async def _cleanup(self):
        """Cleanup connection"""
        
        self.logger.info("🧹 Cleaning up...")
        
        if self.ibkr_client:
            try:
                await self.ibkr_client.disconnect()
                self.logger.info("✅ IBKR client disconnected")
            except Exception as e:
                self.logger.warning(f"⚠️ Disconnect failed: {e}")


async def run_simple_test():
    """Run the simple IBKR test"""
    
    test = IBKRSimpleTest()
    await test.run_simple_test()


if __name__ == "__main__":
    print("🚀 Starting IBKR Simple Connection Test")
    print("=" * 50)
    print("Prerequisites:")
    print("1. IB Gateway running on localhost:7497")
    print("2. Paper trading account active")
    print("3. API connections enabled")
    print("=" * 50)
    
    asyncio.run(run_simple_test())
