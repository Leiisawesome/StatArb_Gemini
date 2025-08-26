"""
Quick Integration Example - Add Optimization to Existing Backtest
================================================================

This example shows how to add optimization to your existing backtest system
with minimal changes. Simply replace your existing execution calls with the
optimized wrapper.

Author: Pro Quant Desk Trader
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Any

# Import the optimization wrapper
from optimized_backtest_wrapper import (
    OptimizedBacktestWrapper, 
    OptimizationConfig, 
    OptimizationMode,
    create_optimized_wrapper
)

async def example_integration_with_existing_backtest():
    """
    Example: How to integrate optimization with your existing backtest
    """
    
    print("🚀 OPTIMIZATION INTEGRATION EXAMPLE")
    print("="*50)
    
    # Step 1: Create optimized wrapper (replaces your existing engine)
    print("\n1. Creating optimized wrapper...")
    
    wrapper = await create_optimized_wrapper(
        mode=OptimizationMode.AB_TESTING,
        optimized_percentage=25.0  # Start with 25% optimization traffic
    )
    
    print("✅ Optimization wrapper created and initialized")
    
    # Step 2: Simulate your existing market data (replace with your actual data)
    print("\n2. Loading market data...")
    
    # This represents your existing market data format
    # Replace this with your actual data loading logic
    market_data_stream = [
        {
            'timestamp': datetime.now(),
            'prices': {'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 2500.0},
            'volumes': {'AAPL': 5000, 'MSFT': 3000, 'GOOGL': 1500}
        },
        {
            'timestamp': datetime.now(),
            'prices': {'AAPL': 151.2, 'MSFT': 301.5, 'GOOGL': 2510.0},
            'volumes': {'AAPL': 5200, 'MSFT': 3100, 'GOOGL': 1600}
        },
        {
            'timestamp': datetime.now(),
            'prices': {'AAPL': 149.8, 'MSFT': 299.2, 'GOOGL': 2495.5},
            'volumes': {'AAPL': 4800, 'MSFT': 2900, 'GOOGL': 1400}
        }
    ]
    
    print(f"✅ Loaded {len(market_data_stream)} market data points")
    
    # Step 3: Execute trading cycles with optimization (replaces your existing loop)
    print("\n3. Executing optimized trading cycles...")
    
    results = []
    
    for i, market_data in enumerate(market_data_stream):
        print(f"\n  Cycle {i+1}:")
        
        # This is the main change: replace your existing execution call with this
        # OLD: result = your_existing_backtest_function(market_data)
        # NEW: result = await wrapper.execute_trading_cycle(market_data)
        
        result = await wrapper.execute_trading_cycle(
            market_data=market_data,
            strategy_params={'symbols': ['AAPL', 'MSFT', 'GOOGL']}
        )
        
        # Process results (same as your existing code)
        print(f"    Optimization: {'✅ APPLIED' if result['optimization_applied'] else '❌ LEGACY'}")
        print(f"    Execution Time: {result['execution_time_ms']:.2f}ms")
        print(f"    Signals Generated: {len(result.get('signals', []))}")
        print(f"    Orders Placed: {len(result.get('orders', []))}")
        
        results.append(result)
    
    # Step 4: Get performance report
    print("\n4. Performance Analysis:")
    print("-" * 30)
    print(wrapper.get_performance_report())
    
    # Step 5: Export metrics for analysis
    print("\n5. Exporting metrics...")
    metrics_file = wrapper.export_metrics()
    print(f"✅ Metrics exported for analysis")
    
    return results

async def example_ab_testing_progression():
    """
    Example: How to progressively increase optimization percentage
    """
    
    print("\n" + "="*60)
    print("A/B TESTING PROGRESSION EXAMPLE")
    print("="*60)
    
    # Create wrapper for A/B testing
    wrapper = await create_optimized_wrapper(
        mode=OptimizationMode.AB_TESTING,
        optimized_percentage=10.0  # Start with 10%
    )
    
    # Simulate progressive rollout
    rollout_schedule = [
        {'percentage': 10, 'cycles': 5, 'description': 'Initial validation'},
        {'percentage': 25, 'cycles': 5, 'description': 'Increased testing'},
        {'percentage': 50, 'cycles': 5, 'description': 'Half traffic'},
        {'percentage': 75, 'cycles': 5, 'description': 'Majority traffic'},
        {'percentage': 100, 'cycles': 5, 'description': 'Full optimization'}
    ]
    
    for phase in rollout_schedule:
        print(f"\nPhase: {phase['description']} ({phase['percentage']}% optimization)")
        
        # Update optimization percentage
        wrapper.update_optimization_percentage(phase['percentage'])
        
        # Run test cycles
        for cycle in range(phase['cycles']):
            market_data = {
                'prices': {'AAPL': 150 + cycle, 'MSFT': 300 + cycle},
                'volumes': {'AAPL': 5000, 'MSFT': 3000}
            }
            
            result = await wrapper.execute_trading_cycle(market_data)
            
            optimization_used = "OPT" if result['optimization_applied'] else "LEG"
            print(f"  Cycle {cycle+1}: {optimization_used} ({result['execution_time_ms']:.2f}ms)")
        
        # Show phase results
        print(f"  Phase complete - {phase['percentage']}% optimization active")
    
    # Final performance report
    print("\nFINAL A/B TESTING RESULTS:")
    print(wrapper.get_performance_report())

async def example_production_integration():
    """
    Example: Production-ready integration with monitoring
    """
    
    print("\n" + "="*60)
    print("PRODUCTION INTEGRATION EXAMPLE")
    print("="*60)
    
    # Production configuration
    config = OptimizationConfig(
        mode=OptimizationMode.HYBRID,  # Smart routing
        optimized_percentage=70.0,     # 70% optimization
        enable_monitoring=True,        # Full monitoring
        enable_caching=True,           # Performance caching
        enable_batching=True,          # Batch processing
        max_execution_time_ms=5.0      # 5ms alert threshold
    )
    
    wrapper = OptimizedBacktestWrapper(config)
    await wrapper.initialize()
    
    print("✅ Production wrapper initialized with full monitoring")
    
    # Simulate production trading day
    print("\nSimulating production trading day...")
    
    trading_hours = 20  # Simulate 20 data points (trading day)
    
    for hour in range(trading_hours):
        # Simulate varying market conditions
        market_data = {
            'timestamp': datetime.now(),
            'prices': {
                'AAPL': 150 + (hour * 0.5),
                'MSFT': 300 + (hour * 0.3), 
                'GOOGL': 2500 + (hour * 2.0),
                'TSLA': 800 + (hour * 1.5),
                'NVDA': 400 + (hour * 0.8)
            },
            'volumes': {symbol: 5000 + (hour * 100) for symbol in ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']}
        }
        
        result = await wrapper.execute_trading_cycle(
            market_data=market_data,
            strategy_params={'symbols': list(market_data['prices'].keys())}
        )
        
        # Log key metrics every 5 hours
        if hour % 5 == 0:
            opt_status = "🚀 OPT" if result['optimization_applied'] else "🔧 LEG"
            print(f"Hour {hour+1:2d}: {opt_status} | {result['execution_time_ms']:.2f}ms | "
                  f"{len(result.get('signals', []))} signals | {len(result.get('orders', []))} orders")
    
    # Production day summary
    print("\nPRODUCTION DAY SUMMARY:")
    print(wrapper.get_performance_report())
    
    # Export daily metrics
    daily_metrics = wrapper.export_metrics("production_daily_metrics.json")
    print(f"✅ Daily metrics exported for compliance and analysis")

async def main():
    """Run all integration examples"""
    
    print("OPTIMIZED BACKTEST INTEGRATION EXAMPLES")
    print("="*60)
    print("These examples show how to add optimization to your existing system")
    print("with minimal code changes and maximum performance benefits.")
    
    try:
        # Example 1: Basic integration
        await example_integration_with_existing_backtest()
        
        # Example 2: A/B testing progression
        await example_ab_testing_progression()
        
        # Example 3: Production integration
        await example_production_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL INTEGRATION EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\nKey Integration Benefits Demonstrated:")
        print("✅ Drop-in replacement for existing backtest execution")
        print("✅ A/B testing with progressive optimization rollout")
        print("✅ Production-ready monitoring and performance tracking")
        print("✅ Automatic fallback and error handling")
        print("✅ Comprehensive performance analytics")
        
        print("\nNext Steps for Your System:")
        print("1. Replace your existing trading cycle execution with OptimizedBacktestWrapper")
        print("2. Start with A/B testing mode at 10% optimization")
        print("3. Monitor performance improvements and gradually increase percentage")
        print("4. Deploy full optimization once validated for maximum 2.24x performance gain")
        
        print("\nIntegration Code:")
        print("```python")
        print("# Replace this:")
        print("# result = your_existing_backtest_function(market_data)")
        print("#")
        print("# With this:")
        print("wrapper = await create_optimized_wrapper()")
        print("result = await wrapper.execute_trading_cycle(market_data)")
        print("print(wrapper.get_performance_report())")
        print("```")
        
    except Exception as e:
        print(f"\n❌ Integration example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the integration examples
    asyncio.run(main())
