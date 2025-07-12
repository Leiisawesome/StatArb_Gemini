"""
Enhanced Pair Backtester Models Package

This package contains advanced statistical models for pair trading:
- Kalman Filter for dynamic hedge ratio estimation
- HMM for regime detection
- Ensemble methods for trade filtering
- Signal Generator for comprehensive trading signals
"""

from .kalman_filter import KalmanHedgeRatioFilter, KalmanResult
from .hmm_regime import HMMRegimeDetector, HMMResult, RegimeState, create_hmm_detector
from .hmm_regime_optimized import OptimizedHMMRegimeDetector, create_optimized_hmm_detector
from .ensemble_filter import EnsembleTradeFilter, EnsembleResult, TradeSignal, create_ensemble_filter
from .ensemble_filter_simple import SimpleEnsembleFilter, create_simple_ensemble_filter
from .signal_generator import SignalGenerator, SignalConfig, TradingSignal, SignalType, RegimeType

__all__ = [
    'KalmanHedgeRatioFilter', 'KalmanResult',
    'HMMRegimeDetector', 'HMMResult', 'RegimeState', 'create_hmm_detector',
    'OptimizedHMMRegimeDetector', 'create_optimized_hmm_detector',
    'EnsembleTradeFilter', 'EnsembleResult', 'TradeSignal', 'create_ensemble_filter',
    'SimpleEnsembleFilter', 'create_simple_ensemble_filter',
    'SignalGenerator', 'SignalConfig', 'TradingSignal', 'SignalType', 'RegimeType'
] 