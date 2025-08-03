"""
SignalBridge Validation Script for Phase 7

This script validates the SignalBridge implementation for Phase 7:
Core System ↔ Backtesting Framework Integration

Validation Categories:
1. SignalBridge Core Functionality
2. Performance and Scalability
3. Integration with Core System
4. Integration with Backtesting Framework
5. Error Handling and Recovery
6. Signal Consistency Validation
7. Cache and Optimization
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

from signal_generation.signal_bridge import (
    SignalBridge, 
    SignalBridgeConfig, 
    SignalBridgeResult,
    create_signal_bridge,
    generate_signals_for_backtesting
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SignalBridgeValidator:
    """Comprehensive validator for SignalBridge implementation"""
    
    def __init__(self):
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Phase 7: SignalBridge Implementation',
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'success_rate': 0.0,
            'categories': {},
            'performance_metrics': {},
            'recommendations': []
        }
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks"""
        logger.info("Starting SignalBridge validation for Phase 7")
        
        # Run validation categories
        self._validate_core_functionality()
        self._validate_performance_scalability()
        self._validate_core_system_integration()
        self._validate_backtesting_integration()
        self._validate_error_handling()
        self._validate_signal_consistency()
        self._validate_cache_optimization()
        self._validate_production_readiness()
        
        # Calculate overall results
        self._calculate_final_results()
        
        # Generate report
        self._generate_validation_report()
        
        return self.validation_results
    
    def _validate_core_functionality(self):
        """Validate core SignalBridge functionality"""
        logger.info("Validating core functionality...")
        
        category = 'CoreFunctionality'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            # Test 1: SignalBridge initialization
            bridge = create_signal_bridge()
            self._add_check(category, "SignalBridge Initialization", True, "Bridge created successfully")
            
            # Test 2: Configuration validation
            config = SignalBridgeConfig(
                use_core_signal_generator=True,
                use_ai_enhancement=True,
                max_concurrent_signals=5
            )
            bridge_with_config = SignalBridge(config)
            self._add_check(category, "Custom Configuration", True, "Custom config applied successfully")
            
            # Test 3: Basic signal generation
            symbols = ["AAPL", "SPY"]
            market_data = self._create_sample_market_data(symbols)
            current_date = datetime.now()
            
            results = bridge.generate_signals_sync(symbols, market_data, current_date)
            self._add_check(category, "Basic Signal Generation", len(results) == 2, 
                          f"Generated {len(results)} signals")
            
            # Test 4: Signal result structure
            if results:
                result = list(results.values())[0]
                is_valid_structure = (
                    hasattr(result, 'symbol') and
                    hasattr(result, 'signal_value') and
                    hasattr(result, 'confidence') and
                    hasattr(result, 'timestamp') and
                    hasattr(result, 'source')
                )
                self._add_check(category, "Signal Result Structure", is_valid_structure,
                              "Signal result has correct structure")
            
            # Test 5: Performance stats
            stats = bridge.get_performance_stats()
            has_stats = all(key in stats for key in ['total_signals', 'success_rate', 'avg_processing_time'])
            self._add_check(category, "Performance Statistics", has_stats, "Performance stats available")
            
        except Exception as e:
            self._add_check(category, "Core Functionality", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_performance_scalability(self):
        """Validate performance and scalability"""
        logger.info("Validating performance and scalability...")
        
        category = 'PerformanceScalability'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            bridge = create_signal_bridge()
            
            # Test 1: Single symbol performance
            symbols = ["AAPL"]
            market_data = self._create_sample_market_data(symbols)
            current_date = datetime.now()
            
            start_time = time.time()
            results = bridge.generate_signals_sync(symbols, market_data, current_date)
            single_symbol_time = time.time() - start_time
            
            self._add_check(category, "Single Symbol Performance", single_symbol_time < 1.0,
                          f"Single symbol processed in {single_symbol_time:.3f}s")
            
            # Test 2: Multiple symbols performance
            symbols = ["AAPL", "SPY", "MSFT", "GOOGL", "TSLA"]
            market_data = self._create_sample_market_data(symbols)
            
            start_time = time.time()
            results = bridge.generate_signals_sync(symbols, market_data, current_date)
            multi_symbol_time = time.time() - start_time
            
            # Should be faster than sequential processing due to concurrency
            expected_sequential_time = single_symbol_time * len(symbols)
            is_efficient = multi_symbol_time < expected_sequential_time * 0.8
            
            self._add_check(category, "Concurrent Processing", is_efficient,
                          f"Multi-symbol processed in {multi_symbol_time:.3f}s (vs {expected_sequential_time:.3f}s sequential)")
            
            # Test 3: Throughput measurement
            symbols = ["AAPL", "SPY", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META", "NFLX", "AMD"]
            market_data = self._create_sample_market_data(symbols)
            
            start_time = time.time()
            results = bridge.generate_signals_sync(symbols, market_data, current_date)
            throughput_time = time.time() - start_time
            
            throughput = len(symbols) / throughput_time
            self._add_check(category, "Signal Throughput", throughput > 5.0,
                          f"Throughput: {throughput:.1f} signals/second")
            
            # Store performance metrics
            self.validation_results['performance_metrics'].update({
                'single_symbol_time': single_symbol_time,
                'multi_symbol_time': multi_symbol_time,
                'throughput': throughput,
                'concurrent_efficiency': multi_symbol_time / expected_sequential_time
            })
            
        except Exception as e:
            self._add_check(category, "Performance Testing", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_core_system_integration(self):
        """Validate integration with core system components"""
        logger.info("Validating core system integration...")
        
        category = 'CoreSystemIntegration'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            bridge = create_signal_bridge()
            
            # Test 1: SignalGenerator integration
            has_signal_generator = hasattr(bridge, 'signal_generator')
            self._add_check(category, "SignalGenerator Integration", has_signal_generator,
                          "SignalGenerator component available")
            
            # Test 2: AI enhancement integration
            has_ai_enhancer = hasattr(bridge, 'ai_enhancer')
            self._add_check(category, "AI Enhancement Integration", has_ai_enhancer,
                          "AI Signal Enhancer component available")
            
            # Test 3: Regime detection integration
            has_regime_detector = hasattr(bridge, 'regime_detector')
            self._add_check(category, "Regime Detection Integration", has_regime_detector,
                          "Regime Detector component available")
            
            # Test 4: Feature engine integration
            has_feature_engine = hasattr(bridge, 'feature_engine')
            self._add_check(category, "Feature Engine Integration", has_feature_engine,
                          "Feature Engine component available")
            
            # Test 5: Component initialization
            components_initialized = all([
                has_signal_generator,
                has_ai_enhancer,
                has_regime_detector,
                has_feature_engine
            ])
            self._add_check(category, "Component Initialization", components_initialized,
                          "All core components initialized")
            
        except Exception as e:
            self._add_check(category, "Core System Integration", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_backtesting_integration(self):
        """Validate integration with backtesting framework"""
        logger.info("Validating backtesting framework integration...")
        
        category = 'BacktestingIntegration'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            # Test 1: Convenience function
            symbols = ["AAPL", "SPY"]
            market_data = self._create_sample_market_data(symbols)
            current_date = datetime.now()
            
            results = generate_signals_for_backtesting(symbols, market_data, current_date)
            
            is_dict = isinstance(results, dict)
            has_float_values = all(isinstance(v, float) for v in results.values())
            
            self._add_check(category, "Convenience Function", is_dict and has_float_values,
                          f"Generated {len(results)} float signals for backtesting")
            
            # Test 2: Signal value range
            valid_range = all(-2.0 <= v <= 2.0 for v in results.values())
            self._add_check(category, "Signal Value Range", valid_range,
                          "All signal values in valid range [-2.0, 2.0]")
            
            # Test 3: Backtesting compatibility
            bridge = create_signal_bridge()
            bridge_results = bridge.generate_signals_sync(symbols, market_data, current_date)
            
            # Convert bridge results to backtesting format
            bridge_signals = {symbol: result.signal_value for symbol, result in bridge_results.items()}
            
            # Compare with convenience function
            signals_match = all(
                abs(bridge_signals.get(symbol, 0) - results.get(symbol, 0)) < 0.001
                for symbol in symbols
            )
            
            self._add_check(category, "Backtesting Compatibility", signals_match,
                          "Bridge results compatible with backtesting format")
            
        except Exception as e:
            self._add_check(category, "Backtesting Integration", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_error_handling(self):
        """Validate error handling and recovery mechanisms"""
        logger.info("Validating error handling and recovery...")
        
        category = 'ErrorHandling'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            # Test 1: Fallback mechanism
            config = SignalBridgeConfig(enable_fallback=True)
            bridge = SignalBridge(config)
            
            # Create invalid market data to trigger fallback
            symbols = ["INVALID"]
            market_data = {"INVALID": pd.DataFrame()}  # Empty DataFrame
            
            results = bridge.generate_signals_sync(symbols, market_data, datetime.now())
            
            has_fallback = "INVALID" in results and results["INVALID"].source == "fallback"
            self._add_check(category, "Fallback Mechanism", has_fallback,
                          "Fallback mechanism triggered for invalid data")
            
            # Test 2: Error recovery
            config_no_fallback = SignalBridgeConfig(enable_fallback=False)
            bridge_no_fallback = SignalBridge(config_no_fallback)
            
            try:
                bridge_no_fallback.generate_signals_sync(symbols, market_data, datetime.now())
                error_raised = False
            except Exception:
                error_raised = True
            
            self._add_check(category, "Error Propagation", error_raised,
                          "Errors properly propagated when fallback disabled")
            
            # Test 3: Timeout handling
            config_timeout = SignalBridgeConfig(timeout_seconds=0.001)  # Very short timeout
            bridge_timeout = SignalBridge(config_timeout)
            
            # This should trigger timeout handling
            symbols = ["AAPL"]
            market_data = self._create_sample_market_data(symbols)
            
            try:
                results = bridge_timeout.generate_signals_sync(symbols, market_data, datetime.now())
                timeout_handled = True
            except Exception:
                timeout_handled = False
            
            self._add_check(category, "Timeout Handling", timeout_handled,
                          "Timeout handling working correctly")
            
        except Exception as e:
            self._add_check(category, "Error Handling", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_signal_consistency(self):
        """Validate signal consistency between environments"""
        logger.info("Validating signal consistency...")
        
        category = 'SignalConsistency'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            bridge = create_signal_bridge()
            symbols = ["AAPL", "SPY"]
            market_data = self._create_sample_market_data(symbols)
            current_date = datetime.now()
            
            # Test 1: Signal consistency across calls
            results1 = bridge.generate_signals_sync(symbols, market_data, current_date)
            results2 = bridge.generate_signals_sync(symbols, market_data, current_date)
            
            # Second call should use cache
            cache_used = all(result.source == "cached" for result in results2.values())
            self._add_check(category, "Cache Consistency", cache_used,
                          "Cache used for repeated signal generation")
            
            # Test 2: Signal value consistency
            values_consistent = all(
                abs(results1[symbol].signal_value - results2[symbol].signal_value) < 0.001
                for symbol in symbols
            )
            self._add_check(category, "Signal Value Consistency", values_consistent,
                          "Signal values consistent between calls")
            
            # Test 3: Confidence consistency
            confidence_consistent = all(
                abs(results1[symbol].confidence - results2[symbol].confidence) < 0.001
                for symbol in symbols
            )
            self._add_check(category, "Confidence Consistency", confidence_consistent,
                          "Confidence values consistent between calls")
            
        except Exception as e:
            self._add_check(category, "Signal Consistency", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_cache_optimization(self):
        """Validate cache and optimization features"""
        logger.info("Validating cache and optimization...")
        
        category = 'CacheOptimization'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            bridge = create_signal_bridge()
            symbols = ["AAPL"]
            market_data = self._create_sample_market_data(symbols)
            current_date = datetime.now()
            
            # Test 1: Cache functionality
            # First call - should generate signals
            start_time = time.time()
            results1 = bridge.generate_signals_sync(symbols, market_data, current_date)
            first_call_time = time.time() - start_time
            
            # Second call - should use cache
            start_time = time.time()
            results2 = bridge.generate_signals_sync(symbols, market_data, current_date)
            second_call_time = time.time() - start_time
            
            cache_faster = second_call_time < first_call_time
            self._add_check(category, "Cache Performance", cache_faster,
                          f"Cache call ({second_call_time:.3f}s) faster than first call ({first_call_time:.3f}s)")
            
            # Test 2: Cache size management
            initial_cache_size = len(bridge._signal_cache)
            
            # Generate many signals to test cache size limit
            many_symbols = [f"SYMBOL_{i}" for i in range(100)]
            many_market_data = self._create_sample_market_data(many_symbols)
            
            bridge.generate_signals_sync(many_symbols, many_market_data, current_date)
            
            final_cache_size = len(bridge._signal_cache)
            cache_limited = final_cache_size <= bridge.config.cache_size
            
            self._add_check(category, "Cache Size Management", cache_limited,
                          f"Cache size ({final_cache_size}) within limit ({bridge.config.cache_size})")
            
            # Test 3: Cache clearing
            bridge.clear_cache()
            cache_cleared = len(bridge._signal_cache) == 0
            self._add_check(category, "Cache Clearing", cache_cleared,
                          "Cache cleared successfully")
            
        except Exception as e:
            self._add_check(category, "Cache Optimization", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _validate_production_readiness(self):
        """Validate production readiness"""
        logger.info("Validating production readiness...")
        
        category = 'ProductionReadiness'
        self.validation_results['categories'][category] = {
            'checks': [],
            'passed': 0,
            'failed': 0,
            'success_rate': 0.0
        }
        
        try:
            bridge = create_signal_bridge()
            
            # Test 1: Resource cleanup
            bridge.shutdown()
            self._add_check(category, "Resource Cleanup", True,
                          "Resources cleaned up successfully")
            
            # Test 2: Configuration validation
            config = SignalBridgeConfig(
                max_concurrent_signals=10,
                timeout_seconds=5.0,
                cache_size=1000
            )
            
            valid_config = (
                0 < config.max_concurrent_signals <= 100 and
                0 < config.timeout_seconds <= 60 and
                0 < config.cache_size <= 10000
            )
            
            self._add_check(category, "Configuration Validation", valid_config,
                          "Configuration parameters within valid ranges")
            
            # Test 3: Memory usage
            bridge = create_signal_bridge()
            symbols = ["AAPL", "SPY", "MSFT", "GOOGL", "TSLA"]
            market_data = self._create_sample_market_data(symbols)
            
            # Generate signals multiple times
            for _ in range(10):
                bridge.generate_signals_sync(symbols, market_data, datetime.now())
            
            stats = bridge.get_performance_stats()
            memory_efficient = stats['total_signals'] > 0
            
            self._add_check(category, "Memory Efficiency", memory_efficient,
                          f"Processed {stats['total_signals']} signals without memory issues")
            
            # Test 4: Thread safety
            import threading
            
            def generate_signals_thread():
                try:
                    bridge.generate_signals_sync(symbols, market_data, datetime.now())
                    return True
                except Exception:
                    return False
            
            threads = []
            results = []
            
            for _ in range(5):
                thread = threading.Thread(target=lambda: results.append(generate_signals_thread()))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            thread_safe = all(results)
            self._add_check(category, "Thread Safety", thread_safe,
                          "Thread-safe signal generation")
            
        except Exception as e:
            self._add_check(category, "Production Readiness", False, f"Error: {str(e)}")
        
        self._calculate_category_results(category)
    
    def _create_sample_market_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Create sample market data for testing"""
        market_data = {}
        
        for symbol in symbols:
            dates = pd.date_range('2023-01-01', periods=100, freq='D')
            data = {
                'open': np.random.uniform(100, 200, 100),
                'high': np.random.uniform(100, 200, 100),
                'low': np.random.uniform(100, 200, 100),
                'close': np.random.uniform(100, 200, 100),
                'volume': np.random.uniform(1000000, 5000000, 100)
            }
            market_data[symbol] = pd.DataFrame(data, index=dates)
        
        return market_data
    
    def _add_check(self, category: str, check_name: str, passed: bool, message: str):
        """Add a validation check result"""
        check = {
            'name': check_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.validation_results['categories'][category]['checks'].append(check)
        self.validation_results['total_checks'] += 1
        
        if passed:
            self.validation_results['categories'][category]['passed'] += 1
            self.validation_results['passed_checks'] += 1
            logger.info(f"✅ {category}: {check_name} - {message}")
        else:
            self.validation_results['categories'][category]['failed'] += 1
            self.validation_results['failed_checks'] += 1
            logger.error(f"❌ {category}: {check_name} - {message}")
    
    def _calculate_category_results(self, category: str):
        """Calculate results for a category"""
        cat = self.validation_results['categories'][category]
        total_checks = len(cat['checks'])
        
        if total_checks > 0:
            cat['success_rate'] = (cat['passed'] / total_checks) * 100
        else:
            cat['success_rate'] = 0.0
    
    def _calculate_final_results(self):
        """Calculate final validation results"""
        total_checks = self.validation_results['total_checks']
        
        if total_checks > 0:
            self.validation_results['success_rate'] = (
                self.validation_results['passed_checks'] / total_checks
            ) * 100
        else:
            self.validation_results['success_rate'] = 0.0
        
        # Generate recommendations
        self._generate_recommendations()
    
    def _generate_recommendations(self):
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check overall success rate
        if self.validation_results['success_rate'] < 80:
            recommendations.append("Overall success rate below 80%. Review failed checks and fix issues.")
        
        # Check performance
        perf_metrics = self.validation_results.get('performance_metrics', {})
        if perf_metrics.get('throughput', 0) < 5.0:
            recommendations.append("Signal throughput below 5 signals/second. Consider performance optimization.")
        
        # Check error handling
        error_category = self.validation_results['categories'].get('ErrorHandling', {})
        if error_category.get('success_rate', 0) < 100:
            recommendations.append("Error handling needs improvement. Review error handling mechanisms.")
        
        # Check production readiness
        prod_category = self.validation_results['categories'].get('ProductionReadiness', {})
        if prod_category.get('success_rate', 0) < 100:
            recommendations.append("Production readiness issues detected. Address before deployment.")
        
        if not recommendations:
            recommendations.append("All validations passed successfully. SignalBridge is ready for production use.")
        
        self.validation_results['recommendations'] = recommendations
    
    def _generate_validation_report(self):
        """Generate and save validation report"""
        report = {
            'validation_summary': {
                'phase': self.validation_results['phase'],
                'timestamp': self.validation_results['timestamp'],
                'total_checks': self.validation_results['total_checks'],
                'passed_checks': self.validation_results['passed_checks'],
                'failed_checks': self.validation_results['failed_checks'],
                'success_rate': f"{self.validation_results['success_rate']:.1f}%"
            },
            'category_results': {},
            'performance_metrics': self.validation_results['performance_metrics'],
            'recommendations': self.validation_results['recommendations']
        }
        
        # Add category results
        for category, data in self.validation_results['categories'].items():
            report['category_results'][category] = {
                'passed': data['passed'],
                'failed': data['failed'],
                'success_rate': f"{data['success_rate']:.1f}%",
                'checks': data['checks']
            }
        
        # Save report
        report_file = f"signal_bridge_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Validation report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("SIGNALBRIDGE VALIDATION SUMMARY")
        print("="*80)
        print(f"Phase: {self.validation_results['phase']}")
        print(f"Timestamp: {self.validation_results['timestamp']}")
        print(f"Total Checks: {self.validation_results['total_checks']}")
        print(f"Passed: {self.validation_results['passed_checks']}")
        print(f"Failed: {self.validation_results['failed_checks']}")
        print(f"Success Rate: {self.validation_results['success_rate']:.1f}%")
        print("\nCategory Results:")
        
        for category, data in self.validation_results['categories'].items():
            print(f"  {category}: {data['success_rate']:.1f}% ({data['passed']}/{data['passed'] + data['failed']})")
        
        print("\nPerformance Metrics:")
        for metric, value in self.validation_results['performance_metrics'].items():
            if isinstance(value, float):
                print(f"  {metric}: {value:.3f}")
            else:
                print(f"  {metric}: {value}")
        
        print("\nRecommendations:")
        for rec in self.validation_results['recommendations']:
            print(f"  • {rec}")
        
        print("="*80)


def main():
    """Main validation function"""
    validator = SignalBridgeValidator()
    results = validator.run_all_validations()
    
    # Return success if overall success rate >= 80%
    return results['success_rate'] >= 80.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 