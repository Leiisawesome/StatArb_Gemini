#!/usr/bin/env python3
"""
IBKR Connection Diagnostics
==========================

Diagnostic tool to help troubleshoot IBKR connection issues.
Provides comprehensive connection testing and diagnostics.

Author: Professional Trading System Architecture
Version: 1.0.0 (IBKR Diagnostics)
"""

import asyncio
import logging
import socket
import time
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IBKRConnectionDiagnostics:
    """IBKR connection diagnostics tool"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.IBKRConnectionDiagnostics")
        self.host = "127.0.0.1"
        self.ports = [4002, 4001]  # Paper trading and live trading ports
        self.timeout = 5
    
    async def run_diagnostics(self):
        """Run comprehensive connection diagnostics"""
        
        self.logger.info("🔍 Starting IBKR Connection Diagnostics")
        self.logger.info("=" * 50)
        
        try:
            # 1. Test network connectivity
            await self._test_network_connectivity()
            
            # 2. Test IB Gateway availability
            await self._test_ib_gateway_availability()
            
            # 3. Test ib_insync availability
            await self._test_ib_insync_availability()
            
            # 4. Test basic IBKR client creation
            await self._test_ibkr_client_creation()
            
            # 5. Provide recommendations
            await self._provide_recommendations()
            
            self.logger.info("✅ Diagnostics completed")
            
        except Exception as e:
            self.logger.error(f"❌ Diagnostics failed: {e}")
    
    async def _test_network_connectivity(self):
        """Test basic network connectivity"""
        
        self.logger.info("\n🌐 Testing Network Connectivity")
        self.logger.info("-" * 30)
        
        for port in self.ports:
            try:
                self.logger.info(f"Testing connection to {self.host}:{port}...")
                
                # Test socket connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                
                start_time = time.time()
                result = sock.connect_ex((self.host, port))
                connection_time = time.time() - start_time
                
                sock.close()
                
                if result == 0:
                    self.logger.info(f"✅ Port {port} is accessible (connection time: {connection_time:.3f}s)")
                else:
                    self.logger.warning(f"⚠️ Port {port} is not accessible (error code: {result})")
                
            except Exception as e:
                self.logger.error(f"❌ Port {port} test failed: {e}")
    
    async def _test_ib_gateway_availability(self):
        """Test IB Gateway availability"""
        
        self.logger.info("\n🏦 Testing IB Gateway Availability")
        self.logger.info("-" * 30)
        
        try:
            # Test if IB Gateway is responding
            self.logger.info("Testing IB Gateway response...")
            
            for port in self.ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(self.timeout)
                    
                    result = sock.connect_ex((self.host, port))
                    
                    if result == 0:
                        self.logger.info(f"✅ IB Gateway appears to be running on port {port}")
                        
                        # Try to read some data to confirm it's IB Gateway
                        try:
                            sock.send(b"")
                            response = sock.recv(1024)
                            if response:
                                self.logger.info(f"✅ IB Gateway responded on port {port}")
                            else:
                                self.logger.warning(f"⚠️ No response from IB Gateway on port {port}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Could not communicate with IB Gateway on port {port}: {e}")
                    
                    sock.close()
                    
                except Exception as e:
                    self.logger.error(f"❌ IB Gateway test failed for port {port}: {e}")
        
        except Exception as e:
            self.logger.error(f"❌ IB Gateway availability test failed: {e}")
    
    async def _test_ib_insync_availability(self):
        """Test ib_insync library availability"""
        
        self.logger.info("\n📚 Testing ib_insync Library Availability")
        self.logger.info("-" * 30)
        
        try:
            import ib_insync
            self.logger.info(f"✅ ib_insync is available (version: {ib_insync.__version__})")
            
            # Test basic ib_insync functionality
            try:
                from ib_insync import IB, Stock
                self.logger.info("✅ ib_insync core classes imported successfully")
                
                # Test creating IB instance
                ib = IB()
                self.logger.info("✅ IB instance created successfully")
                
                # Test creating Stock contract
                stock = Stock('AAPL', 'SMART', 'USD')
                self.logger.info("✅ Stock contract created successfully")
                
            except Exception as e:
                self.logger.error(f"❌ ib_insync functionality test failed: {e}")
            
        except ImportError as e:
            self.logger.error(f"❌ ib_insync not available: {e}")
            self.logger.error("Install with: pip install ib_insync")
        except Exception as e:
            self.logger.error(f"❌ ib_insync test failed: {e}")
    
    async def _test_ibkr_client_creation(self):
        """Test IBKR client creation"""
        
        self.logger.info("\n🔧 Testing IBKR Client Creation")
        self.logger.info("-" * 30)
        
        try:
            from core_structure.components.broker_integration import IBKRClient, IBKRConfig, BrokerConfig
            
            # Create configuration
            ibkr_config = IBKRConfig()
            ibkr_config.host = self.host
            ibkr_config.port = 7497
            ibkr_config.client_id = 1
            ibkr_config.timeout = 30
            
            broker_config = BrokerConfig(
                broker_name="IBKR_Diagnostics",
                account_id="DU123456",
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
            ibkr_client = IBKRClient(broker_config)
            self.logger.info("✅ IBKR client created successfully")
            
            # Test connection (without actually connecting)
            self.logger.info("✅ IBKR client configuration is valid")
            
        except ImportError as e:
            self.logger.error(f"❌ IBKR client import failed: {e}")
        except Exception as e:
            self.logger.error(f"❌ IBKR client creation failed: {e}")
    
    async def _provide_recommendations(self):
        """Provide recommendations based on diagnostics"""
        
        self.logger.info("\n💡 Recommendations")
        self.logger.info("-" * 30)
        
        self.logger.info("Based on the diagnostics, here are the recommendations:")
        self.logger.info("")
        
        self.logger.info("1. IB Gateway Setup:")
        self.logger.info("   - Ensure IB Gateway is running")
        self.logger.info("   - Check that API connections are enabled")
        self.logger.info("   - Verify the correct port (4002 for paper, 4001 for live)")
        self.logger.info("")
        
        self.logger.info("2. Network Configuration:")
        self.logger.info("   - Ensure localhost (127.0.0.1) is accessible")
        self.logger.info("   - Check firewall settings")
        self.logger.info("   - Verify no other applications are using the ports")
        self.logger.info("")
        
        self.logger.info("3. Account Configuration:")
        self.logger.info("   - Ensure paper trading account is active")
        self.logger.info("   - Check API permissions in IB Gateway")
        self.logger.info("   - Verify client ID is unique (not used by other applications)")
        self.logger.info("")
        
        self.logger.info("4. Library Dependencies:")
        self.logger.info("   - Ensure ib_insync is installed: pip install ib_insync")
        self.logger.info("   - Check Python version compatibility")
        self.logger.info("   - Verify all required dependencies are available")
        self.logger.info("")
        
        self.logger.info("5. Testing Steps:")
        self.logger.info("   - Start with simple connection test")
        self.logger.info("   - Test basic market data retrieval")
        self.logger.info("   - Gradually test more advanced features")
        self.logger.info("")


async def run_diagnostics():
    """Run IBKR connection diagnostics"""
    
    diagnostics = IBKRConnectionDiagnostics()
    await diagnostics.run_diagnostics()


if __name__ == "__main__":
    print("🔍 IBKR Connection Diagnostics")
    print("=" * 50)
    print("This tool will help diagnose IBKR connection issues.")
    print("=" * 50)
    
    asyncio.run(run_diagnostics())
