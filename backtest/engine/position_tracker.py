"""
Position Tracker - Professional Position and Cash Management
=============================================================

Helper class for tracking positions, cash, and P&L during backtesting.
Provides validation for BUY/SELL orders and integrates with CentralRiskManager.

This is a critical component that ensures:
- Accurate position tracking by symbol
- Cash management (can't buy if insufficient cash)
- Position validation (can't sell if no position)
- Unrealized and realized P&L calculation
- Position history for analytics

Author: StatArb_Gemini Backtest Application
Version: 1.0.0
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class Position:
    """Represents a position in a symbol"""
    symbol: str
    quantity: float  # Positive for long, negative for short
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_cost_basis: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def position_side(self) -> PositionSide:
        """Get position side"""
        if self.quantity > 0:
            return PositionSide.LONG
        elif self.quantity < 0:
            return PositionSide.SHORT
        else:
            return PositionSide.FLAT
    
    @property
    def market_value(self) -> float:
        """Calculate current market value"""
        return self.quantity * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        """Calculate P&L percentage"""
        if self.total_cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / abs(self.total_cost_basis)) * 100
    
    def update_price(self, new_price: float) -> None:
        """Update current price and recalculate unrealized P&L"""
        self.current_price = new_price
        
        # Recalculate unrealized P&L
        if self.quantity != 0:
            # Long position: profit when price goes up
            # Short position: profit when price goes down
            self.unrealized_pnl = (self.current_price - self.avg_entry_price) * self.quantity
        else:
            self.unrealized_pnl = 0.0
        
        self.last_updated = datetime.now()


@dataclass
class Trade:
    """Represents a completed trade"""
    trade_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    strategy_id: str = ""
    position_before: float = 0.0
    position_after: float = 0.0
    realized_pnl: float = 0.0
    
    @property
    def gross_amount(self) -> float:
        """Gross trade amount (before commissions)"""
        return self.quantity * self.price
    
    @property
    def net_amount(self) -> float:
        """Net trade amount (after commissions)"""
        return self.gross_amount + self.commission


class PositionTracker:
    """
    Professional position and cash tracking for backtesting
    
    This class provides:
    - Position tracking by symbol (long/short)
    - Cash availability tracking
    - Trade validation (sufficient cash/position)
    - P&L calculation (unrealized + realized)
    - Position history for analytics
    - Integration with CentralRiskManager
    
    Critical for institutional-grade backtesting:
    - Prevents trading with insufficient capital
    - Accurate position and P&L tracking
    - Complete audit trail
    """
    
    def __init__(self, initial_capital: float, commission_per_trade: float = 0.0):
        """
        Initialize position tracker
        
        Args:
            initial_capital: Starting cash balance
            commission_per_trade: Commission per trade (fixed)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_per_trade = commission_per_trade
        
        # Position tracking
        self.positions: Dict[str, Position] = {}  # {symbol: Position}
        
        # Trade history
        self.trades: List[Trade] = []
        self.trade_count = 0
        
        # P&L tracking
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_commissions = 0.0
        
        # Metrics
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        
        logger.info(f"📊 PositionTracker initialized with ${initial_capital:,.2f}")
    
    # ============================================================
    # Trade Validation Methods
    # ============================================================
    
    def can_buy(self, symbol: str, quantity: float, price: float, 
                include_commission: bool = True) -> tuple[bool, str]:
        """
        Check if sufficient cash for BUY order
        
        Args:
            symbol: Symbol to buy
            quantity: Quantity to buy
            price: Price per unit
            include_commission: Whether to include commission in check
            
        Returns:
            (can_buy, reason) - True if sufficient cash, False otherwise with reason
        """
        required_cash = quantity * price
        
        if include_commission:
            required_cash += self.commission_per_trade
        
        if self.cash >= required_cash:
            return True, f"Sufficient cash: ${self.cash:,.2f} >= ${required_cash:,.2f}"
        else:
            shortage = required_cash - self.cash
            return False, f"Insufficient cash: ${self.cash:,.2f} < ${required_cash:,.2f} (shortage: ${shortage:,.2f})"
    
    def can_sell(self, symbol: str, quantity: float) -> tuple[bool, str]:
        """
        Check if sufficient position for SELL order
        
        Args:
            symbol: Symbol to sell
            quantity: Quantity to sell
            
        Returns:
            (can_sell, reason) - True if sufficient position, False otherwise with reason
        """
        current_position = self.get_position_quantity(symbol)
        
        if current_position >= quantity:
            return True, f"Sufficient position: {current_position:.2f} >= {quantity:.2f}"
        else:
            shortage = quantity - current_position
            if current_position <= 0:
                return False, f"No position in {symbol} (current: {current_position:.2f})"
            else:
                return False, f"Insufficient position: {current_position:.2f} < {quantity:.2f} (shortage: {shortage:.2f})"
    
    def validate_trade(self, symbol: str, side: str, quantity: float, price: float) -> tuple[bool, str]:
        """
        Validate trade before execution
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Trade quantity
            price: Trade price
            
        Returns:
            (is_valid, reason) - Validation result with reason
        """
        if side.lower() == 'buy':
            return self.can_buy(symbol, quantity, price)
        elif side.lower() == 'sell':
            return self.can_sell(symbol, quantity)
        else:
            return False, f"Invalid side: {side} (must be 'buy' or 'sell')"
    
    # ============================================================
    # Position Management Methods
    # ============================================================
    
    def update_position(self, symbol: str, side: str, quantity: float, price: float,
                       commission: float = None, strategy_id: str = "",
                       trade_id: str = None) -> Dict[str, Any]:
        """
        Update position after trade execution
        
        This is the main method called after a trade is executed.
        It updates positions, cash, P&L, and records the trade.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Trade quantity
            price: Trade price
            commission: Trade commission (defaults to commission_per_trade)
            strategy_id: Strategy that generated the trade
            trade_id: Unique trade identifier
            
        Returns:
            Dictionary with position update details
        """
        if commission is None:
            commission = self.commission_per_trade
        
        # Get current position
        position_before = self.get_position_quantity(symbol)
        
        # Calculate trade details
        side_lower = side.lower()
        gross_amount = quantity * price
        net_amount = gross_amount + commission
        
        # Update cash based on trade side
        if side_lower == 'buy':
            self.cash -= net_amount
            new_quantity = position_before + quantity
        elif side_lower == 'sell':
            self.cash += gross_amount - commission  # Add proceeds, subtract commission
            new_quantity = position_before - quantity
        else:
            raise ValueError(f"Invalid side: {side}")
        
        # Track commission
        self.total_commissions += commission
        
        # Calculate realized P&L for SELL trades
        realized_pnl = 0.0
        if side_lower == 'sell' and symbol in self.positions:
            # Realized P&L = (sell_price - avg_entry_price) * quantity - commission
            avg_entry = self.positions[symbol].avg_entry_price
            realized_pnl = (price - avg_entry) * quantity - commission
            self.total_realized_pnl += realized_pnl
            
            # Update position's realized P&L
            self.positions[symbol].realized_pnl += realized_pnl
        
        # Update or create position
        if new_quantity == 0:
            # Position closed
            if symbol in self.positions:
                del self.positions[symbol]
        else:
            if symbol not in self.positions:
                # New position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=new_quantity,
                    avg_entry_price=price,
                    current_price=price,
                    total_cost_basis=gross_amount + commission
                )
            else:
                # Update existing position
                position = self.positions[symbol]
                
                if side_lower == 'buy':
                    # Average up/down for new buys
                    old_cost = position.total_cost_basis
                    new_cost = gross_amount + commission
                    position.total_cost_basis = old_cost + new_cost
                    position.avg_entry_price = position.total_cost_basis / new_quantity
                elif side_lower == 'sell':
                    # Reduce cost basis proportionally
                    reduction_ratio = quantity / position_before
                    position.total_cost_basis *= (1 - reduction_ratio)
                
                position.quantity = new_quantity
                position.current_price = price
                position.last_updated = datetime.now()
        
        # Record trade
        if trade_id is None:
            self.trade_count += 1
            trade_id = f"trade_{self.trade_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            commission=commission,
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            position_before=position_before,
            position_after=new_quantity,
            realized_pnl=realized_pnl
        )
        self.trades.append(trade)
        
        # Update metrics
        self._update_metrics()
        
        logger.info(f"📊 Position updated: {symbol} {side.upper()} {quantity:.2f} @ ${price:.2f}")
        logger.info(f"   Position: {position_before:.2f} → {new_quantity:.2f}")
        logger.info(f"   Cash: ${self.cash:,.2f}")
        if realized_pnl != 0:
            logger.info(f"   Realized P&L: ${realized_pnl:,.2f}")
        
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'position_before': position_before,
            'position_after': new_quantity,
            'cash': self.cash,
            'realized_pnl': realized_pnl,
            'trade_id': trade_id
        }
    
    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """
        Update current market prices for all positions
        
        This should be called on every bar to maintain accurate unrealized P&L
        
        Args:
            prices: Dictionary of {symbol: current_price}
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
        
        # Recalculate total unrealized P&L
        self.total_unrealized_pnl = sum(
            pos.unrealized_pnl for pos in self.positions.values()
        )
        
        # Update metrics
        self._update_metrics()
    
    # ============================================================
    # Position Query Methods
    # ============================================================
    
    def get_position_quantity(self, symbol: str) -> float:
        """Get current position quantity for symbol"""
        if symbol in self.positions:
            return self.positions[symbol].quantity
        return 0.0
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position object for symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if has position in symbol"""
        return symbol in self.positions and self.positions[symbol].quantity != 0
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all current positions"""
        return self.positions.copy()
    
    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)
    
    # ============================================================
    # Portfolio Metrics Methods
    # ============================================================
    
    def get_equity(self) -> float:
        """Calculate total equity (cash + positions market value)"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)"""
        return self.total_realized_pnl + self.total_unrealized_pnl
    
    def get_total_pnl_pct(self) -> float:
        """Get total P&L as percentage of initial capital"""
        return (self.get_total_pnl() / self.initial_capital) * 100
    
    def get_return_pct(self) -> float:
        """Get return percentage"""
        current_equity = self.get_equity()
        return ((current_equity - self.initial_capital) / self.initial_capital) * 100
    
    def _update_metrics(self) -> None:
        """Update portfolio metrics (drawdown, peak equity, etc.)"""
        current_equity = self.get_equity()
        
        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Calculate drawdown
        if self.peak_equity > 0:
            drawdown = self.peak_equity - current_equity
            drawdown_pct = (drawdown / self.peak_equity) * 100
            
            # Update max drawdown
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                self.max_drawdown_pct = drawdown_pct
    
    # ============================================================
    # Reporting Methods
    # ============================================================
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        current_equity = self.get_equity()
        
        return {
            'cash': self.cash,
            'initial_capital': self.initial_capital,
            'current_equity': current_equity,
            'return_pct': self.get_return_pct(),
            'total_pnl': self.get_total_pnl(),
            'total_pnl_pct': self.get_total_pnl_pct(),
            'realized_pnl': self.total_realized_pnl,
            'unrealized_pnl': self.total_unrealized_pnl,
            'total_commissions': self.total_commissions,
            'position_count': self.get_position_count(),
            'trade_count': len(self.trades),
            'peak_equity': self.peak_equity,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct
        }
    
    def get_positions_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all positions"""
        return [
            {
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'side': pos.position_side.value,
                'avg_entry_price': pos.avg_entry_price,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'unrealized_pnl': pos.unrealized_pnl,
                'pnl_pct': pos.pnl_pct,
                'realized_pnl': pos.realized_pnl
            }
            for pos in self.positions.values()
        ]
    
    def get_trades_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all trades"""
        return [asdict(trade) for trade in self.trades]
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"PositionTracker(\n"
            f"  cash=${self.cash:,.2f},\n"
            f"  equity=${self.get_equity():,.2f},\n"
            f"  positions={self.get_position_count()},\n"
            f"  trades={len(self.trades)},\n"
            f"  pnl=${self.get_total_pnl():,.2f} ({self.get_total_pnl_pct():.2f}%)\n"
            f")"
        )

