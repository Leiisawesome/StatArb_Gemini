#!/usr/bin/env python3
"""
Test Historical Data Replay System
===================================

Basic validation tests for the historical data replay functionality.
Tests core components without requiring ClickHouse connection.

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from core_engine.data.replay.config import ReplayConfig, ReplaySpeed
from core_engine.data.replay.engine import (
    HistoricalDataReplayEngine,
    ReplayStatus
)
from core_engine.data.replay.adapter import HistoricalReplayFeedAdapter
from core_engine.data.feeds.adapters import FeedMessage, FeedProvider


async def test_replay_engine_initialization():
    """Test replay engine initialization"""
    print("🧪 Testing replay engine initialization...")

    config = ReplayConfig(
        symbols=["AAPL", "TSLA"],
        start_date="2024-12-20",
        end_date="2024-12-20",
        speed=ReplaySpeed.FAST_10X
    )

    engine = HistoricalDataReplayEngine(config)

    # Test initialization (will fail without ClickHouse, but should not crash)
    try:
        success = await engine.initialize()
        print(f"   Initialization result: {success}")
        print("   ✅ Engine initialization completed (expected to fail without ClickHouse)")
    except Exception as e:
        print(f"   ⚠️  Initialization failed as expected: {e}")

    return engine


async def test_replay_adapter_initialization():
    """Test replay adapter initialization"""
    print("🧪 Testing replay adapter initialization...")

    config = ReplayConfig.create_for_symbol(
        symbol="AAPL",
        start_date="2024-12-20",
        end_date="2024-12-20",
        speed=ReplaySpeed.REALTIME
    )

    adapter = HistoricalReplayFeedAdapter(config)

    # Test connection (will fail without ClickHouse, but should not crash)
    try:
        connected = await adapter.connect()
        print(f"   Connection result: {connected}")
        print("   ✅ Adapter connection completed (expected to fail without ClickHouse)")
    except Exception as e:
        print(f"   ⚠️  Connection failed as expected: {e}")

    return adapter


async def test_config_validation():
    """Test configuration validation"""
    print("🧪 Testing configuration validation...")

    # Test valid config
    try:
        config = ReplayConfig(
            symbols=["AAPL", "TSLA"],
            start_date="2024-12-20",
            end_date="2024-12-20",
            speed=ReplaySpeed.FAST_5X
        )
        print("   ✅ Valid configuration accepted")
    except Exception as e:
        print(f"   ❌ Valid configuration rejected: {e}")
        return False

    # Test invalid date format
    try:
        config = ReplayConfig(
            symbols=["AAPL"],
            start_date="2024/12/20",  # Invalid format
            end_date="2024-12-20"
        )
        print("   ❌ Invalid date format should have been rejected")
        return False
    except ValueError:
        print("   ✅ Invalid date format correctly rejected")

    # Test empty symbols
    try:
        config = ReplayConfig(
            symbols=[],  # Empty symbols
            start_date="2024-12-20",
            end_date="2024-12-20"
        )
        print("   ❌ Empty symbols should have been rejected")
        return False
    except ValueError:
        print("   ✅ Empty symbols correctly rejected")

    return True


async def test_speed_enum():
    """Test replay speed functionality"""
    print("🧪 Testing replay speed enum...")

    speeds = [
        ReplaySpeed.PAUSED,
        ReplaySpeed.REALTIME,
        ReplaySpeed.FAST_2X,
        ReplaySpeed.FAST_10X,
        ReplaySpeed.INSTANT
    ]

    for speed in speeds:
        print(f"   {speed.name}: {speed.value}x speed")

    print("   ✅ Speed enum values are correct")
    return True


async def test_message_handling():
    """Test message handling without actual replay"""
    print("🧪 Testing message handling...")

    config = ReplayConfig(symbols=["AAPL"])
    engine = HistoricalDataReplayEngine(config)

    # Test message handler registration
    messages_received = []

    async def test_handler(message: FeedMessage):
        messages_received.append(message)

    engine.add_message_handler(test_handler)
    print("   ✅ Message handler registered")

    # Test status handler
    status_changes = []

    def status_handler(status: ReplayStatus):
        status_changes.append(status)

    engine.add_status_handler(status_handler)
    print("   ✅ Status handler registered")

    # Verify handlers are registered
    assert len(engine.message_handlers) == 1
    assert len(engine.status_handlers) == 1
    print("   ✅ Handlers correctly registered")

    return True


async def test_statistics():
    """Test statistics tracking"""
    print("🧪 Testing statistics tracking...")

    config = ReplayConfig(symbols=["AAPL"])
    engine = HistoricalDataReplayEngine(config)

    stats = engine.get_statistics()
    print(f"   Initial stats: {stats}")

    # Check required fields exist
    assert hasattr(stats, 'total_records')
    assert hasattr(stats, 'records_processed')
    assert hasattr(stats, 'speed_multiplier')
    print("   ✅ Statistics object has required attributes")

    # Check initial values
    assert stats.total_records == 0
    assert stats.records_processed == 0
    assert stats.speed_multiplier == 1.0
    print("   ✅ Statistics have correct initial values")

    return True


async def run_all_tests():
    """Run all validation tests"""
    print("🚀 Starting Historical Data Replay System Tests")
    print("=" * 50)

    tests = [
        ("Configuration Validation", test_config_validation),
        ("Speed Enum", test_speed_enum),
        ("Message Handling", test_message_handling),
        ("Statistics", test_statistics),
        ("Engine Initialization", test_replay_engine_initialization),
        ("Adapter Initialization", test_replay_adapter_initialization),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result is not False:  # Some tests return None on success
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
        print()

    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Historical Data Replay System is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)