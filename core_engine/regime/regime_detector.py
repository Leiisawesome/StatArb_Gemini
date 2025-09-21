"""
Regime Detection Engine - Regime Detector
Advanced market regime detection using multiple methodologies and statistical models
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy import stats
from scipy.stats import norm
import statsmodels.api as sm
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from statsmodels.tsa.stattools import adfuller
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    EXPANSION = "expansion"
    CONTRACTION = "contraction"
    UNKNOWN = "unknown"


class DetectionMethod(Enum):
    """Regime detection methods"""
    MARKOV_SWITCHING = "markov_switching"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    CLUSTERING = "clustering"
    THRESHOLD_BASED = "threshold_based"
    STATISTICAL_TESTS = "statistical_tests"
    VOLATILITY_BASED = "volatility_based"
    CORRELATION_BASED = "correlation_based"
    MACHINE_LEARNING = "machine_learning"


class ConfidenceLevel(Enum):
    """Confidence levels for regime detection"""
    VERY_LOW = 0.50
    LOW = 0.65
    MEDIUM = 0.75
    HIGH = 0.85
    VERY_HIGH = 0.95


@dataclass
class RegimeDetectionConfig:
    """Configuration for regime detection"""
    
    # Detection methods to use
    methods: List[DetectionMethod] = field(default_factory=lambda: [
        DetectionMethod.MARKOV_SWITCHING,
        DetectionMethod.GAUSSIAN_MIXTURE,
        DetectionMethod.VOLATILITY_BASED
    ])
    
    # Lookback periods
    short_lookback: int = 20      # Short-term lookback
    medium_lookback: int = 60     # Medium-term lookback
    long_lookback: int = 252      # Long-term lookback
    
    # Volatility parameters
    volatility_window: int = 20
    volatility_threshold_high: float = 0.25  # 25% annualized
    volatility_threshold_low: float = 0.10   # 10% annualized
    
    # Return thresholds
    bull_threshold: float = 0.15    # 15% annual return
    bear_threshold: float = -0.10   # -10% annual return
    
    # Statistical parameters
    min_regime_duration: int = 10   # Minimum days in regime
    confidence_threshold: float = 0.75
    
    # Markov switching parameters
    n_regimes: int = 3
    switching_variance: bool = True
    
    # Clustering parameters
    n_clusters: int = 3
    random_state: int = 42
    
    # Update frequency
    update_frequency: str = "daily"  # daily, weekly, monthly
    
    # Regime persistence
    regime_persistence: float = 0.8  # Probability of staying in same regime


@dataclass
class RegimeDetection:
    """Individual regime detection result"""
    
    # Basic information
    timestamp: datetime = field(default_factory=datetime.now)
    regime_type: RegimeType = RegimeType.UNKNOWN
    confidence: float = 0.0
    method: DetectionMethod = DetectionMethod.THRESHOLD_BASED
    
    # Regime characteristics
    regime_start: Optional[datetime] = None
    regime_duration: Optional[int] = None  # In periods
    expected_duration: Optional[int] = None
    
    # Statistical measures
    regime_probability: float = 0.0
    transition_probability: float = 0.0
    stability_score: float = 0.0
    
    # Market characteristics during regime
    avg_return: float = 0.0
    volatility: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    max_drawdown: float = 0.0
    
    # Feature values
    features: Dict[str, float] = field(default_factory=dict)
    
    # Model outputs
    model_output: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    data_quality: float = 1.0
    warning_flags: List[str] = field(default_factory=list)


@dataclass
class RegimeTransition:
    """Regime transition information"""
    
    # Transition details
    from_regime: RegimeType
    to_regime: RegimeType
    transition_date: datetime
    transition_probability: float = 0.0
    
    # Transition characteristics
    transition_speed: str = "normal"  # fast, normal, slow
    transition_volatility: float = 0.0
    market_stress: float = 0.0
    
    # Predictive indicators
    leading_indicators: Dict[str, float] = field(default_factory=dict)
    warning_signals: List[str] = field(default_factory=list)
    
    # Performance impact
    performance_impact: float = 0.0
    risk_impact: float = 0.0


class MarkovSwitchingDetector:
    """Markov switching model for regime detection"""
    
    def __init__(self, config: RegimeDetectionConfig):
        self.config = config
        self.model = None
        self.fitted = False
        
        logger.info("Markov switching detector initialized")
    
    def fit(self, returns: pd.Series) -> bool:
        """Fit Markov switching model"""
        
        try:
            # Prepare data
            returns_clean = returns.dropna()
            
            if len(returns_clean) < 100:
                logger.warning("Insufficient data for Markov switching model")
                return False
            
            # Fit Markov regression model
            self.model = MarkovRegression(
                returns_clean.values,
                k_regimes=self.config.n_regimes,
                switching_variance=self.config.switching_variance
            )
            
            self.fitted_model = self.model.fit()
            self.fitted = True
            
            logger.info(f"Markov switching model fitted with {self.config.n_regimes} regimes")
            return True
            
        except Exception as e:
            logger.error(f"Error fitting Markov switching model: {e}")
            return False
    
    def detect_regime(self, returns: pd.Series, timestamp: datetime) -> Optional[RegimeDetection]:
        """Detect current regime using Markov switching model"""
        
        try:
            if not self.fitted:
                if not self.fit(returns):
                    return None
            
            # Get regime probabilities
            regime_probs = self.fitted_model.smoothed_marginal_probabilities
            
            # Handle both numpy array and pandas DataFrame formats
            if isinstance(regime_probs, np.ndarray):
                # Current regime (highest probability) - numpy array format
                current_regime_idx = np.argmax(regime_probs[-1])
                current_regime_prob = regime_probs[-1, current_regime_idx]
                latest_probs = regime_probs[-1]
            else:
                # Current regime (highest probability) - pandas DataFrame format
                current_regime_idx = np.argmax(regime_probs.iloc[-1])
                current_regime_prob = regime_probs.iloc[-1, current_regime_idx]
                latest_probs = regime_probs.iloc[-1]
            
            # Map regime index to regime type
            regime_type = self._map_regime_index(current_regime_idx, returns)
            
            # Calculate regime characteristics
            regime_returns = returns[regime_probs.iloc[:, current_regime_idx] > 0.5]
            
            detection = RegimeDetection(
                timestamp=timestamp,
                regime_type=regime_type,
                confidence=current_regime_prob,
                method=DetectionMethod.MARKOV_SWITCHING,
                regime_probability=current_regime_prob,
                avg_return=regime_returns.mean() if len(regime_returns) > 0 else 0,
                volatility=regime_returns.std() if len(regime_returns) > 0 else 0,
                model_output={
                    'regime_probabilities': latest_probs.to_dict() if hasattr(latest_probs, 'to_dict') else dict(enumerate(latest_probs)),
                    'regime_index': current_regime_idx,
                    'aic': self.fitted_model.aic,
                    'bic': self.fitted_model.bic
                }
            )
            
            return detection
            
        except Exception as e:
            logger.error(f"Error detecting regime with Markov switching: {e}")
            return None
    
    def _map_regime_index(self, regime_idx: int, returns: pd.Series) -> RegimeType:
        """Map regime index to regime type based on characteristics"""
        
        try:
            if not self.fitted:
                return RegimeType.UNKNOWN
            
            # Get regime parameters safely
            try:
                # Try different parameter naming conventions
                param_names = [f'const[{regime_idx}]', f'const.{regime_idx}', f'regime_{regime_idx}_const']
                regime_means = None
                
                for param_name in param_names:
                    if hasattr(self.fitted_model, 'params') and param_name in self.fitted_model.params:
                        regime_means = self.fitted_model.params[param_name]
                        break
                
                if regime_means is None:
                    # Fallback: calculate from returns data
                    regime_means = returns.mean()
                
                # Try to get variance
                variance_names = [f'sigma2[{regime_idx}]', f'sigma2.{regime_idx}', f'regime_{regime_idx}_var']
                regime_variance = None
                
                for var_name in variance_names:
                    if hasattr(self.fitted_model, 'params') and var_name in self.fitted_model.params:
                        regime_variance = self.fitted_model.params[var_name]
                        break
                
                if regime_variance is None:
                    # Fallback: calculate from returns data
                    regime_variance = returns.var()
                    
            except Exception as param_error:
                logger.warning(f"Could not extract regime parameters: {param_error}")
                # Use fallback values from returns data
                regime_means = returns.mean()
                regime_variance = returns.var()
            
            # Classify based on mean return and volatility
            annualized_return = regime_means * 252
            annualized_volatility = np.sqrt(regime_variance * 252)
            
            if annualized_return > self.config.bull_threshold:
                if annualized_volatility > self.config.volatility_threshold_high:
                    return RegimeType.HIGH_VOLATILITY
                else:
                    return RegimeType.BULL_MARKET
            elif annualized_return < self.config.bear_threshold:
                if annualized_volatility > self.config.volatility_threshold_high:
                    return RegimeType.CRISIS
                else:
                    return RegimeType.BEAR_MARKET
            else:
                if annualized_volatility > self.config.volatility_threshold_high:
                    return RegimeType.HIGH_VOLATILITY
                else:
                    return RegimeType.SIDEWAYS
                    
        except Exception as e:
            logger.warning(f"Error mapping regime index: {e}")
            return RegimeType.UNKNOWN


class GaussianMixtureDetector:
    """Gaussian mixture model for regime detection"""
    
    def __init__(self, config: RegimeDetectionConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.fitted = False
        
        logger.info("Gaussian mixture detector initialized")
    
    def fit(self, features: pd.DataFrame) -> bool:
        """Fit Gaussian mixture model"""
        
        try:
            # Prepare features
            features_clean = features.dropna()
            
            if len(features_clean) < 50:
                logger.warning("Insufficient data for Gaussian mixture model")
                return False
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_clean)
            
            # Fit Gaussian mixture model
            self.model = GaussianMixture(
                n_components=self.config.n_clusters,
                random_state=self.config.random_state,
                covariance_type='full'
            )
            
            self.model.fit(features_scaled)
            self.fitted = True
            
            logger.info(f"Gaussian mixture model fitted with {self.config.n_clusters} components")
            return True
            
        except Exception as e:
            logger.error(f"Error fitting Gaussian mixture model: {e}")
            return False
    
    def detect_regime(self, features: pd.DataFrame, timestamp: datetime) -> Optional[RegimeDetection]:
        """Detect current regime using Gaussian mixture model"""
        
        try:
            if not self.fitted:
                if not self.fit(features):
                    return None
            
            # Get current features
            current_features = features.iloc[-1:].dropna()
            
            if len(current_features) == 0:
                return None
            
            # Scale features
            current_features_scaled = self.scaler.transform(current_features)
            
            # Predict regime
            regime_idx = self.model.predict(current_features_scaled)[0]
            regime_probs = self.model.predict_proba(current_features_scaled)[0]
            
            # Map regime index to regime type
            regime_type = self._map_cluster_to_regime(regime_idx, features)
            
            detection = RegimeDetection(
                timestamp=timestamp,
                regime_type=regime_type,
                confidence=regime_probs[regime_idx],
                method=DetectionMethod.GAUSSIAN_MIXTURE,
                regime_probability=regime_probs[regime_idx],
                features=current_features.iloc[0].to_dict(),
                model_output={
                    'regime_probabilities': regime_probs.tolist(),
                    'cluster_index': int(regime_idx),
                    'aic': self.model.aic(self.scaler.transform(features.dropna())),
                    'bic': self.model.bic(self.scaler.transform(features.dropna()))
                }
            )
            
            return detection
            
        except Exception as e:
            logger.error(f"Error detecting regime with Gaussian mixture: {e}")
            return None
    
    def _map_cluster_to_regime(self, cluster_idx: int, features: pd.DataFrame) -> RegimeType:
        """Map cluster index to regime type"""
        
        try:
            # Get cluster characteristics
            features_scaled = self.scaler.transform(features.dropna())
            cluster_labels = self.model.predict(features_scaled)
            
            cluster_mask = cluster_labels == cluster_idx
            cluster_features = features.dropna()[cluster_mask]
            
            if len(cluster_features) == 0:
                return RegimeType.UNKNOWN
            
            # Analyze cluster characteristics
            if 'returns' in cluster_features.columns:
                avg_return = cluster_features['returns'].mean()
                if 'volatility' in cluster_features.columns:
                    avg_volatility = cluster_features['volatility'].mean()
                else:
                    avg_volatility = cluster_features['returns'].std()
                
                # Classify regime
                if avg_return > 0.001:  # Positive returns
                    if avg_volatility > 0.02:
                        return RegimeType.HIGH_VOLATILITY
                    else:
                        return RegimeType.BULL_MARKET
                elif avg_return < -0.001:  # Negative returns
                    if avg_volatility > 0.03:
                        return RegimeType.CRISIS
                    else:
                        return RegimeType.BEAR_MARKET
                else:  # Neutral returns
                    if avg_volatility > 0.02:
                        return RegimeType.HIGH_VOLATILITY
                    else:
                        return RegimeType.SIDEWAYS
            
            return RegimeType.UNKNOWN
            
        except Exception as e:
            logger.error(f"Error mapping cluster to regime: {e}")
            return RegimeType.UNKNOWN


class VolatilityBasedDetector:
    """Volatility-based regime detection"""
    
    def __init__(self, config: RegimeDetectionConfig):
        self.config = config
        logger.info("Volatility-based detector initialized")
    
    def detect_regime(self, returns: pd.Series, timestamp: datetime) -> Optional[RegimeDetection]:
        """Detect regime based on volatility patterns"""
        
        try:
            if len(returns) < self.config.volatility_window:
                return None
            
            # Calculate rolling volatility
            rolling_vol = returns.rolling(
                window=self.config.volatility_window
            ).std() * np.sqrt(252)  # Annualized
            
            current_vol = rolling_vol.iloc[-1]
            
            # Calculate returns for additional context
            rolling_returns = returns.rolling(
                window=self.config.volatility_window
            ).mean() * 252  # Annualized
            
            current_return = rolling_returns.iloc[-1]
            
            # Determine regime based on volatility and returns
            regime_type = self._classify_volatility_regime(current_vol, current_return)
            
            # Calculate confidence based on volatility persistence
            vol_history = rolling_vol.tail(self.config.short_lookback)
            if regime_type == RegimeType.HIGH_VOLATILITY:
                confidence = (vol_history > self.config.volatility_threshold_high).mean()
            elif regime_type == RegimeType.LOW_VOLATILITY:
                confidence = (vol_history < self.config.volatility_threshold_low).mean()
            else:
                confidence = 0.75  # Default confidence for other regimes
            
            # Calculate additional statistics
            recent_returns = returns.tail(self.config.volatility_window)
            
            detection = RegimeDetection(
                timestamp=timestamp,
                regime_type=regime_type,
                confidence=confidence,
                method=DetectionMethod.VOLATILITY_BASED,
                avg_return=current_return,
                volatility=current_vol,
                skewness=recent_returns.skew(),
                kurtosis=recent_returns.kurtosis(),
                max_drawdown=self._calculate_max_drawdown(recent_returns),
                features={
                    'current_volatility': current_vol,
                    'avg_volatility': vol_history.mean(),
                    'volatility_percentile': (vol_history < current_vol).mean(),
                    'volatility_trend': (vol_history.tail(5).mean() - vol_history.head(5).mean())
                }
            )
            
            return detection
            
        except Exception as e:
            logger.error(f"Error detecting volatility-based regime: {e}")
            return None
    
    def _classify_volatility_regime(self, volatility: float, returns: float) -> RegimeType:
        """Classify regime based on volatility and returns"""
        
        try:
            if volatility > self.config.volatility_threshold_high:
                if returns < self.config.bear_threshold:
                    return RegimeType.CRISIS
                else:
                    return RegimeType.HIGH_VOLATILITY
            elif volatility < self.config.volatility_threshold_low:
                if returns > self.config.bull_threshold:
                    return RegimeType.BULL_MARKET
                elif returns < self.config.bear_threshold:
                    return RegimeType.BEAR_MARKET
                else:
                    return RegimeType.LOW_VOLATILITY
            else:
                # Medium volatility
                if returns > self.config.bull_threshold:
                    return RegimeType.BULL_MARKET
                elif returns < self.config.bear_threshold:
                    return RegimeType.BEAR_MARKET
                else:
                    return RegimeType.SIDEWAYS
                    
        except Exception as e:
            logger.error(f"Error classifying volatility regime: {e}")
            return RegimeType.UNKNOWN
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0


class ThresholdBasedDetector:
    """Threshold-based regime detection"""
    
    def __init__(self, config: RegimeDetectionConfig):
        self.config = config
        logger.info("Threshold-based detector initialized")
    
    def detect_regime(self, returns: pd.Series, timestamp: datetime) -> Optional[RegimeDetection]:
        """Detect regime based on return thresholds"""
        
        try:
            if len(returns) < self.config.short_lookback:
                return None
            
            # Calculate metrics for different lookback periods
            short_return = returns.tail(self.config.short_lookback).mean() * 252
            medium_return = returns.tail(self.config.medium_lookback).mean() * 252 if len(returns) >= self.config.medium_lookback else short_return
            
            short_vol = returns.tail(self.config.short_lookback).std() * np.sqrt(252)
            
            # Determine regime
            regime_type = self._classify_threshold_regime(short_return, medium_return, short_vol)
            
            # Calculate confidence based on consistency across timeframes
            confidence = self._calculate_threshold_confidence(returns)
            
            detection = RegimeDetection(
                timestamp=timestamp,
                regime_type=regime_type,
                confidence=confidence,
                method=DetectionMethod.THRESHOLD_BASED,
                avg_return=short_return,
                volatility=short_vol,
                features={
                    'short_return': short_return,
                    'medium_return': medium_return,
                    'return_consistency': abs(short_return - medium_return),
                    'trend_strength': self._calculate_trend_strength(returns)
                }
            )
            
            return detection
            
        except Exception as e:
            logger.error(f"Error detecting threshold-based regime: {e}")
            return None
    
    def _classify_threshold_regime(self, short_return: float, medium_return: float, volatility: float) -> RegimeType:
        """Classify regime based on thresholds"""
        
        try:
            # Primary classification based on returns
            if short_return > self.config.bull_threshold and medium_return > self.config.bull_threshold * 0.5:
                return RegimeType.BULL_MARKET
            elif short_return < self.config.bear_threshold and medium_return < self.config.bear_threshold * 0.5:
                return RegimeType.BEAR_MARKET
            elif volatility > self.config.volatility_threshold_high:
                return RegimeType.HIGH_VOLATILITY
            elif volatility < self.config.volatility_threshold_low:
                return RegimeType.LOW_VOLATILITY
            else:
                return RegimeType.SIDEWAYS
                
        except Exception as e:
            logger.error(f"Error classifying threshold regime: {e}")
            return RegimeType.UNKNOWN
    
    def _calculate_threshold_confidence(self, returns: pd.Series) -> float:
        """Calculate confidence based on signal consistency"""
        
        try:
            if len(returns) < self.config.medium_lookback:
                return 0.5
            
            # Check consistency across different windows
            windows = [10, 20, 40, 60]
            classifications = []
            
            for window in windows:
                if len(returns) >= window:
                    window_return = returns.tail(window).mean() * 252
                    window_vol = returns.tail(window).std() * np.sqrt(252)
                    regime = self._classify_threshold_regime(window_return, window_return, window_vol)
                    classifications.append(regime)
            
            if not classifications:
                return 0.5
            
            # Calculate agreement across timeframes
            most_common = max(set(classifications), key=classifications.count)
            agreement = classifications.count(most_common) / len(classifications)
            
            return agreement
            
        except Exception as e:
            logger.error(f"Error calculating threshold confidence: {e}")
            return 0.5
    
    def _calculate_trend_strength(self, returns: pd.Series) -> float:
        """Calculate trend strength"""
        
        try:
            if len(returns) < 20:
                return 0.0
            
            # Linear regression slope as trend measure
            x = np.arange(len(returns.tail(20)))
            cumulative = (1 + returns.tail(20)).cumprod()
            
            slope, _, r_value, _, _ = stats.linregress(x, cumulative.values)
            
            return slope * (r_value ** 2)  # Adjusted by R-squared
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 0.0


class RegimeDetector:
    """
    Comprehensive Market Regime Detector
    
    Combines multiple detection methods to identify market regimes with high confidence.
    Supports Markov switching, Gaussian mixture models, volatility-based detection,
    and threshold-based classification.
    """
    
    def __init__(self, config: Optional[RegimeDetectionConfig] = None):
        """Initialize regime detector"""
        
        self.config = config or RegimeDetectionConfig()
        
        # Initialize detectors based on configuration
        self.detectors = {}
        
        if DetectionMethod.MARKOV_SWITCHING in self.config.methods:
            self.detectors[DetectionMethod.MARKOV_SWITCHING] = MarkovSwitchingDetector(self.config)
        
        if DetectionMethod.GAUSSIAN_MIXTURE in self.config.methods:
            self.detectors[DetectionMethod.GAUSSIAN_MIXTURE] = GaussianMixtureDetector(self.config)
        
        if DetectionMethod.VOLATILITY_BASED in self.config.methods:
            self.detectors[DetectionMethod.VOLATILITY_BASED] = VolatilityBasedDetector(self.config)
        
        if DetectionMethod.THRESHOLD_BASED in self.config.methods:
            self.detectors[DetectionMethod.THRESHOLD_BASED] = ThresholdBasedDetector(self.config)
        
        # Detection history
        self.detection_history: List[RegimeDetection] = []
        self.current_regime: Optional[RegimeDetection] = None
        self.regime_transitions: List[RegimeTransition] = []
        
        logger.info(f"Regime detector initialized with {len(self.detectors)} methods")
    
    def detect_current_regime(self, market_data: pd.DataFrame, 
                            timestamp: Optional[datetime] = None) -> Optional[RegimeDetection]:
        """Detect current market regime using all configured methods"""
        
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Extract returns from market data
            if 'close' in market_data.columns:
                returns = market_data['close'].pct_change().dropna()
            elif 'price' in market_data.columns:
                returns = market_data['price'].pct_change().dropna()
            else:
                # Assume first numeric column is price
                price_col = market_data.select_dtypes(include=[np.number]).columns[0]
                returns = market_data[price_col].pct_change().dropna()
            
            if len(returns) < self.config.short_lookback:
                logger.warning("Insufficient data for regime detection")
                return None
            
            # Run all detection methods
            detections = []
            
            for method, detector in self.detectors.items():
                try:
                    if method == DetectionMethod.GAUSSIAN_MIXTURE:
                        # Prepare features for Gaussian mixture model
                        features = self._prepare_features(market_data, returns)
                        detection = detector.detect_regime(features, timestamp)
                    else:
                        detection = detector.detect_regime(returns, timestamp)
                    
                    if detection:
                        detections.append(detection)
                        
                except Exception as e:
                    logger.warning(f"Error in {method.value} detection: {e}")
            
            if not detections:
                return None
            
            # Combine detections using ensemble method
            combined_detection = self._combine_detections(detections, timestamp)
            
            # Check for regime transition
            if self.current_regime and combined_detection.regime_type != self.current_regime.regime_type:
                transition = self._create_transition(self.current_regime, combined_detection)
                self.regime_transitions.append(transition)
            
            # Update current regime
            self.current_regime = combined_detection
            self.detection_history.append(combined_detection)
            
            # Keep history manageable
            if len(self.detection_history) > 1000:
                self.detection_history = self.detection_history[-500:]
            
            return combined_detection
            
        except Exception as e:
            logger.error(f"Error detecting current regime: {e}")
            return None
    
    def _prepare_features(self, market_data: pd.DataFrame, returns: pd.Series) -> pd.DataFrame:
        """Prepare features for machine learning models"""
        
        try:
            features = pd.DataFrame(index=returns.index)
            
            # Return-based features
            features['returns'] = returns
            features['returns_ma5'] = returns.rolling(5).mean()
            features['returns_ma20'] = returns.rolling(20).mean()
            features['returns_std20'] = returns.rolling(20).std()
            
            # Volatility features
            features['volatility'] = returns.rolling(20).std() * np.sqrt(252)
            features['volatility_ma'] = features['volatility'].rolling(10).mean()
            features['volatility_ratio'] = features['volatility'] / features['volatility_ma']
            
            # Trend features
            if len(returns) >= 50:
                features['trend_short'] = returns.rolling(10).mean()
                features['trend_medium'] = returns.rolling(30).mean()
                features['trend_ratio'] = features['trend_short'] / features['trend_medium']
            
            # Price-based features (if available)
            if 'close' in market_data.columns:
                close = market_data['close']
                features['price_ma20'] = close.rolling(20).mean()
                features['price_ma50'] = close.rolling(50).mean()
                features['price_ratio'] = close / features['price_ma20']
                
                if 'volume' in market_data.columns:
                    features['volume_ma'] = market_data['volume'].rolling(20).mean()
                    features['volume_ratio'] = market_data['volume'] / features['volume_ma']
            
            # Technical indicators
            features['rsi'] = self._calculate_rsi(returns)
            features['momentum'] = returns.rolling(10).sum()
            
            # Higher-order moments
            features['skewness'] = returns.rolling(30).skew()
            features['kurtosis'] = returns.rolling(30).apply(lambda x: x.kurtosis())
            
            return features.dropna()
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, returns: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        
        try:
            delta = returns
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=returns.index, dtype=float)
    
    def _combine_detections(self, detections: List[RegimeDetection], 
                           timestamp: datetime) -> RegimeDetection:
        """Combine multiple detection results using ensemble method"""
        
        try:
            if len(detections) == 1:
                return detections[0]
            
            # Weight detections by confidence
            regime_votes = {}
            total_weight = 0
            
            for detection in detections:
                regime = detection.regime_type
                weight = detection.confidence
                
                if regime not in regime_votes:
                    regime_votes[regime] = 0
                
                regime_votes[regime] += weight
                total_weight += weight
            
            # Normalize votes
            if total_weight > 0:
                for regime in regime_votes:
                    regime_votes[regime] /= total_weight
            
            # Select regime with highest weighted vote
            best_regime = max(regime_votes.keys(), key=lambda x: regime_votes[x])
            best_confidence = regime_votes[best_regime]
            
            # Combine other metrics (weighted average)
            combined_features = {}
            combined_model_output = {}
            
            for detection in detections:
                weight = detection.confidence / total_weight if total_weight > 0 else 1.0 / len(detections)
                
                # Combine features
                for key, value in detection.features.items():
                    if key not in combined_features:
                        combined_features[key] = 0
                    combined_features[key] += value * weight
                
                # Combine model outputs
                combined_model_output[detection.method.value] = detection.model_output
            
            # Calculate weighted averages for other metrics
            avg_return = sum(d.avg_return * d.confidence for d in detections) / total_weight if total_weight > 0 else 0
            avg_volatility = sum(d.volatility * d.confidence for d in detections) / total_weight if total_weight > 0 else 0
            
            # Create combined detection
            combined = RegimeDetection(
                timestamp=timestamp,
                regime_type=best_regime,
                confidence=best_confidence,
                method=DetectionMethod.MACHINE_LEARNING,  # Indicates ensemble
                avg_return=avg_return,
                volatility=avg_volatility,
                features=combined_features,
                model_output=combined_model_output
            )
            
            # Add ensemble-specific information
            combined.model_output['ensemble_votes'] = regime_votes
            combined.model_output['individual_detections'] = len(detections)
            combined.model_output['agreement_score'] = best_confidence
            
            return combined
            
        except Exception as e:
            logger.error(f"Error combining detections: {e}")
            # Return first detection as fallback
            return detections[0] if detections else RegimeDetection(timestamp=timestamp)
    
    def _create_transition(self, from_detection: RegimeDetection, 
                          to_detection: RegimeDetection) -> RegimeTransition:
        """Create regime transition object"""
        
        try:
            transition = RegimeTransition(
                from_regime=from_detection.regime_type,
                to_regime=to_detection.regime_type,
                transition_date=to_detection.timestamp,
                transition_probability=to_detection.confidence
            )
            
            # Calculate transition characteristics
            volatility_change = to_detection.volatility - from_detection.volatility
            transition.transition_volatility = abs(volatility_change)
            
            # Determine transition speed based on confidence change
            confidence_change = to_detection.confidence - from_detection.confidence
            if abs(confidence_change) > 0.3:
                transition.transition_speed = "fast"
            elif abs(confidence_change) < 0.1:
                transition.transition_speed = "slow"
            else:
                transition.transition_speed = "normal"
            
            # Market stress indicator
            if to_detection.regime_type in [RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY]:
                transition.market_stress = min(1.0, to_detection.volatility / 0.5)
            else:
                transition.market_stress = 0.1
            
            return transition
            
        except Exception as e:
            logger.error(f"Error creating transition: {e}")
            return RegimeTransition(
                from_regime=from_detection.regime_type,
                to_regime=to_detection.regime_type,
                transition_date=to_detection.timestamp
            )
    
    def get_regime_history(self, lookback_days: int = 30) -> List[RegimeDetection]:
        """Get regime history for specified period"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            
            return [
                detection for detection in self.detection_history
                if detection.timestamp >= cutoff_date
            ]
            
        except Exception as e:
            logger.error(f"Error getting regime history: {e}")
            return []
    
    def get_transition_history(self, lookback_days: int = 90) -> List[RegimeTransition]:
        """Get regime transition history"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            
            return [
                transition for transition in self.regime_transitions
                if transition.transition_date >= cutoff_date
            ]
            
        except Exception as e:
            logger.error(f"Error getting transition history: {e}")
            return []
    
    def get_regime_statistics(self) -> Dict[str, Any]:
        """Get comprehensive regime statistics"""
        
        try:
            if not self.detection_history:
                return {}
            
            # Regime distribution
            regime_counts = {}
            for detection in self.detection_history:
                regime = detection.regime_type
                if regime not in regime_counts:
                    regime_counts[regime] = 0
                regime_counts[regime] += 1
            
            total_detections = len(self.detection_history)
            regime_distribution = {
                regime.value: count / total_detections 
                for regime, count in regime_counts.items()
            }
            
            # Average regime duration
            regime_durations = self._calculate_regime_durations()
            
            # Transition statistics
            transition_matrix = self._calculate_transition_matrix()
            
            # Performance by regime
            regime_performance = self._calculate_regime_performance()
            
            return {
                'total_detections': total_detections,
                'regime_distribution': regime_distribution,
                'regime_durations': regime_durations,
                'transition_matrix': transition_matrix,
                'regime_performance': regime_performance,
                'current_regime': self.current_regime.regime_type.value if self.current_regime else None,
                'current_confidence': self.current_regime.confidence if self.current_regime else 0,
                'total_transitions': len(self.regime_transitions)
            }
            
        except Exception as e:
            logger.error(f"Error getting regime statistics: {e}")
            return {}
    
    def _calculate_regime_durations(self) -> Dict[str, float]:
        """Calculate average regime durations"""
        
        try:
            regime_durations = {}
            current_regime = None
            current_start = None
            
            for detection in self.detection_history:
                if current_regime != detection.regime_type:
                    # Regime change
                    if current_regime is not None and current_start is not None:
                        duration = (detection.timestamp - current_start).days
                        
                        if current_regime.value not in regime_durations:
                            regime_durations[current_regime.value] = []
                        
                        regime_durations[current_regime.value].append(duration)
                    
                    current_regime = detection.regime_type
                    current_start = detection.timestamp
            
            # Calculate averages
            avg_durations = {}
            for regime, durations in regime_durations.items():
                avg_durations[regime] = sum(durations) / len(durations) if durations else 0
            
            return avg_durations
            
        except Exception as e:
            logger.error(f"Error calculating regime durations: {e}")
            return {}
    
    def _calculate_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        """Calculate regime transition matrix"""
        
        try:
            transition_counts = {}
            
            for transition in self.regime_transitions:
                from_regime = transition.from_regime.value
                to_regime = transition.to_regime.value
                
                if from_regime not in transition_counts:
                    transition_counts[from_regime] = {}
                
                if to_regime not in transition_counts[from_regime]:
                    transition_counts[from_regime][to_regime] = 0
                
                transition_counts[from_regime][to_regime] += 1
            
            # Normalize to probabilities
            transition_matrix = {}
            for from_regime, to_regimes in transition_counts.items():
                total_transitions = sum(to_regimes.values())
                
                transition_matrix[from_regime] = {}
                for to_regime, count in to_regimes.items():
                    transition_matrix[from_regime][to_regime] = count / total_transitions
            
            return transition_matrix
            
        except Exception as e:
            logger.error(f"Error calculating transition matrix: {e}")
            return {}
    
    def _calculate_regime_performance(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance statistics by regime"""
        
        try:
            regime_performance = {}
            
            for detection in self.detection_history:
                regime = detection.regime_type.value
                
                if regime not in regime_performance:
                    regime_performance[regime] = {
                        'returns': [],
                        'volatilities': [],
                        'confidences': []
                    }
                
                regime_performance[regime]['returns'].append(detection.avg_return)
                regime_performance[regime]['volatilities'].append(detection.volatility)
                regime_performance[regime]['confidences'].append(detection.confidence)
            
            # Calculate statistics
            regime_stats = {}
            for regime, data in regime_performance.items():
                regime_stats[regime] = {
                    'avg_return': np.mean(data['returns']) if data['returns'] else 0,
                    'avg_volatility': np.mean(data['volatilities']) if data['volatilities'] else 0,
                    'avg_confidence': np.mean(data['confidences']) if data['confidences'] else 0,
                    'return_std': np.std(data['returns']) if data['returns'] else 0,
                    'count': len(data['returns'])
                }
            
            return regime_stats
            
        except Exception as e:
            logger.error(f"Error calculating regime performance: {e}")
            return {}