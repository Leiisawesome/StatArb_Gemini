"""
Trading Engine - Enhanced Trading Manager
Comprehensive trading manager integrating all trading components with sophisticated order orchestration
"""

import logging
import threading
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque

from .order_manager import (
    OrderManager, Order, OrderSide, OrderStatus
)
from .execution_handler import (
    ExecutionHandler, ExecutionStrategy, ExecutionReport
)
from .transaction_cost_analyzer import (
    TransactionCostAnalyzer, BenchmarkType
)
from .venue_router import (
    VenueRouter, RoutingStrategy, RoutingPlan, RouteOption
)

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    """Trading operation modes"""
    LIVE = "live"
    PAPER = "paper"
    SIMULATION = "simulation"
    BACKTEST = "backtest"


class TradingSessionStatus(Enum):
    """Trading session status"""
    INACTIVE = "inactive"
    PRE_MARKET = "pre_market"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    HALT = "halt"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class TradingConfiguration:
    """Trading system configuration"""
    mode: TradingMode
    session_status: TradingSessionStatus
    
    # Risk controls
    max_position_size: float
    max_daily_volume: float
    max_order_value: float
    position_limit_percentage: float
    
    # Execution settings
    default_execution_strategy: ExecutionStrategy
    default_routing_strategy: RoutingStrategy
    default_benchmark: BenchmarkType
    
    # Performance settings
    enable_cost_analysis: bool
    enable_venue_routing: bool
    enable_real_time_risk: bool
    
    # Operational settings
    order_timeout_seconds: int
    max_retry_attempts: int
    cool_down_period_seconds: int
    
    # Market data settings
    market_data_timeout_seconds: int
    price_staleness_threshold_seconds: int


@dataclass
class TradingMetrics:
    """Comprehensive trading performance metrics"""
    # Volume metrics
    total_orders: int
    executed_orders: int
    cancelled_orders: int
    rejected_orders: int
    total_volume: float
    total_value: float
    
    # Performance metrics
    fill_rate: float
    average_execution_time_ms: float
    average_slippage_bps: float
    average_cost_bps: float
    
    # Risk metrics
    max_position_size: float
    current_exposure: float
    risk_limit_breaches: int
    emergency_stops: int
    
    # Venue metrics
    venue_utilization: Dict[str, float]
    venue_performance: Dict[str, Dict[str, float]]
    
    # Time-based metrics
    orders_per_hour: float
    volume_per_hour: float
    peak_concurrent_orders: int
    
    # Quality metrics
    execution_quality_score: float
    cost_efficiency_score: float
    routing_efficiency_score: float
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradingAlert:
    """Trading system alert"""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    component: str
    
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    venue_id: Optional[str] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class TradingManagerEnhanced:
    """
    Enhanced trading manager orchestrating all trading components
    
    Provides comprehensive trading infrastructure with order management,
    execution handling, cost analysis, venue routing, and risk controls.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced trading manager"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Trading configuration
        self.trading_config = self._initialize_trading_config()
        
        # Core components
        self.order_manager = OrderManager(self.config.get('order_manager', {}))
        self.execution_handler = ExecutionHandler(self.config.get('execution_handler', {}))
        self.cost_analyzer = TransactionCostAnalyzer(self.config.get('cost_analyzer', {}))
        self.venue_router = VenueRouter(self.config.get('venue_router', {}))
        
        # Trading state
        self._active_orders = {}
        self._pending_executions = {}
        self._trading_metrics = self._initialize_metrics()
        
        # Session management
        self._session_start_time = None
        self._session_orders = deque(maxlen=10000)
        self._session_executions = deque(maxlen=10000)
        
        # Alert system
        self._alerts = deque(maxlen=1000)
        self._alert_handlers = {}
        
        # Performance tracking
        self._performance_history = defaultdict(list)
        self._execution_reports = deque(maxlen=5000)
        
        # Callbacks and hooks
        self._order_status_callbacks = []
        self._execution_callbacks = []
        self._risk_callbacks = []
        
        # Background tasks
        self._monitoring_tasks = []
        self._cleanup_tasks = []
        
        # Initialize monitoring
        asyncio.create_task(self._start_monitoring())
        
        logger.info("TradingManagerEnhanced initialized")
    
    def _initialize_trading_config(self) -> TradingConfiguration:
        """Initialize trading configuration"""
        return TradingConfiguration(
            mode=TradingMode(self.config.get('mode', 'paper')),
            session_status=TradingSessionStatus.INACTIVE,
            max_position_size=self.config.get('max_position_size', 1000000),
            max_daily_volume=self.config.get('max_daily_volume', 10000000),
            max_order_value=self.config.get('max_order_value', 500000),
            position_limit_percentage=self.config.get('position_limit_percentage', 5.0),
            default_execution_strategy=ExecutionStrategy(
                self.config.get('default_execution_strategy', 'balanced')
            ),
            default_routing_strategy=RoutingStrategy(
                self.config.get('default_routing_strategy', 'balanced')
            ),
            default_benchmark=BenchmarkType(
                self.config.get('default_benchmark', 'arrival_price')
            ),
            enable_cost_analysis=self.config.get('enable_cost_analysis', True),
            enable_venue_routing=self.config.get('enable_venue_routing', True),
            enable_real_time_risk=self.config.get('enable_real_time_risk', True),
            order_timeout_seconds=self.config.get('order_timeout_seconds', 300),
            max_retry_attempts=self.config.get('max_retry_attempts', 3),
            cool_down_period_seconds=self.config.get('cool_down_period_seconds', 60),
            market_data_timeout_seconds=self.config.get('market_data_timeout_seconds', 30),
            price_staleness_threshold_seconds=self.config.get('price_staleness_threshold_seconds', 10)
        )
    
    def _initialize_metrics(self) -> TradingMetrics:
        """Initialize trading metrics"""
        return TradingMetrics(
            total_orders=0,
            executed_orders=0,
            cancelled_orders=0,
            rejected_orders=0,
            total_volume=0.0,
            total_value=0.0,
            fill_rate=0.0,
            average_execution_time_ms=0.0,
            average_slippage_bps=0.0,
            average_cost_bps=0.0,
            max_position_size=0.0,
            current_exposure=0.0,
            risk_limit_breaches=0,
            emergency_stops=0,
            venue_utilization={},
            venue_performance={},
            orders_per_hour=0.0,
            volume_per_hour=0.0,
            peak_concurrent_orders=0,
            execution_quality_score=0.0,
            cost_efficiency_score=0.0,
            routing_efficiency_score=0.0
        )
    
    async def _start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        self._monitoring_tasks = [
            asyncio.create_task(self._monitor_orders()),
            asyncio.create_task(self._monitor_executions()),
            asyncio.create_task(self._monitor_metrics()),
            asyncio.create_task(self._monitor_risk()),
        ]
        
        logger.info("Started trading monitoring tasks")
    
    async def start_trading_session(self) -> None:
        """Start trading session"""
        try:
            self.trading_config.session_status = TradingSessionStatus.OPEN
            self._session_start_time = datetime.now()
            
            # Reset session metrics
            self._session_orders.clear()
            self._session_executions.clear()
            
            logger.info("Trading session started")
            
            # Send session start alert
            await self._send_alert(
                alert_type="session_event",
                severity="info",
                message="Trading session started",
                component="trading_manager"
            )
            
        except Exception as e:
            logger.error(f"Error starting trading session: {e}")
            raise
    
    async def stop_trading_session(self, emergency: bool = False) -> None:
        """Stop trading session"""
        try:
            if emergency:
                self.trading_config.session_status = TradingSessionStatus.EMERGENCY_STOP
                
                # Cancel all active orders
                await self._cancel_all_active_orders("Emergency stop")
                
                logger.warning("Emergency stop activated - all orders cancelled")
            else:
                self.trading_config.session_status = TradingSessionStatus.CLOSED
                logger.info("Trading session stopped")
            
            # Send session stop alert
            await self._send_alert(
                alert_type="session_event",
                severity="warning" if emergency else "info",
                message=f"Trading session {'emergency stopped' if emergency else 'stopped'}",
                component="trading_manager"
            )
            
        except Exception as e:
            logger.error(f"Error stopping trading session: {e}")
            raise
    
    async def submit_order(
        self,
        order: Order,
        execution_strategy: Optional[ExecutionStrategy] = None,
        routing_strategy: Optional[RoutingStrategy] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit order for execution
        
        Args:
            order: Order to submit
            execution_strategy: Execution strategy override
            routing_strategy: Routing strategy override
            constraints: Additional constraints
            
        Returns:
            Order ID
        """
        try:
            # Check trading session status
            if self.trading_config.session_status not in [TradingSessionStatus.OPEN, TradingSessionStatus.PRE_MARKET]:
                raise ValueError(f"Trading session not active: {self.trading_config.session_status.value}")
            
            logger.debug(f"Submitting order: {order.symbol} {order.side.value} {order.quantity}")
            
            # Pre-trade risk checks
            await self._pre_trade_risk_check(order)
            
            # Submit to order manager
            order_id = await self.order_manager.submit_order(order)
            
            # Store active order
            with self._lock:
                self._active_orders[order_id] = {
                    'order': order,
                    'submission_time': datetime.now(),
                    'execution_strategy': execution_strategy or self.trading_config.default_execution_strategy,
                    'routing_strategy': routing_strategy or self.trading_config.default_routing_strategy,
                    'constraints': constraints or {}
                }
                self._session_orders.append(order_id)
            
            # Create routing plan if venue routing enabled
            if self.trading_config.enable_venue_routing:
                routing_plan = await self.venue_router.create_routing_plan(
                    order,
                    routing_strategy or self.trading_config.default_routing_strategy,
                    constraints
                )
                
                # Store routing plan
                self._active_orders[order_id]['routing_plan'] = routing_plan
            
            # Begin execution
            await self._execute_order(order_id)
            
            # Update metrics
            with self._lock:
                self._trading_metrics.total_orders += 1
            
            logger.info(f"Order submitted successfully: {order_id}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            
            # Update metrics
            with self._lock:
                self._trading_metrics.rejected_orders += 1
            
            # Send alert
            await self._send_alert(
                alert_type="order_error",
                severity="error",
                message=f"Order submission failed: {e}",
                component="trading_manager",
                order_id=order.order_id,
                symbol=order.symbol
            )
            
            raise
    
    async def _pre_trade_risk_check(self, order: Order) -> None:
        """Perform pre-trade risk checks"""
        
        # Check order value limit
        estimated_value = order.quantity * (order.price or 100.0)  # Use price or estimate
        if estimated_value > self.trading_config.max_order_value:
            raise ValueError(f"Order value {estimated_value} exceeds limit {self.trading_config.max_order_value}")
        
        # Check position size limit
        if order.quantity > self.trading_config.max_position_size:
            raise ValueError(f"Order quantity {order.quantity} exceeds position limit {self.trading_config.max_position_size}")
        
        # Check daily volume limit
        daily_volume = await self._calculate_daily_volume()
        if daily_volume + order.quantity > self.trading_config.max_daily_volume:
            raise ValueError(f"Order would exceed daily volume limit")
        
        # Additional real-time risk checks
        if self.trading_config.enable_real_time_risk:
            current_exposure = await self._calculate_current_exposure(order.symbol)
            max_symbol_exposure = self.trading_config.max_position_size * 0.1  # 10% per symbol
            
            if current_exposure + order.quantity > max_symbol_exposure:
                raise ValueError(f"Order would exceed symbol exposure limit")
    
    async def _execute_order(self, order_id: str) -> None:
        """Execute order using configured strategy"""
        try:
            order_info = self._active_orders.get(order_id)
            if not order_info:
                raise ValueError(f"Order {order_id} not found in active orders")
            
            order = order_info['order']
            execution_strategy = order_info['execution_strategy']
            routing_plan = order_info.get('routing_plan')
            
            # Prepare execution context
            execution_context = {
                'order': order,
                'strategy': execution_strategy,
                'routing_plan': routing_plan,
                'market_data': await self._get_market_data(order.symbol),
                'venue_selection': self._prepare_venue_selection(routing_plan)
            }
            
            # Execute using execution handler
            execution_report = await self.execution_handler.execute_order(
                order,
                execution_strategy,
                execution_context
            )
            
            # Store execution report
            with self._lock:
                self._execution_reports.append(execution_report)
                self._session_executions.append(execution_report)
            
            # Process execution results
            await self._process_execution_report(execution_report)
            
            logger.info(f"Order execution completed: {order_id}")
            
        except Exception as e:
            logger.error(f"Error executing order {order_id}: {e}")
            await self._handle_execution_error(order_id, e)
    
    def _prepare_venue_selection(self, routing_plan: Optional[RoutingPlan]) -> Optional[Dict[str, Any]]:
        """Prepare venue selection from routing plan"""
        if not routing_plan:
            return None
        
        # Convert routing plan to venue selection
        venue_allocations = {}
        for route_option in routing_plan.route_options:
            venue_allocations[route_option.venue_id] = route_option.allocation_percentage / 100.0
        
        return {
            'primary_venue': routing_plan.route_options[0].venue_id if routing_plan.route_options else None,
            'venue_allocations': venue_allocations,
            'routing_strategy': routing_plan.routing_strategy
        }
    
    async def _process_execution_report(self, execution_report: ExecutionReport) -> None:
        """Process execution report and update metrics"""
        
        metrics = execution_report.metrics
        
        # Update order status
        order_status = OrderStatus.PARTIALLY_FILLED if metrics.executed_quantity < metrics.total_quantity else OrderStatus.FILLED
        await self.order_manager.update_order_status(execution_report.order_id, order_status)
        
        # Cost analysis if enabled
        if self.trading_config.enable_cost_analysis:
            try:
                cost_breakdown = await self.cost_analyzer.analyze_transaction_costs(
                    execution_report,
                    await self._get_market_data(metrics.symbol),
                    self.trading_config.default_benchmark
                )
                
                # Store cost analysis
                execution_report.cost_breakdown = cost_breakdown
                
            except Exception as e:
                logger.warning(f"Cost analysis failed for order {execution_report.order_id}: {e}")
        
        # Update trading metrics
        await self._update_trading_metrics(execution_report)
        
        # Call execution callbacks
        for callback in self._execution_callbacks:
            try:
                await callback(execution_report)
            except Exception as e:
                logger.warning(f"Execution callback error: {e}")
        
        # Check for alerts
        await self._check_execution_alerts(execution_report)
    
    async def _update_trading_metrics(self, execution_report: ExecutionReport) -> None:
        """Update trading performance metrics"""
        
        metrics = execution_report.metrics
        
        with self._lock:
            # Execution metrics
            if metrics.executed_quantity > 0:
                self._trading_metrics.executed_orders += 1
                self._trading_metrics.total_volume += metrics.executed_quantity
                self._trading_metrics.total_value += metrics.executed_quantity * metrics.average_execution_price
            
            # Performance metrics
            total_orders = max(1, self._trading_metrics.total_orders)
            executed_orders = self._trading_metrics.executed_orders
            
            self._trading_metrics.fill_rate = executed_orders / total_orders
            
            # Update averages
            if executed_orders > 0:
                current_avg_time = self._trading_metrics.average_execution_time_ms
                new_time = metrics.execution_duration_ms
                self._trading_metrics.average_execution_time_ms = (
                    (current_avg_time * (executed_orders - 1) + new_time) / executed_orders
                )
                
                current_avg_slippage = self._trading_metrics.average_slippage_bps
                new_slippage = abs(metrics.slippage_bps)
                self._trading_metrics.average_slippage_bps = (
                    (current_avg_slippage * (executed_orders - 1) + new_slippage) / executed_orders
                )
                
                # Cost metrics if available
                if hasattr(execution_report, 'cost_breakdown') and execution_report.cost_breakdown:
                    current_avg_cost = self._trading_metrics.average_cost_bps
                    new_cost = abs(execution_report.cost_breakdown.total_cost_bps)
                    self._trading_metrics.average_cost_bps = (
                        (current_avg_cost * (executed_orders - 1) + new_cost) / executed_orders
                    )
            
            # Update exposure
            position_change = metrics.executed_quantity if metrics.side == OrderSide.BUY else -metrics.executed_quantity
            self._trading_metrics.current_exposure += position_change * metrics.average_execution_price
            
            # Update concurrent orders
            self._trading_metrics.peak_concurrent_orders = max(
                self._trading_metrics.peak_concurrent_orders,
                len(self._active_orders)
            )
    
    async def _check_execution_alerts(self, execution_report: ExecutionReport) -> None:
        """Check for execution-related alerts"""
        
        metrics = execution_report.metrics
        
        # High slippage alert
        if abs(metrics.slippage_bps) > 50:
            await self._send_alert(
                alert_type="execution_performance",
                severity="warning",
                message=f"High slippage detected: {metrics.slippage_bps:.2f} bps",
                component="execution_handler",
                order_id=execution_report.order_id,
                symbol=metrics.symbol,
                metadata={'slippage_bps': metrics.slippage_bps}
            )
        
        # Poor fill rate alert
        fill_rate = metrics.executed_quantity / metrics.total_quantity
        if fill_rate < 0.8:
            await self._send_alert(
                alert_type="execution_performance",
                severity="warning",
                message=f"Low fill rate: {fill_rate:.1%}",
                component="execution_handler",
                order_id=execution_report.order_id,
                symbol=metrics.symbol,
                metadata={'fill_rate': fill_rate}
            )
        
        # Long execution time alert
        if metrics.execution_duration_ms > 30000:  # 30 seconds
            await self._send_alert(
                alert_type="execution_performance",
                severity="warning",
                message=f"Long execution time: {metrics.execution_duration_ms/1000:.1f}s",
                component="execution_handler",
                order_id=execution_report.order_id,
                symbol=metrics.symbol,
                metadata={'execution_time_ms': metrics.execution_duration_ms}
            )
    
    async def cancel_order(self, order_id: str, reason: str = "User cancellation") -> bool:
        """Cancel an active order"""
        try:
            success = await self.order_manager.cancel_order(order_id, reason)
            
            if success:
                # Remove from active orders
                with self._lock:
                    self._active_orders.pop(order_id, None)
                    self._trading_metrics.cancelled_orders += 1
                
                logger.info(f"Order cancelled: {order_id}")
                
                # Send alert
                await self._send_alert(
                    alert_type="order_event",
                    severity="info",
                    message=f"Order cancelled: {reason}",
                    component="trading_manager",
                    order_id=order_id
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def _cancel_all_active_orders(self, reason: str) -> None:
        """Cancel all active orders"""
        active_order_ids = list(self._active_orders.keys())
        
        for order_id in active_order_ids:
            try:
                await self.cancel_order(order_id, reason)
            except Exception as e:
                logger.error(f"Error cancelling order {order_id}: {e}")
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for symbol"""
        # In a real implementation, this would fetch from market data provider
        # For now, simulate market data
        return {
            'symbol': symbol,
            'bid_price': 99.95,
            'ask_price': 100.05,
            'last_price': 100.0,
            'bid_size': 1000,
            'ask_size': 1000,
            'volume': 50000,
            'volatility': 0.2,
            'timestamp': datetime.now()
        }
    
    async def _calculate_daily_volume(self) -> float:
        """Calculate total volume traded today"""
        today = datetime.now().date()
        
        daily_volume = 0.0
        with self._lock:
            for execution_report in self._execution_reports:
                if execution_report.timestamp.date() == today:
                    daily_volume += execution_report.metrics.executed_quantity
        
        return daily_volume
    
    async def _calculate_current_exposure(self, symbol: str) -> float:
        """Calculate current exposure for symbol"""
        # This would typically query from portfolio manager
        # For now, return a simple calculation
        exposure = 0.0
        
        with self._lock:
            for execution_report in self._execution_reports:
                if execution_report.metrics.symbol == symbol:
                    if execution_report.metrics.side == OrderSide.BUY:
                        exposure += execution_report.metrics.executed_quantity
                    else:
                        exposure -= execution_report.metrics.executed_quantity
        
        return abs(exposure)
    
    async def _handle_execution_error(self, order_id: str, error: Exception) -> None:
        """Handle execution error"""
        
        # Update order status
        await self.order_manager.update_order_status(order_id, OrderStatus.REJECTED, str(error))
        
        # Remove from active orders
        with self._lock:
            self._active_orders.pop(order_id, None)
            self._trading_metrics.rejected_orders += 1
        
        # Send alert
        await self._send_alert(
            alert_type="execution_error",
            severity="error",
            message=f"Execution error: {error}",
            component="execution_handler",
            order_id=order_id
        )
    
    async def _send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        component: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        venue_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send system alert"""
        
        alert = TradingAlert(
            alert_id=f"alert_{int(time.time() * 1000)}",
            alert_type=alert_type,
            severity=severity,
            message=message,
            component=component,
            order_id=order_id,
            symbol=symbol,
            venue_id=venue_id,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._alerts.append(alert)
        
        # Call alert handlers
        for handler in self._alert_handlers.get(alert_type, []):
            try:
                await handler(alert)
            except Exception as e:
                logger.warning(f"Alert handler error: {e}")
        
        # Log alert
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(log_level, f"ALERT [{alert_type}]: {message}")
    
    async def _monitor_orders(self) -> None:
        """Monitor active orders"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                current_time = datetime.now()
                timeout_threshold = timedelta(seconds=self.trading_config.order_timeout_seconds)
                
                # Check for timed out orders
                with self._lock:
                    timed_out_orders = []
                    for order_id, order_info in self._active_orders.items():
                        if current_time - order_info['submission_time'] > timeout_threshold:
                            timed_out_orders.append(order_id)
                
                # Cancel timed out orders
                for order_id in timed_out_orders:
                    logger.warning(f"Order {order_id} timed out")
                    await self.cancel_order(order_id, "Order timeout")
                
            except Exception as e:
                logger.error(f"Error in order monitoring: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_executions(self) -> None:
        """Monitor execution performance"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Calculate recent performance metrics
                recent_executions = []
                cutoff_time = datetime.now() - timedelta(minutes=15)
                
                with self._lock:
                    recent_executions = [
                        report for report in self._execution_reports
                        if report.timestamp >= cutoff_time
                    ]
                
                if recent_executions:
                    # Calculate average metrics
                    avg_slippage = np.mean([
                        abs(report.metrics.slippage_bps) for report in recent_executions
                    ])
                    
                    avg_execution_time = np.mean([
                        report.metrics.execution_duration_ms for report in recent_executions
                    ])
                    
                    fill_rates = [
                        report.metrics.executed_quantity / report.metrics.total_quantity
                        for report in recent_executions
                    ]
                    avg_fill_rate = np.mean(fill_rates)
                    
                    # Check for performance degradation
                    if avg_slippage > 25:  # 25 bps threshold
                        await self._send_alert(
                            alert_type="performance_degradation",
                            severity="warning",
                            message=f"High average slippage: {avg_slippage:.2f} bps",
                            component="trading_manager"
                        )
                    
                    if avg_fill_rate < 0.85:  # 85% threshold
                        await self._send_alert(
                            alert_type="performance_degradation",
                            severity="warning",
                            message=f"Low average fill rate: {avg_fill_rate:.1%}",
                            component="trading_manager"
                        )
                
            except Exception as e:
                logger.error(f"Error in execution monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_metrics(self) -> None:
        """Monitor and update trading metrics"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Update session-based metrics
                if self._session_start_time:
                    session_duration = (datetime.now() - self._session_start_time).total_seconds() / 3600
                    
                    with self._lock:
                        self._trading_metrics.orders_per_hour = (
                            len(self._session_orders) / session_duration if session_duration > 0 else 0
                        )
                        self._trading_metrics.volume_per_hour = (
                            self._trading_metrics.total_volume / session_duration if session_duration > 0 else 0
                        )
                
                # Calculate quality scores
                with self._lock:
                    # Execution quality score
                    if self._trading_metrics.average_slippage_bps > 0:
                        self._trading_metrics.execution_quality_score = max(0, 100 - self._trading_metrics.average_slippage_bps)
                    
                    # Cost efficiency score
                    if self._trading_metrics.average_cost_bps > 0:
                        self._trading_metrics.cost_efficiency_score = max(0, 100 - self._trading_metrics.average_cost_bps)
                    
                    # Update timestamp
                    self._trading_metrics.timestamp = datetime.now()
                
            except Exception as e:
                logger.error(f"Error in metrics monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_risk(self) -> None:
        """Monitor risk metrics and limits"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Check position limits
                current_exposure = abs(self._trading_metrics.current_exposure)
                max_exposure = self.trading_config.max_position_size * 100  # Assuming $100 per share
                
                if current_exposure > max_exposure * 0.9:  # 90% of limit
                    await self._send_alert(
                        alert_type="risk_limit",
                        severity="warning",
                        message=f"Approaching exposure limit: {current_exposure:.0f} / {max_exposure:.0f}",
                        component="risk_monitor"
                    )
                
                # Check daily volume limits
                daily_volume = await self._calculate_daily_volume()
                if daily_volume > self.trading_config.max_daily_volume * 0.9:
                    await self._send_alert(
                        alert_type="risk_limit",
                        severity="warning",
                        message=f"Approaching daily volume limit: {daily_volume:.0f} / {self.trading_config.max_daily_volume:.0f}",
                        component="risk_monitor"
                    )
                
            except Exception as e:
                logger.error(f"Error in risk monitoring: {e}")
                await asyncio.sleep(30)
    
    def add_order_status_callback(self, callback: Callable) -> None:
        """Add order status change callback"""
        self._order_status_callbacks.append(callback)
    
    def add_execution_callback(self, callback: Callable) -> None:
        """Add execution callback"""
        self._execution_callbacks.append(callback)
    
    def add_risk_callback(self, callback: Callable) -> None:
        """Add risk event callback"""
        self._risk_callbacks.append(callback)
    
    def add_alert_handler(self, alert_type: str, handler: Callable) -> None:
        """Add alert handler for specific alert type"""
        if alert_type not in self._alert_handlers:
            self._alert_handlers[alert_type] = []
        self._alert_handlers[alert_type].append(handler)
    
    def get_trading_metrics(self) -> TradingMetrics:
        """Get current trading metrics"""
        with self._lock:
            return self._trading_metrics
    
    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """Get active orders"""
        with self._lock:
            return self._active_orders.copy()
    
    def get_recent_alerts(self, hours: int = 24) -> List[TradingAlert]:
        """Get recent alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                alert for alert in self._alerts
                if alert.timestamp >= cutoff_time
            ]
    
    def get_execution_reports(self, hours: int = 24) -> List[ExecutionReport]:
        """Get recent execution reports"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [
                report for report in self._execution_reports
                if report.timestamp >= cutoff_time
            ]
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get trading session summary"""
        if not self._session_start_time:
            return {'message': 'No active trading session'}
        
        session_duration = datetime.now() - self._session_start_time
        
        with self._lock:
            session_orders = len(self._session_orders)
            session_executions = len(self._session_executions)
            
            return {
                'session_start': self._session_start_time.isoformat(),
                'session_duration_hours': session_duration.total_seconds() / 3600,
                'session_status': self.trading_config.session_status.value,
                'total_orders': session_orders,
                'total_executions': session_executions,
                'active_orders': len(self._active_orders),
                'trading_metrics': self._trading_metrics,
                'recent_alerts': len([
                    alert for alert in self._alerts
                    if alert.timestamp >= self._session_start_time
                ])
            }
    
    async def cleanup(self) -> None:
        """Cleanup trading manager resources"""
        try:
            # Stop monitoring tasks
            for task in self._monitoring_tasks:
                task.cancel()
            
            # Cancel all active orders
            await self._cancel_all_active_orders("System shutdown")
            
            # Cleanup components
            await self.order_manager.cleanup()
            await self.execution_handler.cleanup()
            await self.cost_analyzer.cleanup()
            await self.venue_router.cleanup()
            
            logger.info("TradingManagerEnhanced cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise