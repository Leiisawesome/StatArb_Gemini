#!/usr/bin/env python3
"""
Production cleanup validation script
"""

import os
import sys
from pathlib import Path

def check_module_structure():
    """Validate the production module structure"""
    print("Checking production module structure...")
    
    required_files = [
        'src/__init__.py',
        'src/config/__init__.py',
        'src/data/__init__.py',
        'src/data/clickhouse_connector.py',
        'src/strategy/__init__.py',
        'src/backtesting/__init__.py',
        'src/risk/__init__.py',
        'src/utils/__init__.py',
        'scripts/run_backtest.py',
        'scripts/quick_start.py',
        'README.md'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✓ {file_path}")
    
    if missing_files:
        print("\n❌ Missing files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print("\n✅ All required files present")
    return True

def check_imports():
    """Test all module imports"""
    print("\nChecking module imports...")
    
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    import_tests = [
        ('config', 'ConfigManager, load_config, PRESET_CONFIGS'),
        ('strategy', 'ModernMomentumStrategy, BaseStrategy'),
        ('backtesting', 'MomentumBacktest, BacktestResults'),
        ('risk', 'RiskManager'),
        ('utils', 'PerformanceAnalyzer'),
        ('data.clickhouse_connector', 'ClickHouseDataLoader')
    ]
    
    failed_imports = []
    for module, components in import_tests:
        try:
            exec(f"from {module} import {components}")
            print(f"✓ {module}: {components}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed_imports.append((module, str(e)))
    
    if failed_imports:
        print(f"\n❌ {len(failed_imports)} import failures")
        return False
    
    print("\n✅ All imports successful")
    return True

def check_configuration():
    """Test configuration system"""
    print("\nChecking configuration system...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from config import ConfigManager, PRESET_CONFIGS
        
        # Test default config
        config = ConfigManager(environment="development")
        print("✓ Default configuration loaded")
        
        # Test preset configs
        for preset_name in PRESET_CONFIGS:
            config_copy = ConfigManager(environment="development")
            config_copy.update(PRESET_CONFIGS[preset_name])
            print(f"✓ Preset '{preset_name}' applied successfully")
        
        # Test configuration validation
        test_config = {
            "data": {
                "training_start": "2023-01-01",
                "training_end": "2023-12-31",
                "testing_start": "2024-01-01", 
                "testing_end": "2024-06-30"
            }
        }
        config.update(test_config)
        print("✓ Configuration validation working")
        
        print("\n✅ Configuration system functional")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")
        return False

def check_strategy_system():
    """Test strategy system"""
    print("\nChecking strategy system...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from strategy import ModernMomentumStrategy, BaseStrategy
        from config import ConfigManager
        
        # Test strategy initialization
        config = ConfigManager(environment="development")
        strategy = ModernMomentumStrategy(config.get_all())
        print("✓ ModernMomentumStrategy initialization")
        
        # Test abstract base class
        assert hasattr(BaseStrategy, 'generate_signals')
        assert hasattr(BaseStrategy, 'calculate_scores')
        print("✓ BaseStrategy interface validation")
        
        print("\n✅ Strategy system functional")
        return True
        
    except Exception as e:
        print(f"\n❌ Strategy system error: {e}")
        return False

def check_backtest_system():
    """Test backtesting system"""
    print("\nChecking backtesting system...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from backtesting import MomentumBacktest, BacktestResults
        from strategy import ModernMomentumStrategy
        from risk import RiskManager
        from config import ConfigManager
        
        # Test component initialization
        config = ConfigManager(environment="development")
        strategy = ModernMomentumStrategy(config.get_all())
        risk_manager = RiskManager(config.get_all())
        backtest = MomentumBacktest(strategy, risk_manager, config.get_all())
        print("✓ MomentumBacktest initialization")
        
        # Test BacktestResults class
        results = BacktestResults()
        assert hasattr(results, 'portfolio_history')
        assert hasattr(results, 'trade_history')
        print("✓ BacktestResults class validation")
        
        print("\n✅ Backtesting system functional")
        return True
        
    except Exception as e:
        print(f"\n❌ Backtesting system error: {e}")
        return False

def check_risk_system():
    """Test risk management system"""
    print("\nChecking risk management system...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from risk import RiskManager
        from config import ConfigManager
        
        # Test risk manager initialization
        config = ConfigManager(environment="development")
        risk_manager = RiskManager(config.get_all())
        print("✓ RiskManager initialization")
        
        # Test key methods exist
        assert hasattr(risk_manager, 'calculate_position_sizes')
        assert hasattr(risk_manager, 'check_portfolio_risk')
        print("✓ RiskManager interface validation")
        
        print("\n✅ Risk management system functional")
        return True
        
    except Exception as e:
        print(f"\n❌ Risk management error: {e}")
        return False

def check_analytics_system():
    """Test analytics system"""
    print("\nChecking analytics system...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from utils import PerformanceAnalyzer
        
        # Test analyzer initialization
        analyzer = PerformanceAnalyzer()
        print("✓ PerformanceAnalyzer initialization")
        
        # Test key methods exist
        assert hasattr(analyzer, 'calculate_metrics')
        print("✓ PerformanceAnalyzer interface validation")
        
        print("\n✅ Analytics system functional")
        return True
        
    except Exception as e:
        print(f"\n❌ Analytics system error: {e}")
        return False

def generate_production_report():
    """Generate production readiness report"""
    print("\n" + "="*60)
    print("PRODUCTION CLEANUP VALIDATION REPORT")
    print("="*60)
    
    checks = [
        ("Module Structure", check_module_structure),
        ("Import System", check_imports),
        ("Configuration", check_configuration),
        ("Strategy System", check_strategy_system),
        ("Backtesting System", check_backtest_system),
        ("Risk Management", check_risk_system),
        ("Analytics System", check_analytics_system)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:20} {status}")
    
    print("\n" + "-"*60)
    print(f"Overall: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 PRODUCTION CLEANUP COMPLETED SUCCESSFULLY!")
        print("✅ All systems validated and ready for production use")
        print("\nNext steps:")
        print("1. Run: python scripts/quick_start.py --test")
        print("2. Run: python scripts/quick_start.py --example")
        print("3. Run: python scripts/run_backtest.py --preset quick_test")
    else:
        print(f"\n⚠️  PRODUCTION CLEANUP INCOMPLETE")
        print(f"❌ {total - passed} systems require attention")
        print("\nPlease address the failed checks before production deployment")
    
    print("="*60)
    return passed == total

def main():
    """Main validation entry point"""
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    success = generate_production_report()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
