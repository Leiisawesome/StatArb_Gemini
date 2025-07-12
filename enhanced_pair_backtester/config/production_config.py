"""
Production Configuration for VNET/GDS Pair Trading Strategy
Author: Professional Quant Desk Trader
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class ProductionConfig:
    """Production configuration for VNET/GDS pair trading strategy"""
    
    # Trading pair configuration
    symbol1: str = 'VNET'
    symbol2: str = 'GDS'
    pair_name: str = 'VNET_GDS'
    
    # Capital and position sizing
    initial_capital: float = 1000000.0  # $1M initial capital
    max_position_size: float = 0.10     # 10% max position size
    min_confidence: float = 0.6         # 60% minimum confidence
    
    # Signal generation parameters (optimized for VNET/GDS)
    entry_threshold: float = 0.8        # More aggressive than backtest
    exit_threshold: float = 0.2         # Quick exits
    lookback_window: int = 60           # 60-day lookback
    signal_frequency: int = 60          # Check every 60 seconds
    
    # Model parameters
    use_kalman_filter: bool = True
    use_hmm_regime: bool = True
    use_ensemble_filter: bool = True
    
    # Kalman filter configuration
    kalman_config: Optional[Dict] = None
    
    # HMM regime detection configuration
    hmm_config: Optional[Dict] = None
    
    # Ensemble filter configuration
    ensemble_config: Optional[Dict] = None
    
    # Risk management parameters
    max_drawdown_limit: float = 0.05    # 5% max drawdown
    daily_var_limit: float = 0.02       # 2% daily VaR limit
    position_concentration_limit: float = 0.25  # 25% concentration limit
    
    # Transaction costs
    commission_per_trade: float = 0.5   # $0.50 per trade
    bid_ask_spread_bps: float = 2.0     # 2 bps bid-ask spread
    market_impact_bps: float = 1.0      # 1 bps market impact
    
    # Database configuration
    database_config: Optional[Dict] = None
    
    # Monitoring and alerting
    enable_alerts: bool = True
    alert_email: str = 'trading-team@company.com'
    alert_slack_channel: str = '#trading-alerts'
    
    # Logging configuration
    log_level: str = 'INFO'
    log_file: str = 'production.log'
    enable_audit_log: bool = True
    
    def __post_init__(self):
        """Initialize nested configurations"""
        
        # Kalman filter configuration
        if self.kalman_config is None:
            self.kalman_config = {
                'process_noise_beta': 1e-06,
                'process_noise_alpha': 1e-06,
                'observation_noise': 0.0001,
                'initial_beta': 1.0,
                'initial_alpha': 0.0
            }
        
        # HMM regime detection configuration
        if self.hmm_config is None:
            self.hmm_config = {
                'num_regimes': 3,
                'regime_thresholds': {
                    '0': 0.8,  # More aggressive for VNET/GDS
                    '1': 1.0,
                    '2': 1.2
                }
            }
        
        # Ensemble filter configuration
        if self.ensemble_config is None:
            self.ensemble_config = {
                'min_confidence': 0.6,
                'n_estimators': 100,
                'max_depth': 5,
                'lookback_periods': [5, 10, 20]
            }
        
        # Database configuration
        if self.database_config is None:
            self.database_config = {
                'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
                'port': int(os.getenv('CLICKHOUSE_PORT', 8123)),
                'user': os.getenv('CLICKHOUSE_USER', 'default'),
                'password': os.getenv('CLICKHOUSE_PASSWORD', ''),
                'database': os.getenv('CLICKHOUSE_DB', 'polygon_data')
            }
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            'symbol1': self.symbol1,
            'symbol2': self.symbol2,
            'pair_name': self.pair_name,
            'initial_capital': self.initial_capital,
            'max_position_size': self.max_position_size,
            'min_confidence': self.min_confidence,
            'entry_threshold': self.entry_threshold,
            'exit_threshold': self.exit_threshold,
            'lookback_window': self.lookback_window,
            'signal_frequency': self.signal_frequency,
            'use_kalman_filter': self.use_kalman_filter,
            'use_hmm_regime': self.use_hmm_regime,
            'use_ensemble_filter': self.use_ensemble_filter,
            'kalman_config': self.kalman_config,
            'hmm_config': self.hmm_config,
            'ensemble_config': self.ensemble_config,
            'max_drawdown_limit': self.max_drawdown_limit,
            'daily_var_limit': self.daily_var_limit,
            'position_concentration_limit': self.position_concentration_limit,
            'commission_per_trade': self.commission_per_trade,
            'bid_ask_spread_bps': self.bid_ask_spread_bps,
            'market_impact_bps': self.market_impact_bps,
            'database_config': self.database_config,
            'enable_alerts': self.enable_alerts,
            'alert_email': self.alert_email,
            'alert_slack_channel': self.alert_slack_channel,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'enable_audit_log': self.enable_audit_log
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'ProductionConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, config_file: str) -> 'ProductionConfig':
        """Load configuration from JSON file"""
        import json
        with open(config_file, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def save_to_file(self, config_file: str):
        """Save configuration to JSON file"""
        import json
        with open(config_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        errors = []
        
        # Validate thresholds
        if self.entry_threshold <= 0:
            errors.append("Entry threshold must be positive")
        
        if self.exit_threshold <= 0:
            errors.append("Exit threshold must be positive")
        
        if self.exit_threshold >= self.entry_threshold:
            errors.append("Exit threshold must be less than entry threshold")
        
        # Validate position sizing
        if not (0 < self.max_position_size <= 1):
            errors.append("Max position size must be between 0 and 1")
        
        if not (0 < self.min_confidence <= 1):
            errors.append("Min confidence must be between 0 and 1")
        
        # Validate risk limits
        if not (0 < self.max_drawdown_limit <= 1):
            errors.append("Max drawdown limit must be between 0 and 1")
        
        if not (0 < self.daily_var_limit <= 1):
            errors.append("Daily VaR limit must be between 0 and 1")
        
        # Validate capital
        if self.initial_capital <= 0:
            errors.append("Initial capital must be positive")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True

# Environment-specific configurations
class DevelopmentConfig(ProductionConfig):
    """Development environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.initial_capital = 100000.0  # $100K for development
        self.max_position_size = 0.05    # 5% max position size
        self.signal_frequency = 300      # Check every 5 minutes
        self.log_level = 'DEBUG'
        self.enable_alerts = False       # Disable alerts in development

class StagingConfig(ProductionConfig):
    """Staging environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.initial_capital = 500000.0  # $500K for staging
        self.max_position_size = 0.08    # 8% max position size
        self.signal_frequency = 120      # Check every 2 minutes
        self.log_level = 'INFO'
        self.enable_alerts = True        # Enable alerts in staging

class ProductionConfigHigh(ProductionConfig):
    """High-frequency production configuration"""
    
    def __init__(self):
        super().__init__()
        self.signal_frequency = 30       # Check every 30 seconds
        self.entry_threshold = 0.6       # More aggressive
        self.exit_threshold = 0.15       # Quicker exits
        self.min_confidence = 0.55       # Lower confidence threshold

def get_config(environment: Optional[str] = None) -> ProductionConfig:
    """Get configuration based on environment"""
    env = environment or os.getenv('ENVIRONMENT', 'production').lower()
    
    if env == 'development':
        return DevelopmentConfig()
    elif env == 'staging':
        return StagingConfig()
    elif env == 'production_high':
        return ProductionConfigHigh()
    else:
        return ProductionConfig() 