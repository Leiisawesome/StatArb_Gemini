"""
Unified Configuration System for ClickHouse-Enhanced Backtester Integration
========================================================================

This module provides a unified configuration system that coordinates settings
between ClickHouse screening and enhanced backtester components.

Key Features:
- Single configuration interface for both systems
- Environment-based configuration management
- Validation and error checking
- Configuration profiles for different use cases
- Dynamic configuration updates
- Export/import capabilities

Author: Pro Quant Desk Trader
"""

import os
import json
import yaml
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

# Import component configurations
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from clickhouse_pair_screening import ScreeningConfig as CHScreeningConfig
except ImportError:
    CHScreeningConfig = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from ..config.backtest_config import BacktestConfig as EBBacktestConfig
except ImportError:
    try:
        from config.backtest_config import BacktestConfig as EBBacktestConfig
    except ImportError:
        EBBacktestConfig = None

logger = logging.getLogger(__name__)

class ConfigurationProfile(Enum):
    """Predefined configuration profiles"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    RESEARCH = "research"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"

class DataSource(Enum):
    """Available data sources"""
    CLICKHOUSE = "clickhouse"
    POLYGON = "polygon"
    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO = "yahoo"
    CSV = "csv"

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    # ClickHouse settings
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "polygon_data"
    clickhouse_table: str = "prices_5min"
    
    # Connection settings
    connection_timeout: int = 30
    max_connections: int = 10
    retry_attempts: int = 3
    
    # Performance settings
    batch_size: int = 10000
    parallel_queries: int = 4
    cache_size: int = 1000

@dataclass
class MarketDataConfig:
    """Market data configuration"""
    # Primary data source
    primary_source: DataSource = DataSource.CLICKHOUSE
    fallback_sources: List[DataSource] = field(default_factory=lambda: [DataSource.POLYGON, DataSource.YAHOO])
    
    # API keys
    polygon_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    
    # Data settings
    data_frequency: str = "5min"  # 1min, 5min, 1hour, 1day
    market_hours_only: bool = True
    timezone: str = "US/Eastern"
    
    # Historical data range
    default_lookback_days: int = 365
    max_lookback_days: int = 1095  # 3 years
    
    # Data quality
    min_data_points: int = 1000
    max_missing_data_pct: float = 0.05  # 5%
    outlier_threshold: float = 5.0  # Standard deviations

@dataclass
class ScreeningConfig:
    """Unified screening configuration"""
    # Universe settings
    max_symbols: int = 1000
    min_market_cap: float = 1e9  # $1B
    min_avg_volume: float = 1e6  # 1M shares
    excluded_sectors: List[str] = field(default_factory=list)
    
    # Pair screening criteria
    min_correlation: float = 0.3
    max_correlation: float = 0.95
    min_cointegration_pvalue: float = 0.05
    max_cointegration_pvalue: float = 0.10
    
    # Regime analysis
    regime_window: int = 60  # Days
    min_regime_stability: float = 0.5
    max_regime_transitions: int = 50
    
    # Liquidity and trading
    min_liquidity_score: float = 0.3
    max_transaction_cost_bps: float = 50.0
    min_spread_consistency: float = 0.6
    
    # Scoring and ranking
    composite_score_weights: Dict[str, float] = field(default_factory=lambda: {
        'correlation': 0.2,
        'cointegration': 0.25,
        'regime_stability': 0.2,
        'liquidity': 0.15,
        'transaction_cost': 0.1,
        'spread_consistency': 0.1
    })
    
    # Output settings
    max_pairs_to_test: int = 100
    min_composite_score: float = 0.5

@dataclass
class BacktestingConfig:
    """Unified backtesting configuration"""
    # Capital and position sizing
    initial_capital: float = 1_000_000
    max_position_size: float = 0.25  # 25% of capital
    min_position_size: float = 0.01  # 1% of capital
    
    # Signal generation
    entry_threshold: float = 2.0  # Z-score
    exit_threshold: float = 0.5   # Z-score
    stop_loss_threshold: float = 3.0  # Z-score
    lookback_window: int = 60  # Days
    
    # Model settings
    use_kalman_filter: bool = True
    use_hmm_regime: bool = True
    use_ensemble_filter: bool = True
    
    # Kalman filter parameters
    kalman_config: Dict[str, float] = field(default_factory=lambda: {
        'process_noise_beta': 1e-6,
        'process_noise_alpha': 1e-6,
        'observation_noise': 1e-4,
        'initial_beta': 1.0,
        'initial_alpha': 0.0
    })
    
    # HMM regime parameters
    hmm_config: Dict[str, Any] = field(default_factory=lambda: {
        'num_regimes': 3,
        'covariance_type': 'full',
        'max_iterations': 100,
        'convergence_threshold': 1e-6
    })
    
    # Ensemble filter parameters
    ensemble_config: Dict[str, Any] = field(default_factory=lambda: {
        'models': ['random_forest', 'gradient_boosting', 'svm'],
        'voting_method': 'soft',
        'cross_validation_folds': 5
    })
    
    # Transaction costs
    commission_per_share: float = 0.005
    commission_minimum: float = 1.0
    spread_cost_multiplier: float = 0.5
    market_impact_coefficient: float = 0.1
    slippage_coefficient: float = 0.05
    
    # Risk management
    max_drawdown_limit: float = 0.15  # 15%
    var_confidence_level: float = 0.05  # 5%
    max_leverage: float = 2.0

@dataclass
class IntegrationConfig:
    """Integration-specific configuration"""
    # Processing settings
    max_pairs_to_backtest: int = 50
    parallel_backtests: int = 4
    backtest_timeout: int = 300  # 5 minutes
    
    # Filtering criteria
    min_screening_score: float = 0.6
    min_backtest_sharpe: float = 0.5
    max_backtest_drawdown: float = 0.20
    min_backtest_trades: int = 10
    
    # Ranking and selection
    final_score_weights: Dict[str, float] = field(default_factory=lambda: {
        'screening_score': 0.4,
        'backtest_performance': 0.6
    })
    
    # Risk assessment
    risk_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.2,
        'medium': 0.4,
        'high': 0.6
    })
    
    # Output settings
    max_recommendations: int = 20
    save_detailed_results: bool = True
    generate_visualizations: bool = True

@dataclass
class MonitoringConfig:
    """Real-time monitoring configuration"""
    # Update frequencies
    screening_update_interval: int = 3600  # 1 hour
    performance_update_interval: int = 300  # 5 minutes
    risk_check_interval: int = 60  # 1 minute
    
    # Alert thresholds
    correlation_breakdown_threshold: float = 0.3
    performance_degradation_threshold: float = -0.1  # 10% loss
    regime_change_sensitivity: float = 0.8
    
    # Notification settings
    email_alerts: bool = False
    slack_webhook: Optional[str] = None
    alert_cooldown: int = 300  # 5 minutes
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "integration_monitoring.log"
    max_log_size: int = 100  # MB

@dataclass
class UnifiedConfig:
    """Unified configuration for the integrated system"""
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    screening: ScreeningConfig = field(default_factory=ScreeningConfig)
    backtesting: BacktestingConfig = field(default_factory=BacktestingConfig)
    integration: IntegrationConfig = field(default_factory=IntegrationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # System settings
    profile: ConfigurationProfile = ConfigurationProfile.DEVELOPMENT
    environment: str = "development"
    debug_mode: bool = False
    
    # Paths
    output_dir: str = "integration_results"
    log_dir: str = "logs"
    cache_dir: str = "cache"
    
    # Metadata
    config_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class UnifiedConfigManager:
    """Manager for unified configuration system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = UnifiedConfig()
        
        # Load configuration if file provided
        if config_file and Path(config_file).exists():
            self.load_config(config_file)
        
        # Override with environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"UnifiedConfigManager initialized with profile: {self.config.profile.value}")
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Database settings
        clickhouse_host = os.getenv('CLICKHOUSE_HOST')
        if clickhouse_host:
            self.config.database.clickhouse_host = clickhouse_host
        
        clickhouse_port = os.getenv('CLICKHOUSE_PORT')
        if clickhouse_port:
            self.config.database.clickhouse_port = int(clickhouse_port)
        
        clickhouse_user = os.getenv('CLICKHOUSE_USER')
        if clickhouse_user:
            self.config.database.clickhouse_user = clickhouse_user
        
        clickhouse_password = os.getenv('CLICKHOUSE_PASSWORD')
        if clickhouse_password:
            self.config.database.clickhouse_password = clickhouse_password
        
        clickhouse_database = os.getenv('CLICKHOUSE_DATABASE')
        if clickhouse_database:
            self.config.database.clickhouse_database = clickhouse_database
        
        # API keys
        polygon_api_key = os.getenv('POLYGON_API_KEY')
        if polygon_api_key:
            self.config.market_data.polygon_api_key = polygon_api_key
        
        alpha_vantage_api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if alpha_vantage_api_key:
            self.config.market_data.alpha_vantage_api_key = alpha_vantage_api_key
        
        # System settings
        environment = os.getenv('ENVIRONMENT')
        if environment:
            self.config.environment = environment
        
        debug_mode = os.getenv('DEBUG_MODE')
        if debug_mode:
            self.config.debug_mode = debug_mode.lower() == 'true'
        
        # Capital settings
        initial_capital = os.getenv('INITIAL_CAPITAL')
        if initial_capital:
            self.config.backtesting.initial_capital = float(initial_capital)
        
        logger.info("Configuration loaded from environment variables")
    
    def _validate_config(self):
        """Validate configuration settings"""
        errors = []
        
        # Validate database settings
        if not self.config.database.clickhouse_host:
            errors.append("ClickHouse host is required")
        
        # Validate thresholds
        if self.config.screening.min_correlation >= self.config.screening.max_correlation:
            errors.append("min_correlation must be less than max_correlation")
        
        if self.config.backtesting.entry_threshold <= self.config.backtesting.exit_threshold:
            errors.append("entry_threshold must be greater than exit_threshold")
        
        # Validate weights
        screening_weights = self.config.screening.composite_score_weights
        if abs(sum(screening_weights.values()) - 1.0) > 0.01:
            errors.append("Composite score weights must sum to 1.0")
        
        integration_weights = self.config.integration.final_score_weights
        if abs(sum(integration_weights.values()) - 1.0) > 0.01:
            errors.append("Final score weights must sum to 1.0")
        
        # Validate paths
        for path_attr in ['output_dir', 'log_dir', 'cache_dir']:
            path = getattr(self.config, path_attr)
            Path(path).mkdir(parents=True, exist_ok=True)
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        logger.info("Configuration validation passed")
    
    def load_config(self, config_file: str):
        """Load configuration from file"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        if config_path.suffix.lower() == '.json':
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        elif config_path.suffix.lower() in ['.yaml', '.yml']:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        # Update configuration
        self._update_config_from_dict(config_data)
        self.config.updated_at = datetime.now()
        
        logger.info(f"Configuration loaded from {config_file}")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration from dictionary"""
        for section, values in config_data.items():
            if hasattr(self.config, section):
                section_config = getattr(self.config, section)
                for key, value in values.items():
                    if hasattr(section_config, key):
                        setattr(section_config, key, value)
    
    def save_config(self, config_file: str, format: str = 'json'):
        """Save configuration to file"""
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = asdict(self.config)
        
        # Convert datetime objects to strings
        config_dict['created_at'] = self.config.created_at.isoformat()
        config_dict['updated_at'] = self.config.updated_at.isoformat()
        
        if format.lower() == 'json':
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        elif format.lower() in ['yaml', 'yml']:
            with open(config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Configuration saved to {config_file}")
    
    def apply_profile(self, profile: ConfigurationProfile):
        """Apply predefined configuration profile"""
        self.config.profile = profile
        
        if profile == ConfigurationProfile.DEVELOPMENT:
            self._apply_development_profile()
        elif profile == ConfigurationProfile.TESTING:
            self._apply_testing_profile()
        elif profile == ConfigurationProfile.PRODUCTION:
            self._apply_production_profile()
        elif profile == ConfigurationProfile.RESEARCH:
            self._apply_research_profile()
        elif profile == ConfigurationProfile.AGGRESSIVE:
            self._apply_aggressive_profile()
        elif profile == ConfigurationProfile.CONSERVATIVE:
            self._apply_conservative_profile()
        
        self.config.updated_at = datetime.now()
        logger.info(f"Applied {profile.value} profile")
    
    def _apply_development_profile(self):
        """Apply development profile settings"""
        self.config.debug_mode = True
        self.config.screening.max_pairs_to_test = 20
        self.config.integration.max_pairs_to_backtest = 10
        self.config.integration.parallel_backtests = 2
        self.config.monitoring.log_level = "DEBUG"
    
    def _apply_testing_profile(self):
        """Apply testing profile settings"""
        self.config.debug_mode = True
        self.config.screening.max_pairs_to_test = 50
        self.config.integration.max_pairs_to_backtest = 20
        self.config.integration.parallel_backtests = 4
        self.config.monitoring.log_level = "INFO"
    
    def _apply_production_profile(self):
        """Apply production profile settings"""
        self.config.debug_mode = False
        self.config.screening.max_pairs_to_test = 1000
        self.config.integration.max_pairs_to_backtest = 100
        self.config.integration.parallel_backtests = 8
        self.config.monitoring.log_level = "WARNING"
        self.config.monitoring.email_alerts = True
    
    def _apply_research_profile(self):
        """Apply research profile settings"""
        self.config.debug_mode = False
        self.config.screening.max_pairs_to_test = 500
        self.config.integration.max_pairs_to_backtest = 100
        self.config.backtesting.lookback_window = 120  # Longer lookback
        self.config.integration.save_detailed_results = True
        self.config.integration.generate_visualizations = True
    
    def _apply_aggressive_profile(self):
        """Apply aggressive trading profile"""
        self.config.screening.min_correlation = 0.2
        self.config.backtesting.entry_threshold = 1.5
        self.config.backtesting.exit_threshold = 0.3
        self.config.backtesting.max_position_size = 0.3
        self.config.integration.min_backtest_sharpe = 0.3
    
    def _apply_conservative_profile(self):
        """Apply conservative trading profile"""
        self.config.screening.min_correlation = 0.5
        self.config.backtesting.entry_threshold = 2.5
        self.config.backtesting.exit_threshold = 0.8
        self.config.backtesting.max_position_size = 0.15
        self.config.integration.min_backtest_sharpe = 0.8
        self.config.backtesting.max_drawdown_limit = 0.10
    
    def get_clickhouse_screening_config(self):
        """Convert to ClickHouse screening configuration"""
        if CHScreeningConfig is None:
            raise ImportError("ClickHouse screening module not available")
        
        return CHScreeningConfig(
            clickhouse_host=self.config.database.clickhouse_host,
            clickhouse_port=self.config.database.clickhouse_port,
            clickhouse_user=self.config.database.clickhouse_user,
            clickhouse_password=self.config.database.clickhouse_password,
            database_name=self.config.database.clickhouse_database,
            min_correlation=self.config.screening.min_correlation,
            min_cointegration_pvalue=self.config.screening.min_cointegration_pvalue,
            regime_window=self.config.screening.regime_window,
            min_regime_stability=self.config.screening.min_regime_stability,
            max_pairs_to_test=self.config.screening.max_pairs_to_test,
            batch_size=self.config.database.batch_size,
            max_workers=self.config.database.parallel_queries,
            results_dir=self.config.output_dir
        )
    
    def get_enhanced_backtest_config(self):
        """Convert to enhanced backtester configuration"""
        if EBBacktestConfig is None:
            raise ImportError("Enhanced backtester module not available")
        
        return EBBacktestConfig(
            initial_capital=self.config.backtesting.initial_capital,
            max_position_size=self.config.backtesting.max_position_size,
            entry_threshold=self.config.backtesting.entry_threshold,
            exit_threshold=self.config.backtesting.exit_threshold,
            stop_loss_threshold=self.config.backtesting.stop_loss_threshold,
            lookback_window=self.config.backtesting.lookback_window,
            use_kalman_filter=self.config.backtesting.use_kalman_filter,
            use_hmm_regime=self.config.backtesting.use_hmm_regime,
            use_ensemble_filter=self.config.backtesting.use_ensemble_filter,
            kalman_config=self.config.backtesting.kalman_config,
            hmm_config=self.config.backtesting.hmm_config,
            ensemble_config=self.config.backtesting.ensemble_config,
            data_source=self.config.market_data.primary_source.value,
            data_frequency=self.config.market_data.data_frequency,
            database_config={
                'host': self.config.database.clickhouse_host,
                'port': self.config.database.clickhouse_port,
                'user': self.config.database.clickhouse_user,
                'password': self.config.database.clickhouse_password,
                'database': self.config.database.clickhouse_database
            },
            output_dir=self.config.output_dir
        )
    
    def update_config(self, section: str, key: str, value: Any):
        """Update specific configuration value"""
        if hasattr(self.config, section):
            section_config = getattr(self.config, section)
            if hasattr(section_config, key):
                setattr(section_config, key, value)
                self.config.updated_at = datetime.now()
                logger.info(f"Updated {section}.{key} = {value}")
            else:
                raise ValueError(f"Key '{key}' not found in section '{section}'")
        else:
            raise ValueError(f"Section '{section}' not found")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            'profile': self.config.profile.value,
            'environment': self.config.environment,
            'database_host': self.config.database.clickhouse_host,
            'primary_data_source': self.config.market_data.primary_source.value,
            'max_pairs_to_test': self.config.screening.max_pairs_to_test,
            'initial_capital': self.config.backtesting.initial_capital,
            'entry_threshold': self.config.backtesting.entry_threshold,
            'max_pairs_to_backtest': self.config.integration.max_pairs_to_backtest,
            'parallel_backtests': self.config.integration.parallel_backtests,
            'debug_mode': self.config.debug_mode,
            'created_at': self.config.created_at.isoformat(),
            'updated_at': self.config.updated_at.isoformat()
        }
    
    def export_config(self, format: str = 'json') -> str:
        """Export configuration as string"""
        config_dict = asdict(self.config)
        config_dict['created_at'] = self.config.created_at.isoformat()
        config_dict['updated_at'] = self.config.updated_at.isoformat()
        
        if format.lower() == 'json':
            return json.dumps(config_dict, indent=2)
        elif format.lower() in ['yaml', 'yml']:
            return yaml.dump(config_dict, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

# Predefined configuration profiles
PROFILE_CONFIGS = {
    ConfigurationProfile.DEVELOPMENT: {
        'screening': {'max_pairs_to_test': 20},
        'integration': {'max_pairs_to_backtest': 10, 'parallel_backtests': 2},
        'monitoring': {'log_level': 'DEBUG'}
    },
    ConfigurationProfile.TESTING: {
        'screening': {'max_pairs_to_test': 50},
        'integration': {'max_pairs_to_backtest': 20, 'parallel_backtests': 4},
        'monitoring': {'log_level': 'INFO'}
    },
    ConfigurationProfile.PRODUCTION: {
        'screening': {'max_pairs_to_test': 1000},
        'integration': {'max_pairs_to_backtest': 100, 'parallel_backtests': 8},
        'monitoring': {'log_level': 'WARNING', 'email_alerts': True}
    },
    ConfigurationProfile.RESEARCH: {
        'screening': {'max_pairs_to_test': 500},
        'integration': {'max_pairs_to_backtest': 100, 'save_detailed_results': True},
        'backtesting': {'lookback_window': 120}
    },
    ConfigurationProfile.AGGRESSIVE: {
        'screening': {'min_correlation': 0.2},
        'backtesting': {'entry_threshold': 1.5, 'exit_threshold': 0.3, 'max_position_size': 0.3},
        'integration': {'min_backtest_sharpe': 0.3}
    },
    ConfigurationProfile.CONSERVATIVE: {
        'screening': {'min_correlation': 0.5},
        'backtesting': {'entry_threshold': 2.5, 'exit_threshold': 0.8, 'max_position_size': 0.15},
        'integration': {'min_backtest_sharpe': 0.8}
    }
}

# Example usage
if __name__ == "__main__":
    # Create configuration manager
    config_manager = UnifiedConfigManager()
    
    # Apply production profile
    config_manager.apply_profile(ConfigurationProfile.PRODUCTION)
    
    # Update specific settings
    config_manager.update_config('backtesting', 'initial_capital', 5_000_000)
    
    # Get component configurations
    screening_config = config_manager.get_clickhouse_screening_config()
    backtest_config = config_manager.get_enhanced_backtest_config()
    
    # Save configuration
    config_manager.save_config('production_config.json')
    
    # Display summary
    summary = config_manager.get_config_summary()
    print("Configuration Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}") 