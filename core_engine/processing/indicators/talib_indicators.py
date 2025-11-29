"""
TA-Lib Indicator Wrapper - Optimized Technical Analysis Functions

Provides high-performance technical indicator calculations using TA-Lib when available,
with automatic fallback to pure Python/NumPy implementations.

Performance Benefits of TA-Lib:
- 10-100x faster than pure Python implementations
- C-optimized Wilder's smoothing for RSI, ADX
- Battle-tested implementations used by thousands of quant systems
- Consistent with industry-standard calculations

Usage:
    from core_engine.processing.indicators.talib_indicators import (
        calculate_rsi, calculate_macd, calculate_bollinger_bands,
        calculate_atr, calculate_adx, TALIB_AVAILABLE
    )
    
    # Check if TA-Lib is available
    if TALIB_AVAILABLE:
        print("Using optimized TA-Lib")
    else:
        print("Using fallback implementations")
    
    # Functions work the same regardless
    rsi = calculate_rsi(close_prices, period=14)

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Optional, Union

logger = logging.getLogger(__name__)

# Try to import TA-Lib
try:
    import talib  # type: ignore[import-not-found]
    TALIB_AVAILABLE = True
    logger.info("✅ TA-Lib available - using optimized implementations")
except ImportError:
    TALIB_AVAILABLE = False
    logger.info("⚠️ TA-Lib not installed - using fallback implementations")


# =============================================================================
# RSI - Relative Strength Index
# =============================================================================

def calculate_rsi(
    close: Union[pd.Series, np.ndarray],
    period: int = 14
) -> Union[pd.Series, np.ndarray]:
    """
    Calculate Relative Strength Index (RSI)
    
    RSI measures momentum on a 0-100 scale:
    - RSI > 70: Overbought
    - RSI < 30: Oversold
    
    Args:
        close: Close prices
        period: RSI period (default 14)
        
    Returns:
        RSI values
    """
    is_series = isinstance(close, pd.Series)
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        result = talib.RSI(close_arr.astype(np.float64), timeperiod=period)
    else:
        result = _rsi_fallback(close_arr, period)
    
    if is_series:
        return pd.Series(result, index=close.index, name='rsi')
    return result


def _rsi_fallback(close: np.ndarray, period: int) -> np.ndarray:
    """Pure Python RSI implementation using Wilder's smoothing"""
    delta = np.diff(close, prepend=close[0])
    
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    
    # Wilder's smoothing (exponential moving average with alpha = 1/period)
    alpha = 1.0 / period
    
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    
    # Initialize with simple average
    avg_gain[period] = np.mean(gains[1:period+1])
    avg_loss[period] = np.mean(losses[1:period+1])
    
    # Apply Wilder's smoothing
    for i in range(period + 1, len(close)):
        avg_gain[i] = avg_gain[i-1] * (1 - alpha) + gains[i] * alpha
        avg_loss[i] = avg_loss[i-1] * (1 - alpha) + losses[i] * alpha
    
    # Calculate RS and RSI
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Set NaN for insufficient data
    rsi[:period] = np.nan
    
    return rsi


# =============================================================================
# MACD - Moving Average Convergence Divergence
# =============================================================================

def calculate_macd(
    close: Union[pd.Series, np.ndarray],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        close: Close prices
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    is_series = isinstance(close, pd.Series)
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        macd, signal, hist = talib.MACD(
            close_arr.astype(np.float64),
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )
    else:
        macd, signal, hist = _macd_fallback(close_arr, fast_period, slow_period, signal_period)
    
    if is_series:
        return (
            pd.Series(macd, index=close.index, name='macd'),
            pd.Series(signal, index=close.index, name='macd_signal'),
            pd.Series(hist, index=close.index, name='macd_histogram')
        )
    return macd, signal, hist


def _macd_fallback(
    close: np.ndarray,
    fast_period: int,
    slow_period: int,
    signal_period: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pure Python MACD implementation"""
    ema_fast = _ema(close, fast_period)
    ema_slow = _ema(close, slow_period)
    
    macd = ema_fast - ema_slow
    signal = _ema(macd, signal_period)
    histogram = macd - signal
    
    return macd, signal, histogram


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Calculate Exponential Moving Average"""
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
    
    return result


# =============================================================================
# Bollinger Bands
# =============================================================================

def calculate_bollinger_bands(
    close: Union[pd.Series, np.ndarray],
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
    """
    Calculate Bollinger Bands
    
    Args:
        close: Close prices
        period: Moving average period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    is_series = isinstance(close, pd.Series)
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        upper, middle, lower = talib.BBANDS(
            close_arr.astype(np.float64),
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev,
            matype=0  # SMA
        )
    else:
        upper, middle, lower = _bollinger_fallback(close_arr, period, std_dev)
    
    if is_series:
        return (
            pd.Series(upper, index=close.index, name='bb_upper'),
            pd.Series(middle, index=close.index, name='bb_middle'),
            pd.Series(lower, index=close.index, name='bb_lower')
        )
    return upper, middle, lower


def _bollinger_fallback(
    close: np.ndarray,
    period: int,
    std_dev: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pure Python Bollinger Bands implementation"""
    n = len(close)
    middle = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    
    for i in range(period - 1, n):
        window = close[i - period + 1:i + 1]
        mean = np.mean(window)
        std = np.std(window, ddof=0)
        
        middle[i] = mean
        upper[i] = mean + std_dev * std
        lower[i] = mean - std_dev * std
    
    return upper, middle, lower


# =============================================================================
# ATR - Average True Range
# =============================================================================

def calculate_atr(
    high: Union[pd.Series, np.ndarray],
    low: Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    period: int = 14
) -> Union[pd.Series, np.ndarray]:
    """
    Calculate Average True Range (ATR)
    
    ATR measures volatility using true range:
    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default 14)
        
    Returns:
        ATR values
    """
    is_series = isinstance(close, pd.Series)
    high_arr = high.values if isinstance(high, pd.Series) else high
    low_arr = low.values if isinstance(low, pd.Series) else low
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        result = talib.ATR(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
    else:
        result = _atr_fallback(high_arr, low_arr, close_arr, period)
    
    if is_series:
        return pd.Series(result, index=close.index, name='atr')
    return result


def _atr_fallback(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int
) -> np.ndarray:
    """Pure Python ATR implementation with Wilder's smoothing"""
    n = len(close)
    tr = np.zeros(n)
    
    # True Range
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    
    # Wilder's smoothing for ATR
    atr = np.full(n, np.nan)
    atr[period-1] = np.mean(tr[:period])
    
    alpha = 1.0 / period
    for i in range(period, n):
        atr[i] = atr[i-1] * (1 - alpha) + tr[i] * alpha
    
    return atr


# =============================================================================
# ADX - Average Directional Index
# =============================================================================

def calculate_adx(
    high: Union[pd.Series, np.ndarray],
    low: Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    period: int = 14
) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
    """
    Calculate ADX (Average Directional Index), +DI, and -DI
    
    ADX measures trend strength (0-100):
    - ADX < 20: Weak/No trend
    - ADX 20-40: Strong trend
    - ADX > 40: Very strong trend
    
    +DI > -DI: Bullish trend
    -DI > +DI: Bearish trend
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ADX period (default 14)
        
    Returns:
        Tuple of (adx, plus_di, minus_di)
    """
    is_series = isinstance(close, pd.Series)
    high_arr = high.values if isinstance(high, pd.Series) else high
    low_arr = low.values if isinstance(low, pd.Series) else low
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        adx = talib.ADX(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
        plus_di = talib.PLUS_DI(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
        minus_di = talib.MINUS_DI(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
    else:
        adx, plus_di, minus_di = _adx_fallback(high_arr, low_arr, close_arr, period)
    
    if is_series:
        return (
            pd.Series(adx, index=close.index, name='adx'),
            pd.Series(plus_di, index=close.index, name='plus_di'),
            pd.Series(minus_di, index=close.index, name='minus_di')
        )
    return adx, plus_di, minus_di


def _adx_fallback(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pure Python ADX implementation with Wilder's smoothing"""
    n = len(close)
    
    # Calculate True Range
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    
    # Calculate +DM and -DM
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    
    for i in range(1, n):
        up = high[i] - high[i-1]
        down = low[i-1] - low[i]
        
        if up > down and up > 0:
            plus_dm[i] = up
        if down > up and down > 0:
            minus_dm[i] = down
    
    # Wilder's smoothing
    alpha = 1.0 / period
    
    # Smooth TR, +DM, -DM
    atr = np.full(n, np.nan)
    plus_dm_smooth = np.full(n, np.nan)
    minus_dm_smooth = np.full(n, np.nan)
    
    atr[period-1] = np.sum(tr[:period])
    plus_dm_smooth[period-1] = np.sum(plus_dm[:period])
    minus_dm_smooth[period-1] = np.sum(minus_dm[:period])
    
    for i in range(period, n):
        atr[i] = atr[i-1] - atr[i-1] / period + tr[i]
        plus_dm_smooth[i] = plus_dm_smooth[i-1] - plus_dm_smooth[i-1] / period + plus_dm[i]
        minus_dm_smooth[i] = minus_dm_smooth[i-1] - minus_dm_smooth[i-1] / period + minus_dm[i]
    
    # Calculate +DI and -DI
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    
    mask = atr > 0
    plus_di[mask] = 100.0 * plus_dm_smooth[mask] / atr[mask]
    minus_di[mask] = 100.0 * minus_dm_smooth[mask] / atr[mask]
    
    # Calculate DX
    dx = np.full(n, np.nan)
    di_sum = plus_di + minus_di
    di_diff = np.abs(plus_di - minus_di)
    
    mask = di_sum > 0
    dx[mask] = 100.0 * di_diff[mask] / di_sum[mask]
    
    # Calculate ADX (smoothed DX)
    adx = np.full(n, np.nan)
    
    # First ADX value
    first_adx_idx = 2 * period - 2
    if first_adx_idx < n:
        adx[first_adx_idx] = np.nanmean(dx[period-1:first_adx_idx+1])
        
        for i in range(first_adx_idx + 1, n):
            if not np.isnan(adx[i-1]) and not np.isnan(dx[i]):
                adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
    
    return adx, plus_di, minus_di


# =============================================================================
# Stochastic Oscillator
# =============================================================================

def calculate_stochastic(
    high: Union[pd.Series, np.ndarray],
    low: Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    k_period: int = 14,
    d_period: int = 3,
    slowing: int = 3
) -> Tuple[Union[pd.Series, np.ndarray], Union[pd.Series, np.ndarray]]:
    """
    Calculate Stochastic Oscillator (%K and %D)
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period (default 14)
        d_period: %D smoothing period (default 3)
        slowing: Slowing period (default 3)
        
    Returns:
        Tuple of (stoch_k, stoch_d)
    """
    is_series = isinstance(close, pd.Series)
    high_arr = high.values if isinstance(high, pd.Series) else high
    low_arr = low.values if isinstance(low, pd.Series) else low
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        slowk, slowd = talib.STOCH(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            fastk_period=k_period,
            slowk_period=slowing,
            slowk_matype=0,
            slowd_period=d_period,
            slowd_matype=0
        )
    else:
        slowk, slowd = _stochastic_fallback(high_arr, low_arr, close_arr, k_period, d_period, slowing)
    
    if is_series:
        return (
            pd.Series(slowk, index=close.index, name='stoch_k'),
            pd.Series(slowd, index=close.index, name='stoch_d')
        )
    return slowk, slowd


def _stochastic_fallback(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    k_period: int,
    d_period: int,
    slowing: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Pure Python Stochastic Oscillator implementation"""
    n = len(close)
    
    # Calculate Fast %K
    fastk = np.full(n, np.nan)
    
    for i in range(k_period - 1, n):
        highest = np.max(high[i - k_period + 1:i + 1])
        lowest = np.min(low[i - k_period + 1:i + 1])
        
        if highest != lowest:
            fastk[i] = 100.0 * (close[i] - lowest) / (highest - lowest)
        else:
            fastk[i] = 50.0
    
    # Calculate Slow %K (smoothed Fast %K)
    slowk = np.full(n, np.nan)
    for i in range(k_period + slowing - 2, n):
        slowk[i] = np.nanmean(fastk[i - slowing + 1:i + 1])
    
    # Calculate Slow %D (smoothed Slow %K)
    slowd = np.full(n, np.nan)
    for i in range(k_period + slowing + d_period - 3, n):
        slowd[i] = np.nanmean(slowk[i - d_period + 1:i + 1])
    
    return slowk, slowd


# =============================================================================
# Simple and Exponential Moving Averages
# =============================================================================

def calculate_sma(
    data: Union[pd.Series, np.ndarray],
    period: int
) -> Union[pd.Series, np.ndarray]:
    """Calculate Simple Moving Average"""
    is_series = isinstance(data, pd.Series)
    data_arr = data.values if is_series else data
    
    if TALIB_AVAILABLE:
        result = talib.SMA(data_arr.astype(np.float64), timeperiod=period)
    else:
        n = len(data_arr)
        result = np.full(n, np.nan)
        for i in range(period - 1, n):
            result[i] = np.mean(data_arr[i - period + 1:i + 1])
    
    if is_series:
        return pd.Series(result, index=data.index, name=f'sma_{period}')
    return result


def calculate_ema(
    data: Union[pd.Series, np.ndarray],
    period: int
) -> Union[pd.Series, np.ndarray]:
    """Calculate Exponential Moving Average"""
    is_series = isinstance(data, pd.Series)
    data_arr = data.values if is_series else data
    
    if TALIB_AVAILABLE:
        result = talib.EMA(data_arr.astype(np.float64), timeperiod=period)
    else:
        result = _ema(data_arr, period)
    
    if is_series:
        return pd.Series(result, index=data.index, name=f'ema_{period}')
    return result


# =============================================================================
# Williams %R
# =============================================================================

def calculate_williams_r(
    high: Union[pd.Series, np.ndarray],
    low: Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    period: int = 14
) -> Union[pd.Series, np.ndarray]:
    """
    Calculate Williams %R
    
    Williams %R is a momentum indicator (-100 to 0):
    - %R > -20: Overbought
    - %R < -80: Oversold
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default 14)
        
    Returns:
        Williams %R values
    """
    is_series = isinstance(close, pd.Series)
    high_arr = high.values if isinstance(high, pd.Series) else high
    low_arr = low.values if isinstance(low, pd.Series) else low
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        result = talib.WILLR(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
    else:
        n = len(close_arr)
        result = np.full(n, np.nan)
        
        for i in range(period - 1, n):
            highest = np.max(high_arr[i - period + 1:i + 1])
            lowest = np.min(low_arr[i - period + 1:i + 1])
            
            if highest != lowest:
                result[i] = -100.0 * (highest - close_arr[i]) / (highest - lowest)
            else:
                result[i] = -50.0
    
    if is_series:
        return pd.Series(result, index=close.index, name='williams_r')
    return result


# =============================================================================
# OBV - On Balance Volume
# =============================================================================

def calculate_obv(
    close: Union[pd.Series, np.ndarray],
    volume: Union[pd.Series, np.ndarray]
) -> Union[pd.Series, np.ndarray]:
    """
    Calculate On Balance Volume (OBV)
    
    OBV is a cumulative volume indicator that adds volume on up days
    and subtracts on down days.
    
    Args:
        close: Close prices
        volume: Volume data
        
    Returns:
        OBV values
    """
    is_series = isinstance(close, pd.Series)
    close_arr = close.values if is_series else close
    volume_arr = volume.values if isinstance(volume, pd.Series) else volume
    
    if TALIB_AVAILABLE:
        result = talib.OBV(
            close_arr.astype(np.float64),
            volume_arr.astype(np.float64)
        )
    else:
        n = len(close_arr)
        result = np.zeros(n)
        result[0] = volume_arr[0]
        
        for i in range(1, n):
            if close_arr[i] > close_arr[i-1]:
                result[i] = result[i-1] + volume_arr[i]
            elif close_arr[i] < close_arr[i-1]:
                result[i] = result[i-1] - volume_arr[i]
            else:
                result[i] = result[i-1]
    
    if is_series:
        return pd.Series(result, index=close.index, name='obv')
    return result


# =============================================================================
# CCI - Commodity Channel Index
# =============================================================================

def calculate_cci(
    high: Union[pd.Series, np.ndarray],
    low: Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    period: int = 20
) -> Union[pd.Series, np.ndarray]:
    """
    Calculate Commodity Channel Index (CCI)
    
    CCI measures the current price level relative to an average price level:
    - CCI > +100: Overbought
    - CCI < -100: Oversold
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: CCI period (default 20)
        
    Returns:
        CCI values
    """
    is_series = isinstance(close, pd.Series)
    high_arr = high.values if isinstance(high, pd.Series) else high
    low_arr = low.values if isinstance(low, pd.Series) else low
    close_arr = close.values if is_series else close
    
    if TALIB_AVAILABLE:
        result = talib.CCI(
            high_arr.astype(np.float64),
            low_arr.astype(np.float64),
            close_arr.astype(np.float64),
            timeperiod=period
        )
    else:
        # Typical price
        tp = (high_arr + low_arr + close_arr) / 3.0
        
        n = len(close_arr)
        result = np.full(n, np.nan)
        
        for i in range(period - 1, n):
            window = tp[i - period + 1:i + 1]
            sma = np.mean(window)
            mad = np.mean(np.abs(window - sma))
            
            if mad > 0:
                result[i] = (tp[i] - sma) / (0.015 * mad)
            else:
                result[i] = 0.0
    
    if is_series:
        return pd.Series(result, index=close.index, name='cci')
    return result


# =============================================================================
# Module-level utility functions
# =============================================================================

def get_available_indicators() -> dict:
    """Get dictionary of available indicator functions and their descriptions"""
    return {
        'rsi': 'Relative Strength Index - momentum oscillator (0-100)',
        'macd': 'Moving Average Convergence Divergence - trend/momentum',
        'bollinger_bands': 'Bollinger Bands - volatility bands',
        'atr': 'Average True Range - volatility measure',
        'adx': 'Average Directional Index - trend strength (0-100)',
        'stochastic': 'Stochastic Oscillator - momentum (0-100)',
        'sma': 'Simple Moving Average',
        'ema': 'Exponential Moving Average',
        'williams_r': 'Williams %R - momentum (-100 to 0)',
        'obv': 'On Balance Volume - volume indicator',
        'cci': 'Commodity Channel Index - momentum/mean reversion'
    }


def check_talib_status() -> dict:
    """Check TA-Lib installation status and available functions"""
    status = {
        'installed': TALIB_AVAILABLE,
        'version': None,
        'functions_available': 0
    }
    
    if TALIB_AVAILABLE:
        status['version'] = getattr(talib, '__version__', 'unknown')
        status['functions_available'] = len(talib.get_functions())
    
    return status
