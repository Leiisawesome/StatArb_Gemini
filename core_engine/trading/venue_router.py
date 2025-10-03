"""
Trading Engine - Venue Router
Intelligent routing across multiple execution venues with cost optimization and liquidity aggregation
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .order_manager import Order, OrderSide, OrderType, OrderStatus
from .execution_handler import ExecutionStrategy

logger = logging.getLogger(__name__)


class VenueType(Enum):
    """Execution venue types"""
    EXCHANGE = "exchange"
    DARK_POOL = "dark_pool"
    ECN = "ecn"
    CROSSING_NETWORK = "crossing_network"
    INTERNALIZATION = "internalization"
    ALTERNATIVE_VENUE = "alternative_venue"


class VenueStatus(Enum):
    """Venue operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


@dataclass
class VenueProfile:
    """Execution venue profile and characteristics"""
    venue_id: str
    name: str
    venue_type: VenueType
    status: VenueStatus
    
    # Trading characteristics
    supported_order_types: Set[OrderType]
    supported_symbols: Set[str]
    min_order_size: float
    max_order_size: float
    tick_size: float
    
    # Liquidity characteristics
    typical_depth: float
    fill_rate: float
    average_fill_size: float
    dark_pool_indicator: bool
    
    # Cost characteristics
    commission_rate: float
    fee_structure: Dict[str, float]
    rebate_rate: float
    access_fee: float
    
    # Performance metrics
    average_latency_ms: float
    success_rate: float
    rejection_rate: float
    market_impact_factor: float
    
    # Operational details
    trading_hours: Dict[str, str]
    connectivity_type: str
    api_version: str
    
    # Real-time metrics
    current_volume: float = 0
    current_spread_bps: float = 0
    queue_depth: int = 0
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class RouteOption:
    """Individual routing option"""
    venue_id: str
    allocation_percentage: float
    expected_fill_rate: float
    estimated_cost_bps: float
    estimated_impact_bps: float
    estimated_latency_ms: float
    priority_score: float
    
    # Risk factors
    concentration_risk: float
    venue_risk_score: float
    liquidity_risk: float


@dataclass
class RoutingPlan:
    """Complete routing plan for an order"""
    order_id: str
    symbol: str
    total_quantity: float
    route_options: List[RouteOption]
    
    # Plan characteristics
    total_expected_fill_rate: float
    weighted_average_cost_bps: float
    estimated_completion_time_ms: float
    risk_score: float
    
    # Strategy parameters
    routing_strategy: str
    optimization_objective: str
    constraints: Dict[str, Any]
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VenueExecution:
    """Execution result from a specific venue"""
    venue_id: str
    order_id: str
    child_order_id: str
    
    quantity_sent: float
    quantity_filled: float
    fill_rate: float
    
    average_price: float
    total_value: float
    commission: float
    fees: float
    
    execution_time_ms: float
    latency_ms: float
    
    status: OrderStatus
    rejection_reason: Optional[str] = None
    
    timestamp: datetime = field(default_factory=datetime.now)


class RoutingStrategy(Enum):
    """Routing optimization strategies"""
    BEST_PRICE = "best_price"
    LOWEST_COST = "lowest_cost"
    FASTEST_EXECUTION = "fastest_execution"
    HIGHEST_FILL_RATE = "highest_fill_rate"
    BALANCED = "balanced"
    DARK_FIRST = "dark_first"
    FRAGMENTED = "fragmented"
    CONCENTRATED = "concentrated"


class VenueRouter:
    """
    Intelligent venue router for order execution
    
    Provides sophisticated routing logic across multiple execution venues
    with cost optimization, liquidity aggregation, and risk management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize venue router"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Venue management
        self._venues = {}
        self._venue_groups = defaultdict(list)
        self._dark_pools = set()
        
        # Routing tracking
        self._routing_plans = deque(maxlen=1000)
        self._executions_by_venue = defaultdict(list)
        self._routing_performance = defaultdict(dict)
        
        # Market data and analytics
        self._venue_analytics = defaultdict(dict)
        self._liquidity_matrix = defaultdict(dict)
        self._cost_matrix = defaultdict(dict)
        
        # Configuration
        self.max_venues_per_order = self.config.get('max_venues_per_order', 4)
        self.min_allocation_percentage = self.config.get('min_allocation_percentage', 5.0)
        self.default_routing_strategy = RoutingStrategy(
            self.config.get('default_routing_strategy', 'balanced')
        )
        
        # Risk limits
        self.max_venue_concentration = self.config.get('max_venue_concentration', 50.0)
        self.max_dark_pool_allocation = self.config.get('max_dark_pool_allocation', 40.0)
        
        # Initialize default venues
        asyncio.create_task(self._initialize_default_venues())
        
        # Performance tracking
        self._routing_stats = {
            'total_orders_routed': 0,
            'average_fill_rate': 0.0,
            'average_cost_bps': 0.0,
            'average_completion_time_ms': 0.0,
            'venue_utilization': defaultdict(float),
            'routing_efficiency_score': 0.0
        }
        
        logger.info("VenueRouter initialized")
    
    async def _initialize_default_venues(self) -> None:
        """Initialize default venue profiles"""
        
        # Major exchanges
        await self.register_venue(VenueProfile(
            venue_id="NASDAQ",
            name="NASDAQ Stock Market",
            venue_type=VenueType.EXCHANGE,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.MARKET, OrderType.LIMIT, OrderType.STOP},
            supported_symbols={"*"},  # All symbols
            min_order_size=1,
            max_order_size=1000000,
            tick_size=0.01,
            typical_depth=50000,
            fill_rate=0.95,
            average_fill_size=2500,
            dark_pool_indicator=False,
            commission_rate=0.002,
            fee_structure={"access_fee": 0.003, "liquidity_rebate": -0.001},
            rebate_rate=0.001,
            access_fee=0.003,
            average_latency_ms=2.5,
            success_rate=0.98,
            rejection_rate=0.02,
            market_impact_factor=1.0,
            trading_hours={"open": "09:30", "close": "16:00"},
            connectivity_type="FIX",
            api_version="4.4"
        ))
        
        await self.register_venue(VenueProfile(
            venue_id="NYSE",
            name="New York Stock Exchange",
            venue_type=VenueType.EXCHANGE,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.MARKET, OrderType.LIMIT, OrderType.STOP},
            supported_symbols={"*"},
            min_order_size=1,
            max_order_size=1000000,
            tick_size=0.01,
            typical_depth=45000,
            fill_rate=0.93,
            average_fill_size=2200,
            dark_pool_indicator=False,
            commission_rate=0.002,
            fee_structure={"access_fee": 0.003, "liquidity_rebate": -0.001},
            rebate_rate=0.001,
            access_fee=0.003,
            average_latency_ms=3.0,
            success_rate=0.97,
            rejection_rate=0.03,
            market_impact_factor=1.1,
            trading_hours={"open": "09:30", "close": "16:00"},
            connectivity_type="FIX",
            api_version="4.4"
        ))
        
        # Dark pools
        await self.register_venue(VenueProfile(
            venue_id="CROSSFINDER",
            name="Credit Suisse CrossFinder",
            venue_type=VenueType.DARK_POOL,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.LIMIT, OrderType.MARKET},
            supported_symbols={"*"},
            min_order_size=100,
            max_order_size=500000,
            tick_size=0.01,
            typical_depth=25000,
            fill_rate=0.65,
            average_fill_size=1800,
            dark_pool_indicator=True,
            commission_rate=0.001,
            fee_structure={"access_fee": 0.001},
            rebate_rate=0.0,
            access_fee=0.001,
            average_latency_ms=15.0,
            success_rate=0.92,
            rejection_rate=0.08,
            market_impact_factor=0.3,
            trading_hours={"open": "09:30", "close": "16:00"},
            connectivity_type="FIX",
            api_version="4.4"
        ))
        
        await self.register_venue(VenueProfile(
            venue_id="SIGMA_X",
            name="Goldman Sachs Sigma X",
            venue_type=VenueType.DARK_POOL,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.LIMIT, OrderType.MARKET},
            supported_symbols={"*"},
            min_order_size=100,
            max_order_size=500000,
            tick_size=0.01,
            typical_depth=30000,
            fill_rate=0.70,
            average_fill_size=2100,
            dark_pool_indicator=True,
            commission_rate=0.0012,
            fee_structure={"access_fee": 0.0012},
            rebate_rate=0.0,
            access_fee=0.0012,
            average_latency_ms=12.0,
            success_rate=0.94,
            rejection_rate=0.06,
            market_impact_factor=0.25,
            trading_hours={"open": "09:30", "close": "16:00"},
            connectivity_type="FIX",
            api_version="4.4"
        ))
        
        # ECN
        await self.register_venue(VenueProfile(
            venue_id="ARCA",
            name="NYSE Arca",
            venue_type=VenueType.ECN,
            status=VenueStatus.ACTIVE,
            supported_order_types={OrderType.MARKET, OrderType.LIMIT, OrderType.STOP},
            supported_symbols={"*"},
            min_order_size=1,
            max_order_size=1000000,
            tick_size=0.01,
            typical_depth=35000,
            fill_rate=0.88,
            average_fill_size=1900,
            dark_pool_indicator=False,
            commission_rate=0.0015,
            fee_structure={"access_fee": 0.0025, "liquidity_rebate": -0.0015},
            rebate_rate=0.0015,
            access_fee=0.0025,
            average_latency_ms=1.8,
            success_rate=0.96,
            rejection_rate=0.04,
            market_impact_factor=0.8,
            trading_hours={"open": "09:30", "close": "16:00"},
            connectivity_type="FIX",
            api_version="4.4"
        ))
        
        # Update venue groups
        self._venue_groups['exchanges'] = ['NASDAQ', 'NYSE']
        self._venue_groups['dark_pools'] = ['CROSSFINDER', 'SIGMA_X']
        self._venue_groups['ecns'] = ['ARCA']
        self._dark_pools = {'CROSSFINDER', 'SIGMA_X'}
    
    async def register_venue(self, venue_profile: VenueProfile) -> None:
        """Register a new execution venue"""
        with self._lock:
            self._venues[venue_profile.venue_id] = venue_profile
            
            if venue_profile.dark_pool_indicator:
                self._dark_pools.add(venue_profile.venue_id)
        
        logger.info(f"Registered venue: {venue_profile.name} ({venue_profile.venue_id})")
    
    async def create_routing_plan(
        self,
        order: Order,
        routing_strategy: Optional[RoutingStrategy] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> RoutingPlan:
        """
        Create optimal routing plan for an order
        
        Args:
            order: Order to route
            routing_strategy: Routing optimization strategy
            constraints: Additional routing constraints
            
        Returns:
            Optimal routing plan
        """
        try:
            logger.debug(f"Creating routing plan for order {order.order_id}")
            
            strategy = routing_strategy or self.default_routing_strategy
            constraints = constraints or {}
            
            # Get eligible venues
            eligible_venues = await self._get_eligible_venues(order, constraints)
            
            if not eligible_venues:
                raise ValueError(f"No eligible venues found for order {order.order_id}")
            
            # Analyze venue characteristics
            venue_analysis = await self._analyze_venue_characteristics(
                order, eligible_venues
            )
            
            # Generate route options
            route_options = await self._generate_route_options(
                order, venue_analysis, strategy, constraints
            )
            
            # Optimize allocation
            optimized_routes = await self._optimize_allocation(
                order, route_options, strategy, constraints
            )
            
            # Calculate plan metrics
            plan_metrics = await self._calculate_plan_metrics(optimized_routes)
            
            # Create routing plan
            routing_plan = RoutingPlan(
                order_id=order.order_id,
                symbol=order.symbol,
                total_quantity=order.quantity,
                route_options=optimized_routes,
                total_expected_fill_rate=plan_metrics['fill_rate'],
                weighted_average_cost_bps=plan_metrics['cost_bps'],
                estimated_completion_time_ms=plan_metrics['completion_time_ms'],
                risk_score=plan_metrics['risk_score'],
                routing_strategy=strategy.value,
                optimization_objective=self._get_optimization_objective(strategy),
                constraints=constraints
            )
            
            # Store routing plan
            with self._lock:
                self._routing_plans.append(routing_plan)
            
            logger.info(f"Created routing plan: {len(optimized_routes)} venues, "
                       f"{plan_metrics['fill_rate']:.1%} fill rate, "
                       f"{plan_metrics['cost_bps']:.2f} bps cost")
            
            return routing_plan
            
        except Exception as e:
            logger.error(f"Error creating routing plan: {e}")
            raise
    
    async def _get_eligible_venues(
        self,
        order: Order,
        constraints: Dict[str, Any]
    ) -> List[VenueProfile]:
        """Get eligible venues for order execution"""
        
        eligible_venues = []
        
        with self._lock:
            for venue in self._venues.values():
                # Check basic eligibility
                if (venue.status != VenueStatus.ACTIVE or
                    order.order_type not in venue.supported_order_types or
                    order.quantity < venue.min_order_size or
                    order.quantity > venue.max_order_size):
                    continue
                
                # Check symbol support
                if "*" not in venue.supported_symbols and order.symbol not in venue.supported_symbols:
                    continue
                
                # Check constraints
                if self._check_venue_constraints(venue, constraints):
                    eligible_venues.append(venue)
        
        return eligible_venues
    
    def _check_venue_constraints(
        self,
        venue: VenueProfile,
        constraints: Dict[str, Any]
    ) -> bool:
        """Check if venue meets constraints"""
        
        # Venue type constraints
        if 'allowed_venue_types' in constraints:
            if venue.venue_type not in constraints['allowed_venue_types']:
                return False
        
        if 'excluded_venue_types' in constraints:
            if venue.venue_type in constraints['excluded_venue_types']:
                return False
        
        # Specific venue constraints
        if 'allowed_venues' in constraints:
            if venue.venue_id not in constraints['allowed_venues']:
                return False
        
        if 'excluded_venues' in constraints:
            if venue.venue_id in constraints['excluded_venues']:
                return False
        
        # Performance constraints
        if 'min_fill_rate' in constraints:
            if venue.fill_rate < constraints['min_fill_rate']:
                return False
        
        if 'max_latency_ms' in constraints:
            if venue.average_latency_ms > constraints['max_latency_ms']:
                return False
        
        return True
    
    async def _analyze_venue_characteristics(
        self,
        order: Order,
        venues: List[VenueProfile]
    ) -> Dict[str, Dict[str, float]]:
        """Analyze venue characteristics for the specific order"""
        
        analysis = {}
        
        for venue in venues:
            # Calculate order-specific metrics
            size_factor = min(1.0, order.quantity / venue.typical_depth)
            
            # Adjust fill rate based on order size
            adjusted_fill_rate = venue.fill_rate * (1 - size_factor * 0.3)
            
            # Estimate cost based on venue characteristics
            base_cost_bps = venue.commission_rate * 10000
            spread_cost_bps = venue.current_spread_bps or 5.0  # Default 5 bps
            impact_cost_bps = venue.market_impact_factor * size_factor * 10
            
            total_cost_bps = base_cost_bps + spread_cost_bps + impact_cost_bps
            
            # Calculate latency including queue time
            queue_delay = venue.queue_depth * 0.1  # Estimate 0.1ms per order in queue
            total_latency = venue.average_latency_ms + queue_delay
            
            analysis[venue.venue_id] = {
                'adjusted_fill_rate': adjusted_fill_rate,
                'estimated_cost_bps': total_cost_bps,
                'estimated_latency_ms': total_latency,
                'size_factor': size_factor,
                'liquidity_score': min(1.0, venue.typical_depth / order.quantity),
                'reliability_score': venue.success_rate,
                'dark_pool_flag': venue.dark_pool_indicator
            }
        
        return analysis
    
    async def _generate_route_options(
        self,
        order: Order,
        venue_analysis: Dict[str, Dict[str, float]],
        strategy: RoutingStrategy,
        constraints: Dict[str, Any]
    ) -> List[RouteOption]:
        """Generate routing options based on strategy"""
        
        route_options = []
        
        for venue_id, analysis in venue_analysis.items():
            # Calculate priority score based on strategy
            priority_score = await self._calculate_priority_score(
                venue_id, analysis, strategy
            )
            
            # Calculate risk factors
            venue = self._venues[venue_id]
            concentration_risk = min(1.0, order.quantity / venue.typical_depth)
            venue_risk_score = 1 - venue.success_rate
            liquidity_risk = 1 - analysis['liquidity_score']
            
            route_option = RouteOption(
                venue_id=venue_id,
                allocation_percentage=0,  # Will be set during optimization
                expected_fill_rate=analysis['adjusted_fill_rate'],
                estimated_cost_bps=analysis['estimated_cost_bps'],
                estimated_impact_bps=analysis['size_factor'] * venue.market_impact_factor * 10,
                estimated_latency_ms=analysis['estimated_latency_ms'],
                priority_score=priority_score,
                concentration_risk=concentration_risk,
                venue_risk_score=venue_risk_score,
                liquidity_risk=liquidity_risk
            )
            
            route_options.append(route_option)
        
        # Sort by priority score
        route_options.sort(key=lambda x: x.priority_score, reverse=True)
        
        return route_options
    
    async def _calculate_priority_score(
        self,
        venue_id: str,
        analysis: Dict[str, float],
        strategy: RoutingStrategy
    ) -> float:
        """Calculate venue priority score based on routing strategy"""
        
        if strategy == RoutingStrategy.BEST_PRICE:
            # Prioritize low cost and high fill rate
            cost_score = max(0, 100 - analysis['estimated_cost_bps'])
            fill_score = analysis['adjusted_fill_rate'] * 100
            return (cost_score * 0.6 + fill_score * 0.4)
        
        elif strategy == RoutingStrategy.LOWEST_COST:
            # Prioritize lowest cost
            return max(0, 100 - analysis['estimated_cost_bps'])
        
        elif strategy == RoutingStrategy.FASTEST_EXECUTION:
            # Prioritize low latency and high fill rate
            latency_score = max(0, 100 - analysis['estimated_latency_ms'])
            fill_score = analysis['adjusted_fill_rate'] * 100
            return (latency_score * 0.7 + fill_score * 0.3)
        
        elif strategy == RoutingStrategy.HIGHEST_FILL_RATE:
            # Prioritize fill rate
            return analysis['adjusted_fill_rate'] * 100
        
        elif strategy == RoutingStrategy.DARK_FIRST:
            # Prioritize dark pools
            if analysis['dark_pool_flag']:
                base_score = analysis['adjusted_fill_rate'] * 100
                return base_score + 50  # Bonus for dark pools
            else:
                return analysis['adjusted_fill_rate'] * 50
        
        elif strategy == RoutingStrategy.BALANCED:
            # Balanced approach
            cost_score = max(0, 100 - analysis['estimated_cost_bps'])
            fill_score = analysis['adjusted_fill_rate'] * 100
            latency_score = max(0, 100 - analysis['estimated_latency_ms'])
            liquidity_score = analysis['liquidity_score'] * 100
            
            return (cost_score * 0.3 + fill_score * 0.3 + 
                   latency_score * 0.2 + liquidity_score * 0.2)
        
        else:
            # Default balanced scoring
            return analysis['adjusted_fill_rate'] * 100
    
    async def _optimize_allocation(
        self,
        order: Order,
        route_options: List[RouteOption],
        strategy: RoutingStrategy,
        constraints: Dict[str, Any]
    ) -> List[RouteOption]:
        """Optimize allocation across venues"""
        
        # Limit number of venues
        max_venues = min(self.max_venues_per_order, len(route_options))
        top_venues = route_options[:max_venues]
        
        # Calculate initial allocations based on priority scores
        total_priority = sum(option.priority_score for option in top_venues)
        
        if total_priority == 0:
            # Equal allocation if no priority differences
            allocation_each = 100.0 / len(top_venues)
            for option in top_venues:
                option.allocation_percentage = allocation_each
        else:
            # Weighted allocation based on priority
            for option in top_venues:
                base_allocation = (option.priority_score / total_priority) * 100
                option.allocation_percentage = max(self.min_allocation_percentage, base_allocation)
        
        # Apply constraints
        top_venues = await self._apply_allocation_constraints(
            top_venues, constraints
        )
        
        # Normalize allocations to 100%
        total_allocation = sum(option.allocation_percentage for option in top_venues)
        if total_allocation > 0:
            for option in top_venues:
                option.allocation_percentage = (option.allocation_percentage / total_allocation) * 100
        
        # Remove venues with allocation below minimum
        final_venues = [
            option for option in top_venues
            if option.allocation_percentage >= self.min_allocation_percentage
        ]
        
        # Re-normalize if venues were removed
        total_allocation = sum(option.allocation_percentage for option in final_venues)
        if total_allocation > 0 and len(final_venues) > 0:
            for option in final_venues:
                option.allocation_percentage = (option.allocation_percentage / total_allocation) * 100
        
        return final_venues
    
    async def _apply_allocation_constraints(
        self,
        route_options: List[RouteOption],
        constraints: Dict[str, Any]
    ) -> List[RouteOption]:
        """Apply allocation constraints"""
        
        # Apply dark pool allocation limit
        dark_pool_allocation = 0
        for option in route_options:
            if option.venue_id in self._dark_pools:
                dark_pool_allocation += option.allocation_percentage
        
        if dark_pool_allocation > self.max_dark_pool_allocation:
            # Scale down dark pool allocations
            scale_factor = self.max_dark_pool_allocation / dark_pool_allocation
            for option in route_options:
                if option.venue_id in self._dark_pools:
                    option.allocation_percentage *= scale_factor
        
        # Apply venue concentration limits
        for option in route_options:
            if option.allocation_percentage > self.max_venue_concentration:
                option.allocation_percentage = self.max_venue_concentration
        
        # Apply custom constraints
        if 'max_allocation_per_venue' in constraints:
            max_allocation = constraints['max_allocation_per_venue']
            for option in route_options:
                option.allocation_percentage = min(option.allocation_percentage, max_allocation)
        
        return route_options
    
    async def _calculate_plan_metrics(
        self,
        route_options: List[RouteOption]
    ) -> Dict[str, float]:
        """Calculate routing plan metrics"""
        
        if not route_options:
            return {
                'fill_rate': 0.0,
                'cost_bps': 0.0,
                'completion_time_ms': 0.0,
                'risk_score': 1.0
            }
        
        # Weighted averages
        total_weight = sum(option.allocation_percentage for option in route_options)
        
        weighted_fill_rate = sum(
            option.expected_fill_rate * option.allocation_percentage
            for option in route_options
        ) / total_weight if total_weight > 0 else 0
        
        weighted_cost_bps = sum(
            option.estimated_cost_bps * option.allocation_percentage
            for option in route_options
        ) / total_weight if total_weight > 0 else 0
        
        # Completion time (maximum latency across venues)
        max_latency = max(option.estimated_latency_ms for option in route_options)
        
        # Risk score (average of risk factors)
        risk_scores = []
        for option in route_options:
            venue_risk = (option.concentration_risk + option.venue_risk_score + 
                         option.liquidity_risk) / 3
            risk_scores.append(venue_risk * option.allocation_percentage / total_weight)
        
        total_risk_score = sum(risk_scores)
        
        return {
            'fill_rate': weighted_fill_rate,
            'cost_bps': weighted_cost_bps,
            'completion_time_ms': max_latency,
            'risk_score': total_risk_score
        }
    
    def _get_optimization_objective(self, strategy: RoutingStrategy) -> str:
        """Get optimization objective description"""
        objectives = {
            RoutingStrategy.BEST_PRICE: "Optimize for best execution price",
            RoutingStrategy.LOWEST_COST: "Minimize total execution costs",
            RoutingStrategy.FASTEST_EXECUTION: "Minimize execution latency",
            RoutingStrategy.HIGHEST_FILL_RATE: "Maximize fill probability",
            RoutingStrategy.BALANCED: "Balance cost, speed, and fill rate",
            RoutingStrategy.DARK_FIRST: "Prioritize dark pool execution",
            RoutingStrategy.FRAGMENTED: "Spread across multiple venues",
            RoutingStrategy.CONCENTRATED: "Concentrate in top venues"
        }
        return objectives.get(strategy, "Balanced optimization")
    
    def get_venue_status(self, venue_id: Optional[str] = None) -> Dict[str, Any]:
        """Get venue status information"""
        if venue_id:
            with self._lock:
                venue = self._venues.get(venue_id)
                if venue:
                    return {
                        'venue_id': venue.venue_id,
                        'name': venue.name,
                        'status': venue.status.value,
                        'venue_type': venue.venue_type.value,
                        'current_volume': venue.current_volume,
                        'queue_depth': venue.queue_depth,
                        'last_update': venue.last_update.isoformat()
                    }
                else:
                    return {'error': 'Venue not found'}
        else:
            with self._lock:
                return {
                    venue_id: {
                        'name': venue.name,
                        'status': venue.status.value,
                        'venue_type': venue.venue_type.value,
                        'current_volume': venue.current_volume,
                        'queue_depth': venue.queue_depth
                    }
                    for venue_id, venue in self._venues.items()
                }
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics"""
        with self._lock:
            return self._routing_stats.copy()
    
    def get_recent_routing_plans(self, hours: int = 24) -> List[RoutingPlan]:
        """Get recent routing plans"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            recent_plans = [
                plan for plan in self._routing_plans
                if plan.timestamp >= cutoff_time
            ]
        
        return recent_plans
    
    async def update_venue_status(
        self,
        venue_id: str,
        status: VenueStatus,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update venue status and metrics"""
        with self._lock:
            venue = self._venues.get(venue_id)
            if venue:
                venue.status = status
                venue.last_update = datetime.now()
                
                if metrics:
                    venue.current_volume = metrics.get('volume', venue.current_volume)
                    venue.current_spread_bps = metrics.get('spread_bps', venue.current_spread_bps)
                    venue.queue_depth = metrics.get('queue_depth', venue.queue_depth)
        
        logger.info(f"Updated venue {venue_id} status to {status.value}")
    
    async def cleanup(self) -> None:
        """Cleanup venue router resources"""
        logger.info("VenueRouter cleanup completed")