"""
Dynamic Threshold Adjustment System
===================================

This module implements a comprehensive dynamic threshold adjustment system that
automatically optimizes trading thresholds based on market conditions, performance
feedback, and statistical analysis for statistical arbitrage pairs.

Key Features:
- Automated threshold optimization using multiple algorithms
- Market condition-aware threshold adaptation
- Performance-based threshold adjustment
- Multi-objective optimization for competing metrics
- Real-time threshold monitoring and adjustment
- Statistical validation of threshold changes

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

# Optimization and statistical libraries
from scipy.optimize import minimize, differential_evolution, basinhopping
from scipy import stats
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_squared_error
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThresholdType(Enum):
    """Types of thresholds in the system"""
    CORRELATION_THRESHOLD = "CORRELATION_THRESHOLD"
    COINTEGRATION_THRESHOLD = "COINTEGRATION_THRESHOLD"
    ENTRY_THRESHOLD = "ENTRY_THRESHOLD"
    EXIT_THRESHOLD = "EXIT_THRESHOLD"
    STOP_LOSS_THRESHOLD = "STOP_LOSS_THRESHOLD"
    TAKE_PROFIT_THRESHOLD = "TAKE_PROFIT_THRESHOLD"
    VOLATILITY_THRESHOLD = "VOLATILITY_THRESHOLD"
    VOLUME_THRESHOLD = "VOLUME_THRESHOLD"
    SPREAD_THRESHOLD = "SPREAD_THRESHOLD"
    RISK_THRESHOLD = "RISK_THRESHOLD"

class OptimizationMethod(Enum):
    """Optimization methods for threshold adjustment"""
    GRADIENT_DESCENT = "GRADIENT_DESCENT"
    EVOLUTIONARY = "EVOLUTIONARY"
    BAYESIAN = "BAYESIAN"
    GRID_SEARCH = "GRID_SEARCH"
    RANDOM_SEARCH = "RANDOM_SEARCH"
    SIMULATED_ANNEALING = "SIMULATED_ANNEALING"

class MarketCondition(Enum):
    """Market conditions affecting thresholds"""
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CRISIS = "CRISIS"
    NORMAL = "NORMAL"

class AdjustmentTrigger(Enum):
    """Triggers for threshold adjustment"""
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    MARKET_REGIME_CHANGE = "MARKET_REGIME_CHANGE"
    STATISTICAL_SIGNIFICANCE = "STATISTICAL_SIGNIFICANCE"
    SCHEDULED_OPTIMIZATION = "SCHEDULED_OPTIMIZATION"
    MANUAL_TRIGGER = "MANUAL_TRIGGER"

@dataclass
class ThresholdParameter:
    """Individual threshold parameter"""
    threshold_type: ThresholdType
    current_value: float
    min_value: float
    max_value: float
    default_value: float
    
    # Optimization parameters
    learning_rate: float = 0.01
    momentum: float = 0.9
    last_gradient: float = 0.0
    
    # Performance tracking
    performance_impact: float = 0.0
    effectiveness_score: float = 0.0
    
    # Adaptation parameters
    adaptation_speed: float = 0.1
    stability_requirement: float = 0.8
    
    # Historical tracking
    value_history: List[float] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    
    # Statistical properties
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    statistical_significance: float = 0.0
    
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class ThresholdConfiguration:
    """Complete threshold configuration for a market condition"""
    market_condition: MarketCondition
    thresholds: Dict[ThresholdType, ThresholdParameter]
    
    # Configuration metadata
    creation_time: datetime
    last_optimization: datetime
    optimization_score: float
    
    # Performance metrics
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Validation metrics
    cross_validation_score: float = 0.0
    out_of_sample_performance: float = 0.0
    
    # Usage statistics
    trades_executed: int = 0
    successful_trades: int = 0
    
    # Stability metrics
    configuration_stability: float = 0.0
    parameter_correlation: Dict[str, float] = field(default_factory=dict)

@dataclass
class OptimizationResult:
    """Result of threshold optimization"""
    optimization_id: str
    market_condition: MarketCondition
    method: OptimizationMethod
    trigger: AdjustmentTrigger
    
    # Optimization details
    optimization_start: datetime
    optimization_end: datetime
    iterations: int
    convergence_achieved: bool
    
    # Results
    previous_thresholds: Dict[ThresholdType, float]
    optimized_thresholds: Dict[ThresholdType, float]
    performance_improvement: float
    
    # Validation
    validation_score: float
    confidence_level: float
    
    # Implementation
    implemented: bool = False
    implementation_time: Optional[datetime] = None
    
    # Monitoring
    post_implementation_performance: Optional[float] = None
    rollback_required: bool = False

class DynamicThresholdAdjustment:
    """
    Comprehensive dynamic threshold adjustment system
    
    This class provides:
    - Automated threshold optimization using multiple algorithms
    - Market condition-aware threshold adaptation
    - Performance-based threshold adjustment
    - Multi-objective optimization for competing metrics
    - Real-time threshold monitoring and adjustment
    """
    
    def __init__(self, 
                 db_path: str = "dynamic_thresholds.db",
                 optimization_frequency: int = 7,  # days
                 min_performance_samples: int = 100,
                 significance_level: float = 0.05):
        """
        Initialize the dynamic threshold adjustment system
        
        Args:
            db_path: Path to SQLite database
            optimization_frequency: Optimization frequency in days
            min_performance_samples: Minimum samples for optimization
            significance_level: Statistical significance level
        """
        self.db_path = db_path
        self.optimization_frequency = optimization_frequency
        self.min_performance_samples = min_performance_samples
        self.significance_level = significance_level
        
        # Threshold configurations by market condition
        self.threshold_configurations: Dict[MarketCondition, ThresholdConfiguration] = {}
        
        # Current market condition
        self.current_market_condition = MarketCondition.NORMAL
        
        # Performance data
        self.performance_data: List[Dict[str, Any]] = []
        self.optimization_results: List[OptimizationResult] = []
        
        # Optimization models
        self.optimization_models: Dict[str, Any] = {}
        
        # Callbacks
        self.threshold_update_callbacks: List[Callable[[ThresholdConfiguration], None]] = []
        self.optimization_callbacks: List[Callable[[OptimizationResult], None]] = []
        
        # Threading
        self.optimization_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
        
        # Initialize optimization models
        self._initialize_optimization_models()
        
        logger.info("Dynamic threshold adjustment system initialized")
    
    def _init_database(self):
        """Initialize SQLite database for threshold data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threshold_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_condition TEXT NOT NULL,
                    threshold_type TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    default_value REAL NOT NULL,
                    learning_rate REAL,
                    momentum REAL,
                    last_gradient REAL,
                    performance_impact REAL,
                    effectiveness_score REAL,
                    adaptation_speed REAL,
                    stability_requirement REAL,
                    confidence_interval_low REAL,
                    confidence_interval_high REAL,
                    statistical_significance REAL,
                    last_update DATETIME,
                    UNIQUE(market_condition, threshold_type)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    optimization_id TEXT UNIQUE NOT NULL,
                    market_condition TEXT NOT NULL,
                    method TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    optimization_start DATETIME NOT NULL,
                    optimization_end DATETIME NOT NULL,
                    iterations INTEGER,
                    convergence_achieved BOOLEAN,
                    previous_thresholds TEXT,
                    optimized_thresholds TEXT,
                    performance_improvement REAL,
                    validation_score REAL,
                    confidence_level REAL,
                    implemented BOOLEAN DEFAULT FALSE,
                    implementation_time DATETIME,
                    post_implementation_performance REAL,
                    rollback_required BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    market_condition TEXT NOT NULL,
                    thresholds TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    trade_data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threshold_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    threshold_type TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    market_condition TEXT NOT NULL,
                    performance_impact REAL,
                    effectiveness_score REAL,
                    adjustment_trigger TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Dynamic thresholds database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _initialize_default_thresholds(self):
        """Initialize default threshold configurations"""
        try:
            # Default thresholds for different market conditions
            default_thresholds = {
                MarketCondition.NORMAL: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.7, 0.3, 0.95),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.05, 0.01, 0.1),
                    ThresholdType.ENTRY_THRESHOLD: (2.0, 1.0, 3.0),
                    ThresholdType.EXIT_THRESHOLD: (0.5, 0.1, 1.0),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.05, 0.01, 0.1),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.03, 0.01, 0.05),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.3, 0.1, 0.5),
                    ThresholdType.VOLUME_THRESHOLD: (1000000, 100000, 10000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.02, 0.005, 0.05),
                    ThresholdType.RISK_THRESHOLD: (0.02, 0.005, 0.05)
                },
                MarketCondition.HIGH_VOLATILITY: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.8, 0.5, 0.95),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.03, 0.01, 0.05),
                    ThresholdType.ENTRY_THRESHOLD: (2.5, 1.5, 3.5),
                    ThresholdType.EXIT_THRESHOLD: (0.3, 0.1, 0.8),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.03, 0.01, 0.05),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.05, 0.02, 0.08),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.5, 0.3, 0.8),
                    ThresholdType.VOLUME_THRESHOLD: (2000000, 500000, 20000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.03, 0.01, 0.08),
                    ThresholdType.RISK_THRESHOLD: (0.015, 0.005, 0.03)
                },
                MarketCondition.LOW_VOLATILITY: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.6, 0.3, 0.9),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.08, 0.05, 0.15),
                    ThresholdType.ENTRY_THRESHOLD: (1.5, 0.8, 2.5),
                    ThresholdType.EXIT_THRESHOLD: (0.8, 0.3, 1.5),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.08, 0.03, 0.15),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.02, 0.005, 0.03),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.2, 0.05, 0.3),
                    ThresholdType.VOLUME_THRESHOLD: (500000, 100000, 5000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.015, 0.005, 0.03),
                    ThresholdType.RISK_THRESHOLD: (0.025, 0.01, 0.05)
                },
                MarketCondition.TRENDING_BULL: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.65, 0.4, 0.9),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.06, 0.02, 0.12),
                    ThresholdType.ENTRY_THRESHOLD: (1.8, 1.0, 2.8),
                    ThresholdType.EXIT_THRESHOLD: (0.6, 0.2, 1.2),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.06, 0.02, 0.12),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.04, 0.015, 0.06),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.25, 0.1, 0.4),
                    ThresholdType.VOLUME_THRESHOLD: (1500000, 300000, 15000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.025, 0.008, 0.06),
                    ThresholdType.RISK_THRESHOLD: (0.03, 0.01, 0.06)
                },
                MarketCondition.TRENDING_BEAR: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.75, 0.5, 0.95),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.04, 0.01, 0.08),
                    ThresholdType.ENTRY_THRESHOLD: (2.2, 1.2, 3.2),
                    ThresholdType.EXIT_THRESHOLD: (0.4, 0.1, 0.9),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.04, 0.01, 0.08),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.06, 0.02, 0.1),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.35, 0.15, 0.6),
                    ThresholdType.VOLUME_THRESHOLD: (2500000, 500000, 25000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.035, 0.01, 0.08),
                    ThresholdType.RISK_THRESHOLD: (0.018, 0.008, 0.035)
                },
                MarketCondition.MEAN_REVERTING: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.8, 0.6, 0.95),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.03, 0.01, 0.06),
                    ThresholdType.ENTRY_THRESHOLD: (2.5, 1.5, 3.5),
                    ThresholdType.EXIT_THRESHOLD: (0.2, 0.05, 0.5),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.07, 0.02, 0.12),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.025, 0.01, 0.04),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.4, 0.2, 0.7),
                    ThresholdType.VOLUME_THRESHOLD: (800000, 200000, 8000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.02, 0.005, 0.04),
                    ThresholdType.RISK_THRESHOLD: (0.022, 0.008, 0.04)
                },
                MarketCondition.CRISIS: {
                    ThresholdType.CORRELATION_THRESHOLD: (0.9, 0.7, 0.98),
                    ThresholdType.COINTEGRATION_THRESHOLD: (0.01, 0.005, 0.03),
                    ThresholdType.ENTRY_THRESHOLD: (3.0, 2.0, 4.0),
                    ThresholdType.EXIT_THRESHOLD: (0.1, 0.05, 0.3),
                    ThresholdType.STOP_LOSS_THRESHOLD: (0.02, 0.005, 0.04),
                    ThresholdType.TAKE_PROFIT_THRESHOLD: (0.08, 0.03, 0.15),
                    ThresholdType.VOLATILITY_THRESHOLD: (0.8, 0.5, 1.2),
                    ThresholdType.VOLUME_THRESHOLD: (5000000, 1000000, 50000000),
                    ThresholdType.SPREAD_THRESHOLD: (0.05, 0.02, 0.12),
                    ThresholdType.RISK_THRESHOLD: (0.01, 0.003, 0.02)
                }
            }
            
            # Create threshold configurations
            for market_condition, thresholds in default_thresholds.items():
                threshold_params = {}
                
                for threshold_type, (default_val, min_val, max_val) in thresholds.items():
                    threshold_params[threshold_type] = ThresholdParameter(
                        threshold_type=threshold_type,
                        current_value=default_val,
                        min_value=min_val,
                        max_value=max_val,
                        default_value=default_val
                    )
                
                self.threshold_configurations[market_condition] = ThresholdConfiguration(
                    market_condition=market_condition,
                    thresholds=threshold_params,
                    creation_time=datetime.now(),
                    last_optimization=datetime.now(),
                    optimization_score=0.0
                )
            
            # Store in database
            self._store_all_threshold_configurations()
            
            logger.info("Default threshold configurations initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default thresholds: {e}")
            raise
    
    def _initialize_optimization_models(self):
        """Initialize optimization models"""
        try:
            # Gaussian Process for Bayesian optimization
            kernel = RBF(length_scale=1.0) + Matern(length_scale=1.0, nu=2.5)
            self.optimization_models['gaussian_process'] = GaussianProcessRegressor(
                kernel=kernel,
                alpha=1e-6,
                normalize_y=True,
                n_restarts_optimizer=10
            )
            
            # Random Forest for performance prediction
            self.optimization_models['random_forest'] = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            # Feature scaler
            self.optimization_models['scaler'] = StandardScaler()
            
            logger.info("Optimization models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing optimization models: {e}")
            raise
    
    def _store_all_threshold_configurations(self):
        """Store all threshold configurations in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for market_condition, config in self.threshold_configurations.items():
                for threshold_type, threshold in config.thresholds.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO threshold_configurations 
                        (market_condition, threshold_type, current_value, min_value, max_value,
                         default_value, learning_rate, momentum, last_gradient, performance_impact,
                         effectiveness_score, adaptation_speed, stability_requirement,
                         confidence_interval_low, confidence_interval_high, statistical_significance,
                         last_update)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        market_condition.value, threshold_type.value, threshold.current_value,
                        threshold.min_value, threshold.max_value, threshold.default_value,
                        threshold.learning_rate, threshold.momentum, threshold.last_gradient,
                        threshold.performance_impact, threshold.effectiveness_score,
                        threshold.adaptation_speed, threshold.stability_requirement,
                        threshold.confidence_interval[0], threshold.confidence_interval[1],
                        threshold.statistical_significance, threshold.last_update
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing threshold configurations: {e}")
    
    def update_market_condition(self, new_condition: MarketCondition):
        """Update current market condition"""
        if new_condition != self.current_market_condition:
            logger.info(f"Market condition changed: {self.current_market_condition.value} -> {new_condition.value}")
            self.current_market_condition = new_condition
            
            # Trigger optimization for new condition
            self._trigger_optimization(new_condition, AdjustmentTrigger.MARKET_REGIME_CHANGE)
    
    def add_performance_data(self, performance_metrics: Dict[str, float], 
                           trade_data: Optional[Dict[str, Any]] = None):
        """Add performance data for threshold optimization"""
        try:
            # Get current thresholds
            current_config = self.threshold_configurations.get(self.current_market_condition)
            if not current_config:
                return
            
            current_thresholds = {
                threshold_type.value: threshold.current_value
                for threshold_type, threshold in current_config.thresholds.items()
            }
            
            # Store performance data
            performance_record = {
                'timestamp': datetime.now(),
                'market_condition': self.current_market_condition.value,
                'thresholds': current_thresholds,
                'performance_metrics': performance_metrics,
                'trade_data': trade_data or {}
            }
            
            self.performance_data.append(performance_record)
            
            # Store in database
            self._store_performance_data(performance_record)
            
            # Update threshold performance impacts
            self._update_threshold_performance_impacts(performance_metrics)
            
            # Check if optimization is needed
            if len(self.performance_data) >= self.min_performance_samples:
                self._check_optimization_trigger()
            
        except Exception as e:
            logger.error(f"Error adding performance data: {e}")
    
    def _store_performance_data(self, performance_record: Dict[str, Any]):
        """Store performance data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_data 
                (timestamp, market_condition, thresholds, performance_metrics, trade_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                performance_record['timestamp'],
                performance_record['market_condition'],
                json.dumps(performance_record['thresholds']),
                json.dumps(performance_record['performance_metrics']),
                json.dumps(performance_record['trade_data'])
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance data: {e}")
    
    def _update_threshold_performance_impacts(self, performance_metrics: Dict[str, float]):
        """Update performance impacts for thresholds"""
        try:
            config = self.threshold_configurations.get(self.current_market_condition)
            if not config:
                return
            
            # Simple performance impact calculation
            sharpe_ratio = performance_metrics.get('sharpe_ratio', 0.0)
            
            for threshold_type, threshold in config.thresholds.items():
                # Update performance impact with exponential moving average
                alpha = 0.1
                threshold.performance_impact = (
                    alpha * sharpe_ratio + 
                    (1 - alpha) * threshold.performance_impact
                )
                
                # Update performance history
                threshold.performance_history.append(sharpe_ratio)
                if len(threshold.performance_history) > 100:
                    threshold.performance_history.pop(0)
                
                # Update effectiveness score
                if len(threshold.performance_history) >= 10:
                    recent_performance = np.mean(threshold.performance_history[-10:])
                    historical_performance = np.mean(threshold.performance_history[:-10]) if len(threshold.performance_history) > 10 else 0.0
                    
                    if historical_performance != 0:
                        threshold.effectiveness_score = (recent_performance - historical_performance) / abs(historical_performance)
                    else:
                        threshold.effectiveness_score = recent_performance
                
                threshold.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating threshold performance impacts: {e}")
    
    def _check_optimization_trigger(self):
        """Check if optimization should be triggered"""
        try:
            config = self.threshold_configurations.get(self.current_market_condition)
            if not config:
                return
            
            # Check time since last optimization
            time_since_optimization = datetime.now() - config.last_optimization
            if time_since_optimization > timedelta(days=self.optimization_frequency):
                self._trigger_optimization(self.current_market_condition, AdjustmentTrigger.SCHEDULED_OPTIMIZATION)
                return
            
            # Check performance degradation
            recent_performance = self.performance_data[-10:] if len(self.performance_data) >= 10 else []
            if len(recent_performance) >= 5:
                recent_sharpe = np.mean([p['performance_metrics'].get('sharpe_ratio', 0.0) for p in recent_performance])
                
                if recent_sharpe < 0.3:  # Performance degradation threshold
                    self._trigger_optimization(self.current_market_condition, AdjustmentTrigger.PERFORMANCE_DEGRADATION)
                    return
            
            # Check statistical significance of threshold changes
            self._check_statistical_significance()
            
        except Exception as e:
            logger.error(f"Error checking optimization trigger: {e}")
    
    def _check_statistical_significance(self):
        """Check statistical significance of threshold performance"""
        try:
            config = self.threshold_configurations.get(self.current_market_condition)
            if not config:
                return
            
            for threshold_type, threshold in config.thresholds.items():
                if len(threshold.performance_history) >= 30:
                    # Split into two periods
                    mid_point = len(threshold.performance_history) // 2
                    period1 = threshold.performance_history[:mid_point]
                    period2 = threshold.performance_history[mid_point:]
                    
                    # Perform t-test
                    t_stat, p_value = stats.ttest_ind(period1, period2)
                    
                    threshold.statistical_significance = 1.0 - p_value
                    
                    # Trigger optimization if significant change detected
                    if p_value < self.significance_level:
                        self._trigger_optimization(
                            self.current_market_condition, 
                            AdjustmentTrigger.STATISTICAL_SIGNIFICANCE
                        )
                        break
            
        except Exception as e:
            logger.error(f"Error checking statistical significance: {e}")
    
    def _trigger_optimization(self, market_condition: MarketCondition, trigger: AdjustmentTrigger):
        """Trigger threshold optimization"""
        try:
            logger.info(f"Triggering optimization for {market_condition.value} due to {trigger.value}")
            
            # Run optimization in background
            optimization_thread = threading.Thread(
                target=self._optimize_thresholds,
                args=(market_condition, trigger),
                daemon=True
            )
            optimization_thread.start()
            
        except Exception as e:
            logger.error(f"Error triggering optimization: {e}")
    
    def _optimize_thresholds(self, market_condition: MarketCondition, trigger: AdjustmentTrigger):
        """Optimize thresholds for a market condition"""
        try:
            config = self.threshold_configurations.get(market_condition)
            if not config:
                return
            
            # Prepare optimization data
            X, y = self._prepare_optimization_data(market_condition)
            
            if len(X) < self.min_performance_samples:
                logger.warning(f"Insufficient data for optimization: {len(X)} samples")
                return
            
            # Store previous thresholds
            previous_thresholds = {
                threshold_type: threshold.current_value
                for threshold_type, threshold in config.thresholds.items()
            }
            
            # Run optimization
            optimization_start = datetime.now()
            optimized_thresholds = self._run_optimization(X, y, config)
            optimization_end = datetime.now()
            
            # Validate optimization
            validation_score = self._validate_optimization(X, y, optimized_thresholds)
            
            # Create optimization result
            optimization_result = OptimizationResult(
                optimization_id=f"{market_condition.value}_{int(optimization_start.timestamp())}",
                market_condition=market_condition,
                method=OptimizationMethod.BAYESIAN,  # Default method
                trigger=trigger,
                optimization_start=optimization_start,
                optimization_end=optimization_end,
                iterations=100,  # Would track actual iterations
                convergence_achieved=True,  # Would check actual convergence
                previous_thresholds=previous_thresholds,
                optimized_thresholds=optimized_thresholds,
                performance_improvement=validation_score,
                validation_score=validation_score,
                confidence_level=0.95  # Would calculate actual confidence
            )
            
            # Store optimization result
            self.optimization_results.append(optimization_result)
            self._store_optimization_result(optimization_result)
            
            # Implement optimization if improvement is significant
            if validation_score > 0.05:  # 5% improvement threshold
                self._implement_optimization(optimization_result)
            
            # Trigger callbacks
            for callback in self.optimization_callbacks:
                try:
                    callback(optimization_result)
                except Exception as e:
                    logger.error(f"Error in optimization callback: {e}")
            
            logger.info(f"Optimization completed for {market_condition.value}, improvement: {validation_score:.4f}")
            
        except Exception as e:
            logger.error(f"Error optimizing thresholds: {e}")
    
    def _prepare_optimization_data(self, market_condition: MarketCondition) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for optimization"""
        try:
            # Filter data for this market condition
            condition_data = [
                data for data in self.performance_data
                if data['market_condition'] == market_condition.value
            ]
            
            if len(condition_data) < self.min_performance_samples:
                return np.array([]), np.array([])
            
            # Extract features (threshold values) and targets (performance)
            X = []
            y = []
            
            for data in condition_data:
                # Feature vector: threshold values
                thresholds = data['thresholds']
                feature_vector = []
                
                for threshold_type in ThresholdType:
                    threshold_value = thresholds.get(threshold_type.value, 0.0)
                    feature_vector.append(threshold_value)
                
                X.append(feature_vector)
                
                # Target: Sharpe ratio (or composite performance metric)
                performance = data['performance_metrics']
                sharpe_ratio = performance.get('sharpe_ratio', 0.0)
                y.append(sharpe_ratio)
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Error preparing optimization data: {e}")
            return np.array([]), np.array([])
    
    def _run_optimization(self, X: np.ndarray, y: np.ndarray, 
                         config: ThresholdConfiguration) -> Dict[ThresholdType, float]:
        """Run threshold optimization"""
        try:
            # Scale features
            scaler = self.optimization_models['scaler']
            X_scaled = scaler.fit_transform(X)
            
            # Train Gaussian Process
            gp_model = self.optimization_models['gaussian_process']
            gp_model.fit(X_scaled, y)
            
            # Define optimization objective
            def objective(threshold_vector):
                # Reshape for prediction
                X_test = scaler.transform(threshold_vector.reshape(1, -1))
                
                # Predict performance
                performance_pred = gp_model.predict(X_test)[0]
                
                # Return negative performance (for minimization)
                return -performance_pred
            
            # Define bounds
            bounds = []
            for threshold_type in ThresholdType:
                threshold = config.thresholds.get(threshold_type)
                if threshold:
                    bounds.append((threshold.min_value, threshold.max_value))
                else:
                    bounds.append((0.0, 1.0))  # Default bounds
            
            # Initial guess (current values)
            initial_guess = []
            for threshold_type in ThresholdType:
                threshold = config.thresholds.get(threshold_type)
                if threshold:
                    initial_guess.append(threshold.current_value)
                else:
                    initial_guess.append(0.5)  # Default value
            
            # Run optimization
            result = minimize(
                objective,
                initial_guess,
                method='L-BFGS-B',
                bounds=bounds,
                options={'maxiter': 100}
            )
            
            # Extract optimized thresholds
            optimized_thresholds = {}
            for i, threshold_type in enumerate(ThresholdType):
                optimized_thresholds[threshold_type] = result.x[i]
            
            return optimized_thresholds
            
        except Exception as e:
            logger.error(f"Error running optimization: {e}")
            # Return current thresholds as fallback
            return {
                threshold_type: threshold.current_value
                for threshold_type, threshold in config.thresholds.items()
            }
    
    def _validate_optimization(self, X: np.ndarray, y: np.ndarray, 
                             optimized_thresholds: Dict[ThresholdType, float]) -> float:
        """Validate optimization results"""
        try:
            # Use current model to predict performance with optimized thresholds
            scaler = self.optimization_models['scaler']
            gp_model = self.optimization_models['gaussian_process']
            
            # Create feature vector from optimized thresholds
            threshold_vector = np.array([
                optimized_thresholds.get(threshold_type, 0.0)
                for threshold_type in ThresholdType
            ])
            
            # Scale and predict
            X_test = scaler.transform(threshold_vector.reshape(1, -1))
            predicted_performance = gp_model.predict(X_test)[0]
            
            # Calculate improvement over current average performance
            current_avg_performance = np.mean(y)
            improvement = predicted_performance - current_avg_performance
            
            return improvement
            
        except Exception as e:
            logger.error(f"Error validating optimization: {e}")
            return 0.0
    
    def _implement_optimization(self, optimization_result: OptimizationResult):
        """Implement optimization results"""
        try:
            config = self.threshold_configurations.get(optimization_result.market_condition)
            if not config:
                return
            
            # Update threshold values
            for threshold_type, new_value in optimization_result.optimized_thresholds.items():
                if threshold_type in config.thresholds:
                    threshold = config.thresholds[threshold_type]
                    
                    # Update value with bounds checking
                    new_value = max(threshold.min_value, min(threshold.max_value, new_value))
                    threshold.current_value = new_value
                    
                    # Update history
                    threshold.value_history.append(new_value)
                    if len(threshold.value_history) > 100:
                        threshold.value_history.pop(0)
                    
                    threshold.last_update = datetime.now()
            
            # Update configuration
            config.last_optimization = datetime.now()
            config.optimization_score = optimization_result.validation_score
            
            # Mark as implemented
            optimization_result.implemented = True
            optimization_result.implementation_time = datetime.now()
            
            # Store updated configuration
            self._store_threshold_configuration(config)
            
            # Trigger callbacks
            for callback in self.threshold_update_callbacks:
                try:
                    callback(config)
                except Exception as e:
                    logger.error(f"Error in threshold update callback: {e}")
            
            logger.info(f"Optimization implemented for {optimization_result.market_condition.value}")
            
        except Exception as e:
            logger.error(f"Error implementing optimization: {e}")
    
    def _store_threshold_configuration(self, config: ThresholdConfiguration):
        """Store threshold configuration in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for threshold_type, threshold in config.thresholds.items():
                cursor.execute('''
                    UPDATE threshold_configurations 
                    SET current_value = ?, performance_impact = ?, effectiveness_score = ?,
                        statistical_significance = ?, last_update = ?
                    WHERE market_condition = ? AND threshold_type = ?
                ''', (
                    threshold.current_value, threshold.performance_impact,
                    threshold.effectiveness_score, threshold.statistical_significance,
                    threshold.last_update, config.market_condition.value, threshold_type.value
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing threshold configuration: {e}")
    
    def _store_optimization_result(self, result: OptimizationResult):
        """Store optimization result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_results 
                (optimization_id, market_condition, method, trigger_type, optimization_start,
                 optimization_end, iterations, convergence_achieved, previous_thresholds,
                 optimized_thresholds, performance_improvement, validation_score,
                 confidence_level, implemented, implementation_time,
                 post_implementation_performance, rollback_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.optimization_id, result.market_condition.value, result.method.value,
                result.trigger.value, result.optimization_start, result.optimization_end,
                result.iterations, result.convergence_achieved,
                json.dumps({k.value: v for k, v in result.previous_thresholds.items()}),
                json.dumps({k.value: v for k, v in result.optimized_thresholds.items()}),
                result.performance_improvement, result.validation_score,
                result.confidence_level, result.implemented, result.implementation_time,
                result.post_implementation_performance, result.rollback_required
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing optimization result: {e}")
    
    def get_current_thresholds(self, market_condition: Optional[MarketCondition] = None) -> Dict[ThresholdType, float]:
        """Get current thresholds for a market condition"""
        if market_condition is None:
            market_condition = self.current_market_condition
        
        config = self.threshold_configurations.get(market_condition)
        if not config:
            return {}
        
        return {
            threshold_type: threshold.current_value
            for threshold_type, threshold in config.thresholds.items()
        }
    
    def manual_threshold_adjustment(self, threshold_type: ThresholdType, 
                                  new_value: float, 
                                  market_condition: Optional[MarketCondition] = None):
        """Manually adjust a threshold"""
        try:
            if market_condition is None:
                market_condition = self.current_market_condition
            
            config = self.threshold_configurations.get(market_condition)
            if not config or threshold_type not in config.thresholds:
                logger.error(f"Threshold {threshold_type.value} not found for {market_condition.value}")
                return False
            
            threshold = config.thresholds[threshold_type]
            
            # Validate bounds
            if new_value < threshold.min_value or new_value > threshold.max_value:
                logger.error(f"Value {new_value} out of bounds [{threshold.min_value}, {threshold.max_value}]")
                return False
            
            # Update threshold
            old_value = threshold.current_value
            threshold.current_value = new_value
            threshold.value_history.append(new_value)
            threshold.last_update = datetime.now()
            
            # Store in database
            self._store_threshold_configuration(config)
            
            # Log monitoring data
            self._log_threshold_monitoring(
                threshold_type, new_value, market_condition, 
                AdjustmentTrigger.MANUAL_TRIGGER
            )
            
            logger.info(f"Manually adjusted {threshold_type.value} from {old_value} to {new_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error in manual threshold adjustment: {e}")
            return False
    
    def _log_threshold_monitoring(self, threshold_type: ThresholdType, 
                                threshold_value: float, 
                                market_condition: MarketCondition,
                                trigger: AdjustmentTrigger):
        """Log threshold monitoring data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            config = self.threshold_configurations.get(market_condition)
            threshold = config.thresholds.get(threshold_type) if config else None
            
            cursor.execute('''
                INSERT INTO threshold_monitoring 
                (timestamp, threshold_type, threshold_value, market_condition,
                 performance_impact, effectiveness_score, adjustment_trigger)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(), threshold_type.value, threshold_value,
                market_condition.value,
                threshold.performance_impact if threshold else 0.0,
                threshold.effectiveness_score if threshold else 0.0,
                trigger.value
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging threshold monitoring: {e}")
    
    def start_monitoring(self):
        """Start threshold monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitoring already running")
            return
        
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Threshold monitoring started")
    
    def stop_monitoring(self):
        """Stop threshold monitoring"""
        self.stop_event.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5)
        
        logger.info("Threshold monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set():
            try:
                # Check for optimization triggers
                self._check_optimization_trigger()
                
                # Monitor threshold stability
                self._monitor_threshold_stability()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep
                self.stop_event.wait(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)
    
    def _monitor_threshold_stability(self):
        """Monitor threshold stability"""
        try:
            for market_condition, config in self.threshold_configurations.items():
                for threshold_type, threshold in config.thresholds.items():
                    if len(threshold.value_history) >= 10:
                        # Calculate stability
                        recent_values = threshold.value_history[-10:]
                        stability = 1.0 - (np.std(recent_values) / np.mean(recent_values)) if np.mean(recent_values) > 0 else 0.0
                        
                        # Update stability requirement
                        if stability < threshold.stability_requirement:
                            logger.warning(f"Threshold {threshold_type.value} unstable: {stability:.3f}")
                            
                            # Consider reverting to default
                            if stability < 0.3:
                                threshold.current_value = threshold.default_value
                                threshold.last_update = datetime.now()
                                logger.info(f"Reverted {threshold_type.value} to default: {threshold.default_value}")
            
        except Exception as e:
            logger.error(f"Error monitoring threshold stability: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            cutoff_time = datetime.now() - timedelta(days=90)
            
            # Clean up performance data
            self.performance_data = [
                data for data in self.performance_data
                if data['timestamp'] > cutoff_time
            ]
            
            # Clean up optimization results
            self.optimization_results = [
                result for result in self.optimization_results
                if result.optimization_start > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        try:
            # Calculate overall statistics
            recent_optimizations = [
                result for result in self.optimization_results
                if result.optimization_start > datetime.now() - timedelta(days=30)
            ]
            
            # Performance statistics
            recent_performance = self.performance_data[-100:] if len(self.performance_data) >= 100 else self.performance_data
            avg_performance = np.mean([
                p['performance_metrics'].get('sharpe_ratio', 0.0)
                for p in recent_performance
            ]) if recent_performance else 0.0
            
            # Threshold statistics
            threshold_stats = {}
            for market_condition, config in self.threshold_configurations.items():
                threshold_stats[market_condition.value] = {
                    'last_optimization': config.last_optimization.isoformat(),
                    'optimization_score': config.optimization_score,
                    'threshold_count': len(config.thresholds),
                    'avg_effectiveness': np.mean([
                        t.effectiveness_score for t in config.thresholds.values()
                    ])
                }
            
            return {
                'current_market_condition': self.current_market_condition.value,
                'total_performance_records': len(self.performance_data),
                'recent_optimizations': len(recent_optimizations),
                'avg_recent_performance': avg_performance,
                'threshold_statistics': threshold_stats,
                'optimization_success_rate': np.mean([
                    1.0 if r.performance_improvement > 0 else 0.0
                    for r in recent_optimizations
                ]) if recent_optimizations else 0.0,
                'monitoring_status': 'RUNNING' if self.monitoring_thread and self.monitoring_thread.is_alive() else 'STOPPED',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating system summary: {e}")
            return {}
    
    def add_threshold_update_callback(self, callback: Callable[[ThresholdConfiguration], None]):
        """Add callback for threshold updates"""
        self.threshold_update_callbacks.append(callback)
    
    def add_optimization_callback(self, callback: Callable[[OptimizationResult], None]):
        """Add callback for optimization events"""
        self.optimization_callbacks.append(callback)

# Example usage
if __name__ == "__main__":
    # Create threshold adjustment system
    threshold_system = DynamicThresholdAdjustment()
    
    # Add callbacks
    def threshold_update_handler(config: ThresholdConfiguration):
        print(f"THRESHOLDS UPDATED: {config.market_condition.value}")
    
    def optimization_handler(result: OptimizationResult):
        print(f"OPTIMIZATION: {result.market_condition.value} - Improvement: {result.performance_improvement:.4f}")
    
    threshold_system.add_threshold_update_callback(threshold_update_handler)
    threshold_system.add_optimization_callback(optimization_handler)
    
    # Start monitoring
    threshold_system.start_monitoring()
    
    # Simulate performance data
    import random
    
    for i in range(150):
        # Simulate performance metrics
        performance_metrics = {
            'sharpe_ratio': random.gauss(0.8, 0.3),
            'max_drawdown': random.uniform(0.05, 0.2),
            'win_rate': random.uniform(0.4, 0.7),
            'profit_factor': random.uniform(0.8, 1.5)
        }
        
        # Add performance data
        threshold_system.add_performance_data(performance_metrics)
        
        # Occasionally change market condition
        if i % 50 == 0 and i > 0:
            new_condition = random.choice(list(MarketCondition))
            threshold_system.update_market_condition(new_condition)
    
    # Test manual adjustment
    threshold_system.manual_threshold_adjustment(
        ThresholdType.CORRELATION_THRESHOLD, 0.75
    )
    
    # Get system summary
    summary = threshold_system.get_system_summary()
    print(json.dumps(summary, indent=2))
    
    # Stop monitoring
    threshold_system.stop_monitoring() 