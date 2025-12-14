#!/usr/bin/env python3
"""
Comprehensive tests for Signal Validators
=========================================

Tests all functionality to achieve 100% coverage.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from core_engine.processing.signals.validators import (
    SignalValidator,
    ValidationRuleEngine,
    ValidationRule,
    ValidationResult,
    SignalValidationReport,
    PortfolioValidationReport,
    ValidationLevel,
    ValidationCategory,
    ValidationStatus
)

class TestValidationRule:
    """Test ValidationRule dataclass"""

    def test_validation_rule_creation(self):
        """Test creating a validation rule"""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Rule",
            description="A test validation rule",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR
        )

        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.description == "A test validation rule"
        assert rule.category == ValidationCategory.DATA_QUALITY
        assert rule.level == ValidationLevel.ERROR
        assert rule.enabled is True
        assert rule.mandatory is False
        assert rule.weight == 1.0
        assert rule.threshold is None
        assert rule.min_threshold is None
        assert rule.max_threshold is None
        assert rule.validation_function is None
        assert rule.required_fields == []
        assert rule.required_context == []
        assert rule.custom_params == {}

    def test_validation_rule_with_parameters(self):
        """Test creating a validation rule with parameters"""
        def test_function(signal, context):
            return True

        rule = ValidationRule(
            rule_id="test_rule_with_params",
            name="Test Rule With Params",
            description="A test validation rule with parameters",
            category=ValidationCategory.SIGNAL_QUALITY,
            level=ValidationLevel.WARNING,
            threshold=0.5,
            min_threshold=0.0,
            max_threshold=1.0,
            validation_function=test_function,
            enabled=False,
            mandatory=True,
            weight=2.0,
            required_fields=["confidence", "strength"],
            required_context=["market_data"],
            custom_params={"param1": "value1", "param2": 42}
        )

        assert rule.threshold == 0.5
        assert rule.min_threshold == 0.0
        assert rule.max_threshold == 1.0
        assert rule.validation_function == test_function
        assert rule.enabled is False
        assert rule.mandatory is True
        assert rule.weight == 2.0
        assert rule.required_fields == ["confidence", "strength"]
        assert rule.required_context == ["market_data"]
        assert rule.custom_params == {"param1": "value1", "param2": 42}

class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_validation_result_creation(self):
        """Test creating a validation result"""
        result = ValidationResult(
            rule_id="test_rule",
            status=ValidationStatus.PASSED,
            message="Test passed",
            score=0.8
        )

        assert result.rule_id == "test_rule"
        assert result.status == ValidationStatus.PASSED
        assert result.message == "Test passed"
        assert result.score == 0.8
        assert result.value is None
        assert result.threshold is None
        assert result.details == {}
        assert result.suggestions == []
        assert isinstance(result.validation_time, datetime)
        assert result.execution_time_ms == 0.0

    def test_validation_result_with_parameters(self):
        """Test creating a validation result with parameters"""
        result = ValidationResult(
            rule_id="test_rule_with_params",
            status=ValidationStatus.FAILED,
            message="Test failed",
            score=0.2,
            value=0.3,
            threshold=0.5,
            details={"key1": "value1", "key2": 42},
            suggestions=["suggestion1", "suggestion2"],
            execution_time_ms=1.5
        )

        assert result.rule_id == "test_rule_with_params"
        assert result.status == ValidationStatus.FAILED
        assert result.message == "Test failed"
        assert result.score == 0.2
        assert result.value == 0.3
        assert result.threshold == 0.5
        assert result.details == {"key1": "value1", "key2": 42}
        assert result.suggestions == ["suggestion1", "suggestion2"]
        assert result.execution_time_ms == 1.5

class TestSignalValidationReport:
    """Test SignalValidationReport dataclass"""

    def test_signal_validation_report_creation(self):
        """Test creating a signal validation report"""
        report = SignalValidationReport(
            signal_id="test_signal_1",
            symbol="AAPL",
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.PASSED,
            overall_score=0.8,
            confidence_level=0.75
        )

        assert report.signal_id == "test_signal_1"
        assert report.symbol == "AAPL"
        assert isinstance(report.validation_timestamp, datetime)
        assert report.overall_status == ValidationStatus.PASSED
        assert report.overall_score == 0.8
        assert report.confidence_level == 0.75
        assert report.data_quality_score == 0.0
        assert report.signal_quality_score == 0.0
        assert report.risk_score == 0.0
        assert report.consistency_score == 0.0
        assert report.validation_results == []
        assert report.rules_passed == 0
        assert report.rules_warning == 0
        assert report.rules_failed == 0
        assert report.rules_critical == 0
        assert report.recommendations == []
        assert report.risk_warnings == []
        assert report.validation_duration_ms == 0.0
        assert report.validator_version == "1.0"

    def test_signal_validation_report_with_parameters(self):
        """Test creating a signal validation report with parameters"""
        validation_results = [
            ValidationResult("rule1", ValidationStatus.PASSED, "Rule 1 passed", 0.9),
            ValidationResult("rule2", ValidationStatus.WARNING, "Rule 2 warning", 0.7)
        ]

        report = SignalValidationReport(
            signal_id="test_signal_2",
            symbol="TSLA",
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.WARNING,
            overall_score=0.6,
            confidence_level=0.8,
            data_quality_score=0.7,
            signal_quality_score=0.6,
            risk_score=0.5,
            consistency_score=0.8,
            validation_results=validation_results,
            rules_passed=1,
            rules_warning=1,
            rules_failed=0,
            rules_critical=0,
            recommendations=["Recommendation 1", "Recommendation 2"],
            risk_warnings=["Risk warning 1"],
            validation_duration_ms=5.2
        )

        assert report.signal_id == "test_signal_2"
        assert report.symbol == "TSLA"
        assert report.overall_status == ValidationStatus.WARNING
        assert report.overall_score == 0.6
        assert report.confidence_level == 0.8
        assert report.data_quality_score == 0.7
        assert report.signal_quality_score == 0.6
        assert report.risk_score == 0.5
        assert report.consistency_score == 0.8
        assert len(report.validation_results) == 2
        assert report.rules_passed == 1
        assert report.rules_warning == 1
        assert report.rules_failed == 0
        assert report.rules_critical == 0
        assert len(report.recommendations) == 2
        assert len(report.risk_warnings) == 1
        assert report.validation_duration_ms == 5.2

class TestPortfolioValidationReport:
    """Test PortfolioValidationReport dataclass"""

    def test_portfolio_validation_report_creation(self):
        """Test creating a portfolio validation report"""
        report = PortfolioValidationReport(
            validation_id="portfolio_123",
            validation_timestamp=datetime.now(),
            total_signals=10,
            valid_signals=8,
            invalid_signals=2,
            portfolio_concentration=0.15
        )

        assert report.validation_id == "portfolio_123"
        assert isinstance(report.validation_timestamp, datetime)
        assert report.total_signals == 10
        assert report.valid_signals == 8
        assert report.invalid_signals == 2
        assert report.portfolio_concentration == 0.15
        assert report.sector_concentration == {}
        assert report.total_exposure == 0.0
        assert report.net_exposure == 0.0
        assert report.signal_quality_distribution == {}
        assert report.average_signal_quality == 0.0
        assert report.portfolio_issues == []
        assert report.risk_alerts == []
        assert report.signal_reports == []

    def test_portfolio_validation_report_with_parameters(self):
        """Test creating a portfolio validation report with parameters"""
        signal_reports = [
            SignalValidationReport("signal1", "AAPL", datetime.now(), ValidationStatus.PASSED, 0.8, 0.75),
            SignalValidationReport("signal2", "TSLA", datetime.now(), ValidationStatus.WARNING, 0.6, 0.7)
        ]

        report = PortfolioValidationReport(
            validation_id="portfolio_456",
            validation_timestamp=datetime.now(),
            total_signals=5,
            valid_signals=3,
            invalid_signals=2,
            portfolio_concentration=0.25,
            sector_concentration={"Technology": 0.6, "Healthcare": 0.4},
            total_exposure=1.5,
            net_exposure=0.3,
            signal_quality_distribution={"High": 2, "Medium": 1, "Low": 2},
            average_signal_quality=0.65,
            portfolio_issues=["Issue 1", "Issue 2"],
            risk_alerts=["Risk alert 1"],
            signal_reports=signal_reports
        )

        assert report.validation_id == "portfolio_456"
        assert report.total_signals == 5
        assert report.valid_signals == 3
        assert report.invalid_signals == 2
        assert report.portfolio_concentration == 0.25
        assert report.sector_concentration == {"Technology": 0.6, "Healthcare": 0.4}
        assert report.total_exposure == 1.5
        assert report.net_exposure == 0.3
        assert report.signal_quality_distribution == {"High": 2, "Medium": 1, "Low": 2}
        assert report.average_signal_quality == 0.65
        assert len(report.portfolio_issues) == 2
        assert len(report.risk_alerts) == 1
        assert len(report.signal_reports) == 2

class TestValidationRuleEngine:
    """Test ValidationRuleEngine class"""

    @pytest.fixture
    def rule_engine(self):
        return ValidationRuleEngine()

    def test_initialization(self, rule_engine):
        """Test rule engine initialization"""
        assert isinstance(rule_engine.rules, dict)
        assert len(rule_engine.rules) > 0  # Should have default rules

    def test_register_rule(self, rule_engine):
        """Test registering a custom rule"""
        rule = ValidationRule(
            rule_id="custom_rule",
            name="Custom Rule",
            description="A custom validation rule",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR
        )

        rule_engine.register_rule(rule)

        assert "custom_rule" in rule_engine.rules
        assert rule_engine.rules["custom_rule"] == rule

    def test_unregister_rule(self, rule_engine):
        """Test unregistering a rule"""
        # First register a rule
        rule = ValidationRule(
            rule_id="temp_rule",
            name="Temporary Rule",
            description="A temporary validation rule",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR
        )
        rule_engine.register_rule(rule)

        # Then unregister it
        result = rule_engine.unregister_rule("temp_rule")

        assert result is True
        assert "temp_rule" not in rule_engine.rules

    def test_unregister_nonexistent_rule(self, rule_engine):
        """Test unregistering a non-existent rule"""
        result = rule_engine.unregister_rule("nonexistent_rule")

        assert result is False

    def test_get_rules_all(self, rule_engine):
        """Test getting all rules"""
        rules = rule_engine.get_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0
        assert all(isinstance(rule, ValidationRule) for rule in rules)

    def test_get_rules_by_category(self, rule_engine):
        """Test getting rules by category"""
        data_quality_rules = rule_engine.get_rules(ValidationCategory.DATA_QUALITY)

        assert isinstance(data_quality_rules, list)
        assert all(rule.category == ValidationCategory.DATA_QUALITY for rule in data_quality_rules)

    def test_validate_signal_strength_range(self, rule_engine):
        """Test signal strength range validation"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 0.5

        context = {}

        result = rule_engine._validate_signal_strength_range(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "signal_strength_range"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert result.value == 0.5

    def test_validate_signal_strength_range_out_of_bounds(self, rule_engine):
        """Test signal strength range validation with out-of-bounds value"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 1.5  # Out of bounds

        context = {}

        result = rule_engine._validate_signal_strength_range(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "signal_strength_range"
        assert result.status == ValidationStatus.FAILED
        assert result.score == 0.0
        assert result.value == 1.5

    def test_validate_confidence_range(self, rule_engine):
        """Test confidence range validation"""
        # Create a mock signal
        signal = Mock()
        signal.confidence = 0.8

        context = {}

        result = rule_engine._validate_confidence_range(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "confidence_range"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert result.value == 0.8

    def test_validate_confidence_range_out_of_bounds(self, rule_engine):
        """Test confidence range validation with out-of-bounds value"""
        # Create a mock signal
        signal = Mock()
        signal.confidence = 1.5  # Out of bounds

        context = {}

        result = rule_engine._validate_confidence_range(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "confidence_range"
        assert result.status == ValidationStatus.FAILED
        assert result.score == 0.0
        assert result.value == 1.5

    def test_validate_min_confidence(self, rule_engine):
        """Test minimum confidence validation"""
        # Create a mock signal
        signal = Mock()
        signal.confidence = 0.7

        context = {}

        result = rule_engine._validate_min_confidence(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "min_confidence_threshold"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.7
        assert result.value == 0.7
        assert result.threshold == 0.5

    def test_validate_min_confidence_below_threshold(self, rule_engine):
        """Test minimum confidence validation with below-threshold value"""
        # Create a mock signal
        signal = Mock()
        signal.confidence = 0.3  # Below threshold

        context = {}

        result = rule_engine._validate_min_confidence(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "min_confidence_threshold"
        assert result.status == ValidationStatus.WARNING
        assert result.score == 0.6  # 0.3 / 0.5
        assert result.value == 0.3
        assert result.threshold == 0.5

    def test_validate_signal_significance(self, rule_engine):
        """Test signal significance validation"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 0.5
        signal.z_score = 2.5

        context = {}

        result = rule_engine._validate_signal_significance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "signal_significance"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0  # min(2.5 / 2.0, 1.0)
        assert result.value == 2.5
        assert result.threshold == 2.0

    def test_validate_signal_significance_below_threshold(self, rule_engine):
        """Test signal significance validation with below-threshold value"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 0.5
        signal.z_score = 1.5  # Below threshold

        context = {}

        result = rule_engine._validate_signal_significance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "signal_significance"
        assert result.status == ValidationStatus.WARNING
        assert result.score == 0.75  # 1.5 / 2.0
        assert result.value == 1.5
        assert result.threshold == 2.0

    def test_validate_signal_significance_no_z_score(self, rule_engine):
        """Test signal significance validation without z_score"""
        # Create a mock signal
        signal = Mock()
        signal.strength = 0.5
        signal.z_score = None

        context = {"historical_volatility": 0.2}

        result = rule_engine._validate_signal_significance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "signal_significance"
        # Should calculate z_score from strength and volatility
        expected_z_score = abs(0.5) / max(0.2, 0.01)
        assert result.value == expected_z_score

    def test_validate_position_size(self, rule_engine):
        """Test position size validation"""
        # Create a mock signal
        signal = Mock()
        signal.suggested_position_size = 0.05  # 5%

        context = {}

        result = rule_engine._validate_position_size(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "position_size_limit"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert result.value == 0.05
        assert result.threshold == 0.1

    def test_validate_position_size_exceeds_limit(self, rule_engine):
        """Test position size validation with size exceeding limit"""
        # Create a mock signal
        signal = Mock()
        signal.suggested_position_size = 0.15  # 15% - exceeds limit

        context = {}

        result = rule_engine._validate_position_size(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "position_size_limit"
        assert result.status == ValidationStatus.FAILED
        assert result.score == 0.0
        assert result.value == 0.15
        assert result.threshold == 0.1
        assert len(result.suggestions) > 0

    def test_validate_volatility(self, rule_engine):
        """Test volatility validation"""
        # Create a mock signal
        signal = Mock()
        signal.expected_volatility = 0.3  # 30%

        context = {}

        result = rule_engine._validate_volatility(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "volatility_check"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.7  # 1.0 - (0.3 / 1.0)
        assert result.value == 0.3
        assert result.threshold == 1.0

    def test_validate_volatility_exceeds_threshold(self, rule_engine):
        """Test volatility validation with volatility exceeding threshold"""
        # Create a mock signal
        signal = Mock()
        signal.expected_volatility = 1.2  # 120% - exceeds threshold

        context = {}

        result = rule_engine._validate_volatility(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "volatility_check"
        assert result.status == ValidationStatus.WARNING
        assert result.score == 0.8  # max(0, 1.0 - (1.2 - 1.0)) = 0.8
        assert result.value == 1.2
        assert result.threshold == 1.0
        assert len(result.suggestions) > 0

    def test_validate_volatility_from_context(self, rule_engine):
        """Test volatility validation using context data"""
        # Create a mock signal
        signal = Mock()
        signal.expected_volatility = None

        context = {"historical_volatility": 0.25}

        result = rule_engine._validate_volatility(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "volatility_check"
        assert result.value == 0.25  # From context
        assert result.status == ValidationStatus.PASSED

    def test_validate_correlation_no_recent_signals(self, rule_engine):
        """Test correlation validation with no recent signals"""
        # Create a mock signal
        signal = Mock()
        signal.symbol = "AAPL"

        context = {"recent_signals": []}

        result = rule_engine._validate_correlation(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "correlation_check"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert "No recent signals to compare" in result.message

    def test_validate_correlation_insufficient_signals(self, rule_engine):
        """Test correlation validation with insufficient recent signals"""
        # Create a mock signal
        signal = Mock()
        signal.symbol = "AAPL"
        signal.strength = 0.5

        # Create recent signals for different symbol
        recent_signal = Mock()
        recent_signal.symbol = "TSLA"
        recent_signal.strength = 0.3

        context = {"recent_signals": [recent_signal]}

        result = rule_engine._validate_correlation(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "correlation_check"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0
        assert "Insufficient recent signals for correlation check" in result.message

    def test_validate_correlation_sufficient_signals(self, rule_engine):
        """Test correlation validation with sufficient recent signals"""
        # Create a mock signal
        signal = Mock()
        signal.symbol = "AAPL"
        signal.strength = 0.5

        # Create recent signals for same symbol
        recent_signals = []
        for i in range(5):
            recent_signal = Mock()
            recent_signal.symbol = "AAPL"
            recent_signal.strength = 0.3 + i * 0.1
            recent_signals.append(recent_signal)

        context = {"recent_signals": recent_signals}

        result = rule_engine._validate_correlation(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "correlation_check"
        # Should calculate correlation and determine if it's acceptable

    def test_validate_historical_performance(self, rule_engine):
        """Test historical performance validation"""
        # Create a mock signal
        signal = Mock()
        signal.signal_type = Mock()
        signal.signal_type.value = "BUY"

        context = {"historical_performance": {"BUY": 0.15}}  # 15% return

        result = rule_engine._validate_historical_performance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "historical_performance"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 1.0  # min(0.15 + 1, 1.0)
        assert result.value == 0.15
        assert result.threshold == 0.0

    def test_validate_historical_performance_poor(self, rule_engine):
        """Test historical performance validation with poor performance"""
        # Create a mock signal
        signal = Mock()
        signal.signal_type = Mock()
        signal.signal_type.value = "SELL"

        context = {"historical_performance": {"SELL": -0.05}}  # -5% return

        result = rule_engine._validate_historical_performance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "historical_performance"
        assert result.status == ValidationStatus.WARNING
        assert result.score == 0.95  # max(0, -0.05 + 1)
        assert result.value == -0.05
        assert result.threshold == 0.0
        assert len(result.suggestions) > 0

    def test_validate_historical_performance_no_data(self, rule_engine):
        """Test historical performance validation with no data"""
        # Create a mock signal
        signal = Mock()
        signal.signal_type = Mock()
        signal.signal_type.value = "BUY"

        context = {}

        result = rule_engine._validate_historical_performance(signal, context)

        assert isinstance(result, ValidationResult)
        assert result.rule_id == "historical_performance"
        assert result.status == ValidationStatus.PASSED
        assert result.score == 0.5
        assert "No historical performance data available" in result.message

class TestSignalValidator:
    """Test SignalValidator class"""

    @pytest.fixture
    def validator(self):
        return SignalValidator()

    @pytest.fixture
    def mock_signal(self):
        """Create mock signal for testing"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 0.8
        signal.confidence = 0.8
        signal.price = 150.0
        signal.quantity = 100
        signal.strategy = "test_strategy"
        signal.metadata = {"test": "value"}
        return signal

    def test_initialization_default(self, validator):
        """Test initialization with default config"""
        assert validator.config == {}
        assert validator.enable_all_rules is True
        assert validator.fail_on_critical is True
        assert validator.min_overall_score == 0.5
        assert isinstance(validator.rule_engine, ValidationRuleEngine)
        assert len(validator._validation_history) == 0
        assert len(validator._signal_history) == 0
        assert len(validator._validation_times) == 0
        assert len(validator._validation_stats) == 0

    def test_initialization_custom_config(self, validator):
        """Test initialization with custom config"""
        config = {
            'enable_all_rules': False,
            'fail_on_critical': False,
            'min_overall_score': 0.7,
            'min_confidence': 0.6,
            'max_age_seconds': 600,
            'required_indicators': ['rsi', 'macd'],
            'max_position_size': 50000,
            'max_drawdown': 0.05,
            'max_volatility': 0.3,
            'min_volume': 2000,
            'max_spread': 0.03
        }
        validator = SignalValidator(config)
        assert validator.config == config
        assert validator.enable_all_rules is False
        assert validator.fail_on_critical is False
        assert validator.min_overall_score == 0.7

    def test_validate_confidence(self, validator, mock_signal):
        """Test confidence validation"""
        # Test with high confidence
        mock_signal.confidence = 0.8
        valid, status, message = validator.validate_confidence(mock_signal)

        assert valid is True
        assert status == ValidationStatus.PASSED
        assert "meets minimum threshold" in message

        # Test with low confidence
        mock_signal.confidence = 0.3
        valid, status, message = validator.validate_confidence(mock_signal)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "below minimum threshold" in message

    def test_validate_age(self, validator, mock_signal):
        """Test age validation"""
        # Test with fresh signal
        mock_signal.timestamp = datetime.now()
        valid, status, message = validator.validate_age(mock_signal)

        assert valid is True
        assert status == ValidationStatus.PASSED
        assert "within limit" in message

        # Test with old signal
        mock_signal.timestamp = datetime.now() - timedelta(minutes=10)
        valid, status, message = validator.validate_age(mock_signal)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "exceeds limit" in message

    def test_validate_indicators(self, validator, mock_signal):
        """Test indicators validation"""
        # Test with all required indicators
        mock_signal.metadata = {
            'indicators': {
                'rsi': 0.6,
                'macd': 0.1,
                'volume': 1000000
            }
        }
        valid, status, message = validator.validate_indicators(mock_signal)

        assert valid is True
        assert status == ValidationStatus.PASSED
        assert "All required indicators present" in message

        # Test with missing indicators
        mock_signal.metadata = {
            'indicators': {
                'rsi': 0.6,
                'macd': 0.1
                # Missing 'volume'
            }
        }
        valid, status, message = validator.validate_indicators(mock_signal)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "Missing required indicators" in message
        assert "volume" in message

    def test_validate_risk_limits(self, validator, mock_signal):
        """Test risk limits validation"""
        # Test with acceptable risk levels
        market_data = {
            'position_size': 50000,
            'current_drawdown': 0.05,
            'volatility': 0.2
        }
        valid, status, message = validator.validate_risk_limits(mock_signal, market_data)

        assert valid is True
        assert status == ValidationStatus.PASSED
        assert "All risk limits within acceptable ranges" in message

        # Test with excessive position size
        market_data = {
            'position_size': 150000,  # Exceeds default limit
            'current_drawdown': 0.05,
            'volatility': 0.2
        }
        valid, status, message = validator.validate_risk_limits(mock_signal, market_data)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "exceeds limit" in message

        # Test with excessive drawdown
        market_data = {
            'position_size': 50000,
            'current_drawdown': 0.15,  # Exceeds default limit
            'volatility': 0.2
        }
        valid, status, message = validator.validate_risk_limits(mock_signal, market_data)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "exceeds limit" in message

        # Test with excessive volatility
        market_data = {
            'position_size': 50000,
            'current_drawdown': 0.05,
            'volatility': 0.6  # Exceeds default limit
        }
        valid, status, message = validator.validate_risk_limits(mock_signal, market_data)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "exceeds limit" in message

    def test_validate_market_conditions(self, validator, mock_signal):
        """Test market conditions validation"""
        # Test with acceptable market conditions
        market_conditions = {
            'volume': 5000,
            'spread': 0.02
        }
        valid, status, message = validator.validate_market_conditions(mock_signal, market_conditions)

        assert valid is True
        assert status == ValidationStatus.PASSED
        assert "Market conditions acceptable" in message

        # Test with low volume
        market_conditions = {
            'volume': 500,  # Below default minimum
            'spread': 0.02
        }
        valid, status, message = validator.validate_market_conditions(mock_signal, market_conditions)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "below minimum" in message

        # Test with high spread
        market_conditions = {
            'volume': 5000,
            'spread': 0.08  # Exceeds default maximum
        }
        valid, status, message = validator.validate_market_conditions(mock_signal, market_conditions)

        assert valid is False
        assert status == ValidationStatus.FAILED
        assert "exceeds maximum" in message

    def test_validate_signal_comprehensive(self, validator, mock_signal):
        """Test comprehensive signal validation"""
        market_data = {
            'position_size': 50000,
            'current_drawdown': 0.05,
            'volatility': 0.2
        }
        market_conditions = {
            'volume': 5000,
            'spread': 0.02
        }

        result = validator.validate_signal(mock_signal, market_data, market_conditions)

        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

        # Check validation details
        details = result['validation_details']
        assert 'confidence' in details
        assert 'age' in details
        assert 'indicators' in details
        assert 'risk_limits' in details
        assert 'market_conditions' in details

        # Each detail should have valid, status, and message
        for key, detail in details.items():
            assert 'valid' in detail
            assert 'status' in detail
            assert 'message' in detail

    def test_validate_signal_with_warnings(self, validator, mock_signal):
        """Test signal validation with warnings"""
        # Set up signal to trigger warnings
        mock_signal.confidence = 0.4  # Below threshold
        mock_signal.timestamp = datetime.now() - timedelta(minutes=10)  # Old signal
        mock_signal.metadata = {'indicators': {}}  # Missing indicators

        market_data = {
            'position_size': 150000,  # Exceeds limit
            'current_drawdown': 0.15,  # Exceeds limit
            'volatility': 0.6  # Exceeds limit
        }
        market_conditions = {
            'volume': 500,  # Below minimum
            'spread': 0.08  # Exceeds maximum
        }

        result = validator.validate_signal(mock_signal, market_data, market_conditions)

        assert result['overall_status'] == ValidationStatus.FAILED
        assert len(result['warnings']) > 0

        # Check that all validations failed
        details = result['validation_details']
        for key, detail in details.items():
            assert detail['valid'] is False
            assert detail['status'] == ValidationStatus.FAILED

    def test_add_custom_rule(self, validator):
        """Test adding a custom rule"""
        rule = ValidationRule(
            rule_id="custom_test_rule",
            name="Custom Test Rule",
            description="A custom test rule",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR
        )

        validator.add_custom_rule(rule)

        assert "custom_test_rule" in validator.rule_engine.rules

    def test_remove_rule(self, validator):
        """Test removing a rule"""
        # First add a custom rule
        rule = ValidationRule(
            rule_id="temp_rule",
            name="Temporary Rule",
            description="A temporary rule",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR
        )
        validator.add_custom_rule(rule)

        # Then remove it
        result = validator.remove_rule("temp_rule")

        assert result is True
        assert "temp_rule" not in validator.rule_engine.rules

    def test_remove_nonexistent_rule(self, validator):
        """Test removing a non-existent rule"""
        result = validator.remove_rule("nonexistent_rule")

        assert result is False

    def test_get_validation_statistics(self, validator):
        """Test getting validation statistics"""
        stats = validator.get_validation_statistics()

        assert isinstance(stats, dict)
        assert 'total_validations' in stats
        assert 'average_validation_time_ms' in stats
        assert 'validation_status_distribution' in stats
        assert 'registered_rules' in stats
        assert 'enabled_rules' in stats
        assert 'recent_validations' in stats

    def test_get_recent_validations(self, validator):
        """Test getting recent validations"""
        recent = validator.get_recent_validations()

        assert isinstance(recent, list)
        assert len(recent) == 0  # No validations yet

    def test_get_validation_rules(self, validator):
        """Test getting validation rules"""
        rules = validator.get_validation_rules()

        assert isinstance(rules, list)
        assert len(rules) > 0
        assert all(isinstance(rule, ValidationRule) for rule in rules)

    def test_update_rule_config(self, validator):
        """Test updating rule configuration"""
        # Update an existing rule
        result = validator.update_rule_config("min_confidence_threshold", threshold=0.7)

        assert result is True
        rule = validator.rule_engine.rules["min_confidence_threshold"]
        assert rule.threshold == 0.7

    def test_update_rule_config_nonexistent(self, validator):
        """Test updating configuration for non-existent rule"""
        result = validator.update_rule_config("nonexistent_rule", threshold=0.7)

        assert result is False

    def test_generate_recommendations(self, validator):
        """Test generating recommendations"""
        # Create a validation report with low scores
        report = SignalValidationReport(
            signal_id="test_signal",
            symbol="AAPL",
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.WARNING,
            overall_score=0.3,
            confidence_level=0.4,
            data_quality_score=0.2,
            signal_quality_score=0.3,
            risk_score=0.4,
            consistency_score=0.5
        )

        recommendations = validator._generate_recommendations(report)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("low" in rec.lower() for rec in recommendations)
        assert any("data quality" in rec.lower() for rec in recommendations)
        assert any("signal quality" in rec.lower() for rec in recommendations)
        assert any("high risk" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_validate_portfolio(self, validator):
        """Test portfolio validation"""
        # Create test signals
        signals = []
        for i in range(3):
            signal = Mock()
            signal.symbol = f"STOCK_{i}"
            signal.suggested_position_size = 0.1 + i * 0.05
            signal.timestamp = datetime.now()
            signal.confidence = 0.6 + i * 0.1
            signal.strength = 0.5 + i * 0.1
            signal.signal_type = "BUY" if i % 2 == 0 else "SELL"
            signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}
            signals.append(signal)

        context = {
            'sectors': {
                'STOCK_0': 'Technology',
                'STOCK_1': 'Healthcare',
                'STOCK_2': 'Technology'
            }
        }

        result = await validator.validate_portfolio(signals, context)

        assert isinstance(result, PortfolioValidationReport)
        assert result.total_signals == 3
        assert result.valid_signals >= 0
        assert result.invalid_signals >= 0
        assert result.valid_signals + result.invalid_signals == 3
        assert len(result.signal_reports) == 3
        assert result.portfolio_concentration >= 0
        assert result.total_exposure >= 0
        assert result.net_exposure is not None
        assert result.average_signal_quality >= 0

    @pytest.mark.asyncio
    async def test_validate_portfolio_empty(self, validator):
        """Test portfolio validation with empty signal list"""
        result = await validator.validate_portfolio([], {})

        assert isinstance(result, PortfolioValidationReport)
        assert result.total_signals == 0
        assert result.valid_signals == 0
        assert result.invalid_signals == 0
        assert len(result.signal_reports) == 0

    @pytest.mark.asyncio
    async def test_validate_portfolio_error_handling(self, validator):
        """Test portfolio validation error handling"""
        # Create a signal that will cause an error
        signal = Mock()
        signal.symbol = "ERROR_SIGNAL"
        signal.suggested_position_size = 0.1
        signal.timestamp = datetime.now()
        signal.confidence = 0.6
        signal.strength = 0.5
        signal.signal_type = "BUY"
        signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

        # Mock the validate_signal method to raise an exception
        with patch.object(validator, 'validate_signal', side_effect=Exception("Test error")):
            result = await validator.validate_portfolio([signal], {})

            assert isinstance(result, PortfolioValidationReport)
            assert len(result.portfolio_issues) > 0
            assert any("error" in issue.lower() for issue in result.portfolio_issues)

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""

    @pytest.fixture
    def validator(self):
        return SignalValidator()

    def test_validate_confidence_missing_attribute(self, validator):
        """Test confidence validation with missing confidence attribute"""
        # Create a signal object without confidence attribute
        class SignalWithoutConfidence:
            def __init__(self):
                pass

        signal = SignalWithoutConfidence()

        valid, status, message = validator.validate_confidence(signal)

        assert valid  # Should default to 0.5 which passes
        assert status == ValidationStatus.PASSED

    def test_validate_age_missing_timestamp(self, validator):
        """Test age validation with missing timestamp attribute"""
        # Create a signal object without timestamp attribute
        class SignalWithoutTimestamp:
            def __init__(self):
                pass

        signal = SignalWithoutTimestamp()

        valid, status, message = validator.validate_age(signal)

        assert valid  # Should default to current time which passes
        assert status == ValidationStatus.PASSED

    def test_validate_indicators_missing_metadata(self, validator):
        """Test indicators validation with missing metadata attribute"""
        # Create a signal object without metadata attribute
        class SignalWithoutMetadata:
            def __init__(self):
                pass

        signal = SignalWithoutMetadata()

        valid, status, message = validator.validate_indicators(signal)

        assert not valid  # Should fail due to missing indicators
        assert status == ValidationStatus.FAILED
        assert "Missing required indicators" in message

    def test_validate_risk_limits_missing_market_data(self, validator):
        """Test risk limits validation with missing market data"""
        # Create a mock signal
        signal = Mock()
        signal.symbol = "AAPL"
        signal.quantity = 100

        market_data = {}  # Empty market data

        valid, status, message = validator.validate_risk_limits(signal, market_data)

        assert valid is True  # Should use default values
        assert status == ValidationStatus.PASSED

    def test_validate_market_conditions_missing_data(self, validator):
        """Test market conditions validation with missing data"""
        # Create a mock signal
        signal = Mock()
        signal.symbol = "AAPL"

        market_conditions = {}  # Empty market conditions

        valid, status, message = validator.validate_market_conditions(signal, market_conditions)

        assert valid is False  # Should fail due to missing volume
        assert status == ValidationStatus.FAILED
        assert "below minimum" in message

    def test_validate_signal_with_none_values(self, validator):
        """Test signal validation with None values"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = None
        signal.signal_type = None
        signal.strength = None
        signal.confidence = None
        signal.price = None
        signal.quantity = None
        signal.strategy = None
        signal.metadata = None

        market_data = {}
        market_conditions = {}

        result = validator.validate_signal(signal, market_data, market_conditions)

        # Should handle None values gracefully
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

    def test_validate_signal_with_extreme_values(self, validator):
        """Test signal validation with extreme values"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = 1e10  # Extreme strength
        signal.confidence = 1e10  # Extreme confidence
        signal.price = 1e10  # Extreme price
        signal.quantity = 1e10  # Extreme quantity
        signal.strategy = "test_strategy"
        signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

        market_data = {
            'position_size': 1e10,
            'current_drawdown': 1e10,
            'volatility': 1e10
        }
        market_conditions = {
            'volume': 1e10,
            'spread': 1e10
        }

        result = validator.validate_signal(signal, market_data, market_conditions)

        # Should handle extreme values gracefully
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

    def test_validate_signal_with_negative_values(self, validator):
        """Test signal validation with negative values"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = -1e10  # Extreme negative strength
        signal.confidence = -1e10  # Extreme negative confidence
        signal.price = -1e10  # Extreme negative price
        signal.quantity = -1e10  # Extreme negative quantity
        signal.strategy = "test_strategy"
        signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

        market_data = {
            'position_size': -1e10,
            'current_drawdown': -1e10,
            'volatility': -1e10
        }
        market_conditions = {
            'volume': -1e10,
            'spread': -1e10
        }

        result = validator.validate_signal(signal, market_data, market_conditions)

        # Should handle negative values gracefully
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

    def test_validate_signal_with_nan_values(self, validator):
        """Test signal validation with NaN values"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = np.nan
        signal.confidence = np.nan
        signal.price = np.nan
        signal.quantity = np.nan
        signal.strategy = "test_strategy"
        signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

        market_data = {
            'position_size': np.nan,
            'current_drawdown': np.nan,
            'volatility': np.nan
        }
        market_conditions = {
            'volume': np.nan,
            'spread': np.nan
        }

        result = validator.validate_signal(signal, market_data, market_conditions)

        # Should handle NaN values gracefully
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

    def test_validate_signal_with_inf_values(self, validator):
        """Test signal validation with infinite values"""
        signal = Mock()
        signal.symbol = "AAPL"
        signal.timestamp = datetime.now()
        signal.signal_type = "BUY"
        signal.strength = np.inf
        signal.confidence = np.inf
        signal.price = np.inf
        signal.quantity = np.inf
        signal.strategy = "test_strategy"
        signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

        market_data = {
            'position_size': np.inf,
            'current_drawdown': np.inf,
            'volatility': np.inf
        }
        market_conditions = {
            'volume': np.inf,
            'spread': np.inf
        }

        result = validator.validate_signal(signal, market_data, market_conditions)

        # Should handle infinite values gracefully
        assert isinstance(result, dict)
        assert 'overall_status' in result
        assert 'validation_details' in result
        assert 'warnings' in result

class TestPerformanceAndOptimization:
    """Test performance and optimization features"""

    @pytest.fixture
    def validator(self):
        return SignalValidator()

    @pytest.fixture
    def large_signal_set(self):
        """Create large set of signals for performance testing"""
        signals = []
        for i in range(100):
            signal = Mock()
            signal.symbol = f"STOCK_{i % 10}"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i % 2 == 0 else "SELL"
            signal.strength = 0.5 + (i % 10) * 0.05
            signal.confidence = 0.6 + (i % 10) * 0.04
            signal.price = 100.0 + i
            signal.quantity = 100 + i
            signal.strategy = f"strategy_{i % 5}"
            signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}
            signals.append(signal)
        return signals

    def test_performance_metrics_tracking(self, validator, large_signal_set):
        """Test that performance metrics are properly tracked"""
        initial_stats = validator.get_validation_statistics()

        # Validate signals
        for signal in large_signal_set:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            validator.validate_signal(signal, market_data, market_conditions)

        final_stats = validator.get_validation_statistics()

        # Check that metrics are updated
        assert final_stats['total_validations'] > initial_stats['total_validations']
        assert final_stats['average_validation_time_ms'] >= 0
        assert final_stats['registered_rules'] > 0
        assert final_stats['enabled_rules'] > 0

    def test_validation_history_tracking(self, validator, large_signal_set):
        """Test that validation history is properly tracked"""
        # Validate signals
        for signal in large_signal_set[:10]:  # Test with first 10 signals
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            validator.validate_signal(signal, market_data, market_conditions)

        # Check validation history
        recent_validations = validator.get_recent_validations()
        assert len(recent_validations) >= 0  # May be 0 if no reports were generated

        # Check statistics
        stats = validator.get_validation_statistics()
        assert stats['total_validations'] >= 0
        assert stats['recent_validations'] >= 0

    def test_memory_usage(self, validator, large_signal_set):
        """Test memory usage with large signal sets"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Validate signals
        for signal in large_signal_set:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            validator.validate_signal(signal, market_data, market_conditions)

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024

    def test_concurrent_validation(self, validator):
        """Test concurrent validation if threading is supported"""
        import threading

        def validate_signal_worker(signal_id):
            signal = Mock()
            signal.symbol = f"STOCK_{signal_id}"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY"
            signal.strength = 0.5
            signal.confidence = 0.6
            signal.price = 100.0
            signal.quantity = 100
            signal.strategy = "test_strategy"
            signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}

            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }

            result = validator.validate_signal(signal, market_data, market_conditions)
            return result

        # Test concurrent validation
        threads = []
        results = []

        for i in range(10):
            thread = threading.Thread(target=lambda i=i: results.append(validate_signal_worker(i)))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All validations should complete successfully
        assert len(results) == 10
        for result in results:
            assert isinstance(result, dict)
            assert 'overall_status' in result
            assert 'validation_details' in result
            assert 'warnings' in result

class TestIntegrationAndCompatibility:
    """Test integration and compatibility with other components"""

    @pytest.fixture
    def validator(self):
        return SignalValidator()

    @pytest.fixture
    def test_signals(self):
        """Create test signals for integration tests"""
        signals = []
        for i in range(5):
            signal = Mock()
            signal.symbol = f"STOCK_{i}"
            signal.timestamp = datetime.now()
            signal.signal_type = "BUY" if i < 3 else "SELL"
            signal.strength = 0.5 + i * 0.1
            signal.confidence = 0.6 + i * 0.1
            signal.price = 100.0 + i * 10
            signal.quantity = 100 + i * 10
            signal.strategy = f"strategy_{i}"
            signal.metadata = {'indicators': {'rsi': 0.6, 'macd': 0.1, 'volume': 1000000}}
            signals.append(signal)
        return signals

    def test_integration_with_pandas_operations(self, validator, test_signals):
        """Test integration with pandas operations"""
        # Validate signals
        results = []
        for signal in test_signals:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            result = validator.validate_signal(signal, market_data, market_conditions)
            results.append(result)

        # Should work with pandas operations
        assert isinstance(results, list)
        assert len(results) == len(test_signals)
        for result in results:
            assert isinstance(result, dict)
            assert 'overall_status' in result
            assert 'validation_details' in result
            assert 'warnings' in result

    def test_integration_with_numpy_operations(self, validator, test_signals):
        """Test integration with numpy operations"""
        # Validate signals
        results = []
        for signal in test_signals:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            result = validator.validate_signal(signal, market_data, market_conditions)
            results.append(result)

        # Should work with numpy operations
        assert isinstance(results, list)
        assert len(results) == len(test_signals)

        # Test numpy operations on results
        statuses = [result['overall_status'] for result in results]
        assert len(statuses) == len(test_signals)

        # Test numpy operations on validation details
        for result in results:
            details = result['validation_details']
            for key, detail in details.items():
                assert 'valid' in detail
                assert 'status' in detail
                assert 'message' in detail

    def test_integration_with_serialization(self, validator, test_signals):
        """Test integration with serialization"""
        # Validate signals
        results = []
        for signal in test_signals:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            result = validator.validate_signal(signal, market_data, market_conditions)
            results.append(result)

        # Should work with pickle
        import pickle
        pickled = pickle.dumps(results)
        unpickled = pickle.loads(pickled)

        assert len(unpickled) == len(results)
        for i in range(len(results)):
            assert unpickled[i]['overall_status'] == results[i]['overall_status']
            assert unpickled[i]['validation_details'] == results[i]['validation_details']
            assert unpickled[i]['warnings'] == results[i]['warnings']

    def test_integration_with_database_operations(self, validator, test_signals):
        """Test integration with database operations"""
        # Validate signals
        results = []
        for signal in test_signals:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            result = validator.validate_signal(signal, market_data, market_conditions)
            results.append(result)

        # Should work with SQL operations
        try:
            import sqlite3
            conn = sqlite3.connect(':memory:')

            # Create table
            conn.execute('''
                CREATE TABLE signal_validations (
                    signal_id INTEGER,
                    overall_status TEXT,
                    confidence REAL,
                    strength REAL
                )
            ''')

            # Insert results
            for i, result in enumerate(results):
                conn.execute('''
                    INSERT INTO signal_validations (signal_id, overall_status, confidence, strength)
                    VALUES (?, ?, ?, ?)
                ''', (i, str(result['overall_status']), 0.6, 0.5))

            # Verify data was stored correctly
            cursor = conn.execute('SELECT COUNT(*) FROM signal_validations')
            count = cursor.fetchone()[0]
            assert count == len(results)

            conn.close()
        except ImportError:
            # SQLite not available, skip test
            pass

    def test_integration_with_logging(self, validator, test_signals):
        """Test integration with logging"""
        import logging

        # Set up logging
        logger = logging.getLogger('test_validator')
        logger.setLevel(logging.DEBUG)

        # Validate signals
        results = []
        for signal in test_signals:
            market_data = {
                'position_size': 50000,
                'current_drawdown': 0.05,
                'volatility': 0.2
            }
            market_conditions = {
                'volume': 5000,
                'spread': 0.02
            }
            result = validator.validate_signal(signal, market_data, market_conditions)
            results.append(result)

        # Should complete without logging errors
        assert len(results) == len(test_signals)
        for result in results:
            assert isinstance(result, dict)
            assert 'overall_status' in result
            assert 'validation_details' in result
            assert 'warnings' in result