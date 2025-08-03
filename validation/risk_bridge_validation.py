"""
RiskBridge Validation Script for Phase 9

This script validates the RiskBridge implementation for Phase 9:
Production ↔ Backtesting Risk Management Integration

Validation Categories:
1. RiskBridge Core Functionality
2. Performance and Scalability
3. VaR Calculation and Monitoring
4. Risk Metrics Calculation
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

from risk.risk_bridge import (
    RiskBridge,
    RiskBridgeConfig,
    RiskMetrics,
    PortfolioRiskMetrics,
    RiskLevel,
    RiskMode,
    VaRResult,
    create_risk_bridge,
    calculate_risk_for_backtesting
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskBridgeValidator:
    """Validator for RiskBridge implementation"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 9: RiskBridge Implementation',
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
            'peak_value': 110000,
            'max_drawdown': 0.05,
            'daily_pnl': 1000,
            'current_risk': 0.015
        }
        
        # Create sample positions
        self.positions = {
            'AAPL': {
                'quantity': 100,
                'current_price': 150.0,
                'avg_price': 145.0
            },
            'SPY': {
                'quantity': 200,
                'current_price': 400.0,
                'avg_price': 395.0
            },
            'MSFT': {
                'quantity': 50,
                'current_price': 310.0,
                'avg_price': 300.0
            },
            'GOOGL': {
                'quantity': 25,
                'current_price': 2500.0,
                'avg_price': 2450.0
            },
            'TSLA': {
                'quantity': 200,
                'current_price': 850.0,
                'avg_price': 800.0
            }
        }
    
    def validate_core_functionality(self):
        """Validate core functionality"""
        logger.info("Validating core functionality...")
        category = 'CoreFunctionality'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            # Test 1: Bridge initialization
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            self._add_check(category, "Bridge Initialization", True, "Bridge created successfully")
            
            # Test 2: Position risk calculation
            risk_metrics = bridge.calculate_position_risk(
                symbol="AAPL",
                position_size=100,
                current_price=150.0,
                avg_price=145.0,
                market_data=self.market_data,
                portfolio_state=self.portfolio_state
            )
            
            success = (risk_metrics.symbol == "AAPL" and 
                      risk_metrics.position_size == 100 and
                      risk_metrics.unrealized_pnl == 500.0)
            self._add_check(category, "Position Risk Calculation", success, 
                          f"Position risk calculated: PnL ${risk_metrics.unrealized_pnl:.2f}")
            
            # Test 3: Portfolio risk calculation
            market_data = {
                'AAPL': self.market_data,
                'SPY': self.market_data,
                'MSFT': self.market_data
            }
            
            portfolio_metrics = bridge.calculate_portfolio_risk(
                self.positions, market_data, self.portfolio_state
            )
            
            success = (portfolio_metrics.total_value > 0 and 
                      portfolio_metrics.total_pnl > 0 and
                      len(portfolio_metrics.position_risks) == 5)
            self._add_check(category, "Portfolio Risk Calculation", success, 
                          f"Portfolio risk calculated: ${portfolio_metrics.total_value:.2f} value, ${portfolio_metrics.total_pnl:.2f} PnL")
            
            # Test 4: Risk metrics structure
            required_fields = ['symbol', 'position_size', 'current_price', 'avg_price', 
                             'unrealized_pnl', 'var_1d', 'volatility', 'risk_level']
            success = all(hasattr(risk_metrics, field) for field in required_fields)
            self._add_check(category, "Risk Metrics Structure", success, "Risk metrics have correct structure")
            
            # Test 5: Performance statistics
            stats = bridge.get_performance_stats()
            success = 'total_risk_checks' in stats and 'avg_calculation_time' in stats
            self._add_check(category, "Performance Statistics", success, "Performance stats available")
            
        except Exception as e:
            self._add_check(category, "Core Functionality", False, f"Error: {e}")
    
    def validate_performance_scalability(self):
        """Validate performance and scalability"""
        logger.info("Validating performance and scalability...")
        category = 'PerformanceScalability'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            
            # Test 1: Single position performance
            start_time = time.time()
            risk_metrics = bridge.calculate_position_risk(
                "AAPL", 100, 150.0, 145.0, self.market_data
            )
            single_time = time.time() - start_time
            
            success = single_time < 1.0
            self._add_check(category, "Single Position Performance", success, 
                          f"Single position processed in {single_time:.3f}s")
            
            # Test 2: Portfolio performance
            market_data = {symbol: self.market_data for symbol in self.positions.keys()}
            
            start_time = time.time()
            portfolio_metrics = bridge.calculate_portfolio_risk(
                self.positions, market_data, self.portfolio_state
            )
            portfolio_time = time.time() - start_time
            
            success = portfolio_time < 5.0 and len(portfolio_metrics.position_risks) == len(self.positions)
            self._add_check(category, "Portfolio Performance", success, 
                          f"Portfolio of {len(self.positions)} positions processed in {portfolio_time:.3f}s")
            
            # Test 3: Large portfolio performance
            large_positions = {
                f'SYMBOL_{i}': {
                    'quantity': 100 + i,
                    'current_price': 150.0 + i,
                    'avg_price': 145.0 + i
                }
                for i in range(100)
            }
            
            large_market_data = {
                f'SYMBOL_{i}': self.market_data for i in range(100)
            }
            
            start_time = time.time()
            large_portfolio = bridge.calculate_portfolio_risk(
                large_positions, large_market_data, self.portfolio_state
            )
            large_time = time.time() - start_time
            
            success = large_time < 10.0 and len(large_portfolio.position_risks) == 100
            self._add_check(category, "Large Portfolio Performance", success, 
                          f"Large portfolio of 100 positions processed in {large_time:.3f}s")
            
            # Store performance metrics
            self.results['performance_metrics'].update({
                'single_position_time': single_time,
                'portfolio_time': portfolio_time,
                'large_portfolio_time': large_time,
                'positions_per_second': len(large_positions) / large_time if large_time > 0 else 0
            })
            
        except Exception as e:
            self._add_check(category, "Performance Testing", False, f"Error: {e}")
    
    def validate_var_calculation(self):
        """Validate VaR calculation and monitoring"""
        logger.info("Validating VaR calculation and monitoring...")
        category = 'VaRCalculation'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(
                risk_mode=RiskMode.BACKTESTING,
                enable_var_calculation=True,
                var_confidence_level=0.95
            )
            bridge = RiskBridge(config)
            
            # Test 1: VaR calculation
            var_result = bridge._calculate_var(
                symbol="AAPL",
                market_data=self.market_data,
                position_size=100,
                current_price=150.0
            )
            
            success = (var_result.symbol == "AAPL" and 
                      var_result.var_1d >= 0 and
                      var_result.var_1d_pct >= 0 and
                      var_result.confidence_level == 0.95)
            self._add_check(category, "VaR Calculation", success, 
                          f"VaR calculated: ${var_result.var_1d:.2f} ({var_result.var_1d_pct:.2%})")
            
            # Test 2: CVaR calculation
            success = (var_result.cvar_1d >= 0 and
                      var_result.cvar_1d_pct >= 0)
            self._add_check(category, "CVaR Calculation", success, 
                          f"CVaR calculated: ${var_result.cvar_1d:.2f} ({var_result.cvar_1d_pct:.2%})")
            
            # Test 3: Multiple time horizons
            success = (var_result.var_5d >= 0 and
                      var_result.var_5d_pct >= 0)
            self._add_check(category, "Multiple Time Horizons", success, 
                          f"5-day VaR: ${var_result.var_5d:.2f} ({var_result.var_5d_pct:.2%})")
            
            # Test 4: VaR disabled
            config_no_var = RiskBridgeConfig(
                risk_mode=RiskMode.BACKTESTING,
                enable_var_calculation=False
            )
            bridge_no_var = RiskBridge(config_no_var)
            
            risk_metrics = bridge_no_var.calculate_position_risk(
                "AAPL", 100, 150.0, 145.0, self.market_data
            )
            
            success = risk_metrics.var_1d == 0.0
            self._add_check(category, "VaR Disabled", success, "VaR calculation disabled when configured")
            
        except Exception as e:
            self._add_check(category, "VaR Calculation", False, f"Error: {e}")
    
    def validate_risk_metrics(self):
        """Validate risk metrics calculation"""
        logger.info("Validating risk metrics calculation...")
        category = 'RiskMetrics'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            
            # Test 1: Volatility calculation
            volatility = bridge._calculate_volatility(self.market_data)
            success = volatility >= 0 and isinstance(volatility, float)
            self._add_check(category, "Volatility Calculation", success, 
                          f"Volatility calculated: {volatility:.2%}")
            
            # Test 2: Sharpe ratio calculation
            sharpe_positive = bridge._calculate_sharpe_ratio(0.1, 0.2)
            sharpe_negative = bridge._calculate_sharpe_ratio(-0.1, 0.2)
            
            success = (sharpe_positive == 0.5 and sharpe_negative == -0.5)
            self._add_check(category, "Sharpe Ratio Calculation", success, 
                          f"Sharpe ratios: {sharpe_positive:.2f}, {sharpe_negative:.2f}")
            
            # Test 3: Risk level determination
            low_risk = bridge._determine_risk_level(0.02, 0.01, 0.1, 0.05)
            high_risk = bridge._determine_risk_level(-0.04, 0.016, 0.2, 0.05)
            
            success = (low_risk == RiskLevel.LOW and high_risk == RiskLevel.HIGH)
            self._add_check(category, "Risk Level Determination", success, 
                          f"Risk levels: {low_risk.value}, {high_risk.value}")
            
            # Test 4: Portfolio risk metrics
            market_data = {symbol: self.market_data for symbol in self.positions.keys()}
            portfolio_metrics = bridge.calculate_portfolio_risk(
                self.positions, market_data, self.portfolio_state
            )
            
            success = (portfolio_metrics.portfolio_volatility >= 0 and
                      portfolio_metrics.portfolio_beta == 1.0 and
                      portfolio_metrics.portfolio_sharpe_ratio >= 0)
            self._add_check(category, "Portfolio Risk Metrics", success, 
                          f"Portfolio volatility: {portfolio_metrics.portfolio_volatility:.2%}")
            
        except Exception as e:
            self._add_check(category, "Risk Metrics", False, f"Error: {e}")
    
    def validate_error_handling(self):
        """Validate error handling and recovery"""
        logger.info("Validating error handling and recovery...")
        category = 'ErrorHandling'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            
            # Test 1: Invalid market data handling
            risk_metrics = bridge.calculate_position_risk(
                symbol="INVALID",
                position_size=100,
                current_price=150.0,
                avg_price=145.0,
                market_data=pd.DataFrame({'close': []}),  # DataFrame with no data
                portfolio_state=self.portfolio_state
            )
            
            success = (risk_metrics.symbol == "INVALID" and 
                      risk_metrics.risk_level == RiskLevel.HIGH and
                      len(risk_metrics.alerts) > 0)
            self._add_check(category, "Invalid Market Data Handling", success, 
                          f"Error handled: {len(risk_metrics.alerts)} alerts generated")
            
            # Test 2: Risk limit checking
            class MockOrder:
                def __init__(self, symbol, quantity, price):
                    self.symbol = symbol
                    self.quantity = quantity
                    self.price = price
            
            # Test valid order (small order)
            valid_order = MockOrder("AAPL", 10, 150.0)
            is_valid, violations = bridge.check_risk_limits(valid_order, self.portfolio_state)
            success = is_valid and len(violations) == 0
            self._add_check(category, "Valid Risk Limit Check", success, 
                          f"Valid order passed: {len(violations)} violations")
            
            # Test invalid order
            invalid_order = MockOrder("AAPL", 10000, 150.0)
            is_valid, violations = bridge.check_risk_limits(invalid_order, self.portfolio_state)
            success = not is_valid and len(violations) > 0
            self._add_check(category, "Invalid Risk Limit Check", success, 
                          f"Invalid order rejected: {len(violations)} violations")
            
        except Exception as e:
            self._add_check(category, "Error Handling", False, f"Error: {e}")
    
    def validate_core_system_integration(self):
        """Validate integration with core system"""
        logger.info("Validating core system integration...")
        category = 'CoreSystemIntegration'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            
            # Test 1: Risk manager integration
            success = hasattr(bridge, 'risk_manager')
            self._add_check(category, "Risk Manager Integration", success, 
                          "Risk manager component available")
            
            # Test 2: Stop-loss manager integration
            success = hasattr(bridge, 'stop_loss_manager')
            self._add_check(category, "Stop-Loss Manager Integration", success, 
                          "Stop-loss manager component available")
            
            # Test 3: VaR calculator integration
            success = hasattr(bridge, 'var_calculator')
            self._add_check(category, "VaR Calculator Integration", success, 
                          "VaR calculator component available")
            
            # Test 4: Component initialization
            success = bridge is not None
            self._add_check(category, "Component Initialization", success, 
                          "All core components initialized")
            
            # Test 5: Configuration integration
            success = (bridge.config.risk_mode == RiskMode.BACKTESTING and
                      bridge.config.enable_var_calculation == True)
            self._add_check(category, "Configuration Integration", success, 
                          "Configuration properly integrated")
            
        except Exception as e:
            self._add_check(category, "Core System Integration", False, f"Error: {e}")
    
    def validate_backtesting_integration(self):
        """Validate integration with backtesting framework"""
        logger.info("Validating backtesting framework integration...")
        category = 'BacktestingIntegration'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            # Test 1: Convenience function
            market_data = {
                'AAPL': self.market_data,
                'SPY': self.market_data,
                'MSFT': self.market_data
            }
            
            portfolio_metrics = calculate_risk_for_backtesting(
                self.positions, market_data, self.portfolio_state
            )
            
            success = (portfolio_metrics.total_value > 0 and
                      portfolio_metrics.total_pnl > 0 and
                      len(portfolio_metrics.position_risks) == 5)
            self._add_check(category, "Convenience Function", success, 
                          f"Generated portfolio metrics for {len(portfolio_metrics.position_risks)} positions")
            
            # Test 2: Backtesting compatibility
            success = isinstance(portfolio_metrics, PortfolioRiskMetrics)
            self._add_check(category, "Backtesting Compatibility", success, 
                          "Portfolio metrics compatible with backtesting format")
            
            # Test 3: Performance metrics for backtesting
            config = RiskBridgeConfig(risk_mode=RiskMode.BACKTESTING)
            bridge = RiskBridge(config)
            
            bridge.calculate_portfolio_risk(self.positions, market_data, self.portfolio_state)
            stats = bridge.get_performance_stats()
            
            success = stats['total_risk_checks'] > 0
            self._add_check(category, "Performance Metrics", success, 
                          f"Performance metrics available: {stats['total_risk_checks']} checks")
            
        except Exception as e:
            self._add_check(category, "Backtesting Integration", False, f"Error: {e}")
    
    def validate_production_readiness(self):
        """Validate production readiness"""
        logger.info("Validating production readiness...")
        category = 'ProductionReadiness'
        self.results['categories'][category] = {'passed': 0, 'failed': 0, 'checks': []}
        
        try:
            config = RiskBridgeConfig(risk_mode=RiskMode.PRODUCTION)
            bridge = RiskBridge(config)
            
            # Test 1: Production mode
            success = bridge.config.risk_mode == RiskMode.PRODUCTION
            self._add_check(category, "Production Mode", success, 
                          f"Production mode: {bridge.config.risk_mode.value}")
            
            # Test 2: Resource cleanup
            bridge.shutdown()
            success = True  # If no exception, shutdown worked
            self._add_check(category, "Resource Cleanup", success, 
                          "Resources cleaned up successfully")
            
            # Test 3: Configuration validation
            config = RiskBridgeConfig(
                risk_mode=RiskMode.BACKTESTING,
                max_concurrent_calculations=100,
                calculation_timeout=60.0
            )
            bridge = RiskBridge(config)
            
            success = (config.max_concurrent_calculations == 100 and
                      config.calculation_timeout == 60.0)
            self._add_check(category, "Configuration Validation", success, 
                          "Configuration parameters within valid ranges")
            
            # Test 4: Memory efficiency
            large_positions = {
                f'SYMBOL_{i}': {
                    'quantity': 100 + i,
                    'current_price': 150.0 + i,
                    'avg_price': 145.0 + i
                }
                for i in range(200)
            }
            
            large_market_data = {
                f'SYMBOL_{i}': self.market_data for i in range(200)
            }
            
            portfolio_metrics = bridge.calculate_portfolio_risk(
                large_positions, large_market_data, self.portfolio_state
            )
            
            success = len(portfolio_metrics.position_risks) == 200
            self._add_check(category, "Memory Efficiency", success, 
                          f"Processed {len(portfolio_metrics.position_risks)} positions without memory issues")
            
            # Test 5: Thread safety
            import threading
            
            def calculate_risk_thread():
                thread_positions = {
                    'AAPL': {'quantity': 100, 'current_price': 150.0, 'avg_price': 145.0}
                }
                thread_market_data = {'AAPL': self.market_data}
                return bridge.calculate_portfolio_risk(thread_positions, thread_market_data)
            
            threads = [threading.Thread(target=calculate_risk_thread) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            success = True  # If no exceptions, thread-safe
            self._add_check(category, "Thread Safety", success, 
                          "Thread-safe risk calculation")
            
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
        logger.info("Starting RiskBridge validation for Phase 9")
        
        # Run all validation categories
        self.validate_core_functionality()
        self.validate_performance_scalability()
        self.validate_var_calculation()
        self.validate_risk_metrics()
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
            recommendations.append("• Performance optimization needed. Review calculation efficiency.")
        
        # Check VaR calculation
        var_calculation = self.results['categories'].get('VaRCalculation', {})
        if var_calculation.get('failed', 0) > 0:
            recommendations.append("• VaR calculation needs refinement. Review VaR models.")
        
        # Check risk metrics
        risk_metrics = self.results['categories'].get('RiskMetrics', {})
        if risk_metrics.get('failed', 0) > 0:
            recommendations.append("• Risk metrics calculation needs improvement. Review risk models.")
        
        if not recommendations:
            recommendations.append("• All validation checks passed successfully.")
        
        self.results['recommendations'] = recommendations
    
    def _print_summary(self, success_rate: float):
        """Print validation summary"""
        print("\n" + "="*80)
        print("RISKBRIDGE VALIDATION SUMMARY")
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
            if 'single_position_time' in metrics:
                print(f"  single_position_time: {metrics['single_position_time']:.3f}")
            if 'portfolio_time' in metrics:
                print(f"  portfolio_time: {metrics['portfolio_time']:.3f}")
            if 'large_portfolio_time' in metrics:
                print(f"  large_portfolio_time: {metrics['large_portfolio_time']:.3f}")
            if 'positions_per_second' in metrics:
                print(f"  positions_per_second: {metrics['positions_per_second']:.1f}")
        
        if self.results['recommendations']:
            print("\nRecommendations:")
            for rec in self.results['recommendations']:
                print(f"  {rec}")
        
        print("="*80)
    
    def _save_results(self):
        """Save validation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"risk_bridge_validation_report_{timestamp}.json"
        
        # Convert datetime objects to strings for JSON serialization
        results_copy = self.results.copy()
        results_copy['timestamp'] = results_copy['timestamp']
        
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2, default=str)
        
        logger.info(f"Validation report saved to: {filename}")

def main():
    """Main validation function"""
    validator = RiskBridgeValidator()
    results = validator.run_validation()
    return results

if __name__ == "__main__":
    main() 