#!/usr/bin/env python3
"""
IBKR API Connection Test
========================

Simple test to verify IBKR API connection with proper error handling.
Tests the actual API handshake and basic functionality.

Author: Professional Trading System Architecture
Version: 1.0.0 (API Test)
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ibkr_api_connection():
    """Test IBKR API connection with detailed error reporting"""
    
    logger.info("🔌 Testing IBKR API Connection")
    logger.info("=" * 40)
    
    try:
        from ib_insync import IB, Stock
        
        # Create IB instance
        ib = IB()
        
        logger.info("📡 Attempting to connect to IB Gateway...")
        logger.info("   Host: 127.0.0.1")
        logger.info("   Port: 4002 (Paper Trading)")
        logger.info("   Client ID: 1")
        
        # Attempt connection with timeout
        try:
            await ib.connectAsync('127.0.0.1', 4002, clientId=1, timeout=10)
            logger.info("✅ Successfully connected to IB Gateway!")
            
            # Test basic functionality
            logger.info("🔍 Testing basic API functionality...")
            
            # Get account summary
            account_summary = ib.accountSummary()
            logger.info(f"✅ Account Summary: {len(account_summary)} items")
            
            # Get positions
            positions = ib.positions()
            logger.info(f"✅ Positions: {len(positions)} found")
            
            # Test market data (if available)
            try:
                contract = Stock('AAPL', 'SMART', 'USD')
                ib.qualifyContracts(contract)
                ticker = ib.reqMktData(contract)
                
                # Wait a moment for data
                await asyncio.sleep(2)
                
                if ticker.bid:
                    logger.info(f"✅ Market Data: AAPL Bid=${ticker.bid}, Ask=${ticker.ask}")
                else:
                    logger.info("⚠️ Market data not available (may be outside trading hours)")
                
                ib.cancelMktData(contract)
                
            except Exception as e:
                logger.warning(f"⚠️ Market data test failed: {e}")
            
            # Disconnect
            await ib.disconnectAsync()
            logger.info("✅ Successfully disconnected from IB Gateway")
            
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ Connection timeout - API handshake failed")
            logger.error("   This usually means:")
            logger.error("   1. API connections not enabled in IB Gateway")
            logger.error("   2. Client ID 1 not authorized")
            logger.error("   3. IB Gateway not fully initialized")
            return False
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            logger.error("   Check IB Gateway settings and API permissions")
            return False
            
    except ImportError as e:
        logger.error(f"❌ ib_insync not available: {e}")
        return False


async def main():
    """Main test function"""
    
    print("🚀 IBKR API Connection Test")
    print("=" * 40)
    print("Testing direct API connection to IB Gateway")
    print("=" * 40)
    
    success = await test_ibkr_api_connection()
    
    if success:
        print("\n🎉 API connection test PASSED!")
        print("Your IBKR integration is ready for testing.")
    else:
        print("\n❌ API connection test FAILED!")
        print("Please check:")
        print("1. IB Gateway is running and logged in")
        print("2. API connections are enabled (Configure → Settings → API → Settings)")
        print("3. Client ID 1 is authorized")
        print("4. Paper trading account is active")


if __name__ == "__main__":
    asyncio.run(main())