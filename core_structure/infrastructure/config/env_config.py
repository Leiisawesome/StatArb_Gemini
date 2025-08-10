"""
Environment Configuration Loader
Securely loads API keys and configuration from environment variables
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any

def load_env_file(env_file: str = ".env") -> Dict[str, str]:
    """
    Load environment variables from a .env file
    
    Args:
        env_file: Path to the environment file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    env_path = Path(env_file)
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars

def get_api_key(service: str, env_file: Optional[str] = None) -> Optional[str]:
    """
    Get API key for a service from environment variables
    
    Args:
        service: Service name (e.g., 'polygon', 'alpha_vantage')
        env_file: Optional path to .env file
        
    Returns:
        API key if found, None otherwise
    """
    # Map service names to environment variable names
    service_map = {
        'polygon': 'POLYGON_API_KEY',
        'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
        'iex': 'IEX_API_KEY',
        'quandl': 'QUANDL_API_KEY'
    }
    
    env_var = service_map.get(service.lower())
    if not env_var:
        return None
    
    # Try to get from OS environment first
    api_key = os.getenv(env_var)
    
    # If not found and env_file specified, try loading from file
    if not api_key and env_file:
        env_vars = load_env_file(env_file)
        api_key = env_vars.get(env_var)
    
    return api_key

def get_database_config(env_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Get database configuration from environment
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Database configuration dictionary
    """
    # Load from .env file if specified
    env_vars = {}
    if env_file:
        env_vars = load_env_file(env_file)
    
    # Get values from environment or .env file
    def get_env(key: str, default: Any = None) -> Any:
        return os.getenv(key, env_vars.get(key, default))
    
    config = {
        'host': get_env('CLICKHOUSE_HOST', 'localhost'),
        'port': int(get_env('CLICKHOUSE_PORT', 9000)),
        'database': get_env('CLICKHOUSE_DATABASE', 'polygon_data'),
        'user': get_env('CLICKHOUSE_USER', 'default'),
        'password': get_env('CLICKHOUSE_PASSWORD', ''),
        'pool_size': int(get_env('CLICKHOUSE_POOL_SIZE', 5))
    }
    
    return config

def get_feeds_config(env_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Get market data feeds configuration
    
    Args:
        env_file: Optional path to .env file
        
    Returns:
        Feeds configuration dictionary
    """
    polygon_key = get_api_key('polygon', env_file)
    alpha_vantage_key = get_api_key('alpha_vantage', env_file)
    
    config = {
        'feeds': {}
    }
    
    # Add Polygon feed if API key available
    if polygon_key:
        config['feeds']['polygon'] = {
            'enabled': True,
            'api_key': polygon_key,
            'base_url': 'https://api.polygon.io',
            'ws_url': 'wss://socket.polygon.io/stocks',
            'timeout': 30,
            'max_retries': 3
        }
    
    # Add Alpha Vantage feed if API key available
    if alpha_vantage_key:
        config['feeds']['alpha_vantage'] = {
            'enabled': True,
            'api_key': alpha_vantage_key,
            'base_url': 'https://www.alphavantage.co',
            'timeout': 30,
            'poll_interval': 60
        }
    
    return config

class SecureConfigManager:
    """
    Secure configuration manager that loads from environment variables
    """
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        if os.path.exists(self.env_file):
            env_vars = load_env_file(self.env_file)
            for key, value in env_vars.items():
                if key not in os.environ:  # Don't override existing env vars
                    os.environ[key] = value
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a service"""
        return get_api_key(service, self.env_file)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return get_database_config(self.env_file)
    
    def get_feeds_config(self) -> Dict[str, Any]:
        """Get feeds configuration"""
        return get_feeds_config(self.env_file)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        # Handle nested keys like 'market_data.feeds'
        if '.' in key:
            parts = key.split('.')
            if parts[0] == 'market_data' and parts[1] == 'feeds':
                return self.get_feeds_config().get('feeds', {})
        
        # Handle database config
        if key == 'database':
            return self.get_database_config()
        
        # Default behavior - get from environment
        return os.getenv(key, default)

if __name__ == "__main__":
    # Test the configuration loader
    config = SecureConfigManager()
    
    
    db_config = config.get_database_config()
    
    feeds_config = config.get_feeds_config()
