"""
Real-Time Monitoring and Alerting System

Professional-grade monitoring system providing:
- Real-time performance monitoring
- Intelligent alerting and notifications
- Risk monitoring and controls
- System health monitoring
- Custom dashboard creation
- Automated reporting

Author: Pro Quant Desk Trader
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import warnings

warnings.filterwarnings('ignore')


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts"""
    PERFORMANCE = "performance"
    RISK = "risk"
    SYSTEM = "system"
    EXECUTION = "execution"
    MARKET = "market"
    CUSTOM = "custom"


class MonitoringFrequency(Enum):
    """Monitoring frequency"""
    REAL_TIME = "real_time"
    MINUTE = "minute"
    FIVE_MINUTE = "five_minute"
    HOURLY = "hourly"
    DAILY = "daily"


@dataclass
class AlertRule:
    """Alert rule definition"""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # Condition parameters
    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold: float
    
    # Time-based conditions
    lookback_period: timedelta = timedelta(minutes=5)
    consecutive_violations: int = 1
    
    # Alert management
    enabled: bool = True
    cooldown_period: timedelta = timedelta(minutes=15)
    last_triggered: Optional[datetime] = None
    
    # Notification settings
    email_recipients: List[str] = field(default_factory=list)
    slack_channel: Optional[str] = None
    
    # Custom conditions
    custom_condition: Optional[Callable] = None
    
    def should_trigger(self, current_value: float, timestamp: datetime) -> bool:
        """Check if alert should trigger"""
        if not self.enabled:
            return False
        
        # Check cooldown period
        if (self.last_triggered and 
            timestamp - self.last_triggered < self.cooldown_period):
            return False
        
        # Check threshold condition
        if self.operator == '>':
            return current_value > self.threshold
        elif self.operator == '<':
            return current_value < self.threshold
        elif self.operator == '>=':
            return current_value >= self.threshold
        elif self.operator == '<=':
            return current_value <= self.threshold
        elif self.operator == '==':
            return current_value == self.threshold
        elif self.operator == '!=':
            return current_value != self.threshold
        
        return False


@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule: AlertRule
    triggered_at: datetime
    metric_value: float
    message: str
    
    # Context information
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    # Status tracking
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def acknowledge(self, user: str):
        """Acknowledge alert"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = datetime.now()
    
    def resolve(self):
        """Resolve alert"""
        self.resolved = True
        self.resolved_at = datetime.now()


@dataclass
class MonitoringDashboard:
    """Monitoring dashboard configuration"""
    dashboard_id: str
    name: str
    description: str
    
    # Metrics to display
    metrics: List[str] = field(default_factory=list)
    
    # Layout configuration
    layout: Dict[str, Any] = field(default_factory=dict)
    
    # Refresh settings
    refresh_interval: timedelta = timedelta(seconds=30)
    
    # Access control
    authorized_users: List[str] = field(default_factory=list)
    
    # Dashboard state
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class RealTimeMonitor:
    """
    Real-time monitoring engine
    
    Features:
    - Continuous metric collection
    - Real-time alerting
    - Performance tracking
    - System health monitoring
    """
    
    def __init__(self, update_interval: float = 1.0):
        """
        Initialize real-time monitor
        
        Args:
            update_interval: Update interval in seconds
        """
        self.update_interval = update_interval
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.is_running = False
        self.metrics = {}
        self.metric_history = {}
        
        # Data sources
        self.data_sources = {}
        
        # Callbacks
        self.metric_callbacks = {}
        
        self.logger.info("RealTimeMonitor initialized")
    
    def register_data_source(self, name: str, source: Any):
        """Register data source for monitoring"""
        self.data_sources[name] = source
        self.logger.info(f"Data source registered: {name}")
    
    def register_metric_callback(self, metric_name: str, callback: Callable):
        """Register callback for metric updates"""
        if metric_name not in self.metric_callbacks:
            self.metric_callbacks[metric_name] = []
        self.metric_callbacks[metric_name].append(callback)
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        self.is_running = True
        self.logger.info("Real-time monitoring started")
        
        while self.is_running:
            try:
                # Update all metrics
                await self._update_metrics()
                
                # Sleep until next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {str(e)}")
                await asyncio.sleep(self.update_interval)
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_running = False
        self.logger.info("Real-time monitoring stopped")
    
    async def _update_metrics(self):
        """Update all monitored metrics"""
        timestamp = datetime.now()
        
        # Update portfolio metrics
        if 'portfolio_manager' in self.data_sources:
            portfolio_manager = self.data_sources['portfolio_manager']
            
            # Get current portfolio value
            portfolio_value = portfolio_manager.get_portfolio_value()
            self._update_metric('portfolio_value', portfolio_value, timestamp)
            
            # Get current positions
            positions = portfolio_manager.get_current_positions()
            self._update_metric('active_positions', len(positions), timestamp)
            
            # Calculate daily P&L
            daily_pnl = portfolio_manager.get_daily_pnl()
            self._update_metric('daily_pnl', daily_pnl, timestamp)
        
        # Update risk metrics
        if 'risk_manager' in self.data_sources:
            risk_manager = self.data_sources['risk_manager']
            
            # Get current VaR
            var_95 = risk_manager.calculate_portfolio_var()
            self._update_metric('var_95', var_95, timestamp)
            
            # Get current leverage
            leverage = risk_manager.get_current_leverage()
            self._update_metric('leverage', leverage, timestamp)
        
        # Update execution metrics
        if 'execution_engine' in self.data_sources:
            execution_engine = self.data_sources['execution_engine']
            
            # Get execution summary
            summary = execution_engine.get_execution_summary()
            self._update_metric('success_rate', summary.get('success_rate', 0), timestamp)
            self._update_metric('avg_execution_time', summary.get('average_execution_time', 0), timestamp)
    
    def _update_metric(self, metric_name: str, value: float, timestamp: datetime):
        """Update individual metric"""
        # Store current value
        self.metrics[metric_name] = value
        
        # Store in history
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = []
        
        self.metric_history[metric_name].append({
            'timestamp': timestamp,
            'value': value
        })
        
        # Limit history size
        if len(self.metric_history[metric_name]) > 10000:
            self.metric_history[metric_name] = self.metric_history[metric_name][-5000:]
        
        # Trigger callbacks
        if metric_name in self.metric_callbacks:
            for callback in self.metric_callbacks[metric_name]:
                try:
                    callback(metric_name, value, timestamp)
                except Exception as e:
                    self.logger.error(f"Callback error for {metric_name}: {str(e)}")
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current metric values"""
        return self.metrics.copy()
    
    def get_metric_history(self, metric_name: str, 
                          lookback_period: Optional[timedelta] = None) -> List[Dict[str, Any]]:
        """Get metric history"""
        if metric_name not in self.metric_history:
            return []
        
        history = self.metric_history[metric_name]
        
        if lookback_period:
            cutoff_time = datetime.now() - lookback_period
            history = [h for h in history if h['timestamp'] >= cutoff_time]
        
        return history


class AlertManager:
    """
    Intelligent alert management system
    
    Features:
    - Rule-based alerting
    - Alert correlation and grouping
    - Notification management
    - Alert lifecycle tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Alert management
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = []
        
        # Notification settings
        self.email_config = {}
        self.slack_config = {}
        
        # Alert correlation
        self.correlation_rules = []
        
        self.logger.info("AlertManager initialized")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.alert_rules[rule.rule_id] = rule
        self.logger.info(f"Alert rule added: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str):
        """Remove alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Alert rule removed: {rule_id}")
    
    def check_alerts(self, metrics: Dict[str, float], timestamp: datetime):
        """Check all alert rules against current metrics"""
        
        for rule_id, rule in self.alert_rules.items():
            if rule.metric_name in metrics:
                current_value = metrics[rule.metric_name]
                
                # Check if alert should trigger
                if rule.should_trigger(current_value, timestamp):
                    self._trigger_alert(rule, current_value, timestamp)
    
    def _trigger_alert(self, rule: AlertRule, value: float, timestamp: datetime):
        """Trigger alert"""
        alert_id = f"{rule.rule_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Create alert message
        message = f"Alert: {rule.name}\n"
        message += f"Metric: {rule.metric_name} = {value:.4f}\n"
        message += f"Threshold: {rule.operator} {rule.threshold}\n"
        message += f"Severity: {rule.severity.value.upper()}\n"
        message += f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            rule=rule,
            triggered_at=timestamp,
            metric_value=value,
            message=message
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Update rule last triggered time
        rule.last_triggered = timestamp
        
        # Send notifications
        self._send_notifications(alert)
        
        self.logger.warning(f"Alert triggered: {rule.name} ({alert_id})")
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        
        # Email notifications
        if alert.rule.email_recipients and self.email_config:
            try:
                self._send_email_notification(alert)
            except Exception as e:
                self.logger.error(f"Email notification failed: {str(e)}")
        
        # Slack notifications
        if alert.rule.slack_channel and self.slack_config:
            try:
                self._send_slack_notification(alert)
            except Exception as e:
                self.logger.error(f"Slack notification failed: {str(e)}")
    
    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        if not self.email_config:
            return
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.email_config['from_email']
        msg['To'] = ', '.join(alert.rule.email_recipients)
        msg['Subject'] = f"Trading Alert: {alert.rule.name}"
        
        body = alert.message
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
        if self.email_config.get('use_tls'):
            server.starttls()
        if self.email_config.get('username'):
            server.login(self.email_config['username'], self.email_config['password'])
        
        server.send_message(msg)
        server.quit()
    
    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        # This would integrate with Slack API
        # For now, just log the notification
        self.logger.info(f"Slack notification: {alert.rule.slack_channel} - {alert.message}")
    
    def acknowledge_alert(self, alert_id: str, user: str):
        """Acknowledge alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledge(user)
            self.logger.info(f"Alert acknowledged: {alert_id} by {user}")
    
    def resolve_alert(self, alert_id: str):
        """Resolve alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolve()
            # Move to history if needed
            del self.active_alerts[alert_id]
            self.logger.info(f"Alert resolved: {alert_id}")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.rule.severity == severity]
        
        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        # Count by severity
        severity_counts = {}
        for alert in self.alert_history:
            severity = alert.rule.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by type
        type_counts = {}
        for alert in self.alert_history:
            alert_type = alert.rule.alert_type.value
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'severity_distribution': severity_counts,
            'type_distribution': type_counts,
            'alert_rules': len(self.alert_rules)
        }


class MonitoringEngine:
    """
    Comprehensive monitoring engine
    
    Features:
    - Real-time monitoring
    - Alert management
    - Dashboard management
    - Performance tracking
    - System health monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.real_time_monitor = RealTimeMonitor()
        self.alert_manager = AlertManager()
        
        # Dashboard management
        self.dashboards = {}
        
        # System health
        self.system_health = {
            'status': 'healthy',
            'last_check': datetime.now(),
            'components': {}
        }
        
        # Performance tracking
        self.performance_metrics = {}
        
        self.logger.info("MonitoringEngine initialized with comprehensive capabilities")
    
    def setup_default_alerts(self):
        """Setup default alert rules"""
        
        # Portfolio alerts
        portfolio_alerts = [
            AlertRule(
                rule_id='portfolio_drawdown',
                name='Portfolio Drawdown Alert',
                description='Alert when portfolio drawdown exceeds threshold',
                alert_type=AlertType.RISK,
                severity=AlertSeverity.WARNING,
                metric_name='current_drawdown',
                operator='<',
                threshold=-0.05,  # 5% drawdown
                cooldown_period=timedelta(hours=1)
            ),
            AlertRule(
                rule_id='daily_pnl_loss',
                name='Daily P&L Loss Alert',
                description='Alert when daily P&L loss exceeds threshold',
                alert_type=AlertType.PERFORMANCE,
                severity=AlertSeverity.ERROR,
                metric_name='daily_pnl',
                operator='<',
                threshold=-50000,  # $50k loss
                cooldown_period=timedelta(hours=2)
            )
        ]
        
        # Risk alerts
        risk_alerts = [
            AlertRule(
                rule_id='var_breach',
                name='VaR Breach Alert',
                description='Alert when VaR is breached',
                alert_type=AlertType.RISK,
                severity=AlertSeverity.CRITICAL,
                metric_name='var_95',
                operator='<',
                threshold=-100000,  # $100k VaR
                cooldown_period=timedelta(minutes=30)
            ),
            AlertRule(
                rule_id='high_leverage',
                name='High Leverage Alert',
                description='Alert when leverage exceeds threshold',
                alert_type=AlertType.RISK,
                severity=AlertSeverity.WARNING,
                metric_name='leverage',
                operator='>',
                threshold=2.0,  # 2x leverage
                cooldown_period=timedelta(hours=1)
            )
        ]
        
        # Execution alerts
        execution_alerts = [
            AlertRule(
                rule_id='low_execution_success',
                name='Low Execution Success Rate',
                description='Alert when execution success rate drops',
                alert_type=AlertType.EXECUTION,
                severity=AlertSeverity.WARNING,
                metric_name='success_rate',
                operator='<',
                threshold=90.0,  # 90% success rate
                cooldown_period=timedelta(hours=1)
            )
        ]
        
        # Add all alerts
        all_alerts = portfolio_alerts + risk_alerts + execution_alerts
        for alert in all_alerts:
            self.alert_manager.add_alert_rule(alert)
        
        self.logger.info(f"Added {len(all_alerts)} default alert rules")
    
    def create_dashboard(self, dashboard: MonitoringDashboard):
        """Create monitoring dashboard"""
        self.dashboards[dashboard.dashboard_id] = dashboard
        self.logger.info(f"Dashboard created: {dashboard.name}")
    
    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get dashboard data"""
        if dashboard_id not in self.dashboards:
            return {}
        
        dashboard = self.dashboards[dashboard_id]
        
        # Get current metrics
        current_metrics = self.real_time_monitor.get_current_metrics()
        
        # Get metric history for dashboard metrics
        dashboard_data = {
            'dashboard_info': {
                'name': dashboard.name,
                'description': dashboard.description,
                'last_updated': datetime.now().isoformat()
            },
            'current_metrics': {},
            'metric_history': {},
            'alerts': []
        }
        
        # Add current metrics
        for metric in dashboard.metrics:
            if metric in current_metrics:
                dashboard_data['current_metrics'][metric] = current_metrics[metric]
        
        # Add metric history
        for metric in dashboard.metrics:
            history = self.real_time_monitor.get_metric_history(
                metric, lookback_period=timedelta(hours=24)
            )
            dashboard_data['metric_history'][metric] = history
        
        # Add active alerts
        active_alerts = self.alert_manager.get_active_alerts()
        dashboard_data['alerts'] = [
            {
                'alert_id': alert.alert_id,
                'rule_name': alert.rule.name,
                'severity': alert.rule.severity.value,
                'message': alert.message,
                'triggered_at': alert.triggered_at.isoformat()
            }
            for alert in active_alerts[:10]  # Latest 10 alerts
        ]
        
        return dashboard_data
    
    async def start_monitoring(self):
        """Start comprehensive monitoring"""
        # Setup default alerts
        self.setup_default_alerts()
        
        # Register alert checking callback
        self.real_time_monitor.register_metric_callback(
            'all_metrics', self._check_alerts_callback
        )
        
        # Start real-time monitoring
        await self.real_time_monitor.start_monitoring()
    
    def _check_alerts_callback(self, metric_name: str, value: float, timestamp: datetime):
        """Callback to check alerts on metric updates"""
        current_metrics = self.real_time_monitor.get_current_metrics()
        self.alert_manager.check_alerts(current_metrics, timestamp)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'monitoring_status': 'running' if self.real_time_monitor.is_running else 'stopped',
            'active_alerts': len(self.alert_manager.get_active_alerts()),
            'alert_rules': len(self.alert_manager.alert_rules),
            'dashboards': len(self.dashboards),
            'system_health': self.system_health,
            'last_update': datetime.now().isoformat()
        } 