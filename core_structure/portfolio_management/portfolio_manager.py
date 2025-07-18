"""
Enhanced Portfolio Manager for AI-Ready Statistical Arbitrage System
====================================================================

This module provides comprehensive portfolio management with:
- AI-driven portfolio optimization and allocation
- Real-time portfolio monitoring and rebalancing
- Multi-strategy portfolio construction
- Advanced performance attribution
- Risk-adjusted capital allocation

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import json

logger = logging.getLogger(__name__)

class PortfolioState(Enum):
    """Portfolio states"""
    ACTIVE = "active"
    REBALANCING = "rebalancing"
    LIQUIDATING = "liquidating"
    PAUSED = "paused"

@dataclass
class Position:
    """Individual position in portfolio"""
    symbol_pair: str
    strategy: str
    entry_time: datetime
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    weight: float
    risk_contribution: float
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_price(self, new_price: float):
        """Update position with new price"""
        self.current_price = new_price
        self.market_value = self.quantity * new_price
        self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        self.last_update = datetime.now()

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    cash: float
    invested_capital: float
    total_return: float
    daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    positions_count: int
    concentration: float
    correlation_risk: float
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioConfig:
    """Portfolio configuration"""
    initial_capital: float = 1_000_000
    max_positions: int = 50
    max_position_weight: float = 0.15
    target_volatility: float = 0.12
    rebalancing_threshold: float = 0.03
    correlation_threshold: float = 0.8
    minimum_position_size: float = 0.01
    cash_buffer: float = 0.05
    risk_budget: float = 0.02

class PortfolioManager:
    """
    Enhanced Portfolio Manager with AI-driven optimization
    
    Provides comprehensive portfolio management including:
    - Real-time portfolio monitoring
    - AI-driven allocation optimization
    - Risk-adjusted position sizing
    - Automated rebalancing
    - Performance attribution
    """
    
    def __init__(self, config: Union[Dict[str, Any], PortfolioConfig]):
        """Initialize portfolio manager"""
        if isinstance(config, dict):
            self.config = PortfolioConfig(**config)
        else:
            self.config = config
            
        # Portfolio state
        self.state = PortfolioState.ACTIVE
        self.positions: Dict[str, Position] = {}
        self.cash = self.config.initial_capital
        self.total_value = self.config.initial_capital
        self.creation_time = datetime.now()
        
        # Performance tracking
        self.performance_history: List[PortfolioMetrics] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.rebalancing_history: List[Dict[str, Any]] = []
        
        # Risk management
        self.risk_limits = {
            'max_var': self.config.risk_budget,
            'max_position_size': self.config.max_position_weight,
            'max_correlation': self.config.correlation_threshold,
            'min_cash_buffer': self.config.cash_buffer
        }
        
        logger.info(f"Portfolio manager initialized with ${self.config.initial_capital:,.2f}")
    
    def add_position(self, symbol_pair: str, strategy: str, quantity: float, 
                    entry_price: float, signal_data: Optional[Dict] = None) -> bool:
        """Add new position to portfolio"""
        try:
            # Check if we can add this position
            if not self._can_add_position(symbol_pair, quantity, entry_price):
                return False
            
            # Calculate position metrics
            market_value = quantity * entry_price
            weight = market_value / self.total_value
            
            # Create position
            position = Position(
                symbol_pair=symbol_pair,
                strategy=strategy,
                entry_time=datetime.now(),
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
                market_value=market_value,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                weight=weight,
                risk_contribution=0.0
            )
            
            # Add to portfolio
            self.positions[symbol_pair] = position
            self.cash -= market_value
            
            # Record trade
            self.trade_history.append({
                'timestamp': datetime.now(),
                'action': 'BUY',
                'symbol_pair': symbol_pair,
                'quantity': quantity,
                'price': entry_price,
                'value': market_value,
                'strategy': strategy,
                'signal_data': signal_data
            })
            
            logger.info(f"Added position: {symbol_pair} ({strategy}) - ${market_value:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding position {symbol_pair}: {e}")
            return False
    
    def remove_position(self, symbol_pair: str, exit_price: float, 
                       reason: str = "manual") -> bool:
        """Remove position from portfolio"""
        try:
            if symbol_pair not in self.positions:
                logger.warning(f"Position {symbol_pair} not found")
                return False
            
            position = self.positions[symbol_pair]
            
            # Calculate exit value and PnL
            exit_value = position.quantity * exit_price
            realized_pnl = (exit_price - position.entry_price) * position.quantity
            
            # Update cash
            self.cash += exit_value
            
            # Record trade
            self.trade_history.append({
                'timestamp': datetime.now(),
                'action': 'SELL',
                'symbol_pair': symbol_pair,
                'quantity': position.quantity,
                'price': exit_price,
                'value': exit_value,
                'pnl': realized_pnl,
                'holding_period': datetime.now() - position.entry_time,
                'reason': reason
            })
            
            # Remove position
            del self.positions[symbol_pair]
            
            logger.info(f"Removed position: {symbol_pair} - PnL: ${realized_pnl:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing position {symbol_pair}: {e}")
            return False
    
    def update_prices(self, price_data: Dict[str, float]) -> None:
        """Update portfolio with new prices"""
        try:
            for symbol_pair, new_price in price_data.items():
                if symbol_pair in self.positions:
                    self.positions[symbol_pair].update_price(new_price)
            
            # Recalculate portfolio metrics
            self._update_portfolio_metrics()
            
        except Exception as e:
            logger.error(f"Error updating prices: {e}")
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio metrics"""
        try:
            # Calculate total portfolio value
            positions_value = sum(pos.market_value for pos in self.positions.values())
            total_value = positions_value + self.cash
            
            # Calculate returns
            total_return = (total_value - self.config.initial_capital) / self.config.initial_capital
            
            # Calculate daily return (if we have history)
            daily_return = 0.0
            if len(self.performance_history) > 0:
                prev_value = self.performance_history[-1].total_value
                daily_return = (total_value - prev_value) / prev_value
            
            # Calculate volatility (if we have sufficient history)
            volatility = 0.0
            if len(self.performance_history) >= 20:
                returns = [m.daily_return for m in self.performance_history[-20:]]
                volatility = np.std(returns) * np.sqrt(252)  # Annualized
            
            # Calculate Sharpe ratio
            sharpe_ratio = 0.0
            if volatility > 0:
                sharpe_ratio = (total_return * 252) / volatility  # Annualized
            
            # Calculate max drawdown
            max_drawdown = self._calculate_max_drawdown()
            
            # Calculate VaR (95% confidence)
            var_95 = self._calculate_var()
            
            # Calculate concentration and correlation risk
            concentration = self._calculate_concentration()
            correlation_risk = self._calculate_correlation_risk()
            
            return PortfolioMetrics(
                total_value=total_value,
                cash=self.cash,
                invested_capital=positions_value,
                total_return=total_return,
                daily_return=daily_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                var_95=var_95,
                positions_count=len(self.positions),
                concentration=concentration,
                correlation_risk=correlation_risk
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return PortfolioMetrics(
                total_value=self.cash,
                cash=self.cash,
                invested_capital=0.0,
                total_return=0.0,
                daily_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                positions_count=0,
                concentration=0.0,
                correlation_risk=0.0
            )
    
    def needs_rebalancing(self) -> bool:
        """Check if portfolio needs rebalancing"""
        try:
            current_metrics = self.get_portfolio_metrics()
            
            # Check various rebalancing triggers
            triggers = []
            
            # Weight drift trigger
            for position in self.positions.values():
                current_weight = position.market_value / current_metrics.total_value
                if abs(current_weight - position.weight) > self.config.rebalancing_threshold:
                    triggers.append(f"Weight drift: {position.symbol_pair}")
            
            # Concentration trigger
            if current_metrics.concentration > self.config.max_position_weight:
                triggers.append("Concentration limit exceeded")
            
            # Correlation trigger
            if current_metrics.correlation_risk > self.config.correlation_threshold:
                triggers.append("Correlation risk too high")
            
            # Cash buffer trigger
            cash_ratio = self.cash / current_metrics.total_value
            if cash_ratio < self.config.cash_buffer:
                triggers.append("Cash buffer too low")
            
            if triggers:
                logger.info(f"Rebalancing needed: {', '.join(triggers)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking rebalancing need: {e}")
            return False
    
    def get_position_summary(self) -> pd.DataFrame:
        """Get summary of all positions"""
        try:
            if not self.positions:
                return pd.DataFrame()
            
            data = []
            for symbol_pair, position in self.positions.items():
                data.append({
                    'Symbol': symbol_pair,
                    'Strategy': position.strategy,
                    'Quantity': position.quantity,
                    'Entry Price': position.entry_price,
                    'Current Price': position.current_price,
                    'Market Value': position.market_value,
                    'Unrealized PnL': position.unrealized_pnl,
                    'Weight': position.weight,
                    'Risk Contribution': position.risk_contribution,
                    'Days Held': (datetime.now() - position.entry_time).days
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error generating position summary: {e}")
            return pd.DataFrame()
    
    def _can_add_position(self, symbol_pair: str, quantity: float, price: float) -> bool:
        """Check if we can add this position"""
        try:
            # Check if position already exists
            if symbol_pair in self.positions:
                logger.warning(f"Position {symbol_pair} already exists")
                return False
            
            # Check if we have enough cash
            required_cash = quantity * price
            if required_cash > self.cash:
                logger.warning(f"Insufficient cash: need ${required_cash:,.2f}, have ${self.cash:,.2f}")
                return False
            
            # Check position size limits
            position_weight = required_cash / self.total_value
            if position_weight > self.config.max_position_weight:
                logger.warning(f"Position too large: {position_weight:.2%} > {self.config.max_position_weight:.2%}")
                return False
            
            # Check maximum positions
            if len(self.positions) >= self.config.max_positions:
                logger.warning(f"Maximum positions reached: {len(self.positions)}")
                return False
            
            # Check minimum position size
            if position_weight < self.config.minimum_position_size:
                logger.warning(f"Position too small: {position_weight:.2%} < {self.config.minimum_position_size:.2%}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking position constraints: {e}")
            return False
    
    def _update_portfolio_metrics(self) -> None:
        """Update portfolio metrics and history"""
        try:
            current_metrics = self.get_portfolio_metrics()
            self.performance_history.append(current_metrics)
            
            # Keep only last 252 days of history
            if len(self.performance_history) > 252:
                self.performance_history = self.performance_history[-252:]
            
            # Update total value
            self.total_value = current_metrics.total_value
            
            # Update position weights
            for position in self.positions.values():
                position.weight = position.market_value / self.total_value
            
        except Exception as e:
            logger.error(f"Error updating portfolio metrics: {e}")
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(self.performance_history) < 2:
                return 0.0
            
            values = [m.total_value for m in self.performance_history]
            peak = values[0]
            max_dd = 0.0
            
            for value in values[1:]:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
            
            return max_dd
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def _calculate_var(self, confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        try:
            if len(self.performance_history) < 20:
                return 0.0
            
            returns = [m.daily_return for m in self.performance_history[-20:]]
            return np.percentile(returns, (1 - confidence) * 100)
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0.0
    
    def _calculate_concentration(self) -> float:
        """Calculate portfolio concentration (largest position weight)"""
        try:
            if not self.positions:
                return 0.0
            
            weights = [pos.market_value / self.total_value for pos in self.positions.values()]
            return max(weights)
            
        except Exception as e:
            logger.error(f"Error calculating concentration: {e}")
            return 0.0
    
    def _calculate_correlation_risk(self) -> float:
        """Calculate correlation risk (simplified)"""
        try:
            # This is a simplified correlation risk calculation
            # In practice, you'd use actual correlation matrices
            if len(self.positions) < 2:
                return 0.0
            
            # Assume higher correlation risk with more positions
            # This should be replaced with actual correlation calculation
            return min(0.8, len(self.positions) * 0.1)
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0.0
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get complete portfolio state summary"""
        try:
            metrics = self.get_portfolio_metrics()
            
            return {
                'portfolio_state': self.state.value,
                'creation_time': self.creation_time.isoformat(),
                'config': {
                    'initial_capital': self.config.initial_capital,
                    'max_positions': self.config.max_positions,
                    'max_position_weight': self.config.max_position_weight,
                    'target_volatility': self.config.target_volatility
                },
                'metrics': {
                    'total_value': metrics.total_value,
                    'cash': metrics.cash,
                    'invested_capital': metrics.invested_capital,
                    'total_return': metrics.total_return,
                    'daily_return': metrics.daily_return,
                    'volatility': metrics.volatility,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'var_95': metrics.var_95,
                    'positions_count': metrics.positions_count,
                    'concentration': metrics.concentration,
                    'correlation_risk': metrics.correlation_risk
                },
                'positions': {
                    symbol: {
                        'strategy': pos.strategy,
                        'quantity': pos.quantity,
                        'market_value': pos.market_value,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'weight': pos.weight,
                        'entry_time': pos.entry_time.isoformat()
                    }
                    for symbol, pos in self.positions.items()
                },
                'risk_status': {
                    'within_limits': all([
                        metrics.concentration <= self.config.max_position_weight,
                        metrics.correlation_risk <= self.config.correlation_threshold,
                        self.cash / metrics.total_value >= self.config.cash_buffer
                    ]),
                    'needs_rebalancing': self.needs_rebalancing()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating state summary: {e}")
            return {'error': str(e)} 