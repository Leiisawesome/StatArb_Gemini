"""
Base Configuration and Strategy Definition Classes

Core base classes for the trading strategy layer including configuration
management, strategy definitions, and result data structures.

Author: Pro Quant Desk Trader
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import json


class StrategyType(Enum):
    """Strategy types enumeration"""
    MOMENTUM = "momentum"
    PAIR_TRADING = "pair_trading"
    MEAN_REVERSION = "mean_reversion"
    CUSTOM = "custom"


class StrategyStatus(Enum):
    """Strategy status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    TESTING = "testing"


@dataclass
class BaseConfig:
    """Base configuration class for all components"""
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    created_date: datetime = field(default_factory=datetime.now)
    updated_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseConfig':
        """Create configuration from dictionary"""
        return cls(
            name=data['name'],
            version=data.get('version', '1.0.0'),
            description=data.get('description'),
            created_date=datetime.fromisoformat(data.get('created_date', datetime.now().isoformat())),
            updated_date=datetime.fromisoformat(data.get('updated_date', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )


@dataclass
class ParserConfig(BaseConfig):
    """Configuration for strategy parsers"""
    schema_validation_enabled: bool = True
    strict_mode: bool = False
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    max_file_size_mb: int = 10
    allowed_extensions: List[str] = field(default_factory=lambda: ['.json'])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parser configuration to dictionary"""
        base_dict = super().to_dict()
        base_dict.update({
            'schema_validation_enabled': self.schema_validation_enabled,
            'strict_mode': self.strict_mode,
            'cache_enabled': self.cache_enabled,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'max_file_size_mb': self.max_file_size_mb,
            'allowed_extensions': self.allowed_extensions
        })
        return base_dict


@dataclass
class StrategyConfig:
    """Configuration for trading strategies"""
    # Required fields (no defaults)
    strategy_id: str
    strategy_type: StrategyType
    name: str
    
    # Optional fields with defaults
    version: str = "1.0.0"
    description: Optional[str] = None
    status: StrategyStatus = StrategyStatus.DRAFT
    created_date: datetime = field(default_factory=datetime.now)
    updated_date: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Strategy parameters
    signal_generation: Dict[str, Any] = field(default_factory=dict)
    risk_management: Dict[str, Any] = field(default_factory=dict)
    entry_exit_logic: Dict[str, Any] = field(default_factory=dict)
    execution: Dict[str, Any] = field(default_factory=dict)
    portfolio_management: Dict[str, Any] = field(default_factory=dict)
    
    # Performance parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy configuration to dictionary"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat(),
            'metadata': self.metadata,
            'strategy_id': self.strategy_id,
            'strategy_type': self.strategy_type.value,
            'status': self.status.value,
            'signal_generation': self.signal_generation,
            'risk_management': self.risk_management,
            'entry_exit_logic': self.entry_exit_logic,
            'execution': self.execution,
            'portfolio_management': self.portfolio_management,
            'parameters': self.parameters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyConfig':
        """Create strategy configuration from dictionary"""
        return cls(
            name=data['name'],
            strategy_id=data['strategy_id'],
            strategy_type=StrategyType(data['strategy_type']),
            status=StrategyStatus(data.get('status', 'draft')),
            version=data.get('version', '1.0.0'),
            description=data.get('description'),
            created_date=datetime.fromisoformat(data.get('created_date', datetime.now().isoformat())),
            updated_date=datetime.fromisoformat(data.get('updated_date', datetime.now().isoformat())),
            metadata=data.get('metadata', {}),
            signal_generation=data.get('signal_generation', {}),
            risk_management=data.get('risk_management', {}),
            entry_exit_logic=data.get('entry_exit_logic', {}),
            execution=data.get('execution', {}),
            portfolio_management=data.get('portfolio_management', {}),
            parameters=data.get('parameters', {})
        )


@dataclass
class StrategyResult:
    """Result data structure for strategy execution"""
    strategy_id: str
    execution_time: datetime
    signals: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, float] = field(default_factory=dict)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class StrategyExecutionResult:
    """Result data structure for strategy execution with trading actions"""
    strategy_id: str
    symbol: str
    action: str  # BUY, SELL, HOLD, ERROR
    position_size: float
    entry_price: float
    stop_loss: float
    take_profit: float
    signal_strength: float
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy result to dictionary"""
        return {
            'strategy_id': self.strategy_id,
            'execution_time': self.execution_time.isoformat(),
            'signals': self.signals,
            'positions': self.positions,
            'orders': self.orders,
            'performance_metrics': self.performance_metrics,
            'risk_metrics': self.risk_metrics,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyResult':
        """Create strategy result from dictionary"""
        return cls(
            strategy_id=data['strategy_id'],
            execution_time=datetime.fromisoformat(data['execution_time']),
            signals=data.get('signals', {}),
            positions=data.get('positions', {}),
            orders=data.get('orders', []),
            performance_metrics=data.get('performance_metrics', {}),
            risk_metrics=data.get('risk_metrics', {}),
            errors=data.get('errors', []),
            warnings=data.get('warnings', [])
        )


class StrategyDefinition(ABC):
    """Abstract base class for strategy definitions"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._validate_config()
    
    @abstractmethod
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate trading signals from market data"""
        pass
    
    @abstractmethod
    def calculate_position_sizes(self, signals: Dict[str, float], market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate position sizes based on signals and market data"""
        pass
    
    @abstractmethod
    def validate_risk(self, positions: Dict[str, float], market_data: Dict[str, Any]) -> bool:
        """Validate risk parameters for positions"""
        pass
    
    @abstractmethod
    def should_enter_position(self, symbol: str, signal: float, market_data: Dict[str, Any]) -> bool:
        """Determine if should enter a position"""
        pass
    
    @abstractmethod
    def should_exit_position(self, symbol: str, position: float, market_data: Dict[str, Any]) -> bool:
        """Determine if should exit a position"""
        pass
    
    def _validate_config(self):
        """Validate strategy configuration"""
        if not self.config.strategy_id:
            raise ValueError("Strategy ID is required")
        
        if not self.config.signal_generation:
            raise ValueError("Signal generation configuration is required")
        
        if not self.config.risk_management:
            raise ValueError("Risk management configuration is required")
    
    def get_config(self) -> StrategyConfig:
        """Get strategy configuration"""
        return self.config
    
    def update_config(self, config: StrategyConfig):
        """Update strategy configuration"""
        self.config = config
        self._validate_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy definition to dictionary"""
        return {
            'config': self.config.to_dict(),
            'class_name': self.__class__.__name__
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyDefinition':
        """Create strategy definition from dictionary"""
        config = StrategyConfig.from_dict(data['config'])
        return cls(config)


class StrategyError(Exception):
    """Base exception for strategy-related errors"""
    pass


class StrategyValidationError(StrategyError):
    """Exception for strategy validation errors"""
    pass


class StrategyExecutionError(StrategyError):
    """Exception for strategy execution errors"""
    pass


class StrategyConfigurationError(StrategyError):
    """Exception for strategy configuration errors"""
    pass
