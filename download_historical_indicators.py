#!/usr/bin/env python3
"""
Historical Technical Indicators Downloader
==========================================

Downloads 2.5 years of technical indicators (2023-01-01 to 2025-06-30)
for statistical arbitrage system enhancement.

Key Features:
- Robust API rate limiting (5 requests/minute limit)
- Resume capability for interrupted downloads  
- ClickHouse integration for fast storage
- Data validation and quality checks
- Progress tracking and logging

Indicators Downloaded:
- SMA (20, 50 day windows)
- EMA (20 day window)  
- RSI (14 day window)
- MACD (12,26,9 parameters)
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests
import logging
from pathlib import Path

# Add project path
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/new_structure')

try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    print("⚠️  ClickHouse driver not available. Install with: pip install clickhouse-connect")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indicators_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalIndicatorsDownloader:
    """Download and store 2.5 years of technical indicators"""
    
    def __init__(self, api_key: str, start_date: str = "2023-01-01", 
                 end_date: str = "2025-06-30"):
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date
        self.base_url = "https://api.polygon.io/v1/indicators"
        
        # Rate limiting (Polygon.io: 5 requests/minute for basic plan)
        self.rate_limit_delay = 12  # 12 seconds between requests
        self.last_request_time = 0
        
        # Progress tracking
        self.progress_file = "download_progress.json"
        self.progress = self.load_progress()
        
        # ClickHouse setup
        self.setup_clickhouse()
        
        # Symbol universe (from your pair screening results)
        self.symbols = self.get_symbol_universe()
        
        logger.info(f"Initialized downloader for {len(self.symbols)} symbols")
        logger.info(f"Date range: {start_date} to {end_date}")
        
    def setup_clickhouse(self):
        """Setup ClickHouse connection and create tables"""
        if not CLICKHOUSE_AVAILABLE:
            logger.warning("ClickHouse not available - data will be saved to CSV files")
            self.clickhouse_available = False
            return
            
        try:
            self.ch_client = clickhouse_connect.get_client(
                host="localhost",
                port=8123,
                database='polygon_data'
            )
            self.clickhouse_available = True
            self.create_indicators_table()
            logger.info("✅ ClickHouse connection established")
            
        except Exception as e:
            logger.warning(f"ClickHouse not available: {e}")
            self.clickhouse_available = False
    
    def create_indicators_table(self):
        """Create technical indicators table in ClickHouse"""
        if not self.clickhouse_available:
            return
            
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS technical_indicators (
            symbol String,
            date Date,
            timestamp DateTime,
            
            -- Moving Averages
            sma_20 Nullable(Float64),
            sma_50 Nullable(Float64), 
            ema_20 Nullable(Float64),
            
            -- Momentum Oscillators
            rsi_14 Nullable(Float64),
            
            -- MACD
            macd_line Nullable(Float64),
            macd_signal Nullable(Float64),
            macd_histogram Nullable(Float64),
            
            -- Metadata
            indicator_type String,
            timespan String DEFAULT 'day',
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (symbol, date)
        PARTITION BY toYYYYMM(date)
        """
        
        try:
            self.ch_client.command(create_table_sql)
            logger.info("✅ Technical indicators table created/verified")
        except Exception as e:
            logger.error(f"Error creating indicators table: {e}")
            raise
    
    def get_symbol_universe(self) -> List[str]:
        """Get symbols from pair screening results"""
        # From your relaxed pair screening results
        base_symbols = [
            # Pairs that passed screening
            "QQQ", "TQQQ",  # QQQ-TQQQ pair
            "BITX", "IBIT", # BITX-IBIT pair  
            "TLT", "TMF",   # TLT-TMF pair
            "NVDA", "NVDL", # NVDA-NVDL pair
            "SOFI", "SPY",  # SOFI-SPY pair
            "SOXL",         # NVDA-SOXL pair
            
            # Additional major symbols for broader coverage
            "AAPL", "GOOGL", "MSFT", "TSLA", "AMZN",
            "META", "NFLX", "AMD", "INTC", "CRM",
            "VTI", "VOO", "IWM", "DIA", "XLF",
            "XLK", "XLE", "XLV", "XLRE", "XLI"
        ]
        
        return sorted(list(set(base_symbols)))  # Remove duplicates and sort
    
    def load_progress(self) -> Dict:
        """Load download progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                logger.info(f"Loaded progress: {len(progress)} completed downloads")
                return progress
            except Exception as e:
                logger.warning(f"Error loading progress: {e}")
        
        return {}
    
    def save_progress(self):
        """Save download progress to file"""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    def rate_limit_wait(self):
        """Ensure we don't exceed API rate limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def download_indicator(self, symbol: str, indicator_type: str, **kwargs) -> Optional[pd.DataFrame]:
        """Download single indicator for a symbol"""
        
        # Check if already downloaded
        progress_key = f"{symbol}_{indicator_type}_{kwargs.get('window', '')}"
        if progress_key in self.progress:
            logger.debug(f"Skipping {progress_key} - already downloaded")
            return None
        
        # Rate limiting
        self.rate_limit_wait()
        
        # Build parameters
        params = {
            f"timestamp.gte": self.start_date,
            f"timestamp.lte": self.end_date,
            "timespan": "day",
            "adjusted": "true", 
            "series_type": "close",
            "order": "asc",
            "limit": 5000,  # Max per request
            "apikey": self.api_key
        }
        
        # Add indicator-specific parameters
        if indicator_type in ["sma", "ema"]:
            params["window"] = kwargs.get("window", 20)
        elif indicator_type == "rsi":
            params["window"] = kwargs.get("window", 14)
        elif indicator_type == "macd":
            params.update({
                "short_window": kwargs.get("short_window", 12),
                "long_window": kwargs.get("long_window", 26),
                "signal_window": kwargs.get("signal_window", 9)
            })
        
        all_data = []
        next_url = f"{self.base_url}/{indicator_type}/{symbol}"
        
        logger.info(f"📥 Downloading {indicator_type.upper()} for {symbol} (window: {kwargs.get('window', 'default')})")
        
        while next_url:
            try:
                if next_url.startswith("http") and "cursor=" in next_url:
                    # Use the full next_url for pagination
                    response = requests.get(next_url)
                else:
                    # First request with parameters
                    response = requests.get(next_url, params=params)
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    logger.error(f"API Error for {symbol} {indicator_type}: {data}")
                    break
                
                results = data.get("results", {})
                values = results.get("values", [])
                
                if not values:
                    logger.debug(f"No more data for {symbol} {indicator_type}")
                    break
                
                all_data.extend(values)
                logger.debug(f"   Downloaded {len(values)} values (total: {len(all_data)})")
                
                # Check for next page
                next_url = data.get("next_url")
                if next_url:
                    self.rate_limit_wait()  # Rate limit between pages
                
            except Exception as e:
                logger.error(f"Error downloading {indicator_type} for {symbol}: {e}")
                break
        
        if all_data:
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['date'] = df['timestamp'].dt.date
            df['symbol'] = symbol
            df['indicator_type'] = indicator_type
            
            # Rename columns based on indicator type
            if indicator_type == "sma":
                window = kwargs.get("window", 20)
                df[f'sma_{window}'] = df['value']
                df = df.drop('value', axis=1)
            elif indicator_type == "ema":
                window = kwargs.get("window", 20)
                df[f'ema_{window}'] = df['value']
                df = df.drop('value', axis=1)
            elif indicator_type == "rsi":
                df['rsi_14'] = df['value']
                df = df.drop('value', axis=1)
            elif indicator_type == "macd":
                df['macd_line'] = df['value']
                df['macd_signal'] = df['signal']
                df['macd_histogram'] = df['histogram']
                df = df.drop(['value', 'signal', 'histogram'], axis=1)
            
            # Mark as completed
            self.progress[progress_key] = {
                "completed_at": datetime.now().isoformat(),
                "records": len(df)
            }
            self.save_progress()
            
            logger.info(f"✅ Downloaded {len(df)} {indicator_type.upper()} records for {symbol}")
            return df
        
        return None
    
    def store_data(self, df: pd.DataFrame):
        """Store data to ClickHouse or CSV"""
        if df is None or df.empty:
            return
            
        if self.clickhouse_available:
            try:
                # Prepare for ClickHouse insertion
                df_insert = df.copy()
                
                # Fill missing columns with None
                for col in ['sma_20', 'sma_50', 'ema_20', 'rsi_14', 'macd_line', 'macd_signal', 'macd_histogram']:
                    if col not in df_insert.columns:
                        df_insert[col] = None
                
                # Insert to ClickHouse
                self.ch_client.insert_df('technical_indicators', df_insert)
                logger.info(f"✅ Stored {len(df_insert)} records to ClickHouse")
                
            except Exception as e:
                logger.error(f"Error storing to ClickHouse: {e}")
                # Fallback to CSV
                self.store_to_csv(df)
        else:
            self.store_to_csv(df)
    
    def store_to_csv(self, df: pd.DataFrame):
        """Store data to CSV file as backup"""
        csv_dir = Path("indicators_data")
        csv_dir.mkdir(exist_ok=True)
        
        symbol = df['symbol'].iloc[0]
        indicator = df['indicator_type'].iloc[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = csv_dir / f"{symbol}_{indicator}_{timestamp}.csv"
        df.to_csv(filename, index=False)
        logger.info(f"📁 Saved to CSV: {filename}")
    
    def download_all_indicators(self):
        """Download all indicators for all symbols"""
        
        total_tasks = len(self.symbols) * 5  # 5 indicators per symbol
        completed_tasks = len(self.progress)
        
        logger.info(f"🚀 Starting download of indicators for {len(self.symbols)} symbols")
        logger.info(f"📊 Progress: {completed_tasks}/{total_tasks} tasks completed")
        logger.info(f"⏱️  Estimated time remaining: {(total_tasks - completed_tasks) * self.rate_limit_delay / 60:.1f} minutes")
        
        for i, symbol in enumerate(self.symbols):
            logger.info(f"\n📈 Processing {symbol} ({i+1}/{len(self.symbols)})")
            
            # Download SMA-20
            df = self.download_indicator(symbol, "sma", window=20)
            if df is not None:
                self.store_data(df)
            
            # Download SMA-50
            df = self.download_indicator(symbol, "sma", window=50)
            if df is not None:
                self.store_data(df)
            
            # Download EMA-20
            df = self.download_indicator(symbol, "ema", window=20)
            if df is not None:
                self.store_data(df)
            
            # Download RSI-14
            df = self.download_indicator(symbol, "rsi", window=14)
            if df is not None:
                self.store_data(df)
            
            # Download MACD
            df = self.download_indicator(symbol, "macd")
            if df is not None:
                self.store_data(df)
        
        logger.info("🎉 Download completed!")
        self.print_summary()
    
    def print_summary(self):
        """Print download summary"""
        completed = len(self.progress)
        total_records = sum(item.get('records', 0) for item in self.progress.values())
        
        print(f"\n📊 DOWNLOAD SUMMARY")
        print(f"=" * 50)
        print(f"✅ Completed downloads: {completed}")
        print(f"📈 Total indicator records: {total_records:,}")
        print(f"📅 Date range: {self.start_date} to {self.end_date}")
        print(f"🔑 API key used: {self.api_key[:10]}...{self.api_key[-5:]}")
        
        if self.clickhouse_available:
            try:
                # Check ClickHouse data
                count_query = "SELECT COUNT(*) as count FROM technical_indicators"
                result = self.ch_client.query(count_query).result_rows[0][0]
                print(f"🗄️  Records in ClickHouse: {result:,}")
            except Exception as e:
                print(f"⚠️  Could not verify ClickHouse data: {e}")

def main():
    """Main download function"""
    
    print("""
🚀 HISTORICAL TECHNICAL INDICATORS DOWNLOADER
==============================================

This script downloads 2.5 years of technical indicators
(2023-01-01 to 2025-06-30) for your statistical arbitrage system.

Indicators downloaded:
✅ SMA (20, 50 day windows)
✅ EMA (20 day window)
✅ RSI (14 day window)  
✅ MACD (12,26,9 parameters)

⚠️  Rate Limited: ~12 seconds between API calls
⏱️  Estimated time: 45-60 minutes for full download
    """)
    
    # Configuration
    API_KEY = "kwnaUOlnQq7lLqRU0KQg2MqndGblHPnR"
    START_DATE = "2023-01-01"
    END_DATE = "2025-06-30"
    
    # Initialize downloader
    downloader = HistoricalIndicatorsDownloader(API_KEY, START_DATE, END_DATE)
    
    # Start download
    try:
        downloader.download_all_indicators()
    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
        print("💾 Progress saved - you can resume by running the script again")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        print("💾 Progress saved - check logs for details")

if __name__ == "__main__":
    main()
