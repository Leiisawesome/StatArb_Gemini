"""
Market Data Analytics Module

Comprehensive market data analysis and quality monitoring system for
Phase 6: Market Data & Performance Integration.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


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


@dataclass
class DataQualityMetrics:
    """Data quality metrics for market data"""
    
    # Basic metrics
    completeness: float  # Percentage of expected data points present
    accuracy: float  # Percentage of data points within expected ranges
    consistency: float  # Percentage of data points with consistent format
    timeliness: float  # Percentage of data points received within expected time
    
    # Advanced metrics
    outlier_rate: float  # Percentage of outliers detected
    duplicate_rate: float  # Percentage of duplicate entries
    gap_count: int  # Number of data gaps
    max_gap_duration: timedelta  # Maximum gap duration
    
    # Calculated quality score
    overall_quality_score: float
    
    # Timestamp for tracking
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Issues detected
    issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'completeness': self.completeness,
            'accuracy': self.accuracy,
            'consistency': self.consistency,
            'timeliness': self.timeliness,
            'outlier_rate': self.outlier_rate,
            'duplicate_rate': self.duplicate_rate,
            'gap_count': self.gap_count,
            'max_gap_duration': str(self.max_gap_duration),
            'overall_quality_score': self.overall_quality_score,
            'timestamp': self.timestamp.isoformat(),
            'issues': self.issues
        }


@dataclass
class MarketDataPerformance:
    """Market data performance metrics"""
    
    # Performance metrics
    data_throughput: float  # Data points per second
    processing_latency: float  # Average processing time in milliseconds
    storage_efficiency: float  # Storage utilization percentage
    retrieval_speed: float  # Average retrieval time in milliseconds
    
    # System metrics
    memory_usage: float  # Memory usage in MB
    cpu_usage: float  # CPU usage percentage
    disk_usage: float  # Disk usage percentage
    
    # Calculated performance score
    overall_performance_score: float
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'data_throughput': self.data_throughput,
            'processing_latency': self.processing_latency,
            'storage_efficiency': self.storage_efficiency,
            'retrieval_speed': self.retrieval_speed,
            'memory_usage': self.memory_usage,
            'cpu_usage': self.cpu_usage,
            'disk_usage': self.disk_usage,
            'overall_performance_score': self.overall_performance_score,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MarketDataAnalyticsConfig:
    """Configuration for market data analytics"""
    
    # Quality thresholds
    min_completeness_threshold: float = 0.95  # 95% minimum completeness
    min_accuracy_threshold: float = 0.98  # 98% minimum accuracy
    min_consistency_threshold: float = 0.90  # 90% minimum consistency
    max_latency_threshold: float = 1000.0  # 1 second maximum latency
    
    # Outlier detection
    outlier_std_threshold: float = 3.0  # Standard deviations for outlier detection
    outlier_iqr_multiplier: float = 1.5  # IQR multiplier for outlier detection
    
    # Performance thresholds
    min_throughput_threshold: float = 1000.0  # Minimum data points per second
    max_processing_latency: float = 100.0  # Maximum processing latency in ms
    
    # Monitoring settings
    monitoring_interval_seconds: int = 60  # Monitoring interval
    alert_threshold_score: float = 70.0  # Alert threshold for quality score
    retention_days: int = 30  # Data retention period
    
    # Analysis settings
    enable_real_time_monitoring: bool = True
    enable_historical_analysis: bool = True
    enable_anomaly_detection: bool = True


class MarketDataAnalytics:
    """
    Market Data Analytics System
    
    Provides comprehensive analysis of market data quality, performance,
    and integration metrics for the trading system.
    """
    
    def __init__(self, config: Optional[MarketDataAnalyticsConfig] = None):
        """
        Initialize Market Data Analytics
        
        Args:
            config: Configuration for analytics system
        """
        self.config = config or MarketDataAnalyticsConfig()
        self.quality_history: List[DataQualityMetrics] = []
        self.performance_history: List[MarketDataPerformance] = []
        self.issue_history: List[Dict[str, Any]] = []
        
        # Initialize monitoring
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        logger.info("MarketDataAnalytics initialized")
    
    async def analyze_data_quality(self, market_data: pd.DataFrame, symbol: str) -> DataQualityMetrics:
        """
        Analyze data quality for given market data
        
        Args:
            market_data: Market data DataFrame
            symbol: Symbol being analyzed
            
        Returns:
            DataQualityMetrics with quality analysis results
        """
        logger.info(f"Analyzing data quality for {symbol}")
        
        # Calculate basic quality metrics
        completeness = self._calculate_completeness(market_data)
        accuracy = self._calculate_accuracy(market_data)
        consistency = self._calculate_consistency(market_data)
        timeliness = self._calculate_timeliness(market_data)
        
        # Calculate advanced metrics
        outlier_rate = self._calculate_outlier_rate(market_data)
        duplicate_rate = self._calculate_duplicate_rate(market_data)
        gap_count, max_gap_duration = self._calculate_gap_metrics(market_data)
        
        # Detect issues
        issues = self._detect_data_issues(market_data, symbol)
        
        # Calculate overall quality score
        overall_quality_score = self._calculate_quality_score(
            completeness, accuracy, consistency, timeliness,
            outlier_rate, duplicate_rate, gap_count
        )
        
        # Create quality metrics
        quality_metrics = DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            outlier_rate=outlier_rate,
            duplicate_rate=duplicate_rate,
            gap_count=gap_count,
            max_gap_duration=max_gap_duration,
            overall_quality_score=overall_quality_score,
            timestamp=datetime.now(),
            issues=issues
        )
        
        # Store in history
        self.quality_history.append(quality_metrics)
        
        logger.info(f"Data quality analysis completed for {symbol}: {overall_quality_score:.2f}")
        return quality_metrics
    
    async def analyze_performance(self, market_data: pd.DataFrame, processing_time: float) -> MarketDataPerformance:
        """
        Analyze performance metrics for market data processing
        
        Args:
            market_data: Market data DataFrame
            processing_time: Time taken to process data in seconds
            
        Returns:
            MarketDataPerformance with performance metrics
        """
        logger.info("Analyzing market data performance")
        
        # Calculate performance metrics
        data_throughput = len(market_data) / processing_time if processing_time > 0 else 0
        processing_latency = processing_time * 1000  # Convert to milliseconds
        
        # Calculate system metrics (mock implementation)
        storage_efficiency = self._calculate_storage_efficiency(market_data)
        retrieval_speed = self._calculate_retrieval_speed()
        memory_usage = self._get_memory_usage()
        cpu_usage = self._get_cpu_usage()
        disk_usage = self._get_disk_usage()
        
        # Calculate overall performance score
        overall_performance_score = self._calculate_performance_score(
            data_throughput, processing_latency, storage_efficiency,
            retrieval_speed, memory_usage, cpu_usage, disk_usage
        )
        
        # Create performance metrics
        performance_metrics = MarketDataPerformance(
            data_throughput=data_throughput,
            processing_latency=processing_latency,
            storage_efficiency=storage_efficiency,
            retrieval_speed=retrieval_speed,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            disk_usage=disk_usage,
            overall_performance_score=overall_performance_score
        )
        
        # Store in history
        self.performance_history.append(performance_metrics)
        
        logger.info(f"Performance analysis completed: {overall_performance_score:.2f}")
        return performance_metrics
    
    async def start_monitoring(self):
        """Start real-time monitoring of market data quality and performance"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Market data monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring"""
        if not self.monitoring_active:
            logger.warning("Monitoring not active")
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Market data monitoring stopped")
    
    def get_quality_summary(self, symbol: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """
        Get quality summary for specified period
        
        Args:
            symbol: Optional symbol filter
            days: Number of days to analyze
            
        Returns:
            Quality summary dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter quality history by date
        recent_quality = [
            q for q in self.quality_history
            if q.timestamp > cutoff_date
        ]
        
        if not recent_quality:
            return {"error": "No quality data available for specified period"}
        
        # Calculate summary statistics
        avg_completeness = np.mean([q.completeness for q in recent_quality])
        avg_accuracy = np.mean([q.accuracy for q in recent_quality])
        avg_consistency = np.mean([q.consistency for q in recent_quality])
        avg_quality_score = np.mean([q.overall_quality_score for q in recent_quality])
        
        # Count issues
        total_issues = sum(len(q.issues) for q in recent_quality)
        
        return {
            'period_days': days,
            'data_points': len(recent_quality),
            'avg_completeness': avg_completeness,
            'avg_accuracy': avg_accuracy,
            'avg_consistency': avg_consistency,
            'avg_quality_score': avg_quality_score,
            'total_issues': total_issues,
            'quality_trend': self._calculate_quality_trend(recent_quality)
        }
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get performance summary for specified period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Performance summary dictionary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Filter performance history by date
        recent_performance = [
            p for p in self.performance_history
            if p.timestamp > cutoff_date
        ]
        
        if not recent_performance:
            return {"error": "No performance data available for specified period"}
        
        # Calculate summary statistics
        avg_throughput = np.mean([p.data_throughput for p in recent_performance])
        avg_latency = np.mean([p.processing_latency for p in recent_performance])
        avg_performance_score = np.mean([p.overall_performance_score for p in recent_performance])
        
        return {
            'period_days': days,
            'data_points': len(recent_performance),
            'avg_throughput': avg_throughput,
            'avg_latency': avg_latency,
            'avg_performance_score': avg_performance_score,
            'performance_trend': self._calculate_performance_trend(recent_performance)
        }
    
    def generate_analytics_report(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report
        
        Args:
            symbol: Symbol to analyze
            days: Number of days to analyze
            
        Returns:
            Comprehensive analytics report
        """
        logger.info(f"Generating analytics report for {symbol} (last {days} days)")
        
        quality_summary = self.get_quality_summary(symbol, days)
        performance_summary = self.get_performance_summary(days)
        
        # Calculate overall health score
        quality_score = quality_summary.get('avg_quality_score', 0)
        performance_score = performance_summary.get('avg_performance_score', 0)
        overall_health_score = (quality_score + performance_score) / 2
        
        # Determine health status
        if overall_health_score >= 90:
            health_status = "EXCELLENT"
        elif overall_health_score >= 80:
            health_status = "GOOD"
        elif overall_health_score >= 70:
            health_status = "AVERAGE"
        elif overall_health_score >= 60:
            health_status = "POOR"
        else:
            health_status = "CRITICAL"
        
        report = {
            'symbol': symbol,
            'analysis_period_days': days,
            'timestamp': datetime.now().isoformat(),
            'overall_health_score': overall_health_score,
            'health_status': health_status,
            'quality_summary': quality_summary,
            'performance_summary': performance_summary,
            'recommendations': self._generate_recommendations(quality_summary, performance_summary),
            'alerts': self._generate_alerts(quality_summary, performance_summary)
        }
        
        logger.info(f"Analytics report generated for {symbol}: {health_status}")
        return report
    
    # Private helper methods
    
    def _calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness percentage"""
        if data.empty:
            return 0.0
        
        # Count non-null values
        non_null_count = data.count().sum()
        total_count = data.size
        
        return (non_null_count / total_count) * 100 if total_count > 0 else 0.0
    
    def _calculate_accuracy(self, data: pd.DataFrame) -> float:
        """Calculate data accuracy percentage"""
        if data.empty:
            return 0.0
        
        # Check for reasonable value ranges
        accuracy_checks = 0
        total_checks = 0
        
        # Price checks
        if 'close' in data.columns:
            total_checks += 1
            if (data['close'] > 0).all():
                accuracy_checks += 1
        
        if 'volume' in data.columns:
            total_checks += 1
            if (data['volume'] >= 0).all():
                accuracy_checks += 1
        
        # High/Low checks
        if all(col in data.columns for col in ['high', 'low', 'close']):
            total_checks += 1
            if (data['high'] >= data['low']).all() and (data['high'] >= data['close']).all():
                accuracy_checks += 1
        
        return (accuracy_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    def _calculate_consistency(self, data: pd.DataFrame) -> float:
        """Calculate data consistency percentage"""
        if data.empty:
            return 0.0
        
        # Check for consistent data types and formats
        consistency_checks = 0
        total_checks = 0
        
        # Check numeric columns
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            total_checks += 1
            if not data[col].isnull().all():
                consistency_checks += 1
        
        # Check timestamp consistency if available
        if 'timestamp' in data.columns:
            total_checks += 1
            try:
                pd.to_datetime(data['timestamp'])
                consistency_checks += 1
            except:
                pass
        
        return (consistency_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    def _calculate_timeliness(self, data: pd.DataFrame) -> float:
        """Calculate data timeliness percentage"""
        if data.empty or 'timestamp' not in data.columns:
            return 0.0
        
        try:
            timestamps = pd.to_datetime(data['timestamp'])
            current_time = pd.Timestamp.now()
            
            # Check if data is within expected time window (e.g., 5 minutes)
            time_window = pd.Timedelta(minutes=5)
            timely_data = (current_time - timestamps) <= time_window
            
            return (timely_data.sum() / len(timely_data)) * 100
        except:
            return 0.0
    
    def _calculate_outlier_rate(self, data: pd.DataFrame) -> float:
        """Calculate outlier rate percentage"""
        if data.empty:
            return 0.0
        
        outlier_count = 0
        total_count = 0
        
        # Check numeric columns for outliers
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['close', 'high', 'low', 'open']:
                total_count += len(data[col])
                
                # Use IQR method for outlier detection
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - self.config.outlier_iqr_multiplier * IQR
                upper_bound = Q3 + self.config.outlier_iqr_multiplier * IQR
                
                outliers = ((data[col] < lower_bound) | (data[col] > upper_bound)).sum()
                outlier_count += outliers
        
        return (outlier_count / total_count) * 100 if total_count > 0 else 0.0
    
    def _calculate_duplicate_rate(self, data: pd.DataFrame) -> float:
        """Calculate duplicate rate percentage"""
        if data.empty:
            return 0.0
        
        # Count duplicates
        duplicate_count = data.duplicated().sum()
        total_count = len(data)
        
        return (duplicate_count / total_count) * 100 if total_count > 0 else 0.0
    
    def _calculate_gap_metrics(self, data: pd.DataFrame) -> Tuple[int, timedelta]:
        """Calculate gap metrics"""
        if data.empty or 'timestamp' not in data.columns:
            return 0, timedelta(0)
        
        try:
            timestamps = pd.to_datetime(data['timestamp']).sort_values()
            
            # Calculate time differences
            time_diffs = timestamps.diff().dropna()
            
            # Count gaps (assuming expected interval is 1 minute)
            expected_interval = pd.Timedelta(minutes=1)
            gaps = time_diffs > expected_interval * 2  # Allow some tolerance
            
            gap_count = gaps.sum()
            max_gap_duration = time_diffs.max() if not time_diffs.empty else timedelta(0)
            
            return int(gap_count), max_gap_duration
        except:
            return 0, timedelta(0)
    
    def _detect_data_issues(self, data: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """Detect data issues"""
        issues = []
        
        # Check for missing data
        if data.empty:
            issues.append({
                'type': DataIssueType.MISSING_DATA.value,
                'severity': 'high',
                'description': f'No data available for {symbol}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for duplicates
        duplicate_count = data.duplicated().sum()
        if duplicate_count > 0:
            issues.append({
                'type': DataIssueType.DUPLICATE_DATA.value,
                'severity': 'medium',
                'description': f'{duplicate_count} duplicate records found for {symbol}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for outliers
        outlier_rate = self._calculate_outlier_rate(data)
        if outlier_rate > 5.0:  # More than 5% outliers
            issues.append({
                'type': DataIssueType.OUTLIER_DATA.value,
                'severity': 'medium',
                'description': f'{outlier_rate:.1f}% outliers detected for {symbol}',
                'timestamp': datetime.now().isoformat()
            })
        
        return issues
    
    def _calculate_quality_score(self, completeness: float, accuracy: float, 
                                consistency: float, timeliness: float,
                                outlier_rate: float, duplicate_rate: float, 
                                gap_count: int) -> float:
        """Calculate overall quality score"""
        # Base score from core metrics
        base_score = (completeness + accuracy + consistency + timeliness) / 4
        
        # Penalties for issues
        outlier_penalty = outlier_rate * 0.5
        duplicate_penalty = duplicate_rate * 0.3
        gap_penalty = min(gap_count * 2, 20)  # Cap at 20 points
        
        final_score = base_score - outlier_penalty - duplicate_penalty - gap_penalty
        
        return max(0, min(100, final_score))  # Clamp between 0 and 100
    
    def _calculate_storage_efficiency(self, data: pd.DataFrame) -> float:
        """Calculate storage efficiency (mock implementation)"""
        # Mock implementation - in real system would check actual storage usage
        return 85.0  # 85% efficiency
    
    def _calculate_retrieval_speed(self) -> float:
        """Calculate retrieval speed (mock implementation)"""
        # Mock implementation - in real system would measure actual retrieval time
        return 50.0  # 50ms average retrieval time
    
    def _get_memory_usage(self) -> float:
        """Get memory usage (mock implementation)"""
        # Mock implementation - in real system would use psutil
        return 512.0  # 512MB
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage (mock implementation)"""
        # Mock implementation - in real system would use psutil
        return 25.0  # 25%
    
    def _get_disk_usage(self) -> float:
        """Get disk usage (mock implementation)"""
        # Mock implementation - in real system would use psutil
        return 60.0  # 60%
    
    def _calculate_performance_score(self, throughput: float, latency: float,
                                   storage_efficiency: float, retrieval_speed: float,
                                   memory_usage: float, cpu_usage: float, 
                                   disk_usage: float) -> float:
        """Calculate overall performance score"""
        # Normalize metrics to 0-100 scale
        throughput_score = min(throughput / 1000, 100)  # Normalize to 1000 pts/sec
        latency_score = max(0, 100 - latency / 10)  # Penalize high latency
        storage_score = storage_efficiency
        retrieval_score = max(0, 100 - retrieval_speed / 2)  # Penalize slow retrieval
        memory_score = max(0, 100 - memory_usage / 10)  # Penalize high memory usage
        cpu_score = max(0, 100 - cpu_usage)  # Penalize high CPU usage
        disk_score = max(0, 100 - disk_usage)  # Penalize high disk usage
        
        # Weighted average
        weights = [0.3, 0.2, 0.1, 0.15, 0.1, 0.1, 0.05]
        scores = [throughput_score, latency_score, storage_score, retrieval_score,
                 memory_score, cpu_score, disk_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _calculate_quality_trend(self, quality_data: List[DataQualityMetrics]) -> str:
        """Calculate quality trend"""
        if len(quality_data) < 2:
            return "insufficient_data"
        
        scores = [q.overall_quality_score for q in quality_data]
        if len(scores) >= 2:
            trend = scores[-1] - scores[0]
            if trend > 5:
                return "improving"
            elif trend < -5:
                return "declining"
            else:
                return "stable"
        
        return "insufficient_data"
    
    def _calculate_performance_trend(self, performance_data: List[MarketDataPerformance]) -> str:
        """Calculate performance trend"""
        if len(performance_data) < 2:
            return "insufficient_data"
        
        scores = [p.overall_performance_score for p in performance_data]
        if len(scores) >= 2:
            trend = scores[-1] - scores[0]
            if trend > 5:
                return "improving"
            elif trend < -5:
                return "declining"
            else:
                return "stable"
        
        return "insufficient_data"
    
    def _generate_recommendations(self, quality_summary: Dict[str, Any], 
                                performance_summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Quality recommendations
        avg_quality = quality_summary.get('avg_quality_score', 0)
        if avg_quality < 80:
            recommendations.append("Consider implementing data validation checks")
        if avg_quality < 90:
            recommendations.append("Review data source reliability and consistency")
        
        # Performance recommendations
        avg_performance = performance_summary.get('avg_performance_score', 0)
        if avg_performance < 80:
            recommendations.append("Optimize data processing pipeline")
        if avg_performance < 90:
            recommendations.append("Consider scaling data infrastructure")
        
        if not recommendations:
            recommendations.append("System performing well - continue monitoring")
        
        return recommendations
    
    def _generate_alerts(self, quality_summary: Dict[str, Any], 
                        performance_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on analysis"""
        alerts = []
        
        # Quality alerts
        avg_quality = quality_summary.get('avg_quality_score', 0)
        if avg_quality < 70:
            alerts.append({
                'level': 'critical',
                'message': f'Data quality critically low: {avg_quality:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        elif avg_quality < 80:
            alerts.append({
                'level': 'warning',
                'message': f'Data quality below threshold: {avg_quality:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        
        # Performance alerts
        avg_performance = performance_summary.get('avg_performance_score', 0)
        if avg_performance < 70:
            alerts.append({
                'level': 'critical',
                'message': f'Performance critically low: {avg_performance:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        elif avg_performance < 80:
            alerts.append({
                'level': 'warning',
                'message': f'Performance below threshold: {avg_performance:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    async def _monitoring_loop(self):
        """Real-time monitoring loop"""
        while self.monitoring_active:
            try:
                # Perform monitoring tasks
                await self._perform_monitoring_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _perform_monitoring_cycle(self):
        """Perform one monitoring cycle"""
        # This would integrate with actual market data sources
        # For now, just log the monitoring cycle
        logger.debug("Performing monitoring cycle")
        
        # Check for alerts
        quality_summary = self.get_quality_summary(days=1)
        performance_summary = self.get_performance_summary(days=1)
        
        alerts = self._generate_alerts(quality_summary, performance_summary)
        for alert in alerts:
            logger.warning(f"Alert: {alert['message']}")
    
    def clear_history(self, days: Optional[int] = None):
        """Clear historical data"""
        if days is None:
            self.quality_history.clear()
            self.performance_history.clear()
            self.issue_history.clear()
        else:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            self.quality_history = [
                q for q in self.quality_history
                if q.timestamp > cutoff_date
            ]
            
            self.performance_history = [
                p for p in self.performance_history
                if p.timestamp > cutoff_date
            ]
            
            self.issue_history = [
                i for i in self.issue_history
                if 'timestamp' in i and datetime.fromisoformat(i['timestamp']) > cutoff_date
            ]
        
        logger.info(f"Cleared historical data (days: {days or 'all'})") 