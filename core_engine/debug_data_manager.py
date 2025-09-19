#!/usr/bin/env python3
"""Debug script to test data manager query"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager_enhanced import ClickHouseDataManager

dm = ClickHouseDataManager()

# Test connection
print("Testing connection...")
result = dm._test_connection()
print(f"Connection result: {result}")

# Test query execution
print("\nTesting query execution...")
query = """
SELECT ticker, COUNT(*) as records
FROM polygon_data.ticks 
WHERE toDate(toDateTime(window_start / 1000000000)) = '2024-12-20'
GROUP BY ticker
HAVING records > 100
ORDER BY records DESC
LIMIT 5
"""

try:
    df = dm._execute_query(query)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"First few rows:\n{df.head()}")
    
    if 'ticker' in df.columns:
        symbols = df['ticker'].tolist()
        print(f"Symbols: {symbols}")
    else:
        print("No ticker column found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Test get_available_symbols
print("\nTesting get_available_symbols...")
try:
    symbols = dm.get_available_symbols()
    print(f"Available symbols: {symbols}")
except Exception as e:
    print(f"Error in get_available_symbols: {e}")
    import traceback
    traceback.print_exc()