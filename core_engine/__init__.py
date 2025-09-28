"""
Core Engine - Institutional Trading System

A complete institutional-grade trading engine following the SystemOrchestrator
architecture with hierarchical control, central risk governance, and unified
execution capabilities.
"""

__version__ = "2.0.0"
__author__ = "StatArb_Gemini"

# Only import components that actually exist after migration
try:
    # System components (existing)
    from .system.hierarchical_orchestrator import HierarchicalSystemOrchestrator
    from .system.central_risk_manager import CentralRiskManager
    from .system.unified_execution_engine import UnifiedExecutionEngine
    
    # Data management (moved)
    from .data.manager import ClickHouseDataManager
    
    # Regime assessment (existing)
    from .regime.engine import EnhancedRegimeEngine
    
    # Processing pipeline (moved)
    from .processing.indicators.engine import EnhancedTechnicalIndicators
    from .processing.features.engineer import EnhancedFeatureEngineer
    from .processing.signals.generator import EnhancedSignalGenerator
    
    # Trading components (moved)
    from .trading.portfolio.manager import PortfolioManager
    
    # Configuration (new)
    from .config.system_config import SystemConfig
    from .config.component_config import DataConfig, RiskConfig, ProcessingConfig
    
    __all__ = [
        # System components
        'HierarchicalSystemOrchestrator',
        'CentralRiskManager', 
        'UnifiedExecutionEngine',
        
        # Data and processing
        'ClickHouseDataManager',
        'RegimeEngine',
        'EnhancedTechnicalIndicators',
        'FeatureEngineer',
        'SignalGenerator',
        
        # Trading
        'PortfolioManager',
        
        # Configuration
        'SystemConfig',
        'DataConfig',
        'RiskConfig', 
        'ProcessingConfig'
    ]
    
except ImportError as e:
    # Graceful fallback during migration
    print(f"Warning: Some components not available during migration: {e}")
    __all__ = []
