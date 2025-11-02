#!/usr/bin/env python3
"""
Live Data Signal Generation Integration Test
============================================

End-to-end integration test that simulates live data processing with regime-aware
signal generation using real historical data from ClickHouse.

Process Flow:
1. Load raw OHLCV data (TSLA, 2024-12-20, 1min frequency)
2. Process through complete pipeline (Rule 3):
   - Data loading → Indicators → Features → Signals
3. Apply regime-aware processing (Rule 2):
   - Regime detection → Regime-aware indicator adaptation
4. Generate trading signals with regime context

Output:
- Generated signals with regime context and confidence scores

Author: StatArb_Gemini Integration Testing
Phase: Live Data Simulation & Signal Generation
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add core_engine to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class LiveDataSignalGenerationTest:
    """
    Integration test for live data simulation with regime-aware signal generation
    """
    
    def __init__(self):
        self.test_results = {}
        self.signals_generated = []
        self.regime_context = None
        
    async def run_test(self) -> Dict[str, Any]:
        """
        Run complete end-to-end signal generation test
        
        Returns:
            Dict with test results and generated signals
        """
        logger.info("🚀 Starting Live Data Signal Generation Integration Test")
        logger.info("=" * 80)
        
        try:
            # Step 1: Load raw OHLCV data
            logger.info("\n📊 Step 1: Loading raw OHLCV data...")
            raw_data = await self._load_raw_data()
            
            if raw_data is None or raw_data.empty:
                logger.error("❌ No data retrieved - cannot proceed with test")
                return {
                    'status': 'failed',
                    'error': 'No data retrieved from ClickHouse',
                    'signals': []
                }
            
            logger.info(f"✅ Loaded {len(raw_data)} records for TSLA (2024-12-20, 1min)")
            logger.info(f"   Date range: {raw_data.index[0]} to {raw_data.index[-1]}")
            logger.info(f"   Columns: {list(raw_data.columns)}")
            
            # Step 2: Initialize regime engine (Rule 2: Regime-First)
            logger.info("\n🔄 Step 2: Initializing Regime Engine (Rule 2: Regime-First)...")
            regime_engine = await self._initialize_regime_engine()
            
            # Step 3: Detect regime from raw data
            logger.info("\n📈 Step 3: Detecting market regime...")
            regime_context = await self._detect_regime(regime_engine, raw_data)
            self.regime_context = regime_context
            
            if regime_context:
                logger.info(f"✅ Regime detected:")
                logger.info(f"   Primary Regime: {regime_context.get('primary_regime', 'unknown')}")
                logger.info(f"   Volatility Regime: {regime_context.get('volatility_regime', 'unknown')}")
                logger.info(f"   Confidence: {regime_context.get('confidence', 0):.2%}")
            
            # Step 4: Process through pipeline using orchestrator (Rule 3: Data Pipeline)
            # Note: We'll use the orchestrator's data loading (no need to pre-load)
            logger.info("\n⚙️  Step 4: Processing through complete pipeline with orchestrator...")
            enriched_data = await self._process_pipeline_with_orchestrator(regime_engine)
            
            # Step 5: Generate signals with regime awareness
            logger.info("\n📡 Step 5: Generating regime-aware signals...")
            signals = await self._generate_signals(enriched_data, regime_context)
            self.signals_generated = signals
            
            # Step 6: Display results
            logger.info("\n" + "=" * 80)
            logger.info("📊 SIGNAL GENERATION RESULTS")
            logger.info("=" * 80)
            await self._display_results(signals, regime_context)
            
            # Cleanup
            await self._cleanup(regime_engine)
            
            return {
                'status': 'passed',
                'data_points': len(raw_data),
                'regime_context': regime_context,
                'signals': signals,
                'signals_count': len(signals)
            }
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e),
                'signals': []
            }
    
    async def _load_raw_data(self) -> pd.DataFrame:
        """Load raw OHLCV data from ClickHouse"""
        try:
            from core_engine.config import DataConfig
            from core_engine.data.manager import ClickHouseDataManager
            
            # Initialize data manager
            data_config = DataConfig()
            data_manager = ClickHouseDataManager(data_config)
            await data_manager.initialize()
            await data_manager.start()
            
            try:
                # Load data for TSLA on 2024-12-20 at 1min frequency
                start_time = '2024-12-20 09:30:00'
                end_time = '2024-12-20 16:00:00'
                
                logger.info(f"   Loading TSLA data: {start_time} to {end_time}")
                raw_data = data_manager.get_market_data(
                    symbol='TSLA',
                    start_time=start_time,
                    end_time=end_time
                )
                
                return raw_data
                
            finally:
                await data_manager.stop()
                
        except Exception as e:
            logger.error(f"Error loading raw data: {e}")
            return None
    
    async def _initialize_regime_engine(self):
        """Initialize regime engine (Rule 2: Regime-First Principle)"""
        try:
            from core_engine.config import RegimeConfig
            from core_engine.regime.engine import EnhancedRegimeEngine
            
            regime_config = RegimeConfig()
            regime_engine = EnhancedRegimeEngine(regime_config)
            await regime_engine.initialize()
            await regime_engine.start()
            
            logger.info("   ✅ Regime Engine initialized and started")
            return regime_engine
            
        except Exception as e:
            logger.error(f"Error initializing regime engine: {e}")
            raise
    
    async def _detect_regime(self, regime_engine, raw_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect market regime from raw data (now with bar-by-bar regime sequence)"""
        try:
            # Process data through regime engine (now returns regime sequence)
            regime_result = regime_engine.process_market_data(raw_data)
            
            if regime_result and regime_result.get('market_data_processed'):
                # Get regime sequence (bar-by-bar regime tracking)
                regime_sequence = regime_result.get('regime_sequence', [])
                
                # Get current regime context (most recent regime)
                if hasattr(regime_engine, 'current_regime') and regime_engine.current_regime:
                    current_regime = regime_engine.current_regime
                    
                    # Enhanced regime context with sequence information
                    regime_context = {
                        'primary_regime': current_regime.primary_regime.value if hasattr(current_regime.primary_regime, 'value') else str(current_regime.primary_regime),
                        'volatility_regime': current_regime.volatility_regime.value if hasattr(current_regime.volatility_regime, 'value') else str(current_regime.volatility_regime),
                        'confidence': float(current_regime.confidence) if hasattr(current_regime, 'confidence') else 0.0,
                        'regime_id': current_regime.regime_id if hasattr(current_regime, 'regime_id') else None,
                        # CRITICAL: Add regime sequence for regime-aware processing
                        'regime_sequence': regime_sequence,  # Bar-by-bar regime tracking
                        'regime_changes_count': regime_result.get('regime_changes_count', 0),
                        'total_bars_analyzed': regime_result.get('total_bars_analyzed', 0),
                        'warm_up_bars': regime_result.get('warm_up_bars', 0)
                    }
                    
                    if regime_sequence:
                        logger.info(f"   📊 Regime sequence: {len(regime_sequence)} bars analyzed")
                        logger.info(f"   🔄 Regime changes detected: {regime_context['regime_changes_count']}")
                    
                    return regime_context
                else:
                    logger.warning("   ⚠️  Regime detected but no current_regime available")
                    return None
            else:
                logger.warning("   ⚠️  No regime detected from data")
                return None
                
        except Exception as e:
            logger.error(f"Error detecting regime: {e}", exc_info=True)
            return None
    
    async def _process_pipeline_with_orchestrator(self, regime_engine) -> Dict[str, pd.DataFrame]:
        """
        Process data through complete pipeline using ProcessingPipelineOrchestrator (Rule 3):
        Raw OHLCV → Indicators → Features → Signals
        
        **ENHANCED:** Now uses ProcessingPipelineOrchestrator which automatically
        performs regime-segmented processing when regime changes are detected.
        
        Uses LIVE data from ClickHouse (2024-12-20, TSLA, 1min).
        """
        try:
            from core_engine.config import DataConfig, IndicatorConfig, FeatureConfig, SignalConfig
            from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator
            from core_engine.processing.signals.generator import EnhancedSignalGenerator
            
            # Initialize pipeline orchestrator (includes regime-segmented processing)
            # The orchestrator will create its own data_manager in initialize()
            data_config = DataConfig()
            indicator_config = IndicatorConfig()
            feature_config = FeatureConfig()
            signal_config = SignalConfig()
            
            # Initialize pipeline orchestrator
            pipeline = ProcessingPipelineOrchestrator(
                data_config=data_config,
                indicator_config=indicator_config,
                feature_config=feature_config,
                signal_config=signal_config
            )
            
            await pipeline.initialize()
            await pipeline.start()
            
            # Inject regime engine (enables regime-segmented processing)
            pipeline.set_regime_engine(regime_engine)
            
            try:
                # Use LIVE data: TSLA, 2024-12-20, 1min
                start_time = datetime(2024, 12, 20, 9, 30, 0)  # Market open
                end_time = datetime(2024, 12, 20, 16, 0, 0)    # Market close
                
                logger.info("   📊 Processing through pipeline orchestrator (with regime-segmented processing)...")
                logger.info(f"   📅 Loading LIVE data: TSLA, {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
                
                # Process through orchestrator (automatically handles regime-segmented processing)
                # This will load LIVE data from ClickHouse and process it
                enriched_data_dict = await pipeline.process_market_data(
                    symbols=['TSLA'],
                    start_time=start_time,
                    end_time=end_time,
                    timeframe='1min'
                )
                
                if 'TSLA' not in enriched_data_dict:
                    raise ValueError("No enriched data returned from pipeline")
                
                enriched_data = enriched_data_dict['TSLA']
                
                # Extract DataFrames from EnrichedMarketData
                raw_data = enriched_data.raw_data
                indicators_df = enriched_data.indicators
                features_df = enriched_data.features
                signals_df = enriched_data.signals
                
                logger.info(f"   ✅ Pipeline processing complete:")
                logger.info(f"      Raw data: {len(raw_data)} bars")
                logger.info(f"      Indicators: {len(indicators_df)} rows, {len(indicators_df.columns)} columns")
                logger.info(f"      Features: {len(features_df)} rows, {len(features_df.columns)} columns")
                logger.info(f"      Signals DataFrame: {len(signals_df)} rows, {len(signals_df.columns)} columns")
                
                # Generate TradingSignal objects from signals DataFrame
                # (Signal generator is already part of orchestrator, but we need the actual TradingSignal objects)
                signal_generator = EnhancedSignalGenerator(signal_config)
                signal_generator.set_regime_engine(regime_engine)
                trading_signals = signal_generator.generate_signals(features_df)
                
                logger.info(f"   ✅ TradingSignals generated: {len(trading_signals)} TradingSignal objects")
                
                # Check for regime-segmented processing
                if hasattr(pipeline, 'regime_engine') and pipeline.regime_engine:
                    logger.info("   ✅ Regime-segmented processing: ENABLED (config adapts per regime segment)")
                else:
                    logger.info("   ⚠️  Regime-segmented processing: DISABLED (single-segment processing)")
                
                return {
                    'raw': raw_data,
                    'indicators': indicators_df,
                    'features': features_df,
                    'signals': trading_signals,  # List of TradingSignal objects
                    'enriched': signals_df  # Final enriched DataFrame (features + indicators + raw + signals)
                }
                
            finally:
                await pipeline.stop()
                
        except Exception as e:
            logger.error(f"Error processing pipeline: {e}", exc_info=True)
            raise
    
    async def _generate_signals(self, enriched_data: Dict[str, Any], regime_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate final trading signals with regime awareness
        
        Processes the TradingSignal objects from the signal generator
        """
        try:
            trading_signals = enriched_data.get('signals', [])  # List of TradingSignal objects
            features_df = enriched_data.get('enriched', pd.DataFrame())  # Features DataFrame for additional data
            
            # Convert TradingSignal objects to dictionary format
            signals = []
            
            for trading_signal in trading_signals:
                # Get signal type (BUY/SELL)
                signal_type = str(trading_signal.signal_type).upper() if hasattr(trading_signal.signal_type, 'value') else str(trading_signal.signal_type).upper()
                
                # Get strength
                strength_str = str(trading_signal.strength).upper() if hasattr(trading_signal.strength, 'value') else str(trading_signal.strength).upper()
                
                # Get timestamp
                timestamp = trading_signal.timestamp
                if not isinstance(timestamp, (pd.Timestamp, datetime)):
                    timestamp = pd.Timestamp(timestamp)
                
                # Try to get additional data from features DataFrame if available
                raw_data = {}
                if not features_df.empty and 'timestamp' in features_df.columns:
                    # Try to find matching row in features DataFrame
                    matching_rows = features_df[features_df['timestamp'] == timestamp]
                    if not matching_rows.empty:
                        row = matching_rows.iloc[0]
                        raw_data = {
                            'open': float(row['open']) if 'open' in row else None,
                            'high': float(row['high']) if 'high' in row else None,
                            'low': float(row['low']) if 'low' in row else None,
                            'close': float(row['close']) if 'close' in row else None,
                        }
                
                signal = {
                    'timestamp': timestamp,
                    'symbol': trading_signal.symbol,
                    'signal_type': signal_type,
                    'confidence': float(trading_signal.confidence),
                    'strength': strength_str,
                    'price': float(trading_signal.price) if trading_signal.price else None,
                    'target_price': float(trading_signal.target_price) if hasattr(trading_signal, 'target_price') and trading_signal.target_price else None,
                    'stop_loss': float(trading_signal.stop_loss) if hasattr(trading_signal, 'stop_loss') and trading_signal.stop_loss else None,
                    'position_size': float(trading_signal.position_size) if hasattr(trading_signal, 'position_size') and trading_signal.position_size else None,
                    'strategy': trading_signal.strategy if hasattr(trading_signal, 'strategy') else 'unknown',
                    'regime_context': regime_context,
                    'metadata': trading_signal.metadata if hasattr(trading_signal, 'metadata') else {},
                    'raw_data': raw_data
                }
                
                signals.append(signal)
            
            # Sort by timestamp (most recent first)
            signals.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}", exc_info=True)
            return []
    
    async def _display_results(self, signals: List[Dict[str, Any]], regime_context: Dict[str, Any]):
        """Display test results with regime sequence information"""
        logger.info(f"\n📊 Generated {len(signals)} signals")
        
        if regime_context:
            logger.info(f"\n📈 Regime Context:")
            logger.info(f"   Primary Regime: {regime_context.get('primary_regime', 'unknown')}")
            logger.info(f"   Volatility Regime: {regime_context.get('volatility_regime', 'unknown')}")
            logger.info(f"   Confidence: {regime_context.get('confidence', 0):.2%}")
            
            # Display regime sequence information (CRITICAL for regime-aware design)
            regime_sequence = regime_context.get('regime_sequence', [])
            if regime_sequence:
                logger.info(f"\n🔄 Regime Sequence Analysis:")
                logger.info(f"   Total Bars Analyzed: {regime_context.get('total_bars_analyzed', 0)}")
                logger.info(f"   Warm-up Bars: {regime_context.get('warm_up_bars', 0)}")
                logger.info(f"   Regime Changes: {regime_context.get('regime_changes_count', 0)}")
                
                # Show regime transitions
                if regime_context.get('regime_changes_count', 0) > 0:
                    logger.info(f"\n   📊 Regime Transitions Detected:")
                    current_regime = None
                    transition_start = None
                    for regime_entry in regime_sequence:
                        if regime_entry.get('regime_changed') and current_regime:
                            logger.info(
                                f"      {transition_start} → {regime_entry['timestamp']}: "
                                f"{current_regime} → {regime_entry['regime']}"
                            )
                        if regime_entry.get('regime_changed'):
                            transition_start = regime_entry['timestamp']
                        current_regime = regime_entry['regime']
                
                # Show regime distribution
                regime_counts = {}
                for regime_entry in regime_sequence:
                    regime = regime_entry['regime']
                    regime_counts[regime] = regime_counts.get(regime, 0) + 1
                
                if regime_counts:
                    logger.info(f"\n   📊 Regime Distribution:")
                    for regime, count in sorted(regime_counts.items(), key=lambda x: x[1], reverse=True):
                        pct = (count / len(regime_sequence)) * 100
                        logger.info(f"      {regime}: {count} bars ({pct:.1f}%)")
        
        if signals:
            logger.info(f"\n📡 Top 10 Most Recent Signals:")
            logger.info("-" * 100)
            logger.info(f"{'Timestamp':<20} {'Type':<8} {'Price':<10} {'Confidence':<12} {'Strength':<10} {'Strategy':<15}")
            logger.info("-" * 100)
            
            for signal in signals[:10]:
                timestamp_str = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(signal['timestamp'], 'strftime') else str(signal['timestamp'])
                signal_type = signal['signal_type']
                price = f"${signal['price']:.2f}" if signal.get('price') else "N/A"
                confidence = f"{signal['confidence']:.2%}"
                strength = signal.get('strength', 'N/A')
                strategy = signal.get('strategy', 'N/A')
                
                logger.info(f"{timestamp_str:<20} {signal_type:<8} {price:<10} {confidence:<12} {strength:<10} {strategy:<15}")
            
            # Signal statistics
            signal_types = {}
            for signal in signals:
                sig_type = signal['signal_type']
                signal_types[sig_type] = signal_types.get(sig_type, 0) + 1
            
            logger.info("\n📊 Signal Statistics:")
            for sig_type, count in signal_types.items():
                logger.info(f"   {sig_type}: {count}")
            
            avg_confidence = np.mean([s['confidence'] for s in signals])
            logger.info(f"\n   Average Confidence: {avg_confidence:.2%}")
        else:
            logger.warning("   ⚠️  No signals generated")
    
    async def _cleanup(self, regime_engine):
        """Cleanup resources"""
        try:
            if regime_engine:
                await regime_engine.stop()
                logger.info("   ✅ Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """Main function to run the integration test"""
    test = LiveDataSignalGenerationTest()
    
    try:
        results = await test.run_test()
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Status: {results['status'].upper()}")
        
        if results['status'] == 'passed':
            logger.info(f"✅ Test PASSED")
            logger.info(f"   Data Points: {results['data_points']}")
            logger.info(f"   Signals Generated: {results['signals_count']}")
            
            if results['regime_context']:
                logger.info(f"   Regime: {results['regime_context'].get('primary_regime', 'unknown')}")
                logger.info(f"   Confidence: {results['regime_context'].get('confidence', 0):.2%}")
        else:
            logger.error(f"❌ Test FAILED")
            logger.error(f"   Error: {results.get('error', 'Unknown error')}")
        
        # Exit with appropriate code
        return 0 if results['status'] == 'passed' else 1
        
    except Exception as e:
        logger.error(f"💥 Test runner failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

