"""
JIT Utilities for Core Engine
=============================

Provides centralized JIT (Just-In-Time) compilation utilities using Numba.
Includes safe decorators that fall back to standard Python if Numba is not available.

Usage:
    from core_engine.utils.jit_utils import njit_conditional

    @njit_conditional
    def my_heavy_function(data):
        # ... numerical loops ...
        pass

Author: StatArb_Gemini Core Engine
"""

import logging
import functools
import numpy as np

logger = logging.getLogger(__name__)

# Try to import Numba
try:
    import numba  # type: ignore
    from numba import njit, prange  # type: ignore
    NUMBA_AVAILABLE = True
    # Import-time log is intentionally debug-only to avoid noisy runs.
    logger.debug("Numba available - JIT optimization enabled")
except ImportError:
    NUMBA_AVAILABLE = False
    # Import-time log is intentionally debug-only to avoid noisy runs.
    logger.debug("Numba not installed - JIT optimization disabled (falling back to pure Python)")

def njit_conditional(func=None, **kwargs):
    """
    Decorator that applies numba.njit if available, otherwise returns the original function.
    """
    if func is None:
        return lambda f: njit_conditional(f, **kwargs)

    if NUMBA_AVAILABLE:
        return njit(**kwargs)(func)
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs_inner):
            return func(*args, **kwargs_inner)
        return wrapper

def is_numba_available() -> bool:
    """Check if Numba is available in the current environment."""
    return NUMBA_AVAILABLE

@njit_conditional
def jit_rolling_rank(data: np.ndarray, window: int) -> np.ndarray:
    """
    JIT-optimized rolling rank (percentile).
    Matches pd.Series(x).rank(pct=True, method='average').iloc[-1]
    """
    n = len(data)
    result = np.empty(n)
    result[:] = np.nan
    
    if n < window:
        return result
        
    for i in range(window - 1, n):
        # Extract window manually to avoid slicing overhead if possible
        # but slicing is usually fine in Numba
        window_data = data[i - window + 1 : i + 1]
        last_val = data[i]
        
        smaller = 0
        equal = 0
        for j in range(window):
            val = window_data[j]
            if val < last_val:
                smaller += 1
            elif val == last_val:
                equal += 1
        
        result[i] = (smaller + (equal + 1) / 2.0) / window
        
    return result

@njit_conditional
def jit_rolling_mad_zscore(data: np.ndarray, window: int, min_periods: int = 20) -> np.ndarray:
    """
    JIT-optimized rolling MAD (Median Absolute Deviation) Z-score.
    """
    n = len(data)
    result = np.empty(n)
    result[:] = np.nan
    
    for i in range(min_periods - 1, n):
        start = max(0, i - window + 1)
        window_data = data[start : i + 1]
        
        if len(window_data) < min_periods:
            continue
            
        # Numba supports np.median
        median_val = np.median(window_data)
        
        # Calculate MAD
        abs_diff = np.abs(window_data - median_val)
        mad_val = np.median(abs_diff)
        
        last_val = data[i]
        
        if mad_val < 1e-8:
            # Fallback to standard Z-score
            sum_val = 0.0
            for j in range(len(window_data)):
                sum_val += window_data[j]
            mean_val = sum_val / len(window_data)
            
            sq_diff_sum = 0.0
            for j in range(len(window_data)):
                sq_diff_sum += (window_data[j] - mean_val)**2
            std_val = np.sqrt(sq_diff_sum / len(window_data))
            
            if std_val < 1e-8:
                result[i] = 0.0
            else:
                result[i] = (last_val - mean_val) / std_val
        else:
            # MAD-based Z-score (1.4826 is scaling factor for normal distribution)
            result[i] = (last_val - median_val) / (1.4826 * mad_val)
            
    return result

@njit_conditional
def jit_calculate_correlation_spike(original_values: np.ndarray, stress_factor: float) -> np.ndarray:
    """
    JIT-optimized correlation spike calculation for stress testing.
    Moves correlations towards 1 or -1 based on their sign.
    """
    n = original_values.shape[0]
    stressed_values = original_values.copy()
    
    for i in range(n):
        for j in range(n):
            if i != j:
                current_corr = original_values[i, j]
                if current_corr >= 0:
                    stressed_values[i, j] = current_corr + (1.0 - current_corr) * stress_factor
                else:
                    stressed_values[i, j] = current_corr + (-1.0 - current_corr) * stress_factor
                    
    return stressed_values

@njit_conditional
def jit_calculate_ewma_weights(n: int, lambda_factor: float) -> np.ndarray:
    """
    JIT-optimized EWMA weights calculation.
    """
    weights = np.empty(n)
    for i in range(n):
        weights[i] = lambda_factor ** i
    
    # Reverse to give more weight to recent observations
    weights = weights[::-1]
    
    # Normalize
    total = np.sum(weights)
    if total > 0:
        weights = weights / total
        
    return weights

@njit_conditional
def jit_calculate_cvar(returns: np.ndarray, var_value: float) -> float:
    """
    JIT-optimized Conditional Value at Risk (Expected Shortfall) calculation.
    """
    count = 0
    total = 0.0
    
    # var_value is usually positive (representing a loss)
    # returns are usually negative for losses
    threshold = -var_value
    
    for i in range(len(returns)):
        if returns[i] <= threshold:
            total += returns[i]
            count += 1
            
    if count > 0:
        return -total / count
    else:
        return var_value

@njit_conditional
def jit_calculate_spread_proxy(high: float, low: float, close: float) -> float:
    """JIT-optimized spread proxy calculation."""
    if close <= 0:
        return 10.0
    
    spread_bps = (high - low) / close * 10000.0
    
    # Manual clip for Numba compatibility
    if spread_bps < 0.5:
        return 0.5
    if spread_bps > 500.0:
        return 500.0
    return spread_bps

@njit_conditional
def jit_calculate_spread_history(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
    """JIT-optimized historical spread calculation."""
    n = len(highs)
    result = np.empty(n)
    for i in range(n):
        result[i] = jit_calculate_spread_proxy(highs[i], lows[i], closes[i])
    return result

@njit_conditional
def jit_calculate_overall_score(volume_ratio: float, spread_bps: float, volatility: float) -> float:
    """JIT-optimized overall liquidity score calculation."""
    # Volume score (0-100)
    if volume_ratio >= 2.0:
        volume_score = 100.0
    elif volume_ratio >= 1.0:
        volume_score = 50.0 + 50.0 * (volume_ratio - 1.0)
    elif volume_ratio >= 0.5:
        volume_score = 25.0 + 50.0 * (volume_ratio - 0.5)
    else:
        volume_score = 50.0 * volume_ratio

    # Spread score (0-100)
    if spread_bps <= 5.0:
        spread_score = 100.0
    elif spread_bps <= 20.0:
        spread_score = 100.0 - (spread_bps - 5.0) * 2.0
    elif spread_bps <= 50.0:
        spread_score = 70.0 - (spread_bps - 20.0) * 1.0
    else:
        val = 40.0 - (spread_bps - 50.0) * 0.5
        spread_score = val if val > 0.0 else 0.0

    # Volatility score (0-100)
    vol_pct = volatility * 100.0
    if vol_pct <= 1.0:
        vol_score = 100.0
    elif vol_pct <= 3.0:
        vol_score = 100.0 - (vol_pct - 1.0) * 15.0
    else:
        val = 70.0 - (vol_pct - 3.0) * 10.0
        vol_score = val if val > 0.0 else 0.0

    # Weighted combination
    overall = (
        volume_score * 0.40 +
        spread_score * 0.40 +
        vol_score * 0.20
    )

    if overall < 0.0:
        return 0.0
    if overall > 100.0:
        return 100.0
    return overall

@njit_conditional
def jit_find_timestamp_indices(timestamps: np.ndarray, target: int) -> tuple:
    """
    JIT-optimized binary search to find start and end indices for a target timestamp 
    in a sorted array. Returns (-1, -1) if not found.
    
    Args:
        timestamps: Sorted array of timestamps (as int64/datetime64)
        target: Target timestamp to find
        
    Returns:
        tuple: (start_idx, end_idx) where end_idx is exclusive
    """
    n = len(timestamps)
    if n == 0:
        return (-1, -1)
        
    # Binary search for the first occurrence
    start = np.searchsorted(timestamps, target, side='left')
    
    if start >= n or timestamps[start] != target:
        return (-1, -1)
    
    # Binary search for the last occurrence
    end = np.searchsorted(timestamps, target, side='right')
    
    return (start, end)

@njit_conditional
def jit_merge_sorted_timestamps(timestamp_arrays: list) -> np.ndarray:
    """
    JIT-optimized merging of multiple sorted timestamp arrays into a single 
    unique sorted array.
    """
    # Numba doesn't handle list of arrays well in all versions, 
    # but we can use a simple approach if we know the structure.
    # For now, we'll use a simpler version or just rely on numpy.
    pass

@njit_conditional
def jit_calculate_percentile(value: float, history: np.ndarray) -> float:
    """JIT-optimized percentile calculation."""
    if len(history) == 0:
        return 50.0
    
    count = 0
    for i in range(len(history)):
        if history[i] <= value:
            count += 1
            
    return (count / len(history)) * 100.0

@njit_conditional
def jit_detect_price_spike(current_price: float, recent_prices: np.ndarray, threshold: float) -> bool:
    """JIT-optimized price spike detection."""
    if len(recent_prices) < 3:
        return False
    
    avg_price = np.mean(recent_prices)
    if avg_price > 0:
        price_change_pct = abs(current_price - avg_price) / avg_price * 100.0
        return price_change_pct > threshold
    return False

@njit_conditional
def jit_detect_volume_spike(current_volume: float, recent_volumes: np.ndarray, threshold: float) -> bool:
    """JIT-optimized volume spike detection."""
    if len(recent_volumes) < 5:
        return False
    
    avg_volume = np.mean(recent_volumes)
    if avg_volume > 0:
        volume_factor = current_volume / avg_volume
        return volume_factor > threshold
    return False

@njit_conditional
def jit_detect_outlier(value: float, history: np.ndarray, threshold_std: float) -> bool:
    """JIT-optimized statistical outlier detection."""
    if len(history) < 10:
        return False
    
    mean_val = np.mean(history)
    std_val = np.std(history)
    
    if std_val > 0:
        z_score = abs(value - mean_val) / std_val
        return z_score > threshold_std
    return False


@njit_conditional
def jit_ewma_volatility(returns: np.ndarray, lambda_: float) -> float:
    """
    JIT-optimized EWMA volatility forecast.
    """
    if returns.size < 2:
        return 0.0

    # Seed with recent variance (last 20 points or all if less)
    seed_size = min(20, returns.size)
    seed_data = returns[-seed_size:]
    
    # Manual variance calculation for seed
    mean = 0.0
    for i in range(seed_size):
        mean += seed_data[i]
    mean /= seed_size
    
    var = 0.0
    for i in range(seed_size):
        var += (seed_data[i] - mean) ** 2
    var /= seed_size

    for i in range(returns.size):
        var = lambda_ * var + (1.0 - lambda_) * (returns[i] ** 2)
    
    return np.sqrt(max(var, 0.0))


@njit_conditional
def jit_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """
    JIT-optimized Pearson correlation.
    """
    if x.size < 5:
        return 0.0
    
    n = x.size
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0
    sum_y2 = 0.0
    
    for i in range(n):
        sum_x += x[i]
        sum_y += y[i]
        sum_xy += x[i] * y[i]
        sum_x2 += x[i] * x[i]
        sum_y2 += y[i] * y[i]
        
    numerator = n * sum_xy - sum_x * sum_y
    denominator = np.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator
