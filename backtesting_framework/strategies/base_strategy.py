"""
Base Strategy Class for Backtesting Framework

Provides the foundation for all trading strategies with common functionality
and required interface methods.
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal types"""
    LONG = 1
    SHORT = -1
    HOLD = 0
    CLOSE_LONG = 2
    CLOSE_SHORT = -2

@dataclass
class TradingSignal:
    """Standardized trading signal structure"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    price: float
    volume: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Position information"""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: float
    pnl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Base configuration for strategies"""
    # Required fields (no defaults)
    symbols: List[str]
    
    # Optional fields (with defaults)
    name: str = "Base Strategy"
    version: str = "1.0.0"
    
    # Capital and position management
    initial_capital: float = 100000.0  # $100K default capital
    position_size: float = 0.1
    max_positions: int = 10
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_drawdown: float = 0.2
    
    # Execution parameters
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    
    # Data parameters
    lookback_window: int = 60
    min_data_points: int = 100
    
    # Performance tracking
    benchmark_symbol: Optional[str] = None
    risk_free_rate: float = 0.02

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Provides common functionality and enforces required interface methods.
    """
    
    def __init__(self, config: StrategyConfig):
        """
        Initialize the base strategy
        
        Args:
            config: Strategy configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Portfolio state
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.portfolio_value = config.initial_capital
        self.initial_capital = config.initial_capital  # Track for return calculations
        self.equity_curve: List[float] = [config.initial_capital]
        
        # Performance tracking
        self.returns: List[float] = []
        self.trades: List[Dict[str, Any]] = []
        
        # Market data storage
        self.market_data: Dict[str, pd.DataFrame] = {}
        
        # Signal tracking
        self.signals: List = []
        
        # Risk management
        self.max_position_size = getattr(config, 'max_position_size', 0.1)
        self.stop_loss_threshold = getattr(config, 'stop_loss_threshold', 0.05)
        
        self.logger.info(f"Strategy initialized: {config.name}")
        self.logger.info(f"Initial capital: ${config.initial_capital:,.2f}")
    
    def _validate_config(self):
        """Validate strategy configuration"""
        if not self.config.symbols:
            raise ValueError("At least one symbol must be specified")
        
        if self.config.position_size <= 0 or self.config.position_size > 1:
            raise ValueError("Position size must be between 0 and 1")
        
        if self.config.max_drawdown <= 0 or self.config.max_drawdown > 1:
            raise ValueError("Max drawdown must be between 0 and 1")
    
    @abstractmethod
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Generate trading signals based on market data
        
        Args:
            data: Dictionary mapping symbols to DataFrames with OHLCV data
            
        Returns:
            List of trading signals
        """
        pass
    
    @abstractmethod
    def calculate_positions(self, signals: List[TradingSignal], 
                          current_positions: Dict[str, Position],
                          available_cash: float) -> Dict[str, float]:
        """
        Calculate target positions based on signals and current positions
        
        Args:
            signals: List of current trading signals
            current_positions: Current portfolio positions
            available_cash: Available cash for trading
            
        Returns:
            Dictionary mapping symbols to target position sizes
        """
        pass
    
    def update_market_data(self, data: Dict[str, pd.DataFrame]):
        """
        Update market data for the strategy
        
        Args:
            data: Dictionary mapping symbols to DataFrames
        """
        self.market_data.update(data)
        
        # Generate features if needed (optional method)
        try:
            if hasattr(self, 'generate_features'):
                self.features = self.generate_features(data)
        except AttributeError:
            pass  # generate_features method is optional
    
    def process_signals(self, timestamp: datetime, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Process market data and generate signals
        
        Args:
            timestamp: Current timestamp
            data: Market data for all symbols
            
        Returns:
            List of trading signals
        """
        # Update market data
        self.update_market_data(data)
        
        # Generate signals
        signals = self.generate_signals(data)
        
        # Add timestamp if not present
        for signal in signals:
            if not hasattr(signal, 'timestamp') or signal.timestamp is None:
                signal.timestamp = timestamp
        
        # Store signals
        self.signals.extend(signals)
        
        return signals
    
    def execute_trades(self, signals: List[TradingSignal], 
                      current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Execute trades based on signals and current prices
        
        Args:
            signals: List of trading signals
            current_prices: Current prices for all symbols
            
        Returns:
            List of executed trades
        """
        trades = []
        
        # Calculate target positions
        target_positions = self.calculate_positions(signals, self.positions, self.cash)
        
        # Execute position changes
        for symbol, target_size in target_positions.items():
            current_position = self.positions.get(symbol)
            current_size = current_position.quantity if current_position else 0
            
            if abs(target_size - current_size) > 1e-6:  # Significant change
                trade = self._execute_position_change(
                    symbol, current_size, target_size, current_prices[symbol]
                )
                if trade:
                    trades.append(trade)
        
        return trades
    
    def _execute_position_change(self, symbol: str, current_size: float, 
                               target_size: float, price: float) -> Optional[Dict[str, Any]]:
        """
        Execute a position change for a single symbol
        
        Args:
            symbol: Symbol to trade
            current_size: Current position size
            target_size: Target position size
            price: Current price
            
        Returns:
            Trade information or None if no trade
        """
        size_change = target_size - current_size
        
        if abs(size_change) < 1e-6:  # No significant change
            return None
        
        # Calculate trade details
        trade_value = abs(size_change) * price
        commission = trade_value * self.config.commission_rate
        slippage = trade_value * self.config.slippage_rate
        total_cost = trade_value + commission + slippage
        
        # Check if we have enough cash
        if size_change > 0 and total_cost > self.cash:
            self.logger.warning(f"Insufficient cash for {symbol} trade: need {total_cost:.2f}, have {self.cash:.2f}")
            return None
        
        # Execute trade
        if size_change > 0:  # Buy
            self.cash -= total_cost
            if symbol in self.positions:
                # Add to existing position
                current_pos = self.positions[symbol]
                total_quantity = current_pos.quantity + size_change
                avg_price = ((current_pos.quantity * current_pos.entry_price) + 
                           (size_change * price)) / total_quantity
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=total_quantity,
                    entry_price=avg_price,
                    entry_time=datetime.now(),
                    current_price=price
                )
            else:
                # New position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=size_change,
                    entry_price=price,
                    entry_time=datetime.now(),
                    current_price=price
                )
        else:  # Sell
            self.cash += trade_value - commission - slippage
            if symbol in self.positions:
                current_pos = self.positions[symbol]
                new_quantity = current_pos.quantity + size_change
                if new_quantity <= 0:
                    # Close position
                    del self.positions[symbol]
                else:
                    # Reduce position
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=new_quantity,
                        entry_price=current_pos.entry_price,
                        entry_time=current_pos.entry_time,
                        current_price=price
                    )
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'action': 'BUY' if size_change > 0 else 'SELL',
            'quantity': abs(size_change),
            'price': price,
            'value': trade_value,
            'commission': commission,
            'slippage': slippage,
            'total_cost': total_cost
        }
        
        self.trades.append(trade)
        return trade
    
    def update_portfolio_value(self, current_prices: Dict[str, float]):
        """
        Update portfolio value based on current prices
        
        Args:
            current_prices: Current prices for all symbols
        """
        # Update position prices
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position.current_price = current_prices[symbol]
                position.pnl = (position.current_price - position.entry_price) * position.quantity
        
        # Calculate total portfolio value
        position_value = sum(pos.quantity * pos.current_price for pos in self.positions.values())
        total_value = self.cash + position_value
        
        # Calculate return
        if self.portfolio_value > 0:
            return_rate = (total_value - self.portfolio_value) / self.portfolio_value
            self.returns.append(return_rate)
        
        self.portfolio_value = total_value
        self.equity_curve.append(total_value)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Calculate performance metrics
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.returns:
            return {
                'total_return': 0.0,
                'annualized_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': len(self.trades)
            }
        
        returns = np.array(self.returns)
        
        # Calculate total return using initial capital
        total_return = (self.portfolio_value - self.initial_capital) / self.initial_capital
        
        metrics = {
            'total_return': total_return,
            'annualized_return': self._calculate_annualized_return(returns),
            'volatility': np.std(returns) * np.sqrt(252),
            'sharpe_ratio': self._calculate_sharpe_ratio(returns),
            'max_drawdown': self._calculate_max_drawdown(),
            'win_rate': np.mean(returns > 0) if len(returns) > 0 else 0.0,
            'profit_factor': self._calculate_profit_factor(returns),
            'total_trades': len(self.trades)
        }
        
        return metrics
    
    def _calculate_annualized_return(self, returns: np.ndarray) -> float:
        """Calculate annualized return"""
        if len(returns) == 0:
            return 0.0
        total_return = (1 + returns).prod() - 1
        return (1 + total_return) ** (252 / len(returns)) - 1
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        excess_returns = returns - self.config.risk_free_rate / 252
        return np.mean(excess_returns) / np.std(returns) * np.sqrt(252)
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        equity = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        return np.min(drawdown)
    
    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """Calculate profit factor"""
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]
        
        if len(winning_returns) == 0 or len(losing_returns) == 0:
            return 0.0
        
        return np.sum(winning_returns) / abs(np.sum(losing_returns))
    
    def reset(self):
        """Reset strategy state for new backtest"""
        self.positions.clear()
        self.signals.clear()
        self.trades.clear()
        self.portfolio_value = 1.0
        self.cash = 1.0
        self.returns.clear()
        self.equity_curve = [1.0]
        self.market_data.clear()
        self.features.clear()
        
        self.logger.info("Strategy state reset")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current strategy state
        
        Returns:
            Dictionary containing strategy state
        """
        return {
            'positions': {sym: {
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'pnl': pos.pnl
            } for sym, pos in self.positions.items()},
            'cash': self.cash,
            'portfolio_value': self.portfolio_value,
            'total_trades': len(self.trades),
            'total_signals': len(self.signals)
        } 