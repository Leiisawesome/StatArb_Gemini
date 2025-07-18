"""
Enhanced Data Processor
Advanced data processing with feature engineering and AI-ready streams
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, RobustScaler
import ta  # Technical analysis library

from .feeds import MarketTick, DataType
from ..infrastructure.messaging.message_bus import MessageBus
from ..infrastructure.monitoring.metrics_collector import MetricsCollector
from ..infrastructure.config.config_manager import ConfigManager


class ProcessingStage(Enum):
    """Data processing stages"""
    RAW = "raw"
    CLEANED = "cleaned"
    NORMALIZED = "normalized"
    FEATURED = "featured"
    AI_READY = "ai_ready"


@dataclass
class ProcessedData:
    """Processed market data with features"""
    symbol: str
    timestamp: datetime
    raw_data: Dict[str, Any]
    cleaned_data: Dict[str, Any]
    features: Dict[str, float]
    stage: ProcessingStage
    quality_score: float
    processing_latency_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'raw_data': self.raw_data,
            'cleaned_data': self.cleaned_data,
            'features': self.features,
            'stage': self.stage.value,
            'quality_score': self.quality_score,
            'processing_latency_ms': self.processing_latency_ms
        }


@dataclass
class MarketRegime:
    """Market regime information"""
    regime_id: int
    regime_name: str
    probability: float
    volatility_level: str  # low, medium, high
    trend_direction: str  # bullish, bearish, sideways
    confidence: float
    detected_at: datetime


class DataQualityChecker:
    """Checks and scores data quality"""
    
    def __init__(self):
        self.logger = logging.getLogger("data_processor.quality")
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[int]] = {}
        
    def check_tick_quality(self, tick: MarketTick) -> Tuple[bool, float, List[str]]:
        """
        Check tick data quality
        
        Returns:
            (is_valid, quality_score, issues)
        """
        issues = []
        quality_score = 1.0
        
        try:
            # Basic validation
            if tick.price <= 0:
                issues.append("invalid_price")
                quality_score *= 0.0
                
            if tick.volume < 0:
                issues.append("negative_volume")
                quality_score *= 0.5
                
            # Timestamp checks
            now = datetime.now()
            time_diff = abs((tick.timestamp - now).total_seconds())
            if time_diff > 300:  # 5 minutes
                issues.append("stale_timestamp")
                quality_score *= 0.7
                
            # Price sanity checks
            if tick.bid and tick.ask:
                if tick.bid >= tick.ask:
                    issues.append("crossed_spread")
                    quality_score *= 0.3
                    
                spread_pct = (tick.ask - tick.bid) / tick.price * 100
                if spread_pct > 5:  # 5% spread seems excessive
                    issues.append("wide_spread")
                    quality_score *= 0.8
                    
            # Historical price consistency
            symbol = tick.symbol
            if symbol in self.price_history:
                recent_prices = self.price_history[symbol][-10:]  # Last 10 prices
                if recent_prices:
                    avg_price = np.mean(recent_prices)
                    price_deviation = abs(tick.price - avg_price) / avg_price
                    
                    if price_deviation > 0.1:  # 10% deviation
                        issues.append("price_outlier")
                        quality_score *= 0.6
                        
            # Update history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
                self.volume_history[symbol] = []
                
            self.price_history[symbol].append(tick.price)
            self.volume_history[symbol].append(tick.volume)
            
            # Keep only recent history
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]
                self.volume_history[symbol] = self.volume_history[symbol][-100:]
                
            is_valid = quality_score > 0.3  # Minimum quality threshold
            
            return is_valid, quality_score, issues
            
        except Exception as e:
            self.logger.error(f"Quality check error for {tick.symbol}: {e}")
            return False, 0.0, ["processing_error"]


class FeatureEngine:
    """Advanced feature engineering for market data"""
    
    def __init__(self, window_sizes: Optional[List[int]] = None):
        self.logger = logging.getLogger("data_processor.features")
        self.window_sizes = window_sizes or [5, 10, 20, 50]
        self.price_buffers: Dict[str, pd.DataFrame] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        
    def process_tick_features(self, tick: MarketTick, historical_data: pd.DataFrame) -> Dict[str, float]:
        """
        Extract comprehensive features from tick data
        
        Args:
            tick: Current market tick
            historical_data: Historical price data
            
        Returns:
            Dictionary of feature values
        """
        features = {}
        
        try:
            # Basic price features
            features.update(self._extract_price_features(tick, historical_data))
            
            # Volume features
            features.update(self._extract_volume_features(tick, historical_data))
            
            # Spread and liquidity features
            features.update(self._extract_liquidity_features(tick))
            
            # Technical indicators
            features.update(self._extract_technical_features(historical_data))
            
            # Microstructure features
            features.update(self._extract_microstructure_features(tick, historical_data))
            
            # Regime features
            features.update(self._extract_regime_features(historical_data))
            
        except Exception as e:
            self.logger.error(f"Feature extraction error for {tick.symbol}: {e}")
            
        return features
    
    def _extract_price_features(self, tick: MarketTick, df: pd.DataFrame) -> Dict[str, float]:
        """Extract price-based features"""
        features = {}
        
        if len(df) < 2:
            return features
            
        try:
            current_price = tick.price
            
            # Price changes and returns
            for window in self.window_sizes:
                if len(df) >= window:
                    window_data = df.tail(window)
                    
                    # Returns
                    returns = window_data['close'].pct_change().dropna()
                    if len(returns) > 0:
                        features[f'return_mean_{window}'] = returns.mean()
                        features[f'return_std_{window}'] = returns.std()
                        features[f'return_skew_{window}'] = returns.skew()
                        features[f'return_kurt_{window}'] = returns.kurtosis()
                    
                    # Price momentum
                    start_price = window_data['close'].iloc[0]
                    features[f'momentum_{window}'] = (current_price - start_price) / start_price
                    
                    # Relative strength
                    max_price = window_data['high'].max()
                    min_price = window_data['low'].min()
                    if max_price > min_price:
                        features[f'rsi_{window}'] = (current_price - min_price) / (max_price - min_price)
                    
        except Exception as e:
            self.logger.error(f"Price feature extraction error: {e}")
            
        return features
    
    def _extract_volume_features(self, tick: MarketTick, df: pd.DataFrame) -> Dict[str, float]:
        """Extract volume-based features"""
        features = {}
        
        if len(df) < 2:
            return features
            
        try:
            current_volume = tick.volume
            
            for window in self.window_sizes:
                if len(df) >= window:
                    window_data = df.tail(window)
                    
                    # Volume statistics
                    avg_volume = window_data['volume'].mean()
                    if avg_volume > 0:
                        features[f'volume_ratio_{window}'] = current_volume / avg_volume
                    
                    features[f'volume_std_{window}'] = window_data['volume'].std()
                    
                    # Volume-price relationship
                    price_change = window_data['close'].pct_change()
                    volume_change = window_data['volume'].pct_change()
                    
                    correlation = price_change.corr(volume_change)
                    if not np.isnan(correlation):
                        features[f'price_volume_corr_{window}'] = correlation
                        
        except Exception as e:
            self.logger.error(f"Volume feature extraction error: {e}")
            
        return features
    
    def _extract_liquidity_features(self, tick: MarketTick) -> Dict[str, float]:
        """Extract liquidity and spread features"""
        features = {}
        
        try:
            if tick.bid and tick.ask and tick.bid_size and tick.ask_size:
                # Spread metrics
                spread = tick.ask - tick.bid
                mid_price = (tick.bid + tick.ask) / 2
                
                features['bid_ask_spread'] = spread
                features['spread_bps'] = (spread / mid_price) * 10000
                
                # Size imbalance
                total_size = tick.bid_size + tick.ask_size
                if total_size > 0:
                    features['size_imbalance'] = (tick.ask_size - tick.bid_size) / total_size
                
                # Liquidity metrics
                features['bid_size'] = tick.bid_size
                features['ask_size'] = tick.ask_size
                features['total_size'] = total_size
                
        except Exception as e:
            self.logger.error(f"Liquidity feature extraction error: {e}")
            
        return features
    
    def _extract_technical_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract technical analysis features"""
        features = {}
        
        if len(df) < 20:  # Minimum data for technical indicators
            return features
            
        try:
            # Moving averages
            for window in [5, 10, 20]:
                if len(df) >= window:
                    ma = df['close'].rolling(window).mean()
                    features[f'ma_{window}'] = ma.iloc[-1] if len(ma) > 0 else 0
                    
                    # Price relative to MA
                    current_price = df['close'].iloc[-1]
                    features[f'price_ma_ratio_{window}'] = current_price / ma.iloc[-1] if ma.iloc[-1] > 0 else 1
            
            # Volatility indicators
            returns = df['close'].pct_change().dropna()
            if len(returns) >= 10:
                features['volatility_10'] = returns.rolling(10).std().iloc[-1]
                features['volatility_20'] = returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else 0
            
            # RSI
            if len(df) >= 14:
                rsi = ta.momentum.RSIIndicator(df['close'], window=14)
                features['rsi_14'] = rsi.rsi().iloc[-1]
            
            # Bollinger Bands
            if len(df) >= 20:
                bb = ta.volatility.BollingerBands(df['close'], window=20)
                features['bb_upper'] = bb.bollinger_hband().iloc[-1]
                features['bb_lower'] = bb.bollinger_lband().iloc[-1]
                features['bb_width'] = features['bb_upper'] - features['bb_lower']
                features['bb_position'] = (df['close'].iloc[-1] - features['bb_lower']) / features['bb_width']
                
        except Exception as e:
            self.logger.error(f"Technical feature extraction error: {e}")
            
        return features
    
    def _extract_microstructure_features(self, tick: MarketTick, df: pd.DataFrame) -> Dict[str, float]:
        """Extract market microstructure features"""
        features = {}
        
        try:
            # Trade classification (Lee-Ready algorithm approximation)
            if tick.bid and tick.ask:
                mid_price = (tick.bid + tick.ask) / 2
                if tick.price > mid_price:
                    features['trade_direction'] = 1  # Buy
                elif tick.price < mid_price:
                    features['trade_direction'] = -1  # Sell
                else:
                    features['trade_direction'] = 0  # Unknown
            
            # Effective spread
            if tick.bid and tick.ask:
                features['effective_spread'] = 2 * abs(tick.price - (tick.bid + tick.ask) / 2)
            
            # Price impact approximation
            if len(df) >= 2:
                prev_price = df['close'].iloc[-2]
                features['price_impact'] = (tick.price - prev_price) / prev_price if prev_price > 0 else 0
                
        except Exception as e:
            self.logger.error(f"Microstructure feature extraction error: {e}")
            
        return features
    
    def _extract_regime_features(self, df: pd.DataFrame) -> Dict[str, float]:
        """Extract market regime features"""
        features = {}
        
        try:
            if len(df) >= 20:
                returns = df['close'].pct_change().dropna()
                
                # Regime indicators
                features['trend_strength'] = abs(returns.rolling(10).mean().iloc[-1]) if len(returns) >= 10 else 0
                features['volatility_regime'] = returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else 0
                
                # Mean reversion indicator
                if len(returns) >= 10:
                    features['mean_reversion'] = -returns.rolling(10).autocorr().iloc[-1] if len(returns) >= 10 else 0
                    
        except Exception as e:
            self.logger.error(f"Regime feature extraction error: {e}")
            
        return features


class DataProcessor:
    """Main data processing engine"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.logger = logging.getLogger("data_processor")
        self.message_bus = MessageBus()
        self.metrics = MetricsCollector()
        
        # Components
        self.quality_checker = DataQualityChecker()
        self.feature_engine = FeatureEngine()
        
        # Processing queues
        self.processing_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.output_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Data buffers
        self.data_buffers: Dict[str, pd.DataFrame] = {}
        self.buffer_size = config.get("data_processor.buffer_size", 1000)
        
        # Processing workers
        self.num_workers = config.get("data_processor.workers", 4)
        self.workers: List[asyncio.Task] = []
        
        # Performance tracking
        self.processing_stats = {
            'processed_count': 0,
            'failed_count': 0,
            'avg_latency_ms': 0.0,
            'quality_score_avg': 0.0
        }
        
    async def start(self) -> None:
        """Start the data processor"""
        try:
            self.logger.info("Starting data processor...")
            
            # Start processing workers
            for i in range(self.num_workers):
                worker = asyncio.create_task(self._processing_worker(f"worker_{i}"))
                self.workers.append(worker)
            
            # Start output publisher
            asyncio.create_task(self._output_publisher())
            
            self.logger.info(f"Data processor started with {self.num_workers} workers")
            
        except Exception as e:
            self.logger.error(f"Error starting data processor: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the data processor"""
        try:
            self.logger.info("Stopping data processor...")
            
            # Cancel workers
            for worker in self.workers:
                worker.cancel()
                
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
            
            self.logger.info("Data processor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping data processor: {e}")
    
    async def process_tick(self, tick: MarketTick) -> None:
        """
        Queue tick for processing
        
        Args:
            tick: Market tick to process
        """
        try:
            await self.processing_queue.put(tick)
            
        except asyncio.QueueFull:
            self.logger.warning(f"Processing queue full, dropping tick for {tick.symbol}")
            self.metrics.increment_counter("data_processor.queue_full")
    
    async def _processing_worker(self, worker_id: str) -> None:
        """Processing worker coroutine"""
        self.logger.info(f"Started processing worker: {worker_id}")
        
        while True:
            try:
                # Get tick from queue
                tick = await self.processing_queue.get()
                
                # Process tick
                processed_data = await self._process_single_tick(tick)
                
                if processed_data:
                    # Queue for output
                    await self.output_queue.put(processed_data)
                    
                    # Update stats
                    self.processing_stats['processed_count'] += 1
                    self.processing_stats['avg_latency_ms'] = (
                        self.processing_stats['avg_latency_ms'] * 0.9 +
                        processed_data.processing_latency_ms * 0.1
                    )
                    self.processing_stats['quality_score_avg'] = (
                        self.processing_stats['quality_score_avg'] * 0.9 +
                        processed_data.quality_score * 0.1
                    )
                else:
                    self.processing_stats['failed_count'] += 1
                
                # Mark task done
                self.processing_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                self.processing_stats['failed_count'] += 1
    
    async def _process_single_tick(self, tick: MarketTick) -> Optional[ProcessedData]:
        """Process a single tick through all stages"""
        start_time = time.time()
        
        try:
            # Stage 1: Quality check
            is_valid, quality_score, issues = self.quality_checker.check_tick_quality(tick)
            
            if not is_valid:
                self.logger.debug(f"Invalid tick for {tick.symbol}: {issues}")
                return None
            
            # Stage 2: Data cleaning and normalization
            cleaned_data = self._clean_tick_data(tick)
            
            # Stage 3: Update data buffer
            self._update_data_buffer(tick.symbol, tick)
            
            # Stage 4: Feature extraction
            historical_data = self.data_buffers.get(tick.symbol, pd.DataFrame())
            features = self.feature_engine.process_tick_features(tick, historical_data)
            
            # Calculate processing latency
            processing_latency_ms = (time.time() - start_time) * 1000
            
            # Create processed data
            processed_data = ProcessedData(
                symbol=tick.symbol,
                timestamp=tick.timestamp,
                raw_data=tick.to_dict(),
                cleaned_data=cleaned_data,
                features=features,
                stage=ProcessingStage.AI_READY,
                quality_score=quality_score,
                processing_latency_ms=processing_latency_ms
            )
            
            # Record metrics
            self.metrics.record_latency(
                "data_processor.processing_latency_ms",
                processing_latency_ms
            )
            self.metrics.set_gauge(
                f"data_processor.quality_score.{tick.symbol}",
                quality_score
            )
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing tick for {tick.symbol}: {e}")
            return None
    
    def _clean_tick_data(self, tick: MarketTick) -> Dict[str, Any]:
        """Clean and normalize tick data"""
        cleaned = {
            'symbol': tick.symbol,
            'timestamp': tick.timestamp.isoformat(),
            'price': tick.price,
            'volume': tick.volume,
            'data_type': tick.data_type.value
        }
        
        # Add optional fields if available
        if tick.bid is not None:
            cleaned['bid'] = tick.bid
        if tick.ask is not None:
            cleaned['ask'] = tick.ask
        if tick.bid_size is not None:
            cleaned['bid_size'] = tick.bid_size
        if tick.ask_size is not None:
            cleaned['ask_size'] = tick.ask_size
        if tick.exchange:
            cleaned['exchange'] = tick.exchange
            
        return cleaned
    
    def _update_data_buffer(self, symbol: str, tick: MarketTick) -> None:
        """Update data buffer for symbol"""
        try:
            if symbol not in self.data_buffers:
                self.data_buffers[symbol] = pd.DataFrame()
            
            # Create new row
            new_row = {
                'timestamp': tick.timestamp,
                'open': tick.price,  # For tick data, open = close
                'high': tick.price,
                'low': tick.price,
                'close': tick.price,
                'volume': tick.volume
            }
            
            # Add to buffer
            df = self.data_buffers[symbol]
            new_df = pd.DataFrame([new_row])
            df = pd.concat([df, new_df], ignore_index=True)
            
            # Keep only recent data
            if len(df) > self.buffer_size:
                df = df.tail(self.buffer_size)
            
            self.data_buffers[symbol] = df
            
        except Exception as e:
            self.logger.error(f"Error updating buffer for {symbol}: {e}")
    
    async def _output_publisher(self) -> None:
        """Publish processed data to message bus"""
        while True:
            try:
                # Get processed data
                processed_data = await self.output_queue.get()
                
                # Publish to message bus
                self.message_bus.publish(
                    message_type=f"processed_data.{processed_data.symbol}",
                    payload=processed_data.to_dict()
                )
                
                # Publish to AI stream
                self.message_bus.publish(
                    message_type="ai.processed_data_stream",
                    payload={
                        "type": "processed_market_data",
                        "data": processed_data.to_dict(),
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Mark task done
                self.output_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Output publisher error: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.processing_stats,
            'queue_size': self.processing_queue.qsize(),
            'output_queue_size': self.output_queue.qsize(),
            'active_symbols': len(self.data_buffers),
            'total_buffer_size': sum(len(df) for df in self.data_buffers.values())
        }
    
    def get_symbol_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Get recent data for symbol"""
        if symbol in self.data_buffers:
            return self.data_buffers[symbol].tail(limit).copy()
        return None 