#!/usr/bin/env python3
"""
RTH Regime Changes Utility
==========================

Institutional-grade utility for listing market regime changes during Regular Trading Hours (RTH)
for specified symbols over a given lookback period.

Features:
- Bar-by-bar regime analysis to detect precise transition points
- RTH filtering to remove overnight noise/distortions
- Multi-symbol support with professional reporting
- Adheres to Rule 2 (Regime-First Principle)

Usage:
    python utils/rth_regime_changes.py --symbols SPY,QQQ,TSLA --days 30 --timeframe 1h
"""

import sys
import os
import argparse
import asyncio
import pandas as pd
import logging
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from math import ceil

# Add root to path for core_engine imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core_engine.data.manager import ClickHouseDataManager as DataManager
    from core_engine.regime.engine import EnhancedRegimeEngine as RegimeEngine
    from core_engine.data.rth_filter import filter_bars_to_rth
    from core_engine.config.component_config import RegimeConfig, DataConfig
    from core_engine.type_definitions.regime import MarketRegime
    from core_engine.data.market_calendar import MarketCalendar
except ImportError as e:
    print(f"Error importing core_engine components: {e}")
    print("Ensure you are running this from the project root and requirements are installed.")
    sys.exit(1)

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RTHRegimeTracker")

class RTHRegimeTracker:
    """Utility class to track and report RTH regime changes."""
    
    def __init__(self, symbols: List[str], start_date: datetime, end_date: datetime, timeframe: str, warmup_bars: int = 200):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.timeframe = timeframe
        self.warmup_bars = warmup_bars
        self.data_manager: Optional[DataManager] = None
        self.regime_engine: Optional[RegimeEngine] = None
        
    async def initialize(self):
        """Initialize the data and regime components."""
        logger.info("Initializing Data and Regime components...")
        
        # Calculate warmup needed BEFORE initializing DataManager
        # This ensures the DataManager config covers the warmup period
        calendar = MarketCalendar()
        asset_class = calendar.get_asset_class(self.symbols[0] if self.symbols else "SPY")
        
        # Estimate bars per day for the chosen timeframe
        # US Equity RTH is 390 minutes (9:30-16:00)
        session_minutes = 390
        try:
            # Try to get actual session minutes if possible
            open_dt, close_dt = calendar.get_session_times(self.start_date, asset_class)
            session_minutes = int((close_dt - open_dt).total_seconds() // 60)
        except Exception:
            pass

        interval_min = 1
        if self.timeframe.endswith("m") or self.timeframe.endswith("min"):
            try:
                interval_min = int(self.timeframe.replace("min", "").replace("m", ""))
            except Exception:
                interval_min = 1
        elif self.timeframe == "1h":
            interval_min = 60
        elif self.timeframe == "1d":
            interval_min = session_minutes

        bars_per_day = max(1, session_minutes // interval_min)
        warmup_days = max(1, int(ceil(max(0, self.warmup_bars) / bars_per_day)) + 3) # Extra buffer
        
        self.fetch_start_date = self.start_date - timedelta(days=warmup_days)
        
        # Initialize Data Manager with the BROADER range for warmup
        data_config = DataConfig(
            symbols=self.symbols,
            start_date=self.fetch_start_date.strftime('%Y-%m-%d'),
            end_date=self.end_date.strftime('%Y-%m-%d')
        )
        self.data_manager = DataManager(config=data_config)
        
        # Initialize Regime Engine
        regime_config = RegimeConfig()
        self.regime_engine = RegimeEngine(config=regime_config)
        
        try:
            # Initialize components
            await self.data_manager.initialize()
            await self.data_manager.start()
            
            await self.regime_engine.initialize()
            await self.regime_engine.start()
            
            logger.info(f"✅ Components initialized with warmup range starting {self.fetch_start_date.date()}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
            return False

    async def run(self):
        """Run the regime change analysis for all symbols."""
        if not await self.initialize():
            return

        print("\n" + "="*90)
        print(f"RTH REGIME CHANGE ANALYSIS REPORT")
        print(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Period:      {self.start_date.date()} to {self.end_date.date()}")
        print(f"Warmup Bars: {self.warmup_bars}")
        print(f"Timeframe:   {self.timeframe}")
        print("="*90)

        report_data = {}

        for symbol in self.symbols:
            logger.info(f"Processing {symbol}...")
            
            try:
                # 1. Fetch data using the pre-calculated fetch_start_date
                df = await self.data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=self.fetch_start_date,
                    end_date=self.end_date,
                    timeframe=self.timeframe
                )
                
                if df is None or df.empty:
                    logger.warning(f"No data retrieved for {symbol}")
                    continue

                # Ensure timestamp is the index for resampling
                if 'timestamp' in df.columns:
                    df = df.set_index('timestamp')
                
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)

                # 2. Resample to requested timeframe if not 1min
                # ClickHouseDataManager usually returns raw data.
                tf_mapping = {
                    '1m': '1min',
                    '5m': '5min',
                    '15m': '15min',
                    '30m': '30min',
                    '1h': '1h',
                    '1d': '1D'
                }
                actual_tf = tf_mapping.get(self.timeframe.lower(), self.timeframe)
                
                if actual_tf != '1min':
                    logger.info(f"Resampling data to {actual_tf}...")
                    resampled = df.resample(actual_tf).agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum'
                    }).dropna()
                    df = resampled

                # Restore timestamp column for engine
                df['timestamp'] = df.index
                df['symbol'] = symbol
                    
                # 3. Filter to RTH
                rth_df = filter_bars_to_rth(df, symbol=symbol)
                if rth_df.empty:
                    logger.warning(f"No RTH data for {symbol} after filtering")
                    continue
                
                # 4. Analyze regimes bar-by-bar
                # Note: process_market_data(DataFrame) performs sequential analysis
                result = self.regime_engine.process_market_data(rth_df)
                
                if not result or not result.get('market_data_processed'):
                    logger.error(f"Regime analysis failed for {symbol}: {result.get('error', 'Unknown error')}")
                    continue
                
                sequence = result.get('regime_sequence', [])
                
                # 4. Identify changes in the requested period (excluding warm-up)
                analysis_start_ts = pd.Timestamp(self.start_date)
                
                changes = []
                last_regime = None
                
                # Check if we need to handle timezone awareness
                is_aware = False
                if sequence and isinstance(sequence[0]['timestamp'], (pd.Timestamp, datetime)):
                    first_ts = sequence[0]['timestamp']
                    if hasattr(first_ts, 'tzinfo') and first_ts.tzinfo is not None:
                        is_aware = True
                        if analysis_start_ts.tzinfo is None:
                            # Localize to the same timezone as the data
                            analysis_start_ts = analysis_start_ts.tz_localize(first_ts.tzinfo)
                
                for entry in sequence:
                    ts = entry['timestamp']
                    # Convert to pandas Timestamp for comparison if needed
                    if not isinstance(ts, pd.Timestamp):
                        ts = pd.Timestamp(ts)
                    
                    if is_aware and ts.tzinfo is None:
                        # Should not happen if first_ts was aware, but for safety
                        ts = ts.tz_localize(analysis_start_ts.tzinfo)
                    elif not is_aware and ts.tzinfo is not None:
                        ts = ts.tz_localize(None)
                        
                    current_regime = entry['regime']
                    
                    if current_regime != last_regime:
                        # Only record if it's within our reporting period OR it's the first known regime
                        if ts >= analysis_start_ts or last_regime is None:
                            changes.append({
                                'timestamp': ts,
                                'regime': current_regime,
                                'confidence': entry.get('confidence', 0.0),
                                'is_transition': last_regime is not None
                            })
                        last_regime = current_regime
                
                report_data[symbol] = [c for c in changes if c['is_transition'] or c['timestamp'] >= analysis_start_ts]

            except Exception as e:
                logger.error(f"Error analyzing symbol {symbol}: {e}")

        # Final Formatting and Output
        for symbol, changes in report_data.items():
            print(f"\n>>> SYMBOL: {symbol}")
            if not changes:
                print("    No regime changes detected in the specified period.")
            else:
                print(f"    {'Timestamp':<25} | {'Regime Change':<20} | {'Confidence':<10}")
                print(f"    {'-'*25}-+-{'-'*20}-+-{'-'*10}")
                for i, change in enumerate(changes):
                    ts_str = change['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    regime_str = change['regime']
                    confidence = change['confidence']
                    
                    prefix = "TRANSITION ->" if change['is_transition'] else "START REGIME :"
                    print(f"    {ts_str:<25} | {prefix} {regime_str:<10} | {confidence:.4f}")
        
        print("\n" + "="*90)
        print("Analysis Complete.")
        
        # Cleanup
        await self.data_manager.stop()
        await self.regime_engine.stop()

def main():
    parser = argparse.ArgumentParser(description="Professional RTH Regime Change Tracker")
    parser.add_argument("--config", type=str, default="utils/regime_report_config.yaml", help="Path to config YAML file")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols (overrides config)")
    parser.add_argument("--start_date", type=str, help="Start date YYYY-MM-DD (overrides config)")
    parser.add_argument("--end_date", type=str, help="End date YYYY-MM-DD (overrides config)")
    parser.add_argument("--timeframe", type=str, help="Data timeframe (overrides config)")
    parser.add_argument("--warmup-bars", type=int, help="Number of bars for warmup (overrides config)")
    
    args = parser.parse_args()
    
    # Default values
    config_data = {
        'symbols': ['SPY'],
        'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
        'timeframe': '1h',
        'warmup_bars': 200
    }

    # Load from config file if exists
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.config)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config:
                    config_data.update(loaded_config)
            logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    else:
        logger.warning(f"Config file {args.config} not found, using defaults.")

    # Override with command line arguments if provided
    if args.symbols:
        config_data['symbols'] = [s.strip().upper() for s in args.symbols.split(",")]
    if args.start_date:
        config_data['start_date'] = args.start_date
    if args.end_date:
        config_data['end_date'] = args.end_date
    if args.timeframe:
        config_data['timeframe'] = args.timeframe
    if args.warmup_bars:
        config_data['warmup_bars'] = args.warmup_bars
    
    symbols = config_data['symbols']
    timeframe = config_data['timeframe']
    warmup_bars = config_data['warmup_bars']
    
    # Parse dates
    try:
        start_date = datetime.strptime(config_data['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(config_data['end_date'], '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"Error parsing dates: {e}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    tracker = RTHRegimeTracker(symbols, start_date, end_date, timeframe, warmup_bars)
    asyncio.run(tracker.run())

if __name__ == "__main__":
    main()
