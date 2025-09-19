#!/usr/bin/env python3
"""
Paper Trading Execution and Portfolio Management
===============================================

Simplified execution and portfolio management system for testing the complete
trading pipeline with paper trading simulation.

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Paper Trading)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"

@dataclass
class Order:
    """Order representation"""
    order_id: str
    symbol: str
    side: str  # buy/sell
    quantity: float
    price: float
    order_type: str = "market"
    timestamp: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0

@dataclass
class Position:
    """Position representation"""
    symbol: str
    side: PositionSide
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def market_value(self) -> float:
        """Current market value of position"""
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        """Cost basis of position"""
        return self.quantity * self.avg_price

@dataclass
class Trade:
    """Executed trade representation"""
    trade_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0
    order_id: Optional[str] = None

class PaperTradingEngine:
    """
    Paper Trading Execution Engine
    
    Simulates order execution with realistic slippage and commission models.
    """
    
    def __init__(self, initial_capital: float = 100000.0, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        
        # Storage
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.positions: Dict[str, Position] = {}
        
        # Market data for pricing
        self.current_prices: Dict[str, float] = {}
        
        self.logger = logging.getLogger("paper_trading")
        self.logger.info(f"PaperTradingEngine initialized with ${initial_capital:,.2f}")
    
    def update_market_data(self, prices: Dict[str, float]):
        """Update current market prices"""
        self.current_prices.update(prices)
        self._update_position_values()
    
    def submit_order(self, symbol: str, side: str, quantity: float, 
                    order_type: str = "market", price: Optional[float] = None) -> str:
        """Submit a trading order"""
        order_id = str(uuid.uuid4())
        
        # Get current market price
        if symbol not in self.current_prices:
            self.logger.error(f"No market data for {symbol}")
            return None
        
        market_price = self.current_prices[symbol]
        order_price = price if price and order_type == "limit" else market_price
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=order_price,
            order_type=order_type
        )
        
        self.orders[order_id] = order
        
        # For paper trading, execute immediately
        if order_type == "market":
            self._execute_order(order_id)
        
        return order_id
    
    def _execute_order(self, order_id: str) -> bool:
        """Execute an order"""
        order = self.orders.get(order_id)
        if not order:
            return False
        
        # Calculate execution price with slippage
        market_price = self.current_prices[order.symbol]
        slippage = self._calculate_slippage(order.quantity, order.symbol)
        
        if order.side == "buy":
            execution_price = market_price * (1 + slippage)
        else:
            execution_price = market_price * (1 - slippage)
        
        # Check if we have enough capital/shares
        if not self._validate_order(order, execution_price):
            order.status = OrderStatus.REJECTED
            self.logger.warning(f"Order {order_id} rejected - insufficient funds/shares")
            return False
        
        # Calculate commission
        commission = execution_price * order.quantity * self.commission_rate
        
        # Execute the trade
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            timestamp=datetime.now(),
            commission=commission,
            order_id=order_id
        )
        
        self.trades.append(trade)
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.commission = commission
        
        # Update positions and cash
        self._update_position(trade)
        self._update_cash(trade)
        
        self.logger.info(f"Order {order_id} executed: {order.side} {order.quantity} {order.symbol} @ ${execution_price:.2f}")
        return True
    
    def _calculate_slippage(self, quantity: float, symbol: str) -> float:
        """Calculate slippage based on order size"""
        # Simple slippage model - larger orders have more slippage
        base_slippage = 0.0005  # 0.05% base slippage
        size_factor = min(quantity / 1000, 0.002)  # Additional slippage for size
        return base_slippage + size_factor
    
    def _validate_order(self, order: Order, execution_price: float) -> bool:
        """Validate if order can be executed"""
        if order.side == "buy":
            # Check if we have enough cash
            required_cash = execution_price * order.quantity * (1 + self.commission_rate)
            return self.cash >= required_cash
        else:
            # Check if we have enough shares
            position = self.positions.get(order.symbol)
            if not position or position.side != PositionSide.LONG:
                return False
            return position.quantity >= order.quantity
    
    def _update_position(self, trade: Trade):
        """Update position after trade execution"""
        symbol = trade.symbol
        existing_position = self.positions.get(symbol)
        
        if trade.side == "buy":
            if existing_position and existing_position.side == PositionSide.LONG:
                # Add to existing long position
                total_quantity = existing_position.quantity + trade.quantity
                total_cost = (existing_position.quantity * existing_position.avg_price + 
                             trade.quantity * trade.price)
                new_avg_price = total_cost / total_quantity
                
                existing_position.quantity = total_quantity
                existing_position.avg_price = new_avg_price
            else:
                # Create new long position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=trade.quantity,
                    avg_price=trade.price,
                    current_price=trade.price
                )
        
        else:  # sell
            if existing_position and existing_position.side == PositionSide.LONG:
                # Reduce long position
                existing_position.quantity -= trade.quantity
                
                # Calculate realized PnL
                realized_pnl = (trade.price - existing_position.avg_price) * trade.quantity
                existing_position.realized_pnl += realized_pnl
                
                # Remove position if quantity is zero
                if existing_position.quantity <= 0:
                    del self.positions[symbol]
    
    def _update_cash(self, trade: Trade):
        """Update cash after trade execution"""
        if trade.side == "buy":
            self.cash -= (trade.price * trade.quantity + trade.commission)
        else:
            self.cash += (trade.price * trade.quantity - trade.commission)
    
    def _update_position_values(self):
        """Update unrealized PnL for all positions"""
        for symbol, position in self.positions.items():
            if symbol in self.current_prices:
                position.current_price = self.current_prices[symbol]
                if position.side == PositionSide.LONG:
                    position.unrealized_pnl = (position.current_price - position.avg_price) * position.quantity
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + position_value
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        portfolio_value = self.get_portfolio_value()
        position_value = sum(pos.market_value for pos in self.positions.values())
        total_realized_pnl = sum(pos.realized_pnl for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            "portfolio_value": portfolio_value,
            "cash": self.cash,
            "position_value": position_value,
            "initial_capital": self.initial_capital,
            "total_return": (portfolio_value - self.initial_capital) / self.initial_capital,
            "realized_pnl": total_realized_pnl,
            "unrealized_pnl": total_unrealized_pnl,
            "total_pnl": total_realized_pnl + total_unrealized_pnl,
            "num_positions": len(self.positions),
            "num_trades": len(self.trades),
            "cash_utilization": 1 - (self.cash / self.initial_capital)
        }

class PortfolioManager:
    """
    Portfolio Management System
    
    Manages position sizing, risk controls, and portfolio optimization.
    """
    
    def __init__(self, trading_engine: PaperTradingEngine, max_position_size: float = 0.1):
        self.trading_engine = trading_engine
        self.max_position_size = max_position_size  # Maximum 10% per position
        
        # Risk controls
        self.max_portfolio_leverage = 1.0  # No leverage for paper trading
        self.max_sector_exposure = 0.3     # 30% max per sector
        
        self.logger = logging.getLogger("portfolio_manager")
    
    def execute_signal(self, signal) -> Optional[str]:
        """Execute a trading signal"""
        from core_engine.signal_generator import SignalType
        
        # Calculate position size
        portfolio_value = self.trading_engine.get_portfolio_value()
        max_dollar_amount = portfolio_value * self.max_position_size
        
        # Adjust for signal strength and confidence
        size_multiplier = signal.position_size  # Already calculated in signal generator
        target_dollar_amount = max_dollar_amount * size_multiplier
        
        # Calculate shares to trade
        current_price = self.trading_engine.current_prices.get(signal.symbol)
        if not current_price:
            self.logger.error(f"No current price for {signal.symbol}")
            return None
        
        target_shares = int(target_dollar_amount / current_price)
        
        if target_shares == 0:
            self.logger.info(f"Position size too small for {signal.symbol}")
            return None
        
        # Determine order side
        if signal.signal_type == SignalType.BUY:
            order_side = "buy"
        elif signal.signal_type == SignalType.SELL:
            order_side = "sell"
        else:
            return None  # No action for HOLD signals
        
        # Submit order
        order_id = self.trading_engine.submit_order(
            symbol=signal.symbol,
            side=order_side,
            quantity=target_shares,
            order_type="market"
        )
        
        if order_id:
            self.logger.info(f"Executed signal: {order_side} {target_shares} {signal.symbol} (confidence: {signal.confidence:.2f})")
        
        return order_id
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate portfolio risk metrics"""
        positions = self.trading_engine.positions
        portfolio_value = self.trading_engine.get_portfolio_value()
        
        if not positions:
            return {
                "total_exposure": 0, 
                "max_position_exposure": 0, 
                "num_positions": 0,
                "portfolio_volatility": 0,
                "leverage": 0,
                "diversification_ratio": 0
            }
        
        # Position exposures
        exposures = []
        for position in positions.values():
            exposure = position.market_value / portfolio_value
            exposures.append(exposure)
        
        # Calculate concentration
        max_exposure = max(exposures) if exposures else 0
        total_exposure = sum(exposures)
        
        # Calculate portfolio volatility (simplified)
        if len(self.trading_engine.trades) > 1:
            trade_returns = []
            prev_value = self.trading_engine.initial_capital
            
            # This is simplified - in practice you'd use proper return calculation
            for trade in self.trading_engine.trades[-10:]:  # Last 10 trades
                pnl = trade.quantity * (trade.price - prev_value) if hasattr(trade, 'pnl') else 0
                trade_returns.append(pnl / prev_value)
                prev_value = trade.price
            
            portfolio_volatility = np.std(trade_returns) if trade_returns else 0
        else:
            portfolio_volatility = 0
        
        return {
            "total_exposure": total_exposure,
            "max_position_exposure": max_exposure,
            "num_positions": len(positions),
            "portfolio_volatility": portfolio_volatility,
            "leverage": total_exposure,  # Since we don't use margin
            "diversification_ratio": 1 / len(positions) if positions else 0
        }
    
    def rebalance_portfolio(self, target_weights: Dict[str, float] = None):
        """Rebalance portfolio to target weights"""
        # Simplified rebalancing - in practice this would be more sophisticated
        current_positions = self.trading_engine.positions
        portfolio_value = self.trading_engine.get_portfolio_value()
        
        self.logger.info(f"Portfolio rebalancing not implemented in this demo")
        # Implementation would calculate required trades to reach target weights
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics"""
        summary = self.trading_engine.get_portfolio_summary()
        
        # Calculate additional metrics
        if len(self.trading_engine.trades) > 0:
            winning_trades = [t for t in self.trading_engine.trades if hasattr(t, 'pnl') and t.pnl > 0]
            losing_trades = [t for t in self.trading_engine.trades if hasattr(t, 'pnl') and t.pnl < 0]
            
            win_rate = len(winning_trades) / len(self.trading_engine.trades) if self.trading_engine.trades else 0
            
            avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Sharpe ratio (simplified)
        total_return = summary['total_return']
        sharpe_ratio = total_return / 0.15 if total_return > 0 else 0  # Assuming 15% volatility
        
        return {
            **summary,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": 0,  # Would need to track portfolio value over time
        }