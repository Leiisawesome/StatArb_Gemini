#!/usr/bin/env python3
"""
Test Parameter Optimization Flow and File-Based Persistence
Verifies the complete flow from training optimization to trading parameter application
"""

import sys
import os
# Add the current directory (StatArb_Gemini root) to the path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)
# Also add the current working directory
sys.path.insert(0, os.getcwd())

from strategies.multi_factor_ensemble_strategy import MultiFactorEnsembleStrategy, MultiFactorConfig, FactorConfig, FactorType
from core_structure.infrastructure.config.enhanced_config_manager import EnhancedConfigManager
from engines.enhanced_backtesting_engine import EnhancedBacktestingEngine

import logging
import json
import tempfile
import shutil
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ParameterOptimizationFlowTest:
    """Test the complete parameter optimization flow"""
    
    def __init__(self):
        self.config_manager = EnhancedConfigManager()
        self.engine = EnhancedBacktestingEngine()
        self.test_results = {}
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp(prefix="param_opt_test_")
        logger.info(f"Created temporary test directory: {self.temp_dir}")
        
    def run_complete_flow_test(self):
        """Run complete parameter optimization flow test"""
        
        logger.info("Starting Parameter Optimization Flow Test")
        
        try:
            # Step 1: Test Strategy Parameter Optimization
            logger.info("Step 1: Testing strategy parameter optimization...")
            optimization_test = self._test_strategy_optimization()
            
            # Step 2: Test Parameter Persistence
            logger.info("Step 2: Testing parameter persistence...")
            persistence_test = self._test_parameter_persistence()
            
            # Step 3: Test Parameter Loading for Trading
            logger.info("Step 3: Testing parameter loading for trading...")
            loading_test = self._test_parameter_loading()
            
            # Step 4: Test Complete Flow Integration
            logger.info("Step 4: Testing complete flow integration...")
            integration_test = self._test_complete_integration()
            
            # Compile results
            self.test_results = {
                'optimization_test': optimization_test,
                'persistence_test': persistence_test,
                'loading_test': loading_test,
                'integration_test': integration_test,
                'test_summary': self._generate_test_summary(),
                'test_date': datetime.now().isoformat()
            }
            
            logger.info("Parameter optimization flow test completed successfully!")
            return self.test_results
            
        except Exception as e:
            logger.error(f"Parameter optimization flow test failed: {e}")
            raise
        finally:
            # Clean up temporary directory
            self._cleanup()
    
    def _test_strategy_optimization(self) -> Dict[str, Any]:
        """Test that MultiFactorEnsembleStrategy can optimize parameters"""
        
        try:
            # Create test configuration
            config = self._create_test_config()
            
            # Initialize strategy
            strategy = MultiFactorEnsembleStrategy(config)
            
            # Simulate some performance data
            strategy.performance_metrics = {
                'sharpe_ratio': 0.3,  # Low Sharpe ratio to trigger optimization
                'total_return': 0.05,
                'max_drawdown': 0.12,
                'volatility': 0.15
            }
            
            # Simulate factor signals
            strategy.factor_signals = {
                'AAPL': {'technical': 0.2, 'momentum': 0.1, 'mean_reversion': 0.05, 'volatility': 0.02},
                'MSFT': {'technical': 0.15, 'momentum': 0.08, 'mean_reversion': 0.03, 'volatility': 0.01}
            }
            
            # Run parameter optimization
            optimization_results = strategy.optimize_parameters()
            
            # Validate results
            validation = {
                'optimization_successful': len(optimization_results) > 0,
                'has_recommended_adjustments': 'recommended_adjustments' in optimization_results,
                'has_optimization_score': 'optimization_score' in optimization_results,
                'has_factor_optimization': 'factor_optimization' in optimization_results,
                'optimization_score': optimization_results.get('optimization_score', 0),
                'recommended_weights': optimization_results.get('recommended_adjustments', {}).get('factor_weights', {}),
                'optimization_reason': optimization_results.get('recommended_adjustments', {}).get('optimization_reason', '')
            }
            
            logger.info(f"Strategy optimization test completed - Score: {validation['optimization_score']:.4f}")
            logger.info(f"Recommended weights: {validation['recommended_weights']}")
            
            return {
                'test_name': 'Strategy Parameter Optimization',
                'status': 'PASS' if validation['optimization_successful'] else 'FAIL',
                'validation': validation,
                'optimization_results': optimization_results
            }
            
        except Exception as e:
            logger.error(f"Strategy optimization test failed: {e}")
            return {
                'test_name': 'Strategy Parameter Optimization',
                'status': 'FAIL',
                'error': str(e)
            }
    
    def _test_parameter_persistence(self) -> Dict[str, Any]:
        """Test parameter persistence to file"""
        
        try:
            # Create test parameters
            test_parameters = {
                'factor_weights': {
                    'technical': 0.5,
                    'momentum': 0.25,
                    'mean_reversion': 0.15,
                    'volatility': 0.1
                },
                'thresholds': {
                    'signal_threshold': 0.12,
                    'max_positions': 18
                }
            }
            
            test_performance_metrics = {
                'sharpe_ratio': 0.8,
                'total_return': 0.15,
                'max_drawdown': 0.08
            }
            
            # Save parameters
            strategy_name = "technical_momentum"
            self.config_manager.save_optimized_parameters(
                strategy_name, test_parameters, test_performance_metrics
            )
            
            # Load parameters back
            loaded_parameters = self.config_manager._load_optimized_parameters(strategy_name)
            
            # Validate persistence
            validation = {
                'save_successful': len(loaded_parameters) > 0,
                'parameters_match': test_parameters == loaded_parameters,
                'has_factor_weights': 'factor_weights' in loaded_parameters,
                'has_thresholds': 'thresholds' in loaded_parameters,
                'factor_weights_match': test_parameters['factor_weights'] == loaded_parameters.get('factor_weights', {}),
                'thresholds_match': test_parameters['thresholds'] == loaded_parameters.get('thresholds', {})
            }
            
            logger.info(f"Parameter persistence test completed - Match: {validation['parameters_match']}")
            
            return {
                'test_name': 'Parameter Persistence',
                'status': 'PASS' if validation['save_successful'] and validation['parameters_match'] else 'FAIL',
                'validation': validation,
                'saved_parameters': test_parameters,
                'loaded_parameters': loaded_parameters
            }
            
        except Exception as e:
            logger.error(f"Parameter persistence test failed: {e}")
            return {
                'test_name': 'Parameter Persistence',
                'status': 'FAIL',
                'error': str(e)
            }
    
    def _test_parameter_loading(self) -> Dict[str, Any]:
        """Test parameter loading for trading configuration"""
        
        try:
            # Create step 2 (real-time) configuration
            config = self.config_manager.create_step2_realtime_config(
                strategy_name="technical_momentum",
                trading_start="2025-01-01"
            )
            
            # Check if optimized parameters were loaded
            strategy_params = config.strategy.parameters
            
            validation = {
                'config_created': config is not None,
                'has_strategy_config': hasattr(config, 'strategy'),
                'has_parameters': len(strategy_params) > 0,
                'parameters_loaded': 'factor_weights' in strategy_params or 'thresholds' in strategy_params
            }
            
            logger.info(f"Parameter loading test completed - Parameters loaded: {validation['parameters_loaded']}")
            
            return {
                'test_name': 'Parameter Loading for Trading',
                'status': 'PASS' if validation['config_created'] and validation['parameters_loaded'] else 'FAIL',
                'validation': validation,
                'loaded_parameters': strategy_params
            }
            
        except Exception as e:
            logger.error(f"Parameter loading test failed: {e}")
            return {
                'test_name': 'Parameter Loading for Trading',
                'status': 'FAIL',
                'error': str(e)
            }
    
    def _test_complete_integration(self) -> Dict[str, Any]:
        """Test complete integration flow"""
        
        try:
            # Step 1: Create training configuration
            training_config = self.config_manager.create_step1_backtesting_config(
                strategy_name="technical_momentum",
                training_start="2023-01-01",
                training_end="2024-12-31",
                validation_start="2025-01-01",
                validation_end="2025-06-30"
            )
            
            # Step 2: Simulate parameter optimization during training
            test_optimized_params = {
                'factor_weights': {
                    'technical': 0.55,
                    'momentum': 0.20,
                    'mean_reversion': 0.15,
                    'volatility': 0.10
                },
                'thresholds': {
                    'signal_threshold': 0.10,
                    'max_positions': 20
                }
            }
            
            # Step 3: Save optimized parameters
            self.config_manager.save_optimized_parameters(
                "technical_momentum",
                test_optimized_params,
                {'sharpe_ratio': 0.9, 'total_return': 0.18, 'max_drawdown': 0.06}
            )
            
            # Step 4: Create trading configuration (should load optimized params)
            trading_config = self.config_manager.create_step2_realtime_config(
                strategy_name="technical_momentum",
                trading_start="2025-01-01"
            )
            
            # Step 5: Verify optimized parameters are applied
            trading_params = trading_config.strategy.parameters
            
            validation = {
                'training_config_created': training_config is not None,
                'trading_config_created': trading_config is not None,
                'optimized_params_applied': len(trading_params) > 0,
                'factor_weights_applied': 'factor_weights' in trading_params or any('weight' in k for k in trading_params.keys()),
                'thresholds_applied': 'thresholds' in trading_params or any('threshold' in k for k in trading_params.keys())
            }
            
            logger.info(f"Complete integration test completed - Params applied: {validation['optimized_params_applied']}")
            
            return {
                'test_name': 'Complete Integration Flow',
                'status': 'PASS' if all(validation.values()) else 'FAIL',
                'validation': validation,
                'training_config_params': training_config.strategy.parameters,
                'trading_config_params': trading_params
            }
            
        except Exception as e:
            logger.error(f"Complete integration test failed: {e}")
            return {
                'test_name': 'Complete Integration Flow',
                'status': 'FAIL',
                'error': str(e)
            }
    
    def _create_test_config(self) -> MultiFactorConfig:
        """Create test configuration for MultiFactorEnsembleStrategy"""
        
        factors = [
            FactorConfig(
                factor_type=FactorType.TECHNICAL,
                lookback_period=20,
                threshold=0.15,
                weight=0.4,
                indicators={
                    'rsi_period': 14,
                    'macd_fast': 12,
                    'macd_slow': 26,
                    'bollinger_period': 20
                }
            ),
            FactorConfig(
                factor_type=FactorType.MOMENTUM,
                lookback_period=252,
                threshold=0.10,
                weight=0.3,
                momentum_type="risk_adjusted"
            ),
            FactorConfig(
                factor_type=FactorType.MEAN_REVERSION,
                lookback_period=60,
                threshold=0.20,
                weight=0.2,
                mean_reversion_threshold=0.5
            ),
            FactorConfig(
                factor_type=FactorType.VOLATILITY,
                lookback_period=30,
                threshold=0.25,
                weight=0.1,
                volatility_metrics=["rolling_std", "bollinger_width"]
            )
        ]
        
        return MultiFactorConfig(
            factors=factors,
            ensemble_method="adaptive_weighting",
            factor_combination_method="weighted_sum",
            signal_threshold=0.15,
            max_factors_per_asset=4,
            initial_capital=100000,
            max_position_value=10000,
            max_positions=15
        )
    
    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        
        total_tests = 4
        passed_tests = sum(1 for test_name in ['optimization_test', 'persistence_test', 'loading_test', 'integration_test']
                          if self.test_results.get(test_name, {}).get('status') == 'PASS')
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'overall_status': 'PASS' if passed_tests == total_tests else 'FAIL'
        }
    
    def _cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {e}")
    
    def save_test_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"results/parameter_optimization_flow_test_{timestamp}.json"
        
        # Ensure results directory exists
        os.makedirs("results", exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to {results_file}")
        return results_file

def main():
    """Main execution function"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run parameter optimization flow test
    test = ParameterOptimizationFlowTest()
    results = test.run_complete_flow_test()
    
    # Save results
    results_file = test.save_test_results()
    
    # Print summary
    print("\n" + "="*80)
    print("PARAMETER OPTIMIZATION FLOW TEST RESULTS")
    print("="*80)
    
    summary = results.get('test_summary', {})
    print(f"Overall Status: {summary.get('overall_status', 'UNKNOWN')}")
    print(f"Tests Passed: {summary.get('passed_tests', 0)}/{summary.get('total_tests', 0)}")
    print(f"Success Rate: {summary.get('success_rate', 0):.1%}")
    
    print(f"\nDetailed Results:")
    for test_name in ['optimization_test', 'persistence_test', 'loading_test', 'integration_test']:
        test_result = results.get(test_name, {})
        status = test_result.get('status', 'UNKNOWN')
        test_name_display = test_result.get('test_name', test_name)
        print(f"  {test_name_display}: {status}")
    
    print(f"\nTest results saved to: {results_file}")
    
    if summary.get('overall_status') == 'PASS':
        print("\n✅ PARAMETER OPTIMIZATION FLOW TEST PASSED!")
        print("All components are working correctly:")
        print("  - Strategy parameter optimization ✅")
        print("  - Parameter persistence to file ✅")
        print("  - Parameter loading for trading ✅")
        print("  - Complete integration flow ✅")
    else:
        print("\n❌ PARAMETER OPTIMIZATION FLOW TEST FAILED!")
        print("Check the detailed results for specific issues.")

if __name__ == "__main__":
    main() 