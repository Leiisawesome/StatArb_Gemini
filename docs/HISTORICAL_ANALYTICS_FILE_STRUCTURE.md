# Historical Analytics File Structure
# ==================================

## 📁 **Proposed Directory Structure**

```
core_structure/
├── analytics/
│   ├── __init__.py
│   ├── market_condition_analytics.py          # Existing (validated)
│   └── historical_analytics/                  # NEW MODULE
│       ├── __init__.py
│       ├── engine.py                         # Main HistoricalMarketAnalyticsEngine
│       ├── data_ingestion.py                 # HistoricalDataManager
│       ├── regime_analyzer.py                # HistoricalRegimeAnalyzer  
│       ├── instrument_optimizer.py           # StrategyInstrumentOptimizer
│       ├── output_manager.py                 # HistoricalAnalyticsOutputManager
│       ├── clustering.py                     # RegimeClusteringEngine
│       ├── performance_calculator.py         # PerformanceCalculator
│       └── types.py                          # Data classes and types
│
├── integration/                               # NEW MODULE
│   ├── __init__.py
│   ├── historical_analytics_backtest_bridge.py
│   ├── backtest_config_generator.py
│   └── performance_comparator.py
│
outputs/                                       # NEW DIRECTORY
├── historical_analytics/
│   ├── regime_analysis/
│   ├── instrument_rankings/
│   ├── backtest_configs/
│   └── metadata/
│
tests/
├── integration/
│   ├── test_historical_analytics_integration.py
│   └── test_backtest_integration.py
└── unit/
    ├── test_historical_regime_analyzer.py
    ├── test_instrument_optimizer.py
    └── test_output_manager.py
```

## 🏗️ **Core Implementation Files**

### **1. Main Engine (engine.py)**
```python
#!/usr/bin/env python3
"""
Historical Market Analytics Engine
=================================

Production-ready engine for comprehensive historical market condition analysis.
Transforms validated demo components into a robust analytics framework.

Author: StatArb Gemini Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging

from .data_ingestion import HistoricalDataManager, HistoricalPeriod, MarketDataset
from .regime_analyzer import HistoricalRegimeAnalyzer, RegimeAnalysisOutput
from .instrument_optimizer import StrategyInstrumentOptimizer, InstrumentRankings
from .output_manager import HistoricalAnalyticsOutputManager, AnalysisOutputPaths, RankingsOutputPaths
from .types import AnalysisResults

logger = logging.getLogger(__name__)


class HistoricalMarketAnalyticsEngine:
    """
    Main engine for historical market condition analytics.
    
    Coordinates the complete pipeline:
    1. Historical data ingestion
    2. Regime analysis and clustering
    3. Instrument optimization per strategy/regime
    4. Output persistence
    5. Backtest configuration generation
    """
    
    def __init__(self, 
                 clickhouse_manager=None,
                 output_directory: str = "outputs/historical_analytics"):
        """Initialize the historical analytics engine"""
        
        # Core components
        self.data_manager = HistoricalDataManager(clickhouse_manager)
        self.regime_analyzer = HistoricalRegimeAnalyzer()
        self.instrument_optimizer = StrategyInstrumentOptimizer()
        self.output_manager = HistoricalAnalyticsOutputManager(output_directory)
        
        # Analysis state
        self.analysis_periods = []
        self.analysis_results = None
        
        logger.info("🏗️ Historical Market Analytics Engine initialized")
    
    async def run_comprehensive_analysis(self, 
                                       custom_periods: Optional[List[HistoricalPeriod]] = None) -> AnalysisResults:
        """
        Execute complete historical analytics pipeline
        
        Args:
            custom_periods: Optional custom analysis periods. If None, uses default comprehensive periods.
            
        Returns:
            AnalysisResults containing all outputs and metadata
        """
        try:
            logger.info("🚀 Starting comprehensive historical market analysis...")
            start_time = datetime.now()
            
            # Step 1: Define analysis periods
            if custom_periods is None:
                periods = self.data_manager.define_analysis_periods()
            else:
                periods = custom_periods
            
            logger.info(f"📊 Analyzing {len(periods)} historical periods")
            
            # Step 2: Ingest historical data for all periods
            logger.info("📥 Ingesting historical market data...")
            datasets = []
            total_data_points = 0
            
            for period in periods:
                dataset = await self.data_manager.ingest_period_data(period)
                datasets.append(dataset)
                total_data_points += dataset.total_data_points
                
                logger.info(f"   ✅ {period.name}: {dataset.total_data_points:,} data points")
            
            logger.info(f"📈 Total data points ingested: {total_data_points:,}")
            
            # Step 3: Analyze regimes across all periods
            logger.info("🧠 Performing comprehensive regime analysis...")
            regime_analysis = await self.regime_analyzer.analyze_comprehensive_regimes(datasets)
            
            logger.info(f"   📊 Regime distribution calculated across {len(regime_analysis.regime_results)} periods")
            logger.info(f"   🎯 Average regime confidence: {self._calculate_avg_confidence(regime_analysis):.1%}")
            
            # Step 4: Optimize instruments per strategy per regime
            logger.info("⚡ Optimizing instrument rankings...")
            instrument_rankings = await self.instrument_optimizer.optimize_instruments_per_regime(
                regime_analysis=regime_analysis,
                datasets=datasets
            )
            
            strategies_count = len(instrument_rankings.strategy_rankings)
            regimes_count = len(next(iter(instrument_rankings.strategy_rankings.values())))
            logger.info(f"   🎯 Generated rankings for {strategies_count} strategies across {regimes_count} regimes")
            
            # Step 5: Persist all results
            logger.info("💾 Persisting analysis results...")
            analysis_paths = await self.output_manager.persist_regime_analysis(regime_analysis)
            rankings_paths = await self.output_manager.persist_instrument_rankings(instrument_rankings)
            
            logger.info(f"   📁 Regime analysis saved: {analysis_paths.timestamp}")
            logger.info(f"   📁 Instrument rankings saved: {rankings_paths.timestamp}")
            
            # Step 6: Generate backtest configurations
            logger.info("🔧 Generating optimized backtest configurations...")
            from ..integration.historical_analytics_backtest_bridge import HistoricalAnalyticsBacktestBridge
            
            backtest_bridge = HistoricalAnalyticsBacktestBridge()
            backtest_suite = await backtest_bridge.generate_optimized_backtest_suite(
                analysis_paths=analysis_paths,
                rankings_paths=rankings_paths
            )
            
            logger.info(f"   ⚙️ Generated {len(backtest_suite.optimized_configs)} optimized backtest configs")
            logger.info(f"   📋 Generated {len(backtest_suite.baseline_configs)} baseline backtest configs")
            
            # Compile final results
            execution_time = datetime.now() - start_time
            
            analysis_results = AnalysisResults(
                regime_analysis=regime_analysis,
                instrument_rankings=instrument_rankings,
                analysis_paths=analysis_paths,
                rankings_paths=rankings_paths,
                backtest_suite=backtest_suite,
                execution_metadata={
                    "analysis_date": start_time,
                    "execution_time_seconds": execution_time.total_seconds(),
                    "total_periods_analyzed": len(periods),
                    "total_data_points": total_data_points,
                    "engine_version": "1.0.0"
                }
            )
            
            self.analysis_results = analysis_results
            
            logger.info(f"✅ Historical market analysis completed in {execution_time.total_seconds():.1f} seconds")
            logger.info(f"📊 Results available in: {analysis_paths.regime_distribution.parent}")
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive historical analysis: {e}")
            raise
    
    def _calculate_avg_confidence(self, regime_analysis: RegimeAnalysisOutput) -> float:
        """Calculate average confidence across all regime detections"""
        if not regime_analysis.regime_results:
            return 0.0
        
        return sum(r.confidence for r in regime_analysis.regime_results) / len(regime_analysis.regime_results)
    
    async def get_regime_summary(self) -> Dict[str, Any]:
        """Get summary of regime analysis results"""
        if not self.analysis_results:
            raise ValueError("No analysis results available. Run comprehensive analysis first.")
        
        regime_analysis = self.analysis_results.regime_analysis
        
        return {
            "regime_distribution": {
                regime: {
                    "frequency": stats.frequency,
                    "avg_confidence": stats.avg_confidence,
                    "avg_duration_days": stats.avg_duration_days
                }
                for regime, stats in regime_analysis.regime_distribution.items()
            },
            "total_periods": len(regime_analysis.regime_results),
            "avg_confidence": self._calculate_avg_confidence(regime_analysis),
            "analysis_date": self.analysis_results.execution_metadata["analysis_date"]
        }
    
    async def get_top_instruments_by_strategy(self, strategy: str, regime: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get top N instruments for a specific strategy in a specific regime"""
        if not self.analysis_results:
            raise ValueError("No analysis results available. Run comprehensive analysis first.")
        
        rankings = self.analysis_results.instrument_rankings
        
        if strategy not in rankings.strategy_rankings:
            raise ValueError(f"Strategy '{strategy}' not found in rankings")
        
        if regime not in rankings.strategy_rankings[strategy]:
            raise ValueError(f"Regime '{regime}' not found for strategy '{strategy}'")
        
        instruments = rankings.strategy_rankings[strategy][regime][:top_n]
        
        return [
            {
                "symbol": inst.symbol,
                "score": inst.composite_score,
                "expected_return": inst.expected_return,
                "sharpe_ratio": inst.sharpe_ratio,
                "max_drawdown": inst.max_drawdown
            }
            for inst in instruments
        ]


# Convenience function for quick analysis
async def run_historical_analysis(periods: Optional[List[HistoricalPeriod]] = None) -> AnalysisResults:
    """
    Convenience function to run complete historical analysis
    
    Usage:
        results = await run_historical_analysis()
        print(f"Analysis completed: {len(results.regime_analysis.regime_results)} periods analyzed")
    """
    engine = HistoricalMarketAnalyticsEngine()
    return await engine.run_comprehensive_analysis(custom_periods=periods)
```

### **2. Types and Data Classes (types.py)**
```python
#!/usr/bin/env python3
"""
Data types and classes for historical analytics
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd

from ..market_condition_analytics import MarketCondition, StrategyType


@dataclass
class HistoricalPeriod:
    """Represents a historical analysis period"""
    name: str
    start_date: str
    end_date: str
    regime_hint: Optional[str] = None  # Expected regime for validation
    
    @property
    def duration_days(self) -> int:
        """Calculate duration in days"""
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        return (end - start).days


@dataclass
class MarketDataset:
    """Market data for a specific historical period"""
    period: HistoricalPeriod
    market_data: pd.DataFrame
    macro_data: Dict[str, Any]
    sentiment_data: Dict[str, Any]
    total_data_points: int


@dataclass
class RegimeStats:
    """Statistical information about a market regime"""
    frequency: float
    avg_confidence: float
    avg_duration_days: float
    dominant_periods: List[str]
    key_characteristics: Dict[str, Any]


@dataclass
class RegimeAnalysisOutput:
    """Complete output from regime analysis"""
    regime_results: List[Any]  # List of RegimeResult objects
    regime_distribution: Dict[str, RegimeStats]
    transition_patterns: Dict[str, Any]
    regime_clusters: Dict[str, Any]
    analysis_metadata: Dict[str, Any]


@dataclass
class InstrumentScore:
    """Performance score for an instrument in a specific strategy/regime"""
    symbol: str
    expected_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    regime_consistency: float
    composite_score: float


@dataclass
class InstrumentRankings:
    """Instrument rankings across all strategies and regimes"""
    strategy_rankings: Dict[str, Dict[str, List[InstrumentScore]]]
    ranking_metadata: Dict[str, Any]


@dataclass
class AnalysisOutputPaths:
    """File paths for persisted analysis outputs"""
    regime_distribution: Path
    regime_transitions: Path
    detailed_results: Path
    timestamp: str


@dataclass
class RankingsOutputPaths:
    """File paths for persisted ranking outputs"""
    strategy_files: Dict[str, Path]
    timestamp: str


@dataclass
class BacktestConfig:
    """Configuration for a single backtest"""
    name: str
    strategy: str
    instruments: List[str]
    regime_context: str
    parameters: Dict[str, Any]
    risk_params: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class BacktestSuite:
    """Complete suite of backtest configurations"""
    optimized_configs: List[BacktestConfig]
    baseline_configs: List[BacktestConfig]
    stress_configs: List[BacktestConfig]
    suite_metadata: Dict[str, Any]


@dataclass
class AnalysisResults:
    """Complete results from historical market analytics"""
    regime_analysis: RegimeAnalysisOutput
    instrument_rankings: InstrumentRankings
    analysis_paths: AnalysisOutputPaths
    rankings_paths: RankingsOutputPaths
    backtest_suite: BacktestSuite
    execution_metadata: Dict[str, Any]
```

### **3. Demo Integration Script**
```python
#!/usr/bin/env python3
"""
Historical Analytics Demo Integration
====================================

Demonstrates the complete historical analytics pipeline integration
with the existing validated MarketCondition Analytics system.
"""

import asyncio
import logging
from datetime import datetime

from core_structure.analytics.historical_analytics import run_historical_analysis, HistoricalPeriod

logger = logging.getLogger(__name__)


async def main():
    """Demonstrate historical analytics integration"""
    
    print("🏗️ Historical Market Analytics Integration Demo")
    print("=" * 60)
    print(f"📅 Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Define custom test periods (subset for demo)
        demo_periods = [
            HistoricalPeriod("covid-crash-demo", "2020-03-01", "2020-04-30", regime_hint="crisis_mode"),
            HistoricalPeriod("bull-market-demo", "2021-01-01", "2021-02-28", regime_hint="trending_bull"),
            HistoricalPeriod("sideways-demo", "2023-06-01", "2023-07-31", regime_hint="sideways_range")
        ]
        
        print(f"🔧 Running analysis on {len(demo_periods)} demo periods...")
        print()
        
        # Run complete historical analysis
        results = await run_historical_analysis(periods=demo_periods)
        
        # Display results summary
        print("📊 Analysis Results Summary:")
        print("-" * 30)
        
        regime_summary = await results.regime_analysis
        print(f"• Total periods analyzed: {len(results.regime_analysis.regime_results)}")
        print(f"• Total data points: {results.execution_metadata['total_data_points']:,}")
        print(f"• Execution time: {results.execution_metadata['execution_time_seconds']:.1f} seconds")
        print()
        
        # Show regime distribution
        print("🎯 Regime Distribution:")
        for regime, stats in results.regime_analysis.regime_distribution.items():
            print(f"   • {regime}: {stats.frequency:.1%} frequency, {stats.avg_confidence:.1%} confidence")
        print()
        
        # Show top instruments for each strategy
        print("🏆 Top Instruments by Strategy:")
        for strategy in ["momentum", "pairs_trading", "mean_reversion"]:
            if strategy in results.instrument_rankings.strategy_rankings:
                print(f"   📈 {strategy.upper()}:")
                
                for regime in ["crisis_mode", "trending_bull", "sideways_range"]:
                    if regime in results.instrument_rankings.strategy_rankings[strategy]:
                        top_instruments = results.instrument_rankings.strategy_rankings[strategy][regime][:3]
                        if top_instruments:
                            instruments_str = ", ".join([f"{inst.symbol} ({inst.composite_score:.2f})" 
                                                       for inst in top_instruments])
                            print(f"      {regime}: {instruments_str}")
                print()
        
        # Show backtest configurations generated
        print("⚙️ Backtest Configurations Generated:")
        print(f"   • Optimized configs: {len(results.backtest_suite.optimized_configs)}")
        print(f"   • Baseline configs: {len(results.backtest_suite.baseline_configs)}")
        print(f"   • Stress test configs: {len(results.backtest_suite.stress_configs)}")
        print()
        
        # Show output file locations
        print("📁 Output Files:")
        print(f"   • Regime analysis: {results.analysis_paths.regime_distribution}")
        print(f"   • Instrument rankings: {list(results.rankings_paths.strategy_files.values())[0].parent}")
        print()
        
        print("✅ Historical Analytics Integration Demo completed successfully!")
        print()
        print("🚀 Next Steps:")
        print("   1. Review generated JSON files in outputs/ directory")
        print("   2. Execute optimized backtest configurations") 
        print("   3. Compare performance vs baseline configurations")
        print("   4. Validate regime-specific instrument rankings")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
```

This file structure provides a clear, modular architecture for implementing the historical analytics framework, building upon the validated demo components while creating a production-ready system.