"""
Enhanced Pair Backtesting System
================================

A comprehensive, isolated backtesting framework for statistical arbitrage pair trading.
Designed to be generic and work with any trading pair while maintaining complete
separation from the main stat_arb_project codebase.

Features:
- Generic pair support (any symbol1/symbol2 combination)
- Dynamic hedge ratio estimation using Kalman filters
- Regime detection using Hidden Markov Models
- ML-based trade filtering with ensemble methods
- Comprehensive performance analysis
- Professional-grade risk management
- Realistic transaction cost modeling

Author: Pro Quant Desk Trader
"""

__version__ = "1.0.0"
__author__ = "Pro Quant Desk Trader"

# Core modules
from .data import DataLoader, DataProcessor
from .models import KalmanFilter, HMM, EnsembleClassifier
from .strategies import PairTradingStrategy
from .execution import TradeExecutor, RiskManager
from .analysis import PerformanceAnalyzer, Visualizer
from .config import BacktestConfig

__all__ = [
    'DataLoader',
    'DataProcessor', 
    'KalmanFilter',
    'HMM',
    'EnsembleClassifier',
    'PairTradingStrategy',
    'TradeExecutor',
    'RiskManager',
    'PerformanceAnalyzer',
    'Visualizer',
    'BacktestConfig'
] 