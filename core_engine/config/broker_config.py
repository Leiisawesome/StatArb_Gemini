"""
Broker Configuration Management
Secure credential loading and broker configuration for live trading integration
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Trading mode enumeration"""
    PAPER = "paper"
    LIVE = "live"
    SIMULATION = "simulation"

class BrokerType(Enum):
    """Supported broker types"""
    INTERACTIVE_BROKERS = "interactive_brokers"
    ALPACA = "alpaca"

@dataclass
class RiskLimits:
    """Broker integration risk limits configuration"""
    # Position limits
    max_position_size: int = 100  # shares
    max_position_value: float = 1000.00  # USD
    max_positions: int = 5

    # Trading limits
    max_orders_per_minute: int = 2
    max_daily_trades: int = 10
    max_daily_loss: float = 100.00  # USD

    # Safety flags
    paper_trading_only: bool = True
    require_manual_approval: bool = True
    enable_kill_switch: bool = True

    # Monitoring
    alert_on_every_order: bool = True
    log_all_activities: bool = True

    def validate(self) -> bool:
        """Validate risk limits are safe"""
        if not self.paper_trading_only:
            logger.warning("⚠️ LIVE TRADING MODE - Exercise extreme caution!")

        if self.max_daily_loss > 1000.00:
            logger.error("Daily loss limit too high for Phase 9!")
            return False

        if self.max_position_size > 500:
            logger.error("Position size too large for Phase 9!")
            return False

        return True

@dataclass
class InteractiveBrokersConfig:
    """Interactive Brokers configuration"""
    host: str
    port: int
    client_id: int
    account_id: Optional[str] = None
    paper_trading: bool = True

    def validate(self) -> bool:
        """Validate IB configuration"""
        if not self.host or not self.port:
            logger.error("IB connection details missing!")
            return False

        if self.paper_trading and self.port not in [7497, 4002]:
            logger.warning(f"Paper trading port {self.port} unusual (expected 7497 or 4002)")

        if not self.paper_trading and self.port in [7497, 4002]:
            logger.error("Live trading flag but using paper trading port!")
            return False

        return True

@dataclass
class AlpacaConfig:
    """Alpaca configuration"""
    api_key: str
    secret_key: str
    base_url: str
    data_feed_url: Optional[str] = None
    paper_trading: bool = True

    def validate(self) -> bool:
        """Validate Alpaca configuration"""
        if not self.api_key or not self.secret_key:
            logger.error("Alpaca API credentials missing!")
            return False

        if not self.base_url:
            logger.error("Alpaca base URL missing!")
            return False

        return True

@dataclass
class BrokerConfig:
    """Main broker configuration"""
    # Trading mode
    trading_mode: TradingMode = TradingMode.PAPER

    # Broker configurations
    interactive_brokers: Optional[InteractiveBrokersConfig] = None
    alpaca: Optional[AlpacaConfig] = None

    # Active broker
    active_broker: BrokerType = BrokerType.ALPACA

    # Risk limits
    risk_limits: RiskLimits = field(default_factory=RiskLimits)

    # Feature flags
    enable_live_data: bool = True
    enable_order_submission: bool = True
    enable_position_tracking: bool = True
    enable_monitoring: bool = True

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_directory: str = "logs/phase9"

    def validate(self) -> bool:
        """Validate entire configuration"""
        # Check trading mode
        if self.trading_mode != TradingMode.PAPER:
            logger.error("⚠️ Broker integration must use PAPER trading mode initially!")
            return False

        # Validate risk limits
        if not self.risk_limits.validate():
            return False

        # Validate active broker config
        if self.active_broker == BrokerType.INTERACTIVE_BROKERS:
            if not self.interactive_brokers:
                logger.error("IB selected but not configured!")
                return False
            if not self.interactive_brokers.validate():
                return False
        elif self.active_broker == BrokerType.ALPACA:
            if not self.alpaca:
                logger.error("Alpaca selected but not configured!")
                return False
            if not self.alpaca.validate():
                return False

        logger.info("✅ Broker configuration validated successfully")
        return True

class BrokerConfigLoader:
    """Load broker configuration from environment variables"""

    @staticmethod
    def load_from_env(env_file: Optional[str] = None) -> BrokerConfig:
        """Load configuration from .env file"""
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            # Look for .env in project root
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                logger.info(f"Loaded environment from {env_path}")

        # Create configuration
        config = BrokerConfig()

        # Load trading mode (support both old and new variable names)
        trading_mode = (
            os.getenv("TRADING_MODE") or
            os.getenv("PHASE_9_TRADING_MODE") or
            "paper"
        ).lower()
        if trading_mode == "paper":
            config.trading_mode = TradingMode.PAPER
        elif trading_mode == "live":
            config.trading_mode = TradingMode.LIVE
            logger.warning("⚠️ LIVE trading mode configured!")

        # Load Interactive Brokers configuration
        ib_host = os.getenv("IB_PAPER_HOST") or os.getenv("IB_HOST")
        ib_port = os.getenv("IB_PAPER_PORT") or os.getenv("IB_PORT")

        if ib_host and ib_port:
            config.interactive_brokers = InteractiveBrokersConfig(
                host=ib_host,
                port=int(ib_port),
                client_id=int(os.getenv("IB_PAPER_CLIENT_ID", "1")),
                account_id=os.getenv("IB_PAPER_ACCOUNT") or os.getenv("IB_ACCOUNT_ID"),
                paper_trading=os.getenv("IB_PAPER_TRADING", "true").lower() == "true"
            )
            logger.info("✅ Interactive Brokers configuration loaded")

        # Load Alpaca configuration
        alpaca_api_key = os.getenv("ALPACA_PAPER_API_KEY") or os.getenv("ALPACA_API_KEY")
        alpaca_secret_key = os.getenv("ALPACA_PAPER_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

        if alpaca_api_key and alpaca_secret_key:
            config.alpaca = AlpacaConfig(
                api_key=alpaca_api_key,
                secret_key=alpaca_secret_key,
                base_url=os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
                data_feed_url=os.getenv("ALPACA_DATA_FEED_URL"),
                paper_trading=os.getenv("ALPACA_PAPER_TRADING", "true").lower() == "true"
            )
            logger.info("✅ Alpaca configuration loaded")

        # Load active broker (support both old and new variable names)
        active_broker = (
            os.getenv("BROKER_TYPE") or
            os.getenv("ACTIVE_BROKER") or
            os.getenv("PHASE_9_ACTIVE_BROKER") or
            "alpaca"
        ).lower()
        if active_broker in ["ib", "interactive_brokers"]:
            config.active_broker = BrokerType.INTERACTIVE_BROKERS
        elif active_broker in ["alpaca"]:
            config.active_broker = BrokerType.ALPACA

        # Load risk limits (support both old and new variable names)
        config.risk_limits = RiskLimits(
            max_position_size=int(os.getenv("TRADING_MAX_POSITION_SIZE") or os.getenv("PHASE_9_MAX_POSITION_SIZE") or "100"),
            max_position_value=float(os.getenv("TRADING_MAX_POSITION_VALUE") or os.getenv("PHASE_9_MAX_POSITION_VALUE") or "1000.00"),
            max_positions=int(os.getenv("TRADING_MAX_POSITIONS") or os.getenv("PHASE_9_MAX_POSITIONS") or "5"),
            max_orders_per_minute=int(os.getenv("TRADING_MAX_ORDERS_PER_MINUTE") or os.getenv("PHASE_9_MAX_ORDERS_PER_MINUTE") or "2"),
            max_daily_trades=int(os.getenv("TRADING_MAX_DAILY_TRADES") or os.getenv("PHASE_9_MAX_DAILY_TRADES") or "10"),
            max_daily_loss=float(os.getenv("TRADING_MAX_DAILY_LOSS") or os.getenv("PHASE_9_MAX_DAILY_LOSS") or "100.00"),
            paper_trading_only=(os.getenv("TRADING_PAPER_ONLY") or os.getenv("PHASE_9_PAPER_TRADING_ONLY") or "true").lower() == "true",
            require_manual_approval=(os.getenv("TRADING_REQUIRE_APPROVAL") or os.getenv("PHASE_9_REQUIRE_MANUAL_APPROVAL") or "true").lower() == "true",
            enable_kill_switch=(os.getenv("TRADING_ENABLE_KILL_SWITCH") or os.getenv("PHASE_9_ENABLE_KILL_SWITCH") or "true").lower() == "true",
            alert_on_every_order=(os.getenv("TRADING_ALERT_ON_EVERY_ORDER") or os.getenv("PHASE_9_ALERT_ON_EVERY_ORDER") or "true").lower() == "true",
            log_all_activities=(os.getenv("TRADING_LOG_ALL_ACTIVITIES") or os.getenv("PHASE_9_LOG_ALL_ACTIVITIES") or "true").lower() == "true"
        )

        # Feature flags (support both old and new variable names)
        config.enable_live_data = (os.getenv("TRADING_ENABLE_LIVE_DATA") or os.getenv("PHASE_9_ENABLE_LIVE_DATA") or "true").lower() == "true"
        config.enable_order_submission = (os.getenv("TRADING_ENABLE_ORDER_SUBMISSION") or os.getenv("PHASE_9_ENABLE_ORDER_SUBMISSION") or "true").lower() == "true"
        config.enable_position_tracking = (os.getenv("TRADING_ENABLE_POSITION_TRACKING") or os.getenv("PHASE_9_ENABLE_POSITION_TRACKING") or "true").lower() == "true"
        config.enable_monitoring = (os.getenv("TRADING_ENABLE_MONITORING") or os.getenv("PHASE_9_ENABLE_MONITORING") or "true").lower() == "true"

        # Load feature flags
        config.enable_live_data = os.getenv("PHASE_9_ENABLE_LIVE_DATA", "true").lower() == "true"
        config.enable_order_submission = os.getenv("PHASE_9_ENABLE_ORDER_SUBMISSION", "true").lower() == "true"
        config.enable_position_tracking = os.getenv("PHASE_9_ENABLE_POSITION_TRACKING", "true").lower() == "true"
        config.enable_monitoring = os.getenv("PHASE_9_ENABLE_MONITORING", "true").lower() == "true"

        # Load logging configuration
        config.log_level = os.getenv("PHASE_9_LOG_LEVEL", "INFO")
        config.log_to_file = os.getenv("PHASE_9_LOG_TO_FILE", "true").lower() == "true"
        config.log_directory = os.getenv("PHASE_9_LOG_DIRECTORY", "logs/phase9")

        return config

    @staticmethod
    def create_sample_env_file(path: str = ".env.sample"):
        """Create a sample .env file for reference"""
        sample_content = """# Phase 9 Broker Credentials - SAMPLE FILE
# Copy to .env and fill in your actual credentials
# DO NOT COMMIT .env TO GIT!

# Trading Mode (paper/live) - KEEP ON PAPER FOR PHASE 9!
PHASE_9_TRADING_MODE=paper

# Alpaca (Paper Trading)
ALPACA_PAPER_API_KEY=your_alpaca_paper_api_key_here
ALPACA_PAPER_SECRET_KEY=your_alpaca_paper_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_DATA_FEED_URL=https://data.alpaca.markets
ALPACA_PAPER_TRADING=true

# Interactive Brokers (Paper Trading)
IB_PAPER_HOST=127.0.0.1
IB_PAPER_PORT=7497
IB_PAPER_CLIENT_ID=1
IB_PAPER_ACCOUNT=DU1234567
IB_PAPER_TRADING=true

# Active Broker (alpaca)
PHASE_9_ACTIVE_BROKER=alpaca

# Risk Limits (Conservative for Phase 9)
PHASE_9_MAX_POSITION_SIZE=100
PHASE_9_MAX_POSITION_VALUE=1000.00
PHASE_9_MAX_POSITIONS=5
PHASE_9_MAX_ORDERS_PER_MINUTE=2
PHASE_9_MAX_DAILY_TRADES=10
PHASE_9_MAX_DAILY_LOSS=100.00

# Safety Settings (DO NOT CHANGE FOR PHASE 9)
PHASE_9_PAPER_TRADING_ONLY=true
PHASE_9_REQUIRE_MANUAL_APPROVAL=true
PHASE_9_ENABLE_KILL_SWITCH=true
PHASE_9_ALERT_ON_EVERY_ORDER=true
PHASE_9_LOG_ALL_ACTIVITIES=true

# Feature Flags
PHASE_9_ENABLE_LIVE_DATA=true
PHASE_9_ENABLE_ORDER_SUBMISSION=true
PHASE_9_ENABLE_POSITION_TRACKING=true
PHASE_9_ENABLE_MONITORING=true

# Logging
PHASE_9_LOG_LEVEL=INFO
PHASE_9_LOG_TO_FILE=true
PHASE_9_LOG_DIRECTORY=logs/phase9
"""
        with open(path, 'w') as f:
            f.write(sample_content)

        logger.info(f"✅ Sample .env file created at {path}")

# Convenience function for quick loading
def load_broker_config(env_file: Optional[str] = None) -> BrokerConfig:
    """
    Load and validate broker configuration

    Args:
        env_file: Optional path to .env file

    Returns:
        Validated BrokerConfig

    Raises:
        ValueError: If configuration is invalid
    """
    config = BrokerConfigLoader.load_from_env(env_file)

    if not config.validate():
        raise ValueError("Broker configuration validation failed!")

    return config

# Backward compatibility aliases
Phase9Config = BrokerConfig
Phase9ConfigLoader = BrokerConfigLoader
load_phase9_config = load_broker_config

if __name__ == "__main__":
    # Test configuration loading
    logging.basicConfig(level=logging.INFO)

    # Create sample .env file
    BrokerConfigLoader.create_sample_env_file()

    print("\n✅ Broker configuration module ready")
    print("Next step: Copy .env.sample to .env and add your credentials")
