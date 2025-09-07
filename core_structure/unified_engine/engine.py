"""
Unified Trading Engine - Phase 1 Consolidation
==============================================

Professional-grade unified trading engine that consolidates the best features
from all existing engines into a single, optimized implementation.

Combines:
- Core orchestration from unified_core_engine.py
- Interface delegation (formerly from trade_engine/core, now archived)  
- Performance optimizations (now built-in, formerly from trade_engine/optimization)

Author: Professional Trading System Architecture
Version: 4.0 (Unified Consolidation)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import pandas as pd

# Core Structure Imports (Updated for new structure)
from ..components.signal_generation import UnifiedSignalEngine as SignalGenerator, SignalConfig, TradingSignal, SignalType, SignalStrength
from ..components.execution.unified_execution_engine import UnifiedExecutionEngine, ExecutionMode, ExecutionRequest, ExecutionResult, ExecutionStatus
from ..components.risk import RiskManager, RiskLimits, TradingMode
from ..components.portfolio.portfolio_manager import PortfolioManager, PortfolioMetrics
from ..components.market_data import EnhancedDataManager as DataManager
from ..infrastructure import OrderSide

# Strategy Interface (Clean Delegation)
from ..interfaces.strategy_interfaces import StrategyInterface, StrategyFactory, StrategyType, StrategyContext, StrategyError, StrategyConfig

# Performance Optimizations (Phase 2)
from ..optimization.performance import (
    optimize_signal_generation, optimize_order_execution, optimize_portfolio_update, optimize_risk_calculation,
    performance_monitor, get_performance_summary, get_cache_statistics, clear_all_caches,
    batch_processor, CircularBuffer, FastDataFrame
)

# Memory Management (Phase 2 Batch 2)
from ..optimization.memory import (
    pool_manager, memory_monitor, memory_optimizer,
    get_trading_signal, release_trading_signal, get_order, release_order,
    pooled_signal, pooled_order, pooled_market_data, cleanup_memory_resources
)

# Async Optimization (Phase 2 Batch 3)
from ..optimization.async_features import (
    async_timed, async_retry, ConcurrencyLimiter, AsyncBatchProcessor,
    async_timeout_context, AsyncTradingOperations, async_task_manager,
    async_event_bus, get_async_performance_report, cleanup_async_resources
)

logger = logging.getLogger(__name__)

# ================================================================================
# UNIFIED ENGINE CONFIGURATION
# ================================================================================

class EngineStatus(Enum):
    """Engine operational status"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class TradingMode(Enum):
    """Trading execution mode"""
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"

@dataclass
class UnifiedEngineConfig:
    """Unified engine configuration combining all previous configs"""
    # Engine Identity
    engine_id: str = field(default_factory=lambda: f"unified_engine_{uuid.uuid4().hex[:8]}")
    trading_mode: TradingMode = TradingMode.PAPER_TRADING
    
    # Performance Settings (from optimized engine)
    enable_hot_path_optimization: bool = True
    enable_object_pooling: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    max_concurrent_strategies: int = 10
    max_processing_time_ms: int = 1000
    
    # Phase 2 Performance Enhancements
    enable_performance_monitoring: bool = True
    enable_batch_processing: bool = True
    batch_size: int = 50
    enable_memory_optimization: bool = True
    market_data_buffer_size: int = 1000
    
    # Phase 2 Memory Management
    enable_object_pooling: bool = True
    enable_gc_optimization: bool = True
    enable_memory_monitoring: bool = True
    pool_initial_sizes: Dict[str, int] = field(default_factory=lambda: {
        'trading_signals': 50,
        'orders': 30,
        'market_data': 100
    })
    
    # Phase 2 Async Optimization
    enable_async_optimization: bool = True
    max_concurrent_strategies: int = 20
    max_concurrent_executions: int = 10
    async_timeout_seconds: float = 30.0
    enable_async_monitoring: bool = True
    enable_event_driven_updates: bool = True
    
    # Component Validation (from delegated engine)
    enable_component_validation: bool = True
    enable_risk_checks: bool = True
    enable_signal_filtering: bool = True
    max_signals_per_cycle: int = 100
    
    # Core Engine Settings (from unified core engine)
    initial_capital: float = 10_000_000
    max_order_value: float = 1_000_000
    commission_rate: float = 0.0005
    default_execution_algorithm: str = "TWAP"
    
    # Risk Management
    max_portfolio_risk: float = 0.02
    max_position_size: float = 0.1
    max_drawdown: float = 0.15
    
    # Monitoring
    enable_monitoring: bool = True
    enable_dashboard: bool = True
    dashboard_update_interval: float = 1.0

@dataclass
class UnifiedTradingResult:
    """Unified trading result combining all result types"""
    strategy_id: str
    timestamp: datetime
    success: bool
    
    # Performance Metrics (non-default fields first)
    processing_time_ms: float = 0.0
    
    # Optimization Metrics
    cache_hit: bool = False
    objects_pooled: int = 0
    
    # Error Handling
    error_message: str = ""
    
    # Core Results (default factory fields last)
    signals_generated: List[TradingSignal] = field(default_factory=list)
    execution_results: List[ExecutionResult] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    portfolio_update: Optional[PortfolioMetrics] = field(default=None)
    warnings: List[str] = field(default_factory=list)

# ================================================================================
# UNIFIED TRADING ENGINE
# ================================================================================

class UnifiedTradingEngine:
    """
    Unified Trading Engine - Consolidation of All Engines
    
    This engine combines the best features from:
    1. Core orchestration and component management
    2. Clean interface delegation patterns
    3. Performance optimizations and hot path caching
    
    Key Features:
    - Single source of truth for trading operations
    - Clean strategy delegation with validation
    - Integrated performance optimizations
    - Comprehensive error handling and monitoring
    """
    
    def __init__(self, config: Optional[UnifiedEngineConfig] = None):
        """Initialize unified trading engine"""
        self.config = config or UnifiedEngineConfig()
        self.status = EngineStatus.INITIALIZING
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"🚀 UnifiedTradingEngine initializing with ID: {self.config.engine_id}")
        
        # Core Components
        self._initialize_core_components()
        
        # Strategy Management (Clean Delegation)
        self._strategy_instances: Dict[str, StrategyInterface] = {}
        self._strategy_configs: Dict[str, StrategyConfig] = {}
        
        # Performance Optimization Components (Phase 2 integration)
        self._performance_cache: Dict[str, Any] = {}
        self._object_pools: Dict[str, Any] = {}
        
        # Phase 2 Performance Components
        if self.config.enable_memory_optimization:
            self._market_data_buffer = CircularBuffer(self.config.market_data_buffer_size)
        else:
            self._market_data_buffer = None
        
        # Phase 2 Memory Management Components
        if self.config.enable_object_pooling:
            # Pool manager is already initialized globally
            self._pool_manager = pool_manager
            
            # Optimize garbage collection if enabled
            if self.config.enable_gc_optimization:
                self._gc_optimization_results = memory_optimizer.optimize_garbage_collection()
                self.logger.info(f"🧹 GC optimization applied: {self._gc_optimization_results}")
        else:
            self._pool_manager = None
            self._gc_optimization_results = None
        
        # Phase 2 Async Optimization Components
        if self.config.enable_async_optimization:
            # Initialize async trading operations with configured limits
            self._async_trading_ops = AsyncTradingOperations(
                max_concurrent_signals=self.config.max_concurrent_strategies,
                max_concurrent_executions=self.config.max_concurrent_executions
            )
            
            # Initialize concurrency limiters
            self._strategy_limiter = ConcurrencyLimiter(self.config.max_concurrent_strategies)
            self._execution_limiter = ConcurrencyLimiter(self.config.max_concurrent_executions)
            
            # Initialize async batch processor
            self._async_batch_processor = AsyncBatchProcessor(
                batch_size=self.config.batch_size,
                max_concurrent=min(5, self.config.max_concurrent_executions)
            )
        else:
            self._async_trading_ops = None
            self._strategy_limiter = None
            self._execution_limiter = None
            self._async_batch_processor = None
        
        # Engine Metrics
        self._cycle_count = 0
        self._successful_cycles = 0
        self._failed_cycles = 0
        self._total_processing_time = 0.0
        
        self.status = EngineStatus.READY
        self.logger.info(f"✅ UnifiedTradingEngine ready: {self.config.engine_id}")
    
    def _initialize_core_components(self):
        """Initialize core trading components"""
        try:
            # Signal Generation
            signal_config = SignalConfig()
            self.signal_generator = SignalGenerator(signal_config)
            
            # Risk Management
            risk_limits = RiskLimits(
                max_position_size=self.config.max_position_size,
                max_portfolio_risk=self.config.max_portfolio_risk,
                max_drawdown=self.config.max_drawdown
            )
            # Initialize unified risk manager
            self.risk_manager = RiskManager(
                risk_limits=risk_limits,
                trading_mode=TradingMode.LIVE_TRADING,  # Default for unified engine
                initial_capital=self.config.initial_capital
            )
            
            # Portfolio Management
            self.portfolio_manager = PortfolioManager(
                initial_capital=self.config.initial_capital
            )
            
            # Unified Execution Engine (supports all trading modes)
            execution_mode = ExecutionMode.LIVE_TRADING  # Default for unified engine
            if self.config.trading_mode == TradingMode.SIMULATION:
                execution_mode = ExecutionMode.BACKTESTING
            
            self.execution_engine = UnifiedExecutionEngine(
                mode=execution_mode,
                initial_capital=self.config.initial_capital
            )
            
            # Data Management
            self.data_manager = DataManager()
            
            self.logger.info("✅ Core components initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Core component initialization failed: {e}")
            raise
    
    # ================================================================================
    # STRATEGY MANAGEMENT (CLEAN DELEGATION)
    # ================================================================================
    
    def register_strategy(self, strategy_config: StrategyConfig) -> None:
        """Register a strategy using clean delegation pattern"""
        try:
            # Create strategy instance through factory
            strategy_instance = StrategyFactory.create_strategy(
                strategy_type=strategy_config.strategy_type,
                strategy_id=strategy_config.strategy_id,
                config=strategy_config.signal_params
            )
            
            # Validate strategy if component validation enabled
            if self.config.enable_component_validation:
                if not strategy_instance.validate_parameters(strategy_config.signal_params):
                    raise StrategyError(f"Strategy parameter validation failed: {strategy_config.strategy_id}")
            
            # Store strategy and config
            self._strategy_instances[strategy_config.strategy_id] = strategy_instance
            self._strategy_configs[strategy_config.strategy_id] = strategy_config
            
            self.logger.info(f"✅ Strategy registered: {strategy_config.strategy_id} ({strategy_config.strategy_type.value})")
            
        except Exception as e:
            self.logger.error(f"❌ Strategy registration failed: {strategy_config.strategy_id} - {e}")
            raise StrategyError(f"Failed to register strategy: {e}")
    
    def unregister_strategy(self, strategy_id: str) -> None:
        """Unregister a strategy"""
        if strategy_id in self._strategy_instances:
            del self._strategy_instances[strategy_id]
            del self._strategy_configs[strategy_id]
            self.logger.info(f"✅ Strategy unregistered: {strategy_id}")
        else:
            self.logger.warning(f"⚠️ Strategy not found for unregistration: {strategy_id}")
    
    def get_registered_strategies(self) -> List[str]:
        """Get list of registered strategy IDs"""
        return list(self._strategy_instances.keys())
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific strategy"""
        if strategy_id in self._strategy_instances:
            strategy = self._strategy_instances[strategy_id]
            return strategy.get_strategy_metrics().__dict__
        return None
    
    # ================================================================================
    # UNIFIED TRADING CYCLE (COMBINING ALL PATTERNS)
    # ================================================================================
    
    async def execute_trading_cycle(self, market_data: pd.DataFrame, 
                                  strategy_ids: Optional[List[str]] = None) -> List[UnifiedTradingResult]:
        """
        Execute unified trading cycle combining all engine patterns:
        - Core orchestration (from unified_core_engine)
        - Clean delegation (formerly from delegated_core_engine, now built-in)  
        - Performance optimization (from optimized_core_engine)
        """
        if self.status != EngineStatus.READY:
            raise RuntimeError(f"Engine not ready: {self.status}")
        
        self.status = EngineStatus.RUNNING
        cycle_start_time = datetime.now()
        self._cycle_count += 1
        
        try:
            # Select strategies to run
            target_strategies = strategy_ids or list(self._strategy_instances.keys())
            
            if not target_strategies:
                self.logger.warning("⚠️ No strategies to execute")
                return []
            
            self.logger.info(f"🔄 Executing unified trading cycle {self._cycle_count} for {len(target_strategies)} strategies")
            
            # Execute strategies with async optimization
            if self.config.enable_async_optimization and len(target_strategies) > 1:
                # Use async-optimized parallel execution with proper concurrency control
                results = await self._execute_strategies_async_optimized(
                    target_strategies, market_data, cycle_start_time
                )
            else:
                # Execute strategies in parallel (standard async)
                results = await asyncio.gather(*[
                    self._execute_strategy_cycle(strategy_id, market_data, cycle_start_time)
                    for strategy_id in target_strategies
                ], return_exceptions=True)
            
            # Process results
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Strategy execution failed: {target_strategies[i]} - {result}")
                    self._failed_cycles += 1
                else:
                    successful_results.append(result)
                    self._successful_cycles += 1
            
            # Update engine metrics
            processing_time = (datetime.now() - cycle_start_time).total_seconds() * 1000
            self._total_processing_time += processing_time
            
            self.logger.info(f"✅ Unified trading cycle {self._cycle_count} complete: {len(successful_results)}/{len(target_strategies)} successful ({processing_time:.2f}ms)")
            
            return successful_results
            
        except Exception as e:
            self.logger.error(f"❌ Unified trading cycle failed: {e}")
            self._failed_cycles += 1
            raise
        finally:
            self.status = EngineStatus.READY
    
    async def _execute_strategy_cycle(self, strategy_id: str, market_data: pd.DataFrame,
                                    cycle_start_time: datetime) -> UnifiedTradingResult:
        """Execute single strategy cycle with unified patterns"""
        try:
            # Get strategy and config
            strategy = self._strategy_instances[strategy_id]
            strategy_config = self._strategy_configs[strategy_id]
            
            # Create strategy context (clean delegation pattern)
            context = StrategyContext(
                market_data=market_data,
                portfolio_state=self.portfolio_manager.get_portfolio_state(),
                risk_parameters=strategy_config.risk_params,
                timestamp=cycle_start_time,
                strategy_config=strategy_config.signal_params
            )
            
            # STEP 1: Generate signals through strategy delegation (memory optimized)
            signals = await self._generate_signals_with_pooling(strategy, context)
            
            # STEP 2: Validate signals through risk management
            validated_signals = await self._validate_signals(signals, strategy_config)
            
            # STEP 3: Execute validated signals (memory optimized)
            execution_results = await self._execute_signals_with_pooling(validated_signals, strategy_config)
            
            # STEP 4: Update portfolio
            portfolio_update = await self._update_portfolio(execution_results)
            
            # STEP 5: Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(
                strategy_id, signals, execution_results
            )
            
            # Create unified result
            processing_time = (datetime.now() - cycle_start_time).total_seconds() * 1000
            
            return UnifiedTradingResult(
                strategy_id=strategy_id,
                timestamp=cycle_start_time,
                success=True,
                signals_generated=validated_signals,
                execution_results=execution_results,
                portfolio_update=portfolio_update,
                performance_metrics=performance_metrics,
                processing_time_ms=processing_time,
                cache_hit=False,  # Will be enhanced in Phase 2
                objects_pooled=0  # Will be enhanced in Phase 2
            )
            
        except Exception as e:
            self.logger.error(f"❌ Strategy cycle failed: {strategy_id} - {e}")
            return UnifiedTradingResult(
                strategy_id=strategy_id,
                timestamp=cycle_start_time,
                success=False,
                error_message=str(e),
                processing_time_ms=(datetime.now() - cycle_start_time).total_seconds() * 1000
            )
    
    # ================================================================================
    # OPTIMIZED SUPPORTING METHODS (PHASE 2 PERFORMANCE)
    # ================================================================================
    
    @optimize_signal_generation
    async def _validate_signals(self, signals: List[TradingSignal], 
                               strategy_config: StrategyConfig) -> List[TradingSignal]:
        """Validate signals using risk management (optimized with caching)"""
        try:
            if not self.config.enable_risk_checks:
                return signals
            
            validated_signals = []
            
            # Use batch processing if enabled
            if self.config.enable_batch_processing and len(signals) > self.config.batch_size:
                # Process in batches for better performance
                batches = [signals[i:i + self.config.batch_size] 
                          for i in range(0, len(signals), self.config.batch_size)]
                
                for batch in batches:
                    batch_validated = await self._validate_signal_batch(batch, strategy_config)
                    validated_signals.extend(batch_validated)
            else:
                # Process all signals at once
                validated_signals = await self._validate_signal_batch(signals, strategy_config)
            
            self.logger.debug(f"✅ Validated {len(validated_signals)}/{len(signals)} signals")
            return validated_signals
            
        except Exception as e:
            self.logger.error(f"❌ Signal validation failed: {e}")
            return []
    
    async def _validate_signal_batch(self, signals: List[TradingSignal], 
                                   strategy_config: StrategyConfig) -> List[TradingSignal]:
        """Validate a batch of signals"""
        validated_signals = []
        
        for signal in signals:
            # Use risk manager for validation (pure delegation)
            position_size = self.risk_manager.calculate_position_size(
                symbol=signal.symbol_pair,
                signal_strength=signal.confidence,
                method="signal_strength"
            )
            
            if position_size.position_size <= self.risk_manager.risk_limits.max_position_size:
                validated_signals.append(signal)
            else:
                self.logger.warning(f"⚠️ Signal rejected - position size limit: {signal.symbol_pair}")
        
        return validated_signals
    
    @optimize_order_execution
    async def _execute_signals(self, signals: List[TradingSignal], 
                             strategy_config: StrategyConfig) -> List[ExecutionResult]:
        """Execute trading signals (optimized with batching and caching)"""
        try:
            if not signals:
                return []
            
            execution_results = []
            
            # Use batch processing if enabled and beneficial
            if (self.config.enable_batch_processing and 
                len(signals) > self.config.batch_size):
                
                # Process signals in optimized batches
                execution_results = await batch_processor.process_signals_batch(
                    signals, 
                    lambda batch: self._execute_signal_batch(batch, strategy_config)
                )
            else:
                # Process all signals in single batch
                execution_results = await self._execute_signal_batch(signals, strategy_config)
            
            return execution_results
            
        except Exception as e:
            self.logger.error(f"❌ Signal execution failed: {e}")
            return []
    
    async def _execute_signal_batch(self, signals: List[TradingSignal], 
                                  strategy_config: StrategyConfig) -> List[ExecutionResult]:
        """Execute a batch of signals efficiently"""
        execution_results = []
        
        for signal in signals:
            try:
                # Pure delegation to execution engine
                execution_request = ExecutionRequest(
                    symbol=signal.symbol_pair,
                    side=OrderSide.BUY if signal.signal_type in [SignalType.LONG] else OrderSide.SELL,
                    quantity=signal.position_size,
                    order_type="MARKET",
                    algorithm=self.config.default_execution_algorithm
                )
                
                result = await self.execution_engine.execute_order(execution_request)
                execution_results.append(result)
                
                self.logger.debug(f"📋 Executed: {signal.symbol_pair} - {result.status}")
                
            except Exception as e:
                self.logger.warning(f"Failed to execute signal for {signal.symbol_pair}: {e}")
                continue
        
        return execution_results
    
    @optimize_portfolio_update
    async def _update_portfolio(self, execution_results: List[ExecutionResult]) -> Optional[PortfolioMetrics]:
        """Update portfolio based on executions (optimized with caching)"""
        try:
            if not execution_results:
                return None
            
            for result in execution_results:
                if result.status == ExecutionStatus.FILLED:
                    # Pure delegation to portfolio manager
                    self.portfolio_manager.update_position(
                        symbol=result.symbol,
                        quantity=result.filled_quantity,
                        price=result.average_price
                    )
            
            return self.portfolio_manager.get_portfolio_metrics()
            
        except Exception as e:
            self.logger.error(f"❌ Portfolio update failed: {e}")
            return None
    
    @optimize_risk_calculation
    def _calculate_performance_metrics(self, strategy_id: str, signals: List[TradingSignal],
                                     execution_results: List[ExecutionResult]) -> Dict[str, Any]:
        """Calculate performance metrics (optimized with caching)"""
        try:
            # Basic performance metrics
            metrics = {
                'signals_generated': len(signals),
                'orders_executed': len(execution_results),
                'execution_rate': len(execution_results) / len(signals) if signals else 0.0,
                'strategy_id': strategy_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add execution-specific metrics
            if execution_results:
                filled_orders = [r for r in execution_results if r.status == ExecutionStatus.FILLED]
                metrics.update({
                    'fill_rate': len(filled_orders) / len(execution_results),
                    'total_volume': sum(r.filled_quantity for r in filled_orders),
                    'average_fill_price': sum(r.average_price * r.filled_quantity for r in filled_orders) / 
                                        sum(r.filled_quantity for r in filled_orders) if filled_orders else 0.0
                })
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"❌ Performance calculation failed: {e}")
            return {'error': str(e)}
    
    # ================================================================================
    # MEMORY-OPTIMIZED METHODS (PHASE 2 BATCH 2)
    # ================================================================================
    
    async def _generate_signals_with_pooling(self, strategy: StrategyInterface, 
                                           context: StrategyContext) -> List[TradingSignal]:
        """Generate signals using object pooling for memory efficiency"""
        if not self.config.enable_object_pooling:
            # Fall back to regular signal generation
            return await strategy.generate_signals(context)
        
        try:
            # Use context manager for automatic pool management
            with pooled_signal() as pooled_signals_list:
                # Generate signals through strategy
                raw_signals = await strategy.generate_signals(context)
                
                # Convert to pooled objects if needed
                if self.config.enable_memory_optimization:
                    optimized_signals = []
                    for signal in raw_signals:
                        # Use pooled signal object
                        pooled_signal_obj = get_trading_signal()
                        
                        # Populate with signal data
                        pooled_signal_obj.populate(
                            symbol=getattr(signal, 'symbol_pair', ''),
                            signal_type=getattr(signal, 'signal_type', '').value if hasattr(getattr(signal, 'signal_type', ''), 'value') else str(getattr(signal, 'signal_type', '')),
                            strength=getattr(signal, 'strength', 0.0),
                            confidence=getattr(signal, 'confidence', 0.0),
                            position_size=getattr(signal, 'position_size', 0.0)
                        )
                        
                        optimized_signals.append(signal)  # Keep original signal format for compatibility
                        
                        # Store pooled object for later cleanup
                        pooled_signals_list.append(pooled_signal_obj)
                    
                    return optimized_signals
                else:
                    return raw_signals
                    
        except Exception as e:
            self.logger.error(f"❌ Memory-optimized signal generation failed: {e}")
            # Fall back to regular generation
            return await strategy.generate_signals(context)
    
    async def _execute_signals_with_pooling(self, signals: List[TradingSignal], 
                                          strategy_config: StrategyConfig) -> List[ExecutionResult]:
        """Execute signals using object pooling for orders"""
        if not self.config.enable_object_pooling:
            # Fall back to regular execution
            return await self._execute_signals(signals, strategy_config)
        
        try:
            execution_results = []
            pooled_orders = []
            
            for signal in signals:
                try:
                    # Use pooled order object
                    pooled_order = get_order()
                    
                    # Populate order from signal
                    pooled_order.populate(
                        order_id=f"order_{int(time.time() * 1000000)}",
                        symbol=getattr(signal, 'symbol_pair', ''),
                        side="BUY" if getattr(signal, 'signal_type', None) in [SignalType.LONG] else "SELL",
                        quantity=getattr(signal, 'position_size', 0.0),
                        order_type="MARKET"
                    )
                    
                    pooled_orders.append(pooled_order)
                    
                    # Execute through regular engine (using pooled order data)
                    execution_request = ExecutionRequest(
                        symbol=pooled_order.symbol,
                        side=OrderSide.BUY if pooled_order.side == "BUY" else OrderSide.SELL,
                        quantity=pooled_order.quantity,
                        order_type=pooled_order.order_type,
                        algorithm=self.config.default_execution_algorithm
                    )
                    
                    result = await self.execution_engine.execute_order(execution_request)
                    execution_results.append(result)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to execute pooled signal: {e}")
                    continue
            
            # Release pooled orders back to pool
            for pooled_order in pooled_orders:
                release_order(pooled_order)
            
            return execution_results
            
        except Exception as e:
            self.logger.error(f"❌ Memory-optimized execution failed: {e}")
            # Fall back to regular execution
            return await self._execute_signals(signals, strategy_config)
    
    # ================================================================================
    # ASYNC-OPTIMIZED METHODS (PHASE 2 BATCH 3)
    # ================================================================================
    
    @async_timed("async_strategies_execution", timeout=30.0)
    async def _execute_strategies_async_optimized(self, strategy_ids: List[str], 
                                                market_data: pd.DataFrame, 
                                                cycle_start_time: datetime) -> List[UnifiedTradingResult]:
        """Execute multiple strategies with full async optimization"""
        if not self.config.enable_async_optimization or not self._async_batch_processor:
            # Fall back to standard execution
            return await asyncio.gather(*[
                self._execute_strategy_cycle(strategy_id, market_data, cycle_start_time)
                for strategy_id in strategy_ids
            ], return_exceptions=True)
        
        try:
            # Use async timeout context for the entire operation
            async with async_timeout_context(self.config.async_timeout_seconds, "strategy_batch_execution"):
                
                # Create strategy execution coroutines with concurrency limiting
                async def execute_single_strategy_with_limit(strategy_id: str):
                    async with self._strategy_limiter:
                        return await self._execute_strategy_cycle(strategy_id, market_data, cycle_start_time)
                
                # Process strategies using async batch processor
                strategy_coros = [execute_single_strategy_with_limit(sid) for sid in strategy_ids]
                
                # Execute with proper concurrency control
                results = await asyncio.gather(*strategy_coros, return_exceptions=True)
                
                return results
                
        except asyncio.TimeoutError:
            self.logger.error(f"❌ Async strategy execution timed out after {self.config.async_timeout_seconds}s")
            # Return timeout errors for all strategies
            return [asyncio.TimeoutError("Strategy execution timeout") for _ in strategy_ids]
        except Exception as e:
            self.logger.error(f"❌ Async strategy execution failed: {e}")
            return [e for _ in strategy_ids]
    
    @async_timed("async_signal_validation")
    async def _validate_signals_async_optimized(self, signals: List[TradingSignal], 
                                              strategy_config: StrategyConfig) -> List[TradingSignal]:
        """Validate signals with async optimization for large signal sets"""
        if not self.config.enable_async_optimization or len(signals) < self.config.batch_size:
            # Use regular validation for small signal sets
            return await self._validate_signals(signals, strategy_config)
        
        try:
            # Process large signal sets in async batches
            async def validate_signal_batch(signal_batch: List[TradingSignal]) -> List[TradingSignal]:
                return await self._validate_signal_batch(signal_batch, strategy_config)
            
            # Use async batch processor for concurrent validation
            if self._async_batch_processor:
                validated_batches = await self._async_batch_processor.process_batch(
                    [signals[i:i + self.config.batch_size] 
                     for i in range(0, len(signals), self.config.batch_size)],
                    validate_signal_batch
                )
                
                # Flatten results
                validated_signals = []
                for batch_result in validated_batches:
                    if isinstance(batch_result, list):
                        validated_signals.extend(batch_result)
                
                return validated_signals
            else:
                return await self._validate_signals(signals, strategy_config)
                
        except Exception as e:
            self.logger.error(f"❌ Async signal validation failed: {e}")
            # Fall back to regular validation
            return await self._validate_signals(signals, strategy_config)
    
    # ================================================================================
    # PERFORMANCE MONITORING AND REPORTING (PHASE 2)
    # ================================================================================
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary including Phase 2 optimizations"""
        base_summary = {
            'engine_id': self.config.engine_id,
            'total_cycles': self._cycle_count,
            'successful_cycles': self._successful_cycles,
            'failed_cycles': self._failed_cycles,
            'success_rate': self._successful_cycles / self._cycle_count if self._cycle_count > 0 else 0.0,
            'average_processing_time_ms': self._total_processing_time / self._cycle_count if self._cycle_count > 0 else 0.0,
            'active_strategies': len(self._strategy_instances),
            'registered_strategies': len(self._strategy_configs)
        }
        
        # Add Phase 2 performance data if monitoring enabled
        if self.config.enable_performance_monitoring:
            perf_summary = get_performance_summary()
            cache_stats = get_cache_statistics()
            
            base_summary.update({
                'hot_path_performance': perf_summary,
                'cache_statistics': cache_stats,
                'hot_path_optimization_enabled': self.config.enable_hot_path_optimization,
                'memory_optimization_enabled': self.config.enable_memory_optimization,
                'async_optimization_enabled': self.config.enable_async_optimization,
                'batch_processing_enabled': self.config.enable_batch_processing,
                'batch_size': self.config.batch_size
            })
            
            # Add memory management metrics if enabled
            if self.config.enable_object_pooling and self._pool_manager:
                pool_stats = self._pool_manager.get_all_statistics()
                memory_summary = memory_monitor.get_memory_summary()
                
                base_summary.update({
                    'object_pooling_enabled': True,
                    'pool_statistics': {name: {
                        'current_size': stats.current_size,
                        'efficiency': stats.get_efficiency_rate(),
                        'hit_rate': stats.get_hit_rate()
                    } for name, stats in pool_stats.items()},
                    'memory_usage_mb': memory_summary['current_memory_mb'],
                    'memory_growth_mb': memory_summary['memory_growth_mb'],
                    'gc_collections': memory_summary['gc_collections']
                })
            
            # Add async optimization metrics if enabled
            if self.config.enable_async_optimization and self.config.enable_async_monitoring:
                async_metrics = {}
                
                # Get async task status
                task_status = async_task_manager.get_task_status()
                if task_status:
                    async_metrics['active_tasks'] = len([s for s in task_status.values() if s == 'running'])
                    async_metrics['completed_tasks'] = len([s for s in task_status.values() if s == 'completed'])
                    async_metrics['failed_tasks'] = len([s for s in task_status.values() if s == 'failed'])
                
                # Get concurrency limiter status
                if self._strategy_limiter:
                    async_metrics['strategy_concurrency_active'] = self._strategy_limiter.get_active_count()
                    async_metrics['strategy_concurrency_limit'] = self.config.max_concurrent_strategies
                
                if self._execution_limiter:
                    async_metrics['execution_concurrency_active'] = self._execution_limiter.get_active_count()
                    async_metrics['execution_concurrency_limit'] = self.config.max_concurrent_executions
                
                base_summary.update({
                    'async_optimization_enabled': True,
                    'async_metrics': async_metrics
                })
        
        return base_summary
    
    def get_detailed_performance_report(self) -> str:
        """Generate detailed performance report including Phase 2 metrics"""
        report = []
        report.append("=" * 80)
        report.append("UNIFIED TRADING ENGINE PERFORMANCE REPORT")
        report.append("=" * 80)
        
        # Engine Overview
        report.append("ENGINE OVERVIEW")
        report.append("-" * 40)
        report.append(f"Engine ID: {self.config.engine_id}")
        report.append(f"Trading Mode: {self.config.trading_mode.value}")
        report.append(f"Status: {self.status.value}")
        report.append(f"Total Cycles: {self._cycle_count}")
        report.append(f"Success Rate: {self._successful_cycles / self._cycle_count * 100 if self._cycle_count > 0 else 0:.1f}%")
        report.append(f"Active Strategies: {len(self._strategy_instances)}")
        report.append("")
        
        # Phase 2 Performance Features
        report.append("PHASE 2 PERFORMANCE FEATURES")
        report.append("-" * 40)
        report.append(f"Hot Path Optimization: {'✅ Enabled' if self.config.enable_hot_path_optimization else '❌ Disabled'}")
        report.append(f"Performance Monitoring: {'✅ Enabled' if self.config.enable_performance_monitoring else '❌ Disabled'}")
        report.append(f"Batch Processing: {'✅ Enabled' if self.config.enable_batch_processing else '❌ Disabled'}")
        report.append(f"Memory Optimization: {'✅ Enabled' if self.config.enable_memory_optimization else '❌ Disabled'}")
        report.append(f"Object Pooling: {'✅ Enabled' if self.config.enable_object_pooling else '❌ Disabled'}")
        report.append(f"GC Optimization: {'✅ Enabled' if self.config.enable_gc_optimization else '❌ Disabled'}")
        report.append(f"Async Optimization: {'✅ Enabled' if self.config.enable_async_optimization else '❌ Disabled'}")
        report.append(f"Event-Driven Updates: {'✅ Enabled' if self.config.enable_event_driven_updates else '❌ Disabled'}")
        report.append(f"Caching: {'✅ Enabled' if self.config.enable_caching else '❌ Disabled'}")
        report.append("")
        
        # Hot Path Performance (if monitoring enabled)
        if self.config.enable_performance_monitoring:
            report.append("HOT PATH PERFORMANCE")
            report.append("-" * 40)
            hot_path_report = performance_monitor.get_performance_report()
            report.append(hot_path_report)
            report.append("")
            
            # Cache Statistics
            report.append("CACHE PERFORMANCE")
            report.append("-" * 40)
            cache_stats = get_cache_statistics()
            for cache_name, stats in cache_stats.items():
                report.append(f"📦 {cache_name}:")
                report.append(f"  • Size: {stats['size']}/{stats['max_size']}")
                report.append(f"  • Hit Rate: {stats['hit_rate']:.1%}")
                report.append(f"  • Hits/Misses: {stats['hits']}/{stats['misses']}")
                report.append(f"  • Evictions: {stats['evictions']}")
                report.append("")
            
            # Memory Management (if enabled)
            if self.config.enable_object_pooling and self._pool_manager:
                report.append("MEMORY MANAGEMENT")
                report.append("-" * 40)
                memory_report = self._pool_manager.get_memory_report()
                report.append(memory_report)
                report.append("")
            
            # Async Performance (if enabled)
            if self.config.enable_async_optimization and self.config.enable_async_monitoring:
                report.append("ASYNC PERFORMANCE")
                report.append("-" * 40)
                async_report = get_async_performance_report()
                report.append(async_report)
                report.append("")
        
        # Strategy Performance
        report.append("STRATEGY PERFORMANCE")
        report.append("-" * 40)
        for strategy_id in self._strategy_instances.keys():
            strategy_metrics = self.get_strategy_metrics(strategy_id)
            if strategy_metrics:
                report.append(f"📊 {strategy_id}:")
                report.append(f"  • Type: {strategy_metrics.get('strategy_type', 'Unknown')}")
                report.append(f"  • Status: Active")
                report.append("")
        
        report.append("=" * 80)
        return "\n".join(report)
    
    def clear_performance_caches(self) -> None:
        """Clear all performance caches"""
        if self.config.enable_caching:
            clear_all_caches()
            self.logger.info("🧹 Performance caches cleared")
    
    def reset_performance_metrics(self) -> None:
        """Reset all performance metrics"""
        if self.config.enable_performance_monitoring:
            performance_monitor.reset_metrics()
            self._cycle_count = 0
            self._successful_cycles = 0
            self._failed_cycles = 0
            self._total_processing_time = 0.0
            self.logger.info("🔄 Performance metrics reset")
    
    async def shutdown(self):
        """Shutdown engine gracefully with Phase 2 cleanup"""
        self.logger.info("🛑 Shutting down UnifiedTradingEngine (Phase 2 Enhanced)")
        self.status = EngineStatus.SHUTDOWN
        
        # Phase 2 cleanup
        if self.config.enable_performance_monitoring:
            # Generate final performance report
            final_report = self.get_detailed_performance_report()
            self.logger.info(f"Final Performance Report:\n{final_report}")
        
        # Clear caches and cleanup resources
        self.clear_performance_caches()
        
        # Cleanup batch processor
        if hasattr(batch_processor, 'shutdown'):
            batch_processor.shutdown()
        
        # Phase 2 Batch 2: Memory management cleanup
        if self.config.enable_object_pooling and self._pool_manager:
            # Generate final memory report
            final_memory_report = self._pool_manager.get_memory_report()
            self.logger.info(f"Final Memory Report:\n{final_memory_report}")
            
            # Cleanup memory resources
            cleanup_memory_resources()
        
        # Phase 2 Batch 3: Async optimization cleanup
        if self.config.enable_async_optimization:
            try:
                # Generate final async performance report
                final_async_report = get_async_performance_report()
                self.logger.info(f"Final Async Performance Report:\n{final_async_report}")
                
                # Cleanup async resources
                await cleanup_async_resources()
                self.logger.info("🚀 Async optimization resources cleaned up")
            except Exception as e:
                self.logger.error(f"❌ Error during async cleanup: {e}")
        
        self.logger.info("✅ Engine shutdown complete (Phase 2 Fully Optimized)")
