"""
Unified Trading Engine - Core Module
===================================

This module contains the core UnifiedTradingEngine and all related components.
The UnifiedTradingEngine is the single, authoritative trading engine for the entire system.

Components:
- engine.py: Main UnifiedTradingEngine implementation
- factory.py: Engine factory and builder patterns
- configuration.py: Unified configuration management
- strategy_registry.py: Strategy registration and management
- compatibility.py: Legacy compatibility layer

Author: Professional Trading System Architecture
Version: PRODUCTION (Reorganized)
"""

# Core Engine
from .engine import UnifiedTradingEngine, UnifiedEngineConfig, UnifiedTradingResult, TradingMode, EngineStatus

# Factory and Builder
from .factory import (
    UnifiedEngineFactory, 
    UnifiedEngineBuilder,
    create_unified_engine, 
    create_backtesting_engine,
    migrate_legacy_engine
)

# Configuration
from .configuration import (
    UnifiedConfigurationManager, 
    UnifiedConfig, 
    Environment, 
    TradingMode
)

# Strategy Management
from .strategy_registry import (
    UnifiedStrategyRegistry,
    auto_discover_and_register_strategies
)

# Legacy Compatibility
from .compatibility import (
    UnifiedCoreEngine,
    DelegatedCoreEngine,
    OptimizedCoreEngine,
    wrap_legacy_strategy,
    migrate_existing_system
)

__all__ = [
    # Core Engine
    'UnifiedTradingEngine',
    'UnifiedEngineConfig', 
    'UnifiedTradingResult',
    'TradingMode',
    'EngineStatus',
    
    # Factory
    'UnifiedEngineFactory',
    'UnifiedEngineBuilder',
    'create_unified_engine', 
    'create_backtesting_engine',
    'migrate_legacy_engine',
    
    # Configuration
    'UnifiedConfigurationManager',
    'UnifiedConfig',
    'Environment',
    
    # Strategy Management
    'UnifiedStrategyRegistry',
    'auto_discover_and_register_strategies',
    
    # Legacy Compatibility
    'UnifiedCoreEngine',
    'DelegatedCoreEngine', 
    'OptimizedCoreEngine',
    'wrap_legacy_strategy',
    'migrate_existing_system'
]
