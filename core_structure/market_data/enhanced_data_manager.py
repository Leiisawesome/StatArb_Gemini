"""
Enhanced Unified Data Management System
======================================

Professional data management system consolidating all data functionality.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass
import warnings

from ..infrastructure import (
    ClickHouseClient,
    MetricsCollector,
    MessageBus,
    ConfigManager
)

logger = logging.getLogger(__name__)

@dataclass
class DataQualityThresholds:
    """Data quality monitoring thresholds"""
    max_price_change: float = 0.1  # 10% max price change
    max_volume: int = 1000000      # 1M max volume
    max_staleness: int = 300       # 5 minutes max staleness
    min_data_points: int = 10      # Minimum data points required

@dataclass
class DataStreamConfig:
    """Real-time data streaming configuration"""
    symbols: List[str]
    interval: str = "1m"
    include_depth: bool = False
    include_volume: bool = True
    buffer_size: int = 1000
    reconnect_attempts: int = 3

@dataclass
class MarketDataConfig:
    """Configuration for market data operations"""
    cache_ttl_seconds: int = 300
    real_time_enabled: bool = True
    max_symbols_per_query: int = 50
    default_lookback_days: int = 252
    enable_regime_detection: bool = True
    enable_liquidity_analysis: bool = True
    quality_monitoring: bool = True
    data_streaming: bool = True

class BasicDataQualityMonitor:
    """Basic data quality monitoring system for enhanced data manager
    
    Note: For comprehensive data quality monitoring with alerts and history,
    see data_quality_monitor.py (DataQualityMonitor)
    """
    
    def __init__(self, thresholds: Optional[DataQualityThresholds] = None):
        self.thresholds = thresholds or DataQualityThresholds()
        self.alert_callbacks: List[Callable] = []
        self.quality_metrics: Dict[str, Any] = {}
        
        logger.info("DataQualityMonitor initialized")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback for data quality issues"""
        self.alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def check_data_quality(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Check data quality for all symbols"""
        quality_report = {}
        
        for symbol, df in data.items():
            if df.empty:
                quality_report[symbol] = {
                    'status': 'ERROR',
                    'issues': ['Empty data'],
                    'severity': 'HIGH'
                }
                continue
            
            issues = []
            severity = 'LOW'
            
            # Check for missing values
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                issues.append(f"Missing values: {missing_values}")
                severity = 'MEDIUM'
            
            # Check for price anomalies
            if 'close' in df.columns:
                price_changes = df['close'].pct_change().abs()
                max_change = price_changes.max()
                if max_change > self.thresholds.max_price_change:
                    issues.append(f"Large price change detected: {max_change:.2%}")
                    severity = 'HIGH'
            
            # Check for volume anomalies
            if 'volume' in df.columns:
                max_volume = df['volume'].max()
                if max_volume > self.thresholds.max_volume:
                    issues.append(f"Unusual volume detected: {max_volume:,}")
                    severity = 'MEDIUM'
            
            # Check data freshness
            if 'timestamp' in df.index:
                latest_time = df.index.max()
                if isinstance(latest_time, datetime):
                    time_diff = datetime.now() - latest_time
                    if time_diff.total_seconds() > self.thresholds.max_staleness:
                        issues.append(f"Data may be stale: {time_diff.total_seconds():.0f}s old")
                        severity = 'HIGH'
            
            # Check data sufficiency
            if len(df) < self.thresholds.min_data_points:
                issues.append(f"Insufficient data points: {len(df)}")
                severity = 'MEDIUM'
            
            quality_report[symbol] = {
                'status': 'OK' if not issues else 'WARNING',
                'issues': issues,
                'severity': severity,
                'data_points': len(df),
                'last_update': df.index.max() if not df.empty else None
            }
        
        return quality_report
    
    async def notify_alerts(self, quality_report: Dict[str, Any]):
        """Notify alert callbacks of quality issues"""
        for symbol, report in quality_report.items():
            if report['status'] != 'OK':
                for callback in self.alert_callbacks:
                    try:
                        await callback(symbol, report)
                    except Exception as e:
                        logger.error(f"Alert callback failed: {e}")
    
    def get_quality_summary(self, quality_report: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of data quality"""
        total_symbols = len(quality_report)
        ok_count = sum(1 for report in quality_report.values() if report['status'] == 'OK')
        warning_count = sum(1 for report in quality_report.values() if report['status'] == 'WARNING')
        error_count = sum(1 for report in quality_report.values() if report['status'] == 'ERROR')
        
        return {
            'total_symbols': total_symbols,
            'ok_count': ok_count,
            'warning_count': warning_count,
            'error_count': error_count,
            'quality_score': ok_count / total_symbols if total_symbols > 0 else 0
        }

class DataStreamManager:
    """Real-time data streaming management"""
    
    def __init__(self, config: DataStreamConfig):
        self.config = config
        self.streams: Dict[str, Any] = {}
        self.data_buffer: Dict[str, List[Dict[str, Any]]] = {}
        self.is_running = False
        
        logger.info(f"DataStreamManager initialized for {len(config.symbols)} symbols")
    
    async def start_streaming(self):
        """Start real-time data streaming"""
        if self.is_running:
            logger.warning("Data streaming already running")
            return
        
        self.is_running = True
        logger.info("Starting real-time data streaming")
        
        # Initialize data buffers
        for symbol in self.config.symbols:
            self.data_buffer[symbol] = []
        
        # Start streaming tasks
        tasks = []
        for symbol in self.config.symbols:
            task = asyncio.create_task(self._stream_symbol_data(symbol))
            tasks.append(task)
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Data streaming error: {e}")
            self.is_running = False
    
    async def stop_streaming(self):
        """Stop real-time data streaming"""
        self.is_running = False
        logger.info("Stopping real-time data streaming")
    
    async def _stream_symbol_data(self, symbol: str):
        """Stream data for a specific symbol"""
        while self.is_running:
            try:
                # Simulate real-time data (replace with actual data source)
                data = await self._get_real_time_data(symbol)
                
                if data:
                    self.data_buffer[symbol].append(data)
                    
                    # Maintain buffer size
                    if len(self.data_buffer[symbol]) > self.config.buffer_size:
                        self.data_buffer[symbol].pop(0)
                
                await asyncio.sleep(1)  # 1 second interval
                
            except Exception as e:
                logger.error(f"Error streaming data for {symbol}: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _get_real_time_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time data for symbol (placeholder implementation)"""
        # This would be replaced with actual real-time data source
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price': 100.0 + np.random.normal(0, 1),
            'volume': int(np.random.exponential(1000))
        }
    
    def get_latest_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest data for symbol"""
        buffer = self.data_buffer.get(symbol, [])
        return buffer[-1] if buffer else None
    
    def get_data_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get data history for symbol"""
        buffer = self.data_buffer.get(symbol, [])
        return buffer[-limit:] if buffer else []

class DataCache:
    """Enhanced caching system for market data with TTL and intelligent eviction"""
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
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
        """Get item from cache"""
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
        """Put item in cache"""
        # Evict if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        # Create cache entry
        cache_entry = {
            'data': data,
            'created': datetime.now(),
            'ttl': ttl or self.default_ttl
        }
        
        self.cache[key] = cache_entry
        self.access_times[key] = datetime.now()
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        return self._remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        self.access_times.clear()
        self.logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'evictions': self.evictions,
            'size': len(self.cache),
            'max_size': self.max_size
        }
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired"""
        created = cache_entry['created']
        ttl = cache_entry['ttl']
        return (datetime.now() - created).total_seconds() > ttl
    
    def _remove(self, key: str) -> bool:
        """Remove item from cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return True
        return False
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove(lru_key)
        self.evictions += 1
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries"""
        expired_keys = []
        for key, cache_entry in self.cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove(key)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)

class EnhancedDataManager:
    """Enhanced unified data management system"""
    
    def __init__(self, config: Optional[MarketDataConfig] = None):
        self.config = config or MarketDataConfig()
        
        # Initialize components
        self.cache = DataCache(
            default_ttl=self.config.cache_ttl_seconds,
            max_size=1000
        )
        
        self.quality_monitor = BasicDataQualityMonitor() if self.config.quality_monitoring else None
        self.stream_manager: Optional[DataStreamManager] = None
        
        # Initialize core components
        try:
            self.clickhouse_client = ClickHouseClient()
            self.metrics_collector = MetricsCollector()
            self.message_bus = MessageBus()
            self.config_manager = ConfigManager()
            logger.info("Core components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize core components: {e}")
            raise
        
        logger.info("EnhancedDataManager initialized")
    
    def load_historical_data(
        self,
        symbols: List[str],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        interval: str = '1d',
        include_volume: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """Load historical data for symbols"""
        logger.info(f"Loading historical data for {len(symbols)} symbols")
        
        # Generate cache key
        cache_key = self._generate_cache_key(symbols, start_date, end_date, interval)
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            logger.info("Data loaded from cache")
            return cached_data
        
        # Load from database
        try:
            data = {}
            for symbol in symbols:
                df = self._load_symbol_data(symbol, start_date, end_date, interval)
                if df is not None and not df.empty:
                    data[symbol] = self._process_symbol_data(df, symbol, include_volume)
            
            # Cache the data
            self.cache.put(cache_key, data)
            
            # Check data quality if monitoring is enabled
            if self.quality_monitor:
                quality_report = self.quality_monitor.check_data_quality(data)
                logger.info(f"Data quality report: {self.quality_monitor.get_quality_summary(quality_report)}")
            
            logger.info(f"Loaded historical data for {len(data)} symbols")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            raise
    
    def start_real_time_streaming(self, symbols: List[str], config: Optional[DataStreamConfig] = None):
        """Start real-time data streaming"""
        if not self.config.real_time_enabled:
            logger.warning("Real-time streaming not enabled")
            return
        
        stream_config = config or DataStreamConfig(symbols=symbols)
        self.stream_manager = DataStreamManager(stream_config)
        
        # Start streaming in background
        asyncio.create_task(self.stream_manager.start_streaming())
        logger.info(f"Started real-time streaming for {len(symbols)} symbols")
    
    def stop_real_time_streaming(self):
        """Stop real-time data streaming"""
        if self.stream_manager:
            asyncio.create_task(self.stream_manager.stop_streaming())
            self.stream_manager = None
            logger.info("Stopped real-time streaming")
    
    def get_real_time_data(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get latest real-time data for symbols"""
        if not self.stream_manager:
            return {symbol: None for symbol in symbols}
        
        return {
            symbol: self.stream_manager.get_latest_data(symbol)
            for symbol in symbols
        }
    
    def get_universe_symbols(self, universe_size: int, min_market_cap: float, min_avg_volume: float) -> List[str]:
        """Get universe of symbols based on institutional-grade screening criteria"""
        logger.info(f"Getting universe of {universe_size} symbols")
        
        # This would implement institutional screening logic
        # For now, return a curated list
        curated_symbols = [
            "SPY", "QQQ", "IWM", "EFA", "EEM", "AGG", "TLT", "GLD", "USO", "VNQ",
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "CRM", "ADBE"
        ]
        
        return curated_symbols[:universe_size]
    
    def validate_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
        """Validate data quality and integrity"""
        validation_errors = {}
        
        for symbol, df in data.items():
            errors = []
            
            if df.empty:
                errors.append("Empty dataframe")
                validation_errors[symbol] = errors
                continue
            
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing columns: {missing_columns}")
            
            # Check for negative prices
            if 'close' in df.columns:
                negative_prices = (df['close'] <= 0).sum()
                if negative_prices > 0:
                    errors.append(f"Negative prices found: {negative_prices}")
            
            # Check for missing values
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                errors.append(f"Missing values: {missing_values}")
            
            if errors:
                validation_errors[symbol] = errors
        
        return validation_errors
    
    def get_data_info(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get comprehensive information about the data"""
        info = {
            'total_symbols': len(data),
            'symbols': list(data.keys()),
            'date_range': {},
            'data_points': {},
            'columns': set()
        }
        
        all_start_dates = []
        all_end_dates = []
        
        for symbol, df in data.items():
            if not df.empty:
                info['data_points'][symbol] = len(df)
                info['columns'].update(df.columns.tolist())
                
                if 'timestamp' in df.index:
                    all_start_dates.append(df.index.min())
                    all_end_dates.append(df.index.max())
        
        if all_start_dates:
            info['date_range'] = {
                'start': min(all_start_dates),
                'end': max(all_end_dates)
            }
        
        info['columns'] = list(info['columns'])
        
        return info
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Clear data cache"""
        self.cache.clear()
        logger.info("Data cache cleared")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status"""
        return {
            'status': 'healthy',
            'cache_stats': self.cache.get_stats(),
            'quality_monitoring': self.quality_monitor is not None,
            'real_time_streaming': self.stream_manager is not None and self.stream_manager.is_running,
            'timestamp': datetime.now()
        }
    
    def _generate_cache_key(self, symbols: List[str], start_date, end_date, interval: str) -> str:
        """Generate cache key for data request"""
        start_str = str(start_date) if start_date else 'None'
        end_str = str(end_date) if end_date else 'None'
        return f"{','.join(sorted(symbols))}_{start_str}_{end_str}_{interval}"
    
    def _load_symbol_data(self, symbol: str, start_date, end_date, interval: str) -> Optional[pd.DataFrame]:
        """Load data for a single symbol from database"""
        try:
            # This would implement actual database query
            # For now, return None as placeholder
            return None
        except Exception as e:
            logger.error(f"Failed to load data for {symbol}: {e}")
            return None
    
    def _process_symbol_data(self, df: pd.DataFrame, symbol: str, include_volume: bool = True) -> pd.DataFrame:
        """Process and clean symbol data"""
        if df.empty:
            return df
        
        # Ensure required columns exist
        required_columns = ['open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0.0
        
        # Remove volume if not requested
        if not include_volume and 'volume' in df.columns:
            df = df.drop('volume', axis=1)
        
        # Clean data
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna()
        
        return df 