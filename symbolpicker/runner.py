"""
Main runner for the Symbol Picker.
Orchestrates data fetching, filtering, feature engineering, ranking, and export.
"""
import asyncio
import logging
import argparse
import yaml
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.data.feeds.polygon_rest import create_polygon_rest_service
from symbolpicker.filters import CoarseFilter
from symbolpicker.features import IntradayFeatureEngine
from symbolpicker.ranker import Ranker
from symbolpicker.regime_adapter import RegimeAdapter
from symbolpicker.exporter import ArtifactExporter
from core_engine.utils.structured_logging import init_logging, LogConfig

logger = logging.getLogger("core_engine.symbolpicker.runner")

class SymbolPickerRunner:
    def __init__(self, config_path: str = "symbolpicker/config.yaml"):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path: str):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    async def run(self, date: datetime = None) -> Optional[str]:
        """
        Run the symbol picking pipeline.
        
        Args:
            date: The target date for selection (default: yesterday/today depending on time)
        """
        if date is None:
            # Default to yesterday if running early morning, or today if after close?
            # Safer to default to "previous trading day" logic, but for simplicity let's use yesterday
            # as this is typically run pre-market for the *coming* day using *yesterday's* data.
            date = datetime.now() - timedelta(days=1)
            
        logger.info(f"Starting Symbol Picker for date: {date.strftime('%Y-%m-%d')}")
        
        # 1. Initialize Services
        polygon = await create_polygon_rest_service()
        if not polygon.is_initialized:
            logger.error("Failed to initialize Polygon service")
            return

        try:
            # 2. Broad Scan (Coarse Filter)
            logger.info("Phase 1: Broad Market Scan...")
            # Fetch Grouped Daily Bars (The entire market)
            daily_market = await polygon.get_grouped_daily_bars(date)
            logger.info(f"Fetched {len(daily_market)} symbols from Polygon.")
            
            coarse_filter = CoarseFilter(self.config)
            candidates = coarse_filter.filter_universe(daily_market)
            
            if not candidates:
                logger.error("No candidates passed coarse filter!")
                return
                
            # Limit candidates for deep dive if too many passed (safety cap)
            # If we want top 20, maybe sending 100-200 to deep dive is enough
            max_deep_dive = 200
            if len(candidates) > max_deep_dive:
                logger.info(f"Capping deep dive candidates to {max_deep_dive} (from {len(candidates)}) by Dollar Vol.")
                # We need to re-sort by dollar vol to pick top N for deep dive
                # Re-calculate dollar vol since filter just returned list
                subset = daily_market.loc[candidates]
                subset['dollar_vol'] = subset['close'] * subset['volume']
                candidates = subset.sort_values('dollar_vol', ascending=False).head(max_deep_dive).index.tolist()
                
            logger.info(f"Proceeding to Phase 2 with {len(candidates)} candidates.")

            # 3. Deep Dive (Intraday Features)
            logger.info("Phase 2: Deep Dive (Intraday Data)...")
            feature_engine = IntradayFeatureEngine(self.config)
            lookback = self.config['features']['lookback_days']
            
            # Fetch minute bars for all candidates
            minute_data = await polygon.get_bars_multi(
                candidates, 
                timeframe='1min', 
                days=lookback
            )
            
            sample_size = 0
            if minute_data:
                first_key = list(minute_data.keys())[0]
                sample_size = len(minute_data[first_key])
            
            logger.info(f"Fetched minute bars for {len(minute_data)} symbols. Sample size ({list(minute_data.keys())[0] if minute_data else 'N/A'}): {sample_size}")
            
            features_df = feature_engine.compute_features(minute_data)
            logger.info(f"Computed features for {len(features_df)} symbols.")
            
            # Merge daily stats (dollar vol) into features_df for ranking
            # Daily snapshot data for dollar vol
            daily_subset = daily_market.loc[features_df.index]
            features_df['dollar_vol'] = daily_subset['close'] * daily_subset['volume']
            
            # 4. Selection (Ranking)
            logger.info("Phase 3: Ranking & Selection...")
            ranker = Ranker(self.config)
            
            # TODO: Load previous universe for hysteresis (Empty for now)
            previous_universe = set() 
            
            final_universe = ranker.select_universe(features_df, previous_universe)
            logger.info(f"Selected {len(final_universe)} symbols.")
            
            # 5. Regime Context
            logger.info("Phase 4: Regime Analysis...")
            regime_adapter = RegimeAdapter(self.config)
            regime_data = await regime_adapter.generate_regime_label(polygon, date)
            logger.info(f"Detected Regime: {regime_data.get('label')}")
            
            # 6. Export
            logger.info("Phase 5: Exporting Artifact...")
            exporter = ArtifactExporter(self.config)
            file_path = exporter.export(final_universe, regime_data, date)
            
            print("\n" + "="*50)
            print(f"🚀 SYMBOL PICKER SUCCESS | {date.strftime('%Y-%m-%d')}")
            print("="*50)
            print(f"📁 Artifact: {file_path}")
            print(f"📊 Regime:   {regime_data.get('label', 'UNKNOWN').upper()}")
            print(f"🔢 Count:    {len(final_universe)} symbols")
            print(f"🔝 Top 5:    {', '.join(list(final_universe.keys())[:5])}")
            print("="*50)
            
            # Print full ranked table
            print(f"{'Rank':<5} | {'Symbol':<8} | {'Score':<8} | {'Dollar Vol (M)':<15} | {'Vol (%)':<8} | {'Spread (bps)':<12}")
            print("-" * 75)
            
            # Sort by rank just in case
            sorted_universe = sorted(final_universe.items(), key=lambda x: x[1]['rank'])
            
            for sym, data in sorted_universe:
                metrics = data['metrics']
                dvol_m = metrics['dollar_vol'] / 1_000_000
                vol_pct = metrics['realized_vol'] * 100
                spread = metrics['avg_spread_bps']
                print(f"{data['rank']:<5} | {sym:<8} | {data['score']:<8.4f} | {dvol_m:<15.2f} | {vol_pct:<8.2f} | {spread:<12.2f}")
            
            print("="*75 + "\n")
            
            return file_path
            
        finally:
            await polygon.close()

if __name__ == "__main__":
    # Load environment variables from .env
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run Quant Symbol Picker")
    parser.add_argument("--date", type=str, help="YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--config", type=str, default="symbolpicker/config.yaml", help="Path to config")
    parser.add_argument("--log-format", type=str, choices=["structured", "human"], default="human", help="Log format")
    
    args = parser.parse_args()
    
    init_logging(LogConfig(level="INFO", format=args.log_format))
    
    runner = SymbolPickerRunner(args.config)
    
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
        asyncio.run(runner.run(target_date))
    elif 'data' in runner.config and 'start_date' in runner.config['data'] and 'end_date' in runner.config['data']:
        start_date = datetime.strptime(runner.config['data']['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(runner.config['data']['end_date'], '%Y-%m-%d')
        
        current_date = start_date
        while current_date <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                asyncio.run(runner.run(current_date))
            current_date += timedelta(days=1)
    else:
        # Default to yesterday
        target_date = datetime.now() - timedelta(days=1)
        asyncio.run(runner.run(target_date))

