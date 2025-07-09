#!/usr/bin/env python3
"""
Find popular symbol pairs for statistical arbitrage from Polygon.io data.
"""

import os
import pandas as pd
import numpy as np
from collections import Counter
import gzip
from pathlib import Path
import yaml

def load_config():
    """Load configuration from multiple sources."""
    # Try environment variable first
    data_dir = os.getenv('POLYGON_DATA_DIR')
    
    if not data_dir:
        # Try config file
        config_path = Path('stat_arb_project/config/production_config.yaml')
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                data_dir = config.get('data', {}).get('polygon_data_dir')
    
    if not data_dir:
        # Default fallback
        data_dir = '/Users/lei/Documents/data/polygon'
    
    return data_dir

def analyze_symbol_frequency(data_dir, sample_size=50):
    """Analyze symbol frequency across data files."""
    print(f"Analyzing symbol frequency in {data_dir}...")
    
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"Data directory {data_dir} does not exist!")
        return {}
    
    # Get all CSV files
    csv_files = list(data_path.glob('*.csv.gz'))
    print(f"Found {len(csv_files)} data files")
    
    if len(csv_files) == 0:
        print("No CSV files found!")
        return {}
    
    # Sample files for analysis (to avoid processing all files)
    sample_files = np.random.choice(np.array(csv_files), min(sample_size, len(csv_files)), replace=False)
    
    symbol_counts = Counter()
    total_records = 0
    
    for file_path in sample_files:
        try:
            with gzip.open(file_path, 'rt') as f:
                df = pd.read_csv(f)
                if 'ticker' in df.columns:
                    symbol_counts.update(df['ticker'].value_counts())
                    total_records += len(df)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
    
    print(f"Analyzed {len(sample_files)} files with {total_records:,} total records")
    return dict(symbol_counts.most_common(100))

def find_popular_pairs(symbol_counts, min_count=100):
    """Find popular symbol pairs based on trading frequency."""
    print(f"\nFinding symbols with at least {min_count} occurrences...")
    
    # Filter symbols by minimum count
    popular_symbols = {symbol: count for symbol, count in symbol_counts.items() 
                      if count >= min_count}
    
    print(f"Found {len(popular_symbols)} symbols meeting criteria")
    
    # Group by sector/industry (simple heuristic based on symbol patterns)
    sectors = {
        'Technology': ['AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC', 'CRM'],
        'Financial': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'V', 'MA'],
        'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'DHR', 'BMY', 'AMGN'],
        'Consumer': ['AMZN', 'HD', 'MCD', 'NKE', 'SBUX', 'COST', 'WMT', 'TGT', 'LOW', 'TJX'],
        'Energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'OXY', 'HAL'],
        'Industrial': ['BA', 'CAT', 'MMM', 'GE', 'HON', 'UPS', 'FDX', 'RTX', 'LMT', 'NOC']
    }
    
    # Find symbols in each sector
    sector_symbols = {}
    for sector, symbols in sectors.items():
        sector_symbols[sector] = [s for s in symbols if s in popular_symbols]
    
    return popular_symbols, sector_symbols

def suggest_pairs(sector_symbols, popular_symbols):
    """Suggest specific pairs for trading."""
    print("\n=== POPULAR SYMBOL PAIRS FOR STATISTICAL ARBITRAGE ===\n")
    
    # High-frequency pairs (same sector)
    print("🔹 HIGH-FREQUENCY PAIRS (Same Sector):")
    print("   These pairs are likely to have strong correlations:")
    
    for sector, symbols in sector_symbols.items():
        if len(symbols) >= 2:
            print(f"\n   {sector}:")
            # Take top symbols from each sector
            top_symbols = symbols[:min(6, len(symbols))]
            for i in range(0, len(top_symbols), 2):
                if i + 1 < len(top_symbols):
                    symbol1, symbol2 = top_symbols[i], top_symbols[i+1]
                    count1 = popular_symbols.get(symbol1, 0)
                    count2 = popular_symbols.get(symbol2, 0)
                    print(f"     • {symbol1} ({count1:,} trades) ↔ {symbol2} ({count2:,} trades)")
    
    # Cross-sector pairs (popular combinations)
    print(f"\n🔹 CROSS-SECTOR PAIRS:")
    print("   These pairs may offer diversification benefits:")
    
    cross_pairs = [
        ('AAPL', 'MSFT'),  # Tech giants
        ('JPM', 'BAC'),    # Banking
        ('XOM', 'CVX'),    # Energy
        ('JNJ', 'PFE'),    # Healthcare
        ('AMZN', 'WMT'),   # Retail
        ('BA', 'CAT'),     # Industrial
        ('V', 'MA'),       # Payment processors
        ('GOOGL', 'META'), # Tech advertising
        ('NVDA', 'AMD'),   # Semiconductor
        ('HD', 'LOW'),     # Home improvement
    ]
    
    for symbol1, symbol2 in cross_pairs:
        if symbol1 in popular_symbols and symbol2 in popular_symbols:
            count1 = popular_symbols[symbol1]
            count2 = popular_symbols[symbol2]
            print(f"     • {symbol1} ({count1:,} trades) ↔ {symbol2} ({count2:,} trades)")
    
    # Top 20 most traded symbols
    print(f"\n🔹 TOP 20 MOST TRADED SYMBOLS:")
    print("   (Use these for pair selection)")
    
    top_symbols = sorted(popular_symbols.items(), key=lambda x: x[1], reverse=True)[:20]
    for i, (symbol, count) in enumerate(top_symbols, 1):
        print(f"   {i:2d}. {symbol:>6} - {count:,} trades")

def main():
    """Main analysis function."""
    print("=" * 60)
    print("POPULAR SYMBOL PAIRS ANALYSIS")
    print("=" * 60)
    
    # Load configuration
    data_dir = load_config()
    print(f"Using data directory: {data_dir}")
    
    # Analyze symbol frequency
    symbol_counts = analyze_symbol_frequency(data_dir, sample_size=200)
    
    if not symbol_counts:
        print("No data found or analysis failed!")
        return
    
    # Find popular symbols and sector groupings
    popular_symbols, sector_symbols = find_popular_pairs(symbol_counts, min_count=50)
    
    # Suggest pairs
    suggest_pairs(sector_symbols, popular_symbols)
    
    print(f"\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\n💡 TIPS:")
    print("   • Start with high-frequency pairs for better liquidity")
    print("   • Same-sector pairs often have stronger correlations")
    print("   • Cross-sector pairs may offer better diversification")
    print("   • Consider market cap and volatility when selecting pairs")
    print(f"\n📊 Total symbols analyzed: {len(symbol_counts)}")
    print(f"📊 Popular symbols (50+ trades): {len(popular_symbols)}")

if __name__ == "__main__":
    main() 