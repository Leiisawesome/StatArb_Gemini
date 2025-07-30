#!/usr/bin/env python3
"""
Smart Order Router
Phase 2: Core System Integration - Batch 2
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np

from .order_manager import OrderManager, Order, OrderType, OrderSide, OrderStatus

logger = logging.getLogger(__name__)

class ExecutionStrategy(Enum):
    """Execution strategies"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"  # Time-Weighted Average Price
    VWAP = "VWAP"  # Volume-Weighted Average Price
    ICEBERG = "ICEBERG"  # Iceberg orders
    POV = "POV"  # Percentage of Volume

class SmartOrderRouter:
    """Smart order routing system"""
    
    def __init__(self, order_manager: OrderManager):
        self.order_manager = order_manager
        self.execution_strategies = {}
        self.market_data = {}
        self.execution_analytics = {}
        
        # Execution parameters
        self.default_slippage = 0.001  # 0.1% default slippage
        self.max_order_size = 10000    # Maximum order size
        self.min_order_size = 100      # Minimum order size
        
        logger.info("Initialized SmartOrderRouter")
    
    def add_execution_strategy(self, strategy: ExecutionStrategy, config: Dict):
        """Add execution strategy configuration"""
        self.execution_strategies[strategy] = config
        logger.info(f"Added execution strategy: {strategy.value}")
    
    def update_market_data(self, symbol: str, data: Dict):
        """Update market data for routing decisions"""
        self.market_data[symbol] = data
        logger.debug(f"Updated market data for {symbol}")
    
    def route_order(self, symbol: str, side: OrderSide, quantity: int,
                   strategy: ExecutionStrategy = ExecutionStrategy.MARKET,
                   urgency: str = "NORMAL") -> Order:
        """Route order using smart execution strategy"""
        
        # Validate order parameters
        if quantity > self.max_order_size:
            logger.warning(f"Order size {quantity} exceeds maximum {self.max_order_size}")
            quantity = self.max_order_size
        
        if quantity < self.min_order_size:
            logger.warning(f"Order size {quantity} below minimum {self.min_order_size}")
            quantity = self.min_order_size
        
        # Get market data
        market_data = self.market_data.get(symbol, {})
        
        # Apply execution strategy
        if strategy == ExecutionStrategy.MARKET:
            return self._execute_market_order(symbol, side, quantity, urgency)
        elif strategy == ExecutionStrategy.LIMIT:
            return self._execute_limit_order(symbol, side, quantity, market_data)
        elif strategy == ExecutionStrategy.TWAP:
            return self._execute_twap_order(symbol, side, quantity, market_data)
        elif strategy == ExecutionStrategy.VWAP:
            return self._execute_vwap_order(symbol, side, quantity, market_data)
        else:
            logger.warning(f"Unknown strategy {strategy}, falling back to MARKET")
            return self._execute_market_order(symbol, side, quantity, urgency)
    
    def _execute_market_order(self, symbol: str, side: OrderSide, quantity: int, 
                            urgency: str) -> Order:
        """Execute market order with slippage adjustment"""
        
        # Get current market price
        market_price = self._get_market_price(symbol)
        if market_price is None:
            logger.error(f"No market price available for {symbol}")
            return None
        
        # Apply slippage based on urgency
        slippage_multiplier = {
            "HIGH": 2.0,
            "NORMAL": 1.0,
            "LOW": 0.5
        }.get(urgency, 1.0)
        
        slippage = self.default_slippage * slippage_multiplier
        
        # Adjust price for slippage
        if side == OrderSide.BUY:
            execution_price = market_price * (1 + slippage)
        else:
            execution_price = market_price * (1 - slippage)
        
        # Create and execute order
        order = self.order_manager.create_order(symbol, side, quantity, OrderType.MARKET)
        self.order_manager.submit_order(order.order_id)
        self.order_manager.execute_order(order.order_id, execution_price)
        
        logger.info(f"Executed market order: {side.value} {quantity} {symbol} @ ${execution_price:.2f}")
        return order
    
    def _execute_limit_order(self, symbol: str, side: OrderSide, quantity: int,
                           market_data: Dict) -> Order:
        """Execute limit order with smart pricing"""
        
        market_price = self._get_market_price(symbol)
        if market_price is None:
            logger.error(f"No market price available for {symbol}")
            return None
        
        # Calculate limit price based on market conditions
        spread = market_data.get('spread', 0.001)  # 0.1% default spread
        
        if side == OrderSide.BUY:
            limit_price = market_price * (1 - spread/2)  # Buy at bid
        else:
            limit_price = market_price * (1 + spread/2)  # Sell at ask
        
        # Create limit order
        order = self.order_manager.create_order(symbol, side, quantity, 
                                               OrderType.LIMIT, limit_price)
        self.order_manager.submit_order(order.order_id)
        
        logger.info(f"Created limit order: {side.value} {quantity} {symbol} @ ${limit_price:.2f}")
        return order
    
    def _execute_twap_order(self, symbol: str, side: OrderSide, quantity: int,
                          market_data: Dict) -> Order:
        """Execute TWAP (Time-Weighted Average Price) order"""
        
        # TWAP implementation - split order over time
        num_slices = 4  # Split into 4 slices
        slice_quantity = quantity // num_slices
        remaining_quantity = quantity % num_slices
        
        orders = []
        
        for i in range(num_slices):
            current_quantity = slice_quantity + (remaining_quantity if i == 0 else 0)
            if current_quantity <= 0:
                continue
            
            # Execute slice
            order = self._execute_market_order(symbol, side, current_quantity, "LOW")
            if order:
                orders.append(order)
        
        logger.info(f"Executed TWAP order: {side.value} {quantity} {symbol} in {len(orders)} slices")
        return orders[0] if orders else None
    
    def _execute_vwap_order(self, symbol: str, side: OrderSide, quantity: int,
                          market_data: Dict) -> Order:
        """Execute VWAP (Volume-Weighted Average Price) order"""
        
        # VWAP implementation - execute based on volume profile
        avg_volume = market_data.get('avg_volume', 1000)
        current_volume = market_data.get('volume', avg_volume)
        
        # Adjust order size based on volume
        volume_ratio = current_volume / avg_volume
        adjusted_quantity = int(quantity * min(volume_ratio, 2.0))  # Cap at 2x
        
        # Execute as market order
        order = self._execute_market_order(symbol, side, adjusted_quantity, "NORMAL")
        
        logger.info(f"Executed VWAP order: {side.value} {adjusted_quantity} {symbol} "
                   f"(volume ratio: {volume_ratio:.2f})")
        return order
    
    def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for symbol"""
        market_data = self.market_data.get(symbol, {})
        return market_data.get('close') or market_data.get('price')
    
    def get_execution_analytics(self) -> Dict:
        """Get execution analytics"""
        filled_orders = self.order_manager.get_filled_orders()
        
        if not filled_orders:
            return {
                'total_orders': 0,
                'total_volume': 0,
                'avg_execution_time': 0,
                'avg_slippage': 0,
                'execution_quality': 0
            }
        
        # Calculate analytics
        total_volume = sum(order.filled_quantity for order in filled_orders)
        execution_times = []
        slippages = []
        
        for order in filled_orders:
            if order.fills:
                # Execution time
                exec_time = (order.fills[-1]['timestamp'] - order.created_at).total_seconds()
                execution_times.append(exec_time)
                
                # Slippage (simplified calculation)
                if order.side == OrderSide.BUY:
                    slippage = (order.avg_fill_price - self._get_market_price(order.symbol)) / self._get_market_price(order.symbol)
                else:
                    slippage = (self._get_market_price(order.symbol) - order.avg_fill_price) / self._get_market_price(order.symbol)
                slippages.append(abs(slippage))
        
        return {
            'total_orders': len(filled_orders),
            'total_volume': total_volume,
            'avg_execution_time': np.mean(execution_times) if execution_times else 0,
            'avg_slippage': np.mean(slippages) if slippages else 0,
            'execution_quality': 1.0 - (np.mean(slippages) if slippages else 0)
        } 