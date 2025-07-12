"""
Helper utilities for the enhanced pair backtesting system.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format a decimal value as a percentage."""
    return f"{value * 100:.{decimals}f}%"

def format_currency(value: float, currency: str = "$") -> str:
    """Format a value as currency."""
    return f"{currency}{value:,.2f}"

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio."""
    if returns.std() == 0:
        return 0.0
    return (returns.mean() * 252 - risk_free_rate) / (returns.std() * np.sqrt(252))

def calculate_max_drawdown(prices: pd.Series) -> float:
    """Calculate maximum drawdown."""
    peak = prices.expanding().max()
    drawdown = (prices - peak) / peak
    return drawdown.min()

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator 