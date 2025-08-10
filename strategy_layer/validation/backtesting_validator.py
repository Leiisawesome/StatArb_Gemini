"""
Backtesting Validator

Backtesting implementation for strategy validation.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .strategy_validator import (
    StrategyValidator,
    ValidationConfig,
    ValidationResult,
    Trade,
    PortfolioState
)
from strategy_layer.base import StrategyError, StrategyDefinition


class BacktestingValidator(StrategyValidator):
    """Backtesting validator for strategy validation"""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.trades: List[Trade] = []
        self.portfolio_history: List[PortfolioState] = []
        self.current_positions: Dict[str, float] = {}
        self.cash: float = config.initial_capital
        self.total_value: float = config.initial_capital
        self.peak_value: float = config.initial_capital
    
    def validate_strategy(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """Validate a trading strategy using backtesting"""
        try:
            self.logger.info(f"Starting backtesting validation for strategy: {strategy.config.strategy_id}")
            
            # Initialize backtesting state
            self._initialize_backtesting()
            
            # Get common date range
            common_dates = self._get_common_dates(market_data)
            if len(common_dates) == 0:
                raise StrategyError("No common dates found in market data")
            
            # Run backtesting
            self._run_backtesting(strategy, market_data, common_dates)
            
            # Calculate final metrics
            result = self._calculate_validation_result(strategy, market_data)
            
            self.logger.info(f"Backtesting completed. Total trades: {len(self.trades)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in backtesting validation: {e}")
            raise StrategyError(f"Backtesting validation failed: {e}")
    
    def _initialize_backtesting(self):
        """Initialize backtesting state"""
        self.trades = []
        self.portfolio_history = []
        self.current_positions = {}
        self.cash = self.config.initial_capital
        self.total_value = self.config.initial_capital
        self.peak_value = self.config.initial_capital
    
    def _get_common_dates(self, market_data: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Get common dates across all market data"""
        date_sets = []
        for symbol, data in market_data.items():
            if not data.empty:
                date_sets.append(set(data.index))
        
        if not date_sets:
            return pd.DatetimeIndex([])
        
        common_dates = set.intersection(*date_sets)
        filtered_dates = [d for d in common_dates if self.config.start_date <= d <= self.config.end_date]
        
        return pd.DatetimeIndex(sorted(filtered_dates))
    
    def _run_backtesting(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame], dates: pd.DatetimeIndex):
        """Run the backtesting simulation"""
        for date in dates:
            try:
                # Get market data for current date
                current_data = {}
                for symbol, data in market_data.items():
                    if date in data.index:
                        current_data[symbol] = data.loc[:date]  # Data up to current date
                
                if not current_data:
                    continue
                
                # Update portfolio value
                self._update_portfolio_value(current_data, date)
                
                # Check for exit signals on existing positions
                self._check_exit_signals(strategy, current_data, date)
                
                # Check for entry signals
                self._check_entry_signals(strategy, current_data, date)
                
                # Record portfolio state
                self._record_portfolio_state(date)
                
            except Exception as e:
                self.logger.warning(f"Error processing date {date}: {e}")
                continue
    
    def _update_portfolio_value(self, current_data: Dict[str, pd.DataFrame], date: datetime):
        """Update portfolio value based on current positions"""
        unrealized_pnl = 0.0
        
        for symbol, position in self.current_positions.items():
            if symbol in current_data and not current_data[symbol].empty:
                current_price = current_data[symbol]['close'].iloc[-1]
                unrealized_pnl += position * current_price
        
        self.total_value = self.cash + unrealized_pnl
        self.peak_value = max(self.peak_value, self.total_value)
    
    def _check_exit_signals(self, strategy: StrategyDefinition, current_data: Dict[str, pd.DataFrame], date: datetime):
        """Check for exit signals on existing positions"""
        for symbol, position in list(self.current_positions.items()):
            if symbol not in current_data:
                continue
            
            data = current_data[symbol]
            if data.empty:
                continue
            
            current_price = data['close'].iloc[-1]
            
            # Check stop loss and take profit
            for trade in self.trades:
                if trade.symbol == symbol and trade.exit_date is None:
                    # Check stop loss
                    if trade.stop_loss and current_price <= trade.stop_loss:
                        self._close_trade(trade, current_price, date, "STOP_LOSS")
                    
                    # Check take profit
                    elif trade.take_profit and current_price >= trade.take_profit:
                        self._close_trade(trade, current_price, date, "TAKE_PROFIT")
                    
                    # Check strategy exit signal
                    elif strategy.should_exit_position(symbol, position, data.to_dict()):
                        self._close_trade(trade, current_price, date, "STRATEGY_SIGNAL")
    
    def _check_entry_signals(self, strategy: StrategyDefinition, current_data: Dict[str, pd.DataFrame], date: datetime):
        """Check for entry signals"""
        for symbol, data in current_data.items():
            if symbol in self.current_positions:
                continue  # Already have position
            
            # Check if should enter position
            signals = strategy.generate_signals(data.to_dict())
            if not signals:
                continue
            
            # Combine signals
            combined_signal = sum(signals.values()) / len(signals)
            
            if strategy.should_enter_position(symbol, combined_signal, data.to_dict()):
                # Calculate position size
                position_sizes = strategy.calculate_position_sizes(signals, data.to_dict())
                if not position_sizes:
                    continue
                
                position_size = list(position_sizes.values())[0]
                if position_size <= 0:
                    continue
                
                # Check risk limits
                if not strategy.validate_risk({symbol: position_size}, data.to_dict()):
                    continue
                
                # Execute trade
                self._execute_trade(symbol, position_size, data, date, strategy)
    
    def _execute_trade(self, symbol: str, position_size: float, data: pd.DataFrame, date: datetime, strategy: StrategyDefinition):
        """Execute a new trade"""
        current_price = data['close'].iloc[-1]
        
        # Calculate trade value
        trade_value = position_size * self.total_value
        shares = trade_value / current_price
        
        # Check if we have enough cash
        if trade_value > self.cash:
            return
        
        # Calculate costs
        commission = trade_value * self.config.commission_rate
        slippage = trade_value * self.config.slippage_rate
        total_cost = trade_value + commission + slippage
        
        # Update cash and positions
        self.cash -= total_cost
        self.current_positions[symbol] = shares
        
        # Create trade record
        trade = Trade(
            symbol=symbol,
            entry_date=date,
            entry_price=current_price,
            position_size=shares,
            side="LONG" if shares > 0 else "SHORT",
            commission=commission,
            slippage=slippage,
            stop_loss=current_price * (1 - self.config.stop_loss) if shares > 0 else current_price * (1 + self.config.stop_loss),
            take_profit=current_price * (1 + self.config.take_profit) if shares > 0 else current_price * (1 - self.config.take_profit)
        )
        
        self.trades.append(trade)
        self.logger.debug(f"Opened trade: {symbol} at {current_price:.2f}")
    
    def _close_trade(self, trade: Trade, exit_price: float, date: datetime, reason: str):
        """Close an existing trade"""
        # Calculate P&L
        if trade.side == "LONG":
            pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            pnl = (trade.entry_price - exit_price) * abs(trade.position_size)
        
        # Calculate costs
        trade_value = exit_price * trade.position_size
        commission = trade_value * self.config.commission_rate
        slippage = trade_value * self.config.slippage_rate
        total_cost = commission + slippage
        
        # Update trade record
        trade.exit_date = date
        trade.exit_price = exit_price
        trade.pnl = pnl - total_cost
        trade.pnl_pct = trade.pnl / (trade.entry_price * trade.position_size)
        trade.commission += commission
        trade.slippage += slippage
        trade.exit_reason = reason
        
        # Update portfolio
        self.cash += trade_value - total_cost
        self.current_positions.pop(trade.symbol, None)
        
        self.logger.debug(f"Closed trade: {trade.symbol} at {exit_price:.2f}, P&L: {trade.pnl:.2f}")
    
    def _record_portfolio_state(self, date: datetime):
        """Record current portfolio state"""
        state = PortfolioState(
            date=date,
            total_value=self.total_value,
            cash=self.cash,
            positions=self.current_positions.copy(),
            unrealized_pnl=self.total_value - self.cash,
            realized_pnl=sum(t.pnl for t in self.trades if t.exit_date is not None),
            total_commission=sum(t.commission for t in self.trades),
            total_slippage=sum(t.slippage for t in self.trades)
        )
        
        self.portfolio_history.append(state)
    
    def _calculate_validation_result(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """Calculate validation result from backtesting data"""
        # Calculate portfolio returns
        portfolio_values = pd.Series([state.total_value for state in self.portfolio_history],
                                   index=[state.date for state in self.portfolio_history])
        
        if len(portfolio_values) < 2:
            raise StrategyError("Insufficient data for validation")
        
        portfolio_returns = self._calculate_returns(portfolio_values)
        
        # Calculate benchmark returns
        benchmark_returns = self._calculate_benchmark_returns(market_data)
        
        # Calculate performance metrics
        total_return = (self.total_value - self.config.initial_capital) / self.config.initial_capital
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1 if len(portfolio_returns) > 0 else 0.0
        sharpe_ratio = self._calculate_sharpe_ratio(portfolio_returns)
        sortino_ratio = self._calculate_sortino_ratio(portfolio_returns)
        max_drawdown = self._calculate_max_drawdown(portfolio_values)
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0.0
        
        # Calculate risk metrics
        volatility = portfolio_returns.std() * np.sqrt(252) if len(portfolio_returns) > 0 else 0.0
        var_95, cvar_95 = self._calculate_var_cvar(portfolio_returns)
        beta, alpha = self._calculate_beta_alpha(portfolio_returns, benchmark_returns)
        
        # Calculate trading metrics
        closed_trades = [t for t in self.trades if t.exit_date is not None]
        trade_metrics = self._calculate_trade_metrics(closed_trades)
        
        # Create validation result
        result = ValidationResult(
            strategy_id=strategy.config.strategy_id,
            strategy_name=strategy.config.name,
            validation_period=(self.config.start_date, self.config.end_date),
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            var_95=var_95,
            cvar_95=cvar_95,
            beta=beta,
            alpha=alpha,
            total_trades=trade_metrics['total_trades'],
            winning_trades=trade_metrics['winning_trades'],
            losing_trades=trade_metrics['losing_trades'],
            win_rate=trade_metrics['win_rate'],
            avg_win=trade_metrics['avg_win'],
            avg_loss=trade_metrics['avg_loss'],
            profit_factor=trade_metrics['profit_factor'],
            final_value=self.total_value,
            peak_value=self.peak_value,
            final_positions=self.current_positions.copy(),
            trades=self.trades,
            portfolio_history=self.portfolio_history,
            benchmark_returns=benchmark_returns.tolist() if len(benchmark_returns) > 0 else [],
            config=self.config
        )
        
        return result
    
    def _calculate_benchmark_returns(self, market_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate benchmark returns"""
        if self.config.benchmark_symbol not in market_data:
            return pd.Series(dtype=float)
        
        benchmark_data = market_data[self.config.benchmark_symbol]
        if benchmark_data.empty:
            return pd.Series(dtype=float)
        
        # Filter to validation period
        mask = (benchmark_data.index >= self.config.start_date) & (benchmark_data.index <= self.config.end_date)
        filtered_data = benchmark_data[mask]
        
        if len(filtered_data) < 2:
            return pd.Series(dtype=float)
        
        return self._calculate_returns(filtered_data['close'])
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """Get summary of trades"""
        if not self.trades:
            return {}
        
        closed_trades = [t for t in self.trades if t.exit_date is not None]
        open_trades = [t for t in self.trades if t.exit_date is None]
        
        return {
            'total_trades': len(self.trades),
            'closed_trades': len(closed_trades),
            'open_trades': len(open_trades),
            'total_pnl': sum(t.pnl for t in closed_trades),
            'total_commission': sum(t.commission for t in self.trades),
            'total_slippage': sum(t.slippage for t in self.trades),
            'avg_trade_duration': np.mean([(t.exit_date - t.entry_date).days for t in closed_trades]) if closed_trades else 0
        }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get summary of portfolio performance"""
        if not self.portfolio_history:
            return {}
        
        initial_value = self.config.initial_capital
        final_value = self.total_value
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': (final_value - initial_value) / initial_value,
            'peak_value': self.peak_value,
            'max_drawdown': self._calculate_max_drawdown(pd.Series([state.total_value for state in self.portfolio_history])),
            'current_cash': self.cash,
            'current_positions': self.current_positions
        }
