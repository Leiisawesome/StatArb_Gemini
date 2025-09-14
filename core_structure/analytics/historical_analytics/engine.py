#!/usr/bin/env python3
"""
Historical Analytics Engine
===========================

Main orchestration engine for the complete historical analytics pipeline.
Coordinates data loading, regime analysis, instrument ranking, and 
backtest configuration generation.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import gc
from dataclasses import asdict
import json
from pathlib import Path
import time
import traceback

from .data_types import (
    HistoricalPeriod, MarketDataset, RegimeAnalysisOutput,
    InstrumentRankings, BacktestSuite, AnalysisResults,
    AnalysisOutputPaths, RankingsOutputPaths
)

from .data_ingestion import HistoricalDataManager, DataValidationEngine
from .regime_analyzer import HistoricalRegimeAnalyzer
from .ranking_engine import HistoricalRankingEngine, RankingAnalytics
from .config_generator import BacktestConfigGenerator

# Import from existing strategy system
from ..market_condition_analytics import StrategyType

# Configure logging
logger = logging.getLogger(__name__)


class HistoricalAnalyticsEngine:
    """
    Main engine orchestrating the complete historical analytics pipeline
    """
    
    def __init__(self, 
                 data_source_path: str,
                 output_base_dir: Optional[str] = None,
                 enable_caching: bool = True,
                 enable_parallel_processing: bool = True):
        """
        Initialize the historical analytics engine
        
        Args:
            data_source_path: Path to market data source
            output_base_dir: Base directory for outputs
            enable_caching: Whether to enable result caching
            enable_parallel_processing: Whether to use parallel processing
        """
        self.data_source_path = data_source_path
        self.output_base_dir = Path(output_base_dir) if output_base_dir else Path("outputs/historical_analytics")
        self.enable_caching = enable_caching
        self.enable_parallel_processing = enable_parallel_processing
        
        # Initialize core components
        self.data_manager = HistoricalDataManager(
            data_source_path=data_source_path,
            cache_enabled=enable_caching
        )
        
        self.data_validator = DataValidationEngine()
        
        self.regime_analyzer = HistoricalRegimeAnalyzer(
            confidence_threshold=0.6,
            enable_clustering=True
        )
        
        self.ranking_engine = HistoricalRankingEngine(
            min_sample_size=30,
            enable_parallel_processing=enable_parallel_processing
        )
        
        self.ranking_analytics = RankingAnalytics()
        
        self.config_generator = BacktestConfigGenerator(
            max_instruments_per_config=20,
            enable_portfolio_optimization=True
        )
        
        # Pipeline execution tracking
        self.execution_state = {
            'current_step': 'initialized',
            'steps_completed': [],
            'start_time': None,
            'errors': [],
            'warnings': []
        }
        
        # Ensure output directories exist
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"HistoricalAnalyticsEngine initialized with data source: {data_source_path}")
    
    def run_complete_analysis(self, 
                            periods_config: Optional[Dict] = None,
                            target_strategies: Optional[List[StrategyType]] = None,
                            target_symbols: Optional[List[str]] = None,
                            analysis_name: Optional[str] = None) -> AnalysisResults:
        """
        Run the complete historical analytics pipeline
        
        Args:
            periods_config: Optional custom period configuration
            target_strategies: Optional list of strategies to analyze
            target_symbols: Optional list of symbols to analyze
            analysis_name: Optional name for this analysis run
            
        Returns:
            Complete analysis results with all outputs
        """
        if analysis_name is None:
            analysis_name = f"historical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting complete historical analysis: {analysis_name}")
        self._start_execution_tracking()
        
        try:
            # Step 1: Define and load historical periods
            logger.info("Step 1: Loading historical periods and data")
            periods, datasets = self._load_historical_data(periods_config, target_symbols)
            self._mark_step_completed('data_loading')
            
            # Step 2: Validate data compatibility
            logger.info("Step 2: Validating data compatibility")
            validation_report = self._validate_data_compatibility(datasets)
            self._mark_step_completed('data_validation')
            
            # Step 3: Perform regime analysis
            logger.info("Step 3: Performing regime analysis")
            regime_analysis = self._perform_regime_analysis(datasets)
            self._mark_step_completed('regime_analysis')
            
            # Step 4: Generate instrument rankings
            logger.info("Step 4: Generating instrument rankings")
            rankings = self._generate_instrument_rankings(regime_analysis, datasets, target_strategies)
            self._mark_step_completed('instrument_ranking')
            
            # Step 5: Generate backtest configurations
            logger.info("Step 5: Generating backtest configurations")
            backtest_suite = self._generate_backtest_configurations(regime_analysis, rankings)
            self._mark_step_completed('backtest_config_generation')
            
            # Step 6: Export results
            logger.info("Step 6: Exporting analysis results")
            analysis_paths, rankings_paths = self._export_analysis_results(
                regime_analysis, rankings, analysis_name
            )
            self._mark_step_completed('results_export')
            
            # Create comprehensive results
            results = AnalysisResults(
                regime_analysis=regime_analysis,
                instrument_rankings=rankings,
                analysis_paths=analysis_paths,
                rankings_paths=rankings_paths,
                backtest_suite=backtest_suite,
                execution_metadata={
                    'analysis_name': analysis_name,
                    'execution_time': self._get_execution_time(),
                    'data_source': str(self.data_source_path),
                    'periods_analyzed': len(datasets),
                    'validation_report': validation_report,
                    'pipeline_state': self.execution_state.copy(),
                    'success_metrics': {}  # Will be populated below
                }
            )
            
            # Calculate success metrics
            results.execution_metadata['success_metrics'] = results.success_metrics
            
            logger.info(
                f"Complete analysis finished successfully in {self._get_execution_time():.1f}s: "
                f"{len(regime_analysis.regime_results)} periods analyzed, "
                f"{backtest_suite.total_configs} backtest configs generated"
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Historical analytics pipeline failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.execution_state['errors'].append(error_msg)
            raise
    
    async def run_streaming_analysis(self, 
                                   periods_config: Optional[Dict] = None,
                                   target_strategies: Optional[List[StrategyType]] = None,
                                   target_symbols: Optional[List[str]] = None,
                                   analysis_name: Optional[str] = None,
                                   chunk_size: int = 5000) -> AnalysisResults:
        """
        Run the complete historical analytics pipeline with streaming for large datasets
        
        Args:
            periods_config: Optional custom period configuration
            target_strategies: Optional list of strategies to analyze
            target_symbols: Optional list of symbols to analyze
            analysis_name: Optional name for this analysis run
            chunk_size: Number of rows per chunk for streaming
            
        Returns:
            Complete analysis results with all outputs
        """
        if analysis_name is None:
            analysis_name = f"streaming_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting streaming historical analysis: {analysis_name}")
        self._start_execution_tracking()
        
        try:
            # Step 1: Define historical periods (no data loading yet)
            self.execution_state['current_step'] = 'defining_periods'
            periods = self.data_manager.define_historical_periods(periods_config)
            
            if not periods:
                raise ValueError("No valid historical periods defined")
            
            logger.info(f"Defined {len(periods)} periods for streaming analysis")
            
            # Step 2: Stream regime analysis
            logger.info("Step 2: Performing streaming regime analysis...")
            regime_results = []
            
            async for period_name, data_chunk in self.data_manager.stream_multiple_periods(
                periods, target_symbols, chunk_size
            ):
                try:
                    # Process chunk through regime analyzer
                    chunk_result = await self._process_regime_chunk(period_name, data_chunk)
                    if chunk_result:
                        regime_results.append(chunk_result)
                    
                    # Force garbage collection periodically
                    if len(regime_results) % 10 == 0:
                        gc.collect()
                        
                except Exception as e:
                    logger.warning(f"Failed to process chunk for {period_name}: {e}")
                    continue
            
            # Step 3: Combine regime results
            from .data_types import RegimeAnalysisOutput
            regime_analysis = RegimeAnalysisOutput(
                regime_results=regime_results,
                regime_distribution={},
                transition_matrix={},
                regime_clusters={},
                analysis_metadata={
                    'total_periods': len(periods),
                    'streaming_mode': True,
                    'chunk_size': chunk_size,
                    'analysis_timestamp': datetime.now().isoformat()
                }
            )
            
            # Step 4: Generate instrument rankings (using aggregated data)
            logger.info("Step 4: Generating instrument rankings...")
            rankings = await self._generate_streaming_rankings(regime_analysis, target_strategies)
            
            # Step 5: Generate backtest configs
            logger.info("Step 5: Generating backtest configurations...")
            backtest_suite = self.config_generator.generate_comprehensive_configs(
                regime_analysis=regime_analysis,
                rankings=rankings,
                target_strategies=target_strategies or [StrategyType.MEAN_REVERSION, StrategyType.MOMENTUM]
            )
            
            # Step 6: Export results
            analysis_paths, rankings_paths = self._export_analysis_results(
                regime_analysis, rankings, analysis_name
            )
            
            # Create final results
            results = AnalysisResults(
                regime_analysis=regime_analysis,
                instrument_rankings=rankings,
                backtest_suite=backtest_suite,
                analysis_metadata={
                    'analysis_name': analysis_name,
                    'streaming_mode': True,
                    'chunk_size': chunk_size,
                    'timestamp': datetime.now().isoformat(),
                    'execution_time_seconds': self._get_execution_time()
                },
                output_paths=analysis_paths,
                rankings_paths=rankings_paths,
                execution_metadata=self.execution_state.copy()
            )
            
            # Calculate success metrics
            results.execution_metadata['success_metrics'] = results.success_metrics
            
            logger.info(
                f"Streaming analysis finished successfully in {self._get_execution_time():.1f}s: "
                f"{len(regime_analysis.regime_results)} periods analyzed"
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Streaming historical analytics pipeline failed: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.execution_state['errors'].append(error_msg)
            raise
    
    async def _process_regime_chunk(self, period_name: str, data_chunk: pd.DataFrame) -> Optional[Any]:
        """Process a data chunk for regime analysis"""
        try:
            # Create a temporary dataset for this chunk
            from .data_types import HistoricalPeriod, MarketDataset
            
            # Extract period info from period_name and create basic period
            temp_period = HistoricalPeriod(
                name=period_name,
                start_date=data_chunk['timestamp'].min().strftime('%Y-%m-%d'),
                end_date=data_chunk['timestamp'].max().strftime('%Y-%m-%d'),
                description=f"Streaming chunk for {period_name}"
            )
            
            temp_dataset = MarketDataset(
                period=temp_period,
                market_data=data_chunk,
                metadata={'streaming_chunk': True, 'chunk_size': len(data_chunk)}
            )
            
            # Analyze this chunk
            return self.regime_analyzer.analyze_single_period(
                dataset=temp_dataset,
                include_transition_analysis=False  # Skip transitions for chunks
            )
            
        except Exception as e:
            logger.warning(f"Error processing regime chunk for {period_name}: {e}")
            return None
    
    async def _generate_streaming_rankings(self, regime_analysis: Any, 
                                         target_strategies: Optional[List[StrategyType]]) -> Any:
        """Generate rankings from streaming regime analysis"""
        try:
            # Use the ranking engine with the compiled regime results
            return self.ranking_engine.rank_instruments_across_regimes(
                regime_analysis=regime_analysis,
                target_strategies=target_strategies or [StrategyType.MEAN_REVERSION, StrategyType.MOMENTUM]
            )
        except Exception as e:
            logger.error(f"Error generating streaming rankings: {e}")
            # Return empty rankings as fallback
            from .data_types import InstrumentRankings
            return InstrumentRankings(
                rankings_by_strategy={},
                cross_strategy_rankings=[],
                rankings_metadata={
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            )
    
    def run_regime_analysis_only(self, 
                               periods_config: Optional[Dict] = None,
                               target_symbols: Optional[List[str]] = None) -> RegimeAnalysisOutput:
        """
        Run only the regime analysis portion of the pipeline
        
        Args:
            periods_config: Optional custom period configuration
            target_symbols: Optional list of symbols to analyze
            
        Returns:
            Regime analysis results
        """
        logger.info("Running regime analysis only")
        self._start_execution_tracking()
        
        try:
            # Load data
            periods, datasets = self._load_historical_data(periods_config, target_symbols)
            
            # Perform regime analysis
            regime_analysis = self._perform_regime_analysis(datasets)
            
            logger.info(f"Regime analysis completed: {len(regime_analysis.regime_results)} periods analyzed")
            return regime_analysis
            
        except Exception as e:
            logger.error(f"Regime analysis failed: {e}")
            raise
    
    def run_ranking_analysis_only(self,
                                regime_analysis: RegimeAnalysisOutput,
                                datasets: Dict[str, MarketDataset],
                                target_strategies: Optional[List[StrategyType]] = None) -> InstrumentRankings:
        """
        Run only the instrument ranking analysis
        
        Args:
            regime_analysis: Pre-computed regime analysis
            datasets: Market datasets
            target_strategies: Optional list of strategies to analyze
            
        Returns:
            Instrument rankings
        """
        logger.info("Running ranking analysis only")
        
        try:
            rankings = self._generate_instrument_rankings(regime_analysis, datasets, target_strategies)
            logger.info("Ranking analysis completed")
            return rankings
            
        except Exception as e:
            logger.error(f"Ranking analysis failed: {e}")
            raise
    
    def validate_analysis_pipeline(self) -> Dict[str, Any]:
        """
        Validate the analysis pipeline configuration and dependencies
        
        Returns:
            Validation report
        """
        logger.info("Validating analysis pipeline")
        
        validation_report = {
            'pipeline_valid': True,
            'component_status': {},
            'data_source_status': {},
            'output_directory_status': {},
            'recommendations': []
        }
        
        try:
            # Validate data source
            data_source_path = Path(self.data_source_path)
            if data_source_path.exists():
                validation_report['data_source_status'] = {
                    'exists': True,
                    'readable': data_source_path.is_file(),
                    'size_mb': data_source_path.stat().st_size / (1024 * 1024) if data_source_path.is_file() else 0
                }
            else:
                validation_report['data_source_status'] = {'exists': False}
                validation_report['pipeline_valid'] = False
                validation_report['recommendations'].append(
                    f"Data source not found: {self.data_source_path}"
                )
            
            # Validate output directory
            validation_report['output_directory_status'] = {
                'exists': self.output_base_dir.exists(),
                'writable': True  # Assume writable for now
            }
            
            # Validate components
            components = {
                'data_manager': self.data_manager,
                'regime_analyzer': self.regime_analyzer,
                'ranking_engine': self.ranking_engine,
                'config_generator': self.config_generator
            }
            
            for name, component in components.items():
                validation_report['component_status'][name] = {
                    'initialized': component is not None,
                    'type': type(component).__name__
                }
            
            logger.info(f"Pipeline validation complete: {'VALID' if validation_report['pipeline_valid'] else 'INVALID'}")
            return validation_report
            
        except Exception as e:
            logger.error(f"Pipeline validation failed: {e}")
            validation_report['pipeline_valid'] = False
            validation_report['recommendations'].append(f"Validation error: {e}")
            return validation_report
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline execution status"""
        return {
            'current_step': self.execution_state['current_step'],
            'steps_completed': self.execution_state['steps_completed'],
            'execution_time': self._get_execution_time(),
            'errors_count': len(self.execution_state['errors']),
            'warnings_count': len(self.execution_state['warnings']),
            'last_error': self.execution_state['errors'][-1] if self.execution_state['errors'] else None
        }
    
    def _load_historical_data(self, periods_config: Optional[Dict],
                            target_symbols: Optional[List[str]]) -> Tuple[List[HistoricalPeriod], Dict[str, MarketDataset]]:
        """Load historical periods and market data"""
        self.execution_state['current_step'] = 'loading_data'
        
        # Define historical periods
        periods = self.data_manager.define_historical_periods(periods_config)
        
        if not periods:
            raise ValueError("No valid historical periods defined")
        
        # Load data for all periods
        datasets = self.data_manager.load_multiple_periods(periods, target_symbols)
        
        if not datasets:
            raise ValueError("No datasets successfully loaded")
        
        logger.info(f"Loaded {len(datasets)} datasets across {len(periods)} periods")
        return periods, datasets
    
    def _validate_data_compatibility(self, datasets: Dict[str, MarketDataset]) -> Dict[str, Any]:
        """Validate data compatibility across periods"""
        self.execution_state['current_step'] = 'validating_data'
        
        validation_report = self.data_validator.validate_dataset_compatibility(datasets)
        
        # Add warnings for validation issues
        if not validation_report['overall_compatibility']:
            warning_msg = "Data compatibility issues detected"
            self.execution_state['warnings'].append(warning_msg)
            logger.warning(warning_msg)
        
        return validation_report
    
    def _perform_regime_analysis(self, datasets: Dict[str, MarketDataset]) -> RegimeAnalysisOutput:
        """Perform comprehensive regime analysis"""
        self.execution_state['current_step'] = 'regime_analysis'
        
        regime_analysis = self.regime_analyzer.analyze_multiple_periods(
            datasets, enable_cross_period_analysis=True
        )
        
        # Validate regime predictions if regime hints are available
        validation_results = self.regime_analyzer.validate_regime_predictions(regime_analysis)
        
        if validation_results.get('overall_accuracy', 0) < 0.7:
            warning_msg = f"Low regime detection accuracy: {validation_results['overall_accuracy']:.1%}"
            self.execution_state['warnings'].append(warning_msg)
            logger.warning(warning_msg)
        
        return regime_analysis
    
    def _generate_instrument_rankings(self, 
                                    regime_analysis: RegimeAnalysisOutput,
                                    datasets: Dict[str, MarketDataset],
                                    target_strategies: Optional[List[StrategyType]]) -> InstrumentRankings:
        """Generate comprehensive instrument rankings"""
        self.execution_state['current_step'] = 'instrument_ranking'
        
        if target_strategies is None:
            target_strategies = list(StrategyType)
        
        rankings = self.ranking_engine.generate_comprehensive_rankings(
            regime_analysis, datasets, target_strategies
        )
        
        # Perform additional ranking analytics
        stability_analysis = self.ranking_analytics.analyze_ranking_stability(rankings)
        specialists = self.ranking_analytics.identify_regime_specialists(rankings)
        
        # Add analytics to metadata
        rankings.ranking_metadata.update({
            'stability_analysis': stability_analysis,
            'regime_specialists': specialists
        })
        
        return rankings
    
    def _generate_backtest_configurations(self,
                                        regime_analysis: RegimeAnalysisOutput,
                                        rankings: InstrumentRankings) -> BacktestSuite:
        """Generate comprehensive backtest configuration suite"""
        self.execution_state['current_step'] = 'backtest_config_generation'
        
        target_regimes = list(regime_analysis.regime_distribution.keys())
        
        backtest_suite = self.config_generator.generate_comprehensive_suite(
            regime_analysis, rankings, target_regimes
        )
        
        return backtest_suite
    
    def _export_analysis_results(self, 
                               regime_analysis: RegimeAnalysisOutput,
                               rankings: InstrumentRankings,
                               analysis_name: str) -> Tuple[AnalysisOutputPaths, RankingsOutputPaths]:
        """Export analysis results to files"""
        self.execution_state['current_step'] = 'exporting_results'
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create analysis-specific output directory
        analysis_output_dir = self.output_base_dir / analysis_name
        analysis_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export regime analysis
        regime_distribution_file = analysis_output_dir / f"regime_distribution_{timestamp}.json"
        regime_transitions_file = analysis_output_dir / f"regime_transitions_{timestamp}.json"
        detailed_results_file = analysis_output_dir / f"detailed_results_{timestamp}.json"
        
        # Export regime distribution
        with open(regime_distribution_file, 'w') as f:
            regime_dist_data = {
                regime: asdict(stats) for regime, stats in regime_analysis.regime_distribution.items()
            }
            json.dump(regime_dist_data, f, indent=2, default=str)
        
        # Export transition matrix
        with open(regime_transitions_file, 'w') as f:
            json.dump(regime_analysis.transition_matrix, f, indent=2)
        
        # Export detailed results
        detailed_data = {
            'regime_results': [asdict(result) for result in regime_analysis.regime_results],
            'analysis_metadata': regime_analysis.analysis_metadata,
            'clustering_results': regime_analysis.regime_clusters
        }
        
        with open(detailed_results_file, 'w') as f:
            json.dump(detailed_data, f, indent=2, default=str)
        
        analysis_paths = AnalysisOutputPaths(
            regime_distribution=regime_distribution_file,
            regime_transitions=regime_transitions_file,
            detailed_results=detailed_results_file,
            timestamp=timestamp
        )
        
        # Export rankings
        rankings_output_dir = analysis_output_dir / "rankings"
        rankings_paths = self.ranking_engine.export_detailed_rankings(rankings, rankings_output_dir)
        
        logger.info(f"Analysis results exported to: {analysis_output_dir}")
        
        return analysis_paths, rankings_paths
    
    def _start_execution_tracking(self):
        """Start tracking pipeline execution"""
        self.execution_state = {
            'current_step': 'starting',
            'steps_completed': [],
            'start_time': time.time(),
            'errors': [],
            'warnings': []
        }
    
    def _mark_step_completed(self, step_name: str):
        """Mark a pipeline step as completed"""
        self.execution_state['steps_completed'].append({
            'step': step_name,
            'completed_at': time.time(),
            'duration': time.time() - self.execution_state['start_time']
        })
        logger.debug(f"Pipeline step completed: {step_name}")
    
    def _get_execution_time(self) -> float:
        """Get total execution time"""
        if self.execution_state['start_time'] is None:
            return 0.0
        return time.time() - self.execution_state['start_time']


class AnalyticsPipelineManager:
    """
    High-level manager for running multiple analytics pipelines and managing results
    """
    
    def __init__(self, base_output_dir: str = "outputs/historical_analytics"):
        self.base_output_dir = Path(base_output_dir)
        self.pipeline_results: Dict[str, AnalysisResults] = {}
        
        # Create base output directory
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AnalyticsPipelineManager initialized with output dir: {base_output_dir}")
    
    def run_analysis_batch(self, 
                         analysis_configs: List[Dict[str, Any]]) -> Dict[str, AnalysisResults]:
        """
        Run a batch of analysis configurations
        
        Args:
            analysis_configs: List of configuration dictionaries
            
        Returns:
            Dictionary mapping analysis names to results
        """
        logger.info(f"Running batch of {len(analysis_configs)} analyses")
        
        batch_results = {}
        
        for i, config in enumerate(analysis_configs):
            try:
                analysis_name = config.get('name', f'analysis_{i+1}')
                data_source = config['data_source_path']
                
                # Create engine for this analysis
                engine = HistoricalAnalyticsEngine(
                    data_source_path=data_source,
                    output_base_dir=str(self.base_output_dir),
                    enable_caching=config.get('enable_caching', True),
                    enable_parallel_processing=config.get('enable_parallel_processing', True)
                )
                
                # Run analysis
                results = engine.run_complete_analysis(
                    periods_config=config.get('periods_config'),
                    target_strategies=config.get('target_strategies'),
                    target_symbols=config.get('target_symbols'),
                    analysis_name=analysis_name
                )
                
                batch_results[analysis_name] = results
                self.pipeline_results[analysis_name] = results
                
                logger.info(f"Completed analysis: {analysis_name}")
                
            except Exception as e:
                logger.error(f"Failed analysis {i+1}: {e}")
                continue
        
        logger.info(f"Batch analysis complete: {len(batch_results)} successful out of {len(analysis_configs)}")
        return batch_results
    
    def compare_analysis_results(self, analysis_names: List[str]) -> Dict[str, Any]:
        """
        Compare results across multiple analyses
        
        Args:
            analysis_names: Names of analyses to compare
            
        Returns:
            Comparison report
        """
        if not all(name in self.pipeline_results for name in analysis_names):
            missing = [name for name in analysis_names if name not in self.pipeline_results]
            raise ValueError(f"Missing analysis results: {missing}")
        
        comparison = {
            'analyses_compared': analysis_names,
            'regime_detection_comparison': {},
            'ranking_consistency': {},
            'performance_metrics': {},
            'summary': {}
        }
        
        # Compare regime detection accuracy
        for name in analysis_names:
            results = self.pipeline_results[name]
            accuracy = results.regime_analysis.get_regime_accuracy()
            comparison['regime_detection_comparison'][name] = {
                'accuracy': accuracy,
                'avg_confidence': results.regime_analysis.avg_confidence,
                'periods_analyzed': results.regime_analysis.total_periods_analyzed
            }
        
        # Compare ranking consistency
        # Implementation would compare top performers across analyses
        
        # Generate summary
        avg_accuracy = np.mean([
            comp['accuracy'] for comp in comparison['regime_detection_comparison'].values()
            if comp['accuracy'] is not None
        ])
        
        comparison['summary'] = {
            'total_analyses': len(analysis_names),
            'avg_regime_accuracy': avg_accuracy,
            'best_performing_analysis': max(
                analysis_names,
                key=lambda x: comparison['regime_detection_comparison'][x]['accuracy'] or 0
            )
        }
        
        return comparison
    
    def export_batch_summary(self, output_file: Optional[Path] = None) -> Path:
        """Export summary of all pipeline results"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.base_output_dir / f"batch_summary_{timestamp}.json"
        
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'total_analyses': len(self.pipeline_results),
            'analysis_summaries': {}
        }
        
        for name, results in self.pipeline_results.items():
            summary['analysis_summaries'][name] = {
                'success_metrics': results.success_metrics,
                'execution_metadata': results.execution_metadata,
                'total_configs_generated': results.backtest_suite.total_configs if results.backtest_suite else 0
            }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Batch summary exported to: {output_file}")
        return output_file