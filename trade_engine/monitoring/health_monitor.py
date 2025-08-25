#!/usr/bin/env python3
"""
Health Monitor System
====================

Comprehensive health monitoring system for trading engine components,
providing real-time health checks, status tracking, and dependency monitoring.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import psutil
import time

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ComponentType(Enum):
    """Component types"""
    SYSTEM = "system"
    DATABASE = "database"
    MARKET_DATA = "market_data"
    STRATEGY = "strategy"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    MONITORING = "monitoring"

@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    component: str
    component_type: ComponentType
    check_function: Callable[[], bool]
    description: str = ""
    interval_seconds: float = 60
    timeout_seconds: float = 30
    retries: int = 3
    enabled: bool = True

@dataclass
class HealthStatus:
    """Health status data"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    last_check: datetime
    next_check: datetime
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    check_duration: float = 0.0
    consecutive_failures: int = 0
    uptime_percentage: float = 100.0

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    process_count: int
    load_average: List[float]

class HealthMonitor:
    """
    Advanced health monitoring system.
    
    Features:
    - Component health tracking
    - Automated health checks
    - Dependency monitoring
    - System metrics collection
    - Health status aggregation
    - Alert integration
    """
    
    def __init__(self, check_interval: float = 60):
        self.check_interval = check_interval
        
        # Health check management
        self.health_checks: Dict[str, HealthCheck] = {}
        self.health_statuses: Dict[str, HealthStatus] = {}
        self.component_dependencies: Dict[str, Set[str]] = {}
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.monitoring_lock = threading.RLock()
        
        # System metrics
        self.system_metrics_history: List[SystemMetrics] = []
        self.max_history_size = 1440  # 24 hours of minute-by-minute data
        
        # Health statistics
        self.health_stats = {
            'total_components': 0,
            'healthy_components': 0,
            'warning_components': 0,
            'unhealthy_components': 0,
            'critical_components': 0,
            'unknown_components': 0
        }
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[str, HealthStatus, str], None]] = []
        
        logger.info("HealthMonitor initialized")
    
    async def start_monitoring(self):
        """Start health monitoring"""
        if self.is_monitoring:
            logger.warning("Health monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Setup default system health checks
        self._setup_system_health_checks()
        
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    def register_health_check(self, health_check: HealthCheck):
        """Register a new health check"""
        self.health_checks[health_check.name] = health_check
        
        # Initialize health status
        self.health_statuses[health_check.name] = HealthStatus(
            component=health_check.component,
            component_type=health_check.component_type,
            status=HealthStatus.UNKNOWN,
            last_check=datetime.now(),
            next_check=datetime.now() + timedelta(seconds=health_check.interval_seconds),
            message="Not yet checked"
        )
        
        logger.info(f"Registered health check: {health_check.name}")
    
    def unregister_health_check(self, check_name: str):
        """Unregister a health check"""
        if check_name in self.health_checks:
            del self.health_checks[check_name]
            if check_name in self.health_statuses:
                del self.health_statuses[check_name]
            logger.info(f"Unregistered health check: {check_name}")
    
    def add_component_dependency(self, component: str, depends_on: str):
        """Add a dependency relationship between components"""
        if component not in self.component_dependencies:
            self.component_dependencies[component] = set()
        
        self.component_dependencies[component].add(depends_on)
        logger.info(f"Added dependency: {component} depends on {depends_on}")
    
    async def run_health_check(self, check_name: str) -> HealthStatus:
        """Run a specific health check"""
        if check_name not in self.health_checks:
            logger.error(f"Health check not found: {check_name}")
            return HealthStatus.UNKNOWN
        
        health_check = self.health_checks[check_name]
        
        if not health_check.enabled:
            return HealthStatus.UNKNOWN
        
        start_time = time.time()
        status = HealthStatus.UNKNOWN
        message = ""
        details = {}
        
        try:
            # Run the health check with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, health_check.check_function
                ),
                timeout=health_check.timeout_seconds
            )
            
            if result:
                status = HealthStatus.HEALTHY
                message = "Health check passed"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Health check failed"
                
        except asyncio.TimeoutError:
            status = HealthStatus.CRITICAL
            message = f"Health check timed out after {health_check.timeout_seconds}s"
            
        except Exception as e:
            status = HealthStatus.CRITICAL
            message = f"Health check error: {str(e)}"
            details['error'] = str(e)
        
        check_duration = time.time() - start_time
        
        # Update health status
        with self.monitoring_lock:
            if check_name in self.health_statuses:
                health_status = self.health_statuses[check_name]
                
                # Update consecutive failures
                if status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    health_status.consecutive_failures += 1
                else:
                    health_status.consecutive_failures = 0
                
                # Update status
                health_status.status = status
                health_status.last_check = datetime.now()
                health_status.next_check = datetime.now() + timedelta(seconds=health_check.interval_seconds)
                health_status.message = message
                health_status.details = details
                health_status.check_duration = check_duration
                
                # Calculate uptime percentage (simplified)
                if status == HealthStatus.HEALTHY:
                    health_status.uptime_percentage = min(
                        100.0,
                        health_status.uptime_percentage + (100 / (24 * 60))  # Assume minute checks
                    )
                else:
                    health_status.uptime_percentage = max(
                        0.0,
                        health_status.uptime_percentage - (100 / (24 * 60))
                    )
        
        # Send alerts if status changed to unhealthy
        if status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
            self._send_health_alert(check_name, status, message)
        
        logger.debug(f"Health check completed: {check_name} -> {status.value}")
        return status
    
    async def run_all_health_checks(self) -> Dict[str, HealthStatus]:
        """Run all enabled health checks"""
        results = {}
        
        for check_name, health_check in self.health_checks.items():
            if health_check.enabled:
                results[check_name] = await self.run_health_check(check_name)
        
        return results
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_stats = {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv
            }
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Unix-like systems)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]  # Windows fallback
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_stats,
                process_count=process_count,
                load_average=load_average
            )
            
            # Store in history
            self.system_metrics_history.append(metrics)
            
            # Keep only recent history
            if len(self.system_metrics_history) > self.max_history_size:
                self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                process_count=0,
                load_average=[0.0, 0.0, 0.0]
            )
    
    def get_overall_health_status(self) -> HealthStatus:
        """Get overall system health status"""
        with self.monitoring_lock:
            if not self.health_statuses:
                return HealthStatus.UNKNOWN
            
            # Count statuses
            status_counts = {status: 0 for status in HealthStatus}
            
            for health_status in self.health_statuses.values():
                status_counts[health_status.status] += 1
            
            # Determine overall status
            if status_counts[HealthStatus.CRITICAL] > 0:
                return HealthStatus.CRITICAL
            elif status_counts[HealthStatus.UNHEALTHY] > 0:
                return HealthStatus.UNHEALTHY
            elif status_counts[HealthStatus.WARNING] > 0:
                return HealthStatus.WARNING
            elif status_counts[HealthStatus.HEALTHY] > 0:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
    
    def get_component_health(self, component: str) -> List[HealthStatus]:
        """Get health status for a specific component"""
        with self.monitoring_lock:
            return [
                status for status in self.health_statuses.values()
                if status.component == component
            ]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary statistics"""
        with self.monitoring_lock:
            # Update statistics
            self.health_stats['total_components'] = len(self.health_statuses)
            
            status_counts = {status: 0 for status in HealthStatus}
            for health_status in self.health_statuses.values():
                status_counts[health_status.status] += 1
            
            self.health_stats.update({
                'healthy_components': status_counts[HealthStatus.HEALTHY],
                'warning_components': status_counts[HealthStatus.WARNING],
                'unhealthy_components': status_counts[HealthStatus.UNHEALTHY],
                'critical_components': status_counts[HealthStatus.CRITICAL],
                'unknown_components': status_counts[HealthStatus.UNKNOWN]
            })
            
            return {
                'overall_status': self.get_overall_health_status().value,
                'statistics': self.health_stats.copy(),
                'last_update': datetime.now().isoformat()
            }
    
    def get_system_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get system metrics summary for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_metrics = [
            metrics for metrics in self.system_metrics_history
            if metrics.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_disk = sum(m.disk_usage for m in recent_metrics) / len(recent_metrics)
        
        # Get latest metrics
        latest_metrics = recent_metrics[-1]
        
        return {
            'period_hours': hours,
            'sample_count': len(recent_metrics),
            'averages': {
                'cpu_usage': avg_cpu,
                'memory_usage': avg_memory,
                'disk_usage': avg_disk
            },
            'current': {
                'cpu_usage': latest_metrics.cpu_usage,
                'memory_usage': latest_metrics.memory_usage,
                'disk_usage': latest_metrics.disk_usage,
                'process_count': latest_metrics.process_count,
                'load_average': latest_metrics.load_average
            },
            'timestamp': latest_metrics.timestamp.isoformat()
        }
    
    def _setup_system_health_checks(self):
        """Setup default system health checks"""
        # CPU health check
        def check_cpu_health():
            cpu_usage = psutil.cpu_percent(interval=1)
            return cpu_usage < 90  # Alert if CPU > 90%
        
        self.register_health_check(HealthCheck(
            name="system_cpu",
            component="system",
            component_type=ComponentType.SYSTEM,
            check_function=check_cpu_health,
            description="Monitor CPU usage",
            interval_seconds=60
        ))
        
        # Memory health check
        def check_memory_health():
            memory = psutil.virtual_memory()
            return memory.percent < 85  # Alert if memory > 85%
        
        self.register_health_check(HealthCheck(
            name="system_memory",
            component="system",
            component_type=ComponentType.SYSTEM,
            check_function=check_memory_health,
            description="Monitor memory usage",
            interval_seconds=60
        ))
        
        # Disk health check
        def check_disk_health():
            disk = psutil.disk_usage('/')
            return disk.percent < 90  # Alert if disk > 90%
        
        self.register_health_check(HealthCheck(
            name="system_disk",
            component="system",
            component_type=ComponentType.SYSTEM,
            check_function=check_disk_health,
            description="Monitor disk usage",
            interval_seconds=300  # Check every 5 minutes
        ))
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Collect system metrics
                self.collect_system_metrics()
                
                # Run health checks that are due
                now = datetime.now()
                checks_to_run = []
                
                with self.monitoring_lock:
                    for check_name, health_status in self.health_statuses.items():
                        if now >= health_status.next_check:
                            checks_to_run.append(check_name)
                
                # Run due health checks
                for check_name in checks_to_run:
                    await self.run_health_check(check_name)
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def _send_health_alert(self, check_name: str, status: HealthStatus, message: str):
        """Send health alerts"""
        for callback in self.alert_callbacks:
            try:
                callback(check_name, status, message)
            except Exception as e:
                logger.error(f"Error sending health alert: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, HealthStatus, str], None]):
        """Add an alert callback"""
        self.alert_callbacks.append(callback)
        logger.info("Added health alert callback")

# Global health monitor instance
health_monitor = HealthMonitor()

async def start_health_monitoring():
    """Start global health monitoring"""
    await health_monitor.start_monitoring()

async def stop_health_monitoring():
    """Stop global health monitoring"""
    await health_monitor.stop_monitoring()
