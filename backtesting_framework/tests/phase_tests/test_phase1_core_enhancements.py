#!/usr/bin/env python3
"""
Test Phase 1: Core System Enhancements
Validates enhanced technical indicators, signal generation, and benchmark analysis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from core_structure.signal_generation.indicators.enhanced_technical_indicators import (
    EnhancedTechnicalIndicatorEngine, AcademicMomentumConfig, RegimeType
)
from core_structure.signal_generation.enhanced_signal_generator import (
    EnhancedSignalGenerator, AcademicSignalConfig
)
from core_structure.performance.benchmark_analyzer import (
    BenchmarkAnalyzer, BenchmarkConfig
)

def create_test_data():
    """Create test market data for validation"""
    print("Creating test market data...")
    
    # Generate 2 years of daily data
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
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
    
    return {
        'SPY': spy_data,
        'AAPL': aapl_data,
        'MSFT': msft_data
    }

def test_enhanced_technical_indicators():
    """Test the enhanced technical indicators engine"""
    print("\n=== Testing Enhanced Technical Indicators Engine ===")
    
    # Create test data
    test_data = create_test_data()
    
    # Initialize indicator engine
    config = AcademicMomentumConfig()
    indicator_engine = EnhancedTechnicalIndicatorEngine(config)
    
    # Test academic momentum signals
    print("\n1. Testing Academic Momentum Signals...")
    try:
        academic_signals = indicator_engine.calculate_academic_momentum_signals(
            test_data, test_data['SPY']
        )
        
        print(f"✅ Academic momentum signals calculated successfully")
        print(f"   Symbols processed: {len(academic_signals)}")
        
        # Check signal structure
        for symbol, signals in academic_signals.items():
            print(f"   {symbol}: {len(signals)} signals")
            # Check for key signal types
            expected_signals = [
                'momentum_1w', 'momentum_1m', 'momentum_3m', 'momentum_6m',
                'volume_weighted_momentum', 'regime_adjusted_momentum',
                'crash_protected_momentum', 'macro_adjusted_momentum'
            ]
            
            for expected in expected_signals:
                if expected in signals:
                    print(f"     ✅ {expected}: {signals[expected]:.4f}")
                else:
                    print(f"     ❌ {expected}: Missing")
        
    except Exception as e:
        print(f"❌ Academic momentum signals failed: {e}")
        return False
    
    # Test regime detection
    print("\n2. Testing Market Regime Detection...")
    try:
        regime = indicator_engine.regime_detector.detect_regime(test_data['SPY'])
        print(f"✅ Market regime detected: {regime.value}")
        
        # Test all regime types
        regimes = [RegimeType.BULL_MARKET, RegimeType.BEAR_MARKET, 
                  RegimeType.HIGH_VOLATILITY, RegimeType.MOMENTUM_CRASH]
        print(f"   Supported regimes: {[r.value for r in regimes]}")
        
    except Exception as e:
        print(f"❌ Regime detection failed: {e}")
        return False
    
    # Test volume momentum analysis
    print("\n3. Testing Volume Momentum Analysis...")
    try:
        volume_analysis = indicator_engine.volume_analyzer.analyze_volume_momentum(
            test_data['AAPL']
        )
        
        print(f"✅ Volume momentum analysis completed")
        for key, value in volume_analysis.items():
            print(f"   {key}: {value:.4f}")
        
    except Exception as e:
        print(f"❌ Volume momentum analysis failed: {e}")
        return False
    
    return True

def test_enhanced_signal_generator():
    """Test the enhanced signal generator"""
    print("\n=== Testing Enhanced Signal Generator ===")
    
    # Create test data
    test_data = create_test_data()
    
    # Initialize signal generator
    config = AcademicSignalConfig()
    signal_generator = EnhancedSignalGenerator(config)
    
    # Test academic momentum signal generation
    print("\n1. Testing Academic Momentum Signal Generation...")
    try:
        combined_signals = signal_generator.generate_academic_momentum_signals(
            test_data, test_data['SPY']
        )
        
        print(f"✅ Combined signals generated successfully")
        print(f"   Symbols with signals: {len(combined_signals)}")
        
        for symbol, signal in combined_signals.items():
            print(f"   {symbol}: {signal:.4f}")
            
            # Validate signal range (should be reasonable)
            if -5.0 <= signal <= 5.0:
                print(f"     ✅ Signal in reasonable range")
            else:
                print(f"     ⚠️  Signal outside expected range: {signal}")
        
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return False
    
    # Test signal combination methods
    print("\n2. Testing Signal Combination Methods...")
    try:
        # Test multi-horizon combination
        test_indicators = {
            'momentum_1w': 0.5,
            'momentum_1m': 0.8,
            'momentum_3m': 1.2,
            'momentum_6m': 0.9
        }
        
        combined = signal_generator._combine_multi_horizon_signals(test_indicators)
        print(f"✅ Multi-horizon combination: {combined:.4f}")
        
        # Test volume weighting
        volume_adjusted = signal_generator._apply_volume_weighting(
            {'volume_weighted_momentum': 0.3, 'high_volume_momentum': 0.2}, 
            combined
        )
        print(f"✅ Volume-weighted adjustment: {volume_adjusted:.4f}")
        
    except Exception as e:
        print(f"❌ Signal combination failed: {e}")
        return False
    
    return True

def test_benchmark_analyzer():
    """Test the benchmark analyzer"""
    print("\n=== Testing Benchmark Analyzer ===")
    
    # Create test returns data
    np.random.seed(42)
    n_days = 252 * 2  # 2 years
    
    # Strategy returns (slightly better than market)
    strategy_returns = pd.Series(np.random.normal(0.001, 0.02, n_days))
    
    # SPY returns (market benchmark)
    spy_returns = pd.Series(np.random.normal(0.0008, 0.015, n_days))
    
    # Initialize benchmark analyzer
    config = BenchmarkConfig()
    analyzer = BenchmarkAnalyzer(config)
    
    # Test benchmark metrics calculation
    print("\n1. Testing Benchmark Metrics Calculation...")
    try:
        metrics = analyzer.calculate_benchmark_metrics(strategy_returns, spy_returns)
        
        print(f"✅ Benchmark metrics calculated successfully")
        
        # Display key metrics
        key_metrics = [
            'information_ratio', 'sharpe_ratio', 'tracking_error', 
            'beta', 'excess_return', 'max_strategy_drawdown'
        ]
        
        for metric in key_metrics:
            if metric in metrics:
                print(f"   {metric}: {metrics[metric]:.4f}")
            else:
                print(f"   ❌ {metric}: Missing")
        
    except Exception as e:
        print(f"❌ Benchmark metrics calculation failed: {e}")
        return False
    
    # Test optimization analysis
    print("\n2. Testing Optimization Analysis...")
    try:
        optimization = analyzer.optimize_for_benchmark(strategy_returns, spy_returns)
        
        print(f"✅ Optimization analysis completed")
        print(f"   Optimization score: {optimization['optimization_score']:.4f}")
        
        # Check constraints
        constraints = optimization['constraints_met']
        for constraint, met in constraints.items():
            status = "✅" if met else "❌"
            print(f"   {status} {constraint}: {met}")
        
    except Exception as e:
        print(f"❌ Optimization analysis failed: {e}")
        return False
    
    return True

def main():
    """Run all Phase 1 tests"""
    print("🚀 Phase 1: Core System Enhancements Tests")
    print("=" * 60)
    
    tests = [
        ("Enhanced Technical Indicators", test_enhanced_technical_indicators),
        ("Enhanced Signal Generator", test_enhanced_signal_generator),
        ("Benchmark Analyzer", test_benchmark_analyzer)
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
        print("🎉 Phase 1 Implementation: SUCCESS")
        print("\n✅ Core system enhancements are ready!")
        print("✅ Enhanced technical indicators with academic foundations")
        print("✅ Academic signal generation and combination")
        print("✅ SPY benchmark analysis and optimization")
        print("✅ Ready for Phase 2: Backtesting Framework Integration")
    else:
        print("❌ Phase 1 Implementation: FAILED")
        print("Please fix the failing tests before proceeding to Phase 2")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 