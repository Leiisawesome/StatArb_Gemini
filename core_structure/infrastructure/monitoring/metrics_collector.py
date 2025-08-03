"""
Metrics collection system with performance monitoring and alerting capabilities
"""
from typing import Dict, List, Optional, Union, Any
import logging
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from queue import Queue
import json

logger = logging.getLogger(__name__)

@dataclass
class MetricValue:
    """Represents a single metric measurement"""
    timestamp: datetime
    value: float
    tags: Dict[str, str]

class MetricsCollector:
    """
    Centralized metrics collection system with real-time monitoring
    and alerting capabilities
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[MetricValue]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._alert_thresholds: Dict[str, Dict[str, float]] = {}
        self._alert_callbacks: Dict[str, List[callable]] = defaultdict(list)
        
        # Performance tracking
        self._latency_buffer_size = 1000
        self._latency_percentiles = [50, 90, 95, 99]
        
        # Metric aggregation
        self._aggregation_interval = timedelta(minutes=1)
        self._last_aggregation = datetime.now()
        
        # Background processing
        self._metric_queue = Queue()
        self._processing_thread = threading.Thread(
            target=self._process_metrics,
            daemon=True
        )
        self._processing_thread.start()
    
    def record_latency(self, metric_name: str, value_ms: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a latency measurement
        
        Args:
            metric_name: Name of the metric
            value_ms: Latency value in milliseconds
            tags: Optional tags for metric categorization
        """
        self._metric_queue.put({
            'type': 'latency',
            'name': metric_name,
            'value': value_ms,
            'tags': tags or {},
            'timestamp': datetime.now()
        })
    
    def increment_counter(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric
        
        Args:
            metric_name: Name of the counter
            value: Value to increment by
            tags: Optional tags for metric categorization
        """
        self._metric_queue.put({
            'type': 'counter',
            'name': metric_name,
            'value': value,
            'tags': tags or {},
            'timestamp': datetime.now()
        })
    
    def set_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric value
        
        Args:
            metric_name: Name of the gauge
            value: Current value
            tags: Optional tags for metric categorization
        """
        self._metric_queue.put({
            'type': 'gauge',
            'name': metric_name,
            'value': value,
            'tags': tags or {},
            'timestamp': datetime.now()
        })
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a generic metric value
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for metric categorization
        """
        self._metric_queue.put({
            'type': 'metric',
            'name': metric_name,
            'value': value,
            'tags': tags or {},
            'timestamp': datetime.now()
        })
    
    def set_alert_threshold(
        self,
        metric_name: str,
        warning_threshold: float,
        critical_threshold: float,
        callback: Optional[callable] = None
    ):
        """
        Set alert thresholds for a metric
        
        Args:
            metric_name: Name of the metric to monitor
            warning_threshold: Threshold for warning alerts
            critical_threshold: Threshold for critical alerts
            callback: Optional callback function for alert notifications
        """
        self._alert_thresholds[metric_name] = {
            'warning': warning_threshold,
            'critical': critical_threshold
        }
        
        if callback:
            self._alert_callbacks[metric_name].append(callback)
    
    def get_metric_statistics(
        self,
        metric_name: str,
        time_window: timedelta = timedelta(minutes=5),
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        Get statistical summary of a metric
        
        Args:
            metric_name: Name of the metric
            time_window: Time window for statistics calculation
            tags: Optional tags to filter metrics
            
        Returns:
            Dict containing metric statistics
        """
        cutoff_time = datetime.now() - time_window
        relevant_metrics = [
            m.value for m in self._metrics[metric_name]
            if m.timestamp >= cutoff_time
            and (not tags or all(m.tags.get(k) == v for k, v in tags.items()))
        ]
        
        if not relevant_metrics:
            return {}
        
        return {
            'count': len(relevant_metrics),
            'mean': np.mean(relevant_metrics),
            'std': np.std(relevant_metrics),
            'min': np.min(relevant_metrics),
            'max': np.max(relevant_metrics),
            **{
                f'p{p}': np.percentile(relevant_metrics, p)
                for p in self._latency_percentiles
            }
        }
    
    def _process_metrics(self):
        """Background thread for processing metrics"""
        while True:
            try:
                metric = self._metric_queue.get()
                self._handle_metric(metric)
                self._check_alerts(metric)
                self._aggregate_metrics()
            except Exception as e:
                logger.error(f"Error processing metric: {str(e)}")
    
    def _handle_metric(self, metric: Dict):
        """Process a single metric"""
        metric_value = MetricValue(
            timestamp=metric['timestamp'],
            value=metric['value'],
            tags=metric['tags']
        )
        
        if metric['type'] == 'latency':
            self._metrics[metric['name']].append(metric_value)
            # Maintain buffer size
            if len(self._metrics[metric['name']]) > self._latency_buffer_size:
                self._metrics[metric['name']].pop(0)
        
        elif metric['type'] == 'counter':
            self._counters[metric['name']] += metric['value']
            self._metrics[metric['name']].append(metric_value)
        
        elif metric['type'] == 'gauge':
            self._gauges[metric['name']] = metric['value']
            self._metrics[metric['name']] = [metric_value]
    
    def _check_alerts(self, metric: Dict):
        """Check if metric triggers any alerts"""
        metric_name = metric['name']
        if metric_name not in self._alert_thresholds:
            return
        
        thresholds = self._alert_thresholds[metric_name]
        value = metric['value']
        
        if value >= thresholds['critical']:
            self._trigger_alert(metric_name, 'CRITICAL', value)
        elif value >= thresholds['warning']:
            self._trigger_alert(metric_name, 'WARNING', value)
    
    def _trigger_alert(self, metric_name: str, level: str, value: float):
        """Trigger alert callbacks"""
        alert = {
            'metric': metric_name,
            'level': level,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.warning(f"Alert triggered: {json.dumps(alert)}")
        
        for callback in self._alert_callbacks[metric_name]:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {str(e)}")
    
    def _aggregate_metrics(self):
        """Aggregate metrics periodically"""
        now = datetime.now()
        if now - self._last_aggregation < self._aggregation_interval:
            return
        
        for metric_name, values in self._metrics.items():
            # Keep only recent values
            cutoff_time = now - timedelta(hours=24)
            self._metrics[metric_name] = [
                v for v in values
                if v.timestamp >= cutoff_time
            ]
        
        self._last_aggregation = now
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all current metrics
        
        Returns:
            Dictionary containing all current metrics
        """
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'latency_metrics': {
                name: [{'timestamp': m.timestamp.isoformat(), 'value': m.value, 'tags': m.tags} 
                       for m in values[-10:]]  # Last 10 values
                for name, values in self._metrics.items()
            },
            'alert_thresholds': dict(self._alert_thresholds),
            'total_metrics': len(self._metrics),
            'total_counters': len(self._counters),
            'total_gauges': len(self._gauges)
        }
    
    def __del__(self):
        """Cleanup"""
        # Stop the processing thread
        if hasattr(self, '_processing_thread') and self._processing_thread.is_alive():
            self._metric_queue.put(None)
            self._processing_thread.join(timeout=1) 