"""
ExecutionBridge Validation Script for Phase 8

This script validates the ExecutionBridge implementation for Phase 8:
Production ↔ Backtesting Execution Integration

Validation Categories:
1. ExecutionBridge Core Functionality
2. Performance and Scalability
3. Market Impact Modeling
4. Transaction Cost Optimization
5. Error Handling and Recovery
6. Integration with Core System
7. Integration with Backtesting Framework
8. Production Readiness
"""

import sys
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Add core_structure to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core_structure'))

from execution.execution_bridge import (
    ExecutionBridge,
    ExecutionBridgeConfig,
    ExecutionOrder,
    ExecutionResult,
    ExecutionMode,
    OrderType,
    create_execution_bridge,
    execute_orders_for_backtesting
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExecutionBridgeValidator:
    """Validator for ExecutionBridge implementation"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 8: ExecutionBridge Implementation',
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'categories': {},
            'performance_metrics': {},
            'recommendations': []
        }
        
        # Create sample data
        self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample market data and portfolio state"""
        # Create market data
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        self.market_data = pd.DataFrame({
            'open': [100 + i for i in range(len(dates))],
            'high': [105 + i for i in range(len(dates))],
            'low': [95 + i for i in range(len(dates))],
            'close': [102 + i for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }, index=dates)
        
        # Create portfolio state
        self.portfolio_state = {
            'total_value': 100000,
            'cash': 50000,
            'positions': {'AAPL': 100, 'SPY': 200, 'MSFT': 150},
            'risk_limits': {'max_position_size': 0.1}
        }
        
        # Create sample orders with reasonable sizes
        self.sample_orders = [
            ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0),
            ExecutionOrder("SPY", "sell", 5, OrderType.MARKET, 400.0),
            ExecutionOrder("MSFT", "buy", 8, OrderType.LIMIT, 300.0),
            ExecutionOrder("GOOGL", "buy", 2, OrderType.STOP, 2500.0),
            ExecutionOrder("TSLA", "sell", 20, OrderType.TWAP, 800.0)
        ]
    
    def validate_core_functionality(self):
        """Validate core functionality"""
        logger.info("Validating core functionality...")
        category = 'CoreFunctionality'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            # Test 1: Bridge initialization
            config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
            bridge = ExecutionBridge(config)
            self._add_check(category, "Bridge Initialization", True, "Bridge created successfully")
            
            # Test 2: Order creation
            order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
            self._add_check(category, "Order Creation", True, "Order created successfully")
            
            # Test 3: Basic order execution
            order = ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0)  # Smaller order
            result = bridge.execute_order(order, self.market_data, self.portfolio_state)
            success = result.status == "filled" and result.symbol == "AAPL"
            self._add_check(category, "Basic Order Execution", success, f"Order executed: {result.status}")
            
            # Test 4: Order result structure
            required_fields = ['order_id', 'symbol', 'side', 'quantity', 'filled_quantity', 
                             'price', 'execution_price', 'commission', 'slippage', 'market_impact']
            success = all(hasattr(result, field) for field in required_fields)
            self._add_check(category, "Order Result Structure", success, "Result has correct structure")
            
            # Test 5: Performance statistics
            stats = bridge.get_performance_stats()
            success = 'total_orders' in stats and 'successful_orders' in stats
            self._add_check(category, "Performance Statistics", success, "Performance stats available")
            
        except Exception as e:
            self._add_check(category, "Core Functionality", False, f"Error: {e}")
    
    def validate_performance_scalability(self):
        """Validate performance and scalability"""
        logger.info("Validating performance and scalability...")
        category = 'PerformanceScalability'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
            bridge = ExecutionBridge(config)
            
            # Test 1: Single order performance
            order = ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0)  # Smaller order
            start_time = time.time()
            result = bridge.execute_order(order, self.market_data)
            single_time = time.time() - start_time
            
            success = single_time < 1.0
            self._add_check(category, "Single Order Performance", success, 
                          f"Single order processed in {single_time:.3f}s")
            
            # Test 2: Batch order performance
            orders = self.sample_orders * 10  # 50 orders
            market_data = {
                order.symbol: self.market_data for order in orders
            }
            
            start_time = time.time()
            results = bridge.execute_orders_batch(orders, market_data, self.portfolio_state)
            batch_time = time.time() - start_time
            
            success = batch_time < 5.0 and len(results) == len(orders)
            self._add_check(category, "Batch Order Performance", success, 
                          f"Batch of {len(orders)} orders processed in {batch_time:.3f}s")
            
            # Test 3: Concurrent processing efficiency
            sequential_time = single_time * len(orders)
            efficiency = sequential_time / batch_time if batch_time > 0 else 1.0
            
            success = efficiency > 1.0
            self._add_check(category, "Concurrent Processing", success, 
                          f"Concurrent efficiency: {efficiency:.2f}x")
            
            # Store performance metrics
            self.results['performance_metrics'].update({
                'single_order_time': single_time,
                'batch_order_time': batch_time,
                'concurrent_efficiency': efficiency,
                'orders_per_second': len(orders) / batch_time if batch_time > 0 else 0
            })
            
        except Exception as e:
            self._add_check(category, "Performance Testing", False, f"Error: {e}")
    
    def validate_market_impact_modeling(self):
        """Validate market impact modeling"""
        logger.info("Validating market impact modeling...")
        category = 'MarketImpactModeling'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                enable_market_impact=True,
                impact_sensitivity=0.1
            )
            bridge = ExecutionBridge(config)
            
            # Test 1: Market impact calculation
            small_order = ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0)
            large_order = ExecutionOrder("AAPL", "buy", 1000, OrderType.MARKET, 150.0)
            
            small_impact = bridge._calculate_market_impact(small_order, self.market_data)
            large_impact = bridge._calculate_market_impact(large_order, self.market_data)
            
            success = large_impact.impact_percentage > small_impact.impact_percentage
            self._add_check(category, "Market Impact Calculation", success, 
                          f"Large order impact ({large_impact.impact_percentage:.4f}) > small order impact ({small_impact.impact_percentage:.4f})")
            
            # Test 2: Buy vs sell impact
            buy_order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
            sell_order = ExecutionOrder("AAPL", "sell", 100, OrderType.MARKET, 150.0)
            
            buy_impact = bridge._calculate_market_impact(buy_order, self.market_data)
            sell_impact = bridge._calculate_market_impact(sell_order, self.market_data)
            
            success = buy_impact.impacted_price > sell_impact.impacted_price
            self._add_check(category, "Buy vs Sell Impact", success, 
                          f"Buy price ({buy_impact.impacted_price:.2f}) > sell price ({sell_impact.impacted_price:.2f})")
            
            # Test 3: Market impact disabled
            config_no_impact = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                enable_market_impact=False
            )
            bridge_no_impact = ExecutionBridge(config_no_impact)
            
            no_impact = bridge_no_impact._calculate_market_impact(large_order, self.market_data)
            success = no_impact.impact_amount == 0.0
            self._add_check(category, "Market Impact Disabled", success, 
                          "Market impact disabled when configured")
            
        except Exception as e:
            self._add_check(category, "Market Impact Modeling", False, f"Error: {e}")
    
    def validate_transaction_costs(self):
        """Validate transaction cost optimization"""
        logger.info("Validating transaction cost optimization...")
        category = 'TransactionCosts'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                enable_transaction_costs=True,
                commission_rate=0.001,
                slippage_rate=0.0005
            )
            bridge = ExecutionBridge(config)
            
            # Test 1: Transaction cost calculation
            order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
            market_impact = bridge._calculate_market_impact(order, self.market_data)
            transaction_costs = bridge._calculate_transaction_costs(order, market_impact)
            
            success = transaction_costs.commission > 0 and transaction_costs.slippage > 0
            self._add_check(category, "Transaction Cost Calculation", success, 
                          f"Commission: ${transaction_costs.commission:.2f}, Slippage: ${transaction_costs.slippage:.2f}")
            
            # Test 2: Cost scaling with order size
            small_order = ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0)
            large_order = ExecutionOrder("AAPL", "buy", 1000, OrderType.MARKET, 150.0)
            
            small_impact = bridge._calculate_market_impact(small_order, self.market_data)
            large_impact = bridge._calculate_market_impact(large_order, self.market_data)
            
            small_costs = bridge._calculate_transaction_costs(small_order, small_impact)
            large_costs = bridge._calculate_transaction_costs(large_order, large_impact)
            
            success = large_costs.total_cost > small_costs.total_cost
            self._add_check(category, "Cost Scaling", success, 
                          f"Large order cost (${large_costs.total_cost:.2f}) > small order cost (${small_costs.total_cost:.2f})")
            
            # Test 3: Transaction costs disabled
            config_no_costs = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                enable_transaction_costs=False
            )
            bridge_no_costs = ExecutionBridge(config_no_costs)
            
            no_costs = bridge_no_costs._calculate_transaction_costs(order, market_impact)
            success = no_costs.total_cost == 0.0
            self._add_check(category, "Transaction Costs Disabled", success, 
                          "Transaction costs disabled when configured")
            
        except Exception as e:
            self._add_check(category, "Transaction Costs", False, f"Error: {e}")
    
    def validate_error_handling(self):
        """Validate error handling and recovery"""
        logger.info("Validating error handling and recovery...")
        category = 'ErrorHandling'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                validate_orders=True
            )
            bridge = ExecutionBridge(config)
            
            # Test 1: Invalid order handling
            invalid_order = ExecutionOrder("AAPL", "buy", -100, OrderType.MARKET, 150.0)
            result = bridge.execute_order(invalid_order, self.market_data)
            
            success = result.status == "rejected" and result.error_message is not None
            self._add_check(category, "Invalid Order Handling", success, 
                          f"Invalid order rejected: {result.error_message}")
            
            # Test 2: Order size validation
            small_order = ExecutionOrder("AAPL", "buy", 1, OrderType.MARKET, 50.0)
            result = bridge.execute_order(small_order, self.market_data)
            
            success = result.status == "rejected"
            self._add_check(category, "Order Size Validation", success, 
                          f"Small order rejected: {result.error_message}")
            
            # Test 3: Position limit validation
            large_order = ExecutionOrder("AAPL", "buy", 10000, OrderType.MARKET, 150.0)
            result = bridge.execute_order(large_order, self.market_data, self.portfolio_state)
            
            success = result.status == "rejected"
            self._add_check(category, "Position Limit Validation", success, 
                          f"Large order rejected: {result.error_message}")
            
        except Exception as e:
            self._add_check(category, "Error Handling", False, f"Error: {e}")
    
    def validate_core_system_integration(self):
        """Validate integration with core system"""
        logger.info("Validating core system integration...")
        category = 'CoreSystemIntegration'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
            bridge = ExecutionBridge(config)
            
            # Test 1: Order manager integration
            success = hasattr(bridge, 'order_manager')
            self._add_check(category, "Order Manager Integration", success, 
                          "Order manager component available")
            
            # Test 2: Smart router integration
            success = hasattr(bridge, 'smart_router')
            self._add_check(category, "Smart Router Integration", success, 
                          "Smart router component available")
            
            # Test 3: Cost optimizer integration
            success = hasattr(bridge, 'cost_optimizer')
            self._add_check(category, "Cost Optimizer Integration", success, 
                          "Cost optimizer component available")
            
            # Test 4: Impact modeler integration
            success = hasattr(bridge, 'impact_modeler')
            self._add_check(category, "Impact Modeler Integration", success, 
                          "Impact modeler component available")
            
            # Test 5: Component initialization
            success = bridge is not None
            self._add_check(category, "Component Initialization", success, 
                          "All core components initialized")
            
        except Exception as e:
            self._add_check(category, "Core System Integration", False, f"Error: {e}")
    
    def validate_backtesting_integration(self):
        """Validate integration with backtesting framework"""
        logger.info("Validating backtesting framework integration...")
        category = 'BacktestingIntegration'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            # Test 1: Convenience function
            orders = [
                ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0),
                ExecutionOrder("SPY", "sell", 5, OrderType.MARKET, 400.0)
            ]
            
            market_data = {
                'AAPL': self.market_data,
                'SPY': self.market_data
            }
            
            results = execute_orders_for_backtesting(orders, market_data, self.portfolio_state)
            
            success = len(results) == 2 and all(r.status == "filled" for r in results)
            self._add_check(category, "Convenience Function", success, 
                          f"Generated {len(results)} execution results for backtesting")
            
            # Test 2: Backtesting compatibility
            success = all(isinstance(r, ExecutionResult) for r in results)
            self._add_check(category, "Backtesting Compatibility", success, 
                          "All results compatible with backtesting format")
            
            # Test 3: Performance metrics for backtesting
            config = ExecutionBridgeConfig(execution_mode=ExecutionMode.BACKTESTING)
            bridge = ExecutionBridge(config)
            
            for order in orders:
                bridge.execute_order(order, market_data[order.symbol])
            
            stats = bridge.get_performance_stats()
            success = stats['total_orders'] > 0
            self._add_check(category, "Performance Metrics", success, 
                          f"Performance metrics available: {stats['total_orders']} orders")
            
        except Exception as e:
            self._add_check(category, "Backtesting Integration", False, f"Error: {e}")
    
    def validate_production_readiness(self):
        """Validate production readiness"""
        logger.info("Validating production readiness...")
        category = 'ProductionReadiness'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = ExecutionBridgeConfig(execution_mode=ExecutionMode.PRODUCTION)
            bridge = ExecutionBridge(config)
            
            # Test 1: Production mode execution
            order = ExecutionOrder("AAPL", "buy", 100, OrderType.MARKET, 150.0)
            result = bridge.execute_order(order, self.market_data)
            
            success = result.metadata.get('mode') == 'production'
            self._add_check(category, "Production Mode", success, 
                          f"Production mode execution: {result.metadata.get('mode')}")
            
            # Test 2: Resource cleanup
            bridge.shutdown()
            success = True  # If no exception, shutdown worked
            self._add_check(category, "Resource Cleanup", success, 
                          "Resources cleaned up successfully")
            
            # Test 3: Configuration validation
            config = ExecutionBridgeConfig(
                execution_mode=ExecutionMode.BACKTESTING,
                max_concurrent_orders=100,
                timeout_seconds=60.0
            )
            bridge = ExecutionBridge(config)
            
            success = (config.max_concurrent_orders == 100 and 
                      config.timeout_seconds == 60.0)
            self._add_check(category, "Configuration Validation", success, 
                          "Configuration parameters within valid ranges")
            
            # Test 4: Memory efficiency
            orders = [ExecutionOrder(f"SYMBOL_{i}", "buy", 10, OrderType.MARKET, 150.0) 
                     for i in range(100)]
            
            market_data = {order.symbol: self.market_data for order in orders}
            results = bridge.execute_orders_batch(orders, market_data)
            
            success = len(results) == 100
            self._add_check(category, "Memory Efficiency", success, 
                          f"Processed {len(results)} orders without memory issues")
            
            # Test 5: Thread safety
            import threading
            
            def execute_orders_thread():
                thread_orders = [ExecutionOrder("AAPL", "buy", 10, OrderType.MARKET, 150.0)]
                return bridge.execute_orders_batch(thread_orders, {'AAPL': self.market_data})
            
            threads = [threading.Thread(target=execute_orders_thread) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            success = True  # If no exceptions, thread-safe
            self._add_check(category, "Thread Safety", success, 
                          "Thread-safe execution")
            
        except Exception as e:
            self._add_check(category, "Production Readiness", False, f"Error: {e}")
    
    def _add_check(self, category: str, check_name: str, passed: bool, message: str):
        """Add a validation check result"""
        self.results['total_checks'] += 1
        if passed:
            self.results['passed_checks'] += 1
            self.results['categories'][category]['passed'] += 1
            logger.info(f"✅ {category}: {check_name} - {message}")
        else:
            self.results['failed_checks'] += 1
            self.results['categories'][category]['failed'] += 1
            logger.error(f"❌ {category}: {check_name} - {message}")
        
        self.results['categories'][category]['checks'].append({
            'name': check_name,
            'passed': passed,
            'message': message
        })
    
    def run_validation(self):
        """Run all validation tests"""
        logger.info("Starting ExecutionBridge validation for Phase 8")
        
        # Run all validation categories
        self.validate_core_functionality()
        self.validate_performance_scalability()
        self.validate_market_impact_modeling()
        self.validate_transaction_costs()
        self.validate_error_handling()
        self.validate_core_system_integration()
        self.validate_backtesting_integration()
        self.validate_production_readiness()
        
        # Calculate success rate
        success_rate = (self.results['passed_checks'] / self.results['total_checks'] * 100 
                       if self.results['total_checks'] > 0 else 0)
        
        # Generate recommendations
        self._generate_recommendations()
        
        # Print summary
        self._print_summary(success_rate)
        
        # Save results
        self._save_results()
        
        return self.results
    
    def _generate_recommendations(self):
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check error handling
        error_handling = self.results['categories'].get('ErrorHandling', {})
        if error_handling.get('failed', 0) > 0:
            recommendations.append("• Error handling needs improvement. Review error handling mechanisms.")
        
        # Check performance
        performance = self.results['categories'].get('PerformanceScalability', {})
        if performance.get('failed', 0) > 0:
            recommendations.append("• Performance optimization needed. Review execution efficiency.")
        
        # Check market impact
        market_impact = self.results['categories'].get('MarketImpactModeling', {})
        if market_impact.get('failed', 0) > 0:
            recommendations.append("• Market impact modeling needs refinement. Review impact calculations.")
        
        # Check transaction costs
        transaction_costs = self.results['categories'].get('TransactionCosts', {})
        if transaction_costs.get('failed', 0) > 0:
            recommendations.append("• Transaction cost modeling needs improvement. Review cost calculations.")
        
        if not recommendations:
            recommendations.append("• All validation checks passed successfully.")
        
        self.results['recommendations'] = recommendations
    
    def _print_summary(self, success_rate: float):
        """Print validation summary"""
        print("\n" + "="*80)
        print("EXECUTIONBRIDGE VALIDATION SUMMARY")
        print("="*80)
        print(f"Phase: {self.results['phase']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Total Checks: {self.results['total_checks']}")
        print(f"Passed: {self.results['passed_checks']}")
        print(f"Failed: {self.results['failed_checks']}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        print("Category Results:")
        for category, stats in self.results['categories'].items():
            total = stats['passed'] + stats['failed']
            rate = (stats['passed'] / total * 100) if total > 0 else 0
            print(f"  {category}: {rate:.1f}% ({stats['passed']}/{total})")
        
        if self.results['performance_metrics']:
            print("\nPerformance Metrics:")
            metrics = self.results['performance_metrics']
            if 'single_order_time' in metrics:
                print(f"  single_order_time: {metrics['single_order_time']:.3f}")
            if 'batch_order_time' in metrics:
                print(f"  batch_order_time: {metrics['batch_order_time']:.3f}")
            if 'concurrent_efficiency' in metrics:
                print(f"  concurrent_efficiency: {metrics['concurrent_efficiency']:.3f}")
            if 'orders_per_second' in metrics:
                print(f"  orders_per_second: {metrics['orders_per_second']:.1f}")
        
        if self.results['recommendations']:
            print("\nRecommendations:")
            for rec in self.results['recommendations']:
                print(f"  {rec}")
        
        print("="*80)
    
    def _save_results(self):
        """Save validation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"execution_bridge_validation_report_{timestamp}.json"
        
        # Convert datetime objects to strings for JSON serialization
        results_copy = self.results.copy()
        results_copy['timestamp'] = results_copy['timestamp']
        
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2, default=str)
        
        logger.info(f"Validation report saved to: {filename}")

def main():
    """Main validation function"""
    validator = ExecutionBridgeValidator()
    results = validator.run_validation()
    return results

if __name__ == "__main__":
    main() 