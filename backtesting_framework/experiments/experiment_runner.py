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
import yaml
import json
import os
from pathlib import Path

# Import core system components
import sys
sys.path.append('../core_structure')

# Try to import core system components
try:
    from core_structure.market_data.data_manager import DataManager
    from core_structure.analytics.performance_analytics import PerformanceAnalyzer
    CORE_SYSTEM_AVAILABLE = True
except ImportError:
    CORE_SYSTEM_AVAILABLE = False
    logging.warning("Core system not available, using fallback components")

from strategies.base_strategy import BaseStrategy, StrategyConfig

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
        
        # Initialize components
        if CORE_SYSTEM_AVAILABLE:
            try:
                self.data_manager = DataManager()
                self.performance_analyzer = PerformanceAnalyzer()
            except Exception as e:
                logger.warning(f"Failed to initialize core components: {e}")
                self.data_manager = None
                self.performance_analyzer = None
        else:
            self.data_manager = None
            self.performance_analyzer = None
        
        # Initialize data integration manager
        from utils.data_integration import DataIntegrationManager
        self.data_integration = DataIntegrationManager(use_core_system=CORE_SYSTEM_AVAILABLE)
        
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
            
            # Calculate performance metrics
            result.strategy_metrics = self._calculate_performance_metrics(
                result.returns, result.benchmark_returns
            )
            
            # Generate benchmark comparison if available
            if result.benchmark_returns:
                result.benchmark_metrics = self._calculate_performance_metrics(
                    result.benchmark_returns
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
        
        Args:
            config: Experiment configuration
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        self.logger.info(f"Loading data for symbols: {config.symbols}")
        
        # Convert date strings to datetime
        start_date = pd.to_datetime(config.start_date)
        end_date = pd.to_datetime(config.end_date)
        
        # Load data using data integration manager
        data = self.data_integration.load_historical_data(
            symbols=config.symbols,
            start_date=start_date,
            end_date=end_date
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
        
        return data
        
        # Validate data
        for symbol, df in data.items():
            if len(df) < 100:
                raise ValueError(f"Insufficient data for {symbol}: {len(df)} observations")
            
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing columns for {symbol}: {missing_columns}")
        
        self.logger.info(f"Loaded {len(data)} symbols with {len(list(data.values())[0])} observations each")
        return data
    
    def _initialize_strategy(self, config: ExperimentConfig) -> BaseStrategy:
        """
        Initialize strategy with configuration
        
        Args:
            config: Experiment configuration
            
        Returns:
            Initialized strategy instance
        """
        # Create strategy configuration
        strategy_config = StrategyConfig(
            name=config.name,
            symbols=config.symbols,
            position_size=config.max_position_size,
            stop_loss=config.stop_loss,
            take_profit=config.take_profit,
            commission_rate=config.commission_rate,
            slippage_rate=config.slippage_rate,
            benchmark_symbol=config.benchmark_symbol,
            risk_free_rate=config.risk_free_rate,
            **config.strategy_params
        )
        
        # Import and instantiate strategy
        try:
            # Dynamic import based on strategy class name
            strategy_module = __import__(f"strategies.{config.strategy_class.lower()}", 
                                       fromlist=[config.strategy_class])
            strategy_class = getattr(strategy_module, config.strategy_class)
            strategy = strategy_class(strategy_config)
            
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Failed to import strategy {config.strategy_class}: {e}")
            raise ValueError(f"Strategy class {config.strategy_class} not found")
        
        self.logger.info(f"Initialized strategy: {config.strategy_class}")
        return strategy
    
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
        
        # Align data timestamps
        aligned_data = self._align_data(data)
        timestamps = aligned_data.index
        
        # Initialize result
        result = ExperimentResult(
            config=config,
            start_time=datetime.now(),
            equity_curve=[config.initial_capital],
            returns=[],
            trades=[],
            signals=[],
            positions_history=[],
            drawdown_series=[]
        )
        
        # Load benchmark data if specified
        if config.benchmark_symbol:
            benchmark_data = self._load_benchmark_data(config.benchmark_symbol, timestamps)
            result.benchmark_returns = []
        
        # Run simulation
        for i, timestamp in enumerate(timestamps):
            # Get current market data
            current_data = {}
            current_prices = {}
            
            for symbol in config.symbols:
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
            
            # Record data
            result.equity_curve.append(strategy.portfolio_value * config.initial_capital)
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
            if config.benchmark_symbol and benchmark_data is not None:
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
            benchmark_data = self.data_manager.load_historical_data(
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
                                     benchmark_returns: Optional[List[float]] = None) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics
        
        Args:
            returns: Strategy returns
            benchmark_returns: Benchmark returns (optional)
            
        Returns:
            Dictionary of performance metrics
        """
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        metrics = {
            'total_return': (1 + returns_array).prod() - 1,
            'annualized_return': (1 + returns_array).prod() ** (252 / len(returns_array)) - 1,
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
            metrics.update({
                'alpha': metrics['annualized_return'] - (1 + benchmark_array).prod() ** (252 / len(benchmark_array)) + 1,
                'beta': np.cov(returns_array, benchmark_array)[0, 1] / np.var(benchmark_array) if np.var(benchmark_array) > 0 else 0,
                'information_ratio': (metrics['annualized_return'] - (1 + benchmark_array).prod() ** (252 / len(benchmark_array)) + 1) / 
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