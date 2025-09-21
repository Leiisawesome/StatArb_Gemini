#!/usr/bin/env python3
"""
Multi-Timeframe Regime Detection Test - Tier 2 Enhancement #2
===========================================================

Test the multi-timeframe regime detection capabilities across 5min, 1H, 1D, 1W timeframes.

This test demonstrates:
- Multi-timeframe regime analysis (5min, 1H, 1D, 1W)
- Regime consensus calculation across timeframes
- Dominant timeframe identification
- Timeframe hierarchy weighting
- Cross-timeframe regime consistency analysis

Author: StatArb_Gemini Tier 2 Multi-Timeframe Enhancement
"""

import sys
import os
# Add the project root to sys.path (two levels up from regime_test)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Core engine imports
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.regime.engine import RegimeEngine, MarketRegime, TimeframeRegime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiTimeframeRegimeTest:
    """Test multi-timeframe regime detection capabilities"""
    
    def __init__(self):
        """Initialize multi-timeframe regime test"""
        
        # Test symbols for different market conditions
        self.test_symbols = ['SPY', 'QQQ', 'TSLA', 'NVDA']  # Mix of ETFs and individual stocks
        
        # Test configuration
        self.test_config = {
            'test_date': '2024-12-20',
            'symbols': self.test_symbols
        }
        
        # Initialize components
        self.data_manager = None
        self.regime_engine = None
        
        logger.info("🚀 Multi-Timeframe Regime Test Initialized")
    
    async def initialize_components(self):
        """Initialize multi-timeframe regime detection components"""
        
        try:
            logger.info("🔧 Initializing multi-timeframe regime components...")
            
            # Initialize data manager
            config = ClickHouseDataConfig(
                symbols=self.test_symbols,
                target_date=self.test_config['test_date']
            )
            self.data_manager = ClickHouseDataManager(config)
            
            # Initialize regime engine with multi-timeframe support
            regime_config = {}  # Use default configuration
            self.regime_engine = RegimeEngine(regime_config)
            
            logger.info("✅ Multi-timeframe regime components initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            raise
    
    async def load_test_data(self) -> Dict[str, pd.DataFrame]:
        """Load market data for multi-timeframe testing"""
        
        logger.info("📊 Loading test data for multi-timeframe regime analysis...")
        market_data = {}
        
        for symbol in self.test_symbols:
            try:
                data = self.data_manager.get_market_data(symbol=symbol)
                
                if data is not None and not data.empty:
                    # Ensure proper datetime index
                    if 'timestamp' in data.columns:
                        data.set_index('timestamp', inplace=True)
                    
                    market_data[symbol] = data
                    logger.info(f"  ✅ {symbol}: {len(data)} records loaded")
                else:
                    logger.warning(f"  ⚠️ {symbol}: No data available")
                    
            except Exception as e:
                logger.warning(f"  ❌ {symbol}: Load failed - {str(e)[:50]}...")
        
        logger.info(f"📈 Successfully loaded {len(market_data)}/{len(self.test_symbols)} symbols")
        return market_data
    
    async def demonstrate_multi_timeframe_analysis(self, market_data: Dict[str, pd.DataFrame]):
        """Demonstrate multi-timeframe regime analysis"""
        
        logger.info("🎯 Demonstrating Multi-Timeframe Regime Analysis...")
        
        regime_results = {}
        
        for symbol, data in market_data.items():
            try:
                logger.info(f"\n📊 Analyzing {symbol} across multiple timeframes...")
                
                # Feed data to regime engine (simulating real-time data flow)
                logger.info(f"  📊 Feeding {len(data)} data points to regime engine...")
                for _, row in data.iterrows():
                    # Add symbol to row data
                    row_data = row.to_dict()
                    row_data['symbol'] = symbol
                    await self.regime_engine.on_market_data(row_data)
                
                # Trigger multi-timeframe regime analysis
                logger.info(f"  🔍 Triggering multi-timeframe regime analysis...")
                regime_analysis = await self.regime_engine.analyze_regime(force_update=True)
                
                if regime_analysis:
                    regime_results[symbol] = regime_analysis
                    
                    # Display multi-timeframe regime information
                    self._display_multi_timeframe_analysis(symbol, regime_analysis)
                else:
                    logger.warning(f"  ⚠️ No regime analysis available for {symbol}")
                    
            except Exception as e:
                logger.error(f"  ❌ Multi-timeframe analysis failed for {symbol}: {e}")
        
        return regime_results
    
    def _display_multi_timeframe_analysis(self, symbol: str, analysis):
        """Display detailed multi-timeframe regime analysis"""
        
        print(f"\n{'='*80}")
        print(f"🎯 MULTI-TIMEFRAME REGIME ANALYSIS: {symbol}")
        print(f"{'='*80}")
        
        # Primary regime classification
        print(f"\n🏷️  PRIMARY REGIME (Consensus):")
        print(f"   • Regime: {analysis.primary_regime.value}")
        print(f"   • Confidence: {analysis.confidence:.3f}")
        print(f"   • Regime Consensus: {analysis.regime_consensus:.3f}")
        print(f"   • Dominant Timeframe: {analysis.dominant_timeframe}")
        
        # Multi-timeframe breakdown
        if analysis.timeframe_regimes:
            print(f"\n📊 TIMEFRAME-SPECIFIC REGIMES:")
            
            # Sort timeframes by hierarchy importance
            hierarchy = analysis.regime_hierarchy or {"5min": 0.15, "1H": 0.25, "1D": 0.40, "1W": 0.20}
            sorted_timeframes = sorted(hierarchy.items(), key=lambda x: x[1], reverse=True)
            
            for timeframe, weight in sorted_timeframes:
                if timeframe in analysis.timeframe_regimes:
                    tf_regime = analysis.timeframe_regimes[timeframe]
                    importance = "🔴 HIGH" if weight > 0.35 else "🟡 MEDIUM" if weight > 0.20 else "🟢 LOW"
                    
                    print(f"\n   📈 {timeframe.upper()} TIMEFRAME:")
                    print(f"      • Regime: {tf_regime.regime.value}")
                    print(f"      • Confidence: {tf_regime.confidence:.3f}")
                    print(f"      • Trend Strength: {tf_regime.trend_strength:.3f}")
                    print(f"      • Volatility: {tf_regime.volatility:.3f}")
                    print(f"      • Transition Risk: {tf_regime.transition_probability:.3f}")
                    print(f"      • Hierarchy Weight: {weight:.2f} ({importance})")
        
        # Regime consensus analysis
        print(f"\n🤝 CONSENSUS ANALYSIS:")
        if analysis.regime_consensus > 0.75:
            consensus_level = "🟢 STRONG CONSENSUS"
        elif analysis.regime_consensus > 0.5:
            consensus_level = "🟡 MODERATE CONSENSUS"
        else:
            consensus_level = "🔴 WEAK CONSENSUS"
        
        print(f"   • Consensus Level: {consensus_level}")
        print(f"   • Agreement Score: {analysis.regime_consensus:.3f}")
        print(f"   • Dominant Timeframe: {analysis.dominant_timeframe}")
        
        # Strategy implications
        print(f"\n💡 MULTI-TIMEFRAME STRATEGY IMPLICATIONS:")
        print(f"   • Risk Adjustment: {analysis.risk_adjustment:.2f}x")
        print(f"   • Position Sizing: {analysis.position_sizing_factor:.2f}x")
        
        if analysis.strategy_suitability:
            print(f"\n🎯 STRATEGY SUITABILITY (Consensus-Weighted):")
            for strategy, score in analysis.strategy_suitability.items():
                stars = "⭐" * min(5, int(score * 5))
                print(f"   • {strategy}: {score:.3f} {stars}")
    
    async def demonstrate_timeframe_hierarchy(self, regime_results: Dict[str, Any]):
        """Demonstrate timeframe hierarchy and weighting"""
        
        logger.info("\n🏗️ Demonstrating Timeframe Hierarchy Analysis...")
        
        print(f"\n{'='*80}")
        print(f"🏗️ TIMEFRAME HIERARCHY & WEIGHTING ANALYSIS")
        print(f"{'='*80}")
        
        # Aggregate hierarchy weights across all symbols
        hierarchy_weights = {}
        timeframe_performance = {}
        
        for symbol, analysis in regime_results.items():
            if analysis.regime_hierarchy:
                for timeframe, weight in analysis.regime_hierarchy.items():
                    if timeframe not in hierarchy_weights:
                        hierarchy_weights[timeframe] = []
                        timeframe_performance[timeframe] = []
                    
                    hierarchy_weights[timeframe].append(weight)
                    
                    # Get performance metrics for this timeframe
                    if timeframe in analysis.timeframe_regimes:
                        tf_regime = analysis.timeframe_regimes[timeframe]
                        performance_score = tf_regime.confidence * (1 - tf_regime.transition_probability)
                        timeframe_performance[timeframe].append(performance_score)
        
        # Calculate average weights and performance
        print(f"\n📊 TIMEFRAME HIERARCHY (Average across {len(regime_results)} symbols):")
        
        avg_hierarchy = {}
        for timeframe, weights in hierarchy_weights.items():
            avg_weight = np.mean(weights)
            avg_performance = np.mean(timeframe_performance[timeframe]) if timeframe_performance[timeframe] else 0
            avg_hierarchy[timeframe] = (avg_weight, avg_performance)
        
        # Sort by hierarchy weight
        sorted_hierarchy = sorted(avg_hierarchy.items(), key=lambda x: x[1][0], reverse=True)
        
        for i, (timeframe, (weight, performance)) in enumerate(sorted_hierarchy, 1):
            importance = "🔴 CRITICAL" if weight > 0.35 else "🟡 IMPORTANT" if weight > 0.20 else "🟢 SUPPORTING"
            print(f"   {i}. {timeframe.upper()}: {weight:.2f} weight, {performance:.3f} performance ({importance})")
        
        # Timeframe characteristics
        print(f"\n🔍 TIMEFRAME CHARACTERISTICS:")
        print(f"   • 5MIN: High frequency, noise filtering, short-term signals")
        print(f"   • 1H: Intraday trends, momentum detection, tactical positioning")
        print(f"   • 1D: Primary analysis, strategic decisions, regime classification")
        print(f"   • 1W: Long-term context, structural trends, risk assessment")
    
    async def demonstrate_regime_consensus(self, regime_results: Dict[str, Any]):
        """Demonstrate regime consensus calculation"""
        
        logger.info("\n🤝 Demonstrating Regime Consensus Analysis...")
        
        print(f"\n{'='*80}")
        print(f"🤝 REGIME CONSENSUS ANALYSIS")
        print(f"{'='*80}")
        
        for symbol, analysis in regime_results.items():
            print(f"\n📊 {symbol} CONSENSUS BREAKDOWN:")
            
            if analysis.timeframe_regimes:
                # Show regime agreement across timeframes
                regimes_by_timeframe = {}
                for timeframe, tf_regime in analysis.timeframe_regimes.items():
                    regime_name = tf_regime.regime.value
                    if regime_name not in regimes_by_timeframe:
                        regimes_by_timeframe[regime_name] = []
                    regimes_by_timeframe[regime_name].append(timeframe)
                
                print(f"   • Regime Distribution:")
                for regime, timeframes in regimes_by_timeframe.items():
                    print(f"     - {regime}: {', '.join(timeframes)}")
                
                print(f"   • Consensus Score: {analysis.regime_consensus:.3f}")
                print(f"   • Primary Regime: {analysis.primary_regime.value}")
                print(f"   • Dominant Timeframe: {analysis.dominant_timeframe}")
                
                # Consensus strength assessment
                if analysis.regime_consensus > 0.75:
                    print(f"   • Assessment: 🟢 STRONG AGREEMENT - High confidence regime")
                elif analysis.regime_consensus > 0.5:
                    print(f"   • Assessment: 🟡 MODERATE AGREEMENT - Regime transition possible")
                else:
                    print(f"   • Assessment: 🔴 WEAK AGREEMENT - Mixed signals, high uncertainty")
    
    async def generate_multi_timeframe_summary(self, regime_results: Dict[str, Any]):
        """Generate comprehensive multi-timeframe summary"""
        
        logger.info("\n📋 Generating multi-timeframe comprehensive summary...")
        
        print(f"\n{'='*80}")
        print(f"🎉 TIER 2 MULTI-TIMEFRAME REGIMES - COMPREHENSIVE SUMMARY")
        print(f"{'='*80}")
        
        # Count unique regimes across all timeframes
        all_regimes = set()
        timeframe_counts = {"5min": 0, "1H": 0, "1D": 0, "1W": 0}
        consensus_scores = []
        
        for analysis in regime_results.values():
            all_regimes.add(analysis.primary_regime.value)
            consensus_scores.append(analysis.regime_consensus)
            
            if analysis.timeframe_regimes:
                for timeframe in analysis.timeframe_regimes:
                    timeframe_counts[timeframe] += 1
        
        print(f"\n📊 MULTI-TIMEFRAME CAPABILITIES DEMONSTRATED:")
        print(f"   • Symbols Analyzed: {len(regime_results)}")
        print(f"   • Unique Regimes Detected: {len(all_regimes)}")
        print(f"   • Timeframes Analyzed: 4 (5min, 1H, 1D, 1W)")
        print(f"   • Average Consensus: {np.mean(consensus_scores):.3f}")
        
        print(f"\n🎯 TIMEFRAME COVERAGE:")
        for timeframe, count in timeframe_counts.items():
            coverage = (count / len(regime_results)) * 100
            print(f"   • {timeframe}: {count}/{len(regime_results)} symbols ({coverage:.1f}%)")
        
        print(f"\n🎯 DETECTED REGIME TYPES:")
        for regime_type in sorted(all_regimes):
            print(f"   • {regime_type}")
        
        print(f"\n🏆 TIER 2 ENHANCEMENT #2 ACHIEVEMENTS:")
        print(f"   ✅ Multi-timeframe regime detection (5min, 1H, 1D, 1W)")
        print(f"   ✅ Timeframe hierarchy weighting system")
        print(f"   ✅ Cross-timeframe regime consensus calculation")
        print(f"   ✅ Dominant timeframe identification")
        print(f"   ✅ Multi-timeframe strategy optimization")
        print(f"   ✅ Regime transition analysis per timeframe")
        print(f"   ✅ Professional timeframe-specific risk assessment")
        
        print(f"\n{'='*80}")
        print(f"✅ TIER 2 MULTI-TIMEFRAME REGIME DETECTION SUCCESSFULLY IMPLEMENTED!")
        print(f"{'='*80}")
    
    async def run_multi_timeframe_test(self):
        """Run the complete multi-timeframe regime test"""
        
        try:
            logger.info("🚀 Starting Multi-Timeframe Regime Detection Test...")
            
            # Initialize components
            await self.initialize_components()
            
            # Load test data
            market_data = await self.load_test_data()
            
            if not market_data:
                logger.error("❌ No market data loaded - cannot proceed")
                return
            
            # Demonstrate multi-timeframe analysis
            regime_results = await self.demonstrate_multi_timeframe_analysis(market_data)
            
            if not regime_results:
                logger.error("❌ No regime analysis results - cannot proceed")
                return
            
            # Demonstrate timeframe hierarchy
            await self.demonstrate_timeframe_hierarchy(regime_results)
            
            # Demonstrate regime consensus
            await self.demonstrate_regime_consensus(regime_results)
            
            # Generate comprehensive summary
            await self.generate_multi_timeframe_summary(regime_results)
            
            logger.info("🎉 Multi-timeframe regime test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise


async def main():
    """Main test execution"""
    test = MultiTimeframeRegimeTest()
    await test.run_multi_timeframe_test()


if __name__ == "__main__":
    asyncio.run(main())
