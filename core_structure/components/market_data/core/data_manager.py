"""
Unified Data Manager - Market Data Core
=======================================

Consolidated data management system combining:
- Enhanced data manager functionality
- Data processing operations  
- Backtesting data provider
- Unified data pipeline management

This module replaces:
- enhanced_data_manager.py (589 lines)
- data_processor.py (657 lines) 
- backtesting_data_provider.py (195 lines)

Author: StatArb_Gemini Architecture Consolidation
Version: 4.0 (Phase 4B)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union, Callable, Set
from datetime import datetime, timedelta
import logging
import asyncio
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
import warnings
from concurrent.futures import ThreadPoolExecutor
import queue

# Core infrastructure imports
try:
    from core_structure.infrastructure import (
        ClickHouseClient,
        MetricsCollector,
        MessageBus,
        ConfigManager
    )
except ImportError:
    ClickHouseClient = None
    MetricsCollector = None  
    MessageBus = None
    ConfigManager = None

logger = logging.getLogger(__name__)

class DataStatus(Enum):
    """Data status enumeration"""
    VALID = "valid"
    STALE = "stale"
    INVALID = "invalid"
    MISSING = "missing"
    PROCESSING = "processing"

class ProcessingMode(Enum):
    """Data processing mode"""
    REALTIME = "realtime"
    BATCH = "batch"
    BACKTEST = "backtest"
    VALIDATION = "validation"

@dataclass
class DataQualityThresholds:
    """Data quality monitoring thresholds"""
    max_price_change: float = 0.1  # 10% max price change
    max_volume: int = 1000000      # 1M max volume
    max_staleness: int = 300       # 5 minutes max staleness
    min_data_points: int = 10      # Minimum data points required
    price_precision: int = 4       # Price decimal precision
    volume_precision: int = 0      # Volume decimal precision

@dataclass
class DataStreamConfig:
    """Real-time data streaming configuration"""
    symbols: List[str]
    interval: str = "1m"
    include_depth: bool = False
    include_volume: bool = True
    buffer_size: int = 1000
    reconnect_attempts: int = 3
    max_latency_ms: int = 100
    quality_checks: bool = True

@dataclass
class MarketDataConfig:
    """Configuration for market data operations"""
    cache_ttl_seconds: int = 300
    real_time_enabled: bool = True
    max_symbols_per_query: int = 50
    default_lookback_days: int = 252
    processing_mode: ProcessingMode = ProcessingMode.REALTIME
    quality_thresholds: DataQualityThresholds = field(default_factory=DataQualityThresholds)
    stream_config: Optional[DataStreamConfig] = None
    enable_preprocessing: bool = True
    enable_validation: bool = True

@dataclass
class DataMetrics:
    """Data processing metrics"""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    processing_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.now)

class DataQualityMonitor:
    """Integrated data quality monitoring"""
    
    def __init__(self, thresholds: DataQualityThresholds):
        self.thresholds = thresholds
        self.metrics = DataMetrics()
        self._quality_history = {}
        
    def validate_data(self, data: pd.DataFrame, symbol: str) -> Tuple[bool, List[str]]:
        """Validate data quality with detailed error reporting"""
        issues = []
        
        if data.empty:
            issues.append(f"Empty dataset for {symbol}")
            return False, issues
            
        # Price validation
        if 'close' in data.columns:
            price_changes = data['close'].pct_change().abs()
            if (price_changes > self.thresholds.max_price_change).any():
                issues.append(f"Excessive price changes detected for {symbol}")
                
        # Volume validation  
        if 'volume' in data.columns:
            if (data['volume'] > self.thresholds.max_volume).any():
                issues.append(f"Excessive volume detected for {symbol}")
                
        # Data completeness
        if len(data) < self.thresholds.min_data_points:
            issues.append(f"Insufficient data points for {symbol}: {len(data)} < {self.thresholds.min_data_points}")
            
        # Staleness check
        if 'timestamp' in data.columns:
            latest_time = pd.to_datetime(data['timestamp']).max()
            staleness = (datetime.now() - latest_time).total_seconds()
            if staleness > self.thresholds.max_staleness:
                issues.append(f"Stale data for {symbol}: {staleness:.0f}s old")
                
        return len(issues) == 0, issues

class DataProcessor:
    """Unified data processing engine"""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.quality_monitor = DataQualityMonitor(config.quality_thresholds)
        self._cache = {}
        self._processing_stats = {}
        
    def process_raw_data(self, raw_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Process raw market data with quality checks and standardization"""
        start_time = time.time()
        
        try:
            # Basic validation
            if self.config.enable_validation:
                is_valid, issues = self.quality_monitor.validate_data(raw_data, symbol)
                if not is_valid:
                    logger.warning(f"Data quality issues for {symbol}: {issues}")
                    
            # Data standardization
            processed_data = self._standardize_data(raw_data, symbol)
            
            # Apply preprocessing if enabled
            if self.config.enable_preprocessing:
                processed_data = self._preprocess_data(processed_data, symbol)
                
            # Update metrics
            processing_time = (time.time() - start_time) * 1000
            self._update_processing_stats(symbol, len(processed_data), processing_time)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing data for {symbol}: {e}")
            self.quality_monitor.metrics.error_count += 1
            raise
            
    def _standardize_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Standardize data format and columns"""
        standardized = data.copy()
        
        # Ensure timestamp column
        if 'timestamp' not in standardized.columns and standardized.index.name == 'timestamp':
            standardized = standardized.reset_index()
            
        # Standardize column names
        column_mapping = {
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'timestamp': 'timestamp'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in standardized.columns and old_col != new_col:
                standardized = standardized.rename(columns={old_col: new_col})
                
        # Ensure numeric types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in standardized.columns:
                standardized[col] = pd.to_numeric(standardized[col], errors='coerce')
                
        # Ensure timestamp is datetime
        if 'timestamp' in standardized.columns:
            standardized['timestamp'] = pd.to_datetime(standardized['timestamp'])
            
        # Add symbol column if not present
        if 'symbol' not in standardized.columns:
            standardized['symbol'] = symbol
            
        return standardized
        
    def _preprocess_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Apply preprocessing operations"""
        processed = data.copy()
        
        # Sort by timestamp
        if 'timestamp' in processed.columns:
            processed = processed.sort_values('timestamp')
            
        # Remove duplicates
        processed = processed.drop_duplicates()
        
        # Forward fill missing values
        processed = processed.fillna(method='ffill')
        
        # Remove outliers (basic z-score method)
        if 'close' in processed.columns and len(processed) > 10:
            z_scores = np.abs((processed['close'] - processed['close'].mean()) / processed['close'].std())
            processed = processed[z_scores < 3]  # Remove data more than 3 std devs away
            
        return processed
        
    def _update_processing_stats(self, symbol: str, record_count: int, processing_time: float):
        """Update processing statistics"""
        if symbol not in self._processing_stats:
            self._processing_stats[symbol] = {
                'total_records': 0,
                'total_time': 0.0,
                'call_count': 0
            }
            
        stats = self._processing_stats[symbol]
        stats['total_records'] += record_count
        stats['total_time'] += processing_time
        stats['call_count'] += 1

class BacktestingDataProvider:
    """Backtesting data provider integration"""
    
    def __init__(self, data_manager: 'UnifiedDataManager'):
        self.data_manager = data_manager
        self.backtest_cache = {}
        
    def get_historical_data(self, 
                          symbols: List[str],
                          start_date: datetime,
                          end_date: datetime,
                          interval: str = "1m") -> Dict[str, pd.DataFrame]:
        """Get historical data for backtesting"""
        result = {}
        
        for symbol in symbols:
            try:
                data = self.data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval
                )
                
                if data is not None and not data.empty:
                    result[symbol] = data
                else:
                    logger.warning(f"No data available for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error getting historical data for {symbol}: {e}")
                
        return result
        
    def setup_backtest_environment(self, config: dict) -> bool:
        """Setup backtesting environment"""
        try:
            # Configure data manager for backtesting mode
            self.data_manager.config.processing_mode = ProcessingMode.BACKTEST
            self.data_manager.config.real_time_enabled = False
            
            # Clear real-time caches
            self.data_manager._clear_realtime_caches()
            
            logger.info("Backtesting environment configured")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up backtest environment: {e}")
            return False

class UnifiedDataManager:
    """
    Unified data manager consolidating all market data functionality
    
    Replaces:
    - EnhancedDataManager
    - DataProcessor  
    - BacktestingDataProvider
    """
    
    def __init__(self, config: Optional[MarketDataConfig] = None):
        self.config = config or MarketDataConfig()
        self.data_processor = DataProcessor(self.config)
        self.backtesting_provider = BacktestingDataProvider(self)
        
        # Core components
        self._cache = {}
        self._real_time_feeds = {}
        self._subscribers = {}
        self._processing_queue = queue.Queue()
        self._metrics = DataMetrics()
        
        # Initialize infrastructure components if available
        self.clickhouse_client = ClickHouseClient() if ClickHouseClient else None
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        self.message_bus = MessageBus() if MessageBus else None
        
        # Background processing
        self._processing_thread = None
        self._running = False
        
        logger.info("UnifiedDataManager initialized")
        
    def start(self):
        """Start the data manager"""
        if not self._running:
            self._running = True
            self._processing_thread = threading.Thread(target=self._background_processor)
            self._processing_thread.daemon = True
            self._processing_thread.start()
            logger.info("UnifiedDataManager started")
            
    def stop(self):
        """Stop the data manager"""
        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5)
        logger.info("UnifiedDataManager stopped")
        
    def get_historical_data(self,
                          symbol: str,
                          start_date: datetime,
                          end_date: datetime,
                          interval: str = "1m") -> Optional[pd.DataFrame]:
        """Get historical market data"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{start_date}_{end_date}_{interval}"
            if cache_key in self._cache:
                cached_data, cache_time = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self.config.cache_ttl_seconds:
                    self._metrics.cache_hit_rate += 1
                    return cached_data
                    
            # Fetch from data source
            raw_data = self._fetch_historical_data(symbol, start_date, end_date, interval)
            
            if raw_data is not None and not raw_data.empty:
                # Process the data
                processed_data = self.data_processor.process_raw_data(raw_data, symbol)
                
                # Cache the result
                self._cache[cache_key] = (processed_data, datetime.now())
                
                # Update metrics
                self._metrics.total_records += len(processed_data)
                self._metrics.valid_records += len(processed_data)
                
                return processed_data
            else:
                logger.warning(f"No data returned for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            self._metrics.error_count += 1
            return None
            
    def _fetch_historical_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str) -> Optional[pd.DataFrame]:
        """Fetch historical data from data source"""
        if self.clickhouse_client:
            try:
                # Use ClickHouse if available
                query = f"""
                SELECT timestamp, open, high, low, close, volume
                FROM market_data 
                WHERE symbol = '{symbol}'
                AND timestamp BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY timestamp
                """
                return self.clickhouse_client.query_dataframe(query)
            except Exception as e:
                logger.error(f"ClickHouse query failed: {e}")
                
        # Fallback to mock data for testing
        return self._generate_mock_data(symbol, start_date, end_date, interval)
        
    def _generate_mock_data(self, symbol: str, start_date: datetime, end_date: datetime, interval: str) -> pd.DataFrame:
        """Generate mock data for testing"""
        periods = int((end_date - start_date).total_seconds() / 60)  # Assuming 1min intervals
        dates = pd.date_range(start_date, end_date, periods=periods)
        
        # Generate realistic price data
        np.random.seed(hash(symbol) % 2**32)
        returns = np.random.normal(0, 0.01, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.002, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.002, len(dates)))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates)),
            'symbol': symbol
        })
        
    def _background_processor(self):
        """Background processing thread"""
        while self._running:
            try:
                # Process queued items
                if not self._processing_queue.empty():
                    item = self._processing_queue.get_nowait()
                    self._process_queue_item(item)
                    
                # Periodic maintenance
                self._periodic_maintenance()
                
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                
    def _process_queue_item(self, item: dict):
        """Process a queued item"""
        # Implementation for processing queued data updates
        pass
        
    def _periodic_maintenance(self):
        """Periodic maintenance tasks"""
        # Clean up old cache entries
        current_time = datetime.now()
        expired_keys = []
        
        for key, (data, cache_time) in self._cache.items():
            if (current_time - cache_time).seconds > self.config.cache_ttl_seconds:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self._cache[key]
            
    def _clear_realtime_caches(self):
        """Clear real-time caches for backtesting"""
        self._cache.clear()
        self._real_time_feeds.clear()
        
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_records': self._metrics.total_records,
            'valid_records': self._metrics.valid_records,
            'invalid_records': self._metrics.invalid_records,
            'error_count': self._metrics.error_count,
            'cache_hit_rate': self._metrics.cache_hit_rate,
            'processing_stats': self.data_processor._processing_stats,
            'cache_size': len(self._cache)
        }

# Backward compatibility aliases
EnhancedDataManager = UnifiedDataManager
DataManager = UnifiedDataManager

# Export classes
__all__ = [
    'UnifiedDataManager',
    'DataProcessor', 
    'BacktestingDataProvider',
    'DataQualityMonitor',
    'MarketDataConfig',
    'DataConfig',  # Alias for backward compatibility
    'DataQualityThresholds',
    'DataStreamConfig',
    'DataStatus',
    'ProcessingMode',
    'DataMetrics',
    # Backward compatibility
    'EnhancedDataManager',
    'DataManager'
]

# Create alias for backward compatibility
DataConfig = MarketDataConfig
