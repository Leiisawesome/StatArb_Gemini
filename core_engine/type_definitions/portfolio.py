"""
Core Engine Portfolio Types

Lightweight portfolio management for standalone core_engine.

⚠️ NOTE: For full position tracking, use PositionBook (SSOT):
    from core_engine.trading.position_book import PositionBook, BookPosition

This module provides simplified types for basic portfolio operations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class Position:
    """
    Lightweight position representation for basic portfolio operations.

    For full position tracking with fills, P&L, and history,
    use BookPosition from core_engine.trading.position_book instead.
    """
    symbol: str
    quantity: float
    average_price: float
    market_price: Optional[float] = None

    @property
    def market_value(self) -> float:
        """Current market value of position"""
        if self.market_price is None:
            return self.quantity * self.average_price
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L"""
        if self.market_price is None:
            return 0.0
        return (self.market_price - self.average_price) * self.quantity


@dataclass
class PortfolioSnapshot:
    """Portfolio state snapshot"""
    timestamp: datetime
    cash: float
    positions: Dict[str, Position]
    total_value: float
    unrealized_pnl: float
    realized_pnl: float = 0.0

    @classmethod
    def create(cls, cash: float, positions: Dict[str, Position]) -> 'PortfolioSnapshot':
        """Create snapshot from current state"""
        total_value = cash + sum(pos.market_value for pos in positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions.values())

        return cls(
            timestamp=datetime.now(),
            cash=cash,
            positions=positions.copy(),
            total_value=total_value,
            unrealized_pnl=unrealized_pnl
        )


@dataclass
class PortfolioConfig:
    """Portfolio configuration"""
    initial_cash: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    min_cash_reserve: float = 1000.0
    max_position_size: float = 0.1  # 10% max per position
    enable_short_selling: bool = False


class Portfolio:
    """Core portfolio management"""

    def __init__(self, config: PortfolioConfig):
        self.config = config
        self.cash = config.initial_cash
        self.positions: Dict[str, Position] = {}
        self.history: List[PortfolioSnapshot] = []

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)

    def update_position(self, symbol: str, quantity: float, price: float):
        """Update position from trade execution"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            # Calculate new average price
            total_cost = pos.quantity * pos.average_price + quantity * price
            total_quantity = pos.quantity + quantity

            if abs(total_quantity) < 1e-8:  # Position closed
                del self.positions[symbol]
                self.cash += -quantity * price  # Add proceeds
            else:
                pos.quantity = total_quantity
                pos.average_price = total_cost / total_quantity
                self.cash += -quantity * price  # Subtract cost
        else:
            # New position
            self.positions[symbol] = Position(symbol, quantity, price)
            self.cash += -quantity * price

    def update_market_prices(self, prices: Dict[str, float]):
        """Update market prices for positions"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].market_price = price

    def get_snapshot(self) -> PortfolioSnapshot:
        """Get current portfolio snapshot"""
        snapshot = PortfolioSnapshot.create(self.cash, self.positions)
        self.history.append(snapshot)
        return snapshot

    @property
    def total_value(self) -> float:
        """Current total portfolio value"""
        return self.cash + sum(pos.market_value for pos in self.positions.values())

    @property
    def unrealized_pnl(self) -> float:
        """Current unrealized P&L"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())


class PortfolioManager:
    """Portfolio manager for core engine"""

    def __init__(self, config: PortfolioConfig):
        self.portfolio = Portfolio(config)
        self.config = config

    def execute_trade(self, symbol: str, quantity: float, price: float) -> bool:
        """Execute trade and update portfolio"""
        # Calculate commission
        commission = abs(quantity * price) * self.config.commission_rate

        # Check cash requirements
        cash_needed = quantity * price + commission
        if self.portfolio.cash < cash_needed and quantity > 0:
            return False  # Insufficient cash

        # Execute trade
        self.portfolio.update_position(symbol, quantity, price)
        self.portfolio.cash -= commission

        return True

    def get_position_size(self, symbol: str) -> float:
        """Get current position size for symbol"""
        pos = self.portfolio.get_position(symbol)
        return pos.quantity if pos else 0.0

    def can_trade(self, symbol: str, quantity: float, price: float) -> bool:
        """Check if trade is allowed"""
        # Check cash
        if quantity > 0:  # Buy
            cash_needed = quantity * price * (1 + self.config.commission_rate)
            if self.portfolio.cash < cash_needed:
                return False

        # Check position size limits
        new_position_value = abs(self.get_position_size(symbol) + quantity) * price
        if new_position_value > self.portfolio.total_value * self.config.max_position_size:
            return False

        return True