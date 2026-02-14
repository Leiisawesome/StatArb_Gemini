"""
Regime Detection Engine
=======================

Market regime detection and analysis for the StatArb_Gemini trading platform.

Call DAG (backtest path)::

    InstitutionalBacktestEngine
      └─ RegimeManager (BRICK #1)               ← coordinator
             ├─ RealTimeRegimeSensor (engine.py)  ← per-bar EWMA sensor
             ├─ RegimeDetector                    ← batch statistical detection
             ├─ MarketRegimeAnalyzer              ← cross-asset / macro analysis
             ├─ RegimeIndicatorEngine             ← indicator + transition signals
             ├─ RegimeTransitionManager           ← transition prediction
             ├─ RegimeAwarePortfolioManager       ← allocation metadata
             └─ RegimePerformanceAttributor       ← performance attribution

    SessionManagementMixin
      └─ RealTimeRegimeSensor (fresh per day)    ← intraday state isolation

Components
----------
RegimeManager       Coordinator and primary system brick.
RealTimeRegimeSensor  Low-latency per-bar signal processing (alias: EnhancedRegimeEngine).
RegimeDetector      Statistical regime detection (Markov, GMM, volatility, threshold).
MarketRegimeAnalyzer  Cross-asset and macro regime analysis.
RegimeTransitionManager  Regime transition prediction and rebalancing.
RegimeIndicatorEngine  Regime-specific technical indicators.
RegimeClassifier    ML-based regime classification (optional — imports sklearn).
"""

# ---------------------------------------------------------------------------
# Core components (always imported)
# ---------------------------------------------------------------------------
from .regime_manager import (
    RegimeManager,
    RegimeManagerStatus,
    AdaptationMode,
    RegimeAdaptation,
)
from .allocation import RegimeAwarePortfolioManager
from .attribution import RegimePerformanceAttributor

from .regime_detector import (
    RegimeDetector,
    RegimeType,
    RegimeDetection,
    DetectionMethod,
    ConfidenceLevel,
)

from .engine import RealTimeRegimeSensor, EnhancedRegimeEngine

from .regime_indicators import (
    RegimeIndicatorEngine,
    RegimeIndicator,
    IndicatorType,
    TransitionSignal,
    RegimeStrengthMeasure,
    SignalStrength,
)

from .market_regime_analyzer import (
    MarketRegimeAnalyzer,
    MacroRegime,
    MarketCycle,
    RiskEnvironment,
    AssetRegimeProfile,
    CrossAssetRegime,
)

from .regime_transition_manager import (
    RegimeTransitionManager,
    TransitionPhase,
    TransitionType,
    TransitionPrediction,
    RebalancingTrigger,
    RebalancingRecommendation,
    TransitionMonitoring,
)

# ---------------------------------------------------------------------------
# Optional / ML component (deferred import to avoid eager sklearn load)
# ---------------------------------------------------------------------------
def __getattr__(name):
    """Lazy-load RegimeClassifier and friends to avoid importing sklearn at
    package-init time (~34 MB).  Only loaded when explicitly accessed."""
    _classifier_names = {
        'RegimeClassifier', 'RegimeClassification',
        'MLModel', 'FeatureType', 'FeatureImportance', 'ModelPerformance',
    }
    if name in _classifier_names:
        from . import regime_classifier as _rc
        obj = getattr(_rc, name)
        globals()[name] = obj  # cache for subsequent access
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core Components
    'RegimeManager',
    'RegimeDetector',
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
    'RegimeAdaptation',

    # RegimeDetector Types
    'RegimeType',
    'RegimeDetection',
    'DetectionMethod',
    'ConfidenceLevel',

    # Engine (alias)

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
    'TransitionMonitoring',

    # ML Classifier (lazy-loaded)
    'RegimeClassifier',
    'RegimeClassification',
    'MLModel',
    'FeatureType',
    'FeatureImportance',
    'ModelPerformance',
]

