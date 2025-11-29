"""
Core Metrics - Canonical Metric Calculations
============================================

Single source of truth for fundamental financial metrics.
All other modules should import from here to avoid duplication.

Professional Grade Pure Functions - No State, No Side Effects

Design Philosophy:
- Pure functions for maximum reusability
- NumPy-native for performance
- Consistent interface across all metrics
- No class overhead for simple calculations

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple, Optional
from scipy import stats
from enum import Enum


class VarMethod(Enum):
    """VaR calculation methods"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"


# =============================================================================
# VALUE AT RISK (VaR) - Single Source of Truth
# =============================================================================

def calculate_var(
    returns: Union[np.ndarray, pd.Series],
    confidence_level: float = 0.95,
    method: str = "historical",
    n_simulations: int = 10000
) -> float:
    """
    Calculate Value at Risk (VaR)
    
    This is the CANONICAL VaR implementation. All other VaR calculations
    should call this function.
    
    Args:
        returns: Array of returns (not prices)
        confidence_level: Confidence level (e.g., 0.95 for 95% VaR)
        method: 'historical', 'parametric', or 'monte_carlo'
        n_simulations: Number of simulations for Monte Carlo method
        
    Returns:
        VaR value (negative number representing loss)
        
    Example:
        >>> returns = np.array([-0.02, 0.01, -0.03, 0.02, -0.01])
        >>> var_95 = calculate_var(returns, 0.95)
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    alpha = 1 - confidence_level
    
    if method == "historical":
        return float(np.percentile(returns, alpha * 100))
    
    elif method == "parametric":
        # Assumes normal distribution
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        return float(stats.norm.ppf(alpha, mu, sigma))
    
    elif method == "monte_carlo":
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        np.random.seed(42)  # Reproducibility
        simulated = np.random.normal(mu, sigma, n_simulations)
        return float(np.percentile(simulated, alpha * 100))
    
    elif method == "cornish_fisher":
        # Cornish-Fisher expansion for non-normal distributions
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)
        skew = stats.skew(returns)
        kurt = stats.kurtosis(returns)
        
        z = stats.norm.ppf(alpha)
        z_cf = (z + (z**2 - 1) * skew / 6 +
                (z**3 - 3*z) * (kurt - 3) / 24 -
                (2*z**3 - 5*z) * skew**2 / 36)
        
        return float(mu + sigma * z_cf)
    
    else:
        # Default to historical
        return float(np.percentile(returns, alpha * 100))


def calculate_cvar(
    returns: Union[np.ndarray, pd.Series],
    confidence_level: float = 0.95,
    method: str = "historical"
) -> float:
    """
    Calculate Conditional Value at Risk (CVaR / Expected Shortfall)
    
    This is the CANONICAL CVaR implementation.
    
    Args:
        returns: Array of returns
        confidence_level: Confidence level
        method: VaR method to use
        
    Returns:
        CVaR value (average of losses beyond VaR)
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    var = calculate_var(returns, confidence_level, method)
    tail_losses = returns[returns <= var]
    
    if len(tail_losses) == 0:
        return var
    
    return float(np.mean(tail_losses))


# =============================================================================
# SHARPE RATIO - Single Source of Truth
# =============================================================================

def calculate_sharpe_ratio(
    returns: Union[np.ndarray, pd.Series],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Sharpe Ratio
    
    This is the CANONICAL Sharpe implementation.
    
    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods in a year (252 for daily)
        
    Returns:
        Annualized Sharpe ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    # Convert annual risk-free rate to per-period
    rf_per_period = risk_free_rate / periods_per_year
    
    excess_returns = returns - rf_per_period
    
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)
    
    if std_excess == 0 or np.isnan(std_excess):
        return 0.0
    
    # Annualize
    sharpe = (mean_excess / std_excess) * np.sqrt(periods_per_year)
    
    return float(sharpe)


def calculate_sortino_ratio(
    returns: Union[np.ndarray, pd.Series],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
    target_return: float = 0.0
) -> float:
    """
    Calculate Sortino Ratio (downside deviation-adjusted returns)
    
    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods in a year
        target_return: Minimum acceptable return (per period)
        
    Returns:
        Annualized Sortino ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    rf_per_period = risk_free_rate / periods_per_year
    excess_returns = returns - rf_per_period
    
    # Downside returns only
    downside_returns = np.minimum(returns - target_return, 0)
    downside_std = np.std(downside_returns, ddof=1)
    
    if downside_std == 0 or np.isnan(downside_std):
        return 0.0
    
    mean_excess = np.mean(excess_returns)
    sortino = (mean_excess / downside_std) * np.sqrt(periods_per_year)
    
    return float(sortino)


# =============================================================================
# DRAWDOWN METRICS - Single Source of Truth
# =============================================================================

def calculate_max_drawdown(
    returns: Union[np.ndarray, pd.Series]
) -> float:
    """
    Calculate maximum drawdown (convenience wrapper)
    
    This is the CANONICAL max drawdown implementation.
    All other modules should import this function.
    
    Args:
        returns: Array of returns (not cumulative prices)
        
    Returns:
        Maximum drawdown as a negative float (e.g., -0.25 for 25% drawdown)
    """
    _, max_dd, _ = calculate_drawdown(returns)
    return max_dd


def calculate_drawdown(
    returns: Union[np.ndarray, pd.Series]
) -> Tuple[np.ndarray, float, int]:
    """
    Calculate drawdown series, maximum drawdown, and duration
    
    This is the CANONICAL drawdown implementation.
    
    Args:
        returns: Array of returns (not cumulative)
        
    Returns:
        Tuple of (drawdown_series, max_drawdown, max_duration)
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return np.array([]), 0.0, 0
    
    # Calculate cumulative wealth
    cumulative = np.cumprod(1 + returns)
    
    # Running maximum
    running_max = np.maximum.accumulate(cumulative)
    
    # Drawdown series
    drawdown = (cumulative - running_max) / running_max
    
    # Maximum drawdown
    max_dd = float(np.min(drawdown))
    
    # Calculate duration of maximum drawdown
    max_dd_idx = np.argmin(drawdown)
    
    # Find where the drawdown started (last peak before max_dd)
    pre_dd = drawdown[:max_dd_idx + 1]
    peak_indices = np.where(pre_dd == 0)[0]
    
    if len(peak_indices) > 0:
        dd_start = peak_indices[-1]
        max_duration = max_dd_idx - dd_start
    else:
        max_duration = max_dd_idx
    
    return drawdown, max_dd, int(max_duration)


def calculate_calmar_ratio(
    returns: Union[np.ndarray, pd.Series],
    periods_per_year: int = 252
) -> float:
    """
    Calculate Calmar Ratio (annualized return / max drawdown)
    
    Args:
        returns: Array of returns
        periods_per_year: Number of periods in a year
        
    Returns:
        Calmar ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    # Annualized return
    total_return = np.prod(1 + returns) - 1
    n_periods = len(returns)
    annualized_return = (1 + total_return) ** (periods_per_year / n_periods) - 1
    
    # Max drawdown
    _, max_dd, _ = calculate_drawdown(returns)
    
    if max_dd == 0:
        return 0.0
    
    return float(annualized_return / abs(max_dd))


# =============================================================================
# VOLATILITY METRICS - Single Source of Truth
# =============================================================================

def calculate_volatility(
    returns: Union[np.ndarray, pd.Series],
    periods_per_year: int = 252
) -> float:
    """
    Calculate annualized volatility
    
    Args:
        returns: Array of returns
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized volatility
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    std = np.std(returns, ddof=1)
    return float(std * np.sqrt(periods_per_year))


def calculate_downside_volatility(
    returns: Union[np.ndarray, pd.Series],
    target_return: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    Calculate annualized downside volatility
    
    Args:
        returns: Array of returns
        target_return: Minimum acceptable return
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized downside volatility
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    downside = np.minimum(returns - target_return, 0)
    downside_std = np.std(downside, ddof=1)
    
    return float(downside_std * np.sqrt(periods_per_year))


# =============================================================================
# RETURN METRICS - Single Source of Truth
# =============================================================================

def calculate_annualized_return(
    returns: Union[np.ndarray, pd.Series],
    periods_per_year: int = 252
) -> float:
    """
    Calculate annualized return (geometric)
    
    Args:
        returns: Array of periodic returns
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized return
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    total_return = np.prod(1 + returns) - 1
    n_periods = len(returns)
    
    annualized = (1 + total_return) ** (periods_per_year / n_periods) - 1
    return float(annualized)


def calculate_total_return(
    returns: Union[np.ndarray, pd.Series]
) -> float:
    """
    Calculate total cumulative return
    
    Args:
        returns: Array of periodic returns
        
    Returns:
        Total return
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) == 0:
        return 0.0
    
    return float(np.prod(1 + returns) - 1)


# =============================================================================
# HIGHER MOMENTS - Single Source of Truth
# =============================================================================

def calculate_skewness(
    returns: Union[np.ndarray, pd.Series]
) -> float:
    """Calculate return skewness"""
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) < 3:
        return 0.0
    
    return float(stats.skew(returns))


def calculate_kurtosis(
    returns: Union[np.ndarray, pd.Series]
) -> float:
    """Calculate return kurtosis (excess kurtosis)"""
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    
    if len(returns) < 4:
        return 0.0
    
    return float(stats.kurtosis(returns))


# =============================================================================
# BENCHMARK-RELATIVE METRICS
# =============================================================================

def calculate_beta(
    returns: Union[np.ndarray, pd.Series],
    benchmark_returns: Union[np.ndarray, pd.Series]
) -> float:
    """
    Calculate portfolio beta relative to benchmark
    
    Args:
        returns: Portfolio returns
        benchmark_returns: Benchmark returns
        
    Returns:
        Beta coefficient
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    if isinstance(benchmark_returns, pd.Series):
        benchmark_returns = benchmark_returns.dropna().values
    
    min_len = min(len(returns), len(benchmark_returns))
    if min_len < 2:
        return 1.0
    
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    
    covariance = np.cov(returns, benchmark_returns)[0, 1]
    variance = np.var(benchmark_returns, ddof=1)
    
    if variance == 0:
        return 1.0
    
    return float(covariance / variance)


def calculate_alpha(
    returns: Union[np.ndarray, pd.Series],
    benchmark_returns: Union[np.ndarray, pd.Series],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Jensen's Alpha
    
    Args:
        returns: Portfolio returns
        benchmark_returns: Benchmark returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized alpha
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    if isinstance(benchmark_returns, pd.Series):
        benchmark_returns = benchmark_returns.dropna().values
    
    min_len = min(len(returns), len(benchmark_returns))
    if min_len < 2:
        return 0.0
    
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    
    rf_per_period = risk_free_rate / periods_per_year
    
    beta = calculate_beta(returns, benchmark_returns)
    
    portfolio_excess = np.mean(returns) - rf_per_period
    benchmark_excess = np.mean(benchmark_returns) - rf_per_period
    
    alpha_per_period = portfolio_excess - beta * benchmark_excess
    
    # Annualize
    return float(alpha_per_period * periods_per_year)


def calculate_information_ratio(
    returns: Union[np.ndarray, pd.Series],
    benchmark_returns: Union[np.ndarray, pd.Series],
    periods_per_year: int = 252
) -> float:
    """
    Calculate Information Ratio
    
    Args:
        returns: Portfolio returns
        benchmark_returns: Benchmark returns
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized information ratio
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    if isinstance(benchmark_returns, pd.Series):
        benchmark_returns = benchmark_returns.dropna().values
    
    min_len = min(len(returns), len(benchmark_returns))
    if min_len < 2:
        return 0.0
    
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    
    active_returns = returns - benchmark_returns
    tracking_error = np.std(active_returns, ddof=1)
    
    if tracking_error == 0:
        return 0.0
    
    mean_active = np.mean(active_returns)
    
    # Annualize
    return float((mean_active / tracking_error) * np.sqrt(periods_per_year))


def calculate_tracking_error(
    returns: Union[np.ndarray, pd.Series],
    benchmark_returns: Union[np.ndarray, pd.Series],
    periods_per_year: int = 252
) -> float:
    """
    Calculate Tracking Error
    
    Args:
        returns: Portfolio returns
        benchmark_returns: Benchmark returns
        periods_per_year: Number of periods in a year
        
    Returns:
        Annualized tracking error
    """
    if isinstance(returns, pd.Series):
        returns = returns.dropna().values
    if isinstance(benchmark_returns, pd.Series):
        benchmark_returns = benchmark_returns.dropna().values
    
    min_len = min(len(returns), len(benchmark_returns))
    if min_len < 2:
        return 0.0
    
    returns = returns[-min_len:]
    benchmark_returns = benchmark_returns[-min_len:]
    
    active_returns = returns - benchmark_returns
    tracking_error = np.std(active_returns, ddof=1)
    
    # Annualize
    return float(tracking_error * np.sqrt(periods_per_year))
