"""
Core Portfolio Management System
===============================

Professional portfolio management system consolidating all portfolio functionality.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class PositionMetrics:
    """Position-level metrics"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    market_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    weight: float
    return_pct: float
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioMetrics:
    """Portfolio-level metrics"""
    total_market_value: float
    available_capital: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_pnl: float
    total_return_pct: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    position_count: int
    timestamp: datetime = field(default_factory=datetime.now)

class Position:
    """Portfolio management position with full trade history and methods
    
    Note: This is a specialized position class for portfolio management
    with trade tracking and position methods. For canonical position representation,
    see infrastructure/types/strategy_types.py
    """
    
    def __init__(self, symbol: str, quantity: int = 0, avg_price: float = 0.0, entry_slice: int = -1, created_at: datetime = None):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.total_pnl = 0.0
        self.market_value = 0.0
        self.created_at = created_at if created_at is not None else datetime.now()
        self.updated_at = datetime.now()
        self.trades = []
        self.entry_slice = entry_slice  # Track which slice this position was opened in
        
        logger.debug(f"Created position for {symbol}: {quantity} shares @ ${avg_price:.2f} at {self.created_at}")
    
    def update_position(self, trade_quantity: int, trade_price: float, trade_type: str):
        """Update position with new trade"""
        old_quantity = self.quantity
        old_avg_price = self.avg_price
        
        if trade_type == "BUY":
            # Add to position
            if self.quantity == 0:
                self.quantity = trade_quantity
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
    
    def get_metrics(self, current_price: float, portfolio_value: float) -> PositionMetrics:
        """Get position metrics"""
        self.update_market_value(current_price)
        
        weight = self.market_value / portfolio_value if portfolio_value > 0 else 0.0
        return_pct = (current_price - self.avg_price) / self.avg_price if self.avg_price > 0 else 0.0
        
        return PositionMetrics(
            symbol=self.symbol,
            quantity=self.quantity,
            avg_price=self.avg_price,
            current_price=current_price,
            market_value=self.market_value,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            total_pnl=self.total_pnl,
            weight=weight,
            return_pct=return_pct,
                         created_at=self.created_at,
             updated_at=self.updated_at
         )

class PnLTracker:
    """Profit and Loss tracking system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.pnl_history = []
        self.daily_pnl = {}
        self.position_pnl = {}
        
        # P&L metrics
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        logger.info(f"Initialized PnLTracker with ${initial_capital:,.2f} initial capital")
    
    def update_pnl(self, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0,
                  symbol: str = None, position_pnl: float = 0.0):
        """Update P&L with new values"""
        
        # Update totals
        self.total_realized_pnl += realized_pnl
        self.total_unrealized_pnl = unrealized_pnl
        self.total_pnl = self.total_realized_pnl + self.total_unrealized_pnl
        
        # Update current capital
        self.current_capital = self.initial_capital + self.total_pnl
        
        # Update peak capital and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Record P&L entry
        pnl_entry = {
            'timestamp': datetime.now(),
            'realized_pnl': self.total_realized_pnl,
            'unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'current_capital': self.current_capital,
            'drawdown': current_drawdown,
            'symbol': symbol,
            'position_pnl': position_pnl
        }
        self.pnl_history.append(pnl_entry)
        
        # Update daily P&L
        today = datetime.now().date()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = {
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'total_pnl': 0.0,
                'trades_count': 0
            }
        
        self.daily_pnl[today]['realized_pnl'] += realized_pnl
        self.daily_pnl[today]['unrealized_pnl'] = unrealized_pnl
        self.daily_pnl[today]['total_pnl'] = self.daily_pnl[today]['realized_pnl'] + self.daily_pnl[today]['unrealized_pnl']
        if realized_pnl != 0:
            self.daily_pnl[today]['trades_count'] += 1
        
        # Update position P&L
        if symbol:
            if symbol not in self.position_pnl:
                self.position_pnl[symbol] = {
                    'total_pnl': 0.0,
                    'trades_count': 0,
                    'last_update': datetime.now()
                }
            self.position_pnl[symbol]['total_pnl'] += position_pnl
            self.position_pnl[symbol]['trades_count'] += 1
            self.position_pnl[symbol]['last_update'] = datetime.now()
        
        # Keep only last 1000 records
        if len(self.pnl_history) > 1000:
            self.pnl_history = self.pnl_history[-1000:]
        
        logger.debug(f"Updated P&L: Realized=${self.total_realized_pnl:.2f}, "
                    f"Unrealized=${self.total_unrealized_pnl:.2f}, "
                    f"Total=${self.total_pnl:.2f}")
    
    def get_pnl_summary(self) -> Dict:
        """Get P&L summary"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'total_return_pct': (self.total_pnl / self.initial_capital) * 100,
            'max_drawdown': self.max_drawdown,
            'peak_capital': self.peak_capital,
            'position_pnl': self.position_pnl
        }
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not self.pnl_history:
            return 0.0
        
        # Calculate daily returns
        df = pd.DataFrame(self.pnl_history)
        if len(df) < 2:
            return 0.0
        
        df['daily_return'] = df['current_capital'].pct_change()
        returns = df['daily_return'].dropna()
        
        if len(returns) == 0:
            return 0.0
        
        # Calculate Sharpe ratio
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        return sharpe_ratio
    
    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if not self.pnl_history:
            return 0.0
        
        # Calculate daily returns
        df = pd.DataFrame(self.pnl_history)
        if len(df) < 2:
            return 0.0
        
        df['daily_return'] = df['current_capital'].pct_change()
        returns = df['daily_return'].dropna()
        
        if len(returns) == 0:
            return 0.0
        
        # Calculate downside deviation
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(252)
        return sortino_ratio

class PortfolioManager:
    """Comprehensive portfolio management system"""
    
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
        
        # Initialize P&L tracker
        self.pnl_tracker = PnLTracker(initial_capital)
        
        # Performance tracking
        self.peak_value = initial_capital
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        logger.info(f"Initialized PortfolioManager with ${initial_capital:,.2f} capital")
    
    def add_portfolio_callback(self, callback: Callable):
        """Add callback for portfolio events"""
        self.portfolio_callbacks.append(callback)
        logger.info(f"Added portfolio callback: {callback.__name__}")
    
    def process_trade(self, symbol: str, quantity: int, price: float, trade_type: str, timestamp: datetime = None):
        """Process a trade and update portfolio"""
        
        # Calculate trade value
        trade_value = quantity * price
        
        if trade_type == "BUY":
            # Check if we have enough capital
            if trade_value > self.available_capital:
                logger.warning(f"Insufficient capital for {symbol} trade: ${trade_value:.2f} > ${self.available_capital:.2f}")
                return False
            
            # Update available capital
            self.available_capital -= trade_value
            
            # Create or update position
            if symbol not in self.positions:
                # 🎯 CRITICAL FIX: Pass timestamp for backtesting
                self.positions[symbol] = Position(symbol, created_at=timestamp)
            
            self.positions[symbol].update_position(quantity, price, "BUY")
            
        elif trade_type == "SELL":
            # Check if we have the position
            if symbol not in self.positions or self.positions[symbol].quantity < quantity:
                logger.warning(f"Insufficient position for {symbol} sell: {quantity} > {self.positions[symbol].quantity if symbol in self.positions else 0}")
                # PROFESSIONAL FIX: Auto-correct sell quantity to available position
                available_quantity = self.positions[symbol].quantity if symbol in self.positions else 0
                if available_quantity > 0:
                    logger.info(f"Auto-correcting {symbol} sell: {quantity} → {available_quantity} shares")
                    quantity = available_quantity
                else:
                    logger.info(f"Skipping {symbol} sell - no position to close")
                    return False
            
            # Calculate P&L BEFORE updating position (for accurate avg_price)
            realized_pnl = (price - self.positions[symbol].avg_price) * quantity
            
            # Update position
            self.positions[symbol].update_position(quantity, price, "SELL")
            
            # Update available capital
            self.available_capital += trade_value
            
            # Update P&L tracker immediately after position update
            self.pnl_tracker.update_pnl(realized_pnl=realized_pnl, symbol=symbol, position_pnl=realized_pnl)
            
            # Remove empty positions
            if self.positions[symbol].quantity == 0:
                del self.positions[symbol]
        
        # Update portfolio totals
        self._update_portfolio_totals()
        
        # Record portfolio state
        self._record_portfolio_state()
        
        # Notify callbacks
        for callback in self.portfolio_callbacks:
            try:
                callback(symbol, trade_type, quantity, price)
            except Exception as e:
                logger.error(f"Portfolio callback error: {e}")
        
        logger.info(f"Processed {trade_type} trade: {symbol} {quantity} @ ${price:.2f}")
        return True
    
    def update_market_prices(self, market_data: Dict[str, float]):
        """Update market prices and recalculate portfolio values"""
        
        for symbol, current_price in market_data.items():
            if symbol in self.positions:
                self.positions[symbol].update_market_value(current_price)
        
        # Update portfolio totals
        self._update_portfolio_totals()
        
        # Update P&L tracker
        self.pnl_tracker.update_pnl(unrealized_pnl=self.total_unrealized_pnl)
        
        # Record portfolio state
        self._record_portfolio_state()
        
        logger.debug(f"Updated market prices for {len(market_data)} symbols")
    
    def _update_portfolio_totals(self):
        """Update portfolio totals"""
        self.total_market_value = sum(pos.market_value for pos in self.positions.values())
        self.total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        self.total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.total_pnl = self.total_realized_pnl + self.total_unrealized_pnl
        
        # Update drawdown
        total_value = self.total_market_value + self.available_capital
        if total_value > self.peak_value:
            self.peak_value = total_value
        
        self.current_drawdown = (self.peak_value - total_value) / self.peak_value if self.peak_value > 0 else 0.0
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
    
    def _record_portfolio_state(self):
        """Record current portfolio state"""
        portfolio_state = {
            'timestamp': datetime.now(),
            'total_market_value': self.total_market_value,
            'available_capital': self.available_capital,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'position_count': len(self.positions)
        }
        self.portfolio_history.append(portfolio_state)
        
        # Keep only last 1000 records
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-1000:]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_value = self.total_market_value + self.available_capital
        total_return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'total_market_value': self.total_market_value,
            'available_capital': self.available_capital,
            'total_value': total_value,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'total_return_pct': total_return_pct,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'position_count': len(self.positions),
            'sharpe_ratio': self.pnl_tracker.calculate_sharpe_ratio(),
            'sortino_ratio': self.pnl_tracker.calculate_sortino_ratio()
        }
    
    def get_position_weights(self) -> Dict[str, float]:
        """Get position weights"""
        total_value = self.total_market_value + self.available_capital
        if total_value == 0:
            return {}
        
        weights = {}
        for symbol, position in self.positions.items():
            weights[symbol] = position.market_value / total_value
        
        return weights
    
    def get_portfolio_metrics(self, current_prices: Dict[str, float]) -> PortfolioMetrics:
        """Get comprehensive portfolio metrics"""
        # Update market values
        self.update_market_prices(current_prices)
        
        total_value = self.total_market_value + self.available_capital
        total_return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
        
        return PortfolioMetrics(
            total_market_value=self.total_market_value,
            available_capital=self.available_capital,
            total_realized_pnl=self.total_realized_pnl,
            total_unrealized_pnl=self.total_unrealized_pnl,
            total_pnl=self.total_pnl,
            total_return_pct=total_return_pct,
            max_drawdown=self.max_drawdown,
            current_drawdown=self.current_drawdown,
            sharpe_ratio=self.pnl_tracker.calculate_sharpe_ratio(),
            sortino_ratio=self.pnl_tracker.calculate_sortino_ratio(),
            position_count=len(self.positions)
        )
    
    def get_position_metrics(self, current_prices: Dict[str, float]) -> Dict[str, PositionMetrics]:
        """Get metrics for all positions"""
        total_value = self.total_market_value + self.available_capital
        
        position_metrics = {}
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position_metrics[symbol] = position.get_metrics(current_prices[symbol], total_value)
        
        return position_metrics
    
    def reset_for_backtesting(self):
        """Reset portfolio manager for backtesting - clear all positions and history"""
        logger.info("🔄 Resetting portfolio manager for backtesting")
        
        # Clear all positions
        self.positions.clear()
        
        # Reset capital to initial amount
        self.available_capital = self.initial_capital
        
        # Reset all P&L metrics
        self.total_market_value = 0.0
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_pnl = 0.0
        
        # Reset performance tracking
        self.peak_value = self.initial_capital
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        
        # Clear history
        self.portfolio_history.clear()
        
        # Reset P&L tracker
        self.pnl_tracker = PnLTracker(self.initial_capital)
        
        logger.info(f"✅ Portfolio manager reset: ${self.initial_capital:,.2f} capital, 0 positions")

    def shutdown(self):
        """Shutdown portfolio manager"""
        logger.info("Shutting down PortfolioManager") 