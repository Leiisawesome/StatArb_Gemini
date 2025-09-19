"""
Regime Detection Engine - Regime Transition Manager
Advanced regime transition prediction, timing analysis, portfolio rebalancing
triggers, and risk adjustments during regime changes
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy import stats
from scipy.optimize import minimize
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
import seaborn as sns

# Import regime components
from .regime_detector import RegimeType, RegimeDetection, DetectionMethod
from .regime_indicators import RegimeIndicator, TransitionSignal, SignalStrength

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class TransitionPhase(Enum):
    """Regime transition phases"""
    STABLE = "stable"
    EARLY_WARNING = "early_warning"
    TRANSITION_BEGINNING = "transition_beginning"
    ACTIVE_TRANSITION = "active_transition"
    TRANSITION_COMPLETION = "transition_completion"
    CONSOLIDATION = "consolidation"


class TransitionType(Enum):
    """Types of regime transitions"""
    GRADUAL = "gradual"
    SUDDEN = "sudden"
    OSCILLATING = "oscillating"
    FAILED = "failed"
    PARTIAL = "partial"


class RebalancingTrigger(Enum):
    """Portfolio rebalancing triggers"""
    REGIME_CHANGE_CONFIRMED = "regime_change_confirmed"
    TRANSITION_PROBABILITY_HIGH = "transition_probability_high"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    STRESS_INDICATOR_ALERT = "stress_indicator_alert"
    TIME_BASED = "time_based"
    PERFORMANCE_DEVIATION = "performance_deviation"


@dataclass
class TransitionPredictionConfig:
    """Configuration for transition prediction"""
    
    # Prediction models
    prediction_horizon_days: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    model_types: List[str] = field(default_factory=lambda: ["random_forest", "gradient_boosting", "logistic"])
    
    # Feature engineering
    feature_lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 252])
    volatility_features: bool = True
    momentum_features: bool = True
    correlation_features: bool = True
    sentiment_features: bool = False
    
    # Training parameters
    min_training_samples: int = 200
    test_size: float = 0.2
    cross_validation_folds: int = 5
    
    # Prediction thresholds
    transition_probability_threshold: float = 0.7
    early_warning_threshold: float = 0.4
    confidence_threshold: float = 0.6
    
    # Risk management
    max_portfolio_adjustment: float = 0.3  # Maximum 30% adjustment
    risk_scaling_factor: float = 1.5  # Scale risk during transitions
    volatility_adjustment_factor: float = 1.2
    
    # Rebalancing triggers
    rebalancing_thresholds: Dict[RebalancingTrigger, float] = field(default_factory=lambda: {
        RebalancingTrigger.REGIME_CHANGE_CONFIRMED: 0.8,
        RebalancingTrigger.TRANSITION_PROBABILITY_HIGH: 0.7,
        RebalancingTrigger.RISK_THRESHOLD_EXCEEDED: 0.6,
        RebalancingTrigger.VOLATILITY_SPIKE: 0.8,
        RebalancingTrigger.CORRELATION_BREAKDOWN: 0.7
    })
    
    # Update frequency
    prediction_update_frequency: int = 1  # Daily
    model_retrain_frequency: int = 30  # Days


@dataclass
class TransitionPrediction:
    """Regime transition prediction"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Prediction details
    current_regime: RegimeType = RegimeType.UNKNOWN
    predicted_regime: RegimeType = RegimeType.UNKNOWN
    transition_probability: float = 0.0
    prediction_confidence: float = 0.0
    
    # Timing prediction
    predicted_transition_date: Optional[datetime] = None
    confidence_interval_days: int = 5
    transition_duration_estimate: int = 10  # Days
    
    # Transition characteristics
    transition_type: TransitionType = TransitionType.GRADUAL
    transition_phase: TransitionPhase = TransitionPhase.STABLE
    transition_intensity: float = 0.0  # 0-1 scale
    
    # Risk implications
    risk_increase_factor: float = 1.0
    volatility_increase_factor: float = 1.0
    correlation_change_factor: float = 1.0
    
    # Model metadata
    model_used: str = ""
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Supporting evidence
    supporting_indicators: List[str] = field(default_factory=list)
    contradicting_indicators: List[str] = field(default_factory=list)
    
    # Historical context
    similar_historical_transitions: int = 0
    historical_accuracy: float = 0.0


@dataclass
class RebalancingRecommendation:
    """Portfolio rebalancing recommendation"""
    
    trigger: RebalancingTrigger = RebalancingTrigger.TIME_BASED
    recommendation_timestamp: datetime = field(default_factory=datetime.now)
    
    # Rebalancing details
    urgency: SignalStrength = SignalStrength.MODERATE
    recommended_adjustments: Dict[str, float] = field(default_factory=dict)  # Asset -> weight change
    
    # Risk adjustments
    target_volatility_adjustment: float = 1.0
    position_size_adjustment: float = 1.0
    leverage_adjustment: float = 1.0
    
    # Timing recommendations
    implementation_horizon: int = 1  # Days to implement
    partial_implementation: bool = False
    staged_implementation: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk considerations
    expected_risk_increase: float = 0.0
    maximum_acceptable_risk: float = 0.0
    risk_mitigation_measures: List[str] = field(default_factory=list)
    
    # Cost considerations
    estimated_transaction_costs: float = 0.0
    cost_benefit_ratio: float = 0.0
    
    # Validation
    recommendation_confidence: float = 0.0
    alternative_recommendations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TransitionMonitoring:
    """Transition monitoring status"""
    
    monitoring_start: datetime = field(default_factory=datetime.now)
    current_phase: TransitionPhase = TransitionPhase.STABLE
    
    # Progress tracking
    transition_progress: float = 0.0  # 0-1 scale
    expected_completion_date: Optional[datetime] = None
    
    # Performance during transition
    portfolio_performance: float = 0.0
    benchmark_performance: float = 0.0
    relative_performance: float = 0.0
    
    # Risk metrics during transition
    realized_volatility: float = 0.0
    maximum_drawdown: float = 0.0
    var_95: float = 0.0
    
    # Transition quality metrics
    prediction_accuracy: float = 0.0
    timing_accuracy: float = 0.0
    risk_control_effectiveness: float = 0.0
    
    # Lessons learned
    successful_adjustments: List[str] = field(default_factory=list)
    failed_adjustments: List[str] = field(default_factory=list)
    improvement_opportunities: List[str] = field(default_factory=list)


class TransitionPredictor:
    """Predict regime transitions using machine learning"""
    
    def __init__(self, config: TransitionPredictionConfig):
        self.config = config
        self.models = {}
        self.scalers = {}
        self.is_trained = False
        self.feature_names = []
        
        logger.info("Transition predictor initialized")
    
    def train_prediction_models(self, historical_data: pd.DataFrame,
                              regime_history: pd.Series,
                              indicators_history: List[Dict[str, RegimeIndicator]]) -> Dict[str, Any]:
        """Train regime transition prediction models"""
        
        try:
            logger.info("Training transition prediction models")
            
            # Prepare training data
            features, labels = self._prepare_training_data(
                historical_data, regime_history, indicators_history
            )
            
            if features.empty or labels.empty:
                logger.error("Insufficient training data")
                return {}
            
            # Train models for different prediction horizons
            model_performances = {}
            
            for horizon in self.config.prediction_horizon_days:
                logger.info(f"Training models for {horizon}-day horizon")
                
                # Create labels for this horizon
                horizon_labels = self._create_transition_labels(regime_history, horizon)
                
                # Align features and labels
                common_index = features.index.intersection(horizon_labels.index)
                X = features.loc[common_index]
                y = horizon_labels.loc[common_index]
                
                if len(X) < self.config.min_training_samples:
                    logger.warning(f"Insufficient data for {horizon}-day horizon")
                    continue
                
                # Train models
                horizon_performances = self._train_horizon_models(X, y, horizon)
                model_performances[f'{horizon}d'] = horizon_performances
            
            self.is_trained = True
            return model_performances
            
        except Exception as e:
            logger.error(f"Error training prediction models: {e}")
            return {}
    
    def predict_transition(self, current_data: pd.DataFrame,
                         current_indicators: Dict[str, RegimeIndicator],
                         current_regime: RegimeType) -> TransitionPrediction:
        """Predict regime transition"""
        
        try:
            if not self.is_trained:
                logger.warning("Models not trained")
                return TransitionPrediction(current_regime=current_regime)
            
            # Prepare features for prediction
            features = self._extract_prediction_features(current_data, current_indicators)
            
            if features.empty:
                logger.error("No features available for prediction")
                return TransitionPrediction(current_regime=current_regime)
            
            # Get predictions from all models
            predictions = {}
            confidences = {}
            
            for horizon in self.config.prediction_horizon_days:
                horizon_key = f'{horizon}d'
                if horizon_key in self.models:
                    pred, conf = self._get_horizon_prediction(features, horizon_key)
                    predictions[horizon] = pred
                    confidences[horizon] = conf
            
            if not predictions:
                return TransitionPrediction(current_regime=current_regime)
            
            # Combine predictions
            primary_prediction = self._combine_predictions(predictions, confidences)
            
            # Create transition prediction
            transition_prediction = TransitionPrediction(
                current_regime=current_regime,
                predicted_regime=primary_prediction['regime'],
                transition_probability=primary_prediction['probability'],
                prediction_confidence=primary_prediction['confidence'],
                model_used=primary_prediction['model']
            )
            
            # Estimate timing
            transition_prediction = self._estimate_transition_timing(
                transition_prediction, predictions, confidences
            )
            
            # Assess transition characteristics
            transition_prediction = self._assess_transition_characteristics(
                transition_prediction, current_indicators
            )
            
            # Calculate risk implications
            transition_prediction = self._calculate_risk_implications(
                transition_prediction, current_indicators
            )
            
            return transition_prediction
            
        except Exception as e:
            logger.error(f"Error predicting transition: {e}")
            return TransitionPrediction(current_regime=current_regime)
    
    def _prepare_training_data(self, historical_data: pd.DataFrame,
                             regime_history: pd.Series,
                             indicators_history: List[Dict[str, RegimeIndicator]]) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data for transition prediction"""
        
        try:
            # Extract features from historical data
            features_list = []
            
            # Price-based features
            returns = historical_data.pct_change()
            
            for period in self.config.feature_lookback_periods:
                if len(returns) < period:
                    continue
                
                # Volatility features
                if self.config.volatility_features:
                    vol = returns.rolling(period).std().mean(axis=1) * np.sqrt(252)
                    features_list.append(pd.DataFrame({f'volatility_{period}d': vol}))
                
                # Momentum features
                if self.config.momentum_features:
                    momentum = returns.rolling(period).sum().mean(axis=1)
                    features_list.append(pd.DataFrame({f'momentum_{period}d': momentum}))
                
                # Correlation features
                if self.config.correlation_features and returns.shape[1] > 1:
                    corr = returns.rolling(period).corr().mean(axis=1).groupby(level=0).mean()
                    features_list.append(pd.DataFrame({f'correlation_{period}d': corr}))
            
            # Combine features
            if features_list:
                features = pd.concat(features_list, axis=1).dropna()
            else:
                features = pd.DataFrame()
            
            # Store feature names
            self.feature_names = features.columns.tolist()
            
            return features, regime_history
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return pd.DataFrame(), pd.Series()
    
    def _create_transition_labels(self, regime_history: pd.Series, horizon: int) -> pd.Series:
        """Create transition labels for given horizon"""
        
        try:
            # Create binary labels for regime transitions
            current_regime = regime_history
            future_regime = regime_history.shift(-horizon)
            
            # 1 if regime changes, 0 if stays same
            transition_labels = (current_regime != future_regime).astype(int)
            
            return transition_labels.dropna()
            
        except Exception as e:
            logger.error(f"Error creating transition labels: {e}")
            return pd.Series()
    
    def _train_horizon_models(self, X: pd.DataFrame, y: pd.Series, horizon: int) -> Dict[str, Any]:
        """Train models for specific prediction horizon"""
        
        try:
            performances = {}
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.test_size, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            self.scalers[f'{horizon}d'] = scaler
            
            # Train different model types
            for model_type in self.config.model_types:
                model = self._create_prediction_model(model_type)
                
                # Train model
                model.fit(X_train_scaled, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test_scaled)
                
                if model_type == 'logistic':
                    # Classification metrics
                    accuracy = (y_pred.round() == y_test).mean()
                    performance = {'accuracy': accuracy, 'type': 'classification'}
                else:
                    # Regression metrics
                    mse = mean_squared_error(y_test, y_pred)
                    mae = mean_absolute_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    performance = {'mse': mse, 'mae': mae, 'r2': r2, 'type': 'regression'}
                
                performances[model_type] = performance
                
                # Store model
                model_key = f'{horizon}d_{model_type}'
                self.models[model_key] = model
            
            return performances
            
        except Exception as e:
            logger.error(f"Error training horizon models: {e}")
            return {}
    
    def _create_prediction_model(self, model_type: str):
        """Create prediction model instance"""
        
        try:
            if model_type == 'random_forest':
                return RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif model_type == 'gradient_boosting':
                return GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=6,
                    random_state=42
                )
            elif model_type == 'logistic':
                return LogisticRegression(
                    random_state=42,
                    max_iter=1000
                )
            else:
                logger.warning(f"Unknown model type: {model_type}")
                return RandomForestRegressor(random_state=42)
                
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            return RandomForestRegressor(random_state=42)
    
    def _extract_prediction_features(self, current_data: pd.DataFrame,
                                   current_indicators: Dict[str, RegimeIndicator]) -> pd.DataFrame:
        """Extract features for current prediction"""
        
        try:
            features_dict = {}
            
            # Extract features similar to training
            returns = current_data.pct_change().dropna()
            
            for period in self.config.feature_lookback_periods:
                if len(returns) < period:
                    continue
                
                # Volatility features
                if self.config.volatility_features:
                    vol = returns.rolling(period).std().mean(axis=1) * np.sqrt(252)
                    features_dict[f'volatility_{period}d'] = vol.iloc[-1] if len(vol) > 0 else 0
                
                # Momentum features
                if self.config.momentum_features:
                    momentum = returns.rolling(period).sum().mean(axis=1)
                    features_dict[f'momentum_{period}d'] = momentum.iloc[-1] if len(momentum) > 0 else 0
                
                # Correlation features
                if self.config.correlation_features and returns.shape[1] > 1:
                    corr = returns.rolling(period).corr().mean()
                    features_dict[f'correlation_{period}d'] = corr if not np.isnan(corr) else 0
            
            # Create DataFrame with single row
            features = pd.DataFrame([features_dict])
            
            # Ensure all training features are present
            for feature_name in self.feature_names:
                if feature_name not in features.columns:
                    features[feature_name] = 0
            
            # Reorder columns to match training
            features = features[self.feature_names]
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting prediction features: {e}")
            return pd.DataFrame()
    
    def _get_horizon_prediction(self, features: pd.DataFrame, horizon_key: str) -> Tuple[float, float]:
        """Get prediction for specific horizon"""
        
        try:
            predictions = []
            confidences = []
            
            for model_type in self.config.model_types:
                model_key = f'{horizon_key}_{model_type}'
                
                if model_key in self.models and horizon_key in self.scalers:
                    model = self.models[model_key]
                    scaler = self.scalers[horizon_key]
                    
                    # Scale features
                    features_scaled = scaler.transform(features)
                    
                    # Get prediction
                    pred = model.predict(features_scaled)[0]
                    predictions.append(pred)
                    
                    # Estimate confidence
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(features_scaled)[0]
                        confidence = max(proba)
                    else:
                        confidence = min(1.0, max(0.0, 1 - abs(pred - 0.5) * 2))
                    
                    confidences.append(confidence)
            
            if predictions:
                avg_prediction = sum(predictions) / len(predictions)
                avg_confidence = sum(confidences) / len(confidences)
                return avg_prediction, avg_confidence
            else:
                return 0.0, 0.0
                
        except Exception as e:
            logger.error(f"Error getting horizon prediction: {e}")
            return 0.0, 0.0
    
    def _combine_predictions(self, predictions: Dict[int, float],
                           confidences: Dict[int, float]) -> Dict[str, Any]:
        """Combine predictions from different horizons"""
        
        try:
            if not predictions:
                return {
                    'regime': RegimeType.UNKNOWN,
                    'probability': 0.0,
                    'confidence': 0.0,
                    'model': 'none'
                }
            
            # Weight predictions by confidence and inverse of horizon
            weighted_sum = 0
            weight_sum = 0
            
            for horizon, prob in predictions.items():
                confidence = confidences.get(horizon, 0.5)
                weight = confidence / horizon  # Shorter horizons get more weight
                weighted_sum += prob * weight
                weight_sum += weight
            
            combined_probability = weighted_sum / weight_sum if weight_sum > 0 else 0.0
            combined_confidence = sum(confidences.values()) / len(confidences)
            
            # Determine predicted regime (simplified)
            if combined_probability > self.config.transition_probability_threshold:
                predicted_regime = RegimeType.HIGH_VOLATILITY  # Transition likely
            else:
                predicted_regime = RegimeType.LOW_VOLATILITY   # Stable regime
            
            return {
                'regime': predicted_regime,
                'probability': combined_probability,
                'confidence': combined_confidence,
                'model': 'ensemble'
            }
            
        except Exception as e:
            logger.error(f"Error combining predictions: {e}")
            return {
                'regime': RegimeType.UNKNOWN,
                'probability': 0.0,
                'confidence': 0.0,
                'model': 'error'
            }
    
    def _estimate_transition_timing(self, prediction: TransitionPrediction,
                                  predictions: Dict[int, float],
                                  confidences: Dict[int, float]) -> TransitionPrediction:
        """Estimate transition timing"""
        
        try:
            if prediction.transition_probability < self.config.early_warning_threshold:
                return prediction
            
            # Find most likely horizon
            best_horizon = None
            best_score = 0
            
            for horizon, prob in predictions.items():
                confidence = confidences.get(horizon, 0.5)
                score = prob * confidence
                
                if score > best_score:
                    best_score = score
                    best_horizon = horizon
            
            if best_horizon:
                prediction.predicted_transition_date = datetime.now() + timedelta(days=best_horizon)
                prediction.confidence_interval_days = max(2, best_horizon // 3)
                prediction.transition_duration_estimate = max(5, best_horizon // 2)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error estimating transition timing: {e}")
            return prediction
    
    def _assess_transition_characteristics(self, prediction: TransitionPrediction,
                                         indicators: Dict[str, RegimeIndicator]) -> TransitionPrediction:
        """Assess transition characteristics"""
        
        try:
            # Determine transition type based on indicators
            volatility_indicators = [ind for ind in indicators.values() 
                                   if 'volatility' in ind.name.lower()]
            
            if volatility_indicators:
                avg_vol_signal = sum(ind.signal_direction for ind in volatility_indicators) / len(volatility_indicators)
                
                if abs(avg_vol_signal) > 0.8:
                    prediction.transition_type = TransitionType.SUDDEN
                elif abs(avg_vol_signal) > 0.3:
                    prediction.transition_type = TransitionType.GRADUAL
                else:
                    prediction.transition_type = TransitionType.OSCILLATING
            
            # Determine transition phase
            if prediction.transition_probability > self.config.transition_probability_threshold:
                prediction.transition_phase = TransitionPhase.ACTIVE_TRANSITION
            elif prediction.transition_probability > self.config.early_warning_threshold:
                prediction.transition_phase = TransitionPhase.EARLY_WARNING
            else:
                prediction.transition_phase = TransitionPhase.STABLE
            
            # Calculate transition intensity
            prediction.transition_intensity = min(1.0, prediction.transition_probability * prediction.prediction_confidence)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error assessing transition characteristics: {e}")
            return prediction
    
    def _calculate_risk_implications(self, prediction: TransitionPrediction,
                                   indicators: Dict[str, RegimeIndicator]) -> TransitionPrediction:
        """Calculate risk implications of transition"""
        
        try:
            base_risk_increase = 1.0
            
            # Risk increase based on transition probability
            if prediction.transition_probability > 0.8:
                base_risk_increase = self.config.risk_scaling_factor
            elif prediction.transition_probability > 0.6:
                base_risk_increase = 1 + (self.config.risk_scaling_factor - 1) * 0.5
            
            # Additional risk from volatility indicators
            vol_indicators = [ind for ind in indicators.values() if 'volatility' in ind.name.lower()]
            if vol_indicators:
                avg_vol_strength = sum(ind.confidence for ind in vol_indicators) / len(vol_indicators)
                base_risk_increase *= (1 + avg_vol_strength * 0.5)
            
            prediction.risk_increase_factor = base_risk_increase
            prediction.volatility_increase_factor = base_risk_increase * self.config.volatility_adjustment_factor
            
            # Correlation change factor
            correlation_indicators = [ind for ind in indicators.values() if 'correlation' in ind.name.lower()]
            if correlation_indicators:
                avg_corr_signal = sum(ind.signal_direction for ind in correlation_indicators) / len(correlation_indicators)
                prediction.correlation_change_factor = 1 + abs(avg_corr_signal) * 0.3
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error calculating risk implications: {e}")
            return prediction


class RebalancingManager:
    """Manage portfolio rebalancing during regime transitions"""
    
    def __init__(self, config: TransitionPredictionConfig):
        self.config = config
        
        logger.info("Rebalancing manager initialized")
    
    def generate_rebalancing_recommendations(self, transition_prediction: TransitionPrediction,
                                           current_portfolio: Dict[str, float],
                                           indicators: Dict[str, RegimeIndicator]) -> List[RebalancingRecommendation]:
        """Generate rebalancing recommendations"""
        
        try:
            recommendations = []
            
            # Check each trigger type
            for trigger in RebalancingTrigger:
                recommendation = self._evaluate_trigger(
                    trigger, transition_prediction, current_portfolio, indicators
                )
                
                if recommendation:
                    recommendations.append(recommendation)
            
            # Sort by urgency
            recommendations.sort(key=lambda x: self._get_urgency_score(x.urgency), reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating rebalancing recommendations: {e}")
            return []
    
    def _evaluate_trigger(self, trigger: RebalancingTrigger,
                         transition_prediction: TransitionPrediction,
                         current_portfolio: Dict[str, float],
                         indicators: Dict[str, RegimeIndicator]) -> Optional[RebalancingRecommendation]:
        """Evaluate specific rebalancing trigger"""
        
        try:
            threshold = self.config.rebalancing_thresholds.get(trigger, 0.5)
            
            if trigger == RebalancingTrigger.REGIME_CHANGE_CONFIRMED:
                if transition_prediction.transition_probability > threshold:
                    return self._create_regime_change_recommendation(transition_prediction, current_portfolio)
            
            elif trigger == RebalancingTrigger.TRANSITION_PROBABILITY_HIGH:
                if (transition_prediction.transition_probability > threshold and 
                    transition_prediction.prediction_confidence > self.config.confidence_threshold):
                    return self._create_probability_based_recommendation(transition_prediction, current_portfolio)
            
            elif trigger == RebalancingTrigger.RISK_THRESHOLD_EXCEEDED:
                if transition_prediction.risk_increase_factor > threshold:
                    return self._create_risk_based_recommendation(transition_prediction, current_portfolio)
            
            elif trigger == RebalancingTrigger.VOLATILITY_SPIKE:
                vol_indicators = [ind for ind in indicators.values() if 'volatility' in ind.name.lower()]
                if vol_indicators:
                    max_vol_signal = max(ind.confidence for ind in vol_indicators)
                    if max_vol_signal > threshold:
                        return self._create_volatility_based_recommendation(transition_prediction, current_portfolio)
            
            elif trigger == RebalancingTrigger.CORRELATION_BREAKDOWN:
                corr_indicators = [ind for ind in indicators.values() if 'correlation' in ind.name.lower()]
                if corr_indicators:
                    max_corr_signal = max(abs(ind.signal_direction) * ind.confidence for ind in corr_indicators)
                    if max_corr_signal > threshold:
                        return self._create_correlation_based_recommendation(transition_prediction, current_portfolio)
            
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating trigger {trigger}: {e}")
            return None
    
    def _create_regime_change_recommendation(self, prediction: TransitionPrediction,
                                           portfolio: Dict[str, float]) -> RebalancingRecommendation:
        """Create regime change rebalancing recommendation"""
        
        try:
            # Conservative adjustment based on regime change
            adjustment_magnitude = min(
                self.config.max_portfolio_adjustment,
                prediction.transition_probability * 0.3
            )
            
            # Reduce risk positions during transition
            adjustments = {}
            for asset, weight in portfolio.items():
                if weight > 0.1:  # Only adjust significant positions
                    adjustments[asset] = -adjustment_magnitude * weight
            
            return RebalancingRecommendation(
                trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED,
                urgency=SignalStrength.STRONG,
                recommended_adjustments=adjustments,
                target_volatility_adjustment=prediction.volatility_increase_factor,
                position_size_adjustment=1 / prediction.risk_increase_factor,
                implementation_horizon=2,
                expected_risk_increase=prediction.risk_increase_factor - 1,
                recommendation_confidence=prediction.prediction_confidence
            )
            
        except Exception as e:
            logger.error(f"Error creating regime change recommendation: {e}")
            return RebalancingRecommendation(trigger=RebalancingTrigger.REGIME_CHANGE_CONFIRMED)
    
    def _create_probability_based_recommendation(self, prediction: TransitionPrediction,
                                               portfolio: Dict[str, float]) -> RebalancingRecommendation:
        """Create probability-based rebalancing recommendation"""
        
        try:
            # Gradual adjustment based on probability
            prob_factor = (prediction.transition_probability - 0.5) * 2  # Scale to 0-1
            adjustment_magnitude = prob_factor * self.config.max_portfolio_adjustment * 0.5
            
            adjustments = {}
            for asset, weight in portfolio.items():
                if weight > 0.05:
                    adjustments[asset] = -adjustment_magnitude * weight * 0.5
            
            return RebalancingRecommendation(
                trigger=RebalancingTrigger.TRANSITION_PROBABILITY_HIGH,
                urgency=SignalStrength.MODERATE,
                recommended_adjustments=adjustments,
                target_volatility_adjustment=1 + prob_factor * 0.2,
                position_size_adjustment=1 - prob_factor * 0.1,
                implementation_horizon=3,
                partial_implementation=True,
                recommendation_confidence=prediction.prediction_confidence
            )
            
        except Exception as e:
            logger.error(f"Error creating probability-based recommendation: {e}")
            return RebalancingRecommendation(trigger=RebalancingTrigger.TRANSITION_PROBABILITY_HIGH)
    
    def _create_risk_based_recommendation(self, prediction: TransitionPrediction,
                                        portfolio: Dict[str, float]) -> RebalancingRecommendation:
        """Create risk-based rebalancing recommendation"""
        
        try:
            # Focus on risk reduction
            risk_factor = prediction.risk_increase_factor - 1
            
            adjustments = {}
            for asset, weight in portfolio.items():
                # Reduce higher-risk positions more
                risk_reduction = min(0.3, risk_factor * weight)
                adjustments[asset] = -risk_reduction
            
            return RebalancingRecommendation(
                trigger=RebalancingTrigger.RISK_THRESHOLD_EXCEEDED,
                urgency=SignalStrength.VERY_STRONG,
                recommended_adjustments=adjustments,
                target_volatility_adjustment=prediction.volatility_increase_factor,
                position_size_adjustment=1 / prediction.risk_increase_factor,
                leverage_adjustment=1 / prediction.risk_increase_factor,
                implementation_horizon=1,
                expected_risk_increase=risk_factor,
                risk_mitigation_measures=["Reduce position sizes", "Increase cash allocation", "Add hedging"],
                recommendation_confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error creating risk-based recommendation: {e}")
            return RebalancingRecommendation(trigger=RebalancingTrigger.RISK_THRESHOLD_EXCEEDED)
    
    def _create_volatility_based_recommendation(self, prediction: TransitionPrediction,
                                              portfolio: Dict[str, float]) -> RebalancingRecommendation:
        """Create volatility-based rebalancing recommendation"""
        
        try:
            vol_factor = prediction.volatility_increase_factor - 1
            
            adjustments = {}
            for asset, weight in portfolio.items():
                vol_adjustment = min(0.2, vol_factor * weight * 0.5)
                adjustments[asset] = -vol_adjustment
            
            return RebalancingRecommendation(
                trigger=RebalancingTrigger.VOLATILITY_SPIKE,
                urgency=SignalStrength.STRONG,
                recommended_adjustments=adjustments,
                target_volatility_adjustment=1 / prediction.volatility_increase_factor,
                implementation_horizon=1,
                risk_mitigation_measures=["Reduce volatility exposure", "Increase defensive positions"],
                recommendation_confidence=0.7
            )
            
        except Exception as e:
            logger.error(f"Error creating volatility-based recommendation: {e}")
            return RebalancingRecommendation(trigger=RebalancingTrigger.VOLATILITY_SPIKE)
    
    def _create_correlation_based_recommendation(self, prediction: TransitionPrediction,
                                               portfolio: Dict[str, float]) -> RebalancingRecommendation:
        """Create correlation-based rebalancing recommendation"""
        
        try:
            corr_factor = prediction.correlation_change_factor - 1
            
            adjustments = {}
            for asset, weight in portfolio.items():
                # Diversification adjustment
                corr_adjustment = min(0.15, corr_factor * weight * 0.3)
                adjustments[asset] = -corr_adjustment
            
            return RebalancingRecommendation(
                trigger=RebalancingTrigger.CORRELATION_BREAKDOWN,
                urgency=SignalStrength.MODERATE,
                recommended_adjustments=adjustments,
                implementation_horizon=2,
                risk_mitigation_measures=["Improve diversification", "Add uncorrelated assets"],
                recommendation_confidence=0.6
            )
            
        except Exception as e:
            logger.error(f"Error creating correlation-based recommendation: {e}")
            return RebalancingRecommendation(trigger=RebalancingTrigger.CORRELATION_BREAKDOWN)
    
    def _get_urgency_score(self, urgency: SignalStrength) -> int:
        """Get numeric urgency score"""
        
        urgency_map = {
            SignalStrength.VERY_WEAK: 1,
            SignalStrength.WEAK: 2,
            SignalStrength.MODERATE: 3,
            SignalStrength.STRONG: 4,
            SignalStrength.VERY_STRONG: 5
        }
        
        return urgency_map.get(urgency, 3)


class TransitionMonitor:
    """Monitor ongoing regime transitions"""
    
    def __init__(self, config: TransitionPredictionConfig):
        self.config = config
        self.active_transitions: Dict[str, TransitionMonitoring] = {}
        
        logger.info("Transition monitor initialized")
    
    def start_transition_monitoring(self, transition_id: str,
                                  prediction: TransitionPrediction) -> TransitionMonitoring:
        """Start monitoring a regime transition"""
        
        try:
            monitoring = TransitionMonitoring(
                monitoring_start=datetime.now(),
                current_phase=prediction.transition_phase,
                expected_completion_date=prediction.predicted_transition_date
            )
            
            self.active_transitions[transition_id] = monitoring
            
            logger.info(f"Started monitoring transition {transition_id}")
            return monitoring
            
        except Exception as e:
            logger.error(f"Error starting transition monitoring: {e}")
            return TransitionMonitoring()
    
    def update_transition_monitoring(self, transition_id: str,
                                   current_regime: RegimeType,
                                   portfolio_performance: float,
                                   benchmark_performance: float,
                                   realized_volatility: float) -> Optional[TransitionMonitoring]:
        """Update transition monitoring"""
        
        try:
            if transition_id not in self.active_transitions:
                logger.warning(f"No active monitoring for transition {transition_id}")
                return None
            
            monitoring = self.active_transitions[transition_id]
            
            # Update performance metrics
            monitoring.portfolio_performance = portfolio_performance
            monitoring.benchmark_performance = benchmark_performance
            monitoring.relative_performance = portfolio_performance - benchmark_performance
            monitoring.realized_volatility = realized_volatility
            
            # Update transition progress (simplified)
            days_elapsed = (datetime.now() - monitoring.monitoring_start).days
            
            if monitoring.expected_completion_date:
                total_days = (monitoring.expected_completion_date - monitoring.monitoring_start).days
                monitoring.transition_progress = min(1.0, days_elapsed / max(1, total_days))
            else:
                monitoring.transition_progress = min(1.0, days_elapsed / 30)  # 30-day default
            
            # Update phase based on progress
            if monitoring.transition_progress > 0.9:
                monitoring.current_phase = TransitionPhase.CONSOLIDATION
            elif monitoring.transition_progress > 0.7:
                monitoring.current_phase = TransitionPhase.TRANSITION_COMPLETION
            elif monitoring.transition_progress > 0.3:
                monitoring.current_phase = TransitionPhase.ACTIVE_TRANSITION
            elif monitoring.transition_progress > 0.1:
                monitoring.current_phase = TransitionPhase.TRANSITION_BEGINNING
            
            return monitoring
            
        except Exception as e:
            logger.error(f"Error updating transition monitoring: {e}")
            return None
    
    def complete_transition_monitoring(self, transition_id: str,
                                     final_regime: RegimeType) -> Optional[TransitionMonitoring]:
        """Complete transition monitoring and generate lessons learned"""
        
        try:
            if transition_id not in self.active_transitions:
                return None
            
            monitoring = self.active_transitions[transition_id]
            monitoring.current_phase = TransitionPhase.CONSOLIDATION
            monitoring.transition_progress = 1.0
            
            # Calculate final metrics
            self._calculate_final_metrics(monitoring)
            
            # Generate lessons learned
            self._generate_lessons_learned(monitoring)
            
            # Remove from active monitoring
            completed_monitoring = self.active_transitions.pop(transition_id)
            
            logger.info(f"Completed monitoring for transition {transition_id}")
            return completed_monitoring
            
        except Exception as e:
            logger.error(f"Error completing transition monitoring: {e}")
            return None
    
    def _calculate_final_metrics(self, monitoring: TransitionMonitoring):
        """Calculate final performance metrics"""
        
        try:
            # Risk control effectiveness
            target_vol = 0.15  # Example target
            if monitoring.realized_volatility <= target_vol * 1.2:
                monitoring.risk_control_effectiveness = 0.8
            elif monitoring.realized_volatility <= target_vol * 1.5:
                monitoring.risk_control_effectiveness = 0.6
            else:
                monitoring.risk_control_effectiveness = 0.4
            
            # Performance assessment
            if monitoring.relative_performance > 0:
                monitoring.prediction_accuracy = 0.8
            elif monitoring.relative_performance > -0.02:
                monitoring.prediction_accuracy = 0.6
            else:
                monitoring.prediction_accuracy = 0.4
            
        except Exception as e:
            logger.error(f"Error calculating final metrics: {e}")
    
    def _generate_lessons_learned(self, monitoring: TransitionMonitoring):
        """Generate lessons learned from transition"""
        
        try:
            # Successful adjustments
            if monitoring.relative_performance > 0:
                monitoring.successful_adjustments.append("Effective risk management during transition")
            
            if monitoring.risk_control_effectiveness > 0.7:
                monitoring.successful_adjustments.append("Good volatility control")
            
            # Failed adjustments
            if monitoring.relative_performance < -0.05:
                monitoring.failed_adjustments.append("Underperformed during transition")
            
            if monitoring.realized_volatility > 0.25:
                monitoring.failed_adjustments.append("Excessive volatility realized")
            
            # Improvement opportunities
            if monitoring.prediction_accuracy < 0.6:
                monitoring.improvement_opportunities.append("Improve transition timing prediction")
            
            if monitoring.risk_control_effectiveness < 0.7:
                monitoring.improvement_opportunities.append("Enhance risk management during transitions")
            
        except Exception as e:
            logger.error(f"Error generating lessons learned: {e}")


class RegimeTransitionManager:
    """
    Comprehensive Regime Transition Manager
    
    Integrates transition prediction, rebalancing management, and monitoring
    to provide comprehensive regime transition management capabilities.
    """
    
    def __init__(self, config: Optional[TransitionPredictionConfig] = None):
        """Initialize regime transition manager"""
        
        self.config = config or TransitionPredictionConfig()
        
        # Initialize components
        self.predictor = TransitionPredictor(self.config)
        self.rebalancing_manager = RebalancingManager(self.config)
        self.monitor = TransitionMonitor(self.config)
        
        # Transition history
        self.prediction_history: List[TransitionPrediction] = []
        self.rebalancing_history: List[RebalancingRecommendation] = []
        
        logger.info("Regime transition manager initialized")
    
    def train_transition_models(self, historical_data: pd.DataFrame,
                              regime_history: pd.Series,
                              indicators_history: List[Dict[str, RegimeIndicator]]) -> Dict[str, Any]:
        """Train transition prediction models"""
        
        try:
            return self.predictor.train_prediction_models(
                historical_data, regime_history, indicators_history
            )
            
        except Exception as e:
            logger.error(f"Error training transition models: {e}")
            return {}
    
    def analyze_transition_opportunity(self, current_data: pd.DataFrame,
                                     current_indicators: Dict[str, RegimeIndicator],
                                     current_regime: RegimeType,
                                     current_portfolio: Dict[str, float]) -> Dict[str, Any]:
        """Analyze current transition opportunity"""
        
        try:
            logger.info("Analyzing regime transition opportunity")
            
            # Get transition prediction
            prediction = self.predictor.predict_transition(
                current_data, current_indicators, current_regime
            )
            
            # Generate rebalancing recommendations
            recommendations = self.rebalancing_manager.generate_rebalancing_recommendations(
                prediction, current_portfolio, current_indicators
            )
            
            # Store in history
            self.prediction_history.append(prediction)
            self.rebalancing_history.extend(recommendations)
            
            # Limit history size
            if len(self.prediction_history) > 100:
                self.prediction_history = self.prediction_history[-50:]
            
            if len(self.rebalancing_history) > 200:
                self.rebalancing_history = self.rebalancing_history[-100:]
            
            # Create comprehensive analysis
            analysis = {
                'timestamp': datetime.now(),
                'transition_prediction': prediction,
                'rebalancing_recommendations': recommendations,
                'risk_assessment': self._assess_transition_risks(prediction, current_indicators),
                'implementation_guidance': self._create_implementation_guidance(recommendations),
                'monitoring_setup': self._setup_monitoring_guidance(prediction)
            }
            
            logger.info("Transition opportunity analysis completed")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing transition opportunity: {e}")
            return {}
    
    def _assess_transition_risks(self, prediction: TransitionPrediction,
                               indicators: Dict[str, RegimeIndicator]) -> Dict[str, Any]:
        """Assess risks during transition"""
        
        try:
            risk_assessment = {
                'overall_risk_level': 'moderate',
                'primary_risks': [],
                'risk_factors': {},
                'mitigation_strategies': []
            }
            
            # Overall risk level
            if prediction.risk_increase_factor > 1.5:
                risk_assessment['overall_risk_level'] = 'high'
            elif prediction.risk_increase_factor > 1.2:
                risk_assessment['overall_risk_level'] = 'moderate'
            else:
                risk_assessment['overall_risk_level'] = 'low'
            
            # Primary risks
            if prediction.volatility_increase_factor > 1.3:
                risk_assessment['primary_risks'].append('volatility_spike')
            
            if prediction.correlation_change_factor > 1.2:
                risk_assessment['primary_risks'].append('correlation_breakdown')
            
            if prediction.transition_intensity > 0.8:
                risk_assessment['primary_risks'].append('sudden_regime_change')
            
            # Risk factors
            risk_assessment['risk_factors'] = {
                'volatility_risk': prediction.volatility_increase_factor - 1,
                'correlation_risk': prediction.correlation_change_factor - 1,
                'timing_risk': 1 - prediction.prediction_confidence,
                'transition_risk': prediction.transition_intensity
            }
            
            # Mitigation strategies
            if prediction.volatility_increase_factor > 1.2:
                risk_assessment['mitigation_strategies'].append('Reduce position sizes')
                risk_assessment['mitigation_strategies'].append('Increase cash allocation')
            
            if prediction.correlation_change_factor > 1.1:
                risk_assessment['mitigation_strategies'].append('Enhance diversification')
                risk_assessment['mitigation_strategies'].append('Add uncorrelated assets')
            
            if prediction.prediction_confidence < 0.7:
                risk_assessment['mitigation_strategies'].append('Implement gradual adjustments')
                risk_assessment['mitigation_strategies'].append('Monitor closely for confirmation')
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error assessing transition risks: {e}")
            return {}
    
    def _create_implementation_guidance(self, recommendations: List[RebalancingRecommendation]) -> Dict[str, Any]:
        """Create implementation guidance"""
        
        try:
            if not recommendations:
                return {'status': 'no_action_required'}
            
            # Sort by urgency
            urgent_recommendations = [rec for rec in recommendations 
                                    if rec.urgency in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]
            
            guidance = {
                'immediate_actions': [],
                'phased_implementation': [],
                'monitoring_requirements': [],
                'success_criteria': []
            }
            
            # Immediate actions
            for rec in urgent_recommendations[:3]:  # Top 3 urgent
                guidance['immediate_actions'].append({
                    'trigger': rec.trigger.value,
                    'adjustments': rec.recommended_adjustments,
                    'timeline': f"{rec.implementation_horizon} days"
                })
            
            # Phased implementation
            moderate_recommendations = [rec for rec in recommendations 
                                      if rec.urgency == SignalStrength.MODERATE]
            
            for i, rec in enumerate(moderate_recommendations):
                guidance['phased_implementation'].append({
                    'phase': i + 1,
                    'trigger': rec.trigger.value,
                    'adjustments': rec.recommended_adjustments,
                    'timeline': f"{rec.implementation_horizon + i} days"
                })
            
            # Monitoring requirements
            guidance['monitoring_requirements'] = [
                'Track portfolio volatility daily',
                'Monitor regime indicators for confirmation',
                'Assess relative performance vs benchmark',
                'Watch for additional transition signals'
            ]
            
            # Success criteria
            guidance['success_criteria'] = [
                'Volatility remains within target range',
                'Relative performance maintained or improved',
                'Risk metrics stay within acceptable bounds',
                'Transition prediction accuracy validated'
            ]
            
            return guidance
            
        except Exception as e:
            logger.error(f"Error creating implementation guidance: {e}")
            return {}
    
    def _setup_monitoring_guidance(self, prediction: TransitionPrediction) -> Dict[str, Any]:
        """Setup monitoring guidance"""
        
        try:
            monitoring_guidance = {
                'monitoring_duration': 30,  # Days
                'key_metrics': [],
                'alert_thresholds': {},
                'review_schedule': []
            }
            
            # Monitoring duration based on prediction
            if prediction.predicted_transition_date:
                days_to_transition = (prediction.predicted_transition_date - datetime.now()).days
                monitoring_guidance['monitoring_duration'] = max(30, days_to_transition + 10)
            
            # Key metrics to monitor
            monitoring_guidance['key_metrics'] = [
                'portfolio_volatility',
                'relative_performance',
                'regime_indicators',
                'transition_probability',
                'correlation_structure'
            ]
            
            # Alert thresholds
            monitoring_guidance['alert_thresholds'] = {
                'volatility_threshold': prediction.volatility_increase_factor * 1.2,
                'drawdown_threshold': -0.05,
                'correlation_threshold': prediction.correlation_change_factor * 1.1,
                'regime_probability_threshold': 0.8
            }
            
            # Review schedule
            if prediction.transition_intensity > 0.7:
                monitoring_guidance['review_schedule'] = ['daily', 'weekly_detailed']
            elif prediction.transition_intensity > 0.4:
                monitoring_guidance['review_schedule'] = ['every_2_days', 'weekly_detailed']
            else:
                monitoring_guidance['review_schedule'] = ['weekly', 'monthly_detailed']
            
            return monitoring_guidance
            
        except Exception as e:
            logger.error(f"Error setting up monitoring guidance: {e}")
            return {}
    
    def start_transition_monitoring(self, transition_id: str,
                                  prediction: TransitionPrediction) -> TransitionMonitoring:
        """Start monitoring a transition"""
        
        return self.monitor.start_transition_monitoring(transition_id, prediction)
    
    def update_transition_monitoring(self, transition_id: str,
                                   current_regime: RegimeType,
                                   portfolio_performance: float,
                                   benchmark_performance: float,
                                   realized_volatility: float) -> Optional[TransitionMonitoring]:
        """Update transition monitoring"""
        
        return self.monitor.update_transition_monitoring(
            transition_id, current_regime, portfolio_performance,
            benchmark_performance, realized_volatility
        )
    
    def get_transition_summary(self) -> Dict[str, Any]:
        """Get summary of recent transitions"""
        
        try:
            if not self.prediction_history:
                return {'status': 'no_recent_predictions'}
            
            recent_predictions = self.prediction_history[-10:]
            recent_recommendations = self.rebalancing_history[-20:]
            
            summary = {
                'recent_predictions': len(recent_predictions),
                'average_transition_probability': sum(p.transition_probability for p in recent_predictions) / len(recent_predictions),
                'average_confidence': sum(p.prediction_confidence for p in recent_predictions) / len(recent_predictions),
                'most_common_predicted_regime': self._get_most_common_regime(recent_predictions),
                'rebalancing_triggers': self._summarize_triggers(recent_recommendations),
                'active_monitoring': len(self.monitor.active_transitions)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating transition summary: {e}")
            return {}
    
    def _get_most_common_regime(self, predictions: List[TransitionPrediction]) -> str:
        """Get most commonly predicted regime"""
        
        try:
            regime_counts = {}
            for pred in predictions:
                regime = pred.predicted_regime.value
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            if regime_counts:
                return max(regime_counts.keys(), key=lambda x: regime_counts[x])
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error getting most common regime: {e}")
            return "unknown"
    
    def _summarize_triggers(self, recommendations: List[RebalancingRecommendation]) -> Dict[str, int]:
        """Summarize rebalancing triggers"""
        
        try:
            trigger_counts = {}
            for rec in recommendations:
                trigger = rec.trigger.value
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
            
            return trigger_counts
            
        except Exception as e:
            logger.error(f"Error summarizing triggers: {e}")
            return {}