"""
Health Check System - Core Engine
=================================

Health monitoring and check endpoints for all major core_engine components.
Provides real-time status monitoring and automated health verification.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .logging import get_logger
from .exceptions import ErrorContext, handle_error

logger = get_logger("health")

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0

    @property
    def is_healthy(self) -> bool:
        """Check if the component is healthy"""
        return self.status == HealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        """Check if the component is degraded"""
        return self.status == HealthStatus.DEGRADED

class HealthCheck:
    """Base class for health checks"""

    def __init__(self, name: str, component: str, timeout_seconds: float = 5.0):
        self.name = name
        self.component = component
        self.timeout_seconds = timeout_seconds

    async def check(self) -> HealthCheckResult:
        """Perform the health check"""
        raise NotImplementedError("Subclasses must implement check()")

class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity"""

    def __init__(self, component: str, connection_check_func: Callable[[], Awaitable[bool]]):
        super().__init__("database", component)
        self.connection_check_func = connection_check_func

    async def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            is_connected = await asyncio.wait_for(
                self.connection_check_func(),
                timeout=self.timeout_seconds
            )
            response_time = (time.time() - start_time) * 1000

            if is_connected:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    details={"connection_status": "connected"},
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.UNHEALTHY,
                    message="Database connection failed",
                    details={"connection_status": "disconnected"},
                    response_time_ms=response_time
                )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message="Database health check timed out",
                details={"error": "timeout"},
                response_time_ms=self.timeout_seconds * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Database health check failed: {str(e)}",
                details={"error": str(e)},
                response_time_ms=(time.time() - start_time) * 1000
            )

class BrokerHealthCheck(HealthCheck):
    """Health check for broker connectivity"""

    def __init__(self, component: str, broker_check_func: Callable[[], Awaitable[bool]]):
        super().__init__("broker", component)
        self.broker_check_func = broker_check_func

    async def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            is_connected = await asyncio.wait_for(
                self.broker_check_func(),
                timeout=self.timeout_seconds
            )
            response_time = (time.time() - start_time) * 1000

            if is_connected:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.HEALTHY,
                    message="Broker connection successful",
                    details={"connection_status": "connected"},
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.UNHEALTHY,
                    message="Broker connection failed",
                    details={"connection_status": "disconnected"},
                    response_time_ms=response_time
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Broker health check failed: {str(e)}",
                details={"error": str(e)},
                response_time_ms=(time.time() - start_time) * 1000
            )

class ComponentHealthCheck(HealthCheck):
    """Generic health check for component status"""

    def __init__(self, component: str, health_check_func: Callable[[], Awaitable[Dict[str, Any]]]):
        super().__init__("component", component)
        self.health_check_func = health_check_func

    async def check(self) -> HealthCheckResult:
        start_time = time.time()
        try:
            health_data = await asyncio.wait_for(
                self.health_check_func(),
                timeout=self.timeout_seconds
            )
            response_time = (time.time() - start_time) * 1000

            # Determine status based on health data
            status = HealthStatus.HEALTHY
            message = "Component is healthy"

            if "status" in health_data:
                status_str = health_data["status"].lower()
                if status_str == "degraded":
                    status = HealthStatus.DEGRADED
                    message = "Component is degraded"
                elif status_str in ("unhealthy", "error", "failed"):
                    status = HealthStatus.UNHEALTHY
                    message = "Component is unhealthy"

            return HealthCheckResult(
                component=self.component,
                status=status,
                message=message,
                details=health_data,
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.component,
                status=HealthStatus.UNHEALTHY,
                message=f"Component health check failed: {str(e)}",
                details={"error": str(e)},
                response_time_ms=(time.time() - start_time) * 1000
            )

class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage"""

    def __init__(self, component: str, max_memory_mb: float = 1000.0):
        super().__init__("memory", component)
        self.max_memory_mb = max_memory_mb

    async def check(self) -> HealthCheckResult:
        import psutil
        import os

        start_time = time.time()
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            details = {
                "memory_mb": round(memory_mb, 2),
                "max_memory_mb": self.max_memory_mb,
                "memory_percent": round(memory_mb / self.max_memory_mb * 100, 2)
            }

            if memory_mb > self.max_memory_mb:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Memory usage too high: {memory_mb:.1f}MB > {self.max_memory_mb}MB",
                    details=details,
                    response_time_ms=(time.time() - start_time) * 1000
                )
            elif memory_mb > self.max_memory_mb * 0.8:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.DEGRADED,
                    message=f"Memory usage high: {memory_mb:.1f}MB",
                    details=details,
                    response_time_ms=(time.time() - start_time) * 1000
                )
            else:
                return HealthCheckResult(
                    component=self.component,
                    status=HealthStatus.HEALTHY,
                    message=f"Memory usage normal: {memory_mb:.1f}MB",
                    details=details,
                    response_time_ms=(time.time() - start_time) * 1000
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.component,
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                details={"error": str(e)},
                response_time_ms=(time.time() - start_time) * 1000
            )

class HealthMonitor:
    """
    Health monitoring system for core_engine components

    Provides centralized health checking with automatic monitoring,
    alerting, and status reporting.
    """

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.alert_callbacks: List[Callable[[HealthCheckResult], Awaitable[None]]] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self.check_interval = 30.0  # seconds

    def add_check(self, check: HealthCheck):
        """Add a health check"""
        self.checks[check.name] = check
        logger.info(f"Added health check: {check.name} for component {check.component}")

    def remove_check(self, check_name: str):
        """Remove a health check"""
        if check_name in self.checks:
            del self.checks[check_name]
            logger.info(f"Removed health check: {check_name}")

    def add_alert_callback(self, callback: Callable[[HealthCheckResult], Awaitable[None]]):
        """Add callback for health alerts"""
        self.alert_callbacks.append(callback)

    async def run_check(self, check_name: str) -> Optional[HealthCheckResult]:
        """Run a specific health check"""
        if check_name not in self.checks:
            logger.warning(f"Health check not found: {check_name}")
            return None

        check = self.checks[check_name]
        try:
            result = await check.check()
            self.results[check_name] = result

            # Update consecutive failures
            if result.is_healthy:
                result.last_success = datetime.now()
                result.consecutive_failures = 0
            else:
                result.consecutive_failures = self.results.get(check_name, result).consecutive_failures + 1

            # Trigger alerts for unhealthy components
            if not result.is_healthy:
                await self._trigger_alerts(result)

            logger.debug(f"Health check {check_name}: {result.status.value} - {result.message}")
            return result

        except Exception as e:
            logger.error(f"Health check {check_name} failed with exception: {e}")
            result = HealthCheckResult(
                component=check.component,
                status=HealthStatus.UNKNOWN,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)}
            )
            self.results[check_name] = result
            return result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        results = {}
        for check_name in self.checks:
            result = await self.run_check(check_name)
            if result:
                results[check_name] = result

        return results

    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
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

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self.run_all_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _trigger_alerts(self, result: HealthCheckResult):
        """Trigger alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                await callback(result)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.results:
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "total_checks": 0,
                "healthy_checks": 0,
                "degraded_checks": 0,
                "unhealthy_checks": 0,
                "unknown_checks": 0
            }

        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.UNKNOWN: 0
        }

        for result in self.results.values():
            status_counts[result.status] += 1

        # Determine overall status
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.DEGRADED] > 0:
            overall_status = HealthStatus.DEGRADED
        elif status_counts[HealthStatus.HEALTHY] > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        return {
            "overall_status": overall_status.value,
            "total_checks": len(self.results),
            "healthy_checks": status_counts[HealthStatus.HEALTHY],
            "degraded_checks": status_counts[HealthStatus.DEGRADED],
            "unhealthy_checks": status_counts[HealthStatus.UNHEALTHY],
            "unknown_checks": status_counts[HealthStatus.UNKNOWN],
            "last_check": max(r.timestamp for r in self.results.values()).isoformat() if self.results else None
        }

    def get_component_status(self, component: str) -> Dict[str, Any]:
        """Get health status for a specific component"""
        component_results = {
            name: result for name, result in self.results.items()
            if result.component == component
        }

        if not component_results:
            return {"status": HealthStatus.UNKNOWN.value, "checks": {}}

        # Determine component status
        statuses = [r.status for r in component_results.values()]
        if HealthStatus.UNHEALTHY in statuses:
            status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            status = HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            status = HealthStatus.HEALTHY
        else:
            status = HealthStatus.UNKNOWN

        return {
            "status": status.value,
            "checks": {
                name: {
                    "status": result.status.value,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "timestamp": result.timestamp.isoformat()
                }
                for name, result in component_results.items()
            }
        }

# Global health monitor instance
_monitor = HealthMonitor()

def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor"""
    return _monitor

def add_health_check(check: HealthCheck):
    """Add a health check to the global monitor"""
    _monitor.add_check(check)

def create_database_health_check(component: str, connection_check_func: Callable[[], Awaitable[bool]]) -> DatabaseHealthCheck:
    """Create a database health check"""
    return DatabaseHealthCheck(component, connection_check_func)

def create_broker_health_check(component: str, broker_check_func: Callable[[], Awaitable[bool]]) -> BrokerHealthCheck:
    """Create a broker health check"""
    return BrokerHealthCheck(component, broker_check_func)

def create_component_health_check(component: str, health_check_func: Callable[[], Awaitable[Dict[str, Any]]]) -> ComponentHealthCheck:
    """Create a component health check"""
    return ComponentHealthCheck(component, health_check_func)

def create_memory_health_check(component: str, max_memory_mb: float = 1000.0) -> MemoryHealthCheck:
    """Create a memory health check"""
    return MemoryHealthCheck(component, max_memory_mb)