"""
Data loading and management for momentum backtest
Integrates with existing ClickHouse infrastructure
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import clickhouse_connect

# Add parent directory to path to import from new_structure
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'new_structure'))

try:
    from market_data.data_manager import DataManager
    from infrastructure.database_layer import DatabaseClient
except ImportError as e:
    logging.warning(f"Could not import from new_structure: {e}")
    DataManager = None
    DatabaseClient = None

logger = logging.getLogger(__name__)

class ClickHouseDataLoader:
    """
    Production-grade data loader for momentum backtesting
    Interfaces with existing ClickHouse infrastructure
    """
    
    def __init__(self, config: Dict):
        """Initialize ClickHouse connection"""
        # Try clickhouse section first, then fall back to data section
        clickhouse_config = config.get('clickhouse', {})
        data_config = config.get('data', {})
        
        self.host = clickhouse_config.get('host', data_config.get('clickhouse_host', 'localhost'))
        self.port = clickhouse_config.get('port', data_config.get('clickhouse_port', 8123))
        self.database = clickhouse_config.get('database', data_config.get('clickhouse_database', 'polygon_data'))
        self.username = clickhouse_config.get('username', 'default')
        self.password = clickhouse_config.get('password', '')
        
        self.min_trading_days = data_config.get('min_trading_days', 200)
        self.min_avg_volume = data_config.get('min_avg_volume', 1000000)
        self.universe_size = data_config.get('universe_size', 100)
        
        # Configurable date periods
        self.training_start = data_config.get('training_start', '2023-01-01')
        self.training_end = data_config.get('training_end', '2024-01-31')
        self.testing_start = data_config.get('testing_start', '2025-01-01')
        self.testing_end = data_config.get('testing_end', '2025-06-30')
        
        # Initialize connection
        self.client = None
        self._connect()
        
    def _connect(self):
        """Establish ClickHouse connection"""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                database=self.database,
                username=self.username,
                password=self.password
            )
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port}/{self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols in the database using configurable date range"""
        try:
            # Use the earlier of training_start and testing_start as the start date
            # Use the later of training_end and testing_end as the end date
            # This ensures symbols have data coverage for the entire period being used
            overall_start = min(self.training_start, self.testing_start)
            overall_end = max(self.training_end, self.testing_end)
            
            # Query to get symbols with sufficient data from ticks table
            query = f"""
            SELECT 
                ticker, 
                COUNT(DISTINCT DATE(toDateTime(toUInt32(window_start / 1000000000)))) as trading_days,
                AVG(volume) as avg_volume
            FROM ticks 
            WHERE DATE(toDateTime(toUInt32(window_start / 1000000000))) >= '{overall_start}' 
            AND DATE(toDateTime(toUInt32(window_start / 1000000000))) <= '{overall_end}'
            AND volume > 0 
            AND close > 5.0
            GROUP BY ticker
            HAVING trading_days >= {self.min_trading_days}
            AND avg_volume >= {self.min_avg_volume}
            ORDER BY avg_volume DESC
            LIMIT {self.universe_size}
            """
            
            result = self.client.query(query)
            
            symbols = [row[0] for row in result.result_set]
            logger.info(f"Found {len(symbols)} symbols meeting criteria for period {overall_start} to {overall_end}")
            return symbols
            
        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []
    
    def load_price_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load OHLCV price data for given symbols and date range
        
        Returns:
            DataFrame with MultiIndex (date, symbol) and columns [open, high, low, close, volume]
        """
        try:
            # Format symbols for SQL IN clause
            symbols_str = "', '".join(symbols)
            
            query = f"""
            SELECT 
                date,
                symbol,
                open,
                high,
                low,
                close,
                volume
            FROM stock_prices 
            WHERE symbol IN ('{symbols_str}')
            AND date >= '{start_date}'
            AND date <= '{end_date}'
            AND volume > 0
            ORDER BY date, symbol
            """
            
            result = self.client.query(query)
            
            # Convert to DataFrame
            df = pd.DataFrame(result.result_rows, columns=[
                'date', 'symbol', 'open', 'high', 'low', 'close', 'volume'
            ])
            
            # Convert date column
            df['date'] = pd.to_datetime(df['date'])
            
            # Set MultiIndex
            df = df.set_index(['date', 'symbol'])
            
            # Sort index
            df = df.sort_index()
            
            logger.info(f"Loaded {len(df)} price records for {len(symbols)} symbols")
            logger.info(f"Date range: {df.index.get_level_values('date').min()} to {df.index.get_level_values('date').max()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading price data: {e}")
            return pd.DataFrame()
    
    def load_training_data(self) -> Tuple[pd.DataFrame, List[str]]:
        """Load training data from configurable date range from ticks table (aggregated to daily)"""
        start_date = self.training_start
        end_date = self.training_end
        
        logger.info(f"Loading training data: {start_date} to {end_date}")
        
        # Get symbol universe
        symbols = self.get_available_symbols()
        
        if not symbols:
            logger.error("No symbols found for training data")
            return pd.DataFrame(), []
        
        # Load and aggregate ticks data to daily OHLCV
        symbols_str = "', '".join(symbols)
        
        query = f"""
        SELECT 
            ticker as symbol,
            DATE(toDateTime(toUInt32(window_start / 1000000000))) as date,
            argMin(open, window_start) as open,
            MAX(high) as high,
            MIN(low) as low,
            argMax(close, window_start) as close,
            SUM(volume) as volume,
            SUM(transactions) as transaction_count
        FROM ticks 
        WHERE DATE(toDateTime(toUInt32(window_start / 1000000000))) >= '{start_date}' 
            AND DATE(toDateTime(toUInt32(window_start / 1000000000))) <= '{end_date}'
            AND ticker IN ('{symbols_str}')
        GROUP BY ticker, DATE(toDateTime(toUInt32(window_start / 1000000000)))
        ORDER BY ticker, date
        """
        
        result = self.client.query(query)
        
        if not result.result_set:
            logger.warning("No training data returned from query")
            return pd.DataFrame(), symbols
        
        # Convert to DataFrame
        df = pd.DataFrame(result.result_set, columns=[
            'symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'transaction_count'
        ])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index(['symbol', 'date'])
        
        # Calculate returns
        df['returns'] = df.groupby('symbol')['close'].pct_change()
        
        logger.info(f"Loaded {len(df)} training records for {len(symbols)} symbols")
        logger.info(f"Date range: {df.index.get_level_values('date').min()} to {df.index.get_level_values('date').max()}")
        
        return df, symbols
    
    def load_testing_data(self, symbols: List[str]) -> pd.DataFrame:
        """Load testing data from configurable date range using same symbols as training"""
        start_date = self.testing_start
        end_date = self.testing_end
        
        logger.info(f"Loading testing data: {start_date} to {end_date}")
        logger.info(f"Using {len(symbols)} symbols from training period")
        
        # Load and aggregate ticks data to daily OHLCV
        symbols_str = "', '".join(symbols)
        
        query = f"""
        SELECT 
            ticker as symbol,
            DATE(toDateTime(toUInt32(window_start / 1000000000))) as date,
            argMin(open, window_start) as open,
            MAX(high) as high,
            MIN(low) as low,
            argMax(close, window_start) as close,
            SUM(volume) as volume,
            SUM(transactions) as transaction_count
        FROM ticks 
        WHERE DATE(toDateTime(toUInt32(window_start / 1000000000))) >= '{start_date}' 
            AND DATE(toDateTime(toUInt32(window_start / 1000000000))) <= '{end_date}'
            AND ticker IN ('{symbols_str}')
        GROUP BY ticker, DATE(toDateTime(toUInt32(window_start / 1000000000)))
        ORDER BY ticker, date
        """
        
        result = self.client.query(query)
        
        if not result.result_set:
            logger.warning("No testing data returned from query")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(result.result_set, columns=[
            'symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'transaction_count'
        ])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index(['symbol', 'date'])
        
        # Calculate returns
        df['returns'] = df.groupby('symbol')['close'].pct_change()
        
        logger.info(f"Loaded {len(df)} testing records")
        logger.info(f"Date range: {df.index.get_level_values('date').min()} to {df.index.get_level_values('date').max()}")
        
        return df
    
    def get_benchmark_data(self, start_date: str, end_date: str, symbol: str = 'SPY') -> pd.DataFrame:
        """Load benchmark data (SPY by default)"""
        try:
            query = f"""
            SELECT 
                date,
                close
            FROM stock_prices 
            WHERE symbol = '{symbol}'
            AND date >= '{start_date}'
            AND date <= '{end_date}'
            ORDER BY date
            """
            
            result = self.client.query(query)
            
            df = pd.DataFrame(result.result_rows, columns=['date', 'close'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df.columns = [f'{symbol}_close']
            
            logger.info(f"Loaded benchmark data for {symbol}: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading benchmark data: {e}")
            return pd.DataFrame()
    
    def validate_data_quality(self, data: pd.DataFrame) -> Dict[str, any]:
        """Validate data quality and return statistics"""
        validation_results = {
            'total_records': len(data),
            'symbols_count': len(data.index.get_level_values('symbol').unique()),
            'date_range': (
                data.index.get_level_values('date').min(),
                data.index.get_level_values('date').max()
            ),
            'missing_values': data.isnull().sum().to_dict(),
            'price_anomalies': {},
            'volume_anomalies': {}
        }
        
        # Check for price anomalies
        for symbol in data.index.get_level_values('symbol').unique():
            symbol_data = data.xs(symbol, level='symbol')
            
            # Daily returns
            returns = symbol_data['close'].pct_change()
            
            # Extreme returns (>20% daily moves)
            extreme_returns = returns[abs(returns) > 0.20]
            validation_results['price_anomalies'][symbol] = len(extreme_returns)
            
            # Zero volume days
            zero_volume = symbol_data[symbol_data['volume'] == 0]
            validation_results['volume_anomalies'][symbol] = len(zero_volume)
        
        logger.info(f"Data validation completed:")
        logger.info(f"  Total records: {validation_results['total_records']}")
        logger.info(f"  Symbols: {validation_results['symbols_count']}")
        logger.info(f"  Date range: {validation_results['date_range']}")
        
        return validation_results
