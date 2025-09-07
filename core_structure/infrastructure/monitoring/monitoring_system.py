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
    # System metrics
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    
    # Trading metrics
    SHARPE_RATIO = "sharpe_ratio"
    DRAWDOWN = "drawdown"
    PNL = "pnl"
    
    # Enhanced metric types (from trade engine)
    COUNTER = "counter"          # Monotonically increasing
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Timing measurements
    BUSINESS = "business"        # Business metrics


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


class HealthStatus(Enum):
    """Component health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Component types for health monitoring"""
    SYSTEM = "system"
    DATABASE = "database"
    MARKET_DATA = "market_data"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    MONITORING = "monitoring"


# =============================================================================
# Enhanced Data Classes (from trade engine monitoring)
# =============================================================================

@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    component_type: ComponentType
    check_function: Callable[[], bool]
    interval_seconds: float = 60.0
    timeout_seconds: float = 10.0
    retry_count: int = 3
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: List[float]


@dataclass
class EnhancedMetric:
    """Enhanced metric with tags and metadata"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Statistical summary of metrics"""
    name: str
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    tags: Dict[str, str] = field(default_factory=dict)


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
    Enhanced centralized metrics collection system with real-time monitoring,
    alerting capabilities, and advanced features from trade engine monitoring.
    
    Features:
    - Multi-type metric support (counters, gauges, histograms, timers, business)
    - Tag-based metric organization
    - Real-time aggregation and statistics
    - Automatic metric retention and cleanup
    - Performance-optimized storage
    - Enhanced alerting with rule-based system
    """
    
    def __init__(self, config: MetricsConfig):
        self.config = config
        
        # Enhanced storage with tags and metadata
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._enhanced_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Enhanced features from trade engine
        self.metric_metadata: Dict[str, MetricType] = {}
        self.metric_tags: Dict[str, Dict[str, str]] = {}
        self.aggregated_metrics: Dict[str, MetricSummary] = {}
        self.aggregation_window = timedelta(minutes=1)
        
        # Registered metric sources
        self.metric_sources: Dict[str, Callable] = {}
        
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
    
    # Enhanced methods from trade engine monitoring
    def record_enhanced_metric(self, metric: EnhancedMetric) -> None:
        """Record an enhanced metric with tags and metadata"""
        self._enhanced_metrics[metric.name].append(metric)
        self.metric_metadata[metric.name] = metric.metric_type
        self.metric_tags[metric.name] = metric.tags
        
        # Also record in legacy format for compatibility
        self.record_metric(metric.name, metric.value, metric.tags)
    
    def record_business_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a business-specific metric"""
        enhanced_metric = EnhancedMetric(
            name=name,
            value=value,
            metric_type=MetricType.BUSINESS,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata={'category': 'business'}
        )
        self.record_enhanced_metric(enhanced_metric)
    
    def record_timer_metric(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric"""
        enhanced_metric = EnhancedMetric(
            name=name,
            value=duration_ms,
            metric_type=MetricType.TIMER,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata={'unit': 'milliseconds'}
        )
        self.record_enhanced_metric(enhanced_metric)
    
    def register_metric_source(self, name: str, source_func: Callable) -> None:
        """Register a metric source function"""
        self.metric_sources[name] = source_func
        logger.info(f"Registered metric source: {name}")
    
    def get_metric_summary(self, name: str, window_minutes: int = 5) -> Optional[MetricSummary]:
        """Get statistical summary for a metric"""
        if name not in self._enhanced_metrics:
            return None
        
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [
            m for m in self._enhanced_metrics[name] 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return None
        
        values = [m.value for m in recent_metrics]
        
        return MetricSummary(
            name=name,
            count=len(values),
            min_value=min(values),
            max_value=max(values),
            mean_value=statistics.mean(values),
            median_value=statistics.median(values) if values else 0.0,
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            percentile_95=np.percentile(values, 95) if len(values) > 0 else 0.0,
            percentile_99=np.percentile(values, 99) if len(values) > 0 else 0.0,
            tags=self.metric_tags.get(name, {})
        )
    
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
# Enhanced Health Monitoring System (from trade engine)
# =============================================================================

class EnhancedHealthMonitor:
    """
    Advanced health monitoring system with component tracking,
    dependency monitoring, and automated health checks.
    
    Features:
    - Component health tracking
    - Automated health checks
    - Dependency monitoring
    - System metrics collection
    - Health status aggregation
    - Alert integration
    """
    
    def __init__(self, check_interval: float = 60):
        self.check_interval = check_interval
        
        # Health check management
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_statuses: Dict[str, HealthStatus] = {}
        self.component_dependencies: Dict[str, set] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_lock = threading.RLock()
        
        # System metrics
        self.system_metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1440  # 24 hours of minute-by-minute data
        
        # Health statistics
        self.health_stats = {
            'total_components': 0,
            'healthy_components': 0,
            'warning_components': 0,
            'unhealthy_components': 0,
            'critical_components': 0,
            'unknown_components': 0
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, HealthStatus, str], None]] = []
        
        logger.info("EnhancedHealthMonitor initialized")
    
    def register_health_check(self, health_check: HealthCheck) -> None:
        """Register a health check"""
        self.health_checks[health_check.name] = health_check
        self.health_statuses[health_check.name] = HealthStatus.UNKNOWN
        logger.info(f"Registered health check: {health_check.name}")
    
    def add_component_dependency(self, component: str, depends_on: str) -> None:
        """Add a component dependency"""
        if component not in self.component_dependencies:
            self.component_dependencies[component] = set()
        self.component_dependencies[component].add(depends_on)
        logger.info(f"Added dependency: {component} depends on {depends_on}")
    
    async def start_monitoring(self):
        """Start health monitoring"""
        if self.is_monitoring:
            logger.warning("Health monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Setup default system health checks
        self._setup_system_health_checks()
        
        logger.info("Enhanced health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Enhanced health monitoring stopped")
    
    def _setup_system_health_checks(self):
        """Setup default system health checks"""
        # CPU health check
        cpu_check = HealthCheck(
            name="system_cpu",
            component_type=ComponentType.SYSTEM,
            check_function=self._check_cpu_health,
            interval_seconds=30.0,
            tags={'category': 'system', 'resource': 'cpu'}
        )
        self.register_health_check(cpu_check)
        
        # Memory health check
        memory_check = HealthCheck(
            name="system_memory",
            component_type=ComponentType.SYSTEM,
            check_function=self._check_memory_health,
            interval_seconds=30.0,
            tags={'category': 'system', 'resource': 'memory'}
        )
        self.register_health_check(memory_check)
    
    def _check_cpu_health(self) -> bool:
        """Check CPU health"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 90.0  # Healthy if CPU < 90%
        except Exception:
            return False
    
    def _check_memory_health(self) -> bool:
        """Check memory health"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 85.0  # Healthy if memory < 85%
        except Exception:
            return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._run_health_checks()
                await self._collect_system_metrics()
                await self._update_health_statistics()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        for name, health_check in self.health_checks.items():
            try:
                is_healthy = health_check.check_function()
                new_status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY
                
                # Check if status changed
                if self.health_statuses.get(name) != new_status:
                    self.health_statuses[name] = new_status
                    await self._notify_status_change(name, new_status)
                    
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                self.health_statuses[name] = HealthStatus.CRITICAL
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            import psutil
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=psutil.cpu_percent(),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=psutil.disk_usage('/').percent,
                network_bytes_sent=psutil.net_io_counters().bytes_sent,
                network_bytes_recv=psutil.net_io_counters().bytes_recv,
                load_average=list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
            )
            
            self.system_metrics_history.append(metrics)
            
            # Maintain history size
            if len(self.system_metrics_history) > self.max_history_size:
                self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]
                
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def _update_health_statistics(self):
        """Update health statistics"""
        self.health_stats = {
            'total_components': len(self.health_statuses),
            'healthy_components': sum(1 for s in self.health_statuses.values() if s == HealthStatus.HEALTHY),
            'warning_components': sum(1 for s in self.health_statuses.values() if s == HealthStatus.WARNING),
            'unhealthy_components': sum(1 for s in self.health_statuses.values() if s == HealthStatus.UNHEALTHY),
            'critical_components': sum(1 for s in self.health_statuses.values() if s == HealthStatus.CRITICAL),
            'unknown_components': sum(1 for s in self.health_statuses.values() if s == HealthStatus.UNKNOWN)
        }
    
    async def _notify_status_change(self, component: str, status: HealthStatus):
        """Notify about status changes"""
        message = f"Component {component} status changed to {status.value}"
        
        for callback in self.alert_callbacks:
            try:
                callback(component, status, message)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        return {
            'overall_status': self._calculate_overall_status(),
            'component_statuses': dict(self.health_statuses),
            'statistics': dict(self.health_stats),
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health status"""
        if self.health_stats['critical_components'] > 0:
            return HealthStatus.CRITICAL
        elif self.health_stats['unhealthy_components'] > 0:
            return HealthStatus.UNHEALTHY
        elif self.health_stats['warning_components'] > 0:
            return HealthStatus.WARNING
        elif self.health_stats['healthy_components'] > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


# =============================================================================
# Monitoring System Factory
# =============================================================================

class MonitoringSystemFactory:
    """Factory for creating monitoring system components"""
    
    @staticmethod
    def create_production_monitoring_system() -> Tuple[MetricsCollector, RealTimeMonitor, PerformanceDashboard, EnhancedHealthMonitor]:
        """Create enhanced monitoring system for production environment"""
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
        health_monitor = EnhancedHealthMonitor(check_interval=30.0)  # Production: 30s checks
        
        return metrics_collector, monitor, dashboard, health_monitor
    
    @staticmethod
    def create_development_monitoring_system() -> Tuple[MetricsCollector, RealTimeMonitor, PerformanceDashboard, EnhancedHealthMonitor]:
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
        health_monitor = EnhancedHealthMonitor(check_interval=60.0)  # Development: 60s checks
        
        return metrics_collector, monitor, dashboard, health_monitor


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    'MetricType',
    'AlertLevel',
    'DashboardMode',
    'MonitoringStatus',
    'HealthStatus',
    'ComponentType',
    
    # Configuration classes
    'MonitorConfig',
    'DashboardConfig',
    'MetricsConfig',
    
    # Data classes
    'MetricValue',
    'PerformanceAlert',
    'DashboardMetric',
    'SystemHealth',
    'HealthCheck',
    'SystemMetrics',
    'EnhancedMetric',
    'MetricSummary',
    
    # Core systems
    'MetricsCollector',
    'RealTimeMonitor',
    'PerformanceDashboard',
    'EnhancedHealthMonitor',
    
    # Factory
    'MonitoringSystemFactory'
]
