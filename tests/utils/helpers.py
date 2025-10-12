"""
Test helper functions for common test operations.

Provides utility functions for data generation, async operations,
logging capture, and other common test tasks.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Callable, List, Optional, Generator
from unittest.mock import AsyncMock, MagicMock


def generate_random_prices(
    n: int,
    start_price: float = 100.0,
    volatility: float = 0.02,
    trend: float = 0.0,
    seed: Optional[int] = 42
) -> np.ndarray:
    """
    Generate array of random prices with specified characteristics.
    
    Args:
        n: Number of prices to generate
        start_price: Starting price
        volatility: Daily volatility (e.g., 0.02 = 2%)
        trend: Daily trend/drift (e.g., 0.001 = 0.1%)
        seed: Random seed for reproducibility
        
    Returns:
        Array of prices
        
    Example:
        prices = generate_random_prices(100, start_price=150.0, volatility=0.03)
    """
    if seed is not None:
        np.random.seed(seed)
    
    returns = np.random.normal(trend, volatility, n)
    prices = start_price * np.exp(np.cumsum(returns))
    
    return prices


def generate_returns_series(
    n: int,
    mean: float = 0.0,
    std: float = 0.01,
    seed: Optional[int] = 42
) -> pd.Series:
    """
    Generate a pandas Series of returns.
    
    Args:
        n: Number of returns to generate
        mean: Mean return
        std: Standard deviation of returns
        seed: Random seed for reproducibility
        
    Returns:
        Series of returns with datetime index
        
    Example:
        returns = generate_returns_series(252, mean=0.0005, std=0.02)
    """
    if seed is not None:
        np.random.seed(seed)
    
    dates = pd.date_range(
        datetime.now() - timedelta(days=n),
        periods=n,
        freq='D'
    )
    
    returns = pd.Series(
        np.random.normal(mean, std, n),
        index=dates
    )
    
    return returns


def create_mock_async_context():
    """
    Create a mock object that works as an async context manager.
    
    Returns:
        Mock object with __aenter__ and __aexit__ methods
        
    Example:
        mock_connection = create_mock_async_context()
        async with mock_connection as conn:
            await conn.execute("SELECT 1")
    """
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 5.0,
    check_interval: float = 0.1,
    error_msg: str = "Condition not met within timeout"
) -> None:
    """
    Wait for a condition to become true with timeout.
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        check_interval: How often to check condition in seconds
        error_msg: Error message if timeout occurs
        
    Raises:
        TimeoutError: If condition not met within timeout
        
    Example:
        await wait_for_condition(
            lambda: order.status == 'filled',
            timeout=10.0
        )
    """
    start_time = asyncio.get_event_loop().time()
    
    while True:
        if condition():
            return
        
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(
                f"{error_msg} (waited {elapsed:.2f}s)"
            )
        
        await asyncio.sleep(check_interval)


@contextmanager
def capture_logs(
    logger_name: Optional[str] = None,
    level: int = logging.INFO
) -> Generator[List[logging.LogRecord], None, None]:
    """
    Context manager to capture log messages for testing.
    
    Args:
        logger_name: Name of logger to capture (None = root logger)
        level: Minimum log level to capture
        
    Yields:
        List of captured LogRecord objects
        
    Example:
        with capture_logs('my_module') as logs:
            my_function()
            assert len(logs) == 1
            assert 'error' in logs[0].message.lower()
    """
    logger = logging.getLogger(logger_name)
    original_level = logger.level
    original_handlers = logger.handlers.copy()
    
    # Create capturing handler
    records = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)
    
    handler = ListHandler()
    handler.setLevel(level)
    
    # Set up logger
    logger.setLevel(level)
    logger.handlers = [handler]
    
    try:
        yield records
    finally:
        # Restore original logger state
        logger.level = original_level
        logger.handlers = original_handlers


def create_correlated_returns(
    n_assets: int,
    n_periods: int,
    correlation: float = 0.5,
    mean: float = 0.0,
    std: float = 0.01,
    seed: Optional[int] = 42
) -> pd.DataFrame:
    """
    Generate correlated return series for multiple assets.
    
    Args:
        n_assets: Number of assets
        n_periods: Number of time periods
        correlation: Target correlation between assets
        mean: Mean return
        std: Standard deviation
        seed: Random seed
        
    Returns:
        DataFrame with columns for each asset
        
    Example:
        returns = create_correlated_returns(
            n_assets=5,
            n_periods=252,
            correlation=0.6
        )
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Create correlation matrix
    corr_matrix = np.full((n_assets, n_assets), correlation)
    np.fill_diagonal(corr_matrix, 1.0)
    
    # Generate correlated random returns
    # Use Cholesky decomposition
    L = np.linalg.cholesky(corr_matrix)
    uncorrelated = np.random.normal(0, 1, (n_periods, n_assets))
    correlated = uncorrelated @ L.T
    
    # Scale to desired mean and std
    returns = mean + std * correlated
    
    # Create DataFrame
    dates = pd.date_range(
        datetime.now() - timedelta(days=n_periods),
        periods=n_periods,
        freq='D'
    )
    
    df = pd.DataFrame(
        returns,
        index=dates,
        columns=[f'asset_{i}' for i in range(n_assets)]
    )
    
    return df


def assert_dataframe_equal_ignore_order(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    sort_by: Optional[str] = None
) -> None:
    """
    Assert DataFrames are equal, ignoring row order.
    
    Args:
        df1: First DataFrame
        df2: Second DataFrame
        sort_by: Column name to sort by (if None, sorts by all columns)
        
    Example:
        assert_dataframe_equal_ignore_order(
            result_df,
            expected_df,
            sort_by='timestamp'
        )
    """
    if sort_by:
        df1_sorted = df1.sort_values(sort_by).reset_index(drop=True)
        df2_sorted = df2.sort_values(sort_by).reset_index(drop=True)
    else:
        df1_sorted = df1.sort_values(by=list(df1.columns)).reset_index(drop=True)
        df2_sorted = df2.sort_values(by=list(df2.columns)).reset_index(drop=True)
    
    pd.testing.assert_frame_equal(df1_sorted, df2_sorted)


def create_price_spike(
    base_prices: np.ndarray,
    spike_index: int,
    spike_magnitude: float = 0.1
) -> np.ndarray:
    """
    Create a price spike in a price series for testing anomaly detection.
    
    Args:
        base_prices: Base price array
        spike_index: Index where spike occurs
        spike_magnitude: Magnitude of spike as fraction (0.1 = 10%)
        
    Returns:
        Modified price array with spike
        
    Example:
        prices = generate_random_prices(100)
        prices_with_spike = create_price_spike(prices, 50, 0.2)
    """
    prices = base_prices.copy()
    prices[spike_index] *= (1 + spike_magnitude)
    return prices


def generate_regime_transitions(
    n_periods: int,
    n_regimes: int = 3,
    min_duration: int = 10,
    seed: Optional[int] = 42
) -> np.ndarray:
    """
    Generate regime labels with transitions for regime testing.
    
    Args:
        n_periods: Total number of periods
        n_regimes: Number of different regimes
        min_duration: Minimum duration of each regime
        seed: Random seed
        
    Returns:
        Array of regime labels
        
    Example:
        regimes = generate_regime_transitions(252, n_regimes=3, min_duration=20)
    """
    if seed is not None:
        np.random.seed(seed)
    
    regimes = []
    current_period = 0
    
    while current_period < n_periods:
        # Random duration for this regime
        duration = min_duration + np.random.randint(0, min_duration * 2)
        duration = min(duration, n_periods - current_period)
        
        # Random regime
        regime = np.random.randint(0, n_regimes)
        
        regimes.extend([regime] * duration)
        current_period += duration
    
    return np.array(regimes[:n_periods])


def create_mock_strategy_config(
    **overrides
) -> dict:
    """
    Create a mock strategy configuration with sensible defaults.
    
    Args:
        **overrides: Any configuration values to override
        
    Returns:
        Configuration dictionary
        
    Example:
        config = create_mock_strategy_config(
            lookback_period=50,
            signal_threshold=0.7
        )
    """
    default_config = {
        'lookback_period': 20,
        'signal_threshold': 0.5,
        'position_size': 0.02,
        'stop_loss': 0.05,
        'take_profit': 0.10,
        'max_positions': 10,
        'rebalance_frequency': 'daily',
    }
    
    default_config.update(overrides)
    return default_config


def create_sample_order_book(
    mid_price: float = 100.0,
    spread: float = 0.1,
    depth: int = 5
) -> dict:
    """
    Create a sample order book for testing.
    
    Args:
        mid_price: Mid price of the book
        spread: Bid-ask spread
        depth: Number of price levels on each side
        
    Returns:
        Order book dictionary with bids and asks
        
    Example:
        book = create_sample_order_book(mid_price=150.0, spread=0.2)
    """
    half_spread = spread / 2
    best_bid = mid_price - half_spread
    best_ask = mid_price + half_spread
    
    bids = []
    for i in range(depth):
        price = best_bid - (i * 0.01)
        quantity = 100 * (depth - i)
        bids.append({'price': price, 'quantity': quantity})
    
    asks = []
    for i in range(depth):
        price = best_ask + (i * 0.01)
        quantity = 100 * (depth - i)
        asks.append({'price': price, 'quantity': quantity})
    
    return {
        'bids': bids,
        'asks': asks,
        'mid_price': mid_price,
        'spread': spread,
        'timestamp': datetime.now()
    }
