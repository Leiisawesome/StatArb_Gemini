"""
Technical Indicators Module
============================

Institutional-grade technical indicators engine with orchestrator integration.

Features:
- 42+ professional technical indicators
- Multi-timeframe analysis support
- Macro regime indicators (VIX, DXY, TNX, etc.)
- Regime-aware parameter adaptation
- ISystemComponent lifecycle management
- Health monitoring and performance tracking

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Enhanced with orchestrator integration)
"""

from .engine import (
    EnhancedTechnicalIndicators,
    IndicatorResult,
)

# Import centralized configuration
try:
    from core_engine.config import IndicatorConfig
except ImportError:
    # Fallback for backward compatibility
    from .engine import EnhancedIndicatorConfig as IndicatorConfig

__all__ = [
    'EnhancedTechnicalIndicators',
    'IndicatorResult',
    'IndicatorConfig',
]

