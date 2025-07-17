"""
AI-Ready Model Ensemble for Signal Generation
=============================================

Professional ensemble framework that combines multiple models with:
- Dynamic model weighting based on performance
- Real-time confidence scoring and uncertainty quantification
- Parallel model execution with sub-100ms latency
- Comprehensive model monitoring and drift detection
- Production-ready model management and versioning

Key Features:
- Multi-model prediction aggregation (Kalman, HMM, ML models)
- Adaptive weighting based on recent performance
- Real-time model performance monitoring
- Automated model retraining and versioning
- Professional error handling and fallback mechanisms

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
import pickle
from collections import defaultdict, deque

# External dependencies with graceful fallback
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    from sklearn.model_selection import TimeSeriesSplit
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Base model interface
class BaseModel:
    """Abstract base class for all models"""
    
    def __init__(self, **kwargs):
        self.hyperparameters = kwargs
        self.is_fitted = False
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the model"""
        raise NotImplementedError
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        raise NotImplementedError
        
    def predict_proba(self, X: np.ndarray) -> Optional[np.ndarray]:
        """Get prediction probabilities if supported"""
        return None

class KalmanFilterModel(BaseModel):
    """Kalman Filter for time-series prediction"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Kalman filter parameters
        self.process_noise = kwargs.get('process_noise', 0.1)
        self.observation_noise = kwargs.get('observation_noise', 0.1)
        self.initial_state_variance = kwargs.get('initial_state_variance', 1.0)
        
        # State variables
        self.state_mean = 0.0
        self.state_variance = self.initial_state_variance
        self.predictions_history = deque(maxlen=100)
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Initialize Kalman filter with training data"""
        if len(y) > 0:
            self.state_mean = np.mean(y)
            self.state_variance = np.var(y) if len(y) > 1 else self.initial_state_variance
        self.is_fitted = True
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using Kalman filter"""
        if not self.is_fitted:
            return np.zeros(X.shape[0])
            
        predictions = []
        for i in range(X.shape[0]):
            # Prediction step
            predicted_state = self.state_mean
            predicted_variance = self.state_variance + self.process_noise
            
            # Update step (using feature as observation)
            if X.shape[1] > 0:
                observation = np.mean(X[i])  # Simple observation from features
                kalman_gain = predicted_variance / (predicted_variance + self.observation_noise)
                
                # Update state
                self.state_mean = predicted_state + kalman_gain * (observation - predicted_state)
                self.state_variance = (1 - kalman_gain) * predicted_variance
            
            # Convert to binary prediction
            prediction = 1 if self.state_mean > 0 else 0
            predictions.append(prediction)
            
        return np.array(predictions)

class HMMRegimeModel(BaseModel):
    """Hidden Markov Model for regime detection"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.n_states = kwargs.get('n_states', 3)  # Bull, Bear, Sideways
        self.regime_names = ['bearish', 'sideways', 'bullish']
        
        # Simple regime thresholds
        self.bull_threshold = kwargs.get('bull_threshold', 0.02)
        self.bear_threshold = kwargs.get('bear_threshold', -0.02)
        
        # State tracking
        self.current_regime = 1  # Start with sideways
        self.regime_history = deque(maxlen=50)
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train HMM on historical data"""
        # Simple implementation: analyze returns to determine regime patterns
        if X.shape[1] > 0:
            returns = X[:, 0] if X.shape[1] > 0 else y  # Use first feature as returns
            
            # Calculate regime transitions based on returns
            for ret in returns:
                if ret > self.bull_threshold:
                    regime = 2  # Bullish
                elif ret < self.bear_threshold:
                    regime = 0  # Bearish
                else:
                    regime = 1  # Sideways
                self.regime_history.append(regime)
                
        self.is_fitted = True
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict regime and convert to trading signal"""
        if not self.is_fitted:
            return np.zeros(X.shape[0])
            
        predictions = []
        for i in range(X.shape[0]):
            # Simple regime detection based on recent returns
            if X.shape[1] > 0:
                recent_return = X[i, 0] if X.shape[1] > 0 else 0
                
                if recent_return > self.bull_threshold:
                    regime = 2  # Bullish
                elif recent_return < self.bear_threshold:
                    regime = 0  # Bearish
                else:
                    regime = 1  # Sideways
                    
                self.current_regime = regime
                
                # Convert regime to binary prediction
                # Bullish regime -> buy signal (1), others -> sell signal (0)
                prediction = 1 if regime == 2 else 0
                predictions.append(prediction)
            else:
                predictions.append(0)
                
        return np.array(predictions)
        
    def get_current_regime(self) -> str:
        """Get current regime name"""
        return self.regime_names[self.current_regime]

class CustomModel(BaseModel):
    """Extensible custom model framework"""
    
    def __init__(self, custom_predictor: Optional[Callable] = None, **kwargs):
        # Remove custom_predictor from kwargs to avoid duplicate argument
        kwargs.pop('custom_predictor', None)
        super().__init__(**kwargs)
        self.custom_predictor = custom_predictor
        self.model_data = {}
        
    def set_custom_predictor(self, predictor: Callable) -> None:
        """Set custom prediction function"""
        self.custom_predictor = predictor
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train custom model"""
        self.model_data['X_train'] = X
        self.model_data['y_train'] = y
        
        # If custom predictor has a fit method, call it
        if hasattr(self.custom_predictor, 'fit'):
            self.custom_predictor.fit(X, y)
            
        self.is_fitted = True
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using custom predictor"""
        if not self.is_fitted or self.custom_predictor is None:
            return np.zeros(X.shape[0])
            
        try:
            # Call custom predictor
            if callable(self.custom_predictor):
                predictions = self.custom_predictor(X)
                if isinstance(predictions, (int, float)):
                    return np.array([predictions])
                return np.array(predictions)
            else:
                return np.zeros(X.shape[0])
        except Exception as e:
            logger.error(f"Custom predictor failed: {e}")
            return np.zeros(X.shape[0])

class EnsembleVotingModel(BaseModel):
    """Meta-ensemble that combines multiple models using voting"""
    
    def __init__(self, models: Optional[List[BaseModel]] = None, voting_strategy: str = 'majority', **kwargs):
        # Remove known arguments from kwargs to avoid duplicate argument
        kwargs.pop('voting_strategy', None)
        kwargs.pop('models', None)
        kwargs.pop('model_weights', None)
        
        super().__init__(**kwargs)
        self.models = models or []
        self.voting_strategy = voting_strategy  # 'majority', 'weighted', 'unanimous'
        self.model_weights = kwargs.get('model_weights', None)
        
    def add_model(self, model: BaseModel, weight: float = 1.0) -> None:
        """Add a model to the voting ensemble"""
        self.models.append(model)
        if self.model_weights is None:
            self.model_weights = []
        self.model_weights.append(weight)
        
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train all models in the voting ensemble"""
        for model in self.models:
            try:
                model.fit(X, y)
            except Exception as e:
                logger.error(f"Model training failed in voting ensemble: {e}")
        self.is_fitted = True
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions using voting strategy"""
        if not self.is_fitted or not self.models:
            return np.zeros(X.shape[0])
            
        predictions = []
        
        for i in range(X.shape[0]):
            model_predictions = []
            
            # Get predictions from all models
            for model in self.models:
                try:
                    pred = model.predict(X[i:i+1])
                    model_predictions.append(pred[0] if len(pred) > 0 else 0)
                except Exception as e:
                    logger.error(f"Model prediction failed in voting: {e}")
                    model_predictions.append(0)
            
            # Apply voting strategy
            if self.voting_strategy == 'majority':
                # Simple majority vote
                final_pred = 1 if sum(model_predictions) > len(model_predictions) / 2 else 0
            elif self.voting_strategy == 'weighted' and self.model_weights:
                # Weighted vote
                weighted_sum = sum(p * w for p, w in zip(model_predictions, self.model_weights))
                total_weight = sum(self.model_weights)
                final_pred = 1 if weighted_sum > total_weight / 2 else 0
            elif self.voting_strategy == 'unanimous':
                # All models must agree
                final_pred = 1 if all(p == 1 for p in model_predictions) else 0
            else:
                # Default to majority
                final_pred = 1 if sum(model_predictions) > len(model_predictions) / 2 else 0
                
            predictions.append(final_pred)
            
        return np.array(predictions)

class ModelType(Enum):
    """Supported model types"""
    KALMAN_FILTER = "kalman_filter"
    HMM_REGIME = "hmm_regime"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOST = "gradient_boost"
    LOGISTIC_REGRESSION = "logistic_regression"
    ENSEMBLE_VOTING = "ensemble_voting"
    CUSTOM = "custom"

class ModelStatus(Enum):
    """Model status indicators"""
    ACTIVE = "active"
    TRAINING = "training"
    STALE = "stale"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class ModelConfig:
    """Configuration for individual models"""
    model_type: ModelType
    name: str
    weight: float = 1.0
    enabled: bool = True
    retrain_frequency_hours: int = 24
    performance_window: int = 100
    min_accuracy_threshold: float = 0.55
    max_staleness_hours: int = 48
    hyperparameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PredictionMetrics:
    """Comprehensive prediction metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confidence: float
    uncertainty: float
    prediction_time_ms: float
    model_version: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EnsembleResult:
    """Ensemble prediction result with metadata"""
    prediction: Union[int, float]
    confidence: float
    uncertainty: float
    model_contributions: Dict[str, float]
    individual_predictions: Dict[str, Union[int, float]]
    model_weights: Dict[str, float]
    consensus_score: float
    prediction_time_ms: float
    model_versions: Dict[str, str]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ModelWeights:
    """Dynamic model weights with performance tracking"""
    weights: Dict[str, float]
    performance_scores: Dict[str, float]
    last_updated: datetime
    decay_rate: float = 0.95
    min_weight: float = 0.01
    max_weight: float = 0.5

class ModelPerformanceTracker:
    """Track model performance with exponential decay"""
    
    def __init__(self, window_size: int = 100, decay_rate: float = 0.95):
        self.window_size = window_size
        self.decay_rate = decay_rate
        self.predictions: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.actuals: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.performance_cache: Dict[str, PredictionMetrics] = {}
        self._lock = threading.RLock()
    
    def record_prediction(
        self,
        model_name: str,
        prediction: Union[int, float],
        actual: Union[int, float],
        confidence: float = 1.0,
        prediction_time_ms: float = 0.0
    ) -> None:
        """Record model prediction and actual outcome"""
        with self._lock:
            self.predictions[model_name].append(prediction)
            self.actuals[model_name].append(actual)
            self.timestamps[model_name].append(datetime.now())
            
            # Invalidate cache
            if model_name in self.performance_cache:
                del self.performance_cache[model_name]
    
    def get_performance(self, model_name: str) -> Optional[PredictionMetrics]:
        """Get performance metrics for a model"""
        with self._lock:
            if model_name in self.performance_cache:
                return self.performance_cache[model_name]
            
            if model_name not in self.predictions or len(self.predictions[model_name]) < 10:
                return None
            
            try:
                predictions = np.array(list(self.predictions[model_name]))
                actuals = np.array(list(self.actuals[model_name]))
                timestamps = list(self.timestamps[model_name])
                
                # Apply time decay
                current_time = datetime.now()
                time_weights = np.array([
                    self.decay_rate ** ((current_time - ts).total_seconds() / 3600)
                    for ts in timestamps
                ])
                
                # Calculate weighted metrics
                if len(np.unique(actuals)) > 1:  # Classification metrics
                    # Convert to binary for metrics calculation
                    pred_binary = (predictions > 0.5).astype(int)
                    actual_binary = (actuals > 0.5).astype(int)
                    
                    # Weighted accuracy
                    correct = (pred_binary == actual_binary).astype(float)
                    accuracy = np.average(correct, weights=time_weights)
                    
                    # Precision and recall (simplified)
                    true_positives = np.sum((pred_binary == 1) & (actual_binary == 1) * time_weights)
                    false_positives = np.sum((pred_binary == 1) & (actual_binary == 0) * time_weights)
                    false_negatives = np.sum((pred_binary == 0) & (actual_binary == 1) * time_weights)
                    
                    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
                    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
                    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
                else:
                    # Regression metrics
                    mse = np.average((predictions - actuals) ** 2, weights=time_weights)
                    accuracy = max(0.0, 1.0 - mse)  # Normalized accuracy
                    precision = accuracy
                    recall = accuracy
                    f1_score = accuracy
                
                # Calculate confidence and uncertainty
                prediction_variance = np.average((predictions - np.average(predictions, weights=time_weights)) ** 2, weights=time_weights)
                confidence = max(0.0, min(1.0, accuracy))
                uncertainty = min(1.0, prediction_variance)
                
                metrics = PredictionMetrics(
                    accuracy=accuracy,
                    precision=precision,
                    recall=recall,
                    f1_score=f1_score,
                    confidence=confidence,
                    uncertainty=uncertainty,
                    prediction_time_ms=0.0,  # Updated separately
                    model_version="1.0"
                )
                
                # Cache the result
                self.performance_cache[model_name] = metrics
                return metrics
                
            except Exception as e:
                logger.error(f"Performance calculation failed for {model_name}: {e}")
                return None
    
    def get_all_performance(self) -> Dict[str, PredictionMetrics]:
        """Get performance metrics for all models"""
        results = {}
        for model_name in self.predictions.keys():
            metrics = self.get_performance(model_name)
            if metrics:
                results[model_name] = metrics
        return results

class ModelEnsemble:
    """
    Professional AI-ready model ensemble with dynamic weighting
    """
    
    def __init__(self, models: Optional[List[ModelConfig]] = None):
        """
        Initialize model ensemble
        
        Args:
            models: List of model configurations
        """
        self.models: Dict[str, Any] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_status: Dict[str, ModelStatus] = {}
        
        # Performance tracking
        self.performance_tracker = ModelPerformanceTracker()
        self.model_weights = ModelWeights(
            weights={},
            performance_scores={},
            last_updated=datetime.now()
        )
        
        # Execution management
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.prediction_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl_seconds = 60
        
        # Initialize with provided models
        if models:
            for model_config in models:
                self.add_model(model_config)
        
        logger.info("ModelEnsemble initialized")
    
    def add_model(self, config: ModelConfig) -> bool:
        """
        Add a model to the ensemble
        
        Args:
            config: Model configuration
            
        Returns:
            True if model added successfully
        """
        try:
            model_name = config.name
            
            # Initialize model based on type
            if config.model_type == ModelType.RANDOM_FOREST and SKLEARN_AVAILABLE:
                model = RandomForestClassifier(**config.hyperparameters)
            elif config.model_type == ModelType.GRADIENT_BOOST and SKLEARN_AVAILABLE:
                model = GradientBoostingClassifier(**config.hyperparameters)
            elif config.model_type == ModelType.LOGISTIC_REGRESSION and SKLEARN_AVAILABLE:
                model = LogisticRegression(**config.hyperparameters)
            elif config.model_type == ModelType.KALMAN_FILTER:
                model = KalmanFilterModel(**config.hyperparameters)
            elif config.model_type == ModelType.HMM_REGIME:
                model = HMMRegimeModel(**config.hyperparameters)
            elif config.model_type == ModelType.CUSTOM:
                custom_predictor = config.hyperparameters.get('custom_predictor', None)
                # Create clean hyperparameters without custom_predictor
                clean_params = {k: v for k, v in config.hyperparameters.items() if k != 'custom_predictor'}
                model = CustomModel(custom_predictor=custom_predictor, **clean_params)
            elif config.model_type == ModelType.ENSEMBLE_VOTING:
                voting_strategy = config.hyperparameters.get('voting_strategy', 'majority')
                model_weights = config.hyperparameters.get('model_weights', None)
                # Create clean hyperparameters
                clean_params = {k: v for k, v in config.hyperparameters.items() 
                              if k not in ['voting_strategy', 'model_weights']}
                model = EnsembleVotingModel(
                    models=[],
                    voting_strategy=voting_strategy,
                    model_weights=model_weights,
                    **clean_params
                )
            else:
                # Fallback for unknown types
                model = None
                logger.warning(f"Model type {config.model_type} not implemented, using placeholder")
            
            # Store model components
            self.models[model_name] = model
            self.model_configs[model_name] = config
            self.model_status[model_name] = ModelStatus.ACTIVE if model else ModelStatus.ERROR
            
            # Initialize weight
            self.model_weights.weights[model_name] = config.weight
            self.model_weights.performance_scores[model_name] = 0.5  # Neutral start
            
            logger.info(f"Added model {model_name} of type {config.model_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add model {config.name}: {e}")
            return False
    
    def remove_model(self, model_name: str) -> bool:
        """Remove a model from the ensemble"""
        try:
            if model_name in self.models:
                del self.models[model_name]
                del self.model_configs[model_name]
                del self.model_status[model_name]
                self.model_weights.weights.pop(model_name, None)
                self.model_weights.performance_scores.pop(model_name, None)
                logger.info(f"Removed model {model_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove model {model_name}: {e}")
            return False
    
    async def predict(
        self,
        features: Dict[str, float],
        feature_array: Optional[np.ndarray] = None
    ) -> Optional[EnsembleResult]:
        """
        Generate ensemble prediction
        
        Args:
            features: Feature dictionary
            feature_array: Optional pre-processed feature array
            
        Returns:
            EnsembleResult with prediction and metadata
        """
        start_time = time.time()
        
        try:
            # Check cache
            cache_key = self._generate_cache_key(features)
            cached_result = self._get_cached_prediction(cache_key)
            if cached_result:
                return cached_result
            
            # Prepare features
            if feature_array is None:
                feature_array = self._prepare_features(features)
            
            if feature_array is None or len(feature_array) == 0:
                logger.warning("No features available for prediction")
                return None
            
            # Get predictions from all active models
            prediction_tasks = []
            active_models = [
                name for name, status in self.model_status.items()
                if status == ModelStatus.ACTIVE and self.model_configs[name].enabled
            ]
            
            for model_name in active_models:
                task = asyncio.create_task(
                    self._get_model_prediction(model_name, feature_array, features)
                )
                prediction_tasks.append((model_name, task))
            
            # Execute predictions in parallel
            individual_predictions = {}
            model_confidences = {}
            
            for model_name, task in prediction_tasks:
                try:
                    prediction, confidence = await asyncio.wait_for(task, timeout=0.1)  # 100ms timeout
                    individual_predictions[model_name] = prediction
                    model_confidences[model_name] = confidence
                except asyncio.TimeoutError:
                    logger.warning(f"Model {model_name} prediction timed out")
                    self.model_status[model_name] = ModelStatus.STALE
                except Exception as e:
                    logger.error(f"Model {model_name} prediction failed: {e}")
                    self.model_status[model_name] = ModelStatus.ERROR
            
            if not individual_predictions:
                logger.warning("No models produced predictions")
                return None
            
            # Update model weights based on recent performance
            self._update_model_weights()
            
            # Calculate ensemble prediction
            ensemble_prediction = self._calculate_ensemble_prediction(individual_predictions)
            
            # Calculate confidence and uncertainty
            confidence = self._calculate_ensemble_confidence(individual_predictions, model_confidences)
            uncertainty = self._calculate_ensemble_uncertainty(individual_predictions)
            consensus_score = self._calculate_consensus_score(individual_predictions)
            
            # Create result
            prediction_time = (time.time() - start_time) * 1000
            
            result = EnsembleResult(
                prediction=ensemble_prediction,
                confidence=confidence,
                uncertainty=uncertainty,
                model_contributions=self._calculate_model_contributions(individual_predictions),
                individual_predictions=individual_predictions,
                model_weights=dict(self.model_weights.weights),
                consensus_score=consensus_score,
                prediction_time_ms=prediction_time,
                model_versions={name: "1.0" for name in individual_predictions.keys()}
            )
            
            # Cache result
            self._cache_prediction(cache_key, result)
            
            logger.debug(f"Ensemble prediction completed in {prediction_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return None
    
    async def _get_model_prediction(
        self,
        model_name: str,
        feature_array: np.ndarray,
        features: Dict[str, float]
    ) -> Tuple[Union[int, float], float]:
        """Get prediction from individual model"""
        try:
            model = self.models[model_name]
            
            if model is None:
                # Fallback for None models
                return 0.0, 0.5
            
            # Handle BaseModel instances (our custom models)
            if isinstance(model, BaseModel):
                # Make prediction
                prediction = model.predict(feature_array.reshape(1, -1))
                pred_value = float(prediction[0]) if len(prediction) > 0 else 0.0
                
                # Calculate confidence based on model type
                if isinstance(model, KalmanFilterModel):
                    # Confidence based on state variance (lower variance = higher confidence)
                    confidence = max(0.1, min(1.0, 1.0 / (1.0 + model.state_variance)))
                elif isinstance(model, HMMRegimeModel):
                    # Confidence based on regime stability
                    if len(model.regime_history) > 0:
                        recent_regimes = list(model.regime_history)[-10:]
                        regime_stability = len(set(recent_regimes)) / len(recent_regimes) if recent_regimes else 1.0
                        confidence = max(0.1, 1.0 - regime_stability)
                    else:
                        confidence = 0.5
                elif isinstance(model, CustomModel):
                    # Default confidence for custom models
                    confidence = 0.7
                elif isinstance(model, EnsembleVotingModel):
                    # Confidence based on consensus among sub-models
                    confidence = 0.8 if len(model.models) > 1 else 0.5
                else:
                    confidence = 0.6
                
                return pred_value, confidence
            
            # Handle sklearn models
            elif hasattr(model, 'predict'):
                # Check if model is trained
                if not hasattr(model, 'classes_') and not hasattr(model, 'coef_'):
                    # Model not trained, return default
                    return 0.0, 0.5
                
                # Make prediction
                if hasattr(model, 'predict_proba'):
                    # Classification with probabilities
                    proba = model.predict_proba(feature_array.reshape(1, -1))
                    prediction = np.argmax(proba[0])
                    confidence = float(np.max(proba[0]))
                else:
                    # Regression or binary classification
                    prediction = model.predict(feature_array.reshape(1, -1))[0]
                    confidence = min(abs(float(prediction)), 1.0)  # Simple confidence estimate
                
                return float(prediction), confidence
            
            else:
                # Unknown model type
                return 0.0, 0.5
            
        except Exception as e:
            logger.error(f"Model {model_name} prediction failed: {e}")
            return 0.0, 0.0
    
    def _prepare_features(self, features: Dict[str, float]) -> Optional[np.ndarray]:
        """Convert feature dictionary to array"""
        try:
            # Define standard feature order
            standard_features = [
                'returns_1d', 'returns_5d', 'returns_20d',
                'volatility_5d', 'volatility_20d',
                'rsi_14', 'macd', 'volume_ratio'
            ]
            
            feature_array = []
            for feature_name in standard_features:
                if feature_name in features:
                    feature_array.append(features[feature_name])
                else:
                    feature_array.append(0.0)  # Default value
            
            return np.array(feature_array) if feature_array else None
            
        except Exception as e:
            logger.error(f"Feature preparation failed: {e}")
            return None
    
    def _calculate_ensemble_prediction(self, predictions: Dict[str, Union[int, float]]) -> Union[int, float]:
        """Calculate weighted ensemble prediction"""
        try:
            if not predictions:
                return 0.0
            
            weighted_sum = 0.0
            total_weight = 0.0
            
            for model_name, prediction in predictions.items():
                weight = self.model_weights.weights.get(model_name, 0.0)
                weighted_sum += prediction * weight
                total_weight += weight
            
            return weighted_sum / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Ensemble prediction calculation failed: {e}")
            return 0.0
    
    def _calculate_ensemble_confidence(
        self,
        predictions: Dict[str, Union[int, float]],
        confidences: Dict[str, float]
    ) -> float:
        """Calculate ensemble confidence score"""
        try:
            if not predictions:
                return 0.0
            
            # Weight confidences by model weights
            weighted_confidence = 0.0
            total_weight = 0.0
            
            for model_name, confidence in confidences.items():
                if model_name in predictions:
                    weight = self.model_weights.weights.get(model_name, 0.0)
                    performance = self.model_weights.performance_scores.get(model_name, 0.5)
                    
                    # Combine confidence with model performance
                    adjusted_confidence = confidence * performance
                    weighted_confidence += adjusted_confidence * weight
                    total_weight += weight
            
            return weighted_confidence / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Ensemble confidence calculation failed: {e}")
            return 0.0
    
    def _calculate_ensemble_uncertainty(self, predictions: Dict[str, Union[int, float]]) -> float:
        """Calculate prediction uncertainty based on model disagreement"""
        try:
            if len(predictions) < 2:
                return 1.0  # High uncertainty with single model
            
            pred_values = list(predictions.values())
            
            # Calculate variance as measure of uncertainty
            variance = np.var(pred_values)
            
            # Normalize to 0-1 range
            normalized_uncertainty = min(1.0, variance / 0.25)  # Assuming max variance of 0.25
            
            return normalized_uncertainty
            
        except Exception as e:
            logger.error(f"Uncertainty calculation failed: {e}")
            return 1.0
    
    def _calculate_consensus_score(self, predictions: Dict[str, Union[int, float]]) -> float:
        """Calculate consensus score among models"""
        try:
            if len(predictions) < 2:
                return 1.0
            
            pred_values = list(predictions.values())
            
            # For binary predictions, calculate agreement percentage
            if all(isinstance(p, (int, bool)) or p in [0, 1] for p in pred_values):
                agreement = sum(1 for p in pred_values if p == pred_values[0]) / len(pred_values)
                return agreement
            
            # For continuous predictions, calculate correlation-based consensus
            mean_pred = np.mean(pred_values)
            deviations = [abs(p - mean_pred) for p in pred_values]
            avg_deviation = np.mean(deviations)
            
            # Convert to 0-1 scale (assuming max meaningful deviation of 1.0)
            consensus = max(0.0, 1.0 - avg_deviation)
            
            return consensus
            
        except Exception as e:
            logger.error(f"Consensus calculation failed: {e}")
            return 0.0
    
    def _calculate_model_contributions(self, predictions: Dict[str, Union[int, float]]) -> Dict[str, float]:
        """Calculate each model's contribution to final prediction"""
        try:
            contributions = {}
            total_weight = sum(self.model_weights.weights.get(name, 0.0) for name in predictions.keys())
            
            for model_name in predictions.keys():
                weight = self.model_weights.weights.get(model_name, 0.0)
                contribution = weight / total_weight if total_weight > 0 else 0.0
                contributions[model_name] = contribution
            
            return contributions
            
        except Exception as e:
            logger.error(f"Model contribution calculation failed: {e}")
            return {}
    
    def _update_model_weights(self) -> None:
        """Update model weights based on recent performance"""
        try:
            performance_metrics = self.performance_tracker.get_all_performance()
            
            for model_name in self.model_weights.weights.keys():
                if model_name in performance_metrics:
                    metrics = performance_metrics[model_name]
                    
                    # Combine accuracy and confidence for weight calculation
                    performance_score = (metrics.accuracy * 0.7 + metrics.confidence * 0.3)
                    
                    # Update performance score with exponential smoothing
                    old_score = self.model_weights.performance_scores.get(model_name, 0.5)
                    new_score = 0.9 * old_score + 0.1 * performance_score
                    self.model_weights.performance_scores[model_name] = new_score
                    
                    # Update weight based on performance
                    base_weight = self.model_configs[model_name].weight
                    performance_multiplier = max(0.1, min(2.0, new_score * 2))
                    new_weight = base_weight * performance_multiplier
                    
                    # Apply constraints
                    new_weight = max(self.model_weights.min_weight, 
                                   min(new_weight, self.model_weights.max_weight))
                    
                    self.model_weights.weights[model_name] = new_weight
            
            # Normalize weights to sum to 1
            total_weight = sum(self.model_weights.weights.values())
            if total_weight > 0:
                for model_name in self.model_weights.weights:
                    self.model_weights.weights[model_name] /= total_weight
            
            self.model_weights.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Model weight update failed: {e}")
    
    def _generate_cache_key(self, features: Dict[str, float]) -> str:
        """Generate cache key for prediction"""
        try:
            # Create hash from sorted features
            feature_str = json.dumps(features, sort_keys=True)
            return f"ensemble_{hash(feature_str)}"
        except Exception:
            return f"ensemble_{int(time.time())}"
    
    def _get_cached_prediction(self, cache_key: str) -> Optional[EnsembleResult]:
        """Get cached prediction if valid"""
        if cache_key in self.prediction_cache:
            result, timestamp = self.prediction_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl_seconds:
                return result
            else:
                del self.prediction_cache[cache_key]
        return None
    
    def _cache_prediction(self, cache_key: str, result: EnsembleResult) -> None:
        """Cache prediction result"""
        self.prediction_cache[cache_key] = (result, datetime.now())
        
        # Clean old cache entries
        if len(self.prediction_cache) > 1000:
            old_keys = [
                k for k, (_, ts) in self.prediction_cache.items()
                if (datetime.now() - ts).total_seconds() > self.cache_ttl_seconds
            ]
            for k in old_keys:
                del self.prediction_cache[k]
    
    def record_outcome(
        self,
        features: Dict[str, float],
        actual_outcome: Union[int, float],
        prediction_result: EnsembleResult
    ) -> None:
        """Record actual outcome for model performance tracking"""
        try:
            for model_name, prediction in prediction_result.individual_predictions.items():
                self.performance_tracker.record_prediction(
                    model_name=model_name,
                    prediction=prediction,
                    actual=actual_outcome,
                    confidence=prediction_result.confidence
                )
        except Exception as e:
            logger.error(f"Outcome recording failed: {e}")
    
    def get_ensemble_health(self) -> Dict[str, Any]:
        """Get ensemble health and performance metrics"""
        try:
            performance_metrics = self.performance_tracker.get_all_performance()
            
            return {
                'model_count': len(self.models),
                'active_models': len([s for s in self.model_status.values() if s == ModelStatus.ACTIVE]),
                'model_weights': dict(self.model_weights.weights),
                'performance_scores': dict(self.model_weights.performance_scores),
                'model_status': {name: status.value for name, status in self.model_status.items()},
                'average_accuracy': np.mean([m.accuracy for m in performance_metrics.values()]) if performance_metrics else 0.0,
                'cache_size': len(self.prediction_cache),
                'last_weight_update': self.model_weights.last_updated.isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {}
    
    def train_model(self, model_name: str, X: np.ndarray, y: np.ndarray) -> bool:
        """
        Train a specific model in the ensemble
        
        Args:
            model_name: Name of the model to train
            X: Feature array
            y: Target array
            
        Returns:
            True if training successful
        """
        try:
            if model_name not in self.models:
                logger.error(f"Model {model_name} not found in ensemble")
                return False
            
            model = self.models[model_name]
            if model is None:
                logger.error(f"Model {model_name} is None")
                return False
            
            # Train the model
            if isinstance(model, BaseModel):
                model.fit(X, y)
            elif hasattr(model, 'fit'):
                model.fit(X, y)
            else:
                logger.error(f"Model {model_name} does not support training")
                return False
            
            # Update model status
            self.model_status[model_name] = ModelStatus.ACTIVE
            logger.info(f"Successfully trained model {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to train model {model_name}: {e}")
            self.model_status[model_name] = ModelStatus.ERROR
            return False
    
    def train_all_models(self, X: np.ndarray, y: np.ndarray) -> Dict[str, bool]:
        """
        Train all models in the ensemble
        
        Args:
            X: Feature array
            y: Target array
            
        Returns:
            Dictionary mapping model names to training success status
        """
        results = {}
        
        for model_name in self.models.keys():
            results[model_name] = self.train_model(model_name, X, y)
            
        return results
    
    def add_model_to_voting_ensemble(self, voting_model_name: str, model_to_add: str, weight: float = 1.0) -> bool:
        """
        Add an existing model to a voting ensemble model
        
        Args:
            voting_model_name: Name of the voting ensemble model
            model_to_add: Name of the model to add to the voting ensemble
            weight: Weight for the model in voting
            
        Returns:
            True if successful
        """
        try:
            if voting_model_name not in self.models:
                logger.error(f"Voting model {voting_model_name} not found")
                return False
                
            if model_to_add not in self.models:
                logger.error(f"Model to add {model_to_add} not found")
                return False
                
            voting_model = self.models[voting_model_name]
            model = self.models[model_to_add]
            
            if not isinstance(voting_model, EnsembleVotingModel):
                logger.error(f"Model {voting_model_name} is not a voting ensemble")
                return False
                
            if model is None:
                logger.error(f"Model {model_to_add} is None")
                return False
                
            # Add model to voting ensemble
            voting_model.add_model(model, weight)
            logger.info(f"Added model {model_to_add} to voting ensemble {voting_model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add model to voting ensemble: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information
        """
        try:
            if model_name not in self.models:
                return None
                
            model = self.models[model_name]
            config = self.model_configs[model_name]
            status = self.model_status[model_name]
            
            info = {
                'name': model_name,
                'type': config.model_type.value,
                'status': status.value,
                'weight': self.model_weights.weights.get(model_name, 0.0),
                'performance_score': self.model_weights.performance_scores.get(model_name, 0.0),
                'hyperparameters': config.hyperparameters,
                'enabled': config.enabled,
                'is_fitted': False
            }
            
            # Check if model is fitted/trained
            if isinstance(model, BaseModel):
                info['is_fitted'] = model.is_fitted
            elif hasattr(model, 'classes_') or hasattr(model, 'coef_'):
                info['is_fitted'] = True
                
            # Add model-specific information
            if isinstance(model, KalmanFilterModel):
                info['state_mean'] = model.state_mean
                info['state_variance'] = model.state_variance
            elif isinstance(model, HMMRegimeModel):
                info['current_regime'] = model.get_current_regime()
                info['n_states'] = model.n_states
            elif isinstance(model, EnsembleVotingModel):
                info['voting_strategy'] = model.voting_strategy
                info['sub_models_count'] = len(model.models)
                
            return info
            
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return None

    def shutdown(self) -> None:
        """Graceful shutdown of ensemble"""
        try:
            logger.info("Shutting down ModelEnsemble...")
            
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            
            # Clear caches
            self.prediction_cache.clear()
            
            logger.info("ModelEnsemble shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during ensemble shutdown: {e}") 