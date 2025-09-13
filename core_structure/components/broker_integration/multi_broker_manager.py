#!/usr/bin/env python3
"""
Multi-Broker Management System
=============================

Institutional-grade multi-broker management with intelligent order routing,
broker selection, and failover capabilities.

Features:
- Multi-broker support with unified interface
- Intelligent broker selection based on performance
- Automatic failover and load balancing
- Cross-broker position reconciliation
- Performance analytics and broker comparison
- Smart order routing based on liquidity and costs

Author: Professional Trading System Architecture
Version: 1.0.0 (Multi-Broker Enhancement)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
from collections import defaultdict

from .base_broker import BaseBroker, Order, OrderResult, OrderStatus, Position, AccountSummary
from .advanced_order_management import AdvancedOrderManager, ExecutionParameters, ExecutionResult

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Supported broker types"""
    IBKR = "ibkr"
    ALPACA = "alpaca"
    TD_AMERITRADE = "td_ameritrade"
    SCHWAB = "schwab"
    FIDELITY = "fidelity"
    ROBINHOOD = "robinhood"
    WEBULL = "webull"


class RoutingStrategy(Enum):
    """Order routing strategies"""
    BEST_EXECUTION = "best_execution"  # Route to best execution
    LOWEST_COST = "lowest_cost"        # Route to lowest cost
    LOAD_BALANCE = "load_balance"      # Distribute across brokers
    PRIMARY_ONLY = "primary_only"      # Use primary broker only
    FAILOVER = "failover"              # Use failover logic
    LIQUIDITY_OPTIMIZED = "liquidity_optimized"  # Route based on liquidity


class BrokerStatus(Enum):
    """Broker connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    RATE_LIMITED = "rate_limited"


@dataclass
class BrokerMetrics:
    """Performance metrics for a broker"""
    broker_id: str
    broker_type: BrokerType
    
    # Connection metrics
    status: BrokerStatus = BrokerStatus.DISCONNECTED
    last_heartbeat: Optional[datetime] = None
    connection_uptime: float = 0.0
    
    # Order execution metrics
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    success_rate: float = 0.0
    
    # Performance metrics
    average_execution_time: float = 0.0
    average_slippage_bps: float = 0.0
    average_market_impact_bps: float = 0.0
    total_volume_traded: float = 0.0
    
    # Cost metrics
    commission_per_trade: float = 0.0
    total_commission_paid: float = 0.0
    
    # Reliability metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # Liquidity metrics (by symbol)
    symbol_liquidity: Dict[str, float] = field(default_factory=dict)
    best_bid_ask_spread: Dict[str, float] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingDecision:
    """Order routing decision"""
    order_id: str
    symbol: str
    quantity: float
    side: str
    
    # Routing decision
    selected_broker_id: str
    routing_strategy: RoutingStrategy
    confidence: float  # 0.0 to 1.0
    
    # Reasoning
    primary_reason: str
    alternative_brokers: List[str] = field(default_factory=list)
    
    # Performance expectations
    expected_execution_time: float = 0.0
    expected_cost_bps: float = 0.0
    expected_slippage_bps: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiBrokerManager:
    """Multi-broker management system with intelligent routing"""
    
    def __init__(self, primary_broker_id: str = "ibkr_primary"):
        self.logger = logging.getLogger(f"{__name__}.MultiBrokerManager")
        
        # Broker management
        self.brokers: Dict[str, BaseBroker] = {}
        self.broker_metrics: Dict[str, BrokerMetrics] = {}
        self.advanced_managers: Dict[str, AdvancedOrderManager] = {}
        
        # Configuration
        self.primary_broker_id = primary_broker_id
        self.routing_strategy = RoutingStrategy.BEST_EXECUTION
        self.failover_enabled = True
        self.load_balancing_enabled = True
        
        # Performance tracking
        self.routing_history: List[RoutingDecision] = []
        self.cross_broker_positions: Dict[str, Dict[str, Position]] = defaultdict(dict)
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.last_health_check = None
        
        self.logger.info(f"Multi-Broker Manager initialized with primary: {primary_broker_id}")
    
    async def add_broker(self, broker_id: str, broker: BaseBroker, broker_type: BrokerType) -> bool:
        """Add a broker to the manager"""
        try:
            self.brokers[broker_id] = broker
            self.broker_metrics[broker_id] = BrokerMetrics(
                broker_id=broker_id,
                broker_type=broker_type
            )
            
            # Create advanced order manager for this broker
            self.advanced_managers[broker_id] = AdvancedOrderManager(broker)
            
            # Test connection
            is_connected = await broker.connect()
            if is_connected:
                self.broker_metrics[broker_id].status = BrokerStatus.CONNECTED
                self.broker_metrics[broker_id].last_heartbeat = datetime.now()
                self.logger.info(f"Broker {broker_id} added and connected successfully")
            else:
                self.broker_metrics[broker_id].status = BrokerStatus.ERROR
                self.logger.warning(f"Broker {broker_id} added but connection failed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add broker {broker_id}: {e}")
            return False
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove a broker from the manager"""
        try:
            if broker_id in self.brokers:
                # Disconnect broker
                await self.brokers[broker_id].disconnect()
                
                # Clean up
                del self.brokers[broker_id]
                del self.broker_metrics[broker_id]
                if broker_id in self.advanced_managers:
                    del self.advanced_managers[broker_id]
                
                self.logger.info(f"Broker {broker_id} removed successfully")
                return True
            else:
                self.logger.warning(f"Broker {broker_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove broker {broker_id}: {e}")
            return False
    
    async def execute_order(self, order: Order, routing_strategy: Optional[RoutingStrategy] = None) -> OrderResult:
        """Execute order using multi-broker routing"""
        
        strategy = routing_strategy or self.routing_strategy
        
        # Make routing decision
        routing_decision = await self._make_routing_decision(order, strategy)
        
        # Store routing decision
        self.routing_history.append(routing_decision)
        
        try:
            # Execute order on selected broker
            selected_broker = self.brokers[routing_decision.selected_broker_id]
            result = await selected_broker.place_order(order)
            
            # Update broker metrics
            await self._update_broker_metrics(routing_decision.selected_broker_id, order, result)
            
            # Add routing information to result
            result.routing_info = {
                'broker_id': routing_decision.selected_broker_id,
                'routing_strategy': routing_decision.routing_strategy.value,
                'confidence': routing_decision.confidence,
                'reasoning': routing_decision.primary_reason
            }
            
            self.logger.info(f"Order {order.order_id} executed on {routing_decision.selected_broker_id} "
                           f"using {routing_decision.routing_strategy.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Order execution failed on {routing_decision.selected_broker_id}: {e}")
            
            # Try failover if enabled
            if self.failover_enabled:
                return await self._execute_failover(order, routing_decision)
            else:
                # Return failed result
                return OrderResult(
                    order_id=order.order_id,
                    success=False,
                    error_message=str(e),
                    timestamp=datetime.now()
                )
    
    async def execute_advanced_order(self, params: ExecutionParameters, 
                                   routing_strategy: Optional[RoutingStrategy] = None) -> ExecutionResult:
        """Execute advanced order using multi-broker routing"""
        
        strategy = routing_strategy or self.routing_strategy
        
        # Make routing decision
        routing_decision = await self._make_routing_decision(
            Order(
                order_id=params.symbol + "_" + str(uuid.uuid4().hex[:8]),
                symbol=params.symbol,
                side=params.side,
                quantity=params.quantity,
                order_type=None,  # Will be determined by execution algorithm
                time_in_force="GTC"
            ),
            strategy
        )
        
        try:
            # Execute advanced order on selected broker
            advanced_manager = self.advanced_managers[routing_decision.selected_broker_id]
            result = await advanced_manager.execute_order(params)
            
            # Update broker metrics
            await self._update_broker_metrics_advanced(routing_decision.selected_broker_id, params, result)
            
            # Add routing information to result
            result.routing_info = {
                'broker_id': routing_decision.selected_broker_id,
                'routing_strategy': routing_decision.routing_strategy.value,
                'confidence': routing_decision.confidence,
                'reasoning': routing_decision.primary_reason
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Advanced order execution failed on {routing_decision.selected_broker_id}: {e}")
            
            # Try failover if enabled
            if self.failover_enabled:
                return await self._execute_advanced_failover(params, routing_decision)
            else:
                # Return failed result
                return ExecutionResult(
                    order_id=params.symbol + "_" + str(uuid.uuid4().hex[:8]),
                    algorithm=params.algorithm,
                    execution_status=OrderStatus.REJECTED,
                    total_quantity=params.quantity,
                    filled_quantity=0.0,
                    average_price=0.0,
                    market_impact_bps=0.0,
                    timing_cost_bps=0.0,
                    total_cost_bps=0.0,
                    execution_time_minutes=0.0,
                    participation_rate=0.0,
                    slippage_bps=0.0
                )
    
    async def _make_routing_decision(self, order: Order, strategy: RoutingStrategy) -> RoutingDecision:
        """Make intelligent routing decision for order"""
        
        available_brokers = await self._get_available_brokers()
        
        if not available_brokers:
            raise RuntimeError("No available brokers for order routing")
        
        # Apply routing strategy
        if strategy == RoutingStrategy.PRIMARY_ONLY:
            selected_broker_id = self.primary_broker_id
            confidence = 1.0
            reason = "Primary broker only strategy"
            
        elif strategy == RoutingStrategy.BEST_EXECUTION:
            selected_broker_id, confidence = await self._select_best_execution_broker(order, available_brokers)
            reason = "Best execution based on historical performance"
            
        elif strategy == RoutingStrategy.LOWEST_COST:
            selected_broker_id, confidence = await self._select_lowest_cost_broker(order, available_brokers)
            reason = "Lowest cost based on commission and spreads"
            
        elif strategy == RoutingStrategy.LOAD_BALANCE:
            selected_broker_id, confidence = await self._select_load_balanced_broker(order, available_brokers)
            reason = "Load balancing across available brokers"
            
        elif strategy == RoutingStrategy.LIQUIDITY_OPTIMIZED:
            selected_broker_id, confidence = await self._select_liquidity_optimized_broker(order, available_brokers)
            reason = "Optimized for liquidity and market depth"
            
        else:  # FAILOVER or default
            selected_broker_id = self.primary_broker_id
            if selected_broker_id not in available_brokers:
                selected_broker_id = available_brokers[0]
            confidence = 0.8
            reason = "Failover routing"
        
        # Get alternative brokers
        alternative_brokers = [b for b in available_brokers if b != selected_broker_id]
        
        return RoutingDecision(
            order_id=order.order_id,
            symbol=order.symbol,
            quantity=order.quantity,
            side=order.side.value,
            selected_broker_id=selected_broker_id,
            routing_strategy=strategy,
            confidence=confidence,
            primary_reason=reason,
            alternative_brokers=alternative_brokers,
            expected_execution_time=self.broker_metrics[selected_broker_id].average_execution_time,
            expected_cost_bps=self.broker_metrics[selected_broker_id].average_market_impact_bps,
            expected_slippage_bps=self.broker_metrics[selected_broker_id].average_slippage_bps
        )
    
    async def _get_available_brokers(self) -> List[str]:
        """Get list of available brokers"""
        available = []
        
        for broker_id, metrics in self.broker_metrics.items():
            if (metrics.status == BrokerStatus.CONNECTED and 
                broker_id in self.brokers):
                try:
                    is_connected = await self.brokers[broker_id].is_connected()
                    if is_connected:
                        available.append(broker_id)
                except Exception:
                    # If connection check fails, skip this broker
                    continue
        
        return available
    
    async def _select_best_execution_broker(self, order: Order, available_brokers: List[str]) -> Tuple[str, float]:
        """Select broker with best execution performance"""
        
        best_broker = None
        best_score = -1.0
        
        for broker_id in available_brokers:
            metrics = self.broker_metrics[broker_id]
            
            # Calculate execution score based on multiple factors
            success_rate = metrics.success_rate
            execution_speed = 1.0 / max(metrics.average_execution_time, 0.1)  # Faster is better
            cost_efficiency = 1.0 / max(metrics.average_market_impact_bps, 0.1)  # Lower cost is better
            
            # Weighted score
            score = (success_rate * 0.4 + 
                    execution_speed * 0.3 + 
                    cost_efficiency * 0.3)
            
            if score > best_score:
                best_score = score
                best_broker = broker_id
        
        return best_broker or available_brokers[0], min(best_score, 1.0)
    
    async def _select_lowest_cost_broker(self, order: Order, available_brokers: List[str]) -> Tuple[str, float]:
        """Select broker with lowest cost"""
        
        lowest_cost_broker = None
        lowest_cost = float('inf')
        
        for broker_id in available_brokers:
            metrics = self.broker_metrics[broker_id]
            
            # Calculate total cost (commission + market impact + slippage)
            total_cost = (metrics.commission_per_trade + 
                         metrics.average_market_impact_bps + 
                         metrics.average_slippage_bps)
            
            if total_cost < lowest_cost:
                lowest_cost = total_cost
                lowest_cost_broker = broker_id
        
        return lowest_cost_broker or available_brokers[0], 0.9
    
    async def _select_load_balanced_broker(self, order: Order, available_brokers: List[str]) -> Tuple[str, float]:
        """Select broker for load balancing"""
        
        # Find broker with least recent activity
        least_active_broker = None
        min_activity = float('inf')
        
        for broker_id in available_brokers:
            metrics = self.broker_metrics[broker_id]
            
            # Use recent order count as activity measure
            activity = metrics.total_orders
            
            if activity < min_activity:
                min_activity = activity
                least_active_broker = broker_id
        
        return least_active_broker or available_brokers[0], 0.8
    
    async def _select_liquidity_optimized_broker(self, order: Order, available_brokers: List[str]) -> Tuple[str, float]:
        """Select broker optimized for liquidity"""
        
        best_liquidity_broker = None
        best_liquidity_score = -1.0
        
        for broker_id in available_brokers:
            metrics = self.broker_metrics[broker_id]
            
            # Check symbol-specific liquidity
            symbol_liquidity = metrics.symbol_liquidity.get(order.symbol, 1.0)
            spread = metrics.best_bid_ask_spread.get(order.symbol, 0.01)
            
            # Calculate liquidity score
            liquidity_score = symbol_liquidity / max(spread, 0.001)
            
            if liquidity_score > best_liquidity_score:
                best_liquidity_score = liquidity_score
                best_liquidity_broker = broker_id
        
        return best_liquidity_broker or available_brokers[0], min(best_liquidity_score / 100, 1.0)
    
    async def _execute_failover(self, order: Order, original_decision: RoutingDecision) -> OrderResult:
        """Execute failover to alternative broker"""
        
        self.logger.warning(f"Executing failover for order {order.order_id}")
        
        for broker_id in original_decision.alternative_brokers:
            try:
                broker = self.brokers[broker_id]
                result = await broker.place_order(order)
                
                if result.success:
                    self.logger.info(f"Failover successful to broker {broker_id}")
                    
                    # Update routing decision
                    original_decision.selected_broker_id = broker_id
                    original_decision.primary_reason = f"Failover from {original_decision.selected_broker_id}"
                    
                    # Update metrics
                    await self._update_broker_metrics(broker_id, order, result)
                    
                    return result
                    
            except Exception as e:
                self.logger.warning(f"Failover to {broker_id} failed: {e}")
                continue
        
        # All failovers failed
        self.logger.error(f"All failover attempts failed for order {order.order_id}")
        
        return OrderResult(
            order_id=order.order_id,
            success=False,
            error_message="All brokers failed",
            timestamp=datetime.now()
        )
    
    async def _execute_advanced_failover(self, params: ExecutionParameters, 
                                       original_decision: RoutingDecision) -> ExecutionResult:
        """Execute advanced order failover"""
        
        self.logger.warning(f"Executing advanced failover for {params.symbol}")
        
        for broker_id in original_decision.alternative_brokers:
            try:
                advanced_manager = self.advanced_managers[broker_id]
                result = await advanced_manager.execute_order(params)
                
                if result.execution_status == OrderStatus.FILLED:
                    self.logger.info(f"Advanced failover successful to broker {broker_id}")
                    
                    # Update routing decision
                    original_decision.selected_broker_id = broker_id
                    original_decision.primary_reason = f"Advanced failover from {original_decision.selected_broker_id}"
                    
                    # Update metrics
                    await self._update_broker_metrics_advanced(broker_id, params, result)
                    
                    return result
                    
            except Exception as e:
                self.logger.warning(f"Advanced failover to {broker_id} failed: {e}")
                continue
        
        # All failovers failed
        self.logger.error(f"All advanced failover attempts failed for {params.symbol}")
        
        return ExecutionResult(
            order_id=params.symbol + "_" + str(uuid.uuid4().hex[:8]),
            algorithm=params.algorithm,
            execution_status=OrderStatus.REJECTED,
            total_quantity=params.quantity,
            filled_quantity=0.0,
            average_price=0.0,
            market_impact_bps=0.0,
            timing_cost_bps=0.0,
            total_cost_bps=0.0,
            execution_time_minutes=0.0,
            participation_rate=0.0,
            slippage_bps=0.0
        )
    
    async def _update_broker_metrics(self, broker_id: str, order: Order, result: OrderResult):
        """Update broker performance metrics"""
        
        if broker_id not in self.broker_metrics:
            return
        
        metrics = self.broker_metrics[broker_id]
        metrics.total_orders += 1
        
        if result.success:
            metrics.successful_orders += 1
        else:
            metrics.failed_orders += 1
            metrics.last_error = result.error_message
            metrics.last_error_time = datetime.now()
        
        # Update success rate
        metrics.success_rate = metrics.successful_orders / metrics.total_orders
        
        # Update volume
        if result.success and hasattr(result, 'filled_quantity'):
            metrics.total_volume_traded += result.filled_quantity
        
        # Update execution time
        if hasattr(result, 'execution_time'):
            metrics.average_execution_time = (
                (metrics.average_execution_time * (metrics.total_orders - 1) + result.execution_time) / 
                metrics.total_orders
            )
        
        metrics.updated_at = datetime.now()
    
    async def _update_broker_metrics_advanced(self, broker_id: str, params: ExecutionParameters, result: ExecutionResult):
        """Update broker metrics for advanced orders"""
        
        if broker_id not in self.broker_metrics:
            return
        
        metrics = self.broker_metrics[broker_id]
        metrics.total_orders += 1
        
        if result.execution_status == OrderStatus.FILLED:
            metrics.successful_orders += 1
            
            # Update advanced metrics
            metrics.average_market_impact_bps = (
                (metrics.average_market_impact_bps * (metrics.total_orders - 1) + result.market_impact_bps) / 
                metrics.total_orders
            )
            
            metrics.average_slippage_bps = (
                (metrics.average_slippage_bps * (metrics.total_orders - 1) + result.slippage_bps) / 
                metrics.total_orders
            )
            
            metrics.total_volume_traded += result.filled_quantity
            
        else:
            metrics.failed_orders += 1
            metrics.last_error = f"Advanced order failed: {result.execution_status.value}"
            metrics.last_error_time = datetime.now()
        
        # Update success rate
        metrics.success_rate = metrics.successful_orders / metrics.total_orders
        
        # Update execution time
        metrics.average_execution_time = (
            (metrics.average_execution_time * (metrics.total_orders - 1) + result.execution_time_minutes) / 
            metrics.total_orders
        )
        
        metrics.updated_at = datetime.now()
    
    async def get_consolidated_positions(self) -> Dict[str, Position]:
        """Get consolidated positions across all brokers"""
        
        consolidated = {}
        
        for broker_id, broker in self.brokers.items():
            try:
                positions = await broker.get_positions()
                self.cross_broker_positions[broker_id] = positions
                
                # Consolidate positions by symbol
                for symbol, position in positions.items():
                    if symbol in consolidated:
                        # Add to existing position
                        consolidated[symbol].quantity += position.quantity
                        consolidated[symbol].market_value += position.market_value
                        consolidated[symbol].unrealized_pnl += position.unrealized_pnl
                    else:
                        # Create new consolidated position
                        consolidated[symbol] = Position(
                            symbol=position.symbol,
                            quantity=position.quantity,
                            market_price=position.market_price,
                            market_value=position.market_value,
                            average_price=position.average_price,
                            unrealized_pnl=position.unrealized_pnl,
                            realized_pnl=position.realized_pnl,
                            broker_id=broker_id
                        )
                        
            except Exception as e:
                self.logger.warning(f"Failed to get positions from broker {broker_id}: {e}")
        
        return consolidated
    
    async def get_consolidated_account_summary(self) -> AccountSummary:
        """Get consolidated account summary across all brokers"""
        
        total_equity = 0.0
        total_buying_power = 0.0
        total_cash = 0.0
        
        for broker_id, broker in self.brokers.items():
            try:
                summary = await broker.get_account_summary()
                total_equity += summary.equity
                total_buying_power += summary.buying_power
                total_cash += summary.cash
                
            except Exception as e:
                self.logger.warning(f"Failed to get account summary from broker {broker_id}: {e}")
        
        return AccountSummary(
            equity=total_equity,
            buying_power=total_buying_power,
            cash=total_cash,
            timestamp=datetime.now()
        )
    
    def get_broker_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive broker performance report"""
        
        report = {
            'timestamp': datetime.now(),
            'total_brokers': len(self.brokers),
            'connected_brokers': len([b for b in self.broker_metrics.values() if b.status == BrokerStatus.CONNECTED]),
            'routing_strategy': self.routing_strategy.value,
            'brokers': {}
        }
        
        for broker_id, metrics in self.broker_metrics.items():
            report['brokers'][broker_id] = {
                'broker_type': metrics.broker_type.value,
                'status': metrics.status.value,
                'success_rate': metrics.success_rate,
                'total_orders': metrics.total_orders,
                'total_volume': metrics.total_volume_traded,
                'average_execution_time': metrics.average_execution_time,
                'average_market_impact': metrics.average_market_impact_bps,
                'average_slippage': metrics.average_slippage_bps,
                'total_commission': metrics.total_commission_paid,
                'uptime_hours': (datetime.now() - metrics.created_at).total_seconds() / 3600,
                'last_heartbeat': metrics.last_heartbeat.isoformat() if metrics.last_heartbeat else None,
                'last_error': metrics.last_error,
                'last_error_time': metrics.last_error_time.isoformat() if metrics.last_error_time else None
            }
        
        # Add routing statistics
        if self.routing_history:
            recent_routing = self.routing_history[-100:]  # Last 100 decisions
            
            strategy_counts = {}
            broker_counts = {}
            
            for decision in recent_routing:
                strategy = decision.routing_strategy.value
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
                
                broker = decision.selected_broker_id
                broker_counts[broker] = broker_counts.get(broker, 0) + 1
            
            report['routing_statistics'] = {
                'strategy_distribution': strategy_counts,
                'broker_distribution': broker_counts,
                'average_confidence': np.mean([d.confidence for d in recent_routing]),
                'total_decisions': len(recent_routing)
            }
        
        return report
    
    async def start_health_monitoring(self):
        """Start health monitoring for all brokers"""
        
        self.logger.info("Starting broker health monitoring")
        
        while True:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _perform_health_check(self):
        """Perform health check on all brokers"""
        
        self.last_health_check = datetime.now()
        
        for broker_id, broker in self.brokers.items():
            try:
                is_connected = await broker.is_connected()
                metrics = self.broker_metrics[broker_id]
                
                if is_connected:
                    metrics.status = BrokerStatus.CONNECTED
                    metrics.last_heartbeat = datetime.now()
                else:
                    metrics.status = BrokerStatus.DISCONNECTED
                    self.logger.warning(f"Broker {broker_id} health check failed")
                
                metrics.updated_at = datetime.now()
                
            except Exception as e:
                metrics = self.broker_metrics[broker_id]
                metrics.status = BrokerStatus.ERROR
                metrics.last_error = str(e)
                metrics.last_error_time = datetime.now()
                
                self.logger.error(f"Health check failed for broker {broker_id}: {e}")


# Factory function for creating multi-broker manager
def create_multi_broker_manager(primary_broker_id: str = "ibkr_primary") -> MultiBrokerManager:
    """Create a multi-broker manager instance"""
    return MultiBrokerManager(primary_broker_id)
