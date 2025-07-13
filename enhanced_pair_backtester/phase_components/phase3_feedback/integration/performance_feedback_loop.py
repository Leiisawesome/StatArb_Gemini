"""
Performance Feedback Loop System
================================

This module implements a comprehensive performance feedback loop for statistical arbitrage pairs,
providing real-time performance tracking, success pattern analysis, and adaptive adjustment
mechanisms to continuously improve trading performance.

Key Features:
- Real-time performance tracking and analysis
- Success pattern identification and learning
- Adaptive parameter adjustment based on performance
- Performance attribution analysis
- Predictive performance modeling
- Automated strategy optimization

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

# Statistical and ML libraries
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMetricType(Enum):
    """Types of performance metrics"""
    SHARPE_RATIO = "SHARPE_RATIO"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    WIN_RATE = "WIN_RATE"
    PROFIT_FACTOR = "PROFIT_FACTOR"
    CALMAR_RATIO = "CALMAR_RATIO"
    TOTAL_RETURN = "TOTAL_RETURN"
    VOLATILITY = "VOLATILITY"
    SKEWNESS = "SKEWNESS"
    KURTOSIS = "KURTOSIS"
    VAR_95 = "VAR_95"

class FeedbackSignal(Enum):
    """Types of feedback signals"""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    STRONG_POSITIVE = "STRONG_POSITIVE"
    STRONG_NEGATIVE = "STRONG_NEGATIVE"

class AdjustmentType(Enum):
    """Types of parameter adjustments"""
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    MAINTAIN = "MAINTAIN"
    RESET = "RESET"

@dataclass
class PerformanceRecord:
    """Individual performance record"""
    pair_id: str
    timestamp: datetime
    
    # Performance metrics
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_return: float
    volatility: float
    
    # Trading metrics
    num_trades: int
    avg_trade_duration: float
    avg_profit_per_trade: float
    
    # Market context
    market_regime: str
    volatility_regime: str
    correlation_level: float
    
    # Strategy parameters at time of performance
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Attribution factors
    attribution_factors: Dict[str, float] = field(default_factory=dict)

@dataclass
class FeedbackEvent:
    """Feedback event for performance analysis"""
    event_id: str
    pair_id: str
    timestamp: datetime
    
    # Performance change
    metric_type: PerformanceMetricType
    previous_value: float
    current_value: float
    change_percentage: float
    
    # Feedback signal
    signal: FeedbackSignal
    confidence: float
    
    # Context
    market_conditions: Dict[str, Any]
    strategy_changes: Dict[str, Any]
    
    # Recommended actions
    recommended_adjustments: List[Dict[str, Any]]
    
    processed: bool = False

@dataclass
class PerformancePattern:
    """Identified performance pattern"""
    pattern_id: str
    pattern_type: str
    
    # Pattern characteristics
    success_rate: float
    avg_performance: float
    consistency: float
    
    # Conditions
    market_conditions: Dict[str, Any]
    strategy_conditions: Dict[str, Any]
    
    # Predictive power
    predictive_accuracy: float
    confidence_interval: Tuple[float, float]
    
    # Usage statistics
    occurrences: int
    last_seen: datetime
    
    # Performance attribution
    performance_contribution: float

class PerformanceFeedbackLoop:
    """
    Comprehensive performance feedback loop system
    
    This class provides:
    - Real-time performance tracking and analysis
    - Success pattern identification and learning
    - Adaptive parameter adjustment
    - Performance attribution analysis
    - Predictive performance modeling
    """
    
    def __init__(self, 
                 db_path: str = "performance_feedback.db",
                 learning_window: int = 252,  # Trading days
                 min_performance_samples: int = 50,
                 feedback_sensitivity: float = 0.05):
        """
        Initialize the performance feedback loop
        
        Args:
            db_path: Path to SQLite database
            learning_window: Window for learning patterns
            min_performance_samples: Minimum samples for analysis
            feedback_sensitivity: Sensitivity for feedback signals
        """
        self.db_path = db_path
        self.learning_window = learning_window
        self.min_performance_samples = min_performance_samples
        self.feedback_sensitivity = feedback_sensitivity
        
        # Performance tracking
        self.performance_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.learning_window * 2)
        )
        self.feedback_events: List[FeedbackEvent] = []
        self.performance_patterns: Dict[str, PerformancePattern] = {}
        
        # Learning models
        self.performance_predictors: Dict[str, Any] = {}
        self.pattern_recognizers: Dict[str, Any] = {}
        
        # Adjustment tracking
        self.adjustment_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.parameter_effectiveness: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Callbacks
        self.feedback_callbacks: List[Callable[[FeedbackEvent], None]] = []
        self.adjustment_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Threading
        self.feedback_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Initialize models
        self._init_models()
        
        logger.info("Performance feedback loop initialized")
    
    def _init_database(self):
        """Initialize SQLite database for feedback data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    total_return REAL,
                    volatility REAL,
                    num_trades INTEGER,
                    avg_trade_duration REAL,
                    avg_profit_per_trade REAL,
                    market_regime TEXT,
                    volatility_regime TEXT,
                    correlation_level REAL,
                    strategy_params TEXT,
                    attribution_factors TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metric_type TEXT NOT NULL,
                    previous_value REAL NOT NULL,
                    current_value REAL NOT NULL,
                    change_percentage REAL NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    market_conditions TEXT,
                    strategy_changes TEXT,
                    recommended_adjustments TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    success_rate REAL NOT NULL,
                    avg_performance REAL NOT NULL,
                    consistency REAL NOT NULL,
                    market_conditions TEXT,
                    strategy_conditions TEXT,
                    predictive_accuracy REAL,
                    confidence_interval_low REAL,
                    confidence_interval_high REAL,
                    occurrences INTEGER,
                    last_seen DATETIME,
                    performance_contribution REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adjustment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    parameter_name TEXT NOT NULL,
                    old_value REAL,
                    new_value REAL,
                    adjustment_type TEXT NOT NULL,
                    reason TEXT,
                    expected_impact REAL,
                    actual_impact REAL,
                    effectiveness_score REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Performance feedback database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _init_models(self):
        """Initialize machine learning models"""
        try:
            # Performance prediction models
            self.performance_predictors = {
                'sharpe_predictor': RandomForestRegressor(n_estimators=100, random_state=42),
                'drawdown_predictor': GradientBoostingRegressor(n_estimators=100, random_state=42),
                'return_predictor': LinearRegression()
            }
            
            # Pattern recognition models
            self.pattern_recognizers = {
                'success_classifier': RandomForestRegressor(n_estimators=50, random_state=42),
                'regime_classifier': GradientBoostingRegressor(n_estimators=50, random_state=42)
            }
            
            # Feature scalers
            self.feature_scalers = {
                'performance_scaler': StandardScaler(),
                'pattern_scaler': StandardScaler()
            }
            
            logger.info("ML models initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    def add_performance_record(self, record: PerformanceRecord):
        """Add a performance record to the feedback system"""
        try:
            # Store in memory
            self.performance_history[record.pair_id].append(record)
            
            # Store in database
            self._store_performance_record(record)
            
            # Analyze for feedback signals
            self._analyze_performance_change(record)
            
            # Update patterns
            self._update_performance_patterns(record)
            
            # Trigger learning if enough data
            if len(self.performance_history[record.pair_id]) >= self.min_performance_samples:
                self._trigger_learning(record.pair_id)
            
        except Exception as e:
            logger.error(f"Error adding performance record: {e}")
    
    def _store_performance_record(self, record: PerformanceRecord):
        """Store performance record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_records 
                (pair_id, timestamp, sharpe_ratio, max_drawdown, win_rate, profit_factor,
                 total_return, volatility, num_trades, avg_trade_duration, avg_profit_per_trade,
                 market_regime, volatility_regime, correlation_level, strategy_params, attribution_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.pair_id, record.timestamp, record.sharpe_ratio, record.max_drawdown,
                record.win_rate, record.profit_factor, record.total_return, record.volatility,
                record.num_trades, record.avg_trade_duration, record.avg_profit_per_trade,
                record.market_regime, record.volatility_regime, record.correlation_level,
                json.dumps(record.strategy_params), json.dumps(record.attribution_factors)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance record: {e}")
    
    def _analyze_performance_change(self, current_record: PerformanceRecord):
        """Analyze performance changes and generate feedback signals"""
        try:
            pair_history = list(self.performance_history[current_record.pair_id])
            if len(pair_history) < 2:
                return
            
            previous_record = pair_history[-2]
            
            # Analyze each metric
            metrics_to_analyze = [
                ('sharpe_ratio', PerformanceMetricType.SHARPE_RATIO, True),
                ('max_drawdown', PerformanceMetricType.MAX_DRAWDOWN, False),
                ('win_rate', PerformanceMetricType.WIN_RATE, True),
                ('profit_factor', PerformanceMetricType.PROFIT_FACTOR, True),
                ('total_return', PerformanceMetricType.TOTAL_RETURN, True)
            ]
            
            for metric_name, metric_type, higher_is_better in metrics_to_analyze:
                previous_value = getattr(previous_record, metric_name)
                current_value = getattr(current_record, metric_name)
                
                if previous_value != 0:
                    change_pct = (current_value - previous_value) / abs(previous_value)
                    
                    # Generate feedback signal
                    signal = self._generate_feedback_signal(
                        change_pct, higher_is_better, metric_type
                    )
                    
                    if signal != FeedbackSignal.NEUTRAL:
                        feedback_event = self._create_feedback_event(
                            current_record, metric_type, previous_value, 
                            current_value, change_pct, signal
                        )
                        
                        self.feedback_events.append(feedback_event)
                        self._store_feedback_event(feedback_event)
                        
                        # Trigger callbacks
                        for callback in self.feedback_callbacks:
                            try:
                                callback(feedback_event)
                            except Exception as e:
                                logger.error(f"Error in feedback callback: {e}")
            
        except Exception as e:
            logger.error(f"Error analyzing performance change: {e}")
    
    def _generate_feedback_signal(self, change_pct: float, higher_is_better: bool, 
                                metric_type: PerformanceMetricType) -> FeedbackSignal:
        """Generate feedback signal based on performance change"""
        abs_change = abs(change_pct)
        
        # Adjust sensitivity based on metric type
        sensitivity = self.feedback_sensitivity
        if metric_type == PerformanceMetricType.MAX_DRAWDOWN:
            sensitivity *= 0.5  # More sensitive to drawdown changes
        elif metric_type == PerformanceMetricType.SHARPE_RATIO:
            sensitivity *= 1.5  # Less sensitive to Sharpe changes
        
        # Determine signal strength
        if abs_change < sensitivity:
            return FeedbackSignal.NEUTRAL
        elif abs_change > sensitivity * 3:
            # Strong signal
            if higher_is_better:
                return FeedbackSignal.STRONG_POSITIVE if change_pct > 0 else FeedbackSignal.STRONG_NEGATIVE
            else:
                return FeedbackSignal.STRONG_NEGATIVE if change_pct > 0 else FeedbackSignal.STRONG_POSITIVE
        else:
            # Regular signal
            if higher_is_better:
                return FeedbackSignal.POSITIVE if change_pct > 0 else FeedbackSignal.NEGATIVE
            else:
                return FeedbackSignal.NEGATIVE if change_pct > 0 else FeedbackSignal.POSITIVE
    
    def _create_feedback_event(self, record: PerformanceRecord, metric_type: PerformanceMetricType,
                             previous_value: float, current_value: float, 
                             change_pct: float, signal: FeedbackSignal) -> FeedbackEvent:
        """Create a feedback event"""
        event_id = f"{record.pair_id}_{metric_type.value}_{int(record.timestamp.timestamp())}"
        
        # Calculate confidence based on change magnitude and consistency
        confidence = min(1.0, abs(change_pct) / self.feedback_sensitivity)
        
        # Generate recommendations
        recommendations = self._generate_adjustment_recommendations(
            record, metric_type, signal, change_pct
        )
        
        return FeedbackEvent(
            event_id=event_id,
            pair_id=record.pair_id,
            timestamp=record.timestamp,
            metric_type=metric_type,
            previous_value=previous_value,
            current_value=current_value,
            change_percentage=change_pct,
            signal=signal,
            confidence=confidence,
            market_conditions={
                'regime': record.market_regime,
                'volatility_regime': record.volatility_regime,
                'correlation_level': record.correlation_level
            },
            strategy_changes=record.strategy_params,
            recommended_adjustments=recommendations
        )
    
    def _generate_adjustment_recommendations(self, record: PerformanceRecord, 
                                          metric_type: PerformanceMetricType,
                                          signal: FeedbackSignal, 
                                          change_pct: float) -> List[Dict[str, Any]]:
        """Generate parameter adjustment recommendations"""
        recommendations = []
        
        # Base recommendations by metric type and signal
        if metric_type == PerformanceMetricType.SHARPE_RATIO:
            if signal in [FeedbackSignal.NEGATIVE, FeedbackSignal.STRONG_NEGATIVE]:
                recommendations.extend([
                    {'parameter': 'position_size', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 0.1},
                    {'parameter': 'stop_loss', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 0.05},
                    {'parameter': 'correlation_threshold', 'adjustment': AdjustmentType.INCREASE, 'magnitude': 0.05}
                ])
        
        elif metric_type == PerformanceMetricType.MAX_DRAWDOWN:
            if signal in [FeedbackSignal.NEGATIVE, FeedbackSignal.STRONG_NEGATIVE]:
                recommendations.extend([
                    {'parameter': 'position_size', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 0.2},
                    {'parameter': 'max_positions', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 1},
                    {'parameter': 'risk_limit', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 0.1}
                ])
        
        elif metric_type == PerformanceMetricType.WIN_RATE:
            if signal in [FeedbackSignal.NEGATIVE, FeedbackSignal.STRONG_NEGATIVE]:
                recommendations.extend([
                    {'parameter': 'entry_threshold', 'adjustment': AdjustmentType.INCREASE, 'magnitude': 0.1},
                    {'parameter': 'exit_threshold', 'adjustment': AdjustmentType.DECREASE, 'magnitude': 0.05},
                    {'parameter': 'holding_period', 'adjustment': AdjustmentType.INCREASE, 'magnitude': 0.1}
                ])
        
        # Add context-specific recommendations
        if record.market_regime == 'HIGH_VOLATILITY':
            recommendations.append({
                'parameter': 'volatility_adjustment', 
                'adjustment': AdjustmentType.INCREASE, 
                'magnitude': 0.15
            })
        
        if record.correlation_level < 0.5:
            recommendations.append({
                'parameter': 'correlation_threshold', 
                'adjustment': AdjustmentType.INCREASE, 
                'magnitude': 0.1
            })
        
        return recommendations
    
    def _store_feedback_event(self, event: FeedbackEvent):
        """Store feedback event in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feedback_events 
                (event_id, pair_id, timestamp, metric_type, previous_value, current_value,
                 change_percentage, signal, confidence, market_conditions, strategy_changes,
                 recommended_adjustments, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.pair_id, event.timestamp, event.metric_type.value,
                event.previous_value, event.current_value, event.change_percentage,
                event.signal.value, event.confidence, json.dumps(event.market_conditions),
                json.dumps(event.strategy_changes), json.dumps(event.recommended_adjustments),
                event.processed
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing feedback event: {e}")
    
    def _update_performance_patterns(self, record: PerformanceRecord):
        """Update performance patterns based on new record"""
        try:
            # Identify current conditions
            conditions = {
                'market_regime': record.market_regime,
                'volatility_regime': record.volatility_regime,
                'correlation_level': record.correlation_level,
                'strategy_params': record.strategy_params
            }
            
            # Create pattern key
            pattern_key = self._create_pattern_key(conditions)
            
            # Update or create pattern
            if pattern_key in self.performance_patterns:
                pattern = self.performance_patterns[pattern_key]
                self._update_existing_pattern(pattern, record)
            else:
                self._create_new_pattern(pattern_key, conditions, record)
            
        except Exception as e:
            logger.error(f"Error updating performance patterns: {e}")
    
    def _create_pattern_key(self, conditions: Dict[str, Any]) -> str:
        """Create a unique key for performance pattern"""
        key_parts = [
            conditions.get('market_regime', 'UNKNOWN'),
            conditions.get('volatility_regime', 'UNKNOWN'),
            f"corr_{conditions.get('correlation_level', 0.0):.1f}"
        ]
        
        # Add key strategy parameters
        strategy_params = conditions.get('strategy_params', {})
        for param in ['position_size', 'correlation_threshold', 'stop_loss']:
            if param in strategy_params:
                key_parts.append(f"{param}_{strategy_params[param]:.2f}")
        
        return "_".join(key_parts)
    
    def _create_new_pattern(self, pattern_key: str, conditions: Dict[str, Any], 
                          record: PerformanceRecord):
        """Create a new performance pattern"""
        pattern = PerformancePattern(
            pattern_id=pattern_key,
            pattern_type="PERFORMANCE_PATTERN",
            success_rate=1.0 if record.sharpe_ratio > 0 else 0.0,
            avg_performance=record.sharpe_ratio,
            consistency=1.0,  # Will be updated as more data comes in
            market_conditions=conditions,
            strategy_conditions=conditions.get('strategy_params', {}),
            predictive_accuracy=0.0,  # Will be calculated later
            confidence_interval=(record.sharpe_ratio * 0.8, record.sharpe_ratio * 1.2),
            occurrences=1,
            last_seen=record.timestamp,
            performance_contribution=record.sharpe_ratio
        )
        
        self.performance_patterns[pattern_key] = pattern
        self._store_performance_pattern(pattern)
    
    def _update_existing_pattern(self, pattern: PerformancePattern, record: PerformanceRecord):
        """Update existing performance pattern"""
        # Update success rate
        old_success = pattern.success_rate * pattern.occurrences
        new_success = 1.0 if record.sharpe_ratio > 0 else 0.0
        pattern.success_rate = (old_success + new_success) / (pattern.occurrences + 1)
        
        # Update average performance
        old_avg = pattern.avg_performance * pattern.occurrences
        pattern.avg_performance = (old_avg + record.sharpe_ratio) / (pattern.occurrences + 1)
        
        # Update consistency (inverse of standard deviation)
        # Simplified calculation - would use proper rolling statistics in production
        pattern.consistency = max(0.1, 1.0 - abs(record.sharpe_ratio - pattern.avg_performance))
        
        # Update other fields
        pattern.occurrences += 1
        pattern.last_seen = record.timestamp
        pattern.performance_contribution = pattern.avg_performance * pattern.success_rate
        
        # Update in database
        self._store_performance_pattern(pattern)
    
    def _store_performance_pattern(self, pattern: PerformancePattern):
        """Store performance pattern in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO performance_patterns 
                (pattern_id, pattern_type, success_rate, avg_performance, consistency,
                 market_conditions, strategy_conditions, predictive_accuracy,
                 confidence_interval_low, confidence_interval_high, occurrences,
                 last_seen, performance_contribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id, pattern.pattern_type, pattern.success_rate,
                pattern.avg_performance, pattern.consistency,
                json.dumps(pattern.market_conditions), json.dumps(pattern.strategy_conditions),
                pattern.predictive_accuracy, pattern.confidence_interval[0],
                pattern.confidence_interval[1], pattern.occurrences,
                pattern.last_seen, pattern.performance_contribution
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance pattern: {e}")
    
    def _trigger_learning(self, pair_id: str):
        """Trigger machine learning updates for a pair"""
        try:
            # Get performance history
            history = list(self.performance_history[pair_id])
            if len(history) < self.min_performance_samples:
                return
            
            # Prepare training data
            features, targets = self._prepare_training_data(history)
            
            if len(features) < 10:  # Need minimum samples for ML
                return
            
            # Train performance prediction models
            self._train_performance_predictors(pair_id, features, targets)
            
            # Update pattern recognition
            self._update_pattern_recognition(pair_id, history)
            
            logger.info(f"Learning triggered for {pair_id}")
            
        except Exception as e:
            logger.error(f"Error in learning trigger: {e}")
    
    def _prepare_training_data(self, history: List[PerformanceRecord]) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Prepare training data for ML models"""
        features = []
        targets = {
            'sharpe_ratio': [],
            'max_drawdown': [],
            'total_return': []
        }
        
        for record in history:
            # Feature vector
            feature_vector = [
                record.correlation_level,
                record.volatility,
                record.num_trades,
                record.avg_trade_duration,
                1.0 if record.market_regime == 'HIGH_VOLATILITY' else 0.0,
                1.0 if record.market_regime == 'TRENDING' else 0.0,
                1.0 if record.volatility_regime == 'HIGH' else 0.0,
            ]
            
            # Add strategy parameters
            for param in ['position_size', 'correlation_threshold', 'stop_loss']:
                feature_vector.append(record.strategy_params.get(param, 0.0))
            
            features.append(feature_vector)
            
            # Target values
            targets['sharpe_ratio'].append(record.sharpe_ratio)
            targets['max_drawdown'].append(record.max_drawdown)
            targets['total_return'].append(record.total_return)
        
        return np.array(features), {k: np.array(v) for k, v in targets.items()}
    
    def _train_performance_predictors(self, pair_id: str, features: np.ndarray, 
                                    targets: Dict[str, np.ndarray]):
        """Train performance prediction models"""
        try:
            # Scale features
            scaled_features = self.feature_scalers['performance_scaler'].fit_transform(features)
            
            # Train each predictor
            for target_name, target_values in targets.items():
                if target_name in self.performance_predictors:
                    model = self.performance_predictors[target_name.replace('_', '_') + '_predictor']
                    
                    # Time series cross-validation
                    tscv = TimeSeriesSplit(n_splits=3)
                    scores = []
                    
                    for train_idx, test_idx in tscv.split(scaled_features):
                        X_train, X_test = scaled_features[train_idx], scaled_features[test_idx]
                        y_train, y_test = target_values[train_idx], target_values[test_idx]
                        
                        model.fit(X_train, y_train)
                        y_pred = model.predict(X_test)
                        scores.append(r2_score(y_test, y_pred))
                    
                    # Final training on all data
                    model.fit(scaled_features, target_values)
                    
                    logger.info(f"Trained {target_name} predictor for {pair_id}, avg R² = {np.mean(scores):.3f}")
            
        except Exception as e:
            logger.error(f"Error training performance predictors: {e}")
    
    def _update_pattern_recognition(self, pair_id: str, history: List[PerformanceRecord]):
        """Update pattern recognition models"""
        try:
            # Identify successful periods
            success_labels = [1.0 if record.sharpe_ratio > 0.5 else 0.0 for record in history]
            
            if sum(success_labels) < 5:  # Need some successful periods
                return
            
            # Prepare pattern features
            pattern_features = []
            for record in history:
                pattern_vector = [
                    record.correlation_level,
                    record.volatility,
                    record.win_rate,
                    record.avg_trade_duration,
                    1.0 if record.market_regime == 'TRENDING' else 0.0,
                    1.0 if record.volatility_regime == 'HIGH' else 0.0
                ]
                pattern_features.append(pattern_vector)
            
            pattern_features = np.array(pattern_features)
            scaled_pattern_features = self.feature_scalers['pattern_scaler'].fit_transform(pattern_features)
            
            # Train success classifier
            self.pattern_recognizers['success_classifier'].fit(scaled_pattern_features, success_labels)
            
            logger.info(f"Updated pattern recognition for {pair_id}")
            
        except Exception as e:
            logger.error(f"Error updating pattern recognition: {e}")
    
    def predict_performance(self, pair_id: str, current_conditions: Dict[str, Any]) -> Dict[str, float]:
        """Predict performance based on current conditions"""
        try:
            # Prepare feature vector
            feature_vector = [
                current_conditions.get('correlation_level', 0.0),
                current_conditions.get('volatility', 0.0),
                current_conditions.get('num_trades', 0),
                current_conditions.get('avg_trade_duration', 0.0),
                1.0 if current_conditions.get('market_regime') == 'HIGH_VOLATILITY' else 0.0,
                1.0 if current_conditions.get('market_regime') == 'TRENDING' else 0.0,
                1.0 if current_conditions.get('volatility_regime') == 'HIGH' else 0.0,
            ]
            
            # Add strategy parameters
            strategy_params = current_conditions.get('strategy_params', {})
            for param in ['position_size', 'correlation_threshold', 'stop_loss']:
                feature_vector.append(strategy_params.get(param, 0.0))
            
            feature_vector = np.array(feature_vector).reshape(1, -1)
            scaled_features = self.feature_scalers['performance_scaler'].transform(feature_vector)
            
            # Make predictions
            predictions = {}
            for predictor_name, model in self.performance_predictors.items():
                try:
                    prediction = model.predict(scaled_features)[0]
                    predictions[predictor_name.replace('_predictor', '')] = prediction
                except Exception as e:
                    logger.warning(f"Error predicting with {predictor_name}: {e}")
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return {}
    
    def get_adjustment_recommendations(self, pair_id: str, 
                                    current_performance: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get parameter adjustment recommendations based on current performance"""
        try:
            recommendations = []
            
            # Get recent feedback events
            recent_events = [
                event for event in self.feedback_events
                if event.pair_id == pair_id and 
                event.timestamp > datetime.now() - timedelta(days=7)
            ]
            
            # Analyze patterns
            negative_signals = [
                event for event in recent_events 
                if event.signal in [FeedbackSignal.NEGATIVE, FeedbackSignal.STRONG_NEGATIVE]
            ]
            
            if len(negative_signals) > 2:  # Multiple negative signals
                recommendations.extend([
                    {
                        'parameter': 'position_size',
                        'adjustment': AdjustmentType.DECREASE,
                        'magnitude': 0.2,
                        'reason': 'Multiple negative performance signals'
                    },
                    {
                        'parameter': 'risk_limit',
                        'adjustment': AdjustmentType.DECREASE,
                        'magnitude': 0.15,
                        'reason': 'Risk reduction due to poor performance'
                    }
                ])
            
            # Check specific metrics
            if current_performance.get('sharpe_ratio', 0) < 0.5:
                recommendations.append({
                    'parameter': 'correlation_threshold',
                    'adjustment': AdjustmentType.INCREASE,
                    'magnitude': 0.1,
                    'reason': 'Low Sharpe ratio - increase selectivity'
                })
            
            if current_performance.get('max_drawdown', 0) > 0.15:
                recommendations.append({
                    'parameter': 'stop_loss',
                    'adjustment': AdjustmentType.DECREASE,
                    'magnitude': 0.05,
                    'reason': 'High drawdown - tighten stop losses'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting adjustment recommendations: {e}")
            return []
    
    def apply_adjustment(self, pair_id: str, parameter: str, adjustment: AdjustmentType, 
                        magnitude: float, reason: str) -> bool:
        """Apply parameter adjustment and track effectiveness"""
        try:
            # Get current parameter value (would integrate with actual strategy)
            current_value = self._get_current_parameter_value(pair_id, parameter)
            
            # Calculate new value
            if adjustment == AdjustmentType.INCREASE:
                new_value = current_value * (1 + magnitude)
            elif adjustment == AdjustmentType.DECREASE:
                new_value = current_value * (1 - magnitude)
            elif adjustment == AdjustmentType.RESET:
                new_value = self._get_default_parameter_value(parameter)
            else:
                new_value = current_value
            
            # Apply adjustment (would integrate with actual strategy)
            success = self._apply_parameter_change(pair_id, parameter, new_value)
            
            if success:
                # Record adjustment
                adjustment_record = {
                    'pair_id': pair_id,
                    'timestamp': datetime.now(),
                    'parameter_name': parameter,
                    'old_value': current_value,
                    'new_value': new_value,
                    'adjustment_type': adjustment.value,
                    'reason': reason,
                    'expected_impact': magnitude,
                    'actual_impact': 0.0,  # Will be updated later
                    'effectiveness_score': 0.0  # Will be calculated later
                }
                
                self.adjustment_history[pair_id].append(adjustment_record)
                self._store_adjustment_record(adjustment_record)
                
                # Trigger callbacks
                for callback in self.adjustment_callbacks:
                    try:
                        callback(adjustment_record)
                    except Exception as e:
                        logger.error(f"Error in adjustment callback: {e}")
                
                logger.info(f"Applied adjustment: {parameter} {adjustment.value} by {magnitude:.2%} for {pair_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error applying adjustment: {e}")
            return False
    
    def _get_current_parameter_value(self, pair_id: str, parameter: str) -> float:
        """Get current parameter value (placeholder)"""
        # In practice, this would integrate with the actual strategy
        default_values = {
            'position_size': 0.1,
            'correlation_threshold': 0.7,
            'stop_loss': 0.05,
            'risk_limit': 0.02,
            'max_positions': 10
        }
        return default_values.get(parameter, 1.0)
    
    def _get_default_parameter_value(self, parameter: str) -> float:
        """Get default parameter value"""
        default_values = {
            'position_size': 0.1,
            'correlation_threshold': 0.7,
            'stop_loss': 0.05,
            'risk_limit': 0.02,
            'max_positions': 10
        }
        return default_values.get(parameter, 1.0)
    
    def _apply_parameter_change(self, pair_id: str, parameter: str, new_value: float) -> bool:
        """Apply parameter change to strategy (placeholder)"""
        # In practice, this would integrate with the actual strategy
        logger.info(f"Would apply {parameter} = {new_value} for {pair_id}")
        return True
    
    def _store_adjustment_record(self, record: Dict[str, Any]):
        """Store adjustment record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO adjustment_history 
                (pair_id, timestamp, parameter_name, old_value, new_value, adjustment_type,
                 reason, expected_impact, actual_impact, effectiveness_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['pair_id'], record['timestamp'], record['parameter_name'],
                record['old_value'], record['new_value'], record['adjustment_type'],
                record['reason'], record['expected_impact'], record['actual_impact'],
                record['effectiveness_score']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing adjustment record: {e}")
    
    def start_feedback_loop(self):
        """Start the feedback loop processing"""
        if self.feedback_thread and self.feedback_thread.is_alive():
            logger.warning("Feedback loop already running")
            return
        
        self.stop_event.clear()
        self.feedback_thread = threading.Thread(target=self._feedback_loop, daemon=True)
        self.feedback_thread.start()
        
        logger.info("Feedback loop started")
    
    def stop_feedback_loop(self):
        """Stop the feedback loop processing"""
        self.stop_event.set()
        if self.feedback_thread:
            self.feedback_thread.join(timeout=5)
        
        logger.info("Feedback loop stopped")
    
    def _feedback_loop(self):
        """Main feedback loop processing"""
        while not self.stop_event.is_set():
            try:
                # Process unprocessed feedback events
                self._process_feedback_events()
                
                # Update adjustment effectiveness
                self._update_adjustment_effectiveness()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep
                self.stop_event.wait(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in feedback loop: {e}")
                time.sleep(60)
    
    def _process_feedback_events(self):
        """Process unprocessed feedback events"""
        unprocessed_events = [event for event in self.feedback_events if not event.processed]
        
        for event in unprocessed_events:
            try:
                # Apply recommended adjustments
                for adjustment in event.recommended_adjustments:
                    self.apply_adjustment(
                        event.pair_id,
                        adjustment['parameter'],
                        adjustment['adjustment'],
                        adjustment['magnitude'],
                        f"Feedback response to {event.metric_type.value} change"
                    )
                
                event.processed = True
                
            except Exception as e:
                logger.error(f"Error processing feedback event {event.event_id}: {e}")
    
    def _update_adjustment_effectiveness(self):
        """Update effectiveness scores for adjustments"""
        try:
            for pair_id, adjustments in self.adjustment_history.items():
                for adjustment in adjustments:
                    if adjustment['effectiveness_score'] == 0.0:  # Not yet calculated
                        effectiveness = self._calculate_adjustment_effectiveness(pair_id, adjustment)
                        adjustment['effectiveness_score'] = effectiveness
                        
                        # Update parameter effectiveness tracking
                        param_name = adjustment['parameter_name']
                        if param_name not in self.parameter_effectiveness[pair_id]:
                            self.parameter_effectiveness[pair_id][param_name] = []
                        
                        self.parameter_effectiveness[pair_id][param_name].append(effectiveness)
            
        except Exception as e:
            logger.error(f"Error updating adjustment effectiveness: {e}")
    
    def _calculate_adjustment_effectiveness(self, pair_id: str, adjustment: Dict[str, Any]) -> float:
        """Calculate effectiveness of an adjustment"""
        try:
            # Get performance before and after adjustment
            adjustment_time = adjustment['timestamp']
            before_window = timedelta(days=7)
            after_window = timedelta(days=7)
            
            history = list(self.performance_history[pair_id])
            
            # Performance before adjustment
            before_records = [
                record for record in history
                if adjustment_time - before_window <= record.timestamp <= adjustment_time
            ]
            
            # Performance after adjustment
            after_records = [
                record for record in history
                if adjustment_time <= record.timestamp <= adjustment_time + after_window
            ]
            
            if not before_records or not after_records:
                return 0.0
            
            # Calculate average performance
            before_performance = np.mean([record.sharpe_ratio for record in before_records])
            after_performance = np.mean([record.sharpe_ratio for record in after_records])
            
            # Calculate effectiveness
            if before_performance != 0:
                effectiveness = (after_performance - before_performance) / abs(before_performance)
            else:
                effectiveness = after_performance
            
            return min(1.0, max(-1.0, effectiveness))
            
        except Exception as e:
            logger.error(f"Error calculating adjustment effectiveness: {e}")
            return 0.0
    
    def _cleanup_old_data(self):
        """Clean up old data to prevent memory issues"""
        try:
            cutoff_time = datetime.now() - timedelta(days=30)
            
            # Clean up feedback events
            self.feedback_events = [
                event for event in self.feedback_events
                if event.timestamp > cutoff_time
            ]
            
            # Clean up adjustment history
            for pair_id in self.adjustment_history:
                self.adjustment_history[pair_id] = [
                    adjustment for adjustment in self.adjustment_history[pair_id]
                    if adjustment['timestamp'] > cutoff_time
                ]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        """Get comprehensive feedback system summary"""
        try:
            recent_events = [
                event for event in self.feedback_events
                if event.timestamp > datetime.now() - timedelta(days=7)
            ]
            
            return {
                'pairs_tracked': len(self.performance_history),
                'total_feedback_events': len(self.feedback_events),
                'recent_feedback_events': len(recent_events),
                'performance_patterns': len(self.performance_patterns),
                'adjustment_effectiveness': self._calculate_overall_effectiveness(),
                'top_performing_patterns': self._get_top_patterns(),
                'recent_adjustments': self._get_recent_adjustments(),
                'system_health': self._assess_system_health(),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating feedback summary: {e}")
            return {}
    
    def _calculate_overall_effectiveness(self) -> float:
        """Calculate overall adjustment effectiveness"""
        try:
            all_effectiveness = []
            for pair_effectiveness in self.parameter_effectiveness.values():
                for param_effectiveness in pair_effectiveness.values():
                    all_effectiveness.extend(param_effectiveness)
            
            return np.mean(all_effectiveness) if all_effectiveness else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating overall effectiveness: {e}")
            return 0.0
    
    def _get_top_patterns(self) -> List[Dict[str, Any]]:
        """Get top performing patterns"""
        try:
            patterns = list(self.performance_patterns.values())
            patterns.sort(key=lambda p: p.performance_contribution, reverse=True)
            
            return [
                {
                    'pattern_id': pattern.pattern_id,
                    'success_rate': pattern.success_rate,
                    'avg_performance': pattern.avg_performance,
                    'occurrences': pattern.occurrences,
                    'performance_contribution': pattern.performance_contribution
                }
                for pattern in patterns[:5]
            ]
            
        except Exception as e:
            logger.error(f"Error getting top patterns: {e}")
            return []
    
    def _get_recent_adjustments(self) -> List[Dict[str, Any]]:
        """Get recent adjustments"""
        try:
            recent_adjustments = []
            cutoff_time = datetime.now() - timedelta(days=7)
            
            for pair_id, adjustments in self.adjustment_history.items():
                for adjustment in adjustments:
                    if adjustment['timestamp'] > cutoff_time:
                        recent_adjustments.append({
                            'pair_id': pair_id,
                            'parameter': adjustment['parameter_name'],
                            'adjustment_type': adjustment['adjustment_type'],
                            'effectiveness': adjustment['effectiveness_score'],
                            'timestamp': adjustment['timestamp'].isoformat()
                        })
            
            return sorted(recent_adjustments, key=lambda x: x['timestamp'], reverse=True)[:10]
            
        except Exception as e:
            logger.error(f"Error getting recent adjustments: {e}")
            return []
    
    def _assess_system_health(self) -> str:
        """Assess overall system health"""
        try:
            # Check various health indicators
            health_score = 0
            
            # Check if we have recent data
            if any(len(history) > 0 for history in self.performance_history.values()):
                health_score += 25
            
            # Check if patterns are being learned
            if len(self.performance_patterns) > 0:
                health_score += 25
            
            # Check if adjustments are being made
            recent_adjustments = sum(
                1 for adjustments in self.adjustment_history.values()
                for adj in adjustments
                if adj['timestamp'] > datetime.now() - timedelta(days=7)
            )
            if recent_adjustments > 0:
                health_score += 25
            
            # Check adjustment effectiveness
            overall_effectiveness = self._calculate_overall_effectiveness()
            if overall_effectiveness > 0:
                health_score += 25
            
            if health_score >= 75:
                return "EXCELLENT"
            elif health_score >= 50:
                return "GOOD"
            elif health_score >= 25:
                return "FAIR"
            else:
                return "POOR"
                
        except Exception as e:
            logger.error(f"Error assessing system health: {e}")
            return "UNKNOWN"
    
    def add_feedback_callback(self, callback: Callable[[FeedbackEvent], None]):
        """Add callback for feedback events"""
        self.feedback_callbacks.append(callback)
    
    def add_adjustment_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for adjustment events"""
        self.adjustment_callbacks.append(callback)

# Example usage
if __name__ == "__main__":
    # Create feedback loop
    feedback_loop = PerformanceFeedbackLoop()
    
    # Add callbacks
    def feedback_handler(event: FeedbackEvent):
        print(f"FEEDBACK: {event.pair_id} - {event.metric_type.value} - {event.signal.value}")
    
    def adjustment_handler(adjustment: Dict[str, Any]):
        print(f"ADJUSTMENT: {adjustment['parameter_name']} {adjustment['adjustment_type']} for {adjustment['pair_id']}")
    
    feedback_loop.add_feedback_callback(feedback_handler)
    feedback_loop.add_adjustment_callback(adjustment_handler)
    
    # Start feedback loop
    feedback_loop.start_feedback_loop()
    
    # Simulate performance records
    import random
    
    for i in range(20):
        record = PerformanceRecord(
            pair_id="TSLA_NVDA",
            timestamp=datetime.now() - timedelta(days=20-i),
            sharpe_ratio=random.gauss(0.5, 0.3),
            max_drawdown=random.uniform(0.05, 0.2),
            win_rate=random.uniform(0.4, 0.7),
            profit_factor=random.uniform(0.8, 1.5),
            total_return=random.gauss(0.02, 0.05),
            volatility=random.uniform(0.1, 0.3),
            num_trades=random.randint(10, 50),
            avg_trade_duration=random.uniform(30, 180),
            avg_profit_per_trade=random.gauss(0.001, 0.002),
            market_regime=random.choice(['TRENDING', 'MEAN_REVERTING', 'HIGH_VOLATILITY']),
            volatility_regime=random.choice(['LOW', 'MODERATE', 'HIGH']),
            correlation_level=random.uniform(0.3, 0.9),
            strategy_params={'position_size': 0.1, 'correlation_threshold': 0.7, 'stop_loss': 0.05}
        )
        
        feedback_loop.add_performance_record(record)
    
    # Get summary
    summary = feedback_loop.get_feedback_summary()
    print(json.dumps(summary, indent=2))
    
    # Stop feedback loop
    feedback_loop.stop_feedback_loop() 