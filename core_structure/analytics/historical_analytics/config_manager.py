#!/usr/bin/env python3
"""
Configuration Management System
==============================

YAML-based configuration management for historical analytics
with support for periods, data sources, and analysis parameters.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import yaml
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AnalyticsConfig:
    """Main configuration for historical analytics"""
    data_source_path: str
    output_base_dir: str = "outputs/historical_analytics"
    enable_caching: bool = True
    enable_parallel_processing: bool = True
    confidence_threshold: float = 0.6
    min_sample_size: int = 30
    max_instruments_per_config: int = 20


class HistoricalAnalyticsConfigManager:
    """
    Configuration manager for historical analytics system
    """
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configuration files
        self.default_files = {
            'main': self.config_dir / 'historical_analytics.yaml',
            'periods': self.config_dir / 'historical_periods.yaml',
            'strategies': self.config_dir / 'strategy_parameters.yaml',
            'risk': self.config_dir / 'risk_parameters.yaml'
        }
        
        # Initialize with defaults if files don't exist
        self._ensure_default_configs()
        
        logger.info(f"ConfigManager initialized: {config_dir}")
    
    def load_main_config(self) -> AnalyticsConfig:
        """Load main analytics configuration"""
        config_data = self._load_yaml_file(self.default_files['main'])
        return AnalyticsConfig(**config_data.get('analytics', {}))
    
    def load_periods_config(self) -> Dict[str, Any]:
        """Load historical periods configuration"""
        return self._load_yaml_file(self.default_files['periods'])
    
    def load_strategy_config(self) -> Dict[str, Any]:
        """Load strategy parameters configuration"""
        return self._load_yaml_file(self.default_files['strategies'])
    
    def load_risk_config(self) -> Dict[str, Any]:
        """Load risk management configuration"""
        return self._load_yaml_file(self.default_files['risk'])
    
    def save_config(self, config: AnalyticsConfig, config_name: str = 'main'):
        """Save analytics configuration"""
        if config_name == 'main':
            file_path = self.default_files['main']
            config_data = {'analytics': asdict(config)}
        else:
            file_path = self.config_dir / f'{config_name}.yaml'
            config_data = asdict(config)
        
        self._save_yaml_file(config_data, file_path)
        logger.info(f"Configuration saved: {file_path}")
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get complete default configuration for historical analytics"""
        return {
            'historical_periods': {
                'bull_market_2019': {
                    'start_date': '2019-01-01',
                    'end_date': '2019-12-31',
                    'description': 'Bull market period'
                },
                'covid_crash_2020': {
                    'start_date': '2020-02-01',
                    'end_date': '2020-04-30',
                    'description': 'COVID-19 market crash'
                },
                'recovery_2020': {
                    'start_date': '2020-05-01',
                    'end_date': '2020-12-31',
                    'description': 'Recovery period'
                },
                'tech_rally_2021': {
                    'start_date': '2021-01-01',
                    'end_date': '2021-12-31',
                    'description': 'Technology sector rally'
                }
            },
            'strategy_configs': {
                'mean_reversion': {
                    'lookback_period': 20,
                    'entry_threshold': 2.0,
                    'exit_threshold': 0.5,
                    'rebalance_frequency': 'daily'
                },
                'momentum': {
                    'lookback_period': 12,
                    'momentum_threshold': 0.05,
                    'holding_period': 5,
                    'rebalance_frequency': 'weekly'
                },
                'pairs_trading': {
                    'lookback_period': 60,
                    'entry_threshold': 2.0,
                    'exit_threshold': 0.5,
                    'correlation_threshold': 0.8
                }
            },
            'risk_management': {
                'max_position_size': 0.1,
                'max_portfolio_exposure': 0.8,
                'stop_loss_threshold': 0.05,
                'max_drawdown_threshold': 0.15,
                'volatility_target': 0.20
            },
            'analysis_settings': {
                'min_regime_duration': 30,
                'confidence_threshold': 0.8,
                'parallel_processing': True,
                'enable_clustering': True,
                'portfolio_optimization': {
                    'enable_optimization': True,
                    'optimization_method': 'mean_variance',
                    'risk_aversion': 3.0,
                    'max_instruments': 10
                }
            }
        }
    
    def create_custom_periods_config(self, periods: List[Dict[str, Any]],
                                   config_name: str) -> Path:
        """Create custom periods configuration"""
        config_file = self.config_dir / f'periods_{config_name}.yaml'
        config_data = {'periods': periods}
        
        self._save_yaml_file(config_data, config_file)
        logger.info(f"Custom periods config created: {config_file}")
        return config_file
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Config file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            return {}
    
    def _save_yaml_file(self, data: Dict[str, Any], file_path: Path):
        """Save data to YAML file"""
        with open(file_path, 'w') as f:
            yaml.dump(data, f, indent=2, default_flow_style=False)
    
    def _ensure_default_configs(self):
        """Ensure default configuration files exist"""
        if not self.default_files['main'].exists():
            self._create_default_main_config()
        
        if not self.default_files['periods'].exists():
            self._create_default_periods_config()
        
        if not self.default_files['strategies'].exists():
            self._create_default_strategy_config()
        
        if not self.default_files['risk'].exists():
            self._create_default_risk_config()
    
    def _create_default_main_config(self):
        """Create default main configuration"""
        default_config = {
            'analytics': {
                'data_source_path': 'data/market_data.csv',
                'output_base_dir': 'outputs/historical_analytics',
                'enable_caching': True,
                'enable_parallel_processing': True,
                'confidence_threshold': 0.6,
                'min_sample_size': 30,
                'max_instruments_per_config': 20
            }
        }
        
        self._save_yaml_file(default_config, self.default_files['main'])
    
    def _create_default_periods_config(self):
        """Create default periods configuration"""
        default_periods = {
            'periods': [
                {
                    'name': '2008_financial_crisis',
                    'start_date': '2008-01-01',
                    'end_date': '2009-12-31',
                    'regime_hint': 'high_volatility',
                    'description': 'Global Financial Crisis period',
                    'category': 'crisis'
                },
                {
                    'name': '2010_2012_recovery',
                    'start_date': '2010-01-01',
                    'end_date': '2012-12-31',
                    'regime_hint': 'bull_market',
                    'description': 'Post-crisis recovery',
                    'category': 'bull'
                },
                {
                    'name': '2020_covid_crash',
                    'start_date': '2020-01-01',
                    'end_date': '2020-12-31',
                    'regime_hint': 'high_volatility',
                    'description': 'COVID-19 pandemic disruption',
                    'category': 'crisis'
                }
            ]
        }
        
        self._save_yaml_file(default_periods, self.default_files['periods'])
    
    def _create_default_strategy_config(self):
        """Create default strategy configuration"""
        default_strategies = {
            'strategies': {
                'mean_reversion': {
                    'default_parameters': {
                        'lookback_period': 20,
                        'entry_threshold': 2.0,
                        'exit_threshold': 0.5,
                        'rebalance_frequency': 'daily'
                    }
                },
                'momentum': {
                    'default_parameters': {
                        'momentum_window': 20,
                        'signal_window': 5,
                        'trend_threshold': 0.05,
                        'rebalance_frequency': 'weekly'
                    }
                },
                'pairs_trading': {
                    'default_parameters': {
                        'cointegration_window': 252,
                        'entry_zscore': 2.0,
                        'exit_zscore': 0.5,
                        'hedge_ratio_lookback': 60
                    }
                }
            }
        }
        
        self._save_yaml_file(default_strategies, self.default_files['strategies'])
    
    def _create_default_risk_config(self):
        """Create default risk configuration"""
        default_risk = {
            'risk_management': {
                'default_parameters': {
                    'max_position_size': 0.05,
                    'portfolio_volatility_limit': 0.20,
                    'max_portfolio_drawdown': 0.15,
                    'stop_loss_threshold': 0.05,
                    'rebalance_threshold': 0.02,
                    'cash_buffer': 0.05
                },
                'regime_adjustments': {
                    'high_volatility': {
                        'max_position_size_multiplier': 0.7,
                        'stop_loss_multiplier': 0.6,
                        'cash_buffer_multiplier': 2.0
                    },
                    'low_volatility': {
                        'max_position_size_multiplier': 1.2,
                        'stop_loss_multiplier': 1.6,
                        'cash_buffer_multiplier': 0.5
                    }
                }
            }
        }
        
        self._save_yaml_file(default_risk, self.default_files['risk'])