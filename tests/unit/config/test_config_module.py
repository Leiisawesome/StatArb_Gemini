"""
Unit tests for config component.
Tests config classes, unified configuration management, and configuration loading.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

# Import config classes
from core_engine.config.component_config import (
    DataConfig,
    RiskConfig,
    ProcessingConfig
)

from core_engine.config.system_config import SystemConfig

from core_engine.config.unified_config import (
    UnifiedConfig,
    ConfigFormat,
    ConfigSource,
    get_config,
    init_config,
    config_get,
    config_set,
    config_section
)

class TestDataConfig:
    """Test suite for DataConfig class."""

    def test_initialization(self):
        """Test DataConfig initialization with defaults."""
        config = DataConfig()
        assert config.symbols == ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ']
        assert config.start_date is None
        assert config.end_date is None
        assert config.caching.enable_caching is True
        assert config.caching.cache_ttl == 300

    def test_custom_initialization(self):
        """Test DataConfig initialization with custom values."""
        config = DataConfig(
            symbols=["AAPL", "GOOGL"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        assert config.symbols == ["AAPL", "GOOGL"]
        assert config.start_date == "2024-01-01"
        assert config.end_date == "2024-01-31"
        assert config.caching.enable_caching is True  # Default from CachingConfig
        assert config.caching.cache_ttl == 300  # Default from CachingConfig

class TestRiskConfig:
    """Test suite for RiskConfig class."""

    def test_initialization(self):
        """Test RiskConfig initialization with defaults."""
        config = RiskConfig()
        assert config.position_limits.max_position_size == 0.10
        assert config.risk_limits.max_daily_var == 0.05
        assert config.auto_approval_threshold == 0.01
        assert config.elevated_review_threshold == 0.05

    def test_custom_initialization(self):
        """Test RiskConfig initialization with custom values."""
        from core_engine.config.component_config import PositionLimits, RiskLimits

        config = RiskConfig(
            position_limits=PositionLimits(max_position_size=0.05),
            risk_limits=RiskLimits(max_daily_var=0.03),
            auto_approval_threshold=0.005,
            elevated_review_threshold=0.03
        )
        assert config.position_limits.max_position_size == 0.05
        assert config.risk_limits.max_daily_var == 0.03
        assert config.auto_approval_threshold == 0.005
        assert config.elevated_review_threshold == 0.03

class TestProcessingConfig:
    """Test suite for ProcessingConfig class."""

    def test_initialization(self):
        """Test ProcessingConfig initialization with defaults."""
        config = ProcessingConfig()
        assert config.signal_threshold == 0.6
        assert config.feature_normalization == "robust"
        assert config.enable_cross_sectional is True

    def test_custom_initialization(self):
        """Test ProcessingConfig initialization with custom values."""
        config = ProcessingConfig(
            signal_threshold=0.8,
            feature_normalization="standard",
            enable_cross_sectional=False
        )
        assert config.signal_threshold == 0.8
        assert config.feature_normalization == "standard"
        assert config.enable_cross_sectional is False

class TestSystemConfig:
    """Test suite for SystemConfig class."""

    def test_initialization(self):
        """Test SystemConfig initialization with defaults."""
        config = SystemConfig()
        assert config.max_components == 100
        assert config.health_check_interval == 30
        assert config.initialization_timeout == 60
        assert config.log_level == "INFO"
        assert config.max_concurrent_operations == 50
        assert config.operation_timeout == 300

    def test_custom_initialization(self):
        """Test SystemConfig initialization with custom values."""
        config = SystemConfig(
            max_components=200,
            health_check_interval=60,
            log_level="DEBUG",
            max_concurrent_operations=100
        )
        assert config.max_components == 200
        assert config.health_check_interval == 60
        assert config.log_level == "DEBUG"
        assert config.max_concurrent_operations == 100

    def test_from_dict(self):
        """Test creating SystemConfig from dictionary."""
        config_dict = {
            "max_components": 150,
            "health_check_interval": 45,
            "log_level": "WARNING",
            "max_concurrent_operations": 75
        }
        config = SystemConfig.from_dict(config_dict)
        assert config.max_components == 150
        assert config.health_check_interval == 45
        assert config.log_level == "WARNING"
        assert config.max_concurrent_operations == 75

class TestUnifiedConfig:
    """Test suite for UnifiedConfig class."""

    def test_initialization(self):
        """Test UnifiedConfig initialization."""
        config = UnifiedConfig()
        assert config.sources == []
        assert config._config == {}
        assert config._loaded is False

    def test_add_source(self):
        """Test adding configuration sources."""
        config = UnifiedConfig()
        config.add_source("/path/to/config.yaml", ConfigFormat.YAML, priority=100)

        assert len(config.sources) == 1
        assert config.sources[0].path == Path("/path/to/config.yaml")
        assert config.sources[0].format == ConfigFormat.YAML
        assert config.sources[0].priority == 100

    def test_add_env_source(self):
        """Test adding environment variable source."""
        config = UnifiedConfig()
        config.add_env_source("TEST_PREFIX", priority=200)

        assert len(config.sources) == 1
        assert config.sources[0].format == ConfigFormat.ENV
        assert config.sources[0].priority == 200

    def test_source_priority_sorting(self):
        """Test that sources are sorted by priority."""
        config = UnifiedConfig()
        config.add_source("low.yaml", ConfigFormat.YAML, priority=50)
        config.add_source("high.yaml", ConfigFormat.YAML, priority=100)
        config.add_source("medium.yaml", ConfigFormat.YAML, priority=75)

        assert len(config.sources) == 3
        assert config.sources[0].priority == 100  # Highest first
        assert config.sources[1].priority == 75
        assert config.sources[2].priority == 50

    @patch('builtins.open', new_callable=mock_open, read_data='key: value\nnested:\n  subkey: subvalue')
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_yaml_config(self, mock_exists, mock_file):
        """Test loading YAML configuration."""
        config = UnifiedConfig()
        config.add_source("test.yaml", ConfigFormat.YAML)

        result = config.load()

        assert result == {"key": "value", "nested": {"subkey": "subvalue"}}
        assert config._loaded is True

    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value", "nested": {"subkey": "subvalue"}}')
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_json_config(self, mock_exists, mock_file):
        """Test loading JSON configuration."""
        config = UnifiedConfig()
        config.add_source("test.json", ConfigFormat.JSON)

        result = config.load()

        assert result == {"key": "value", "nested": {"subkey": "subvalue"}}
        assert config._loaded is True

    @patch.dict(os.environ, {'TEST_PREFIX_KEY': 'value', 'TEST_PREFIX_NESTED_SUBKEY': 'subvalue'})
    def test_load_env_config(self):
        """Test loading environment variable configuration."""
        config = UnifiedConfig()
        config.add_env_source("TEST_PREFIX")

        result = config.load()

        assert result == {"key": "value", "nested": {"subkey": "subvalue"}}

    def test_deep_merge(self):
        """Test deep merging of configurations."""
        config = UnifiedConfig()

        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}, "e": 4}

        result = config._deep_merge(base, override)

        assert result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

    def test_get_value(self):
        """Test getting configuration values."""
        config = UnifiedConfig()
        config._config = {"database": {"host": "localhost", "port": 5432}}
        config._loaded = True

        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432
        assert config.get("database.user", "default") == "default"
        assert config.get("nonexistent", "default") == "default"

    def test_set_value(self):
        """Test setting configuration values."""
        config = UnifiedConfig()
        config._loaded = True

        config.set("database.host", "remotehost")
        config.set("new.deep.nested", "value")

        assert config._config["database"]["host"] == "remotehost"
        assert config._config["new"]["deep"]["nested"] == "value"

    def test_get_section(self):
        """Test getting configuration sections."""
        config = UnifiedConfig()
        config._config = {"database": {"host": "localhost", "port": 5432}, "api": {"url": "http://api.example.com"}}
        config._loaded = True

        db_section = config.get_section("database")
        assert db_section == {"host": "localhost", "port": 5432}

        api_section = config.get_section("api")
        assert api_section == {"url": "http://api.example.com"}

        nonexistent = config.get_section("nonexistent")
        assert nonexistent == {}

    def test_reload(self):
        """Test configuration reloading."""
        config = UnifiedConfig()
        config._config = {"old": "value"}
        config._loaded = True

        # Add a source that would load new config
        config.sources = [ConfigSource(path=None, format=ConfigFormat.ENV)]

        with patch.object(config, '_load_env_config', return_value={"new": "value"}):
            result = config.reload()

            assert result == {"new": "value"}
            assert config._loaded is True

    def test_convert_value(self):
        """Test value type conversion."""
        config = UnifiedConfig()

        assert config._convert_value("true") is True
        assert config._convert_value("false") is False
        assert config._convert_value("42") == 42
        assert config._convert_value("3.14") == 3.14
        assert config._convert_value("hello") == "hello"

class TestGlobalConfigFunctions:
    """Test suite for global configuration functions."""

    def test_get_config(self):
        """Test getting global config instance."""
        config = get_config()
        assert isinstance(config, UnifiedConfig)

    def test_init_config(self):
        """Test initializing global configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config files
            config_dir = Path(temp_dir)
            (config_dir / "config.yaml").write_text("test: value")

            # Store original config
            from core_engine.config.unified_config import _config as original_config

            try:
                result = init_config(config_dir, "TEST_PREFIX")

                # Verify the function returns a UnifiedConfig instance
                assert isinstance(result, UnifiedConfig)

                # Verify sources were added
                assert len(result.sources) > 0

                # Check that base config file source was added
                yaml_sources = [s for s in result.sources if s.format == ConfigFormat.YAML]
                assert len(yaml_sources) >= 2  # base config and env-specific

            finally:
                # Restore original config
                import core_engine.config.unified_config
                core_engine.config.unified_config._config = original_config

    def test_config_get(self):
        """Test global config_get function."""
        with patch('core_engine.config.unified_config.get_config') as mock_get_config:
            mock_config = mock_get_config.return_value
            mock_config.get.return_value = "test_value"

            result = config_get("test.key")
            assert result == "test_value"
            mock_config.get.assert_called_with("test.key", None)

    def test_config_set(self):
        """Test global config_set function."""
        with patch('core_engine.config.unified_config.get_config') as mock_get_config:
            mock_config = mock_get_config.return_value

            config_set("test.key", "test_value")
            mock_config.set.assert_called_with("test.key", "test_value")

    def test_config_section(self):
        """Test global config_section function."""
        with patch('core_engine.config.unified_config.get_config') as mock_get_config:
            mock_config = mock_get_config.return_value
            mock_config.get_section.return_value = {"key": "value"}

            result = config_section("database")
            assert result == {"key": "value"}
            mock_config.get_section.assert_called_with("database")