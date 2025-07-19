#!/usr/bin/env python3
"""
ClickHouse Data Loader for MVS Framework
Institutional-grade market data loading
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

try:
    from clickhouse_driver import Client
    CLICKHOUSE_AVAILABLE = True
    print("✅ ClickHouse driver loaded successfully")
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    print("❌ ClickHouse driver not available")

class ClickHouseConfig:
    """ClickHouse configuration manager"""
    
    def __init__(self, config_path=None):
        if config_path is None:
            # Try to find config file
            possible_paths = [
                "../ClickHouse_Manager/configs/clickhouse_config.json",
                "../../ClickHouse_Manager/configs/clickhouse_config.json",
                "configs/clickhouse_config.json"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    self.config = json.load(f)
                print(f"✅ Loaded ClickHouse config from {config_path}")
            except Exception as e:
                print(f"⚠️  Failed to load config from {config_path}: {e}")
                self.config = self._default_config()
        else:
            print("⚠️  Using default ClickHouse configuration")
            self.config = self._default_config()
    
    def _default_config(self):
        return {
            "host": "localhost",
            "port": 9000,
            "database": "polygon_data", 
            "user": "default",
            "password": "",
            "settings": {
                "max_execution_time": 300,
                "max_memory_usage": 10000000000
            }
        }
    
    def get_connection_params(self):
        return {
            'host': self.config.get('host', 'localhost'),
            'port': self.config.get('port', 9000),
            'database': self.config.get('database', 'polygon_data'),
            'user': self.config.get('user', 'default'),
            'password': self.config.get('password', ''),
            'settings': self.config.get('settings', {})
        }

class MVSClickHouseLoader:
    """ClickHouse data loader optimized for MVS framework"""
    
    def __init__(self, config_path=None):
        self.config = ClickHouseConfig(config_path)
        self.client = None
        self._connected = False
        
        if CLICKHOUSE_AVAILABLE:
            try:
                self.client = Client(**self.config.get_connection_params())
                # Test connection
                result = self.client.execute("SELECT 1")
                self._connected = True
                print("✅ ClickHouse connection established")
                print(f"📊 Connected to database: {self.config.config['database']}")
            except Exception as e:
                print(f"⚠️  ClickHouse connection failed: {e}")
                print(f"🔧 Attempted connection to: {self.config.get_connection_params()}")
                self._connected = False
        else:
            print("❌ ClickHouse driver not available")
    
    def is_connected(self):
        return self._connected and self.client is not None
    
    def load_market_data(self, symbols: List[str], days: int = 500, interval: str = '1d') -> Dict[str, pd.DataFrame]:
        """
        Load market data for given symbols
        
        Args:
            symbols: List of symbols to load
            days: Number of days to load
            interval: Data interval (1d, 1h, 1min)
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        if not self.is_connected():
            raise Exception("ClickHouse not connected")
        
        print(f"📊 Loading {len(symbols)} symbols from ClickHouse...")
        print(f"📅 Period: {days} days, Interval: {interval}")
        
        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Convert to nanoseconds for window_start comparison
        start_ns = int(start_date.timestamp() * 1_000_000_000)
        end_ns = int(end_date.timestamp() * 1_000_000_000)
        
        market_data = {}
        
        # Check if we have the ticks table (which is actually aggregated bars)
        tables = self.get_available_tables()
        
        if 'ticks' in tables:
            # Use the ticks table structure
            for symbol in symbols:
                try:
                    query = f"""
                    SELECT 
                        window_start,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM ticks
                    WHERE ticker = '{symbol}'
                    AND window_start BETWEEN {start_ns} AND {end_ns}
                    ORDER BY window_start
                    """
                    
                    result = self.client.execute(query)
                    
                    if result:
                        # Create DataFrame
                        df = pd.DataFrame(result, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        
                        # Convert nanosecond timestamp to datetime
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ns')
                        df.set_index('timestamp', inplace=True)
                        
                        # Resample if needed
                        if interval != '1min':  # Default appears to be 1-minute bars
                            df = self._resample_data(df, interval)
                        
                        market_data[symbol] = df
                        print(f"✅ {symbol}: {len(df)} records from {df.index.min()} to {df.index.max()}")
                    else:
                        print(f"⚠️  {symbol}: No data found")
                        
                except Exception as e:
                    print(f"❌ Error loading {symbol}: {e}")
        else:
            # Fallback to original table-based approach
            return self._load_from_standard_tables(symbols, days, interval)
                
        return market_data
    
    def _resample_data(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """Resample data to different intervals"""
        # Map intervals to pandas frequency strings
        freq_map = {
            '1min': '1T',
            '5min': '5T', 
            '15min': '15T',
            '30min': '30T',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        
        freq = freq_map.get(interval, '1D')
        
        return df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    def _load_from_standard_tables(self, symbols: List[str], days: int, interval: str) -> Dict[str, pd.DataFrame]:
        """Fallback method for standard table structures"""
        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        market_data = {}
        
        # Determine table name based on interval
        table_mapping = {
            '1min': 'minute_bars',
            '5min': 'minute_bars',  # We'll aggregate
            '1h': 'hourly_bars',
            '1d': 'daily_bars'
        }
        
        table_name = table_mapping.get(interval, 'daily_bars')
        
        for symbol in symbols:
            try:
                # Build query based on interval
                if interval == '1d':
                    query = f"""
                    SELECT 
                        date,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM {table_name}
                    WHERE symbol = '{symbol}'
                    AND date BETWEEN '{start_date.strftime('%Y-%m-%d')}' 
                    AND '{end_date.strftime('%Y-%m-%d')}'
                    ORDER BY date
                    """
                else:
                    query = f"""
                    SELECT 
                        timestamp,
                        open,
                        high,
                        low,
                        close,
                        volume
                    FROM {table_name}
                    WHERE symbol = '{symbol}'
                    AND timestamp BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' 
                    AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    ORDER BY timestamp
                    """
                
                # Execute query
                result = self.client.execute(query)
                
                if result:
                    # Create DataFrame
                    time_col = 'date' if interval == '1d' else 'timestamp'
                    df = pd.DataFrame(result, columns=[time_col, 'open', 'high', 'low', 'close', 'volume'])
                    df[time_col] = pd.to_datetime(df[time_col])
                    df.set_index(time_col, inplace=True)
                    
                    # Aggregate if needed
                    if interval == '5min' and table_name == 'minute_bars':
                        df = self._aggregate_to_5min(df)
                    
                    market_data[symbol] = df
                    print(f"✅ {symbol}: {len(df)} records from {df.index.min()} to {df.index.max()}")
                else:
                    print(f"⚠️  {symbol}: No data found")
                    
            except Exception as e:
                print(f"❌ Error loading {symbol}: {e}")
                
        return market_data
    
    def _aggregate_to_5min(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate minute data to 5-minute bars"""
        return df.resample('5T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables"""
        if not self.is_connected():
            return []
        
        try:
            query = "SHOW TABLES"
            result = self.client.execute(query)
            tables = [row[0] for row in result]
            print(f"📋 Available tables: {tables}")
            return tables
            
        except Exception as e:
            print(f"❌ Error getting tables: {e}")
            return []
    
    def get_available_symbols(self, limit: int = 100) -> List[str]:
        """Get list of available symbols"""
        if not self.is_connected():
            return []
        
        # First check what tables are available
        tables = self.get_available_tables()
        
        # Try different table names, including 'ticks'
        possible_tables = ['daily_bars', 'minute_bars', 'stock_data', 'polygon_stocks', 'market_data', 'ticks']
        table_to_use = None
        
        for table in possible_tables:
            if table in tables:
                table_to_use = table
                break
        
        if not table_to_use:
            print(f"⚠️  No recognized data tables found. Available: {tables}")
            return []
        
        # Examine table structure first
        try:
            print(f"🔍 Examining table structure for '{table_to_use}'...")
            describe_result = self.client.execute(f"DESCRIBE {table_to_use}")
            print("📋 Column structure:")
            for row in describe_result:
                print(f"  {row[0]} - {row[1]}")
                
            # Get sample data
            sample_result = self.client.execute(f"SELECT * FROM {table_to_use} LIMIT 3")
            print("📊 Sample data:")
            for i, row in enumerate(sample_result):
                print(f"  Row {i+1}: {row}")
                
        except Exception as e:
            print(f"⚠️  Could not examine table structure: {e}")
        
        try:
            # Try to get symbols - adapt query based on table
            if table_to_use == 'ticks':
                # For ticks table, try common column names
                possible_symbol_columns = ['symbol', 'ticker', 'sym', 'stock_symbol']
                symbol_query = None
                
                for col in possible_symbol_columns:
                    try:
                        test_query = f"SELECT DISTINCT {col} FROM {table_to_use} LIMIT 1"
                        self.client.execute(test_query)
                        symbol_query = f"SELECT DISTINCT {col} FROM {table_to_use} ORDER BY {col} LIMIT {limit}"
                        break
                    except:
                        continue
                
                if not symbol_query:
                    print(f"⚠️  Could not find symbol column in {table_to_use}")
                    return []
                    
                result = self.client.execute(symbol_query)
            else:
                query = f"""
                SELECT DISTINCT symbol 
                FROM {table_to_use} 
                ORDER BY symbol 
                LIMIT {limit}
                """
                result = self.client.execute(query)
            
            symbols = [row[0] for row in result]
            print(f"✅ Found {len(symbols)} symbols in table '{table_to_use}'")
            return symbols
            
        except Exception as e:
            print(f"❌ Error getting symbols from {table_to_use}: {e}")
            return []
    
    def get_data_range(self, symbol: str) -> Optional[tuple]:
        """Get date range for a symbol"""
        if not self.is_connected():
            return None
            
        try:
            query = f"""
            SELECT 
                min(date) as start_date,
                max(date) as end_date,
                count(*) as record_count
            FROM {self.config.config['database']}.daily_bars 
            WHERE symbol = '{symbol}'
            """
            
            result = self.client.execute(query)
            if result:
                return result[0]
            return None
            
        except Exception as e:
            print(f"❌ Error getting date range for {symbol}: {e}")
            return None
    
    def close(self):
        """Close ClickHouse connection"""
        if self.client:
            try:
                self.client.disconnect()
                print("✅ ClickHouse connection closed")
            except:
                pass
            self._connected = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Async wrapper for compatibility with institutional demo
class AsyncClickHouseLoader:
    """Async wrapper for ClickHouse loader"""
    
    def __init__(self, config_path=None):
        self.loader = MVSClickHouseLoader(config_path)
    
    async def load_market_data(self, request):
        """Async interface for market data loading"""
        # Extract parameters from request object
        symbols = request.symbols if hasattr(request, 'symbols') else request
        days = getattr(request, 'days', 500)
        interval = getattr(request, 'interval', '1d')
        
        # Use sync loader
        return self.loader.load_market_data(symbols, days, interval)
    
    async def close(self):
        """Close connection"""
        self.loader.close()

if __name__ == "__main__":
    # Test the loader
    print("🧪 Testing ClickHouse loader...")
    
    with MVSClickHouseLoader() as loader:
        if loader.is_connected():
            # Get available symbols
            symbols = loader.get_available_symbols(10)
            print(f"📋 Available symbols: {symbols}")
            
            if symbols:
                # Test data loading
                test_symbols = symbols[:3]  # Test first 3 symbols
                data = loader.load_market_data(test_symbols, days=30, interval='1d')
                
                for symbol, df in data.items():
                    print(f"📊 {symbol}: {len(df)} records")
                    if not df.empty:
                        print(f"    Latest: {df.index[-1]} - Close: ${df['close'].iloc[-1]:.2f}")
            
        else:
            print("❌ ClickHouse not available - check connection and driver installation")
