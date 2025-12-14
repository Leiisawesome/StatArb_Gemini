"""
Signals Engine - Signal Generator
Advanced signal generation with multiple signal types, factor analysis, and research capabilities
"""

import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
from scipy import stats
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    VOLATILITY = "volatility"
    CROSS_SECTIONAL = "cross_sectional"
    TIME_SERIES = "time_series"
    FACTOR_BASED = "factor_based"

class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class SignalDirection(Enum):
    """Signal direction"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"

@dataclass
class SignalParameters:
    """Signal generation parameters"""
    signal_type: SignalType
    lookback_period: int

    # Technical parameters
    fast_period: Optional[int] = None
    slow_period: Optional[int] = None
    threshold: Optional[float] = None

    # Statistical parameters
    z_score_threshold: float = 2.0
    confidence_level: float = 0.95
    min_observations: int = 20

    # Factor parameters
    factors: List[str] = field(default_factory=list)
    factor_weights: Optional[Dict[str, float]] = None

    # Risk parameters
    max_position_size: float = 1.0
    stop_loss_threshold: Optional[float] = None
    take_profit_threshold: Optional[float] = None

    # Timing parameters
    entry_delay: int = 0
    exit_delay: int = 0
    signal_decay: float = 1.0  # Signal strength decay per period

    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SignalResult:
    """Signal generation result"""
    signal_id: str
    symbol: str
    timestamp: datetime

    # Signal properties
    signal_type: SignalType
    direction: SignalDirection
    strength: float  # -1.0 to 1.0
    strength_category: SignalStrength
    confidence: float  # 0.0 to 1.0

    # Quantitative metrics
    z_score: Optional[float] = None
    p_value: Optional[float] = None
    sharpe_ratio: Optional[float] = None

    # Position sizing
    suggested_position_size: float = 0.0
    max_position_size: float = 1.0

    # Risk metrics
    expected_return: Optional[float] = None
    expected_volatility: Optional[float] = None
    var_95: Optional[float] = None

    # Timing
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    expected_holding_period: Optional[int] = None

    # Supporting data
    underlying_data: Dict[str, Any] = field(default_factory=dict)
    factor_exposures: Dict[str, float] = field(default_factory=dict)

    # Metadata
    generation_method: str = ""
    model_version: str = "1.0"
    data_quality_score: float = 1.0

    # Decay tracking
    signal_age: int = 0
    decayed_strength: Optional[float] = None

@dataclass
class SignalStatistics:
    """Signal generation statistics"""
    generator_id: str

    # Generation statistics
    total_signals_generated: int = 0
    signals_by_type: Dict[str, int] = field(default_factory=dict)
    signals_by_direction: Dict[str, int] = field(default_factory=dict)
    signals_by_strength: Dict[str, int] = field(default_factory=dict)

    # Performance metrics
    average_signal_strength: float = 0.0
    average_confidence: float = 0.0
    signal_accuracy: float = 0.0  # Historical accuracy if available

    # Timing metrics
    average_generation_time_ms: float = 0.0
    last_generation_time: Optional[datetime] = None

    # Quality metrics
    data_quality_average: float = 0.0
    rejected_signals_count: int = 0

    # Error statistics
    generation_errors: int = 0
    data_errors: int = 0
    calculation_errors: int = 0

    last_update: datetime = field(default_factory=datetime.now)

class SignalStrategy(ABC):
    """Abstract signal generation strategy"""

    def __init__(self, name: str, parameters: SignalParameters):
        self.name = name
        self.parameters = parameters
        self.statistics = SignalStatistics(generator_id=name)

    @abstractmethod
    async def generate_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> Optional[SignalResult]:
        """Generate signal for symbol"""

    @abstractmethod
    def get_required_data_fields(self) -> List[str]:
        """Get required data fields"""

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data"""
        required_fields = self.get_required_data_fields()

        if data.empty:
            return False

        # Check required columns
        missing_fields = set(required_fields) - set(data.columns)
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            return False

        # Check minimum observations
        if len(data) < self.parameters.min_observations:
            logger.warning(f"Insufficient data: {len(data)} < {self.parameters.min_observations}")
            return False

        return True

class MomentumSignalStrategy(SignalStrategy):
    """Momentum-based signal strategy"""

    def __init__(self, parameters: SignalParameters):
        super().__init__("momentum_strategy", parameters)

    async def generate_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> Optional[SignalResult]:
        """Generate momentum signal"""

        try:
            if not self.validate_data(data):
                return None

            # Calculate momentum indicators
            lookback = self.parameters.lookback_period
            prices = data['close'].values

            # Price momentum
            price_momentum = (prices[-1] / prices[-lookback] - 1) if len(prices) >= lookback else 0

            # Moving average crossover
            fast_ma = np.mean(prices[-self.parameters.fast_period:]) if self.parameters.fast_period else prices[-1]
            slow_ma = np.mean(prices[-self.parameters.slow_period:]) if self.parameters.slow_period else prices[-lookback]

            ma_signal = (fast_ma / slow_ma - 1) if slow_ma != 0 else 0

            # Rate of change
            roc = np.diff(prices[-lookback:])
            avg_roc = np.mean(roc) if len(roc) > 0 else 0

            # Combine signals
            momentum_score = (price_momentum * 0.4 + ma_signal * 0.4 + avg_roc * 0.2)

            # Determine direction and strength
            direction = SignalDirection.LONG if momentum_score > 0 else SignalDirection.SHORT
            strength = np.clip(abs(momentum_score) * 5, 0, 1)  # Scale to 0-1

            # Calculate confidence based on consistency
            momentum_values = []
            for i in range(min(5, len(prices) - lookback + 1)):
                start_idx = -(lookback + i)
                end_idx = -i if i > 0 else None
                mom = (prices[end_idx or -1] / prices[start_idx] - 1)
                momentum_values.append(mom)

            consistency = 1 - np.std(momentum_values) if len(momentum_values) > 1 else 0.5
            confidence = np.clip(consistency, 0, 1)

            # Calculate position sizing
            volatility = np.std(prices[-lookback:]) / np.mean(prices[-lookback:])
            position_size = np.clip(strength / max(volatility, 0.01), 0, self.parameters.max_position_size)

            # Create signal result
            signal_result = SignalResult(
                signal_id=f"momentum_{symbol}_{int(time.time())}",
                symbol=symbol,
                timestamp=datetime.now(),
                signal_type=SignalType.MOMENTUM,
                direction=direction,
                strength=strength if direction == SignalDirection.LONG else -strength,
                strength_category=self._categorize_strength(strength),
                confidence=confidence,
                suggested_position_size=position_size,
                max_position_size=self.parameters.max_position_size,
                entry_price=prices[-1],
                underlying_data={
                    'price_momentum': price_momentum,
                    'ma_signal': ma_signal,
                    'avg_roc': avg_roc,
                    'volatility': volatility
                },
                generation_method="momentum_crossover",
                data_quality_score=self._calculate_data_quality(data)
            )

            # Update statistics
            self._update_statistics(signal_result)

            return signal_result

        except Exception as e:
            logger.error(f"Error generating momentum signal for {symbol}: {e}")
            self.statistics.generation_errors += 1
            return None

    def get_required_data_fields(self) -> List[str]:
        """Get required data fields"""
        return ['close', 'timestamp']

    def _categorize_strength(self, strength: float) -> SignalStrength:
        """Categorize signal strength"""
        if strength < 0.2:
            return SignalStrength.VERY_WEAK
        elif strength < 0.4:
            return SignalStrength.WEAK
        elif strength < 0.6:
            return SignalStrength.MODERATE
        elif strength < 0.8:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG

    def _calculate_data_quality(self, data: pd.DataFrame) -> float:
        """Calculate data quality score"""
        try:
            # Check for missing values
            missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))

            # Check for price anomalies
            price_changes = data['close'].pct_change().dropna()
            outlier_ratio = len(price_changes[abs(price_changes) > 0.1]) / len(price_changes)

            # Combine quality metrics
            quality_score = (1 - missing_ratio) * 0.5 + (1 - outlier_ratio) * 0.5

            return np.clip(quality_score, 0, 1)

        except Exception:
            return 0.5

    def _update_statistics(self, signal: SignalResult) -> None:
        """Update strategy statistics"""
        stats = self.statistics

        stats.total_signals_generated += 1
        stats.signals_by_type[signal.signal_type.value] = stats.signals_by_type.get(signal.signal_type.value, 0) + 1
        stats.signals_by_direction[signal.direction.value] = stats.signals_by_direction.get(signal.direction.value, 0) + 1
        stats.signals_by_strength[signal.strength_category.value] = stats.signals_by_strength.get(signal.strength_category.value, 0) + 1

        # Update averages
        total = stats.total_signals_generated
        stats.average_signal_strength = ((stats.average_signal_strength * (total - 1)) + abs(signal.strength)) / total
        stats.average_confidence = ((stats.average_confidence * (total - 1)) + signal.confidence) / total
        stats.data_quality_average = ((stats.data_quality_average * (total - 1)) + signal.data_quality_score) / total

        stats.last_generation_time = datetime.now()
        stats.last_update = datetime.now()

class MeanReversionSignalStrategy(SignalStrategy):
    """Mean reversion signal strategy"""

    def __init__(self, parameters: SignalParameters):
        super().__init__("mean_reversion_strategy", parameters)

    async def generate_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> Optional[SignalResult]:
        """Generate mean reversion signal"""

        try:
            if not self.validate_data(data):
                return None

            lookback = self.parameters.lookback_period
            prices = data['close'].values

            # Calculate z-score
            recent_prices = prices[-lookback:]
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)

            if std_price == 0:
                return None

            current_price = prices[-1]
            z_score = (current_price - mean_price) / std_price

            # Bollinger Band deviation
            bb_upper = mean_price + (2 * std_price)
            bb_lower = mean_price - (2 * std_price)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5

            # RSI-like oscillator
            price_changes = np.diff(recent_prices)
            gains = np.where(price_changes > 0, price_changes, 0)
            losses = np.where(price_changes < 0, -price_changes, 0)

            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0

            rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            rsi = 100 - (100 / (1 + rs)) if rs != float('inf') else 100

            # Combine mean reversion signals
            # Strong positive z-score suggests overextension (short signal)
            # Strong negative z-score suggests oversold (long signal)

            reversion_score = -z_score * 0.6 + (50 - rsi) / 50 * 0.3 + (0.5 - bb_position) * 0.1

            # Determine direction and strength
            direction = SignalDirection.LONG if reversion_score > 0 else SignalDirection.SHORT
            strength = np.clip(abs(reversion_score), 0, 1)

            # Calculate confidence based on z-score magnitude
            confidence = np.clip(abs(z_score) / self.parameters.z_score_threshold, 0, 1)

            # Only generate signal if z-score exceeds threshold
            if abs(z_score) < self.parameters.z_score_threshold:
                return None

            # Calculate position sizing based on reversion strength
            volatility = std_price / mean_price
            position_size = np.clip(strength / max(volatility, 0.01), 0, self.parameters.max_position_size)

            # Calculate target and stop prices
            target_price = mean_price  # Target is the mean
            if direction == SignalDirection.LONG:
                stop_loss_price = current_price * 0.98  # 2% stop loss
            else:
                stop_loss_price = current_price * 1.02

            # Create signal result
            signal_result = SignalResult(
                signal_id=f"mean_reversion_{symbol}_{int(time.time())}",
                symbol=symbol,
                timestamp=datetime.now(),
                signal_type=SignalType.MEAN_REVERSION,
                direction=direction,
                strength=strength if direction == SignalDirection.LONG else -strength,
                strength_category=self._categorize_strength(strength),
                confidence=confidence,
                z_score=z_score,
                suggested_position_size=position_size,
                max_position_size=self.parameters.max_position_size,
                entry_price=current_price,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                expected_holding_period=lookback // 2,  # Expect reversion within half lookback period
                underlying_data={
                    'z_score': z_score,
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'mean_price': mean_price,
                    'volatility': volatility,
                    'reversion_score': reversion_score
                },
                generation_method="z_score_mean_reversion",
                data_quality_score=self._calculate_data_quality(data)
            )

            # Update statistics
            self._update_statistics(signal_result)

            return signal_result

        except Exception as e:
            logger.error(f"Error generating mean reversion signal for {symbol}: {e}")
            self.statistics.generation_errors += 1
            return None

    def get_required_data_fields(self) -> List[str]:
        """Get required data fields"""
        return ['close', 'timestamp']

    def _categorize_strength(self, strength: float) -> SignalStrength:
        """Categorize signal strength"""
        if strength < 0.2:
            return SignalStrength.VERY_WEAK
        elif strength < 0.4:
            return SignalStrength.WEAK
        elif strength < 0.6:
            return SignalStrength.MODERATE
        elif strength < 0.8:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG

    def _calculate_data_quality(self, data: pd.DataFrame) -> float:
        """Calculate data quality score"""
        try:
            # Check for missing values
            missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))

            # Check for price continuity
            price_changes = data['close'].pct_change().dropna()
            gap_ratio = len(price_changes[abs(price_changes) > 0.1]) / len(price_changes)

            # Check for sufficient variance
            price_std = data['close'].std()
            price_mean = data['close'].mean()
            variance_score = 1 if price_mean > 0 and (price_std / price_mean) > 0.01 else 0.5

            quality_score = (1 - missing_ratio) * 0.4 + (1 - gap_ratio) * 0.4 + variance_score * 0.2

            return np.clip(quality_score, 0, 1)

        except Exception:
            return 0.5

    def _update_statistics(self, signal: SignalResult) -> None:
        """Update strategy statistics"""
        stats = self.statistics

        stats.total_signals_generated += 1
        stats.signals_by_type[signal.signal_type.value] = stats.signals_by_type.get(signal.signal_type.value, 0) + 1
        stats.signals_by_direction[signal.direction.value] = stats.signals_by_direction.get(signal.direction.value, 0) + 1
        stats.signals_by_strength[signal.strength_category.value] = stats.signals_by_strength.get(signal.strength_category.value, 0) + 1

        # Update averages
        total = stats.total_signals_generated
        stats.average_signal_strength = ((stats.average_signal_strength * (total - 1)) + abs(signal.strength)) / total
        stats.average_confidence = ((stats.average_confidence * (total - 1)) + signal.confidence) / total
        stats.data_quality_average = ((stats.data_quality_average * (total - 1)) + signal.data_quality_score) / total

        stats.last_generation_time = datetime.now()
        stats.last_update = datetime.now()

class StatisticalArbitrageSignalStrategy(SignalStrategy):
    """Statistical arbitrage signal strategy"""

    def __init__(self, parameters: SignalParameters):
        super().__init__("statistical_arbitrage_strategy", parameters)
        self.cointegration_cache = {}

    async def generate_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> Optional[SignalResult]:
        """Generate statistical arbitrage signal"""

        try:
            if not self.validate_data(data):
                return None

            # Get pair data from context
            pair_data = context.get('pair_data')
            if pair_data is None or symbol not in pair_data:
                return None

            primary_prices = data['close'].values
            pair_prices = pair_data[symbol]['close'].values

            # Ensure same length
            min_length = min(len(primary_prices), len(pair_prices))
            primary_prices = primary_prices[-min_length:]
            pair_prices = pair_prices[-min_length:]

            if min_length < self.parameters.lookback_period:
                return None

            # Calculate spread
            spread = primary_prices - pair_prices

            # Calculate rolling statistics for spread
            lookback = self.parameters.lookback_period
            spread_window = spread[-lookback:]

            spread_mean = np.mean(spread_window)
            spread_std = np.std(spread_window)

            if spread_std == 0:
                return None

            # Current spread z-score
            current_spread = spread[-1]
            spread_z_score = (current_spread - spread_mean) / spread_std

            # Check cointegration (simplified Engle-Granger test)
            cointegration_score = self._test_cointegration(primary_prices, pair_prices)

            # Calculate hedge ratio using linear regression
            hedge_ratio = self._calculate_hedge_ratio(primary_prices, pair_prices)

            # Adjusted spread using hedge ratio
            adjusted_spread = primary_prices - (hedge_ratio * pair_prices)
            adjusted_spread_z = (adjusted_spread[-1] - np.mean(adjusted_spread[-lookback:])) / np.std(adjusted_spread[-lookback:])

            # Combine signals
            arbitrage_score = -adjusted_spread_z  # Negative z-score suggests long primary, short pair

            # Determine direction and strength
            direction = SignalDirection.LONG if arbitrage_score > 0 else SignalDirection.SHORT
            strength = np.clip(abs(arbitrage_score) / self.parameters.z_score_threshold, 0, 1)

            # Only generate signal if spread z-score exceeds threshold and pairs are cointegrated
            if abs(adjusted_spread_z) < self.parameters.z_score_threshold or cointegration_score < 0.5:
                return None

            # Calculate confidence based on cointegration and spread stability
            spread_consistency = 1 - np.std(np.diff(spread_window)) / abs(spread_mean) if spread_mean != 0 else 0
            confidence = np.clip((cointegration_score + spread_consistency) / 2, 0, 1)

            # Position sizing
            spread_volatility = spread_std / abs(spread_mean) if spread_mean != 0 else 1
            position_size = np.clip(strength / max(spread_volatility, 0.01), 0, self.parameters.max_position_size)

            # Create signal result
            signal_result = SignalResult(
                signal_id=f"stat_arb_{symbol}_{int(time.time())}",
                symbol=symbol,
                timestamp=datetime.now(),
                signal_type=SignalType.STATISTICAL_ARBITRAGE,
                direction=direction,
                strength=strength if direction == SignalDirection.LONG else -strength,
                strength_category=self._categorize_strength(strength),
                confidence=confidence,
                z_score=adjusted_spread_z,
                suggested_position_size=position_size,
                max_position_size=self.parameters.max_position_size,
                entry_price=primary_prices[-1],
                target_price=primary_prices[-1] + (hedge_ratio * pair_prices[-1] - adjusted_spread[-1]) / 2,
                expected_holding_period=lookback // 4,  # Expect convergence within quarter of lookback
                underlying_data={
                    'spread_z_score': spread_z_score,
                    'adjusted_spread_z': adjusted_spread_z,
                    'hedge_ratio': hedge_ratio,
                    'cointegration_score': cointegration_score,
                    'spread_mean': spread_mean,
                    'spread_std': spread_std,
                    'pair_symbol': list(pair_data.keys())[0] if pair_data else None
                },
                factor_exposures={
                    'spread_factor': adjusted_spread_z,
                    'cointegration_factor': cointegration_score
                },
                generation_method="cointegration_spread",
                data_quality_score=self._calculate_data_quality(data)
            )

            # Update statistics
            self._update_statistics(signal_result)

            return signal_result

        except Exception as e:
            logger.error(f"Error generating statistical arbitrage signal for {symbol}: {e}")
            self.statistics.generation_errors += 1
            return None

    def get_required_data_fields(self) -> List[str]:
        """Get required data fields"""
        return ['close', 'timestamp']

    def _test_cointegration(self, series1: np.ndarray, series2: np.ndarray) -> float:
        """Test cointegration between two series (simplified)"""
        try:
            # Simple correlation-based cointegration test
            correlation = np.corrcoef(series1, series2)[0, 1]

            # Test if spread is stationary (simplified ADF test)
            spread = series1 - series2
            spread_changes = np.diff(spread)

            # Check if spread changes have zero mean (stationarity indicator)
            t_stat, p_value = stats.ttest_1samp(spread_changes, 0)
            stationarity_score = 1 - min(p_value, 1.0) if not np.isnan(p_value) else 0

            # Combine correlation and stationarity
            cointegration_score = (abs(correlation) + stationarity_score) / 2

            return np.clip(cointegration_score, 0, 1)

        except Exception:
            return 0.0

    def _calculate_hedge_ratio(self, series1: np.ndarray, series2: np.ndarray) -> float:
        """Calculate hedge ratio using linear regression"""
        try:
            # Linear regression: series1 = alpha + beta * series2
            correlation_matrix = np.corrcoef(series1, series2)
            correlation = correlation_matrix[0, 1]

            std1 = np.std(series1)
            std2 = np.std(series2)

            # Beta coefficient (hedge ratio)
            hedge_ratio = correlation * (std1 / std2) if std2 != 0 else 1.0

            return hedge_ratio

        except Exception:
            return 1.0

    def _categorize_strength(self, strength: float) -> SignalStrength:
        """Categorize signal strength"""
        if strength < 0.2:
            return SignalStrength.VERY_WEAK
        elif strength < 0.4:
            return SignalStrength.WEAK
        elif strength < 0.6:
            return SignalStrength.MODERATE
        elif strength < 0.8:
            return SignalStrength.STRONG
        else:
            return SignalStrength.VERY_STRONG

    def _calculate_data_quality(self, data: pd.DataFrame) -> float:
        """Calculate data quality score"""
        try:
            # Check for missing values
            missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))

            # Check for sufficient data points
            length_score = min(len(data) / self.parameters.min_observations, 1.0)

            # Check for price volatility (not flat)
            price_std = data['close'].std()
            price_mean = data['close'].mean()
            volatility_score = 1 if price_mean > 0 and (price_std / price_mean) > 0.005 else 0.5

            quality_score = (1 - missing_ratio) * 0.4 + length_score * 0.3 + volatility_score * 0.3

            return np.clip(quality_score, 0, 1)

        except Exception:
            return 0.5

    def _update_statistics(self, signal: SignalResult) -> None:
        """Update strategy statistics"""
        stats = self.statistics

        stats.total_signals_generated += 1
        stats.signals_by_type[signal.signal_type.value] = stats.signals_by_type.get(signal.signal_type.value, 0) + 1
        stats.signals_by_direction[signal.direction.value] = stats.signals_by_direction.get(signal.direction.value, 0) + 1
        stats.signals_by_strength[signal.strength_category.value] = stats.signals_by_strength.get(signal.strength_category.value, 0) + 1

        # Update averages
        total = stats.total_signals_generated
        stats.average_signal_strength = ((stats.average_signal_strength * (total - 1)) + abs(signal.strength)) / total
        stats.average_confidence = ((stats.average_confidence * (total - 1)) + signal.confidence) / total
        stats.data_quality_average = ((stats.data_quality_average * (total - 1)) + signal.data_quality_score) / total

        stats.last_generation_time = datetime.now()
        stats.last_update = datetime.now()

class SignalGenerator:
    """
    Advanced signal generation engine

    Orchestrates multiple signal strategies to generate trading signals
    with comprehensive analysis and risk assessment.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize signal generator"""
        self.config = config or {}

        # Strategy registry
        self._strategies = {}
        self._strategy_weights = {}

        # Threading
        self._lock = threading.Lock()

        # Signal tracking
        self._active_signals = {}
        self._signal_history = deque(maxlen=10000)

        # Performance tracking
        self._generation_times = deque(maxlen=1000)

        # Initialize default strategies
        self._initialize_default_strategies()

        # Background tasks
        self._monitoring_tasks = []

        logger.info("SignalGenerator initialized")

    def _initialize_default_strategies(self) -> None:
        """Initialize default signal strategies"""

        # Momentum strategy
        momentum_params = SignalParameters(
            signal_type=SignalType.MOMENTUM,
            lookback_period=20,
            fast_period=5,
            slow_period=20,
            z_score_threshold=1.5
        )
        self.register_strategy(MomentumSignalStrategy(momentum_params), weight=0.3)

        # Mean reversion strategy
        mean_reversion_params = SignalParameters(
            signal_type=SignalType.MEAN_REVERSION,
            lookback_period=50,
            z_score_threshold=2.0,
            confidence_level=0.95
        )
        self.register_strategy(MeanReversionSignalStrategy(mean_reversion_params), weight=0.3)

        # Statistical arbitrage strategy
        stat_arb_params = SignalParameters(
            signal_type=SignalType.STATISTICAL_ARBITRAGE,
            lookback_period=100,
            z_score_threshold=2.5,
            confidence_level=0.99
        )
        self.register_strategy(StatisticalArbitrageSignalStrategy(stat_arb_params), weight=0.4)

        logger.info("Default signal strategies initialized")

    def register_strategy(self, strategy: SignalStrategy, weight: float = 1.0) -> None:
        """Register a signal strategy"""

        with self._lock:
            self._strategies[strategy.name] = strategy
            self._strategy_weights[strategy.name] = weight

        logger.info(f"Registered strategy: {strategy.name} (weight: {weight})")

    def unregister_strategy(self, strategy_name: str) -> bool:
        """Unregister a signal strategy"""

        try:
            with self._lock:
                self._strategies.pop(strategy_name, None)
                self._strategy_weights.pop(strategy_name, None)

            logger.info(f"Unregistered strategy: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"Error unregistering strategy {strategy_name}: {e}")
            return False

    async def generate_signals(
        self,
        symbols: List[str],
        data: Dict[str, pd.DataFrame],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[SignalResult]]:
        """Generate signals for multiple symbols"""

        context = context or {}
        results = {}

        for symbol in symbols:
            symbol_data = data.get(symbol)
            if symbol_data is not None and not symbol_data.empty:
                signals = await self.generate_signal(symbol, symbol_data, context)
                if signals:
                    results[symbol] = signals

        return results

    async def generate_signal(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None
    ) -> List[SignalResult]:
        """Generate signals for a single symbol"""

        start_time = time.time()
        context = context or {}
        signals = []

        try:
            # Generate signals from all strategies
            for strategy_name, strategy in self._strategies.items():
                try:
                    signal = await strategy.generate_signal(symbol, data, context)
                    if signal:
                        # Apply strategy weight
                        weight = self._strategy_weights.get(strategy_name, 1.0)
                        signal.strength *= weight
                        signal.suggested_position_size *= weight

                        signals.append(signal)

                        # Track active signals
                        with self._lock:
                            if symbol not in self._active_signals:
                                self._active_signals[symbol] = []
                            self._active_signals[symbol].append(signal)

                except Exception as e:
                    logger.error(f"Error in strategy {strategy_name} for {symbol}: {e}")
                    continue

            # Age existing signals and remove expired ones
            await self._age_signals(symbol)

            # Record generation time
            generation_time = (time.time() - start_time) * 1000
            self._generation_times.append(generation_time)

            # Add to history
            for signal in signals:
                self._signal_history.append(signal)

            logger.debug(f"Generated {len(signals)} signals for {symbol} in {generation_time:.2f}ms")

            return signals

        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []

    async def _age_signals(self, symbol: str) -> None:
        """Age signals and apply decay"""

        with self._lock:
            if symbol not in self._active_signals:
                return

            active_signals = self._active_signals[symbol]
            valid_signals = []

            current_time = datetime.now()

            for signal in active_signals:
                # Calculate signal age
                signal.signal_age = int((current_time - signal.timestamp).total_seconds() / 60)  # Age in minutes

                # Apply decay
                decay_factor = signal.signal_age * 0.1  # 10% decay per minute
                signal.decayed_strength = signal.strength * max(0, 1 - decay_factor)

                # Keep signal if not fully decayed
                if signal.decayed_strength > 0.01:  # Minimum threshold
                    valid_signals.append(signal)

            self._active_signals[symbol] = valid_signals

    def get_active_signals(self, symbol: Optional[str] = None) -> Dict[str, List[SignalResult]]:
        """Get active signals"""

        with self._lock:
            if symbol:
                return {symbol: self._active_signals.get(symbol, [])}
            else:
                return dict(self._active_signals)

    def get_signal_statistics(self) -> Dict[str, SignalStatistics]:
        """Get statistics for all strategies"""

        return {name: strategy.statistics for name, strategy in self._strategies.items()}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""

        with self._lock:
            total_signals = len(self._signal_history)
            avg_generation_time = np.mean(self._generation_times) if self._generation_times else 0

            # Signal distribution
            signal_types = defaultdict(int)
            signal_directions = defaultdict(int)

            for signal in self._signal_history:
                signal_types[signal.signal_type.value] += 1
                signal_directions[signal.direction.value] += 1

            return {
                'total_signals_generated': total_signals,
                'average_generation_time_ms': avg_generation_time,
                'active_signals_count': sum(len(signals) for signals in self._active_signals.values()),
                'signal_types_distribution': dict(signal_types),
                'signal_directions_distribution': dict(signal_directions),
                'registered_strategies': list(self._strategies.keys()),
                'strategy_weights': dict(self._strategy_weights)
            }

    def clear_expired_signals(self, max_age_hours: int = 24) -> int:
        """Clear expired signals"""

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        removed_count = 0

        with self._lock:
            for symbol in list(self._active_signals.keys()):
                original_count = len(self._active_signals[symbol])
                self._active_signals[symbol] = [
                    signal for signal in self._active_signals[symbol]
                    if signal.timestamp > cutoff_time
                ]
                removed_count += original_count - len(self._active_signals[symbol])

                # Remove empty entries
                if not self._active_signals[symbol]:
                    del self._active_signals[symbol]

        logger.info(f"Cleared {removed_count} expired signals")
        return removed_count