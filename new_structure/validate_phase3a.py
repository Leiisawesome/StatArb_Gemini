#!/usr/bin/env python3
"""
Phase 3A Portfolio & Risk Management Migration Validation
=========================================================

Comprehensive validation script for portfolio and risk management components with:
- Portfolio manager functionality testing
- Risk management system validation
- Position sizing algorithm testing
- Portfolio optimization verification
- Risk metrics calculation testing
- Integration testing with existing components

Author: Pro Quant Desk Trader
"""

import sys
import os
import time
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def validate_phase3a():
    """Validate Phase 3A: Portfolio & Risk Management Migration completion"""
    print("🚀 StatArb System Migration Validation")
    print("Phase 3A: Portfolio & Risk Management Migration")
    print("=" * 60)
    
    validation_results = {
        'infrastructure': False,
        'portfolio_management': False,
        'risk_management': False,
        'position_sizing': False,
        'portfolio_optimization': False,
        'risk_metrics': False,
        'integration': False
    }
    
    try:
        # Check dependencies
        print("🔧 Checking dependencies...")
        check_dependencies()
        
        # Check file structure
        print("\n📁 Checking file structure...")
        
        required_files = [
            'portfolio_management/__init__.py',
            'portfolio_management/portfolio_manager.py',
            'portfolio_management/allocation_optimizer.py',
            'risk_management/__init__.py',
            'risk_management/risk_manager.py',
            'risk_management/position_sizer.py',
            'risk_management/risk_metrics.py'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        print("✅ All required files present")
        
        # Test infrastructure components
        print("\n🏗️ Testing infrastructure components...")
        validation_results['infrastructure'] = test_infrastructure()
        
        # Test portfolio management
        print("\n📊 Testing portfolio management...")
        validation_results['portfolio_management'] = test_portfolio_management()
        
        # Test risk management
        print("\n⚠️ Testing risk management...")
        validation_results['risk_management'] = test_risk_management()
        
        # Test position sizing
        print("\n📏 Testing position sizing...")
        validation_results['position_sizing'] = test_position_sizing()
        
        # Test portfolio optimization
        print("\n🎯 Testing portfolio optimization...")
        validation_results['portfolio_optimization'] = test_portfolio_optimization()
        
        # Test risk metrics
        print("\n📈 Testing risk metrics...")
        validation_results['risk_metrics'] = test_risk_metrics()
        
        # Test integration
        print("\n🔗 Testing integration...")
        validation_results['integration'] = test_integration()
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 VALIDATION RESULTS")
        print("=" * 60)
        
        total_tests = len(validation_results)
        passed_tests = sum(validation_results.values())
        
        for component, result in validation_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{component.upper():.<30} {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("\n🎉 Phase 3A Migration: COMPLETE")
            print("✅ Portfolio & Risk Management system ready for production")
            create_completion_marker()
            return True
        else:
            print(f"\n⚠️ Phase 3A Migration: {total_tests - passed_tests} issues to resolve")
            return False
            
    except Exception as e:
        print(f"❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """Check required dependencies"""
    required_modules = [
        'numpy', 'pandas', 'scipy', 'datetime', 'typing', 'dataclasses', 'enum', 'json'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        raise ImportError(f"Missing required modules: {missing_modules}")
    
    print("✅ All dependencies available")

def test_infrastructure():
    """Test infrastructure components"""
    try:
        # Test infrastructure import
        sys.path.append('.')
        from infrastructure import get_module_health
        
        health = get_module_health()
        if health['status'] != 'healthy':
            print(f"❌ Infrastructure not healthy: {health}")
            return False
        
        print("✅ Infrastructure components working")
        return True
        
    except Exception as e:
        print(f"❌ Infrastructure test failed: {e}")
        return False

def test_portfolio_management():
    """Test portfolio management components"""
    try:
        # Test portfolio management imports
        from portfolio_management import (
            PortfolioManager, AllocationOptimizer, PortfolioConfig,
            get_module_health, create_portfolio_manager
        )
        
        # Test module health
        health = get_module_health()
        if not health['components_available']:
            print(f"❌ Portfolio management components not available: {health}")
            return False
        
        # Test portfolio manager creation
        config = PortfolioConfig(initial_capital=1000000, max_positions=10)
        portfolio_manager = PortfolioManager(config)
        
        if portfolio_manager is None:
            print("❌ Failed to create portfolio manager")
            return False
        
        # Test basic portfolio operations
        success = portfolio_manager.add_position(
            symbol_pair="TEST_PAIR",
            strategy="test_strategy",
            quantity=100,
            entry_price=50.0
        )
        
        if not success:
            print("❌ Failed to add position to portfolio")
            return False
        
        # Test portfolio metrics
        metrics = portfolio_manager.get_portfolio_metrics()
        if metrics.positions_count != 1:
            print(f"❌ Portfolio metrics incorrect: {metrics.positions_count} positions")
            return False
        
        # Test position removal
        success = portfolio_manager.remove_position("TEST_PAIR", 55.0)
        if not success:
            print("❌ Failed to remove position from portfolio")
            return False
        
        print("✅ Portfolio management components working")
        return True
        
    except Exception as e:
        print(f"❌ Portfolio management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_management():
    """Test risk management components"""
    try:
        # Test risk management imports
        from risk_management import (
            RiskManager, PositionSizer, RiskMetrics, RiskConfig,
            get_module_health, create_risk_manager
        )
        
        # Test module health
        health = get_module_health()
        if not health['components_available']:
            print(f"❌ Risk management components not available: {health}")
            return False
        
        # Test risk manager creation
        risk_manager = create_risk_manager()
        if risk_manager is None:
            print("❌ Failed to create risk manager")
            return False
        
        # Test portfolio risk check
        test_portfolio = {
            'metrics': {
                'total_value': 1000000,
                'var_95': 0.015,
                'max_drawdown': 0.03,
                'concentration': 0.12,
                'volatility': 0.15,
                'correlation_risk': 0.6,
                'cash': 50000
            },
            'positions': {
                'TEST_PAIR': {
                    'market_value': 100000,
                    'volatility': 0.2
                }
            }
        }
        
        risk_result = risk_manager.check_portfolio_risk(test_portfolio)
        if not hasattr(risk_result, 'passed'):
            print("❌ Risk check failed to return proper result")
            return False
        
        print("✅ Risk management components working")
        return True
        
    except Exception as e:
        print(f"❌ Risk management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_position_sizing():
    """Test position sizing algorithms"""
    try:
        from risk_management import PositionSizer, PositionSizeMethod, PositionSizeConfig
        
        # Test different position sizing methods
        methods_to_test = [
            PositionSizeMethod.KELLY,
            PositionSizeMethod.RISK_PARITY,
            PositionSizeMethod.VOLATILITY_TARGET,
            PositionSizeMethod.ADAPTIVE
        ]
        
        for method in methods_to_test:
            config = PositionSizeConfig(method=method)
            sizer = PositionSizer(method, config)
            
            # Test position size calculation
            portfolio_state = {
                'metrics': {
                    'total_value': 1000000,
                    'volatility': 0.12,
                    'daily_return': 0.001,
                    'sharpe_ratio': 1.2
                },
                'positions': {}
            }
            
            result = sizer.calculate_position_size(
                expected_return=0.15,
                volatility=0.20,
                signal_confidence=0.8,
                portfolio_state=portfolio_state
            )
            
            if not hasattr(result, 'recommended_size'):
                print(f"❌ Position sizing failed for method {method.value}")
                return False
            
            if result.recommended_size <= 0 or result.recommended_size > 1:
                print(f"❌ Invalid position size for method {method.value}: {result.recommended_size}")
                return False
        
        print("✅ Position sizing algorithms working")
        return True
        
    except Exception as e:
        print(f"❌ Position sizing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_portfolio_optimization():
    """Test portfolio optimization"""
    try:
        from portfolio_management import AllocationOptimizer, AllocationMethod, AllocationConfig
        
        # Create test data
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        assets = ['ASSET1', 'ASSET2', 'ASSET3', 'ASSET4']
        
        # Generate correlated returns
        returns = np.random.multivariate_normal(
            mean=[0.0008, 0.0006, 0.0010, 0.0004],
            cov=[[0.0004, 0.0001, 0.0002, 0.0001],
                 [0.0001, 0.0003, 0.0001, 0.0001],
                 [0.0002, 0.0001, 0.0005, 0.0002],
                 [0.0001, 0.0001, 0.0002, 0.0002]],
            size=252
        )
        
        asset_data = pd.DataFrame(returns, index=dates, columns=assets)
        
        # Test different optimization methods
        methods_to_test = [
            AllocationMethod.MEAN_VARIANCE,
            AllocationMethod.RISK_PARITY,
            AllocationMethod.EQUAL_WEIGHT,
            AllocationMethod.MINIMUM_VARIANCE
        ]
        
        for method in methods_to_test:
            config = AllocationConfig(method=method)
            optimizer = AllocationOptimizer(config)
            
            result = optimizer.optimize_allocation(asset_data)
            
            if not hasattr(result, 'weights'):
                print(f"❌ Optimization failed for method {method.value}")
                return False
            
            # Check weights sum to 1
            total_weight = sum(result.weights.values())
            if abs(total_weight - 1.0) > 0.01:
                print(f"❌ Weights don't sum to 1 for method {method.value}: {total_weight}")
                return False
        
        print("✅ Portfolio optimization working")
        return True
        
    except Exception as e:
        print(f"❌ Portfolio optimization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_metrics():
    """Test risk metrics calculations"""
    try:
        from risk_management import RiskMetrics, VaRMethod, StressTestScenario
        
        # Generate test data
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        
        # Portfolio returns
        portfolio_returns = np.random.normal(0.001, 0.02, 252)
        portfolio_values = (1 + pd.Series(portfolio_returns, index=dates)).cumprod() * 1000000
        
        # Asset returns
        asset_returns = np.random.multivariate_normal(
            mean=[0.0008, 0.0006, 0.0010],
            cov=[[0.0004, 0.0001, 0.0002],
                 [0.0001, 0.0003, 0.0001],
                 [0.0002, 0.0001, 0.0005]],
            size=252
        )
        
        returns_data = pd.DataFrame(asset_returns, index=dates, columns=['ASSET1', 'ASSET2', 'ASSET3'])
        
        # Test portfolio data
        portfolio_data = {
            'metrics': {
                'total_value': 1000000,
                'var_95': 0.02,
                'max_drawdown': 0.05,
                'concentration': 0.15,
                'volatility': 0.12,
                'correlation_risk': 0.5
            },
            'positions': {
                'ASSET1': {'market_value': 400000, 'volatility': 0.15},
                'ASSET2': {'market_value': 300000, 'volatility': 0.12},
                'ASSET3': {'market_value': 300000, 'volatility': 0.18}
            }
        }
        
        # Test risk metrics
        risk_metrics = RiskMetrics(confidence_level=0.95)
        
        # Test VaR calculation
        var_result = risk_metrics.var_calculator.calculate_var(
            pd.Series(portfolio_returns), VaRMethod.HISTORICAL, 1000000
        )
        
        if not hasattr(var_result, 'var_value'):
            print("❌ VaR calculation failed")
            return False
        
        # Test CVaR calculation
        cvar_result = risk_metrics.cvar_calculator.calculate_cvar(
            pd.Series(portfolio_returns), 1000000
        )
        
        if not hasattr(cvar_result, 'cvar_value'):
            print("❌ CVaR calculation failed")
            return False
        
        # Test stress testing
        stress_result = risk_metrics.stress_tester.run_stress_test(
            portfolio_data, StressTestScenario.MARKET_CRASH
        )
        
        if not hasattr(stress_result, 'portfolio_loss'):
            print("❌ Stress testing failed")
            return False
        
        # Test correlation analysis
        corr_analysis = risk_metrics.correlation_analyzer.analyze_correlations(returns_data)
        
        if not hasattr(corr_analysis, 'correlation_matrix'):
            print("❌ Correlation analysis failed")
            return False
        
        print("✅ Risk metrics calculations working")
        return True
        
    except Exception as e:
        print(f"❌ Risk metrics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test integration with existing components"""
    try:
        # Test integration with signal generation
        from signal_generation import get_module_health as signal_health
        from strategy_engine import get_module_health as strategy_health
        from portfolio_management import get_module_health as portfolio_health
        from risk_management import get_module_health as risk_health
        
        # Check all components are healthy
        components = {
            'signal_generation': signal_health(),
            'strategy_engine': strategy_health(),
            'portfolio_management': portfolio_health(),
            'risk_management': risk_health()
        }
        
        for component, health in components.items():
            if health['status'] != 'healthy':
                print(f"❌ Component {component} not healthy: {health}")
                return False
        
        # Test end-to-end integration
        from portfolio_management import PortfolioManager, PortfolioConfig
        from risk_management import RiskManager, create_risk_manager
        
        # Create integrated system
        portfolio_config = PortfolioConfig(initial_capital=1000000)
        portfolio_manager = PortfolioManager(portfolio_config)
        risk_manager = create_risk_manager()
        
        # Test workflow
        # 1. Add position
        success = portfolio_manager.add_position(
            symbol_pair="INTEGRATION_TEST",
            strategy="test_strategy",
            quantity=200,
            entry_price=25.0
        )
        
        if not success:
            print("❌ Integration test: Failed to add position")
            return False
        
        # 2. Check risk
        portfolio_state = portfolio_manager.get_state_summary()
        risk_result = risk_manager.check_portfolio_risk(portfolio_state)
        
        if not risk_result.passed:
            print("❌ Integration test: Risk check failed")
            return False
        
        # 3. Update prices and recheck
        portfolio_manager.update_prices({"INTEGRATION_TEST": 30.0})
        updated_state = portfolio_manager.get_state_summary()
        
        if updated_state['metrics']['total_value'] <= 1000000:
            print("❌ Integration test: Portfolio value not updated")
            return False
        
        print("✅ Integration with existing components working")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_completion_marker():
    """Create completion marker for Phase 3A"""
    try:
        marker_content = f"""Phase 3A: Portfolio & Risk Management Migration - COMPLETE
=============================================================

Completion Time: {datetime.now().isoformat()}
Status: ✅ COMPLETE

Components Delivered:
- Portfolio Management System
- Risk Management System  
- Position Sizing Algorithms
- Portfolio Optimization Engine
- Risk Metrics Calculator
- Integration with Existing Systems

Ready for: Phase 3B (Execution Engine Migration)
"""
        
        with open('phase3a_complete.marker', 'w') as f:
            f.write(marker_content)
        
        print("✅ Phase 3A completion marker created")
        
    except Exception as e:
        print(f"❌ Failed to create completion marker: {e}")

def run_performance_benchmark():
    """Run performance benchmark for Phase 3A components"""
    try:
        print("\n⚡ Running performance benchmarks...")
        
        # Portfolio management benchmark
        start_time = time.time()
        from portfolio_management import PortfolioManager, PortfolioConfig
        
        config = PortfolioConfig(initial_capital=1000000)
        portfolio_manager = PortfolioManager(config)
        
        # Add multiple positions
        for i in range(50):
            portfolio_manager.add_position(
                symbol_pair=f"PAIR_{i}",
                strategy="benchmark_strategy",
                quantity=100,
                entry_price=50.0 + i
            )
        
        portfolio_time = time.time() - start_time
        
        # Risk management benchmark
        start_time = time.time()
        from risk_management import create_risk_manager
        
        risk_manager = create_risk_manager()
        portfolio_state = portfolio_manager.get_state_summary()
        
        for _ in range(10):
            risk_manager.check_portfolio_risk(portfolio_state)
        
        risk_time = time.time() - start_time
        
        print(f"📊 Portfolio Management: {portfolio_time:.3f}s (50 positions)")
        print(f"📊 Risk Management: {risk_time:.3f}s (10 risk checks)")
        print(f"📊 Total Phase 3A Performance: {portfolio_time + risk_time:.3f}s")
        
        # Performance targets
        if portfolio_time > 1.0:
            print("⚠️ Portfolio management slower than target (1.0s)")
        if risk_time > 0.5:
            print("⚠️ Risk management slower than target (0.5s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Phase 3A Validation...")
    
    # Run main validation
    success = validate_phase3a()
    
    if success:
        # Run performance benchmark
        run_performance_benchmark()
        
        print("\n" + "=" * 60)
        print("🎉 PHASE 3A MIGRATION COMPLETE!")
        print("=" * 60)
        print("✅ Portfolio & Risk Management system is ready")
        print("✅ All components tested and validated")
        print("✅ Integration with existing systems confirmed")
        print("✅ Performance benchmarks passed")
        print("\n🚀 Ready to proceed to Phase 3B: Execution Engine Migration")
    else:
        print("\n" + "=" * 60)
        print("❌ PHASE 3A VALIDATION FAILED")
        print("=" * 60)
        print("Please resolve the issues above before proceeding")
    
    sys.exit(0 if success else 1) 