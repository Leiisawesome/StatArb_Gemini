"""
System Monitoring Module for HierarchicalSystemOrchestrator
==========================================================

Handles system metrics, performance tracking, and health monitoring.
Extracted from the main orchestrator for better maintainability.

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Modular Architecture)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

# Import ISystemComponent for orchestrator integration (Rule 1)
from .interfaces import ISystemComponent

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    total_components: int
    operational_components: int
    failed_components: int
    system_uptime: float
    memory_usage: float
    cpu_usage: float
    error_rate: float
    throughput: float


class SystemMonitor(ISystemComponent):
    """
    Handles system monitoring, metrics collection, and performance tracking

    Implements ISystemComponent for orchestrator integration (Rule 1).
    """

    def __init__(self):
        self.system_metrics: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.started_at: Optional[datetime] = None
        self.is_monitoring: bool = False

        # ISystemComponent state
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None

    async def start_monitoring(self) -> None:
        """Start continuous system monitoring"""

        try:
            if self.is_monitoring:
                return

            self.started_at = datetime.now()
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("📊 System monitoring started")

        except Exception as e:
            logger.error(f"❌ Failed to start system monitoring: {e}")

    async def stop_monitoring(self) -> None:
        """Stop system monitoring"""

        try:
            self.is_monitoring = False

            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

            logger.info("📊 System monitoring stopped")

        except Exception as e:
            logger.error(f"❌ Failed to stop system monitoring: {e}")

    async def _monitoring_loop(self) -> None:
        """Continuous system monitoring loop"""

        logger.info("📊 System monitoring loop started")

        try:
            while self.is_monitoring:
                # Update system metrics
                self._update_system_metrics()

                # Update performance metrics
                self._update_performance_metrics()

                # Check for performance degradation
                await self._check_performance_degradation()

                # Wait for next monitoring cycle
                await asyncio.sleep(5)  # 5-second monitoring interval

        except asyncio.CancelledError:
            logger.info("📊 System monitoring cancelled")
        except Exception as e:
            logger.error(f"❌ System monitoring error: {e}")

        logger.info("📊 System monitoring stopped")

    def _update_system_metrics(self) -> None:
        """Update system performance metrics"""

        try:
            uptime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0

            self.system_metrics.update({
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': uptime,
                'uptime_formatted': str(timedelta(seconds=int(uptime))),
                'monitoring_active': self.is_monitoring,
                'last_update': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"❌ Metrics update error: {e}")

    def _update_performance_metrics(self) -> None:
        """Update performance tracking metrics"""

        try:
            # Basic performance metrics
            self.performance_metrics.update({
                'timestamp': datetime.now().isoformat(),
                'metrics_collection_active': True,
                'last_performance_update': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"❌ Performance metrics update error: {e}")

    async def _check_performance_degradation(self) -> None:
        """Check for system performance degradation"""

        try:
            # Check system health indicators
            current_time = datetime.now()

            # Check if monitoring is running too long without updates
            if self.started_at:
                uptime = (current_time - self.started_at).total_seconds()
                if uptime > 86400:  # 24 hours
                    logger.warning("⚠️ System has been running for over 24 hours - consider restart")

        except Exception as e:
            logger.error(f"❌ Performance degradation check error: {e}")

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return self.system_metrics.copy()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.performance_metrics.copy()

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status"""
        return {
            'monitoring_active': self.is_monitoring,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'monitoring_task_active': self.monitoring_task and not self.monitoring_task.done() if self.monitoring_task else False
        }

    async def collect_comprehensive_metrics(self, component_registry: Dict[str, Any]) -> SystemMetrics:
        """Collect comprehensive system metrics"""

        try:
            total_components = len(component_registry)
            operational_components = sum(
                1 for reg in component_registry.values()
                if reg.status == 'operational'
            )
            failed_components = sum(
                1 for reg in component_registry.values()
                if reg.status in ['failed', 'error']
            )

            uptime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
            error_rate = failed_components / total_components if total_components > 0 else 0

            return SystemMetrics(
                timestamp=datetime.now(),
                total_components=total_components,
                operational_components=operational_components,
                failed_components=failed_components,
                system_uptime=uptime,
                memory_usage=0.0,  # Would be implemented with actual memory monitoring
                cpu_usage=0.0,     # Would be implemented with actual CPU monitoring
                error_rate=error_rate,
                throughput=0.0     # Would be implemented with actual throughput monitoring
            )

        except Exception as e:
            logger.error(f"❌ Comprehensive metrics collection error: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                total_components=0,
                operational_components=0,
                failed_components=0,
                system_uptime=0,
                memory_usage=0.0,
                cpu_usage=0.0,
                error_rate=1.0,
                throughput=0.0
            )

    # ========================================================================
    # ISystemComponent Interface Implementation (Rule 1)
    # ========================================================================

    async def initialize(self) -> bool:
        """Initialize the system monitor"""
        try:
            logger.info("📊 Initializing System Monitor...")
            self.is_initialized = True
            logger.info("✅ System Monitor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ System Monitor initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start the system monitor"""
        try:
            if not self.is_initialized:
                logger.warning("⚠️ Cannot start System Monitor - not initialized")
                return False

            await self.start_monitoring()
            self.is_operational = True
            logger.info("✅ System Monitor started successfully")
            return True
        except Exception as e:
            logger.error(f"❌ System Monitor start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop the system monitor"""
        try:
            await self.stop_monitoring()
            self.is_operational = False
            logger.info("✅ System Monitor stopped successfully")
            return True
        except Exception as e:
            logger.error(f"❌ System Monitor stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on system monitor"""
        return {
            'healthy': self.is_operational and self.is_monitoring,
            'initialized': self.is_initialized,
            'component_type': 'SystemMonitor',
            'monitoring_active': self.is_monitoring,
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            'status': 'operational' if self.is_operational else 'stopped'
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of system monitor"""
        return {
            'component_type': 'SystemMonitor',
            'operational': self.is_operational,
            'initialized': self.is_initialized,
            'monitoring_active': self.is_monitoring,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        }
