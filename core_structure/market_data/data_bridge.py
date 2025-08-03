"""
DataBridge: Core System ↔ Backtesting Framework Integration

This module provides a bridge between the core system's market data management
and the backtesting framework's data requirements. It ensures data consistency
between production and backtesting environments.

Key Features:
- Production-to-backtesting data bridging
- Data quality monitoring and validation
- Regime detection integration
- Performance optimization for backtesting
- Error handling and recovery
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
from enum import Enum

from .data_manager import DataManager
from .data_processor import DataProcessor
from .data_quality_monitor import DataQualityMonitor
from .market_data_analytics import MarketDataAnalytics
from .performance_integration import PerformanceIntegration
from .feeds import BaseFeed, MarketTick

logger = logging.getLogger(__name__)


class DataMode(Enum):
    """Data bridge operation modes"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"


class DataQualityLevel(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class DataBridgeConfig:
    """Configuration for DataBridge"""
    
    # Data mode settings
    data_mode: DataMode = DataMode.BACKTESTING
    
    # Data management settings
    enable_data_quality_monitoring: bool = True
    enable_regime_detection: bool = True
    enable_performance_tracking: bool = True
    
    # Quality thresholds
    min_data_quality_score: float = 0.7
    max_missing_data_pct: float = 0.05  # 5%
    max_latency_ms: float = 100.0
    
    # Performance settings
    max_concurrent_requests: int = 20
    timeout_seconds: float = 10.0
    cache_size: int = 5000
    
    # Data retention
    data_retention_days: int = 30
    max_memory_usage_mb: int = 1024
    
    # Validation settings
    validate_data_consistency: bool = True
    enable_data_validation: bool = True
    
    # Logging settings
    log_performance: bool = True
    log_errors: bool = True


@dataclass
class DataBridgeResult:
    """Result from DataBridge data operations"""
    
    symbol: str
    data_type: str  # 'market_data', 'quality_metrics', 'regime_data'
    data: Union[pd.DataFrame, Dict[str, Any]]
    quality_score: float
    timestamp: datetime
    source: str  # 'production', 'backtesting', 'cached'
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class DataQualityReport:
    """Data quality report from DataBridge"""
    
    overall_quality_score: float
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    quality_level: DataQualityLevel
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DataConsistencyReport:
    """Data consistency report between production and backtesting"""
    
    consistency_score: float
    production_data_points: int
    backtesting_data_points: int
    missing_data_points: int
    inconsistent_data_points: int
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class DataBridge:
    """
    Bridge between core system market data management and backtesting framework.
    
    This class provides:
    1. Production-to-backtesting data bridging
    2. Data quality monitoring and validation
    3. Regime detection integration
    4. Performance optimization
    5. Error handling and recovery
    """
    
    def __init__(self, config: Optional[DataBridgeConfig] = None):
        """Initialize DataBridge with configuration"""
        self.config = config or DataBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.DataBridge")
        
        # Initialize core system components
        self._initialize_core_components()
        
        # Initialize caching and performance tracking
        self._data_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._performance_stats = {
            'total_requests': 0,
            'production_requests': 0,
            'backtesting_requests': 0,
            'cached_requests': 0,
            'errors': 0,
            'avg_processing_time': 0.0,
            'total_data_points': 0
        }
        
        # Thread pool for concurrent operations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests)
        
        self.logger.info(f"DataBridge initialized in {self.config.data_mode.value} mode")
    
    def _initialize_core_components(self):
        """Initialize core system data management components"""
        try:
            # Initialize data manager
            self.data_manager = DataManager()
            
            # Initialize data processor with empty config
            try:
                self.data_processor = DataProcessor({})
            except TypeError:
                # If DataProcessor doesn't require config, initialize without it
                self.data_processor = DataProcessor()
            
            # Initialize data quality monitor
            if self.config.enable_data_quality_monitoring:
                try:
                    self.data_quality_monitor = DataQualityMonitor()
                except Exception:
                    self.logger.warning("DataQualityMonitor initialization failed, continuing without it")
                    self.data_quality_monitor = None
            
            # Initialize market data analytics
            if self.config.enable_performance_tracking:
                try:
                    self.market_data_analytics = MarketDataAnalytics()
                    self.performance_integration = PerformanceIntegration()
                except Exception:
                    self.logger.warning("Analytics components initialization failed, continuing without them")
                    self.market_data_analytics = None
                    self.performance_integration = None
            
            self.logger.info("Core data components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize core components: {e}")
            raise
    
    async def get_market_data(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        data_type: str = "ohlcv"
    ) -> DataBridgeResult:
        """
        Get market data for a symbol with quality validation
        
        Args:
            symbol: Trading symbol
            start_time: Start time for data
            end_time: End time for data
            data_type: Type of data to retrieve
            
        Returns:
            DataBridgeResult with market data and quality metrics
        """
        start_time_ms = time.time()
        
        try:
            # Check cache first
            cache_key = f"{symbol}_{data_type}_{start_time}_{end_time}"
            if cache_key in self._data_cache:
                cached_data, cache_time = self._data_cache[cache_key]
                if datetime.now() - cache_time < timedelta(minutes=5):  # 5-minute cache
                    self._performance_stats['cached_requests'] += 1
                    processing_time = (time.time() - start_time_ms) * 1000
                    return DataBridgeResult(
                        symbol=symbol,
                        data_type=data_type,
                        data=cached_data,
                        quality_score=1.0,
                        timestamp=datetime.now(),
                        source='cached',
                        processing_time_ms=processing_time
                    )
            
            # Get data based on mode
            if self.config.data_mode == DataMode.PRODUCTION:
                data = await self._get_production_data(symbol, start_time, end_time, data_type)
                source = 'production'
            else:
                data = await self._get_backtesting_data(symbol, start_time, end_time, data_type)
                source = 'backtesting'
            
            # Calculate quality score
            quality_score = await self._calculate_data_quality(data, symbol, data_type)
            
            # Cache the result
            self._data_cache[cache_key] = (data, datetime.now())
            
            # Update performance stats
            self._update_performance_stats(source, time.time() - start_time_ms)
            
            processing_time = (time.time() - start_time_ms) * 1000
            
            return DataBridgeResult(
                symbol=symbol,
                data_type=data_type,
                data=data,
                quality_score=quality_score,
                timestamp=datetime.now(),
                source=source,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            self._performance_stats['errors'] += 1
            
            # Return fallback data if available
            fallback_data = await self._get_fallback_data(symbol, data_type)
            
            return DataBridgeResult(
                symbol=symbol,
                data_type=data_type,
                data=fallback_data,
                quality_score=0.0,
                timestamp=datetime.now(),
                source='fallback',
                processing_time_ms=(time.time() - start_time_ms) * 1000,
                error_message=str(e)
            )
    
    async def get_data_quality_report(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> DataQualityReport:
        """
        Get comprehensive data quality report for a symbol
        
        Args:
            symbol: Trading symbol
            start_time: Start time for analysis
            end_time: End time for analysis
            
        Returns:
            DataQualityReport with quality metrics and recommendations
        """
        try:
            if not self.config.enable_data_quality_monitoring:
                raise ValueError("Data quality monitoring is disabled")
            
            # Get market data for quality analysis
            data_result = await self.get_market_data(symbol, start_time, end_time)
            
            if isinstance(data_result.data, pd.DataFrame):
                # Calculate quality metrics
                completeness_score = self._calculate_completeness(data_result.data)
                accuracy_score = self._calculate_accuracy(data_result.data)
                consistency_score = self._calculate_consistency(data_result.data)
                timeliness_score = self._calculate_timeliness(data_result.data)
                
                # Calculate overall quality score
                overall_score = (completeness_score + accuracy_score + 
                               consistency_score + timeliness_score) / 4.0
                
                # Determine quality level
                if overall_score >= 0.9:
                    quality_level = DataQualityLevel.EXCELLENT
                elif overall_score >= 0.8:
                    quality_level = DataQualityLevel.GOOD
                elif overall_score >= 0.7:
                    quality_level = DataQualityLevel.FAIR
                elif overall_score >= 0.6:
                    quality_level = DataQualityLevel.POOR
                else:
                    quality_level = DataQualityLevel.CRITICAL
                
                # Generate issues and recommendations
                issues = self._identify_data_issues(data_result.data, overall_score)
                recommendations = self._generate_quality_recommendations(issues, overall_score)
                
                return DataQualityReport(
                    overall_quality_score=overall_score,
                    completeness_score=completeness_score,
                    accuracy_score=accuracy_score,
                    consistency_score=consistency_score,
                    timeliness_score=timeliness_score,
                    quality_level=quality_level,
                    issues=issues,
                    recommendations=recommendations
                )
            else:
                raise ValueError("Data is not in DataFrame format for quality analysis")
                
        except Exception as e:
            self.logger.error(f"Error generating data quality report for {symbol}: {e}")
            raise
    
    async def validate_data_consistency(
        self,
        symbol: str,
        production_data: pd.DataFrame,
        backtesting_data: pd.DataFrame
    ) -> DataConsistencyReport:
        """
        Validate consistency between production and backtesting data
        
        Args:
            symbol: Trading symbol
            production_data: Production market data
            backtesting_data: Backtesting market data
            
        Returns:
            DataConsistencyReport with consistency metrics
        """
        try:
            if not self.config.validate_data_consistency:
                raise ValueError("Data consistency validation is disabled")
            
            # Align data by timestamp
            aligned_data = self._align_data_by_timestamp(production_data, backtesting_data)
            
            if aligned_data is None:
                return DataConsistencyReport(
                    consistency_score=0.0,
                    production_data_points=len(production_data),
                    backtesting_data_points=len(backtesting_data),
                    missing_data_points=0,
                    inconsistent_data_points=0,
                    issues=["Data alignment failed"],
                    recommendations=["Check timestamp formats and data ranges"]
                )
            
            prod_aligned, backtest_aligned = aligned_data
            
            # Calculate consistency metrics
            total_points = len(prod_aligned)
            missing_points = total_points - len(backtest_aligned)
            
            # Compare data values
            if len(backtest_aligned) > 0:
                # Calculate price differences
                price_diff = np.abs(prod_aligned['close'] - backtest_aligned['close'])
                volume_diff = np.abs(prod_aligned['volume'] - backtest_aligned['volume'])
                
                # Count inconsistent points
                price_threshold = prod_aligned['close'].mean() * 0.001  # 0.1% threshold
                volume_threshold = prod_aligned['volume'].mean() * 0.01  # 1% threshold
                
                inconsistent_price = np.sum(price_diff > price_threshold)
                inconsistent_volume = np.sum(volume_diff > volume_threshold)
                inconsistent_points = max(inconsistent_price, inconsistent_volume)
                
                # Calculate consistency score
                consistency_score = 1.0 - (inconsistent_points / total_points)
            else:
                inconsistent_points = total_points
                consistency_score = 0.0
            
            # Generate issues and recommendations
            issues = []
            recommendations = []
            
            if missing_points > 0:
                issues.append(f"Missing {missing_points} data points in backtesting data")
                recommendations.append("Ensure complete data coverage in backtesting")
            
            if inconsistent_points > 0:
                issues.append(f"Inconsistent {inconsistent_points} data points")
                recommendations.append("Verify data source consistency")
            
            if consistency_score < 0.9:
                recommendations.append("Consider data reconciliation process")
            
            return DataConsistencyReport(
                consistency_score=consistency_score,
                production_data_points=len(production_data),
                backtesting_data_points=len(backtesting_data),
                missing_data_points=missing_points,
                inconsistent_data_points=inconsistent_points,
                issues=issues,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error validating data consistency for {symbol}: {e}")
            raise
    
    async def get_regime_data(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> DataBridgeResult:
        """
        Get regime detection data for a symbol
        
        Args:
            symbol: Trading symbol
            start_time: Start time for regime analysis
            end_time: End time for regime analysis
            
        Returns:
            DataBridgeResult with regime data
        """
        try:
            if not self.config.enable_regime_detection:
                raise ValueError("Regime detection is disabled")
            
            # Get market data for regime analysis
            market_data_result = await self.get_market_data(symbol, start_time, end_time)
            
            if isinstance(market_data_result.data, pd.DataFrame):
                # Calculate regime indicators
                regime_data = self._calculate_regime_indicators(market_data_result.data)
                
                return DataBridgeResult(
                    symbol=symbol,
                    data_type='regime_data',
                    data=regime_data,
                    quality_score=market_data_result.quality_score,
                    timestamp=datetime.now(),
                    source=market_data_result.source,
                    processing_time_ms=market_data_result.processing_time_ms
                )
            else:
                raise ValueError("Market data is not in DataFrame format for regime analysis")
                
        except Exception as e:
            self.logger.error(f"Error getting regime data for {symbol}: {e}")
            raise
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear data cache"""
        self._data_cache.clear()
        self.logger.info("Data cache cleared")
    
    async def _get_production_data(
        self,
        symbol: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        data_type: str
    ) -> pd.DataFrame:
        """Get data from production data manager"""
        try:
            # Use data manager to get production data
            data = await self.data_manager.get_market_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                data_type=data_type
            )
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting production data: {e}")
            raise
    
    async def _get_backtesting_data(
        self,
        symbol: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        data_type: str
    ) -> pd.DataFrame:
        """Get data optimized for backtesting"""
        try:
            # For backtesting, we might use cached or optimized data
            # This could be historical data stored locally
            data = await self.data_manager.get_historical_data(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                data_type=data_type
            )
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting backtesting data: {e}")
            raise
    
    async def _get_fallback_data(
        self,
        symbol: str,
        data_type: str
    ) -> pd.DataFrame:
        """Get fallback data when primary sources fail"""
        try:
            # Return empty DataFrame as fallback
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error getting fallback data: {e}")
            return pd.DataFrame()
    
    async def _calculate_data_quality(
        self,
        data: pd.DataFrame,
        symbol: str,
        data_type: str
    ) -> float:
        """Calculate data quality score"""
        try:
            if data.empty:
                return 0.0
            
            # Basic quality checks
            completeness = self._calculate_completeness(data)
            accuracy = self._calculate_accuracy(data)
            consistency = self._calculate_consistency(data)
            timeliness = self._calculate_timeliness(data)
            
            # Weighted average
            quality_score = (completeness * 0.3 + accuracy * 0.3 + 
                           consistency * 0.2 + timeliness * 0.2)
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Error calculating data quality: {e}")
            return 0.0
    
    def _calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness score"""
        try:
            if data.empty:
                return 0.0
            
            # Check for missing values
            total_cells = data.size
            missing_cells = data.isnull().sum().sum()
            completeness = 1.0 - (missing_cells / total_cells)
            
            return max(0.0, min(1.0, completeness))
            
        except Exception as e:
            self.logger.error(f"Error calculating completeness: {e}")
            return 0.0
    
    def _calculate_accuracy(self, data: pd.DataFrame) -> float:
        """Calculate data accuracy score"""
        try:
            if data.empty:
                return 0.0
            
            # Basic accuracy checks
            accuracy_score = 1.0
            
            # Check for negative prices
            if 'close' in data.columns:
                negative_prices = (data['close'] <= 0).sum()
                if negative_prices > 0:
                    accuracy_score -= 0.2
            
            # Check for extreme outliers
            if 'close' in data.columns:
                q99 = data['close'].quantile(0.99)
                q01 = data['close'].quantile(0.01)
                outliers = ((data['close'] > q99 * 2) | (data['close'] < q01 * 0.5)).sum()
                if outliers > 0:
                    accuracy_score -= 0.1
            
            return max(0.0, min(1.0, accuracy_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating accuracy: {e}")
            return 0.0
    
    def _calculate_consistency(self, data: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        try:
            if data.empty:
                return 0.0
            
            consistency_score = 1.0
            
            # Check for timestamp consistency
            if 'timestamp' in data.columns:
                timestamps = pd.to_datetime(data['timestamp'])
                time_diffs = timestamps.diff().dropna()
                
                if len(time_diffs) > 0:
                    # Check for irregular intervals
                    mean_interval = time_diffs.mean()
                    irregular_intervals = (time_diffs > mean_interval * 2).sum()
                    
                    if irregular_intervals > 0:
                        consistency_score -= 0.1
            
            return max(0.0, min(1.0, consistency_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating consistency: {e}")
            return 0.0
    
    def _calculate_timeliness(self, data: pd.DataFrame) -> float:
        """Calculate data timeliness score"""
        try:
            if data.empty:
                return 0.0
            
            timeliness_score = 1.0
            
            # Check for recent data
            if 'timestamp' in data.columns:
                timestamps = pd.to_datetime(data['timestamp'])
                latest_timestamp = timestamps.max()
                current_time = datetime.now()
                
                time_diff = (current_time - latest_timestamp).total_seconds()
                
                # Penalize old data
                if time_diff > 3600:  # 1 hour
                    timeliness_score -= 0.2
                elif time_diff > 300:  # 5 minutes
                    timeliness_score -= 0.1
            
            return max(0.0, min(1.0, timeliness_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating timeliness: {e}")
            return 0.0
    
    def _identify_data_issues(self, data: pd.DataFrame, quality_score: float) -> List[str]:
        """Identify data quality issues"""
        issues = []
        
        try:
            if data.empty:
                issues.append("Empty dataset")
                return issues
            
            # Check for missing values
            missing_counts = data.isnull().sum()
            for col, count in missing_counts.items():
                if count > 0:
                    issues.append(f"Missing {count} values in {col}")
            
            # Check for negative prices
            if 'close' in data.columns:
                negative_prices = (data['close'] <= 0).sum()
                if negative_prices > 0:
                    issues.append(f"Found {negative_prices} negative/zero prices")
            
            # Check for outliers
            if 'close' in data.columns:
                q99 = data['close'].quantile(0.99)
                q01 = data['close'].quantile(0.01)
                outliers = ((data['close'] > q99 * 2) | (data['close'] < q01 * 0.5)).sum()
                if outliers > 0:
                    issues.append(f"Found {outliers} extreme price outliers")
            
            # Check for timestamp issues
            if 'timestamp' in data.columns:
                timestamps = pd.to_datetime(data['timestamp'])
                time_diffs = timestamps.diff().dropna()
                
                if len(time_diffs) > 0:
                    mean_interval = time_diffs.mean()
                    irregular_intervals = (time_diffs > mean_interval * 2).sum()
                    
                    if irregular_intervals > 0:
                        issues.append(f"Found {irregular_intervals} irregular time intervals")
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Error identifying data issues: {e}")
            issues.append(f"Error in issue identification: {e}")
            return issues
    
    def _generate_quality_recommendations(
        self,
        issues: List[str],
        quality_score: float
    ) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        try:
            if quality_score < 0.8:
                recommendations.append("Consider data source validation")
            
            if any("missing" in issue.lower() for issue in issues):
                recommendations.append("Implement data gap filling strategies")
            
            if any("negative" in issue.lower() for issue in issues):
                recommendations.append("Review data source for price validation")
            
            if any("outlier" in issue.lower() for issue in issues):
                recommendations.append("Implement outlier detection and handling")
            
            if any("irregular" in issue.lower() for issue in issues):
                recommendations.append("Check data source for consistent intervals")
            
            if not recommendations:
                recommendations.append("Data quality is acceptable")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Error in recommendation generation"]
    
    def _align_data_by_timestamp(
        self,
        production_data: pd.DataFrame,
        backtesting_data: pd.DataFrame
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Align production and backtesting data by timestamp"""
        try:
            if production_data.empty or backtesting_data.empty:
                return None
            
            # Ensure timestamp columns exist
            if 'timestamp' not in production_data.columns or 'timestamp' not in backtesting_data.columns:
                return None
            
            # Convert timestamps
            prod_timestamps = pd.to_datetime(production_data['timestamp'])
            backtest_timestamps = pd.to_datetime(backtesting_data['timestamp'])
            
            # Find common timestamps using set intersection
            prod_timestamp_set = set(prod_timestamps)
            backtest_timestamp_set = set(backtest_timestamps)
            common_timestamps = prod_timestamp_set.intersection(backtest_timestamp_set)
            
            if len(common_timestamps) == 0:
                return None
            
            # Filter data to common timestamps
            prod_aligned = production_data[prod_timestamps.isin(common_timestamps)]
            backtest_aligned = backtesting_data[backtest_timestamps.isin(common_timestamps)]
            
            return prod_aligned, backtest_aligned
            
        except Exception as e:
            self.logger.error(f"Error aligning data by timestamp: {e}")
            return None
    
    def _calculate_regime_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate regime detection indicators"""
        try:
            if data.empty or 'close' not in data.columns:
                return {}
            
            # Calculate basic regime indicators
            returns = data['close'].pct_change().dropna()
            
            # Volatility regime
            volatility = returns.rolling(window=20).std()
            
            # Trend regime
            sma_20 = data['close'].rolling(window=20).mean()
            sma_50 = data['close'].rolling(window=50).mean()
            trend = (sma_20 > sma_50).astype(int)
            
            # Volume regime
            if 'volume' in data.columns:
                volume_sma = data['volume'].rolling(window=20).mean()
                volume_regime = (data['volume'] > volume_sma).astype(int)
            else:
                volume_regime = pd.Series([0] * len(data))
            
            return {
                'volatility': volatility.tolist(),
                'trend': trend.tolist(),
                'volume_regime': volume_regime.tolist(),
                'returns': returns.tolist()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating regime indicators: {e}")
            return {}
    
    def _update_performance_stats(self, source: str, processing_time: float):
        """Update performance statistics"""
        try:
            self._performance_stats['total_requests'] += 1
            self._performance_stats['total_data_points'] += 1
            
            if source == 'production':
                self._performance_stats['production_requests'] += 1
            elif source == 'backtesting':
                self._performance_stats['backtesting_requests'] += 1
            
            # Update average processing time
            total_requests = self._performance_stats['total_requests']
            current_avg = self._performance_stats['avg_processing_time']
            new_avg = ((current_avg * (total_requests - 1)) + processing_time) / total_requests
            self._performance_stats['avg_processing_time'] = new_avg
            
        except Exception as e:
            self.logger.error(f"Error updating performance stats: {e}")


def create_data_bridge(config: Optional[DataBridgeConfig] = None) -> DataBridge:
    """
    Factory function to create DataBridge instance
    
    Args:
        config: DataBridge configuration
        
    Returns:
        DataBridge instance
    """
    return DataBridge(config)


def get_data_for_backtesting(
    symbol: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    data_type: str = "ohlcv"
) -> pd.DataFrame:
    """
    Convenience function for backtesting data retrieval
    
    Args:
        symbol: Trading symbol
        start_time: Start time for data
        end_time: End time for data
        data_type: Type of data to retrieve
        
    Returns:
        Market data DataFrame optimized for backtesting
    """
    config = DataBridgeConfig(data_mode=DataMode.BACKTESTING)
    bridge = create_data_bridge(config)
    
    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # If we're already in an event loop, we can't use run_until_complete
        # Return empty DataFrame as fallback
        return pd.DataFrame()
    except RuntimeError:
        # No event loop running, we can create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                bridge.get_market_data(symbol, start_time, end_time, data_type)
            )
            return result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()
        finally:
            loop.close() 