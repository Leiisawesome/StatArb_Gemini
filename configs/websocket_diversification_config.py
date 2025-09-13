"""
WebSocket Diversification Configuration
======================================

Configuration management for WebSocket diversification system.
Provides templates, validation, and environment-specific settings.

Author: StatArb_Gemini WebSocket Enhancement
"""

import os
import yaml
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class WebSocketDiversificationConfig:
    """Main configuration for WebSocket diversification"""
    
    # Data Sources
    enable_alpaca: bool = True
    enable_polygon: bool = True
    enable_finnhub: bool = False
    enable_twelve_data: bool = False
    
    # API Keys (from environment variables)
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    twelve_data_api_key: Optional[str] = None
    
    # Symbols and Data Types
    default_symbols: List[str] = None
    data_types: List[str] = None
    
    # Connection Settings
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 1.0
    connection_timeout: int = 30
    ping_interval: int = 30
    
    # Performance Settings
    message_buffer_size: int = 5000
    processing_batch_size: int = 100
    max_latency_ms: float = 1000.0
    min_message_rate: float = 1.0
    
    # Quality Settings
    enable_quality_monitoring: bool = True
    quality_check_interval: int = 30
    max_error_rate: float = 0.05
    min_uptime_percentage: float = 95.0
    
    # Failover Settings
    enable_automatic_failover: bool = True
    min_active_sources: int = 1
    failover_delay: float = 2.0
    
    # Integration Settings
    enable_strategy_integration: bool = True
    enable_paper_trading_integration: bool = True
    enable_analytics_integration: bool = True
    
    def __post_init__(self):
        """Initialize default values"""
        if self.default_symbols is None:
            self.default_symbols = [
                "SPY", "QQQ", "IWM",  # ETFs
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",  # Large cap
                "NVDA", "META", "NFLX", "CRM"  # Tech
            ]
        
        if self.data_types is None:
            self.data_types = ["trade", "quote"]
        
        # Load API keys from environment
        self._load_api_keys_from_env()
    
    def _load_api_keys_from_env(self):
        """Load API keys from environment variables"""
        env_mapping = {
            "alpaca_api_key": "ALPACA_API_KEY",
            "alpaca_secret_key": "ALPACA_SECRET_KEY",
            "polygon_api_key": "POLYGON_API_KEY",
            "finnhub_api_key": "FINNHUB_API_KEY",
            "twelve_data_api_key": "TWELVE_DATA_API_KEY"
        }
        
        for attr, env_var in env_mapping.items():
            if getattr(self, attr) is None:
                setattr(self, attr, os.getenv(env_var))
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check if at least one source is enabled with API key
        enabled_sources = []
        if self.enable_alpaca and self.alpaca_api_key:
            enabled_sources.append("Alpaca")
        if self.enable_polygon and self.polygon_api_key:
            enabled_sources.append("Polygon")
        if self.enable_finnhub and self.finnhub_api_key:
            enabled_sources.append("Finnhub")
        if self.enable_twelve_data and self.twelve_data_api_key:
            enabled_sources.append("TwelveData")
        
        if not enabled_sources:
            issues.append("No data sources enabled with valid API keys")
        
        # Validate symbols
        if not self.default_symbols:
            issues.append("No default symbols specified")
        
        # Validate performance settings
        if self.message_buffer_size < 100:
            issues.append("Message buffer size too small (minimum 100)")
        
        if self.processing_batch_size > self.message_buffer_size:
            issues.append("Processing batch size cannot exceed buffer size")
        
        if self.max_latency_ms < 10:
            issues.append("Maximum latency too restrictive (minimum 10ms)")
        
        # Validate quality settings
        if self.max_error_rate < 0 or self.max_error_rate > 1:
            issues.append("Error rate must be between 0 and 1")
        
        if self.min_uptime_percentage < 0 or self.min_uptime_percentage > 100:
            issues.append("Uptime percentage must be between 0 and 100")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSocketDiversificationConfig":
        """Create from dictionary"""
        return cls(**data)

def load_config(config_path: Optional[str] = None) -> WebSocketDiversificationConfig:
    """Load configuration from file or create default"""
    
    if config_path is None:
        # Try default locations
        possible_paths = [
            "configs/websocket_diversification.yaml",
            "configs/websocket_diversification.yml",
            "websocket_diversification.yaml",
            "websocket_diversification.yml"
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith(('.yaml', '.yml')):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            return WebSocketDiversificationConfig.from_dict(data)
        
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default configuration")
    
    return WebSocketDiversificationConfig()

def save_config(config: WebSocketDiversificationConfig, config_path: str):
    """Save configuration to file"""
    
    # Create directory if it doesn't exist
    Path(config_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Remove sensitive data for saving
    safe_config = config.to_dict()
    sensitive_keys = [
        "alpaca_api_key", "alpaca_secret_key",
        "polygon_api_key", "finnhub_api_key",
        "twelve_data_api_key"
    ]
    
    for key in sensitive_keys:
        if key in safe_config and safe_config[key]:
            safe_config[key] = "***REDACTED***"
    
    try:
        with open(config_path, 'w') as f:
            if config_path.endswith(('.yaml', '.yml')):
                yaml.dump(safe_config, f, default_flow_style=False, indent=2)
            else:
                json.dump(safe_config, f, indent=2)
        
        print(f"Configuration saved to {config_path}")
        
    except Exception as e:
        print(f"Failed to save config to {config_path}: {e}")

def create_sample_config() -> str:
    """Create a sample configuration file"""
    
    sample_config = WebSocketDiversificationConfig()
    
    config_content = f"""# WebSocket Diversification Configuration
# ========================================

# Data Sources Configuration
enable_alpaca: {sample_config.enable_alpaca}
enable_polygon: {sample_config.enable_polygon}
enable_finnhub: {sample_config.enable_finnhub}
enable_twelve_data: {sample_config.enable_twelve_data}

# API Keys (set via environment variables for security)
# ALPACA_API_KEY=your_alpaca_key
# POLYGON_API_KEY=your_polygon_key
# FINNHUB_API_KEY=your_finnhub_key
# TWELVE_DATA_API_KEY=your_twelve_data_key

# Default Symbols
default_symbols:
{chr(10).join(f"  - {symbol}" for symbol in sample_config.default_symbols)}

# Data Types
data_types:
{chr(10).join(f"  - {dt}" for dt in sample_config.data_types)}

# Connection Settings
max_reconnect_attempts: {sample_config.max_reconnect_attempts}
reconnect_delay: {sample_config.reconnect_delay}
connection_timeout: {sample_config.connection_timeout}
ping_interval: {sample_config.ping_interval}

# Performance Settings
message_buffer_size: {sample_config.message_buffer_size}
processing_batch_size: {sample_config.processing_batch_size}
max_latency_ms: {sample_config.max_latency_ms}
min_message_rate: {sample_config.min_message_rate}

# Quality Settings
enable_quality_monitoring: {sample_config.enable_quality_monitoring}
quality_check_interval: {sample_config.quality_check_interval}
max_error_rate: {sample_config.max_error_rate}
min_uptime_percentage: {sample_config.min_uptime_percentage}

# Failover Settings
enable_automatic_failover: {sample_config.enable_automatic_failover}
min_active_sources: {sample_config.min_active_sources}
failover_delay: {sample_config.failover_delay}

# Integration Settings
enable_strategy_integration: {sample_config.enable_strategy_integration}
enable_paper_trading_integration: {sample_config.enable_paper_trading_integration}
enable_analytics_integration: {sample_config.enable_analytics_integration}
"""
    
    return config_content

def setup_environment_template() -> str:
    """Create environment template for API keys"""
    
    template = """# WebSocket Diversification Environment Variables
# ===============================================

# Alpaca Markets API Keys
# Get from: https://alpaca.markets/
ALPACA_API_KEY=REDACTED
ALPACA_SECRET_KEY=REDACTED

# Polygon.io API Key
# Get from: https://polygon.io/
POLYGON_API_KEY=your_polygon_api_key_here

# Finnhub API Key
# Get from: https://finnhub.io/
FINNHUB_API_KEY=your_finnhub_api_key_here

# Twelve Data API Key
# Get from: https://twelvedata.com/
TWELVE_DATA_API_KEY=your_twelve_data_api_key_here

# Optional: WebSocket Configuration Override
WEBSOCKET_MAX_LATENCY_MS=1000
WEBSOCKET_BUFFER_SIZE=5000
WEBSOCKET_ENABLE_FAILOVER=true
"""
    
    return template

if __name__ == "__main__":
    """CLI for configuration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Diversification Configuration")
    parser.add_argument("--create-sample", action="store_true", help="Create sample configuration")
    parser.add_argument("--create-env", action="store_true", help="Create environment template")
    parser.add_argument("--validate", help="Validate configuration file")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    if args.create_sample:
        content = create_sample_config()
        output_path = args.output or "websocket_diversification.yaml"
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"Sample configuration created: {output_path}")
    
    elif args.create_env:
        content = setup_environment_template()
        output_path = args.output or ".env.websocket"
        
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"Environment template created: {output_path}")
    
    elif args.validate:
        try:
            config = load_config(args.validate)
            issues = config.validate()
            
            if not issues:
                print(f"✓ Configuration is valid: {args.validate}")
            else:
                print(f"✗ Configuration has issues: {args.validate}")
                for issue in issues:
                    print(f"  - {issue}")
        
        except Exception as e:
            print(f"✗ Failed to validate configuration: {e}")
    
    else:
        # Show current configuration
        config = load_config()
        issues = config.validate()
        
        print("Current WebSocket Diversification Configuration:")
        print("=" * 50)
        
        if issues:
            print("⚠️  Configuration Issues:")
            for issue in issues:
                print(f"  - {issue}")
            print()
        
        print(f"Enabled Sources: {sum([config.enable_alpaca, config.enable_polygon, config.enable_finnhub, config.enable_twelve_data])}")
        print(f"Default Symbols: {len(config.default_symbols)}")
        print(f"Data Types: {config.data_types}")
        print(f"Buffer Size: {config.message_buffer_size}")
        print(f"Quality Monitoring: {'Enabled' if config.enable_quality_monitoring else 'Disabled'}")
        print(f"Automatic Failover: {'Enabled' if config.enable_automatic_failover else 'Disabled'}")
