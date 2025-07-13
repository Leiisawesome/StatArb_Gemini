"""
Advanced Regime Detection for Statistical Arbitrage
=================================================

Professional-grade regime detection system supporting:
- Hidden Markov Model (HMM) regime detection
- Kalman filter-based regime transitions
- Real-time regime classification
- Regime-aware parameter adaptation
- Multi-timeframe regime analysis

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.optimize import minimize
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class RegimeState:
    """Single regime state definition"""
    regime_id: int
    regime_name: str
    volatility_level: str  # 'low', 'medium', 'high'
    mean_return: float
    volatility: float
    persistence: float  # Average regime duration
    transition_probs: Dict[int, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.transition_probs:
            self.transition_probs = {self.regime_id: 0.95}  # Default high persistence

@dataclass
class RegimeDetectionResult:
    """Results from regime detection"""
    timestamp: datetime
    current_regime: int
    regime_probability: float
    regime_probabilities: Dict[int, float]
    regime_duration: int  # Days in current regime
    transition_probability: float
    volatility_estimate: float
    regime_stability: float  # 0-1 score
    
@dataclass
class RegimeTransition:
    """Regime transition event"""
    timestamp: datetime
    from_regime: int
    to_regime: int
    transition_probability: float
    duration_in_previous: int  # Days
    confidence: float

class BaseRegimeDetector:
    """Base class for regime detection algorithms"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.n_regimes = config.get('n_regimes', 3)
        self.lookback_window = config.get('lookback_window', 252)
        self.min_regime_duration = config.get('min_regime_duration', 5)
        self.regime_states = {}
        self.current_regime = None
        self.regime_history = []
        
    def fit(self, data: pd.Series) -> None:
        """Fit the regime detection model"""
        raise NotImplementedError
    
    def predict(self, data: pd.Series) -> RegimeDetectionResult:
        """Predict current regime"""
        raise NotImplementedError
    
    def get_regime_parameters(self, regime_id: int) -> Dict[str, float]:
        """Get parameters for specific regime"""
        if regime_id in self.regime_states:
            state = self.regime_states[regime_id]
            return {
                'mean_return': state.mean_return,
                'volatility': state.volatility,
                'persistence': state.persistence
            }
        return {}
    
    def get_transition_matrix(self) -> np.ndarray:
        """Get regime transition matrix"""
        matrix = np.zeros((self.n_regimes, self.n_regimes))
        for i in range(self.n_regimes):
            if i in self.regime_states:
                for j, prob in self.regime_states[i].transition_probs.items():
                    matrix[i, j] = prob
        return matrix

class HMMRegimeDetector(BaseRegimeDetector):
    """Hidden Markov Model regime detector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.scaler = StandardScaler()
        self.transition_matrix = None
        self.emission_params = None
        self.regime_means = None
        self.regime_vars = None
        
    def fit(self, data: pd.Series) -> None:
        """Fit HMM model to data"""
        try:
            # Prepare features
            features = self._prepare_features(data)
            
            # Fit Gaussian Mixture Model as HMM approximation
            self.model = GaussianMixture(
                n_components=self.n_regimes,
                covariance_type='full',
                max_iter=100,
                random_state=42
            )
            
            # Standardize features
            features_scaled = self.scaler.fit_transform(features)
            
            # Fit model
            self.model.fit(features_scaled)
            
            # Extract regime parameters
            self._extract_regime_parameters(features_scaled)
            
            # Estimate transition matrix
            self._estimate_transition_matrix(features_scaled)
            
            logger.info(f"HMM regime detector fitted with {self.n_regimes} regimes")
            
        except Exception as e:
            logger.error(f"Failed to fit HMM model: {e}")
            raise
    
    def _prepare_features(self, data: pd.Series) -> np.ndarray:
        """Prepare features for regime detection"""
        # Calculate returns
        returns = data.pct_change().dropna()
        
        # Feature engineering
        features = []
        
        # Rolling volatility (multiple windows)
        for window in [5, 10, 20, 60]:
            vol = returns.rolling(window).std()
            features.append(vol)
        
        # Rolling returns
        for window in [5, 10, 20]:
            ret = returns.rolling(window).mean()
            features.append(ret)
        
        # Volatility of volatility
        vol_20 = returns.rolling(20).std()
        vol_of_vol = vol_20.rolling(20).std()
        features.append(vol_of_vol)
        
        # Skewness and kurtosis
        skew = returns.rolling(60).skew()
        kurt = returns.rolling(60).kurt()
        features.append(skew)
        features.append(kurt)
        
        # Combine features
        feature_df = pd.concat(features, axis=1)
        feature_df.columns = [f'feature_{i}' for i in range(len(features))]
        
        # Drop NaN values
        feature_df = feature_df.dropna()
        
        return feature_df.values
    
    def _extract_regime_parameters(self, features: np.ndarray):
        """Extract regime parameters from fitted model"""
        self.regime_means = self.model.means_
        self.regime_vars = self.model.covariances_
        
        # Create regime states
        for i in range(self.n_regimes):
            # Determine volatility level based on first feature (5-day volatility)
            vol_level = self.regime_means[i][0]
            
            if vol_level < np.percentile(features[:, 0], 33):
                vol_name = 'low'
            elif vol_level < np.percentile(features[:, 0], 67):
                vol_name = 'medium'
            else:
                vol_name = 'high'
            
            self.regime_states[i] = RegimeState(
                regime_id=i,
                regime_name=f'Regime_{i}_{vol_name}',
                volatility_level=vol_name,
                mean_return=self.regime_means[i][5] if len(self.regime_means[i]) > 5 else 0.0,
                volatility=vol_level,
                persistence=0.95  # Will be updated by transition matrix
            )
    
    def _estimate_transition_matrix(self, features: np.ndarray):
        """Estimate transition matrix from regime sequence"""
        # Get regime sequence
        regime_probs = self.model.predict_proba(features)
        regime_sequence = np.argmax(regime_probs, axis=1)
        
        # Count transitions
        transition_counts = np.zeros((self.n_regimes, self.n_regimes))
        
        for i in range(1, len(regime_sequence)):
            from_regime = regime_sequence[i-1]
            to_regime = regime_sequence[i]
            transition_counts[from_regime, to_regime] += 1
        
        # Normalize to get probabilities
        self.transition_matrix = np.zeros((self.n_regimes, self.n_regimes))
        for i in range(self.n_regimes):
            row_sum = transition_counts[i].sum()
            if row_sum > 0:
                self.transition_matrix[i] = transition_counts[i] / row_sum
            else:
                self.transition_matrix[i, i] = 1.0  # Stay in same regime if no data
        
        # Update regime states with transition probabilities
        for i in range(self.n_regimes):
            transition_probs = {}
            for j in range(self.n_regimes):
                if self.transition_matrix[i, j] > 0.01:  # Only include significant transitions
                    transition_probs[j] = self.transition_matrix[i, j]
            
            self.regime_states[i].transition_probs = transition_probs
            self.regime_states[i].persistence = self.transition_matrix[i, i]
    
    def predict(self, data: pd.Series) -> RegimeDetectionResult:
        """Predict current regime"""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        try:
            # Prepare features for recent data
            features = self._prepare_features(data)
            
            if len(features) == 0:
                raise ValueError("Insufficient data for regime prediction")
            
            # Get last observation
            last_features = features[-1:].reshape(1, -1)
            
            # Scale features
            last_features_scaled = self.scaler.transform(last_features)
            
            # Predict regime probabilities
            regime_probs = self.model.predict_proba(last_features_scaled)[0]
            current_regime = np.argmax(regime_probs)
            
            # Calculate regime duration
            regime_duration = self._calculate_regime_duration(data, current_regime)
            
            # Calculate transition probability
            transition_prob = 1.0 - self.transition_matrix[current_regime, current_regime]
            
            # Calculate regime stability
            regime_stability = self._calculate_regime_stability(regime_probs)
            
            # Estimate current volatility
            vol_estimate = float(last_features_scaled[0, 0])  # First feature is volatility
            
            result = RegimeDetectionResult(
                timestamp=datetime.now(),
                current_regime=current_regime,
                regime_probability=regime_probs[current_regime],
                regime_probabilities={i: prob for i, prob in enumerate(regime_probs)},
                regime_duration=regime_duration,
                transition_probability=transition_prob,
                volatility_estimate=vol_estimate,
                regime_stability=regime_stability
            )
            
            # Update history
            self.regime_history.append(result)
            if len(self.regime_history) > 1000:  # Keep last 1000 observations
                self.regime_history = self.regime_history[-1000:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in regime prediction: {e}")
            raise
    
    def _calculate_regime_duration(self, data: pd.Series, current_regime: int) -> int:
        """Calculate how long we've been in current regime"""
        if len(self.regime_history) < 2:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 1, 0, -1):
            if self.regime_history[i-1].current_regime == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _calculate_regime_stability(self, regime_probs: np.ndarray) -> float:
        """Calculate regime stability score"""
        # Higher entropy means less stable
        entropy = -np.sum(regime_probs * np.log(regime_probs + 1e-10))
        max_entropy = np.log(len(regime_probs))
        
        # Convert to stability score (0-1, higher is more stable)
        stability = 1.0 - (entropy / max_entropy)
        return stability

class KalmanRegimeDetector(BaseRegimeDetector):
    """Kalman filter-based regime detector"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.volatility_states = None
        self.transition_threshold = config.get('transition_threshold', 2.0)
        self.process_noise = config.get('process_noise', 1e-4)
        self.observation_noise = config.get('observation_noise', 1e-2)
        
    def fit(self, data: pd.Series) -> None:
        """Fit Kalman filter regime detector"""
        try:
            # Calculate returns and volatility
            returns = data.pct_change().dropna()
            volatility = returns.rolling(20).std()
            
            # Define volatility quantiles for regime boundaries
            vol_quantiles = volatility.quantile([0.33, 0.67])
            
            # Create regime states based on volatility levels
            self.regime_states = {
                0: RegimeState(
                    regime_id=0,
                    regime_name='Low_Volatility',
                    volatility_level='low',
                    mean_return=returns[volatility <= vol_quantiles.iloc[0]].mean(),
                    volatility=volatility[volatility <= vol_quantiles.iloc[0]].mean(),
                    persistence=0.95
                ),
                1: RegimeState(
                    regime_id=1,
                    regime_name='Medium_Volatility',
                    volatility_level='medium',
                    mean_return=returns[(volatility > vol_quantiles.iloc[0]) & 
                                      (volatility <= vol_quantiles.iloc[1])].mean(),
                    volatility=volatility[(volatility > vol_quantiles.iloc[0]) & 
                                        (volatility <= vol_quantiles.iloc[1])].mean(),
                    persistence=0.90
                ),
                2: RegimeState(
                    regime_id=2,
                    regime_name='High_Volatility',
                    volatility_level='high',
                    mean_return=returns[volatility > vol_quantiles.iloc[1]].mean(),
                    volatility=volatility[volatility > vol_quantiles.iloc[1]].mean(),
                    persistence=0.85
                )
            }
            
            # Store volatility thresholds
            self.volatility_states = {
                'low_threshold': vol_quantiles.iloc[0],
                'high_threshold': vol_quantiles.iloc[1]
            }
            
            logger.info("Kalman regime detector fitted")
            
        except Exception as e:
            logger.error(f"Failed to fit Kalman regime detector: {e}")
            raise
    
    def predict(self, data: pd.Series) -> RegimeDetectionResult:
        """Predict current regime using Kalman filter"""
        if self.volatility_states is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        try:
            # Calculate current volatility
            returns = data.pct_change().dropna()
            current_vol = returns.tail(20).std()
            
            # Classify regime based on volatility
            if current_vol <= self.volatility_states['low_threshold']:
                current_regime = 0
            elif current_vol <= self.volatility_states['high_threshold']:
                current_regime = 1
            else:
                current_regime = 2
            
            # Calculate regime probabilities using Gaussian distributions
            regime_probs = self._calculate_regime_probabilities(current_vol)
            
            # Calculate regime duration
            regime_duration = self._calculate_regime_duration(data, current_regime)
            
            # Calculate transition probability
            transition_prob = 1.0 - self.regime_states[current_regime].persistence
            
            # Calculate regime stability
            regime_stability = self._calculate_regime_stability(regime_probs)
            
            result = RegimeDetectionResult(
                timestamp=datetime.now(),
                current_regime=current_regime,
                regime_probability=regime_probs[current_regime],
                regime_probabilities=regime_probs,
                regime_duration=regime_duration,
                transition_probability=transition_prob,
                volatility_estimate=current_vol,
                regime_stability=regime_stability
            )
            
            # Update history
            self.regime_history.append(result)
            if len(self.regime_history) > 1000:
                self.regime_history = self.regime_history[-1000:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Kalman regime prediction: {e}")
            raise
    
    def _calculate_regime_probabilities(self, current_vol: float) -> Dict[int, float]:
        """Calculate regime probabilities using Gaussian distributions"""
        probs = {}
        total_prob = 0.0
        
        for regime_id, state in self.regime_states.items():
            # Gaussian probability
            prob = stats.norm.pdf(current_vol, state.volatility, state.volatility * 0.5)
            probs[regime_id] = prob
            total_prob += prob
        
        # Normalize probabilities
        if total_prob > 0:
            for regime_id in probs:
                probs[regime_id] /= total_prob
        else:
            # Equal probabilities if no clear signal
            for regime_id in probs:
                probs[regime_id] = 1.0 / len(probs)
        
        return probs
    
    def _calculate_regime_duration(self, data: pd.Series, current_regime: int) -> int:
        """Calculate regime duration"""
        if len(self.regime_history) < 2:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 1, 0, -1):
            if self.regime_history[i-1].current_regime == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _calculate_regime_stability(self, regime_probs: Dict[int, float]) -> float:
        """Calculate regime stability score"""
        prob_values = list(regime_probs.values())
        max_prob = max(prob_values)
        
        # Stability is higher when one regime has much higher probability
        return max_prob

class RegimeAwarePairAnalyzer:
    """Analyzes pairs with regime-aware considerations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.regime_detector = self._create_regime_detector()
        self.regime_cache = {}
        
    def _create_regime_detector(self) -> BaseRegimeDetector:
        """Create regime detector based on config"""
        detector_type = self.config.get('detector_type', 'hmm')
        
        if detector_type == 'hmm':
            return HMMRegimeDetector(self.config)
        elif detector_type == 'kalman':
            return KalmanRegimeDetector(self.config)
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
    
    def fit_regime_model(self, price_data: pd.Series) -> None:
        """Fit regime detection model"""
        self.regime_detector.fit(price_data)
    
    def analyze_pair_regimes(self, price1: pd.Series, price2: pd.Series) -> Dict[str, Any]:
        """Analyze regime characteristics of a pair"""
        try:
            # Fit regime models for both assets
            self.regime_detector.fit(price1)
            regime1 = self.regime_detector.predict(price1)
            
            self.regime_detector.fit(price2)
            regime2 = self.regime_detector.predict(price2)
            
            # Calculate spread
            spread = price1 - price2
            
            # Fit regime model for spread
            self.regime_detector.fit(spread)
            spread_regime = self.regime_detector.predict(spread)
            
            # Analyze regime consistency
            regime_consistency = self._analyze_regime_consistency(regime1, regime2, spread_regime)
            
            # Calculate regime-adjusted correlation
            regime_correlation = self._calculate_regime_correlation(price1, price2, spread_regime)
            
            # Assess regime stability
            regime_stability = self._assess_regime_stability([regime1, regime2, spread_regime])
            
            return {
                'asset1_regime': regime1,
                'asset2_regime': regime2,
                'spread_regime': spread_regime,
                'regime_consistency': regime_consistency,
                'regime_correlation': regime_correlation,
                'regime_stability': regime_stability,
                'tradeable_in_regime': self._is_tradeable_in_regime(spread_regime)
            }
            
        except Exception as e:
            logger.error(f"Error in regime analysis: {e}")
            return {}
    
    def _analyze_regime_consistency(self, regime1: RegimeDetectionResult, 
                                   regime2: RegimeDetectionResult,
                                   spread_regime: RegimeDetectionResult) -> Dict[str, float]:
        """Analyze consistency between asset regimes and spread regime"""
        # Check if assets are in similar regimes
        asset_regime_similarity = 1.0 - abs(regime1.current_regime - regime2.current_regime) / 2.0
        
        # Check regime stability
        avg_stability = (regime1.regime_stability + regime2.regime_stability + 
                        spread_regime.regime_stability) / 3.0
        
        # Check transition probabilities
        avg_transition_prob = (regime1.transition_probability + regime2.transition_probability +
                              spread_regime.transition_probability) / 3.0
        
        return {
            'asset_regime_similarity': asset_regime_similarity,
            'average_stability': avg_stability,
            'average_transition_probability': avg_transition_prob,
            'consistency_score': asset_regime_similarity * avg_stability * (1.0 - avg_transition_prob)
        }
    
    def _calculate_regime_correlation(self, price1: pd.Series, price2: pd.Series,
                                    spread_regime: RegimeDetectionResult) -> Dict[str, float]:
        """Calculate correlation in different regimes"""
        returns1 = price1.pct_change().dropna()
        returns2 = price2.pct_change().dropna()
        
        # Overall correlation
        overall_corr = returns1.corr(returns2)
        
        # Regime-specific correlations would require more complex analysis
        # For now, return overall correlation with regime adjustment
        regime_adjustment = spread_regime.regime_stability
        
        return {
            'overall_correlation': overall_corr,
            'regime_adjusted_correlation': overall_corr * regime_adjustment,
            'correlation_stability': regime_adjustment
        }
    
    def _assess_regime_stability(self, regimes: List[RegimeDetectionResult]) -> Dict[str, float]:
        """Assess overall regime stability"""
        stabilities = [r.regime_stability for r in regimes]
        durations = [r.regime_duration for r in regimes]
        
        return {
            'average_stability': np.mean(stabilities),
            'min_stability': np.min(stabilities),
            'average_duration': np.mean(durations),
            'stability_score': np.mean(stabilities) * (1.0 - np.mean([r.transition_probability for r in regimes]))
        }
    
    def _is_tradeable_in_regime(self, spread_regime: RegimeDetectionResult) -> bool:
        """Determine if pair is tradeable in current regime"""
        # Pair is tradeable if:
        # 1. Regime is stable (high stability score)
        # 2. We've been in regime long enough
        # 3. Transition probability is not too high
        
        stable_enough = spread_regime.regime_stability > 0.6
        duration_enough = spread_regime.regime_duration >= self.config.get('min_regime_duration', 5)
        transition_low = spread_regime.transition_probability < 0.3
        
        return stable_enough and duration_enough and transition_low

def create_regime_detector(config: Dict[str, Any]) -> BaseRegimeDetector:
    """Factory function to create regime detector"""
    detector_type = config.get('detector_type', 'hmm')
    
    if detector_type == 'hmm':
        return HMMRegimeDetector(config)
    elif detector_type == 'kalman':
        return KalmanRegimeDetector(config)
    else:
        raise ValueError(f"Unknown detector type: {detector_type}") 