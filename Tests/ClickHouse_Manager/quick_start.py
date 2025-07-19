#!/usr/bin/env python3
"""
ClickHouse Manager Quick Start Script
====================================

This script helps you get started with the ClickHouse Manager by:
1. Testing the database connection
2. Creating essential tables
3. Loading sample data
4. Running basic queries

Usage:
    python quick_start.py
    python quick_start.py --config configs/production_config.json
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Import the ClickHouse manager
from clickhouse_manager import ClickHouseManager

def generate_sample_market_data(symbols=['AAPL', 'MSFT', 'GOOGL'], days=30):
    """Generate sample market data for testing"""
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    for symbol in symbols:
        base_price = np.random.uniform(100, 300)
        
        for i in range(days * 24):  # Hourly data
            timestamp = base_date + timedelta(hours=i)
            
            # Simple price walk
            price_change = np.random.normal(0, 0.02)
            base_price *= (1 + price_change)
            
            high = base_price * (1 + abs(np.random.normal(0, 0.01)))
            low = base_price * (1 - abs(np.random.normal(0, 0.01)))
            volume = int(np.random.uniform(10000, 100000))
            
            data.append({
                'timestamp': timestamp,
                'symbol': symbol,
                'open': round(base_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(base_price, 2),
                'volume': volume,
                'vwap': round(base_price * (1 + np.random.normal(0, 0.001)), 2),
                'trade_count': int(np.random.uniform(100, 1000))
            })
    
    return data

def quick_start_setup(config_file=None):
    """Run the quick start setup process"""
    print("🚀 ClickHouse Manager Quick Start")
    print("=" * 50)
    
    # Initialize manager
    print("1️⃣ Initializing ClickHouse Manager...")
    try:
        manager = ClickHouseManager(config_file)
        print("✅ Connected to ClickHouse successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("💡 Check your configuration in configs/clickhouse_config.json")
        return False
    
    # Show current database status
    print("\n2️⃣ Current Database Status:")
    try:
        manager.get_database_stats()
    except Exception as e:
        print(f"⚠️  Could not get database stats: {e}")
    
    # Create essential tables
    print("\n3️⃣ Setting up essential tables...")
    
    tables_to_create = [
        ('market_data', 'schemas/market_data.sql'),
        ('trading_signals', 'schemas/trading_signals.sql'),
        ('portfolio_positions', 'schemas/portfolio_positions.sql'),
        ('performance_analytics', 'schemas/performance_analytics.sql')
    ]
    
    for table_name, schema_file in tables_to_create:
        try:
            if manager.create_table(table_name, schema_file):
                print(f"✅ Created table: {table_name}")
            else:
                print(f"⚠️  Table {table_name} might already exist")
        except Exception as e:
            print(f"❌ Failed to create {table_name}: {e}")
    
    # Generate and load sample data
    print("\n4️⃣ Loading sample data...")
    try:
        # Generate sample market data
        sample_data = generate_sample_market_data()
        
        # Save to CSV for reference
        df = pd.DataFrame(sample_data)
        sample_file = Path('sample_data/sample_market_data.csv')
        sample_file.parent.mkdir(exist_ok=True)
        df.to_csv(sample_file, index=False)
        print(f"📁 Saved sample data to {sample_file}")
        
        # Load data into ClickHouse
        if manager.insert_data('market_data', data=sample_data):
            print(f"✅ Loaded {len(sample_data)} rows of sample data")
        else:
            print("❌ Failed to load sample data")
            
    except Exception as e:
        print(f"❌ Error loading sample data: {e}")
    
    # Run test queries
    print("\n5️⃣ Running test queries...")
    
    test_queries = [
        "SELECT COUNT(*) as total_rows FROM market_data",
        "SELECT symbol, COUNT(*) as records FROM market_data GROUP BY symbol",
        "SELECT symbol, MAX(high) as max_price, MIN(low) as min_price FROM market_data GROUP BY symbol"
    ]
    
    for query in test_queries:
        try:
            print(f"\n🔍 Query: {query}")
            manager.query_data(query, limit=10)
        except Exception as e:
            print(f"❌ Query failed: {e}")
    
    # Show final status
    print("\n6️⃣ Final Setup Status:")
    try:
        tables = manager.list_tables()
        print(f"✅ Setup complete! Created {len(tables)} tables.")
    except Exception as e:
        print(f"⚠️  Could not get final status: {e}")
    
    print("\n🎉 Quick Start Complete!")
    print("\n💡 Next Steps:")
    print("   • Run: python clickhouse_manager.py --interactive")
    print("   • Explore tables: python clickhouse_manager.py list-tables")
    print("   • Query data: python clickhouse_manager.py query 'SELECT * FROM market_data LIMIT 5'")
    print("   • Check README.md for detailed usage instructions")
    
    return True

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClickHouse Manager Quick Start")
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--skip-data', action='store_true', help='Skip sample data generation')
    
    args = parser.parse_args()
    
    # Run quick start
    success = quick_start_setup(args.config)
    
    if not success:
        print("\n❌ Quick start failed. Please check your configuration and try again.")
        sys.exit(1)
    else:
        print("\n✅ Quick start completed successfully!")

if __name__ == "__main__":
    main()
