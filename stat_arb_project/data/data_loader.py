"""
Handles loading and preprocessing of price data, now optimized for intraday.
"""
import pandas as pd
import yfinance as yf
from typing import List

def load_intraday_data(tickers: List[str], duration_days: int, interval: str) -> pd.DataFrame:
    """
    Loads historical intraday price data from Yahoo Finance and cleans it.
    """
    print(f"Loading {interval} intraday data for tickers: {tickers} over the last {duration_days} days.")
    
    try:
        period = f"{duration_days}d"
        data = yf.download(tickers, period=period, interval=interval, progress=False, auto_adjust=True)['Close']
        
        if data.empty:
            print("\n" + "="*80)
            print("ERROR: No data downloaded from yfinance.")
            print(f"This could be due to several reasons:")
            print(f"  1. Invalid tickers: {tickers}")
            print(f"  2. The requested interval ('{interval}') is not available for the requested duration ('{period}').")
            print("  3. yfinance API is temporarily unavailable or has changed.")
            print("  - For 1m interval, max history is 7 days.")
            print("  - For intervals < 1h, max history is typically 60 days.")
            print("="*80 + "\n")
            return pd.DataFrame()

        if len(tickers) == 1:
            data = data.to_frame(name=tickers[0])
        
        data.dropna(axis=1, how='all', inplace=True)
        if data.shape[1] < 2 and len(tickers) > 1:
            print("Error: Not enough valid data for at least two tickers. Cannot form a pair.")
            return pd.DataFrame()
        
        data.fillna(method='ffill', inplace=True)
        data.fillna(method='bfill', inplace=True)
        data.dropna(inplace=True)

        print(f"Successfully loaded {data.shape[0]} bars of data.")
        return data

    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return pd.DataFrame() 