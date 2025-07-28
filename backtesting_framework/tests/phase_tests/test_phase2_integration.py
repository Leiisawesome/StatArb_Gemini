#!/usr/bin/env python3
"""
Test Phase 2: Backtesting Framework Integration
Validates integration of Phase 1 components with enhanced backtesting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import json

from enhanced_backtesting_engine import EnhancedBacktestingEngine
from strategies.enhanced_academic_strategy import EnhancedAcademicStrategy

def create_test_data():
    """Create test market data for Phase 2 validation"""
    print("Creating test market data for Phase 2...")
    
    # Generate 3 years of daily data
    dates = pd.date_range(start='2021-01-01', end='2023-12-31', freq='D')
    n_days = len(dates)
    
    # Create realistic price data with trends and volatility
    np.random.seed(42)  # For reproducible results
    
    # SPY data (market benchmark)
    spy_returns = np.random.normal(0.0008, 0.015, n_days)  # 20% annual return, 24% vol
    spy_prices = 400 * np.exp(np.cumsum(spy_returns))
    spy_data = pd.DataFrame({
        'close': spy_prices,
        'volume': np.random.lognormal(15, 0.5, n_days) * 1000000  # Realistic volume
    }, index=dates)
    
    # AAPL data (individual stock)
    aapl_returns = np.random.normal(0.001, 0.02, n_days)  # 25% annual return, 32% vol
    aapl_prices = 150 * np.exp(np.cumsum(aapl_returns))
    aapl_data = pd.DataFrame({
        'close': aapl_prices,
        'volume': np.random.lognormal(16, 0.4, n_days) * 1000000
    }, index=dates)
    
    # MSFT data
    msft_returns = np.random.normal(0.0009, 0.018, n_days)  # 23% annual return, 29% vol
    msft_prices = 300 * np.exp(np.cumsum(msft_returns))
    msft_data = pd.DataFrame({
        'close': msft_prices,
        'volume': np.random.lognormal(15.5, 0.45, n_days) * 1000000
    }, index=dates)
    
    # GOOGL data
    googl_returns = np.random.normal(0.0011, 0.019, n_days)  # 28% annual return, 30% vol
    googl_prices = 2500 * np.exp(np.cumsum(googl_returns))
    googl_data = pd.DataFrame({
        'close': googl_prices,
        'volume': np.random.lognormal(14.5, 0.5, n_days) * 1000000
    }, index=dates)
    
    return {
        'SPY': spy_data,
        'AAPL': aapl_data,
        'MSFT': msft_data,
        'GOOGL': googl_data
    }

def test_enhanced_backtesting_engine():
    """Test the enhanced backtesting engine"""
    print("\n=== Testing Enhanced Backtesting Engine ===")
    
    # Create test data
    test_data = create_test_data()
    
    # Initialize backtesting engine
    print("\n1. Testing Engine Initialization...")
    try:
        engine = EnhancedBacktestingEngine()
        print("✅ Enhanced backtesting engine initialized successfully")
        
        # Manually set data (bypassing data loader for testing)
        engine.data = test_data
        print(f"✅ Test data loaded: {len(engine.data)} symbols")
        
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")
        return False
    
    # Test strategy initialization
    print("\n2. Testing Strategy Initialization...")
    try:
        engine.initialize_strategy()
        print("✅ Enhanced academic strategy initialized successfully")
        
        # Check strategy components
        if hasattr(engine.strategy, 'signal_generator'):
            print("✅ Signal generator integrated")
        if hasattr(engine.strategy, 'benchmark_analyzer'):
            print("✅ Benchmark analyzer integrated")
        if hasattr(engine.strategy, 'spy_data'):
            print("✅ SPY benchmark data loaded")
        
    except Exception as e:
        print(f"❌ Strategy initialization failed: {e}")
        return False
    
    # Test backtesting execution
    print("\n3. Testing Backtesting Execution...")
    try:
        results = engine.run_backtest()
        print("✅ Enhanced backtesting completed successfully")
        
        # Validate results structure
        required_keys = ['backtest_results', 'performance_metrics', 'optimization_results', 'strategy_summary', 'academic_analysis']
        for key in required_keys:
            if key in results:
                print(f"✅ {key} present in results")
            else:
                print(f"❌ {key} missing from results")
                return False
        
    except Exception as e:
        print(f"❌ Backtesting execution failed: {e}")
        return False
    
    # Test results analysis
    print("\n4. Testing Results Analysis...")
    try:
        # Check backtest results
        backtest_results = results['backtest_results']
        print(f"✅ Signals generated: {backtest_results.get('signals_generated', 0)}")
        print(f"✅ Trades executed: {backtest_results.get('trades_executed', 0)}")
        
        # Check performance metrics
        performance_metrics = results['performance_metrics']
        print(f"✅ Performance metrics calculated: {len(performance_metrics)} metrics")
        
        # Check academic analysis
        academic_analysis = results['academic_analysis']
        if academic_analysis.get('academic_foundations_implemented'):
            print("✅ Academic foundations implemented")
        if academic_analysis.get('benchmark_analysis', {}).get('spy_benchmark_used'):
            print("✅ SPY benchmark analysis active")
        
    except Exception as e:
        print(f"❌ Results analysis failed: {e}")
        return False
    
    return True

def test_enhanced_academic_strategy():
    """Test the enhanced academic strategy directly"""
    print("\n=== Testing Enhanced Academic Strategy ===")
    
    # Create test data
    test_data = create_test_data()
    
    # Initialize strategy
    print("\n1. Testing Strategy Initialization...")
    try:
        strategy = EnhancedAcademicStrategy({})
        strategy.initialize(test_data)
        print("✅ Enhanced academic strategy initialized successfully")
        
    except Exception as e:
        print(f"❌ Strategy initialization failed: {e}")
        return False
    
    # Test signal generation
    print("\n2. Testing Signal Generation...")
    try:
        signals = strategy.generate_signals(test_data)
        print(f"✅ Generated {len(signals)} academic momentum signals")
        
        # Check signal quality
        if len(signals) > 0:
            for signal in signals[:3]:  # Show first 3 signals
                print(f"   Signal: {signal.symbol} {signal.signal_type.value} "
                      f"(confidence: {signal.confidence:.4f})")
        
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return False
    
    # Test performance metrics calculation
    print("\n3. Testing Performance Metrics...")
    try:
        # Simulate some returns for testing
        strategy.returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        metrics = strategy.calculate_performance_metrics()
        print(f"✅ Performance metrics calculated: {len(metrics)} metrics")
        
        # Check for benchmark metrics
        benchmark_metrics = ['information_ratio', 'tracking_error', 'beta']
        for metric in benchmark_metrics:
            if metric in metrics:
                print(f"✅ {metric}: {metrics[metric]:.4f}")
            else:
                print(f"⚠️  {metric} not calculated")
        
    except Exception as e:
        print(f"❌ Performance metrics calculation failed: {e}")
        return False
    
    # Test parameter optimization
    print("\n4. Testing Parameter Optimization...")
    try:
        optimization = strategy.optimize_parameters()
        print("✅ Parameter optimization completed")
        
        if 'optimization_score' in optimization:
            print(f"✅ Optimization score: {optimization['optimization_score']:.4f}")
        
        if 'recommended_adjustments' in optimization:
            print("✅ Parameter adjustments recommended")
        
    except Exception as e:
        print(f"❌ Parameter optimization failed: {e}")
        return False
    
    return True

def test_results_saving_and_reporting():
    """Test results saving and report generation"""
    print("\n=== Testing Results Saving and Reporting ===")
    
    # Create test data and run backtest
    test_data = create_test_data()
    engine = EnhancedBacktestingEngine()
    engine.data = test_data
    engine.initialize_strategy()
    results = engine.run_backtest()
    
    # Test results saving
    print("\n1. Testing Results Saving...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        engine.save_results(temp_path)
        print(f"✅ Results saved to temporary file")
        
        # Verify saved results
        with open(temp_path, 'r') as f:
            saved_results = json.load(f)
        
        if 'backtest_results' in saved_results:
            print("✅ Saved results contain backtest data")
        else:
            print("❌ Saved results missing backtest data")
            return False
        
        # Clean up
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"❌ Results saving failed: {e}")
        return False
    
    # Test report generation
    print("\n2. Testing Report Generation...")
    try:
        report = engine.generate_report()
        print("✅ Report generated successfully")
        
        # Check report content
        if "ENHANCED ACADEMIC BACKTESTING REPORT" in report:
            print("✅ Report contains proper header")
        if "STRATEGY SUMMARY" in report:
            print("✅ Report contains strategy summary")
        if "PERFORMANCE METRICS" in report:
            print("✅ Report contains performance metrics")
        if "ACADEMIC ANALYSIS" in report:
            print("✅ Report contains academic analysis")
        
        print(f"✅ Report length: {len(report)} characters")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        return False
    
    return True

def main():
    """Run all Phase 2 tests"""
    print("🚀 Phase 2: Backtesting Framework Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Enhanced Backtesting Engine", test_enhanced_backtesting_engine),
        ("Enhanced Academic Strategy", test_enhanced_academic_strategy),
        ("Results Saving and Reporting", test_results_saving_and_reporting)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 2 Implementation: SUCCESS")
        print("\n✅ Backtesting framework integration complete!")
        print("✅ Enhanced academic strategy operational")
        print("✅ Phase 1 components successfully integrated")
        print("✅ Results saving and reporting functional")
        print("✅ Ready for Phase 3: Real-Time Integration")
    else:
        print("❌ Phase 2 Implementation: FAILED")
        print("Please fix the failing tests before proceeding to Phase 3")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 