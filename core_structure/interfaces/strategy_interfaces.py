"""
Strategy Interface Layer - Clean Architecture
===========================================

Professional interface definitions for strategy implementations.
Ensures clean separation between core orchestration and strategy logic.

This module provides the foundational contracts and base classes that all
strategy implementations must follow. It serves as the architectural foundation
for the unified strategy system.

Key Components:
- StrategyInterface: Protocol defining strategy contracts
- BaseStrategy: Abstract base class with common functionality  
- StrategyFactory: Factory pattern for strategy creation
- StrategyContext: Execution context data structure
- StrategyMetrics: Performance tracking framework

Author: Professional Trading System Architecture
Version: 3.0.0 (Updated for Consolidated Architecture)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd

# Core signal types
from ..components.signal_generation import TradingSignal, SignalType, SignalStrength
# Use canonical strategy types
from ..infrastructure import StrategyType, StrategyConfig


@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    total_signals: int = 0
    successful_signals: int = 0
    average_confidence: float = 0.0
    processing_time_ms: float = 0.0
    last_updated: datetime = None


@dataclass
class StrategyContext:
    """Context information for strategy execution"""
    market_data: pd.DataFrame
    portfolio_state: Dict[str, Any]
    risk_parameters: Dict[str, Any]
    timestamp: datetime
    strategy_config: Dict[str, Any]


class StrategyInterface(Protocol):
    """
    Strategy interface for clean delegation pattern.
    
    All strategy implementations must implement this interface
    to ensure proper separation of concerns.
    """
    
    @property
    def strategy_id(self) -> str:
        """Unique strategy identifier"""
        ...
    
    @property
    def strategy_type(self) -> StrategyType:
        """Strategy type classification"""
        ...
    
    @property
    def required_indicators(self) -> List[str]:
        """Required market data indicators"""
        ...
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration parameters"""
        ...
    
    async def generate_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate trading signals based on market context"""
        ...
    
    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        ...
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters dynamically"""
        ...


class BaseStrategy(ABC):
    """
    Base strategy implementation with common functionality.
    
    Provides framework for strategy implementations while
    maintaining clean separation from core engine logic.
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self._strategy_id = strategy_id
        self._config = config
        self._metrics = StrategyMetrics()
        self._last_signals: List[TradingSignal] = []
    
    @property
    def strategy_id(self) -> str:
        return self._strategy_id
    
    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """Strategy type - must be implemented by subclasses"""
        pass
    
    @property
    @abstractmethod
    def required_indicators(self) -> List[str]:
        """Required indicators - must be implemented by subclasses"""
        pass
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Base parameter validation"""
        required_params = self._get_required_parameters()
        for param in required_params:
            if param not in config:
                return False
        return True
    
    @abstractmethod
    def _get_required_parameters(self) -> List[str]:
        """Get list of required configuration parameters"""
        pass
    
    @abstractmethod
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Strategy-specific signal generation logic"""
        pass
    
    async def generate_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate signals with metrics tracking"""
        start_time = datetime.now()
        
        try:
            signals = await self._generate_strategy_signals(context)
            self._last_signals = signals
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_metrics(signals, processing_time)
            
            return signals
            
        except Exception as e:
            self._metrics.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            raise RuntimeError(f"Signal generation failed for {self.strategy_id}: {e}")
    
    def get_strategy_metrics(self) -> StrategyMetrics:
        return self._metrics
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy configuration"""
        self._config.update(parameters)
    
    def _update_metrics(self, signals: List[TradingSignal], processing_time_ms: float) -> None:
        """Update strategy performance metrics"""
        self._metrics.total_signals += len(signals)
        if signals:
            avg_confidence = sum(signal.confidence for signal in signals) / len(signals)
            # Weighted average for overall confidence
            total_weight = self._metrics.total_signals
            current_weight = len(signals)
            self._metrics.average_confidence = (
                (self._metrics.average_confidence * (total_weight - current_weight) + 
                 avg_confidence * current_weight) / total_weight
            )
        
        self._metrics.processing_time_ms = processing_time_ms
        self._metrics.last_updated = datetime.now()


class StrategyFactory:
    """Factory for creating strategy instances"""
    
    _strategy_registry: Dict[StrategyType, type] = {}
    
    @classmethod
    def register_strategy(cls, strategy_type: StrategyType, strategy_class: type) -> None:
        """Register a strategy implementation"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"Strategy class must inherit from BaseStrategy")
        cls._strategy_registry[strategy_type] = strategy_class
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, strategy_id: str, 
                       config: Dict[str, Any]) -> BaseStrategy:
        """Create strategy instance"""
        if strategy_type not in cls._strategy_registry:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        strategy_class = cls._strategy_registry[strategy_type]
        return strategy_class(strategy_id, config)
    
    @classmethod
    def get_available_strategies(cls) -> List[StrategyType]:
        """Get list of available strategy types"""
        return list(cls._strategy_registry.keys())


# Exception classes for strategy errors
class StrategyError(Exception):
    """Base exception for strategy errors"""
    pass


class StrategyConfigurationError(StrategyError):
    """Strategy configuration validation error"""
    pass


class StrategyExecutionError(StrategyError):
    """Strategy execution error"""
    pass


# Auto-register available strategies
def _auto_register_strategies():
    """Auto-register available strategy implementations from consolidated system"""
    import importlib
    
    # Updated paths to use the consolidated strategy system
    strategy_modules = [
        ('core_structure.strategies.momentum_strategy', 'MomentumStrategy', StrategyType.MOMENTUM),
        ('core_structure.strategies.mean_reversion_strategy', 'MeanReversionStrategy', StrategyType.MEAN_REVERSION),
        ('core_structure.strategies.pairs_trading_strategy', 'PairsTradingStrategy', StrategyType.PAIRS_TRADING),
        # Note: Arbitrage and Custom strategies not yet implemented in consolidated system
        # ('core_structure.strategies.arbitrage_strategy', 'ArbitrageStrategy', StrategyType.ARBITRAGE),
        # ('core_structure.strategies.custom_strategy', 'CustomStrategy', StrategyType.CUSTOM),
    ]
    
    for module_name, class_name, strategy_type in strategy_modules:
        try:
            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)
            StrategyFactory.register_strategy(strategy_type, strategy_class)
        except (ImportError, AttributeError) as e:
            # Strategy not available - skip silently
            pass


# Register strategies on module import
_auto_register_strategies()
