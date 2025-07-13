"""
Real-Time Market Data Feeds for Statistical Arbitrage
====================================================

Professional-grade market data integration supporting:
- Level 1 & Level 2 market data
- Real-time bid-ask spreads
- Order book depth analysis
- Tick-by-tick data processing
- Market maker identification
- Liquidity analysis

Author: Pro Quant Desk Trader
"""

import asyncio
import aiohttp
import websockets
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import time
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

@dataclass
class MarketDataTick:
    """Single market data tick with microstructure information"""
    symbol: str
    timestamp: datetime
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    last_price: float
    last_size: int
    volume: int
    spread_bps: float
    mid_price: float
    
    def __post_init__(self):
        self.mid_price = (self.bid_price + self.ask_price) / 2
        if self.mid_price > 0:
            self.spread_bps = ((self.ask_price - self.bid_price) / self.mid_price) * 10000

@dataclass
class OrderBookLevel:
    """Single order book level"""
    price: float
    size: int
    orders: int = 1

@dataclass
class OrderBookSnapshot:
    """Complete order book snapshot"""
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    
    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        return self.bids[0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        return self.asks[0] if self.asks else None
    
    @property
    def spread_bps(self) -> float:
        if self.best_bid and self.best_ask:
            mid = (self.best_bid.price + self.best_ask.price) / 2
            return ((self.best_ask.price - self.best_bid.price) / mid) * 10000
        return 0.0
    
    @property
    def bid_depth(self) -> float:
        """Total bid depth in dollars"""
        return sum(level.price * level.size for level in self.bids)
    
    @property
    def ask_depth(self) -> float:
        """Total ask depth in dollars"""
        return sum(level.price * level.size for level in self.asks)

@dataclass
class LiquidityMetrics:
    """Comprehensive liquidity metrics"""
    symbol: str
    timestamp: datetime
    
    # Spread metrics
    bid_ask_spread_bps: float
    effective_spread_bps: float
    quoted_spread_bps: float
    
    # Depth metrics
    bid_depth_dollars: float
    ask_depth_dollars: float
    total_depth_dollars: float
    depth_imbalance: float  # (bid_depth - ask_depth) / total_depth
    
    # Volume metrics
    volume_10s: int
    volume_1min: int
    volume_5min: int
    
    # Market impact estimates
    impact_100k: float  # Estimated impact for $100k trade
    impact_500k: float  # Estimated impact for $500k trade
    impact_1m: float    # Estimated impact for $1M trade
    
    # Timing metrics
    time_between_trades: float  # Seconds
    tick_frequency: float       # Ticks per second
    
    # Quality metrics
    liquidity_score: float      # 0-1 composite score
    execution_risk: float       # 0-1 risk score

class MarketDataFeed:
    """Base class for market data feeds"""
    
    def __init__(self, symbols: List[str], config: Dict[str, Any]):
        self.symbols = symbols
        self.config = config
        self.callbacks: List[Callable] = []
        self.is_running = False
        self.last_update = {}
        
    def add_callback(self, callback: Callable):
        """Add callback for market data updates"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start(self):
        """Start the market data feed"""
        self.is_running = True
        await self._connect()
    
    async def stop(self):
        """Stop the market data feed"""
        self.is_running = False
        await self._disconnect()
    
    async def _connect(self):
        """Connect to data source - implement in subclass"""
        raise NotImplementedError
    
    async def _disconnect(self):
        """Disconnect from data source - implement in subclass"""
        raise NotImplementedError
    
    def _notify_callbacks(self, data: Any):
        """Notify all callbacks of new data"""
        for callback in self.callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

class PolygonMarketDataFeed(MarketDataFeed):
    """Polygon.io real-time market data feed"""
    
    def __init__(self, symbols: List[str], config: Dict[str, Any]):
        super().__init__(symbols, config)
        self.api_key = config.get('polygon_api_key', '')
        self.websocket = None
        self.session = None
        
    async def _connect(self):
        """Connect to Polygon websocket"""
        try:
            self.session = aiohttp.ClientSession()
            
            # WebSocket connection
            ws_url = f"wss://socket.polygon.io/stocks"
            self.websocket = await websockets.connect(ws_url)
            
            # Authenticate
            auth_message = {
                "action": "auth",
                "params": self.api_key
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Subscribe to Level 1 quotes
            subscribe_message = {
                "action": "subscribe",
                "params": f"Q.{','.join(self.symbols)}"
            }
            await self.websocket.send(json.dumps(subscribe_message))
            
            # Subscribe to trades
            trade_message = {
                "action": "subscribe", 
                "params": f"T.{','.join(self.symbols)}"
            }
            await self.websocket.send(json.dumps(trade_message))
            
            logger.info(f"Connected to Polygon feed for {len(self.symbols)} symbols")
            
            # Start listening
            await self._listen()
            
        except Exception as e:
            logger.error(f"Failed to connect to Polygon: {e}")
            raise
    
    async def _listen(self):
        """Listen for market data messages"""
        try:
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                data = json.loads(message)
                await self._process_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Polygon connection closed")
        except Exception as e:
            logger.error(f"Error in Polygon listener: {e}")
    
    async def _process_message(self, data: List[Dict]):
        """Process incoming market data messages"""
        for item in data:
            msg_type = item.get('ev', '')
            
            if msg_type == 'Q':  # Quote update
                tick = self._parse_quote(item)
                if tick:
                    self._notify_callbacks(tick)
            
            elif msg_type == 'T':  # Trade update
                trade = self._parse_trade(item)
                if trade:
                    self._notify_callbacks(trade)
    
    def _parse_quote(self, data: Dict) -> Optional[MarketDataTick]:
        """Parse quote message into MarketDataTick"""
        try:
            return MarketDataTick(
                symbol=data['sym'],
                timestamp=datetime.fromtimestamp(data['t'] / 1000),
                bid_price=data['bp'],
                ask_price=data['ap'],
                bid_size=data['bs'],
                ask_size=data['as'],
                last_price=data.get('lp', 0),
                last_size=data.get('ls', 0),
                volume=0,
                spread_bps=0,  # Will be calculated in __post_init__
                mid_price=0    # Will be calculated in __post_init__
            )
        except KeyError as e:
            logger.error(f"Missing field in quote data: {e}")
            return None
    
    def _parse_trade(self, data: Dict) -> Optional[Dict]:
        """Parse trade message"""
        try:
            return {
                'type': 'trade',
                'symbol': data['sym'],
                'timestamp': datetime.fromtimestamp(data['t'] / 1000),
                'price': data['p'],
                'size': data['s'],
                'conditions': data.get('c', [])
            }
        except KeyError as e:
            logger.error(f"Missing field in trade data: {e}")
            return None
    
    async def _disconnect(self):
        """Disconnect from Polygon"""
        if self.websocket:
            await self.websocket.close()
        if self.session:
            await self.session.close()

class AlphaVantageMarketDataFeed(MarketDataFeed):
    """Alpha Vantage backup market data feed"""
    
    def __init__(self, symbols: List[str], config: Dict[str, Any]):
        super().__init__(symbols, config)
        self.api_key = config.get('alpha_vantage_api_key', '')
        self.session = None
        self.update_interval = config.get('update_interval', 5)  # seconds
        
    async def _connect(self):
        """Connect to Alpha Vantage API"""
        self.session = aiohttp.ClientSession()
        logger.info(f"Connected to Alpha Vantage feed for {len(self.symbols)} symbols")
        
        # Start polling
        await self._poll_data()
    
    async def _poll_data(self):
        """Poll Alpha Vantage for market data"""
        while self.is_running:
            try:
                tasks = [self._get_quote(symbol) for symbol in self.symbols]
                quotes = await asyncio.gather(*tasks, return_exceptions=True)
                
                for quote in quotes:
                    if isinstance(quote, MarketDataTick):
                        self._notify_callbacks(quote)
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error polling Alpha Vantage: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _get_quote(self, symbol: str) -> Optional[MarketDataTick]:
        """Get quote for single symbol"""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                quote_data = data.get('Global Quote', {})
                if not quote_data:
                    return None
                
                price = float(quote_data.get('05. price', 0))
                
                # Alpha Vantage doesn't provide bid/ask, so we estimate
                spread_estimate = price * 0.0001  # 1bp spread estimate
                
                return MarketDataTick(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    bid_price=price - spread_estimate/2,
                    ask_price=price + spread_estimate/2,
                    bid_size=1000,  # Estimated
                    ask_size=1000,  # Estimated
                    last_price=price,
                    last_size=100,  # Estimated
                    volume=int(quote_data.get('06. volume', 0)),
                    spread_bps=0,
                    mid_price=0
                )
                
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    async def _disconnect(self):
        """Disconnect from Alpha Vantage"""
        if self.session:
            await self.session.close()

class MarketMicrostructureAnalyzer:
    """Analyzes market microstructure from real-time data"""
    
    def __init__(self, symbols: List[str], config: Dict[str, Any]):
        self.symbols = symbols
        self.config = config
        self.tick_buffer = {symbol: [] for symbol in symbols}
        self.order_book_buffer = {symbol: [] for symbol in symbols}
        self.liquidity_cache = {}
        self.max_buffer_size = config.get('max_buffer_size', 10000)
        
    def process_tick(self, tick: MarketDataTick):
        """Process incoming market data tick"""
        symbol = tick.symbol
        
        # Add to buffer
        self.tick_buffer[symbol].append(tick)
        
        # Maintain buffer size
        if len(self.tick_buffer[symbol]) > self.max_buffer_size:
            self.tick_buffer[symbol] = self.tick_buffer[symbol][-self.max_buffer_size:]
        
        # Update liquidity metrics
        self._update_liquidity_metrics(symbol)
    
    def _update_liquidity_metrics(self, symbol: str):
        """Update liquidity metrics for symbol"""
        ticks = self.tick_buffer[symbol]
        if len(ticks) < 10:
            return
        
        recent_ticks = ticks[-100:]  # Last 100 ticks
        
        # Calculate spread metrics
        spreads = [tick.spread_bps for tick in recent_ticks if tick.spread_bps > 0]
        avg_spread = np.mean(spreads) if spreads else 0
        
        # Calculate depth metrics (simplified)
        recent_tick = recent_ticks[-1]
        bid_depth = recent_tick.bid_price * recent_tick.bid_size
        ask_depth = recent_tick.ask_price * recent_tick.ask_size
        total_depth = bid_depth + ask_depth
        
        # Calculate volume metrics
        now = datetime.now()
        volume_10s = sum(tick.volume for tick in recent_ticks 
                        if (now - tick.timestamp).total_seconds() <= 10)
        volume_1min = sum(tick.volume for tick in recent_ticks 
                         if (now - tick.timestamp).total_seconds() <= 60)
        volume_5min = sum(tick.volume for tick in recent_ticks 
                         if (now - tick.timestamp).total_seconds() <= 300)
        
        # Estimate market impact using square root law
        avg_volume_per_second = volume_1min / 60 if volume_1min > 0 else 1000
        
        def estimate_impact(trade_size_dollars: float) -> float:
            if avg_volume_per_second <= 0:
                return 0.01  # 1% default impact
            participation_rate = trade_size_dollars / (avg_volume_per_second * recent_tick.mid_price)
            return 0.001 * np.sqrt(participation_rate)  # Square root law
        
        # Calculate timing metrics
        if len(recent_ticks) >= 2:
            time_diffs = [(recent_ticks[i].timestamp - recent_ticks[i-1].timestamp).total_seconds() 
                         for i in range(1, len(recent_ticks))]
            avg_time_between_trades = np.mean(time_diffs) if time_diffs else 1.0
            tick_frequency = 1.0 / avg_time_between_trades if avg_time_between_trades > 0 else 1.0
        else:
            avg_time_between_trades = 1.0
            tick_frequency = 1.0
        
        # Calculate composite liquidity score
        liquidity_score = self._calculate_liquidity_score(
            avg_spread, total_depth, volume_1min, tick_frequency
        )
        
        # Create liquidity metrics
        metrics = LiquidityMetrics(
            symbol=symbol,
            timestamp=now,
            bid_ask_spread_bps=avg_spread,
            effective_spread_bps=avg_spread * 0.8,  # Estimated
            quoted_spread_bps=avg_spread,
            bid_depth_dollars=bid_depth,
            ask_depth_dollars=ask_depth,
            total_depth_dollars=total_depth,
            depth_imbalance=(bid_depth - ask_depth) / max(total_depth, 1),
            volume_10s=volume_10s,
            volume_1min=volume_1min,
            volume_5min=volume_5min,
            impact_100k=estimate_impact(100000),
            impact_500k=estimate_impact(500000),
            impact_1m=estimate_impact(1000000),
            time_between_trades=avg_time_between_trades,
            tick_frequency=tick_frequency,
            liquidity_score=liquidity_score,
            execution_risk=1.0 - liquidity_score
        )
        
        self.liquidity_cache[symbol] = metrics
    
    def _calculate_liquidity_score(self, spread: float, depth: float, 
                                  volume: int, tick_freq: float) -> float:
        """Calculate composite liquidity score (0-1, higher is better)"""
        score = 1.0
        
        # Penalize wide spreads
        if spread > 10:  # > 10 bps
            score *= 0.3
        elif spread > 5:  # > 5 bps
            score *= 0.6
        elif spread > 2:  # > 2 bps
            score *= 0.8
        
        # Penalize low depth
        if depth < 10000:  # < $10k depth
            score *= 0.4
        elif depth < 50000:  # < $50k depth
            score *= 0.7
        
        # Penalize low volume
        if volume < 1000:  # < 1000 shares per minute
            score *= 0.5
        elif volume < 5000:  # < 5000 shares per minute
            score *= 0.8
        
        # Penalize low tick frequency
        if tick_freq < 0.1:  # < 1 tick per 10 seconds
            score *= 0.6
        elif tick_freq < 0.5:  # < 1 tick per 2 seconds
            score *= 0.8
        
        return max(0.0, min(1.0, score))
    
    def get_liquidity_metrics(self, symbol: str) -> Optional[LiquidityMetrics]:
        """Get current liquidity metrics for symbol"""
        return self.liquidity_cache.get(symbol)
    
    def get_execution_cost_estimate(self, symbol: str, trade_size_dollars: float) -> Dict[str, float]:
        """Get execution cost estimate for trade"""
        metrics = self.get_liquidity_metrics(symbol)
        if not metrics:
            return {'total_cost_bps': 50.0, 'spread_cost_bps': 20.0, 'impact_cost_bps': 30.0}
        
        # Spread cost (half spread)
        spread_cost_bps = metrics.bid_ask_spread_bps / 2
        
        # Market impact cost
        if trade_size_dollars <= 100000:
            impact_cost_bps = metrics.impact_100k * 10000
        elif trade_size_dollars <= 500000:
            impact_cost_bps = metrics.impact_500k * 10000
        else:
            impact_cost_bps = metrics.impact_1m * 10000
        
        # Timing cost (based on execution risk)
        timing_cost_bps = metrics.execution_risk * 5.0
        
        total_cost_bps = spread_cost_bps + impact_cost_bps + timing_cost_bps
        
        return {
            'total_cost_bps': total_cost_bps,
            'spread_cost_bps': spread_cost_bps,
            'impact_cost_bps': impact_cost_bps,
            'timing_cost_bps': timing_cost_bps,
            'liquidity_score': metrics.liquidity_score,
            'execution_risk': metrics.execution_risk
        }

class MarketDataManager:
    """Manages multiple market data feeds with failover"""
    
    def __init__(self, symbols: List[str], config: Dict[str, Any]):
        self.symbols = symbols
        self.config = config
        self.feeds = []
        self.analyzer = MarketMicrostructureAnalyzer(symbols, config)
        self.is_running = False
        
        # Initialize feeds
        self._initialize_feeds()
    
    def _initialize_feeds(self):
        """Initialize market data feeds"""
        # Primary feed: Polygon
        if self.config.get('polygon_api_key'):
            polygon_feed = PolygonMarketDataFeed(self.symbols, self.config)
            polygon_feed.add_callback(self._on_market_data)
            self.feeds.append(polygon_feed)
        
        # Backup feed: Alpha Vantage
        if self.config.get('alpha_vantage_api_key'):
            av_feed = AlphaVantageMarketDataFeed(self.symbols, self.config)
            av_feed.add_callback(self._on_market_data)
            self.feeds.append(av_feed)
        
        logger.info(f"Initialized {len(self.feeds)} market data feeds")
    
    def _on_market_data(self, data: Any):
        """Handle incoming market data"""
        if isinstance(data, MarketDataTick):
            self.analyzer.process_tick(data)
        # Handle other data types as needed
    
    async def start(self):
        """Start all market data feeds"""
        self.is_running = True
        
        # Start feeds with failover
        for feed in self.feeds:
            try:
                await feed.start()
                logger.info(f"Started {feed.__class__.__name__}")
                break  # Use first successful feed
            except Exception as e:
                logger.error(f"Failed to start {feed.__class__.__name__}: {e}")
                continue
        
        if not any(feed.is_running for feed in self.feeds):
            raise RuntimeError("No market data feeds available")
    
    async def stop(self):
        """Stop all market data feeds"""
        self.is_running = False
        
        for feed in self.feeds:
            try:
                await feed.stop()
            except Exception as e:
                logger.error(f"Error stopping feed: {e}")
    
    def get_real_time_quote(self, symbol: str) -> Optional[MarketDataTick]:
        """Get latest real-time quote for symbol"""
        ticks = self.analyzer.tick_buffer.get(symbol, [])
        return ticks[-1] if ticks else None
    
    def get_liquidity_analysis(self, symbol: str) -> Optional[LiquidityMetrics]:
        """Get liquidity analysis for symbol"""
        return self.analyzer.get_liquidity_metrics(symbol)
    
    def get_execution_cost_estimate(self, symbol: str, trade_size: float) -> Dict[str, float]:
        """Get execution cost estimate"""
        return self.analyzer.get_execution_cost_estimate(symbol, trade_size)
    
    def get_market_quality_score(self, symbol1: str, symbol2: str) -> float:
        """Get market quality score for pair"""
        metrics1 = self.get_liquidity_analysis(symbol1)
        metrics2 = self.get_liquidity_analysis(symbol2)
        
        if not metrics1 or not metrics2:
            return 0.0
        
        # Combine liquidity scores
        combined_score = (metrics1.liquidity_score + metrics2.liquidity_score) / 2
        
        # Penalize asymmetric liquidity
        liquidity_asymmetry = abs(metrics1.liquidity_score - metrics2.liquidity_score)
        asymmetry_penalty = 1.0 - (liquidity_asymmetry * 0.5)
        
        return combined_score * asymmetry_penalty 