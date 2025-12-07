"""
Core Engine Processing Module
==============================

Professional data processing pipeline with orchestrator integration:
- Pipeline Orchestration: Unified data flow coordination (Rule 3)
- Technical Indicators: 42+ institutional-grade indicators
- Feature Engineering: ML-ready feature transformation
- Signal Generation: Multi-strategy signal generation with ML enhancement
- Signal Validation: Comprehensive signal validation engine
- Signal Combination: Advanced ensemble methods for signal aggregation

All components implement ISystemComponent and IRegimeAware interfaces.

Author: StatArb_Gemini Core Engine
Version: 2.0.0 (Enhanced with Pipeline Orchestrator - Phase 2 Complete)
"""

# Import pipeline orchestrator (Rule 3 - Unified Data Flow)
from .pipeline_orchestrator import ProcessingPipelineOrchestrator, EnrichedMarketData

# Import main processing components
from .indicators.engine import EnhancedTechnicalIndicators, IndicatorResult
from .features.engineer import EnhancedFeatureEngineer, FeatureConfig
from .signals.generator import (
    EnhancedSignalGenerator,
    TradingSignal,
    SignalType,
    SignalStrength,
    SignalConfig
)
from .signals.validators import SignalValidator, ValidationResult
from .signals.combiners import SignalCombiner, CombinationMethod

__all__ = [
    # Pipeline Orchestrator (Rule 3)
    'ProcessingPipelineOrchestrator',
    'EnrichedMarketData',

    # Indicators
    'EnhancedTechnicalIndicators',
    'IndicatorResult',

    # Features
    'EnhancedFeatureEngineer',
    'FeatureConfig',

    # Signals
    'EnhancedSignalGenerator',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    'SignalConfig',

    # Validation
    'SignalValidator',
    'ValidationResult',

    # Combination
    'SignalCombiner',
    'CombinationMethod',
]

