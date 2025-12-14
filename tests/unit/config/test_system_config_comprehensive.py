"""
Comprehensive unit tests for system_config.py
Tests BacktestConfig and SystemConfig methods for complete coverage
"""
import json
import tempfile
from pathlib import Path
from core_engine.config.system_config import (
    SystemConfig,
    BacktestConfig,
    BacktestMode
)

class TestSystemConfig:
    """Test suite for SystemConfig class."""

    def test_from_dict(self):
        """Test creating SystemConfig from dictionary."""
        config_dict = {
            "max_components": 50,
            "health_check_interval": 60,
            "log_level": "DEBUG"
        }
        config = SystemConfig.from_dict(config_dict)
        assert config.max_components == 50
        assert config.health_check_interval == 60
        assert config.log_level == "DEBUG"

class TestBacktestConfig:
    """Comprehensive test suite for BacktestConfig class."""

    def test_initialization_defaults(self):
        """Test BacktestConfig initialization with defaults."""
        config = BacktestConfig(backtest_name="Test")
        assert config.backtest_name == "Test"
        assert config.backtest_mode == BacktestMode.SINGLE_STRATEGY
        assert config.symbols == []
        assert config.start_date == ""
        assert config.end_date == ""
        assert config.interval == "1min"
        assert config.initial_capital == 1_000_000.0
        assert config.max_position_size == 0.10
        assert config.enable_regime_adjustments is True

    def test_validate_empty_symbols(self):
        """Test validation fails with empty symbols."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=[],
            start_date="2024-01-01",
            end_date="2024-01-02"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "Must specify at least one symbol" in errors

    def test_validate_missing_dates(self):
        """Test validation fails with missing dates."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="",
            end_date=""
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "Must specify start_date and end_date" in errors

    def test_validate_invalid_date_format(self):
        """Test validation fails with invalid date format."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="invalid-date",
            end_date="2024-01-02"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("Invalid date format" in err for err in errors)

    def test_validate_end_before_start(self):
        """Test validation fails when end_date is before start_date."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-02",
            end_date="2024-01-01"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "end_date must be after start_date" in errors

    def test_validate_end_equals_start(self):
        """Test validation fails when end_date equals start_date."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-01"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "end_date must be after start_date" in errors

    def test_validate_invalid_interval(self):
        """Test validation fails with invalid interval."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            interval="invalid"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("Invalid interval" in err for err in errors)

    def test_validate_valid_intervals(self):
        """Test validation accepts valid intervals."""
        valid_intervals = ["1min", "5min", "15min", "30min", "1H", "1D"]
        for interval in valid_intervals:
            config = BacktestConfig(
                backtest_name="Test",
                symbols=["AAPL"],
                start_date="2024-01-01",
                end_date="2024-01-02",
                interval=interval
            )
            is_valid, errors = config.validate()
            assert is_valid is True, f"Interval {interval} should be valid"

    def test_validate_zero_capital(self):
        """Test validation fails with zero capital."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            initial_capital=0.0
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "initial_capital must be positive" in errors

    def test_validate_negative_capital(self):
        """Test validation fails with negative capital."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            initial_capital=-1000.0
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "initial_capital must be positive" in errors

    def test_validate_position_size_out_of_range(self):
        """Test validation fails with position size out of range."""
        # Test > 1.0
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            max_position_size=1.5
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "max_position_size must be between 0 and 1" in errors

        # Test = 0.0
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            max_position_size=0.0
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "max_position_size must be between 0 and 1" in errors

    def test_validate_daily_var_out_of_range(self):
        """Test validation fails with daily var out of range."""
        # Test > 1.0
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            max_daily_var=1.5
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "max_daily_var must be between 0 and 1" in errors

        # Test = 0.0
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            max_daily_var=0.0
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "max_daily_var must be between 0 and 1" in errors

    def test_validate_liquidity_score_out_of_range(self):
        """Test validation fails with liquidity score out of range."""
        # Test > 100.0
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            min_liquidity_score=150.0
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert "min_liquidity_score must be between 0 and 100" in errors

    def test_validate_invalid_impact_model(self):
        """Test validation fails with invalid impact model."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            impact_model="invalid_model"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("Invalid impact_model" in err for err in errors)

    def test_validate_valid_impact_models(self):
        """Test validation accepts valid impact models."""
        valid_models = ["almgren_chriss", "kyle_lambda", "simple"]
        for model in valid_models:
            config = BacktestConfig(
                backtest_name="Test",
                symbols=["AAPL"],
                start_date="2024-01-01",
                end_date="2024-01-02",
                impact_model=model
            )
            is_valid, errors = config.validate()
            assert is_valid is True, f"Impact model {model} should be valid"

    def test_validate_invalid_metrics_frequency(self):
        """Test validation fails with invalid metrics frequency."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            metrics_calculation_frequency="invalid"
        )
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("Invalid metrics_calculation_frequency" in err for err in errors)

    def test_validate_valid_metrics_frequencies(self):
        """Test validation accepts valid metrics frequencies."""
        valid_frequencies = ["real_time", "end_of_day", "end_of_backtest"]
        for frequency in valid_frequencies:
            config = BacktestConfig(
                backtest_name="Test",
                symbols=["AAPL"],
                start_date="2024-01-01",
                end_date="2024-01-02",
                metrics_calculation_frequency=frequency
            )
            is_valid, errors = config.validate()
            assert is_valid is True, f"Metrics frequency {frequency} should be valid"

    def test_validate_success(self):
        """Test validation succeeds with valid config."""
        config = BacktestConfig(
            backtest_name="Test",
            symbols=["AAPL", "TSLA"],
            start_date="2024-01-01",
            end_date="2024-01-02",
            interval="1min",
            initial_capital=1000000.0,
            max_position_size=0.1,
            max_daily_var=0.05,
            min_liquidity_score=60.0,
            impact_model="almgren_chriss",
            metrics_calculation_frequency="end_of_day"
        )
        is_valid, errors = config.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_from_dict_string_mode(self):
        """Test from_dict with string backtest_mode (should convert to enum)."""
        config_dict = {
            "backtest_name": "Test",
            "backtest_mode": "multi_strategy",
            "symbols": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        config = BacktestConfig.from_dict(config_dict)
        assert config.backtest_mode == BacktestMode.MULTI_STRATEGY
        assert isinstance(config.backtest_mode, BacktestMode)

    def test_from_dict_enum_mode(self):
        """Test from_dict with enum backtest_mode (should keep as enum)."""
        config_dict = {
            "backtest_name": "Test",
            "backtest_mode": BacktestMode.REGIME_ADAPTIVE,
            "symbols": ["AAPL"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        config = BacktestConfig.from_dict(config_dict)
        assert config.backtest_mode == BacktestMode.REGIME_ADAPTIVE

    def test_from_json(self):
        """Test from_json loads config from JSON file."""
        config_dict = {
            "backtest_name": "JSON Test",
            "backtest_mode": "single_strategy",
            "symbols": ["AAPL", "TSLA"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "interval": "5min",
            "initial_capital": 2000000.0
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_dict, f)
            json_path = f.name

        try:
            config = BacktestConfig.from_json(json_path)
            assert config.backtest_name == "JSON Test"
            assert config.backtest_mode == BacktestMode.SINGLE_STRATEGY
            assert config.symbols == ["AAPL", "TSLA"]
            assert config.start_date == "2024-01-01"
            assert config.end_date == "2024-01-02"
            assert config.interval == "5min"
            assert config.initial_capital == 2000000.0
        finally:
            Path(json_path).unlink()

    def test_to_dict(self):
        """Test to_dict converts config to dictionary."""
        config = BacktestConfig(
            backtest_name="Test",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02"
        )
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["backtest_name"] == "Test"
        assert config_dict["backtest_mode"] == "single_strategy"  # Enum converted to value
        assert config_dict["symbols"] == ["AAPL"]

    def test_to_dict_with_enums(self):
        """Test to_dict properly handles enum fields."""
        config = BacktestConfig(
            backtest_name="Test",
            backtest_mode=BacktestMode.REGIME_ADAPTIVE,
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-01-02"
        )
        config_dict = config.to_dict()
        assert config_dict["backtest_mode"] == "regime_adaptive"
        assert isinstance(config_dict["backtest_mode"], str)

    def test_str_representation(self):
        """Test __str__ generates human-readable summary."""
        config = BacktestConfig(
            backtest_name="My Backtest",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            symbols=["AAPL", "TSLA", "NVDA"],
            start_date="2024-01-01",
            end_date="2024-12-31",
            initial_capital=5_000_000.0,
            output_directory="results"
        )
        summary = str(config)
        assert "My Backtest" in summary
        assert "single_strategy" in summary
        assert "2024-01-01" in summary
        assert "2024-12-31" in summary
        assert "AAPL" in summary
        assert "TSLA" in summary
        assert "NVDA" in summary
        assert "$5,000,000" in summary
        assert "results" in summary

