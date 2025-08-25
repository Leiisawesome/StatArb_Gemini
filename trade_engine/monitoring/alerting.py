#!/usr/bin/env python3
"""
Alert Management System
=======================

Comprehensive alerting system for real-time monitoring and notification
of trading system performance, health, and business metrics.

Author: StatArb_Gemini Team
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = ""
    metric_name: str = ""
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    condition: str  # 'greater_than', 'less_than', 'equals', 'not_equals'
    threshold: float
    severity: AlertSeverity
    component: str = ""
    description: str = ""
    cooldown_seconds: float = 300  # 5 minutes default
    tags: Dict[str, str] = field(default_factory=dict)

class AlertManager:
    """
    Advanced alert management system.
    
    Features:
    - Rule-based alerting
    - Alert deduplication and grouping
    - Notification delivery
    - Alert lifecycle management
    - Escalation policies
    """
    
    def __init__(self, max_alerts: int = 10000):
        self.max_alerts = max_alerts
        
        # Alert storage
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=max_alerts)
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # Alert state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_lock = threading.RLock()
        
        # Notification handlers
        self.notification_handlers: List[Callable[[Alert], None]] = []
        
        # Alert statistics
        self.alert_stats = {
            'total_alerts': 0,
            'active_alerts': 0,
            'acknowledged_alerts': 0,
            'resolved_alerts': 0,
            'critical_alerts': 0
        }
        
        # Cooldown tracking
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        logger.info("AlertManager initialized")
    
    async def start_monitoring(self):
        """Start alert monitoring"""
        if self.is_monitoring:
            logger.warning("Alert monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("Alert monitoring started")
    
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alert monitoring stopped")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.alert_rules[rule.name] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove an alert rule"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"Removed alert rule: {rule_name}")
    
    def create_alert(
        self,
        title: str,
        description: str,
        severity: AlertSeverity,
        component: str = "",
        metric_name: str = "",
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Alert:
        """Create a new alert"""
        alert_id = f"{component}_{metric_name}_{int(datetime.now().timestamp())}"
        
        alert = Alert(
            id=alert_id,
            title=title,
            description=description,
            severity=severity,
            component=component,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
            tags=tags or {}
        )
        
        with self.monitoring_lock:
            # Check if we're in cooldown for this type of alert
            cooldown_key = f"{component}_{metric_name}"
            if cooldown_key in self.alert_cooldowns:
                if datetime.now() < self.alert_cooldowns[cooldown_key]:
                    logger.debug(f"Alert {cooldown_key} is in cooldown, skipping")
                    return alert
            
            # Add to active alerts
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # Update statistics
            self.alert_stats['total_alerts'] += 1
            self.alert_stats['active_alerts'] += 1
            if severity == AlertSeverity.CRITICAL:
                self.alert_stats['critical_alerts'] += 1
            
            # Set cooldown
            cooldown_duration = timedelta(seconds=300)  # Default 5 minutes
            self.alert_cooldowns[cooldown_key] = datetime.now() + cooldown_duration
        
        # Send notifications
        self._send_notifications(alert)
        
        logger.warning(f"Alert created: [{severity.value.upper()}] {title}")
        return alert
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge an alert"""
        with self.monitoring_lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now()
                
                self.alert_stats['acknowledged_alerts'] += 1
                
                logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                return True
        
        return False
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        with self.monitoring_lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                
                # Move from active to resolved
                del self.active_alerts[alert_id]
                
                self.alert_stats['active_alerts'] -= 1
                self.alert_stats['resolved_alerts'] += 1
                
                logger.info(f"Alert resolved: {alert_id}")
                return True
        
        return False
    
    def check_metric_against_rules(self, metric_name: str, metric_value: float, component: str = ""):
        """Check a metric value against all applicable rules"""
        for rule_name, rule in self.alert_rules.items():
            if rule.metric_name == metric_name and (not rule.component or rule.component == component):
                if self._evaluate_rule_condition(rule, metric_value):
                    # Create alert
                    self.create_alert(
                        title=f"{rule.name} triggered",
                        description=f"{rule.description} (Value: {metric_value}, Threshold: {rule.threshold})",
                        severity=rule.severity,
                        component=component,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        threshold=rule.threshold,
                        tags=rule.tags
                    )
    
    def _evaluate_rule_condition(self, rule: AlertRule, value: float) -> bool:
        """Evaluate if a rule condition is met"""
        if rule.condition == 'greater_than':
            return value > rule.threshold
        elif rule.condition == 'less_than':
            return value < rule.threshold
        elif rule.condition == 'equals':
            return abs(value - rule.threshold) < 1e-6
        elif rule.condition == 'not_equals':
            return abs(value - rule.threshold) >= 1e-6
        else:
            logger.warning(f"Unknown condition: {rule.condition}")
            return False
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add a notification handler"""
        self.notification_handlers.append(handler)
        logger.info("Added notification handler")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Clean up old cooldowns
                self._cleanup_cooldowns()
                
                # Auto-resolve old alerts (optional)
                await self._auto_resolve_alerts()
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def _cleanup_cooldowns(self):
        """Clean up expired cooldowns"""
        now = datetime.now()
        expired_cooldowns = [
            key for key, expire_time in self.alert_cooldowns.items()
            if now >= expire_time
        ]
        
        for key in expired_cooldowns:
            del self.alert_cooldowns[key]
    
    async def _auto_resolve_alerts(self):
        """Auto-resolve alerts that are no longer relevant"""
        # This is a placeholder for auto-resolution logic
        # In practice, this would check if the conditions that triggered
        # the alert are no longer present
        pass
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        with self.monitoring_lock:
            alerts = list(self.active_alerts.values())
            
            if severity_filter:
                alerts = [alert for alert in alerts if alert.severity == severity_filter]
            
            # Sort by severity and timestamp
            severity_order = {
                AlertSeverity.CRITICAL: 0,
                AlertSeverity.HIGH: 1,
                AlertSeverity.MEDIUM: 2,
                AlertSeverity.LOW: 3
            }
            
            alerts.sort(key=lambda x: (severity_order[x.severity], x.timestamp), reverse=True)
            
            return alerts
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified number of hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        with self.monitoring_lock:
            # Update active alerts count
            self.alert_stats['active_alerts'] = len(self.active_alerts)
            
            return self.alert_stats.copy()
    
    def get_alerts_by_component(self, component: str) -> List[Alert]:
        """Get alerts for a specific component"""
        with self.monitoring_lock:
            return [
                alert for alert in self.active_alerts.values()
                if alert.component == component
            ]
    
    def export_alerts_json(self) -> str:
        """Export alerts as JSON"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.get_alert_statistics(),
            'active_alerts': [
                {
                    'id': alert.id,
                    'title': alert.title,
                    'description': alert.description,
                    'severity': alert.severity.value,
                    'status': alert.status.value,
                    'timestamp': alert.timestamp.isoformat(),
                    'component': alert.component,
                    'metric_name': alert.metric_name,
                    'metric_value': alert.metric_value,
                    'threshold': alert.threshold
                }
                for alert in self.get_active_alerts()
            ]
        }
        
        return json.dumps(alert_data, indent=2)

# Global alert manager instance
alert_manager = AlertManager()

# Default alert rules
def setup_default_alert_rules():
    """Setup default alert rules for common scenarios"""
    default_rules = [
        AlertRule(
            name="High CPU Usage",
            metric_name="cpu_usage",
            condition="greater_than",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            description="CPU usage is above 80%"
        ),
        AlertRule(
            name="Critical CPU Usage",
            metric_name="cpu_usage",
            condition="greater_than",
            threshold=95.0,
            severity=AlertSeverity.CRITICAL,
            description="CPU usage is above 95%"
        ),
        AlertRule(
            name="High Memory Usage",
            metric_name="memory_usage",
            condition="greater_than",
            threshold=85.0,
            severity=AlertSeverity.HIGH,
            description="Memory usage is above 85%"
        ),
        AlertRule(
            name="Signal Generation Latency",
            metric_name="signal_generation_latency",
            condition="greater_than",
            threshold=10.0,
            severity=AlertSeverity.MEDIUM,
            description="Signal generation taking too long"
        )
    ]
    
    for rule in default_rules:
        alert_manager.add_alert_rule(rule)

# Notification handlers
def console_notification_handler(alert: Alert):
    """Simple console notification handler"""
    print(f"🚨 ALERT [{alert.severity.value.upper()}]: {alert.title}")
    print(f"   Description: {alert.description}")
    print(f"   Component: {alert.component}")
    print(f"   Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

async def start_alert_monitoring():
    """Start global alert monitoring"""
    setup_default_alert_rules()
    alert_manager.add_notification_handler(console_notification_handler)
    await alert_manager.start_monitoring()

async def stop_alert_monitoring():
    """Stop global alert monitoring"""
    await alert_manager.stop_monitoring()
