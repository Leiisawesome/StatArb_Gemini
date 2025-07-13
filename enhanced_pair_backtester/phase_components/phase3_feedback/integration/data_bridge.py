"""
Data Bridge Layer for ClickHouse-Enhanced Backtester Integration
===============================================================

This module provides data transformation and bridge functionality between
ClickHouse screening results and enhanced backtester input format.

Key Features:
- Seamless data format conversion
- Data validation and quality checks
- Performance optimization
- Error handling and recovery
- Caching for improved performance
- Batch processing capabilities

Author: Pro Quant Desk Trader
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import pickle
from pathlib import Path
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class DataQualityLevel(Enum):
    """Data quality assessment levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"

@dataclass
class DataQualityMetrics:
    """Metrics for data quality assessment"""
    completeness: float  # 0-1, percentage of non-null values
    consistency: float   # 0-1, consistency across time series
    accuracy: float      # 0-1, accuracy based on validation rules
    timeliness: float    # 0-1, how recent the data is
    uniqueness: float    # 0-1, percentage of unique values
    validity: float      # 0-1, percentage of valid values
    overall_score: float # 0-1, weighted average
    quality_level: DataQualityLevel
    issues: List[str]    # List of identified issues

@dataclass
class ScreeningDataPoint:
    """Single screening result data point"""
    pair: Tuple[str, str]
    timestamp: datetime
    correlation: float
    cointegration_pvalue: float
    hedge_ratio: float
    spread_mean: float
    spread_std: float
    regime_score: float
    liquidity_score: float
    transaction_cost_bps: float
    composite_score: float
    
    # Additional metrics
    volatility: float = 0.0
    volume_ratio: float = 1.0
    price_ratio: float = 1.0
    market_cap_ratio: float = 1.0
    
    # Quality metrics
    data_quality: Optional[DataQualityMetrics] = None

@dataclass
class BacktestDataPoint:
    """Single backtest input data point"""
    symbol1: str
    symbol2: str
    timestamp: datetime
    price1: float
    price2: float
    volume1: float = 0.0
    volume2: float = 0.0
    
    # Calculated fields
    spread: float = 0.0
    z_score: float = 0.0
    returns1: float = 0.0
    returns2: float = 0.0
    
    # Metadata
    data_source: str = "clickhouse"
    quality_score: float = 1.0

@dataclass
class BridgeConfiguration:
    """Configuration for data bridge operations"""
    # Data validation settings
    min_correlation: float = 0.1
    max_correlation: float = 0.99
    min_cointegration_pvalue: float = 0.001
    max_cointegration_pvalue: float = 0.10
    min_data_points: int = 100
    max_missing_data_pct: float = 0.05
    
    # Quality thresholds
    min_quality_score: float = 0.6
    quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'completeness': 0.25,
        'consistency': 0.20,
        'accuracy': 0.20,
        'timeliness': 0.15,
        'uniqueness': 0.10,
        'validity': 0.10
    })
    
    # Performance settings
    batch_size: int = 1000
    max_workers: int = 4
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # Output settings
    save_intermediate_results: bool = True
    output_format: str = "pandas"  # pandas, dict, json

class DataBridge:
    """
    Main data bridge class for converting between ClickHouse screening
    and enhanced backtester formats.
    """
    
    def __init__(self, config: Optional[BridgeConfiguration] = None):
        self.config = config or BridgeConfiguration()
        self.cache = {}
        self.cache_timestamps = {}
        
        # Statistics
        self.conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_conversion_time': 0.0,
            'data_quality_distribution': {}
        }
        
        logger.info("DataBridge initialized")
    
    def convert_screening_to_backtest_input(self, 
                                          screening_results: List[ScreeningDataPoint],
                                          price_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Convert screening results to backtest input format.
        
        Args:
            screening_results: List of screening data points
            price_data: Optional price data for validation
            
        Returns:
            Dictionary containing converted data and metadata
        """
        start_time = datetime.now()
        
        try:
            # Validate input data
            validated_results = self._validate_screening_data(screening_results)
            
            # Convert to backtest format
            backtest_pairs = self._extract_pairs_for_backtesting(validated_results)
            
            # Generate synthetic or load real price data
            if price_data is None:
                price_data = self._generate_synthetic_price_data(backtest_pairs)
            
            # Create backtest input structure
            backtest_input = self._create_backtest_input(backtest_pairs, price_data)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_conversion_quality(validated_results, backtest_input)
            
            # Update statistics
            conversion_time = (datetime.now() - start_time).total_seconds()
            self._update_conversion_stats(len(screening_results), True, conversion_time)
            
            result = {
                'pairs': backtest_pairs,
                'price_data': price_data,
                'backtest_input': backtest_input,
                'quality_metrics': quality_metrics,
                'metadata': {
                    'source_count': len(screening_results),
                    'converted_count': len(backtest_pairs),
                    'conversion_time': conversion_time,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            logger.info(f"Successfully converted {len(screening_results)} screening results to backtest format")
            return result
            
        except Exception as e:
            self._update_conversion_stats(len(screening_results), False, 0.0)
            logger.error(f"Conversion failed: {e}")
            raise
    
    def _validate_screening_data(self, screening_results: List[ScreeningDataPoint]) -> List[ScreeningDataPoint]:
        """Validate screening data quality"""
        validated_results = []
        
        for result in screening_results:
            try:
                # Basic validation
                if not self._is_valid_pair(result.pair):
                    continue
                
                # Correlation validation
                if not (self.config.min_correlation <= abs(result.correlation) <= self.config.max_correlation):
                    continue
                
                # Cointegration validation
                if not (self.config.min_cointegration_pvalue <= result.cointegration_pvalue <= self.config.max_cointegration_pvalue):
                    continue
                
                # Calculate data quality metrics
                quality_metrics = self._assess_data_quality(result)
                result.data_quality = quality_metrics
                
                # Quality threshold check
                if quality_metrics.overall_score >= self.config.min_quality_score:
                    validated_results.append(result)
                
            except Exception as e:
                logger.warning(f"Validation failed for pair {result.pair}: {e}")
                continue
        
        logger.info(f"Validated {len(validated_results)} out of {len(screening_results)} screening results")
        return validated_results
    
    def _is_valid_pair(self, pair: Tuple[str, str]) -> bool:
        """Check if pair is valid for backtesting"""
        if not pair or len(pair) != 2:
            return False
        
        symbol1, symbol2 = pair
        
        # Check symbol format
        if not symbol1 or not symbol2 or symbol1 == symbol2:
            return False
        
        # Check symbol length (reasonable limits)
        if len(symbol1) > 10 or len(symbol2) > 10:
            return False
        
        # Check for valid characters (alphanumeric)
        if not symbol1.isalnum() or not symbol2.isalnum():
            return False
        
        return True
    
    def _assess_data_quality(self, screening_result: ScreeningDataPoint) -> DataQualityMetrics:
        """Assess data quality for a screening result"""
        issues = []
        
        # Completeness check
        required_fields = ['correlation', 'cointegration_pvalue', 'hedge_ratio', 'spread_mean', 'spread_std']
        non_null_count = sum(1 for field in required_fields if getattr(screening_result, field) is not None)
        completeness = non_null_count / len(required_fields)
        
        if completeness < 1.0:
            issues.append(f"Missing data in {len(required_fields) - non_null_count} fields")
        
        # Consistency check
        consistency = 1.0
        if screening_result.correlation is not None and abs(screening_result.correlation) > 1.0:
            consistency -= 0.5
            issues.append("Correlation value out of valid range")
        
        if screening_result.cointegration_pvalue is not None and not (0.0 <= screening_result.cointegration_pvalue <= 1.0):
            consistency -= 0.3
            issues.append("Cointegration p-value out of valid range")
        
        # Accuracy check (based on statistical relationships)
        accuracy = 1.0
        if (screening_result.correlation is not None and 
            screening_result.cointegration_pvalue is not None):
            # High correlation should generally correspond to low p-value
            if abs(screening_result.correlation) > 0.7 and screening_result.cointegration_pvalue > 0.05:
                accuracy -= 0.2
                issues.append("Inconsistent correlation and cointegration values")
        
        # Timeliness check
        time_diff = (datetime.now() - screening_result.timestamp).total_seconds()
        timeliness = max(0.0, 1.0 - time_diff / 86400)  # Decay over 24 hours
        
        if timeliness < 0.5:
            issues.append("Data is more than 12 hours old")
        
        # Uniqueness check (always 1.0 for individual records)
        uniqueness = 1.0
        
        # Validity check
        validity = 1.0
        if screening_result.composite_score < 0 or screening_result.composite_score > 1:
            validity -= 0.3
            issues.append("Composite score out of valid range")
        
        # Calculate overall score
        weights = self.config.quality_weights
        overall_score = (
            weights['completeness'] * completeness +
            weights['consistency'] * consistency +
            weights['accuracy'] * accuracy +
            weights['timeliness'] * timeliness +
            weights['uniqueness'] * uniqueness +
            weights['validity'] * validity
        )
        
        # Determine quality level
        if overall_score >= 0.9:
            quality_level = DataQualityLevel.EXCELLENT
        elif overall_score >= 0.8:
            quality_level = DataQualityLevel.GOOD
        elif overall_score >= 0.6:
            quality_level = DataQualityLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            quality_level = DataQualityLevel.POOR
        else:
            quality_level = DataQualityLevel.UNUSABLE
        
        return DataQualityMetrics(
            completeness=completeness,
            consistency=consistency,
            accuracy=accuracy,
            timeliness=timeliness,
            uniqueness=uniqueness,
            validity=validity,
            overall_score=overall_score,
            quality_level=quality_level,
            issues=issues
        )
    
    def _extract_pairs_for_backtesting(self, validated_results: List[ScreeningDataPoint]) -> List[Tuple[str, str]]:
        """Extract pairs suitable for backtesting"""
        # Sort by composite score
        sorted_results = sorted(validated_results, key=lambda x: x.composite_score, reverse=True)
        
        # Extract unique pairs
        pairs = []
        seen_pairs = set()
        
        for result in sorted_results:
            pair = result.pair
            reversed_pair = (pair[1], pair[0])
            
            if pair not in seen_pairs and reversed_pair not in seen_pairs:
                pairs.append(pair)
                seen_pairs.add(pair)
        
        logger.info(f"Extracted {len(pairs)} unique pairs for backtesting")
        return pairs
    
    def _generate_synthetic_price_data(self, pairs: List[Tuple[str, str]]) -> pd.DataFrame:
        """Generate synthetic price data for backtesting"""
        # Create date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        date_range = pd.date_range(start=start_date, end=end_date, freq='5min')
        
        # Generate data for all symbols
        all_symbols = set()
        for pair in pairs:
            all_symbols.update(pair)
        
        data = {}
        
        for symbol in all_symbols:
            # Generate realistic price series
            np.random.seed(hash(symbol) % 2**32)  # Reproducible but symbol-specific
            
            # Starting price
            base_price = 50 + np.random.uniform(-20, 50)
            
            # Generate returns with realistic properties
            returns = np.random.normal(0, 0.002, len(date_range))  # 0.2% volatility
            
            # Add some autocorrelation
            for i in range(1, len(returns)):
                returns[i] += 0.1 * returns[i-1]
            
            # Convert to prices
            prices = base_price * np.exp(np.cumsum(returns))
            
            # Add some volume data
            base_volume = 100000 + np.random.uniform(0, 50000)
            volume = base_volume * (1 + np.random.uniform(-0.5, 0.5, len(date_range)))
            
            data[f"{symbol}_price"] = prices
            data[f"{symbol}_volume"] = volume
        
        # Create DataFrame
        df = pd.DataFrame(data, index=date_range)
        df.index.name = 'timestamp'
        
        logger.info(f"Generated synthetic price data for {len(all_symbols)} symbols")
        return df
    
    def _create_backtest_input(self, pairs: List[Tuple[str, str]], price_data: pd.DataFrame) -> Dict[str, Any]:
        """Create structured backtest input"""
        backtest_input = {
            'pairs': pairs,
            'data': {},
            'metadata': {
                'data_frequency': '5min',
                                 'start_date': str(price_data.index[0]),
                 'end_date': str(price_data.index[-1]),
                'total_observations': len(price_data),
                'symbols': list(set([symbol for pair in pairs for symbol in pair]))
            }
        }
        
        # Process each pair
        for pair in pairs:
            symbol1, symbol2 = pair
            pair_key = f"{symbol1}_{symbol2}"
            
            # Extract price data
            price1_col = f"{symbol1}_price"
            price2_col = f"{symbol2}_price"
            volume1_col = f"{symbol1}_volume"
            volume2_col = f"{symbol2}_volume"
            
            if price1_col in price_data.columns and price2_col in price_data.columns:
                pair_data = pd.DataFrame({
                    'timestamp': price_data.index,
                    'price1': price_data[price1_col],
                    'price2': price_data[price2_col],
                    'volume1': price_data.get(volume1_col, 0),
                    'volume2': price_data.get(volume2_col, 0)
                })
                
                # Calculate additional metrics
                pair_data['spread'] = pair_data['price1'] - pair_data['price2']
                pair_data['returns1'] = pair_data['price1'].pct_change()
                pair_data['returns2'] = pair_data['price2'].pct_change()
                
                # Calculate z-score
                spread_mean = pair_data['spread'].mean()
                spread_std = pair_data['spread'].std()
                pair_data['z_score'] = (pair_data['spread'] - spread_mean) / spread_std
                
                # Remove NaN values
                pair_data = pair_data.dropna()
                
                backtest_input['data'][pair_key] = pair_data
        
        logger.info(f"Created backtest input for {len(backtest_input['data'])} pairs")
        return backtest_input
    
    def _calculate_conversion_quality(self, screening_results: List[ScreeningDataPoint], 
                                    backtest_input: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall conversion quality metrics"""
        if not screening_results:
            return {'overall_quality': 0.0, 'quality_distribution': {}}
        
        # Calculate quality distribution
        quality_levels = [result.data_quality.quality_level.value for result in screening_results if result.data_quality]
        quality_distribution = {}
        
        for level in DataQualityLevel:
            quality_distribution[level.value] = quality_levels.count(level.value)
        
        # Calculate overall quality score
        quality_scores = [result.data_quality.overall_score for result in screening_results if result.data_quality]
        overall_quality = np.mean(quality_scores) if quality_scores else 0.0
        
        # Calculate conversion efficiency
        conversion_efficiency = len(backtest_input['data']) / len(screening_results)
        
        return {
            'overall_quality': overall_quality,
            'quality_distribution': quality_distribution,
            'conversion_efficiency': conversion_efficiency,
            'average_quality_score': overall_quality,
            'total_pairs_processed': len(screening_results),
            'successful_conversions': len(backtest_input['data']),
            'quality_issues': self._aggregate_quality_issues(screening_results)
        }
    
    def _aggregate_quality_issues(self, screening_results: List[ScreeningDataPoint]) -> Dict[str, int]:
        """Aggregate quality issues across all results"""
        issue_counts = {}
        
        for result in screening_results:
            if result.data_quality and result.data_quality.issues:
                for issue in result.data_quality.issues:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        return issue_counts
    
    def _update_conversion_stats(self, input_count: int, success: bool, conversion_time: float):
        """Update conversion statistics"""
        self.conversion_stats['total_conversions'] += 1
        
        if success:
            self.conversion_stats['successful_conversions'] += 1
        else:
            self.conversion_stats['failed_conversions'] += 1
        
        # Update average conversion time
        total_time = (self.conversion_stats['average_conversion_time'] * 
                     (self.conversion_stats['total_conversions'] - 1) + conversion_time)
        self.conversion_stats['average_conversion_time'] = total_time / self.conversion_stats['total_conversions']
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """Get current conversion statistics"""
        return self.conversion_stats.copy()
    
    def clear_cache(self):
        """Clear conversion cache"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Conversion cache cleared")
    
    def save_conversion_results(self, results: Dict[str, Any], filename: str):
        """Save conversion results to file"""
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if filepath.suffix.lower() == '.json':
            # Convert non-serializable objects
            serializable_results = self._make_serializable(results)
            with open(filepath, 'w') as f:
                json.dump(serializable_results, f, indent=2)
        elif filepath.suffix.lower() == '.pkl':
            with open(filepath, 'wb') as f:
                pickle.dump(results, f)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")
        
        logger.info(f"Conversion results saved to {filename}")
    
    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
                 elif hasattr(obj, 'item') and callable(getattr(obj, 'item')):
            return obj.item()
        elif isinstance(obj, DataQualityLevel):
            return obj.value
        else:
            return obj
    
    def load_conversion_results(self, filename: str) -> Dict[str, Any]:
        """Load conversion results from file"""
        filepath = Path(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        if filepath.suffix.lower() == '.json':
            with open(filepath, 'r') as f:
                return json.load(f)
        elif filepath.suffix.lower() == '.pkl':
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")
    
    async def convert_screening_to_backtest_async(self, 
                                                screening_results: List[ScreeningDataPoint],
                                                price_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Asynchronous version of screening to backtest conversion"""
        loop = asyncio.get_event_loop()
        
        # Run conversion in thread pool
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            result = await loop.run_in_executor(
                executor,
                self.convert_screening_to_backtest_input,
                screening_results,
                price_data
            )
        
        return result
    
    def batch_convert_screening_results(self, 
                                      screening_results: List[ScreeningDataPoint],
                                      batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Convert screening results in batches"""
        batch_size = batch_size or self.config.batch_size
        results = []
        
        for i in range(0, len(screening_results), batch_size):
            batch = screening_results[i:i + batch_size]
            try:
                batch_result = self.convert_screening_to_backtest_input(batch)
                results.append(batch_result)
            except Exception as e:
                logger.error(f"Batch conversion failed for batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Completed batch conversion: {len(results)} successful batches")
        return results

# Utility functions
def create_screening_data_point(pair: Tuple[str, str], 
                              correlation: float,
                              cointegration_pvalue: float,
                              **kwargs) -> ScreeningDataPoint:
    """Create a screening data point with defaults"""
    return ScreeningDataPoint(
        pair=pair,
        timestamp=datetime.now(),
        correlation=correlation,
        cointegration_pvalue=cointegration_pvalue,
        hedge_ratio=kwargs.get('hedge_ratio', 1.0),
        spread_mean=kwargs.get('spread_mean', 0.0),
        spread_std=kwargs.get('spread_std', 1.0),
        regime_score=kwargs.get('regime_score', 0.5),
        liquidity_score=kwargs.get('liquidity_score', 0.5),
        transaction_cost_bps=kwargs.get('transaction_cost_bps', 30.0),
        composite_score=kwargs.get('composite_score', 0.5),
        volatility=kwargs.get('volatility', 0.02),
        volume_ratio=kwargs.get('volume_ratio', 1.0),
        price_ratio=kwargs.get('price_ratio', 1.0),
        market_cap_ratio=kwargs.get('market_cap_ratio', 1.0)
    )

def create_test_screening_data(num_pairs: int = 10) -> List[ScreeningDataPoint]:
    """Create test screening data for development"""
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'ADBE', 'CRM']
    screening_data = []
    
    for i in range(num_pairs):
        symbol1 = test_symbols[i % len(test_symbols)]
        symbol2 = test_symbols[(i + 1) % len(test_symbols)]
        
        # Generate realistic values
        correlation = np.random.uniform(0.3, 0.8)
        cointegration_pvalue = np.random.uniform(0.01, 0.05)
        composite_score = np.random.uniform(0.5, 0.9)
        
        data_point = create_screening_data_point(
            pair=(symbol1, symbol2),
            correlation=correlation,
            cointegration_pvalue=cointegration_pvalue,
            composite_score=composite_score,
            liquidity_score=np.random.uniform(0.6, 0.9),
            transaction_cost_bps=np.random.uniform(20, 40)
        )
        
        screening_data.append(data_point)
    
    return screening_data

# Example usage
if __name__ == "__main__":
    # Create data bridge
    bridge = DataBridge()
    
    # Create test data
    test_data = create_test_screening_data(5)
    
    # Convert to backtest format
    result = bridge.convert_screening_to_backtest_input(test_data)
    
    # Display results
    print(f"Conversion completed successfully!")
    print(f"Converted {result['metadata']['source_count']} screening results")
    print(f"Generated {result['metadata']['converted_count']} backtest pairs")
    print(f"Overall quality: {result['quality_metrics']['overall_quality']:.3f}")
    
    # Display pairs
    print("\nConverted pairs:")
    for i, pair in enumerate(result['pairs'][:5], 1):
        print(f"{i}. {pair[0]} / {pair[1]}")
    
    # Display statistics
    stats = bridge.get_conversion_stats()
    print(f"\nConversion Statistics:")
    print(f"Total conversions: {stats['total_conversions']}")
    print(f"Success rate: {stats['successful_conversions']}/{stats['total_conversions']}")
    print(f"Average conversion time: {stats['average_conversion_time']:.3f} seconds") 