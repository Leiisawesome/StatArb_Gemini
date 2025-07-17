"""
Simplified and clean backtesting module
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BacktestResults:
    """
    Container for backtest results and performance metrics
    """
    
    def __init__(self):
        """Initialize empty results container"""
        self.portfolio_history = []
        self.trade_history = []
        self.performance_metrics = {}
        
    def get_portfolio_dataframe(self) -> pd.DataFrame:
        """Convert portfolio history to DataFrame"""
        if not self.portfolio_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.portfolio_history)
        if 'date' in df.columns:
            df.set_index('date', inplace=True)
        return df
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Convert trade history to DataFrame"""
        if not self.trade_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trade_history)
        if 'date' in df.columns:
            df.set_index('date', inplace=True)
        return df

class MomentumBacktest:
    """
    Production-grade momentum backtesting engine
    """
    
    def __init__(self, strategy, risk_manager, config: Dict[str, Any]):
        """
        Initialize backtest engine
        
        Args:
            strategy: Trading strategy instance
            risk_manager: Risk management instance
            config: Configuration dictionary
        """
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.config = config
        
        # Backtest parameters
        backtest_config = config.get('backtesting', {})
        self.initial_capital = backtest_config.get('initial_capital', 100000.0)
        self.commission_rate = backtest_config.get('commission_rate', 0.001)
        self.market_impact = backtest_config.get('market_impact', 0.0005)
        self.slippage = backtest_config.get('slippage', 0.0001)
        
        logger.info(f"MomentumBacktest initialized with ${self.initial_capital:,.2f} capital")
    
    def run(self, training_data: pd.DataFrame, testing_data: pd.DataFrame) -> BacktestResults:
        """
        Run complete backtest on provided data
        
        Args:
            training_data: Historical data for strategy training
            testing_data: Data for backtesting
            
        Returns:
            BacktestResults with comprehensive performance metrics
        """
        logger.info("Starting momentum backtest run...")
        
        # Initialize results
        results = BacktestResults()
        
        # Initialize portfolio state
        current_cash = self.initial_capital
        positions = {}  # {symbol: shares}
        
        # Get unique dates in testing period
        test_dates = testing_data.index.get_level_values('date').unique().sort_values()
        
        logger.info(f"Running backtest over {len(test_dates)} trading dates")
        
        for date in test_dates:
            try:
                # Get available data up to current date
                historical_data = testing_data[
                    testing_data.index.get_level_values('date') <= date
                ]
                
                # Generate trading signals
                signals = self.strategy.generate_signals(historical_data, date)
                
                # Get current prices for the date
                current_prices = self._get_current_prices(testing_data, date)
                
                if signals and current_prices:
                    # Calculate current portfolio value
                    portfolio_value = current_cash + sum(
                        positions.get(symbol, 0) * current_prices.get(symbol, 0)
                        for symbol in positions
                    )
                    
                    # Apply risk management and calculate position sizes
                    position_sizes = self.risk_manager.calculate_position_sizes(
                        signals, current_prices, current_cash
                    )
                    
                    # Execute trades
                    current_cash, positions = self._execute_trades(
                        position_sizes, positions, current_cash, current_prices, date, results
                    )
                
                # Record portfolio state
                self._record_portfolio_state(results, date, positions, current_cash, testing_data)
                
            except Exception as e:
                logger.warning(f"Error processing date {date}: {e}")
                continue
        
        logger.info(f"Backtest completed. Processed {len(results.portfolio_history)} days")
        logger.info(f"Executed {len(results.trade_history)} trades")
        
        return results
    
    def _get_current_prices(self, data: pd.DataFrame, date: pd.Timestamp) -> Dict[str, float]:
        """Get current prices for all symbols on given date"""
        try:
            current_data = data.xs(date, level='date', drop_level=False)
            prices = {}
            for (_, symbol), row in current_data.iterrows():
                prices[symbol] = row['close']
            return prices
        except KeyError:
            return {}
    
    def _execute_trades(self, position_sizes: Dict[str, float], current_positions: Dict[str, int],
                       current_cash: float, current_prices: Dict[str, float], date: pd.Timestamp,
                       results: BacktestResults) -> tuple:
        """Execute trades based on position sizes"""
        new_cash = current_cash
        new_positions = current_positions.copy()
        
        for symbol, target_position_value in position_sizes.items():
            if symbol not in current_prices or current_prices[symbol] <= 0:
                continue
            
            current_price = current_prices[symbol]
            target_shares = int(target_position_value / current_price)
            current_shares = current_positions.get(symbol, 0)
            
            if target_shares != current_shares:
                trade_shares = target_shares - current_shares
                trade_value = abs(trade_shares) * current_price
                
                # Calculate transaction costs
                commission = trade_value * self.commission_rate
                market_impact_cost = trade_value * self.market_impact
                slippage_cost = trade_value * self.slippage
                total_cost = commission + market_impact_cost + slippage_cost
                
                # Execute trade
                if trade_shares > 0:  # Buy order
                    total_required = trade_value + total_cost
                    if new_cash >= total_required:
                        new_cash -= total_required
                        new_positions[symbol] = target_shares
                        
                        # Record trade
                        results.trade_history.append({
                            'date': date,
                            'symbol': symbol,
                            'action': 'BUY',
                            'shares': trade_shares,
                            'price': current_price,
                            'value': trade_value,
                            'commission': commission,
                            'total_cost': total_cost
                        })
                else:  # Sell order
                    new_cash += trade_value - total_cost
                    new_positions[symbol] = target_shares
                    
                    # Record trade
                    results.trade_history.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'shares': abs(trade_shares),
                        'price': current_price,
                        'value': trade_value,
                        'commission': commission,
                        'total_cost': total_cost
                    })
                
                # Remove zero positions
                if new_positions.get(symbol, 0) == 0:
                    new_positions.pop(symbol, None)
        
        return new_cash, new_positions
    
    def _record_portfolio_state(self, results: BacktestResults, date: pd.Timestamp, 
                               positions: Dict[str, int], cash: float, 
                               data: pd.DataFrame):
        """Record current portfolio state"""
        # Get current prices
        current_prices = self._get_current_prices(data, date)
        
        # Calculate portfolio value
        position_values = {}
        total_position_value = 0
        
        for symbol, shares in positions.items():
            if symbol in current_prices:
                value = shares * current_prices[symbol]
                position_values[symbol] = value
                total_position_value += value
        
        total_portfolio_value = cash + total_position_value
        
        # Record state
        portfolio_record = {
            'date': date,
            'cash': cash,
            'positions': positions.copy(),
            'position_values': position_values,
            'total_value': total_portfolio_value,
            'daily_return': 0.0
        }
        
        # Calculate daily return if we have previous data
        if results.portfolio_history:
            prev_value = results.portfolio_history[-1]['total_value']
            if prev_value > 0:
                portfolio_record['daily_return'] = (total_portfolio_value / prev_value) - 1
        
        results.portfolio_history.append(portfolio_record)

__all__ = ['MomentumBacktest', 'BacktestResults']
