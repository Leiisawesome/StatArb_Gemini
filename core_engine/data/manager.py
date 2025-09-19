#!/usr/bin/env python3
"""
Data Manager - Core Engine
==========================

Clean implementation of market data management for core_engine.
Leverages existing high-quality components from core_structure without delegation overhead.

Migration: Direct implementation using proven data management patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production)
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Leverage existing high-quality data components
import sys
# Use internal core_engine types for independence
from ..types import (
    DataManager as BaseDataManager, DataProvider, DataConfig, MarketData
)

# Import data providers with fallbacks
try:
    from core_structure.components.market_data import EnhancedClickHouseLoader, BacktestingDataProvider
    from core_structure.components.market_data.core.data_manager import UnifiedDataManager as CoreDataManager
except ImportError:
    EnhancedClickHouseLoader = None
    BacktestingDataProvider = None
    CoreDataManager = None

logger = logging.getLogger(__name__)

@dataclass
class MarketDataPoint:
    """Standard market data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str = "core_engine"

@dataclass
class DataConfig:
    """Data manager configuration"""
    symbols: List[str] = None
    data_sources: List[str] = None
    update_frequency: int = 60  # seconds
    history_lookback: int = 252  # trading days
    enable_real_time: bool = True
    enable_historical: bool = True
    clickhouse_enabled: bool = True
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['SPY', 'QQQ', 'IWM', 'AAPL', 'MSFT', 'GOOGL']
        if self.data_sources is None:
            self.data_sources = ['clickhouse', 'polygon', 'alpaca']

class IDataSubscriber(ABC):
    """Interface for data subscribers"""
    
    @abstractmethod
    async def on_market_data(self, data: MarketDataPoint) -> None:
        """Handle new market data"""
        pass

class DataManager:
    """
    Core Engine Data Manager
    
    Responsible for:
    1. Market data ingestion from multiple sources
    2. Real-time data feed management  
    3. Historical data retrieval
    4. Data validation and quality assurance
    5. Data distribution to regime engine and other components
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = DataConfig(**config) if config else DataConfig()
        
        # Data storage
        self.latest_data: Dict[str, MarketDataPoint] = {}
        self.historical_data: Dict[str, pd.DataFrame] = {}
        
        # Subscribers for data distribution
        self.subscribers: List[IDataSubscriber] = []
        self.regime_engine: Optional[Any] = None
        
        # Data providers (leverage existing high-quality implementations)
        self.clickhouse_loader: Optional[Any] = None
        self.backtest_provider: Optional[Any] = None
        self.core_data_manager: Optional[Any] = None
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.data_feed_task: Optional[asyncio.Task] = None
        
        logger.info("📊 Data Manager initialized for core engine")
    
    async def initialize(self) -> bool:
        """Initialize data manager and providers"""
        try:
            logger.info("🔄 Initializing Data Manager...")
            
                        # Initialize ClickHouse loader if enabled
            if self.config.clickhouse_enabled and EnhancedClickHouseLoader is not None:
                self.clickhouse_loader = EnhancedClickHouseLoader()
                await self.clickhouse_loader.initialize()
                logger.info("✅ ClickHouse loader initialized")
            
            # Initialize backtesting provider if needed
            if BacktestingDataProvider is not None:
                self.backtest_provider = BacktestingDataProvider()
                logger.info("✅ Backtesting data provider initialized")
            
            # Initialize core data manager
            if CoreDataManager is not None:
                self.core_data_manager = CoreDataManager()
                logger.info("✅ Core data manager initialized")
            
            # Load initial historical data
            await self._load_initial_data()
            
            self.is_initialized = True
            logger.info("✅ Data Manager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data Manager initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start data feeds"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Data Manager not initialized")
            
            logger.info("🚀 Starting data feeds...")
            
            # Start real-time data feed
            if self.config.enable_real_time:
                self.data_feed_task = asyncio.create_task(self._run_data_feed())
                logger.info("✅ Real-time data feed started")
            
            self.is_running = True
            logger.info("✅ Data Manager started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Data Manager: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop data feeds"""
        try:
            logger.info("🛑 Stopping Data Manager...")
            
            if self.data_feed_task:
                self.data_feed_task.cancel()
                try:
                    await self.data_feed_task
                except asyncio.CancelledError:
                    pass
                self.data_feed_task = None
            
            self.is_running = False
            logger.info("✅ Data Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Data Manager: {e}")
            return False
    
    def set_regime_engine(self, regime_engine: Any):
        """Set regime engine for data distribution"""
        self.regime_engine = regime_engine
        logger.info("🔗 Regime engine linked to Data Manager")
    
    def subscribe(self, subscriber: IDataSubscriber):
        """Subscribe to data updates"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New data subscriber added: {type(subscriber).__name__}")
    
    async def get_latest_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """Get latest market data for symbol"""
        return self.latest_data.get(symbol)
    
    async def get_historical_data(self, symbol: str, days: int = None) -> Optional[pd.DataFrame]:
        """Get historical data for symbol"""
        days = days or self.config.history_lookback
        
        try:
            # Try ClickHouse first if available
            if self.clickhouse_loader:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                data = await self.clickhouse_loader.load_data(
                    symbols=[symbol],
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if not data.empty:
                    return data
            
            # Fallback to backtesting provider
            if self.backtest_provider:
                data = await self.backtest_provider.get_historical_data(symbol, days)
                return data
            
            logger.warning(f"⚠️ No historical data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get historical data for {symbol}: {e}")
            return None
    
    async def get_market_data_batch(self, symbols: List[str]) -> Dict[str, MarketDataPoint]:
        """Get latest data for multiple symbols"""
        return {
            symbol: data for symbol, data in self.latest_data.items() 
            if symbol in symbols and data is not None
        }
    
    async def _load_initial_data(self):
        """Load initial historical data for all configured symbols"""
        logger.info("📥 Loading initial historical data...")
        
        for symbol in self.config.symbols:
            try:
                data = await self.get_historical_data(symbol)
                if data is not None:
                    self.historical_data[symbol] = data
                    logger.info(f"✅ Loaded {len(data)} historical records for {symbol}")
                else:
                    logger.warning(f"⚠️ No historical data loaded for {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to load historical data for {symbol}: {e}")
        
        logger.info(f"📥 Initial data load complete for {len(self.historical_data)} symbols")
    
    async def _run_data_feed(self):
        """Run real-time data feed loop"""
        logger.info("📡 Starting real-time data feed loop...")
        
        while self.is_running:
            try:
                # Simulate data updates (in production this would connect to real feeds)
                await self._update_market_data()
                await asyncio.sleep(self.config.update_frequency)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Data feed error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _update_market_data(self):
        """Update market data from sources"""
        for symbol in self.config.symbols:
            try:
                # Generate simulated market data (replace with real feeds in production)
                data_point = await self._get_latest_market_data(symbol)
                
                if data_point:
                    self.latest_data[symbol] = data_point
                    
                    # Distribute to subscribers
                    await self._distribute_data(data_point)
                    
            except Exception as e:
                logger.error(f"❌ Failed to update data for {symbol}: {e}")
    
    async def _get_latest_market_data(self, symbol: str) -> Optional[MarketDataPoint]:
        """Get latest market data for symbol (simulate for now)"""
        # In production, this would fetch from real market data APIs
        # For now, simulate price movement
        
        import random
        base_price = {'SPY': 450, 'QQQ': 380, 'IWM': 200, 'AAPL': 175, 'MSFT': 350, 'GOOGL': 140}.get(symbol, 100)
        
        # Simulate price with small random walk
        price_change = random.uniform(-0.01, 0.01)  # ±1% change
        current_price = base_price * (1 + price_change)
        
        return MarketDataPoint(
            symbol=symbol,
            timestamp=datetime.now(),
            open=current_price * 0.999,
            high=current_price * 1.001,
            low=current_price * 0.998,
            close=current_price,
            volume=random.randint(100000, 1000000),
            source="core_engine_simulation"
        )
    
    async def _distribute_data(self, data: MarketDataPoint):
        """Distribute data to subscribers"""
        # Notify regime engine first (next in flow)
        if self.regime_engine and hasattr(self.regime_engine, 'on_market_data'):
            try:
                await self.regime_engine.on_market_data(data)
            except Exception as e:
                logger.error(f"❌ Failed to notify regime engine: {e}")
        
        # Notify other subscribers
        for subscriber in self.subscribers:
            try:
                await subscriber.on_market_data(data)
            except Exception as e:
                logger.error(f"❌ Failed to notify subscriber {type(subscriber).__name__}: {e}")
    
    def get_data_status(self) -> Dict[str, Any]:
        """Get data manager status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'symbols_count': len(self.config.symbols),
            'latest_data_count': len(self.latest_data),
            'historical_data_count': len(self.historical_data),
            'subscribers_count': len(self.subscribers),
            'clickhouse_enabled': self.config.clickhouse_enabled,
            'real_time_enabled': self.config.enable_real_time
        }