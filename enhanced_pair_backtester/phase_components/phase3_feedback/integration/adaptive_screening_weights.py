"""
Adaptive Screening Weights System
=================================

This module implements an adaptive screening weights system that dynamically adjusts
pair selection criteria based on historical performance, market conditions, and
success patterns to optimize pair selection for statistical arbitrage.

Key Features:
- Dynamic weight adjustment based on performance feedback
- Market regime-aware weight adaptation
- Historical performance-based weight optimization
- Multi-objective optimization for screening criteria
- Automated weight rebalancing
- Performance attribution analysis for weights

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

# Optimization and ML libraries
from scipy.optimize import minimize, differential_evolution
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import cross_val_score
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScreeningCriterion(Enum):
    """Screening criteria for pair selection"""
    CORRELATION = "CORRELATION"
    COINTEGRATION = "COINTEGRATION"
    VOLATILITY_MATCH = "VOLATILITY_MATCH"
    LIQUIDITY = "LIQUIDITY"
    SECTOR_SIMILARITY = "SECTOR_SIMILARITY"
    MARKET_CAP_RATIO = "MARKET_CAP_RATIO"
    TRADING_VOLUME = "TRADING_VOLUME"
    PRICE_SPREAD = "PRICE_SPREAD"
    BETA_SIMILARITY = "BETA_SIMILARITY"
    MOMENTUM_DIVERGENCE = "MOMENTUM_DIVERGENCE"

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CRISIS = "CRISIS"
    RECOVERY = "RECOVERY"

class WeightAdjustmentMethod(Enum):
    """Methods for weight adjustment"""
    GRADIENT_DESCENT = "GRADIENT_DESCENT"
    EVOLUTIONARY = "EVOLUTIONARY"
    BAYESIAN = "BAYESIAN"
    REINFORCEMENT = "REINFORCEMENT"

@dataclass
class ScreeningWeight:
    """Individual screening weight configuration"""
    criterion: ScreeningCriterion
    weight: float
    min_weight: float = 0.0
    max_weight: float = 1.0
    
    # Performance tracking
    performance_contribution: float = 0.0
    effectiveness_score: float = 0.0
    
    # Adaptation parameters
    learning_rate: float = 0.01
    momentum: float = 0.9
    last_gradient: float = 0.0
    
    # Historical tracking
    weight_history: List[float] = field(default_factory=list)
    performance_history: List[float] = field(default_factory=list)
    
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class WeightConfiguration:
    """Complete weight configuration for a market regime"""
    regime: MarketRegime
    weights: Dict[ScreeningCriterion, ScreeningWeight]
    
    # Configuration metadata
    creation_time: datetime
    last_optimization: datetime
    optimization_score: float
    
    # Performance metrics
    avg_performance: float = 0.0
    consistency: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Usage statistics
    pairs_selected: int = 0
    successful_pairs: int = 0
    
    # Validation metrics
    cross_validation_score: float = 0.0
    out_of_sample_score: float = 0.0

@dataclass
class PairSelectionResult:
    """Result of pair selection with weights"""
    pair_id: str
    symbol1: str
    symbol2: str
    
    # Selection scores
    overall_score: float
    criterion_scores: Dict[ScreeningCriterion, float]
    
    # Weight contributions
    weight_contributions: Dict[ScreeningCriterion, float]
    
    # Selection context
    market_regime: MarketRegime
    selection_timestamp: datetime
    
    # Performance tracking
    actual_performance: Optional[float] = None
    performance_attribution: Dict[ScreeningCriterion, float] = field(default_factory=dict)

class AdaptiveScreeningWeights:
    """
    Adaptive screening weights system for dynamic pair selection optimization
    
    This class provides:
    - Dynamic weight adjustment based on performance feedback
    - Market regime-aware weight configurations
    - Multi-objective optimization for screening criteria
    - Automated weight rebalancing and validation
    - Performance attribution analysis
    """
    
    def __init__(self, 
                 db_path: str = "adaptive_weights.db",
                 optimization_frequency: int = 7,  # days
                 min_performance_samples: int = 100,
                 weight_decay: float = 0.95):
        """
        Initialize the adaptive screening weights system
        
        Args:
            db_path: Path to SQLite database
            optimization_frequency: How often to optimize weights (days)
            min_performance_samples: Minimum samples for optimization
            weight_decay: Decay factor for historical weights
        """
        self.db_path = db_path
        self.optimization_frequency = optimization_frequency
        self.min_performance_samples = min_performance_samples
        self.weight_decay = weight_decay
        
        # Weight configurations by regime
        self.weight_configurations: Dict[MarketRegime, WeightConfiguration] = {}
        
        # Selection history
        self.selection_history: List[PairSelectionResult] = []
        self.performance_feedback: Dict[str, float] = {}
        
        # Optimization models
        self.optimization_models: Dict[str, Any] = {}
        
        # Current market regime
        self.current_regime = MarketRegime.MEAN_REVERTING
        
        # Callbacks
        self.weight_update_callbacks: List[Callable[[WeightConfiguration], None]] = []
        self.optimization_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Threading
        self.optimization_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Initialize default weights
        self._initialize_default_weights()
        
        # Initialize optimization models
        self._initialize_optimization_models()
        
        logger.info("Adaptive screening weights system initialized")
    
    def _init_database(self):
        """Initialize SQLite database for weight data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weight_configurations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regime TEXT NOT NULL,
                    criterion TEXT NOT NULL,
                    weight REAL NOT NULL,
                    min_weight REAL NOT NULL,
                    max_weight REAL NOT NULL,
                    performance_contribution REAL,
                    effectiveness_score REAL,
                    learning_rate REAL,
                    momentum REAL,
                    last_gradient REAL,
                    last_update DATETIME,
                    UNIQUE(regime, criterion)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS selection_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    symbol1 TEXT NOT NULL,
                    symbol2 TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    criterion_scores TEXT,
                    weight_contributions TEXT,
                    market_regime TEXT NOT NULL,
                    selection_timestamp DATETIME NOT NULL,
                    actual_performance REAL,
                    performance_attribution TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regime TEXT NOT NULL,
                    optimization_timestamp DATETIME NOT NULL,
                    method TEXT NOT NULL,
                    previous_weights TEXT,
                    optimized_weights TEXT,
                    performance_improvement REAL,
                    validation_score REAL,
                    optimization_time REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weight_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    regime TEXT NOT NULL,
                    criterion TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    weight REAL NOT NULL,
                    performance_contribution REAL,
                    effectiveness_score REAL,
                    market_conditions TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Adaptive weights database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _initialize_default_weights(self):
        """Initialize default weight configurations for each market regime"""
        try:
            # Default weights for different market regimes
            default_weights = {
                MarketRegime.TRENDING_BULL: {
                    ScreeningCriterion.CORRELATION: 0.25,
                    ScreeningCriterion.COINTEGRATION: 0.20,
                    ScreeningCriterion.MOMENTUM_DIVERGENCE: 0.15,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.10,
                    ScreeningCriterion.LIQUIDITY: 0.10,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.08,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.07,
                    ScreeningCriterion.TRADING_VOLUME: 0.05
                },
                MarketRegime.TRENDING_BEAR: {
                    ScreeningCriterion.CORRELATION: 0.30,
                    ScreeningCriterion.COINTEGRATION: 0.25,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.15,
                    ScreeningCriterion.LIQUIDITY: 0.10,
                    ScreeningCriterion.MOMENTUM_DIVERGENCE: 0.08,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.07,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.05
                },
                MarketRegime.MEAN_REVERTING: {
                    ScreeningCriterion.CORRELATION: 0.35,
                    ScreeningCriterion.COINTEGRATION: 0.30,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.15,
                    ScreeningCriterion.LIQUIDITY: 0.08,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.07,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.05
                },
                MarketRegime.HIGH_VOLATILITY: {
                    ScreeningCriterion.CORRELATION: 0.20,
                    ScreeningCriterion.COINTEGRATION: 0.15,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.25,
                    ScreeningCriterion.LIQUIDITY: 0.20,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.10,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.05,
                    ScreeningCriterion.TRADING_VOLUME: 0.05
                },
                MarketRegime.LOW_VOLATILITY: {
                    ScreeningCriterion.CORRELATION: 0.40,
                    ScreeningCriterion.COINTEGRATION: 0.35,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.10,
                    ScreeningCriterion.LIQUIDITY: 0.05,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.05,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.05
                },
                MarketRegime.CRISIS: {
                    ScreeningCriterion.CORRELATION: 0.15,
                    ScreeningCriterion.COINTEGRATION: 0.10,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.15,
                    ScreeningCriterion.LIQUIDITY: 0.30,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.15,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.10,
                    ScreeningCriterion.TRADING_VOLUME: 0.05
                },
                MarketRegime.RECOVERY: {
                    ScreeningCriterion.CORRELATION: 0.25,
                    ScreeningCriterion.COINTEGRATION: 0.20,
                    ScreeningCriterion.MOMENTUM_DIVERGENCE: 0.20,
                    ScreeningCriterion.VOLATILITY_MATCH: 0.15,
                    ScreeningCriterion.LIQUIDITY: 0.10,
                    ScreeningCriterion.SECTOR_SIMILARITY: 0.05,
                    ScreeningCriterion.MARKET_CAP_RATIO: 0.05
                }
            }
            
            # Create weight configurations
            for regime, weights in default_weights.items():
                screening_weights = {}
                
                for criterion, weight in weights.items():
                    screening_weights[criterion] = ScreeningWeight(
                        criterion=criterion,
                        weight=weight,
                        min_weight=0.0,
                        max_weight=1.0
                    )
                
                self.weight_configurations[regime] = WeightConfiguration(
                    regime=regime,
                    weights=screening_weights,
                    creation_time=datetime.now(),
                    last_optimization=datetime.now(),
                    optimization_score=0.0
                )
            
            # Store in database
            self._store_all_weight_configurations()
            
            logger.info("Default weight configurations initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default weights: {e}")
            raise
    
    def _initialize_optimization_models(self):
        """Initialize optimization models"""
        try:
            # Performance prediction models
            self.optimization_models = {
                'performance_predictor': RandomForestRegressor(n_estimators=100, random_state=42),
                'weight_optimizer': Ridge(alpha=1.0),
                'regime_classifier': RandomForestRegressor(n_estimators=50, random_state=42)
            }
            
            # Feature scalers
            self.feature_scalers = {
                'weight_scaler': StandardScaler(),
                'performance_scaler': StandardScaler()
            }
            
            logger.info("Optimization models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing optimization models: {e}")
            raise
    
    def _store_all_weight_configurations(self):
        """Store all weight configurations in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for regime, config in self.weight_configurations.items():
                for criterion, weight in config.weights.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO weight_configurations 
                        (regime, criterion, weight, min_weight, max_weight, 
                         performance_contribution, effectiveness_score, learning_rate, 
                         momentum, last_gradient, last_update)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        regime.value, criterion.value, weight.weight, weight.min_weight,
                        weight.max_weight, weight.performance_contribution,
                        weight.effectiveness_score, weight.learning_rate, weight.momentum,
                        weight.last_gradient, weight.last_update
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing weight configurations: {e}")
    
    def update_market_regime(self, new_regime: MarketRegime):
        """Update current market regime"""
        if new_regime != self.current_regime:
            logger.info(f"Market regime changed: {self.current_regime.value} -> {new_regime.value}")
            self.current_regime = new_regime
            
            # Trigger regime-specific optimization if needed
            self._trigger_regime_optimization(new_regime)
    
    def _trigger_regime_optimization(self, regime: MarketRegime):
        """Trigger optimization for a specific regime"""
        try:
            config = self.weight_configurations.get(regime)
            if config:
                # Check if optimization is needed
                time_since_optimization = datetime.now() - config.last_optimization
                
                if time_since_optimization > timedelta(days=self.optimization_frequency):
                    logger.info(f"Triggering optimization for regime {regime.value}")
                    self._optimize_weights_for_regime(regime)
            
        except Exception as e:
            logger.error(f"Error triggering regime optimization: {e}")
    
    def calculate_pair_score(self, pair_data: Dict[str, Any], 
                           regime: Optional[MarketRegime] = None) -> PairSelectionResult:
        """Calculate pair selection score using current weights"""
        try:
            if regime is None:
                regime = self.current_regime
            
            config = self.weight_configurations.get(regime)
            if not config:
                raise ValueError(f"No configuration found for regime {regime.value}")
            
            # Extract pair information
            pair_id = pair_data.get('pair_id', f"{pair_data.get('symbol1', 'UNK')}_{pair_data.get('symbol2', 'UNK')}")
            symbol1 = pair_data.get('symbol1', 'UNK')
            symbol2 = pair_data.get('symbol2', 'UNK')
            
            # Calculate criterion scores
            criterion_scores = self._calculate_criterion_scores(pair_data)
            
            # Calculate weighted score
            overall_score = 0.0
            weight_contributions = {}
            
            for criterion, weight in config.weights.items():
                if criterion in criterion_scores:
                    contribution = weight.weight * criterion_scores[criterion]
                    overall_score += contribution
                    weight_contributions[criterion] = contribution
            
            # Create result
            result = PairSelectionResult(
                pair_id=pair_id,
                symbol1=symbol1,
                symbol2=symbol2,
                overall_score=overall_score,
                criterion_scores=criterion_scores,
                weight_contributions=weight_contributions,
                market_regime=regime,
                selection_timestamp=datetime.now()
            )
            
            # Store selection result
            self.selection_history.append(result)
            self._store_selection_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating pair score: {e}")
            raise
    
    def _calculate_criterion_scores(self, pair_data: Dict[str, Any]) -> Dict[ScreeningCriterion, float]:
        """Calculate scores for each screening criterion"""
        scores = {}
        
        try:
            # Correlation score
            correlation = pair_data.get('correlation', 0.0)
            scores[ScreeningCriterion.CORRELATION] = min(1.0, max(0.0, abs(correlation)))
            
            # Cointegration score
            cointegration_pvalue = pair_data.get('cointegration_pvalue', 1.0)
            scores[ScreeningCriterion.COINTEGRATION] = min(1.0, max(0.0, 1.0 - cointegration_pvalue))
            
            # Volatility match score
            vol1 = pair_data.get('volatility1', 0.0)
            vol2 = pair_data.get('volatility2', 0.0)
            if vol1 > 0 and vol2 > 0:
                vol_ratio = min(vol1, vol2) / max(vol1, vol2)
                scores[ScreeningCriterion.VOLATILITY_MATCH] = vol_ratio
            else:
                scores[ScreeningCriterion.VOLATILITY_MATCH] = 0.0
            
            # Liquidity score
            liquidity1 = pair_data.get('liquidity1', 0.0)
            liquidity2 = pair_data.get('liquidity2', 0.0)
            min_liquidity = min(liquidity1, liquidity2)
            scores[ScreeningCriterion.LIQUIDITY] = min(1.0, min_liquidity / 1000000)  # Normalize by 1M
            
            # Sector similarity score
            sector1 = pair_data.get('sector1', '')
            sector2 = pair_data.get('sector2', '')
            scores[ScreeningCriterion.SECTOR_SIMILARITY] = 1.0 if sector1 == sector2 else 0.0
            
            # Market cap ratio score
            market_cap1 = pair_data.get('market_cap1', 0.0)
            market_cap2 = pair_data.get('market_cap2', 0.0)
            if market_cap1 > 0 and market_cap2 > 0:
                cap_ratio = min(market_cap1, market_cap2) / max(market_cap1, market_cap2)
                scores[ScreeningCriterion.MARKET_CAP_RATIO] = cap_ratio
            else:
                scores[ScreeningCriterion.MARKET_CAP_RATIO] = 0.0
            
            # Trading volume score
            volume1 = pair_data.get('volume1', 0.0)
            volume2 = pair_data.get('volume2', 0.0)
            min_volume = min(volume1, volume2)
            scores[ScreeningCriterion.TRADING_VOLUME] = min(1.0, min_volume / 10000000)  # Normalize by 10M
            
            # Price spread score
            price1 = pair_data.get('price1', 0.0)
            price2 = pair_data.get('price2', 0.0)
            if price1 > 0 and price2 > 0:
                price_ratio = min(price1, price2) / max(price1, price2)
                scores[ScreeningCriterion.PRICE_SPREAD] = price_ratio
            else:
                scores[ScreeningCriterion.PRICE_SPREAD] = 0.0
            
            # Beta similarity score
            beta1 = pair_data.get('beta1', 1.0)
            beta2 = pair_data.get('beta2', 1.0)
            beta_diff = abs(beta1 - beta2)
            scores[ScreeningCriterion.BETA_SIMILARITY] = max(0.0, 1.0 - beta_diff)
            
            # Momentum divergence score
            momentum1 = pair_data.get('momentum1', 0.0)
            momentum2 = pair_data.get('momentum2', 0.0)
            momentum_divergence = abs(momentum1 - momentum2)
            scores[ScreeningCriterion.MOMENTUM_DIVERGENCE] = min(1.0, momentum_divergence / 0.1)  # Normalize by 10%
            
        except Exception as e:
            logger.error(f"Error calculating criterion scores: {e}")
        
        return scores
    
    def _store_selection_result(self, result: PairSelectionResult):
        """Store selection result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO selection_results 
                (pair_id, symbol1, symbol2, overall_score, criterion_scores, 
                 weight_contributions, market_regime, selection_timestamp, 
                 actual_performance, performance_attribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.pair_id, result.symbol1, result.symbol2, result.overall_score,
                json.dumps({k.value: v for k, v in result.criterion_scores.items()}),
                json.dumps({k.value: v for k, v in result.weight_contributions.items()}),
                result.market_regime.value, result.selection_timestamp,
                result.actual_performance, json.dumps(result.performance_attribution)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing selection result: {e}")
    
    def add_performance_feedback(self, pair_id: str, performance: float):
        """Add performance feedback for a selected pair"""
        try:
            self.performance_feedback[pair_id] = performance
            
            # Update selection result
            for result in self.selection_history:
                if result.pair_id == pair_id and result.actual_performance is None:
                    result.actual_performance = performance
                    
                    # Calculate performance attribution
                    result.performance_attribution = self._calculate_performance_attribution(result)
                    
                    # Update weight performance contributions
                    self._update_weight_performance_contributions(result)
                    
                    break
            
            # Trigger optimization if enough feedback
            if len(self.performance_feedback) >= self.min_performance_samples:
                self._trigger_weight_optimization()
            
        except Exception as e:
            logger.error(f"Error adding performance feedback: {e}")
    
    def _calculate_performance_attribution(self, result: PairSelectionResult) -> Dict[ScreeningCriterion, float]:
        """Calculate performance attribution to each criterion"""
        attribution = {}
        
        try:
            if result.actual_performance is None:
                return attribution
            
            # Simple attribution based on weight contributions
            total_contribution = sum(result.weight_contributions.values())
            
            if total_contribution > 0:
                for criterion, contribution in result.weight_contributions.items():
                    attribution[criterion] = (contribution / total_contribution) * result.actual_performance
            
        except Exception as e:
            logger.error(f"Error calculating performance attribution: {e}")
        
        return attribution
    
    def _update_weight_performance_contributions(self, result: PairSelectionResult):
        """Update weight performance contributions based on actual performance"""
        try:
            config = self.weight_configurations.get(result.market_regime)
            if not config or result.actual_performance is None:
                return
            
            # Update performance contributions
            for criterion, attribution in result.performance_attribution.items():
                if criterion in config.weights:
                    weight = config.weights[criterion]
                    
                    # Update performance contribution with exponential moving average
                    alpha = 0.1  # Learning rate
                    weight.performance_contribution = (
                        alpha * attribution + 
                        (1 - alpha) * weight.performance_contribution
                    )
                    
                    # Update effectiveness score
                    weight.effectiveness_score = (
                        alpha * (attribution / max(0.001, abs(result.actual_performance))) + 
                        (1 - alpha) * weight.effectiveness_score
                    )
                    
                    # Update history
                    weight.performance_history.append(attribution)
                    if len(weight.performance_history) > 100:
                        weight.performance_history.pop(0)
                    
                    weight.last_update = datetime.now()
            
            # Store updated weights
            self._store_weight_performance(result)
            
        except Exception as e:
            logger.error(f"Error updating weight performance contributions: {e}")
    
    def _store_weight_performance(self, result: PairSelectionResult):
        """Store weight performance data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            config = self.weight_configurations.get(result.market_regime)
            if not config:
                return
            
            for criterion, weight in config.weights.items():
                cursor.execute('''
                    INSERT INTO weight_performance 
                    (regime, criterion, timestamp, weight, performance_contribution, 
                     effectiveness_score, market_conditions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.market_regime.value, criterion.value, datetime.now(),
                    weight.weight, weight.performance_contribution,
                    weight.effectiveness_score, json.dumps({})
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing weight performance: {e}")
    
    def _trigger_weight_optimization(self):
        """Trigger weight optimization based on performance feedback"""
        try:
            # Check if enough time has passed since last optimization
            for regime, config in self.weight_configurations.items():
                time_since_optimization = datetime.now() - config.last_optimization
                
                if time_since_optimization > timedelta(days=self.optimization_frequency):
                    logger.info(f"Triggering weight optimization for regime {regime.value}")
                    self._optimize_weights_for_regime(regime)
            
        except Exception as e:
            logger.error(f"Error triggering weight optimization: {e}")
    
    def _optimize_weights_for_regime(self, regime: MarketRegime):
        """Optimize weights for a specific market regime"""
        try:
            config = self.weight_configurations.get(regime)
            if not config:
                return
            
            # Get performance data for this regime
            regime_results = [
                result for result in self.selection_history
                if result.market_regime == regime and result.actual_performance is not None
            ]
            
            if len(regime_results) < self.min_performance_samples:
                logger.warning(f"Not enough performance data for regime {regime.value}")
                return
            
            # Prepare optimization data
            X, y = self._prepare_optimization_data(regime_results)
            
            if len(X) < 10:
                logger.warning(f"Insufficient data for optimization: {len(X)} samples")
                return
            
            # Store previous weights
            previous_weights = {k: v.weight for k, v in config.weights.items()}
            
            # Optimize weights
            optimized_weights = self._optimize_weights(X, y, previous_weights)
            
            # Validate optimization
            validation_score = self._validate_optimization(X, y, optimized_weights)
            
            if validation_score > 0:  # Improvement found
                # Update weights
                for criterion, new_weight in optimized_weights.items():
                    if criterion in config.weights:
                        config.weights[criterion].weight = new_weight
                        config.weights[criterion].last_update = datetime.now()
                
                config.last_optimization = datetime.now()
                config.optimization_score = validation_score
                
                # Store optimization results
                self._store_optimization_result(regime, previous_weights, optimized_weights, validation_score)
                
                # Trigger callbacks
                for callback in self.optimization_callbacks:
                    try:
                        callback({
                            'regime': regime.value,
                            'previous_weights': previous_weights,
                            'optimized_weights': optimized_weights,
                            'validation_score': validation_score
                        })
                    except Exception as e:
                        logger.error(f"Error in optimization callback: {e}")
                
                logger.info(f"Weights optimized for regime {regime.value}, validation score: {validation_score:.4f}")
            
        except Exception as e:
            logger.error(f"Error optimizing weights for regime {regime.value}: {e}")
    
    def _prepare_optimization_data(self, results: List[PairSelectionResult]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for weight optimization"""
        X = []
        y = []
        
        for result in results:
            if result.actual_performance is not None:
                # Feature vector: criterion scores
                feature_vector = []
                for criterion in ScreeningCriterion:
                    score = result.criterion_scores.get(criterion, 0.0)
                    feature_vector.append(score)
                
                X.append(feature_vector)
                y.append(result.actual_performance)
        
        return np.array(X), np.array(y)
    
    def _optimize_weights(self, X: np.ndarray, y: np.ndarray, 
                         current_weights: Dict[ScreeningCriterion, float]) -> Dict[ScreeningCriterion, float]:
        """Optimize weights using performance data"""
        try:
            # Extract current weight vector
            weight_vector = np.array([current_weights.get(criterion, 0.0) for criterion in ScreeningCriterion])
            
            # Objective function: maximize correlation between weighted scores and performance
            def objective(weights):
                # Ensure weights sum to 1
                weights = weights / np.sum(weights)
                
                # Calculate weighted scores
                weighted_scores = np.dot(X, weights)
                
                # Return negative correlation (for minimization)
                correlation = np.corrcoef(weighted_scores, y)[0, 1]
                return -correlation if not np.isnan(correlation) else 0.0
            
            # Constraints: weights sum to 1, all weights >= 0
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
            ]
            
            bounds = [(0.0, 1.0) for _ in range(len(ScreeningCriterion))]
            
            # Optimize
            result = minimize(
                objective,
                weight_vector,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                optimized_weights = result.x / np.sum(result.x)  # Normalize
                
                # Convert back to dictionary
                optimized_dict = {}
                for i, criterion in enumerate(ScreeningCriterion):
                    optimized_dict[criterion] = optimized_weights[i]
                
                return optimized_dict
            else:
                logger.warning("Weight optimization failed, returning current weights")
                return current_weights
            
        except Exception as e:
            logger.error(f"Error in weight optimization: {e}")
            return current_weights
    
    def _validate_optimization(self, X: np.ndarray, y: np.ndarray, 
                             optimized_weights: Dict[ScreeningCriterion, float]) -> float:
        """Validate optimization results using cross-validation"""
        try:
            # Convert weights to vector
            weight_vector = np.array([optimized_weights.get(criterion, 0.0) for criterion in ScreeningCriterion])
            weight_vector = weight_vector / np.sum(weight_vector)
            
            # Calculate weighted scores
            weighted_scores = np.dot(X, weight_vector)
            
            # Calculate correlation
            correlation = np.corrcoef(weighted_scores, y)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            logger.error(f"Error validating optimization: {e}")
            return 0.0
    
    def _store_optimization_result(self, regime: MarketRegime, 
                                 previous_weights: Dict[ScreeningCriterion, float],
                                 optimized_weights: Dict[ScreeningCriterion, float],
                                 validation_score: float):
        """Store optimization result in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO optimization_history 
                (regime, optimization_timestamp, method, previous_weights, 
                 optimized_weights, performance_improvement, validation_score, optimization_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                regime.value, datetime.now(), 'GRADIENT_DESCENT',
                json.dumps({k.value: v for k, v in previous_weights.items()}),
                json.dumps({k.value: v for k, v in optimized_weights.items()}),
                validation_score, validation_score, 0.0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing optimization result: {e}")
    
    def get_current_weights(self, regime: Optional[MarketRegime] = None) -> Dict[ScreeningCriterion, float]:
        """Get current weights for a regime"""
        if regime is None:
            regime = self.current_regime
        
        config = self.weight_configurations.get(regime)
        if not config:
            return {}
        
        return {criterion: weight.weight for criterion, weight in config.weights.items()}
    
    def get_weight_performance(self, regime: Optional[MarketRegime] = None) -> Dict[str, Any]:
        """Get weight performance analysis"""
        if regime is None:
            regime = self.current_regime
        
        config = self.weight_configurations.get(regime)
        if not config:
            return {}
        
        performance_data = {}
        
        for criterion, weight in config.weights.items():
            performance_data[criterion.value] = {
                'current_weight': weight.weight,
                'performance_contribution': weight.performance_contribution,
                'effectiveness_score': weight.effectiveness_score,
                'weight_history': weight.weight_history[-10:],  # Last 10 values
                'performance_history': weight.performance_history[-10:],
                'last_update': weight.last_update.isoformat()
            }
        
        return performance_data
    
    def start_optimization_loop(self):
        """Start automatic optimization loop"""
        if self.optimization_thread and self.optimization_thread.is_alive():
            logger.warning("Optimization loop already running")
            return
        
        self.stop_event.clear()
        self.optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self.optimization_thread.start()
        
        logger.info("Optimization loop started")
    
    def stop_optimization_loop(self):
        """Stop automatic optimization loop"""
        self.stop_event.set()
        if self.optimization_thread:
            self.optimization_thread.join(timeout=10)
        
        logger.info("Optimization loop stopped")
    
    def _optimization_loop(self):
        """Main optimization loop"""
        while not self.stop_event.is_set():
            try:
                # Check each regime for optimization needs
                for regime in MarketRegime:
                    config = self.weight_configurations.get(regime)
                    if config:
                        time_since_optimization = datetime.now() - config.last_optimization
                        
                        if time_since_optimization > timedelta(days=self.optimization_frequency):
                            self._optimize_weights_for_regime(regime)
                
                # Sleep for 1 hour
                self.stop_event.wait(3600)
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                time.sleep(3600)  # Wait 1 hour before retrying
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        try:
            # Calculate overall statistics
            total_selections = len(self.selection_history)
            selections_with_performance = len([r for r in self.selection_history if r.actual_performance is not None])
            
            avg_performance = 0.0
            if selections_with_performance > 0:
                avg_performance = np.mean([
                    r.actual_performance for r in self.selection_history 
                    if r.actual_performance is not None
                ])
            
            # Regime statistics
            regime_stats = {}
            for regime in MarketRegime:
                regime_results = [r for r in self.selection_history if r.market_regime == regime]
                regime_performance = [r.actual_performance for r in regime_results if r.actual_performance is not None]
                
                regime_stats[regime.value] = {
                    'total_selections': len(regime_results),
                    'selections_with_performance': len(regime_performance),
                    'avg_performance': np.mean(regime_performance) if regime_performance else 0.0,
                    'last_optimization': self.weight_configurations[regime].last_optimization.isoformat() if regime in self.weight_configurations else None
                }
            
            return {
                'current_regime': self.current_regime.value,
                'total_selections': total_selections,
                'selections_with_performance': selections_with_performance,
                'avg_performance': avg_performance,
                'regime_statistics': regime_stats,
                'weight_configurations': {
                    regime.value: self.get_current_weights(regime)
                    for regime in MarketRegime
                },
                'optimization_status': 'RUNNING' if self.optimization_thread and self.optimization_thread.is_alive() else 'STOPPED',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating system summary: {e}")
            return {}
    
    def add_weight_update_callback(self, callback: Callable[[WeightConfiguration], None]):
        """Add callback for weight updates"""
        self.weight_update_callbacks.append(callback)
    
    def add_optimization_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for optimization events"""
        self.optimization_callbacks.append(callback)

# Example usage
if __name__ == "__main__":
    # Create adaptive weights system
    weights_system = AdaptiveScreeningWeights()
    
    # Add callbacks
    def optimization_handler(result: Dict[str, Any]):
        print(f"OPTIMIZATION: {result['regime']} - Score: {result['validation_score']:.4f}")
    
    weights_system.add_optimization_callback(optimization_handler)
    
    # Start optimization loop
    weights_system.start_optimization_loop()
    
    # Simulate pair selection and performance feedback
    import random
    
    for i in range(100):
        # Simulate pair data
        pair_data = {
            'pair_id': f"PAIR_{i}",
            'symbol1': f"STOCK_{i}A",
            'symbol2': f"STOCK_{i}B",
            'correlation': random.uniform(0.3, 0.9),
            'cointegration_pvalue': random.uniform(0.01, 0.1),
            'volatility1': random.uniform(0.1, 0.5),
            'volatility2': random.uniform(0.1, 0.5),
            'liquidity1': random.uniform(100000, 10000000),
            'liquidity2': random.uniform(100000, 10000000),
            'sector1': random.choice(['TECH', 'FINANCE', 'HEALTHCARE']),
            'sector2': random.choice(['TECH', 'FINANCE', 'HEALTHCARE']),
            'market_cap1': random.uniform(1e9, 100e9),
            'market_cap2': random.uniform(1e9, 100e9)
        }
        
        # Calculate pair score
        result = weights_system.calculate_pair_score(pair_data)
        
        # Simulate performance feedback
        performance = random.gauss(0.02, 0.05)  # 2% average with 5% volatility
        weights_system.add_performance_feedback(result.pair_id, performance)
    
    # Get system summary
    summary = weights_system.get_system_summary()
    print(json.dumps(summary, indent=2))
    
    # Stop optimization loop
    weights_system.stop_optimization_loop() 