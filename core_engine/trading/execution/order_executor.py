"""
Execution Engine - Order Executor
Advanced order execution with sophisticated algorithms and market microstructure optimization
"""

import logging
import threading
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import time
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    MARKET_ON_CLOSE = "market_on_close"
    LIMIT_ON_CLOSE = "limit_on_close"
    ICEBERG = "iceberg"
    HIDDEN = "hidden"
    RESERVE = "reserve"


class TimeInForce(Enum):
    """Time in force options"""
    DAY = "day"
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTC = "gtc"  # Good Till Cancel
    GTD = "gtd"  # Good Till Date
    ATC = "atc"  # At The Close
    ATO = "ato"  # At The Open


class OrderStatus(Enum):
    """Order status"""
    PENDING_NEW = "pending_new"
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PENDING_CANCEL = "pending_cancel"
    CANCELLED = "cancelled"
    PENDING_REPLACE = "pending_replace"
    REPLACED = "replaced"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class ExecutionQuality(Enum):
    """Execution quality levels"""
    AGGRESSIVE = "aggressive"
    NORMAL = "normal"
    PASSIVE = "passive"
    PATIENT = "patient"


@dataclass
class OrderExecutionConfig:
    """Order execution configuration"""
    # Execution parameters
    default_order_type: OrderType = OrderType.LIMIT
    default_time_in_force: TimeInForce = TimeInForce.DAY
    default_execution_quality: ExecutionQuality = ExecutionQuality.NORMAL
    
    # Timing controls
    max_order_lifetime: int = 3600  # 1 hour
    order_refresh_interval: int = 60  # 1 minute
    price_update_threshold: float = 0.001  # 0.1%
    
    # Liquidity seeking
    enable_liquidity_seeking: bool = True
    passive_aggression_ratio: float = 0.7  # 70% passive, 30% aggressive
    hidden_order_ratio: float = 0.2  # 20% hidden volume
    
    # Price improvement
    enable_price_improvement: bool = True
    tick_improvement_enabled: bool = True
    midpoint_pegging: bool = True
    
    # Market microstructure
    book_depth_levels: int = 5
    min_size_at_level: float = 1000  # Minimum size to consider level
    spread_crossing_threshold: float = 0.5  # Cross spread if < 0.5 tick wide
    
    # Risk controls
    max_order_size: float = 1_000_000
    concentration_limit: float = 0.1  # 10% of daily volume
    adverse_selection_threshold: float = 0.002  # 20 bps
    
    # Performance tracking
    benchmark_against_midpoint: bool = True
    track_queue_position: bool = True
    measure_market_impact: bool = True
    
    # Advanced features
    enable_smart_routing: bool = True
    enable_dark_pool_access: bool = True
    enable_iceberg_orders: bool = True
    randomize_order_sizes: bool = True


@dataclass
class OrderRequest:
    """Order execution request"""
    # Basic order details
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    order_type: OrderType = OrderType.LIMIT
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution style
    execution_quality: ExecutionQuality = ExecutionQuality.NORMAL
    urgency_level: int = 5  # 1-10 scale
    
    # Advanced parameters
    iceberg_visible_qty: Optional[float] = None
    reserve_qty: Optional[float] = None
    min_fill_size: Optional[float] = None
    
    # Routing preferences
    preferred_venues: List[str] = field(default_factory=list)
    avoid_venues: List[str] = field(default_factory=list)
    
    # Parent information
    parent_request_id: Optional[str] = None
    slice_number: Optional[int] = None
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Callbacks
    fill_callback: Optional[Callable] = None
    status_callback: Optional[Callable] = None


@dataclass
class Fill:
    """Order fill representation"""
    fill_id: str
    order_id: str
    symbol: str
    side: str
    
    # Fill details
    fill_quantity: float
    fill_price: float
    fill_time: datetime
    
    # Venue information
    venue: str
    venue_order_id: Optional[str] = None
    
    # Execution details
    liquidity_flag: str = "Unknown"  # Added, Removed, etc.
    commission: float = 0.0
    fees: float = 0.0
    
    # Quality metrics
    price_improvement: float = 0.0
    effective_spread: float = 0.0
    market_impact: float = 0.0
    
    # Market data at fill
    bid_at_fill: Optional[float] = None
    ask_at_fill: Optional[float] = None
    midpoint_at_fill: Optional[float] = None


@dataclass
class OrderState:
    """Complete order state"""
    request: OrderRequest
    status: OrderStatus = OrderStatus.PENDING_NEW
    
    # Execution progress
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    avg_fill_price: float = 0.0
    
    # Fills
    fills: List[Fill] = field(default_factory=list)
    
    # Venue routing
    active_child_orders: Dict[str, Dict] = field(default_factory=dict)
    venue_allocations: Dict[str, float] = field(default_factory=dict)
    
    # Performance tracking
    creation_time: datetime = field(default_factory=datetime.now)
    first_fill_time: Optional[datetime] = None
    last_fill_time: Optional[datetime] = None
    
    # Market context
    arrival_midpoint: Optional[float] = None
    departure_midpoint: Optional[float] = None
    
    # Quality metrics
    total_slippage: float = 0.0
    total_market_impact: float = 0.0
    price_improvement: float = 0.0
    effective_spread: float = 0.0
    
    # Errors and messages
    error_messages: List[str] = field(default_factory=list)
    status_messages: List[str] = field(default_factory=list)


class MarketMicrostructureAnalyzer:
    """Analyzes market microstructure for optimal execution"""
    
    def __init__(self, config: OrderExecutionConfig):
        self.config = config
        self._market_data_cache = {}
        self._lock = threading.Lock()
    
    def analyze_order_book(self, symbol: str) -> Dict[str, Any]:
        """Analyze order book structure"""
        
        # Mock order book analysis
        book_analysis = {
            'bid_ask_spread': np.random.uniform(0.01, 0.05),
            'book_depth': {
                'bid_levels': 5,
                'ask_levels': 5,
                'total_bid_size': np.random.uniform(10000, 100000),
                'total_ask_size': np.random.uniform(10000, 100000)
            },
            'liquidity_score': np.random.uniform(0.6, 0.95),
            'imbalance_ratio': np.random.uniform(-0.3, 0.3),
            'price_pressure': np.random.uniform(-0.1, 0.1),
            'volatility_regime': np.random.choice(['low', 'medium', 'high']),
            'tick_size': 0.01,
            'optimal_order_size': np.random.uniform(1000, 10000),
            'recommended_aggression': np.random.uniform(0.3, 0.8)
        }
        
        return book_analysis
    
    def calculate_optimal_price(
        self,
        symbol: str,
        side: str,
        quantity: float,
        quality: ExecutionQuality
    ) -> Dict[str, float]:
        """Calculate optimal limit price"""
        
        book_analysis = self.analyze_order_book(symbol)
        
        # Mock current prices
        mid_price = 100.0
        spread = book_analysis['bid_ask_spread']
        
        bid = mid_price - spread / 2
        ask = mid_price + spread / 2
        
        # Calculate optimal price based on execution quality
        if quality == ExecutionQuality.AGGRESSIVE:
            # Cross the spread for immediate execution
            optimal_price = ask if side == 'BUY' else bid
            aggression_level = 1.0
            
        elif quality == ExecutionQuality.PASSIVE:
            # Post at best bid/offer
            optimal_price = bid if side == 'BUY' else ask
            aggression_level = 0.0
            
        elif quality == ExecutionQuality.PATIENT:
            # Post inside the spread
            tick_size = book_analysis['tick_size']
            if side == 'BUY':
                optimal_price = bid - tick_size
            else:
                optimal_price = ask + tick_size
            aggression_level = -0.2
            
        else:  # NORMAL
            # Join the inside market or slightly improve
            tick_size = book_analysis['tick_size']
            if side == 'BUY':
                optimal_price = bid + tick_size * np.random.uniform(0, 0.5)
            else:
                optimal_price = ask - tick_size * np.random.uniform(0, 0.5)
            aggression_level = 0.3
        
        return {
            'optimal_price': optimal_price,
            'aggression_level': aggression_level,
            'confidence': np.random.uniform(0.7, 0.95),
            'expected_fill_time': self._estimate_fill_time(quantity, aggression_level),
            'market_impact_estimate': self._estimate_market_impact(quantity, book_analysis)
        }
    
    def _estimate_fill_time(self, quantity: float, aggression_level: float) -> float:
        """Estimate expected fill time in seconds"""
        
        base_time = 60  # 1 minute base
        
        # More aggressive = faster fill
        aggression_factor = 1.0 - aggression_level
        
        # Larger quantity = longer fill time
        size_factor = np.log(quantity / 1000) if quantity > 1000 else 1.0
        
        return base_time * aggression_factor * size_factor
    
    def _estimate_market_impact(self, quantity: float, book_analysis: Dict) -> float:
        """Estimate market impact in basis points"""
        
        liquidity_score = book_analysis['liquidity_score']
        total_size = book_analysis['book_depth']['total_bid_size']
        
        # Impact increases with size and decreases with liquidity
        size_ratio = quantity / total_size
        impact_bps = size_ratio * (1.0 - liquidity_score) * 100  # Convert to bps
        
        return max(0.1, min(impact_bps, 50.0))  # Cap between 0.1 and 50 bps


class VenueSelector:
    """Smart venue selection for optimal execution"""
    
    def __init__(self, config: OrderExecutionConfig):
        self.config = config
        self._venue_performance = defaultdict(dict)
        self._venue_connectivity = {}
    
    def select_execution_venues(
        self,
        symbol: str,
        side: str,
        quantity: float,
        quality: ExecutionQuality
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Select optimal venues for execution"""
        
        # Available venues (mock)
        available_venues = [
            'NYSE', 'NASDAQ', 'ARCA', 'BATS',
            'DARK_POOL_1', 'DARK_POOL_2', 'DARK_POOL_3',
            'IEX', 'EDGX', 'EDGA'
        ]
        
        venue_scores = []
        
        for venue in available_venues:
            score = self._calculate_venue_score(venue, symbol, side, quantity, quality)
            venue_info = self._get_venue_info(venue, symbol)
            
            venue_scores.append((venue, score, venue_info))
        
        # Sort by score (higher is better)
        venue_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select top venues and allocate quantity
        selected_venues = []
        total_allocation = 0.0
        
        for venue, score, info in venue_scores[:5]:  # Top 5 venues
            if total_allocation >= 1.0:
                break
            
            # Allocate based on score and venue constraints
            max_allocation = min(0.5, 1.0 - total_allocation)  # Max 50% per venue
            allocation = min(score / sum(s[1] for s in venue_scores[:5]), max_allocation)
            
            if allocation > 0.05:  # Minimum 5% allocation
                selected_venues.append((venue, allocation, info))
                total_allocation += allocation
        
        # Normalize allocations to sum to 1.0
        if total_allocation > 0:
            selected_venues = [
                (venue, alloc / total_allocation, info)
                for venue, alloc, info in selected_venues
            ]
        
        return selected_venues
    
    def _calculate_venue_score(
        self,
        venue: str,
        symbol: str,
        side: str,
        quantity: float,
        quality: ExecutionQuality
    ) -> float:
        """Calculate venue suitability score"""
        
        # Base score
        score = 0.5
        
        # Venue type scoring
        if 'DARK' in venue:
            # Dark pools good for large orders and passive execution
            if quantity > 10000 and quality in [ExecutionQuality.PASSIVE, ExecutionQuality.PATIENT]:
                score += 0.3
            else:
                score += 0.1
        else:
            # Lit venues good for aggressive execution
            if quality in [ExecutionQuality.AGGRESSIVE, ExecutionQuality.NORMAL]:
                score += 0.3
            else:
                score += 0.1
        
        # Historical performance (mock)
        historical_perf = self._venue_performance.get(venue, {})
        fill_rate = historical_perf.get('fill_rate', 0.8)
        avg_slippage = historical_perf.get('avg_slippage', 0.001)
        
        score += fill_rate * 0.2  # 20% weight to fill rate
        score -= avg_slippage * 100  # Penalize high slippage
        
        # Connectivity and latency
        venue_info = self._get_venue_info(venue, symbol)
        latency_score = 1.0 - (venue_info.get('latency', 5) / 20)  # Normalize latency
        score += latency_score * 0.1
        
        # Capacity constraints
        current_capacity = venue_info.get('current_capacity', 0.8)
        score *= current_capacity
        
        return max(0.0, min(score, 1.0))
    
    def _get_venue_info(self, venue: str, symbol: str) -> Dict[str, Any]:
        """Get venue information"""
        
        # Mock venue information
        return {
            'latency': np.random.uniform(1, 10),  # milliseconds
            'fill_rate': np.random.uniform(0.85, 0.98),
            'avg_slippage': np.random.uniform(0.0005, 0.003),
            'current_capacity': np.random.uniform(0.7, 0.95),
            'fees': np.random.uniform(0.0001, 0.0005),
            'min_size': 100,
            'max_size': 1000000,
            'supports_hidden': 'DARK' in venue or venue in ['IEX'],
            'supports_iceberg': venue not in ['DARK_POOL_1', 'DARK_POOL_2'],
            'session_status': 'OPEN'
        }


class OrderLifecycleManager:
    """Manages complete order lifecycle"""
    
    def __init__(self, config: OrderExecutionConfig):
        self.config = config
        self._order_states = {}
        self._lock = threading.Lock()
    
    def create_order_state(self, request: OrderRequest) -> OrderState:
        """Create new order state"""
        
        state = OrderState(request=request)
        state.remaining_quantity = request.quantity
        state.arrival_midpoint = self._get_current_midpoint(request.symbol)
        
        with self._lock:
            self._order_states[request.order_id] = state
        
        return state
    
    def update_order_status(self, order_id: str, new_status: OrderStatus) -> None:
        """Update order status"""
        
        with self._lock:
            if order_id in self._order_states:
                old_status = self._order_states[order_id].status
                self._order_states[order_id].status = new_status
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                message = f"{timestamp}: Status changed from {old_status.value} to {new_status.value}"
                self._order_states[order_id].status_messages.append(message)
    
    def process_fill(self, order_id: str, fill: Fill) -> None:
        """Process order fill"""
        
        with self._lock:
            if order_id not in self._order_states:
                logger.warning(f"Received fill for unknown order {order_id}")
                return
            
            state = self._order_states[order_id]
            
            # Add fill to order
            state.fills.append(fill)
            
            # Update quantities and pricing
            state.filled_quantity += fill.fill_quantity
            state.remaining_quantity = state.request.quantity - state.filled_quantity
            
            # Update average fill price
            total_value = sum(f.fill_quantity * f.fill_price for f in state.fills)
            state.avg_fill_price = total_value / state.filled_quantity if state.filled_quantity > 0 else 0
            
            # Update timing
            if state.first_fill_time is None:
                state.first_fill_time = fill.fill_time
            state.last_fill_time = fill.fill_time
            
            # Update status based on fill
            if state.remaining_quantity <= 0.01:  # Essentially filled
                state.status = OrderStatus.FILLED
            else:
                state.status = OrderStatus.PARTIALLY_FILLED
            
            # Calculate performance metrics
            self._update_performance_metrics(state, fill)
            
            # Trigger callback if provided
            if state.request.fill_callback:
                try:
                    state.request.fill_callback(fill, state)
                except Exception as e:
                    logger.error(f"Error in fill callback: {e}")
    
    def _update_performance_metrics(self, state: OrderState, fill: Fill) -> None:
        """Update order performance metrics"""
        
        # Market impact (simplified)
        if fill.midpoint_at_fill:
            if state.request.side == 'BUY':
                impact = (fill.fill_price - fill.midpoint_at_fill) / fill.midpoint_at_fill
            else:
                impact = (fill.midpoint_at_fill - fill.fill_price) / fill.midpoint_at_fill
            
            state.total_market_impact += impact * (fill.fill_quantity / state.request.quantity)
        
        # Slippage against arrival price
        if state.arrival_midpoint:
            if state.request.side == 'BUY':
                slippage = (fill.fill_price - state.arrival_midpoint) / state.arrival_midpoint
            else:
                slippage = (state.arrival_midpoint - fill.fill_price) / state.arrival_midpoint
            
            state.total_slippage += slippage * (fill.fill_quantity / state.request.quantity)
        
        # Price improvement
        state.price_improvement += fill.price_improvement * (fill.fill_quantity / state.request.quantity)
        
        # Effective spread
        state.effective_spread += fill.effective_spread * (fill.fill_quantity / state.request.quantity)
    
    def _get_current_midpoint(self, symbol: str) -> float:
        """Get current midpoint price"""
        # Mock implementation
        return 100.0 + np.random.normal(0, 1)
    
    def get_order_state(self, order_id: str) -> Optional[OrderState]:
        """Get order state"""
        
        with self._lock:
            return self._order_states.get(order_id)
    
    def get_active_orders(self) -> List[OrderState]:
        """Get all active orders"""
        
        with self._lock:
            return [
                state for state in self._order_states.values()
                if state.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
            ]


class OrderExecutor:
    """
    Advanced Order Executor
    
    Sophisticated order execution with market microstructure analysis,
    smart venue selection, and optimal timing strategies.
    """
    
    def __init__(self, config: Optional[OrderExecutionConfig] = None):
        """Initialize order executor"""
        self.config = config or OrderExecutionConfig()
        
        # Core components
        self.microstructure_analyzer = MarketMicrostructureAnalyzer(self.config)
        self.venue_selector = VenueSelector(self.config)
        self.lifecycle_manager = OrderLifecycleManager(self.config)
        
        # Execution tracking
        self._execution_queue = asyncio.Queue()
        self._performance_metrics = defaultdict(list)
        
        # Threading
        self._lock = threading.Lock()
        self._running = False
        
        logger.info("Order Executor initialized")
    
    async def execute_order(self, request: OrderRequest) -> str:
        """Execute order with optimal strategy"""
        
        try:
            # Create order state
            state = self.lifecycle_manager.create_order_state(request)
            
            # Analyze market microstructure
            book_analysis = self.microstructure_analyzer.analyze_order_book(request.symbol)
            pricing_analysis = self.microstructure_analyzer.calculate_optimal_price(
                request.symbol,
                request.side,
                request.quantity,
                request.execution_quality
            )
            
            # Select execution venues
            venues = self.venue_selector.select_execution_venues(
                request.symbol,
                request.side,
                request.quantity,
                request.execution_quality
            )
            
            # Update order state with analysis
            state.venue_allocations = {venue: allocation for venue, allocation, _ in venues}
            
            # Set optimal limit price if not specified
            if request.limit_price is None and request.order_type == OrderType.LIMIT:
                request.limit_price = pricing_analysis['optimal_price']
            
            # Execute across selected venues
            await self._execute_across_venues(state, venues, book_analysis)
            
            logger.info(f"Order execution initiated for {request.order_id}")
            return request.order_id
            
        except Exception as e:
            logger.error(f"Error executing order {request.order_id}: {e}")
            raise
    
    async def _execute_across_venues(
        self,
        state: OrderState,
        venues: List[Tuple[str, float, Dict[str, Any]]],
        book_analysis: Dict[str, Any]
    ) -> None:
        """Execute order across multiple venues"""
        
        request = state.request
        
        for venue, allocation, venue_info in venues:
            if allocation <= 0:
                continue
            
            venue_quantity = request.quantity * allocation
            
            # Create venue-specific order
            venue_order = await self._create_venue_order(
                request, venue, venue_quantity, venue_info
            )
            
            # Track child order
            state.active_child_orders[venue] = venue_order
            
            # Submit to venue (simulated)
            await self._submit_to_venue(venue_order, venue, venue_info)
    
    async def _create_venue_order(
        self,
        parent_request: OrderRequest,
        venue: str,
        quantity: float,
        venue_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create venue-specific order"""
        
        venue_order = {
            'venue_order_id': f"{parent_request.order_id}_{venue}_{int(time.time())}",
            'parent_order_id': parent_request.order_id,
            'venue': venue,
            'symbol': parent_request.symbol,
            'side': parent_request.side,
            'quantity': quantity,
            'order_type': parent_request.order_type,
            'limit_price': parent_request.limit_price,
            'time_in_force': parent_request.time_in_force,
            'created_at': datetime.now()
        }
        
        # Venue-specific modifications
        if venue_info.get('supports_hidden') and parent_request.execution_quality == ExecutionQuality.PASSIVE:
            venue_order['display_quantity'] = 0  # Hidden order
        elif venue_info.get('supports_iceberg') and parent_request.iceberg_visible_qty:
            venue_order['display_quantity'] = parent_request.iceberg_visible_qty
        
        return venue_order
    
    async def _submit_to_venue(
        self,
        venue_order: Dict[str, Any],
        venue: str,
        venue_info: Dict[str, Any]
    ) -> None:
        """Submit order to venue (simulated)"""
        
        # Simulate venue submission delay
        latency = venue_info.get('latency', 5) / 1000  # Convert to seconds
        await asyncio.sleep(latency)
        
        # Update order status
        parent_order_id = venue_order['parent_order_id']
        self.lifecycle_manager.update_order_status(parent_order_id, OrderStatus.NEW)
        
        # Simulate fills
        await self._simulate_venue_execution(venue_order, venue_info)
    
    async def _simulate_venue_execution(
        self,
        venue_order: Dict[str, Any],
        venue_info: Dict[str, Any]
    ) -> None:
        """Simulate venue execution (replace with real venue integration)"""
        
        fill_rate = venue_info.get('fill_rate', 0.9)
        avg_slippage = venue_info.get('avg_slippage', 0.001)
        
        # Simulate partial fills over time
        remaining_qty = venue_order['quantity']
        fill_count = 0
        
        while remaining_qty > 0 and fill_count < 5:  # Max 5 fills per order
            await asyncio.sleep(np.random.uniform(1, 10))  # Random fill timing
            
            # Determine fill size
            fill_qty = min(remaining_qty, remaining_qty * np.random.uniform(0.2, 0.8))
            
            if np.random.random() < fill_rate:
                # Create fill
                fill = Fill(
                    fill_id=f"fill_{venue_order['venue_order_id']}_{fill_count}",
                    order_id=venue_order['parent_order_id'],
                    symbol=venue_order['symbol'],
                    side=venue_order['side'],
                    fill_quantity=fill_qty,
                    fill_price=self._calculate_fill_price(venue_order, avg_slippage),
                    fill_time=datetime.now(),
                    venue=venue_order['venue'],
                    venue_order_id=venue_order['venue_order_id'],
                    liquidity_flag="Added" if np.random.random() > 0.5 else "Removed"
                )
                
                # Add market data context
                fill.midpoint_at_fill = 100.0  # Mock midpoint
                fill.bid_at_fill = 99.99
                fill.ask_at_fill = 100.01
                
                # Calculate quality metrics
                fill.effective_spread = abs(fill.fill_price - fill.midpoint_at_fill) * 2
                fill.price_improvement = max(0, np.random.uniform(-0.001, 0.002))
                fill.market_impact = abs(np.random.normal(0, 0.001))
                
                # Process fill
                self.lifecycle_manager.process_fill(venue_order['parent_order_id'], fill)
                
                remaining_qty -= fill_qty
                fill_count += 1
            else:
                break  # No more fills
    
    def _calculate_fill_price(self, venue_order: Dict[str, Any], avg_slippage: float) -> float:
        """Calculate realistic fill price"""
        
        base_price = venue_order.get('limit_price', 100.0)
        
        # Add random slippage
        slippage = np.random.normal(0, avg_slippage)
        
        if venue_order['side'] == 'BUY':
            fill_price = base_price + abs(slippage)
        else:
            fill_price = base_price - abs(slippage)
        
        return fill_price
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order execution status"""
        
        state = self.lifecycle_manager.get_order_state(order_id)
        
        if not state:
            return None
        
        return {
            'order_id': order_id,
            'symbol': state.request.symbol,
            'side': state.request.side,
            'status': state.status.value,
            'total_quantity': state.request.quantity,
            'filled_quantity': state.filled_quantity,
            'remaining_quantity': state.remaining_quantity,
            'avg_fill_price': state.avg_fill_price,
            'fill_rate': state.filled_quantity / state.request.quantity if state.request.quantity > 0 else 0,
            'number_of_fills': len(state.fills),
            'execution_time': (datetime.now() - state.creation_time).total_seconds(),
            'total_slippage': state.total_slippage,
            'market_impact': state.total_market_impact,
            'price_improvement': state.price_improvement,
            'venue_breakdown': state.venue_allocations,
            'last_status_message': state.status_messages[-1] if state.status_messages else None
        }
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        
        try:
            state = self.lifecycle_manager.get_order_state(order_id)
            
            if not state:
                return False
            
            if state.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                return False
            
            # Update status
            self.lifecycle_manager.update_order_status(order_id, OrderStatus.PENDING_CANCEL)
            
            # Simulate cancellation delay
            asyncio.create_task(self._process_cancellation(order_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def _process_cancellation(self, order_id: str) -> None:
        """Process order cancellation"""
        
        await asyncio.sleep(0.5)  # Simulate cancellation latency
        self.lifecycle_manager.update_order_status(order_id, OrderStatus.CANCELLED)
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution performance metrics"""
        
        active_orders = self.lifecycle_manager.get_active_orders()
        all_states = list(self.lifecycle_manager._order_states.values())
        
        if not all_states:
            return {'total_orders': 0}
        
        # Calculate aggregate metrics
        total_orders = len(all_states)
        filled_orders = len([s for s in all_states if s.status == OrderStatus.FILLED])
        
        avg_fill_rate = np.mean([s.filled_quantity / s.request.quantity for s in all_states if s.request.quantity > 0])
        avg_slippage = np.mean([s.total_slippage for s in all_states if s.total_slippage is not None])
        avg_market_impact = np.mean([s.total_market_impact for s in all_states if s.total_market_impact is not None])
        
        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'completion_rate': filled_orders / total_orders if total_orders > 0 else 0,
            'active_orders': len(active_orders),
            'avg_fill_rate': avg_fill_rate,
            'avg_slippage_bps': avg_slippage * 10000,  # Convert to bps
            'avg_market_impact_bps': avg_market_impact * 10000,
            'total_fills': sum(len(s.fills) for s in all_states),
            'executor_uptime': datetime.now().isoformat()
        }
    
    def start(self) -> None:
        """Start order executor"""
        self._running = True
        logger.info("Order Executor started")
    
    def stop(self) -> None:
        """Stop order executor"""
        self._running = False
        logger.info("Order Executor stopped")