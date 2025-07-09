#!/usr/bin/env python3
"""
Check Available Symbols in Data Directory
"""
import sys
import os
from pathlib import Path
import pandas as pd
import gzip

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stat_arb_project.data.unified_data_loader import UnifiedDataLoader
from stat_arb_project.data.data_config import DataConfig, DataSource

def check_available_symbols():
    """Check what symbols are available in the data files."""
    print("="*60)
    print("CHECKING AVAILABLE SYMBOLS IN DATA FILES")
    print("="*60)
    
    data_dir = Path("/Users/lei/Documents/data/polygon")
    
    if not data_dir.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return
    
    print(f"✓ Data directory exists: {data_dir}")
    
    # Get all .csv.gz files
    gz_files = list(data_dir.glob("*.csv.gz"))
    print(f"✓ Found {len(gz_files)} .csv.gz files")
    
    if not gz_files:
        print("❌ No .csv.gz files found")
        return
    
    # Sample a few files to understand the structure
    print(f"\n📊 Analyzing file structure...")
    
    all_symbols = set()
    sample_files = gz_files[:5]  # Check first 5 files
    
    for file_path in sample_files:
        try:
            print(f"\n📁 Analyzing: {file_path.name}")
            
            # Read the first few lines to understand structure
            with gzip.open(file_path, 'rt') as f:
                lines = [next(f) for _ in range(5)]  # First 5 lines
            
            print(f"   First 5 lines:")
            for i, line in enumerate(lines, 1):
                print(f"   {i}: {line.strip()}")
            
            # Try to parse as CSV to get column names
            try:
                df_sample = pd.read_csv(file_path, compression='gzip', nrows=10)
                print(f"   Columns: {list(df_sample.columns)}")
                print(f"   Shape: {df_sample.shape}")
                
                # Check for symbol/ticker columns
                symbol_columns = [col for col in df_sample.columns if 'symbol' in col.lower() or 'ticker' in col.lower()]
                if symbol_columns:
                    print(f"   Symbol columns found: {symbol_columns}")
                    symbols_in_file = df_sample[symbol_columns[0]].unique()
                    print(f"   Symbols in this file: {symbols_in_file}")
                    all_symbols.update(symbols_in_file)
                
            except Exception as e:
                print(f"   Error parsing CSV: {e}")
                
        except Exception as e:
            print(f"   Error reading file: {e}")
    
    print(f"\n🎯 SUMMARY")
    print(f"="*40)
    print(f"Total unique symbols found: {len(all_symbols)}")
    if all_symbols:
        print(f"Available symbols: {sorted(list(all_symbols))}")
        
        # Suggest some pairs for testing
        symbols_list = sorted(list(all_symbols))
        if len(symbols_list) >= 2:
            print(f"\n💡 Suggested pairs for testing:")
            for i in range(0, min(len(symbols_list), 6), 2):
                if i + 1 < len(symbols_list):
                    print(f"   {symbols_list[i]} vs {symbols_list[i+1]}")
    else:
        print("❌ No symbols found in the analyzed files")
    
    # Check file naming pattern
    print(f"\n📋 File naming pattern analysis:")
    sample_names = [f.name for f in gz_files[:10]]
    for name in sample_names:
        print(f"   {name}")

if __name__ == "__main__":
    check_available_symbols() 