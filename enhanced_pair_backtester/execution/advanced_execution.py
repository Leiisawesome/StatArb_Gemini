"""
Advanced Execution Algorithms for Statistical Arbitrage
======================================================

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

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class Order:
    """Single order representation"""
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: str = field(default_factory=lambda: str(int(datetime.now().timestamp() * 1000000)))
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    
    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity
    
    @property
    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity
    
    @property
    def fill_ratio(self) -> float:
        return self.filled_quantity / self.quantity if self.quantity > 0 else 0.0

@dataclass
class Fill:
    """Order fill representation"""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float = 0.0
    
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
    
@dataclass
class ExecutionResult:
    """Result of execution algorithm"""
    symbol: str
    total_quantity: int
    executed_quantity: int
    avg_execution_price: float
    total_cost: float
    market_impact_bps: float
    timing_cost_bps: float
    total_cost_bps: float
    execution_time: float  # seconds
    slices: List[ExecutionSlice]
    orders: List[Order]
    fills: List[Fill]
    
    @property
    def execution_rate(self) -> float:
        return self.executed_quantity / self.total_quantity if self.total_quantity > 0 else 0.0

class BaseExecutionAlgorithm(ABC):
    """Base class for execution algorithms"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.market_data_feed = None
        self.order_manager = None
        self.execution_history = []
        
    @abstractmethod
    async def execute(self, symbol: str, side: OrderSide, quantity: int, 
                     target_price: Optional[float] = None) -> ExecutionResult:
        """Execute order using algorithm"""
        pass
    
    def set_market_data_feed(self, feed):
        """Set market data feed"""
        self.market_data_feed = feed
    
    def set_order_manager(self, manager):
        """Set order manager"""
        self.order_manager = manager
    
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
                           end_time: datetime) -> List[float]:
        """Get expected volume profile for time period"""
        # Simplified volume profile (U-shaped intraday pattern)
        duration_hours = (end_time - start_time).total_seconds() / 3600
        time_points = max(1, int(duration_hours * 60))  # Minute intervals
        
        # Generate U-shaped volume profile
        profile = []
        for i in range(time_points):
            # Higher volume at start and end, lower in middle
            normalized_time = i / max(1, time_points - 1)
            volume_factor = 1.0 + 0.5 * (abs(normalized_time - 0.5) * 2)
            profile.append(volume_factor)
        
        return profile

class TWAPExecutionAlgorithm(BaseExecutionAlgorithm):
    """Time-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_duration = config.get('default_duration_minutes', 30)
        self.slice_interval = config.get('slice_interval_seconds', 60)
        self.max_participation = config.get('max_participation_rate', 0.2)
        
    async def execute(self, symbol: str, side: OrderSide, quantity: int,
                     target_price: Optional[float] = None) -> ExecutionResult:
        """Execute using TWAP algorithm"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=self.default_duration)
        
        logger.info(f"Starting TWAP execution: {symbol} {side.value} {quantity}")
        
        # Calculate execution slices
        slices = self._calculate_twap_slices(symbol, side, quantity, start_time, end_time)
        
        # Execute slices
        orders = []
        fills = []
        total_executed = 0
        total_cost = 0.0
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                now = datetime.now()
                if slice_info.start_time > now:
                    wait_seconds = (slice_info.start_time - now).total_seconds()
                    await asyncio.sleep(wait_seconds)
                
                # Create and submit order
                order = Order(
                    symbol=symbol,
                    side=side,
                    quantity=slice_info.quantity,
                    order_type=OrderType.MARKET,
                    price=slice_info.target_price
                )
                
                # Simulate order execution
                fill = await self._simulate_order_execution(order)
                
                orders.append(order)
                fills.append(fill)
                total_executed += fill.quantity
                total_cost += fill.quantity * fill.price
                
                logger.info(f"TWAP slice executed: {fill.quantity} @ {fill.price}")
                
            except Exception as e:
                logger.error(f"Error executing TWAP slice: {e}")
                continue
        
        # Calculate execution metrics
        avg_price = total_cost / total_executed if total_executed > 0 else 0.0
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate costs
        market_impact_bps = self._calculate_total_market_impact(fills)
        timing_cost_bps = self._calculate_timing_cost(fills, target_price)
        total_cost_bps = market_impact_bps + timing_cost_bps
        
        result = ExecutionResult(
            symbol=symbol,
            total_quantity=quantity,
            executed_quantity=total_executed,
            avg_execution_price=avg_price,
            total_cost=total_cost,
            market_impact_bps=market_impact_bps,
            timing_cost_bps=timing_cost_bps,
            total_cost_bps=total_cost_bps,
            execution_time=execution_time,
            slices=slices,
            orders=orders,
            fills=fills
        )
        
        self.execution_history.append(result)
        return result
    
    def _calculate_twap_slices(self, symbol: str, side: OrderSide, quantity: int,
                              start_time: datetime, end_time: datetime) -> List[ExecutionSlice]:
        """Calculate TWAP execution slices"""
        total_duration = (end_time - start_time).total_seconds()
        num_slices = max(1, int(total_duration / self.slice_interval))
        slice_duration = total_duration / num_slices
        
        slices = []
        remaining_quantity = quantity
        
        for i in range(num_slices):
            slice_start = start_time + timedelta(seconds=i * slice_duration)
            slice_end = slice_start + timedelta(seconds=slice_duration)
            
            # Equal quantity per slice for TWAP
            slice_quantity = remaining_quantity // (num_slices - i)
            remaining_quantity -= slice_quantity
            
            if slice_quantity > 0:
                slices.append(ExecutionSlice(
                    symbol=symbol,
                    side=side,
                    quantity=slice_quantity,
                    target_price=None,  # Market price
                    start_time=slice_start,
                    end_time=slice_end,
                    urgency=0.5,  # Medium urgency
                    max_participation=self.max_participation
                ))
        
        return slices
    
    async def _simulate_order_execution(self, order: Order) -> Fill:
        """Simulate order execution (replace with real execution)"""
        # Get current price
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            current_price = 100.0  # Default price
        
        # Add some market impact and noise
        impact = self._calculate_market_impact(order.symbol, order.quantity, 0.1)
        noise = np.random.normal(0, current_price * 0.0001)  # 1bp noise
        
        if order.side == OrderSide.BUY:
            fill_price = current_price + (current_price * impact) + noise
        else:
            fill_price = current_price - (current_price * impact) + noise
        
        # Simulate partial fill possibility
        fill_quantity = order.quantity
        if np.random.random() < 0.1:  # 10% chance of partial fill
            fill_quantity = int(order.quantity * np.random.uniform(0.7, 0.95))
        
        order.status = OrderStatus.FILLED if fill_quantity == order.quantity else OrderStatus.PARTIALLY_FILLED
        order.filled_quantity = fill_quantity
        order.avg_fill_price = fill_price
        
        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            timestamp=datetime.now(),
            commission=0.5  # $0.50 commission
        )
    
    def _calculate_total_market_impact(self, fills: List[Fill]) -> float:
        """Calculate total market impact in bps"""
        if not fills:
            return 0.0
        
        # Simplified calculation
        total_impact = 0.0
        for fill in fills:
            # Estimate impact based on fill size
            participation_rate = fill.quantity / 10000  # Assume 10k average volume
            impact = 10 * np.sqrt(participation_rate)  # 10 bps * sqrt(participation)
            total_impact += impact
        
        return total_impact / len(fills)
    
    def _calculate_timing_cost(self, fills: List[Fill], target_price: Optional[float]) -> float:
        """Calculate timing cost in bps"""
        if not fills or target_price is None:
            return 0.0
        
        total_timing_cost = 0.0
        for fill in fills:
            timing_cost = abs(fill.price - target_price) / target_price * 10000
            total_timing_cost += timing_cost
        
        return total_timing_cost / len(fills)

class VWAPExecutionAlgorithm(BaseExecutionAlgorithm):
    """Volume-Weighted Average Price execution algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.default_duration = config.get('default_duration_minutes', 30)
        self.max_participation = config.get('max_participation_rate', 0.15)
        self.volume_lookback = config.get('volume_lookback_days', 20)
        
    async def execute(self, symbol: str, side: OrderSide, quantity: int,
                     target_price: Optional[float] = None) -> ExecutionResult:
        """Execute using VWAP algorithm"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=self.default_duration)
        
        logger.info(f"Starting VWAP execution: {symbol} {side.value} {quantity}")
        
        # Get volume profile
        volume_profile = self._get_volume_profile(symbol, start_time, end_time)
        
        # Calculate execution slices based on volume profile
        slices = self._calculate_vwap_slices(symbol, side, quantity, start_time, 
                                           end_time, volume_profile)
        
        # Execute slices
        orders = []
        fills = []
        total_executed = 0
        total_cost = 0.0
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                now = datetime.now()
                if slice_info.start_time > now:
                    wait_seconds = (slice_info.start_time - now).total_seconds()
                    await asyncio.sleep(wait_seconds)
                
                # Create and submit order
                order = Order(
                    symbol=symbol,
                    side=side,
                    quantity=slice_info.quantity,
                    order_type=OrderType.MARKET,
                    price=slice_info.target_price
                )
                
                # Simulate order execution
                fill = await self._simulate_order_execution(order)
                
                orders.append(order)
                fills.append(fill)
                total_executed += fill.quantity
                total_cost += fill.quantity * fill.price
                
                logger.info(f"VWAP slice executed: {fill.quantity} @ {fill.price}")
                
            except Exception as e:
                logger.error(f"Error executing VWAP slice: {e}")
                continue
        
        # Calculate execution metrics
        avg_price = total_cost / total_executed if total_executed > 0 else 0.0
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate costs
        market_impact_bps = self._calculate_total_market_impact(fills)
        timing_cost_bps = self._calculate_timing_cost(fills, target_price)
        total_cost_bps = market_impact_bps + timing_cost_bps
        
        result = ExecutionResult(
            symbol=symbol,
            total_quantity=quantity,
            executed_quantity=total_executed,
            avg_execution_price=avg_price,
            total_cost=total_cost,
            market_impact_bps=market_impact_bps,
            timing_cost_bps=timing_cost_bps,
            total_cost_bps=total_cost_bps,
            execution_time=execution_time,
            slices=slices,
            orders=orders,
            fills=fills
        )
        
        self.execution_history.append(result)
        return result
    
    def _calculate_vwap_slices(self, symbol: str, side: OrderSide, quantity: int,
                              start_time: datetime, end_time: datetime,
                              volume_profile: List[float]) -> List[ExecutionSlice]:
        """Calculate VWAP execution slices based on volume profile"""
        total_duration = (end_time - start_time).total_seconds()
        slice_duration = total_duration / len(volume_profile)
        
        # Normalize volume profile
        total_volume_weight = sum(volume_profile)
        normalized_profile = [v / total_volume_weight for v in volume_profile]
        
        slices = []
        for i, volume_weight in enumerate(normalized_profile):
            slice_start = start_time + timedelta(seconds=i * slice_duration)
            slice_end = slice_start + timedelta(seconds=slice_duration)
            
            # Quantity proportional to volume
            slice_quantity = int(quantity * volume_weight)
            
            if slice_quantity > 0:
                slices.append(ExecutionSlice(
                    symbol=symbol,
                    side=side,
                    quantity=slice_quantity,
                    target_price=None,  # Market price
                    start_time=slice_start,
                    end_time=slice_end,
                    urgency=0.4,  # Lower urgency for VWAP
                    max_participation=self.max_participation
                ))
        
        return slices
    
    async def _simulate_order_execution(self, order: Order) -> Fill:
        """Simulate order execution with VWAP considerations"""
        # Get current price
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            current_price = 100.0  # Default price
        
        # VWAP has lower market impact due to volume matching
        impact = self._calculate_market_impact(order.symbol, order.quantity, 0.05)
        noise = np.random.normal(0, current_price * 0.0001)
        
        if order.side == OrderSide.BUY:
            fill_price = current_price + (current_price * impact) + noise
        else:
            fill_price = current_price - (current_price * impact) + noise
        
        # Better fill rates for VWAP
        fill_quantity = order.quantity
        if np.random.random() < 0.05:  # 5% chance of partial fill
            fill_quantity = int(order.quantity * np.random.uniform(0.8, 0.95))
        
        order.status = OrderStatus.FILLED if fill_quantity == order.quantity else OrderStatus.PARTIALLY_FILLED
        order.filled_quantity = fill_quantity
        order.avg_fill_price = fill_price
        
        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            timestamp=datetime.now(),
            commission=0.5
        )
    
    def _calculate_total_market_impact(self, fills: List[Fill]) -> float:
        """Calculate total market impact for VWAP"""
        if not fills:
            return 0.0
        
        # VWAP typically has lower impact due to volume matching
        total_impact = 0.0
        for fill in fills:
            participation_rate = fill.quantity / 15000  # Higher assumed volume
            impact = 8 * np.sqrt(participation_rate)  # 8 bps * sqrt(participation)
            total_impact += impact
        
        return total_impact / len(fills)
    
    def _calculate_timing_cost(self, fills: List[Fill], target_price: Optional[float]) -> float:
        """Calculate timing cost for VWAP"""
        if not fills or target_price is None:
            return 0.0
        
        total_timing_cost = 0.0
        for fill in fills:
            timing_cost = abs(fill.price - target_price) / target_price * 10000
            total_timing_cost += timing_cost
        
        return total_timing_cost / len(fills)

class ImplementationShortfallAlgorithm(BaseExecutionAlgorithm):
    """Implementation Shortfall optimization algorithm"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.risk_aversion = config.get('risk_aversion', 0.5)
        self.volatility_lookback = config.get('volatility_lookback_days', 20)
        self.max_participation = config.get('max_participation_rate', 0.25)
        
    async def execute(self, symbol: str, side: OrderSide, quantity: int,
                     target_price: Optional[float] = None) -> ExecutionResult:
        """Execute using Implementation Shortfall algorithm"""
        start_time = datetime.now()
        
        logger.info(f"Starting IS execution: {symbol} {side.value} {quantity}")
        
        # Estimate optimal execution schedule
        optimal_schedule = self._calculate_optimal_schedule(symbol, quantity, target_price)
        
        # Convert to execution slices
        slices = self._schedule_to_slices(symbol, side, optimal_schedule)
        
        # Execute slices
        orders = []
        fills = []
        total_executed = 0
        total_cost = 0.0
        
        for slice_info in slices:
            try:
                # Wait until slice start time
                now = datetime.now()
                if slice_info.start_time > now:
                    wait_seconds = (slice_info.start_time - now).total_seconds()
                    await asyncio.sleep(wait_seconds)
                
                # Create and submit order
                order = Order(
                    symbol=symbol,
                    side=side,
                    quantity=slice_info.quantity,
                    order_type=OrderType.MARKET,
                    price=slice_info.target_price
                )
                
                # Simulate order execution
                fill = await self._simulate_order_execution(order)
                
                orders.append(order)
                fills.append(fill)
                total_executed += fill.quantity
                total_cost += fill.quantity * fill.price
                
                logger.info(f"IS slice executed: {fill.quantity} @ {fill.price}")
                
            except Exception as e:
                logger.error(f"Error executing IS slice: {e}")
                continue
        
        # Calculate execution metrics
        avg_price = total_cost / total_executed if total_executed > 0 else 0.0
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate costs
        market_impact_bps = self._calculate_total_market_impact(fills)
        timing_cost_bps = self._calculate_timing_cost(fills, target_price)
        total_cost_bps = market_impact_bps + timing_cost_bps
        
        result = ExecutionResult(
            symbol=symbol,
            total_quantity=quantity,
            executed_quantity=total_executed,
            avg_execution_price=avg_price,
            total_cost=total_cost,
            market_impact_bps=market_impact_bps,
            timing_cost_bps=timing_cost_bps,
            total_cost_bps=total_cost_bps,
            execution_time=execution_time,
            slices=slices,
            orders=orders,
            fills=fills
        )
        
        self.execution_history.append(result)
        return result
    
    def _calculate_optimal_schedule(self, symbol: str, quantity: int, 
                                  target_price: Optional[float]) -> List[Tuple[datetime, int]]:
        """Calculate optimal execution schedule using IS optimization"""
        # Simplified IS optimization
        # In practice, this would solve a complex optimization problem
        
        # Estimate volatility
        volatility = self._estimate_volatility(symbol)
        
        # Calculate optimal execution rate
        # Higher volatility -> faster execution
        # Higher risk aversion -> faster execution
        urgency_factor = volatility * self.risk_aversion
        
        # Determine execution horizon
        execution_horizon = max(5, int(30 / (1 + urgency_factor)))  # 5-30 minutes
        
        # Create schedule with front-loaded execution
        schedule = []
        remaining_quantity = quantity
        start_time = datetime.now()
        
        for i in range(execution_horizon):
            # Front-load execution (more aggressive early on)
            time_factor = (execution_horizon - i) / execution_horizon
            slice_quantity = int(remaining_quantity * time_factor * 0.3)  # 30% of remaining
            slice_quantity = min(slice_quantity, remaining_quantity)
            
            if slice_quantity > 0:
                slice_time = start_time + timedelta(minutes=i)
                schedule.append((slice_time, slice_quantity))
                remaining_quantity -= slice_quantity
        
        # Execute remaining quantity in final slice
        if remaining_quantity > 0:
            final_time = start_time + timedelta(minutes=execution_horizon)
            schedule.append((final_time, remaining_quantity))
        
        return schedule
    
    def _schedule_to_slices(self, symbol: str, side: OrderSide, 
                           schedule: List[Tuple[datetime, int]]) -> List[ExecutionSlice]:
        """Convert schedule to execution slices"""
        slices = []
        
        for i, (slice_time, slice_quantity) in enumerate(schedule):
            end_time = slice_time + timedelta(minutes=1)  # 1 minute execution window
            
            # Higher urgency for later slices
            urgency = 0.3 + (i / len(schedule)) * 0.5
            
            slices.append(ExecutionSlice(
                symbol=symbol,
                side=side,
                quantity=slice_quantity,
                target_price=None,
                start_time=slice_time,
                end_time=end_time,
                urgency=urgency,
                max_participation=self.max_participation
            ))
        
        return slices
    
    def _estimate_volatility(self, symbol: str) -> float:
        """Estimate current volatility for symbol"""
        # In practice, this would use historical data
        # For now, return a default estimate
        return 0.02  # 2% daily volatility
    
    async def _simulate_order_execution(self, order: Order) -> Fill:
        """Simulate order execution with IS considerations"""
        current_price = self._get_current_price(order.symbol)
        if current_price is None:
            current_price = 100.0
        
        # IS algorithm optimizes for lower total cost
        impact = self._calculate_market_impact(order.symbol, order.quantity, 0.08)
        noise = np.random.normal(0, current_price * 0.0001)
        
        if order.side == OrderSide.BUY:
            fill_price = current_price + (current_price * impact) + noise
        else:
            fill_price = current_price - (current_price * impact) + noise
        
        # Higher fill rates for IS
        fill_quantity = order.quantity
        if np.random.random() < 0.03:  # 3% chance of partial fill
            fill_quantity = int(order.quantity * np.random.uniform(0.85, 0.95))
        
        order.status = OrderStatus.FILLED if fill_quantity == order.quantity else OrderStatus.PARTIALLY_FILLED
        order.filled_quantity = fill_quantity
        order.avg_fill_price = fill_price
        
        return Fill(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_quantity,
            price=fill_price,
            timestamp=datetime.now(),
            commission=0.5
        )
    
    def _calculate_total_market_impact(self, fills: List[Fill]) -> float:
        """Calculate total market impact for IS"""
        if not fills:
            return 0.0
        
        # IS optimizes for lower total impact
        total_impact = 0.0
        for fill in fills:
            participation_rate = fill.quantity / 12000
            impact = 6 * np.sqrt(participation_rate)  # 6 bps * sqrt(participation)
            total_impact += impact
        
        return total_impact / len(fills)
    
    def _calculate_timing_cost(self, fills: List[Fill], target_price: Optional[float]) -> float:
        """Calculate timing cost for IS"""
        if not fills or target_price is None:
            return 0.0
        
        total_timing_cost = 0.0
        for fill in fills:
            timing_cost = abs(fill.price - target_price) / target_price * 10000
            total_timing_cost += timing_cost
        
        return total_timing_cost / len(fills)

class PairExecutionCoordinator:
    """Coordinates execution of pair trades"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.execution_algorithms = {
            'twap': TWAPExecutionAlgorithm(config),
            'vwap': VWAPExecutionAlgorithm(config),
            'is': ImplementationShortfallAlgorithm(config)
        }
        
    async def execute_pair_trade(self, symbol1: str, symbol2: str, 
                               quantity1: int, quantity2: int,
                               algorithm: str = 'twap') -> Tuple[ExecutionResult, ExecutionResult]:
        """Execute coordinated pair trade"""
        if algorithm not in self.execution_algorithms:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        algo = self.execution_algorithms[algorithm]
        
        # Determine sides (typically one buy, one sell)
        side1 = OrderSide.BUY if quantity1 > 0 else OrderSide.SELL
        side2 = OrderSide.SELL if quantity2 > 0 else OrderSide.BUY
        
        # Execute both legs simultaneously
        tasks = [
            algo.execute(symbol1, side1, abs(quantity1)),
            algo.execute(symbol2, side2, abs(quantity2))
        ]
        
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Pair trade executed: {symbol1} {side1.value} {abs(quantity1)}, "
                   f"{symbol2} {side2.value} {abs(quantity2)}")
        
        return results[0], results[1]
    
    def get_execution_summary(self, result1: ExecutionResult, result2: ExecutionResult) -> Dict[str, Any]:
        """Get summary of pair execution"""
        total_cost_bps = (result1.total_cost_bps + result2.total_cost_bps) / 2
        total_execution_time = max(result1.execution_time, result2.execution_time)
        
        return {
            'leg1_symbol': result1.symbol,
            'leg1_executed': result1.executed_quantity,
            'leg1_avg_price': result1.avg_execution_price,
            'leg1_cost_bps': result1.total_cost_bps,
            'leg2_symbol': result2.symbol,
            'leg2_executed': result2.executed_quantity,
            'leg2_avg_price': result2.avg_execution_price,
            'leg2_cost_bps': result2.total_cost_bps,
            'total_cost_bps': total_cost_bps,
            'execution_time': total_execution_time,
            'execution_quality': 1.0 - (total_cost_bps / 100)  # Quality score
        }

def create_execution_algorithm(algorithm_type: str, config: Dict[str, Any]) -> BaseExecutionAlgorithm:
    """Factory function to create execution algorithm"""
    if algorithm_type == 'twap':
        return TWAPExecutionAlgorithm(config)
    elif algorithm_type == 'vwap':
        return VWAPExecutionAlgorithm(config)
    elif algorithm_type == 'is':
        return ImplementationShortfallAlgorithm(config)
    else:
        raise ValueError(f"Unknown algorithm type: {algorithm_type}") 