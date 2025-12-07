"""
Unit tests for broker configuration classes.
Tests all broker config classes with comprehensive validation.

Author: StatArb_Gemini Configuration Testing
Date: October 29, 2025
Version: 1.0.0
"""

from dataclasses import asdict
from unittest.mock import patch

from core_engine.config.broker_config import (
    AlpacaConfig,
    InteractiveBrokersConfig,
    BrokerConfig,
    BrokerConfigLoader,
    RiskLimits,
    TradingMode,
    BrokerType
)


class TestAlpacaConfig:
    """Test suite for AlpacaConfig class."""

    def test_initialization(self):
        """Test AlpacaConfig initialization with required parameters."""
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://paper-api.alpaca.markets"
        )
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://paper-api.alpaca.markets"
        assert config.data_feed_url is None
        assert config.paper_trading is True

    def test_custom_initialization(self):
        """Test AlpacaConfig initialization with custom values."""
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://api.alpaca.markets",
            data_feed_url="https://data.alpaca.markets",
            paper_trading=False
        )
        assert config.api_key == "test_key"
        assert config.secret_key == "test_secret"
        assert config.base_url == "https://api.alpaca.markets"
        assert config.data_feed_url == "https://data.alpaca.markets"
        assert config.paper_trading is False

    def test_validation(self):
        """Test AlpacaConfig validation."""
        # Test valid config
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://paper-api.alpaca.markets"
        )
        assert config.validate() is True

        # Test missing API key
        config = AlpacaConfig(
            api_key="",
            secret_key="test_secret",
            base_url="https://paper-api.alpaca.markets"
        )
        assert config.validate() is False

        # Test missing secret key
        config = AlpacaConfig(
            api_key="test_key",
            secret_key="",
            base_url="https://paper-api.alpaca.markets"
        )
        assert config.validate() is False

    def test_to_dict(self):
        """Test AlpacaConfig to_dict conversion."""
        config = AlpacaConfig(
            api_key="test",
            secret_key="secret",
            base_url="https://paper-api.alpaca.markets"
        )
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["api_key"] == "test"
        assert config_dict["secret_key"] == "secret"
        assert config_dict["base_url"] == "https://paper-api.alpaca.markets"


class TestInteractiveBrokersConfig:
    """Test suite for InteractiveBrokersConfig class."""

    def test_initialization(self):
        """Test InteractiveBrokersConfig initialization with required parameters."""
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1
        )
        assert config.host == "127.0.0.1"
        assert config.port == 7497
        assert config.client_id == 1
        assert config.account_id is None
        assert config.paper_trading is True

    def test_custom_initialization(self):
        """Test InteractiveBrokersConfig initialization with custom values."""
        config = InteractiveBrokersConfig(
            host="192.168.1.100",
            port=7496,
            client_id=2,
            account_id="DU1234567",
            paper_trading=False
        )
        assert config.host == "192.168.1.100"
        assert config.port == 7496
        assert config.client_id == 2
        assert config.account_id == "DU1234567"
        assert config.paper_trading is False

    def test_validation(self):
        """Test InteractiveBrokersConfig validation."""
        # Test valid config
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1
        )
        assert config.validate() is True

        # Test missing host
        config = InteractiveBrokersConfig(
            host="",
            port=7497,
            client_id=1
        )
        assert config.validate() is False

        # Test missing port
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=0,
            client_id=1
        )
        assert config.validate() is False

    def test_to_dict(self):
        """Test InteractiveBrokersConfig to_dict conversion."""
        config = InteractiveBrokersConfig(
            host="test",
            port=1234,
            client_id=1
        )
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["host"] == "test"
        assert config_dict["port"] == 1234
        assert config_dict["client_id"] == 1


class TestRiskLimits:
    """Test suite for RiskLimits class."""

    def test_initialization(self):
        """Test RiskLimits initialization with defaults."""
        config = RiskLimits()
        assert config.max_position_size == 100
        assert config.max_position_value == 1000.00
        assert config.max_positions == 5
        assert config.max_orders_per_minute == 2
        assert config.max_daily_trades == 10
        assert config.max_daily_loss == 100.00
        assert config.paper_trading_only is True
        assert config.require_manual_approval is True
        assert config.enable_kill_switch is True
        assert config.alert_on_every_order is True
        assert config.log_all_activities is True

    def test_custom_initialization(self):
        """Test RiskLimits initialization with custom values."""
        config = RiskLimits(
            max_position_size=200,
            max_position_value=2000.00,
            max_positions=10,
            max_orders_per_minute=5,
            max_daily_trades=20,
            max_daily_loss=200.00,
            paper_trading_only=False,
            require_manual_approval=False,
            enable_kill_switch=False,
            alert_on_every_order=False,
            log_all_activities=False
        )
        assert config.max_position_size == 200
        assert config.max_position_value == 2000.00
        assert config.max_positions == 10
        assert config.max_orders_per_minute == 5
        assert config.max_daily_trades == 20
        assert config.max_daily_loss == 200.00
        assert config.paper_trading_only is False
        assert config.require_manual_approval is False
        assert config.enable_kill_switch is False
        assert config.alert_on_every_order is False
        assert config.log_all_activities is False

    def test_validation(self):
        """Test RiskLimits validation."""
        # Test valid config
        config = RiskLimits()
        assert config.validate() is True

        # Test invalid daily loss limit
        config = RiskLimits(max_daily_loss=2000.00)
        assert config.validate() is False

        # Test invalid position size
        config = RiskLimits(max_position_size=1000)
        assert config.validate() is False

    def test_to_dict(self):
        """Test RiskLimits to_dict conversion."""
        config = RiskLimits(max_position_size=150)
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["max_position_size"] == 150


class TestBrokerConfig:
    """Test suite for BrokerConfig class."""

    def test_initialization(self):
        """Test BrokerConfig initialization with defaults."""
        config = BrokerConfig()
        assert config.trading_mode == TradingMode.PAPER
        assert config.alpaca is None
        assert config.interactive_brokers is None
        assert config.active_broker == BrokerType.ALPACA
        assert config.risk_limits is not None
        assert config.enable_live_data is True
        assert config.enable_order_submission is True
        assert config.enable_position_tracking is True
        assert config.enable_monitoring is True

    def test_custom_initialization(self):
        """Test BrokerConfig initialization with custom values."""
        alpaca_config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://api.alpaca.markets"
        )
        risk_limits = RiskLimits(max_position_size=200)

        config = BrokerConfig(
            trading_mode=TradingMode.LIVE,
            alpaca=alpaca_config,
            active_broker=BrokerType.ALPACA,
            risk_limits=risk_limits,
            enable_live_data=False,
            enable_order_submission=False,
            enable_position_tracking=False,
            enable_monitoring=False
        )
        assert config.trading_mode == TradingMode.LIVE
        assert config.alpaca.api_key == "test_key"
        assert config.active_broker == BrokerType.ALPACA
        assert config.risk_limits.max_position_size == 200
        assert config.enable_live_data is False
        assert config.enable_order_submission is False
        assert config.enable_position_tracking is False
        assert config.enable_monitoring is False

    def test_validation(self):
        """Test BrokerConfig validation."""
        # Test with Alpaca config
        alpaca_config = AlpacaConfig(
            api_key="test_key",
            secret_key="test_secret",
            base_url="https://paper-api.alpaca.markets"
        )
        config = BrokerConfig(alpaca=alpaca_config, active_broker=BrokerType.ALPACA)
        assert config.validate() is True

        # Test with Interactive Brokers config
        ib_config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1
        )
        config = BrokerConfig(interactive_brokers=ib_config, active_broker=BrokerType.INTERACTIVE_BROKERS)
        assert config.validate() is True

    def test_to_dict(self):
        """Test BrokerConfig to_dict conversion."""
        config = BrokerConfig(active_broker=BrokerType.INTERACTIVE_BROKERS)
        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["active_broker"] == BrokerType.INTERACTIVE_BROKERS


class TestBrokerConfigLoader:
    """Test suite for BrokerConfigLoader class."""

    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        import os

        # Set environment variables
        env_vars = {
            "ALPACA_PAPER_API_KEY": "test_api_key",
            "ALPACA_PAPER_SECRET_KEY": "test_secret_key",
            "ALPACA_PAPER_BASE_URL": "https://paper-api.alpaca.markets",
            "PHASE_9_ACTIVE_BROKER": "alpaca",
            "PHASE_9_TRADING_MODE": "paper"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BrokerConfigLoader.load_from_env()

            assert config.trading_mode == TradingMode.PAPER
            assert config.active_broker == BrokerType.ALPACA
            assert config.alpaca is not None
            assert config.alpaca.api_key == "test_api_key"
            assert config.alpaca.secret_key == "test_secret_key"
            assert config.alpaca.base_url == "https://paper-api.alpaca.markets"

    def test_load_from_env_file(self):
        """Test loading configuration from specific env file."""
        import tempfile
        import os

        # Create temporary .env file
        env_content = """
ALPACA_PAPER_API_KEY=test_key
ALPACA_PAPER_SECRET_KEY=test_secret
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
PHASE_9_ACTIVE_BROKER=alpaca
PHASE_9_TRADING_MODE=paper
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            temp_file = f.name

        try:
            # Clear environment to avoid interference from actual .env file
            with patch.dict(os.environ, {}, clear=True):
                config = BrokerConfigLoader.load_from_env(temp_file)

                assert config.trading_mode == TradingMode.PAPER
                assert config.active_broker == BrokerType.ALPACA
                assert config.alpaca is not None
                assert config.alpaca.api_key == "test_key"
        finally:
            os.unlink(temp_file)

    def test_create_sample_env_file(self):
        """Test creating sample .env file."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            sample_file = os.path.join(temp_dir, ".env.sample")
            BrokerConfigLoader.create_sample_env_file(sample_file)

            assert os.path.exists(sample_file)

            with open(sample_file, 'r') as f:
                content = f.read()
                assert "ALPACA_PAPER_API_KEY" in content
                assert "PHASE_9_TRADING_MODE" in content


class TestBrokerConfigIntegration:
    """Integration tests for broker configs."""

    def test_all_broker_configs_serialization(self):
        """Test that all broker configs can be serialized to dict."""
        configs = [
            AlpacaConfig(
                api_key="test",
                secret_key="test",
                base_url="https://paper-api.alpaca.markets"
            ),
            InteractiveBrokersConfig(
                host="127.0.0.1",
                port=7497,
                client_id=1
            ),
            RiskLimits(),
            BrokerConfig()
        ]

        for config in configs:
            config_dict = asdict(config)
            assert isinstance(config_dict, dict)

    def test_broker_config_loader_integration(self):
        """Test BrokerConfigLoader with all broker types."""
        import os

        # Test Alpaca config loading
        env_vars = {
            "ALPACA_PAPER_API_KEY": "test_key",
            "ALPACA_PAPER_SECRET_KEY": "test_secret",
            "PHASE_9_ACTIVE_BROKER": "alpaca"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BrokerConfigLoader.load_from_env()
            assert config.active_broker == BrokerType.ALPACA
            assert config.validate() is True

        # Test Interactive Brokers config loading
        env_vars = {
            "IB_PAPER_HOST": "127.0.0.1",
            "IB_PAPER_PORT": "7497",
            "IB_PAPER_CLIENT_ID": "1",
            "PHASE_9_ACTIVE_BROKER": "interactive_brokers"
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BrokerConfigLoader.load_from_env()
            assert config.active_broker == BrokerType.INTERACTIVE_BROKERS
            assert config.validate() is True

    def test_broker_config_validation_consistency(self):
        """Test that all broker configs have consistent validation."""
        # Test AlpacaConfig validation
        config = AlpacaConfig(
            api_key="test",
            secret_key="test",
            base_url="https://paper-api.alpaca.markets"
        )
        assert config.validate() is True

        # Test InteractiveBrokersConfig validation
        config = InteractiveBrokersConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1
        )
        assert config.validate() is True

        # Test RiskLimits validation
        config = RiskLimits()
        assert config.validate() is True

        # Test BrokerConfig validation with Alpaca
        alpaca_config = AlpacaConfig(
            api_key="test",
            secret_key="test",
            base_url="https://paper-api.alpaca.markets"
        )
        config = BrokerConfig(alpaca=alpaca_config, active_broker=BrokerType.ALPACA)
        assert config.validate() is True

    def test_broker_config_composition(self):
        """Test that BrokerConfig properly composes other configs."""
        alpaca_config = AlpacaConfig(
            api_key="test",
            secret_key="test",
            base_url="https://paper-api.alpaca.markets"
        )
        risk_limits = RiskLimits(max_position_size=150)

        broker_config = BrokerConfig(
            alpaca=alpaca_config,
            risk_limits=risk_limits
        )

        # Test that composed configs are properly set
        assert broker_config.alpaca.api_key == "test"
        assert broker_config.risk_limits.max_position_size == 150

        # Test that composed configs can be modified
        broker_config.risk_limits.max_position_size = 200
        assert broker_config.risk_limits.max_position_size == 200
