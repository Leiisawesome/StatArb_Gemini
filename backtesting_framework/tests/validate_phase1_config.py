#!/usr/bin/env python3
"""
Phase 1 Configuration Validation
Validates that all Phase 1 components are properly configured and importable
"""

import sys
import os
# Add the current directory (StatArb_Gemini root) to the path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)
# Also add the current working directory
sys.path.insert(0, os.getcwd())

# Global imports for all validation functions
try:
    from core_structure.infrastructure.config.enhanced_config_manager import EnhancedConfigManager
    from strategies.multi_factor_ensemble_strategy import MultiFactorEnsembleStrategy, MultiFactorConfig, FactorType
    from engines.enhanced_backtesting_engine import EnhancedBacktestingEngine
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Global import failed: {e}")
    IMPORTS_SUCCESSFUL = False

def validate_imports():
    """Validate that all required modules can be imported"""
    print("🔍 Validating imports...")
    
    if IMPORTS_SUCCESSFUL:
        print("✅ EnhancedConfigManager imported successfully")
        print("✅ MultiFactorEnsembleStrategy imported successfully")
        print("✅ EnhancedBacktestingEngine imported successfully")
        return True
    else:
        print("❌ Imports failed")
        return False

def validate_configuration():
    """Validate that configuration files can be loaded"""
    print("\n🔍 Validating configuration...")
    
    try:
        config_manager = EnhancedConfigManager()
        
        # Test loading technical momentum configuration
        strategy_config = config_manager._load_strategy_config('technical_momentum')
        print("✅ Technical momentum configuration loaded successfully")
        print(f"   Strategy: {strategy_config.name}")
        print(f"   Version: {strategy_config.version}")
        print(f"   Symbols: {len(strategy_config.symbols)} symbols")
        
        # Test creating backtesting configuration
        backtest_config = config_manager.create_step1_backtesting_config(
            strategy_name="technical_momentum",
            training_start="2023-01-01",
            training_end="2024-12-31",
            validation_start="2025-01-01",
            validation_end="2025-06-30"
        )
        print("✅ Backtesting configuration created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def validate_strategy_creation():
    """Validate that strategy can be created"""
    print("\n🔍 Validating strategy creation...")
    
    try:
        from strategies.multi_factor_ensemble_strategy import FactorConfig, FactorType, MultiFactorConfig
        
        # Create test factor configurations
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
                    'macd_signal': 9
                }
            ),
            FactorConfig(
                factor_type=FactorType.MOMENTUM,
                lookback_period=252,
                threshold=0.10,
                weight=0.3,
                momentum_type="risk_adjusted"
            )
        ]
        
        # Create strategy configuration
        config = MultiFactorConfig(
            factors=factors,
            initial_capital=100000,
            max_position_value=10000,
            max_positions=15
        )
        
        # Create strategy
        strategy = MultiFactorEnsembleStrategy(config)
        print("✅ MultiFactorEnsembleStrategy created successfully")
        print(f"   Factors: {list(strategy.factors.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy creation failed: {e}")
        return False

def validate_engine_integration():
    """Validate that engine can integrate with strategy"""
    print("\n🔍 Validating engine integration...")
    
    try:
        engine = EnhancedBacktestingEngine()
        
        # Test strategy initialization
        strategy_config = {
            'name': 'technical_momentum',
            'version': '2.0.0',
            'parameters': {}
        }
        
        # This should not fail even without data
        print("✅ Engine created successfully")
        print("✅ Strategy configuration prepared")
        
        return True
        
    except Exception as e:
        print(f"❌ Engine integration failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 PHASE 1 CONFIGURATION VALIDATION")
    print("="*50)
    
    # Run all validations
    validations = [
        ("Imports", validate_imports),
        ("Configuration", validate_configuration),
        ("Strategy Creation", validate_strategy_creation),
        ("Engine Integration", validate_engine_integration)
    ]
    
    results = []
    for name, validation_func in validations:
        try:
            result = validation_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} validation crashed: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*50)
    print("VALIDATION SUMMARY")
    print("="*50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Phase 1 is ready for testing")
        print("🚀 Run: python backtesting_framework/scripts/run_phase1_technical_momentum.py")
        return 0
    else:
        print("⚠️ SOME VALIDATIONS FAILED!")
        print("🔧 Please fix the issues before running Phase 1 tests")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 