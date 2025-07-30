#!/usr/bin/env python3
"""
Real-Time Data Streaming Module
Phase 2: Core System Integration - Batch 1
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class RealTimeDataStream:
    """Real-time data streaming for live trading"""
    
    def __init__(self, symbols: List[str], api_key: str = None):
        self.symbols = symbols
        self.api_key = api_key
        self.is_running = False
        self.data_callbacks = []
        self.latest_data = {}
        self.data_history = {}
        self.stream_start_time = None
        
        # Initialize data structures
        for symbol in symbols:
            self.latest_data[symbol] = {}
            self.data_history[symbol] = []
        
        logger.info(f"Initialized RealTimeDataStream for {len(symbols)} symbols")
    
    def add_data_callback(self, callback: Callable):
        """Add callback function for data updates"""
        self.data_callbacks.append(callback)
        logger.info(f"Added data callback: {callback.__name__}")
    
    async def start_streaming(self):
        """Start real-time data streaming"""
        logger.info(f"Starting real-time data stream for {len(self.symbols)} symbols")
        self.is_running = True
        self.stream_start_time = datetime.now()
        
        try:
            while self.is_running:
                # Simulate real-time data updates
                await self._fetch_latest_data()
                await self._process_data_updates()
                await asyncio.sleep(15)  # 15-second intervals (simulating 15-min bars)
                
        except Exception as e:
            logger.error(f"Data streaming error: {e}")
            self.is_running = False
    
    async def stop_streaming(self):
        """Stop real-time data streaming"""
        logger.info("Stopping real-time data stream")
        self.is_running = False
    
    async def _fetch_latest_data(self):
        """Fetch latest market data (simulated for now)"""
        current_time = datetime.now()
        
        for symbol in self.symbols:
            # Simulate real-time price data
            base_price = self._get_base_price(symbol)
            price_change = np.random.normal(0, 0.002)  # 0.2% volatility
            new_price = base_price * (1 + price_change)
            
            # Create OHLCV data
            high = new_price * (1 + abs(np.random.normal(0, 0.001)))
            low = new_price * (1 - abs(np.random.normal(0, 0.001)))
            open_price = base_price
            close_price = new_price
            volume = int(np.random.uniform(1000, 10000))
            
            # Store latest data
            self.latest_data[symbol] = {
                'timestamp': current_time,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume,
                'symbol': symbol
            }
            
            # Add to history
            self.data_history[symbol].append(self.latest_data[symbol].copy())
            
            # Keep only last 1000 data points
            if len(self.data_history[symbol]) > 1000:
                self.data_history[symbol] = self.data_history[symbol][-1000:]
    
    async def _process_data_updates(self):
        """Process and notify data updates"""
        if not self.data_callbacks:
            return
        
        # Create DataFrame for latest data
        latest_df = {}
        for symbol in self.symbols:
            if self.latest_data[symbol]:
                df = pd.DataFrame([self.latest_data[symbol]])
                df.set_index('timestamp', inplace=True)
                latest_df[symbol] = df
        
        # Notify all callbacks
        for callback in self.data_callbacks:
            try:
                await callback(latest_df)
            except Exception as e:
                logger.error(f"Callback error in {callback.__name__}: {e}")
    
    def _get_base_price(self, symbol: str) -> float:
        """Get base price for symbol (simulated)"""
        base_prices = {
            'A': 150.0,  # AAPL
            'L': 60.0,   # Likely stock
            'M': 20.0,   # MSFT
            'S': 15.0,   # SPY
            'F': 12.0,   # Ford
            'T': 28.0,   # TSLA
            'G': 45.0,   # GOOGL
            'O': 65.0,   # Another stock
            'Z': 35.0,   # Another stock
        }
        return base_prices.get(symbol, 50.0)
    
    def get_latest_data(self, symbol: str = None) -> Dict:
        """Get latest data for symbol or all symbols"""
        if symbol:
            return self.latest_data.get(symbol, {})
        return self.latest_data
    
    def get_data_history(self, symbol: str, lookback_periods: int = 100) -> pd.DataFrame:
        """Get historical data for symbol"""
        if symbol not in self.data_history:
            return pd.DataFrame()
        
        history = self.data_history[symbol][-lookback_periods:]
        if not history:
            return pd.DataFrame()
        
        df = pd.DataFrame(history)
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_streaming_stats(self) -> Dict:
        """Get streaming statistics"""
        return {
            'is_running': self.is_running,
            'symbols_count': len(self.symbols),
            'stream_start_time': self.stream_start_time,
            'uptime_seconds': (datetime.now() - self.stream_start_time).total_seconds() if self.stream_start_time else 0,
            'total_data_points': sum(len(history) for history in self.data_history.values()),
            'callbacks_count': len(self.data_callbacks)
        }

class DataQualityMonitor:
    """Monitor data quality and integrity"""
    
    def __init__(self):
        self.quality_metrics = {}
        self.alert_callbacks = []
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback for data quality issues"""
        self.alert_callbacks.append(callback)
    
    def check_data_quality(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Check data quality for all symbols"""
        quality_report = {}
        
        for symbol, df in data.items():
            if df.empty:
                quality_report[symbol] = {
                    'status': 'ERROR',
                    'issues': ['Empty data']
                }
                continue
            
            issues = []
            
            # Check for missing values
            missing_values = df.isnull().sum().sum()
            if missing_values > 0:
                issues.append(f"Missing values: {missing_values}")
            
            # Check for price anomalies
            if 'close' in df.columns:
                price_changes = df['close'].pct_change().abs()
                if price_changes.max() > 0.1:  # 10% price change
                    issues.append("Large price change detected")
            
            # Check for volume anomalies
            if 'volume' in df.columns:
                if df['volume'].max() > 1000000:  # 1M volume
                    issues.append("Unusual volume detected")
            
            # Check data freshness
            if 'timestamp' in df.index:
                latest_time = df.index.max()
                time_diff = datetime.now() - latest_time
                if time_diff.total_seconds() > 300:  # 5 minutes
                    issues.append("Data may be stale")
            
            quality_report[symbol] = {
                'status': 'OK' if not issues else 'WARNING',
                'issues': issues,
                'data_points': len(df)
            }
        
        return quality_report
    
    async def notify_alerts(self, quality_report: Dict):
        """Notify alert callbacks of quality issues"""
        for symbol, report in quality_report.items():
            if report['status'] != 'OK':
                for callback in self.alert_callbacks:
                    try:
                        await callback(symbol, report)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

# Example usage and testing
async def example_data_callback(data: Dict[str, pd.DataFrame]):
    """Example callback function for data updates"""
    print(f"Received data update at {datetime.now()}")
    for symbol, df in data.items():
        if not df.empty:
            latest_price = df['close'].iloc[-1]
            print(f"  {symbol}: ${latest_price:.2f}")

async def example_alert_callback(symbol: str, report: Dict):
    """Example alert callback for data quality issues"""
    print(f"ALERT: {symbol} - {report['status']}: {report['issues']}")

if __name__ == "__main__":
    # Test the real-time data streaming
    symbols = ["A", "L", "M", "S", "F", "T", "G", "O", "Z"]
    
    # Create data stream
    data_stream = RealTimeDataStream(symbols)
    data_stream.add_data_callback(example_data_callback)
    
    # Create quality monitor
    quality_monitor = DataQualityMonitor()
    quality_monitor.add_alert_callback(example_alert_callback)
    
    # Start streaming
    print("Starting real-time data stream test...")
    asyncio.run(data_stream.start_streaming()) 