#!/usr/bin/env python3
"""
Multi-Strategy Coordination Framework - Rule 5 Implementation
============================================================

Advanced multi-strategy coordination with:
- Signal aggregation across multiple strategies
- Conflict resolution between competing signals
- Strategy performance attribution
- Dynamic strategy weighting
- Risk-aware signal processing

Author: StatArb_Gemini Multi-Strategy Team
Version: 1.0.0 (Production Ready)
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd

# Import ISystemComponent for orchestrator integration
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
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

# Import canonical types from type_definitions (Single Source of Truth)
from ...type_definitions.strategy import StrategyType, SignalType

logger = logging.getLogger(__name__)

# SignalType imported from type_definitions.strategy (canonical source)


class ConflictResolutionMethod(Enum):
    """Conflict resolution methods"""
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    STRATEGY_WEIGHTED = "strategy_weighted"
    MAJORITY_VOTE = "majority_vote"
    HIGHEST_CONFIDENCE = "highest_confidence"
    RISK_ADJUSTED = "risk_adjusted"


@dataclass
class EnhancedSignal:
    """Enhanced trading signal with metadata"""
    signal_id: str
    symbol: str
    signal_type: SignalType
    confidence: float
    quantity: float
    timestamp: datetime
    strategy_id: str
    strategy_type: str
    price: Optional[float] = None
    # CRITICAL FIX: Add position sizing parameters for percentage-based sizing
    target_weight: Optional[float] = None  # Portfolio weight (e.g., 0.02 = 2%)
    quantity_type: str = "ABSOLUTE"  # "PERCENTAGE" or "ABSOLUTE"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def copy(self) -> 'EnhancedSignal':
        """Create a copy of the signal"""
        return EnhancedSignal(
            signal_id=self.signal_id,
            symbol=self.symbol,
            signal_type=self.signal_type,
            confidence=self.confidence,
            quantity=self.quantity,
            timestamp=self.timestamp,
            strategy_id=self.strategy_id,
            strategy_type=self.strategy_type,
            price=self.price,
            target_weight=self.target_weight,
            quantity_type=self.quantity_type,
            metadata=self.metadata.copy()
        )


@dataclass
class StrategyRegistration:
    """Strategy registration information"""
    strategy_id: str
    strategy_instance: Any
    strategy_type: StrategyType
    weight: float
    priority: int
    allocation_pct: float
    max_positions: int
    risk_limit: float
    is_active: bool = True
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class MultiStrategySignalAggregator(ISystemComponent):
    """
    Advanced signal aggregation across multiple strategies
    
    Features:
    - Multi-strategy signal collection
    - Weighted signal aggregation
    - Performance-based dynamic weighting
    - Risk-aware signal processing
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        
        # Strategy management
        self.registered_strategies: Dict[str, StrategyRegistration] = {}
        self.strategy_weights: Dict[str, float] = {}
        self.strategy_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Signal processing
        self.signal_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.aggregated_signals: List[EnhancedSignal] = []
        
        # Configuration
        self.max_concurrent_strategies = self.config.get('max_concurrent_strategies', 10)
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.6)
        self.enable_dynamic_weighting = self.config.get('enable_dynamic_weighting', False)  # Disabled by default for stability
        
        self.logger.info(f"🎯 MultiStrategySignalAggregator initialized: {self.component_id}")
    
    async def initialize(self) -> bool:
        """Initialize signal aggregator"""
        try:
            self.logger.info("🔄 Initializing Multi-Strategy Signal Aggregator...")
            self.is_initialized = True
            self.logger.info("✅ Multi-Strategy Signal Aggregator initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Signal Aggregator initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start signal aggregator"""
        if not self.is_initialized:
            return False
        
        try:
            self.logger.info("🚀 Starting Multi-Strategy Signal Aggregator...")
            self.is_operational = True
            self.logger.info("✅ Multi-Strategy Signal Aggregator started")
            return True
        except Exception as e:
            self.logger.error(f"❌ Signal Aggregator start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop signal aggregator"""
        try:
            self.logger.info("🛑 Stopping Multi-Strategy Signal Aggregator...")
            self.is_operational = False
            self.logger.info("✅ Multi-Strategy Signal Aggregator stopped")
            return True
        except Exception as e:
            self.logger.error(f"❌ Signal Aggregator stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for signal aggregator"""
        return {
            'healthy': self.is_operational,
            'component_type': 'MultiStrategySignalAggregator',
            'component_id': self.component_id,
            'registered_strategies': len(self.registered_strategies),
            'active_strategies': len([s for s in self.registered_strategies.values() if s.is_active]),
            'signals_processed': sum(len(history) for history in self.signal_history.values())
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get aggregator status"""
        return {
            'component_id': self.component_id,
            'component_type': 'MultiStrategySignalAggregator',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'registered_strategies': len(self.registered_strategies),
            'strategy_weights': self.strategy_weights
        }
    
    async def register_strategy(self, strategy_id: str, strategy_instance: Any,
                              strategy_type: StrategyType, weight: float = 1.0,
                              priority: int = 1, allocation_pct: float = 0.1,
                              max_positions: int = 5, risk_limit: float = 0.05) -> bool:
        """Register a strategy for coordination"""
        try:
            if len(self.registered_strategies) >= self.max_concurrent_strategies:
                self.logger.warning(f"Maximum strategies ({self.max_concurrent_strategies}) already registered")
                return False
            
            registration = StrategyRegistration(
                strategy_id=strategy_id,
                strategy_instance=strategy_instance,
                strategy_type=strategy_type,
                weight=weight,
                priority=priority,
                allocation_pct=allocation_pct,
                max_positions=max_positions,
                risk_limit=risk_limit
            )
            
            self.registered_strategies[strategy_id] = registration
            self.strategy_weights[strategy_id] = weight
            
            # Initialize performance tracking
            self.strategy_performance[strategy_id] = {
                'total_signals': 0,
                'successful_signals': 0,
                'win_rate': 0.0,
                'avg_confidence': 0.0,
                'performance_score': 1.0
            }
            
            # Configure strategy callbacks if supported
            if hasattr(strategy_instance, 'set_signal_callback'):
                strategy_instance.set_signal_callback(
                    lambda signals, sid=strategy_id: self._receive_strategy_signals(sid, signals)
                )
            
            self.logger.info(f"✅ Strategy registered: {strategy_id} ({strategy_type.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Strategy registration failed: {e}")
            return False
    
    async def unregister_strategy(self, strategy_id: str) -> bool:
        """Unregister a strategy"""
        try:
            if strategy_id in self.registered_strategies:
                del self.registered_strategies[strategy_id]
                del self.strategy_weights[strategy_id]
                if strategy_id in self.strategy_performance:
                    del self.strategy_performance[strategy_id]
                
                self.logger.info(f"✅ Strategy unregistered: {strategy_id}")
                return True
            else:
                self.logger.warning(f"Strategy not found for unregistration: {strategy_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Strategy unregistration failed: {e}")
            return False
    
    async def collect_all_signals(self, market_data) -> Dict[str, List[EnhancedSignal]]:
        """
        Collect signals from all registered strategies
        
        Args:
            market_data: Either pd.DataFrame or Dict[str, pd.DataFrame]
                - If DataFrame: will be converted to dict format for enhanced strategies
                - If Dict: passed directly to strategies
        """
        strategy_signals = {}
        
        # Normalize market_data to dict format for enhanced strategies
        if isinstance(market_data, pd.DataFrame):
            # Skip empty DataFrames
            if market_data.empty:
                self.logger.debug("collect_all_signals received empty DataFrame, skipping")
                return {}
            
            # Extract symbol from DataFrame if available
            if 'symbol' in market_data.columns:
                symbols = market_data['symbol'].unique()
                enriched_data = {
                    symbol: market_data[market_data['symbol'] == symbol].copy()
                    for symbol in symbols
                }
            else:
                # No symbol column - try to infer from first registered strategy's config
                inferred_symbol = None
                for _, registration in self.registered_strategies.items():
                    if hasattr(registration.strategy_instance, 'config'):
                        config = registration.strategy_instance.config
                        if hasattr(config, 'symbols') and config.symbols:
                            inferred_symbol = config.symbols[0]
                            break
                
                if inferred_symbol:
                    enriched_data = {inferred_symbol: market_data}
                else:
                    # Last resort fallback
                    self.logger.debug("No symbol info available, using fallback key")
                    enriched_data = {'DEFAULT': market_data}
        elif isinstance(market_data, dict):
            enriched_data = market_data
        else:
            self.logger.warning(f"Unexpected market_data type: {type(market_data)}")
            return {}
        
        for strategy_id, registration in self.registered_strategies.items():
            if not registration.is_active:
                continue
            
            try:
                # Generate signals from strategy
                if hasattr(registration.strategy_instance, 'generate_signals'):
                    raw_signals = await registration.strategy_instance.generate_signals(enriched_data)
                    
                    # Convert to enhanced signals
                    enhanced_signals = []
                    for signal in raw_signals:
                        enhanced_signal = self._convert_to_enhanced_signal(signal, strategy_id, registration)
                        if enhanced_signal and enhanced_signal.confidence >= self.min_confidence_threshold:
                            enhanced_signals.append(enhanced_signal)
                    
                    strategy_signals[strategy_id] = enhanced_signals
                    
                    # Update performance tracking
                    await self._update_strategy_performance(strategy_id, enhanced_signals)
                    
            except Exception as e:
                self.logger.error(f"❌ Signal collection failed for {strategy_id}: {e}")
                strategy_signals[strategy_id] = []
        
        return strategy_signals
    
    async def aggregate_strategy_signals(self, strategy_signals: Dict[str, List[EnhancedSignal]]) -> List[EnhancedSignal]:
        """Aggregate signals from multiple strategies with conflict resolution"""
        try:
            # Step 1: Collect all signals with weights
            weighted_signals = []
            for strategy_id, signals in strategy_signals.items():
                if strategy_id not in self.strategy_weights:
                    continue
                
                strategy_weight = self.strategy_weights[strategy_id]
                
                # DEBUG: Log strategy weight
                self.logger.debug(f"📊 Strategy {strategy_id}: weight={strategy_weight}, signals={len(signals)}")
                
                # Apply dynamic weighting if enabled
                if self.enable_dynamic_weighting:
                    performance_multiplier = self.strategy_performance[strategy_id].get('performance_score', 1.0)
                    strategy_weight *= performance_multiplier
                
                for signal in signals:
                    weighted_signal = signal.copy()
                    # Store original confidence before weighting
                    weighted_signal.metadata['original_confidence'] = signal.confidence
                    weighted_signal.metadata['strategy_weight'] = strategy_weight
                    # Only apply weight if multiple strategies (preserve confidence for single strategy)
                    if len(strategy_signals) > 1:
                        weighted_signal.confidence *= strategy_weight
                    weighted_signals.append(weighted_signal)
            
            # Step 2: Group signals by symbol
            signals_by_symbol = defaultdict(list)
            for signal in weighted_signals:
                signals_by_symbol[signal.symbol].append(signal)
            
            # Step 3: Resolve conflicts and aggregate
            aggregated_signals = []
            for symbol, symbol_signals in signals_by_symbol.items():
                resolved_signal = await self._resolve_signal_conflicts(symbol_signals)
                if resolved_signal:
                    aggregated_signals.append(resolved_signal)
            
            # Store aggregated signals
            self.aggregated_signals = aggregated_signals
            
            self.logger.info(f"📊 Aggregated {len(aggregated_signals)} signals from {len(strategy_signals)} strategies")
            return aggregated_signals
            
        except Exception as e:
            self.logger.error(f"❌ Signal aggregation failed: {e}")
            return []
    
    def _convert_to_enhanced_signal(self, raw_signal: Any, strategy_id: str, 
                                  registration: StrategyRegistration) -> Optional[EnhancedSignal]:
        """Convert raw signal to enhanced signal"""
        try:
            # Handle different signal formats
            if hasattr(raw_signal, 'signal_type'):
                st = raw_signal.signal_type
                # Handle both enum and string formats
                if isinstance(st, SignalType):
                    signal_type = st
                elif isinstance(st, str):
                    signal_type = SignalType(st.lower())
                else:
                    signal_type = SignalType(str(st).lower())
            elif hasattr(raw_signal, 'action'):
                action = raw_signal.action
                if isinstance(action, str):
                    signal_type = SignalType(action.lower())
                else:
                    signal_type = SignalType(str(action).lower())
            else:
                return None
            
            enhanced_signal = EnhancedSignal(
                signal_id=f"{strategy_id}_{uuid.uuid4().hex[:8]}",
                symbol=getattr(raw_signal, 'symbol', 'UNKNOWN'),
                signal_type=signal_type,
                confidence=getattr(raw_signal, 'confidence', 0.5),
                quantity=getattr(raw_signal, 'quantity', 0.0),
                timestamp=getattr(raw_signal, 'timestamp', datetime.now()),
                strategy_id=strategy_id,
                strategy_type=registration.strategy_type.value,
                price=getattr(raw_signal, 'price', None),
                # CRITICAL FIX: Preserve position sizing parameters
                target_weight=getattr(raw_signal, 'target_weight', None),
                quantity_type=getattr(raw_signal, 'quantity_type', 'ABSOLUTE'),
                metadata={
                    'strategy_priority': registration.priority,
                    'strategy_allocation': registration.allocation_pct,
                    'risk_limit': registration.risk_limit
                }
            )
            
            return enhanced_signal
            
        except Exception as e:
            self.logger.error(f"Signal conversion failed: {e}")
            return None
    
    async def _receive_strategy_signals(self, strategy_id: str, signals: List[Any]):
        """Receive signals from strategy callback"""
        try:
            # Store signals in history
            for signal in signals:
                self.signal_history[strategy_id].append({
                    'timestamp': datetime.now(),
                    'signal': signal
                })
            
            self.logger.debug(f"📨 Received {len(signals)} signals from {strategy_id}")
            
        except Exception as e:
            self.logger.error(f"Signal reception failed for {strategy_id}: {e}")
    
    async def _update_strategy_performance(self, strategy_id: str, signals: List[EnhancedSignal]):
        """Update strategy performance metrics"""
        try:
            performance = self.strategy_performance[strategy_id]
            
            # Update signal counts
            performance['total_signals'] += len(signals)
            
            # Update confidence metrics
            if signals:
                confidences = [s.confidence for s in signals]
                performance['avg_confidence'] = np.mean(confidences)
            
            # Calculate performance score (placeholder - would use actual trading results)
            win_rate = performance.get('win_rate', 0.5)
            avg_confidence = performance.get('avg_confidence', 0.5)
            performance['performance_score'] = (win_rate * 0.6) + (avg_confidence * 0.4)
            
            # Update dynamic weights if enabled
            if self.enable_dynamic_weighting and strategy_id in self.strategy_weights:
                base_weight = self.registered_strategies[strategy_id].weight
                performance_multiplier = performance['performance_score']
                self.strategy_weights[strategy_id] = base_weight * performance_multiplier
            
        except Exception as e:
            self.logger.error(f"Performance update failed for {strategy_id}: {e}")

    async def _resolve_signal_conflicts(self, signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve signal conflicts using SignalConflictResolver"""
        # Initialize conflict resolver if not exists
        if not hasattr(self, 'conflict_resolver') or self.conflict_resolver is None:
            self.conflict_resolver = SignalConflictResolver()
            await self.conflict_resolver.initialize()
            await self.conflict_resolver.start()
        
        return await self.conflict_resolver.resolve_conflicts(signals)


class SignalConflictResolver(ISystemComponent):
    """
    Advanced signal conflict resolution
    
    Features:
    - Multiple resolution methods
    - Risk-aware conflict resolution
    - Strategy priority consideration
    - Confidence-based weighting
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        
        # Configuration
        self.default_resolution_method = ConflictResolutionMethod(
            self.config.get('resolution_method', 'confidence_weighted')
        )
        self.conflict_threshold = self.config.get('conflict_threshold', 0.1)  # 10% difference threshold
        
        # Conflict tracking
        self.conflict_history = []
        self.resolution_stats = defaultdict(int)
        
        self.logger.info(f"⚖️ SignalConflictResolver initialized: {self.component_id}")
    
    async def initialize(self) -> bool:
        """Initialize conflict resolver"""
        try:
            self.logger.info("🔄 Initializing Signal Conflict Resolver...")
            self.is_initialized = True
            self.logger.info("✅ Signal Conflict Resolver initialized")
            return True
        except Exception as e:
            self.logger.error(f"❌ Conflict Resolver initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start conflict resolver"""
        if not self.is_initialized:
            return False
        
        try:
            self.logger.info("🚀 Starting Signal Conflict Resolver...")
            self.is_operational = True
            self.logger.info("✅ Signal Conflict Resolver started")
            return True
        except Exception as e:
            self.logger.error(f"❌ Conflict Resolver start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop conflict resolver"""
        try:
            self.logger.info("🛑 Stopping Signal Conflict Resolver...")
            self.is_operational = False
            self.logger.info("✅ Signal Conflict Resolver stopped")
            return True
        except Exception as e:
            self.logger.error(f"❌ Conflict Resolver stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for conflict resolver"""
        return {
            'healthy': self.is_operational,
            'component_type': 'SignalConflictResolver',
            'component_id': self.component_id,
            'conflicts_resolved': len(self.conflict_history),
            'resolution_method': self.default_resolution_method.value
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get resolver status"""
        return {
            'component_id': self.component_id,
            'component_type': 'SignalConflictResolver',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'resolution_method': self.default_resolution_method.value,
            'resolution_stats': dict(self.resolution_stats)
        }
    
    async def resolve_conflicts(self, signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve conflicts between signals for the same symbol"""
        if not signals:
            return None
        
        if len(signals) == 1:
            return signals[0]
        
        try:
            # Separate by signal type
            buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
            sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
            hold_signals = [s for s in signals if s.signal_type == SignalType.HOLD]
            
            # Record conflict
            conflict_record = {
                'timestamp': datetime.now(),
                'symbol': signals[0].symbol,
                'total_signals': len(signals),
                'buy_signals': len(buy_signals),
                'sell_signals': len(sell_signals),
                'hold_signals': len(hold_signals)
            }
            self.conflict_history.append(conflict_record)
            
            # Resolution logic
            if buy_signals and sell_signals:
                # Conflicting signals - use resolution method
                resolved_signal = await self._resolve_conflicting_signals(buy_signals, sell_signals)
                self.resolution_stats['conflicting_resolved'] += 1
                return resolved_signal
            elif buy_signals:
                # Aggregate buy signals
                resolved_signal = await self._aggregate_same_direction_signals(buy_signals)
                self.resolution_stats['buy_aggregated'] += 1
                return resolved_signal
            elif sell_signals:
                # Aggregate sell signals
                resolved_signal = await self._aggregate_same_direction_signals(sell_signals)
                self.resolution_stats['sell_aggregated'] += 1
                return resolved_signal
            else:
                # Only hold signals
                resolved_signal = hold_signals[0] if hold_signals else None
                self.resolution_stats['hold_selected'] += 1
                return resolved_signal
                
        except Exception as e:
            self.logger.error(f"Conflict resolution failed: {e}")
            return signals[0] if signals else None
    
    async def _resolve_conflicting_signals(self, buy_signals: List[EnhancedSignal], 
                                         sell_signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve conflicting buy/sell signals"""
        
        if self.default_resolution_method == ConflictResolutionMethod.CONFIDENCE_WEIGHTED:
            return await self._resolve_by_confidence_weighted(buy_signals, sell_signals)
        elif self.default_resolution_method == ConflictResolutionMethod.STRATEGY_WEIGHTED:
            return await self._resolve_by_strategy_weighted(buy_signals, sell_signals)
        elif self.default_resolution_method == ConflictResolutionMethod.HIGHEST_CONFIDENCE:
            return await self._resolve_by_highest_confidence(buy_signals, sell_signals)
        elif self.default_resolution_method == ConflictResolutionMethod.MAJORITY_VOTE:
            return await self._resolve_by_majority_vote(buy_signals, sell_signals)
        else:
            # Default to confidence weighted
            return await self._resolve_by_confidence_weighted(buy_signals, sell_signals)
    
    async def _resolve_by_confidence_weighted(self, buy_signals: List[EnhancedSignal], 
                                            sell_signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve using confidence-weighted approach"""
        
        # Calculate weighted confidence for each direction
        buy_confidence = sum(s.confidence * s.metadata.get('strategy_weight', 1.0) for s in buy_signals)
        sell_confidence = sum(s.confidence * s.metadata.get('strategy_weight', 1.0) for s in sell_signals)
        
        # Choose direction with higher weighted confidence
        if buy_confidence > sell_confidence * (1 + self.conflict_threshold):
            return await self._aggregate_same_direction_signals(buy_signals)
        elif sell_confidence > buy_confidence * (1 + self.conflict_threshold):
            return await self._aggregate_same_direction_signals(sell_signals)
        else:
            # Too close - generate hold signal
            return self._create_hold_signal(buy_signals[0].symbol, buy_signals + sell_signals)
    
    async def _resolve_by_strategy_weighted(self, buy_signals: List[EnhancedSignal], 
                                          sell_signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve using strategy weights"""
        
        buy_weight = sum(s.metadata.get('strategy_weight', 1.0) for s in buy_signals)
        sell_weight = sum(s.metadata.get('strategy_weight', 1.0) for s in sell_signals)
        
        if buy_weight > sell_weight:
            return await self._aggregate_same_direction_signals(buy_signals)
        elif sell_weight > buy_weight:
            return await self._aggregate_same_direction_signals(sell_signals)
        else:
            return self._create_hold_signal(buy_signals[0].symbol, buy_signals + sell_signals)
    
    async def _resolve_by_highest_confidence(self, buy_signals: List[EnhancedSignal], 
                                           sell_signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve by selecting highest confidence signal"""
        
        all_signals = buy_signals + sell_signals
        highest_confidence_signal = max(all_signals, key=lambda s: s.confidence)
        
        if highest_confidence_signal.signal_type == SignalType.BUY:
            return await self._aggregate_same_direction_signals(buy_signals)
        else:
            return await self._aggregate_same_direction_signals(sell_signals)
    
    async def _resolve_by_majority_vote(self, buy_signals: List[EnhancedSignal], 
                                      sell_signals: List[EnhancedSignal]) -> Optional[EnhancedSignal]:
        """Resolve by majority vote"""
        
        if len(buy_signals) > len(sell_signals):
            return await self._aggregate_same_direction_signals(buy_signals)
        elif len(sell_signals) > len(buy_signals):
            return await self._aggregate_same_direction_signals(sell_signals)
        else:
            return self._create_hold_signal(buy_signals[0].symbol, buy_signals + sell_signals)
    
    async def _aggregate_same_direction_signals(self, signals: List[EnhancedSignal]) -> EnhancedSignal:
        """Aggregate signals in the same direction"""
        if not signals:
            return None
        
        # Weighted average of confidence and quantity
        total_weight = sum(s.metadata.get('strategy_weight', 1.0) for s in signals)
        weighted_confidence = sum(s.confidence * s.metadata.get('strategy_weight', 1.0) for s in signals) / total_weight
        weighted_quantity = sum(s.quantity * s.metadata.get('strategy_weight', 1.0) for s in signals) / total_weight
        
        # Create aggregated signal
        aggregated_signal = EnhancedSignal(
            signal_id=f"aggregated_{uuid.uuid4().hex[:8]}",
            symbol=signals[0].symbol,
            signal_type=signals[0].signal_type,
            confidence=min(weighted_confidence, 1.0),  # Cap at 1.0
            quantity=weighted_quantity,
            timestamp=max(s.timestamp for s in signals),  # Use latest timestamp
            strategy_id="multi_strategy_aggregated",
            strategy_type="aggregated",
            metadata={
                'aggregated_from': [s.strategy_id for s in signals],
                'contributing_strategies': len(signals),
                'aggregation_method': 'weighted_average',
                'original_confidences': [s.confidence for s in signals],
                'resolution_method': self.default_resolution_method.value
            }
        )
        
        return aggregated_signal
    
    def _create_hold_signal(self, symbol: str, contributing_signals: List[EnhancedSignal]) -> EnhancedSignal:
        """Create a hold signal when conflicts cannot be resolved"""
        
        return EnhancedSignal(
            signal_id=f"hold_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            signal_type=SignalType.HOLD,
            confidence=0.5,
            quantity=0.0,
            timestamp=datetime.now(),
            strategy_id="conflict_resolver",
            strategy_type="hold",
            metadata={
                'resolution_reason': 'conflicting_signals_unresolvable',
                'contributing_signals': len(contributing_signals),
                'conflict_threshold': self.conflict_threshold,
                'resolution_method': self.default_resolution_method.value
            }
        )
