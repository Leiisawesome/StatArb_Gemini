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
    pass
    
    # Data management (moved)
    
    # Regime assessment (existing)
    
    # Processing pipeline (moved)
    
    # Trading components (moved)
    
    # Configuration (new)
    
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
