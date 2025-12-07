"""
Signal Generation Module
=========================

Multi-strategy signal generation engine with ML enhancement and orchestrator integration.

Features:
- Multi-strategy signal generation (mean reversion, momentum, volume)
- ML-enhanced signals with confidence scoring
- Regime-aware signal filtering and confidence adjustment
- Strategy-regime appropriateness matrix
- Comprehensive signal validation with rule engine
- Advanced ensemble methods for signal combination
- ISystemComponent lifecycle management

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Enhanced with orchestrator integration)
"""

from .generator import (
    EnhancedSignalGenerator,
    TradingSignal,
    SignalType,
    SignalStrength,
)

from .validators import (
    SignalValidator,
    ValidationResult,
    ValidationRule,
)

from .combiners import (
    SignalCombiner,
    CombinationMethod,
)

# Import centralized configuration
try:
    from core_engine.config import SignalConfig
except ImportError:
    # Fallback for backward compatibility
    from .generator import SignalConfig

__all__ = [
    # Generation
    'EnhancedSignalGenerator',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'SignalConfig',

    # Validation
    'SignalValidator',
    'ValidationResult',
    'ValidationRule',

    # Combination
    'SignalCombiner',
    'CombinationMethod',
]

