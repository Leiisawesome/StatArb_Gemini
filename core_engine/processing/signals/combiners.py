"""
Signals Engine - Signal Combiner
Advanced signal combination and ensemble methods for enhanced signal quality
"""

import logging
import threading
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
import warnings

# Import signal types
from .generator import SignalType, SignalStrength, TradingSignal

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class CombinationMethod(Enum):
    """Signal combination methods"""
    SIMPLE_AVERAGE = "simple_average"
    WEIGHTED_AVERAGE = "weighted_average"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    PERFORMANCE_WEIGHTED = "performance_weighted"
    RANK_BASED = "rank_based"
    MACHINE_LEARNING = "machine_learning"
    ENSEMBLE_VOTING = "ensemble_voting"
    DYNAMIC_WEIGHTING = "dynamic_weighting"


class EnsembleStrategy(Enum):
    """Ensemble strategies"""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_VOTE = "weighted_vote"
    STACKING = "stacking"
    BLENDING = "blending"
    BAGGING = "bagging"
    BOOSTING = "boosting"


class SignalWeight(Enum):
    """Signal weighting schemes"""
    EQUAL = "equal"
    CONFIDENCE = "confidence"
    PERFORMANCE = "performance"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    SHARPE_BASED = "sharpe_based"
    INFORMATION_RATIO = "information_ratio"
    DECAY_WEIGHTED = "decay_weighted"


@dataclass
class CombinationConfig:
    """Signal combination configuration"""
    method: CombinationMethod = CombinationMethod.WEIGHTED_AVERAGE
    weighting_scheme: SignalWeight = SignalWeight.EQUAL
    
    # Method-specific parameters
    min_signals: int = 2
    max_signals: int = 10
    confidence_threshold: float = 0.5
    performance_lookback: int = 252  # Trading days
    
    # ML parameters
    ml_model: str = "random_forest"  # random_forest, gradient_boosting, linear
    ml_features: List[str] = field(default_factory=lambda: ['strength', 'confidence', 'z_score'])
    ml_lookback: int = 1000
    
    # Ensemble parameters
    ensemble_strategy: EnsembleStrategy = EnsembleStrategy.WEIGHTED_VOTE
    voting_threshold: float = 0.6
    
    # Dynamic parameters
    adaptation_rate: float = 0.1
    decay_factor: float = 0.95
    rebalance_frequency: int = 20  # Days
    
    # Risk controls
    max_position_concentration: float = 0.3
    correlation_threshold: float = 0.8
    volatility_scaling: bool = True


@dataclass
class SignalCombination:
    """Result of signal combination"""
    combined_signal_id: str
    symbol: str
    combination_method: CombinationMethod
    timestamp: datetime
    
    # Combined signal properties
    combined_strength: float
    combined_confidence: float
    combined_position_size: float
    
    # Component signals
    component_signals: List[Any]
    signal_weights: Dict[str, float]
    
    # Quality metrics
    combination_quality: float = 0.0
    consensus_level: float = 0.0  # Agreement between signals
    diversification_score: float = 0.0
    
    # Performance attribution
    expected_return: float = 0.0
    expected_volatility: float = 0.2
    expected_sharpe: float = 0.0
    
    # Metadata
    combination_details: Dict[str, Any] = field(default_factory=dict)
    performance_attribution: Dict[str, float] = field(default_factory=dict)


@dataclass
class EnsembleModel:
    """Ensemble model for signal combination"""
    model_id: str
    model_type: str
    trained_model: Any
    
    # Training metadata
    training_date: datetime
    training_samples: int
    training_features: List[str]
    
    # Performance metrics
    training_score: float
    validation_score: float
    out_of_sample_score: float
    
    # Model parameters
    feature_importance: Dict[str, float] = field(default_factory=dict)
    model_parameters: Dict[str, Any] = field(default_factory=dict)


class SignalWeightCalculator:
    """Calculate signal weights using different schemes"""
    
    def __init__(self):
        self.performance_history = defaultdict(list)
        self.weight_cache = {}
        self._lock = threading.Lock()
    
    def calculate_weights(
        self,
        signals: List[Any],
        weighting_scheme: SignalWeight,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """Calculate weights for signals"""
        
        context = context or {}
        
        if weighting_scheme == SignalWeight.EQUAL:
            return self._equal_weights(signals)
        elif weighting_scheme == SignalWeight.CONFIDENCE:
            return self._confidence_weights(signals)
        elif weighting_scheme == SignalWeight.PERFORMANCE:
            return self._performance_weights(signals, context)
        elif weighting_scheme == SignalWeight.VOLATILITY_ADJUSTED:
            return self._volatility_adjusted_weights(signals, context)
        elif weighting_scheme == SignalWeight.SHARPE_BASED:
            return self._sharpe_based_weights(signals, context)
        elif weighting_scheme == SignalWeight.INFORMATION_RATIO:
            return self._information_ratio_weights(signals, context)
        elif weighting_scheme == SignalWeight.DECAY_WEIGHTED:
            return self._decay_weighted_weights(signals, context)
        else:
            return self._equal_weights(signals)
    
    def _equal_weights(self, signals: List[Any]) -> Dict[str, float]:
        """Equal weighting"""
        weight = 1.0 / len(signals) if signals else 0.0
        return {getattr(s, 'signal_id', f'signal_{i}'): weight for i, s in enumerate(signals)}
    
    def _confidence_weights(self, signals: List[Any]) -> Dict[str, float]:
        """Confidence-based weighting"""
        confidences = [getattr(s, 'confidence', 0.5) for s in signals]
        total_confidence = sum(confidences)
        
        if total_confidence == 0:
            return self._equal_weights(signals)
        
        return {
            getattr(s, 'signal_id', f'signal_{i}'): conf / total_confidence
            for i, (s, conf) in enumerate(zip(signals, confidences))
        }
    
    def _performance_weights(self, signals: List[Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Performance-based weighting"""
        performance_data = context.get('performance_data', {})
        
        if not performance_data:
            return self._equal_weights(signals)
        
        performances = []
        for signal in signals:
            signal_type = getattr(signal, 'signal_type', None)
            if signal_type and signal_type.value in performance_data:
                # Use Sharpe ratio as performance metric
                perf = performance_data[signal_type.value].get('sharpe_ratio', 0.0)
                performances.append(max(perf, 0.01))  # Minimum weight
            else:
                performances.append(0.5)  # Default performance
        
        total_performance = sum(performances)
        
        return {
            getattr(s, 'signal_id', f'signal_{i}'): perf / total_performance
            for i, (s, perf) in enumerate(zip(signals, performances))
        }
    
    def _volatility_adjusted_weights(self, signals: List[Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Volatility-adjusted weighting (inverse volatility)"""
        volatilities = []
        
        for signal in signals:
            vol = getattr(signal, 'expected_volatility', context.get('default_volatility', 0.2))
            volatilities.append(max(vol, 0.01))  # Minimum volatility
        
        # Inverse volatility weights
        inv_vol_weights = [1.0 / vol for vol in volatilities]
        total_weight = sum(inv_vol_weights)
        
        return {
            getattr(s, 'signal_id', f'signal_{i}'): weight / total_weight
            for i, (s, weight) in enumerate(zip(signals, inv_vol_weights))
        }
    
    def _sharpe_based_weights(self, signals: List[Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Sharpe ratio-based weighting"""
        sharpe_ratios = []
        
        for signal in signals:
            expected_return = getattr(signal, 'expected_return', 0.0)
            expected_volatility = getattr(signal, 'expected_volatility', 0.2)
            
            sharpe = expected_return / max(expected_volatility, 0.01)
            sharpe_ratios.append(max(sharpe, 0.01))  # Minimum Sharpe
        
        total_sharpe = sum(sharpe_ratios)
        
        return {
            getattr(s, 'signal_id', f'signal_{i}'): sharpe / total_sharpe
            for i, (s, sharpe) in enumerate(zip(signals, sharpe_ratios))
        }
    
    def _information_ratio_weights(self, signals: List[Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Information ratio-based weighting"""
        # Simplified - use confidence as proxy for information ratio
        return self._confidence_weights(signals)
    
    def _decay_weighted_weights(self, signals: List[Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Time decay-based weighting (more recent signals get higher weight)"""
        current_time = datetime.now()
        decay_factor = context.get('decay_factor', 0.95)
        
        weights = []
        for signal in signals:
            signal_time = getattr(signal, 'timestamp', current_time)
            time_diff = (current_time - signal_time).total_seconds() / 3600  # Hours
            decay_weight = decay_factor ** time_diff
            weights.append(decay_weight)
        
        total_weight = sum(weights)
        
        return {
            getattr(s, 'signal_id', f'signal_{i}'): weight / total_weight
            for i, (s, weight) in enumerate(zip(signals, weights))
        }


class EnsembleEngine:
    """Machine learning ensemble engine for signal combination"""
    
    def __init__(self, config: CombinationConfig):
        self.config = config
        self.models = {}
        self.training_data = defaultdict(list)
        self._lock = threading.Lock()
    
    def train_ensemble_model(
        self,
        training_signals: List[List[Any]],
        training_returns: List[float],
        symbol: str
    ) -> EnsembleModel:
        """Train ensemble model for signal combination"""
        
        try:
            # Prepare training data
            X, y = self._prepare_training_data(training_signals, training_returns)
            
            if len(X) < self.config.min_signals:
                raise ValueError(f"Insufficient training data: {len(X)} samples")
            
            # Split into train/validation
            split_idx = int(len(X) * 0.8)
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Train model
            if self.config.ml_model == "random_forest":
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif self.config.ml_model == "gradient_boosting":
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            elif self.config.ml_model == "linear":
                model = Ridge(alpha=1.0)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            
            # Fit model
            model.fit(X_train, y_train)
            
            # Calculate scores
            train_score = model.score(X_train, y_train)
            val_score = model.score(X_val, y_val) if len(X_val) > 0 else train_score
            
            # Feature importance
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                for i, importance in enumerate(model.feature_importances_):
                    if i < len(self.config.ml_features):
                        feature_importance[self.config.ml_features[i]] = importance
            
            ensemble_model = EnsembleModel(
                model_id=f"{symbol}_{self.config.ml_model}_{int(time.time())}",
                model_type=self.config.ml_model,
                trained_model=model,
                training_date=datetime.now(),
                training_samples=len(X_train),
                training_features=self.config.ml_features.copy(),
                training_score=train_score,
                validation_score=val_score,
                out_of_sample_score=0.0,  # To be updated with real performance
                feature_importance=feature_importance
            )
            
            # Store model
            with self._lock:
                self.models[symbol] = ensemble_model
            
            logger.info(f"Trained ensemble model for {symbol}: train_score={train_score:.3f}, val_score={val_score:.3f}")
            
            return ensemble_model
            
        except Exception as e:
            logger.error(f"Error training ensemble model for {symbol}: {e}")
            raise
    
    def _prepare_training_data(
        self,
        training_signals: List[List[Any]],
        training_returns: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ensemble model"""
        
        features = []
        targets = []
        
        for signal_group, target_return in zip(training_signals, training_returns):
            if not signal_group:
                continue
            
            # Extract features from signal group
            signal_features = []
            
            for signal in signal_group:
                for feature_name in self.config.ml_features:
                    value = getattr(signal, feature_name, 0.0)
                    signal_features.append(value)
            
            # Pad or truncate to fixed length
            max_signals = self.config.max_signals
            expected_length = max_signals * len(self.config.ml_features)
            
            if len(signal_features) < expected_length:
                signal_features.extend([0.0] * (expected_length - len(signal_features)))
            elif len(signal_features) > expected_length:
                signal_features = signal_features[:expected_length]
            
            features.append(signal_features)
            targets.append(target_return)
        
        return np.array(features), np.array(targets)
    
    def predict_combination(
        self,
        signals: List[Any],
        symbol: str
    ) -> Tuple[float, float]:
        """Predict optimal combination using ensemble model"""
        
        with self._lock:
            model = self.models.get(symbol)
        
        if not model:
            logger.warning(f"No ensemble model available for {symbol}")
            return 0.0, 0.5  # Default strength and confidence
        
        try:
            # Prepare features
            signal_features = []
            
            for signal in signals:
                for feature_name in self.config.ml_features:
                    value = getattr(signal, feature_name, 0.0)
                    signal_features.append(value)
            
            # Pad or truncate to expected length
            max_signals = self.config.max_signals
            expected_length = max_signals * len(self.config.ml_features)
            
            if len(signal_features) < expected_length:
                signal_features.extend([0.0] * (expected_length - len(signal_features)))
            elif len(signal_features) > expected_length:
                signal_features = signal_features[:expected_length]
            
            # Make prediction
            X = np.array([signal_features])
            predicted_return = model.trained_model.predict(X)[0]
            
            # Convert to signal strength and confidence
            strength = np.tanh(predicted_return * 5)  # Scale and bound
            confidence = min(abs(predicted_return) + 0.3, 1.0)  # Higher for stronger predictions
            
            return strength, confidence
            
        except Exception as e:
            logger.error(f"Error predicting combination for {symbol}: {e}")
            return 0.0, 0.5


class SignalCombiner:
    """
    Advanced signal combination engine
    
    Combines multiple signals using various methods including
    simple averaging, weighted schemes, and machine learning ensembles.
    """
    
    def __init__(self, config: Optional[CombinationConfig] = None):
        """Initialize signal combiner"""
        self.config = config or CombinationConfig(method=CombinationMethod.WEIGHTED_AVERAGE)
        
        # Components
        self.weight_calculator = SignalWeightCalculator()
        self.ensemble_engine = EnsembleEngine(self.config)
        
        # Combination history
        self._combination_history = deque(maxlen=10000)
        self._symbol_combinations = defaultdict(list)
        
        # Performance tracking
        self._combination_performance = defaultdict(list)
        self._method_performance = defaultdict(list)
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info(f"SignalCombiner initialized with method: {self.config.method.value}")
    
    async def combine_signals(
        self,
        signals: List[Any],
        symbol: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SignalCombination]:
        """Combine multiple signals into a single signal"""
        
        if not signals:
            raise ValueError("Cannot combine empty signal list")
        
        if len(signals) < self.config.min_signals:
            raise ValueError(f"Insufficient signals for combination: {len(signals)} < {self.config.min_signals}")
        
        context = context or {}
        
        try:
            # Filter and validate signals
            valid_signals = self._filter_signals(signals, context)
            
            if len(valid_signals) < self.config.min_signals:
                logger.warning(f"Insufficient valid signals after filtering: {len(valid_signals)}")
                return None
            
            # Limit number of signals
            if len(valid_signals) > self.config.max_signals:
                valid_signals = self._select_best_signals(valid_signals, self.config.max_signals)
            
            # Calculate signal weights
            weights = self.weight_calculator.calculate_weights(
                valid_signals,
                self.config.weighting_scheme,
                context
            )
            
            # Combine signals based on method
            if self.config.method == CombinationMethod.SIMPLE_AVERAGE:
                combination = await self._simple_average_combination(valid_signals, symbol, weights, context)
            elif self.config.method == CombinationMethod.WEIGHTED_AVERAGE:
                combination = await self._weighted_average_combination(valid_signals, symbol, weights, context)
            elif self.config.method == CombinationMethod.CONFIDENCE_WEIGHTED:
                combination = await self._confidence_weighted_combination(valid_signals, symbol, context)
            elif self.config.method == CombinationMethod.PERFORMANCE_WEIGHTED:
                combination = await self._performance_weighted_combination(valid_signals, symbol, context)
            elif self.config.method == CombinationMethod.RANK_BASED:
                combination = await self._rank_based_combination(valid_signals, symbol, weights, context)
            elif self.config.method == CombinationMethod.MACHINE_LEARNING:
                combination = await self._machine_learning_combination(valid_signals, symbol, context)
            elif self.config.method == CombinationMethod.ENSEMBLE_VOTING:
                combination = await self._ensemble_voting_combination(valid_signals, symbol, context)
            elif self.config.method == CombinationMethod.DYNAMIC_WEIGHTING:
                combination = await self._dynamic_weighting_combination(valid_signals, symbol, context)
            else:
                combination = await self._weighted_average_combination(valid_signals, symbol, weights, context)
            
            if combination:
                # Calculate quality metrics
                combination.combination_quality = self._calculate_combination_quality(valid_signals, combination)
                combination.consensus_level = self._calculate_consensus_level(valid_signals)
                combination.diversification_score = self._calculate_diversification_score(valid_signals)
                
                # Store combination
                with self._lock:
                    self._combination_history.append(combination)
                    self._symbol_combinations[symbol].append(combination)
                    # Keep only recent combinations
                    self._symbol_combinations[symbol] = self._symbol_combinations[symbol][-100:]
                
                logger.debug(f"Combined {len(valid_signals)} signals for {symbol}: "
                           f"strength={combination.combined_strength:.3f}, "
                           f"confidence={combination.combined_confidence:.3f}")
            
            return combination
            
        except Exception as e:
            logger.error(f"Error combining signals for {symbol}: {e}")
            return None
    
    def combine_weighted_average(self, signals: List[Any]) -> Optional[TradingSignal]:
        """Synchronous wrapper for weighted average combination"""
        import asyncio
        
        if not signals:
            return None
        
        # Extract symbol from first signal
        symbol = getattr(signals[0], 'symbol', 'UNKNOWN')
        
        async def _combine():
            combination = await self.combine_signals(signals, symbol, {"method": "weighted_average"})
            if combination:
                return TradingSignal(
                    symbol=combination.symbol,
                    timestamp=combination.timestamp,
                    signal_type=SignalType.HOLD if abs(combination.combined_strength) < 0.1 else (SignalType.BUY if combination.combined_strength > 0 else SignalType.SELL),
                    strength=SignalStrength.STRONG if abs(combination.combined_strength) > 0.7 else SignalStrength.MODERATE,
                    confidence=combination.combined_confidence,
                    price=100.0,  # Default price
                    strategy="combined",
                    metadata={"combination_method": "weighted_average"}
                )
            return None
        
        try:
            return asyncio.run(_combine())
        except Exception as e:
            logger.error(f"Error in combine_weighted_average: {e}")
            return None
    
    def combine_majority_vote(self, signals: List[Any]) -> Optional[TradingSignal]:
        """Synchronous wrapper for majority vote combination"""
        import asyncio
        
        if not signals:
            return None
        
        # Extract symbol from first signal
        symbol = getattr(signals[0], 'symbol', 'UNKNOWN')
        
        async def _combine():
            combination = await self.combine_signals(signals, symbol, {"method": "majority_vote"})
            if combination:
                return TradingSignal(
                    symbol=combination.symbol,
                    timestamp=combination.timestamp,
                    signal_type=SignalType.HOLD if abs(combination.combined_strength) < 0.1 else (SignalType.BUY if combination.combined_strength > 0 else SignalType.SELL),
                    strength=SignalStrength.STRONG if abs(combination.combined_strength) > 0.7 else SignalStrength.MODERATE,
                    confidence=combination.combined_confidence,
                    price=100.0,  # Default price
                    strategy="combined",
                    metadata={"combination_method": "majority_vote"}
                )
            return None
        
        try:
            return asyncio.run(_combine())
        except Exception as e:
            logger.error(f"Error in combine_majority_vote: {e}")
            return None
    
    def combine_ml_ensemble(self, signals: List[Any]) -> Optional[TradingSignal]:
        """Synchronous wrapper for ML ensemble combination"""
        import asyncio
        
        if not signals:
            return None
        
        # Extract symbol from first signal
        symbol = getattr(signals[0], 'symbol', 'UNKNOWN')
        
        async def _combine():
            combination = await self.combine_signals(signals, symbol, {"method": "machine_learning"})
            if combination:
                return TradingSignal(
                    symbol=combination.symbol,
                    timestamp=combination.timestamp,
                    signal_type=SignalType.HOLD if abs(combination.combined_strength) < 0.1 else (SignalType.BUY if combination.combined_strength > 0 else SignalType.SELL),
                    strength=SignalStrength.STRONG if abs(combination.combined_strength) > 0.7 else SignalStrength.MODERATE,
                    confidence=combination.combined_confidence,
                    price=100.0,  # Default price
                    strategy="ml_ensemble",
                    metadata={"combination_method": "machine_learning"}
                )
            return None
        
        try:
            return asyncio.run(_combine())
        except Exception as e:
            logger.error(f"Error in combine_ml_ensemble: {e}")
            return None
    
    def _filter_signals(self, signals: List[Any], context: Dict[str, Any]) -> List[Any]:
        """Filter signals based on quality and consistency"""
        
        filtered_signals = []
        
        for signal in signals:
            # Basic validation
            if not hasattr(signal, 'strength') or not hasattr(signal, 'confidence'):
                continue
            
            # Confidence threshold
            if getattr(signal, 'confidence', 0.0) < self.config.confidence_threshold:
                continue
            
            # Age check
            signal_time = getattr(signal, 'timestamp', datetime.now())
            age_hours = (datetime.now() - signal_time).total_seconds() / 3600
            
            if age_hours > 24:  # Signals older than 24 hours
                continue
            
            filtered_signals.append(signal)
        
        return filtered_signals
    
    def _select_best_signals(self, signals: List[Any], max_signals: int) -> List[Any]:
        """Select best signals when there are too many"""
        
        # Score signals by confidence * |strength|
        scored_signals = []
        for signal in signals:
            strength_value = getattr(signal, 'strength', SignalStrength.MODERATE).value
            score = getattr(signal, 'confidence', 0.5) * strength_value
            scored_signals.append((score, signal))
        
        # Sort by score and take top signals
        scored_signals.sort(key=lambda x: x[0], reverse=True)
        return [signal for _, signal in scored_signals[:max_signals]]
    
    async def _simple_average_combination(
        self,
        signals: List[Any],
        symbol: str,
        weights: Dict[str, float],
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Simple average combination"""
        
        strengths = [getattr(s, 'strength', SignalStrength.MODERATE).value * 
                     (-1 if getattr(s, 'signal_type', SignalType.BUY) == SignalType.SELL else 1) 
                     for s in signals]
        confidences = [getattr(s, 'confidence', 0.5) for s in signals]
        position_sizes = [getattr(s, 'suggested_position_size', 0.0) for s in signals]
        
        combined_strength = np.mean(strengths)
        combined_confidence = np.mean(confidences)
        combined_position_size = np.mean(position_sizes)
        
        return SignalCombination(
            combined_signal_id=f"combined_{symbol}_{int(time.time())}",
            symbol=symbol,
            combination_method=CombinationMethod.SIMPLE_AVERAGE,
            timestamp=datetime.now(),
            combined_strength=combined_strength,
            combined_confidence=combined_confidence,
            combined_position_size=combined_position_size,
            component_signals=signals,
            signal_weights={getattr(s, 'signal_id', f'signal_{i}'): 1.0/len(signals) for i, s in enumerate(signals)},
            expected_return=combined_strength * 0.1,  # Simplified
            expected_volatility=np.mean([getattr(s, 'expected_volatility', 0.2) for s in signals]),
            expected_sharpe=0.0  # To be calculated
        )
    
    async def _weighted_average_combination(
        self,
        signals: List[Any],
        symbol: str,
        weights: Dict[str, float],
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Weighted average combination"""
        
        combined_strength = 0.0
        combined_confidence = 0.0
        combined_position_size = 0.0
        
        for i, signal in enumerate(signals):
            signal_id = getattr(signal, 'signal_id', f'signal_{i}')
            weight = weights.get(signal_id, 0.0)
            
            # Get strength with direction based on signal type
            strength_value = getattr(signal, 'strength', SignalStrength.MODERATE).value
            if getattr(signal, 'signal_type', SignalType.BUY) == SignalType.SELL:
                strength_value = -strength_value
            
            combined_strength += weight * strength_value
            combined_confidence += weight * getattr(signal, 'confidence', 0.5)
            combined_position_size += weight * getattr(signal, 'suggested_position_size', 0.0)
        
        return SignalCombination(
            combined_signal_id=f"combined_{symbol}_{int(time.time())}",
            symbol=symbol,
            combination_method=CombinationMethod.WEIGHTED_AVERAGE,
            timestamp=datetime.now(),
            combined_strength=combined_strength,
            combined_confidence=combined_confidence,
            combined_position_size=combined_position_size,
            component_signals=signals,
            signal_weights=weights,
            expected_return=combined_strength * 0.1,
            expected_volatility=np.mean([getattr(s, 'expected_volatility', 0.2) for s in signals]),
            expected_sharpe=0.0
        )
    
    async def _confidence_weighted_combination(
        self,
        signals: List[Any],
        symbol: str,
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Confidence-weighted combination"""
        
        confidences = [getattr(s, 'confidence', 0.5) for s in signals]
        total_confidence = sum(confidences)
        
        if total_confidence == 0:
            return await self._simple_average_combination(signals, symbol, {}, context)
        
        combined_strength = 0.0
        combined_position_size = 0.0
        
        weights = {}
        for i, signal in enumerate(signals):
            weight = confidences[i] / total_confidence
            signal_id = getattr(signal, 'signal_id', f'signal_{i}')
            weights[signal_id] = weight
            
            # Get strength with direction based on signal type
            strength_value = getattr(signal, 'strength', SignalStrength.MODERATE).value
            if getattr(signal, 'signal_type', SignalType.BUY) == SignalType.SELL:
                strength_value = -strength_value
            
            combined_strength += weight * strength_value
            combined_position_size += weight * getattr(signal, 'suggested_position_size', 0.0)
        
        combined_confidence = np.mean(confidences)  # Average confidence
        
        return SignalCombination(
            combined_signal_id=f"combined_{symbol}_{int(time.time())}",
            symbol=symbol,
            combination_method=CombinationMethod.CONFIDENCE_WEIGHTED,
            timestamp=datetime.now(),
            combined_strength=combined_strength,
            combined_confidence=combined_confidence,
            combined_position_size=combined_position_size,
            component_signals=signals,
            signal_weights=weights,
            expected_return=combined_strength * 0.1,
            expected_volatility=np.mean([getattr(s, 'expected_volatility', 0.2) for s in signals]),
            expected_sharpe=0.0
        )
    
    async def _performance_weighted_combination(
        self,
        signals: List[Any],
        symbol: str,
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Performance-weighted combination"""
        
        # Use performance-based weights
        weights = self.weight_calculator.calculate_weights(
            signals,
            SignalWeight.PERFORMANCE,
            context
        )
        
        return await self._weighted_average_combination(signals, symbol, weights, context)
    
    async def _rank_based_combination(
        self,
        signals: List[Any],
        symbol: str,
        weights: Dict[str, float],
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Rank-based combination"""
        
        # Rank signals by strength
        signal_strengths = [(getattr(s, 'strength', 0.0), i, s) for i, s in enumerate(signals)]
        signal_strengths.sort(reverse=True)
        
        # Assign rank-based weights
        n = len(signals)
        rank_weights = {}
        
        for rank, (strength, orig_idx, signal) in enumerate(signal_strengths):
            signal_id = getattr(signal, 'signal_id', f'signal_{orig_idx}')
            # Higher weight for higher rank (lower rank number)
            rank_weights[signal_id] = (n - rank) / sum(range(1, n + 1))
        
        return await self._weighted_average_combination(signals, symbol, rank_weights, context)
    
    async def _machine_learning_combination(
        self,
        signals: List[Any],
        symbol: str,
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Machine learning-based combination"""
        
        try:
            # Use ensemble model if available
            strength, confidence = self.ensemble_engine.predict_combination(signals, symbol)
            
            # Calculate position size based on combined signal
            avg_position_size = np.mean([getattr(s, 'suggested_position_size', 0.0) for s in signals])
            combined_position_size = strength * avg_position_size
            
            # Equal weights for component attribution
            weights = {getattr(s, 'signal_id', f'signal_{i}'): 1.0/len(signals) for i, s in enumerate(signals)}
            
            return SignalCombination(
                combined_signal_id=f"combined_{symbol}_{int(time.time())}",
                symbol=symbol,
                combination_method=CombinationMethod.MACHINE_LEARNING,
                timestamp=datetime.now(),
                combined_strength=strength,
                combined_confidence=confidence,
                combined_position_size=combined_position_size,
                component_signals=signals,
                signal_weights=weights,
                expected_return=strength * 0.1,
                expected_volatility=np.mean([getattr(s, 'expected_volatility', 0.2) for s in signals]),
                expected_sharpe=0.0
            )
            
        except Exception as e:
            logger.error(f"ML combination failed for {symbol}: {e}")
            # Fallback to weighted average
            weights = self.weight_calculator.calculate_weights(signals, SignalWeight.CONFIDENCE, context)
            return await self._weighted_average_combination(signals, symbol, weights, context)
    
    async def _ensemble_voting_combination(
        self,
        signals: List[Any],
        symbol: str,
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Ensemble voting combination"""
        
        # Count votes for long/short/neutral
        long_votes = sum(1 for s in signals if getattr(s, 'strength', SignalStrength.MODERATE).value > 0.1)
        short_votes = sum(1 for s in signals if getattr(s, 'strength', SignalStrength.MODERATE).value < -0.1)
        neutral_votes = len(signals) - long_votes - short_votes
        
        total_votes = len(signals)
        
        # Determine combined signal based on majority vote
        if long_votes / total_votes >= self.config.voting_threshold:
            combined_strength = 0.5  # Moderate long signal
        elif short_votes / total_votes >= self.config.voting_threshold:
            combined_strength = -0.5  # Moderate short signal
        else:
            combined_strength = 0.0  # Neutral
        
        # Confidence based on consensus level
        max_votes = max(long_votes, short_votes, neutral_votes)
        combined_confidence = max_votes / total_votes
        
        # Equal weights
        weights = {getattr(s, 'signal_id', f'signal_{i}'): 1.0/len(signals) for i, s in enumerate(signals)}
        
        combined_position_size = combined_strength * np.mean([abs(getattr(s, 'suggested_position_size', 0.0)) for s in signals])
        
        return SignalCombination(
            combined_signal_id=f"combined_{symbol}_{int(time.time())}",
            symbol=symbol,
            combination_method=CombinationMethod.ENSEMBLE_VOTING,
            timestamp=datetime.now(),
            combined_strength=combined_strength,
            combined_confidence=combined_confidence,
            combined_position_size=combined_position_size,
            component_signals=signals,
            signal_weights=weights,
            expected_return=combined_strength * 0.1,
            expected_volatility=np.mean([getattr(s, 'expected_volatility', 0.2) for s in signals]),
            expected_sharpe=0.0,
            combination_details={
                'long_votes': long_votes,
                'short_votes': short_votes,
                'neutral_votes': neutral_votes,
                'voting_threshold': self.config.voting_threshold
            }
        )
    
    async def _dynamic_weighting_combination(
        self,
        signals: List[Any],
        symbol: str,
        context: Dict[str, Any]
    ) -> SignalCombination:
        """Dynamic weighting based on recent performance"""
        
        # Get recent performance data
        with self._lock:
            recent_combinations = self._symbol_combinations.get(symbol, [])
        
        if not recent_combinations:
            # Fallback to confidence weighting
            return await self._confidence_weighted_combination(signals, symbol, context)
        
        # Calculate adaptive weights based on recent performance
        signal_performance = defaultdict(list)
        
        # Simplified: use last few combinations
        for combination in recent_combinations[-10:]:
            for signal_id, weight in combination.signal_weights.items():
                # Estimate signal contribution to performance
                signal_performance[signal_id].append(weight * combination.combined_strength)
        
        # Calculate dynamic weights
        dynamic_weights = {}
        total_weight = 0.0
        
        for signal in signals:
            signal_id = getattr(signal, 'signal_id', f'signal_{id(signal)}')
            
            if signal_id in signal_performance:
                # Recent performance average
                recent_perf = np.mean(signal_performance[signal_id])
                weight = max(recent_perf + 0.1, 0.01)  # Minimum weight
            else:
                # Default weight for new signals
                weight = 0.5
            
            dynamic_weights[signal_id] = weight
            total_weight += weight
        
        # Normalize weights
        if total_weight > 0:
            dynamic_weights = {k: v/total_weight for k, v in dynamic_weights.items()}
        else:
            dynamic_weights = {getattr(s, 'signal_id', f'signal_{i}'): 1.0/len(signals) for i, s in enumerate(signals)}
        
        return await self._weighted_average_combination(signals, symbol, dynamic_weights, context)
    
    def _calculate_combination_quality(self, signals: List[Any], combination: SignalCombination) -> float:
        """Calculate quality score for signal combination"""
        
        # Factors: signal quality, consensus, diversification
        avg_confidence = np.mean([getattr(s, 'confidence', 0.5) for s in signals])
        
        # Signal strength consistency
        strengths = [getattr(s, 'strength', SignalStrength.MODERATE).value for s in signals]
        strength_std = np.std(strengths) if len(strengths) > 1 else 0.0
        consistency_score = 1.0 / (1.0 + strength_std)  # Higher for more consistent signals
        
        # Overall quality score
        quality_score = (avg_confidence * 0.5 + 
                        combination.consensus_level * 0.3 + 
                        consistency_score * 0.2)
        
        return min(quality_score, 1.0)
    
    def _calculate_consensus_level(self, signals: List[Any]) -> float:
        """Calculate consensus level among signals"""
        
        strengths = [getattr(s, 'strength', SignalStrength.MODERATE).value for s in signals]
        
        if not strengths:
            return 0.0
        
        # Check direction consensus
        positive = sum(1 for s in strengths if s > 0)
        negative = sum(1 for s in strengths if s < 0)
        neutral = len(strengths) - positive - negative
        
        max_consensus = max(positive, negative, neutral)
        consensus_level = max_consensus / len(strengths)
        
        return consensus_level
    
    def _calculate_diversification_score(self, signals: List[Any]) -> float:
        """Calculate diversification score among signals"""
        
        # Simplified: based on signal types
        signal_types = [getattr(s, 'signal_type', 'unknown') for s in signals]
        unique_types = len(set(signal_types))
        
        diversification_score = min(unique_types / max(len(signals), 1), 1.0)
        
        return diversification_score
    
    def train_combination_models(
        self,
        historical_data: Dict[str, Any],
        symbols: List[str]
    ) -> Dict[str, EnsembleModel]:
        """Train combination models for multiple symbols"""
        
        trained_models = {}
        
        for symbol in symbols:
            try:
                symbol_data = historical_data.get(symbol, {})
                training_signals = symbol_data.get('signals', [])
                training_returns = symbol_data.get('returns', [])
                
                if len(training_signals) >= self.config.ml_lookback:
                    model = self.ensemble_engine.train_ensemble_model(
                        training_signals[-self.config.ml_lookback:],
                        training_returns[-self.config.ml_lookback:],
                        symbol
                    )
                    trained_models[symbol] = model
                    logger.info(f"Trained combination model for {symbol}")
                
            except Exception as e:
                logger.error(f"Error training model for {symbol}: {e}")
                continue
        
        return trained_models
    
    def update_performance(self, combination_id: str, realized_return: float) -> None:
        """Update performance tracking for a combination"""
        
        with self._lock:
            # Find the combination
            for combination in self._combination_history:
                if combination.combined_signal_id == combination_id:
                    # Store performance
                    self._combination_performance[combination_id].append({
                        'realized_return': realized_return,
                        'expected_return': combination.expected_return,
                        'timestamp': datetime.now()
                    })
                    
                    # Update method performance
                    method = combination.combination_method.value
                    self._method_performance[method].append(realized_return)
                    
                    logger.debug(f"Updated performance for combination {combination_id}: {realized_return:.3f}")
                    break
    
    def get_combination_statistics(self) -> Dict[str, Any]:
        """Get combination statistics"""
        
        with self._lock:
            method_stats = {}
            
            for method, returns in self._method_performance.items():
                if returns:
                    method_stats[method] = {
                        'count': len(returns),
                        'mean_return': np.mean(returns),
                        'std_return': np.std(returns),
                        'sharpe_ratio': np.mean(returns) / max(np.std(returns), 0.01),
                        'win_rate': sum(1 for r in returns if r > 0) / len(returns)
                    }
            
            return {
                'total_combinations': len(self._combination_history),
                'method_performance': method_stats,
                'trained_models': len(self.ensemble_engine.models),
                'active_symbols': len(self._symbol_combinations)
            }
    
    def get_recent_combinations(self, symbol: Optional[str] = None, limit: int = 100) -> List[SignalCombination]:
        """Get recent combinations"""
        
        with self._lock:
            if symbol:
                return list(self._symbol_combinations.get(symbol, []))[-limit:]
            else:
                return list(self._combination_history)[-limit:]