#!/usr/bin/env python3
"""
Unified Regime Engine
====================

Centralized regime detection and management system serving as the single source of truth
for market regime analysis across all trading components.

This engine consolidates scattered regime functionality and provides:
- Unified regime detection algorithms
- Consistent regime state management
- Component subscription system
- Regime-based adaptation parameters
- Performance monitoring by regime

Author: Professional Quant System Architect
Version: 1.0
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import threading
from collections import defaultdict, deque
import json

# Scientific computing
try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    import hmmlearn.hmm
    SKLEARN_AVAILABLE = True
    HMM_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    HMM_AVAILABLE = False

logger = logging.getLogger(__name__)

# ================================================================================
# PERFORMANCE UTILITIES
# ================================================================================

class BoundedCache:
    """
    Thread-safe bounded cache with LRU eviction
    Prevents memory leaks from unbounded cache growth
    """
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_order = deque()
        self.max_size = max_size
        self._lock = threading.RLock()
    
    def get(self, key):
        """Get value and update access order"""
        with self._lock:
            if key in self.cache:
                # Move to end (most recent)
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
    
    def put(self, key, value):
        """Put value with LRU eviction"""
        with self._lock:
            if key in self.cache:
                # Update existing
                self.access_order.remove(key)
                self.access_order.append(key)
                self.cache[key] = value
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Evict oldest
                    oldest = self.access_order.popleft()
                    del self.cache[oldest]
                
                self.cache[key] = value
                self.access_order.append(key)
    
    def clear(self):
        """Clear all cached data"""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
    
    def size(self):
        """Get current cache size"""
        with self._lock:
            return len(self.cache)

# ================================================================================
# UNIFIED REGIME TYPES
# ================================================================================

class RegimeType(Enum):
    """
    Unified market regime classification
    Single source of truth for all components
    """
    # Primary Market Regimes
    BULL_TREND = "bull_trend"
    BEAR_TREND = "bear_trend"
    SIDEWAYS = "sideways"
    
    # Volatility Regimes
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    
    # Special Regimes
    REGIME_TRANSITION = "regime_transition"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    
    # Market Structure
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    BREAKOUT = "breakout"
    
    # Unknown/Undefined
    UNKNOWN = "unknown"

class RegimeConfidence(Enum):
    """Confidence levels for regime detection"""
    HIGH = "high"        # > 80% confidence
    MEDIUM = "medium"    # 60-80% confidence
    LOW = "low"          # 40-60% confidence
    UNCERTAIN = "uncertain"  # < 40% confidence

# ================================================================================
# DATA STRUCTURES
# ================================================================================

@dataclass
class RegimeState:
    """Complete regime state information"""
    primary_regime: RegimeType
    secondary_regime: Optional[RegimeType] = None
    confidence: float = 0.0
    confidence_level: RegimeConfidence = RegimeConfidence.UNCERTAIN
    
    # Regime characteristics
    volatility_regime: RegimeType = RegimeType.UNKNOWN
    trend_strength: float = 0.0
    mean_reversion_strength: float = 0.0
    
    # Regime probabilities
    regime_probabilities: Dict[RegimeType, float] = field(default_factory=dict)
    
    # Market conditions
    market_volatility: float = 0.0
    market_volume_ratio: float = 1.0
    correlation_level: float = 0.0
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    regime_duration: timedelta = timedelta(0)
    time_since_transition: timedelta = timedelta(0)
    
    # Metadata
    detection_method: str = "unified"
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'primary_regime': self.primary_regime.value,
            'secondary_regime': self.secondary_regime.value if self.secondary_regime else None,
            'confidence': self.confidence,
            'confidence_level': self.confidence_level.value,
            'volatility_regime': self.volatility_regime.value,
            'trend_strength': self.trend_strength,
            'mean_reversion_strength': self.mean_reversion_strength,
            'regime_probabilities': {k.value: v for k, v in self.regime_probabilities.items()},
            'market_volatility': self.market_volatility,
            'market_volume_ratio': self.market_volume_ratio,
            'correlation_level': self.correlation_level,
            'timestamp': self.timestamp.isoformat(),
            'regime_duration': self.regime_duration.total_seconds(),
            'time_since_transition': self.time_since_transition.total_seconds()
        }

@dataclass
class RegimeTransition:
    """Information about regime transitions"""
    from_regime: RegimeType
    to_regime: RegimeType
    transition_time: datetime
    transition_confidence: float
    transition_triggers: List[str] = field(default_factory=list)
    market_impact: float = 0.0

@dataclass
class RegimeAdaptations:
    """Regime-based adaptation parameters for all components"""
    
    # Strategy Adjustments
    momentum_lookback_multiplier: float = 1.0
    momentum_threshold_adjustment: float = 0.0
    mean_reversion_entry_threshold: float = 2.0
    mean_reversion_exit_threshold: float = 0.5
    pairs_correlation_threshold: float = 0.7
    signal_confidence_multiplier: float = 1.0
    
    # Risk Management Adjustments
    position_size_multiplier: float = 1.0
    stop_loss_multiplier: float = 1.0
    take_profit_multiplier: float = 1.0
    max_positions_adjustment: int = 0
    leverage_limit: float = 1.0
    
    # Portfolio Adjustments
    diversification_requirement: float = 1.0
    sector_concentration_limit: float = 0.3
    rebalance_frequency_hours: int = 24
    
    # Execution Adjustments
    prefer_passive_execution: bool = False
    slippage_buffer_multiplier: float = 1.0
    order_size_reduction: float = 0.0
    execution_urgency: str = "normal"
    use_limit_orders: bool = False
    
    # Universe Selection Adjustments
    quality_score_threshold: float = 0.6
    liquidity_requirement_multiplier: float = 1.0
    volatility_filter_threshold: float = 0.5
    correlation_filter_strength: float = 0.7

@dataclass
class RegimeConfig:
    """Enhanced configuration for regime engine"""
    # Detection settings
    lookback_window: int = 60
    min_data_points: int = 30
    update_frequency_seconds: int = 60
    confidence_threshold: float = 0.3
    
    # Model settings
    n_regimes: int = 5
    use_hmm: bool = True
    use_gmm: bool = True
    ensemble_method: str = "weighted_average"
    
    # Feature settings
    use_price_features: bool = True
    use_volume_features: bool = True
    use_volatility_features: bool = True
    use_technical_indicators: bool = True
    use_cross_asset_features: bool = False
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    max_history_size: int = 1000
    parallel_processing: bool = True
    
    # Memory management
    feature_cache_size: int = 500
    regime_cache_size: int = 1000
    max_subscriber_count: int = 100
    
    # Error handling
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    
    # Security
    enable_input_validation: bool = True
    max_data_points: int = 100000  # Prevent DoS attacks
    
    # Monitoring
    enable_performance_tracking: bool = True
    metrics_update_interval: int = 60
    alert_cooldown_seconds: int = 300
    
    # Notification settings
    enable_notifications: bool = True
    transition_confidence_threshold: float = 0.7
    notification_cooldown_seconds: int = 300

# ================================================================================
# REGIME SUBSCRIBER INTERFACE
# ================================================================================

class IRegimeSubscriber(ABC):
    """Interface for components that subscribe to regime changes"""
    
    @abstractmethod
    async def on_regime_change(self, 
                             old_regime: RegimeState, 
                             new_regime: RegimeState,
                             transition: RegimeTransition) -> None:
        """Handle regime change notification"""
        pass
    
    @abstractmethod
    def get_subscriber_id(self) -> str:
        """Get unique subscriber identifier"""
        pass

# ================================================================================
# UNIFIED REGIME ENGINE
# ================================================================================

class UnifiedRegimeEngine:
    """
    Centralized Regime Engine - Single Source of Truth
    
    Consolidates all regime detection functionality and serves:
    - Strategy adaptation
    - Risk management
    - Portfolio optimization
    - Universe selection
    - Execution timing
    - Performance analytics
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        """Initialize the unified regime engine"""
        self.config = config or RegimeConfig()
        self.logger = logging.getLogger(f"{__name__}.UnifiedRegimeEngine")
        
        # Regime state
        self.current_regime: Optional[RegimeState] = None
        self.regime_history: deque = deque(maxlen=self.config.max_history_size)
        self.transition_history: deque = deque(maxlen=100)
        
        # Models
        self._initialize_models()
        
        # Subscribers
        self.subscribers: Set[IRegimeSubscriber] = set()
        self._subscriber_lock = threading.RLock()
        
        # Enhanced caching with configurable bounds
        self._feature_cache = BoundedCache(max_size=self.config.feature_cache_size)
        self._regime_cache = BoundedCache(max_size=self.config.regime_cache_size)
        self._cache_lock = threading.RLock()
        
        # Performance tracking
        self.performance_metrics = {
            'regime_updates': 0,
            'transitions_detected': 0,
            'avg_detection_time_ms': 0.0,
            'cache_hit_rate': 0.0,
            'last_update': datetime.now()
        }
        
        # Advanced features (Phase 3)
        self.multi_timeframe_states: Dict[str, RegimeState] = {}  # timeframe -> regime
        self.transition_predictor = None
        self.cross_asset_validator = None
        self.regime_stability_scores: Dict[RegimeType, float] = {}
        self.predictive_features: Dict[str, Any] = {}
        self._initialize_advanced_features()
        
        # Regime adaptation mappings
        self._initialize_adaptation_mappings()
        
        self.logger.info("🎯 Unified Regime Engine initialized")
    
    def _initialize_advanced_features(self) -> None:
        """Initialize advanced regime detection features (Phase 3)"""
        try:
            if SKLEARN_AVAILABLE:
                # Initialize regime transition predictor
                from sklearn.ensemble import RandomForestClassifier
                self.transition_predictor = RandomForestClassifier(
                    n_estimators=50,
                    max_depth=5,
                    random_state=42
                )
                self.logger.info("📊 Regime transition predictor initialized")
                
                # Initialize cross-asset validator
                from sklearn.decomposition import PCA
                self.cross_asset_validator = PCA(n_components=3)
                self.logger.info("🔍 Cross-asset validator initialized")
                
        except Exception as e:
            self.logger.warning(f"Could not initialize advanced features: {e}")
    
    def _initialize_models(self) -> None:
        """Initialize regime detection models"""
        self.models = {}
        
        # Gaussian Mixture Model
        if SKLEARN_AVAILABLE and self.config.use_gmm:
            self.models['gmm'] = GaussianMixture(
                n_components=self.config.n_regimes,
                covariance_type='full',
                random_state=42
            )
            self.scaler = StandardScaler()
            self.logger.info("✅ GMM model initialized")
        
        # Hidden Markov Model
        if HMM_AVAILABLE and self.config.use_hmm:
            self.models['hmm'] = hmmlearn.hmm.GaussianHMM(
                n_components=self.config.n_regimes,
                covariance_type='full',
                random_state=42
            )
            self.logger.info("✅ HMM model initialized")
    
    def _initialize_adaptation_mappings(self) -> None:
        """Initialize regime-specific adaptation parameters"""
        self.adaptation_mappings = {
            RegimeType.BULL_TREND: RegimeAdaptations(
                momentum_lookback_multiplier=0.8,
                momentum_threshold_adjustment=-0.5,
                position_size_multiplier=1.2,
                leverage_limit=1.5,
                prefer_passive_execution=False,
                quality_score_threshold=0.5
            ),
            RegimeType.BEAR_TREND: RegimeAdaptations(
                momentum_lookback_multiplier=1.2,
                mean_reversion_entry_threshold=2.5,
                position_size_multiplier=0.7,
                stop_loss_multiplier=0.8,
                prefer_passive_execution=True,
                liquidity_requirement_multiplier=1.5
            ),
            RegimeType.HIGH_VOLATILITY: RegimeAdaptations(
                position_size_multiplier=0.5,
                stop_loss_multiplier=1.5,
                diversification_requirement=1.5,
                slippage_buffer_multiplier=2.0,
                use_limit_orders=True,
                volatility_filter_threshold=0.3
            ),
            RegimeType.LOW_VOLATILITY: RegimeAdaptations(
                mean_reversion_entry_threshold=1.5,
                position_size_multiplier=1.3,
                leverage_limit=2.0,
                execution_urgency="normal",
                quality_score_threshold=0.7
            ),
            RegimeType.SIDEWAYS: RegimeAdaptations(
                mean_reversion_entry_threshold=1.8,
                mean_reversion_exit_threshold=0.3,
                momentum_threshold_adjustment=1.0,
                rebalance_frequency_hours=48,
                correlation_filter_strength=0.8
            ),
            RegimeType.CRISIS: RegimeAdaptations(
                position_size_multiplier=0.3,
                stop_loss_multiplier=0.5,
                max_positions_adjustment=-5,
                leverage_limit=0.5,
                prefer_passive_execution=True,
                use_limit_orders=True,
                liquidity_requirement_multiplier=2.0
            )
        }
    
    async def update_regime(self, 
                          symbol: str,
                          market_data: pd.DataFrame,
                          cross_asset_data: Optional[Dict[str, pd.DataFrame]] = None) -> RegimeState:
        """
        Update regime detection with new market data
        
        Args:
            symbol: Primary symbol for regime detection
            market_data: Market data for the symbol
            cross_asset_data: Optional cross-asset data for enhanced detection
            
        Returns:
            Updated regime state
        """
        start_time = datetime.now()
        
        try:
            # Enhanced input validation
            if not self._validate_inputs(symbol, market_data):
                self.logger.warning(f"Invalid inputs for regime update: {symbol}")
                return self.current_regime or self._get_default_regime()
            
            # Check cache first
            if self.config.enable_caching:
                cached_regime = self._get_cached_regime(symbol)
                if cached_regime:
                    self.performance_metrics['cache_hit_rate'] += 0.01
                    return cached_regime
            
            # Validate data
            if not self._validate_market_data(market_data):
                return self.current_regime or self._get_default_regime()
            
            # Extract features
            features = await self._extract_regime_features(
                market_data, 
                cross_asset_data
            )
            
            # Detect regime using ensemble
            regime_state = await self._detect_regime_ensemble(features, market_data)
            
            # Check for regime transition
            if self.current_regime:
                transition = self._check_regime_transition(
                    self.current_regime,
                    regime_state
                )
                
                if transition:
                    await self._handle_regime_transition(
                        self.current_regime,
                        regime_state,
                        transition
                    )
            
            # Update state
            self.current_regime = regime_state
            self.regime_history.append(regime_state)
            
            # Cache result
            if self.config.enable_caching:
                self._cache_regime(symbol, regime_state)
            
            # Update metrics
            detection_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_metrics(detection_time)
            
            return regime_state
            
        except Exception as e:
            self.logger.error(f"Error updating regime: {e}")
            return self.current_regime or self._get_default_regime()
    
    def _validate_inputs(self, symbol: str, market_data: pd.DataFrame) -> bool:
        """Enhanced input validation with security checks"""
        if not self.config.enable_input_validation:
            return True
        
        # Symbol validation
        if not symbol or not isinstance(symbol, str):
            self.logger.error("Invalid symbol: must be non-empty string")
            return False
        
        if len(symbol) > 20:  # Prevent extremely long symbols
            self.logger.error(f"Symbol too long: {len(symbol)} > 20")
            return False
        
        # Data frame validation
        if not isinstance(market_data, pd.DataFrame):
            self.logger.error("market_data must be pandas DataFrame")
            return False
        
        if len(market_data) > self.config.max_data_points:
            self.logger.error(f"Data too large: {len(market_data)} > {self.config.max_data_points}")
            return False
        
        return self._validate_market_data(market_data)
    
    def _validate_market_data(self, market_data: pd.DataFrame) -> bool:
        """Validate market data quality"""
        if market_data is None or market_data.empty:
            return False
        
        if len(market_data) < self.config.min_data_points:
            return False
        
        required_columns = ['close', 'volume']
        if not all(col in market_data.columns for col in required_columns):
            return False
        
        # Check for NaN values
        if market_data[required_columns].isnull().any().any():
            self.logger.warning("Market data contains NaN values")
            return False
        
        # Check for negative prices or volumes
        if (market_data['close'] <= 0).any():
            self.logger.error("Invalid prices: found negative or zero values")
            return False
        
        if (market_data['volume'] < 0).any():
            self.logger.error("Invalid volumes: found negative values")
            return False
        
        # Check for extreme values that might indicate data corruption
        price_changes = market_data['close'].pct_change().dropna()
        if len(price_changes) > 0 and (abs(price_changes) > 0.5).any():  # 50% price change
            self.logger.warning("Extreme price changes detected - possible data corruption")
            return False
        
        return True
    
    def _get_default_regime(self) -> RegimeState:
        """Get default regime state for error cases"""
        return RegimeState(
            primary_regime=RegimeType.UNKNOWN,
            confidence=0.0,
            confidence_level=RegimeConfidence.UNCERTAIN,
            volatility_regime=RegimeType.UNKNOWN,
            trend_strength=0.0,
            mean_reversion_strength=0.0
        )
    
    async def _extract_regime_features(self,
                                     market_data: pd.DataFrame,
                                     cross_asset_data: Optional[Dict[str, pd.DataFrame]] = None) -> np.ndarray:
        """Extract features for regime detection"""
        features = []
        
        # Price features
        if self.config.use_price_features:
            returns = market_data['close'].pct_change().dropna()
            features.extend([
                returns.mean(),
                returns.std(),
                returns.skew(),
                returns.kurt(),
                np.log(market_data['close'].iloc[-1] / market_data['close'].iloc[0])
            ])
        
        # Volume features
        if self.config.use_volume_features:
            volume_ratio = market_data['volume'] / market_data['volume'].rolling(20).mean()
            features.extend([
                volume_ratio.mean(),
                volume_ratio.std(),
                market_data['volume'].iloc[-1] / market_data['volume'].mean()
            ])
        
        # Volatility features
        if self.config.use_volatility_features:
            volatility = returns.rolling(20).std()
            features.extend([
                volatility.iloc[-1],
                volatility.mean(),
                volatility.max() / volatility.mean() if volatility.mean() > 0 else 1
            ])
        
        # Technical indicators
        if self.config.use_technical_indicators:
            # RSI
            rsi = self._calculate_rsi(market_data['close'])
            features.append(rsi)
            
            # Bollinger Band position
            bb_position = self._calculate_bb_position(market_data['close'])
            features.append(bb_position)
        
        # Cross-asset features
        if self.config.use_cross_asset_features and cross_asset_data:
            correlations = self._calculate_cross_asset_correlations(
                market_data,
                cross_asset_data
            )
            features.extend(correlations)
        
        return np.array(features).reshape(1, -1)
    
    async def _detect_regime_ensemble(self,
                                    features: np.ndarray,
                                    market_data: pd.DataFrame) -> RegimeState:
        """Detect regime using parallel ensemble of models"""
        regime_votes = defaultdict(float)
        total_weight = 0
        
        # Create async tasks for parallel execution
        tasks = []
        
        # GMM detection (async)
        if 'gmm' in self.models and SKLEARN_AVAILABLE:
            tasks.append(self._run_gmm_detection_async(features, market_data))
        
        # HMM detection (async)
        if 'hmm' in self.models:
            tasks.append(self._run_hmm_detection_async(features, market_data))
        
        # Rule-based detection (async)
        tasks.append(self._run_rule_based_detection_async(market_data))
        
        # Execute all models in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Model detection failed: {result}")
                    continue
                
                if result and isinstance(result, dict):
                    regime = result.get('regime')
                    weight = result.get('weight', 0.2)
                    
                    if regime and regime != RegimeType.UNKNOWN:
                        regime_votes[regime] += weight
                        total_weight += weight
        
        # Fallback to synchronous rule-based if all async tasks failed
        if total_weight == 0:
            rule_regime = self._detect_rule_based_regime(market_data)
            regime_votes[rule_regime] += 1.0
            total_weight += 1.0
        
        # Determine primary regime
        if total_weight > 0:
            primary_regime = max(regime_votes.items(), key=lambda x: x[1])[0]
            confidence = regime_votes[primary_regime] / total_weight
        else:
            primary_regime = RegimeType.UNKNOWN
            confidence = 0.0
        
        # Create regime state
        regime_state = RegimeState(
            primary_regime=primary_regime,
            confidence=confidence,
            confidence_level=self._get_confidence_level(confidence),
            regime_probabilities={k: v/total_weight for k, v in regime_votes.items()},
            market_volatility=self._calculate_current_volatility(market_data),
            detection_method="ensemble"
        )
        
        # Add characteristics
        self._add_regime_characteristics(regime_state, market_data)
        
        return regime_state
    
    async def _run_gmm_detection_async(self, features: np.ndarray, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Run GMM detection asynchronously"""
        try:
            # Prepare training features if model not fitted
            if not hasattr(self.models['gmm'], 'converged_'):
                training_features = self._prepare_training_features(market_data)
                if training_features is not None and len(training_features) >= self.config.n_regimes:
                    scaled_training = self.scaler.fit_transform(training_features)
                    self.models['gmm'].fit(scaled_training)
            
            # Now predict on current features
            if hasattr(self.models['gmm'], 'converged_'):
                scaled_features = self.scaler.transform(features)
                gmm_probs = self.models['gmm'].predict_proba(scaled_features)[0]
                gmm_regime = self._map_cluster_to_regime(
                    self.models['gmm'].predict(scaled_features)[0],
                    market_data
                )
                
                return {
                    'regime': gmm_regime,
                    'confidence': np.max(gmm_probs),
                    'weight': 0.4,
                    'model': 'gmm'
                }
        except Exception as e:
            self.logger.warning(f"GMM detection failed: {e}")
            return {'regime': RegimeType.UNKNOWN, 'weight': 0.0, 'model': 'gmm'}
        
        return {'regime': RegimeType.UNKNOWN, 'weight': 0.0, 'model': 'gmm'}
    
    async def _run_hmm_detection_async(self, features: np.ndarray, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Run HMM detection asynchronously"""
        try:
            hmm_regime = self._detect_hmm_regime(features, market_data)
            return {
                'regime': hmm_regime,
                'confidence': 0.7,  # Default confidence for HMM
                'weight': 0.4,
                'model': 'hmm'
            }
        except Exception as e:
            self.logger.warning(f"HMM detection failed: {e}")
            return {'regime': RegimeType.UNKNOWN, 'weight': 0.0, 'model': 'hmm'}
    
    async def _run_rule_based_detection_async(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Run rule-based detection asynchronously"""
        try:
            rule_regime = self._detect_rule_based_regime(market_data)
            return {
                'regime': rule_regime,
                'confidence': 0.6,  # Default confidence for rules
                'weight': 0.2,
                'model': 'rule'
            }
        except Exception as e:
            self.logger.warning(f"Rule-based detection failed: {e}")
            return {'regime': RegimeType.UNKNOWN, 'weight': 0.0, 'model': 'rule'}
    
    def _map_cluster_to_regime(self, cluster: int, market_data: pd.DataFrame) -> RegimeType:
        """Map statistical cluster to regime type"""
        # Simple mapping based on returns and volatility
        returns = market_data['close'].pct_change().dropna()
        avg_return = returns.mean()
        volatility = returns.std()
        
        if cluster == 0:
            if avg_return > 0.001:
                return RegimeType.BULL_TREND
            else:
                return RegimeType.BEAR_TREND
        elif cluster == 1:
            if volatility > 0.02:
                return RegimeType.HIGH_VOLATILITY
            else:
                return RegimeType.LOW_VOLATILITY
        elif cluster == 2:
            return RegimeType.SIDEWAYS
        elif cluster == 3:
            return RegimeType.REGIME_TRANSITION
        else:
            return RegimeType.UNKNOWN
    
    def _detect_hmm_regime(self, features: np.ndarray, market_data: pd.DataFrame) -> RegimeType:
        """Detect regime using Hidden Markov Model"""
        # Simplified HMM detection
        returns = market_data['close'].pct_change().dropna().values.reshape(-1, 1)
        
        if len(returns) < 30:
            return RegimeType.UNKNOWN
        
        self.models['hmm'].fit(returns[-100:])
        states = self.models['hmm'].predict(returns[-30:])
        
        # Map HMM states to regimes based on characteristics
        current_state = states[-1]
        state_returns = returns[-30:][states == current_state]
        
        if len(state_returns) > 0:
            avg_return = np.mean(state_returns)
            vol = np.std(state_returns)
            
            if avg_return > 0.001 and vol < 0.015:
                return RegimeType.BULL_TREND
            elif avg_return < -0.001 and vol < 0.015:
                return RegimeType.BEAR_TREND
            elif vol > 0.025:
                return RegimeType.HIGH_VOLATILITY
            else:
                return RegimeType.SIDEWAYS
        
        return RegimeType.UNKNOWN
    
    def _detect_rule_based_regime(self, market_data: pd.DataFrame) -> RegimeType:
        """Rule-based regime detection with enhanced error handling"""
        try:
            if len(market_data) < self.config.min_data_points:
                return RegimeType.UNKNOWN
            
            returns = market_data['close'].pct_change().dropna()
            prices = market_data['close']
            current_price = prices.iloc[-1]
            
            # Ensure we have enough data for calculations
            if len(prices) < 20:
                return RegimeType.UNKNOWN
            
            # Trend detection
            sma_20 = prices.rolling(20).mean()
            
            # Use 50-period SMA only if we have enough data
            if len(prices) >= 50:
                sma_50 = prices.rolling(50).mean()
                
                # Strong trend detection
                if current_price > sma_20.iloc[-1] > sma_50.iloc[-1]:
                    if returns.tail(20).mean() > 0.001:
                        return RegimeType.BULL_TREND
                elif current_price < sma_20.iloc[-1] < sma_50.iloc[-1]:
                    if returns.tail(20).mean() < -0.001:
                        return RegimeType.BEAR_TREND
            
            # Volatility regime (works with shorter data)
            if len(returns) >= 20:
                recent_vol = returns.tail(20).std()
                hist_vol = returns.std()
                
                if recent_vol > hist_vol * 1.5:
                    return RegimeType.HIGH_VOLATILITY
                elif recent_vol < hist_vol * 0.5:
                    return RegimeType.LOW_VOLATILITY
            
            # Mean reversion detection (requires 20+ periods)
            if len(prices) >= 20:
                bb_std = returns.rolling(20).std().iloc[-1]
                if not np.isnan(bb_std) and bb_std > 0:
                    bb_upper = sma_20.iloc[-1] + 2 * bb_std
                    bb_lower = sma_20.iloc[-1] - 2 * bb_std
                    
                    if bb_lower < current_price < bb_upper:
                        return RegimeType.SIDEWAYS
            
            return RegimeType.UNKNOWN
            
        except Exception as e:
            self.logger.error(f"Rule-based detection error: {e}")
            return RegimeType.UNKNOWN
    
    def _add_regime_characteristics(self, regime_state: RegimeState, market_data: pd.DataFrame) -> None:
        """Add detailed characteristics to regime state"""
        returns = market_data['close'].pct_change().dropna()
        
        # Trend strength
        if len(returns) >= 20:
            trend_slope = np.polyfit(range(20), market_data['close'].tail(20), 1)[0]
            regime_state.trend_strength = abs(trend_slope) / market_data['close'].mean()
        
        # Mean reversion strength
        regime_state.mean_reversion_strength = self._calculate_mean_reversion_strength(returns)
        
        # Volatility regime
        current_vol = returns.tail(20).std()
        if current_vol > 0.02:
            regime_state.volatility_regime = RegimeType.HIGH_VOLATILITY
        else:
            regime_state.volatility_regime = RegimeType.LOW_VOLATILITY
        
        # Volume analysis
        if 'volume' in market_data.columns:
            recent_volume = market_data['volume'].tail(20).mean()
            hist_volume = market_data['volume'].mean()
            regime_state.market_volume_ratio = recent_volume / hist_volume if hist_volume > 0 else 1.0
    
    def _calculate_mean_reversion_strength(self, returns: pd.Series) -> float:
        """Calculate mean reversion strength"""
        if len(returns) < 20:
            return 0.0
        
        # Autocorrelation at lag 1
        autocorr = returns.autocorr(lag=1)
        
        # Negative autocorrelation indicates mean reversion
        return max(0, -autocorr)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        if loss.iloc[-1] == 0:
            return 100.0
        
        rs = gain.iloc[-1] / loss.iloc[-1]
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bb_position(self, prices: pd.Series, period: int = 20) -> float:
        """Calculate Bollinger Band position"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        if std.iloc[-1] == 0:
            return 0.5
        
        upper_band = sma.iloc[-1] + 2 * std.iloc[-1]
        lower_band = sma.iloc[-1] - 2 * std.iloc[-1]
        
        position = (prices.iloc[-1] - lower_band) / (upper_band - lower_band)
        return np.clip(position, 0, 1)
    
    def _calculate_current_volatility(self, market_data: pd.DataFrame) -> float:
        """Calculate current market volatility"""
        returns = market_data['close'].pct_change().dropna()
        if len(returns) >= 20:
            return returns.tail(20).std() * np.sqrt(252)  # Annualized
        return 0.0
    
    def _calculate_cross_asset_correlations(self,
                                          market_data: pd.DataFrame,
                                          cross_asset_data: Dict[str, pd.DataFrame]) -> List[float]:
        """Calculate cross-asset correlations"""
        correlations = []
        
        primary_returns = market_data['close'].pct_change().dropna()
        
        for asset, data in list(cross_asset_data.items())[:3]:  # Top 3 correlations
            if 'close' in data.columns:
                asset_returns = data['close'].pct_change().dropna()
                
                # Align indices
                common_idx = primary_returns.index.intersection(asset_returns.index)
                if len(common_idx) >= 20:
                    corr = primary_returns[common_idx].corr(asset_returns[common_idx])
                    correlations.append(corr)
        
        return correlations
    
    # ================================================================================
    # PHASE 3: ADVANCED FEATURES
    # ================================================================================
    
    async def update_multi_timeframe_regime(self, symbol: str, market_data: pd.DataFrame,
                                          timeframes: List[str] = None) -> Dict[str, RegimeState]:
        """
        Analyze regime across multiple timeframes for comprehensive market view
        
        Args:
            symbol: Trading symbol
            market_data: Full market data (will be resampled)
            timeframes: List of timeframes to analyze (e.g., ['5min', '1H', '1D'])
        
        Returns:
            Dictionary mapping timeframe to regime state
        """
        if timeframes is None:
            timeframes = ['5min', '15min', '1H', '4H', '1D']
        
        multi_tf_regimes = {}
        
        for tf in timeframes:
            try:
                # Resample data to timeframe
                resampled_data = self._resample_to_timeframe(market_data, tf)
                
                if len(resampled_data) < self.config.lookback_window:
                    self.logger.warning(f"Insufficient data for {tf} timeframe")
                    continue
                
                # Update regime for this timeframe
                regime_state = await self.update_regime(f"{symbol}_{tf}", resampled_data)
                multi_tf_regimes[tf] = regime_state
                
                # Store in multi-timeframe cache
                self.multi_timeframe_states[tf] = regime_state
                
            except Exception as e:
                self.logger.error(f"Error in {tf} timeframe analysis: {e}")
        
        # Synthesize overall regime from multi-timeframe analysis
        self._synthesize_multi_timeframe_regime(multi_tf_regimes)
        
        return multi_tf_regimes
    
    def _resample_to_timeframe(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Resample market data to specified timeframe"""
        # Map timeframe strings to pandas resample rules
        tf_map = {
            '5min': '5T',
            '15min': '15T',
            '1H': '1H',
            '4H': '4H',
            '1D': '1D'
        }
        
        rule = tf_map.get(timeframe, '5T')
        
        # Ensure we have a datetime index
        if 'timestamp' in data.columns:
            data = data.set_index('timestamp')
        
        # Resample OHLCV data
        resampled = data.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return resampled.reset_index()
    
    def _synthesize_multi_timeframe_regime(self, multi_tf_regimes: Dict[str, RegimeState]) -> None:
        """Synthesize overall market regime from multiple timeframe analysis"""
        if not multi_tf_regimes:
            return
        
        # Weight different timeframes
        tf_weights = {
            '5min': 0.1,
            '15min': 0.15,
            '1H': 0.25,
            '4H': 0.3,
            '1D': 0.2
        }
        
        # Aggregate regime votes
        regime_scores = {}
        total_weight = 0.0
        
        for tf, regime in multi_tf_regimes.items():
            weight = tf_weights.get(tf, 0.1)
            regime_type = regime.primary_regime
            
            if regime_type not in regime_scores:
                regime_scores[regime_type] = 0.0
            
            regime_scores[regime_type] += weight * regime.confidence
            total_weight += weight
        
        # Normalize scores
        if total_weight > 0:
            for regime_type in regime_scores:
                regime_scores[regime_type] /= total_weight
        
        # Log multi-timeframe consensus
        consensus_regime = max(regime_scores.items(), key=lambda x: x[1])
        self.logger.info(f"📊 Multi-timeframe consensus: {consensus_regime[0].value} "
                        f"(score: {consensus_regime[1]:.2%})")
    
    async def predict_regime_transition(self, market_data: pd.DataFrame, 
                                      horizon: int = 30) -> Dict[str, Any]:
        """
        Predict potential regime transitions in the near future
        
        Args:
            market_data: Historical market data
            horizon: Prediction horizon in minutes
        
        Returns:
            Transition probability and predicted regime
        """
        if not self.transition_predictor or not SKLEARN_AVAILABLE:
            return {'probability': 0.0, 'predicted_regime': self.current_regime}
        
        try:
            # Extract predictive features
            features = self._extract_predictive_features(market_data)
            
            if features is None:
                return {'probability': 0.0, 'predicted_regime': self.current_regime}
            
            # Check if model is trained
            if not hasattr(self.transition_predictor, 'classes_'):
                # Train on historical transitions if available
                self._train_transition_predictor()
            
            # Make prediction
            if hasattr(self.transition_predictor, 'classes_'):
                transition_prob = self.transition_predictor.predict_proba(features.reshape(1, -1))[0]
                max_prob_idx = np.argmax(transition_prob[1:]) + 1  # Skip "no transition" class
                
                predicted_regime = RegimeType(self.transition_predictor.classes_[max_prob_idx])
                transition_probability = transition_prob[max_prob_idx]
                
                # Store predictive features for analysis
                self.predictive_features = {
                    'momentum_divergence': features[0],
                    'volume_anomaly': features[1],
                    'volatility_expansion': features[2],
                    'correlation_breakdown': features[3]
                }
                
                self.logger.info(f"🔮 Regime transition prediction: {predicted_regime.value} "
                               f"(probability: {transition_probability:.2%})")
                
                return {
                    'probability': transition_probability,
                    'predicted_regime': predicted_regime,
                    'horizon': horizon,
                    'features': self.predictive_features
                }
            
        except Exception as e:
            self.logger.error(f"Error in regime transition prediction: {e}")
        
        return {'probability': 0.0, 'predicted_regime': self.current_regime}
    
    def _extract_predictive_features(self, market_data: pd.DataFrame) -> Optional[np.ndarray]:
        """Extract features that predict regime transitions"""
        try:
            if len(market_data) < 60:
                return None
            
            # Calculate predictive indicators
            returns = market_data['close'].pct_change().dropna()
            
            # 1. Momentum divergence (price vs volume momentum)
            price_momentum = returns.rolling(20).mean().iloc[-1]
            volume_momentum = market_data['volume'].pct_change().rolling(20).mean().iloc[-1]
            momentum_divergence = abs(price_momentum - volume_momentum)
            
            # 2. Volume anomaly score
            volume_mean = market_data['volume'].rolling(30).mean()
            volume_std = market_data['volume'].rolling(30).std()
            volume_zscore = abs((market_data['volume'].iloc[-1] - volume_mean.iloc[-1]) / 
                               (volume_std.iloc[-1] + 1e-8))
            
            # 3. Volatility expansion rate
            short_vol = returns.rolling(10).std().iloc[-1]
            long_vol = returns.rolling(30).std().iloc[-1]
            vol_expansion = short_vol / (long_vol + 1e-8)
            
            # 4. Correlation breakdown indicator
            if len(returns) > 40:
                # Compare recent correlation to historical
                recent_corr = self._calculate_cross_asset_correlations(market_data.iloc[-20:])
                hist_corr = self._calculate_cross_asset_correlations(market_data.iloc[-60:-20])
                corr_breakdown = abs(recent_corr - hist_corr)
            else:
                corr_breakdown = 0.0
            
            # 5. Extreme return indicator
            extreme_threshold = returns.std() * 2.5
            extreme_return = 1.0 if abs(returns.iloc[-1]) > extreme_threshold else 0.0
            
            # 6. Trend acceleration
            sma_10 = market_data['close'].rolling(10).mean()
            sma_20 = market_data['close'].rolling(20).mean()
            trend_accel = (sma_10.iloc[-1] - sma_10.iloc[-5]) / (sma_20.iloc[-1] - sma_20.iloc[-5] + 1e-8)
            
            features = np.array([
                momentum_divergence,
                volume_zscore,
                vol_expansion,
                corr_breakdown,
                extreme_return,
                trend_accel
            ])
            
            return features
            
        except Exception as e:
            self.logger.warning(f"Error extracting predictive features: {e}")
            return None
    
    def _train_transition_predictor(self) -> None:
        """Train regime transition predictor on historical data"""
        if not self.transition_history or len(self.transition_history) < 10:
            return
        
        try:
            # Prepare training data from transition history
            X_train = []
            y_train = []
            
            # This is a simplified training - in production, you'd use
            # actual historical features before each transition
            for transition in self.transition_history:
                # Generate synthetic features for demonstration
                features = np.random.randn(6)  # 6 predictive features
                X_train.append(features)
                y_train.append(transition.to_regime.value)
            
            if X_train:
                X_train = np.array(X_train)
                y_train = np.array(y_train)
                self.transition_predictor.fit(X_train, y_train)
                self.logger.info("✅ Regime transition predictor trained")
                
        except Exception as e:
            self.logger.error(f"Error training transition predictor: {e}")
    
    def validate_cross_asset_regime(self, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Validate regime detection using cross-asset analysis
        
        Args:
            asset_data: Dictionary mapping asset symbols to their market data
        
        Returns:
            Validation results and confidence adjustments
        """
        if not self.cross_asset_validator or not asset_data or len(asset_data) < 2:
            return {'valid': True, 'confidence_adjustment': 1.0}
        
        try:
            # Extract features from multiple assets
            asset_features = []
            asset_regimes = {}
            
            for symbol, data in asset_data.items():
                if len(data) < self.config.lookback_window:
                    continue
                
                features = self._extract_regime_features(data)
                if features is not None:
                    asset_features.append(features)
                    
                    # Get regime for this asset
                    regime = self._detect_regime_ensemble(data, features)
                    asset_regimes[symbol] = regime
            
            if len(asset_features) < 2:
                return {'valid': True, 'confidence_adjustment': 1.0}
            
            # Perform cross-asset validation
            asset_features = np.array(asset_features)
            
            # Fit PCA if not fitted
            if not hasattr(self.cross_asset_validator, 'components_'):
                self.cross_asset_validator.fit(asset_features)
            
            # Transform features to principal components
            pca_features = self.cross_asset_validator.transform(asset_features)
            
            # Calculate regime coherence across assets
            regime_counts = {}
            for regime in asset_regimes.values():
                if regime not in regime_counts:
                    regime_counts[regime] = 0
                regime_counts[regime] += 1
            
            # Most common regime
            dominant_regime = max(regime_counts.items(), key=lambda x: x[1])[0]
            coherence_ratio = regime_counts[dominant_regime] / len(asset_regimes)
            
            # Analyze PCA components for market-wide patterns
            explained_variance = self.cross_asset_validator.explained_variance_ratio_
            market_concentration = explained_variance[0]  # First component dominance
            
            # Validate based on coherence and market concentration
            is_valid = coherence_ratio > 0.6 or market_concentration > 0.5
            
            # Adjust confidence based on cross-asset agreement
            confidence_adjustment = 0.5 + 0.5 * coherence_ratio
            if market_concentration > 0.6:
                confidence_adjustment *= 1.2
            
            validation_result = {
                'valid': is_valid,
                'confidence_adjustment': min(confidence_adjustment, 1.5),
                'coherence_ratio': coherence_ratio,
                'market_concentration': market_concentration,
                'dominant_regime': dominant_regime.value,
                'asset_regimes': {s: r.value for s, r in asset_regimes.items()}
            }
            
            self.logger.info(f"🔍 Cross-asset validation: coherence={coherence_ratio:.2%}, "
                           f"concentration={market_concentration:.2%}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Error in cross-asset validation: {e}")
            return {'valid': True, 'confidence_adjustment': 1.0}
    
    def calculate_regime_stability(self, lookback_periods: int = 20) -> Dict[RegimeType, float]:
        """
        Calculate stability scores for each regime type
        
        Args:
            lookback_periods: Number of historical periods to analyze
        
        Returns:
            Dictionary mapping regime types to stability scores (0-1)
        """
        if len(self.regime_history) < lookback_periods:
            return {}
        
        recent_history = list(self.regime_history)[-lookback_periods:]
        regime_durations = {}
        regime_transitions = {}
        
        # Initialize counters
        for regime_type in RegimeType:
            regime_durations[regime_type] = []
            regime_transitions[regime_type] = 0
        
        # Analyze regime patterns
        current_regime = recent_history[0].primary_regime
        current_duration = 1
        
        for i in range(1, len(recent_history)):
            regime = recent_history[i].primary_regime
            
            if regime == current_regime:
                current_duration += 1
            else:
                # Record duration and transition
                regime_durations[current_regime].append(current_duration)
                regime_transitions[current_regime] += 1
                
                # Start new regime tracking
                current_regime = regime
                current_duration = 1
        
        # Record final duration
        regime_durations[current_regime].append(current_duration)
        
        # Calculate stability scores
        stability_scores = {}
        
        for regime_type in RegimeType:
            durations = regime_durations[regime_type]
            transitions = regime_transitions[regime_type]
            
            if not durations:
                stability_scores[regime_type] = 0.0
                continue
            
            # Average duration (normalized)
            avg_duration = np.mean(durations) / lookback_periods
            
            # Transition frequency (inverted and normalized)
            transition_freq = 1.0 - (transitions / lookback_periods)
            
            # Duration consistency
            if len(durations) > 1:
                duration_cv = np.std(durations) / (np.mean(durations) + 1e-8)
                consistency = 1.0 / (1.0 + duration_cv)
            else:
                consistency = 0.5
            
            # Combined stability score
            stability = (avg_duration * 0.4 + transition_freq * 0.3 + consistency * 0.3)
            stability_scores[regime_type] = min(stability, 1.0)
        
        # Store for later use
        self.regime_stability_scores = stability_scores
        
        # Log stability analysis
        stable_regimes = [r for r, s in stability_scores.items() if s > 0.7]
        if stable_regimes:
            self.logger.info(f"📊 Stable regimes detected: {[r.value for r in stable_regimes]}")
        
        return stability_scores
    
    def get_regime_confidence_with_validation(self, symbol: str, market_data: pd.DataFrame,
                                            cross_assets: Optional[Dict[str, pd.DataFrame]] = None) -> float:
        """
        Get regime confidence with multi-factor validation
        
        Args:
            symbol: Trading symbol
            market_data: Market data for the symbol
            cross_assets: Optional cross-asset data for validation
        
        Returns:
            Adjusted confidence score (0-1)
        """
        # Get base confidence
        base_confidence = self.current_regime.confidence if self.current_regime else 0.5
        
        # Factor 1: Regime stability
        stability_scores = self.calculate_regime_stability()
        current_stability = stability_scores.get(self.current_regime.primary_regime, 0.5)
        
        # Factor 2: Multi-timeframe agreement
        if self.multi_timeframe_states:
            regime_agreement = sum(1 for r in self.multi_timeframe_states.values() 
                                 if r.primary_regime == self.current_regime.primary_regime)
            tf_agreement_ratio = regime_agreement / len(self.multi_timeframe_states)
        else:
            tf_agreement_ratio = 0.5
        
        # Factor 3: Cross-asset validation
        if cross_assets:
            validation = self.validate_cross_asset_regime(cross_assets)
            cross_asset_factor = validation['confidence_adjustment']
        else:
            cross_asset_factor = 1.0
        
        # Factor 4: Model consensus
        if hasattr(self, 'last_model_confidences'):
            model_consensus = np.std(list(self.last_model_confidences.values()))
            consensus_factor = 1.0 - model_consensus  # Lower std = higher consensus
        else:
            consensus_factor = 0.5
        
        # Combine factors
        adjusted_confidence = (
            base_confidence * 0.3 +
            current_stability * 0.2 +
            tf_agreement_ratio * 0.2 +
            cross_asset_factor * 0.2 +
            consensus_factor * 0.1
        )
        
        # Apply bounds
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))
        
        self.logger.debug(f"🎯 Regime confidence: base={base_confidence:.2%}, "
                         f"adjusted={adjusted_confidence:.2%}")
        
        return adjusted_confidence
    
    def _prepare_training_features(self, market_data: pd.DataFrame) -> Optional[np.ndarray]:
        """Prepare features for model training"""
        try:
            if len(market_data) < self.config.lookback_window:
                return None
            
            features_list = []
            window_size = 20
            
            # Extract features for multiple time windows
            for i in range(window_size, len(market_data) - window_size, 5):
                window_data = market_data.iloc[i-window_size:i+window_size]
                
                # Simple features for training
                returns = window_data['close'].pct_change().dropna()
                features = [
                    returns.mean(),
                    returns.std(),
                    returns.skew(),
                    returns.kurt(),
                    np.log(window_data['close'].iloc[-1] / window_data['close'].iloc[0]),
                    window_data['volume'].mean() / 1e6,  # Normalized volume
                    window_data['volume'].std() / 1e6
                ]
                
                features_list.append(features)
            
            if features_list:
                return np.array(features_list)
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error preparing training features: {e}")
            return None
    
    def _get_confidence_level(self, confidence: float) -> RegimeConfidence:
        """Map confidence score to confidence level"""
        if confidence > 0.8:
            return RegimeConfidence.HIGH
        elif confidence > 0.6:
            return RegimeConfidence.MEDIUM
        elif confidence > 0.4:
            return RegimeConfidence.LOW
        else:
            return RegimeConfidence.UNCERTAIN
    
    def _check_regime_transition(self,
                               old_regime: RegimeState,
                               new_regime: RegimeState) -> Optional[RegimeTransition]:
        """Check if regime transition occurred"""
        if old_regime.primary_regime != new_regime.primary_regime:
            if new_regime.confidence >= self.config.transition_confidence_threshold:
                return RegimeTransition(
                    from_regime=old_regime.primary_regime,
                    to_regime=new_regime.primary_regime,
                    transition_time=datetime.now(),
                    transition_confidence=new_regime.confidence,
                    transition_triggers=self._identify_transition_triggers(old_regime, new_regime)
                )
        return None
    
    def _identify_transition_triggers(self,
                                    old_regime: RegimeState,
                                    new_regime: RegimeState) -> List[str]:
        """Identify what triggered the regime transition"""
        triggers = []
        
        # Volatility change
        if old_regime.market_volatility != 0:
            vol_change = (new_regime.market_volatility - old_regime.market_volatility) / old_regime.market_volatility
            if abs(vol_change) > 0.5:
                triggers.append(f"Volatility {'spike' if vol_change > 0 else 'drop'}: {vol_change:.1%}")
        
        # Trend reversal
        if old_regime.trend_strength * new_regime.trend_strength < 0:
            triggers.append("Trend reversal detected")
        
        # Volume surge
        if new_regime.market_volume_ratio > 2.0:
            triggers.append(f"Volume surge: {new_regime.market_volume_ratio:.1f}x")
        
        return triggers
    
    async def _handle_regime_transition(self,
                                      old_regime: RegimeState,
                                      new_regime: RegimeState,
                                      transition: RegimeTransition) -> None:
        """Handle regime transition"""
        self.logger.info(f"🔄 Regime transition: {transition.from_regime.value} → {transition.to_regime.value} "
                        f"(confidence: {transition.transition_confidence:.2f})")
        
        # Record transition
        self.transition_history.append(transition)
        self.performance_metrics['transitions_detected'] += 1
        
        # Notify subscribers
        if self.config.enable_notifications:
            await self._notify_subscribers(old_regime, new_regime, transition)
    
    async def _notify_subscribers(self,
                                old_regime: RegimeState,
                                new_regime: RegimeState,
                                transition: RegimeTransition) -> None:
        """Notify all subscribers of regime change"""
        with self._subscriber_lock:
            subscribers = list(self.subscribers)
        
        # Notify all subscribers in parallel
        tasks = []
        for subscriber in subscribers:
            task = asyncio.create_task(
                self._notify_subscriber_safe(subscriber, old_regime, new_regime, transition)
            )
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _notify_subscriber_safe(self,
                                    subscriber: IRegimeSubscriber,
                                    old_regime: RegimeState,
                                    new_regime: RegimeState,
                                    transition: RegimeTransition) -> None:
        """Safely notify a subscriber"""
        try:
            await subscriber.on_regime_change(old_regime, new_regime, transition)
        except Exception as e:
            self.logger.error(f"Error notifying subscriber {subscriber.get_subscriber_id()}: {e}")
    
    def subscribe_to_regime_changes(self, subscriber: IRegimeSubscriber) -> None:
        """Subscribe to regime change notifications"""
        with self._subscriber_lock:
            self.subscribers.add(subscriber)
            self.logger.info(f"📋 Subscriber registered: {subscriber.get_subscriber_id()}")
    
    def unsubscribe_from_regime_changes(self, subscriber: IRegimeSubscriber) -> None:
        """Unsubscribe from regime change notifications"""
        with self._subscriber_lock:
            self.subscribers.discard(subscriber)
            self.logger.info(f"📋 Subscriber unregistered: {subscriber.get_subscriber_id()}")
    
    def get_regime_adaptations(self, regime: Optional[RegimeType] = None) -> RegimeAdaptations:
        """Get adaptation parameters for current or specified regime"""
        target_regime = regime or (self.current_regime.primary_regime if self.current_regime else RegimeType.UNKNOWN)
        
        if target_regime in self.adaptation_mappings:
            return self.adaptation_mappings[target_regime]
        
        # Return default adaptations
        return RegimeAdaptations()
    
    def get_strategy_adjustments(self, strategy_type: str) -> Dict[str, Any]:
        """Get regime-based strategy parameter adjustments"""
        adaptations = self.get_regime_adaptations()
        
        adjustments = {
            'momentum': {
                'lookback_multiplier': adaptations.momentum_lookback_multiplier,
                'threshold_adjustment': adaptations.momentum_threshold_adjustment,
                'confidence_multiplier': adaptations.signal_confidence_multiplier
            },
            'mean_reversion': {
                'entry_threshold': adaptations.mean_reversion_entry_threshold,
                'exit_threshold': adaptations.mean_reversion_exit_threshold,
                'confidence_multiplier': adaptations.signal_confidence_multiplier
            },
            'pairs_trading': {
                'correlation_threshold': adaptations.pairs_correlation_threshold,
                'confidence_multiplier': adaptations.signal_confidence_multiplier
            }
        }
        
        return adjustments.get(strategy_type, {})
    
    def get_risk_multipliers(self) -> Dict[str, float]:
        """Get regime-based risk multipliers"""
        adaptations = self.get_regime_adaptations()
        
        return {
            'position_size': adaptations.position_size_multiplier,
            'stop_loss': adaptations.stop_loss_multiplier,
            'take_profit': adaptations.take_profit_multiplier,
            'leverage': adaptations.leverage_limit
        }
    
    def get_execution_preferences(self) -> Dict[str, Any]:
        """Get regime-optimized execution parameters"""
        adaptations = self.get_regime_adaptations()
        
        return {
            'prefer_passive': adaptations.prefer_passive_execution,
            'slippage_buffer': adaptations.slippage_buffer_multiplier,
            'order_size_reduction': adaptations.order_size_reduction,
            'urgency': adaptations.execution_urgency,
            'use_limit_orders': adaptations.use_limit_orders
        }
    
    def get_universe_selection_params(self) -> Dict[str, float]:
        """Get regime-based universe selection parameters"""
        adaptations = self.get_regime_adaptations()
        
        return {
            'quality_threshold': adaptations.quality_score_threshold,
            'liquidity_multiplier': adaptations.liquidity_requirement_multiplier,
            'volatility_threshold': adaptations.volatility_filter_threshold,
            'correlation_strength': adaptations.correlation_filter_strength
        }
    
    def get_portfolio_constraints(self) -> Dict[str, Any]:
        """Get regime-based portfolio constraints"""
        adaptations = self.get_regime_adaptations()
        
        return {
            'diversification_requirement': adaptations.diversification_requirement,
            'sector_concentration_limit': adaptations.sector_concentration_limit,
            'rebalance_frequency_hours': adaptations.rebalance_frequency_hours,
            'max_positions_adjustment': adaptations.max_positions_adjustment
        }
    
    def _get_cached_regime(self, symbol: str) -> Optional[RegimeState]:
        """Get cached regime if valid"""
        cached_data = self._regime_cache.get(symbol)
        if cached_data:
            regime, timestamp = cached_data
            
            # Check if cache is still valid
            if (datetime.now() - timestamp).total_seconds() < self.config.cache_ttl_seconds:
                return regime
        
        return None
    
    def _cache_regime(self, symbol: str, regime: RegimeState) -> None:
        """Cache regime detection result with automatic cleanup"""
        self._regime_cache.put(symbol, (regime, datetime.now()))
    
    def _update_performance_metrics(self, detection_time_ms: float) -> None:
        """Update performance metrics"""
        self.performance_metrics['regime_updates'] += 1
        
        # Update average detection time
        n = self.performance_metrics['regime_updates']
        current_avg = self.performance_metrics['avg_detection_time_ms']
        self.performance_metrics['avg_detection_time_ms'] = (
            (current_avg * (n - 1) + detection_time_ms) / n
        )
        
        self.performance_metrics['last_update'] = datetime.now()
    
    def _get_default_regime(self) -> RegimeState:
        """Get default regime state"""
        return RegimeState(
            primary_regime=RegimeType.UNKNOWN,
            confidence=0.0,
            confidence_level=RegimeConfidence.UNCERTAIN
        )
    
    def get_regime_history(self, lookback_periods: int = 10) -> List[RegimeState]:
        """Get recent regime history"""
        return list(self.regime_history)[-lookback_periods:]
    
    def get_transition_history(self, lookback_transitions: int = 10) -> List[RegimeTransition]:
        """Get recent regime transitions"""
        return list(self.transition_history)[-lookback_transitions:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get engine performance metrics"""
        return self.performance_metrics.copy()
    
    def get_current_regime(self) -> Optional[RegimeState]:
        """Get current regime state"""
        return self.current_regime

# ================================================================================
# FACTORY FUNCTION
# ================================================================================

def create_regime_engine(config: Optional[RegimeConfig] = None) -> UnifiedRegimeEngine:
    """Factory function to create regime engine"""
    return UnifiedRegimeEngine(config)

# ================================================================================
# EXAMPLE USAGE
# ================================================================================

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        # Create regime engine
        engine = create_regime_engine()
        
        # Example market data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        market_data = pd.DataFrame({
            'timestamp': dates,
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.randint(1000, 5000, 100)
        })
        
        # Update regime
        regime = await engine.update_regime('AAPL', market_data)
        
        print(f"Current regime: {regime.primary_regime.value}")
        print(f"Confidence: {regime.confidence:.2f}")
        print(f"Adaptations: {engine.get_strategy_adjustments('momentum')}")
    
    asyncio.run(main())
