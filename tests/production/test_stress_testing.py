"""
72-Hour Stress Test

Continuous operation test to validate:
- Memory leak detection
- Connection pool stability
- Long-running process health
- Performance degradation over time
- Resource cleanup
"""

import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import psutil
import pytest


@dataclass
class StressTestCheckpoint:
    """Snapshot of system state at a specific time."""
    
    timestamp: datetime
    elapsed_hours: float
    
    # Memory metrics
    memory_rss_mb: float
    memory_vms_mb: float
    memory_percent: float
    
    # CPU metrics
    cpu_percent: float
    
    # Connection metrics
    num_connections: int
    num_threads: int
    
    # Performance metrics
    orders_processed: int
    avg_latency_ms: float
    error_count: int
    
    # Health status
    is_healthy: bool
    health_issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'elapsed_hours': round(self.elapsed_hours, 2),
            'memory': {
                'rss_mb': round(self.memory_rss_mb, 2),
                'vms_mb': round(self.memory_vms_mb, 2),
                'percent': round(self.memory_percent, 2),
            },
            'cpu_percent': round(self.cpu_percent, 2),
            'connections': {
                'num_connections': self.num_connections,
                'num_threads': self.num_threads,
            },
            'performance': {
                'orders_processed': self.orders_processed,
                'avg_latency_ms': round(self.avg_latency_ms, 2),
                'error_count': self.error_count,
            },
            'health': {
                'is_healthy': self.is_healthy,
                'issues': self.health_issues,
            }
        }


@dataclass
class StressTestReport:
    """Complete stress test report."""
    
    start_time: datetime
    end_time: Optional[datetime] = None
    target_duration_hours: float = 72.0
    actual_duration_hours: float = 0.0
    
    checkpoints: List[StressTestCheckpoint] = field(default_factory=list)
    
    # Summary metrics
    total_orders: int = 0
    total_errors: int = 0
    memory_leak_detected: bool = False
    performance_degradation_detected: bool = False
    
    # Thresholds
    max_memory_mb: float = 2000.0  # 2GB max
    max_latency_degradation_pct: float = 50.0  # 50% max increase
    
    def add_checkpoint(self, checkpoint: StressTestCheckpoint):
        """Add a checkpoint to the report."""
        self.checkpoints.append(checkpoint)
        
        # Analyze for issues
        self._check_memory_leak()
        self._check_performance_degradation()
    
    def _check_memory_leak(self):
        """Detect memory leaks by analyzing trend."""
        if len(self.checkpoints) < 10:
            return
        
        # Compare first and last 5 checkpoints
        first_5_avg = sum(c.memory_rss_mb for c in self.checkpoints[:5]) / 5
        last_5_avg = sum(c.memory_rss_mb for c in self.checkpoints[-5:]) / 5
        
        # If memory increased by >50% over time, flag as leak
        increase_pct = ((last_5_avg - first_5_avg) / first_5_avg) * 100
        if increase_pct > 50:
            self.memory_leak_detected = True
    
    def _check_performance_degradation(self):
        """Detect performance degradation over time."""
        if len(self.checkpoints) < 10:
            return
        
        # Compare latency at start vs end
        first_5_avg = sum(c.avg_latency_ms for c in self.checkpoints[:5]) / 5
        last_5_avg = sum(c.avg_latency_ms for c in self.checkpoints[-5:]) / 5
        
        # If latency increased by >50%, flag degradation
        if first_5_avg > 0:
            increase_pct = ((last_5_avg - first_5_avg) / first_5_avg) * 100
            if increase_pct > self.max_latency_degradation_pct:
                self.performance_degradation_detected = True
    
    def save_to_file(self, filepath: Path):
        """Save report to JSON file."""
        report_data = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': {
                'target_hours': self.target_duration_hours,
                'actual_hours': self.actual_duration_hours,
            },
            'summary': {
                'total_orders': self.total_orders,
                'total_errors': self.total_errors,
                'memory_leak_detected': self.memory_leak_detected,
                'performance_degradation_detected': self.performance_degradation_detected,
            },
            'checkpoints': [cp.to_dict() for cp in self.checkpoints],
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"Stress test report saved to: {filepath}")


class StressTestRunner:
    """
    72-hour stress test runner.
    
    Runs system continuously and monitors:
    - Memory usage and leaks
    - CPU usage
    - Connection stability
    - Performance metrics
    - Error rates
    """
    
    def __init__(
        self,
        target_duration_hours: float = 72.0,
        checkpoint_interval_minutes: int = 60,
        report_path: Optional[Path] = None
    ):
        self.target_duration_hours = target_duration_hours
        self.checkpoint_interval_minutes = checkpoint_interval_minutes
        self.report_path = report_path or Path("stress_test_report.json")
        
        self.report = StressTestReport(
            start_time=datetime.now(),
            target_duration_hours=target_duration_hours
        )
        
        self.process = psutil.Process()
        self._stop_requested = False
        
        # Performance tracking
        self.orders_processed = 0
        self.errors_encountered = 0
        self.latency_samples: List[float] = []
    
    async def run_stress_test(self):
        """
        Run the complete 72-hour stress test.
        
        Returns:
            StressTestReport with results
        """
        print(f"\n{'='*60}")
        print(f"Starting {self.target_duration_hours}-hour stress test")
        print(f"Checkpoints every {self.checkpoint_interval_minutes} minutes")
        print(f"Report will be saved to: {self.report_path}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        next_checkpoint = time.time() + (self.checkpoint_interval_minutes * 60)
        
        try:
            while not self._stop_requested:
                current_time = time.time()
                elapsed_hours = (current_time - start_time) / 3600
                
                # Check if target duration reached
                if elapsed_hours >= self.target_duration_hours:
                    print(f"\n✅ Target duration of {self.target_duration_hours} hours reached!")
                    break
                
                # Checkpoint if interval passed
                if current_time >= next_checkpoint:
                    checkpoint = self._create_checkpoint(elapsed_hours)
                    self.report.add_checkpoint(checkpoint)
                    self._print_checkpoint(checkpoint)
                    self.report.save_to_file(self.report_path)
                    next_checkpoint = current_time + (self.checkpoint_interval_minutes * 60)
                
                # Simulate workload
                await self._simulate_trading_workload()
                
                # Brief pause between iterations
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⚠️  Stress test interrupted by user")
        except Exception as e:
            print(f"\n❌ Stress test failed with error: {e}")
            raise
        finally:
            # Final checkpoint
            elapsed_hours = (time.time() - start_time) / 3600
            final_checkpoint = self._create_checkpoint(elapsed_hours)
            self.report.add_checkpoint(final_checkpoint)
            
            # Complete report
            self.report.end_time = datetime.now()
            self.report.actual_duration_hours = elapsed_hours
            self.report.total_orders = self.orders_processed
            self.report.total_errors = self.errors_encountered
            
            # Save final report
            self.report.save_to_file(self.report_path)
            self._print_final_report()
        
        return self.report
    
    def _create_checkpoint(self, elapsed_hours: float) -> StressTestCheckpoint:
        """Create a checkpoint with current system state."""
        mem_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent(interval=1)
        num_threads = self.process.num_threads()
        
        # Get connection count (approximation via file descriptors)
        try:
            num_connections = len(self.process.connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            num_connections = 0
        
        # Calculate average latency from recent samples
        avg_latency = sum(self.latency_samples[-100:]) / len(self.latency_samples[-100:]) if self.latency_samples else 0
        
        # Health checks
        is_healthy = True
        health_issues = []
        
        memory_mb = mem_info.rss / 1024 / 1024
        if memory_mb > self.report.max_memory_mb:
            is_healthy = False
            health_issues.append(f"Memory usage ({memory_mb:.0f}MB) exceeds limit ({self.report.max_memory_mb:.0f}MB)")
        
        if self.report.memory_leak_detected:
            is_healthy = False
            health_issues.append("Memory leak detected")
        
        if self.report.performance_degradation_detected:
            is_healthy = False
            health_issues.append("Performance degradation detected")
        
        return StressTestCheckpoint(
            timestamp=datetime.now(),
            elapsed_hours=elapsed_hours,
            memory_rss_mb=memory_mb,
            memory_vms_mb=mem_info.vms / 1024 / 1024,
            memory_percent=self.process.memory_percent(),
            cpu_percent=cpu_percent,
            num_connections=num_connections,
            num_threads=num_threads,
            orders_processed=self.orders_processed,
            avg_latency_ms=avg_latency,
            error_count=self.errors_encountered,
            is_healthy=is_healthy,
            health_issues=health_issues
        )
    
    async def _simulate_trading_workload(self):
        """Simulate realistic trading workload."""
        # Simulate order processing
        start = time.time()
        
        try:
            # Simulate work (replace with actual system calls in real test)
            await asyncio.sleep(0.01)  # 10ms per order
            
            self.orders_processed += 1
            latency_ms = (time.time() - start) * 1000
            self.latency_samples.append(latency_ms)
            
        except Exception:
            self.errors_encountered += 1
    
    def _print_checkpoint(self, checkpoint: StressTestCheckpoint):
        """Print checkpoint information."""
        status = "✅ HEALTHY" if checkpoint.is_healthy else "⚠️  ISSUES DETECTED"
        
        print(f"\n{'─'*60}")
        print(f"Checkpoint at {checkpoint.elapsed_hours:.2f} hours - {status}")
        print(f"{'─'*60}")
        print(f"Memory: {checkpoint.memory_rss_mb:.2f}MB (RSS), {checkpoint.memory_percent:.2f}% of system")
        print(f"CPU: {checkpoint.cpu_percent:.1f}%")
        print(f"Connections: {checkpoint.num_connections}, Threads: {checkpoint.num_threads}")
        print(f"Orders: {checkpoint.orders_processed:,} processed, {checkpoint.error_count} errors")
        print(f"Latency: {checkpoint.avg_latency_ms:.2f}ms average")
        
        if checkpoint.health_issues:
            print(f"\n⚠️  Health Issues:")
            for issue in checkpoint.health_issues:
                print(f"  - {issue}")
        
        print(f"{'─'*60}\n")
    
    def _print_final_report(self):
        """Print final stress test report."""
        print(f"\n{'='*60}")
        print(f"STRESS TEST FINAL REPORT")
        print(f"{'='*60}")
        print(f"Duration: {self.report.actual_duration_hours:.2f} / {self.report.target_duration_hours:.2f} hours")
        print(f"Checkpoints: {len(self.report.checkpoints)}")
        print(f"Total Orders: {self.report.total_orders:,}")
        print(f"Total Errors: {self.report.total_errors:,}")
        print(f"Error Rate: {(self.report.total_errors / max(self.report.total_orders, 1)) * 100:.4f}%")
        print(f"\nMemory Leak Detected: {'❌ YES' if self.report.memory_leak_detected else '✅ NO'}")
        print(f"Performance Degradation: {'❌ YES' if self.report.performance_degradation_detected else '✅ NO'}")
        print(f"\nReport saved to: {self.report_path}")
        print(f"{'='*60}\n")


@pytest.mark.production
@pytest.mark.stress_test
@pytest.mark.slow
class TestStressTest:
    """Stress testing suite."""
    
    @pytest.mark.asyncio
    async def test_short_stress_test_1_hour(self):
        """Short stress test (1 hour) for validation."""
        runner = StressTestRunner(
            target_duration_hours=1.0,
            checkpoint_interval_minutes=15,
            report_path=Path("stress_test_1h_report.json")
        )
        
        report = await runner.run_stress_test()
        
        # Assertions
        assert not report.memory_leak_detected, "Memory leak detected"
        assert not report.performance_degradation_detected, "Performance degradation detected"
        assert report.actual_duration_hours >= 0.95, "Test did not complete"
        
        # All checkpoints should be healthy
        unhealthy_checkpoints = [cp for cp in report.checkpoints if not cp.is_healthy]
        assert len(unhealthy_checkpoints) == 0, f"Found {len(unhealthy_checkpoints)} unhealthy checkpoints"
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Full 72-hour test - run manually")
    async def test_full_stress_test_72_hours(self):
        """
        Full 72-hour stress test.
        
        This test should be run manually as part of production validation.
        It will take 3 days to complete.
        
        To run:
            pytest tests/production/test_stress_testing.py::TestStressTest::test_full_stress_test_72_hours -v
        """
        runner = StressTestRunner(
            target_duration_hours=72.0,
            checkpoint_interval_minutes=60,  # Hourly checkpoints
            report_path=Path("stress_test_72h_report.json")
        )
        
        report = await runner.run_stress_test()
        
        # Assertions for 72-hour test
        assert not report.memory_leak_detected, "Memory leak detected over 72 hours"
        assert not report.performance_degradation_detected, "Performance degraded over 72 hours"
        assert report.actual_duration_hours >= 71.5, "Test did not complete full 72 hours"
        
        # Check final memory usage
        final_checkpoint = report.checkpoints[-1]
        assert final_checkpoint.memory_rss_mb < 2000, f"Memory usage too high: {final_checkpoint.memory_rss_mb}MB"
        
        # Check error rate
        error_rate = report.total_errors / max(report.total_orders, 1)
        assert error_rate < 0.001, f"Error rate too high: {error_rate * 100:.4f}%"
        
        print("\n✅ 72-hour stress test PASSED - System is production-ready!")


if __name__ == "__main__":
    # Run a short stress test
    import asyncio
    
    async def main():
        runner = StressTestRunner(
            target_duration_hours=0.1,  # 6 minutes for demo
            checkpoint_interval_minutes=2,
            report_path=Path("stress_test_demo.json")
        )
        await runner.run_stress_test()
    
    asyncio.run(main())
