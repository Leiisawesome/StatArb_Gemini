"""
ConfigBridge: Core System ↔ Backtesting Framework Integration

This module provides a bridge between the core system's configuration management
and the backtesting framework's configuration requirements.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
from enum import Enum
import json
import yaml

logger = logging.getLogger(__name__)


class ConfigMode(Enum):
    """Configuration bridge operation modes"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"


class ConfigStatus(Enum):
    """Configuration status levels"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    VALIDATING = "validating"


@dataclass
class ConfigBridgeConfig:
    """Configuration for ConfigBridge"""
    config_mode: ConfigMode = ConfigMode.BACKTESTING
    enable_config_validation: bool = True
    enable_config_caching: bool = True
    enable_config_sync: bool = True
    max_concurrent_operations: int = 10
    timeout_seconds: float = 10.0
    cache_size: int = 1000
    config_file_paths: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigBridgeResult:
    """Result from ConfigBridge operations"""
    operation_type: str
    config_id: str
    data: Union[pd.DataFrame, Dict[str, Any]]
    success: bool
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class ConfigSnapshot:
    """Configuration snapshot with current state"""
    config_id: str
    config_type: str
    config_data: Dict[str, Any]
    validation_status: ConfigStatus
    last_updated: datetime
    version: str
    environment: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfigValidationReport:
    """Configuration validation report"""
    config_id: str
    validation_status: ConfigStatus
    validation_score: float
    total_rules: int
    passed_rules: int
    failed_rules: int
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class ConfigBridge:
    """Bridge between core system configuration management and backtesting framework."""
    
    def __init__(self, config: Optional[ConfigBridgeConfig] = None):
        """Initialize ConfigBridge with configuration"""
        self.config = config or ConfigBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.ConfigBridge")
        
        # Initialize caching and performance tracking
        self._config_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._performance_stats = {
            'total_operations': 0,
            'production_operations': 0,
            'backtesting_operations': 0,
            'cached_operations': 0,
            'errors': 0,
            'avg_processing_time': 0.0,
            'total_configs': 0
        }
        
        # Thread pool for concurrent operations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_operations)
        
        # Initialize default configs
        self._initialize_default_configs()
        
        self.logger.info(f"ConfigBridge initialized in {self.config.config_mode.value} mode")
    
    def _initialize_default_configs(self):
        """Initialize default configuration templates"""
        self.default_configs = {
            'trading_config': {
                'max_position_size': 0.1,
                'max_portfolio_risk': 0.02,
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.10,
                'max_drawdown': 0.15,
                'daily_loss_limit': 0.05
            },
            'risk_config': {
                'var_confidence_level': 0.95,
                'var_time_horizon': 1,
                'max_volatility': 0.25,
                'max_beta': 1.5,
                'max_correlation': 0.8
            },
            'execution_config': {
                'max_slippage': 0.001,
                'min_trade_size': 100,
                'max_trade_size': 10000,
                'execution_timeout': 30,
                'retry_attempts': 3
            },
            'data_config': {
                'data_source': 'polygon',
                'update_frequency': 1,
                'cache_duration': 300,
                'max_data_age': 3600,
                'quality_threshold': 0.95
            }
        }
    
    async def get_config_snapshot(self, config_id: str) -> ConfigSnapshot:
        """Get current configuration snapshot"""
        start_time_ms = time.time()
        
        try:
            # Check cache first
            cache_key = f"config_{config_id}"
            if cache_key in self._config_cache:
                cached_data, cache_time = self._config_cache[cache_key]
                if datetime.now() - cache_time < timedelta(minutes=5):  # 5-minute cache
                    self._performance_stats['cached_operations'] += 1
                    return cached_data
            
            # Create config snapshot
            snapshot = self._create_config_snapshot(config_id)
            
            # Cache the result
            self._config_cache[cache_key] = (snapshot, datetime.now())
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error getting config snapshot for {config_id}: {e}")
            self._performance_stats['errors'] += 1
            return self._create_fallback_snapshot(config_id)
    
    async def update_config(
        self,
        config_id: str,
        config_data: Dict[str, Any],
        config_type: str = "trading"
    ) -> ConfigBridgeResult:
        """Update configuration"""
        start_time_ms = time.time()
        
        try:
            # Validate configuration
            if not self._validate_config(config_data, config_type):
                raise ValueError(f"Configuration validation failed for {config_id}")
            
            # Mock config update
            result = {
                'config_id': config_id,
                'config_type': config_type,
                'config_data': config_data,
                'timestamp': datetime.now(),
                'version': '1.0.0'
            }
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return ConfigBridgeResult(
                operation_type='config_update',
                config_id=config_id,
                data=result,
                success=True,
                timestamp=datetime.now(),
                source='backtesting',
                processing_time_ms=(time.time() - start_time_ms) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Error updating config for {config_id}: {e}")
            self._performance_stats['errors'] += 1
            
            return ConfigBridgeResult(
                operation_type='config_update',
                config_id=config_id,
                data={},
                success=False,
                timestamp=datetime.now(),
                source='fallback',
                processing_time_ms=(time.time() - start_time_ms) * 1000,
                error_message=str(e)
            )
    
    async def validate_config(
        self,
        config_id: str,
        config_data: Dict[str, Any]
    ) -> ConfigValidationReport:
        """Validate configuration"""
        try:
            # Validate configuration data
            validation_score = self._calculate_validation_score(config_data)
            total_rules = len(self.config.validation_rules) if self.config.validation_rules else 10
            passed_rules = int(validation_score * total_rules)
            failed_rules = total_rules - passed_rules
            
            # Generate issues and recommendations
            issues = self._identify_config_issues(config_data)
            recommendations = self._generate_config_recommendations(issues, validation_score)
            
            status = ConfigStatus.ACTIVE if validation_score >= 0.8 else ConfigStatus.ERROR
            
            return ConfigValidationReport(
                config_id=config_id,
                validation_status=status,
                validation_score=validation_score,
                total_rules=total_rules,
                passed_rules=passed_rules,
                failed_rules=failed_rules,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error validating config for {config_id}: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear configuration cache"""
        self._config_cache.clear()
        self.logger.info("Configuration cache cleared")
    
    def _create_config_snapshot(self, config_id: str) -> ConfigSnapshot:
        """Create configuration snapshot"""
        # Get config type from ID
        config_type = config_id.split('_')[0] if '_' in config_id else 'trading'
        
        # Get config data
        config_data = self.default_configs.get(config_type, {})
        
        return ConfigSnapshot(
            config_id=config_id,
            config_type=config_type,
            config_data=config_data,
            validation_status=ConfigStatus.ACTIVE,
            last_updated=datetime.now(),
            version='1.0.0',
            environment=self.config.config_mode.value
        )
    
    def _create_fallback_snapshot(self, config_id: str) -> ConfigSnapshot:
        """Create fallback configuration snapshot"""
        return ConfigSnapshot(
            config_id=config_id,
            config_type='fallback',
            config_data={},
            validation_status=ConfigStatus.ERROR,
            last_updated=datetime.now(),
            version='0.0.0',
            environment='fallback'
        )
    
    def _validate_config(self, config_data: Dict[str, Any], config_type: str) -> bool:
        """Validate configuration data"""
        try:
            if not config_data:
                return False
            
            # Basic validation based on config type
            if config_type == 'trading':
                required_keys = ['max_position_size', 'max_portfolio_risk']
            elif config_type == 'risk':
                required_keys = ['var_confidence_level', 'max_volatility']
            elif config_type == 'execution':
                required_keys = ['max_slippage', 'min_trade_size']
            elif config_type == 'data':
                required_keys = ['data_source', 'update_frequency']
            else:
                required_keys = []
            
            # Check required keys
            for key in required_keys:
                if key not in config_data:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating config: {e}")
            return False
    
    def _calculate_validation_score(self, config_data: Dict[str, Any]) -> float:
        """Calculate configuration validation score"""
        try:
            if not config_data:
                return 0.0
            
            # Simple validation scoring
            score = 0.0
            total_checks = 0
            
            # Check for required fields
            required_fields = ['max_position_size', 'max_portfolio_risk', 'stop_loss_pct']
            for field in required_fields:
                total_checks += 1
                if field in config_data:
                    score += 1.0
            
            # Check for valid ranges
            if 'max_position_size' in config_data:
                total_checks += 1
                if 0 < config_data['max_position_size'] <= 1.0:
                    score += 1.0
            
            if 'max_portfolio_risk' in config_data:
                total_checks += 1
                if 0 < config_data['max_portfolio_risk'] <= 0.1:
                    score += 1.0
            
            return score / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating validation score: {e}")
            return 0.0
    
    def _identify_config_issues(self, config_data: Dict[str, Any]) -> List[str]:
        """Identify configuration issues"""
        issues = []
        
        try:
            if not config_data:
                issues.append("Empty configuration data")
                return issues
            
            # Check for missing required fields
            required_fields = ['max_position_size', 'max_portfolio_risk']
            for field in required_fields:
                if field not in config_data:
                    issues.append(f"Missing required field: {field}")
            
            # Check for invalid values
            if 'max_position_size' in config_data:
                value = config_data['max_position_size']
                if value <= 0 or value > 1.0:
                    issues.append(f"Invalid max_position_size: {value} (should be 0-1)")
            
            if 'max_portfolio_risk' in config_data:
                value = config_data['max_portfolio_risk']
                if value <= 0 or value > 0.1:
                    issues.append(f"Invalid max_portfolio_risk: {value} (should be 0-0.1)")
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Error identifying config issues: {e}")
            return ["Error in issue identification"]
    
    def _generate_config_recommendations(self, issues: List[str], validation_score: float) -> List[str]:
        """Generate configuration recommendations"""
        recommendations = []
        
        try:
            if validation_score < 0.8:
                recommendations.append("Review configuration validation rules")
            
            if any("missing" in issue.lower() for issue in issues):
                recommendations.append("Add missing required configuration fields")
            
            if any("invalid" in issue.lower() for issue in issues):
                recommendations.append("Verify configuration value ranges")
            
            if not recommendations:
                recommendations.append("Configuration is valid and ready for use")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating config recommendations: {e}")
            return ["Error in recommendation generation"]
    
    def _update_performance_stats(self, source: str, processing_time: float):
        """Update performance statistics"""
        try:
            self._performance_stats['total_operations'] += 1
            self._performance_stats['total_configs'] += 1
            
            if source == 'production':
                self._performance_stats['production_operations'] += 1
            elif source == 'backtesting':
                self._performance_stats['backtesting_operations'] += 1
            
            # Update average processing time
            total_operations = self._performance_stats['total_operations']
            current_avg = self._performance_stats['avg_processing_time']
            new_avg = ((current_avg * (total_operations - 1)) + processing_time) / total_operations
            self._performance_stats['avg_processing_time'] = new_avg
            
        except Exception as e:
            self.logger.error(f"Error updating performance stats: {e}")


def create_config_bridge(config: Optional[ConfigBridgeConfig] = None) -> ConfigBridge:
    """Factory function to create ConfigBridge instance"""
    return ConfigBridge(config)


def get_config_for_backtesting(config_id: str) -> ConfigSnapshot:
    """Convenience function for backtesting configuration retrieval"""
    config = ConfigBridgeConfig(config_mode=ConfigMode.BACKTESTING)
    bridge = create_config_bridge(config)
    
    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # Return fallback snapshot as fallback
        return ConfigSnapshot(
            config_id=config_id,
            config_type='fallback',
            config_data={},
            validation_status=ConfigStatus.ERROR,
            last_updated=datetime.now(),
            version='0.0.0',
            environment='fallback'
        )
    except RuntimeError:
        # No event loop running, we can create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            snapshot = loop.run_until_complete(
                bridge.get_config_snapshot(config_id)
            )
            return snapshot
        finally:
            loop.close() 