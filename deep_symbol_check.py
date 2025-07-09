#!/usr/bin/env python3
"""
Deep Symbol Check - Investigate why only one symbol is found
"""
import sys
import os
from pathlib import Path
import pandas as pd
import gzip
import random

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def deep_symbol_check():
    """Perform a deep check for symbols across multiple files."""
    print("="*80)
    print("DEEP SYMBOL CHECK - INVESTIGATING DATA CONTENT")
    print("="*80)
    
    data_dir = Path("/Users/lei/Documents/data/polygon")
    
    if not data_dir.exists():
        print(f"❌ Data directory does not exist: {data_dir}")
        return
    
    # Get all .csv.gz files
    gz_files = list(data_dir.glob("*.csv.gz"))
    print(f"✓ Found {len(gz_files)} .csv.gz files")
    
    if not gz_files:
        print("❌ No .csv.gz files found")
        return
    
    # Check multiple files randomly to see if there are other symbols
    print(f"\n🔍 Checking multiple files for symbols...")
    
    all_symbols = set()
    checked_files = 0
    max_files_to_check = 20  # Check up to 20 files
    
    # Sample files from different time periods
    sample_files = []
    
    # Check files from different years
    for year in [2023, 2024, 2025]:
        year_files = [f for f in gz_files if str(year) in f.name]
        if year_files:
            sample_files.extend(random.sample(year_files, min(3, len(year_files))))
    
    # Add some random files
    remaining_files = [f for f in gz_files if f not in sample_files]
    if remaining_files:
        sample_files.extend(random.sample(remaining_files, min(5, len(remaining_files))))
    
    print(f"Checking {len(sample_files)} sample files from different time periods...")
    
    for file_path in sample_files:
        try:
            checked_files += 1
            print(f"\n📁 File {checked_files}: {file_path.name}")
            
            # Read the entire file to get all symbols
            df = pd.read_csv(file_path, compression='gzip')
            
            if 'ticker' in df.columns:
                symbols_in_file = df['ticker'].unique()
                all_symbols.update(symbols_in_file)
                print(f"   Symbols found: {symbols_in_file}")
                print(f"   Total rows: {len(df)}")
                
                # Show symbol distribution
                symbol_counts = df['ticker'].value_counts()
                print(f"   Symbol distribution:")
                for symbol, count in symbol_counts.items():
                    print(f"     {symbol}: {count} rows")
            else:
                print(f"   No 'ticker' column found. Columns: {list(df.columns)}")
                
        except Exception as e:
            print(f"   Error reading file: {e}")
    
    print(f"\n" + "="*80)
    print("DEEP CHECK RESULTS")
    print("="*80)
    print(f"Files checked: {checked_files}")
    print(f"Total unique symbols found: {len(all_symbols)}")
    print(f"All symbols: {sorted(list(all_symbols))}")
    
    # Analyze the findings
    if len(all_symbols) == 1:
        print(f"\n🔍 ANALYSIS: Only one symbol found")
        print(f"This could be due to:")
        print(f"1. Data subscription limited to one symbol")
        print(f"2. Data download was for specific symbol only")
        print(f"3. Data format is single-symbol focused")
        print(f"4. Other symbols are in different files/format")
        
        # Check if there are other file types
        print(f"\n🔍 Checking for other file types...")
        all_files = list(data_dir.glob("*"))
        file_types = {}
        for file in all_files:
            ext = file.suffix
            file_types[ext] = file_types.get(ext, 0) + 1
        
        print(f"File types found:")
        for ext, count in file_types.items():
            print(f"  {ext}: {count} files")
            
    elif len(all_symbols) > 1:
        print(f"\n✅ Multiple symbols found!")
        print(f"Available symbols for pair trading: {sorted(list(all_symbols))}")
        
        # Suggest pairs
        symbols_list = sorted(list(all_symbols))
        if len(symbols_list) >= 2:
            print(f"\n💡 Suggested pairs for testing:")
            for i in range(0, len(symbols_list), 2):
                if i + 1 < len(symbols_list):
                    print(f"   {symbols_list[i]} vs {symbols_list[i+1]}")
    
    # Check file sizes to understand data volume
    print(f"\n📊 File size analysis:")
    total_size = 0
    for file in gz_files[:10]:  # Check first 10 files
        size_mb = file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  {file.name}: {size_mb:.2f} MB")
    
    avg_size = total_size / min(10, len(gz_files))
    print(f"Average file size: {avg_size:.2f} MB")
    print(f"Total data volume: {len(gz_files) * avg_size:.2f} MB")

def check_data_source_info():
    """Check if there are any clues about the data source."""
    print(f"\n" + "="*80)
    print("DATA SOURCE INVESTIGATION")
    print("="*80)
    
    data_dir = Path("/Users/lei/Documents/data/polygon")
    
    # Look for any metadata files
    metadata_files = list(data_dir.glob("*.txt")) + list(data_dir.glob("*.md")) + list(data_dir.glob("*.json"))
    
    if metadata_files:
        print(f"Found metadata files:")
        for file in metadata_files:
            print(f"  {file.name}")
            try:
                with open(file, 'r') as f:
                    content = f.read()[:500]  # First 500 chars
                    print(f"    Content preview: {content[:100]}...")
            except Exception as e:
                print(f"    Error reading: {e}")
    else:
        print(f"No metadata files found")
    
    # Check file naming patterns
    print(f"\n📋 File naming pattern analysis:")
    gz_files = list(data_dir.glob("*.csv.gz"))
    
    # Group by year
    years = {}
    for file in gz_files:
        year = file.name[:4]  # First 4 chars should be year
        if year.isdigit():
            years[year] = years.get(year, 0) + 1
    
    print(f"Files by year:")
    for year, count in sorted(years.items()):
        print(f"  {year}: {count} files")
    
    # Check if files are from different months
    months = {}
    for file in gz_files:
        if len(file.name) >= 7:
            month = file.name[5:7]  # Month part
            if month.isdigit():
                months[month] = months.get(month, 0) + 1
    
    print(f"Files by month (sample):")
    for month, count in sorted(months.items())[:6]:
        print(f"  Month {month}: {count} files")

if __name__ == "__main__":
    deep_symbol_check()
    check_data_source_info() 