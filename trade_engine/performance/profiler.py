#!/usr/bin/env python3
"""
System Profiler for Performance Analysis
========================================

Comprehensive system profiling and performance analysis for the trade engine.
Provides real-time performance monitoring, bottleneck identification, and 
optimization recommendations.

Author: StatArb_Gemini Team
"""

import time
import psutil
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import threading
import gc
import tracemalloc

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: float
    disk_io_read: float
    disk_io_write: float
    network_io_sent: float
    network_io_recv: float
    active_threads: int
    gc_collections: Dict[int, int]
    signal_generation_latency: Optional[float] = None
    portfolio_update_latency: Optional[float] = None
    execution_latency: Optional[float] = None

@dataclass
class PerformanceAlert:
    """Performance alert information"""
    alert_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    timestamp: datetime
    component: str
    metrics: Dict[str, Any]

class SystemProfiler:
    """
    Advanced system profiler for comprehensive performance analysis.
    
    Features:
    - Real-time system metrics collection
    - Component-specific performance tracking
    - Memory leak detection
    - Performance bottleneck identification
    - Automated alert generation
    """
    
    def __init__(self, collection_interval: float = 1.0, history_size: int = 3600):
        self.collection_interval = collection_interval
        self.history_size = history_size
        
        # Performance history
        self.metrics_history: deque = deque(maxlen=history_size)
        self.component_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        
        # Alert system
        self.alerts: deque = deque(maxlen=1000)
        self.alert_thresholds = {
            'cpu_usage': {'high': 80.0, 'critical': 95.0},
            'memory_usage': {'high': 85.0, 'critical': 95.0},
            'signal_latency': {'high': 5.0, 'critical': 10.0},  # milliseconds
            'portfolio_latency': {'high': 20.0, 'critical': 50.0},  # milliseconds
            'execution_latency': {'high': 100.0, 'critical': 500.0}  # milliseconds
        }
        
        # Profiling state
        self.is_profiling = False
        self.profiling_thread: Optional[threading.Thread] = None
        self.profiling_lock = threading.Lock()
        
        # Component timing
        self.component_timers: Dict[str, List[float]] = defaultdict(list)
        self.active_timers: Dict[str, float] = {}
        
        # Memory tracking
        self.memory_snapshots: List[Tuple[datetime, Any]] = []
        self.memory_tracking_enabled = False
        
        logger.info("SystemProfiler initialized")
    
    async def start_profiling(self):
        """Start continuous system profiling"""
        if self.is_profiling:
            logger.warning("Profiling already active")
            return
        
        self.is_profiling = True
        
        # Start memory tracking if available
        try:
            tracemalloc.start()
            self.memory_tracking_enabled = True
            logger.info("Memory tracking enabled")
        except Exception as e:
            logger.warning(f"Memory tracking unavailable: {e}")
        
        # Start profiling thread
        self.profiling_thread = threading.Thread(target=self._profiling_loop, daemon=True)
        self.profiling_thread.start()
        
        logger.info("System profiling started")
    
    async def stop_profiling(self):
        """Stop system profiling"""
        self.is_profiling = False
        
        if self.profiling_thread:
            self.profiling_thread.join(timeout=5.0)
        
        if self.memory_tracking_enabled:
            tracemalloc.stop()
        
        logger.info("System profiling stopped")
    
    def _profiling_loop(self):
        """Main profiling loop (runs in separate thread)"""
        while self.is_profiling:
            try:
                metrics = self._collect_system_metrics()
                
                with self.profiling_lock:
                    self.metrics_history.append(metrics)
                    self._check_alerts(metrics)
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in profiling loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> PerformanceMetrics:
        """Collect current system performance metrics"""
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        
        # Thread count
        active_threads = threading.active_count()
        
        # Garbage collection stats
        gc_stats = {}
        for i in range(3):
            gc_stats[i] = gc.get_count()[i]
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            memory_available=memory.available / (1024**3),  # GB
            disk_io_read=disk_io.read_bytes / (1024**2) if disk_io else 0,  # MB
            disk_io_write=disk_io.write_bytes / (1024**2) if disk_io else 0,  # MB
            network_io_sent=network_io.bytes_sent / (1024**2) if network_io else 0,  # MB
            network_io_recv=network_io.bytes_recv / (1024**2) if network_io else 0,  # MB
            active_threads=active_threads,
            gc_collections=gc_stats
        )
    
    def start_timer(self, component: str) -> str:
        """Start timing for a component"""
        timer_id = f"{component}_{int(time.time() * 1000000)}"  # Use microseconds for uniqueness
        self.active_timers[timer_id] = time.perf_counter()
        return timer_id
    
    def end_timer(self, timer_id: str) -> float:
        """End timing and record duration"""
        if timer_id not in self.active_timers:
            logger.warning(f"Timer {timer_id} not found")
            return 0.0
        
        start_time = self.active_timers.pop(timer_id)
        duration = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
        
        # Extract component name (everything except the last part after the last underscore)
        component_parts = timer_id.split('_')
        if len(component_parts) > 1:
            component = '_'.join(component_parts[:-1])  # Join all but the timestamp
        else:
            component = component_parts[0]
            
        self.component_timers[component].append(duration)
        
        # Keep only recent measurements
        if len(self.component_timers[component]) > 1000:
            self.component_timers[component] = self.component_timers[component][-1000:]
        
        return duration
    
    async def record_component_metric(self, component: str, metric_name: str, value: float):
        """Record a component-specific metric"""
        timestamp = datetime.now()
        metric_data = {
            'timestamp': timestamp,
            'metric_name': metric_name,
            'value': value
        }
        
        with self.profiling_lock:
            self.component_metrics[component].append(metric_data)
    
    def _check_alerts(self, metrics: PerformanceMetrics):
        """Check for performance alerts"""
        # CPU usage alert
        if metrics.cpu_usage > self.alert_thresholds['cpu_usage']['critical']:
            self._create_alert('cpu_usage', 'CRITICAL', 
                             f"Critical CPU usage: {metrics.cpu_usage:.1f}%", metrics)
        elif metrics.cpu_usage > self.alert_thresholds['cpu_usage']['high']:
            self._create_alert('cpu_usage', 'HIGH',
                             f"High CPU usage: {metrics.cpu_usage:.1f}%", metrics)
        
        # Memory usage alert
        if metrics.memory_usage > self.alert_thresholds['memory_usage']['critical']:
            self._create_alert('memory_usage', 'CRITICAL',
                             f"Critical memory usage: {metrics.memory_usage:.1f}%", metrics)
        elif metrics.memory_usage > self.alert_thresholds['memory_usage']['high']:
            self._create_alert('memory_usage', 'HIGH',
                             f"High memory usage: {metrics.memory_usage:.1f}%", metrics)
    
    def _create_alert(self, alert_type: str, severity: str, message: str, metrics: PerformanceMetrics):
        """Create a performance alert"""
        alert = PerformanceAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
            component='system',
            metrics={
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'memory_available': metrics.memory_available
            }
        )
        
        self.alerts.append(alert)
        logger.warning(f"Performance Alert [{severity}]: {message}")
    
    def get_performance_summary(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self.profiling_lock:
            recent_metrics = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        
        if not recent_metrics:
            return {'error': 'No recent metrics available'}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_threads = sum(m.active_threads for m in recent_metrics) / len(recent_metrics)
        
        # Calculate component latencies
        component_stats = {}
        for component, timings in self.component_timers.items():
            if timings:
                recent_timings = timings[-100:]  # Last 100 measurements
                component_stats[component] = {
                    'avg_latency_ms': sum(recent_timings) / len(recent_timings),
                    'max_latency_ms': max(recent_timings),
                    'min_latency_ms': min(recent_timings),
                    'sample_count': len(recent_timings)
                }
        
        return {
            'duration_minutes': duration_minutes,
            'sample_count': len(recent_metrics),
            'avg_cpu_usage': avg_cpu,
            'avg_memory_usage': avg_memory,
            'avg_active_threads': avg_threads,
            'component_performance': component_stats,
            'recent_alerts': len([a for a in self.alerts if a.timestamp > cutoff_time])
        }
    
    def get_recent_alerts(self, severity_filter: Optional[str] = None) -> List[PerformanceAlert]:
        """Get recent alerts, optionally filtered by severity"""
        alerts = list(self.alerts)
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def take_memory_snapshot(self, label: str = ""):
        """Take a memory snapshot for leak detection"""
        if not self.memory_tracking_enabled:
            logger.warning("Memory tracking not enabled")
            return
        
        try:
            snapshot = tracemalloc.take_snapshot()
            self.memory_snapshots.append((datetime.now(), snapshot))
            
            # Keep only recent snapshots
            if len(self.memory_snapshots) > 10:
                self.memory_snapshots = self.memory_snapshots[-10:]
            
            logger.info(f"Memory snapshot taken: {label}")
            
        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
    
    def analyze_memory_growth(self) -> Optional[Dict[str, Any]]:
        """Analyze memory growth between snapshots"""
        if len(self.memory_snapshots) < 2:
            return None
        
        try:
            # Compare first and last snapshots
            first_time, first_snapshot = self.memory_snapshots[0]
            last_time, last_snapshot = self.memory_snapshots[-1]
            
            # Get top memory consumers
            top_stats = last_snapshot.compare_to(first_snapshot, 'lineno')[:10]
            
            memory_analysis = {
                'time_span_minutes': (last_time - first_time).total_seconds() / 60,
                'top_memory_growth': []
            }
            
            for stat in top_stats:
                memory_analysis['top_memory_growth'].append({
                    'filename': stat.traceback.format()[0],
                    'size_diff_mb': stat.size_diff / (1024**2),
                    'count_diff': stat.count_diff
                })
            
            return memory_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing memory growth: {e}")
            return None

# Global profiler instance
system_profiler = SystemProfiler()

async def start_performance_profiling():
    """Start global performance profiling"""
    await system_profiler.start_profiling()

async def stop_performance_profiling():
    """Stop global performance profiling"""
    await system_profiler.stop_profiling()

def time_component(component_name: str):
    """Decorator for timing component operations"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                timer_id = system_profiler.start_timer(component_name)
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    system_profiler.end_timer(timer_id)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                timer_id = system_profiler.start_timer(component_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    system_profiler.end_timer(timer_id)
            return sync_wrapper
    return decorator
