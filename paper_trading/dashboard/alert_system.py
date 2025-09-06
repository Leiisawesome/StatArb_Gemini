#!/usr/bin/env python3
"""
Advanced Alert System
=====================

Professional alert and notification system for trading dashboard.
Supports email, SMS, webhook notifications with custom rules and thresholds.

Author: Pro Quant Desk Trader
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    """Types of alerts"""
    RISK = "RISK"
    PERFORMANCE = "PERFORMANCE"
    TECHNICAL = "TECHNICAL"
    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"

class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"
    SLACK = "SLACK"
    DISCORD = "DISCORD"
    CONSOLE = "CONSOLE"

@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # Condition parameters
    metric: str  # e.g., 'portfolio_drawdown', 'strategy_pnl', 'position_size'
    operator: str  # 'gt', 'lt', 'eq', 'gte', 'lte'
    threshold: float
    
    # Optional parameters
    strategy_filter: Optional[str] = None  # Filter by strategy
    symbol_filter: Optional[str] = None    # Filter by symbol
    time_window: Optional[int] = None      # Time window in minutes
    
    # Notification settings
    channels: List[NotificationChannel] = field(default_factory=list)
    cooldown_minutes: int = 15  # Minimum time between same alerts
    
    # Status
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

@dataclass
class Alert:
    """Alert instance"""
    alert_id: str
    rule_id: str
    timestamp: datetime
    severity: AlertSeverity
    alert_type: AlertType
    title: str
    message: str
    
    # Context data
    current_value: float
    threshold: float
    strategy_id: Optional[str] = None
    symbol: Optional[str] = None
    
    # Notification status
    notifications_sent: List[NotificationChannel] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

@dataclass
class NotificationConfig:
    """Notification channel configuration"""
    channel: NotificationChannel
    enabled: bool = True
    
    # Email configuration
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    from_email: Optional[str] = None
    to_emails: List[str] = field(default_factory=list)
    
    # SMS configuration (using email-to-SMS gateways)
    sms_gateway: Optional[str] = None  # e.g., 'verizon', 'att', 'tmobile'
    phone_numbers: List[str] = field(default_factory=list)
    
    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    
    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # Discord configuration
    discord_webhook_url: Optional[str] = None

class AlertSystem:
    """
    Advanced alert and notification system
    
    Features:
    - Custom alert rules with flexible conditions
    - Multiple notification channels (email, SMS, webhooks)
    - Alert severity levels and cooldown periods
    - Alert history and acknowledgment system
    - Real-time alert monitoring
    - Integration with trading metrics
    """
    
    def __init__(self):
        # Alert rules and history
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.active_alerts: Dict[str, Alert] = {}
        
        # Notification configuration
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Alert statistics
        self.alert_stats = {
            'total_alerts': 0,
            'alerts_by_severity': defaultdict(int),
            'alerts_by_type': defaultdict(int),
            'notifications_sent': defaultdict(int)
        }
        
        # SMS gateway mappings
        self.sms_gateways = {
            'verizon': 'vtext.com',
            'att': 'txt.att.net',
            'tmobile': 'tmomail.net',
            'sprint': 'messaging.sprintpcs.com'
        }
        
        logger.info("🚨 Advanced Alert System initialized")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule"""
        self.alert_rules[rule.rule_id] = rule
        logger.info(f"📋 Alert rule added: {rule.name} ({rule.rule_id})")
    
    def remove_alert_rule(self, rule_id: str):
        """Remove an alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"🗑️ Alert rule removed: {rule_id}")
    
    def configure_notification_channel(self, config: NotificationConfig):
        """Configure a notification channel"""
        self.notification_configs[config.channel] = config
        logger.info(f"📧 Notification channel configured: {config.channel.value}")
    
    def create_default_rules(self):
        """Create default alert rules for common scenarios"""
        
        # Portfolio drawdown alert
        self.add_alert_rule(AlertRule(
            rule_id="portfolio_drawdown_high",
            name="High Portfolio Drawdown",
            description="Alert when portfolio drawdown exceeds 5%",
            alert_type=AlertType.RISK,
            severity=AlertSeverity.HIGH,
            metric="portfolio_drawdown",
            operator="gt",
            threshold=0.05,
            channels=[NotificationChannel.EMAIL, NotificationChannel.CONSOLE],
            cooldown_minutes=30
        ))
        
        # Critical drawdown alert
        self.add_alert_rule(AlertRule(
            rule_id="portfolio_drawdown_critical",
            name="Critical Portfolio Drawdown",
            description="Alert when portfolio drawdown exceeds 8%",
            alert_type=AlertType.RISK,
            severity=AlertSeverity.CRITICAL,
            metric="portfolio_drawdown",
            operator="gt",
            threshold=0.08,
            channels=[NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.CONSOLE],
            cooldown_minutes=15
        ))
        
        # Large loss alert
        self.add_alert_rule(AlertRule(
            rule_id="large_loss",
            name="Large Daily Loss",
            description="Alert when daily P&L loss exceeds $5,000",
            alert_type=AlertType.PERFORMANCE,
            severity=AlertSeverity.MEDIUM,
            metric="daily_pnl",
            operator="lt",
            threshold=-5000,
            channels=[NotificationChannel.EMAIL, NotificationChannel.CONSOLE],
            cooldown_minutes=60
        ))
        
        # Strategy underperformance
        self.add_alert_rule(AlertRule(
            rule_id="strategy_underperformance",
            name="Strategy Underperformance",
            description="Alert when strategy return falls below -10%",
            alert_type=AlertType.PERFORMANCE,
            severity=AlertSeverity.MEDIUM,
            metric="strategy_return",
            operator="lt",
            threshold=-0.10,
            channels=[NotificationChannel.EMAIL, NotificationChannel.CONSOLE],
            cooldown_minutes=120
        ))
        
        # High volatility alert
        self.add_alert_rule(AlertRule(
            rule_id="high_volatility",
            name="High Portfolio Volatility",
            description="Alert when portfolio volatility exceeds 30%",
            alert_type=AlertType.RISK,
            severity=AlertSeverity.MEDIUM,
            metric="portfolio_volatility",
            operator="gt",
            threshold=0.30,
            channels=[NotificationChannel.EMAIL, NotificationChannel.CONSOLE],
            cooldown_minutes=180
        ))
        
        logger.info("📋 Default alert rules created")
    
    async def check_alerts(self, trading_data: Dict[str, Any]):
        """Check all alert rules against current trading data"""
        try:
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Check cooldown period
                if rule.last_triggered:
                    time_since_last = datetime.now() - rule.last_triggered
                    if time_since_last.total_seconds() < rule.cooldown_minutes * 60:
                        continue
                
                # Evaluate rule condition
                if await self._evaluate_rule(rule, trading_data):
                    await self._trigger_alert(rule, trading_data)
                    
        except Exception as e:
            logger.error(f"❌ Error checking alerts: {e}")
    
    async def _evaluate_rule(self, rule: AlertRule, trading_data: Dict[str, Any]) -> bool:
        """Evaluate if an alert rule condition is met"""
        try:
            # Extract metric value based on rule configuration
            metric_value = self._extract_metric_value(rule, trading_data)
            
            if metric_value is None:
                return False
            
            # Apply operator
            if rule.operator == "gt":
                return metric_value > rule.threshold
            elif rule.operator == "lt":
                return metric_value < rule.threshold
            elif rule.operator == "eq":
                return abs(metric_value - rule.threshold) < 0.0001
            elif rule.operator == "gte":
                return metric_value >= rule.threshold
            elif rule.operator == "lte":
                return metric_value <= rule.threshold
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error evaluating rule {rule.rule_id}: {e}")
            return False
    
    def _extract_metric_value(self, rule: AlertRule, trading_data: Dict[str, Any]) -> Optional[float]:
        """Extract metric value from trading data"""
        try:
            # Portfolio-level metrics
            if rule.metric == "portfolio_drawdown":
                return trading_data.get('performance_metrics', {}).get('current_drawdown', 0) / 100
            
            elif rule.metric == "portfolio_value":
                return trading_data.get('portfolio_value', 0)
            
            elif rule.metric == "total_pnl":
                return trading_data.get('total_pnl', 0)
            
            elif rule.metric == "daily_pnl":
                return trading_data.get('daily_pnl', 0)
            
            elif rule.metric == "portfolio_volatility":
                return trading_data.get('performance_metrics', {}).get('volatility', 0) / 100
            
            # Strategy-level metrics
            elif rule.metric == "strategy_return" and rule.strategy_filter:
                strategy_data = trading_data.get('strategy_performance', {}).get(rule.strategy_filter, {})
                return strategy_data.get('return_pct', 0) / 100
            
            elif rule.metric == "strategy_pnl" and rule.strategy_filter:
                strategy_data = trading_data.get('strategy_performance', {}).get(rule.strategy_filter, {})
                return strategy_data.get('current_pnl', 0)
            
            # Position-level metrics
            elif rule.metric == "position_size" and rule.symbol_filter:
                positions = trading_data.get('positions', {})
                for pos_id, position in positions.items():
                    if position.get('symbol') == rule.symbol_filter:
                        return abs(position.get('quantity', 0) * position.get('current_price', 0))
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting metric {rule.metric}: {e}")
            return None
    
    async def _trigger_alert(self, rule: AlertRule, trading_data: Dict[str, Any]):
        """Trigger an alert and send notifications"""
        try:
            # Create alert instance
            alert_id = f"{rule.rule_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            current_value = self._extract_metric_value(rule, trading_data)
            
            alert = Alert(
                alert_id=alert_id,
                rule_id=rule.rule_id,
                timestamp=datetime.now(),
                severity=rule.severity,
                alert_type=rule.alert_type,
                title=rule.name,
                message=self._generate_alert_message(rule, current_value, trading_data),
                current_value=current_value or 0,
                threshold=rule.threshold,
                strategy_id=rule.strategy_filter,
                symbol=rule.symbol_filter
            )
            
            # Update rule status
            rule.last_triggered = datetime.now()
            rule.trigger_count += 1
            
            # Store alert
            self.alert_history.append(alert)
            self.active_alerts[alert_id] = alert
            
            # Update statistics
            self.alert_stats['total_alerts'] += 1
            self.alert_stats['alerts_by_severity'][rule.severity.value] += 1
            self.alert_stats['alerts_by_type'][rule.alert_type.value] += 1
            
            # Send notifications
            await self._send_notifications(alert, rule.channels)
            
            logger.warning(f"🚨 ALERT TRIGGERED: {alert.title} - {alert.message}")
            
        except Exception as e:
            logger.error(f"❌ Error triggering alert: {e}")
    
    def _generate_alert_message(self, rule: AlertRule, current_value: Optional[float], trading_data: Dict[str, Any]) -> str:
        """Generate alert message"""
        try:
            base_message = f"{rule.description}\n"
            
            if current_value is not None:
                if rule.metric.endswith('_pct') or 'drawdown' in rule.metric or 'volatility' in rule.metric:
                    base_message += f"Current: {current_value:.2%}, Threshold: {rule.threshold:.2%}\n"
                else:
                    base_message += f"Current: ${current_value:,.2f}, Threshold: ${rule.threshold:,.2f}\n"
            
            # Add context
            portfolio_value = trading_data.get('portfolio_value', 0)
            total_pnl = trading_data.get('total_pnl', 0)
            base_message += f"Portfolio Value: ${portfolio_value:,.2f}, Total P&L: ${total_pnl:,.2f}\n"
            
            # Add timestamp
            base_message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return base_message
            
        except Exception as e:
            logger.error(f"❌ Error generating alert message: {e}")
            return f"{rule.description} - Alert triggered at {datetime.now()}"
    
    async def _send_notifications(self, alert: Alert, channels: List[NotificationChannel]):
        """Send notifications through specified channels"""
        for channel in channels:
            try:
                if channel in self.notification_configs and self.notification_configs[channel].enabled:
                    success = await self._send_notification(alert, channel)
                    if success:
                        alert.notifications_sent.append(channel)
                        self.alert_stats['notifications_sent'][channel.value] += 1
                elif channel == NotificationChannel.CONSOLE:
                    # Console notification always available
                    self._send_console_notification(alert)
                    alert.notifications_sent.append(channel)
                    self.alert_stats['notifications_sent'][channel.value] += 1
                    
            except Exception as e:
                logger.error(f"❌ Error sending notification via {channel.value}: {e}")
    
    async def _send_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send notification through specific channel"""
        try:
            config = self.notification_configs[channel]
            
            if channel == NotificationChannel.EMAIL:
                return await self._send_email_notification(alert, config)
            elif channel == NotificationChannel.SMS:
                return await self._send_sms_notification(alert, config)
            elif channel == NotificationChannel.WEBHOOK:
                return await self._send_webhook_notification(alert, config)
            elif channel == NotificationChannel.SLACK:
                return await self._send_slack_notification(alert, config)
            elif channel == NotificationChannel.DISCORD:
                return await self._send_discord_notification(alert, config)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in {channel.value} notification: {e}")
            return False
    
    async def _send_email_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send email notification"""
        try:
            if not all([config.smtp_server, config.email_username, config.email_password, config.from_email]):
                logger.warning("⚠️  Email configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = config.from_email
            msg['To'] = ', '.join(config.to_emails)
            msg['Subject'] = f"🚨 Trading Alert: {alert.title} [{alert.severity.value}]"
            
            # Email body
            body = f"""
Trading Alert Notification

Alert: {alert.title}
Severity: {alert.severity.value}
Type: {alert.alert_type.value}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Current Value: {alert.current_value}
Threshold: {alert.threshold}

This is an automated alert from your trading system.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(config.smtp_server, config.smtp_port)
            server.starttls()
            server.login(config.email_username, config.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Email notification sent for alert: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email notification failed: {e}")
            return False
    
    async def _send_sms_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send SMS notification via email-to-SMS gateway"""
        try:
            if not config.sms_gateway or config.sms_gateway not in self.sms_gateways:
                logger.warning("⚠️  SMS gateway not configured")
                return False
            
            gateway_domain = self.sms_gateways[config.sms_gateway]
            
            # Create SMS message (keep it short)
            sms_message = f"🚨 Trading Alert: {alert.title} [{alert.severity.value}] - {alert.current_value:.2f} vs {alert.threshold:.2f}"
            
            # Send to each phone number
            for phone in config.phone_numbers:
                sms_email = f"{phone}@{gateway_domain}"
                
                msg = MIMEText(sms_message)
                msg['From'] = config.from_email
                msg['To'] = sms_email
                msg['Subject'] = ""  # SMS doesn't need subject
                
                server = smtplib.SMTP(config.smtp_server, config.smtp_port)
                server.starttls()
                server.login(config.email_username, config.email_password)
                server.send_message(msg)
                server.quit()
            
            logger.info(f"📱 SMS notification sent for alert: {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ SMS notification failed: {e}")
            return False
    
    async def _send_webhook_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send webhook notification"""
        try:
            if not config.webhook_url:
                return False
            
            payload = {
                'alert_id': alert.alert_id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'type': alert.alert_type.value,
                'timestamp': alert.timestamp.isoformat(),
                'current_value': alert.current_value,
                'threshold': alert.threshold
            }
            
            headers = {'Content-Type': 'application/json'}
            headers.update(config.webhook_headers)
            
            response = requests.post(
                config.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"🔗 Webhook notification sent for alert: {alert.alert_id}")
                return True
            else:
                logger.warning(f"⚠️  Webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Webhook notification failed: {e}")
            return False
    
    async def _send_slack_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send Slack notification"""
        try:
            if not config.slack_webhook_url:
                return False
            
            # Slack color based on severity
            color_map = {
                AlertSeverity.LOW: "#36a64f",
                AlertSeverity.MEDIUM: "#ff9500",
                AlertSeverity.HIGH: "#ff0000",
                AlertSeverity.CRITICAL: "#8B0000"
            }
            
            payload = {
                "channel": config.slack_channel or "#trading-alerts",
                "username": "Trading Bot",
                "icon_emoji": ":warning:",
                "attachments": [{
                    "color": color_map.get(alert.severity, "#ff0000"),
                    "title": f"🚨 {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value, "short": True},
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Current Value", "value": f"{alert.current_value:.2f}", "short": True},
                        {"title": "Threshold", "value": f"{alert.threshold:.2f}", "short": True}
                    ],
                    "timestamp": alert.timestamp.timestamp()
                }]
            }
            
            response = requests.post(config.slack_webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"💬 Slack notification sent for alert: {alert.alert_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Slack notification failed: {e}")
            return False
    
    async def _send_discord_notification(self, alert: Alert, config: NotificationConfig) -> bool:
        """Send Discord notification"""
        try:
            if not config.discord_webhook_url:
                return False
            
            # Discord color based on severity
            color_map = {
                AlertSeverity.LOW: 0x36a64f,
                AlertSeverity.MEDIUM: 0xff9500,
                AlertSeverity.HIGH: 0xff0000,
                AlertSeverity.CRITICAL: 0x8B0000
            }
            
            payload = {
                "embeds": [{
                    "title": f"🚨 {alert.title}",
                    "description": alert.message,
                    "color": color_map.get(alert.severity, 0xff0000),
                    "fields": [
                        {"name": "Severity", "value": alert.severity.value, "inline": True},
                        {"name": "Type", "value": alert.alert_type.value, "inline": True},
                        {"name": "Current Value", "value": f"{alert.current_value:.2f}", "inline": True},
                        {"name": "Threshold", "value": f"{alert.threshold:.2f}", "inline": True}
                    ],
                    "timestamp": alert.timestamp.isoformat()
                }]
            }
            
            response = requests.post(config.discord_webhook_url, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                logger.info(f"🎮 Discord notification sent for alert: {alert.alert_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Discord notification failed: {e}")
            return False
    
    def _send_console_notification(self, alert: Alert):
        """Send console notification"""
        severity_icons = {
            AlertSeverity.LOW: "ℹ️",
            AlertSeverity.MEDIUM: "⚠️",
            AlertSeverity.HIGH: "🚨",
            AlertSeverity.CRITICAL: "🔥"
        }
        
        icon = severity_icons.get(alert.severity, "🚨")
        print(f"\n{icon} TRADING ALERT [{alert.severity.value}] {icon}")
        print(f"Title: {alert.title}")
        print(f"Message: {alert.message}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now()
            
            logger.info(f"✅ Alert acknowledged: {alert_id} by {acknowledged_by}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unacknowledged) alerts"""
        return [alert for alert in self.active_alerts.values() if not alert.acknowledged]
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert system statistics"""
        active_count = len(self.get_active_alerts())
        recent_count = len(self.get_alert_history(24))
        
        return {
            'active_alerts': active_count,
            'alerts_last_24h': recent_count,
            'total_alerts': self.alert_stats['total_alerts'],
            'alerts_by_severity': dict(self.alert_stats['alerts_by_severity']),
            'alerts_by_type': dict(self.alert_stats['alerts_by_type']),
            'notifications_sent': dict(self.alert_stats['notifications_sent']),
            'configured_channels': list(self.notification_configs.keys()),
            'active_rules': len([r for r in self.alert_rules.values() if r.enabled])
        }

# Helper functions for easy setup
def create_email_config(smtp_server: str, username: str, password: str, 
                       from_email: str, to_emails: List[str]) -> NotificationConfig:
    """Create email notification configuration"""
    return NotificationConfig(
        channel=NotificationChannel.EMAIL,
        smtp_server=smtp_server,
        email_username=username,
        email_password=password,
        from_email=from_email,
        to_emails=to_emails
    )

def create_slack_config(webhook_url: str, channel: str = "#trading-alerts") -> NotificationConfig:
    """Create Slack notification configuration"""
    return NotificationConfig(
        channel=NotificationChannel.SLACK,
        slack_webhook_url=webhook_url,
        slack_channel=channel
    )
