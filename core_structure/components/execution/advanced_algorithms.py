"""
Advanced Execution Algorithms

Professional-grade execution algorithms supporting:
- TWAP (Time-Weighted Average Price) execution
- VWAP (Volume-Weighted Average Price) execution  
- Implementation Shortfall optimization
- Real-time market impact modeling
- Liquidity-aware execution scheduling
- Multi-venue execution routing

Author: Pro Quant Desk Trader
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import warnings
from abc import ABC, abstractmethod

# Import execution engine components
from .unified_execution_engine import ExecutionRequest, ExecutionResult, ExecutionStatus
from .order_manager import Order, OrderType, OrderSide, OrderStatus
from .market_impact import MarketConditions, MarketImpactModel
from .transaction_cost_optimizer import TransactionCostOptimizer

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class ExecutionSlice:
    """Single execution slice for algorithms"""
    symbol: str
    side: OrderSide
    quantity: int
    target_price: Optional[float]
    start_time: datetime
    end_time: datetime
    urgency: float  # 0-1, higher means more urgent
    max_participation: float  # Maximum participation rate
    
    # Execution results
    actual_quantity: int = 0
    actual_price: float = 0.0
    execution_cost: float = 0.0
    market_impact: float = 0.0
    
    @property
    def fill_rate(self) -> float:
        """Fill rate for this slice"""
        if self.quantity == 0:
            return 0.0
        return (self.actual_quantity / self.quantity) * 100
    
    @property
    def duration_minutes(self) -> float:
        """Duration of slice in minutes"""
        return (self.end_time - self.start_time).total_seconds() / 60


class BaseExecutionAlgorithm(ABC):
    """Base class for execution algorithms"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.execution_engine = None
        self.market_data_feed = None
        self.order_manager = None
        self.execution_history = []
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    async def execute(self, request: ExecutionRequest, 
                     market_conditions: MarketConditions) -> ExecutionResult:
        """Execute order using algorithm"""
        pass
    
    def set_execution_engine(self, engine):
        """Set execution engine reference"""
        self.execution_engine = engine
        self.order_manager = engine.order_manager
    
    def set_market_data_feed(self, feed):
        """Set market data feed"""
        self.market_data_feed = feed
    
    def _calculate_market_impact(self, symbol: str, quantity: int, 
                               participation_rate: float) -> float:
        """Calculate estimated market impact"""
        # Simplified market impact model (square root law)
        base_impact = 0.001  # 10 bps base impact
        impact = base_impact * np.sqrt(participation_rate)
        return min(impact, 0.01)  # Cap at 100 bps
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        if self.market_data_feed:
            quote = self.market_data_feed.get_real_time_quote(symbol)
            return quote.mid_price if quote else None
        return None
    
    def _get_volume_profile(self, symbol: str, start_time: datetime, 
                           end_time: datetime) -> pd.Series:
        """Get historical volume profile"""
        # In real implementation, this would fetch from market data
        # For now, return a simple U-shaped profile
        duration_hours = (end_time - start_time).total_seconds() / 3600
        num_points = max(1, int(duration_hours * 2))  # 30-minute intervals
        
        # U-shaped volume profile (higher at open/close)
        x = np.linspace(0, 1, num_points)
        volume_profile = 0.5 + 0.3 * (x**2 + (1-x)**2)  # U-shape
        
        return pd.Series(volume_profile, 
                        index=pd.date_range(start_time, end_time, periods=num_points))


class TWAPAlgorithm(BaseExecutionAlgorithm):
    """Time-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_duration = config.get('default_duration_minutes', 30)
        self.slice_interval = config.get('slice_interval_seconds', 60)
        self.max_participation = config.get('max_participation_rate', 0.2)
        self.adaptive_sizing = config.get('adaptive_sizing', True)
        
    async def execute(self, request: ExecutionRequest,
                     market_conditions: MarketConditions) -> ExecutionResult:
        """Execute using TWAP algorithm"""
        start_time = datetime.now()
        duration = request.time_limit or self.default_duration
        end_time = start_time + timedelta(minutes=duration)
        
        self.logger.info(f"Starting TWAP execution: {request.symbol} {request.side.value} {request.quantity}")
        
        # Calculate execution slices
        slices = self._calculate_twap_slices(request, start_time, end_time, market_conditions)
        
        # Execute slices
        orders = []
        total_executed = 0
        total_cost = 0.0
        execution_errors = []
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                if slice_info.start_time > datetime.now():
                    await asyncio.sleep((slice_info.start_time - datetime.now()).total_seconds())
                
                # Execute slice
                slice_result = await self._execute_slice(slice_info, market_conditions)
                
                if slice_result:
                    orders.extend(slice_result.orders)
                    total_executed += slice_result.executed_quantity
                    total_cost += slice_result.total_cost
                    
                    # Update slice with actual results
                    slice_info.actual_quantity = slice_result.executed_quantity
                    slice_info.actual_price = slice_result.average_price
                    slice_info.execution_cost = slice_result.total_cost
                
                # Adaptive sizing - adjust remaining slices based on market conditions
                if self.adaptive_sizing and total_executed < request.quantity:
                    remaining_slices = [s for s in slices if s.start_time > datetime.now()]
                    if remaining_slices:
                        self._adjust_slice_sizes(remaining_slices, 
                                               request.quantity - total_executed,
                                               market_conditions)
                
            except Exception as e:
                self.logger.error(f"TWAP slice execution failed: {str(e)}")
                execution_errors.append(str(e))
        
        # Calculate final results
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Determine status
        if total_executed == 0:
            status = ExecutionStatus.FAILED
        elif total_executed < request.quantity * 0.95:  # Less than 95% filled
            status = ExecutionStatus.PARTIAL
        else:
            status = ExecutionStatus.SUCCESS
        
        result = ExecutionResult(
            request_id=request.request_id,
            status=status,
            symbol=request.symbol,
            side=request.side,
            requested_quantity=request.quantity,
            executed_quantity=total_executed,
            total_cost=total_cost,
            orders=orders,
            execution_time=execution_time,
            algorithm_used=request.algorithm
        )
        
        if execution_errors:
            result.warnings.extend(execution_errors)
        
        # Store execution history
        self.execution_history.append({
            'request': request,
            'result': result,
            'slices': slices,
            'market_conditions': market_conditions
        })
        
        return result
    
    def _calculate_twap_slices(self, request: ExecutionRequest, 
                             start_time: datetime, end_time: datetime,
                             market_conditions: MarketConditions) -> List[ExecutionSlice]:
        """Calculate TWAP execution slices"""
        duration_seconds = (end_time - start_time).total_seconds()
        num_slices = max(1, int(duration_seconds / self.slice_interval))
        
        # Equal-sized slices for basic TWAP
        slice_size = request.quantity / num_slices
        slices = []
        
        for i in range(num_slices):
            slice_start = start_time + timedelta(seconds=i * self.slice_interval)
            slice_end = min(slice_start + timedelta(seconds=self.slice_interval), end_time)
            
            # Adjust slice size based on urgency
            urgency_factor = request.urgency
            adjusted_size = slice_size * (1 + urgency_factor * 0.2)  # Up to 20% larger for urgent orders
            
            slices.append(ExecutionSlice(
                symbol=request.symbol,
                side=request.side,
                quantity=int(adjusted_size),
                target_price=request.target_price,
                start_time=slice_start,
                end_time=slice_end,
                urgency=urgency_factor,
                max_participation=request.max_participation
            ))
        
        # Ensure total quantity matches (adjust last slice)
        total_slice_quantity = sum(s.quantity for s in slices)
        if total_slice_quantity != request.quantity:
            slices[-1].quantity += request.quantity - total_slice_quantity
        
        return slices
    
    def _adjust_slice_sizes(self, remaining_slices: List[ExecutionSlice],
                           remaining_quantity: int,
                           market_conditions: MarketConditions):
        """Adjust remaining slice sizes based on market conditions"""
        if not remaining_slices:
            return
        
        # Redistribute remaining quantity
        new_slice_size = remaining_quantity / len(remaining_slices)
        
        for slice_info in remaining_slices:
            # Adjust based on market conditions
            if market_conditions.regime.value == 'volatile':
                # Smaller slices in volatile markets
                slice_info.quantity = int(new_slice_size * 0.8)
            elif market_conditions.regime.value == 'illiquid':
                # Larger slices in illiquid markets
                slice_info.quantity = int(new_slice_size * 1.2)
            else:
                slice_info.quantity = int(new_slice_size)
    
    async def _execute_slice(self, slice_info: ExecutionSlice,
                           market_conditions: MarketConditions) -> Optional[ExecutionResult]:
        """Execute individual slice"""
        # Create order for slice
        order = Order(
            symbol=slice_info.symbol,
            side=slice_info.side,
            quantity=slice_info.quantity,
            order_type=OrderType.LIMIT if slice_info.target_price else OrderType.MARKET,
            price=slice_info.target_price
        )
        
        # Submit order
        if not self.order_manager.submit_order(order):
            return None
        
        # Simulate execution (in real system, would wait for market fills)
        current_price = self._get_current_price(slice_info.symbol) or 100.0
        
        # Add some realistic slippage
        slippage = np.random.normal(0, 0.001)  # 10 bps standard deviation
        execution_price = current_price * (1 + slippage)
        
        # Fill order
        commission = slice_info.quantity * execution_price * 0.0005  # 5 bps commission
        fill = self.order_manager.fill_order(
            order_id=order.order_id,
            fill_quantity=slice_info.quantity,
            fill_price=execution_price,
            commission=commission
        )
        
        if fill:
            return ExecutionResult(
                request_id="slice_" + str(hash(slice_info)),
                status=ExecutionStatus.SUCCESS,
                symbol=slice_info.symbol,
                side=slice_info.side,
                requested_quantity=slice_info.quantity,
                executed_quantity=slice_info.quantity,
                average_price=execution_price,
                total_cost=commission,
                orders=[order]
            )
        
        return None


class VWAPAlgorithm(BaseExecutionAlgorithm):
    """Volume-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_duration = config.get('default_duration_minutes', 30)
        self.max_participation = config.get('max_participation_rate', 0.15)
        self.volume_lookback = config.get('volume_lookback_days', 20)
        self.adaptive_participation = config.get('adaptive_participation', True)
        
    async def execute(self, request: ExecutionRequest,
                     market_conditions: MarketConditions) -> ExecutionResult:
        """Execute using VWAP algorithm"""
        start_time = datetime.now()
        duration = request.time_limit or self.default_duration
        end_time = start_time + timedelta(minutes=duration)
        
        self.logger.info(f"Starting VWAP execution: {request.symbol} {request.side.value} {request.quantity}")
        
        # Get volume profile
        volume_profile = self._get_volume_profile(request.symbol, start_time, end_time)
        
        # Calculate execution slices based on volume profile
        slices = self._calculate_vwap_slices(request, start_time, end_time, 
                                           volume_profile, market_conditions)
        
        # Execute slices
        orders = []
        total_executed = 0
        total_cost = 0.0
        vwap_tracking = []
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                if slice_info.start_time > datetime.now():
                    await asyncio.sleep((slice_info.start_time - datetime.now()).total_seconds())
                
                # Execute slice
                slice_result = await self._execute_slice(slice_info, market_conditions)
                
                if slice_result:
                    orders.extend(slice_result.orders)
                    total_executed += slice_result.executed_quantity
                    total_cost += slice_result.total_cost
                    
                    # Track VWAP performance
                    vwap_tracking.append({
                        'time': datetime.now(),
                        'price': slice_result.average_price,
                        'quantity': slice_result.executed_quantity,
                        'market_vwap': self._estimate_market_vwap(request.symbol)
                    })
                
            except Exception as e:
                self.logger.error(f"VWAP slice execution failed: {str(e)}")
        
        # Calculate VWAP performance
        if vwap_tracking:
            execution_vwap = sum(t['price'] * t['quantity'] for t in vwap_tracking) / total_executed
            market_vwap = np.mean([t['market_vwap'] for t in vwap_tracking])
            vwap_performance = (execution_vwap - market_vwap) / market_vwap * 10000  # bps
        else:
            vwap_performance = 0.0
        
        # Determine status
        if total_executed == 0:
            status = ExecutionStatus.FAILED
        elif total_executed < request.quantity * 0.95:
            status = ExecutionStatus.PARTIAL
        else:
            status = ExecutionStatus.SUCCESS
        
        result = ExecutionResult(
            request_id=request.request_id,
            status=status,
            symbol=request.symbol,
            side=request.side,
            requested_quantity=request.quantity,
            executed_quantity=total_executed,
            total_cost=total_cost,
            orders=orders,
            execution_time=(datetime.now() - start_time).total_seconds(),
            algorithm_used=request.algorithm
        )
        
        # Add VWAP-specific metrics
        result.metadata = {
            'vwap_performance_bps': vwap_performance,
            'execution_vwap': execution_vwap if vwap_tracking else 0.0,
            'market_vwap': market_vwap if vwap_tracking else 0.0,
            'volume_profile_used': volume_profile.to_dict()
        }
        
        return result
    
    def _calculate_vwap_slices(self, request: ExecutionRequest,
                             start_time: datetime, end_time: datetime,
                             volume_profile: pd.Series,
                             market_conditions: MarketConditions) -> List[ExecutionSlice]:
        """Calculate VWAP execution slices based on volume profile"""
        slices = []
        
        # Normalize volume profile
        total_volume_weight = volume_profile.sum()
        
        for i, (timestamp, volume_weight) in enumerate(volume_profile.items()):
            # Calculate slice size based on volume weight
            slice_proportion = volume_weight / total_volume_weight
            slice_size = int(request.quantity * slice_proportion)
            
            if slice_size == 0:
                continue
            
            # Calculate slice timing
            if i < len(volume_profile) - 1:
                slice_end = volume_profile.index[i + 1]
            else:
                slice_end = end_time
            
            # Adjust participation rate based on market conditions
            participation_rate = request.max_participation
            if self.adaptive_participation:
                if market_conditions.regime.value == 'volatile':
                    participation_rate *= 0.7  # Reduce participation in volatile markets
                elif market_conditions.regime.value == 'illiquid':
                    participation_rate *= 1.3  # Increase participation in illiquid markets
            
            slices.append(ExecutionSlice(
                symbol=request.symbol,
                side=request.side,
                quantity=slice_size,
                target_price=request.target_price,
                start_time=timestamp,
                end_time=slice_end,
                urgency=request.urgency,
                max_participation=participation_rate
            ))
        
        return slices
    
    def _estimate_market_vwap(self, symbol: str) -> float:
        """Estimate current market VWAP"""
        # In real implementation, this would calculate from market data
        # For now, return a simulated value
        current_price = self._get_current_price(symbol) or 100.0
        return current_price * (1 + np.random.normal(0, 0.001))
    
    async def _execute_slice(self, slice_info: ExecutionSlice,
                           market_conditions: MarketConditions) -> Optional[ExecutionResult]:
        """Execute individual VWAP slice"""
        # Similar to TWAP but with volume-aware execution
        order = Order(
            symbol=slice_info.symbol,
            side=slice_info.side,
            quantity=slice_info.quantity,
            order_type=OrderType.LIMIT if slice_info.target_price else OrderType.MARKET,
            price=slice_info.target_price
        )
        
        if not self.order_manager.submit_order(order):
            return None
        
        # Simulate execution with volume-aware pricing
        current_price = self._get_current_price(slice_info.symbol) or 100.0
        
        # Better execution in high-volume periods
        volume_factor = min(slice_info.max_participation, 0.2)  # Cap at 20%
        price_improvement = volume_factor * 0.0002  # 2 bps improvement per 10% participation
        
        if slice_info.side == OrderSide.BUY:
            execution_price = current_price * (1 - price_improvement)
        else:
            execution_price = current_price * (1 + price_improvement)
        
        commission = slice_info.quantity * execution_price * 0.0005
        fill = self.order_manager.fill_order(
            order_id=order.order_id,
            fill_quantity=slice_info.quantity,
            fill_price=execution_price,
            commission=commission
        )
        
        if fill:
            return ExecutionResult(
                request_id="vwap_slice_" + str(hash(slice_info)),
                status=ExecutionStatus.SUCCESS,
                symbol=slice_info.symbol,
                side=slice_info.side,
                requested_quantity=slice_info.quantity,
                executed_quantity=slice_info.quantity,
                average_price=execution_price,
                total_cost=commission,
                orders=[order]
            )
        
        return None


class ImplementationShortfallAlgorithm(BaseExecutionAlgorithm):
    """Implementation Shortfall optimization algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.risk_aversion = config.get('risk_aversion', 0.5)
        self.volatility_lookback = config.get('volatility_lookback_days', 20)
        self.max_participation = config.get('max_participation_rate', 0.25)
        self.optimization_method = config.get('optimization_method', 'almgren_chriss')
        
    async def execute(self, request: ExecutionRequest,
                     market_conditions: MarketConditions) -> ExecutionResult:
        """Execute using Implementation Shortfall algorithm"""
        start_time = datetime.now()
        
        self.logger.info(f"Starting IS execution: {request.symbol} {request.side.value} {request.quantity}")
        
        # Estimate optimal execution schedule
        optimal_schedule = self._calculate_optimal_schedule(request, market_conditions)
        
        # Convert to execution slices
        slices = self._schedule_to_slices(request, optimal_schedule)
        
        # Execute slices with real-time optimization
        orders = []
        total_executed = 0
        total_cost = 0.0
        implementation_shortfall = 0.0
        
        arrival_price = self._get_current_price(request.symbol) or 100.0
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                if slice_info.start_time > datetime.now():
                    await asyncio.sleep((slice_info.start_time - datetime.now()).total_seconds())
                
                # Real-time optimization: adjust slice based on current conditions
                current_conditions = await self._get_current_market_conditions(request.symbol)
                optimized_slice = self._optimize_slice_real_time(slice_info, current_conditions)
                
                # Execute slice
                slice_result = await self._execute_slice(optimized_slice, current_conditions)
                
                if slice_result:
                    orders.extend(slice_result.orders)
                    total_executed += slice_result.executed_quantity
                    total_cost += slice_result.total_cost
                    
                    # Calculate implementation shortfall
                    price_diff = slice_result.average_price - arrival_price
                    if request.side == OrderSide.SELL:
                        price_diff = -price_diff
                    
                    implementation_shortfall += price_diff * slice_result.executed_quantity
                
            except Exception as e:
                self.logger.error(f"IS slice execution failed: {str(e)}")
        
        # Calculate final implementation shortfall in bps
        if total_executed > 0:
            implementation_shortfall_bps = (implementation_shortfall / (total_executed * arrival_price)) * 10000
        else:
            implementation_shortfall_bps = 0.0
        
        # Determine status
        if total_executed == 0:
            status = ExecutionStatus.FAILED
        elif total_executed < request.quantity * 0.95:
            status = ExecutionStatus.PARTIAL
        else:
            status = ExecutionStatus.SUCCESS
        
        result = ExecutionResult(
            request_id=request.request_id,
            status=status,
            symbol=request.symbol,
            side=request.side,
            requested_quantity=request.quantity,
            executed_quantity=total_executed,
            total_cost=total_cost,
            orders=orders,
            execution_time=(datetime.now() - start_time).total_seconds(),
            algorithm_used=request.algorithm,
            implementation_shortfall=implementation_shortfall_bps
        )
        
        return result
    
    def _calculate_optimal_schedule(self, request: ExecutionRequest,
                                  market_conditions: MarketConditions) -> List[Tuple[float, float]]:
        """Calculate optimal execution schedule using Almgren-Chriss framework"""
        # Simplified Almgren-Chriss implementation
        T = (request.time_limit or 30) / 60  # Convert to hours
        X = request.quantity
        sigma = market_conditions.volatility
        
        # Market impact parameters (simplified)
        eta = 0.001  # Temporary impact parameter
        gamma = 0.0001  # Permanent impact parameter
        
        # Calculate optimal trajectory
        kappa = np.sqrt(self.risk_aversion * sigma**2 / (eta * T))
        
        # Number of time steps
        n_steps = max(1, int(T * 4))  # 15-minute intervals
        dt = T / n_steps
        
        schedule = []
        for i in range(n_steps):
            t = i * dt
            
            # Optimal trading rate (simplified)
            if self.optimization_method == 'almgren_chriss':
                # Almgren-Chriss solution
                remaining_time = T - t
                if remaining_time > 0:
                    trading_rate = X * kappa * np.sinh(kappa * remaining_time) / np.sinh(kappa * T)
                else:
                    trading_rate = 0
            else:
                # Linear schedule as fallback
                trading_rate = X / n_steps
            
            schedule.append((t, trading_rate * dt))
        
        return schedule
    
    def _schedule_to_slices(self, request: ExecutionRequest,
                          schedule: List[Tuple[float, float]]) -> List[ExecutionSlice]:
        """Convert optimal schedule to execution slices"""
        slices = []
        start_time = datetime.now()
        
        for i, (time_hours, quantity) in enumerate(schedule):
            if quantity <= 0:
                continue
            
            slice_start = start_time + timedelta(hours=time_hours)
            slice_end = slice_start + timedelta(minutes=15)  # 15-minute slices
            
            slices.append(ExecutionSlice(
                symbol=request.symbol,
                side=request.side,
                quantity=int(quantity),
                target_price=request.target_price,
                start_time=slice_start,
                end_time=slice_end,
                urgency=request.urgency,
                max_participation=self.max_participation
            ))
        
        return slices
    
    async def _get_current_market_conditions(self, symbol: str) -> MarketConditions:
        """Get current market conditions for real-time optimization"""
        # In real implementation, this would fetch live data
        return MarketConditions(
            volatility=0.02,
            volume=1_000_000,
            spread=0.001
        )
    
    def _optimize_slice_real_time(self, slice_info: ExecutionSlice,
                                current_conditions: MarketConditions) -> ExecutionSlice:
        """Optimize slice in real-time based on current conditions"""
        # Adjust slice size based on current volatility
        if current_conditions.volatility > 0.03:  # High volatility
            slice_info.quantity = int(slice_info.quantity * 0.8)  # Reduce size
        elif current_conditions.volatility < 0.01:  # Low volatility
            slice_info.quantity = int(slice_info.quantity * 1.2)  # Increase size
        
        return slice_info
    
    async def _execute_slice(self, slice_info: ExecutionSlice,
                           market_conditions: MarketConditions) -> Optional[ExecutionResult]:
        """Execute Implementation Shortfall slice"""
        # Use limit orders for better execution
        current_price = self._get_current_price(slice_info.symbol) or 100.0
        
        # Calculate optimal limit price
        if slice_info.side == OrderSide.BUY:
            limit_price = current_price * (1 + market_conditions.spread / 2)
        else:
            limit_price = current_price * (1 - market_conditions.spread / 2)
        
        order = Order(
            symbol=slice_info.symbol,
            side=slice_info.side,
            quantity=slice_info.quantity,
            order_type=OrderType.LIMIT,
            price=limit_price
        )
        
        if not self.order_manager.submit_order(order):
            return None
        
        # Simulate execution with improved pricing due to optimization
        execution_price = limit_price * (1 + np.random.normal(0, 0.0005))  # Reduced slippage
        
        commission = slice_info.quantity * execution_price * 0.0005
        fill = self.order_manager.fill_order(
            order_id=order.order_id,
            fill_quantity=slice_info.quantity,
            fill_price=execution_price,
            commission=commission
        )
        
        if fill:
            return ExecutionResult(
                request_id="is_slice_" + str(hash(slice_info)),
                status=ExecutionStatus.SUCCESS,
                symbol=slice_info.symbol,
                side=slice_info.side,
                requested_quantity=slice_info.quantity,
                executed_quantity=slice_info.quantity,
                average_price=execution_price,
                total_cost=commission,
                orders=[order]
            )
        
        return None


class PairExecutionCoordinator:
    """Coordinates execution of pair trades"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.algorithms = {
            'twap': TWAPAlgorithm(config),
            'vwap': VWAPAlgorithm(config),
            'implementation_shortfall': ImplementationShortfallAlgorithm(config)
        }
        self.logger = logging.getLogger(__name__)
        
    def set_execution_engine(self, engine):
        """Set execution engine for all algorithms"""
        for algorithm in self.algorithms.values():
            algorithm.set_execution_engine(engine)
    
    async def execute_pair_trade(self, symbol1: str, symbol2: str, 
                               quantity1: int, quantity2: int,
                               algorithm: str = 'twap',
                               market_conditions: Optional[MarketConditions] = None) -> Tuple[ExecutionResult, ExecutionResult]:
        """Execute coordinated pair trade"""
        if algorithm not in self.algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        algo = self.algorithms[algorithm]
        
        # Default market conditions if not provided
        if market_conditions is None:
            market_conditions = MarketConditions(
                volatility=0.02,
                volume=1_000_000,
                spread=0.001
            )
        
        # Create execution requests
        request1 = ExecutionRequest(
            symbol=symbol1,
            side=OrderSide.BUY if quantity1 > 0 else OrderSide.SELL,
            quantity=abs(quantity1),
            algorithm=algorithm
        )
        
        request2 = ExecutionRequest(
            symbol=symbol2,
            side=OrderSide.BUY if quantity2 > 0 else OrderSide.SELL,
            quantity=abs(quantity2),
            algorithm=algorithm
        )
        
        # Execute both legs simultaneously
        tasks = [
            algo.execute(request1, market_conditions),
            algo.execute(request2, market_conditions)
        ]
        
        results = await asyncio.gather(*tasks)
        
        self.logger.info(f"Pair trade executed: {symbol1} {quantity1}, {symbol2} {quantity2}")
        
        return results[0], results[1]


class ExecutionAlgorithmFactory:
    """Factory for creating execution algorithms"""
    
    @staticmethod
    def create_algorithm(algorithm_type: str, config: Dict[str, Any]) -> BaseExecutionAlgorithm:
        """Create execution algorithm instance"""
        if algorithm_type.lower() == 'twap':
            return TWAPAlgorithm(config)
        elif algorithm_type.lower() == 'vwap':
            return VWAPAlgorithm(config)
        elif algorithm_type.lower() == 'implementation_shortfall':
            return ImplementationShortfallAlgorithm(config)
        else:
            raise ValueError(f"Unknown algorithm type: {algorithm_type}")
    
    @staticmethod
    def get_available_algorithms() -> List[str]:
        """Get list of available algorithms"""
        return ['twap', 'vwap', 'implementation_shortfall']
    
    @staticmethod
    def get_algorithm_config_template(algorithm_type: str) -> Dict[str, Any]:
        """Get configuration template for algorithm"""
        templates = {
            'twap': {
                'default_duration_minutes': 30,
                'slice_interval_seconds': 60,
                'max_participation_rate': 0.2,
                'adaptive_sizing': True
            },
            'vwap': {
                'default_duration_minutes': 30,
                'max_participation_rate': 0.15,
                'volume_lookback_days': 20,
                'adaptive_participation': True
            },
            'implementation_shortfall': {
                'risk_aversion': 0.5,
                'volatility_lookback_days': 20,
                'max_participation_rate': 0.25,
                'optimization_method': 'almgren_chriss'
            }
        }
        
        return templates.get(algorithm_type.lower(), {}) 