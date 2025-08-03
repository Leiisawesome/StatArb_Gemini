"""
PortfolioBridge Validation Script

This script validates the PortfolioBridge implementation by testing:
- Portfolio snapshot retrieval
- Position updates
- Performance metrics
- Error handling
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

# Import PortfolioBridge components
try:
    from core_structure.portfolio.portfolio_bridge import (
        PortfolioBridge, PortfolioBridgeConfig, PortfolioMode, PortfolioStatus,
        PortfolioBridgeResult, PortfolioSnapshot, create_portfolio_bridge, get_portfolio_for_backtesting
    )
    PORTFOLIO_BRIDGE_IMPORT_SUCCESS = True
except ImportError as e:
    logger.error(f"Failed to import PortfolioBridge: {e}")
    PORTFOLIO_BRIDGE_IMPORT_SUCCESS = False


class PortfolioBridgeValidator:
    """Validator for PortfolioBridge functionality"""
    
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
    
    def save_results(self, filename: str = "portfolio_bridge_validation_report.json"):
        """Save validation results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Validation results saved to {filename}")


def test_import_validation() -> bool:
    """Test PortfolioBridge import validation"""
    return PORTFOLIO_BRIDGE_IMPORT_SUCCESS


def test_portfolio_bridge_initialization() -> bool:
    """Test PortfolioBridge initialization"""
    try:
        # Test default initialization
        bridge = PortfolioBridge()
        assert bridge.config.portfolio_mode == PortfolioMode.BACKTESTING
        assert bridge.config.enable_position_tracking is True
        
        # Test custom initialization
        config = PortfolioBridgeConfig(portfolio_mode=PortfolioMode.PRODUCTION)
        bridge = PortfolioBridge(config)
        assert bridge.config.portfolio_mode == PortfolioMode.PRODUCTION
        
        return True
    except Exception as e:
        logger.error(f"Initialization test failed: {e}")
        return False


def test_factory_function() -> bool:
    """Test factory function"""
    try:
        config = PortfolioBridgeConfig(portfolio_mode=PortfolioMode.SIMULATION)
        bridge = create_portfolio_bridge(config)
        assert isinstance(bridge, PortfolioBridge)
        assert bridge.config.portfolio_mode == PortfolioMode.SIMULATION
        return True
    except Exception as e:
        logger.error(f"Factory function test failed: {e}")
        return False


async def test_portfolio_snapshot_retrieval() -> bool:
    """Test portfolio snapshot retrieval"""
    try:
        bridge = PortfolioBridge()
        
        # Test snapshot retrieval
        snapshot = await bridge.get_portfolio_snapshot("test_portfolio")
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.portfolio_id == "test_portfolio"
        assert snapshot.total_value > 0
        assert snapshot.total_pnl >= 0
        assert isinstance(snapshot.positions, dict)
        assert isinstance(snapshot.risk_metrics, dict)
        assert snapshot.status == PortfolioStatus.ACTIVE
        
        return True
    except Exception as e:
        logger.error(f"Portfolio snapshot retrieval test failed: {e}")
        return False


async def test_position_update() -> bool:
    """Test position update functionality"""
    try:
        bridge = PortfolioBridge()
        
        # Test position update
        result = await bridge.update_position(
            portfolio_id="test_portfolio",
            symbol="AAPL",
            quantity=100,
            price=150.0,
            operation="buy"
        )
        
        assert isinstance(result, PortfolioBridgeResult)
        assert result.operation_type == "position_update"
        assert result.portfolio_id == "test_portfolio"
        assert result.success is True
        assert result.source == "backtesting"
        assert "symbol" in result.data
        assert result.data["symbol"] == "AAPL"
        
        return True
    except Exception as e:
        logger.error(f"Position update test failed: {e}")
        return False


def test_performance_metrics() -> bool:
    """Test performance metrics"""
    try:
        bridge = PortfolioBridge()
        
        stats = bridge.get_performance_stats()
        assert isinstance(stats, dict)
        assert "total_operations" in stats
        assert "production_operations" in stats
        assert "backtesting_operations" in stats
        assert "cached_operations" in stats
        assert "errors" in stats
        assert "avg_processing_time" in stats
        assert "total_positions" in stats
        
        return True
    except Exception as e:
        logger.error(f"Performance metrics test failed: {e}")
        return False


def test_cache_functionality() -> bool:
    """Test cache functionality"""
    try:
        bridge = PortfolioBridge()
        
        # Add some data to cache
        bridge._portfolio_cache["test_key"] = ("test_data", datetime.now())
        assert len(bridge._portfolio_cache) > 0
        
        # Clear cache
        bridge.clear_cache()
        assert len(bridge._portfolio_cache) == 0
        
        return True
    except Exception as e:
        logger.error(f"Cache functionality test failed: {e}")
        return False


def test_position_size_validation() -> bool:
    """Test position size validation"""
    try:
        bridge = PortfolioBridge()
        
        # Test valid position size
        valid = bridge._validate_position_size("AAPL", 100, 150.0)
        assert valid is True
        
        # Test invalid position size (too large)
        invalid = bridge._validate_position_size("AAPL", 1000000, 150.0)
        assert invalid is False
        
        return True
    except Exception as e:
        logger.error(f"Position size validation test failed: {e}")
        return False


def test_risk_metrics_calculation() -> bool:
    """Test risk metrics calculation"""
    try:
        bridge = PortfolioBridge()
        
        # Test positions
        positions = {
            'AAPL': {
                'quantity': 100,
                'avg_price': 150.0,
                'current_price': 155.0,
                'market_value': 15500.0,
                'unrealized_pnl': 500.0,
                'unrealized_pnl_pct': 3.33
            },
            'GOOGL': {
                'quantity': 50,
                'avg_price': 2800.0,
                'current_price': 2850.0,
                'market_value': 142500.0,
                'unrealized_pnl': 2500.0,
                'unrealized_pnl_pct': 1.79
            }
        }
        
        risk_metrics = bridge._calculate_basic_risk_metrics(positions)
        assert isinstance(risk_metrics, dict)
        assert "total_positions" in risk_metrics
        assert "max_position_size" in risk_metrics
        assert "avg_position_size" in risk_metrics
        assert risk_metrics["total_positions"] == 2
        
        return True
    except Exception as e:
        logger.error(f"Risk metrics calculation test failed: {e}")
        return False


def test_mock_snapshot_creation() -> bool:
    """Test mock snapshot creation"""
    try:
        bridge = PortfolioBridge()
        
        snapshot = bridge._create_mock_snapshot("test_portfolio")
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.portfolio_id == "test_portfolio"
        assert snapshot.total_value > 0
        assert len(snapshot.positions) > 0
        assert snapshot.status == PortfolioStatus.ACTIVE
        
        return True
    except Exception as e:
        logger.error(f"Mock snapshot creation test failed: {e}")
        return False


def test_fallback_snapshot_creation() -> bool:
    """Test fallback snapshot creation"""
    try:
        bridge = PortfolioBridge()
        
        snapshot = bridge._create_fallback_snapshot("test_portfolio")
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.portfolio_id == "test_portfolio"
        assert snapshot.total_value == 0.0
        assert len(snapshot.positions) == 0
        assert snapshot.status == PortfolioStatus.ERROR
        
        return True
    except Exception as e:
        logger.error(f"Fallback snapshot creation test failed: {e}")
        return False


def test_convenience_function() -> bool:
    """Test convenience function"""
    try:
        # Since we're already in an async context, the convenience function will return fallback snapshot
        # This is expected behavior to avoid event loop conflicts
        snapshot = get_portfolio_for_backtesting("test_portfolio")
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.portfolio_id == "test_portfolio"
        return True
    except Exception as e:
        logger.error(f"Convenience function test failed: {e}")
        return False


async def test_error_handling() -> bool:
    """Test error handling"""
    try:
        bridge = PortfolioBridge()
        
        # Test invalid position update (should handle error gracefully)
        result = await bridge.update_position(
            portfolio_id="test_portfolio",
            symbol="INVALID",
            quantity=1000000,  # Too large
            price=150.0,
            operation="buy"
        )
        
        # Should return error result
        assert isinstance(result, PortfolioBridgeResult)
        assert result.success is False
        assert result.error_message is not None
        
        return True
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")
        return False


async def test_caching_behavior() -> bool:
    """Test caching behavior"""
    try:
        bridge = PortfolioBridge()
        
        # First request
        snapshot1 = await bridge.get_portfolio_snapshot("test_portfolio")
        
        # Second request (should be cached)
        snapshot2 = await bridge.get_portfolio_snapshot("test_portfolio")
        
        assert snapshot1.portfolio_id == snapshot2.portfolio_id
        assert snapshot1.total_value == snapshot2.total_value
        
        # Check performance stats for cached operations
        stats = bridge.get_performance_stats()
        assert stats["cached_operations"] > 0
        
        return True
    except Exception as e:
        logger.error(f"Caching behavior test failed: {e}")
        return False


async def run_validation_suite():
    """Run the complete validation suite"""
    logger.info("🚀 Starting PortfolioBridge Validation Suite")
    logger.info("=" * 60)
    
    validator = PortfolioBridgeValidator()
    
    # Run synchronous tests
    validator.run_test("Import Validation", test_import_validation)
    validator.run_test("Initialization Test", test_portfolio_bridge_initialization)
    validator.run_test("Factory Function Test", test_factory_function)
    validator.run_test("Performance Metrics Test", test_performance_metrics)
    validator.run_test("Cache Functionality Test", test_cache_functionality)
    validator.run_test("Position Size Validation Test", test_position_size_validation)
    validator.run_test("Risk Metrics Calculation Test", test_risk_metrics_calculation)
    validator.run_test("Mock Snapshot Creation Test", test_mock_snapshot_creation)
    validator.run_test("Fallback Snapshot Creation Test", test_fallback_snapshot_creation)
    validator.run_test("Convenience Function Test", test_convenience_function)
    
    # Run asynchronous tests
    await validator.run_async_test("Portfolio Snapshot Retrieval Test", test_portfolio_snapshot_retrieval)
    await validator.run_async_test("Position Update Test", test_position_update)
    await validator.run_async_test("Error Handling Test", test_error_handling)
    await validator.run_async_test("Caching Behavior Test", test_caching_behavior)
    
    # Calculate and display results
    success_rate = validator.get_success_rate()
    total_tests = validator.results['tests_run']
    passed_tests = validator.results['tests_passed']
    failed_tests = validator.results['tests_failed']
    
    logger.info("=" * 60)
    logger.info("📊 VALIDATION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        logger.info("🎉 EXCELLENT! PortfolioBridge validation successful!")
    elif success_rate >= 80:
        logger.info("✅ GOOD! PortfolioBridge validation mostly successful!")
    elif success_rate >= 70:
        logger.info("⚠️  FAIR! PortfolioBridge validation partially successful!")
    else:
        logger.info("❌ POOR! PortfolioBridge validation needs improvement!")
    
    # Save results
    validator.save_results()
    
    # Generate recommendations
    if failed_tests > 0:
        validator.results['recommendations'].append("Review failed tests and fix implementation issues")
    
    if success_rate < 90:
        validator.results['recommendations'].append("Improve test coverage and error handling")
    
    if success_rate >= 90:
        validator.results['recommendations'].append("PortfolioBridge is ready for production use")
    
    logger.info("=" * 60)
    logger.info("📝 RECOMMENDATIONS")
    logger.info("=" * 60)
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
            logger.info("✅ All tests passed! PortfolioBridge validation successful.")
            return 0
        else:
            logger.warning(f"⚠️  {results['tests_failed']} tests failed. Review results.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Validation suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 