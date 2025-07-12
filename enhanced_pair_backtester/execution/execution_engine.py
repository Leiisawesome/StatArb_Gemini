"""
Trade Execution Engine

Professional-grade execution engine that integrates:
- Market impact modeling
- Order management
- Position tracking
- Risk management
- Execution quality metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging

from .market_impact import MarketImpactModel, MarketConditions, TransactionCosts, estimate_market_conditions
from .order_management import OrderManager, Order, OrderType, OrderSide, OrderStatus, Fill, Position


class ExecutionStatus(Enum):
    """Execution status for trade requests"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    REJECTED = "rejected"


@dataclass
class TradeRequest:
    """Trade request from strategy"""
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str = "market"
    price: Optional[float] = None
    strategy_id: str = "pairs_trading"
    notes: str = ""


@dataclass
class Trade:
    """Completed trade record"""
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    transaction_costs: TransactionCosts
    market_conditions: MarketConditions
    execution_quality: float = 0.0  # 0-100 quality score
    
    @property
    def notional_value(self) -> float:
        """Notional value of the trade"""
        return abs(self.quantity * self.price)
    
    @property
    def total_cost(self) -> float:
        """Total cost including transaction costs"""
        return self.transaction_costs.total_cost


@dataclass
class ExecutionResult:
    """Result of trade execution attempt"""
    status: ExecutionStatus
    trades: List[Trade] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    error_message: str = ""
    execution_time: float = 0.0
    
    @property
    def total_quantity_filled(self) -> float:
        """Total quantity filled across all trades"""
        return sum(trade.quantity for trade in self.trades)
    
    @property
    def average_execution_price(self) -> float:
        """Volume-weighted average execution price"""
        if not self.trades:
            return 0.0
        
        total_value = sum(trade.quantity * trade.price for trade in self.trades)
        total_quantity = sum(trade.quantity for trade in self.trades)
        
        return total_value / total_quantity if total_quantity > 0 else 0.0
    
    @property
    def total_transaction_costs(self) -> float:
        """Total transaction costs across all trades"""
        return sum(trade.transaction_costs.total_cost for trade in self.trades)


class ExecutionEngine:
    """
    Professional trade execution engine for pairs trading
    
    Features:
    - Realistic market impact modeling
    - Order management and tracking
    - Risk controls and validation
    - Execution quality measurement
    - Performance analytics
    """
    
    def __init__(self, 
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.001,
                 max_order_value: float = 100000,
                 max_position_value: float = 500000,
                 risk_check_enabled: bool = True):
        """
        Initialize execution engine
        
        Args:
            initial_capital: Starting capital
            commission_rate: Commission rate (fraction of trade value)
            max_order_value: Maximum order value for risk checks
            max_position_value: Maximum position value for risk checks
            risk_check_enabled: Whether to perform risk checks
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Initialize components
        self.market_impact_model = MarketImpactModel(commission_rate=commission_rate)
        self.order_manager = OrderManager(
            max_order_value=max_order_value,
            max_position_value=max_position_value,
            risk_check_enabled=risk_check_enabled
        )
        
        # Execution tracking
        self.executed_trades: List[Trade] = []
        self.execution_history: List[ExecutionResult] = []
        
        # Performance metrics
        self.total_pnl = 0.0
        self.total_commission = 0.0
        self.execution_quality_scores: List[float] = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def execute_trade(self, 
                     trade_request: TradeRequest,
                     current_prices: Dict[str, float],
                     market_data: Dict[str, pd.DataFrame]) -> ExecutionResult:
        """
        Execute a trade request
        
        Args:
            trade_request: Trade request from strategy
            current_prices: Current market prices
            market_data: Historical market data for impact estimation
            
        Returns:
            ExecutionResult with execution details
        """
        start_time = datetime.now()
        
        try:
            # Validate trade request
            if not self._validate_trade_request(trade_request, current_prices):
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    error_message="Trade request validation failed"
                )
            
            # Get current market conditions
            market_conditions = self._get_market_conditions(
                trade_request.symbol, market_data
            )
            
            # Create and submit order
            order = self._create_order(trade_request, current_prices[trade_request.symbol])
            
            if not self.order_manager.submit_order(order):
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    orders=[order],
                    error_message=f"Order submission failed: {order.notes}"
                )
            
            # Execute order (simulate market execution)
            execution_result = self._execute_order(
                order, current_prices[trade_request.symbol], market_conditions, market_data
            )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            execution_result.execution_time = execution_time
            
            # Store execution history
            self.execution_history.append(execution_result)
            
            # Update performance metrics
            self._update_performance_metrics(execution_result)
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {str(e)}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error_message=f"Execution error: {str(e)}"
            )
    
    def execute_pair_trade(self,
                          symbol1: str,
                          symbol2: str,
                          quantities: Tuple[float, float],
                          current_prices: Dict[str, float],
                          market_data: Dict[str, pd.DataFrame]) -> List[ExecutionResult]:
        """
        Execute a pairs trade (both legs simultaneously)
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            quantities: Quantities for each symbol (positive=buy, negative=sell)
            current_prices: Current market prices
            market_data: Historical market data
            
        Returns:
            List of ExecutionResult for each leg
        """
        results = []
        
        # Execute first leg
        if quantities[0] != 0:
            trade_request1 = TradeRequest(
                symbol=symbol1,
                side="buy" if quantities[0] > 0 else "sell",
                quantity=abs(quantities[0]),
                strategy_id="pairs_trading"
            )
            results.append(self.execute_trade(trade_request1, current_prices, market_data))
        
        # Execute second leg
        if quantities[1] != 0:
            trade_request2 = TradeRequest(
                symbol=symbol2,
                side="buy" if quantities[1] > 0 else "sell",
                quantity=abs(quantities[1]),
                strategy_id="pairs_trading"
            )
            results.append(self.execute_trade(trade_request2, current_prices, market_data))
        
        return results
    
    def get_current_positions(self) -> Dict[str, Position]:
        """
        Get current positions across all symbols
        
        Returns:
            Dictionary of symbol -> Position
        """
        return {symbol: pos for symbol, pos in self.order_manager.positions.items() 
                if pos.quantity != 0}
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate current portfolio value
        
        Args:
            current_prices: Current market prices
            
        Returns:
            Total portfolio value
        """
        positions = self.get_current_positions()
        position_value = 0.0
        
        for symbol, position in positions.items():
            if symbol in current_prices:
                position.market_value = position.quantity * current_prices[symbol]
                position.unrealized_pnl = (
                    position.market_value - position.quantity * position.average_price
                )
                position_value += position.market_value
        
        return self.current_capital + position_value
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive execution summary
        
        Returns:
            Dictionary with execution metrics
        """
        order_summary = self.order_manager.get_performance_summary()
        
        total_trades = len(self.executed_trades)
        total_notional = sum(trade.notional_value for trade in self.executed_trades)
        
        avg_execution_quality = (
            np.mean(self.execution_quality_scores) if self.execution_quality_scores else 0.0
        )
        
        return {
            # Order management metrics
            **order_summary,
            
            # Trade execution metrics
            'total_trades': total_trades,
            'total_notional_value': total_notional,
            'total_pnl': self.total_pnl,
            'total_commission': self.total_commission,
            'avg_execution_quality': avg_execution_quality,
            
            # Portfolio metrics
            'current_capital': self.current_capital,
            'active_positions': len(self.get_current_positions()),
            
            # Execution history
            'successful_executions': len([r for r in self.execution_history 
                                        if r.status == ExecutionStatus.SUCCESS]),
            'failed_executions': len([r for r in self.execution_history 
                                    if r.status == ExecutionStatus.FAILED]),
            'rejected_executions': len([r for r in self.execution_history 
                                      if r.status == ExecutionStatus.REJECTED])
        }
    
    def _validate_trade_request(self, 
                               trade_request: TradeRequest,
                               current_prices: Dict[str, float]) -> bool:
        """
        Validate trade request before execution
        
        Args:
            trade_request: Trade request to validate
            current_prices: Current market prices
            
        Returns:
            True if valid, False otherwise
        """
        # Check if symbol exists in current prices
        if trade_request.symbol not in current_prices:
            self.logger.warning(f"Symbol {trade_request.symbol} not found in current prices")
            return False
        
        # Check quantity
        if trade_request.quantity <= 0:
            self.logger.warning(f"Invalid quantity: {trade_request.quantity}")
            return False
        
        # Check side
        if trade_request.side not in ['buy', 'sell']:
            self.logger.warning(f"Invalid side: {trade_request.side}")
            return False
        
        # Check order type
        if trade_request.order_type not in ['market', 'limit']:
            self.logger.warning(f"Invalid order type: {trade_request.order_type}")
            return False
        
        return True
    
    def _create_order(self, trade_request: TradeRequest, current_price: float) -> Order:
        """
        Create order from trade request
        
        Args:
            trade_request: Trade request
            current_price: Current market price
            
        Returns:
            Order object
        """
        order_side = OrderSide.BUY if trade_request.side == 'buy' else OrderSide.SELL
        order_type = OrderType.MARKET if trade_request.order_type == 'market' else OrderType.LIMIT
        
        price = trade_request.price if trade_request.order_type == 'limit' else current_price
        
        return self.order_manager.create_order(
            symbol=trade_request.symbol,
            side=order_side,
            quantity=trade_request.quantity,
            order_type=order_type,
            price=price,
            strategy_id=trade_request.strategy_id
        )
    
    def _execute_order(self,
                      order: Order,
                      current_price: float,
                      market_conditions: MarketConditions,
                      market_data: Dict[str, pd.DataFrame]) -> ExecutionResult:
        """
        Execute order with realistic market impact
        
        Args:
            order: Order to execute
            current_price: Current market price
            market_conditions: Market conditions
            market_data: Historical market data
            
        Returns:
            ExecutionResult
        """
        try:
            # Calculate order value
            order_value = order.quantity * current_price
            if order.side == OrderSide.SELL:
                order_value = -order_value
            
            # Estimate execution price and costs
            execution_price, transaction_costs = self.market_impact_model.estimate_execution_price(
                order_value=order_value,
                current_price=current_price,
                market_conditions=market_conditions,
                average_volume=market_conditions.volume
            )
            
            # Fill the order
            fill = self.order_manager.fill_order(
                order_id=order.order_id,
                fill_quantity=order.quantity,
                fill_price=execution_price,
                commission=transaction_costs.commission
            )
            
            if fill is None:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    orders=[order],
                    error_message="Order fill failed"
                )
            
            # Calculate execution quality
            execution_quality = self._calculate_execution_quality(
                order, execution_price, current_price, market_conditions
            )
            
            # Create trade record
            trade = Trade(
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=execution_price,
                timestamp=datetime.now(),
                transaction_costs=transaction_costs,
                market_conditions=market_conditions,
                execution_quality=execution_quality
            )
            
            self.executed_trades.append(trade)
            
            # Update capital
            trade_pnl = self._calculate_trade_pnl(trade)
            self.current_capital += trade_pnl - transaction_costs.total_cost
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                trades=[trade],
                orders=[order]
            )
            
        except Exception as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                orders=[order],
                error_message=f"Execution failed: {str(e)}"
            )
    
    def _get_market_conditions(self, 
                              symbol: str,
                              market_data: Dict[str, pd.DataFrame]) -> MarketConditions:
        """
        Get current market conditions for a symbol
        
        Args:
            symbol: Trading symbol
            market_data: Historical market data
            
        Returns:
            MarketConditions object
        """
        if symbol in market_data:
            return estimate_market_conditions(market_data[symbol])
        else:
            # Default market conditions if no data available
            return MarketConditions(
                volatility=0.02,  # 2% daily volatility
                volume=1000000,   # $1M daily volume
                spread=0.001      # 10 bps spread
            )
    
    def _calculate_execution_quality(self,
                                   order: Order,
                                   execution_price: float,
                                   benchmark_price: float,
                                   market_conditions: MarketConditions) -> float:
        """
        Calculate execution quality score (0-100)
        
        Args:
            order: Executed order
            execution_price: Actual execution price
            benchmark_price: Benchmark price (e.g., arrival price)
            market_conditions: Market conditions
            
        Returns:
            Quality score (0-100, higher is better)
        """
        # Calculate price improvement/degradation
        if order.side == OrderSide.BUY:
            price_impact = (execution_price - benchmark_price) / benchmark_price
        else:
            price_impact = (benchmark_price - execution_price) / benchmark_price
        
        # Base quality score (starts at 100)
        quality_score = 100.0
        
        # Penalize for price impact
        impact_penalty = abs(price_impact) * 10000  # 100 points per 1% impact
        quality_score -= impact_penalty
        
        # Adjust for market conditions
        if market_conditions.regime.value == "volatile":
            quality_score += 10  # Bonus for executing in volatile conditions
        elif market_conditions.regime.value == "stressed":
            quality_score += 20  # Larger bonus for stressed conditions
        
        return max(0.0, min(100.0, quality_score))
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """
        Calculate immediate P&L from trade (for position updates)
        
        Args:
            trade: Trade to calculate P&L for
            
        Returns:
            Trade P&L
        """
        # For now, return 0 as P&L is realized when position is closed
        # This could be enhanced to include mark-to-market P&L
        return 0.0
    
    def _update_performance_metrics(self, execution_result: ExecutionResult):
        """
        Update performance metrics after execution
        
        Args:
            execution_result: Execution result to process
        """
        if execution_result.status == ExecutionStatus.SUCCESS:
            for trade in execution_result.trades:
                self.total_commission += trade.transaction_costs.commission
                self.execution_quality_scores.append(trade.execution_quality) 