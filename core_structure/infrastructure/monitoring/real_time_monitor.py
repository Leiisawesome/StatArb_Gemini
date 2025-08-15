"""
Real-Time Performance Monitor
============================

Provides real-time monitoring of core engine performance with
alerting and automatic issue detection.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class MetricType(Enum):
    """Types of metrics to monitor"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"

@dataclass
class MonitorConfig:
    """Configuration for real-time monitoring"""
    # Monitoring settings
    monitoring_interval_ms: int = 100  # 100ms monitoring intervals
    metric_history_size: int = 1000
    alert_threshold_multiplier: float = 2.0
    
    # Performance thresholds
    max_latency_ms: float = 5.0
    min_throughput: float = 1000.0
    max_error_rate: float = 0.01  # 1%
    max_memory_usage_mb: float = 1024.0  # 1GB
    max_cpu_usage: float = 0.8  # 80%
    
    # Alerting
    enable_alerts: bool = True
    enable_auto_recovery: bool = True
    alert_cooldown_seconds: int = 60

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    timestamp: datetime
    component: str
    metric_type: MetricType
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """Performance alert notification"""
    timestamp: datetime
    level: AlertLevel
    component: str
    metric_type: MetricType
    message: str
    current_value: float
    threshold: float
    suggested_action: str

class MetricAggregator:
    """Aggregates and analyzes performance metrics"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_metric(self, metric: PerformanceMetric):
        """Add a new metric to the aggregator"""
        key = f"{metric.component}_{metric.metric_type.value}"
        self.metrics[key].append(metric)
    
    def get_recent_metrics(self, component: str, metric_type: MetricType, 
                          duration_seconds: int = 60) -> List[PerformanceMetric]:
        """Get recent metrics for a component and type"""
        key = f"{component}_{metric_type.value}"
        if key not in self.metrics:
            return []
        
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        return [m for m in self.metrics[key] if m.timestamp >= cutoff_time]
    
    def calculate_statistics(self, component: str, metric_type: MetricType,
                           duration_seconds: int = 60) -> Dict[str, float]:
        """Calculate statistics for recent metrics"""
        recent_metrics = self.get_recent_metrics(component, metric_type, duration_seconds)
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99)
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Register callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def check_thresholds(self, metric: PerformanceMetric) -> Optional[PerformanceAlert]:
        """Check if metric exceeds thresholds and create alert if needed"""
        alert = None
        
        # Check latency thresholds
        if metric.metric_type == MetricType.LATENCY:
            if metric.value > self.config.max_latency_ms:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if metric.value < self.config.max_latency_ms * 2 else AlertLevel.CRITICAL,
                    component=metric.component,
                    metric_type=metric.metric_type,
                    message=f"High latency detected in {metric.component}",
                    current_value=metric.value,
                    threshold=self.config.max_latency_ms,
                    suggested_action="Check component optimization settings"
                )
        
        # Check throughput thresholds
        elif metric.metric_type == MetricType.THROUGHPUT:
            if metric.value < self.config.min_throughput:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if metric.value > self.config.min_throughput * 0.5 else AlertLevel.CRITICAL,
                    component=metric.component,
                    metric_type=metric.metric_type,
                    message=f"Low throughput detected in {metric.component}",
                    current_value=metric.value,
                    threshold=self.config.min_throughput,
                    suggested_action="Increase parallel processing or batch size"
                )
        
        # Check error rate thresholds
        elif metric.metric_type == MetricType.ERROR_RATE:
            if metric.value > self.config.max_error_rate:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.CRITICAL if metric.value > self.config.max_error_rate * 2 else AlertLevel.WARNING,
                    component=metric.component,
                    metric_type=metric.metric_type,
                    message=f"High error rate detected in {metric.component}",
                    current_value=metric.value,
                    threshold=self.config.max_error_rate,
                    suggested_action="Investigate component errors and stability"
                )
        
        # Check memory usage thresholds
        elif metric.metric_type == MetricType.MEMORY_USAGE:
            if metric.value > self.config.max_memory_usage_mb:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if metric.value < self.config.max_memory_usage_mb * 1.5 else AlertLevel.CRITICAL,
                    component=metric.component,
                    metric_type=metric.metric_type,
                    message=f"High memory usage detected in {metric.component}",
                    current_value=metric.value,
                    threshold=self.config.max_memory_usage_mb,
                    suggested_action="Enable memory optimization or increase limits"
                )
        
        # Check CPU usage thresholds
        elif metric.metric_type == MetricType.CPU_USAGE:
            if metric.value > self.config.max_cpu_usage:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.WARNING if metric.value < self.config.max_cpu_usage * 1.2 else AlertLevel.CRITICAL,
                    component=metric.component,
                    metric_type=metric.metric_type,
                    message=f"High CPU usage detected in {metric.component}",
                    current_value=metric.value,
                    threshold=self.config.max_cpu_usage,
                    suggested_action="Optimize processing algorithms or reduce load"
                )
        
        if alert and self._should_send_alert(alert):
            self._send_alert(alert)
            return alert
        
        return None
    
    def _should_send_alert(self, alert: PerformanceAlert) -> bool:
        """Check if alert should be sent based on cooldown"""
        if not self.config.enable_alerts:
            return False
        
        key = f"{alert.component}_{alert.metric_type.value}_{alert.level.value}"
        
        if key in self.alert_cooldowns:
            time_since_last = datetime.now() - self.alert_cooldowns[key]
            if time_since_last.total_seconds() < self.config.alert_cooldown_seconds:
                return False
        
        return True
    
    def _send_alert(self, alert: PerformanceAlert):
        """Send alert to registered callbacks"""
        self.alert_cooldowns[f"{alert.component}_{alert.metric_type.value}_{alert.level.value}"] = datetime.now()
        self.alert_history.append(alert)
        
        self.logger.warning(f"ALERT [{alert.level.value.upper()}] {alert.message}: "
                           f"{alert.current_value:.3f} (threshold: {alert.threshold:.3f})")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

class RealTimeMonitor:
    """
    Real-time performance monitor for the unified core engine.
    Provides continuous monitoring, alerting, and performance tracking.
    """
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Monitoring components
        self.metric_aggregator = MetricAggregator(self.config.metric_history_size)
        self.alert_manager = AlertManager(self.config)
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitored_components: Dict[str, Any] = {}
        
        # Performance tracking
        self.monitoring_start_time: Optional[datetime] = None
        self.total_metrics_collected = 0
        self.total_alerts_generated = 0
        
        self.logger.info(f"RealTimeMonitor initialized - Interval: {self.config.monitoring_interval_ms}ms")
    
    def register_component(self, name: str, component: Any):
        """Register a component for monitoring"""
        self.monitored_components[name] = component
        self.logger.info(f"Registered component for monitoring: {name}")
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Register callback for alert notifications"""
        self.alert_manager.register_alert_callback(callback)
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_monitoring:
            self.logger.warning("Monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitoring_start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        self.logger.info("Real-time monitoring stopped")
    
    def record_metric(self, component: str, metric_type: MetricType, value: float,
                     metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            component=component,
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
        
        self.metric_aggregator.add_metric(metric)
        self.total_metrics_collected += 1
        
        # Check for alerts
        alert = self.alert_manager.check_thresholds(metric)
        if alert:
            self.total_alerts_generated += 1
    
    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get current status for a specific component"""
        status = {
            'component': component_name,
            'is_registered': component_name in self.monitored_components,
            'metrics': {}
        }
        
        # Get statistics for each metric type
        for metric_type in MetricType:
            stats = self.metric_aggregator.calculate_statistics(component_name, metric_type, 60)
            if stats:
                status['metrics'][metric_type.value] = stats
        
        return status
    
    def get_overall_status(self) -> Dict[str, Any]:
        """Get overall monitoring status"""
        uptime = (datetime.now() - self.monitoring_start_time).total_seconds() if self.monitoring_start_time else 0
        
        return {
            'monitoring_active': self.is_monitoring,
            'uptime_seconds': uptime,
            'monitored_components': list(self.monitored_components.keys()),
            'total_metrics_collected': self.total_metrics_collected,
            'total_alerts_generated': self.total_alerts_generated,
            'metrics_per_second': self.total_metrics_collected / uptime if uptime > 0 else 0,
            'recent_alerts': list(self.alert_manager.alert_history)[-10:]  # Last 10 alerts
        }
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        self.logger.info("Starting monitoring loop")
        
        while self.is_monitoring:
            try:
                start_time = time.perf_counter()
                
                # Collect metrics from all registered components
                for component_name, component in self.monitored_components.items():
                    self._collect_component_metrics(component_name, component)
                
                # Calculate loop timing
                loop_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
                
                # Record monitoring overhead
                self.record_metric('monitor', MetricType.LATENCY, loop_time)
                
                # Sleep for remaining interval time
                sleep_time = max(0, (self.config.monitoring_interval_ms - loop_time) / 1000)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(1.0)  # Error recovery delay
    
    def _collect_component_metrics(self, component_name: str, component: Any):
        """Collect metrics from a specific component"""
        try:
            # Try to get performance metrics if component supports it
            if hasattr(component, 'get_performance_metrics'):
                metrics = component.get_performance_metrics()
                
                if isinstance(metrics, dict):
                    # Map common metric names to our types
                    metric_mappings = {
                        'average_latency_ms': MetricType.LATENCY,
                        'average_processing_time_ms': MetricType.LATENCY,
                        'latency_ms': MetricType.LATENCY,
                        'throughput_ops_per_second': MetricType.THROUGHPUT,
                        'ops_per_second': MetricType.THROUGHPUT,
                        'signals_per_second': MetricType.THROUGHPUT,
                        'validations_per_second': MetricType.THROUGHPUT,
                        'orders_per_second': MetricType.THROUGHPUT,
                        'error_rate': MetricType.ERROR_RATE,
                        'memory_usage_mb': MetricType.MEMORY_USAGE,
                        'cpu_usage': MetricType.CPU_USAGE
                    }
                    
                    for metric_name, value in metrics.items():
                        if metric_name in metric_mappings and isinstance(value, (int, float)):
                            self.record_metric(component_name, metric_mappings[metric_name], float(value))
            
            # Try to get current status if component supports it
            if hasattr(component, 'get_current_status'):
                status = component.get_current_status()
                if isinstance(status, dict):
                    # Extract any numeric metrics from status
                    for key, value in status.items():
                        if isinstance(value, (int, float)) and 'error' in key.lower():
                            # Assume error-related metrics are error rates
                            self.record_metric(component_name, MetricType.ERROR_RATE, float(value))
                
        except Exception as e:
            self.logger.debug(f"Failed to collect metrics from {component_name}: {e}")
            # Record collection failure as error rate
            self.record_metric(component_name, MetricType.ERROR_RATE, 1.0)
    
    def generate_performance_report(self, duration_seconds: int = 3600) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'duration_seconds': duration_seconds,
            'components': {}
        }
        
        for component_name in self.monitored_components.keys():
            component_report = {
                'metrics': {}
            }
            
            for metric_type in MetricType:
                stats = self.metric_aggregator.calculate_statistics(component_name, metric_type, duration_seconds)
                if stats:
                    component_report['metrics'][metric_type.value] = stats
            
            if component_report['metrics']:
                report['components'][component_name] = component_report
        
        return report
