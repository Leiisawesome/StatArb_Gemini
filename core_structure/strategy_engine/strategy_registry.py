"""
Strategy Registry for AI-Ready Multi-Strategy Framework
======================================================

Professional strategy management system with:
- Dynamic strategy registration and discovery
- Performance-based strategy ranking and selection
- AI agent integration points for adaptive strategy allocation
- Real-time strategy monitoring and health checks
- Comprehensive strategy metadata and performance tracking

Key Features:
- Multi-strategy support (StatArb, Momentum, Mean Reversion, Volatility)
- Dynamic strategy allocation with performance feedback
- AI-ready interfaces for strategy selection and optimization
- Professional performance attribution and risk analysis
- Real-time strategy health monitoring and failover

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import json
from collections import defaultdict, deque
import uuid

# Core infrastructure imports
try:
    from ..infrastructure.config_manager import ConfigManager
    from ..infrastructure.message_bus import MessageBus
    from ..infrastructure.metrics_collector import MetricsCollector
except ImportError:
    ConfigManager = None
    MessageBus = None
    MetricsCollector = None

# Signal generation imports
try:
    from ..signal_generation.signal_generator import TradingSignal, SignalType
    from ..signal_generation.regime_detector import RegimeType
except ImportError:
    TradingSignal = None
    SignalType = None
    RegimeType = None

# External dependencies with graceful fallback
try:
    from sklearn.metrics import sharpe_ratio
    from sklearn.preprocessing import StandardScaler
    from scipy import stats
    from scipy.optimize import minimize
    SKLEARN_AVAILABLE = True
    SCIPY_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    SCIPY_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Types of trading strategies"""
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY = "volatility"
    PAIRS_TRADING = "pairs_trading"
    TREND_FOLLOWING = "trend_following"
    CONTRARIAN = "contrarian"
    MARKET_NEUTRAL = "market_neutral"
    CUSTOM = "custom"

class StrategyStatus(Enum):
    """Strategy operational status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"
    TRAINING = "training"
    TESTING = "testing"

class AllocationMethod(Enum):
    """Strategy allocation methods"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    PERFORMANCE_BASED = "performance_based"
    KELLY_CRITERION = "kelly_criterion"
    BLACK_LITTERMAN = "black_litterman"
    REGIME_BASED = "regime_based"
    AI_OPTIMIZED = "ai_optimized"

@dataclass
class StrategyMetadata:
    """Comprehensive strategy metadata"""
    strategy_id: str
    name: str
    strategy_type: StrategyType
    description: str
    version: str = "1.0"
    author: str = "Pro Quant Desk Trader"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Strategy characteristics
    min_lookback_periods: int = 60
    max_position_size: float = 0.25
    target_sharpe: float = 1.5
    max_drawdown: float = 0.15
    
    # AI readiness
    supports_ai_optimization: bool = True
    ai_feature_count: int = 0
    model_complexity: str = "medium"  # low, medium, high
    
    # Performance requirements
    min_data_points: int = 252
    update_frequency: str = "daily"  # intraday, daily, weekly
    regime_sensitive: bool = True
    
    # Risk profile
    risk_category: str = "moderate"  # conservative, moderate, aggressive
    correlation_tolerance: float = 0.8
    leverage_limit: float = 2.0

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_id: str
    timestamp: datetime
    
    # Return metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    excess_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    downside_volatility: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    
    # Performance ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Trading statistics
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 1.0
    avg_trade_duration: float = 0.0
    
    # AI performance metrics
    prediction_accuracy: float = 0.0
    feature_importance_stability: float = 0.0
    model_drift_score: float = 0.0
    
    # Operational metrics
    execution_latency_ms: float = 0.0
    signal_quality_score: float = 0.0
    regime_adaptation_score: float = 0.0

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Provides the unified interface that all strategies must implement
    for integration with the strategy engine and AI agents.
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        """
        Initialize base strategy
        
        Args:
            strategy_id: Unique strategy identifier
            config: Strategy configuration parameters
        """
        self.strategy_id = strategy_id
        self.config = config
        self.metadata = self._create_metadata()
        self.status = StrategyStatus.ACTIVE
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=10000)
        self.signal_history: deque = deque(maxlen=5000)
        self.execution_history: deque = deque(maxlen=5000)
        
        # Strategy state
        self.current_positions: Dict[str, float] = {}
        self.capital_allocated: float = 0.0
        self.last_update: Optional[datetime] = None
        
        # AI integration
        self.ai_features: Dict[str, float] = {}
        self.model_version: str = "1.0"
        self.feature_importance: Dict[str, float] = {}
        
        # Performance monitoring
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        self.message_bus = MessageBus() if MessageBus else None
        
        logger.info(f"Strategy {self.strategy_id} initialized")
    
    @abstractmethod
    def _create_metadata(self) -> StrategyMetadata:
        """Create strategy metadata - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def generate_signals(
        self,
        market_data: pd.DataFrame,
        portfolio_state: Dict[str, Any],
        regime_context: Optional[str] = None
    ) -> List['TradingSignal']:
        """
        Generate trading signals based on market data and portfolio state
        
        Args:
            market_data: Historical and real-time market data
            portfolio_state: Current portfolio positions and metrics
            regime_context: Current market regime information
            
        Returns:
            List of trading signals with confidence scores
        """
        pass
    
    @abstractmethod
    async def calculate_position_size(
        self,
        signal: 'TradingSignal',
        portfolio_value: float,
        risk_metrics: Dict[str, float]
    ) -> float:
        """
        Calculate optimal position size for a signal
        
        Args:
            signal: Trading signal with metadata
            portfolio_value: Current portfolio value
            risk_metrics: Risk metrics and constraints
            
        Returns:
            Position size as fraction of portfolio
        """
        pass
    
    @abstractmethod
    async def update_model(
        self,
        market_data: pd.DataFrame,
        performance_feedback: StrategyPerformance
    ) -> bool:
        """
        Update strategy model based on new data and performance feedback
        
        Args:
            market_data: Latest market data
            performance_feedback: Recent performance metrics
            
        Returns:
            True if model updated successfully
        """
        pass
    
    async def get_ai_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """
        Extract AI-ready features for this strategy
        
        Args:
            market_data: Market data for feature extraction
            
        Returns:
            Dictionary of features for AI models
        """
        try:
            # Base implementation - can be overridden by subclasses
            features = {}
            
            if 'close' in market_data.columns:
                close = market_data['close']
                returns = close.pct_change().dropna()
                
                # Basic features
                features['volatility_20d'] = returns.tail(20).std() * np.sqrt(252)
                features['return_20d'] = (close.iloc[-1] / close.iloc[-21] - 1) if len(close) > 20 else 0.0
                features['sharpe_20d'] = returns.tail(20).mean() / returns.tail(20).std() * np.sqrt(252) if len(returns) > 20 and returns.tail(20).std() > 0 else 0.0
                
                # Strategy-specific features
                strategy_features = await self._extract_strategy_features(market_data)
                features.update(strategy_features)
            
            self.ai_features = features
            return features
            
        except Exception as e:
            logger.error(f"AI feature extraction failed for {self.strategy_id}: {e}")
            return {}
    
    async def _extract_strategy_features(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Extract strategy-specific features - override in subclasses"""
        return {}
    
    def update_performance(self, performance: StrategyPerformance) -> None:
        """Update strategy performance metrics"""
        try:
            performance.strategy_id = self.strategy_id
            performance.timestamp = datetime.now()
            self.performance_history.append(performance)
            
            # Publish performance update
            if self.message_bus:
                asyncio.create_task(self.message_bus.publish(
                    'strategy_performance_updated',
                    {
                        'strategy_id': self.strategy_id,
                        'sharpe_ratio': performance.sharpe_ratio,
                        'total_return': performance.total_return,
                        'max_drawdown': performance.max_drawdown
                    },
                    source='strategy_registry'
                ))
            
        except Exception as e:
            logger.error(f"Performance update failed for {self.strategy_id}: {e}")
    
    def get_current_performance(self) -> Optional[StrategyPerformance]:
        """Get most recent performance metrics"""
        return self.performance_history[-1] if self.performance_history else None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get strategy health and operational status"""
        try:
            latest_performance = self.get_current_performance()
            
            return {
                'strategy_id': self.strategy_id,
                'status': self.status.value,
                'last_update': self.last_update.isoformat() if self.last_update else None,
                'signals_generated': len(self.signal_history),
                'trades_executed': len(self.execution_history),
                'current_positions': len(self.current_positions),
                'capital_allocated': self.capital_allocated,
                'latest_sharpe': latest_performance.sharpe_ratio if latest_performance else 0.0,
                'latest_return': latest_performance.total_return if latest_performance else 0.0,
                'ai_features_count': len(self.ai_features),
                'model_version': self.model_version
            }
        except Exception as e:
            logger.error(f"Health status check failed for {self.strategy_id}: {e}")
            return {'strategy_id': self.strategy_id, 'status': 'error', 'error': str(e)}

class StrategyRegistry:
    """
    Comprehensive strategy registry for managing multiple trading strategies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy registry
        
        Args:
            config: Registry configuration
        """
        self.config = config or {}
        
        # Strategy storage
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_types: Dict[StrategyType, List[str]] = defaultdict(list)
        self.strategy_allocations: Dict[str, float] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[StrategyPerformance]] = defaultdict(list)
        self.allocation_history: List[Dict[str, float]] = []
        
        # AI integration
        self.ai_optimizers: List[Callable] = []
        self.allocation_method = AllocationMethod.EQUAL_WEIGHT
        
        # Infrastructure
        self.config_manager = ConfigManager() if ConfigManager else None
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        self.message_bus = MessageBus() if MessageBus else None
        
        # Thread pool for parallel strategy execution
        self.executor = ThreadPoolExecutor(max_workers=8)
        
        # Performance monitoring
        self.registry_start_time = datetime.now()
        self.total_signals_generated = 0
        self.total_trades_executed = 0
        
        logger.info("StrategyRegistry initialized")
    
    def register_strategy(self, strategy: BaseStrategy) -> bool:
        """
        Register a new strategy in the registry
        
        Args:
            strategy: Strategy instance to register
            
        Returns:
            True if registration successful
        """
        try:
            strategy_id = strategy.strategy_id
            
            if strategy_id in self.strategies:
                logger.warning(f"Strategy {strategy_id} already registered, updating")
            
            # Store strategy
            self.strategies[strategy_id] = strategy
            self.strategy_types[strategy.metadata.strategy_type].append(strategy_id)
            
            # Initialize allocation
            if strategy_id not in self.strategy_allocations:
                self.strategy_allocations[strategy_id] = 0.0
            
            # Rebalance allocations
            self._rebalance_allocations()
            
            logger.info(f"Strategy {strategy_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Strategy registration failed: {e}")
            return False
    
    def unregister_strategy(self, strategy_id: str) -> bool:
        """
        Unregister a strategy from the registry
        
        Args:
            strategy_id: Strategy identifier to remove
            
        Returns:
            True if unregistration successful
        """
        try:
            if strategy_id not in self.strategies:
                logger.warning(f"Strategy {strategy_id} not found for unregistration")
                return False
            
            # Get strategy info before removal
            strategy = self.strategies[strategy_id]
            strategy_type = strategy.metadata.strategy_type
            
            # Remove strategy
            del self.strategies[strategy_id]
            
            # Remove from type mapping
            if strategy_id in self.strategy_types[strategy_type]:
                self.strategy_types[strategy_type].remove(strategy_id)
            
            # Remove allocation
            self.strategy_allocations.pop(strategy_id, None)
            
            # Rebalance remaining allocations
            self._rebalance_allocations()
            
            logger.info(f"Strategy {strategy_id} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Strategy unregistration failed: {e}")
            return False
    
    async def generate_all_signals(
        self,
        market_data: pd.DataFrame,
        portfolio_state: Dict[str, Any],
        regime_context: Optional[str] = None
    ) -> Dict[str, List['TradingSignal']]:
        """
        Generate signals from all active strategies in parallel
        
        Args:
            market_data: Market data for signal generation
            portfolio_state: Current portfolio state
            regime_context: Market regime information
            
        Returns:
            Dictionary mapping strategy IDs to their signals
        """
        try:
            # Create signal generation tasks
            signal_tasks = []
            active_strategies = [
                strategy for strategy in self.strategies.values()
                if strategy.status == StrategyStatus.ACTIVE
            ]
            
            for strategy in active_strategies:
                task = asyncio.create_task(
                    strategy.generate_signals(market_data, portfolio_state, regime_context)
                )
                signal_tasks.append((strategy.strategy_id, task))
            
            # Execute all tasks in parallel
            all_signals = {}
            for strategy_id, task in signal_tasks:
                try:
                    signals = await asyncio.wait_for(task, timeout=1.0)  # 1 second timeout
                    all_signals[strategy_id] = signals
                    self.total_signals_generated += len(signals)
                except asyncio.TimeoutError:
                    logger.warning(f"Signal generation timeout for strategy {strategy_id}")
                    all_signals[strategy_id] = []
                except Exception as e:
                    logger.error(f"Signal generation failed for strategy {strategy_id}: {e}")
                    all_signals[strategy_id] = []
            
            return all_signals
            
        except Exception as e:
            logger.error(f"Batch signal generation failed: {e}")
            return {}
    
    def get_strategy_allocations(self) -> Dict[str, float]:
        """Get current strategy allocations"""
        return self.strategy_allocations.copy()
    
    def set_allocation_method(self, method: AllocationMethod) -> None:
        """Set strategy allocation method"""
        self.allocation_method = method
        self._rebalance_allocations()
        logger.info(f"Allocation method set to {method.value}")
    
    def _rebalance_allocations(self) -> None:
        """Rebalance strategy allocations based on current method"""
        try:
            active_strategies = [
                strategy_id for strategy_id, strategy in self.strategies.items()
                if strategy.status == StrategyStatus.ACTIVE
            ]
            
            if not active_strategies:
                return
            
            if self.allocation_method == AllocationMethod.EQUAL_WEIGHT:
                # Equal weight allocation
                allocation = 1.0 / len(active_strategies)
                for strategy_id in active_strategies:
                    self.strategy_allocations[strategy_id] = allocation
            
            elif self.allocation_method == AllocationMethod.PERFORMANCE_BASED:
                # Performance-based allocation
                self._allocate_by_performance()
            
            elif self.allocation_method == AllocationMethod.RISK_PARITY:
                # Risk parity allocation
                self._allocate_by_risk_parity()
            
            else:
                # Default to equal weight
                allocation = 1.0 / len(active_strategies)
                for strategy_id in active_strategies:
                    self.strategy_allocations[strategy_id] = allocation
            
            # Record allocation history
            self.allocation_history.append({
                'timestamp': datetime.now(),
                'method': self.allocation_method.value,
                'allocations': self.strategy_allocations.copy()
            })
            
        except Exception as e:
            logger.error(f"Allocation rebalancing failed: {e}")
    
    def _allocate_by_performance(self) -> None:
        """Allocate based on historical performance"""
        try:
            performance_scores = {}
            
            for strategy_id, strategy in self.strategies.items():
                if strategy.status != StrategyStatus.ACTIVE:
                    continue
                
                latest_performance = strategy.get_current_performance()
                if latest_performance:
                    # Score based on risk-adjusted return
                    score = latest_performance.sharpe_ratio * (1 - latest_performance.max_drawdown)
                    performance_scores[strategy_id] = max(0.01, score)  # Minimum 1% allocation
                else:
                    performance_scores[strategy_id] = 0.01
            
            # Normalize to sum to 1
            total_score = sum(performance_scores.values())
            if total_score > 0:
                for strategy_id in performance_scores:
                    self.strategy_allocations[strategy_id] = performance_scores[strategy_id] / total_score
            
        except Exception as e:
            logger.error(f"Performance-based allocation failed: {e}")
            self._allocate_equal_weight()
    
    def _allocate_by_risk_parity(self) -> None:
        """Allocate based on risk parity"""
        try:
            risk_scores = {}
            
            for strategy_id, strategy in self.strategies.items():
                if strategy.status != StrategyStatus.ACTIVE:
                    continue
                
                latest_performance = strategy.get_current_performance()
                if latest_performance and latest_performance.volatility > 0:
                    # Inverse volatility weighting
                    risk_scores[strategy_id] = 1.0 / latest_performance.volatility
                else:
                    risk_scores[strategy_id] = 1.0
            
            # Normalize to sum to 1
            total_score = sum(risk_scores.values())
            if total_score > 0:
                for strategy_id in risk_scores:
                    self.strategy_allocations[strategy_id] = risk_scores[strategy_id] / total_score
            
        except Exception as e:
            logger.error(f"Risk parity allocation failed: {e}")
            self._allocate_equal_weight()
    
    def _allocate_equal_weight(self) -> None:
        """Fallback equal weight allocation"""
        active_strategies = [
            strategy_id for strategy_id, strategy in self.strategies.items()
            if strategy.status == StrategyStatus.ACTIVE
        ]
        
        if active_strategies:
            allocation = 1.0 / len(active_strategies)
            for strategy_id in active_strategies:
                self.strategy_allocations[strategy_id] = allocation
    
    def get_strategies_by_type(self, strategy_type: StrategyType) -> List[BaseStrategy]:
        """Get all strategies of a specific type"""
        strategy_ids = self.strategy_types.get(strategy_type, [])
        return [self.strategies[sid] for sid in strategy_ids if sid in self.strategies]
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary for all strategies"""
        try:
            summary = {
                'total_strategies': len(self.strategies),
                'active_strategies': len([s for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE]),
                'total_signals_generated': self.total_signals_generated,
                'total_trades_executed': self.total_trades_executed,
                'allocation_method': self.allocation_method.value,
                'strategies': {}
            }
            
            for strategy_id, strategy in self.strategies.items():
                perf = strategy.get_current_performance()
                health = strategy.get_health_status()
                
                summary['strategies'][strategy_id] = {
                    'type': strategy.metadata.strategy_type.value,
                    'status': strategy.status.value,
                    'allocation': self.strategy_allocations.get(strategy_id, 0.0),
                    'sharpe_ratio': perf.sharpe_ratio if perf else 0.0,
                    'total_return': perf.total_return if perf else 0.0,
                    'max_drawdown': perf.max_drawdown if perf else 0.0,
                    'signals_generated': health.get('signals_generated', 0),
                    'trades_executed': health.get('trades_executed', 0)
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Performance summary generation failed: {e}")
            return {}
    
    def register_ai_optimizer(self, optimizer_func: Callable) -> bool:
        """Register AI optimization function"""
        try:
            self.ai_optimizers.append(optimizer_func)
            logger.info("AI optimizer registered")
            return True
        except Exception as e:
            logger.error(f"AI optimizer registration failed: {e}")
            return False
    
    async def optimize_allocations_with_ai(self, market_data: pd.DataFrame) -> bool:
        """Use AI optimizers to improve strategy allocations"""
        try:
            if not self.ai_optimizers:
                logger.warning("No AI optimizers registered")
                return False
            
            # Prepare data for AI optimizers
            strategy_features = {}
            for strategy_id, strategy in self.strategies.items():
                features = await strategy.get_ai_features(market_data)
                performance = strategy.get_current_performance()
                
                strategy_features[strategy_id] = {
                    'features': features,
                    'performance': performance,
                    'current_allocation': self.strategy_allocations.get(strategy_id, 0.0)
                }
            
            # Run AI optimizers
            for optimizer in self.ai_optimizers:
                try:
                    new_allocations = await optimizer(strategy_features, market_data)
                    if new_allocations and isinstance(new_allocations, dict):
                        # Validate and apply new allocations
                        if abs(sum(new_allocations.values()) - 1.0) < 0.01:  # Allow small rounding errors
                            self.strategy_allocations.update(new_allocations)
                            self.allocation_method = AllocationMethod.AI_OPTIMIZED
                            logger.info("AI-optimized allocations applied")
                            return True
                except Exception as e:
                    logger.error(f"AI optimizer failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"AI allocation optimization failed: {e}")
            return False
    
    def get_registry_health(self) -> Dict[str, Any]:
        """Get overall registry health and status"""
        try:
            uptime = (datetime.now() - self.registry_start_time).total_seconds()
            
            return {
                'registry_status': 'healthy',
                'uptime_seconds': uptime,
                'total_strategies': len(self.strategies),
                'active_strategies': len([s for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE]),
                'strategy_types': {st.value: len(sids) for st, sids in self.strategy_types.items()},
                'allocation_method': self.allocation_method.value,
                'total_signals_generated': self.total_signals_generated,
                'total_trades_executed': self.total_trades_executed,
                'ai_optimizers_registered': len(self.ai_optimizers),
                'performance_history_size': sum(len(ph) for ph in self.performance_history.values()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Registry health check failed: {e}")
            return {'registry_status': 'error', 'error': str(e)}
    
    def shutdown(self) -> None:
        """Graceful shutdown of strategy registry"""
        try:
            logger.info("Shutting down StrategyRegistry...")
            
            # Shutdown thread pool
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            
            # Clear data structures
            self.strategies.clear()
            self.strategy_types.clear()
            self.performance_history.clear()
            
            logger.info("StrategyRegistry shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during registry shutdown: {e}") 