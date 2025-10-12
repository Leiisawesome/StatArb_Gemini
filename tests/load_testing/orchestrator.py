"""
Load Test Orchestrator
======================

Orchestrates comprehensive load testing by connecting:
- Order Generator → Mock Trading System → Performance Monitor

Provides complete end-to-end testing with realistic simulation.
"""

import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json

from order_generator import OrderGenerator, OrderGeneratorConfig, OrderPattern
from performance_monitor import PerformanceMonitor
from mock_trading_system import MockTradingSystem

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTestOrchestrator:
    """
    Load Test Orchestrator
    
    Coordinates order generation, system execution, and performance monitoring.
    """
    
    def __init__(self, test_name: str = "load_test"):
        self.test_name = test_name
        self.trading_system = MockTradingSystem()
        self.monitor = PerformanceMonitor()
        self.results_dir = Path("load_test_results")
        self.results_dir.mkdir(exist_ok=True)
    
    async def run_test(
        self,
        duration_seconds: int,
        target_orders: int,
        pattern: OrderPattern = OrderPattern.STEADY,
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Run a load test
        
        Args:
            duration_seconds: How long to run the test
            target_orders: Total orders to generate
            pattern: Order generation pattern
            batch_size: Orders to submit in parallel batches
        
        Returns:
            Test results dictionary
        """
        logger.info(f"Starting load test: {self.test_name}")
        logger.info(f"Duration: {duration_seconds}s, Target orders: {target_orders}")
        logger.info(f"Pattern: {pattern.value}, Batch size: {batch_size}")
        
        # Configure order generator
        config = OrderGeneratorConfig(
            target_orders_per_day=target_orders * (86400 / duration_seconds),
            pattern=pattern,
            strategy_weights={
                'momentum': 0.40,
                'mean_reversion': 0.35,
                'pairs_trading': 0.25
            }
        )
        generator = OrderGenerator(config)
        
        # Start monitoring
        await self.monitor.start()
        
        # Track test progress
        orders_submitted = 0
        orders_completed = 0
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate orders
            all_orders = await generator.generate_orders(duration_seconds)
            
            logger.info(f"Generated {len(all_orders)} orders, processing...")
            
            # Process orders in batches
            for i in range(0, len(all_orders), batch_size):
                batch = all_orders[i:i + batch_size]
                
                # Record submission for monitoring
                for order in batch:
                    self.monitor.record_order_submission(order.order_id)
                    orders_submitted += 1
                
                # Submit batch to trading system
                order_dicts = [
                    {
                        'order_id': o.order_id,
                        'symbol': o.symbol,
                        'quantity': int(o.quantity),
                        'side': o.side,
                        'strategy': o.strategy,
                        'price': o.limit_price if o.limit_price else 100.0  # Use limit_price or default
                    }
                    for o in batch
                ]
                results = await self.trading_system.submit_orders_batch(order_dicts)
                
                # Record results
                for result in results:
                    success = result.status.value == 'filled'
                    self.monitor.record_order_completion(
                        result.order_id,
                        success=success,
                        error_type=result.rejection_reason.value if result.rejection_reason else None
                    )
                    orders_completed += 1
                
                # Log progress periodically
                if orders_submitted % 100 == 0:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    rate = orders_submitted / elapsed if elapsed > 0 else 0
                    logger.info(
                        f"Progress: {orders_submitted}/{target_orders} orders "
                        f"({rate:.1f} orders/sec)"
                    )
        
        except asyncio.CancelledError:
            logger.info("Test cancelled by user")
        except Exception as e:
            logger.error(f"Test error: {e}", exc_info=True)
        finally:
            # Stop monitoring and collect results
            await self.monitor.stop()
            
            # Get final statistics
            test_duration = asyncio.get_event_loop().time() - start_time
            system_stats = self.trading_system.get_stats()
            monitor_stats = self.monitor.get_summary()
            
            results = {
                'test_name': self.test_name,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': test_duration,
                'target_orders': target_orders,
                'orders_submitted': orders_submitted,
                'orders_completed': orders_completed,
                'pattern': pattern.value,
                'batch_size': batch_size,
                'system_stats': system_stats,
                'performance_stats': monitor_stats
            }
            
            # Save results
            self._save_results(results)
            
            # Print summary
            self._print_summary(results)
            
            return results
    
    def _save_results(self, results: Dict[str, Any]):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"{self.test_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {filename}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print test summary"""
        print("\n" + "=" * 80)
        print(f"LOAD TEST SUMMARY: {results['test_name']}")
        print("=" * 80)
        
        print(f"\n📊 Test Configuration:")
        print(f"  Duration: {results['duration_seconds']:.1f}s")
        print(f"  Target Orders: {results['target_orders']}")
        print(f"  Orders Submitted: {results['orders_submitted']}")
        print(f"  Orders Completed: {results['orders_completed']}")
        print(f"  Pattern: {results['pattern']}")
        print(f"  Batch Size: {results['batch_size']}")
        
        # System stats
        sys_stats = results['system_stats']
        print(f"\n🎯 Order Execution:")
        print(f"  Processed: {sys_stats['orders_processed']}")
        print(f"  Filled: {sys_stats['orders_filled']}")
        print(f"  Rejected: {sys_stats['orders_rejected']}")
        print(f"  Fill Rate: {sys_stats['fill_rate']:.2%}")
        print(f"  Rejection Rate: {sys_stats['rejection_rate']:.2%}")
        
        # Performance stats
        perf_stats = results['performance_stats']
        print(f"\n⚡ Performance Metrics:")
        print(f"  Avg Latency: {perf_stats['avg_latency_ms']:.2f}ms")
        print(f"  P95 Latency: {perf_stats['p95_latency_ms']:.2f}ms")
        print(f"  P99 Latency: {perf_stats['p99_latency_ms']:.2f}ms")
        print(f"  Max Latency: {perf_stats['max_latency_ms']:.2f}ms")
        print(f"  Throughput: {perf_stats['throughput_per_sec']:.2f} orders/sec")
        print(f"  Success Rate: {perf_stats['success_rate']:.2%}")
        
        # Resource usage
        print(f"\n💻 Resource Usage:")
        print(f"  Peak CPU: {perf_stats['peak_cpu_percent']:.1f}%")
        print(f"  Peak Memory: {perf_stats['peak_memory_mb']:.1f} MB")
        
        # Portfolio stats
        portfolio = sys_stats['portfolio']
        print(f"\n💰 Portfolio:")
        print(f"  Positions: {portfolio['num_positions']}")
        print(f"  Total Exposure: ${portfolio['total_exposure']:,.2f}")
        print(f"  Realized P&L: ${portfolio['total_realized_pnl']:,.2f}")
        
        # Pass/Fail assessment
        print(f"\n✅ Production Readiness Assessment:")
        passed = []
        failed = []
        
        # Check latency target (<100ms avg, <200ms P99)
        if perf_stats['avg_latency_ms'] < 100:
            passed.append("✅ Average latency < 100ms")
        else:
            failed.append(f"❌ Average latency: {perf_stats['avg_latency_ms']:.2f}ms (target: <100ms)")
        
        if perf_stats['p99_latency_ms'] < 200:
            passed.append("✅ P99 latency < 200ms")
        else:
            failed.append(f"❌ P99 latency: {perf_stats['p99_latency_ms']:.2f}ms (target: <200ms)")
        
        # Check success rate (>95%)
        if perf_stats['success_rate'] > 0.95:
            passed.append("✅ Success rate > 95%")
        else:
            failed.append(f"❌ Success rate: {perf_stats['success_rate']:.2%} (target: >95%)")
        
        # Check throughput
        if perf_stats['throughput_per_sec'] > 1:
            passed.append("✅ Throughput > 1 order/sec")
        else:
            failed.append(f"❌ Throughput: {perf_stats['throughput_per_sec']:.2f} orders/sec")
        
        for item in passed:
            print(f"  {item}")
        for item in failed:
            print(f"  {item}")
        
        if len(failed) == 0:
            print(f"\n🎉 PASSED: System meets all production targets!")
        else:
            print(f"\n⚠️  NEEDS WORK: {len(failed)} target(s) not met")
        
        print("=" * 80 + "\n")


# Predefined test scenarios
async def quick_test():
    """Quick validation test: 1000 orders in 1 minute"""
    orchestrator = LoadTestOrchestrator("quick_validation")
    return await orchestrator.run_test(
        duration_seconds=60,
        target_orders=1000,
        pattern=OrderPattern.STEADY,
        batch_size=10
    )


async def standard_test():
    """Standard load test: 10,000 orders over 30 minutes"""
    orchestrator = LoadTestOrchestrator("standard_load")
    return await orchestrator.run_test(
        duration_seconds=1800,  # 30 minutes
        target_orders=10000,
        pattern=OrderPattern.MARKET_HOURS,
        batch_size=20
    )


async def stress_test(duration_minutes: int = 30):
    """Stress test: Maximum load for specified duration"""
    orchestrator = LoadTestOrchestrator("stress_test")
    target_orders = duration_minutes * 1000  # 1000 orders/minute
    return await orchestrator.run_test(
        duration_seconds=duration_minutes * 60,
        target_orders=target_orders,
        pattern=OrderPattern.BURST,
        batch_size=50
    )


async def custom_test(duration: int, orders: int, pattern: str = "steady", batch_size: int = 10):
    """Custom test with specified parameters"""
    orchestrator = LoadTestOrchestrator("custom_test")
    pattern_map = {
        'steady': OrderPattern.STEADY,
        'burst': OrderPattern.BURST,
        'market': OrderPattern.MARKET_HOURS,
        'stress': OrderPattern.STRESS
    }
    return await orchestrator.run_test(
        duration_seconds=duration,
        target_orders=orders,
        pattern=pattern_map.get(pattern, OrderPattern.STEADY),
        batch_size=batch_size
    )


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Run load tests on mock trading system')
    parser.add_argument('test_type', choices=['quick', 'standard', 'stress', 'custom'],
                       help='Type of test to run')
    parser.add_argument('--duration', type=int, help='Test duration in seconds (for custom test)')
    parser.add_argument('--orders', type=int, help='Target number of orders (for custom test)')
    parser.add_argument('--pattern', choices=['steady', 'burst', 'market', 'stress'],
                       default='steady', help='Order generation pattern (for custom test)')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for order submission')
    parser.add_argument('--stress-duration', type=int, default=30,
                       help='Duration in minutes for stress test')
    
    args = parser.parse_args()
    
    # Run selected test
    if args.test_type == 'quick':
        asyncio.run(quick_test())
    elif args.test_type == 'standard':
        asyncio.run(standard_test())
    elif args.test_type == 'stress':
        asyncio.run(stress_test(args.stress_duration))
    elif args.test_type == 'custom':
        if not args.duration or not args.orders:
            parser.error("custom test requires --duration and --orders")
        asyncio.run(custom_test(args.duration, args.orders, args.pattern, args.batch_size))


if __name__ == '__main__':
    main()
