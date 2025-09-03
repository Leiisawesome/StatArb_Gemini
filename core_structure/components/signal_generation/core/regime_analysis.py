"""
Consolidated Regime Analysis Engine
==================================

Unified market regime detection combining:
- Regime detection and classification (from regime_detector.py)
- Regime filtering and validation (from regime_filter.py)
- Real-time regime monitoring
- Performance-optimized regime computation

This module consolidates regime functionality from:
- regime_detector.py (781 lines)
- regime_filter.py

Author: GitHub Copilot Architecture Simplification
Version: 4.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
from collections import defaultdict, deque

# Core infrastructure imports
try:
    from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager
    from core_structure.infrastructure.message_bus import MessageBus
    from core_structure.infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Scientific computing with graceful fallback
try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    from scipy import stats
    from scipy.optimize import minimize
    SKLEARN_AVAILABLE = True
    SCIPY_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    SCIPY_AVAILABLE = False

# HMM for advanced regime detection
try:
    import hmmlearn.hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class RegimeType(Enum):
    """Market regime classifications"""
    MEAN_REVERTING = "mean_reverting"
    TRENDING = "trending"  
    VOLATILE = "volatile"
    STABLE = "stable"
    CRISIS = "crisis"
    UNKNOWN = "unknown"

class RegimeConfidence(Enum):
    """Regime confidence levels"""
    VERY_HIGH = 4  # >90%
    HIGH = 3       # 75-90%
    MEDIUM = 2     # 50-75%
    LOW = 1        # 25-50%
    VERY_LOW = 0   # <25%

@dataclass
class RegimeConfig:
    """Configuration for regime detection"""
    # Model parameters
    n_regimes: int = 5
    lookback_window: int = 252
    min_observations: int = 60
    update_frequency: int = 20  # Update every N observations
    
    # Performance settings
    max_parallel_symbols: int = 8
    detection_timeout_ms: int = 50
    cache_ttl_seconds: int = 300
    
    # Feature engineering
    enable_volatility_features: bool = True
    enable_return_features: bool = True
    enable_volume_features: bool = True
    
    # Filtering
    min_confidence_threshold: float = 0.5
    regime_persistence_periods: int = 5
    enable_smoothing: bool = True

@dataclass
class RegimeState:
    """Current market regime state"""
    regime: RegimeType
    confidence: float
    confidence_level: RegimeConfidence
    probability_distribution: Dict[RegimeType, float]
    features: Dict[str, float]
    timestamp: datetime
    duration: int  # Number of periods in current regime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'regime': self.regime.value,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'probability_distribution': {k.value: v for k, v in self.probability_distribution.items()},
            'features': self.features,
            'timestamp': self.timestamp.isoformat(),
            'duration': self.duration
        }

class RegimeAnalysisEngine:
    """
    Consolidated Regime Analysis Engine
    
    Unified market regime detection combining classification,
    filtering, and real-time monitoring capabilities.
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        """Initialize regime analysis engine"""
        self.config = config or RegimeConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize models and state
        self._initialize_models()
        self._regime_history = {}  # symbol -> deque of regime states
        self._feature_cache = {}
        self._lock = threading.Lock()
        
        # Performance tracking
        self.performance_metrics = {
            'regimes_detected': 0,
            'avg_confidence': 0.0,
            'avg_detection_time': 0.0,
            'regime_transitions': 0,
            'last_update': datetime.now()
        }
        
        self.logger.info(f"RegimeAnalysisEngine initialized with {self.config.n_regimes} regimes, "
                        f"lookback={self.config.lookback_window}")
    
    def _initialize_models(self):
        """Initialize regime detection models"""
        self.models = {}
        
        # Gaussian Mixture Model for basic regime detection
        if SKLEARN_AVAILABLE:
            self.gmm_model = GaussianMixture(
                n_components=self.config.n_regimes,
                covariance_type='full',
                random_state=42
            )
            self.scaler = StandardScaler()
        else:
            self.gmm_model = None
            self.scaler = None
        
        # HMM model for advanced regime detection
        if HMM_AVAILABLE:
            self.hmm_model = hmmlearn.hmm.GaussianHMM(
                n_components=self.config.n_regimes,
                covariance_type='full',
                random_state=42
            )
        else:
            self.hmm_model = None
    
    def detect_regime(self, symbol: str, market_data: pd.DataFrame) -> Optional[RegimeState]:
        """
        Detect current market regime for a symbol
        
        Args:
            symbol: Trading symbol
            market_data: Historical market data
            
        Returns:
            Current regime state or None if detection fails
        """
        start_time = time.time()
        
        try:
            # Validate input data
            if not self._validate_market_data(market_data):
                return None
            
            # Extract regime features
            features = self._extract_regime_features(market_data)
            if not features:
                return None
            
            # Detect regime using available models
            regime_probabilities = self._classify_regime(features, market_data)
            
            # Determine best regime and confidence
            best_regime, confidence = self._select_best_regime(regime_probabilities)
            
            # Apply filtering and smoothing
            if self.config.enable_smoothing:
                best_regime, confidence = self._apply_regime_filtering(
                    symbol, best_regime, confidence
                )
            
            # Create regime state
            regime_state = RegimeState(
                regime=best_regime,
                confidence=confidence,
                confidence_level=self._get_confidence_level(confidence),
                probability_distribution=regime_probabilities,
                features=features,
                timestamp=datetime.now(),
                duration=self._get_regime_duration(symbol, best_regime)
            )
            
            # Update history
            self._update_regime_history(symbol, regime_state)
            
            # Update performance metrics
            self._update_performance_metrics(regime_state, time.time() - start_time)
            
            self.logger.debug(f"Detected regime for {symbol}: {best_regime.value} "
                            f"(confidence: {confidence:.3f})")
            
            return regime_state
            
        except Exception as e:
            self.logger.error(f"Error detecting regime for {symbol}: {e}")
            return None
    
    def _validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Validate market data for regime detection"""
        if market_data.empty:
            return False
        
        if len(market_data) < self.config.min_observations:
            self.logger.debug(f"Insufficient data: {len(market_data)} < {self.config.min_observations}")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            self.logger.warning("Missing required OHLCV columns")
            return False
        
        return True
    
    def _extract_regime_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract features for regime classification"""
        features = {}
        
        try:
            close = market_data['close']
            high = market_data['high']
            low = market_data['low']
            volume = market_data['volume']
            
            # Return-based features
            if self.config.enable_return_features:
                returns = close.pct_change().dropna()
                
                if len(returns) > 0:
                    # Basic return statistics
                    features['returns_mean'] = float(returns.mean())
                    features['returns_std'] = float(returns.std())
                    features['returns_skew'] = float(returns.skew()) if len(returns) >= 3 else 0.0
                    features['returns_kurtosis'] = float(returns.kurtosis()) if len(returns) >= 4 else 0.0
                    
                    # Recent vs historical returns
                    if len(returns) >= 20:
                        recent_mean = returns.tail(5).mean()
                        historical_mean = returns.head(-5).mean()
                        features['return_momentum'] = float(recent_mean - historical_mean)
                    
                    # Autocorrelation (mean reversion indicator)
                    if len(returns) > 1:
                        try:
                            autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
                            features['return_autocorr'] = float(autocorr) if not np.isnan(autocorr) else 0.0
                        except:
                            features['return_autocorr'] = 0.0
            
            # Volatility-based features
            if self.config.enable_volatility_features:
                returns = close.pct_change().dropna()
                
                if len(returns) >= 20:
                    # Rolling volatility
                    vol_short = returns.rolling(5).std()
                    vol_long = returns.rolling(20).std()
                    
                    features['volatility_short'] = float(vol_short.iloc[-1]) if not pd.isna(vol_short.iloc[-1]) else 0.0
                    features['volatility_long'] = float(vol_long.iloc[-1]) if not pd.isna(vol_long.iloc[-1]) else 0.0
                    features['volatility_ratio'] = float(vol_short.iloc[-1] / vol_long.iloc[-1]) if vol_long.iloc[-1] > 0 else 1.0
                    
                    # Volatility clustering
                    vol_changes = vol_short.pct_change().dropna()
                    if len(vol_changes) > 1:
                        try:
                            vol_autocorr = np.corrcoef(vol_changes[:-1], vol_changes[1:])[0, 1]
                            features['volatility_clustering'] = float(vol_autocorr) if not np.isnan(vol_autocorr) else 0.0
                        except:
                            features['volatility_clustering'] = 0.0
                
                # Price range volatility
                ranges = (high - low) / close
                if len(ranges) >= 10:
                    features['range_volatility'] = float(ranges.rolling(10).std().iloc[-1])
            
            # Volume-based features
            if self.config.enable_volume_features:
                if len(volume) >= 20:
                    vol_ma = volume.rolling(20).mean()
                    features['volume_ratio'] = float(volume.iloc[-1] / vol_ma.iloc[-1]) if vol_ma.iloc[-1] > 0 else 1.0
                    
                    # Volume trend
                    vol_trend = volume.rolling(5).mean() / volume.rolling(20).mean()
                    features['volume_trend'] = float(vol_trend.iloc[-1]) if not pd.isna(vol_trend.iloc[-1]) else 1.0
                    
                    # Price-volume correlation
                    if len(close) >= 20:
                        try:
                            pv_corr = close.rolling(20).corr(volume).iloc[-1]
                            features['price_volume_corr'] = float(pv_corr) if not pd.isna(pv_corr) else 0.0
                        except:
                            features['price_volume_corr'] = 0.0
            
            # Trend strength
            if len(close) >= 20:
                # Simple trend indicator
                trend_short = close.rolling(5).mean()
                trend_long = close.rolling(20).mean()
                features['trend_strength'] = float((trend_short.iloc[-1] - trend_long.iloc[-1]) / trend_long.iloc[-1]) if trend_long.iloc[-1] > 0 else 0.0
                
                # Trend consistency
                price_changes = close.diff()
                if len(price_changes) >= 10:
                    up_days = (price_changes > 0).rolling(10).sum()
                    features['trend_consistency'] = float(up_days.iloc[-1] / 10.0)
            
        except Exception as e:
            self.logger.warning(f"Error extracting regime features: {e}")
        
        return features
    
    def _classify_regime(self, features: Dict[str, float], 
                        market_data: pd.DataFrame) -> Dict[RegimeType, float]:
        """Classify regime using available models"""
        regime_probabilities = {regime: 0.0 for regime in RegimeType}
        
        try:
            # Convert features to array
            feature_values = np.array(list(features.values())).reshape(1, -1)
            
            # Use simple heuristic-based classification as fallback
            regime_probabilities = self._heuristic_regime_classification(features)
            
            # Use ML models if available
            if self.gmm_model and SKLEARN_AVAILABLE:
                try:
                    ml_probabilities = self._ml_regime_classification(feature_values)
                    # Combine heuristic and ML results
                    for i, regime in enumerate(RegimeType):
                        if i < len(ml_probabilities):
                            regime_probabilities[regime] = (
                                regime_probabilities[regime] * 0.6 + 
                                ml_probabilities[i] * 0.4
                            )
                except Exception as e:
                    self.logger.debug(f"ML classification failed: {e}")
            
        except Exception as e:
            self.logger.warning(f"Error in regime classification: {e}")
            # Fallback to unknown regime
            regime_probabilities[RegimeType.UNKNOWN] = 1.0
        
        return regime_probabilities
    
    def _heuristic_regime_classification(self, features: Dict[str, float]) -> Dict[RegimeType, float]:
        """Heuristic-based regime classification"""
        probabilities = {regime: 0.0 for regime in RegimeType}
        
        try:
            # Extract key features
            volatility_ratio = features.get('volatility_ratio', 1.0)
            return_autocorr = features.get('return_autocorr', 0.0)
            trend_strength = abs(features.get('trend_strength', 0.0))
            returns_std = features.get('returns_std', 0.0)
            volatility_clustering = features.get('volatility_clustering', 0.0)
            
            # Crisis regime: High volatility, high volatility clustering
            if returns_std > 0.03 and volatility_ratio > 2.0:
                probabilities[RegimeType.CRISIS] = min(0.9, 0.3 + returns_std * 10 + volatility_ratio * 0.2)
            
            # Volatile regime: High volatility but not crisis level
            elif returns_std > 0.02 or volatility_ratio > 1.5:
                probabilities[RegimeType.VOLATILE] = min(0.8, 0.4 + returns_std * 8 + volatility_ratio * 0.15)
            
            # Trending regime: Strong trend, low mean reversion
            elif trend_strength > 0.02 and return_autocorr < 0.1:
                probabilities[RegimeType.TRENDING] = min(0.8, 0.5 + trend_strength * 10)
            
            # Mean reverting regime: High autocorrelation
            elif return_autocorr < -0.1:
                probabilities[RegimeType.MEAN_REVERTING] = min(0.8, 0.4 + abs(return_autocorr) * 2)
            
            # Stable regime: Low volatility, weak trends
            elif returns_std < 0.015 and trend_strength < 0.01:
                probabilities[RegimeType.STABLE] = min(0.8, 0.6 - returns_std * 20)
            
            # Default to unknown if no clear classification
            else:
                probabilities[RegimeType.UNKNOWN] = 0.5
            
            # Normalize probabilities
            total_prob = sum(probabilities.values())
            if total_prob > 0:
                for regime in probabilities:
                    probabilities[regime] /= total_prob
            else:
                probabilities[RegimeType.UNKNOWN] = 1.0
            
        except Exception as e:
            self.logger.warning(f"Error in heuristic classification: {e}")
            probabilities[RegimeType.UNKNOWN] = 1.0
        
        return probabilities
    
    def _ml_regime_classification(self, features: np.ndarray) -> List[float]:
        """ML-based regime classification (placeholder for future implementation)"""
        # This would implement actual ML-based regime classification
        # For now, return uniform probabilities
        n_regimes = len(RegimeType) - 1  # Exclude UNKNOWN
        return [1.0 / n_regimes] * n_regimes
    
    def _select_best_regime(self, probabilities: Dict[RegimeType, float]) -> Tuple[RegimeType, float]:
        """Select regime with highest probability"""
        best_regime = max(probabilities, key=probabilities.get)
        confidence = probabilities[best_regime]
        
        # Apply minimum confidence threshold
        if confidence < self.config.min_confidence_threshold:
            return RegimeType.UNKNOWN, confidence
        
        return best_regime, confidence
    
    def _apply_regime_filtering(self, symbol: str, regime: RegimeType, 
                               confidence: float) -> Tuple[RegimeType, float]:
        """Apply temporal filtering to regime detection"""
        with self._lock:
            if symbol not in self._regime_history:
                return regime, confidence
            
            # Get recent regime history
            recent_regimes = list(self._regime_history[symbol])[-self.config.regime_persistence_periods:]
            
            if len(recent_regimes) == 0:
                return regime, confidence
            
            # Check for regime persistence
            recent_regime_types = [r.regime for r in recent_regimes]
            most_common = max(set(recent_regime_types), key=recent_regime_types.count)
            
            # If detected regime is different from recent consensus, require higher confidence
            if regime != most_common and confidence < 0.7:
                return most_common, confidence * 0.8  # Reduce confidence for regime change
            
            return regime, confidence
    
    def _get_confidence_level(self, confidence: float) -> RegimeConfidence:
        """Convert numeric confidence to confidence level"""
        if confidence >= 0.9:
            return RegimeConfidence.VERY_HIGH
        elif confidence >= 0.75:
            return RegimeConfidence.HIGH
        elif confidence >= 0.5:
            return RegimeConfidence.MEDIUM
        elif confidence >= 0.25:
            return RegimeConfidence.LOW
        else:
            return RegimeConfidence.VERY_LOW
    
    def _get_regime_duration(self, symbol: str, regime: RegimeType) -> int:
        """Get duration of current regime"""
        with self._lock:
            if symbol not in self._regime_history:
                return 1
            
            history = list(self._regime_history[symbol])
            if not history:
                return 1
            
            # Count consecutive periods in current regime
            duration = 1
            for state in reversed(history):
                if state.regime == regime:
                    duration += 1
                else:
                    break
            
            return duration
    
    def _update_regime_history(self, symbol: str, regime_state: RegimeState):
        """Update regime history for symbol"""
        with self._lock:
            if symbol not in self._regime_history:
                self._regime_history[symbol] = deque(maxlen=100)  # Keep last 100 states
            
            self._regime_history[symbol].append(regime_state)
    
    def _update_performance_metrics(self, regime_state: RegimeState, detection_time: float):
        """Update performance tracking metrics"""
        self.performance_metrics['regimes_detected'] += 1
        
        # Rolling average of confidence
        total_detections = self.performance_metrics['regimes_detected']
        old_avg_confidence = self.performance_metrics['avg_confidence']
        self.performance_metrics['avg_confidence'] = (
            (old_avg_confidence * (total_detections - 1) + regime_state.confidence) / total_detections
        )
        
        # Rolling average of detection time
        old_avg_time = self.performance_metrics['avg_detection_time']
        self.performance_metrics['avg_detection_time'] = (
            (old_avg_time * (total_detections - 1) + detection_time) / total_detections
        )
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def get_regime_history(self, symbol: str, limit: int = 50) -> List[RegimeState]:
        """Get regime history for symbol"""
        with self._lock:
            if symbol not in self._regime_history:
                return []
            
            return list(self._regime_history[symbol])[-limit:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.performance_metrics.copy()
    
    def reset_history(self, symbol: Optional[str] = None):
        """Reset regime history"""
        with self._lock:
            if symbol:
                if symbol in self._regime_history:
                    self._regime_history[symbol].clear()
            else:
                self._regime_history.clear()
        
        self.logger.info(f"Regime history reset for {'all symbols' if not symbol else symbol}")

# Backward compatibility aliases
RegimeDetector = RegimeAnalysisEngine
RegimeAwareFilter = RegimeAnalysisEngine

# For compatibility with canonical types
try:
    from core_structure.infrastructure.types.market_types import MarketRegime
    # Map our detailed RegimeType to canonical MarketRegime if needed
except ImportError:
    MarketRegime = RegimeType  # Fallback

__all__ = [
    'RegimeAnalysisEngine',
    'RegimeDetector',  # Backward compatibility
    'RegimeAwareFilter',  # Backward compatibility
    'RegimeState',
    'RegimeType',
    'RegimeConfidence',
    'RegimeConfig',
    'MarketRegime'  # Canonical compatibility
]
