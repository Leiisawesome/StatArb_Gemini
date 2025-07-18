"""
Polygon Streaming Engine - Real-time Indicator Calculation
==========================================================

Real-time streaming engine for calculating technical indicators
using Polygon WebSocket feeds. Preserves our battle-tested
SSL fixes and streaming architecture.

Author: Pro Trading System
"""

import asyncio
import json
import ssl
import logging
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from collections import deque, defaultdict

from technical_indicators import TechnicalIndicatorEngine, IndicatorResult, IndicatorConfig

class StreamingStatus(Enum):
    """Streaming connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    SUBSCRIBED = "subscribed"
    ERROR = "error"

@dataclass
class StreamingConfig:
    """Configuration for real-time streaming"""
    polygon_api_key: str
    websocket_url: str = "wss://socket.polygon.io/stocks"
    max_reconnect_attempts: int = 5
    reconnect_delay: int = 5
    heartbeat_interval: int = 30
    enable_ssl_verification: bool = False  # Our SSL fix
    buffer_size: int = 1000
    min_data_points: int = 50

@dataclass
class RealTimeIndicators:
    """Container for real-time indicator data"""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    indicators: Dict[str, float]
    regime: str
    confidence: float

class PolygonStreamingEngine:
    """
    Real-time streaming engine with technical indicators
    Includes our SSL fixes and production optimizations
    """
    
    def __init__(self, config: StreamingConfig):
        """Initialize streaming engine"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize indicator engine
        indicator_config = IndicatorConfig()
        indicator_config.polygon_api_key = config.polygon_api_key
        self.indicator_engine = TechnicalIndicatorEngine(indicator_config)
        
        # Connection management
        self.websocket = None
        self.status = StreamingStatus.DISCONNECTED
        self.subscribed_symbols = set()
        
        # Data management
        self.price_buffers = defaultdict(lambda: deque(maxlen=config.buffer_size))
        self.volume_buffers = defaultdict(lambda: deque(maxlen=config.buffer_size))
        self.timestamp_buffers = defaultdict(lambda: deque(maxlen=config.buffer_size))
        
        # Callbacks
        self.indicator_callbacks = []
        self.error_callbacks = []
        
        # SSL context (our fix)
        self.ssl_context = self._create_ssl_context()
        
        self.logger.info("Polygon Streaming Engine initialized")
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with our fixes"""
        ssl_context = ssl.create_default_context()
        
        if not self.config.enable_ssl_verification:
            # Our SSL fix for development/testing
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.logger.info("SSL verification disabled (development mode)")
        
        return ssl_context
    
    async def connect(self) -> bool:
        """Connect to Polygon WebSocket with SSL fixes"""
        try:
            self.status = StreamingStatus.CONNECTING
            self.logger.info("Connecting to Polygon WebSocket...")
            
            # Connect with SSL context
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                ssl=self.ssl_context,
                ping_interval=self.config.heartbeat_interval
            )
            
            self.status = StreamingStatus.CONNECTED
            self.logger.info("✅ WebSocket connected")
            
            # Authenticate
            auth_success = await self._authenticate()
            if auth_success:
                self.status = StreamingStatus.AUTHENTICATED
                self.logger.info("✅ WebSocket authenticated")
                return True
            else:
                await self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.status = StreamingStatus.ERROR
            return False
    
    async def _authenticate(self) -> bool:
        """Authenticate with Polygon API"""
        try:
            auth_message = {
                "action": "auth",
                "params": self.config.polygon_api_key
            }
            
            await self.websocket.send(json.dumps(auth_message))
            self.logger.info("Authentication message sent")
            
            # Wait for auth response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            auth_response = json.loads(response)
            
            if auth_response.get("status") == "auth_success":
                return True
            else:
                self.logger.error(f"Authentication failed: {auth_response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    async def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to real-time data for symbols"""
        try:
            if self.status != StreamingStatus.AUTHENTICATED:
                self.logger.error("Not authenticated, cannot subscribe")
                return False
            
            for symbol in symbols:
                # Subscribe to trades and quotes
                trade_sub = {
                    "action": "subscribe",
                    "params": f"T.{symbol}"
                }
                quote_sub = {
                    "action": "subscribe", 
                    "params": f"Q.{symbol}"
                }
                
                await self.websocket.send(json.dumps(trade_sub))
                await self.websocket.send(json.dumps(quote_sub))
                
                self.subscribed_symbols.add(symbol)
                self.logger.info(f"Subscribed to {symbol}")
            
            self.status = StreamingStatus.SUBSCRIBED
            return True
            
        except Exception as e:
            self.logger.error(f"Subscription error: {e}")
            return False
    
    async def start_streaming(self, symbols: List[str]) -> bool:
        """Start real-time streaming for symbols"""
        try:
            # Connect if not connected
            if self.status == StreamingStatus.DISCONNECTED:
                connected = await self.connect()
                if not connected:
                    return False
            
            # Subscribe to symbols
            subscribed = await self.subscribe_symbols(symbols)
            if not subscribed:
                return False
            
            # Start message processing
            asyncio.create_task(self._process_messages())
            
            self.logger.info(f"✅ Started streaming for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def _process_messages(self):
        """Process incoming WebSocket messages"""
        try:
            while self.websocket and not self.websocket.closed:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=30)
                    await self._handle_message(message)
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.websocket.ping()
                    
                except Exception as e:
                    self.logger.error(f"Message processing error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Message loop error: {e}")
            self.status = StreamingStatus.ERROR
            
            # Trigger error callbacks
            for callback in self.error_callbacks:
                try:
                    await callback(e)
                except Exception as cb_error:
                    self.logger.error(f"Error callback failed: {cb_error}")
    
    async def _handle_message(self, message: str):
        """Handle individual WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if isinstance(data, list):
                for item in data:
                    await self._process_market_data(item)
            elif isinstance(data, dict):
                await self._process_market_data(data)
                
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
    
    async def _process_market_data(self, data: Dict):
        """Process market data and calculate indicators"""
        try:
            msg_type = data.get("ev")
            
            if msg_type == "T":  # Trade data
                await self._process_trade(data)
            elif msg_type == "Q":  # Quote data
                await self._process_quote(data)
            elif msg_type == "status":
                self.logger.info(f"Status: {data}")
                
        except Exception as e:
            self.logger.error(f"Market data processing error: {e}")
    
    async def _process_trade(self, trade_data: Dict):
        """Process trade data and update indicators"""
        try:
            symbol = trade_data.get("sym", "")
            price = float(trade_data.get("p", 0))
            volume = int(trade_data.get("s", 0))
            timestamp = datetime.fromtimestamp(trade_data.get("t", 0) / 1000)
            
            if not symbol or price <= 0:
                return
            
            # Update buffers
            self.price_buffers[symbol].append(price)
            self.volume_buffers[symbol].append(volume)
            self.timestamp_buffers[symbol].append(timestamp)
            
            # Calculate indicators if we have enough data
            if len(self.price_buffers[symbol]) >= self.config.min_data_points:
                indicators = await self._calculate_real_time_indicators(symbol)
                
                if indicators:
                    # Trigger callbacks
                    for callback in self.indicator_callbacks:
                        try:
                            await callback(indicators)
                        except Exception as cb_error:
                            self.logger.error(f"Indicator callback failed: {cb_error}")
                            
        except Exception as e:
            self.logger.error(f"Trade processing error: {e}")
    
    async def _process_quote(self, quote_data: Dict):
        """Process quote data"""
        try:
            symbol = quote_data.get("sym", "")
            bid = float(quote_data.get("bp", 0))
            ask = float(quote_data.get("ap", 0))
            
            if symbol and bid > 0 and ask > 0:
                mid_price = (bid + ask) / 2
                
                # Use mid price for indicator calculation
                self.price_buffers[symbol].append(mid_price)
                self.timestamp_buffers[symbol].append(datetime.now())
                
        except Exception as e:
            self.logger.error(f"Quote processing error: {e}")
    
    async def _calculate_real_time_indicators(self, symbol: str) -> Optional[RealTimeIndicators]:
        """Calculate indicators for real-time data"""
        try:
            # Create DataFrame from buffers
            prices = list(self.price_buffers[symbol])
            volumes = list(self.volume_buffers[symbol])
            timestamps = list(self.timestamp_buffers[symbol])
            
            if len(prices) < self.config.min_data_points:
                return None
            
            # Create OHLCV data (simplified - using price as all OHLC)
            df_data = {
                'timestamp': timestamps,
                'open': prices,
                'high': prices,
                'low': prices,
                'close': prices,
                'volume': volumes if len(volumes) == len(prices) else [1] * len(prices)
            }
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            
            # Calculate indicators
            result = await self.indicator_engine.calculate_indicators_async(df, symbol)
            
            if result.indicators:
                return RealTimeIndicators(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=prices[-1],
                    volume=volumes[-1] if volumes else 0,
                    indicators=result.indicators,
                    regime=result.regime.value,
                    confidence=result.confidence
                )
                
        except Exception as e:
            self.logger.error(f"Real-time indicator calculation error: {e}")
            
        return None
    
    def add_indicator_callback(self, callback: Callable[[RealTimeIndicators], None]):
        """Add callback for indicator updates"""
        self.indicator_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception], None]):
        """Add callback for errors"""
        self.error_callbacks.append(callback)
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.status = StreamingStatus.DISCONNECTED
            self.subscribed_symbols.clear()
            self.logger.info("WebSocket disconnected")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
    
    def get_status(self) -> Dict:
        """Get current streaming status"""
        return {
            'status': self.status.value,
            'subscribed_symbols': list(self.subscribed_symbols),
            'buffer_sizes': {symbol: len(buffer) for symbol, buffer in self.price_buffers.items()},
            'ssl_verification': self.config.enable_ssl_verification
        }
    
    async def get_latest_indicators(self, symbol: str) -> Optional[RealTimeIndicators]:
        """Get latest indicators for symbol"""
        if symbol in self.price_buffers and len(self.price_buffers[symbol]) >= self.config.min_data_points:
            return await self._calculate_real_time_indicators(symbol)
        return None
