#!/usr/bin/env python3
"""
Test script to verify data loading from external directory
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stat_arb_project.data.unified_data_loader import UnifiedDataLoader
from stat_arb_project.data.data_config import DataConfig, DataSource

def test_data_loading():
    """Test loading data from the external directory."""
    print("="*60)
    print("TESTING DATA LOADING FROM EXTERNAL DIRECTORY")
    print("="*60)
    
    # Test 1: Using default configuration
    print("\n1. Testing with default configuration...")
    try:
        from stat_arb_project.data.unified_data_loader import load_intraday_data
        
        data = load_intraday_data(
            tickers=['AAPL', 'MSFT'],
            duration_days=5,  # Just 5 days for testing
            interval='1m',
            data_source='polygon_offline'
        )
        
        if not data.empty:
            print(f"✓ Successfully loaded {len(data)} data points")
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")
            print(f"  Columns: {list(data.columns)}")
        else:
            print("✗ No data loaded")
            
    except Exception as e:
        print(f"✗ Error loading data: {e}")
    
    # Test 2: Using custom configuration
    print("\n2. Testing with custom configuration...")
    try:
        config = DataConfig(
            source=DataSource.POLYGON_OFFLINE,
            data_directory="/Users/lei/Documents/data/polygon",
            validate_quality=True
        )
        
        print(f"  Config data directory: {config.data_directory}")
        
        loader = UnifiedDataLoader(config)
        
        # Check available symbols
        symbols = loader.get_available_symbols()
        print(f"✓ Available symbols: {symbols}")
        
        # Load data
        data = loader.load_data(
            symbols=['AAPL', 'MSFT'],
            start_date='2023-01-01',
            end_date='2023-01-05',
            interval='1m',
            data_type='close'
        )
        
        if not data.empty:
            print(f"✓ Successfully loaded {len(data)} data points")
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")
        else:
            print("✗ No data loaded")
            
    except Exception as e:
        print(f"✗ Error with custom config: {e}")
    
    # Test 2.5: Using environment-based configuration
    print("\n2.5. Testing with environment-based configuration...")
    try:
        config = DataConfig.from_env()
        print(f"  Environment-based config data directory: {config.data_directory}")
        
        loader = UnifiedDataLoader(config)
        
        # Check available symbols
        symbols = loader.get_available_symbols()
        print(f"✓ Available symbols: {symbols}")
        
        # Load data
        data = loader.load_data(
            symbols=['AAPL', 'MSFT'],
            start_date='2023-01-01',
            end_date='2023-01-05',
            interval='1m',
            data_type='close'
        )
        
        if not data.empty:
            print(f"✓ Successfully loaded {len(data)} data points")
            print(f"  Date range: {data.index[0]} to {data.index[-1]}")
        else:
            print("✗ No data loaded")
            
    except Exception as e:
        print(f"✗ Error with environment config: {e}")
    
    # Test 3: Check directory structure
    print("\n3. Checking directory structure...")
    data_dir = Path("/Users/lei/Documents/data/polygon")
    
    if data_dir.exists():
        print(f"✓ Data directory exists: {data_dir}")
        
        # Count files
        csv_files = list(data_dir.glob("*.csv"))
        gz_files = list(data_dir.glob("*.csv.gz"))
        
        print(f"  CSV files: {len(csv_files)}")
        print(f"  GZ files: {len(gz_files)}")
        
        if csv_files or gz_files:
            print("  Sample files:")
            for file in (csv_files + gz_files)[:5]:  # Show first 5 files
                print(f"    - {file.name}")
        else:
            print("  ⚠️  No data files found in directory")
    else:
        print(f"✗ Data directory does not exist: {data_dir}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)

if __name__ == "__main__":
    test_data_loading() 