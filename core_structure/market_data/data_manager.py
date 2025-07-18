"""
Core Market Data Manager
Orchestrates all market data operations with enhanced ClickHouse integration
"""
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass

from ..infrastructure import (
    ClickHouseClient,
    MetricsCollector,
    MessageBus,
    ConfigManager
)

logger = logging.getLogger(__name__)

@dataclass
class MarketDataConfig:
    """Configuration for market data operations"""
    cache_ttl_seconds: int = 300
    real_time_enabled: bool = True
    max_symbols_per_query: int = 50
    default_lookback_days: int = 252
    enable_regime_detection: bool = True
    enable_liquidity_analysis: bool = True


class DataCache:
    """
    Enhanced caching system for market data with TTL and intelligent eviction
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache
        
        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of items in cache
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, datetime] = {}
        self.logger = logging.getLogger(f"{__name__}.DataCache")
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        cache_entry = self.cache[key]
        
        # Check if expired
        if self._is_expired(cache_entry):
            self._remove(key)
            self.misses += 1
            return None
        
        # Update access time
        self.access_times[key] = datetime.now()
        self.hits += 1
        
        return cache_entry['data']
    
    def put(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Put item in cache
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time-to-live in seconds (optional)
        """
        # Evict if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        # Create cache entry
        cache_entry = {
            'data': data,
            'created_at': datetime.now(),
            'ttl': ttl or self.default_ttl
        }
        
        self.cache[key] = cache_entry
        self.access_times[key] = datetime.now()
    
    def remove(self, key: str) -> bool:
        """
        Remove item from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if item was removed, False if not found
        """
        return self._remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.access_times.clear()
        self.logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache performance metrics
        """
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
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired"""
        created_at = cache_entry['created_at']
        ttl = cache_entry['ttl']
        
        return datetime.now() > created_at + timedelta(seconds=ttl)
    
    def _remove(self, key: str) -> bool:
        """Remove item from cache and access times"""
        removed = False
        
        if key in self.cache:
            del self.cache[key]
            removed = True
        
        if key in self.access_times:
            del self.access_times[key]
        
        return removed
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        # Find LRU item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Remove it
        self._remove(lru_key)
        self.evictions += 1
        
        self.logger.debug(f"Evicted LRU item: {lru_key}")
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired entries
        
        Returns:
            Number of entries cleaned up
        """
        expired_keys = []
        
        for key, cache_entry in self.cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove(key)
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)

class DataManager:
    """
    Core market data manager that orchestrates all data operations
    
    Features:
    - Unified interface for historical and real-time data
    - Enhanced ClickHouse integration with caching
    - Real-time market feeds with failover
    - AI-ready data streams and features
    - Performance monitoring and optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the data manager
        
        Args:
            config: Optional configuration dictionary
        """
        self.config_manager = ConfigManager()
        self.db_client = ClickHouseClient()
        self.metrics = MetricsCollector()
        self.message_bus = MessageBus()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Market data specific configuration
        market_config = self.config_manager.get('market_data', {})
        self.data_config = MarketDataConfig(**market_config)
        
        # Component initialization
        cache_size = market_config.get('cache_max_size', 1000)
        self.cache = DataCache(
            default_ttl=self.data_config.cache_ttl_seconds,
            max_size=cache_size
        )
        self._real_time_feeds = {}
        self._subscriptions = {}
        
        # Initialize enhanced loader
        try:
            from .enhanced_clickhouse_loader import EnhancedClickHouseLoader
            self.enhanced_loader = EnhancedClickHouseLoader()
        except ImportError:
            self.enhanced_loader = None
            self.logger.warning("Enhanced ClickHouse loader not available")
        
        # Performance monitoring
        self.metrics.set_alert_threshold(
            'market_data_latency',
            warning_threshold=100,
            critical_threshold=500
        )
        
        self.logger.info("DataManager initialized successfully")
    
    def load_pair_data(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load historical data for multiple symbols
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data (optional)
            end_date: End date for data (optional)
            days_back: Number of days back from today (optional)
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        try:
            # Generate cache key
            cache_key = f"pair_data_{'-'.join(sorted(symbols))}_{start_date}_{end_date}_{days_back}"
            
            # Check cache first
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                self.logger.debug(f"Cache hit for pair data: {symbols}")
                return cached_data
            
            # Load from enhanced loader
            if hasattr(self, 'enhanced_loader') and self.enhanced_loader:
                self.logger.info(f"Loading pair data for {len(symbols)} symbols using enhanced loader")
                
                # Use parallel loading for multiple symbols
                if len(symbols) > 1:
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    
                    with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as executor:
                        # Submit parallel load tasks
                        future_to_symbol = {
                            executor.submit(
                                self.enhanced_loader.load_symbol_data, 
                                symbol, 
                                start_date, 
                                end_date, 
                                days_back
                            ): symbol
                            for symbol in symbols
                        }
                        
                        result_data = {}
                        for future in as_completed(future_to_symbol):
                            symbol = future_to_symbol[future]
                            try:
                                result_data[symbol] = future.result()
                            except Exception as e:
                                self.logger.error(f"Failed to load data for {symbol}: {str(e)}")
                                result_data[symbol] = pd.DataFrame()
                else:
                    # Single symbol - direct load
                    result_data = {
                        symbols[0]: self.enhanced_loader.load_symbol_data(
                            symbols[0], start_date, end_date, days_back
                        )
                    }
            else:
                self.logger.warning("Enhanced loader not available, using basic implementation")
                result_data = {}
                for symbol in symbols:
                    # Basic fallback implementation
                    result_data[symbol] = pd.DataFrame()
            
            # Process the raw data
            processed_data = self._process_raw_data(result_data)
            
            # Cache the result
            self._add_to_cache(cache_key, processed_data)
            
            self.logger.info(f"Successfully loaded data for {len(symbols)} symbols")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error loading pair data: {str(e)}")
            # Return empty DataFrames for all symbols on error
            return {symbol: pd.DataFrame() for symbol in symbols}
    
    def load_historical_data(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Alias for load_pair_data to maintain compatibility with validation scripts
        
        Args:
            symbols: List of symbols to load
            start_date: Start date for data (optional)
            end_date: End date for data (optional)
            days_back: Number of days back from today (optional)
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        return self.load_pair_data(symbols, start_date, end_date, days_back)
    
    def start_real_time_feeds(self, symbols: List[str]) -> bool:
        """
        Start real-time data feeds for specified symbols
        
        Args:
            symbols: List of symbols to start feeds for
            
        Returns:
            True if feeds started successfully, False otherwise
        """
        if not self.data_config.real_time_enabled:
            self.logger.warning("Real-time feeds are disabled in configuration")
            return False
        
        try:
            self.logger.info(f"Starting real-time feeds for {len(symbols)} symbols: {symbols}")
            
            # Initialize feeds if not already done
            if not hasattr(self, '_feeds_manager'):
                try:
                    from .feeds import FeedManager
                    self._feeds_manager = FeedManager()
                except ImportError:
                    self.logger.warning("FeedManager not available, using mock feeds")
                    self._feeds_manager = None
            
            # Start feeds for each symbol
            successfully_started = []
            for symbol in symbols:
                try:
                    if self._feeds_manager:
                        # Use real feed manager
                        feed_started = self._feeds_manager.start_feed(symbol)
                        if feed_started:
                            successfully_started.append(symbol)
                            self._subscriptions[symbol] = datetime.now()
                    else:
                        # Mock implementation for testing
                        self._subscriptions[symbol] = datetime.now()
                        successfully_started.append(symbol)
                        
                except Exception as e:
                    self.logger.error(f"Failed to start feed for {symbol}: {str(e)}")
            
            success_rate = len(successfully_started) / len(symbols) if symbols else 0
            self.logger.info(f"Started feeds for {len(successfully_started)}/{len(symbols)} symbols (success rate: {success_rate:.1%})")
            
            # Publish feed start event
            if hasattr(self, 'message_bus'):
                self.message_bus.publish(
                    'real_time_feeds_started',
                    {
                        'symbols': successfully_started,
                        'timestamp': datetime.now().isoformat(),
                        'success_rate': success_rate
                    },
                    source='data_manager'
                )
            
            return success_rate > 0.5  # Consider successful if >50% of feeds started
            
        except Exception as e:
            self.logger.error(f"Error starting real-time feeds: {str(e)}")
            return False
    
    def get_real_time_data(
        self,
        symbols: List[str],
        include_depth: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time market data for symbols
        
        Args:
            symbols: List of symbol identifiers
            include_depth: Whether to include order book depth
            
        Returns:
            Dict mapping symbols to their real-time data
        """
        if not self.data_config.real_time_enabled:
            self.logger.warning("Real-time data is disabled")
            return {}
        
        start_time = datetime.now()
        real_time_data = {}
        
        try:
            # Implementation would use real-time feeds here
            # For now, return mock real-time data structure
            for symbol in symbols:
                real_time_data[symbol] = {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'bid_price': 100.0,  # Mock data
                    'ask_price': 100.05,
                    'last_price': 100.02,
                    'volume': 1000,
                    'spread_bps': 5.0
                }
                
                if include_depth:
                    real_time_data[symbol]['depth'] = {
                        'bid_depth': 50000,
                        'ask_depth': 52000
                    }
            
            # Record metrics
            latency = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics.record_latency('real_time_data_fetch', latency)
            
            return real_time_data
            
        except Exception as e:
            self.metrics.increment_counter('real_time_errors')
            self.logger.error(f"Error fetching real-time data: {str(e)}")
            raise
    
    def get_aligned_pair_data(
        self,
        symbol1: str,
        symbol2: str,
        days_back: int = 252
    ) -> pd.DataFrame:
        """
        Get aligned data for a specific pair
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol  
            days_back: Number of days to look back
            
        Returns:
            DataFrame with aligned pair data
        """
        # Load individual symbol data
        data = self.load_pair_data([symbol1, symbol2], days_back=days_back)
        
        if symbol1 not in data or symbol2 not in data:
            raise ValueError(f"Missing data for symbols: {symbol1}, {symbol2}")
        
        # Align by timestamp
        df1 = data[symbol1]
        df2 = data[symbol2]
        
        # Find common timestamps
        common_index = df1.index.intersection(df2.index)
        
        if len(common_index) < 50:
            raise ValueError(f"Insufficient overlapping data: {len(common_index)} points")
        
        # Create aligned DataFrame
        aligned = pd.DataFrame(index=common_index)
        
        # Add price data
        aligned[f'{symbol1}_close'] = df1.loc[common_index, 'close']
        aligned[f'{symbol2}_close'] = df2.loc[common_index, 'close']
        aligned[f'{symbol1}_volume'] = df1.loc[common_index, 'volume']
        aligned[f'{symbol2}_volume'] = df2.loc[common_index, 'volume']
        
        # Add returns
        aligned[f'{symbol1}_returns'] = df1.loc[common_index, 'close'].pct_change()
        aligned[f'{symbol2}_returns'] = df2.loc[common_index, 'close'].pct_change()
        
        # Calculate spread and ratio
        aligned['spread'] = aligned[f'{symbol1}_close'] - aligned[f'{symbol2}_close']
        aligned['ratio'] = aligned[f'{symbol1}_close'] / aligned[f'{symbol2}_close']
        aligned['log_ratio'] = np.log(aligned['ratio'])
        
        # Calculate z-score
        aligned['z_score'] = (aligned['spread'] - aligned['spread'].rolling(60).mean()) / aligned['spread'].rolling(60).std()
        
        # Remove NaN values
        aligned = aligned.dropna()
        
        self.logger.info(f"Aligned pair data: {len(aligned)} observations for {symbol1}/{symbol2}")
        return aligned
    
    def analyze_liquidity(
        self,
        symbols: List[str],
        window_minutes: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Analyze liquidity metrics for symbols
        
        Args:
            symbols: List of symbols to analyze
            window_minutes: Time window for analysis
            
        Returns:
            Dict mapping symbols to liquidity metrics
        """
        if not self.data_config.enable_liquidity_analysis:
            return {}
        
        liquidity_metrics = {}
        
        for symbol in symbols:
            # Get recent data for liquidity analysis
            real_time_data = self.get_real_time_data([symbol], include_depth=True)
            
            if symbol in real_time_data:
                data = real_time_data[symbol]
                
                # Calculate basic liquidity metrics
                spread_bps = ((data['ask_price'] - data['bid_price']) / 
                             ((data['ask_price'] + data['bid_price']) / 2)) * 10000
                
                liquidity_metrics[symbol] = {
                    'spread_bps': spread_bps,
                    'bid_depth': data.get('depth', {}).get('bid_depth', 0),
                    'ask_depth': data.get('depth', {}).get('ask_depth', 0),
                    'volume': data['volume'],
                    'liquidity_score': max(0, 1.0 - (spread_bps / 100))  # Simple score
                }
        
        return liquidity_metrics
    
    def detect_market_regimes(
        self,
        symbols: List[str],
        window_days: int = 60
    ) -> Dict[str, Dict[str, Any]]:
        """
        Detect market regimes for symbols
        
        Args:
            symbols: List of symbols to analyze
            window_days: Window for regime detection
            
        Returns:
            Dict mapping symbols to regime information
        """
        if not self.data_config.enable_regime_detection:
            return {}
        
        regime_data = {}
        
        # Load recent data
        data = self.load_pair_data(symbols, days_back=window_days * 2)
        
        for symbol in symbols:
            if symbol not in data:
                continue
            
            df = data[symbol]
            returns = df['close'].pct_change().dropna()
            
            # Simple volatility regime detection
            volatility = returns.rolling(window=20).std()
            vol_quantiles = volatility.quantile([0.33, 0.67])
            
            current_vol = volatility.iloc[-1] if len(volatility) > 0 else 0
            
            if current_vol <= vol_quantiles.iloc[0]:
                regime = 'low_volatility'
            elif current_vol <= vol_quantiles.iloc[1]:
                regime = 'medium_volatility'  
            else:
                regime = 'high_volatility'
            
            regime_data[symbol] = {
                'current_regime': regime,
                'current_volatility': current_vol,
                'regime_score': min(current_vol * 100, 100),  # Normalize to 0-100
                'stability': 0.8  # Mock stability score
            }
        
        return regime_data
    
    def create_ai_data_stream(
        self,
        symbols: List[str],
        include_features: bool = True
    ) -> Dict[str, Any]:
        """
        Create AI-ready data stream for symbols
        
        Args:
            symbols: List of symbols for the stream
            include_features: Whether to include engineered features
            
        Returns:
            AI-ready data stream configuration
        """
        stream_config = {
            'stream_id': f"ai_stream_{'-'.join(symbols)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'symbols': symbols,
            'created_at': datetime.now().isoformat(),
            'features_enabled': include_features,
            'data_sources': ['historical', 'real_time'] if self.data_config.real_time_enabled else ['historical']
        }
        
        # Publish AI stream creation event
        self.message_bus.publish_ai_message(
            {
                'action': 'stream_created',
                'stream_config': stream_config,
                'symbols': symbols
            },
            source='data_manager'
        )
        
        self.logger.info(f"Created AI data stream for {len(symbols)} symbols")
        return stream_config
    
    def _process_raw_data(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Process and validate raw market data"""
        processed_data = {}
        
        for symbol, df in raw_data.items():
            if df.empty:
                self.logger.warning(f"Empty data for symbol: {symbol}")
                continue
            
            # Ensure required columns exist
            required_columns = ['close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.logger.warning(f"Missing columns for {symbol}: {missing_columns}")
                continue
            
            # Calculate returns if not present
            if 'returns' not in df.columns:
                df = df.copy()
                df['returns'] = df['close'].pct_change()
            
            # Remove outliers (simple method)
            returns = df['returns'].dropna()
            if len(returns) > 0:
                q99 = returns.quantile(0.99)
                q01 = returns.quantile(0.01)
                df.loc[df['returns'] > q99, 'returns'] = q99
                df.loc[df['returns'] < q01, 'returns'] = q01
            
            # Sort by timestamp
            df = df.sort_index()
            
            processed_data[symbol] = df
        
        return processed_data
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired"""
        return self.cache.get(key)
    
    def _add_to_cache(self, key: str, data: Any) -> None:
        """Add data to cache"""
        self.cache.put(key, data)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of data manager"""
        cache_stats = self.cache.get_stats()
        return {
            'database_connected': self.db_client is not None,
            'real_time_enabled': self.data_config.real_time_enabled,
            'cache_entries': cache_stats['size'],
            'cache_hit_ratio': cache_stats['hit_ratio'],
            'active_subscriptions': len(self._subscriptions),
            'last_update': datetime.now().isoformat()
        } 