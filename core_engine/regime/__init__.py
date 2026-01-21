"""
Regime Detection Engine
=======================

Central regime detection and analysis system for StatArb_Gemini trading platform.

This module provides comprehensive market regime detection, classification, and
analysis capabilities to enable regime-aware trading strategies and risk management.

Components:
-----------
- RegimeManager: [AUTHORITY] Central coordinator and primary system brick for regime analysis.
- RealTimeRegimeSensor: [SENSOR] Low-latency per-bar signal processing (formerly EnhancedRegimeEngine).
- RegimeDetector: Core regime detection using multiple methodologies.
- RegimeClassifier: ML-based regime classification with feature engineering.
- RegimeAwarePortfolioManager: Metadata-driven asset allocation by regime.
- RegimePerformanceAttributor: Specialized performance math for regime analysis.

- EnhancedRegimeEngine: [LEGACY ALIAS] Redirects to RealTimeRegimeSensor for backward compatibility.
- RegimeIndicatorEngine: Regime-specific technical indicators.
- MarketRegimeAnalyzer: Cross-asset and macro regime analysis.
- RegimeTransitionManager: Regime transition prediction and management

Type Definitions:
-----------------
- RegimeType: Market regime types (bull, bear, sideways, high_vol, etc.)
- RegimeState: Current regime state with metrics and implications
- RegimeContext: Comprehensive regime context for system-wide distribution
- RegimeDetection: Individual regime detection result
- RegimeClassification: ML-based regime classification result

Usage Example:
--------------
```python
from core_engine.regime import (
    RegimeManager,
    RegimeDetector,
    RegimeClassifier,
    RegimeType,
    RegimeConfig
)

# Initialize with centralized configuration
from core_engine.config import RegimeConfig

config = RegimeConfig(
    confidence_threshold=0.7,
    lookback_window=60,
    enable_ml_predictions=True
)

# Create regime manager
regime_manager = RegimeManager(config)

# Initialize for orchestrator integration (ISystemComponent)
await regime_manager.initialize()
await regime_manager.start()

# Perform regime analysis
regime_state = await regime_manager.update_regime_analysis(market_data)

# Access regime information
current_regime = regime_state.current_regime
confidence = regime_state.regime_confidence
implications = regime_state.portfolio_implications

# Generate strategy adaptations
adaptation = regime_manager.generate_regime_adaptation(
    regime_state,
    current_strategies
)
```

Architecture:
-------------
All components implement ISystemComponent for orchestrator integration:
- initialize() -> bool: Initialize the component
- start() -> bool: Start operations
- stop() -> bool: Stop operations
- health_check() -> Dict[str, Any]: Health monitoring
- get_status() -> Dict[str, Any]: Status reporting

All components use centralized RegimeConfig (Rule 1, Section 7):
- Single source of configuration truth
- Type-safe dataclass configuration
- Built-in validation
- Backward compatibility

Author: StatArb_Gemini Team
Version: 2.0.0
Status: Production Ready
Last Updated: October 21, 2025
"""

# Core Components
from .regime_manager import (
    RegimeManager,
    RegimeManagerStatus,
    AdaptationMode,
    RegimeAdaptation
)
from .allocation import RegimeAwarePortfolioManager
from .attribution import RegimePerformanceAttributor

from .regime_detector import (
    RegimeDetector,
    RegimeType,
    RegimeDetection,
    DetectionMethod,
    ConfidenceLevel
)

from .regime_classifier import (
    RegimeClassifier,
    RegimeClassification,
    MLModel,
    FeatureType,
    FeatureImportance,
    ModelPerformance
)

from .engine import RealTimeRegimeSensor, EnhancedRegimeEngine

from .regime_indicators import (
    RegimeIndicatorEngine,
    RegimeIndicator,
    IndicatorType,
    TransitionSignal,
    RegimeStrengthMeasure,
    SignalStrength
)

from .market_regime_analyzer import (
    MarketRegimeAnalyzer,
    MacroRegime,
    MarketCycle,
    RiskEnvironment,
    AssetRegimeProfile,
    CrossAssetRegime
)

from .regime_transition_manager import (
    RegimeTransitionManager,
    TransitionPhase,
    TransitionType,
    TransitionPrediction,
    RebalancingTrigger,
    RebalancingRecommendation,
    TransitionMonitoring
)

# Export all
__all__ = [
    # Core Components
    'RegimeManager',
    'RegimeDetector',
    'RegimeClassifier',
    'RealTimeRegimeSensor',
    'EnhancedRegimeEngine',
    'RegimeIndicatorEngine',
    'MarketRegimeAnalyzer',
    'RegimeTransitionManager',
    'RegimeAwarePortfolioManager',
    'RegimePerformanceAttributor',

    # RegimeManager Types
    'RegimeManagerStatus',
    'AdaptationMode',
    'MarketRegimeState',
    'RegimeState',
    'RegimeAdaptation',

    # RegimeDetector Types
    'RegimeType',
    'RegimeDetection',
    'DetectionMethod',
    'ConfidenceLevel',

    # RegimeClassifier Types
    'RegimeClassification',
    'MLModel',
    'FeatureType',
    'FeatureImportance',
    'ModelPerformance',

    # Engine Types

    # Indicator Types
    'RegimeIndicator',
    'IndicatorType',
    'TransitionSignal',
    'RegimeStrengthMeasure',
    'SignalStrength',

    # Analyzer Types
    'MacroRegime',
    'MarketCycle',
    'RiskEnvironment',
    'AssetRegimeProfile',
    'CrossAssetRegime',

    # Transition Manager Types
    'TransitionPhase',
    'TransitionType',
    'TransitionPrediction',
    'RebalancingTrigger',
    'RebalancingRecommendation',
    'TransitionMonitoring'
]

# Version information
__version__ = '2.0.0'
__author__ = 'StatArb_Gemini Team'
__status__ = 'Production'

