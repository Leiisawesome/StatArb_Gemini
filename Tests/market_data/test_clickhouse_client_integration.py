"""
Integration tests for ClickHouse client with real database
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
import asyncio

# Import the client
try:
    from core_structure.infrastructure.database.clickhouse_client import ClickHouseClient
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE, 
    reason=f"ClickHouse client imports not available: {IMPORT_ERROR if not IMPORTS_AVAILABLE else ''}"
)

@pytest.mark.integration
class TestClickHouseClientIntegration:
    """Integration tests with real ClickHouse database"""
    
    @pytest.fixture
    def real_clickhouse_config(self):
        """Real ClickHouse configuration"""
        return {
            'host': 'localhost',
            'port': 9000,
            'database': 'polygon_data',
            'user': 'default',
            'password': '',
            'pool_size': 2
        }
    
    def test_connection_and_basic_query(self, real_clickhouse_config):
        """Test basic connection and query"""
        client = ClickHouseClient(real_clickhouse_config)
        
        # Test basic query - get version
        results = client._execute_query("SELECT version()")
        assert len(results) > 0
        assert isinstance(results[0][0], str)
        print(f"ClickHouse version: {results[0][0]}")
    
    def test_table_exists_and_schema(self, real_clickhouse_config):
        """Test that ticks table exists and has expected schema"""
        client = ClickHouseClient(real_clickhouse_config)
        
        # Check if ticks table exists
        results = client._execute_query("SHOW TABLES")
        table_names = [row[0] for row in results]
        assert 'ticks' in table_names
        
        # Get table schema
        results = client._execute_query("DESCRIBE ticks")
        columns = {row[0]: row[1] for row in results}
        
        # Check expected columns
        expected_columns = ['ticker', 'volume', 'open', 'close', 'high', 'low', 'window_start', 'transactions']
        for col in expected_columns:
            assert col in columns, f"Column {col} not found in ticks table"
        
        print(f"Table schema: {columns}")
    
    def test_data_retrieval_from_ticks(self, real_clickhouse_config):
        """Test retrieving actual data from ticks table"""
        client = ClickHouseClient(real_clickhouse_config)
        
        # Get count of records
        results = client._execute_query("SELECT COUNT(*) FROM ticks")
        total_count = results[0][0]
        assert total_count > 0
        print(f"Total records in ticks: {total_count:,}")
        
        # Get sample of distinct tickers
        results = client._execute_query("SELECT DISTINCT ticker FROM ticks LIMIT 10")
        tickers = [row[0] for row in results]
        assert len(tickers) > 0
        print(f"Sample tickers: {tickers}")
        
        # Get sample data for first ticker
        if tickers:
            sample_ticker = tickers[0]
            results = client._execute_query(
                "SELECT * FROM ticks WHERE ticker = %(ticker)s LIMIT 5",
                {'ticker': sample_ticker}
            )
            assert len(results) > 0
            print(f"Sample data for {sample_ticker}: {len(results)} records")
    
    @pytest.mark.asyncio
    async def test_async_execute_query(self, real_clickhouse_config):
        """Test the async execute_query method"""
        client = ClickHouseClient(real_clickhouse_config)
        
        # Test async query
        df = await client.execute_query("SELECT COUNT(*) as count FROM ticks")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert 'count' in df.columns or 'col_0' in df.columns
        
        print(f"Async query result: {df}")
    
    @pytest.mark.asyncio
    async def test_async_close(self, real_clickhouse_config):
        """Test the async close method"""
        client = ClickHouseClient(real_clickhouse_config)
        
        # Test connection works
        results = client._execute_query("SELECT 1")
        assert len(results) > 0
        
        # Test close
        await client.close()
        print("Connection closed successfully")

if __name__ == "__main__":
    # Quick test run
    pytest.main([__file__, "-v"])
