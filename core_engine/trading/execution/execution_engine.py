"""
Execution Engine - Core Execution Framework
Advanced trade execution engine with institutional-grade algorithms and controls
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ExecutionAlgorithm(Enum):
    """Execution algorithm types"""
    MARKET = "market"
    LIMIT = "limit"
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    POV = "pov"    # Participation of Volume
    IS = "implementation_shortfall"
    ICEBERG = "iceberg"
    SNIPER = "sniper"
    GUERRILLA = "guerrilla"
    ADAPTIVE = "adaptive"


class ExecutionUrgency(Enum):
    """Execution urgency levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ExecutionStyle(Enum):
    """Execution style preferences"""
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    NEUTRAL = "neutral"
    OPPORTUNISTIC = "opportunistic"


class ExecutionStatus(Enum):
    """Execution status"""
    PENDING = "pending"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class ExecutionConfig:
    """Execution engine configuration"""
    # Algorithm settings
    default_algorithm: ExecutionAlgorithm = ExecutionAlgorithm.TWAP
    enable_adaptive_algorithms: bool = True
    
    # Timing controls
    max_execution_time: int = 3600  # 1 hour in seconds
    slice_interval: int = 30  # 30 seconds between slices
    min_slice_size: float = 0.01  # 1% of order size
    max_slice_size: float = 0.25  # 25% of order size
    
    # Market impact controls
    max_participation_rate: float = 0.20  # 20% of volume
    impact_threshold: float = 0.005  # 0.5% price impact limit
    
    # Risk controls
    enable_pre_trade_risk: bool = True
    enable_real_time_risk: bool = True
    max_order_value: float = 10_000_000  # $10M
    max_position_concentration: float = 0.05  # 5%
    
    # Liquidity settings
    min_adv_participation: float = 0.01  # 1% of ADV
    max_adv_participation: float = 0.10  # 10% of ADV
    liquidity_buffer: float = 0.20  # 20% liquidity buffer
    
    # Slippage controls
    max_acceptable_slippage: float = 0.002  # 20 bps
    slippage_tolerance: float = 0.001  # 10 bps
    
    # Dark pool settings
    enable_dark_pools: bool = True
    dark_pool_preference: float = 0.30  # 30% to dark pools
    
    # Smart order routing
    enable_smart_routing: bool = True
    venue_timeout: int = 5  # 5 seconds venue timeout
    
    # Performance tracking
    track_execution_quality: bool = True
    benchmark_against_arrival: bool = True
    
    # Emergency controls
    circuit_breaker_threshold: float = 0.05  # 5% adverse move
    emergency_cancel_enabled: bool = True


@dataclass
class ExecutionRequest:
    """Execution request specification"""
    # Basic order information
    request_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    order_type: str = "MARKET"
    
    # Execution parameters
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.TWAP
    urgency: ExecutionUrgency = ExecutionUrgency.NORMAL
    style: ExecutionStyle = ExecutionStyle.NEUTRAL
    
    # Timing constraints
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_duration: Optional[int] = None  # seconds
    
    # Price constraints
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    benchmark_price: Optional[float] = None
    
    # Volume constraints
    participation_rate: Optional[float] = None  # % of volume
    min_fill_size: Optional[float] = None
    max_slice_size: Optional[float] = None
    
    # Routing preferences
    preferred_venues: List[str] = field(default_factory=list)
    excluded_venues: List[str] = field(default_factory=list)
    dark_pool_preference: Optional[float] = None
    
    # Risk parameters
    max_market_impact: Optional[float] = None
    slippage_tolerance: Optional[float] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    client_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Advanced options
    iceberg_visible_qty: Optional[float] = None
    randomize_timing: bool = False
    liquidity_seeking: bool = True
    
    # Callbacks
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None


@dataclass
class ExecutionSlice:
    """Individual execution slice"""
    slice_id: str
    parent_request_id: str
    
    # Slice details
    symbol: str
    side: str
    quantity: float
    slice_number: int
    total_slices: int
    
    # Timing
    scheduled_time: datetime
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    
    # Pricing
    limit_price: Optional[float] = None
    avg_fill_price: Optional[float] = None
    
    # Status
    status: ExecutionStatus = ExecutionStatus.PENDING
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    
    # Venue information
    target_venue: Optional[str] = None
    actual_venue: Optional[str] = None
    
    # Performance metrics
    slippage: Optional[float] = None
    market_impact: Optional[float] = None
    execution_shortfall: Optional[float] = None
    
    # Risk metrics
    risk_score: Optional[float] = None
    compliance_status: str = "PENDING"


@dataclass
class ExecutionResult:
    """Execution result summary"""
    request_id: str
    symbol: str
    
    # Execution summary
    total_quantity: float
    filled_quantity: float
    remaining_quantity: float
    fill_rate: float
    
    # Pricing metrics
    avg_fill_price: float
    benchmark_price: float
    arrival_price: float
    
    # Performance metrics
    total_slippage: float
    market_impact: float
    implementation_shortfall: float
    execution_cost: float
    
    # Timing metrics
    start_time: datetime
    end_time: datetime
    execution_duration: timedelta
    
    # Quality metrics
    participation_rate: float
    venue_breakdown: Dict[str, float]
    dark_pool_rate: float
    
    # Risk metrics
    max_adverse_move: float
    risk_adjusted_cost: float
    
    # Status
    final_status: ExecutionStatus
    completion_reason: str
    
    # Detailed breakdown
    slice_results: List[ExecutionSlice] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)


@dataclass
class ExecutionMetrics:
    """Execution performance metrics"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    total_volume: float = 0.0
    avg_slippage: float = 0.0
    completion_rate: float = 0.0


class MarketDataProvider:
    """Market data provider for execution"""
    
    def __init__(self):
        self._market_data = {}
        self._lock = threading.Lock()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        with self._lock:
            data = self._market_data.get(symbol, {})
            return data.get('price')
    
    def get_bid_ask(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Get current bid/ask"""
        with self._lock:
            data = self._market_data.get(symbol, {})
            return data.get('bid'), data.get('ask')
    
    def get_volume_profile(self, symbol: str) -> Dict[str, float]:
        """Get volume profile"""
        # Mock implementation
        return {
            'current_volume': 1000000,
            'avg_daily_volume': 5000000,
            'volume_rate': 0.02,  # 2% of ADV per minute
            'liquidity_score': 0.85
        }
    
    def update_market_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update market data"""
        with self._lock:
            self._market_data[symbol] = data


class VenueRouter:
    """Smart order routing engine"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._venue_stats = defaultdict(dict)
        self._venue_connectivity = {}
    
    def select_venues(
        self,
        symbol: str,
        quantity: float,
        algorithm: ExecutionAlgorithm,
        preferences: Dict[str, Any]
    ) -> List[Tuple[str, float]]:
        """Select optimal venues for execution"""
        
        # Mock venue selection logic
        venues = []
        
        if algorithm == ExecutionAlgorithm.MARKET:
            venues = [("PRIMARY_EXCHANGE", 1.0)]
        elif algorithm == ExecutionAlgorithm.VWAP:
            venues = [
                ("PRIMARY_EXCHANGE", 0.60),
                ("DARK_POOL_1", 0.25),
                ("ECN_1", 0.15)
            ]
        else:
            venues = [
                ("PRIMARY_EXCHANGE", 0.50),
                ("DARK_POOL_1", 0.30),
                ("ECN_1", 0.20)
            ]
        
        return venues
    
    def get_venue_quality(self, venue: str, symbol: str) -> Dict[str, float]:
        """Get venue quality metrics"""
        
        # Mock venue quality data
        return {
            'fill_rate': 0.95,
            'avg_latency': 2.5,  # milliseconds
            'slippage': 0.0015,  # 1.5 bps
            'market_impact': 0.001,  # 1 bp
            'liquidity_score': 0.85,
            'cost_score': 0.90
        }


class SlicingEngine:
    """Order slicing engine"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self.market_data = MarketDataProvider()
    
    def generate_slices(
        self,
        request: ExecutionRequest,
        market_conditions: Dict[str, Any]
    ) -> List[ExecutionSlice]:
        """Generate execution slices"""
        
        slices = []
        
        # Determine slicing parameters
        total_quantity = request.quantity
        duration = self._calculate_duration(request)
        slice_count = self._calculate_slice_count(request, duration)
        
        # Generate time schedule
        start_time = request.start_time or datetime.now()
        slice_interval = duration / slice_count
        
        for i in range(slice_count):
            # Calculate slice size
            if request.algorithm == ExecutionAlgorithm.TWAP:
                slice_size = total_quantity / slice_count
            elif request.algorithm == ExecutionAlgorithm.VWAP:
                slice_size = self._calculate_vwap_slice(i, slice_count, total_quantity, market_conditions)
            else:
                slice_size = self._calculate_adaptive_slice(i, slice_count, total_quantity, market_conditions)
            
            # Create slice
            slice_time = start_time + timedelta(seconds=i * slice_interval.total_seconds())
            
            execution_slice = ExecutionSlice(
                slice_id=f"{request.request_id}_slice_{i+1}",
                parent_request_id=request.request_id,
                symbol=request.symbol,
                side=request.side,
                quantity=slice_size,
                slice_number=i + 1,
                total_slices=slice_count,
                scheduled_time=slice_time,
                remaining_quantity=slice_size
            )
            
            slices.append(execution_slice)
        
        return slices
    
    def _calculate_duration(self, request: ExecutionRequest) -> timedelta:
        """Calculate execution duration"""
        
        if request.max_duration:
            return timedelta(seconds=request.max_duration)
        elif request.end_time and request.start_time:
            return request.end_time - request.start_time
        else:
            # Default duration based on urgency
            if request.urgency == ExecutionUrgency.URGENT:
                return timedelta(minutes=15)
            elif request.urgency == ExecutionUrgency.HIGH:
                return timedelta(minutes=30)
            elif request.urgency == ExecutionUrgency.NORMAL:
                return timedelta(hours=1)
            else:  # LOW
                return timedelta(hours=4)
    
    def _calculate_slice_count(self, request: ExecutionRequest, duration: timedelta) -> int:
        """Calculate number of slices"""
        
        interval_seconds = self.config.slice_interval
        max_slices = int(duration.total_seconds() / interval_seconds)
        
        # Minimum and maximum slice constraints
        min_slices = 2
        max_reasonable_slices = 100
        
        return max(min_slices, min(max_slices, max_reasonable_slices))
    
    def _calculate_vwap_slice(
        self,
        slice_index: int,
        total_slices: int,
        total_quantity: float,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate VWAP-based slice size"""
        
        # Mock VWAP calculation
        volume_profile = market_conditions.get('volume_profile', [1.0] * total_slices)
        
        if slice_index < len(volume_profile):
            volume_weight = volume_profile[slice_index]
        else:
            volume_weight = 1.0 / total_slices
        
        total_weight = sum(volume_profile[:total_slices])
        slice_size = total_quantity * (volume_weight / total_weight)
        
        return slice_size
    
    def _calculate_adaptive_slice(
        self,
        slice_index: int,
        total_slices: int,
        total_quantity: float,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate adaptive slice size"""
        
        # Base size
        base_size = total_quantity / total_slices
        
        # Adjust based on market conditions
        volatility = market_conditions.get('volatility', 0.02)
        liquidity = market_conditions.get('liquidity_score', 0.8)
        
        # Higher volatility -> smaller slices
        volatility_adj = 1.0 - (volatility * 0.5)
        
        # Lower liquidity -> smaller slices
        liquidity_adj = liquidity
        
        adjusted_size = base_size * volatility_adj * liquidity_adj
        
        # Apply min/max constraints
        min_size = total_quantity * self.config.min_slice_size
        max_size = total_quantity * self.config.max_slice_size
        
        return max(min_size, min(adjusted_size, max_size))


class RiskMonitor:
    """Real-time execution risk monitor"""
    
    def __init__(self, config: ExecutionConfig):
        self.config = config
        self._risk_metrics = {}
        self._lock = threading.Lock()
    
    def check_pre_trade_risk(self, request: ExecutionRequest) -> Tuple[bool, List[str]]:
        """Pre-trade risk check"""
        
        issues = []
        
        # Order size check
        order_value = request.quantity * (request.limit_price or 100)  # Estimate
        if order_value > self.config.max_order_value:
            issues.append(f"Order value {order_value:,.0f} exceeds limit {self.config.max_order_value:,.0f}")
        
        # Concentration check (simplified)
        # In real implementation, would check against current positions
        
        # Market hours check
        now = datetime.now().time()
        if now.hour < 9 or now.hour >= 16:  # Outside market hours
            issues.append("Order submitted outside market hours")
        
        return len(issues) == 0, issues
    
    def monitor_execution_risk(
        self,
        slice: ExecutionSlice,
        market_data: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Real-time execution risk monitoring"""
        
        alerts = []
        
        # Price movement check
        current_price = market_data.get('current_price', 0)
        benchmark_price = market_data.get('benchmark_price', current_price)
        
        if current_price and benchmark_price:
            price_move = abs(current_price - benchmark_price) / benchmark_price
            if price_move > self.config.circuit_breaker_threshold:
                alerts.append(f"Circuit breaker triggered: {price_move:.2%} price move")
        
        # Slippage check
        if slice.avg_fill_price and benchmark_price:
            slippage = abs(slice.avg_fill_price - benchmark_price) / benchmark_price
            if slippage > self.config.max_acceptable_slippage:
                alerts.append(f"Excessive slippage: {slippage:.4f}")
        
        return len(alerts) == 0, alerts
    
    def update_risk_metrics(self, request_id: str, metrics: Dict[str, float]) -> None:
        """Update risk metrics"""
        
        with self._lock:
            self._risk_metrics[request_id] = metrics


class ExecutionEngine:
    """
    Advanced Execution Engine
    
    Institutional-grade trade execution with sophisticated algorithms,
    smart order routing, and comprehensive risk controls.
    """
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """Initialize execution engine"""
        self.config = config or ExecutionConfig()
        
        # Core components
        self.market_data = MarketDataProvider()
        self.venue_router = VenueRouter(self.config)
        self.slicing_engine = SlicingEngine(self.config)
        self.risk_monitor = RiskMonitor(self.config)
        
        # Execution state
        self._active_requests = {}
        self._execution_history = {}
        self._slice_queue = asyncio.PriorityQueue()
        
        # Performance tracking
        self._execution_metrics = defaultdict(list)
        
        # Threading and async
        self._lock = threading.Lock()
        self._executor = None
        self._running = False
        
        logger.info("Execution Engine initialized")
    
    async def submit_execution_request(self, request: ExecutionRequest) -> str:
        """Submit execution request"""
        
        try:
            # Pre-trade risk check
            if self.config.enable_pre_trade_risk:
                risk_ok, risk_issues = self.risk_monitor.check_pre_trade_risk(request)
                if not risk_ok:
                    raise ValueError(f"Pre-trade risk check failed: {', '.join(risk_issues)}")
            
            # Generate execution slices
            market_conditions = self._get_market_conditions(request.symbol)
            slices = self.slicing_engine.generate_slices(request, market_conditions)
            
            # Store request
            with self._lock:
                self._active_requests[request.request_id] = {
                    'request': request,
                    'slices': slices,
                    'status': ExecutionStatus.PENDING,
                    'created_at': datetime.now()
                }
            
            # Queue slices for execution
            for slice in slices:
                priority = self._calculate_slice_priority(slice, request)
                await self._slice_queue.put((priority, slice.scheduled_time, slice))
            
            logger.info(f"Submitted execution request {request.request_id} with {len(slices)} slices")
            return request.request_id
            
        except Exception as e:
            logger.error(f"Error submitting execution request: {e}")
            raise
    
    async def execute_slice(self, slice: ExecutionSlice) -> ExecutionSlice:
        """Execute individual slice"""
        
        try:
            slice.status = ExecutionStatus.WORKING
            slice.submitted_time = datetime.now()
            
            # Get current market data
            market_data = self._get_current_market_data(slice.symbol)
            
            # Real-time risk check
            if self.config.enable_real_time_risk:
                risk_ok, risk_alerts = self.risk_monitor.monitor_execution_risk(slice, market_data)
                if not risk_ok:
                    slice.status = ExecutionStatus.REJECTED
                    logger.warning(f"Slice {slice.slice_id} rejected: {', '.join(risk_alerts)}")
                    return slice
            
            # Select venue
            venues = self.venue_router.select_venues(
                slice.symbol,
                slice.quantity,
                ExecutionAlgorithm.TWAP,  # Simplified
                {}
            )
            
            if venues:
                slice.target_venue = venues[0][0]
                slice.actual_venue = venues[0][0]
            
            # Simulate execution (replace with real broker integration)
            execution_result = await self._simulate_execution(slice, market_data)
            
            # Update slice with results
            slice.filled_quantity = execution_result['filled_quantity']
            slice.remaining_quantity = slice.quantity - slice.filled_quantity
            slice.avg_fill_price = execution_result['avg_fill_price']
            slice.slippage = execution_result['slippage']
            slice.market_impact = execution_result['market_impact']
            slice.filled_time = datetime.now()
            
            # Update status
            if slice.filled_quantity >= slice.quantity * 0.99:  # 99% filled
                slice.status = ExecutionStatus.FILLED
            elif slice.filled_quantity > 0:
                slice.status = ExecutionStatus.PARTIALLY_FILLED
            else:
                slice.status = ExecutionStatus.REJECTED
            
            logger.debug(f"Executed slice {slice.slice_id}: {slice.filled_quantity}/{slice.quantity}")
            return slice
            
        except Exception as e:
            slice.status = ExecutionStatus.ERROR
            logger.error(f"Error executing slice {slice.slice_id}: {e}")
            return slice
    
    async def _simulate_execution(
        self,
        slice: ExecutionSlice,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate execution (replace with real broker integration)"""
        
        # Simulate execution delay
        await asyncio.sleep(0.1)
        
        # Mock execution results
        current_price = market_data.get('current_price', 100.0)
        bid_ask_spread = market_data.get('spread', 0.01)
        
        # Simulate partial fill based on market conditions
        fill_probability = 0.95  # 95% fill rate
        filled_quantity = slice.quantity * fill_probability
        
        # Calculate execution price with slippage
        if slice.side == 'BUY':
            execution_price = current_price + (bid_ask_spread / 2) + np.random.normal(0, 0.005)
        else:
            execution_price = current_price - (bid_ask_spread / 2) + np.random.normal(0, 0.005)
        
        # Calculate metrics
        slippage = (execution_price - current_price) / current_price
        market_impact = abs(slippage) * 0.5  # Simplified market impact
        
        return {
            'filled_quantity': filled_quantity,
            'avg_fill_price': execution_price,
            'slippage': slippage,
            'market_impact': market_impact
        }
    
    def _get_market_conditions(self, symbol: str) -> Dict[str, Any]:
        """Get current market conditions"""
        
        # Mock market conditions
        return {
            'volatility': np.random.uniform(0.01, 0.05),
            'liquidity_score': np.random.uniform(0.7, 0.95),
            'volume_profile': [np.random.uniform(0.8, 1.2) for _ in range(20)],
            'current_volume': np.random.uniform(500000, 2000000)
        }
    
    def _get_current_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get current market data"""
        
        # Mock market data
        base_price = 100.0
        return {
            'current_price': base_price + np.random.normal(0, 1),
            'benchmark_price': base_price,
            'bid': base_price - 0.005,
            'ask': base_price + 0.005,
            'spread': 0.01,
            'volume': np.random.uniform(10000, 100000)
        }
    
    def _calculate_slice_priority(self, slice: ExecutionSlice, request: ExecutionRequest) -> int:
        """Calculate slice priority for queue"""
        
        # Higher number = lower priority
        if request.urgency == ExecutionUrgency.URGENT:
            return 1
        elif request.urgency == ExecutionUrgency.HIGH:
            return 2
        elif request.urgency == ExecutionUrgency.NORMAL:
            return 3
        else:
            return 4
    
    def get_execution_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        
        with self._lock:
            request_data = self._active_requests.get(request_id)
            
            if not request_data:
                # Check history
                return self._execution_history.get(request_id)
            
            slices = request_data['slices']
            total_quantity = sum(s.quantity for s in slices)
            filled_quantity = sum(s.filled_quantity for s in slices)
            
            return {
                'request_id': request_id,
                'status': request_data['status'],
                'total_quantity': total_quantity,
                'filled_quantity': filled_quantity,
                'fill_rate': filled_quantity / total_quantity if total_quantity > 0 else 0,
                'slices_total': len(slices),
                'slices_completed': len([s for s in slices if s.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED]]),
                'avg_fill_price': np.mean([s.avg_fill_price for s in slices if s.avg_fill_price]),
                'total_slippage': sum(s.slippage or 0 for s in slices),
                'execution_time': (datetime.now() - request_data['created_at']).total_seconds()
            }
    
    def cancel_execution(self, request_id: str) -> bool:
        """Cancel execution request"""
        
        try:
            with self._lock:
                if request_id in self._active_requests:
                    self._active_requests[request_id]['status'] = ExecutionStatus.CANCELLED
                    
                    # Cancel pending slices
                    slices = self._active_requests[request_id]['slices']
                    for slice in slices:
                        if slice.status == ExecutionStatus.PENDING:
                            slice.status = ExecutionStatus.CANCELLED
                    
                    logger.info(f"Cancelled execution request {request_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling execution {request_id}: {e}")
            return False
    
    def get_execution_metrics(self) -> ExecutionMetrics:
        """Get execution performance metrics"""
        
        with self._lock:
            total_requests = len(self._active_requests) + len(self._execution_history)
            completed_requests = len([r for r in self._active_requests.values() 
                                   if r['status'] in [ExecutionStatus.FILLED, ExecutionStatus.CANCELLED]])
            
            # Calculate average metrics
            all_slices = []
            for request_data in self._active_requests.values():
                all_slices.extend(request_data['slices'])
            
            if all_slices:
                avg_slippage = np.mean([s.slippage for s in all_slices if s.slippage is not None])
                np.mean([s.market_impact for s in all_slices if s.market_impact is not None])
                np.mean([s.filled_quantity / s.quantity for s in all_slices if s.quantity > 0])
            else:
                avg_slippage = 0
        
        return ExecutionMetrics(
            total_executions=total_requests,
            successful_executions=completed_requests,
            failed_executions=total_requests - completed_requests,
            avg_slippage=avg_slippage,
            completion_rate=completed_requests / total_requests if total_requests > 0 else 0
        )
    
    def start(self) -> None:
        """Start execution engine"""
        self._running = True
        logger.info("Execution Engine started")
    
    def stop(self) -> None:
        """Stop execution engine"""
        self._running = False
        logger.info("Execution Engine stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()