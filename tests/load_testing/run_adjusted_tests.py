"""
Quick Test Runner with Adjusted Risk Limits

Runs a quick test with higher risk limits to demonstrate realistic fill rates.
"""

import asyncio
import logging
from orchestrator import LoadTestOrchestrator
from order_generator import OrderPattern
from mock_trading_system import MockTradingSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_adjusted_quick_test():
    """Run quick test with adjusted risk limits"""
    
    # Create orchestrator with higher limits
    orchestrator = LoadTestOrchestrator("quick_adjusted")
    
    # Override trading system with higher limits
    orchestrator.trading_system = MockTradingSystem(
        max_position_size=100000,  # 100K shares (vs 10K default)
        max_total_exposure=100_000_000  # $100M (vs $1M default)
    )
    
    print("="*80)
    print("ADJUSTED QUICK TEST - Higher Risk Limits for Realistic Fill Rates")
    print("="*80)
    print("Max Position Size: 100,000 shares")
    print("Max Exposure: $100,000,000")
    print("Expected Fill Rate: ~95%")
    print("="*80 + "\n")
    
    # Run test
    results = await orchestrator.run_test(
        duration_seconds=60,
        target_orders=1000,
        pattern=OrderPattern.STEADY,
        batch_size=10
    )
    
    return results

async def run_standard_test():
    """Run standard 30-minute test"""
    
    orchestrator = LoadTestOrchestrator("standard_load")
    
    # Higher limits for long test
    orchestrator.trading_system = MockTradingSystem(
        max_position_size=100000,
        max_total_exposure=100_000_000
    )
    
    print("="*80)
    print("STANDARD LOAD TEST - 30 Minutes, 10K Orders")
    print("="*80)
    print("Duration: 30 minutes (1,800 seconds)")
    print("Target Orders: 10,000")
    print("Pattern: Market Hours")
    print("="*80 + "\n")
    
    results = await orchestrator.run_test(
        duration_seconds=1800,
        target_orders=10000,
        pattern=OrderPattern.MARKET_HOURS,
        batch_size=20
    )
    
    return results

async def run_stress_test(duration_minutes=10):
    """Run stress test with burst pattern"""
    
    orchestrator = LoadTestOrchestrator("stress_test")
    
    # Very high limits for stress test
    orchestrator.trading_system = MockTradingSystem(
        max_position_size=1_000_000,
        max_total_exposure=1_000_000_000
    )
    
    target_orders = duration_minutes * 1000
    
    print("="*80)
    print(f"STRESS TEST - {duration_minutes} Minutes, Maximum Load")
    print("="*80)
    print(f"Duration: {duration_minutes} minutes ({duration_minutes * 60} seconds)")
    print(f"Target Orders: {target_orders:,}")
    print("Pattern: Burst")
    print("Batch Size: 50")
    print("="*80 + "\n")
    
    results = await orchestrator.run_test(
        duration_seconds=duration_minutes * 60,
        target_orders=target_orders,
        pattern=OrderPattern.BURST,
        batch_size=50
    )
    
    return results

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == 'quick':
            asyncio.run(run_adjusted_quick_test())
        elif test_type == 'standard':
            asyncio.run(run_standard_test())
        elif test_type == 'stress':
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            asyncio.run(run_stress_test(duration))
        else:
            print("Usage: python run_adjusted_tests.py [quick|standard|stress] [duration_minutes]")
    else:
        print("Running adjusted quick test by default...\n")
        asyncio.run(run_adjusted_quick_test())
