#!/usr/bin/env python3
"""
Production Configuration
Phase 4: Production Deployment & Monitoring
"""

import logging
import yaml
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class ProductionConfig:
    """Production configuration management"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'production_config.yaml'
        self.config = self._load_config()
        self.config_history = []
        
        logger.info("Initialized ProductionConfig")
    
    def _load_config(self) -> Dict:
        """Load production configuration"""
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded production config from {self.config_path}")
                return config
            else:
                # Default production configuration
                default_config = {
                    'environment': {
                        'name': 'production',
                        'version': '1.0.0',
                        'debug': False,
                        'log_level': 'INFO'
                    },
                    'database': {
                        'clickhouse': {
                            'host': 'clickhouse-service',
                            'port': 9000,
                            'database': 'trading_data',
                            'username': 'default',
                            'password': 'password',
                            'pool_size': 20,
                            'timeout': 30
                        },
                        'redis': {
                            'host': 'redis-service',
                            'port': 6379,
                            'password': None,
                            'db': 0,
                            'pool_size': 10,
                            'timeout': 5
                        }
                    },
                    'trading': {
                        'max_positions': 100,
                        'max_leverage': 5.0,
                        'risk_limits': {
                            'max_drawdown': 0.15,
                            'max_var': 0.05,
                            'max_correlation': 0.8
                        },
                        'execution': {
                            'default_slippage': 0.001,
                            'max_slippage': 0.005,
                            'execution_timeout': 30
                        }
                    },
                    'monitoring': {
                        'metrics_interval': 30,
                        'health_check_interval': 60,
                        'alert_thresholds': {
                            'cpu_usage': 0.9,
                            'memory_usage': 0.85,
                            'disk_usage': 0.9,
                            'error_rate': 0.05
                        }
                    },
                    'security': {
                        'api_key_required': True,
                        'rate_limiting': {
                            'requests_per_minute': 1000,
                            'burst_limit': 100
                        },
                        'ssl_enabled': True,
                        'cors_origins': ['https://trading.example.com']
                    },
                    'logging': {
                        'level': 'INFO',
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        'handlers': {
                            'file': {
                                'enabled': True,
                                'filename': '/var/log/trading-system/app.log',
                                'max_size': '100MB',
                                'backup_count': 5
                            },
                            'console': {
                                'enabled': True
                            }
                        }
                    }
                }
                
                # Save default config
                self._save_config(default_config)
                logger.info("Created default production configuration")
                return default_config
                
        except Exception as e:
            logger.error(f"Failed to load production config: {e}")
            return {}
    
    def _save_config(self, config: Dict):
        """Save configuration to file"""
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def get_config(self, section: str = None) -> Dict:
        """Get configuration section or entire config"""
        
        if section:
            return self.config.get(section, {})
        return self.config
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """Update configuration value"""
        
        try:
            # Store current config in history
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'section': section,
                'key': key,
                'old_value': self.config.get(section, {}).get(key),
                'new_value': value
            })
            
            # Update configuration
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            
            # Save updated configuration
            self._save_config(self.config)
            
            logger.info(f"Configuration updated: {section}.{key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    def validate_config(self) -> Dict:
        """Validate production configuration"""
        
        try:
            logger.info("Validating production configuration...")
            
            validation_results = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'validation_date': datetime.now().isoformat()
            }
            
            # Validate environment settings
            environment = self.config.get('environment', {})
            if not environment.get('name'):
                validation_results['errors'].append("Environment name not specified")
                validation_results['valid'] = False
            
            if environment.get('debug', False):
                validation_results['warnings'].append("Debug mode enabled in production")
            
            # Validate database settings
            database = self.config.get('database', {})
            for db_name, db_config in database.items():
                if not db_config.get('host'):
                    validation_results['errors'].append(f"Database host not specified for {db_name}")
                    validation_results['valid'] = False
                
                if not db_config.get('port'):
                    validation_results['errors'].append(f"Database port not specified for {db_name}")
                    validation_results['valid'] = False
            
            # Validate trading settings
            trading = self.config.get('trading', {})
            if trading.get('max_leverage', 0) > 10:
                validation_results['warnings'].append("High leverage setting detected")
            
            risk_limits = trading.get('risk_limits', {})
            if risk_limits.get('max_drawdown', 0) > 0.2:
                validation_results['warnings'].append("High max drawdown setting")
            
            # Validate monitoring settings
            monitoring = self.config.get('monitoring', {})
            if monitoring.get('metrics_interval', 0) < 10:
                validation_results['warnings'].append("Very frequent metrics collection")
            
            # Validate security settings
            security = self.config.get('security', {})
            if not security.get('api_key_required', False):
                validation_results['warnings'].append("API key not required")
            
            if not security.get('ssl_enabled', False):
                validation_results['warnings'].append("SSL not enabled")
            
            logger.info(f"Configuration validation: {validation_results['valid']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {'valid': False, 'errors': [str(e)], 'warnings': []}
    
    def get_config_summary(self) -> Dict:
        """Get configuration summary"""
        
        return {
            'config_path': self.config_path,
            'config_sections': list(self.config.keys()),
            'config_history_count': len(self.config_history),
            'last_modified': datetime.now().isoformat(),
            'validation_status': self.validate_config()['valid']
        }
    
    def export_config(self, format: str = 'yaml') -> str:
        """Export configuration in specified format"""
        
        try:
            if format.lower() == 'yaml':
                return yaml.dump(self.config, default_flow_style=False, indent=2)
            elif format.lower() == 'json':
                return json.dumps(self.config, indent=2)
            else:
                logger.warning(f"Unsupported export format: {format}")
                return str(self.config)
                
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return ""
    
    def backup_config(self) -> bool:
        """Create configuration backup"""
        
        try:
            backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with open(backup_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create configuration backup: {e}")
            return False
    
    def restore_config(self, backup_path: str) -> bool:
        """Restore configuration from backup"""
        
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            with open(backup_path, 'r') as f:
                backup_config = yaml.safe_load(f)
            
            # Store current config in history
            self.config_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'restore',
                'backup_path': backup_path
            })
            
            # Restore configuration
            self.config = backup_config
            self._save_config(self.config)
            
            logger.info(f"Configuration restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            return False
