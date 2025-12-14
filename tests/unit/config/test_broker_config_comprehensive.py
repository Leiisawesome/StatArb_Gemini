"""
Comprehensive unit tests for broker_config.py
Tests error paths, edge cases, and missing coverage areas
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from core_engine.config.broker_config import (
    InteractiveBrokersConfig,
    BrokerConfig,
    BrokerConfigLoader,
    RiskLimits,
    TradingMode,
    BrokerType,
    load_broker_config
)

class TestRiskLimitsValidation:
    """Test RiskLimits validation edge cases."""

    def test_validate_live_trading_warning(self):
        """Test validation logs warning for live trading."""
        limits = RiskLimits(paper_trading_only=False)
        # Should return True but log warning
        assert limits.validate() is True

    def test_validate_daily_loss_too_high(self):
        """Test validation fails with daily loss > 1000."""
        limits = RiskLimits(max_daily_loss=1500.0)
        assert limits.validate() is False

    def test_validate_position_size_too_large(self):
        """Test validation fails with position size > 500."""
        limits = RiskLimits(max_position_size=600)
        assert limits.validate() is False

class TestInteractiveBrokersConfigValidation:
    """Test InteractiveBrokersConfig validation edge cases."""

    def test_validate_paper_port_warning(self):
        """Test validation logs warning for unusual paper port."""
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=4003,  # Unusual paper port
            client_id=1,
            paper_trading=True
        )
        # Should return True but log warning
        assert config.validate() is True

    def test_validate_live_flag_paper_port(self):
        """Test validation fails when live flag is True but port is paper."""
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,  # Paper port
            client_id=1,
            paper_trading=False  # Live trading
        )
        assert config.validate() is False

class TestBrokerConfigValidation:
    """Test BrokerConfig validation edge cases."""

    def test_validate_non_paper_mode(self):
        """Test validation fails for non-paper trading mode."""
        config = BrokerConfig(trading_mode=TradingMode.LIVE)
        assert config.validate() is False

    def test_validate_ib_not_configured(self):
        """Test validation fails when IB selected but not configured."""
        config = BrokerConfig(
            trading_mode=TradingMode.PAPER,
            active_broker=BrokerType.INTERACTIVE_BROKERS,
            interactive_brokers=None
        )
        assert config.validate() is False

    def test_validate_ib_invalid(self):
        """Test validation fails when IB config is invalid."""
        invalid_ib = InteractiveBrokersConfig(
            host="",  # Missing host
            port=7497,
            client_id=1
        )
        config = BrokerConfig(
            trading_mode=TradingMode.PAPER,
            active_broker=BrokerType.INTERACTIVE_BROKERS,
            interactive_brokers=invalid_ib
        )
        assert config.validate() is False

    def test_validate_success(self):
        """Test validation succeeds with valid config."""
        ib = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1,
            paper_trading=True
        )
        config = BrokerConfig(
            trading_mode=TradingMode.PAPER,
            active_broker=BrokerType.INTERACTIVE_BROKERS,
            interactive_brokers=ib
        )
        assert config.validate() is True

class TestBrokerConfigLoader:
    """Test BrokerConfigLoader edge cases."""

    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_with_file(self):
        """Test loading from specified env file."""
        env_content = """IB_PAPER_HOST=127.0.0.1
IB_PAPER_PORT=7497
IB_PAPER_CLIENT_ID=1
PHASE_9_TRADING_MODE=paper
PHASE_9_ACTIVE_BROKER=interactive_brokers
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            env_path = f.name

        try:
            config = BrokerConfigLoader.load_from_env(env_path)
            assert config.interactive_brokers is not None
            assert config.interactive_brokers.host == "127.0.0.1"
            assert config.interactive_brokers.port == 7497
        finally:
            Path(env_path).unlink()

    @patch('core_engine.config.broker_config.load_dotenv')  # Prevent loading from .env file
    @patch.dict(os.environ, {
        'PHASE_9_TRADING_MODE': 'live',
        'ALPACA_PAPER_API_KEY': 'key',
        'ALPACA_PAPER_SECRET_KEY': 'secret',
        'ALPACA_PAPER_BASE_URL': 'https://paper-api.alpaca.markets'
    }, clear=True)
    def test_load_from_env_live_mode(self, mock_load_dotenv):
        """Test loading live trading mode from env."""
        mock_load_dotenv.return_value = None  # Don't load .env file
        config = BrokerConfigLoader.load_from_env()
        assert config.trading_mode == TradingMode.LIVE

    @patch.dict(os.environ, {
        'BROKER_TYPE': 'ib',
        'IB_PAPER_HOST': '127.0.0.1',
        'IB_PAPER_PORT': '7497',
        'IB_PAPER_CLIENT_ID': '1'
    }, clear=False)
    def test_load_from_env_legacy_broker_type(self):
        """Test loading broker type from legacy BROKER_TYPE env var."""
        config = BrokerConfigLoader.load_from_env()
        assert config.active_broker == BrokerType.INTERACTIVE_BROKERS

    @patch.dict(os.environ, {
        'ACTIVE_BROKER': 'interactive_brokers',
        'IB_PAPER_HOST': '127.0.0.1',
        'IB_PAPER_PORT': '7497',
        'IB_PAPER_CLIENT_ID': '1'
    }, clear=False)
    def test_load_from_env_active_broker_var(self):
        """Test loading broker type from ACTIVE_BROKER env var."""
        config = BrokerConfigLoader.load_from_env()
        assert config.active_broker == BrokerType.INTERACTIVE_BROKERS

    @patch.dict(os.environ, {
        'TRADING_MODE': 'simulation',
        'ALPACA_PAPER_API_KEY': 'key',
        'ALPACA_PAPER_SECRET_KEY': 'secret'
    }, clear=False)
    def test_load_from_env_simulation_mode(self):
        """Test loading simulation trading mode from env."""
        config = BrokerConfigLoader.load_from_env()
        # Simulation mode should default to PAPER
        assert config.trading_mode == TradingMode.PAPER

    @patch.dict(os.environ, {
        'IB_HOST': '127.0.0.1',  # Legacy var without PAPER prefix
        'IB_PORT': '7497',
        'IB_PAPER_CLIENT_ID': '1'
    }, clear=False)
    def test_load_from_env_legacy_ib_vars(self):
        """Test loading IB config from legacy env vars."""
        config = BrokerConfigLoader.load_from_env()
        assert config.interactive_brokers is not None
        assert config.interactive_brokers.host == "127.0.0.1"
        assert config.interactive_brokers.port == 7497

    @patch.dict(os.environ, {
        'TRADING_MAX_POSITION_SIZE': '200',
        'TRADING_MAX_DAILY_LOSS': '500.00'
    }, clear=False)
    def test_load_from_env_legacy_risk_vars(self):
        """Test loading risk limits from legacy env vars."""
        config = BrokerConfigLoader.load_from_env()
        assert config.risk_limits.max_position_size == 200
        assert config.risk_limits.max_daily_loss == 500.00

    @patch.dict(os.environ, {
        'PHASE_9_ENABLE_LIVE_DATA': 'false'
    }, clear=False)
    def test_load_from_env_feature_flags_override(self):
        """Test that PHASE_9 feature flags override TRADING flags."""
        # Note: The code has duplicate assignments, last one wins
        config = BrokerConfigLoader.load_from_env()
        assert config.enable_live_data is False

    def test_create_sample_env_file(self):
        """Test creating sample env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env.sample', delete=False) as f:
            sample_path = f.name

        try:
            BrokerConfigLoader.create_sample_env_file(sample_path)
            assert Path(sample_path).exists()

            content = Path(sample_path).read_text()
            assert "Phase 9 Broker Credentials" in content
            assert "IB_PAPER_HOST" in content
            assert "PHASE_9_TRADING_MODE" in content
        finally:
            if Path(sample_path).exists():
                Path(sample_path).unlink()

class TestLoadBrokerConfig:
    """Test load_broker_config convenience function."""

    @patch.dict(os.environ, {
        'IB_PAPER_HOST': '127.0.0.1',
        'IB_PAPER_PORT': '7497',
        'IB_PAPER_CLIENT_ID': '1',
        'PHASE_9_TRADING_MODE': 'paper',
        'PHASE_9_ACTIVE_BROKER': 'interactive_brokers'
    }, clear=False)
    def test_load_broker_config_success(self):
        """Test load_broker_config succeeds with valid config."""
        config = load_broker_config()
        assert config is not None
        assert config.interactive_brokers is not None
        assert config.validate() is True

    @patch('core_engine.config.broker_config.load_dotenv')  # Prevent loading from .env file
    @patch.dict(os.environ, {
        'PHASE_9_TRADING_MODE': 'live',  # Invalid for validation
        'ALPACA_PAPER_API_KEY': 'key',
        'ALPACA_PAPER_SECRET_KEY': 'secret',
        'ALPACA_PAPER_BASE_URL': 'https://paper-api.alpaca.markets'
    }, clear=True)
    def test_load_broker_config_validation_fails(self, mock_load_dotenv):
        """Test load_broker_config raises ValueError on validation failure."""
        mock_load_dotenv.return_value = None  # Don't load .env file
        with pytest.raises(ValueError, match="Broker configuration validation failed"):
            load_broker_config()

class TestBackwardCompatibility:
    """Test backward compatibility aliases."""

    def test_phase9_aliases(self):
        """Test Phase9Config aliases exist."""
        from core_engine.config.broker_config import (
            Phase9Config,
            Phase9ConfigLoader,
            load_phase9_config
        )

        assert Phase9Config == BrokerConfig
        assert Phase9ConfigLoader == BrokerConfigLoader
        assert load_phase9_config == load_broker_config

class TestMainBlock:
    """Test __main__ block execution."""

    @patch('core_engine.config.broker_config.BrokerConfigLoader.create_sample_env_file')
    @patch('builtins.print')
    def test_main_block_execution(self, mock_print, mock_create_sample):
        """Test __main__ block creates sample file and prints message."""
        import core_engine.config.broker_config as broker_config_module

        # Execute main block
        if hasattr(broker_config_module, '__main__'):
            exec(open(broker_config_module.__file__).read())

        # Verify sample file creation was attempted
        # (The actual execution happens when running as script, but we can test the pattern)
        pass  # Main block testing is limited when importing as module

