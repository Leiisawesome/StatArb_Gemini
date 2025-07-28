#!/usr/bin/env python3
"""
Test Phase 0: Configuration Architecture Enhancement
Validates the enhanced configuration manager and validation system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_structure.infrastructure.config.enhanced_config_manager import (
    EnhancedConfigManager, EnhancedConfig, Environment
)
from core_structure.infrastructure.config.config_validator import ConfigValidator
import yaml
import json

def test_enhanced_config_manager():
    """Test the enhanced configuration manager"""
    print("=== Testing Enhanced Configuration Manager ===")
    
    # Initialize config manager
    config_manager = EnhancedConfigManager("backtesting_framework/configs/strategies")
    
    # Test Step 1 configuration creation
    print("\n1. Testing Step 1 Backtesting Configuration...")
    try:
        step1_config = config_manager.create_step1_backtesting_config(
            strategy_name="enhanced_momentum",
            training_start="2023-01-01",
            training_end="2024-12-31",
            validation_start="2025-01-01",
            validation_end="2025-06-30"
        )
        
        print(f"✅ Step 1 config created successfully")
        print(f"   Environment: {step1_config.environment.value}")
        print(f"   Strategy: {step1_config.strategy.name}")
        print(f"   Training period: {step1_config.training.start_date} to {step1_config.training.end_date}")
        print(f"   Trading period: {step1_config.trading.start_date} to {step1_config.trading.end_date}")
        
    except Exception as e:
        print(f"❌ Step 1 config creation failed: {e}")
        return False
    
    # Test Step 2 configuration creation
    print("\n2. Testing Step 2 Real-time Configuration...")
    try:
        step2_config = config_manager.create_step2_realtime_config(
            strategy_name="enhanced_momentum",
            trading_start="2025-07-01"
        )
        
        print(f"✅ Step 2 config created successfully")
        print(f"   Environment: {step2_config.environment.value}")
        print(f"   Strategy: {step2_config.strategy.name}")
        print(f"   Trading period: {step2_config.trading.start_date} (ongoing)")
        
    except Exception as e:
        print(f"❌ Step 2 config creation failed: {e}")
        return False
    
    # Test parameter persistence
    print("\n3. Testing Parameter Persistence...")
    try:
        # Save optimized parameters
        test_parameters = {
            'momentum_lookback_short': 5,
            'momentum_lookback_medium': 21,
            'momentum_lookback_long': 63,
            'volume_weight': 0.3,
            'signal_threshold': 0.7
        }
        
        test_performance = {
            'sharpe_ratio': 1.8,
            'max_drawdown': -0.12,
            'information_ratio': 1.2
        }
        
        config_manager.current_config = step1_config
        config_manager.save_optimized_parameters(
            "enhanced_momentum",
            test_parameters,
            test_performance
        )
        
        # Load optimized parameters
        loaded_params = config_manager._load_optimized_parameters("enhanced_momentum")
        
        if loaded_params == test_parameters:
            print("✅ Parameter persistence working correctly")
        else:
            print(f"❌ Parameter persistence failed: {loaded_params} != {test_parameters}")
            return False
            
    except Exception as e:
        print(f"❌ Parameter persistence test failed: {e}")
        return False
    
    return True

def test_config_validator():
    """Test the configuration validator"""
    print("\n=== Testing Configuration Validator ===")
    
    validator = ConfigValidator()
    
    # Test valid strategy config
    print("\n1. Testing Valid Strategy Configuration...")
    valid_strategy = {
        'name': 'test_strategy',
        'version': '1.0.0',
        'parameters': {
            'momentum_lookback_short': 5,
            'momentum_lookback_medium': 21,
            'momentum_lookback_long': 63,
            'volume_weight': 0.3,
            'signal_threshold': 0.7,
            'position_size': 0.1,
            'max_positions': 10
        },
        'risk_limits': {
            'max_daily_loss': 0.02,
            'max_drawdown': 0.15,
            'max_position_value': 5000000
        },
        'timeframes': ['1min', '5min', '1hour'],
        'symbols': ['AAPL', 'MSFT', 'GOOGL']
    }
    
    errors = validator.validate_strategy_config(valid_strategy)
    if len(errors) == 0:
        print("✅ Valid strategy config passed validation")
    else:
        print(f"❌ Valid strategy config failed validation: {len(errors)} errors")
        validator.print_validation_errors(errors)
        return False
    
    # Test invalid strategy config
    print("\n2. Testing Invalid Strategy Configuration...")
    invalid_strategy = {
        'name': 'test_strategy',
        'version': '1.0.0',
        'parameters': {
            'momentum_lookback_short': 100,  # Invalid: too high
            'volume_weight': 1.5,  # Invalid: > 1.0
            'signal_threshold': -0.5  # Invalid: negative
        },
        'risk_limits': {
            'max_daily_loss': 0.5,  # Invalid: too high
            'max_drawdown': 0.8  # Invalid: too high
        },
        'timeframes': ['1min', '5min', '1hour'],
        'symbols': ['AAPL', 'MSFT', 'GOOGL']
    }
    
    errors = validator.validate_strategy_config(invalid_strategy)
    if len(errors) > 0:
        print(f"✅ Invalid strategy config correctly caught {len(errors)} errors")
        validator.print_validation_errors(errors)
    else:
        print("❌ Invalid strategy config should have failed validation")
        return False
    
    # Test enhanced config validation
    print("\n3. Testing Enhanced Configuration Validation...")
    valid_enhanced_config = {
        'environment': 'backtesting',
        'strategy': valid_strategy,
        'training': {
            'start_date': '2023-01-01',
            'end_date': '2024-12-31',
            'validation_split': 0.2,
            'optimization_method': 'grid_search'
        },
        'trading': {
            'start_date': '2025-01-01',
            'end_date': '2025-06-30',
            'real_time': False,
            'execution_mode': 'simulation',
            'position_sizing': 'fixed'
        }
    }
    
    errors = validator.validate_enhanced_config(valid_enhanced_config)
    if len(errors) == 0:
        print("✅ Valid enhanced config passed validation")
    else:
        print(f"❌ Valid enhanced config failed validation: {len(errors)} errors")
        validator.print_validation_errors(errors)
        return False
    
    return True

def test_strategy_config_files():
    """Test loading strategy configuration files"""
    print("\n=== Testing Strategy Configuration Files ===")
    
    # Test enhanced momentum strategy config
    print("\n1. Testing Enhanced Momentum Strategy Config...")
    try:
        with open("backtesting_framework/configs/strategies/enhanced_momentum_strategy.yaml", 'r') as f:
            enhanced_config = yaml.safe_load(f)
        
        print(f"✅ Enhanced momentum config loaded successfully")
        print(f"   Name: {enhanced_config['name']}")
        print(f"   Version: {enhanced_config['version']}")
        print(f"   Academic basis: {len(enhanced_config['academic_basis'])} theories")
        print(f"   Parameters: {len(enhanced_config['parameters'])} parameters")
        print(f"   Symbols: {len(enhanced_config['symbols'])} symbols")
        
    except Exception as e:
        print(f"❌ Enhanced momentum config loading failed: {e}")
        return False
    
    # Test technical momentum strategy config
    print("\n2. Testing Technical Momentum Strategy Config...")
    try:
        with open("backtesting_framework/configs/strategies/technical_momentum_strategy.yaml", 'r') as f:
            technical_config = yaml.safe_load(f)
        
        print(f"✅ Technical momentum config loaded successfully")
        print(f"   Name: {technical_config['name']}")
        print(f"   Version: {technical_config['version']}")
        print(f"   Parameters: {len(technical_config['parameters'])} parameters")
        print(f"   Symbols: {len(technical_config['symbols'])} symbols")
        
    except Exception as e:
        print(f"❌ Technical momentum config loading failed: {e}")
        return False
    
    return True

def main():
    """Run all Phase 0 tests"""
    print("🚀 Phase 0: Configuration Architecture Enhancement Tests")
    print("=" * 60)
    
    tests = [
        ("Enhanced Configuration Manager", test_enhanced_config_manager),
        ("Configuration Validator", test_config_validator),
        ("Strategy Configuration Files", test_strategy_config_files)
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
        print("🎉 Phase 0 Implementation: SUCCESS")
        print("\n✅ Configuration architecture enhancement is ready!")
        print("✅ Enhanced config manager with parameter persistence")
        print("✅ Academic parameter validation")
        print("✅ Strategy configuration templates")
        print("✅ Ready for Phase 1: Core System Enhancements")
    else:
        print("❌ Phase 0 Implementation: FAILED")
        print("Please fix the failing tests before proceeding to Phase 1")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 