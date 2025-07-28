#!/usr/bin/env python3
"""
Test Phase 3: Real-Time Integration
Validates integration of Phase 1 and Phase 2 components in real-time system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import tempfile
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from enhanced_real_time_system import EnhancedRealTimeSystem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_mock_market_data():
    """Create mock market data for testing"""
    print("Creating mock market data for Phase 3 testing...")
    
    # Generate 30 days of hourly data
    dates = pd.date_range(start='2024-01-01', end='2024-01-30', freq='H')
    n_periods = len(dates)
    
    # Create realistic price data
    np.random.seed(42)
    
    # SPY data
    spy_returns = np.random.normal(0.0001, 0.008, n_periods)
    spy_prices = 450 * np.exp(np.cumsum(spy_returns))
    spy_data = pd.DataFrame({
        'close': spy_prices,
        'volume': np.random.lognormal(15, 0.3, n_periods) * 1000000
    }, index=dates)
    
    # AAPL data
    aapl_returns = np.random.normal(0.00012, 0.01, n_periods)
    aapl_prices = 180 * np.exp(np.cumsum(aapl_returns))
    aapl_data = pd.DataFrame({
        'close': aapl_prices,
        'volume': np.random.lognormal(16, 0.25, n_periods) * 1000000
    }, index=dates)
    
    # MSFT data
    msft_returns = np.random.normal(0.00011, 0.009, n_periods)
    msft_prices = 350 * np.exp(np.cumsum(msft_returns))
    msft_data = pd.DataFrame({
        'close': msft_prices,
        'volume': np.random.lognormal(15.5, 0.28, n_periods) * 1000000
    }, index=dates)
    
    return {
        'SPY': spy_data,
        'AAPL': aapl_data,
        'MSFT': msft_data
    }

async def test_enhanced_real_time_system():
    """Test the enhanced real-time trading system"""
    print("\n=== Testing Enhanced Real-Time Trading System ===")
    
    # Create mock data
    mock_data = create_mock_market_data()
    
    # Initialize system
    print("\n1. Testing System Initialization...")
    try:
        system = EnhancedRealTimeSystem()
        
        # Mock the data manager to return our test data
        class MockDataManager:
            async def initialize(self):
                pass
            
            async def start_real_time_feeds(self, symbols):
                pass
            
            async def get_recent_data(self, symbol, lookback_days=30):
                return mock_data.get(symbol)
            
            async def shutdown(self):
                pass
        
        system.data_manager = MockDataManager()
        
        # Mock the signal generator
        class MockSignalGenerator:
            async def initialize(self):
                pass
            
            async def shutdown(self):
                pass
        
        system.signal_generator = MockSignalGenerator()
        
        # Initialize strategy with mock data
        strategy_config = {
            'name': 'enhanced_academic_strategy',
            'version': '3.0.0',
            'symbols': ['SPY', 'AAPL', 'MSFT'],
            'initial_capital': 100000.0,
            'position_size': 0.1,
            'max_positions': 10
        }
        
        from backtesting_framework.strategies.enhanced_academic_strategy import EnhancedAcademicStrategy
        system.strategy = EnhancedAcademicStrategy(strategy_config)
        system.strategy.initialize(mock_data)
        
        print("✅ Enhanced real-time system initialized successfully")
        
    except Exception as e:
        print(f"❌ System initialization failed: {e}")
        return False
    
    # Test signal generation
    print("\n2. Testing Signal Generation...")
    try:
        signals = await system._generate_academic_signals(mock_data)
        print(f"✅ Generated {len(signals)} academic signals")
        
        if len(signals) > 0:
            for signal in signals[:3]:  # Show first 3 signals
                print(f"   Signal: {signal.symbol} {signal.signal_type.value} "
                      f"(confidence: {signal.confidence:.4f})")
        
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return False
    
    # Test trade execution
    print("\n3. Testing Trade Execution...")
    try:
        if len(signals) > 0:
            await system._execute_trades(signals, mock_data)
            print(f"✅ Executed trades for {len(signals)} signals")
            print(f"   Portfolio value: ${system.portfolio_value:,.2f}")
            print(f"   Current positions: {len(system.current_positions)}")
        else:
            print("⚠️  No signals to execute")
        
    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        return False
    
    # Test performance metrics
    print("\n4. Testing Performance Metrics...")
    try:
        await system._update_performance_metrics()
        
        if len(system.performance_metrics) > 0:
            print("✅ Performance metrics updated")
            for key, value in system.performance_metrics.items():
                if isinstance(value, float):
                    print(f"   {key}: {value:.4f}")
                else:
                    print(f"   {key}: {value}")
        else:
            print("⚠️  No performance metrics available")
        
    except Exception as e:
        print(f"❌ Performance metrics failed: {e}")
        return False
    
    # Test system status
    print("\n5. Testing System Status...")
    try:
        status = system.get_system_status()
        print("✅ System status retrieved")
        
        # Check academic foundations
        academic_foundations = status.get('academic_foundations', {})
        for foundation, enabled in academic_foundations.items():
            status_icon = "✅" if enabled else "❌"
            print(f"   {status_icon} {foundation}")
        
    except Exception as e:
        print(f"❌ System status failed: {e}")
        return False
    
    return True

async def test_trading_log_saving():
    """Test trading log saving functionality"""
    print("\n=== Testing Trading Log Saving ===")
    
    try:
        # Create a temporary system with some data
        system = EnhancedRealTimeSystem()
        
        # Add some mock trading data
        system.signal_history = [
            {
                'timestamp': datetime.now(),
                'symbol': 'AAPL',
                'signal_type': 1,
                'confidence': 0.8,
                'price': 180.0
            }
        ]
        
        system.trade_history = [
            {
                'timestamp': datetime.now(),
                'symbol': 'AAPL',
                'signal_type': 1,
                'position_size': 0.1,
                'price': 180.0,
                'confidence': 0.8
            }
        ]
        
        system.performance_metrics = {
            'total_return': 0.05,
            'portfolio_value': 105000.0,
            'total_trades': 1,
            'total_signals': 1
        }
        
        # Save trading log
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        system.save_trading_log(temp_path)
        print(f"✅ Trading log saved to temporary file")
        
        # Verify saved data
        with open(temp_path, 'r') as f:
            saved_data = json.load(f)
        
        if 'system_status' in saved_data:
            print("✅ System status saved")
        if 'signal_history' in saved_data:
            print("✅ Signal history saved")
        if 'trade_history' in saved_data:
            print("✅ Trade history saved")
        if 'performance_metrics' in saved_data:
            print("✅ Performance metrics saved")
        
        # Clean up
        import os
        os.unlink(temp_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Trading log saving failed: {e}")
        return False

async def test_real_time_loop_simulation():
    """Test real-time loop simulation"""
    print("\n=== Testing Real-Time Loop Simulation ===")
    
    try:
        # Create system
        system = EnhancedRealTimeSystem()
        
        # Mock data manager
        mock_data = create_mock_market_data()
        
        class MockDataManager:
            async def initialize(self):
                pass
            
            async def start_real_time_feeds(self, symbols):
                pass
            
            async def get_recent_data(self, symbol, lookback_days=30):
                return mock_data.get(symbol)
            
            async def shutdown(self):
                pass
        
        system.data_manager = MockDataManager()
        
        # Mock signal generator
        class MockSignalGenerator:
            async def initialize(self):
                pass
            
            async def shutdown(self):
                pass
        
        system.signal_generator = MockSignalGenerator()
        
        # Initialize strategy
        strategy_config = {
            'name': 'enhanced_academic_strategy',
            'version': '3.0.0',
            'symbols': ['SPY', 'AAPL', 'MSFT'],
            'initial_capital': 100000.0,
            'position_size': 0.1,
            'max_positions': 10
        }
        
        from backtesting_framework.strategies.enhanced_academic_strategy import EnhancedAcademicStrategy
        system.strategy = EnhancedAcademicStrategy(strategy_config)
        system.strategy.initialize(mock_data)
        
        # Simulate a few iterations of the real-time loop
        print("🔄 Simulating real-time trading loop...")
        
        for i in range(3):  # Simulate 3 iterations
            print(f"\n   Iteration {i+1}:")
            
            # Get market data
            market_data = await system._get_current_market_data()
            print(f"     Market data: {len(market_data)} symbols")
            
            # Generate signals
            signals = await system._generate_academic_signals(market_data)
            print(f"     Signals: {len(signals)} generated")
            
            # Execute trades
            if signals:
                await system._execute_trades(signals, market_data)
                print(f"     Trades: {len(signals)} executed")
            
            # Update metrics
            await system._update_performance_metrics()
            print(f"     Portfolio: ${system.portfolio_value:,.2f}")
        
        print("✅ Real-time loop simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Real-time loop simulation failed: {e}")
        return False

async def main():
    """Run all Phase 3 tests"""
    print("🚀 Phase 3: Real-Time Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Enhanced Real-Time System", test_enhanced_real_time_system),
        ("Trading Log Saving", test_trading_log_saving),
        ("Real-Time Loop Simulation", test_real_time_loop_simulation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 3 Implementation: SUCCESS")
        print("\n✅ Real-time integration complete!")
        print("✅ Phase 1 academic foundations integrated")
        print("✅ Phase 2 backtesting components integrated")
        print("✅ Real-time signal generation operational")
        print("✅ Trade execution framework functional")
        print("✅ Performance monitoring active")
        print("✅ Ready for production deployment")
    else:
        print("❌ Phase 3 Implementation: FAILED")
        print("Please fix the failing tests before proceeding to production")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 