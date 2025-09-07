"""
Smart Order Routing System

Professional-grade smart order routing with:
- Multi-venue execution optimization
- Real-time venue selection
- Liquidity aggregation
- Cost-aware routing decisions
- Fill probability optimization
- Latency-sensitive routing

Author: Pro Quant Desk Trader
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod

# Import execution engine components
from .unified_execution_engine import ExecutionRequest, ExecutionResult, ExecutionStatus
from .order_manager import Order, OrderType, OrderSide, OrderStatus
from .market_impact import MarketConditions
from .transaction_cost_optimizer import VenueCharacteristics, VenueType


class RoutingStrategy(Enum):
    """Order routing strategies"""
    COST_MINIMIZATION = "cost_minimization"
    SPEED_OPTIMIZATION = "speed_optimization"
    FILL_PROBABILITY = "fill_probability"
    MARKET_IMPACT = "market_impact"
    LIQUIDITY_SEEKING = "liquidity_seeking"
    SMART_ROUTING = "smart_routing"


class VenueStatus(Enum):
    """Venue operational status"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


@dataclass
class ExecutionVenue:
    """Execution venue definition"""
    venue_id: str
    venue_name: str
    venue_type: VenueType
    
    # Operational status
    status: VenueStatus = VenueStatus.ACTIVE
    uptime: float = 0.999
    latency_ms: float = 1.0
    
    # Liquidity characteristics
    average_spread_bps: float = 10.0
    depth_shares: int = 1000
    fill_probability: float = 0.95
    
    # Cost structure
    maker_rebate_bps: float = 2.0
    taker_fee_bps: float = 30.0
    
    # Order constraints
    min_order_size: int = 1
    max_order_size: int = 1_000_000
    tick_size: float = 0.01
    
    # Performance metrics
    average_fill_time_ms: float = 100.0
    reject_rate: float = 0.01
    
    # Market data
    last_trade_price: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    
    @property
    def is_available(self) -> bool:
        """Check if venue is available for trading"""
        return self.status in [VenueStatus.ACTIVE, VenueStatus.DEGRADED]
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        if self.bid_price > 0 and self.ask_price > 0:
            return (self.bid_price + self.ask_price) / 2
        return self.last_trade_price
    
    @property
    def spread_bps(self) -> float:
        """Calculate current spread in basis points"""
        if self.bid_price > 0 and self.ask_price > 0 and self.mid_price > 0:
            return ((self.ask_price - self.bid_price) / self.mid_price) * 10000
        return self.average_spread_bps
    
    def get_expected_cost(self, order_side: OrderSide, quantity: int, 
                         is_aggressive: bool = True) -> float:
        """Calculate expected execution cost"""
        if is_aggressive:
            # Market order or aggressive limit
            cost_bps = self.taker_fee_bps + self.spread_bps / 2
        else:
            # Passive limit order
            cost_bps = -self.maker_rebate_bps  # Negative for rebate
        
        # Adjust for quantity (larger orders have higher impact)
        if quantity > self.depth_shares:
            impact_multiplier = np.sqrt(quantity / self.depth_shares)
            cost_bps *= impact_multiplier
        
        return cost_bps
    
    def can_handle_order(self, quantity: int) -> bool:
        """Check if venue can handle order size"""
        return (self.min_order_size <= quantity <= self.max_order_size and 
                self.is_available)


@dataclass
class RoutingDecision:
    """Order routing decision"""
    venue_id: str
    quantity: int
    order_type: OrderType
    price: Optional[float]
    expected_cost_bps: float
    expected_fill_time_ms: float
    confidence: float
    
    # Reasoning
    routing_strategy: RoutingStrategy
    decision_factors: Dict[str, float] = field(default_factory=dict)
    
    @property
    def expected_cost_dollars(self) -> float:
        """Expected cost in dollars"""
        if self.price:
            return (self.expected_cost_bps / 10000) * self.quantity * self.price
        return 0.0


@dataclass
class RoutingResult:
    """Result of routing decision"""
    original_request: ExecutionRequest
    routing_decisions: List[RoutingDecision]
    total_expected_cost: float
    total_expected_time: float
    
    # Execution results
    executed_decisions: List[RoutingDecision] = field(default_factory=list)
    execution_results: List[ExecutionResult] = field(default_factory=list)
    
    @property
    def total_routed_quantity(self) -> int:
        """Total quantity routed"""
        return sum(decision.quantity for decision in self.routing_decisions)
    
    @property
    def total_executed_quantity(self) -> int:
        """Total quantity executed"""
        return sum(result.executed_quantity for result in self.execution_results)
    
    @property
    def fill_rate(self) -> float:
        """Overall fill rate"""
        if self.original_request.quantity == 0:
            return 0.0
        return (self.total_executed_quantity / self.original_request.quantity) * 100


class VenueSelector:
    """Venue selection engine"""
    
    def __init__(self, venues: List[ExecutionVenue]):
        self.venues = {venue.venue_id: venue for venue in venues}
        self.venue_performance = {}  # Track historical performance
        self.logger = logging.getLogger(__name__)
        
    def select_venues(self, request: ExecutionRequest, 
                     market_conditions: MarketConditions,
                     routing_strategy: RoutingStrategy) -> List[RoutingDecision]:
        """Select optimal venues for order execution"""
        
        # Filter available venues
        available_venues = [venue for venue in self.venues.values() 
                          if venue.can_handle_order(request.quantity)]
        
        if not available_venues:
            self.logger.warning(f"No available venues for order: {request.symbol} {request.quantity}")
            return []
        
        # Score venues based on strategy
        venue_scores = {}
        for venue in available_venues:
            score = self._calculate_venue_score(venue, request, market_conditions, routing_strategy)
            venue_scores[venue.venue_id] = score
        
        # Select routing approach
        if routing_strategy == RoutingStrategy.SMART_ROUTING:
            return self._smart_routing_decision(request, available_venues, venue_scores)
        else:
            return self._single_venue_decision(request, available_venues, venue_scores, routing_strategy)
    
    def _calculate_venue_score(self, venue: ExecutionVenue, 
                             request: ExecutionRequest,
                             market_conditions: MarketConditions,
                             routing_strategy: RoutingStrategy) -> float:
        """Calculate venue score based on routing strategy"""
        
        # Base factors
        cost_factor = venue.get_expected_cost(request.side, request.quantity, 
                                            request.urgency > 0.5)
        speed_factor = venue.average_fill_time_ms
        fill_factor = venue.fill_probability
        
        # Strategy-specific scoring
        if routing_strategy == RoutingStrategy.COST_MINIMIZATION:
            score = -cost_factor  # Lower cost = higher score
        elif routing_strategy == RoutingStrategy.SPEED_OPTIMIZATION:
            score = -speed_factor  # Lower latency = higher score
        elif routing_strategy == RoutingStrategy.FILL_PROBABILITY:
            score = fill_factor * 100  # Higher fill probability = higher score
        elif routing_strategy == RoutingStrategy.MARKET_IMPACT:
            # Favor venues with better liquidity
            impact_score = venue.depth_shares / max(1, request.quantity)
            score = impact_score * 100
        elif routing_strategy == RoutingStrategy.LIQUIDITY_SEEKING:
            # Favor dark pools and crossing networks
            if venue.venue_type in [VenueType.DARK_POOL, VenueType.CROSSING_NETWORK]:
                score = 100
            else:
                score = venue.depth_shares / 1000  # Liquidity-based score
        else:  # SMART_ROUTING
            # Weighted combination of factors
            score = (
                -cost_factor * 0.4 +           # 40% cost
                -speed_factor * 0.002 +        # 20% speed (scaled)
                fill_factor * 30 +             # 30% fill probability
                (venue.depth_shares / 1000) * 0.1  # 10% liquidity
            )
        
        # Apply venue status penalty
        if venue.status == VenueStatus.DEGRADED:
            score *= 0.8
        elif venue.status != VenueStatus.ACTIVE:
            score = -1000  # Heavily penalize inactive venues
        
        return score
    
    def _smart_routing_decision(self, request: ExecutionRequest,
                              venues: List[ExecutionVenue],
                              venue_scores: Dict[str, float]) -> List[RoutingDecision]:
        """Make smart routing decision across multiple venues"""
        
        # Sort venues by score
        sorted_venues = sorted(venues, key=lambda v: venue_scores[v.venue_id], reverse=True)
        
        decisions = []
        remaining_quantity = request.quantity
        
        # Distribute order across top venues
        for i, venue in enumerate(sorted_venues[:3]):  # Top 3 venues
            if remaining_quantity <= 0:
                break
            
            # Calculate allocation percentage
            if i == 0:
                allocation_pct = 0.6  # 60% to best venue
            elif i == 1:
                allocation_pct = 0.3  # 30% to second best
            else:
                allocation_pct = 0.1  # 10% to third best
            
            # Calculate quantity for this venue
            venue_quantity = min(
                int(request.quantity * allocation_pct),
                remaining_quantity,
                venue.max_order_size
            )
            
            if venue_quantity < venue.min_order_size:
                continue
            
            # Determine order type and price
            if request.urgency > 0.7:
                order_type = OrderType.MARKET
                price = None
            else:
                order_type = OrderType.LIMIT
                if request.side == OrderSide.BUY:
                    price = venue.bid_price if venue.bid_price > 0 else venue.mid_price
                else:
                    price = venue.ask_price if venue.ask_price > 0 else venue.mid_price
            
            # Create routing decision
            decision = RoutingDecision(
                venue_id=venue.venue_id,
                quantity=venue_quantity,
                order_type=order_type,
                price=price,
                expected_cost_bps=venue.get_expected_cost(request.side, venue_quantity, 
                                                        order_type == OrderType.MARKET),
                expected_fill_time_ms=venue.average_fill_time_ms,
                confidence=venue.fill_probability,
                routing_strategy=RoutingStrategy.SMART_ROUTING,
                decision_factors={
                    'venue_score': venue_scores[venue.venue_id],
                    'cost_factor': venue.get_expected_cost(request.side, venue_quantity),
                    'speed_factor': venue.average_fill_time_ms,
                    'fill_probability': venue.fill_probability,
                    'allocation_pct': allocation_pct
                }
            )
            
            decisions.append(decision)
            remaining_quantity -= venue_quantity
        
        # If quantity remains, put it on the best venue
        if remaining_quantity > 0 and decisions:
            decisions[0].quantity += remaining_quantity
        
        return decisions
    
    def _single_venue_decision(self, request: ExecutionRequest,
                             venues: List[ExecutionVenue],
                             venue_scores: Dict[str, float],
                             routing_strategy: RoutingStrategy) -> List[RoutingDecision]:
        """Route entire order to single best venue"""
        
        # Select best venue
        best_venue = max(venues, key=lambda v: venue_scores[v.venue_id])
        
        # Determine order type
        if request.urgency > 0.7 or routing_strategy == RoutingStrategy.SPEED_OPTIMIZATION:
            order_type = OrderType.MARKET
            price = None
        else:
            order_type = OrderType.LIMIT
            if request.side == OrderSide.BUY:
                price = best_venue.bid_price if best_venue.bid_price > 0 else best_venue.mid_price
            else:
                price = best_venue.ask_price if best_venue.ask_price > 0 else best_venue.mid_price
        
        decision = RoutingDecision(
            venue_id=best_venue.venue_id,
            quantity=request.quantity,
            order_type=order_type,
            price=price,
            expected_cost_bps=best_venue.get_expected_cost(request.side, request.quantity,
                                                         order_type == OrderType.MARKET),
            expected_fill_time_ms=best_venue.average_fill_time_ms,
            confidence=best_venue.fill_probability,
            routing_strategy=routing_strategy,
            decision_factors={
                'venue_score': venue_scores[best_venue.venue_id],
                'selected_reason': f'Best venue for {routing_strategy.value}'
            }
        )
        
        return [decision]
    
    def update_venue_performance(self, venue_id: str, 
                               execution_result: ExecutionResult):
        """Update venue performance metrics"""
        if venue_id not in self.venue_performance:
            self.venue_performance[venue_id] = {
                'total_orders': 0,
                'successful_orders': 0,
                'total_quantity': 0,
                'filled_quantity': 0,
                'average_fill_time': 0.0,
                'average_cost': 0.0
            }
        
        perf = self.venue_performance[venue_id]
        perf['total_orders'] += 1
        perf['total_quantity'] += execution_result.requested_quantity
        perf['filled_quantity'] += execution_result.executed_quantity
        
        if execution_result.status == ExecutionStatus.SUCCESS:
            perf['successful_orders'] += 1
        
        # Update averages
        n = perf['total_orders']
        perf['average_fill_time'] = (
            (perf['average_fill_time'] * (n-1) + execution_result.execution_time) / n
        )
        perf['average_cost'] = (
            (perf['average_cost'] * (n-1) + execution_result.total_cost) / n
        )
    
    def get_venue_rankings(self, routing_strategy: RoutingStrategy) -> List[Dict[str, Any]]:
        """Get venue rankings for given strategy"""
        rankings = []
        
        for venue_id, venue in self.venues.items():
            perf = self.venue_performance.get(venue_id, {})
            
            ranking = {
                'venue_id': venue_id,
                'venue_name': venue.venue_name,
                'venue_type': venue.venue_type.value,
                'status': venue.status.value,
                'fill_probability': venue.fill_probability,
                'average_cost_bps': venue.get_expected_cost(OrderSide.BUY, 1000),
                'latency_ms': venue.latency_ms,
                'historical_fill_rate': (
                    perf.get('filled_quantity', 0) / max(1, perf.get('total_quantity', 1))
                ) * 100,
                'historical_success_rate': (
                    perf.get('successful_orders', 0) / max(1, perf.get('total_orders', 1))
                ) * 100
            }
            
            rankings.append(ranking)
        
        # Sort by strategy-specific criteria
        if routing_strategy == RoutingStrategy.COST_MINIMIZATION:
            rankings.sort(key=lambda x: x['average_cost_bps'])
        elif routing_strategy == RoutingStrategy.SPEED_OPTIMIZATION:
            rankings.sort(key=lambda x: x['latency_ms'])
        elif routing_strategy == RoutingStrategy.FILL_PROBABILITY:
            rankings.sort(key=lambda x: x['fill_probability'], reverse=True)
        
        return rankings


class SmartOrderRouter:
    """
    Smart order routing system
    
    Features:
    - Multi-venue execution optimization
    - Real-time venue selection
    - Adaptive routing strategies
    - Performance tracking
    - Cost optimization
    """
    
    def __init__(self, venues: List[ExecutionVenue]):
        self.venue_selector = VenueSelector(venues)
        self.routing_history = []
        self.logger = logging.getLogger(__name__)
        
        # Default routing strategies by order characteristics
        self.default_strategies = {
            'large_urgent': RoutingStrategy.SMART_ROUTING,
            'large_patient': RoutingStrategy.COST_MINIMIZATION,
            'small_urgent': RoutingStrategy.SPEED_OPTIMIZATION,
            'small_patient': RoutingStrategy.FILL_PROBABILITY
        }
    
    async def route_order(self, request: ExecutionRequest,
                         market_conditions: MarketConditions,
                         routing_strategy: Optional[RoutingStrategy] = None) -> RoutingResult:
        """
        Route order to optimal venues
        
        Args:
            request: Execution request
            market_conditions: Current market conditions
            routing_strategy: Routing strategy (auto-selected if None)
            
        Returns:
            RoutingResult with routing decisions
        """
        start_time = datetime.now()
        
        # Auto-select routing strategy if not specified
        if routing_strategy is None:
            routing_strategy = self._select_routing_strategy(request, market_conditions)
        
        self.logger.info(f"Routing order: {request.symbol} {request.quantity} "
                        f"using {routing_strategy.value}")
        
        # Get routing decisions
        routing_decisions = self.venue_selector.select_venues(
            request, market_conditions, routing_strategy
        )
        
        if not routing_decisions:
            return RoutingResult(
                original_request=request,
                routing_decisions=[],
                total_expected_cost=0.0,
                total_expected_time=0.0
            )
        
        # Calculate expected totals
        total_expected_cost = sum(d.expected_cost_dollars for d in routing_decisions)
        total_expected_time = max(d.expected_fill_time_ms for d in routing_decisions)
        
        # Create result
        result = RoutingResult(
            original_request=request,
            routing_decisions=routing_decisions,
            total_expected_cost=total_expected_cost,
            total_expected_time=total_expected_time
        )
        
        # Store routing history
        self.routing_history.append({
            'timestamp': start_time,
            'request': request,
            'strategy': routing_strategy,
            'decisions': routing_decisions,
            'market_conditions': market_conditions
        })
        
        return result
    
    def _select_routing_strategy(self, request: ExecutionRequest,
                               market_conditions: MarketConditions) -> RoutingStrategy:
        """Auto-select optimal routing strategy"""
        
        # Classify order
        is_large = request.quantity > 10000  # Threshold for large orders
        is_urgent = request.urgency > 0.6
        
        # Select strategy based on order characteristics
        if is_large and is_urgent:
            return self.default_strategies['large_urgent']
        elif is_large and not is_urgent:
            return self.default_strategies['large_patient']
        elif not is_large and is_urgent:
            return self.default_strategies['small_urgent']
        else:
            return self.default_strategies['small_patient']
    
    async def execute_routing_decisions(self, routing_result: RoutingResult,
                                      execution_engine) -> RoutingResult:
        """Execute routing decisions"""
        
        execution_tasks = []
        
        for decision in routing_result.routing_decisions:
            # Create execution request for this venue
            venue_request = ExecutionRequest(
                symbol=routing_result.original_request.symbol,
                side=routing_result.original_request.side,
                quantity=decision.quantity,
                algorithm=routing_result.original_request.algorithm,
                target_price=decision.price,
                urgency=routing_result.original_request.urgency,
                strategy_id=routing_result.original_request.strategy_id,
                metadata={'venue_id': decision.venue_id}
            )
            
            # Execute on venue
            task = execution_engine.execute_order(venue_request)
            execution_tasks.append((decision, task))
        
        # Wait for all executions to complete
        for decision, task in execution_tasks:
            try:
                execution_result = await task
                routing_result.executed_decisions.append(decision)
                routing_result.execution_results.append(execution_result)
                
                # Update venue performance
                self.venue_selector.update_venue_performance(
                    decision.venue_id, execution_result
                )
                
            except Exception as e:
                self.logger.error(f"Execution failed for venue {decision.venue_id}: {str(e)}")
        
        return routing_result
    
    def get_routing_analytics(self) -> Dict[str, Any]:
        """Get routing analytics and performance metrics"""
        
        if not self.routing_history:
            return {'total_routings': 0}
        
        # Calculate routing statistics
        total_routings = len(self.routing_history)
        strategy_usage = {}
        venue_usage = {}
        
        for record in self.routing_history:
            strategy = record['strategy'].value
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
            
            for decision in record['decisions']:
                venue_id = decision.venue_id
                venue_usage[venue_id] = venue_usage.get(venue_id, 0) + 1
        
        # Calculate success rates
        successful_routings = sum(1 for record in self.routing_history 
                                if len(record['decisions']) > 0)
        
        return {
            'total_routings': total_routings,
            'success_rate': (successful_routings / total_routings) * 100,
            'strategy_usage': strategy_usage,
            'venue_usage': venue_usage,
            'venue_performance': self.venue_selector.venue_performance,
            'available_venues': len(self.venue_selector.venues),
            'active_venues': len([v for v in self.venue_selector.venues.values() 
                                if v.status == VenueStatus.ACTIVE])
        }
    
    def update_venue_status(self, venue_id: str, status: VenueStatus):
        """Update venue operational status"""
        if venue_id in self.venue_selector.venues:
            self.venue_selector.venues[venue_id].status = status
            self.logger.info(f"Updated venue {venue_id} status to {status.value}")
    
    def add_venue(self, venue: ExecutionVenue):
        """Add new execution venue"""
        self.venue_selector.venues[venue.venue_id] = venue
        self.logger.info(f"Added venue: {venue.venue_name} ({venue.venue_id})")
    
    def remove_venue(self, venue_id: str):
        """Remove execution venue"""
        if venue_id in self.venue_selector.venues:
            del self.venue_selector.venues[venue_id]
            self.logger.info(f"Removed venue: {venue_id}")
    
    def get_venue_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current status of all venues"""
        status = {}
        
        for venue_id, venue in self.venue_selector.venues.items():
            status[venue_id] = {
                'name': venue.venue_name,
                'type': venue.venue_type.value,
                'status': venue.status.value,
                'uptime': venue.uptime,
                'latency_ms': venue.latency_ms,
                'fill_probability': venue.fill_probability,
                'last_update': venue.last_update.isoformat()
            }
        
        return status 