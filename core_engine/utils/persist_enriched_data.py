#!/usr/bin/env python3
"""
Persist Enriched Market Data Utility
====================================

Utility script to process market data through the full pipeline (Phase 0-4)
and persist the resulting EnrichedDataFrame to a CSV file.

Usage:
    python core_engine/utils/persist_enriched_data.py --symbol TSLA --date 2024-12-20

Author: StatArb_Gemini
Version: 1.0.0
"""

import os
import asyncio
import logging
import argparse
import pandas as pd
from datetime import datetime, time
from pathlib import Path

# Core Engine Imports
from core_engine.config.unified_config import init_config, get_config
from core_engine.config.component_config import (
    DataConfig, IndicatorConfig, FeatureConfig, SignalConfig, RegimeConfig,
    ConnectionConfig, CachingConfig
)
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.data.liquidity_engine import LiquidityAssessmentEngine
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import EnhancedFeatureEngineer
from core_engine.processing.signals.generator import EnhancedSignalGenerator
from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PersistEnrichedData")

async def persist_enriched_data(symbol: str, target_date: str, output_dir: str):
    """
    Process and persist enriched data for a specific symbol and date.
    """
    logger.info(f"🚀 Starting data persistence for {symbol} on {target_date}")
    
    # 1. Initialize Configuration
    # Load base config and smoke_test config for environment settings
    config_dir = Path("backtest/configs")
    unified_config = init_config(config_dir)
    
    # Add smoke_test.yaml as a source to get the correct environment/ClickHouse settings
    smoke_test_path = config_dir / "smoke_test.yaml"
    if smoke_test_path.exists():
        logger.info(f"Loading additional config from {smoke_test_path}")
        unified_config.add_source(smoke_test_path, priority=100)
        unified_config.reload()
    
    # 2. Extract Component Configs
    # We use the centralized config classes which can be initialized from dicts
    data_cfg_dict = unified_config.get_section("data")
    regime_cfg_dict = unified_config.get_section("regime")
    indicator_cfg_dict = unified_config.get_section("indicators")
    feature_cfg_dict = unified_config.get_section("features")
    signal_cfg_dict = unified_config.get_section("signals")
    
    # Initialize dataclass configs (handling potential empty dicts with defaults)
    # DataConfig has nested sub-configs, so we need to handle them if present in dict
    def init_data_config(cfg_dict):
        if not cfg_dict: return DataConfig()
        
        # Extract sub-configs if they exist as dicts
        conn_dict = cfg_dict.pop("connection", {})
        cache_dict = cfg_dict.pop("caching", {})
        
        # Create sub-configs
        conn_cfg = ConnectionConfig(**conn_dict) if conn_dict else ConnectionConfig()
        cache_cfg = CachingConfig(**cache_dict) if cache_dict else CachingConfig()
        
        # Create main config with remaining items
        return DataConfig(connection=conn_cfg, caching=cache_cfg, **cfg_dict)

    data_config = init_data_config(data_cfg_dict)
    regime_config = RegimeConfig(**regime_cfg_dict) if regime_cfg_dict else RegimeConfig()
    indicator_config = IndicatorConfig(**indicator_cfg_dict) if indicator_cfg_dict else IndicatorConfig()
    feature_config = FeatureConfig(**feature_cfg_dict) if feature_cfg_dict else FeatureConfig()
    signal_config = SignalConfig(**signal_cfg_dict) if signal_cfg_dict else SignalConfig()
    
    # 3. Initialize Engines
    logger.info("Initializing engines...")
    
    data_manager = ClickHouseDataManager(data_config)
    regime_engine = EnhancedRegimeEngine(regime_config)
    liquidity_engine = LiquidityAssessmentEngine() # Uses default config or can be extended
    
    indicators_engine = EnhancedTechnicalIndicators(indicator_config)
    feature_engineer = EnhancedFeatureEngineer(feature_config)
    signal_generator = EnhancedSignalGenerator(signal_config)
    
    # 4. Initialize Orchestrator
    pipeline = ProcessingPipelineOrchestrator(
        data_config=data_config,
        indicator_config=indicator_config,
        feature_config=feature_config,
        signal_config=signal_config
    )
    
    # Inject dependencies (Rule 2 & 3)
    pipeline.data_manager = data_manager
    pipeline.set_regime_engine(regime_engine)
    pipeline.set_liquidity_engine(liquidity_engine)
    pipeline.indicators_engine = indicators_engine
    pipeline.feature_engineer = feature_engineer
    pipeline.signal_generator = signal_generator
    
    # Initialize all components
    await pipeline.initialize()
    await pipeline.start()
    
    # 5. Process Data
    # Define time range for the specific date
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    start_time = datetime.combine(dt, time.min)
    end_time = datetime.combine(dt, time.max)
    
    logger.info(f"Processing pipeline for {symbol} from {start_time} to {end_time}...")
    
    enriched_results = await pipeline.process_market_data(
        symbols=[symbol],
        start_time=start_time,
        end_time=end_time,
        timeframe="1min"
    )
    
    if symbol not in enriched_results:
        logger.error(f"❌ Failed to get enriched data for {symbol}")
        return
    
    # 6. Extract and Persist
    enriched_data = enriched_results[symbol]
    df = enriched_data.get_enriched_dataframe()
    
    if df.empty:
        logger.warning(f"⚠️  Enriched DataFrame is empty for {symbol}")
        return

    # ENHANCEMENT: Add signal scores to the DataFrame for persistence
    # Since the orchestrator doesn't merge them into the DataFrame, we do it here
    logger.info("Adding signal scores to DataFrame...")
    try:
        mean_rev_scores = signal_generator._generate_mean_reversion_signals(df)
        momentum_scores = signal_generator._generate_momentum_signals(df)
        volume_scores = signal_generator._generate_volume_signals(df)
        
        if 'mean_reversion_score' in mean_rev_scores.columns:
            df['signal_mean_reversion_score'] = mean_rev_scores['mean_reversion_score']
        if 'momentum_score' in momentum_scores.columns:
            df['signal_momentum_score'] = momentum_scores['momentum_score']
        if 'volume_score' in volume_scores.columns:
            df['signal_volume_score'] = volume_scores['volume_score']
            
        logger.info(f"Added signal scores: MR, Momentum, Volume")
    except Exception as e:
        logger.warning(f"Could not add signal scores: {e}")
    
    # Ensure output directory exists
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    file_name = f"{symbol.lower()}_enriched_{target_date.replace('-', '')}.csv"
    full_path = out_path / file_name
    
    logger.info(f"💾 Persisting {len(df)} rows to {full_path}")
    df.to_csv(full_path, index=False)
    
    # Also save a summary for verification
    summary = enriched_data.get_summary()
    logger.info(f"✅ Processing Summary: {summary}")
    
    logger.info("✨ Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Persist Enriched Market Data")
    parser.add_argument("--symbol", type=str, default="TSLA", help="Ticker symbol")
    parser.add_argument("--date", type=str, default="2024-12-20", help="Date in YYYY-MM-DD format")
    parser.add_argument("--output", type=str, default="backtest/results", help="Output directory")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(persist_enriched_data(args.symbol, args.date, args.output))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
