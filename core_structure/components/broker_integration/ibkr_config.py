"""
IBKR Configuration and Setup

Configuration management for Interactive Brokers integration.
Includes setup instructions and configuration validation.

Author: Pro Quant Desk Trader
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path

from .base_broker import BrokerConfig

logger = logging.getLogger(__name__)


@dataclass
class IBKRConfig(BrokerConfig):
    """IBKR-specific configuration with enhanced setup"""
    # Account information (required field)
    account_id: str = ""
    
    # Connection parameters
    host: str = "127.0.0.1"
    port: int = 7497  # TWS Paper Trading (7496 for live)
    client_id: int = 1
    
    # Override broker name
    broker_name: str = "IBKR"
    
    # IBKR-specific settings
    use_tws: bool = True  # Use TWS instead of IB Gateway
    enable_notifications: bool = True
    download_historical_data: bool = True
    
    # Market data settings
    market_data_type: str = "REALTIME"  # REALTIME, FROZEN, DELAYED
    historical_data_duration: str = "1 Y"
    historical_data_bar_size: str = "1 day"
    
    # Order settings
    default_time_in_force: str = "DAY"
    enable_smart_routing: bool = True
    
    # Paper trading settings
    paper_trading: bool = True
    
    # Connection settings
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Rate limiting
    max_requests_per_second: int = 50  # IBKR limit
    max_orders_per_second: int = 5     # IBKR limit
    
    # Risk management
    max_position_size: float = 0.1
    max_daily_loss: float = 0.02
    max_order_value: float = 1000000
    
    def __post_init__(self):
        """Validate IBKR configuration"""
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        # Validate port
        valid_ports = [7496, 7497, 4001, 4002]
        if self.port not in valid_ports:
            raise ValueError(f"Invalid IBKR port {self.port}. Valid ports: {valid_ports}")
        
        # Validate account ID
        if not self.account_id:
            logger.warning("Account ID not provided. Will use default account.")
        
        # Validate client ID
        if self.client_id <= 0:
            raise ValueError("Client ID must be positive")
        
        # Validate risk parameters
        if self.max_position_size <= 0 or self.max_position_size > 1:
            raise ValueError("Max position size must be between 0 and 1")
        
        if self.max_daily_loss <= 0 or self.max_daily_loss > 1:
            raise ValueError("Max daily loss must be between 0 and 1")
        
        if self.max_order_value <= 0:
            raise ValueError("Max order value must be positive")


class IBKRSetupHelper:
    """Helper class for IBKR setup and configuration"""
    
    @staticmethod
    def create_paper_trading_config(account_id: str = "") -> IBKRConfig:
        """Create configuration for paper trading"""
        return IBKRConfig(
            account_id=account_id,
            paper_trading=True,
            port=7497,  # TWS Paper Trading
            host="127.0.0.1",
            client_id=1,
            use_tws=True,
            enable_notifications=True
        )
    
    @staticmethod
    def create_live_trading_config(account_id: str) -> IBKRConfig:
        """Create configuration for live trading"""
        if not account_id:
            raise ValueError("Account ID required for live trading")
        
        return IBKRConfig(
            account_id=account_id,
            paper_trading=False,
            port=7496,  # TWS Live Trading
            host="127.0.0.1",
            client_id=1,
            use_tws=True,
            enable_notifications=True
        )
    
    @staticmethod
    def create_gateway_config(account_id: str, paper_trading: bool = True) -> IBKRConfig:
        """Create configuration for IB Gateway"""
        port = 4002 if paper_trading else 4001
        
        return IBKRConfig(
            account_id=account_id,
            paper_trading=paper_trading,
            port=port,  # IB Gateway
            host="127.0.0.1",
            client_id=1,
            use_tws=False,
            enable_notifications=True
        )
    
    @staticmethod
    def get_setup_instructions() -> str:
        """Get setup instructions for IBKR"""
        return """
IBKR Setup Instructions:
=======================

1. TWS (Trader Workstation) Setup:
   - Download TWS from: https://www.interactivebrokers.com/en/trading/tws.php
   - Install and launch TWS
   - Go to Edit > Global Configuration > API > Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Set Socket port to 7497 (paper) or 7496 (live)
   - Add your IP address to "Trusted IPs" or use "127.0.0.1"
   - Save and restart TWS

2. IB Gateway Setup (Alternative):
   - Download IB Gateway from: https://www.interactivebrokers.com/en/trading/ib-api.php
   - Install and launch IB Gateway
   - Configure connection settings
   - Set port to 4002 (paper) or 4001 (live)

3. Account Configuration:
   - Log into TWS/IB Gateway with your IBKR Pro account
   - Enable API access in account settings
   - Note your account ID for configuration

4. Python Environment:
   - Install ib_insync: pip install ib_insync
   - Configure your account ID in the IBKRConfig

5. Testing Connection:
   - Run the test script to verify connectivity
   - Check that market data is flowing
   - Verify order placement works

6. Paper Trading:
   - Use paper trading for testing (port 7497)
   - Switch to live trading only after thorough testing
   - Ensure all risk controls are in place

Security Notes:
- Never share your account credentials
- Use paper trading for development and testing
- Enable all available security features
- Monitor your account regularly
"""
    
    @staticmethod
    def validate_connection_requirements() -> Dict[str, bool]:
        """Validate connection requirements"""
        requirements = {
            'ib_insync_installed': False,
            'tws_running': False,
            'port_available': False,
            'account_configured': False
        }
        
        # Check ib_insync installation
        try:
            import ib_insync
            requirements['ib_insync_installed'] = True
        except ImportError:
            logger.error("ib_insync not installed. Run: pip install ib_insync")
        
        # Check if TWS is running (basic check)
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 7497))
            requirements['port_available'] = (result == 0)
            sock.close()
        except Exception:
            requirements['port_available'] = False
        
        # Check account configuration
        if os.getenv('IBKR_ACCOUNT_ID'):
            requirements['account_configured'] = True
        
        return requirements
    
    @staticmethod
    def load_config_from_env() -> IBKRConfig:
        """Load configuration from environment variables"""
        return IBKRConfig(
            account_id=os.getenv('IBKR_ACCOUNT_ID', ''),
            paper_trading=os.getenv('IBKR_PAPER_TRADING', 'true').lower() == 'true',
            host=os.getenv('IBKR_HOST', '127.0.0.1'),
            port=int(os.getenv('IBKR_PORT', '7497')),
            client_id=int(os.getenv('IBKR_CLIENT_ID', '1')),
            use_tws=os.getenv('IBKR_USE_TWS', 'true').lower() == 'true'
        )
    
    @staticmethod
    def save_config_to_env(config: IBKRConfig):
        """Save configuration to environment variables"""
        os.environ['IBKR_ACCOUNT_ID'] = config.account_id
        os.environ['IBKR_PAPER_TRADING'] = str(config.paper_trading).lower()
        os.environ['IBKR_HOST'] = config.host
        os.environ['IBKR_PORT'] = str(config.port)
        os.environ['IBKR_CLIENT_ID'] = str(config.client_id)
        os.environ['IBKR_USE_TWS'] = str(config.use_tws).lower()


def get_default_config() -> IBKRConfig:
    """Get default IBKR configuration"""
    return IBKRSetupHelper.create_paper_trading_config()


def validate_ibkr_setup() -> Dict[str, Any]:
    """Validate IBKR setup and return status"""
    requirements = IBKRSetupHelper.validate_connection_requirements()
    
    status = {
        'ready': all(requirements.values()),
        'requirements': requirements,
        'setup_instructions': IBKRSetupHelper.get_setup_instructions()
    }
    
    if not status['ready']:
        logger.warning("IBKR setup incomplete. Check requirements and setup instructions.")
    
    return status
