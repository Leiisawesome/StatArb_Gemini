#!/usr/bin/env python3
"""
Phase 2 Error Handling Validation Test
=====================================

Tests circuit breakers, retry mechanisms, and error recovery patterns
to ensure they work correctly under various failure scenarios.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from core_structure.analytics.error_handling import (
    error_handling_manager,
    CircuitBreakerError,
    MaxRetriesExceededError,
    CircuitBreakerState
)
from core_structure.analytics.core_analytics import CoreAnalyticsEngine
from core_structure.analytics.monitoring_analytics import MonitoringAnalyticsEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_circuit_breaker_functionality():
    """Test circuit breaker behavior under failure conditions"""
    logger.info("🔧 Testing Circuit Breaker Functionality")
    
    # Create a test circuit breaker
    test_cb = error_handling_manager.circuit_breakers.get("database")
    if not test_cb:
        logger.error("Database circuit breaker not found")
        return False
    
    # Test normal operation
    try:
        async def normal_operation():
            await asyncio.sleep(0.1)  # Simulate work
            return "success"
        
        result = await test_cb(normal_operation)
        assert result == "success", "Normal operation should succeed"
        assert test_cb.state == CircuitBreakerState.CLOSED, "Circuit should remain closed"
        logger.info("✅ Normal operation test passed")
        
    except Exception as e:
        logger.error(f"❌ Normal operation test failed: {e}")
        return False
    
    # Test failure scenarios
    failure_count = 0
    try:
        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            raise ValueError(f"Simulated failure #{failure_count}")
        
        # Trigger failures to open circuit
        for i in range(test_cb.failure_threshold + 1):
            try:
                await test_cb(failing_operation)
            except (ValueError, CircuitBreakerError):
                pass  # Expected failures
        
        # Check if circuit is open
        if test_cb.state == CircuitBreakerState.OPEN:
            logger.info("✅ Circuit breaker opened after threshold failures")
        else:
            logger.warning(f"⚠️ Circuit breaker state: {test_cb.state.value} (expected: OPEN)")
        
        # Test fail-fast behavior
        try:
            await test_cb(normal_operation)
            logger.error("❌ Circuit should fail fast when open")
            return False
        except CircuitBreakerError:
            logger.info("✅ Circuit breaker failing fast correctly")
        
    except Exception as e:
        logger.error(f"❌ Circuit breaker failure test failed: {e}")
        return False
    
    return True


async def test_retry_mechanism():
    """Test retry manager with exponential backoff"""
    logger.info("🔄 Testing Retry Mechanism")
    
    retry_manager = error_handling_manager.retry_managers.get("database")
    if not retry_manager:
        logger.error("Database retry manager not found")
        return False
    
    # Test successful retry
    attempt_count = 0
    try:
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:  # Fail first attempt, succeed second
                raise ValueError(f"Attempt {attempt_count} failed")
            return f"success_on_attempt_{attempt_count}"
        
        result = await retry_manager.execute_with_retry(
            flaky_operation,
            "flaky_test",
            (ValueError,)
        )
        
        assert "success_on_attempt_2" in result, "Should succeed on second attempt"
        logger.info(f"✅ Retry mechanism successful: {result}")
        
    except Exception as e:
        logger.error(f"❌ Retry mechanism test failed: {e}")
        return False
    
    # Test max retries exceeded
    attempt_count = 0
    try:
        async def always_failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            raise RuntimeError(f"Always fails - attempt {attempt_count}")
        
        await retry_manager.execute_with_retry(
            always_failing_operation,
            "always_fail_test",
            (RuntimeError,)
        )
        
        logger.error("❌ Should have raised MaxRetriesExceededError")
        return False
        
    except MaxRetriesExceededError:
        logger.info("✅ Max retries exceeded correctly detected")
    except Exception as e:
        logger.error(f"❌ Unexpected exception: {e}")
        return False
    
    return True


async def test_analytics_error_handling():
    """Test error handling in analytics operations"""
    logger.info("📊 Testing Analytics Error Handling")
    
    # Reset circuit breakers before testing
    error_handling_manager.reset_all_circuit_breakers()
    
    core_analytics = CoreAnalyticsEngine()
    
    # Test with invalid data
    try:
        # Empty returns
        result = await core_analytics.analyze_performance(pd.Series(dtype=float))
        assert result is not None, "Should return default metrics for empty data"
        logger.info("✅ Empty data handling test passed")
        
        # NaN returns
        nan_returns = pd.Series([np.nan, np.nan, np.nan])
        result = await core_analytics.analyze_performance(nan_returns)
        assert result is not None, "Should handle NaN data gracefully"
        logger.info("✅ NaN data handling test passed")
        
        # Valid data
        valid_returns = pd.Series([0.01, -0.02, 0.015, -0.005, 0.02])
        result = await core_analytics.analyze_performance(valid_returns)
        assert result is not None, "Should process valid data"
        assert result.total_return != 0, "Should calculate meaningful metrics"
        logger.info("✅ Valid data processing test passed")
        
    except Exception as e:
        logger.error(f"❌ Analytics error handling test failed: {e}")
        return False
    
    return True


async def test_monitoring_error_handling():
    """Test error handling in monitoring operations"""
    logger.info("🔍 Testing Monitoring Error Handling")
    
    # Reset circuit breakers before testing
    error_handling_manager.reset_all_circuit_breakers()
    
    monitoring = MonitoringAnalyticsEngine()
    
    try:
        # Test with empty data
        anomalies = await monitoring.detect_anomalies(pd.DataFrame(), "test_metric")
        assert isinstance(anomalies, list), "Should return empty list for empty data"
        logger.info("✅ Empty data anomaly detection test passed")
        
        # Test with minimal data
        small_data = pd.DataFrame({'value': [1, 2, 3]})  # Less than minimum 10 rows
        anomalies = await monitoring.detect_anomalies(small_data, "test_metric")
        assert isinstance(anomalies, list), "Should handle insufficient data gracefully"
        logger.info("✅ Insufficient data handling test passed")
        
        # Test alert creation with invalid inputs
        from core_structure.analytics.monitoring_analytics import AlertSeverity, AlertType
        alert = await monitoring.create_alert(
            severity=AlertSeverity.INFO,  # Valid severity
            alert_type=AlertType.SYSTEM,  # Valid type
            title="Test Alert",  # Valid title
            message="Test message",  # Valid message
            source="test"  # Valid source
        )
        assert alert is not None, "Should create alert successfully"
        logger.info("✅ Valid alert creation test passed")
        
    except Exception as e:
        logger.error(f"❌ Monitoring error handling test failed: {e}")
        return False
    
    return True


async def test_error_handling_health_status():
    """Test error handling health monitoring"""
    logger.info("💊 Testing Error Handling Health Status")
    
    try:
        health_status = error_handling_manager.get_health_status()
        
        # Validate structure
        assert "circuit_breakers" in health_status, "Should include circuit breaker status"
        assert "retry_managers" in health_status, "Should include retry manager status"
        
        # Check circuit breakers
        cb_status = health_status["circuit_breakers"]
        for name, status in cb_status.items():
            assert "state" in status, f"Circuit breaker {name} should have state"
            assert "stats" in status, f"Circuit breaker {name} should have stats"
            assert "config" in status, f"Circuit breaker {name} should have config"
        
        # Check retry managers
        rm_status = health_status["retry_managers"]
        for name, status in rm_status.items():
            assert "config" in status, f"Retry manager {name} should have config"
        
        logger.info("✅ Health status validation passed")
        logger.info(f"📊 Found {len(cb_status)} circuit breakers and {len(rm_status)} retry managers")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Health status test failed: {e}")
        return False


async def main():
    """Run all Phase 2 error handling validation tests"""
    logger.info("🚀 Starting Phase 2 Error Handling Validation Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Circuit Breaker Functionality", test_circuit_breaker_functionality),
        ("Retry Mechanism", test_retry_mechanism),
        ("Analytics Error Handling", test_analytics_error_handling),
        ("Monitoring Error Handling", test_monitoring_error_handling),
        ("Health Status Monitoring", test_error_handling_health_status)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"   {status}: {test_name}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"   ❌ FAILED: {test_name} - {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 Phase 2 Error Handling Validation Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {status}: {test_name}")
    
    logger.info("-" * 60)
    logger.info(f"📊 Results: {passed}/{total} tests passed ({(passed/total*100):.1f}%)")
    
    if passed == total:
        logger.info("🎉 All Phase 2 error handling tests passed successfully!")
        return True
    else:
        logger.error(f"⚠️ {total - passed} tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    asyncio.run(main())