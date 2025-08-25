#!/usr/bin/env python3
"""
Real-Time Metrics Collector
===========================

Comprehensive metrics collection system for real-time monitoring
of trading system performance, health, and business metrics.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import statistics
from enum import Enum

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"          # Monotonically increasing
    GAUGE = "gauge"              # Current value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Timing measurements
    BUSINESS = "business"        # Business metrics

@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    value: Union[float, int]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""

@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    name: str
    metric_type: MetricType
    count: int
    latest_value: Union[float, int]
    min_value: Union[float, int]
    max_value: Union[float, int]
    avg_value: float
    percentile_95: float
    percentile_99: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)

class MetricsCollector:
    """
    Advanced real-time metrics collection system.
    
    Features:
    - Multi-type metric support (counters, gauges, histograms, timers)
    - Real-time aggregation and statistics
    - Tag-based metric organization
    - Automatic metric retention and cleanup
    - Performance-optimized storage
    """
    
    def __init__(
        self,
        collection_interval: float = 1.0,
        retention_hours: int = 24,
        max_metrics_per_type: int = 10000
    ):
        self.collection_interval = collection_interval
        self.retention_hours = retention_hours
        self.max_metrics_per_type = max_metrics_per_type
        
        # Metric storage
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_per_type))
        self.metric_metadata: Dict[str, MetricType] = {}
        self.metric_tags: Dict[str, Dict[str, str]] = {}
        
        # Real-time aggregations
        self.aggregated_metrics: Dict[str, MetricSummary] = {}
        self.aggregation_window = timedelta(minutes=1)
        
        # Collection state
        self.is_collecting = False
        self.collection_task: Optional[asyncio.Task] = None
        self.collection_lock = threading.RLock()
        
        # Performance counters
        self.collection_stats = {
            'metrics_collected': 0,
            'aggregations_computed': 0,
            'cleanup_operations': 0,
            'collection_errors': 0
        }
        
        # Registered metric sources
        self.metric_sources: Dict[str, Callable] = {}
        
        logger.info("MetricsCollector initialized")
    
    async def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            logger.warning("Metrics collection already active")
            return
        
        self.is_collecting = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        logger.info("Metrics collection started")
    
    async def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collection stopped")
    
    def record_metric(
        self,
        name: str,
        value: Union[float, int],
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
        unit: str = "",
        description: str = ""
    ):
        """Record a single metric"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {},
            unit=unit,
            description=description
        )
        
        with self.collection_lock:
            self.metrics[name].append(metric)
            self.metric_metadata[name] = metric_type
            if tags:
                self.metric_tags[name] = tags
            
            self.collection_stats['metrics_collected'] += 1
    
    def record_counter(self, name: str, value: Union[float, int] = 1, tags: Optional[Dict[str, str]] = None):
        """Record a counter metric"""
        self.record_metric(name, value, MetricType.COUNTER, tags)
    
    def record_gauge(self, name: str, value: Union[float, int], tags: Optional[Dict[str, str]] = None):
        """Record a gauge metric"""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timer(self, name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric"""
        self.record_metric(name, duration_ms, MetricType.TIMER, tags, unit="ms")
    
    def record_histogram(self, name: str, value: Union[float, int], tags: Optional[Dict[str, str]] = None):
        """Record a histogram metric"""
        self.record_metric(name, value, MetricType.HISTOGRAM, tags)
    
    def record_business_metric(self, name: str, value: Union[float, int], tags: Optional[Dict[str, str]] = None):
        """Record a business metric"""
        self.record_metric(name, value, MetricType.BUSINESS, tags)
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Increment a counter by 1"""
        self.record_counter(name, 1, tags)
    
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimerContext(self, name, tags)
    
    def register_metric_source(self, name: str, source_func: Callable):
        """Register a function to provide metrics"""
        self.metric_sources[name] = source_func
        logger.info(f"Registered metric source: {name}")
    
    def unregister_metric_source(self, name: str):
        """Unregister a metric source"""
        if name in self.metric_sources:
            del self.metric_sources[name]
            logger.info(f"Unregistered metric source: {name}")
    
    async def _collection_loop(self):
        """Main collection loop"""
        while self.is_collecting:
            try:
                # Collect from registered sources
                await self._collect_from_sources()
                
                # Compute aggregations
                await self._compute_aggregations()
                
                # Cleanup old metrics
                if self.collection_stats['metrics_collected'] % 1000 == 0:
                    await self._cleanup_old_metrics()
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                self.collection_stats['collection_errors'] += 1
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_from_sources(self):
        """Collect metrics from registered sources"""
        for source_name, source_func in self.metric_sources.items():
            try:
                # Run source function
                if asyncio.iscoroutinefunction(source_func):
                    metrics_data = await source_func()
                else:
                    metrics_data = source_func()
                
                # Process returned metrics
                if isinstance(metrics_data, dict):
                    for metric_name, metric_value in metrics_data.items():
                        if isinstance(metric_value, (int, float)):
                            self.record_gauge(f"{source_name}.{metric_name}", metric_value)
                        elif isinstance(metric_value, dict) and 'value' in metric_value:
                            metric_type = MetricType(metric_value.get('type', 'gauge'))
                            self.record_metric(
                                f"{source_name}.{metric_name}",
                                metric_value['value'],
                                metric_type,
                                metric_value.get('tags'),
                                metric_value.get('unit', ''),
                                metric_value.get('description', '')
                            )
                
            except Exception as e:
                logger.error(f"Error collecting from source {source_name}: {e}")
    
    async def _compute_aggregations(self):
        """Compute real-time metric aggregations"""
        cutoff_time = datetime.now() - self.aggregation_window
        
        with self.collection_lock:
            for metric_name, metric_deque in self.metrics.items():
                if not metric_deque:
                    continue
                
                # Get recent metrics
                recent_metrics = [
                    m for m in metric_deque
                    if m.timestamp > cutoff_time
                ]
                
                if not recent_metrics:
                    continue
                
                # Calculate summary statistics
                values = [m.value for m in recent_metrics]
                metric_type = self.metric_metadata.get(metric_name, MetricType.GAUGE)
                
                if len(values) > 0:
                    summary = MetricSummary(
                        name=metric_name,
                        metric_type=metric_type,
                        count=len(values),
                        latest_value=values[-1],
                        min_value=min(values),
                        max_value=max(values),
                        avg_value=statistics.mean(values),
                        percentile_95=self._percentile(values, 95),
                        percentile_99=self._percentile(values, 99),
                        timestamp=datetime.now(),
                        tags=self.metric_tags.get(metric_name, {})
                    )
                    
                    self.aggregated_metrics[metric_name] = summary
                    self.collection_stats['aggregations_computed'] += 1
    
    def _percentile(self, values: List[Union[float, int]], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return float(sorted_values[index])
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics to manage memory"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        cleaned_count = 0
        
        with self.collection_lock:
            for metric_name, metric_deque in self.metrics.items():
                # Remove old metrics
                original_size = len(metric_deque)
                
                # Convert to list, filter, and replace
                recent_metrics = [m for m in metric_deque if m.timestamp > cutoff_time]
                metric_deque.clear()
                metric_deque.extend(recent_metrics)
                
                cleaned_count += original_size - len(metric_deque)
        
        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} old metrics")
            self.collection_stats['cleanup_operations'] += 1
    
    def get_metric_summary(self, metric_name: str) -> Optional[MetricSummary]:
        """Get summary for a specific metric"""
        return self.aggregated_metrics.get(metric_name)
    
    def get_all_summaries(self) -> Dict[str, MetricSummary]:
        """Get all metric summaries"""
        return self.aggregated_metrics.copy()
    
    def get_metrics_by_tag(self, tag_key: str, tag_value: str) -> List[MetricSummary]:
        """Get metrics filtered by tag"""
        results = []
        for summary in self.aggregated_metrics.values():
            if summary.tags.get(tag_key) == tag_value:
                results.append(summary)
        return results
    
    def get_metrics_by_type(self, metric_type: MetricType) -> List[MetricSummary]:
        """Get metrics filtered by type"""
        return [
            summary for summary in self.aggregated_metrics.values()
            if summary.metric_type == metric_type
        ]
    
    def get_recent_metrics(
        self,
        metric_name: str,
        duration_minutes: int = 10
    ) -> List[Metric]:
        """Get recent raw metrics for a specific metric"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self.collection_lock:
            if metric_name in self.metrics:
                return [
                    m for m in self.metrics[metric_name]
                    if m.timestamp > cutoff_time
                ]
        
        return []
    
    def export_metrics(self, format_type: str = 'json') -> str:
        """Export metrics in specified format"""
        if format_type == 'json':
            return self._export_json()
        elif format_type == 'prometheus':
            return self._export_prometheus()
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_json(self) -> str:
        """Export metrics as JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'collection_stats': self.collection_stats,
            'metrics': {}
        }
        
        for name, summary in self.aggregated_metrics.items():
            export_data['metrics'][name] = asdict(summary)
            # Convert datetime to string for JSON serialization
            export_data['metrics'][name]['timestamp'] = summary.timestamp.isoformat()
        
        return json.dumps(export_data, indent=2)
    
    def _export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for name, summary in self.aggregated_metrics.items():
            # Create Prometheus metric name
            prom_name = name.replace('.', '_').replace('-', '_')
            
            # Add metric documentation
            lines.append(f"# HELP {prom_name} {summary.name}")
            lines.append(f"# TYPE {prom_name} gauge")
            
            # Add metric value with tags
            tag_str = ""
            if summary.tags:
                tag_pairs = [f'{k}="{v}"' for k, v in summary.tags.items()]
                tag_str = "{" + ",".join(tag_pairs) + "}"
            
            lines.append(f"{prom_name}{tag_str} {summary.latest_value}")
        
        return "\n".join(lines)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            **self.collection_stats,
            'active_metrics': len(self.metrics),
            'aggregated_metrics': len(self.aggregated_metrics),
            'registered_sources': len(self.metric_sources),
            'collection_active': self.is_collecting
        }

class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.collector.record_timer(self.name, duration_ms, self.tags)

# Global metrics collector instance
metrics_collector = MetricsCollector()

async def start_metrics_collection():
    """Start global metrics collection"""
    await metrics_collector.start_collection()

async def stop_metrics_collection():
    """Stop global metrics collection"""
    await metrics_collector.stop_collection()

# Convenience functions for common metrics
def record_trade_execution(symbol: str, quantity: float, price: float, execution_time_ms: float):
    """Record trade execution metrics"""
    metrics_collector.record_business_metric('trades.executed', 1, {'symbol': symbol})
    metrics_collector.record_business_metric('trades.volume', quantity, {'symbol': symbol})
    metrics_collector.record_business_metric('trades.value', quantity * price, {'symbol': symbol})
    metrics_collector.record_timer('execution.latency', execution_time_ms, {'symbol': symbol})

def record_signal_generation(strategy: str, signal_count: int, generation_time_ms: float):
    """Record signal generation metrics"""
    metrics_collector.record_business_metric('signals.generated', signal_count, {'strategy': strategy})
    metrics_collector.record_timer('signals.generation_time', generation_time_ms, {'strategy': strategy})

def record_portfolio_update(portfolio_value: float, update_time_ms: float):
    """Record portfolio update metrics"""
    metrics_collector.record_gauge('portfolio.value', portfolio_value)
    metrics_collector.record_timer('portfolio.update_time', update_time_ms)
