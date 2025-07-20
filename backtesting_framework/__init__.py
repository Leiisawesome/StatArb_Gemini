"""
StatArb Backtesting Framework

Professional backtesting framework for quantitative trading strategies.
"""

__version__ = "1.0.0"
__author__ = "StatArb_Gemini Team"

from .experiments.experiment_runner import ExperimentRunner, ExperimentConfig, ExperimentResult
from .experiments.parameter_sweep import ParameterSweep, OptimizationConfig, OptimizationResult
from .strategies.base_strategy import BaseStrategy, StrategyConfig, TradingSignal, SignalType

__all__ = [
    'ExperimentRunner',
    'ExperimentConfig', 
    'ExperimentResult',
    'ParameterSweep',
    'OptimizationConfig',
    'OptimizationResult',
    'BaseStrategy',
    'StrategyConfig',
    'TradingSignal',
    'SignalType'
] 