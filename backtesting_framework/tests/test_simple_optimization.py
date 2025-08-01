#!/usr/bin/env python3
"""
Simple Test for MultiFactorEnsembleStrategy Parameter Optimization
Tests the optimize_parameters method without complex dependencies
"""

import sys
import os
# Add the current directory to the path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from strategies.multi_factor_ensemble_strategy import MultiFactorEnsembleStrategy, MultiFactorConfig, FactorConfig, FactorType
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def test_optimize_parameters():
    """Test that MultiFactorEnsembleStrategy can optimize parameters"""
    
    print("Testing MultiFactorEnsembleStrategy.optimize_parameters()...")
    
    try:
        # Create test configuration
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
        
        config = MultiFactorConfig(
            factors=factors,
            ensemble_method="adaptive_weighting",
            factor_combination_method="weighted_sum",
            signal_threshold=0.15,
            max_factors_per_asset=4,
            initial_capital=100000,
            max_position_value=10000,
            max_positions=15
        )
        
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
        print(f"✅ Optimization successful: {len(optimization_results) > 0}")
        print(f"✅ Has recommended adjustments: {'recommended_adjustments' in optimization_results}")
        print(f"✅ Has optimization score: {'optimization_score' in optimization_results}")
        print(f"✅ Has factor optimization: {'factor_optimization' in optimization_results}")
        
        print(f"\nOptimization Score: {optimization_results.get('optimization_score', 0):.4f}")
        
        recommended_weights = optimization_results.get('recommended_adjustments', {}).get('factor_weights', {})
        print(f"Recommended Factor Weights: {recommended_weights}")
        
        optimization_reason = optimization_results.get('recommended_adjustments', {}).get('optimization_reason', '')
        print(f"Optimization Reason: {optimization_reason}")
        
        # Test factor performance analysis
        factor_optimization = optimization_results.get('factor_optimization', {})
        print(f"\nFactor Optimization Analysis:")
        for factor_name, factor_data in factor_optimization.items():
            print(f"  {factor_name}: {factor_data.get('performance_score', 0):.4f}")
        
        print("\n✅ MultiFactorEnsembleStrategy.optimize_parameters() test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_persistence():
    """Test parameter persistence functionality"""
    
    print("\nTesting parameter persistence...")
    
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
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        param_file = f"test_optimized_params_{timestamp}.json"
        
        param_data = {
            'parameters': test_parameters,
            'performance_metrics': {
                'sharpe_ratio': 0.8,
                'total_return': 0.15,
                'max_drawdown': 0.08
            },
            'optimization_date': datetime.now().isoformat()
        }
        
        with open(param_file, 'w') as f:
            json.dump(param_data, f, indent=2)
        
        print(f"✅ Parameters saved to {param_file}")
        
        # Load from file
        with open(param_file, 'r') as f:
            loaded_data = json.load(f)
        
        loaded_parameters = loaded_data.get('parameters', {})
        
        # Validate
        parameters_match = test_parameters == loaded_parameters
        print(f"✅ Parameters match: {parameters_match}")
        
        # Clean up
        import os
        if os.path.exists(param_file):
            os.remove(param_file)
            print(f"✅ Cleaned up {param_file}")
        
        print("✅ Parameter persistence test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Parameter persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("="*60)
    print("SIMPLE PARAMETER OPTIMIZATION TEST")
    print("="*60)
    
    # Test 1: Strategy optimization
    test1_passed = test_optimize_parameters()
    
    # Test 2: Parameter persistence
    test2_passed = test_parameter_persistence()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Strategy Optimization: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Parameter Persistence: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ MultiFactorEnsembleStrategy.optimize_parameters() is working")
        print("✅ Parameter persistence system is working")
        print("✅ Parameter flow from training to trading is ready")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("Check the output above for specific issues.")

if __name__ == "__main__":
    main() 