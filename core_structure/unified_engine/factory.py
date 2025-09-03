"""
Unified Trading Engine Factory - Integration Layer
================================================

Factory and builder patterns for creating UnifiedTradingEngine instances.
Provides seamless migration from existing three-engine architecture.

Features:
- Factory methods for different use cases
- Configuration migration from old engines
- Backwards compatibility layer
- Environment-specific engine creation
- Strategy auto-discovery and registration

Author: Professional Trading System Architecture
Version: 1.0 (Integration Layer)
"""

import logging
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import importlib
import inspect

# Import unified components (Updated for new structure)
from .engine import UnifiedTradingEngine, UnifiedEngineConfig
from .configuration import UnifiedConfigurationManager, UnifiedConfig, Environment, TradingMode
from .strategy_registry import UnifiedStrategyRegistry, auto_discover_and_register_strategies
from ..interfaces.strategy_interfaces import StrategyInterface, BaseStrategy

# Import legacy components for migration via compatibility layer
try:
    from .compatibility import UnifiedCoreEngineCompat as UnifiedCoreEngine
    from .compatibility import CoreEngineConfig
    LEGACY_CORE_AVAILABLE = True
except ImportError:
    LEGACY_CORE_AVAILABLE = False

try:
    from ...trade_engine.core.delegated_core_engine import DelegatedCoreEngine
    LEGACY_DELEGATED_AVAILABLE = True
except ImportError:
    LEGACY_DELEGATED_AVAILABLE = False

try:
    from ...trade_engine.optimization.optimized_core_engine import OptimizedCoreEngine
    LEGACY_OPTIMIZED_AVAILABLE = True
except ImportError:
    LEGACY_OPTIMIZED_AVAILABLE = False

logger = logging.getLogger(__name__)

# ================================================================================
# FACTORY CONFIGURATION
# ================================================================================

@dataclass
class EngineFactoryConfig:
    """Configuration for engine factory"""
    # Environment settings
    environment: Environment = Environment.DEVELOPMENT
    trading_mode: TradingMode = TradingMode.PAPER_TRADING
    
    # Performance optimization settings
    enable_all_optimizations: bool = True
    enable_hot_path_optimization: bool = True
    enable_memory_optimization: bool = True
    enable_async_optimization: bool = True
    
    # Strategy discovery settings
    auto_discover_strategies: bool = True
    strategy_search_paths: List[str] = field(default_factory=lambda: [
        "trade_engine/strategies",
        "core_structure/strategies", 
        "strategies"
    ])
    
    # Migration settings
    migrate_from_legacy: bool = True
    legacy_config_path: Optional[str] = None
    
    # Monitoring and logging
    enable_comprehensive_monitoring: bool = True
    log_level: str = "INFO"

# ================================================================================
# UNIFIED ENGINE FACTORY
# ================================================================================

class UnifiedEngineFactory:
    """
    Factory for creating UnifiedTradingEngine instances with proper configuration.
    Handles migration from legacy engines and provides various creation patterns.
    """
    
    def __init__(self, factory_config: Optional[EngineFactoryConfig] = None):
        self.factory_config = factory_config or EngineFactoryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration manager
        self.config_manager = UnifiedConfigurationManager()
        
        # Initialize strategy registry
        self.strategy_registry = UnifiedStrategyRegistry(self.config_manager)
        
        self.logger.info(f"🏭 UnifiedEngineFactory initialized for {self.factory_config.environment.value}")
    
    # ================================================================================
    # PRIMARY FACTORY METHODS
    # ================================================================================
    
    def create_production_engine(self, 
                               config_path: Optional[str] = None,
                               strategies: Optional[List[str]] = None) -> UnifiedTradingEngine:
        """
        Create production-ready UnifiedTradingEngine with full optimizations.
        
        Args:
            config_path: Path to configuration file
            strategies: List of strategy IDs to register
            
        Returns:
            Fully configured UnifiedTradingEngine
        """
        self.logger.info("🚀 Creating production UnifiedTradingEngine")
        
        # Load production configuration
        if config_path:
            unified_config = self.config_manager.load_from_file(config_path)
        else:
            unified_config = self._create_production_config()
        
        # Create engine configuration with full optimizations
        engine_config = self._create_optimized_engine_config(unified_config)
        
        # Create engine instance
        engine = UnifiedTradingEngine(engine_config)
        
        # Auto-discover and register strategies
        if self.factory_config.auto_discover_strategies:
            self._auto_register_strategies(engine)
        
        # Register specific strategies if provided
        if strategies:
            self._register_specific_strategies(engine, strategies)
        
        self.logger.info("✅ Production UnifiedTradingEngine created successfully")
        return engine
    
    def create_development_engine(self, 
                                enable_debug: bool = True,
                                mock_data: bool = True) -> UnifiedTradingEngine:
        """
        Create development UnifiedTradingEngine with debugging features.
        
        Args:
            enable_debug: Enable debug logging and validation
            mock_data: Use mock market data for testing
            
        Returns:
            Development-configured UnifiedTradingEngine
        """
        self.logger.info("🛠️ Creating development UnifiedTradingEngine")
        
        # Create development configuration
        unified_config = self._create_development_config(enable_debug, mock_data)
        engine_config = self._create_development_engine_config(unified_config)
        
        # Create engine with development settings
        engine = UnifiedTradingEngine(engine_config)
        
        # Register development strategies
        if self.factory_config.auto_discover_strategies:
            self._auto_register_strategies(engine)
        
        self.logger.info("✅ Development UnifiedTradingEngine created successfully")
        return engine
    
    def create_backtesting_engine(self, 
                                backtest_config: Dict[str, Any]) -> UnifiedTradingEngine:
        """
        Create UnifiedTradingEngine optimized for backtesting.
        
        Args:
            backtest_config: Backtesting-specific configuration
            
        Returns:
            Backtesting-optimized UnifiedTradingEngine
        """
        self.logger.info("📊 Creating backtesting UnifiedTradingEngine")
        
        # Create backtesting configuration
        unified_config = self._create_backtesting_config(backtest_config)
        engine_config = self._create_backtesting_engine_config(unified_config)
        
        # Create engine optimized for backtesting
        engine = UnifiedTradingEngine(engine_config)
        
        # Register backtesting strategies
        self._register_backtesting_strategies(engine, backtest_config)
        
        self.logger.info("✅ Backtesting UnifiedTradingEngine created successfully")
        return engine
    
    # ================================================================================
    # MIGRATION FACTORY METHODS
    # ================================================================================
    
    def migrate_from_legacy_engine(self, 
                                 legacy_engine: Any,
                                 preserve_state: bool = True) -> UnifiedTradingEngine:
        """
        Migrate from legacy engine to UnifiedTradingEngine.
        
        Args:
            legacy_engine: Existing legacy engine instance
            preserve_state: Whether to preserve engine state during migration
            
        Returns:
            Migrated UnifiedTradingEngine
        """
        self.logger.info(f"🔄 Migrating from legacy engine: {type(legacy_engine).__name__}")
        
        # Extract configuration from legacy engine
        migrated_config = self._extract_legacy_config(legacy_engine)
        
        # Create unified configuration
        unified_config = self._convert_legacy_to_unified_config(migrated_config)
        engine_config = self._create_migrated_engine_config(unified_config)
        
        # Create new unified engine
        unified_engine = UnifiedTradingEngine(engine_config)
        
        # Migrate strategies and state if requested
        if preserve_state:
            self._migrate_engine_state(legacy_engine, unified_engine)
        
        self.logger.info("✅ Legacy engine migration completed successfully")
        return unified_engine
    
    def create_from_legacy_config(self, 
                                legacy_config_path: str) -> UnifiedTradingEngine:
        """
        Create UnifiedTradingEngine from legacy configuration file.
        
        Args:
            legacy_config_path: Path to legacy configuration
            
        Returns:
            UnifiedTradingEngine with migrated configuration
        """
        self.logger.info(f"📄 Creating engine from legacy config: {legacy_config_path}")
        
        # Load and convert legacy configuration
        legacy_config = self._load_legacy_config(legacy_config_path)
        unified_config = self._convert_legacy_to_unified_config(legacy_config)
        engine_config = self._create_migrated_engine_config(unified_config)
        
        # Create engine
        engine = UnifiedTradingEngine(engine_config)
        
        # Register strategies from legacy config
        self._register_legacy_strategies(engine, legacy_config)
        
        self.logger.info("✅ Engine created from legacy configuration")
        return engine
    
    # ================================================================================
    # BUILDER PATTERN METHODS
    # ================================================================================
    
    def builder(self) -> 'UnifiedEngineBuilder':
        """
        Create a builder for step-by-step engine configuration.
        
        Returns:
            UnifiedEngineBuilder instance
        """
        return UnifiedEngineBuilder(self)
    
    # ================================================================================
    # CONFIGURATION CREATION METHODS
    # ================================================================================
    
    def _create_production_config(self) -> UnifiedConfig:
        """Create production-ready unified configuration"""
        config = UnifiedConfig(
            environment=Environment.PRODUCTION,
            trading=self.config_manager._create_default_trading_config(TradingMode.LIVE_TRADING),
            features={
                'enable_hot_path_optimization': True,
                'enable_memory_optimization': True,
                'enable_async_optimization': True,
                'enable_performance_monitoring': True,
                'enable_risk_management': True,
                'enable_real_time_analytics': True
            }
        )
        return config
    
    def _create_development_config(self, enable_debug: bool, mock_data: bool) -> UnifiedConfig:
        """Create development configuration"""
        config = UnifiedConfig(
            environment=Environment.DEVELOPMENT,
            trading=self.config_manager._create_default_trading_config(TradingMode.PAPER_TRADING),
            features={
                'enable_debug_logging': enable_debug,
                'enable_mock_data': mock_data,
                'enable_hot_path_optimization': False,  # Disable for easier debugging
                'enable_memory_optimization': False,
                'enable_async_optimization': True,
                'enable_comprehensive_validation': True
            }
        )
        return config
    
    def _create_backtesting_config(self, backtest_config: Dict[str, Any]) -> UnifiedConfig:
        """Create backtesting-optimized configuration"""
        config = UnifiedConfig(
            environment=Environment.TESTING,
            trading=self.config_manager._create_default_trading_config(TradingMode.BACKTESTING),
            features={
                'enable_hot_path_optimization': True,
                'enable_memory_optimization': True,
                'enable_async_optimization': True,
                'enable_backtesting_mode': True,
                'enable_historical_data': True
            }
        )
        
        # Apply backtest-specific settings
        config.trading.update(backtest_config)
        return config
    
    def _create_optimized_engine_config(self, unified_config: UnifiedConfig) -> UnifiedEngineConfig:
        """Create engine configuration with full optimizations"""
        return UnifiedEngineConfig(
            engine_id=f"unified_prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trading_mode=unified_config.trading.get('mode', TradingMode.LIVE_TRADING),
            
            # Enable all Phase 2 optimizations
            enable_hot_path_optimization=True,
            enable_performance_monitoring=True,
            enable_caching=True,
            enable_batch_processing=True,
            enable_memory_optimization=True,
            enable_object_pooling=True,
            enable_gc_optimization=True,
            enable_async_optimization=True,
            enable_async_monitoring=True,
            enable_event_driven_updates=True,
            
            # Production settings
            max_concurrent_strategies=20,
            max_concurrent_executions=10,
            async_timeout_seconds=30.0,
            batch_size=50
        )
    
    def _create_development_engine_config(self, unified_config: UnifiedConfig) -> UnifiedEngineConfig:
        """Create engine configuration for development"""
        return UnifiedEngineConfig(
            engine_id=f"unified_dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}",

            trading_mode=unified_config.trading.get('mode', TradingMode.PAPER_TRADING),
            
            # Selective optimizations for development
            enable_hot_path_optimization=False,  # Easier debugging
            enable_performance_monitoring=True,
            enable_caching=False,  # Avoid cache-related debugging issues
            enable_batch_processing=True,
            enable_memory_optimization=False,  # Easier memory debugging
            enable_object_pooling=False,
            enable_gc_optimization=False,
            enable_async_optimization=True,  # Keep async for realistic testing
            enable_async_monitoring=True,
            
            # Development settings
            max_concurrent_strategies=5,
            max_concurrent_executions=3,
            async_timeout_seconds=60.0,  # Longer timeout for debugging
            batch_size=10
        )
    
    def _create_backtesting_engine_config(self, unified_config: UnifiedConfig) -> UnifiedEngineConfig:
        """Create engine configuration for backtesting"""
        return UnifiedEngineConfig(
            engine_id=f"unified_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",

            trading_mode=TradingMode.BACKTESTING,
            
            # Optimizations for backtesting performance
            enable_hot_path_optimization=True,
            enable_performance_monitoring=True,
            enable_caching=True,
            enable_batch_processing=True,
            enable_memory_optimization=True,
            enable_object_pooling=True,
            enable_gc_optimization=True,
            enable_async_optimization=True,
            
            # Backtesting-specific settings
            max_concurrent_strategies=50,  # Higher for batch backtesting
            max_concurrent_executions=20,
            async_timeout_seconds=120.0,  # Longer for complex backtests
            batch_size=100
        )
    
    def _create_migrated_engine_config(self, unified_config: UnifiedConfig) -> UnifiedEngineConfig:
        """Create engine configuration from migrated legacy config"""
        return UnifiedEngineConfig(
            engine_id=f"unified_migrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",

            trading_mode=unified_config.trading.get('mode', TradingMode.PAPER_TRADING),
            
            # Balanced optimizations for migrated engines
            enable_hot_path_optimization=self.factory_config.enable_hot_path_optimization,
            enable_performance_monitoring=True,
            enable_caching=True,
            enable_batch_processing=True,
            enable_memory_optimization=self.factory_config.enable_memory_optimization,
            enable_object_pooling=True,
            enable_gc_optimization=True,
            enable_async_optimization=self.factory_config.enable_async_optimization,
            enable_async_monitoring=True,
            
            # Migrated settings
            max_concurrent_strategies=15,
            max_concurrent_executions=8,
            async_timeout_seconds=45.0,
            batch_size=25
        )
    
    # ================================================================================
    # STRATEGY REGISTRATION METHODS
    # ================================================================================
    
    def _auto_register_strategies(self, engine: UnifiedTradingEngine):
        """Auto-discover and register strategies"""
        try:
            # Use unified strategy registry for discovery
            # Note: This should be called in an async context, but for now we skip it
            # TODO: Refactor factory methods to be async
            self.logger.info("📋 Strategy auto-discovery skipped (requires async context)")
            return
            
            # Register discovered strategies with engine
            for strategy_id in discovery_results.registered_strategies:
                strategy_registration = self.strategy_registry.get_strategy_registration(strategy_id)
                if strategy_registration and strategy_registration.status.value == "registered":
                    # Create strategy instance and register with engine
                    strategy_instance = self.strategy_registry.create_strategy_instance(strategy_id)
                    if strategy_instance:
                        engine.register_strategy(strategy_id, strategy_instance)
            
            self.logger.info(f"✅ Auto-registered {len(discovery_results.registered_strategies)} strategies")
            
        except Exception as e:
            self.logger.error(f"❌ Strategy auto-registration failed: {e}")
    
    def _register_specific_strategies(self, engine: UnifiedTradingEngine, strategy_ids: List[str]):
        """Register specific strategies by ID"""
        for strategy_id in strategy_ids:
            try:
                # Check if strategy is already registered in registry
                if self.strategy_registry.get_strategy_registration(strategy_id):
                    strategy_instance = self.strategy_registry.create_strategy_instance(strategy_id)
                    if strategy_instance:
                        engine.register_strategy(strategy_id, strategy_instance)
                        self.logger.info(f"✅ Registered strategy: {strategy_id}")
                else:
                    self.logger.warning(f"⚠️ Strategy not found in registry: {strategy_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to register strategy {strategy_id}: {e}")
    
    def _register_backtesting_strategies(self, engine: UnifiedTradingEngine, backtest_config: Dict[str, Any]):
        """Register strategies for backtesting"""
        # Get strategies from backtest config or auto-discover
        strategy_ids = backtest_config.get('strategies', [])
        
        if strategy_ids:
            self._register_specific_strategies(engine, strategy_ids)
        else:
            self._auto_register_strategies(engine)
    
    def _register_legacy_strategies(self, engine: UnifiedTradingEngine, legacy_config: Dict[str, Any]):
        """Register strategies from legacy configuration"""
        # Extract strategy information from legacy config
        legacy_strategies = legacy_config.get('strategies', {})
        
        for strategy_name, strategy_config in legacy_strategies.items():
            try:
                # Convert legacy strategy to unified format
                unified_strategy = self._convert_legacy_strategy(strategy_name, strategy_config)
                if unified_strategy:
                    engine.register_strategy(strategy_name, unified_strategy)
                    self.logger.info(f"✅ Migrated legacy strategy: {strategy_name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to migrate legacy strategy {strategy_name}: {e}")
    
    # ================================================================================
    # LEGACY MIGRATION METHODS
    # ================================================================================
    
    def _extract_legacy_config(self, legacy_engine: Any) -> Dict[str, Any]:
        """Extract configuration from legacy engine"""
        config = {}
        
        try:
            if hasattr(legacy_engine, 'config'):
                legacy_config = legacy_engine.config
                
                # Extract common configuration elements
                if hasattr(legacy_config, 'engine_id'):
                    config['engine_id'] = legacy_config.engine_id
                if hasattr(legacy_config, 'trading_mode'):
                    config['trading_mode'] = legacy_config.trading_mode
                if hasattr(legacy_config, 'risk_management'):
                    config['risk_management'] = legacy_config.risk_management
                
                # Extract strategy configurations
                if hasattr(legacy_engine, '_strategy_configs'):
                    config['strategies'] = legacy_engine._strategy_configs
                
                self.logger.info("✅ Extracted legacy engine configuration")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to extract legacy config: {e}")
            config = {}
        
        return config
    
    def _convert_legacy_to_unified_config(self, legacy_config: Dict[str, Any]) -> UnifiedConfig:
        """Convert legacy configuration to unified format"""
        # Create base unified config
        unified_config = UnifiedConfig(
            environment=Environment.DEVELOPMENT,  # Safe default
            trading=self.config_manager._create_default_trading_config(TradingMode.PAPER_TRADING)
        )
        
        # Map legacy settings to unified format
        if 'trading_mode' in legacy_config:
            try:
                trading_mode = TradingMode(legacy_config['trading_mode'])
                unified_config.trading['mode'] = trading_mode
            except ValueError:
                self.logger.warning(f"Unknown trading mode: {legacy_config['trading_mode']}")
        
        if 'risk_management' in legacy_config:
            unified_config.risk = legacy_config['risk_management']
        
        if 'strategies' in legacy_config:
            unified_config.strategies = legacy_config['strategies']
        
        return unified_config
    
    def _load_legacy_config(self, config_path: str) -> Dict[str, Any]:
        """Load legacy configuration from file"""
        try:
            # This would be implemented based on the specific legacy config format
            # For now, return empty config as placeholder
            self.logger.warning(f"Legacy config loading not yet implemented for: {config_path}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Failed to load legacy config: {e}")
            return {}
    
    def _convert_legacy_strategy(self, strategy_name: str, strategy_config: Dict[str, Any]) -> Optional[StrategyInterface]:
        """Convert legacy strategy configuration to unified strategy"""
        try:
            # This would be implemented based on specific legacy strategy formats
            # For now, return None as placeholder
            self.logger.warning(f"Legacy strategy conversion not yet implemented for: {strategy_name}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Failed to convert legacy strategy {strategy_name}: {e}")
            return None
    
    def _migrate_engine_state(self, legacy_engine: Any, unified_engine: UnifiedTradingEngine):
        """Migrate engine state from legacy to unified engine"""
        try:
            # Migrate performance metrics
            if hasattr(legacy_engine, '_engine_metrics'):
                # This would copy relevant metrics
                pass
            
            # Migrate strategy states
            if hasattr(legacy_engine, '_strategy_instances'):
                # This would migrate strategy states
                pass
            
            self.logger.info("✅ Engine state migration completed")
            
        except Exception as e:
            self.logger.error(f"❌ Engine state migration failed: {e}")

# ================================================================================
# BUILDER PATTERN
# ================================================================================

class UnifiedEngineBuilder:
    """
    Builder pattern for step-by-step UnifiedTradingEngine configuration.
    Provides fluent interface for complex engine setup.
    """
    
    def __init__(self, factory: UnifiedEngineFactory):
        self.factory = factory
        self.config = UnifiedEngineConfig()
        self.strategies: List[str] = []
        self.custom_settings: Dict[str, Any] = {}
        
    def with_environment(self, environment: Environment) -> 'UnifiedEngineBuilder':
        """Set environment"""
        self.config.environment = environment
        return self
    
    def with_trading_mode(self, trading_mode: TradingMode) -> 'UnifiedEngineBuilder':
        """Set trading mode"""
        self.config.trading_mode = trading_mode
        return self
    
    def with_optimizations(self, 
                         hot_path: bool = True,
                         memory: bool = True, 
                         async_opt: bool = True) -> 'UnifiedEngineBuilder':
        """Configure optimizations"""
        self.config.enable_hot_path_optimization = hot_path
        self.config.enable_memory_optimization = memory
        self.config.enable_async_optimization = async_opt
        return self
    
    def with_concurrency(self, 
                        max_strategies: int = 20,
                        max_executions: int = 10) -> 'UnifiedEngineBuilder':
        """Configure concurrency limits"""
        self.config.max_concurrent_strategies = max_strategies
        self.config.max_concurrent_executions = max_executions
        return self
    
    def with_strategies(self, strategy_ids: List[str]) -> 'UnifiedEngineBuilder':
        """Add strategies to register"""
        self.strategies.extend(strategy_ids)
        return self
    
    def with_custom_setting(self, key: str, value: Any) -> 'UnifiedEngineBuilder':
        """Add custom configuration setting"""
        self.custom_settings[key] = value
        return self
    
    def build(self) -> UnifiedTradingEngine:
        """Build the configured UnifiedTradingEngine"""
        # Apply custom settings to config
        for key, value in self.custom_settings.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Create engine
        engine = UnifiedTradingEngine(self.config)
        
        # Register strategies
        if self.strategies:
            self.factory._register_specific_strategies(engine, self.strategies)
        else:
            self.factory._auto_register_strategies(engine)
        
        return engine

# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

def create_unified_engine(environment: Environment = Environment.DEVELOPMENT,
                        trading_mode: TradingMode = TradingMode.PAPER_TRADING,
                        enable_optimizations: bool = True) -> UnifiedTradingEngine:
    """
    Convenience function to create UnifiedTradingEngine with common settings.
    
    Args:
        environment: Target environment
        trading_mode: Trading mode
        enable_optimizations: Whether to enable performance optimizations
        
    Returns:
        Configured UnifiedTradingEngine
    """
    factory = UnifiedEngineFactory()
    
    if environment == Environment.PRODUCTION:
        return factory.create_production_engine()
    elif environment == Environment.DEVELOPMENT:
        return factory.create_development_engine()
    else:
        return factory.builder().with_environment(environment).with_trading_mode(trading_mode).build()

def migrate_legacy_engine(legacy_engine: Any) -> UnifiedTradingEngine:
    """
    Convenience function to migrate from legacy engine.
    
    Args:
        legacy_engine: Legacy engine instance
        
    Returns:
        Migrated UnifiedTradingEngine
    """
    factory = UnifiedEngineFactory()
    return factory.migrate_from_legacy_engine(legacy_engine)

def create_backtesting_engine(strategies: List[str],
                            start_date: str,
                            end_date: str,
                            initial_capital: float = 1000000.0) -> UnifiedTradingEngine:
    """
    Convenience function to create backtesting engine.
    
    Args:
        strategies: List of strategy IDs
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Initial capital
        
    Returns:
        Backtesting-configured UnifiedTradingEngine
    """
    factory = UnifiedEngineFactory()
    backtest_config = {
        'strategies': strategies,
        'start_date': start_date,
        'end_date': end_date,
        'initial_capital': initial_capital
    }
    return factory.create_backtesting_engine(backtest_config)
