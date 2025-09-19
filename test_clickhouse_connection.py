#!/usr/bin/env python3
"""
Test ClickHouse Connection and Explore Available Data
====================================================

Test script to connect to local ClickHouse and explore available data
for the trading pipeline implementation.
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_clickhouse_connection():
    """Test ClickHouse connection and explore available data"""
    try:
        # Use core_structure ClickHouse client
        from core_structure.infrastructure.database.database_system import ClickHouseClient
        
        # Create client with development defaults
        client = ClickHouseClient()
        
        logger.info("Testing ClickHouse connection...")
        
        # Test basic connection
        if client.test_connection():
            logger.info("✅ ClickHouse connection successful!")
        else:
            logger.error("❌ ClickHouse connection failed!")
            return False
            
        # Get available databases
        logger.info("\n=== Available Databases ===")
        databases = client.query_dataframe("SHOW DATABASES")
        print(databases)
        
        # Check specific databases
        for db in ['polygon_data', 'trading', 'default']:
            try:
                # Switch to database and check tables
                logger.info(f"\n=== Tables in {db} database ===")
                tables = client.query_dataframe(f"SHOW TABLES FROM {db}")
                print(f"Tables in {db}:")
                print(tables)
                
                # If we find any tables, check the first one
                if not tables.empty:
                    table_name = tables.iloc[0, 0]  # First table name
                    logger.info(f"\n=== Sample data from {db}.{table_name} ===")
                    sample = client.query_dataframe(f"SELECT * FROM {db}.{table_name} LIMIT 5")
                    print(sample)
                    
            except Exception as e:
                logger.warning(f"Could not access database {db}: {e}")
        
        # Check for market data specifically
        logger.info("\n=== Searching for Market Data ===")
        for db in ['polygon_data', 'trading', 'default']:
            try:
                # Look for market data tables
                tables = client.query_dataframe(f"""
                    SELECT name 
                    FROM system.tables 
                    WHERE database = '{db}' 
                    AND (name LIKE '%market%' OR name LIKE '%ohlc%' OR name LIKE '%price%' OR name LIKE '%tick%')
                """)
                
                if not tables.empty:
                    logger.info(f"Found market data tables in {db}:")
                    for _, row in tables.iterrows():
                        table_name = row['name']
                        print(f"  - {table_name}")
                        
                        # Get table structure
                        try:
                            structure = client.query_dataframe(f"DESCRIBE {db}.{table_name}")
                            print(f"    Structure: {list(structure['name'])}")
                            
                            # Check for 2024-12-20 data
                            count_query = f"""
                            SELECT COUNT(*) as count 
                            FROM {db}.{table_name} 
                            WHERE timestamp >= '2024-12-20 00:00:00' 
                            AND timestamp < '2024-12-21 00:00:00'
                            """
                            count_result = client.query_dataframe(count_query)
                            if not count_result.empty and count_result.iloc[0]['count'] > 0:
                                logger.info(f"    ✅ Found {count_result.iloc[0]['count']} records for 2024-12-20")
                                
                                # Get sample of 2024-12-20 data
                                sample_query = f"""
                                SELECT * 
                                FROM {db}.{table_name} 
                                WHERE timestamp >= '2024-12-20 00:00:00' 
                                AND timestamp < '2024-12-21 00:00:00'
                                LIMIT 3
                                """
                                sample = client.query_dataframe(sample_query)
                                print("    Sample data:")
                                print(sample)
                            else:
                                logger.info(f"    ❌ No data found for 2024-12-20")
                                
                        except Exception as e:
                            logger.warning(f"    Error checking table {table_name}: {e}")
                            
            except Exception as e:
                logger.warning(f"Error searching {db}: {e}")
        
        # Check available symbols for 2024-12-20
        logger.info("\n=== Available Symbols for 2024-12-20 ===")
        for db in ['polygon_data', 'trading']:
            for table in ['market_data', 'ohlc_data', 'ticks', 'bars']:
                try:
                    symbols_query = f"""
                    SELECT DISTINCT ticker as symbol, COUNT(*) as records
                    FROM {db}.{table} 
                    WHERE timestamp >= '2024-12-20 00:00:00' 
                    AND timestamp < '2024-12-21 00:00:00'
                    GROUP BY ticker
                    ORDER BY records DESC
                    LIMIT 10
                    """
                    symbols = client.query_dataframe(symbols_query)
                    if not symbols.empty:
                        logger.info(f"Top symbols in {db}.{table} for 2024-12-20:")
                        print(symbols)
                        
                except Exception as e:
                    continue  # Table might not exist
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"Error testing ClickHouse: {e}")
        return False

if __name__ == "__main__":
    test_clickhouse_connection()