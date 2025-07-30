#!/usr/bin/env python3
"""
Alert System
Phase 4: Production Deployment & Monitoring
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class AlertSystem:
    """Production alert system for the trading system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.alerts = []
        self.alert_rules = self._load_alert_rules()
        self.alert_history = []
        self.alerting_active = False
        self.alerting_thread = None
        
        # Alert channels
        self.email_config = self.config.get('email', {})
        self.slack_config = self.config.get('slack', {})
        self.webhook_config = self.config.get('webhook', {})
        
        logger.info("Initialized AlertSystem")
    
    def _load_alert_rules(self) -> List[Dict]:
        """Load alert rules"""
        
        default_rules = [
            {
                'id': 'high_cpu_usage',
                'name': 'High CPU Usage',
                'condition': 'cpu_percent > 90',
                'severity': 'WARNING',
                'message': 'CPU usage is above 90%',
                'enabled': True
            },
            {
                'id': 'critical_cpu_usage',
                'name': 'Critical CPU Usage',
                'condition': 'cpu_percent > 95',
                'severity': 'CRITICAL',
                'message': 'CPU usage is above 95%',
                'enabled': True
            },
            {
                'id': 'high_memory_usage',
                'name': 'High Memory Usage',
                'condition': 'memory_percent > 85',
                'severity': 'WARNING',
                'message': 'Memory usage is above 85%',
                'enabled': True
            },
            {
                'id': 'critical_memory_usage',
                'name': 'Critical Memory Usage',
                'condition': 'memory_percent > 95',
                'severity': 'CRITICAL',
                'message': 'Memory usage is above 95%',
                'enabled': True
            },
            {
                'id': 'high_disk_usage',
                'name': 'High Disk Usage',
                'condition': 'disk_percent > 90',
                'severity': 'WARNING',
                'message': 'Disk usage is above 90%',
                'enabled': True
            },
            {
                'id': 'service_unhealthy',
                'name': 'Service Unhealthy',
                'condition': 'service_status == "UNHEALTHY"',
                'severity': 'CRITICAL',
                'message': 'Service is unhealthy',
                'enabled': True
            },
            {
                'id': 'database_unhealthy',
                'name': 'Database Unhealthy',
                'condition': 'database_status == "UNHEALTHY"',
                'severity': 'CRITICAL',
                'message': 'Database is unhealthy',
                'enabled': True
            },
            {
                'id': 'high_error_rate',
                'name': 'High Error Rate',
                'condition': 'error_rate > 0.05',
                'severity': 'WARNING',
                'message': 'Error rate is above 5%',
                'enabled': True
            },
            {
                'id': 'critical_error_rate',
                'name': 'Critical Error Rate',
                'condition': 'error_rate > 0.10',
                'severity': 'CRITICAL',
                'message': 'Error rate is above 10%',
                'enabled': True
            }
        ]
        
        return default_rules
    
    def start_alerting(self) -> bool:
        """Start the alerting system"""
        
        try:
            if self.alerting_active:
                logger.warning("Alerting system is already active")
                return True
            
            logger.info("Starting alerting system...")
            
            self.alerting_active = True
            self.alerting_thread = threading.Thread(target=self._alerting_loop, daemon=True)
            self.alerting_thread.start()
            
            logger.info("Alerting system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start alerting system: {e}")
            return False
    
    def stop_alerting(self) -> bool:
        """Stop the alerting system"""
        
        try:
            logger.info("Stopping alerting system...")
            
            self.alerting_active = False
            if self.alerting_thread and self.alerting_thread.is_alive():
                self.alerting_thread.join(timeout=5)
            
            logger.info("Alerting system stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop alerting system: {e}")
            return False
    
    def _alerting_loop(self):
        """Main alerting loop"""
        
        while self.alerting_active:
            try:
                # Process pending alerts
                self._process_alerts()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Sleep for alerting interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in alerting loop: {e}")
                time.sleep(5)
    
    def create_alert(self, alert_type: str, message: str, severity: str = 'INFO', 
                    metadata: Dict = None) -> str:
        """Create a new alert"""
        
        try:
            alert_id = f"alert_{len(self.alerts) + 1}_{int(time.time())}"
            
            alert = {
                'id': alert_id,
                'type': alert_type,
                'message': message,
                'severity': severity.upper(),
                'timestamp': datetime.now().isoformat(),
                'acknowledged': False,
                'resolved': False,
                'metadata': metadata or {},
                'channels_sent': []
            }
            
            self.alerts.append(alert)
            self.alert_history.append(alert.copy())
            
            logger.info(f"Alert created: {alert_id} - {severity} - {message}")
            return alert_id
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return ""
    
    def _process_alerts(self):
        """Process pending alerts"""
        
        try:
            for alert in self.alerts:
                if not alert['acknowledged'] and not alert['resolved']:
                    # Send alert through configured channels
                    self._send_alert(alert)
                    
        except Exception as e:
            logger.error(f"Failed to process alerts: {e}")
    
    def _send_alert(self, alert: Dict):
        """Send alert through configured channels"""
        
        try:
            channels_sent = []
            
            # Send email alert
            if self.email_config and alert['severity'] in ['WARNING', 'CRITICAL']:
                if self._send_email_alert(alert):
                    channels_sent.append('email')
            
            # Send Slack alert
            if self.slack_config and alert['severity'] in ['WARNING', 'CRITICAL']:
                if self._send_slack_alert(alert):
                    channels_sent.append('slack')
            
            # Send webhook alert
            if self.webhook_config:
                if self._send_webhook_alert(alert):
                    channels_sent.append('webhook')
            
            # Update alert with sent channels
            alert['channels_sent'] = channels_sent
            
            logger.info(f"Alert sent through channels: {channels_sent}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _send_email_alert(self, alert: Dict) -> bool:
        """Send email alert"""
        
        try:
            # Mock email sending (in real implementation, this would use SMTP)
            logger.info(f"Email alert sent: {alert['message']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_slack_alert(self, alert: Dict) -> bool:
        """Send Slack alert"""
        
        try:
            # Mock Slack sending (in real implementation, this would use Slack API)
            logger.info(f"Slack alert sent: {alert['message']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def _send_webhook_alert(self, alert: Dict) -> bool:
        """Send webhook alert"""
        
        try:
            # Mock webhook sending (in real implementation, this would use HTTP requests)
            logger.info(f"Webhook alert sent: {alert['message']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        
        try:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['acknowledged'] = True
                    alert['acknowledged_at'] = datetime.now().isoformat()
                    logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            
            logger.warning(f"Alert not found: {alert_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Resolve an alert"""
        
        try:
            for alert in self.alerts:
                if alert['id'] == alert_id:
                    alert['resolved'] = True
                    alert['resolved_at'] = datetime.now().isoformat()
                    alert['resolution_notes'] = resolution_notes
                    logger.info(f"Alert resolved: {alert_id}")
                    return True
            
            logger.warning(f"Alert not found: {alert_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def _cleanup_old_alerts(self):
        """Clean up old alerts"""
        
        try:
            # Remove resolved alerts older than 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            self.alerts = [
                alert for alert in self.alerts
                if not (alert['resolved'] and 
                       datetime.fromisoformat(alert['resolved_at']) < cutoff_date)
            ]
            
            # Keep only last 1000 alerts in history
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")
    
    def get_alerts(self, severity: str = None, acknowledged: bool = None, 
                  resolved: bool = None) -> List[Dict]:
        """Get alerts with optional filtering"""
        
        try:
            filtered_alerts = self.alerts.copy()
            
            if severity:
                filtered_alerts = [alert for alert in filtered_alerts if alert['severity'] == severity.upper()]
            
            if acknowledged is not None:
                filtered_alerts = [alert for alert in filtered_alerts if alert['acknowledged'] == acknowledged]
            
            if resolved is not None:
                filtered_alerts = [alert for alert in filtered_alerts if alert['resolved'] == resolved]
            
            return filtered_alerts
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def get_alert_summary(self) -> Dict:
        """Get alert summary"""
        
        try:
            total_alerts = len(self.alerts)
            active_alerts = len([alert for alert in self.alerts if not alert['resolved']])
            acknowledged_alerts = len([alert for alert in self.alerts if alert['acknowledged']])
            resolved_alerts = len([alert for alert in self.alerts if alert['resolved']])
            
            severity_counts = {}
            for alert in self.alerts:
                severity = alert['severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            summary = {
                'total_alerts': total_alerts,
                'active_alerts': active_alerts,
                'acknowledged_alerts': acknowledged_alerts,
                'resolved_alerts': resolved_alerts,
                'severity_distribution': severity_counts,
                'alerting_active': self.alerting_active,
                'alert_rules_count': len(self.alert_rules)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {}
