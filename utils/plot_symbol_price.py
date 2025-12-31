#!/usr/bin/env python3
"""
Utility script to plot price movement for a symbol over a period of time.
Uses Polygon REST API via core_engine.
"""

import asyncio
import argparse
import os
import sys
import yaml
from datetime import datetime, time
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from dotenv import load_dotenv

# Add project root to sys.path to allow imports from core_engine
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core_engine.data.feeds.polygon_rest import PolygonRestService

async def plot_symbol_price(symbol: str, start_date: str, end_date: str, timeframe: str = "1min", output_dir: str = ".", market_only: bool = False, plot_type: str = "line"):
    """
    Fetches price data and plots it.
    """
    # Load environment variables from .env if it exists
    load_dotenv()
    
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("Error: POLYGON_API_KEY environment variable not set.")
        return

    service = PolygonRestService(api_key=api_key)
    
    try:
        initialized = await service.initialize()
        if not initialized:
            print("Error: Failed to initialize PolygonRestService. Check your API key.")
            return

        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        # Set end_dt to the end of the day to ensure the range is inclusive
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        
        print(f"Fetching {timeframe} bars for {symbol} from {start_dt} to {end_dt}...")
        
        df = await service.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start_dt,
            end=end_dt
        )
        
        if df.empty:
            print(f"No data found for {symbol} in the specified range.")
            return

        print(f"Successfully fetched {len(df)} bars.")
        
        # Convert index to New York time for filtering and plotting
        df.index = df.index.tz_convert("America/New_York")
        
        # Filter for market hours if requested (9:30 AM - 4:00 PM ET)
        if market_only:
            print("Filtering for market hours (09:30 - 16:00 ET)...")
            
            # Create mask for market hours
            market_open = time(9, 30)
            market_close = time(16, 0)
            
            mask = []
            for t in df.index:
                is_weekday = t.weekday() < 5
                is_during_hours = market_open <= t.time() <= market_close
                mask.append(is_weekday and is_during_hours)
            
            df = df[mask]
            print(f"Data points after filtering: {len(df)}")
            
            if df.empty:
                print("No data points remain after market hours filtering.")
                return

        # Plotting
        plt.figure(figsize=(12, 6))
        
        if plot_type == "candle":
            print("Plotting candlesticks...")
            # Define colors
            up_color = 'green'
            down_color = 'red'
            
            # Calculate width of the bars based on timeframe
            # Default to a reasonable width if we can't determine it
            width = 0.0005 # Default for 1min
            if timeframe == "1min": width = 0.0005
            elif timeframe == "5min": width = 0.0025
            elif timeframe == "1h": width = 0.03
            elif timeframe == "1d": width = 0.6
            elif "s" in timeframe: width = 0.000008
            
            # Plot up bars
            up = df[df.close >= df.open]
            plt.bar(up.index, up.close - up.open, width, bottom=up.open, color=up_color, edgecolor=up_color)
            plt.vlines(up.index, up.low, up.high, color=up_color, linewidth=1)
            
            # Plot down bars
            down = df[df.close < df.open]
            plt.bar(down.index, down.open - down.close, width, bottom=down.close, color=down_color, edgecolor=down_color)
            plt.vlines(down.index, down.low, down.high, color=down_color, linewidth=1)
            
            plt.title(f"{symbol} Candlestick Chart ({timeframe}) | {start_date} to {end_date}", fontsize=14)
        else:
            plt.plot(df.index, df['close'], label='Close Price', color='blue', linewidth=1.5)
            plt.title(f"{symbol} Price Movement ({timeframe}) | {start_date} to {end_date}", fontsize=14)
        
        # Add labels and title
        plt.xlabel("Time (ET)", fontsize=12)
        plt.ylabel("Price (USD)", fontsize=12)
        
        # Format x-axis
        ax = plt.gca()
        
        # Use the actual range of the data for formatting decisions
        data_range_days = (df.index.max() - df.index.min()).days
        
        if data_range_days < 1:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=ZoneInfo("America/New_York")))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=[0, 30]))
        elif data_range_days <= 7:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M', tz=ZoneInfo("America/New_York")))
            ax.xaxis.set_major_locator(mdates.DayLocator())
            ax.xaxis.set_minor_locator(mdates.HourLocator(interval=4))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d', tz=ZoneInfo("America/New_York")))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())

        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save the plot
        if output_dir != "." and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_file = os.path.join(output_dir, f"{symbol}_{start_date}_{end_date}.png")
        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")
        
        # Show the plot if in an interactive environment
        # plt.show()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await service.close()

def main():
    parser = argparse.ArgumentParser(description="Plot price movement for a symbol using Polygon REST API.")
    parser.add_argument("--symbol", type=str, help="Stock symbol (e.g., TSLA)")
    parser.add_argument("--start_date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--timeframe", type=str, default="1min", help="Timeframe (e.g., 1min, 5min, 1h, 1d). Default: 1min")
    parser.add_argument("--config", type=str, help="Path to a YAML config file")
    parser.add_argument("--output_dir", type=str, default=".", help="Directory to save the plot. Default: current directory")
    parser.add_argument("--market_only", action="store_true", help="Only plot market hours (09:30-16:00 ET)")
    parser.add_argument("--plot_type", type=str, choices=["line", "candle"], default="line", help="Type of plot: 'line' or 'candle'. Default: 'line'")

    args = parser.parse_args()

    symbol = args.symbol
    start_date = args.start_date
    end_date = args.end_date
    timeframe = args.timeframe
    output_dir = args.output_dir
    market_only = args.market_only
    plot_type = args.plot_type

    # Load from config if provided
    if args.config:
        if os.path.exists(args.config):
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
                symbol = config.get('symbol', symbol)
                start_date = config.get('start_date', start_date)
                end_date = config.get('end_date', end_date)
                timeframe = config.get('timeframe', timeframe)
                output_dir = config.get('output_dir', output_dir)
                market_only = config.get('market_only', market_only)
                plot_type = config.get('plot_type', plot_type)
        else:
            print(f"Error: Config file {args.config} not found.")
            return

    # Validate required parameters
    if not all([symbol, start_date, end_date]):
        print("Error: symbol, start_date, and end_date are required (either via arguments or config file).")
        parser.print_help()
        return

    asyncio.run(plot_symbol_price(symbol, start_date, end_date, timeframe, output_dir, market_only, plot_type))

if __name__ == "__main__":
    main()
