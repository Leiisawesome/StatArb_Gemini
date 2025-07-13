"""
Regime Change Monitoring System
===============================

This module provides advanced regime change detection for statistical arbitrage pairs,
using Hidden Markov Models (HMM) and other statistical techniques to identify
market regime transitions that affect pair relationships.

Key Features:
- HMM-based regime detection
- Multi-factor regime analysis
- Regime transition probability estimation
- Market condition integration
- Automated regime change alerts
- Historical regime analysis and learning

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
from collections import defaultdict, deque
import warnings

# Statistical and ML libraries
from scipy import stats
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from hmmlearn import hmm
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegimeType(Enum):
    """Market regime types"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    TRANSITIONAL = "TRANSITIONAL"
    CRISIS = "CRISIS"
    RECOVERY = "RECOVERY"

class RegimeConfidence(Enum):
    """Confidence levels for regime detection"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class RegimeChangeType(Enum):
    """Types of regime changes"""
    GRADUAL_TRANSITION = "GRADUAL_TRANSITION"
    SUDDEN_SHIFT = "SUDDEN_SHIFT"
    CYCLICAL_RETURN = "CYCLICAL_RETURN"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"
    TEMPORARY_DISRUPTION = "TEMPORARY_DISRUPTION"

@dataclass
class RegimeState:
    """Current regime state information"""
    regime_type: RegimeType
    confidence: RegimeConfidence
    probability: float
    duration: timedelta
    stability: float
    
    # Regime characteristics
    mean_return: float
    volatility: float
    correlation_level: float
    trend_strength: float
    
    # Transition probabilities
    transition_probabilities: Dict[RegimeType, float] = field(default_factory=dict)
    expected_duration: Optional[timedelta] = None
    
    # Market factors
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class RegimeChangeEvent:
    """Regime change event"""
    pair_id: str
    event_id: str
    timestamp: datetime
    
    # Regime information
    previous_regime: RegimeType
    new_regime: RegimeType
    change_type: RegimeChangeType
    
    # Detection metrics
    detection_confidence: RegimeConfidence
    detection_probability: float
    statistical_significance: float
    
    # Timing information
    detection_lag: timedelta
    transition_duration: timedelta
    expected_regime_duration: Optional[timedelta]
    
    # Impact assessment
    correlation_impact: float
    volatility_impact: float
    trading_impact: str
    
    # Context
    trigger_factors: List[str]
    market_context: Dict[str, Any]
    
    # Recommendations
    recommended_actions: List[str]
    risk_adjustment: str
    
    acknowledged: bool = False

@dataclass
class RegimeFeatures:
    """Features used for regime detection"""
    returns: np.ndarray
    volatility: np.ndarray
    correlation: np.ndarray
    volume: np.ndarray
    spread: np.ndarray
    
    # Derived features
    momentum: np.ndarray
    mean_reversion: np.ndarray
    trend_strength: np.ndarray
    volatility_regime: np.ndarray
    
    timestamps: List[datetime]

class RegimeChangeMonitor:
    """
    Advanced regime change monitoring system
    
    This class provides comprehensive regime change detection using:
    - Hidden Markov Models for regime identification
    - Multi-factor analysis for regime characterization
    - Transition probability estimation
    - Market condition integration
    - Automated alert generation
    """
    
    def __init__(self, 
                 db_path: str = "regime_monitor.db",
                 n_regimes: int = 5,
                 lookback_window: int = 252,
                 update_frequency: int = 60):
        """
        Initialize the regime change monitor
        
        Args:
            db_path: Path to SQLite database
            n_regimes: Number of regimes to detect
            lookback_window: Lookback window for analysis
            update_frequency: Update frequency in seconds
        """
        self.db_path = db_path
        self.n_regimes = n_regimes
        self.lookback_window = lookback_window
        self.update_frequency = update_frequency
        
        # Data storage
        self.pair_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.lookback_window * 2))
        self.regime_states: Dict[str, RegimeState] = {}
        self.regime_events: List[RegimeChangeEvent] = []
        
        # Models
        self.hmm_models: Dict[str, hmm.GaussianHMM] = {}
        self.feature_scalers: Dict[str, StandardScaler] = {}
        
        # Configuration
        self.regime_thresholds = {
            'confidence_threshold': 0.7,
            'probability_threshold': 0.6,
            'stability_threshold': 0.8,
            'transition_threshold': 0.3
        }
        
        # Callbacks
        self.regime_callbacks: List[Callable[[RegimeChangeEvent], None]] = []
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Regime change monitor initialized with {n_regimes} regimes")
    
    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS regime_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    regime_type TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    probability REAL NOT NULL,
                    duration INTEGER NOT NULL,
                    stability REAL NOT NULL,
                    mean_return REAL,
                    volatility REAL,
                    correlation_level REAL,
                    trend_strength REAL,
                    transition_probabilities TEXT,
                    market_conditions TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS regime_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    previous_regime TEXT NOT NULL,
                    new_regime TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    detection_confidence TEXT NOT NULL,
                    detection_probability REAL NOT NULL,
                    statistical_significance REAL NOT NULL,
                    detection_lag INTEGER,
                    transition_duration INTEGER,
                    correlation_impact REAL,
                    volatility_impact REAL,
                    trading_impact TEXT,
                    trigger_factors TEXT,
                    market_context TEXT,
                    recommended_actions TEXT,
                    risk_adjustment TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS regime_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    returns REAL,
                    volatility REAL,
                    correlation REAL,
                    volume REAL,
                    spread REAL,
                    momentum REAL,
                    mean_reversion REAL,
                    trend_strength REAL,
                    volatility_regime REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Regime monitor database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_pair_data(self, pair_id: str, price1: float, price2: float, 
                     volume1: float = 1.0, volume2: float = 1.0, 
                     timestamp: datetime = None):
        """Add price and volume data for a pair"""
        if timestamp is None:
            timestamp = datetime.now()
        
        data_point = {
            'timestamp': timestamp,
            'price1': price1,
            'price2': price2,
            'volume1': volume1,
            'volume2': volume2
        }
        
        self.pair_data[pair_id].append(data_point)
        
        # Update regime analysis if enough data
        if len(self.pair_data[pair_id]) >= 50:
            self._update_regime_analysis(pair_id)
    
    def _update_regime_analysis(self, pair_id: str):
        """Update regime analysis for a pair"""
        try:
            # Extract features
            features = self._extract_features(pair_id)
            if features is None:
                return
            
            # Train/update HMM model
            self._update_hmm_model(pair_id, features)
            
            # Detect current regime
            current_regime = self._detect_current_regime(pair_id, features)
            
            # Check for regime changes
            self._check_regime_change(pair_id, current_regime)
            
            # Update regime state
            self.regime_states[pair_id] = current_regime
            
            # Store in database
            self._store_regime_state(pair_id, current_regime)
            self._store_features(pair_id, features)
            
        except Exception as e:
            logger.error(f"Error updating regime analysis for {pair_id}: {e}")
    
    def _extract_features(self, pair_id: str) -> Optional[RegimeFeatures]:
        """Extract features for regime detection"""
        try:
            data = list(self.pair_data[pair_id])
            if len(data) < 50:
                return None
            
            # Convert to arrays
            timestamps = [d['timestamp'] for d in data]
            prices1 = np.array([d['price1'] for d in data])
            prices2 = np.array([d['price2'] for d in data])
            volumes1 = np.array([d['volume1'] for d in data])
            volumes2 = np.array([d['volume2'] for d in data])
            
            # Calculate basic features
            returns1 = np.diff(np.log(prices1))
            returns2 = np.diff(np.log(prices2))
            spread_returns = returns1 - returns2
            
            # Rolling correlation
            window = min(20, len(returns1) // 2)
            correlation = np.array([
                np.corrcoef(returns1[max(0, i-window):i+1], returns2[max(0, i-window):i+1])[0, 1]
                if i >= window else 0.0
                for i in range(len(returns1))
            ])
            
            # Volatility (rolling standard deviation)
            volatility = np.array([
                np.std(spread_returns[max(0, i-window):i+1])
                if i >= window else 0.0
                for i in range(len(spread_returns))
            ])
            
            # Volume features
            volume_ratio = volumes1[1:] / (volumes2[1:] + 1e-8)
            
            # Spread
            spread = prices1[1:] - prices2[1:]
            
            # Derived features
            momentum = self._calculate_momentum(spread_returns)
            mean_reversion = self._calculate_mean_reversion(spread)
            trend_strength = self._calculate_trend_strength(spread)
            volatility_regime = self._calculate_volatility_regime(volatility)
            
            return RegimeFeatures(
                returns=spread_returns,
                volatility=volatility,
                correlation=correlation,
                volume=volume_ratio,
                spread=spread,
                momentum=momentum,
                mean_reversion=mean_reversion,
                trend_strength=trend_strength,
                volatility_regime=volatility_regime,
                timestamps=timestamps[1:]  # Adjust for diff
            )
            
        except Exception as e:
            logger.error(f"Error extracting features for {pair_id}: {e}")
            return None
    
    def _calculate_momentum(self, returns: np.ndarray, window: int = 10) -> np.ndarray:
        """Calculate momentum indicator"""
        momentum = np.zeros_like(returns)
        for i in range(window, len(returns)):
            momentum[i] = np.mean(returns[i-window:i])
        return momentum
    
    def _calculate_mean_reversion(self, spread: np.ndarray, window: int = 20) -> np.ndarray:
        """Calculate mean reversion strength"""
        mean_reversion = np.zeros_like(spread)
        for i in range(window, len(spread)):
            window_data = spread[i-window:i]
            # Calculate half-life of mean reversion
            lagged = window_data[:-1]
            changes = np.diff(window_data)
            if len(lagged) > 0 and np.var(lagged) > 0:
                beta = np.cov(changes, lagged)[0, 1] / np.var(lagged)
                half_life = -np.log(2) / np.log(1 + beta) if beta < 0 else np.inf
                mean_reversion[i] = 1.0 / (1.0 + half_life) if half_life != np.inf else 0.0
        return mean_reversion
    
    def _calculate_trend_strength(self, spread: np.ndarray, window: int = 20) -> np.ndarray:
        """Calculate trend strength"""
        trend_strength = np.zeros_like(spread)
        for i in range(window, len(spread)):
            window_data = spread[i-window:i]
            x = np.arange(len(window_data))
            slope, _, r_value, p_value, _ = stats.linregress(x, window_data)
            trend_strength[i] = abs(slope) * (r_value ** 2) if p_value < 0.05 else 0.0
        return trend_strength
    
    def _calculate_volatility_regime(self, volatility: np.ndarray, window: int = 20) -> np.ndarray:
        """Calculate volatility regime indicator"""
        vol_regime = np.zeros_like(volatility)
        for i in range(window, len(volatility)):
            window_vol = volatility[i-window:i]
            current_vol = volatility[i]
            vol_percentile = stats.percentileofscore(window_vol, current_vol) / 100.0
            vol_regime[i] = vol_percentile
        return vol_regime
    
    def _update_hmm_model(self, pair_id: str, features: RegimeFeatures):
        """Update HMM model for regime detection"""
        try:
            # Prepare feature matrix
            feature_matrix = np.column_stack([
                features.returns,
                features.volatility,
                features.correlation,
                features.momentum,
                features.mean_reversion,
                features.trend_strength,
                features.volatility_regime
            ])
            
            # Remove NaN values
            valid_indices = ~np.isnan(feature_matrix).any(axis=1)
            feature_matrix = feature_matrix[valid_indices]
            
            if len(feature_matrix) < 50:
                return
            
            # Scale features
            if pair_id not in self.feature_scalers:
                self.feature_scalers[pair_id] = StandardScaler()
            
            scaled_features = self.feature_scalers[pair_id].fit_transform(feature_matrix)
            
            # Train HMM model
            if pair_id not in self.hmm_models:
                self.hmm_models[pair_id] = hmm.GaussianHMM(
                    n_components=self.n_regimes,
                    covariance_type="full",
                    n_iter=100,
                    random_state=42
                )
            
            # Fit model
            self.hmm_models[pair_id].fit(scaled_features)
            
            logger.debug(f"Updated HMM model for {pair_id}")
            
        except Exception as e:
            logger.error(f"Error updating HMM model for {pair_id}: {e}")
    
    def _detect_current_regime(self, pair_id: str, features: RegimeFeatures) -> RegimeState:
        """Detect current regime state"""
        try:
            if pair_id not in self.hmm_models:
                return self._create_default_regime_state()
            
            # Prepare recent features
            feature_matrix = np.column_stack([
                features.returns[-20:],
                features.volatility[-20:],
                features.correlation[-20:],
                features.momentum[-20:],
                features.mean_reversion[-20:],
                features.trend_strength[-20:],
                features.volatility_regime[-20:]
            ])
            
            # Remove NaN values
            valid_indices = ~np.isnan(feature_matrix).any(axis=1)
            feature_matrix = feature_matrix[valid_indices]
            
            if len(feature_matrix) < 5:
                return self._create_default_regime_state()
            
            # Scale features
            scaled_features = self.feature_scalers[pair_id].transform(feature_matrix)
            
            # Predict regime
            regime_probs = self.hmm_models[pair_id].predict_proba(scaled_features)
            current_regime_id = np.argmax(regime_probs[-1])
            current_regime_prob = regime_probs[-1][current_regime_id]
            
            # Get regime characteristics
            regime_characteristics = self._analyze_regime_characteristics(
                pair_id, current_regime_id, features
            )
            
            # Determine regime type
            regime_type = self._classify_regime_type(regime_characteristics)
            
            # Calculate confidence
            confidence = self._calculate_regime_confidence(current_regime_prob, regime_characteristics)
            
            # Calculate stability
            stability = self._calculate_regime_stability(regime_probs)
            
            # Calculate transition probabilities
            transition_probs = self._calculate_transition_probabilities(pair_id, current_regime_id)
            
            # Estimate duration
            current_time = datetime.now()
            previous_state = self.regime_states.get(pair_id)
            duration = (current_time - previous_state.last_update) if previous_state else timedelta(0)
            
            return RegimeState(
                regime_type=regime_type,
                confidence=confidence,
                probability=current_regime_prob,
                duration=duration,
                stability=stability,
                mean_return=regime_characteristics['mean_return'],
                volatility=regime_characteristics['volatility'],
                correlation_level=regime_characteristics['correlation'],
                trend_strength=regime_characteristics['trend_strength'],
                transition_probabilities=transition_probs,
                market_conditions=self._get_market_conditions(),
                last_update=current_time
            )
            
        except Exception as e:
            logger.error(f"Error detecting current regime for {pair_id}: {e}")
            return self._create_default_regime_state()
    
    def _create_default_regime_state(self) -> RegimeState:
        """Create default regime state"""
        return RegimeState(
            regime_type=RegimeType.TRANSITIONAL,
            confidence=RegimeConfidence.LOW,
            probability=0.5,
            duration=timedelta(0),
            stability=0.5,
            mean_return=0.0,
            volatility=0.1,
            correlation_level=0.5,
            trend_strength=0.0
        )
    
    def _analyze_regime_characteristics(self, pair_id: str, regime_id: int, 
                                     features: RegimeFeatures) -> Dict[str, float]:
        """Analyze characteristics of a specific regime"""
        try:
            model = self.hmm_models[pair_id]
            
            # Get regime parameters from HMM
            regime_mean = model.means_[regime_id]
            regime_cov = model.covars_[regime_id]
            
            # Calculate characteristics
            characteristics = {
                'mean_return': regime_mean[0],  # Returns feature
                'volatility': np.sqrt(regime_cov[1, 1]),  # Volatility feature
                'correlation': regime_mean[2],  # Correlation feature
                'momentum': regime_mean[3],  # Momentum feature
                'mean_reversion': regime_mean[4],  # Mean reversion feature
                'trend_strength': regime_mean[5],  # Trend strength feature
                'volatility_regime': regime_mean[6]  # Volatility regime feature
            }
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Error analyzing regime characteristics: {e}")
            return {
                'mean_return': 0.0,
                'volatility': 0.1,
                'correlation': 0.5,
                'momentum': 0.0,
                'mean_reversion': 0.5,
                'trend_strength': 0.0,
                'volatility_regime': 0.5
            }
    
    def _classify_regime_type(self, characteristics: Dict[str, float]) -> RegimeType:
        """Classify regime type based on characteristics"""
        mean_return = characteristics['mean_return']
        volatility = characteristics['volatility']
        trend_strength = characteristics['trend_strength']
        mean_reversion = characteristics['mean_reversion']
        volatility_regime = characteristics['volatility_regime']
        
        # High volatility regimes
        if volatility_regime > 0.8:
            return RegimeType.HIGH_VOLATILITY
        elif volatility_regime < 0.2:
            return RegimeType.LOW_VOLATILITY
        
        # Crisis detection (high volatility + negative returns)
        if volatility > 0.5 and mean_return < -0.02:
            return RegimeType.CRISIS
        
        # Recovery detection (moderate volatility + positive returns)
        if volatility > 0.2 and mean_return > 0.02:
            return RegimeType.RECOVERY
        
        # Trending regimes
        if trend_strength > 0.3:
            if mean_return > 0:
                return RegimeType.TRENDING_UP
            else:
                return RegimeType.TRENDING_DOWN
        
        # Mean reverting regime
        if mean_reversion > 0.6:
            return RegimeType.MEAN_REVERTING
        
        # Default to transitional
        return RegimeType.TRANSITIONAL
    
    def _calculate_regime_confidence(self, probability: float, 
                                   characteristics: Dict[str, float]) -> RegimeConfidence:
        """Calculate confidence level for regime detection"""
        # Base confidence from probability
        base_confidence = probability
        
        # Adjust based on regime stability
        volatility = characteristics['volatility']
        stability_factor = 1.0 / (1.0 + volatility)
        
        # Combined confidence
        combined_confidence = base_confidence * stability_factor
        
        if combined_confidence > 0.9:
            return RegimeConfidence.VERY_HIGH
        elif combined_confidence > 0.7:
            return RegimeConfidence.HIGH
        elif combined_confidence > 0.5:
            return RegimeConfidence.MEDIUM
        elif combined_confidence > 0.3:
            return RegimeConfidence.LOW
        else:
            return RegimeConfidence.VERY_LOW
    
    def _calculate_regime_stability(self, regime_probs: np.ndarray) -> float:
        """Calculate regime stability"""
        if len(regime_probs) < 5:
            return 0.5
        
        # Calculate entropy of recent regime probabilities
        recent_probs = regime_probs[-5:]
        max_probs = np.max(recent_probs, axis=1)
        stability = np.mean(max_probs)
        
        return stability
    
    def _calculate_transition_probabilities(self, pair_id: str, current_regime: int) -> Dict[RegimeType, float]:
        """Calculate transition probabilities to other regimes"""
        try:
            if pair_id not in self.hmm_models:
                return {}
            
            model = self.hmm_models[pair_id]
            transition_matrix = model.transmat_
            
            # Get transition probabilities from current regime
            transition_probs = transition_matrix[current_regime]
            
            # Map to regime types (simplified mapping)
            regime_types = [
                RegimeType.TRENDING_UP,
                RegimeType.TRENDING_DOWN,
                RegimeType.MEAN_REVERTING,
                RegimeType.HIGH_VOLATILITY,
                RegimeType.LOW_VOLATILITY
            ]
            
            result = {}
            for i, regime_type in enumerate(regime_types[:len(transition_probs)]):
                result[regime_type] = transition_probs[i]
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating transition probabilities: {e}")
            return {}
    
    def _get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions"""
        # Placeholder - in practice, integrate with market data feeds
        return {
            'vix_level': 'MODERATE',
            'market_trend': 'NEUTRAL',
            'liquidity': 'NORMAL',
            'sector_rotation': 'LOW'
        }
    
    def _check_regime_change(self, pair_id: str, current_regime: RegimeState):
        """Check for regime changes and generate events"""
        try:
            previous_state = self.regime_states.get(pair_id)
            
            if previous_state is None:
                return  # First detection
            
            # Check if regime has changed
            if current_regime.regime_type != previous_state.regime_type:
                # Determine change type
                change_type = self._classify_regime_change(previous_state, current_regime)
                
                # Calculate impacts
                correlation_impact = current_regime.correlation_level - previous_state.correlation_level
                volatility_impact = current_regime.volatility - previous_state.volatility
                
                # Generate event
                event = RegimeChangeEvent(
                    pair_id=pair_id,
                    event_id=f"{pair_id}_regime_change_{int(datetime.now().timestamp())}",
                    timestamp=datetime.now(),
                    previous_regime=previous_state.regime_type,
                    new_regime=current_regime.regime_type,
                    change_type=change_type,
                    detection_confidence=current_regime.confidence,
                    detection_probability=current_regime.probability,
                    statistical_significance=self._calculate_change_significance(previous_state, current_regime),
                    detection_lag=timedelta(seconds=self.update_frequency),
                    transition_duration=current_regime.duration,
                    correlation_impact=correlation_impact,
                    volatility_impact=volatility_impact,
                    trading_impact=self._assess_trading_impact(previous_state, current_regime),
                    trigger_factors=self._identify_trigger_factors(previous_state, current_regime),
                    market_context=current_regime.market_conditions,
                    recommended_actions=self._generate_regime_recommendations(current_regime),
                    risk_adjustment=self._assess_risk_adjustment(current_regime)
                )
                
                self.regime_events.append(event)
                self._store_regime_event(event)
                
                # Notify callbacks
                for callback in self.regime_callbacks:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in regime callback: {e}")
                
                logger.info(f"Regime change detected for {pair_id}: {previous_state.regime_type.value} -> {current_regime.regime_type.value}")
            
        except Exception as e:
            logger.error(f"Error checking regime change for {pair_id}: {e}")
    
    def _classify_regime_change(self, previous: RegimeState, current: RegimeState) -> RegimeChangeType:
        """Classify the type of regime change"""
        # Sudden vs gradual change
        if current.probability > 0.8 and previous.probability > 0.8:
            return RegimeChangeType.SUDDEN_SHIFT
        elif current.stability < 0.5:
            return RegimeChangeType.GRADUAL_TRANSITION
        
        # Check for cyclical patterns
        if self._is_cyclical_return(previous.regime_type, current.regime_type):
            return RegimeChangeType.CYCLICAL_RETURN
        
        # Check for structural breaks
        if abs(current.volatility - previous.volatility) > 0.3:
            return RegimeChangeType.STRUCTURAL_BREAK
        
        # Check for temporary disruptions
        if current.regime_type in [RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY]:
            return RegimeChangeType.TEMPORARY_DISRUPTION
        
        return RegimeChangeType.GRADUAL_TRANSITION
    
    def _is_cyclical_return(self, previous_regime: RegimeType, current_regime: RegimeType) -> bool:
        """Check if this is a cyclical return to a previous regime"""
        # Simplified logic - in practice, maintain longer history
        cyclical_pairs = [
            (RegimeType.TRENDING_UP, RegimeType.TRENDING_DOWN),
            (RegimeType.HIGH_VOLATILITY, RegimeType.LOW_VOLATILITY),
            (RegimeType.CRISIS, RegimeType.RECOVERY)
        ]
        
        for pair in cyclical_pairs:
            if (previous_regime, current_regime) in [pair, pair[::-1]]:
                return True
        
        return False
    
    def _calculate_change_significance(self, previous: RegimeState, current: RegimeState) -> float:
        """Calculate statistical significance of regime change"""
        # Simplified significance calculation
        prob_change = abs(current.probability - previous.probability)
        volatility_change = abs(current.volatility - previous.volatility)
        correlation_change = abs(current.correlation_level - previous.correlation_level)
        
        # Weighted significance
        significance = (
            0.4 * prob_change +
            0.3 * volatility_change +
            0.3 * correlation_change
        )
        
        return min(1.0, significance)
    
    def _assess_trading_impact(self, previous: RegimeState, current: RegimeState) -> str:
        """Assess impact on trading strategy"""
        if current.regime_type == RegimeType.CRISIS:
            return "STOP_TRADING"
        elif current.regime_type == RegimeType.HIGH_VOLATILITY:
            return "REDUCE_POSITION_SIZE"
        elif current.regime_type == RegimeType.MEAN_REVERTING:
            return "INCREASE_MEAN_REVERSION_SIGNALS"
        elif current.regime_type in [RegimeType.TRENDING_UP, RegimeType.TRENDING_DOWN]:
            return "ADJUST_FOR_TREND"
        else:
            return "MONITOR_CLOSELY"
    
    def _identify_trigger_factors(self, previous: RegimeState, current: RegimeState) -> List[str]:
        """Identify factors that triggered the regime change"""
        triggers = []
        
        # Volatility triggers
        if current.volatility > previous.volatility * 1.5:
            triggers.append("VOLATILITY_SPIKE")
        
        # Correlation triggers
        if abs(current.correlation_level - previous.correlation_level) > 0.3:
            triggers.append("CORRELATION_BREAKDOWN")
        
        # Trend triggers
        if current.trend_strength > previous.trend_strength * 2:
            triggers.append("TREND_ACCELERATION")
        
        # Market condition triggers
        if current.market_conditions.get('vix_level') == 'HIGH':
            triggers.append("MARKET_STRESS")
        
        return triggers if triggers else ["UNKNOWN"]
    
    def _generate_regime_recommendations(self, regime: RegimeState) -> List[str]:
        """Generate recommendations based on regime"""
        recommendations = []
        
        if regime.regime_type == RegimeType.CRISIS:
            recommendations.extend([
                "CLOSE_ALL_POSITIONS",
                "INCREASE_CASH_ALLOCATION",
                "IMPLEMENT_HEDGING"
            ])
        elif regime.regime_type == RegimeType.HIGH_VOLATILITY:
            recommendations.extend([
                "REDUCE_POSITION_SIZE",
                "TIGHTEN_STOP_LOSSES",
                "INCREASE_MONITORING_FREQUENCY"
            ])
        elif regime.regime_type == RegimeType.MEAN_REVERTING:
            recommendations.extend([
                "INCREASE_MEAN_REVERSION_EXPOSURE",
                "REDUCE_MOMENTUM_STRATEGIES",
                "OPTIMIZE_ENTRY_TIMING"
            ])
        elif regime.regime_type in [RegimeType.TRENDING_UP, RegimeType.TRENDING_DOWN]:
            recommendations.extend([
                "ADJUST_FOR_DIRECTIONAL_BIAS",
                "REDUCE_CONTRARIAN_POSITIONS",
                "MONITOR_TREND_STRENGTH"
            ])
        else:
            recommendations.append("MAINTAIN_CURRENT_STRATEGY")
        
        return recommendations
    
    def _assess_risk_adjustment(self, regime: RegimeState) -> str:
        """Assess required risk adjustment"""
        if regime.regime_type == RegimeType.CRISIS:
            return "MAXIMUM_RISK_REDUCTION"
        elif regime.regime_type == RegimeType.HIGH_VOLATILITY:
            return "HIGH_RISK_REDUCTION"
        elif regime.volatility > 0.3:
            return "MODERATE_RISK_REDUCTION"
        elif regime.regime_type == RegimeType.LOW_VOLATILITY:
            return "RISK_INCREASE_OPPORTUNITY"
        else:
            return "MAINTAIN_CURRENT_RISK"
    
    def _store_regime_state(self, pair_id: str, regime: RegimeState):
        """Store regime state in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO regime_states 
                (pair_id, timestamp, regime_type, confidence, probability, duration,
                 stability, mean_return, volatility, correlation_level, trend_strength,
                 transition_probabilities, market_conditions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pair_id, regime.last_update, regime.regime_type.value,
                regime.confidence.value, regime.probability,
                int(regime.duration.total_seconds()), regime.stability,
                regime.mean_return, regime.volatility, regime.correlation_level,
                regime.trend_strength, json.dumps({k.value: v for k, v in regime.transition_probabilities.items()}),
                json.dumps(regime.market_conditions)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing regime state: {e}")
    
    def _store_regime_event(self, event: RegimeChangeEvent):
        """Store regime change event in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO regime_events 
                (pair_id, event_id, timestamp, previous_regime, new_regime, change_type,
                 detection_confidence, detection_probability, statistical_significance,
                 detection_lag, transition_duration, correlation_impact, volatility_impact,
                 trading_impact, trigger_factors, market_context, recommended_actions,
                 risk_adjustment, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.pair_id, event.event_id, event.timestamp,
                event.previous_regime.value, event.new_regime.value, event.change_type.value,
                event.detection_confidence.value, event.detection_probability,
                event.statistical_significance, int(event.detection_lag.total_seconds()),
                int(event.transition_duration.total_seconds()), event.correlation_impact,
                event.volatility_impact, event.trading_impact,
                json.dumps(event.trigger_factors), json.dumps(event.market_context),
                json.dumps(event.recommended_actions), event.risk_adjustment,
                event.acknowledged
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing regime event: {e}")
    
    def _store_features(self, pair_id: str, features: RegimeFeatures):
        """Store feature data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store recent features
            for i in range(max(0, len(features.timestamps) - 10), len(features.timestamps)):
                cursor.execute('''
                    INSERT INTO regime_features 
                    (pair_id, timestamp, returns, volatility, correlation, volume,
                     spread, momentum, mean_reversion, trend_strength, volatility_regime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pair_id, features.timestamps[i], features.returns[i],
                    features.volatility[i], features.correlation[i], features.volume[i],
                    features.spread[i], features.momentum[i], features.mean_reversion[i],
                    features.trend_strength[i], features.volatility_regime[i]
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing features: {e}")
    
    def get_current_regime(self, pair_id: str) -> Optional[RegimeState]:
        """Get current regime state for a pair"""
        return self.regime_states.get(pair_id)
    
    def get_regime_events(self, pair_id: str = None, hours: int = 24) -> List[RegimeChangeEvent]:
        """Get recent regime change events"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        events = [event for event in self.regime_events if event.timestamp > cutoff_time]
        
        if pair_id:
            events = [event for event in events if event.pair_id == pair_id]
        
        return events
    
    def add_regime_callback(self, callback: Callable[[RegimeChangeEvent], None]):
        """Add callback for regime change notifications"""
        self.regime_callbacks.append(callback)
    
    def acknowledge_regime_event(self, event_id: str):
        """Acknowledge a regime change event"""
        for event in self.regime_events:
            if event.event_id == event_id:
                event.acknowledged = True
                
                # Update database
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE regime_events SET acknowledged = TRUE WHERE event_id = ?', 
                                 (event_id,))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error acknowledging regime event: {e}")
                
                logger.info(f"Regime event {event_id} acknowledged")
                break
    
    def get_monitor_summary(self) -> Dict[str, Any]:
        """Get monitoring summary"""
        recent_events = self.get_regime_events(hours=24)
        
        return {
            'pairs_monitored': len(self.regime_states),
            'recent_regime_changes': len(recent_events),
            'unacknowledged_events': len([e for e in recent_events if not e.acknowledged]),
            'current_regimes': {
                pair_id: state.regime_type.value
                for pair_id, state in self.regime_states.items()
            },
            'model_performance': {
                'average_confidence': np.mean([s.probability for s in self.regime_states.values()]),
                'average_stability': np.mean([s.stability for s in self.regime_states.values()])
            },
            'last_update': datetime.now().isoformat()
        }

# Example usage
if __name__ == "__main__":
    # Create regime monitor
    monitor = RegimeChangeMonitor()
    
    # Add callback
    def regime_change_handler(event: RegimeChangeEvent):
        print(f"REGIME CHANGE: {event.pair_id} - {event.previous_regime.value} -> {event.new_regime.value}")
    
    monitor.add_regime_callback(regime_change_handler)
    
    # Simulate price data
    import random
    
    for i in range(200):
        # Simulate regime change at i=100
        if i < 100:
            price1 = 100 + random.random() * 5
            price2 = 200 + random.random() * 10
        else:
            price1 = 100 + random.random() * 20  # Higher volatility
            price2 = 200 + random.random() * 40
        
        monitor.add_pair_data("TSLA_NVDA", price1, price2)
    
    # Get summary
    summary = monitor.get_monitor_summary()
    print(json.dumps(summary, indent=2)) 