"""
Configuration Management Module for HierarchicalSystemOrchestrator
================================================================

Handles system configuration, validation, and management.
Extracted from the main orchestrator for better maintainability.

CONFIGURATION ARCHITECTURE NOTES (Rule 1, Section 7):
-----------------------------------------------------
This file contains ORCHESTRATOR-SPECIFIC configurations that are:
1. Used ONLY by HierarchicalSystemOrchestrator (not shared)
2. Tightly coupled with ConfigurationManager (runtime validation)
3. Implementation details (not domain configurations)

These configs are DISTINCT from:
- core_engine/config/system_config.py (system-wide settings)
- core_engine/config/component_config.py (domain configs: data, risk, strategies)

Why configs remain here (NOT consolidated):
✅ Orchestrator-internal implementation details
✅ Not shared across multiple components
✅ Include complex runtime validation logic
✅ Encapsulated with ConfigurationManager

This follows Rule 1, Section 7 principle:
"Centralized config for SHARED domain configurations"
Component-internal configs can remain with the component.

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Modular Architecture)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class SystemOrchestrationConfig:
    """Configuration for system orchestration"""

    # Initialization settings
    component_startup_timeout: int = 60  # seconds
    initialization_retry_attempts: int = 3
    graceful_shutdown_timeout: int = 30  # seconds

    # Monitoring settings
    health_check_interval: int = 30      # seconds
    performance_monitoring_interval: int = 5  # seconds

    # Authority and governance
    enforce_hierarchical_control: bool = True
    require_risk_manager_authorization: bool = True
    emergency_override_enabled: bool = True

    # Escalation settings
    max_component_errors: int = 5
    escalation_timeout: int = 300  # 5 minutes

    # Resource management
    max_concurrent_operations: int = 100
    resource_allocation_timeout: int = 10  # seconds

@dataclass
class ComponentConfig:
    """Configuration for individual components"""
    name: str
    enabled: bool = True
    initialization_order: int = 100
    health_check_interval: int = 30
    max_error_count: int = 5
    timeout: int = 60
    retry_attempts: int = 3
    custom_settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """Security configuration for the orchestrator"""
    enable_audit_logging: bool = True
    audit_log_level: str = "INFO"
    max_audit_entries: int = 10000
    enable_authorization_checks: bool = True
    session_timeout: int = 3600  # 1 hour
    max_failed_attempts: int = 5

@dataclass
class PerformanceConfig:
    """Performance configuration for the orchestrator"""
    enable_performance_monitoring: bool = True
    metrics_collection_interval: int = 5  # seconds
    max_metrics_history: int = 1000
    enable_profiling: bool = False
    memory_threshold_mb: int = 1024
    cpu_threshold_percent: float = 80.0

class ConfigurationManager:
    """Manages system configuration, validation, and runtime updates"""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration manager"""

        # Load base configuration
        self.system_config = SystemOrchestrationConfig(**(config_dict or {}))

        # Initialize sub-configurations
        self.component_configs: Dict[str, ComponentConfig] = {}
        self.security_config = SecurityConfig()
        self.performance_config = PerformanceConfig()

        # Configuration metadata
        self.config_version = "1.0.0"
        self.last_updated = datetime.now()
        self.config_source = "default"

        # Validation results
        self.validation_errors: List[str] = []
        self.is_valid = True

        # Validate configuration on initialization
        self._validate_configuration()

        logger.info("📋 ConfigurationManager initialized")

    def _validate_configuration(self) -> None:
        """Validate all configuration settings"""

        self.validation_errors.clear()

        try:
            # Validate system configuration
            self._validate_system_config()

            # Validate security configuration
            self._validate_security_config()

            # Validate performance configuration
            self._validate_performance_config()

            # Validate component configurations
            self._validate_component_configs()

            self.is_valid = len(self.validation_errors) == 0

            if self.is_valid:
                logger.info("✅ Configuration validation passed")
            else:
                logger.warning(f"⚠️ Configuration validation failed: {len(self.validation_errors)} errors")
                for error in self.validation_errors:
                    logger.warning(f"  - {error}")

        except Exception as e:
            self.validation_errors.append(f"Configuration validation error: {e}")
            self.is_valid = False
            logger.error(f"❌ Configuration validation exception: {e}")

    def _validate_system_config(self) -> None:
        """Validate system orchestration configuration"""

        config = self.system_config

        # Validate timeouts
        if config.component_startup_timeout <= 0:
            self.validation_errors.append("component_startup_timeout must be positive")

        if config.graceful_shutdown_timeout <= 0:
            self.validation_errors.append("graceful_shutdown_timeout must be positive")

        # Validate intervals
        if config.health_check_interval <= 0:
            self.validation_errors.append("health_check_interval must be positive")

        if config.performance_monitoring_interval <= 0:
            self.validation_errors.append("performance_monitoring_interval must be positive")

        # Validate limits
        if config.max_component_errors <= 0:
            self.validation_errors.append("max_component_errors must be positive")

        if config.max_concurrent_operations <= 0:
            self.validation_errors.append("max_concurrent_operations must be positive")

    def _validate_security_config(self) -> None:
        """Validate security configuration"""

        config = self.security_config

        # Validate audit settings
        if config.max_audit_entries <= 0:
            self.validation_errors.append("max_audit_entries must be positive")

        if config.audit_log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.validation_errors.append("audit_log_level must be a valid log level")

        # Validate session settings
        if config.session_timeout <= 0:
            self.validation_errors.append("session_timeout must be positive")

        if config.max_failed_attempts <= 0:
            self.validation_errors.append("max_failed_attempts must be positive")

    def _validate_performance_config(self) -> None:
        """Validate performance configuration"""

        config = self.performance_config

        # Validate monitoring settings
        if config.metrics_collection_interval <= 0:
            self.validation_errors.append("metrics_collection_interval must be positive")

        if config.max_metrics_history <= 0:
            self.validation_errors.append("max_metrics_history must be positive")

        # Validate thresholds
        if config.memory_threshold_mb <= 0:
            self.validation_errors.append("memory_threshold_mb must be positive")

        if not (0 < config.cpu_threshold_percent <= 100):
            self.validation_errors.append("cpu_threshold_percent must be between 0 and 100")

    def _validate_component_configs(self) -> None:
        """Validate component configurations"""

        for name, config in self.component_configs.items():
            if config.initialization_order < 0:
                self.validation_errors.append(f"Component {name}: initialization_order must be non-negative")

            if config.health_check_interval <= 0:
                self.validation_errors.append(f"Component {name}: health_check_interval must be positive")

            if config.max_error_count <= 0:
                self.validation_errors.append(f"Component {name}: max_error_count must be positive")

            if config.timeout <= 0:
                self.validation_errors.append(f"Component {name}: timeout must be positive")

    def add_component_config(self, name: str, config: ComponentConfig) -> None:
        """Add configuration for a specific component"""

        self.component_configs[name] = config
        self.last_updated = datetime.now()

        # Re-validate after adding component config
        self._validate_component_configs()

        logger.info(f"📋 Added configuration for component: {name}")

    def get_component_config(self, name: str) -> Optional[ComponentConfig]:
        """Get configuration for a specific component"""

        return self.component_configs.get(name)

    def update_system_config(self, **kwargs) -> None:
        """Update system configuration parameters"""

        try:
            # Update configuration
            for key, value in kwargs.items():
                if hasattr(self.system_config, key):
                    setattr(self.system_config, key, value)
                    logger.info(f"📋 Updated system config: {key} = {value}")
                else:
                    logger.warning(f"⚠️ Unknown system config parameter: {key}")

            self.last_updated = datetime.now()

            # Re-validate configuration
            self._validate_configuration()

        except Exception as e:
            logger.error(f"❌ Failed to update system configuration: {e}")

    def update_security_config(self, **kwargs) -> None:
        """Update security configuration parameters"""

        try:
            for key, value in kwargs.items():
                if hasattr(self.security_config, key):
                    setattr(self.security_config, key, value)
                    logger.info(f"🔒 Updated security config: {key} = {value}")
                else:
                    logger.warning(f"⚠️ Unknown security config parameter: {key}")

            self.last_updated = datetime.now()
            self._validate_security_config()

        except Exception as e:
            logger.error(f"❌ Failed to update security configuration: {e}")

    def update_performance_config(self, **kwargs) -> None:
        """Update performance configuration parameters"""

        try:
            for key, value in kwargs.items():
                if hasattr(self.performance_config, key):
                    setattr(self.performance_config, key, value)
                    logger.info(f"⚡ Updated performance config: {key} = {value}")
                else:
                    logger.warning(f"⚠️ Unknown performance config parameter: {key}")

            self.last_updated = datetime.now()
            self._validate_performance_config()

        except Exception as e:
            logger.error(f"❌ Failed to update performance configuration: {e}")

    def load_from_file(self, file_path: str) -> bool:
        """Load configuration from JSON file"""

        try:
            if not os.path.exists(file_path):
                logger.error(f"❌ Configuration file not found: {file_path}")
                return False

            with open(file_path, 'r') as f:
                config_data = json.load(f)

            # Update configurations from file
            if 'system' in config_data:
                self.update_system_config(**config_data['system'])

            if 'security' in config_data:
                self.update_security_config(**config_data['security'])

            if 'performance' in config_data:
                self.update_performance_config(**config_data['performance'])

            if 'components' in config_data:
                for name, comp_config in config_data['components'].items():
                    self.add_component_config(name, ComponentConfig(name=name, **comp_config))

            self.config_source = file_path
            logger.info(f"✅ Configuration loaded from: {file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load configuration from {file_path}: {e}")
            return False

    def save_to_file(self, file_path: str) -> bool:
        """Save current configuration to JSON file"""

        try:
            config_data = {
                'metadata': {
                    'version': self.config_version,
                    'last_updated': self.last_updated.isoformat(),
                    'source': self.config_source
                },
                'system': {
                    'component_startup_timeout': self.system_config.component_startup_timeout,
                    'initialization_retry_attempts': self.system_config.initialization_retry_attempts,
                    'graceful_shutdown_timeout': self.system_config.graceful_shutdown_timeout,
                    'health_check_interval': self.system_config.health_check_interval,
                    'performance_monitoring_interval': self.system_config.performance_monitoring_interval,
                    'enforce_hierarchical_control': self.system_config.enforce_hierarchical_control,
                    'require_risk_manager_authorization': self.system_config.require_risk_manager_authorization,
                    'emergency_override_enabled': self.system_config.emergency_override_enabled,
                    'max_component_errors': self.system_config.max_component_errors,
                    'escalation_timeout': self.system_config.escalation_timeout,
                    'max_concurrent_operations': self.system_config.max_concurrent_operations,
                    'resource_allocation_timeout': self.system_config.resource_allocation_timeout
                },
                'security': {
                    'enable_audit_logging': self.security_config.enable_audit_logging,
                    'audit_log_level': self.security_config.audit_log_level,
                    'max_audit_entries': self.security_config.max_audit_entries,
                    'enable_authorization_checks': self.security_config.enable_authorization_checks,
                    'session_timeout': self.security_config.session_timeout,
                    'max_failed_attempts': self.security_config.max_failed_attempts
                },
                'performance': {
                    'enable_performance_monitoring': self.performance_config.enable_performance_monitoring,
                    'metrics_collection_interval': self.performance_config.metrics_collection_interval,
                    'max_metrics_history': self.performance_config.max_metrics_history,
                    'enable_profiling': self.performance_config.enable_profiling,
                    'memory_threshold_mb': self.performance_config.memory_threshold_mb,
                    'cpu_threshold_percent': self.performance_config.cpu_threshold_percent
                },
                'components': {
                    name: {
                        'enabled': config.enabled,
                        'initialization_order': config.initialization_order,
                        'health_check_interval': config.health_check_interval,
                        'max_error_count': config.max_error_count,
                        'timeout': config.timeout,
                        'retry_attempts': config.retry_attempts,
                        'custom_settings': config.custom_settings
                    }
                    for name, config in self.component_configs.items()
                }
            }

            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"✅ Configuration saved to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save configuration to {file_path}: {e}")
            return False

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get comprehensive configuration summary"""

        return {
            'metadata': {
                'version': self.config_version,
                'last_updated': self.last_updated.isoformat(),
                'source': self.config_source,
                'is_valid': self.is_valid,
                'validation_errors': self.validation_errors
            },
            'system_config': {
                'startup_timeout': self.system_config.component_startup_timeout,
                'shutdown_timeout': self.system_config.graceful_shutdown_timeout,
                'health_check_interval': self.system_config.health_check_interval,
                'max_concurrent_operations': self.system_config.max_concurrent_operations,
                'hierarchical_control': self.system_config.enforce_hierarchical_control
            },
            'security_config': {
                'audit_logging': self.security_config.enable_audit_logging,
                'authorization_checks': self.security_config.enable_authorization_checks,
                'session_timeout': self.security_config.session_timeout
            },
            'performance_config': {
                'monitoring_enabled': self.performance_config.enable_performance_monitoring,
                'metrics_interval': self.performance_config.metrics_collection_interval,
                'memory_threshold': self.performance_config.memory_threshold_mb,
                'cpu_threshold': self.performance_config.cpu_threshold_percent
            },
            'component_count': len(self.component_configs)
        }

    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values"""

        try:
            self.system_config = SystemOrchestrationConfig()
            self.security_config = SecurityConfig()
            self.performance_config = PerformanceConfig()
            self.component_configs.clear()

            self.last_updated = datetime.now()
            self.config_source = "default"

            self._validate_configuration()

            logger.info("🔄 Configuration reset to defaults")

        except Exception as e:
            logger.error(f"❌ Failed to reset configuration: {e}")
