"""
WebSocket Diversification Integration
====================================

Integration module connecting WebSocket diversification to existing trading systems.
Provides unified interface for strategy engines and paper trading systems.

This module:
- Integrates WebSocket diversification with existing strategies
- Provides data routing to paper trading engine
- Handles real-time data standardization
- Manages subscription lifecycle
- Provides monitoring and analytics integration

Author: StatArb_Gemini WebSocket Enhancement
Version: 1.0
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from queue import Queue, Empty
import pandas as pd
import json

# Import existing infrastructure - MANDATORY (NO FALLBACKS)
from .websocket_diversification import (
    WebSocketDiversificationManager, 
    WebSocketSource, 
    SourceConfig, 
    SourcePriority,
    DataType,
    WebSocketMessage,
    create_websocket_diversification_manager
)
from ..core.data_feeds import MarketDataPoint, DataSource
# TODO: Implement these dependencies when ready:
# from core_structure.strategies.unified_strategy_system import StrategyEngine  
# from paper_trading.multi_strategy_paper_trading import MultiStrategyPaperTradingEngine

logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for WebSocket integration"""
    # Data source API keys
    alpaca_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    
    # Symbol lists
    symbols: List[str] = field(default_factory=lambda: ["SPY", "QQQ", "IWM", "AAPL", "MSFT"])
    data_types: List[str] = field(default_factory=lambda: ["trade", "quote"])
    
    # Buffer and processing
    message_buffer_size: int = 5000
    processing_batch_size: int = 100
    max_latency_ms: float = 1000.0
    
    # Quality and reliability
    enable_quality_monitoring: bool = True
    enable_failover: bool = True
    min_source_count: int = 1
    
    # Integration settings
    enable_strategy_integration: bool = True
    enable_paper_trading_integration: bool = True
    enable_analytics_integration: bool = True

@dataclass
class MarketDataUpdate:
    """Standardized market data update for strategy consumption"""
    symbol: str
    timestamp: datetime
    price: float
    volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    source: str = "websocket"
    data_type: str = "trade"
    quality_score: float = 1.0

class WebSocketStrategyIntegration:
    """
    Integration layer between WebSocket diversification and strategy engines
    """
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self._ws_manager = None
        self._running = False
        
        # Data processing
        self._data_processors = []
        self._strategy_subscribers = {}
        self._paper_trading_engine = None
        
        # Message routing
        self._message_buffer = Queue(maxsize=config.message_buffer_size)
        self._processing_thread = None
        
        # Analytics and monitoring
        self._analytics_callbacks = []
        self._performance_metrics = {
            "messages_processed": 0,
            "messages_dropped": 0,
            "processing_latency_ms": 0.0,
            "last_update_time": None
        }
        
        logger.info("WebSocket Strategy Integration initialized")
    
    async def initialize(self):
        """Initialize the WebSocket integration"""
        try:
            # Create WebSocket diversification manager
            self._ws_manager = create_websocket_diversification_manager(
                alpaca_api_key=self.config.alpaca_api_key,
                polygon_api_key=self.config.polygon_api_key,
                symbols=self.config.symbols
            )
            
            # Add message subscriber
            self._ws_manager.add_subscriber(self._handle_websocket_message)
            
            # Start WebSocket manager
            await self._ws_manager.start()
            
            # Subscribe to symbols
            data_types = [getattr(DataType, dt.upper()) for dt in self.config.data_types if hasattr(DataType, dt.upper())]
            await self._ws_manager.subscribe_symbols(self.config.symbols, data_types)
            
            # Start processing thread
            self._running = True
            self._processing_thread = threading.Thread(target=self._processing_loop)
            self._processing_thread.daemon = True
            self._processing_thread.start()
            
            logger.info("WebSocket integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket integration: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the WebSocket integration"""
        self._running = False
        
        if self._ws_manager:
            await self._ws_manager.stop()
        
        logger.info("WebSocket integration shut down")
    
    def _handle_websocket_message(self, message: WebSocketMessage):
        """Handle incoming WebSocket message"""
        try:
            # Add to processing buffer
            self._message_buffer.put(message, timeout=0.1)
            
        except Exception as e:
            self._performance_metrics["messages_dropped"] += 1
            logger.warning(f"Dropped WebSocket message: {e}")
    
    def _processing_loop(self):
        """Main message processing loop"""
        batch = []
        last_process_time = time.time()
        
        while self._running:
            try:
                # Collect messages in batches
                try:
                    message = self._message_buffer.get(timeout=0.1)
                    batch.append(message)
                    
                    # Process batch when full or after timeout
                    if (len(batch) >= self.config.processing_batch_size or 
                        time.time() - last_process_time > 0.1):
                        
                        self._process_message_batch(batch)
                        batch.clear()
                        last_process_time = time.time()
                    
                except Empty:
                    # Process any remaining messages
                    if batch:
                        self._process_message_batch(batch)
                        batch.clear()
                        last_process_time = time.time()
                    continue
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                batch.clear()
    
    def _process_message_batch(self, messages: List[WebSocketMessage]):
        """Process a batch of WebSocket messages"""
        start_time = time.time()
        
        try:
            for message in messages:
                # Convert to standardized format
                market_update = self._convert_to_market_update(message)
                
                if market_update:
                    # Route to subscribers
                    self._route_market_update(market_update)
                    
                    self._performance_metrics["messages_processed"] += 1
            
            # Update performance metrics
            processing_time = (time.time() - start_time) * 1000
            self._performance_metrics["processing_latency_ms"] = processing_time
            self._performance_metrics["last_update_time"] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing message batch: {e}")
    
    def _convert_to_market_update(self, message: WebSocketMessage) -> Optional[MarketDataUpdate]:
        """Convert WebSocket message to standardized market update"""
        try:
            # Extract common fields
            symbol = message.symbol
            timestamp = message.timestamp
            data = message.data
            
            # Extract price and volume based on message type
            price = None
            volume = None
            bid = None
            ask = None
            
            if message.message_type.value == "trade":
                price = data.get("p") or data.get("price") or data.get("c")
                volume = data.get("s") or data.get("size") or data.get("v")
                
            elif message.message_type.value == "quote":
                bid = data.get("bp") or data.get("bid_price") or data.get("b")
                ask = data.get("ap") or data.get("ask_price") or data.get("a")
                price = (bid + ask) / 2 if (bid and ask) else (bid or ask)
            
            if price is None:
                return None
            
            # Calculate spread
            spread = None
            if bid and ask:
                spread = ask - bid
            
            return MarketDataUpdate(
                symbol=symbol,
                timestamp=timestamp,
                price=float(price),
                volume=int(volume) if volume else None,
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                spread=float(spread) if spread else None,
                source=message.source.value,
                data_type=message.message_type.value,
                quality_score=message.quality_score
            )
            
        except Exception as e:
            logger.error(f"Error converting message: {e}")
            return None
    
    def _route_market_update(self, update: MarketDataUpdate):
        """Route market update to appropriate subscribers"""
        try:
            # Route to strategy subscribers
            if update.symbol in self._strategy_subscribers:
                for callback in self._strategy_subscribers[update.symbol]:
                    try:
                        callback(update)
                    except Exception as e:
                        logger.error(f"Error in strategy callback: {e}")
            
            # Route to paper trading engine
            if self._paper_trading_engine and self.config.enable_paper_trading_integration:
                self._route_to_paper_trading(update)
            
            # Route to analytics
            if self.config.enable_analytics_integration:
                self._route_to_analytics(update)
                
        except Exception as e:
            logger.error(f"Error routing market update: {e}")
    
    def _route_to_paper_trading(self, update: MarketDataUpdate):
        """Route update to paper trading engine"""
        try:
            # Convert to format expected by paper trading engine
            market_data = {
                "symbol": update.symbol,
                "price": update.price,
                "timestamp": update.timestamp,
                "volume": update.volume,
                "bid": update.bid,
                "ask": update.ask,
                "source": "websocket_diversification"
            }
            
            # Send to paper trading engine if it has a market data handler
            if hasattr(self._paper_trading_engine, 'handle_market_data'):
                self._paper_trading_engine.handle_market_data(market_data)
                
        except Exception as e:
            logger.error(f"Error routing to paper trading: {e}")
    
    def _route_to_analytics(self, update: MarketDataUpdate):
        """Route update to analytics callbacks"""
        try:
            for callback in self._analytics_callbacks:
                callback(update)
        except Exception as e:
            logger.error(f"Error routing to analytics: {e}")
    
    def register_strategy_subscriber(self, symbol: str, callback: Callable[[MarketDataUpdate], None]):
        """Register a strategy for market data updates"""
        if symbol not in self._strategy_subscribers:
            self._strategy_subscribers[symbol] = []
        
        self._strategy_subscribers[symbol].append(callback)
        logger.info(f"Registered strategy subscriber for {symbol}")
    
    def register_paper_trading_engine(self, engine):
        """Register paper trading engine"""
        self._paper_trading_engine = engine
        logger.info("Registered paper trading engine")
    
    def register_analytics_callback(self, callback: Callable[[MarketDataUpdate], None]):
        """Register analytics callback"""
        self._analytics_callbacks.append(callback)
        logger.info("Registered analytics callback")
    
    async def add_symbols(self, symbols: List[str]):
        """Add new symbols to subscription"""
        if self._ws_manager:
            data_types = [getattr(DataType, dt.upper()) for dt in self.config.data_types if hasattr(DataType, dt.upper())]
            await self._ws_manager.subscribe_symbols(symbols, data_types)
            
            # Update config
            self.config.symbols.extend([s for s in symbols if s not in self.config.symbols])
            
            logger.info(f"Added symbols: {symbols}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance and status metrics"""
        metrics = self._performance_metrics.copy()
        
        # Add WebSocket manager status if available
        if self._ws_manager:
            ws_status = self._ws_manager.get_status_summary()
            metrics["websocket_status"] = ws_status
        
        # Add buffer status
        metrics["buffer_size"] = self._message_buffer.qsize()
        metrics["max_buffer_size"] = self.config.message_buffer_size
        
        return metrics
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """Get data quality report"""
        if not self._ws_manager:
            return {"error": "WebSocket manager not initialized"}
        
        ws_status = self._ws_manager.get_status_summary()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy" if ws_status["active_sources"] >= self.config.min_source_count else "degraded",
            "active_sources": ws_status["active_sources"],
            "total_sources": ws_status["total_sources"],
            "primary_source": ws_status["primary_source"],
            "total_messages": ws_status["total_messages"],
            "source_switches": ws_status["source_switches"],
            "processing_metrics": self._performance_metrics,
            "source_details": ws_status["sources"]
        }
        
        return report

# Enhanced paper trading integration
class WebSocketPaperTradingIntegration:
    """
    Enhanced paper trading integration with WebSocket diversification
    """
    
    def __init__(self, paper_trading_engine, websocket_integration: WebSocketStrategyIntegration):
        self.paper_trading_engine = paper_trading_engine
        self.websocket_integration = websocket_integration
        
        # Market data cache
        self._market_data_cache = {}
        self._price_history = {}
        
        # Register with WebSocket integration
        self.websocket_integration.register_paper_trading_engine(self)
        
        logger.info("WebSocket Paper Trading Integration initialized")
    
    def handle_market_data(self, market_data: Dict[str, Any]):
        """Handle market data from WebSocket integration"""
        try:
            symbol = market_data["symbol"]
            price = market_data["price"]
            timestamp = market_data["timestamp"]
            
            # Update cache
            self._market_data_cache[symbol] = market_data
            
            # Update price history
            if symbol not in self._price_history:
                self._price_history[symbol] = []
            
            self._price_history[symbol].append({
                "price": price,
                "timestamp": timestamp
            })
            
            # Keep only recent history (last 1000 points)
            if len(self._price_history[symbol]) > 1000:
                self._price_history[symbol] = self._price_history[symbol][-1000:]
            
            # Forward to paper trading engine's risk manager if it exists
            if hasattr(self.paper_trading_engine, 'risk_manager'):
                risk_manager = self.paper_trading_engine.risk_manager
                if hasattr(risk_manager, 'update_market_data'):
                    risk_manager.update_market_data(symbol, price, timestamp)
            
        except Exception as e:
            logger.error(f"Error handling market data: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        if symbol in self._market_data_cache:
            return self._market_data_cache[symbol]["price"]
        return None
    
    def get_price_history(self, symbol: str, count: int = 100) -> List[Dict[str, Any]]:
        """Get recent price history for symbol"""
        if symbol in self._price_history:
            return self._price_history[symbol][-count:]
        return []

# Factory function for easy setup
def create_websocket_integration(
    symbols: List[str] = None,
    alpaca_api_key: Optional[str] = None,
    polygon_api_key: Optional[str] = None,
    paper_trading_engine = None
) -> WebSocketStrategyIntegration:
    """Create WebSocket integration with default configuration"""
    
    if symbols is None:
        symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    
    config = IntegrationConfig(
        alpaca_api_key=alpaca_api_key,
        polygon_api_key=polygon_api_key,
        symbols=symbols,
        data_types=["trade", "quote"],
        enable_strategy_integration=True,
        enable_paper_trading_integration=bool(paper_trading_engine),
        enable_analytics_integration=True
    )
    
    integration = WebSocketStrategyIntegration(config)
    
    # Setup paper trading integration if engine provided
    if paper_trading_engine:
        paper_integration = WebSocketPaperTradingIntegration(paper_trading_engine, integration)
    
    return integration
