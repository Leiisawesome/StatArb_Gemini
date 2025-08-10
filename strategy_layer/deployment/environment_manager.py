"""
Environment Manager

Multi-environment deployment and configuration management.

Author: Pro Quant Desk Trader
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .strategy_deployer import EnvironmentType, DeploymentConfig


@dataclass
class EnvironmentConfig:
    """Configuration for a specific environment"""
    name: str
    environment_type: EnvironmentType
    description: str
    is_active: bool = True
    max_strategies: int = 10
    health_check_interval: int = 30
    monitoring_enabled: bool = True
    backup_enabled: bool = True
    auto_restart: bool = True
    resource_limits: Dict[str, float] = field(default_factory=dict)
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class EnvironmentManager:
    """Manages multiple deployment environments"""
    
    def __init__(self, config_file: str = "environments.json"):
        self.config_file = config_file
        self.logger = logging.getLogger(self.__class__.__name__)
        self.environments: Dict[str, EnvironmentConfig] = {}
        self.active_environment: Optional[str] = None
        
        # Load environments
        self._load_environments()
    
    def _load_environments(self):
        """Load environment configurations from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                for env_data in data.get('environments', []):
                    env_config = EnvironmentConfig(
                        name=env_data['name'],
                        environment_type=EnvironmentType(env_data['environment_type']),
                        description=env_data.get('description', ''),
                        is_active=env_data.get('is_active', True),
                        max_strategies=env_data.get('max_strategies', 10),
                        health_check_interval=env_data.get('health_check_interval', 30),
                        monitoring_enabled=env_data.get('monitoring_enabled', True),
                        backup_enabled=env_data.get('backup_enabled', True),
                        auto_restart=env_data.get('auto_restart', True),
                        resource_limits=env_data.get('resource_limits', {}),
                        custom_settings=env_data.get('custom_settings', {})
                    )
                    self.environments[env_config.name] = env_config
                
                # Set active environment
                active_env = data.get('active_environment')
                if active_env and active_env in self.environments:
                    self.active_environment = active_env
                
                self.logger.info(f"Loaded {len(self.environments)} environments")
            else:
                # Create default environments
                self._create_default_environments()
                
        except Exception as e:
            self.logger.error(f"Failed to load environments: {e}")
            self._create_default_environments()
    
    def _create_default_environments(self):
        """Create default environment configurations"""
        default_environments = [
            EnvironmentConfig(
                name="development",
                environment_type=EnvironmentType.DEVELOPMENT,
                description="Development environment for testing",
                max_strategies=5,
                health_check_interval=60,
                monitoring_enabled=True,
                backup_enabled=False,
                auto_restart=True
            ),
            EnvironmentConfig(
                name="staging",
                environment_type=EnvironmentType.STAGING,
                description="Staging environment for pre-production testing",
                max_strategies=10,
                health_check_interval=30,
                monitoring_enabled=True,
                backup_enabled=True,
                auto_restart=True
            ),
            EnvironmentConfig(
                name="paper_trading",
                environment_type=EnvironmentType.PAPER_TRADING,
                description="Paper trading environment for live testing",
                max_strategies=15,
                health_check_interval=15,
                monitoring_enabled=True,
                backup_enabled=True,
                auto_restart=True
            ),
            EnvironmentConfig(
                name="production",
                environment_type=EnvironmentType.PRODUCTION,
                description="Production environment for live trading",
                max_strategies=20,
                health_check_interval=10,
                monitoring_enabled=True,
                backup_enabled=True,
                auto_restart=True
            )
        ]
        
        for env in default_environments:
            self.environments[env.name] = env
        
        # Set development as active by default
        self.active_environment = "development"
        
        # Save default environments
        self._save_environments()
        
        self.logger.info("Created default environments")
    
    def _save_environments(self):
        """Save environment configurations to file"""
        try:
            data = {
                'environments': [
                    {
                        'name': env.name,
                        'environment_type': env.environment_type.value,
                        'description': env.description,
                        'is_active': env.is_active,
                        'max_strategies': env.max_strategies,
                        'health_check_interval': env.health_check_interval,
                        'monitoring_enabled': env.monitoring_enabled,
                        'backup_enabled': env.backup_enabled,
                        'auto_restart': env.auto_restart,
                        'resource_limits': env.resource_limits,
                        'custom_settings': env.custom_settings
                    }
                    for env in self.environments.values()
                ],
                'active_environment': self.active_environment
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save environments: {e}")
    
    def get_environment(self, name: str) -> Optional[EnvironmentConfig]:
        """Get environment configuration by name"""
        return self.environments.get(name)
    
    def get_active_environment(self) -> Optional[EnvironmentConfig]:
        """Get the currently active environment"""
        if self.active_environment:
            return self.environments.get(self.active_environment)
        return None
    
    def set_active_environment(self, name: str) -> bool:
        """Set the active environment"""
        if name in self.environments:
            self.active_environment = name
            self._save_environments()
            self.logger.info(f"Set active environment to: {name}")
            return True
        else:
            self.logger.error(f"Environment '{name}' not found")
            return False
    
    def add_environment(self, config: EnvironmentConfig) -> bool:
        """Add a new environment"""
        try:
            self.environments[config.name] = config
            self._save_environments()
            self.logger.info(f"Added environment: {config.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add environment {config.name}: {e}")
            return False
    
    def update_environment(self, name: str, config: EnvironmentConfig) -> bool:
        """Update an existing environment"""
        if name not in self.environments:
            self.logger.error(f"Environment '{name}' not found")
            return False
        
        try:
            self.environments[name] = config
            self._save_environments()
            self.logger.info(f"Updated environment: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update environment {name}: {e}")
            return False
    
    def remove_environment(self, name: str) -> bool:
        """Remove an environment"""
        if name not in self.environments:
            self.logger.error(f"Environment '{name}' not found")
            return False
        
        if name == self.active_environment:
            self.logger.error(f"Cannot remove active environment: {name}")
            return False
        
        try:
            del self.environments[name]
            self._save_environments()
            self.logger.info(f"Removed environment: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove environment {name}: {e}")
            return False
    
    def list_environments(self) -> List[EnvironmentConfig]:
        """List all environments"""
        return list(self.environments.values())
    
    def get_environment_names(self) -> List[str]:
        """Get list of environment names"""
        return list(self.environments.keys())
    
    def create_deployment_config(self, environment_name: str) -> Optional[DeploymentConfig]:
        """Create deployment config from environment"""
        env_config = self.get_environment(environment_name)
        if not env_config:
            return None
        
        return DeploymentConfig(
            environment=env_config.environment_type,
            max_concurrent_strategies=env_config.max_strategies,
            health_check_interval=env_config.health_check_interval,
            monitoring_enabled=env_config.monitoring_enabled,
            backup_enabled=env_config.backup_enabled,
            auto_restart_on_failure=env_config.auto_restart,
            max_memory_usage=env_config.resource_limits.get('max_memory_usage', 0.8),
            max_cpu_usage=env_config.resource_limits.get('max_cpu_usage', 0.9)
        )
    
    def validate_environment(self, name: str) -> bool:
        """Validate environment configuration"""
        env_config = self.get_environment(name)
        if not env_config:
            return False
        
        # Check required fields
        if not env_config.name or not env_config.environment_type:
            return False
        
        # Check resource limits
        if env_config.max_strategies <= 0:
            return False
        
        if env_config.health_check_interval <= 0:
            return False
        
        return True
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get summary of all environments"""
        summary = {
            'total_environments': len(self.environments),
            'active_environment': self.active_environment,
            'environments': {}
        }
        
        for name, config in self.environments.items():
            summary['environments'][name] = {
                'type': config.environment_type.value,
                'description': config.description,
                'is_active': config.is_active,
                'max_strategies': config.max_strategies,
                'monitoring_enabled': config.monitoring_enabled,
                'backup_enabled': config.backup_enabled
            }
        
        return summary
