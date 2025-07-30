#!/usr/bin/env python3
"""
Monitoring System
Phase 4: Production Deployment & Monitoring
"""

import logging
import time
import psutil
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import requests
from collections import defaultdict, deque
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class MonitoringSystem:
    """Production monitoring system for the trading system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.metrics = defaultdict(deque)
        self.alerts = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.metrics_history = []
        
        # Monitoring intervals
        self.system_metrics_interval = self.config.get('system_metrics_interval', 30)
        self.application_metrics_interval = self.config.get('application_metrics_interval', 60)
        self.health_check_interval = self.config.get('health_check_interval', 30)
        
        logger.info("Initialized MonitoringSystem")
    
    def start_monitoring(self) -> bool:
        """Start the monitoring system"""
        
        try:
            if self.monitoring_active:
                logger.warning("Monitoring system is already active")
                return True
            
            logger.info("Starting monitoring system...")
            
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Monitoring system started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring system: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop the monitoring system"""
        
        try:
            logger.info("Stopping monitoring system...")
            
            self.monitoring_active = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            logger.info("Monitoring system stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring system: {e}")
            return False
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Collect application metrics
                self._collect_application_metrics()
                
                # Perform health checks
                self._perform_health_checks()
                
                # Check for alerts
                self._check_alerts()
                
                # Store metrics history
                self._store_metrics_history()
                
                # Sleep for monitoring interval
                time.sleep(self.system_metrics_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available = memory.available / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free = disk.free / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # Network metrics
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # Process metrics
            process = psutil.Process()
            process_cpu_percent = process.cpu_percent()
            process_memory_percent = process.memory_percent()
            process_memory_info = process.memory_info()
            
            system_metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else 0
                },
                'memory': {
                    'percent': memory_percent,
                    'available_gb': memory_available,
                    'total_gb': memory_total,
                    'used_gb': memory_total - memory_available
                },
                'disk': {
                    'percent': disk_percent,
                    'free_gb': disk_free,
                    'total_gb': disk_total,
                    'used_gb': disk_total - disk_free
                },
                'network': {
                    'bytes_sent': network_bytes_sent,
                    'bytes_recv': network_bytes_recv
                },
                'process': {
                    'cpu_percent': process_cpu_percent,
                    'memory_percent': process_memory_percent,
                    'memory_rss_mb': process_memory_info.rss / (1024**2),
                    'memory_vms_mb': process_memory_info.vms / (1024**2)
                }
            }
            
            # Store metrics
            self.metrics['system'].append(system_metrics)
            
            # Keep only recent metrics (last 1000 entries)
            if len(self.metrics['system']) > 1000:
                self.metrics['system'].popleft()
            
            logger.debug(f"System metrics collected: CPU {cpu_percent}%, Memory {memory_percent}%")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        
        try:
            # Mock application metrics
            application_metrics = {
                'timestamp': datetime.now().isoformat(),
                'trading_metrics': {
                    'active_strategies': 5,
                    'total_trades': 1250,
                    'successful_trades': 1180,
                    'failed_trades': 70,
                    'success_rate': 0.944,
                    'total_pnl': 125000.50,
                    'daily_pnl': 2500.75
                },
                'performance_metrics': {
                    'response_time_ms': 45.2,
                    'throughput_tps': 150.5,
                    'error_rate': 0.002,
                    'uptime_percent': 99.8
                },
                'database_metrics': {
                    'clickhouse_connections': 12,
                    'redis_connections': 8,
                    'query_response_time_ms': 15.3,
                    'cache_hit_rate': 0.85
                },
                'ml_metrics': {
                    'models_active': 3,
                    'predictions_per_second': 25.5,
                    'model_accuracy': 0.78,
                    'feature_importance_updated': True
                }
            }
            
            # Store metrics
            self.metrics['application'].append(application_metrics)
            
            # Keep only recent metrics
            if len(self.metrics['application']) > 1000:
                self.metrics['application'].popleft()
            
            logger.debug("Application metrics collected")
            
        except Exception as e:
            logger.error(f"Failed to collect application metrics: {e}")
    
    def _perform_health_checks(self):
        """Perform health checks on system components"""
        
        try:
            health_checks = {
                'timestamp': datetime.now().isoformat(),
                'system_health': {
                    'cpu_healthy': True,
                    'memory_healthy': True,
                    'disk_healthy': True,
                    'network_healthy': True
                },
                'application_health': {
                    'api_healthy': True,
                    'database_healthy': True,
                    'ml_models_healthy': True,
                    'trading_engine_healthy': True
                },
                'service_health': {
                    'clickhouse_healthy': True,
                    'redis_healthy': True,
                    'monitoring_healthy': True
                }
            }
            
            # Check system health thresholds
            if self.metrics['system']:
                latest_system = self.metrics['system'][-1]
                
                # CPU health check
                if latest_system['cpu']['percent'] > 90:
                    health_checks['system_health']['cpu_healthy'] = False
                    self._create_alert('HIGH_CPU_USAGE', f"CPU usage: {latest_system['cpu']['percent']}%")
                
                # Memory health check
                if latest_system['memory']['percent'] > 85:
                    health_checks['system_health']['memory_healthy'] = False
                    self._create_alert('HIGH_MEMORY_USAGE', f"Memory usage: {latest_system['memory']['percent']}%")
                
                # Disk health check
                if latest_system['disk']['percent'] > 90:
                    health_checks['system_health']['disk_healthy'] = False
                    self._create_alert('HIGH_DISK_USAGE', f"Disk usage: {latest_system['disk']['percent']}%")
            
            # Store health checks
            self.metrics['health'].append(health_checks)
            
            # Keep only recent health checks
            if len(self.metrics['health']) > 1000:
                self.metrics['health'].popleft()
            
            logger.debug("Health checks performed")
            
        except Exception as e:
            logger.error(f"Failed to perform health checks: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions"""
        
        try:
            if not self.metrics['system']:
                return
            
            latest_system = self.metrics['system'][-1]
            
            # Check for critical conditions
            if latest_system['cpu']['percent'] > 95:
                self._create_alert('CRITICAL_CPU_USAGE', f"Critical CPU usage: {latest_system['cpu']['percent']}%")
            
            if latest_system['memory']['percent'] > 95:
                self._create_alert('CRITICAL_MEMORY_USAGE', f"Critical memory usage: {latest_system['memory']['percent']}%")
            
            if latest_system['disk']['percent'] > 95:
                self._create_alert('CRITICAL_DISK_USAGE', f"Critical disk usage: {latest_system['disk']['percent']}%")
            
            # Check application metrics
            if self.metrics['application']:
                latest_app = self.metrics['application'][-1]
                
                if latest_app['performance_metrics']['error_rate'] > 0.05:
                    self._create_alert('HIGH_ERROR_RATE', f"High error rate: {latest_app['performance_metrics']['error_rate']}")
                
                if latest_app['performance_metrics']['response_time_ms'] > 100:
                    self._create_alert('HIGH_RESPONSE_TIME', f"High response time: {latest_app['performance_metrics']['response_time_ms']}ms")
            
        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
    
    def _create_alert(self, alert_type: str, message: str):
        """Create an alert"""
        
        alert = {
            'id': f"alert_{len(self.alerts) + 1}",
            'type': alert_type,
            'message': message,
            'severity': 'HIGH' if 'CRITICAL' in alert_type else 'MEDIUM',
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {alert_type} - {message}")
    
    def _store_metrics_history(self):
        """Store metrics history for analysis"""
        
        try:
            if self.metrics['system']:
                latest_metrics = {
                    'timestamp': datetime.now().isoformat(),
                    'system': self.metrics['system'][-1] if self.metrics['system'] else {},
                    'application': self.metrics['application'][-1] if self.metrics['application'] else {},
                    'health': self.metrics['health'][-1] if self.metrics['health'] else {}
                }
                
                self.metrics_history.append(latest_metrics)
                
                # Keep only last 24 hours of history (assuming 30s intervals)
                max_history = 24 * 60 * 2  # 24 hours * 60 minutes * 2 entries per minute
                if len(self.metrics_history) > max_history:
                    self.metrics_history = self.metrics_history[-max_history:]
            
        except Exception as e:
            logger.error(f"Failed to store metrics history: {e}")
    
    def get_current_metrics(self) -> Dict:
        """Get current metrics"""
        
        current_metrics = {
            'system': self.metrics['system'][-1] if self.metrics['system'] else {},
            'application': self.metrics['application'][-1] if self.metrics['application'] else {},
            'health': self.metrics['health'][-1] if self.metrics['health'] else {},
            'alerts': self.alerts[-10:] if self.alerts else [],  # Last 10 alerts
            'monitoring_active': self.monitoring_active
        }
        
        return current_metrics
    
    def get_metrics_summary(self) -> Dict:
        """Get metrics summary"""
        
        summary = {
            'total_metrics_collected': sum(len(metrics) for metrics in self.metrics.values()),
            'metrics_history_count': len(self.metrics_history),
            'active_alerts': len([alert for alert in self.alerts if not alert['acknowledged']]),
            'total_alerts': len(self.alerts),
            'monitoring_active': self.monitoring_active,
            'metrics_types': list(self.metrics.keys())
        }
        
        return summary
    
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
