"""
Handles loading and preprocessing of price data, now optimized for intraday.
"""
import pandas as pd
import yfinance as yf
from typing import List, Optional
import numpy as np
from datetime import datetime, time
import time as time_module
import logging

logger = logging.getLogger(__name__)

def validate_ticker_symbols(tickers: List[str]) -> List[str]:
    """Validates ticker symbols and returns valid ones."""
    valid_tickers = []
    for ticker in tickers:
        try:
            # Quick validation by attempting to get basic info
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            if info and 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                valid_tickers.append(ticker)
            else:
                logger.warning(f"Ticker {ticker} appears to be invalid or delisted")
        except Exception as e:
            logger.warning(f"Could not validate {ticker}: {e}")
    return valid_tickers

def detect_outliers(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Detects outliers using z-score method."""
    z_scores = np.abs((series - series.mean()) / series.std())
    return z_scores > threshold

def filter_market_hours_safe(data: pd.DataFrame) -> pd.DataFrame:
    """Safely filters data to include only regular market hours (9:30 AM - 4:00 PM ET)."""
    try:
        market_start = time(9, 30)
        market_end = time(16, 0)
        
        # Handle timezone conversion safely
        data_et = data.copy()
        
        # Check if index has timezone info
        if hasattr(data_et.index, 'tz') and data_et.index.tz is not None:
            # Already timezone-aware, convert to Eastern
            data_et.index = data_et.index.tz_convert('US/Eastern')
        else:
            # Timezone-naive, assume UTC and convert
            data_et.index = pd.to_datetime(data_et.index).tz_localize('UTC').tz_convert('US/Eastern')
        
        # Filter by time
        market_mask = (data_et.index.time >= market_start) & (data_et.index.time <= market_end)
        filtered_data = data[market_mask]
        
        logger.info(f"Filtered to market hours: {len(filtered_data)}/{len(data)} bars retained")
        return filtered_data
        
    except Exception as e:
        logger.warning(f"Market hours filtering failed: {e}. Using original data.")
        return data

def validate_data_quality(data: pd.DataFrame) -> tuple[bool, str]:
    """Comprehensive data quality validation."""
    if data.empty:
        return False, "Data is empty"
    
    # Check for sufficient data points
    if len(data) < 100:
        return False, f"Insufficient data points: {len(data)}"
    
    # Check for null values
    null_count = data.isnull().sum().sum()
    if null_count > 0:
        return False, f"Contains {null_count} null values"
    
    # Check for zero or negative prices
    zero_prices = (data <= 0).any(axis=1).sum()
    if zero_prices > 0:
        return False, f"Contains {zero_prices} rows with zero/negative prices"
    
    # Check for extreme outliers (>10x price changes)
    returns = data.pct_change().abs()
    extreme_returns = (returns > 1.0).any(axis=1).sum()
    if extreme_returns > len(data) * 0.01:  # More than 1% extreme returns
        return False, f"Contains {extreme_returns} extreme price movements"
    
    # Check data freshness (should be within last 24 hours for intraday)
    try:
        latest_timestamp = pd.to_datetime(data.index.max())
        current_time = pd.Timestamp.now()
        if latest_timestamp < current_time - pd.Timedelta(days=1):
            return False, "Data appears to be stale"
    except Exception:
        logger.warning("Could not check data freshness")
    
    return True, "Data quality validation passed"

def load_intraday_data_with_retry(tickers: List[str], duration_days: int, interval: str, 
                                 max_retries: int = 3, retry_delay: float = 1.0) -> pd.DataFrame:
    """
    Loads data with retry logic for production robustness.
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Loading {interval} intraday data for tickers: {tickers} over the last {duration_days} days (attempt {attempt + 1}/{max_retries})")
            
            # Validate ticker symbols first
            valid_tickers = validate_ticker_symbols(tickers)
            if not valid_tickers:
                logger.error("No valid ticker symbols found.")
                return pd.DataFrame()
            
            if len(valid_tickers) != len(tickers):
                logger.warning(f"Only {len(valid_tickers)}/{len(tickers)} tickers are valid: {valid_tickers}")
            
            period = f"{duration_days}d"
            data = yf.download(valid_tickers, period=period, interval=interval, 
                              progress=False, auto_adjust=True)['Close']
            
            if data.empty:
                logger.error("No data downloaded from yfinance.")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time_module.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                return pd.DataFrame()

            if len(valid_tickers) == 1:
                data = data.to_frame(name=valid_tickers[0])
            
            # Remove columns with all NaN values
            data.dropna(axis=1, how='all', inplace=True)
            if data.shape[1] < 2 and len(valid_tickers) > 1:
                logger.error("Not enough valid data for at least two tickers. Cannot form a pair.")
                return pd.DataFrame()
            
            # Enhanced data cleaning
            logger.info("Cleaning and validating data...")
            
            # Forward fill then backward fill (proper method)
            data = data.ffill().bfill()
            
            # Remove any remaining NaN values
            data.dropna(inplace=True)
            
            # Filter to market hours only
            data = filter_market_hours_safe(data)
            
            # Detect and handle outliers
            outlier_mask = pd.DataFrame(False, index=data.index, columns=data.columns)
            for col in data.columns:
                outlier_mask[col] = detect_outliers(data[col])
            
            outlier_count = outlier_mask.any(axis=1).sum()
            if outlier_count > 0:
                logger.warning(f"Detected {outlier_count} outlier bars. Interpolating...")
                # Replace outliers with interpolated values
                for col in data.columns:
                    outlier_indices = outlier_mask[col]
                    if outlier_indices.any():
                        data.loc[outlier_indices, col] = np.nan
                        data[col] = data[col].interpolate(method='time')
            
            # Final quality validation
            is_valid, message = validate_data_quality(data)
            if not is_valid:
                logger.error(f"Data quality validation failed: {message}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time_module.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return pd.DataFrame()
            
            logger.info(f"✓ {message}")
            logger.info(f"Successfully loaded {data.shape[0]} bars of data.")
            logger.info(f"Data range: {data.index[0]} to {data.index[-1]}")
            
            return data

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time_module.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("All retry attempts failed.")
                return pd.DataFrame()
    
    return pd.DataFrame()

def load_intraday_data(tickers: List[str], duration_days: int, interval: str, 
                      validate_quality: bool = True) -> pd.DataFrame:
    """
    Loads historical intraday price data from Yahoo Finance with enhanced quality checks.
    """
    return load_intraday_data_with_retry(tickers, duration_days, interval) 