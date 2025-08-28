"""
Core Signal Generation Components
================================

Core signal generation functionality including:
- signal_engine.py: Main signal generation engine
- feature_processor.py: Feature engineering and extraction  
- regime_analysis.py: Market regime detection and analysis

These components form the foundation of the consolidated
signal generation architecture.
"""

from .signal_engine import (
    UnifiedSignalEngine,
    TradingSignal,
    SignalConfig,
    SignalType,
    SignalStrength,
    SignalMetrics
)

from .feature_processor import (
    FeatureProcessor,
    FeatureConfig,
    FeatureSet,
    FeatureType,
    FeatureQuality
)

from .regime_analysis import (
    RegimeAnalysisEngine,
    RegimeState,
    RegimeType,
    RegimeConfidence,
    RegimeConfig
)

# Backward compatibility
SignalGenerator = UnifiedSignalEngine
FeatureEngine = FeatureProcessor
RegimeDetector = RegimeAnalysisEngine

__all__ = [
    'UnifiedSignalEngine',
    'TradingSignal',
    'SignalConfig',
    'SignalType',
    'SignalStrength',
    'SignalMetrics',
    'FeatureProcessor',
    'FeatureConfig',
    'FeatureSet',
    'FeatureType',
    'FeatureQuality',
    'RegimeAnalysisEngine',
    'RegimeState',
    'RegimeType',
    'RegimeConfidence',
    'RegimeConfig',
    'SignalGenerator',  # Backward compatibility
    'FeatureEngine',    # Backward compatibility
    'RegimeDetector'    # Backward compatibility
]
