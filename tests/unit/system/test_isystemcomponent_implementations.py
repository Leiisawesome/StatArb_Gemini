#!/usr/bin/env python3
"""
Test ISystemComponent Implementation for SystemValidator and SystemMonitor
==========================================================================

Verifies that both SystemValidator and SystemMonitor properly implement
the ISystemComponent interface.

Author: StatArb_Gemini Code Review Fixes
Date: October 21, 2025
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.system.system_validator import SystemValidator, ValidationLevel
from core_engine.system.orchestrator_monitoring import SystemMonitor
from core_engine.system.interfaces import ISystemComponent

async def test_system_validator_interface():
    """Test SystemValidator implements ISystemComponent"""
    print("\n" + "="*80)
    print("TEST: SystemValidator ISystemComponent Implementation")
    print("="*80 + "\n")

    # Test 1: Instance creation
    validator = SystemValidator(ValidationLevel.BASIC)
    assert isinstance(validator, ISystemComponent), "SystemValidator must implement ISystemComponent"
    print("✅ Test 1.1: SystemValidator implements ISystemComponent")

    # Test 2: Initialize
    result = await validator.initialize()
    assert result is True, "Initialize should return True"
    assert validator.is_initialized is True, "is_initialized should be True"
    print("✅ Test 1.2: initialize() works correctly")

    # Test 3: Start
    result = await validator.start()
    assert result is True, "Start should return True"
    assert validator.is_operational is True, "is_operational should be True"
    print("✅ Test 1.3: start() works correctly")

    # Test 4: Health check
    health = await validator.health_check()
    assert isinstance(health, dict), "health_check should return dict"
    assert health['healthy'] is True, "Should be healthy"
    assert health['component_type'] == 'SystemValidator', "Component type should be SystemValidator"
    print("✅ Test 1.4: health_check() returns proper dict")

    # Test 5: Get status
    status = validator.get_status()
    assert isinstance(status, dict), "get_status should return dict"
    assert status['operational'] is True, "Should be operational"
    assert status['component_type'] == 'SystemValidator', "Component type should be SystemValidator"
    print("✅ Test 1.5: get_status() returns proper dict")

    # Test 6: Stop
    result = await validator.stop()
    assert result is True, "Stop should return True"
    assert validator.is_operational is False, "is_operational should be False"
    print("✅ Test 1.6: stop() works correctly")

    print("\n🎉 SystemValidator: ALL TESTS PASSED (6/6)")

async def test_system_monitor_interface():
    """Test SystemMonitor implements ISystemComponent"""
    print("\n" + "="*80)
    print("TEST: SystemMonitor ISystemComponent Implementation")
    print("="*80 + "\n")

    # Test 1: Instance creation
    monitor = SystemMonitor()
    assert isinstance(monitor, ISystemComponent), "SystemMonitor must implement ISystemComponent"
    print("✅ Test 2.1: SystemMonitor implements ISystemComponent")

    # Test 2: Initialize
    result = await monitor.initialize()
    assert result is True, "Initialize should return True"
    assert monitor.is_initialized is True, "is_initialized should be True"
    print("✅ Test 2.2: initialize() works correctly")

    # Test 3: Start
    result = await monitor.start()
    assert result is True, "Start should return True"
    assert monitor.is_operational is True, "is_operational should be True"
    assert monitor.is_monitoring is True, "Monitoring should be active"
    print("✅ Test 2.3: start() works correctly")

    # Wait a moment for monitoring to start
    await asyncio.sleep(0.5)

    # Test 4: Health check
    health = await monitor.health_check()
    assert isinstance(health, dict), "health_check should return dict"
    assert health['component_type'] == 'SystemMonitor', "Component type should be SystemMonitor"
    assert health['monitoring_active'] is True, "Monitoring should be active"
    print("✅ Test 2.4: health_check() returns proper dict")

    # Test 5: Get status
    status = monitor.get_status()
    assert isinstance(status, dict), "get_status should return dict"
    assert status['operational'] is True, "Should be operational"
    assert status['component_type'] == 'SystemMonitor', "Component type should be SystemMonitor"
    assert status['monitoring_active'] is True, "Monitoring should be active"
    print("✅ Test 2.5: get_status() returns proper dict")

    # Test 6: Stop
    result = await monitor.stop()
    assert result is True, "Stop should return True"
    assert monitor.is_operational is False, "is_operational should be False"
    assert monitor.is_monitoring is False, "Monitoring should be stopped"
    print("✅ Test 2.6: stop() works correctly")

    print("\n🎉 SystemMonitor: ALL TESTS PASSED (6/6)")

async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("ISYSTEMCOMPONENT IMPLEMENTATION TESTS")
    print("="*80)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    # Test SystemValidator
    try:
        await test_system_validator_interface()
        passed_tests += 6
        total_tests += 6
    except Exception as e:
        failed_tests += 1
        total_tests += 6
        print(f"\n❌ SystemValidator tests FAILED: {e}")

    # Test SystemMonitor
    try:
        await test_system_monitor_interface()
        passed_tests += 6
        total_tests += 6
    except Exception as e:
        failed_tests += 1
        total_tests += 6
        print(f"\n❌ SystemMonitor tests FAILED: {e}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! ISystemComponent implementation verified!")
        return 0
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

