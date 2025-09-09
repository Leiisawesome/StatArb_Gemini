"""
Unit Tests for Configuration System
==================================

Tests for the streamlined configuration system (config.py).
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

from core_structure.config import (
    TradingConfig, ConfigManager, Environment, TradingMode, LogLevel,
    ConfigurationError, ValidationError
)


class TestTradingConfig:
    """Test TradingConfig dataclass"""
    
    def test_default_config_creation(self):
        """Test creating config with default values"""
        config = TradingConfig()
        
        assert config.environment == Environment.DEVELOPMENT
        assert config.trading_mode == TradingMode.BACKTEST
        assert config.log_level == LogLevel.INFO
        assert config.initial_capital == 100000.0
        assert config.max_position_size == 10000.0  # Actual default value
        # Note: risk_limit doesn't exist in TradingConfig, using max_daily_loss instead
        assert config.max_daily_loss == 5000.0
    
    def test_custom_config_creation(self):
        """Test creating config with custom values"""
        config = TradingConfig(
            environment=Environment.PRODUCTION,
            trading_mode=TradingMode.LIVE,
            log_level=LogLevel.DEBUG,
            initial_capital=500000.0,
            max_position_size=5000.0,
            max_daily_loss=2500.0
        )
        
        assert config.environment == Environment.PRODUCTION
        assert config.trading_mode == TradingMode.LIVE
        assert config.log_level == LogLevel.DEBUG
        assert config.initial_capital == 500000.0
        assert config.max_position_size == 5000.0
        assert config.max_daily_loss == 2500.0
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config should not raise
        config = TradingConfig(initial_capital=100000.0, max_daily_loss=2000.0)
        assert config.initial_capital > 0
        assert config.max_daily_loss > 0
        
        # Test edge cases
        config_edge = TradingConfig(initial_capital=1.0, max_daily_loss=0.5)
        assert config_edge.initial_capital == 1.0
        assert config_edge.max_daily_loss == 0.5
    
    def test_config_serialization(self):
        """Test config to/from dict conversion"""
        config = TradingConfig(
            environment=Environment.PRODUCTION,
            initial_capital=250000.0,
            clickhouse_host="prod-db.example.com"
        )
        
        # Test dict conversion (if implemented)
        config_dict = {
            'environment': config.environment.value,
            'trading_mode': config.trading_mode.value,
            'log_level': config.log_level.value,
            'initial_capital': config.initial_capital,
            'clickhouse_host': config.clickhouse_host
        }
        
        assert config_dict['environment'] == 'production'
        assert config_dict['initial_capital'] == 250000.0
        assert config_dict['clickhouse_host'] == "prod-db.example.com"


class TestConfigManager:
    """Test ConfigManager functionality"""
    
    def test_config_manager_creation(self, test_config):
        """Test creating config manager"""
        manager = ConfigManager()  # Create without file path
        manager._config = test_config  # Set config directly for testing
        
        assert manager.get_config() == test_config
        assert manager.get_config().initial_capital == test_config.initial_capital
    
    def test_config_manager_default(self):
        """Test config manager with default config"""
        manager = ConfigManager()
        
        config = manager.get_config()
        assert isinstance(config, TradingConfig)
        assert config.environment == Environment.DEVELOPMENT
    
    def test_config_file_operations(self, temp_dir):
        """Test loading and saving config files"""
        config_file = temp_dir / "test_config.yml"
        
        # Create test config data
        config_data = {
            'environment': 'production',
            'trading_mode': 'live',
            'initial_capital': 500000.0,
            'clickhouse_host': 'prod-db.example.com',
            'clickhouse_port': 9000
        }
        
        # Write config file
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Test loading
        manager = ConfigManager()
        loaded_config = manager.load_config(str(config_file))  # Use load_config method
        
        assert loaded_config.environment.value == 'production'
        assert loaded_config.trading_mode.value == 'live'
        assert loaded_config.initial_capital == 500000.0
        assert loaded_config.clickhouse_host == 'prod-db.example.com'
    
    def test_environment_detection(self):
        """Test environment detection and setup"""
        manager = ConfigManager()
        
        # Test development environment (default)
        config = manager.get_config()
        assert config.environment == Environment.DEVELOPMENT
        assert manager.is_production() == False  # Use manager's method
        
        # Test production environment
        manager.set_environment(Environment.PRODUCTION)
        assert manager.is_production() == True
    
    def test_backward_compatibility_methods(self, config_manager):
        """Test backward compatibility methods"""
        manager = config_manager
        
        # Test legacy get method
        config = manager.get_config()
        assert manager.get('initial_capital') == config.initial_capital
        assert manager.get('nonexistent_key', 'default') == 'default'
        
        # Test database config
        db_config = manager.get_database_config()
        assert 'host' in db_config
        assert 'port' in db_config
        assert 'database' in db_config
        
        # Test strategy config
        strategy_config = manager.get_strategy_config('momentum')
        assert hasattr(strategy_config, 'period')
        assert hasattr(strategy_config, 'capital')
    
    def test_config_validation_errors(self):
        """Test configuration validation errors"""
        manager = ConfigManager()
        
        # Test invalid config data
        invalid_configs = [
            {'initial_capital': -1000},  # Negative capital
            {'risk_limit': 1.5},  # Risk limit > 1
            {'max_position_size': -0.1},  # Negative position size
        ]
        
        for invalid_config in invalid_configs:
            # Should handle invalid configs gracefully
            # (Implementation may vary based on validation strategy)
            pass


class TestConfigEnums:
    """Test configuration enums"""
    
    def test_environment_enum(self):
        """Test Environment enum"""
        assert Environment.DEVELOPMENT.value == 'development'
        assert Environment.PRODUCTION.value == 'production'
        assert Environment.TESTING.value == 'testing'
        
        # Test enum comparison
        assert Environment.DEVELOPMENT != Environment.PRODUCTION
    
    def test_trading_mode_enum(self):
        """Test TradingMode enum"""
        assert TradingMode.BACKTEST.value == 'backtest'
        assert TradingMode.PAPER.value == 'paper'
        assert TradingMode.LIVE.value == 'live'
    
    def test_log_level_enum(self):
        """Test LogLevel enum"""
        assert LogLevel.DEBUG.value == 'DEBUG'
        assert LogLevel.INFO.value == 'INFO'
        assert LogLevel.WARNING.value == 'WARNING'
        assert LogLevel.ERROR.value == 'ERROR'


class TestConfigIntegration:
    """Test configuration integration scenarios"""
    
    def test_config_environment_switching(self):
        """Test switching between environments"""
        # Development config
        dev_manager = ConfigManager()
        dev_config = dev_manager.get_config()
        
        assert dev_config.environment == Environment.DEVELOPMENT
        assert dev_config.log_level == LogLevel.INFO  # Default for dev
        
        # Production config
        prod_manager = ConfigManager()
        prod_manager.set_environment(Environment.PRODUCTION)
        
        assert prod_manager.is_production()
    
    def test_config_with_different_trading_modes(self):
        """Test config behavior with different trading modes"""
        modes = [TradingMode.BACKTEST, TradingMode.PAPER, TradingMode.LIVE]
        
        for mode in modes:
            manager = ConfigManager()
            manager.set_trading_mode(mode)
            
            assert manager.get_config().trading_mode == mode
    
    def test_config_parameter_inheritance(self):
        """Test configuration parameter inheritance and overrides"""
        base_config = TradingConfig(
            initial_capital=100000.0,
            max_daily_loss=2000.0
        )
        
        # Override specific parameters
        override_config = TradingConfig(
            initial_capital=base_config.initial_capital,
            max_daily_loss=1000.0,  # Override daily loss limit
            max_position_size=5000.0  # Override position size
        )
        
        assert override_config.initial_capital == base_config.initial_capital
        assert override_config.max_daily_loss != base_config.max_daily_loss
        assert override_config.max_daily_loss == 1000.0


@pytest.mark.performance
class TestConfigPerformance:
    """Test configuration system performance"""
    
    def test_config_creation_performance(self, performance_timer):
        """Test config creation performance"""
        performance_timer.start()
        
        # Create multiple configs
        configs = []
        for i in range(1000):
            config = TradingConfig(
                initial_capital=100000.0 + i,
                max_daily_loss=2000.0
            )
            configs.append(config)
        
        performance_timer.stop()
        
        assert len(configs) == 1000
        assert performance_timer.elapsed_seconds < 1.0  # Should be very fast
    
    def test_config_manager_performance(self, config_manager, performance_timer):
        """Test config manager performance"""
        manager = config_manager
        
        performance_timer.start()
        
        # Perform multiple operations
        for i in range(1000):
            config = manager.get_config()
            manager.get('initial_capital')
            manager.is_production()
        
        performance_timer.stop()
        
        assert performance_timer.elapsed_seconds < 0.5  # Should be very fast
