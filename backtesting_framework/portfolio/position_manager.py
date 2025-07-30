#!/usr/bin/env python3
"""
Portfolio Position Manager
Phase 2: Core System Integration - Batch 3
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class Position:
    """Position object for tracking individual symbol positions"""
    
    def __init__(self, symbol: str, quantity: int = 0, avg_price: float = 0.0):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_pnl = 0.0
        self.market_value = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.trades = []
        
        logger.debug(f"Created position for {symbol}: {quantity} shares @ ${avg_price:.2f}")
    
    def update_position(self, trade_quantity: int, trade_price: float, trade_type: str):
        """Update position with new trade"""
        old_quantity = self.quantity
        old_avg_price = self.avg_price
        
        if trade_type == "BUY":
            # Add to position
            if self.quantity == 0:
                self.avg_price = trade_price
            else:
                # Calculate new average price
                total_cost = (self.quantity * self.avg_price) + (trade_quantity * trade_price)
                self.quantity += trade_quantity
                self.avg_price = total_cost / self.quantity
        else:
            # Sell from position
            if trade_quantity > self.quantity:
                logger.warning(f"Attempting to sell {trade_quantity} shares but only have {self.quantity}")
                trade_quantity = self.quantity
            
            # Calculate realized P&L
            realized_pnl = (trade_price - self.avg_price) * trade_quantity
            self.realized_pnl += realized_pnl
            
            # Update position
            self.quantity -= trade_quantity
            if self.quantity == 0:
                self.avg_price = 0.0
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'type': trade_type,
            'quantity': trade_quantity,
            'price': trade_price,
            'realized_pnl': self.realized_pnl
        }
        self.trades.append(trade)
        
        self.updated_at = datetime.now()
        
        logger.info(f"Updated {self.symbol} position: {old_quantity}→{self.quantity} shares, "
                   f"${old_avg_price:.2f}→${self.avg_price:.2f}, P&L: ${self.realized_pnl:.2f}")
    
    def update_market_value(self, current_price: float):
        """Update market value and unrealized P&L"""
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = (current_price - self.avg_price) * self.quantity
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        self.updated_at = datetime.now()

class PortfolioManager:
    """Portfolio management system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.positions = {}
        self.portfolio_callbacks = []
        self.rebalancing_callbacks = []
        
        # Portfolio tracking
        self.total_market_value = 0.0
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_pnl = 0.0
        self.portfolio_history = []
        
        logger.info(f"Initialized PortfolioManager with ${initial_capital:,.2f} capital")
    
    def add_portfolio_callback(self, callback: Callable):
        """Add callback for portfolio events"""
        self.portfolio_callbacks.append(callback)
        logger.info(f"Added portfolio callback: {callback.__name__}")
    
    def add_rebalancing_callback(self, callback: Callable):
        """Add callback for rebalancing events"""
        self.rebalancing_callbacks.append(callback)
        logger.info(f"Added rebalancing callback: {callback.__name__}")
    
    def process_trade(self, symbol: str, quantity: int, price: float, trade_type: str):
        """Process a trade and update portfolio"""
        
        # Update or create position
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        position = self.positions[symbol]
        position.update_position(quantity, price, trade_type)
        
        # Update capital
        trade_value = quantity * price
        if trade_type == "BUY":
            self.available_capital -= trade_value
        else:
            self.available_capital += trade_value
        
        # Update market value
        position.update_market_value(price)
        
        # Update portfolio totals
        self._update_portfolio_totals()
        
        # Record portfolio state
        self._record_portfolio_state()
        
        # Notify callbacks
        for callback in self.portfolio_callbacks:
            try:
                callback(symbol, position, trade_type)
            except Exception as e:
                logger.error(f"Portfolio callback error: {e}")
        
        logger.info(f"Processed {trade_type} trade: {quantity} {symbol} @ ${price:.2f}")
    
    def update_market_prices(self, market_data: Dict[str, float]):
        """Update portfolio with current market prices"""
        for symbol, price in market_data.items():
            if symbol in self.positions:
                self.positions[symbol].update_market_value(price)
        
        # Update portfolio totals
        self._update_portfolio_totals()
        
        # Record portfolio state
        self._record_portfolio_state()
        
        logger.debug(f"Updated market prices for {len(market_data)} symbols")
    
    def _update_portfolio_totals(self):
        """Update portfolio totals"""
        self.total_market_value = sum(pos.market_value for pos in self.positions.values())
        self.total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        self.total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.total_pnl = self.total_realized_pnl + self.total_unrealized_pnl
    
    def _record_portfolio_state(self):
        """Record current portfolio state"""
        state = {
            'timestamp': datetime.now(),
            'total_market_value': self.total_market_value,
            'available_capital': self.available_capital,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'positions_count': len(self.positions)
        }
        self.portfolio_history.append(state)
        
        # Keep only last 1000 records
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-1000:]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_value = self.total_market_value + self.available_capital
        
        return {
            'initial_capital': self.initial_capital,
            'available_capital': self.available_capital,
            'total_market_value': self.total_market_value,
            'total_portfolio_value': total_value,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'total_return': (total_value - self.initial_capital) / self.initial_capital,
            'positions_count': len(self.positions),
            'portfolio_callbacks': len(self.portfolio_callbacks),
            'rebalancing_callbacks': len(self.rebalancing_callbacks)
        }
    
    def get_position_weights(self) -> Dict[str, float]:
        """Get position weights as percentage of total portfolio"""
        total_value = self.total_market_value + self.available_capital
        if total_value == 0:
            return {}
        
        weights = {}
        for symbol, position in self.positions.items():
            weights[symbol] = position.market_value / total_value
        
        return weights
    
    def get_portfolio_history(self, lookback_periods: int = 100) -> pd.DataFrame:
        """Get portfolio history as DataFrame"""
        if not self.portfolio_history:
            return pd.DataFrame()
        
        history = self.portfolio_history[-lookback_periods:]
        df = pd.DataFrame(history)
        df.set_index('timestamp', inplace=True)
        return df 