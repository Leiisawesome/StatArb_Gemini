"""
Data Quality Monitor Module

Real-time data quality monitoring and alerting system for
Phase 6: Market Data & Performance Integration.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from .market_data_analytics import (
    MarketDataAnalytics, DataQualityMetrics, MarketDataPerformance,
    DataQualityLevel, DataIssueType, MarketDataAnalyticsConfig
)

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert level enumeration"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitoringStatus(Enum):
    """Monitoring status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class QualityAlert:
    """Data quality alert"""
    
    # Alert details
    alert_id: str
    level: AlertLevel
    message: str
    symbol: str
    timestamp: datetime
    
    # Alert context
    metric_name: str
    current_value: float
    threshold_value: float
    severity_score: float
    
    # Alert metadata
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'alert_id': self.alert_id,
            'level': self.level.value,
            'message': self.message,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'severity_score': self.severity_score,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'acknowledged_by': self.acknowledged_by,
            'resolved_by': self.resolved_by,
            'resolution_notes': self.resolution_notes
        }


@dataclass
class QualityThreshold:
    """Quality threshold configuration"""
    
    # Threshold values
    completeness_min: float = 95.0
    accuracy_min: float = 98.0
    consistency_min: float = 90.0
    timeliness_min: float = 95.0
    outlier_rate_max: float = 5.0
    duplicate_rate_max: float = 2.0
    gap_count_max: int = 10
    
    # Performance thresholds
    throughput_min: float = 1000.0
    latency_max: float = 100.0
    memory_usage_max: float = 80.0
    cpu_usage_max: float = 80.0
    disk_usage_max: float = 85.0
    
    # Alert thresholds
    quality_score_warning: float = 80.0
    quality_score_critical: float = 70.0
    performance_score_warning: float = 80.0
    performance_score_critical: float = 70.0


@dataclass
class DataQualityMonitorConfig:
    """Configuration for data quality monitor"""
    
    # Monitoring settings
    monitoring_interval_seconds: int = 30
    alert_cooldown_minutes: int = 5
    max_alerts_per_symbol: int = 10
    alert_retention_days: int = 7
    
    # Thresholds
    thresholds: QualityThreshold = field(default_factory=QualityThreshold)
    
    # Notification settings
    enable_email_alerts: bool = False
    enable_slack_alerts: bool = False
    enable_webhook_alerts: bool = False
    
    # Integration settings
    enable_analytics_integration: bool = True
    enable_system_orchestrator_integration: bool = True
    
    # Advanced settings
    enable_anomaly_detection: bool = True
    enable_trend_analysis: bool = True
    enable_auto_resolution: bool = False


class DataQualityMonitor:
    """
    Data Quality Monitor System
    
    Provides real-time monitoring, alerting, and quality management
    for market data across the trading system.
    """
    
    def __init__(self, config: Optional[DataQualityMonitorConfig] = None):
        """
        Initialize Data Quality Monitor
        
        Args:
            config: Configuration for monitor system
        """
        self.config = config or DataQualityMonitorConfig()
        
        # Initialize analytics integration
        if self.config.enable_analytics_integration:
            analytics_config = MarketDataAnalyticsConfig(
                monitoring_interval_seconds=self.config.monitoring_interval_seconds
            )
            self.analytics = MarketDataAnalytics(analytics_config)
        else:
            self.analytics = None
        
        # Initialize monitoring state
        self.status = MonitoringStatus.STOPPED
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Alert management
        self.active_alerts: Dict[str, QualityAlert] = {}
        self.alert_history: List[QualityAlert] = []
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Symbol tracking
        self.monitored_symbols: Set[str] = set()
        self.symbol_quality_history: Dict[str, List[DataQualityMetrics]] = {}
        self.symbol_performance_history: Dict[str, List[MarketDataPerformance]] = {}
        
        # Callback handlers
        self.alert_handlers: List[Callable[[QualityAlert], None]] = []
        self.quality_handlers: List[Callable[[str, DataQualityMetrics], None]] = []
        self.performance_handlers: List[Callable[[str, MarketDataPerformance], None]] = []
        
        logger.info("DataQualityMonitor initialized")
    
    async def start_monitoring(self):
        """Start data quality monitoring"""
        if self.status == MonitoringStatus.ACTIVE:
            logger.warning("Monitoring already active")
            return
        
        self.status = MonitoringStatus.ACTIVE
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start analytics monitoring if enabled
        if self.analytics and self.config.enable_analytics_integration:
            await self.analytics.start_monitoring()
        
        logger.info("Data quality monitoring started")
    
    async def stop_monitoring(self):
        """Stop data quality monitoring"""
        if self.status == MonitoringStatus.STOPPED:
            logger.warning("Monitoring already stopped")
            return
        
        self.status = MonitoringStatus.STOPPED
        
        # Stop monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Stop analytics monitoring if enabled
        if self.analytics and self.config.enable_analytics_integration:
            await self.analytics.stop_monitoring()
        
        logger.info("Data quality monitoring stopped")
    
    async def pause_monitoring(self):
        """Pause data quality monitoring"""
        if self.status != MonitoringStatus.ACTIVE:
            logger.warning("Monitoring not active, cannot pause")
            return
        
        self.status = MonitoringStatus.PAUSED
        logger.info("Data quality monitoring paused")
    
    async def resume_monitoring(self):
        """Resume data quality monitoring"""
        if self.status != MonitoringStatus.PAUSED:
            logger.warning("Monitoring not paused, cannot resume")
            return
        
        self.status = MonitoringStatus.ACTIVE
        logger.info("Data quality monitoring resumed")
    
    def add_symbol(self, symbol: str):
        """Add symbol to monitoring"""
        self.monitored_symbols.add(symbol)
        self.symbol_quality_history[symbol] = []
        self.symbol_performance_history[symbol] = []
        logger.info(f"Added {symbol} to quality monitoring")
    
    def remove_symbol(self, symbol: str):
        """Remove symbol from monitoring"""
        self.monitored_symbols.discard(symbol)
        self.symbol_quality_history.pop(symbol, None)
        self.symbol_performance_history.pop(symbol, None)
        logger.info(f"Removed {symbol} from quality monitoring")
    
    async def process_market_data(self, symbol: str, market_data: pd.DataFrame, 
                                processing_time: float = 0.0):
        """
        Process market data for quality monitoring
        
        Args:
            symbol: Symbol being processed
            market_data: Market data DataFrame
            processing_time: Time taken to process data
        """
        if symbol not in self.monitored_symbols:
            return
        
        try:
            # Analyze data quality
            if self.analytics:
                quality_metrics = await self.analytics.analyze_data_quality(market_data, symbol)
                performance_metrics = await self.analytics.analyze_performance(market_data, processing_time)
                
                # Store in history
                self.symbol_quality_history[symbol].append(quality_metrics)
                self.symbol_performance_history[symbol].append(performance_metrics)
                
                # Check for alerts
                await self._check_quality_alerts(symbol, quality_metrics)
                await self._check_performance_alerts(symbol, performance_metrics)
                
                # Trigger handlers
                for handler in self.quality_handlers:
                    try:
                        handler(symbol, quality_metrics)
                    except Exception as e:
                        logger.error(f"Error in quality handler: {e}")
                
                for handler in self.performance_handlers:
                    try:
                        handler(symbol, performance_metrics)
                    except Exception as e:
                        logger.error(f"Error in performance handler: {e}")
                
                logger.debug(f"Processed market data for {symbol}: quality={quality_metrics.overall_quality_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
            await self._create_system_alert(symbol, f"Data processing error: {e}", AlertLevel.ERROR)
    
    def add_alert_handler(self, handler: Callable[[QualityAlert], None]):
        """Add alert handler callback"""
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def add_quality_handler(self, handler: Callable[[str, DataQualityMetrics], None]):
        """Add quality metrics handler callback"""
        self.quality_handlers.append(handler)
        logger.info("Added quality handler")
    
    def add_performance_handler(self, handler: Callable[[str, MarketDataPerformance], None]):
        """Add performance metrics handler callback"""
        self.performance_handlers.append(handler)
        logger.info("Added performance handler")
    
    def get_active_alerts(self, symbol: Optional[str] = None) -> List[QualityAlert]:
        """Get active alerts"""
        if symbol:
            return [alert for alert in self.active_alerts.values() if alert.symbol == symbol]
        return list(self.active_alerts.values())
    
    def get_alert_history(self, symbol: Optional[str] = None, days: int = 7) -> List[QualityAlert]:
        """Get alert history"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_date
        ]
        
        if symbol:
            filtered_alerts = [alert for alert in filtered_alerts if alert.symbol == symbol]
        
        return filtered_alerts
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
    
    def resolve_alert(self, alert_id: str, resolved_by: str, notes: Optional[str] = None):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_by = resolved_by
            alert.resolution_notes = notes
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
    
    def get_quality_summary(self, symbol: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
        """Get quality summary"""
        if self.analytics:
            return self.analytics.get_quality_summary(symbol, days)
        return {"error": "Analytics not enabled"}
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary"""
        if self.analytics:
            return self.analytics.get_performance_summary(days)
        return {"error": "Analytics not enabled"}
    
    def generate_monitoring_report(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        if not self.analytics:
            return {"error": "Analytics not enabled"}
        
        # Get analytics report
        analytics_report = self.analytics.generate_analytics_report(symbol, days)
        
        # Add monitoring-specific information
        active_alerts = self.get_active_alerts(symbol)
        alert_history = self.get_alert_history(symbol, days)
        
        monitoring_report = {
            'monitoring_status': self.status.value,
            'monitored_symbols': list(self.monitored_symbols),
            'active_alerts_count': len(active_alerts),
            'alert_history_count': len(alert_history),
            'alert_summary': {
                'critical': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
                'error': len([a for a in active_alerts if a.level == AlertLevel.ERROR]),
                'warning': len([a for a in active_alerts if a.level == AlertLevel.WARNING]),
                'info': len([a for a in active_alerts if a.level == AlertLevel.INFO])
            },
            'analytics_report': analytics_report
        }
        
        return monitoring_report
    
    # Private helper methods
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.status == MonitoringStatus.ACTIVE:
            try:
                # Perform monitoring cycle
                await self._perform_monitoring_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.status = MonitoringStatus.ERROR
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _perform_monitoring_cycle(self):
        """Perform one monitoring cycle"""
        logger.debug("Performing monitoring cycle")
        
        # Check for stale alerts
        await self._check_stale_alerts()
        
        # Perform trend analysis if enabled
        if self.config.enable_trend_analysis:
            await self._perform_trend_analysis()
        
        # Perform anomaly detection if enabled
        if self.config.enable_anomaly_detection:
            await self._perform_anomaly_detection()
        
        # Auto-resolve alerts if enabled
        if self.config.enable_auto_resolution:
            await self._auto_resolve_alerts()
    
    async def _check_quality_alerts(self, symbol: str, quality_metrics: DataQualityMetrics):
        """Check for quality alerts"""
        thresholds = self.config.thresholds
        
        # Check completeness
        if quality_metrics.completeness < thresholds.completeness_min:
            await self._create_quality_alert(
                symbol, "completeness", quality_metrics.completeness,
                thresholds.completeness_min, AlertLevel.WARNING
            )
        
        # Check accuracy
        if quality_metrics.accuracy < thresholds.accuracy_min:
            await self._create_quality_alert(
                symbol, "accuracy", quality_metrics.accuracy,
                thresholds.accuracy_min, AlertLevel.WARNING
            )
        
        # Check consistency
        if quality_metrics.consistency < thresholds.consistency_min:
            await self._create_quality_alert(
                symbol, "consistency", quality_metrics.consistency,
                thresholds.consistency_min, AlertLevel.WARNING
            )
        
        # Check timeliness
        if quality_metrics.timeliness < thresholds.timeliness_min:
            await self._create_quality_alert(
                symbol, "timeliness", quality_metrics.timeliness,
                thresholds.timeliness_min, AlertLevel.WARNING
            )
        
        # Check outlier rate
        if quality_metrics.outlier_rate > thresholds.outlier_rate_max:
            await self._create_quality_alert(
                symbol, "outlier_rate", quality_metrics.outlier_rate,
                thresholds.outlier_rate_max, AlertLevel.WARNING
            )
        
        # Check duplicate rate
        if quality_metrics.duplicate_rate > thresholds.duplicate_rate_max:
            await self._create_quality_alert(
                symbol, "duplicate_rate", quality_metrics.duplicate_rate,
                thresholds.duplicate_rate_max, AlertLevel.WARNING
            )
        
        # Check gap count
        if quality_metrics.gap_count > thresholds.gap_count_max:
            await self._create_quality_alert(
                symbol, "gap_count", quality_metrics.gap_count,
                thresholds.gap_count_max, AlertLevel.WARNING
            )
        
        # Check overall quality score
        if quality_metrics.overall_quality_score < thresholds.quality_score_critical:
            await self._create_quality_alert(
                symbol, "overall_quality_score", quality_metrics.overall_quality_score,
                thresholds.quality_score_critical, AlertLevel.CRITICAL
            )
        elif quality_metrics.overall_quality_score < thresholds.quality_score_warning:
            await self._create_quality_alert(
                symbol, "overall_quality_score", quality_metrics.overall_quality_score,
                thresholds.quality_score_warning, AlertLevel.WARNING
            )
    
    async def _check_performance_alerts(self, symbol: str, performance_metrics: MarketDataPerformance):
        """Check for performance alerts"""
        thresholds = self.config.thresholds
        
        # Check throughput
        if performance_metrics.data_throughput < thresholds.throughput_min:
            await self._create_performance_alert(
                symbol, "data_throughput", performance_metrics.data_throughput,
                thresholds.throughput_min, AlertLevel.WARNING
            )
        
        # Check latency
        if performance_metrics.processing_latency > thresholds.latency_max:
            await self._create_performance_alert(
                symbol, "processing_latency", performance_metrics.processing_latency,
                thresholds.latency_max, AlertLevel.WARNING
            )
        
        # Check memory usage
        if performance_metrics.memory_usage > thresholds.memory_usage_max:
            await self._create_performance_alert(
                symbol, "memory_usage", performance_metrics.memory_usage,
                thresholds.memory_usage_max, AlertLevel.WARNING
            )
        
        # Check CPU usage
        if performance_metrics.cpu_usage > thresholds.cpu_usage_max:
            await self._create_performance_alert(
                symbol, "cpu_usage", performance_metrics.cpu_usage,
                thresholds.cpu_usage_max, AlertLevel.WARNING
            )
        
        # Check disk usage
        if performance_metrics.disk_usage > thresholds.disk_usage_max:
            await self._create_performance_alert(
                symbol, "disk_usage", performance_metrics.disk_usage,
                thresholds.disk_usage_max, AlertLevel.WARNING
            )
        
        # Check overall performance score
        if performance_metrics.overall_performance_score < thresholds.performance_score_critical:
            await self._create_performance_alert(
                symbol, "overall_performance_score", performance_metrics.overall_performance_score,
                thresholds.performance_score_critical, AlertLevel.CRITICAL
            )
        elif performance_metrics.overall_performance_score < thresholds.performance_score_warning:
            await self._create_performance_alert(
                symbol, "overall_performance_score", performance_metrics.overall_performance_score,
                thresholds.performance_score_warning, AlertLevel.WARNING
            )
    
    async def _create_quality_alert(self, symbol: str, metric_name: str, current_value: float,
                                  threshold_value: float, level: AlertLevel):
        """Create quality alert"""
        alert_id = f"quality_{symbol}_{metric_name}_{datetime.now().timestamp()}"
        
        # Check cooldown
        if self._is_in_cooldown(alert_id):
            return
        
        # Check max alerts per symbol
        symbol_alerts = [a for a in self.active_alerts.values() if a.symbol == symbol]
        if len(symbol_alerts) >= self.config.max_alerts_per_symbol:
            return
        
        # Calculate severity score
        severity_score = self._calculate_severity_score(current_value, threshold_value, metric_name)
        
        # Create alert
        alert = QualityAlert(
            alert_id=alert_id,
            level=level,
            message=f"{metric_name} for {symbol} is {current_value:.2f} (threshold: {threshold_value:.2f})",
            symbol=symbol,
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            severity_score=severity_score
        )
        
        # Add to active alerts
        self.active_alerts[alert_id] = alert
        self.alert_cooldowns[alert_id] = datetime.now()
        
        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.warning(f"Quality alert created: {alert.message}")
    
    async def _create_performance_alert(self, symbol: str, metric_name: str, current_value: float,
                                      threshold_value: float, level: AlertLevel):
        """Create performance alert"""
        alert_id = f"performance_{symbol}_{metric_name}_{datetime.now().timestamp()}"
        
        # Check cooldown
        if self._is_in_cooldown(alert_id):
            return
        
        # Check max alerts per symbol
        symbol_alerts = [a for a in self.active_alerts.values() if a.symbol == symbol]
        if len(symbol_alerts) >= self.config.max_alerts_per_symbol:
            return
        
        # Calculate severity score
        severity_score = self._calculate_severity_score(current_value, threshold_value, metric_name)
        
        # Create alert
        alert = QualityAlert(
            alert_id=alert_id,
            level=level,
            message=f"{metric_name} for {symbol} is {current_value:.2f} (threshold: {threshold_value:.2f})",
            symbol=symbol,
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            severity_score=severity_score
        )
        
        # Add to active alerts
        self.active_alerts[alert_id] = alert
        self.alert_cooldowns[alert_id] = datetime.now()
        
        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.warning(f"Performance alert created: {alert.message}")
    
    async def _create_system_alert(self, symbol: str, message: str, level: AlertLevel):
        """Create system alert"""
        alert_id = f"system_{symbol}_{datetime.now().timestamp()}"
        
        # Check cooldown
        if self._is_in_cooldown(alert_id):
            return
        
        # Create alert
        alert = QualityAlert(
            alert_id=alert_id,
            level=level,
            message=message,
            symbol=symbol,
            timestamp=datetime.now(),
            metric_name="system_error",
            current_value=0.0,
            threshold_value=0.0,
            severity_score=1.0
        )
        
        # Add to active alerts
        self.active_alerts[alert_id] = alert
        self.alert_cooldowns[alert_id] = datetime.now()
        
        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.error(f"System alert created: {message}")
    
    def _is_in_cooldown(self, alert_id: str) -> bool:
        """Check if alert is in cooldown period"""
        if alert_id in self.alert_cooldowns:
            cooldown_time = self.alert_cooldowns[alert_id]
            cooldown_duration = timedelta(minutes=self.config.alert_cooldown_minutes)
            return datetime.now() - cooldown_time < cooldown_duration
        return False
    
    def _calculate_severity_score(self, current_value: float, threshold_value: float, 
                                metric_name: str) -> float:
        """Calculate alert severity score"""
        # Normalize to 0-1 scale based on how far the value is from threshold
        if metric_name in ['completeness', 'accuracy', 'consistency', 'timeliness', 
                          'overall_quality_score', 'overall_performance_score']:
            # Higher is better
            if current_value >= threshold_value:
                return 0.0
            else:
                return min(1.0, (threshold_value - current_value) / threshold_value)
        else:
            # Lower is better
            if current_value <= threshold_value:
                return 0.0
            else:
                return min(1.0, (current_value - threshold_value) / threshold_value)
    
    async def _check_stale_alerts(self):
        """Check for stale alerts and clean them up"""
        current_time = datetime.now()
        stale_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            # Consider alerts stale after 24 hours
            if current_time - alert.timestamp > timedelta(hours=24):
                stale_alerts.append(alert_id)
        
        # Move stale alerts to history
        for alert_id in stale_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_by = "system"
            alert.resolution_notes = "Auto-resolved due to staleness"
            
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            logger.info(f"Stale alert {alert_id} auto-resolved")
    
    async def _perform_trend_analysis(self):
        """Perform trend analysis on quality metrics"""
        for symbol in self.monitored_symbols:
            if symbol in self.symbol_quality_history:
                quality_history = self.symbol_quality_history[symbol]
                
                if len(quality_history) >= 5:  # Need at least 5 data points
                    # Calculate trend
                    recent_scores = [q.overall_quality_score for q in quality_history[-5:]]
                    trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                    
                    # Alert on declining trend
                    if trend < -2.0:  # Declining by more than 2 points per cycle
                        await self._create_system_alert(
                            symbol, f"Quality trend declining: {trend:.2f} points per cycle", 
                            AlertLevel.WARNING
                        )
    
    async def _perform_anomaly_detection(self):
        """Perform anomaly detection on quality metrics"""
        for symbol in self.monitored_symbols:
            if symbol in self.symbol_quality_history:
                quality_history = self.symbol_quality_history[symbol]
                
                if len(quality_history) >= 10:  # Need at least 10 data points
                    # Calculate anomaly score using simple statistical method
                    scores = [q.overall_quality_score for q in quality_history[-10:]]
                    mean_score = np.mean(scores)
                    std_score = np.std(scores)
                    
                    if std_score > 0:  # Avoid division by zero
                        latest_score = scores[-1]
                        z_score = abs(latest_score - mean_score) / std_score
                        
                        # Alert on significant anomaly
                        if z_score > 2.0:  # More than 2 standard deviations
                            await self._create_system_alert(
                                symbol, f"Quality anomaly detected: z-score {z_score:.2f}", 
                                AlertLevel.WARNING
                            )
    
    async def _auto_resolve_alerts(self):
        """Auto-resolve alerts based on conditions"""
        current_time = datetime.now()
        alerts_to_resolve = []
        
        for alert_id, alert in self.active_alerts.items():
            # Auto-resolve if metric has improved
            if alert.metric_name in ['completeness', 'accuracy', 'consistency', 'timeliness']:
                if symbol in self.symbol_quality_history:
                    latest_quality = self.symbol_quality_history[symbol][-1]
                    current_value = getattr(latest_quality, alert.metric_name, 0)
                    
                    if current_value >= alert.threshold_value:
                        alerts_to_resolve.append(alert_id)
        
        # Resolve alerts
        for alert_id in alerts_to_resolve:
            self.resolve_alert(alert_id, "system", "Auto-resolved due to metric improvement")
    
    def clear_history(self, days: Optional[int] = None):
        """Clear historical data"""
        if days is None:
            self.alert_history.clear()
            for symbol in self.symbol_quality_history:
                self.symbol_quality_history[symbol].clear()
            for symbol in self.symbol_performance_history:
                self.symbol_performance_history[symbol].clear()
        else:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clear alert history
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.timestamp > cutoff_date
            ]
            
            # Clear quality history
            for symbol in self.symbol_quality_history:
                self.symbol_quality_history[symbol] = [
                    q for q in self.symbol_quality_history[symbol]
                    if hasattr(q, 'timestamp') and q.timestamp > cutoff_date
                ]
            
            # Clear performance history
            for symbol in self.symbol_performance_history:
                self.symbol_performance_history[symbol] = [
                    p for p in self.symbol_performance_history[symbol]
                    if p.timestamp > cutoff_date
                ]
        
        logger.info(f"Cleared historical data (days: {days or 'all'})") 