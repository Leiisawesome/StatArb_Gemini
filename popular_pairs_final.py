#!/usr/bin/env python3
"""
Popular Symbol Pairs for Statistical Arbitrage
Based on actual symbols found in the Polygon.io data.
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

def get_available_symbols(data_dir, num_files=50):
    """Get available symbols from the data."""
    data_path = Path(data_dir)
    csv_files = list(data_path.glob('*.csv.gz'))
    
    symbol_counts = Counter()
    
    for file_path in csv_files[:num_files]:
        try:
            with gzip.open(file_path, 'rt') as f:
                df = pd.read_csv(f)
                if 'ticker' in df.columns:
                    symbols = df['ticker'].unique()
                    symbol_counts.update(symbols)
        except Exception as e:
            continue
    
    # Filter for stock symbols
    stock_symbols = {}
    for symbol, count in symbol_counts.items():
        if (isinstance(symbol, str) and 
            len(symbol) >= 2 and 
            not symbol.isdigit() and
            symbol != 'nan'):
            stock_symbols[symbol] = count
    
    return stock_symbols

def main():
    """Main function to display popular symbol pairs."""
    print("=" * 70)
    print("POPULAR SYMBOL PAIRS FOR STATISTICAL ARBITRAGE")
    print("=" * 70)
    
    data_dir = load_config()
    print(f"Data source: {data_dir}")
    
    # Get available symbols
    available_symbols = get_available_symbols(data_dir, num_files=100)
    
    if not available_symbols:
        print("No symbols found in data!")
        return
    
    print(f"\n📊 Found {len(available_symbols)} unique stock symbols")
    
    # Define popular pairs by sector
    popular_pairs = {
        "Technology": [
            ("AAPL", "MSFT"),    # Apple vs Microsoft
            ("GOOGL", "META"),   # Google vs Meta
            ("NVDA", "AMD"),     # NVIDIA vs AMD
            ("TSLA", "NIO"),     # Tesla vs NIO
            ("CRM", "ORCL"),     # Salesforce vs Oracle
            ("ADBE", "INTU"),    # Adobe vs Intuit
        ],
        "Financial": [
            ("JPM", "BAC"),      # JPMorgan vs Bank of America
            ("V", "MA"),         # Visa vs Mastercard
            ("GS", "MS"),        # Goldman vs Morgan Stanley
            ("WFC", "C"),        # Wells Fargo vs Citigroup
            ("BLK", "AXP"),      # BlackRock vs American Express
        ],
        "Healthcare": [
            ("JNJ", "PFE"),      # Johnson & Johnson vs Pfizer
            ("UNH", "ABBV"),     # UnitedHealth vs AbbVie
            ("MRK", "ABT"),      # Merck vs Abbott
            ("TMO", "DHR"),      # Thermo Fisher vs Danaher
            ("BMY", "AMGN"),     # Bristol-Myers vs Amgen
        ],
        "Consumer": [
            ("AMZN", "WMT"),     # Amazon vs Walmart
            ("HD", "LOW"),       # Home Depot vs Lowe's
            ("MCD", "SBUX"),     # McDonald's vs Starbucks
            ("NKE", "UA"),       # Nike vs Under Armour
            ("COST", "TGT"),     # Costco vs Target
        ],
        "Energy": [
            ("XOM", "CVX"),      # Exxon vs Chevron
            ("COP", "EOG"),      # ConocoPhillips vs EOG
            ("SLB", "HAL"),      # Schlumberger vs Halliburton
            ("PSX", "VLO"),      # Phillips 66 vs Valero
        ],
        "Industrial": [
            ("BA", "CAT"),       # Boeing vs Caterpillar
            ("MMM", "GE"),       # 3M vs General Electric
            ("UPS", "FDX"),      # UPS vs FedEx
            ("RTX", "LMT"),      # Raytheon vs Lockheed Martin
        ]
    }
    
    # Check which pairs are available
    available_pairs = {}
    for sector, pairs in popular_pairs.items():
        available_pairs[sector] = []
        for symbol1, symbol2 in pairs:
            if symbol1 in available_symbols and symbol2 in available_symbols:
                count1 = available_symbols[symbol1]
                count2 = available_symbols[symbol2]
                available_pairs[sector].append((symbol1, symbol2, count1, count2))
    
    # Display available pairs by sector
    print(f"\n🔹 AVAILABLE POPULAR PAIRS BY SECTOR:")
    print("=" * 50)
    
    for sector, pairs in available_pairs.items():
        if pairs:
            print(f"\n📈 {sector.upper()}:")
            for symbol1, symbol2, count1, count2 in pairs:
                print(f"   • {symbol1} ({count1:,}) ↔ {symbol2} ({count2:,})")
    
    # Show top 20 most frequent symbols
    print(f"\n🔹 TOP 20 MOST FREQUENT SYMBOLS:")
    print("=" * 40)
    
    top_symbols = sorted(available_symbols.items(), key=lambda x: x[1], reverse=True)[:20]
    for i, (symbol, count) in enumerate(top_symbols, 1):
        print(f"   {i:2d}. {symbol:>6} - {count:,} occurrences")
    
    # Suggest some high-frequency pairs
    print(f"\n🔹 HIGH-FREQUENCY PAIRS (Top Symbols):")
    print("=" * 40)
    
    top_symbols_list = [s[0] for s in top_symbols[:10]]
    for i in range(0, len(top_symbols_list), 2):
        if i + 1 < len(top_symbols_list):
            symbol1, symbol2 = top_symbols_list[i], top_symbols_list[i+1]
            count1 = available_symbols[symbol1]
            count2 = available_symbols[symbol2]
            print(f"   • {symbol1} ({count1:,}) ↔ {symbol2} ({count2:,})")
    
    # Trading recommendations
    print(f"\n" + "=" * 70)
    print("TRADING RECOMMENDATIONS")
    print("=" * 70)
    
    print(f"\n💡 START WITH THESE PAIRS:")
    print("   1. AAPL ↔ MSFT (Technology - High liquidity)")
    print("   2. JPM ↔ BAC (Financial - Strong correlation)")
    print("   3. V ↔ MA (Payment processors - Similar business)")
    print("   4. JNJ ↔ PFE (Healthcare - Stable correlation)")
    print("   5. XOM ↔ CVX (Energy - Sector correlation)")
    
    print(f"\n📊 DATA INSIGHTS:")
    print(f"   • Total symbols available: {len(available_symbols)}")
    print(f"   • Files analyzed: 100")
    print(f"   • Time period: 2023-2024")
    print(f"   • Data source: Polygon.io")
    
    print(f"\n⚡ NEXT STEPS:")
    print("   1. Choose a pair from the recommendations above")
    print("   2. Run cointegration analysis on the selected pair")
    print("   3. Backtest the strategy with historical data")
    print("   4. Monitor correlation stability over time")
    
    print(f"\n" + "=" * 70)

if __name__ == "__main__":
    main() 