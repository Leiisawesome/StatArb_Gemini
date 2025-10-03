#!/usr/bin/env python3
"""
Performance Monitor - Core Engine
=================================

Clean implementation of the performance monitor for core_engine.
This component provides real-time analytics, performance tracking, and reporting.

As a supporting component in the institutional architecture:
- Monitors system-wide performance metrics
- Tracks strategy and portfolio performance
- Generates real-time analytics and reports
- Provides alerting and notification capabilities

Migration: Direct implementation using proven analytics patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production - Analytics)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

# Leverage existing high-quality analytics components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ..performance_analyzer import PerformanceAnalyzer
from ..manager_enhanced import EnhancedAnalyticsManager

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MetricType(Enum):
    """Performance metric types"""
    SYSTEM = "system"
    STRATEGY = "strategy"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    EXECUTION = "execution"
    BROKER = "broker"

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    metric_id: str
    metric_type: MetricType
    name: str
    value: float
    unit: str
    timestamp: datetime
    component: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    severity: AlertSeverity
    component: str
    metric_name: str
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemHealthStatus:
    """System health status"""
    overall_health: float  # 0.0 to 1.0
    component_health: Dict[str, float]
    active_alerts: int
    critical_alerts: int
    last_updated: datetime
    uptime_seconds: float

@dataclass
class PerformanceReport:
    """Performance report"""
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    metrics: List[PerformanceMetric]
    summary: Dict[str, Any]
    generated_at: datetime

@dataclass
class PerformanceMonitorConfig:
    """Performance monitor configuration"""
    monitoring_interval: int = 30  # seconds
    metrics_retention_days: int = 30
    enable_real_time_alerts: bool = True
    enable_health_monitoring: bool = True
    alert_cooldown_minutes: int = 5
    report_generation_interval: int = 3600  # 1 hour
    system_health_threshold: float = 0.8

class IPerformanceSubscriber:
    """Interface for performance event subscribers"""
    
    async def on_metric_update(self, metric: PerformanceMetric) -> None:
        """Handle metric updates"""
    
    async def on_alert_generated(self, alert: PerformanceAlert) -> None:
        """Handle alert generation"""
    
    async def on_health_status_change(self, status: SystemHealthStatus) -> None:
        """Handle health status changes"""

class PerformanceMonitor:
    """
    Core Engine Performance Monitor
    
    This component provides comprehensive performance monitoring:
    
    1. Tracks system-wide performance metrics
    2. Monitors all component health and performance
    3. Generates alerts for performance anomalies
    4. Creates periodic performance reports
    5. Provides real-time analytics dashboard data
    
    The performance monitoring includes:
    - Real-time metric collection
    - Health status aggregation
    - Alert generation and management
    - Historical performance tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = PerformanceMonitorConfig(**config) if config else PerformanceMonitorConfig()
        
        # Component references
        self.core_engine: Optional[Any] = None
        self.risk_manager: Optional[Any] = None
        self.portfolio_manager: Optional[Any] = None
        self.broker_manager: Optional[Any] = None
        
        # Performance data
        self.metrics: Dict[str, List[PerformanceMetric]] = {}
        self.alerts: Dict[str, PerformanceAlert] = {}
        self.alert_history: List[PerformanceAlert] = []
        
        # System health
        self.system_health: SystemHealthStatus = SystemHealthStatus(
            overall_health=1.0,
            component_health={},
            active_alerts=0,
            critical_alerts=0,
            last_updated=datetime.now(),
            uptime_seconds=0.0
        )
        
        # Performance tracking
        self.start_time: datetime = datetime.now()
        self.component_metrics: Dict[str, Dict[str, Any]] = {}
        self.performance_reports: List[PerformanceReport] = []
        
        # Alert tracking
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Subscribers
        self.subscribers: List[IPerformanceSubscriber] = []
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.reporting_task: Optional[asyncio.Task] = None
        
        # Leverage existing analytics engines
        self.core_analytics: Optional[PerformanceAnalyzer] = None
        self.monitoring_analytics: Optional[EnhancedAnalyticsManager] = None
        
        logger.info("📊 Performance Monitor initialized")
    
    async def initialize(self) -> bool:
        """Initialize performance monitor"""
        try:
            logger.info("🔄 Initializing Performance Monitor...")
            
            # Initialize analytics engines
            self.core_analytics = PerformanceAnalyzer()
            self.monitoring_analytics = EnhancedAnalyticsManager()
            
            # Initialize metric collections
            for metric_type in MetricType:
                self.metrics[metric_type.value] = []
            
            # Record start time
            self.start_time = datetime.now()
            
            self.is_initialized = True
            logger.info("✅ Performance Monitor initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Performance Monitor initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start performance monitor"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Performance Monitor not initialized")
            
            logger.info("🚀 Starting Performance Monitor...")
            
            # Start monitoring tasks
            self.monitoring_task = asyncio.create_task(self._run_performance_monitoring())
            self.reporting_task = asyncio.create_task(self._run_report_generation())
            
            self.is_running = True
            logger.info("✅ Performance Monitor started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Performance Monitor: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop performance monitor"""
        try:
            logger.info("🛑 Stopping Performance Monitor...")
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            if self.reporting_task:
                self.reporting_task.cancel()
                try:
                    await self.reporting_task
                except asyncio.CancelledError:
                    pass
                self.reporting_task = None
            
            # Generate final report
            await self._generate_performance_report("final")
            
            self.is_running = False
            logger.info("✅ Performance Monitor stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Performance Monitor: {e}")
            return False
    
    # Component Integration
    def set_core_engine(self, core_engine: Any):
        """Set core engine reference"""
        self.core_engine = core_engine
        logger.info("🔗 Core Engine linked to Performance Monitor")
    
    def set_risk_manager(self, risk_manager: Any):
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info("🔗 Risk Manager linked to Performance Monitor")
    
    def set_portfolio_manager(self, portfolio_manager: Any):
        """Set portfolio manager reference"""
        self.portfolio_manager = portfolio_manager
        logger.info("🔗 Portfolio Manager linked to Performance Monitor")
    
    def set_broker_manager(self, broker_manager: Any):
        """Set broker manager reference"""
        self.broker_manager = broker_manager
        logger.info("🔗 Broker Manager linked to Performance Monitor")
    
    def subscribe(self, subscriber: IPerformanceSubscriber):
        """Subscribe to performance events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New performance subscriber: {type(subscriber).__name__}")
    
    # Core Performance Methods
    async def record_metric(self, metric: PerformanceMetric) -> None:
        """Record performance metric"""
        try:
            # Store metric
            metric_type = metric.metric_type.value
            if metric_type not in self.metrics:
                self.metrics[metric_type] = []
            
            self.metrics[metric_type].append(metric)
            
            # Limit retention
            cutoff_date = datetime.now() - timedelta(days=self.config.metrics_retention_days)
            self.metrics[metric_type] = [
                m for m in self.metrics[metric_type] 
                if m.timestamp > cutoff_date
            ]
            
            # Check for alerts
            await self._check_metric_alerts(metric)
            
            # Notify subscribers
            for subscriber in self.subscribers:
                await subscriber.on_metric_update(metric)
                
        except Exception as e:
            logger.error(f"❌ Failed to record metric: {e}")
    
    async def generate_alert(self, alert: PerformanceAlert) -> None:
        """Generate performance alert"""
        try:
            # Check cooldown
            cooldown_key = f"{alert.component}_{alert.metric_name}"
            if cooldown_key in self.alert_cooldowns:
                if datetime.now() - self.alert_cooldowns[cooldown_key] < timedelta(minutes=self.config.alert_cooldown_minutes):
                    return
            
            # Store alert
            self.alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            self.alert_cooldowns[cooldown_key] = datetime.now()
            
            # Update system health
            await self._update_system_health()
            
            # Notify subscribers
            for subscriber in self.subscribers:
                await subscriber.on_alert_generated(alert)
            
            logger.warning(f"🚨 Alert generated: {alert.component} - {alert.message}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate alert: {e}")
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge alert"""
        try:
            if alert_id in self.alerts:
                self.alerts[alert_id].acknowledged = True
                await self._update_system_health()
                logger.info(f"✅ Alert acknowledged: {alert_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to acknowledge alert: {e}")
            return False
    
    async def get_system_health(self) -> SystemHealthStatus:
        """Get current system health status"""
        return self.system_health
    
    async def get_component_metrics(self, component: str, metric_type: Optional[MetricType] = None) -> List[PerformanceMetric]:
        """Get metrics for specific component"""
        all_metrics = []
        
        if metric_type:
            metrics_list = self.metrics.get(metric_type.value, [])
        else:
            metrics_list = []
            for metric_list in self.metrics.values():
                metrics_list.extend(metric_list)
        
        return [m for m in metrics_list if m.component == component]
    
    async def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[PerformanceAlert]:
        """Get active alerts"""
        active_alerts = [alert for alert in self.alerts.values() if not alert.acknowledged]
        
        if severity:
            active_alerts = [alert for alert in active_alerts if alert.severity == severity]
        
        return sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)
    
    async def get_performance_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            uptime = (datetime.now() - self.start_time).total_seconds()
            
            # Count metrics
            total_metrics = sum(len(metrics) for metrics in self.metrics.values())
            
            # Count alerts by severity
            active_alerts = await self.get_active_alerts()
            alert_counts = {}
            for severity in AlertSeverity:
                alert_counts[severity.value] = len([a for a in active_alerts if a.severity == severity])
            
            summary = {
                'uptime_seconds': uptime,
                'uptime_human': str(timedelta(seconds=int(uptime))),
                'system_health': self.system_health.overall_health,
                'total_metrics': total_metrics,
                'active_alerts': len(active_alerts),
                'alert_breakdown': alert_counts,
                'component_health': self.system_health.component_health,
                'last_updated': datetime.now()
            }
            
            # Add component-specific data
            if component:
                component_metrics = await self.get_component_metrics(component)
                summary['component_metrics'] = len(component_metrics)
                summary['component_alerts'] = len([a for a in active_alerts if a.component == component])
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance summary: {e}")
            return {}
    
    # Monitoring Implementation Methods
    async def _run_performance_monitoring(self):
        """Run continuous performance monitoring"""
        logger.info("📊 Starting performance monitoring...")
        
        while self.is_running:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect component metrics
                await self._collect_component_metrics()
                
                # Update system health
                await self._update_system_health()
                
                await asyncio.sleep(self.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Performance monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            current_time = datetime.now()
            
            # System uptime
            uptime = (current_time - self.start_time).total_seconds()
            await self.record_metric(PerformanceMetric(
                metric_id=str(uuid.uuid4()),
                metric_type=MetricType.SYSTEM,
                name="uptime",
                value=uptime,
                unit="seconds",
                timestamp=current_time,
                component="system"
            ))
            
            # Memory usage (simplified)
            import psutil
            memory_usage = psutil.virtual_memory().percent
            await self.record_metric(PerformanceMetric(
                metric_id=str(uuid.uuid4()),
                metric_type=MetricType.SYSTEM,
                name="memory_usage",
                value=memory_usage,
                unit="percent",
                timestamp=current_time,
                component="system"
            ))
            
            # CPU usage
            cpu_usage = psutil.cpu_percent()
            await self.record_metric(PerformanceMetric(
                metric_id=str(uuid.uuid4()),
                metric_type=MetricType.SYSTEM,
                name="cpu_usage",
                value=cpu_usage,
                unit="percent",
                timestamp=current_time,
                component="system"
            ))
            
        except Exception as e:
            logger.error(f"❌ System metrics collection failed: {e}")
    
    async def _collect_component_metrics(self):
        """Collect component-specific metrics"""
        try:
            current_time = datetime.now()
            
            # Risk Manager metrics
            if self.risk_manager:
                risk_status = self.risk_manager.get_risk_status()
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.RISK,
                    name="active_positions",
                    value=risk_status.get('active_positions', 0),
                    unit="count",
                    timestamp=current_time,
                    component="risk_manager"
                ))
                
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.RISK,
                    name="daily_var_utilization",
                    value=risk_status.get('daily_var_utilization', 0),
                    unit="ratio",
                    timestamp=current_time,
                    component="risk_manager"
                ))
            
            # Portfolio Manager metrics
            if self.portfolio_manager:
                portfolio_status = self.portfolio_manager.get_portfolio_status()
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.PORTFOLIO,
                    name="open_positions",
                    value=portfolio_status.get('open_positions', 0),
                    unit="count",
                    timestamp=current_time,
                    component="portfolio_manager"
                ))
                
                # Portfolio value
                portfolio_value = await self.portfolio_manager.get_portfolio_value()
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.PORTFOLIO,
                    name="portfolio_value",
                    value=portfolio_value,
                    unit="currency",
                    timestamp=current_time,
                    component="portfolio_manager"
                ))
            
            # Broker Manager metrics
            if self.broker_manager:
                broker_status = self.broker_manager.get_broker_manager_status()
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.BROKER,
                    name="connection_rate",
                    value=broker_status.get('connection_rate', 0),
                    unit="ratio",
                    timestamp=current_time,
                    component="broker_manager"
                ))
                
                await self.record_metric(PerformanceMetric(
                    metric_id=str(uuid.uuid4()),
                    metric_type=MetricType.BROKER,
                    name="active_orders",
                    value=broker_status.get('active_orders', 0),
                    unit="count",
                    timestamp=current_time,
                    component="broker_manager"
                ))
                
        except Exception as e:
            logger.error(f"❌ Component metrics collection failed: {e}")
    
    async def _check_metric_alerts(self, metric: PerformanceMetric):
        """Check if metric triggers any alerts"""
        try:
            # Define alert thresholds
            alert_thresholds = {
                'memory_usage': {'threshold': 80.0, 'severity': AlertSeverity.HIGH},
                'cpu_usage': {'threshold': 90.0, 'severity': AlertSeverity.HIGH},
                'daily_var_utilization': {'threshold': 0.8, 'severity': AlertSeverity.MEDIUM},
                'connection_rate': {'threshold': 0.5, 'severity': AlertSeverity.HIGH}
            }
            
            if metric.name in alert_thresholds:
                config = alert_thresholds[metric.name]
                threshold = config['threshold']
                
                # Check if threshold exceeded
                if (metric.name in ['memory_usage', 'cpu_usage', 'daily_var_utilization'] and metric.value > threshold) or \
                   (metric.name == 'connection_rate' and metric.value < threshold):
                    
                    alert = PerformanceAlert(
                        alert_id=str(uuid.uuid4()),
                        severity=config['severity'],
                        component=metric.component,
                        metric_name=metric.name,
                        message=f"{metric.name} threshold exceeded: {metric.value} (threshold: {threshold})",
                        threshold=threshold,
                        current_value=metric.value,
                        timestamp=datetime.now()
                    )
                    
                    await self.generate_alert(alert)
                    
        except Exception as e:
            logger.error(f"❌ Alert check failed: {e}")
    
    async def _update_system_health(self):
        """Update overall system health status"""
        try:
            # Count alerts by severity
            active_alerts = await self.get_active_alerts()
            critical_alerts = len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL])
            high_alerts = len([a for a in active_alerts if a.severity == AlertSeverity.HIGH])
            
            # Calculate component health
            component_health = {}
            components = ['system', 'risk_manager', 'portfolio_manager', 'broker_manager']
            
            for component in components:
                component_alerts = [a for a in active_alerts if a.component == component]
                if not component_alerts:
                    component_health[component] = 1.0
                else:
                    # Reduce health based on alert severity
                    health_reduction = 0
                    for alert in component_alerts:
                        if alert.severity == AlertSeverity.CRITICAL:
                            health_reduction += 0.5
                        elif alert.severity == AlertSeverity.HIGH:
                            health_reduction += 0.3
                        elif alert.severity == AlertSeverity.MEDIUM:
                            health_reduction += 0.1
                    
                    component_health[component] = max(0.0, 1.0 - health_reduction)
            
            # Calculate overall health
            if component_health:
                overall_health = np.mean(list(component_health.values()))
            else:
                overall_health = 1.0
            
            # Update system health
            self.system_health = SystemHealthStatus(
                overall_health=overall_health,
                component_health=component_health,
                active_alerts=len(active_alerts),
                critical_alerts=critical_alerts,
                last_updated=datetime.now(),
                uptime_seconds=(datetime.now() - self.start_time).total_seconds()
            )
            
            # Notify subscribers if health changed significantly
            if overall_health < self.config.system_health_threshold:
                for subscriber in self.subscribers:
                    await subscriber.on_health_status_change(self.system_health)
                    
        except Exception as e:
            logger.error(f"❌ System health update failed: {e}")
    
    # Reporting Methods
    async def _run_report_generation(self):
        """Run periodic report generation"""
        logger.info("📄 Starting periodic report generation...")
        
        while self.is_running:
            try:
                await self._generate_performance_report("periodic")
                await asyncio.sleep(self.config.report_generation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Report generation error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _generate_performance_report(self, report_type: str):
        """Generate performance report"""
        try:
            period_end = datetime.now()
            period_start = period_end - timedelta(hours=1)  # Last hour
            
            # Collect metrics for period
            period_metrics = []
            for metric_list in self.metrics.values():
                period_metrics.extend([
                    m for m in metric_list 
                    if period_start <= m.timestamp <= period_end
                ])
            
            # Generate summary
            summary = await self.get_performance_summary()
            
            report = PerformanceReport(
                report_id=str(uuid.uuid4()),
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                metrics=period_metrics,
                summary=summary,
                generated_at=datetime.now()
            )
            
            self.performance_reports.append(report)
            
            # Keep only last 100 reports
            if len(self.performance_reports) > 100:
                self.performance_reports = self.performance_reports[-100:]
            
            logger.info(f"📄 Performance report generated: {report_type} ({len(period_metrics)} metrics)")
            
        except Exception as e:
            logger.error(f"❌ Performance report generation failed: {e}")
    
    def get_performance_monitor_status(self) -> Dict[str, Any]:
        """Get comprehensive performance monitor status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'total_metrics': sum(len(metrics) for metrics in self.metrics.values()),
            'active_alerts': len([a for a in self.alerts.values() if not a.acknowledged]),
            'total_alerts': len(self.alert_history),
            'system_health': self.system_health.overall_health,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'performance_reports': len(self.performance_reports),
            'monitoring_interval': self.config.monitoring_interval,
            'components_linked': {
                'core_engine': self.core_engine is not None,
                'risk_manager': self.risk_manager is not None,
                'portfolio_manager': self.portfolio_manager is not None,
                'broker_manager': self.broker_manager is not None
            }
        }