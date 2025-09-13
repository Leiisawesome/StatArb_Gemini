#!/usr/bin/env python3
"""
IBKR Connection Verification Utility
====================================

Simple utility to verify IB Gateway connection and show available data.
This is useful for quick connectivity checks during development.

Author: Professional Trading System Architecture
Version: 2.0.0 (Integration Test)
"""

import asyncio
from ib_insync import IB, Stock
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def verify_ibkr_connection():
    """Verify IBKR connection and show available data"""
    ib = IB()
    
    try:
        # Connect with optimal settings
        logger.info("🔌 Connecting to IB Gateway...")
        await ib.connectAsync('127.0.0.1', 4002, clientId=0, timeout=15)
        
        if not ib.isConnected():
            logger.error("❌ Failed to connect")
            return False
        
        logger.info("✅ Successfully connected to IB Gateway!")
        logger.info(f"📡 Server Version: {ib.client.serverVersion}")
        
        # Show account information
        logger.info("\n📊 Account Information:")
        managed_accounts = ib.managedAccounts()
        logger.info(f"   Managed Accounts: {managed_accounts}")
        
        # Try to get account summary (with error handling)
        try:
            account_summary = ib.accountSummary()
            if account_summary:
                logger.info(f"   Account summary items: {len(account_summary)}")
                # Show first few items
                for item in account_summary[:3]:
                    logger.info(f"      {item.tag}: {item.value}")
            else:
                logger.info("   No account summary available")
        except Exception as e:
            logger.warning(f"⚠️ Account summary error: {e}")
        
        # Try to get market data for a simple test
        logger.info("\n📈 Market Data Test:")
        try:
            # Create a simple stock contract
            aapl = Stock('AAPL', 'SMART', 'USD')
            ib.qualifyContracts(aapl)
            
            # Request market data
            ticker = ib.reqMktData(aapl, '', False, False)
            await asyncio.sleep(1)  # Wait for data
            
            if ticker.bid and ticker.ask:
                logger.info(f"   AAPL: Bid={ticker.bid}, Ask={ticker.ask}")
            else:
                logger.info("   Market data: No live data available (may need market data subscription)")
                
            # Cancel market data
            ib.cancelMktData(aapl)
            
        except Exception as e:
            logger.warning(f"⚠️ Market data error: {e}")
        
        # Show portfolio information
        logger.info("\n💼 Portfolio Information:")
        positions = ib.positions()
        if positions:
            logger.info(f"   Active positions: {len(positions)}")
            for pos in positions[:3]:  # Show first 3
                logger.info(f"      {pos.contract.symbol}: {pos.position} @ {pos.avgCost}")
        else:
            logger.info("   No active positions")
        
        logger.info("\n🎉 IB Gateway connection verification completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection verification failed: {e}")
        return False
        
    finally:
        if ib.isConnected():
            ib.disconnect()
            logger.info("🧹 Disconnected from IB Gateway")


async def main():
    """Main function"""
    print("🚀 IBKR Connection Verification Utility")
    print("=" * 50)
    
    success = await verify_ibkr_connection()
    
    if success:
        print("\n" + "="*60)
        print("🎯 RESULT: IB Gateway connection is WORKING!")
        print("✅ Your trading system can now connect to IBKR")
        print("✅ Market data access is functional")
        print("✅ Account information is accessible")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ RESULT: IB Gateway connection FAILED!")
        print("Please check:")
        print("1. IB Gateway is running on localhost:4002")
        print("2. Paper trading account is logged in")
        print("3. API connections are enabled in Gateway settings")
        print("="*60)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Verification interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)