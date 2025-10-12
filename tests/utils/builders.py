"""
Test data builders for creating consistent test fixtures.

Provides builder classes for creating test data with sensible defaults
and fluent interfaces for customization.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class MarketDataBuilder:
    """
    Builder for creating market data DataFrames for testing.
    
    Example:
        data = (MarketDataBuilder()
                .with_symbol('AAPL')
                .with_days(100)
                .with_trend(0.001)  # 0.1% daily growth
                .with_volatility(0.02)  # 2% daily vol
                .build())
    """
    
    def __init__(self):
        self._symbol = 'TEST'
        self._start_price = 100.0
        self._days = 252
        self._start_date = datetime.now() - timedelta(days=252)
        self._trend = 0.0
        self._volatility = 0.01
        self._seed = 42
        
    def with_symbol(self, symbol: str) -> 'MarketDataBuilder':
        """Set the symbol/ticker."""
        self._symbol = symbol
        return self
    
    def with_start_price(self, price: float) -> 'MarketDataBuilder':
        """Set the starting price."""
        self._start_price = price
        return self
    
    def with_days(self, days: int) -> 'MarketDataBuilder':
        """Set the number of days of data."""
        self._days = days
        return self
    
    def with_start_date(self, date: datetime) -> 'MarketDataBuilder':
        """Set the start date."""
        self._start_date = date
        return self
    
    def with_trend(self, daily_return: float) -> 'MarketDataBuilder':
        """Set the daily trend (e.g., 0.001 = 0.1% daily growth)."""
        self._trend = daily_return
        return self
    
    def with_volatility(self, daily_vol: float) -> 'MarketDataBuilder':
        """Set the daily volatility (e.g., 0.02 = 2%)."""
        self._volatility = daily_vol
        return self
    
    def with_seed(self, seed: int) -> 'MarketDataBuilder':
        """Set the random seed for reproducibility."""
        self._seed = seed
        return self
    
    def build(self) -> pd.DataFrame:
        """Build and return the market data DataFrame."""
        np.random.seed(self._seed)
        
        dates = pd.date_range(
            self._start_date,
            periods=self._days,
            freq='D'
        )
        
        # Generate returns with trend and volatility
        returns = np.random.normal(
            self._trend,
            self._volatility,
            self._days
        )
        
        # Generate price series
        prices = self._start_price * np.exp(np.cumsum(returns))
        
        # Create DataFrame with OHLCV data
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': self._symbol,
            'open': prices * (1 + np.random.uniform(-0.002, 0.002, self._days)),
            'high': prices * (1 + np.random.uniform(0.001, 0.01, self._days)),
            'low': prices * (1 + np.random.uniform(-0.01, -0.001, self._days)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, self._days),
            'returns': returns,
            'volatility': np.random.uniform(
                self._volatility * 0.5,
                self._volatility * 1.5,
                self._days
            )
        })
        
        return df


class OrderBuilder:
    """
    Builder for creating order dictionaries for testing.
    
    Example:
        order = (OrderBuilder()
                 .with_symbol('AAPL')
                 .with_quantity(100)
                 .buy()
                 .at_market()
                 .build())
    """
    
    def __init__(self):
        self._order = {
            'symbol': 'TEST',
            'quantity': 100,
            'side': 'buy',
            'order_type': 'market',
            'status': 'pending',
            'created_at': datetime.now(),
        }
    
    def with_symbol(self, symbol: str) -> 'OrderBuilder':
        """Set the symbol."""
        self._order['symbol'] = symbol
        return self
    
    def with_quantity(self, quantity: float) -> 'OrderBuilder':
        """Set the quantity."""
        self._order['quantity'] = quantity
        return self
    
    def buy(self) -> 'OrderBuilder':
        """Set side to buy."""
        self._order['side'] = 'buy'
        return self
    
    def sell(self) -> 'OrderBuilder':
        """Set side to sell."""
        self._order['side'] = 'sell'
        return self
    
    def at_market(self) -> 'OrderBuilder':
        """Set order type to market."""
        self._order['order_type'] = 'market'
        return self
    
    def at_limit(self, price: float) -> 'OrderBuilder':
        """Set order type to limit with price."""
        self._order['order_type'] = 'limit'
        self._order['limit_price'] = price
        return self
    
    def with_status(self, status: str) -> 'OrderBuilder':
        """Set order status."""
        self._order['status'] = status
        return self
    
    def filled(self, fill_price: Optional[float] = None) -> 'OrderBuilder':
        """Mark order as filled."""
        self._order['status'] = 'filled'
        self._order['filled_at'] = datetime.now()
        if fill_price:
            self._order['fill_price'] = fill_price
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the order dictionary."""
        return self._order.copy()


class PositionBuilder:
    """
    Builder for creating position dictionaries for testing.
    
    Example:
        position = (PositionBuilder()
                    .with_symbol('AAPL')
                    .with_quantity(100)
                    .with_average_price(150.0)
                    .long()
                    .build())
    """
    
    def __init__(self):
        self._position = {
            'symbol': 'TEST',
            'quantity': 100,
            'average_price': 100.0,
            'side': 'long',
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
        }
    
    def with_symbol(self, symbol: str) -> 'PositionBuilder':
        """Set the symbol."""
        self._position['symbol'] = symbol
        return self
    
    def with_quantity(self, quantity: float) -> 'PositionBuilder':
        """Set the quantity."""
        self._position['quantity'] = quantity
        return self
    
    def with_average_price(self, price: float) -> 'PositionBuilder':
        """Set the average entry price."""
        self._position['average_price'] = price
        return self
    
    def long(self) -> 'PositionBuilder':
        """Set position side to long."""
        self._position['side'] = 'long'
        return self
    
    def short(self) -> 'PositionBuilder':
        """Set position side to short."""
        self._position['side'] = 'short'
        return self
    
    def with_pnl(self, unrealized: float, realized: float = 0.0) -> 'PositionBuilder':
        """Set P&L values."""
        self._position['unrealized_pnl'] = unrealized
        self._position['realized_pnl'] = realized
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the position dictionary."""
        return self._position.copy()


class PortfolioBuilder:
    """
    Builder for creating portfolio state for testing.
    
    Example:
        portfolio = (PortfolioBuilder()
                     .with_cash(100000)
                     .add_position('AAPL', 100, 150.0)
                     .add_position('GOOGL', 50, 2800.0)
                     .build())
    """
    
    def __init__(self):
        self._portfolio = {
            'cash': 100000.0,
            'positions': {},
            'total_value': 100000.0,
        }
    
    def with_cash(self, cash: float) -> 'PortfolioBuilder':
        """Set cash balance."""
        self._portfolio['cash'] = cash
        return self
    
    def add_position(
        self,
        symbol: str,
        quantity: float,
        avg_price: float
    ) -> 'PortfolioBuilder':
        """Add a position to the portfolio."""
        self._portfolio['positions'][symbol] = {
            'quantity': quantity,
            'average_price': avg_price,
            'market_value': quantity * avg_price
        }
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the portfolio dictionary."""
        # Calculate total value
        positions_value = sum(
            p['market_value']
            for p in self._portfolio['positions'].values()
        )
        self._portfolio['total_value'] = self._portfolio['cash'] + positions_value
        
        return self._portfolio.copy()


class SignalBuilder:
    """
    Builder for creating trading signals for testing.
    
    Example:
        signal = (SignalBuilder()
                  .with_symbol('AAPL')
                  .buy()
                  .with_strength(0.8)
                  .with_confidence(0.9)
                  .build())
    """
    
    def __init__(self):
        self._signal = {
            'symbol': 'TEST',
            'direction': 'buy',
            'strength': 0.5,
            'confidence': 0.5,
            'timestamp': datetime.now(),
        }
    
    def with_symbol(self, symbol: str) -> 'SignalBuilder':
        """Set the symbol."""
        self._signal['symbol'] = symbol
        return self
    
    def buy(self) -> 'SignalBuilder':
        """Set direction to buy."""
        self._signal['direction'] = 'buy'
        return self
    
    def sell(self) -> 'SignalBuilder':
        """Set direction to sell."""
        self._signal['direction'] = 'sell'
        return self
    
    def neutral(self) -> 'SignalBuilder':
        """Set direction to neutral."""
        self._signal['direction'] = 'neutral'
        return self
    
    def with_strength(self, strength: float) -> 'SignalBuilder':
        """Set signal strength (0.0 to 1.0)."""
        assert 0.0 <= strength <= 1.0, "Strength must be between 0 and 1"
        self._signal['strength'] = strength
        return self
    
    def with_confidence(self, confidence: float) -> 'SignalBuilder':
        """Set signal confidence (0.0 to 1.0)."""
        assert 0.0 <= confidence <= 1.0, "Confidence must be between 0 and 1"
        self._signal['confidence'] = confidence
        return self
    
    def with_reason(self, reason: str) -> 'SignalBuilder':
        """Add reasoning for the signal."""
        self._signal['reason'] = reason
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and return the signal dictionary."""
        return self._signal.copy()
