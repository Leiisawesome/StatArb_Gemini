"""
Polygon.io Data Loader for Offline Backtesting
Loads data from Polygon.io CSV files with proper schema handling.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, time, timedelta
import logging
from pathlib import Path
import glob
import os

logger = logging.getLogger(__name__)

class PolygonDataLoader:
    """
    Data loader for Polygon.io offline CSV files.
    Supports Polygon.io schema for intraday and daily data.
    """
    
    def __init__(self, data_directory: str = "data/polygon"):
        """
        Initialize Polygon data loader.
        
        Args:
            data_directory: Directory containing Polygon.io CSV files
        """
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Polygon.io schema mapping
        self.schema_mapping = {
            'timestamp': 't',  # Unix timestamp in milliseconds
            'open': 'o',       # Open price
            'high': 'h',       # High price
            'low': 'l',        # Low price
            'close': 'c',      # Close price
            'volume': 'v',     # Volume
            'vwap': 'vw',      # Volume weighted average price
            'transactions': 'n' # Number of transactions
        }
        
        # Supported intervals
        self.supported_intervals = {
            '1m': 'minute',
            '5m': 'minute',
            '15m': 'minute', 
            '30m': 'minute',
            '1h': 'hour',
            '1d': 'day'
        }
        
        logger.info(f"Initialized Polygon data loader with directory: {self.data_directory}")
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols from data directory."""
        # Check for daily aggregate format first
        daily_pattern = str(self.data_directory / "*.csv.gz")
        daily_files = glob.glob(daily_pattern)
        
        if daily_files:
            # For daily aggregates, we need to scan the files to find symbols
            # This is a simplified approach - in practice you might want to cache this
            symbols = set()
            for file in daily_files[:5]:  # Check first 5 files to find symbols
                try:
                    df = pd.read_csv(file, compression='gzip', nrows=100)
                    if 'symbol' in df.columns:
                        symbols.update(df['symbol'].unique())
                    elif 'ticker' in df.columns:
                        symbols.update(df['ticker'].unique())
                except:
                    continue
            
            if symbols:
                return list(symbols)
        
        # Fallback to symbol-based format
        pattern = str(self.data_directory / "*.csv")
        files = glob.glob(pattern)
        symbols = []
        
        for file in files:
            filename = Path(file).stem
            # Extract symbol from filename (e.g., "AAPL_1m_2023.csv" -> "AAPL")
            parts = filename.split('_')
            if len(parts) >= 2:
                symbols.append(parts[0])
        
        return list(set(symbols))
    
    def get_available_dates(self, symbol: str) -> List[str]:
        """Get available dates for a symbol."""
        pattern = str(self.data_directory / f"{symbol}_*.csv")
        files = glob.glob(pattern)
        dates = []
        
        for file in files:
            filename = Path(file).stem
            parts = filename.split('_')
            if len(parts) >= 3:
                # Extract date from filename (e.g., "AAPL_1m_2023.csv" -> "2023")
                date_part = parts[-1].replace('.csv', '')
                dates.append(date_part)
        
        return sorted(list(set(dates)))
    
    def _load_polygon_csv(self, file_path: Path) -> pd.DataFrame:
        """
        Load and parse a Polygon.io CSV file (supports .csv and .csv.gz).
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            DataFrame with standardized column names
        """
        try:
            # Read CSV with Polygon.io schema (handles gzipped files automatically)
            df = pd.read_csv(file_path, compression='gzip' if file_path.suffix == '.gz' else None)
            
            # Rename columns to standard names
            column_mapping = {v: k for k, v in self.schema_mapping.items()}
            df = df.rename(columns=column_mapping)
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
            
            # Ensure all required columns exist
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Missing required column: {col}")
                    return pd.DataFrame()
            
            # Sort by timestamp
            df.sort_index(inplace=True)
            
            logger.debug(f"Loaded {len(df)} records from {file_path}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return pd.DataFrame()
    
    def _find_data_files(self, symbol: str, start_date: str, end_date: str, interval: str = '1m') -> List[Path]:
        """
        Find relevant data files for the given parameters.
        Supports both symbol-based and daily aggregate formats.
        
        Args:
            symbol: Stock symbol (not used for daily aggregates)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval
            
        Returns:
            List of file paths
        """
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        relevant_files = []
        
        # Check for daily aggregate format first (YYYY-MM-DD.csv.gz)
        daily_pattern = str(self.data_directory / "*.csv.gz")
        daily_files = glob.glob(daily_pattern)
        
        if daily_files:
            # Daily aggregate format
            for file in daily_files:
                file_path = Path(file)
                filename = file_path.stem  # Remove .gz extension
                
                try:
                    # Extract date from filename (YYYY-MM-DD.csv)
                    file_date_str = filename
                    file_date = pd.to_datetime(file_date_str)
                    
                    if start_dt <= file_date <= end_dt:
                        relevant_files.append(file_path)
                except:
                    continue
        else:
            # Fallback to symbol-based format
            pattern = str(self.data_directory / f"{symbol}_{interval}_*.csv")
            files = glob.glob(pattern)
            
            for file in files:
                file_path = Path(file)
                filename = file_path.stem
                parts = filename.split('_')
                
                if len(parts) >= 3:
                    # Extract date from filename
                    date_part = parts[-1]
                    try:
                        file_date = pd.to_datetime(date_part, format='%Y')
                        if start_dt.year <= file_date.year <= end_dt.year:
                            relevant_files.append(file_path)
                    except:
                        # Try different date formats
                        try:
                            file_date = pd.to_datetime(date_part, format='%Y%m')
                            if start_dt <= file_date <= end_dt:
                                relevant_files.append(file_path)
                        except:
                            continue
        
        return sorted(relevant_files)
    
    def load_data(self, 
                  symbol: str, 
                  start_date: str, 
                  end_date: str, 
                  interval: str = '1m',
                  data_type: str = 'close') -> pd.DataFrame:
        """
        Load data for a single symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval
            data_type: Type of data to return ('close', 'ohlcv', 'full')
            
        Returns:
            DataFrame with requested data
        """
        logger.info(f"Loading {interval} data for {symbol} from {start_date} to {end_date}")
        
        # Find relevant files
        files = self._find_data_files(symbol, start_date, end_date, interval)
        
        if not files:
            logger.warning(f"No data files found for {symbol} {interval} {start_date} to {end_date}")
            return pd.DataFrame()
        
        # Load and combine data from all files
        all_data = []
        for file_path in files:
            df = self._load_polygon_csv(file_path)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            logger.error(f"No valid data loaded for {symbol}")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, axis=0)
        combined_data = combined_data.sort_index()
        
        # Remove duplicates
        combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
        
        # Filter to exact date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        combined_data = combined_data[(combined_data.index >= start_dt) & (combined_data.index <= end_dt)]
        
        # Return requested data type
        if data_type == 'close':
            return combined_data[['close']].rename(columns={'close': symbol})
        elif data_type == 'ohlcv':
            return combined_data[['open', 'high', 'low', 'close', 'volume']]
        elif data_type == 'full':
            return combined_data
        else:
            logger.warning(f"Unknown data_type: {data_type}, returning close prices")
            return combined_data[['close']].rename(columns={'close': symbol})
    
    def load_multiple_symbols(self, 
                             symbols: List[str], 
                             start_date: str, 
                             end_date: str, 
                             interval: str = '1m',
                             data_type: str = 'close') -> pd.DataFrame:
        """
        Load data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval
            data_type: Type of data to return
            
        Returns:
            DataFrame with data for all symbols
        """
        logger.info(f"Loading data for {len(symbols)} symbols: {symbols}")
        
        all_data = {}
        for symbol in symbols:
            symbol_data = self.load_data(symbol, start_date, end_date, interval, data_type)
            if not symbol_data.empty:
                if data_type == 'close':
                    all_data[symbol] = symbol_data[symbol]
                else:
                    all_data[symbol] = symbol_data
        
        if not all_data:
            logger.error("No data loaded for any symbol")
            return pd.DataFrame()
        
        # Combine all symbols
        if data_type == 'close':
            combined_df = pd.DataFrame(all_data)
        else:
            # For OHLCV data, we need to handle this differently
            # For now, return close prices
            close_data = {}
            for symbol, data in all_data.items():
                if 'close' in data.columns:
                    close_data[symbol] = data['close']
            combined_df = pd.DataFrame(close_data)
        
        # Align timestamps
        combined_df = combined_df.dropna()
        
        logger.info(f"Successfully loaded data for {len(combined_df.columns)} symbols")
        logger.info(f"Data range: {combined_df.index[0]} to {combined_df.index[-1]}")
        logger.info(f"Total observations: {len(combined_df)}")
        
        return combined_df
    
    def validate_data_quality(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """Validate data quality for Polygon.io data."""
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
        price_columns = [col for col in data.columns if col in ['open', 'high', 'low', 'close']]
        if price_columns:
            zero_prices = (data[price_columns] <= 0).any(axis=1).sum()
            if zero_prices > 0:
                return False, f"Contains {zero_prices} rows with zero/negative prices"
        
        # Check for extreme outliers (>10x price changes)
        if 'close' in data.columns:
            returns = data['close'].pct_change().abs()
            extreme_returns = (returns > 1.0).sum()
            if extreme_returns > len(data) * 0.01:  # More than 1% extreme returns
                return False, f"Contains {extreme_returns} extreme price movements"
        
        return True, "Data quality validation passed"
    
    def get_data_info(self, symbol: str) -> Dict[str, Any]:
        """Get information about available data for a symbol."""
        files = glob.glob(str(self.data_directory / f"{symbol}_*.csv"))
        
        info = {
            'symbol': symbol,
            'available_files': len(files),
            'intervals': [],
            'date_range': {'start': None, 'end': None},
            'total_records': 0
        }
        
        all_dates = []
        for file in files:
            file_path = Path(file)
            filename = file_path.stem
            parts = filename.split('_')
            
            if len(parts) >= 3:
                interval = parts[1]
                if interval not in info['intervals']:
                    info['intervals'].append(interval)
                
                # Get date from filename
                date_part = parts[-1]
                try:
                    file_date = pd.to_datetime(date_part, format='%Y')
                    all_dates.append(file_date)
                except:
                    continue
        
        if all_dates:
            info['date_range']['start'] = min(all_dates)
            info['date_range']['end'] = max(all_dates)
        
        return info

# Backward compatibility functions
def load_intraday_data(tickers: List[str], duration_days: int, interval: str, 
                      validate_quality: bool = True) -> pd.DataFrame:
    """
    Load intraday data using Polygon.io files (replaces yfinance function).
    
    Args:
        tickers: List of ticker symbols
        duration_days: Number of days to load
        interval: Data interval
        validate_quality: Whether to validate data quality
        
    Returns:
        DataFrame with price data
    """
    # Calculate date range
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=duration_days)).strftime('%Y-%m-%d')
    
    # Initialize loader
    loader = PolygonDataLoader()
    
    # Load data
    data = loader.load_multiple_symbols(tickers, start_date, end_date, interval, 'close')
    
    # Validate quality if requested
    if validate_quality and not data.empty:
        is_valid, message = loader.validate_data_quality(data)
        if not is_valid:
            logger.warning(f"Data quality issues: {message}")
    
    return data

def load_intraday_data_with_retry(tickers: List[str], duration_days: int, interval: str, 
                                 max_retries: int = 3, retry_delay: float = 1.0) -> pd.DataFrame:
    """
    Load intraday data with retry logic (replaces yfinance function).
    """
    for attempt in range(max_retries):
        try:
            data = load_intraday_data(tickers, duration_days, interval)
            if not data.empty:
                return data
            
            if attempt < max_retries - 1:
                logger.info(f"Retry {attempt + 1}/{max_retries} in {retry_delay} seconds...")
                import time as time_module
                time_module.sleep(retry_delay)
                retry_delay *= 2
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time as time_module
                time_module.sleep(retry_delay)
                retry_delay *= 2
    
    return pd.DataFrame() 