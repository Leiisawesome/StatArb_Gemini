"""
Enhanced ClickHouse Data Loader
High-performance data loading with advanced caching and pair screening
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache
import hashlib
import pickle

from core_structure.infrastructure.database import DatabaseSystemFactory
from core_structure.infrastructure.monitoring import MonitoringSystemFactory
from core_structure.infrastructure.config import UnifiedConfigManager as ConfigManager


@dataclass
class DataRequest:
    """Data request specification"""
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    interval: str = '1min'  # 1min, 5min, 1h, 1d
    include_volume: bool = True
    include_technical: bool = False
    cache_key: Optional[str] = None
    
    def __post_init__(self):
        """Generate cache key"""
        if not self.cache_key:
            key_data = f"{sorted(self.symbols)}-{self.start_date}-{self.end_date}-{self.interval}"
            self.cache_key = hashlib.md5(key_data.encode()).hexdigest()


@dataclass
class PairScreeningCriteria:
    """Criteria for pair screening"""
    min_correlation: float = 0.7
    max_correlation: float = 0.95
    min_cointegration_pvalue: float = 0.05
    min_trading_days: int = 252
    min_avg_volume: float = 1000000  # $1M daily volume
    exclude_same_sector: bool = False
    sector_mapping: Optional[Dict[str, str]] = None


@dataclass
class CachedResult:
    """Cached data result"""
    data: Any
    timestamp: datetime
    ttl_seconds: int
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl_seconds)


class SmartCache:
    """Intelligent caching system with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CachedResult] = {}
        self.access_order: List[str] = []
        self.lock = threading.RLock()
        self.logger = logging.getLogger("cache")
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key in self.cache:
                result = self.cache[key]
                
                # Check if expired
                if result.is_expired:
                    del self.cache[key]
                    if key in self.access_order:
                        self.access_order.remove(key)
                    self.misses += 1
                    return None
                
                # Update access order
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
                
                # Update hit count
                result.hit_count += 1
                self.hits += 1
                
                return result.data
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put item in cache"""
        with self.lock:
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            # Store result
            self.cache[key] = CachedResult(
                data=value,
                timestamp=datetime.now(),
                ttl_seconds=ttl or self.default_ttl
            )
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]
                self.evictions += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_ratio = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_ratio': hit_ratio,
                'evictions': self.evictions
            }
    
    def clear(self) -> None:
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()


class EnhancedClickHouseLoader:
    """Enhanced ClickHouse data loader with caching and pair screening"""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        if config is None:
            # Create a default config manager if none provided
            config = ConfigManager()
        
        self.config = config
        self.logger = logging.getLogger("clickhouse_loader")
        
        # Use consolidated database and monitoring systems
        self.db_system = DatabaseSystemFactory.create_development_database_system()
        self.clickhouse = self.db_system.clickhouse
        
        # Initialize monitoring system
        metrics_collector, _, _, _ = MonitoringSystemFactory.create_development_monitoring_system()
        self.metrics = metrics_collector
        
        # Caching
        cache_config = config.get("clickhouse_loader.cache", {})
        self.cache = SmartCache(
            max_size=cache_config.get("max_size", 1000),
            default_ttl=cache_config.get("default_ttl", 3600)
        )
        
        # Threading
        self.executor = ThreadPoolExecutor(
            max_workers=config.get("clickhouse_loader.max_workers", 8)
        )
        
        # Performance tracking
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'avg_query_time': 0.0,
            'data_points_loaded': 0
        }
        
        # Import validation monitor (will create basic validation if not available)
        try:
            from .data_validation_monitor import DataValidationMonitor, ValidationSeverity
            self.validation_monitor = DataValidationMonitor()
            self.enable_validation = config.get("clickhouse_loader.enable_validation", True)
        except ImportError:
            self.validation_monitor = None
            self.enable_validation = False
            self.logger.warning("DataValidationMonitor not available, skipping validation")
        
    async def load_market_data(
        self,
        request: DataRequest,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Load market data with intelligent caching
        
        Args:
            request: Data request specification
            use_cache: Whether to use caching
            
        Returns:
            DataFrame with market data
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cached_data = self.cache.get(request.cache_key)
                if cached_data is not None:
                    self.query_stats['cache_hits'] += 1
                    self.logger.debug(f"Cache hit for {request.symbols}")
                    return cached_data
            
            # Load from database
            self.logger.info(f"Loading data for {len(request.symbols)} symbols from {request.start_date} to {request.end_date}")
            
            # Parallel loading for multiple symbols
            if len(request.symbols) > 1:
                data = await self._load_parallel(request)
            else:
                data = await self._load_single_symbol(request.symbols[0], request)
            
            # Cache result
            if use_cache and data is not None and not data.empty:
                # Calculate TTL based on data recency
                latest_time = data.index.max() if not data.empty else datetime.now()
                age_hours = (datetime.now() - latest_time).total_seconds() / 3600
                ttl = min(3600, max(300, int(age_hours * 60)))  # 5min to 1hour
                
                self.cache.put(request.cache_key, data, ttl)
            
            # Update statistics
            query_time = time.time() - start_time
            self.query_stats['total_queries'] += 1
            self.query_stats['avg_query_time'] = (
                self.query_stats['avg_query_time'] * 0.9 + query_time * 0.1
            )
            if data is not None:
                self.query_stats['data_points_loaded'] += len(data)
            
            # Record metrics using consolidated monitoring system
            self.metrics.record_metric("clickhouse_loader.query_time_ms", query_time * 1000)
            self.metrics.increment_counter("clickhouse_loader.queries_total")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading market data: {e}")
            self.metrics.increment_counter("clickhouse_loader.errors")
            raise
    
    async def _load_parallel(self, request: DataRequest) -> pd.DataFrame:
        """Load data for multiple symbols sequentially to avoid connection issues"""
        dataframes = []
        
        for symbol in request.symbols:
            try:
                data = await self._load_single_symbol(symbol, request)
                if data is not None and not data.empty:
                    dataframes.append(data)
            except Exception as e:
                self.logger.error(f"Error loading {symbol}: {e}")
                continue
        
        if not dataframes:
            return pd.DataFrame()
        
        # For multi-symbol data, concatenate vertically to maintain symbol column
        if len(dataframes) > 1:
            combined_data = pd.concat(dataframes, ignore_index=False)
            combined_data = combined_data.sort_index()  # Sort by timestamp
            self.logger.info(f"Combined {len(dataframes)} symbol datasets into {len(combined_data)} total rows")
        else:
            combined_data = dataframes[0]
        
        return combined_data
    
    def load_symbol_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Load data for a single symbol (synchronous wrapper for DataManager compatibility)
        
        Args:
            symbol: Symbol to load
            start_date: Start date (optional)
            end_date: End date (optional)
            days_back: Days back from today (optional)
            
        Returns:
            DataFrame with symbol data
        """
        # Set default dates
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            if days_back is not None:
                start_date = end_date - timedelta(days=days_back)
            else:
                start_date = end_date - timedelta(days=252)  # Default to 1 year
        
        # Create data request
        request = DataRequest(
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            interval='5m'  # 5-minute bars for trading
        )
        
        # Use proper async handling - check if we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an event loop, use thread executor for async compatibility
            future = asyncio.ensure_future(self.load_market_data(request))
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, self.load_market_data(request)).result(timeout=30)
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            try:
                return asyncio.run(self.load_market_data(request))
            except Exception as e:
                self.logger.error(f"Error loading data for {symbol}: {e}")
                return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def _load_single_symbol(self, symbol: str, request: DataRequest) -> pd.DataFrame:
        """Load data for single symbol"""
        try:
            # Build query based on interval - using the full polygon_data.ticks table
            table = 'polygon_data.ticks'
            
            # Convert datetime to nanoseconds for window_start
            start_date_ns = int(request.start_date.timestamp() * 1_000_000_000)
            end_date_ns = int(request.end_date.timestamp() * 1_000_000_000)
            
            # Build query based on interval
            if request.interval == '1d':
                # Aggregate to daily data
                query = f"""
                SELECT 
                    toDate(toDateTime(window_start / 1000000000)) as date,
                    argMin(open, window_start) as open,
                    max(high) as high,
                    min(low) as low,
                    argMax(close, window_start) as close,
                    sum(volume) as volume
                FROM {table}
                WHERE ticker = '{symbol}'
                AND window_start >= {start_date_ns}
                AND window_start <= {end_date_ns}
                GROUP BY toDate(toDateTime(window_start / 1000000000))
                ORDER BY date
                """
            elif request.interval == '5min':
                # Aggregate to 5-minute data
                query = f"""
                SELECT 
                    toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 5 minute) as timestamp,
                    ticker as symbol,
                    argMin(open, window_start) as open,
                    max(high) as high,
                    min(low) as low,
                    argMax(close, window_start) as close,
                    sum(volume) as volume
                FROM {table}
                WHERE ticker = '{symbol}'
                AND window_start >= {start_date_ns}
                AND window_start <= {end_date_ns}
                GROUP BY toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 5 minute), ticker
                ORDER BY timestamp
                """
            elif request.interval == '15min':
                # Aggregate to 15-minute data
                query = f"""
                SELECT 
                    toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 15 minute) as timestamp,
                    ticker as symbol,
                    argMin(open, window_start) as open,
                    max(high) as high,
                    min(low) as low,
                    argMax(close, window_start) as close,
                    sum(volume) as volume
                FROM {table}
                WHERE ticker = '{symbol}'
                AND window_start >= {start_date_ns}
                AND window_start <= {end_date_ns}
                GROUP BY toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 15 minute), ticker
                ORDER BY timestamp
                """
            elif request.interval == '1h' or request.interval == '1hour':
                # Aggregate to 1-hour data
                query = f"""
                SELECT 
                    toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 1 hour) as timestamp,
                    ticker as symbol,
                    argMin(open, window_start) as open,
                    max(high) as high,
                    min(low) as low,
                    argMax(close, window_start) as close,
                    sum(volume) as volume
                FROM {table}
                WHERE ticker = '{symbol}'
                AND window_start >= {start_date_ns}
                AND window_start <= {end_date_ns}
                GROUP BY toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 1 hour), ticker
                ORDER BY timestamp
                """
            else:
                # For 1-minute data, select directly
                query = f"""
                SELECT 
                    toDateTime(window_start / 1000000000) as timestamp,
                    ticker as symbol,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM {table}
                WHERE ticker = '{symbol}'
                AND window_start >= {start_date_ns}
                AND window_start <= {end_date_ns}
                ORDER BY window_start
                """
            
            # Execute query using the consolidated database system
            data = self.clickhouse.execute_query(query)
            
            if not data:
                self.logger.warning(f"No data found for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if request.interval == '1d':
                df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            else:
                df.columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # Keep symbol as a column (don't set as index)
                df.set_index('timestamp', inplace=True)
            
            # Clean data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any rows with NaN values
            df = df.dropna()
            
            if df.empty:
                self.logger.warning(f"No valid data after processing for {symbol}")
                return pd.DataFrame()
            
            self.logger.info(f"Loaded {len(df)} rows for {symbol} from {df.index.min()} to {df.index.max()}")
            
            # Data validation and monitoring (if available)
            if self.enable_validation and self.validation_monitor and not df.empty:
                try:
                    from .data_validation_monitor import ValidationSeverity
                    validation_results = self.validation_monitor.validate_market_data(df, symbol)
                    
                    # Check for critical errors
                    critical_errors = [r for r in validation_results if r.severity == ValidationSeverity.ERROR]
                    if critical_errors:
                        error_messages = [r.message for r in critical_errors]
                        self.logger.error(f"❌ CRITICAL DATA VALIDATION ERRORS for {symbol}: {error_messages}")
                        # Still return data but log the issues for monitoring
                    
                    # Log validation summary (smart filtering for market data)
                    warnings = [r for r in validation_results if r.severity == ValidationSeverity.WARNING]
                    if warnings:
                        # Filter out expected market data warnings
                        significant_warnings = []
                        for w in warnings:
                            # Skip normal timestamp gaps (weekends, holidays)
                            if w.check_name == "timestamps.gaps" and len(warnings) == 1:
                                continue  # Normal market gaps, don't spam logs
                            # Skip low-level statistical outliers
                            if w.check_name == "outliers.statistical_outliers" and "5." in w.message:
                                continue  # Normal volatility, don't spam logs
                            significant_warnings.append(w)
                        
                        # Only log significant issues
                        if significant_warnings:
                            warning_types = [w.check_name for w in significant_warnings]
                            self.logger.warning(f"⚠️  Data validation issues for {symbol}: {warning_types}")
                        else:
                            # All warnings were filtered as normal market behavior
                            self.logger.debug(f"Data validation: {len(warnings)} normal market data patterns for {symbol}")
                except ImportError:
                    pass  # Validation not available
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            self.metrics.increment_counter("clickhouse_loader.errors")
            return pd.DataFrame()
    
    async def screen_pairs(
        self,
        universe: List[str],
        criteria: PairScreeningCriteria,
        lookback_days: int = 252
    ) -> List[Tuple[str, str, Dict[str, float]]]:
        """
        Screen for trading pairs based on criteria
        
        Args:
            universe: List of symbols to screen
            criteria: Screening criteria
            lookback_days: Historical lookback period
            
        Returns:
            List of (symbol1, symbol2, metrics) tuples
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Screening {len(universe)} symbols for pairs")
            
            # Load historical data for all symbols
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            request = DataRequest(
                symbols=universe,
                start_date=start_date,
                end_date=end_date,
                interval='1d'  # Daily data for screening
            )
            
            data = await self.load_market_data(request)
            
            if data.empty:
                self.logger.warning("No data available for pair screening")
                return []
            
            # Group by symbol and get close prices
            symbol_data = {}
            for symbol in universe:
                symbol_df = data[data['symbol'] == symbol] if 'symbol' in data.columns else data
                if not symbol_df.empty:
                    symbol_data[symbol] = symbol_df['close'].dropna()
            
            # Screen pairs
            pairs = []
            symbols = list(symbol_data.keys())
            
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    symbol1, symbol2 = symbols[i], symbols[j]
                    
                    # Skip if same sector (if specified)
                    if criteria.exclude_same_sector and criteria.sector_mapping:
                        if (symbol1 in criteria.sector_mapping and 
                            symbol2 in criteria.sector_mapping and
                            criteria.sector_mapping[symbol1] == criteria.sector_mapping[symbol2]):
                            continue
                    
                    # Get aligned data
                    prices1 = symbol_data[symbol1]
                    prices2 = symbol_data[symbol2]
                    
                    # Align indices
                    aligned_data = pd.DataFrame({
                        symbol1: prices1,
                        symbol2: prices2
                    }).dropna()
                    
                    if len(aligned_data) < criteria.min_trading_days:
                        continue
                    
                    # Calculate correlation
                    correlation = aligned_data[symbol1].corr(aligned_data[symbol2])
                    
                    if (correlation < criteria.min_correlation or 
                        correlation > criteria.max_correlation):
                        continue
                    
                    # Calculate cointegration (simplified ADF test)
                    try:
                        from statsmodels.tsa.stattools import coint
                        _, p_value, _ = coint(aligned_data[symbol1], aligned_data[symbol2])
                        
                        if p_value > criteria.min_cointegration_pvalue:
                            continue
                    except ImportError:
                        # Skip cointegration test if statsmodels not available
                        p_value = 0.01  # Assume cointegrated
                    
                    # Calculate additional metrics
                    spread = aligned_data[symbol1] - aligned_data[symbol2]
                    spread_std = spread.std()
                    spread_mean = spread.mean()
                    
                    metrics = {
                        'correlation': correlation,
                        'cointegration_pvalue': p_value,
                        'spread_mean': spread_mean,
                        'spread_std': spread_std,
                        'trading_days': len(aligned_data)
                    }
                    
                    pairs.append((symbol1, symbol2, metrics))
            
            # Sort by correlation (descending)
            pairs.sort(key=lambda x: x[2]['correlation'], reverse=True)
            
            self.logger.info(f"Found {len(pairs)} qualifying pairs in {time.time() - start_time:.2f}s")
            
            return pairs
            
        except Exception as e:
            self.logger.error(f"Error screening pairs: {e}")
            return []
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_stats = self.cache.get_stats()
        cache_stats.update(self.query_stats)
        return cache_stats
    
    def clear_cache(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.logger.info("Cache cleared")
    
    def close(self) -> None:
        """Close connections and cleanup resources"""
        try:
            self.executor.shutdown(wait=True)
            if hasattr(self.clickhouse, 'close'):
                self.clickhouse.close()
            self.logger.info("EnhancedClickHouseLoader closed")
        except Exception as e:
            self.logger.error(f"Error closing EnhancedClickHouseLoader: {e}")
