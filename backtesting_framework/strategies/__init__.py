"""
Trading Strategies Module

Contains all trading strategy implementations.
"""

from .base_strategy import BaseStrategy, StrategyConfig, TradingSignal, SignalType, Position
from .pairs_trading import PairsTradingStrategy, PairsTradingConfig
from .momentum_strategy import MomentumStrategy, MomentumConfig
from .multi_factor_ensemble_strategy import MultiFactorEnsembleStrategy, MultiFactorConfig, FactorConfig, FactorType

__all__ = [
    'BaseStrategy',
    'StrategyConfig',
    'TradingSignal',
    'SignalType',
    'Position',
    'PairsTradingStrategy',
    'PairsTradingConfig',
    'MomentumStrategy',
    'MomentumConfig',
    'MultiFactorEnsembleStrategy',
    'MultiFactorConfig',
    'FactorConfig',
    'FactorType'
] 