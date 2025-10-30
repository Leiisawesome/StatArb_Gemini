#!/usr/bin/env python3
"""
Real-Time Regime Detection Test
===============================

This script demonstrates regime detection at 1-minute frequency once the 60-minute
rolling window is ready. It shows how the regime engine processes data in real-time
as each new minute of data becomes available.

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import core engine components
from core_engine.config import RegimeConfig, DataConfig
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.data.manager import ClickHouseDataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealTimeRegimeDetector:
    """Real-time regime detection with 1-minute frequency updates"""
    
    def __init__(self, symbol: str = 'AAPL'):
        self.symbol = symbol
        self.regime_engine = None
        self.data_manager = None
        self.regime_history = []
        self.data_buffer = []
        self.current_regime = None
        self.regime_changes = []
        
    async def initialize(self):
        """Initialize the regime detection system"""
        logger.info("🚀 Initializing Real-Time Regime Detection System...")
        
        # Initialize data manager
        data_config = DataConfig()
        self.data_manager = ClickHouseDataManager(data_config)
        await self.data_manager.initialize()
        await self.data_manager.start()
        
        # Initialize regime engine
        regime_config = RegimeConfig()
        self.regime_engine = EnhancedRegimeEngine(regime_config)
        await self.regime_engine.initialize()
        await self.regime_engine.start()
        
        logger.info("✅ System initialized successfully")
    
    async def load_historical_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load historical data for the specified date range"""
        logger.info(f"📊 Loading historical data for {self.symbol} from {start_date} to {end_date}")
        
        try:
            # Get data from ClickHouse
            data = self.data_manager.get_market_data(
                self.symbol, 
                start_time=start_date, 
                end_time=end_date
            )
            
            if data is None or data.empty:
                logger.warning("No data available from ClickHouse, generating synthetic data")
                data = self._generate_synthetic_data(start_date, end_date)
            
            logger.info(f"✅ Loaded {len(data)} data points")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            logger.info("Generating synthetic data as fallback")
            return self._generate_synthetic_data(start_date, end_date)
    
    def _generate_synthetic_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate synthetic data for testing"""
        logger.info("🔧 Generating synthetic data for testing...")
        
        # Create 1-minute intervals for the trading day
        start_dt = datetime.strptime(f"{start_date} 09:30:00", "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(f"{end_date} 16:00:00", "%Y-%m-%d %H:%M:%S")
        
        # Generate 1-minute timestamps
        timestamps = pd.date_range(start=start_dt, end=end_dt, freq='1min')
        
        # Generate realistic price movements with different regimes
        base_price = 150.0
        prices = [base_price]
        
        # Simulate different market regimes throughout the day
        for i in range(1, len(timestamps)):
            # Morning: Bullish trend
            if i < 60:  # First hour
                trend = 0.001  # 0.1% upward trend per minute
                volatility = 0.005
            # Mid-morning: Range-bound
            elif i < 120:  # Second hour
                trend = 0.000  # No trend
                volatility = 0.003
            # Lunch: Choppy
            elif i < 180:  # Third hour
                trend = 0.000  # No trend
                volatility = 0.008
            # Afternoon: Bearish trend
            elif i < 240:  # Fourth hour
                trend = -0.0005  # 0.05% downward trend per minute
                volatility = 0.004
            # Late afternoon: Recovery
            else:  # Last hour
                trend = 0.0002  # Slight upward trend
                volatility = 0.003
            
            # Generate price movement
            change = np.random.normal(trend, volatility)
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Create OHLCV data
        data = []
        for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
            # Generate realistic OHLCV
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            open_price = prices[i-1] if i > 0 else price
            volume = np.random.randint(100000, 500000)
            
            data.append({
                'timestamp': timestamp,
                'symbol': self.symbol,
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    async def process_realtime_data(self, data: pd.DataFrame):
        """Process data in real-time, showing regime detection at 1-minute frequency"""
        logger.info("🔄 Starting real-time regime detection...")
        logger.info(f"Processing {len(data)} data points at 1-minute frequency")
        
        # Process data minute by minute
        for i, (_, row) in enumerate(data.iterrows()):
            # Convert row to dict for regime engine
            data_point = {
                'symbol': row['symbol'],
                'timestamp': row['timestamp'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
            
            # Process through regime engine
            result = self.regime_engine.process_market_data(data_point)
            
            # Display results
            self._display_regime_update(i + 1, data_point, result)
            
            # Track regime changes
            if result.get('regime_changed', False):
                self.regime_changes.append({
                    'minute': i + 1,
                    'timestamp': data_point['timestamp'],
                    'old_regime': self.current_regime,
                    'new_regime': result.get('regime_detected'),
                    'confidence': result.get('confidence', 0.0)
                })
                self.current_regime = result.get('regime_detected')
            
            # Store regime history
            if result.get('regime_detected'):
                self.regime_history.append({
                    'minute': i + 1,
                    'timestamp': data_point['timestamp'],
                    'regime': result.get('regime_detected'),
                    'confidence': result.get('confidence', 0.0),
                    'buffer_size': result.get('buffer_size', 0)
                })
            
            # Add small delay to simulate real-time processing
            await asyncio.sleep(0.01)  # 10ms delay for readability
    
    def _display_regime_update(self, minute: int, data_point: Dict, result: Dict):
        """Display regime update for current minute"""
        timestamp = data_point['timestamp'].strftime('%H:%M:%S')
        price = data_point['close']
        volume = data_point['volume']
        
        # Status indicators
        if result.get('regime_detected'):
            regime = result['regime_detected']
            confidence = result.get('confidence', 0.0)
            buffer_size = result.get('buffer_size', 0)
            
            # Color coding for regime types
            regime_colors = {
                'bull_low_volatility': '🟢',
                'bull_high_volatility': '🟡',
                'bear_low_volatility': '🔴',
                'bear_high_volatility': '🟠',
                'range_bound': '🔵',
                'choppy': '🟣'
            }
            
            color = regime_colors.get(regime, '⚪')
            
            if result.get('regime_changed', False):
                logger.info(f"🔄 MINUTE {minute:3d} [{timestamp}] {color} REGIME CHANGE: {regime.upper()} (conf: {confidence:.2f}) | Price: ${price:.2f} | Vol: {volume:,} | Buffer: {buffer_size}")
            else:
                logger.info(f"📊 MINUTE {minute:3d} [{timestamp}] {color} {regime.upper()} (conf: {confidence:.2f}) | Price: ${price:.2f} | Vol: {volume:,} | Buffer: {buffer_size}")
        else:
            buffer_size = result.get('buffer_size', 0)
            required = result.get('required_size', 60)
            logger.info(f"⏳ MINUTE {minute:3d} [{timestamp}] Building buffer... ({buffer_size}/{required}) | Price: ${price:.2f} | Vol: {volume:,}")
    
    def display_summary(self):
        """Display summary of regime detection results"""
        logger.info("\n" + "="*80)
        logger.info("📈 REGIME DETECTION SUMMARY")
        logger.info("="*80)
        
        # Regime changes
        if self.regime_changes:
            logger.info(f"\n🔄 REGIME CHANGES DETECTED: {len(self.regime_changes)}")
            for change in self.regime_changes:
                logger.info(f"   Minute {change['minute']:3d} [{change['timestamp'].strftime('%H:%M:%S')}]: {change['old_regime']} → {change['new_regime']} (conf: {change['confidence']:.2f})")
        else:
            logger.info("\n🔄 NO REGIME CHANGES DETECTED")
        
        # Regime distribution
        if self.regime_history:
            regime_counts = {}
            for entry in self.regime_history:
                regime = entry['regime']
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            logger.info(f"\n📊 REGIME DISTRIBUTION:")
            for regime, count in sorted(regime_counts.items()):
                percentage = (count / len(self.regime_history)) * 100
                logger.info(f"   {regime}: {count} minutes ({percentage:.1f}%)")
        
        # Current regime
        if self.current_regime:
            logger.info(f"\n🎯 CURRENT REGIME: {self.current_regime.upper()}")
        else:
            logger.info(f"\n🎯 CURRENT REGIME: Not detected yet")
        
        logger.info("="*80)
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up resources...")
        
        if self.data_manager:
            await self.data_manager.stop()
        
        if self.regime_engine:
            await self.regime_engine.stop()
        
        logger.info("✅ Cleanup complete")

async def main():
    """Main execution function"""
    logger.info("🚀 Starting Real-Time Regime Detection Test")
    
    # Initialize detector
    detector = RealTimeRegimeDetector('AAPL')
    
    try:
        # Initialize system
        await detector.initialize()
        
        # Load historical data for 2024-12-20
        data = await detector.load_historical_data('2024-12-20', '2024-12-20')
        
        # Process data in real-time
        await detector.process_realtime_data(data)
        
        # Display summary
        detector.display_summary()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup
        await detector.cleanup()
    
    logger.info("✅ Real-Time Regime Detection Test completed")

if __name__ == "__main__":
    asyncio.run(main())
