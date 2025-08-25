#!/usr/bin/env python3
"""
Regime Detector - ML-Powered Market Regime Identification
=========================================================

Advanced market regime detection system using Hidden Markov Models, clustering,
and change point detection for market condition identification and strategy adaptation.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import warnings
warnings.filterwarnings('ignore')

# ML and statistical libraries
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from scipy import stats
from scipy.signal import argrelextrema
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional dependencies - install with: pip install ruptures hmmlearn
try:
    import ruptures as rpt  # Change point detection
    HAS_RUPTURES = True
except ImportError:
    HAS_RUPTURES = False
    logger.warning("ruptures not available - change point detection disabled")

try:
    from hmmlearn import hmm  # Hidden Markov Models
    HAS_HMMLEARN = True
except ImportError:
    HAS_HMMLEARN = False
    logger.warning("hmmlearn not available - HMM regime detection disabled")

class MarketRegime(Enum):
    """Market regime classifications"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"

class VolatilityRegime(Enum):
    """Volatility regime classifications"""
    LOW_VOL = "low_volatility"
    MEDIUM_VOL = "medium_volatility"
    HIGH_VOL = "high_volatility"
    EXTREME_VOL = "extreme_volatility"

class CorrelationRegime(Enum):
    """Correlation regime classifications"""
    LOW_CORRELATION = "low_correlation"
    MEDIUM_CORRELATION = "medium_correlation"
    HIGH_CORRELATION = "high_correlation"
    EXTREME_CORRELATION = "extreme_correlation"

class TrendRegime(Enum):
    """Trend regime classifications"""
    STRONG_UPTREND = "strong_uptrend"
    WEAK_UPTREND = "weak_uptrend"
    SIDEWAYS = "sideways"
    WEAK_DOWNTREND = "weak_downtrend"
    STRONG_DOWNTREND = "strong_downtrend"

@dataclass
class RegimeState:
    """Market regime state"""
    timestamp: datetime
    regime_type: MarketRegime
    confidence: float  # 0-1
    duration: int  # Days in current regime
    transition_probability: float  # Probability of regime change
    
    # Regime characteristics
    volatility_regime: VolatilityRegime
    correlation_regime: CorrelationRegime
    trend_regime: TrendRegime
    
    # Statistical features
    mean_return: float
    volatility: float
    skewness: float
    kurtosis: float
    max_drawdown: float
    
    # Regime metadata
    regime_strength: float = 0.0  # How strong/clear the regime is
    stability: float = 0.0  # How stable the regime is

@dataclass
class RegimeTransition:
    """Regime transition event"""
    transition_time: datetime
    from_regime: MarketRegime
    to_regime: MarketRegime
    transition_probability: float
    confidence: float
    
    # Transition characteristics
    transition_speed: str  # "gradual", "moderate", "sudden"
    warning_signals: List[str]
    impact_magnitude: float
    
    # Context
    trigger_events: List[str] = field(default_factory=list)
    market_conditions: Dict[str, float] = field(default_factory=dict)

@dataclass
class RegimeForecast:
    """Regime forecast prediction"""
    forecast_horizon: int  # Days
    predicted_regime: MarketRegime
    regime_probabilities: Dict[MarketRegime, float]
    confidence: float
    expected_duration: int  # Days
    
    # Forecast features
    transition_signals: List[str]
    risk_factors: Dict[str, float]
    recommended_adaptations: List[str]

@dataclass
class StrategyAdaptation:
    """Strategy adaptation recommendation"""
    strategy_id: str
    current_regime: MarketRegime
    recommended_parameters: Dict[str, float]
    parameter_changes: Dict[str, Tuple[float, float]]  # (old, new)
    adaptation_reason: str
    expected_improvement: float
    
    # Implementation details
    urgency: str  # "low", "medium", "high"
    risk_impact: str  # "positive", "neutral", "negative"
    implementation_cost: float

class RegimeDetector:
    """
    ML-powered market regime detection system
    
    Features:
    - Hidden Markov Model regime detection
    - K-means clustering for regime identification
    - Change point detection for regime transitions
    - Volatility regime monitoring
    - Correlation regime analysis
    - Strategy adaptation recommendations
    """
    
    def __init__(self,
                 lookback_window: int = 252,  # 1 year
                 min_regime_duration: int = 5,  # Minimum days
                 n_regimes: int = 5,
                 update_frequency: int = 1,  # Daily updates
                 confidence_threshold: float = 0.7):
        
        self.lookback_window = lookback_window
        self.min_regime_duration = min_regime_duration
        self.n_regimes = n_regimes
        self.update_frequency = update_frequency
        self.confidence_threshold = confidence_threshold
        
        # ML models (with optional dependency handling)
        if HAS_HMMLEARN:
            self.hmm_model = hmm.GaussianHMM(n_components=n_regimes, random_state=42)
        else:
            self.hmm_model = None
            
        self.kmeans_model = KMeans(n_clusters=n_regimes, random_state=42)
        self.gmm_model = GaussianMixture(n_components=n_regimes, random_state=42)
        self.rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        # Change point detection (with optional dependency)
        if HAS_RUPTURES:
            self.change_detector = rpt.Pelt(model="rbf", min_size=self.min_regime_duration)
        else:
            self.change_detector = None
        
        # Data storage
        self.market_data: List[Dict[str, Any]] = []
        self.regime_history: List[RegimeState] = []
        self.transition_history: List[RegimeTransition] = []
        self.forecast_history: List[RegimeForecast] = []
        
        # Current state
        self.current_regime: Optional[RegimeState] = None
        self.regime_model_trained = False
        
        # Regime definitions
        self.regime_characteristics = self._initialize_regime_characteristics()
        
        # State management
        self.is_detecting = False
        self.lock = Lock()
        
        logger.info("RegimeDetector initialized with HMM and clustering models")
    
    def _initialize_regime_characteristics(self) -> Dict[MarketRegime, Dict[str, Any]]:
        """Initialize regime characteristics for classification"""
        return {
            MarketRegime.BULL_MARKET: {
                'mean_return_range': (0.0005, 0.003),  # 0.05-0.3% daily
                'volatility_range': (0.005, 0.02),     # 0.5-2% daily
                'trend_strength': 0.7,
                'correlation_level': 'medium'
            },
            MarketRegime.BEAR_MARKET: {
                'mean_return_range': (-0.003, -0.0005),  # -0.3 to -0.05% daily
                'volatility_range': (0.01, 0.05),        # 1-5% daily
                'trend_strength': -0.7,
                'correlation_level': 'high'
            },
            MarketRegime.SIDEWAYS_MARKET: {
                'mean_return_range': (-0.0005, 0.0005),  # -0.05 to 0.05% daily
                'volatility_range': (0.005, 0.015),      # 0.5-1.5% daily
                'trend_strength': 0.1,
                'correlation_level': 'medium'
            },
            MarketRegime.HIGH_VOLATILITY: {
                'volatility_range': (0.03, 0.1),         # 3-10% daily
                'correlation_level': 'high'
            },
            MarketRegime.CRISIS: {
                'mean_return_range': (-0.05, -0.01),     # -5 to -1% daily
                'volatility_range': (0.05, 0.2),         # 5-20% daily
                'correlation_level': 'extreme'
            }
        }
    
    async def start_detection(self) -> None:
        """Start regime detection"""
        with self.lock:
            if self.is_detecting:
                logger.warning("Regime detection already running")
                return
            
            self.is_detecting = True
            logger.info("Starting ML-powered regime detection")
    
    async def stop_detection(self) -> None:
        """Stop regime detection"""
        with self.lock:
            self.is_detecting = False
            logger.info("Regime detection stopped")
    
    def add_market_data(self, timestamp: datetime, market_metrics: Dict[str, float]) -> None:
        """Add market data for regime detection"""
        with self.lock:
            # Calculate additional features
            enhanced_metrics = market_metrics.copy()
            
            # Add derived features if we have history
            if len(self.market_data) > 0:
                prev_data = self.market_data[-1]
                
                # Returns
                if 'price' in market_metrics and 'price' in prev_data:
                    enhanced_metrics['return'] = (market_metrics['price'] - prev_data['price']) / prev_data['price']
                
                # Volatility (if we have enough history)
                if len(self.market_data) >= 20:
                    recent_returns = [d.get('return', 0) for d in self.market_data[-20:]]
                    enhanced_metrics['rolling_volatility'] = float(np.std(recent_returns))
                
                # Correlation (simplified - would need multiple assets)
                enhanced_metrics['correlation_proxy'] = market_metrics.get('volatility', 0.01)
            
            self.market_data.append({
                'timestamp': timestamp,
                **enhanced_metrics
            })
            
            # Maintain rolling window
            if len(self.market_data) > self.lookback_window:
                self.market_data = self.market_data[-self.lookback_window:]
    
    async def detect_current_regime(self) -> Optional[RegimeState]:
        """Detect current market regime using multiple methods"""
        if len(self.market_data) < 30:
            logger.warning("Insufficient data for regime detection")
            return None
        
        try:
            # Prepare features
            features = self._prepare_regime_features()
            if features is None:
                return None
            
            # Train models if needed
            if not self.regime_model_trained or len(self.regime_history) == 0:
                await self._train_regime_models(features)
            
            # Get current features
            current_features = features[-1:] if len(features) > 0 else None
            if current_features is None:
                return None
            
            # Ensemble regime detection
            regime_predictions = []
            confidences = []
            
            # 1. Hidden Markov Model
            hmm_regime, hmm_confidence = self._detect_regime_hmm(features)
            if hmm_regime:
                regime_predictions.append(hmm_regime)
                confidences.append(hmm_confidence)
            
            # 2. K-means clustering
            kmeans_regime, kmeans_confidence = self._detect_regime_kmeans(current_features)
            if kmeans_regime:
                regime_predictions.append(kmeans_regime)
                confidences.append(kmeans_confidence)
            
            # 3. Gaussian Mixture Model
            gmm_regime, gmm_confidence = self._detect_regime_gmm(current_features)
            if gmm_regime:
                regime_predictions.append(gmm_regime)
                confidences.append(gmm_confidence)
            
            # 4. Random Forest (if we have labeled data)
            if len(self.regime_history) > 50:
                rf_regime, rf_confidence = self._detect_regime_rf(current_features)
                if rf_regime:
                    regime_predictions.append(rf_regime)
                    confidences.append(rf_confidence)
            
            # Ensemble decision
            if not regime_predictions:
                return None
            
            # Weighted voting
            regime_votes = {}
            for regime, confidence in zip(regime_predictions, confidences):
                if regime not in regime_votes:
                    regime_votes[regime] = 0
                regime_votes[regime] += confidence
            
            # Select regime with highest weighted vote
            best_regime = max(regime_votes.items(), key=lambda x: x[1])
            predicted_regime = best_regime[0]
            ensemble_confidence = best_regime[1] / len(regime_predictions)
            
            # Calculate regime duration
            duration = self._calculate_regime_duration(predicted_regime)
            
            # Detect sub-regimes
            volatility_regime = self._detect_volatility_regime()
            correlation_regime = self._detect_correlation_regime()
            trend_regime = self._detect_trend_regime()
            
            # Calculate regime characteristics
            recent_data = self.market_data[-30:]  # Last 30 days
            returns = [d.get('return', 0) for d in recent_data if 'return' in d]
            
            mean_return = float(np.mean(returns)) if returns else 0.0
            volatility = float(np.std(returns)) if returns else 0.0
            skewness = float(stats.skew(returns)) if len(returns) > 3 else 0.0
            kurtosis = float(stats.kurtosis(returns)) if len(returns) > 3 else 0.0
            
            # Calculate drawdown
            prices = [d.get('price', 100) for d in recent_data if 'price' in d]
            max_drawdown = self._calculate_max_drawdown(prices) if prices else 0.0
            
            # Transition probability
            transition_prob = self._calculate_transition_probability(predicted_regime)
            
            # Create regime state
            regime_state = RegimeState(
                timestamp=datetime.now(),
                regime_type=predicted_regime,
                confidence=float(ensemble_confidence),
                duration=duration,
                transition_probability=transition_prob,
                volatility_regime=volatility_regime,
                correlation_regime=correlation_regime,
                trend_regime=trend_regime,
                mean_return=mean_return,
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                max_drawdown=max_drawdown,
                regime_strength=self._calculate_regime_strength(predicted_regime),
                stability=self._calculate_regime_stability()
            )
            
            # Check for regime transition
            if self.current_regime and self.current_regime.regime_type != predicted_regime:
                await self._record_regime_transition(self.current_regime, regime_state)
            
            # Update current regime
            self.current_regime = regime_state
            
            # Store in history
            with self.lock:
                self.regime_history.append(regime_state)
                if len(self.regime_history) > 1000:
                    self.regime_history = self.regime_history[-1000:]
            
            logger.info(f"Detected regime: {predicted_regime.value} (confidence: {ensemble_confidence:.3f})")
            return regime_state
            
        except Exception as e:
            logger.error(f"Error detecting current regime: {e}")
            return None
    
    async def forecast_regime_transition(self, horizon_days: int = 30) -> Optional[RegimeForecast]:
        """Forecast potential regime transitions"""
        if len(self.regime_history) < 50:
            logger.warning("Insufficient regime history for forecasting")
            return None
        
        try:
            # Analyze historical transition patterns
            transition_patterns = self._analyze_transition_patterns()
            
            # Calculate regime probabilities for forecast horizon
            current_regime = self.current_regime.regime_type if self.current_regime else MarketRegime.SIDEWAYS_MARKET
            
            # Build transition matrix
            transition_matrix = self._build_transition_matrix()
            
            # Multi-step forecast
            regime_probs = self._forecast_regime_probabilities(
                current_regime, horizon_days, transition_matrix
            )
            
            # Most likely regime
            predicted_regime = max(regime_probs.items(), key=lambda x: x[1])[0]
            confidence = regime_probs[predicted_regime]
            
            # Expected duration
            expected_duration = self._estimate_regime_duration(predicted_regime)
            
            # Identify transition signals
            transition_signals = self._identify_transition_signals()
            
            # Risk factors
            risk_factors = self._analyze_regime_risk_factors(predicted_regime)
            
            # Strategy adaptations
            adaptations = self._recommend_regime_adaptations(predicted_regime)
            
            forecast = RegimeForecast(
                forecast_horizon=horizon_days,
                predicted_regime=predicted_regime,
                regime_probabilities=regime_probs,
                confidence=confidence,
                expected_duration=expected_duration,
                transition_signals=transition_signals,
                risk_factors=risk_factors,
                recommended_adaptations=adaptations
            )
            
            # Store forecast
            with self.lock:
                self.forecast_history.append(forecast)
                if len(self.forecast_history) > 100:
                    self.forecast_history = self.forecast_history[-100:]
            
            logger.info(f"Forecasted regime: {predicted_regime.value} (confidence: {confidence:.3f})")
            return forecast
            
        except Exception as e:
            logger.error(f"Error forecasting regime transition: {e}")
            return None
    
    async def recommend_strategy_adaptations(self, strategies: List[str]) -> List[StrategyAdaptation]:
        """Recommend strategy adaptations based on current regime"""
        if not self.current_regime:
            return []
        
        try:
            adaptations = []
            current_regime = self.current_regime.regime_type
            
            for strategy_id in strategies:
                adaptation = self._generate_strategy_adaptation(strategy_id, current_regime)
                if adaptation:
                    adaptations.append(adaptation)
            
            logger.info(f"Generated {len(adaptations)} strategy adaptations for regime {current_regime.value}")
            return adaptations
            
        except Exception as e:
            logger.error(f"Error recommending strategy adaptations: {e}")
            return []
    
    def _prepare_regime_features(self) -> Optional[np.ndarray]:
        """Prepare features for regime detection"""
        if len(self.market_data) < 20:
            return None
        
        try:
            features = []
            
            # Rolling windows for feature calculation
            windows = [5, 10, 20]
            
            for i in range(20, len(self.market_data)):
                feature_vector = []
                
                # Get recent data window
                window_data = self.market_data[max(0, i-20):i]
                
                # Basic features
                returns = [d.get('return', 0) for d in window_data if 'return' in d]
                volatilities = [d.get('volatility', 0.01) for d in window_data]
                volumes = [d.get('volume', 1000000) for d in window_data if 'volume' in d]
                
                if not returns:
                    continue
                
                # Return statistics
                feature_vector.extend([
                    np.mean(returns),
                    np.std(returns),
                    stats.skew(returns) if len(returns) > 3 else 0,
                    stats.kurtosis(returns) if len(returns) > 3 else 0
                ])
                
                # Volatility statistics
                feature_vector.extend([
                    np.mean(volatilities),
                    np.std(volatilities),
                    np.max(volatilities),
                    np.min(volatilities)
                ])
                
                # Trend features
                if len(returns) >= 10:
                    # Linear trend
                    x = np.arange(len(returns))
                    slope, _, r_value, _, _ = stats.linregress(x, returns)
                    feature_vector.extend([slope, r_value**2])
                else:
                    feature_vector.extend([0, 0])
                
                # Momentum features
                for window in windows:
                    if len(returns) >= window:
                        momentum = np.sum(returns[-window:])
                        feature_vector.append(momentum)
                    else:
                        feature_vector.append(0)
                
                # Volatility momentum
                if len(volatilities) >= 10:
                    vol_momentum = np.mean(volatilities[-5:]) - np.mean(volatilities[-10:-5])
                    feature_vector.append(vol_momentum)
                else:
                    feature_vector.append(0)
                
                # Volume features (if available)
                if volumes:
                    feature_vector.extend([
                        np.mean(volumes),
                        np.std(volumes)
                    ])
                else:
                    feature_vector.extend([1000000, 100000])  # Defaults
                
                features.append(feature_vector)
            
            if not features:
                return None
            
            # Convert to numpy array and handle NaN values
            features_array = np.array(features)
            features_array = np.nan_to_num(features_array, nan=0.0, posinf=0.0, neginf=0.0)
            
            return features_array
            
        except Exception as e:
            logger.error(f"Error preparing regime features: {e}")
            return None
    
    async def _train_regime_models(self, features: np.ndarray) -> None:
        """Train regime detection models"""
        try:
            if len(features) < 50:
                logger.warning("Insufficient data for regime model training")
                return
            
            # Scale features
            scaled_features = self.scaler.fit_transform(features)
            
            # Train Hidden Markov Model
            if HAS_HMMLEARN and self.hmm_model is not None:
                try:
                    self.hmm_model.fit(scaled_features)
                    logger.info("HMM model trained successfully")
                except Exception as e:
                    logger.warning(f"HMM training failed: {e}")
            else:
                logger.info("HMM training skipped - hmmlearn not available")
            
            # Train K-means clustering
            try:
                self.kmeans_model.fit(scaled_features)
                logger.info("K-means model trained successfully")
            except Exception as e:
                logger.warning(f"K-means training failed: {e}")
            
            # Train Gaussian Mixture Model
            try:
                self.gmm_model.fit(scaled_features)
                logger.info("GMM model trained successfully")
            except Exception as e:
                logger.warning(f"GMM training failed: {e}")
            
            # Train Random Forest (if we have regime labels)
            if len(self.regime_history) > 20:
                try:
                    # Create labels from regime history
                    labels = self._create_regime_labels(features)
                    if labels is not None and len(labels) == len(scaled_features):
                        self.rf_classifier.fit(scaled_features, labels)
                        logger.info("Random Forest classifier trained successfully")
                except Exception as e:
                    logger.warning(f"Random Forest training failed: {e}")
            
            self.regime_model_trained = True
            logger.info("Regime models training completed")
            
        except Exception as e:
            logger.error(f"Error training regime models: {e}")
    
    def _detect_regime_hmm(self, features: np.ndarray) -> Tuple[Optional[MarketRegime], float]:
        """Detect regime using Hidden Markov Model"""
        try:
            if not HAS_HMMLEARN or self.hmm_model is None:
                return None, 0.0
                
            if not hasattr(self.hmm_model, 'means_'):
                return None, 0.0
            
            scaled_features = self.scaler.transform(features)
            
            # Predict hidden states
            hidden_states = self.hmm_model.predict(scaled_features)
            current_state = hidden_states[-1]
            
            # Get state probabilities
            log_probs = self.hmm_model.predict_proba(scaled_features)
            current_prob = log_probs[-1, current_state]
            
            # Map state to regime
            regime = self._map_state_to_regime(current_state, scaled_features[-1])
            
            return regime, float(current_prob)
            
        except Exception as e:
            logger.error(f"Error in HMM regime detection: {e}")
            return None, 0.0
    
    def _detect_regime_kmeans(self, features: np.ndarray) -> Tuple[Optional[MarketRegime], float]:
        """Detect regime using K-means clustering"""
        try:
            if not hasattr(self.kmeans_model, 'cluster_centers_'):
                return None, 0.0
            
            scaled_features = self.scaler.transform(features)
            
            # Predict cluster
            cluster = self.kmeans_model.predict(scaled_features)[0]
            
            # Calculate distance to cluster center
            distances = self.kmeans_model.transform(scaled_features)[0]
            confidence = 1.0 / (1.0 + distances[cluster])  # Inverse distance
            
            # Map cluster to regime
            regime = self._map_cluster_to_regime(cluster, scaled_features[0])
            
            return regime, float(confidence)
            
        except Exception as e:
            logger.error(f"Error in K-means regime detection: {e}")
            return None, 0.0
    
    def _detect_regime_gmm(self, features: np.ndarray) -> Tuple[Optional[MarketRegime], float]:
        """Detect regime using Gaussian Mixture Model"""
        try:
            if not hasattr(self.gmm_model, 'means_'):
                return None, 0.0
            
            scaled_features = self.scaler.transform(features)
            
            # Predict component and probability
            component = self.gmm_model.predict(scaled_features)[0]
            probabilities = self.gmm_model.predict_proba(scaled_features)[0]
            confidence = probabilities[component]
            
            # Map component to regime
            regime = self._map_component_to_regime(component, scaled_features[0])
            
            return regime, float(confidence)
            
        except Exception as e:
            logger.error(f"Error in GMM regime detection: {e}")
            return None, 0.0
    
    def _detect_regime_rf(self, features: np.ndarray) -> Tuple[Optional[MarketRegime], float]:
        """Detect regime using Random Forest"""
        try:
            if not hasattr(self.rf_classifier, 'classes_'):
                return None, 0.0
            
            scaled_features = self.scaler.transform(features)
            
            # Predict regime
            prediction = self.rf_classifier.predict(scaled_features)[0]
            probabilities = self.rf_classifier.predict_proba(scaled_features)[0]
            confidence = np.max(probabilities)
            
            # Convert prediction to MarketRegime
            regime = MarketRegime(prediction) if prediction in [r.value for r in MarketRegime] else MarketRegime.SIDEWAYS_MARKET
            
            return regime, float(confidence)
            
        except Exception as e:
            logger.error(f"Error in Random Forest regime detection: {e}")
            return None, 0.0
    
    def _map_state_to_regime(self, state: int, features: np.ndarray) -> MarketRegime:
        """Map HMM state to market regime based on features"""
        # Simplified mapping based on feature characteristics
        if len(features) < 4:
            return MarketRegime.SIDEWAYS_MARKET
        
        mean_return = features[0]
        volatility = features[1]
        
        # Simple heuristic mapping
        if volatility > 0.5:  # High volatility
            if mean_return < -0.5:
                return MarketRegime.CRISIS
            else:
                return MarketRegime.HIGH_VOLATILITY
        elif mean_return > 0.3:
            return MarketRegime.BULL_MARKET
        elif mean_return < -0.3:
            return MarketRegime.BEAR_MARKET
        else:
            return MarketRegime.SIDEWAYS_MARKET
    
    def _map_cluster_to_regime(self, cluster: int, features: np.ndarray) -> MarketRegime:
        """Map K-means cluster to market regime"""
        return self._map_state_to_regime(cluster, features)
    
    def _map_component_to_regime(self, component: int, features: np.ndarray) -> MarketRegime:
        """Map GMM component to market regime"""
        return self._map_state_to_regime(component, features)
    
    def _create_regime_labels(self, features: np.ndarray) -> Optional[np.ndarray]:
        """Create regime labels from historical data for supervised learning"""
        try:
            if len(self.regime_history) < 20:
                return None
            
            # Use most recent regime history to create labels
            labels = []
            
            # Align regime history with features
            min_length = min(len(features), len(self.regime_history))
            
            for i in range(min_length):
                regime = self.regime_history[-(min_length-i)].regime_type
                labels.append(regime.value)
            
            return np.array(labels) if labels else None
            
        except Exception as e:
            logger.error(f"Error creating regime labels: {e}")
            return None
    
    def _detect_volatility_regime(self) -> VolatilityRegime:
        """Detect current volatility regime"""
        if len(self.market_data) < 20:
            return VolatilityRegime.MEDIUM_VOL
        
        recent_data = self.market_data[-20:]
        volatilities = [d.get('volatility', 0.01) for d in recent_data]
        current_vol = np.mean(volatilities)
        
        # Volatility thresholds (simplified)
        if current_vol < 0.01:
            return VolatilityRegime.LOW_VOL
        elif current_vol < 0.02:
            return VolatilityRegime.MEDIUM_VOL
        elif current_vol < 0.05:
            return VolatilityRegime.HIGH_VOL
        else:
            return VolatilityRegime.EXTREME_VOL
    
    def _detect_correlation_regime(self) -> CorrelationRegime:
        """Detect current correlation regime"""
        # Simplified correlation regime (would need multiple assets)
        if len(self.market_data) < 20:
            return CorrelationRegime.MEDIUM_CORRELATION
        
        # Use volatility as proxy for correlation regime
        recent_data = self.market_data[-20:]
        volatilities = [d.get('volatility', 0.01) for d in recent_data]
        vol_correlation = np.std(volatilities) / (np.mean(volatilities) + 1e-6)
        
        if vol_correlation < 0.2:
            return CorrelationRegime.LOW_CORRELATION
        elif vol_correlation < 0.5:
            return CorrelationRegime.MEDIUM_CORRELATION
        elif vol_correlation < 0.8:
            return CorrelationRegime.HIGH_CORRELATION
        else:
            return CorrelationRegime.EXTREME_CORRELATION
    
    def _detect_trend_regime(self) -> TrendRegime:
        """Detect current trend regime"""
        if len(self.market_data) < 20:
            return TrendRegime.SIDEWAYS
        
        recent_data = self.market_data[-20:]
        returns = [d.get('return', 0) for d in recent_data if 'return' in d]
        
        if not returns:
            return TrendRegime.SIDEWAYS
        
        # Calculate trend strength
        x = np.arange(len(returns))
        slope, _, r_value, _, _ = stats.linregress(x, returns)
        trend_strength = slope * r_value**2
        
        if trend_strength > 0.001:
            return TrendRegime.STRONG_UPTREND if trend_strength > 0.002 else TrendRegime.WEAK_UPTREND
        elif trend_strength < -0.001:
            return TrendRegime.STRONG_DOWNTREND if trend_strength < -0.002 else TrendRegime.WEAK_DOWNTREND
        else:
            return TrendRegime.SIDEWAYS
    
    def _calculate_regime_duration(self, regime: MarketRegime) -> int:
        """Calculate how long current regime has been active"""
        if not self.regime_history:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 1, -1, -1):
            if self.regime_history[i].regime_type == regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _calculate_transition_probability(self, regime: MarketRegime) -> float:
        """Calculate probability of regime transition"""
        if len(self.regime_history) < 10:
            return 0.1  # Default low probability
        
        # Analyze historical transition patterns
        current_duration = self._calculate_regime_duration(regime)
        
        # Simple model: probability increases with duration
        base_prob = 0.05  # 5% base daily transition probability
        duration_factor = min(current_duration / 30.0, 1.0)  # Max at 30 days
        
        return base_prob + (0.15 * duration_factor)  # Max 20% daily probability
    
    def _calculate_regime_strength(self, regime: MarketRegime) -> float:
        """Calculate how strong/clear the current regime is"""
        if len(self.market_data) < 20:
            return 0.5
        
        recent_data = self.market_data[-20:]
        returns = [d.get('return', 0) for d in recent_data if 'return' in d]
        volatilities = [d.get('volatility', 0.01) for d in recent_data]
        
        if not returns:
            return 0.5
        
        # Regime strength based on consistency with regime characteristics
        regime_chars = self.regime_characteristics.get(regime, {})
        
        strength_factors = []
        
        # Return consistency
        mean_return = np.mean(returns)
        if 'mean_return_range' in regime_chars:
            min_ret, max_ret = regime_chars['mean_return_range']
            if min_ret <= mean_return <= max_ret:
                strength_factors.append(1.0)
            else:
                distance = min(abs(mean_return - min_ret), abs(mean_return - max_ret))
                strength_factors.append(max(0.0, 1.0 - distance * 1000))  # Scale distance
        
        # Volatility consistency
        mean_vol = np.mean(volatilities)
        if 'volatility_range' in regime_chars:
            min_vol, max_vol = regime_chars['volatility_range']
            if min_vol <= mean_vol <= max_vol:
                strength_factors.append(1.0)
            else:
                distance = min(abs(mean_vol - min_vol), abs(mean_vol - max_vol))
                strength_factors.append(max(0.0, 1.0 - distance * 100))  # Scale distance
        
        return float(np.mean(strength_factors)) if strength_factors else 0.5
    
    def _calculate_regime_stability(self) -> float:
        """Calculate regime stability"""
        if len(self.regime_history) < 10:
            return 0.5
        
        # Count regime changes in recent history
        recent_regimes = [r.regime_type for r in self.regime_history[-10:]]
        unique_regimes = len(set(recent_regimes))
        
        # Stability = 1 - (regime_changes / total_periods)
        stability = 1.0 - (unique_regimes - 1) / 9.0  # 9 possible transitions in 10 periods
        return max(0.0, min(1.0, stability))
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(prices) < 2:
            return 0.0
        
        peak = prices[0]
        max_dd = 0.0
        
        for price in prices[1:]:
            if price > peak:
                peak = price
            else:
                drawdown = (peak - price) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    async def _record_regime_transition(self, from_regime: RegimeState, to_regime: RegimeState) -> None:
        """Record a regime transition event"""
        try:
            # Analyze transition characteristics
            transition_speed = self._analyze_transition_speed(from_regime, to_regime)
            warning_signals = self._identify_warning_signals()
            impact_magnitude = abs(to_regime.volatility - from_regime.volatility)
            
            transition = RegimeTransition(
                transition_time=to_regime.timestamp,
                from_regime=from_regime.regime_type,
                to_regime=to_regime.regime_type,
                transition_probability=to_regime.transition_probability,
                confidence=to_regime.confidence,
                transition_speed=transition_speed,
                warning_signals=warning_signals,
                impact_magnitude=impact_magnitude
            )
            
            with self.lock:
                self.transition_history.append(transition)
                if len(self.transition_history) > 200:
                    self.transition_history = self.transition_history[-200:]
            
            logger.info(f"Recorded regime transition: {from_regime.regime_type.value} → {to_regime.regime_type.value}")
            
        except Exception as e:
            logger.error(f"Error recording regime transition: {e}")
    
    def _analyze_transition_speed(self, from_regime: RegimeState, to_regime: RegimeState) -> str:
        """Analyze the speed of regime transition"""
        volatility_change = abs(to_regime.volatility - from_regime.volatility)
        
        if volatility_change > 0.02:
            return "sudden"
        elif volatility_change > 0.01:
            return "moderate"
        else:
            return "gradual"
    
    def _identify_warning_signals(self) -> List[str]:
        """Identify warning signals for regime transitions"""
        signals = []
        
        if len(self.market_data) < 10:
            return signals
        
        recent_data = self.market_data[-10:]
        
        # Volatility spike
        volatilities = [d.get('volatility', 0.01) for d in recent_data]
        if len(volatilities) >= 5:
            recent_vol = np.mean(volatilities[-3:])
            past_vol = np.mean(volatilities[-8:-3])
            if recent_vol > past_vol * 1.5:
                signals.append("volatility_spike")
        
        # Return reversal
        returns = [d.get('return', 0) for d in recent_data if 'return' in d]
        if len(returns) >= 5:
            recent_ret = np.mean(returns[-3:])
            past_ret = np.mean(returns[-8:-3])
            if recent_ret * past_ret < 0 and abs(recent_ret - past_ret) > 0.001:
                signals.append("return_reversal")
        
        # Volume spike (if available)
        volumes = [d.get('volume', 1000000) for d in recent_data if 'volume' in d]
        if len(volumes) >= 5:
            recent_vol = np.mean(volumes[-3:])
            past_vol = np.mean(volumes[-8:-3])
            if recent_vol > past_vol * 1.3:
                signals.append("volume_spike")
        
        return signals
    
    def _analyze_transition_patterns(self) -> Dict[str, Any]:
        """Analyze historical transition patterns"""
        if len(self.transition_history) < 10:
            return {}
        
        patterns = {
            'average_duration': {},
            'transition_frequencies': {},
            'common_sequences': []
        }
        
        # Analyze transition frequencies
        transition_counts = {}
        for transition in self.transition_history:
            key = f"{transition.from_regime.value}_to_{transition.to_regime.value}"
            transition_counts[key] = transition_counts.get(key, 0) + 1
        
        patterns['transition_frequencies'] = transition_counts
        
        # Average regime durations (from regime history)
        if len(self.regime_history) > 20:
            regime_durations = {}
            current_regime = None
            current_duration = 0
            
            for regime_state in self.regime_history:
                if regime_state.regime_type != current_regime:
                    if current_regime and current_duration > 0:
                        if current_regime not in regime_durations:
                            regime_durations[current_regime] = []
                        regime_durations[current_regime].append(current_duration)
                    current_regime = regime_state.regime_type
                    current_duration = 1
                else:
                    current_duration += 1
            
            # Calculate averages
            for regime, durations in regime_durations.items():
                patterns['average_duration'][regime.value] = np.mean(durations)
        
        return patterns
    
    def _build_transition_matrix(self) -> Dict[MarketRegime, Dict[MarketRegime, float]]:
        """Build regime transition probability matrix"""
        if len(self.transition_history) < 5:
            # Default transition matrix
            regimes = list(MarketRegime)
            n_regimes = len(regimes)
            default_prob = 1.0 / n_regimes
            
            matrix = {}
            for from_regime in regimes:
                matrix[from_regime] = {to_regime: default_prob for to_regime in regimes}
            
            return matrix
        
        # Count transitions
        transition_counts = {}
        
        for transition in self.transition_history:
            from_regime = transition.from_regime
            to_regime = transition.to_regime
            
            if from_regime not in transition_counts:
                transition_counts[from_regime] = {}
            
            transition_counts[from_regime][to_regime] = transition_counts[from_regime].get(to_regime, 0) + 1
        
        # Convert to probabilities
        transition_matrix = {}
        
        for from_regime, to_regimes in transition_counts.items():
            total_transitions = sum(to_regimes.values())
            transition_matrix[from_regime] = {}
            
            for to_regime, count in to_regimes.items():
                transition_matrix[from_regime][to_regime] = count / total_transitions
        
        # Fill missing regimes with default probabilities
        all_regimes = set(MarketRegime)
        for regime in all_regimes:
            if regime not in transition_matrix:
                n_regimes = len(all_regimes)
                default_prob = 1.0 / n_regimes
                transition_matrix[regime] = {r: default_prob for r in all_regimes}
        
        return transition_matrix
    
    def _forecast_regime_probabilities(self, current_regime: MarketRegime, horizon_days: int,
                                     transition_matrix: Dict[MarketRegime, Dict[MarketRegime, float]]) -> Dict[MarketRegime, float]:
        """Forecast regime probabilities using transition matrix"""
        # Initialize current state
        regimes = list(MarketRegime)
        current_probs = {regime: 0.0 for regime in regimes}
        current_probs[current_regime] = 1.0
        
        # Multi-step transition
        for day in range(horizon_days):
            new_probs = {regime: 0.0 for regime in regimes}
            
            for from_regime, prob in current_probs.items():
                if from_regime in transition_matrix:
                    for to_regime, trans_prob in transition_matrix[from_regime].items():
                        new_probs[to_regime] += prob * trans_prob
            
            current_probs = new_probs
        
        return current_probs
    
    def _estimate_regime_duration(self, regime: MarketRegime) -> int:
        """Estimate expected duration for a regime"""
        if len(self.regime_history) < 20:
            return 30  # Default 30 days
        
        # Calculate historical average duration
        durations = []
        current_regime = None
        current_duration = 0
        
        for regime_state in self.regime_history:
            if regime_state.regime_type == regime:
                if current_regime == regime:
                    current_duration += 1
                else:
                    current_regime = regime
                    current_duration = 1
            else:
                if current_regime == regime and current_duration > 0:
                    durations.append(current_duration)
                current_regime = None
                current_duration = 0
        
        if durations:
            return int(np.mean(durations))
        else:
            return 30  # Default
    
    def _identify_transition_signals(self) -> List[str]:
        """Identify current signals that may indicate regime transition"""
        signals = []
        
        if len(self.market_data) < 20:
            return signals
        
        recent_data = self.market_data[-20:]
        
        # Technical signals
        returns = [d.get('return', 0) for d in recent_data if 'return' in d]
        volatilities = [d.get('volatility', 0.01) for d in recent_data]
        
        # Moving average crossover
        if len(returns) >= 10:
            short_ma = np.mean(returns[-5:])
            long_ma = np.mean(returns[-10:])
            if abs(short_ma - long_ma) > 0.001:
                signals.append("moving_average_divergence")
        
        # Volatility regime change
        if len(volatilities) >= 10:
            recent_vol = np.mean(volatilities[-5:])
            historical_vol = np.mean(volatilities[-20:-5])
            if recent_vol > historical_vol * 1.3:
                signals.append("volatility_breakout")
        
        # Momentum shift
        if len(returns) >= 15:
            recent_momentum = np.sum(returns[-5:])
            past_momentum = np.sum(returns[-15:-10])
            if recent_momentum * past_momentum < 0:
                signals.append("momentum_reversal")
        
        return signals
    
    def _analyze_regime_risk_factors(self, regime: MarketRegime) -> Dict[str, float]:
        """Analyze risk factors for a specific regime"""
        risk_factors = {
            'volatility_risk': 0.0,
            'correlation_risk': 0.0,
            'liquidity_risk': 0.0,
            'tail_risk': 0.0
        }
        
        # Regime-specific risk assessments
        if regime == MarketRegime.CRISIS:
            risk_factors.update({
                'volatility_risk': 0.9,
                'correlation_risk': 0.9,
                'liquidity_risk': 0.8,
                'tail_risk': 0.9
            })
        elif regime == MarketRegime.HIGH_VOLATILITY:
            risk_factors.update({
                'volatility_risk': 0.8,
                'correlation_risk': 0.6,
                'liquidity_risk': 0.5,
                'tail_risk': 0.7
            })
        elif regime == MarketRegime.BULL_MARKET:
            risk_factors.update({
                'volatility_risk': 0.3,
                'correlation_risk': 0.4,
                'liquidity_risk': 0.2,
                'tail_risk': 0.3
            })
        elif regime == MarketRegime.BEAR_MARKET:
            risk_factors.update({
                'volatility_risk': 0.6,
                'correlation_risk': 0.7,
                'liquidity_risk': 0.5,
                'tail_risk': 0.6
            })
        else:  # SIDEWAYS_MARKET
            risk_factors.update({
                'volatility_risk': 0.4,
                'correlation_risk': 0.4,
                'liquidity_risk': 0.3,
                'tail_risk': 0.4
            })
        
        return risk_factors
    
    def _recommend_regime_adaptations(self, regime: MarketRegime) -> List[str]:
        """Recommend general adaptations for a regime"""
        adaptations = []
        
        if regime == MarketRegime.BULL_MARKET:
            adaptations.extend([
                "Increase position sizes",
                "Reduce hedging",
                "Focus on momentum strategies",
                "Expand market exposure"
            ])
        elif regime == MarketRegime.BEAR_MARKET:
            adaptations.extend([
                "Reduce position sizes",
                "Increase hedging",
                "Focus on defensive strategies",
                "Consider short positions"
            ])
        elif regime == MarketRegime.HIGH_VOLATILITY:
            adaptations.extend([
                "Reduce leverage",
                "Tighten stop losses",
                "Increase diversification",
                "Focus on volatility strategies"
            ])
        elif regime == MarketRegime.CRISIS:
            adaptations.extend([
                "Minimize exposure",
                "Maximize liquidity",
                "Implement crisis protocols",
                "Focus on safe haven assets"
            ])
        else:  # SIDEWAYS_MARKET
            adaptations.extend([
                "Use range trading strategies",
                "Focus on mean reversion",
                "Optimize transaction costs",
                "Maintain balanced exposure"
            ])
        
        return adaptations
    
    def _generate_strategy_adaptation(self, strategy_id: str, regime: MarketRegime) -> Optional[StrategyAdaptation]:
        """Generate specific strategy adaptation recommendation"""
        try:
            # Strategy-specific parameter adjustments based on regime
            parameter_adjustments = self._get_strategy_parameters(strategy_id, regime)
            
            if not parameter_adjustments:
                return None
            
            # Calculate expected improvement (simplified)
            expected_improvement = self._estimate_adaptation_improvement(strategy_id, regime)
            
            # Determine urgency and risk impact
            urgency = self._assess_adaptation_urgency(regime)
            risk_impact = self._assess_risk_impact(parameter_adjustments)
            
            # Implementation cost (simplified)
            implementation_cost = len(parameter_adjustments) * 0.1  # Complexity cost
            
            adaptation = StrategyAdaptation(
                strategy_id=strategy_id,
                current_regime=regime,
                recommended_parameters=parameter_adjustments['new'],
                parameter_changes=parameter_adjustments['changes'],
                adaptation_reason=f"Optimization for {regime.value} regime",
                expected_improvement=expected_improvement,
                urgency=urgency,
                risk_impact=risk_impact,
                implementation_cost=implementation_cost
            )
            
            return adaptation
            
        except Exception as e:
            logger.error(f"Error generating strategy adaptation for {strategy_id}: {e}")
            return None
    
    def _get_strategy_parameters(self, strategy_id: str, regime: MarketRegime) -> Dict[str, Any]:
        """Get strategy-specific parameter adjustments for regime"""
        # Simplified parameter adjustments (would be customized per strategy)
        base_params = {
            'position_size': 1.0,
            'stop_loss': 0.02,
            'take_profit': 0.04,
            'lookback_period': 20,
            'rebalance_frequency': 1
        }
        
        adjustments = {}
        
        if regime == MarketRegime.BULL_MARKET:
            adjustments = {
                'position_size': 1.2,
                'stop_loss': 0.025,
                'take_profit': 0.05,
                'lookback_period': 15,
                'rebalance_frequency': 1
            }
        elif regime == MarketRegime.BEAR_MARKET:
            adjustments = {
                'position_size': 0.7,
                'stop_loss': 0.015,
                'take_profit': 0.03,
                'lookback_period': 30,
                'rebalance_frequency': 1
            }
        elif regime == MarketRegime.HIGH_VOLATILITY:
            adjustments = {
                'position_size': 0.8,
                'stop_loss': 0.01,
                'take_profit': 0.02,
                'lookback_period': 10,
                'rebalance_frequency': 2
            }
        elif regime == MarketRegime.CRISIS:
            adjustments = {
                'position_size': 0.3,
                'stop_loss': 0.005,
                'take_profit': 0.01,
                'lookback_period': 5,
                'rebalance_frequency': 4
            }
        else:  # SIDEWAYS_MARKET
            adjustments = {
                'position_size': 1.0,
                'stop_loss': 0.02,
                'take_profit': 0.04,
                'lookback_period': 20,
                'rebalance_frequency': 1
            }
        
        # Calculate changes
        changes = {}
        for param, new_value in adjustments.items():
            old_value = base_params.get(param, 1.0)
            changes[param] = (old_value, new_value)
        
        return {
            'new': adjustments,
            'changes': changes
        }
    
    def _estimate_adaptation_improvement(self, strategy_id: str, regime: MarketRegime) -> float:
        """Estimate expected improvement from adaptation"""
        # Simplified improvement estimation
        regime_improvements = {
            MarketRegime.BULL_MARKET: 0.15,
            MarketRegime.BEAR_MARKET: 0.10,
            MarketRegime.HIGH_VOLATILITY: 0.20,
            MarketRegime.CRISIS: 0.25,
            MarketRegime.SIDEWAYS_MARKET: 0.05
        }
        
        return regime_improvements.get(regime, 0.10)
    
    def _assess_adaptation_urgency(self, regime: MarketRegime) -> str:
        """Assess urgency of adaptation"""
        high_urgency_regimes = [MarketRegime.CRISIS, MarketRegime.HIGH_VOLATILITY]
        medium_urgency_regimes = [MarketRegime.BEAR_MARKET]
        
        if regime in high_urgency_regimes:
            return "high"
        elif regime in medium_urgency_regimes:
            return "medium"
        else:
            return "low"
    
    def _assess_risk_impact(self, parameter_changes: Dict[str, Tuple[float, float]]) -> str:
        """Assess risk impact of parameter changes"""
        risk_increasing_changes = 0
        total_changes = len(parameter_changes)
        
        for param, (old_val, new_val) in parameter_changes.items():
            if param == 'position_size' and new_val > old_val:
                risk_increasing_changes += 1
            elif param == 'stop_loss' and new_val > old_val:
                risk_increasing_changes -= 1  # Wider stop loss = more risk
            elif param == 'leverage' and new_val > old_val:
                risk_increasing_changes += 1
        
        risk_ratio = risk_increasing_changes / max(total_changes, 1)
        
        if risk_ratio > 0.3:
            return "negative"  # Risk increasing
        elif risk_ratio < -0.3:
            return "positive"  # Risk decreasing
        else:
            return "neutral"
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get comprehensive regime detection summary"""
        with self.lock:
            return {
                'is_detecting': self.is_detecting,
                'data_points': len(self.market_data),
                'current_regime': self.current_regime,
                'regime_history_length': len(self.regime_history),
                'transitions_recorded': len(self.transition_history),
                'forecasts_generated': len(self.forecast_history),
                'model_trained': self.regime_model_trained,
                'confidence_threshold': self.confidence_threshold,
                'lookback_window': self.lookback_window
            }

# Global regime detector instance
regime_detector = RegimeDetector()

# Export main components
__all__ = [
    'RegimeDetector',
    'RegimeState',
    'RegimeTransition', 
    'RegimeForecast',
    'StrategyAdaptation',
    'MarketRegime',
    'VolatilityRegime',
    'CorrelationRegime',
    'TrendRegime',
    'regime_detector'
]
