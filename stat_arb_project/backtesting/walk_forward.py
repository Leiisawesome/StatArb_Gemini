"""
Professional Walk-Forward Analysis for Statistical Arbitrage
Implements rolling window parameter estimation and out-of-sample validation.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class WalkForwardAnalyzer:
    """
    Professional walk-forward analysis for statistical arbitrage strategies.
    Implements rolling window parameter estimation and out-of-sample validation.
    """
    
    def __init__(self,
                 training_window: int = 252,  # 1 year of trading days
                 testing_window: int = 63,   # 3 months of trading days
                 step_size: int = 21,        # 1 month step
                 min_training_obs: int = 100,
                 min_testing_obs: int = 20):
        """
        Initialize walk-forward analyzer.
        
        Args:
            training_window: Number of observations for training
            testing_window: Number of observations for testing
            step_size: Number of observations to step forward
            min_training_obs: Minimum observations required for training
            min_testing_obs: Minimum observations required for testing
        """
        self.training_window = training_window
        self.testing_window = testing_window
        self.step_size = step_size
        self.min_training_obs = min_training_obs
        self.min_testing_obs = min_testing_obs
        
        # Results storage
        self.window_results = []
        self.parameter_history = []
        self.performance_history = []
        
    def run_walk_forward_analysis(self,
                                 data: pd.DataFrame,
                                 strategy_factory: Callable,
                                 parameter_grid: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
        """
        Run comprehensive walk-forward analysis.
        
        Args:
            data: Price data for both assets
            strategy_factory: Function that creates strategy instances
            parameter_grid: Grid of parameters to test
            
        Returns:
            Walk-forward analysis results
        """
        logger.info(f"Starting walk-forward analysis with {len(data)} observations")
        
        # Generate walk-forward windows
        windows = self._generate_windows(len(data))
        logger.info(f"Generated {len(windows)} walk-forward windows")
        
        # Run analysis for each window
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(f"Processing window {i+1}/{len(windows)}: "
                       f"Train[{train_start}:{train_end}] Test[{test_start}:{test_end}]")
            
            # Extract data for this window
            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[test_start:test_end]
            
            if len(train_data) < self.min_training_obs or len(test_data) < self.min_testing_obs:
                logger.warning(f"Window {i+1} has insufficient data, skipping")
                continue
            
            # Run window analysis
            window_result = self._analyze_window(train_data, test_data, strategy_factory, parameter_grid)
            self.window_results.append(window_result)
            
            # Store parameter history
            if window_result['best_parameters']:
                self.parameter_history.append({
                    'window': i,
                    'train_period': (train_start, train_end),
                    'test_period': (test_start, test_end),
                    'parameters': window_result['best_parameters'],
                    'performance': window_result['test_performance']
                })
        
        # Aggregate results
        return self._aggregate_results()
    
    def _generate_windows(self, data_length: int) -> List[Tuple[int, int, int, int]]:
        """
        Generate walk-forward windows.
        
        Args:
            data_length: Total length of data
            
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        windows = []
        train_start = 0
        
        while True:
            train_end = train_start + self.training_window
            test_start = train_end
            test_end = test_start + self.testing_window
            
            # Check if we have enough data
            if test_end > data_length:
                break
            
            windows.append((train_start, train_end, test_start, test_end))
            
            # Step forward
            train_start += self.step_size
        
        return windows
    
    def _analyze_window(self,
                       train_data: pd.DataFrame,
                       test_data: pd.DataFrame,
                       strategy_factory: Callable,
                       parameter_grid: Optional[Dict[str, List]] = None) -> Dict[str, Any]:
        """
        Analyze a single walk-forward window.
        
        Args:
            train_data: Training data
            test_data: Testing data
            strategy_factory: Function to create strategy instances
            parameter_grid: Parameter grid for optimization
            
        Returns:
            Window analysis results
        """
        try:
            # Parameter optimization on training data
            if parameter_grid:
                best_parameters, train_performance = self._optimize_parameters(
                    train_data, strategy_factory, parameter_grid
                )
            else:
                # Use default parameters
                best_parameters = {}
                train_performance = self._evaluate_strategy(train_data, strategy_factory, {})
            
            # Out-of-sample testing
            test_performance = self._evaluate_strategy(test_data, strategy_factory, best_parameters)
            
            # Parameter stability analysis
            stability_metrics = self._analyze_parameter_stability(best_parameters)
            
            return {
                'train_performance': train_performance,
                'test_performance': test_performance,
                'best_parameters': best_parameters,
                'stability_metrics': stability_metrics,
                'train_data_length': len(train_data),
                'test_data_length': len(test_data)
            }
            
        except Exception as e:
            logger.error(f"Window analysis failed: {e}")
            return {
                'train_performance': {},
                'test_performance': {},
                'best_parameters': {},
                'stability_metrics': {},
                'error': str(e)
            }
    
    def _optimize_parameters(self,
                           data: pd.DataFrame,
                           strategy_factory: Callable,
                           parameter_grid: Dict[str, List]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Optimize strategy parameters using grid search.
        
        Args:
            data: Training data
            strategy_factory: Function to create strategy instances
            parameter_grid: Parameter grid for optimization
            
        Returns:
            Tuple of (best_parameters, best_performance)
        """
        best_performance = -float('inf')
        best_parameters = {}
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(parameter_grid)
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations")
        
        for params in param_combinations:
            try:
                performance = self._evaluate_strategy(data, strategy_factory, params)
                
                # Use Sharpe ratio as optimization metric
                sharpe_ratio = performance.get('sharpe_ratio', -float('inf'))
                
                if sharpe_ratio > best_performance:
                    best_performance = sharpe_ratio
                    best_parameters = params.copy()
                    
            except Exception as e:
                logger.warning(f"Parameter combination {params} failed: {e}")
                continue
        
        return best_parameters, {'sharpe_ratio': best_performance}
    
    def _generate_parameter_combinations(self, parameter_grid: Dict[str, List]) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from grid.
        
        Args:
            parameter_grid: Parameter grid
            
        Returns:
            List of parameter dictionaries
        """
        import itertools
        
        # Get parameter names and values
        param_names = list(parameter_grid.keys())
        param_values = list(parameter_grid.values())
        
        # Generate all combinations
        combinations = list(itertools.product(*param_values))
        
        # Convert to dictionaries
        param_combinations = []
        for combo in combinations:
            params = dict(zip(param_names, combo))
            param_combinations.append(params)
        
        return param_combinations
    
    def _evaluate_strategy(self,
                          data: pd.DataFrame,
                          strategy_factory: Callable,
                          parameters: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluate strategy performance on given data.
        
        Args:
            data: Price data
            strategy_factory: Function to create strategy instances
            parameters: Strategy parameters
            
        Returns:
            Performance metrics
        """
        try:
            # Create strategy instance
            strategy = strategy_factory(**parameters)
            
            # Run strategy
            equity_curve = []
            current_capital = 100000.0  # Initial capital
            
            for i in range(len(data)):
                current_data = data.iloc[:i+1]
                current_prices = data.iloc[i]
                
                # Generate signals
                signals = strategy.generate_signals(current_data)
                
                # Execute trades
                trades = strategy.execute_trades(signals, current_prices)
                
                # Update capital
                pnl = strategy.calculate_pnl(current_prices)
                current_capital += pnl
                equity_curve.append(current_capital)
            
            # Calculate performance metrics
            return self._calculate_performance_metrics(equity_curve)
            
        except Exception as e:
            logger.error(f"Strategy evaluation failed: {e}")
            return {'sharpe_ratio': -float('inf')}
    
    def _calculate_performance_metrics(self, equity_curve: List[float]) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            equity_curve: List of portfolio values
            
        Returns:
            Performance metrics dictionary
        """
        if len(equity_curve) < 2:
            return {'sharpe_ratio': -float('inf')}
        
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        
        if len(returns) == 0:
            return {'sharpe_ratio': -float('inf')}
        
        # Basic metrics
        total_return = (equity_series.iloc[-1] - equity_series.iloc[0]) / equity_series.iloc[0]
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0
        
        # Drawdown
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min()
        
        # Additional metrics
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
        avg_loss = negative_returns.mean() if len(negative_returns) > 0 else 0
        profit_factor = abs(positive_returns.sum() / negative_returns.sum()) if negative_returns.sum() != 0 else float('inf')
        
        return {
            'total_return': float(total_return),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor) if profit_factor != float('inf') else 0.0
        }
    
    def _analyze_parameter_stability(self, parameters: Dict[str, Any]) -> Dict[str, float]:
        """
        Analyze parameter stability across windows.
        
        Args:
            parameters: Current window parameters
            
        Returns:
            Stability metrics
        """
        if not self.parameter_history:
            return {'stability_score': 1.0}
        
        # Calculate parameter changes
        param_changes = []
        for hist in self.parameter_history[-5:]:  # Last 5 windows
            for param_name, param_value in parameters.items():
                if param_name in hist['parameters']:
                    change = abs(param_value - hist['parameters'][param_name])
                    param_changes.append(change)
        
        if not param_changes:
            return {'stability_score': 1.0}
        
        # Calculate stability score
        avg_change = np.mean(param_changes)
        stability_score = 1.0 / (1.0 + avg_change)
        
        return {
            'stability_score': float(stability_score),
            'avg_parameter_change': float(avg_change),
            'parameter_volatility': float(np.std(param_changes))
        }
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """
        Aggregate walk-forward analysis results.
        
        Returns:
            Comprehensive analysis results
        """
        if not self.window_results:
            return {'error': 'No valid windows analyzed'}
        
        # Extract performance metrics
        train_performances = [w['train_performance'] for w in self.window_results if 'train_performance' in w]
        test_performances = [w['test_performance'] for w in self.window_results if 'test_performance' in w]
        
        # Calculate aggregate metrics
        train_sharpe_ratios = [p.get('sharpe_ratio', 0) for p in train_performances]
        test_sharpe_ratios = [p.get('sharpe_ratio', 0) for p in test_performances]
        
        # Performance degradation analysis
        performance_degradation = []
        for train_perf, test_perf in zip(train_performances, test_performances):
            train_sharpe = train_perf.get('sharpe_ratio', 0)
            test_sharpe = test_perf.get('sharpe_ratio', 0)
            if train_sharpe > 0:
                degradation = (train_sharpe - test_sharpe) / train_sharpe
                performance_degradation.append(degradation)
        
        # Parameter stability analysis
        param_stability = self._analyze_parameter_stability_across_windows()
        
        return {
            'summary': {
                'total_windows': len(self.window_results),
                'valid_windows': len([w for w in self.window_results if 'error' not in w]),
                'avg_train_sharpe': float(np.mean(train_sharpe_ratios)),
                'avg_test_sharpe': float(np.mean(test_sharpe_ratios)),
                'avg_performance_degradation': float(np.mean(performance_degradation)) if performance_degradation else 0.0,
                'parameter_stability': param_stability
            },
            'detailed_results': self.window_results,
            'parameter_history': self.parameter_history
        }
    
    def _analyze_parameter_stability_across_windows(self) -> Dict[str, float]:
        """
        Analyze parameter stability across all windows.
        
        Returns:
            Parameter stability metrics
        """
        if len(self.parameter_history) < 2:
            return {'overall_stability': 1.0}
        
        # Extract parameter values
        param_names = set()
        for hist in self.parameter_history:
            param_names.update(hist['parameters'].keys())
        
        stability_metrics = {}
        for param_name in param_names:
            values = [hist['parameters'].get(param_name, 0) for hist in self.parameter_history]
            if len(values) > 1:
                stability_metrics[f'{param_name}_stability'] = 1.0 / (1.0 + np.std(values))
        
        overall_stability = np.mean(list(stability_metrics.values())) if stability_metrics else 1.0
        
        return {
            'overall_stability': float(overall_stability),
            **stability_metrics
        }

def run_walk_forward_analysis(data: pd.DataFrame,
                            strategy_factory: Callable,
                            parameter_grid: Optional[Dict[str, List]] = None,
                            training_window: int = 252,
                            testing_window: int = 63,
                            step_size: int = 21) -> Dict[str, Any]:
    """
    Run walk-forward analysis with default settings.
    
    Args:
        data: Price data
        strategy_factory: Function to create strategy instances
        parameter_grid: Parameter grid for optimization
        training_window: Training window size
        testing_window: Testing window size
        step_size: Step size
        
    Returns:
        Walk-forward analysis results
    """
    analyzer = WalkForwardAnalyzer(
        training_window=training_window,
        testing_window=testing_window,
        step_size=step_size
    )
    
    return analyzer.run_walk_forward_analysis(data, strategy_factory, parameter_grid) 