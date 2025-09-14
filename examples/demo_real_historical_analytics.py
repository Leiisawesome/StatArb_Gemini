#!/usr/bin/env python3
"""
Real Market Data Historical Analytics Demo
=========================================

Production demonstration of the Historical Analytics Framework
using real market data from ClickHouse database.

This demo showcases:
- Real historical market data ingestion from ClickHouse
- Multi-period regime analysis with production data
- Cross-market condition instrument ranking
- Automated backtest configuration generation
- End-to-end analytics pipeline with real data

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Core imports
from core_structure.analytics.historical_analytics import (
    RealHistoricalDataLoader,
    PredefinedHistoricalPeriods,
    MarketDataset,
    AnalysisResults,
    HistoricalRegimeAnalyzer,
    HistoricalRankingEngine,
    BacktestConfigGenerator
)

# Infrastructure imports
from core_structure.components.market_data.core.enhanced_clickhouse_loader import EnhancedClickHouseLoader


class RealHistoricalAnalyticsDemo:
    """
    Comprehensive demonstration of Historical Analytics Framework 
    with real ClickHouse market data.
    """
    
    def __init__(self):
        """Initialize the real data analytics demo."""
        self.clickhouse_loader = None
        self.data_loader = None
        self.regime_analyzer = None
        self.ranking_engine = None
        self.config_generator = None
        self.results: Optional[AnalysisResults] = None
        
    async def setup_infrastructure(self) -> bool:
        """Setup ClickHouse connection and data infrastructure."""
        try:
            logger.info("Setting up ClickHouse infrastructure...")
            
            # Initialize ClickHouse loader (it's initialized in constructor)
            self.clickhouse_loader = EnhancedClickHouseLoader()
            
            # Initialize real data loader
            self.data_loader = RealHistoricalDataLoader(self.clickhouse_loader)
            
            # Initialize analytics components
            self.regime_analyzer = HistoricalRegimeAnalyzer(
                confidence_threshold=0.6,
                enable_clustering=True
            )
            
            self.ranking_engine = HistoricalRankingEngine(
                min_sample_size=30,
                enable_parallel_processing=True
            )
            
            self.config_generator = BacktestConfigGenerator(
                max_instruments_per_config=20,
                enable_portfolio_optimization=True
            )
            
            logger.info("✓ Infrastructure setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Infrastructure setup failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def verify_data_availability(self) -> bool:
        """Verify that historical market data is available in ClickHouse."""
        try:
            logger.info("Verifying data availability...")
            
            # First, let's check what tables exist
            tables_query = "SHOW TABLES FROM polygon_data"
            tables_result = self.clickhouse_loader.clickhouse.execute_query(tables_query)
            
            if tables_result:
                logger.info(f"Available tables in polygon_data: {[row[0] for row in tables_result]}")
            
            # Check the structure of the ticks table
            structure_query = "DESCRIBE TABLE polygon_data.ticks"
            try:
                structure_result = self.clickhouse_loader.clickhouse.execute_query(structure_query)
                if structure_result:
                    logger.info("polygon_data.ticks table structure:")
                    for row in structure_result:
                        logger.info(f"  {row[0]} - {row[1]}")
            except Exception as e:
                logger.warning(f"Could not describe ticks table: {e}")
            
            # Simple count query first
            simple_query = "SELECT COUNT(*) as total_rows FROM polygon_data.ticks LIMIT 1"
            result = self.clickhouse_loader.clickhouse.execute_query(simple_query)
            
            if result and len(result) > 0:
                row_count = result[0][0]
                logger.info(f"✓ Data availability check:")
                logger.info(f"  Total rows in polygon_data.ticks: {row_count:,}")
                
                return row_count > 0
            else:
                logger.warning("No data found in polygon_data.ticks table")
                return False
                
        except Exception as e:
            logger.error(f"Data availability check failed: {e}")
            return False
    
    async def load_real_market_data(self) -> Optional[Dict[str, MarketDataset]]:
        """Load real historical market data for multiple periods."""
        try:
            logger.info("Loading real historical market data...")
            
            # Get predefined analysis periods
            all_periods = PredefinedHistoricalPeriods.get_major_market_periods()
            
            # Select a few recent periods for demonstration
            analysis_periods = [
                all_periods[-3],  # Bank crisis 2023
                all_periods[-2],  # Recent recovery (if exists)
                all_periods[-1],  # Most recent period
            ]
            
            # Filter to existing periods
            analysis_periods = [p for p in analysis_periods if p is not None][:3]
            
            logger.info(f"Selected {len(analysis_periods)} periods for analysis:")
            for period in analysis_periods:
                logger.info(f"  - {period.name}: {period.start_date} to {period.end_date}")
            
            # Load data for all periods
            period_datasets = await self.data_loader.load_multiple_periods(
                periods=analysis_periods,
                instruments=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'SPY', 'QQQ'],
                timeframe='1d'
            )
            
            # Log results
            for period_name, dataset in period_datasets.items():
                if dataset:
                    logger.info(f"✓ Loaded {period_name}:")
                    logger.info(f"  Period: {dataset.period.start_date} to {dataset.period.end_date}")
                    logger.info(f"  Data records: {len(dataset.market_data)} total")
                    
                    # Log symbols if available
                    if hasattr(dataset.market_data, 'columns') and 'symbol' in dataset.market_data.columns:
                        unique_symbols = dataset.market_data['symbol'].nunique()
                        logger.info(f"  Unique symbols: {unique_symbols}")
                    else:
                        logger.info(f"  Market data shape: {dataset.market_data.shape if hasattr(dataset.market_data, 'shape') else 'Unknown'}")
                else:
                    logger.warning(f"✗ Failed to load data for {period_name}")
            
            return period_datasets
            
        except Exception as e:
            logger.error(f"Real market data loading failed: {e}")
            logger.error(traceback.format_exc())
            return None
    
    async def run_real_analytics_pipeline(self, datasets: Dict[str, MarketDataset]) -> Optional[AnalysisResults]:
        """Run the complete analytics pipeline on real market data."""
        start_time = time.time()
        
        try:
            logger.info("Running analytics pipeline on real market data...")
            
            # Filter successful datasets
            valid_datasets = {name: dataset for name, dataset in datasets.items() if dataset is not None}
            
            if not valid_datasets:
                logger.error("No valid datasets available for analysis")
                return None
            
            logger.info(f"Processing {len(valid_datasets)} valid datasets...")
            
            # Step 1: Regime Analysis
            logger.info("Step 1: Performing regime analysis...")
            regime_results = []
            
            for period_name, dataset in valid_datasets.items():
                try:
                    # Convert dataset to the format expected by regime analyzer
                    regime_result = self.regime_analyzer.analyze_single_period(
                        dataset=dataset,
                        include_transition_analysis=True
                    )
                    regime_results.append(regime_result)
                    logger.info(f"✓ Regime analysis complete for {period_name}")
                except Exception as e:
                    logger.warning(f"Regime analysis failed for {period_name}: {e}")
            
            # Create RegimeAnalysisOutput from individual results
            if regime_results:
                from core_structure.analytics.historical_analytics.data_types import RegimeAnalysisOutput
                regime_analysis = RegimeAnalysisOutput(
                    regime_results=regime_results,
                    regime_distribution={},  # Will be populated by the analyzer
                    transition_matrix={},
                    regime_clusters={},
                    analysis_metadata={'total_periods': len(regime_results)}
                )
            else:
                regime_analysis = None
            
            # Step 2: Instrument Ranking
            logger.info("Step 2: Generating instrument rankings...")
            rankings = None
            
            if regime_analysis:
                try:
                    rankings = self.ranking_engine.generate_comprehensive_rankings(
                        regime_analysis=regime_analysis,
                        datasets=valid_datasets,
                        strategies=None  # Use all strategies
                    )
                    logger.info("✓ Ranking analysis complete")
                except Exception as e:
                    logger.warning(f"Ranking analysis failed: {e}")
            else:
                logger.warning("Skipping ranking analysis - no regime results available")
            
            # Step 3: Configuration Generation
            logger.info("Step 3: Generating backtest configurations...")
            backtest_configs = []
            
            if regime_analysis and rankings:
                try:
                    # Generate configurations based on analysis results
                    suite = self.config_generator.generate_comprehensive_suite(
                        regime_analysis=regime_analysis,
                        rankings=rankings,
                        target_regimes=None  # Use all regimes
                    )
                    backtest_configs = suite.optimized_configs + suite.baseline_configs
                    logger.info(f"✓ Generated {len(backtest_configs)} backtest configurations")
                except Exception as e:
                    logger.warning(f"Configuration generation failed: {e}")
            else:
                logger.warning("Skipping config generation - missing regime analysis or rankings")
            
            # Create results object
            if regime_analysis or rankings or backtest_configs:
                from core_structure.analytics.historical_analytics.data_types import (
                    AnalysisResults, AnalysisOutputPaths, RankingsOutputPaths, BacktestSuite
                )
                from pathlib import Path
                
                # Create dummy output paths for demo
                analysis_paths = AnalysisOutputPaths(
                    regime_distribution=Path("/tmp/regime_dist.json"),
                    regime_transitions=Path("/tmp/regime_trans.json"),
                    detailed_results=Path("/tmp/detailed.json")
                )
                
                rankings_paths = RankingsOutputPaths(
                    strategy_files={}
                )
                
                # Create backtest suite if configs were generated
                backtest_suite = None
                if backtest_configs:
                    backtest_suite = BacktestSuite(
                        optimized_configs=backtest_configs,
                        baseline_configs=[],
                        stress_configs=[],
                        suite_metadata={'demo_generated': True},
                        total_configs=len(backtest_configs)
                    )
                
                results = AnalysisResults(
                    regime_analysis=regime_analysis,
                    instrument_rankings=rankings,
                    analysis_paths=analysis_paths,
                    rankings_paths=rankings_paths,
                    backtest_suite=backtest_suite,
                    execution_metadata={
                        'total_time': f"{time.time() - start_time:.2f}s",
                        'data_quality': f"{sum(1 for d in valid_datasets.values() if d) / len(datasets):.2%}",
                        'regimes_analyzed': len(regime_results) if regime_results else 0,
                        'rankings_generated': 1 if rankings else 0,
                        'configs_created': len(backtest_configs)
                    }
                )
            else:
                results = None
            
            if results:
                logger.info("✓ Analytics pipeline completed successfully")
                self.results = results
                return results
            else:
                logger.error("Analytics pipeline returned no results")
                return None
                
        except Exception as e:
            logger.error(f"Analytics pipeline failed: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def display_real_market_insights(self, results: AnalysisResults):
        """Display insights from real market data analysis."""
        try:
            logger.info("=== REAL MARKET DATA INSIGHTS ===")
            
            # Regime Analysis Results
            if results.regime_results:
                logger.info("\n📊 Market Regime Analysis:")
                for period_id, regime_result in results.regime_results.items():
                    logger.info(f"\nPeriod: {period_id}")
                    logger.info(f"  Detected Regime: {regime_result.detected_regime}")
                    logger.info(f"  Confidence: {regime_result.confidence:.2%}")
                    logger.info(f"  Key Characteristics:")
                    for key, value in regime_result.characteristics.items():
                        logger.info(f"    {key}: {value}")
            
            # Ranking Results
            if results.ranking_results:
                logger.info("\n🏆 Instrument Performance Rankings:")
                for period_id, rankings in results.ranking_results.items():
                    logger.info(f"\nTop performers in {period_id}:")
                    for i, score in enumerate(rankings.rankings[:5], 1):
                        logger.info(f"  {i}. {score.symbol}: {score.score:.3f} "
                                  f"(Return: {score.return_metrics.get('total_return', 'N/A'):.2%})")
            
            # Generated Configurations
            if results.backtest_configs:
                logger.info(f"\n⚙️  Generated {len(results.backtest_configs)} backtest configurations")
                for i, config in enumerate(results.backtest_configs[:3], 1):
                    logger.info(f"  Config {i}: {config.strategy_type} "
                              f"({config.regime_focus} conditions)")
            
            # Performance Summary
            if hasattr(results, 'performance_summary'):
                logger.info(f"\n📈 Analysis Performance:")
                logger.info(f"  Total processing time: {results.performance_summary.get('total_time', 'N/A')}")
                logger.info(f"  Data quality score: {results.performance_summary.get('data_quality', 'N/A')}")
            
            logger.info("\n✓ Real market data analysis complete!")
            
        except Exception as e:
            logger.error(f"Failed to display insights: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.clickhouse_loader:
                self.clickhouse_loader.close()
            logger.info("✓ Cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main demonstration function."""
    demo = RealHistoricalAnalyticsDemo()
    
    try:
        logger.info("🚀 Starting Real Market Data Historical Analytics Demo")
        logger.info("=" * 60)
        
        # Setup infrastructure
        if not await demo.setup_infrastructure():
            logger.error("Failed to setup infrastructure - aborting demo")
            return
        
        # Verify data availability
        if not await demo.verify_data_availability():
            logger.error("Insufficient data available - aborting demo")
            return
        
        # Load real market data
        datasets = await demo.load_real_market_data()
        if not datasets:
            logger.error("Failed to load market data - aborting demo")
            return
        
        # Run analytics pipeline
        results = await demo.run_real_analytics_pipeline(datasets)
        if not results:
            logger.error("Analytics pipeline failed - aborting demo")
            return
        
        # Display insights
        demo.display_real_market_insights(results)
        
        logger.info("\n🎉 Demo completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        logger.error(traceback.format_exc())
    
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())