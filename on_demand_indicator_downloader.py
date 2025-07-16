#!/usr/bin/env python3
"""
On-Demand Technical Indicators Downloader for New Pairs
=======================================================

This script downloads missing technical indicators for newly discovered pairs
that aren't in your existing ClickHouse technical_indicators table.

Features:
✅ Checks existing data to avoid duplicates
✅ Downloads only missing indicators
✅ Supports custom date ranges
✅ Rate limiting and resume capability
✅ Integration with pair discovery system

Usage:
    python on_demand_indicator_downloader.py --symbols COIN,MSTR --start-date 2023-01-01
    python on_demand_indicator_downloader.py --check-missing ARKK,ARKG
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
import clickhouse_connect

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ClickHouse availability check
try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    logger.warning("ClickHouse not available - install with: pip install clickhouse-connect")

class OnDemandIndicatorDownloader:
    """Download missing technical indicators for new pairs"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable required")
            
        self.base_url = "https://api.polygon.io/v1/indicators"
        self.rate_limit_delay = 12  # 12 seconds between requests
        self.last_request_time = 0
        
        # ClickHouse setup
        self.setup_clickhouse()
        
        # Standard indicators configuration
        self.indicators_config = {
            "sma": [{"window": 20}, {"window": 50}],
            "ema": [{"window": 20}],
            "rsi": [{"window": 14}],
            "macd": [{"short_window": 12, "long_window": 26, "signal_window": 9}]
        }
        
    def setup_clickhouse(self):
        """Setup ClickHouse connection"""
        if not CLICKHOUSE_AVAILABLE:
            logger.error("ClickHouse not available - cannot check existing data")
            raise ImportError("ClickHouse required for missing data detection")
            
        try:
            self.ch_client = clickhouse_connect.get_client(
                host="localhost",
                port=8123,
                database='polygon_data'
            )
            logger.info("✅ ClickHouse connection established")
            
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            raise
    
    def get_existing_symbols(self) -> Set[str]:
        """Get symbols that already have indicator data"""
        try:
            query = "SELECT DISTINCT symbol FROM technical_indicators"
            result = self.ch_client.query(query)
            existing_symbols = {row[0] for row in result.result_set}
            logger.info(f"Found {len(existing_symbols)} symbols with existing indicator data")
            return existing_symbols
            
        except Exception as e:
            logger.error(f"Error querying existing symbols: {e}")
            return set()
    
    def get_missing_indicators(self, symbol: str, start_date: str = "2023-01-01", 
                             end_date: str = "2025-06-30") -> List[Dict]:
        """Check which indicators are missing for a specific symbol"""
        missing_indicators = []
        
        try:
            # Check each indicator type against the actual table schema
            indicator_checks = [
                ("sma", {"window": 20}, "sma_20"),
                ("sma", {"window": 50}, "sma_50"),
                ("ema", {"window": 20}, "ema_20"),
                ("rsi", {"window": 14}, "rsi_14"),
                ("macd", {"short_window": 12, "long_window": 26, "signal_window": 9}, "macd_line")
            ]
            
            for indicator_type, config, column_name in indicator_checks:
                # Check if data exists for this indicator
                query = f"""
                SELECT COUNT(*) 
                FROM technical_indicators 
                WHERE symbol = '{symbol}' 
                AND date BETWEEN '{start_date}' AND '{end_date}'
                AND {column_name} IS NOT NULL
                """
                
                result = self.ch_client.query(query)
                count = result.result_set[0][0] if result.result_set else 0
                
                if count == 0:
                    missing_indicators.append({
                        "indicator_type": indicator_type,
                        "config": config,
                        "reason": f"No {column_name} data found"
                    })
                else:
                    logger.debug(f"✅ {symbol} {indicator_type} exists ({count} records)")
                        
        except Exception as e:
            logger.error(f"Error checking missing indicators for {symbol}: {e}")
            # If we can't check, assume all are missing
            for indicator_type, configs in self.indicators_config.items():
                for config in configs:
                    missing_indicators.append({
                        "indicator_type": indicator_type,
                        "config": config,
                        "reason": f"Check failed: {e}"
                    })
        
        return missing_indicators
    
    def rate_limit_wait(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def download_indicator(self, symbol: str, indicator_type: str, 
                          start_date: str, end_date: str, **config) -> Optional[List[Dict]]:
        """Download a specific indicator for a symbol"""
        
        # Rate limiting
        self.rate_limit_wait()
        
        # Build parameters
        params = {
            f"timestamp.gte": start_date,
            f"timestamp.lte": end_date,
            "timespan": "day",
            "adjusted": "true", 
            "series_type": "close",
            "order": "asc",
            "limit": 5000,
            "apikey": self.api_key
        }
        
        # Add indicator-specific parameters
        if indicator_type in ["sma", "ema"]:
            params["window"] = config.get("window", 20)
        elif indicator_type == "rsi":
            params["window"] = config.get("window", 14)
        elif indicator_type == "macd":
            params.update({
                "short_window": config.get("short_window", 12),
                "long_window": config.get("long_window", 26),
                "signal_window": config.get("signal_window", 9)
            })
        
        all_data = []
        next_url = f"{self.base_url}/{indicator_type}/{symbol}"
        
        window_desc = config.get("window", "default")
        logger.info(f"📥 Downloading {indicator_type.upper()} for {symbol} (window: {window_desc})")
        
        while next_url:
            try:
                if next_url.startswith("http") and "cursor=" in next_url:
                    response = requests.get(next_url)
                else:
                    response = requests.get(next_url, params=params)
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    logger.error(f"API Error for {symbol} {indicator_type}: {data}")
                    break
                
                results = data.get("results", {}).get("values", [])
                if not results:
                    logger.warning(f"No data returned for {symbol} {indicator_type}")
                    break
                
                # Process results into standard format
                for item in results:
                    # Debug: log the raw item structure
                    logger.debug(f"Raw API item: {item}")
                    
                    # Convert timestamp to proper date format
                    timestamp = item.get("timestamp", "")
                    if isinstance(timestamp, (int, float)):
                        # Convert Unix timestamp (milliseconds) to date
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
                    else:
                        date_str = str(timestamp).split("T")[0] if "T" in str(timestamp) else str(timestamp)
                    
                    record = {
                        "symbol": symbol,
                        "date": date_str,
                        "indicator_type": indicator_type,
                        "value": item.get("value"),
                        "window": config.get("window"),
                        "timespan": "day"
                    }
                    
                    # Handle MACD special case (multiple values)
                    if indicator_type == "macd":
                        record.update({
                            "macd_line": item.get("value"),
                            "signal_line": item.get("signal"),
                            "histogram": item.get("histogram")
                        })
                    
                    all_data.append(record)
                
                # Check for pagination
                next_url = data.get("next_url")
                if next_url:
                    logger.debug(f"Fetching next page for {symbol} {indicator_type}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {symbol} {indicator_type}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error for {symbol} {indicator_type}: {e}")
                break
        
        if all_data:
            logger.info(f"✅ Downloaded {len(all_data)} {indicator_type.upper()} records for {symbol}")
        
        return all_data if all_data else None
    
    def store_to_clickhouse(self, data: List[Dict]) -> bool:
        """Store indicator data to ClickHouse"""
        if not data:
            return False
            
        try:
            # Transform data to match ClickHouse schema
            formatted_data = []
            
            logger.debug(f"Transforming {len(data)} records for ClickHouse")
            
            for record in data:
                indicator_type = record.get("indicator_type")
                symbol = record.get("symbol")
                date = record.get("date")
                value = record.get("value")
                
                logger.debug(f"Processing record: {symbol} {indicator_type} {date} = {value}")
                
                # Date should already be in YYYY-MM-DD format from download_indicator
                
                # Base record
                base_record = {
                    "symbol": symbol,
                    "date": date,
                    "timestamp": f"{date} 00:00:00",
                    "indicator_type": indicator_type,
                    "timespan": record.get("timespan", "day"),
                    "sma_20": None,
                    "sma_50": None,
                    "ema_20": None,
                    "rsi_14": None,
                    "macd_line": None,
                    "macd_signal": None,
                    "macd_histogram": None
                }
                
                # Map indicator values to correct columns
                if indicator_type == "sma":
                    window = record.get("window", 20)
                    if window == 20:
                        base_record["sma_20"] = value
                    elif window == 50:
                        base_record["sma_50"] = value
                elif indicator_type == "ema":
                    window = record.get("window", 20)
                    if window == 20:
                        base_record["ema_20"] = value
                elif indicator_type == "rsi":
                    window = record.get("window", 14)
                    if window == 14:
                        base_record["rsi_14"] = value
                elif indicator_type == "macd":
                    base_record["macd_line"] = record.get("macd_line") or value
                    base_record["macd_signal"] = record.get("signal_line")
                    base_record["macd_histogram"] = record.get("histogram")
                
                formatted_data.append(base_record)
            
            logger.debug(f"Formatted {len(formatted_data)} records for insertion")
            
            # Convert to DataFrame for insertion (same as original downloader)
            import pandas as pd
            df = pd.DataFrame(formatted_data)
            
            # Convert date column to proper datetime format
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Insert using DataFrame method
            self.ch_client.insert_df('technical_indicators', df)
            logger.info(f"✅ Stored {len(formatted_data)} records to ClickHouse")
            return True
            
        except Exception as e:
            import traceback
            logger.error(f"Error storing to ClickHouse: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(f"Sample data: {data[:1] if data else 'No data'}")
            return False
    
    def download_missing_for_symbol(self, symbol: str, start_date: str = "2023-01-01", 
                                   end_date: str = "2025-06-30") -> Dict:
        """Download all missing indicators for a single symbol"""
        
        logger.info(f"\n📈 Checking missing indicators for {symbol}")
        
        missing_indicators = self.get_missing_indicators(symbol, start_date, end_date)
        
        if not missing_indicators:
            logger.info(f"✅ All indicators already exist for {symbol}")
            return {"symbol": symbol, "downloaded": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"Found {len(missing_indicators)} missing indicators for {symbol}")
        
        downloaded = 0
        errors = 0
        
        for missing in missing_indicators:
            indicator_type = missing["indicator_type"]
            config = missing["config"]
            
            try:
                data = self.download_indicator(
                    symbol=symbol,
                    indicator_type=indicator_type,
                    start_date=start_date,
                    end_date=end_date,
                    **config
                )
                
                if data and self.store_to_clickhouse(data):
                    downloaded += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error downloading {indicator_type} for {symbol}: {e}")
                errors += 1
        
        result = {
            "symbol": symbol,
            "downloaded": downloaded,
            "skipped": 0,
            "errors": errors
        }
        
        logger.info(f"✅ {symbol} complete: {downloaded} downloaded, {errors} errors")
        return result
    
    def download_missing_for_symbols(self, symbols: List[str], 
                                   start_date: str = "2023-01-01", 
                                   end_date: str = "2025-06-30") -> Dict:
        """Download missing indicators for multiple symbols"""
        
        logger.info(f"\n🚀 MISSING INDICATORS DOWNLOADER")
        logger.info(f"{'='*50}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Rate limited: ~{self.rate_limit_delay} seconds between calls")
        
        total_results = {
            "symbols_processed": 0,
            "total_downloaded": 0,
            "total_errors": 0,
            "results": []
        }
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n📊 Processing {symbol} ({i}/{len(symbols)})")
            
            result = self.download_missing_for_symbol(symbol, start_date, end_date)
            total_results["results"].append(result)
            total_results["symbols_processed"] += 1
            total_results["total_downloaded"] += result["downloaded"]
            total_results["total_errors"] += result["errors"]
        
        # Summary
        logger.info(f"\n🎯 DOWNLOAD COMPLETE")
        logger.info(f"{'='*30}")
        logger.info(f"Symbols processed: {total_results['symbols_processed']}")
        logger.info(f"Indicators downloaded: {total_results['total_downloaded']}")
        logger.info(f"Errors: {total_results['total_errors']}")
        
        return total_results


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Download missing technical indicators")
    parser.add_argument("--symbols", type=str, help="Comma-separated list of symbols")
    parser.add_argument("--check-missing", type=str, help="Check which indicators are missing for symbols")
    parser.add_argument("--start-date", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2025-06-30", help="End date (YYYY-MM-DD)")
    parser.add_argument("--api-key", type=str, help="Polygon.io API key (or use POLYGON_API_KEY env var)")
    
    args = parser.parse_args()
    
    if not args.symbols and not args.check_missing:
        print("Please provide --symbols or --check-missing")
        parser.print_help()
        return
    
    try:
        downloader = OnDemandIndicatorDownloader(api_key=args.api_key)
        
        if args.check_missing:
            symbols = [s.strip() for s in args.check_missing.split(",")]
            logger.info(f"Checking missing indicators for: {symbols}")
            
            for symbol in symbols:
                missing = downloader.get_missing_indicators(symbol, args.start_date, args.end_date)
                if missing:
                    logger.info(f"\n{symbol} missing indicators:")
                    for m in missing:
                        logger.info(f"  - {m['indicator_type']} {m['config']}")
                else:
                    logger.info(f"\n{symbol}: All indicators present ✅")
        
        if args.symbols:
            symbols = [s.strip() for s in args.symbols.split(",")]
            results = downloader.download_missing_for_symbols(symbols, args.start_date, args.end_date)
            
            # Save results
            with open("missing_indicators_download_results.json", "w") as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"📁 Results saved to: missing_indicators_download_results.json")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
