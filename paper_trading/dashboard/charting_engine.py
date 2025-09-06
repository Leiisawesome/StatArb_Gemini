#!/usr/bin/env python3
"""
Advanced Charting Engine
========================

Professional charting system with interactive charts and technical indicators.
Provides real-time price charts, performance visualizations, and technical analysis.

Author: Pro Quant Desk Trader
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ChartDataPoint:
    """Single chart data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
@dataclass
class TechnicalIndicator:
    """Technical indicator data"""
    name: str
    values: List[float]
    timestamps: List[datetime]
    parameters: Dict[str, Any] = field(default_factory=dict)

class TechnicalAnalysis:
    """Technical analysis calculations"""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> List[float]:
        """Simple Moving Average"""
        if len(prices) < period:
            return []
        
        sma_values = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma_values.append(avg)
        
        return sma_values
    
    @staticmethod
    def ema(prices: List[float], period: int) -> List[float]:
        """Exponential Moving Average"""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = []
        
        # Start with SMA for first value
        sma_first = sum(prices[:period]) / period
        ema_values.append(sma_first)
        
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
        """Bollinger Bands (Middle, Upper, Lower)"""
        if len(prices) < period:
            return [], [], []
        
        middle_band = TechnicalAnalysis.sma(prices, period)
        upper_band = []
        lower_band = []
        
        for i in range(period - 1, len(prices)):
            price_slice = prices[i - period + 1:i + 1]
            std = np.std(price_slice)
            middle = middle_band[i - period + 1]
            
            upper_band.append(middle + (std_dev * std))
            lower_band.append(middle - (std_dev * std))
        
        return middle_band, upper_band, lower_band
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[float]:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        rsi_values = []
        
        # Calculate initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
        
        # Calculate subsequent RSI values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """MACD (MACD Line, Signal Line, Histogram)"""
        if len(prices) < slow:
            return [], [], []
        
        ema_fast = TechnicalAnalysis.ema(prices, fast)
        ema_slow = TechnicalAnalysis.ema(prices, slow)
        
        # Align EMAs (slow EMA starts later)
        start_idx = slow - fast
        ema_fast_aligned = ema_fast[start_idx:]
        
        # Calculate MACD line
        macd_line = [fast_val - slow_val for fast_val, slow_val in zip(ema_fast_aligned, ema_slow)]
        
        # Calculate signal line (EMA of MACD)
        signal_line = TechnicalAnalysis.ema(macd_line, signal)
        
        # Calculate histogram (MACD - Signal)
        histogram_start = len(macd_line) - len(signal_line)
        macd_aligned = macd_line[histogram_start:]
        histogram = [macd_val - signal_val for macd_val, signal_val in zip(macd_aligned, signal_line)]
        
        return macd_line, signal_line, histogram

class ChartingEngine:
    """
    Advanced charting engine for trading dashboard
    
    Features:
    - Real-time price charts with OHLCV data
    - Technical indicators (SMA, EMA, Bollinger Bands, RSI, MACD)
    - Performance charts (P&L, drawdown, returns)
    - Strategy comparison charts
    - Interactive chart controls
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Chart data storage
        self.price_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.portfolio_data: deque = deque(maxlen=max_history)
        self.strategy_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # Technical indicators cache
        self.indicators_cache: Dict[str, Dict[str, TechnicalIndicator]] = defaultdict(dict)
        
        # Chart configurations
        self.chart_configs = {
            'price_chart': {
                'indicators': ['sma_20', 'sma_50', 'bollinger_bands'],
                'timeframes': ['1m', '5m', '15m', '1h', '1d']
            },
            'performance_chart': {
                'metrics': ['portfolio_value', 'total_pnl', 'drawdown'],
                'timeframes': ['1h', '1d', '1w']
            },
            'strategy_chart': {
                'metrics': ['individual_pnl', 'allocation', 'returns'],
                'comparison': True
            }
        }
        
        logger.info("📈 Advanced Charting Engine initialized")
    
    def update_price_data(self, symbol: str, price: float, volume: int = 0, timestamp: Optional[datetime] = None):
        """Update price data for charting"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # For simplicity, create OHLC from single price (in real system, would get actual OHLC)
        data_point = ChartDataPoint(
            timestamp=timestamp,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume
        )
        
        self.price_data[symbol].append(data_point)
        
        # Update technical indicators
        self._update_technical_indicators(symbol)
    
    def update_portfolio_data(self, portfolio_value: float, total_pnl: float, timestamp: Optional[datetime] = None):
        """Update portfolio data for performance charts"""
        if timestamp is None:
            timestamp = datetime.now()
        
        portfolio_point = {
            'timestamp': timestamp,
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'return_pct': ((portfolio_value / 100000.0) - 1) * 100  # Assuming 100k initial
        }
        
        self.portfolio_data.append(portfolio_point)
    
    def update_strategy_data(self, strategy_id: str, pnl: float, allocation: float, timestamp: Optional[datetime] = None):
        """Update strategy-specific data"""
        if timestamp is None:
            timestamp = datetime.now()
        
        strategy_point = {
            'timestamp': timestamp,
            'pnl': pnl,
            'allocation': allocation,
            'return_pct': (pnl / (100000.0 * allocation)) * 100 if allocation > 0 else 0
        }
        
        self.strategy_data[strategy_id].append(strategy_point)
    
    def _update_technical_indicators(self, symbol: str):
        """Update technical indicators for a symbol"""
        try:
            price_history = [point.close for point in self.price_data[symbol]]
            timestamps = [point.timestamp for point in self.price_data[symbol]]
            
            if len(price_history) < 20:  # Need minimum data for indicators
                return
            
            # Simple Moving Averages
            sma_20 = TechnicalAnalysis.sma(price_history, 20)
            sma_50 = TechnicalAnalysis.sma(price_history, 50)
            
            if sma_20:
                self.indicators_cache[symbol]['sma_20'] = TechnicalIndicator(
                    name='SMA 20',
                    values=sma_20,
                    timestamps=timestamps[-len(sma_20):],
                    parameters={'period': 20}
                )
            
            if sma_50:
                self.indicators_cache[symbol]['sma_50'] = TechnicalIndicator(
                    name='SMA 50',
                    values=sma_50,
                    timestamps=timestamps[-len(sma_50):],
                    parameters={'period': 50}
                )
            
            # Exponential Moving Averages
            ema_12 = TechnicalAnalysis.ema(price_history, 12)
            ema_26 = TechnicalAnalysis.ema(price_history, 26)
            
            if ema_12:
                self.indicators_cache[symbol]['ema_12'] = TechnicalIndicator(
                    name='EMA 12',
                    values=ema_12,
                    timestamps=timestamps[-len(ema_12):],
                    parameters={'period': 12}
                )
            
            # Bollinger Bands
            bb_middle, bb_upper, bb_lower = TechnicalAnalysis.bollinger_bands(price_history, 20, 2)
            if bb_middle:
                self.indicators_cache[symbol]['bollinger_bands'] = TechnicalIndicator(
                    name='Bollinger Bands',
                    values={'middle': bb_middle, 'upper': bb_upper, 'lower': bb_lower},
                    timestamps=timestamps[-len(bb_middle):],
                    parameters={'period': 20, 'std_dev': 2}
                )
            
            # RSI
            rsi_values = TechnicalAnalysis.rsi(price_history, 14)
            if rsi_values:
                self.indicators_cache[symbol]['rsi'] = TechnicalIndicator(
                    name='RSI',
                    values=rsi_values,
                    timestamps=timestamps[-len(rsi_values):],
                    parameters={'period': 14}
                )
            
            # MACD
            macd_line, signal_line, histogram = TechnicalAnalysis.macd(price_history, 12, 26, 9)
            if macd_line:
                self.indicators_cache[symbol]['macd'] = TechnicalIndicator(
                    name='MACD',
                    values={'macd': macd_line, 'signal': signal_line, 'histogram': histogram},
                    timestamps=timestamps[-len(macd_line):],
                    parameters={'fast': 12, 'slow': 26, 'signal': 9}
                )
            
        except Exception as e:
            logger.error(f"❌ Error updating technical indicators for {symbol}: {e}")
    
    def get_price_chart_data(self, symbol: str, timeframe: str = '1m', indicators: List[str] = None) -> Dict[str, Any]:
        """Get price chart data with technical indicators"""
        if symbol not in self.price_data:
            return {}
        
        if indicators is None:
            indicators = ['sma_20', 'sma_50']
        
        # Get price data
        price_points = list(self.price_data[symbol])
        
        chart_data = {
            'symbol': symbol,
            'timeframe': timeframe,
            'ohlcv': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'open': point.open,
                    'high': point.high,
                    'low': point.low,
                    'close': point.close,
                    'volume': point.volume
                }
                for point in price_points
            ],
            'indicators': {}
        }
        
        # Add technical indicators
        for indicator_name in indicators:
            if indicator_name in self.indicators_cache[symbol]:
                indicator = self.indicators_cache[symbol][indicator_name]
                
                if isinstance(indicator.values, dict):
                    # Multi-line indicator (like Bollinger Bands, MACD)
                    chart_data['indicators'][indicator_name] = {
                        'name': indicator.name,
                        'type': 'multi_line',
                        'data': {}
                    }
                    
                    for line_name, values in indicator.values.items():
                        chart_data['indicators'][indicator_name]['data'][line_name] = [
                            {
                                'timestamp': ts.isoformat(),
                                'value': val
                            }
                            for ts, val in zip(indicator.timestamps, values)
                        ]
                else:
                    # Single line indicator
                    chart_data['indicators'][indicator_name] = {
                        'name': indicator.name,
                        'type': 'line',
                        'data': [
                            {
                                'timestamp': ts.isoformat(),
                                'value': val
                            }
                            for ts, val in zip(indicator.timestamps, indicator.values)
                        ]
                    }
        
        return chart_data
    
    def get_performance_chart_data(self, timeframe: str = '1h') -> Dict[str, Any]:
        """Get portfolio performance chart data"""
        portfolio_points = list(self.portfolio_data)
        
        if not portfolio_points:
            return {}
        
        # Calculate drawdown
        peak_value = 100000.0  # Initial capital
        drawdown_data = []
        
        for point in portfolio_points:
            if point['portfolio_value'] > peak_value:
                peak_value = point['portfolio_value']
            
            drawdown = ((peak_value - point['portfolio_value']) / peak_value) * 100
            drawdown_data.append({
                'timestamp': point['timestamp'].isoformat(),
                'drawdown': drawdown
            })
        
        chart_data = {
            'timeframe': timeframe,
            'portfolio_value': [
                {
                    'timestamp': point['timestamp'].isoformat(),
                    'value': point['portfolio_value']
                }
                for point in portfolio_points
            ],
            'total_pnl': [
                {
                    'timestamp': point['timestamp'].isoformat(),
                    'value': point['total_pnl']
                }
                for point in portfolio_points
            ],
            'returns': [
                {
                    'timestamp': point['timestamp'].isoformat(),
                    'value': point['return_pct']
                }
                for point in portfolio_points
            ],
            'drawdown': drawdown_data
        }
        
        return chart_data
    
    def get_strategy_comparison_chart_data(self) -> Dict[str, Any]:
        """Get strategy comparison chart data"""
        chart_data = {
            'strategies': {}
        }
        
        for strategy_id, strategy_points in self.strategy_data.items():
            if not strategy_points:
                continue
            
            points_list = list(strategy_points)
            
            chart_data['strategies'][strategy_id] = {
                'pnl': [
                    {
                        'timestamp': point['timestamp'].isoformat(),
                        'value': point['pnl']
                    }
                    for point in points_list
                ],
                'returns': [
                    {
                        'timestamp': point['timestamp'].isoformat(),
                        'value': point['return_pct']
                    }
                    for point in points_list
                ],
                'allocation': [
                    {
                        'timestamp': point['timestamp'].isoformat(),
                        'value': point['allocation'] * 100  # Convert to percentage
                    }
                    for point in points_list
                ]
            }
        
        return chart_data
    
    def get_all_chart_data(self) -> Dict[str, Any]:
        """Get all chart data for dashboard"""
        try:
            all_data = {
                'timestamp': datetime.now().isoformat(),
                'price_charts': {},
                'performance_chart': self.get_performance_chart_data(),
                'strategy_comparison': self.get_strategy_comparison_chart_data(),
                'available_indicators': [
                    'sma_20', 'sma_50', 'ema_12', 'ema_26',
                    'bollinger_bands', 'rsi', 'macd'
                ],
                'available_timeframes': ['1m', '5m', '15m', '1h', '1d']
            }
            
            # Add price charts for all symbols
            for symbol in self.price_data.keys():
                all_data['price_charts'][symbol] = self.get_price_chart_data(
                    symbol, 
                    indicators=['sma_20', 'bollinger_bands', 'rsi']
                )
            
            return all_data
            
        except Exception as e:
            logger.error(f"❌ Error getting chart data: {e}")
            return {}
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Get chart configuration for frontend"""
        return {
            'chart_types': {
                'price': {
                    'name': 'Price Chart',
                    'description': 'OHLCV price data with technical indicators',
                    'indicators': [
                        {'name': 'SMA 20', 'key': 'sma_20', 'type': 'overlay'},
                        {'name': 'SMA 50', 'key': 'sma_50', 'type': 'overlay'},
                        {'name': 'EMA 12', 'key': 'ema_12', 'type': 'overlay'},
                        {'name': 'Bollinger Bands', 'key': 'bollinger_bands', 'type': 'overlay'},
                        {'name': 'RSI', 'key': 'rsi', 'type': 'oscillator'},
                        {'name': 'MACD', 'key': 'macd', 'type': 'oscillator'}
                    ]
                },
                'performance': {
                    'name': 'Performance Chart',
                    'description': 'Portfolio performance metrics over time',
                    'metrics': ['portfolio_value', 'total_pnl', 'returns', 'drawdown']
                },
                'strategy_comparison': {
                    'name': 'Strategy Comparison',
                    'description': 'Compare performance across strategies',
                    'metrics': ['pnl', 'returns', 'allocation']
                }
            },
            'timeframes': [
                {'name': '1 Minute', 'key': '1m'},
                {'name': '5 Minutes', 'key': '5m'},
                {'name': '15 Minutes', 'key': '15m'},
                {'name': '1 Hour', 'key': '1h'},
                {'name': '1 Day', 'key': '1d'}
            ],
            'colors': {
                'bullish': '#4CAF50',
                'bearish': '#f44336',
                'neutral': '#2196F3',
                'indicators': {
                    'sma_20': '#FF9800',
                    'sma_50': '#9C27B0',
                    'bollinger_upper': '#E91E63',
                    'bollinger_middle': '#607D8B',
                    'bollinger_lower': '#E91E63',
                    'rsi': '#00BCD4',
                    'macd': '#795548'
                }
            }
        }

# Integration helper functions
def create_charting_engine(trading_engine) -> ChartingEngine:
    """Create and configure charting engine for trading system"""
    charting = ChartingEngine()
    
    # Initialize with current data if available
    if hasattr(trading_engine, 'prices'):
        for symbol, price in trading_engine.prices.items():
            charting.update_price_data(symbol, price)
    
    if hasattr(trading_engine, 'portfolio_value'):
        total_pnl = trading_engine.portfolio_value - getattr(trading_engine, 'initial_capital', 100000)
        charting.update_portfolio_data(trading_engine.portfolio_value, total_pnl)
    
    return charting
