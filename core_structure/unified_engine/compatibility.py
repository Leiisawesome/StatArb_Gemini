"""
Compatibility Layer - Legacy Engine Support
==========================================

Provides backwards compatibility for existing code that uses the previous
three-engine architecture. Allows seamless migration to UnifiedTradingEngine
while maintaining existing API contracts.

Features:
- Legacy engine API emulation
- Automatic migration and delegation
- Drop-in replacement classes
- Configuration translation
- Strategy interface adaptation

Author: Professional Trading System Architecture
Version: 1.0 (Compatibility Layer)
"""

import logging
import warnings
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
import asyncio

# Import unified components (Updated for new structure)
from .engine import UnifiedTradingEngine, UnifiedEngineConfig, UnifiedTradingResult
from .factory import UnifiedEngineFactory, create_unified_engine, migrate_legacy_engine
from .configuration import Environment, TradingMode
from ..interfaces.strategy_interfaces import StrategyInterface, StrategyContext

# Legacy imports (with fallbacks) - unified_core_engine moved to archived
LEGACY_CORE_AVAILABLE = False
# Create placeholder classes for legacy compatibility
class CoreEngineConfig:
    """Legacy CoreEngineConfig compatibility class"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class EngineStatus:
    """Legacy EngineStatus compatibility class"""
    READY = "ready"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class StrategyConfig:
    """Legacy StrategyConfig compatibility class"""
    def __init__(self, strategy_id: str = "", strategy_type: str = "", **kwargs):
        self.strategy_id = strategy_id
        self.strategy_type = strategy_type
        for key, value in kwargs.items():
            setattr(self, key, value)

class TradingResult:
    """Legacy TradingResult compatibility class"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

logger = logging.getLogger(__name__)

# ================================================================================
# COMPATIBILITY WARNINGS
# ================================================================================

def _emit_deprecation_warning(old_class: str, new_class: str = "UnifiedTradingEngine"):
    """Emit deprecation warning for legacy engine usage"""
    warnings.warn(
        f"{old_class} is deprecated and will be removed in a future version. "
        f"Please migrate to {new_class} using the UnifiedEngineFactory.",
        DeprecationWarning,
        stacklevel=3
    )

# ================================================================================
# LEGACY CORE ENGINE COMPATIBILITY
# ================================================================================

class UnifiedCoreEngineCompat:
    """
    Compatibility wrapper for UnifiedCoreEngine.
    Provides the same API while delegating to UnifiedTradingEngine.
    """
    
    def __init__(self, config: Optional[CoreEngineConfig] = None):
        _emit_deprecation_warning("UnifiedCoreEngine")
        
        # Convert legacy config to unified config
        unified_config = self._convert_legacy_config(config)
        
        # Create unified engine through factory
        factory = UnifiedEngineFactory()
        self._unified_engine = factory.create_development_engine()
        
        # Maintain legacy API properties
        self.config = config or CoreEngineConfig()
        self.status = EngineStatus.READY
        self.logger = logging.getLogger(__name__)
        
        # Legacy property mappings
        self._strategy_instances = {}
        self._strategy_configs = {}
        self._engine_metrics = None
        
        self.logger.info("🔄 UnifiedCoreEngine compatibility layer active")
    
    def _convert_legacy_config(self, config: Optional[CoreEngineConfig]) -> UnifiedEngineConfig:
        """Convert legacy config to unified format"""
        if not config:
            return UnifiedEngineConfig()
        
        # Map legacy settings to unified format
        unified_config = UnifiedEngineConfig(
            engine_id=getattr(config, 'engine_id', f"compat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            trading_mode=TradingMode.PAPER_TRADING
        )
        
        return unified_config
    
    # Legacy API methods - delegate to unified engine
    async def initialize(self) -> bool:
        """Legacy initialize method"""
        return True  # Unified engine initializes in constructor
    
    def register_strategy(self, strategy_id: str, strategy: StrategyInterface, 
                         config: Optional[Dict[str, Any]] = None) -> bool:
        """Legacy strategy registration"""
        result = self._unified_engine.register_strategy(strategy_id, strategy, config)
        
        # Update legacy tracking
        self._strategy_instances[strategy_id] = strategy
        if config:
            self._strategy_configs[strategy_id] = config
        
        return result
    
    def unregister_strategy(self, strategy_id: str) -> bool:
        """Legacy strategy unregistration"""
        result = self._unified_engine.unregister_strategy(strategy_id)
        
        # Update legacy tracking
        self._strategy_instances.pop(strategy_id, None)
        self._strategy_configs.pop(strategy_id, None)
        
        return result
    
    async def execute_trading_cycle(self, market_data, target_strategies: Optional[List[str]] = None):
        """Legacy trading cycle execution"""
        results = await self._unified_engine.execute_trading_cycle(market_data, target_strategies)
        
        # Convert unified results to legacy format if needed
        return self._convert_to_legacy_results(results)
    
    def get_strategy_metrics(self, strategy_id: str) -> Dict[str, Any]:
        """Legacy strategy metrics"""
        return self._unified_engine.get_strategy_metrics(strategy_id)
    
    def get_registered_strategies(self) -> List[str]:
        """Legacy registered strategies list"""
        return self._unified_engine.get_registered_strategies()
    
    async def shutdown(self):
        """Legacy shutdown method"""
        await self._unified_engine.shutdown()
    
    def _convert_to_legacy_results(self, unified_results: List[UnifiedTradingResult]) -> List[Dict[str, Any]]:
        """Convert unified results to legacy format"""
        legacy_results = []
        
        for result in unified_results:
            legacy_result = {
                'strategy_id': result.strategy_id,
                'signals_generated': len(result.signals_generated),
                'orders_executed': len(result.execution_results),
                'success': result.success,
                'execution_time_ms': result.execution_time_ms,
                'errors': result.errors
            }
            legacy_results.append(legacy_result)
        
        return legacy_results

# ================================================================================
# DELEGATED CORE ENGINE COMPATIBILITY
# ================================================================================

class DelegatedCoreEngineCompat:
    """
    Compatibility wrapper for DelegatedCoreEngine.
    Provides pure delegation pattern API while using UnifiedTradingEngine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        _emit_deprecation_warning("DelegatedCoreEngine")
        
        # Create unified engine with delegation-focused settings
        factory = UnifiedEngineFactory()
        self._unified_engine = factory.builder().with_environment(Environment.DEVELOPMENT).build()
        
        # Legacy properties
        self.config = config or {}
        self.is_initialized = True
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🔄 DelegatedCoreEngine compatibility layer active")
    
    async def process_market_data(self, market_data, strategy_filter: Optional[Callable] = None):
        """Legacy market data processing with strategy filtering"""
        # Apply strategy filter if provided
        target_strategies = None
        if strategy_filter:
            all_strategies = self._unified_engine.get_registered_strategies()
            target_strategies = [s for s in all_strategies if strategy_filter(s)]
        
        return await self._unified_engine.execute_trading_cycle(market_data, target_strategies)
    
    def validate_strategy_compatibility(self, strategy: StrategyInterface) -> bool:
        """Legacy strategy compatibility validation"""
        # Use unified engine's validation logic
        return hasattr(strategy, 'generate_signals') and callable(strategy.generate_signals)
    
    async def delegate_signal_generation(self, strategy_id: str, context: StrategyContext):
        """Legacy signal generation delegation"""
        # This would be handled internally by unified engine during trading cycle
        strategy_metrics = self._unified_engine.get_strategy_metrics(strategy_id)
        return strategy_metrics.get('last_signals', [])
    
    # Delegate other methods to unified engine
    def register_strategy(self, strategy_id: str, strategy: StrategyInterface) -> bool:
        return self._unified_engine.register_strategy(strategy_id, strategy)
    
    def get_registered_strategies(self) -> List[str]:
        return self._unified_engine.get_registered_strategies()
    
    async def shutdown(self):
        await self._unified_engine.shutdown()

# ================================================================================
# OPTIMIZED CORE ENGINE COMPATIBILITY
# ================================================================================

class OptimizedCoreEngineCompat:
    """
    Compatibility wrapper for OptimizedCoreEngine.
    Provides performance optimization API while using UnifiedTradingEngine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        _emit_deprecation_warning("OptimizedCoreEngine")
        
        # Create unified engine with full optimizations
        factory = UnifiedEngineFactory()
        self._unified_engine = factory.create_production_engine()
        
        # Legacy properties
        self.config = config or {}
        self.optimization_enabled = True
        self.performance_metrics = {}
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🔄 OptimizedCoreEngine compatibility layer active")
    
    def enable_hot_path_optimization(self) -> bool:
        """Legacy hot path optimization enablement"""
        # Already enabled in production engine
        return self._unified_engine.config.enable_hot_path_optimization
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Legacy optimization metrics"""
        return self._unified_engine.get_performance_summary()
    
    def configure_object_pooling(self, pool_sizes: Dict[str, int]) -> bool:
        """Legacy object pooling configuration"""
        # Object pooling is already configured in unified engine
        return self._unified_engine.config.enable_object_pooling
    
    async def execute_optimized_cycle(self, market_data, optimization_level: str = "high"):
        """Legacy optimized cycle execution"""
        # Unified engine always uses optimizations when enabled
        return await self._unified_engine.execute_trading_cycle(market_data)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Legacy cache statistics"""
        summary = self._unified_engine.get_performance_summary()
        return summary.get('cache_statistics', {})
    
    def clear_performance_caches(self):
        """Legacy cache clearing"""
        self._unified_engine.clear_performance_caches()
    
    # Delegate other methods
    def register_strategy(self, strategy_id: str, strategy: StrategyInterface) -> bool:
        return self._unified_engine.register_strategy(strategy_id, strategy)
    
    async def shutdown(self):
        await self._unified_engine.shutdown()

# ================================================================================
# INTEGRATION ADAPTER COMPATIBILITY
# ================================================================================

class TwoLayerIntegrationAdapterCompat:
    """
    Compatibility wrapper for TwoLayerIntegrationAdapter.
    Provides integration testing API while using UnifiedTradingEngine.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        _emit_deprecation_warning("TwoLayerIntegrationAdapter")
        
        # Create unified engine for integration testing
        factory = UnifiedEngineFactory()
        self._unified_engine = factory.create_development_engine(enable_debug=True)
        
        # Legacy properties
        self.config = config or {}
        self.is_initialized = False
        self.metrics = {}
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("🔄 TwoLayerIntegrationAdapter compatibility layer active")
    
    async def initialize(self, strategy_config: Dict[str, Any]) -> bool:
        """Legacy initialization"""
        self.is_initialized = True
        return True
    
    async def execute_with_comparison(self, market_data, mode: str = "unified"):
        """Legacy A/B testing execution"""
        # Always use unified engine (no comparison needed)
        results = await self._unified_engine.execute_trading_cycle(market_data)
        
        # Format as comparison results
        return {
            'unified_results': results,
            'legacy_results': [],  # No legacy engine to compare
            'performance_comparison': self._unified_engine.get_performance_summary()
        }
    
    def get_integration_metrics(self) -> Dict[str, Any]:
        """Legacy integration metrics"""
        return {
            'unified_engine_metrics': self._unified_engine.get_performance_summary(),
            'integration_status': 'unified_only',
            'migration_complete': True
        }

# ================================================================================
# STRATEGY INTERFACE ADAPTERS
# ================================================================================

class LegacyStrategyAdapter:
    """
    Adapter to make legacy strategies work with UnifiedTradingEngine.
    Handles interface differences and method mapping.
    """
    
    def __init__(self, legacy_strategy: Any):
        self.legacy_strategy = legacy_strategy
        self.logger = logging.getLogger(__name__)
    
    @property
    def strategy_id(self) -> str:
        """Map legacy strategy name to ID"""
        if hasattr(self.legacy_strategy, 'get_strategy_name'):
            return self.legacy_strategy.get_strategy_name()
        elif hasattr(self.legacy_strategy, 'name'):
            return self.legacy_strategy.name
        else:
            return f"legacy_{id(self.legacy_strategy)}"
    
    @property
    def strategy_type(self):
        """Default strategy type for legacy strategies"""
        return "legacy_strategy"
    
    @property
    def required_indicators(self) -> List[str]:
        """Map legacy required indicators"""
        if hasattr(self.legacy_strategy, 'get_required_indicators'):
            return self.legacy_strategy.get_required_indicators()
        return []
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Map legacy parameter validation"""
        if hasattr(self.legacy_strategy, 'validate_parameters'):
            return self.legacy_strategy.validate_parameters(config)
        return True
    
    async def generate_signals(self, context: StrategyContext):
        """Adapt legacy signal generation to unified interface"""
        try:
            # Try different legacy signal generation methods
            if hasattr(self.legacy_strategy, 'calculate_signals'):
                # Trade engine interface
                raw_signals = self.legacy_strategy.calculate_signals(context.market_data)
                return self._convert_raw_signals_to_unified(raw_signals)
            
            elif hasattr(self.legacy_strategy, 'generate_signals'):
                # Core structure interface
                if asyncio.iscoroutinefunction(self.legacy_strategy.generate_signals):
                    return await self.legacy_strategy.generate_signals(context)
                else:
                    return self.legacy_strategy.generate_signals(context.market_data)
            
            else:
                self.logger.warning(f"Legacy strategy {self.strategy_id} has no recognized signal generation method")
                return []
                
        except Exception as e:
            self.logger.error(f"Legacy strategy {self.strategy_id} signal generation failed: {e}")
            return []
    
    def _convert_raw_signals_to_unified(self, raw_signals: List[Any]):
        """Convert legacy raw signals to unified format"""
        # This would implement the actual conversion logic
        # For now, return as-is (placeholder)
        return raw_signals
    
    def get_strategy_metrics(self):
        """Map legacy metrics to unified format"""
        if hasattr(self.legacy_strategy, 'get_performance_metrics'):
            return self.legacy_strategy.get_performance_metrics()
        return {}
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Map legacy parameter updates"""
        if hasattr(self.legacy_strategy, 'set_parameters'):
            self.legacy_strategy.set_parameters(parameters)
        elif hasattr(self.legacy_strategy, 'update_config'):
            self.legacy_strategy.update_config(parameters)

# ================================================================================
# CONVENIENCE FUNCTIONS FOR MIGRATION
# ================================================================================

def wrap_legacy_strategy(legacy_strategy: Any) -> LegacyStrategyAdapter:
    """
    Wrap a legacy strategy to work with UnifiedTradingEngine.
    
    Args:
        legacy_strategy: Legacy strategy instance
        
    Returns:
        Adapted strategy compatible with unified engine
    """
    return LegacyStrategyAdapter(legacy_strategy)

def create_compatible_engine(engine_type: str = "unified", **kwargs) -> UnifiedTradingEngine:
    """
    Create engine with compatibility for different legacy types.
    
    Args:
        engine_type: Type of engine compatibility ("core", "delegated", "optimized", "unified")
        **kwargs: Additional configuration parameters
        
    Returns:
        UnifiedTradingEngine configured for compatibility
    """
    factory = UnifiedEngineFactory()
    
    if engine_type == "core":
        return factory.create_development_engine()
    elif engine_type == "delegated":
        return factory.builder().with_environment(Environment.DEVELOPMENT).build()
    elif engine_type == "optimized":
        return factory.create_production_engine()
    else:  # unified
        return factory.create_development_engine()

def migrate_existing_system(legacy_engines: List[Any]) -> UnifiedTradingEngine:
    """
    Migrate an entire system with multiple legacy engines to unified engine.
    
    Args:
        legacy_engines: List of legacy engine instances
        
    Returns:
        Single UnifiedTradingEngine replacing all legacy engines
    """
    factory = UnifiedEngineFactory()
    
    # Create unified engine
    unified_engine = factory.create_production_engine()
    
    # Migrate strategies from all legacy engines
    for legacy_engine in legacy_engines:
        try:
            # Extract and migrate strategies
            if hasattr(legacy_engine, '_strategy_instances'):
                for strategy_id, strategy in legacy_engine._strategy_instances.items():
                    adapted_strategy = wrap_legacy_strategy(strategy)
                    unified_engine.register_strategy(strategy_id, adapted_strategy)
                    
            logger.info(f"✅ Migrated strategies from {type(legacy_engine).__name__}")
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate from {type(legacy_engine).__name__}: {e}")
    
    return unified_engine

# ================================================================================
# LEGACY ENGINE REPLACEMENTS (Drop-in replacements)
# ================================================================================

# These can be imported as drop-in replacements for legacy engines
UnifiedCoreEngine = UnifiedCoreEngineCompat
DelegatedCoreEngine = DelegatedCoreEngineCompat  
OptimizedCoreEngine = OptimizedCoreEngineCompat
TwoLayerIntegrationAdapter = TwoLayerIntegrationAdapterCompat
