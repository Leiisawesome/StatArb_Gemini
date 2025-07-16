#!/usr/bin/env python3
"""
PHASE 3: LIVE TRADING INTEGRATION WITH REAL-TIME INDICATORS
===========================================================

This module integrates real-time technical indicators with live statistical arbitrage trading.

Features:
✅ Real-time WebSocket data streams from Polygon.io
✅ Live technical indicator calculation
✅ Real-time signal generation using Phase 2 enhancements
✅ Paper trading simulation with live data
✅ Risk management and position sizing
✅ Performance monitoring and alerts

Architecture:
1. WebSocket Manager - Real-time market data
2. Live Indicator Calculator - Real-time technical indicators
3. Enhanced Signal Generator - Using Phase 2 logic
4. Trading Engine - Execution and position management
5. Risk Manager - Real-time risk controls
6. Performance Monitor - Live performance tracking
"""

import os
import sys
import json
import time
import asyncio
import logging
import websockets
import ssl
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import numpy as np
import pandas as pd

# Import our Phase 2 components
from enhanced_backtesting_with_indicators import (
    TechnicalIndicatorDataLoader, 
    MarketRegimeClassifier,
    EnhancedSignalGenerator
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LiveMarketData:
    """Real-time market data point"""
    symbol: str
    price: float
    volume: int
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None

@dataclass
class LiveIndicators:
    """Real-time technical indicators"""
    symbol: str
    timestamp: datetime
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_20: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

@dataclass
class TradingSignal:
    """Enhanced trading signal with indicators"""
    symbol_pair: Tuple[str, str]
    signal_type: str  # 'LONG', 'SHORT', 'EXIT', 'HOLD'
    confidence: float
    timestamp: datetime
    spread_z_score: float
    indicators_score: float
    regime: str
    position_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class Position:
    """Live trading position"""
    symbol_pair: Tuple[str, str]
    position_type: str  # 'LONG', 'SHORT'
    entry_time: datetime
    entry_spread: float
    position_size: float
    current_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class LiveIndicatorCalculator:
    """Real-time technical indicator calculation"""
    
    def __init__(self, lookback_periods: int = 200):
        self.lookback_periods = lookback_periods
        self.price_history = defaultdict(lambda: deque(maxlen=lookback_periods))
        self.indicators_cache = {}
        
    def update_price(self, symbol: str, price: float, timestamp: datetime):
        """Update price history and calculate indicators"""
        self.price_history[symbol].append((price, timestamp))
        
        # Calculate indicators if we have enough data
        if len(self.price_history[symbol]) >= 50:  # Minimum for reliable indicators
            indicators = self._calculate_indicators(symbol)
            self.indicators_cache[symbol] = indicators
            return indicators
        
        return None
    
    def _calculate_indicators(self, symbol: str) -> LiveIndicators:
        """Calculate all technical indicators for a symbol"""
        prices = [p[0] for p in self.price_history[symbol]]
        timestamps = [p[1] for p in self.price_history[symbol]]
        
        if len(prices) < 50:
            return LiveIndicators(symbol=symbol, timestamp=timestamps[-1])
        
        # Convert to pandas for calculation
        df = pd.DataFrame({
            'close': prices,
            'timestamp': timestamps
        })
        
        indicators = LiveIndicators(
            symbol=symbol,
            timestamp=timestamps[-1]
        )
        
        try:
            # Simple Moving Averages
            if len(prices) >= 20:
                indicators.sma_20 = np.mean(prices[-20:])
            if len(prices) >= 50:
                indicators.sma_50 = np.mean(prices[-50:])
            
            # Exponential Moving Average
            if len(prices) >= 20:
                indicators.ema_20 = self._calculate_ema(prices, 20)
            
            # RSI
            if len(prices) >= 14:
                indicators.rsi_14 = self._calculate_rsi(prices, 14)
            
            # MACD
            if len(prices) >= 26:
                macd_data = self._calculate_macd(prices)
                indicators.macd_line = macd_data.get('macd')
                indicators.macd_signal = macd_data.get('signal')
                indicators.macd_histogram = macd_data.get('histogram')
                
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
        
        return indicators
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD"""
        if len(prices) < slow:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need historical MACD values
        # Simplified: use the current MACD as signal approximation
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

class WebSocketManager:
    """Manage real-time WebSocket connections to Polygon.io"""
    
    def __init__(self, api_key: str, symbols: List[str]):
        self.api_key = api_key
        self.symbols = symbols
        self.ws_url = f"wss://socket.polygon.io/stocks"
        self.callbacks = []
        self.running = False
        
    def add_callback(self, callback: Callable[[LiveMarketData], None]):
        """Add callback for real-time data"""
        self.callbacks.append(callback)
    
    async def start_streaming(self):
        """Start WebSocket streaming"""
        logger.info(f"🔌 Starting WebSocket for {len(self.symbols)} symbols")
        
        # Create SSL context that doesn't verify certificates (for development)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        try:
            async with websockets.connect(self.ws_url, ssl=ssl_context) as websocket:
                # Authenticate
                auth_msg = {"action": "auth", "params": self.api_key}
                await websocket.send(json.dumps(auth_msg))
                
                # Subscribe to symbols
                subscribe_msg = {
                    "action": "subscribe",
                    "params": f"A.{',A.'.join(self.symbols)}"  # Aggregate bars
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                logger.info("✅ WebSocket connected and subscribed")
                self.running = True
                
                # Listen for messages
                async for message in websocket:
                    if not self.running:
                        break
                        
                    try:
                        data = json.loads(message)
                        await self._process_message(data)
                    except Exception as e:
                        logger.error(f"Error processing WebSocket message: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.running = False
    
    async def _process_message(self, data: List[Dict]):
        """Process incoming WebSocket message"""
        for item in data:
            if item.get("ev") == "A":  # Aggregate bar
                market_data = LiveMarketData(
                    symbol=item.get("sym"),
                    price=item.get("c", 0),  # Close price
                    volume=item.get("v", 0),
                    timestamp=datetime.fromtimestamp(item.get("t", 0) / 1000)
                )
                
                # Call all callbacks
                for callback in self.callbacks:
                    try:
                        callback(market_data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
    
    def stop(self):
        """Stop WebSocket streaming"""
        self.running = False

class LiveTradingEngine:
    """Main live trading engine integrating all components"""
    
    def __init__(self, api_key: str, symbols: List[str], initial_capital: float = 1000000):
        self.api_key = api_key
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Initialize components
        self.indicator_calculator = LiveIndicatorCalculator()
        self.regime_classifier = MarketRegimeClassifier()
        self.websocket_manager = WebSocketManager(api_key, symbols)
        
        # Trading state
        self.positions = {}  # symbol_pair -> Position
        self.signals_history = deque(maxlen=1000)
        self.performance_history = deque(maxlen=10000)
        
        # Risk management
        self.max_position_size = 0.1  # 10% of capital per position
        self.max_drawdown = 0.2  # 20% maximum drawdown
        self.stop_loss_pct = 0.05  # 5% stop loss
        
        # Setup callbacks
        self.websocket_manager.add_callback(self._on_market_data)
        
        logger.info(f"🚀 Live Trading Engine initialized")
        logger.info(f"   📊 Symbols: {symbols}")
        logger.info(f"   💰 Capital: ${initial_capital:,.2f}")
    
    async def start_trading(self):
        """Start live trading"""
        logger.info("🚀 STARTING LIVE TRADING")
        logger.info("=" * 50)
        
        # Start performance monitoring
        monitor_task = asyncio.create_task(self._performance_monitor())
        
        # Start WebSocket streaming
        await self.websocket_manager.start_streaming()
    
    def _on_market_data(self, data: LiveMarketData):
        """Handle incoming market data"""
        try:
            # Update indicators
            indicators = self.indicator_calculator.update_price(
                data.symbol, data.price, data.timestamp
            )
            
            if indicators:
                # Generate signals for pairs containing this symbol
                self._generate_signals(data.symbol, data, indicators)
                
        except Exception as e:
            logger.error(f"Error processing market data for {data.symbol}: {e}")
    
    def _generate_signals(self, updated_symbol: str, market_data: LiveMarketData, indicators: LiveIndicators):
        """Generate trading signals when we have updated data"""
        
        # Find pairs containing this symbol
        for i, symbol1 in enumerate(self.symbols):
            for symbol2 in self.symbols[i+1:]:
                if updated_symbol in [symbol1, symbol2]:
                    pair = (symbol1, symbol2)
                    
                    # Check if we have indicators for both symbols
                    indicators1 = self.indicator_calculator.indicators_cache.get(symbol1)
                    indicators2 = self.indicator_calculator.indicators_cache.get(symbol2)
                    
                    if indicators1 and indicators2:
                        signal = self._evaluate_pair_signal(pair, indicators1, indicators2, market_data.timestamp)
                        
                        if signal and signal.signal_type != 'HOLD':
                            self._execute_signal(signal)
    
    def _evaluate_pair_signal(self, pair: Tuple[str, str], indicators1: LiveIndicators, 
                             indicators2: LiveIndicators, timestamp: datetime) -> Optional[TradingSignal]:
        """Evaluate trading signal for a symbol pair"""
        
        symbol1, symbol2 = pair
        
        # Get current prices
        prices1 = [p[0] for p in self.indicator_calculator.price_history[symbol1]]
        prices2 = [p[0] for p in self.indicator_calculator.price_history[symbol2]]
        
        if len(prices1) < 50 or len(prices2) < 50:
            return None
        
        # Calculate spread
        current_spread = prices1[-1] - prices2[-1]
        spread_history = [p1 - p2 for p1, p2 in zip(prices1[-50:], prices2[-50:])]
        spread_mean = np.mean(spread_history)
        spread_std = np.std(spread_history)
        
        if spread_std == 0:
            return None
        
        z_score = (current_spread - spread_mean) / spread_std
        
        # Enhanced signal logic from Phase 2
        signal_type = 'HOLD'
        confidence = 0.0
        
        # Basic mean reversion signals
        if z_score > 2.0:
            signal_type = 'SHORT'  # Spread too high, expect reversion
            confidence = min(abs(z_score) / 3.0, 1.0)
        elif z_score < -2.0:
            signal_type = 'LONG'   # Spread too low, expect reversion
            confidence = min(abs(z_score) / 3.0, 1.0)
        elif abs(z_score) < 0.5 and pair in self.positions:
            signal_type = 'EXIT'   # Near mean, exit position
            confidence = 0.8
        
        # Enhanced filtering using technical indicators
        indicators_score = self._calculate_indicators_score(indicators1, indicators2)
        
        # Regime classification
        regime = self._classify_pair_regime(indicators1, indicators2)
        
        # Adjust confidence based on indicators and regime
        if regime in ['overbought', 'oversold', 'uncertain']:
            confidence *= 0.5  # Reduce confidence in extreme regimes
        
        confidence *= indicators_score  # Scale by indicator quality
        
        # Position sizing
        position_size = self._calculate_position_size(confidence, z_score)
        
        if signal_type != 'HOLD' and confidence > 0.3:
            return TradingSignal(
                symbol_pair=pair,
                signal_type=signal_type,
                confidence=confidence,
                timestamp=timestamp,
                spread_z_score=z_score,
                indicators_score=indicators_score,
                regime=regime,
                position_size=position_size,
                stop_loss=self._calculate_stop_loss(z_score, signal_type),
                take_profit=self._calculate_take_profit(z_score, signal_type)
            )
        
        return None
    
    def _calculate_indicators_score(self, ind1: LiveIndicators, ind2: LiveIndicators) -> float:
        """Calculate indicator quality score"""
        score = 1.0
        
        try:
            # RSI confirmation
            if ind1.rsi_14 and ind2.rsi_14:
                # Prefer signals when RSI is not extreme
                rsi_avg = (ind1.rsi_14 + ind2.rsi_14) / 2
                if 30 <= rsi_avg <= 70:
                    score *= 1.2
                else:
                    score *= 0.8
            
            # MACD confirmation
            if ind1.macd_histogram and ind2.macd_histogram:
                # Check for momentum alignment
                if np.sign(ind1.macd_histogram) == np.sign(ind2.macd_histogram):
                    score *= 1.1
            
            # Trend confirmation
            if (ind1.sma_20 and ind1.sma_50 and ind2.sma_20 and ind2.sma_50):
                trend1 = 1 if ind1.sma_20 > ind1.sma_50 else -1
                trend2 = 1 if ind2.sma_20 > ind2.sma_50 else -1
                
                if trend1 == trend2:  # Same trend direction
                    score *= 1.1
                    
        except Exception as e:
            logger.error(f"Error calculating indicators score: {e}")
        
        return min(score, 2.0)  # Cap at 2x
    
    def _classify_pair_regime(self, ind1: LiveIndicators, ind2: LiveIndicators) -> str:
        """Classify market regime for the pair"""
        
        # Simple regime classification based on indicators
        try:
            if ind1.rsi_14 and ind2.rsi_14:
                avg_rsi = (ind1.rsi_14 + ind2.rsi_14) / 2
                
                if avg_rsi > 70:
                    return "overbought"
                elif avg_rsi < 30:
                    return "oversold"
                elif 40 <= avg_rsi <= 60:
                    return "ranging"
                else:
                    return "trending"
            
            return "uncertain"
            
        except:
            return "uncertain"
    
    def _calculate_position_size(self, confidence: float, z_score: float) -> float:
        """Calculate position size based on confidence and risk"""
        
        base_size = self.max_position_size * confidence
        
        # Scale by z-score strength
        z_score_multiplier = min(abs(z_score) / 3.0, 1.5)
        
        position_size = base_size * z_score_multiplier
        
        # Risk-adjusted sizing
        available_capital = self.current_capital * 0.8  # Keep 20% in reserve
        max_position_value = available_capital * self.max_position_size
        
        return min(position_size, max_position_value / self.current_capital)
    
    def _calculate_stop_loss(self, z_score: float, signal_type: str) -> float:
        """Calculate stop loss level"""
        # Stop loss at 1.5x the current z-score in opposite direction
        if signal_type == 'LONG':
            return z_score - 1.5
        elif signal_type == 'SHORT':
            return z_score + 1.5
        return None
    
    def _calculate_take_profit(self, z_score: float, signal_type: str) -> float:
        """Calculate take profit level"""
        # Take profit when spread returns to mean
        return 0.0  # Target mean reversion
    
    def _execute_signal(self, signal: TradingSignal):
        """Execute trading signal"""
        
        symbol1, symbol2 = signal.symbol_pair
        
        logger.info(f"🎯 SIGNAL: {signal.signal_type} {symbol1}/{symbol2}")
        logger.info(f"   📊 Z-Score: {signal.spread_z_score:.2f}")
        logger.info(f"   🎯 Confidence: {signal.confidence:.2f}")
        logger.info(f"   📈 Regime: {signal.regime}")
        logger.info(f"   💰 Position Size: {signal.position_size:.2%}")
        
        # Check if we already have a position
        if signal.symbol_pair in self.positions:
            if signal.signal_type == 'EXIT':
                self._close_position(signal.symbol_pair, signal.timestamp)
            else:
                logger.info(f"   ⚠️  Position already exists for {symbol1}/{symbol2}")
        else:
            if signal.signal_type in ['LONG', 'SHORT']:
                self._open_position(signal)
        
        # Store signal in history
        self.signals_history.append(signal)
    
    def _open_position(self, signal: TradingSignal):
        """Open new position"""
        
        symbol1, symbol2 = signal.symbol_pair
        
        # Get current prices
        price1 = self.indicator_calculator.price_history[symbol1][-1][0]
        price2 = self.indicator_calculator.price_history[symbol2][-1][0]
        current_spread = price1 - price2
        
        position = Position(
            symbol_pair=signal.symbol_pair,
            position_type=signal.signal_type,
            entry_time=signal.timestamp,
            entry_spread=current_spread,
            position_size=signal.position_size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        self.positions[signal.symbol_pair] = position
        
        logger.info(f"✅ OPENED {signal.signal_type} position: {symbol1}/{symbol2}")
        logger.info(f"   💰 Size: {signal.position_size:.2%} of capital")
        logger.info(f"   📊 Entry Spread: {current_spread:.4f}")
    
    def _close_position(self, symbol_pair: Tuple[str, str], timestamp: datetime):
        """Close existing position"""
        
        if symbol_pair not in self.positions:
            return
        
        position = self.positions[symbol_pair]
        symbol1, symbol2 = symbol_pair
        
        # Calculate PnL
        current_price1 = self.indicator_calculator.price_history[symbol1][-1][0]
        current_price2 = self.indicator_calculator.price_history[symbol2][-1][0]
        current_spread = current_price1 - current_price2
        
        spread_change = current_spread - position.entry_spread
        
        if position.position_type == 'LONG':
            pnl = spread_change * position.position_size * self.current_capital
        else:  # SHORT
            pnl = -spread_change * position.position_size * self.current_capital
        
        self.current_capital += pnl
        
        # Remove position
        del self.positions[symbol_pair]
        
        logger.info(f"❌ CLOSED {position.position_type} position: {symbol1}/{symbol2}")
        logger.info(f"   💰 PnL: ${pnl:,.2f}")
        logger.info(f"   📊 Capital: ${self.current_capital:,.2f}")
        
        # Record performance
        self.performance_history.append({
            'timestamp': timestamp,
            'symbol_pair': symbol_pair,
            'pnl': pnl,
            'capital': self.current_capital,
            'position_type': position.position_type,
            'holding_period': (timestamp - position.entry_time).total_seconds() / 3600  # hours
        })
    
    async def _performance_monitor(self):
        """Monitor performance and risk"""
        
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Update position PnLs
                total_unrealized = 0
                for symbol_pair, position in self.positions.items():
                    symbol1, symbol2 = symbol_pair
                    
                    if (symbol1 in self.indicator_calculator.price_history and 
                        symbol2 in self.indicator_calculator.price_history):
                        
                        current_price1 = self.indicator_calculator.price_history[symbol1][-1][0]
                        current_price2 = self.indicator_calculator.price_history[symbol2][-1][0]
                        current_spread = current_price1 - current_price2
                        
                        spread_change = current_spread - position.entry_spread
                        
                        if position.position_type == 'LONG':
                            unrealized_pnl = spread_change * position.position_size * self.current_capital
                        else:
                            unrealized_pnl = -spread_change * position.position_size * self.current_capital
                        
                        position.unrealized_pnl = unrealized_pnl
                        total_unrealized += unrealized_pnl
                
                # Performance summary
                total_capital = self.current_capital + total_unrealized
                total_return = (total_capital - self.initial_capital) / self.initial_capital
                
                logger.info(f"📊 PERFORMANCE UPDATE")
                logger.info(f"   💰 Capital: ${self.current_capital:,.2f}")
                logger.info(f"   📈 Unrealized: ${total_unrealized:,.2f}")
                logger.info(f"   🎯 Total: ${total_capital:,.2f}")
                logger.info(f"   📊 Return: {total_return:.2%}")
                logger.info(f"   🔄 Positions: {len(self.positions)}")
                
                # Risk checks
                if total_return < -self.max_drawdown:
                    logger.warning(f"⚠️  MAXIMUM DRAWDOWN EXCEEDED: {total_return:.2%}")
                
                # Check stop losses
                await self._check_stop_losses()
                
            except Exception as e:
                logger.error(f"Error in performance monitor: {e}")
    
    async def _check_stop_losses(self):
        """Check and execute stop losses"""
        
        positions_to_close = []
        
        for symbol_pair, position in self.positions.items():
            if position.stop_loss is None:
                continue
                
            symbol1, symbol2 = symbol_pair
            
            if (symbol1 in self.indicator_calculator.price_history and 
                symbol2 in self.indicator_calculator.price_history):
                
                current_price1 = self.indicator_calculator.price_history[symbol1][-1][0]
                current_price2 = self.indicator_calculator.price_history[symbol2][-1][0]
                current_spread = current_price1 - current_price2
                
                # Calculate current z-score
                prices1 = [p[0] for p in self.indicator_calculator.price_history[symbol1][-50:]]
                prices2 = [p[0] for p in self.indicator_calculator.price_history[symbol2][-50:]]
                spread_history = [p1 - p2 for p1, p2 in zip(prices1, prices2)]
                spread_mean = np.mean(spread_history)
                spread_std = np.std(spread_history)
                
                if spread_std > 0:
                    current_z_score = (current_spread - spread_mean) / spread_std
                    
                    # Check stop loss conditions
                    stop_triggered = False
                    
                    if position.position_type == 'LONG' and current_z_score <= position.stop_loss:
                        stop_triggered = True
                    elif position.position_type == 'SHORT' and current_z_score >= position.stop_loss:
                        stop_triggered = True
                    
                    if stop_triggered:
                        logger.warning(f"🛑 STOP LOSS TRIGGERED: {symbol1}/{symbol2}")
                        positions_to_close.append(symbol_pair)
        
        # Close positions that hit stop loss
        for symbol_pair in positions_to_close:
            self._close_position(symbol_pair, datetime.now())

    def get_status(self) -> Dict:
        """Get current trading status"""
        
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_capital = self.current_capital + total_unrealized
        total_return = (total_capital - self.initial_capital) / self.initial_capital
        
        return {
            'timestamp': datetime.now().isoformat(),
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'unrealized_pnl': total_unrealized,
            'total_capital': total_capital,
            'total_return': total_return,
            'num_positions': len(self.positions),
            'positions': [asdict(pos) for pos in self.positions.values()],
            'recent_signals': [asdict(signal) for signal in list(self.signals_history)[-10:]],
            'recent_performance': list(self.performance_history)[-10:]
        }


async def main():
    """Main function for live trading"""
    
    # Configuration
    API_KEY = os.getenv("POLYGON_API_KEY")
    if not API_KEY:
        logger.error("POLYGON_API_KEY environment variable required")
        return
    
    # Test with a small universe
    SYMBOLS = ["QQQ", "TQQQ", "SPY", "ARKK"]
    INITIAL_CAPITAL = 1000000  # $1M paper trading
    
    logger.info("🚀 PHASE 3: LIVE TRADING INTEGRATION")
    logger.info("=" * 50)
    logger.info(f"📊 Symbols: {SYMBOLS}")
    logger.info(f"💰 Capital: ${INITIAL_CAPITAL:,.2f}")
    logger.info("🔴 PAPER TRADING MODE - No real money at risk")
    
    # Initialize trading engine
    engine = LiveTradingEngine(API_KEY, SYMBOLS, INITIAL_CAPITAL)
    
    try:
        # Start live trading
        await engine.start_trading()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down live trading...")
        engine.websocket_manager.stop()
        
        # Final status
        status = engine.get_status()
        logger.info(f"📊 FINAL STATUS:")
        logger.info(f"   💰 Capital: ${status['current_capital']:,.2f}")
        logger.info(f"   📈 Return: {status['total_return']:.2%}")
        logger.info(f"   🔄 Positions: {status['num_positions']}")
        
        # Save results
        with open(f"live_trading_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(status, f, indent=2, default=str)
        
        logger.info("✅ Results saved")


if __name__ == "__main__":
    asyncio.run(main())
