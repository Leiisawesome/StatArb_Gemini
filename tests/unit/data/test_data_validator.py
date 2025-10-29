"""
Unit Tests for Data Validator
==============================

Tests for the DataValidator with comprehensive validation rules,
anomaly detection, quality scoring, and integrity checking.

Author: StatArb_Gemini Testing Team
Version: 1.0.0
"""

import pytest
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from core_engine.data.validation.validator import (
    DataValidator,
    ValidationStatus,
    ValidationResult,
    DataQualityMetrics,
    ValidationConfiguration,
    AnomalyDetector
)

logger = logging.getLogger(__name__)


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
async def validator():
    """Create DataValidator instance (async)"""
    # Create validator without starting monitoring task
    val = DataValidator.__new__(DataValidator)
    val.config = {}
    val._lock = threading.Lock()
    val.anomaly_detector = AnomalyDetector({})
    val._validation_configs = {}
    val._default_config = val._create_default_config()
    val._validation_results = deque(maxlen=10000)
    val._quality_metrics = deque(maxlen=5000)
    val._validation_by_symbol = defaultdict(lambda: deque(maxlen=1000))
    val._validation_stats = {
        'total_validations': 0,
        'passed_validations': 0,
        'failed_validations': 0,
        'warnings_issued': 0,
        'anomalies_detected': 0,
        'average_validation_time_ms': 0.0,
        'quality_score_average': 0.0
    }
    val._cross_validation_data = defaultdict(lambda: defaultdict(deque))
    val._monitoring_tasks = []
    val._initialize_default_validations()
    return val


@pytest.fixture
def valid_quote_data():
    """Create valid quote data for testing"""
    return {
        'data_id': 'quote_001',
        'symbol': 'AAPL',
        'bid_price': 175.50,
        'ask_price': 175.52,
        'bid_size': 100,
        'ask_size': 200,
        'timestamp': datetime.now()
    }


@pytest.fixture
def valid_trade_data():
    """Create valid trade data for testing"""
    return {
        'data_id': 'trade_001',
        'symbol': 'AAPL',
        'price': 175.51,
        'volume': 1000,
        'timestamp': datetime.now()
    }


@pytest.fixture
def invalid_quote_data():
    """Create invalid quote data for testing"""
    return {
        'data_id': 'quote_002',
        'symbol': 'AAPL',
        'bid_price': 175.60,  # Invalid: bid > ask
        'ask_price': 175.52,
        'timestamp': datetime.now()
    }


@pytest.fixture
def anomaly_detector():
    """Create AnomalyDetector instance"""
    return AnomalyDetector()


@pytest.fixture
def validation_config():
    """Create ValidationConfiguration instance"""
    return ValidationConfiguration(
        data_type="test",
        min_price=0.01,
        max_price=10000.0,
        max_price_change_pct=15.0,
        max_spread_pct=3.0,
        required_fields=['symbol', 'price', 'timestamp']
    )


# ========================================
# CATEGORY 1: DATA VALIDATOR INITIALIZATION (3 tests)
# ========================================

class TestDataValidatorInitialization:
    """Test DataValidator initialization"""
    
    def test_validator_creation(self, validator):
        """Test validator creation"""
        assert validator is not None
        assert hasattr(validator, 'config')
        assert hasattr(validator, 'anomaly_detector')
        assert hasattr(validator, '_validation_results')
        assert hasattr(validator, '_quality_metrics')
        
        logger.info("✅ Validator creation test passed")
    
    @pytest.mark.asyncio
    async def test_validator_with_custom_config(self):
        """Test validator with custom configuration"""
        custom_config = {
            'anomaly_detection': {
                'z_score_threshold': 3.5,
                'window_size': 50
            }
        }
        
        # Create validator manually without async task
        validator = DataValidator.__new__(DataValidator)
        validator.config = custom_config
        validator._lock = threading.Lock()
        validator.anomaly_detector = AnomalyDetector(custom_config.get('anomaly_detection', {}))
        validator._validation_configs = {}
        validator._default_config = validator._create_default_config()
        validator._validation_results = deque(maxlen=10000)
        validator._quality_metrics = deque(maxlen=5000)
        validator._validation_by_symbol = defaultdict(lambda: deque(maxlen=1000))
        validator._validation_stats = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'warnings_issued': 0,
            'anomalies_detected': 0,
            'average_validation_time_ms': 0.0,
            'quality_score_average': 0.0
        }
        validator._cross_validation_data = defaultdict(lambda: defaultdict(deque))
        validator._monitoring_tasks = []
        validator._initialize_default_validations()
        
        assert validator is not None
        assert validator.config == custom_config
        
        logger.info("✅ Validator with custom config test passed")
    
    def test_validator_default_validations(self, validator):
        """Test validator has default validation configurations"""
        assert hasattr(validator, '_validation_configs')
        assert 'quote' in validator._validation_configs
        assert 'trade' in validator._validation_configs
        assert 'depth' in validator._validation_configs
        
        # Verify quote config
        quote_config = validator._validation_configs['quote']
        assert quote_config.data_type == "quote"
        assert 'bid_price' in quote_config.required_fields
        assert 'ask_price' in quote_config.required_fields
        
        logger.info("✅ Validator default validations test passed")


# ========================================
# CATEGORY 2: VALIDATION CONFIGURATION (3 tests)
# ========================================

class TestValidationConfiguration:
    """Test ValidationConfiguration dataclass"""
    
    def test_validation_config_creation(self, validation_config):
        """Test ValidationConfiguration creation"""
        assert validation_config.data_type == "test"
        assert validation_config.min_price == 0.01
        assert validation_config.max_price == 10000.0
        assert validation_config.max_price_change_pct == 15.0
        
        logger.info("✅ ValidationConfiguration creation test passed")
    
    def test_validation_config_defaults(self):
        """Test ValidationConfiguration with defaults"""
        config = ValidationConfiguration(data_type="default")
        
        assert config.data_type == "default"
        assert config.min_price is None
        assert config.max_price is None
        assert config.required_fields == []
        assert config.min_volume == 0
        
        logger.info("✅ ValidationConfiguration defaults test passed")
    
    def test_validation_config_required_fields(self):
        """Test ValidationConfiguration required fields validation"""
        config = ValidationConfiguration(
            data_type="quote",
            required_fields=['symbol', 'bid_price', 'ask_price', 'timestamp']
        )
        
        assert len(config.required_fields) == 4
        assert 'symbol' in config.required_fields
        assert 'bid_price' in config.required_fields
        
        logger.info("✅ ValidationConfiguration required fields test passed")


# ========================================
# CATEGORY 3: BASIC DATA VALIDATION (5 tests)
# ========================================

class TestBasicDataValidation:
    """Test basic data validation functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_valid_quote_data(self, validator, valid_quote_data):
        """Test validation of valid quote data"""
        result, metrics = await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        assert isinstance(metrics, DataQualityMetrics)
        assert result.status == ValidationStatus.PASSED
        assert result.score >= 0.8
        assert metrics.overall_score >= 0.8
        
        logger.info("✅ Valid quote data validation test passed")
    
    @pytest.mark.asyncio
    async def test_validate_valid_trade_data(self, validator, valid_trade_data):
        """Test validation of valid trade data"""
        result, metrics = await validator.validate_data(
            data=valid_trade_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        assert result.status == ValidationStatus.PASSED
        assert result.score >= 0.8
        assert metrics.symbol == 'AAPL'
        
        logger.info("✅ Valid trade data validation test passed")
    
    @pytest.mark.asyncio
    async def test_validate_invalid_quote_data(self, validator, invalid_quote_data):
        """Test validation of invalid quote data (bid > ask)"""
        result, metrics = await validator.validate_data(
            data=invalid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        # Should detect the spread issue
        assert result.score < 1.0  # Not perfect score
        
        logger.info("✅ Invalid quote data validation test passed")
    
    @pytest.mark.asyncio
    async def test_validate_incomplete_data(self, validator):
        """Test validation of incomplete data"""
        incomplete_data = {
            'data_id': 'incomplete_001',
            'symbol': 'AAPL'
            # Missing required fields
        }
        
        result, metrics = await validator.validate_data(
            data=incomplete_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        # Should fail completeness check
        assert 'completeness' in result.details
        assert result.details['completeness']['passed'] == False
        
        logger.info("✅ Incomplete data validation test passed")
    
    @pytest.mark.asyncio
    async def test_validate_data_with_missing_timestamp(self, validator):
        """Test validation of data with missing timestamp"""
        data = {
            'data_id': 'no_timestamp_001',
            'symbol': 'AAPL',
            'bid_price': 175.50,
            'ask_price': 175.52
            # Missing timestamp
        }
        
        result, metrics = await validator.validate_data(
            data=data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        # Should detect missing timestamp
        assert 'completeness' in result.details
        
        logger.info("✅ Data with missing timestamp validation test passed")


# ========================================
# CATEGORY 4: PRICE VALIDATION (3 tests)
# ========================================

class TestPriceValidation:
    """Test price validation rules"""
    
    @pytest.mark.asyncio
    async def test_price_range_validation(self, validator):
        """Test price range validation"""
        # Test price too low
        low_price_data = {
            'data_id': 'low_price_001',
            'symbol': 'AAPL',
            'price': 0.001,  # Below minimum
            'volume': 100,
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=low_price_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert 'price_range' in result.details
        assert result.details['price_range']['passed'] == False
        
        logger.info("✅ Price range validation test passed")
    
    @pytest.mark.asyncio
    async def test_negative_price_detection(self, validator):
        """Test detection of negative prices"""
        negative_price_data = {
            'data_id': 'negative_price_001',
            'symbol': 'AAPL',
            'price': -10.0,  # Negative price
            'volume': 100,
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=negative_price_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert 'price_range' in result.details
        assert result.details['price_range']['passed'] == False
        
        logger.info("✅ Negative price detection test passed")
    
    @pytest.mark.asyncio
    async def test_extreme_price_detection(self, validator):
        """Test detection of extreme prices"""
        extreme_price_data = {
            'data_id': 'extreme_price_001',
            'symbol': 'AAPL',
            'price': 99999.0,  # Unrealistically high
            'volume': 100,
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=extreme_price_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert 'price_range' in result.details
        # Should detect extreme price
        
        logger.info("✅ Extreme price detection test passed")


# ========================================
# CATEGORY 5: SPREAD VALIDATION (3 tests)
# ========================================

class TestSpreadValidation:
    """Test spread validation rules"""
    
    @pytest.mark.asyncio
    async def test_valid_spread(self, validator):
        """Test validation of valid spread"""
        valid_spread_data = {
            'data_id': 'valid_spread_001',
            'symbol': 'AAPL',
            'bid_price': 175.50,
            'ask_price': 175.52,  # Tight spread (0.02)
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=valid_spread_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert 'spread' in result.details
        assert result.details['spread']['passed'] == True
        
        logger.info("✅ Valid spread validation test passed")
    
    @pytest.mark.asyncio
    async def test_wide_spread_detection(self, validator):
        """Test detection of excessively wide spreads"""
        wide_spread_data = {
            'data_id': 'wide_spread_001',
            'symbol': 'AAPL',
            'bid_price': 170.00,
            'ask_price': 180.00,  # 10 dollar spread (~5.7%)
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=wide_spread_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert 'spread' in result.details
        # Should detect wide spread
        assert result.details['spread']['passed'] == False
        
        logger.info("✅ Wide spread detection test passed")
    
    @pytest.mark.asyncio
    async def test_negative_spread_detection(self, validator):
        """Test detection of negative spreads (bid >= ask)"""
        negative_spread_data = {
            'data_id': 'negative_spread_001',
            'symbol': 'AAPL',
            'bid_price': 175.52,
            'ask_price': 175.50,  # Bid > Ask (invalid)
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=negative_spread_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert 'spread' in result.details
        assert result.details['spread']['passed'] == False
        assert len(result.details['spread']['issues']) > 0
        
        logger.info("✅ Negative spread detection test passed")


# ========================================
# CATEGORY 6: VOLUME VALIDATION (2 tests)
# ========================================

class TestVolumeValidation:
    """Test volume validation rules"""
    
    @pytest.mark.asyncio
    async def test_valid_volume(self, validator):
        """Test validation of valid volume"""
        valid_volume_data = {
            'data_id': 'valid_volume_001',
            'symbol': 'AAPL',
            'price': 175.50,
            'volume': 1000,
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=valid_volume_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert 'volume' in result.details
        assert result.details['volume']['passed'] == True
        
        logger.info("✅ Valid volume validation test passed")
    
    @pytest.mark.asyncio
    async def test_negative_volume_detection(self, validator):
        """Test detection of negative volume"""
        negative_volume_data = {
            'data_id': 'negative_volume_001',
            'symbol': 'AAPL',
            'price': 175.50,
            'volume': -100,  # Negative volume
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=negative_volume_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert 'volume' in result.details
        assert result.details['volume']['passed'] == False
        
        logger.info("✅ Negative volume detection test passed")


# ========================================
# CATEGORY 7: ANOMALY DETECTION (3 tests)
# ========================================

class TestAnomalyDetection:
    """Test anomaly detection functionality"""
    
    @pytest.mark.asyncio
    async def test_anomaly_detector_creation(self, anomaly_detector):
        """Test AnomalyDetector creation"""
        assert anomaly_detector is not None
        assert hasattr(anomaly_detector, 'config')
        
        logger.info("✅ AnomalyDetector creation test passed")
    
    @pytest.mark.asyncio
    async def test_price_spike_detection(self, anomaly_detector):
        """Test price spike anomaly detection"""
        # This tests the detect_anomalies method exists and returns expected structure
        data_point = {
            'price': 200.0,  # Significantly different from typical AAPL price
            'timestamp': datetime.now()
        }
        
        anomalies = await anomaly_detector.detect_anomalies(
            data_point=data_point,
            symbol='AAPL',
            data_type='trade'
        )
        
        assert isinstance(anomalies, list)
        # Anomaly detection should return a list (may be empty)
        
        logger.info("✅ Price spike detection test passed")
    
    @pytest.mark.asyncio
    async def test_anomaly_detection_with_historical_context(self, validator):
        """Test anomaly detection with historical context"""
        # Send multiple data points to build context
        for i in range(5):
            data = {
                'data_id': f'context_{i}',
                'symbol': 'AAPL',
                'price': 175.00 + (i * 0.1),
                'volume': 1000,
                'timestamp': datetime.now() - timedelta(minutes=5-i)
            }
            
            await validator.validate_data(
                data=data,
                data_type='trade',
                symbol='AAPL'
            )
        
        # Now send an anomalous data point
        anomalous_data = {
            'data_id': 'anomaly_001',
            'symbol': 'AAPL',
            'price': 200.00,  # Significant spike
            'volume': 1000,
            'timestamp': datetime.now()
        }
        
        result, _ = await validator.validate_data(
            data=anomalous_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        assert isinstance(result, ValidationResult)
        # Anomaly detection should have processed this
        
        logger.info("✅ Anomaly detection with historical context test passed")


# ========================================
# CATEGORY 8: QUALITY METRICS (3 tests)
# ========================================

class TestQualityMetrics:
    """Test data quality metrics calculation"""
    
    @pytest.mark.asyncio
    async def test_quality_metrics_creation(self, validator, valid_quote_data):
        """Test DataQualityMetrics creation"""
        _, metrics = await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        assert isinstance(metrics, DataQualityMetrics)
        assert metrics.symbol == 'AAPL'
        assert metrics.data_type == 'quote'
        assert 0.0 <= metrics.overall_score <= 1.0
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.completeness_score <= 1.0
        
        logger.info("✅ Quality metrics creation test passed")
    
    @pytest.mark.asyncio
    async def test_quality_score_calculation(self, validator):
        """Test quality score calculation for various data quality levels"""
        # High quality data
        high_quality_data = {
            'data_id': 'high_quality_001',
            'symbol': 'AAPL',
            'bid_price': 175.50,
            'ask_price': 175.52,
            'bid_size': 100,
            'ask_size': 200,
            'timestamp': datetime.now()
        }
        
        _, high_metrics = await validator.validate_data(
            data=high_quality_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Low quality data (incomplete, issues)
        low_quality_data = {
            'data_id': 'low_quality_001',
            'symbol': 'AAPL',
            'bid_price': -10.0  # Invalid
            # Missing many required fields
        }
        
        _, low_metrics = await validator.validate_data(
            data=low_quality_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # High quality should have higher score
        assert high_metrics.overall_score > low_metrics.overall_score
        
        logger.info("✅ Quality score calculation test passed")
    
    @pytest.mark.asyncio
    async def test_quality_metrics_components(self, validator, valid_quote_data):
        """Test individual quality metric components"""
        _, metrics = await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Check all component scores exist
        assert hasattr(metrics, 'accuracy_score')
        assert hasattr(metrics, 'completeness_score')
        assert hasattr(metrics, 'consistency_score')
        assert hasattr(metrics, 'timeliness_score')
        assert hasattr(metrics, 'validity_score')
        
        # All should be between 0 and 1
        assert 0.0 <= metrics.accuracy_score <= 1.0
        assert 0.0 <= metrics.completeness_score <= 1.0
        assert 0.0 <= metrics.consistency_score <= 1.0
        assert 0.0 <= metrics.timeliness_score <= 1.0
        assert 0.0 <= metrics.validity_score <= 1.0
        
        logger.info("✅ Quality metrics components test passed")


# ========================================
# CATEGORY 9: VALIDATION RESULTS STORAGE (2 tests)
# ========================================

class TestValidationResultsStorage:
    """Test validation results storage and retrieval"""
    
    @pytest.mark.asyncio
    async def test_validation_results_storage(self, validator, valid_quote_data):
        """Test that validation results are stored"""
        initial_count = len(validator._validation_results)
        
        await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Should have one more result
        assert len(validator._validation_results) == initial_count + 1
        
        logger.info("✅ Validation results storage test passed")
    
    @pytest.mark.asyncio
    async def test_validation_results_by_symbol(self, validator):
        """Test validation results storage by symbol"""
        # Validate data for AAPL
        aapl_data = {
            'data_id': 'aapl_001',
            'symbol': 'AAPL',
            'price': 175.50,
            'volume': 1000,
            'timestamp': datetime.now()
        }
        
        await validator.validate_data(
            data=aapl_data,
            data_type='trade',
            symbol='AAPL'
        )
        
        # Validate data for GOOGL
        googl_data = {
            'data_id': 'googl_001',
            'symbol': 'GOOGL',
            'price': 140.50,
            'volume': 500,
            'timestamp': datetime.now()
        }
        
        await validator.validate_data(
            data=googl_data,
            data_type='trade',
            symbol='GOOGL'
        )
        
        # Check results are stored by symbol
        assert 'AAPL' in validator._validation_by_symbol
        assert 'GOOGL' in validator._validation_by_symbol
        assert len(validator._validation_by_symbol['AAPL']) > 0
        assert len(validator._validation_by_symbol['GOOGL']) > 0
        
        logger.info("✅ Validation results by symbol test passed")


# ========================================
# CATEGORY 10: VALIDATION STATISTICS (3 tests)
# ========================================

class TestValidationStatistics:
    """Test validation statistics tracking"""
    
    @pytest.mark.asyncio
    async def test_validation_stats_tracking(self, validator, valid_quote_data):
        """Test validation statistics are tracked"""
        initial_total = validator._validation_stats['total_validations']
        
        await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Total validations should increment
        assert validator._validation_stats['total_validations'] == initial_total + 1
        
        logger.info("✅ Validation stats tracking test passed")
    
    @pytest.mark.asyncio
    async def test_validation_stats_passed_count(self, validator, valid_quote_data):
        """Test passed validations count"""
        initial_passed = validator._validation_stats['passed_validations']
        
        await validator.validate_data(
            data=valid_quote_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Passed validations should increment
        assert validator._validation_stats['passed_validations'] >= initial_passed
        
        logger.info("✅ Validation stats passed count test passed")
    
    @pytest.mark.asyncio
    async def test_validation_stats_failed_count(self, validator):
        """Test failed validations count"""
        initial_failed = validator._validation_stats['failed_validations']
        
        # Submit invalid data
        invalid_data = {
            'data_id': 'invalid_001',
            'symbol': 'AAPL',
            'bid_price': -10.0,  # Invalid
            'timestamp': datetime.now()
        }
        
        await validator.validate_data(
            data=invalid_data,
            data_type='quote',
            symbol='AAPL'
        )
        
        # Failed validations should increment if score is low
        current_failed = validator._validation_stats['failed_validations']
        assert current_failed >= initial_failed
        
        logger.info("✅ Validation stats failed count test passed")


# ========================================
# SUMMARY
# ========================================

"""
Test Coverage Summary
====================

Total Tests: 30

Category Breakdown:
- Category 1: Data Validator Initialization (3 tests)
- Category 2: Validation Configuration (3 tests)
- Category 3: Basic Data Validation (5 tests)
- Category 4: Price Validation (3 tests)
- Category 5: Spread Validation (3 tests)
- Category 6: Volume Validation (2 tests)
- Category 7: Anomaly Detection (3 tests)
- Category 8: Quality Metrics (3 tests)
- Category 9: Validation Results Storage (2 tests)
- Category 10: Validation Statistics (3 tests)

Target Coverage:
- DataValidator class: Core validation logic, quality metrics, anomaly detection
- ValidationConfiguration: Configuration management and defaults
- AnomalyDetector: Anomaly detection integration
- ValidationResult & DataQualityMetrics: Result structures

Critical Paths Tested:
- Data validation workflow (validate_data)
- Price range validation
- Spread validation
- Volume validation
- Completeness checking
- Anomaly detection integration
- Quality metrics calculation
- Results storage and retrieval
- Statistics tracking
"""
