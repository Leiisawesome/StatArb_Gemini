"""
Performance Monitoring - Core Engine
===================================

Performance monitoring and profiling system for core_engine components.
Provides real-time performance metrics, profiling, and bottleneck detection.
"""

import time
import threading
import asyncio
import psutil
import tracemalloc
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
import cProfile
import pstats
import io

from .logging import get_logger, log_performance_metric
from .exceptions import ErrorContext

logger = get_logger("performance")

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    component: str = ""
    operation: str = ""

@dataclass
class PerformanceSnapshot:
    """System performance snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    network_connections: int
    thread_count: int
    open_files: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OperationProfile:
    """Operation performance profile"""
    operation_name: str
    call_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    last_called: Optional[datetime] = None
    error_count: int = 0

class PerformanceMonitor:
    """
    Performance monitoring system

    Provides comprehensive performance tracking, profiling, and alerting
    for core_engine components.
    """

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.snapshots: List[PerformanceSnapshot] = []
        self.operation_profiles: Dict[str, OperationProfile] = {}
        self.alert_thresholds: Dict[str, float] = {}
        self.alert_callbacks: List[Callable[[PerformanceMetric], Awaitable[None]]] = []

        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.snapshot_interval = 60.0  # seconds

        # Profiling state
        self.memory_tracing = False
        self.cpu_profiling = False

        # Locks for thread safety
        self._metrics_lock = threading.Lock()
        self._profiles_lock = threading.Lock()

    def start_monitoring(self):
        """Start performance monitoring"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                asyncio.wait_for(self.monitoring_task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                snapshot = self.take_snapshot()
                self.snapshots.append(snapshot)

                # Keep only recent snapshots (last 24 hours)
                cutoff = datetime.now() - timedelta(hours=24)
                self.snapshots = [s for s in self.snapshots if s.timestamp > cutoff]

                await asyncio.sleep(self.snapshot_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(5)

    def take_snapshot(self) -> PerformanceSnapshot:
        """Take a system performance snapshot"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent

            # Network connections
            network_connections = len(psutil.net_connections())

            # Thread count
            thread_count = threading.active_count()

            # Open files (Unix only)
            try:
                open_files = len(psutil.Process().open_files())
            except (psutil.AccessDenied, AttributeError):
                open_files = 0

            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage_percent,
                network_connections=network_connections,
                thread_count=thread_count,
                open_files=open_files
            )

            logger.debug(f"Performance snapshot: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB ({memory_percent:.1f}%)")
            return snapshot

        except Exception as e:
            logger.error(f"Failed to take performance snapshot: {e}")
            return PerformanceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_connections=0,
                thread_count=0,
                open_files=0,
                metadata={"error": str(e)}
            )

    def record_metric(self, name: str, value: float, unit: str = "",
                     component: str = "", operation: str = "",
                     metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            component=component,
            operation=operation,
            metadata=metadata or {}
        )

        with self._metrics_lock:
            self.metrics.append(metric)

            # Keep only recent metrics (last hour)
            cutoff = datetime.now() - timedelta(hours=1)
            self.metrics = [m for m in self.metrics if m.timestamp > cutoff]

        # Log the metric
        log_performance_metric(component or "performance", name, value, unit, metadata)

        # Check alert thresholds
        if name in self.alert_thresholds:
            threshold = self.alert_thresholds[name]
            if self._should_alert(name, value, threshold):
                asyncio.create_task(self._trigger_alerts(metric))

    def set_alert_threshold(self, metric_name: str, threshold: float):
        """Set alert threshold for a metric"""
        self.alert_thresholds[metric_name] = threshold

    def add_alert_callback(self, callback: Callable[[PerformanceMetric], Awaitable[None]]):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)

    def _should_alert(self, metric_name: str, value: float, threshold: float) -> bool:
        """Determine if an alert should be triggered"""
        # Simple threshold-based alerting
        # Could be extended with more sophisticated logic
        return value > threshold

    async def _trigger_alerts(self, metric: PerformanceMetric):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                await callback(metric)
            except Exception as e:
                logger.error(f"Performance alert callback failed: {e}")

    @contextmanager
    def profile_operation(self, operation_name: str, component: str = ""):
        """Context manager for operation profiling"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss if psutil else 0

        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time

            end_memory = psutil.Process().memory_info().rss if psutil else 0
            memory_delta = end_memory - start_memory

            # Record metrics
            self.record_metric(
                f"{operation_name}_duration",
                duration * 1000,  # Convert to milliseconds
                "ms",
                component,
                operation_name
            )

            if memory_delta != 0:
                self.record_metric(
                    f"{operation_name}_memory_delta",
                    memory_delta / 1024 / 1024,  # Convert to MB
                    "MB",
                    component,
                    operation_name
                )

            # Update operation profile
            self._update_operation_profile(operation_name, duration)

    def profile_function(self, component: str = "", operation: str = None):
        """Decorator for function profiling"""
        def decorator(func):
            op_name = operation or f"{func.__module__}.{func.__qualname__}"

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.profile_operation(op_name, component):
                    return func(*args, **kwargs)

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.profile_operation(op_name, component):
                    return await func(*args, **kwargs)

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def _update_operation_profile(self, operation_name: str, duration: float):
        """Update operation performance profile"""
        with self._profiles_lock:
            if operation_name not in self.operation_profiles:
                self.operation_profiles[operation_name] = OperationProfile(operation_name)

            profile = self.operation_profiles[operation_name]
            profile.call_count += 1
            profile.total_time += duration
            profile.avg_time = profile.total_time / profile.call_count
            profile.min_time = min(profile.min_time, duration)
            profile.max_time = max(profile.max_time, duration)
            profile.last_called = datetime.now()

    def get_operation_profile(self, operation_name: str) -> Optional[OperationProfile]:
        """Get performance profile for an operation"""
        return self.operation_profiles.get(operation_name)

    def get_all_profiles(self) -> Dict[str, OperationProfile]:
        """Get all operation profiles"""
        with self._profiles_lock:
            return self.operation_profiles.copy()

    def start_memory_tracing(self):
        """Start memory tracing"""
        if not self.memory_tracing:
            tracemalloc.start()
            self.memory_tracing = True
            logger.info("Memory tracing started")

    def stop_memory_tracing(self):
        """Stop memory tracing"""
        if self.memory_tracing:
            tracemalloc.stop()
            self.memory_tracing = False
            logger.info("Memory tracing stopped")

    def get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory usage snapshot"""
        if not self.memory_tracing:
            return {"error": "Memory tracing not enabled"}

        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')

            return {
                "total_blocks": len(snapshot.traces),
                "total_size_mb": sum(stat.size for stat in top_stats) / 1024 / 1024,
                "top_allocations": [
                    {
                        "size_mb": stat.size / 1024 / 1024,
                        "count": stat.count,
                        "file": stat.traceback[0].filename if stat.traceback else "unknown",
                        "line": stat.traceback[0].lineno if stat.traceback else 0
                    }
                    for stat in top_stats[:10]
                ]
            }
        except Exception as e:
            return {"error": str(e)}

    def start_cpu_profiling(self, output_file: Optional[str] = None):
        """Start CPU profiling"""
        if not self.cpu_profiling:
            self._profiler = cProfile.Profile()
            self._profiler.enable()
            self.cpu_profiling = True
            self._profile_output = output_file
            logger.info("CPU profiling started")

    def stop_cpu_profiling(self) -> Optional[str]:
        """Stop CPU profiling and return profile stats"""
        if not self.cpu_profiling:
            return None

        self._profiler.disable()
        self.cpu_profiling = False

        # Generate profile stats
        stats = pstats.Stats(self._profiler)
        stats.sort_stats('cumulative')

        if self._profile_output:
            stats.dump_stats(self._profile_output)
            logger.info(f"CPU profile saved to {self._profile_output}")
            return self._profile_output
        else:
            # Return stats as string
            output = io.StringIO()
            stats.stream = output
            stats.print_stats(20)
            profile_str = output.getvalue()
            logger.info("CPU profiling completed")
            return profile_str

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system performance metrics"""
        latest_snapshot = self.snapshots[-1] if self.snapshots else None

        return {
            "current_snapshot": {
                "cpu_percent": latest_snapshot.cpu_percent if latest_snapshot else 0,
                "memory_mb": latest_snapshot.memory_mb if latest_snapshot else 0,
                "memory_percent": latest_snapshot.memory_percent if latest_snapshot else 0,
                "thread_count": latest_snapshot.thread_count if latest_snapshot else 0,
                "timestamp": latest_snapshot.timestamp.isoformat() if latest_snapshot else None
            },
            "operation_profiles": {
                name: {
                    "call_count": profile.call_count,
                    "avg_time_ms": profile.avg_time * 1000,
                    "min_time_ms": profile.min_time * 1000,
                    "max_time_ms": profile.max_time * 1000,
                    "last_called": profile.last_called.isoformat() if profile.last_called else None
                }
                for name, profile in self.get_all_profiles().items()
            },
            "memory_tracing": self.memory_tracing,
            "cpu_profiling": self.cpu_profiling,
            "alert_thresholds": self.alert_thresholds.copy()
        }

# Global performance monitor instance
_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor"""
    return _monitor

def record_performance_metric(name: str, value: float, unit: str = "",
                             component: str = "", operation: str = "",
                             metadata: Optional[Dict[str, Any]] = None):
    """Record a performance metric"""
    _monitor.record_metric(name, value, unit, component, operation, metadata)

def profile_function(component: str = "", operation: str = None):
    """Decorator for function profiling"""
    return _monitor.profile_function(component, operation)

def profile_operation(operation_name: str, component: str = ""):
    """Context manager for operation profiling"""
    return _monitor.profile_operation(operation_name, component)

# Convenience functions
def start_performance_monitoring():
    """Start the global performance monitor"""
    _monitor.start_monitoring()

def stop_performance_monitoring():
    """Stop the global performance monitor"""
    _monitor.stop_monitoring()

def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return _monitor.get_system_metrics()