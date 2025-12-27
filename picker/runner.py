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
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, Set
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.data.feeds.polygon_rest import create_polygon_rest_service
from picker.filters import CoarseFilter
from picker.features import IntradayFeatureEngine
from picker.ranker import Ranker
from picker.regime_adapter import RegimeAdapter
from picker.exporter import ArtifactExporter
from core_engine.utils.structured_logging import init_logging, LogConfig

logger = logging.getLogger("core_engine.picker.runner")

class SymbolPickerRunner:
    def __init__(self, config_path: str = "picker/config.yaml"):
        self.config = self._load_config(config_path)
        
    def _load_config(self, path: str):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    async def run(self, date: datetime = None) -> Optional[str]:
        """
        Run the symbol picking pipeline.
        
        Args:
            date: The reference date (as-of date) for selection
        """
        if date is None:
            # Default to the most recent completed trading day
            # If today is Monday, yesterday was Sunday, so use Friday.
            date = datetime.now() - timedelta(days=1)
            while date.weekday() >= 5:
                date -= timedelta(days=1)
            
        trade_date = self._get_next_trading_day(date)
        logger.info(f"Starting Symbol Picker | As-Of: {date.strftime('%Y-%m-%d')} | Trade-Date: {trade_date.strftime('%Y-%m-%d')}")
        
        # 1. Initialize Services
        polygon = await create_polygon_rest_service()
        if not polygon.is_initialized:
            logger.error("Failed to initialize Polygon service")
            return

        try:
            # 1. Broad Scan (Coarse Filter)
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
            # To avoid biasing only towards Mega-Caps, we take a stratified sample
            max_deep_dive = 400 
            if len(candidates) > max_deep_dive:
                logger.info(f"Capping deep dive candidates to {max_deep_dive} (from {len(candidates)}) using stratified sampling.")
                subset = daily_market.loc[candidates].copy()
                subset['dollar_vol'] = subset['close'] * subset['volume']
                subset = subset.sort_values('dollar_vol', ascending=False)
                
                # Take top 150 (Mega/Large)
                top_tier = subset.head(150).index.tolist()
                # Take 250 from the rest (Mid/Small) spread out
                remaining = subset.iloc[150:]
                if len(remaining) > 250:
                    # Sample every Nth to get a broad range of sizes
                    step = len(remaining) // 250
                    mid_small_tier = remaining.iloc[::step].head(250).index.tolist()
                else:
                    mid_small_tier = remaining.index.tolist()
                
                candidates = top_tier + mid_small_tier
            
            # Ensure candidates are unique and exist in daily_market
            candidates = [c for c in list(dict.fromkeys(candidates)) if c in daily_market.index]
                
            logger.info(f"Proceeding to Phase 2 with {len(candidates)} candidates.")

            # 2. Fetch Metadata (Market Cap, Sector) - Institutional Upgrade
            logger.info("Phase 1.5: Fetching Institutional Metadata...")
            metadata_map = await polygon.get_ticker_details_multi(candidates)
            logger.info(f"Fetched metadata for {len(metadata_map)} symbols.")

            # 3. Deep Dive (Intraday Features)
            logger.info("Phase 2: Deep Dive (Intraday Data)...")
            feature_engine = IntradayFeatureEngine(self.config)
            lookback = self.config['features']['lookback_days']
            
            # Fetch minute bars for all candidates
            minute_data = await polygon.get_bars_multi(
                candidates, 
                timeframe='1min', 
                days=lookback,
                end=date
            )
            
            sample_size = 0
            if minute_data:
                # Find a symbol that actually has data
                for sym in candidates:
                    if sym in minute_data and not minute_data[sym].empty:
                        sample_size = len(minute_data[sym])
                        logger.info(f"Fetched minute bars for {len(minute_data)} symbols. Sample size ({sym}): {sample_size}")
                        break
            
            features_df = feature_engine.compute_features(minute_data)
            logger.info(f"Computed features for {len(features_df)} symbols.")
            
            # 3.5 Correlation Matrix (Vectorized)
            logger.info("Phase 2.5: Computing Correlation Matrix...")
            returns_map = {}
            for sym, df in minute_data.items():
                if not df.empty and len(df) > 10:
                    returns_map[sym] = df['close'].pct_change().fillna(0)
            
            returns_df = pd.DataFrame(returns_map)
            correlation_matrix = returns_df.corr()
            
            # 3.6 Rolling 30d ADV (Institutional Liquidity Filter)
            logger.info("Phase 2.6: Fetching 30d ADV...")
            adv_map = await polygon.get_adv_multi(candidates, days=30, end_date=date)
            
            # Merge daily stats (dollar vol), ADV, and metadata into features_df for ranking
            daily_subset = daily_market.loc[features_df.index]
            features_df['dollar_vol'] = daily_subset['close'] * daily_subset['volume']
            features_df['adv_30d'] = pd.Series(adv_map)
            features_df['close'] = daily_subset['close']
            
            # Enrich with metadata (Vectorized)
            metadata_df = pd.DataFrame.from_dict(metadata_map, orient='index')
            if not metadata_df.empty:
                # Ensure required columns exist and rename them
                cols_to_keep = {
                    'market_cap': 'market_cap',
                    'sic_description': 'sector',
                    'type': 'ticker_type'
                }
                
                # Add missing columns as NaN
                for col in cols_to_keep.keys():
                    if col not in metadata_df.columns:
                        metadata_df[col] = np.nan
                
                # Select and rename
                metadata_subset = metadata_df[list(cols_to_keep.keys())].rename(columns=cols_to_keep)
                features_df = features_df.join(metadata_subset, how='left')
            else:
                features_df['market_cap'] = 0
                features_df['sector'] = 'UNKNOWN'
                features_df['ticker_type'] = 'CS'

            features_df['market_cap'] = features_df['market_cap'].fillna(0)
            features_df['sector'] = features_df['sector'].fillna('UNKNOWN')
            features_df['ticker_type'] = features_df['ticker_type'].fillna('CS')
            
            # 4. Regime Context (Moved up because ranking is regime-adaptive)
            logger.info("Phase 3: Regime Analysis...")
            regime_adapter = RegimeAdapter(self.config)
            regime_data = await regime_adapter.generate_regime_label(polygon, date)
            regime_label = regime_data.get('primary', 'UNKNOWN')
            logger.info(f"Detected Regime: {regime_label}")

            # 5. Selection (Ranking)
            logger.info("Phase 4: Ranking & Selection...")
            ranker = Ranker(self.config)
            
            # Log candidate distribution (Vectorized)
            temp_buckets = pd.Series('small', index=features_df.index)
            mcap_bn = features_df['market_cap'] / 1_000_000_000
            temp_buckets.loc[mcap_bn >= ranker.cap_thresholds['small_max']] = 'mid'
            temp_buckets.loc[mcap_bn >= ranker.cap_thresholds['mid_max']] = 'large'
            temp_buckets.loc[features_df['ticker_type'] == 'ETF'] = 'etf'
            dist = temp_buckets.value_counts()
            logger.info(f"Candidate Distribution ({len(features_df)}): {dist.to_dict()}")

            # Load previous universe for hysteresis
            previous_universe = self._load_previous_universe() 
            
            selection_result = ranker.select_universe(
                features_df, 
                previous_universe, 
                regime_label=regime_label,
                correlation_matrix=correlation_matrix
            )
            final_universe = selection_result['symbols']
            diagnostics = selection_result['diagnostics']
            
            # 5.5 Post-Selection Filters (Earnings, NBBO, Borrow)
            logger.info("Phase 4.5: Post-Selection Risk Checks...")
            selected_symbols = list(final_universe.keys())
            
            # Fetch Risk Data
            earnings_task = polygon.get_upcoming_earnings(selected_symbols)
            nbbo_task = polygon.get_last_quote_multi(selected_symbols)
            borrow_task = polygon.get_borrow_info_multi(selected_symbols)
            
            earnings_map, nbbo_map, borrow_map = await asyncio.gather(earnings_task, nbbo_task, borrow_task)
            
            # Filter out earnings (within next 2 days)
            filtered_universe = {}
            earnings_count = 0
            for sym, data in final_universe.items():
                earnings_date = earnings_map.get(sym)
                if earnings_date:
                    try:
                        e_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
                        if (e_dt - trade_date).days <= 2:
                            logger.warning(f"Excluding {sym} due to upcoming earnings on {earnings_date}")
                            earnings_count += 1
                            continue
                    except: pass
                
                # Enrich with NBBO and Borrow info
                quote = nbbo_map.get(sym, {})
                if quote.get('bid') and quote.get('ask'):
                    actual_spread_bps = (quote['ask'] - quote['bid']) / ((quote['ask'] + quote['bid']) / 2) * 10000
                    data['metrics']['nbbo_spread_bps'] = actual_spread_bps
                else:
                    data['metrics']['nbbo_spread_bps'] = data['metrics']['avg_spread_bps']
                
                data['risk'] = {
                    'earnings_date': earnings_date,
                    'borrow': borrow_map.get(sym, {'status': 'UNKNOWN'})
                }
                filtered_universe[sym] = data
            
            # 6. Micro-Stability Check (Phase 4.7)
            # Use 1-second bars for the final selection to detect jitter/voids
            logger.info("Phase 4.7: Micro-Stability Validation (1s Data)...")
            final_candidates = list(filtered_universe.keys())[:20] # Top 20
            
            # Fetch last 10 minutes of 1s data
            # Note: We use the 'date' (as-of) and look at the end of that day
            # For a real live system, this would be 'now'
            end_time = date.replace(hour=16, minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(minutes=10)
            
            second_data = await polygon.get_bars_multi(
                final_candidates, 
                timeframe='1s', 
                start=start_time, 
                end=end_time
            )
            
            feature_engine = IntradayFeatureEngine(self.config)
            micro_metrics = feature_engine.compute_micro_stability(second_data)
            
            # Enrich universe with micro-stability
            for sym in final_candidates:
                if sym in micro_metrics:
                    filtered_universe[sym]['micro_stability'] = micro_metrics[sym]
                    if micro_metrics[sym]['micro_score'] < self.config['selection'].get('min_micro_score', 0.3):
                        logger.warning(f"Low micro-stability for {sym}: score={micro_metrics[sym]['micro_score']:.2f}")

            final_universe = filtered_universe
            logger.info(f"Selected {len(final_universe)} symbols. Churn: {diagnostics.get('churn', 0):.2%}. Earnings Exclusions: {earnings_count}")
            
            # 7. Export (Phase 5)
            logger.info("Phase 5: Exporting Artifact...")
            exporter = ArtifactExporter(self.config)
            file_path = exporter.export(final_universe, regime_data, date, trade_date=trade_date, diagnostics=diagnostics)
            
            print("\n" + "="*50)
            print(f"🚀 SYMBOL PICKER SUCCESS | Trade Date: {trade_date.strftime('%Y-%m-%d')}")
            print("="*50)
            print(f"📁 Artifact: {file_path}")
            print(f"📅 As-Of:    {date.strftime('%Y-%m-%d')}")
            print(f"📊 Regime:   {regime_label.upper()}")
            print(f"🔢 Count:    {len(final_universe)} symbols")
            print(f"🔝 Top 5:    {', '.join(list(final_universe.keys())[:5])}")
            print("="*50)
            
            # 1st List: Analysis Period (Top 20 Candidates by Raw Score)
            print("\n" + "-"*15 + " LIST 1: ANALYSIS PERIOD (Top 20 by Score) " + "-"*15)
            print(f"{'Rank':<5} | {'Symbol':<8} | {'Score':<8} | {'Bucket':<8} | {'ADV 30d (M)':<15} | {'Vol (%)':<8} | {'Spread (bps)':<12}")
            print("-" * 95)
            
            top_candidates = features_df.sort_values('score', ascending=False).head(20)
            for sym, row in top_candidates.iterrows():
                adv_m = row['adv_30d'] / 1_000_000
                vol_pct = row['realized_vol'] * 100
                spread = row['avg_spread_bps']
                print(f"{int(row['rank']):<5} | {sym:<8} | {row['score']:<8.4f} | {row['bucket']:<8} | {adv_m:<15.2f} | {vol_pct:<8.2f} | {spread:<12.2f}")

            # 2nd List: Next Trading Day (Final Selection with Risk Checks)
            print("\n" + "-"*15 + " LIST 2: NEXT TRADING DAY (Final Selection) " + "-"*15)
            print(f"{'Rank':<5} | {'Symbol':<8} | {'Score':<8} | {'Borrow':<8} | {'ADV 30d (M)':<15} | {'NBBO (bps)':<10} | {'Micro-Stab':<10} | {'Earnings':<10}")
            print("-" * 115)
            sorted_universe = sorted(final_universe.items(), key=lambda x: x[1]['rank'])
            for sym, data in sorted_universe:
                metrics = data['metrics']
                risk = data.get('risk', {})
                micro = data.get('micro_stability', {}).get('micro_score', 1.0)
                adv_m = metrics.get('adv_30d', metrics.get('dollar_vol', 0)) / 1_000_000
                nbbo = metrics.get('nbbo_spread_bps', 0)
                borrow = risk.get('borrow', {}).get('status', 'ETB')
                earnings = risk.get('earnings_date', 'None')
                earnings_str = str(earnings) if earnings else "None"
                print(f"{data['rank']:<5} | {sym:<8} | {data['score']:<8.4f} | {borrow:<8} | {adv_m:<15.2f} | {nbbo:<10.2f} | {micro:<10.2f} | {earnings_str:<10}")
            
            # 3rd List: Low Price Opportunities ($2-$20)
            print("\n" + "-"*15 + " LIST 3: LOW PRICE OPPORTUNITIES ($2-$20) " + "-"*15)
            print(f"{'Rank':<5} | {'Symbol':<8} | {'Price':<8} | {'Score':<8} | {'ADV 30d (M)':<15} | {'Vol (%)':<8} | {'Spread (bps)':<12}")
            print("-" * 100)
            low_price_df = features_df[(features_df['close'] >= 2) & (features_df['close'] <= 20)]
            low_price_top = low_price_df.sort_values('score', ascending=False).head(20)
            
            for i, (sym, row) in enumerate(low_price_top.iterrows(), 1):
                adv_m = row['adv_30d'] / 1_000_000
                vol_pct = row['realized_vol'] * 100
                spread = row['avg_spread_bps']
                print(f"{i:<5} | {sym:<8} | {row['close']:<8.2f} | {row['score']:<8.4f} | {adv_m:<15.2f} | {vol_pct:<8.2f} | {spread:<12.2f}")

            print("="*75 + "\n")
            
            return file_path
            
        finally:
            await polygon.close()

    def _load_previous_universe(self) -> Set[str]:
        """Try to load the most recent universe artifact to enable hysteresis"""
        try:
            output_dir = self.config['output']['directory']
            if not os.path.exists(output_dir):
                return set()
            
            files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
            if not files:
                return set()
            
            # Sort by filename (which contains date)
            latest_file = sorted(files)[-1]
            with open(os.path.join(output_dir, latest_file), 'r') as f:
                data = json.load(f)
                return set(data.get('symbols', {}).keys())
        except Exception as e:
            logger.warning(f"Could not load previous universe: {e}")
            return set()

    def _get_next_trading_day(self, date: datetime) -> datetime:
        """Simple holiday-unaware next trading day (skips weekends)"""
        next_day = date + timedelta(days=1)
        while next_day.weekday() >= 5: # 5=Saturday, 6=Sunday
            next_day += timedelta(days=1)
        return next_day

if __name__ == "__main__":
    # Load environment variables from .env
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run Quant Symbol Picker")
    parser.add_argument("--date", type=str, help="YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--config", type=str, default="picker/config.yaml", help="Path to config")
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

