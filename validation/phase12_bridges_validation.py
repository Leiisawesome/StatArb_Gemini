"""
Phase 12 Bridges Validation Script

This script validates the ConfigBridge and AnalyticsBridge implementations by testing:
- Configuration management and validation
- Analytics calculations and reporting
- Performance metrics and risk metrics
- Error handling and caching
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import bridge components
try:
    from core_structure.infrastructure.config.config_bridge import (
        ConfigBridge, ConfigBridgeConfig, ConfigMode, ConfigStatus,
        ConfigBridgeResult, ConfigSnapshot, ConfigValidationReport,
        create_config_bridge, get_config_for_backtesting
    )
    CONFIG_BRIDGE_IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Failed to import ConfigBridge: {e}")
    CONFIG_BRIDGE_IMPORT_SUCCESS = False

try:
    from core_structure.analytics.analytics_bridge import (
        AnalyticsBridge, AnalyticsBridgeConfig, AnalyticsMode, AnalyticsStatus,
        AnalyticsBridgeResult, AnalyticsSnapshot, PerformanceMetrics, RiskMetrics,
        create_analytics_bridge, get_analytics_for_backtesting
    )
    ANALYTICS_BRIDGE_IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Failed to import AnalyticsBridge: {e}")
    ANALYTICS_BRIDGE_IMPORT_SUCCESS = False


class Phase12BridgesValidator:
    """Validator for Phase 12 bridges functionality"""
    
    def __init__(self):
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': [],
            'performance_metrics': {},
            'recommendations': []
        }
    
    def run_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """Run a test and record results"""
        self.results['tests_run'] += 1
        
        try:
            start_time = time.time()
            result = test_func(*args, **kwargs)
            end_time = time.time()
            
            if result:
                self.results['tests_passed'] += 1
                logger.info(f"✅ PASS: {test_name}")
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'PASS',
                    'duration_ms': (end_time - start_time) * 1000
                })
                return True
            else:
                self.results['tests_failed'] += 1
                logger.error(f"❌ FAIL: {test_name}")
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'FAIL',
                    'duration_ms': (end_time - start_time) * 1000
                })
                return False
                
        except Exception as e:
            self.results['tests_failed'] += 1
            logger.error(f"❌ ERROR: {test_name} - {e}")
            self.results['test_details'].append({
                'test': test_name,
                'status': 'ERROR',
                'error': str(e),
                'duration_ms': 0
            })
            return False
    
    async def run_async_test(self, test_name: str, test_func, *args, **kwargs) -> bool:
        """Run an async test and record results"""
        self.results['tests_run'] += 1
        
        try:
            start_time = time.time()
            result = await test_func(*args, **kwargs)
            end_time = time.time()
            
            if result:
                self.results['tests_passed'] += 1
                logger.info(f"✅ PASS: {test_name}")
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'PASS',
                    'duration_ms': (end_time - start_time) * 1000
                })
                return True
            else:
                self.results['tests_failed'] += 1
                logger.error(f"❌ FAIL: {test_name}")
                self.results['test_details'].append({
                    'test': test_name,
                    'status': 'FAIL',
                    'duration_ms': (end_time - start_time) * 1000
                })
                return False
                
        except Exception as e:
            self.results['tests_failed'] += 1
            logger.error(f"❌ ERROR: {test_name} - {e}")
            self.results['test_details'].append({
                'test': test_name,
                'status': 'ERROR',
                'error': str(e),
                'duration_ms': 0
            })
            return False
    
    def get_success_rate(self) -> float:
        """Calculate test success rate"""
        if self.results['tests_run'] == 0:
            return 0.0
        return (self.results['tests_passed'] / self.results['tests_run']) * 100
    
    def save_results(self, filename: str = "phase12_bridges_validation_report.json"):
        """Save validation results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Validation results saved to {filename}")


# ConfigBridge Tests
def test_config_bridge_import_validation() -> bool:
    """Test ConfigBridge import validation"""
    return CONFIG_BRIDGE_IMPORT_SUCCESS


def test_config_bridge_initialization() -> bool:
    """Test ConfigBridge initialization"""
    try:
        # Test default initialization
        bridge = ConfigBridge()
        assert bridge.config.config_mode == ConfigMode.BACKTESTING
        assert bridge.config.enable_config_validation is True
        
        # Test custom initialization
        config = ConfigBridgeConfig(config_mode=ConfigMode.PRODUCTION)
        bridge = ConfigBridge(config)
        assert bridge.config.config_mode == ConfigMode.PRODUCTION
        
        return True
    except Exception as e:
        logger.error(f"ConfigBridge initialization test failed: {e}")
        return False


def test_config_bridge_factory_function() -> bool:
    """Test ConfigBridge factory function"""
    try:
        config = ConfigBridgeConfig(config_mode=ConfigMode.SIMULATION)
        bridge = create_config_bridge(config)
        assert isinstance(bridge, ConfigBridge)
        assert bridge.config.config_mode == ConfigMode.SIMULATION
        return True
    except Exception as e:
        logger.error(f"ConfigBridge factory function test failed: {e}")
        return False


async def test_config_snapshot_retrieval() -> bool:
    """Test configuration snapshot retrieval"""
    try:
        bridge = ConfigBridge()
        
        # Test snapshot retrieval
        snapshot = await bridge.get_config_snapshot("trading_config")
        assert isinstance(snapshot, ConfigSnapshot)
        assert snapshot.config_id == "trading_config"
        assert snapshot.config_type == "trading"
        assert isinstance(snapshot.config_data, dict)
        assert snapshot.validation_status == ConfigStatus.ACTIVE
        
        return True
    except Exception as e:
        logger.error(f"Config snapshot retrieval test failed: {e}")
        return False


async def test_config_update() -> bool:
    """Test configuration update functionality"""
    try:
        bridge = ConfigBridge()
        
        # Test config update
        config_data = {
            'max_position_size': 0.05,
            'max_portfolio_risk': 0.01,
            'stop_loss_pct': 0.03
        }
        
        result = await bridge.update_config(
            config_id="test_config",
            config_data=config_data,
            config_type="trading"
        )
        
        assert isinstance(result, ConfigBridgeResult)
        assert result.operation_type == "config_update"
        assert result.config_id == "test_config"
        assert result.success is True
        assert result.source == "backtesting"
        assert "config_data" in result.data
        
        return True
    except Exception as e:
        logger.error(f"Config update test failed: {e}")
        return False


async def test_config_validation() -> bool:
    """Test configuration validation"""
    try:
        bridge = ConfigBridge()
        
        # Test valid config
        valid_config = {
            'max_position_size': 0.05,
            'max_portfolio_risk': 0.01,
            'stop_loss_pct': 0.03
        }
        
        report = await bridge.validate_config("test_config", valid_config)
        assert isinstance(report, ConfigValidationReport)
        assert report.config_id == "test_config"
        assert report.validation_score > 0
        assert report.total_rules > 0
        
        return True
    except Exception as e:
        logger.error(f"Config validation test failed: {e}")
        return False


def test_config_performance_metrics() -> bool:
    """Test ConfigBridge performance metrics"""
    try:
        bridge = ConfigBridge()
        
        stats = bridge.get_performance_stats()
        assert isinstance(stats, dict)
        assert "total_operations" in stats
        assert "production_operations" in stats
        assert "backtesting_operations" in stats
        assert "cached_operations" in stats
        assert "errors" in stats
        assert "avg_processing_time" in stats
        assert "total_configs" in stats
        
        return True
    except Exception as e:
        logger.error(f"ConfigBridge performance metrics test failed: {e}")
        return False


def test_config_cache_functionality() -> bool:
    """Test ConfigBridge cache functionality"""
    try:
        bridge = ConfigBridge()
        
        # Add some data to cache
        bridge._config_cache["test_key"] = ("test_data", datetime.now())
        assert len(bridge._config_cache) > 0
        
        # Clear cache
        bridge.clear_cache()
        assert len(bridge._config_cache) == 0
        
        return True
    except Exception as e:
        logger.error(f"ConfigBridge cache functionality test failed: {e}")
        return False


def test_config_convenience_function() -> bool:
    """Test ConfigBridge convenience function"""
    try:
        # Since we're already in an async context, the convenience function will return fallback snapshot
        snapshot = get_config_for_backtesting("test_config")
        assert isinstance(snapshot, ConfigSnapshot)
        assert snapshot.config_id == "test_config"
        return True
    except Exception as e:
        logger.error(f"ConfigBridge convenience function test failed: {e}")
        return False


# AnalyticsBridge Tests
def test_analytics_bridge_import_validation() -> bool:
    """Test AnalyticsBridge import validation"""
    return ANALYTICS_BRIDGE_IMPORT_SUCCESS


def test_analytics_bridge_initialization() -> bool:
    """Test AnalyticsBridge initialization"""
    try:
        # Test default initialization
        bridge = AnalyticsBridge()
        assert bridge.config.analytics_mode == AnalyticsMode.BACKTESTING
        assert bridge.config.enable_performance_analytics is True
        
        # Test custom initialization
        config = AnalyticsBridgeConfig(analytics_mode=AnalyticsMode.PRODUCTION)
        bridge = AnalyticsBridge(config)
        assert bridge.config.analytics_mode == AnalyticsMode.PRODUCTION
        
        return True
    except Exception as e:
        logger.error(f"AnalyticsBridge initialization test failed: {e}")
        return False


def test_analytics_bridge_factory_function() -> bool:
    """Test AnalyticsBridge factory function"""
    try:
        config = AnalyticsBridgeConfig(analytics_mode=AnalyticsMode.SIMULATION)
        bridge = create_analytics_bridge(config)
        assert isinstance(bridge, AnalyticsBridge)
        assert bridge.config.analytics_mode == AnalyticsMode.SIMULATION
        return True
    except Exception as e:
        logger.error(f"AnalyticsBridge factory function test failed: {e}")
        return False


async def test_analytics_snapshot_retrieval() -> bool:
    """Test analytics snapshot retrieval"""
    try:
        bridge = AnalyticsBridge()
        
        # Test snapshot retrieval
        snapshot = await bridge.get_analytics_snapshot("performance_analytics")
        assert isinstance(snapshot, AnalyticsSnapshot)
        assert snapshot.analytics_id == "performance_analytics"
        assert snapshot.analytics_type == "performance"
        assert isinstance(snapshot.analytics_data, dict)
        assert snapshot.status == AnalyticsStatus.COMPLETED
        
        return True
    except Exception as e:
        logger.error(f"Analytics snapshot retrieval test failed: {e}")
        return False


async def test_performance_metrics_calculation() -> bool:
    """Test performance metrics calculation"""
    try:
        bridge = AnalyticsBridge()
        
        # Create mock returns data
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        # Calculate performance metrics
        metrics = await bridge.calculate_performance_metrics(returns)
        
        assert isinstance(metrics, PerformanceMetrics)
        assert hasattr(metrics, 'total_return')
        assert hasattr(metrics, 'annualized_return')
        assert hasattr(metrics, 'sharpe_ratio')
        assert hasattr(metrics, 'max_drawdown')
        assert hasattr(metrics, 'win_rate')
        assert hasattr(metrics, 'profit_factor')
        
        return True
    except Exception as e:
        logger.error(f"Performance metrics calculation test failed: {e}")
        return False


async def test_risk_metrics_calculation() -> bool:
    """Test risk metrics calculation"""
    try:
        bridge = AnalyticsBridge()
        
        # Create mock returns data
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))
        
        # Calculate risk metrics
        metrics = await bridge.calculate_risk_metrics(returns)
        
        assert isinstance(metrics, RiskMetrics)
        assert hasattr(metrics, 'var_95')
        assert hasattr(metrics, 'var_99')
        assert hasattr(metrics, 'cvar_95')
        assert hasattr(metrics, 'cvar_99')
        assert hasattr(metrics, 'volatility')
        assert hasattr(metrics, 'beta')
        assert hasattr(metrics, 'max_drawdown')
        assert hasattr(metrics, 'skewness')
        assert hasattr(metrics, 'kurtosis')
        
        return True
    except Exception as e:
        logger.error(f"Risk metrics calculation test failed: {e}")
        return False


async def test_analytics_report_generation() -> bool:
    """Test analytics report generation"""
    try:
        bridge = AnalyticsBridge()
        
        # Test report generation
        data = {
            'returns': pd.Series(np.random.normal(0.001, 0.02, 252)),
            'benchmark_returns': pd.Series(np.random.normal(0.0008, 0.015, 252))
        }
        
        result = await bridge.generate_analytics_report("test_analytics", data)
        
        assert isinstance(result, AnalyticsBridgeResult)
        assert result.operation_type == "analytics_report"
        assert result.analytics_id == "test_analytics"
        assert result.success is True
        assert result.source == "backtesting"
        assert "performance_metrics" in result.data
        assert "risk_metrics" in result.data
        
        return True
    except Exception as e:
        logger.error(f"Analytics report generation test failed: {e}")
        return False


def test_analytics_performance_metrics() -> bool:
    """Test AnalyticsBridge performance metrics"""
    try:
        bridge = AnalyticsBridge()
        
        stats = bridge.get_performance_stats()
        assert isinstance(stats, dict)
        assert "total_operations" in stats
        assert "production_operations" in stats
        assert "backtesting_operations" in stats
        assert "cached_operations" in stats
        assert "errors" in stats
        assert "avg_processing_time" in stats
        assert "total_analytics" in stats
        
        return True
    except Exception as e:
        logger.error(f"AnalyticsBridge performance metrics test failed: {e}")
        return False


def test_analytics_cache_functionality() -> bool:
    """Test AnalyticsBridge cache functionality"""
    try:
        bridge = AnalyticsBridge()
        
        # Add some data to cache
        bridge._analytics_cache["test_key"] = ("test_data", datetime.now())
        assert len(bridge._analytics_cache) > 0
        
        # Clear cache
        bridge.clear_cache()
        assert len(bridge._analytics_cache) == 0
        
        return True
    except Exception as e:
        logger.error(f"AnalyticsBridge cache functionality test failed: {e}")
        return False


def test_analytics_convenience_function() -> bool:
    """Test AnalyticsBridge convenience function"""
    try:
        # Since we're already in an async context, the convenience function will return fallback snapshot
        snapshot = get_analytics_for_backtesting("test_analytics")
        assert isinstance(snapshot, AnalyticsSnapshot)
        assert snapshot.analytics_id == "test_analytics"
        return True
    except Exception as e:
        logger.error(f"AnalyticsBridge convenience function test failed: {e}")
        return False


async def test_error_handling() -> bool:
    """Test error handling for both bridges"""
    try:
        # Test ConfigBridge error handling
        config_bridge = ConfigBridge()
        invalid_config = {}
        result = await config_bridge.update_config("test_config", invalid_config, "trading")
        assert isinstance(result, ConfigBridgeResult)
        assert result.success is False
        assert result.error_message is not None
        
        # Test AnalyticsBridge error handling
        analytics_bridge = AnalyticsBridge()
        empty_returns = pd.Series([])
        try:
            await analytics_bridge.calculate_performance_metrics(empty_returns)
            return False  # Should raise an exception
        except Exception:
            pass  # Expected behavior
        
        return True
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


async def test_caching_behavior() -> bool:
    """Test caching behavior for both bridges"""
    try:
        # Test ConfigBridge caching
        config_bridge = ConfigBridge()
        snapshot1 = await config_bridge.get_config_snapshot("test_config")
        snapshot2 = await config_bridge.get_config_snapshot("test_config")
        assert snapshot1.config_id == snapshot2.config_id
        
        # Test AnalyticsBridge caching
        analytics_bridge = AnalyticsBridge()
        analytics1 = await analytics_bridge.get_analytics_snapshot("test_analytics")
        analytics2 = await analytics_bridge.get_analytics_snapshot("test_analytics")
        assert analytics1.analytics_id == analytics2.analytics_id
        
        return True
    except Exception as e:
        logger.error(f"Caching behavior test failed: {e}")
        return False


async def run_validation_suite():
    """Run the complete validation suite"""
    logger.info("🚀 Starting Phase 12 Bridges Validation Suite")
    logger.info("=" * 70)
    
    validator = Phase12BridgesValidator()
    
    # Run ConfigBridge tests
    logger.info("📋 Testing ConfigBridge...")
    validator.run_test("ConfigBridge Import Validation", test_config_bridge_import_validation)
    validator.run_test("ConfigBridge Initialization Test", test_config_bridge_initialization)
    validator.run_test("ConfigBridge Factory Function Test", test_config_bridge_factory_function)
    validator.run_test("ConfigBridge Performance Metrics Test", test_config_performance_metrics)
    validator.run_test("ConfigBridge Cache Functionality Test", test_config_cache_functionality)
    validator.run_test("ConfigBridge Convenience Function Test", test_config_convenience_function)
    
    await validator.run_async_test("ConfigBridge Snapshot Retrieval Test", test_config_snapshot_retrieval)
    await validator.run_async_test("ConfigBridge Update Test", test_config_update)
    await validator.run_async_test("ConfigBridge Validation Test", test_config_validation)
    
    # Run AnalyticsBridge tests
    logger.info("📊 Testing AnalyticsBridge...")
    validator.run_test("AnalyticsBridge Import Validation", test_analytics_bridge_import_validation)
    validator.run_test("AnalyticsBridge Initialization Test", test_analytics_bridge_initialization)
    validator.run_test("AnalyticsBridge Factory Function Test", test_analytics_bridge_factory_function)
    validator.run_test("AnalyticsBridge Performance Metrics Test", test_analytics_performance_metrics)
    validator.run_test("AnalyticsBridge Cache Functionality Test", test_analytics_cache_functionality)
    validator.run_test("AnalyticsBridge Convenience Function Test", test_analytics_convenience_function)
    
    await validator.run_async_test("AnalyticsBridge Snapshot Retrieval Test", test_analytics_snapshot_retrieval)
    await validator.run_async_test("AnalyticsBridge Performance Metrics Calculation Test", test_performance_metrics_calculation)
    await validator.run_async_test("AnalyticsBridge Risk Metrics Calculation Test", test_risk_metrics_calculation)
    await validator.run_async_test("AnalyticsBridge Report Generation Test", test_analytics_report_generation)
    
    # Run integration tests
    logger.info("🔗 Testing Integration...")
    await validator.run_async_test("Error Handling Test", test_error_handling)
    await validator.run_async_test("Caching Behavior Test", test_caching_behavior)
    
    # Calculate and display results
    success_rate = validator.get_success_rate()
    total_tests = validator.results['tests_run']
    passed_tests = validator.results['tests_passed']
    failed_tests = validator.results['tests_failed']
    
    logger.info("=" * 70)
    logger.info("📊 VALIDATION RESULTS")
    logger.info("=" * 70)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        logger.info("🎉 EXCELLENT! Phase 12 bridges validation successful!")
    elif success_rate >= 80:
        logger.info("✅ GOOD! Phase 12 bridges validation mostly successful!")
    elif success_rate >= 70:
        logger.info("⚠️  FAIR! Phase 12 bridges validation partially successful!")
    else:
        logger.info("❌ POOR! Phase 12 bridges validation needs improvement!")
    
    # Save results
    validator.save_results()
    
    # Generate recommendations
    if failed_tests > 0:
        validator.results['recommendations'].append("Review failed tests and fix implementation issues")
    
    if success_rate < 90:
        validator.results['recommendations'].append("Improve test coverage and error handling")
    
    if success_rate >= 90:
        validator.results['recommendations'].append("Phase 12 bridges are ready for production use")
    
    logger.info("=" * 70)
    logger.info("📝 RECOMMENDATIONS")
    logger.info("=" * 70)
    for i, recommendation in enumerate(validator.results['recommendations'], 1):
        logger.info(f"{i}. {recommendation}")
    
    return validator.results


def main():
    """Main validation function"""
    try:
        # Run the validation suite
        results = asyncio.run(run_validation_suite())
        
        # Exit with appropriate code
        if results['tests_failed'] == 0:
            logger.info("✅ All tests passed! Phase 12 bridges validation successful.")
            return 0
        else:
            logger.warning(f"⚠️  {results['tests_failed']} tests failed. Review results.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Validation suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 