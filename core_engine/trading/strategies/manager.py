#!/usr/bin/env python3
"""
Strategy Manager - Core Engine (WHAT Component)
===============================================

Clean implementation of the strategy manager for core_engine.
This component determines WHAT trades should be made.

Architecture Compliance (Tier-1 Rules):
- Rule 1: System Architecture - Layer 4 (Analytics & Strategy)
- Rule 2: Data Pipeline - Phase 5 (Strategy Logic)
- Rule 3: Risk & Compliance Governance - Phase 6 (Multi-Strategy Coordination)
  - Signal aggregation across strategies
  - Conflict resolution for same-symbol signals
  - Strategy weighting and correlation analysis
  - Submits TradingDecisionRequest to RiskManager (Phase 7)

Key Responsibilities:
- Analyzes market data and conditions
- Determines which strategies to activate
- Generates trading signals and recommendations
- Aggregates and resolves multi-strategy conflicts
- Submits trade requests to Risk Manager for authorization

Migration: December 2025 - Former Rule 5 content absorbed into Rule 3.

Author: StatArb_Gemini Core Engine Migration
Version: 2.0.0 (Rules Migration December 2025)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd

# Use internal core_engine types for independence
from ...type_definitions.strategy import StrategyType, StrategyConfig
from ...exceptions import ConfigurationRequiredError

# Import enhanced strategy implementations
from .implementations import (
    EnhancedMomentumStrategy, MomentumConfig,
    EnhancedMeanReversionStrategy, MeanReversionConfig,
    EnhancedStatisticalArbitrageStrategy,
    EnhancedFactorStrategy, FactorConfig,
    EnhancedMultiAssetStrategy, MultiAssetConfig,
    EnhancedPairsTradingStrategy, PairsConfig,
    EnhancedVolatilityStrategy, VolatilityConfig,
    EnhancedArbitrageStrategy, ArbitrageConfig
)

# Import SES Pairs Trading Strategy (advanced implementation)
from .implementations.pairs_trading import SESPairsTradingStrategy

# Import StatisticalArbitrageConfig separately
from .implementations.statistical_arbitrage import StatisticalArbitrageConfig

# Import base strategy and registry
from .base_strategy_enhanced import EnhancedBaseStrategy
from .strategy_registry import StrategyRegistry
from .strategy_validator import EnhancedStrategyValidator, Rule7ComplianceError

# Import multi-strategy coordination components
from .multi_strategy_coordinator import (
    MultiStrategySignalAggregator, SignalConflictResolver,
    EnhancedSignal, StrategyRegistration
)

# Import ISystemComponent and IRegimeAware for orchestrator integration (Rule 1, Rule 2)
from ...system.interfaces import ISystemComponent, IRegimeAware

# Import TradingDecisionRequest for Phase 6→7 conversion (Rule 4)
from ...system.central_risk_manager import TradingDecisionRequest, TradingDecisionType

# Import ProcessingPipelineOrchestrator (Rule 3 - Phase 3 Integration)
from ...processing.pipeline_orchestrator import ProcessingPipelineOrchestrator

# Hybrid recombination config and combiner
from core_engine.config import HybridRecombinationConfig
from core_engine.processing.signals.combiners import SignalCombiner

# Import canonical SignalType and SignalStrength from type_definitions
from ...type_definitions.strategy import SignalType, SignalStrength

logger = logging.getLogger(__name__)

# SignalType imported from type_definitions.strategy (canonical source)
# SignalStrength imported from type_definitions.strategy (canonical source)

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

    # Position sizing fields (CRITICAL for percentage-based sizing)
    target_weight: Optional[float] = None  # Target portfolio weight (0.05 = 5%)
    quantity_type: str = "ABSOLUTE"  # "PERCENTAGE" or "ABSOLUTE"

    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: Optional[timedelta] = None
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

    # Phase 3: Pipeline integration settings (Rule 3)
    enable_pipeline_integration: bool = True  # Use ProcessingPipelineOrchestrator
    pipeline_config: Optional[Any] = None      # Pipeline configuration

    # Hybrid MOM/MR recombination (configure via YAML only)
    hybrid_recombination: Optional[HybridRecombinationConfig] = None

class EnhancedStrategyFactory:
    """Factory for creating enhanced strategy instances"""

    # Strategy class mapping
    STRATEGY_CLASSES = {
        StrategyType.MOMENTUM: EnhancedMomentumStrategy,
        StrategyType.MEAN_REVERSION: EnhancedMeanReversionStrategy,
        StrategyType.STATISTICAL_ARBITRAGE: EnhancedStatisticalArbitrageStrategy,
        StrategyType.FACTOR: EnhancedFactorStrategy,
        StrategyType.MULTI_ASSET: EnhancedMultiAssetStrategy,
        StrategyType.PAIRS_TRADING: EnhancedPairsTradingStrategy,
        StrategyType.SES_PAIRS_TRADING: SESPairsTradingStrategy,  # Advanced SES-based pairs
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
        StrategyType.PAIRS_TRADING: PairsConfig,
        StrategyType.SES_PAIRS_TRADING: PairsConfig,  # SES uses same config as pairs
        StrategyType.VOLATILITY: VolatilityConfig,
        StrategyType.ARBITRAGE: ArbitrageConfig
    }

    @classmethod
    def create_strategy(cls, strategy_type: StrategyType, config: Dict[str, Any]) -> Optional[EnhancedBaseStrategy]:
        """Create enhanced strategy instance"""
        try:
            # Select strategy class based on type
            strategy_class = cls.STRATEGY_CLASSES.get(strategy_type)
            
            if not strategy_class:
                logger.error(f"No enhanced strategy class found for type: {strategy_type}")
                raise ConfigurationRequiredError(f"Unknown strategy type: {strategy_type}")

            # Create configuration object
            config_class = cls.CONFIG_CLASSES.get(strategy_type)
            if config_class:
                # Convert dict config to proper config object
                strategy_config = cls._create_config_object(config_class, config)
            else:
                # Use basic StrategyConfig for strategies without specific config
                strategy_config = StrategyConfig(
                    name=config.get('name', f'{strategy_type.value}_strategy'),
                    strategy_type=strategy_type,
                    **{k: v for k, v in config.items() if k not in ['name', 'type', 'strategy_type']}
                )

            # Create strategy instance
            strategy_instance = strategy_class(strategy_config)

            logger.info(f"✅ Created enhanced strategy: {strategy_type.value} - {config.get('name')}")
            return strategy_instance

        except ConfigurationRequiredError as config_error:
            # Configuration validation failed (e.g., invalid lookback)
            logger.error(
                f"❌ Failed to create enhanced strategy {strategy_type}: {config_error}. "
                f"Strategy config: {config}"
            )
            return None
        except Exception as e:
            logger.exception(f"❌ Unexpected error creating enhanced strategy {strategy_type}: {e}")
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
            logger.error(f"Failed to create config object: {e}")
            raise ConfigurationRequiredError(f"Cannot create strategy configuration: {e}") from e

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

    def __init__(self, config: Dict[str, Any], data_config: Optional[Any] = None):
        config = config.copy() if config else {}
        hybrid_payload = config.pop("hybrid_recombination", None)
        if isinstance(hybrid_payload, dict):
            hybrid_cfg = HybridRecombinationConfig(**hybrid_payload)
        elif isinstance(hybrid_payload, HybridRecombinationConfig):
            hybrid_cfg = hybrid_payload
        else:
            hybrid_cfg = None
        self.config = StrategyManagerConfig(**config) if config else StrategyManagerConfig()
        self.config.hybrid_recombination = hybrid_cfg
        self.data_config = data_config  # Store data config for pipeline orchestrator
        self.component_id = f"strategy_manager_{uuid.uuid4().hex[:8]}"

        # Component references (set by Risk Manager)
        self.risk_manager: Optional[Any] = None
        self.data_manager: Optional[Any] = None
        self.regime_engine: Optional[Any] = None

        # Enhanced strategy integration
        self.strategy_factory = EnhancedStrategyFactory()
        self.strategy_registry: Optional[StrategyRegistry] = None
        self._rule7_validator = EnhancedStrategyValidator()

        # Phase 3: Pipeline orchestrator integration (Rule 3)
        self.pipeline_orchestrator: Optional[ProcessingPipelineOrchestrator] = None
        self.pipeline_enabled = self.config.enable_pipeline_integration

        if self.pipeline_enabled:
            logger.info("✅ Pipeline integration enabled (Rule 3 - Phase 3)")
        else:
            logger.warning("⚠️  Pipeline integration disabled, using legacy mode")

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

        # Hybrid recombination
        self.hybrid_config = self.config.hybrid_recombination or HybridRecombinationConfig(
            enable_hybrid_recombination=False
        )
        self.signal_combiner = SignalCombiner()
        self._hybrid_weight_cache: Dict[str, Dict[str, float]] = {}
        self._hybrid_strength_history: Dict[str, List[Tuple[float, float]]] = {}

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

            # Strategies must be registered manually - no default strategies
            logger.info("📊 Manual strategy registration mode - no default strategies")

            # Initialize strategy performance tracking
            await self._initialize_performance_tracking()

            # Initialize multi-strategy coordination if enabled
            if self.enable_multi_strategy:
                await self._initialize_multi_strategy_coordination()

                # CRITICAL FIX: Sync already-registered strategies to signal aggregator
                # (strategies may have been registered before signal_aggregator existed)
                if self.signal_aggregator and self.active_strategies:
                    logger.info(f"📊 Syncing {len(self.active_strategies)} pre-registered strategies to signal aggregator...")
                    for strategy_name, strategy_instance in self.active_strategies.items():
                        allocation = self.strategy_allocations.get(strategy_name)
                        if allocation:
                            try:
                                await self.signal_aggregator.register_strategy(
                                    strategy_id=strategy_name,
                                    strategy_instance=strategy_instance,
                                    strategy_type=allocation.strategy_type,
                                    weight=1.0,
                                    priority=1,
                                    allocation_pct=allocation.allocation_pct,
                                    max_positions=allocation.max_positions,
                                    risk_limit=allocation.risk_limit
                                )
                                logger.info(f"   ✅ Synced: {strategy_name}")
                            except Exception as e:
                                logger.warning(f"   ⚠️ Failed to sync {strategy_name}: {e}")

            # Phase 3: Initialize pipeline orchestrator (Rule 3)
            if self.pipeline_enabled:
                try:
                    logger.info("🔧 Initializing ProcessingPipelineOrchestrator (Rule 3)...")
                    self.pipeline_orchestrator = ProcessingPipelineOrchestrator(
                        data_config=self.data_config if self.data_config else (
                            self.config.pipeline_config if self.config.pipeline_config else None
                        ),
                        data_manager=self.data_manager
                    )
                    await self.pipeline_orchestrator.initialize()
                    await self.pipeline_orchestrator.start()

                    # Inject regime engine into pipeline
                    if self.regime_engine:
                        self.pipeline_orchestrator.set_regime_engine(self.regime_engine)
                        logger.debug("✅ Regime engine propagated to pipeline")

                    logger.info("✅ Pipeline orchestrator initialized and operational")
                except Exception as e:
                    logger.error(f"❌ Pipeline orchestrator initialization failed: {e}")
                    self.pipeline_enabled = False

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

            # CRITICAL FIX: Register with signal aggregator for multi-strategy coordination
            if self.signal_aggregator:
                try:
                    await self.signal_aggregator.register_strategy(
                        strategy_id=strategy_name,
                        strategy_instance=strategy_instance,
                        strategy_type=strategy_type,
                        weight=config.get('weight', 1.0),
                        priority=config.get('priority', 1),
                        allocation_pct=allocation.allocation_pct,
                        max_positions=allocation.max_positions,
                        risk_limit=allocation.risk_limit
                    )
                    logger.info(f"✅ Strategy registered with signal aggregator: {strategy_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Signal aggregator registration failed for {strategy_name}: {e}")

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

            # Phase 3: Stop pipeline orchestrator
            if self.pipeline_orchestrator:
                await self.pipeline_orchestrator.stop()
                logger.debug("✅ Pipeline orchestrator stopped")

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

        # Phase 3: Propagate regime engine to pipeline (Rule 2 + Rule 3)
        if self.pipeline_orchestrator and hasattr(self.pipeline_orchestrator, 'set_regime_engine'):
            self.pipeline_orchestrator.set_regime_engine(regime_engine)
            logger.debug("✅ Regime engine propagated to pipeline orchestrator")

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
            strategy_name = strategy_config.get('name', 'unnamed_strategy')
            # Support both 'type' and 'strategy_type' (alias)
            strategy_type_str = strategy_config.get('type') or strategy_config.get('strategy_type')
            if not strategy_type_str:
                raise KeyError("'type' or 'strategy_type' must be specified in strategy config")
            
            strategy_type = StrategyType(strategy_type_str)

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

    async def generate_signals_with_pipeline(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        timeframe: str = "1min",
        current_positions: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[TradingSignal]:
        """
        Generate trading signals using pipeline orchestrator (Rule 3 - Phase 3)

        **KEY CHANGE:** Process data through pipeline ONCE, then all strategies
        consume the SAME enriched data.

        **ARCHITECTURAL NOTE (Rule 4 - Approach 3: Continuous Signal Stream):**
        Strategies are STATELESS and generate signals based ONLY on market state.
        They do NOT receive current_positions for signal generation.

        Why this design?
        - ✅ Strategies focus on alpha logic (WHAT to trade based on market conditions)
        - ✅ Risk Manager handles position awareness (WHETHER to execute)
        - ✅ Risk Manager filters redundant signals (e.g., BUY when already long)
        - ✅ Clean separation of concerns (Strategy=WHAT, RiskManager=WHETHER)
        - ✅ Stateless strategies are easier to test and backtest

        Position awareness flow:
        1. Strategy generates signal: "Market is oversold" → BUY signal
        2. Strategy generates signal: "Market at mean" → CLOSE signal
        3. StrategyManager aggregates signals (this method)
        4. Risk Manager checks positions:
           - BUY signal + already have position → REJECT (redundant)
           - CLOSE signal + no position → REJECT (redundant)
           - BUY signal + no position → AUTHORIZE (valid)
           - CLOSE signal + have position → AUTHORIZE (valid)

        current_positions parameter:
        - Reserved for filtering/aggregation logic in StrategyManager
        - NOT passed to strategy.generate_signals() per Approach 3 design
        - Risk Manager performs final position-aware filtering

        See: docs/08_analysis/WHY_STRATEGY_TRACKS_POSITIONS.md (Approach 3)

        Args:
            symbols: List of symbols to process
            start_time: Start time for data
            end_time: End time for data
            timeframe: Data timeframe (default: 1min)
            current_positions: Current positions for filtering/aggregation

        Returns:
            List[TradingSignal]: Aggregated signals from all strategies
        """
        try:
            if not self.pipeline_enabled or not self.pipeline_orchestrator:
                logger.warning("Pipeline not available, falling back to legacy generate_signals")
                # Fallback to existing method
                return await self.generate_signals(symbols, market_data=None, current_positions=current_positions)

            # PHASE 1-4: Process data through pipeline ONCE
            logger.info(f"📊 Processing {len(symbols)} symbols through pipeline (Rule 3)")
            enriched_data = await self.pipeline_orchestrator.process_market_data(
                symbols=symbols,
                start_time=start_time,
                end_time=end_time,
                timeframe=timeframe
            )

            if not enriched_data:
                logger.warning("No enriched data from pipeline")
                return []

            logger.info(f"✅ Pipeline processing complete: {len(enriched_data)} symbols enriched")

            # Convert EnrichedMarketData to strategy format
            enriched_dataframes = {
                symbol: data.get_enriched_dataframe()
                for symbol, data in enriched_data.items()
            }

            # PHASE 5: All strategies consume SAME enriched data
            all_signals = []

            # Update market context
            await self._update_market_context()
            regime_info = await self._get_current_regime_info()

            # Generate signals from each active strategy
            for strategy_name, strategy in self.active_strategies.items():
                allocation = self.strategy_allocations.get(strategy_name)
                if not allocation or not allocation.active:
                    continue

                try:
                    logger.debug(f"📡 Generating signals from {strategy_name} with enriched data")

                    # Call strategy with enriched data
                    if isinstance(strategy, EnhancedBaseStrategy):
                        # Strategy receives enriched DataFrames (OHLCV + indicators + features)
                        raw_signals = await strategy.generate_signals(enriched_dataframes)

                        logger.info(f"✅ {strategy_name}: generated {len(raw_signals)} signals from enriched data")

                        # Convert to TradingSignal objects
                        strategy_type = allocation.strategy_type
                        converted_count = 0
                        for raw_signal in raw_signals:
                            try:
                                # Convert SignalType enum to string for comparison
                                signal_type_str = raw_signal.signal_type.value if hasattr(raw_signal.signal_type, 'value') else str(raw_signal.signal_type).lower()

                                # ✅ CRITICAL FIX: Extract target_weight and quantity_type
                                # Strategies use target_weight (percentage) instead of quantity (shares)
                                target_quantity = getattr(raw_signal, 'target_quantity', None)
                                target_weight = getattr(raw_signal, 'target_weight', None)
                                quantity_type = getattr(raw_signal, 'quantity_type', 'ABSOLUTE')

                                # Determine quantity field based on type
                                if quantity_type == 'PERCENTAGE' and target_weight is not None:
                                    quantity = None  # Will be calculated by engine from target_weight
                                else:
                                    quantity = target_quantity if target_quantity is not None else getattr(raw_signal, 'quantity', None)

                                trading_signal = TradingSignal(
                                    signal_id=str(uuid.uuid4()),
                                    strategy_name=strategy_name,
                                    strategy_type=strategy_type,
                                    symbol=raw_signal.symbol,
                                    signal_type=SignalType(signal_type_str),
                                    strength=raw_signal.strength,
                                    confidence=getattr(raw_signal, 'confidence', 0.5),
                                    expected_return=getattr(raw_signal, 'expected_return', 0.0),
                                    risk_score=getattr(raw_signal, 'risk_score', 0.5),
                                    quantity=quantity,

                                    # ✅ CRITICAL FIX: Add position sizing fields
                                    target_weight=target_weight,
                                    quantity_type=quantity_type,

                                    target_price=getattr(raw_signal, 'target_price', None),
                                    stop_loss=getattr(raw_signal, 'stop_loss', None),
                                    take_profit=getattr(raw_signal, 'take_profit', None),
                                    time_horizon=None,
                                    metadata={
                                        'pipeline_processed': True,  # Mark as pipeline-processed
                                        'enriched_data': True,
                                        # ✅ Store in metadata for downstream access
                                        'target_weight': target_weight,
                                        'quantity_type': quantity_type,
                                        **getattr(raw_signal, 'additional_data', {})
                                    }
                                )
                                all_signals.append(trading_signal)
                                converted_count += 1
                                logger.debug(f"   ✅ Converted signal: {strategy_name} {raw_signal.symbol} {signal_type_str} (confidence: {trading_signal.confidence:.4f}, weight: {target_weight})")
                            except Exception as conv_error:
                                logger.error(f"   ❌ Failed to convert signal from {strategy_name}: {conv_error}")
                                logger.error(f"      Signal type: {type(raw_signal.signal_type)}, value: {raw_signal.signal_type}")
                                logger.error(f"      Signal attributes: {dir(raw_signal)}")
                                import traceback
                                logger.error(f"      Traceback: {traceback.format_exc()}")

                        logger.info(f"   📊 Converted {converted_count}/{len(raw_signals)} signals to TradingSignal objects")

                except Exception as e:
                    logger.error(f"❌ Signal generation failed for {strategy_name}: {e}")
                    continue

            # Enhanced filtering and aggregation (optional)
            filtered_signals = await self._filter_signals_enhanced(all_signals, regime_info, current_positions)
            if self.config.enable_signal_aggregation:
                aggregated_signals = await self._aggregate_signals_enhanced(filtered_signals, regime_info)
            else:
                aggregated_signals = filtered_signals

            # Store signals
            for signal in aggregated_signals:
                self.pending_signals[signal.signal_id] = signal
                self.aggregated_signals[signal.symbol] = signal

            # Notify subscribers
            for signal in aggregated_signals:
                for subscriber in self.subscribers:
                    await subscriber.on_signal_generated(signal)

            logger.info(f"📊 Raw signals: {len(all_signals)}, Filtered: {len(filtered_signals) if 'filtered_signals' in locals() else 0}, Aggregated: {len(aggregated_signals)}")
            logger.info(
                f"📊 Pipeline signal generation complete: "
                f"{len(aggregated_signals)} final signals from {len(all_signals)} raw signals "
                f"(regime: {regime_info.get('regime', 'unknown')})"
            )

            return aggregated_signals

        except Exception as e:
            logger.error(f"❌ Pipeline signal generation failed: {e}", exc_info=True)
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
                    # Rule 7 compliance (hard-fail)
                    try:
                        self._rule7_validator.enforce_rule7(strategy_instance)
                    except Rule7ComplianceError as e:
                        logger.error(str(e))
                        raise
                    # Initialize the enhanced strategy
                    await strategy_instance.initialize()
                    logger.info(f"✅ Enhanced strategy created and initialized: {config['name']}")
                    return strategy_instance
                else:
                    logger.error(f"❌ Failed to create enhanced strategy: {strategy_type}")
                    raise ConfigurationRequiredError(f"Cannot create enhanced strategy: {strategy_type}")
            else:
                logger.error(f"❌ Enhanced strategies disabled, cannot create strategy: {strategy_type}")
                raise ConfigurationRequiredError("Enhanced strategies are disabled")

        except Exception as e:
            logger.error(f"❌ Error creating strategy instance: {e}")
            return None

    async def _aggregate_symbol_signals(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """
        Aggregate multiple signals for the same symbol

        **ENHANCED:** Improved aggregation logic that:
        1. Uses proper weighted average (not confidence squared)
        2. Adds confidence boost for multiple signals (consensus strength)
        3. Ensures aggregated confidence doesn't drop below reasonable threshold
        """
        if not signals:
            return None

        # Weighted average aggregation
        total_weight = sum(s.confidence for s in signals)
        if total_weight == 0:
            return None

        signal_count = len(signals)
        avg_confidence = total_weight / signal_count if signal_count > 0 else 0.0

        # ENHANCED: For multiple signals, use consensus-based aggregation
        # When many signals agree, it's a strong signal (not a weak one)
        if signal_count > 1:
            # Use weighted average formula: sum(confidence^2) / sum(confidence)
            # This gives more weight to high-confidence signals
            weighted_confidence = sum(s.confidence * s.confidence for s in signals) / total_weight

            # ENHANCED: Add consensus boost for multiple signals
            # Many signals with same direction = strong consensus = higher confidence
            # Boost scales with signal count and average confidence
            consensus_boost = min(0.15, signal_count * 0.002)  # Up to 15% boost for many signals

            # Additional boost if average confidence is already high
            if avg_confidence > 0.6:
                consensus_boost += 0.05  # Extra 5% for high-confidence consensus

            # Apply consensus boost
            weighted_confidence = min(1.0, weighted_confidence + consensus_boost)

            # ENHANCED: For many signals (>20), the aggregated confidence should reflect consensus strength
            # When we have 100+ signals, that's a VERY strong consensus
            if signal_count > 20:
                # Use the higher of: weighted average or average with boost
                # This ensures many signals don't get penalized
                weighted_confidence = max(weighted_confidence, avg_confidence * 0.9 + consensus_boost)

            # ENHANCED: Floor for many signals - if we have 50+ signals, minimum confidence should be reasonable
            if signal_count > 50:
                min_confidence_floor = max(0.5, avg_confidence * 0.7)  # At least 70% of average
                weighted_confidence = max(weighted_confidence, min_confidence_floor)
        else:
            # Single signal - use its confidence directly
            weighted_confidence = signals[0].confidence if signals else 0.0

        weighted_expected_return = sum(s.expected_return * s.confidence for s in signals) / total_weight
        weighted_risk_score = sum(s.risk_score * s.confidence for s in signals) / total_weight

        # Determine consensus signal type (weighted by confidence)
        signal_votes = {}
        for signal in signals:
            vote = signal.signal_type
            signal_votes[vote] = signal_votes.get(vote, 0) + signal.confidence

        if not signal_votes:
            return None

        consensus_signal = max(signal_votes.items(), key=lambda x: x[1])[0]
        consensus_strength = signal_votes[consensus_signal] / total_weight  # Percentage of weighted votes

        # Calculate total quantity (use average, not sum, to avoid position sizing issues)
        matching_signals = [s for s in signals if s.signal_type == consensus_signal]
        if matching_signals:
            # Use average quantity for aggregated signal (more reasonable than sum)
            total_quantity = sum(s.quantity for s in matching_signals if s.quantity) / len(matching_signals) if matching_signals else None
        else:
            total_quantity = None

        logger.debug(f"   📊 Aggregation stats: {signal_count} signals, consensus={consensus_signal.value}, "
                    f"strength={consensus_strength:.2%}, confidence={weighted_confidence:.4f}")

        return TradingSignal(
            signal_id=str(uuid.uuid4()),
            strategy_name="aggregated",
            strategy_type=signals[0].strategy_type,
            symbol=signals[0].symbol,
            signal_type=consensus_signal,
            strength=SignalStrength.MEDIUM,
            confidence=min(1.0, weighted_confidence),  # Cap at 1.0
            expected_return=weighted_expected_return,
            risk_score=weighted_risk_score,
            quantity=total_quantity,
            target_price=signals[0].target_price,
            stop_loss=signals[0].stop_loss,
            take_profit=signals[0].take_profit,
            time_horizon=signals[0].time_horizon,
            metadata={'aggregated_from': len(signals), 'consensus_strength': consensus_strength}
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

    async def _initialize_performance_tracking(self):
        """Initialize strategy performance tracking"""
        logger.info("📊 Initializing strategy performance tracking...")
        # Performance tracking setup

    # ENHANCED METHODS - Multi-Strategy with Regime Awareness

    async def _get_current_regime_info(self) -> Dict[str, Any]:
        """Get comprehensive current regime information"""
        try:
            if self.regime_engine:
                # Use canonical get_current_regime() method (Rule 2)
                # Note: This is typically sync in the core engine implementation
                regime_analysis = self.regime_engine.get_current_regime()
                
                if regime_analysis:
                    # Handle both dict and object-based RegimeAnalysis
                    if isinstance(regime_analysis, dict):
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
                        # Object-based (RegimeAnalysis dataclass)
                        return {
                            'regime': getattr(regime_analysis, 'regime', 'neutral'),
                            'confidence': getattr(regime_analysis, 'confidence', 0.5),
                            'volatility': getattr(regime_analysis, 'volatility', 0.02),
                            'trend_strength': getattr(regime_analysis, 'trend_strength', 0.0),
                            'risk_multiplier': getattr(regime_analysis, 'risk_multiplier', 1.0),
                            'recommended_strategies': getattr(regime_analysis, 'recommended_strategies', ['mean_reversion', 'momentum']),
                            'strategy_weights': getattr(regime_analysis, 'strategy_weights', {'mean_reversion': 0.5, 'momentum': 0.5})
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

    def _is_strategy_regime_supported(self, strategy_type: StrategyType, regime_info: Dict[str, Any]) -> bool:
        """Check if strategy type is supported in current regime"""
        regime = regime_info.get('regime', 'neutral').lower()

        if strategy_type == StrategyType.MEAN_REVERSION:
            # Mean reversion works well in ranging/volatile markets
            # ENHANCED: Include canonical high volatility regimes (Rule 2)
            supported_regimes = [
                'ranging', 'volatile', 'calm_ranging', 'volatile_ranging', 'neutral',
                'range_bound', 'choppy', 'high_volatility', 'extreme_volatility',
                'bull_high_volatility', 'bear_high_volatility'
            ]
            return regime in supported_regimes
        elif strategy_type == StrategyType.MOMENTUM:
            # Momentum works well in trending markets
            # ENHANCED: Include canonical trending regimes (Rule 2)
            supported_regimes = [
                'trending', 'trending_up', 'trending_down', 'calm_trending', 'volatile_trending', 'neutral',
                'strong_trending', 'weak_trending', 'bull_low_volatility', 'bear_low_volatility'
            ]
            return regime in supported_regimes
        else:
            # Other strategies - allow by default
            return True

    async def _filter_signals_enhanced(self, signals: List[TradingSignal],
                                     regime_info: Dict[str, Any],
                                     current_positions: Optional[Dict[str, Dict[str, Any]]] = None) -> List[TradingSignal]:
        """Enhanced signal filtering with regime and position awareness"""
        filtered = []

        logger.info(f"🔍 Filtering {len(signals)} signals")

        for signal in signals:
            filter_reason = None

            # Regime appropriateness check
            if not self._is_strategy_regime_supported(signal.strategy_type, regime_info):
                filter_reason = f"strategy not supported in current regime"
                logger.debug(f"   ❌ Filtered {signal.strategy_name} {signal.symbol} {signal.signal_type}: {filter_reason}")
                continue

            # Position-aware filtering
            if current_positions:
                current_pos = current_positions.get(signal.symbol, {'shares': 0})
                has_position = current_pos.get('shares', 0) != 0
                is_long = current_pos.get('shares', 0) > 0

                # Don't buy if already long, don't sell if no position
                if signal.signal_type == SignalType.BUY and is_long:
                    filter_reason = f"already long position"
                    logger.debug(f"   ❌ Filtered {signal.strategy_name} {signal.symbol} {signal.signal_type}: {filter_reason}")
                    continue
                if signal.signal_type == SignalType.SELL and not has_position:
                    filter_reason = f"no position to sell"
                    logger.debug(f"   ❌ Filtered {signal.strategy_name} {signal.symbol} {signal.signal_type}: {filter_reason}")
                    continue

            # Strategy allocation check
            allocation = self.strategy_allocations.get(signal.strategy_name)
            if not allocation:
                filter_reason = f"no allocation found for {signal.strategy_name}"
                logger.debug(f"   ❌ Filtered {signal.strategy_name} {signal.symbol} {signal.signal_type}: {filter_reason}")
                continue
            if not allocation.active:
                filter_reason = f"allocation not active for {signal.strategy_name}"
                logger.debug(f"   ❌ Filtered {signal.strategy_name} {signal.symbol} {signal.signal_type}: {filter_reason}")
                continue

            filtered.append(signal)
            logger.debug(f"   ✅ Passed filter: {signal.strategy_name} {signal.symbol} {signal.signal_type} (confidence: {signal.confidence:.4f})")

        logger.info(f"✅ Filtered {len(filtered)}/{len(signals)} signals passed")
        return filtered

    def _strength_to_float(self, strength: SignalStrength) -> float:
        """Map SignalStrength enum to numeric scale."""
        if hasattr(strength, "value"):
            name = str(strength.value).lower()
        else:
            name = str(strength).lower()
        mapping = {
            "very_weak": 0.1,
            "weak": 0.3,
            "medium": 0.5,
            "moderate": 0.5,
            "strong": 0.7,
            "very_strong": 0.9,
        }
        return float(mapping.get(name, 0.5))

    def _strength_enum_from_value(self, value: float) -> SignalStrength:
        """Map numeric strength to SignalStrength enum."""
        v = abs(float(value))
        if v >= 0.85:
            return SignalStrength.VERY_STRONG
        if v >= 0.65:
            return SignalStrength.STRONG
        if v >= 0.45:
            return SignalStrength.MODERATE
        if v >= 0.25:
            return SignalStrength.WEAK
        return SignalStrength.VERY_WEAK

    def _signal_direction(self, signal: TradingSignal) -> int:
        """Return +1 for long, -1 for short, 0 otherwise."""
        st = signal.signal_type
        if hasattr(st, "value"):
            st_val = st.value
        else:
            st_val = str(st)
        st_val = str(st_val).lower()
        if st_val in ("long_entry", "buy", "increase_long", "long"):
            return 1
        if st_val in ("short_entry", "sell", "increase_short", "short"):
            return -1
        return 0

    def _compute_decorrelation_beta(self, symbol: str, mom_strength: float, mr_strength: float) -> float:
        """Compute rolling beta for MR vs MOM strengths."""
        history = self._hybrid_strength_history.get(symbol, [])
        history = history[-50:]  # cap window
        if len(history) < 5:
            return 0.0
        moms = [pair[0] for pair in history]
        mrs = [pair[1] for pair in history]
        mom_mean = sum(moms) / len(moms)
        mr_mean = sum(mrs) / len(mrs)
        cov = sum((m - mom_mean) * (r - mr_mean) for m, r in zip(moms, mrs)) / max(1, len(moms) - 1)
        var = sum((m - mom_mean) ** 2 for m in moms) / max(1, len(moms) - 1)
        if abs(var) < 1e-9:
            return 0.0
        return float(cov / var)

    def _update_strength_history(self, symbol: str, mom_strength: float, mr_strength: float) -> None:
        """Track recent MOM/MR strength pairs for decorrelation and covariance."""
        history = self._hybrid_strength_history.setdefault(symbol, [])
        history.append((float(mom_strength), float(mr_strength)))
        if len(history) > 200:
            del history[: len(history) - 200]

    def _recombine_mom_mr_signals(
        self,
        symbol: str,
        symbol_signals: List[TradingSignal],
        regime_info: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """Recombine MOM/MR signals for a symbol into a single hybrid signal."""
        if not self.hybrid_config.enable_hybrid_recombination:
            return None

        mom_candidates = []
        mr_candidates = []
        for signal in symbol_signals:
            source = signal.metadata.get("signal_source") if isinstance(signal.metadata, dict) else None
            if source == "momentum" or signal.strategy_type == StrategyType.MOMENTUM:
                mom_candidates.append(signal)
            elif source == "mean_reversion" or signal.strategy_type == StrategyType.MEAN_REVERSION:
                mr_candidates.append(signal)

        if not mom_candidates or not mr_candidates:
            return None

        mom_signal = max(mom_candidates, key=lambda s: s.confidence)
        mr_signal = max(mr_candidates, key=lambda s: s.confidence)

        mom_dir = self._signal_direction(mom_signal)
        mr_dir = self._signal_direction(mr_signal)
        if mom_dir == 0 or mr_dir == 0:
            return None

        mom_strength = mom_signal.metadata.get(
            "volatility_normalized_strength",
            self._strength_to_float(mom_signal.strength)
        )
        mr_strength = mr_signal.metadata.get(
            "volatility_normalized_strength",
            self._strength_to_float(mr_signal.strength)
        )

        mom_hold = mom_signal.metadata.get("expected_holding_period", self.hybrid_config.expected_holding_period_mom)
        mr_hold = mr_signal.metadata.get("expected_holding_period", self.hybrid_config.expected_holding_period_mr)
        mom_strength = float(mom_strength) / max(1.0, float(mom_hold)) ** 0.5
        mr_strength = float(mr_strength) / max(1.0, float(mr_hold)) ** 0.5

        # Decorrelation (orthogonalize MR to MOM)
        beta = self._compute_decorrelation_beta(symbol, mom_strength, mr_strength)
        mr_strength = float(mr_strength) - float(beta) * float(mom_strength)

        context = {
            "regime": regime_info.get("regime", "unknown"),
            "regime_probabilities": regime_info.get("regime_probabilities"),
            "regime_weight_map": self.hybrid_config.regime_weight_map,
            "mom_base_weight": self.hybrid_config.mom_base_weight,
            "mr_base_weight": self.hybrid_config.mr_base_weight,
            "weight_min": self.hybrid_config.weight_min,
            "weight_max": self.hybrid_config.weight_max,
            "weight_stability_threshold": self.hybrid_config.weight_stability_threshold,
            "rolling_sharpe_window": self.hybrid_config.rolling_sharpe_window,
            "use_probabilistic_regime": self.hybrid_config.use_probabilistic_regime,
            "use_covariance_blend": self.hybrid_config.use_covariance_blend,
            "strategy_performance": self.strategy_performance,
            "previous_weights": self._hybrid_weight_cache.get(symbol),
        }

        # Covariance-aware inputs (from rolling strength history)
        history = self._hybrid_strength_history.get(symbol, [])
        if len(history) >= 30:
            moms = [p[0] for p in history]
            mrs = [p[1] for p in history]
            mom_mean = sum(moms) / len(moms)
            mr_mean = sum(mrs) / len(mrs)
            cov_mm = sum((m - mom_mean) ** 2 for m in moms) / max(1, len(moms) - 1)
            cov_rr = sum((r - mr_mean) ** 2 for r in mrs) / max(1, len(mrs) - 1)
            cov_mr = sum((m - mom_mean) * (r - mr_mean) for m, r in zip(moms, mrs)) / max(1, len(moms) - 1)
            context["covariance_matrix"] = [[cov_mm, cov_mr], [cov_mr, cov_rr]]
            context["expected_returns"] = [mom_mean, mr_mean]

        weights = self.signal_combiner.calculate_hybrid_weights(mom_signal, mr_signal, context)
        mom_w = float(weights.get("mom_weight", 0.5))
        mr_w = float(weights.get("mr_weight", 0.5))

        combined_confidence = (mom_signal.confidence * mom_w) + (mr_signal.confidence * mr_w)
        conflict_detected = mom_dir != mr_dir
        conflict_penalty_applied = 0.0
        if conflict_detected:
            denom = max(abs(mom_strength), abs(mr_strength), 1e-6)
            disagreement = min(abs(mom_strength), abs(mr_strength)) / denom
            conflict_penalty_applied = float(self.hybrid_config.conflict_penalty_factor) * disagreement
            combined_confidence *= max(0.0, 1.0 - conflict_penalty_applied)

        combined_strength = (mom_strength * mom_w) + (mr_strength * mr_w)
        if abs(combined_strength) < 1e-3:
            return None

        combined_direction = SignalType.LONG_ENTRY if combined_strength >= 0 else SignalType.SHORT_ENTRY
        strength_enum = self._strength_enum_from_value(combined_strength)

        target_weight = None
        if mom_signal.target_weight is not None or mr_signal.target_weight is not None:
            mom_tw = float(mom_signal.target_weight or 0.0)
            mr_tw = float(mr_signal.target_weight or 0.0)
            target_weight = (mom_tw * mom_w) + (mr_tw * mr_w)

        hybrid_signal = TradingSignal(
            signal_id=str(uuid.uuid4()),
            strategy_name="hybrid_mom_mr",
            strategy_type=StrategyType.MULTI_FACTOR,
            symbol=symbol,
            signal_type=combined_direction,
            strength=strength_enum,
            confidence=float(combined_confidence),
            expected_return=(mom_signal.expected_return * mom_w) + (mr_signal.expected_return * mr_w),
            risk_score=(mom_signal.risk_score * mom_w) + (mr_signal.risk_score * mr_w),
            quantity=0.0,
            target_weight=target_weight,
            quantity_type="PERCENTAGE" if target_weight is not None else "ABSOLUTE",
            target_price=mom_signal.target_price or mr_signal.target_price,
            stop_loss=mom_signal.stop_loss or mr_signal.stop_loss,
            take_profit=mom_signal.take_profit or mr_signal.take_profit,
            metadata={
                "signal_source": "hybrid_mom_mr",
                "mom_contribution": mom_strength * mom_w,
                "mr_contribution": mr_strength * mr_w,
                "regime_used": regime_info.get("regime", "unknown"),
                "covariance_blend_used": bool(self.hybrid_config.use_covariance_blend),
                "conflict_detected": conflict_detected,
                "conflict_penalty_applied": conflict_penalty_applied,
                "decorrelation_beta": beta,
                "weights": {"mom": mom_w, "mr": mr_w},
            }
        )

        self._update_strength_history(symbol, mom_strength, mr_strength)
        self._hybrid_weight_cache[symbol] = {"mom_weight": mom_w, "mr_weight": mr_w}
        return hybrid_signal

    async def _aggregate_signals_enhanced(self, signals: List[TradingSignal],
                                        regime_info: Dict[str, Any]) -> List[TradingSignal]:
        """Enhanced signal aggregation with regime weighting"""
        if not signals:
            logger.info("📊 Aggregation: No signals to aggregate")
            return []

        logger.info(f"📊 Aggregating {len(signals)} signals for {len(set(s.symbol for s in signals))} symbols")

        # Group by symbol
        symbol_signals = {}
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)

        logger.info(f"📊 Grouped into {len(symbol_signals)} symbols")

        # Aggregate with regime weighting
        aggregated = []
        regime_weights = regime_info.get('strategy_weights', {})

        for symbol, symbol_signal_list in symbol_signals.items():
            # Hybrid MOM/MR recombination (optional)
            hybrid_signal = self._recombine_mom_mr_signals(symbol, symbol_signal_list, regime_info)
            if hybrid_signal is not None:
                non_mom_mr = []
                for s in symbol_signal_list:
                    source = s.metadata.get("signal_source") if isinstance(s.metadata, dict) else None
                    if source in ("momentum", "mean_reversion"):
                        continue
                    if s.strategy_type in (StrategyType.MOMENTUM, StrategyType.MEAN_REVERSION):
                        continue
                    non_mom_mr.append(s)
                if self.hybrid_config.hybrid_only:
                    symbol_signal_list = [hybrid_signal]
                else:
                    symbol_signal_list = non_mom_mr + [hybrid_signal]

            if len(symbol_signal_list) == 1:
                # Single signal - apply regime weighting (but don't penalize below threshold)
                signal = symbol_signal_list[0]
                original_confidence = signal.confidence
                strategy_weight = regime_weights.get(signal.strategy_type.value, 1.0)

                logger.info(f"📊 Aggregation for {symbol}: {signal.strategy_name} {signal.signal_type}")
                logger.info(f"   Original confidence: {original_confidence:.4f}")
                logger.info(f"   Regime weight: {strategy_weight:.4f}")

                weighted_confidence = original_confidence * strategy_weight
                signal.confidence = max(0.0, min(1.0, weighted_confidence))
                logger.info(f"   Regime adjustment applied: {original_confidence:.4f} → {weighted_confidence:.4f} → {signal.confidence:.4f}")

                logger.info(f"   Final confidence: {signal.confidence:.4f}")
                aggregated.append(signal)
                logger.info(f"   ✅ Signal added to aggregated list")
            else:
                # Multiple signals - intelligent aggregation
                logger.info(f"📊 Aggregating {len(symbol_signal_list)} signals for {symbol}")
                agg_signal = await self._aggregate_symbol_signals_enhanced(symbol_signal_list, regime_weights)
                if agg_signal:
                    aggregated.append(agg_signal)
                    logger.info(f"   ✅ Aggregated signal added: confidence {agg_signal.confidence:.4f}")
                else:
                    logger.warning(f"   ❌ Aggregation returned None for {len(symbol_signal_list)} signals")

        return aggregated

    async def _aggregate_symbol_signals_enhanced(self, signals: List[TradingSignal],
                                               regime_weights: Dict[str, float]) -> Optional[TradingSignal]:
        """
        Enhanced symbol signal aggregation with regime weighting

        **ENHANCED:** For multiple signals, apply regime weight AFTER aggregation to preserve
        consensus strength. This ensures that many signals agreeing doesn't get over-penalized.
        """
        if not signals:
            return None

        signal_count = len(signals)
        logger.info(f"📊 Aggregating {signal_count} signals for {signals[0].symbol}")

        # Calculate original confidence stats
        total_original_confidence = sum(s.confidence for s in signals)
        avg_original_confidence = total_original_confidence / signal_count if signal_count > 0 else 0.0
        regime_weight = regime_weights.get(signals[0].strategy_type.value, 1.0)

        logger.info(f"   📊 Original confidence stats: avg={avg_original_confidence:.4f}, total={total_original_confidence:.4f}")
        logger.info(f"   📊 Regime weight: {regime_weight:.4f}")

        # DETAILED: Show signal distribution
        confidence_distribution = {}
        signal_type_distribution = {}
        confidence_values = []

        for signal in signals:
            # Collect confidence values
            conf = signal.confidence
            confidence_values.append(conf)

            # Round confidence to 0.05 for grouping (more granular)
            conf_bucket = round(conf * 20) / 20  # Round to nearest 0.05
            confidence_distribution[conf_bucket] = confidence_distribution.get(conf_bucket, 0) + 1

            # Get signal type (handle both enum and string)
            try:
                if hasattr(signal.signal_type, 'value'):
                    sig_type = signal.signal_type.value
                elif hasattr(signal.signal_type, 'name'):
                    sig_type = signal.signal_type.name
                else:
                    sig_type = str(signal.signal_type)
            except Exception:  # Fix: avoid catching SystemExit, KeyboardInterrupt, etc.
                sig_type = str(signal.signal_type)

            signal_type_distribution[sig_type] = signal_type_distribution.get(sig_type, 0) + 1

        # Calculate statistics
        min_conf = min(confidence_values) if confidence_values else 0.0
        max_conf = max(confidence_values) if confidence_values else 0.0
        median_conf = sorted(confidence_values)[len(confidence_values) // 2] if confidence_values else 0.0

        logger.info(f"   📊 Signal Confidence Statistics:")
        logger.info(f"      Min: {min_conf:.4f}, Max: {max_conf:.4f}, Median: {median_conf:.4f}, Avg: {avg_original_confidence:.4f}")

        logger.info(f"   📊 Signal Confidence Distribution (by 0.05 buckets):")
        for conf_bucket in sorted(confidence_distribution.keys(), reverse=True):
            count = confidence_distribution[conf_bucket]
            pct = (count / signal_count) * 100
            bar = "█" * int(pct / 2)  # Visual bar
            logger.info(f"      {conf_bucket:.2f}: {count:3d} signals ({pct:5.1f}%) {bar}")

        logger.info(f"   📊 Signal Type Distribution:")
        for sig_type, count in sorted(signal_type_distribution.items(), key=lambda x: x[1], reverse=True):
            pct = (count / signal_count) * 100
            bar = "█" * int(pct / 2)  # Visual bar
            logger.info(f"      {sig_type}: {count:3d} signals ({pct:5.1f}%) {bar}")

        # Show sample signals with timestamps
        logger.info(f"   📊 Sample Signals (first 5 and last 5):")
        for i, signal in enumerate(signals[:5]):
            sig_type_str = str(signal.signal_type)
            if hasattr(signal.signal_type, 'value'):
                sig_type_str = signal.signal_type.value
            elif hasattr(signal.signal_type, 'name'):
                sig_type_str = signal.signal_type.name

            strength_str = str(signal.strength)
            if hasattr(signal.strength, 'value'):
                strength_str = signal.strength.value
            elif hasattr(signal.strength, 'name'):
                strength_str = signal.strength.name

            # Get timestamp from created_at or metadata
            timestamp = signal.created_at if hasattr(signal, 'created_at') and signal.created_at else None
            if not timestamp and 'timestamp' in signal.metadata:
                timestamp = signal.metadata.get('timestamp')
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except Exception:  # Fix: avoid catching SystemExit, KeyboardInterrupt, etc.
                        pass

            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'N/A'
            logger.info(f"      Signal {i+1}: {sig_type_str:4s} confidence={signal.confidence:.4f}, strength={strength_str}, timestamp={timestamp_str}")

        if signal_count > 10:
            logger.info(f"      ... ({signal_count - 10} signals in between) ...")
            for i, signal in enumerate(signals[-5:], start=signal_count-4):
                sig_type_str = str(signal.signal_type)
                if hasattr(signal.signal_type, 'value'):
                    sig_type_str = signal.signal_type.value
                elif hasattr(signal.signal_type, 'name'):
                    sig_type_str = signal.signal_type.name

                strength_str = str(signal.strength)
                if hasattr(signal.strength, 'value'):
                    strength_str = signal.strength.value
                elif hasattr(signal.strength, 'name'):
                    strength_str = signal.strength.name

                # Get timestamp
                timestamp = signal.created_at if hasattr(signal, 'created_at') and signal.created_at else None
                if not timestamp and 'timestamp' in signal.metadata:
                    timestamp = signal.metadata.get('timestamp')
                    if isinstance(timestamp, str):
                        try:
                            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except Exception:  # Fix: avoid catching SystemExit, KeyboardInterrupt, etc.
                            pass

                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'N/A'
                logger.info(f"      Signal {i}: {sig_type_str:4s} confidence={signal.confidence:.4f}, strength={strength_str}, timestamp={timestamp_str}")

        # Show ALL timestamps grouped by signal type
        logger.info(f"   📊 ALL 115 Signal Timestamps:")
        buy_signals_with_metadata = []
        sell_signals_with_metadata = []

        for signal in signals:
            # Get timestamp
            timestamp = signal.created_at if hasattr(signal, 'created_at') and signal.created_at else None

            # Try to get bar_index from metadata to reconstruct timestamp
            bar_index = None
            if signal.metadata:
                bar_index = signal.metadata.get('bar_index')
                # Also try additional_data
                if not bar_index and 'additional_data' in signal.metadata:
                    bar_index = signal.metadata['additional_data'].get('bar_index')

            # Get entry price for reference
            entry_price = None
            if signal.metadata:
                entry_price = signal.metadata.get('entry_price')
                if not entry_price and 'additional_data' in signal.metadata:
                    entry_price = signal.metadata['additional_data'].get('entry_price')

            sig_type_str = str(signal.signal_type)
            if hasattr(signal.signal_type, 'value'):
                sig_type_str = signal.signal_type.value
            elif hasattr(signal.signal_type, 'name'):
                sig_type_str = signal.signal_type.name

            signal_info = {
                'timestamp': timestamp,
                'bar_index': bar_index,
                'entry_price': entry_price,
                'confidence': signal.confidence
            }

            if sig_type_str.lower() == 'buy':
                buy_signals_with_metadata.append(signal_info)
            elif sig_type_str.lower() == 'sell':
                sell_signals_with_metadata.append(signal_info)

        # Sort by bar_index if available, otherwise by timestamp
        buy_signals_with_metadata.sort(key=lambda x: x['bar_index'] if x['bar_index'] is not None else (x['timestamp'] or datetime.min))
        sell_signals_with_metadata.sort(key=lambda x: x['bar_index'] if x['bar_index'] is not None else (x['timestamp'] or datetime.min))

        logger.info(f"      BUY Signals ({len(buy_signals_with_metadata)} total):")
        logger.info(f"         ⚠️  Note: Timestamps show signal creation time. Bar indices indicate historical evaluation.")
        for i, sig_info in enumerate(buy_signals_with_metadata[:20], 1):  # Show first 20
            bar_info = f"bar_idx={sig_info['bar_index']}" if sig_info['bar_index'] is not None else "bar_idx=N/A"
            price_info = f"price=${sig_info['entry_price']:.2f}" if sig_info['entry_price'] else "price=N/A"
            ts_str = sig_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if sig_info['timestamp'] else 'N/A'
            logger.info(f"         {i:3d}. {ts_str} | {bar_info} | {price_info} | conf={sig_info['confidence']:.4f}")
        if len(buy_signals_with_metadata) > 20:
            logger.info(f"         ... ({len(buy_signals_with_metadata) - 20} more BUY signals) ...")

        logger.info(f"      SELL Signals ({len(sell_signals_with_metadata)} total):")
        for i, sig_info in enumerate(sell_signals_with_metadata, 1):
            bar_info = f"bar_idx={sig_info['bar_index']}" if sig_info['bar_index'] is not None else "bar_idx=N/A"
            price_info = f"price=${sig_info['entry_price']:.2f}" if sig_info['entry_price'] else "price=N/A"
            ts_str = sig_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if sig_info['timestamp'] else 'N/A'
            logger.info(f"         {i:3d}. {ts_str} | {bar_info} | {price_info} | conf={sig_info['confidence']:.4f}")

        # Summary
        bar_indices = [s['bar_index'] for s in buy_signals_with_metadata + sell_signals_with_metadata if s['bar_index'] is not None]
        if bar_indices:
            min_bar = min(bar_indices)
            max_bar = max(bar_indices)
            logger.info(f"      📊 Bar Index Range: {min_bar} → {max_bar} (evaluated {max_bar - min_bar + 1} bars from historical data)")
            logger.info(f"      📊 Historical Scanning: {len(bar_indices)} signals generated from {max_bar - min_bar + 1} different bars")

        # ENHANCED: For multiple signals, aggregate FIRST, then apply regime weight
        # This preserves the consensus strength of many signals
        # Aggregation should reflect the strength of agreement, not be penalized before it happens
        logger.info(f"   📊 Step 1: Aggregating {signal_count} signals into single consensus signal...")
        agg_signal = await self._aggregate_symbol_signals(signals)

        if not agg_signal:
            logger.warning(f"   ❌ Aggregation returned None for {signal_count} signals")
            return None

        logger.info(f"   ✅ Aggregation complete: {signal_count} signals → 1 consensus signal")
        logger.info(f"      Consensus type: {agg_signal.signal_type.value if hasattr(agg_signal.signal_type, 'value') else agg_signal.signal_type}")
        logger.info(f"      Aggregated confidence (before regime): {agg_signal.confidence:.4f}")
        logger.info(f"      Aggregated from: {agg_signal.metadata.get('aggregated_from', signal_count)} signals")

        # Apply regime weight AFTER aggregation (for multiple signals)
        # This way, the consensus strength is preserved, and regime weight adjusts the final signal
        original_agg_confidence = agg_signal.confidence

        # ENHANCED: For many signals with high consensus, apply regime weight more gently
        # Many signals agreeing is a strong signal that should be respected
        if signal_count > 20 and original_agg_confidence >= 0.7:
            # Strong consensus (many signals + high confidence) - apply regime weight more gently
            # Use a blended approach: part regime weight, part original
            # This preserves the strength of consensus while still adjusting for regime
            regime_adjustment_factor = 0.7 + (0.3 * regime_weight)  # Blend: 70% preserve, 30% regime weight
            final_confidence = original_agg_confidence * regime_adjustment_factor
            logger.info(f"   📊 Strong consensus detected ({signal_count} signals, {original_agg_confidence:.4f} conf) - using gentle regime adjustment")
            logger.info(f"   📊 Regime adjustment: {original_agg_confidence:.4f} * {regime_adjustment_factor:.4f} = {final_confidence:.4f}")
        else:
            # Apply regime weight normally
            final_confidence = original_agg_confidence * regime_weight
            logger.info(f"   📊 Regime adjustment: {original_agg_confidence:.4f} * {regime_weight:.4f} = {final_confidence:.4f}")

        agg_signal.confidence = max(0.0, min(1.0, final_confidence))

        logger.info(f"   📊 Final aggregated signal confidence: {agg_signal.confidence:.4f}")
        logger.info("   ✅ Aggregated confidence computed (risk layer decides hard confidence eligibility)")

        return agg_signal

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
    # MULTI-STRATEGY COORDINATION METHODS
    # ========================================

    async def _initialize_multi_strategy_coordination(self) -> None:
        """Initialize multi-strategy coordination components"""
        try:
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

            # Rule 7 compliance (hard-fail)
            try:
                self._rule7_validator.enforce_rule7(strategy_instance)
            except Rule7ComplianceError as e:
                logger.error(str(e))
                raise

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

    async def collect_all_signals(self, market_data, position_details: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, List[EnhancedSignal]]:
        """
        Collect signals from all registered strategies

        Args:
            market_data: Dict mapping symbol to enriched DataFrame
            position_details: Dict mapping symbol to rich position info (entry_price, pnl, etc.)
        """
        if not self.signal_aggregator:
            logger.warning("Signal aggregator not available")
            return {}

        try:
            return await self.signal_aggregator.collect_all_signals(market_data, position_details=position_details)
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

    async def convert_signals_to_trading_requests(
        self,
        signals: List[EnhancedSignal],
        regime_context: Optional[Dict[str, Any]] = None
    ) -> List[TradingDecisionRequest]:
        """
        Convert EnhancedSignal objects to TradingDecisionRequest objects

        Implements Phase 6→7 conversion per Rule 4.1

        Args:
            signals: List of EnhancedSignal from strategy aggregation
            regime_context: Optional regime context for decision requests

        Returns:
            List of TradingDecisionRequest ready for risk authorization
        """
        try:
            # Get current regime if not provided
            if regime_context is None and self.regime_engine:
                try:
                    regime_analysis = await self.regime_engine.get_current_regime()
                    regime_context = {
                        'regime': regime_analysis.primary_regime.value if hasattr(regime_analysis, 'primary_regime') else 'unknown',
                        'confidence': regime_analysis.confidence if hasattr(regime_analysis, 'confidence') else 0.5,
                        'volatility': regime_analysis.volatility if hasattr(regime_analysis, 'volatility') else 0.02
                    }
                except Exception as e:
                    logger.warning(f"Could not get regime context: {e}")
                    regime_context = {'regime': 'unknown', 'confidence': 0.5, 'volatility': 0.02}
            elif regime_context is None:
                regime_context = {'regime': 'unknown', 'confidence': 0.5, 'volatility': 0.02}

            trading_requests = []

            for signal in signals:
                # Determine decision type based on signal type
                # Handle both enum and string values
                signal_type_value = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)

                if signal_type_value.lower() in ['buy', 'long']:
                    decision_type = TradingDecisionType.POSITION_ENTRY
                    side = 'buy'
                elif signal_type_value.lower() in ['sell', 'short']:
                    decision_type = TradingDecisionType.POSITION_EXIT
                    side = 'sell'
                elif signal_type_value.lower() == 'close':
                    decision_type = TradingDecisionType.POSITION_EXIT
                    side = 'sell'  # Close implies sell
                else:  # HOLD or unknown
                    continue  # Skip hold signals

                # Create TradingDecisionRequest
                request = TradingDecisionRequest(
                    decision_type=decision_type,
                    strategy_id=signal.strategy_id,
                    symbol=signal.symbol,
                    side=side,
                    quantity=signal.quantity,
                    confidence=signal.confidence,

                    # Market context
                    current_price=signal.price if signal.price else signal.metadata.get('current_price', 0.0),
                    market_regime=regime_context.get('regime', 'unknown'),
                    regime_confidence=regime_context.get('confidence', 0.5),
                    volatility_estimate=regime_context.get('volatility', 0.02),

                    # Metadata from signal
                    requesting_component='StrategyManager',
                    justification=f"Signal from {signal.strategy_type} strategy",
                    metadata={
                        'signal_id': signal.signal_id,
                        'strategy_type': signal.strategy_type,
                        'signal_timestamp': signal.timestamp.isoformat() if isinstance(signal.timestamp, datetime) else str(signal.timestamp),
                        'original_signal_metadata': signal.metadata
                    }
                )

                trading_requests.append(request)

            logger.info(
                f"✅ Converted {len(signals)} signals to {len(trading_requests)} trading requests "
                f"(Phase 6→7 conversion per Rule 4.1)"
            )

            return trading_requests

        except Exception as e:
            logger.error(f"Signal to request conversion failed: {e}")
            return []

    async def aggregate_signals_and_create_requests(
        self,
        strategy_signals: Dict[str, List[EnhancedSignal]]
    ) -> List[TradingDecisionRequest]:
        """
        Complete Phase 6 flow: Aggregate signals and convert to trading requests

        This is the main entry point for Phase 6→7 integration.

        Args:
            strategy_signals: Dict mapping strategy_id to list of signals

        Returns:
            List of TradingDecisionRequest ready for Phase 7 authorization
        """
        try:
            # Step 1: Aggregate signals from multiple strategies
            aggregated_signals = await self.aggregate_strategy_signals(strategy_signals)

            if not aggregated_signals:
                logger.warning("No signals after aggregation")
                return []

            logger.info(f"📊 Aggregated {len(aggregated_signals)} signals from {len(strategy_signals)} strategies")

            # Step 2: Convert to TradingDecisionRequest
            trading_requests = await self.convert_signals_to_trading_requests(aggregated_signals)

            logger.info(
                f"✅ Phase 6 complete: {len(aggregated_signals)} signals → "
                f"{len(trading_requests)} trading requests ready for Phase 7"
            )

            return trading_requests

        except Exception as e:
            logger.error(f"Phase 6 aggregation and conversion failed: {e}")
            return []

    async def generate_signals(
        self,
        symbols: List[str],
        market_data: Optional[Dict[str, Any]] = None,
        current_positions: Optional[Dict[str, Dict[str, Any]]] = None,
        position_details: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[EnhancedSignal]:
        """
        Generate signals using multi-strategy coordination
        """
        try:
            # Store position details for strategies to access
            self._position_details = position_details or {}

            if not self.enable_multi_strategy or not self.signal_aggregator:
                # Fallback to traditional signal generation (single-strategy / legacy mode)
                # IMPORTANT: This must still generate signals when multi-strategy coordinator is disabled.
                out = await self._generate_traditional_signals(
                    symbols,
                    market_data=market_data,
                    position_details=position_details,
                )

                # --- CP2: Pipeline Trace - Signal Generation (traditional path) ---
                try:
                    from core_engine.utils.pipeline_trace import get_tracer, CP2_SIGNAL_GEN
                    _cp2t = get_tracer()
                    if _cp2t.enabled and out:
                        def _extract_entry_diag(_sig):
                            _meta = getattr(_sig, 'metadata', {}) or {}
                            _ad = _meta.get('additional_data', {}) if isinstance(_meta, dict) else {}
                            if not isinstance(_ad, dict):
                                _ad = {}
                            _entry_diag = _meta.get('entry_diag', _ad.get('entry_diag'))
                            _entry_mode = _meta.get('entry_mode', _ad.get('entry_mode'))
                            if _entry_mode is None and isinstance(_entry_diag, dict):
                                _entry_mode = _entry_diag.get('entry_mode')
                            _expected_return_bps = _meta.get('expected_return_bps', _ad.get('expected_return_bps'))
                            return _entry_diag, _entry_mode, _expected_return_bps

                        for _sig in out:
                            _entry_diag, _entry_mode, _expected_return_bps = _extract_entry_diag(_sig)
                            _cp2t.emit(
                                trace_id=getattr(_sig, 'signal_id', '') or f"sig_{getattr(_sig, 'symbol', 'UNK')}",
                                checkpoint=CP2_SIGNAL_GEN,
                                component="StrategyManager",
                                method="generate_signals(traditional)",
                                symbol=getattr(_sig, 'symbol', ''),
                                bar_timestamp=getattr(_sig, 'timestamp', None),
                                input_data={
                                    "symbols": symbols,
                                    "market_data_keys": list((market_data or {}).keys()),
                                    "bar_timestamp": str(getattr(_sig, 'timestamp', '')),
                                    "symbol": getattr(_sig, 'symbol', ''),
                                },
                                output_data={
                                    "signal_type": str(getattr(_sig, 'signal_type', '')),
                                    "strength": float(getattr(_sig, 'strength', 0)),
                                    "confidence": float(getattr(_sig, 'confidence', 0)),
                                    "strategy_id": getattr(_sig, 'strategy_id', ''),
                                    "target_weight": getattr(_sig, 'target_weight', None),
                                    "entry_diag": _entry_diag,
                                    "entry_mode": _entry_mode,
                                    "expected_return_bps": _expected_return_bps,
                                },
                                metadata={
                                    "signal_count": len(out),
                                    "mode": "traditional",
                                    "entry_diag": _entry_diag,
                                    "entry_mode": _entry_mode,
                                    "expected_return_bps": _expected_return_bps,
                                },
                            )
                except Exception:
                    pass  # Never let trace errors break signal generation

                return out

            # Get market data (use provided or fetch)
            if market_data is None:
                market_data = await self._get_market_data(symbols)

            # Collect signals from all strategies (passing position details)
            strategy_signals = await self.collect_all_signals(market_data, position_details=position_details)

            # Aggregate and resolve conflicts
            aggregated_signals = await self.aggregate_strategy_signals(strategy_signals)

            # Performance/log-noise: avoid per-bar INFO logs when there are no signals.
            # INFO should represent actionable events; DEBUG heartbeat provides periodic visibility.
            if not hasattr(self, "_signal_log_counter"):
                self._signal_log_counter = 0
            self._signal_log_counter += 1

            if len(aggregated_signals) > 0:
                logger.info(
                    f"[SIG] Generated {len(aggregated_signals)} aggregated signals from {len(strategy_signals)} strategies"
                )
            else:
                if (self._signal_log_counter % 200) == 0:
                    logger.debug(
                        f"[SIG] Generated 0 aggregated signals from {len(strategy_signals)} strategies (heartbeat)"
                    )

            # --- CP2: Pipeline Trace - Signal Generation (multi-strategy path) ---
            try:
                from core_engine.utils.pipeline_trace import get_tracer, CP2_SIGNAL_GEN
                _cp2m = get_tracer()
                if _cp2m.enabled and aggregated_signals:
                    def _extract_entry_diag(_sig):
                        _meta = getattr(_sig, 'metadata', {}) or {}
                        _ad = _meta.get('additional_data', {}) if isinstance(_meta, dict) else {}
                        if not isinstance(_ad, dict):
                            _ad = {}
                        _entry_diag = _meta.get('entry_diag', _ad.get('entry_diag'))
                        _entry_mode = _meta.get('entry_mode', _ad.get('entry_mode'))
                        if _entry_mode is None and isinstance(_entry_diag, dict):
                            _entry_mode = _entry_diag.get('entry_mode')
                        _expected_return_bps = _meta.get('expected_return_bps', _ad.get('expected_return_bps'))
                        return _entry_diag, _entry_mode, _expected_return_bps

                    for _sig in aggregated_signals:
                        _entry_diag, _entry_mode, _expected_return_bps = _extract_entry_diag(_sig)
                        _cp2m.emit(
                            trace_id=getattr(_sig, 'signal_id', '') or f"sig_{getattr(_sig, 'symbol', 'UNK')}",
                            checkpoint=CP2_SIGNAL_GEN,
                            component="StrategyManager",
                            method="generate_signals(multi_strategy)",
                            symbol=getattr(_sig, 'symbol', ''),
                            bar_timestamp=getattr(_sig, 'timestamp', None),
                            input_data={
                                "symbols": symbols,
                                "strategy_count": len(strategy_signals),
                                "bar_timestamp": str(getattr(_sig, 'timestamp', '')),
                                "symbol": getattr(_sig, 'symbol', ''),
                            },
                            output_data={
                                "signal_type": str(getattr(_sig, 'signal_type', '')),
                                "strength": float(getattr(_sig, 'strength', 0)),
                                "confidence": float(getattr(_sig, 'confidence', 0)),
                                "strategy_id": getattr(_sig, 'strategy_id', ''),
                                "target_weight": getattr(_sig, 'target_weight', None),
                                "entry_diag": _entry_diag,
                                "entry_mode": _entry_mode,
                                "expected_return_bps": _expected_return_bps,
                            },
                            metadata={
                                "raw_signal_count": sum(len(s) for s in strategy_signals.values()) if isinstance(strategy_signals, dict) else len(strategy_signals),
                                "aggregated_count": len(aggregated_signals),
                                "mode": "multi_strategy",
                                "entry_diag": _entry_diag,
                                "entry_mode": _entry_mode,
                                "expected_return_bps": _expected_return_bps,
                            },
                        )
            except Exception:
                pass  # Never let trace errors break signal generation

            return aggregated_signals

        except Exception as e:
            logger.error(f"Multi-strategy signal generation failed: {e}")
            return []

    async def _generate_traditional_signals(
        self,
        symbols: List[str],
        market_data: Optional[Dict[str, Any]] = None,
        position_details: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[EnhancedSignal]:
        """
        Traditional signal generation (single-strategy / legacy mode).

        Generates signals directly from `active_strategies` without requiring
        MultiStrategySignalAggregator, which may be disabled in streaming runners.
        """
        try:
            if not self.active_strategies:
                return []

            # Market data is expected to be Dict[symbol, pd.DataFrame]
            if market_data is None or not isinstance(market_data, dict):
                return []

            enriched_dataframes: Dict[str, Any] = {}
            for sym in symbols:
                df = market_data.get(sym)
                if df is not None:
                    enriched_dataframes[sym] = df

            if not enriched_dataframes:
                return []

            out: List[EnhancedSignal] = []
            now = datetime.now()

            for strategy_name, strategy in self.active_strategies.items():
                allocation = self.strategy_allocations.get(strategy_name)
                if not allocation or not allocation.active:
                    continue

                # Strategy implementations accept Dict[symbol, pd.DataFrame]
                try:
                    try:
                        raw_signals = await strategy.generate_signals(
                            enriched_dataframes,
                            position_details=position_details,
                        )
                    except TypeError:
                        raw_signals = await strategy.generate_signals(enriched_dataframes)
                except Exception:
                    continue

                for rs in raw_signals or []:
                    try:
                        st = getattr(rs, "signal_type", SignalType.HOLD)
                        # Default quantities: support both ABSOLUTE and PERCENTAGE sizing
                        quantity_type = getattr(rs, "quantity_type", "ABSOLUTE") or "ABSOLUTE"
                        target_weight = getattr(rs, "target_weight", None)
                        target_qty = getattr(rs, "target_quantity", None)

                        _rs_additional_data = getattr(rs, "additional_data", {}) or {}
                        if not isinstance(_rs_additional_data, dict):
                            _rs_additional_data = {}

                        qty = float(target_qty or 0.0)
                        out.append(
                            EnhancedSignal(
                                signal_id=str(getattr(rs, "signal_id", "") or uuid.uuid4()),
                                symbol=str(getattr(rs, "symbol", "")),
                                signal_type=st if isinstance(st, SignalType) else SignalType(str(st).lower()),
                                confidence=float(getattr(rs, "confidence", 0.5) or 0.5),
                                strength=float(getattr(rs, "strength", 0.5) or 0.5),
                                quantity=qty,
                                timestamp=getattr(rs, "timestamp", now),
                                strategy_id=str(getattr(rs, "strategy_id", strategy_name) or strategy_name),
                                strategy_type=str(getattr(allocation.strategy_type, "value", allocation.strategy_type)),
                                price=getattr(rs, "signal_price", None),
                                target_weight=float(target_weight) if target_weight is not None else None,
                                quantity_type=str(quantity_type),
                                metadata={
                                    "strategy_name": strategy_name,
                                    "legacy_mode": True,
                                    "additional_data": _rs_additional_data,
                                    **_rs_additional_data,
                                },
                            )
                        )
                    except Exception:
                        continue

            return out
        except Exception:
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