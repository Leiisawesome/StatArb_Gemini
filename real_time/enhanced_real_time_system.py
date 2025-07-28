#!/usr/bin/env python3
"""
Enhanced Real-Time Trading System - Phase 3 Integration
Integrates Phase 1 academic foundations and Phase 2 backtesting components
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# Core structure imports
from core_structure.infrastructure.config.enhanced_config_manager import (
    EnhancedConfigManager, Environment
)
from core_structure.signal_generation.enhanced_signal_generator import (
    EnhancedSignalGenerator, AcademicSignalConfig
)
from core_structure.performance.benchmark_analyzer import (
    BenchmarkAnalyzer, BenchmarkConfig
)
from core_structure.market_data.data_manager import DataManager
from core_structure.signal_generation.signal_generator import SignalGenerator

# Backtesting framework imports
from backtesting_framework.strategies.enhanced_academic_strategy import EnhancedAcademicStrategy

logger = logging.getLogger(__name__)

class EnhancedRealTimeSystem:
    """Enhanced real-time trading system with academic foundations"""
    
    def __init__(self, config_path: str = None):
        self.config_manager = EnhancedConfigManager()
        self.config = None
        self.strategy = None
        self.data_manager = None
        self.signal_generator = None
        self.benchmark_analyzer = None
        
        # Real-time state
        self.is_running = False
        self.current_positions = {}
        self.portfolio_value = 0.0
        self.performance_metrics = {}
        self.signal_history = []
        self.trade_history = []
        
        # Academic components
        self.academic_signal_config = AcademicSignalConfig()
        self.benchmark_config = BenchmarkConfig()
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
        else:
            # Use default real-time configuration
            trading_start = datetime.now().strftime('%Y-%m-%d')
            self.config = self.config_manager.create_real_time_config("enhanced_momentum", trading_start)
    
    def load_config(self, config_path: str):
        """Load enhanced configuration for real-time trading"""
        try:
            self.config = self.config_manager.load_from_file(config_path)
            logger.info(f"Real-time configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Use default real-time configuration
            self.config = self.config_manager.create_real_time_config("enhanced_momentum")
    
    async def initialize(self):
        """Initialize the enhanced real-time system"""
        try:
            logger.info("Initializing Enhanced Real-Time Trading System...")
            
            # Initialize data manager
            self.data_manager = DataManager()
            await self.data_manager.initialize()
            logger.info("✅ Data manager initialized")
            
            # Initialize signal generator
            self.signal_generator = SignalGenerator()
            await self.signal_generator.initialize()
            logger.info("✅ Signal generator initialized")
            
            # Initialize benchmark analyzer
            self.benchmark_analyzer = BenchmarkAnalyzer(self.benchmark_config)
            logger.info("✅ Benchmark analyzer initialized")
            
            # Initialize enhanced academic strategy
            strategy_config = {
                'name': 'enhanced_academic_strategy',
                'version': '3.0.0',
                'symbols': self.config.strategy.symbols,
                'initial_capital': 100000.0,
                'position_size': 0.1,
                'max_positions': 10
            }
            self.strategy = EnhancedAcademicStrategy(strategy_config)
            logger.info("✅ Enhanced academic strategy initialized")
            
            # Initialize portfolio
            self.portfolio_value = strategy_config['initial_capital']
            logger.info(f"✅ Portfolio initialized with ${self.portfolio_value:,.2f}")
            
            logger.info("🎉 Enhanced Real-Time System initialization complete!")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            raise
    
    async def start_trading(self):
        """Start the enhanced real-time trading system"""
        if self.is_running:
            logger.warning("Trading system is already running")
            return
        
        try:
            logger.info("🚀 Starting Enhanced Real-Time Trading System...")
            self.is_running = True
            
            # Start data feeds
            await self._start_data_feeds()
            
            # Start signal generation loop
            await self._signal_generation_loop()
            
        except Exception as e:
            logger.error(f"Trading system failed: {e}")
            self.is_running = False
            raise
    
    async def stop_trading(self):
        """Stop the enhanced real-time trading system"""
        logger.info("🛑 Stopping Enhanced Real-Time Trading System...")
        self.is_running = False
        
        # Stop data feeds
        if self.data_manager:
            await self.data_manager.shutdown()
        
        # Stop signal generator
        if self.signal_generator:
            await self.signal_generator.shutdown()
        
        logger.info("✅ Trading system stopped")
    
    async def _start_data_feeds(self):
        """Start real-time data feeds"""
        try:
            # Start data feeds for all symbols including SPY
            symbols = self.config.strategy.symbols.copy()
            if 'SPY' not in symbols:
                symbols.append('SPY')
            
            await self.data_manager.start_real_time_feeds(symbols)
            logger.info(f"✅ Real-time data feeds started for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to start data feeds: {e}")
            raise
    
    async def _signal_generation_loop(self):
        """Main signal generation and trading loop"""
        logger.info("🔄 Starting signal generation loop...")
        
        while self.is_running:
            try:
                # Get current market data
                market_data = await self._get_current_market_data()
                
                if market_data and len(market_data) > 0:
                    # Generate academic signals
                    signals = await self._generate_academic_signals(market_data)
                    
                    # Execute trades based on signals
                    if signals:
                        await self._execute_trades(signals, market_data)
                    
                    # Update performance metrics
                    await self._update_performance_metrics()
                    
                    # Log current state
                    await self._log_trading_state()
                
                # Wait for next iteration
                await asyncio.sleep(1)  # 1-second intervals
                
            except Exception as e:
                logger.error(f"Signal generation loop error: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _get_current_market_data(self) -> Dict[str, pd.DataFrame]:
        """Get current market data for all symbols"""
        try:
            market_data = {}
            
            for symbol in self.config.strategy.symbols:
                # Get recent data for the symbol
                symbol_data = await self.data_manager.get_recent_data(symbol, lookback_days=30)
                
                if symbol_data is not None and len(symbol_data) > 0:
                    market_data[symbol] = symbol_data
            
            # Add SPY data for benchmark analysis
            spy_data = await self.data_manager.get_recent_data('SPY', lookback_days=30)
            if spy_data is not None and len(spy_data) > 0:
                market_data['SPY'] = spy_data
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return {}
    
    async def _generate_academic_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[Any]:
        """Generate academic momentum signals"""
        try:
            if not market_data or len(market_data) < 2:
                return []
            
            # Extract SPY data for benchmark
            spy_data = market_data.get('SPY')
            if spy_data is None:
                logger.warning("SPY data not available for benchmark analysis")
                return []
            
            # Generate academic signals using enhanced strategy
            signals = self.strategy.generate_signals(market_data)
            
            # Store signal history
            for signal in signals:
                self.signal_history.append({
                    'timestamp': signal.timestamp,
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type.value,
                    'confidence': signal.confidence,
                    'price': signal.price
                })
            
            logger.info(f"Generated {len(signals)} academic signals")
            return signals
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return []
    
    async def _execute_trades(self, signals: List[Any], market_data: Dict[str, pd.DataFrame]):
        """Execute trades based on academic signals"""
        try:
            for signal in signals:
                # Calculate position size
                position_size = self.strategy._calculate_position_size(signal.confidence, signal.symbol)
                
                if abs(position_size) > 0.01:  # Minimum position threshold
                    # Execute trade (simplified for now)
                    trade_result = await self._execute_single_trade(signal, position_size)
                    
                    if trade_result:
                        self.trade_history.append(trade_result)
                        logger.info(f"Executed trade: {signal.symbol} {signal.signal_type.value} "
                                  f"size={position_size:.4f}")
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
    
    async def _execute_single_trade(self, signal: Any, position_size: float) -> Dict[str, Any]:
        """Execute a single trade"""
        try:
            # Simplified trade execution
            trade = {
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type.value,
                'position_size': position_size,
                'price': signal.price,
                'confidence': signal.confidence
            }
            
            # Update portfolio (simplified)
            # In a real implementation, this would interact with a broker
            self._update_portfolio_position(signal.symbol, position_size, signal.price)
            
            return trade
            
        except Exception as e:
            logger.error(f"Single trade execution failed: {e}")
            return None
    
    def _update_portfolio_position(self, symbol: str, position_size: float, price: float):
        """Update portfolio position (simplified)"""
        try:
            # Update current positions
            if symbol not in self.current_positions:
                self.current_positions[symbol] = 0.0
            
            self.current_positions[symbol] += position_size
            
            # Update portfolio value (simplified calculation)
            position_value = position_size * price
            self.portfolio_value += position_value
            
        except Exception as e:
            logger.error(f"Portfolio update failed: {e}")
    
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            # Calculate basic performance metrics
            if len(self.trade_history) > 0:
                # Calculate returns (simplified)
                total_return = (self.portfolio_value - 100000.0) / 100000.0
                
                self.performance_metrics = {
                    'total_return': total_return,
                    'portfolio_value': self.portfolio_value,
                    'total_trades': len(self.trade_history),
                    'total_signals': len(self.signal_history),
                    'current_positions': len([p for p in self.current_positions.values() if abs(p) > 0.01])
                }
            
        except Exception as e:
            logger.error(f"Performance metrics update failed: {e}")
    
    async def _log_trading_state(self):
        """Log current trading state"""
        try:
            if len(self.performance_metrics) > 0:
                logger.info(f"Portfolio: ${self.performance_metrics.get('portfolio_value', 0):,.2f} "
                          f"| Trades: {self.performance_metrics.get('total_trades', 0)} "
                          f"| Signals: {self.performance_metrics.get('total_signals', 0)}")
            
        except Exception as e:
            logger.error(f"State logging failed: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'is_running': self.is_running,
            'portfolio_value': self.portfolio_value,
            'performance_metrics': self.performance_metrics,
            'current_positions': self.current_positions,
            'total_signals': len(self.signal_history),
            'total_trades': len(self.trade_history),
            'academic_foundations': {
                'multi_horizon_momentum': True,
                'volume_weighting': True,
                'regime_detection': True,
                'crash_protection': True,
                'macro_adjustments': True
            }
        }
    
    def save_trading_log(self, output_path: str):
        """Save trading log to file"""
        try:
            log_data = {
                'system_status': self.get_system_status(),
                'signal_history': self.signal_history,
                'trade_history': self.trade_history,
                'performance_metrics': self.performance_metrics
            }
            
            with open(output_path, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
            
            logger.info(f"Trading log saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save trading log: {e}") 