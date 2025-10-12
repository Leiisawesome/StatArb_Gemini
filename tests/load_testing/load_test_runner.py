"""
Load Test Runner
================

Main runner for executing production load tests.

Test Scenarios:
1. Quick Load Test - 1000 orders in 1 minute
2. Standard Load Test - 10,000 orders over 6.5 hours (market hours)
3. Stress Test - Maximum sustained load
4. Endurance Test - 72-hour continuous operation
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.load_testing.order_generator import (
    OrderGenerator, OrderGeneratorConfig, OrderPattern
)
from tests.load_testing.performance_monitor import (
    PerformanceMonitor, PerformanceMonitorConfig
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoadTestRunner:
    """
    Load Test Runner
    
    Orchestrates load testing with order generation and performance monitoring.
    """
    
    def __init__(self, test_name: str = "load_test"):
        self.test_name = test_name
        self.generator: Optional[OrderGenerator] = None
        self.monitor: Optional[PerformanceMonitor] = None
        self.is_running = False
        
    async def run_quick_test(self) -> Dict[str, Any]:
        """
        Quick Load Test
        
        Generate 1000 orders in 1 minute to verify system can handle basic load.
        """
        logger.info("=" * 80)
        logger.info("🚀 Starting QUICK LOAD TEST")
        logger.info("   Target: 1,000 orders in 1 minute")
        logger.info("=" * 80)
        
        # Configure
        generator_config = OrderGeneratorConfig(
            target_orders_per_day=1000 * 1440,  # Scale to match 1000 orders/minute
            pattern=OrderPattern.STEADY
        )
        
        monitor_config = PerformanceMonitorConfig(
            metrics_display_interval_sec=10.0,
            metrics_file_path=f"metrics_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        
        # Run test
        results = await self._run_test(
            generator_config=generator_config,
            monitor_config=monitor_config,
            duration_seconds=60,
            target_orders=1000
        )
        
        logger.info("✅ Quick load test complete!")
        return results
    
    async def run_standard_test(self) -> Dict[str, Any]:
        """
        Standard Load Test
        
        Generate 10,000 orders over market hours (6.5 hours)
        simulating realistic production trading patterns.
        """
        logger.info("=" * 80)
        logger.info("🚀 Starting STANDARD LOAD TEST")
        logger.info("   Target: 10,000 orders over 6.5 hours (market hours)")
        logger.info("   Pattern: Market hours with peak volume")
        logger.info("=" * 80)
        
        # Configure
        generator_config = OrderGeneratorConfig(
            target_orders_per_day=10000,
            pattern=OrderPattern.MARKET_HOURS
        )
        
        monitor_config = PerformanceMonitorConfig(
            metrics_display_interval_sec=300.0,  # Every 5 minutes
            metrics_file_path=f"metrics_standard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            latency_threshold_ms=100.0,
            error_rate_threshold=0.01
        )
        
        # Run test for 6.5 hours
        duration_hours = 6.5
        results = await self._run_test(
            generator_config=generator_config,
            monitor_config=monitor_config,
            duration_seconds=int(duration_hours * 3600),
            target_orders=10000
        )
        
        logger.info("✅ Standard load test complete!")
        return results
    
    async def run_stress_test(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """
        Stress Test
        
        Push system to maximum sustainable load for specified duration.
        """
        logger.info("=" * 80)
        logger.info(f"🚀 Starting STRESS TEST")
        logger.info(f"   Duration: {duration_minutes} minutes")
        logger.info("   Pattern: Maximum sustained load")
        logger.info("=" * 80)
        
        # Configure for stress
        generator_config = OrderGeneratorConfig(
            target_orders_per_day=100000,  # Very high rate
            pattern=OrderPattern.STRESS
        )
        
        monitor_config = PerformanceMonitorConfig(
            metrics_display_interval_sec=30.0,
            metrics_file_path=f"metrics_stress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            latency_threshold_ms=200.0,  # More lenient under stress
            error_rate_threshold=0.05  # Allow 5% errors under stress
        )
        
        # Run stress test
        results = await self._run_test(
            generator_config=generator_config,
            monitor_config=monitor_config,
            duration_seconds=duration_minutes * 60
        )
        
        logger.info("✅ Stress test complete!")
        return results
    
    async def _run_test(
        self,
        generator_config: OrderGeneratorConfig,
        monitor_config: PerformanceMonitorConfig,
        duration_seconds: int,
        target_orders: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run load test with specified configuration
        
        Args:
            generator_config: Order generator configuration
            monitor_config: Performance monitor configuration
            duration_seconds: Test duration
            target_orders: Stop after generating this many orders (optional)
        
        Returns:
            Test results dictionary
        """
        self.is_running = True
        
        # Initialize components
        self.generator = OrderGenerator(generator_config)
        self.monitor = PerformanceMonitor(monitor_config)
        
        # Start monitoring
        await self.monitor.start()
        
        try:
            # Generate and process orders
            orders_processed = 0
            start_time = datetime.now()
            
            # Start background order generation
            self.generator.start_background_generation()
            
            # Process orders
            while self.is_running:
                # Check stopping conditions
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration_seconds:
                    logger.info(f"⏱️  Duration limit reached: {elapsed:.0f}s")
                    break
                
                if target_orders and orders_processed >= target_orders:
                    logger.info(f"🎯 Target orders reached: {orders_processed:,}")
                    break
                
                # Get next order
                order = await self.generator.get_next_order(timeout=1.0)
                if not order:
                    continue
                
                # Record submission
                self.monitor.record_order_submission(order.order_id)
                
                # Simulate order processing
                # In real implementation, this would call the actual trading system
                await asyncio.sleep(0.001)  # Simulate minimal processing
                
                # Simulate success/failure (95% success rate)
                import random
                success = random.random() > 0.05
                error_type = None if success else random.choice(['timeout', 'rejected', 'connection_error'])
                
                # Record completion
                self.monitor.record_order_completion(order.order_id, success, error_type)
                
                orders_processed += 1
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Test interrupted by user")
        except Exception as e:
            logger.error(f"❌ Test error: {e}", exc_info=True)
        finally:
            # Cleanup
            await self.generator.stop()
            await self.monitor.stop()
            self.is_running = False
        
        # Get final results
        final_metrics = self.monitor.get_current_metrics()
        
        return {
            'test_name': self.test_name,
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'orders_generated': self.generator.orders_generated,
            'orders_processed': orders_processed,
            'final_metrics': final_metrics.to_dict() if final_metrics else None
        }
    
    async def stop(self):
        """Stop the test"""
        self.is_running = False
        if self.generator:
            await self.generator.stop()
        if self.monitor:
            await self.monitor.stop()


async def main():
    """Main entry point for load testing"""
    
    parser = argparse.ArgumentParser(description="Load Testing for StatArb_Gemini")
    parser.add_argument(
        'test_type',
        choices=['quick', 'standard', 'stress', 'endurance'],
        help='Type of load test to run'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Duration in minutes (for stress test)'
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = LoadTestRunner(test_name=f"{args.test_type}_test")
    
    try:
        # Run selected test
        if args.test_type == 'quick':
            results = await runner.run_quick_test()
        elif args.test_type == 'standard':
            results = await runner.run_standard_test()
        elif args.test_type == 'stress':
            results = await runner.run_stress_test(duration_minutes=args.duration)
        elif args.test_type == 'endurance':
            logger.info("⚠️  Endurance test (72-hour) should be run using continuous_test.py")
            logger.info("   Run: python tests/load_testing/continuous_test.py")
            return
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Test Type:        {results['test_name']}")
        print(f"Duration:         {results['duration_seconds']:.0f} seconds")
        print(f"Orders Generated: {results['orders_generated']:,}")
        print(f"Orders Processed: {results['orders_processed']:,}")
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test stopped by user")
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
