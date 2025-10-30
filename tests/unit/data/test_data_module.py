"""
Unit tests for data component.
Tests data manager, market data structures, alternative data, and validation components.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

# Import data component classes
from core_engine.data.manager import (
    ClickHouseDataConfig,
    EnhancedMarketData,
    ClickHouseDataManager
)

from core_engine.data.alternative_data_handler import (
    AlternativeDataPoint,
    AlternativeDataType,
    DataProvider
)

from core_engine.data.sources.market_data import (
    MarketDataPoint,
    DataSource,
    DataType,
    DataQuality
)

from core_engine.data.validation.validator import (
    ValidationResult,
    DataQualityMetrics,
    ValidationStatus,
    ValidationRule,
    AnomalyType
)


class TestClickHouseDataConfig:
    """Test suite for ClickHouseDataConfig class."""

    def test_initialization_with_defaults(self):
        """Test ClickHouseDataConfig initialization with defaults."""
        config = ClickHouseDataConfig()

        assert config.symbols == ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ']
        assert config.interval == "1min"
        assert config.clickhouse_host == "localhost"
        assert config.clickhouse_port == 8123
        assert config.clickhouse_database == "polygon_data"
        assert config.enable_caching is True
        assert config.cache_ttl == 300


class TestEnhancedMarketData:
    """Test suite for EnhancedMarketData class."""

    def test_initialization(self):
        """Test EnhancedMarketData initialization."""
        timestamp = datetime.now()
        data = EnhancedMarketData(
            symbol="AAPL",
            timestamp=timestamp,
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=1000000,
            transactions=500
        )

        assert data.symbol == "AAPL"
        assert data.timestamp == timestamp
        assert data.open == 150.0
        assert data.high == 155.0
        assert data.low == 149.0
        assert data.close == 154.0
        assert data.volume == 1000000
        assert data.transactions == 500
        assert data.source == "clickhouse"


@pytest.fixture
def data_manager():
    """Fixture for ClickHouseDataManager instance."""
    config = ClickHouseDataConfig()
    with patch('core_engine.data.manager.ClickHouseDataManager._test_connection', return_value=True):
        return ClickHouseDataManager(config)


class TestClickHouseDataManager:
    """Test suite for ClickHouseDataManager class."""

    def test_initialization(self, data_manager):
        """Test ClickHouseDataManager initialization."""
        assert isinstance(data_manager.enhanced_config, ClickHouseDataConfig)
        assert data_manager.subscribers == []
        assert data_manager.clickhouse_url == "http://localhost:8123"

    @patch('requests.post')
    def test_test_connection_success(self, mock_post, data_manager):
        """Test successful ClickHouse connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "1"
        mock_post.return_value = mock_response

        result = data_manager._test_connection()

        assert result is True
        mock_post.assert_called_once()


class TestAlternativeDataPoint:
    """Test suite for AlternativeDataPoint class."""

    def test_initialization(self):
        """Test AlternativeDataPoint initialization."""
        data = AlternativeDataPoint(
            data_id="alt_123",
            symbol="AAPL",
            data_type=AlternativeDataType.SENTIMENT,
            provider=DataProvider.TWITTER,
            raw_content="Great earnings report from Apple!",
            structured_data={"sentiment": 0.75, "confidence": 0.85}
        )

        assert data.data_id == "alt_123"
        assert data.symbol == "AAPL"
        assert data.data_type == AlternativeDataType.SENTIMENT
        assert data.provider == DataProvider.TWITTER
        assert data.raw_content == "Great earnings report from Apple!"
        assert data.structured_data == {"sentiment": 0.75, "confidence": 0.85}


class TestMarketDataPoint:
    """Test suite for MarketDataPoint class."""

    def test_initialization_quote_data(self):
        """Test MarketDataPoint initialization with quote data."""
        timestamp = datetime.now()
        data = MarketDataPoint(
            symbol="AAPL",
            timestamp=timestamp,
            data_type=DataType.QUOTE,
            source=DataSource.EXCHANGE,
            quality=DataQuality.REAL_TIME,
            bid_price=149.50,
            ask_price=149.55,
            bid_size=100,
            ask_size=200
        )

        assert data.symbol == "AAPL"
        assert data.timestamp == timestamp
        assert data.data_type == DataType.QUOTE
        assert data.source == DataSource.EXCHANGE
        assert data.quality == DataQuality.REAL_TIME
        assert data.bid_price == 149.50
        assert data.ask_price == 149.55
        assert data.bid_size == 100
        assert data.ask_size == 200


class TestValidationResult:
    """Test suite for ValidationResult class."""

    def test_initialization(self):
        """Test ValidationResult initialization."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        result = ValidationResult(
            validation_id="val_123",
            data_id="data_456",
            rule=ValidationRule.PRICE_RANGE,
            status=ValidationStatus.PASSED,
            score=0.95,
            message="Validation passed",
            details={"min_price": 100, "max_price": 200},
            anomalies=[AnomalyType.PRICE_SPIKE],
            validation_time_ms=150.5,
            timestamp=timestamp
        )

        assert result.validation_id == "val_123"
        assert result.data_id == "data_456"
        assert result.rule == ValidationRule.PRICE_RANGE
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.95
        assert result.message == "Validation passed"
        assert result.details == {"min_price": 100, "max_price": 200}
        assert result.anomalies == [AnomalyType.PRICE_SPIKE]
        assert result.validation_time_ms == 150.5
        assert result.timestamp == timestamp

    def test_initialization_with_defaults(self):
        """Test ValidationResult initialization with defaults."""
        result = ValidationResult(
            validation_id="val_123",
            data_id="data_456",
            rule=ValidationRule.VOLUME_CHECK,
            status=ValidationStatus.FAILED,
            score=0.3,
            message="Volume too low",
            details={}
        )

        assert result.details == {}
        assert result.anomalies == []
        assert result.validation_time_ms == 0.0
        assert isinstance(result.timestamp, datetime)


class TestDataQualityMetrics:
    """Test suite for DataQualityMetrics class."""

    def test_initialization(self):
        """Test DataQualityMetrics initialization."""
        metrics = DataQualityMetrics(
            data_id="data_123",
            symbol="AAPL",
            data_type="market_data",
            overall_score=0.85,
            accuracy_score=0.90,
            completeness_score=0.95,
            consistency_score=0.80,
            timeliness_score=0.88,
            validity_score=0.92,
            missing_data_percentage=0.05,
            duplicate_data_percentage=0.02,
            anomaly_count=3,
            validation_failures=1
        )

        assert metrics.data_id == "data_123"
        assert metrics.symbol == "AAPL"
        assert metrics.data_type == "market_data"
        assert metrics.overall_score == 0.85
        assert metrics.accuracy_score == 0.90
        assert metrics.completeness_score == 0.95
        assert metrics.consistency_score == 0.80
        assert metrics.timeliness_score == 0.88
        assert metrics.validity_score == 0.92
        assert metrics.missing_data_percentage == 0.05
        assert metrics.duplicate_data_percentage == 0.02
        assert metrics.anomaly_count == 3
        assert metrics.validation_failures == 1
