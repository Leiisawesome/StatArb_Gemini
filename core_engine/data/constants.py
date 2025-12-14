#!/usr/bin/env python3
"""
Data Module Constants

Centralized constants for the data brick to eliminate magic numbers
and improve code maintainability.
"""

class DataIntervals:
    """Time intervals for background tasks and polling (in seconds)"""

    # Monitoring intervals
    PERFORMANCE_MONITORING_SECONDS = 60
    HEALTH_CHECK_SECONDS = 30
    RESOURCE_MONITORING_SECONDS = 300
    VALIDATION_MONITORING_SECONDS = 300

    # Cleanup intervals
    DATA_CLEANUP_SECONDS = 3600  # 1 hour
    VALIDATION_CLEANUP_SECONDS = 3600

    # Scraping intervals
    WEB_SCRAPING_SECONDS = 300  # 5 minutes

    # Polling intervals
    HTTP_POLLING_SECONDS = 1.0
    REALTIME_UPDATE_SECONDS = 0.1  # 100ms for real-time data

    # WebSocket connection
    WS_CONNECTION_WAIT_SECONDS = 1
    WS_RECONNECT_WAIT_SECONDS = 5

class DataRetention:
    """Data retention periods"""

    # Alternative data
    ALT_DATA_RETENTION_DAYS = 7

    # Market data
    MARKET_DATA_RETENTION_HOURS = 24

    # Validation results
    VALIDATION_RETENTION_DAYS = 1

    # Cross-validation data buffer size
    CROSS_VALIDATION_BUFFER_SIZE = 100

    # Real-time data buffer
    REALTIME_BUFFER_SIZE = 1000

class CircuitBreaker:
    """Circuit breaker configuration"""

    FAILURE_THRESHOLD = 5
    RESET_TIMEOUT_SECONDS = 60

class AnomalyDetection:
    """Anomaly detection thresholds"""

    # Minimum data points needed for anomaly detection
    MIN_HISTORY_POINTS = 5
    MIN_HISTORY_FOR_STATS = 10

    # Price anomaly thresholds
    PRICE_SPIKE_THRESHOLD_PERCENT = 5.0

    # Volume anomaly thresholds
    VOLUME_SPIKE_THRESHOLD_FACTOR = 10.0

    # Statistical thresholds
    OUTLIER_STD_THRESHOLD = 3.0

    # Temporal thresholds
    STALE_DATA_THRESHOLD_SECONDS = 60
    SEQUENCE_GAP_MULTIPLIER = 10  # Gap > expected_frequency * this = anomaly

    # Spread anomaly thresholds
    ABNORMAL_SPREAD_MULTIPLIER = 3.0  # 3x normal spread = anomaly

class ValidationThresholds:
    """Data validation thresholds"""

    # Quality thresholds
    MIN_QUALITY_SCORE = 0.8
    MIN_VALIDATION_SUCCESS_RATE = 0.9
    HIGH_FAILURE_RATE_THRESHOLD = 0.1

    # Default validation config values
    DEFAULT_MAX_PRICE_CHANGE_PERCENT = 20.0
    DEFAULT_MAX_SPREAD_PERCENT = 5.0
    DEFAULT_MAX_SPREAD_BPS = 500.0
    DEFAULT_MAX_VOLUME_SPIKE_FACTOR = 10.0
    DEFAULT_MAX_DATA_AGE_SECONDS = 30.0
    DEFAULT_REQUIRED_UPDATE_FREQUENCY_SECONDS = 1.0
    DEFAULT_MIN_COMPLETENESS_PERCENT = 95.0
    DEFAULT_MAX_CROSS_VALIDATION_DIFF_PERCENT = 2.0

    # Quality score weights
    COMPLETENESS_WEIGHT = 0.3
    PRICE_RANGE_WEIGHT = 0.2
    SPREAD_WEIGHT = 0.15
    VOLUME_WEIGHT = 0.1
    TIMESTAMP_WEIGHT = 0.15
    CONSISTENCY_WEIGHT = 0.1

class MarketDataConfig:
    """Market data configuration"""

    # Spread thresholds
    MAX_SPREAD_PERCENT_WARNING = 5.0

    # Quality score adjustments
    QUALITY_PENALTY_BAD_SPREAD = 0.3
    QUALITY_PENALTY_WIDE_SPREAD = 0.7

    # Latency thresholds
    DEFAULT_MAX_LATENCY_MS = 10.0

    # Data age thresholds
    STALE_DATA_SECONDS = 1.0
    STALE_DATA_DECAY_SECONDS = 10.0

    # Heartbeat timeout
    HEARTBEAT_TIMEOUT_SECONDS = 60
    HIGH_ERROR_COUNT_THRESHOLD = 10

class FeedConfig:
    """Feed management configuration"""

    # Health thresholds
    MIN_ACTIVE_FEED_RATIO = 0.7  # At least 70% feeds should be active

    # Top feeds for subscription routing
    MAX_FEEDS_PER_SUBSCRIPTION = 3

class AlternativeDataConfig:
    """Alternative data configuration"""

    # Provider credibility scores
    CREDIBILITY_BLOOMBERG = 0.95
    CREDIBILITY_NEWS_API = 0.8
    CREDIBILITY_TWITTER = 0.6
    CREDIBILITY_REDDIT = 0.4
    CREDIBILITY_CUSTOM_SCRAPER = 0.7

    # Content quality thresholds
    SUBSTANTIAL_CONTENT_LENGTH = 500

    # Credibility bonuses
    AUTHOR_CREDIBILITY_BONUS = 0.1
    CONTENT_LENGTH_BONUS = 0.1
    TRUSTED_DOMAIN_BONUS = 0.15

    # Trusted domains for credibility scoring
    TRUSTED_DOMAINS = [
        'bloomberg.com',
        'reuters.com',
        'wsj.com',
        'ft.com'
    ]

    # Impact decay
    IMPACT_DECAY_HOURS = 24

    # Error rate threshold for health check
    MAX_ERROR_RATE = 0.1  # 10%
