#!/usr/bin/env python3
"""
Historical Data Ingestion and Management
=======================================

Handles loading, validation, and enrichment of market data
for historical analytics across multiple time periods.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, AsyncGenerator
from datetime import datetime, timedelta
import logging
import json
import gc
from dataclasses import asdict

from .data_types import (
    HistoricalPeriod, MarketDataset, AnalysisOutputPaths,
    validate_historical_period, validate_market_dataset
)

# Configure logging
logger = logging.getLogger(__name__)


class HistoricalDataManager:
    """
    Comprehensive manager for historical market data across multiple periods
    """
    
    def __init__(self, data_source_path: str, cache_enabled: bool = True):
        """
        Initialize the data manager
        
        Args:
            data_source_path: Path to market data source (CSV, database, etc.)
            cache_enabled: Whether to cache processed datasets
        """
        self.data_source_path = Path(data_source_path)
        self.cache_enabled = cache_enabled
        self.cache_dir = Path("outputs/historical_analytics/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Data validation parameters
        self.min_data_points_per_period = 100
        self.required_columns = ['timestamp', 'symbol', 'close', 'volume']
        self.optional_columns = ['open', 'high', 'low', 'returns', 'volatility']
        
        # Cache for loaded datasets
        self._dataset_cache: Dict[str, MarketDataset] = {}
        
        logger.info(f"HistoricalDataManager initialized with data source: {self.data_source_path}")
    
    def define_historical_periods(self, periods_config: Optional[Dict] = None) -> List[HistoricalPeriod]:
        """
        Define historical periods for analysis
        
        Args:
            periods_config: Optional custom period configuration
            
        Returns:
            List of validated historical periods
        """
        if periods_config is None:
            periods_config = self._get_default_periods()
        
        periods = []
        for period_data in periods_config.get('periods', []):
            try:
                period = HistoricalPeriod(**period_data)
                if validate_historical_period(period):
                    periods.append(period)
                    logger.info(f"Added period: {period.name} ({period.start_date} to {period.end_date})")
                else:
                    logger.warning(f"Period {period_data.get('name')} failed validation")
            except Exception as e:
                logger.error(f"Error creating period {period_data.get('name')}: {e}")
        
        logger.info(f"Defined {len(periods)} historical periods for analysis")
        return periods
    
    def load_period_data(self, period: HistoricalPeriod, 
                        symbols: Optional[List[str]] = None,
                        force_reload: bool = False) -> MarketDataset:
        """
        Load market data for a specific historical period
        
        Args:
            period: Historical period to load data for
            symbols: Optional list of symbols to filter (loads all if None)
            force_reload: Force reload even if cached
            
        Returns:
            Validated MarketDataset for the period
        """
        cache_key = f"{period.name}_{hash(str(symbols))}"
        
        # Check cache first
        if not force_reload and self.cache_enabled and cache_key in self._dataset_cache:
            logger.info(f"Loading cached data for period: {period.name}")
            return self._dataset_cache[cache_key]
        
        logger.info(f"Loading fresh data for period: {period.name}")
        
        try:
            # Load raw market data
            raw_data = self._load_raw_data(period.start_date, period.end_date, symbols)
            
            # Validate and clean data
            cleaned_data = self._validate_and_clean_data(raw_data, period)
            
            # Enrich with derived features
            enriched_data = self._enrich_market_data(cleaned_data)
            
            # Create dataset
            dataset = MarketDataset(
                period=period,
                market_data=enriched_data,
                metadata={
                    'load_timestamp': datetime.now().isoformat(),
                    'source_file': str(self.data_source_path),
                    'symbols_requested': symbols,
                    'symbols_loaded': list(enriched_data['symbol'].unique()) if 'symbol' in enriched_data.columns else [],
                    'data_quality_score': self._calculate_data_quality_score(enriched_data)
                }
            )
            
            # Validate dataset
            if not validate_market_dataset(dataset):
                raise ValueError(f"Dataset for period {period.name} failed validation")
            
            # Cache if enabled
            if self.cache_enabled:
                self._dataset_cache[cache_key] = dataset
            
            logger.info(f"Successfully loaded {dataset.total_data_points} data points for period {period.name}")
            return dataset
            
        except Exception as e:
            logger.error(f"Error loading data for period {period.name}: {e}")
            raise
    
    def load_multiple_periods(self, periods: List[HistoricalPeriod],
                            symbols: Optional[List[str]] = None,
                            parallel_loading: bool = True) -> Dict[str, MarketDataset]:
        """
        Load data for multiple historical periods
        
        Args:
            periods: List of historical periods to load
            symbols: Optional symbol filter
            parallel_loading: Whether to load periods in parallel
            
        Returns:
            Dictionary mapping period names to datasets
        """
        datasets = {}
        failed_periods = []
        
        logger.info(f"Loading data for {len(periods)} periods")
        
        for period in periods:
            try:
                dataset = self.load_period_data(period, symbols)
                datasets[period.name] = dataset
            except Exception as e:
                logger.error(f"Failed to load period {period.name}: {e}")
                failed_periods.append(period.name)
        
        logger.info(f"Successfully loaded {len(datasets)} periods, {len(failed_periods)} failed")
        if failed_periods:
            logger.warning(f"Failed periods: {failed_periods}")
        
        return datasets
    
    async def stream_multiple_periods(self, periods: List[HistoricalPeriod],
                                    symbols: Optional[List[str]] = None,
                                    chunk_size: int = 5000) -> AsyncGenerator[Tuple[str, pd.DataFrame], None]:
        """
        Stream data from multiple periods for memory-efficient batch processing
        
        Args:
            periods: List of historical periods to stream
            symbols: Optional list of symbols to filter
            chunk_size: Number of rows per chunk
            
        Yields:
            Tuple[str, pd.DataFrame]: (period_name, data_chunk) pairs
        """
        logger.info(f"Starting streaming load for {len(periods)} periods")
        
        for period in periods:
            try:
                logger.debug(f"Streaming period: {period.name}")
                async for chunk in self.stream_period_data(period, symbols, chunk_size):
                    yield (period.name, chunk)
                    
                # Force garbage collection between periods
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error streaming period {period.name}: {e}")
                continue
        
        logger.info("Completed streaming all periods")
    
    def get_period_statistics(self, datasets: Dict[str, MarketDataset]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics across all loaded periods
        
        Args:
            datasets: Dictionary of period datasets
            
        Returns:
            Statistical summary of the datasets
        """
        stats = {
            'total_periods': len(datasets),
            'total_data_points': sum(d.total_data_points for d in datasets.values()),
            'period_statistics': {},
            'data_quality': {},
            'coverage_analysis': {}
        }
        
        # Per-period statistics
        for name, dataset in datasets.items():
            period_stats = {
                'data_points': dataset.total_data_points,
                'symbols_count': len(dataset.symbols),
                'date_range': dataset.date_range,
                'duration_days': dataset.period.duration_days,
                'data_quality_score': dataset.metadata.get('data_quality_score', 0.0)
            }
            stats['period_statistics'][name] = period_stats
        
        # Data quality analysis
        quality_scores = [d.metadata.get('data_quality_score', 0.0) for d in datasets.values()]
        stats['data_quality'] = {
            'avg_quality_score': np.mean(quality_scores) if quality_scores else 0.0,
            'min_quality_score': min(quality_scores) if quality_scores else 0.0,
            'max_quality_score': max(quality_scores) if quality_scores else 0.0,
            'quality_distribution': self._categorize_quality_scores(quality_scores)
        }
        
        # Coverage analysis
        all_symbols = set()
        for dataset in datasets.values():
            all_symbols.update(dataset.symbols)
        
        symbol_coverage = {}
        for symbol in all_symbols:
            periods_with_symbol = sum(1 for d in datasets.values() if symbol in d.symbols)
            symbol_coverage[symbol] = periods_with_symbol / len(datasets)
        
        stats['coverage_analysis'] = {
            'total_unique_symbols': len(all_symbols),
            'avg_symbol_coverage': np.mean(list(symbol_coverage.values())) if symbol_coverage else 0.0,
            'symbols_with_full_coverage': sum(1 for coverage in symbol_coverage.values() if coverage == 1.0),
            'symbols_with_partial_coverage': sum(1 for coverage in symbol_coverage.values() if 0 < coverage < 1.0)
        }
        
        return stats
    
    def export_period_summary(self, datasets: Dict[str, MarketDataset],
                            output_path: Optional[Path] = None) -> Path:
        """
        Export a comprehensive summary of loaded period data
        
        Args:
            datasets: Dictionary of period datasets
            output_path: Optional custom output path
            
        Returns:
            Path to exported summary file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(f"outputs/historical_analytics/data_summary_{timestamp}.json")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive summary
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'data_source': str(self.data_source_path),
            'periods_loaded': list(datasets.keys()),
            'statistics': self.get_period_statistics(datasets),
            'period_details': {}
        }
        
        # Add detailed period information
        for name, dataset in datasets.items():
            summary['period_details'][name] = {
                'period_info': asdict(dataset.period),
                'data_summary': {
                    'total_points': dataset.total_data_points,
                    'symbols': dataset.symbols,
                    'date_range': dataset.date_range
                },
                'metadata': dataset.metadata
            }
        
        # Export to JSON
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Exported data summary to: {output_path}")
        return output_path
    
    def _load_raw_data(self, start_date: str, end_date: str, 
                      symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """Load raw market data from source"""
        try:
            # Handle different data source types with chunked reading for memory efficiency
            if self.data_source_path.suffix == '.csv':
                # For large CSV files, use chunked reading
                chunks = []
                chunk_size = 10000  # Process 10K rows at a time
                
                for chunk in pd.read_csv(self.data_source_path, chunksize=chunk_size):
                    # Apply timestamp and date conversions early
                    if 'timestamp' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
                    elif 'date' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['date'])
                        chunk = chunk.drop('date', axis=1)
                    else:
                        raise ValueError("No timestamp or date column found in data")
                    
                    # Filter by date range early to reduce memory usage
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    filtered_chunk = chunk[(chunk['timestamp'] >= start_dt) & (chunk['timestamp'] <= end_dt)]
                    
                    # Filter by symbols if specified
                    if symbols is not None and 'symbol' in filtered_chunk.columns:
                        filtered_chunk = filtered_chunk[filtered_chunk['symbol'].isin(symbols)]
                    
                    if not filtered_chunk.empty:
                        chunks.append(filtered_chunk)
                
                # Combine chunks if any data found
                if chunks:
                    data = pd.concat(chunks, ignore_index=True)
                    # Clean up chunks from memory
                    del chunks
                    gc.collect()
                else:
                    data = pd.DataFrame()
                    
            elif self.data_source_path.suffix == '.parquet':
                # Parquet files typically handle memory more efficiently
                data = pd.read_parquet(self.data_source_path)
                
                # Apply date filtering and conversions
                if 'timestamp' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['timestamp'])
                elif 'date' in data.columns:
                    data['timestamp'] = pd.to_datetime(data['date'])
                    data = data.drop('date', axis=1)
                else:
                    raise ValueError("No timestamp or date column found in data")
                
                # Filter by date range
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                data = data[(data['timestamp'] >= start_dt) & (data['timestamp'] <= end_dt)]
                
                # Filter by symbols if specified
                if symbols is not None and 'symbol' in data.columns:
                    data = data[data['symbol'].isin(symbols)]
            else:
                # Assume CSV if no extension, use chunked reading
                chunks = []
                chunk_size = 10000
                
                for chunk in pd.read_csv(self.data_source_path, chunksize=chunk_size):
                    # Apply timestamp and date conversions early
                    if 'timestamp' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
                    elif 'date' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['date'])
                        chunk = chunk.drop('date', axis=1)
                    else:
                        raise ValueError("No timestamp or date column found in data")
                    
                    # Filter by date range early
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    filtered_chunk = chunk[(chunk['timestamp'] >= start_dt) & (chunk['timestamp'] <= end_dt)]
                    
                    # Filter by symbols if specified
                    if symbols is not None and 'symbol' in filtered_chunk.columns:
                        filtered_chunk = filtered_chunk[filtered_chunk['symbol'].isin(symbols)]
                    
                    if not filtered_chunk.empty:
                        chunks.append(filtered_chunk)
                
                # Combine chunks if any data found
                if chunks:
                    data = pd.concat(chunks, ignore_index=True)
                    del chunks
                    gc.collect()
                else:
                    data = pd.DataFrame()

            return data
            
        except Exception as e:
            logger.error(f"Error loading raw data: {e}")
            raise
    
    async def stream_period_data(self, period: HistoricalPeriod, 
                                symbols: Optional[List[str]] = None,
                                chunk_size: int = 5000) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Stream period data in chunks for memory-efficient processing of large datasets
        
        Args:
            period: Historical period to load
            symbols: Optional list of symbols to filter
            chunk_size: Number of rows per chunk
            
        Yields:
            pd.DataFrame: Chunks of market data
        """
        logger.info(f"Starting streaming data load for period {period.name}")
        
        try:
            start_dt = pd.to_datetime(period.start_date)
            end_dt = pd.to_datetime(period.end_date)
            
            if self.data_source_path.suffix == '.csv':
                # Stream CSV data
                for chunk in pd.read_csv(self.data_source_path, chunksize=chunk_size):
                    # Process chunk
                    if 'timestamp' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['timestamp'])
                    elif 'date' in chunk.columns:
                        chunk['timestamp'] = pd.to_datetime(chunk['date'])
                        chunk = chunk.drop('date', axis=1)
                    else:
                        continue  # Skip chunks without timestamp
                    
                    # Filter by date range
                    filtered_chunk = chunk[(chunk['timestamp'] >= start_dt) & (chunk['timestamp'] <= end_dt)]
                    
                    # Filter by symbols if specified
                    if symbols is not None and 'symbol' in filtered_chunk.columns:
                        filtered_chunk = filtered_chunk[filtered_chunk['symbol'].isin(symbols)]
                    
                    if not filtered_chunk.empty:
                        # Validate and clean chunk
                        cleaned_chunk = self._validate_and_clean_data(filtered_chunk, period)
                        if not cleaned_chunk.empty:
                            # Enrich with derived features
                            enriched_chunk = self._enrich_market_data(cleaned_chunk)
                            yield enriched_chunk
                    
                    # Allow other async operations to run
                    await asyncio.sleep(0)
            else:
                # For non-CSV files, fall back to loading all at once but yield in chunks
                data = self._load_raw_data(period.start_date, period.end_date, symbols)
                cleaned_data = self._validate_and_clean_data(data, period)
                enriched_data = self._enrich_market_data(cleaned_data)
                
                # Yield in chunks
                for i in range(0, len(enriched_data), chunk_size):
                    chunk = enriched_data.iloc[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0)
                    
        except Exception as e:
            logger.error(f"Error streaming data for period {period.name}: {e}")
            raise
    
    def _validate_and_clean_data(self, data: pd.DataFrame, period: HistoricalPeriod) -> pd.DataFrame:
        """Validate and clean market data"""
        original_length = len(data)
        
        # Check required columns
        missing_columns = [col for col in self.required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Remove rows with missing critical data
        critical_columns = ['timestamp', 'symbol', 'close']
        data = data.dropna(subset=critical_columns)
        
        # Remove invalid prices (negative or zero)
        data = data[data['close'] > 0]
        
        # Remove invalid volumes (negative)
        if 'volume' in data.columns:
            data = data[data['volume'] >= 0]
        
        # Sort by timestamp and symbol
        data = data.sort_values(['timestamp', 'symbol'])
        
        # Check minimum data requirement
        if len(data) < self.min_data_points_per_period:
            raise ValueError(
                f"Insufficient data for period {period.name}: "
                f"{len(data)} < {self.min_data_points_per_period} required"
            )
        
        cleaned_length = len(data)
        cleaning_loss = (original_length - cleaned_length) / original_length
        
        if cleaning_loss > 0.3:  # More than 30% data loss
            logger.warning(
                f"High data loss during cleaning for period {period.name}: "
                f"{cleaning_loss:.1%} ({original_length} -> {cleaned_length})"
            )
        
        logger.debug(f"Data cleaning completed: {cleaned_length} records retained")
        return data
    
    def _enrich_market_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add derived features to market data"""
        enriched_data = data.copy()
        
        # Calculate returns if not present
        if 'returns' not in enriched_data.columns and 'close' in enriched_data.columns:
            enriched_data = enriched_data.sort_values(['symbol', 'timestamp'])
            enriched_data['returns'] = enriched_data.groupby('symbol')['close'].pct_change()
        
        # Calculate rolling volatility
        if 'volatility' not in enriched_data.columns and 'returns' in enriched_data.columns:
            enriched_data['volatility'] = (
                enriched_data.groupby('symbol')['returns']
                .rolling(window=20, min_periods=5)
                .std() * np.sqrt(252)  # Annualized volatility
            ).reset_index(level=0, drop=True)
        
        # Add price momentum indicators
        if 'close' in enriched_data.columns:
            for window in [5, 20, 60]:
                col_name = f'momentum_{window}d'
                enriched_data[col_name] = (
                    enriched_data.groupby('symbol')['close']
                    .pct_change(periods=window)
                )
        
        # Add volume indicators
        if 'volume' in enriched_data.columns:
            enriched_data['volume_ma_20'] = (
                enriched_data.groupby('symbol')['volume']
                .rolling(window=20, min_periods=5)
                .mean()
            ).reset_index(level=0, drop=True)
            
            enriched_data['volume_ratio'] = (
                enriched_data['volume'] / enriched_data['volume_ma_20']
            )
        
        # Remove any infinite or extremely large values
        enriched_data = enriched_data.replace([np.inf, -np.inf], np.nan)
        
        return enriched_data
    
    def _calculate_data_quality_score(self, data: pd.DataFrame) -> float:
        """Calculate a data quality score for the dataset"""
        if data.empty:
            return 0.0
        
        # Factors contributing to quality score
        factors = {}
        
        # 1. Completeness (no missing values in key columns)
        key_columns = ['timestamp', 'symbol', 'close']
        missing_ratio = data[key_columns].isnull().sum().sum() / (len(data) * len(key_columns))
        factors['completeness'] = max(0, 1 - missing_ratio)
        
        # 2. Consistency (reasonable price movements)
        if 'returns' in data.columns:
            extreme_returns = (data['returns'].abs() > 0.5).sum() / len(data)  # >50% daily moves
            factors['consistency'] = max(0, 1 - extreme_returns * 10)  # Penalize extreme moves
        else:
            factors['consistency'] = 0.8  # Default if no returns
        
        # 3. Coverage (data points per day)
        if 'timestamp' in data.columns:
            date_range = (data['timestamp'].max() - data['timestamp'].min()).days
            expected_points = date_range * len(data['symbol'].unique()) if 'symbol' in data.columns else date_range
            coverage_ratio = len(data) / max(expected_points, 1)
            factors['coverage'] = min(1.0, coverage_ratio)
        else:
            factors['coverage'] = 0.5
        
        # 4. Diversity (number of symbols)
        if 'symbol' in data.columns:
            symbol_count = data['symbol'].nunique()
            factors['diversity'] = min(1.0, symbol_count / 100)  # Normalize to 100 symbols
        else:
            factors['diversity'] = 0.5
        
        # Weighted average
        weights = {'completeness': 0.3, 'consistency': 0.3, 'coverage': 0.2, 'diversity': 0.2}
        quality_score = sum(factors[k] * weights[k] for k in factors)
        
        return round(quality_score, 3)
    
    def _categorize_quality_scores(self, scores: List[float]) -> Dict[str, int]:
        """Categorize quality scores into bins"""
        if not scores:
            return {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        categories = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
        
        for score in scores:
            if score >= 0.9:
                categories['excellent'] += 1
            elif score >= 0.7:
                categories['good'] += 1
            elif score >= 0.5:
                categories['fair'] += 1
            else:
                categories['poor'] += 1
        
        return categories
    
    def _get_default_periods(self) -> Dict[str, Any]:
        """Get default historical periods for analysis"""
        return {
            'periods': [
                {
                    'name': '2008_financial_crisis',
                    'start_date': '2008-01-01',
                    'end_date': '2009-12-31',
                    'regime_hint': 'high_volatility',
                    'description': 'Global Financial Crisis period with extreme market stress',
                    'category': 'crisis'
                },
                {
                    'name': '2010_2012_recovery',
                    'start_date': '2010-01-01',
                    'end_date': '2012-12-31',
                    'regime_hint': 'bull_market',
                    'description': 'Post-crisis recovery period',
                    'category': 'bull'
                },
                {
                    'name': '2015_2016_volatility',
                    'start_date': '2015-01-01',
                    'end_date': '2016-12-31',
                    'regime_hint': 'high_volatility',
                    'description': 'Period of increased market volatility',
                    'category': 'volatile'
                },
                {
                    'name': '2017_2019_bull_run',
                    'start_date': '2017-01-01',
                    'end_date': '2019-12-31',
                    'regime_hint': 'bull_market',
                    'description': 'Extended bull market period',
                    'category': 'bull'
                },
                {
                    'name': '2020_covid_crash',
                    'start_date': '2020-01-01',
                    'end_date': '2020-12-31',
                    'regime_hint': 'high_volatility',
                    'description': 'COVID-19 pandemic market disruption',
                    'category': 'crisis'
                },
                {
                    'name': '2021_2022_mixed',
                    'start_date': '2021-01-01',
                    'end_date': '2022-12-31',
                    'regime_hint': 'sideways_market',
                    'description': 'Mixed market conditions with policy changes',
                    'category': 'sideways'
                }
            ]
        }


class DataValidationEngine:
    """
    Specialized engine for comprehensive data validation and quality assessment
    """
    
    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()
    
    def validate_dataset_compatibility(self, datasets: Dict[str, MarketDataset]) -> Dict[str, Any]:
        """
        Validate compatibility across multiple datasets for cross-period analysis
        
        Args:
            datasets: Dictionary of period datasets
            
        Returns:
            Validation report with compatibility assessment
        """
        report = {
            'overall_compatibility': True,
            'symbol_consistency': {},
            'data_structure_consistency': {},
            'temporal_consistency': {},
            'recommendations': []
        }
        
        # Symbol consistency check
        all_symbols = set()
        symbol_coverage = {}
        
        for name, dataset in datasets.items():
            all_symbols.update(dataset.symbols)
            for symbol in dataset.symbols:
                if symbol not in symbol_coverage:
                    symbol_coverage[symbol] = []
                symbol_coverage[symbol].append(name)
        
        # Analyze symbol coverage
        full_coverage_symbols = [s for s, periods in symbol_coverage.items() if len(periods) == len(datasets)]
        partial_coverage_symbols = [s for s, periods in symbol_coverage.items() if 0 < len(periods) < len(datasets)]
        
        report['symbol_consistency'] = {
            'total_unique_symbols': len(all_symbols),
            'full_coverage_symbols': len(full_coverage_symbols),
            'partial_coverage_symbols': len(partial_coverage_symbols),
            'coverage_ratio': len(full_coverage_symbols) / len(all_symbols) if all_symbols else 0
        }
        
        if len(full_coverage_symbols) < 10:
            report['overall_compatibility'] = False
            report['recommendations'].append(
                f"Only {len(full_coverage_symbols)} symbols have full coverage across all periods. "
                "Consider expanding symbol list or adjusting period selection."
            )
        
        return report
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules for data quality assessment"""
        return {
            'min_data_points_per_period': 100,
            'max_daily_return_threshold': 0.5,  # 50% daily move threshold
            'min_symbols_per_period': 5,
            'max_missing_data_ratio': 0.1,  # 10% missing data threshold
            'min_quality_score': 0.5
        }