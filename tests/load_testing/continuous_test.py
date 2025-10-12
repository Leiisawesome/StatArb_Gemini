"""
72-Hour Continuous Operation Test
==================================

Long-running test to validate system reliability and stability:
- Memory leak detection
- Performance degradation monitoring
- Automatic health checks
- State persistence and recovery
- Graceful shutdown handling

Target:
- 72+ hours continuous operation
- Zero memory leaks
- Stable performance (no degradation)
- 100% state recovery after restart
"""

import asyncio
import logging
import signal
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import psutil

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"continuous_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Health check result"""
    timestamp: datetime = field(default_factory=datetime.now)
    memory_mb: float = 0.0
    memory_growth_mb: float = 0.0
    cpu_percent: float = 0.0
    orders_per_second: float = 0.0
    error_rate: float = 0.0
    latency_p99_ms: float = 0.0
    is_healthy: bool = True
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'memory_mb': round(self.memory_mb, 1),
            'memory_growth_mb': round(self.memory_growth_mb, 1),
            'cpu_percent': round(self.cpu_percent, 1),
            'orders_per_second': round(self.orders_per_second, 2),
            'error_rate': round(self.error_rate, 4),
            'latency_p99_ms': round(self.latency_p99_ms, 2),
            'is_healthy': self.is_healthy,
            'issues': self.issues
        }


@dataclass
class ContinuousTestConfig:
    """Configuration for continuous test"""
    
    # Test duration
    target_duration_hours: float = 72.0
    
    # Order generation
    orders_per_day: int = 10000
    order_pattern: OrderPattern = OrderPattern.MARKET_HOURS
    
    # Health checks
    health_check_interval_minutes: int = 15
    memory_leak_threshold_mb_per_hour: float = 10.0
    performance_degradation_threshold_percent: float = 20.0
    
    # Auto-recovery
    enable_auto_recovery: bool = True
    max_consecutive_failures: int = 5
    recovery_cooldown_minutes: int = 5
    
    # State persistence
    state_file: str = "continuous_test_state.json"
    checkpoint_interval_hours: float = 1.0
    
    # Alerts
    enable_alerts: bool = True
    alert_memory_threshold_mb: float = 2048.0
    alert_error_rate_threshold: float = 0.05
    alert_latency_threshold_ms: float = 200.0


class ContinuousTest:
    """
    72-Hour Continuous Operation Test
    
    Monitors system health, detects memory leaks, and validates
    long-term stability under realistic production load.
    """
    
    def __init__(self, config: Optional[ContinuousTestConfig] = None):
        self.config = config or ContinuousTestConfig()
        
        # Components
        self.generator: Optional[OrderGenerator] = None
        self.monitor: Optional[PerformanceMonitor] = None
        
        # Health tracking
        self.health_checks: List[HealthCheckResult] = []
        self.initial_memory_mb: Optional[float] = None
        self.baseline_throughput: Optional[float] = None
        self.consecutive_failures = 0
        
        # State
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.total_runtime_hours: float = 0.0
        self.orders_processed = 0
        
        # Tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._main_task: Optional[asyncio.Task] = None
        
        # Process monitoring
        self.process = psutil.Process()
        
        # Signal handling
        self._setup_signal_handlers()
        
        logger.info("🏥 Continuous Test initialized")
        logger.info(f"   Target Duration: {self.config.target_duration_hours} hours")
        logger.info(f"   Orders per Day: {self.config.orders_per_day:,}")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on signals"""
        def signal_handler(signum, frame):
            logger.info(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self, resume: bool = False):
        """
        Start continuous test
        
        Args:
            resume: Resume from saved state if available
        """
        logger.info("=" * 80)
        logger.info("🚀 Starting 72-HOUR CONTINUOUS OPERATION TEST")
        logger.info("=" * 80)
        
        # Try to resume from checkpoint
        if resume:
            await self._load_state()
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # Record initial memory
        memory_info = self.process.memory_info()
        self.initial_memory_mb = memory_info.rss / 1024 / 1024
        logger.info(f"📊 Initial memory: {self.initial_memory_mb:.1f}MB")
        
        # Initialize components
        generator_config = OrderGeneratorConfig(
            target_orders_per_day=self.config.orders_per_day,
            pattern=self.config.order_pattern
        )
        
        monitor_config = PerformanceMonitorConfig(
            metrics_display_interval_sec=3600.0,  # Every hour
            metrics_file_path=f"continuous_test_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
            latency_threshold_ms=self.config.alert_latency_threshold_ms,
            error_rate_threshold=self.config.alert_error_rate_threshold,
            memory_threshold_mb=self.config.alert_memory_threshold_mb
        )
        
        self.generator = OrderGenerator(generator_config)
        self.monitor = PerformanceMonitor(monitor_config)
        
        # Start monitoring
        await self.monitor.start()
        
        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        self._main_task = asyncio.create_task(self._main_loop())
        
        # Wait for main loop
        try:
            await self._main_task
        except asyncio.CancelledError:
            logger.info("⏹️  Main loop cancelled")
        
        await self.stop()
    
    async def _main_loop(self):
        """Main order processing loop"""
        try:
            # Start order generation
            self.generator.start_background_generation()
            
            while self.is_running:
                # Check if target duration reached
                if self.start_time:
                    elapsed_hours = (datetime.now() - self.start_time).total_seconds() / 3600
                    if elapsed_hours >= self.config.target_duration_hours:
                        logger.info(f"✅ Target duration reached: {elapsed_hours:.2f} hours")
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
                
                # Simulate success/failure (98% success rate for continuous test)
                import random
                success = random.random() > 0.02
                error_type = None if success else random.choice(['timeout', 'rejected', 'connection_error'])
                
                # Record completion
                self.monitor.record_order_completion(order.order_id, success, error_type)
                
                self.orders_processed += 1
                
        except Exception as e:
            logger.error(f"❌ Main loop error: {e}", exc_info=True)
            if self.config.enable_auto_recovery:
                await self._attempt_recovery()
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        try:
            while self.is_running:
                await asyncio.sleep(self.config.health_check_interval_minutes * 60)
                
                result = await self._perform_health_check()
                self.health_checks.append(result)
                
                # Log health status
                if result.is_healthy:
                    logger.info(f"✅ Health Check PASSED - Memory: {result.memory_mb:.1f}MB, Growth: {result.memory_growth_mb:.1f}MB")
                else:
                    logger.warning(f"⚠️  Health Check FAILED - Issues: {', '.join(result.issues)}")
                    self.consecutive_failures += 1
                    
                    # Auto-recovery if enabled
                    if self.config.enable_auto_recovery and self.consecutive_failures >= self.config.max_consecutive_failures:
                        logger.error(f"❌ Too many consecutive failures ({self.consecutive_failures}), attempting recovery...")
                        await self._attempt_recovery()
                
                # Reset consecutive failures on success
                if result.is_healthy:
                    self.consecutive_failures = 0
                
        except asyncio.CancelledError:
            pass
    
    async def _perform_health_check(self) -> HealthCheckResult:
        """Perform health check"""
        result = HealthCheckResult()
        
        # Get current metrics
        current_metrics = self.monitor.get_current_metrics()
        if not current_metrics:
            result.is_healthy = False
            result.issues.append("No metrics available")
            return result
        
        # Check memory
        memory_info = self.process.memory_info()
        result.memory_mb = memory_info.rss / 1024 / 1024
        
        if self.initial_memory_mb:
            result.memory_growth_mb = result.memory_mb - self.initial_memory_mb
            
            # Calculate memory growth rate
            if self.start_time:
                hours_elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
                if hours_elapsed > 0:
                    memory_growth_per_hour = result.memory_growth_mb / hours_elapsed
                    
                    if memory_growth_per_hour > self.config.memory_leak_threshold_mb_per_hour:
                        result.is_healthy = False
                        result.issues.append(f"Memory leak detected: {memory_growth_per_hour:.1f}MB/hour (threshold: {self.config.memory_leak_threshold_mb_per_hour}MB/hour)")
        
        # Check CPU
        result.cpu_percent = self.process.cpu_percent()
        
        # Check throughput
        result.orders_per_second = current_metrics.orders_per_second
        
        # Set baseline if not set
        if self.baseline_throughput is None and result.orders_per_second > 0:
            self.baseline_throughput = result.orders_per_second
        
        # Check for performance degradation
        if self.baseline_throughput and result.orders_per_second > 0:
            degradation_percent = ((self.baseline_throughput - result.orders_per_second) / self.baseline_throughput) * 100
            
            if degradation_percent > self.config.performance_degradation_threshold_percent:
                result.is_healthy = False
                result.issues.append(f"Performance degradation: {degradation_percent:.1f}% (threshold: {self.config.performance_degradation_threshold_percent}%)")
        
        # Check error rate
        result.error_rate = current_metrics.error_rate
        if result.error_rate > self.config.alert_error_rate_threshold:
            result.is_healthy = False
            result.issues.append(f"High error rate: {result.error_rate*100:.2f}% (threshold: {self.config.alert_error_rate_threshold*100:.1f}%)")
        
        # Check latency
        result.latency_p99_ms = current_metrics.p99_latency_ms
        if result.latency_p99_ms > self.config.alert_latency_threshold_ms:
            result.is_healthy = False
            result.issues.append(f"High P99 latency: {result.latency_p99_ms:.1f}ms (threshold: {self.config.alert_latency_threshold_ms}ms)")
        
        return result
    
    async def _checkpoint_loop(self):
        """Periodic checkpoint loop for state persistence"""
        try:
            while self.is_running:
                await asyncio.sleep(self.config.checkpoint_interval_hours * 3600)
                await self._save_state()
        except asyncio.CancelledError:
            pass
    
    async def _save_state(self):
        """Save current state to file"""
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'total_runtime_hours': self.total_runtime_hours,
                'orders_processed': self.orders_processed,
                'initial_memory_mb': self.initial_memory_mb,
                'baseline_throughput': self.baseline_throughput,
                'consecutive_failures': self.consecutive_failures,
                'health_checks_count': len(self.health_checks),
                'last_health_check': self.health_checks[-1].to_dict() if self.health_checks else None
            }
            
            with open(self.config.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"💾 Checkpoint saved - Orders: {self.orders_processed:,}, Runtime: {self.total_runtime_hours:.1f}h")
        
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint: {e}")
    
    async def _load_state(self):
        """Load state from file"""
        try:
            state_file = Path(self.config.state_file)
            if not state_file.exists():
                logger.info("No previous state found, starting fresh")
                return
            
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            self.total_runtime_hours = state.get('total_runtime_hours', 0.0)
            self.orders_processed = state.get('orders_processed', 0)
            self.initial_memory_mb = state.get('initial_memory_mb')
            self.baseline_throughput = state.get('baseline_throughput')
            self.consecutive_failures = state.get('consecutive_failures', 0)
            
            logger.info(f"📂 Resumed from checkpoint - Orders: {self.orders_processed:,}, Runtime: {self.total_runtime_hours:.1f}h")
        
        except Exception as e:
            logger.error(f"❌ Failed to load checkpoint: {e}")
    
    async def _attempt_recovery(self):
        """Attempt to recover from failures"""
        logger.info("🔄 Attempting automatic recovery...")
        
        try:
            # Stop current operations
            if self.generator:
                await self.generator.stop()
            
            # Wait for cooldown
            await asyncio.sleep(self.config.recovery_cooldown_minutes * 60)
            
            # Restart generator
            if self.generator:
                self.generator.start_background_generation()
            
            # Reset failure counter
            self.consecutive_failures = 0
            
            logger.info("✅ Recovery complete")
        
        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}")
    
    async def stop(self):
        """Stop continuous test and cleanup"""
        logger.info("⏹️  Stopping continuous test...")
        
        self.is_running = False
        
        # Cancel tasks
        for task in [self._health_check_task, self._checkpoint_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop components
        if self.generator:
            await self.generator.stop()
        if self.monitor:
            await self.monitor.stop()
        
        # Calculate total runtime
        if self.start_time:
            self.total_runtime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
        
        # Save final state
        await self._save_state()
        
        # Print final report
        self._print_final_report()
        
        logger.info("✅ Continuous test stopped")
    
    def _print_final_report(self):
        """Print final test report"""
        print("\n" + "=" * 80)
        print("📊 CONTINUOUS OPERATION TEST - FINAL REPORT")
        print("=" * 80)
        
        print(f"\n⏱️  Test Duration:")
        print(f"   Target:            {self.config.target_duration_hours} hours")
        print(f"   Actual:            {self.total_runtime_hours:.2f} hours")
        print(f"   Completion:        {(self.total_runtime_hours/self.config.target_duration_hours*100):.1f}%")
        
        print(f"\n📦 Order Statistics:")
        print(f"   Orders Processed:  {self.orders_processed:,}")
        print(f"   Avg Rate:          {self.orders_processed/self.total_runtime_hours/3600:.2f} orders/sec")
        
        print(f"\n🏥 Health Checks:")
        print(f"   Total Checks:      {len(self.health_checks)}")
        healthy_checks = sum(1 for hc in self.health_checks if hc.is_healthy)
        print(f"   Passed:            {healthy_checks} ({healthy_checks/len(self.health_checks)*100:.1f}%)")
        print(f"   Failed:            {len(self.health_checks) - healthy_checks}")
        
        if self.health_checks:
            final_check = self.health_checks[-1]
            print(f"\n💾 Memory Analysis:")
            print(f"   Initial:           {self.initial_memory_mb:.1f}MB")
            print(f"   Final:             {final_check.memory_mb:.1f}MB")
            print(f"   Growth:            {final_check.memory_growth_mb:.1f}MB")
            if self.total_runtime_hours > 0:
                print(f"   Growth Rate:       {final_check.memory_growth_mb/self.total_runtime_hours:.2f}MB/hour")
        
        print(f"\n✅ Test Completion:")
        completed = self.total_runtime_hours >= self.config.target_duration_hours
        print(f"   Status:            {'✅ COMPLETED' if completed else '⏹️  STOPPED EARLY'}")
        print(f"   Memory Leaks:      {'❌ DETECTED' if self.health_checks and any(not hc.is_healthy for hc in self.health_checks) else '✅ NONE DETECTED'}")
        
        print("=" * 80 + "\n")


async def main():
    """Main entry point"""
    
    import argparse
    parser = argparse.ArgumentParser(description="72-Hour Continuous Operation Test")
    parser.add_argument('--duration', type=float, default=72.0, help='Test duration in hours')
    parser.add_argument('--orders-per-day', type=int, default=10000, help='Target orders per day')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ContinuousTestConfig(
        target_duration_hours=args.duration,
        orders_per_day=args.orders_per_day
    )
    
    # Create and run test
    test = ContinuousTest(config)
    
    try:
        await test.start(resume=args.resume)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        await test.stop()


if __name__ == "__main__":
    asyncio.run(main())
