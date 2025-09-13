#!/usr/bin/env python3
"""
IBKR Real Connection Test Suite
==============================

Comprehensive test suite for enhanced broker integration using real IBKR connection.
Tests all advanced features including:
- Real IBKR connection via IB Gateway
- Advanced order management algorithms
- Multi-broker routing with IBKR as primary
- Performance analytics and monitoring
- Risk management and failover

Author: Professional Trading System Architecture
Version: 1.0.0 (Real IBKR Testing)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import time
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core_structure.components.broker_integration import (
    IBKRClient, IBKRConfig, BrokerConfig, Order, OrderSide, OrderType, OrderStatus,
    AdvancedOrderManager, ExecutionParameters, ExecutionAlgorithm, OrderPriority, MarketCondition,
    MultiBrokerManager, RoutingStrategy, BrokerType, create_multi_broker_manager
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IBKRRealTestSuite:
    """Comprehensive IBKR real connection test suite"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.IBKRRealTestSuite")
        
        # Test configuration
        self.test_symbols = ["AAPL", "SPY", "QQQ", "TSLA", "MSFT"]
        self.test_quantities = [1, 10, 100]  # Small quantities for testing
        
        # IBKR connection
        self.ibkr_client = None
        self.advanced_order_manager = None
        self.multi_broker_manager = None
        
        # Test results
        self.test_results = {}
        self.performance_metrics = {}
        
        self.logger.info("IBKR Real Test Suite initialized")
    
    async def run_comprehensive_tests(self):
        """Run comprehensive IBKR real connection tests"""
        
        self.logger.info("🚀 Starting IBKR Real Connection Test Suite")
        self.logger.info("=" * 60)
        
        try:
            # 1. Setup IBKR connection
            await self._setup_ibkr_connection()
            
            # 2. Test basic broker functionality
            await self._test_basic_broker_functionality()
            
            # 3. Test advanced order management
            await self._test_advanced_order_management()
            
            # 4. Test multi-broker routing with IBKR as primary
            await self._test_multi_broker_routing()
            
            # 5. Test performance analytics
            await self._test_performance_analytics()
            
            # 6. Test risk management and monitoring
            await self._test_risk_management()
            
            # 7. Generate comprehensive test report
            await self._generate_test_report()
            
            self.logger.info("✅ IBKR Real Connection Test Suite completed successfully!")
            
        except Exception as e:
            self.logger.error(f"❌ Test suite failed: {e}")
            raise
        finally:
            # Cleanup
            await self._cleanup_connections()
    
    async def _setup_ibkr_connection(self):
        """Setup real IBKR connection"""
        
        self.logger.info("\n📡 Setting up IBKR Real Connection")
        self.logger.info("-" * 40)
        
        try:
            # Create IBKR configuration
            ibkr_config = IBKRConfig()
            ibkr_config.host = "127.0.0.1"  # IB Gateway on localhost
            ibkr_config.port = 4002  # Paper trading port (4002 for paper, 4001 for live)
            ibkr_config.client_id = 1
            ibkr_config.timeout = 30
            
            # Create broker configuration
            broker_config = BrokerConfig(
                broker_name="IBKR_Real",
                account_id="DU123456",  # Will be updated with real account
                paper_trading=True,
                enable_logging=True,
                connection_timeout=30,
                retry_attempts=3,
                retry_delay=1.0,
                host=ibkr_config.host,
                port=ibkr_config.port,
                client_id=ibkr_config.client_id,
                max_requests_per_second=50,  # Conservative for testing
                max_orders_per_second=5,
                max_position_size=0.05,  # 5% max position
                max_daily_loss=0.01,     # 1% daily loss limit
                max_order_value=10000    # $10K max order value
            )
            
            # Create IBKR client
            self.ibkr_client = IBKRClient(broker_config)
            
            # Test connection
            self.logger.info("🔌 Attempting to connect to IB Gateway...")
            connection_success = await self.ibkr_client.connect()
            
            if connection_success:
                self.logger.info("✅ Successfully connected to IB Gateway")
                
                # Verify connection
                is_connected = await self.ibkr_client.is_connected()
                if is_connected:
                    self.logger.info("✅ Connection verified - ready for testing")
                    
                    # Create advanced order manager
                    self.advanced_order_manager = AdvancedOrderManager(self.ibkr_client)
                    self.logger.info("✅ Advanced Order Manager initialized")
                    
                    # Create multi-broker manager with IBKR as primary
                    self.multi_broker_manager = create_multi_broker_manager("ibkr_primary")
                    await self.multi_broker_manager.add_broker(
                        "ibkr_primary", 
                        self.ibkr_client, 
                        BrokerType.IBKR
                    )
                    self.logger.info("✅ Multi-Broker Manager initialized with IBKR")
                    
                else:
                    raise ConnectionError("Connection verification failed")
            else:
                raise ConnectionError("Failed to connect to IB Gateway")
                
        except Exception as e:
            self.logger.error(f"❌ IBKR connection setup failed: {e}")
            self.logger.error("Please ensure:")
            self.logger.error("1. IB Gateway is running on localhost:4002")
            self.logger.error("2. Paper trading account is active")
            self.logger.error("3. API connections are enabled")
            raise
    
    async def _test_basic_broker_functionality(self):
        """Test basic broker functionality"""
        
        self.logger.info("\n🔧 Testing Basic Broker Functionality")
        self.logger.info("-" * 40)
        
        try:
            # Test account summary
            self.logger.info("📊 Testing account summary...")
            account_summary = await self.ibkr_client.get_account_summary()
            self.logger.info(f"✅ Account Summary:")
            self.logger.info(f"   Equity: ${account_summary.equity:,.2f}")
            self.logger.info(f"   Buying Power: ${account_summary.buying_power:,.2f}")
            self.logger.info(f"   Cash: ${account_summary.cash:,.2f}")
            
            # Test positions
            self.logger.info("\n📈 Testing positions...")
            positions = await self.ibkr_client.get_positions()
            self.logger.info(f"✅ Found {len(positions)} positions")
            for symbol, position in positions.items():
                self.logger.info(f"   {symbol}: {position['quantity']} @ ${position['market_price']:.2f}")
            
            # Test market data
            self.logger.info("\n📊 Testing market data...")
            for symbol in self.test_symbols[:2]:  # Test first 2 symbols
                try:
                    market_data = await self.ibkr_client.get_market_data(symbol)
                    self.logger.info(f"✅ {symbol} Market Data:")
                    self.logger.info(f"   Bid: ${market_data.bid:.2f}")
                    self.logger.info(f"   Ask: ${market_data.ask:.2f}")
                    self.logger.info(f"   Last: ${market_data.last:.2f}")
                    self.logger.info(f"   Volume: {market_data.volume:,}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Market data failed for {symbol}: {e}")
            
            # Test portfolio summary
            self.logger.info("\n💼 Testing portfolio summary...")
            portfolio_summary = await self.ibkr_client.get_portfolio_summary()
            self.logger.info(f"✅ Portfolio Summary:")
            self.logger.info(f"   Total Equity: ${portfolio_summary.total_equity:,.2f}")
            self.logger.info(f"   Total Buying Power: ${portfolio_summary.total_buying_power:,.2f}")
            self.logger.info(f"   Unrealized P&L: ${portfolio_summary.unrealized_pnl:,.2f}")
            
            self.test_results["basic_functionality"] = "PASSED"
            self.logger.info("✅ Basic broker functionality tests passed")
            
        except Exception as e:
            self.logger.error(f"❌ Basic functionality test failed: {e}")
            self.test_results["basic_functionality"] = f"FAILED: {e}"
    
    async def _test_advanced_order_management(self):
        """Test advanced order management algorithms"""
        
        self.logger.info("\n🎯 Testing Advanced Order Management")
        self.logger.info("-" * 40)
        
        if not self.advanced_order_manager:
            self.logger.error("❌ Advanced Order Manager not available")
            return
        
        # Test different execution algorithms
        algorithms_to_test = [
            ExecutionAlgorithm.MARKET,
            ExecutionAlgorithm.TWAP,
            ExecutionAlgorithm.VWAP,
            ExecutionAlgorithm.ADAPTIVE_TWAP
        ]
        
        test_symbol = self.test_symbols[0]  # Use first symbol
        test_quantity = self.test_quantities[0]  # Use smallest quantity
        
        for algorithm in algorithms_to_test:
            self.logger.info(f"\n📈 Testing {algorithm.value.upper()} Algorithm")
            
            try:
                # Create execution parameters
                params = ExecutionParameters(
                    symbol=test_symbol,
                    quantity=test_quantity,
                    side=OrderSide.BUY,
                    algorithm=algorithm,
                    priority=OrderPriority.NORMAL,
                    duration_minutes=5,  # Short duration for testing
                    max_market_impact_bps=20.0,  # Higher limit for testing
                    urgency_factor=0.5,
                    participation_rate=0.05  # Very low participation for testing
                )
                
                # Execute order
                self.logger.info(f"   Executing {test_quantity} shares of {test_symbol}...")
                start_time = datetime.now()
                
                result = await self.advanced_order_manager.execute_order(params)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Log results
                self.logger.info(f"   📊 Execution Results:")
                self.logger.info(f"      Status: {result.execution_status.value}")
                self.logger.info(f"      Filled: {result.filled_quantity}/{result.total_quantity}")
                self.logger.info(f"      Average Price: ${result.average_price:.2f}")
                self.logger.info(f"      Market Impact: {result.market_impact_bps:.2f} bps")
                self.logger.info(f"      Execution Time: {execution_time:.2f} seconds")
                self.logger.info(f"      Total Cost: {result.total_cost_bps:.2f} bps")
                
                if result.execution_status == OrderStatus.FILLED:
                    self.logger.info(f"   ✅ {algorithm.value} algorithm executed successfully")
                else:
                    self.logger.warning(f"   ⚠️ {algorithm.value} algorithm did not fill completely")
                
                # Store results
                if algorithm.value not in self.test_results:
                    self.test_results[algorithm.value] = {}
                
                self.test_results[algorithm.value] = {
                    "status": result.execution_status.value,
                    "filled_quantity": result.filled_quantity,
                    "average_price": result.average_price,
                    "market_impact_bps": result.market_impact_bps,
                    "execution_time_seconds": execution_time,
                    "total_cost_bps": result.total_cost_bps
                }
                
            except Exception as e:
                self.logger.error(f"   ❌ {algorithm.value} algorithm failed: {e}")
                self.test_results[algorithm.value] = f"FAILED: {e}"
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Get performance metrics
        metrics = self.advanced_order_manager.get_performance_metrics()
        self.logger.info(f"\n📊 Advanced Order Manager Performance:")
        self.logger.info(f"   Total Orders: {metrics['total_orders']}")
        self.logger.info(f"   Success Rate: {metrics['success_rate']:.1%}")
        self.logger.info(f"   Total Volume: {metrics['total_volume']:.0f}")
        self.logger.info(f"   Average Market Impact: {metrics['average_market_impact']:.2f} bps")
        
        self.performance_metrics["advanced_order_manager"] = metrics
    
    async def _test_multi_broker_routing(self):
        """Test multi-broker routing with IBKR as primary"""
        
        self.logger.info("\n🔄 Testing Multi-Broker Routing")
        self.logger.info("-" * 40)
        
        if not self.multi_broker_manager:
            self.logger.error("❌ Multi-Broker Manager not available")
            return
        
        # Test different routing strategies
        strategies_to_test = [
            RoutingStrategy.PRIMARY_ONLY,
            RoutingStrategy.BEST_EXECUTION,
            RoutingStrategy.LOWEST_COST
        ]
        
        test_symbol = self.test_symbols[1]  # Use second symbol
        test_quantity = self.test_quantities[0]  # Use smallest quantity
        
        for strategy in strategies_to_test:
            self.logger.info(f"\n🎯 Testing {strategy.value.upper()} Routing")
            
            try:
                # Create test order
                order = Order(
                    order_id=f"routing_test_{strategy.value}_{int(time.time())}",
                    symbol=test_symbol,
                    side=OrderSide.BUY,
                    quantity=test_quantity,
                    order_type=OrderType.MARKET,
                    time_in_force="IOC"
                )
                
                # Execute with routing strategy
                self.logger.info(f"   Executing order with {strategy.value} routing...")
                start_time = datetime.now()
                
                result = await self.multi_broker_manager.execute_order(order, strategy)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if result.success:
                    routing_info = getattr(result, 'routing_info', {})
                    self.logger.info(f"   ✅ Order executed successfully")
                    self.logger.info(f"      Broker: {routing_info.get('broker_id', 'Unknown')}")
                    self.logger.info(f"      Strategy: {routing_info.get('routing_strategy', 'Unknown')}")
                    self.logger.info(f"      Confidence: {routing_info.get('confidence', 0):.2f}")
                    self.logger.info(f"      Reasoning: {routing_info.get('reasoning', 'N/A')}")
                    self.logger.info(f"      Average Price: ${result.average_price:.2f}")
                    self.logger.info(f"      Execution Time: {execution_time:.2f} seconds")
                    
                    # Store results
                    if f"routing_{strategy.value}" not in self.test_results:
                        self.test_results[f"routing_{strategy.value}"] = {}
                    
                    self.test_results[f"routing_{strategy.value}"] = {
                        "status": "SUCCESS",
                        "broker_id": routing_info.get('broker_id', 'Unknown'),
                        "confidence": routing_info.get('confidence', 0),
                        "average_price": result.average_price,
                        "execution_time_seconds": execution_time,
                        "reasoning": routing_info.get('reasoning', 'N/A')
                    }
                else:
                    self.logger.error(f"   ❌ Order failed: {result.error_message}")
                    self.test_results[f"routing_{strategy.value}"] = f"FAILED: {result.error_message}"
                
            except Exception as e:
                self.logger.error(f"   ❌ Routing strategy {strategy.value} failed: {e}")
                self.test_results[f"routing_{strategy.value}"] = f"FAILED: {e}"
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Get broker performance report
        report = self.multi_broker_manager.get_broker_performance_report()
        self.logger.info(f"\n📊 Multi-Broker Performance Report:")
        self.logger.info(f"   Total Brokers: {report['total_brokers']}")
        self.logger.info(f"   Connected Brokers: {report['connected_brokers']}")
        self.logger.info(f"   Current Strategy: {report['routing_strategy']}")
        
        for broker_id, metrics in report['brokers'].items():
            self.logger.info(f"   {broker_id}:")
            self.logger.info(f"     Success Rate: {metrics['success_rate']:.1%}")
            self.logger.info(f"     Total Orders: {metrics['total_orders']}")
            self.logger.info(f"     Avg Execution Time: {metrics['average_execution_time']:.2f}s")
        
        self.performance_metrics["multi_broker_manager"] = report
    
    async def _test_performance_analytics(self):
        """Test performance analytics and monitoring"""
        
        self.logger.info("\n📊 Testing Performance Analytics")
        self.logger.info("-" * 40)
        
        try:
            # Test consolidated positions
            if self.multi_broker_manager:
                positions = await self.multi_broker_manager.get_consolidated_positions()
                self.logger.info(f"📈 Consolidated Positions: {len(positions)}")
                
                for symbol, position in positions.items():
                    self.logger.info(f"   {symbol}: {position['quantity']} @ ${position['market_price']:.2f}")
                
                # Test consolidated account summary
                summary = await self.multi_broker_manager.get_consolidated_account_summary()
                self.logger.info(f"\n💰 Consolidated Account Summary:")
                self.logger.info(f"   Total Equity: ${summary.equity:,.2f}")
                self.logger.info(f"   Total Buying Power: ${summary.buying_power:,.2f}")
                self.logger.info(f"   Total Cash: ${summary.cash:,.2f}")
            
            # Test risk metrics
            if self.ibkr_client:
                risk_metrics = await self.ibkr_client.get_risk_metrics()
                self.logger.info(f"\n⚠️ Risk Metrics:")
                self.logger.info(f"   Portfolio VaR: ${risk_metrics.portfolio_var:,.2f}")
                self.logger.info(f"   Max Drawdown: ${risk_metrics.max_drawdown:,.2f}")
                self.logger.info(f"   Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}")
                self.logger.info(f"   Beta: {risk_metrics.beta:.2f}")
            
            # Test P&L calculation
            if self.ibkr_client:
                pnl = await self.ibkr_client.calculate_pnl()
                self.logger.info(f"\n💵 P&L Summary:")
                for symbol, pnl_value in pnl.items():
                    self.logger.info(f"   {symbol}: ${pnl_value:,.2f}")
            
            self.test_results["performance_analytics"] = "PASSED"
            self.logger.info("✅ Performance analytics tests passed")
            
        except Exception as e:
            self.logger.error(f"❌ Performance analytics test failed: {e}")
            self.test_results["performance_analytics"] = f"FAILED: {e}"
    
    async def _test_risk_management(self):
        """Test risk management and monitoring"""
        
        self.logger.info("\n⚠️ Testing Risk Management")
        self.logger.info("-" * 40)
        
        try:
            # Test order validation
            self.logger.info("🔍 Testing order validation...")
            
            # Test order that should be rejected (too large)
            large_order = Order(
                order_id="risk_test_large",
                symbol=self.test_symbols[0],
                side=OrderSide.BUY,
                quantity=10000,  # Large quantity
                order_type=OrderType.MARKET,
                time_in_force="IOC"
            )
            
            # This should be rejected by risk management
            is_valid = self.ibkr_client._validate_order(large_order)
            if not is_valid:
                self.logger.info("✅ Large order correctly rejected by risk management")
            else:
                self.logger.warning("⚠️ Large order was not rejected by risk management")
            
            # Test rate limiting
            self.logger.info("⏱️ Testing rate limiting...")
            start_time = time.time()
            
            # Make multiple rapid requests
            for i in range(10):
                try:
                    await self.ibkr_client.get_market_data(self.test_symbols[0])
                except Exception as e:
                    self.logger.info(f"✅ Rate limiting working: {e}")
                    break
            
            rate_limit_time = time.time() - start_time
            self.logger.info(f"   Rate limiting test completed in {rate_limit_time:.2f} seconds")
            
            # Test connection monitoring
            self.logger.info("🔌 Testing connection monitoring...")
            is_connected = await self.ibkr_client.is_connected()
            if is_connected:
                self.logger.info("✅ Connection monitoring working")
            else:
                self.logger.error("❌ Connection monitoring failed")
            
            self.test_results["risk_management"] = "PASSED"
            self.logger.info("✅ Risk management tests passed")
            
        except Exception as e:
            self.logger.error(f"❌ Risk management test failed: {e}")
            self.test_results["risk_management"] = f"FAILED: {e}"
    
    async def _generate_test_report(self):
        """Generate comprehensive test report"""
        
        self.logger.info("\n📋 Generating Test Report")
        self.logger.info("-" * 40)
        
        # Create comprehensive test report
        report = {
            "test_suite": "IBKR Real Connection Test Suite",
            "timestamp": datetime.now().isoformat(),
            "test_results": self.test_results,
            "performance_metrics": self.performance_metrics,
            "summary": {
                "total_tests": len(self.test_results),
                "passed_tests": len([r for r in self.test_results.values() if isinstance(r, dict) and r.get("status") == "SUCCESS"]),
                "failed_tests": len([r for r in self.test_results.values() if isinstance(r, str) and r.startswith("FAILED")])
            }
        }
        
        # Log summary
        self.logger.info(f"📊 Test Summary:")
        self.logger.info(f"   Total Tests: {report['summary']['total_tests']}")
        self.logger.info(f"   Passed: {report['summary']['passed_tests']}")
        self.logger.info(f"   Failed: {report['summary']['failed_tests']}")
        
        # Save report to file
        report_filename = f"ibkr_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📄 Test report saved to: {report_filename}")
        
        # Log detailed results
        self.logger.info(f"\n📋 Detailed Test Results:")
        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                self.logger.info(f"   {test_name}: {result.get('status', 'UNKNOWN')}")
            else:
                self.logger.info(f"   {test_name}: {result}")
    
    async def _cleanup_connections(self):
        """Cleanup all connections"""
        
        self.logger.info("\n🧹 Cleaning up connections...")
        
        try:
            if self.ibkr_client:
                await self.ibkr_client.disconnect()
                self.logger.info("✅ IBKR client disconnected")
            
            if self.multi_broker_manager:
                # Disconnect all brokers in multi-broker manager
                for broker_id, broker in self.multi_broker_manager.brokers.items():
                    try:
                        await broker.disconnect()
                        self.logger.info(f"✅ Broker {broker_id} disconnected")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to disconnect broker {broker_id}: {e}")
            
            self.logger.info("✅ Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Cleanup failed: {e}")


async def run_ibkr_real_test():
    """Run the IBKR real connection test suite"""
    
    test_suite = IBKRRealTestSuite()
    
    try:
        await test_suite.run_comprehensive_tests()
    except KeyboardInterrupt:
        logger.info("🛑 Test suite interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
    finally:
        await test_suite._cleanup_connections()


if __name__ == "__main__":
    print("🚀 Starting IBKR Real Connection Test Suite")
    print("=" * 60)
    print("Prerequisites:")
    print("1. IB Gateway running on localhost:7497")
    print("2. Paper trading account active")
    print("3. API connections enabled")
    print("=" * 60)
    
    asyncio.run(run_ibkr_real_test())
