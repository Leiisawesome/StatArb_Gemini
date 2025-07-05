"""
Demonstration script for the Statistical Arbitrage Trading System.
This script shows the basic functionality without running the full backtest.
"""
import pandas as pd
import numpy as np
from config import CONFIG_DICT
from structs import Config
from data import data_loader
from strategy import pair_selection
from utils import helpers

def demo_basic_functionality():
    """Demonstrates basic functionality of the system."""
    print("=" * 80)
    print("STATISTICAL ARBITRAGE TRADING SYSTEM - DEMONSTRATION")
    print("=" * 80)
    
    # Load configuration
    config = Config(**CONFIG_DICT)
    print(f"\n1. Configuration loaded:")
    print(f"   - Tickers: {config.tickers}")
    print(f"   - Data interval: {config.data_interval}")
    print(f"   - Training window: {config.training_window_bars} bars")
    print(f"   - Entry threshold: Z-score > {config.entry_z}")
    print(f"   - Exit threshold: Z-score < {config.exit_z}")
    
    # Load sample data (shorter period for demo)
    print(f"\n2. Loading sample data...")
    demo_config = CONFIG_DICT.copy()
    demo_config['history_duration_days'] = 7  # Shorter period for demo
    demo_config['training_window_bars'] = 100  # Smaller training window
    
    try:
        data = data_loader.load_intraday_data(
            tickers=config.tickers,
            duration_days=demo_config['history_duration_days'],
            interval=config.data_interval
        )
        
        if not data.empty:
            print(f"   ✓ Data loaded successfully!")
            print(f"   - Data shape: {data.shape}")
            print(f"   - Date range: {data.index[0]} to {data.index[-1]}")
            print(f"   - Columns: {list(data.columns)}")
            
            # Show sample data
            print(f"\n3. Sample data (first 5 rows):")
            print(data.head())
            
            # Check for cointegration
            print(f"\n4. Checking cointegration...")
            if len(config.tickers) >= 2:
                is_coint = pair_selection.is_cointegrated(data[config.tickers[0]], data[config.tickers[1]])
                print(f"   - {config.tickers[0]} and {config.tickers[1]} are cointegrated: {is_coint}")
            
            print(f"\n5. System ready for backtesting!")
            print(f"   - Run 'python main.py' to execute full backtest")
            print(f"   - Run 'streamlit run dashboard/live_dashboard.py' for interactive dashboard")
            print(f"   - Run 'pytest' to run unit tests")
            
        else:
            print("   ✗ Failed to load data. Check internet connection and ticker symbols.")
            
    except Exception as e:
        print(f"   ✗ Error loading data: {e}")
        print("   This might be due to:")
        print("   - Internet connection issues")
        print("   - yfinance API changes")
        print("   - Invalid ticker symbols")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    demo_basic_functionality() 