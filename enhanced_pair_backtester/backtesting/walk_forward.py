"""
Walk Forward Analysis for Enhanced Pair Trading System

This module implements rolling window optimization and out-of-sample testing
for systematic validation of trading strategies across different market regimes.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)

@dataclass
class WalkForwardConfig:
    """Configuration for walk forward analysis."""
    
    # Time windows
    train_window_days: int = 252  # 1 year training window
    test_window_days: int = 63    # 3 months testing window
    step_size_days: int = 21      # 3 weeks step size
    min_observations: int = 1000  # Minimum observations for training
    
    # Optimization parameters
    optimize_parameters: bool = True
    parameter_grid: Dict[str, List[Any]] = field(default_factory=lambda: {
        'z_entry_threshold': [1.5, 2.0, 2.5],
        'z_exit_threshold': [0.5, 1.0, 1.5],
        'lookback_window': [20, 40, 60],
        'position_size': [0.1, 0.2, 0.3]
    })
    
    # Performance criteria
    optimization_metric: str = 'sharpe_ratio'  # 'sharpe_ratio', 'total_return', 'max_drawdown'
    min_trades_per_period: int = 5
    max_drawdown_threshold: float = 0.2
    
    # Parallel processing
    use_parallel: bool = True
    max_workers: int = 4
    
    # Validation
    require_positive_returns: bool = True
    min_sharpe_ratio: float = 0.5

@dataclass
class WalkForwardPeriod:
    """Results for a single walk forward period."""
    
    # Period information
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    # Optimization results
    best_parameters: Dict[str, Any]
    optimization_score: float
    
    # Out-of-sample performance
    oos_returns: np.ndarray
    oos_trades: int
    oos_sharpe: float
    oos_total_return: float
    oos_max_drawdown: float
    oos_win_rate: float
    
    # Additional metrics
    regime_distribution: Dict[str, float] = field(default_factory=dict)
    signal_statistics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate additional derived metrics."""
        if len(self.oos_returns) > 0:
            self.oos_volatility = np.std(self.oos_returns) * np.sqrt(252)
            self.oos_skewness = float(pd.Series(self.oos_returns).skew())
            self.oos_kurtosis = float(pd.Series(self.oos_returns).kurtosis())
        else:
            self.oos_volatility = 0.0
            self.oos_skewness = 0.0
            self.oos_kurtosis = 0.0

@dataclass
class WalkForwardResult:
    """Complete walk forward analysis results."""
    
    # Configuration
    config: WalkForwardConfig
    
    # Period results
    periods: List[WalkForwardPeriod]
    
    # Aggregate statistics
    total_periods: int
    successful_periods: int
    
    # Performance metrics
    aggregate_returns: np.ndarray
    aggregate_sharpe: float
    aggregate_total_return: float
    aggregate_max_drawdown: float
    aggregate_win_rate: float
    
    # Stability metrics
    sharpe_stability: float  # Std dev of period Sharpe ratios
    return_stability: float  # Std dev of period returns
    parameter_stability: Dict[str, float] = field(default_factory=dict)
    
    # Regime analysis
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate aggregate statistics."""
        if self.periods:
            # Calculate aggregate metrics
            all_returns = np.concatenate([p.oos_returns for p in self.periods])
            self.aggregate_returns = all_returns
            
            if len(all_returns) > 0:
                self.aggregate_sharpe = float(np.mean(all_returns) / np.std(all_returns) * np.sqrt(252))
                self.aggregate_total_return = float(np.prod(1 + all_returns) - 1)
                
                # Calculate max drawdown
                cumulative = np.cumprod(1 + all_returns)
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                self.aggregate_max_drawdown = float(np.min(drawdown))
                
                # Win rate
                self.aggregate_win_rate = float(np.mean(all_returns > 0))
            
            # Stability metrics
            period_sharpes = [p.oos_sharpe for p in self.periods if not np.isnan(p.oos_sharpe)]
            self.sharpe_stability = float(np.std(period_sharpes)) if period_sharpes else 0.0
            
            period_returns = [p.oos_total_return for p in self.periods]
            self.return_stability = float(np.std(period_returns)) if period_returns else 0.0
            
            # Parameter stability
            for param in self.config.parameter_grid.keys():
                param_values = [p.best_parameters.get(param, 0) for p in self.periods]
                self.parameter_stability[param] = float(np.std(param_values)) if param_values else 0.0

class WalkForwardAnalyzer:
    """Main walk forward analysis engine."""
    
    def __init__(self, config: WalkForwardConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def run_analysis(self, 
                    data: pd.DataFrame,
                    strategy_func: Callable,
                    **kwargs) -> WalkForwardResult:
        """
        Run complete walk forward analysis.
        
        Args:
            data: Price data with datetime index
            strategy_func: Function that runs strategy with given parameters
            **kwargs: Additional arguments for strategy function
            
        Returns:
            WalkForwardResult with comprehensive analysis
        """
        self.logger.info("Starting walk forward analysis...")
        
        # Generate time periods
        periods = self._generate_periods(data)
        self.logger.info(f"Generated {len(periods)} walk forward periods")
        
        # Run analysis for each period
        results = []
        
        if self.config.use_parallel and len(periods) > 1:
            results = self._run_parallel_analysis(periods, data, strategy_func, **kwargs)
        else:
            results = self._run_sequential_analysis(periods, data, strategy_func, **kwargs)
        
        # Filter successful periods
        successful_results = [r for r in results if r is not None]
        
        self.logger.info(f"Completed {len(successful_results)}/{len(periods)} periods successfully")
        
        # Create final result
        return WalkForwardResult(
            config=self.config,
            periods=successful_results,
            total_periods=len(periods),
            successful_periods=len(successful_results),
            aggregate_returns=np.array([]),  # Will be calculated in __post_init__
            aggregate_sharpe=0.0,
            aggregate_total_return=0.0,
            aggregate_max_drawdown=0.0,
            aggregate_win_rate=0.0,
            sharpe_stability=0.0,
            return_stability=0.0
        )
    
    def _generate_periods(self, data: pd.DataFrame) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """Generate train/test period combinations."""
        periods = []
        
        start_date = data.index[0]
        end_date = data.index[-1]
        
        current_date = start_date
        
        while current_date + timedelta(days=self.config.train_window_days + self.config.test_window_days) <= end_date:
            train_start = current_date
            train_end = current_date + timedelta(days=self.config.train_window_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.config.test_window_days)
            
            # Ensure we have enough data
            train_data = data[train_start:train_end]
            test_data = data[test_start:test_end]
            
            if len(train_data) >= self.config.min_observations and len(test_data) > 0:
                periods.append((train_start, train_end, test_start, test_end))
            
            current_date += timedelta(days=self.config.step_size_days)
        
        return periods
    
    def _run_sequential_analysis(self, periods, data, strategy_func, **kwargs) -> List[Optional[WalkForwardPeriod]]:
        """Run analysis sequentially."""
        results = []
        
        for i, (train_start, train_end, test_start, test_end) in enumerate(periods):
            self.logger.info(f"Processing period {i+1}/{len(periods)}: {test_start.strftime('%Y-%m-%d')} to {test_end.strftime('%Y-%m-%d')}")
            
            result = self._analyze_period(
                train_start, train_end, test_start, test_end,
                data, strategy_func, **kwargs
            )
            results.append(result)
        
        return results
    
    def _run_parallel_analysis(self, periods, data, strategy_func, **kwargs) -> List[Optional[WalkForwardPeriod]]:
        """Run analysis in parallel."""
        results: List[Optional[WalkForwardPeriod]] = [None] * len(periods)
        
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_index = {}
            for i, (train_start, train_end, test_start, test_end) in enumerate(periods):
                future = executor.submit(
                    self._analyze_period,
                    train_start, train_end, test_start, test_end,
                    data, strategy_func, **kwargs
                )
                future_to_index[future] = i
            
            # Collect results
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    self.logger.info(f"Completed period {index+1}/{len(periods)}")
                except Exception as e:
                    self.logger.error(f"Error in period {index+1}: {e}")
                    results[index] = None
        
        return results
    
    def _analyze_period(self, 
                       train_start: datetime, 
                       train_end: datetime,
                       test_start: datetime, 
                       test_end: datetime,
                       data: pd.DataFrame,
                       strategy_func: Callable,
                       **kwargs) -> Optional[WalkForwardPeriod]:
        """Analyze a single walk forward period."""
        try:
            # Split data
            train_data = data.loc[train_start:train_end]
            test_data = data.loc[test_start:test_end]
            
            if len(train_data) < self.config.min_observations:
                self.logger.warning(f"Insufficient training data: {len(train_data)} < {self.config.min_observations}")
                return None
            
            # Optimize parameters on training data
            if self.config.optimize_parameters:
                best_params, best_score = self._optimize_parameters(train_data, strategy_func, **kwargs)
            else:
                best_params = {}
                best_score = 0.0
            
            # Run strategy on test data with optimized parameters
            test_kwargs = {**kwargs, **best_params}
            test_result = strategy_func(test_data, **test_kwargs)
            
            # Extract performance metrics
            if hasattr(test_result, 'returns') and len(test_result.returns) > 0:
                returns = test_result.returns
                trades = len(test_result.trades) if hasattr(test_result, 'trades') else 0
                
                # Calculate metrics
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
                total_return = np.prod(1 + returns) - 1
                
                # Max drawdown
                cumulative = np.cumprod(1 + returns)
                running_max = np.maximum.accumulate(cumulative)
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = np.min(drawdown)
                
                win_rate = np.mean(returns > 0)
                
                # Validation checks
                if self.config.require_positive_returns and total_return <= 0:
                    self.logger.warning(f"Period failed: negative returns ({total_return:.4f})")
                    return None
                
                if sharpe < self.config.min_sharpe_ratio:
                    self.logger.warning(f"Period failed: low Sharpe ratio ({sharpe:.4f})")
                    return None
                
                if trades < self.config.min_trades_per_period:
                    self.logger.warning(f"Period failed: insufficient trades ({trades})")
                    return None
                
                # Create period result
                return WalkForwardPeriod(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                    best_parameters=best_params,
                    optimization_score=best_score,
                    oos_returns=returns,
                    oos_trades=trades,
                    oos_sharpe=sharpe,
                    oos_total_return=total_return,
                    oos_max_drawdown=max_drawdown,
                    oos_win_rate=win_rate
                )
            
            else:
                self.logger.warning("Strategy returned no valid results")
                return None
                
        except Exception as e:
            self.logger.error(f"Error analyzing period {train_start} to {test_end}: {e}")
            return None
    
    def _optimize_parameters(self, 
                           train_data: pd.DataFrame, 
                           strategy_func: Callable,
                           **kwargs) -> Tuple[Dict[str, Any], float]:
        """Optimize parameters on training data."""
        best_params = {}
        best_score = float('-inf')
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations()
        
        for params in param_combinations:
            try:
                # Run strategy with these parameters
                test_kwargs = {**kwargs, **params}
                result = strategy_func(train_data, **test_kwargs)
                
                # Calculate optimization score
                if hasattr(result, 'returns') and len(result.returns) > 0:
                    score = self._calculate_optimization_score(result.returns)
                    
                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        
            except Exception as e:
                self.logger.debug(f"Parameter combination failed: {params}, error: {e}")
                continue
        
        return best_params, best_score
    
    def _generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations from grid."""
        import itertools
        
        param_names = list(self.config.parameter_grid.keys())
        param_values = list(self.config.parameter_grid.values())
        
        combinations = []
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)
        
        return combinations
    
    def _calculate_optimization_score(self, returns: np.ndarray) -> float:
        """Calculate optimization score based on selected metric."""
        if len(returns) == 0:
            return float('-inf')
        
        if self.config.optimization_metric == 'sharpe_ratio':
            return float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0.0
        
        elif self.config.optimization_metric == 'total_return':
            return float(np.prod(1 + returns) - 1)
        
        elif self.config.optimization_metric == 'max_drawdown':
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            return float(-np.min(drawdown))  # Negative because we want to maximize (minimize drawdown)
        
        else:
            return float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0.0

    def generate_report(self, result: WalkForwardResult) -> str:
        """Generate comprehensive walk forward analysis report."""
        report = []
        report.append("=" * 80)
        report.append("WALK FORWARD ANALYSIS REPORT")
        report.append("=" * 80)
        
        # Configuration
        report.append(f"\nConfiguration:")
        report.append(f"  Training Window: {result.config.train_window_days} days")
        report.append(f"  Testing Window: {result.config.test_window_days} days")
        report.append(f"  Step Size: {result.config.step_size_days} days")
        report.append(f"  Optimization Metric: {result.config.optimization_metric}")
        
        # Summary statistics
        report.append(f"\nSummary:")
        report.append(f"  Total Periods: {result.total_periods}")
        report.append(f"  Successful Periods: {result.successful_periods}")
        report.append(f"  Success Rate: {result.successful_periods/result.total_periods*100:.1f}%")
        
        # Performance metrics
        report.append(f"\nAggregate Performance:")
        report.append(f"  Sharpe Ratio: {result.aggregate_sharpe:.4f}")
        report.append(f"  Total Return: {result.aggregate_total_return*100:.2f}%")
        report.append(f"  Max Drawdown: {result.aggregate_max_drawdown*100:.2f}%")
        report.append(f"  Win Rate: {result.aggregate_win_rate*100:.2f}%")
        
        # Stability metrics
        report.append(f"\nStability Metrics:")
        report.append(f"  Sharpe Stability (StdDev): {result.sharpe_stability:.4f}")
        report.append(f"  Return Stability (StdDev): {result.return_stability:.4f}")
        
        # Parameter stability
        if result.parameter_stability:
            report.append(f"\nParameter Stability:")
            for param, stability in result.parameter_stability.items():
                report.append(f"  {param}: {stability:.4f}")
        
        # Period details
        if result.periods:
            report.append(f"\nPeriod Details:")
            report.append(f"{'Period':<8} {'Start':<12} {'End':<12} {'Trades':<8} {'Return':<10} {'Sharpe':<8} {'MaxDD':<8}")
            report.append("-" * 80)
            
            for i, period in enumerate(result.periods):
                report.append(f"{i+1:<8} {period.test_start.strftime('%Y-%m-%d'):<12} "
                            f"{period.test_end.strftime('%Y-%m-%d'):<12} {period.oos_trades:<8} "
                            f"{period.oos_total_return*100:>8.2f}% {period.oos_sharpe:>7.3f} "
                            f"{period.oos_max_drawdown*100:>7.2f}%")
        
        return "\n".join(report) 