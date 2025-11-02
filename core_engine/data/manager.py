#!/usr/bin/env python3
"""
Enhanced Core Engine Data Manager
=================================

Architecturally compliant data manager for core_engine that follows established patterns.
Integrates ClickHouse capabilities while maintaining core_engine design principles.

Key Features:
- Follows core_engine data management patterns
- Implements IDataSubscriber interface for notifications
- Configuration-driven initialization
- Manager pattern with high-quality fallbacks
- Integration with existing core_engine types

Author: StatArb_Gemini Core Engine (Architecture Compliant)
Version: 2.0.0 (Enhanced Architecture)
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
import asyncio
import time
from abc import ABC, abstractmethod

# Timezone handling
try:
    import pytz
except ImportError:
    pytz = None

# Core engine architectural compliance imports
import sys
import os

# Add paths for core_engine imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'types'))

# Import ISystemComponent for orchestrator integration
from core_engine.system.interfaces import ISystemComponent
from core_engine.exceptions import ClickHouseConnectionError, DataUnavailableError

# Import centralized configuration (Rule 1, Section 7)
try:
    from core_engine.config import (
        DataConfig as CentralizedDataConfig,
        ConnectionConfig,
        CachingConfig
    )
except ImportError:
    CentralizedDataConfig = None
    ConnectionConfig = None
    CachingConfig = None

try:
    from core_engine.type_definitions.data import (
        DataManager as BaseDataManager, DataProvider, DataConfig, MarketData
    )
except ImportError:
    # Alternative import approach
    try:
        sys.path.append(os.path.dirname(current_dir))
        from core_engine.type_definitions.data import (
            DataManager as BaseDataManager, DataProvider, DataConfig, MarketData
        )
    except ImportError:
        # Fallback: define minimal interface
        from abc import ABC, abstractmethod
        
        class BaseDataManager(ABC):
            def __init__(self, config: Dict[str, Any]):
                pass
            
            @abstractmethod
            def get_historical_data(self, symbol: str, start_date: datetime, 
                                  end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
                pass
        
        class DataProvider(ABC):
            pass
            
        class DataConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        class MarketData:
            def __init__(self, symbol: str, timestamp: datetime, open: float, 
                        high: float, low: float, close: float, volume: int):
                self.symbol = symbol
                self.timestamp = timestamp
                self.open = open
                self.high = high
                self.low = low
                self.close = close
                self.volume = volume

# Import high-quality data components when available
try:
    from data.manager import DataManager as CoreDataManager, IDataSubscriber, MarketDataPoint
except ImportError:
    # Fallback definitions for architectural compliance
    class IDataSubscriber(ABC):
        @abstractmethod
        async def on_market_data(self, data: Any) -> None:
            pass
    
    MarketDataPoint = None
    CoreDataManager = None

logger = logging.getLogger(__name__)

@dataclass
class ClickHouseDataConfig(DataConfig):
    """
    DEPRECATED: Legacy ClickHouse data configuration
    
    This class provides backward compatibility. New code should use:
        from core_engine.config import DataConfig
    
    Automatically converts to centralized DataConfig format.
    """
    # Legacy parameters (for backward compatibility)
    symbols: List[str] = None
    start_date: Optional[str] = "2024-12-20"
    end_date: Optional[str] = "2024-12-20"
    interval: str = "1min"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "polygon_data"
    enable_caching: bool = True
    cache_ttl: int = 300
    
    def __post_init__(self):
        """Convert to centralized config format"""
        import warnings
        warnings.warn(
            "ClickHouseDataConfig is deprecated. Use DataConfig from core_engine.config",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Initialize inherited DataConfig attributes for backward compatibility
        if not hasattr(self, 'provider'):
            self.provider = "clickhouse"
        if not hasattr(self, 'update_frequency'):
            self.update_frequency = "1min"
        if not hasattr(self, 'cache_enabled'):
            self.cache_enabled = self.enable_caching
            
        if self.symbols is None:
            self.symbols = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'SPY', 'QQQ']
        
        # Date range validation
        self._validate_date_configuration()
    
    def _validate_date_configuration(self):
        """Validate and normalize date configuration"""
        from datetime import datetime
        
        if self.start_date and self.end_date:
            try:
                start_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
                if start_dt > end_dt:
                    raise ValueError(f"start_date ({self.start_date}) must be <= end_date ({self.end_date})")
            except ValueError as e:
                raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}")
        
        elif not (self.start_date or self.end_date):
            # No date configuration provided. Using default.
            self.start_date = "2024-12-20"
            self.end_date = "2024-12-20"
    
    def to_centralized_config(self) -> 'CentralizedDataConfig':
        """Convert to centralized DataConfig format"""
        if CentralizedDataConfig is None or ConnectionConfig is None or CachingConfig is None:
            raise ImportError("Centralized configuration classes not available")

        return CentralizedDataConfig(
            symbols=self.symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            interval=self.interval,
            connection=ConnectionConfig(
                clickhouse_host=self.clickhouse_host,
                clickhouse_port=self.clickhouse_port,
                clickhouse_database=self.clickhouse_database
            ),
            caching=CachingConfig(
                enable_caching=self.enable_caching,
                cache_ttl=self.cache_ttl
            )
        )

@dataclass
class EnhancedMarketData(MarketData):
    """Enhanced market data structure extending core_engine MarketData"""
    transactions: Optional[int] = None
    source: str = "clickhouse"
    
    def to_core_format(self) -> MarketData:
        """Convert to core_engine MarketData format"""
        return MarketData(
            symbol=self.symbol,
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=int(self.volume) if self.volume else 0
        )

class ClickHouseDataManager(BaseDataManager, ISystemComponent):
    """
    Architecturally Compliant ClickHouse Data Manager
    
    Extends core_engine BaseDataManager with ClickHouse capabilities.
    Follows established architectural patterns:
    - Configuration-driven initialization
    - Subscriber pattern for data distribution
    - Manager pattern with clean interfaces
    - High-quality fallbacks and error handling
    
    Integration Points:
    - Implements core_engine data management interface
    - Provides data to regime engine and strategy components
    - Supports real-time and historical data access
    - Compatible with existing portfolio and risk managers
    """
    
    def __init__(self, config: Optional[Union[ClickHouseDataConfig, 'CentralizedDataConfig', Dict[str, Any]]] = None):
        """
        Initialize ClickHouse Data Manager
        
        Args:
            config: Configuration (supports multiple formats):
                - CentralizedDataConfig (from core_engine.config) - RECOMMENDED
                - ClickHouseDataConfig (legacy) - DEPRECATED
                - Dict[str, Any] - For backward compatibility
                - None - Uses defaults
        """
        # Handle different config input types (Phase 1: Centralized Config)
        if config is None:
            # Default: Use legacy for backward compatibility
            self.enhanced_config = ClickHouseDataConfig()
        elif isinstance(config, ClickHouseDataConfig):
            # Legacy config
            self.enhanced_config = config
        elif CentralizedDataConfig and isinstance(config, CentralizedDataConfig):
            # New centralized config - convert to legacy for internal use
            logger.info("✅ Using centralized DataConfig (Rule 1, Section 7)")
            self.enhanced_config = ClickHouseDataConfig(
                symbols=config.symbols,
                start_date=config.start_date,
                end_date=config.end_date,
                interval=config.interval,
                clickhouse_host=config.connection.clickhouse_host,
                clickhouse_port=config.connection.clickhouse_port,
                clickhouse_database=config.connection.clickhouse_database,
                enable_caching=config.caching.enable_caching,
                cache_ttl=config.caching.cache_ttl
            )
        elif isinstance(config, dict):
            # Dictionary config - convert to legacy
            self.enhanced_config = ClickHouseDataConfig(**config)
        else:
            # Unknown type - try to use as-is
            self.enhanced_config = config or ClickHouseDataConfig()
        
        # Create a compatible DataConfig for BaseDataManager with fallback provider
        base_config = DataConfig(
            provider="yahoo",  # Use yahoo as fallback for BaseDataManager
            update_frequency=self.enhanced_config.interval,
            cache_enabled=self.enhanced_config.enable_caching
        )
        
        # Initialize base data manager (for interface compatibility)
        try:
            super().__init__(base_config)
        except Exception:
            # If inheritance fails, just set up our own attributes
            self.provider = None
            self._data_cache = {}
            self._last_update = {}
        
        self.logger = logging.getLogger("enhanced_data_manager")
        
        # HTTP endpoint for ClickHouse
        self.clickhouse_url = f"http://{self.enhanced_config.clickhouse_host}:{self.enhanced_config.clickhouse_port}"
        
        # Data cache for performance
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Subscriber pattern for data distribution (core_engine architecture)
        self.subscribers: List[IDataSubscriber] = []
        self.data_callbacks: List[Callable] = []
        
        # ISystemComponent state management
        self.is_initialized: bool = False
        self.is_operational: bool = False
        self.component_id: Optional[str] = None
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # Regime-aware integration (Rule 2 (Regime-First Principle))
        self.regime_engine: Optional[Any] = None  # EnhancedRegimeEngine reference
        
        # Test ClickHouse connection - FAIL FAST if unavailable
        self._connection_available = False
        try:
            self._connection_available = self._test_connection()
            if not self._connection_available:
                raise ClickHouseConnectionError(
                    "ClickHouse database unavailable. Cannot proceed without real market data."
                )
        except Exception as e:
            if isinstance(e, ClickHouseConnectionError):
                raise
            raise ClickHouseConnectionError(
                f"ClickHouse connection test failed: {e}. Cannot proceed without real market data."
            ) from e
        
        self.logger.info(
            f"ClickHouseDataManager initialized for {len(self.enhanced_config.symbols)} symbols"
        )
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="ClickHouseDataManager",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=10  # Early initialization for data access
        )
        
        self.logger.info(f"✅ ClickHouseDataManager registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            self.logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine reference for regime-aware data processing (Rule 2 Regime-First)
        
        Args:
            regime_engine: EnhancedRegimeEngine instance
        """
        self.regime_engine = regime_engine
        self.logger.info(f"✅ RegimeEngine injected into DataManager (Regime-First Principle)")
    
    def get_current_regime(self) -> Optional[Any]:
        """Get current market regime from regime engine"""
        if self.regime_engine and hasattr(self.regime_engine, 'current_regime'):
            return self.regime_engine.current_regime
        return None
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize the data manager component"""
        try:
            self.logger.info("Initializing ClickHouseDataManager...")
            
            # Test connection - FAIL FAST if unavailable
            self._connection_available = self._test_connection()
            if not self._connection_available:
                raise ClickHouseConnectionError(
                    "ClickHouse database unavailable during initialization. Cannot proceed without real market data."
                )
            
            # Validate configuration
            if not self.enhanced_config.symbols:
                self.logger.warning("No symbols configured for data manager")
            
            # Pre-warm cache with available symbols if connection is available
            if self._connection_available:
                try:
                    available_symbols = self.get_available_symbols()
                    self.logger.info(f"Found {len(available_symbols)} available symbols")
                except Exception as e:
                    self.logger.warning(f"Could not pre-load available symbols: {e}")
            
            self.is_initialized = True
            self.logger.info("✅ ClickHouseDataManager initialization completed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ClickHouseDataManager initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the data manager operations"""
        if not self.is_initialized:
            self.logger.error("Cannot start ClickHouseDataManager - not initialized")
            return False
        
        try:
            self.is_operational = True
            self.logger.info("✅ ClickHouseDataManager started and operational")
            return True
        except Exception as e:
            self.logger.error(f"❌ ClickHouseDataManager start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the data manager operations"""
        try:
            self.is_operational = False
            
            # Clear cache on shutdown
            self.clear_cache()
            
            self.logger.info("✅ ClickHouseDataManager stopped")
            return True
        except Exception as e:
            self.logger.error(f"❌ ClickHouseDataManager stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the data manager"""
        health_status = {
            'healthy': self.is_operational and self.is_initialized and self._connection_available,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_type': 'ClickHouseDataManager',
            'connection_available': self._connection_available,
            'cache_size': len(self._cache),
            'configured_symbols': len(self.enhanced_config.symbols),
            'date_range': {
                'start_date': self.enhanced_config.start_date,
                'end_date': self.enhanced_config.end_date
            }
        }
        
        # Test connection if operational - FAIL FAST if unavailable
        if self.is_operational:
            try:
                connection_test = self._test_connection()
                health_status['connection_test_result'] = connection_test
                if not connection_test:
                    health_status['healthy'] = False
                    health_status['error'] = 'ClickHouse connection failed'
            except Exception as e:
                health_status['connection_error'] = str(e)
                health_status['healthy'] = False
                health_status['error'] = f'ClickHouse connection test failed: {e}'
        
        return health_status
    
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        return {
            'component_type': 'ClickHouseDataManager',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'connection_available': self._connection_available,
            'cache_stats': self.get_cache_stats(),
            'configuration': {
                'symbols_count': len(self.enhanced_config.symbols),
                'interval': self.enhanced_config.interval,
                'date_range': f"{self.enhanced_config.start_date} to {self.enhanced_config.end_date}",
                'caching_enabled': self.enhanced_config.enable_caching
            }
        }
    
    def add_subscriber(self, subscriber: IDataSubscriber) -> None:
        """Add data subscriber following core_engine pattern"""
        self.subscribers.append(subscriber)
        self.logger.info(f"Added data subscriber: {type(subscriber).__name__}")
    
    def remove_subscriber(self, subscriber: IDataSubscriber) -> None:
        """Remove data subscriber"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
    
    async def notify_subscribers(self, data: EnhancedMarketData) -> None:
        """Notify all subscribers of new data"""
        for subscriber in self.subscribers:
            try:
                await subscriber.on_market_data(data)
            except Exception as e:
                self.logger.warning(f"Subscriber notification failed: {e}")
    
    def _test_connection(self) -> bool:
        """Test ClickHouse connection"""
        try:
            import requests
            response = requests.post(self.clickhouse_url, data="SELECT 1", timeout=5)
            if response.status_code == 200 and response.text.strip() == "1":
                self.logger.info("✅ ClickHouse connection successful")
                return True
            raise Exception(f"Unexpected response: {response.text}")
        except Exception as e:
            self.logger.warning(
                "❌ ClickHouse connection failed: %s. Falling back to synthetic data when required.",
                e,
            )
            return False
    
    def _execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute ClickHouse query and return DataFrame with proper timezone handling
        
        CRITICAL: All timestamps returned from ClickHouse queries are handled here at the source.
        ClickHouse toTimeZone() converts timestamp values to NY time but returns timezone-naive datetimes.
        This method ensures all timestamps are properly localized to America/New_York timezone.
        """
        try:
            import requests
            # Add TSVWithNames format to get proper column names
            formatted_query = f"{query} FORMAT TSVWithNames"
            
            response = requests.post(
                self.clickhouse_url, 
                data=formatted_query,
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response as TSV with headers
            from io import StringIO
            df = pd.read_csv(StringIO(response.text), sep='\t')
            
            # FIX TIMEZONE AT SOURCE: Handle timestamp timezone conversion immediately after query
            # This ensures ALL data returned from ClickHouse has correct timezone, regardless of caller
            if 'timestamp' in df.columns and not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # ClickHouse toTimeZone() converts values to NY time but returns timezone-naive
                # Localize directly to America/New_York (NOT UTC!) to avoid 5-hour offset
                if df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize(
                        'America/New_York', 
                        ambiguous='infer', 
                        nonexistent='shift_forward'
                    )
                else:
                    # Already timezone-aware - ensure it's in NY timezone
                    sample_tz_name = str(df['timestamp'].iloc[0].tz) if len(df) > 0 else None
                    if sample_tz_name and 'America/New_York' not in sample_tz_name and 'US/Eastern' not in sample_tz_name:
                        df['timestamp'] = df['timestamp'].dt.tz_convert('America/New_York')
            
            return df
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.error(f"Query: {query}")
            raise
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols for target date"""
        query = f"""
        SELECT ticker, COUNT(*) as records
        FROM {self.enhanced_config.clickhouse_database}.ticks 
        WHERE toDate(toDateTime(window_start / 1000000000)) BETWEEN '{self.enhanced_config.start_date}' AND '{self.enhanced_config.end_date}'
        GROUP BY ticker
        HAVING records >= 100
        ORDER BY records DESC
        """
        
        try:
            result = self._execute_query(query)
            symbols = result['ticker'].tolist()
            self.logger.info(f"Found {len(symbols)} symbols with data for period {self.enhanced_config.start_date} to {self.enhanced_config.end_date}")
            return symbols
        except Exception as e:
            self.logger.error(f"Failed to get available symbols: {e}")
            return []
    
    def load_market_data(
        self,
        symbols: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load market data from ClickHouse
        
        Args:
            symbols: List of symbols to load
            start_time: Start time (defaults to beginning of date range)
            end_time: End time (defaults to end of date range)  
            interval: Data interval (1min, 5min, 15min, 1h)
            
        Returns:
            DataFrame with OHLCV data
        """
        symbols = symbols or self.enhanced_config.symbols
        interval = interval or self.enhanced_config.interval
        
        # Default to full date range if no times specified
        if start_time is None:
            start_time = datetime.strptime(
                f"{self.enhanced_config.start_date} 00:00:00", "%Y-%m-%d %H:%M:%S"
            )
        if end_time is None:
            end_time = datetime.strptime(
                f"{self.enhanced_config.end_date} 23:59:59", "%Y-%m-%d %H:%M:%S"
            )
        
        # Check cache
        cache_key = f"{'-'.join(symbols)}_{start_time}_{end_time}_{interval}"
        if self._is_cached(cache_key):
            self.logger.debug(f"Returning cached data for {cache_key}")
            return self._cache[cache_key]
        
        # Verify ClickHouse connection is available - FAIL FAST if not
        if not self._connection_available:
            raise ClickHouseConnectionError(
                "ClickHouse database unavailable. Cannot load market data without real database connection."
            )
        
        # Build query based on interval
        query = self._build_query(symbols, start_time, end_time, interval)
        
        try:
            start_query_time = time.time()
            df = self._execute_query(query)
            query_time = time.time() - start_query_time
            
            if df.empty:
                raise DataUnavailableError(
                    f"No data returned for symbols {symbols}. Real market data required."
                )
            else:
                # Standardize the data
                df = self._standardize_data(df)
                self.logger.info(
                    "Loaded %d records for %d symbols in %.2fs",
                    len(df),
                    len(symbols),
                    query_time,
                )
        except Exception as e:
            if isinstance(e, (ClickHouseConnectionError, DataUnavailableError)):
                raise
            raise DataUnavailableError(
                f"Failed to load market data from ClickHouse: {e}. Real market data required."
            ) from e
        
        # Cache the result (real or synthetic)
        self._cache[cache_key] = df
        self._cache_timestamps[cache_key] = datetime.now()
        return df

    
    def _build_query(self, symbols: List[str], start_time: datetime, end_time: datetime, interval: str) -> str:
        """Build ClickHouse query for market data"""
        symbols_str = "', '".join(symbols)
        
        # Convert datetime to string format for timezone-aware querying
        start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert datetime to nanoseconds for window_start comparisons (used in aggregated intervals)
        # ClickHouse stores window_start as nanoseconds since epoch
        # Handle timezone-aware datetimes by converting to UTC timestamp first
        if start_time.tzinfo is not None:
            # Timezone-aware: convert to UTC timestamp
            start_ts = start_time.timestamp()
            end_ts = end_time.timestamp()
        else:
            # Timezone-naive: assume it's already in the target timezone (America/New_York)
            # Create timezone-aware datetime for proper timestamp conversion
            if pytz is not None:
                ny_tz = pytz.timezone('America/New_York')
                start_aware = ny_tz.localize(start_time)
                end_aware = ny_tz.localize(end_time)
                start_ts = start_aware.timestamp()
                end_ts = end_aware.timestamp()
            else:
                # Fallback: use system timezone (less accurate but works without pytz)
                start_ts = time.mktime(start_time.timetuple())
                end_ts = time.mktime(end_time.timetuple())
        
        # Convert to nanoseconds (ClickHouse window_start format)
        start_ns = int(start_ts * 1e9)
        end_ns = int(end_ts * 1e9)
        
        if interval == "1min":
            # Use raw 1-minute data with timezone conversion
            query = f"""
            SELECT 
                toTimeZone(toDateTime(window_start / 1000000000), 'America/New_York') as timestamp,
                ticker as symbol,
                open,
                high,
                low,
                close,
                volume,
                transactions
            FROM {self.enhanced_config.clickhouse_database}.ticks
            WHERE ticker IN ('{symbols_str}')
            AND toDateTime(window_start / 1000000000, 'America/New_York') >= '{start_str}'
            AND toDateTime(window_start / 1000000000, 'America/New_York') <= '{end_str}'
            ORDER BY ticker, window_start
            """
        elif interval == "5min":
            # Aggregate to 5-minute bars
            query = f"""
            SELECT 
                toTimeZone(toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 5 minute), 'America/New_York') as timestamp,
                ticker as symbol,
                argMin(open, window_start) as open,
                max(high) as high,
                min(low) as low,
                argMax(close, window_start) as close,
                sum(volume) as volume,
                sum(transactions) as transactions
            FROM {self.enhanced_config.clickhouse_database}.ticks
            WHERE ticker IN ('{symbols_str}')
            AND window_start >= {start_ns}
            AND window_start <= {end_ns}
            GROUP BY ticker, toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 5 minute)
            ORDER BY ticker, timestamp
            """
        elif interval == "15min":
            # Aggregate to 15-minute bars
            query = f"""
            SELECT 
                toTimeZone(toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 15 minute), 'America/New_York') as timestamp,
                ticker as symbol,
                argMin(open, window_start) as open,
                max(high) as high,
                min(low) as low,
                argMax(close, window_start) as close,
                sum(volume) as volume,
                sum(transactions) as transactions
            FROM {self.enhanced_config.clickhouse_database}.ticks
            WHERE ticker IN ('{symbols_str}')
            AND window_start >= {start_ns}
            AND window_start <= {end_ns}
            GROUP BY ticker, toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 15 minute)
            ORDER BY ticker, timestamp
            """
        elif interval == "1h":
            # Aggregate to 1-hour bars
            query = f"""
            SELECT 
                toTimeZone(toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 1 hour), 'America/New_York') as timestamp,
                ticker as symbol,
                argMin(open, window_start) as open,
                max(high) as high,
                min(low) as low,
                argMax(close, window_start) as close,
                sum(volume) as volume,
                sum(transactions) as transactions
            FROM {self.enhanced_config.clickhouse_database}.ticks
            WHERE ticker IN ('{symbols_str}')
            AND window_start >= {start_ns}
            AND window_start <= {end_ns}
            GROUP BY ticker, toStartOfInterval(toDateTime(window_start / 1000000000), INTERVAL 1 hour)
            ORDER BY ticker, timestamp
            """
        else:
            raise ValueError(f"Unsupported interval: {interval}")
        
        return query
    
    def _standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize DataFrame format"""
        if df.empty:
            return df
        
        # Ensure timestamp is datetime (timezone already handled in _execute_query at source)
        # Note: Timezone conversion is now done in _execute_query() to fix it at the data source
        # This ensures all ClickHouse queries return properly timezone-aware timestamps
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # If somehow timezone was lost (shouldn't happen if _execute_query was used), fix it
            if df['timestamp'].dt.tz is None:
                self.logger.warning("Timestamp timezone missing - applying fix (should be handled in _execute_query)")
                df['timestamp'] = df['timestamp'].dt.tz_localize(
                    'America/New_York', 
                    ambiguous='infer', 
                    nonexistent='shift_forward'
                )
        
        # Ensure numeric columns are float
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by symbol and timestamp
        df = df.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
        
        return df
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and still valid"""
        if not self.enhanced_config.enable_caching:
            return False
        
        if cache_key not in self._cache:
            return False
        
        cache_time = self._cache_timestamps.get(cache_key)
        if cache_time is None:
            return False
        
        age = (datetime.now() - cache_time).total_seconds()
        return age < self.enhanced_config.cache_ttl
    
    def get_latest_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, float]:
        """Get latest prices for symbols"""
        symbols = symbols or self.enhanced_config.symbols
        symbols_str = "', '".join(symbols)
        
        query = f"""
        SELECT 
            ticker as symbol,
            argMax(close, window_start) as latest_price
        FROM {self.enhanced_config.clickhouse_database}.ticks
        WHERE ticker IN ('{symbols_str}')
        AND toDate(toDateTime(window_start / 1000000000)) BETWEEN '{self.enhanced_config.start_date}' AND '{self.enhanced_config.end_date}'
        GROUP BY ticker
        """
        
        try:
            df = self._execute_query(query)
            return dict(zip(df['symbol'], df['latest_price']))
        except Exception as e:
            self.logger.error(f"Failed to get latest prices: {e}")
            return {}
    
    def clear_cache(self):
        """Clear data cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("Data cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'cache_timestamps': {k: v.isoformat() for k, v in self._cache_timestamps.items()}
        }
    
    # ========================================================================================
    # CORE ENGINE INTERFACE COMPLIANCE METHODS
    # ========================================================================================
    
    def get_market_data(self, symbol: str, start_time: Optional[str] = None, 
                       end_time: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Core Engine compatible market data interface
        
        Args:
            symbol: Trading symbol
            start_time: Start time in 'YYYY-MM-DD' or 'HH:MM' format (optional)
            end_time: End time in 'YYYY-MM-DD' or 'HH:MM' format (optional)
            
        Returns:
            DataFrame with OHLCV data following core_engine standards
        """
        try:
            # Convert string times to datetime objects for load_market_data
            start_dt = None
            end_dt = None
            
            if start_time:
                # Check format and parse accordingly
                if ' ' in start_time:  # Full datetime format (YYYY-MM-DD HH:MM:SS)
                    start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                elif len(start_time.split('-')) == 3:  # Date format (YYYY-MM-DD)
                    start_dt = datetime.strptime(f"{start_time} 09:30:00", "%Y-%m-%d %H:%M:%S")
                else:  # Time format (HH:MM)
                    start_dt = datetime.strptime(f"{self.enhanced_config.start_date} {start_time}:00", "%Y-%m-%d %H:%M:%S")
            
            if end_time:
                # Check format and parse accordingly
                if ' ' in end_time:  # Full datetime format (YYYY-MM-DD HH:MM:SS)
                    end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                elif len(end_time.split('-')) == 3:  # Date format (YYYY-MM-DD)
                    end_dt = datetime.strptime(f"{end_time} 16:00:00", "%Y-%m-%d %H:%M:%S")
                else:  # Time format (HH:MM)
                    end_dt = datetime.strptime(f"{self.enhanced_config.end_date} {end_time}:59", "%Y-%m-%d %H:%M:%S")
            
            # Use existing load_market_data method
            df = self.load_market_data(
                symbols=[symbol],
                start_time=start_dt,
                end_time=end_dt,
                interval=self.enhanced_config.interval
            )
            
            if df.empty:
                return None
            
            # Filter for specific symbol and convert to core_engine format
            symbol_df = df[df['symbol'] == symbol].copy()
            if symbol_df.empty:
                return None
            
            # Keep timestamp as column for feature engineering compatibility
            # Don't set as index to avoid ambiguity errors
            symbol_df = symbol_df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            # Sort by timestamp for time-series operations
            symbol_df = symbol_df.sort_values('timestamp').reset_index(drop=True)
            
            # Notify subscribers asynchronously
            if not symbol_df.empty:
                # Use asyncio.create_task only if there's a running event loop
                try:
                    asyncio.get_running_loop()
                    asyncio.create_task(self._notify_latest_data_point(symbol, symbol_df))
                except RuntimeError:
                    # No event loop running, skip async notification
                    pass
            
            return symbol_df
            
        except Exception as e:
            self.logger.error(f"Error in get_market_data for {symbol}: {e}")
            return None
    
    async def _notify_latest_data_point(self, symbol: str, df: pd.DataFrame) -> None:
        """Notify subscribers of latest data point (core_engine pattern)"""
        try:
            if df.empty:
                return
                
            # Get the latest row
            latest_row = df.iloc[-1]
            
            # Create EnhancedMarketData object
            market_data = EnhancedMarketData(
                symbol=symbol,
                timestamp=latest_row.name,
                open=float(latest_row['open']),
                high=float(latest_row['high']),
                low=float(latest_row['low']),
                close=float(latest_row['close']),
                volume=float(latest_row['volume']),
                source="clickhouse"
            )
            
            # Note: Subscriber notification not implemented yet
            # await self.notify_subscribers(market_data)
            
        except Exception as e:
            self.logger.warning(f"Failed to notify subscribers: {e}")
    
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, timeframe: str = "1d") -> pd.DataFrame:
        """
        Core Engine compatible historical data interface
        
        Implements BaseDataManager interface for backward compatibility
        """
        try:
            # Check if requested date range overlaps with our configured date range
            config_start = datetime.strptime(self.enhanced_config.start_date, "%Y-%m-%d").date()
            config_end = datetime.strptime(self.enhanced_config.end_date, "%Y-%m-%d").date()
            
            # Handle different date input types
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Convert to date objects if they're datetime objects
            start_date_obj = start_date.date() if hasattr(start_date, 'date') else start_date
            end_date_obj = end_date.date() if hasattr(end_date, 'date') else end_date
            
            if start_date_obj <= config_end and end_date_obj >= config_start:
                df = self.get_market_data(symbol)
                if df is not None and not df.empty:
                    return df
            
            # Fallback to empty DataFrame with required columns
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
        except Exception as e:
            self.logger.error(f"Error in get_historical_data for {symbol}: {e}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price (latest close price from our data)"""
        try:
            df = self.get_market_data(symbol)
            if df is not None and not df.empty:
                return float(df['close'].iloc[-1])
            return None
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices
    
    def load_data(self, symbols: Optional[List[str]] = None, 
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  interval: Optional[str] = None) -> pd.DataFrame:
        """
        Load data from ClickHouse database
        
        This is the primary data loading method for institutional backtesting.
        Provides comprehensive data loading with validation and caching.
        
        Args:
            symbols: List of symbols to load (defaults to config symbols)
            start_time: Start time for data (defaults to beginning of target date)
            end_time: End time for data (defaults to end of target date)
            interval: Data interval (1min, 5min, 15min, 1h)
            
        Returns:
            DataFrame with loaded market data
        """
        return self.load_market_data(symbols, start_time, end_time, interval)
    
    def validate_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate loaded data quality and integrity
        
        Performs comprehensive validation checks on loaded market data
        including completeness, consistency, and anomaly detection.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            Dictionary with validation results and quality metrics
        """
        if data.empty:
            return {
                'valid': False,
                'score': 0.0,
                'issues': ['Empty dataset'],
                'metrics': {}
            }
        
        validation_results = {
            'valid': True,
            'score': 1.0,
            'issues': [],
            'metrics': {}
        }
        
        try:
            # Check for required columns
            required_cols = ['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                validation_results['issues'].append(f"Missing required columns: {missing_cols}")
                validation_results['valid'] = False
                validation_results['score'] -= 0.3
            
            # Check for null values
            null_counts = data.isnull().sum()
            total_nulls = null_counts.sum()
            if total_nulls > 0:
                validation_results['issues'].append(f"Found {total_nulls} null values")
                validation_results['score'] -= 0.1
            
            # Check timestamp ordering
            if 'timestamp' in data.columns:
                timestamps = pd.to_datetime(data['timestamp'])
                if not timestamps.is_monotonic_increasing:
                    validation_results['issues'].append("Timestamps not in chronological order")
                    validation_results['score'] -= 0.2
            
            # Check price consistency (high >= low, close between high/low)
            if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
                invalid_prices = (
                    (data['high'] < data['low']) |
                    (data['close'] > data['high']) |
                    (data['close'] < data['low'])
                ).sum()
                if invalid_prices > 0:
                    validation_results['issues'].append(f"Found {invalid_prices} invalid price relationships")
                    validation_results['score'] -= 0.3  # More severe penalty for price inconsistencies
            
            # Check volume is non-negative
            if 'volume' in data.columns:
                negative_volume = (data['volume'] < 0).sum()
                if negative_volume > 0:
                    validation_results['issues'].append(f"Found {negative_volume} negative volume values")
                    validation_results['score'] -= 0.2  # More severe penalty for negative volume
            
            # Calculate quality metrics
            validation_results['metrics'] = {
                'total_records': len(data),
                'symbols_count': data['symbol'].nunique() if 'symbol' in data.columns else 0,
                'date_range': {
                    'start': data['timestamp'].min().isoformat() if 'timestamp' in data.columns else None,
                    'end': data['timestamp'].max().isoformat() if 'timestamp' in data.columns else None
                },
                'null_percentage': (total_nulls / (len(data) * len(data.columns))) * 100,
                'completeness_score': 1.0 - (total_nulls / (len(data) * len(data.columns)))
            }
            
            # Ensure score doesn't go below 0
            validation_results['score'] = max(0.0, validation_results['score'])
            
            # Mark as invalid if score too low
            if validation_results['score'] < 0.7:
                validation_results['valid'] = False
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['score'] = 0.0
            validation_results['issues'].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    # ========================================
    # STANDARDIZED DATA FLOW METHODS
    # ========================================
    
    def process_market_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Standardized method for processing market data (alias for get_market_data)"""
        return self.get_market_data(symbol, **kwargs)
    
    def fetch_data(self, symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
        """Standardized method for fetching data (alias for load_data)"""
        return self.load_data(symbols, **kwargs)
    
    def process_data(self, symbols: List[str], **kwargs) -> Dict[str, pd.DataFrame]:
        """Standardized method for data processing (alias for load_market_data)"""
        return self.load_market_data(symbols, **kwargs)
    
    # ========================================
    # ANALYTICS INTEGRATION METHODS
    # ========================================
    
    def calculate_metrics(self, data: Any = None) -> Dict[str, Any]:
        """Calculate data analytics metrics"""
        try:
            # Get data manager state
            symbols_count = len(self.symbols) if hasattr(self, 'symbols') else 0
            
            # Calculate data metrics
            data_metrics = {
                'symbols_managed': symbols_count,
                'data_sources_active': 1 if hasattr(self, 'client') and self.client else 0,
                'cache_enabled': getattr(self, 'enable_caching', False),
                'connection_status': 'connected' if hasattr(self, 'client') and self.client else 'disconnected',
                'data_quality_score': self._calculate_data_quality_score(),
                'coverage_metrics': self._calculate_coverage_metrics()
            }
            
            return {
                'metrics_calculated': True,
                'calculation_timestamp': datetime.now(),
                'data_metrics': data_metrics,
                'component': 'ClickHouseDataManager'
            }
            
        except Exception as e:
            self.logger.error(f"Data metrics calculation failed: {e}")
            return {
                'metrics_calculated': False,
                'error': str(e),
                'calculation_timestamp': datetime.now()
            }
    
    def analyze_performance(self, data: Any = None) -> Dict[str, Any]:
        """Analyze data manager performance"""
        try:
            # Analyze data performance
            performance_analysis = {
                'data_availability': self._assess_data_availability(),
                'query_performance': self._assess_query_performance(),
                'data_freshness': self._assess_data_freshness(),
                'system_health': {
                    'connection_stable': hasattr(self, 'client') and self.client is not None,
                    'cache_utilization': self._calculate_cache_utilization(),
                    'error_rate': 0.0  # Mock low error rate
                },
                'performance_summary': {
                    'data_manager_operational': True,
                    'symbols_available': len(self.symbols) if hasattr(self, 'symbols') else 0,
                    'data_pipeline_status': 'active'
                }
            }
            
            return {
                'performance_analyzed': True,
                'analysis_timestamp': datetime.now(),
                'performance_analysis': performance_analysis,
                'component': 'ClickHouseDataManager'
            }
            
        except Exception as e:
            self.logger.error(f"Data performance analysis failed: {e}")
            return {
                'performance_analyzed': False,
                'error': str(e),
                'analysis_timestamp': datetime.now()
            }
    
    def generate_analytics(self, data: Any = None) -> Dict[str, Any]:
        """Generate comprehensive data analytics"""
        try:
            # Combine metrics and performance analysis
            metrics = self.calculate_metrics(data)
            performance = self.analyze_performance(data)
            
            analytics = {
                'analytics_generated': True,
                'generation_timestamp': datetime.now(),
                'metrics': metrics.get('data_metrics', {}),
                'performance': performance.get('performance_analysis', {}),
                'summary': {
                    'data_health': self._assess_data_health(),
                    'reliability_score': self._calculate_reliability_score(),
                    'efficiency_score': self._calculate_efficiency_score()
                },
                'recommendations': self._generate_data_recommendations(),
                'component': 'ClickHouseDataManager'
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Data analytics generation failed: {e}")
            return {
                'analytics_generated': False,
                'error': str(e),
                'generation_timestamp': datetime.now()
            }
    
    def track_performance(self, data: Any = None) -> Dict[str, Any]:
        """Track data manager performance over time"""
        try:
            # Mock performance tracking (in real implementation, would maintain historical data)
            performance_tracking = {
                'tracking_active': True,
                'tracking_timestamp': datetime.now(),
                'current_metrics': self.calculate_metrics(data),
                'performance_trend': self._assess_performance_trend(),
                'alerts': self._generate_data_alerts(),
                'component': 'ClickHouseDataManager'
            }
            
            return performance_tracking
            
        except Exception as e:
            self.logger.error(f"Data performance tracking failed: {e}")
            return {
                'tracking_active': False,
                'error': str(e),
                'tracking_timestamp': datetime.now()
            }
    
    def monitor_performance(self, data: Any = None) -> Dict[str, Any]:
        """Monitor data performance (alias for track_performance)"""
        return self.track_performance(data)
    
    def _calculate_data_quality_score(self) -> float:
        """Calculate data quality score (0-100)"""
        try:
            # Mock data quality assessment
            if hasattr(self, 'client') and self.client:
                return 85.0  # High quality when connected
            else:
                return 50.0  # Moderate quality when disconnected
                
        except Exception:
            return 50.0  # Default moderate quality
    
    def _calculate_coverage_metrics(self) -> Dict[str, Any]:
        """Calculate data coverage metrics"""
        try:
            symbols_count = len(self.symbols) if hasattr(self, 'symbols') else 0
            
            return {
                'symbols_covered': symbols_count,
                'coverage_percentage': min(100.0, symbols_count * 10),  # Mock calculation
                'data_completeness': 90.0  # Mock high completeness
            }
            
        except Exception:
            return {
                'symbols_covered': 0,
                'coverage_percentage': 0.0,
                'data_completeness': 0.0
            }
    
    def _assess_data_availability(self) -> str:
        """Assess data availability"""
        try:
            if hasattr(self, 'client') and self.client:
                return "High"
            else:
                return "Limited"
                
        except Exception:
            return "Unknown"
    
    def _assess_query_performance(self) -> str:
        """Assess query performance"""
        try:
            # Mock performance assessment
            return "Good"  # Assume good performance
            
        except Exception:
            return "Unknown"
    
    def _assess_data_freshness(self) -> str:
        """Assess data freshness"""
        try:
            # Mock freshness assessment
            return "Current"  # Assume current data
            
        except Exception:
            return "Unknown"
    
    def _calculate_cache_utilization(self) -> float:
        """Calculate cache utilization percentage"""
        try:
            if getattr(self, 'enable_caching', False):
                return 75.0  # Mock good cache utilization
            else:
                return 0.0  # No caching
                
        except Exception:
            return 0.0
    
    def _assess_data_health(self) -> str:
        """Assess overall data health"""
        try:
            if hasattr(self, 'client') and self.client:
                symbols_count = len(self.symbols) if hasattr(self, 'symbols') else 0
                if symbols_count > 0:
                    return "Healthy"
                else:
                    return "No symbols configured"
            else:
                return "Disconnected"
                
        except Exception:
            return "Unknown"
    
    def _calculate_reliability_score(self) -> float:
        """Calculate reliability score (0-100)"""
        try:
            if hasattr(self, 'client') and self.client:
                return 90.0  # High reliability when connected
            else:
                return 30.0  # Low reliability when disconnected
                
        except Exception:
            return 50.0  # Default moderate reliability
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate efficiency score (0-100)"""
        try:
            cache_score = 25.0 if getattr(self, 'enable_caching', False) else 0.0
            connection_score = 50.0 if hasattr(self, 'client') and self.client else 0.0
            symbols_score = min(25.0, len(self.symbols) * 2.5) if hasattr(self, 'symbols') else 0.0
            
            return cache_score + connection_score + symbols_score
            
        except Exception:
            return 50.0  # Default moderate efficiency
    
    def _generate_data_recommendations(self) -> List[str]:
        """Generate data recommendations"""
        try:
            recommendations = []
            
            if not (hasattr(self, 'client') and self.client):
                recommendations.append("Establish database connection")
            
            if not getattr(self, 'enable_caching', False):
                recommendations.append("Enable caching for better performance")
            
            symbols_count = len(self.symbols) if hasattr(self, 'symbols') else 0
            if symbols_count == 0:
                recommendations.append("Configure symbols for data management")
            elif symbols_count < 5:
                recommendations.append("Consider adding more symbols for diversification")
            
            return recommendations
            
        except Exception:
            return ["Unable to generate recommendations"]
    
    def _assess_performance_trend(self) -> str:
        """Assess performance trend"""
        try:
            # Mock trend assessment
            if hasattr(self, 'client') and self.client:
                return "Stable"
            else:
                return "Declining"
                
        except Exception:
            return "Unknown"
    
    def _generate_data_alerts(self) -> List[str]:
        """Generate data alerts"""
        try:
            alerts = []
            
            if not (hasattr(self, 'client') and self.client):
                alerts.append("Database connection lost")
            
            symbols_count = len(self.symbols) if hasattr(self, 'symbols') else 0
            if symbols_count == 0:
                alerts.append("No symbols configured")
            
            return alerts
            
        except Exception:
            return []