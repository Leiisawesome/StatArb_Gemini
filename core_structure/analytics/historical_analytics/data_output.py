#!/usr/bin/env python3
"""
Data Output System
==================

Comprehensive data persistence system for historical analytics results
with support for JSON, CSV, pickle formats and proper file organization.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
import pickle
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import logging
import shutil
from dataclasses import asdict
import gzip
import yaml

from .data_types import (
    AnalysisResults, RegimeAnalysisOutput, InstrumentRankings,
    BacktestSuite, HistoricalPeriod, MarketDataset
)

# Configure logging
logger = logging.getLogger(__name__)


class HistoricalAnalyticsOutputManager:
    """
    Comprehensive output manager for historical analytics results
    """
    
    def __init__(self, base_output_dir: str = "outputs/historical_analytics",
                 enable_compression: bool = True,
                 max_file_size_mb: int = 100):
        """
        Initialize the output manager
        
        Args:
            base_output_dir: Base directory for all outputs
            enable_compression: Whether to compress large files
            max_file_size_mb: Maximum file size before compression
        """
        self.base_output_dir = Path(base_output_dir)
        self.enable_compression = enable_compression
        self.max_file_size_mb = max_file_size_mb
        
        # Create directory structure
        self.directories = {
            'base': self.base_output_dir,
            'analyses': self.base_output_dir / 'analyses',
            'regime_results': self.base_output_dir / 'regime_results',
            'rankings': self.base_output_dir / 'rankings',
            'backtest_configs': self.base_output_dir / 'backtest_configs',
            'datasets': self.base_output_dir / 'datasets',
            'cache': self.base_output_dir / 'cache',
            'exports': self.base_output_dir / 'exports'
        }
        
        # Create all directories
        for dir_path in self.directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"HistoricalAnalyticsOutputManager initialized: {base_output_dir}")
    
    def save_complete_analysis(self, results: AnalysisResults, 
                             analysis_name: str) -> Dict[str, Path]:
        """
        Save complete analysis results with organized file structure
        
        Args:
            results: Complete analysis results
            analysis_name: Name for this analysis
            
        Returns:
            Dictionary of saved file paths
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_dir = self.directories['analyses'] / f"{analysis_name}_{timestamp}"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        logger.info(f"Saving complete analysis: {analysis_name}")
        
        try:
            # Save regime analysis
            regime_files = self._save_regime_analysis(
                results.regime_analysis, analysis_dir / 'regime_analysis'
            )
            saved_files.update(regime_files)
            
            # Save instrument rankings
            ranking_files = self._save_instrument_rankings(
                results.instrument_rankings, analysis_dir / 'rankings'
            )
            saved_files.update(ranking_files)
            
            # Save backtest suite
            if results.backtest_suite:
                backtest_files = self._save_backtest_suite(
                    results.backtest_suite, analysis_dir / 'backtest_configs'
                )
                saved_files.update(backtest_files)
            
            # Save execution metadata
            metadata_file = self._save_execution_metadata(
                results.execution_metadata, analysis_dir / 'metadata.json'
            )
            saved_files['metadata'] = metadata_file
            
            # Create analysis summary
            summary_file = self._create_analysis_summary(
                results, analysis_dir / 'analysis_summary.json'
            )
            saved_files['summary'] = summary_file
            
            # Create README for the analysis
            readme_file = self._create_analysis_readme(
                results, analysis_name, analysis_dir / 'README.md'
            )
            saved_files['readme'] = readme_file
            
            logger.info(f"Analysis saved successfully: {len(saved_files)} files created")
            return saved_files
            
        except Exception as e:
            logger.error(f"Error saving analysis {analysis_name}: {e}")
            raise
    
    def save_regime_analysis(self, regime_analysis: RegimeAnalysisOutput,
                           output_name: Optional[str] = None) -> Dict[str, Path]:
        """Save regime analysis results"""
        if output_name is None:
            output_name = f"regime_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_dir = self.directories['regime_results'] / output_name
        return self._save_regime_analysis(regime_analysis, output_dir)
    
    def save_instrument_rankings(self, rankings: InstrumentRankings,
                               output_name: Optional[str] = None) -> Dict[str, Path]:
        """Save instrument rankings"""
        if output_name is None:
            output_name = f"rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_dir = self.directories['rankings'] / output_name
        return self._save_instrument_rankings(rankings, output_dir)
    
    def save_backtest_suite(self, backtest_suite: BacktestSuite,
                          output_name: Optional[str] = None) -> Dict[str, Path]:
        """Save backtest configuration suite"""
        if output_name is None:
            output_name = f"backtest_suite_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_dir = self.directories['backtest_configs'] / output_name
        return self._save_backtest_suite(backtest_suite, output_dir)
    
    def export_to_csv(self, results: AnalysisResults, 
                     export_name: str) -> Dict[str, Path]:
        """Export analysis results to CSV format for external tools"""
        export_dir = self.directories['exports'] / f"{export_name}_csv"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        # Export regime detection results
        regime_data = []
        for result in results.regime_analysis.regime_results:
            regime_data.append({
                'period_name': result.period.name,
                'start_date': result.period.start_date,
                'end_date': result.period.end_date,
                'detected_regime': result.detected_regime.value,
                'confidence': result.confidence,
                'regime_strength': result.regime_strength,
                'market_stress': result.market_stress,
                'data_points_analyzed': result.data_points_analyzed
            })
        
        regime_df = pd.DataFrame(regime_data)
        regime_file = export_dir / 'regime_detection_results.csv'
        regime_df.to_csv(regime_file, index=False)
        exported_files['regime_results'] = regime_file
        
        # Export instrument rankings
        ranking_data = []
        for strategy_name, regime_rankings in results.instrument_rankings.strategy_rankings.items():
            for regime_name, instruments in regime_rankings.items():
                for rank, instrument in enumerate(instruments, 1):
                    ranking_data.append({
                        'strategy': strategy_name,
                        'regime': regime_name,
                        'rank': rank,
                        'symbol': instrument.symbol,
                        'composite_score': instrument.composite_score,
                        'expected_return': instrument.expected_return,
                        'sharpe_ratio': instrument.sharpe_ratio,
                        'max_drawdown': instrument.max_drawdown,
                        'win_rate': instrument.win_rate,
                        'regime_consistency': instrument.regime_consistency,
                        'volatility': instrument.volatility,
                        'correlation_to_market': instrument.correlation_to_market,
                        'sample_size': instrument.sample_size
                    })
        
        ranking_df = pd.DataFrame(ranking_data)
        ranking_file = export_dir / 'instrument_rankings.csv'
        ranking_df.to_csv(ranking_file, index=False)
        exported_files['rankings'] = ranking_file
        
        # Export backtest configurations
        if results.backtest_suite:
            config_data = []
            all_configs = (results.backtest_suite.optimized_configs + 
                          results.backtest_suite.baseline_configs + 
                          results.backtest_suite.stress_configs)
            
            for config in all_configs:
                config_data.append({
                    'config_id': config.config_id,
                    'name': config.name,
                    'strategy': config.strategy,
                    'regime_context': config.regime_context,
                    'config_type': config.config_type,
                    'instruments': ','.join(config.instruments),
                    'instrument_count': len(config.instruments),
                    'parameters': json.dumps(config.parameters),
                    'risk_parameters': json.dumps(config.risk_params)
                })
            
            config_df = pd.DataFrame(config_data)
            config_file = export_dir / 'backtest_configurations.csv'
            config_df.to_csv(config_file, index=False)
            exported_files['backtest_configs'] = config_file
        
        logger.info(f"Analysis exported to CSV: {len(exported_files)} files")
        return exported_files
    
    def create_analysis_archive(self, analysis_name: str,
                              include_cache: bool = False) -> Path:
        """Create compressed archive of analysis results"""
        import zipfile
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{analysis_name}_archive_{timestamp}.zip"
        archive_path = self.directories['exports'] / archive_name
        
        analysis_pattern = f"{analysis_name}_*"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add analysis files
            for analysis_dir in self.directories['analyses'].glob(analysis_pattern):
                for file_path in analysis_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(self.base_output_dir))
                        zipf.write(file_path, arcname)
            
            # Add related files from other directories
            for dir_name, dir_path in self.directories.items():
                if dir_name in ['analyses', 'exports']:
                    continue
                
                for file_path in dir_path.glob(f"{analysis_name}_*"):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(self.base_output_dir))
                        zipf.write(file_path, arcname)
        
        logger.info(f"Analysis archive created: {archive_path}")
        return archive_path
    
    def _save_regime_analysis(self, regime_analysis: RegimeAnalysisOutput,
                            output_dir: Path) -> Dict[str, Path]:
        """Save regime analysis to organized files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}
        
        # Save regime distribution
        regime_dist_data = {
            regime: asdict(stats) for regime, stats in regime_analysis.regime_distribution.items()
        }
        regime_dist_file = output_dir / 'regime_distribution.json'
        self._save_json(regime_dist_data, regime_dist_file)
        saved_files['regime_distribution'] = regime_dist_file
        
        # Save transition matrix
        transition_file = output_dir / 'transition_matrix.json'
        self._save_json(regime_analysis.transition_matrix, transition_file)
        saved_files['transition_matrix'] = transition_file
        
        # Save detailed results
        detailed_data = {
            'regime_results': [asdict(result) for result in regime_analysis.regime_results],
            'analysis_metadata': regime_analysis.analysis_metadata,
            'clustering_results': regime_analysis.regime_clusters
        }
        detailed_file = output_dir / 'detailed_results.json'
        self._save_json(detailed_data, detailed_file)
        saved_files['detailed_results'] = detailed_file
        
        # Save as pickle for Python compatibility
        pickle_file = output_dir / 'regime_analysis.pkl'
        self._save_pickle(regime_analysis, pickle_file)
        saved_files['pickle'] = pickle_file
        
        return saved_files
    
    def _save_instrument_rankings(self, rankings: InstrumentRankings,
                                output_dir: Path) -> Dict[str, Path]:
        """Save instrument rankings to organized files"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}
        
        # Save complete rankings as JSON
        rankings_data = {
            'strategy_rankings': {},
            'ranking_metadata': rankings.ranking_metadata,
            'generation_timestamp': rankings.generation_timestamp.isoformat()
        }
        
        # Convert instrument scores to dictionaries
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            rankings_data['strategy_rankings'][strategy_name] = {}
            for regime_name, instruments in regime_rankings.items():
                rankings_data['strategy_rankings'][strategy_name][regime_name] = [
                    asdict(instrument) for instrument in instruments
                ]
        
        rankings_file = output_dir / 'complete_rankings.json'
        self._save_json(rankings_data, rankings_file)
        saved_files['complete_rankings'] = rankings_file
        
        # Save individual strategy files
        strategy_dir = output_dir / 'by_strategy'
        strategy_dir.mkdir(exist_ok=True)
        
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            strategy_file = strategy_dir / f'{strategy_name}_rankings.json'
            strategy_data = {
                'strategy': strategy_name,
                'regime_rankings': {}
            }
            
            for regime_name, instruments in regime_rankings.items():
                strategy_data['regime_rankings'][regime_name] = [
                    asdict(instrument) for instrument in instruments
                ]
            
            self._save_json(strategy_data, strategy_file)
            saved_files[f'strategy_{strategy_name}'] = strategy_file
        
        # Save as pickle
        pickle_file = output_dir / 'rankings.pkl'
        self._save_pickle(rankings, pickle_file)
        saved_files['pickle'] = pickle_file
        
        return saved_files
    
    def _save_backtest_suite(self, backtest_suite: BacktestSuite,
                           output_dir: Path) -> Dict[str, Path]:
        """Save backtest configuration suite"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}
        
        # Save complete suite
        suite_data = {
            'optimized_configs': [asdict(config) for config in backtest_suite.optimized_configs],
            'baseline_configs': [asdict(config) for config in backtest_suite.baseline_configs],
            'stress_configs': [asdict(config) for config in backtest_suite.stress_configs],
            'suite_metadata': backtest_suite.suite_metadata,
            'generation_timestamp': backtest_suite.generation_timestamp.isoformat()
        }
        
        suite_file = output_dir / 'complete_suite.json'
        self._save_json(suite_data, suite_file)
        saved_files['complete_suite'] = suite_file
        
        # Save configs by type
        config_types = {
            'optimized': backtest_suite.optimized_configs,
            'baseline': backtest_suite.baseline_configs,
            'stress': backtest_suite.stress_configs
        }
        
        for config_type, configs in config_types.items():
            type_file = output_dir / f'{config_type}_configs.json'
            type_data = {
                'config_type': config_type,
                'configs': [asdict(config) for config in configs]
            }
            self._save_json(type_data, type_file)
            saved_files[f'{config_type}_configs'] = type_file
        
        # Save as pickle
        pickle_file = output_dir / 'backtest_suite.pkl'
        self._save_pickle(backtest_suite, pickle_file)
        saved_files['pickle'] = pickle_file
        
        return saved_files
    
    def _save_execution_metadata(self, metadata: Dict[str, Any],
                               output_file: Path) -> Path:
        """Save execution metadata"""
        self._save_json(metadata, output_file)
        return output_file
    
    def _create_analysis_summary(self, results: AnalysisResults,
                               output_file: Path) -> Path:
        """Create high-level analysis summary"""
        summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'success_metrics': results.success_metrics,
            'regime_analysis_summary': {
                'total_periods': results.regime_analysis.total_periods_analyzed,
                'avg_confidence': results.regime_analysis.avg_confidence,
                'regime_distribution': {
                    regime: {
                        'frequency': stats.frequency,
                        'avg_confidence': stats.avg_confidence,
                        'total_occurrences': stats.total_occurrences
                    }
                    for regime, stats in results.regime_analysis.regime_distribution.items()
                }
            },
            'ranking_summary': {
                'strategies_analyzed': list(results.instrument_rankings.strategy_rankings.keys()),
                'total_instrument_scores': sum(
                    len(instruments)
                    for strategy_rankings in results.instrument_rankings.strategy_rankings.values()
                    for instruments in strategy_rankings.values()
                )
            },
            'backtest_summary': {
                'total_configs': results.backtest_suite.total_configs if results.backtest_suite else 0,
                'config_breakdown': {
                    'optimized': len(results.backtest_suite.optimized_configs) if results.backtest_suite else 0,
                    'baseline': len(results.backtest_suite.baseline_configs) if results.backtest_suite else 0,
                    'stress': len(results.backtest_suite.stress_configs) if results.backtest_suite else 0
                }
            }
        }
        
        self._save_json(summary, output_file)
        return output_file
    
    def _create_analysis_readme(self, results: AnalysisResults,
                              analysis_name: str, output_file: Path) -> Path:
        """Create README file for analysis"""
        readme_content = f"""# Historical Analytics Results: {analysis_name}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This analysis processed {results.regime_analysis.total_periods_analyzed} historical periods with an average regime detection confidence of {results.regime_analysis.avg_confidence:.1%}.

## Results Summary

### Regime Analysis
- **Periods Analyzed**: {results.regime_analysis.total_periods_analyzed}
- **Average Confidence**: {results.regime_analysis.avg_confidence:.1%}
- **Regimes Detected**: {len(results.regime_analysis.regime_distribution)}

### Regime Distribution
"""
        
        for regime, stats in results.regime_analysis.regime_distribution.items():
            readme_content += f"- **{regime}**: {stats.frequency:.1%} frequency, {stats.total_occurrences} occurrences\n"
        
        readme_content += f"""
### Instrument Rankings
- **Strategies Analyzed**: {len(results.instrument_rankings.strategy_rankings)}
- **Total Rankings Generated**: {sum(len(instruments) for strategy_rankings in results.instrument_rankings.strategy_rankings.values() for instruments in strategy_rankings.values())}

### Backtest Configurations
"""
        
        if results.backtest_suite:
            readme_content += f"""- **Total Configurations**: {results.backtest_suite.total_configs}
- **Optimized Configs**: {len(results.backtest_suite.optimized_configs)}
- **Baseline Configs**: {len(results.backtest_suite.baseline_configs)}
- **Stress Test Configs**: {len(results.backtest_suite.stress_configs)}
"""
        else:
            readme_content += "- No backtest configurations generated\n"
        
        readme_content += """
## File Structure

- `regime_analysis/` - Regime detection results and analysis
- `rankings/` - Instrument performance rankings by strategy/regime
- `backtest_configs/` - Generated backtest configurations
- `metadata.json` - Execution metadata and parameters
- `analysis_summary.json` - High-level summary of results

## Usage

The results can be loaded and used as follows:

```python
from core_structure.analytics.historical_analytics import HistoricalAnalyticsOutputManager
import pickle

# Load complete results
output_manager = HistoricalAnalyticsOutputManager()
with open('regime_analysis/regime_analysis.pkl', 'rb') as f:
    regime_analysis = pickle.load(f)

with open('rankings/rankings.pkl', 'rb') as f:
    rankings = pickle.load(f)
```

For CSV exports, use the files in the exports directory for external analysis tools.
"""
        
        with open(output_file, 'w') as f:
            f.write(readme_content)
        
        return output_file
    
    def _save_json(self, data: Any, file_path: Path):
        """Save data as JSON with optional compression"""
        temp_file = file_path.with_suffix('.tmp')
        
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        # Check file size and compress if needed
        if self.enable_compression and temp_file.stat().st_size > self.max_file_size_mb * 1024 * 1024:
            compressed_file = file_path.with_suffix('.json.gz')
            with open(temp_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            temp_file.unlink()
            logger.info(f"Compressed large file: {compressed_file}")
        else:
            temp_file.rename(file_path)
    
    def _save_pickle(self, data: Any, file_path: Path):
        """Save data as pickle with optional compression"""
        if self.enable_compression:
            with gzip.open(file_path.with_suffix('.pkl.gz'), 'wb') as f:
                pickle.dump(data, f)
        else:
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)


class DatasetArchiveManager:
    """
    Manager for archiving and retrieving historical datasets
    """
    
    def __init__(self, archive_dir: str = "outputs/historical_analytics/datasets"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata tracking
        self.metadata_file = self.archive_dir / 'archive_metadata.yaml'
        self.metadata = self._load_metadata()
    
    def archive_datasets(self, datasets: Dict[str, MarketDataset],
                        archive_name: str) -> Path:
        """Archive a collection of datasets"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.archive_dir / f"{archive_name}_{timestamp}.pkl.gz"
        
        # Create archive
        with gzip.open(archive_path, 'wb') as f:
            pickle.dump(datasets, f)
        
        # Update metadata
        self.metadata[archive_name] = {
            'file_path': str(archive_path),
            'creation_timestamp': datetime.now().isoformat(),
            'dataset_count': len(datasets),
            'periods': [dataset.period.name for dataset in datasets.values()],
            'total_data_points': sum(dataset.total_data_points for dataset in datasets.values())
        }
        
        self._save_metadata()
        logger.info(f"Archived {len(datasets)} datasets to: {archive_path}")
        return archive_path
    
    def load_archived_datasets(self, archive_name: str) -> Dict[str, MarketDataset]:
        """Load datasets from archive"""
        if archive_name not in self.metadata:
            raise ValueError(f"Archive not found: {archive_name}")
        
        archive_path = Path(self.metadata[archive_name]['file_path'])
        
        with gzip.open(archive_path, 'rb') as f:
            datasets = pickle.load(f)
        
        logger.info(f"Loaded {len(datasets)} datasets from archive: {archive_name}")
        return datasets
    
    def list_archives(self) -> Dict[str, Dict[str, Any]]:
        """List all available archives"""
        return self.metadata.copy()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load archive metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _save_metadata(self):
        """Save archive metadata"""
        with open(self.metadata_file, 'w') as f:
            yaml.dump(self.metadata, f, indent=2)