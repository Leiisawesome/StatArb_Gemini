"""
Unit tests for papertest.utils.config_loader
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from papertest.utils.config_loader import load_config, validate_papertest_schema, _deep_merge


class TestDeepMerge:
    def test_empty_dicts(self):
        """Test merging empty dictionaries"""
        base = {}
        override = {}
        result = _deep_merge(base, override)
        assert result == {}

    def test_override_simple_values(self):
        """Test overriding simple values"""
        base = {"a": 1, "b": 2}
        override = {"a": 10, "c": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 10, "b": 2, "c": 3}

    def test_deep_merge_nested_dicts(self):
        """Test deep merging nested dictionaries"""
        base = {"nested": {"x": 1, "y": 2}}
        override = {"nested": {"x": 10, "z": 3}}
        result = _deep_merge(base, override)
        assert result == {"nested": {"x": 10, "y": 2, "z": 3}}

    def test_override_with_non_dict(self):
        """Test overriding dict with non-dict value"""
        base = {"nested": {"x": 1}}
        override = {"nested": "not_a_dict"}
        result = _deep_merge(base, override)
        assert result == {"nested": "not_a_dict"}


class TestValidatePapertestSchema:
    def test_valid_config(self):
        """Test validation of a valid config"""
        config = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                }
            }
        }
        # Should not raise
        validate_papertest_schema(config)

    def test_missing_papertest_key(self):
        """Test validation fails without papertest key"""
        config = {}
        with pytest.raises(ValueError, match="Missing top-level 'papertest' dict"):
            validate_papertest_schema(config)

    def test_invalid_papertest_type(self):
        """Test validation fails with invalid papertest type"""
        config = {"papertest": "not_a_dict"}
        with pytest.raises(ValueError, match="Missing top-level 'papertest' dict"):
            validate_papertest_schema(config)

    def test_missing_data_key(self):
        """Test validation fails without data key"""
        config = {"papertest": {}}
        with pytest.raises(ValueError, match="papertest.data missing required key"):
            validate_papertest_schema(config)

    def test_invalid_data_type(self):
        """Test validation fails with invalid data type"""
        config = {"papertest": {"data": "not_a_dict"}}
        with pytest.raises(ValueError, match="papertest.data must be a dict"):
            validate_papertest_schema(config)

    def test_missing_required_data_keys(self):
        """Test validation fails with missing required data keys"""
        config = {"papertest": {"data": {"symbols": ["AAPL"]}}}
        with pytest.raises(ValueError, match="missing required key: start_date"):
            validate_papertest_schema(config)

    def test_empty_symbols_list(self):
        """Test validation fails with empty symbols list"""
        config = {
            "papertest": {
                "data": {
                    "symbols": [],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                }
            }
        }
        with pytest.raises(ValueError, match="symbols must be a non-empty list"):
            validate_papertest_schema(config)

    def test_invalid_symbols_type(self):
        """Test validation fails with invalid symbols type"""
        config = {
            "papertest": {
                "data": {
                    "symbols": "not_a_list",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                }
            }
        }
        with pytest.raises(ValueError, match="symbols must be a non-empty list"):
            validate_papertest_schema(config)

    def test_invalid_debug_time_type(self):
        """Test validation fails with invalid debug time type"""
        config = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                },
                "debug": {
                    "start_at_time": ["not", "a", "string"]  # Should be string
                }
            }
        }
        with pytest.raises(ValueError, match="start_at_time must be a string"):
            validate_papertest_schema(config)


class TestLoadConfig:
    def test_load_config_file_not_found(self):
        """Test loading config with non-existent file"""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config("non_existent.yaml")

    def test_load_config_with_base_file_not_found(self):
        """Test loading config with non-existent base file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"papertest": {"data": {"symbols": ["AAPL"], "start_date": "2024-01-01", "end_date": "2024-01-02", "interval": "1min", "replay_speed": "REALTIME"}}}, f)
            config_path = f.name

        try:
            with pytest.raises(FileNotFoundError, match="Base config file not found"):
                load_config(config_path, "non_existent_base.yaml")
        finally:
            Path(config_path).unlink()

    def test_load_config_success(self):
        """Test successful config loading"""
        config_data = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = load_config(config_path)
            assert result == config_data
        finally:
            Path(config_path).unlink()

    def test_load_config_with_base_merge(self):
        """Test config loading with base config merge"""
        base_data = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                },
                "execution": {
                    "initial_cash": 100000.0
                }
            }
        }

        override_data = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL", "MSFT"]
                },
                "execution": {
                    "commission_per_share": 0.005
                }
            }
        }

        expected = {
            "papertest": {
                "data": {
                    "symbols": ["AAPL", "MSFT"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-02",
                    "interval": "1min",
                    "replay_speed": "REALTIME"
                },
                "execution": {
                    "initial_cash": 100000.0,
                    "commission_per_share": 0.005
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as base_f:
            yaml.dump(base_data, base_f)
            base_path = base_f.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as override_f:
            yaml.dump(override_data, override_f)
            override_path = override_f.name

        try:
            result = load_config(override_path, base_path)
            assert result == expected
        finally:
            Path(base_path).unlink()
            Path(override_path).unlink()