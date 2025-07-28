from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkConfig:
    """SPY benchmark configuration"""
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02  # 2% annual risk-free rate
    benchmark_weight: float = 0.0  # 0% benchmark weight (long-short strategy)
    
    # Performance metrics
    target_information_ratio: float = 1.0
    target_sharpe_ratio: float = 1.5
    max_tracking_error: float = 0.15  # 15% max tracking error
    max_beta: float = 0.3  # 30% max beta to market

class BenchmarkAnalyzer:
    """SPY benchmark analysis and optimization"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
    
    def calculate_benchmark_metrics(self, strategy_returns: pd.Series, 
                                  spy_returns: pd.Series) -> Dict[str, float]:
        """Calculate benchmark-relative performance metrics"""
        
        # Excess returns
        excess_returns = strategy_returns - spy_returns
        
        # Risk metrics
        strategy_vol = strategy_returns.std() * np.sqrt(252)
        spy_vol = spy_returns.std() * np.sqrt(252)
        tracking_error = excess_returns.std() * np.sqrt(252)
        
        # Beta calculation
        beta = np.cov(strategy_returns, spy_returns)[0, 1] / np.var(spy_returns)
        
        # Performance metrics
        information_ratio = excess_returns.mean() / tracking_error if tracking_error > 0 else 0
        sharpe_ratio = strategy_returns.mean() / strategy_vol if strategy_vol > 0 else 0
        spy_sharpe = spy_returns.mean() / spy_vol if spy_vol > 0 else 0
        
        # Drawdown analysis
        strategy_cumulative = (1 + strategy_returns).cumprod()
        spy_cumulative = (1 + spy_returns).cumprod()
        
        strategy_drawdown = (strategy_cumulative / strategy_cumulative.expanding().max() - 1)
        spy_drawdown = (spy_cumulative / spy_cumulative.expanding().max() - 1)
        
        max_strategy_drawdown = strategy_drawdown.min()
        max_spy_drawdown = spy_drawdown.min()
        
        return {
            'information_ratio': information_ratio,
            'sharpe_ratio': sharpe_ratio,
            'spy_sharpe_ratio': spy_sharpe,
            'tracking_error': tracking_error,
            'beta': beta,
            'excess_return': excess_returns.mean() * 252,
            'strategy_volatility': strategy_vol,
            'spy_volatility': spy_vol,
            'max_strategy_drawdown': max_strategy_drawdown,
            'max_spy_drawdown': max_spy_drawdown,
            'relative_drawdown': max_strategy_drawdown - max_spy_drawdown
        }
    
    def optimize_for_benchmark(self, strategy_returns: pd.Series, 
                             spy_returns: pd.Series) -> Dict[str, float]:
        """Optimize strategy parameters for SPY benchmark performance"""
        
        # Calculate current metrics
        current_metrics = self.calculate_benchmark_metrics(strategy_returns, spy_returns)
        
        # Optimization objectives
        objectives = {
            'maximize_information_ratio': -current_metrics['information_ratio'],
            'minimize_tracking_error': current_metrics['tracking_error'],
            'minimize_beta': current_metrics['beta'],
            'minimize_relative_drawdown': current_metrics['relative_drawdown']
        }
        
        # Check if objectives are met
        constraints_met = {
            'information_ratio_target': current_metrics['information_ratio'] >= self.config.target_information_ratio,
            'tracking_error_limit': current_metrics['tracking_error'] <= self.config.max_tracking_error,
            'beta_limit': current_metrics['beta'] <= self.config.max_beta
        }
        
        return {
            'current_metrics': current_metrics,
            'objectives': objectives,
            'constraints_met': constraints_met,
            'optimization_score': self._calculate_optimization_score(current_metrics)
        }
    
    def _calculate_optimization_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall optimization score"""
        
        # Weighted score based on key metrics
        information_ratio_score = min(metrics['information_ratio'] / self.config.target_information_ratio, 1.0)
        tracking_error_score = max(0, 1 - metrics['tracking_error'] / self.config.max_tracking_error)
        beta_score = max(0, 1 - metrics['beta'] / self.config.max_beta)
        drawdown_score = max(0, 1 + metrics['relative_drawdown'])  # Prefer lower relative drawdown
        
        # Combined score
        total_score = (
            information_ratio_score * 0.4 +
            tracking_error_score * 0.3 +
            beta_score * 0.2 +
            drawdown_score * 0.1
        )
        
        return total_score

class SimplePerformanceAttribution:
    """Minimal performance attribution for academic factors"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def attribute_performance(self, signals: Dict[str, float], 
                            returns: pd.Series) -> Dict[str, float]:
        """Simple correlation-based attribution - only if enabled"""
        if not self.enabled:
            return {}
        
        attribution = {}
        
        try:
            for signal_name, signal_values in signals.items():
                if isinstance(signal_values, (list, pd.Series)) and len(signal_values) == len(returns):
                    # Calculate correlation with returns
                    correlation = np.corrcoef(signal_values, returns)[0, 1]
                    if not np.isnan(correlation):
                        attribution[f'{signal_name}_contribution'] = abs(correlation)
                        
        except Exception as e:
            logger.warning(f"Performance attribution failed: {e}")
            return {}
        
        return attribution 