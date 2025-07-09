"""
Data Source Configuration
Allows switching between different data sources for backtesting.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class DataSource(Enum):
    """Available data sources."""
    YFINANCE = "yfinance"
    POLYGON_OFFLINE = "polygon_offline"
    POLYGON_API = "polygon_api"  # Future implementation

@dataclass
class DataConfig:
    """Configuration for data loading."""
    source: DataSource = DataSource.POLYGON_OFFLINE
    data_directory: str = "/Users/lei/Documents/data/polygon"
    cache_enabled: bool = True
    cache_directory: str = "data/cache"
    
    # Polygon.io specific settings
    polygon_api_key: Optional[str] = None
    polygon_base_url: str = "https://api.polygon.io"
    
    # Data quality settings
    validate_quality: bool = True
    filter_market_hours: bool = True
    handle_outliers: bool = True
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DataConfig':
        """Create config from dictionary."""
        import os
        
        source_str = config_dict.get('source', 'polygon_offline')
        source = DataSource(source_str)
        
        # Check for environment variable override
        data_dir = os.getenv('POLYGON_DATA_DIR', config_dict.get('data_directory', '/Users/lei/Documents/data/polygon'))
        
        return cls(
            source=source,
            data_directory=data_dir,
            cache_enabled=config_dict.get('cache_enabled', True),
            cache_directory=config_dict.get('cache_directory', 'data/cache'),
            polygon_api_key=os.getenv('POLYGON_API_KEY', config_dict.get('polygon_api_key')),
            polygon_base_url=config_dict.get('polygon_base_url', 'https://api.polygon.io'),
            validate_quality=config_dict.get('validate_quality', True),
            filter_market_hours=config_dict.get('filter_market_hours', True),
            handle_outliers=config_dict.get('handle_outliers', True),
            max_retries=config_dict.get('max_retries', 3),
            retry_delay=config_dict.get('retry_delay', 1.0)
        )
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'DataConfig':
        """Create config from YAML file."""
        import yaml
        from pathlib import Path
        
        config_path = Path(yaml_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Extract data section
        data_config = config_data.get('data', {})
        return cls.from_dict(data_config)
    
    @classmethod
    def from_env(cls) -> 'DataConfig':
        """Create config from environment variables."""
        import os
        
        source_str = os.getenv('DATA_SOURCE', 'polygon_offline')
        source = DataSource(source_str)
        
        return cls(
            source=source,
            data_directory=os.getenv('POLYGON_DATA_DIR', '/Users/lei/Documents/data/polygon'),
            cache_enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            cache_directory=os.getenv('CACHE_DIRECTORY', 'data/cache'),
            polygon_api_key=os.getenv('POLYGON_API_KEY'),
            polygon_base_url=os.getenv('POLYGON_BASE_URL', 'https://api.polygon.io'),
            validate_quality=os.getenv('VALIDATE_QUALITY', 'true').lower() == 'true',
            filter_market_hours=os.getenv('FILTER_MARKET_HOURS', 'true').lower() == 'true',
            handle_outliers=os.getenv('HANDLE_OUTLIERS', 'true').lower() == 'true',
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('RETRY_DELAY', '1.0'))
        )

# Default configurations
DEFAULT_CONFIG = DataConfig.from_env()

# Configuration for different environments
BACKTEST_CONFIG = DataConfig.from_env()

LIVE_CONFIG = DataConfig(
    source=DataSource.POLYGON_API,
    cache_enabled=True,
    validate_quality=True,
    filter_market_hours=True,
    handle_outliers=True
) 