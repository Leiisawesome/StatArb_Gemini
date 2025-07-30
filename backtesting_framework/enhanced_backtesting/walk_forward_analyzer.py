#!/usr/bin/env python3
"""
Walk-Forward Analysis
Phase 3: Advanced Analytics & Optimization - Batch 4
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class WalkForwardAnalyzer:
    """Walk-forward analysis for strategy validation"""
    
    def __init__(self):
        self.walk_forward_results = {}
        self.performance_history = []
        self.parameter_evolution = {}
        
        logger.info("Initialized WalkForwardAnalyzer")
    
    def run_walk_forward_analysis(self, data: pd.DataFrame, 
                                strategy_function: Callable,
                                initial_params: Dict,
                                train_window: int = 252,
                                test_window: int = 63,
                                step_size: int = 21,
                                rebalance_frequency: str = 'monthly') -> Dict:
        """Run walk-forward analysis"""
        
        if len(data) < train_window + test_window:
            logger.warning(f"Insufficient data for walk-forward: {len(data)} < {train_window + test_window}")
            return {}
        
        try:
            # Calculate number of periods
            total_periods = len(data)
            n_periods = (total_periods - train_window - test_window) // step_size + 1
            
            logger.info(f"Starting walk-forward analysis: {n_periods} periods")
            
            # Initialize results storage
            period_results = []
            parameter_history = []
            performance_metrics = []
            
            for period in range(n_periods):
                # Calculate period boundaries
                train_start = period * step_size
                train_end = train_start + train_window
                test_start = train_end
                test_end = min(test_start + test_window, total_periods)
                
                if test_end <= test_start:
                    break
                
                # Split data
                train_data = data.iloc[train_start:train_end]
                test_data = data.iloc[test_start:test_end]
                
                # Train strategy
                trained_params = self._train_strategy(train_data, strategy_function, initial_params)
                
                # Test strategy
                test_results = self._test_strategy(test_data, strategy_function, trained_params)
                
                # Store results
                period_result = {
                    'period': period,
                    'train_start': train_start,
                    'train_end': train_end,
                    'test_start': test_start,
                    'test_end': test_end,
                    'train_data_length': len(train_data),
                    'test_data_length': len(test_data),
                    'trained_params': trained_params,
                    'test_results': test_results,
                    'period_date': datetime.now().isoformat()
                }
                
                period_results.append(period_result)
                parameter_history.append(trained_params)
                
                # Calculate performance metrics
                if test_results:
                    metrics = self._calculate_period_metrics(test_results)
                    performance_metrics.append(metrics)
                
                logger.debug(f"Completed period {period + 1}/{n_periods}")
            
            # Aggregate results
            aggregated_results = self._aggregate_walk_forward_results(period_results, performance_metrics)
            
            # Store results
            analysis_id = f"walk_forward_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.walk_forward_results[analysis_id] = aggregated_results
            
            # Store performance history
            self.performance_history.extend(performance_metrics)
            
            # Store parameter evolution
            self.parameter_evolution[analysis_id] = parameter_history
            
            logger.info(f"Walk-forward analysis completed: {n_periods} periods analyzed")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Walk-forward analysis failed: {e}")
            return {}
    
    def _train_strategy(self, train_data: pd.DataFrame, 
                       strategy_function: Callable,
                       initial_params: Dict) -> Dict:
        """Train strategy on training data"""
        
        try:
            # Simple parameter optimization (mock implementation)
            # In practice, this would use actual optimization algorithms
            
            # For now, return initial params with some noise
            trained_params = initial_params.copy()
            
            # Add some random variation to simulate optimization
            for key, value in trained_params.items():
                if isinstance(value, (int, float)):
                    variation = np.random.normal(0, 0.1 * abs(value))
                    trained_params[key] = value + variation
            
            return trained_params
            
        except Exception as e:
            logger.error(f"Strategy training failed: {e}")
            return initial_params
    
    def _test_strategy(self, test_data: pd.DataFrame,
                      strategy_function: Callable,
                      trained_params: Dict) -> Dict:
        """Test strategy on test data"""
        
        try:
            # Mock strategy testing
            # In practice, this would run the actual strategy
            
            # Generate mock returns
            n_days = len(test_data)
            daily_returns = np.random.normal(0.001, 0.02, n_days)  # 0.1% daily return, 2% volatility
            
            # Calculate cumulative returns
            cumulative_returns = np.cumprod(1 + daily_returns) - 1
            
            # Calculate metrics
            total_return = cumulative_returns[-1]
            volatility = np.std(daily_returns) * np.sqrt(252)
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
            
            # Calculate drawdown
            peak = np.maximum.accumulate(1 + cumulative_returns)
            drawdown = (1 + cumulative_returns) / peak - 1
            max_drawdown = np.min(drawdown)
            
            results = {
                'daily_returns': daily_returns.tolist(),
                'cumulative_returns': cumulative_returns.tolist(),
                'total_return': total_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'n_trades': np.random.randint(5, 20),
                'win_rate': np.random.uniform(0.4, 0.7),
                'profit_factor': np.random.uniform(1.0, 2.5)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Strategy testing failed: {e}")
            return {}
    
    def _calculate_period_metrics(self, test_results: Dict) -> Dict:
        """Calculate performance metrics for a test period"""
        
        if not test_results:
            return {}
        
        metrics = {
            'total_return': test_results.get('total_return', 0),
            'volatility': test_results.get('volatility', 0),
            'sharpe_ratio': test_results.get('sharpe_ratio', 0),
            'max_drawdown': test_results.get('max_drawdown', 0),
            'n_trades': test_results.get('n_trades', 0),
            'win_rate': test_results.get('win_rate', 0),
            'profit_factor': test_results.get('profit_factor', 0)
        }
        
        return metrics
    
    def _aggregate_walk_forward_results(self, period_results: List[Dict],
                                      performance_metrics: List[Dict]) -> Dict:
        """Aggregate walk-forward analysis results"""
        
        if not performance_metrics:
            return {}
        
        # Calculate aggregate metrics
        total_returns = [m['total_return'] for m in performance_metrics]
        volatilities = [m['volatility'] for m in performance_metrics]
        sharpe_ratios = [m['sharpe_ratio'] for m in performance_metrics]
        max_drawdowns = [m['max_drawdown'] for m in performance_metrics]
        win_rates = [m['win_rate'] for m in performance_metrics]
        profit_factors = [m['profit_factor'] for m in performance_metrics]
        
        aggregated_results = {
            'n_periods': len(period_results),
            'aggregate_metrics': {
                'mean_total_return': np.mean(total_returns),
                'std_total_return': np.std(total_returns),
                'mean_volatility': np.mean(volatilities),
                'mean_sharpe_ratio': np.mean(sharpe_ratios),
                'mean_max_drawdown': np.mean(max_drawdowns),
                'mean_win_rate': np.mean(win_rates),
                'mean_profit_factor': np.mean(profit_factors)
            },
            'stability_metrics': {
                'return_stability': np.std(total_returns) / np.mean(total_returns) if np.mean(total_returns) != 0 else np.inf,
                'sharpe_stability': np.std(sharpe_ratios) / np.mean(sharpe_ratios) if np.mean(sharpe_ratios) != 0 else np.inf,
                'drawdown_stability': np.std(max_drawdowns) / abs(np.mean(max_drawdowns)) if np.mean(max_drawdowns) != 0 else np.inf
            },
            'period_results': period_results,
            'performance_metrics': performance_metrics,
            'analysis_date': datetime.now().isoformat()
        }
        
        return aggregated_results
    
    def analyze_parameter_stability(self, analysis_id: str) -> Dict:
        """Analyze parameter stability across walk-forward periods"""
        
        if analysis_id not in self.parameter_evolution:
            logger.warning(f"Analysis ID {analysis_id} not found")
            return {}
        
        parameter_history = self.parameter_evolution[analysis_id]
        
        if not parameter_history:
            return {}
        
        # Calculate parameter stability metrics
        stability_metrics = {}
        
        # Get all parameter names
        param_names = set()
        for params in parameter_history:
            param_names.update(params.keys())
        
        for param_name in param_names:
            param_values = [params.get(param_name, 0) for params in parameter_history]
            
            if len(param_values) > 1:
                stability_metrics[param_name] = {
                    'mean': np.mean(param_values),
                    'std': np.std(param_values),
                    'coefficient_of_variation': np.std(param_values) / np.mean(param_values) if np.mean(param_values) != 0 else np.inf,
                    'min': np.min(param_values),
                    'max': np.max(param_values),
                    'range': np.max(param_values) - np.min(param_values)
                }
        
        return {
            'parameter_stability': stability_metrics,
            'n_periods': len(parameter_history),
            'analysis_id': analysis_id
        }
    
    def get_walk_forward_summary(self) -> Dict:
        """Get walk-forward analysis summary"""
        return {
            'total_analyses': len(self.walk_forward_results),
            'total_performance_records': len(self.performance_history),
            'available_analyses': list(self.walk_forward_results.keys())
        }
