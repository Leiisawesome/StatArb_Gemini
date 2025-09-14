#!/usr/bin/env python3
"""
Phase 4 Ultimate Production Infrastructure Integration
=====================================================

The final integration layer that brings together all infrastructure components
into a production-ready system with comprehensive monitoring, safety controls,
and zero-configuration deployment capabilities.

PHASE 4 ULTIMATE INTEGRATION FEATURES:
- Production-ready monitoring and alerting
- Automated infrastructure provisioning
- Real-time health checking and recovery
- Database connection management
- Message bus integration
- Circuit breakers and safety controls
- Performance optimization
- Zero-configuration deployment

Author: Professional Trading System Architecture - Phase 4 Ultimate Integration
Version: 7.0.0 (Production Infrastructure)
"""

import asyncio
import logging
import os
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar
from pathlib import Path
import weakref
import uuid

# Import existing infrastructure components
from core_structure.infrastructure.production_safety import ProductionSafetyFramework, Environment, SafetyLevel
from core_structure.infrastructure.monitoring.monitoring_system import (
    EnhancedHealthMonitor, MetricsCollector, RealTimeMonitor, 
    PerformanceDashboard, MetricType, AlertLevel
)
from core_structure.infrastructure.database.database_system import DatabaseManager
from core_structure.infrastructure.messaging.messaging_system import MessageBus, Message
from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager

logger = logging.getLogger(__name__)

# ================================================================================
# PHASE 4 PRODUCTION ENUMS AND TYPES
# ================================================================================

class InfrastructureStatus(Enum):
    """Infrastructure component status"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"

class DeploymentMode(Enum):
    """Deployment modes for Phase 4"""
    DEVELOPMENT = "development"
    PAPER_TRADING = "paper_trading"
    PRODUCTION = "production"
    RESEARCH = "research"

class ServiceType(Enum):
    """Infrastructure service types"""
    DATABASE = "database"
    MONITORING = "monitoring"
    MESSAGING = "messaging"
    MARKET_DATA = "market_data"
    EXECUTION = "execution"
    ANALYTICS = "analytics"
    RISK_MANAGEMENT = "risk_management"

@dataclass
class InfrastructureMetrics:
    """Real-time infrastructure metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    database_connections: int
    active_threads: int
    cache_hit_ratio: float
    error_rate: float
    uptime_seconds: float

@dataclass
class ServiceHealth:
    """Health status of individual services"""
    service_name: str
    service_type: ServiceType
    status: InfrastructureStatus
    last_check: datetime
    response_time_ms: float
    error_count: int
    uptime_percentage: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProductionConfiguration:
    """Complete production configuration"""
    deployment_mode: DeploymentMode = DeploymentMode.DEVELOPMENT
    environment: Environment = Environment.DEVELOPMENT
    safety_level: SafetyLevel = SafetyLevel.DEVELOPMENT
    monitoring_enabled: bool = True
    auto_recovery_enabled: bool = True
    circuit_breakers_enabled: bool = True
    performance_optimization: bool = True
    real_time_alerts: bool = True
    database_config: Dict[str, Any] = field(default_factory=dict)
    messaging_config: Dict[str, Any] = field(default_factory=dict)
    monitoring_config: Dict[str, Any] = field(default_factory=dict)
    
    # Additional configuration for compatibility
    enable_database: bool = True
    enable_monitoring: bool = True
    enable_message_bus: bool = True
    database_url: str = "sqlite:///trading.db"
    monitoring_port: int = 8080
    message_bus_url: str = "memory://local"

# Alias for compatibility with tests
InfrastructureConfiguration = ProductionConfiguration

# ================================================================================
# PRODUCTION INFRASTRUCTURE MANAGER
# ================================================================================

class ProductionInfrastructureManager:
    """
    Ultimate production infrastructure manager that coordinates all infrastructure
    components for Phase 4 deployment
    """
    
    def __init__(self, config: ProductionConfiguration):
        self.config = config
        self.services: Dict[str, Any] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        self.infrastructure_metrics = InfrastructureMetrics(
            timestamp=datetime.now(),
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            network_latency=0.0,
            database_connections=0,
            active_threads=0,
            cache_hit_ratio=0.0,
            error_rate=0.0,
            uptime_seconds=0.0
        )
        
        self._start_time = datetime.now()
        self._health_check_thread = None
        self._metrics_collection_thread = None
        self._running = False
        self._lock = threading.RLock()
        
        # Initialize production safety framework (singleton)
        self.safety_framework = ProductionSafetyFramework()
        
        logger.info(f"🏗️ Production Infrastructure Manager initialized for {config.deployment_mode.value}")
    
    async def initialize_infrastructure(self) -> None:
        """Initialize all infrastructure components for production"""
        with self._lock:
            try:
                # Initialize core services
                await self._initialize_database_service()
                await self._initialize_monitoring_service()
                await self._initialize_messaging_service()
                await self._initialize_market_data_service()
                await self._initialize_execution_service()
                await self._initialize_analytics_service()
                await self._initialize_risk_management_service()
                
                # Start health monitoring
                self._start_health_monitoring()
                
                # Start metrics collection
                self._start_metrics_collection()
                
                self._running = True
                logger.info("✅ Production infrastructure fully initialized")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize production infrastructure: {e}")
                raise
    
    async def _initialize_database_service(self) -> None:
        """Initialize database service with production settings"""
        try:
            # Import DatabaseConfig for proper configuration
            from core_structure.infrastructure.database.database_system import DatabaseConfig
            
            # Create proper database configuration object
            database_config = DatabaseConfig(
                clickhouse={
                    'host': self.config.database_config.get('host', 'localhost'),
                    'port': self.config.database_config.get('port', 9000),
                    'database': self.config.database_config.get('database', 'statarb_production'),
                    'user': self.config.database_config.get('user', 'default'),
                    'password': self.config.database_config.get('password', ''),
                    'connect_timeout': self.config.database_config.get('timeout', 30),
                    'settings': {
                        'max_execution_time': 300,
                        'max_memory_usage': 2000000000
                    }
                },
                redis={
                    'host': self.config.database_config.get('redis_host', 'localhost'),
                    'port': self.config.database_config.get('redis_port', 6379),
                    'db': self.config.database_config.get('redis_db', 0),
                    'decode_responses': False,
                    'max_connections': self.config.database_config.get('pool_size', 20)
                },
                cache={
                    'default_ttl': 300,
                    'max_memory': '1gb',
                    'compression': True
                }
            )
            
            database_manager = DatabaseManager(database_config)
            await database_manager.initialize()
            
            self.services['database'] = database_manager
            self.service_health['database'] = ServiceHealth(
                service_name='database',
                service_type=ServiceType.DATABASE,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Database service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database service: {e}")
            self.service_health['database'] = ServiceHealth(
                service_name='database',
                service_type=ServiceType.DATABASE,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            raise
    
    async def _initialize_monitoring_service(self) -> None:
        """Initialize monitoring service with comprehensive metrics"""
        try:
            monitoring_config = {
                'metrics_interval': self.config.monitoring_config.get('metrics_interval', 30),
                'alert_thresholds': self.config.monitoring_config.get('alert_thresholds', {}),
                'dashboard_port': self.config.monitoring_config.get('dashboard_port', 8080),
                'enable_real_time': self.config.real_time_alerts
            }
            
            # Initialize monitoring components
            health_monitor = EnhancedHealthMonitor(monitoring_config)
            metrics_collector = MetricsCollector(monitoring_config)
            real_time_monitor = RealTimeMonitor(monitoring_config)
            dashboard = PerformanceDashboard(monitoring_config)
            
            # Start monitoring services
            await health_monitor.start()
            await metrics_collector.start()
            await real_time_monitor.start()
            await dashboard.start()
            
            self.services['monitoring'] = {
                'health_monitor': health_monitor,
                'metrics_collector': metrics_collector,
                'real_time_monitor': real_time_monitor,
                'dashboard': dashboard
            }
            
            self.service_health['monitoring'] = ServiceHealth(
                service_name='monitoring',
                service_type=ServiceType.MONITORING,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Monitoring service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitoring service: {e}")
            self.service_health['monitoring'] = ServiceHealth(
                service_name='monitoring',
                service_type=ServiceType.MONITORING,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Monitoring is critical - don't raise exception but continue
    
    async def _initialize_messaging_service(self) -> None:
        """Initialize message bus for inter-component communication"""
        try:
            messaging_config = {
                'broker_url': self.config.messaging_config.get('broker_url', 'redis://localhost:6379'),
                'max_connections': self.config.messaging_config.get('max_connections', 100),
                'message_ttl': self.config.messaging_config.get('message_ttl', 3600),
                'enable_persistence': self.config.messaging_config.get('enable_persistence', True)
            }
            
            message_bus = MessageBus(messaging_config)
            await message_bus.initialize()
            
            self.services['messaging'] = message_bus
            self.service_health['messaging'] = ServiceHealth(
                service_name='messaging',
                service_type=ServiceType.MESSAGING,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Messaging service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize messaging service: {e}")
            self.service_health['messaging'] = ServiceHealth(
                service_name='messaging',
                service_type=ServiceType.MESSAGING,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Continue without messaging for now
    
    async def _initialize_market_data_service(self) -> None:
        """Initialize market data service with redundant feeds"""
        try:
            # Import market data components
            from core_structure.components.market_data import UnifiedDataManager, UnifiedDataFeeds
            
            market_data_config = {
                'primary_source': 'interactive_brokers',
                'fallback_sources': ['yahoo_finance', 'alpha_vantage'],
                'cache_enabled': True,
                'quality_monitoring': True,
                'latency_threshold_ms': 100
            }
            
            data_manager = UnifiedDataManager(market_data_config)
            data_feeds = UnifiedDataFeeds(market_data_config)
            
            await data_manager.initialize()
            await data_feeds.initialize()
            
            self.services['market_data'] = {
                'data_manager': data_manager,
                'data_feeds': data_feeds
            }
            
            self.service_health['market_data'] = ServiceHealth(
                service_name='market_data',
                service_type=ServiceType.MARKET_DATA,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Market data service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize market data service: {e}")
            self.service_health['market_data'] = ServiceHealth(
                service_name='market_data',
                service_type=ServiceType.MARKET_DATA,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Market data is critical for live trading
            if self.config.deployment_mode == DeploymentMode.PRODUCTION:
                raise
    
    async def _initialize_execution_service(self) -> None:
        """Initialize execution service for order management"""
        try:
            # Import execution components
            from core_structure.components.execution import ExecutionEngine, OrderManager
            
            execution_config = {
                'broker': 'interactive_brokers',
                'max_orders_per_second': 10,
                'order_timeout_seconds': 30,
                'enable_smart_routing': True,
                'risk_checks_enabled': True
            }
            
            execution_engine = ExecutionEngine(execution_config)
            order_manager = OrderManager(execution_config)
            
            await execution_engine.initialize()
            await order_manager.initialize()
            
            self.services['execution'] = {
                'execution_engine': execution_engine,
                'order_manager': order_manager
            }
            
            self.service_health['execution'] = ServiceHealth(
                service_name='execution',
                service_type=ServiceType.EXECUTION,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Execution service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize execution service: {e}")
            self.service_health['execution'] = ServiceHealth(
                service_name='execution',
                service_type=ServiceType.EXECUTION,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Continue - execution might be initialized later
    
    async def _initialize_analytics_service(self) -> None:
        """Initialize analytics service with Phase 3 performance optimizations"""
        try:
            # Import analytics components with Phase 3 optimizations
            from core_structure.analytics.core_analytics import CoreAnalytics
            from core_structure.analytics.monitoring_analytics import MonitoringAnalytics
            from core_structure.analytics.research_analytics import ResearchAnalytics
            from core_structure.analytics.performance_optimization import (
                vectorized_calc, parallel_processor, intelligent_cache
            )
            
            analytics_config = {
                'enable_vectorization': True,
                'enable_parallel_processing': True,
                'enable_intelligent_caching': True,
                'cache_size': 10000,
                'max_workers': 8
            }
            
            # Initialize analytics components with optimizations
            core_analytics = CoreAnalytics(analytics_config)
            monitoring_analytics = MonitoringAnalytics(analytics_config)
            research_analytics = ResearchAnalytics(analytics_config)
            
            self.services['analytics'] = {
                'core_analytics': core_analytics,
                'monitoring_analytics': monitoring_analytics,
                'research_analytics': research_analytics,
                'optimizations': {
                    'vectorized_calc': vectorized_calc,
                    'parallel_processor': parallel_processor,
                    'intelligent_cache': intelligent_cache
                }
            }
            
            self.service_health['analytics'] = ServiceHealth(
                service_name='analytics',
                service_type=ServiceType.ANALYTICS,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Analytics service initialized with Phase 3 optimizations")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize analytics service: {e}")
            self.service_health['analytics'] = ServiceHealth(
                service_name='analytics',
                service_type=ServiceType.ANALYTICS,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Analytics is important but not critical for basic operation
    
    async def _initialize_risk_management_service(self) -> None:
        """Initialize risk management service with real-time monitoring"""
        try:
            # Import risk management components
            from core_structure.components.risk import RiskManager, PositionMonitor, VaRCalculator
            
            risk_config = {
                'max_position_size': 0.1,  # 10% max position
                'var_confidence': 0.95,
                'lookback_days': 252,
                'stress_test_enabled': True,
                'real_time_monitoring': True
            }
            
            risk_manager = RiskManager(risk_config)
            position_monitor = PositionMonitor(risk_config)
            var_calculator = VaRCalculator(risk_config)
            
            await risk_manager.initialize()
            await position_monitor.initialize()
            
            self.services['risk_management'] = {
                'risk_manager': risk_manager,
                'position_monitor': position_monitor,
                'var_calculator': var_calculator
            }
            
            self.service_health['risk_management'] = ServiceHealth(
                service_name='risk_management',
                service_type=ServiceType.RISK_MANAGEMENT,
                status=InfrastructureStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=0,
                uptime_percentage=100.0
            )
            
            logger.info("✅ Risk management service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize risk management service: {e}")
            self.service_health['risk_management'] = ServiceHealth(
                service_name='risk_management',
                service_type=ServiceType.RISK_MANAGEMENT,
                status=InfrastructureStatus.CRITICAL,
                last_check=datetime.now(),
                response_time_ms=0.0,
                error_count=1,
                uptime_percentage=0.0,
                metadata={'error': str(e)}
            )
            # Risk management is critical - continue but log the issue
    
    def _start_health_monitoring(self) -> None:
        """Start continuous health monitoring of all services"""
        def health_check_loop():
            while self._running:
                try:
                    self._perform_health_checks()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                    time.sleep(5)  # Shorter delay on error
        
        self._health_check_thread = threading.Thread(target=health_check_loop, daemon=True)
        self._health_check_thread.start()
        logger.info("🔍 Health monitoring started")
    
    def _start_metrics_collection(self) -> None:
        """Start continuous metrics collection"""
        def metrics_collection_loop():
            while self._running:
                try:
                    self._collect_infrastructure_metrics()
                    time.sleep(60)  # Collect every minute
                except Exception as e:
                    logger.error(f"Metrics collection error: {e}")
                    time.sleep(10)  # Shorter delay on error
        
        self._metrics_collection_thread = threading.Thread(target=metrics_collection_loop, daemon=True)
        self._metrics_collection_thread.start()
        logger.info("📊 Metrics collection started")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all services"""
        for service_name, service_health in self.service_health.items():
            try:
                start_time = time.time()
                
                # Perform service-specific health check
                is_healthy = self._check_service_health(service_name)
                
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Update health status
                service_health.last_check = datetime.now()
                service_health.response_time_ms = response_time
                
                if is_healthy:
                    service_health.status = InfrastructureStatus.HEALTHY
                    service_health.uptime_percentage = min(100.0, service_health.uptime_percentage + 0.1)
                else:
                    service_health.status = InfrastructureStatus.DEGRADED
                    service_health.error_count += 1
                    service_health.uptime_percentage = max(0.0, service_health.uptime_percentage - 1.0)
                
            except Exception as e:
                service_health.status = InfrastructureStatus.CRITICAL
                service_health.error_count += 1
                service_health.uptime_percentage = max(0.0, service_health.uptime_percentage - 5.0)
                logger.error(f"Health check failed for {service_name}: {e}")
    
    def _check_service_health(self, service_name: str) -> bool:
        """Check health of a specific service"""
        service = self.services.get(service_name)
        if not service:
            return False
        
        try:
            if service_name == 'database':
                # Check database connection
                return hasattr(service, 'is_connected') and service.is_connected()
            elif service_name == 'monitoring':
                # Check if monitoring components are running
                return all(
                    hasattr(comp, 'is_running') and comp.is_running()
                    for comp in service.values()
                )
            elif service_name == 'messaging':
                # Check message bus connectivity
                return hasattr(service, 'is_connected') and service.is_connected()
            else:
                # Generic health check
                return True
        except:
            return False
    
    def _collect_infrastructure_metrics(self) -> None:
        """Collect comprehensive infrastructure metrics"""
        try:
            import psutil
            
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network metrics (simplified)
            network_latency = 1.0  # Placeholder - would ping monitoring endpoints
            
            # Service metrics
            database_connections = self._get_database_connections()
            active_threads = threading.active_count()
            cache_hit_ratio = self._get_cache_hit_ratio()
            error_rate = self._calculate_error_rate()
            uptime = (datetime.now() - self._start_time).total_seconds()
            
            # Update metrics
            self.infrastructure_metrics = InfrastructureMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_latency=network_latency,
                database_connections=database_connections,
                active_threads=active_threads,
                cache_hit_ratio=cache_hit_ratio,
                error_rate=error_rate,
                uptime_seconds=uptime
            )
            
            # Send metrics to monitoring system
            if 'monitoring' in self.services:
                monitoring = self.services['monitoring']
                if 'metrics_collector' in monitoring:
                    monitoring['metrics_collector'].record_metrics(
                        self.infrastructure_metrics.__dict__
                    )
            
        except Exception as e:
            logger.error(f"Failed to collect infrastructure metrics: {e}")
    
    def _get_database_connections(self) -> int:
        """Get number of active database connections"""
        try:
            if 'database' in self.services:
                db = self.services['database']
                if hasattr(db, 'get_connection_count'):
                    return db.get_connection_count()
            return 0
        except:
            return 0
    
    def _get_cache_hit_ratio(self) -> float:
        """Get overall cache hit ratio"""
        try:
            if 'analytics' in self.services:
                analytics = self.services['analytics']
                if 'optimizations' in analytics:
                    cache = analytics['optimizations'].get('intelligent_cache')
                    if cache and hasattr(cache, 'get_hit_ratio'):
                        return cache.get_hit_ratio()
            return 0.0
        except:
            return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall system error rate"""
        try:
            total_errors = sum(service.error_count for service in self.service_health.values())
            total_checks = len(self.service_health) * 100  # Approximate
            return (total_errors / total_checks) * 100 if total_checks > 0 else 0.0
        except:
            return 0.0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of all production infrastructure components"""
        health_status = {
            "overall_health": "healthy",  # Changed from overall_status to overall_health
            "overall_status": "healthy",   # Keep both for compatibility
            "timestamp": datetime.now(),
            "components": {}
        }
        
        # Check overall service health
        try:
            if self.service_health:
                healthy_services = sum(1 for service in self.service_health.values() 
                                     if hasattr(service, 'status') and service.status == InfrastructureStatus.HEALTHY)
                total_services = len(self.service_health)
                
                if healthy_services == total_services:
                    health_status["overall_health"] = "healthy"
                    health_status["overall_status"] = "healthy"
                elif healthy_services > total_services / 2:
                    health_status["overall_health"] = "degraded"
                    health_status["overall_status"] = "degraded"
                else:
                    health_status["overall_health"] = "critical"
                    health_status["overall_status"] = "critical"
                
                health_status["components"]["services"] = {
                    "status": health_status["overall_status"],
                    "healthy_count": healthy_services,
                    "total_count": total_services,
                    "ready": healthy_services > 0
                }
            else:
                health_status["components"]["services"] = {
                    "status": "unavailable",
                    "ready": False
                }
                health_status["overall_status"] = "degraded"
        except Exception as e:
            health_status["components"]["services"] = {
                "status": "error",
                "error": str(e),
                "ready": False
            }
            health_status["overall_status"] = "degraded"
        
        # Check safety framework
        try:
            if hasattr(self, 'safety_framework') and self.safety_framework:
                health_status["components"]["safety_framework"] = {
                    "status": "healthy",
                    "ready": True
                }
            else:
                health_status["components"]["safety_framework"] = {
                    "status": "unavailable",
                    "ready": False
                }
                health_status["overall_status"] = "degraded"
        except Exception as e:
            health_status["components"]["safety_framework"] = {
                "status": "error",
                "error": str(e),
                "ready": False
            }
            health_status["overall_status"] = "degraded"
        
        # Add performance metrics
        try:
            health_status["metrics"] = {
                "cache_hit_ratio": self._calculate_cache_hit_ratio(),
                "error_rate": self._calculate_error_rate(),
                "uptime": time.time() - getattr(self, '_start_time', time.time())
            }
        except Exception:
            health_status["metrics"] = {}
        
        return health_status

    async def shutdown_infrastructure(self) -> None:
        """Gracefully shutdown all infrastructure components"""
        logger.info("🔄 Shutting down production infrastructure...")
        
        self._running = False
        
        # Wait for monitoring threads to finish
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        if self._metrics_collection_thread:
            self._metrics_collection_thread.join(timeout=5)
        
        # Shutdown services in reverse order
        service_shutdown_order = [
            'risk_management', 'analytics', 'execution', 
            'market_data', 'messaging', 'monitoring', 'database'
        ]
        
        for service_name in service_shutdown_order:
            if service_name in self.services:
                try:
                    service = self.services[service_name]
                    if hasattr(service, 'shutdown'):
                        await service.shutdown()
                    elif isinstance(service, dict):
                        for component in service.values():
                            if hasattr(component, 'shutdown'):
                                await component.shutdown()
                    logger.info(f"✅ {service_name} service shutdown complete")
                except Exception as e:
                    logger.error(f"❌ Error shutting down {service_name}: {e}")
        
        logger.info("✅ Production infrastructure shutdown complete")
    
    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get comprehensive infrastructure status"""
        # Get individual service statuses
        database_status = self.service_health.get('database', {})
        monitoring_status = self.service_health.get('monitoring', {})
        messaging_status = self.service_health.get('messaging', {})
        
        return {
            'overall_status': self._get_overall_status(),
            'service_health': {name: health.__dict__ for name, health in self.service_health.items()},
            'infrastructure_metrics': self.infrastructure_metrics.__dict__,
            
            # Add expected individual service statuses for backward compatibility
            'database_status': {
                'status': database_status.status.value if hasattr(database_status, 'status') else 'unknown',
                'healthy': database_status.status == InfrastructureStatus.HEALTHY if hasattr(database_status, 'status') else False,
                'last_check': database_status.last_check.isoformat() if hasattr(database_status, 'last_check') else None
            },
            'monitoring_status': {
                'status': monitoring_status.status.value if hasattr(monitoring_status, 'status') else 'unknown',
                'healthy': monitoring_status.status == InfrastructureStatus.HEALTHY if hasattr(monitoring_status, 'status') else False,
                'last_check': monitoring_status.last_check.isoformat() if hasattr(monitoring_status, 'last_check') else None
            },
            'message_bus_status': {
                'status': messaging_status.status.value if hasattr(messaging_status, 'status') else 'unknown',
                'healthy': messaging_status.status == InfrastructureStatus.HEALTHY if hasattr(messaging_status, 'status') else False,
                'last_check': messaging_status.last_check.isoformat() if hasattr(messaging_status, 'last_check') else None
            },
            
            'uptime_seconds': (datetime.now() - self._start_time).total_seconds(),
            'deployment_mode': self.config.deployment_mode.value,
            'environment': self.config.environment.value,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_overall_status(self) -> str:
        """Determine overall infrastructure status"""
        if not self.service_health:
            return InfrastructureStatus.OFFLINE.value
        
        statuses = [health.status for health in self.service_health.values()]
        
        if all(status == InfrastructureStatus.HEALTHY for status in statuses):
            return InfrastructureStatus.HEALTHY.value
        elif any(status == InfrastructureStatus.CRITICAL for status in statuses):
            return InfrastructureStatus.CRITICAL.value
        elif any(status == InfrastructureStatus.DEGRADED for status in statuses):
            return InfrastructureStatus.DEGRADED.value
        else:
            return InfrastructureStatus.OFFLINE.value

# ================================================================================
# PRODUCTION INFRASTRUCTURE FACTORY
# ================================================================================

class ProductionInfrastructureFactory:
    """Factory for creating production infrastructure configurations"""
    
    @staticmethod
    def create_production_config() -> ProductionConfiguration:
        """Create production-ready configuration"""
        return ProductionConfiguration(
            deployment_mode=DeploymentMode.PRODUCTION,
            environment=Environment.PRODUCTION,
            safety_level=SafetyLevel.STRICT,
            monitoring_enabled=True,
            auto_recovery_enabled=True,
            circuit_breakers_enabled=True,
            performance_optimization=True,
            real_time_alerts=True,
            database_config={
                'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
                'port': int(os.getenv('CLICKHOUSE_PORT', '9000')),
                'database': os.getenv('CLICKHOUSE_DB', 'statarb_production'),
                'pool_size': 20,
                'timeout': 30,
                'retry_attempts': 3
            },
            messaging_config={
                'broker_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
                'max_connections': 100,
                'message_ttl': 3600,
                'enable_persistence': True
            },
            monitoring_config={
                'metrics_interval': 30,
                'alert_thresholds': {
                    'cpu_usage': 80.0,
                    'memory_usage': 85.0,
                    'error_rate': 5.0,
                    'response_time_ms': 1000.0
                },
                'dashboard_port': int(os.getenv('DASHBOARD_PORT', '8080')),
                'enable_real_time': True
            }
        )
    
    @staticmethod
    def create_paper_trading_config() -> ProductionConfiguration:
        """Create paper trading configuration"""
        return ProductionConfiguration(
            deployment_mode=DeploymentMode.PAPER_TRADING,
            environment=Environment.STAGING,
            safety_level=SafetyLevel.CAUTIOUS,
            monitoring_enabled=True,
            auto_recovery_enabled=True,
            circuit_breakers_enabled=True,
            performance_optimization=True,
            real_time_alerts=True,
            database_config={
                'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
                'port': int(os.getenv('CLICKHOUSE_PORT', '9000')),
                'database': 'statarb_paper_trading',
                'pool_size': 10,
                'timeout': 30,
                'retry_attempts': 2
            },
            messaging_config={
                'broker_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
                'max_connections': 50,
                'message_ttl': 1800,
                'enable_persistence': False
            },
            monitoring_config={
                'metrics_interval': 60,
                'alert_thresholds': {
                    'cpu_usage': 90.0,
                    'memory_usage': 90.0,
                    'error_rate': 10.0,
                    'response_time_ms': 2000.0
                },
                'dashboard_port': int(os.getenv('DASHBOARD_PORT', '8080')),
                'enable_real_time': True
            }
        )
    
    @staticmethod
    def create_development_config() -> ProductionConfiguration:
        """Create development configuration"""
        return ProductionConfiguration(
            deployment_mode=DeploymentMode.DEVELOPMENT,
            environment=Environment.DEVELOPMENT,
            safety_level=SafetyLevel.DEVELOPMENT,
            monitoring_enabled=True,
            auto_recovery_enabled=False,
            circuit_breakers_enabled=False,
            performance_optimization=False,
            real_time_alerts=False,
            database_config={
                'host': 'localhost',
                'port': 9000,
                'database': 'statarb_dev',
                'pool_size': 5,
                'timeout': 10,
                'retry_attempts': 1
            },
            messaging_config={
                'broker_url': 'redis://localhost:6379',
                'max_connections': 10,
                'message_ttl': 300,
                'enable_persistence': False
            },
            monitoring_config={
                'metrics_interval': 120,
                'alert_thresholds': {
                    'cpu_usage': 95.0,
                    'memory_usage': 95.0,
                    'error_rate': 50.0,
                    'response_time_ms': 5000.0
                },
                'dashboard_port': 8080,
                'enable_real_time': False
            }
        )

# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

async def create_production_infrastructure(deployment_mode: str = "production") -> ProductionInfrastructureManager:
    """Create and initialize production infrastructure"""
    factory = ProductionInfrastructureFactory()
    
    if deployment_mode.lower() == "production":
        config = factory.create_production_config()
    elif deployment_mode.lower() == "paper_trading":
        config = factory.create_paper_trading_config()
    else:
        config = factory.create_development_config()
    
    infrastructure = ProductionInfrastructureManager(config)
    await infrastructure.initialize_infrastructure()
    
    return infrastructure

def get_production_infrastructure_status() -> Dict[str, Any]:
    """Get current production infrastructure status"""
    # This would be implemented to return cached status from a global instance
    return {
        'message': 'Production infrastructure factory ready',
        'available_modes': ['production', 'paper_trading', 'development'],
        'timestamp': datetime.now().isoformat()
    }

# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    'ProductionInfrastructureManager',
    'ProductionInfrastructureFactory',
    'ProductionConfiguration',
    'InfrastructureStatus',
    'DeploymentMode',
    'ServiceType',
    'InfrastructureMetrics',
    'ServiceHealth',
    'create_production_infrastructure',
    'get_production_infrastructure_status'
]