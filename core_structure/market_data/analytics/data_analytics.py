"""
Unified Data Analytics - Market Data Analytics & Performance Integration
======================================================================

Consolidated data analytics system combining:
- Market data analytics and quality monitoring
- Performance integration and system metrics
- Analytics reporting and visualization
- Unified analytics interface

This module replaces:
- market_data_analytics.py (819 lines)
- performance_integration.py (780 lines)

Author: StatArb_Gemini Architecture Consolidation
Version: 4.0 (Phase 4B)
"""

import asyncio
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Core infrastructure imports
try:
    from core_structure.infrastructure.types.monitoring_types import PerformanceMetric
    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
    from core_structure.infrastructure.messaging.message_bus import MessageBus
except ImportError:
    # Fallback classes if infrastructure not available
    class PerformanceMetric:
        def __init__(self, name: str, value: float, timestamp: datetime = None):
            self.name = name
            self.value = value
            self.timestamp = timestamp or datetime.now()
    MetricsCollector = None
    MessageBus = None

class DataQualityLevel(Enum):
    """Data quality level enumeration"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    VERY_POOR = "very_poor"

class DataIssueType(Enum):
    """Data issue type enumeration"""
    MISSING_DATA = "missing_data"
    DUPLICATE_DATA = "duplicate_data"
    OUTLIER_DATA = "outlier_data"
    INCONSISTENT_DATA = "inconsistent_data"
    DELAYED_DATA = "delayed_data"
    INVALID_DATA = "invalid_data"

class IntegrationStatus(Enum):
    """Integration status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"

class PerformanceCategory(Enum):
    """Performance metric categories"""
    DATA_QUALITY = "data_quality"
    PROCESSING_PERFORMANCE = "processing_performance"
    SYSTEM_PERFORMANCE = "system_performance"
    INTEGRATION_PERFORMANCE = "integration_performance"
    OVERALL_PERFORMANCE = "overall_performance"

class AnalyticsMode(Enum):
    """Analytics operation modes"""
    REALTIME = "realtime"
    BATCH = "batch"
    HYBRID = "hybrid"

@dataclass
class DataQualityMetrics:
    """Data quality metrics for market data"""
    completeness: float  # Percentage of expected data points present
    accuracy: float  # Percentage of data points within expected ranges
    consistency: float  # Percentage of data points with consistent format
    timeliness: float  # Percentage of data points received within expected time
    freshness: float  # How recent the data is
    coverage: float  # Symbol coverage ratio
    volume_quality: float  # Volume data quality
    price_quality: float  # Price data quality
    overall_score: float  # Overall quality score
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MarketDataPerformance:
    """Market data processing performance metrics"""
    throughput_per_second: float
    average_latency_ms: float
    error_rate: float
    processing_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_ratio: float
    network_latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AnalyticsConfig:
    """Analytics configuration"""
    sampling_interval_seconds: int = 60
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'completeness': 0.95,
        'accuracy': 0.98,
        'consistency': 0.95,
        'timeliness': 0.90,
        'freshness': 0.85
    })
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'max_latency_ms': 100,
        'max_error_rate': 0.01,
        'min_throughput': 1000,
        'max_cpu_usage': 80,
        'max_memory_mb': 1024
    })
    enabled_analytics: Set[str] = field(default_factory=lambda: {
        'quality_monitoring', 'performance_tracking', 'trend_analysis',
        'anomaly_detection', 'health_checks'
    })
    retention_hours: int = 168  # 1 week
    mode: AnalyticsMode = AnalyticsMode.HYBRID

@dataclass
class AnalyticsReport:
    """Comprehensive analytics report"""
    report_id: str
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    symbols_analyzed: List[str]
    quality_summary: Dict[str, Any]
    performance_summary: Dict[str, Any]
    issues_detected: List[Dict[str, Any]]
    recommendations: List[str]
    overall_health_score: float

class QualityAnalyzer:
    """Data quality analysis engine"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self._baseline_stats = {}
        
    def analyze_quality(self, data: pd.DataFrame, symbol: str) -> DataQualityMetrics:
        """Comprehensive data quality analysis"""
        try:
            if data.empty:
                return self._empty_data_metrics()
                
            # Calculate individual quality metrics
            completeness = self._calculate_completeness(data)
            accuracy = self._calculate_accuracy(data, symbol)
            consistency = self._calculate_consistency(data)
            timeliness = self._calculate_timeliness(data)
            freshness = self._calculate_freshness(data)
            coverage = self._calculate_coverage(data, symbol)
            volume_quality = self._calculate_volume_quality(data)
            price_quality = self._calculate_price_quality(data)
            
            # Calculate overall score
            weights = [0.15, 0.20, 0.15, 0.15, 0.10, 0.10, 0.10, 0.05]
            scores = [completeness, accuracy, consistency, timeliness, 
                     freshness, coverage, volume_quality, price_quality]
            overall_score = sum(w * s for w, s in zip(weights, scores))
            
            return DataQualityMetrics(
                completeness=completeness,
                accuracy=accuracy,
                consistency=consistency,
                timeliness=timeliness,
                freshness=freshness,
                coverage=coverage,
                volume_quality=volume_quality,
                price_quality=price_quality,
                overall_score=overall_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing quality for {symbol}: {e}")
            return self._empty_data_metrics()
            
    def _calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness ratio"""
        if data.empty:
            return 0.0
        total_cells = data.size
        missing_cells = data.isnull().sum().sum()
        return max(0.0, (total_cells - missing_cells) / total_cells)
        
    def _calculate_accuracy(self, data: pd.DataFrame, symbol: str) -> float:
        """Calculate data accuracy score"""
        if data.empty:
            return 0.0
            
        accuracy_score = 1.0
        
        # Check for reasonable price ranges
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in data.columns:
                values = data[col].dropna()
                if len(values) > 0:
                    # Check for negative prices
                    negative_count = (values <= 0).sum()
                    accuracy_score *= (len(values) - negative_count) / len(values)
                    
                    # Check for extreme values (beyond 10x median)
                    median_price = values.median()
                    if median_price > 0:
                        extreme_count = (values > 10 * median_price).sum()
                        accuracy_score *= (len(values) - extreme_count) / len(values)
                        
        return max(0.0, accuracy_score)
        
    def _calculate_consistency(self, data: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        if data.empty:
            return 0.0
            
        consistency_score = 1.0
        
        # OHLC consistency checks
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            # High >= max(open, close), Low <= min(open, close)
            valid_high = data['high'] >= data[['open', 'close']].max(axis=1)
            valid_low = data['low'] <= data[['open', 'close']].min(axis=1)
            
            total_records = len(data)
            if total_records > 0:
                high_consistency = valid_high.sum() / total_records
                low_consistency = valid_low.sum() / total_records
                consistency_score = (high_consistency + low_consistency) / 2
                
        return max(0.0, consistency_score)
        
    def _calculate_timeliness(self, data: pd.DataFrame) -> float:
        """Calculate data timeliness score"""
        if data.empty or 'timestamp' not in data.columns:
            return 0.0
            
        try:
            timestamps = pd.to_datetime(data['timestamp'], errors='coerce')
            latest_time = timestamps.max()
            current_time = datetime.now()
            
            if pd.isna(latest_time):
                return 0.0
                
            # Calculate staleness in minutes
            staleness_minutes = (current_time - latest_time.to_pydatetime()).total_seconds() / 60
            max_staleness = 15  # 15 minutes threshold
            
            return max(0.0, 1.0 - (staleness_minutes / max_staleness))
            
        except Exception:
            return 0.0
            
    def _calculate_freshness(self, data: pd.DataFrame) -> float:
        """Calculate data freshness score"""
        if data.empty or 'timestamp' not in data.columns:
            return 0.0
            
        try:
            timestamps = pd.to_datetime(data['timestamp'], errors='coerce')
            time_range = timestamps.max() - timestamps.min()
            expected_range = timedelta(hours=24)  # Expect data for last 24 hours
            
            return min(1.0, time_range.total_seconds() / expected_range.total_seconds())
            
        except Exception:
            return 0.0
            
    def _calculate_coverage(self, data: pd.DataFrame, symbol: str) -> float:
        """Calculate symbol coverage ratio"""
        # For single symbol, coverage is always 1.0
        # In multi-symbol context, this would calculate symbol coverage ratio
        return 1.0
        
    def _calculate_volume_quality(self, data: pd.DataFrame) -> float:
        """Calculate volume data quality"""
        if 'volume' not in data.columns:
            return 0.0
            
        volumes = data['volume'].dropna()
        if len(volumes) == 0:
            return 0.0
            
        # Check for non-negative volumes
        valid_volumes = (volumes >= 0).sum()
        return valid_volumes / len(volumes)
        
    def _calculate_price_quality(self, data: pd.DataFrame) -> float:
        """Calculate price data quality"""
        price_cols = ['open', 'high', 'low', 'close']
        available_cols = [col for col in price_cols if col in data.columns]
        
        if not available_cols:
            return 0.0
            
        quality_scores = []
        for col in available_cols:
            values = data[col].dropna()
            if len(values) > 0:
                # Check for positive prices
                positive_ratio = (values > 0).sum() / len(values)
                quality_scores.append(positive_ratio)
                
        return np.mean(quality_scores) if quality_scores else 0.0
        
    def _empty_data_metrics(self) -> DataQualityMetrics:
        """Return metrics for empty dataset"""
        return DataQualityMetrics(
            completeness=0.0,
            accuracy=0.0,
            consistency=0.0,
            timeliness=0.0,
            freshness=0.0,
            coverage=0.0,
            volume_quality=0.0,
            price_quality=0.0,
            overall_score=0.0
        )

class PerformanceAnalyzer:
    """System performance analysis engine"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self._performance_history = deque(maxlen=1000)
        self._start_time = datetime.now()
        
    def analyze_performance(self, processing_stats: Dict[str, Any]) -> MarketDataPerformance:
        """Analyze system performance metrics"""
        try:
            # Extract performance metrics
            throughput = processing_stats.get('throughput_per_second', 0.0)
            latency = processing_stats.get('average_latency_ms', 0.0)
            error_rate = processing_stats.get('error_rate', 0.0)
            processing_time = processing_stats.get('processing_time_ms', 0.0)
            memory_usage = processing_stats.get('memory_usage_mb', 0.0)
            cpu_usage = processing_stats.get('cpu_usage_percent', 0.0)
            cache_hit_ratio = processing_stats.get('cache_hit_ratio', 0.0)
            network_latency = processing_stats.get('network_latency_ms', 0.0)
            
            performance = MarketDataPerformance(
                throughput_per_second=throughput,
                average_latency_ms=latency,
                error_rate=error_rate,
                processing_time_ms=processing_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                cache_hit_ratio=cache_hit_ratio,
                network_latency_ms=network_latency
            )
            
            self._performance_history.append(performance)
            return performance
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return self._empty_performance_metrics()
            
    def get_performance_trend(self, minutes: int = 60) -> Dict[str, List[float]]:
        """Get performance trends over time"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self._performance_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
            
        return {
            'timestamps': [m.timestamp.timestamp() for m in recent_metrics],
            'throughput': [m.throughput_per_second for m in recent_metrics],
            'latency': [m.average_latency_ms for m in recent_metrics],
            'error_rate': [m.error_rate for m in recent_metrics],
            'cpu_usage': [m.cpu_usage_percent for m in recent_metrics],
            'memory_usage': [m.memory_usage_mb for m in recent_metrics]
        }
        
    def _empty_performance_metrics(self) -> MarketDataPerformance:
        """Return empty performance metrics"""
        return MarketDataPerformance(
            throughput_per_second=0.0,
            average_latency_ms=0.0,
            error_rate=0.0,
            processing_time_ms=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
            cache_hit_ratio=0.0,
            network_latency_ms=0.0
        )

class UnifiedDataAnalytics:
    """
    Unified Data Analytics System
    
    Consolidates:
    - Market data analytics and quality monitoring
    - Performance integration and system metrics
    - Analytics reporting and visualization
    - Comprehensive analytics interface
    """
    
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self.quality_analyzer = QualityAnalyzer(self.config)
        self.performance_analyzer = PerformanceAnalyzer(self.config)
        
        # State management
        self.status = IntegrationStatus.STOPPED
        self._analytics_task = None
        self._quality_history = defaultdict(lambda: deque(maxlen=1000))
        self._performance_history = deque(maxlen=1000)
        self._reports = deque(maxlen=100)
        
        # External integrations
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        self.message_bus = MessageBus() if MessageBus else None
        
        logger.info("UnifiedDataAnalytics initialized")
        
    def start_analytics(self):
        """Start analytics processing"""
        if self.status == IntegrationStatus.ACTIVE:
            logger.warning("Analytics already active")
            return
            
        self.status = IntegrationStatus.ACTIVE
        self._analytics_task = asyncio.create_task(self._analytics_loop())
        logger.info("Data analytics started")
        
    async def stop_analytics(self):
        """Stop analytics processing"""
        self.status = IntegrationStatus.STOPPED
        if self._analytics_task:
            self._analytics_task.cancel()
            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass
        logger.info("Data analytics stopped")
        
    def analyze_data_quality(self, data: pd.DataFrame, symbol: str) -> DataQualityMetrics:
        """Analyze data quality for market data"""
        metrics = self.quality_analyzer.analyze_quality(data, symbol)
        
        # Store metrics
        self._quality_history[symbol].append(metrics)
        
        # Publish metrics if available
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                f"analytics.quality.{symbol}.overall_score",
                metrics.overall_score
            )
            
        return metrics
        
    def analyze_performance(self, processing_stats: Dict[str, Any]) -> MarketDataPerformance:
        """Analyze system performance"""
        performance = self.performance_analyzer.analyze_performance(processing_stats)
        
        # Store performance metrics
        self._performance_history.append(performance)
        
        # Publish metrics if available
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                "analytics.performance.throughput",
                performance.throughput_per_second
            )
            self.metrics_collector.record_metric(
                "analytics.performance.latency",
                performance.average_latency_ms
            )
            
        return performance
        
    def generate_report(self, period_hours: int = 24) -> AnalyticsReport:
        """Generate comprehensive analytics report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Collect data for the period
        symbols_analyzed = list(self._quality_history.keys())
        quality_summary = self._summarize_quality_metrics(start_time, end_time)
        performance_summary = self._summarize_performance_metrics(start_time, end_time)
        issues_detected = self._detect_issues(start_time, end_time)
        recommendations = self._generate_recommendations(quality_summary, performance_summary)
        health_score = self._calculate_health_score(quality_summary, performance_summary)
        
        report = AnalyticsReport(
            report_id=f"report_{int(datetime.now().timestamp())}",
            timestamp=end_time,
            period_start=start_time,
            period_end=end_time,
            symbols_analyzed=symbols_analyzed,
            quality_summary=quality_summary,
            performance_summary=performance_summary,
            issues_detected=issues_detected,
            recommendations=recommendations,
            overall_health_score=health_score
        )
        
        self._reports.append(report)
        return report
        
    def get_quality_metrics(self, symbol: str, hours: int = 24) -> List[DataQualityMetrics]:
        """Get quality metrics for symbol"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            m for m in self._quality_history[symbol]
            if m.timestamp >= cutoff_time
        ]
        
    def get_performance_metrics(self, hours: int = 24) -> List[MarketDataPerformance]:
        """Get performance metrics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            m for m in self._performance_history
            if m.timestamp >= cutoff_time
        ]
        
    def get_performance_trends(self, minutes: int = 60) -> Dict[str, List[float]]:
        """Get performance trends"""
        return self.performance_analyzer.get_performance_trend(minutes)
        
    def get_analytics_status(self) -> Dict[str, Any]:
        """Get analytics system status"""
        return {
            'status': self.status.value,
            'tracked_symbols': len(self._quality_history),
            'quality_points': sum(len(hist) for hist in self._quality_history.values()),
            'performance_points': len(self._performance_history),
            'reports_generated': len(self._reports),
            'config': {
                'mode': self.config.mode.value,
                'enabled_analytics': list(self.config.enabled_analytics)
            }
        }
        
    async def _analytics_loop(self):
        """Main analytics processing loop"""
        while self.status == IntegrationStatus.ACTIVE:
            try:
                # Periodic analytics processing would go here
                # For now, just maintain the loop structure
                await asyncio.sleep(self.config.sampling_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                await asyncio.sleep(5)
                
    def _summarize_quality_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Summarize quality metrics for period"""
        summary = {
            'symbols_count': len(self._quality_history),
            'average_scores': {},
            'trends': {}
        }
        
        for symbol, metrics_list in self._quality_history.items():
            period_metrics = [
                m for m in metrics_list
                if start_time <= m.timestamp <= end_time
            ]
            
            if period_metrics:
                summary['average_scores'][symbol] = {
                    'overall_score': np.mean([m.overall_score for m in period_metrics]),
                    'completeness': np.mean([m.completeness for m in period_metrics]),
                    'accuracy': np.mean([m.accuracy for m in period_metrics])
                }
                
        return summary
        
    def _summarize_performance_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Summarize performance metrics for period"""
        period_metrics = [
            m for m in self._performance_history
            if start_time <= m.timestamp <= end_time
        ]
        
        if not period_metrics:
            return {}
            
        return {
            'average_throughput': np.mean([m.throughput_per_second for m in period_metrics]),
            'average_latency': np.mean([m.average_latency_ms for m in period_metrics]),
            'average_error_rate': np.mean([m.error_rate for m in period_metrics]),
            'average_cpu_usage': np.mean([m.cpu_usage_percent for m in period_metrics]),
            'average_memory_usage': np.mean([m.memory_usage_mb for m in period_metrics])
        }
        
    def _detect_issues(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Detect issues in the specified period"""
        issues = []
        
        # Quality issues
        for symbol, metrics_list in self._quality_history.items():
            period_metrics = [
                m for m in metrics_list
                if start_time <= m.timestamp <= end_time
            ]
            
            for metric in period_metrics:
                if metric.overall_score < 0.7:
                    issues.append({
                        'type': 'quality',
                        'symbol': symbol,
                        'severity': 'high' if metric.overall_score < 0.5 else 'medium',
                        'message': f"Low quality score: {metric.overall_score:.2f}",
                        'timestamp': metric.timestamp
                    })
                    
        # Performance issues
        period_performance = [
            m for m in self._performance_history
            if start_time <= m.timestamp <= end_time
        ]
        
        for perf in period_performance:
            if perf.average_latency_ms > 100:
                issues.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'message': f"High latency: {perf.average_latency_ms:.1f}ms",
                    'timestamp': perf.timestamp
                })
                
        return issues
        
    def _generate_recommendations(self, quality_summary: Dict[str, Any], 
                                performance_summary: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        # Quality recommendations
        if quality_summary.get('average_scores'):
            avg_scores = quality_summary['average_scores']
            low_quality_symbols = [
                symbol for symbol, scores in avg_scores.items()
                if scores.get('overall_score', 0) < 0.8
            ]
            
            if low_quality_symbols:
                recommendations.append(
                    f"Investigate data quality issues for symbols: {', '.join(low_quality_symbols)}"
                )
                
        # Performance recommendations
        if performance_summary:
            if performance_summary.get('average_latency', 0) > 50:
                recommendations.append("Consider optimizing data processing pipeline to reduce latency")
                
            if performance_summary.get('average_error_rate', 0) > 0.01:
                recommendations.append("Investigate error sources to improve system reliability")
                
        return recommendations
        
    def _calculate_health_score(self, quality_summary: Dict[str, Any], 
                              performance_summary: Dict[str, Any]) -> float:
        """Calculate overall system health score"""
        quality_score = 0.8  # Default if no quality data
        performance_score = 0.8  # Default if no performance data
        
        # Quality component
        if quality_summary.get('average_scores'):
            avg_scores = quality_summary['average_scores']
            if avg_scores:
                symbol_scores = [scores.get('overall_score', 0) for scores in avg_scores.values()]
                quality_score = np.mean(symbol_scores)
                
        # Performance component
        if performance_summary:
            # Normalize performance metrics to 0-1 scale
            latency_score = max(0, 1 - (performance_summary.get('average_latency', 0) / 200))
            error_score = max(0, 1 - (performance_summary.get('average_error_rate', 0) * 100))
            performance_score = (latency_score + error_score) / 2
            
        # Weighted combination
        return (quality_score * 0.6 + performance_score * 0.4)

# Backward compatibility aliases
MarketDataAnalytics = UnifiedDataAnalytics
PerformanceIntegration = UnifiedDataAnalytics

# Export classes
__all__ = [
    'UnifiedDataAnalytics',
    'QualityAnalyzer',
    'PerformanceAnalyzer',
    'DataQualityMetrics',
    'MarketDataPerformance',
    'AnalyticsConfig',
    'AnalyticsReport',
    'DataQualityLevel',
    'DataIssueType',
    'IntegrationStatus',
    'PerformanceCategory',
    'AnalyticsMode',
    # Backward compatibility
    'MarketDataAnalytics',
    'PerformanceIntegration'
]
