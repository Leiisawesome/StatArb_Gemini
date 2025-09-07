#!/usr/bin/env python3
"""
Unified Strategy System - Core Strategy Engine and Framework
===========================================================

Consolidates strategy functionality from multiple systems:
- Enhanced strategy interfaces and base classes
- Template-based strategy development (from trade_engine/templates)
- Strategy execution engine and result management
- Unified configuration and parameter management

This module provides the core framework for all strategy implementations,
combining the best features from the previous separate systems.

Author: Professional Trading System Architecture
Version: 2.0.0 (Unified)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import threading
import json
from pathlib import Path

# Import base interfaces
from ..interfaces.strategy_interfaces import (
    StrategyInterface, BaseStrategy, StrategyContext, StrategyMetrics,
    StrategyType, StrategyError, StrategyConfig
)

# Import signal types
from ..components.signal_generation import TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

# ================================================================================
# ENHANCED ENUMS AND DATA CLASSES
# ================================================================================

class StrategyExecutionMode(Enum):
    """Strategy execution modes"""
    BACKTEST = "backtest"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"

class StrategyStatus(Enum):
    """Strategy status states"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class SignalCondition(Enum):
    """Enhanced signal condition types (from templates)"""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUAL_TO = "equal_to"
    BETWEEN = "between"
    OUTSIDE_RANGE = "outside_range"
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    CROSSOVER_ABOVE = "crossover_above"
    CROSSOVER_BELOW = "crossover_below"

@dataclass
class StrategyParameters:
    """Enhanced strategy parameters with validation"""
    # Core parameters
    lookback_period: int = 20
    signal_threshold: float = 0.02
    position_size: float = 0.1
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Risk management
    max_position_size: float = 0.2
    max_drawdown: float = 0.1
    risk_per_trade: float = 0.02
    
    # Template-based parameters (from templates system)
    template_config: Dict[str, Any] = field(default_factory=dict)
    custom_indicators: List[str] = field(default_factory=list)
    signal_conditions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Execution parameters
    execution_mode: StrategyExecutionMode = StrategyExecutionMode.BACKTEST
    rebalance_frequency: str = "daily"
    
    def validate(self) -> bool:
        """Validate strategy parameters"""
        if self.lookback_period <= 0:
            raise ValueError("lookback_period must be positive")
        if not 0 < self.position_size <= 1:
            raise ValueError("position_size must be between 0 and 1")
        if not 0 < self.max_position_size <= 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if self.position_size > self.max_position_size:
            raise ValueError("position_size cannot exceed max_position_size")
        return True

@dataclass
class UnifiedStrategyConfig:
    """Unified strategy configuration (consolidates template config)"""
    strategy_id: str
    strategy_type: StrategyType
    parameters: StrategyParameters
    
    # Enhanced configuration
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    
    # Template integration
    template_based: bool = False
    template_name: Optional[str] = None
    template_version: Optional[str] = None
    
    # Execution settings
    enabled: bool = True
    priority: int = 1
    allocation: float = 1.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': self.strategy_type.value if isinstance(self.strategy_type, StrategyType) else self.strategy_type,
            'parameters': self.parameters.__dict__,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'template_based': self.template_based,
            'template_name': self.template_name,
            'template_version': self.template_version,
            'enabled': self.enabled,
            'priority': self.priority,
            'allocation': self.allocation,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

@dataclass
class StrategyResult:
    """Enhanced strategy execution result"""
    strategy_id: str
    timestamp: datetime
    signals: List[TradingSignal]
    
    # Performance metrics
    execution_time_ms: float = 0.0
    confidence_score: float = 0.0
    risk_score: float = 0.0
    
    # Status information
    status: StrategyStatus = StrategyStatus.ACTIVE
    error_message: Optional[str] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def signal_count(self) -> int:
        return len(self.signals)
    
    @property
    def has_signals(self) -> bool:
        return len(self.signals) > 0

# ================================================================================
# ENHANCED BASE STRATEGY CLASSES
# ================================================================================

class EnhancedBaseStrategy(BaseStrategy):
    """
    Enhanced base strategy with unified functionality.
    
    Combines the best features from BaseStrategy and template system:
    - Enhanced parameter management
    - Template-based configuration support
    - Improved signal generation
    - Better error handling and metrics
    """
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig):
        # Initialize base strategy
        super().__init__(strategy_id, config.parameters.__dict__)
        
        # Enhanced initialization
        self.unified_config = config
        self.parameters = config.parameters
        self.status = StrategyStatus.INACTIVE
        self.execution_mode = config.parameters.execution_mode
        
        # Enhanced metrics
        self._enhanced_metrics = {
            'total_signals_generated': 0,
            'successful_signals': 0,
            'failed_signals': 0,
            'average_confidence': 0.0,
            'average_execution_time': 0.0,
            'last_execution': None,
            'error_count': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Template support
        self._template_cache = {}
        
        logger.info(f"Enhanced strategy initialized: {strategy_id} ({config.strategy_type.value})")
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Enhanced parameter validation"""
        try:
            # Use unified parameter validation
            if hasattr(self.parameters, 'validate'):
                return self.parameters.validate()
            return super().validate_parameters(config)
        except Exception as e:
            logger.error(f"Parameter validation failed for {self.strategy_id}: {e}")
            return False
    
    async def generate_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Enhanced signal generation with better error handling and metrics"""
        start_time = datetime.now()
        
        try:
            with self._lock:
                # Update status
                self.status = StrategyStatus.ACTIVE
                
                # Generate signals using strategy-specific logic
                signals = await self._generate_strategy_signals(context)
                
                # Enhanced signal processing
                processed_signals = self._process_signals(signals, context)
                
                # Update metrics
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_enhanced_metrics(processed_signals, execution_time)
                
                logger.debug(f"Strategy {self.strategy_id} generated {len(processed_signals)} signals in {execution_time:.2f}ms")
                
                return processed_signals
                
        except Exception as e:
            self.status = StrategyStatus.ERROR
            self._enhanced_metrics['error_count'] += 1
            logger.error(f"Signal generation failed for {self.strategy_id}: {e}")
            return []
    
    def _process_signals(self, signals: List[TradingSignal], context: StrategyContext) -> List[TradingSignal]:
        """Process and enhance generated signals"""
        processed_signals = []
        
        for signal in signals:
            # Apply position sizing
            if hasattr(signal, 'quantity') and signal.quantity:
                # Adjust quantity based on position size limits
                max_quantity = context.available_capital * self.parameters.position_size
                signal.quantity = min(signal.quantity, max_quantity)
            
            # Apply risk management
            if self.parameters.stop_loss and hasattr(signal, 'stop_loss'):
                signal.stop_loss = self.parameters.stop_loss
            
            if self.parameters.take_profit and hasattr(signal, 'take_profit'):
                signal.take_profit = self.parameters.take_profit
            
            processed_signals.append(signal)
        
        return processed_signals
    
    def _update_enhanced_metrics(self, signals: List[TradingSignal], execution_time_ms: float):
        """Update enhanced strategy metrics"""
        self._enhanced_metrics['total_signals_generated'] += len(signals)
        self._enhanced_metrics['last_execution'] = datetime.now()
        
        # Update execution time (rolling average)
        current_avg = self._enhanced_metrics['average_execution_time']
        total_executions = self._enhanced_metrics['total_signals_generated']
        
        if total_executions > 0:
            self._enhanced_metrics['average_execution_time'] = (
                (current_avg * (total_executions - len(signals)) + execution_time_ms) / total_executions
            )
        
        # Update confidence (if signals have confidence scores)
        if signals:
            confidences = [getattr(s, 'confidence', 0.5) for s in signals]
            avg_confidence = sum(confidences) / len(confidences)
            
            current_conf_avg = self._enhanced_metrics['average_confidence']
            self._enhanced_metrics['average_confidence'] = (
                (current_conf_avg * (total_executions - len(signals)) + avg_confidence) / total_executions
            )
    
    def get_enhanced_metrics(self) -> Dict[str, Any]:
        """Get enhanced strategy metrics"""
        base_metrics = self.get_strategy_metrics()
        
        return {
            **base_metrics.__dict__,
            **self._enhanced_metrics,
            'status': self.status.value,
            'execution_mode': self.execution_mode.value,
            'parameters': self.parameters.__dict__
        }
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Enhanced parameter update with validation"""
        try:
            # Update parameters
            for key, value in parameters.items():
                if hasattr(self.parameters, key):
                    setattr(self.parameters, key, value)
            
            # Validate updated parameters
            if not self.parameters.validate():
                raise ValueError("Parameter validation failed after update")
            
            # Update timestamp
            self.unified_config.updated_at = datetime.now()
            
            logger.info(f"Parameters updated for strategy {self.strategy_id}")
            
        except Exception as e:
            logger.error(f"Parameter update failed for {self.strategy_id}: {e}")
            raise StrategyError(f"Parameter update failed: {e}")

class TemplateBasedStrategy(EnhancedBaseStrategy):
    """
    Template-based strategy implementation.
    
    Integrates the template system functionality into the unified strategy framework.
    Allows strategies to be defined using template configurations.
    """
    
    def __init__(self, strategy_id: str, config: UnifiedStrategyConfig, template_config: Dict[str, Any]):
        super().__init__(strategy_id, config)
        
        self.template_config = template_config
        self.template_name = config.template_name
        
        # Parse template configuration
        self._parse_template_config()
        
        logger.info(f"Template-based strategy initialized: {strategy_id} using template {self.template_name}")
    
    def _parse_template_config(self):
        """Parse template configuration into strategy parameters"""
        try:
            # Extract signal conditions from template
            if 'signal_conditions' in self.template_config:
                self.parameters.signal_conditions = self.template_config['signal_conditions']
            
            # Extract custom indicators
            if 'indicators' in self.template_config:
                self.parameters.custom_indicators = self.template_config['indicators']
            
            # Extract other template parameters
            template_params = self.template_config.get('parameters', {})
            for key, value in template_params.items():
                if hasattr(self.parameters, key):
                    setattr(self.parameters, key, value)
            
        except Exception as e:
            logger.error(f"Template config parsing failed: {e}")
            raise StrategyError(f"Template configuration parsing failed: {e}")
    
    async def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate signals based on template configuration"""
        signals = []
        
        try:
            # Process each signal condition from template
            for condition in self.parameters.signal_conditions:
                template_signals = await self._evaluate_signal_condition(condition, context)
                signals.extend(template_signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Template signal generation failed: {e}")
            return []
    
    async def _evaluate_signal_condition(self, condition: Dict[str, Any], context: StrategyContext) -> List[TradingSignal]:
        """Evaluate a single signal condition from template"""
        # This is a simplified implementation
        # In a full implementation, this would parse and evaluate complex template conditions
        
        signals = []
        
        try:
            condition_type = condition.get('type', 'greater_than')
            indicator = condition.get('indicator', 'price')
            threshold = condition.get('threshold', 0.0)
            
            # Simple condition evaluation (placeholder)
            if condition_type == 'greater_than':
                # Generate buy signal if condition met
                signal = TradingSignal(
                    symbol=context.symbol,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=0.7,
                    timestamp=datetime.now(),
                    metadata={'template_condition': condition}
                )
                signals.append(signal)
            
        except Exception as e:
            logger.error(f"Signal condition evaluation failed: {e}")
        
        return signals

# ================================================================================
# STRATEGY EXECUTION ENGINE
# ================================================================================

class StrategyExecutionEngine:
    """
    Unified strategy execution engine.
    
    Manages strategy execution, result collection, and performance monitoring
    across all strategy types and execution modes.
    """
    
    def __init__(self):
        self.active_strategies: Dict[str, EnhancedBaseStrategy] = {}
        self.execution_results: List[StrategyResult] = []
        self.execution_lock = threading.RLock()
        
        logger.info("Strategy execution engine initialized")
    
    def register_strategy(self, strategy: EnhancedBaseStrategy) -> None:
        """Register a strategy for execution"""
        with self.execution_lock:
            self.active_strategies[strategy.strategy_id] = strategy
            logger.info(f"Strategy registered: {strategy.strategy_id}")
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """Unregister a strategy"""
        with self.execution_lock:
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]
                logger.info(f"Strategy unregistered: {strategy_id}")
    
    async def execute_strategy(self, strategy_id: str, context: StrategyContext) -> StrategyResult:
        """Execute a single strategy"""
        start_time = datetime.now()
        
        try:
            if strategy_id not in self.active_strategies:
                raise StrategyError(f"Strategy not found: {strategy_id}")
            
            strategy = self.active_strategies[strategy_id]
            
            # Execute strategy
            signals = await strategy.generate_signals(context)
            
            # Create result
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = StrategyResult(
                strategy_id=strategy_id,
                timestamp=datetime.now(),
                signals=signals,
                execution_time_ms=execution_time,
                status=strategy.status
            )
            
            # Store result
            self.execution_results.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Strategy execution failed for {strategy_id}: {e}")
            
            return StrategyResult(
                strategy_id=strategy_id,
                timestamp=datetime.now(),
                signals=[],
                status=StrategyStatus.ERROR,
                error_message=str(e)
            )
    
    async def execute_all_strategies(self, context: StrategyContext) -> List[StrategyResult]:
        """Execute all registered strategies"""
        results = []
        
        # Execute strategies concurrently
        tasks = [
            self.execute_strategy(strategy_id, context)
            for strategy_id in self.active_strategies.keys()
        ]
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            valid_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Strategy execution exception: {result}")
                else:
                    valid_results.append(result)
            
            results = valid_results
        
        return results
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics"""
        with self.execution_lock:
            total_executions = len(self.execution_results)
            successful_executions = len([r for r in self.execution_results if r.status == StrategyStatus.ACTIVE])
            
            return {
                'total_strategies': len(self.active_strategies),
                'total_executions': total_executions,
                'successful_executions': successful_executions,
                'success_rate': successful_executions / total_executions if total_executions > 0 else 0,
                'active_strategies': list(self.active_strategies.keys()),
                'last_execution': self.execution_results[-1].timestamp if self.execution_results else None
            }

# ================================================================================
# UNIFIED STRATEGY ENGINE
# ================================================================================

class UnifiedStrategyEngine:
    """
    Main unified strategy engine.
    
    Consolidates all strategy functionality into a single, comprehensive system:
    - Strategy registration and management
    - Execution coordination
    - Configuration management
    - Performance monitoring
    """
    
    def __init__(self):
        self.execution_engine = StrategyExecutionEngine()
        self.configurations: Dict[str, UnifiedStrategyConfig] = {}
        self.engine_lock = threading.RLock()
        
        logger.info("Unified strategy engine initialized")
    
    def create_strategy(self, config: UnifiedStrategyConfig, strategy_class: Type[EnhancedBaseStrategy] = None) -> EnhancedBaseStrategy:
        """Create a strategy instance"""
        try:
            # Use provided class or default to enhanced base strategy
            if strategy_class is None:
                if config.template_based and config.template_name:
                    strategy_class = TemplateBasedStrategy
                else:
                    strategy_class = EnhancedBaseStrategy
            
            # Create strategy instance
            if config.template_based:
                strategy = strategy_class(config.strategy_id, config, config.parameters.template_config)
            else:
                strategy = strategy_class(config.strategy_id, config)
            
            # Register with execution engine
            self.execution_engine.register_strategy(strategy)
            
            # Store configuration
            self.configurations[config.strategy_id] = config
            
            logger.info(f"Strategy created: {config.strategy_id}")
            return strategy
            
        except Exception as e:
            logger.error(f"Strategy creation failed: {e}")
            raise StrategyError(f"Strategy creation failed: {e}")
    
    async def execute_strategies(self, context: StrategyContext) -> List[StrategyResult]:
        """Execute all strategies"""
        return await self.execution_engine.execute_all_strategies(context)
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy system status"""
        execution_summary = self.execution_engine.get_execution_summary()
        
        return {
            'engine_status': 'active',
            'total_configurations': len(self.configurations),
            'execution_summary': execution_summary,
            'consolidation_info': {
                'unified_system': True,
                'template_support': True,
                'enhanced_metrics': True,
                'concurrent_execution': True
            }
        }

# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

# Global unified strategy engine instance
unified_strategy_engine = UnifiedStrategyEngine()

def create_strategy(config: UnifiedStrategyConfig, strategy_class: Type[EnhancedBaseStrategy] = None) -> EnhancedBaseStrategy:
    """Convenience function for creating strategies"""
    return unified_strategy_engine.create_strategy(config, strategy_class)

async def execute_strategies(context: StrategyContext) -> List[StrategyResult]:
    """Convenience function for executing strategies"""
    return await unified_strategy_engine.execute_strategies(context)

def get_strategy_engine_status() -> Dict[str, Any]:
    """Convenience function for getting engine status"""
    return unified_strategy_engine.get_strategy_status()

logger.info("Unified Strategy System loaded successfully - Multiple systems consolidated into 1")
