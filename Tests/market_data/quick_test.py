#!/usr/bin/env python3
"""
Quick Market Data Test
=====================

Simple test runner that works without optional dependencies.
Tests core functionality of the market_data module.

Usage:
    python quick_test.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test basic imports"""
    print("🔍 Testing Market Data Module Imports...")
    
    try:
        from core_structure.market_data import (
            DataManager, 
            FeedManager, 
            MarketTick, 
            DataType, 
            FeedStatus,
            DATA_PROCESSOR_AVAILABLE
        )
        print("✅ Core imports successful")
        print(f"📊 DataProcessor available: {DATA_PROCESSOR_AVAILABLE}")
        
        if DATA_PROCESSOR_AVAILABLE:
            try:
                from core_structure.market_data import DataProcessor, ProcessedData, ProcessingStage
                print("✅ DataProcessor imports successful")
            except ImportError as e:
                print(f"⚠️  DataProcessor import failed: {e}")
        else:
            print("⚠️  DataProcessor not available (missing dependencies)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_market_tick():
    """Test MarketTick functionality"""
    print("\n🧪 Testing MarketTick...")
    
    try:
        from core_structure.market_data import MarketTick, DataType
        from datetime import datetime
        
        # Create a market tick
        tick = MarketTick(
            symbol="AAPL",
            timestamp=datetime.now(),
            price=150.0,
            volume=1000,
            bid=149.5,
            ask=150.5
        )
        
        # Test basic properties
        assert tick.symbol == "AAPL"
        assert tick.price == 150.0
        assert tick.volume == 1000
        assert tick.data_type == DataType.TICK
        
        # Test serialization
        tick_dict = tick.to_dict()
        assert tick_dict['symbol'] == "AAPL"
        assert tick_dict['price'] == 150.0
        assert tick_dict['data_type'] == "tick"
        
        print("✅ MarketTick tests passed")
        return True
        
    except Exception as e:
        print(f"❌ MarketTick test failed: {e}")
        return False

def test_enums():
    """Test enum classes"""
    print("\n🧪 Testing Enums...")
    
    try:
        from core_structure.market_data import DataType, FeedStatus
        
        # Test DataType enum
        assert DataType.TICK.value == "tick"
        assert DataType.QUOTE.value == "quote"
        assert DataType.TRADE.value == "trade"
        
        # Test FeedStatus enum
        assert FeedStatus.CONNECTED.value == "connected"
        assert FeedStatus.DISCONNECTED.value == "disconnected"
        assert FeedStatus.ERROR.value == "error"
        
        print("✅ Enum tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

def test_managers_initialization():
    """Test manager initialization without external dependencies"""
    print("\n🧪 Testing Manager Initialization...")
    
    try:
        from core_structure.market_data import DataManager, FeedManager
        
        # Test basic initialization with minimal config
        config = {
            'cache_ttl_seconds': 300,
            'real_time_enabled': False,  # Disable to avoid external connections
            'max_symbols_per_query': 10
        }
        
        # This might fail if it tries to connect to ClickHouse
        # We'll catch and handle that gracefully
        try:
            data_manager = DataManager(config=config)
            print("✅ DataManager initialized")
        except Exception as e:
            print(f"⚠️  DataManager initialization failed (expected if no ClickHouse): {e}")
        
        # FeedManager should initialize without issues
        feed_manager = FeedManager(config=config)
        assert feed_manager is not None
        print("✅ FeedManager initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Manager initialization test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("🚀 Quick Market Data Module Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_market_tick,
        test_enums,
        test_managers_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All basic tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
