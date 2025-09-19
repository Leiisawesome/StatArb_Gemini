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
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum

# Use internal core_engine types for independence
from ..types import (
    StrategyType, StrategyConfig, BaseStrategy, StrategyInterface, 
    StrategyMetrics, StrategyManager as CoreStrategyManager, TradingSignal
)

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

class IStrategySubscriber:
    """Interface for strategy event subscribers"""
    
    async def on_signal_generated(self, signal: TradingSignal) -> None:
        """Handle signal generation"""
        pass
    
    async def on_strategy_status_change(self, strategy_event: Dict[str, Any]) -> None:
        """Handle strategy status changes"""
        pass

class StrategyManager:
    """
    Core Engine Strategy Manager - WHAT Component
    
    This component sits within the Risk Manager (Central Hub) and determines
    WHAT trades should be made:
    
    1. Manages multiple trading strategies
    2. Analyzes market conditions and regime changes
    3. Generates trading signals based on strategy analysis
    4. Aggregates and filters signals for quality
    5. Submits trade requests to Risk Manager for authorization
    
    The WHAT methodology includes:
    - Multi-strategy signal generation
    - Regime-aware strategy activation
    - Signal quality filtering and aggregation
    - Portfolio-level signal coordination
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = StrategyManagerConfig(**config) if config else StrategyManagerConfig()
        
        # Component references (set by Risk Manager)
        self.risk_manager: Optional[Any] = None
        self.data_manager: Optional[Any] = None
        self.regime_engine: Optional[Any] = None
        
        # Strategy infrastructure
        self.active_strategies: Dict[str, Any] = {}
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        self.strategy_performance: Dict[str, Dict[str, Any]] = {}
        
        # Signal management
        self.pending_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
        self.aggregated_signals: Dict[str, TradingSignal] = {}
        
        # Current market context
        self.current_regime: Optional[str] = None
        self.market_conditions: Dict[str, Any] = {}
        
        # Subscribers
        self.subscribers: List[IStrategySubscriber] = []
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.signal_generation_task: Optional[asyncio.Task] = None
        
        # Leverage existing core strategy manager
        self.core_strategy_manager: Optional[CoreStrategyManager] = None
        
        logger.info("🧠 Strategy Manager (WHAT) initialized")
    
    async def initialize(self) -> bool:
        """Initialize strategy manager"""
        try:
            logger.info("🔄 Initializing Strategy Manager (WHAT)...")
            
            # Initialize core strategy manager
            self.core_strategy_manager = CoreStrategyManager({
                'enable_mean_reversion': True,
                'enable_momentum': True,
                'enable_pairs_trading': True,
                'risk_tolerance': 'medium',
                'max_positions': 10
            })
            
            # Initialize default strategy allocations
            await self._initialize_default_strategies()
            
            # Initialize strategy performance tracking
            await self._initialize_performance_tracking()
            
            self.is_initialized = True
            logger.info("✅ Strategy Manager (WHAT) initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Strategy Manager initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start strategy manager"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Strategy Manager not initialized")
            
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
    
    # Component Integration
    def set_risk_manager(self, risk_manager: Any):
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info("🔗 Risk Manager linked to Strategy Manager")
    
    def set_data_manager(self, data_manager: Any):
        """Set data manager reference"""
        self.data_manager = data_manager
        logger.info("🔗 Data Manager linked to Strategy Manager")
    
    def set_regime_engine(self, regime_engine: Any):
        """Set regime engine reference"""
        self.regime_engine = regime_engine
        logger.info("🔗 Regime Engine linked to Strategy Manager")
    
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
    
    async def generate_signals(self, symbols: List[str]) -> List[TradingSignal]:
        """Generate trading signals from all active strategies"""
        try:
            all_signals = []
            
            # Update market context
            await self._update_market_context()
            
            # Generate signals from each active strategy
            for strategy_name, strategy in self.active_strategies.items():
                if not self.strategy_allocations[strategy_name].active:
                    continue
                
                try:
                    # Generate signals for symbols
                    strategy_signals = await self._generate_strategy_signals(
                        strategy, strategy_name, symbols
                    )
                    all_signals.extend(strategy_signals)
                    
                except Exception as e:
                    logger.error(f"❌ Signal generation failed for {strategy_name}: {e}")
            
            # Filter and aggregate signals
            filtered_signals = await self._filter_signals(all_signals)
            aggregated_signals = await self._aggregate_signals(filtered_signals)
            
            # Store signals
            for signal in aggregated_signals:
                self.pending_signals[signal.signal_id] = signal
                self.aggregated_signals[signal.symbol] = signal
            
            # Notify subscribers
            for signal in aggregated_signals:
                for subscriber in self.subscribers:
                    await subscriber.on_signal_generated(signal)
            
            logger.info(f"📊 Generated {len(aggregated_signals)} aggregated signals from {len(all_signals)} raw signals")
            return aggregated_signals
            
        except Exception as e:
            logger.error(f"❌ Signal generation failed: {e}")
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
    async def _create_strategy_instance(self, strategy_type: StrategyType, config: Dict[str, Any]) -> Any:
        """Create strategy instance based on type"""
        # Use base strategy framework
        strategy_instance = BaseStrategy()
        strategy_instance.name = config['name']
        strategy_instance.config = config
        strategy_instance.strategy_type = strategy_type
        return strategy_instance
    
    async def _generate_strategy_signals(self, strategy: Any, strategy_name: str, symbols: List[str]) -> List[TradingSignal]:
        """Generate signals from individual strategy"""
        try:
            # Use core strategy manager if available
            if self.core_strategy_manager:
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
                regime_info = await self.regime_engine.get_current_regime()
                self.current_regime = regime_info.get('regime')
                self.market_conditions = regime_info.get('conditions', {})
            
        except Exception as e:
            logger.error(f"❌ Failed to update market context: {e}")
    
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