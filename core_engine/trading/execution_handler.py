"""
Trading Engine - Execution Handler
Advanced order execution with slippage modeling, market impact analysis, and execution algorithms
"""

import logging
import threading
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque

from .order_manager import Order, OrderType, OrderSide, OrderExecution

logger = logging.getLogger(__name__)


class ExecutionVenue(Enum):
    """Execution venues"""
    PRIMARY_EXCHANGE = "primary_exchange"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    CROSSING_NETWORK = "crossing_network"
    INTERNAL = "internal"
    EXTERNAL_BROKER = "external_broker"


class ExecutionStrategy(Enum):
    """Execution strategies"""
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    BALANCED = "balanced"
    STEALTH = "stealth"
    OPPORTUNISTIC = "opportunistic"


class LiquidityType(Enum):
    """Liquidity provision type"""
    MAKER = "maker"  # Adding liquidity
    TAKER = "taker"  # Taking liquidity
    UNKNOWN = "unknown"


@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: float
    ask_size: float
    last_price: float
    volume: float
    timestamp: datetime
    volatility: Optional[float] = None
    average_daily_volume: Optional[float] = None


@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    order_id: str
    symbol: str
    side: OrderSide
    total_quantity: float
    executed_quantity: float
    average_execution_price: float
    benchmark_price: float  # VWAP, arrival price, etc.
    slippage_bps: float
    market_impact_bps: float
    timing_cost_bps: float
    total_cost_bps: float
    execution_time_seconds: float
    venue_breakdown: Dict[str, float]
    liquidity_breakdown: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionReport:
    """Comprehensive execution report"""
    order_id: str
    executions: List[OrderExecution]
    metrics: ExecutionMetrics
    slippage_analysis: Dict[str, float]
    market_impact_analysis: Dict[str, float]
    execution_quality_score: float  # 0-100
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class SlippageModel:
    """Market impact and slippage modeling"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Model parameters
        self.linear_impact_coeff = self.config.get('linear_impact_coeff', 0.1)
        self.sqrt_impact_coeff = self.config.get('sqrt_impact_coeff', 0.05)
        self.volatility_impact_coeff = self.config.get('volatility_impact_coeff', 0.02)
        
        # Bid-ask spread impact
        self.spread_impact_factor = self.config.get('spread_impact_factor', 0.5)
        
        # Volume participation limits
        self.max_participation_rate = self.config.get('max_participation_rate', 0.2)
    
    def calculate_expected_slippage(
        self,
        order: Order,
        market_data: MarketData,
        participation_rate: float = 0.1
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate expected slippage for an order"""
        
        # Basic bid-ask spread cost
        spread = market_data.ask_price - market_data.bid_price
        spread_cost_bps = (spread / market_data.last_price) * 10000 * self.spread_impact_factor
        
        # Volume-based market impact
        if market_data.average_daily_volume and market_data.average_daily_volume > 0:
            volume_ratio = order.quantity / market_data.average_daily_volume
            linear_impact = self.linear_impact_coeff * volume_ratio * 10000
            sqrt_impact = self.sqrt_impact_coeff * np.sqrt(volume_ratio) * 10000
        else:
            linear_impact = 0
            sqrt_impact = 0
        
        # Volatility-based impact
        volatility_impact = 0
        if market_data.volatility:
            volatility_impact = self.volatility_impact_coeff * market_data.volatility * 10000
        
        # Participation rate impact
        participation_impact = 0
        if participation_rate > self.max_participation_rate:
            excess_participation = participation_rate - self.max_participation_rate
            participation_impact = excess_participation * 50  # 50 bps per 1% excess
        
        # Timing impact (simplified)
        timing_impact = np.random.normal(0, 2)  # Random timing cost
        
        # Total expected slippage
        total_slippage = (spread_cost_bps + linear_impact + sqrt_impact + 
                         volatility_impact + participation_impact + timing_impact)
        
        # Apply side multiplier
        side_multiplier = 1 if order.side == OrderSide.BUY else -1
        total_slippage *= side_multiplier
        
        breakdown = {
            'spread_cost': spread_cost_bps,
            'linear_impact': linear_impact,
            'sqrt_impact': sqrt_impact,
            'volatility_impact': volatility_impact,
            'participation_impact': participation_impact,
            'timing_impact': timing_impact
        }
        
        return total_slippage, breakdown


class ExecutionHandler:
    """
    Advanced execution handler
    
    Manages order execution with sophisticated slippage modeling,
    venue selection, and execution quality analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize execution handler"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Execution tracking
        self._active_executions = {}  # order_id -> execution state
        self._execution_reports = deque(maxlen=1000)
        self._execution_metrics = {}
        
        # Market data cache
        self._market_data_cache = {}
        
        # Execution venues and their characteristics
        self._venues = {
            ExecutionVenue.PRIMARY_EXCHANGE: {
                'latency_ms': 1,
                'fill_rate': 0.95,
                'cost_bps': 0.5,
                'min_size': 1,
                'max_size': 100000
            },
            ExecutionVenue.DARK_POOL: {
                'latency_ms': 5,
                'fill_rate': 0.7,
                'cost_bps': 0.3,
                'min_size': 100,
                'max_size': 50000
            },
            ExecutionVenue.ECN: {
                'latency_ms': 2,
                'fill_rate': 0.9,
                'cost_bps': 0.4,
                'min_size': 1,
                'max_size': 75000
            }
        }
        
        # Slippage model
        self.slippage_model = SlippageModel(config.get('slippage_config', {}))
        
        # Configuration
        self.enable_smart_routing = self.config.get('enable_smart_routing', True)
        self.max_execution_time = self.config.get('max_execution_time_seconds', 300)
        self.execution_reporting = self.config.get('enable_execution_reporting', True)
        
        # Performance tracking
        self._execution_stats = {
            'total_orders_executed': 0,
            'total_volume_executed': 0.0,
            'average_slippage_bps': 0.0,
            'average_execution_time': 0.0,
            'fill_rate': 0.0
        }
        
        logger.info("ExecutionHandler initialized")
    
    async def execute_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_strategy: ExecutionStrategy = ExecutionStrategy.BALANCED
    ) -> ExecutionReport:
        """
        Execute an order using specified strategy
        
        Args:
            order: Order to execute
            market_data: Current market data
            execution_strategy: Execution strategy to use
            
        Returns:
            Execution report with detailed metrics
        """
        start_time = time.time()
        
        try:
            logger.info(f"Executing order {order.order_id}: {order.side.value} {order.quantity} {order.symbol}")
            
            # Initialize execution tracking
            execution_state = {
                'start_time': datetime.now(),
                'remaining_quantity': order.quantity,
                'executions': [],
                'benchmark_price': market_data.last_price,
                'venue_usage': defaultdict(float),
                'liquidity_breakdown': defaultdict(float)
            }
            
            with self._lock:
                self._active_executions[order.order_id] = execution_state
            
            # Execute based on order type and strategy
            if order.order_type == OrderType.MARKET:
                await self._execute_market_order(order, market_data, execution_state, execution_strategy)
            elif order.order_type == OrderType.LIMIT:
                await self._execute_limit_order(order, market_data, execution_state, execution_strategy)
            elif order.order_type == OrderType.TWAP:
                await self._execute_twap_order(order, market_data, execution_state)
            elif order.order_type == OrderType.VWAP:
                await self._execute_vwap_order(order, market_data, execution_state)
            elif order.order_type == OrderType.IMPLEMENTATION_SHORTFALL:
                await self._execute_is_order(order, market_data, execution_state)
            else:
                await self._execute_default_order(order, market_data, execution_state)
            
            # Generate execution report
            report = await self._generate_execution_report(order, execution_state, market_data)
            
            # Store report
            if self.execution_reporting:
                with self._lock:
                    self._execution_reports.append(report)
            
            # Update statistics
            await self._update_execution_stats(report)
            
            # Cleanup
            with self._lock:
                if order.order_id in self._active_executions:
                    del self._active_executions[order.order_id]
            
            execution_time = time.time() - start_time
            logger.info(f"Execution completed for order {order.order_id} in {execution_time:.2f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"Error executing order {order.order_id}: {e}")
            
            # Cleanup on error
            with self._lock:
                if order.order_id in self._active_executions:
                    del self._active_executions[order.order_id]
            
            raise
    
    async def _execute_market_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any],
        strategy: ExecutionStrategy
    ) -> None:
        """Execute market order"""
        
        remaining_qty = execution_state['remaining_quantity']
        
        if strategy == ExecutionStrategy.AGGRESSIVE:
            # Execute full quantity immediately
            await self._execute_single_fill(
                order, market_data, remaining_qty, execution_state,
                ExecutionVenue.PRIMARY_EXCHANGE
            )
        
        elif strategy == ExecutionStrategy.PASSIVE:
            # Break into smaller chunks
            chunk_size = min(remaining_qty, remaining_qty * 0.2)
            while execution_state['remaining_quantity'] > 0:
                actual_size = min(chunk_size, execution_state['remaining_quantity'])
                venue = self._select_venue(order, actual_size, market_data)
                
                await self._execute_single_fill(
                    order, market_data, actual_size, execution_state, venue
                )
                
                # Wait between executions
                await asyncio.sleep(0.1)
        
        else:  # BALANCED
            # Use smart routing
            await self._smart_route_execution(order, market_data, execution_state)
    
    async def _execute_limit_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any],
        strategy: ExecutionStrategy
    ) -> None:
        """Execute limit order with price improvement logic"""
        
        # Simulate limit order execution
        limit_price = order.price
        current_price = market_data.ask_price if order.side == OrderSide.BUY else market_data.bid_price
        
        # Check if limit order can be executed
        can_execute = (
            (order.side == OrderSide.BUY and current_price <= limit_price) or
            (order.side == OrderSide.SELL and current_price >= limit_price)
        )
        
        if can_execute:
            # Execute at better of limit price and current market
            execution_price = min(limit_price, current_price) if order.side == OrderSide.BUY else max(limit_price, current_price)
            
            # Create custom market data for execution
            adjusted_market_data = MarketData(
                symbol=market_data.symbol,
                bid_price=execution_price if order.side == OrderSide.SELL else market_data.bid_price,
                ask_price=execution_price if order.side == OrderSide.BUY else market_data.ask_price,
                bid_size=market_data.bid_size,
                ask_size=market_data.ask_size,
                last_price=execution_price,
                volume=market_data.volume,
                timestamp=market_data.timestamp,
                volatility=market_data.volatility,
                average_daily_volume=market_data.average_daily_volume
            )
            
            await self._execute_single_fill(
                order, adjusted_market_data, execution_state['remaining_quantity'],
                execution_state, ExecutionVenue.PRIMARY_EXCHANGE
            )
        else:
            # Limit order not executable at current market
            logger.info(f"Limit order {order.order_id} not executable: limit={limit_price}, market={current_price}")
    
    async def _execute_twap_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any]
    ) -> None:
        """Execute TWAP (Time Weighted Average Price) order"""
        
        # Get TWAP parameters
        duration_minutes = order.algo_params.get('duration_minutes', 30)
        num_slices = order.algo_params.get('num_slices', 10)
        
        slice_quantity = order.quantity / num_slices
        slice_interval = (duration_minutes * 60) / num_slices
        
        for i in range(num_slices):
            if execution_state['remaining_quantity'] <= 0:
                break
            
            actual_quantity = min(slice_quantity, execution_state['remaining_quantity'])
            venue = self._select_venue(order, actual_quantity, market_data)
            
            await self._execute_single_fill(
                order, market_data, actual_quantity, execution_state, venue
            )
            
            # Wait for next slice
            if i < num_slices - 1:
                await asyncio.sleep(slice_interval)
    
    async def _execute_vwap_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any]
    ) -> None:
        """Execute VWAP (Volume Weighted Average Price) order"""
        
        # Simplified VWAP execution - in reality would use historical volume patterns
        participation_rate = order.algo_params.get('participation_rate', 0.1)
        duration_minutes = order.algo_params.get('duration_minutes', 60)
        
        # Estimate volume based on average daily volume
        if market_data.average_daily_volume:
            expected_volume_per_minute = market_data.average_daily_volume / (6.5 * 60)  # Trading day
            target_volume_per_minute = expected_volume_per_minute * participation_rate
        else:
            target_volume_per_minute = order.quantity / duration_minutes
        
        # Execute in time slices
        minutes_elapsed = 0
        while execution_state['remaining_quantity'] > 0 and minutes_elapsed < duration_minutes:
            slice_quantity = min(target_volume_per_minute, execution_state['remaining_quantity'])
            venue = self._select_venue(order, slice_quantity, market_data)
            
            await self._execute_single_fill(
                order, market_data, slice_quantity, execution_state, venue
            )
            
            minutes_elapsed += 1
            await asyncio.sleep(60)  # Wait 1 minute
    
    async def _execute_is_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any]
    ) -> None:
        """Execute Implementation Shortfall order"""
        
        # Implementation Shortfall balances market impact vs timing risk
        risk_aversion = order.algo_params.get('risk_aversion', 0.5)
        
        # Calculate optimal execution rate
        if market_data.volatility and market_data.average_daily_volume:
            volatility = market_data.volatility
            volume = market_data.average_daily_volume
            
            # Simplified IS calculation
            optimal_rate = np.sqrt(volatility / volume) * (1 - risk_aversion)
            optimal_rate = np.clip(optimal_rate, 0.01, 0.5)  # Limit between 1% and 50%
        else:
            optimal_rate = 0.1
        
        # Execute using calculated rate
        remaining_time = order.algo_params.get('max_duration_minutes', 120)
        
        while execution_state['remaining_quantity'] > 0 and remaining_time > 0:
            slice_quantity = execution_state['remaining_quantity'] * optimal_rate
            slice_quantity = max(1, min(slice_quantity, execution_state['remaining_quantity']))
            
            venue = self._select_venue(order, slice_quantity, market_data)
            
            await self._execute_single_fill(
                order, market_data, slice_quantity, execution_state, venue
            )
            
            remaining_time -= 1
            await asyncio.sleep(60)  # Wait 1 minute
    
    async def _execute_default_order(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any]
    ) -> None:
        """Default execution for other order types"""
        await self._smart_route_execution(order, market_data, execution_state)
    
    async def _smart_route_execution(
        self,
        order: Order,
        market_data: MarketData,
        execution_state: Dict[str, Any]
    ) -> None:
        """Smart order routing across multiple venues"""
        
        remaining_qty = execution_state['remaining_quantity']
        
        # Break large orders into smaller chunks
        if remaining_qty > 1000:
            chunk_size = remaining_qty * 0.3
        elif remaining_qty > 100:
            chunk_size = remaining_qty * 0.5
        else:
            chunk_size = remaining_qty
        
        while execution_state['remaining_quantity'] > 0:
            actual_size = min(chunk_size, execution_state['remaining_quantity'])
            venue = self._select_venue(order, actual_size, market_data)
            
            await self._execute_single_fill(
                order, market_data, actual_size, execution_state, venue
            )
            
            # Small delay between chunks
            if execution_state['remaining_quantity'] > 0:
                await asyncio.sleep(0.05)
    
    def _select_venue(self, order: Order, quantity: float, market_data: MarketData) -> ExecutionVenue:
        """Select optimal execution venue"""
        
        if not self.enable_smart_routing:
            return ExecutionVenue.PRIMARY_EXCHANGE
        
        # Venue selection logic based on order characteristics
        
        # Large orders -> Dark pools
        if quantity > 5000:
            return ExecutionVenue.DARK_POOL
        
        # Small orders -> ECN for speed
        elif quantity < 100:
            return ExecutionVenue.ECN
        
        # High volatility -> Primary exchange for certainty
        elif market_data.volatility and market_data.volatility > 0.3:
            return ExecutionVenue.PRIMARY_EXCHANGE
        
        # Default to primary exchange
        else:
            return ExecutionVenue.PRIMARY_EXCHANGE
    
    async def _execute_single_fill(
        self,
        order: Order,
        market_data: MarketData,
        quantity: float,
        execution_state: Dict[str, Any],
        venue: ExecutionVenue
    ) -> None:
        """Execute a single fill"""
        
        # Calculate execution price with slippage
        base_price = market_data.ask_price if order.side == OrderSide.BUY else market_data.bid_price
        
        # Apply slippage model
        participation_rate = quantity / market_data.average_daily_volume if market_data.average_daily_volume else 0.1
        expected_slippage_bps, _ = self.slippage_model.calculate_expected_slippage(
            order, market_data, participation_rate
        )
        
        # Convert slippage to price impact
        slippage_factor = expected_slippage_bps / 10000
        execution_price = base_price * (1 + slippage_factor)
        
        # Add venue-specific costs
        venue_info = self._venues.get(venue, self._venues[ExecutionVenue.PRIMARY_EXCHANGE])
        venue_cost_bps = venue_info['cost_bps']
        execution_price *= (1 + venue_cost_bps / 10000)
        
        # Simulate fill rate
        fill_rate = venue_info['fill_rate']
        if np.random.random() > fill_rate:
            logger.warning(f"Partial fill simulation - order {order.order_id}")
            quantity *= 0.8  # Partial fill
        
        # Create execution record
        execution = OrderExecution(
            execution_id=f"EXEC_{int(time.time() * 1000)}_{len(execution_state['executions'])}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=execution_price,
            timestamp=datetime.now(),
            venue=venue.value,
            commission=quantity * 0.001,  # $0.001 per share
            fees=max(1.0, quantity * 0.0005),  # Minimum $1 fee
            liquidity_flag="T" if venue == ExecutionVenue.PRIMARY_EXCHANGE else "P",
            metadata={
                'slippage_bps': expected_slippage_bps,
                'venue_cost_bps': venue_cost_bps,
                'participation_rate': participation_rate
            }
        )
        
        # Update execution state
        execution_state['executions'].append(execution)
        execution_state['remaining_quantity'] -= quantity
        execution_state['venue_usage'][venue.value] += quantity
        
        liquidity_type = LiquidityType.TAKER if venue == ExecutionVenue.PRIMARY_EXCHANGE else LiquidityType.MAKER
        execution_state['liquidity_breakdown'][liquidity_type.value] += quantity
        
        logger.debug(f"Executed {quantity} @ {execution_price:.4f} on {venue.value} for order {order.order_id}")
    
    async def _generate_execution_report(
        self,
        order: Order,
        execution_state: Dict[str, Any],
        market_data: MarketData
    ) -> ExecutionReport:
        """Generate comprehensive execution report"""
        
        executions = execution_state['executions']
        
        if not executions:
            # No executions
            metrics = ExecutionMetrics(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                total_quantity=order.quantity,
                executed_quantity=0,
                average_execution_price=0,
                benchmark_price=execution_state['benchmark_price'],
                slippage_bps=0,
                market_impact_bps=0,
                timing_cost_bps=0,
                total_cost_bps=0,
                execution_time_seconds=0,
                venue_breakdown={},
                liquidity_breakdown={}
            )
            
            return ExecutionReport(
                order_id=order.order_id,
                executions=[],
                metrics=metrics,
                slippage_analysis={},
                market_impact_analysis={},
                execution_quality_score=0,
                recommendations=["Order not executed"]
            )
        
        # Calculate metrics
        total_executed = sum(exec.quantity for exec in executions)
        total_value = sum(exec.quantity * exec.price for exec in executions)
        avg_execution_price = total_value / total_executed if total_executed > 0 else 0
        
        benchmark_price = execution_state['benchmark_price']
        
        # Calculate slippage
        if order.side == OrderSide.BUY:
            slippage_bps = ((avg_execution_price - benchmark_price) / benchmark_price) * 10000
        else:
            slippage_bps = ((benchmark_price - avg_execution_price) / benchmark_price) * 10000
        
        # Execution time
        start_time = execution_state['start_time']
        end_time = executions[-1].timestamp if executions else start_time
        execution_time = (end_time - start_time).total_seconds()
        
        # Venue breakdown
        venue_breakdown = {}
        total_qty = sum(execution_state['venue_usage'].values())
        for venue, qty in execution_state['venue_usage'].items():
            venue_breakdown[venue] = qty / total_qty if total_qty > 0 else 0
        
        # Liquidity breakdown
        liquidity_breakdown = {}
        for liquidity_type, qty in execution_state['liquidity_breakdown'].items():
            liquidity_breakdown[liquidity_type] = qty / total_executed if total_executed > 0 else 0
        
        # Create metrics
        metrics = ExecutionMetrics(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            total_quantity=order.quantity,
            executed_quantity=total_executed,
            average_execution_price=avg_execution_price,
            benchmark_price=benchmark_price,
            slippage_bps=slippage_bps,
            market_impact_bps=abs(slippage_bps) * 0.7,  # Estimate market impact as 70% of slippage
            timing_cost_bps=abs(slippage_bps) * 0.3,    # Timing cost as 30% of slippage
            total_cost_bps=abs(slippage_bps),
            execution_time_seconds=execution_time,
            venue_breakdown=venue_breakdown,
            liquidity_breakdown=liquidity_breakdown
        )
        
        # Slippage analysis
        slippage_analysis = {
            'expected_vs_actual': slippage_bps,
            'price_improvement': max(0, -slippage_bps),
            'adverse_selection': max(0, slippage_bps)
        }
        
        # Market impact analysis
        market_impact_analysis = {
            'temporary_impact': metrics.market_impact_bps * 0.6,
            'permanent_impact': metrics.market_impact_bps * 0.4,
            'participation_rate': total_executed / market_data.average_daily_volume if market_data.average_daily_volume else 0
        }
        
        # Execution quality score
        quality_score = self._calculate_execution_quality_score(metrics, order)
        
        # Recommendations
        recommendations = self._generate_recommendations(metrics, order, execution_time)
        
        return ExecutionReport(
            order_id=order.order_id,
            executions=executions,
            metrics=metrics,
            slippage_analysis=slippage_analysis,
            market_impact_analysis=market_impact_analysis,
            execution_quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _calculate_execution_quality_score(self, metrics: ExecutionMetrics, order: Order) -> float:
        """Calculate execution quality score (0-100)"""
        
        score = 100
        
        # Slippage penalty
        slippage_penalty = min(50, abs(metrics.slippage_bps) * 2)
        score -= slippage_penalty
        
        # Execution time penalty for large orders
        if order.quantity > 1000 and metrics.execution_time_seconds > 300:
            time_penalty = min(20, (metrics.execution_time_seconds - 300) / 60)
            score -= time_penalty
        
        # Fill rate bonus
        fill_rate = metrics.executed_quantity / metrics.total_quantity
        if fill_rate < 1.0:
            fill_penalty = (1.0 - fill_rate) * 30
            score -= fill_penalty
        
        # Venue diversification bonus
        if len(metrics.venue_breakdown) > 1:
            score += 5
        
        return max(0, min(100, score))
    
    def _generate_recommendations(
        self,
        metrics: ExecutionMetrics,
        order: Order,
        execution_time: float
    ) -> List[str]:
        """Generate execution recommendations"""
        
        recommendations = []
        
        # Slippage recommendations
        if abs(metrics.slippage_bps) > 10:
            recommendations.append("Consider using passive execution strategy to reduce slippage")
        
        if abs(metrics.slippage_bps) < 2:
            recommendations.append("Excellent execution - consider more aggressive strategies")
        
        # Timing recommendations
        if execution_time > 600:  # 10 minutes
            recommendations.append("Consider breaking large orders into smaller chunks")
        
        # Venue recommendations
        if len(metrics.venue_breakdown) == 1:
            recommendations.append("Consider using smart routing across multiple venues")
        
        # Algorithm recommendations
        if order.order_type == OrderType.MARKET and order.quantity > 5000:
            recommendations.append("Consider using TWAP or VWAP for large market orders")
        
        return recommendations
    
    async def _update_execution_stats(self, report: ExecutionReport) -> None:
        """Update execution statistics"""
        
        with self._lock:
            stats = self._execution_stats
            
            # Update counters
            stats['total_orders_executed'] += 1
            stats['total_volume_executed'] += report.metrics.executed_quantity
            
            # Update averages
            current_count = stats['total_orders_executed']
            
            # Average slippage
            current_avg_slippage = stats['average_slippage_bps']
            new_slippage = report.metrics.slippage_bps
            stats['average_slippage_bps'] = (
                (current_avg_slippage * (current_count - 1) + new_slippage) / current_count
            )
            
            # Average execution time
            current_avg_time = stats['average_execution_time']
            new_time = report.metrics.execution_time_seconds
            stats['average_execution_time'] = (
                (current_avg_time * (current_count - 1) + new_time) / current_count
            )
            
            # Fill rate
            fill_rate = report.metrics.executed_quantity / report.metrics.total_quantity
            current_fill_rate = stats['fill_rate']
            stats['fill_rate'] = (
                (current_fill_rate * (current_count - 1) + fill_rate) / current_count
            )
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        with self._lock:
            return self._execution_stats.copy()
    
    def get_execution_reports(self, hours: int = 24) -> List[ExecutionReport]:
        """Get recent execution reports"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                report for report in self._execution_reports
                if report.timestamp >= cutoff_time
            ]
    
    async def cleanup(self) -> None:
        """Cleanup execution handler resources"""
        logger.info("ExecutionHandler cleanup completed")