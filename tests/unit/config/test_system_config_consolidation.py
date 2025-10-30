#!/usr/bin/env python3
"""
System Configuration Consolidation Verification Tests
=====================================================

Tests verifying Priority 1 & 2 fixes:
1. CentralRiskManager uses centralized RiskConfig
2. SystemConfiguration has type-safe configs

Author: StatArb_Gemini Configuration Consolidation (Phase 6)
Date: October 21, 2025
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.system.integration_manager import SystemConfiguration
from core_engine.config.component_config import RiskConfig, DataConfig, PositionLimits, RiskLimits


class TestPriority1_RiskManagerConfig:
    """Test Priority 1: CentralRiskManager uses centralized RiskConfig"""
    
    def test_risk_manager_uses_centralized_config(self):
        """Test that RiskManager uses RiskConfig from core_engine.config"""
        # Create RiskManager with None config (should use defaults)
        risk_manager = CentralRiskManager(None)
        
        # Verify config is RiskConfig type
        assert isinstance(risk_manager.config, RiskConfig), \
            f"Expected RiskConfig, got {type(risk_manager.config)}"
        
        # Verify centralized config structure
        assert hasattr(risk_manager.config, 'position_limits'), "Missing position_limits"
        assert hasattr(risk_manager.config, 'risk_limits'), "Missing risk_limits"
        assert isinstance(risk_manager.config.position_limits, PositionLimits)
        assert isinstance(risk_manager.config.risk_limits, RiskLimits)
        
        print("✅ Test 1.1 passed: RiskManager uses centralized RiskConfig")
    
    def test_risk_manager_accepts_typed_config(self):
        """Test that RiskManager accepts RiskConfig directly"""
        # Create custom RiskConfig
        custom_config = RiskConfig(
            position_limits=PositionLimits(max_position_size=0.15),
            risk_limits=RiskLimits(max_daily_var=0.03),
            auto_approval_threshold=0.02
        )
        
        # Create RiskManager with typed config
        risk_manager = CentralRiskManager(custom_config)
        
        # Verify custom values
        assert risk_manager.config.position_limits.max_position_size == 0.15
        assert risk_manager.config.risk_limits.max_daily_var == 0.03
        assert risk_manager.config.auto_approval_threshold == 0.02
        
        print("✅ Test 1.2 passed: RiskManager accepts typed RiskConfig")
    
    def test_risk_manager_backward_compatible_dict(self):
        """Test backward compatibility with dict config"""
        # Old-style dict config
        dict_config = {
            'max_position_size': 0.12,
            'max_daily_var': 0.04,
            'min_signal_confidence': 0.7,
            'auto_approval_threshold': 0.015
        }
        
        # Create RiskManager with dict
        risk_manager = CentralRiskManager(dict_config)
        
        # Verify values mapped correctly
        assert risk_manager.config.position_limits.max_position_size == 0.12
        assert risk_manager.config.risk_limits.max_daily_var == 0.04
        assert risk_manager.config.risk_limits.confidence_threshold == 0.7
        assert risk_manager.config.auto_approval_threshold == 0.015
        
        print("✅ Test 1.3 passed: Backward compatible with dict config")
    
    def test_risk_manager_helper_properties(self):
        """Test helper properties provide correct values"""
        risk_manager = CentralRiskManager(None)
        
        # Test helper properties
        assert risk_manager.max_position_size == 0.10
        assert risk_manager.max_daily_var == 0.05
        assert risk_manager.position_concentration_limit == 0.15
        assert risk_manager.min_signal_confidence == 0.6
        assert risk_manager.auto_approval_threshold == 0.01
        assert risk_manager.elevated_review_threshold == 0.05
        assert risk_manager.emergency_threshold == 0.10
        
        print("✅ Test 1.4 passed: Helper properties work correctly")
    
    def test_risk_manager_rejects_invalid_config(self):
        """Test that invalid config types are rejected"""
        with pytest.raises(TypeError):
            CentralRiskManager("invalid_config")  # String not allowed
        
        with pytest.raises(TypeError):
            CentralRiskManager(123)  # Int not allowed
        
        print("✅ Test 1.5 passed: Invalid config types rejected")


class TestPriority2_SystemConfiguration:
    """Test Priority 2: SystemConfiguration has type-safe configs"""
    
    def test_system_config_uses_typed_configs(self):
        """Test that SystemConfiguration uses typed configs"""
        sys_config = SystemConfiguration()
        
        # Verify typed configs are initialized
        assert isinstance(sys_config.risk_manager_config, RiskConfig), \
            f"Expected RiskConfig, got {type(sys_config.risk_manager_config)}"
        assert isinstance(sys_config.data_manager_config, DataConfig), \
            f"Expected DataConfig, got {type(sys_config.data_manager_config)}"
        
        # Check other typed configs
        from core_engine.config.component_config import (
            IndicatorConfig, FeatureConfig, SignalConfig,
            RegimeConfig, AnalyticsConfig, ExecutionConfig, PortfolioConfig
        )
        
        assert isinstance(sys_config.indicators_config, IndicatorConfig)
        assert isinstance(sys_config.features_config, FeatureConfig)
        assert isinstance(sys_config.signals_config, SignalConfig)
        assert isinstance(sys_config.regime_engine_config, RegimeConfig)
        assert isinstance(sys_config.analytics_manager_config, AnalyticsConfig)
        assert isinstance(sys_config.execution_engine_config, ExecutionConfig)
        assert isinstance(sys_config.portfolio_manager_config, PortfolioConfig)
        
        print("✅ Test 2.1 passed: SystemConfiguration uses typed configs")
    
    def test_system_config_custom_typed_configs(self):
        """Test custom typed configs"""
        custom_risk = RiskConfig(
            position_limits=PositionLimits(max_position_size=0.20)
        )
        custom_data = DataConfig(
            start_date="2024-12-25",
            end_date="2024-12-25"
        )
        
        sys_config = SystemConfiguration(
            risk_manager_config=custom_risk,
            data_manager_config=custom_data
        )
        
        # Verify custom values
        assert sys_config.risk_manager_config.position_limits.max_position_size == 0.20
        assert sys_config.data_manager_config.start_date == "2024-12-25"
        assert sys_config.data_manager_config.end_date == "2024-12-25"
        assert sys_config.data_manager_config.caching.enable_caching is True  # Default from CachingConfig
        
        print("✅ Test 2.2 passed: Custom typed configs work")
    
    def test_system_config_to_dict(self):
        """Test to_dict() backward compatibility"""
        sys_config = SystemConfiguration()
        config_dict = sys_config.to_dict()
        
        # Verify dict structure
        assert isinstance(config_dict, dict)
        assert 'risk_manager_config' in config_dict
        assert 'data_manager_config' in config_dict
        assert 'indicators_config' in config_dict
        
        # Verify typed configs converted to dicts
        assert isinstance(config_dict['risk_manager_config'], dict)
        assert isinstance(config_dict['data_manager_config'], dict)
        
        print("✅ Test 2.3 passed: to_dict() backward compatibility works")
    
    def test_system_config_post_init(self):
        """Test __post_init__ initializes None configs"""
        # Create with None configs (should auto-initialize)
        sys_config = SystemConfiguration(
            risk_manager_config=None,
            data_manager_config=None
        )
        
        # __post_init__ should have initialized them
        assert sys_config.risk_manager_config is not None
        assert sys_config.data_manager_config is not None
        assert isinstance(sys_config.risk_manager_config, RiskConfig)
        assert isinstance(sys_config.data_manager_config, DataConfig)
        
        print("✅ Test 2.4 passed: __post_init__ auto-initializes configs")


class TestIntegration:
    """Integration tests for both fixes"""
    
    def test_risk_manager_with_system_config(self):
        """Test RiskManager with SystemConfiguration"""
        # Create SystemConfiguration with custom RiskConfig
        sys_config = SystemConfiguration(
            risk_manager_config=RiskConfig(
                position_limits=PositionLimits(max_position_size=0.18),
                auto_approval_threshold=0.02
            )
        )
        
        # Create RiskManager with config from SystemConfiguration
        risk_manager = CentralRiskManager(sys_config.risk_manager_config)
        
        # Verify values
        assert risk_manager.max_position_size == 0.18
        assert risk_manager.auto_approval_threshold == 0.02
        
        print("✅ Integration test passed: RiskManager + SystemConfiguration")


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*80)
    print("SYSTEM CONFIGURATION CONSOLIDATION TESTS")
    print("="*80 + "\n")
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    test_classes = [
        TestPriority1_RiskManagerConfig,
        TestPriority2_SystemConfiguration,
        TestIntegration
    ]
    
    for test_class in test_classes:
        print(f"\n{'='*80}")
        print(f"Running {test_class.__name__}")
        print(f"{'='*80}\n")
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                failed_tests += 1
                print(f"❌ {method_name} FAILED: {e}")
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Configuration consolidation successful!")
        return 0
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

