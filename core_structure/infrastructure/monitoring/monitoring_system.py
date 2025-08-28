"""
Monitoring System for StatArb Trading System
============================================

Phase 5B Infrastructure Consolidation - Monitoring Module
Consolidates monitoring functionality into a unified system.

Consolidated from:
- performance_dashboard.py (494 lines) - Performance visualization and reporting
- real_time_monitor.py (453 lines) - Real-time system monitoring
- metrics_collector.py (289 lines) - System metrics collection

This module provides comprehensive monitoring capabilities including:
- Real-time performance monitoring with alerting
- Performance dashboard with visualization
- Centralized metrics collection and aggregation
- Alert management and notification systems
"""

import asyncio
import logging
import time
import threading
import json
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue
import statistics
import numpy as np

logger = logging.getLogger(__name__)

# =============================================================================
# Core Monitoring Enums and Types
# =============================================================================

class MetricType(Enum):
    """Types of metrics to monitor"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    SHARPE_RATIO = "sharpe_ratio"
    DRAWDOWN = "drawdown"
    PNL = "pnl"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DashboardMode(Enum):
    """Dashboard display modes"""
    OVERVIEW = "overview"
    DETAILED = "detailed"
    OPTIMIZATION = "optimization"
    ALERTS = "alerts"


class MonitoringStatus(Enum):
    """Status of monitoring system"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# =============================================================================
# Configuration Classes
# =============================================================================

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
    enable_alerting: bool = True
    alert_cooldown_seconds: int = 300  # 5 minutes
    escalation_threshold: int = 3  # Escalate after 3 consecutive alerts
    
    # Data retention
    metrics_retention_hours: int = 24
    detailed_metrics_retention_hours: int = 6


@dataclass
class DashboardConfig:
    """Configuration for performance dashboard"""
    # Display settings
    refresh_interval_seconds: int = 5
    history_duration_minutes: int = 60
    max_alerts_displayed: int = 20
    
    # Visualization settings
    enable_real_time_charts: bool = True
    enable_performance_trends: bool = True
    enable_optimization_tracking: bool = True
    
    # Export settings
    enable_data_export: bool = True
    export_format: str = "json"  # json, csv, html
    export_directory: str = "exports"
    
    # Dashboard themes
    theme: str = "dark"  # dark, light, auto
    chart_colors: List[str] = field(default_factory=lambda: ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"])


@dataclass
class MetricsConfig:
    """Configuration for metrics collection"""
    # Collection settings
    collection_interval_ms: int = 1000
    buffer_size: int = 10000
    batch_size: int = 100
    
    # Aggregation settings
    aggregation_interval_minutes: int = 1
    retention_days: int = 30
    compression_threshold_hours: int = 24
    
    # Performance settings
    async_processing: bool = True
    max_queue_size: int = 50000
    processing_threads: int = 2


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class MetricValue:
    """Represents a single metric measurement"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'tags': self.tags
        }


@dataclass
class PerformanceAlert:
    """Represents a performance alert"""
    alert_id: str
    metric_name: str
    alert_level: AlertLevel
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'metric_name': self.metric_name,
            'alert_level': self.alert_level.value,
            'message': self.message,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }


@dataclass
class DashboardMetric:
    """Dashboard metric representation"""
    name: str
    current_value: float
    historical_values: List[float]
    unit: str = ""
    format_string: str = "{:.2f}"
    threshold: Optional[float] = None
    alert_level: Optional[AlertLevel] = None
    
    def get_trend(self) -> str:
        """Get trend direction"""
        if len(self.historical_values) < 2:
            return "stable"
        
        recent = statistics.mean(self.historical_values[-5:])
        older = statistics.mean(self.historical_values[-10:-5]) if len(self.historical_values) >= 10 else recent
        
        if recent > older * 1.05:
            return "up"
        elif recent < older * 0.95:
            return "down"
        else:
            return "stable"
    
    def get_formatted_value(self) -> str:
        """Get formatted current value"""
        return self.format_string.format(self.current_value) + " " + self.unit


@dataclass
class SystemHealth:
    """Overall system health summary"""
    overall_status: str
    component_statuses: Dict[str, str]
    active_alerts: List[PerformanceAlert]
    performance_score: float
    last_updated: datetime
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return (self.overall_status == "healthy" and 
                self.performance_score > 0.8 and
                len([a for a in self.active_alerts if a.alert_level in [AlertLevel.ERROR, AlertLevel.CRITICAL]]) == 0)


# =============================================================================
# Metrics Collector System
# =============================================================================

class MetricsCollector:
    """
    Centralized metrics collection system with real-time monitoring
    and alerting capabilities
    """
    
    def __init__(self, config: MetricsConfig):
        self.config = config
        
        # Storage
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Alert system
        self._alert_thresholds: Dict[str, Dict[str, float]] = {}
        self._alert_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Performance tracking
        self._latency_percentiles = [50, 90, 95, 99]
        
        # Metric aggregation
        self._last_aggregation = datetime.now()
        
        # Background processing
        self._metric_queue = Queue(maxsize=self.config.max_queue_size)
        self._processing_threads: List[threading.Thread] = []
        self._stop_processing = threading.Event()
        
        # Start processing if async enabled
        if self.config.async_processing:
            self._start_processing_threads()
        
        logger.info("MetricsCollector initialized")
    
    def _start_processing_threads(self) -> None:
        """Start background metric processing threads"""
        for i in range(self.config.processing_threads):
            thread = threading.Thread(
                target=self._process_metrics,
                name=f"MetricsProcessor-{i}",
                daemon=True
            )
            thread.start()
            self._processing_threads.append(thread)
    
    def _process_metrics(self) -> None:
        """Background metric processing loop"""
        while not self._stop_processing.is_set():
            try:
                # Process metrics in batches
                batch = []
                for _ in range(self.config.batch_size):
                    try:
                        metric = self._metric_queue.get(timeout=1.0)
                        batch.append(metric)
                    except:
                        break
                
                if batch:
                    self._process_metric_batch(batch)
                
            except Exception as e:
                logger.error(f"Error in metric processing: {e}")
    
    def _process_metric_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Process a batch of metrics"""
        for metric_data in batch:
            metric_name = metric_data['name']
            metric_value = MetricValue(
                timestamp=metric_data['timestamp'],
                value=metric_data['value'],
                tags=metric_data.get('tags', {})
            )
            
            # Store metric
            self._metrics[metric_name].append(metric_value)
            
            # Maintain buffer size
            if len(self._metrics[metric_name]) > self.config.buffer_size:
                self._metrics[metric_name] = self._metrics[metric_name][-self.config.buffer_size:]
            
            # Check alerts
            self._check_metric_alerts(metric_name, metric_value)
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value"""
        metric_data = {
            'name': name,
            'value': value,
            'timestamp': datetime.now(),
            'tags': tags or {}
        }
        
        if self.config.async_processing:
            try:
                self._metric_queue.put_nowait(metric_data)
            except:
                logger.warning(f"Metric queue full, dropping metric: {name}")
        else:
            self._process_metric_batch([metric_data])
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter metric"""
        self._counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value"""
        self._gauges[name] = value
        self.record_metric(name, value, {'type': 'gauge'})
    
    def record_histogram(self, name: str, value: float) -> None:
        """Record a histogram value"""
        self._histograms[name].append(value)
        
        # Maintain histogram size
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]
        
        self.record_metric(name, value, {'type': 'histogram'})
    
    def get_metric_history(self, name: str, duration_minutes: int = 60) -> List[MetricValue]:
        """Get metric history for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        if name in self._metrics:
            return [m for m in self._metrics[name] if m.timestamp >= cutoff_time]
        return []
    
    def get_histogram_percentiles(self, name: str) -> Dict[str, float]:
        """Get histogram percentiles"""
        if name not in self._histograms or not self._histograms[name]:
            return {}
        
        values = self._histograms[name]
        return {
            f"p{p}": np.percentile(values, p) for p in self._latency_percentiles
        }
    
    def set_alert_threshold(self, metric_name: str, threshold_type: str, value: float) -> None:
        """Set alert threshold for a metric"""
        if metric_name not in self._alert_thresholds:
            self._alert_thresholds[metric_name] = {}
        self._alert_thresholds[metric_name][threshold_type] = value
    
    def add_alert_callback(self, metric_name: str, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add alert callback for a metric"""
        self._alert_callbacks[metric_name].append(callback)
    
    def _check_metric_alerts(self, metric_name: str, metric_value: MetricValue) -> None:
        """Check if metric value triggers any alerts"""
        if metric_name not in self._alert_thresholds:
            return
        
        thresholds = self._alert_thresholds[metric_name]
        
        for threshold_type, threshold_value in thresholds.items():
            alert_triggered = False
            alert_level = AlertLevel.WARNING
            
            if threshold_type == "max" and metric_value.value > threshold_value:
                alert_triggered = True
                alert_level = AlertLevel.ERROR if metric_value.value > threshold_value * 1.5 else AlertLevel.WARNING
            elif threshold_type == "min" and metric_value.value < threshold_value:
                alert_triggered = True
                alert_level = AlertLevel.ERROR if metric_value.value < threshold_value * 0.5 else AlertLevel.WARNING
            
            if alert_triggered:
                alert = PerformanceAlert(
                    alert_id=f"{metric_name}_{threshold_type}_{int(time.time())}",
                    metric_name=metric_name,
                    alert_level=alert_level,
                    message=f"{metric_name} {threshold_type} threshold exceeded: {metric_value.value:.2f} vs {threshold_value:.2f}",
                    current_value=metric_value.value,
                    threshold_value=threshold_value,
                    timestamp=metric_value.timestamp,
                    tags=metric_value.tags
                )
                
                self._active_alerts[alert.alert_id] = alert
                
                # Call alert callbacks
                for callback in self._alert_callbacks[metric_name]:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active alerts"""
        return list(self._active_alerts.values())
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].acknowledged = True
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].resolved = True
            return True
        return False


# =============================================================================
# Real-Time Monitor System
# =============================================================================

class RealTimeMonitor:
    """
    Real-time performance monitoring system with alerting
    """
    
    def __init__(self, config: MonitorConfig, metrics_collector: MetricsCollector):
        self.config = config
        self.metrics_collector = metrics_collector
        
        # State tracking
        self.status = MonitoringStatus.STOPPED
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Performance tracking
        self.component_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.metric_history_size))
        self.alert_history: List[PerformanceAlert] = []
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Callbacks
        self.metric_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Set up default alert thresholds
        self._setup_default_thresholds()
        
        logger.info("RealTimeMonitor initialized")
    
    def _setup_default_thresholds(self) -> None:
        """Set up default alert thresholds"""
        self.metrics_collector.set_alert_threshold("latency_ms", "max", self.config.max_latency_ms)
        self.metrics_collector.set_alert_threshold("throughput", "min", self.config.min_throughput)
        self.metrics_collector.set_alert_threshold("error_rate", "max", self.config.max_error_rate)
        self.metrics_collector.set_alert_threshold("memory_usage_mb", "max", self.config.max_memory_usage_mb)
        self.metrics_collector.set_alert_threshold("cpu_usage", "max", self.config.max_cpu_usage)
    
    def start_monitoring(self) -> None:
        """Start real-time monitoring"""
        if self.status == MonitoringStatus.RUNNING:
            logger.warning("Monitoring already running")
            return
        
        self.status = MonitoringStatus.STARTING
        self._stop_monitoring.clear()
        
        # Start monitoring thread
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        self.status = MonitoringStatus.RUNNING
        logger.info("Started real-time monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop real-time monitoring"""
        self.status = MonitoringStatus.STOPPING
        self._stop_monitoring.set()
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        
        self.status = MonitoringStatus.STOPPED
        logger.info("Stopped real-time monitoring")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while not self._stop_monitoring.is_set() and self.status == MonitoringStatus.RUNNING:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Check for alerts
                self._process_alerts()
                
                # Sleep for monitoring interval
                time.sleep(self.config.monitoring_interval_ms / 1000.0)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.status = MonitoringStatus.ERROR
                break
    
    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        import psutil
        
        # CPU usage
        cpu_usage = psutil.cpu_percent()
        self.metrics_collector.set_gauge("cpu_usage", cpu_usage)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage_mb = memory.used / (1024 * 1024)
        self.metrics_collector.set_gauge("memory_usage_mb", memory_usage_mb)
        self.metrics_collector.set_gauge("memory_usage_percent", memory.percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage_percent = disk.percent
        self.metrics_collector.set_gauge("disk_usage_percent", disk_usage_percent)
        
        # Network I/O
        network = psutil.net_io_counters()
        self.metrics_collector.set_gauge("network_bytes_sent", network.bytes_sent)
        self.metrics_collector.set_gauge("network_bytes_recv", network.bytes_recv)
    
    def _process_alerts(self) -> None:
        """Process and handle alerts"""
        active_alerts = self.metrics_collector.get_active_alerts()
        
        for alert in active_alerts:
            if not alert.acknowledged and self._should_send_alert(alert):
                self._send_alert(alert)
                self.last_alert_times[alert.metric_name] = alert.timestamp
    
    def _should_send_alert(self, alert: PerformanceAlert) -> bool:
        """Check if alert should be sent (considering cooldown)"""
        if alert.metric_name in self.last_alert_times:
            time_since_last = datetime.now() - self.last_alert_times[alert.metric_name]
            if time_since_last.total_seconds() < self.config.alert_cooldown_seconds:
                return False
        return True
    
    def _send_alert(self, alert: PerformanceAlert) -> None:
        """Send alert to all registered callbacks"""
        self.alert_history.append(alert)
        
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        logger.warning(f"ALERT: {alert.message}")
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_system_health(self) -> SystemHealth:
        """Get overall system health status"""
        active_alerts = self.metrics_collector.get_active_alerts()
        unresolved_alerts = [a for a in active_alerts if not a.resolved]
        
        # Calculate performance score
        performance_score = self._calculate_performance_score()
        
        # Determine overall status
        critical_alerts = [a for a in unresolved_alerts if a.alert_level == AlertLevel.CRITICAL]
        error_alerts = [a for a in unresolved_alerts if a.alert_level == AlertLevel.ERROR]
        
        if critical_alerts:
            overall_status = "critical"
        elif error_alerts:
            overall_status = "degraded"
        elif unresolved_alerts:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        # Component statuses
        component_statuses = {
            "cpu": "healthy" if self.metrics_collector._gauges.get("cpu_usage", 0) < 80 else "warning",
            "memory": "healthy" if self.metrics_collector._gauges.get("memory_usage_percent", 0) < 85 else "warning",
            "disk": "healthy" if self.metrics_collector._gauges.get("disk_usage_percent", 0) < 90 else "warning",
            "network": "healthy"  # Simplified
        }
        
        return SystemHealth(
            overall_status=overall_status,
            component_statuses=component_statuses,
            active_alerts=unresolved_alerts,
            performance_score=performance_score,
            last_updated=datetime.now()
        )
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-1)"""
        score = 1.0
        
        # CPU score
        cpu_usage = self.metrics_collector._gauges.get("cpu_usage", 0)
        cpu_score = max(0, 1 - cpu_usage / 100)
        score *= cpu_score
        
        # Memory score
        memory_usage = self.metrics_collector._gauges.get("memory_usage_percent", 0)
        memory_score = max(0, 1 - memory_usage / 100)
        score *= memory_score
        
        # Error rate score
        error_rate = self.metrics_collector._gauges.get("error_rate", 0)
        error_score = max(0, 1 - error_rate / 0.1)  # 10% error rate = 0 score
        score *= error_score
        
        return score


# =============================================================================
# Performance Dashboard System
# =============================================================================

class PerformanceDashboard:
    """
    Performance dashboard for visualizing and reporting system metrics
    """
    
    def __init__(self, config: DashboardConfig, metrics_collector: MetricsCollector, monitor: RealTimeMonitor):
        self.config = config
        self.metrics_collector = metrics_collector
        self.monitor = monitor
        
        # Dashboard state
        self.current_mode = DashboardMode.OVERVIEW
        self.dashboard_metrics: Dict[str, DashboardMetric] = {}
        self.last_refresh = datetime.now()
        
        # Initialize dashboard metrics
        self._initialize_dashboard_metrics()
        
        logger.info("PerformanceDashboard initialized")
    
    def _initialize_dashboard_metrics(self) -> None:
        """Initialize dashboard metrics"""
        self.dashboard_metrics = {
            "latency": DashboardMetric(
                name="Latency",
                current_value=0.0,
                historical_values=[],
                unit="ms",
                format_string="{:.2f}",
                threshold=self.config.max_latency_ms if hasattr(self.config, 'max_latency_ms') else 5.0
            ),
            "throughput": DashboardMetric(
                name="Throughput",
                current_value=0.0,
                historical_values=[],
                unit="ops/sec",
                format_string="{:.0f}"
            ),
            "error_rate": DashboardMetric(
                name="Error Rate",
                current_value=0.0,
                historical_values=[],
                unit="%",
                format_string="{:.2%}",
                threshold=0.01
            ),
            "cpu_usage": DashboardMetric(
                name="CPU Usage",
                current_value=0.0,
                historical_values=[],
                unit="%",
                format_string="{:.1f}",
                threshold=80.0
            ),
            "memory_usage": DashboardMetric(
                name="Memory Usage",
                current_value=0.0,
                historical_values=[],
                unit="%",
                format_string="{:.1f}",
                threshold=85.0
            )
        }
    
    def refresh_dashboard(self) -> Dict[str, Any]:
        """Refresh dashboard data"""
        self.last_refresh = datetime.now()
        
        # Update dashboard metrics
        self._update_dashboard_metrics()
        
        # Get system health
        system_health = self.monitor.get_system_health()
        
        # Get active alerts
        active_alerts = self.metrics_collector.get_active_alerts()
        recent_alerts = [a for a in active_alerts if not a.acknowledged][:self.config.max_alerts_displayed]
        
        dashboard_data = {
            "timestamp": self.last_refresh.isoformat(),
            "mode": self.current_mode.value,
            "system_health": {
                "overall_status": system_health.overall_status,
                "performance_score": system_health.performance_score,
                "component_statuses": system_health.component_statuses
            },
            "metrics": {
                name: {
                    "current_value": metric.current_value,
                    "formatted_value": metric.get_formatted_value(),
                    "trend": metric.get_trend(),
                    "alert_level": metric.alert_level.value if metric.alert_level else None
                }
                for name, metric in self.dashboard_metrics.items()
            },
            "alerts": [alert.to_dict() for alert in recent_alerts],
            "charts": self._generate_chart_data() if self.config.enable_real_time_charts else {}
        }
        
        return dashboard_data
    
    def _update_dashboard_metrics(self) -> None:
        """Update dashboard metrics with latest values"""
        # Update from metrics collector
        for metric_name, dashboard_metric in self.dashboard_metrics.items():
            # Get latest value from gauges
            if metric_name == "cpu_usage":
                current_value = self.metrics_collector._gauges.get("cpu_usage", 0.0)
            elif metric_name == "memory_usage":
                current_value = self.metrics_collector._gauges.get("memory_usage_percent", 0.0)
            elif metric_name == "error_rate":
                current_value = self.metrics_collector._gauges.get("error_rate", 0.0)
            elif metric_name == "latency":
                current_value = self.metrics_collector._gauges.get("latency_ms", 0.0)
            elif metric_name == "throughput":
                current_value = self.metrics_collector._gauges.get("throughput", 0.0)
            else:
                current_value = 0.0
            
            # Update dashboard metric
            dashboard_metric.current_value = current_value
            dashboard_metric.historical_values.append(current_value)
            
            # Maintain history size
            max_history = 1000
            if len(dashboard_metric.historical_values) > max_history:
                dashboard_metric.historical_values = dashboard_metric.historical_values[-max_history:]
            
            # Check alert level
            if dashboard_metric.threshold and current_value > dashboard_metric.threshold:
                dashboard_metric.alert_level = AlertLevel.WARNING
            else:
                dashboard_metric.alert_level = None
    
    def _generate_chart_data(self) -> Dict[str, Any]:
        """Generate chart data for visualization"""
        charts = {}
        
        for metric_name, metric in self.dashboard_metrics.items():
            if len(metric.historical_values) > 1:
                # Get time points
                now = datetime.now()
                time_points = [
                    (now - timedelta(minutes=i)).isoformat()
                    for i in range(len(metric.historical_values) - 1, -1, -1)
                ]
                
                charts[metric_name] = {
                    "labels": time_points,
                    "data": list(metric.historical_values),
                    "unit": metric.unit,
                    "color": self.config.chart_colors[hash(metric_name) % len(self.config.chart_colors)]
                }
        
        return charts
    
    def export_data(self, format_type: Optional[str] = None) -> str:
        """Export dashboard data"""
        if not self.config.enable_data_export:
            raise ValueError("Data export is disabled")
        
        format_type = format_type or self.config.export_format
        dashboard_data = self.refresh_dashboard()
        
        if format_type == "json":
            return json.dumps(dashboard_data, indent=2)
        elif format_type == "csv":
            return self._export_csv(dashboard_data)
        elif format_type == "html":
            return self._export_html(dashboard_data)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_csv(self, data: Dict[str, Any]) -> str:
        """Export data as CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Metric', 'Current Value', 'Unit', 'Trend', 'Alert Level'])
        
        # Write metrics
        for metric_name, metric_data in data['metrics'].items():
            writer.writerow([
                metric_name,
                metric_data['current_value'],
                self.dashboard_metrics[metric_name].unit,
                metric_data['trend'],
                metric_data['alert_level'] or 'None'
            ])
        
        return output.getvalue()
    
    def _export_html(self, data: Dict[str, Any]) -> str:
        """Export data as HTML"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Dashboard - {data['timestamp']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .alert {{ color: red; }}
                .warning {{ color: orange; }}
                .healthy {{ color: green; }}
            </style>
        </head>
        <body>
            <h1>Performance Dashboard</h1>
            <p>Generated: {data['timestamp']}</p>
            
            <h2>System Health</h2>
            <p>Status: <span class="{data['system_health']['overall_status']}">{data['system_health']['overall_status']}</span></p>
            <p>Performance Score: {data['system_health']['performance_score']:.2f}</p>
            
            <h2>Metrics</h2>
        """
        
        for metric_name, metric_data in data['metrics'].items():
            alert_class = metric_data['alert_level'] or 'healthy'
            html += f"""
            <div class="metric">
                <strong>{metric_name}:</strong> 
                <span class="{alert_class}">{metric_data['formatted_value']}</span>
                <em>({metric_data['trend']})</em>
            </div>
            """
        
        html += """
            </body>
            </html>
        """
        
        return html
    
    def set_mode(self, mode: DashboardMode) -> None:
        """Set dashboard display mode"""
        self.current_mode = mode
        logger.info(f"Dashboard mode set to: {mode.value}")


# =============================================================================
# Monitoring System Factory
# =============================================================================

class MonitoringSystemFactory:
    """Factory for creating monitoring system components"""
    
    @staticmethod
    def create_production_monitoring_system() -> Tuple[MetricsCollector, RealTimeMonitor, PerformanceDashboard]:
        """Create monitoring system for production environment"""
        # Production metrics config
        metrics_config = MetricsConfig(
            collection_interval_ms=1000,
            buffer_size=50000,
            batch_size=500,
            aggregation_interval_minutes=1,
            retention_days=30,
            async_processing=True,
            max_queue_size=100000,
            processing_threads=4
        )
        
        # Production monitor config
        monitor_config = MonitorConfig(
            monitoring_interval_ms=500,
            metric_history_size=2000,
            max_latency_ms=2.0,
            min_throughput=5000.0,
            max_error_rate=0.005,
            max_memory_usage_mb=2048.0,
            max_cpu_usage=0.75,
            enable_alerting=True,
            alert_cooldown_seconds=300
        )
        
        # Production dashboard config
        dashboard_config = DashboardConfig(
            refresh_interval_seconds=2,
            history_duration_minutes=120,
            max_alerts_displayed=50,
            enable_real_time_charts=True,
            enable_performance_trends=True,
            enable_data_export=True,
            export_format="json"
        )
        
        # Create components
        metrics_collector = MetricsCollector(metrics_config)
        monitor = RealTimeMonitor(monitor_config, metrics_collector)
        dashboard = PerformanceDashboard(dashboard_config, metrics_collector, monitor)
        
        return metrics_collector, monitor, dashboard
    
    @staticmethod
    def create_development_monitoring_system() -> Tuple[MetricsCollector, RealTimeMonitor, PerformanceDashboard]:
        """Create monitoring system for development environment"""
        # Development metrics config
        metrics_config = MetricsConfig(
            collection_interval_ms=2000,
            buffer_size=10000,
            batch_size=100,
            aggregation_interval_minutes=5,
            retention_days=7,
            async_processing=True,
            processing_threads=2
        )
        
        # Development monitor config
        monitor_config = MonitorConfig(
            monitoring_interval_ms=1000,
            metric_history_size=500,
            max_latency_ms=10.0,
            min_throughput=100.0,
            max_error_rate=0.05,
            enable_alerting=False
        )
        
        # Development dashboard config
        dashboard_config = DashboardConfig(
            refresh_interval_seconds=10,
            history_duration_minutes=60,
            enable_real_time_charts=False,
            enable_data_export=False
        )
        
        # Create components
        metrics_collector = MetricsCollector(metrics_config)
        monitor = RealTimeMonitor(monitor_config, metrics_collector)
        dashboard = PerformanceDashboard(dashboard_config, metrics_collector, monitor)
        
        return metrics_collector, monitor, dashboard


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    'MetricType',
    'AlertLevel',
    'DashboardMode',
    'MonitoringStatus',
    
    # Configuration classes
    'MonitorConfig',
    'DashboardConfig',
    'MetricsConfig',
    
    # Data classes
    'MetricValue',
    'PerformanceAlert',
    'DashboardMetric',
    'SystemHealth',
    
    # Core systems
    'MetricsCollector',
    'RealTimeMonitor',
    'PerformanceDashboard',
    
    # Factory
    'MonitoringSystemFactory'
]
