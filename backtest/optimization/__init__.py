"""
Strategy Optimization Package

Provides complete infrastructure for systematic strategy optimization.

Components:
- StrategyOptimizer: Main optimization engine
- ParameterSearchEngine: Search algorithms (grid, Bayesian)
- PerformanceComparator: Performance comparison and ranking
"""

from .strategy_optimizer import StrategyOptimizer
from .parameter_search import ParameterSearchEngine
from .performance_comparator import PerformanceComparator

__all__ = [
    'StrategyOptimizer',
    'ParameterSearchEngine',
    'PerformanceComparator'
]

