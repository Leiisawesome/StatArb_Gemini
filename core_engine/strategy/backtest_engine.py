"""
Strategy Engine - Backtest Engine
Comprehensive strategy backtesting and simulation framework
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict, deque
import copy
import json
from pathlib import Path

# Import strategy and performance components
from .strategy_engine import BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition, StrategyMetrics
from ..performance.performance_calculator import PerformanceCalculator, PerformanceMetrics

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    """Backtest execution modes"""
    HISTORICAL = "historical"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    STRESS_TEST = "stress_test"
    PAPER_TRADING = "paper_trading"


class ExecutionModel(Enum):
    """Trade execution models"""
    IMMEDIATE = "immediate"           # Execute at signal price
    NEXT_BAR = "next_bar"            # Execute at next bar open
    REALISTIC = "realistic"           # Include slippage and delays
    MARKET_IMPACT = "market_impact"   # Model market impact
    LIMIT_ORDERS = "limit_orders"     # Use limit orders


class SlippageModel(Enum):
    """Slippage models"""
    FIXED_PERCENTAGE = "fixed_percentage"
    FIXED_AMOUNT = "fixed_amount"
    VOLUME_BASED = "volume_based"
    SPREAD_BASED = "spread_based"
    MARKET_IMPACT = "market_impact"


class CommissionModel(Enum):
    """Commission models"""
    FIXED_PER_TRADE = "fixed_per_trade"
    PERCENTAGE = "percentage"
    PER_SHARE = "per_share"
    TIERED = "tiered"


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    
    # Basic settings
    start_date: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=365))
    end_date: datetime = field(default_factory=datetime.now)
    initial_capital: float = 100000.0
    benchmark_symbol: str = "SPY"
    
    # Execution settings
    execution_model: ExecutionModel = ExecutionModel.NEXT_BAR
    allow_short_selling: bool = True
    margin_requirement: float = 0.5  # 50% margin
    
    # Transaction costs
    commission_model: CommissionModel = CommissionModel.PERCENTAGE
    commission_rate: float = 0.001   # 0.1% commission
    fixed_commission: float = 5.0    # $5 per trade
    
    # Slippage settings
    slippage_model: SlippageModel = SlippageModel.FIXED_PERCENTAGE
    slippage_rate: float = 0.0005    # 0.05% slippage
    fixed_slippage: float = 0.01     # $0.01 fixed slippage
    
    # Risk management
    margin_call_threshold: float = 0.25  # 25% margin call
    stop_loss_on_margin_call: bool = True
    max_leverage: float = 2.0
    
    # Data settings
    frequency: str = "1D"  # Data frequency (1D, 1H, 5M, etc.)
    adjust_for_splits: bool = True
    adjust_for_dividends: bool = True
    
    # Walk-forward settings (for walk-forward analysis)
    training_period: int = 252      # Days for training
    testing_period: int = 63        # Days for testing
    rebalance_frequency: int = 21   # Days between rebalancing
    
    # Monte Carlo settings
    n_simulations: int = 1000
    confidence_levels: List[float] = field(default_factory=lambda: [0.05, 0.95])
    
    # Performance settings
    calculate_performance_metrics: bool = True
    save_trade_log: bool = True
    save_position_history: bool = True
    
    # Output settings
    output_directory: str = "backtest_results"
    save_detailed_results: bool = True


@dataclass
class Trade:
    """Individual trade record"""
    
    # Trade identification
    trade_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    
    # Trade details
    side: str = "long"  # long, short
    quantity: float = 0.0
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    
    # Timing
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    holding_period: Optional[int] = None  # In periods
    
    # P&L
    gross_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0
    
    # Trade metadata
    entry_signal: Optional[StrategySignal] = None
    exit_reason: str = ""  # signal, stop_loss, take_profit, time_exit
    
    # Additional data
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Portfolio:
    """Portfolio state tracking"""
    
    # Portfolio value
    total_value: float = 0.0
    cash: float = 0.0
    positions_value: float = 0.0
    margin_used: float = 0.0
    
    # Performance metrics
    total_return: float = 0.0
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    
    # Risk metrics
    leverage: float = 0.0
    margin_ratio: float = 0.0
    
    # Position tracking
    positions: Dict[str, StrategyPosition] = field(default_factory=dict)
    
    # Transaction tracking
    trades: List[Trade] = field(default_factory=list)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BacktestResult:
    """Comprehensive backtest results"""
    
    # Basic information
    strategy_id: str = ""
    backtest_config: Optional[BacktestConfig] = None
    
    # Performance metrics
    performance_metrics: Optional[PerformanceMetrics] = None
    final_portfolio_value: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Time series data
    portfolio_history: List[Portfolio] = field(default_factory=list)
    returns_series: Optional[pd.Series] = None
    positions_history: Optional[pd.DataFrame] = None
    
    # Trade log
    trade_log: List[Trade] = field(default_factory=list)
    
    # Benchmark comparison
    benchmark_returns: Optional[pd.Series] = None
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    
    # Risk analysis
    var_95: float = 0.0
    cvar_95: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Execution analysis
    total_commission: float = 0.0
    total_slippage: float = 0.0
    avg_slippage: float = 0.0
    
    # Timing
    backtest_start_time: datetime = field(default_factory=datetime.now)
    backtest_end_time: Optional[datetime] = None
    execution_time: float = 0.0
    
    # Metadata
    data_quality: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TransactionCostCalculator:
    """Calculate transaction costs including commissions and slippage"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        logger.info("Transaction cost calculator initialized")
    
    def calculate_commission(self, trade: Trade) -> float:
        """Calculate commission for a trade"""
        
        try:
            if self.config.commission_model == CommissionModel.FIXED_PER_TRADE:
                return self.config.fixed_commission
            
            elif self.config.commission_model == CommissionModel.PERCENTAGE:
                trade_value = abs(trade.quantity * trade.entry_price)
                return trade_value * self.config.commission_rate
            
            elif self.config.commission_model == CommissionModel.PER_SHARE:
                return abs(trade.quantity) * self.config.commission_rate
            
            elif self.config.commission_model == CommissionModel.TIERED:
                # Simple tiered model
                trade_value = abs(trade.quantity * trade.entry_price)
                if trade_value <= 10000:
                    return trade_value * 0.001
                elif trade_value <= 50000:
                    return trade_value * 0.0008
                else:
                    return trade_value * 0.0005
            
            else:
                return self.config.fixed_commission
                
        except Exception as e:
            logger.error(f"Error calculating commission: {e}")
            return 0.0
    
    def calculate_slippage(self, trade: Trade, market_data: Optional[pd.DataFrame] = None) -> float:
        """Calculate slippage for a trade"""
        
        try:
            if self.config.slippage_model == SlippageModel.FIXED_PERCENTAGE:
                trade_value = abs(trade.quantity * trade.entry_price)
                return trade_value * self.config.slippage_rate
            
            elif self.config.slippage_model == SlippageModel.FIXED_AMOUNT:
                return abs(trade.quantity) * self.config.fixed_slippage
            
            elif self.config.slippage_model == SlippageModel.VOLUME_BASED:
                # Simple volume-based model
                if market_data is not None and 'volume' in market_data.columns:
                    # Estimate slippage based on trade size vs. average volume
                    avg_volume = market_data['volume'].rolling(20).mean().iloc[-1]
                    trade_volume = abs(trade.quantity)
                    
                    if avg_volume > 0:
                        volume_ratio = trade_volume / avg_volume
                        slippage_rate = self.config.slippage_rate * (1 + volume_ratio)
                        trade_value = abs(trade.quantity * trade.entry_price)
                        return trade_value * slippage_rate
                
                # Fallback to fixed percentage
                trade_value = abs(trade.quantity * trade.entry_price)
                return trade_value * self.config.slippage_rate
            
            elif self.config.slippage_model == SlippageModel.SPREAD_BASED:
                # Estimate slippage as fraction of bid-ask spread
                if market_data is not None:
                    if 'bid' in market_data.columns and 'ask' in market_data.columns:
                        bid = market_data['bid'].iloc[-1]
                        ask = market_data['ask'].iloc[-1]
                        spread = ask - bid
                        slippage_cost = abs(trade.quantity) * spread * 0.5  # Half spread
                        return slippage_cost
                
                # Fallback to fixed percentage
                trade_value = abs(trade.quantity * trade.entry_price)
                return trade_value * self.config.slippage_rate
            
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating slippage: {e}")
            return 0.0


class PositionManager:
    """Manage position tracking and updates"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.positions: Dict[str, StrategyPosition] = {}
        
        logger.info("Position manager initialized")
    
    def update_position(self, trade: Trade, current_price: float) -> Optional[StrategyPosition]:
        """Update position based on trade"""
        
        try:
            symbol = trade.symbol
            
            if symbol not in self.positions:
                # Create new position
                position = StrategyPosition(
                    position_id=f"{trade.strategy_id}_{symbol}",
                    strategy_id=trade.strategy_id,
                    symbol=symbol,
                    quantity=0.0,
                    side="long",
                    entry_price=0.0,
                    current_price=current_price
                )
                self.positions[symbol] = position
            
            position = self.positions[symbol]
            
            # Calculate new quantity
            if trade.side == "long":
                new_quantity = position.quantity + trade.quantity
            else:  # short
                new_quantity = position.quantity - trade.quantity
            
            # Update position
            if new_quantity == 0:
                # Position closed
                del self.positions[symbol]
                return None
            else:
                # Update position details
                if (position.quantity >= 0 and new_quantity >= 0) or (position.quantity <= 0 and new_quantity <= 0):
                    # Same side - update average price
                    total_cost = position.quantity * position.entry_price + trade.quantity * trade.entry_price
                    position.quantity = new_quantity
                    position.entry_price = total_cost / new_quantity if new_quantity != 0 else 0
                else:
                    # Side flip or partial close
                    position.quantity = new_quantity
                    if abs(new_quantity) < abs(position.quantity):
                        # Partial close - keep same entry price
                        pass
                    else:
                        # Position flipped - new entry price
                        position.entry_price = trade.entry_price
                
                position.side = "long" if new_quantity > 0 else "short"
                position.current_price = current_price
                position.last_update = datetime.now()
                
                # Update P&L
                self.update_position_pnl(position)
                
                return position
                
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return None
    
    def update_position_pnl(self, position: StrategyPosition) -> None:
        """Update position P&L"""
        
        try:
            if position.quantity == 0:
                position.unrealized_pnl = 0.0
                return
            
            if position.side == "long":
                position.unrealized_pnl = position.quantity * (position.current_price - position.entry_price)
            else:  # short
                position.unrealized_pnl = -position.quantity * (position.current_price - position.entry_price)
            
            position.total_pnl = position.realized_pnl + position.unrealized_pnl
            position.market_value = abs(position.quantity * position.current_price)
            
        except Exception as e:
            logger.error(f"Error updating position P&L: {e}")
    
    def update_all_positions(self, market_data: Dict[str, float]) -> None:
        """Update all positions with current market prices"""
        
        try:
            for symbol, position in self.positions.items():
                if symbol in market_data:
                    position.current_price = market_data[symbol]
                    self.update_position_pnl(position)
                    position.last_update = datetime.now()
                    
        except Exception as e:
            logger.error(f"Error updating all positions: {e}")
    
    def get_positions(self) -> Dict[str, StrategyPosition]:
        """Get current positions"""
        return self.positions.copy()
    
    def get_total_value(self) -> float:
        """Get total value of all positions"""
        return sum(abs(pos.market_value) for pos in self.positions.values())
    
    def get_total_pnl(self) -> float:
        """Get total P&L of all positions"""
        return sum(pos.total_pnl for pos in self.positions.values())


class BacktestEngine:
    """
    Comprehensive Strategy Backtesting Engine
    
    Provides sophisticated backtesting capabilities including realistic execution,
    transaction costs, risk management, and detailed performance analysis.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """Initialize backtest engine"""
        
        self.config = config or BacktestConfig()
        
        # Core components
        self.cost_calculator = TransactionCostCalculator(self.config)
        self.position_manager = PositionManager(self.config)
        self.performance_calculator = PerformanceCalculator()
        
        # Backtest state
        self.current_portfolio = Portfolio(cash=self.config.initial_capital)
        self.current_time: Optional[datetime] = None
        
        # History tracking
        self.portfolio_history: List[Portfolio] = []
        self.trade_log: List[Trade] = []
        self.signals_log: List[StrategySignal] = []
        
        # Market data
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.benchmark_data: Optional[pd.Series] = None
        
        # Performance tracking
        self.backtest_stats = {
            'strategies_tested': 0,
            'total_backtests': 0,
            'successful_backtests': 0,
            'failed_backtests': 0,
            'total_trades_executed': 0
        }
        
        logger.info("Backtest engine initialized")
    
    def run_backtest(self, strategy: BaseStrategy, market_data: Dict[str, pd.DataFrame],
                    benchmark_data: Optional[pd.Series] = None) -> BacktestResult:
        """Run comprehensive backtest"""
        
        start_time = datetime.now()
        
        try:
            self.backtest_stats['total_backtests'] += 1
            
            logger.info(f"Starting backtest for strategy: {strategy.strategy_id}")
            
            # Initialize backtest
            self._initialize_backtest(strategy, market_data, benchmark_data)
            
            # Validate data
            data_quality = self._validate_market_data(market_data)
            
            # Get time index
            time_index = self._get_time_index(market_data)
            
            # Initialize strategy
            if not strategy.initialize():
                raise ValueError("Strategy initialization failed")
            
            # Main backtest loop
            for i, current_time in enumerate(time_index):
                self.current_time = current_time
                
                # Get current market data
                current_data = self._get_current_data(market_data, i)
                current_prices = self._get_current_prices(market_data, i)
                
                # Update positions with current prices
                self.position_manager.update_all_positions(current_prices)
                
                # Update strategy with market data
                new_signals = strategy.update(current_data)
                
                # Process signals
                for signal in new_signals:
                    self._process_signal(signal, current_prices, current_time)
                
                # Update portfolio
                self._update_portfolio(current_prices, current_time)
                
                # Record portfolio history
                if i % 1 == 0:  # Record every period (can be adjusted)
                    self.portfolio_history.append(copy.deepcopy(self.current_portfolio))
            
            # Create backtest result
            result = self._create_backtest_result(strategy, start_time, data_quality)
            
            self.backtest_stats['successful_backtests'] += 1
            
            logger.info(f"Backtest completed for {strategy.strategy_id}: "
                       f"Final value = ${result.final_portfolio_value:,.2f}, "
                       f"Total return = {result.total_return:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            self.backtest_stats['failed_backtests'] += 1
            
            # Return minimal result with error
            result = BacktestResult(
                strategy_id=strategy.strategy_id if strategy else "unknown",
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            return result
    
    def run_walk_forward_analysis(self, strategy_class: type, base_config: StrategyConfig,
                                market_data: Dict[str, pd.DataFrame]) -> List[BacktestResult]:
        """Run walk-forward analysis"""
        
        try:
            logger.info("Starting walk-forward analysis")
            
            results = []
            time_index = self._get_time_index(market_data)
            
            training_days = self.config.training_period
            testing_days = self.config.testing_period
            step_days = self.config.rebalance_frequency
            
            start_idx = 0
            
            while start_idx + training_days + testing_days < len(time_index):
                # Define training and testing periods
                train_end_idx = start_idx + training_days
                test_end_idx = train_end_idx + testing_days
                
                train_start = time_index[start_idx]
                train_end = time_index[train_end_idx]
                test_start = time_index[train_end_idx]
                test_end = time_index[test_end_idx]
                
                logger.info(f"Walk-forward period: Train {train_start} to {train_end}, "
                           f"Test {test_start} to {test_end}")
                
                # Extract data for this period
                test_data = {}
                for symbol, data in market_data.items():
                    mask = (data.index >= test_start) & (data.index <= test_end)
                    test_data[symbol] = data.loc[mask]
                
                # Create strategy instance
                strategy = strategy_class(copy.deepcopy(base_config))
                
                # Run backtest on testing period
                result = self.run_backtest(strategy, test_data)
                result.data_period = (test_start, test_end)
                
                results.append(result)
                
                # Move to next period
                start_idx += step_days
            
            logger.info(f"Walk-forward analysis completed: {len(results)} periods")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in walk-forward analysis: {e}")
            return []
    
    def run_monte_carlo_simulation(self, strategy: BaseStrategy, 
                                 market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Run Monte Carlo simulation on strategy"""
        
        try:
            logger.info(f"Starting Monte Carlo simulation with {self.config.n_simulations} runs")
            
            results = []
            
            for simulation in range(self.config.n_simulations):
                # Shuffle the data for Monte Carlo
                shuffled_data = self._shuffle_market_data(market_data)
                
                # Create strategy copy
                strategy_copy = copy.deepcopy(strategy)
                
                # Run backtest
                result = self.run_backtest(strategy_copy, shuffled_data)
                results.append(result.total_return)
                
                if (simulation + 1) % 100 == 0:
                    logger.info(f"Completed {simulation + 1} Monte Carlo simulations")
            
            # Analyze results
            returns_array = np.array(results)
            
            analysis = {
                'simulations': self.config.n_simulations,
                'mean_return': np.mean(returns_array),
                'std_return': np.std(returns_array),
                'min_return': np.min(returns_array),
                'max_return': np.max(returns_array),
                'percentiles': {},
                'probability_positive': np.mean(returns_array > 0),
                'var_95': np.percentile(returns_array, 5),
                'var_99': np.percentile(returns_array, 1)
            }
            
            # Calculate confidence intervals
            for level in self.config.confidence_levels:
                percentile = level * 100
                analysis['percentiles'][f'p{percentile}'] = np.percentile(returns_array, percentile)
            
            logger.info(f"Monte Carlo simulation completed: "
                       f"Mean return = {analysis['mean_return']:.2%}, "
                       f"Std = {analysis['std_return']:.2%}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo simulation: {e}")
            return {}
    
    def _initialize_backtest(self, strategy: BaseStrategy, market_data: Dict[str, pd.DataFrame],
                           benchmark_data: Optional[pd.Series]) -> None:
        """Initialize backtest state"""
        
        # Reset state
        self.current_portfolio = Portfolio(cash=self.config.initial_capital)
        self.current_portfolio.total_value = self.config.initial_capital
        self.position_manager.positions.clear()
        self.portfolio_history.clear()
        self.trade_log.clear()
        self.signals_log.clear()
        
        # Store data
        self.market_data = market_data
        self.benchmark_data = benchmark_data
        
        logger.info(f"Backtest initialized with ${self.config.initial_capital:,.2f} capital")
    
    def _validate_market_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate market data quality"""
        
        quality_report = {
            'symbols': len(market_data),
            'total_rows': 0,
            'missing_data': {},
            'date_range': {},
            'issues': []
        }
        
        try:
            for symbol, data in market_data.items():
                quality_report['total_rows'] += len(data)
                
                # Check for missing data
                missing_count = data.isnull().sum().sum()
                quality_report['missing_data'][symbol] = missing_count
                
                # Check date range
                quality_report['date_range'][symbol] = {
                    'start': data.index[0],
                    'end': data.index[-1],
                    'periods': len(data)
                }
                
                # Check for data issues
                if missing_count > len(data) * 0.1:  # More than 10% missing
                    quality_report['issues'].append(f"{symbol}: High missing data ({missing_count} points)")
                
                if len(data) < 100:
                    quality_report['issues'].append(f"{symbol}: Insufficient data ({len(data)} points)")
            
            return quality_report
            
        except Exception as e:
            logger.error(f"Error validating market data: {e}")
            return quality_report
    
    def _get_time_index(self, market_data: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Get unified time index from market data"""
        
        try:
            # Find common time index
            common_index = None
            
            for symbol, data in market_data.items():
                if common_index is None:
                    common_index = data.index
                else:
                    common_index = common_index.intersection(data.index)
            
            if common_index is None or len(common_index) == 0:
                raise ValueError("No common time index found in market data")
            
            # Filter by date range
            mask = (common_index >= self.config.start_date) & (common_index <= self.config.end_date)
            filtered_index = common_index[mask]
            
            if len(filtered_index) == 0:
                raise ValueError("No data in specified date range")
            
            return filtered_index.sort_values()
            
        except Exception as e:
            logger.error(f"Error getting time index: {e}")
            raise
    
    def _get_current_data(self, market_data: Dict[str, pd.DataFrame], index: int) -> Dict[str, pd.DataFrame]:
        """Get current market data for strategy update"""
        
        try:
            current_data = {}
            time_index = self._get_time_index(market_data)
            current_time = time_index[index]
            
            for symbol, data in market_data.items():
                # Get data up to current time
                mask = data.index <= current_time
                current_data[symbol] = data.loc[mask]
            
            return current_data
            
        except Exception as e:
            logger.error(f"Error getting current data: {e}")
            return {}
    
    def _get_current_prices(self, market_data: Dict[str, pd.DataFrame], index: int) -> Dict[str, float]:
        """Get current prices for all symbols"""
        
        try:
            current_prices = {}
            time_index = self._get_time_index(market_data)
            current_time = time_index[index]
            
            for symbol, data in market_data.items():
                if current_time in data.index:
                    # Use close price if available, otherwise last available price
                    if 'close' in data.columns:
                        current_prices[symbol] = data.loc[current_time, 'close']
                    else:
                        current_prices[symbol] = data.loc[current_time].iloc[-1]
                else:
                    # Use last available price
                    available_data = data[data.index <= current_time]
                    if len(available_data) > 0:
                        if 'close' in data.columns:
                            current_prices[symbol] = available_data['close'].iloc[-1]
                        else:
                            current_prices[symbol] = available_data.iloc[-1, -1]
            
            return current_prices
            
        except Exception as e:
            logger.error(f"Error getting current prices: {e}")
            return {}
    
    def _process_signal(self, signal: StrategySignal, current_prices: Dict[str, float],
                       current_time: datetime) -> None:
        """Process trading signal"""
        
        try:
            symbol = signal.symbol
            
            if symbol not in current_prices:
                logger.warning(f"No price data for signal symbol: {symbol}")
                return
            
            current_price = current_prices[symbol]
            
            # Determine execution price based on execution model
            execution_price = self._get_execution_price(signal, current_price)
            
            # Create trade
            trade = Trade(
                trade_id=f"{signal.strategy_id}_{symbol}_{int(current_time.timestamp())}",
                strategy_id=signal.strategy_id,
                symbol=symbol,
                side="long" if signal.signal_type.value in ["buy", "increase_long"] else "short",
                quantity=signal.target_quantity,
                entry_price=execution_price,
                entry_time=current_time,
                entry_signal=signal
            )
            
            # Calculate transaction costs
            trade.commission = self.cost_calculator.calculate_commission(trade)
            trade.slippage = self.cost_calculator.calculate_slippage(trade)
            
            # Check if trade is affordable
            trade_cost = abs(trade.quantity * execution_price) + trade.commission + trade.slippage
            
            if trade_cost > self.current_portfolio.cash:
                logger.warning(f"Insufficient cash for trade: ${trade_cost:,.2f} > ${self.current_portfolio.cash:,.2f}")
                return
            
            # Execute trade
            self._execute_trade(trade)
            
            # Log signal and trade
            self.signals_log.append(signal)
            self.trade_log.append(trade)
            
            self.backtest_stats['total_trades_executed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    def _get_execution_price(self, signal: StrategySignal, current_price: float) -> float:
        """Get execution price based on execution model"""
        
        try:
            if self.config.execution_model == ExecutionModel.IMMEDIATE:
                return signal.signal_price or current_price
            
            elif self.config.execution_model == ExecutionModel.NEXT_BAR:
                # In real implementation, this would use next bar's open price
                return current_price
            
            elif self.config.execution_model == ExecutionModel.REALISTIC:
                # Add slippage to price
                slippage_factor = self.config.slippage_rate
                if signal.signal_type.value in ["buy", "increase_long"]:
                    return current_price * (1 + slippage_factor)
                else:
                    return current_price * (1 - slippage_factor)
            
            else:
                return current_price
                
        except Exception as e:
            logger.error(f"Error getting execution price: {e}")
            return current_price
    
    def _execute_trade(self, trade: Trade) -> None:
        """Execute trade and update portfolio"""
        
        try:
            # Update cash
            trade_value = trade.quantity * trade.entry_price
            total_cost = abs(trade_value) + trade.commission + trade.slippage
            
            if trade.side == "long":
                self.current_portfolio.cash -= total_cost
            else:  # short
                self.current_portfolio.cash += abs(trade_value) - trade.commission - trade.slippage
            
            # Update positions
            position = self.position_manager.update_position(trade, trade.entry_price)
            
            # Calculate trade P&L (will be zero for opening trades)
            trade.gross_pnl = 0.0  # Opening trade
            trade.net_pnl = trade.gross_pnl - trade.commission - trade.slippage
            
            logger.debug(f"Executed trade: {trade.symbol} {trade.side} {trade.quantity} @ {trade.entry_price}")
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
    
    def _update_portfolio(self, current_prices: Dict[str, float], current_time: datetime) -> None:
        """Update portfolio value and metrics"""
        
        try:
            # Update position values
            self.position_manager.update_all_positions(current_prices)
            
            # Calculate portfolio values
            self.current_portfolio.positions_value = self.position_manager.get_total_value()
            self.current_portfolio.total_value = self.current_portfolio.cash + self.position_manager.get_total_pnl()
            
            # Calculate returns
            if len(self.portfolio_history) > 0:
                previous_value = self.portfolio_history[-1].total_value
                if previous_value > 0:
                    self.current_portfolio.daily_return = (self.current_portfolio.total_value - previous_value) / previous_value
                    self.current_portfolio.cumulative_return = (self.current_portfolio.total_value - self.config.initial_capital) / self.config.initial_capital
            
            # Calculate leverage and margin
            if self.current_portfolio.total_value > 0:
                self.current_portfolio.leverage = self.current_portfolio.positions_value / self.current_portfolio.total_value
                self.current_portfolio.margin_ratio = self.current_portfolio.margin_used / self.current_portfolio.total_value
            
            # Update timestamp
            self.current_portfolio.timestamp = current_time
            
            # Copy current positions
            self.current_portfolio.positions = self.position_manager.get_positions()
            
        except Exception as e:
            logger.error(f"Error updating portfolio: {e}")
    
    def _create_backtest_result(self, strategy: BaseStrategy, start_time: datetime,
                              data_quality: Dict[str, Any]) -> BacktestResult:
        """Create comprehensive backtest result"""
        
        try:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create result object
            result = BacktestResult(
                strategy_id=strategy.strategy_id,
                backtest_config=self.config,
                backtest_start_time=start_time,
                backtest_end_time=datetime.now(),
                execution_time=execution_time,
                data_quality=data_quality
            )
            
            # Basic performance metrics
            if len(self.portfolio_history) > 0:
                result.final_portfolio_value = self.portfolio_history[-1].total_value
                result.total_return = (result.final_portfolio_value - self.config.initial_capital) / self.config.initial_capital
                
                # Create returns series
                returns_data = [p.daily_return for p in self.portfolio_history]
                dates = [p.timestamp for p in self.portfolio_history]
                result.returns_series = pd.Series(returns_data, index=dates)
                
                # Calculate performance metrics using performance calculator
                if len(result.returns_series.dropna()) > 10:
                    result.performance_metrics = self.performance_calculator.calculate_comprehensive_metrics(
                        result.returns_series, strategy.strategy_id
                    )
                    
                    if result.performance_metrics:
                        result.annualized_return = result.performance_metrics.annualized_return
                        result.volatility = result.performance_metrics.volatility
                        result.sharpe_ratio = result.performance_metrics.sharpe_ratio
                        result.max_drawdown = result.performance_metrics.max_drawdown
                        result.var_95 = result.performance_metrics.var_95
                        result.cvar_95 = result.performance_metrics.cvar_95
                        result.sortino_ratio = result.performance_metrics.sortino_ratio
                        result.calmar_ratio = result.performance_metrics.calmar_ratio
            
            # Trading statistics
            result.total_trades = len(self.trade_log)
            if result.total_trades > 0:
                pnl_values = [trade.net_pnl for trade in self.trade_log if trade.net_pnl != 0]
                
                if pnl_values:
                    winning_trades = [pnl for pnl in pnl_values if pnl > 0]
                    losing_trades = [pnl for pnl in pnl_values if pnl < 0]
                    
                    result.winning_trades = len(winning_trades)
                    result.losing_trades = len(losing_trades)
                    result.win_rate = result.winning_trades / len(pnl_values)
                    
                    if winning_trades:
                        result.avg_win = np.mean(winning_trades)
                    if losing_trades:
                        result.avg_loss = np.mean(losing_trades)
                        if result.avg_loss != 0:
                            result.profit_factor = abs(result.avg_win / result.avg_loss) if result.avg_win > 0 else 0
                
                # Transaction costs
                result.total_commission = sum(trade.commission for trade in self.trade_log)
                result.total_slippage = sum(trade.slippage for trade in self.trade_log)
                result.avg_slippage = result.total_slippage / result.total_trades
            
            # Store detailed data
            result.portfolio_history = self.portfolio_history.copy()
            result.trade_log = self.trade_log.copy()
            
            # Benchmark comparison
            if self.benchmark_data is not None and result.returns_series is not None:
                try:
                    # Align benchmark with strategy returns
                    aligned_benchmark = self.benchmark_data.reindex(result.returns_series.index, method='ffill')
                    benchmark_returns = aligned_benchmark.pct_change().dropna()
                    
                    result.benchmark_returns = benchmark_returns
                    
                    # Calculate alpha and beta
                    if len(benchmark_returns) > 10 and len(result.returns_series.dropna()) > 10:
                        strategy_returns = result.returns_series.dropna()
                        common_index = strategy_returns.index.intersection(benchmark_returns.index)
                        
                        if len(common_index) > 10:
                            strat_aligned = strategy_returns.reindex(common_index)
                            bench_aligned = benchmark_returns.reindex(common_index)
                            
                            # Calculate beta
                            covariance = np.cov(strat_aligned, bench_aligned)[0, 1]
                            benchmark_variance = np.var(bench_aligned)
                            
                            if benchmark_variance > 0:
                                result.beta = covariance / benchmark_variance
                                result.alpha = np.mean(strat_aligned) - result.beta * np.mean(bench_aligned)
                                
                                # Information ratio
                                excess_returns = strat_aligned - bench_aligned
                                if np.std(excess_returns) > 0:
                                    result.information_ratio = np.mean(excess_returns) / np.std(excess_returns)
                
                except Exception as e:
                    logger.warning(f"Error calculating benchmark metrics: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating backtest result: {e}")
            return BacktestResult(strategy_id=strategy.strategy_id, errors=[str(e)])
    
    def _shuffle_market_data(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Shuffle market data for Monte Carlo simulation"""
        
        try:
            shuffled_data = {}
            
            for symbol, data in market_data.items():
                # Simple block shuffle to maintain some temporal structure
                shuffled_data[symbol] = data.sample(frac=1).reset_index(drop=True)
                shuffled_data[symbol].index = data.index  # Keep original time index
            
            return shuffled_data
            
        except Exception as e:
            logger.error(f"Error shuffling market data: {e}")
            return market_data
    
    def get_backtest_stats(self) -> Dict[str, Any]:
        """Get backtest engine statistics"""
        
        return self.backtest_stats.copy()
    
    def export_results(self, result: BacktestResult, format_type: str = "json") -> str:
        """Export backtest results to file"""
        
        try:
            output_dir = Path(self.config.output_directory)
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{result.strategy_id}_{timestamp}"
            
            if format_type == "json":
                output_path = output_dir / f"{filename}.json"
                
                # Prepare data for JSON serialization
                export_data = {
                    'strategy_id': result.strategy_id,
                    'final_portfolio_value': result.final_portfolio_value,
                    'total_return': result.total_return,
                    'annualized_return': result.annualized_return,
                    'volatility': result.volatility,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'execution_time': result.execution_time,
                    'data_quality': result.data_quality,
                    'warnings': result.warnings,
                    'errors': result.errors
                }
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
            elif format_type == "csv":
                output_path = output_dir / f"{filename}_summary.csv"
                
                # Create summary DataFrame
                summary_data = {
                    'Metric': ['Final Portfolio Value', 'Total Return', 'Annualized Return',
                              'Volatility', 'Sharpe Ratio', 'Max Drawdown', 'Total Trades',
                              'Win Rate', 'Profit Factor'],
                    'Value': [result.final_portfolio_value, result.total_return, result.annualized_return,
                             result.volatility, result.sharpe_ratio, result.max_drawdown,
                             result.total_trades, result.win_rate, result.profit_factor]
                }
                
                df = pd.DataFrame(summary_data)
                df.to_csv(output_path, index=False)
            
            logger.info(f"Backtest results exported: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            return ""