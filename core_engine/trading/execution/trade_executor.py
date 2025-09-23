"""
Execution Engine - Trade Executor
High-performance trade execution with advanced algorithms and real-time optimization
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import uuid
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class TradeExecutionAlgorithm(Enum):
    """Trade execution algorithms"""
    TWAP = "twap"  # Time Weighted Average Price
    VWAP = "vwap"  # Volume Weighted Average Price
    POV = "pov"    # Percentage of Volume
    IS = "implementation_shortfall"  # Implementation Shortfall
    ICEBERG = "iceberg"
    SNIPER = "sniper"
    GUERRILLA = "guerrilla"
    ADAPTIVE = "adaptive"
    MARKET = "market"
    LIMIT = "limit"


class TradeStatus(Enum):
    """Trade execution status"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"


class RiskLevel(Enum):
    """Risk tolerance levels"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


@dataclass
class TradeExecutionRequest:
    """Trade execution request with algorithmic parameters"""
    # Basic trade information
    trade_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    
    # Execution algorithm
    algorithm: TradeExecutionAlgorithm = TradeExecutionAlgorithm.TWAP
    
    # Timing parameters
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    
    # Algorithm-specific parameters
    participation_rate: float = 0.1  # For POV (10%)
    risk_aversion: float = 0.5       # For IS (0.5 = balanced)
    price_limit: Optional[float] = None
    
    # Market conditions
    urgency_level: int = 5  # 1-10 scale
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    # Advanced settings
    allow_dark_pools: bool = True
    min_fill_size: Optional[float] = None
    max_slice_size: Optional[float] = None
    randomize_timing: bool = True
    
    # Constraints
    max_market_impact: float = 0.01  # 1%
    max_slippage: float = 0.005      # 0.5%
    
    # Callbacks
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TradeExecutionResult:
    """Trade execution result"""
    trade_id: str
    symbol: str
    quantity: float
    executed_quantity: float
    average_price: float
    total_cost: float
    status: str


@dataclass
class TradeSlice:
    """Individual trade slice execution"""
    slice_id: str
    trade_id: str
    symbol: str
    side: str
    target_quantity: float
    scheduled_time: datetime  # Moved here - required fields first
    
    # Optional slice parameters with defaults
    executed_quantity: float = 0.0
    remaining_quantity: float = 0.0
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    
    # Pricing
    limit_price: Optional[float] = None
    avg_execution_price: float = 0.0
    
    # Performance
    slippage: float = 0.0
    market_impact: float = 0.0
    
    # Status
    status: str = "pending"
    error_message: Optional[str] = None


@dataclass
class MarketDataSnapshot:
    """Market data at execution time"""
    symbol: str
    timestamp: datetime
    
    # Price data
    bid: float
    ask: float
    midpoint: float
    last_price: float
    
    # Volume data
    bid_size: float
    ask_size: float
    volume: float
    avg_volume: float
    
    # Spread and volatility
    spread: float
    volatility: float
    
    # Market state
    session_state: str = "OPEN"
    liquidity_score: float = 0.5


class VWAPCalculator:
    """Volume Weighted Average Price calculator"""
    
    def __init__(self, symbol: str, lookback_days: int = 20):
        self.symbol = symbol
        self.lookback_days = lookback_days
        self._volume_profile = {}
        self._historical_data = deque(maxlen=lookback_days * 390)  # 390 minutes per day
    
    def calculate_expected_volume_profile(self, date: datetime) -> Dict[str, float]:
        """Calculate expected volume profile for the day"""
        
        # Mock volume profile (typically U-shaped)
        market_open = datetime.combine(date.date(), datetime.min.time().replace(hour=9, minute=30))
        market_close = datetime.combine(date.date(), datetime.min.time().replace(hour=16, minute=0))
        
        total_minutes = int((market_close - market_open).total_seconds() / 60)
        volume_profile = {}
        
        for minute in range(total_minutes):
            time_pct = minute / total_minutes
            
            # U-shaped volume profile
            if time_pct < 0.5:
                volume_factor = 1.5 - time_pct  # High at open, declining to midday
            else:
                volume_factor = 0.5 + (time_pct - 0.5) * 2  # Rising toward close
            
            timestamp = market_open + timedelta(minutes=minute)
            volume_profile[timestamp.strftime("%H:%M")] = volume_factor
        
        return volume_profile
    
    def get_current_vwap(self) -> float:
        """Get current VWAP"""
        if not self._historical_data:
            return 100.0  # Mock price
        
        total_volume = sum(data['volume'] for data in self._historical_data)
        total_value = sum(data['price'] * data['volume'] for data in self._historical_data)
        
        return total_value / total_volume if total_volume > 0 else 100.0
    
    def update_market_data(self, price: float, volume: float, timestamp: datetime) -> None:
        """Update with new market data"""
        self._historical_data.append({
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        })


class TWAPExecutor:
    """Time Weighted Average Price execution algorithm"""
    
    def __init__(self, trade_request: TradeExecutionRequest):
        self.request = trade_request
        self.slices = []
    
    def generate_execution_schedule(self) -> List[TradeSlice]:
        """Generate TWAP execution schedule"""
        
        start_time = self.request.start_time or datetime.now()
        
        if self.request.end_time:
            duration = self.request.end_time - start_time
        elif self.request.duration_minutes:
            duration = timedelta(minutes=self.request.duration_minutes)
        else:
            duration = timedelta(hours=1)  # Default 1 hour
        
        # Number of slices (typically 5-20 depending on duration)
        num_slices = max(5, min(20, int(duration.total_seconds() / 300)))  # Every 5 minutes
        slice_interval = duration / num_slices
        slice_size = self.request.quantity / num_slices
        
        slices = []
        
        for i in range(num_slices):
            slice_time = start_time + slice_interval * i
            
            # Add randomization if enabled
            if self.request.randomize_timing:
                jitter = np.random.uniform(-0.3, 0.3) * slice_interval.total_seconds()
                slice_time += timedelta(seconds=jitter)
            
            # Randomize slice size slightly
            if self.request.randomize_timing and i < num_slices - 1:
                size_jitter = np.random.uniform(0.8, 1.2)
                current_slice_size = slice_size * size_jitter
            else:
                # Last slice gets remaining quantity
                current_slice_size = self.request.quantity - sum(s.target_quantity for s in slices)
            
            slice = TradeSlice(
                slice_id=f"{self.request.trade_id}_slice_{i+1}",
                trade_id=self.request.trade_id,
                symbol=self.request.symbol,
                side=self.request.side,
                target_quantity=current_slice_size,
                remaining_quantity=current_slice_size,
                scheduled_time=slice_time
            )
            
            slices.append(slice)
        
        self.slices = slices
        return slices


class POVExecutor:
    """Percentage of Volume execution algorithm"""
    
    def __init__(self, trade_request: TradeExecutionRequest):
        self.request = trade_request
        self.volume_tracker = VWAPCalculator(trade_request.symbol)
        self.executed_quantity = 0.0
    
    def calculate_next_slice_size(self, current_volume: float, time_remaining: float) -> float:
        """Calculate next slice size based on market volume"""
        
        target_participation = self.request.participation_rate
        
        # Base slice size from participation rate
        base_slice = current_volume * target_participation
        
        # Adjust based on remaining quantity and time
        remaining_qty = self.request.quantity - self.executed_quantity
        
        if time_remaining > 0:
            urgency_factor = 1.0 / time_remaining  # Higher urgency as time runs out
            base_slice *= (1.0 + urgency_factor * 0.5)
        
        # Cap slice size
        max_slice = remaining_qty * 0.3  # Never more than 30% in one slice
        min_slice = remaining_qty * 0.01  # At least 1% if urgent
        
        return max(min_slice, min(base_slice, max_slice))


class ImplementationShortfallExecutor:
    """Implementation Shortfall execution algorithm"""
    
    def __init__(self, trade_request: TradeExecutionRequest):
        self.request = trade_request
        self.risk_aversion = trade_request.risk_aversion
        self.arrival_price = None
        self.market_impact_model = MarketImpactModel()
    
    def optimize_execution_schedule(self, market_data: MarketDataSnapshot) -> List[TradeSlice]:
        """Optimize execution to minimize implementation shortfall"""
        
        self.arrival_price = market_data.midpoint
        
        # Estimate market impact and timing risk
        total_quantity = self.request.quantity
        volatility = market_data.volatility
        
        # Simple IS optimization (in practice, this would be much more sophisticated)
        duration_hours = (self.request.end_time - self.request.start_time).total_seconds() / 3600
        
        # Optimal execution rate (simplified Almgren-Chriss model)
        if self.risk_aversion > 0:
            decay_rate = np.sqrt(volatility / (self.risk_aversion * duration_hours))
            optimal_rate = decay_rate * np.exp(-decay_rate * np.arange(0, duration_hours, 0.1))
        else:
            # Risk-neutral case
            optimal_rate = np.ones(int(duration_hours * 10)) / (duration_hours * 10)
        
        # Generate slices based on optimal rate
        slices = []
        cumulative_quantity = 0.0
        start_time = self.request.start_time
        
        for i, rate in enumerate(optimal_rate):
            if cumulative_quantity >= total_quantity:
                break
            
            slice_quantity = min(total_quantity * rate, total_quantity - cumulative_quantity)
            slice_time = start_time + timedelta(hours=i * 0.1)
            
            slice = TradeSlice(
                slice_id=f"{self.request.trade_id}_is_slice_{i+1}",
                trade_id=self.request.trade_id,
                symbol=self.request.symbol,
                side=self.request.side,
                target_quantity=slice_quantity,
                remaining_quantity=slice_quantity,
                scheduled_time=slice_time
            )
            
            slices.append(slice)
            cumulative_quantity += slice_quantity
        
        return slices


class MarketImpactModel:
    """Market impact estimation model"""
    
    def __init__(self):
        self.model_params = {
            'temporary_impact_coeff': 0.5,
            'permanent_impact_coeff': 0.3,
            'volatility_factor': 0.8,
            'liquidity_factor': 0.6
        }
    
    def estimate_impact(
        self,
        symbol: str,
        quantity: float,
        execution_rate: float,
        market_data: MarketDataSnapshot
    ) -> Dict[str, float]:
        """Estimate market impact for execution"""
        
        # Normalize quantity by average daily volume
        normalized_quantity = quantity / market_data.avg_volume
        
        # Temporary impact (recovers after execution)
        temporary_impact = (
            self.model_params['temporary_impact_coeff'] *
            normalized_quantity ** 0.5 *
            execution_rate ** 0.25 *
            market_data.volatility
        )
        
        # Permanent impact (information leakage)
        permanent_impact = (
            self.model_params['permanent_impact_coeff'] *
            normalized_quantity ** 0.6 *
            market_data.volatility ** 0.5
        )
        
        # Liquidity adjustment
        liquidity_adjustment = 1.0 / (market_data.liquidity_score + 0.1)
        
        return {
            'temporary_impact': temporary_impact * liquidity_adjustment,
            'permanent_impact': permanent_impact * liquidity_adjustment,
            'total_impact': (temporary_impact + permanent_impact) * liquidity_adjustment
        }


class AdaptiveExecutionEngine:
    """Adaptive execution engine that adjusts strategy based on real-time conditions"""
    
    def __init__(self):
        self.performance_tracker = ExecutionPerformanceTracker()
        self.market_condition_detector = MarketConditionDetector()
    
    def adapt_execution_strategy(
        self,
        trade_request: TradeExecutionRequest,
        current_performance: Dict[str, float],
        market_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt execution strategy based on performance and market conditions"""
        
        adaptations = {}
        
        # Adjust participation rate based on slippage
        current_slippage = current_performance.get('slippage', 0)
        if current_slippage > trade_request.max_slippage:
            # Reduce aggression
            new_participation = trade_request.participation_rate * 0.8
            adaptations['participation_rate'] = max(0.05, new_participation)
        elif current_slippage < trade_request.max_slippage * 0.5:
            # Increase aggression
            new_participation = trade_request.participation_rate * 1.2
            adaptations['participation_rate'] = min(0.5, new_participation)
        
        # Adjust based on market volatility
        volatility_regime = market_conditions.get('volatility_regime', 'normal')
        if volatility_regime == 'high':
            adaptations['use_smaller_slices'] = True
            adaptations['increase_randomization'] = True
        elif volatility_regime == 'low':
            adaptations['use_larger_slices'] = True
            adaptations['reduce_randomization'] = True
        
        # Adjust based on liquidity
        liquidity_score = market_conditions.get('liquidity_score', 0.5)
        if liquidity_score < 0.3:
            adaptations['prefer_dark_pools'] = True
            adaptations['reduce_visibility'] = True
        
        return adaptations


class MarketConditionDetector:
    """Detects and classifies market conditions"""
    
    def __init__(self):
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
    
    def detect_conditions(self, market_data: MarketDataSnapshot) -> Dict[str, Any]:
        """Detect current market conditions"""
        
        self.price_history.append(market_data.last_price)
        self.volume_history.append(market_data.volume)
        
        if len(self.price_history) < 10:
            return {'volatility_regime': 'normal', 'trend': 'sideways', 'liquidity_score': 0.5}
        
        # Calculate volatility
        returns = np.diff(list(self.price_history))
        volatility = np.std(returns) if len(returns) > 0 else 0
        
        # Classify volatility regime
        if volatility > 0.02:
            volatility_regime = 'high'
        elif volatility < 0.005:
            volatility_regime = 'low'
        else:
            volatility_regime = 'normal'
        
        # Detect trend
        recent_prices = list(self.price_history)[-20:]
        if len(recent_prices) >= 2:
            trend_slope = (recent_prices[-1] - recent_prices[0]) / len(recent_prices)
            if trend_slope > 0.001:
                trend = 'uptrend'
            elif trend_slope < -0.001:
                trend = 'downtrend'
            else:
                trend = 'sideways'
        else:
            trend = 'sideways'
        
        # Estimate liquidity
        avg_volume = np.mean(list(self.volume_history)) if self.volume_history else 1000
        current_volume = market_data.volume
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Liquidity score based on volume and spread
        liquidity_score = min(1.0, volume_ratio * 0.5 + (1 / (market_data.spread + 0.001)) * 0.5)
        
        return {
            'volatility_regime': volatility_regime,
            'volatility_value': volatility,
            'trend': trend,
            'trend_strength': abs(trend_slope) if 'trend_slope' in locals() else 0,
            'liquidity_score': liquidity_score,
            'volume_ratio': volume_ratio
        }


class ExecutionPerformanceTracker:
    """Tracks execution performance in real-time"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.benchmarks = {}
    
    def track_slice_execution(
        self,
        slice: TradeSlice,
        market_data_before: MarketDataSnapshot,
        market_data_after: MarketDataSnapshot
    ) -> Dict[str, float]:
        """Track performance of slice execution"""
        
        # Calculate slippage
        arrival_price = market_data_before.midpoint
        execution_price = slice.avg_execution_price
        
        if slice.side == 'BUY':
            slippage = (execution_price - arrival_price) / arrival_price
        else:
            slippage = (arrival_price - execution_price) / arrival_price
        
        # Calculate market impact
        price_movement = market_data_after.midpoint - market_data_before.midpoint
        market_impact = price_movement / market_data_before.midpoint
        
        # Timing cost (opportunity cost of not executing immediately)
        timing_cost = slippage - market_impact
        
        performance = {
            'slippage': slippage,
            'market_impact': market_impact,
            'timing_cost': timing_cost,
            'effective_spread': abs(execution_price - market_data_before.midpoint) * 2,
            'execution_duration': (slice.execution_end - slice.execution_start).total_seconds() if slice.execution_end else 0
        }
        
        # Store metrics
        for metric, value in performance.items():
            self.metrics[metric].append(value)
        
        return performance
    
    def get_aggregate_performance(self) -> Dict[str, float]:
        """Get aggregate performance metrics"""
        
        if not self.metrics:
            return {}
        
        return {
            metric: {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'count': len(values)
            }
            for metric, values in self.metrics.items()
        }


class TradeExecutor:
    """
    Advanced Trade Executor
    
    High-performance trade execution with sophisticated algorithms,
    real-time adaptation, and institutional-grade performance tracking.
    """
    
    def __init__(self):
        """Initialize trade executor"""
        
        # Core components
        self.performance_tracker = ExecutionPerformanceTracker()
        self.adaptive_engine = AdaptiveExecutionEngine()
        self.market_impact_model = MarketImpactModel()
        self.condition_detector = MarketConditionDetector()
        
        # Active trades
        self._active_trades = {}
        self._trade_history = {}
        
        # Execution engines
        self._execution_engines = {
            TradeExecutionAlgorithm.TWAP: TWAPExecutor,
            TradeExecutionAlgorithm.POV: POVExecutor,
            TradeExecutionAlgorithm.IS: ImplementationShortfallExecutor
        }
        
        # Threading and async
        self._lock = threading.Lock()
        self._running = False
        
        logger.info("Trade Executor initialized")
    
    async def execute_trade(self, trade_request: TradeExecutionRequest) -> str:
        """Execute trade using specified algorithm"""
        
        try:
            # Validate request
            self._validate_trade_request(trade_request)
            
            # Get market data
            market_data = await self._get_market_data(trade_request.symbol)
            
            # Select and initialize execution engine
            engine_class = self._execution_engines.get(trade_request.algorithm)
            if not engine_class:
                raise ValueError(f"Unsupported algorithm: {trade_request.algorithm}")
            
            execution_engine = engine_class(trade_request)
            
            # Generate execution schedule
            if trade_request.algorithm == TradeExecutionAlgorithm.TWAP:
                slices = execution_engine.generate_execution_schedule()
            elif trade_request.algorithm == TradeExecutionAlgorithm.IS:
                slices = execution_engine.optimize_execution_schedule(market_data)
            else:
                slices = self._generate_default_schedule(trade_request)
            
            # Initialize trade state
            trade_state = {
                'request': trade_request,
                'status': TradeStatus.ACTIVE,
                'slices': slices,
                'executed_quantity': 0.0,
                'avg_execution_price': 0.0,
                'start_time': datetime.now(),
                'market_data_at_start': market_data,
                'performance_metrics': {},
                'adaptations_made': []
            }
            
            with self._lock:
                self._active_trades[trade_request.trade_id] = trade_state
            
            # Start execution
            asyncio.create_task(self._execute_trade_slices(trade_request.trade_id))
            
            logger.info(f"Trade execution started: {trade_request.trade_id}")
            return trade_request.trade_id
            
        except Exception as e:
            logger.error(f"Error executing trade {trade_request.trade_id}: {e}")
            raise
    
    async def _execute_trade_slices(self, trade_id: str) -> None:
        """Execute trade slices according to schedule"""
        
        try:
            with self._lock:
                trade_state = self._active_trades.get(trade_id)
            
            if not trade_state:
                return
            
            request = trade_state['request']
            slices = trade_state['slices']
            
            for slice in slices:
                if trade_state['status'] != TradeStatus.ACTIVE:
                    break
                
                # Wait until scheduled time
                now = datetime.now()
                if slice.scheduled_time > now:
                    wait_seconds = (slice.scheduled_time - now).total_seconds()
                    await asyncio.sleep(wait_seconds)
                
                # Get current market conditions
                market_data = await self._get_market_data(request.symbol)
                market_conditions = self.condition_detector.detect_conditions(market_data)
                
                # Check for adaptations
                current_performance = self._calculate_current_performance(trade_state)
                adaptations = self.adaptive_engine.adapt_execution_strategy(
                    request, current_performance, market_conditions
                )
                
                if adaptations:
                    self._apply_adaptations(slice, adaptations)
                    trade_state['adaptations_made'].append({
                        'time': datetime.now(),
                        'adaptations': adaptations,
                        'market_conditions': market_conditions
                    })
                
                # Execute slice
                await self._execute_slice(slice, market_data, trade_state)
                
                # Update trade state
                self._update_trade_state(trade_state, slice)
                
                # Check if trade is complete
                if trade_state['executed_quantity'] >= request.quantity * 0.999:  # 99.9% filled
                    trade_state['status'] = TradeStatus.COMPLETED
                    break
            
            # Finalize trade
            await self._finalize_trade(trade_id)
            
        except Exception as e:
            logger.error(f"Error executing trade slices for {trade_id}: {e}")
            with self._lock:
                if trade_id in self._active_trades:
                    self._active_trades[trade_id]['status'] = TradeStatus.FAILED
    
    async def _execute_slice(
        self,
        slice: TradeSlice,
        market_data: MarketDataSnapshot,
        trade_state: Dict[str, Any]
    ) -> None:
        """Execute individual trade slice"""
        
        slice.execution_start = datetime.now()
        slice.status = "executing"
        
        try:
            # Estimate market impact
            impact_estimates = self.market_impact_model.estimate_impact(
                slice.symbol,
                slice.target_quantity,
                execution_rate=1.0,  # Immediate execution for this example
                market_data=market_data
            )
            
            # Determine execution price with impact
            if slice.side == 'BUY':
                execution_price = market_data.ask * (1 + impact_estimates['total_impact'])
            else:
                execution_price = market_data.bid * (1 - impact_estimates['total_impact'])
            
            # Add some randomness for realism
            price_noise = np.random.normal(0, 0.001)
            execution_price *= (1 + price_noise)
            
            # Simulate partial fills
            fill_rate = np.random.uniform(0.8, 1.0)  # 80-100% fill rate
            executed_qty = slice.target_quantity * fill_rate
            
            # Update slice
            slice.executed_quantity = executed_qty
            slice.remaining_quantity = slice.target_quantity - executed_qty
            slice.avg_execution_price = execution_price
            slice.execution_end = datetime.now()
            slice.status = "completed" if slice.remaining_quantity < 0.01 else "partial"
            
            # Calculate performance metrics
            arrival_price = trade_state['market_data_at_start'].midpoint
            if slice.side == 'BUY':
                slice.slippage = (execution_price - arrival_price) / arrival_price
            else:
                slice.slippage = (arrival_price - execution_price) / arrival_price
            
            slice.market_impact = impact_estimates['total_impact']
            
            logger.debug(f"Slice {slice.slice_id} executed: {executed_qty} @ {execution_price}")
            
        except Exception as e:
            slice.status = "failed"
            slice.error_message = str(e)
            logger.error(f"Error executing slice {slice.slice_id}: {e}")
    
    def _apply_adaptations(self, slice: TradeSlice, adaptations: Dict[str, Any]) -> None:
        """Apply adaptations to slice execution"""
        
        if adaptations.get('use_smaller_slices'):
            slice.target_quantity *= 0.7
        elif adaptations.get('use_larger_slices'):
            slice.target_quantity *= 1.3
        
        if adaptations.get('increase_randomization'):
            jitter = np.random.uniform(-300, 300)  # ±5 minutes
            slice.scheduled_time += timedelta(seconds=jitter)
    
    def _update_trade_state(self, trade_state: Dict[str, Any], executed_slice: TradeSlice) -> None:
        """Update trade state after slice execution"""
        
        # Update executed quantity and average price
        old_qty = trade_state['executed_quantity']
        old_avg_price = trade_state['avg_execution_price']
        
        new_qty = executed_slice.executed_quantity
        new_price = executed_slice.avg_execution_price
        
        total_qty = old_qty + new_qty
        if total_qty > 0:
            trade_state['avg_execution_price'] = (
                (old_qty * old_avg_price + new_qty * new_price) / total_qty
            )
        
        trade_state['executed_quantity'] = total_qty
        
        # Update performance metrics
        current_performance = self._calculate_current_performance(trade_state)
        trade_state['performance_metrics'] = current_performance
        
        # Progress callback
        if trade_state['request'].progress_callback:
            try:
                progress = {
                    'trade_id': trade_state['request'].trade_id,
                    'executed_quantity': total_qty,
                    'remaining_quantity': trade_state['request'].quantity - total_qty,
                    'avg_price': trade_state['avg_execution_price'],
                    'performance': current_performance
                }
                trade_state['request'].progress_callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _calculate_current_performance(self, trade_state: Dict[str, Any]) -> Dict[str, float]:
        """Calculate current trade performance"""
        
        if trade_state['executed_quantity'] == 0:
            return {}
        
        request = trade_state['request']
        arrival_price = trade_state['market_data_at_start'].midpoint
        avg_execution_price = trade_state['avg_execution_price']
        
        # Calculate slippage
        if request.side == 'BUY':
            slippage = (avg_execution_price - arrival_price) / arrival_price
        else:
            slippage = (arrival_price - avg_execution_price) / arrival_price
        
        # Calculate other metrics
        fill_rate = trade_state['executed_quantity'] / request.quantity
        execution_time = (datetime.now() - trade_state['start_time']).total_seconds()
        
        return {
            'slippage': slippage,
            'slippage_bps': slippage * 10000,
            'fill_rate': fill_rate,
            'execution_time_seconds': execution_time,
            'avg_execution_price': avg_execution_price
        }
    
    async def _finalize_trade(self, trade_id: str) -> None:
        """Finalize trade execution"""
        
        with self._lock:
            trade_state = self._active_trades.get(trade_id)
        
        if not trade_state:
            return
        
        # Final performance calculation
        final_performance = self._calculate_current_performance(trade_state)
        trade_state['final_performance'] = final_performance
        trade_state['end_time'] = datetime.now()
        
        # Completion callback
        if trade_state['request'].completion_callback:
            try:
                trade_state['request'].completion_callback(trade_state)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")
        
        # Move to history
        with self._lock:
            self._trade_history[trade_id] = trade_state
            if trade_id in self._active_trades:
                del self._active_trades[trade_id]
        
        logger.info(f"Trade {trade_id} finalized with performance: {final_performance}")
    
    async def _get_market_data(self, symbol: str) -> MarketDataSnapshot:
        """Get current market data (mock implementation)"""
        
        # Mock market data
        base_price = 100.0
        spread = 0.02
        
        return MarketDataSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            bid=base_price - spread/2,
            ask=base_price + spread/2,
            midpoint=base_price,
            last_price=base_price + np.random.normal(0, 0.01),
            bid_size=np.random.uniform(1000, 10000),
            ask_size=np.random.uniform(1000, 10000),
            volume=np.random.uniform(100, 1000),
            avg_volume=np.random.uniform(50000, 200000),
            spread=spread,
            volatility=np.random.uniform(0.005, 0.03),
            liquidity_score=np.random.uniform(0.6, 0.9)
        )
    
    def _generate_default_schedule(self, request: TradeExecutionRequest) -> List[TradeSlice]:
        """Generate default execution schedule"""
        
        # Simple equal-sized slices over time
        num_slices = 10
        slice_size = request.quantity / num_slices
        start_time = request.start_time or datetime.now()
        
        if request.end_time:
            duration = request.end_time - start_time
        else:
            duration = timedelta(hours=1)
        
        slice_interval = duration / num_slices
        
        slices = []
        for i in range(num_slices):
            slice_time = start_time + slice_interval * i
            
            slice = TradeSlice(
                slice_id=f"{request.trade_id}_slice_{i+1}",
                trade_id=request.trade_id,
                symbol=request.symbol,
                side=request.side,
                target_quantity=slice_size,
                remaining_quantity=slice_size,
                scheduled_time=slice_time
            )
            
            slices.append(slice)
        
        return slices
    
    def _validate_trade_request(self, request: TradeExecutionRequest) -> None:
        """Validate trade request"""
        
        if request.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if request.side not in ['BUY', 'SELL']:
            raise ValueError("Side must be 'BUY' or 'SELL'")
        
        if request.participation_rate <= 0 or request.participation_rate > 1:
            raise ValueError("Participation rate must be between 0 and 1")
        
        if request.start_time and request.end_time and request.start_time >= request.end_time:
            raise ValueError("End time must be after start time")
    
    def get_trade_status(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """Get trade execution status"""
        
        with self._lock:
            # Check active trades
            if trade_id in self._active_trades:
                trade_state = self._active_trades[trade_id]
            # Check history
            elif trade_id in self._trade_history:
                trade_state = self._trade_history[trade_id]
            else:
                return None
        
        request = trade_state['request']
        
        return {
            'trade_id': trade_id,
            'symbol': request.symbol,
            'side': request.side,
            'algorithm': request.algorithm.value,
            'total_quantity': request.quantity,
            'executed_quantity': trade_state['executed_quantity'],
            'remaining_quantity': request.quantity - trade_state['executed_quantity'],
            'avg_execution_price': trade_state['avg_execution_price'],
            'status': trade_state['status'].value,
            'fill_rate': trade_state['executed_quantity'] / request.quantity,
            'slices_total': len(trade_state['slices']),
            'slices_completed': len([s for s in trade_state['slices'] if s.status == 'completed']),
            'performance_metrics': trade_state.get('performance_metrics', {}),
            'start_time': trade_state['start_time'].isoformat(),
            'end_time': trade_state.get('end_time', {}).isoformat() if trade_state.get('end_time') else None
        }
    
    def cancel_trade(self, trade_id: str) -> bool:
        """Cancel active trade"""
        
        with self._lock:
            if trade_id not in self._active_trades:
                return False
            
            self._active_trades[trade_id]['status'] = TradeStatus.CANCELLED
        
        logger.info(f"Trade {trade_id} cancelled")
        return True
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution performance statistics"""
        
        all_trades = list(self._trade_history.values())
        
        if not all_trades:
            return {'total_trades': 0}
        
        # Calculate aggregate statistics
        total_trades = len(all_trades)
        completed_trades = len([t for t in all_trades if t['status'] == TradeStatus.COMPLETED])
        
        # Performance metrics
        slippages = [t.get('final_performance', {}).get('slippage', 0) for t in all_trades if 'final_performance' in t]
        fill_rates = [t.get('final_performance', {}).get('fill_rate', 0) for t in all_trades if 'final_performance' in t]
        
        return {
            'total_trades': total_trades,
            'completed_trades': completed_trades,
            'completion_rate': completed_trades / total_trades if total_trades > 0 else 0,
            'active_trades': len(self._active_trades),
            'avg_slippage_bps': np.mean(slippages) * 10000 if slippages else 0,
            'avg_fill_rate': np.mean(fill_rates) if fill_rates else 0,
            'total_volume_executed': sum(t['executed_quantity'] for t in all_trades),
            'performance_tracker': self.performance_tracker.get_aggregate_performance()
        }
    
    def start(self) -> None:
        """Start trade executor"""
        self._running = True
        logger.info("Trade Executor started")
    
    def stop(self) -> None:
        """Stop trade executor"""
        self._running = False
        
        # Cancel all active trades
        with self._lock:
            for trade_id in list(self._active_trades.keys()):
                self._active_trades[trade_id]['status'] = TradeStatus.CANCELLED
        
        logger.info("Trade Executor stopped")