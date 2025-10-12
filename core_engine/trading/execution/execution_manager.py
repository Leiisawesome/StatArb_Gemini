"""
Execution Engine - Execution Manager
Unified execution management orchestrating all execution components
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import time
from collections import defaultdict, deque
import warnings

# Import execution components
from .execution_engine import ExecutionEngine
from .order_executor import OrderExecutor, OrderRequest
from .trade_executor import TradeExecutor, TradeExecutionRequest
from .fill_processor import FillProcessor, TradeExecution
from .execution_validator import ExecutionValidator, ExecutionContext

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ExecutionPriority(Enum):
    """Execution priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class ExecutionMode(Enum):
    """Execution modes"""
    LIVE = "live"
    SIMULATION = "simulation"
    PAPER = "paper"
    BACKTEST = "backtest"


@dataclass
class ExecutionConfiguration:
    """Unified execution configuration"""
    # Core settings
    execution_mode: ExecutionMode = ExecutionMode.LIVE
    enable_pre_trade_validation: bool = True
    enable_real_time_validation: bool = True
    enable_post_trade_validation: bool = True
    
    # Risk controls
    max_order_size: float = 1_000_000
    max_notional_per_order: float = 100_000_000
    max_daily_volume: float = 10_000_000
    max_concentration: float = 0.1  # 10%
    
    # Performance settings
    default_urgency_level: int = 5  # 1-10 scale
    enable_smart_routing: bool = True
    enable_dark_pools: bool = True
    enable_iceberg_orders: bool = True
    
    # Timing controls
    default_execution_horizon: int = 3600  # 1 hour in seconds
    order_timeout: int = 1800  # 30 minutes
    fill_timeout: int = 600  # 10 minutes
    
    # Quality thresholds
    max_slippage_bps: float = 50.0  # 5 bps
    max_market_impact_bps: float = 25.0  # 2.5 bps
    min_fill_rate: float = 0.95  # 95%
    
    # Reporting
    real_time_reporting: bool = True
    generate_execution_reports: bool = True
    report_frequency_minutes: int = 15
    
    # Advanced features
    enable_adaptive_execution: bool = True
    enable_machine_learning: bool = False
    enable_cross_venue_optimization: bool = True


@dataclass
class UnifiedExecutionRequest:
    """Unified execution request handling all execution types"""
    request_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    
    # Execution strategy
    execution_type: str = "TWAP"  # TWAP, VWAP, POV, IS, etc.
    urgency: ExecutionPriority = ExecutionPriority.NORMAL
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Price constraints
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Advanced parameters
    participation_rate: Optional[float] = None
    risk_aversion: Optional[float] = None
    
    # Routing preferences
    preferred_venues: List[str] = field(default_factory=list)
    avoid_venues: List[str] = field(default_factory=list)
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    trader_id: Optional[str] = None
    
    # Callbacks
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    
    # Internal tracking
    created_at: datetime = field(default_factory=datetime.now)
    priority_score: float = 0.0


@dataclass
class ExecutionStatus:
    """Comprehensive execution status"""
    request_id: str
    symbol: str
    side: str
    
    # Progress
    total_quantity: float
    executed_quantity: float
    remaining_quantity: float
    fill_rate: float
    
    # Performance
    avg_execution_price: float
    total_slippage_bps: float
    market_impact_bps: float
    
    # Status
    overall_status: str
    active_orders: int
    completed_orders: int
    
    # Timing
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    actual_completion: Optional[datetime] = None
    
    # Quality metrics
    execution_quality_score: float = 0.0
    venue_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Validation results
    validation_warnings: int = 0
    validation_errors: int = 0
    
    # Last update
    last_updated: datetime = field(default_factory=datetime.now)


class ExecutionQueue:
    """Priority-based execution queue"""
    
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
    
    def add_request(self, request: UnifiedExecutionRequest) -> None:
        """Add execution request to queue"""
        
        # Calculate priority score
        priority_scores = {
            ExecutionPriority.CRITICAL: 100,
            ExecutionPriority.URGENT: 80,
            ExecutionPriority.HIGH: 60,
            ExecutionPriority.NORMAL: 40,
            ExecutionPriority.LOW: 20
        }
        
        base_score = priority_scores.get(request.urgency, 40)
        
        # Adjust for timing urgency
        if request.end_time:
            time_remaining = (request.end_time - datetime.now()).total_seconds()
            time_urgency = max(0, (3600 - time_remaining) / 3600)  # More urgent as time runs out
            base_score += time_urgency * 20
        
        # Adjust for order size (larger orders get higher priority)
        size_factor = min(10, np.log10(request.quantity / 1000))  # Log scale adjustment
        base_score += size_factor
        
        request.priority_score = base_score
        
        with self._lock:
            # Insert in priority order (higher score = higher priority)
            inserted = False
            for i, existing in enumerate(self._queue):
                if request.priority_score > existing.priority_score:
                    self._queue.insert(i, request)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(request)
    
    def get_next_request(self) -> Optional[UnifiedExecutionRequest]:
        """Get next request from queue"""
        
        with self._lock:
            if self._queue:
                return self._queue.pop(0)
            return None
    
    def peek_next_request(self) -> Optional[UnifiedExecutionRequest]:
        """Peek at next request without removing"""
        
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None
    
    def remove_request(self, request_id: str) -> bool:
        """Remove request from queue"""
        
        with self._lock:
            for i, request in enumerate(self._queue):
                if request.request_id == request_id:
                    del self._queue[i]
                    return True
            return False
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        
        with self._lock:
            return len(self._queue)
    
    def get_queue_summary(self) -> Dict[str, Any]:
        """Get queue summary"""
        
        with self._lock:
            if not self._queue:
                return {'size': 0, 'next_symbol': None, 'next_priority': None}
            
            priority_counts = defaultdict(int)
            symbol_counts = defaultdict(int)
            total_notional = 0
            
            for request in self._queue:
                priority_counts[request.urgency.value] += 1
                symbol_counts[request.symbol] += 1
                if request.limit_price:
                    total_notional += request.quantity * request.limit_price
            
            return {
                'size': len(self._queue),
                'next_symbol': self._queue[0].symbol,
                'next_priority': self._queue[0].urgency.value,
                'priority_breakdown': dict(priority_counts),
                'symbol_breakdown': dict(symbol_counts),
                'total_notional': total_notional
            }


class ExecutionMonitor:
    """Real-time execution monitoring and alerting"""
    
    def __init__(self, config: ExecutionConfiguration):
        self.config = config
        self._monitoring_active = False
        self._alerts = deque(maxlen=1000)
        self._performance_metrics = defaultdict(list)
        self._lock = threading.Lock()
    
    def start_monitoring(self) -> None:
        """Start execution monitoring"""
        self._monitoring_active = True
        logger.info("Execution monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop execution monitoring"""
        self._monitoring_active = False
        logger.info("Execution monitoring stopped")
    
    def check_execution_health(self, status: ExecutionStatus) -> List[str]:
        """Check execution health and generate alerts"""
        
        alerts = []
        
        if not self._monitoring_active:
            return alerts
        
        # Check slippage
        if status.total_slippage_bps > self.config.max_slippage_bps:
            alerts.append(f"High slippage: {status.total_slippage_bps:.1f} bps exceeds threshold {self.config.max_slippage_bps:.1f} bps")
        
        # Check market impact
        if status.market_impact_bps > self.config.max_market_impact_bps:
            alerts.append(f"High market impact: {status.market_impact_bps:.1f} bps exceeds threshold {self.config.max_market_impact_bps:.1f} bps")
        
        # Check fill rate
        if status.fill_rate < self.config.min_fill_rate:
            alerts.append(f"Low fill rate: {status.fill_rate:.1%} below threshold {self.config.min_fill_rate:.1%}")
        
        # Check execution time
        if status.start_time:
            execution_time = (datetime.now() - status.start_time).total_seconds()
            if execution_time > self.config.order_timeout:
                alerts.append(f"Long execution time: {execution_time:.0f}s exceeds timeout {self.config.order_timeout}s")
        
        # Store alerts
        with self._lock:
            for alert in alerts:
                self._alerts.append({
                    'timestamp': datetime.now(),
                    'request_id': status.request_id,
                    'symbol': status.symbol,
                    'alert': alert,
                    'severity': 'warning'
                })
        
        return alerts
    
    def update_performance_metrics(self, status: ExecutionStatus) -> None:
        """Update performance metrics"""
        
        with self._lock:
            self._performance_metrics['slippage_bps'].append(status.total_slippage_bps)
            self._performance_metrics['market_impact_bps'].append(status.market_impact_bps)
            self._performance_metrics['fill_rate'].append(status.fill_rate)
            self._performance_metrics['execution_quality'].append(status.execution_quality_score)
    
    def get_recent_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            return [
                alert for alert in self._alerts
                if alert['timestamp'] >= cutoff
            ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        
        with self._lock:
            if not self._performance_metrics:
                return {}
            
            summary = {}
            for metric, values in self._performance_metrics.items():
                if values:
                    summary[metric] = {
                        'mean': np.mean(values),
                        'median': np.median(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values),
                        'count': len(values)
                    }
            
            return summary


class ExecutionReporter:
    """Execution reporting and analytics"""
    
    def __init__(self, config: ExecutionConfiguration):
        self.config = config
        self._execution_history = []
        self._reports_cache = {}
        self._lock = threading.Lock()
    
    def record_execution(self, request: UnifiedExecutionRequest, status: ExecutionStatus) -> None:
        """Record execution for reporting"""
        
        with self._lock:
            self._execution_history.append({
                'request_id': request.request_id,
                'symbol': request.symbol,
                'side': request.side,
                'total_quantity': request.quantity,
                'executed_quantity': status.executed_quantity,
                'avg_execution_price': status.avg_execution_price,
                'slippage_bps': status.total_slippage_bps,
                'market_impact_bps': status.market_impact_bps,
                'fill_rate': status.fill_rate,
                'execution_quality': status.execution_quality_score,
                'start_time': status.start_time,
                'completion_time': status.actual_completion,
                'strategy_id': request.strategy_id,
                'execution_type': request.execution_type,
                'urgency': request.urgency.value,
                'venue_breakdown': status.venue_breakdown
            })
            
            # Clear cache when new data is added
            self._reports_cache.clear()
    
    def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily execution report"""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Filter executions for the day
        daily_executions = [
            exec for exec in self._execution_history
            if start_date <= exec['start_time'] < end_date
        ]
        
        if not daily_executions:
            return {
                'date': date.strftime('%Y-%m-%d'),
                'total_executions': 0,
                'total_volume': 0,
                'total_notional': 0
            }
        
        # Calculate summary statistics
        total_executions = len(daily_executions)
        total_volume = sum(exec['executed_quantity'] for exec in daily_executions)
        avg_slippage = np.mean([exec['slippage_bps'] for exec in daily_executions])
        avg_market_impact = np.mean([exec['market_impact_bps'] for exec in daily_executions])
        avg_fill_rate = np.mean([exec['fill_rate'] for exec in daily_executions])
        avg_quality = np.mean([exec['execution_quality'] for exec in daily_executions])
        
        # Symbol breakdown
        symbol_stats = defaultdict(lambda: {'volume': 0, 'executions': 0, 'avg_slippage': 0})
        for exec in daily_executions:
            symbol = exec['symbol']
            symbol_stats[symbol]['volume'] += exec['executed_quantity']
            symbol_stats[symbol]['executions'] += 1
            symbol_stats[symbol]['avg_slippage'] += exec['slippage_bps']
        
        # Average slippage per symbol
        for stats in symbol_stats.values():
            stats['avg_slippage'] /= stats['executions']
        
        # Strategy breakdown
        strategy_stats = defaultdict(lambda: {'volume': 0, 'executions': 0, 'avg_quality': 0})
        for exec in daily_executions:
            strategy = exec['strategy_id'] or 'Unknown'
            strategy_stats[strategy]['volume'] += exec['executed_quantity']
            strategy_stats[strategy]['executions'] += 1
            strategy_stats[strategy]['avg_quality'] += exec['execution_quality']
        
        # Average quality per strategy
        for stats in strategy_stats.values():
            stats['avg_quality'] /= stats['executions']
        
        return {
            'date': date.strftime('%Y-%m-%d'),
            'total_executions': total_executions,
            'total_volume': total_volume,
            'avg_slippage_bps': avg_slippage,
            'avg_market_impact_bps': avg_market_impact,
            'avg_fill_rate': avg_fill_rate,
            'avg_execution_quality': avg_quality,
            'symbol_breakdown': dict(symbol_stats),
            'strategy_breakdown': dict(strategy_stats),
            'execution_type_breakdown': self._get_execution_type_breakdown(daily_executions),
            'hourly_volume': self._get_hourly_breakdown(daily_executions)
        }
    
    def _get_execution_type_breakdown(self, executions: List[Dict]) -> Dict[str, Dict]:
        """Get breakdown by execution type"""
        
        type_stats = defaultdict(lambda: {'count': 0, 'volume': 0, 'avg_slippage': 0})
        
        for exec in executions:
            exec_type = exec['execution_type']
            type_stats[exec_type]['count'] += 1
            type_stats[exec_type]['volume'] += exec['executed_quantity']
            type_stats[exec_type]['avg_slippage'] += exec['slippage_bps']
        
        # Calculate averages
        for stats in type_stats.values():
            stats['avg_slippage'] /= stats['count']
        
        return dict(type_stats)
    
    def _get_hourly_breakdown(self, executions: List[Dict]) -> Dict[str, float]:
        """Get hourly volume breakdown"""
        
        hourly_volume = defaultdict(float)
        
        for exec in executions:
            hour = exec['start_time'].hour
            hourly_volume[f"{hour:02d}:00"] += exec['executed_quantity']
        
        return dict(hourly_volume)
    
    def generate_performance_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Generate performance analytics over specified period"""
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_executions = [
            exec for exec in self._execution_history
            if exec['start_time'] >= cutoff_date
        ]
        
        if not recent_executions:
            return {'period_days': days, 'executions': 0}
        
        # Performance trends
        slippage_trend = self._calculate_trend([e['slippage_bps'] for e in recent_executions])
        impact_trend = self._calculate_trend([e['market_impact_bps'] for e in recent_executions])
        quality_trend = self._calculate_trend([e['execution_quality'] for e in recent_executions])
        
        # Best and worst performers
        best_execution = min(recent_executions, key=lambda x: x['slippage_bps'])
        worst_execution = max(recent_executions, key=lambda x: x['slippage_bps'])
        
        return {
            'period_days': days,
            'total_executions': len(recent_executions),
            'performance_trends': {
                'slippage_trend': slippage_trend,
                'market_impact_trend': impact_trend,
                'execution_quality_trend': quality_trend
            },
            'best_execution': {
                'request_id': best_execution['request_id'],
                'symbol': best_execution['symbol'],
                'slippage_bps': best_execution['slippage_bps']
            },
            'worst_execution': {
                'request_id': worst_execution['request_id'],
                'symbol': worst_execution['symbol'],
                'slippage_bps': worst_execution['slippage_bps']
            },
            'venue_performance': self._analyze_venue_performance(recent_executions)
        }
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, float]:
        """Calculate trend in values"""
        
        if len(values) < 2:
            return {'trend': 0, 'direction': 'stable'}
        
        # Simple linear trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        direction = 'improving' if slope < 0 else 'deteriorating' if slope > 0 else 'stable'
        
        return {
            'trend': slope,
            'direction': direction,
            'recent_avg': np.mean(values[-10:]) if len(values) >= 10 else np.mean(values)
        }
    
    def _analyze_venue_performance(self, executions: List[Dict]) -> Dict[str, Dict]:
        """Analyze venue performance"""
        
        venue_stats = defaultdict(lambda: {
            'executions': 0,
            'volume': 0,
            'total_slippage': 0,
            'avg_slippage': 0
        })
        
        for exec in executions:
            for venue, allocation in exec.get('venue_breakdown', {}).items():
                stats = venue_stats[venue]
                stats['executions'] += 1
                stats['volume'] += exec['executed_quantity'] * allocation
                stats['total_slippage'] += exec['slippage_bps'] * allocation
        
        # Calculate averages
        for venue, stats in venue_stats.items():
            if stats['executions'] > 0:
                stats['avg_slippage'] = stats['total_slippage'] / stats['executions']
        
        return dict(venue_stats)


class ExecutionManager:
    """
    Unified Execution Manager
    
    Orchestrates all execution components to provide comprehensive
    execution capabilities with unified management and monitoring.
    """
    
    def __init__(self, config: Optional[ExecutionConfiguration] = None):
        """Initialize execution manager"""
        
        self.config = config or ExecutionConfiguration()
        
        # Core execution components
        self.execution_engine = ExecutionEngine()
        self.order_executor = OrderExecutor()
        self.trade_executor = TradeExecutor()
        self.fill_processor = FillProcessor()
        self.execution_validator = ExecutionValidator()
        
        # Management components
        self.execution_queue = ExecutionQueue()
        self.execution_monitor = ExecutionMonitor(self.config)
        self.execution_reporter = ExecutionReporter(self.config)
        
        # Active executions
        self._active_executions = {}
        self._execution_history = {}
        
        # Threading and async
        self._lock = threading.Lock()
        self._running = False
        self._execution_task = None
        
        # Performance tracking
        self._performance_metrics = defaultdict(list)
        
        logger.info("Execution Manager initialized")
    
    async def submit_execution_request(self, request: UnifiedExecutionRequest) -> str:
        """Submit unified execution request"""
        
        try:
            # Validate request
            self._validate_request(request)
            
            # Create execution context for validation
            context = ExecutionContext(
                execution_id=request.request_id,
                order_id=request.request_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=request.limit_price,
                strategy_id=request.strategy_id,
                portfolio_id=request.portfolio_id
            )
            
            # Pre-trade validation
            if self.config.enable_pre_trade_validation:
                validation_passed, validation_results = self.execution_validator.validate_pre_trade(context)
                
                if not validation_passed:
                    error_msg = "Pre-trade validation failed: " + "; ".join([
                        r.message for r in validation_results if not r.passed
                    ])
                    raise ValueError(error_msg)
            
            # Add to execution queue
            self.execution_queue.add_request(request)
            
            # Initialize execution status
            status = ExecutionStatus(
                request_id=request.request_id,
                symbol=request.symbol,
                side=request.side,
                total_quantity=request.quantity,
                executed_quantity=0.0,
                remaining_quantity=request.quantity,
                fill_rate=0.0,
                avg_execution_price=0.0,
                total_slippage_bps=0.0,
                market_impact_bps=0.0,
                overall_status="QUEUED",
                active_orders=0,
                completed_orders=0,
                start_time=datetime.now()
            )
            
            with self._lock:
                self._active_executions[request.request_id] = {
                    'request': request,
                    'status': status,
                    'context': context
                }
            
            logger.info(f"Execution request {request.request_id} submitted and queued")
            return request.request_id
            
        except Exception as e:
            logger.error(f"Error submitting execution request: {e}")
            raise
    
    async def start_execution_processing(self) -> None:
        """Start processing execution queue"""
        
        if self._running:
            return
        
        self._running = True
        self.execution_monitor.start_monitoring()
        
        # Start all components
        self.execution_engine.start()
        self.order_executor.start()
        self.trade_executor.start()
        self.fill_processor.start()
        self.execution_validator.start()
        
        # Start processing task
        self._execution_task = asyncio.create_task(self._execution_processing_loop())
        
        logger.info("Execution processing started")
    
    async def stop_execution_processing(self) -> None:
        """Stop processing execution queue"""
        
        self._running = False
        self.execution_monitor.stop_monitoring()
        
        # Stop components
        self.execution_engine.stop()
        self.order_executor.stop()
        self.trade_executor.stop()
        self.fill_processor.stop()
        self.execution_validator.stop()
        
        # Cancel processing task
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Execution processing stopped")
    
    async def _execution_processing_loop(self) -> None:
        """Main execution processing loop"""
        
        while self._running:
            try:
                # Get next request from queue
                request = self.execution_queue.get_next_request()
                
                if request:
                    # Process execution
                    await self._process_execution_request(request)
                else:
                    # No requests - wait briefly
                    await asyncio.sleep(0.1)
                
                # Update all active executions
                await self._update_active_executions()
                
                # Generate reports if needed
                if self.config.generate_execution_reports:
                    await self._generate_periodic_reports()
                
            except Exception as e:
                logger.error(f"Error in execution processing loop: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _process_execution_request(self, request: UnifiedExecutionRequest) -> None:
        """Process individual execution request"""
        
        try:
            with self._lock:
                execution_data = self._active_executions.get(request.request_id)
            
            if not execution_data:
                logger.warning(f"Execution data not found for request {request.request_id}")
                return
            
            status = execution_data['status']
            execution_data['context']
            
            # Update status to active
            status.overall_status = "ACTIVE"
            status.start_time = datetime.now()
            
            # Determine execution method based on request type
            if request.execution_type in ['TWAP', 'VWAP', 'POV', 'IS']:
                # Use trade executor for algorithmic execution
                trade_request = TradeExecutionRequest(
                    trade_id=request.request_id,
                    symbol=request.symbol,
                    side=request.side,
                    quantity=request.quantity,
                    algorithm=self._map_execution_algorithm(request.execution_type),
                    start_time=request.start_time,
                    end_time=request.end_time,
                    participation_rate=request.participation_rate or 0.1,
                    risk_aversion=request.risk_aversion or 0.5,
                    price_limit=request.limit_price,
                    strategy_id=request.strategy_id,
                    portfolio_id=request.portfolio_id,
                    progress_callback=lambda progress: self._handle_execution_progress(request.request_id, progress),
                    completion_callback=lambda result: self._handle_execution_completion(request.request_id, result)
                )
                
                await self.trade_executor.execute_trade(trade_request)
                
            else:
                # Use order executor for simple orders
                order_request = OrderRequest(
                    order_id=request.request_id,
                    symbol=request.symbol,
                    side=request.side,
                    quantity=request.quantity,
                    limit_price=request.limit_price,
                    strategy_id=request.strategy_id,
                    fill_callback=lambda fill, state: self._handle_order_fill(request.request_id, fill, state)
                )
                
                await self.order_executor.execute_order(order_request)
            
            logger.info(f"Started processing execution request {request.request_id}")
            
        except Exception as e:
            logger.error(f"Error processing execution request {request.request_id}: {e}")
            # Update status to failed
            if request.request_id in self._active_executions:
                self._active_executions[request.request_id]['status'].overall_status = "FAILED"
    
    def _map_execution_algorithm(self, execution_type: str):
        """Map execution type to algorithm enum"""
        from .trade_executor import TradeExecutionAlgorithm
        
        mapping = {
            'TWAP': TradeExecutionAlgorithm.TWAP,
            'VWAP': TradeExecutionAlgorithm.VWAP,
            'POV': TradeExecutionAlgorithm.POV,
            'IS': TradeExecutionAlgorithm.IS
        }
        
        return mapping.get(execution_type, TradeExecutionAlgorithm.TWAP)
    
    def _handle_execution_progress(self, request_id: str, progress: Dict[str, Any]) -> None:
        """Handle execution progress updates"""
        
        with self._lock:
            if request_id in self._active_executions:
                status = self._active_executions[request_id]['status']
                
                # Update status with progress
                status.executed_quantity = progress.get('executed_quantity', 0)
                status.remaining_quantity = progress.get('remaining_quantity', status.total_quantity)
                status.fill_rate = status.executed_quantity / status.total_quantity if status.total_quantity > 0 else 0
                status.avg_execution_price = progress.get('avg_price', 0)
                
                # Update performance metrics
                if 'performance' in progress:
                    perf = progress['performance']
                    status.total_slippage_bps = perf.get('slippage_bps', 0)
                    status.market_impact_bps = perf.get('market_impact_bps', 0)
                
                status.last_updated = datetime.now()
                
                # Check for alerts
                alerts = self.execution_monitor.check_execution_health(status)
                if alerts:
                    logger.warning(f"Execution alerts for {request_id}: {alerts}")
    
    def _handle_execution_completion(self, request_id: str, result: Dict[str, Any]) -> None:
        """Handle execution completion"""
        
        with self._lock:
            if request_id in self._active_executions:
                execution_data = self._active_executions[request_id]
                status = execution_data['status']
                request = execution_data['request']
                
                # Update final status
                status.overall_status = "COMPLETED"
                status.actual_completion = datetime.now()
                status.execution_quality_score = self._calculate_execution_quality(status)
                
                # Move to history
                self._execution_history[request_id] = execution_data
                del self._active_executions[request_id]
                
                # Record for reporting
                self.execution_reporter.record_execution(request, status)
                
                # Update performance metrics
                self.execution_monitor.update_performance_metrics(status)
                
                # Trigger completion callback
                if request.completion_callback:
                    try:
                        request.completion_callback(result)
                    except Exception as e:
                        logger.error(f"Error in completion callback: {e}")
                
                logger.info(f"Execution {request_id} completed")
    
    def _handle_order_fill(self, request_id: str, fill: Any, state: Any) -> None:
        """Handle order fill events"""
        
        # Convert to trade execution for fill processor
        execution = TradeExecution(
            execution_id=f"{request_id}_fill_{int(time.time())}",
            order_id=request_id,
            symbol=fill.symbol,
            side=fill.side,
            quantity=fill.fill_quantity,
            price=fill.fill_price,
            execution_time=fill.fill_time,
            venue=fill.venue
        )
        
        # Process fill
        asyncio.create_task(self.fill_processor.process_fill(execution))
    
    async def _update_active_executions(self) -> None:
        """Update status of all active executions"""
        
        with self._lock:
            active_requests = list(self._active_executions.keys())
        
        for request_id in active_requests:
            try:
                # Get latest status from executors
                trade_status = self.trade_executor.get_trade_status(request_id)
                order_status = self.order_executor.get_order_status(request_id)
                
                # Update execution status
                with self._lock:
                    if request_id in self._active_executions:
                        execution_data = self._active_executions[request_id]
                        status = execution_data['status']
                        context = execution_data['context']
                        
                        # Update from trade executor
                        if trade_status:
                            status.executed_quantity = trade_status.get('executed_quantity', 0)
                            status.avg_execution_price = trade_status.get('avg_execution_price', 0)
                            status.fill_rate = trade_status.get('fill_rate', 0)
                            
                            # Update performance metrics
                            perf = trade_status.get('performance_metrics', {})
                            status.total_slippage_bps = perf.get('slippage_bps', 0)
                            status.market_impact_bps = perf.get('market_impact_bps', 0)
                        
                        # Update from order executor
                        elif order_status:
                            status.executed_quantity = order_status.get('filled_quantity', 0)
                            status.avg_execution_price = order_status.get('avg_fill_price', 0)
                            status.fill_rate = order_status.get('fill_rate', 0)
                            status.total_slippage_bps = order_status.get('slippage_bps', 0)
                        
                        # Real-time validation if enabled
                        if self.config.enable_real_time_validation:
                            execution_metrics = {
                                'slippage': status.total_slippage_bps / 10000,
                                'market_impact': status.market_impact_bps / 10000,
                                'fill_rate': status.fill_rate,
                                'execution_time_seconds': (datetime.now() - status.start_time).total_seconds()
                            }
                            
                            validation_results = self.execution_validator.validate_real_time(context, execution_metrics)
                            
                            # Count validation issues
                            status.validation_warnings = len([r for r in validation_results if not r.passed and r.severity.value == 'warning'])
                            status.validation_errors = len([r for r in validation_results if not r.passed and r.severity.value == 'error'])
                        
                        status.last_updated = datetime.now()
                
            except Exception as e:
                logger.error(f"Error updating execution {request_id}: {e}")
    
    async def _generate_periodic_reports(self) -> None:
        """Generate periodic execution reports"""
        
        if not self.config.real_time_reporting:
            return
        
        # Generate reports every configured interval
        now = datetime.now()
        if hasattr(self, '_last_report_time'):
            time_since_last = (now - self._last_report_time).total_seconds() / 60
            if time_since_last < self.config.report_frequency_minutes:
                return
        
        try:
            # Generate daily report for today
            daily_report = self.execution_reporter.generate_daily_report(now)
            
            # Log key metrics
            if daily_report.get('total_executions', 0) > 0:
                logger.info(
                    f"Daily execution summary: {daily_report['total_executions']} executions, "
                    f"{daily_report['total_volume']:,.0f} volume, "
                    f"{daily_report['avg_slippage_bps']:.1f} bps avg slippage"
                )
            
            self._last_report_time = now
            
        except Exception as e:
            logger.error(f"Error generating periodic reports: {e}")
    
    def _calculate_execution_quality(self, status: ExecutionStatus) -> float:
        """Calculate execution quality score (0-100)"""
        
        score = 100.0
        
        # Penalize high slippage
        if status.total_slippage_bps > 0:
            slippage_penalty = min(50, status.total_slippage_bps * 2)  # 2 points per bp
            score -= slippage_penalty
        
        # Penalize high market impact
        if status.market_impact_bps > 0:
            impact_penalty = min(30, status.market_impact_bps * 3)  # 3 points per bp
            score -= impact_penalty
        
        # Penalize low fill rate
        if status.fill_rate < 1.0:
            fill_penalty = (1.0 - status.fill_rate) * 20  # 20 points for complete miss
            score -= fill_penalty
        
        return max(0, score)
    
    def _validate_request(self, request: UnifiedExecutionRequest) -> None:
        """Validate execution request"""
        
        if request.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if request.side not in ['BUY', 'SELL']:
            raise ValueError("Side must be 'BUY' or 'SELL'")
        
        if request.quantity > self.config.max_order_size:
            raise ValueError(f"Quantity {request.quantity:,.0f} exceeds maximum {self.config.max_order_size:,.0f}")
        
        if request.limit_price and request.quantity * request.limit_price > self.config.max_notional_per_order:
            notional = request.quantity * request.limit_price
            raise ValueError(f"Notional ${notional:,.2f} exceeds maximum ${self.config.max_notional_per_order:,.2f}")
    
    def cancel_execution(self, request_id: str) -> bool:
        """Cancel active execution"""
        
        try:
            # Try to remove from queue first
            if self.execution_queue.remove_request(request_id):
                logger.info(f"Execution {request_id} cancelled from queue")
                return True
            
            # Cancel active execution
            with self._lock:
                if request_id in self._active_executions:
                    execution_data = self._active_executions[request_id]
                    execution_data['status'].overall_status = "CANCELLED"
            
            # Cancel from executors
            trade_cancelled = self.trade_executor.cancel_trade(request_id)
            order_cancelled = self.order_executor.cancel_order(request_id)
            
            if trade_cancelled or order_cancelled:
                logger.info(f"Execution {request_id} cancelled")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling execution {request_id}: {e}")
            return False
    
    def get_execution_status(self, request_id: str) -> Optional[ExecutionStatus]:
        """Get execution status"""
        
        with self._lock:
            # Check active executions
            if request_id in self._active_executions:
                return self._active_executions[request_id]['status']
            
            # Check history
            if request_id in self._execution_history:
                return self._execution_history[request_id]['status']
        
        return None
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get comprehensive execution summary"""
        
        queue_summary = self.execution_queue.get_queue_summary()
        performance_summary = self.execution_monitor.get_performance_summary()
        recent_alerts = self.execution_monitor.get_recent_alerts()
        
        with self._lock:
            active_count = len(self._active_executions)
            completed_count = len(self._execution_history)
        
        return {
            'queue_summary': queue_summary,
            'active_executions': active_count,
            'completed_executions': completed_count,
            'performance_summary': performance_summary,
            'recent_alerts': len(recent_alerts),
            'execution_mode': self.config.execution_mode.value,
            'manager_status': 'running' if self._running else 'stopped'
        }
    
    def generate_comprehensive_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive execution report"""
        
        # Get performance analytics
        performance_analytics = self.execution_reporter.generate_performance_analytics(days)
        
        # Get validation summary
        validation_summary = self.execution_validator.get_validation_summary()
        
        # Get fill processing statistics
        fill_stats = self.fill_processor.get_processing_statistics()
        
        # Get recent daily reports
        daily_reports = []
        for i in range(min(days, 7)):  # Max 7 daily reports
            date = datetime.now() - timedelta(days=i)
            daily_report = self.execution_reporter.generate_daily_report(date)
            if daily_report.get('total_executions', 0) > 0:
                daily_reports.append(daily_report)
        
        return {
            'report_period_days': days,
            'performance_analytics': performance_analytics,
            'validation_summary': validation_summary,
            'fill_processing_stats': fill_stats,
            'daily_reports': daily_reports,
            'current_queue_size': self.execution_queue.get_queue_size(),
            'configuration': {
                'execution_mode': self.config.execution_mode.value,
                'max_order_size': self.config.max_order_size,
                'max_slippage_bps': self.config.max_slippage_bps,
                'enable_validations': {
                    'pre_trade': self.config.enable_pre_trade_validation,
                    'real_time': self.config.enable_real_time_validation,
                    'post_trade': self.config.enable_post_trade_validation
                }
            }
        }
    
    def start(self) -> None:
        """Start execution manager"""
        asyncio.create_task(self.start_execution_processing())
        logger.info("Execution Manager started")
    
    def stop(self) -> None:
        """Stop execution manager"""
        asyncio.create_task(self.stop_execution_processing())
        logger.info("Execution Manager stopped")