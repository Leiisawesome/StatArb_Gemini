"""
Regime Detection Engine - Advanced Regime Classifier
Machine learning-based regime classification with feature engineering,
model selection, and prediction confidence assessment
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from sklearn.ensemble import (RandomForestClassifier, GradientBoostingClassifier, 
                            VotingClassifier, AdaBoostClassifier)
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import (train_test_split, cross_val_score, 
                                   GridSearchCV, TimeSeriesSplit)
from sklearn.preprocessing import StandardScaler, LabelEncoder, RobustScaler
from sklearn.metrics import (classification_report, confusion_matrix, 
                           accuracy_score, precision_recall_fscore_support,
                           roc_auc_score, log_loss)
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.calibration import CalibratedClassifierCV
import joblib
from scipy import stats
from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
import seaborn as sns

# Import regime components
from .regime_detector import RegimeType, RegimeDetection, DetectionMethod

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MLModel(Enum):
    """Machine learning model types"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    SVM = "svm"
    NEURAL_NETWORK = "neural_network"
    LOGISTIC_REGRESSION = "logistic_regression"
    NAIVE_BAYES = "naive_bayes"
    ENSEMBLE = "ensemble"


class FeatureType(Enum):
    """Feature engineering types"""
    PRICE_BASED = "price_based"
    VOLATILITY_BASED = "volatility_based"
    MOMENTUM_BASED = "momentum_based"
    CORRELATION_BASED = "correlation_based"
    VOLUME_BASED = "volume_based"
    TECHNICAL_INDICATORS = "technical_indicators"
    MACRO_INDICATORS = "macro_indicators"
    SENTIMENT_INDICATORS = "sentiment_indicators"


@dataclass
class ClassificationConfig:
    """Configuration for regime classification"""
    
    # Model selection
    primary_model: MLModel = MLModel.ENSEMBLE
    models_to_test: List[MLModel] = field(default_factory=lambda: [
        MLModel.RANDOM_FOREST, MLModel.GRADIENT_BOOSTING, 
        MLModel.SVM, MLModel.LOGISTIC_REGRESSION
    ])
    
    # Feature engineering
    feature_types: List[FeatureType] = field(default_factory=lambda: [
        FeatureType.PRICE_BASED, FeatureType.VOLATILITY_BASED,
        FeatureType.MOMENTUM_BASED, FeatureType.CORRELATION_BASED
    ])
    
    # Data parameters
    lookback_windows: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 252])
    min_training_samples: int = 100  # Reduced for testing with limited data
    test_size: float = 0.2
    validation_splits: int = 5
    
    # Feature selection
    max_features: int = 50
    feature_selection_method: str = "mutual_info"  # 'mutual_info', 'f_classif', 'variance'
    correlation_threshold: float = 0.95  # Remove highly correlated features
    
    # Model parameters
    use_class_weights: bool = True
    calibrate_probabilities: bool = True
    cross_validation_method: str = "time_series"  # 'time_series', 'stratified'
    
    # Performance thresholds
    min_accuracy: float = 0.65
    min_precision: float = 0.60
    min_recall: float = 0.60
    
    # Prediction parameters
    confidence_threshold: float = 0.7
    prediction_horizon: int = 20  # Days to predict ahead
    
    # Update frequency
    retrain_frequency: int = 60  # Days between retraining
    incremental_learning: bool = False


@dataclass
class FeatureImportance:
    """Feature importance analysis"""
    
    feature_name: str = ""
    importance_score: float = 0.0
    importance_rank: int = 0
    
    # Feature statistics
    mean_value: float = 0.0
    std_value: float = 0.0
    correlation_with_target: float = 0.0
    
    # Regime-specific importance
    regime_specific_importance: Dict[str, float] = field(default_factory=dict)


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    
    model_name: str = ""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Cross-validation scores
    cv_accuracy_mean: float = 0.0
    cv_accuracy_std: float = 0.0
    
    # Regime-specific performance
    regime_specific_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Confusion matrix
    confusion_matrix: Optional[np.ndarray] = None
    
    # Feature importance
    feature_importances: List[FeatureImportance] = field(default_factory=list)
    
    # Training metadata
    training_samples: int = 0
    training_time: float = 0.0
    last_trained: Optional[datetime] = None


@dataclass
class RegimeClassification:
    """Regime classification result"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Primary prediction
    predicted_regime: RegimeType = RegimeType.UNKNOWN
    prediction_confidence: float = 0.0
    
    # All regime probabilities
    regime_probabilities: Dict[RegimeType, float] = field(default_factory=dict)
    
    # Alternative predictions
    top_3_regimes: List[Tuple[RegimeType, float]] = field(default_factory=list)
    
    # Feature contributions
    feature_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Model metadata
    model_used: MLModel = MLModel.ENSEMBLE
    model_confidence: float = 0.0
    
    # Historical context
    regime_stability: float = 0.0
    recent_regime_changes: int = 0
    
    # Prediction horizon
    prediction_horizon_days: int = 1
    prediction_decay: float = 1.0  # Confidence decay over time


class FeatureEngineer:
    """Advanced feature engineering for regime classification"""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        
        logger.info("Feature engineer initialized")
    
    def engineer_features(self, price_data: pd.DataFrame,
                         volume_data: Optional[pd.DataFrame] = None,
                         additional_data: Optional[Dict[str, pd.DataFrame]] = None) -> pd.DataFrame:
        """Engineer comprehensive feature set"""
        
        try:
            features_list = []
            
            # Price-based features
            if FeatureType.PRICE_BASED in self.config.feature_types:
                price_features = self._create_price_features(price_data)
                features_list.append(price_features)
            
            # Volatility-based features
            if FeatureType.VOLATILITY_BASED in self.config.feature_types:
                volatility_features = self._create_volatility_features(price_data)
                features_list.append(volatility_features)
            
            # Momentum-based features
            if FeatureType.MOMENTUM_BASED in self.config.feature_types:
                momentum_features = self._create_momentum_features(price_data)
                features_list.append(momentum_features)
            
            # Correlation-based features
            if FeatureType.CORRELATION_BASED in self.config.feature_types:
                correlation_features = self._create_correlation_features(price_data)
                features_list.append(correlation_features)
            
            # Volume-based features
            if FeatureType.VOLUME_BASED in self.config.feature_types and volume_data is not None:
                volume_features = self._create_volume_features(price_data, volume_data)
                features_list.append(volume_features)
            
            # Technical indicators
            if FeatureType.TECHNICAL_INDICATORS in self.config.feature_types:
                technical_features = self._create_technical_indicators(price_data)
                features_list.append(technical_features)
            
            # Combine all features
            if not features_list:
                return pd.DataFrame()
            
            combined_features = pd.concat(features_list, axis=1)
            
            # Remove highly correlated features
            combined_features = self._remove_correlated_features(combined_features)
            
            # Forward fill and drop NaN
            combined_features = combined_features.ffill().dropna()
            
            logger.info(f"Engineered {len(combined_features.columns)} features")
            return combined_features
            
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return pd.DataFrame()
    
    def _create_price_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features"""
        
        try:
            features = {}
            
            # Calculate returns
            returns = price_data.pct_change()
            
            for window in self.config.lookback_windows:
                if len(price_data) < window:
                    continue
                
                # Price momentum
                features[f'price_momentum_{window}d'] = (price_data.iloc[-1] / price_data.shift(window) - 1).mean(axis=1)
                
                # Price range
                features[f'price_range_{window}d'] = (price_data.rolling(window).max() / price_data.rolling(window).min() - 1).mean(axis=1)
                
                # Return statistics
                features[f'return_mean_{window}d'] = returns.rolling(window).mean().mean(axis=1)
                features[f'return_std_{window}d'] = returns.rolling(window).std().mean(axis=1)
                features[f'return_skew_{window}d'] = returns.rolling(window).skew().mean(axis=1)
                features[f'return_kurt_{window}d'] = returns.rolling(window).kurt().mean(axis=1)
                
                # Drawdown features
                cumulative = (1 + returns).cumprod()
                running_max = cumulative.rolling(window).max()
                drawdown = (cumulative - running_max) / running_max
                features[f'max_drawdown_{window}d'] = drawdown.rolling(window).min().mean(axis=1)
                features[f'avg_drawdown_{window}d'] = drawdown.rolling(window).mean().mean(axis=1)
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating price features: {e}")
            return pd.DataFrame()
    
    def _create_volatility_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Create volatility-based features"""
        
        try:
            features = {}
            returns = price_data.pct_change()
            
            for window in self.config.lookback_windows:
                if len(returns) < window:
                    continue
                
                # Realized volatility
                features[f'realized_vol_{window}d'] = returns.rolling(window).std().mean(axis=1) * np.sqrt(252)
                
                # Volatility of volatility
                vol_series = returns.rolling(window).std().mean(axis=1)
                features[f'vol_of_vol_{window}d'] = vol_series.rolling(window).std()
                
                # GARCH-like features
                squared_returns = returns ** 2
                features[f'avg_squared_returns_{window}d'] = squared_returns.rolling(window).mean().mean(axis=1)
                
                # Range-based volatility (Garman-Klass if OHLC available)
                if all(col in price_data.columns for col in ['high', 'low', 'close']):
                    gk_vol = np.log(price_data['high'] / price_data['low']) ** 2
                    features[f'gk_volatility_{window}d'] = gk_vol.rolling(window).mean()
                
                # Volatility clustering
                vol_changes = vol_series.diff().abs()
                features[f'vol_clustering_{window}d'] = vol_changes.rolling(window).mean()
                
                # Volatility momentum
                short_vol = returns.rolling(window//2).std().mean(axis=1) if window >= 10 else vol_series
                long_vol = vol_series
                features[f'vol_momentum_{window}d'] = short_vol / long_vol - 1
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating volatility features: {e}")
            return pd.DataFrame()
    
    def _create_momentum_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Create momentum-based features"""
        
        try:
            features = {}
            returns = price_data.pct_change()
            
            for window in self.config.lookback_windows:
                if len(returns) < window:
                    continue
                
                # Time series momentum
                features[f'momentum_{window}d'] = returns.rolling(window).sum().mean(axis=1)
                
                # Risk-adjusted momentum
                momentum = returns.rolling(window).sum().mean(axis=1)
                volatility = returns.rolling(window).std().mean(axis=1)
                features[f'risk_adj_momentum_{window}d'] = momentum / (volatility + 1e-8)
                
                # Momentum acceleration
                short_momentum = returns.rolling(window//2).sum().mean(axis=1) if window >= 10 else momentum
                features[f'momentum_accel_{window}d'] = short_momentum - momentum
                
                # Cross-sectional momentum
                if price_data.shape[1] > 1:
                    asset_momentum = returns.rolling(window).sum()
                    momentum_rank = asset_momentum.rank(axis=1, pct=True)
                    features[f'cs_momentum_{window}d'] = momentum_rank.mean(axis=1)
                
                # Momentum persistence
                momentum_sign = np.sign(returns.rolling(window).sum())
                features[f'momentum_persistence_{window}d'] = (momentum_sign == momentum_sign.shift(1)).mean(axis=1)
                
                # Momentum reversal indicator
                long_momentum = returns.rolling(window*2).sum().mean(axis=1) if len(returns) >= window*2 else momentum
                features[f'momentum_reversal_{window}d'] = momentum / (long_momentum + 1e-8) - 1
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating momentum features: {e}")
            return pd.DataFrame()
    
    def _create_correlation_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Create correlation-based features"""
        
        try:
            features = {}
            
            if price_data.shape[1] < 2:
                return pd.DataFrame(index=price_data.index)
            
            returns = price_data.pct_change()
            
            for window in self.config.lookback_windows:
                if len(returns) < window:
                    continue
                
                # Rolling correlation matrix
                rolling_corr = returns.rolling(window).corr()
                
                # Average correlation
                def get_avg_correlation(corr_matrix):
                    if corr_matrix is None or corr_matrix.empty:
                        return 0
                    corr_values = corr_matrix.values
                    mask = np.triu(np.ones_like(corr_values, dtype=bool), k=1)
                    return corr_values[mask].mean()
                
                avg_corrs = []
                for date in returns.index:
                    try:
                        if date in rolling_corr.index:
                            corr_matrix = rolling_corr.loc[date]
                            avg_corr = get_avg_correlation(corr_matrix)
                            avg_corrs.append(avg_corr)
                        else:
                            avg_corrs.append(np.nan)
                    except:
                        avg_corrs.append(np.nan)
                
                features[f'avg_correlation_{window}d'] = pd.Series(avg_corrs, index=returns.index)
                
                # Correlation dispersion
                def get_corr_dispersion(corr_matrix):
                    if corr_matrix is None or corr_matrix.empty:
                        return 0
                    corr_values = corr_matrix.values
                    mask = np.triu(np.ones_like(corr_values, dtype=bool), k=1)
                    return corr_values[mask].std()
                
                corr_dispersions = []
                for date in returns.index:
                    try:
                        if date in rolling_corr.index:
                            corr_matrix = rolling_corr.loc[date]
                            corr_disp = get_corr_dispersion(corr_matrix)
                            corr_dispersions.append(corr_disp)
                        else:
                            corr_dispersions.append(np.nan)
                    except:
                        corr_dispersions.append(np.nan)
                
                features[f'correlation_dispersion_{window}d'] = pd.Series(corr_dispersions, index=returns.index)
                
                # Maximum correlation
                max_corrs = []
                for date in returns.index:
                    try:
                        if date in rolling_corr.index:
                            corr_matrix = rolling_corr.loc[date]
                            if corr_matrix is not None and not corr_matrix.empty:
                                corr_values = corr_matrix.values
                                mask = np.triu(np.ones_like(corr_values, dtype=bool), k=1)
                                max_corr = corr_values[mask].max() if mask.any() else 0
                                max_corrs.append(max_corr)
                            else:
                                max_corrs.append(np.nan)
                        else:
                            max_corrs.append(np.nan)
                    except:
                        max_corrs.append(np.nan)
                
                features[f'max_correlation_{window}d'] = pd.Series(max_corrs, index=returns.index)
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating correlation features: {e}")
            return pd.DataFrame(index=price_data.index)
    
    def _create_volume_features(self, price_data: pd.DataFrame, 
                              volume_data: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        
        try:
            features = {}
            returns = price_data.pct_change()
            
            for window in self.config.lookback_windows:
                if len(volume_data) < window:
                    continue
                
                # Volume momentum
                features[f'volume_momentum_{window}d'] = (volume_data.rolling(window).mean() / 
                                                        volume_data.shift(window) - 1).mean(axis=1)
                
                # Price-volume correlation
                pv_corr = returns.rolling(window).corr(volume_data.pct_change())
                features[f'price_volume_corr_{window}d'] = pv_corr.mean(axis=1)
                
                # Volume rate of change
                features[f'volume_roc_{window}d'] = volume_data.pct_change(window).mean(axis=1)
                
                # On-balance volume proxy
                obv_proxy = (returns.sign() * volume_data).cumsum()
                features[f'obv_momentum_{window}d'] = (obv_proxy.rolling(window).mean() / 
                                                     obv_proxy.shift(window) - 1).mean(axis=1)
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating volume features: {e}")
            return pd.DataFrame()
    
    def _create_technical_indicators(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features"""
        
        try:
            features = {}
            
            # Use first column or close price
            if 'close' in price_data.columns:
                price_series = price_data['close']
            else:
                price_series = price_data.iloc[:, 0]
            
            for window in self.config.lookback_windows:
                if len(price_series) < window:
                    continue
                
                # Moving averages
                sma = price_series.rolling(window).mean()
                features[f'sma_ratio_{window}d'] = price_series / sma - 1
                
                # Bollinger Bands
                bb_std = price_series.rolling(window).std()
                bb_upper = sma + 2 * bb_std
                bb_lower = sma - 2 * bb_std
                features[f'bb_position_{window}d'] = (price_series - bb_lower) / (bb_upper - bb_lower)
                
                # RSI approximation
                delta = price_series.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
                rs = gain / (loss + 1e-8)
                features[f'rsi_{window}d'] = 100 - (100 / (1 + rs))
                
                # Price channels
                highest = price_series.rolling(window).max()
                lowest = price_series.rolling(window).min()
                features[f'channel_position_{window}d'] = (price_series - lowest) / (highest - lowest + 1e-8)
            
            return pd.DataFrame(features, index=price_data.index)
            
        except Exception as e:
            logger.error(f"Error creating technical indicators: {e}")
            return pd.DataFrame()
    
    def _remove_correlated_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Remove highly correlated features"""
        
        try:
            if features.empty:
                return features
            
            # Calculate correlation matrix
            corr_matrix = features.corr().abs()
            
            # Find highly correlated pairs
            upper_triangle = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            
            # Find features to drop
            to_drop = [column for column in upper_triangle.columns if 
                      any(upper_triangle[column] > self.config.correlation_threshold)]
            
            # Drop correlated features
            features_cleaned = features.drop(columns=to_drop)
            
            logger.info(f"Removed {len(to_drop)} highly correlated features")
            return features_cleaned
            
        except Exception as e:
            logger.error(f"Error removing correlated features: {e}")
            return features


class RegimeModelTrainer:
    """Train and validate regime classification models"""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.models = {}
        self.scalers = {}
        self.label_encoder = LabelEncoder()
        self.feature_selector = None
        self.training_feature_names = None  # Store feature names from training
        self.is_trained = False
        
        logger.info("Model trainer initialized")
    
    def train_models(self, features: pd.DataFrame, 
                    regime_labels: pd.Series) -> Dict[str, ModelPerformance]:
        """Train multiple regime classification models"""
        
        try:
            if len(features) < self.config.min_training_samples:
                logger.warning(f"Insufficient training samples: {len(features)}")
                return {}
            
            # Align features and labels
            common_index = features.index.intersection(regime_labels.index)
            X = features.loc[common_index]
            y = regime_labels.loc[common_index]
            
            # Remove samples with unknown regime
            valid_mask = y != RegimeType.UNKNOWN
            X = X[valid_mask]
            y = y[valid_mask]
            
            if len(X) < self.config.min_training_samples:
                logger.warning("Insufficient valid training samples")
                return {}
            
            # Encode labels
            y_encoded = self.label_encoder.fit_transform([regime.value for regime in y])
            
            # Feature selection
            X_selected = self._select_features(X, y_encoded)
            
            # Store training feature names for consistent prediction
            self.training_feature_names = list(X_selected.columns)
            
            # Train-test split
            if self.config.cross_validation_method == "time_series":
                # Time series split (no shuffling)
                split_idx = int(len(X_selected) * (1 - self.config.test_size))
                X_train, X_test = X_selected.iloc[:split_idx], X_selected.iloc[split_idx:]
                y_train, y_test = y_encoded[:split_idx], y_encoded[split_idx:]
            else:
                X_train, X_test, y_train, y_test = train_test_split(
                    X_selected, y_encoded, test_size=self.config.test_size, 
                    stratify=y_encoded, random_state=42
                )
            
            # Scale features
            scaler = RobustScaler()
            
            # Clean data to avoid numerical issues while preserving DataFrame structure
            X_train_clean = X_train.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            X_test_clean = X_test.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            
            X_train_scaled = scaler.fit_transform(X_train_clean)
            X_test_scaled = scaler.transform(X_test_clean)
            
            self.scalers['main'] = scaler
            
            # Train models
            model_performances = {}
            
            for model_type in self.config.models_to_test:
                logger.info(f"Training {model_type.value} model")
                
                try:
                    # Create and train model
                    model = self._create_model(model_type)
                    
                    start_time = datetime.now()
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
                        model.fit(X_train_scaled, y_train)
                    training_time = (datetime.now() - start_time).total_seconds()
                    
                    # Calibrate probabilities if requested
                    if self.config.calibrate_probabilities:
                        with warnings.catch_warnings():
                            warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
                            model = CalibratedClassifierCV(model, cv=3)
                            model.fit(X_train_scaled, y_train)
                    
                    self.models[model_type.value] = model
                    
                    # Evaluate model
                    performance = self._evaluate_model(
                        model, X_train_scaled, X_test_scaled, y_train, y_test,
                        X_selected.columns, model_type.value, training_time
                    )
                    
                    model_performances[model_type.value] = performance
                    
                except Exception as e:
                    logger.error(f"Error training {model_type.value} model: {e}")
                    continue
            
            # Create ensemble if multiple models trained
            if len(self.models) > 1 and MLModel.ENSEMBLE in [self.config.primary_model] + self.config.models_to_test:
                ensemble_performance = self._create_ensemble_model(
                    X_train_scaled, X_test_scaled, y_train, y_test, X_selected.columns
                )
                if ensemble_performance:
                    model_performances['ensemble'] = ensemble_performance
            
            self.is_trained = True
            logger.info(f"Successfully trained {len(model_performances)} models")
            
            return model_performances
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return {}
    
    def _select_features(self, X: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
        """Select best features for classification"""
        
        try:
            if len(X.columns) <= self.config.max_features:
                return X
            
            # Remove constant features
            constant_features = X.columns[X.nunique() <= 1]
            X_clean = X.drop(columns=constant_features)
            
            if len(X_clean.columns) <= self.config.max_features:
                return X_clean
            
            # Feature selection
            if self.config.feature_selection_method == "mutual_info":
                selector = SelectKBest(score_func=mutual_info_classif, k=self.config.max_features)
            else:
                selector = SelectKBest(score_func=f_classif, k=self.config.max_features)
            
            X_selected = selector.fit_transform(X_clean, y)
            selected_columns = X_clean.columns[selector.get_support()]
            
            self.feature_selector = selector
            
            logger.info(f"Selected {len(selected_columns)} features from {len(X.columns)}")
            return pd.DataFrame(X_selected, columns=selected_columns, index=X.index)
            
        except Exception as e:
            logger.error(f"Error selecting features: {e}")
            return X
    
    def _create_model(self, model_type: MLModel):
        """Create model instance"""
        
        try:
            if model_type == MLModel.RANDOM_FOREST:
                return RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    class_weight='balanced' if self.config.use_class_weights else None,
                    random_state=42,
                    n_jobs=-1
                )
            
            elif model_type == MLModel.GRADIENT_BOOSTING:
                return GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=6,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42
                )
            
            elif model_type == MLModel.SVM:
                return SVC(
                    kernel='rbf',
                    C=1.0,
                    gamma='scale',
                    class_weight='balanced' if self.config.use_class_weights else None,
                    probability=True,
                    random_state=42
                )
            
            elif model_type == MLModel.NEURAL_NETWORK:
                return MLPClassifier(
                    hidden_layer_sizes=(100, 50),
                    activation='relu',
                    solver='adam',
                    alpha=0.001,
                    learning_rate='adaptive',
                    max_iter=500,
                    random_state=42
                )
            
            elif model_type == MLModel.LOGISTIC_REGRESSION:
                return LogisticRegression(
                    C=0.1,  # Stronger regularization
                    class_weight='balanced' if self.config.use_class_weights else None,
                    max_iter=2000,
                    tol=1e-6,
                    solver='lbfgs',
                    random_state=42
                )
            
            elif model_type == MLModel.NAIVE_BAYES:
                return GaussianNB()
            
            else:
                logger.warning(f"Unknown model type: {model_type}")
                return RandomForestClassifier(random_state=42)
                
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            return RandomForestClassifier(random_state=42)
    
    def _evaluate_model(self, model, X_train: np.ndarray, X_test: np.ndarray,
                       y_train: np.ndarray, y_test: np.ndarray,
                       feature_names: pd.Index, model_name: str,
                       training_time: float) -> ModelPerformance:
        """Evaluate model performance"""
        
        try:
            # Predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test) if hasattr(model, "predict_proba") else None
            
            # Basic metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
            
            # Cross-validation - adapt to dataset size
            min_samples_per_class = min(np.bincount(y_train))
            max_splits = min(5, max(2, min_samples_per_class - 1))  # At least 2 splits, max 5
            
            if self.config.cross_validation_method == "time_series":
                cv = TimeSeriesSplit(n_splits=min(max_splits, self.config.validation_splits))
            else:
                cv = min(max_splits, self.config.validation_splits)
            
            cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='accuracy')
            
            # Confusion matrix
            conf_matrix = confusion_matrix(y_test, y_pred)
            
            # Feature importance
            feature_importances = []
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                for i, (feature, importance) in enumerate(zip(feature_names, importances)):
                    feature_imp = FeatureImportance(
                        feature_name=feature,
                        importance_score=importance,
                        importance_rank=i + 1
                    )
                    feature_importances.append(feature_imp)
                
                # Sort by importance
                feature_importances.sort(key=lambda x: x.importance_score, reverse=True)
                
                # Update ranks
                for i, feature_imp in enumerate(feature_importances):
                    feature_imp.importance_rank = i + 1
            
            # Regime-specific metrics
            regime_specific = {}
            unique_regimes = np.unique(y_test)
            
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.metrics")
                for regime_idx in unique_regimes:
                    regime_mask = y_test == regime_idx
                    if regime_mask.sum() > 0:
                        regime_pred = y_pred[regime_mask]
                        regime_actual = y_test[regime_mask]
                        
                        regime_name = self.label_encoder.inverse_transform([regime_idx])[0]
                        regime_specific[regime_name] = {
                            'precision': precision_recall_fscore_support(regime_actual, regime_pred, average='weighted', zero_division=0)[0],
                            'recall': precision_recall_fscore_support(regime_actual, regime_pred, average='weighted', zero_division=0)[1],
                            'f1_score': precision_recall_fscore_support(regime_actual, regime_pred, average='weighted', zero_division=0)[2],
                            'support': regime_mask.sum()
                        }
            
            return ModelPerformance(
                model_name=model_name,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                cv_accuracy_mean=cv_scores.mean(),
                cv_accuracy_std=cv_scores.std(),
                confusion_matrix=conf_matrix,
                feature_importances=feature_importances,
                regime_specific_metrics=regime_specific,
                training_samples=len(X_train),
                training_time=training_time,
                last_trained=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return ModelPerformance(model_name=model_name)
    
    def _create_ensemble_model(self, X_train: np.ndarray, X_test: np.ndarray,
                             y_train: np.ndarray, y_test: np.ndarray,
                             feature_names: pd.Index) -> Optional[ModelPerformance]:
        """Create ensemble model from trained models"""
        
        try:
            if len(self.models) < 2:
                return None
            
            # Create voting classifier
            estimators = [(name, model) for name, model in self.models.items()]
            ensemble = VotingClassifier(estimators=estimators, voting='soft')
            
            start_time = datetime.now()
            ensemble.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()
            
            self.models['ensemble'] = ensemble
            
            # Evaluate ensemble
            performance = self._evaluate_model(
                ensemble, X_train, X_test, y_train, y_test,
                feature_names, 'ensemble', training_time
            )
            
            logger.info("Created ensemble model")
            return performance
            
        except Exception as e:
            logger.error(f"Error creating ensemble model: {e}")
            return None
    
    def predict_regime(self, features: pd.DataFrame) -> Optional[RegimeClassification]:
        """Predict regime for new data"""
        
        try:
            if not self.is_trained or not self.models:
                logger.warning("Models not trained")
                return None
            
            # Use primary model or best performing model
            model_name = self.config.primary_model.value
            if model_name not in self.models:
                model_name = list(self.models.keys())[0]
            
            model = self.models[model_name]
            scaler = self.scalers.get('main')
            
            if scaler is None:
                logger.warning("Scaler not available")
                return None
            
            # Prepare features - align with training features
            if self.training_feature_names is not None:
                # Create feature matrix aligned with training features
                aligned_features = pd.DataFrame(index=features.index, columns=self.training_feature_names)
                
                # Fill with available features, pad missing with zeros
                for col in self.training_feature_names:
                    if col in features.columns:
                        aligned_features[col] = features[col]
                    else:
                        aligned_features[col] = 0.0
                
                features_selected = aligned_features
            elif self.feature_selector is not None:
                features_selected = features.iloc[:, self.feature_selector.get_support()]
            else:
                features_selected = features
            
            # Scale features
            features_scaled = scaler.transform(features_selected.iloc[-1:])
            
            # Predict
            prediction = model.predict(features_scaled)[0]
            probabilities = model.predict_proba(features_scaled)[0] if hasattr(model, "predict_proba") else None
            
            # Convert prediction back to regime type
            regime_name = self.label_encoder.inverse_transform([prediction])[0]
            predicted_regime = RegimeType(regime_name)
            
            # Get regime probabilities
            regime_probabilities = {}
            if probabilities is not None:
                regime_names = self.label_encoder.inverse_transform(range(len(probabilities)))
                for regime_name, prob in zip(regime_names, probabilities):
                    regime_probabilities[RegimeType(regime_name)] = prob
            
            # Get top 3 predictions
            top_3_regimes = []
            if probabilities is not None:
                top_indices = np.argsort(probabilities)[-3:][::-1]
                for idx in top_indices:
                    regime_name = self.label_encoder.inverse_transform([idx])[0]
                    top_3_regimes.append((RegimeType(regime_name), probabilities[idx]))
            
            # Prediction confidence
            prediction_confidence = probabilities[prediction] if probabilities is not None else 0.5
            
            return RegimeClassification(
                timestamp=datetime.now(),
                predicted_regime=predicted_regime,
                prediction_confidence=prediction_confidence,
                regime_probabilities=regime_probabilities,
                top_3_regimes=top_3_regimes,
                model_used=MLModel(model_name),
                model_confidence=prediction_confidence
            )
            
        except Exception as e:
            logger.error(f"Error predicting regime: {e}")
            return None
    
    def save_models(self, filepath: str) -> bool:
        """Save trained models to file"""
        
        try:
            model_data = {
                'models': self.models,
                'scalers': self.scalers,
                'label_encoder': self.label_encoder,
                'feature_selector': self.feature_selector,
                'training_feature_names': self.training_feature_names,
                'config': self.config,
                'is_trained': self.is_trained
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Models saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return False
    
    def load_models(self, filepath: str) -> bool:
        """Load trained models from file"""
        
        try:
            model_data = joblib.load(filepath)
            
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.label_encoder = model_data['label_encoder']
            self.feature_selector = model_data['feature_selector']
            self.training_feature_names = model_data.get('training_feature_names')  # Backward compatibility
            self.is_trained = model_data['is_trained']
            
            logger.info(f"Models loaded from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False


class RegimeClassifier:
    """
    Advanced Regime Classifier
    
    Integrates feature engineering, model training, and prediction
    to provide comprehensive regime classification capabilities.
    """
    
    def __init__(self, config: Optional[ClassificationConfig] = None):
        """Initialize regime classifier"""
        
        self.config = config or ClassificationConfig()
        
        # Initialize components
        self.feature_engineer = FeatureEngineer(self.config)
        self.model_trainer = RegimeModelTrainer(self.config)
        
        # Classification history
        self.classification_history: List[RegimeClassification] = []
        self.model_performance_history: List[Dict[str, ModelPerformance]] = []
        
        # Last training date
        self.last_training_date: Optional[datetime] = None
        
        logger.info("Regime classifier initialized")
    
    def train(self, price_data: pd.DataFrame, regime_labels: pd.Series,
             volume_data: Optional[pd.DataFrame] = None,
             additional_data: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, ModelPerformance]:
        """Train regime classification models"""
        
        try:
            logger.info("Starting regime classifier training")
            
            # Engineer features
            features = self.feature_engineer.engineer_features(
                price_data, volume_data, additional_data
            )
            
            if features.empty:
                logger.error("No features engineered")
                return {}
            
            # Train models
            model_performances = self.model_trainer.train_models(features, regime_labels)
            
            if model_performances:
                self.model_performance_history.append(model_performances)
                self.last_training_date = datetime.now()
                
                # Log best performing model
                best_model = max(model_performances.items(), key=lambda x: x[1].accuracy)
                logger.info(f"Best model: {best_model[0]} (Accuracy: {best_model[1].accuracy:.3f})")
            
            return model_performances
            
        except Exception as e:
            logger.error(f"Error training regime classifier: {e}")
            return {}
    
    def train_models(self, price_data: pd.DataFrame, 
                    volume_data: Optional[pd.DataFrame] = None) -> bool:
        """
        Simplified training method for testing purposes
        Creates synthetic regime labels and trains models
        """
        
        try:
            logger.info("Training ML models with synthetic regime labels...")
            
            # Create synthetic regime labels based on price movements
            returns = price_data['close'].pct_change().dropna() if 'close' in price_data.columns else price_data.iloc[:, 0].pct_change().dropna()
            
            # Simple regime labeling based on volatility and returns
            rolling_vol = returns.rolling(20).std()
            rolling_ret = returns.rolling(20).mean()
            
            regime_labels = []
            for i in range(len(returns)):
                if i < 20:
                    regime_labels.append(RegimeType.UNKNOWN)
                    continue
                    
                vol = rolling_vol.iloc[i]
                ret = rolling_ret.iloc[i]
                
                if vol > rolling_vol.quantile(0.7):
                    if ret > 0:
                        regime_labels.append(RegimeType.HIGH_VOLATILITY)
                    else:
                        regime_labels.append(RegimeType.CRISIS)
                elif vol < rolling_vol.quantile(0.3):
                    if ret > rolling_ret.quantile(0.6):
                        regime_labels.append(RegimeType.BULL_MARKET)
                    elif ret < rolling_ret.quantile(0.4):
                        regime_labels.append(RegimeType.BEAR_MARKET)
                    else:
                        regime_labels.append(RegimeType.SIDEWAYS)
                else:
                    regime_labels.append(RegimeType.SIDEWAYS)
            
            # Convert to pandas Series
            regime_series = pd.Series(regime_labels, index=returns.index)
            
            # Train models using the existing train method
            model_performances = self.train(price_data, regime_series, volume_data)
            
            # Mark as trained if successful
            if model_performances:
                self.models_trained = True
                logger.info(f"✅ ML models trained successfully with {len(model_performances)} models")
                return True
            else:
                logger.warning("⚠️ ML model training failed")
                return False
                
        except Exception as e:
            logger.error(f"Error in simplified training: {e}")
            return False
    
    def train_on_historical_data(self, symbols: List[str], lookback_days: int = 252) -> bool:
        """
        Train models on historical data for multiple symbols
        This would be used in production with real historical regime labels
        """
        
        try:
            logger.info(f"Training on historical data for {len(symbols)} symbols, {lookback_days} days lookback")
            
            # This is a placeholder for production implementation
            # In production, you would:
            # 1. Load historical data for all symbols
            # 2. Load or create historical regime labels
            # 3. Train models on this comprehensive dataset
            
            logger.info("Historical training not implemented yet - using synthetic data")
            return False
            
        except Exception as e:
            logger.error(f"Error in historical training: {e}")
            return False
    
    def classify_regime(self, price_data: pd.DataFrame,
                       volume_data: Optional[pd.DataFrame] = None,
                       additional_data: Optional[Dict[str, pd.DataFrame]] = None) -> Optional[RegimeClassification]:
        """Classify current market regime"""
        
        try:
            # Engineer features
            features = self.feature_engineer.engineer_features(
                price_data, volume_data, additional_data
            )
            
            if features.empty:
                logger.error("No features available for classification")
                return None
            
            # Predict regime
            classification = self.model_trainer.predict_regime(features)
            
            if classification:
                self.classification_history.append(classification)
                
                # Limit history size
                if len(self.classification_history) > 1000:
                    self.classification_history = self.classification_history[-500:]
            
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying regime: {e}")
            return None
    
    def get_feature_importance(self, top_n: int = 20) -> List[FeatureImportance]:
        """Get most important features across all models"""
        
        try:
            if not self.model_performance_history:
                return []
            
            # Get latest model performances
            latest_performances = self.model_performance_history[-1]
            
            # Combine feature importances from all models
            combined_importances = {}
            
            for model_name, performance in latest_performances.items():
                for feature_imp in performance.feature_importances:
                    feature_name = feature_imp.feature_name
                    if feature_name not in combined_importances:
                        combined_importances[feature_name] = []
                    combined_importances[feature_name].append(feature_imp.importance_score)
            
            # Average importances across models
            averaged_importances = []
            for feature_name, scores in combined_importances.items():
                avg_score = sum(scores) / len(scores)
                feature_imp = FeatureImportance(
                    feature_name=feature_name,
                    importance_score=avg_score
                )
                averaged_importances.append(feature_imp)
            
            # Sort and limit
            averaged_importances.sort(key=lambda x: x.importance_score, reverse=True)
            
            # Update ranks
            for i, feature_imp in enumerate(averaged_importances[:top_n]):
                feature_imp.importance_rank = i + 1
            
            return averaged_importances[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return []
    
    def should_retrain(self) -> bool:
        """Check if models should be retrained"""
        
        try:
            if self.last_training_date is None:
                return True
            
            days_since_training = (datetime.now() - self.last_training_date).days
            return days_since_training >= self.config.retrain_frequency
            
        except Exception as e:
            logger.error(f"Error checking retrain status: {e}")
            return False
    
    def save_classifier(self, filepath: str) -> bool:
        """Save classifier to file"""
        
        try:
            return self.model_trainer.save_models(filepath)
            
        except Exception as e:
            logger.error(f"Error saving classifier: {e}")
            return False
    
    def load_classifier(self, filepath: str) -> bool:
        """Load classifier from file"""
        
        try:
            return self.model_trainer.load_models(filepath)
            
        except Exception as e:
            logger.error(f"Error loading classifier: {e}")
            return False