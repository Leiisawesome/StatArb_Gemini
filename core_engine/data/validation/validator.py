"""
Data Engine - Data Validator
Advanced data validation with quality scoring, anomaly detection, and integrity checking
"""

import logging
import threading
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
import warnings

# Import constants
from ..constants import (
    AnomalyDetection,
    ValidationThresholds,
    DataIntervals,
    DataRetention,
)

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    # Fallback for testing
    from abc import ABC, abstractmethod as abs_abstractmethod
    class ISystemComponent(ABC):
        @abs_abstractmethod
        async def initialize(self) -> bool: pass
        @abs_abstractmethod
        async def start(self) -> bool: pass
        @abs_abstractmethod
        async def stop(self) -> bool: pass
        @abs_abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abs_abstractmethod
        def get_status(self) -> Dict[str, Any]: pass

# Import centralized configuration (Rule 1, Section 7)
try:
    from core_engine.config import DataConfig as CentralizedDataConfig, DataValidationConfig
except ImportError:
    CentralizedDataConfig = None
    DataValidationConfig = None

logger = logging.getLogger(__name__)

class ValidationStatus(Enum):
    """Data validation status"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class ValidationRule(Enum):
    """Data validation rules"""
    PRICE_RANGE = "price_range"
    SPREAD_CHECK = "spread_check"
    VOLUME_CHECK = "volume_check"
    SEQUENCE_CHECK = "sequence_check"
    TIMESTAMP_CHECK = "timestamp_check"
    COMPLETENESS_CHECK = "completeness_check"
    CONSISTENCY_CHECK = "consistency_check"
    ANOMALY_DETECTION = "anomaly_detection"
    CROSS_VALIDATION = "cross_validation"
    STATISTICAL_CHECK = "statistical_check"

class AnomalyType(Enum):
    """Types of data anomalies"""
    PRICE_SPIKE = "price_spike"
    VOLUME_SPIKE = "volume_spike"
    SPREAD_ANOMALY = "spread_anomaly"
    MISSING_DATA = "missing_data"
    DUPLICATE_DATA = "duplicate_data"
    STALE_DATA = "stale_data"
    SEQUENCE_GAP = "sequence_gap"
    OUTLIER = "outlier"

@dataclass
class ValidationResult:
    """Data validation result"""
    validation_id: str
    data_id: str
    rule: ValidationRule
    status: ValidationStatus

    # Validation details
    score: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any]

    # Anomalies detected
    anomalies: List[AnomalyType] = field(default_factory=list)

    # Performance metrics
    validation_time_ms: float = 0.0

    # Temporal information
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    data_id: str
    symbol: str
    data_type: str

    # Overall quality score
    overall_score: float

    # Component scores
    accuracy_score: float
    completeness_score: float
    consistency_score: float
    timeliness_score: float
    validity_score: float

    # Detailed metrics
    missing_data_percentage: float
    duplicate_data_percentage: float
    anomaly_count: int
    validation_failures: int

    # Statistical metrics
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_deviation: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # Temporal metrics
    data_age_seconds: float = 0.0
    update_frequency_seconds: float = 0.0

    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationConfiguration:
    """
    DEPRECATED: Legacy validation configuration for data types

    This class provides backward compatibility. New code should use:
        from core_engine.config import DataValidationConfig

    Automatically converts to centralized DataValidationConfig format.
    """
    data_type: str
    symbol: Optional[str] = None

    # Price validation
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_price_change_pct: float = 20.0

    # Spread validation
    max_spread_pct: float = 5.0
    max_spread_bps: float = 500.0

    # Volume validation
    min_volume: float = 0
    max_volume_spike_factor: float = 10.0

    # Timing validation
    max_data_age_seconds: float = 30.0
    required_update_frequency_seconds: float = 1.0

    # Statistical validation
    outlier_threshold_std: float = 3.0
    moving_average_window: int = 20

    # Completeness validation
    required_fields: List[str] = field(default_factory=list)
    min_completeness_pct: float = 95.0

    # Cross-validation
    enable_cross_validation: bool = True
    cross_validation_sources: List[str] = field(default_factory=list)
    max_cross_validation_diff_pct: float = 2.0

    def __post_init__(self):
        """Warn about deprecation"""
        warnings.warn(
            "ValidationConfiguration is deprecated. Use DataValidationConfig from core_engine.config",
            DeprecationWarning,
            stacklevel=2
        )

    def to_centralized_config(self) -> 'DataValidationConfig':
        """Convert to centralized DataValidationConfig format"""
        if DataValidationConfig is None:
            raise ImportError("DataValidationConfig not available")

        return DataValidationConfig(
            enable_data_validation=True,
            quality_threshold=self.min_completeness_pct / 100.0,
            min_price=self.min_price,
            max_price=self.max_price,
            max_price_change_pct=self.max_price_change_pct,
            max_spread_pct=self.max_spread_pct,
            max_spread_bps=self.max_spread_bps,
            min_volume=self.min_volume,
            max_volume_spike_factor=self.max_volume_spike_factor,
            outlier_threshold_std=self.outlier_threshold_std,
            moving_average_window=self.moving_average_window,
            max_data_age_seconds=self.max_data_age_seconds,
            required_update_frequency_seconds=self.required_update_frequency_seconds,
            min_completeness_pct=self.min_completeness_pct,
            enable_cross_validation=self.enable_cross_validation,
            max_cross_validation_diff_pct=self.max_cross_validation_diff_pct
        )

class AnomalyDetector:
    """Advanced anomaly detection engine"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Historical data for comparison
        self._historical_data = defaultdict(lambda: defaultdict(deque))

        # Anomaly thresholds (use constants as defaults)
        self.price_spike_threshold = self.config.get(
            'price_spike_threshold', AnomalyDetection.PRICE_SPIKE_THRESHOLD_PERCENT
        )
        self.volume_spike_threshold = self.config.get(
            'volume_spike_threshold', AnomalyDetection.VOLUME_SPIKE_THRESHOLD_FACTOR
        )
        self.outlier_std_threshold = self.config.get(
            'outlier_std_threshold', AnomalyDetection.OUTLIER_STD_THRESHOLD
        )

        # Moving averages for comparison
        self._moving_averages = defaultdict(lambda: defaultdict(float))
        self._moving_volumes = defaultdict(lambda: defaultdict(float))

    async def detect_anomalies(
        self,
        data_point: Dict[str, Any],
        symbol: str,
        data_type: str
    ) -> List[AnomalyType]:
        """Detect anomalies in data point"""

        anomalies = []

        # Get historical data for comparison
        historical = self._historical_data[symbol][data_type]

        if len(historical) < AnomalyDetection.MIN_HISTORY_POINTS:  # Need minimum history
            # Store data point and return no anomalies
            historical.append(data_point)
            if len(historical) > 100:
                historical.popleft()
            return anomalies

        # Price anomaly detection
        if 'price' in data_point:
            price_anomalies = await self._detect_price_anomalies(
                data_point['price'], historical, symbol
            )
            anomalies.extend(price_anomalies)

        # Volume anomaly detection
        if 'volume' in data_point:
            volume_anomalies = await self._detect_volume_anomalies(
                data_point['volume'], historical, symbol
            )
            anomalies.extend(volume_anomalies)

        # Spread anomaly detection
        if 'bid_price' in data_point and 'ask_price' in data_point:
            spread_anomalies = await self._detect_spread_anomalies(
                data_point, historical
            )
            anomalies.extend(spread_anomalies)

        # Temporal anomaly detection
        temporal_anomalies = await self._detect_temporal_anomalies(
            data_point, historical
        )
        anomalies.extend(temporal_anomalies)

        # Statistical outlier detection
        statistical_anomalies = await self._detect_statistical_outliers(
            data_point, historical
        )
        anomalies.extend(statistical_anomalies)

        # Store data point for future comparisons
        historical.append(data_point)
        if len(historical) > 100:
            historical.popleft()

        return anomalies

    async def _detect_price_anomalies(
        self,
        current_price: float,
        historical: deque,
        symbol: str
    ) -> List[AnomalyType]:
        """Detect price-related anomalies"""

        anomalies = []

        if not historical:
            return anomalies

        # Get recent prices
        recent_prices = [dp.get('price') for dp in list(historical)[-10:]
                        if dp.get('price') is not None]

        if len(recent_prices) < 3:
            return anomalies

        # Calculate average recent price
        avg_price = np.mean(recent_prices)

        # Price spike detection
        if avg_price > 0:
            price_change_pct = abs(current_price - avg_price) / avg_price * 100

            if price_change_pct > self.price_spike_threshold:
                anomalies.append(AnomalyType.PRICE_SPIKE)

        # Update moving average
        self._moving_averages[symbol]['price'] = avg_price

        return anomalies

    async def _detect_volume_anomalies(
        self,
        current_volume: float,
        historical: deque,
        symbol: str
    ) -> List[AnomalyType]:
        """Detect volume-related anomalies"""

        anomalies = []

        if not historical:
            return anomalies

        # Get recent volumes
        recent_volumes = [dp.get('volume') for dp in list(historical)[-20:]
                         if dp.get('volume') is not None and dp.get('volume') > 0]

        if len(recent_volumes) < 5:
            return anomalies

        # Calculate average volume
        avg_volume = np.mean(recent_volumes)

        # Volume spike detection
        if avg_volume > 0:
            volume_factor = current_volume / avg_volume

            if volume_factor > self.volume_spike_threshold:
                anomalies.append(AnomalyType.VOLUME_SPIKE)

        # Update moving average
        self._moving_volumes[symbol]['volume'] = avg_volume

        return anomalies

    async def _detect_spread_anomalies(
        self,
        data_point: Dict[str, Any],
        historical: deque
    ) -> List[AnomalyType]:
        """Detect spread-related anomalies"""

        anomalies = []

        bid_price = data_point.get('bid_price')
        ask_price = data_point.get('ask_price')

        if bid_price is None or ask_price is None:
            return anomalies

        # Check for negative spread
        if bid_price >= ask_price:
            anomalies.append(AnomalyType.SPREAD_ANOMALY)

        # Calculate spread percentage
        mid_price = (bid_price + ask_price) / 2
        if mid_price > 0:
            spread_pct = (ask_price - bid_price) / mid_price * 100

            # Get historical spreads
            historical_spreads = []
            for dp in list(historical)[-20:]:
                if dp.get('bid_price') and dp.get('ask_price'):
                    hist_mid = (dp['bid_price'] + dp['ask_price']) / 2
                    if hist_mid > 0:
                        hist_spread = (dp['ask_price'] - dp['bid_price']) / hist_mid * 100
                        historical_spreads.append(hist_spread)

            if historical_spreads:
                avg_spread = np.mean(historical_spreads)

                # Anomalous spread detection
                if spread_pct > avg_spread * AnomalyDetection.ABNORMAL_SPREAD_MULTIPLIER:
                    anomalies.append(AnomalyType.SPREAD_ANOMALY)

        return anomalies

    async def _detect_temporal_anomalies(
        self,
        data_point: Dict[str, Any],
        historical: deque
    ) -> List[AnomalyType]:
        """Detect temporal anomalies"""

        anomalies = []

        current_time = data_point.get('timestamp', datetime.now())
        if isinstance(current_time, str):
            current_time = datetime.fromisoformat(current_time)

        if not historical:
            return anomalies

        # Check for stale data
        if isinstance(current_time, datetime):
            age_seconds = (datetime.now() - current_time).total_seconds()
            if age_seconds > AnomalyDetection.STALE_DATA_THRESHOLD_SECONDS:
                anomalies.append(AnomalyType.STALE_DATA)

        # Check for sequence gaps
        last_data = historical[-1]
        last_time = last_data.get('timestamp')

        if last_time and isinstance(last_time, datetime) and isinstance(current_time, datetime):
            time_gap = (current_time - last_time).total_seconds()

            # Expected update frequency (1 second for real-time data)
            expected_frequency = ValidationThresholds.DEFAULT_REQUIRED_UPDATE_FREQUENCY_SECONDS

            if time_gap > expected_frequency * AnomalyDetection.SEQUENCE_GAP_MULTIPLIER:
                anomalies.append(AnomalyType.SEQUENCE_GAP)

        return anomalies

    async def _detect_statistical_outliers(
        self,
        data_point: Dict[str, Any],
        historical: deque
    ) -> List[AnomalyType]:
        """Detect statistical outliers"""

        anomalies = []

        if len(historical) < 10:
            return anomalies

        # Check price outliers
        if 'price' in data_point:
            recent_prices = [dp.get('price') for dp in list(historical)[-30:]
                           if dp.get('price') is not None]

            if len(recent_prices) >= 10:
                mean_price = np.mean(recent_prices)
                std_price = np.std(recent_prices)

                if std_price > 0:
                    z_score = abs(data_point['price'] - mean_price) / std_price

                    if z_score > self.outlier_std_threshold:
                        anomalies.append(AnomalyType.OUTLIER)

        return anomalies

class DataValidator(ISystemComponent):
    """
    Advanced data validator with comprehensive quality scoring

    Provides data validation, anomaly detection, quality scoring,
    and integrity checking for market and alternative data.

    Implements ISystemComponent for orchestrator integration (Rule 1).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize data validator"""
        self.config = config or {}
        self._lock = threading.Lock()

        # ISystemComponent state (Rule 1)
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)

        # Validation components
        self.anomaly_detector = AnomalyDetector(self.config.get('anomaly_detection', {}))

        # Validation configurations
        self._validation_configs = {}
        self._default_config = self._create_default_config()

        # Validation results storage
        self._validation_results = deque(maxlen=10000)
        self._quality_metrics = deque(maxlen=5000)
        self._validation_by_symbol = defaultdict(lambda: deque(maxlen=1000))

        # Performance tracking
        self._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'warnings_issued': 0,
            'anomalies_detected': 0,
            'average_validation_time_ms': 0.0,
            'quality_score_average': 0.0
        }

        # Cross-validation data
        self._cross_validation_data = defaultdict(lambda: defaultdict(deque))

        # Background monitoring
        self._monitoring_tasks = []

        # Initialize default validation rules
        self._initialize_default_validations()

        # Note: Background monitoring will be started in start() method (ISystemComponent lifecycle)
        self.logger.info("✅ DataValidator created (call initialize() and start() for full activation)")

    def _create_default_config(self) -> ValidationConfiguration:
        """Create default validation configuration"""
        return ValidationConfiguration(
            data_type="default",
            max_price_change_pct=ValidationThresholds.DEFAULT_MAX_PRICE_CHANGE_PERCENT,
            max_spread_pct=ValidationThresholds.DEFAULT_MAX_SPREAD_PERCENT,
            max_spread_bps=ValidationThresholds.DEFAULT_MAX_SPREAD_BPS,
            max_volume_spike_factor=ValidationThresholds.DEFAULT_MAX_VOLUME_SPIKE_FACTOR,
            max_data_age_seconds=ValidationThresholds.DEFAULT_MAX_DATA_AGE_SECONDS,
            required_update_frequency_seconds=ValidationThresholds.DEFAULT_REQUIRED_UPDATE_FREQUENCY_SECONDS,
            outlier_threshold_std=AnomalyDetection.OUTLIER_STD_THRESHOLD,
            moving_average_window=20,
            required_fields=['timestamp'],
            min_completeness_pct=ValidationThresholds.DEFAULT_MIN_COMPLETENESS_PERCENT,
            enable_cross_validation=True,
            max_cross_validation_diff_pct=ValidationThresholds.DEFAULT_MAX_CROSS_VALIDATION_DIFF_PERCENT
        )

    def _initialize_default_validations(self) -> None:
        """Initialize default validation configurations"""

        # Quote data validation
        quote_config = ValidationConfiguration(
            data_type="quote",
            min_price=0.01,
            max_price=10000.0,
            max_price_change_pct=15.0,
            max_spread_pct=3.0,
            max_spread_bps=300.0,
            required_fields=['symbol', 'bid_price', 'ask_price', 'timestamp'],
            min_completeness_pct=100.0
        )

        # Trade data validation
        trade_config = ValidationConfiguration(
            data_type="trade",
            min_price=0.01,
            max_price=10000.0,
            max_price_change_pct=20.0,
            min_volume=1,
            max_volume_spike_factor=15.0,
            required_fields=['symbol', 'price', 'volume', 'timestamp'],
            min_completeness_pct=100.0
        )

        # Depth data validation
        depth_config = ValidationConfiguration(
            data_type="depth",
            min_price=0.01,
            max_price=10000.0,
            max_spread_pct=5.0,
            required_fields=['symbol', 'bids', 'asks', 'timestamp'],
            min_completeness_pct=90.0
        )

        self._validation_configs['quote'] = quote_config
        self._validation_configs['trade'] = trade_config
        self._validation_configs['depth'] = depth_config

    async def validate_data(
        self,
        data: Dict[str, Any],
        data_type: str,
        symbol: Optional[str] = None,
        source: Optional[str] = None
    ) -> Tuple[ValidationResult, DataQualityMetrics]:
        """
        Validate data and calculate quality metrics

        Args:
            data: Data to validate
            data_type: Type of data
            symbol: Symbol associated with data
            source: Data source

        Returns:
            Tuple of validation result and quality metrics
        """

        start_time = time.time()
        validation_id = f"val_{int(time.time() * 1000)}"
        data_id = data.get('data_id', f"data_{int(time.time() * 1000)}")

        try:
            # Get validation configuration
            config = self._validation_configs.get(data_type, self._default_config)

            # Perform validation checks
            validation_results = await self._perform_validation_checks(
                data, config, symbol, source
            )

            # Calculate overall validation score
            overall_score = self._calculate_validation_score(validation_results)

            # Detect anomalies
            anomalies = await self.anomaly_detector.detect_anomalies(
                data, symbol or "UNKNOWN", data_type
            )

            # Create validation result
            validation_time = (time.time() - start_time) * 1000

            validation_result = ValidationResult(
                validation_id=validation_id,
                data_id=data_id,
                rule=ValidationRule.COMPLETENESS_CHECK,  # Main rule for summary
                status=ValidationStatus.PASSED if overall_score >= 0.8 else
                       ValidationStatus.WARNING if overall_score >= 0.6 else
                       ValidationStatus.FAILED,
                score=overall_score,
                message=self._generate_validation_message(validation_results, anomalies),
                details=validation_results,
                anomalies=anomalies,
                validation_time_ms=validation_time
            )

            # Calculate quality metrics
            quality_metrics = await self._calculate_quality_metrics(
                data, data_type, symbol, validation_results, anomalies
            )

            # Store results
            with self._lock:
                self._validation_results.append(validation_result)
                self._quality_metrics.append(quality_metrics)

                if symbol:
                    self._validation_by_symbol[symbol].append(validation_result)

                # Update statistics
                self._update_validation_stats(validation_result, quality_metrics)

            # Store for cross-validation
            if source:
                self._store_cross_validation_data(data, symbol, source)

            logger.debug(f"Validation completed: {validation_id} (score: {overall_score:.3f})")

            return validation_result, quality_metrics

        except Exception as e:
            logger.error(f"Error during validation: {e}")

            # Return failed validation
            validation_result = ValidationResult(
                validation_id=validation_id,
                data_id=data_id,
                rule=ValidationRule.COMPLETENESS_CHECK,
                status=ValidationStatus.FAILED,
                score=0.0,
                message=f"Validation error: {e}",
                details={'error': str(e)},
                validation_time_ms=(time.time() - start_time) * 1000
            )

            quality_metrics = DataQualityMetrics(
                data_id=data_id,
                symbol=symbol or "UNKNOWN",
                data_type=data_type,
                overall_score=0.0,
                accuracy_score=0.0,
                completeness_score=0.0,
                consistency_score=0.0,
                timeliness_score=0.0,
                validity_score=0.0,
                missing_data_percentage=100.0,
                duplicate_data_percentage=0.0,
                anomaly_count=0,
                validation_failures=1
            )

            return validation_result, quality_metrics

    async def _perform_validation_checks(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration,
        symbol: Optional[str],
        source: Optional[str]
    ) -> Dict[str, Any]:
        """Perform comprehensive validation checks"""

        results = {}

        # Completeness check
        results['completeness'] = await self._check_completeness(data, config)

        # Price range check
        if 'price' in data or 'bid_price' in data or 'ask_price' in data:
            results['price_range'] = await self._check_price_range(data, config)

        # Spread check
        if 'bid_price' in data and 'ask_price' in data:
            results['spread'] = await self._check_spread(data, config)

        # Volume check
        if 'volume' in data:
            results['volume'] = await self._check_volume(data, config)

        # Timestamp check
        results['timestamp'] = await self._check_timestamp(data, config)

        # Consistency check
        results['consistency'] = await self._check_consistency(data, config)

        # Cross-validation check
        if config.enable_cross_validation and source and symbol:
            results['cross_validation'] = await self._check_cross_validation(
                data, symbol, source, config
            )

        return results

    async def _check_completeness(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check data completeness"""

        missing_fields = []
        present_fields = []

        for field in config.required_fields:
            if field in data and data[field] is not None:
                present_fields.append(field)
            else:
                missing_fields.append(field)

        completeness_pct = (len(present_fields) / len(config.required_fields)) * 100 if config.required_fields else 100

        return {
            'completeness_percentage': completeness_pct,
            'missing_fields': missing_fields,
            'present_fields': present_fields,
            'passed': completeness_pct >= config.min_completeness_pct
        }

    async def _check_price_range(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check price range validity"""

        issues = []
        prices_checked = []

        # Check various price fields
        price_fields = ['price', 'bid_price', 'ask_price', 'open_price', 'high_price', 'low_price', 'close_price']

        for field in price_fields:
            if field in data and data[field] is not None:
                price = data[field]
                prices_checked.append(field)

                # Check minimum price
                if config.min_price is not None and price < config.min_price:
                    issues.append(f"{field} {price} below minimum {config.min_price}")

                # Check maximum price
                if config.max_price is not None and price > config.max_price:
                    issues.append(f"{field} {price} above maximum {config.max_price}")

                # Check for zero or negative prices
                if price <= 0:
                    issues.append(f"{field} {price} is non-positive")

        return {
            'prices_checked': prices_checked,
            'issues': issues,
            'passed': len(issues) == 0
        }

    async def _check_spread(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check bid-ask spread validity"""

        bid_price = data.get('bid_price')
        ask_price = data.get('ask_price')
        issues = []

        if bid_price is None or ask_price is None:
            return {'issues': ['Missing bid or ask price'], 'passed': False}

        # Check for negative spread
        if bid_price >= ask_price:
            issues.append(f"Negative spread: bid {bid_price} >= ask {ask_price}")

        # Check spread percentage
        if ask_price > 0:
            spread_pct = ((ask_price - bid_price) / ask_price) * 100

            if spread_pct > config.max_spread_pct:
                issues.append(f"Spread {spread_pct:.2f}% exceeds maximum {config.max_spread_pct}%")

            # Check spread in basis points
            mid_price = (bid_price + ask_price) / 2
            spread_bps = ((ask_price - bid_price) / mid_price) * 10000

            if spread_bps > config.max_spread_bps:
                issues.append(f"Spread {spread_bps:.0f} bps exceeds maximum {config.max_spread_bps} bps")

            return {
                'spread_percentage': spread_pct,
                'spread_bps': spread_bps,
                'issues': issues,
                'passed': len(issues) == 0
            }

        return {'issues': ['Invalid ask price'], 'passed': False}

    async def _check_volume(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check volume validity"""

        volume = data.get('volume')
        issues = []

        if volume is None:
            return {'issues': ['Missing volume'], 'passed': False}

        # Check minimum volume
        if volume < config.min_volume:
            issues.append(f"Volume {volume} below minimum {config.min_volume}")

        # Check for negative volume
        if volume < 0:
            issues.append(f"Negative volume: {volume}")

        return {
            'volume': volume,
            'issues': issues,
            'passed': len(issues) == 0
        }

    async def _check_timestamp(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check timestamp validity"""

        timestamp = data.get('timestamp')
        issues = []

        if timestamp is None:
            return {'issues': ['Missing timestamp'], 'passed': False}

        # Convert string timestamp if necessary
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                issues.append(f"Invalid timestamp format: {timestamp}")
                return {'issues': issues, 'passed': False}

        if isinstance(timestamp, datetime):
            # Check data age
            age_seconds = (datetime.now() - timestamp).total_seconds()

            if age_seconds > config.max_data_age_seconds:
                issues.append(f"Data too old: {age_seconds:.1f}s > {config.max_data_age_seconds}s")

            # Check for future timestamp
            if age_seconds < -5:  # Allow 5 second clock skew
                issues.append(f"Future timestamp: {timestamp}")

            return {
                'timestamp': timestamp.isoformat(),
                'age_seconds': age_seconds,
                'issues': issues,
                'passed': len(issues) == 0
            }

        return {'issues': ['Invalid timestamp type'], 'passed': False}

    async def _check_consistency(
        self,
        data: Dict[str, Any],
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check internal data consistency"""

        issues = []

        # Check OHLC consistency
        ohlc_fields = ['open_price', 'high_price', 'low_price', 'close_price']
        ohlc_values = {field: data.get(field) for field in ohlc_fields if field in data}

        if len(ohlc_values) >= 3:  # Need at least 3 values for consistency check
            values = list(ohlc_values.values())
            min_val = min(v for v in values if v is not None)
            max_val = max(v for v in values if v is not None)

            # High should be >= all others
            if 'high_price' in ohlc_values and ohlc_values['high_price'] < max_val:
                issues.append("High price is not the maximum OHLC value")

            # Low should be <= all others
            if 'low_price' in ohlc_values and ohlc_values['low_price'] > min_val:
                issues.append("Low price is not the minimum OHLC value")

        # Check bid <= price <= ask consistency
        bid_price = data.get('bid_price')
        ask_price = data.get('ask_price')
        price = data.get('price')

        if bid_price and ask_price and price:
            if not (bid_price <= price <= ask_price):
                issues.append(f"Price {price} not between bid {bid_price} and ask {ask_price}")

        return {
            'checks_performed': ['ohlc_consistency', 'bid_ask_price_consistency'],
            'issues': issues,
            'passed': len(issues) == 0
        }

    async def _check_cross_validation(
        self,
        data: Dict[str, Any],
        symbol: str,
        source: str,
        config: ValidationConfiguration
    ) -> Dict[str, Any]:
        """Check data against other sources for cross-validation"""

        issues = []
        comparisons = []

        # Get data from other sources
        other_sources_data = []
        for other_source, source_data in self._cross_validation_data[symbol].items():
            if other_source != source and source_data:
                # Get most recent data point
                recent_data = source_data[-1] if source_data else None
                if recent_data:
                    other_sources_data.append((other_source, recent_data))

        # Compare prices if available
        current_price = data.get('price') or data.get('bid_price') or data.get('ask_price')

        if current_price and other_sources_data:
            for other_source, other_data in other_sources_data:
                other_price = (other_data.get('price') or
                             other_data.get('bid_price') or
                             other_data.get('ask_price'))

                if other_price:
                    price_diff_pct = abs(current_price - other_price) / other_price * 100

                    comparison = {
                        'source': other_source,
                        'price_diff_pct': price_diff_pct,
                        'current_price': current_price,
                        'other_price': other_price
                    }
                    comparisons.append(comparison)

                    if price_diff_pct > config.max_cross_validation_diff_pct:
                        issues.append(f"Price differs {price_diff_pct:.2f}% from {other_source}")

        return {
            'comparisons': comparisons,
            'issues': issues,
            'passed': len(issues) == 0
        }

    def _calculate_validation_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall validation score"""

        scores = []
        weights = {
            'completeness': ValidationThresholds.COMPLETENESS_WEIGHT,
            'price_range': ValidationThresholds.PRICE_RANGE_WEIGHT,
            'spread': ValidationThresholds.SPREAD_WEIGHT,
            'volume': ValidationThresholds.VOLUME_WEIGHT,
            'timestamp': ValidationThresholds.TIMESTAMP_WEIGHT,
            'consistency': ValidationThresholds.CONSISTENCY_WEIGHT
        }

        for check, result in validation_results.items():
            weight = weights.get(check, ValidationThresholds.CONSISTENCY_WEIGHT)
            passed = result.get('passed', False)
            score = 1.0 if passed else 0.0

            # Partial credit for some checks
            if check == 'completeness':
                score = result.get('completeness_percentage', 0) / 100

            scores.append(score * weight)

        return sum(scores)

    def _generate_validation_message(
        self,
        validation_results: Dict[str, Any],
        anomalies: List[AnomalyType]
    ) -> str:
        """Generate validation summary message"""

        failed_checks = []

        for check, result in validation_results.items():
            if not result.get('passed', True):
                issues = result.get('issues', [])
                if issues:
                    failed_checks.append(f"{check}: {', '.join(issues[:2])}")

        message_parts = []

        if failed_checks:
            message_parts.append(f"Failed checks: {'; '.join(failed_checks[:3])}")

        if anomalies:
            anomaly_names = [anomaly.value for anomaly in anomalies[:3]]
            message_parts.append(f"Anomalies: {', '.join(anomaly_names)}")

        if not message_parts:
            message_parts.append("All validation checks passed")

        return ". ".join(message_parts)

    async def _calculate_quality_metrics(
        self,
        data: Dict[str, Any],
        data_type: str,
        symbol: Optional[str],
        validation_results: Dict[str, Any],
        anomalies: List[AnomalyType]
    ) -> DataQualityMetrics:
        """Calculate comprehensive quality metrics"""

        data_id = data.get('data_id', f"data_{int(time.time() * 1000)}")

        # Component scores
        completeness_result = validation_results.get('completeness', {})
        completeness_score = completeness_result.get('completeness_percentage', 0) / 100

        accuracy_score = 1.0
        if validation_results.get('price_range', {}).get('issues'):
            accuracy_score -= 0.3
        if validation_results.get('spread', {}).get('issues'):
            accuracy_score -= 0.2

        consistency_score = 1.0 if validation_results.get('consistency', {}).get('passed', True) else 0.5

        timeliness_score = 1.0
        timestamp_result = validation_results.get('timestamp', {})
        if timestamp_result.get('age_seconds', 0) > 30:
            timeliness_score = max(0.1, 1.0 - timestamp_result['age_seconds'] / 300)

        validity_score = 1.0 - (len(anomalies) * 0.1)  # Reduce score for each anomaly
        validity_score = max(0.0, validity_score)

        # Overall score
        overall_score = (
            completeness_score * 0.25 +
            accuracy_score * 0.25 +
            consistency_score * 0.2 +
            timeliness_score * 0.15 +
            validity_score * 0.15
        )

        # Calculate statistical metrics if numeric data available
        numeric_fields = ['price', 'bid_price', 'ask_price', 'volume', 'open_price', 'high_price', 'low_price', 'close_price']
        numeric_values = [data[field] for field in numeric_fields if field in data and isinstance(data[field], (int, float))]

        mean_value = np.mean(numeric_values) if numeric_values else None
        median_value = np.median(numeric_values) if numeric_values else None
        std_deviation = np.std(numeric_values) if len(numeric_values) > 1 else None
        min_value = np.min(numeric_values) if numeric_values else None
        max_value = np.max(numeric_values) if numeric_values else None

        # Calculate data age
        timestamp = data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except:
                timestamp = datetime.now()

        data_age_seconds = (datetime.now() - timestamp).total_seconds() if isinstance(timestamp, datetime) else 0

        return DataQualityMetrics(
            data_id=data_id,
            symbol=symbol or "UNKNOWN",
            data_type=data_type,
            overall_score=overall_score,
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            timeliness_score=timeliness_score,
            validity_score=validity_score,
            missing_data_percentage=100 - completeness_score * 100,
            duplicate_data_percentage=0.0,  # Would need duplicate detection logic
            anomaly_count=len(anomalies),
            validation_failures=sum(1 for result in validation_results.values() if not result.get('passed', True)),
            mean_value=mean_value,
            median_value=median_value,
            std_deviation=std_deviation,
            min_value=min_value,
            max_value=max_value,
            data_age_seconds=data_age_seconds
        )

    def _store_cross_validation_data(
        self,
        data: Dict[str, Any],
        symbol: Optional[str],
        source: str
    ) -> None:
        """Store data for cross-validation purposes"""

        if not symbol:
            return

        # Store data with timestamp
        storage_data = data.copy()
        storage_data['validation_timestamp'] = datetime.now()

        with self._lock:
            source_data = self._cross_validation_data[symbol][source]
            source_data.append(storage_data)

            # Keep only recent data
            if len(source_data) > DataRetention.CROSS_VALIDATION_BUFFER_SIZE:
                source_data.popleft()

    def _update_validation_stats(
        self,
        validation_result: ValidationResult,
        quality_metrics: DataQualityMetrics
    ) -> None:
        """Update validation statistics"""

        stats = self._validation_stats

        # Update counters
        stats['total_validations'] += 1

        if validation_result.status == ValidationStatus.PASSED:
            stats['passed_validations'] += 1
        elif validation_result.status == ValidationStatus.FAILED:
            stats['failed_validations'] += 1
        elif validation_result.status == ValidationStatus.WARNING:
            stats['warnings_issued'] += 1

        stats['anomalies_detected'] += len(validation_result.anomalies)

        # Update averages
        total = stats['total_validations']

        current_avg_time = stats['average_validation_time_ms']
        new_time = validation_result.validation_time_ms
        stats['average_validation_time_ms'] = (
            (current_avg_time * (total - 1) + new_time) / total
        )

        current_avg_quality = stats['quality_score_average']
        new_quality = quality_metrics.overall_score
        stats['quality_score_average'] = (
            (current_avg_quality * (total - 1) + new_quality) / total
        )

    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks"""

        self._monitoring_tasks = [
            asyncio.create_task(self._monitor_validation_performance()),
            asyncio.create_task(self._cleanup_old_results())
        ]

        logger.info("Started data validation monitoring")

    async def _monitor_validation_performance(self) -> None:
        """Monitor validation performance"""

        while True:
            try:
                await asyncio.sleep(DataIntervals.VALIDATION_MONITORING_SECONDS)

                with self._lock:
                    stats = self._validation_stats.copy()

                # Check validation performance
                if stats['total_validations'] > 100:
                    failure_rate = stats['failed_validations'] / stats['total_validations']

                    if failure_rate > ValidationThresholds.HIGH_FAILURE_RATE_THRESHOLD:
                        logger.warning(f"High validation failure rate: {failure_rate:.1%}")

                    avg_quality = stats['quality_score_average']
                    if avg_quality < ValidationThresholds.MIN_QUALITY_SCORE:
                        logger.warning(f"Low average data quality: {avg_quality:.3f}")

            except Exception as e:
                logger.error(f"Error in validation monitoring: {e}")
                await asyncio.sleep(DataIntervals.VALIDATION_MONITORING_SECONDS)

    async def _cleanup_old_results(self) -> None:
        """Cleanup old validation results"""

        while True:
            try:
                await asyncio.sleep(DataIntervals.VALIDATION_CLEANUP_SECONDS)

                cutoff_time = datetime.now() - timedelta(days=DataRetention.VALIDATION_RETENTION_DAYS)

                with self._lock:
                    # Cleanup validation results
                    while (self._validation_results and
                           self._validation_results[0].timestamp < cutoff_time):
                        self._validation_results.popleft()

                    # Cleanup quality metrics
                    while (self._quality_metrics and
                           self._quality_metrics[0].timestamp < cutoff_time):
                        self._quality_metrics.popleft()

                    # Cleanup cross-validation data
                    for symbol_data in self._cross_validation_data.values():
                        for source_data in symbol_data.values():
                            while (source_data and
                                   source_data[0].get('validation_timestamp', datetime.now()) < cutoff_time):
                                source_data.popleft()

                logger.info("Completed validation data cleanup")

            except Exception as e:
                logger.error(f"Error in validation cleanup: {e}")
                await asyncio.sleep(3600)

    def register_validation_config(
        self,
        data_type: str,
        config: ValidationConfiguration
    ) -> None:
        """Register validation configuration for data type"""

        with self._lock:
            self._validation_configs[data_type] = config

        logger.info(f"Registered validation config for {data_type}")

    def get_validation_results(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> List[ValidationResult]:
        """Get validation results"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        if symbol:
            with self._lock:
                results = [
                    result for result in self._validation_by_symbol.get(symbol, [])
                    if result.timestamp >= cutoff_time
                ]
        else:
            with self._lock:
                results = [
                    result for result in self._validation_results
                    if result.timestamp >= cutoff_time
                ]

        return results

    def get_quality_metrics(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> List[DataQualityMetrics]:
        """Get quality metrics"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            all_metrics = list(self._quality_metrics)

        # Filter by time and symbol
        filtered_metrics = [
            metrics for metrics in all_metrics
            if (metrics.timestamp >= cutoff_time and
                (not symbol or metrics.symbol == symbol))
        ]

        return filtered_metrics

    def get_validation_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get validation summary"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            recent_results = [
                result for result in self._validation_results
                if result.timestamp >= cutoff_time
            ]

            recent_metrics = [
                metrics for metrics in self._quality_metrics
                if metrics.timestamp >= cutoff_time
            ]

        if not recent_results:
            return {'message': 'No recent validation results available'}

        # Calculate summary statistics
        passed_count = sum(1 for r in recent_results if r.status == ValidationStatus.PASSED)
        failed_count = sum(1 for r in recent_results if r.status == ValidationStatus.FAILED)
        warning_count = sum(1 for r in recent_results if r.status == ValidationStatus.WARNING)

        total_anomalies = sum(len(r.anomalies) for r in recent_results)

        quality_scores = [m.overall_score for m in recent_metrics]
        avg_quality = np.mean(quality_scores) if quality_scores else 0.0

        return {
            'period_hours': hours,
            'total_validations': len(recent_results),
            'passed_validations': passed_count,
            'failed_validations': failed_count,
            'warning_validations': warning_count,
            'success_rate': passed_count / len(recent_results) if recent_results else 0.0,
            'total_anomalies': total_anomalies,
            'average_quality_score': avg_quality,
            'validation_stats': self._validation_stats.copy()
        }

    async def cleanup(self) -> None:
        """Cleanup data validator resources"""

        # Cancel monitoring tasks
        for task in self._monitoring_tasks:
            task.cancel()

        # Clear data
        with self._lock:
            self._validation_results.clear()
            self._quality_metrics.clear()
            self._validation_by_symbol.clear()
            self._cross_validation_data.clear()

        self.logger.info("DataValidator cleanup completed")

    # ========================================================================
    # ISystemComponent Lifecycle Methods (Rule 1)
    # ========================================================================

    async def initialize(self) -> bool:
        """Initialize data validator"""
        try:
            self.logger.info("Initializing DataValidator...")
            self.is_initialized = True
            self.logger.info("✅ DataValidator initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ DataValidator initialization failed: {e}")
            return False

    async def start(self) -> bool:
        """Start data validator operations"""
        try:
            if not self.is_initialized:
                self.logger.error("Cannot start - not initialized. Call initialize() first.")
                return False

            self.logger.info("Starting DataValidator...")

            # Start monitoring if configured
            if self.config.get('enable_monitoring', True):
                await self._start_monitoring()

            self.is_operational = True
            self.logger.info("✅ DataValidator started successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ DataValidator start failed: {e}")
            return False

    async def stop(self) -> bool:
        """Stop data validator operations"""
        try:
            self.logger.info("Stopping DataValidator...")
            await self.cleanup()
            self.is_operational = False
            self.logger.info("✅ DataValidator stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ DataValidator stop failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on data validator"""
        stats = self._validation_stats.copy()

        # Calculate health metrics
        success_rate = 0.0
        if stats['total_validations'] > 0:
            success_rate = stats['passed_validations'] / stats['total_validations']

        # Healthy if operational and initialized, OR if we have good validation rate
        is_healthy = (
            self.is_operational and
            self.is_initialized and
            (stats['total_validations'] == 0 or success_rate >= 0.9)  # Healthy if no validations yet OR 90%+ success
        )

        return {
            'healthy': is_healthy,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'DataValidator',
            'total_validations': stats['total_validations'],
            'success_rate': success_rate,
            'quality_score_average': stats['quality_score_average'],
            'anomalies_detected': stats['anomalies_detected']
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status of data validator"""
        return {
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'DataValidator',
            'validation_stats': dict(self._validation_stats)
        }