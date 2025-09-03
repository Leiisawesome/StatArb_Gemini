"""
Core Structure - Unified Trading Engine (Production)
===================================================

ULTIMATE REPLACEMENT: This module now exports UnifiedTradingEngine as the 
single, authoritative trading engine for the entire system.

The UnifiedTradingEngine replaces:
1. core_structure.compatibility_layer.UnifiedCoreEngineCompat (legacy compatibility)
2. trade_engine.core.delegated_core_engine.DelegatedCoreEngine (archived)  
3. trade_engine.optimization.optimized_core_engine.OptimizedCoreEngine (archived)

Author: Professional Trading System Architecture
Version: PRODUCTION (Reorganized Structure)
"""

# ================================================================================
# REORGANIZED IMPORTS - NEW STRUCTURE
# ================================================================================

# Core Unified Engine (from unified_engine/)
from .unified_engine import (
    UnifiedTradingEngine, 
    UnifiedEngineConfig, 
    UnifiedTradingResult,
    UnifiedEngineFactory,
    create_unified_engine,
    UnifiedEngineBuilder,
    create_backtesting_engine,
    migrate_legacy_engine,
    UnifiedConfigurationManager,
    UnifiedConfig,
    Environment,
    TradingMode,
    UnifiedStrategyRegistry,
    auto_discover_and_register_strategies,
    # Legacy Compatibility
    UnifiedCoreEngine,
    DelegatedCoreEngine,
    OptimizedCoreEngine,
    wrap_legacy_strategy,
    migrate_existing_system
)

# Strategy Interfaces (from interfaces/)
from .interfaces import (
    StrategyInterface, 
    BaseStrategy, 
    StrategyContext, 
    StrategyMetrics
)

# Core Components (from components/) - Available but not exported by default
# These can be imported directly from components if needed:
# from .components import ExecutionEngine, PortfolioManager, etc.

# Optimization Features (from optimization/) - Available but not exported by default  
# These can be imported directly from optimization if needed:
# from .optimization import optimize_signal_generation, etc.

# ================================================================================
# PRODUCTION CONVENIENCE FUNCTIONS (Updated for new structure)
# ================================================================================

def replace_legacy_engines(*legacy_engines) -> UnifiedTradingEngine:
    """
    MIGRATION SHORTCUT: Replace any number of legacy engines with single unified engine
    
    Args:
        *legacy_engines: Any legacy engine instances
        
    Returns:
        Single UnifiedTradingEngine replacing all legacy engines
    """
    return migrate_existing_system(list(legacy_engines))

# ================================================================================
# PRODUCTION READY DEFAULTS
# ================================================================================

# Default production engine instance (lazy-loaded)
_production_engine = None

def get_production_engine() -> UnifiedTradingEngine:
    """
    Get singleton production engine instance.
    Creates on first call, returns same instance on subsequent calls.
    """
    global _production_engine
    if _production_engine is None:
        _production_engine = create_unified_engine(Environment.PRODUCTION, TradingMode.LIVE_TRADING)
    return _production_engine

def create_production_engine(strategies: list = None, config_path: str = None) -> UnifiedTradingEngine:
    """
    PRODUCTION SHORTCUT: Create production-ready UnifiedTradingEngine
    
    This is the simplest way to get a production engine running.
    
    Args:
        strategies: List of strategy IDs to register
        config_path: Path to configuration file
        
    Returns:
        Production-ready UnifiedTradingEngine with all optimizations enabled
    """
    return create_unified_engine(Environment.PRODUCTION, TradingMode.LIVE_TRADING)

# ================================================================================
# EXPORTS FOR PRODUCTION SYSTEM
# ================================================================================

__all__ = [
    # PRIMARY ENGINE (THE REPLACEMENT)
    'UnifiedTradingEngine',
    'UnifiedEngineConfig', 
    'UnifiedTradingResult',
    
    # FACTORY AND CREATION
    'UnifiedEngineFactory',
    'create_unified_engine',
    'create_production_engine',
    'create_backtesting_engine',
    
    # CONFIGURATION
    'UnifiedConfigurationManager',
    'UnifiedConfig',
    'Environment',
    'TradingMode',
    
    # STRATEGY MANAGEMENT
    'UnifiedStrategyRegistry',
    'StrategyInterface',
    'BaseStrategy',
    'StrategyContext',
    
    # LEGACY COMPATIBILITY
    'UnifiedCoreEngine',        # Compatibility wrapper
    'DelegatedCoreEngine',      # Compatibility wrapper  
    'OptimizedCoreEngine',      # Compatibility wrapper
    'wrap_legacy_strategy',
    'migrate_legacy_engine',
    'replace_legacy_engines',
    
    # PRODUCTION SHORTCUTS
    'get_production_engine'
]