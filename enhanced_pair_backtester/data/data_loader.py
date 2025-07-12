"""
Generic data loader for the enhanced pair backtesting system.
Supports multiple data sources and can handle any trading pair.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import clickhouse_connect
from datetime import datetime, timedelta
import logging
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Generic data loader that can handle any trading pair from multiple sources.
    Designed to be completely isolated from the main stat_arb_project codebase.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data loader.
        
        Args:
            config: Configuration dictionary containing data source settings
        """
        self.config = config
        self.data_source = config.get('data_source', 'clickhouse')
        self.database_config = config.get('database_config', {})
        self.data_frequency = config.get('data_frequency', '5min')
        
        # Initialize connections
        self.client = None
        if self.data_source == 'clickhouse':
            self._connect_clickhouse()
    
    def _connect_clickhouse(self):
        """Connect to ClickHouse database."""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.database_config.get('host', 'localhost'),
                port=self.database_config.get('port', 8123),
                user=self.database_config.get('user', 'default'),
                password=self.database_config.get('password', ''),
            )
            logger.info("Connected to ClickHouse successfully")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def load_pair_data(self, 
                      symbol1: str, 
                      symbol2: str, 
                      start_date: str, 
                      end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load data for a trading pair.
        
        Args:
            symbol1: First symbol of the pair
            symbol2: Second symbol of the pair
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            Tuple of (symbol1_data, symbol2_data) as DataFrames
        """
        logger.info(f"Loading data for pair {symbol1}/{symbol2} from {start_date} to {end_date}")
        
        if self.data_source == 'clickhouse':
            return self._load_from_clickhouse(symbol1, symbol2, start_date, end_date)
        elif self.data_source == 'csv':
            return self._load_from_csv(symbol1, symbol2, start_date, end_date)
        else:
            raise ValueError(f"Unsupported data source: {self.data_source}")
    
    def _load_from_clickhouse(self, 
                             symbol1: str, 
                             symbol2: str, 
                             start_date: str, 
                             end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from ClickHouse database."""
        database_name = self.database_config.get('database', 'polygon_data')
        
        # Query for both symbols
        query = f"""
        SELECT 
            ticker as symbol,
            toStartOfFiveMinutes(toDateTime(window_start / 1000000000)) as timestamp,
            argMax(close, window_start) as close_price,
            argMax(open, window_start) as open_price,
            max(high) as high_price,
            min(low) as low_price,
            sum(volume) as volume
        FROM {database_name}.ticks
        WHERE ticker IN ('{symbol1}', '{symbol2}')
        AND toDateTime(window_start / 1000000000) BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY ticker, timestamp
        ORDER BY ticker, timestamp
        """
        
        try:
            df = self.client.query_df(query)
            
            if df.empty:
                raise ValueError(f"No data found for symbols {symbol1}, {symbol2}")
            
            # Split data by symbol
            df1 = df[df['symbol'] == symbol1].copy()
            df2 = df[df['symbol'] == symbol2].copy()
            
            if df1.empty or df2.empty:
                raise ValueError(f"Missing data for one or both symbols: {symbol1}, {symbol2}")
            
            # Process data
            df1 = self._process_raw_data(df1, symbol1)
            df2 = self._process_raw_data(df2, symbol2)
            
            logger.info(f"Loaded {len(df1)} records for {symbol1}, {len(df2)} records for {symbol2}")
            
            return df1, df2
            
        except Exception as e:
            logger.error(f"Error loading data from ClickHouse: {e}")
            raise
    
    def _load_from_csv(self, 
                      symbol1: str, 
                      symbol2: str, 
                      start_date: str, 
                      end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load data from CSV files."""
        try:
            # Load CSV files (assuming they exist in data directory)
            df1 = pd.read_csv(f"data/{symbol1}.csv")
            df2 = pd.read_csv(f"data/{symbol2}.csv")
            
            # Process timestamps
            df1['timestamp'] = pd.to_datetime(df1['timestamp'])
            df2['timestamp'] = pd.to_datetime(df2['timestamp'])
            
            # Filter by date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            df1 = df1[(df1['timestamp'] >= start_dt) & (df1['timestamp'] <= end_dt)]
            df2 = df2[(df2['timestamp'] >= start_dt) & (df2['timestamp'] <= end_dt)]
            
            # Process data
            df1 = self._process_raw_data(df1, symbol1)
            df2 = self._process_raw_data(df2, symbol2)
            
            logger.info(f"Loaded {len(df1)} records for {symbol1}, {len(df2)} records for {symbol2}")
            
            return df1, df2
            
        except Exception as e:
            logger.error(f"Error loading data from CSV: {e}")
            raise
    
    def _process_raw_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Process raw data into standardized format."""
        # Ensure required columns exist
        required_columns = ['timestamp', 'close_price']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns for {symbol}: {missing_columns}")
        
        # Standardize column names
        df = df.rename(columns={
            'close_price': 'close',
            'open_price': 'open',
            'high_price': 'high',
            'low_price': 'low'
        })
        
        # Set timestamp as index
        df = df.set_index('timestamp').sort_index()
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Fill missing OHLC data with close prices if needed
        if 'open' not in df.columns:
            df['open'] = df['close']
        if 'high' not in df.columns:
            df['high'] = df['close']
        if 'low' not in df.columns:
            df['low'] = df['close']
        if 'volume' not in df.columns:
            df['volume'] = 0
        
        # Forward fill missing values
        df = df.fillna(method='ffill')
        
        # Remove any remaining NaN values
        df = df.dropna()
        
        # Add symbol column
        df['symbol'] = symbol
        
        # Calculate basic technical indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        return df
    
    def get_aligned_data(self, 
                        symbol1: str, 
                        symbol2: str, 
                        start_date: str, 
                        end_date: str) -> pd.DataFrame:
        """
        Get aligned data for both symbols in a single DataFrame.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with aligned data for both symbols
        """
        # Load individual data
        df1, df2 = self.load_pair_data(symbol1, symbol2, start_date, end_date)
        
        # Align data by timestamp
        aligned_data = pd.DataFrame(index=df1.index.union(df2.index))
        
        # Add price data
        aligned_data[f'{symbol1}_close'] = df1['close']
        aligned_data[f'{symbol2}_close'] = df2['close']
        aligned_data[f'{symbol1}_volume'] = df1['volume']
        aligned_data[f'{symbol2}_volume'] = df2['volume']
        
        # Add returns
        aligned_data[f'{symbol1}_returns'] = df1['returns']
        aligned_data[f'{symbol2}_returns'] = df2['returns']
        
        # Forward fill missing values
        aligned_data = aligned_data.fillna(method='ffill')
        
        # Remove rows with any missing data
        aligned_data = aligned_data.dropna()
        
        logger.info(f"Aligned data: {len(aligned_data)} common timestamps")
        
        return aligned_data
    
    def get_data_summary(self, 
                        symbol1: str, 
                        symbol2: str, 
                        start_date: str, 
                        end_date: str) -> Dict[str, Any]:
        """
        Get summary statistics for the data.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with summary statistics
        """
        df1, df2 = self.load_pair_data(symbol1, symbol2, start_date, end_date)
        
        summary = {
            'pair': f"{symbol1}/{symbol2}",
            'date_range': f"{start_date} to {end_date}",
            'data_points': {
                symbol1: len(df1),
                symbol2: len(df2)
            },
            'price_stats': {
                symbol1: {
                    'mean': float(df1['close'].mean()),
                    'std': float(df1['close'].std()),
                    'min': float(df1['close'].min()),
                    'max': float(df1['close'].max())
                },
                symbol2: {
                    'mean': float(df2['close'].mean()),
                    'std': float(df2['close'].std()),
                    'min': float(df2['close'].min()),
                    'max': float(df2['close'].max())
                }
            },
            'correlation': float(df1['close'].corr(df2['close'])) if len(df1) == len(df2) else None,
            'data_quality': {
                'missing_data_pct': {
                    symbol1: float(df1.isnull().sum().sum() / len(df1) * 100),
                    symbol2: float(df2.isnull().sum().sum() / len(df2) * 100)
                }
            }
        }
        
        return summary
    
    def validate_data_quality(self, 
                             symbol1: str, 
                             symbol2: str, 
                             start_date: str, 
                             end_date: str) -> Dict[str, Any]:
        """
        Validate data quality for the pair.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with validation results
        """
        df1, df2 = self.load_pair_data(symbol1, symbol2, start_date, end_date)
        
        validation = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'data_coverage': {
                symbol1: len(df1),
                symbol2: len(df2)
            }
        }
        
        # Check minimum data requirements
        min_observations = 100
        if len(df1) < min_observations or len(df2) < min_observations:
            validation['valid'] = False
            validation['issues'].append(f"Insufficient data: need at least {min_observations} observations")
        
        # Check for excessive missing data
        missing_pct_threshold = 5.0
        missing_pct_1 = df1.isnull().sum().sum() / len(df1) * 100
        missing_pct_2 = df2.isnull().sum().sum() / len(df2) * 100
        
        if missing_pct_1 > missing_pct_threshold:
            validation['warnings'].append(f"{symbol1} has {missing_pct_1:.1f}% missing data")
        if missing_pct_2 > missing_pct_threshold:
            validation['warnings'].append(f"{symbol2} has {missing_pct_2:.1f}% missing data")
        
        # Check for zero prices
        if (df1['close'] <= 0).any():
            validation['valid'] = False
            validation['issues'].append(f"{symbol1} has zero or negative prices")
        if (df2['close'] <= 0).any():
            validation['valid'] = False
            validation['issues'].append(f"{symbol2} has zero or negative prices")
        
        # Check for extreme price movements (>50% in one period)
        extreme_threshold = 0.5
        extreme_moves_1 = (df1['returns'].abs() > extreme_threshold).sum()
        extreme_moves_2 = (df2['returns'].abs() > extreme_threshold).sum()
        
        if extreme_moves_1 > 0:
            validation['warnings'].append(f"{symbol1} has {extreme_moves_1} extreme price movements")
        if extreme_moves_2 > 0:
            validation['warnings'].append(f"{symbol2} has {extreme_moves_2} extreme price movements")
        
        return validation 