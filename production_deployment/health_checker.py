#!/usr/bin/env python3
"""
Health Checker
Phase 4: Production Deployment & Monitoring
"""

import logging
import time
import requests
import psutil
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class HealthChecker:
    """Health checking system for production components"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.health_status = {}
        self.health_history = []
        self.checking_active = False
        self.checking_thread = None
        
        # Health check intervals
        self.system_check_interval = self.config.get('system_check_interval', 30)
        self.service_check_interval = self.config.get('service_check_interval', 60)
        self.database_check_interval = self.config.get('database_check_interval', 45)
        
        logger.info("Initialized HealthChecker")
    
    def start_health_checking(self) -> bool:
        """Start health checking"""
        
        try:
            if self.checking_active:
                logger.warning("Health checking is already active")
                return True
            
            logger.info("Starting health checking...")
            
            self.checking_active = True
            self.checking_thread = threading.Thread(target=self._health_checking_loop, daemon=True)
            self.checking_thread.start()
            
            logger.info("Health checking started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start health checking: {e}")
            return False
    
    def stop_health_checking(self) -> bool:
        """Stop health checking"""
        
        try:
            logger.info("Stopping health checking...")
            
            self.checking_active = False
            if self.checking_thread and self.checking_thread.is_alive():
                self.checking_thread.join(timeout=5)
            
            logger.info("Health checking stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop health checking: {e}")
            return False
    
    def _health_checking_loop(self):
        """Main health checking loop"""
        
        while self.checking_active:
            try:
                # Perform system health checks
                self._check_system_health()
                
                # Perform service health checks
                self._check_service_health()
                
                # Perform database health checks
                self._check_database_health()
                
                # Store health history
                self._store_health_history()
                
                # Sleep for checking interval
                time.sleep(self.system_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health checking loop: {e}")
                time.sleep(5)
    
    def _check_system_health(self):
        """Check system health"""
        
        try:
            # CPU health check
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_healthy = cpu_percent < 90
            
            # Memory health check
            memory = psutil.virtual_memory()
            memory_healthy = memory.percent < 85
            
            # Disk health check
            disk = psutil.disk_usage('/')
            disk_healthy = disk.percent < 90
            
            # Network health check
            network_healthy = True  # Mock network check
            
            system_health = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'HEALTHY' if all([cpu_healthy, memory_healthy, disk_healthy, network_healthy]) else 'UNHEALTHY',
                'components': {
                    'cpu': {
                        'status': 'HEALTHY' if cpu_healthy else 'UNHEALTHY',
                        'usage_percent': cpu_percent,
                        'threshold': 90
                    },
                    'memory': {
                        'status': 'HEALTHY' if memory_healthy else 'UNHEALTHY',
                        'usage_percent': memory.percent,
                        'threshold': 85
                    },
                    'disk': {
                        'status': 'HEALTHY' if disk_healthy else 'UNHEALTHY',
                        'usage_percent': disk.percent,
                        'threshold': 90
                    },
                    'network': {
                        'status': 'HEALTHY' if network_healthy else 'UNHEALTHY',
                        'response_time_ms': 15.2
                    }
                }
            }
            
            self.health_status['system'] = system_health
            logger.debug(f"System health check: {system_health['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to check system health: {e}")
    
    def _check_service_health(self):
        """Check service health"""
        
        try:
            # Mock service health checks
            services = {
                'api': {
                    'url': 'http://localhost:8080/health',
                    'timeout': 5
                },
                'monitoring': {
                    'url': 'http://localhost:9090/health',
                    'timeout': 5
                },
                'trading_engine': {
                    'url': 'http://localhost:8081/health',
                    'timeout': 5
                }
            }
            
            service_health = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'HEALTHY',
                'services': {}
            }
            
            unhealthy_services = 0
            
            for service_name, service_config in services.items():
                try:
                    # Mock service check (in real implementation, this would make HTTP requests)
                    response_time = 25.5  # Mock response time
                    service_status = 'HEALTHY'  # Mock status
                    
                    service_health['services'][service_name] = {
                        'status': service_status,
                        'response_time_ms': response_time,
                        'last_check': datetime.now().isoformat()
                    }
                    
                    if service_status != 'HEALTHY':
                        unhealthy_services += 1
                        
                except Exception as e:
                    service_health['services'][service_name] = {
                        'status': 'UNHEALTHY',
                        'error': str(e),
                        'last_check': datetime.now().isoformat()
                    }
                    unhealthy_services += 1
            
            # Determine overall service health
            if unhealthy_services > 0:
                service_health['overall_status'] = 'UNHEALTHY'
            
            self.health_status['services'] = service_health
            logger.debug(f"Service health check: {service_health['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to check service health: {e}")
    
    def _check_database_health(self):
        """Check database health"""
        
        try:
            # Mock database health checks
            databases = {
                'clickhouse': {
                    'host': 'clickhouse-service',
                    'port': 9000,
                    'database': 'trading_data'
                },
                'redis': {
                    'host': 'redis-service',
                    'port': 6379
                }
            }
            
            database_health = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'HEALTHY',
                'databases': {}
            }
            
            unhealthy_databases = 0
            
            for db_name, db_config in databases.items():
                try:
                    # Mock database check (in real implementation, this would test connections)
                    connection_time = 12.5  # Mock connection time
                    db_status = 'HEALTHY'  # Mock status
                    
                    database_health['databases'][db_name] = {
                        'status': db_status,
                        'connection_time_ms': connection_time,
                        'last_check': datetime.now().isoformat(),
                        'connection_count': 15 if db_name == 'clickhouse' else 8
                    }
                    
                    if db_status != 'HEALTHY':
                        unhealthy_databases += 1
                        
                except Exception as e:
                    database_health['databases'][db_name] = {
                        'status': 'UNHEALTHY',
                        'error': str(e),
                        'last_check': datetime.now().isoformat()
                    }
                    unhealthy_databases += 1
            
            # Determine overall database health
            if unhealthy_databases > 0:
                database_health['overall_status'] = 'UNHEALTHY'
            
            self.health_status['databases'] = database_health
            logger.debug(f"Database health check: {database_health['overall_status']}")
            
        except Exception as e:
            logger.error(f"Failed to check database health: {e}")
    
    def _store_health_history(self):
        """Store health check history"""
        
        try:
            health_record = {
                'timestamp': datetime.now().isoformat(),
                'system': self.health_status.get('system', {}),
                'services': self.health_status.get('services', {}),
                'databases': self.health_status.get('databases', {})
            }
            
            self.health_history.append(health_record)
            
            # Keep only recent health history (last 1000 entries)
            if len(self.health_history) > 1000:
                self.health_history = self.health_history[-1000:]
                
        except Exception as e:
            logger.error(f"Failed to store health history: {e}")
    
    def get_health_status(self) -> Dict:
        """Get current health status"""
        
        return {
            'overall_status': self._calculate_overall_health(),
            'system': self.health_status.get('system', {}),
            'services': self.health_status.get('services', {}),
            'databases': self.health_status.get('databases', {}),
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall health status"""
        
        try:
            unhealthy_components = 0
            
            # Check system health
            system_health = self.health_status.get('system', {})
            if system_health.get('overall_status') == 'UNHEALTHY':
                unhealthy_components += 1
            
            # Check service health
            service_health = self.health_status.get('services', {})
            if service_health.get('overall_status') == 'UNHEALTHY':
                unhealthy_components += 1
            
            # Check database health
            database_health = self.health_status.get('databases', {})
            if database_health.get('overall_status') == 'UNHEALTHY':
                unhealthy_components += 1
            
            if unhealthy_components >= 2:
                return 'CRITICAL'
            elif unhealthy_components == 1:
                return 'WARNING'
            else:
                return 'HEALTHY'
                
        except Exception as e:
            logger.error(f"Failed to calculate overall health: {e}")
            return 'UNKNOWN'
    
    def perform_manual_health_check(self) -> Dict:
        """Perform manual health check"""
        
        try:
            logger.info("Performing manual health check...")
            
            # Perform all health checks
            self._check_system_health()
            self._check_service_health()
            self._check_database_health()
            
            # Get overall status
            health_status = self.get_health_status()
            
            logger.info(f"Manual health check completed: {health_status['overall_status']}")
            return health_status
            
        except Exception as e:
            logger.error(f"Manual health check failed: {e}")
            return {'overall_status': 'ERROR', 'error': str(e)}
    
    def get_health_summary(self) -> Dict:
        """Get health checking summary"""
        
        return {
            'health_history_count': len(self.health_history),
            'checking_active': self.checking_active,
            'last_health_status': self.get_health_status()['overall_status'],
            'check_intervals': {
                'system': self.system_check_interval,
                'service': self.service_check_interval,
                'database': self.database_check_interval
            }
        }
