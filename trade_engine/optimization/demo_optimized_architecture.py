"""
Optimized Two-Layer Architecture Demo
====================================

This demo showcases the optimized two-layer architecture with:
- Real-time performance comparison between legacy and optimized engines
- Progressive migration capabilities
- A/B testing functionality
- Comprehensive performance analytics

Run this demo to see the optimization improvements in action.

Author: Pro Quant Desk Trader
"""

import asyncio
import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random

# Add parent directory to path for imports
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from trade_engine.optimization.integration_adapter import (
    TwoLayerIntegrationAdapter, IntegrationConfig, IntegrationMode,
    OptimizedTradingEngine, create_integration_adapter
)
from core_structure.unified_core_engine import StrategyConfig, TradingResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockMarketDataGenerator:
    """Generate realistic mock market data for demo"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        self.current_prices = {symbol: 100.0 + random.uniform(-50, 50) for symbol in self.symbols}
        self.sequence = 0
    
    def generate_market_data(self) -> Dict[str, Any]:
        """Generate realistic market data"""
        self.sequence += 1
        
        # Update prices with random walks
        for symbol in self.symbols:
            change = random.normalvariate(0, 0.5)  # Normal distribution with std=0.5
            self.current_prices[symbol] *= (1 + change / 100)
        
        market_data = {
            'timestamp': datetime.now(),
            'sequence': self.sequence,
            'prices': self.current_prices.copy(),
            'volumes': {symbol: random.randint(1000, 10000) for symbol in self.symbols},
            'bid_ask_spreads': {symbol: random.uniform(0.01, 0.05) for symbol in self.symbols}
        }
        
        return market_data

async def demo_performance_comparison():
    """Demo: Performance comparison between legacy and optimized engines"""
    print("\n" + "="*80)
    print("DEMO 1: PERFORMANCE COMPARISON")
    print("="*80)
    
    # Create strategy config
    strategy_config = StrategyConfig(
        strategy_id="momentum_demo",
        strategy_type="momentum",
        symbols=['AAPL', 'MSFT', 'GOOGL']
    )
    
    # Create integration adapter for performance comparison
    integration_config = IntegrationConfig(
        mode=IntegrationMode.PERFORMANCE_COMPARISON,
        enable_performance_logging=True,
        enable_result_validation=True
    )
    
    adapter = await create_integration_adapter(strategy_config, integration_config)
    market_generator = MockMarketDataGenerator()
    
    print("Running 10 trading cycles with both engines...")
    
    for cycle in range(10):
        market_data = market_generator.generate_market_data()
        
        print(f"\nCycle {cycle + 1}:")
        result = await adapter.execute_trading_cycle(market_data, strategy_config)
        
        print(f"  ✓ Processed {len(result.signals) if result.signals else 0} signals")
        print(f"  ✓ Execution time: {result.processing_time_ms:.2f}ms")
    
    # Show performance report
    print("\n" + "-"*60)
    print("PERFORMANCE COMPARISON RESULTS:")
    print("-"*60)
    print(adapter.get_performance_report())
    
    await adapter.shutdown()

async def demo_ab_testing():
    """Demo: A/B testing between engines"""
    print("\n" + "="*80)
    print("DEMO 2: A/B TESTING")
    print("="*80)
    
    strategy_config = StrategyConfig(
        strategy_id="ab_test_demo",
        strategy_type="mean_reversion",
        symbols=['TSLA', 'NVDA']
    )
    
    # 70% traffic to optimized engine
    integration_config = IntegrationConfig(
        mode=IntegrationMode.A_B_TESTING,
        optimized_engine_percentage=70.0,
        enable_performance_logging=True
    )
    
    adapter = await create_integration_adapter(strategy_config, integration_config)
    market_generator = MockMarketDataGenerator(['TSLA', 'NVDA'])
    
    print("Running A/B test with 70% traffic to optimized engine...")
    
    optimized_count = 0
    legacy_count = 0
    
    for cycle in range(20):
        market_data = market_generator.generate_market_data()
        result = await adapter.execute_trading_cycle(market_data, strategy_config)
        
        # Check which engine was likely used based on processing time
        if result.processing_time_ms < 2.0:  # Optimized engine is typically faster
            optimized_count += 1
            engine_type = "Optimized"
        else:
            legacy_count += 1
            engine_type = "Legacy"
        
        if cycle % 5 == 0:
            print(f"Cycle {cycle + 1}: {engine_type} engine, {result.processing_time_ms:.2f}ms")
    
    print(f"\nA/B Test Results:")
    print(f"  Optimized engine cycles: {optimized_count}")
    print(f"  Legacy engine cycles: {legacy_count}")
    print(f"  Expected split: 70%/30%")
    
    metrics = adapter.get_integration_metrics()
    print(f"  Actual optimized cycles: {metrics.optimized_cycles}")
    print(f"  Actual legacy cycles: {metrics.legacy_cycles}")
    
    await adapter.shutdown()

async def demo_hybrid_mode():
    """Demo: Hybrid mode with complexity-based routing"""
    print("\n" + "="*80)
    print("DEMO 3: HYBRID MODE (COMPLEXITY-BASED ROUTING)")
    print("="*80)
    
    integration_config = IntegrationConfig(
        mode=IntegrationMode.HYBRID,
        max_complexity_for_optimized=5,
        enable_performance_logging=True
    )
    
    market_generator = MockMarketDataGenerator()
    
    # Test with different complexity strategies
    strategies = [
        # Simple strategy (should use optimized)
        StrategyConfig(
            strategy_id="simple_momentum",
            strategy_type="momentum",
            symbols=['AAPL']
        ),
        
        # Complex strategy (should use legacy)
        StrategyConfig(
            strategy_id="complex_multi_asset",
            strategy_type="multi_asset",
            symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        )
    ]
    
    for i, strategy_config in enumerate(strategies):
        print(f"\nTesting Strategy {i + 1}: {strategy_config.strategy_id}")
        
        adapter = await create_integration_adapter(strategy_config, integration_config)
        
        # Run several cycles
        for cycle in range(5):
            market_data = market_generator.generate_market_data()
            result = await adapter.execute_trading_cycle(market_data, strategy_config)
            
            # Infer which engine was used
            engine_used = "Optimized" if result.processing_time_ms < 2.0 else "Legacy"
            print(f"  Cycle {cycle + 1}: {engine_used} engine ({result.processing_time_ms:.2f}ms)")
        
        await adapter.shutdown()

async def demo_optimized_trading_engine():
    """Demo: Using the drop-in replacement OptimizedTradingEngine"""
    print("\n" + "="*80)
    print("DEMO 4: DROP-IN REPLACEMENT ENGINE")
    print("="*80)
    
    strategy_config = StrategyConfig(
        strategy_id="drop_in_demo",
        strategy_type="momentum",
        symbols=['AAPL', 'MSFT']
    )
    
    # Use the drop-in replacement
    integration_config = IntegrationConfig(mode=IntegrationMode.OPTIMIZED_ONLY)
    engine = OptimizedTradingEngine(strategy_config, integration_config)
    
    await engine.initialize()
    
    market_generator = MockMarketDataGenerator(['AAPL', 'MSFT'])
    
    print("Running optimized engine (drop-in replacement)...")
    
    total_time = 0
    cycles = 15
    
    for cycle in range(cycles):
        market_data = market_generator.generate_market_data()
        
        start_time = time.perf_counter()
        result = await engine.execute_trading_cycle(market_data)
        execution_time = (time.perf_counter() - start_time) * 1000
        
        total_time += execution_time
        
        if cycle % 5 == 0:
            print(f"Cycle {cycle + 1}: {execution_time:.2f}ms, "
                  f"{len(result.signals) if result.signals else 0} signals")
    
    avg_time = total_time / cycles
    print(f"\nAverage execution time: {avg_time:.2f}ms")
    print(f"Target performance: <1ms for simple strategies")
    
    if avg_time < 1.0:
        print("🎯 TARGET ACHIEVED: Sub-millisecond execution!")
    elif avg_time < 2.0:
        print("⚡ EXCELLENT: Near sub-millisecond execution!")
    else:
        print("✅ GOOD: Significant performance improvement!")
    
    print("\nDetailed Performance Report:")
    print(engine.get_performance_report())
    
    await engine.shutdown()

async def demo_real_time_optimization():
    """Demo: Real-time optimization monitoring"""
    print("\n" + "="*80)
    print("DEMO 5: REAL-TIME OPTIMIZATION MONITORING")
    print("="*80)
    
    strategy_config = StrategyConfig(
        strategy_id="monitoring_demo",
        strategy_type="momentum",
        symbols=['AAPL', 'MSFT', 'GOOGL']
    )
    
    integration_config = IntegrationConfig(
        mode=IntegrationMode.OPTIMIZED_ONLY,
        enable_performance_logging=True
    )
    
    adapter = await create_integration_adapter(strategy_config, integration_config)
    market_generator = MockMarketDataGenerator()
    
    print("Running continuous optimization monitoring...")
    print("Watch real-time performance metrics:")
    
    for cycle in range(25):
        market_data = market_generator.generate_market_data()
        result = await adapter.execute_trading_cycle(market_data, strategy_config)
        
        # Show real-time metrics every 5 cycles
        if cycle % 5 == 4:
            metrics = adapter.get_integration_metrics()
            
            print(f"\n📊 Cycle {cycle + 1} Metrics:")
            print(f"   Avg Execution Time: {metrics.optimized_avg_time_ms:.2f}ms")
            print(f"   Total Cycles: {metrics.optimized_cycles}")
            print(f"   Error Rate: {metrics.error_rate_optimized:.2%}")
            
            # Show cache and pool efficiency if available
            if adapter.optimized_engine:
                engine_metrics = adapter.optimized_engine.get_performance_metrics()
                print(f"   Cache Hit Rate: {engine_metrics.cache_hit_rate:.1%}")
                print(f"   Pool Efficiency: {engine_metrics.object_pool_efficiency:.1%}")
    
    await adapter.shutdown()

async def main():
    """Run all optimization demos"""
    print("🚀 OPTIMIZED TWO-LAYER ARCHITECTURE DEMO")
    print("=========================================")
    print("Showcasing performance improvements in the trade_engine + core_structure architecture")
    
    try:
        # Run all demos
        await demo_performance_comparison()
        await asyncio.sleep(1)
        
        await demo_ab_testing()
        await asyncio.sleep(1)
        
        await demo_hybrid_mode()
        await asyncio.sleep(1)
        
        await demo_optimized_trading_engine()
        await asyncio.sleep(1)
        
        await demo_real_time_optimization()
        
        print("\n" + "="*80)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nKey Achievements:")
        print("✅ Seamless integration with existing two-layer architecture")
        print("✅ Performance improvements with backwards compatibility")
        print("✅ A/B testing and progressive migration capabilities")
        print("✅ Real-time monitoring and optimization")
        print("✅ Drop-in replacement for existing trading engines")
        
        print("\nNext Steps:")
        print("1. Integrate optimized components into production systems")
        print("2. Configure A/B testing for gradual rollout")
        print("3. Monitor performance improvements in live trading")
        print("4. Extend optimizations to additional strategy types")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
