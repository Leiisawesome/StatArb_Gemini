"""
Research and Backtesting Platform

Professional-grade research platform providing:
- Advanced backtesting engine with realistic execution
- Strategy development and testing framework
- Research tools and data analysis
- Performance optimization and parameter tuning
- Strategy comparison and ranking
- Risk-aware backtesting with transaction costs

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings

warnings.filterwarnings('ignore')


class BacktestMode(Enum):
    """Backtesting modes"""
    VECTORIZED = "vectorized"
    EVENT_DRIVEN = "event_driven"
    MONTE_CARLO = "monte_carlo"


class RebalanceFrequency(Enum):
    """Portfolio rebalancing frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SIGNAL_DRIVEN = "signal_driven"


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 1_000_000
    commission_rate: float = 0.0005
    slippage_rate: float = 0.0001
    
    # Execution parameters
    market_impact_model: str = "square_root"
    execution_delay: int = 0  # Bars delay
    
    # Risk management
    max_position_size: float = 0.1  # 10% max position
    max_leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Rebalancing
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.DAILY
    rebalance_threshold: float = 0.05  # 5% threshold
    
    # Benchmark
    benchmark_symbol: Optional[str] = None
    risk_free_rate: float = 0.02
    
    # Advanced settings
    allow_short_selling: bool = True
    margin_requirement: float = 0.5
    borrowing_cost: float = 0.03


@dataclass
class BacktestResult:
    """Comprehensive backtesting results"""
    # Performance metrics
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
    profit_factor: float = 0.0
    
    # Cost analysis
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_market_impact: float = 0.0
    
    # Time series data
    portfolio_value: pd.Series = field(default_factory=pd.Series)
    returns: pd.Series = field(default_factory=pd.Series)
    positions: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Benchmark comparison
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    cvar_95: float = 0.0
    downside_deviation: float = 0.0
    
    # Configuration used
    config: BacktestConfig = field(default_factory=BacktestConfig)
    
    # Metadata
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0


@dataclass
class StrategyPerformance:
    """Strategy performance comparison"""
    strategy_name: str
    backtest_result: BacktestResult
    
    # Ranking metrics
    risk_adjusted_return: float = 0.0
    consistency_score: float = 0.0
    robustness_score: float = 0.0
    
    # Strategy-specific metrics
    signal_quality: float = 0.0
    turnover_rate: float = 0.0
    capacity_estimate: float = 0.0


class BaseStrategy(ABC):
    """Base class for trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals"""
        pass
    
    @abstractmethod
    def calculate_positions(self, signals: pd.DataFrame, 
                          current_positions: pd.Series) -> pd.DataFrame:
        """Calculate target positions from signals"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {}
    
    def set_parameters(self, params: Dict[str, Any]):
        """Set strategy parameters"""
        pass


class BacktestEngine:
    """
    Advanced backtesting engine
    
    Features:
    - Realistic execution modeling
    - Transaction cost analysis
    - Risk management integration
    - Multi-asset backtesting
    - Performance attribution
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.portfolio_value = config.initial_capital
        self.positions = pd.Series(dtype=float)
        self.cash = config.initial_capital
        
        # Trading records
        self.trades = []
        self.portfolio_history = []
        self.position_history = []
        
        # Performance tracking
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.total_market_impact = 0.0
        
        self.logger.info(f"BacktestEngine initialized: {config.start_date} to {config.end_date}")
    
    async def run_backtest(self, 
                          strategy: BaseStrategy,
                          data: pd.DataFrame,
                          benchmark_data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """
        Run comprehensive backtest
        
        Args:
            strategy: Trading strategy
            data: Market data
            benchmark_data: Benchmark data for comparison
            
        Returns:
            BacktestResult with comprehensive analysis
        """
        start_time = datetime.now()
        
        # Filter data by date range
        data = data[(data.index >= self.config.start_date) & 
                   (data.index <= self.config.end_date)]
        
        if len(data) == 0:
            raise ValueError("No data available for backtesting period")
        
        # Generate signals
        signals = strategy.generate_signals(data)
        
        # Run backtest simulation
        await self._simulate_trading(strategy, data, signals)
        
        # Calculate performance metrics
        result = self._calculate_performance_metrics(data, benchmark_data)
        
        # Add execution metadata
        result.start_time = start_time
        result.end_time = datetime.now()
        result.execution_time = (result.end_time - start_time).total_seconds()
        result.config = self.config
        
        self.logger.info(f"Backtest completed: {result.total_return:.2%} return, "
                        f"{result.sharpe_ratio:.2f} Sharpe ratio")
        
        return result
    
    async def _simulate_trading(self, 
                              strategy: BaseStrategy,
                              data: pd.DataFrame,
                              signals: pd.DataFrame):
        """Simulate trading execution"""
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            # Get current market data
            current_prices = row
            
            # Calculate target positions
            if i < len(signals):
                signal_row = signals.iloc[i]
                target_positions = strategy.calculate_positions(
                    signal_row.to_frame().T, 
                    self.positions
                )
                
                # Execute rebalancing
                if self._should_rebalance(timestamp, target_positions):
                    await self._execute_rebalancing(
                        target_positions.iloc[0] if len(target_positions) > 0 else pd.Series(),
                        current_prices,
                        timestamp
                    )
            
            # Update portfolio value
            self._update_portfolio_value(current_prices, timestamp)
            
            # Apply risk management
            self._apply_risk_management(current_prices, timestamp)
    
    def _should_rebalance(self, timestamp: datetime, 
                         target_positions: pd.DataFrame) -> bool:
        """Determine if rebalancing is needed"""
        
        if self.config.rebalance_frequency == RebalanceFrequency.DAILY:
            return True
        elif self.config.rebalance_frequency == RebalanceFrequency.WEEKLY:
            return timestamp.weekday() == 0  # Monday
        elif self.config.rebalance_frequency == RebalanceFrequency.MONTHLY:
            return timestamp.day == 1  # First day of month
        elif self.config.rebalance_frequency == RebalanceFrequency.SIGNAL_DRIVEN:
            # Check if position changes exceed threshold
            if len(target_positions) > 0:
                target = target_positions.iloc[0]
                current = self.positions.reindex(target.index, fill_value=0)
                position_changes = abs(target - current)
                return position_changes.max() > self.config.rebalance_threshold
        
        return False
    
    async def _execute_rebalancing(self, 
                                 target_positions: pd.Series,
                                 current_prices: pd.Series,
                                 timestamp: datetime):
        """Execute portfolio rebalancing"""
        
        # Calculate position changes
        current_positions = self.positions.reindex(target_positions.index, fill_value=0)
        position_changes = target_positions - current_positions
        
        # Execute trades
        for symbol, quantity_change in position_changes.items():
            if abs(quantity_change) > 0.01:  # Minimum trade size
                price = current_prices.get(symbol, 0)
                
                if price > 0:
                    # Calculate execution costs
                    trade_value = abs(quantity_change * price)
                    commission = trade_value * self.config.commission_rate
                    slippage = trade_value * self.config.slippage_rate
                    
                    # Apply market impact
                    market_impact = self._calculate_market_impact(
                        quantity_change, price, symbol
                    )
                    
                    # Execute trade
                    execution_price = price * (1 + market_impact)
                    total_cost = commission + slippage + abs(quantity_change * price * market_impact)
                    
                    # Update positions and cash
                    self.positions[symbol] = self.positions.get(symbol, 0) + quantity_change
                    self.cash -= quantity_change * execution_price + total_cost
                    
                    # Record trade
                    self.trades.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'quantity': quantity_change,
                        'price': execution_price,
                        'commission': commission,
                        'slippage': slippage,
                        'market_impact': market_impact,
                        'total_cost': total_cost
                    })
                    
                    # Update cost tracking
                    self.total_commission += commission
                    self.total_slippage += slippage
                    self.total_market_impact += abs(quantity_change * price * market_impact)
    
    def _calculate_market_impact(self, quantity: float, price: float, symbol: str) -> float:
        """Calculate market impact for trade"""
        # Simplified market impact model
        # In practice, this would use the market impact models from execution engine
        
        trade_value = abs(quantity * price)
        
        if self.config.market_impact_model == "square_root":
            # Square root model: impact = alpha * sqrt(trade_value / avg_daily_volume)
            alpha = 0.001  # Impact coefficient
            avg_daily_volume = 10_000_000  # Assume $10M average daily volume
            impact = alpha * np.sqrt(trade_value / avg_daily_volume)
        else:
            # Linear model
            impact = trade_value * 0.0001  # 1 bp per $1M
        
        return impact * np.sign(quantity)  # Positive for buys, negative for sells
    
    def _update_portfolio_value(self, current_prices: pd.Series, timestamp: datetime):
        """Update portfolio value and record history"""
        
        # Calculate position values
        position_values = pd.Series(dtype=float)
        for symbol, quantity in self.positions.items():
            price = current_prices.get(symbol, 0)
            position_values[symbol] = quantity * price
        
        # Total portfolio value
        total_position_value = position_values.sum()
        total_portfolio_value = self.cash + total_position_value
        
        # Record history
        self.portfolio_history.append({
            'timestamp': timestamp,
            'portfolio_value': total_portfolio_value,
            'cash': self.cash,
            'position_value': total_position_value
        })
        
        self.position_history.append({
            'timestamp': timestamp,
            **self.positions.to_dict()
        })
        
        # Update current portfolio value
        self.portfolio_value = total_portfolio_value
    
    def _apply_risk_management(self, current_prices: pd.Series, timestamp: datetime):
        """Apply risk management rules"""
        
        # Stop loss check
        if self.config.stop_loss is not None:
            current_return = (self.portfolio_value - self.config.initial_capital) / self.config.initial_capital
            if current_return <= -self.config.stop_loss:
                # Liquidate all positions
                self.positions = pd.Series(dtype=float)
                self.logger.warning(f"Stop loss triggered at {timestamp}")
        
        # Take profit check
        if self.config.take_profit is not None:
            current_return = (self.portfolio_value - self.config.initial_capital) / self.config.initial_capital
            if current_return >= self.config.take_profit:
                # Liquidate all positions
                self.positions = pd.Series(dtype=float)
                self.logger.info(f"Take profit triggered at {timestamp}")
        
        # Position size limits
        for symbol, quantity in self.positions.items():
            price = current_prices.get(symbol, 0)
            position_value = abs(quantity * price)
            position_weight = position_value / self.portfolio_value
            
            if position_weight > self.config.max_position_size:
                # Reduce position to maximum allowed
                max_quantity = self.config.max_position_size * self.portfolio_value / price
                self.positions[symbol] = max_quantity * np.sign(quantity)
                self.logger.warning(f"Position size limit applied for {symbol}")
    
    def _calculate_performance_metrics(self, 
                                     data: pd.DataFrame,
                                     benchmark_data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """Calculate comprehensive performance metrics"""
        
        # Convert history to DataFrames
        portfolio_df = pd.DataFrame(self.portfolio_history).set_index('timestamp')
        trades_df = pd.DataFrame(self.trades)
        
        if len(portfolio_df) == 0:
            return BacktestResult(config=self.config)
        
        # Calculate returns
        portfolio_values = portfolio_df['portfolio_value']
        returns = portfolio_values.pct_change().dropna()
        
        # Basic performance metrics
        total_return = (portfolio_values.iloc[-1] - self.config.initial_capital) / self.config.initial_capital
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (annualized_return - self.config.risk_free_rate) / volatility if volatility > 0 else 0
        
        # Drawdown analysis
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # Trading statistics
        total_trades = len(trades_df)
        if total_trades > 0:
            winning_trades = len(trades_df[trades_df['quantity'] * trades_df['price'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades
            
            # Calculate profit factor
            gross_profit = trades_df[trades_df['quantity'] * trades_df['price'] > 0]['quantity'].sum()
            gross_loss = abs(trades_df[trades_df['quantity'] * trades_df['price'] < 0]['quantity'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        else:
            winning_trades = losing_trades = 0
            win_rate = profit_factor = 0
        
        # Risk metrics
        var_95 = returns.quantile(0.05)
        cvar_95 = returns[returns <= var_95].mean()
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        
        # Benchmark comparison
        benchmark_return = alpha = beta = information_ratio = 0
        if benchmark_data is not None:
            # Calculate benchmark metrics
            benchmark_returns = benchmark_data.pct_change().dropna()
            benchmark_return = (1 + benchmark_returns).prod() - 1
            
            # Alpha and beta calculation
            if len(benchmark_returns) == len(returns):
                covariance = np.cov(returns, benchmark_returns)[0, 1]
                benchmark_variance = np.var(benchmark_returns)
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
                alpha = annualized_return - self.config.risk_free_rate - beta * (benchmark_return - self.config.risk_free_rate)
                
                # Information ratio
                active_returns = returns - benchmark_returns
                information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252) if active_returns.std() > 0 else 0
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_commission=self.total_commission,
            total_slippage=self.total_slippage,
            total_market_impact=self.total_market_impact,
            portfolio_value=portfolio_values,
            returns=returns,
            trades=trades_df,
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta,
            information_ratio=information_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            downside_deviation=downside_deviation,
            config=self.config
        )


class ResearchEngine:
    """
    Comprehensive research engine
    
    Features:
    - Strategy development and testing
    - Parameter optimization
    - Walk-forward analysis
    - Monte Carlo simulation
    - Strategy comparison and ranking
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.strategies = {}
        self.backtest_results = {}
        
    def register_strategy(self, strategy: BaseStrategy):
        """Register a strategy for research"""
        self.strategies[strategy.name] = strategy
        self.logger.info(f"Strategy registered: {strategy.name}")
    
    async def optimize_parameters(self, 
                                strategy: BaseStrategy,
                                data: pd.DataFrame,
                                parameter_ranges: Dict[str, Tuple[float, float]],
                                optimization_metric: str = 'sharpe_ratio',
                                n_trials: int = 100) -> Dict[str, Any]:
        """
        Optimize strategy parameters
        
        Args:
            strategy: Strategy to optimize
            data: Market data
            parameter_ranges: Parameter ranges to search
            optimization_metric: Metric to optimize
            n_trials: Number of optimization trials
            
        Returns:
            Optimization results
        """
        best_params = None
        best_score = float('-inf')
        results = []
        
        # Generate parameter combinations
        for trial in range(n_trials):
            # Random parameter selection
            params = {}
            for param, (min_val, max_val) in parameter_ranges.items():
                params[param] = np.random.uniform(min_val, max_val)
            
            # Set parameters and run backtest
            strategy.set_parameters(params)
            
            config = BacktestConfig(
                start_date=data.index[0],
                end_date=data.index[-1]
            )
            
            backtest_engine = BacktestEngine(config)
            result = await backtest_engine.run_backtest(strategy, data)
            
            # Evaluate performance
            score = getattr(result, optimization_metric, 0)
            
            results.append({
                'trial': trial,
                'parameters': params.copy(),
                'score': score,
                'result': result
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        return {
            'best_parameters': best_params,
            'best_score': best_score,
            'all_results': results,
            'optimization_metric': optimization_metric
        }
    
    async def walk_forward_analysis(self, 
                                  strategy: BaseStrategy,
                                  data: pd.DataFrame,
                                  training_window: int = 252,
                                  testing_window: int = 63) -> Dict[str, Any]:
        """
        Perform walk-forward analysis
        
        Args:
            strategy: Strategy to test
            data: Market data
            training_window: Training window size
            testing_window: Testing window size
            
        Returns:
            Walk-forward analysis results
        """
        results = []
        
        for i in range(training_window, len(data) - testing_window, testing_window):
            # Split data
            train_data = data.iloc[i-training_window:i]
            test_data = data.iloc[i:i+testing_window]
            
            # Train strategy (if applicable)
            # This would depend on the specific strategy implementation
            
            # Test strategy
            config = BacktestConfig(
                start_date=test_data.index[0],
                end_date=test_data.index[-1]
            )
            
            backtest_engine = BacktestEngine(config)
            result = await backtest_engine.run_backtest(strategy, test_data)
            
            results.append({
                'training_period': (train_data.index[0], train_data.index[-1]),
                'testing_period': (test_data.index[0], test_data.index[-1]),
                'result': result
            })
        
        # Aggregate results
        total_returns = [r['result'].total_return for r in results]
        sharpe_ratios = [r['result'].sharpe_ratio for r in results]
        
        return {
            'periods': results,
            'aggregate_return': np.prod([1 + r for r in total_returns]) - 1,
            'average_sharpe': np.mean(sharpe_ratios),
            'consistency': np.std(total_returns),
            'win_rate': len([r for r in total_returns if r > 0]) / len(total_returns)
        }
    
    async def compare_strategies(self, 
                               strategies: List[BaseStrategy],
                               data: pd.DataFrame,
                               config: BacktestConfig) -> List[StrategyPerformance]:
        """
        Compare multiple strategies
        
        Args:
            strategies: List of strategies to compare
            data: Market data
            config: Backtesting configuration
            
        Returns:
            List of StrategyPerformance objects
        """
        results = []
        
        # Run backtests for all strategies
        tasks = []
        for strategy in strategies:
            backtest_engine = BacktestEngine(config)
            task = backtest_engine.run_backtest(strategy, data)
            tasks.append((strategy, task))
        
        # Wait for all backtests to complete
        for strategy, task in tasks:
            result = await task
            
            # Calculate additional metrics
            risk_adjusted_return = result.sharpe_ratio
            consistency_score = 1 / (1 + result.volatility)  # Simple consistency measure
            robustness_score = 1 / (1 + abs(result.max_drawdown))  # Robustness measure
            
            # Calculate turnover rate
            if len(result.trades) > 0:
                total_trade_value = result.trades['quantity'].abs().sum()
                turnover_rate = total_trade_value / config.initial_capital
            else:
                turnover_rate = 0
            
            performance = StrategyPerformance(
                strategy_name=strategy.name,
                backtest_result=result,
                risk_adjusted_return=risk_adjusted_return,
                consistency_score=consistency_score,
                robustness_score=robustness_score,
                turnover_rate=turnover_rate
            )
            
            results.append(performance)
        
        # Sort by risk-adjusted return
        results.sort(key=lambda x: x.risk_adjusted_return, reverse=True)
        
        return results


class StrategyDeveloper:
    """
    Strategy development and testing framework
    
    Features:
    - Strategy template generation
    - Signal analysis and validation
    - Strategy composition and combination
    - Performance attribution
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_signals(self, 
                       signals: pd.DataFrame,
                       returns: pd.Series) -> Dict[str, Any]:
        """
        Analyze signal quality and predictive power
        
        Args:
            signals: Signal data
            returns: Forward returns
            
        Returns:
            Signal analysis results
        """
        analysis = {}
        
        for signal_name in signals.columns:
            signal = signals[signal_name]
            
            # Information coefficient
            ic = signal.corr(returns)
            
            # Information coefficient stability
            rolling_ic = signal.rolling(252).corr(returns)
            ic_stability = rolling_ic.std()
            
            # Signal strength
            signal_strength = abs(ic)
            
            # Turnover analysis
            signal_changes = signal.diff().abs()
            turnover = signal_changes.mean()
            
            analysis[signal_name] = {
                'information_coefficient': ic,
                'ic_stability': ic_stability,
                'signal_strength': signal_strength,
                'turnover': turnover,
                'signal_mean': signal.mean(),
                'signal_std': signal.std()
            }
        
        return analysis
    
    def create_ensemble_strategy(self, 
                               strategies: List[BaseStrategy],
                               weights: Optional[List[float]] = None) -> BaseStrategy:
        """
        Create ensemble strategy from multiple strategies
        
        Args:
            strategies: List of base strategies
            weights: Optional weights for each strategy
            
        Returns:
            Ensemble strategy
        """
        if weights is None:
            weights = [1.0 / len(strategies)] * len(strategies)
        
        class EnsembleStrategy(BaseStrategy):
            def __init__(self, base_strategies, strategy_weights):
                super().__init__("Ensemble")
                self.base_strategies = base_strategies
                self.weights = strategy_weights
            
            def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
                ensemble_signals = pd.DataFrame(index=data.index)
                
                for i, strategy in enumerate(self.base_strategies):
                    signals = strategy.generate_signals(data)
                    
                    # Weight the signals
                    weighted_signals = signals * self.weights[i]
                    
                    # Combine signals
                    if ensemble_signals.empty:
                        ensemble_signals = weighted_signals
                    else:
                        ensemble_signals = ensemble_signals.add(weighted_signals, fill_value=0)
                
                return ensemble_signals
            
            def calculate_positions(self, signals: pd.DataFrame, 
                                  current_positions: pd.Series) -> pd.DataFrame:
                # Simple position calculation based on ensemble signals
                return signals  # This would be more sophisticated in practice
        
        return EnsembleStrategy(strategies, weights) 