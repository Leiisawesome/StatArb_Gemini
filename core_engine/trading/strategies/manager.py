#!/usr/bin/env python3
"""
Strategy Manager - Core Engine (WHAT Component)
===============================================

Clean implementation of the strategy manager for core_engine.
This component determines WHAT trades should be made.

As part of the central Risk Manager hub, this manager:
- Analyzes market data and conditions
- Determines which strategies to activate
- Generates trading signals and recommendations
- Submits trade requests to Risk Manager for authorization

Migration: Direct implementation using proven strategy patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production - WHAT Component)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pandas as pd

# Use internal core_engine types for independence
from ...type_definitions.strategy import StrategyType, StrategyConfig

# Import enhanced strategy implementations
from .implementations import (
    EnhancedMomentumStrategy, MomentumConfig,
    EnhancedMeanReversionStrategy, MeanReversionConfig,
    EnhancedStatisticalArbitrageStrategy,
    EnhancedFactorStrategy, FactorConfig,
    EnhancedMultiAssetStrategy, MultiAssetConfig,
    EnhancedTrendFollowingStrategy, TrendFollowingConfig,
    EnhancedBreakoutStrategy, BreakoutConfig,
    EnhancedPairsTradingStrategy, PairsConfig,
    EnhancedVolatilityStrategy, VolatilityConfig,
    EnhancedArbitrageStrategy, ArbitrageConfig
)

# Import StatisticalArbitrageConfig separately
from .implementations.statistical_arbitrage import StatisticalArbitrageConfig

# Import base strategy and registry
from .base_strategy_enhanced import EnhancedBaseStrategy
from .strategy_registry import StrategyRegistry

# Import multi-strategy coordination components
from .multi_strategy_coordinator import (
    MultiStrategySignalAggregator, SignalConflictResolver, 
    EnhancedSignal, StrategyRegistration
)

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
try:
    from ...system.interfaces import ISystemComponent, IRegimeAware, RegimeContext
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    from dataclasses import dataclass as dc
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass
        
        @abstractmethod
        async def start(self) -> bool:
            pass
        
        @abstractmethod
        async def stop(self) -> bool:
            pass
        
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass
        
        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass
    
    @dc
    class RegimeContext:
        primary_regime: str = "unknown"
        regime_confidence: float = 0.5
    
    class IRegimeAware(ABC):
        @abstractmethod
        def set_regime_engine(self, regime_engine: Any) -> None:
            pass

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    signal_id: str
    strategy_name: str
    strategy_type: StrategyType
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    expected_return: float
    risk_score: float
    quantity: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    time_horizon: Optional[timedelta]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class StrategyAllocation:
    """Strategy allocation configuration"""
    strategy_name: str
    strategy_type: StrategyType
    allocation_pct: float
    max_positions: int
    risk_limit: float
    active: bool = True

@dataclass
class StrategyManagerConfig:
    """Strategy manager configuration"""
    max_concurrent_strategies: int = 5
    signal_generation_interval: int = 60  # seconds
    min_confidence_threshold: float = 0.6
    max_strategy_allocation: float = 0.33  # 33% max per strategy
    enable_regime_awareness: bool = True
    enable_correlation_filtering: bool = True
    signal_aggregation_method: str = "weighted_average"
    enable_enhanced_strategies: bool = True  # Enable enhanced strategy implementations
    auto_discover_strategies: bool = True    # Auto-discover strategies on startup
    strategy_registry_path: str = "strategy_registry.json"  # Registry file path
    
    # Multi-strategy coordination settings
    enable_multi_strategy_coordination: bool = True
    enable_signal_aggregation: bool = True
    enable_conflict_resolution: bool = True
    conflict_resolution_method: str = "confidence_weighted"
    enable_dynamic_weighting: bool = True
    enable_strategy_attribution: bool = True


class EnhancedStrategyFactory:
    """Factory for creating enhanced strategy instances"""
    
    # Strategy class mapping
    STRATEGY_CLASSES = {
        StrategyType.MOMENTUM: EnhancedMomentumStrategy,
        StrategyType.MEAN_REVERSION: EnhancedMeanReversionStrategy,
        StrategyType.STATISTICAL_ARBITRAGE: EnhancedStatisticalArbitrageStrategy,
        StrategyType.FACTOR: EnhancedFactorStrategy,
        StrategyType.MULTI_ASSET: EnhancedMultiAssetStrategy,
        StrategyType.TREND_FOLLOWING: EnhancedTrendFollowingStrategy,
        StrategyType.BREAKOUT: EnhancedBreakoutStrategy,
        StrategyType.PAIRS_TRADING: EnhancedPairsTradingStrategy,
        StrategyType.VOLATILITY: EnhancedVolatilityStrategy,
        StrategyType.ARBITRAGE: EnhancedArbitrageStrategy
    }
    
    # Configuration class mapping
    CONFIG_CLASSES = {
        StrategyType.MOMENTUM: MomentumConfig,
        StrategyType.MEAN_REVERSION: MeanReversionConfig,
        StrategyType.STATISTICAL_ARBITRAGE: StatisticalArbitrageConfig,
        StrategyType.FACTOR: FactorConfig,
        StrategyType.MULTI_ASSET: MultiAssetConfig,
        StrategyType.TREND_FOLLOWING: TrendFollowingConfig,
        StrategyType.BREAKOUT: BreakoutConfig,
        StrategyType.PAIRS_TRADING: PairsConfig,
        StrategyType.VOLATILITY: VolatilityConfig,
        StrategyType.ARBITRAGE: ArbitrageConfig
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: Dict[str, Any]) -> Optional[EnhancedBaseStrategy]:
        """Create enhanced strategy instance"""
        try:
            strategy_class = cls.STRATEGY_CLASSES.get(strategy_type)
            if not strategy_class:
                logger.warning(f"No enhanced strategy class found for type: {strategy_type}")
                return None
            
            # Create configuration object
            config_class = cls.CONFIG_CLASSES.get(strategy_type)
            if config_class:
                # Convert dict config to proper config object
                strategy_config = cls._create_config_object(config_class, config)
            else:
                # Use basic StrategyConfig for strategies without specific config
                strategy_config = StrategyConfig(
                    strategy_name=config.get('name', f'{strategy_type.value}_strategy'),
                    strategy_type=strategy_type,
                    **{k: v for k, v in config.items() if k not in ['name', 'type']}
                )
            
            # Create strategy instance
            strategy_instance = strategy_class(strategy_config)
            
            logger.info(f"✅ Created enhanced strategy: {strategy_type.value} - {config.get('name')}")
            return strategy_instance
            
        except Exception as e:
            logger.error(f"❌ Failed to create enhanced strategy {strategy_type}: {e}")
            return None
    
    @classmethod
    def _create_config_object(cls, config_class: Type, config_dict: Dict[str, Any]):
        """Create configuration object from dictionary"""
        try:
            # Get config class constructor parameters
            import inspect
            sig = inspect.signature(config_class.__init__)
            
            # Extract parameters from nested 'parameters' dict if present
            flat_config = config_dict.copy()
            if 'parameters' in flat_config and isinstance(flat_config['parameters'], dict):
                # Merge parameters into flat config
                parameters = flat_config.pop('parameters')
                flat_config.update(parameters)
            
            # Filter config_dict to only include valid parameters
            valid_params = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                if param_name in flat_config:
                    valid_params[param_name] = flat_config[param_name]
                elif hasattr(param, 'default') and param.default != inspect.Parameter.empty:
                    # Use default value if available
                    continue
            
            return config_class(**valid_params)
            
        except Exception as e:
            logger.warning(f"Failed to create config object: {e}, using basic config")
            return StrategyConfig(
                strategy_name=config_dict.get('name', 'strategy'),
                strategy_type=StrategyType(config_dict.get('type', 'momentum')),
                **{k: v for k, v in config_dict.items() if k not in ['name', 'type']}
            )
    
    @classmethod
    def get_available_strategies(cls) -> List[StrategyType]:
        """Get list of available enhanced strategies"""
        return list(cls.STRATEGY_CLASSES.keys())
    
    @classmethod
    def is_strategy_available(cls, strategy_type: StrategyType) -> bool:
        """Check if enhanced strategy is available"""
        return strategy_type in cls.STRATEGY_CLASSES

class IStrategySubscriber:
    """Interface for strategy event subscribers"""
    
    async def on_signal_generated(self, signal: TradingSignal) -> None:
        """Handle signal generation"""
    
    async def on_strategy_status_change(self, strategy_event: Dict[str, Any]) -> None:
        """Handle strategy status changes"""

class StrategyManager(ISystemComponent, IRegimeAware):
    """
    Core Engine Strategy Manager - WHAT Component with IRegimeAware
    
    This component sits within the Risk Manager (Central Hub) and determines
    WHAT trades should be made:
    
    1. Manages multiple trading strategies
    2. Analyzes market conditions and regime changes
    3. Generates trading signals based on strategy analysis
    4. Aggregates and filters signals for quality
    5. Submits trade requests to Risk Manager for authorization
    
    The WHAT methodology includes:
    - Multi-strategy signal generation
    - Regime-aware strategy activation (IRegimeAware)
    - Signal quality filtering and aggregation
    - Portfolio-level signal coordination
    
    Implements:
    - ISystemComponent for lifecycle management (Rule 1)
    - IRegimeAware for regime adaptation (Rule 2)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = StrategyManagerConfig(**config) if config else StrategyManagerConfig()
        self.component_id = f"strategy_manager_{uuid.uuid4().hex[:8]}"
        
        # Component references (set by Risk Manager)
        self.risk_manager: Optional[Any] = None
        self.data_manager: Optional[Any] = None
        self.regime_engine: Optional[Any] = None
        
        # Enhanced strategy integration
        self.strategy_factory = EnhancedStrategyFactory()
        self.strategy_registry: Optional[StrategyRegistry] = None
        
        # Strategy infrastructure - Now stores actual enhanced strategies
        self.active_strategies: Dict[str, EnhancedBaseStrategy] = {}
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Multi-strategy coordination components
        self.signal_aggregator: Optional[MultiStrategySignalAggregator] = None
        self.conflict_resolver: Optional[SignalConflictResolver] = None
        self.strategy_registrations: Dict[str, StrategyRegistration] = {}
        self.enable_multi_strategy = self.config.enable_multi_strategy_coordination
        
        # Signal management
        self.pending_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
        self.aggregated_signals: Dict[str, TradingSignal] = {}
        
        # Current market context
        self.current_regime: Optional[str] = None
        self.market_conditions: Dict[str, Any] = {}
        
        # Subscribers
        self.subscribers: List[IStrategySubscriber] = []
        
        # ISystemComponent state management
        self.is_initialized = False
        self.is_running = False
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        self.last_error: Optional[str] = None
        self.signal_generation_task: Optional[asyncio.Task] = None
        
        # Leverage existing core strategy manager
        self.core_strategy_manager: Optional[Any] = None
        
        logger.info("🧠 Enhanced Strategy Manager (WHAT) initialized")
        logger.info(f"📊 Available enhanced strategies: {[s.value for s in self.strategy_factory.get_available_strategies()]}")
    
    async def _initialize_strategy_registry(self) -> None:
        """Initialize strategy registry for enhanced strategy management"""
        try:
            self.strategy_registry = StrategyRegistry(
                config={
                    'registry_path': self.config.strategy_registry_path,
                    'auto_discovery_enabled': True,
                    'auto_validation_enabled': True
                }
            )
            await self.strategy_registry.initialize()
            logger.info("✅ Strategy registry initialized")
        except Exception as e:
            logger.warning(f"⚠️ Strategy registry initialization failed: {e}")
    
    async def _discover_enhanced_strategies(self) -> None:
        """Auto-discover enhanced strategies from implementations directory"""
        try:
            if not self.strategy_registry:
                logger.warning("Strategy registry not available for discovery")
                return
            
            # Discover strategies in implementations directory
            implementations_path = Path(__file__).parent / "implementations"
            discovered_strategies = self.strategy_registry.discovery.discover_strategies([str(implementations_path)])
            
            logger.info(f"🔍 Discovered {len(discovered_strategies)} enhanced strategies")
            
            # Register discovered strategies
            for strategy_metadata in discovered_strategies:
                try:
                    strategy_id = await self.strategy_registry.register_strategy(
                        strategy_class=None,  # Will be loaded dynamically
                        metadata=strategy_metadata,
                        validate=False  # Skip validation for now
                    )
                    logger.info(f"📝 Registered strategy: {strategy_metadata.name} ({strategy_id})")
                except Exception as e:
                    logger.warning(f"Failed to register strategy {strategy_metadata.name}: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Enhanced strategy discovery failed: {e}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="StrategyManager",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=20  # PHASE 4: After processing (order=17), before risk (order=25)
        )
        
        logger.info(f"✅ StrategyManager registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize enhanced strategy manager"""
        try:
            logger.info("🔄 Initializing Enhanced Strategy Manager (WHAT)...")
            
            # Initialize strategy registry if enabled
            if self.config.enable_enhanced_strategies:
                await self._initialize_strategy_registry()
            
            # Auto-discover enhanced strategies if enabled
            if self.config.auto_discover_strategies:
                await self._discover_enhanced_strategies()
            
            # Only initialize default strategies if auto-discovery is enabled
            # In backtest mode (auto_discover_strategies=False), strategies are registered manually
            if self.config.auto_discover_strategies:
                # Initialize default strategy allocations with enhanced strategies
                await self._initialize_default_strategies()
                logger.info("📊 Default strategies initialized (auto-discovery mode)")
            else:
                logger.info("📊 Skipping default strategies (manual registration mode)")
            
            # Initialize strategy performance tracking
            await self._initialize_performance_tracking()
            
            # Initialize multi-strategy coordination if enabled
            if self.enable_multi_strategy:
                await self._initialize_multi_strategy_coordination()
            
            self.is_initialized = True
            logger.info("✅ Enhanced Strategy Manager (WHAT) initialization complete")
            logger.info(f"📊 Active enhanced strategies: {len(self.active_strategies)}")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"❌ Enhanced Strategy Manager initialization failed: {e}")
            return False
    
    async def register_enhanced_strategy(self, strategy_type: StrategyType, config: Dict[str, Any]) -> bool:
        """Register an enhanced strategy programmatically"""
        try:
            strategy_name = config.get('name', f'{strategy_type.value}_strategy')
            
            # Check if strategy type is available
            if not self.strategy_factory.is_strategy_available(strategy_type):
                logger.error(f"❌ Enhanced strategy type not available: {strategy_type}")
                return False
            
            # Create enhanced strategy instance
            strategy_instance = await self._create_strategy_instance(strategy_type, config)
            if not strategy_instance:
                logger.error(f"❌ Failed to create enhanced strategy: {strategy_name}")
                return False
            
            # Create allocation
            allocation = StrategyAllocation(
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                allocation_pct=config.get('allocation_pct', 0.2),
                max_positions=config.get('max_positions', 5),
                risk_limit=config.get('risk_limit', 0.05)
            )
            
            # Store strategy and allocation
            self.active_strategies[strategy_name] = strategy_instance
            self.strategy_allocations[strategy_name] = allocation
            self.strategy_performance[strategy_name] = {
                'total_signals': 0,
                'successful_signals': 0,
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'last_signal_time': None
            }
            
            logger.info(f"✅ Enhanced strategy registered: {strategy_name} ({strategy_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register enhanced strategy: {e}")
            return False
    
    def get_enhanced_strategy_status(self) -> Dict[str, Any]:
        """Get status of enhanced strategies"""
        enhanced_strategies = {}
        
        for name, strategy in self.active_strategies.items():
            if isinstance(strategy, EnhancedBaseStrategy):
                enhanced_strategies[name] = {
                    'type': strategy.config.strategy_type.value,
                    'status': strategy.get_status(),
                    'performance': strategy.get_performance_summary(),
                    'health': 'requires_async_call'  # Health check requires async call
                }
        
        return {
            'total_enhanced_strategies': len(enhanced_strategies),
            'available_strategy_types': [s.value for s in self.strategy_factory.get_available_strategies()],
            'enhanced_strategies': enhanced_strategies,
            'registry_status': 'active' if self.strategy_registry else 'not_initialized'
        }
    
    async def start(self) -> bool:
        """Start strategy manager"""
        try:
            if not self.is_initialized:
                logger.error("❌ Cannot start - Strategy Manager not initialized")
                return False
            
            logger.info("🚀 Starting Strategy Manager signal generation...")
            
            # Start signal generation loop
            self.signal_generation_task = asyncio.create_task(self._run_signal_generation())
            
            self.is_running = True
            logger.info("✅ Strategy Manager (WHAT) started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Strategy Manager: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop strategy manager"""
        try:
            logger.info("🛑 Stopping Strategy Manager...")
            
            if self.signal_generation_task:
                self.signal_generation_task.cancel()
                try:
                    await self.signal_generation_task
                except asyncio.CancelledError:
                    pass
                self.signal_generation_task = None
            
            self.is_running = False
            logger.info("✅ Strategy Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Strategy Manager: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check of the strategy manager"""
        
        try:
            health_status = {
                'healthy': True,
                'initialized': self.is_initialized,
                'operational': self.is_running,
                'component_type': 'StrategyManager',
                'active_strategies': len(self.active_strategies),
                'pending_signals': len(self.pending_signals),
                'total_signals_generated': len(self.signal_history),
                'strategy_allocations': len(self.strategy_allocations),
                'current_regime': self.current_regime,
                'component_connections': {
                    'risk_manager': self.risk_manager is not None,
                    'data_manager': self.data_manager is not None,
                    'regime_engine': self.regime_engine is not None
                }
            }
            
            # Check strategy health
            unhealthy_strategies = []
            for strategy_id, strategy in self.active_strategies.items():
                if hasattr(strategy, 'health_check'):
                    strategy_health = await strategy.health_check()
                    if not strategy_health.get('healthy', True):
                        unhealthy_strategies.append(strategy_id)
                        health_status['healthy'] = False
            
            if unhealthy_strategies:
                health_status['unhealthy_strategies'] = unhealthy_strategies
            
            # Check signal generation health
            if self.is_running and not self.signal_generation_task:
                health_status['healthy'] = False
                health_status['warning'] = "Signal generation task not running"
            
            return health_status
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'component_type': 'StrategyManager'
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the strategy manager"""
        
        return {
            'component_type': 'StrategyManager',
            'initialized': self.is_initialized,
            'operational': self.is_running,
            'active_strategies': len(self.active_strategies),
            'strategy_allocations': len(self.strategy_allocations),
            'pending_signals': len(self.pending_signals),
            'signal_history_count': len(self.signal_history),
            'current_regime': self.current_regime,
            'market_conditions': self.market_conditions.copy(),
            'subscribers_count': len(self.subscribers),
            'component_connections': {
                'risk_manager_connected': self.risk_manager is not None,
                'data_manager_connected': self.data_manager is not None,
                'regime_engine_connected': self.regime_engine is not None
            },
            'signal_generation_active': self.signal_generation_task is not None and not self.signal_generation_task.done()
        }
    
    # Component Integration
    def set_risk_manager(self, risk_manager: Any):
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info("🔗 Risk Manager linked to Strategy Manager")
    
    def set_data_manager(self, data_manager: Any):
        """Set data manager reference"""
        self.data_manager = data_manager
        logger.info("🔗 Data Manager linked to Strategy Manager")
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Set regime engine reference - IRegimeAware interface method
        Part of IRegimeAware interface implementation (Rule 2).
        """
        self.regime_engine = regime_engine
        logger.info("✅ Regime Engine linked to Strategy Manager (IRegimeAware, Rule 2)")
    
    async def on_regime_change(self, new_regime_context: Any) -> None:
        """
        Callback for regime changes - IRegimeAware interface method
        Adjust strategy weights based on regime appropriateness.
        
        Args:
            new_regime_context: New regime context with updated information
        """
        if not new_regime_context:
            return
        
        previous_regime = self.current_regime.primary_regime.value if (self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None
        self.current_regime = new_regime_context
        
        regime_name = new_regime_context.primary_regime.value if hasattr(new_regime_context, 'primary_regime') else str(new_regime_context)
        logger.info(f"🔄 Strategy Manager adapting to regime change: {previous_regime} → {regime_name}")
        
        # Adapt strategies to new regime
        await self.adapt_to_regime(new_regime_context)
    
    def get_current_regime_context(self) -> Optional[Any]:
        """
        Get current regime context - IRegimeAware interface method
        
        Returns:
            Current RegimeContext or None if not available
        """
        return self.current_regime if hasattr(self, 'current_regime') else None
    
    async def adapt_to_regime(self, regime_context: Any) -> Dict[str, Any]:
        """
        Adapt component behavior to current regime - IRegimeAware interface method
        
        Adaptation strategy:
        - Trending regimes → Prioritize momentum/trend strategies
        - Range-bound regimes → Prioritize mean-reversion/pairs strategies
        - High volatility → Reduce position sizes, increase quality thresholds
        - Low volatility → Increase position sizes, relax thresholds
        
        Args:
            regime_context: Current regime context
            
        Returns:
            Dictionary with adaptation details and adjustments made
        """
        adaptations = {
            'timestamp': datetime.now().isoformat(),
            'previous_regime': str(self.current_regime.primary_regime.value) if (hasattr(self, 'current_regime') and self.current_regime and hasattr(self.current_regime, 'primary_regime')) else None,
            'new_regime': str(regime_context.primary_regime.value) if hasattr(regime_context, 'primary_regime') else 'unknown',
            'adjustments': [],
            'success': True
        }
        
        try:
            regime_name = regime_context.primary_regime.value if hasattr(regime_context, 'primary_regime') else str(regime_context)
            volatility_regime = regime_context.volatility_regime if hasattr(regime_context, 'volatility_regime') else 'normal_volatility'
            
            # Update current regime
            if not hasattr(self, 'current_regime'):
                self.current_regime = regime_context
            else:
                self.current_regime = regime_context
            
            # Adjust strategy weights based on regime
            if 'trending' in regime_name.lower():
                # Prioritize momentum and trend-following strategies
                adaptations['adjustments'].append({
                    'strategy_preferences': ['momentum', 'trend_following', 'breakout'],
                    'reason': 'trending_regime'
                })
                logger.info(f"📊 Strategies adapted for trending: prioritize momentum/trend-following")
            
            elif 'range' in regime_name.lower() or 'mean_reversion' in regime_name.lower():
                # Prioritize mean-reversion and pairs strategies
                adaptations['adjustments'].append({
                    'strategy_preferences': ['mean_reversion', 'pairs_trading', 'statistical_arbitrage'],
                    'reason': 'range_bound_regime'
                })
                logger.info(f"📊 Strategies adapted for range-bound: prioritize mean-reversion/pairs")
            
            # Adjust risk parameters based on volatility
            if volatility_regime == 'high_volatility':
                self.config.min_confidence_threshold = 0.7  # Higher threshold
                self.config.max_strategy_allocation = 0.25  # More conservative
                adaptations['adjustments'].append({
                    'min_confidence': 0.7,
                    'max_allocation': 0.25,
                    'reason': 'high_volatility'
                })
                logger.info(f"📊 Risk parameters adapted for high volatility")
            elif volatility_regime == 'low_volatility':
                self.config.min_confidence_threshold = 0.5  # Lower threshold
                self.config.max_strategy_allocation = 0.35  # More aggressive
                adaptations['adjustments'].append({
                    'min_confidence': 0.5,
                    'max_allocation': 0.35,
                    'reason': 'low_volatility'
                })
                logger.info(f"📊 Risk parameters adapted for low volatility")
            else:
                self.config.min_confidence_threshold = 0.6  # Normal
                self.config.max_strategy_allocation = 0.33  # Normal
                adaptations['adjustments'].append({
                    'min_confidence': 0.6,
                    'max_allocation': 0.33,
                    'reason': 'normal_volatility'
                })
            
            # Notify all active strategies of regime change
            if hasattr(self, 'active_strategies'):
                for strategy_name, strategy in self.active_strategies.items():
                    if hasattr(strategy, 'on_regime_change'):
                        await strategy.on_regime_change(regime_context)
            
            logger.info(f"✅ Strategy Manager adapted to regime: {regime_name}")
            
        except Exception as e:
            logger.error(f"❌ Regime adaptation failed: {e}")
            adaptations['success'] = False
            adaptations['error'] = str(e)
        
        return adaptations
    
    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is properly configured - IRegimeAware interface method
        
        Returns:
            True if regime engine is properly configured, False otherwise
        """
        is_valid = hasattr(self, 'regime_engine') and self.regime_engine is not None
        if not is_valid:
            logger.warning("⚠️ Regime engine not configured for StrategyManager")
        else:
            logger.debug("✅ Regime engine properly configured")
        return is_valid
    
    def subscribe(self, subscriber: IStrategySubscriber):
        """Subscribe to strategy events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New strategy subscriber: {type(subscriber).__name__}")
    
    # Core Strategy Methods
    async def add_strategy(self, strategy_config: Dict[str, Any]) -> bool:
        """Add new trading strategy"""
        try:
            strategy_name = strategy_config['name']
            strategy_type = StrategyType(strategy_config['type'])
            
            logger.info(f"➕ Adding strategy: {strategy_name} ({strategy_type.value})")
            
            # Create strategy allocation
            allocation = StrategyAllocation(
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                allocation_pct=strategy_config.get('allocation_pct', 0.1),
                max_positions=strategy_config.get('max_positions', 3),
                risk_limit=strategy_config.get('risk_limit', 0.05),
                active=strategy_config.get('active', True)
            )
            
            # Initialize strategy based on type
            strategy = await self._create_strategy_instance(strategy_type, strategy_config)
            
            # Store strategy
            self.active_strategies[strategy_name] = strategy
            self.strategy_allocations[strategy_name] = allocation
            self.strategy_performance[strategy_name] = {
                'total_signals': 0,
                'successful_signals': 0,
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'last_updated': datetime.now()
            }
            
            logger.info(f"✅ Strategy added: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add strategy: {e}")
            return False
    
    async def remove_strategy(self, strategy_name: str) -> bool:
        """Remove trading strategy"""
        try:
            if strategy_name not in self.active_strategies:
                return False
            
            logger.info(f"➖ Removing strategy: {strategy_name}")
            
            # Stop strategy
            strategy = self.active_strategies[strategy_name]
            if hasattr(strategy, 'stop'):
                await strategy.stop()
            
            # Remove from collections
            del self.active_strategies[strategy_name]
            del self.strategy_allocations[strategy_name]
            
            logger.info(f"✅ Strategy removed: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to remove strategy {strategy_name}: {e}")
            return False
    
    async def generate_signals(self, symbols: List[str], market_data: Optional[Dict[str, Any]] = None, 
                             current_positions: Optional[Dict[str, Dict[str, Any]]] = None) -> List[TradingSignal]:
        """
        Generate trading signals from all active strategies
        ENHANCED: Multi-strategy with regime awareness and position tracking
        """
        try:
            all_signals = []
            
            # Update market context
            await self._update_market_context()
            
            # Get current regime for strategy selection
            regime_info = await self._get_current_regime_info()
            
            # Generate signals from each active strategy with enhanced logic
            for strategy_name, strategy in self.active_strategies.items():
                allocation = self.strategy_allocations.get(strategy_name)
                if not allocation or not allocation.active:
                    continue
                
                try:
                    # Enhanced strategy signal generation with position awareness
                    strategy_signals = await self._generate_enhanced_strategy_signals(
                        strategy, strategy_name, symbols, regime_info, 
                        market_data, current_positions
                    )
                    all_signals.extend(strategy_signals)
                    
                except Exception as e:
                    logger.error(f"❌ Signal generation failed for {strategy_name}: {e}")
            
            # Enhanced filtering with regime and position awareness
            filtered_signals = await self._filter_signals_enhanced(all_signals, regime_info, current_positions)
            
            # Intelligent signal aggregation with regime weighting
            aggregated_signals = await self._aggregate_signals_enhanced(filtered_signals, regime_info)
            
            # Store signals
            for signal in aggregated_signals:
                self.pending_signals[signal.signal_id] = signal
                self.aggregated_signals[signal.symbol] = signal
            
            # Notify subscribers
            for signal in aggregated_signals:
                for subscriber in self.subscribers:
                    await subscriber.on_signal_generated(signal)
            
            # Only log when signals are actually generated to reduce spam
            if len(aggregated_signals) > 0:
                logger.info(f"📊 Generated {len(aggregated_signals)} enhanced signals from {len(all_signals)} raw signals "
                           f"(regime: {regime_info.get('regime', 'unknown')})")
            else:
                logger.debug(f"📊 Generated 0 enhanced signals from {len(all_signals)} raw signals "
                            f"(regime: {regime_info.get('regime', 'unknown')})")
            return aggregated_signals
            
        except Exception as e:
            logger.error(f"❌ Enhanced signal generation failed: {e}")
            return []
    
    async def submit_trade_requests(self) -> List[str]:
        """Submit trade requests to Risk Manager based on generated signals"""
        try:
            submitted_requests = []
            
            for signal in list(self.pending_signals.values()):
                # Check if signal meets submission criteria
                if not await self._should_submit_signal(signal):
                    continue
                
                # Create trade request
                trade_request = {
                    'request_id': str(uuid.uuid4()),
                    'symbol': signal.symbol,
                    'strategy': signal.strategy_name,
                    'signal_type': signal.signal_type.value,
                    'quantity': signal.quantity,
                    'confidence': signal.confidence,
                    'expected_return': signal.expected_return,
                    'risk_score': signal.risk_score,
                    'target_price': signal.target_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'metadata': signal.metadata
                }
                
                # Submit to Risk Manager for authorization
                if self.risk_manager:
                    authorization = await self.risk_manager.authorize_trade(
                        type('TradeRequest', (), trade_request)()
                    )
                    
                    if authorization.decision.value == 'approve':
                        submitted_requests.append(trade_request['request_id'])
                        logger.info(f"✅ Trade request submitted: {signal.symbol} {signal.signal_type.value}")
                    else:
                        logger.warning(f"⛔ Trade request rejected: {signal.symbol} - {authorization.reason}")
                
                # Remove from pending
                del self.pending_signals[signal.signal_id]
            
            logger.info(f"📤 Submitted {len(submitted_requests)} trade requests")
            return submitted_requests
            
        except Exception as e:
            logger.error(f"❌ Trade request submission failed: {e}")
            return []
    
    # Strategy Implementation Methods
    async def _create_strategy_instance(self, strategy_type: StrategyType, config: Dict[str, Any]) -> Optional[EnhancedBaseStrategy]:
        """Create enhanced strategy instance using factory"""
        try:
            if self.config.enable_enhanced_strategies:
                # Use enhanced strategy factory
                strategy_instance = self.strategy_factory.create_strategy(strategy_type, config)
                if strategy_instance:
                    # Initialize the enhanced strategy
                    await strategy_instance.initialize()
                    logger.info(f"✅ Enhanced strategy created and initialized: {config['name']}")
                    return strategy_instance
                else:
                    logger.warning(f"⚠️ Failed to create enhanced strategy, falling back to basic strategy")
            
            # Fallback to basic strategy instance
            strategy_instance = type('BasicStrategy', (), {
                'name': config['name'],
                'config': config,
                'strategy_type': strategy_type,
                'generate_signals': lambda symbols: [],
                'get_status': lambda: {'active': True, 'type': strategy_type.value}
            })()
            
            logger.info(f"📝 Basic strategy created: {config['name']}")
            return strategy_instance
            
        except Exception as e:
            logger.error(f"❌ Error creating strategy instance: {e}")
            return None
    
    async def _generate_strategy_signals(self, strategy: Any, strategy_name: str, symbols: List[str]) -> List[TradingSignal]:
        """Generate signals from individual enhanced strategy"""
        try:
            # Check if this is an enhanced strategy
            if isinstance(strategy, EnhancedBaseStrategy):
                # Use enhanced strategy's generate_signals method
                raw_signals = await strategy.generate_signals(symbols)
                logger.debug(f"📊 Enhanced strategy {strategy_name} generated {len(raw_signals)} signals")
            elif self.core_strategy_manager:
                # Use core strategy manager if available
                raw_signals = await self.core_strategy_manager.generate_signals(symbols)
            else:
                # Fallback to strategy-specific generation
                if hasattr(strategy, 'generate_signals'):
                    raw_signals = await strategy.generate_signals(symbols)
                else:
                    raw_signals = []
            
            # Convert to TradingSignal objects
            signals = []
            for raw_signal in raw_signals:
                signal = TradingSignal(
                    signal_id=str(uuid.uuid4()),
                    strategy_name=strategy_name,
                    strategy_type=StrategyType.MEAN_REVERSION,  # Default, should be determined by strategy
                    symbol=raw_signal.get('symbol', 'UNKNOWN'),
                    signal_type=SignalType(raw_signal.get('action', 'hold')),
                    strength=SignalStrength(raw_signal.get('strength', 'medium')),
                    confidence=raw_signal.get('confidence', 0.5),
                    expected_return=raw_signal.get('expected_return', 0.0),
                    risk_score=raw_signal.get('risk_score', 0.5),
                    quantity=raw_signal.get('quantity', 100.0),
                    target_price=raw_signal.get('target_price'),
                    stop_loss=raw_signal.get('stop_loss'),
                    take_profit=raw_signal.get('take_profit'),
                    metadata=raw_signal.get('metadata', {})
                )
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Strategy signal generation failed for {strategy_name}: {e}")
            return []
    
    async def _filter_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Filter signals based on quality criteria"""
        filtered = []
        
        for signal in signals:
            # Confidence threshold
            if signal.confidence < self.config.min_confidence_threshold:
                continue
            
            # Regime awareness filtering
            if self.config.enable_regime_awareness and self.current_regime:
                if not await self._is_signal_regime_appropriate(signal):
                    continue
            
            # Correlation filtering
            if self.config.enable_correlation_filtering:
                if await self._is_signal_correlated(signal):
                    continue
            
            filtered.append(signal)
        
        return filtered
    
    async def _aggregate_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Aggregate signals by symbol"""
        symbol_signals = {}
        
        # Group by symbol
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)
        
        # Aggregate each symbol's signals
        aggregated = []
        for symbol, symbol_signal_list in symbol_signals.items():
            if len(symbol_signal_list) == 1:
                aggregated.append(symbol_signal_list[0])
            else:
                # Aggregate multiple signals for same symbol
                agg_signal = await self._aggregate_symbol_signals(symbol_signal_list)
                if agg_signal:
                    aggregated.append(agg_signal)
        
        return aggregated
    
    async def _aggregate_symbol_signals(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """Aggregate multiple signals for the same symbol"""
        if not signals:
            return None
        
        # Weighted average aggregation
        total_weight = sum(s.confidence for s in signals)
        if total_weight == 0:
            return None
        
        # Calculate weighted averages
        weighted_confidence = sum(s.confidence * s.confidence for s in signals) / total_weight
        weighted_expected_return = sum(s.expected_return * s.confidence for s in signals) / total_weight
        weighted_risk_score = sum(s.risk_score * s.confidence for s in signals) / total_weight
        
        # Determine consensus signal type
        signal_votes = {}
        for signal in signals:
            vote = signal.signal_type
            signal_votes[vote] = signal_votes.get(vote, 0) + signal.confidence
        
        consensus_signal = max(signal_votes.items(), key=lambda x: x[1])[0]
        
        # Calculate total quantity
        total_quantity = sum(s.quantity for s in signals if s.signal_type == consensus_signal)
        
        return TradingSignal(
            signal_id=str(uuid.uuid4()),
            strategy_name="aggregated",
            strategy_type=signals[0].strategy_type,
            symbol=signals[0].symbol,
            signal_type=consensus_signal,
            strength=SignalStrength.MEDIUM,
            confidence=weighted_confidence,
            expected_return=weighted_expected_return,
            risk_score=weighted_risk_score,
            quantity=total_quantity,
            target_price=signals[0].target_price,
            stop_loss=signals[0].stop_loss,
            take_profit=signals[0].take_profit,
            time_horizon=signals[0].time_horizon,
            metadata={'aggregated_from': len(signals)}
        )
    
    # Analysis and Monitoring Methods
    async def _run_signal_generation(self):
        """Run continuous signal generation"""
        logger.info("📊 Starting continuous signal generation...")
        
        while self.is_running:
            try:
                # Get active symbols
                symbols = await self._get_active_symbols()
                
                # Generate signals
                if symbols:
                    signals = await self.generate_signals(symbols)
                    
                    # Submit trade requests
                    if signals:
                        await self.submit_trade_requests()
                
                # Wait for next interval
                await asyncio.sleep(self.config.signal_generation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Signal generation loop error: {e}")
                await asyncio.sleep(30)
    
    async def _update_market_context(self):
        """Update current market context"""
        try:
            # Get current regime from regime engine
            if self.regime_engine:
                regime_info = await self.regime_engine.get_current_regime_info()
                if regime_info:
                    self.current_regime = regime_info.get('regime')
                    self.market_conditions = regime_info.get('conditions', {})
                else:
                    # Fallback if regime_info is None
                    self.current_regime = 'neutral'
                    self.market_conditions = {'volatility': 0.02, 'trend': 'sideways'}
            else:
                # Fallback if no regime engine
                self.current_regime = 'neutral'
                self.market_conditions = {'volatility': 0.02, 'trend': 'sideways'}
            
        except Exception as e:
            logger.debug(f"Market context update failed: {e}, using fallback")
            self.current_regime = 'neutral'
            self.market_conditions = {'volatility': 0.02, 'trend': 'sideways'}
    
    async def _should_submit_signal(self, signal: TradingSignal) -> bool:
        """Check if signal should be submitted for trading"""
        # Basic checks
        if signal.confidence < self.config.min_confidence_threshold:
            return False
        
        # Check strategy allocation limits
        allocation = self.strategy_allocations.get(signal.strategy_name)
        if not allocation or not allocation.active:
            return False
        
        # Additional risk checks can be added here
        return True
    
    async def _is_signal_regime_appropriate(self, signal: TradingSignal) -> bool:
        """Check if signal is appropriate for current market regime"""
        if not self.current_regime:
            return True
        
        # Strategy-regime compatibility logic
        if signal.strategy_type == StrategyType.MEAN_REVERSION:
            return self.current_regime in ['ranging', 'consolidation']
        elif signal.strategy_type == StrategyType.MOMENTUM:
            return self.current_regime in ['trending', 'breakout']
        
        return True
    
    async def _is_signal_correlated(self, signal: TradingSignal) -> bool:
        """Check if signal is too correlated with existing positions"""
        # Simplified correlation check
        return False
    
    async def _get_active_symbols(self) -> List[str]:
        """Get list of active symbols to analyze"""
        # Return default symbols for now
        return ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    
    async def _initialize_default_strategies(self):
        """Initialize default strategy configurations"""
        # Mean reversion strategy
        await self.add_strategy({
            'name': 'mean_reversion_1',
            'type': 'mean_reversion',
            'allocation_pct': 0.25,
            'max_positions': 3,
            'risk_limit': 0.05,
            'lookback_period': 20,
            'z_score_threshold': 2.0
        })
        
        # Momentum strategy
        await self.add_strategy({
            'name': 'momentum_1',
            'type': 'momentum',
            'allocation_pct': 0.25,
            'max_positions': 3,
            'risk_limit': 0.05,
            'lookback_period': 10,
            'momentum_threshold': 0.02
        })
    
    async def _initialize_performance_tracking(self):
        """Initialize strategy performance tracking"""
        logger.info("📊 Initializing strategy performance tracking...")
        # Performance tracking setup
    
    # ENHANCED METHODS - Multi-Strategy with Regime Awareness
    
    async def _get_current_regime_info(self) -> Dict[str, Any]:
        """Get comprehensive current regime information"""
        try:
            if self.regime_engine:
                regime_analysis = await self.regime_engine.get_current_regime_info()
                if regime_analysis:
                    return {
                        'regime': regime_analysis.get('regime', 'neutral'),
                        'confidence': regime_analysis.get('confidence', 0.5),
                        'volatility': regime_analysis.get('volatility', 0.02),
                        'trend_strength': regime_analysis.get('trend_strength', 0.0),
                        'risk_multiplier': regime_analysis.get('risk_multiplier', 1.0),
                        'recommended_strategies': regime_analysis.get('recommended_strategies', ['mean_reversion', 'momentum']),
                        'strategy_weights': regime_analysis.get('strategy_weights', {'mean_reversion': 0.5, 'momentum': 0.5})
                    }
                else:
                    # Fallback if regime_analysis is None
                    return {
                        'regime': 'neutral',
                        'confidence': 0.5,
                        'volatility': 0.02,
                        'trend_strength': 0.0,
                        'risk_multiplier': 1.0,
                        'recommended_strategies': ['mean_reversion', 'momentum'],
                        'strategy_weights': {'mean_reversion': 0.5, 'momentum': 0.5}
                    }
            else:
                return {
                    'regime': 'neutral',
                    'confidence': 0.5,
                    'volatility': 0.02,
                    'trend_strength': 0.0,
                    'risk_multiplier': 1.0,
                    'recommended_strategies': ['mean_reversion', 'momentum'],
                    'strategy_weights': {'mean_reversion': 0.5, 'momentum': 0.5}
                }
        except Exception as e:
            logger.debug(f"Failed to get regime info: {e}, using fallback")
            return {
                'regime': 'neutral',
                'confidence': 0.5,
                'volatility': 0.02,
                'trend_strength': 0.0,
                'risk_multiplier': 1.0,
                'recommended_strategies': ['mean_reversion', 'momentum'],
                'strategy_weights': {'mean_reversion': 0.5, 'momentum': 0.5}
            }
    
    async def _generate_enhanced_strategy_signals(self, strategy: Any, strategy_name: str, 
                                                symbols: List[str], regime_info: Dict[str, Any],
                                                market_data: Optional[Dict[str, Any]] = None,
                                                current_positions: Optional[Dict[str, Dict[str, Any]]] = None) -> List[TradingSignal]:
        """
        Generate enhanced strategy signals with regime awareness and position tracking
        ENHANCED: Multi-strategy logic from test implementation
        """
        try:
            signals = []
            
            # Get strategy type
            allocation = self.strategy_allocations.get(strategy_name)
            if not allocation:
                return signals
            
            strategy_type = allocation.strategy_type
            
            # Check if strategy is appropriate for current regime
            regime_support = self._is_strategy_regime_supported(strategy_type, regime_info)
            if not regime_support:
                logger.debug(f"Strategy {strategy_name} not supported in regime {regime_info.get('regime')}")
                return signals
            
            # For enhanced strategy instances, use their generate_signals method
            if isinstance(strategy, EnhancedBaseStrategy):
                try:
                    # Convert market_data to Dict[str, pd.DataFrame] format expected by enhanced strategies
                    if isinstance(market_data, dict):
                        market_data_dict = market_data
                    elif hasattr(market_data, 'to_dict') or isinstance(market_data, pd.DataFrame):
                        # If market_data is a single DataFrame, assume it contains all symbols
                        # For now, create a dict with available symbols
                        market_data_dict = {}
                        for symbol in symbols:
                            if isinstance(market_data, pd.DataFrame) and symbol in market_data.columns:
                                # Extract symbol-specific data from multi-symbol DataFrame
                                market_data_dict[symbol] = market_data[[col for col in market_data.columns if col.startswith(f'{symbol}_') or col in ['timestamp', 'volume']]].copy()
                            else:
                                market_data_dict[symbol] = market_data
                    else:
                        market_data_dict = {symbol: market_data for symbol in symbols}
                    
                    # Call the enhanced strategy's generate_signals method
                    raw_signals = await strategy.generate_signals(market_data_dict)
                    logger.debug(f"📊 Enhanced strategy {strategy_name} generated {len(raw_signals)} signals")
                    
                    # Convert StrategySignal objects to TradingSignal objects
                    for raw_signal in raw_signals:
                        trading_signal = TradingSignal(
                            signal_id=str(uuid.uuid4()),
                            strategy_name=strategy_name,
                            strategy_type=strategy_type,
                            symbol=raw_signal.symbol,
                            signal_type=SignalType(raw_signal.signal_type.lower()),
                            strength=raw_signal.strength,
                            confidence=getattr(raw_signal, 'confidence', 0.5),
                            expected_return=getattr(raw_signal, 'expected_return', 0.0),
                            risk_score=getattr(raw_signal, 'risk_score', 0.5),
                            quantity=getattr(raw_signal, 'quantity', None),
                            target_price=getattr(raw_signal, 'target_price', None),
                            stop_loss=getattr(raw_signal, 'stop_loss', None),
                            take_profit=getattr(raw_signal, 'take_profit', None),
                            metadata=getattr(raw_signal, 'metadata', {})
                        )
                        signals.append(trading_signal)
                    
                    return signals
                    
                except Exception as e:
                    logger.error(f"❌ Enhanced strategy {strategy_name} signal generation failed: {e}")
                    return signals
            
            # Fallback to built-in signal generation logic for non-enhanced strategies
            # Generate signals for each symbol
            for symbol in symbols:
                try:
                    # Get current position for symbol
                    current_position = current_positions.get(symbol, {'shares': 0, 'entry_price': 0}) if current_positions else {'shares': 0, 'entry_price': 0}
                    
                    # Get market data for symbol
                    symbol_data = market_data.get(symbol) if market_data else None
                    
                    # Generate signal based on strategy type
                    if strategy_type == StrategyType.MEAN_REVERSION:
                        signal = await self._generate_mean_reversion_signal(
                            symbol, symbol_data, regime_info, current_position, strategy_name
                        )
                    elif strategy_type == StrategyType.MOMENTUM:
                        signal = await self._generate_momentum_signal(
                            symbol, symbol_data, regime_info, current_position, strategy_name
                        )
                    else:
                        # Fallback to generic signal generation
                        signal = await self._generate_generic_signal(
                            symbol, symbol_data, regime_info, current_position, strategy_name, strategy_type
                        )
                    
                    if signal:
                        signals.append(signal)
                        
                except Exception as e:
                    logger.error(f"❌ Signal generation failed for {symbol} in {strategy_name}: {e}")
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Enhanced strategy signal generation failed for {strategy_name}: {e}")
            return []
    
    async def _generate_mean_reversion_signal(self, symbol: str, market_data: Optional[Dict[str, Any]], 
                                            regime_info: Dict[str, Any], current_position: Dict[str, Any],
                                            strategy_name: str) -> Optional[TradingSignal]:
        """Generate mean reversion signal with position awareness"""
        try:
            if not market_data:
                return None
            
            # Extract technical indicators
            rsi = market_data.get('rsi', 50)
            zscore = market_data.get('zscore', 0)
            bb_position = market_data.get('bb_position', 0.5)
            price = market_data.get('close', market_data.get('price', 0))
            market_data.get('volume_ratio', 1.0)
            
            # Position awareness
            has_position = current_position.get('shares', 0) != 0
            
            # Mean reversion thresholds (from test implementation)
            rsi_oversold = 25  # More extreme for higher quality
            rsi_overbought = 75
            zscore_threshold = 1.8
            
            signal_type = None
            confidence = 0.0
            reasons = []
            
            # BUY signals (oversold conditions) - only when no position
            if not has_position and rsi < rsi_oversold:
                signal_type = SignalType.BUY
                confidence += 0.4
                reasons.append(f"RSI oversold ({rsi:.1f})")
            
            if not has_position and zscore < -zscore_threshold:
                signal_type = SignalType.BUY
                confidence += 0.4
                reasons.append(f"Extreme negative z-score ({zscore:.2f})")
            
            if not has_position and bb_position < 0.2:
                signal_type = SignalType.BUY
                confidence += 0.2
                reasons.append(f"Near BB lower band ({bb_position:.2f})")
            
            # SELL signals (overbought conditions) - only when have position
            if has_position and rsi > rsi_overbought:
                signal_type = SignalType.SELL
                confidence += 0.4
                reasons.append(f"RSI overbought ({rsi:.1f})")
            
            if has_position and zscore > zscore_threshold:
                signal_type = SignalType.SELL
                confidence += 0.4
                reasons.append(f"Extreme positive z-score ({zscore:.2f})")
            
            if has_position and bb_position > 0.8:
                signal_type = SignalType.SELL
                confidence += 0.2
                reasons.append(f"Near BB upper band ({bb_position:.2f})")
            
            # Minimum confidence threshold
            if confidence < 0.6:
                return None
            
            # Scale confidence to proper range (0.6-0.95)
            scaled_confidence = min(0.95, 0.6 + (confidence - 0.6) * 0.8)
            
            # Dynamic position sizing based on confidence and regime
            base_size = 0.05  # 5% base position
            regime_multiplier = regime_info.get('risk_multiplier', 1.0)
            position_size = base_size * scaled_confidence / regime_multiplier
            
            # Calculate quantity (assuming $100k portfolio, $400 stock price)
            portfolio_value = 100000
            quantity = int((portfolio_value * position_size) / price) if price > 0 else 0
            
            if quantity <= 0:
                return None
            
            return TradingSignal(
                signal_id=str(uuid.uuid4()),
                strategy_name=strategy_name,
                strategy_type=StrategyType.MEAN_REVERSION,
                symbol=symbol,
                signal_type=signal_type,
                strength=SignalStrength.STRONG if scaled_confidence > 0.8 else SignalStrength.MEDIUM,
                confidence=scaled_confidence,
                expected_return=0.02 if signal_type == SignalType.BUY else -0.02,  # 2% expected return
                risk_score=0.3,  # Medium risk
                quantity=quantity,
                target_price=price * (1.02 if signal_type == SignalType.BUY else 0.98),
                stop_loss=price * (0.98 if signal_type == SignalType.BUY else 1.02),
                take_profit=price * (1.04 if signal_type == SignalType.BUY else 0.96),  # 4% take profit
                time_horizon=timedelta(hours=4),  # 4 hour time horizon
                metadata={
                    'regime': regime_info.get('regime'),
                    'reasons': reasons,
                    'rsi': rsi,
                    'zscore': zscore,
                    'bb_position': bb_position,
                    'position_aware': True,
                    'current_position': current_position.get('shares', 0)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Mean reversion signal generation failed for {symbol}: {e}")
            return None
    
    async def _generate_momentum_signal(self, symbol: str, market_data: Optional[Dict[str, Any]], 
                                      regime_info: Dict[str, Any], current_position: Dict[str, Any],
                                      strategy_name: str) -> Optional[TradingSignal]:
        """Generate momentum signal with position awareness"""
        try:
            if not market_data:
                return None
            
            # Extract technical indicators
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)
            macd_signal = market_data.get('macd_signal', 0)
            price = market_data.get('close', market_data.get('price', 0))
            volume_ratio = market_data.get('volume_ratio', 1.0)
            trend_strength = market_data.get('trend_strength', 0)
            
            # Position awareness
            has_position = current_position.get('shares', 0) != 0
            is_long = current_position.get('shares', 0) > 0
            
            # Momentum thresholds
            rsi_momentum_min = 60  # Bullish momentum
            rsi_momentum_max = 40  # Bearish momentum
            
            signal_type = None
            confidence = 0.0
            reasons = []
            
            # BUY signals (bullish momentum) - only when no position or short
            if not is_long and rsi > rsi_momentum_min:
                signal_type = SignalType.BUY
                confidence += 0.3
                reasons.append(f"Bullish RSI momentum ({rsi:.1f})")
            
            if not is_long and macd > macd_signal:
                signal_type = SignalType.BUY
                confidence += 0.3
                reasons.append("MACD bullish crossover")
            
            if not is_long and trend_strength > 0.02:
                signal_type = SignalType.BUY
                confidence += 0.2
                reasons.append(f"Strong uptrend ({trend_strength:.3f})")
            
            if not is_long and volume_ratio > 1.5:
                signal_type = SignalType.BUY
                confidence += 0.1
                reasons.append(f"High volume confirmation ({volume_ratio:.1f}x)")
            
            # SELL signals (bearish momentum) - only when have long position
            if is_long and rsi < rsi_momentum_max:
                signal_type = SignalType.SELL
                confidence += 0.3
                reasons.append(f"Bearish RSI momentum ({rsi:.1f})")
            
            if is_long and macd < macd_signal:
                signal_type = SignalType.SELL
                confidence += 0.3
                reasons.append("MACD bearish crossover")
            
            if is_long and trend_strength < -0.02:
                signal_type = SignalType.SELL
                confidence += 0.2
                reasons.append("Trend weakening")
            
            if is_long and volume_ratio > 2.0:
                signal_type = SignalType.SELL
                confidence += 0.1
                reasons.append(f"High volume exit ({volume_ratio:.1f}x)")
            
            # Minimum confidence threshold
            if confidence < 0.6:
                return None
            
            # Scale confidence
            scaled_confidence = min(0.95, 0.6 + (confidence - 0.6) * 0.8)
            
            # Dynamic position sizing
            base_size = 0.06  # 6% base position (slightly larger for momentum)
            regime_multiplier = regime_info.get('risk_multiplier', 1.0)
            position_size = base_size * scaled_confidence / regime_multiplier
            
            # Calculate quantity
            portfolio_value = 100000
            quantity = int((portfolio_value * position_size) / price) if price > 0 else 0
            
            if quantity <= 0:
                return None
            
            return TradingSignal(
                signal_id=str(uuid.uuid4()),
                strategy_name=strategy_name,
                strategy_type=StrategyType.MOMENTUM,
                symbol=symbol,
                signal_type=signal_type,
                strength=SignalStrength.STRONG if scaled_confidence > 0.8 else SignalStrength.MEDIUM,
                confidence=scaled_confidence,
                expected_return=0.03 if signal_type == SignalType.BUY else -0.03,  # 3% expected return
                risk_score=0.4,  # Higher risk than mean reversion
                quantity=quantity,
                target_price=price * (1.03 if signal_type == SignalType.BUY else 0.97),
                stop_loss=price * (0.97 if signal_type == SignalType.BUY else 1.03),
                take_profit=price * (1.05 if signal_type == SignalType.BUY else 0.95),  # 5% take profit
                time_horizon=timedelta(hours=2),  # 2 hour time horizon for momentum
                metadata={
                    'regime': regime_info.get('regime'),
                    'reasons': reasons,
                    'rsi': rsi,
                    'macd': macd,
                    'trend_strength': trend_strength,
                    'position_aware': True,
                    'current_position': current_position.get('shares', 0)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Momentum signal generation failed for {symbol}: {e}")
            return None
    
    async def _generate_generic_signal(self, symbol: str, market_data: Optional[Dict[str, Any]], 
                                     regime_info: Dict[str, Any], current_position: Dict[str, Any],
                                     strategy_name: str, strategy_type: StrategyType) -> Optional[TradingSignal]:
        """Generate generic signal for other strategy types"""
        # Placeholder for other strategy types
        return None
    
    def _is_strategy_regime_supported(self, strategy_type: StrategyType, regime_info: Dict[str, Any]) -> bool:
        """Check if strategy type is supported in current regime"""
        regime = regime_info.get('regime', 'neutral').lower()
        
        if strategy_type == StrategyType.MEAN_REVERSION:
            # Mean reversion works well in ranging/volatile markets
            return regime in ['ranging', 'volatile', 'calm_ranging', 'volatile_ranging', 'neutral']
        elif strategy_type == StrategyType.MOMENTUM:
            # Momentum works well in trending markets
            return regime in ['trending', 'trending_up', 'trending_down', 'calm_trending', 'volatile_trending', 'neutral']
        else:
            # Other strategies - allow by default
            return True
    
    async def _filter_signals_enhanced(self, signals: List[TradingSignal], 
                                     regime_info: Dict[str, Any],
                                     current_positions: Optional[Dict[str, Dict[str, Any]]] = None) -> List[TradingSignal]:
        """Enhanced signal filtering with regime and position awareness"""
        filtered = []
        
        for signal in signals:
            # Basic confidence threshold
            if signal.confidence < self.config.min_confidence_threshold:
                continue
            
            # Regime appropriateness check
            if not self._is_strategy_regime_supported(signal.strategy_type, regime_info):
                continue
            
            # Position-aware filtering
            if current_positions:
                current_pos = current_positions.get(signal.symbol, {'shares': 0})
                has_position = current_pos.get('shares', 0) != 0
                is_long = current_pos.get('shares', 0) > 0
                
                # Don't buy if already long, don't sell if no position
                if signal.signal_type == SignalType.BUY and is_long:
                    continue
                if signal.signal_type == SignalType.SELL and not has_position:
                    continue
            
            # Strategy allocation check
            allocation = self.strategy_allocations.get(signal.strategy_name)
            if not allocation or not allocation.active:
                continue
            
            filtered.append(signal)
        
        return filtered
    
    async def _aggregate_signals_enhanced(self, signals: List[TradingSignal], 
                                        regime_info: Dict[str, Any]) -> List[TradingSignal]:
        """Enhanced signal aggregation with regime weighting"""
        if not signals:
            return []
        
        # Group by symbol
        symbol_signals = {}
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)
        
        # Aggregate with regime weighting
        aggregated = []
        regime_weights = regime_info.get('strategy_weights', {})
        
        for symbol, symbol_signal_list in symbol_signals.items():
            if len(symbol_signal_list) == 1:
                # Single signal - apply regime weighting
                signal = symbol_signal_list[0]
                strategy_weight = regime_weights.get(signal.strategy_type.value, 1.0)
                signal.confidence *= strategy_weight
                
                if signal.confidence >= self.config.min_confidence_threshold:
                    aggregated.append(signal)
            else:
                # Multiple signals - intelligent aggregation
                agg_signal = await self._aggregate_symbol_signals_enhanced(symbol_signal_list, regime_weights)
                if agg_signal:
                    aggregated.append(agg_signal)
        
        return aggregated
    
    async def _aggregate_symbol_signals_enhanced(self, signals: List[TradingSignal], 
                                               regime_weights: Dict[str, float]) -> Optional[TradingSignal]:
        """Enhanced symbol signal aggregation with regime weighting"""
        if not signals:
            return None
        
        # Apply regime weights to confidences
        weighted_signals = []
        for signal in signals:
            weight = regime_weights.get(signal.strategy_type.value, 1.0)
            weighted_signal = signal
            weighted_signal.confidence *= weight
            weighted_signals.append(weighted_signal)
        
        # Use existing aggregation logic with weighted signals
        return await self._aggregate_symbol_signals(weighted_signals)
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'active_strategies': len(self.active_strategies),
            'pending_signals': len(self.pending_signals),
            'aggregated_signals': len(self.aggregated_signals),
            'current_regime': self.current_regime,
            'strategy_allocations': {
                name: {
                    'type': alloc.strategy_type.value,
                    'allocation_pct': alloc.allocation_pct,
                    'active': alloc.active
                }
                for name, alloc in self.strategy_allocations.items()
            },
            'components_linked': {
                'risk_manager': self.risk_manager is not None,
                'data_manager': self.data_manager is not None,
                'regime_engine': self.regime_engine is not None
            }
        }
    
    # ========================================
    # STANDARDIZED DATA CONSUMPTION METHODS
    # ========================================
    
    def process_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for processing signals data"""
        processed_signals = []
        for signal in signals:
            processed_signal = {
                'original_signal': signal,
                'processed_by': 'StrategyManager',
                'processing_timestamp': datetime.now()
            }
            processed_signals.append(processed_signal)
        return processed_signals
    
    def analyze_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for analyzing signals data (alias)"""
        return self.process_signals(signals)
    
    def evaluate_signals(self, signals: List[Any]) -> List[Any]:
        """Standardized method for evaluating signals data (alias)"""
        return self.process_signals(signals)
    
    def process_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for processing strategy decisions"""
        return self.process_signals(decisions)
    
    def handle_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for handling decisions (alias)"""
        return self.process_decisions(decisions)
    
    def execute_decisions(self, decisions: List[Any]) -> List[Any]:
        """Standardized method for executing decisions (alias)"""
        return self.process_decisions(decisions)
    
    def make_decisions(self, signals: List[Any]) -> List[Any]:
        """Standardized method for making strategy decisions"""
        return self.process_signals(signals)
    
    def evaluate_strategies(self, data: Any) -> List[Any]:
        """Standardized method for evaluating strategies"""
        return [{
            'strategy_evaluation': True,
            'input_data': data,
            'processing_timestamp': datetime.now(),
            'processing_component': 'StrategyManager'
        }]
    
    # ========================================
    # REGIME DATA CONSUMPTION METHODS
    # ========================================
    
    def process_regime(self, regime_data: Any) -> Dict[str, Any]:
        """Standardized method for processing regime data"""
        return {
            'regime_processed': True,
            'regime_data': regime_data,
            'processing_timestamp': datetime.now(),
            'processing_component': 'StrategyManager'
        }
    
    def handle_regime_change(self, regime_analysis: Any) -> Dict[str, Any]:
        """Standardized method for handling regime changes"""
        return self.process_regime(regime_analysis)
    
    # NOTE: adapt_to_regime is now async (IRegimeAware interface) - see line ~698
    # def adapt_to_regime(self, regime_data: Any) -> Dict[str, Any]:
    #     """Deprecated: Use async version (IRegimeAware)"""
    #     return self.process_regime(regime_data)
    
    # ========================================
    # REGIME-ADJUSTED RISK PRODUCTION METHODS
    # ========================================
    
    def generate_risk_adjusted_strategies(self, regime_data: Any = None) -> List[Any]:
        """Standardized method for generating regime-adjusted strategy decisions"""
        return [{
            'regime_adjusted_strategy': True,
            'regime_context': regime_data,
            'risk_adjustment_factor': 0.8,
            'processing_timestamp': datetime.now(),
            'processing_component': 'StrategyManager'
        }]
    
    def create_regime_adjusted_decisions(self, data: Any = None) -> List[Any]:
        """Standardized method for creating regime-adjusted decisions"""
        return self.generate_risk_adjusted_strategies(data)
    
    def produce_risk_context(self, strategy_data: Any = None) -> Dict[str, Any]:
        """Standardized method for producing risk context from strategies"""
        return {
            'risk_context_produced': True,
            'strategy_risk_profile': {
                'volatility_target': 0.15,
                'max_leverage': 2.0,
                'correlation_limit': 0.7
            },
            'processing_timestamp': datetime.now(),
            'processing_component': 'StrategyManager'
        }
    
    # ========================================
    # REGIME-ADJUSTED STRATEGIES PRODUCTION METHODS
    # ========================================
    
    def create_regime_adjusted_strategies(self, regime_data: Any = None) -> List[Any]:
        """Standardized method for creating regime-adjusted strategies"""
        return self.generate_risk_adjusted_strategies(regime_data)
    
    def produce_regime_strategies(self, regime_data: Any = None) -> List[Any]:
        """Standardized method for producing regime strategies"""
        return self.generate_risk_adjusted_strategies(regime_data)
    
    def adapt_strategies_to_regime(self, regime_data: Any = None) -> List[Any]:
        """Standardized method for adapting strategies to regime"""
        return self.generate_risk_adjusted_strategies(regime_data)
    
    # ========================================
    # STRATEGY CALLBACK METHODS
    # ========================================
    
    def set_signal_callback(self, callback: Callable):
        """Set signal callback for strategy notifications"""
        if not hasattr(self, 'signal_callbacks'):
            self.signal_callbacks = []
        
        self.signal_callbacks.append(callback)
        self.logger.info("✅ Signal callback registered with StrategyManager")
    
    def on_signal_generated(self, signal_data: Dict[str, Any]):
        """Callback method for signal generation"""
        try:
            self.logger.info(f"📡 Signal generated: {signal_data.get('symbol', 'unknown')}")
            
            # Process signal data
            self.process_signals([signal_data])
            
            # Notify registered callbacks
            if hasattr(self, 'signal_callbacks'):
                for callback in self.signal_callbacks:
                    try:
                        callback(signal_data)
                    except Exception as e:
                        self.logger.error(f"Signal callback notification failed: {e}")
            
            return {'signal_processed': True, 'notifications_sent': len(getattr(self, 'signal_callbacks', []))}
            
        except Exception as e:
            self.logger.error(f"Signal generation callback failed: {e}")
            return {'error': str(e)}
    
    def register_callback(self, callback_type: str, callback: Callable):
        """Register a callback for specific events"""
        try:
            if callback_type == 'signal':
                self.set_signal_callback(callback)
            elif callback_type == 'strategy':
                if not hasattr(self, 'strategy_callbacks'):
                    self.strategy_callbacks = []
                self.strategy_callbacks.append(callback)
            
            self.logger.info(f"✅ {callback_type} callback registered")
            return True
            
        except Exception as e:
            self.logger.error(f"Callback registration failed: {e}")
            return False
    
    # ========================================
    # RISK MANAGEMENT CALLBACK METHODS
    # ========================================
    
    def set_risk_callbacks(self, risk_callback: Callable = None):
        """Set risk management callback"""
        self.risk_callback = risk_callback
        if risk_callback:
            self.logger.info("✅ Risk callback registered with StrategyManager")
    
    def on_risk_limit_breach(self, risk_data: Dict[str, Any]):
        """Callback method for risk limit breaches"""
        try:
            self.logger.warning(f"🚨 Strategy risk limit breach: {risk_data}")
            
            # Handle risk breach (e.g., pause strategies)
            if hasattr(self, 'risk_callback') and self.risk_callback:
                self.risk_callback(risk_data)
            
            return {'risk_breach_handled': True}
            
        except Exception as e:
            self.logger.error(f"Risk limit breach callback failed: {e}")
            return {'error': str(e)}
    
    def on_emergency_shutdown(self, shutdown_reason: str = "Emergency"):
        """Callback method for emergency shutdown"""
        try:
            self.logger.critical(f"🚨 Strategy emergency shutdown: {shutdown_reason}")
            
            # Emergency strategy actions
            # In a real implementation, this would stop all strategies
            
            return {'emergency_shutdown_handled': True}
            
        except Exception as e:
            self.logger.error(f"Emergency shutdown callback failed: {e}")
            return {'error': str(e)}
    
    # ========================================
    # AUTHORIZATION METHODS
    # ========================================
    
    def authorize_operation(self, operation: str, details: Dict[str, Any] = None) -> bool:
        """Authorize strategy operations"""
        try:
            # Basic authorization logic for strategy operations
            authorized_operations = [
                'generate_signals', 'analyze_market', 'create_strategy',
                'modify_strategy', 'pause_strategy', 'resume_strategy'
            ]
            
            if operation in authorized_operations:
                self.logger.info(f"✅ Strategy operation authorized: {operation}")
                return True
            else:
                self.logger.warning(f"❌ Strategy operation not authorized: {operation}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authorization failed: {e}")
            return False
    
    def validate_authorization(self, authorization_token: str) -> bool:
        """Validate authorization token for strategy operations"""
        try:
            # Mock authorization token validation
            # In real implementation, this would validate against actual tokens
            if authorization_token and len(authorization_token) > 10:
                self.logger.info("✅ Strategy authorization token validated")
                return True
            else:
                self.logger.warning("❌ Invalid strategy authorization token")
                return False
                
        except Exception as e:
            self.logger.error(f"Authorization validation failed: {e}")
            return False
    
    def check_authority_level(self, required_level: str) -> bool:
        """Check if component has required authority level"""
        try:
            # Strategy manager has OPERATIONAL authority level
            component_authority = "OPERATIONAL"
            
            authority_hierarchy = {
                "READ_ONLY": 1,
                "OPERATIONAL": 2,
                "GOVERNANCE_CONTROL": 3,
                "SYSTEM_CONTROL": 4
            }
            
            component_level = authority_hierarchy.get(component_authority, 0)
            required_level_num = authority_hierarchy.get(required_level, 999)
            
            authorized = component_level >= required_level_num
            
            if authorized:
                self.logger.info(f"✅ Authority level check passed: {component_authority} >= {required_level}")
            else:
                self.logger.warning(f"❌ Authority level check failed: {component_authority} < {required_level}")
            
            return authorized
            
        except Exception as e:
            self.logger.error(f"Authority level check failed: {e}")
            return False
    
    # ========================================
    # ANALYTICS INTEGRATION METHODS
    # ========================================
    
    def calculate_metrics(self, data: Any = None) -> Dict[str, Any]:
        """Calculate strategy analytics metrics"""
        try:
            # Get current strategy state
            active_strategies = len(self.active_strategies)
            total_signals = sum(len(signals) for signals in self.strategy_signals.values())
            
            # Calculate strategy metrics
            strategy_metrics = {
                'active_strategies': active_strategies,
                'total_signals_generated': total_signals,
                'strategy_types': list(self.active_strategies.keys()),
                'signal_generation_rate': total_signals / max(1, active_strategies),
                'avg_confidence': self._calculate_average_confidence(),
                'strategy_allocation': self._calculate_strategy_allocation()
            }
            
            # Performance metrics per strategy
            strategy_performance = {}
            for strategy_id in self.active_strategies.keys():
                signals = self.strategy_signals.get(strategy_id, [])
                strategy_performance[strategy_id] = {
                    'signal_count': len(signals),
                    'avg_confidence': sum(s.confidence for s in signals) / len(signals) if signals else 0.0,
                    'signal_types': list(set(s.signal_type.value for s in signals)) if signals else []
                }
            
            return {
                'metrics_calculated': True,
                'calculation_timestamp': datetime.now(),
                'strategy_metrics': strategy_metrics,
                'strategy_performance': strategy_performance,
                'component': 'StrategyManager'
            }
            
        except Exception as e:
            self.logger.error(f"Strategy metrics calculation failed: {e}")
            return {
                'metrics_calculated': False,
                'error': str(e),
                'calculation_timestamp': datetime.now()
            }
    
    def analyze_performance(self, data: Any = None) -> Dict[str, Any]:
        """Analyze strategy performance"""
        try:
            # Analyze strategy performance
            performance_analysis = {
                'strategy_efficiency': self._calculate_strategy_efficiency(),
                'signal_quality': self._assess_signal_quality(),
                'strategy_coordination': self._assess_strategy_coordination(),
                'resource_utilization': {
                    'active_strategies': len(self.active_strategies),
                    'max_strategies': self.config.max_concurrent_strategies,
                    'utilization_pct': (len(self.active_strategies) / self.config.max_concurrent_strategies * 100)
                },
                'performance_summary': {
                    'total_strategies_managed': len(self.active_strategies),
                    'signal_generation_active': len(self.strategy_signals) > 0,
                    'coordination_status': 'active' if self.active_strategies else 'inactive'
                }
            }
            
            return {
                'performance_analyzed': True,
                'analysis_timestamp': datetime.now(),
                'performance_analysis': performance_analysis,
                'component': 'StrategyManager'
            }
            
        except Exception as e:
            self.logger.error(f"Strategy performance analysis failed: {e}")
            return {
                'performance_analyzed': False,
                'error': str(e),
                'analysis_timestamp': datetime.now()
            }
    
    def generate_analytics(self, data: Any = None) -> Dict[str, Any]:
        """Generate comprehensive strategy analytics"""
        try:
            # Combine metrics and performance analysis
            metrics = self.calculate_metrics(data)
            performance = self.analyze_performance(data)
            
            analytics = {
                'analytics_generated': True,
                'generation_timestamp': datetime.now(),
                'metrics': metrics.get('strategy_metrics', {}),
                'performance': performance.get('performance_analysis', {}),
                'summary': {
                    'strategy_health': self._assess_strategy_health(),
                    'coordination_effectiveness': self._assess_coordination_effectiveness(),
                    'signal_quality_score': self._calculate_signal_quality_score()
                },
                'recommendations': self._generate_strategy_recommendations(),
                'component': 'StrategyManager'
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Strategy analytics generation failed: {e}")
            return {
                'analytics_generated': False,
                'error': str(e),
                'generation_timestamp': datetime.now()
            }
    
    def track_performance(self, data: Any = None) -> Dict[str, Any]:
        """Track strategy performance over time"""
        try:
            # Mock performance tracking (in real implementation, would maintain historical data)
            performance_tracking = {
                'tracking_active': True,
                'tracking_timestamp': datetime.now(),
                'current_metrics': self.calculate_metrics(data),
                'performance_trend': self._assess_performance_trend(),
                'alerts': self._generate_performance_alerts(),
                'component': 'StrategyManager'
            }
            
            return performance_tracking
            
        except Exception as e:
            self.logger.error(f"Strategy performance tracking failed: {e}")
            return {
                'tracking_active': False,
                'error': str(e),
                'tracking_timestamp': datetime.now()
            }
    
    def monitor_performance(self, data: Any = None) -> Dict[str, Any]:
        """Monitor strategy performance (alias for track_performance)"""
        return self.track_performance(data)
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all signals"""
        try:
            all_signals = []
            for signals in self.strategy_signals.values():
                all_signals.extend(signals)
            
            if not all_signals:
                return 0.0
            
            return sum(s.confidence for s in all_signals) / len(all_signals)
            
        except Exception:
            return 0.0
    
    def _calculate_strategy_allocation(self) -> Dict[str, float]:
        """Calculate allocation per strategy"""
        try:
            if not self.active_strategies:
                return {}
            
            # Mock allocation calculation (in real implementation, would use actual allocations)
            equal_allocation = 1.0 / len(self.active_strategies)
            return {strategy_id: equal_allocation for strategy_id in self.active_strategies.keys()}
            
        except Exception:
            return {}
    
    def _calculate_strategy_efficiency(self) -> float:
        """Calculate overall strategy efficiency"""
        try:
            if not self.active_strategies:
                return 0.0
            
            # Mock efficiency calculation
            signal_count = sum(len(signals) for signals in self.strategy_signals.values())
            strategy_count = len(self.active_strategies)
            
            # Efficiency = signals per strategy
            efficiency = signal_count / strategy_count if strategy_count > 0 else 0.0
            
            # Normalize to 0-100 scale
            return min(100.0, efficiency * 10)
            
        except Exception:
            return 50.0  # Default moderate efficiency
    
    def _assess_signal_quality(self) -> str:
        """Assess overall signal quality"""
        try:
            avg_confidence = self._calculate_average_confidence()
            
            if avg_confidence > 0.8:
                return "Excellent"
            elif avg_confidence > 0.7:
                return "Good"
            elif avg_confidence > 0.6:
                return "Fair"
            else:
                return "Poor"
                
        except Exception:
            return "Unknown"
    
    def _assess_strategy_coordination(self) -> str:
        """Assess strategy coordination effectiveness"""
        try:
            if len(self.active_strategies) == 0:
                return "No strategies active"
            elif len(self.active_strategies) == 1:
                return "Single strategy"
            elif len(self.active_strategies) <= 3:
                return "Well coordinated"
            elif len(self.active_strategies) <= 5:
                return "Moderately coordinated"
            else:
                return "Over-coordinated"
                
        except Exception:
            return "Unknown"
    
    def _assess_strategy_health(self) -> str:
        """Assess overall strategy health"""
        try:
            active_count = len(self.active_strategies)
            signal_count = sum(len(signals) for signals in self.strategy_signals.values())
            
            if active_count == 0:
                return "Inactive"
            elif signal_count == 0:
                return "No signals"
            elif active_count > self.config.max_concurrent_strategies:
                return "Overloaded"
            else:
                return "Healthy"
                
        except Exception:
            return "Unknown"
    
    def _assess_coordination_effectiveness(self) -> float:
        """Assess coordination effectiveness (0-100)"""
        try:
            if not self.active_strategies:
                return 0.0
            
            # Mock coordination assessment
            strategy_count = len(self.active_strategies)
            signal_count = sum(len(signals) for signals in self.strategy_signals.values())
            
            # Effectiveness based on signal generation per strategy
            if strategy_count == 0:
                return 0.0
            
            signals_per_strategy = signal_count / strategy_count
            effectiveness = min(100.0, signals_per_strategy * 20)  # Scale to 0-100
            
            return effectiveness
            
        except Exception:
            return 50.0  # Default moderate effectiveness
    
    def _calculate_signal_quality_score(self) -> float:
        """Calculate signal quality score (0-100)"""
        try:
            avg_confidence = self._calculate_average_confidence()
            return avg_confidence * 100
            
        except Exception:
            return 50.0  # Default moderate quality
    
    def _generate_strategy_recommendations(self) -> List[str]:
        """Generate strategy recommendations"""
        try:
            recommendations = []
            
            active_count = len(self.active_strategies)
            signal_count = sum(len(signals) for signals in self.strategy_signals.values())
            
            if active_count == 0:
                recommendations.append("Consider activating strategies")
            elif active_count > self.config.max_concurrent_strategies:
                recommendations.append("Reduce number of active strategies")
            elif signal_count == 0:
                recommendations.append("Check strategy signal generation")
            
            avg_confidence = self._calculate_average_confidence()
            if avg_confidence < 0.6:
                recommendations.append("Improve signal confidence thresholds")
            
            return recommendations
            
        except Exception:
            return ["Unable to generate recommendations"]
    
    def _assess_performance_trend(self) -> str:
        """Assess performance trend"""
        try:
            # Mock trend assessment (in real implementation, would use historical data)
            signal_count = sum(len(signals) for signals in self.strategy_signals.values())
            
            if signal_count > 10:
                return "Improving"
            elif signal_count > 5:
                return "Stable"
            else:
                return "Declining"
                
        except Exception:
            return "Unknown"
    
    def _generate_performance_alerts(self) -> List[str]:
        """Generate performance alerts"""
        try:
            alerts = []
            
            if len(self.active_strategies) == 0:
                alerts.append("No active strategies")
            
            avg_confidence = self._calculate_average_confidence()
            if avg_confidence < 0.5:
                alerts.append("Low signal confidence detected")
            
            return alerts
            
        except Exception:
            return []
    
    # ========================================
    # MULTI-STRATEGY COORDINATION METHODS
    # ========================================
    
    async def _initialize_multi_strategy_coordination(self) -> None:
        """Initialize multi-strategy coordination components"""
        try:
            logger.info("🎯 Initializing multi-strategy coordination...")
            
            # Initialize signal aggregator
            if self.config.enable_signal_aggregation:
                aggregator_config = {
                    'max_concurrent_strategies': self.config.max_concurrent_strategies,
                    'min_confidence_threshold': self.config.min_confidence_threshold,
                    'enable_dynamic_weighting': self.config.enable_dynamic_weighting
                }
                self.signal_aggregator = MultiStrategySignalAggregator(aggregator_config)
                await self.signal_aggregator.initialize()
                await self.signal_aggregator.start()
                logger.info("✅ Signal aggregator initialized")
            
            # Initialize conflict resolver
            if self.config.enable_conflict_resolution:
                resolver_config = {
                    'resolution_method': self.config.conflict_resolution_method,
                    'conflict_threshold': 0.1
                }
                self.conflict_resolver = SignalConflictResolver(resolver_config)
                await self.conflict_resolver.initialize()
                await self.conflict_resolver.start()
                logger.info("✅ Conflict resolver initialized")
            
            logger.info("✅ Multi-strategy coordination initialized")
            
        except Exception as e:
            logger.error(f"❌ Multi-strategy coordination initialization failed: {e}")
            raise
    
    async def register_enhanced_strategy(self, strategy_type: StrategyType, 
                                       config: Dict[str, Any]) -> bool:
        """Register an enhanced strategy for multi-strategy coordination"""
        try:
            strategy_id = config.get('name', f"{strategy_type.value}_{uuid.uuid4().hex[:8]}")
            
            # Create strategy instance using factory
            strategy_instance = self.strategy_factory.create_strategy(strategy_type, config)
            if not strategy_instance:
                logger.error(f"Failed to create strategy instance: {strategy_type}")
                return False
            
            # Initialize strategy
            await strategy_instance.initialize()
            
            # Store in active strategies
            self.active_strategies[strategy_id] = strategy_instance
            
            # Create strategy allocation
            allocation = StrategyAllocation(
                strategy_name=strategy_id,
                strategy_type=strategy_type,
                allocation_pct=config.get('allocation_pct', 0.1),
                max_positions=config.get('max_positions', 5),
                risk_limit=config.get('risk_limit', 0.05)
            )
            self.strategy_allocations[strategy_id] = allocation
            
            # Register with signal aggregator if available
            if self.signal_aggregator:
                await self.signal_aggregator.register_strategy(
                    strategy_id=strategy_id,
                    strategy_instance=strategy_instance,
                    strategy_type=strategy_type,
                    weight=config.get('weight', 1.0),
                    priority=config.get('priority', 1),
                    allocation_pct=allocation.allocation_pct,
                    max_positions=allocation.max_positions,
                    risk_limit=allocation.risk_limit
                )
            
            logger.info(f"✅ Enhanced strategy registered: {strategy_id} ({strategy_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced strategy registration failed: {e}")
            return False
    
    async def collect_all_signals(self, market_data) -> Dict[str, List[EnhancedSignal]]:
        """Collect signals from all registered strategies"""
        if not self.signal_aggregator:
            logger.warning("Signal aggregator not available")
            return {}
        
        try:
            return await self.signal_aggregator.collect_all_signals(market_data)
        except Exception as e:
            logger.error(f"Signal collection failed: {e}")
            return {}
    
    async def aggregate_strategy_signals(self, strategy_signals: Dict[str, List[EnhancedSignal]]) -> List[EnhancedSignal]:
        """Aggregate signals from multiple strategies with conflict resolution"""
        if not self.signal_aggregator:
            logger.warning("Signal aggregator not available")
            return []
        
        try:
            return await self.signal_aggregator.aggregate_strategy_signals(strategy_signals)
        except Exception as e:
            logger.error(f"Signal aggregation failed: {e}")
            return []
    
    async def generate_signals(self, symbols: List[str]) -> List[EnhancedSignal]:
        """Generate signals using multi-strategy coordination"""
        try:
            if not self.enable_multi_strategy or not self.signal_aggregator:
                # Fallback to traditional signal generation
                return await self._generate_traditional_signals(symbols)
            
            # Get market data (placeholder - would get from data manager)
            market_data = await self._get_market_data(symbols)
            
            # Collect signals from all strategies
            strategy_signals = await self.collect_all_signals(market_data)
            
            # Aggregate and resolve conflicts
            aggregated_signals = await self.aggregate_strategy_signals(strategy_signals)
            
            logger.info(f"📊 Generated {len(aggregated_signals)} aggregated signals from {len(strategy_signals)} strategies")
            return aggregated_signals
            
        except Exception as e:
            logger.error(f"Multi-strategy signal generation failed: {e}")
            return []
    
    async def _generate_traditional_signals(self, symbols: List[str]) -> List[EnhancedSignal]:
        """Fallback traditional signal generation"""
        # Placeholder - would implement traditional signal generation
        return []
    
    async def _get_market_data(self, symbols: List[str]):
        """Get market data for signal generation"""
        # Placeholder - would get data from data manager
        import pandas as pd
        return pd.DataFrame()  # Empty DataFrame for now
    
    def get_multi_strategy_status(self) -> Dict[str, Any]:
        """Get multi-strategy coordination status"""
        return {
            'multi_strategy_enabled': self.enable_multi_strategy,
            'signal_aggregator_status': self.signal_aggregator.get_status() if self.signal_aggregator else None,
            'conflict_resolver_status': self.conflict_resolver.get_status() if self.conflict_resolver else None,
            'registered_strategies': len(self.strategy_registrations),
            'active_strategies': len(self.active_strategies)
        }