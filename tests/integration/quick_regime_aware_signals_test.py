#!/usr/bin/env python3
"""
Quick Regime-Aware Signal Enhancement Test
==========================================

Tests regime-aware signal enhancement per Week 3 Day 2.
"""

import asyncio
import sys
import os
from dataclasses import dataclass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core_engine.processing.signals.regime_aware_enhancer import (
    RegimeAwareSignalEnhancer, RegimeSignalAdjustment
)

@dataclass
class MockSignal:
    """Mock signal for testing"""
    symbol: str
    confidence: float
    strategy_type: str

async def main():
    """Test regime-aware signal enhancement"""
    
    print("\n" + "="*80)
    print("Regime-Aware Signal Enhancement - Quick Test")
    print("="*80)
    
    enhancer = RegimeAwareSignalEnhancer()
    
    # Test 1: Momentum signals in trending regime (should amplify)
    print("\n" + "-"*80)
    print("Test 1: Momentum Signals in Trending Regime (should AMPLIFY)")
    print("-"*80)
    
    momentum_signals = [
        MockSignal('AAPL', 0.70, 'momentum'),
        MockSignal('TSLA', 0.65, 'momentum')
    ]
    
    regime_context = {'regime': 'trending', 'confidence': 0.9, 'volatility': 'normal_volatility'}
    
    enhanced = await enhancer.enhance_signals(momentum_signals, regime_context)
    
    print(f"\n📊 Enhancement Results:")
    for sig in enhanced:
        print(f"   {sig.original_signal.symbol}: {sig.original_signal.confidence:.2%} → {sig.adjusted_confidence:.2%}")
        print(f"      Adjustment: {sig.adjustment.value.upper()}")
        print(f"      Reason: {sig.adjustment_reason}")
    
    assert all(s.adjustment == RegimeSignalAdjustment.AMPLIFY for s in enhanced), \
        "Momentum signals should be amplified in trending regime"
    assert all(s.adjusted_confidence > s.original_signal.confidence for s in enhanced), \
        "Adjusted confidence should be higher"
    
    print("   ✅ PASSED")
    
    # Test 2: Mean reversion in trending regime (should reduce)
    print("\n" + "-"*80)
    print("Test 2: Mean Reversion in Trending Regime (should REDUCE)")
    print("-"*80)
    
    mr_signals = [MockSignal('NVDA', 0.75, 'mean_reversion')]
    enhanced = await enhancer.enhance_signals(mr_signals, regime_context)
    
    print(f"\n📊 Enhancement Results:")
    for sig in enhanced:
        print(f"   {sig.original_signal.symbol}: {sig.original_signal.confidence:.2%} → {sig.adjusted_confidence:.2%}")
        print(f"      Adjustment: {sig.adjustment.value.upper()}")
    
    assert enhanced[0].adjustment == RegimeSignalAdjustment.REDUCE, \
        "Mean reversion should be reduced in trending regime"
    assert enhanced[0].adjusted_confidence < mr_signals[0].confidence, \
        "Adjusted confidence should be lower"
    
    print("   ✅ PASSED")
    
    # Test 3: Mean reversion in ranging regime (should amplify)
    print("\n" + "-"*80)
    print("Test 3: Mean Reversion in Ranging Regime (should AMPLIFY)")
    print("-"*80)
    
    ranging_regime = {'regime': 'ranging', 'confidence': 0.85, 'volatility': 'low_volatility'}
    enhanced = await enhancer.enhance_signals(mr_signals, ranging_regime)
    
    print(f"\n📊 Enhancement Results:")
    for sig in enhanced:
        print(f"   {sig.original_signal.symbol}: {sig.original_signal.confidence:.2%} → {sig.adjusted_confidence:.2%}")
        print(f"      Adjustment: {sig.adjustment.value.upper()}")
    
    assert enhanced[0].adjustment == RegimeSignalAdjustment.AMPLIFY, \
        "Mean reversion should be amplified in ranging regime"
    assert enhanced[0].adjusted_confidence > mr_signals[0].confidence, \
        "Adjusted confidence should be higher"
    
    print("   ✅ PASSED")
    
    # Test 4: Breakout in ranging regime (should filter)
    print("\n" + "-"*80)
    print("Test 4: Breakout in Ranging Regime (should FILTER)")
    print("-"*80)
    
    breakout_signals = [MockSignal('SPY', 0.68, 'breakout')]
    enhanced = await enhancer.enhance_signals(breakout_signals, ranging_regime)
    
    print(f"\n📊 Enhancement Results:")
    print(f"   Original signals: {len(breakout_signals)}")
    print(f"   Compatible signals: {len(enhanced)}")
    
    assert len(enhanced) == 0, "Breakout signals should be filtered in ranging regime"
    
    print("   ✅ PASSED - Signal correctly filtered")
    
    # Test 5: Enhancement statistics
    print("\n" + "-"*80)
    print("Test 5: Enhancement Statistics")
    print("-"*80)
    
    mixed_signals = [
        MockSignal('AAPL', 0.70, 'momentum'),
        MockSignal('TSLA', 0.65, 'momentum'),
        MockSignal('NVDA', 0.75, 'mean_reversion'),
        MockSignal('AMD', 0.68, 'unknown')
    ]
    
    enhanced = await enhancer.enhance_signals(mixed_signals, regime_context)
    stats = enhancer.get_enhancement_stats(enhanced)
    
    print(f"\n📊 Enhancement Statistics:")
    print(f"   Total Signals: {stats['total_signals']}")
    print(f"   Amplified: {stats['amplified']}")
    print(f"   Reduced: {stats['reduced']}")
    print(f"   Maintained: {stats['maintained']}")
    print(f"   Filtered: {stats['filtered']}")
    print(f"   Avg Adjustment Factor: {stats['avg_adjustment_factor']:.2f}x")
    print(f"   Regime: {stats['regime']}")
    
    assert stats['total_signals'] > 0, "Should have signals"
    assert stats['amplified'] + stats['reduced'] + stats['maintained'] == stats['total_signals'], \
        "All signals should be categorized"
    
    print("   ✅ PASSED")
    
    print("\n" + "="*80)
    print("✅ ALL REGIME-AWARE SIGNAL TESTS PASSED")
    print("="*80)
    print("\n📋 Summary:")
    print("   - Momentum signals amplified in trending regime ✅")
    print("   - Mean reversion reduced in trending regime ✅")
    print("   - Mean reversion amplified in ranging regime ✅")
    print("   - Breakout signals filtered in ranging regime ✅")
    print("   - Enhancement statistics tracking ✅")
    print("\n🎉 Regime-Aware Signal Enhancement: COMPLETE")
    print("\n💡 Regime Compatibility Matrix:")
    print("   Trending → Momentum/Breakout AMPLIFY, Mean Reversion REDUCE")
    print("   Ranging → Mean Reversion/StatArb AMPLIFY, Breakout FILTER")
    print("   High Volatility → All signals REDUCE")
    print("   Crisis → All signals FILTER")
    
    return True

if __name__ == '__main__':
    asyncio.run(main())

