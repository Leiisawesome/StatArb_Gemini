"""
Feature Engineering Module
===========================

Professional feature engineering pipeline with orchestrator integration.

Features:
- 7-stage feature creation pipeline
- Price-based, momentum, volatility, volume features
- Cross-sectional features across symbol universe
- Lag features and rolling statistics
- Regime-aware normalization and adaptation
- ISystemComponent lifecycle management
- Critical preservation of raw trading indicators

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Enhanced with orchestrator integration)
"""

from .engineer import EnhancedFeatureEngineer

# Import centralized configuration
try:
    from core_engine.config import FeatureConfig
except ImportError:
    # Fallback for backward compatibility
    from .engineer import FeatureConfig

__all__ = [
    'EnhancedFeatureEngineer',
    'FeatureConfig',
]

