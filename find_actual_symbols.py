#!/usr/bin/env python3
"""
Find actual stock symbols in the Polygon.io data.
"""

import os
import pandas as pd
import gzip
from pathlib import Path
from collections import Counter
import yaml

def load_config():
    """Load configuration from multiple sources."""
    data_dir = os.getenv('POLYGON_DATA_DIR')
    
    if not data_dir:
        config_path = Path('stat_arb_project/config/production_config.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                data_dir = config.get('data', {}).get('polygon_data_dir')
    
    if not data_dir:
        data_dir = '/Users/lei/Documents/data/polygon'
    
    return data_dir

def find_stock_symbols(data_dir, num_files=50):
    """Find actual stock symbols in the data."""
    print(f"Searching for stock symbols in {data_dir}...")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data directory {data_dir} does not exist!")
        return {}
    
    csv_files = list(data_path.glob('*.csv.gz'))
    print(f"Found {len(csv_files)} data files")
    
    if len(csv_files) == 0:
        print("No CSV files found!")
        return {}
    
    # Check files systematically
    symbol_counts = Counter()
    files_checked = 0
    
    for file_path in csv_files[:num_files]:
        try:
            with gzip.open(file_path, 'rt') as f:
                df = pd.read_csv(f)
                if 'ticker' in df.columns:
                    # Get unique symbols from this file
                    symbols = df['ticker'].unique()
                    symbol_counts.update(symbols)
                    files_checked += 1
                    
                    # Print first few symbols from each file for debugging
                    if files_checked <= 5:
                        print(f"File {file_path.name}: {list(symbols[:10])}")
                        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    print(f"Checked {files_checked} files")
    return dict(symbol_counts.most_common(100))

def filter_stock_symbols(symbol_counts):
    """Filter for actual stock symbols (not numeric)."""
    stock_symbols = {}
    
    for symbol, count in symbol_counts.items():
        # Skip numeric symbols and very short symbols
        if (isinstance(symbol, str) and 
            len(symbol) >= 2 and 
            not symbol.isdigit() and
            not symbol.startswith('0') and
            symbol != 'nan'):
            stock_symbols[symbol] = count
    
    return stock_symbols

def main():
    """Main function."""
    print("=" * 60)
    print("STOCK SYMBOLS ANALYSIS")
    print("=" * 60)
    
    data_dir = load_config()
    print(f"Using data directory: {data_dir}")
    
    # Find all symbols
    all_symbols = find_stock_symbols(data_dir, num_files=100)
    
    if not all_symbols:
        print("No symbols found!")
        return
    
    # Filter for stock symbols
    stock_symbols = filter_stock_symbols(all_symbols)
    
    print(f"\nFound {len(stock_symbols)} stock symbols")
    
    if stock_symbols:
        print(f"\nTOP 30 STOCK SYMBOLS BY FREQUENCY:")
        print("-" * 40)
        
        top_symbols = sorted(stock_symbols.items(), key=lambda x: x[1], reverse=True)[:30]
        for i, (symbol, count) in enumerate(top_symbols, 1):
            print(f"{i:2d}. {symbol:>6} - {count:,} occurrences")
        
        # Suggest some popular pairs
        print(f"\nSUGGESTED POPULAR PAIRS:")
        print("-" * 40)
        
        # Get top symbols for pairing
        top_symbols_list = [s[0] for s in top_symbols[:20]]
        
        # Same-sector pairs
        tech_pairs = [('AAPL', 'MSFT'), ('GOOGL', 'META'), ('NVDA', 'AMD'), ('TSLA', 'NIO')]
        fin_pairs = [('JPM', 'BAC'), ('V', 'MA'), ('GS', 'MS')]
        health_pairs = [('JNJ', 'PFE'), ('UNH', 'ABBV')]
        
        all_suggested_pairs = tech_pairs + fin_pairs + health_pairs
        
        for symbol1, symbol2 in all_suggested_pairs:
            if symbol1 in stock_symbols and symbol2 in stock_symbols:
                count1 = stock_symbols[symbol1]
                count2 = stock_symbols[symbol2]
                print(f"• {symbol1} ({count1:,}) ↔ {symbol2} ({count2:,})")
    
    print(f"\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main() 