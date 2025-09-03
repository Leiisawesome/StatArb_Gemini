"""
Unified Strategy Registry - Phase 1 Consolidation
===============================================

Centralized strategy registration, discovery, and lifecycle management.
Consolidates strategy management from multiple locations into single authority.

Features:
- Automatic strategy discovery and registration
- Strategy lifecycle management (load, validate, unload)
- Performance monitoring per strategy
- Configuration validation and management
- Strategy dependency resolution

Author: Professional Trading System Architecture
Version: 1.0 (Unified Consolidation)
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

# Core imports
from ..interfaces.strategy_interfaces import StrategyInterface, BaseStrategy, StrategyType, StrategyMetrics, StrategyError
from .configuration import UnifiedStrategyConfig, UnifiedConfigurationManager

logger = logging.getLogger(__name__)

# ================================================================================
# STRATEGY REGISTRY TYPES
# ================================================================================

class StrategyStatus(Enum):
    """Strategy lifecycle status"""
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    VALIDATED = "validated"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    UNLOADED = "unloaded"

@dataclass
class StrategyRegistration:
    """Complete strategy registration information"""
    # Basic Info
    strategy_id: str
    strategy_name: str
    strategy_type: StrategyType
    strategy_class: Type[BaseStrategy]
    
    # Configuration
    config: UnifiedStrategyConfig
    
    # Status and Lifecycle
    status: StrategyStatus = StrategyStatus.DISCOVERED
    registered_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Instance Management
    instance: Optional[StrategyInterface] = None
    instance_count: int = 0
    
    # Performance Tracking
    total_executions: int = 0
    successful_executions: int = 0
    total_processing_time_ms: float = 0.0
    last_execution_time: Optional[datetime] = None
    
    # Dependencies and Requirements
    required_indicators: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # Error Tracking
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def update_performance(self, execution_time_ms: float, success: bool) -> None:
        """Update strategy performance metrics"""
        self.total_executions += 1
        self.total_processing_time_ms += execution_time_ms
        self.last_execution_time = datetime.now()
        self.last_updated = datetime.now()
        
        if success:
            self.successful_executions += 1
        else:
            self.error_count += 1
    
    def get_success_rate(self) -> float:
        """Get strategy success rate"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    def get_average_execution_time(self) -> float:
        """Get average execution time in milliseconds"""
        if self.total_executions == 0:
            return 0.0
        return self.total_processing_time_ms / self.total_executions

@dataclass
class StrategyDiscoveryResult:
    """Result of strategy discovery process"""
    discovered_strategies: List[Tuple[str, Type[BaseStrategy]]] = field(default_factory=list)
    failed_imports: List[Tuple[str, str]] = field(default_factory=list)  # (module_path, error)
    discovery_time_ms: float = 0.0
    total_modules_scanned: int = 0

# ================================================================================
# UNIFIED STRATEGY REGISTRY
# ================================================================================

class UnifiedStrategyRegistry:
    """
    Centralized strategy registry managing all strategy operations.
    
    Responsibilities:
    - Strategy discovery and automatic registration
    - Strategy lifecycle management (create, validate, destroy)
    - Performance monitoring and metrics collection
    - Configuration validation and management
    - Dependency resolution and validation
    """
    
    def __init__(self, config_manager: Optional[UnifiedConfigurationManager] = None):
        """Initialize unified strategy registry"""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Strategy storage
        self._registrations: Dict[str, StrategyRegistration] = {}
        self._strategy_classes: Dict[StrategyType, Type[BaseStrategy]] = {}
        self._active_instances: Dict[str, StrategyInterface] = {}
        
        # Discovery settings
        self._discovery_paths = [
            "trade_engine.strategies",
            "core_structure.strategies"  # If it exists
        ]
        
        # Performance tracking
        self._registry_metrics = {
            'total_registrations': 0,
            'active_strategies': 0,
            'total_discoveries': 0,
            'failed_registrations': 0,
            'last_discovery_time': None
        }
        
        self.logger.info("UnifiedStrategyRegistry initialized")
    
    # ================================================================================
    # STRATEGY DISCOVERY
    # ================================================================================
    
    async def discover_strategies(self, additional_paths: Optional[List[str]] = None) -> StrategyDiscoveryResult:
        """
        Discover all available strategy implementations.
        Scans specified modules for BaseStrategy subclasses.
        """
        start_time = datetime.now()
        result = StrategyDiscoveryResult()
        
        # Combine default and additional paths
        search_paths = self._discovery_paths.copy()
        if additional_paths:
            search_paths.extend(additional_paths)
        
        self.logger.info(f"🔍 Discovering strategies in paths: {search_paths}")
        
        for module_path in search_paths:
            try:
                discovered = await self._discover_strategies_in_module(module_path)
                result.discovered_strategies.extend(discovered)
                result.total_modules_scanned += 1
                
            except Exception as e:
                error_msg = f"Failed to discover strategies in {module_path}: {e}"
                self.logger.warning(error_msg)
                result.failed_imports.append((module_path, str(e)))
        
        # Calculate discovery time
        result.discovery_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Update registry metrics
        self._registry_metrics['total_discoveries'] += len(result.discovered_strategies)
        self._registry_metrics['last_discovery_time'] = datetime.now()
        
        self.logger.info(f"✅ Strategy discovery complete: {len(result.discovered_strategies)} strategies found in {result.discovery_time_ms:.2f}ms")
        
        return result
    
    async def _discover_strategies_in_module(self, module_path: str) -> List[Tuple[str, Type[BaseStrategy]]]:
        """Discover strategies in a specific module"""
        discovered = []
        
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Scan for strategy classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseStrategy) and 
                    obj != BaseStrategy and 
                    not inspect.isabstract(obj)):
                    
                    strategy_name = f"{module_path}.{name}"
                    discovered.append((strategy_name, obj))
                    self.logger.debug(f"Discovered strategy: {strategy_name}")
            
            # Also check submodules
            if hasattr(module, '__path__'):
                for submodule_info in importlib.util.iter_modules(module.__path__, module_path + "."):
                    try:
                        submodule = importlib.import_module(submodule_info.name)
                        for name, obj in inspect.getmembers(submodule, inspect.isclass):
                            if (issubclass(obj, BaseStrategy) and 
                                obj != BaseStrategy and 
                                not inspect.isabstract(obj)):
                                
                                strategy_name = f"{submodule_info.name}.{name}"
                                discovered.append((strategy_name, obj))
                                self.logger.debug(f"Discovered strategy: {strategy_name}")
                    except Exception as e:
                        self.logger.debug(f"Could not scan submodule {submodule_info.name}: {e}")
        
        except Exception as e:
            self.logger.warning(f"Failed to scan module {module_path}: {e}")
            raise
        
        return discovered
    
    # ================================================================================
    # STRATEGY REGISTRATION
    # ================================================================================
    
    async def register_strategy(
        self,
        strategy_id: str,
        strategy_class: Type[BaseStrategy],
        config: Optional[UnifiedStrategyConfig] = None
    ) -> StrategyRegistration:
        """
        Register a strategy with the registry.
        Creates registration entry and validates configuration.
        """
        try:
            # Validate strategy class
            if not issubclass(strategy_class, BaseStrategy):
                raise StrategyError(f"Strategy class must inherit from BaseStrategy: {strategy_class}")
            
            # Create or validate configuration
            if config is None:
                config = self._create_default_config(strategy_id, strategy_class)
            
            # Create strategy registration
            registration = StrategyRegistration(
                strategy_id=strategy_id,
                strategy_name=strategy_class.__name__,
                strategy_type=strategy_class.strategy_type,
                strategy_class=strategy_class,
                config=config,
                status=StrategyStatus.REGISTERED
            )
            
            # Get required indicators from strategy
            temp_instance = strategy_class(strategy_id, config.parameters)
            registration.required_indicators = temp_instance.required_indicators
            
            # Validate configuration with strategy
            if not temp_instance.validate_parameters(config.parameters):
                raise StrategyError(f"Strategy configuration validation failed: {strategy_id}")
            
            # Store registration
            self._registrations[strategy_id] = registration
            self._strategy_classes[registration.strategy_type] = strategy_class
            
            # Update metrics
            self._registry_metrics['total_registrations'] += 1
            
            registration.status = StrategyStatus.VALIDATED
            
            self.logger.info(f"✅ Strategy registered: {strategy_id} ({strategy_class.__name__})")
            
            return registration
            
        except Exception as e:
            self._registry_metrics['failed_registrations'] += 1
            self.logger.error(f"❌ Strategy registration failed: {strategy_id} - {e}")
            raise StrategyError(f"Failed to register strategy {strategy_id}: {e}")
    
    async def register_discovered_strategies(self, discovery_result: StrategyDiscoveryResult) -> List[StrategyRegistration]:
        """Register all discovered strategies"""
        registrations = []
        
        for strategy_name, strategy_class in discovery_result.discovered_strategies:
            try:
                # Generate strategy ID from class name
                strategy_id = f"{strategy_class.__name__.lower()}_{len(self._registrations)}"
                
                registration = await self.register_strategy(strategy_id, strategy_class)
                registrations.append(registration)
                
            except Exception as e:
                self.logger.warning(f"Failed to register discovered strategy {strategy_name}: {e}")
        
        self.logger.info(f"✅ Registered {len(registrations)} discovered strategies")
        return registrations
    
    def _create_default_config(self, strategy_id: str, strategy_class: Type[BaseStrategy]) -> UnifiedStrategyConfig:
        """Create default configuration for a strategy"""
        return UnifiedStrategyConfig(
            strategy_id=strategy_id,
            strategy_name=strategy_class.__name__,
            strategy_type=strategy_class.strategy_type.value,
            parameters={
                'lookback_period': 20,
                'confidence_threshold': 0.6,
                'position_size': 0.05
            }
        )
    
    # ================================================================================
    # STRATEGY LIFECYCLE MANAGEMENT
    # ================================================================================
    
    async def create_strategy_instance(self, strategy_id: str) -> StrategyInterface:
        """Create and activate a strategy instance"""
        if strategy_id not in self._registrations:
            raise StrategyError(f"Strategy not registered: {strategy_id}")
        
        registration = self._registrations[strategy_id]
        
        try:
            # Create instance
            instance = registration.strategy_class(
                strategy_id=strategy_id,
                config=registration.config.parameters
            )
            
            # Store instance
            registration.instance = instance
            registration.instance_count += 1
            registration.status = StrategyStatus.ACTIVE
            self._active_instances[strategy_id] = instance
            
            # Update metrics
            self._registry_metrics['active_strategies'] += 1
            
            self.logger.info(f"✅ Strategy instance created: {strategy_id}")
            
            return instance
            
        except Exception as e:
            registration.status = StrategyStatus.ERROR
            registration.last_error = str(e)
            registration.last_error_time = datetime.now()
            
            self.logger.error(f"❌ Failed to create strategy instance: {strategy_id} - {e}")
            raise StrategyError(f"Failed to create strategy instance {strategy_id}: {e}")
    
    async def pause_strategy(self, strategy_id: str) -> None:
        """Pause a strategy (keep instance but mark as paused)"""
        if strategy_id not in self._registrations:
            raise StrategyError(f"Strategy not registered: {strategy_id}")
        
        registration = self._registrations[strategy_id]
        if registration.status == StrategyStatus.ACTIVE:
            registration.status = StrategyStatus.PAUSED
            self._registry_metrics['active_strategies'] -= 1
            
            self.logger.info(f"⏸️ Strategy paused: {strategy_id}")
    
    async def resume_strategy(self, strategy_id: str) -> None:
        """Resume a paused strategy"""
        if strategy_id not in self._registrations:
            raise StrategyError(f"Strategy not registered: {strategy_id}")
        
        registration = self._registrations[strategy_id]
        if registration.status == StrategyStatus.PAUSED:
            registration.status = StrategyStatus.ACTIVE
            self._registry_metrics['active_strategies'] += 1
            
            self.logger.info(f"▶️ Strategy resumed: {strategy_id}")
    
    async def unload_strategy(self, strategy_id: str) -> None:
        """Unload a strategy instance and remove from active instances"""
        if strategy_id not in self._registrations:
            raise StrategyError(f"Strategy not registered: {strategy_id}")
        
        registration = self._registrations[strategy_id]
        
        # Remove from active instances
        if strategy_id in self._active_instances:
            del self._active_instances[strategy_id]
        
        # Update registration
        registration.instance = None
        registration.status = StrategyStatus.UNLOADED
        
        # Update metrics
        if registration.status == StrategyStatus.ACTIVE:
            self._registry_metrics['active_strategies'] -= 1
        
        self.logger.info(f"🗑️ Strategy unloaded: {strategy_id}")
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """Completely remove a strategy from the registry"""
        if strategy_id not in self._registrations:
            self.logger.warning(f"Strategy not found for unregistration: {strategy_id}")
            return
        
        # Unload first
        asyncio.create_task(self.unload_strategy(strategy_id))
        
        # Remove registration
        registration = self._registrations[strategy_id]
        del self._registrations[strategy_id]
        
        # Remove from strategy classes if no other strategies of same type
        strategy_type = registration.strategy_type
        if not any(r.strategy_type == strategy_type for r in self._registrations.values()):
            if strategy_type in self._strategy_classes:
                del self._strategy_classes[strategy_type]
        
        self.logger.info(f"🗑️ Strategy unregistered: {strategy_id}")
    
    # ================================================================================
    # QUERY AND ACCESS METHODS
    # ================================================================================
    
    def get_strategy_registration(self, strategy_id: str) -> Optional[StrategyRegistration]:
        """Get strategy registration by ID"""
        return self._registrations.get(strategy_id)
    
    def get_active_strategy(self, strategy_id: str) -> Optional[StrategyInterface]:
        """Get active strategy instance by ID"""
        return self._active_instances.get(strategy_id)
    
    def get_all_registrations(self) -> Dict[str, StrategyRegistration]:
        """Get all strategy registrations"""
        return self._registrations.copy()
    
    def get_active_strategies(self) -> Dict[str, StrategyInterface]:
        """Get all active strategy instances"""
        return self._active_instances.copy()
    
    def get_strategies_by_type(self, strategy_type: StrategyType) -> List[StrategyRegistration]:
        """Get all strategies of a specific type"""
        return [
            registration for registration in self._registrations.values()
            if registration.strategy_type == strategy_type
        ]
    
    def get_strategies_by_status(self, status: StrategyStatus) -> List[StrategyRegistration]:
        """Get all strategies with a specific status"""
        return [
            registration for registration in self._registrations.values()
            if registration.status == status
        ]
    
    def list_strategy_ids(self) -> List[str]:
        """Get list of all registered strategy IDs"""
        return list(self._registrations.keys())
    
    def list_active_strategy_ids(self) -> List[str]:
        """Get list of active strategy IDs"""
        return [
            strategy_id for strategy_id, registration in self._registrations.items()
            if registration.status == StrategyStatus.ACTIVE
        ]
    
    def is_strategy_registered(self, strategy_id: str) -> bool:
        """Check if strategy is registered"""
        return strategy_id in self._registrations
    
    def is_strategy_active(self, strategy_id: str) -> bool:
        """Check if strategy is active"""
        registration = self._registrations.get(strategy_id)
        return registration is not None and registration.status == StrategyStatus.ACTIVE
    
    # ================================================================================
    # PERFORMANCE MONITORING
    # ================================================================================
    
    def update_strategy_performance(self, strategy_id: str, execution_time_ms: float, success: bool) -> None:
        """Update strategy performance metrics"""
        if strategy_id in self._registrations:
            self._registrations[strategy_id].update_performance(execution_time_ms, success)
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive strategy metrics"""
        registration = self._registrations.get(strategy_id)
        if not registration:
            return None
        
        return {
            'strategy_id': registration.strategy_id,
            'strategy_name': registration.strategy_name,
            'strategy_type': registration.strategy_type.value,
            'status': registration.status.value,
            'registered_at': registration.registered_at.isoformat(),
            'last_updated': registration.last_updated.isoformat(),
            'total_executions': registration.total_executions,
            'successful_executions': registration.successful_executions,
            'success_rate': registration.get_success_rate(),
            'average_execution_time_ms': registration.get_average_execution_time(),
            'error_count': registration.error_count,
            'last_error': registration.last_error,
            'required_indicators': registration.required_indicators,
            'instance_active': registration.instance is not None
        }
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get comprehensive registry summary"""
        active_count = len([r for r in self._registrations.values() if r.status == StrategyStatus.ACTIVE])
        error_count = len([r for r in self._registrations.values() if r.status == StrategyStatus.ERROR])
        
        return {
            'total_registered': len(self._registrations),
            'active_strategies': active_count,
            'error_strategies': error_count,
            'paused_strategies': len([r for r in self._registrations.values() if r.status == StrategyStatus.PAUSED]),
            'strategy_types': list(set(r.strategy_type.value for r in self._registrations.values())),
            'total_executions': sum(r.total_executions for r in self._registrations.values()),
            'total_errors': sum(r.error_count for r in self._registrations.values()),
            'registry_metrics': self._registry_metrics.copy(),
            'last_discovery': self._registry_metrics['last_discovery_time'].isoformat() if self._registry_metrics['last_discovery_time'] else None
        }
    
    def get_performance_report(self) -> str:
        """Generate detailed performance report"""
        report = []
        report.append("=" * 80)
        report.append("UNIFIED STRATEGY REGISTRY PERFORMANCE REPORT")
        report.append("=" * 80)
        
        summary = self.get_registry_summary()
        
        # Registry Overview
        report.append("REGISTRY OVERVIEW")
        report.append("-" * 40)
        report.append(f"Total Registered Strategies: {summary['total_registered']}")
        report.append(f"Active Strategies: {summary['active_strategies']}")
        report.append(f"Error Strategies: {summary['error_strategies']}")
        report.append(f"Paused Strategies: {summary['paused_strategies']}")
        report.append(f"Strategy Types: {', '.join(summary['strategy_types'])}")
        report.append("")
        
        # Performance Metrics
        report.append("PERFORMANCE METRICS")
        report.append("-" * 40)
        report.append(f"Total Executions: {summary['total_executions']:,}")
        report.append(f"Total Errors: {summary['total_errors']:,}")
        
        if summary['total_executions'] > 0:
            overall_success_rate = (summary['total_executions'] - summary['total_errors']) / summary['total_executions'] * 100
            report.append(f"Overall Success Rate: {overall_success_rate:.1f}%")
        
        report.append("")
        
        # Individual Strategy Performance
        report.append("INDIVIDUAL STRATEGY PERFORMANCE")
        report.append("-" * 40)
        
        for strategy_id, registration in self._registrations.items():
            if registration.total_executions > 0:
                report.append(f"📊 {strategy_id}:")
                report.append(f"  • Type: {registration.strategy_type.value}")
                report.append(f"  • Status: {registration.status.value}")
                report.append(f"  • Executions: {registration.total_executions}")
                report.append(f"  • Success Rate: {registration.get_success_rate():.1%}")
                report.append(f"  • Avg Time: {registration.get_average_execution_time():.2f}ms")
                if registration.error_count > 0:
                    report.append(f"  • Errors: {registration.error_count}")
                report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)

# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_unified_strategy_registry(config_manager: Optional[UnifiedConfigurationManager] = None) -> UnifiedStrategyRegistry:
    """Factory function to create unified strategy registry"""
    return UnifiedStrategyRegistry(config_manager)

async def auto_discover_and_register_strategies(
    registry: UnifiedStrategyRegistry,
    additional_paths: Optional[List[str]] = None
) -> Tuple[StrategyDiscoveryResult, List[StrategyRegistration]]:
    """
    Convenience function to automatically discover and register all strategies.
    Returns both discovery results and registration results.
    """
    # Discover strategies
    discovery_result = await registry.discover_strategies(additional_paths)
    
    # Register discovered strategies
    registrations = await registry.register_discovered_strategies(discovery_result)
    
    return discovery_result, registrations
