"""
Experiment Runner for Backtesting Framework

Main orchestrator for running backtesting experiments with strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
import os
from pathlib import Path

# Optional import for config file loading
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Import core system components
import sys
sys.path.append('../core_structure')

# Import core system components (always available in this system)
from core_structure.market_data.data_manager import DataManager
from core_structure.analytics.performance_analytics import PerformanceAnalyzer

from ..strategies.base_strategy import BaseStrategy, StrategyConfig

logger = logging.getLogger(__name__)

@dataclass
class ExperimentConfig:
    """Configuration for backtesting experiments"""
    # Experiment identification
    name: str = "Default Experiment"
    description: str = ""
    version: str = "1.0.0"
    
    # Data configuration
    symbols: List[str] = field(default_factory=lambda: ["AAPL", "MSFT"])
    start_date: str = "2023-01-01"
    end_date: str = "2023-12-31"
    
    # Strategy configuration
    strategy_class: str = "PairsTradingStrategy"
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Execution configuration
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    
    # Risk management
    max_position_size: float = 0.2
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Output configuration
    output_dir: str = "results"
    save_trades: bool = True
    save_signals: bool = True
    generate_plots: bool = True
    
    # Performance tracking
    benchmark_symbol: Optional[str] = None
    risk_free_rate: float = 0.02

@dataclass
class ExperimentResult:
    """Results from a backtesting experiment"""
    # Experiment metadata
    config: ExperimentConfig
    start_time: datetime
    end_time: datetime
    duration: float
    
    # Strategy results
    strategy_metrics: Dict[str, float]
    benchmark_metrics: Optional[Dict[str, float]] = None
    
    # Performance data
    equity_curve: List[float] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)
    benchmark_returns: Optional[List[float]] = None
    
    # Trading data
    trades: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional data
    positions_history: List[Dict[str, Any]] = field(default_factory=list)
    drawdown_series: List[float] = field(default_factory=list)

class ExperimentRunner:
    """
    Main experiment runner for backtesting strategies
    
    Provides a clean interface for running backtesting experiments
    with comprehensive result analysis and reporting.
    """
    
    def __init__(self, config: Optional[ExperimentConfig] = None):
        """
        Initialize experiment runner
        
        Args:
            config: Experiment configuration
        """
        self.config = config or ExperimentConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core system components (required - no fallbacks)
        self.data_manager = DataManager()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Initialize data integration manager (required)
        from utils.data_integration import DataIntegrationManager
        self.data_integration = DataIntegrationManager(cache_data=True)
        
        # Results storage
        self.results: List[ExperimentResult] = []
        
        self.logger.info(f"Initialized ExperimentRunner: {self.config.name}")
    
    def run_experiment(self, config: Optional[ExperimentConfig] = None) -> ExperimentResult:
        """
        Run a complete backtesting experiment
        
        Args:
            config: Experiment configuration (overrides default)
            
        Returns:
            ExperimentResult with comprehensive results
        """
        experiment_config = config or self.config
        start_time = datetime.now()
        
        self.logger.info(f"Starting experiment: {experiment_config.name}")
        
        try:
            # Load data
            data = self._load_data(experiment_config)
            
            # Initialize strategy
            strategy = self._initialize_strategy(experiment_config)
            
            # Run backtest
            result = self._run_backtest(strategy, data, experiment_config)
            
            # Extract trading dates from strategy params
            trading_start = experiment_config.strategy_params.get('trading_start')
            trading_end = experiment_config.strategy_params.get('trading_end')
            
            # Calculate performance metrics with proper date range
            result.strategy_metrics = self._calculate_performance_metrics(
                result.returns, result.benchmark_returns, trading_start, trading_end
            )
            
            # Generate benchmark comparison if available
            if result.benchmark_returns:
                # Use same date range for benchmark
                result.benchmark_metrics = self._calculate_performance_metrics(
                    result.benchmark_returns, None, trading_start, trading_end
                )
            
            # Save results
            self._save_results(result, experiment_config)
            
            # Generate reports
            if experiment_config.generate_plots:
                self._generate_plots(result, experiment_config)
            
            end_time = datetime.now()
            result.end_time = end_time
            result.duration = (end_time - start_time).total_seconds()
            
            self.results.append(result)
            
            self.logger.info(f"Experiment completed: {experiment_config.name}")
            self.logger.info(f"Duration: {result.duration:.2f} seconds")
            self.logger.info(f"Total Return: {result.strategy_metrics.get('total_return', 0):.2%}")
            self.logger.info(f"Sharpe Ratio: {result.strategy_metrics.get('sharpe_ratio', 0):.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            raise
    
    def _load_data(self, config: ExperimentConfig) -> Dict[str, pd.DataFrame]:
        """
        Load market data for the experiment
        
        Strategy-first principle: Load data based on strategy requirements,
        with experiment config providing infrastructure defaults.
        
        Requires core system integration - no fallback mechanisms.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        self.logger.info("Loading data with strategy-first configuration resolution")
        
        # Resolve strategy requirements (strategy config takes precedence)
        data_requirements = self._resolve_data_requirements(config)
        
        self.logger.info(f"Loading data for symbols: {data_requirements['symbols']}")
        self.logger.info(f"Date range: {data_requirements['start_date']} to {data_requirements['end_date']}")
        
        # Load data using resolved requirements
        data = self.data_integration.load_historical_data(
            symbols=data_requirements['symbols'],
            start_date=data_requirements['start_date'],
            end_date=data_requirements['end_date']
        )
        
        # Validate data
        validation_results = self.data_integration.validate_data(data)
        if validation_results['errors']:
            self.logger.error(f"Data validation errors: {validation_results['errors']}")
        if validation_results['warnings']:
            self.logger.warning(f"Data validation warnings: {validation_results['warnings']}")
        
        # Log data info
        data_info = self.data_integration.get_data_info(data)
        self.logger.info(f"Loaded data info: {data_info}")
        
        self.logger.info(f"Loaded {len(data)} symbols with {len(list(data.values())[0])} observations each")
        return data
    
    def _resolve_data_requirements(self, config: ExperimentConfig) -> Dict[str, Any]:
        """
        Resolve data requirements using strategy-first principle
        
        Strategy configuration takes precedence over experiment configuration.
        Experiment config provides infrastructure defaults only.
        
        Requires core system - no fallback mechanisms.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Dictionary with resolved data requirements
        """
        strategy_params = config.strategy_params
        
        # Strategy-first symbol resolution
        symbols = self._resolve_symbols(strategy_params, config.symbols)
        
        # Strategy-first date resolution
        dates = self._resolve_dates(strategy_params, config.start_date, config.end_date)
        
        return {
            'symbols': symbols,
            'start_date': dates['start_date'],
            'end_date': dates['end_date']
        }
    
    def _resolve_symbols(self, strategy_params: Dict[str, Any], infrastructure_symbols: List[str]) -> List[str]:
        """
        Resolve symbol requirements with strategy-first principle
        
        Args:
            strategy_params: Strategy configuration parameters
            infrastructure_symbols: Infrastructure default symbols from experiment config
            
        Returns:
            List of symbols to load
        """
        # Check if strategy specifies its own symbols
        if 'symbols' in strategy_params:
            symbols = strategy_params['symbols']
            self.logger.info(f"Using strategy-specified symbols: {len(symbols)} symbols")
            return symbols
        
        # Check if strategy needs universe-based symbol selection
        if 'universe_size' in strategy_params:
            universe_size = strategy_params['universe_size']
            min_market_cap = strategy_params.get('min_market_cap', 1e9)
            min_avg_volume = strategy_params.get('min_avg_volume', 1e6)
            
            self.logger.info(f"Strategy requires universe selection: {universe_size} symbols")
            self.logger.info(f"Criteria: min_market_cap=${min_market_cap:,.0f}, min_volume=${min_avg_volume:,.0f}")
            
            # Use core system for universe selection (required - no fallbacks)
            universe_symbols = self.data_integration.get_universe_symbols(
                universe_size=universe_size,
                min_market_cap=min_market_cap,
                min_avg_volume=min_avg_volume
            )
            
            if not universe_symbols:
                raise RuntimeError(f"Core system failed to provide universe symbols for size={universe_size}")
            
            self.logger.info(f"Core system provided {len(universe_symbols)} universe symbols")
            return universe_symbols
        
        # Use experiment infrastructure defaults (not fallbacks, but default infrastructure symbols)
        self.logger.info(f"Using experiment infrastructure symbols: {infrastructure_symbols}")
        return infrastructure_symbols
    
    def _resolve_dates(self, strategy_params: Dict[str, Any], 
                      infrastructure_start: str, infrastructure_end: str) -> Dict[str, pd.Timestamp]:
        """
        Resolve date requirements with strategy-first principle
        
        Args:
            strategy_params: Strategy configuration parameters
            infrastructure_start: Infrastructure default start date from experiment config
            infrastructure_end: Infrastructure default end date from experiment config
            
        Returns:
            Dictionary with resolved start and end dates
        """
        # Strategy with training/trading phases (e.g., MomentumStrategy)
        if 'training_start' in strategy_params and 'trading_end' in strategy_params:
            start_date = pd.to_datetime(strategy_params['training_start'])
            end_date = pd.to_datetime(strategy_params['trading_end'])
            
            self.logger.info(f"Strategy defines training/trading phases: {start_date} to {end_date}")
            return {'start_date': start_date, 'end_date': end_date}
        
        # Strategy with explicit date overrides
        elif 'start_date' in strategy_params and 'end_date' in strategy_params:
            start_date = pd.to_datetime(strategy_params['start_date'])
            end_date = pd.to_datetime(strategy_params['end_date'])
            
            self.logger.info(f"Strategy specifies explicit dates: {start_date} to {end_date}")
            return {'start_date': start_date, 'end_date': end_date}
        
        # Use experiment infrastructure defaults
        start_date = pd.to_datetime(infrastructure_start)
        end_date = pd.to_datetime(infrastructure_end)
        
        self.logger.info(f"Using experiment infrastructure dates: {start_date} to {end_date}")
        return {'start_date': start_date, 'end_date': end_date}
    
    def _initialize_strategy(self, config: ExperimentConfig) -> BaseStrategy:
        """
        Initialize strategy with strategy-first configuration resolution
        
        Strategy parameters take precedence over experiment parameters.
        Experiment config provides infrastructure defaults only.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Initialized strategy instance
        """
        # Resolve configuration with strategy-first principle
        resolved_config = self._resolve_strategy_configuration(config)
        
        # Import strategy module first to get the config class
        try:
            # Convert CamelCase to snake_case for module name
            module_name = config.strategy_class
            # Convert CamelCase to snake_case
            snake_case_name = ''.join(['_' + c.lower() if c.isupper() and i > 0 else c.lower() 
                                     for i, c in enumerate(module_name)])
            
            strategy_module = __import__(f"strategies.{snake_case_name}", 
                                       fromlist=[config.strategy_class])
            
            # Try to find strategy-specific config class
            strategy_config_class = getattr(strategy_module, f"{config.strategy_class}Config", None)
            if strategy_config_class is None:
                # Try alternative naming patterns
                strategy_config_class = getattr(strategy_module, "MultiFactorConfig", None)
                if strategy_config_class is None:
                    strategy_config_class = getattr(strategy_module, "MomentumConfig", None)
                    if strategy_config_class is None:
                        # Fallback to base StrategyConfig
                        strategy_config_class = StrategyConfig
            
            # Get field names from the config class
            import dataclasses
            if dataclasses.is_dataclass(strategy_config_class):
                strategy_config_fields = {field.name for field in dataclasses.fields(strategy_config_class)}
            else:
                # Fallback to base StrategyConfig fields
                strategy_config_fields = {
                    'symbols', 'name', 'version', 'position_size', 'max_positions',
                    'stop_loss', 'take_profit', 'max_drawdown', 'commission_rate',
                    'slippage_rate', 'lookback_window', 'min_data_points',
                    'benchmark_symbol', 'risk_free_rate'
                }
            
            # Only pass parameters that the strategy config recognizes
            filtered_config = {k: v for k, v in resolved_config.items() 
                              if k in strategy_config_fields}
            
            # Create strategy configuration with strategy-specific config class
            strategy_config = strategy_config_class(**filtered_config)
            
            # Get strategy class and instantiate
            strategy_class = getattr(strategy_module, config.strategy_class)
            strategy = strategy_class(strategy_config)
            
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to import strategy {config.strategy_class}: {e}")
            raise ValueError(f"Strategy class {config.strategy_class} not found")
        
        self.logger.info(f"Initialized strategy: {config.strategy_class}")
        return strategy
    
    def _resolve_strategy_configuration(self, config: ExperimentConfig) -> Dict[str, Any]:
        """
        Resolve strategy configuration using strategy-first principle
        
        Priority order:
        1. Strategy-specific parameters (from strategy_params)
        2. Experiment infrastructure parameters (fallback)
        
        Args:
            config: Experiment configuration
            
        Returns:
            Dictionary with resolved configuration parameters
        """
        strategy_params = config.strategy_params.copy()
        
        # Resolve symbols using strategy-first principle
        resolved_symbols = self._resolve_symbols(strategy_params, config.symbols)
        
        # Define strategy-first parameter mappings
        # Strategy parameters take precedence over experiment parameters
        parameter_mappings = {
            # Core parameters (use resolved values)
            'name': config.name,
            'symbols': resolved_symbols,  # Use strategy-resolved symbols, not experiment symbols
            
            # Financial parameters (strategy takes precedence)
            'commission_rate': strategy_params.get('commission_rate', config.commission_rate),
            'slippage_rate': strategy_params.get('slippage_rate', config.slippage_rate),
            'benchmark_symbol': strategy_params.get('benchmark_symbol', config.benchmark_symbol),
            'risk_free_rate': strategy_params.get('risk_free_rate', config.risk_free_rate),
            
            # Position sizing (strategy defines its own logic)
            'position_size': strategy_params.get('position_size', config.max_position_size),
            
            # Risk management (strategy takes precedence)
            'stop_loss': strategy_params.get('stop_loss', config.stop_loss),
            'take_profit': strategy_params.get('take_profit', config.take_profit),
        }
        
        # Add all strategy-specific parameters (these always take precedence)
        resolved_config = {**parameter_mappings, **strategy_params}
        
        # Log configuration resolution
        strategy_overrides = [k for k in strategy_params.keys() 
                            if k in parameter_mappings and strategy_params.get(k) != parameter_mappings.get(k)]
        
        if strategy_overrides:
            self.logger.info(f"Strategy overrides experiment config for: {strategy_overrides}")
        
        # Log symbol resolution
        if len(resolved_symbols) != len(config.symbols) or set(resolved_symbols) != set(config.symbols):
            self.logger.info(f"Strategy symbols differ from experiment: {len(resolved_symbols)} vs {len(config.symbols)} symbols")
        
        return resolved_config
    
    def _resolve_benchmark_symbol(self, config: ExperimentConfig) -> Optional[str]:
        """
        Resolve benchmark symbol using strategy-first principle
        
        Args:
            config: Experiment configuration
            
        Returns:
            Benchmark symbol to use, or None
        """
        strategy_params = config.strategy_params
        
        # Strategy-specified benchmark takes precedence
        if 'benchmark_symbol' in strategy_params:
            benchmark = strategy_params['benchmark_symbol']
            if benchmark:
                self.logger.info(f"Using strategy-specified benchmark: {benchmark}")
                return benchmark
        
        # Fall back to experiment benchmark
        if config.benchmark_symbol:
            self.logger.info(f"Using experiment fallback benchmark: {config.benchmark_symbol}")
            return config.benchmark_symbol
        
        # No benchmark specified
        self.logger.info("No benchmark specified")
        return None
    
    def _resolve_initial_capital(self, config: ExperimentConfig) -> float:
        """
        Resolve initial capital using strategy-first principle
        
        Args:
            config: Experiment configuration
            
        Returns:
            Initial capital to use
        """
        strategy_params = config.strategy_params
        
        # Strategy-specified initial capital takes precedence
        if 'initial_capital' in strategy_params:
            capital = strategy_params['initial_capital']
            self.logger.info(f"Using strategy-specified initial capital: ${capital:,.0f}")
            return capital
        
        # Fall back to experiment infrastructure defaults
        self.logger.info(f"Using experiment infrastructure initial capital: ${config.initial_capital:,.0f}")
        return config.initial_capital
    
    def _run_backtest(self, strategy: BaseStrategy, data: Dict[str, pd.DataFrame], 
                     config: ExperimentConfig) -> ExperimentResult:
        """
        Run the actual backtest simulation
        
        Args:
            strategy: Strategy instance
            data: Market data
            config: Experiment configuration
            
        Returns:
            ExperimentResult with backtest data
        """
        self.logger.info("Starting backtest simulation")
        
        # Get resolved requirements (strategy-first)
        data_requirements = self._resolve_data_requirements(config)
        resolved_symbols = data_requirements['symbols']
        
        # Resolve initial capital (strategy can override experiment capital)
        initial_capital = self._resolve_initial_capital(config)
        
        # Align data timestamps
        aligned_data = self._align_data(data)
        timestamps = aligned_data.index
        
        # Initialize result with defaults for required fields
        result = ExperimentResult(
            config=config,
            start_time=datetime.now(),
            end_time=datetime.now(),  # Will be updated at the end
            duration=0.0,  # Will be calculated at the end
            strategy_metrics={},  # Will be calculated at the end
            equity_curve=[initial_capital],
            returns=[],
            trades=[],
            signals=[],
            positions_history=[],
            drawdown_series=[]
        )
        
        # Load benchmark data if specified (strategy preference takes precedence)
        benchmark_symbol = self._resolve_benchmark_symbol(config)
        if benchmark_symbol:
            benchmark_data = self._load_benchmark_data(benchmark_symbol, timestamps)
            result.benchmark_returns = []
        
        # Run simulation
        for i, timestamp in enumerate(timestamps):
            # Get current market data
            current_data = {}
            current_prices = {}
            
            # Use resolved symbols (strategy-first) instead of experiment symbols
            for symbol in resolved_symbols:
                if symbol in aligned_data.columns:
                    symbol_data = data[symbol].loc[:timestamp]
                    current_data[symbol] = symbol_data
                    current_prices[symbol] = aligned_data.loc[timestamp, symbol]
            
            # Generate signals
            signals = strategy.process_signals(timestamp, current_data)
            
            # Execute trades
            trades = strategy.execute_trades(signals, current_prices)
            
            # Update portfolio value
            strategy.update_portfolio_value(current_prices)
            
            # Record data (strategy.portfolio_value is already in dollars)
            result.equity_curve.append(strategy.portfolio_value)
            result.trades.extend(trades)
            result.signals.extend([{
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type.value,
                'strength': signal.strength,
                'confidence': signal.confidence,
                'price': signal.price
            } for signal in signals])
            
            # Record positions
            result.positions_history.append({
                'timestamp': timestamp,
                'positions': strategy.get_state()['positions'],
                'cash': strategy.get_state()['cash'],
                'portfolio_value': strategy.get_state()['portfolio_value']
            })
            
            # Calculate drawdown
            if len(result.equity_curve) > 1:
                peak = max(result.equity_curve)
                current = result.equity_curve[-1]
                drawdown = (current - peak) / peak
                result.drawdown_series.append(drawdown)
            
            # Update benchmark returns
            if benchmark_symbol and benchmark_data is not None:
                if i > 0:
                    benchmark_return = (benchmark_data.iloc[i] / benchmark_data.iloc[i-1]) - 1
                    result.benchmark_returns.append(benchmark_return)
                else:
                    result.benchmark_returns.append(0.0)
        
        # Calculate returns from equity curve
        equity_array = np.array(result.equity_curve)
        result.returns = list(np.diff(equity_array) / equity_array[:-1])
        
        self.logger.info(f"Backtest completed: {len(result.trades)} trades executed")
        return result
    
    def _align_data(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Align data from multiple symbols to common timestamps
        
        Args:
            data: Dictionary of symbol DataFrames
            
        Returns:
            Aligned DataFrame with close prices
        """
        # Extract close prices
        close_prices = {}
        for symbol, df in data.items():
            close_prices[symbol] = df['close']
        
        # Align to common index
        aligned = pd.DataFrame(close_prices)
        aligned = aligned.dropna()  # Remove any missing data
        
        return aligned
    
    def _load_benchmark_data(self, benchmark_symbol: str, timestamps: pd.DatetimeIndex) -> Optional[pd.Series]:
        """
        Load benchmark data for comparison
        
        Args:
            benchmark_symbol: Benchmark symbol
            timestamps: Timestamps to align with
            
        Returns:
            Benchmark price series
        """
        try:
            # Use the same data integration manager for consistency
            benchmark_data = self.data_integration.load_historical_data(
                symbols=[benchmark_symbol],
                start_date=timestamps[0],
                end_date=timestamps[-1]
            )
            
            if benchmark_symbol in benchmark_data:
                return benchmark_data[benchmark_symbol]['close'].reindex(timestamps).fillna(method='ffill')
            
        except Exception as e:
            self.logger.warning(f"Failed to load benchmark data: {e}")
        
        return None
    
    def _calculate_performance_metrics(self, returns: List[float], 
                                     benchmark_returns: Optional[List[float]] = None,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            returns: Strategy returns
            benchmark_returns: Benchmark returns (optional)
            start_date: Trading start date (optional)
            end_date: Trading end date (optional)
            
        Returns:
            Dictionary of performance metrics
        """
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        # Calculate actual time period for proper annualization
        if start_date and end_date:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            time_period_days = (end_dt - start_dt).days
            time_period_years = time_period_days / 365.25  # Account for leap years
            
            # Calculate annualized return using actual time period
            total_return = (1 + returns_array).prod() - 1
            annualized_return = ((1 + total_return) ** (1 / time_period_years)) - 1
        else:
            # Fallback to trading days assumption (legacy method)
            total_return = (1 + returns_array).prod() - 1
            annualized_return = (1 + total_return) ** (252 / len(returns_array)) - 1
        
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': np.std(returns_array) * np.sqrt(252),
            'sharpe_ratio': np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(returns_array),
            'win_rate': np.mean(returns_array > 0),
            'profit_factor': self._calculate_profit_factor(returns_array),
            'calmar_ratio': 0.0,  # Will be calculated if max_drawdown > 0
            'sortino_ratio': self._calculate_sortino_ratio(returns_array)
        }
        
        # Calculate Calmar ratio
        if metrics['max_drawdown'] != 0:
            metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
        
        # Add benchmark comparison if available
        if benchmark_returns:
            benchmark_array = np.array(benchmark_returns)
            
            # Calculate benchmark return using same time period method
            if start_date and end_date:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                time_period_days = (end_dt - start_dt).days
                time_period_years = time_period_days / 365.25
                
                benchmark_total_return = (1 + benchmark_array).prod() - 1
                benchmark_annualized_return = ((1 + benchmark_total_return) ** (1 / time_period_years)) - 1
            else:
                # Fallback method
                benchmark_annualized_return = (1 + benchmark_array).prod() ** (252 / len(benchmark_array)) - 1
            
            metrics.update({
                'alpha': metrics['annualized_return'] - benchmark_annualized_return,
                'beta': np.cov(returns_array, benchmark_array)[0, 1] / np.var(benchmark_array) if np.var(benchmark_array) > 0 else 0,
                'information_ratio': (metrics['annualized_return'] - benchmark_annualized_return) / 
                                   (np.std(returns_array - benchmark_array) * np.sqrt(252)) if np.std(returns_array - benchmark_array) > 0 else 0
            })
        
        return metrics
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)
    
    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """Calculate profit factor"""
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]
        
        if len(winning_returns) == 0 or len(losing_returns) == 0:
            return 0.0
        
        return np.sum(winning_returns) / abs(np.sum(losing_returns))
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sortino ratio"""
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return 0.0
        
        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0.0
        
        return np.mean(returns) / downside_deviation * np.sqrt(252)
    
    def _save_results(self, result: ExperimentResult, config: ExperimentConfig):
        """Save experiment results to files"""
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config_file = output_dir / f"{config.name}_config.json"
        with open(config_file, 'w') as f:
            json.dump(self._config_to_dict(config), f, indent=2, default=str)
        
        # Save results
        results_file = output_dir / f"{config.name}_results.json"
        with open(results_file, 'w') as f:
            json.dump(self._result_to_dict(result), f, indent=2, default=str)
        
        # Save trades if requested
        if config.save_trades and result.trades:
            trades_file = output_dir / f"{config.name}_trades.csv"
            trades_df = pd.DataFrame(result.trades)
            trades_df.to_csv(trades_file, index=False)
        
        # Save signals if requested
        if config.save_signals and result.signals:
            signals_file = output_dir / f"{config.name}_signals.csv"
            signals_df = pd.DataFrame(result.signals)
            signals_df.to_csv(signals_file, index=False)
        
        self.logger.info(f"Results saved to {output_dir}")
    
    def _generate_plots(self, result: ExperimentResult, config: ExperimentConfig):
        """Generate performance plots"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            output_dir = Path(config.output_dir)
            plots_dir = output_dir / "plots"
            plots_dir.mkdir(exist_ok=True)
            
            # Set style
            plt.style.use('seaborn-v0_8')
            
            # Equity curve
            plt.figure(figsize=(12, 8))
            plt.plot(result.equity_curve, label='Strategy', linewidth=2)
            if result.benchmark_returns:
                benchmark_equity = [1.0]
                for ret in result.benchmark_returns:
                    benchmark_equity.append(benchmark_equity[-1] * (1 + ret))
                plt.plot(benchmark_equity, label='Benchmark', linewidth=2, alpha=0.7)
            
            plt.title(f'Equity Curve - {config.name}')
            plt.xlabel('Time')
            plt.ylabel('Portfolio Value')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(plots_dir / f"{config.name}_equity_curve.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            # Drawdown
            if result.drawdown_series:
                plt.figure(figsize=(12, 6))
                plt.plot(result.drawdown_series, color='red', linewidth=2)
                plt.title(f'Drawdown - {config.name}')
                plt.xlabel('Time')
                plt.ylabel('Drawdown')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(plots_dir / f"{config.name}_drawdown.png", dpi=300, bbox_inches='tight')
                plt.close()
            
            self.logger.info(f"Plots generated in {plots_dir}")
            
        except ImportError:
            self.logger.warning("matplotlib not available, skipping plot generation")
    
    def _config_to_dict(self, config: ExperimentConfig) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""
        return {
            'name': config.name,
            'description': config.description,
            'version': config.version,
            'symbols': config.symbols,
            'start_date': config.start_date,
            'end_date': config.end_date,
            'strategy_class': config.strategy_class,
            'strategy_params': config.strategy_params,
            'initial_capital': config.initial_capital,
            'commission_rate': config.commission_rate,
            'slippage_rate': config.slippage_rate,
            'max_position_size': config.max_position_size,
            'stop_loss': config.stop_loss,
            'take_profit': config.take_profit,
            'benchmark_symbol': config.benchmark_symbol,
            'risk_free_rate': config.risk_free_rate
        }
    
    def _result_to_dict(self, result: ExperimentResult) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization"""
        return {
            'config': self._config_to_dict(result.config),
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'duration': result.duration,
            'strategy_metrics': result.strategy_metrics,
            'benchmark_metrics': result.benchmark_metrics,
            'total_trades': len(result.trades),
            'total_signals': len(result.signals),
            'final_portfolio_value': result.equity_curve[-1] if result.equity_curve else 0
        }
    
    def load_config_from_file(self, config_file: str) -> ExperimentConfig:
        """
        Load experiment configuration from YAML file
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            ExperimentConfig instance
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is required for loading config files. Install with: pip install PyYAML")
            
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return ExperimentConfig(**config_data)
    
    def run_experiment_from_file(self, config_file: str) -> ExperimentResult:
        """
        Run experiment from configuration file
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            ExperimentResult
        """
        config = self.load_config_from_file(config_file)
        return self.run_experiment(config) 