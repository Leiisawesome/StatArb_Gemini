"""
System Profiler
===============

Profile actual trading system components to identify bottlenecks.

Profiles:
1. Mock trading system components
2. Load testing framework
3. End-to-end order processing
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.performance.profiler import PerformanceProfiler
from tests.performance.memory_profiler import MemoryProfiler
from tests.load_testing.mock_trading_system import (
    MockMarketData,
    MockRiskManager,
    MockPositionTracker,
    MockTradingSystem
)
from tests.load_testing.order_generator import OrderGenerator, OrderGeneratorConfig, OrderPattern


def profile_market_data(iterations: int = 1000):
    """Profile market data operations"""
    print("\n" + "="*80)
    print("PROFILING: Market Data Operations")
    print("="*80)
    
    market_data = MockMarketData()
    
    def get_prices():
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        prices = {}
        for symbol in symbols:
            prices[symbol] = market_data.get_price(symbol)
        return prices
    
    profiler = PerformanceProfiler("market_data")
    profiler.start()
    
    for _ in range(iterations):
        get_prices()
    
    profiler.stop()
    stats = profiler.get_stats(top_n=10)
    profiler.print_summary()
    
    return stats


async def profile_risk_manager(iterations: int = 1000):
    """Profile risk management operations"""
    print("\n" + "="*80)
    print("PROFILING: Risk Management")
    print("="*80)
    
    risk_manager = MockRiskManager()
    market_data = MockMarketData()
    
    async def check_risk():
        order = {
            'symbol': 'AAPL',
            'side': 'BUY',
            'quantity': 100,
            'price': market_data.get_price('AAPL'),
            'order_type': 'LIMIT'
        }
        return await risk_manager.check_order(order, current_position=0, total_exposure=0.0)
    
    profiler = PerformanceProfiler("risk_manager")
    profiler.start()
    
    for _ in range(iterations):
        await check_risk()
    
    profiler.stop()
    stats = profiler.get_stats(top_n=10)
    profiler.print_summary()
    
    return stats


def profile_position_tracker(iterations: int = 500):
    """Profile position tracking operations"""
    print("\n" + "="*80)
    print("PROFILING: Position Tracking")
    print("="*80)
    
    position_tracker = MockPositionTracker()
    market_data = MockMarketData()
    
    def update_positions():
        # Add some positions
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        for symbol in symbols:
            position_tracker.update_position(symbol, 100, market_data.get_price(symbol))
        
        # Get summary
        summary = position_tracker.get_summary()
        
        return summary
    
    profiler = PerformanceProfiler("position_tracker")
    profiler.start()
    
    for _ in range(iterations):
        update_positions()
    
    profiler.stop()
    stats = profiler.get_stats(top_n=10)
    profiler.print_summary()
    
    return stats


async def profile_order_execution(num_orders: int = 100):
    """Profile order execution pipeline"""
    print("\n" + "="*80)
    print("PROFILING: Order Execution Pipeline")
    print("="*80)
    
    system = MockTradingSystem()
    
    # Generate orders
    config = OrderGeneratorConfig(
        symbols=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'],
        pattern=OrderPattern.CONSTANT
    )
    generator = OrderGenerator(config)
    orders = generator.generate_orders(num_orders)
    
    profiler = PerformanceProfiler("order_execution")
    memory_profiler = MemoryProfiler("order_execution_memory")
    
    profiler.start()
    memory_profiler.start()
    memory_profiler.take_snapshot("start")
    
    # Submit orders
    results = []
    for i, order in enumerate(orders):
        result = await system.submit_order(order)
        results.append(result)
        
        # Take memory snapshots periodically
        if (i + 1) % 20 == 0:
            memory_profiler.take_snapshot(f"after_{i+1}_orders")
    
    memory_profiler.take_snapshot("end")
    memory_profiler.stop()
    profiler.stop()
    
    stats = profiler.get_stats(top_n=15)
    profiler.print_summary()
    memory_profiler.print_summary()
    
    return stats, results


def profile_order_generation(num_orders: int = 1000):
    """Profile order generation"""
    print("\n" + "="*80)
    print("PROFILING: Order Generation")
    print("="*80)
    
    profiler = PerformanceProfiler("order_generation")
    profiler.start()
    
    config = OrderGeneratorConfig(
        symbols=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD'],
        pattern=OrderPattern.RANDOM
    )
    generator = OrderGenerator(config)
    generator.generate_orders(num_orders)
    
    profiler.stop()
    stats = profiler.get_stats(top_n=10)
    profiler.print_summary()
    
    return stats


def run_full_system_profile(num_orders: int = 100):
    """Run comprehensive system profiling"""
    print("\n" + "="*80)
    print("COMPREHENSIVE SYSTEM PROFILING")
    print("="*80)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Orders to process: {num_orders}")
    
    results = {}
    
    # Profile each component
    print("\n📊 Profiling individual components...")
    
    results['market_data'] = profile_market_data(iterations=1000)
    results['risk_manager'] = asyncio.run(profile_risk_manager(iterations=1000))
    results['position_tracker'] = profile_position_tracker(iterations=500)
    results['order_generation'] = profile_order_generation(num_orders=1000)
    
    # Profile end-to-end
    print("\n📊 Profiling end-to-end order processing...")
    stats, order_results = asyncio.run(profile_order_execution(num_orders=num_orders))
    results['order_execution'] = stats
    
    # Summary
    print("\n" + "="*80)
    print("PROFILING COMPLETE")
    print("="*80)
    
    # Calculate fill rate
    filled = sum(1 for r in order_results if r['status'] == 'FILLED')
    rejected = sum(1 for r in order_results if r['status'] == 'REJECTED')
    
    print(f"\n📈 Order Processing Summary:")
    print(f"   Total Orders:  {len(order_results)}")
    print(f"   Filled:        {filled} ({filled/len(order_results)*100:.1f}%)")
    print(f"   Rejected:      {rejected} ({rejected/len(order_results)*100:.1f}%)")
    
    print("\n💡 Key Findings:")
    print("   Check the detailed output above for:")
    print("   1. Top time-consuming functions")
    print("   2. Memory usage patterns")
    print("   3. Potential bottlenecks")
    
    print("\n" + "="*80 + "\n")
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Profile trading system')
    parser.add_argument('--orders', type=int, default=100, help='Number of orders to process')
    parser.add_argument('--component', type=str, choices=['market_data', 'risk', 'positions', 'execution', 'all'],
                        default='all', help='Component to profile')
    
    args = parser.parse_args()
    
    if args.component == 'market_data':
        profile_market_data()
    elif args.component == 'risk':
        asyncio.run(profile_risk_manager())
    elif args.component == 'positions':
        profile_position_tracker()
    elif args.component == 'execution':
        asyncio.run(profile_order_execution(args.orders))
    else:
        run_full_system_profile(args.orders)
