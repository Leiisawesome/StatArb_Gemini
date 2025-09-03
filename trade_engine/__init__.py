"""
Trade Engine - Professional Trading System
==========================================

MIGRATION NOTICE: This module now redirects to the UnifiedTradingEngine.
The UnifiedTradingEngine is the ultimate replacement for all previous engines.

For new code, import directly from core_structure:
    from core_structure import UnifiedTradingEngine, create_production_engine

For legacy compatibility, the old imports still work but redirect to unified engine.
"""

# ================================================================================
# UNIFIED ENGINE INTEGRATION
# ================================================================================

# Import the ultimate replacement
from core_structure import (
    UnifiedTradingEngine,
    UnifiedEngineFactory,
    create_production_engine,
    create_unified_engine,
    Environment,
    TradingMode
)

# ================================================================================
# LEGACY REDIRECTS (For Backwards Compatibility)
# ================================================================================

# Redirect legacy imports to unified engine
from core_structure.unified_engine.compatibility import (
    DelegatedCoreEngine,
    OptimizedCoreEngine,
    TwoLayerIntegrationAdapter
)

# ================================================================================
# PRODUCTION SHORTCUTS
# ================================================================================

def create_trade_engine(engine_type: str = "unified", **kwargs) -> UnifiedTradingEngine:
    """
    Create trading engine - now always returns UnifiedTradingEngine
    
    Args:
        engine_type: Ignored (for compatibility) - always creates unified engine
        **kwargs: Configuration parameters
        
    Returns:
        UnifiedTradingEngine configured for the specified use case
    """
    if engine_type == "production":
        return create_production_engine()
    else:
        return create_unified_engine(Environment.DEVELOPMENT, TradingMode.PAPER_TRADING)

# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    # PRIMARY ENGINE
    'UnifiedTradingEngine',
    'create_trade_engine',
    'create_production_engine',
    
    # LEGACY COMPATIBILITY  
    'DelegatedCoreEngine',
    'OptimizedCoreEngine',
    'TwoLayerIntegrationAdapter',
    
    # CONFIGURATION
    'Environment',
    'TradingMode'
]
