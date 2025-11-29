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
- TA-Lib integration with automatic fallback

Author: StatArb_Gemini Core Engine
Version: 2.1.0 (Enhanced with TA-Lib integration)
"""

from .engine import (
    EnhancedTechnicalIndicators,
    IndicatorResult,
)

# TA-Lib wrapper with automatic fallback
from .talib_indicators import (
    TALIB_AVAILABLE,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_adx,
    calculate_stochastic,
    calculate_sma,
    calculate_ema,
    calculate_williams_r,
    calculate_obv,
    calculate_cci,
    get_available_indicators,
    check_talib_status,
)

# Import centralized configuration
try:
    from core_engine.config import IndicatorConfig
except ImportError:
    # Fallback for backward compatibility
    from .engine import EnhancedIndicatorConfig as IndicatorConfig

__all__ = [
    # Main engine
    'EnhancedTechnicalIndicators',
    'IndicatorResult',
    'IndicatorConfig',
    # TA-Lib wrapper functions
    'TALIB_AVAILABLE',
    'calculate_rsi',
    'calculate_macd',
    'calculate_bollinger_bands',
    'calculate_atr',
    'calculate_adx',
    'calculate_stochastic',
    'calculate_sma',
    'calculate_ema',
    'calculate_williams_r',
    'calculate_obv',
    'calculate_cci',
    'get_available_indicators',
    'check_talib_status',
]
