"""
Strategy Monitor

Real-time strategy performance monitoring and alerting system.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from strategy_layer.base import StrategyConfig, StrategyType, StrategyStatus
from ..deployment import DeploymentInfo, DeploymentStatus


class MonitorStatus(Enum):
    """Monitor status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AlertLevel(Enum):
    """Alert level enumeration"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MonitoringConfig:
    """Configuration for strategy monitoring"""
    monitoring_interval: int = 30  # seconds
    performance_thresholds: Dict[str, float] = field(default_factory=dict)
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    max_alert_history: int = 1000
    enable_performance_tracking: bool = True
    enable_health_monitoring: bool = True
    enable_resource_monitoring: bool = True
    enable_alerting: bool = True
    alert_channels: List[str] = field(default_factory=list)
    data_retention_days: int = 30


@dataclass
class PerformanceMetrics:
    """Strategy performance metrics"""
    strategy_id: str
    timestamp: datetime
    execution_time: float
    success_rate: float
    error_rate: float
    total_executions: int
    success_count: int
    error_count: int
    memory_usage: float
    cpu_usage: float
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Strategy health status"""
    strategy_id: str
    timestamp: datetime
    is_healthy: bool
    health_score: float
    last_execution: datetime
    uptime: float
    restart_count: int
    error_details: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """Monitoring alert"""
    alert_id: str
    strategy_id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_name: str
    metric_value: float
    threshold: float
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class StrategyMonitor:
    """Main strategy monitoring and alerting system"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.status = MonitorStatus.STOPPED
        self.monitoring_task: Optional[asyncio.Task] = None
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.health_history: Dict[str, List[HealthStatus]] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.monitored_strategies: Dict[str, DeploymentInfo] = {}
        self.alert_handlers: List[Callable] = []
        
        # Setup default thresholds
        self._setup_default_thresholds()
    
    def _setup_default_thresholds(self):
        """Setup default monitoring thresholds"""
        if not self.config.performance_thresholds:
            self.config.performance_thresholds = {
                'max_execution_time': 1.0,  # seconds
                'min_success_rate': 0.9,    # 90%
                'max_error_rate': 0.1,      # 10%
                'max_memory_usage': 0.8,    # 80%
                'max_cpu_usage': 0.9        # 90%
            }
        
        if not self.config.alert_thresholds:
            self.config.alert_thresholds = {
                'execution_time_warning': 0.5,   # seconds
                'execution_time_critical': 1.0,  # seconds
                'success_rate_warning': 0.95,    # 95%
                'success_rate_critical': 0.9,    # 90%
                'error_rate_warning': 0.05,      # 5%
                'error_rate_critical': 0.1,      # 10%
                'memory_usage_warning': 0.7,     # 70%
                'memory_usage_critical': 0.8,    # 80%
                'cpu_usage_warning': 0.8,        # 80%
                'cpu_usage_critical': 0.9        # 90%
            }
    
    async def start(self):
        """Start the monitoring system"""
        self.logger.info("Starting Strategy Monitor")
        self.status = MonitorStatus.ACTIVE
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Strategy Monitor started successfully")
    
    async def stop(self):
        """Stop the monitoring system"""
        self.logger.info("Stopping Strategy Monitor")
        self.status = MonitorStatus.STOPPED
        
        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
        
        self.logger.info("Strategy Monitor stopped")
    
    def add_strategy(self, deployment_info: DeploymentInfo):
        """Add a strategy to monitoring"""
        strategy_id = deployment_info.strategy_id
        self.monitored_strategies[strategy_id] = deployment_info
        
        # Initialize history
        if strategy_id not in self.performance_history:
            self.performance_history[strategy_id] = []
        if strategy_id not in self.health_history:
            self.health_history[strategy_id] = []
        
        self.logger.info(f"Added strategy {strategy_id} to monitoring")
    
    def remove_strategy(self, strategy_id: str):
        """Remove a strategy from monitoring"""
        if strategy_id in self.monitored_strategies:
            del self.monitored_strategies[strategy_id]
        
        # Clean up history
        if strategy_id in self.performance_history:
            del self.performance_history[strategy_id]
        if strategy_id in self.health_history:
            del self.health_history[strategy_id]
        
        # Resolve active alerts
        alerts_to_resolve = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.strategy_id == strategy_id
        ]
        for alert_id in alerts_to_resolve:
            self._resolve_alert(alert_id, "Strategy removed from monitoring")
        
        self.logger.info(f"Removed strategy {strategy_id} from monitoring")
    
    def add_alert_handler(self, handler: Callable):
        """Add an alert handler"""
        self.alert_handlers.append(handler)
        self.logger.info("Added alert handler")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.status == MonitorStatus.ACTIVE:
            try:
                # Monitor all strategies
                for strategy_id, deployment_info in self.monitored_strategies.items():
                    if deployment_info.status == DeploymentStatus.ACTIVE:
                        await self._monitor_strategy(strategy_id, deployment_info)
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.config.monitoring_interval)
    
    async def _monitor_strategy(self, strategy_id: str, deployment_info: DeploymentInfo):
        """Monitor a single strategy"""
        try:
            # Collect performance metrics
            if self.config.enable_performance_tracking:
                metrics = await self._collect_performance_metrics(strategy_id, deployment_info)
                self._store_performance_metrics(metrics)
                await self._check_performance_alerts(metrics)
            
            # Check health status
            if self.config.enable_health_monitoring:
                health_status = await self._check_health_status(strategy_id, deployment_info)
                self._store_health_status(health_status)
                await self._check_health_alerts(health_status)
            
            # Monitor resources
            if self.config.enable_resource_monitoring:
                await self._monitor_resources(strategy_id, deployment_info)
            
        except Exception as e:
            self.logger.error(f"Error monitoring strategy {strategy_id}: {e}")
    
    async def _collect_performance_metrics(self, strategy_id: str, deployment_info: DeploymentInfo) -> PerformanceMetrics:
        """Collect performance metrics for a strategy"""
        now = datetime.now()
        
        # Calculate metrics from deployment info
        total_executions = deployment_info.total_executions
        success_count = deployment_info.success_count
        error_count = deployment_info.error_count
        
        success_rate = success_count / total_executions if total_executions > 0 else 0.0
        error_rate = error_count / total_executions if total_executions > 0 else 0.0
        
        # Get resource usage
        resource_usage = deployment_info.resource_usage
        memory_usage = resource_usage.get('memory_usage', 0.0)
        cpu_usage = resource_usage.get('cpu_usage', 0.0)
        
        # Estimate execution time (placeholder)
        execution_time = 0.1  # This would be calculated from actual execution data
        
        metrics = PerformanceMetrics(
            strategy_id=strategy_id,
            timestamp=now,
            execution_time=execution_time,
            success_rate=success_rate,
            error_rate=error_rate,
            total_executions=total_executions,
            success_count=success_count,
            error_count=error_count,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            custom_metrics={
                'restart_count': deployment_info.restart_count,
                'uptime': (now - deployment_info.deployment_time).total_seconds()
            }
        )
        
        return metrics
    
    def _store_performance_metrics(self, metrics: PerformanceMetrics):
        """Store performance metrics in history"""
        strategy_id = metrics.strategy_id
        
        if strategy_id not in self.performance_history:
            self.performance_history[strategy_id] = []
        
        self.performance_history[strategy_id].append(metrics)
        
        # Clean up old data
        cutoff_time = datetime.now() - timedelta(days=self.config.data_retention_days)
        self.performance_history[strategy_id] = [
            m for m in self.performance_history[strategy_id]
            if m.timestamp > cutoff_time
        ]
    
    async def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance-based alerts"""
        if not self.config.enable_alerting:
            return
        
        # Check execution time
        if metrics.execution_time > self.config.alert_thresholds.get('execution_time_critical', 1.0):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.CRITICAL,
                f"Execution time critical: {metrics.execution_time:.2f}s",
                'execution_time',
                metrics.execution_time,
                self.config.alert_thresholds.get('execution_time_critical', 1.0)
            )
        elif metrics.execution_time > self.config.alert_thresholds.get('execution_time_warning', 0.5):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.WARNING,
                f"Execution time high: {metrics.execution_time:.2f}s",
                'execution_time',
                metrics.execution_time,
                self.config.alert_thresholds.get('execution_time_warning', 0.5)
            )
        
        # Check success rate
        if metrics.success_rate < self.config.alert_thresholds.get('success_rate_critical', 0.9):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.CRITICAL,
                f"Success rate critical: {metrics.success_rate:.1%}",
                'success_rate',
                metrics.success_rate,
                self.config.alert_thresholds.get('success_rate_critical', 0.9)
            )
        elif metrics.success_rate < self.config.alert_thresholds.get('success_rate_warning', 0.95):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.WARNING,
                f"Success rate low: {metrics.success_rate:.1%}",
                'success_rate',
                metrics.success_rate,
                self.config.alert_thresholds.get('success_rate_warning', 0.95)
            )
        
        # Check error rate
        if metrics.error_rate > self.config.alert_thresholds.get('error_rate_critical', 0.1):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.CRITICAL,
                f"Error rate critical: {metrics.error_rate:.1%}",
                'error_rate',
                metrics.error_rate,
                self.config.alert_thresholds.get('error_rate_critical', 0.1)
            )
        elif metrics.error_rate > self.config.alert_thresholds.get('error_rate_warning', 0.05):
            await self._create_alert(
                metrics.strategy_id,
                AlertLevel.WARNING,
                f"Error rate high: {metrics.error_rate:.1%}",
                'error_rate',
                metrics.error_rate,
                self.config.alert_thresholds.get('error_rate_warning', 0.05)
            )
    
    async def _check_health_status(self, strategy_id: str, deployment_info: DeploymentInfo) -> HealthStatus:
        """Check health status of a strategy"""
        now = datetime.now()
        
        # Calculate health metrics
        uptime = (now - deployment_info.deployment_time).total_seconds()
        restart_count = deployment_info.restart_count
        total_executions = deployment_info.total_executions
        error_count = deployment_info.error_count
        
        # Calculate health score (0-100)
        health_score = 100.0
        
        # Deduct points for errors
        if total_executions > 0:
            error_rate = error_count / total_executions
            health_score -= error_rate * 50  # Up to 50 points for errors
        
        # Deduct points for restarts
        health_score -= restart_count * 10  # 10 points per restart
        
        # Ensure health score is between 0 and 100
        health_score = max(0.0, min(100.0, health_score))
        
        # Determine if healthy
        is_healthy = health_score >= 70.0
        
        # Generate recommendations
        recommendations = []
        if total_executions > 0 and error_count / total_executions > 0.1:
            recommendations.append("High error rate detected - review strategy logic")
        if restart_count > 3:
            recommendations.append("Multiple restarts detected - check for stability issues")
        if health_score < 50:
            recommendations.append("Critical health issues - immediate attention required")
        
        health_status = HealthStatus(
            strategy_id=strategy_id,
            timestamp=now,
            is_healthy=is_healthy,
            health_score=health_score,
            last_execution=deployment_info.last_health_check,
            uptime=uptime,
            restart_count=restart_count,
            recommendations=recommendations
        )
        
        return health_status
    
    def _store_health_status(self, health_status: HealthStatus):
        """Store health status in history"""
        strategy_id = health_status.strategy_id
        
        if strategy_id not in self.health_history:
            self.health_history[strategy_id] = []
        
        self.health_history[strategy_id].append(health_status)
        
        # Clean up old data
        cutoff_time = datetime.now() - timedelta(days=self.config.data_retention_days)
        self.health_history[strategy_id] = [
            h for h in self.health_history[strategy_id]
            if h.timestamp > cutoff_time
        ]
    
    async def _check_health_alerts(self, health_status: HealthStatus):
        """Check for health-based alerts"""
        if not self.config.enable_alerting:
            return
        
        if not health_status.is_healthy:
            await self._create_alert(
                health_status.strategy_id,
                AlertLevel.WARNING,
                f"Strategy health poor: {health_status.health_score:.1f}/100",
                'health_score',
                health_status.health_score,
                70.0
            )
        
        if health_status.health_score < 30:
            await self._create_alert(
                health_status.strategy_id,
                AlertLevel.CRITICAL,
                f"Strategy health critical: {health_status.health_score:.1f}/100",
                'health_score',
                health_status.health_score,
                30.0
            )
    
    async def _monitor_resources(self, strategy_id: str, deployment_info: DeploymentInfo):
        """Monitor resource usage"""
        if not self.config.enable_alerting:
            return
        
        resource_usage = deployment_info.resource_usage
        memory_usage = resource_usage.get('memory_usage', 0.0)
        cpu_usage = resource_usage.get('cpu_usage', 0.0)
        
        # Check memory usage
        if memory_usage > self.config.alert_thresholds.get('memory_usage_critical', 0.8):
            await self._create_alert(
                strategy_id,
                AlertLevel.CRITICAL,
                f"Memory usage critical: {memory_usage:.1%}",
                'memory_usage',
                memory_usage,
                self.config.alert_thresholds.get('memory_usage_critical', 0.8)
            )
        elif memory_usage > self.config.alert_thresholds.get('memory_usage_warning', 0.7):
            await self._create_alert(
                strategy_id,
                AlertLevel.WARNING,
                f"Memory usage high: {memory_usage:.1%}",
                'memory_usage',
                memory_usage,
                self.config.alert_thresholds.get('memory_usage_warning', 0.7)
            )
        
        # Check CPU usage
        if cpu_usage > self.config.alert_thresholds.get('cpu_usage_critical', 0.9):
            await self._create_alert(
                strategy_id,
                AlertLevel.CRITICAL,
                f"CPU usage critical: {cpu_usage:.1%}",
                'cpu_usage',
                cpu_usage,
                self.config.alert_thresholds.get('cpu_usage_critical', 0.9)
            )
        elif cpu_usage > self.config.alert_thresholds.get('cpu_usage_warning', 0.8):
            await self._create_alert(
                strategy_id,
                AlertLevel.WARNING,
                f"CPU usage high: {cpu_usage:.1%}",
                'cpu_usage',
                cpu_usage,
                self.config.alert_thresholds.get('cpu_usage_warning', 0.8)
            )
    
    async def _create_alert(self, strategy_id: str, level: AlertLevel, message: str, 
                          metric_name: str, metric_value: float, threshold: float):
        """Create and send an alert"""
        alert_id = f"{strategy_id}_{metric_name}_{int(time.time())}"
        
        alert = Alert(
            alert_id=alert_id,
            strategy_id=strategy_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Limit alert history
        if len(self.alert_history) > self.config.max_alert_history:
            self.alert_history = self.alert_history[-self.config.max_alert_history:]
        
        # Send to alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")
        
        self.logger.warning(f"Alert created: {level.value} - {message}")
    
    def _resolve_alert(self, alert_id: str, resolution_notes: str):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.is_resolved = True
            alert.resolved_at = datetime.now()
            alert.resolution_notes = resolution_notes
            
            del self.active_alerts[alert_id]
            
            self.logger.info(f"Alert resolved: {alert_id} - {resolution_notes}")
    
    def get_performance_metrics(self, strategy_id: str, hours: int = 24) -> List[PerformanceMetrics]:
        """Get performance metrics for a strategy"""
        if strategy_id not in self.performance_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            m for m in self.performance_history[strategy_id]
            if m.timestamp > cutoff_time
        ]
    
    def get_health_status(self, strategy_id: str, hours: int = 24) -> List[HealthStatus]:
        """Get health status for a strategy"""
        if strategy_id not in self.health_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            h for h in self.health_history[strategy_id]
            if h.timestamp > cutoff_time
        ]
    
    def get_active_alerts(self, strategy_id: Optional[str] = None) -> List[Alert]:
        """Get active alerts"""
        if strategy_id:
            return [
                alert for alert in self.active_alerts.values()
                if alert.strategy_id == strategy_id
            ]
        return list(self.active_alerts.values())
    
    def get_alert_history(self, strategy_id: Optional[str] = None, hours: int = 24) -> List[Alert]:
        """Get alert history"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
        
        if strategy_id:
            alerts = [
                alert for alert in alerts
                if alert.strategy_id == strategy_id
            ]
        
        return alerts
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get monitoring summary"""
        total_strategies = len(self.monitored_strategies)
        active_strategies = len([
            s for s in self.monitored_strategies.values()
            if s.status == DeploymentStatus.ACTIVE
        ])
        
        total_alerts = len(self.active_alerts)
        critical_alerts = len([
            alert for alert in self.active_alerts.values()
            if alert.level == AlertLevel.CRITICAL
        ])
        
        return {
            'monitor_status': self.status.value,
            'total_strategies': total_strategies,
            'active_strategies': active_strategies,
            'total_alerts': total_alerts,
            'critical_alerts': critical_alerts,
            'monitoring_interval': self.config.monitoring_interval,
            'data_retention_days': self.config.data_retention_days
        }
