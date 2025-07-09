#!/usr/bin/env python3
"""
Test Single Symbol Data Loading
Tests the system with the available symbol 'A' data.
"""
import sys
import os
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stat_arb_project.data.unified_data_loader import UnifiedDataLoader
from stat_arb_project.data.data_config import DataConfig, DataSource

def test_single_symbol():
    """Test loading data for symbol 'A'."""
    print("="*60)
    print("TESTING SINGLE SYMBOL DATA LOADING")
    print("="*60)
    
    # Initialize data loader
    config = DataConfig(
        source=DataSource.POLYGON_OFFLINE,
        data_directory="/Users/lei/Documents/data/polygon",
        validate_quality=True
    )
    
    loader = UnifiedDataLoader(config)
    
    # Test with symbol 'A'
    symbol = "A"
    start_date = "2023-01-01"
    end_date = "2023-01-05"  # Just 5 days for testing
    
    print(f"Loading data for symbol: {symbol}")
    print(f"Date range: {start_date} to {end_date}")
    
    try:
        # Load data
        data = loader.load_data(
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            interval='1m',
            data_type='close'
        )
        
        if data.empty:
            print("❌ No data loaded for symbol 'A'")
            return
        
        print(f"✓ Successfully loaded {len(data)} observations")
        print(f"Data range: {data.index[0]} to {data.index[-1]}")
        print(f"Columns: {list(data.columns)}")
        
        # Show sample data
        print(f"\n📊 Sample data (first 5 rows):")
        print(data.head())
        
        # Show data statistics
        print(f"\n📈 Data Statistics:")
        print(f"Total observations: {len(data)}")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")
        print(f"Price range: ${data[symbol].min():.2f} - ${data[symbol].max():.2f}")
        print(f"Average price: ${data[symbol].mean():.2f}")
        print(f"Price volatility: {data[symbol].std():.2f}")
        
        # Check for data quality
        print(f"\n🔍 Data Quality Check:")
        print(f"Missing values: {data[symbol].isnull().sum()}")
        print(f"Zero prices: {(data[symbol] == 0).sum()}")
        print(f"Negative prices: {(data[symbol] < 0).sum()}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None

def demonstrate_data_capabilities():
    """Demonstrate what we can do with the available data."""
    print(f"\n" + "="*60)
    print("DEMONSTRATING DATA CAPABILITIES")
    print("="*60)
    
    data = test_single_symbol()
    if data is None:
        return
    
    symbol = "A"
    
    # Calculate some basic metrics
    print(f"\n📊 Basic Analysis for {symbol}:")
    
    # Daily returns
    daily_data = data.resample('D').last()
    daily_returns = daily_data[symbol].pct_change().dropna()
    
    print(f"Daily returns - Mean: {daily_returns.mean():.4f}")
    print(f"Daily returns - Std: {daily_returns.std():.4f}")
    print(f"Daily returns - Sharpe: {daily_returns.mean() / daily_returns.std():.2f}")
    
    # Price movement analysis
    price_changes = data[symbol].diff().dropna()
    print(f"Price changes - Mean: ${price_changes.mean():.2f}")
    print(f"Price changes - Std: ${price_changes.std():.2f}")
    
    # Volatility analysis
    rolling_vol = data[symbol].rolling(window=20).std()
    print(f"20-period rolling volatility - Mean: {rolling_vol.mean():.2f}")
    
    print(f"\n✅ System is working correctly with available data!")
    print(f"💡 To run pair trading, you would need data for at least 2 different symbols.")

if __name__ == "__main__":
    demonstrate_data_capabilities() 