"""
ClickHouse database client with connection pooling and query optimization
"""
from typing import Dict, List, Optional, Union, Any
import logging
import pandas as pd
from datetime import datetime, timedelta
from clickhouse_driver import Client
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time

from ..monitoring import MetricsCollector
from ..config import ConfigManager

logger = logging.getLogger(__name__)

def with_metrics(func):
    """Decorator to track query metrics"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(self, *args, **kwargs)
            self.metrics.record_latency(
                f"clickhouse_{func.__name__}",
                (time.perf_counter() - start_time) * 1000
            )
            return result
        except Exception as e:
            self.metrics.increment_counter(f"clickhouse_error_{func.__name__}")
            raise
    return wrapper

class ClickHouseClient:
    """High-performance ClickHouse client with connection pooling"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or ConfigManager().get_database_config()
        self.metrics = MetricsCollector()
        self._init_connection_pool()
        
    def _init_connection_pool(self):
        """Initialize connection pool"""
        self.pool_size = self.config.get('pool_size', 5)
        self.pool = ThreadPoolExecutor(max_workers=self.pool_size)
        self.connections = []
        
        for _ in range(self.pool_size):
            client = Client(
                host=self.config['host'],
                port=self.config.get('port', 9000),
                database=self.config['database'],
                user=self.config.get('user', 'default'),
                password=self.config.get('password', ''),
                settings={
                    'max_execution_time': 300,
                    'max_memory_usage': 10000000000
                }
            )
            self.connections.append(client)
    
    @with_metrics
    def fetch_market_data(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch market data for multiple symbols
        
        Args:
            symbols: List of symbol identifiers
            start_date: Start date for data fetch
            end_date: End date for data fetch
            fields: List of fields to fetch (default: all fields)
        
        Returns:
            Dict mapping symbols to their respective DataFrames
        """
        end_date = end_date or datetime.now()
        start_date = start_date or (end_date - timedelta(days=252))
        fields = fields or ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        query = f"""
            SELECT {', '.join(fields)}
            FROM market_data
            WHERE symbol IN {tuple(symbols)}
                AND timestamp BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY symbol, timestamp
        """
        
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        
        results = self._execute_query(query, params)
        return self._process_market_data(results, symbols, fields)
    
    @with_metrics
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Execute a custom query and return results as DataFrame
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            DataFrame with query results
        """
        # Execute query using thread executor for async compatibility
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _sync_execute():
            results = self._execute_query(query, params)
            if not results:
                return pd.DataFrame()
            
            # Convert results to DataFrame
            # Assuming first row contains column names or we extract from query
            if results:
                columns = [f'col_{i}' for i in range(len(results[0]))]
                # Try to infer columns from query
                if 'SELECT' in query.upper():
                    select_part = query.upper().split('SELECT')[1].split('FROM')[0]
                    if 'timestamp' in select_part.lower():
                        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol'][:len(results[0])]
                
                df = pd.DataFrame(results, columns=columns[:len(results[0])])
                return df
            
            return pd.DataFrame()
        
        return await loop.run_in_executor(None, _sync_execute)
    
    @with_metrics
    def insert_market_data(
        self,
        symbol: str,
        data: pd.DataFrame
    ) -> None:
        """
        Insert market data for a symbol
        
        Args:
            symbol: Symbol identifier
            data: DataFrame containing market data
        """
        required_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        assert all(col in data.columns for col in required_columns), \
            f"Missing required columns. Required: {required_columns}"
        
        # Prepare data for insertion
        data = data.reset_index() if 'timestamp' not in data.columns else data
        records = data.to_dict('records')
        
        query = """
            INSERT INTO market_data (
                symbol, timestamp, open, high, low, close, volume
            ) VALUES
        """
        
        self._execute_query(query, records)
    
    @with_metrics
    def fetch_pairs_data(
        self,
        pairs: List[tuple],
        lookback_days: int = 252
    ) -> Dict[tuple, pd.DataFrame]:
        """
        Fetch data for multiple pairs efficiently
        
        Args:
            pairs: List of symbol pairs (e.g., [('AAPL', 'GOOGL'), ('MSFT', 'AMZN')])
            lookback_days: Number of trading days to look back
        
        Returns:
            Dict mapping pairs to their respective DataFrames
        """
        # Flatten pairs into unique symbols
        symbols = list(set([sym for pair in pairs for sym in pair]))
        
        # Fetch all required data in one query
        all_data = self.fetch_market_data(
            symbols=symbols,
            start_date=datetime.now() - timedelta(days=lookback_days)
        )
        
        # Combine pairs
        pairs_data = {}
        for sym1, sym2 in pairs:
            if sym1 in all_data and sym2 in all_data:
                # Align timestamps
                df1 = all_data[sym1]
                df2 = all_data[sym2]
                combined = pd.merge(
                    df1, df2,
                    on='timestamp',
                    suffixes=(f'_{sym1}', f'_{sym2}')
                )
                pairs_data[(sym1, sym2)] = combined
            
        return pairs_data
    
    def _execute_query(
        self,
        query: str,
        params: Optional[Union[Dict, List]] = None
    ) -> List[tuple]:
        """Execute query with automatic connection management"""
        try:
            # Get a connection from the pool
            client = self.connections[0]  # Simple round-robin for now
            
            # Execute query
            start_time = time.perf_counter()
            results = client.execute(query, params)
            query_time = (time.perf_counter() - start_time) * 1000
            
            # Record metrics
            self.metrics.record_latency("clickhouse_query", query_time)
            if query_time > self.config.get('slow_query_threshold_ms', 1000):
                logger.warning(f"Slow query detected: {query_time:.2f}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            self.metrics.increment_counter("clickhouse_query_error")
            raise
    
    def _process_market_data(
        self,
        results: List[tuple],
        symbols: List[str],
        fields: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Process raw query results into DataFrames"""
        # Group results by symbol
        symbol_data = {sym: [] for sym in symbols}
        for row in results:
            symbol_data[row[0]].append(row[1:])
        
        # Convert to DataFrames
        dataframes = {}
        for symbol, rows in symbol_data.items():
            if rows:
                df = pd.DataFrame(rows, columns=fields[1:])  # Exclude symbol column
                df.set_index('timestamp', inplace=True)
                dataframes[symbol] = df
        
        return dataframes
    
    async def close(self):
        """Close ClickHouse connections"""
        try:
            for client in self.connections:
                client.disconnect()
            self.pool.shutdown(wait=True)
            logger.info("ClickHouse connections closed")
        except Exception as e:
            logger.error(f"Error closing ClickHouse connections: {e}")
    
    def __del__(self):
        """Cleanup connections"""
        for client in self.connections:
            try:
                client.disconnect()
            except:
                pass
        self.pool.shutdown(wait=True) 