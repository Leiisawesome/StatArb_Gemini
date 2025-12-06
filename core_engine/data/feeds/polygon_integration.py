#!/usr/bin/env python3
"""
Polygon.io Data Integration Service
====================================

Integrates Polygon.io real-time WebSocket feed with the data brick pipeline.
Provides seamless data flow from Polygon.io to the processing pipeline.

Features:
    - Real-time data ingestion from Polygon.io Stock Starter subscription
    - Automatic OHLCV bar construction from aggregated streams
    - Integration with ClickHouseDataManager for persistence
    - Real-time data quality monitoring
    - Pipeline-ready DataFrame output

Usage:
    from core_engine.data.feeds.polygon_integration import PolygonDataService
    
    # Initialize with API key
    service = PolygonDataService(
        api_key="your_polygon_api_key",
        symbols=["AAPL", "TSLA", "NVDA", "GOOGL"],
    )
    
    # Start service
    await service.initialize()
    await service.start()
    
    # Get real-time data as DataFrame
    df = service.get_latest_bars("AAPL", timeframe="1m", limit=100)
    
    # Subscribe to bar updates
    service.add_bar_callback(my_strategy_callback)
    
    # Cleanup
    await service.stop()

Architecture Compliance:
    - Rule 1 (ISystemComponent): Implements lifecycle interface
    - Rule 2 (Data Pipeline): Feeds Phase 1 data ingestion
    - Rule 3 (Unified Data Flow): Standardized data output format

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import asyncio
import logging
import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set

import pandas as pd

from .polygon_realtime import (
    PolygonAggregateBar,
    PolygonAggregatedDataManager,
    PolygonCluster,
    PolygonFeedConfig,
    PolygonRealtimeFeedAdapter,
    PolygonSubscriptionTier,
    PolygonTrade,
)

# Re-export PolygonCluster for easy access
__all_clusters__ = ['PolygonCluster']
from .adapters import FeedMessage, FeedProvider

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool: pass
        @abstractmethod
        async def start(self) -> bool: pass
        @abstractmethod
        async def stop(self) -> bool: pass
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]: pass
        @abstractmethod
        def get_status(self) -> Dict[str, Any]: pass


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class PolygonServiceConfig:
    """
    Configuration for Polygon Data Integration Service.
    
    Stock Starter subscription includes:
        - Per-second aggregated bars (A.*)
        - Per-minute aggregated bars (AM.*)
        - Real-time trades (T.*)
    
    NOTE: You must sign exchange agreements in your Polygon.io dashboard
    before receiving market data: https://polygon.io/dashboard
    """
    # API Authentication
    api_key: str = field(default_factory=lambda: os.getenv("POLYGON_API_KEY", ""))
    
    # Symbols to subscribe
    symbols: List[str] = field(default_factory=list)
    
    # Data types to subscribe
    # Options: "second_agg", "minute_agg", "trade"
    data_types: List[str] = field(default_factory=lambda: ["second_agg", "minute_agg", "trade"])
    
    # Subscription tier
    subscription_tier: PolygonSubscriptionTier = PolygonSubscriptionTier.STARTER
    
    # Use delayed data (15-min delay) instead of real-time
    # Set to True if you haven't signed exchange agreements yet
    use_delayed: bool = False
    
    # Bar storage settings
    max_bars_per_symbol: int = 10000  # Max bars to keep in memory
    
    # Data quality settings
    max_latency_warning_ms: float = 1000.0  # Warn if latency exceeds this
    
    # Enable persistence to ClickHouse
    enable_persistence: bool = False
    
    # Service name for logging
    name: str = "polygon-data-service"
    
    def __post_init__(self):
        if not self.api_key:
            logger.warning(
                "Polygon API key not set. Set POLYGON_API_KEY environment variable "
                "or pass api_key to config."
            )


# ============================================================================
# POLYGON DATA SERVICE
# ============================================================================

class PolygonDataService(ISystemComponent):
    """
    Production Polygon.io Data Integration Service.
    
    Provides:
        - Real-time data streaming from Polygon.io
        - OHLCV bar construction and aggregation
        - DataFrame output for pipeline integration
        - Quality monitoring and latency tracking
    
    Implements ISystemComponent for orchestrator integration (Rule 1).
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        config: Optional[PolygonServiceConfig] = None,
    ):
        """
        Initialize Polygon Data Service.
        
        Args:
            api_key: Polygon.io API key (or set POLYGON_API_KEY env var)
            symbols: List of symbols to subscribe
            config: Full configuration (overrides api_key and symbols)
        """
        # Build config
        if config:
            self.config = config
        else:
            self.config = PolygonServiceConfig(
                api_key=api_key or os.getenv("POLYGON_API_KEY", ""),
                symbols=symbols or [],
            )
        
        # ISystemComponent state
        self.is_initialized = False
        self.is_operational = False
        self.component_id: Optional[str] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{self.config.name}]")
        
        # Polygon adapter and manager
        self._adapter: Optional[PolygonRealtimeFeedAdapter] = None
        self._aggregation_manager: Optional[PolygonAggregatedDataManager] = None
        
        # Bar storage: symbol -> timeframe -> deque of bars
        self._bars: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=self.config.max_bars_per_symbol))
        )
        
        # Trade storage: symbol -> deque of trades
        self._trades: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.config.max_bars_per_symbol)
        )
        
        # Latest prices
        self._latest_prices: Dict[str, float] = {}
        
        # Callbacks
        self._bar_callbacks: List[Callable[[str, str, PolygonAggregateBar], None]] = []
        self._trade_callbacks: List[Callable[[str, PolygonTrade], None]] = []
        
        # Statistics
        self._stats = {
            'messages_received': 0,
            'bars_processed': 0,
            'trades_processed': 0,
            'errors': 0,
            'latency_sum_ms': 0.0,
            'latency_count': 0,
            'start_time': None,
        }
        
        self.logger.info(f"PolygonDataService created for {len(self.config.symbols)} symbols")
    
    async def initialize(self) -> bool:
        """Initialize the Polygon data service"""
        try:
            self.logger.info("Initializing PolygonDataService...")
            
            if not self.config.api_key:
                self.logger.error("Polygon API key not configured")
                return False
            
            # Create Polygon feed configuration
            polygon_config = PolygonFeedConfig(
                api_key=self.config.api_key,
                symbols=self.config.symbols,
                subscription_tier=self.config.subscription_tier,
                cluster=PolygonCluster.STOCKS_DELAYED if self.config.use_delayed else PolygonCluster.STOCKS,
                data_types=self.config.data_types,
                name=self.config.name,
            )
            
            # Create adapter
            self._adapter = PolygonRealtimeFeedAdapter(polygon_config)
            
            # Create aggregation manager
            self._aggregation_manager = PolygonAggregatedDataManager(self._adapter)
            
            # Register message handler
            self._adapter.add_message_handler(self._handle_message)
            
            self.is_initialized = True
            self.logger.info("✅ PolygonDataService initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ PolygonDataService initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the Polygon data service"""
        try:
            if not self.is_initialized:
                self.logger.error("Cannot start - not initialized")
                return False
            
            self.logger.info("Starting PolygonDataService...")
            
            # Connect to Polygon
            if not await self._adapter.connect():
                self.logger.error("Failed to connect to Polygon.io")
                return False
            
            # Subscribe to symbols
            if self.config.symbols:
                if not await self._adapter.subscribe(
                    self.config.symbols,
                    self.config.data_types
                ):
                    self.logger.warning("Subscription may have partially failed")
            
            self._stats['start_time'] = datetime.now()
            self.is_operational = True
            self.logger.info("✅ PolygonDataService started")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ PolygonDataService start failed: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the Polygon data service"""
        try:
            self.logger.info("Stopping PolygonDataService...")
            
            if self._adapter:
                await self._adapter.disconnect()
            
            self.is_operational = False
            self.logger.info("✅ PolygonDataService stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ PolygonDataService stop failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service"""
        adapter_connected = self._adapter.is_connected() if self._adapter else False
        
        # Calculate average latency
        avg_latency = (
            self._stats['latency_sum_ms'] / self._stats['latency_count']
            if self._stats['latency_count'] > 0 else 0
        )
        
        is_healthy = (
            self.is_operational and
            self.is_initialized and
            adapter_connected
        )
        
        return {
            'healthy': is_healthy,
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'PolygonDataService',
            'adapter_connected': adapter_connected,
            'messages_received': self._stats['messages_received'],
            'bars_processed': self._stats['bars_processed'],
            'trades_processed': self._stats['trades_processed'],
            'average_latency_ms': round(avg_latency, 2),
            'symbols_subscribed': len(self.config.symbols),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'component_id': self.component_id,
            'component_type': 'PolygonDataService',
            'symbols': self.config.symbols,
            'data_types': self.config.data_types,
            'subscription_tier': self.config.subscription_tier.value,
            'stats': dict(self._stats),
        }
    
    # ========================================================================
    # DATA ACCESS METHODS
    # ========================================================================
    
    def get_latest_bars(
        self,
        symbol: str,
        timeframe: str = 'minute',
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Get latest OHLCV bars as a DataFrame.
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            timeframe: Bar timeframe ("second" or "minute")
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, vwap
        """
        symbol = symbol.upper()
        
        if symbol not in self._bars or timeframe not in self._bars[symbol]:
            return pd.DataFrame(columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'num_trades'
            ])
        
        bars = list(self._bars[symbol][timeframe])[-limit:]
        
        if not bars:
            return pd.DataFrame(columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap', 'num_trades'
            ])
        
        data = [{
            'timestamp': bar.timestamp_end,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'vwap': bar.vwap,
            'num_trades': bar.num_trades,
        } for bar in bars]
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_latest_trades(
        self,
        symbol: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Get latest trades as a DataFrame.
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of trades to return
            
        Returns:
            DataFrame with columns: timestamp, price, size, conditions
        """
        symbol = symbol.upper()
        
        if symbol not in self._trades:
            return pd.DataFrame(columns=['timestamp', 'price', 'size', 'conditions'])
        
        trades = list(self._trades[symbol])[-limit:]
        
        if not trades:
            return pd.DataFrame(columns=['timestamp', 'price', 'size', 'conditions'])
        
        data = [{
            'timestamp': trade.timestamp,
            'price': trade.price,
            'size': trade.size,
            'conditions': trade.conditions,
        } for trade in trades]
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol"""
        return self._latest_prices.get(symbol.upper())
    
    def get_all_latest_prices(self) -> Dict[str, float]:
        """Get latest prices for all subscribed symbols"""
        return dict(self._latest_prices)
    
    def get_ohlcv_for_pipeline(
        self,
        symbol: str,
        timeframe: str = 'minute',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get OHLCV data formatted for the processing pipeline (Rule 2).
        
        Returns DataFrame with standard columns:
            timestamp (index), open, high, low, close, volume
        
        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Pipeline-ready DataFrame
        """
        df = self.get_latest_bars(symbol, timeframe, limit=self.config.max_bars_per_symbol)
        
        if df.empty:
            return df
        
        # Apply time filters if specified
        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            df = df[df.index >= start_time]
        
        if end_time:
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            df = df[df.index <= end_time]
        
        # Ensure standard column order for pipeline
        return df[['open', 'high', 'low', 'close', 'volume']].copy()
    
    # ========================================================================
    # CALLBACK REGISTRATION
    # ========================================================================
    
    def add_bar_callback(
        self,
        callback: Callable[[str, str, PolygonAggregateBar], None]
    ) -> None:
        """
        Register callback for bar updates.
        
        Callback signature: (symbol, timeframe, bar) -> None
        """
        self._bar_callbacks.append(callback)
    
    def add_trade_callback(
        self,
        callback: Callable[[str, PolygonTrade], None]
    ) -> None:
        """
        Register callback for trade updates.
        
        Callback signature: (symbol, trade) -> None
        """
        self._trade_callbacks.append(callback)
    
    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================
    
    async def subscribe(
        self,
        symbols: List[str],
        data_types: Optional[List[str]] = None,
    ) -> bool:
        """Subscribe to additional symbols"""
        if not self._adapter or not self._adapter.is_connected():
            self.logger.error("Cannot subscribe - not connected")
            return False
        
        data_types = data_types or self.config.data_types
        
        success = await self._adapter.subscribe(symbols, data_types)
        
        if success:
            for symbol in symbols:
                if symbol.upper() not in self.config.symbols:
                    self.config.symbols.append(symbol.upper())
        
        return success
    
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        if not self._adapter:
            return True
        
        success = await self._adapter.unsubscribe(symbols)
        
        if success:
            for symbol in symbols:
                symbol_upper = symbol.upper()
                if symbol_upper in self.config.symbols:
                    self.config.symbols.remove(symbol_upper)
        
        return success
    
    # ========================================================================
    # INTERNAL MESSAGE HANDLING
    # ========================================================================
    
    def _handle_message(self, message: FeedMessage) -> None:
        """Handle incoming message from Polygon adapter"""
        try:
            self._stats['messages_received'] += 1
            
            # Track latency
            if message.latency_ms:
                self._stats['latency_sum_ms'] += message.latency_ms
                self._stats['latency_count'] += 1
                
                if message.latency_ms > self.config.max_latency_warning_ms:
                    self.logger.warning(
                        f"High latency for {message.symbol}: {message.latency_ms:.1f}ms"
                    )
            
            # Route by message type
            if message.message_type in ['second_agg', 'minute_agg']:
                self._handle_aggregate(message)
            elif message.message_type == 'trade':
                self._handle_trade(message)
            elif message.message_type == 'quote':
                self._handle_quote(message)
                
        except Exception as e:
            self._stats['errors'] += 1
            self.logger.error(f"Error handling message: {e}")
    
    def _handle_aggregate(self, message: FeedMessage) -> None:
        """Handle aggregate bar message"""
        symbol = message.symbol.upper()
        data = message.data
        
        # Create bar object
        bar = PolygonAggregateBar(
            symbol=symbol,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            vwap=data.get('vwap', 0),
            timestamp_start=datetime.fromisoformat(data['timestamp_start']),
            timestamp_end=datetime.fromisoformat(data['timestamp_end']),
            num_trades=data.get('num_trades', 0),
            bar_type=data['bar_type'],
        )
        
        # Store bar
        timeframe = 'second' if bar.bar_type == 'second' else 'minute'
        self._bars[symbol][timeframe].append(bar)
        
        # Update latest price
        self._latest_prices[symbol] = bar.close
        
        self._stats['bars_processed'] += 1
        
        # Notify callbacks
        for callback in self._bar_callbacks:
            try:
                callback(symbol, timeframe, bar)
            except Exception as e:
                self.logger.error(f"Bar callback error: {e}")
    
    def _handle_trade(self, message: FeedMessage) -> None:
        """Handle trade message"""
        symbol = message.symbol.upper()
        data = message.data
        
        # Create trade object
        trade = PolygonTrade(
            symbol=symbol,
            price=data['price'],
            size=data['size'],
            timestamp=message.timestamp,
            conditions=data.get('conditions', []),
            exchange=data.get('exchange', 0),
            tape=data.get('tape', 0),
        )
        
        # Store trade
        self._trades[symbol].append(trade)
        
        # Update latest price
        self._latest_prices[symbol] = trade.price
        
        self._stats['trades_processed'] += 1
        
        # Notify callbacks
        for callback in self._trade_callbacks:
            try:
                callback(symbol, trade)
            except Exception as e:
                self.logger.error(f"Trade callback error: {e}")
    
    def _handle_quote(self, message: FeedMessage) -> None:
        """Handle quote message (Developer+ tier)"""
        # Quote handling for higher tiers
        symbol = message.symbol.upper()
        data = message.data
        
        # Update latest price from mid-quote
        bid = data.get('bid', 0)
        ask = data.get('ask', 0)
        if bid and ask:
            self._latest_prices[symbol] = (bid + ask) / 2


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def create_polygon_service(
    api_key: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    auto_start: bool = True,
) -> PolygonDataService:
    """
    Convenience function to create and start a Polygon data service.
    
    Args:
        api_key: Polygon API key (or set POLYGON_API_KEY env var)
        symbols: List of symbols to subscribe
        auto_start: Whether to automatically initialize and start
        
    Returns:
        Configured PolygonDataService instance
    
    Example:
        service = await create_polygon_service(
            api_key="your_key",
            symbols=["AAPL", "TSLA", "NVDA"],
        )
        
        # Get real-time bars
        df = service.get_latest_bars("AAPL")
    """
    service = PolygonDataService(
        api_key=api_key,
        symbols=symbols or [],
    )
    
    if auto_start:
        if not await service.initialize():
            raise RuntimeError("Failed to initialize Polygon service")
        
        if not await service.start():
            raise RuntimeError("Failed to start Polygon service")
    
    return service


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'PolygonServiceConfig',
    'PolygonDataService',
    'create_polygon_service',
]

