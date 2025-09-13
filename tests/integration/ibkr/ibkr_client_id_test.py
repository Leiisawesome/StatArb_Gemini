#!/usr/bin/env python3
"""
IBKR Client ID Test
==================

Test different client IDs to find one that works with IB Gateway.

Author: Professional Trading System Architecture
Version: 1.0.0 (Client ID Testing)
"""

import asyncio
import logging
from ib_insync import IB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_client_ids():
    """Test different client IDs to find one that works"""
    
    logger.info("🔍 Testing different client IDs for IB Gateway connection")
    logger.info("=" * 60)
    
    # Common client IDs to test
    client_ids_to_test = [1, 2, 3, 4, 5, 10, 99, 999]
    
    successful_client_ids = []
    
    for client_id in client_ids_to_test:
        logger.info(f"\n🧪 Testing client ID: {client_id}")
        
        ib = IB()
        try:
            # Try to connect with this client ID
            await ib.connectAsync('127.0.0.1', 4002, clientId=client_id)
            
            # If we get here, connection was successful
            logger.info(f"✅ Client ID {client_id}: Connection successful!")
            successful_client_ids.append(client_id)
            
            # Try to get some basic info to confirm API is working
            try:
                account_summary = ib.accountSummary()
                logger.info(f"✅ Client ID {client_id}: Account summary retrieved ({len(account_summary)} items)")
            except Exception as e:
                logger.warning(f"⚠️ Client ID {client_id}: Connection OK but account access failed: {e}")
            
            await ib.disconnectAsync()
            logger.info(f"✅ Client ID {client_id}: Disconnected cleanly")
            
        except Exception as e:
            logger.warning(f"❌ Client ID {client_id}: Failed - {e}")
    
    # Summary
    logger.info(f"\n📊 Client ID Test Results:")
    logger.info(f"Total client IDs tested: {len(client_ids_to_test)}")
    logger.info(f"Successful client IDs: {successful_client_ids}")
    
    if successful_client_ids:
        logger.info(f"✅ Recommended client ID: {successful_client_ids[0]}")
        logger.info(f"💡 Update your scripts to use client_id = {successful_client_ids[0]}")
    else:
        logger.error("❌ No working client IDs found!")
        logger.error("Please check:")
        logger.error("1. IB Gateway is running")
        logger.error("2. API connections are enabled")
        logger.error("3. Paper trading account is active")
        logger.error("4. No firewall blocking connections")
    
    return successful_client_ids


if __name__ == "__main__":
    print("🔍 IBKR Client ID Test")
    print("=" * 60)
    print("This will test different client IDs to find one that works")
    print("=" * 60)
    
    asyncio.run(test_client_ids())
