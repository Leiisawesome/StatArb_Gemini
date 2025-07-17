"""
Production-grade backtesting engine for momentum strategy
Event-driven backtesting with realistic execution modeling
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import sys
import os

# Optional imports for extended functionality
try:
    # Try to import from the new_structure if available
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'new_structure'))
    from risk_management.risk_manager import RiskManager
    from portfolio_management.portfolio_manager import PortfolioManager
    EXTENDED_FEATURES = True
except ImportError:
    # Gracefully handle missing dependencies
    RiskManager = None
    PortfolioManager = None
    EXTENDED_FEATURES = False

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Represents a single trade"""
    symbol: str
    date: datetime
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    commission: float = 0.0
    market_impact: float = 0.0
    slippage: float = 0.0
    total_cost: float = 0.0
    trade_id: str = ""

@dataclass
class Position:
    """Represents a portfolio position"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    weight: float = 0.0

@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time"""
    date: datetime
    total_value: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    daily_return: float = 0.0
    total_return: float = 0.0
    leverage: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    net_exposure: float = 0.0

class ExecutionSimulator:
    """Simulates realistic trade execution with costs"""
    
    def __init__(self, config: Dict):
        self.config = config.get('execution', {})
        
        # Transaction costs
        self.commission_rate = self.config.get('commission_rate', 0.0005)
        self.bid_ask_spread = self.config.get('bid_ask_spread', 0.001)
        self.market_impact_coeff = self.config.get('market_impact_coeff', 0.0005)
        
        # Execution parameters
        self.execution_delay = self.config.get('execution_delay', 1)
        self.partial_fill_prob = self.config.get('partial_fill_probability', 0.95)
        
        # Slippage model
        self.slippage_model = self.config.get('slippage_model', 'sqrt')
        self.slippage_coeff = self.config.get('slippage_coefficient', 0.001)
    
    def simulate_trade_execution(self, symbol: str, target_quantity: float, 
                                current_price: float, volume: float,
                                portfolio_value: float) -> Trade:
        """
        Simulate realistic trade execution with transaction costs
        
        Args:
            symbol: Stock symbol
            target_quantity: Target position (positive for long, negative for short)
            current_price: Current market price
            volume: Daily volume
            portfolio_value: Current portfolio value
            
        Returns:
            Trade object with execution details
        """
        
        # Determine trade side and quantity
        side = 'BUY' if target_quantity > 0 else 'SELL'
        trade_quantity = abs(target_quantity)
        
        if trade_quantity == 0:
            return None
        
        # Calculate trade value
        trade_value = trade_quantity * current_price
        
        # Commission costs
        commission = trade_value * self.commission_rate
        
        # Bid-ask spread cost
        bid_ask_cost = trade_value * self.bid_ask_spread / 2
        
        # Market impact (square-root model)
        if volume > 0:
            participation_rate = trade_quantity / volume
            market_impact = self._calculate_market_impact(participation_rate, trade_value)
        else:
            market_impact = trade_value * 0.001  # Default 10 bps
        
        # Slippage
        slippage = self._calculate_slippage(trade_quantity, volume, current_price)
        
        # Total transaction costs
        total_cost = commission + bid_ask_cost + market_impact + slippage
        
        # Adjust execution price
        if side == 'BUY':
            execution_price = current_price + (market_impact + slippage) / trade_quantity
        else:
            execution_price = current_price - (market_impact + slippage) / trade_quantity
        
        trade = Trade(
            symbol=symbol,
            date=datetime.now(),  # Will be set by backtest engine
            side=side,
            quantity=trade_quantity,
            price=execution_price,
            commission=commission,
            market_impact=market_impact,
            slippage=slippage,
            total_cost=total_cost,
            trade_id=f"{symbol}_{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return trade
    
    def _calculate_market_impact(self, participation_rate: float, trade_value: float) -> float:
        """Calculate market impact using square-root model"""
        # Standard square-root market impact model
        # Impact = coefficient * sqrt(participation_rate) * trade_value
        impact = self.market_impact_coeff * np.sqrt(participation_rate) * trade_value
        return min(impact, trade_value * 0.01)  # Cap at 100 bps
    
    def _calculate_slippage(self, quantity: float, volume: float, price: float) -> float:
        """Calculate slippage based on trade size and liquidity"""
        if volume <= 0:
            return quantity * price * 0.001  # Default 10 bps
        
        volume_ratio = quantity / volume
        
        if self.slippage_model == 'sqrt':
            slippage = self.slippage_coeff * np.sqrt(volume_ratio) * quantity * price
        else:  # Linear model
            slippage = self.slippage_coeff * volume_ratio * quantity * price
        
        return min(slippage, quantity * price * 0.005)  # Cap at 50 bps

class BacktestEngine:
    """
    Production-grade backtesting engine
    
    Features:
    - Event-driven architecture
    - Realistic transaction cost modeling
    - Position and risk management
    - Comprehensive performance tracking
    """
    
    def __init__(self, config: Dict, strategy):
        """Initialize backtest engine"""
        self.config = config
        self.strategy = strategy
        
        # Backtesting configuration
        backtest_config = config.get('backtesting', {})
        self.engine_type = backtest_config.get('engine_type', 'event_driven')
        self.use_vectorized = backtest_config.get('use_vectorized_calculations', True)
        
        # Risk configuration
        risk_config = config.get('risk', {})
        self.max_leverage = risk_config.get('max_leverage', 1.0)
        self.max_position_weight = risk_config.get('max_position_weight', 0.05)
        self.max_drawdown_limit = risk_config.get('max_drawdown_limit', 0.20)
        
        # Initialize components
        self.execution_simulator = ExecutionSimulator(config)
        
        # Portfolio state - get initial capital from config
        self.initial_capital = config.get('backtesting', {}).get('initial_capital', 
                                                              config.get('initial_capital', 1000000))
        self.current_cash = self.initial_capital
        self.positions = {}  # symbol -> Position
        self.portfolio_history = []
        self.trade_history = []
        
        # Performance tracking
        self.daily_returns = []
        self.portfolio_values = []
        self.benchmarks = {}
        
        # Risk monitoring
        self.drawdown_warnings = 0
        self.max_drawdown_warnings = 10  # Limit excessive warnings
        
        logger.info("Backtest engine initialized")
        logger.info(f"  Initial capital: ${self.initial_capital:,.0f}")
        logger.info(f"  Engine type: {self.engine_type}")
        logger.info(f"  Max drawdown limit: {self.max_drawdown_limit:.1%}")
        logger.info(f"  Extended features: {EXTENDED_FEATURES}")
    
    def run_backtest(self, data: pd.DataFrame, benchmark_data: Optional[pd.DataFrame] = None,
                     start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Run the complete backtest
        
        Args:
            data: Historical price data with MultiIndex (date, symbol)
            benchmark_data: Benchmark price data
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dictionary with backtest results
        """
        logger.info("Starting backtest execution...")
        
        # Filter data by date range
        if start_date:
            data = data[data.index.get_level_values('date') >= start_date]
        if end_date:
            data = data[data.index.get_level_values('date') <= end_date]
        
        # Get unique trading dates
        trading_dates = sorted(data.index.get_level_values('date').unique())
        
        logger.info(f"Backtesting period: {trading_dates[0]} to {trading_dates[-1]}")
        logger.info(f"Total trading days: {len(trading_dates)}")
        
        # Initialize benchmark tracking
        if benchmark_data is not None:
            self._initialize_benchmark_tracking(benchmark_data, trading_dates)
        
        # Main backtest loop
        for i, current_date in enumerate(trading_dates):
            try:
                self._process_trading_day(data, current_date, i)
            except Exception as e:
                logger.error(f"Error processing {current_date}: {e}")
                continue
        
        # Generate final results
        results = self._generate_backtest_results()
        
        logger.info("Backtest completed successfully")
        logger.info(f"Final portfolio value: ${results['final_portfolio_value']:,.0f}")
        logger.info(f"Total return: {results['total_return']:.2%}")
        
        return results
    
    def _process_trading_day(self, data: pd.DataFrame, current_date: datetime, day_index: int):
        """Process a single trading day"""
        
        # Get current day's data
        try:
            current_data = data.xs(current_date, level='date')
        except KeyError:
            logger.warning(f"No data available for {current_date}")
            return
        
        # Update position values with current prices
        self._update_position_values(current_data)
        
        # Generate trading signals (only on rebalance days)
        signals = self.strategy.generate_signals(data, current_date)
        
        # Execute trades if signals generated
        if signals:
            self._execute_rebalancing(signals, current_data, current_date)
        
        # Calculate portfolio metrics
        self._calculate_daily_metrics(current_date, day_index)
        
        # Risk management checks
        self._apply_risk_management(current_date)
        
        # Record portfolio snapshot
        self._record_portfolio_snapshot(current_date)
    
    def _update_position_values(self, current_data: pd.DataFrame):
        """Update position values with current market prices"""
        for symbol, position in self.positions.items():
            if symbol in current_data.index:
                current_price = current_data.loc[symbol, 'close']
                position.current_price = current_price
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = position.market_value - (position.quantity * position.avg_cost)
    
    def _execute_rebalancing(self, signals: Dict[str, str], current_data: pd.DataFrame, current_date: datetime):
        """Execute portfolio rebalancing based on signals"""
        
        # Calculate current portfolio value
        portfolio_value = self._calculate_portfolio_value()
        
        # Get target positions from strategy
        target_positions = self.strategy.get_target_positions(signals, current_date)
        
        # Calculate target quantities
        target_quantities = {}
        for symbol, target_weight in target_positions.items():
            if symbol in current_data.index:
                current_price = current_data.loc[symbol, 'close']
                target_value = portfolio_value * target_weight
                target_quantity = target_value / current_price
                target_quantities[symbol] = target_quantity
        
        # Execute trades to reach target positions
        trades = self._execute_trades(target_quantities, current_data, current_date, portfolio_value)
        
        # Record trades
        self.trade_history.extend(trades)
        
        logger.info(f"Executed {len(trades)} trades on {current_date}")
    
    def _execute_trades(self, target_quantities: Dict[str, float], current_data: pd.DataFrame,
                       current_date: datetime, portfolio_value: float) -> List[Trade]:
        """Execute individual trades to reach target positions"""
        
        trades = []
        
        # Calculate trades needed for each position
        for symbol, target_qty in target_quantities.items():
            if symbol not in current_data.index:
                continue
                
            current_qty = self.positions.get(symbol, Position(symbol, 0, 0)).quantity
            trade_qty = target_qty - current_qty
            
            if abs(trade_qty) < 1:  # Minimum trade size
                continue
            
            # Get market data
            current_price = current_data.loc[symbol, 'close']
            volume = current_data.loc[symbol, 'volume'] if 'volume' in current_data.columns else 1000000
            
            # Simulate trade execution
            trade = self.execution_simulator.simulate_trade_execution(
                symbol, trade_qty, current_price, volume, portfolio_value
            )
            
            if trade:
                trade.date = current_date
                
                # Check if we have enough cash for the trade
                if self._can_execute_trade(trade):
                    # Execute the trade
                    self._execute_single_trade(trade)
                    trades.append(trade)
                else:
                    logger.warning(f"Insufficient cash for trade: {trade.symbol} {trade.side} {trade.quantity}")
        
        # Close positions not in target
        symbols_to_close = set(self.positions.keys()) - set(target_quantities.keys())
        for symbol in symbols_to_close:
            if symbol in current_data.index and self.positions[symbol].quantity != 0:
                current_price = current_data.loc[symbol, 'close']
                volume = current_data.loc[symbol, 'volume'] if 'volume' in current_data.columns else 1000000
                
                # Close position
                close_qty = -self.positions[symbol].quantity
                trade = self.execution_simulator.simulate_trade_execution(
                    symbol, close_qty, current_price, volume, portfolio_value
                )
                
                if trade:
                    trade.date = current_date
                    self._execute_single_trade(trade)
                    trades.append(trade)
        
        return trades
    
    def _can_execute_trade(self, trade: Trade) -> bool:
        """Check if trade can be executed given current cash"""
        if trade.side == 'BUY':
            required_cash = trade.quantity * trade.price + trade.total_cost
            return self.current_cash >= required_cash
        else:  # SELL
            return True  # Can always sell existing positions
    
    def _execute_single_trade(self, trade: Trade):
        """Execute a single trade and update portfolio"""
        
        # Update cash
        if trade.side == 'BUY':
            self.current_cash -= (trade.quantity * trade.price + trade.total_cost)
        else:  # SELL
            self.current_cash += (trade.quantity * trade.price - trade.total_cost)
        
        # Update position
        if trade.symbol not in self.positions:
            self.positions[trade.symbol] = Position(trade.symbol, 0, 0)
        
        position = self.positions[trade.symbol]
        
        if trade.side == 'BUY':
            # Calculate new average cost
            total_cost = position.quantity * position.avg_cost + trade.quantity * trade.price
            total_quantity = position.quantity + trade.quantity
            
            if total_quantity > 0:
                position.avg_cost = total_cost / total_quantity
            
            position.quantity += trade.quantity
        else:  # SELL
            position.quantity -= trade.quantity
            
            # Remove position if quantity is zero
            if abs(position.quantity) < 0.001:
                del self.positions[trade.symbol]
    
    def _calculate_portfolio_value(self) -> float:
        """Calculate current total portfolio value"""
        market_value = sum(pos.market_value for pos in self.positions.values())
        return self.current_cash + market_value
    
    def _calculate_daily_metrics(self, current_date: datetime, day_index: int):
        """Calculate daily performance metrics"""
        
        current_portfolio_value = self._calculate_portfolio_value()
        self.portfolio_values.append(current_portfolio_value)
        
        # Calculate daily return
        if day_index > 0:
            prev_value = self.portfolio_values[-2]
            daily_return = (current_portfolio_value / prev_value) - 1
        else:
            daily_return = 0.0
        
        self.daily_returns.append(daily_return)
    
    def _apply_risk_management(self, current_date: datetime):
        """Apply risk management rules"""
        
        portfolio_value = self._calculate_portfolio_value()
        
        # Check drawdown limit
        current_drawdown = (portfolio_value / self.initial_capital) - 1
        if current_drawdown < -self.max_drawdown_limit:
            if self.drawdown_warnings < self.max_drawdown_warnings:
                logger.warning(f"Maximum drawdown limit exceeded on {current_date}: "
                             f"{current_drawdown:.2%} < -{self.max_drawdown_limit:.1%}")
                self.drawdown_warnings += 1
            elif self.drawdown_warnings == self.max_drawdown_warnings:
                logger.warning("Maximum drawdown warnings suppressed (limit reached)")
                self.drawdown_warnings += 1
            # In production, this might trigger position liquidation
        
        # Check leverage limit
        long_exposure = sum(max(0, pos.market_value) for pos in self.positions.values())
        short_exposure = sum(abs(min(0, pos.market_value)) for pos in self.positions.values())
        gross_exposure = long_exposure + short_exposure
        
        leverage = gross_exposure / portfolio_value if portfolio_value > 0 else 0
        
        if leverage > self.max_leverage:
            logger.warning(f"Leverage limit exceeded on {current_date}: {leverage:.2f} > {self.max_leverage}")
    
    def _record_portfolio_snapshot(self, current_date: datetime):
        """Record portfolio state for analysis"""
        
        portfolio_value = self._calculate_portfolio_value()
        
        # Calculate exposures
        long_exposure = sum(max(0, pos.market_value) for pos in self.positions.values())
        short_exposure = sum(abs(min(0, pos.market_value)) for pos in self.positions.values())
        net_exposure = sum(pos.market_value for pos in self.positions.values())
        
        leverage = (long_exposure + short_exposure) / portfolio_value if portfolio_value > 0 else 0
        
        # Calculate returns
        daily_return = self.daily_returns[-1] if self.daily_returns else 0.0
        total_return = (portfolio_value / self.initial_capital) - 1
        
        snapshot = PortfolioSnapshot(
            date=current_date,
            total_value=portfolio_value,
            cash=self.current_cash,
            positions=self.positions.copy(),
            daily_return=daily_return,
            total_return=total_return,
            leverage=leverage,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            net_exposure=net_exposure
        )
        
        self.portfolio_history.append(snapshot)
    
    def _initialize_benchmark_tracking(self, benchmark_data: pd.DataFrame, trading_dates: List[datetime]):
        """Initialize benchmark tracking"""
        
        # Filter benchmark data to trading dates
        benchmark_filtered = benchmark_data[benchmark_data.index.isin(trading_dates)]
        
        if not benchmark_filtered.empty:
            self.benchmarks['SPY'] = benchmark_filtered
            logger.info("Benchmark tracking initialized")
    
    def _generate_backtest_results(self) -> Dict[str, Any]:
        """Generate comprehensive backtest results"""
        
        # Convert portfolio history to DataFrame
        portfolio_df = pd.DataFrame([
            {
                'date': snap.date,
                'portfolio_value': snap.total_value,
                'cash': snap.cash,
                'daily_return': snap.daily_return,
                'total_return': snap.total_return,
                'leverage': snap.leverage,
                'long_exposure': snap.long_exposure,
                'short_exposure': snap.short_exposure,
                'net_exposure': snap.net_exposure
            }
            for snap in self.portfolio_history
        ])
        
        portfolio_df.set_index('date', inplace=True)
        
        # Calculate performance metrics
        returns = np.array(self.daily_returns)
        final_value = self.portfolio_values[-1] if self.portfolio_values else self.initial_capital
        
        results = {
            'portfolio_history': portfolio_df,
            'trade_history': pd.DataFrame([trade.__dict__ for trade in self.trade_history]),
            'daily_returns': returns,
            'portfolio_values': self.portfolio_values,
            
            # Performance metrics
            'initial_capital': self.initial_capital,
            'final_portfolio_value': final_value,
            'total_return': (final_value / self.initial_capital) - 1,
            'annualized_return': ((final_value / self.initial_capital) ** (252 / len(returns))) - 1 if len(returns) > 0 else 0,
            'volatility': np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0,
            'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 and np.std(returns) > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(),
            'winning_trades': len([t for t in self.trade_history if self._calculate_trade_pnl(t) > 0]),
            'total_trades': len(self.trade_history),
            'total_commission': sum(t.commission for t in self.trade_history),
            'total_slippage': sum(t.slippage for t in self.trade_history),
            
            # Risk metrics
            'var_5pct': np.percentile(returns, 5) if len(returns) > 0 else 0,
            'cvar_5pct': np.mean(returns[returns <= np.percentile(returns, 5)]) if len(returns) > 0 else 0,
            
            # Strategy metrics
            'avg_leverage': portfolio_df['leverage'].mean() if not portfolio_df.empty else 0,
            'avg_long_exposure': portfolio_df['long_exposure'].mean() if not portfolio_df.empty else 0,
            'avg_short_exposure': portfolio_df['short_exposure'].mean() if not portfolio_df.empty else 0,
        }
        
        return results
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if not self.portfolio_values:
            return 0.0
        
        portfolio_values = np.array(self.portfolio_values)
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        
        return np.min(drawdown)
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """Calculate P&L for a trade (simplified)"""
        # This is a simplified calculation
        # In practice, you'd need to track the full position lifecycle
        if trade.side == 'SELL':
            return trade.quantity * trade.price - trade.total_cost
        else:
            return -(trade.quantity * trade.price + trade.total_cost)
