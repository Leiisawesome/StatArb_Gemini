"""
Performance Monitor for Load Testing
====================================

Real-time performance monitoring and metrics collection during load tests.

Metrics Tracked:
- Order latency (submission to execution)
- System throughput (orders/second)
- Memory usage (RSS, heap)
- CPU usage (per core, total)
- Network I/O
- Database query performance
- Error rates and types
"""

import asyncio
import psutil
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque
import statistics
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Order metrics
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    orders_per_second: float = 0.0
    
    # Latency metrics (milliseconds)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    
    # System metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    
    # Network metrics (optional)
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    
    # Error metrics
    error_rate: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'orders': {
                'total': self.total_orders,
                'successful': self.successful_orders,
                'failed': self.failed_orders,
                'rate': round(self.orders_per_second, 2)
            },
            'latency_ms': {
                'avg': round(self.avg_latency_ms, 2),
                'p50': round(self.p50_latency_ms, 2),
                'p95': round(self.p95_latency_ms, 2),
                'p99': round(self.p99_latency_ms, 2),
                'max': round(self.max_latency_ms, 2),
                'min': round(self.min_latency_ms, 2)
            },
            'system': {
                'cpu_percent': round(self.cpu_percent, 1),
                'memory_mb': round(self.memory_mb, 1),
                'memory_percent': round(self.memory_percent, 1)
            },
            'network_mb': {
                'sent': round(self.network_sent_mb, 2),
                'recv': round(self.network_recv_mb, 2)
            },
            'errors': {
                'rate': round(self.error_rate, 4),
                'by_type': self.errors_by_type
            }
        }


@dataclass
class PerformanceMonitorConfig:
    """Configuration for performance monitor"""
    
    # Monitoring intervals
    metrics_collection_interval_sec: float = 1.0
    metrics_display_interval_sec: float = 10.0
    
    # History retention
    max_history_size: int = 3600  # 1 hour at 1 sec intervals
    latency_history_size: int = 10000  # Last 10k orders
    
    # Alert thresholds
    latency_threshold_ms: float = 100.0
    error_rate_threshold: float = 0.01  # 1%
    memory_threshold_mb: float = 2048.0  # 2GB
    cpu_threshold_percent: float = 80.0
    
    # Output settings
    save_metrics_to_file: bool = True
    metrics_file_path: str = "load_test_metrics.jsonl"
    display_console: bool = True


@dataclass
class OrderMetric:
    """Individual order performance metric"""
    order_id: str
    submission_time: datetime
    completion_time: Optional[datetime] = None
    latency_ms: Optional[float] = None
    success: bool = False
    error_type: Optional[str] = None
    
    def calculate_latency(self):
        """Calculate latency if completion time is set"""
        if self.completion_time:
            self.latency_ms = (self.completion_time - self.submission_time).total_seconds() * 1000


class PerformanceMonitor:
    """
    Real-time Performance Monitor
    
    Tracks and reports system performance during load testing:
    - Order execution metrics
    - System resource usage
    - Latency distribution
    - Error rates and types
    """
    
    def __init__(self, config: Optional[PerformanceMonitorConfig] = None):
        self.config = config or PerformanceMonitorConfig()
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=self.config.max_history_size)
        self.latency_buffer: deque = deque(maxlen=self.config.latency_history_size)
        self.order_metrics: Dict[str, OrderMetric] = {}
        
        # Counters
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.errors_by_type: Dict[str, int] = {}
        
        # Timing
        self.start_time: Optional[datetime] = None
        self.last_metrics_time: Optional[datetime] = None
        
        # System monitoring
        self.process = psutil.Process()
        self.initial_network_io: Optional[Any] = None
        
        # State
        self.is_running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._display_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.alert_callbacks: List[Callable] = []
        
        # Output file
        self.metrics_file = None
        
        logger.info("📊 Performance Monitor initialized")
    
    async def start(self):
        """Start performance monitoring"""
        self.is_running = True
        self.start_time = datetime.now()
        self.last_metrics_time = self.start_time
        
        # Get initial network I/O
        try:
            self.initial_network_io = psutil.net_io_counters()
        except:
            self.initial_network_io = None
        
        # Open metrics file
        if self.config.save_metrics_to_file:
            self.metrics_file = open(self.config.metrics_file_path, 'w')
        
        # Start monitoring tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._display_task = asyncio.create_task(self._display_loop())
        
        logger.info("🚀 Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring"""
        self.is_running = False
        
        # Cancel tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._display_task:
            self._display_task.cancel()
            try:
                await self._display_task
            except asyncio.CancelledError:
                pass
        
        # Close metrics file
        if self.metrics_file:
            self.metrics_file.close()
        
        # Generate final report
        self._print_final_report()
        
        logger.info("⏹️  Performance monitoring stopped")
    
    def record_order_submission(self, order_id: str):
        """Record order submission"""
        self.order_metrics[order_id] = OrderMetric(
            order_id=order_id,
            submission_time=datetime.now()
        )
        self.total_orders += 1
    
    def record_order_completion(self, order_id: str, success: bool, error_type: Optional[str] = None):
        """Record order completion"""
        if order_id in self.order_metrics:
            metric = self.order_metrics[order_id]
            metric.completion_time = datetime.now()
            metric.success = success
            metric.error_type = error_type
            metric.calculate_latency()
            
            # Update counters
            if success:
                self.successful_orders += 1
                if metric.latency_ms:
                    self.latency_buffer.append(metric.latency_ms)
            else:
                self.failed_orders += 1
                if error_type:
                    self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
            
            # Clean up old metrics (keep last 1000)
            if len(self.order_metrics) > 1000:
                oldest_keys = list(self.order_metrics.keys())[:100]
                for key in oldest_keys:
                    del self.order_metrics[key]
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        
        current_time = datetime.now()
        
        # Calculate orders per second
        if self.last_metrics_time:
            time_delta = (current_time - self.last_metrics_time).total_seconds()
            orders_delta = self.total_orders - (self.metrics_history[-1].total_orders if self.metrics_history else 0)
            orders_per_second = orders_delta / time_delta if time_delta > 0 else 0
        else:
            orders_per_second = 0
        
        # Calculate latency percentiles
        if self.latency_buffer:
            sorted_latencies = sorted(self.latency_buffer)
            n = len(sorted_latencies)
            
            avg_latency = statistics.mean(sorted_latencies)
            p50_latency = sorted_latencies[int(n * 0.50)]
            p95_latency = sorted_latencies[int(n * 0.95)]
            p99_latency = sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]
            max_latency = max(sorted_latencies)
            min_latency = min(sorted_latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = max_latency = min_latency = 0
        
        # Get system metrics
        cpu_percent = self.process.cpu_percent()
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = self.process.memory_percent()
        
        # Get network I/O
        network_sent_mb = 0
        network_recv_mb = 0
        if self.initial_network_io:
            try:
                current_network = psutil.net_io_counters()
                network_sent_mb = (current_network.bytes_sent - self.initial_network_io.bytes_sent) / 1024 / 1024
                network_recv_mb = (current_network.bytes_recv - self.initial_network_io.bytes_recv) / 1024 / 1024
            except:
                pass
        
        # Calculate error rate
        error_rate = self.failed_orders / self.total_orders if self.total_orders > 0 else 0
        
        # Create metrics
        metrics = PerformanceMetrics(
            timestamp=current_time,
            total_orders=self.total_orders,
            successful_orders=self.successful_orders,
            failed_orders=self.failed_orders,
            orders_per_second=orders_per_second,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            max_latency_ms=max_latency,
            min_latency_ms=min_latency,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            error_rate=error_rate,
            errors_by_type=dict(self.errors_by_type)
        )
        
        # Check for alerts
        await self._check_alerts(metrics)
        
        self.last_metrics_time = current_time
        
        return metrics
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        try:
            while self.is_running:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Save to file
                if self.metrics_file:
                    self.metrics_file.write(json.dumps(metrics.to_dict()) + '\n')
                    self.metrics_file.flush()
                
                await asyncio.sleep(self.config.metrics_collection_interval_sec)
        except asyncio.CancelledError:
            pass
    
    async def _display_loop(self):
        """Display metrics periodically"""
        try:
            while self.is_running:
                await asyncio.sleep(self.config.metrics_display_interval_sec)
                
                if self.config.display_console and self.metrics_history:
                    self._print_current_metrics()
        except asyncio.CancelledError:
            pass
    
    def _print_current_metrics(self):
        """Print current metrics to console"""
        if not self.metrics_history:
            return
        
        metrics = self.metrics_history[-1]
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(f"📊 PERFORMANCE METRICS - Elapsed: {elapsed:.0f}s")
        print("=" * 80)
        print(f"Orders:    Total: {metrics.total_orders:,}  |  Success: {metrics.successful_orders:,}  |  Failed: {metrics.failed_orders}")
        print(f"Rate:      {metrics.orders_per_second:.1f} orders/sec")
        print(f"Latency:   Avg: {metrics.avg_latency_ms:.1f}ms  |  P95: {metrics.p95_latency_ms:.1f}ms  |  P99: {metrics.p99_latency_ms:.1f}ms")
        print(f"System:    CPU: {metrics.cpu_percent:.1f}%  |  Memory: {metrics.memory_mb:.0f}MB ({metrics.memory_percent:.1f}%)")
        print(f"Network:   Sent: {metrics.network_sent_mb:.1f}MB  |  Recv: {metrics.network_recv_mb:.1f}MB")
        print(f"Errors:    Rate: {metrics.error_rate*100:.2f}%")
        
        if metrics.errors_by_type:
            print(f"Error Types:")
            for error_type, count in sorted(metrics.errors_by_type.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {error_type}: {count}")
        
        print("=" * 80)
    
    def _print_final_report(self):
        """Print final performance report"""
        if not self.metrics_history:
            return
        
        final_metrics = self.metrics_history[-1]
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("📊 FINAL PERFORMANCE REPORT")
        print("=" * 80)
        print(f"\n⏱️  Test Duration: {elapsed:.0f} seconds ({elapsed/3600:.2f} hours)")
        print(f"\n📦 Order Statistics:")
        print(f"   Total Orders:      {final_metrics.total_orders:,}")
        if final_metrics.total_orders > 0:
            success_pct = final_metrics.successful_orders/final_metrics.total_orders*100
            print(f"   Successful:        {final_metrics.successful_orders:,} ({success_pct:.1f}%)")
        else:
            print(f"   Successful:        {final_metrics.successful_orders:,} (0.0%)")
        print(f"   Failed:            {final_metrics.failed_orders} ({final_metrics.error_rate*100:.2f}%)")
        if elapsed > 0:
            print(f"   Avg Rate:          {final_metrics.total_orders/elapsed:.1f} orders/sec")
        else:
            print(f"   Avg Rate:          0.0 orders/sec")
        
        print(f"\n⚡ Latency Statistics (milliseconds):")
        print(f"   Average:           {final_metrics.avg_latency_ms:.2f}ms")
        print(f"   Median (P50):      {final_metrics.p50_latency_ms:.2f}ms")
        print(f"   P95:               {final_metrics.p95_latency_ms:.2f}ms")
        print(f"   P99:               {final_metrics.p99_latency_ms:.2f}ms")
        print(f"   Max:               {final_metrics.max_latency_ms:.2f}ms")
        print(f"   Min:               {final_metrics.min_latency_ms:.2f}ms")
        
        print(f"\n💻 System Resources:")
        print(f"   Peak CPU:          {max(m.cpu_percent for m in self.metrics_history):.1f}%")
        print(f"   Peak Memory:       {max(m.memory_mb for m in self.metrics_history):.0f}MB")
        print(f"   Avg CPU:           {statistics.mean(m.cpu_percent for m in self.metrics_history):.1f}%")
        print(f"   Avg Memory:        {statistics.mean(m.memory_mb for m in self.metrics_history):.0f}MB")
        
        print(f"\n🌐 Network Usage:")
        print(f"   Total Sent:        {final_metrics.network_sent_mb:.2f}MB")
        print(f"   Total Received:    {final_metrics.network_recv_mb:.2f}MB")
        
        if final_metrics.errors_by_type:
            print(f"\n❌ Error Breakdown:")
            for error_type, count in sorted(final_metrics.errors_by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error_type}: {count}")
        
        # Performance assessment
        print(f"\n✅ Performance Assessment:")
        
        latency_ok = final_metrics.p99_latency_ms < self.config.latency_threshold_ms
        error_rate_ok = final_metrics.error_rate < self.config.error_rate_threshold
        throughput_ok = final_metrics.total_orders / elapsed >= 10000 / (24 * 3600)  # 10k orders/day rate
        
        print(f"   Latency (P99 < {self.config.latency_threshold_ms}ms):       {'✅ PASS' if latency_ok else '❌ FAIL'}")
        print(f"   Error Rate (< {self.config.error_rate_threshold*100:.1f}%):         {'✅ PASS' if error_rate_ok else '❌ FAIL'}")
        print(f"   Throughput (>= 0.12 orders/sec): {'✅ PASS' if throughput_ok else '❌ FAIL'}")
        
        overall_pass = latency_ok and error_rate_ok and throughput_ok
        print(f"\n{'🎉 OVERALL: PASS' if overall_pass else '⚠️  OVERALL: NEEDS IMPROVEMENT'}")
        
        print("=" * 80 + "\n")
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Check for alert conditions"""
        alerts = []
        
        if metrics.p99_latency_ms > self.config.latency_threshold_ms:
            alerts.append(f"High P99 latency: {metrics.p99_latency_ms:.1f}ms (threshold: {self.config.latency_threshold_ms}ms)")
        
        if metrics.error_rate > self.config.error_rate_threshold:
            alerts.append(f"High error rate: {metrics.error_rate*100:.2f}% (threshold: {self.config.error_rate_threshold*100:.1f}%)")
        
        if metrics.memory_mb > self.config.memory_threshold_mb:
            alerts.append(f"High memory usage: {metrics.memory_mb:.0f}MB (threshold: {self.config.memory_threshold_mb}MB)")
        
        if metrics.cpu_percent > self.config.cpu_threshold_percent:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}% (threshold: {self.config.cpu_threshold_percent}%)")
        
        # Trigger callbacks
        for alert in alerts:
            logger.warning(f"⚠️  ALERT: {alert}")
            for callback in self.alert_callbacks:
                try:
                    await callback(alert, metrics)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, duration_seconds: Optional[int] = None) -> List[PerformanceMetrics]:
        """Get metrics history for specified duration"""
        if duration_seconds is None:
            return list(self.metrics_history)
        
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the entire monitoring period"""
        if not self.order_metrics:
            return {
                'total_orders': 0,
                'successful_orders': 0,
                'failed_orders': 0,
                'success_rate': 0.0,
                'avg_latency_ms': 0.0,
                'p50_latency_ms': 0.0,
                'p95_latency_ms': 0.0,
                'p99_latency_ms': 0.0,
                'max_latency_ms': 0.0,
                'min_latency_ms': 0.0,
                'throughput_per_sec': 0.0,
                'peak_cpu_percent': 0.0,
                'peak_memory_mb': 0.0,
                'errors_by_type': {}
            }
        
        #Extract latencies from order metrics
        latencies = [
            (metric.completion_time - metric.submission_time).total_seconds() * 1000 
            for metric in self.order_metrics.values() 
            if metric.completion_time
        ]
        
        if not latencies:
            latencies = [0]
        
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 1
        
        return {
            'total_orders': len(self.order_metrics),
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': self.successful_orders / len(self.order_metrics) if self.order_metrics else 0,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'p50_latency_ms': sorted_latencies[int(n * 0.50)] if n > 0 else 0,
            'p95_latency_ms': sorted_latencies[int(n * 0.95)] if n > 0 else 0,
            'p99_latency_ms': sorted_latencies[int(n * 0.99)] if n > 0 else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'throughput_per_sec': len(self.order_metrics) / duration if duration > 0 else 0,
            'peak_cpu_percent': max((m.cpu_percent for m in self.metrics_history), default=0),
            'peak_memory_mb': max((m.memory_mb for m in self.metrics_history), default=0),
            'errors_by_type': dict(self.errors_by_type)
        }


if __name__ == "__main__":
    # Test the performance monitor
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        print("Testing Performance Monitor...")
        print("-" * 50)
        
        monitor = PerformanceMonitor()
        await monitor.start()
        
        # Simulate some orders
        for i in range(100):
            order_id = f"TEST_{i:04d}"
            monitor.record_order_submission(order_id)
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            # Record completion
            success = i % 10 != 0  # 10% failure rate
            error_type = "timeout" if not success else None
            monitor.record_order_completion(order_id, success, error_type)
        
        # Wait for metrics
        await asyncio.sleep(2)
        
        await monitor.stop()
        
        print("\n✅ Performance monitor test complete!")
    
    asyncio.run(test())
