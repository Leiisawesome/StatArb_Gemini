"""
Success Pattern Learning System
===============================

This module implements a comprehensive success pattern learning system that uses
machine learning to identify, learn, and predict successful trading patterns
for statistical arbitrage pairs.

Key Features:
- ML-based pattern recognition and classification
- Predictive modeling for success probability
- Automated pattern discovery and validation
- Multi-dimensional pattern analysis
- Ensemble learning for robust predictions
- Real-time pattern matching and scoring

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sqlite3
import threading
import time
from collections import defaultdict, deque
import warnings
import pickle
import hashlib

# ML and statistical libraries
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score, TimeSeriesSplit, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif
from scipy import stats
from scipy.signal import find_peaks
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Types of success patterns"""
    CORRELATION_PATTERN = "CORRELATION_PATTERN"
    VOLATILITY_PATTERN = "VOLATILITY_PATTERN"
    MOMENTUM_PATTERN = "MOMENTUM_PATTERN"
    MEAN_REVERSION_PATTERN = "MEAN_REVERSION_PATTERN"
    REGIME_PATTERN = "REGIME_PATTERN"
    SEASONAL_PATTERN = "SEASONAL_PATTERN"
    MARKET_STRUCTURE_PATTERN = "MARKET_STRUCTURE_PATTERN"
    COMPOSITE_PATTERN = "COMPOSITE_PATTERN"

class PatternConfidence(Enum):
    """Confidence levels for pattern predictions"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class LearningMethod(Enum):
    """Machine learning methods for pattern learning"""
    RANDOM_FOREST = "RANDOM_FOREST"
    GRADIENT_BOOSTING = "GRADIENT_BOOSTING"
    NEURAL_NETWORK = "NEURAL_NETWORK"
    ENSEMBLE = "ENSEMBLE"
    DEEP_LEARNING = "DEEP_LEARNING"

@dataclass
class PatternFeatures:
    """Features extracted for pattern analysis"""
    # Price-based features
    correlation_features: Dict[str, float] = field(default_factory=dict)
    volatility_features: Dict[str, float] = field(default_factory=dict)
    momentum_features: Dict[str, float] = field(default_factory=dict)
    mean_reversion_features: Dict[str, float] = field(default_factory=dict)
    
    # Market structure features
    liquidity_features: Dict[str, float] = field(default_factory=dict)
    volume_features: Dict[str, float] = field(default_factory=dict)
    spread_features: Dict[str, float] = field(default_factory=dict)
    
    # Temporal features
    time_features: Dict[str, float] = field(default_factory=dict)
    seasonal_features: Dict[str, float] = field(default_factory=dict)
    
    # Market regime features
    regime_features: Dict[str, float] = field(default_factory=dict)
    
    # Composite features
    interaction_features: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    extraction_timestamp: datetime = field(default_factory=datetime.now)
    feature_version: str = "1.0"

@dataclass
class SuccessPattern:
    """Identified success pattern"""
    pattern_id: str
    pattern_type: PatternType
    pattern_name: str
    
    # Pattern characteristics
    feature_importance: Dict[str, float]
    success_probability: float
    confidence: PatternConfidence
    
    # Performance metrics
    precision: float
    recall: float
    f1_score: float
    auc_score: float
    
    # Pattern conditions
    trigger_conditions: Dict[str, Any]
    market_conditions: Dict[str, Any]
    
    # Validation results
    cross_validation_score: float
    out_of_sample_score: float
    
    # Usage statistics
    occurrences: int
    successful_predictions: int
    failed_predictions: int
    
    # Temporal information
    discovery_date: datetime
    last_seen: datetime
    last_validated: datetime
    
    # Model information
    model_type: str
    model_parameters: Dict[str, Any]
    
    # Pattern evolution
    pattern_stability: float
    adaptation_rate: float

@dataclass
class PatternPrediction:
    """Prediction result from pattern matching"""
    pair_id: str
    pattern_id: str
    pattern_type: PatternType
    
    # Prediction results
    success_probability: float
    confidence: PatternConfidence
    prediction_score: float
    
    # Feature matching
    feature_match_score: float
    key_features: Dict[str, float]
    
    # Context
    market_regime: str
    timestamp: datetime
    
    # Model information
    model_used: str
    ensemble_votes: Dict[str, float] = field(default_factory=dict)
    
    # Validation
    prediction_validated: bool = False
    actual_outcome: Optional[bool] = None
    prediction_accuracy: Optional[float] = None

class SuccessPatternLearning:
    """
    Comprehensive success pattern learning system
    
    This class provides:
    - ML-based pattern recognition and classification
    - Predictive modeling for success probability
    - Automated pattern discovery and validation
    - Real-time pattern matching and scoring
    - Ensemble learning for robust predictions
    """
    
    def __init__(self, 
                 db_path: str = "pattern_learning.db",
                 min_pattern_samples: int = 100,
                 validation_split: float = 0.2,
                 retraining_frequency: int = 7):  # days
        """
        Initialize the success pattern learning system
        
        Args:
            db_path: Path to SQLite database
            min_pattern_samples: Minimum samples for pattern learning
            validation_split: Validation split ratio
            retraining_frequency: Model retraining frequency in days
        """
        self.db_path = db_path
        self.min_pattern_samples = min_pattern_samples
        self.validation_split = validation_split
        self.retraining_frequency = retraining_frequency
        
        # Pattern storage
        self.discovered_patterns: Dict[str, SuccessPattern] = {}
        self.pattern_predictions: List[PatternPrediction] = []
        
        # Training data
        self.training_features: List[PatternFeatures] = []
        self.training_labels: List[bool] = []
        
        # ML models
        self.pattern_models: Dict[str, Any] = {}
        self.ensemble_model: Optional[VotingClassifier] = None
        self.feature_selector: Optional[SelectKBest] = None
        self.feature_scaler: StandardScaler = StandardScaler()
        
        # Feature engineering
        self.feature_extractors: Dict[str, Callable] = {}
        self.feature_importance: Dict[str, float] = {}
        
        # Performance tracking
        self.model_performance: Dict[str, Dict[str, float]] = {}
        self.pattern_performance: Dict[str, Dict[str, float]] = {}
        
        # Callbacks
        self.pattern_discovery_callbacks: List[Callable[[SuccessPattern], None]] = []
        self.prediction_callbacks: List[Callable[[PatternPrediction], None]] = []
        
        # Threading
        self.learning_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Initialize feature extractors
        self._init_feature_extractors()
        
        # Initialize ML models
        self._init_ml_models()
        
        logger.info("Success pattern learning system initialized")
    
    def _init_database(self):
        """Initialize SQLite database for pattern data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS success_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    feature_importance TEXT,
                    success_probability REAL,
                    confidence TEXT,
                    precision_score REAL,
                    recall_score REAL,
                    f1_score REAL,
                    auc_score REAL,
                    trigger_conditions TEXT,
                    market_conditions TEXT,
                    cross_validation_score REAL,
                    out_of_sample_score REAL,
                    occurrences INTEGER,
                    successful_predictions INTEGER,
                    failed_predictions INTEGER,
                    discovery_date DATETIME,
                    last_seen DATETIME,
                    last_validated DATETIME,
                    model_type TEXT,
                    model_parameters TEXT,
                    pattern_stability REAL,
                    adaptation_rate REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pattern_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    pattern_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    success_probability REAL,
                    confidence TEXT,
                    prediction_score REAL,
                    feature_match_score REAL,
                    key_features TEXT,
                    market_regime TEXT,
                    timestamp DATETIME,
                    model_used TEXT,
                    ensemble_votes TEXT,
                    prediction_validated BOOLEAN DEFAULT FALSE,
                    actual_outcome BOOLEAN,
                    prediction_accuracy REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    features TEXT NOT NULL,
                    label BOOLEAN NOT NULL,
                    timestamp DATETIME NOT NULL,
                    market_regime TEXT,
                    feature_version TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    evaluation_date DATETIME NOT NULL,
                    accuracy REAL,
                    precision_score REAL,
                    recall_score REAL,
                    f1_score REAL,
                    auc_score REAL,
                    cross_validation_score REAL,
                    training_samples INTEGER,
                    validation_samples INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Pattern learning database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _init_feature_extractors(self):
        """Initialize feature extraction functions"""
        self.feature_extractors = {
            'correlation': self._extract_correlation_features,
            'volatility': self._extract_volatility_features,
            'momentum': self._extract_momentum_features,
            'mean_reversion': self._extract_mean_reversion_features,
            'liquidity': self._extract_liquidity_features,
            'volume': self._extract_volume_features,
            'spread': self._extract_spread_features,
            'time': self._extract_time_features,
            'seasonal': self._extract_seasonal_features,
            'regime': self._extract_regime_features,
            'interaction': self._extract_interaction_features
        }
        
        logger.info("Feature extractors initialized")
    
    def _init_ml_models(self):
        """Initialize machine learning models"""
        try:
            # Individual models
            self.pattern_models = {
                'random_forest': RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42
                ),
                'gradient_boosting': GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=6,
                    random_state=42
                ),
                'logistic_regression': LogisticRegression(
                    random_state=42,
                    max_iter=1000
                ),
                'svm': SVC(
                    probability=True,
                    random_state=42
                ),
                'neural_network': MLPClassifier(
                    hidden_layer_sizes=(100, 50),
                    max_iter=1000,
                    random_state=42
                )
            }
            
            # Feature selection
            self.feature_selector = SelectKBest(score_func=f_classif, k=50)
            
            logger.info("ML models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing ML models: {e}")
            raise
    
    def extract_features(self, pair_data: Dict[str, Any]) -> PatternFeatures:
        """Extract comprehensive features for pattern analysis"""
        try:
            features = PatternFeatures()
            
            # Extract features using all extractors
            for extractor_name, extractor_func in self.feature_extractors.items():
                try:
                    extracted_features = extractor_func(pair_data)
                    
                    # Store in appropriate feature category
                    if extractor_name == 'correlation':
                        features.correlation_features = extracted_features
                    elif extractor_name == 'volatility':
                        features.volatility_features = extracted_features
                    elif extractor_name == 'momentum':
                        features.momentum_features = extracted_features
                    elif extractor_name == 'mean_reversion':
                        features.mean_reversion_features = extracted_features
                    elif extractor_name == 'liquidity':
                        features.liquidity_features = extracted_features
                    elif extractor_name == 'volume':
                        features.volume_features = extracted_features
                    elif extractor_name == 'spread':
                        features.spread_features = extracted_features
                    elif extractor_name == 'time':
                        features.time_features = extracted_features
                    elif extractor_name == 'seasonal':
                        features.seasonal_features = extracted_features
                    elif extractor_name == 'regime':
                        features.regime_features = extracted_features
                    elif extractor_name == 'interaction':
                        features.interaction_features = extracted_features
                    
                except Exception as e:
                    logger.warning(f"Error extracting {extractor_name} features: {e}")
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return PatternFeatures()
    
    def _extract_correlation_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract correlation-based features"""
        features = {}
        
        try:
            # Basic correlation
            correlation = pair_data.get('correlation', 0.0)
            features['correlation'] = correlation
            features['correlation_abs'] = abs(correlation)
            features['correlation_squared'] = correlation ** 2
            
            # Rolling correlations
            rolling_corr = pair_data.get('rolling_correlation', [])
            if rolling_corr:
                features['correlation_mean'] = np.mean(rolling_corr)
                features['correlation_std'] = np.std(rolling_corr)
                features['correlation_trend'] = self._calculate_trend(rolling_corr)
                features['correlation_stability'] = 1.0 - np.std(rolling_corr) if rolling_corr else 0.0
            
            # Correlation regime
            if correlation > 0.8:
                features['correlation_regime_high'] = 1.0
            elif correlation > 0.6:
                features['correlation_regime_medium'] = 1.0
            else:
                features['correlation_regime_low'] = 1.0
            
        except Exception as e:
            logger.warning(f"Error extracting correlation features: {e}")
        
        return features
    
    def _extract_volatility_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract volatility-based features"""
        features = {}
        
        try:
            # Individual volatilities
            vol1 = pair_data.get('volatility1', 0.0)
            vol2 = pair_data.get('volatility2', 0.0)
            
            features['volatility1'] = vol1
            features['volatility2'] = vol2
            features['volatility_avg'] = (vol1 + vol2) / 2
            features['volatility_ratio'] = vol1 / vol2 if vol2 > 0 else 1.0
            features['volatility_diff'] = abs(vol1 - vol2)
            
            # Volatility matching
            if vol1 > 0 and vol2 > 0:
                features['volatility_match'] = min(vol1, vol2) / max(vol1, vol2)
            
            # Volatility regimes
            avg_vol = (vol1 + vol2) / 2
            if avg_vol > 0.3:
                features['volatility_regime_high'] = 1.0
            elif avg_vol > 0.15:
                features['volatility_regime_medium'] = 1.0
            else:
                features['volatility_regime_low'] = 1.0
            
            # Volatility clustering
            vol_history = pair_data.get('volatility_history', [])
            if vol_history:
                features['volatility_clustering'] = self._calculate_clustering(vol_history)
            
        except Exception as e:
            logger.warning(f"Error extracting volatility features: {e}")
        
        return features
    
    def _extract_momentum_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract momentum-based features"""
        features = {}
        
        try:
            # Price momentum
            momentum1 = pair_data.get('momentum1', 0.0)
            momentum2 = pair_data.get('momentum2', 0.0)
            
            features['momentum1'] = momentum1
            features['momentum2'] = momentum2
            features['momentum_diff'] = abs(momentum1 - momentum2)
            features['momentum_divergence'] = momentum1 - momentum2
            
            # Momentum alignment
            if momentum1 * momentum2 > 0:
                features['momentum_aligned'] = 1.0
            else:
                features['momentum_divergent'] = 1.0
            
            # Momentum strength
            features['momentum_strength'] = (abs(momentum1) + abs(momentum2)) / 2
            
            # Price trends
            price_trend1 = pair_data.get('price_trend1', 0.0)
            price_trend2 = pair_data.get('price_trend2', 0.0)
            
            features['price_trend1'] = price_trend1
            features['price_trend2'] = price_trend2
            features['trend_divergence'] = abs(price_trend1 - price_trend2)
            
        except Exception as e:
            logger.warning(f"Error extracting momentum features: {e}")
        
        return features
    
    def _extract_mean_reversion_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract mean reversion features"""
        features = {}
        
        try:
            # Spread statistics
            spread = pair_data.get('spread', 0.0)
            spread_mean = pair_data.get('spread_mean', 0.0)
            spread_std = pair_data.get('spread_std', 1.0)
            
            features['spread'] = spread
            features['spread_zscore'] = (spread - spread_mean) / spread_std if spread_std > 0 else 0.0
            features['spread_normalized'] = spread / spread_std if spread_std > 0 else 0.0
            
            # Mean reversion indicators
            spread_history = pair_data.get('spread_history', [])
            if len(spread_history) > 10:
                features['mean_reversion_strength'] = self._calculate_mean_reversion_strength(spread_history)
                features['half_life'] = self._calculate_half_life(spread_history)
            
            # Spread extremes
            if abs(features.get('spread_zscore', 0)) > 2:
                features['spread_extreme'] = 1.0
            
            # Cointegration
            cointegration_pvalue = pair_data.get('cointegration_pvalue', 1.0)
            features['cointegration_strength'] = 1.0 - cointegration_pvalue
            
        except Exception as e:
            logger.warning(f"Error extracting mean reversion features: {e}")
        
        return features
    
    def _extract_liquidity_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract liquidity-based features"""
        features = {}
        
        try:
            # Basic liquidity
            liquidity1 = pair_data.get('liquidity1', 0.0)
            liquidity2 = pair_data.get('liquidity2', 0.0)
            
            features['liquidity1'] = liquidity1
            features['liquidity2'] = liquidity2
            features['liquidity_min'] = min(liquidity1, liquidity2)
            features['liquidity_ratio'] = liquidity1 / liquidity2 if liquidity2 > 0 else 1.0
            
            # Liquidity matching
            if liquidity1 > 0 and liquidity2 > 0:
                features['liquidity_match'] = min(liquidity1, liquidity2) / max(liquidity1, liquidity2)
            
            # Bid-ask spreads
            bid_ask1 = pair_data.get('bid_ask_spread1', 0.0)
            bid_ask2 = pair_data.get('bid_ask_spread2', 0.0)
            
            features['bid_ask_spread1'] = bid_ask1
            features['bid_ask_spread2'] = bid_ask2
            features['bid_ask_avg'] = (bid_ask1 + bid_ask2) / 2
            
            # Market impact
            market_impact1 = pair_data.get('market_impact1', 0.0)
            market_impact2 = pair_data.get('market_impact2', 0.0)
            
            features['market_impact1'] = market_impact1
            features['market_impact2'] = market_impact2
            features['market_impact_avg'] = (market_impact1 + market_impact2) / 2
            
        except Exception as e:
            logger.warning(f"Error extracting liquidity features: {e}")
        
        return features
    
    def _extract_volume_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract volume-based features"""
        features = {}
        
        try:
            # Trading volumes
            volume1 = pair_data.get('volume1', 0.0)
            volume2 = pair_data.get('volume2', 0.0)
            
            features['volume1'] = volume1
            features['volume2'] = volume2
            features['volume_ratio'] = volume1 / volume2 if volume2 > 0 else 1.0
            features['volume_imbalance'] = abs(volume1 - volume2) / (volume1 + volume2) if (volume1 + volume2) > 0 else 0.0
            
            # Volume patterns
            volume_history1 = pair_data.get('volume_history1', [])
            volume_history2 = pair_data.get('volume_history2', [])
            
            if volume_history1:
                features['volume_trend1'] = self._calculate_trend(volume_history1)
                features['volume_volatility1'] = np.std(volume_history1) / np.mean(volume_history1) if np.mean(volume_history1) > 0 else 0.0
            
            if volume_history2:
                features['volume_trend2'] = self._calculate_trend(volume_history2)
                features['volume_volatility2'] = np.std(volume_history2) / np.mean(volume_history2) if np.mean(volume_history2) > 0 else 0.0
            
            # Volume-price relationship
            price_volume_corr1 = pair_data.get('price_volume_correlation1', 0.0)
            price_volume_corr2 = pair_data.get('price_volume_correlation2', 0.0)
            
            features['price_volume_corr1'] = price_volume_corr1
            features['price_volume_corr2'] = price_volume_corr2
            
        except Exception as e:
            logger.warning(f"Error extracting volume features: {e}")
        
        return features
    
    def _extract_spread_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract spread-based features"""
        features = {}
        
        try:
            # Current spread
            spread = pair_data.get('spread', 0.0)
            features['spread_current'] = spread
            
            # Spread statistics
            spread_history = pair_data.get('spread_history', [])
            if spread_history:
                features['spread_mean'] = np.mean(spread_history)
                features['spread_std'] = np.std(spread_history)
                features['spread_min'] = np.min(spread_history)
                features['spread_max'] = np.max(spread_history)
                features['spread_range'] = np.max(spread_history) - np.min(spread_history)
                
                # Spread percentiles
                features['spread_percentile_25'] = np.percentile(spread_history, 25)
                features['spread_percentile_75'] = np.percentile(spread_history, 75)
                
                # Current spread position
                if features['spread_std'] > 0:
                    features['spread_zscore'] = (spread - features['spread_mean']) / features['spread_std']
                    features['spread_percentile'] = stats.percentileofscore(spread_history, spread) / 100.0
            
            # Spread dynamics
            if len(spread_history) > 1:
                features['spread_change'] = spread_history[-1] - spread_history[-2]
                features['spread_velocity'] = self._calculate_velocity(spread_history)
                features['spread_acceleration'] = self._calculate_acceleration(spread_history)
            
        except Exception as e:
            logger.warning(f"Error extracting spread features: {e}")
        
        return features
    
    def _extract_time_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract time-based features"""
        features = {}
        
        try:
            current_time = datetime.now()
            
            # Time of day
            features['hour'] = current_time.hour
            features['minute'] = current_time.minute
            features['hour_sin'] = np.sin(2 * np.pi * current_time.hour / 24)
            features['hour_cos'] = np.cos(2 * np.pi * current_time.hour / 24)
            
            # Day of week
            features['day_of_week'] = current_time.weekday()
            features['is_weekend'] = 1.0 if current_time.weekday() >= 5 else 0.0
            
            # Market sessions
            features['is_market_open'] = 1.0 if 9 <= current_time.hour <= 16 else 0.0
            features['is_opening_hour'] = 1.0 if current_time.hour == 9 else 0.0
            features['is_closing_hour'] = 1.0 if current_time.hour == 16 else 0.0
            
            # Time since market open
            if current_time.hour >= 9:
                features['time_since_open'] = (current_time.hour - 9) + current_time.minute / 60.0
            else:
                features['time_since_open'] = 0.0
            
        except Exception as e:
            logger.warning(f"Error extracting time features: {e}")
        
        return features
    
    def _extract_seasonal_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract seasonal features"""
        features = {}
        
        try:
            current_time = datetime.now()
            
            # Month
            features['month'] = current_time.month
            features['month_sin'] = np.sin(2 * np.pi * current_time.month / 12)
            features['month_cos'] = np.cos(2 * np.pi * current_time.month / 12)
            
            # Quarter
            features['quarter'] = (current_time.month - 1) // 3 + 1
            
            # Day of month
            features['day_of_month'] = current_time.day
            
            # Earnings season (simplified)
            earnings_months = [1, 4, 7, 10]  # Typical earnings months
            features['is_earnings_season'] = 1.0 if current_time.month in earnings_months else 0.0
            
            # Holiday effects (simplified)
            holiday_days = [1, 25]  # New Year, Christmas
            features['near_holiday'] = 1.0 if current_time.day in holiday_days else 0.0
            
        except Exception as e:
            logger.warning(f"Error extracting seasonal features: {e}")
        
        return features
    
    def _extract_regime_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract market regime features"""
        features = {}
        
        try:
            # Market regime
            market_regime = pair_data.get('market_regime', 'NORMAL')
            
            # One-hot encode regimes
            regime_types = ['TRENDING', 'MEAN_REVERTING', 'HIGH_VOLATILITY', 'LOW_VOLATILITY', 'CRISIS']
            for regime in regime_types:
                features[f'regime_{regime.lower()}'] = 1.0 if market_regime == regime else 0.0
            
            # Volatility regime
            volatility_regime = pair_data.get('volatility_regime', 'NORMAL')
            vol_regimes = ['LOW', 'NORMAL', 'HIGH', 'EXTREME']
            for vol_regime in vol_regimes:
                features[f'vol_regime_{vol_regime.lower()}'] = 1.0 if volatility_regime == vol_regime else 0.0
            
            # Market stress indicators
            vix_level = pair_data.get('vix_level', 20.0)
            features['vix_level'] = vix_level
            features['vix_high'] = 1.0 if vix_level > 30 else 0.0
            features['vix_low'] = 1.0 if vix_level < 15 else 0.0
            
            # Market trend
            market_trend = pair_data.get('market_trend', 0.0)
            features['market_trend'] = market_trend
            features['market_bullish'] = 1.0 if market_trend > 0.05 else 0.0
            features['market_bearish'] = 1.0 if market_trend < -0.05 else 0.0
            
        except Exception as e:
            logger.warning(f"Error extracting regime features: {e}")
        
        return features
    
    def _extract_interaction_features(self, pair_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract interaction features between different aspects"""
        features = {}
        
        try:
            # Correlation-volatility interaction
            correlation = pair_data.get('correlation', 0.0)
            vol_avg = (pair_data.get('volatility1', 0.0) + pair_data.get('volatility2', 0.0)) / 2
            features['corr_vol_interaction'] = correlation * vol_avg
            
            # Momentum-mean reversion interaction
            momentum_diff = abs(pair_data.get('momentum1', 0.0) - pair_data.get('momentum2', 0.0))
            spread_zscore = pair_data.get('spread_zscore', 0.0)
            features['momentum_mr_interaction'] = momentum_diff * abs(spread_zscore)
            
            # Liquidity-volatility interaction
            min_liquidity = min(pair_data.get('liquidity1', 0.0), pair_data.get('liquidity2', 0.0))
            features['liquidity_vol_interaction'] = min_liquidity * vol_avg
            
            # Time-regime interaction
            hour = datetime.now().hour
            is_high_vol_regime = 1.0 if pair_data.get('volatility_regime', 'NORMAL') == 'HIGH' else 0.0
            features['time_regime_interaction'] = hour * is_high_vol_regime
            
            # Spread-volume interaction
            spread_abs = abs(pair_data.get('spread', 0.0))
            volume_avg = (pair_data.get('volume1', 0.0) + pair_data.get('volume2', 0.0)) / 2
            features['spread_volume_interaction'] = spread_abs * volume_avg
            
        except Exception as e:
            logger.warning(f"Error extracting interaction features: {e}")
        
        return features
    
    def _calculate_trend(self, data: List[float]) -> float:
        """Calculate trend strength"""
        if len(data) < 2:
            return 0.0
        
        x = np.arange(len(data))
        slope, _, r_value, p_value, _ = stats.linregress(x, data)
        
        # Return trend strength (slope weighted by R-squared and significance)
        return slope * (r_value ** 2) if p_value < 0.05 else 0.0
    
    def _calculate_clustering(self, data: List[float]) -> float:
        """Calculate clustering coefficient"""
        if len(data) < 3:
            return 0.0
        
        # Simple clustering measure based on autocorrelation
        autocorr = np.corrcoef(data[:-1], data[1:])[0, 1]
        return autocorr if not np.isnan(autocorr) else 0.0
    
    def _calculate_mean_reversion_strength(self, spread_history: List[float]) -> float:
        """Calculate mean reversion strength"""
        if len(spread_history) < 10:
            return 0.0
        
        # Calculate half-life of mean reversion
        spread_array = np.array(spread_history)
        lagged_spread = spread_array[:-1]
        spread_changes = np.diff(spread_array)
        
        if len(lagged_spread) > 0 and np.var(lagged_spread) > 0:
            beta = np.cov(spread_changes, lagged_spread)[0, 1] / np.var(lagged_spread)
            half_life = -np.log(2) / np.log(1 + beta) if beta < 0 else np.inf
            return 1.0 / (1.0 + half_life) if half_life != np.inf else 0.0
        
        return 0.0
    
    def _calculate_half_life(self, spread_history: List[float]) -> float:
        """Calculate half-life of mean reversion"""
        if len(spread_history) < 10:
            return np.inf
        
        spread_array = np.array(spread_history)
        lagged_spread = spread_array[:-1]
        spread_changes = np.diff(spread_array)
        
        if len(lagged_spread) > 0 and np.var(lagged_spread) > 0:
            beta = np.cov(spread_changes, lagged_spread)[0, 1] / np.var(lagged_spread)
            half_life = -np.log(2) / np.log(1 + beta) if beta < 0 else np.inf
            return half_life if half_life != np.inf else np.inf
        
        return np.inf
    
    def _calculate_velocity(self, data: List[float]) -> float:
        """Calculate velocity (first derivative)"""
        if len(data) < 2:
            return 0.0
        
        return data[-1] - data[-2]
    
    def _calculate_acceleration(self, data: List[float]) -> float:
        """Calculate acceleration (second derivative)"""
        if len(data) < 3:
            return 0.0
        
        return (data[-1] - data[-2]) - (data[-2] - data[-3])
    
    def add_training_sample(self, pair_data: Dict[str, Any], success: bool):
        """Add a training sample for pattern learning"""
        try:
            # Extract features
            features = self.extract_features(pair_data)
            
            # Add to training data
            self.training_features.append(features)
            self.training_labels.append(success)
            
            # Store in database
            self._store_training_sample(pair_data.get('pair_id', 'unknown'), features, success)
            
            # Trigger retraining if enough samples
            if len(self.training_features) >= self.min_pattern_samples:
                if len(self.training_features) % 100 == 0:  # Retrain every 100 samples
                    self._trigger_model_retraining()
            
        except Exception as e:
            logger.error(f"Error adding training sample: {e}")
    
    def _store_training_sample(self, pair_id: str, features: PatternFeatures, success: bool):
        """Store training sample in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert features to JSON
            features_dict = self._features_to_dict(features)
            
            cursor.execute('''
                INSERT INTO training_data 
                (pair_id, features, label, timestamp, market_regime, feature_version)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pair_id,
                json.dumps(features_dict),
                success,
                datetime.now(),
                'UNKNOWN',  # Would be extracted from features
                features.feature_version
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing training sample: {e}")
    
    def _features_to_dict(self, features: PatternFeatures) -> Dict[str, Any]:
        """Convert PatternFeatures to dictionary"""
        return {
            'correlation_features': features.correlation_features,
            'volatility_features': features.volatility_features,
            'momentum_features': features.momentum_features,
            'mean_reversion_features': features.mean_reversion_features,
            'liquidity_features': features.liquidity_features,
            'volume_features': features.volume_features,
            'spread_features': features.spread_features,
            'time_features': features.time_features,
            'seasonal_features': features.seasonal_features,
            'regime_features': features.regime_features,
            'interaction_features': features.interaction_features,
            'extraction_timestamp': features.extraction_timestamp.isoformat(),
            'feature_version': features.feature_version
        }
    
    def _trigger_model_retraining(self):
        """Trigger model retraining"""
        try:
            logger.info("Triggering model retraining")
            
            # Prepare training data
            X, y = self._prepare_training_data()
            
            if len(X) < self.min_pattern_samples:
                logger.warning(f"Insufficient training samples: {len(X)}")
                return
            
            # Train models
            self._train_models(X, y)
            
            # Discover patterns
            self._discover_patterns(X, y)
            
            # Evaluate models
            self._evaluate_models(X, y)
            
            logger.info("Model retraining completed")
            
        except Exception as e:
            logger.error(f"Error in model retraining: {e}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML models"""
        try:
            # Convert features to flat vectors
            feature_vectors = []
            
            for features in self.training_features:
                feature_vector = []
                
                # Flatten all feature categories
                for feature_dict in [
                    features.correlation_features,
                    features.volatility_features,
                    features.momentum_features,
                    features.mean_reversion_features,
                    features.liquidity_features,
                    features.volume_features,
                    features.spread_features,
                    features.time_features,
                    features.seasonal_features,
                    features.regime_features,
                    features.interaction_features
                ]:
                    # Sort keys for consistent ordering
                    for key in sorted(feature_dict.keys()):
                        feature_vector.append(feature_dict[key])
                
                feature_vectors.append(feature_vector)
            
            X = np.array(feature_vectors)
            y = np.array(self.training_labels)
            
            # Handle missing values
            X = np.nan_to_num(X)
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            return np.array([]), np.array([])
    
    def _train_models(self, X: np.ndarray, y: np.ndarray):
        """Train all ML models"""
        try:
            # Feature selection
            self.feature_selector.fit(X, y)
            X_selected = self.feature_selector.transform(X)
            
            # Feature scaling
            X_scaled = self.feature_scaler.fit_transform(X_selected)
            
            # Train individual models
            for model_name, model in self.pattern_models.items():
                try:
                    model.fit(X_scaled, y)
                    logger.info(f"Trained {model_name} model")
                except Exception as e:
                    logger.error(f"Error training {model_name}: {e}")
            
            # Create ensemble model
            ensemble_models = [
                ('rf', self.pattern_models['random_forest']),
                ('gb', self.pattern_models['gradient_boosting']),
                ('lr', self.pattern_models['logistic_regression'])
            ]
            
            self.ensemble_model = VotingClassifier(
                estimators=ensemble_models,
                voting='soft'
            )
            
            self.ensemble_model.fit(X_scaled, y)
            
            logger.info("Ensemble model trained")
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
    
    def _discover_patterns(self, X: np.ndarray, y: np.ndarray):
        """Discover success patterns using trained models"""
        try:
            # Feature selection and scaling
            X_selected = self.feature_selector.transform(X)
            X_scaled = self.feature_scaler.transform(X_selected)
            
            # Get feature importance from random forest
            rf_model = self.pattern_models.get('random_forest')
            if rf_model:
                feature_importance = rf_model.feature_importances_
                
                # Get top features
                top_features_idx = np.argsort(feature_importance)[-20:]  # Top 20 features
                
                # Create pattern based on top features
                pattern = self._create_pattern_from_features(
                    top_features_idx, feature_importance, X_scaled, y
                )
                
                if pattern:
                    self.discovered_patterns[pattern.pattern_id] = pattern
                    self._store_pattern(pattern)
                    
                    # Trigger callbacks
                    for callback in self.pattern_discovery_callbacks:
                        try:
                            callback(pattern)
                        except Exception as e:
                            logger.error(f"Error in pattern discovery callback: {e}")
            
        except Exception as e:
            logger.error(f"Error discovering patterns: {e}")
    
    def _create_pattern_from_features(self, top_features_idx: np.ndarray, 
                                    feature_importance: np.ndarray,
                                    X: np.ndarray, y: np.ndarray) -> Optional[SuccessPattern]:
        """Create a success pattern from top features"""
        try:
            # Calculate pattern characteristics
            success_rate = np.mean(y)
            
            # Feature importance dictionary
            feature_names = [f"feature_{i}" for i in range(len(feature_importance))]
            importance_dict = {
                feature_names[i]: feature_importance[i] 
                for i in top_features_idx
            }
            
            # Generate pattern ID
            pattern_id = hashlib.md5(str(importance_dict).encode()).hexdigest()[:16]
            
            # Create pattern
            pattern = SuccessPattern(
                pattern_id=pattern_id,
                pattern_type=PatternType.COMPOSITE_PATTERN,
                pattern_name=f"ML_Pattern_{pattern_id}",
                feature_importance=importance_dict,
                success_probability=success_rate,
                confidence=self._calculate_pattern_confidence(success_rate, len(y)),
                precision=0.0,  # Will be calculated in evaluation
                recall=0.0,     # Will be calculated in evaluation
                f1_score=0.0,   # Will be calculated in evaluation
                auc_score=0.0,  # Will be calculated in evaluation
                trigger_conditions={},
                market_conditions={},
                cross_validation_score=0.0,
                out_of_sample_score=0.0,
                occurrences=len(y),
                successful_predictions=int(np.sum(y)),
                failed_predictions=int(len(y) - np.sum(y)),
                discovery_date=datetime.now(),
                last_seen=datetime.now(),
                last_validated=datetime.now(),
                model_type="RandomForest",
                model_parameters={},
                pattern_stability=0.8,  # Default
                adaptation_rate=0.1     # Default
            )
            
            return pattern
            
        except Exception as e:
            logger.error(f"Error creating pattern from features: {e}")
            return None
    
    def _calculate_pattern_confidence(self, success_rate: float, sample_size: int) -> PatternConfidence:
        """Calculate pattern confidence based on success rate and sample size"""
        # Calculate confidence interval
        std_error = np.sqrt(success_rate * (1 - success_rate) / sample_size)
        confidence_interval = 1.96 * std_error  # 95% confidence interval
        
        # Determine confidence level
        if confidence_interval < 0.05 and sample_size > 200:
            return PatternConfidence.VERY_HIGH
        elif confidence_interval < 0.1 and sample_size > 100:
            return PatternConfidence.HIGH
        elif confidence_interval < 0.15 and sample_size > 50:
            return PatternConfidence.MEDIUM
        elif confidence_interval < 0.2:
            return PatternConfidence.LOW
        else:
            return PatternConfidence.VERY_LOW
    
    def _store_pattern(self, pattern: SuccessPattern):
        """Store discovered pattern in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO success_patterns 
                (pattern_id, pattern_type, pattern_name, feature_importance, success_probability,
                 confidence, precision_score, recall_score, f1_score, auc_score, trigger_conditions,
                 market_conditions, cross_validation_score, out_of_sample_score, occurrences,
                 successful_predictions, failed_predictions, discovery_date, last_seen,
                 last_validated, model_type, model_parameters, pattern_stability, adaptation_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id, pattern.pattern_type.value, pattern.pattern_name,
                json.dumps(pattern.feature_importance), pattern.success_probability,
                pattern.confidence.value, pattern.precision, pattern.recall,
                pattern.f1_score, pattern.auc_score, json.dumps(pattern.trigger_conditions),
                json.dumps(pattern.market_conditions), pattern.cross_validation_score,
                pattern.out_of_sample_score, pattern.occurrences,
                pattern.successful_predictions, pattern.failed_predictions,
                pattern.discovery_date, pattern.last_seen, pattern.last_validated,
                pattern.model_type, json.dumps(pattern.model_parameters),
                pattern.pattern_stability, pattern.adaptation_rate
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing pattern: {e}")
    
    def _evaluate_models(self, X: np.ndarray, y: np.ndarray):
        """Evaluate model performance"""
        try:
            # Feature selection and scaling
            X_selected = self.feature_selector.transform(X)
            X_scaled = self.feature_scaler.transform(X_selected)
            
            # Time series cross-validation
            tscv = TimeSeriesSplit(n_splits=5)
            
            for model_name, model in self.pattern_models.items():
                try:
                    # Cross-validation scores
                    cv_scores = cross_val_score(model, X_scaled, y, cv=tscv, scoring='roc_auc')
                    
                    # Store performance
                    self.model_performance[model_name] = {
                        'cv_score_mean': np.mean(cv_scores),
                        'cv_score_std': np.std(cv_scores),
                        'training_samples': len(X),
                        'evaluation_date': datetime.now()
                    }
                    
                    logger.info(f"{model_name} CV AUC: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
                    
                except Exception as e:
                    logger.error(f"Error evaluating {model_name}: {e}")
            
            # Evaluate ensemble
            if self.ensemble_model:
                ensemble_scores = cross_val_score(self.ensemble_model, X_scaled, y, cv=tscv, scoring='roc_auc')
                self.model_performance['ensemble'] = {
                    'cv_score_mean': np.mean(ensemble_scores),
                    'cv_score_std': np.std(ensemble_scores),
                    'training_samples': len(X),
                    'evaluation_date': datetime.now()
                }
                
                logger.info(f"Ensemble CV AUC: {np.mean(ensemble_scores):.4f} ± {np.std(ensemble_scores):.4f}")
            
        except Exception as e:
            logger.error(f"Error evaluating models: {e}")
    
    def predict_success(self, pair_data: Dict[str, Any]) -> PatternPrediction:
        """Predict success probability for a pair"""
        try:
            # Extract features
            features = self.extract_features(pair_data)
            
            # Convert to feature vector
            feature_vector = self._features_to_vector(features)
            
            if len(feature_vector) == 0:
                return self._create_default_prediction(pair_data.get('pair_id', 'unknown'))
            
            # Feature selection and scaling
            X = np.array([feature_vector])
            X_selected = self.feature_selector.transform(X)
            X_scaled = self.feature_scaler.transform(X_selected)
            
            # Make predictions with ensemble
            if self.ensemble_model:
                success_prob = self.ensemble_model.predict_proba(X_scaled)[0][1]
                
                # Get individual model votes
                ensemble_votes = {}
                for model_name, model in self.pattern_models.items():
                    try:
                        prob = model.predict_proba(X_scaled)[0][1]
                        ensemble_votes[model_name] = prob
                    except Exception as e:
                        logger.warning(f"Error getting prediction from {model_name}: {e}")
                
                # Calculate confidence
                confidence = self._calculate_prediction_confidence(success_prob, ensemble_votes)
                
                # Create prediction
                prediction = PatternPrediction(
                    pair_id=pair_data.get('pair_id', 'unknown'),
                    pattern_id='ensemble_prediction',
                    pattern_type=PatternType.COMPOSITE_PATTERN,
                    success_probability=success_prob,
                    confidence=confidence,
                    prediction_score=success_prob,
                    feature_match_score=self._calculate_feature_match_score(features),
                    key_features=self._identify_key_features(features),
                    market_regime=pair_data.get('market_regime', 'UNKNOWN'),
                    timestamp=datetime.now(),
                    model_used='ensemble',
                    ensemble_votes=ensemble_votes
                )
                
                # Store prediction
                self.pattern_predictions.append(prediction)
                self._store_prediction(prediction)
                
                # Trigger callbacks
                for callback in self.prediction_callbacks:
                    try:
                        callback(prediction)
                    except Exception as e:
                        logger.error(f"Error in prediction callback: {e}")
                
                return prediction
            
            else:
                return self._create_default_prediction(pair_data.get('pair_id', 'unknown'))
            
        except Exception as e:
            logger.error(f"Error predicting success: {e}")
            return self._create_default_prediction(pair_data.get('pair_id', 'unknown'))
    
    def _features_to_vector(self, features: PatternFeatures) -> List[float]:
        """Convert PatternFeatures to feature vector"""
        try:
            feature_vector = []
            
            # Flatten all feature categories (same order as training)
            for feature_dict in [
                features.correlation_features,
                features.volatility_features,
                features.momentum_features,
                features.mean_reversion_features,
                features.liquidity_features,
                features.volume_features,
                features.spread_features,
                features.time_features,
                features.seasonal_features,
                features.regime_features,
                features.interaction_features
            ]:
                # Sort keys for consistent ordering
                for key in sorted(feature_dict.keys()):
                    feature_vector.append(feature_dict[key])
            
            return feature_vector
            
        except Exception as e:
            logger.error(f"Error converting features to vector: {e}")
            return []
    
    def _calculate_prediction_confidence(self, success_prob: float, 
                                       ensemble_votes: Dict[str, float]) -> PatternConfidence:
        """Calculate prediction confidence"""
        try:
            # Calculate vote agreement
            if len(ensemble_votes) > 1:
                vote_std = np.std(list(ensemble_votes.values()))
                agreement = 1.0 - (vote_std / 0.5)  # Normalize by max possible std
            else:
                agreement = 0.5
            
            # Calculate confidence based on probability and agreement
            confidence_score = (abs(success_prob - 0.5) * 2) * agreement
            
            if confidence_score > 0.8:
                return PatternConfidence.VERY_HIGH
            elif confidence_score > 0.6:
                return PatternConfidence.HIGH
            elif confidence_score > 0.4:
                return PatternConfidence.MEDIUM
            elif confidence_score > 0.2:
                return PatternConfidence.LOW
            else:
                return PatternConfidence.VERY_LOW
                
        except Exception as e:
            logger.error(f"Error calculating prediction confidence: {e}")
            return PatternConfidence.LOW
    
    def _calculate_feature_match_score(self, features: PatternFeatures) -> float:
        """Calculate how well features match known patterns"""
        try:
            # Simple implementation - would be more sophisticated in practice
            total_features = sum(len(d) for d in [
                features.correlation_features,
                features.volatility_features,
                features.momentum_features,
                features.mean_reversion_features,
                features.liquidity_features,
                features.volume_features,
                features.spread_features,
                features.time_features,
                features.seasonal_features,
                features.regime_features,
                features.interaction_features
            ])
            
            return min(1.0, total_features / 50.0)  # Normalize by expected feature count
            
        except Exception as e:
            logger.error(f"Error calculating feature match score: {e}")
            return 0.0
    
    def _identify_key_features(self, features: PatternFeatures) -> Dict[str, float]:
        """Identify key features for prediction"""
        try:
            key_features = {}
            
            # Get features with highest absolute values (simplified)
            all_features = {}
            for feature_dict in [
                features.correlation_features,
                features.volatility_features,
                features.momentum_features,
                features.mean_reversion_features,
                features.liquidity_features,
                features.volume_features,
                features.spread_features,
                features.time_features,
                features.seasonal_features,
                features.regime_features,
                features.interaction_features
            ]:
                all_features.update(feature_dict)
            
            # Sort by absolute value and take top 10
            sorted_features = sorted(all_features.items(), key=lambda x: abs(x[1]), reverse=True)
            key_features = dict(sorted_features[:10])
            
            return key_features
            
        except Exception as e:
            logger.error(f"Error identifying key features: {e}")
            return {}
    
    def _create_default_prediction(self, pair_id: str) -> PatternPrediction:
        """Create default prediction when models are not available"""
        return PatternPrediction(
            pair_id=pair_id,
            pattern_id='default',
            pattern_type=PatternType.COMPOSITE_PATTERN,
            success_probability=0.5,
            confidence=PatternConfidence.VERY_LOW,
            prediction_score=0.5,
            feature_match_score=0.0,
            key_features={},
            market_regime='UNKNOWN',
            timestamp=datetime.now(),
            model_used='default'
        )
    
    def _store_prediction(self, prediction: PatternPrediction):
        """Store prediction in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO pattern_predictions 
                (pair_id, pattern_id, pattern_type, success_probability, confidence,
                 prediction_score, feature_match_score, key_features, market_regime,
                 timestamp, model_used, ensemble_votes, prediction_validated,
                 actual_outcome, prediction_accuracy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                prediction.pair_id, prediction.pattern_id, prediction.pattern_type.value,
                prediction.success_probability, prediction.confidence.value,
                prediction.prediction_score, prediction.feature_match_score,
                json.dumps(prediction.key_features), prediction.market_regime,
                prediction.timestamp, prediction.model_used,
                json.dumps(prediction.ensemble_votes), prediction.prediction_validated,
                prediction.actual_outcome, prediction.prediction_accuracy
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing prediction: {e}")
    
    def validate_prediction(self, pair_id: str, actual_success: bool):
        """Validate a prediction with actual outcome"""
        try:
            # Find the prediction
            for prediction in self.pattern_predictions:
                if prediction.pair_id == pair_id and not prediction.prediction_validated:
                    prediction.prediction_validated = True
                    prediction.actual_outcome = actual_success
                    
                    # Calculate accuracy
                    predicted_success = prediction.success_probability > 0.5
                    prediction.prediction_accuracy = 1.0 if predicted_success == actual_success else 0.0
                    
                    # Update pattern statistics
                    pattern = self.discovered_patterns.get(prediction.pattern_id)
                    if pattern:
                        if actual_success:
                            pattern.successful_predictions += 1
                        else:
                            pattern.failed_predictions += 1
                        
                        pattern.last_seen = datetime.now()
                    
                    logger.info(f"Validated prediction for {pair_id}: {actual_success}")
                    break
            
        except Exception as e:
            logger.error(f"Error validating prediction: {e}")
    
    def start_learning_loop(self):
        """Start automatic learning loop"""
        if self.learning_thread and self.learning_thread.is_alive():
            logger.warning("Learning loop already running")
            return
        
        self.stop_event.clear()
        self.learning_thread = threading.Thread(target=self._learning_loop, daemon=True)
        self.learning_thread.start()
        
        logger.info("Learning loop started")
    
    def stop_learning_loop(self):
        """Stop automatic learning loop"""
        self.stop_event.set()
        if self.learning_thread:
            self.learning_thread.join(timeout=10)
        
        logger.info("Learning loop stopped")
    
    def _learning_loop(self):
        """Main learning loop"""
        while not self.stop_event.is_set():
            try:
                # Check if retraining is needed
                if len(self.training_features) >= self.min_pattern_samples:
                    last_training = getattr(self, '_last_training_time', datetime.min)
                    if datetime.now() - last_training > timedelta(days=self.retraining_frequency):
                        self._trigger_model_retraining()
                        self._last_training_time = datetime.now()
                
                # Sleep for 1 hour
                self.stop_event.wait(3600)
                
            except Exception as e:
                logger.error(f"Error in learning loop: {e}")
                time.sleep(3600)
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get comprehensive learning system summary"""
        try:
            return {
                'training_samples': len(self.training_features),
                'discovered_patterns': len(self.discovered_patterns),
                'recent_predictions': len([p for p in self.pattern_predictions if p.timestamp > datetime.now() - timedelta(days=7)]),
                'model_performance': self.model_performance,
                'pattern_performance': {
                    pattern_id: {
                        'success_rate': pattern.success_probability,
                        'confidence': pattern.confidence.value,
                        'occurrences': pattern.occurrences,
                        'accuracy': pattern.successful_predictions / max(1, pattern.occurrences)
                    }
                    for pattern_id, pattern in self.discovered_patterns.items()
                },
                'learning_status': 'RUNNING' if self.learning_thread and self.learning_thread.is_alive() else 'STOPPED',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating learning summary: {e}")
            return {}
    
    def add_pattern_discovery_callback(self, callback: Callable[[SuccessPattern], None]):
        """Add callback for pattern discovery"""
        self.pattern_discovery_callbacks.append(callback)
    
    def add_prediction_callback(self, callback: Callable[[PatternPrediction], None]):
        """Add callback for predictions"""
        self.prediction_callbacks.append(callback)

# Example usage
if __name__ == "__main__":
    # Create pattern learning system
    pattern_learning = SuccessPatternLearning()
    
    # Add callbacks
    def pattern_discovery_handler(pattern: SuccessPattern):
        print(f"PATTERN DISCOVERED: {pattern.pattern_name} - Success Rate: {pattern.success_probability:.3f}")
    
    def prediction_handler(prediction: PatternPrediction):
        print(f"PREDICTION: {prediction.pair_id} - Success Prob: {prediction.success_probability:.3f}")
    
    pattern_learning.add_pattern_discovery_callback(pattern_discovery_handler)
    pattern_learning.add_prediction_callback(prediction_handler)
    
    # Start learning loop
    pattern_learning.start_learning_loop()
    
    # Simulate training data
    import random
    
    for i in range(200):
        # Simulate pair data
        pair_data = {
            'pair_id': f"PAIR_{i}",
            'correlation': random.uniform(0.3, 0.9),
            'volatility1': random.uniform(0.1, 0.5),
            'volatility2': random.uniform(0.1, 0.5),
            'momentum1': random.gauss(0, 0.1),
            'momentum2': random.gauss(0, 0.1),
            'spread': random.gauss(0, 1),
            'spread_history': [random.gauss(0, 1) for _ in range(50)],
            'liquidity1': random.uniform(1000000, 10000000),
            'liquidity2': random.uniform(1000000, 10000000),
            'market_regime': random.choice(['TRENDING', 'MEAN_REVERTING', 'HIGH_VOLATILITY'])
        }
        
        # Simulate success (higher correlation = higher success probability)
        success_prob = (pair_data['correlation'] - 0.3) / 0.6
        success = random.random() < success_prob
        
        # Add training sample
        pattern_learning.add_training_sample(pair_data, success)
    
    # Test predictions
    for i in range(10):
        test_pair = {
            'pair_id': f"TEST_{i}",
            'correlation': random.uniform(0.5, 0.9),
            'volatility1': random.uniform(0.1, 0.3),
            'volatility2': random.uniform(0.1, 0.3),
            'momentum1': random.gauss(0, 0.05),
            'momentum2': random.gauss(0, 0.05),
            'spread': random.gauss(0, 0.5),
            'spread_history': [random.gauss(0, 0.5) for _ in range(50)],
            'liquidity1': random.uniform(5000000, 15000000),
            'liquidity2': random.uniform(5000000, 15000000),
            'market_regime': 'MEAN_REVERTING'
        }
        
        prediction = pattern_learning.predict_success(test_pair)
        print(f"Test prediction: {prediction.success_probability:.3f}")
    
    # Get summary
    summary = pattern_learning.get_learning_summary()
    print(json.dumps(summary, indent=2))
    
    # Stop learning loop
    pattern_learning.stop_learning_loop() 