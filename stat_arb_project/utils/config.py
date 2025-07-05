"""
Configuration management for production-ready settings.
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file with validation.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        Configuration dictionary
    """
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return get_default_config()
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate and merge with defaults
        config = validate_and_merge_config(config)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        logger.info("Using default configuration")
        return get_default_config()

def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration settings.
    
    Returns:
        Default configuration dictionary
    """
    return {
        # Data settings
        'default_tickers': ['AAPL', 'MSFT'],  # Generic stock pair example
        'data_interval': '1h',
        'history_duration_days': 30,
        
        # Strategy settings
        'lookback_window': 100,
        'entry_threshold': 2.0,
        'exit_threshold': 0.5,
        'max_position_size': 0.1,
        'transaction_cost': 0.001,
        'slippage': 0.0005,
        
        # Risk management
        'max_drawdown': 0.05,
        'max_correlation': 0.8,
        'risk_free_rate': 0.02,
        
        # Backtesting
        'initial_capital': 100000.0,
        'rebalance_frequency': '1D',
        
        # Pair selection
        'correlation_threshold': 0.8,
        'cointegration_threshold': 0.05,
        
        # Logging
        'log_level': 'INFO',
        'log_file': 'logs/stat_arb.log',
        
        # Performance
        'min_trades': 10,
        'min_sharpe': 0.5,
        'max_drawdown_threshold': 0.15
    }

def validate_and_merge_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate configuration and merge with defaults.
    
    Args:
        config: User configuration
    
    Returns:
        Validated and merged configuration
    """
    default_config = get_default_config()
    
    # Merge with defaults
    merged_config = default_config.copy()
    merged_config.update(config)
    
    # Validate critical settings
    validate_config_values(merged_config)
    
    return merged_config

def validate_config_values(config: Dict[str, Any]):
    """
    Validate configuration values.
    
    Args:
        config: Configuration to validate
    """
    # Validate numeric ranges
    if not (0 < config.get('entry_threshold', 0) < 10):
        raise ValueError("entry_threshold must be between 0 and 10")
    
    if not (0 < config.get('exit_threshold', 0) < config.get('entry_threshold', 1)):
        raise ValueError("exit_threshold must be less than entry_threshold")
    
    if not (0 < config.get('max_position_size', 0) <= 1):
        raise ValueError("max_position_size must be between 0 and 1")
    
    if not (0 <= config.get('transaction_cost', -1) < 0.1):
        raise ValueError("transaction_cost must be between 0 and 0.1")
    
    if not (0 <= config.get('max_drawdown', -1) <= 1):
        raise ValueError("max_drawdown must be between 0 and 1")
    
    if not (0 < config.get('initial_capital', 0)):
        raise ValueError("initial_capital must be positive")
    
    # Validate tickers
    tickers = config.get('default_tickers', [])
    if not isinstance(tickers, list) or len(tickers) < 2:
        raise ValueError("default_tickers must be a list with at least 2 tickers")

def save_config(config: Dict[str, Any], config_path: str):
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration to save
        config_path: Path to save configuration
    """
    try:
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
        
    except Exception as e:
        logger.error(f"Error saving config to {config_path}: {e}")
        raise

def create_sample_config(config_path: str = "config.yaml"):
    """
    Create a sample configuration file.
    
    Args:
        config_path: Path for sample configuration
    """
    sample_config = {
        'default_tickers': ['AAPL', 'MSFT'],  # Generic stock pair example
        'data_interval': '1h',
        'history_duration_days': 30,
        'lookback_window': 100,
        'entry_threshold': 2.0,
        'exit_threshold': 0.5,
        'max_position_size': 0.1,
        'transaction_cost': 0.001,
        'initial_capital': 100000.0,
        'log_level': 'INFO'
    }
    
    save_config(sample_config, config_path)
    logger.info(f"Sample configuration created at {config_path}")

def get_env_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.
    
    Returns:
        Configuration from environment variables
    """
    env_config = {}
    
    # Map environment variables to config keys
    env_mapping = {
        'STAT_ARB_TICKERS': 'default_tickers',
        'STAT_ARB_INTERVAL': 'data_interval',
        'STAT_ARB_ENTRY_THRESHOLD': 'entry_threshold',
        'STAT_ARB_EXIT_THRESHOLD': 'exit_threshold',
        'STAT_ARB_MAX_POSITION_SIZE': 'max_position_size',
        'STAT_ARB_TRANSACTION_COST': 'transaction_cost',
        'STAT_ARB_INITIAL_CAPITAL': 'initial_capital',
        'STAT_ARB_LOG_LEVEL': 'log_level'
    }
    
    for env_var, config_key in env_mapping.items():
        value = os.getenv(env_var)
        if value is not None:
            # Convert string values to appropriate types
            if config_key in ['entry_threshold', 'exit_threshold', 'max_position_size', 'transaction_cost']:
                env_config[config_key] = float(value)
            elif config_key == 'initial_capital':
                env_config[config_key] = float(value)
            elif config_key == 'default_tickers':
                env_config[config_key] = value.split(',')
            else:
                env_config[config_key] = value
    
    return env_config 