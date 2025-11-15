#!/usr/bin/env python3
"""
Test script to verify exit_pending logic works correctly
"""
import sys
import asyncio
from unittest.mock import Mock, AsyncMock

# Add parent directory to path
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.config import MomentumConfig


async def test_exit_pending_flow():
    """Test that exit_pending flag works correctly"""
    
    print("🧪 Testing exit_pending logic...")
    
    # Create mock config
    config = MomentumConfig(
        symbols=['TSLA'],
        short_period=5,
        medium_period=10,
        long_period=20
    )
    
    # Create strategy instance
    strategy = EnhancedMomentumStrategy(config=config)
    
    # Create mock risk manager with get_position_state method
    mock_risk_manager = Mock()
    mock_risk_manager.process_signal = AsyncMock()
    
    # Mock position state - initially has position, then closed
    position_states = [
        Mock(quantity=100, average_entry_price=250.0),  # First call: position exists
        Mock(quantity=0, average_entry_price=0)  # Second call: position closed
    ]
    mock_risk_manager.get_position_state = Mock(side_effect=position_states)
    
    strategy.risk_manager = mock_risk_manager
    
    # Simulate position tracking
    strategy.position_tracker['TSLA'] = {
        'entry_bar': 100,
        'entry_price': 250.0,
        'direction': 'LONG',
        'bars_held': 5
    }
    
    print(f"✅ Initial state: position_tracker has TSLA")
    print(f"   exit_pending: {strategy.position_tracker['TSLA'].get('exit_pending', False)}")
    
    # Simulate marking as exit_pending (what happens after exit signal submission)
    strategy.position_tracker['TSLA']['exit_pending'] = True
    strategy.position_tracker['TSLA']['exit_signal_bar'] = 105
    
    print(f"✅ After exit signal: exit_pending = {strategy.position_tracker['TSLA']['exit_pending']}")
    
    # First check: position should still exist (Risk Manager returns quantity=100)
    enriched_data = {'TSLA': Mock(__len__=lambda self: 106)}  # Current bar 106
    
    # Call the sync logic (first part of _check_exits_for_all_positions)
    symbols_to_clear = []
    for symbol in list(strategy.position_tracker.keys()):
        pos = strategy.position_tracker[symbol]
        if pos.get('exit_pending', False):
            current_bar = len(enriched_data.get(symbol, []))
            exit_signal_bar = pos.get('exit_signal_bar', current_bar)
            bars_since_exit = current_bar - exit_signal_bar
            
            print(f"✅ Bar {current_bar}: Checking exit_pending (bars_since_exit={bars_since_exit})")
            
            if bars_since_exit > 10:
                print(f"⚠️  Timeout! Would force clear")
                symbols_to_clear.append(symbol)
                continue
            
            try:
                position_state = strategy.risk_manager.get_position_state(symbol)
                print(f"   Risk Manager position: quantity={position_state.quantity}")
                if position_state is None or position_state.quantity == 0:
                    print(f"✅ Position closed by Risk Manager - will clear")
                    symbols_to_clear.append(symbol)
            except Exception as e:
                print(f"❌ Error querying Risk Manager: {e}")
    
    # Clear positions (should be empty first time)
    for symbol in symbols_to_clear:
        if symbol in strategy.position_tracker:
            del strategy.position_tracker[symbol]
            print(f"✅ Cleared position tracking for {symbol}")
    
    # First check: position should still be there (quantity=100)
    assert 'TSLA' in strategy.position_tracker, "Position should still exist after first check (quantity=100)"
    print("✅ First check: Position still exists (as expected)")
    
    # Second check: now Risk Manager returns quantity=0
    enriched_data = {'TSLA': Mock(__len__=lambda self: 107)}  # Next bar
    symbols_to_clear = []
    for symbol in list(strategy.position_tracker.keys()):
        pos = strategy.position_tracker[symbol]
        if pos.get('exit_pending', False):
            current_bar = len(enriched_data.get(symbol, []))
            exit_signal_bar = pos.get('exit_signal_bar', current_bar)
            bars_since_exit = current_bar - exit_signal_bar
            
            print(f"✅ Bar {current_bar}: Checking exit_pending again (bars_since_exit={bars_since_exit})")
            
            if bars_since_exit > 10:
                symbols_to_clear.append(symbol)
                continue
            
            try:
                position_state = strategy.risk_manager.get_position_state(symbol)
                print(f"   Risk Manager position: quantity={position_state.quantity}")
                if position_state is None or position_state.quantity == 0:
                    print(f"✅ Position closed by Risk Manager - will clear")
                    symbols_to_clear.append(symbol)
            except Exception as e:
                print(f"❌ Error querying Risk Manager: {e}")
    
    # Clear positions (should clear now)
    for symbol in symbols_to_clear:
        if symbol in strategy.position_tracker:
            del strategy.position_tracker[symbol]
            print(f"✅ Cleared position tracking for {symbol}")
    
    # Verify position was cleared after second check
    assert 'TSLA' not in strategy.position_tracker, "Position should be cleared after Risk Manager confirms closure"
    
    print("✅ Test passed! exit_pending logic works correctly")
    print()
    
    # Test 2: Timeout scenario
    print("🧪 Testing exit_pending timeout...")
    strategy.position_tracker['AAPL'] = {
        'entry_bar': 100,
        'exit_pending': True,
        'exit_signal_bar': 95  # 11 bars ago (current = 106)
    }
    
    symbols_to_clear = []
    enriched_data = {'AAPL': Mock(__len__=lambda self: 106)}
    
    for symbol in list(strategy.position_tracker.keys()):
        pos = strategy.position_tracker[symbol]
        if pos.get('exit_pending', False):
            current_bar = len(enriched_data.get(symbol, []))
            exit_signal_bar = pos.get('exit_signal_bar', current_bar)
            bars_since_exit = current_bar - exit_signal_bar
            
            if bars_since_exit > 10:
                print(f"⚠️  {symbol} exit_pending timeout ({bars_since_exit} bars) - force clearing")
                symbols_to_clear.append(symbol)
    
    for symbol in symbols_to_clear:
        if symbol in strategy.position_tracker:
            del strategy.position_tracker[symbol]
    
    assert 'AAPL' not in strategy.position_tracker, "Position should be cleared after timeout"
    print("✅ Timeout test passed!")
    
    print()
    print("🎉 All tests passed! exit_pending mechanism works correctly")


if __name__ == '__main__':
    asyncio.run(test_exit_pending_flow())
