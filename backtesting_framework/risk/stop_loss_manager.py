#!/usr/bin/env python3
"""
Stop-Loss and Take-Profit Management
Phase 2: Core System Integration - Batch 4
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class StopLossOrder:
    """Stop-loss order object"""
    
    def __init__(self, symbol: str, quantity: int, stop_price: float, 
                 order_type: str = "STOP_LOSS", trailing: bool = False):
        self.symbol = symbol
        self.quantity = quantity
        self.stop_price = stop_price
        self.order_type = order_type
        self.trailing = trailing
        self.triggered = False
        self.created_at = datetime.now()
        self.triggered_at = None
        
        logger.debug(f"Created {order_type} order for {symbol}: {quantity} @ ${stop_price:.2f}")

class TakeProfitOrder:
    """Take-profit order object"""
    
    def __init__(self, symbol: str, quantity: int, target_price: float):
        self.symbol = symbol
        self.quantity = quantity
        self.target_price = target_price
        self.triggered = False
        self.created_at = datetime.now()
        self.triggered_at = None
        
        logger.debug(f"Created take-profit order for {symbol}: {quantity} @ ${target_price:.2f}")

class StopLossManager:
    """Stop-loss and take-profit management system"""
    
    def __init__(self):
        self.stop_loss_orders = {}
        self.take_profit_orders = {}
        self.trailing_stops = {}
        self.execution_callbacks = []
        
        # Default settings
        self.default_stop_loss_pct = 0.05  # 5% stop-loss
        self.default_take_profit_pct = 0.10  # 10% take-profit
        self.default_trailing_stop_pct = 0.03  # 3% trailing stop
        
        logger.info("Initialized StopLossManager")
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for order execution events"""
        self.execution_callbacks.append(callback)
        logger.info(f"Added execution callback: {callback.__name__}")
    
    def create_stop_loss(self, symbol: str, quantity: int, avg_price: float,
                        stop_loss_pct: float = None) -> StopLossOrder:
        """Create stop-loss order"""
        
        stop_pct = stop_loss_pct or self.default_stop_loss_pct
        stop_price = avg_price * (1 - stop_pct)
        
        stop_order = StopLossOrder(symbol, quantity, stop_price, "STOP_LOSS")
        self.stop_loss_orders[symbol] = stop_order
        
        logger.info(f"Created stop-loss for {symbol}: {quantity} @ ${stop_price:.2f} ({stop_pct:.1%})")
        return stop_order
    
    def create_take_profit(self, symbol: str, quantity: int, avg_price: float,
                          take_profit_pct: float = None) -> TakeProfitOrder:
        """Create take-profit order"""
        
        profit_pct = take_profit_pct or self.default_take_profit_pct
        target_price = avg_price * (1 + profit_pct)
        
        profit_order = TakeProfitOrder(symbol, quantity, target_price)
        self.take_profit_orders[symbol] = profit_order
        
        logger.info(f"Created take-profit for {symbol}: {quantity} @ ${target_price:.2f} ({profit_pct:.1%})")
        return profit_order
    
    def create_trailing_stop(self, symbol: str, quantity: int, current_price: float,
                           trailing_pct: float = None) -> StopLossOrder:
        """Create trailing stop order"""
        
        trail_pct = trailing_pct or self.default_trailing_stop_pct
        stop_price = current_price * (1 - trail_pct)
        
        trailing_order = StopLossOrder(symbol, quantity, stop_price, "TRAILING_STOP", trailing=True)
        self.trailing_stops[symbol] = trailing_order
        
        logger.info(f"Created trailing stop for {symbol}: {quantity} @ ${stop_price:.2f} ({trail_pct:.1%})")
        return trailing_order
    
    def update_prices(self, market_data: Dict[str, float]):
        """Update stop-loss and take-profit orders with current prices"""
        
        triggered_orders = []
        
        for symbol, current_price in market_data.items():
            # Check stop-loss orders
            if symbol in self.stop_loss_orders:
                stop_order = self.stop_loss_orders[symbol]
                if not stop_order.triggered and current_price <= stop_order.stop_price:
                    stop_order.triggered = True
                    stop_order.triggered_at = datetime.now()
                    triggered_orders.append(('STOP_LOSS', symbol, stop_order))
                    logger.warning(f"Stop-loss triggered for {symbol} @ ${current_price:.2f}")
            
            # Check take-profit orders
            if symbol in self.take_profit_orders:
                profit_order = self.take_profit_orders[symbol]
                if not profit_order.triggered and current_price >= profit_order.target_price:
                    profit_order.triggered = True
                    profit_order.triggered_at = datetime.now()
                    triggered_orders.append(('TAKE_PROFIT', symbol, profit_order))
                    logger.info(f"Take-profit triggered for {symbol} @ ${current_price:.2f}")
            
            # Update trailing stops
            if symbol in self.trailing_stops:
                trailing_order = self.trailing_stops[symbol]
                new_stop_price = current_price * (1 - self.default_trailing_stop_pct)
                
                # Only move stop price up (for long positions)
                if new_stop_price > trailing_order.stop_price:
                    trailing_order.stop_price = new_stop_price
                    logger.debug(f"Updated trailing stop for {symbol}: ${new_stop_price:.2f}")
                
                # Check if trailing stop is triggered
                if not trailing_order.triggered and current_price <= trailing_order.stop_price:
                    trailing_order.triggered = True
                    trailing_order.triggered_at = datetime.now()
                    triggered_orders.append(('TRAILING_STOP', symbol, trailing_order))
                    logger.warning(f"Trailing stop triggered for {symbol} @ ${current_price:.2f}")
        
        # Execute triggered orders
        for order_type, symbol, order in triggered_orders:
            self._execute_order(order_type, symbol, order, market_data.get(symbol, 0))
        
        return triggered_orders
    
    def _execute_order(self, order_type: str, symbol: str, order, execution_price: float):
        """Execute triggered order"""
        
        execution_info = {
            'order_type': order_type,
            'symbol': symbol,
            'quantity': order.quantity,
            'execution_price': execution_price,
            'timestamp': datetime.now()
        }
        
        # Notify callbacks
        for callback in self.execution_callbacks:
            try:
                callback(execution_info)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        logger.info(f"Executed {order_type} for {symbol}: {order.quantity} @ ${execution_price:.2f}")
    
    def cancel_order(self, symbol: str, order_type: str = "ALL"):
        """Cancel stop-loss or take-profit order"""
        
        if order_type in ["STOP_LOSS", "ALL"] and symbol in self.stop_loss_orders:
            del self.stop_loss_orders[symbol]
            logger.info(f"Cancelled stop-loss for {symbol}")
        
        if order_type in ["TAKE_PROFIT", "ALL"] and symbol in self.take_profit_orders:
            del self.take_profit_orders[symbol]
            logger.info(f"Cancelled take-profit for {symbol}")
        
        if order_type in ["TRAILING_STOP", "ALL"] and symbol in self.trailing_stops:
            del self.trailing_stops[symbol]
            logger.info(f"Cancelled trailing stop for {symbol}")
    
    def get_active_orders(self) -> Dict:
        """Get all active orders"""
        return {
            'stop_loss': {symbol: order for symbol, order in self.stop_loss_orders.items() if not order.triggered},
            'take_profit': {symbol: order for symbol, order in self.take_profit_orders.items() if not order.triggered},
            'trailing_stops': {symbol: order for symbol, order in self.trailing_stops.items() if not order.triggered}
        }
    
    def get_triggered_orders(self) -> Dict:
        """Get all triggered orders"""
        return {
            'stop_loss': {symbol: order for symbol, order in self.stop_loss_orders.items() if order.triggered},
            'take_profit': {symbol: order for symbol, order in self.take_profit_orders.items() if order.triggered},
            'trailing_stops': {symbol: order for symbol, order in self.trailing_stops.items() if order.triggered}
        }
    
    def get_summary(self) -> Dict:
        """Get stop-loss manager summary"""
        active_orders = self.get_active_orders()
        triggered_orders = self.get_triggered_orders()
        
        return {
            'active_stop_loss': len(active_orders['stop_loss']),
            'active_take_profit': len(active_orders['take_profit']),
            'active_trailing_stops': len(active_orders['trailing_stops']),
            'triggered_stop_loss': len(triggered_orders['stop_loss']),
            'triggered_take_profit': len(triggered_orders['take_profit']),
            'triggered_trailing_stops': len(triggered_orders['trailing_stops']),
            'execution_callbacks': len(self.execution_callbacks)
        } 