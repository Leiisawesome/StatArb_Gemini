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

from ..infrastructure.database.clickhouse_client import ClickHouseClient
from ..infrastructure.monitoring.metrics_collector import MetricsCollector
from ..infrastructure.config import UnifiedConfigManager as ConfigManager


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
        # Pass the database config dict to ClickHouseClient
        self.clickhouse = ClickHouseClient(config.get_database_config())
        self.metrics = MetricsCollector()
        
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
            
            # Record metrics
            self.metrics.record_latency("clickhouse_loader.query_time_ms", query_time * 1000)
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
        
        # Merge on timestamp
        combined_data = dataframes[0]
        for df in dataframes[1:]:
            combined_data = pd.merge(
                combined_data, df,
                left_index=True, right_index=True,
                how='outer',
                suffixes=('', f'_{df.columns[0].split("_")[0]}')
            )
        
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
            interval='1d'  # Default to daily data
        )
        
        # Use synchronous execution
        try:
            return asyncio.run(self.load_market_data(request))
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _load_symbol_sync(self, symbol: str, request: DataRequest) -> pd.DataFrame:
        """Synchronous symbol loading for executor"""
        return asyncio.run(self._load_single_symbol(symbol, request))
    
    async def _load_single_symbol(self, symbol: str, request: DataRequest) -> pd.DataFrame:
        """Load data for single symbol"""
        try:
            # Build query based on interval - using the actual table name 'ticks'
            table = 'ticks'
            
            # Convert datetime to nanoseconds for window_start
            start_date_ns = int(request.start_date.timestamp() * 1_000_000_000)
            end_date_ns = int(request.end_date.timestamp() * 1_000_000_000)
            
            # Query to aggregate minute data to daily data
            if request.interval == '1d':
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
            else:
                # For minute data, just select directly
                query = f"""
                SELECT 
                    toDateTime(window_start / 1000000000) as timestamp,
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
            
            # Execute query using synchronous method to avoid connection issues
            data = self.clickhouse._execute_query(query)
            
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
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
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
            self.logger.info(f"Screening {len(universe)} symbols for pairs...")
            
            # Load historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 50)  # Extra buffer
            
            request = DataRequest(
                symbols=universe,
                start_date=start_date,
                end_date=end_date,
                interval='1d'
            )
            
            data = await self.load_market_data(request)
            
            if data.empty:
                self.logger.warning("No data available for pair screening")
                return []
            
            # Screen pairs in parallel
            pairs_to_screen = [
                (universe[i], universe[j])
                for i in range(len(universe))
                for j in range(i + 1, len(universe))
            ]
            
            self.logger.info(f"Screening {len(pairs_to_screen)} potential pairs...")
            
            # Parallel screening
            loop = asyncio.get_event_loop()
            tasks = []
            
            for symbol1, symbol2 in pairs_to_screen:
                task = loop.run_in_executor(
                    self.executor,
                    self._screen_single_pair,
                    symbol1,
                    symbol2,
                    data,
                    criteria
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid pairs
            valid_pairs = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    continue
                
                if result is not None:
                    symbol1, symbol2 = pairs_to_screen[i]
                    valid_pairs.append((symbol1, symbol2, result))
            
            # Sort by quality score
            valid_pairs.sort(key=lambda x: x[2].get('quality_score', 0), reverse=True)
            
            screening_time = time.time() - start_time
            self.logger.info(f"Screened {len(pairs_to_screen)} pairs in {screening_time:.2f}s, found {len(valid_pairs)} valid pairs")
            
            # Record metrics
            self.metrics.record_latency("clickhouse_loader.pair_screening_time_ms", screening_time * 1000)
            self.metrics.set_gauge("clickhouse_loader.valid_pairs_found", len(valid_pairs))
            
            return valid_pairs
            
        except Exception as e:
            self.logger.error(f"Error in pair screening: {e}")
            return []
    
    def _screen_single_pair(
        self,
        symbol1: str,
        symbol2: str,
        data: pd.DataFrame,
        criteria: PairScreeningCriteria
    ) -> Optional[Dict[str, float]]:
        """Screen a single pair"""
        try:
            # Extract price series
            price1_col = f"{symbol1}_close"
            price2_col = f"{symbol2}_close"
            
            if price1_col not in data.columns or price2_col not in data.columns:
                return None
            
            prices1 = data[price1_col].dropna()
            prices2 = data[price2_col].dropna()
            
            # Align data
            aligned_data = pd.DataFrame({
                'price1': prices1,
                'price2': prices2
            }).dropna()
            
            if len(aligned_data) < criteria.min_trading_days:
                return None
            
            # Calculate correlation
            correlation = aligned_data['price1'].corr(aligned_data['price2'])
            
            if correlation < criteria.min_correlation or correlation > criteria.max_correlation:
                return None
            
            # Check volume criteria if available
            volume1_col = f"{symbol1}_volume"
            volume2_col = f"{symbol2}_volume"
            
            if volume1_col in data.columns and volume2_col in data.columns:
                avg_volume1 = data[volume1_col].mean()
                avg_volume2 = data[volume2_col].mean()
                
                if avg_volume1 < criteria.min_avg_volume or avg_volume2 < criteria.min_avg_volume:
                    return None
            
            # Cointegration test (simplified)
            log_prices1 = np.log(aligned_data['price1'])
            log_prices2 = np.log(aligned_data['price2'])
            
            # Simple cointegration test using residuals
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_prices1, log_prices2)
            residuals = log_prices2 - (slope * log_prices1 + intercept)
            
            # ADF test approximation using standard deviation
            residual_std = residuals.std()
            half_life = self._calculate_half_life(residuals)
            
            # Quality score
            quality_score = (
                correlation * 0.3 +
                (1 - abs(correlation - 0.85) / 0.15) * 0.3 +  # Prefer correlation around 0.85
                min(1.0, 50 / half_life) * 0.2 +  # Prefer faster mean reversion
                (1 - residual_std) * 0.2
            )
            
            return {
                'correlation': correlation,
                'cointegration_pvalue': p_value,
                'half_life': half_life,
                'residual_std': residual_std,
                'quality_score': quality_score,
                'data_points': len(aligned_data)
            }
            
        except Exception as e:
            self.logger.debug(f"Error screening pair {symbol1}-{symbol2}: {e}")
            return None
    
    def _calculate_half_life(self, residuals: pd.Series) -> float:
        """Calculate mean reversion half-life"""
        try:
            # AR(1) model: residuals[t] = alpha + beta * residuals[t-1] + error
            y = residuals[1:].values
            x = residuals[:-1].values
            
            # Linear regression
            from scipy import stats
            slope, intercept, _, _, _ = stats.linregress(x, y)
            
            # Half-life calculation
            if slope >= 1:
                return float('inf')
            
            half_life = -np.log(2) / np.log(abs(slope))
            return max(1, min(252, half_life))  # Clamp between 1 and 252 days
            
        except Exception:
            return 252  # Default to 1 year
    
    async def load_pair_data(
        self,
        symbol1: str,
        symbol2: str,
        lookback_days: int = 252,
        interval: str = '1h'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load aligned data for a pair"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)
            
            request = DataRequest(
                symbols=[symbol1, symbol2],
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )
            
            data = await self.load_market_data(request)
            
            if data.empty:
                return pd.DataFrame(), pd.DataFrame()
            
            # Extract individual series
            price1_col = f"{symbol1}_close"
            price2_col = f"{symbol2}_close"
            
            if price1_col not in data.columns or price2_col not in data.columns:
                return pd.DataFrame(), pd.DataFrame()
            
            # Create aligned dataframes
            df1 = data[[col for col in data.columns if col.startswith(f"{symbol1}_")]].copy()
            df2 = data[[col for col in data.columns if col.startswith(f"{symbol2}_")]].copy()
            
            # Remove symbol prefix from column names
            df1.columns = [col.replace(f"{symbol1}_", "") for col in df1.columns]
            df2.columns = [col.replace(f"{symbol2}_", "") for col in df2.columns]
            
            return df1, df2
            
        except Exception as e:
            self.logger.error(f"Error loading pair data for {symbol1}-{symbol2}: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get loader performance statistics"""
        cache_stats = self.cache.get_stats()
        
        return {
            **self.query_stats,
            'cache_hit_ratio': cache_stats['hit_ratio'],
            'cache_size': cache_stats['size'],
            'cache_evictions': cache_stats['evictions']
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        self.logger.info("Cache cleared")
    
    async def close(self) -> None:
        """Close the loader and cleanup resources"""
        try:
            await self.clickhouse.close()
            self.executor.shutdown(wait=True)
            self.logger.info("ClickHouse loader closed")
            
        except Exception as e:
            self.logger.error(f"Error closing loader: {e}") 