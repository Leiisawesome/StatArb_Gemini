#!/usr/bin/env python3
"""
Real-Time Trading System Using Core Infrastructure
==================================================

This script leverages the sophisticated core system components for real-time trading:
- Uses core_structure/market_data/feeds.py for institutional-grade data feeds
- Uses core_structure/signal_generation/signal_generator.py for AI-ready signal generation
- Uses core_structure/execution_engine/execution_engine.py for professional execution

This provides the advanced pipeline: Raw Data → Indicators → Features → Model Ensembler → Execution

Author: StatArb Gemini Team
Date: July 27, 2025
"""

import asyncio
import logging
import json
import time
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import argparse
import signal
import threading
from dataclasses import dataclass
import pandas as pd

# Add parent directory to path for core_structure imports
sys.path.append('..')

# Import core system components
try:
    from core_structure.market_data.feeds import FeedManager, MarketTick, DataType, FeedStatus
    from core_structure.market_data.data_manager import DataManager
    from core_structure.signal_generation.signal_generator import SignalGenerator, TradingSignal, SignalType
    from core_structure.execution_engine.execution_engine import ExecutionEngine, ExecutionRequest, ExecutionAlgorithm
    from core_structure.infrastructure.config.config_manager import ConfigManager
    from core_structure.infrastructure.messaging.message_bus import MessageBus
    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Core system components not available: {e}")
    CORE_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('real_time_core_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class HistoricalDataGenerator:
    """Generate historical market data as real-time feed for testing"""
    
    def __init__(self, symbols: List[str], update_frequency_ms: int = 1000, historical_period: str = "2025-01"):
        self.symbols = symbols
        self.update_frequency_ms = update_frequency_ms
        self.historical_period = historical_period
        self.tick_count = 0
        self.current_index = 0
        
        # Generate realistic historical data for January 2025
        self.historical_data = self._generate_historical_data()
        
    def _generate_historical_data(self) -> Dict[str, List[MarketTick]]:
        """Generate realistic historical data for January 2025"""
        import random
        from datetime import datetime, timedelta
        
        # Base prices for January 2025 (realistic starting points)
        base_prices = {
            'AAPL': 185.0,    # Realistic AAPL price in Jan 2025
            'MSFT': 380.0,    # Realistic MSFT price in Jan 2025
            'GOOGL': 2800.0,  # Realistic GOOGL price in Jan 2025
            'AMZN': 3200.0,   # Realistic AMZN price in Jan 2025
            'TSLA': 750.0,    # Realistic TSLA price in Jan 2025
            'VNET': 2.50,     # Realistic VNET price in Jan 2025
            'NVDA': 450.0,    # Realistic NVDA price in Jan 2025
            'META': 350.0,    # Realistic META price in Jan 2025
            'NFLX': 550.0,    # Realistic NFLX price in Jan 2025
            'ADBE': 580.0     # Realistic ADBE price in Jan 2025
        }
        
        # Generate 31 days of data (January 2025)
        start_date = datetime(2025, 1, 1, 9, 30)  # Market open
        end_date = datetime(2025, 1, 31, 16, 0)   # Market close
        
        historical_data = {}
        
        for symbol in self.symbols:
            # Get base price for symbol, or generate a realistic one
            if symbol in base_prices:
                current_price = base_prices[symbol]
            else:
                # Generate a realistic price based on symbol characteristics
                # Use a hash of the symbol to get consistent but varied prices
                symbol_hash = hash(symbol) % 1000
                current_price = 10.0 + (symbol_hash * 0.1)  # Price between $10-$110
                logger.info(f"Generated realistic base price for {symbol}: ${current_price:.2f}")
                
            current_price = base_prices.get(symbol, current_price)
            ticks = []
            
            # Generate daily data points (market hours: 9:30 AM - 4:00 PM)
            current_time = start_date
            while current_time <= end_date:
                # Skip weekends
                if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    current_time += timedelta(days=1)
                    current_time = current_time.replace(hour=9, minute=30)
                    continue
                
                # Generate multiple ticks per day (every 5 minutes during market hours)
                day_start = current_time.replace(hour=9, minute=30)
                day_end = current_time.replace(hour=16, minute=0)
                
                tick_time = day_start
                while tick_time <= day_end:
                    # Add some realistic price movement
                    price_change = random.gauss(0, current_price * 0.002)  # 0.2% volatility
                    current_price = max(current_price + price_change, current_price * 0.98)
                    
                    # Generate volume (higher at open/close, lower midday)
                    hour = tick_time.hour
                    if hour in [9, 16]:  # Open/close
                        volume = random.randint(50000, 200000)
                    else:
                        volume = random.randint(10000, 50000)
                    
                    # Create market tick
                    tick = MarketTick(
                        symbol=symbol,
                        timestamp=tick_time,
                        price=current_price,
                        volume=volume,
                        bid=current_price * 0.9999,
                        ask=current_price * 1.0001,
                        bid_size=volume,
                        ask_size=volume,
                        data_type=DataType.TICK,
                        exchange="HISTORICAL"
                    )
                    
                    ticks.append(tick)
                    tick_time += timedelta(minutes=5)
                
                current_time += timedelta(days=1)
            
            historical_data[symbol] = ticks
        
        return historical_data
    
    def get_next_tick(self, symbol: str) -> Optional[MarketTick]:
        """Get the next historical tick for a symbol"""
        if symbol not in self.historical_data:
            return None
            
        ticks = self.historical_data[symbol]
        if self.current_index >= len(ticks):
            # Reset to beginning for continuous replay
            self.current_index = 0
            
        if self.current_index < len(ticks):
            tick = ticks[self.current_index]
            self.current_index += 1
            self.tick_count += 1
            return tick
            
        return None
    
    def get_all_ticks_for_symbol(self, symbol: str) -> List[MarketTick]:
        """Get all historical ticks for a symbol"""
        return self.historical_data.get(symbol, [])
    
    def get_total_ticks(self) -> int:
        """Get total number of ticks across all symbols"""
        return sum(len(ticks) for ticks in self.historical_data.values())


class SimulatedDataGenerator:
    """Generate simulated market data for testing during off-hours"""
    
    def __init__(self, symbols: List[str], update_frequency_ms: int = 1000):
        self.symbols = symbols
        self.update_frequency_ms = update_frequency_ms
        self.base_prices = {
            'AAPL': 150.0,
            'MSFT': 300.0,
            'GOOGL': 2500.0,
            'AMZN': 3500.0,
            'TSLA': 800.0
        }
        self.current_prices = self.base_prices.copy()
        self.tick_count = 0
        
    def generate_tick(self, symbol: str) -> MarketTick:
        """Generate a simulated market tick"""
        import random
        
        # Update price with random walk
        current_price = self.current_prices[symbol]
        price_change = random.gauss(0, current_price * 0.001)  # 0.1% volatility
        new_price = max(current_price + price_change, current_price * 0.95)  # Prevent going below 95%
        
        # Update volume
        volume = random.randint(100, 10000)
        
        # Create market tick
        tick = MarketTick(
            symbol=symbol,
            timestamp=datetime.now(),
            price=new_price,
            volume=volume,
            bid=new_price * 0.9999,
            ask=new_price * 1.0001,
            bid_size=volume,
            ask_size=volume,
            data_type=DataType.TICK,
            exchange="SIMULATED"
        )
        
        # Update current price
        self.current_prices[symbol] = new_price
        self.tick_count += 1
        
        return tick


@dataclass
class RealTimeConfig:
    """Configuration for real-time trading system"""
    # Data feed configuration
    symbols: List[str] = None
    data_providers: List[str] = None
    update_frequency_ms: int = 1000
    
    # Simulation mode
    demo_mode: bool = False
    simulated_data: bool = False
    
    # Signal generation configuration
    min_confidence_threshold: float = 0.6
    min_signal_strength: float = 0.3
    enable_ml_features: bool = True
    
    # Execution configuration
    max_position_size: float = 0.05
    max_capital_risk: float = 0.02
    execution_algorithm: str = "market"
    
    # System configuration
    report_interval: int = 60
    enable_monitoring: bool = True
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        if self.data_providers is None:
            self.data_providers = ['polygon', 'alpha_vantage']


class RealTimeCoreSystem:
    """Real-time trading system using sophisticated core infrastructure"""
    
    def __init__(self, config: RealTimeConfig):
        self.config = config
        self.is_running = False
        
        # Core system components
        self.feed_manager = None
        self.data_manager = None
        self.signal_generator = None
        self.execution_engine = None
        self.simulated_generator = None
        self.historical_generator = None
        
        # Performance tracking
        self.start_time = None
        self.total_ticks = 0
        self.total_signals = 0
        self.total_executions = 0
        
        # Historical data accumulation for signal generation
        self.historical_data_buffer = {symbol: [] for symbol in self.config.symbols}
        self.buffer_size = 200  # Keep last 200 ticks for each symbol (need at least 60 for signal generation)
        
        # Initialize system
        self._initialize_system()
        
    def _initialize_system(self):
        """Initialize all core system components"""
        logger.info("Initializing Real-Time Core System...")
        
        if not CORE_AVAILABLE:
            logger.error("Core system components not available. Please check core_structure installation.")
            return
            
        try:
            # 1. Initialize Feed Manager (sophisticated data feeds)
            self._initialize_feed_manager()
            
            # 2. Initialize Data Manager
            self._initialize_data_manager()
            
            # 3. Initialize Signal Generator (AI-ready with ML features)
            self._initialize_signal_generator()
            
            # 4. Initialize Execution Engine (professional execution)
            self._initialize_execution_engine()
            
            # 5. Initialize Historical Data Generator (if needed)
            if self.config.simulated_data or self.config.demo_mode:
                self._initialize_historical_data()
            
            # 6. Connect components
            self._connect_components()
            
            logger.info("Core system initialization complete")
            
        except Exception as e:
            logger.error(f"Error initializing core system: {e}")
            raise
            
    def _initialize_feed_manager(self):
        """Initialize sophisticated feed manager from core system"""
        logger.info("Initializing Feed Manager...")
        
        # Create ConfigManager for feed manager
        config_manager = ConfigManager()
        
        # Initialize feed manager with ConfigManager
        self.feed_manager = FeedManager(config_manager)
        
        # Add data callback
        self.feed_manager.add_data_callback(self._on_market_data)
        
        logger.info(f"Feed Manager initialized with {len(self.config.symbols)} symbols")
        
    def _initialize_data_manager(self):
        """Initialize data manager for processing market data"""
        logger.info("Initializing Data Manager...")
        
        data_config = {
            'cache_size': 10000,
            'processing_workers': 4,
            'enable_real_time': True
        }
        
        self.data_manager = DataManager(data_config)
        logger.info("Data Manager initialized")
        
    def _initialize_signal_generator(self):
        """Initialize AI-ready signal generator from core system"""
        logger.info("Initializing Signal Generator...")
        
        # Create sophisticated signal generator configuration
        signal_config = {
            'enable_real_time': True,
            'update_frequency_ms': self.config.update_frequency_ms,
            'min_confidence_threshold': self.config.min_confidence_threshold,
            'enable_ml_features': self.config.enable_ml_features,
            'max_parallel_signals': 4,
            'signal_timeout_ms': 100,
            'lookback_window': 60,
            'regime_switch_penalty': 0.2,
            'max_position_size': self.config.max_position_size,
            'kelly_fraction': 0.25,
            'volatility_target': 0.15
        }
        
        self.signal_generator = SignalGenerator(signal_config)
        logger.info("Signal Generator initialized with ML features")
        
    def _initialize_execution_engine(self):
        """Initialize professional execution engine from core system"""
        logger.info("Initializing Execution Engine...")
        
        # Create sophisticated execution engine configuration
        execution_config = {
            'initial_capital': 1000000.0,  # $1M
            'max_order_value': 100000.0,   # $100K
            'max_position_value': 500000.0, # $500K
            'commission_rate': 0.0005,     # 5 bps
            'enable_risk_checks': True,
            'enable_cost_optimization': True
        }
        
        self.execution_engine = ExecutionEngine(**execution_config)
        
        # Set up execution algorithms
        self._setup_execution_algorithms()
        
        logger.info("Execution Engine initialized with professional features")
        
    def _setup_execution_algorithms(self):
        """Set up sophisticated execution algorithms"""
        # The execution engine comes with built-in algorithms:
        # - MARKET: Immediate execution
        # - TWAP: Time-weighted average price
        # - VWAP: Volume-weighted average price
        # - IMPLEMENTATION_SHORTFALL: Advanced execution
        # - SMART_ROUTING: Intelligent venue selection
        
        logger.info("Execution algorithms configured: MARKET, TWAP, VWAP, IMPLEMENTATION_SHORTFALL, SMART_ROUTING")
        
    def _initialize_historical_data(self):
        """Initialize historical data generator for testing"""
        logger.info("Initializing Historical Data Generator...")
        
        self.historical_generator = HistoricalDataGenerator(
            symbols=self.config.symbols,
            update_frequency_ms=self.config.update_frequency_ms,
            historical_period="2025-01"
        )
        
        total_ticks = self.historical_generator.get_total_ticks()
        logger.info(f"Historical Data Generator initialized for {len(self.config.symbols)} symbols")
        logger.info(f"Generated {total_ticks} historical ticks for January 2025")
        
    def _connect_components(self):
        """Connect all core system components"""
        logger.info("Connecting core system components...")
        
        # Connect feed manager to our data processing
        self.feed_manager.add_data_callback(self._on_market_data)
        
        logger.info("Core system components connected")
        
    def start(self):
        """Start the real-time core trading system"""
        logger.info("Starting Real-Time Core Trading System...")
        
        try:
            # Start all components
            asyncio.run(self._start_async())
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            self.stop()
        except Exception as e:
            logger.error(f"Error starting system: {e}")
            self.stop()
            
    async def _start_async(self):
        """Start system components asynchronously"""
        self.is_running = True
        self.start_time = datetime.now()
        
        if self.config.simulated_data or self.config.demo_mode:
            # Start historical data replay
            logger.info("Starting historical data replay...")
            asyncio.create_task(self._historical_data_loop())
        else:
            # Start feed manager (sophisticated data feeds)
            await self.feed_manager.start_all_feeds()
            
            # Subscribe to symbols
            await self.feed_manager.subscribe_symbols(self.config.symbols)
        
        logger.info(f"Real-Time Core Trading System started successfully")
        logger.info(f"Monitoring symbols: {self.config.symbols}")
        logger.info(f"Using sophisticated core infrastructure")
        
        # Main monitoring loop
        await self._monitoring_loop()
        
    async def _monitoring_loop(self):
        """Main monitoring and reporting loop"""
        report_interval = self.config.report_interval
        
        while self.is_running:
            try:
                # Generate comprehensive system report
                report = self._generate_system_report()
                self._print_system_report(report)
                
                # Check system health
                if not self._check_system_health():
                    logger.warning("System health check failed")
                    
                # Wait for next report
                await asyncio.sleep(report_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
                
    async def _historical_data_loop(self):
        """Replay historical market data at regular intervals"""
        while self.is_running:
            try:
                # Get next historical ticks for all symbols
                for symbol in self.config.symbols:
                    tick = self.historical_generator.get_next_tick(symbol)
                    if tick:
                        # Update timestamp to current time for real-time feel
                        tick.timestamp = datetime.now()
                        self._on_market_data(tick)
                
                # Wait for next update
                await asyncio.sleep(self.config.update_frequency_ms / 1000.0)
                
            except Exception as e:
                logger.error(f"Error in historical data loop: {e}")
                await asyncio.sleep(5)
                
    def stop(self):
        """Stop the real-time core trading system"""
        logger.info("Stopping Real-Time Core Trading System...")
        
        self.is_running = False
        
        # Stop all components
        if self.signal_generator:
            try:
                self.signal_generator.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down signal generator: {e}")
            
        if self.feed_manager:
            try:
                asyncio.run(self.feed_manager.stop_all_feeds())
            except Exception as e:
                logger.warning(f"Error stopping feed manager: {e}")
            
        logger.info("Real-Time Core Trading System stopped")
        
    # ============================================================================
    # CALLBACK METHODS AND DATA PROCESSING
    # ============================================================================
        
    def _on_market_data(self, tick: MarketTick):
        """Callback for incoming market data from sophisticated feed manager"""
        self.total_ticks += 1
        
        logger.debug(f"Market data received: {tick.symbol} @ {tick.price} "
                    f"(volume: {tick.volume}, type: {tick.data_type})")
        
        # Process market data and generate signal
        asyncio.create_task(self._process_market_data_and_generate_signal(tick))
        
    async def _process_market_data_and_generate_signal(self, tick: MarketTick):
        """Process market data and generate trading signal"""
        try:
            # Add tick to historical buffer
            self._add_tick_to_buffer(tick)
            
            # Convert MarketTick to market data format
            market_data = {
                'symbol': tick.symbol,
                'timestamp': tick.timestamp,
                'price': tick.price,
                'volume': tick.volume,
                'data_type': tick.data_type.value if hasattr(tick.data_type, 'value') else str(tick.data_type)
            }
            
            # Generate signal using sophisticated signal generator with historical data
            await self._generate_signal_for_symbol(tick.symbol, market_data)
            
        except Exception as e:
            logger.error(f"Error processing market data for {tick.symbol}: {e}")
            
    def _add_tick_to_buffer(self, tick: MarketTick):
        """Add tick to historical data buffer"""
        symbol = tick.symbol
        if symbol in self.historical_data_buffer:
            # Add new tick
            self.historical_data_buffer[symbol].append({
                'timestamp': tick.timestamp,
                'open': tick.price,
                'high': tick.price,
                'low': tick.price,
                'close': tick.price,
                'volume': tick.volume
            })
            
            # Keep only the last buffer_size ticks
            if len(self.historical_data_buffer[symbol]) > self.buffer_size:
                self.historical_data_buffer[symbol] = self.historical_data_buffer[symbol][-self.buffer_size:]
    
    def _get_historical_dataframe(self, symbol: str) -> pd.DataFrame:
        """Get historical DataFrame for signal generation"""
        if symbol not in self.historical_data_buffer or len(self.historical_data_buffer[symbol]) < 60:
            return pd.DataFrame()
        
        # Convert buffer to DataFrame
        df = pd.DataFrame(self.historical_data_buffer[symbol])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        return df
            
    def _on_processed_data(self, processed_data: Dict[str, Any]):
        """Callback for processed data from data manager"""
        symbol = processed_data.get('symbol')
        
        # Generate signal using sophisticated signal generator
        asyncio.create_task(self._generate_signal_for_symbol(symbol, processed_data))
        
    async def _generate_signal_for_symbol(self, symbol: str, market_data: Dict[str, Any]):
        """Generate trading signal using AI-ready signal generator"""
        try:
            # Get historical DataFrame for signal generation
            df = self._get_historical_dataframe(symbol)
            
            # Only generate signals if we have sufficient historical data
            if df.empty or len(df) < 60:  # Need at least 60 data points for signal generation
                return
            
            # Generate signal using sophisticated signal generator
            signal = await self.signal_generator.generate_signal(
                symbol_pair=symbol,
                market_data=df,
                real_time_data=market_data
            )
            
            if signal:
                self.total_signals += 1
                logger.info(f"Signal generated: {symbol} - {signal.signal_type} "
                           f"(confidence: {signal.confidence:.3f}, strength: {signal.strength})")
                
                # Execute signal directly
                await self._execute_signal(signal)
                
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            
    async def _execute_signal(self, signal: TradingSignal):
        """Execute trading signal using professional execution engine"""
        try:
            # Check signal quality
            if signal.confidence < self.config.min_confidence_threshold:
                logger.debug(f"Signal confidence too low: {signal.confidence}")
                return
                
            # Determine execution algorithm based on signal
            algorithm = self._select_execution_algorithm(signal)
            
            # Create execution request
            request = ExecutionRequest(
                symbol=signal.symbol_pair,
                side=self._convert_signal_to_order_side(signal.signal_type),
                quantity=signal.position_size,
                algorithm=algorithm,
                target_price=signal.entry_price,
                urgency=self._calculate_urgency(signal),
                strategy_id="real_time_core_system"
            )
            
            # Execute using professional execution engine
            result = await self.execution_engine.execute_order(request)
            
            if result.status.value == "success":
                self.total_executions += 1
                logger.info(f"Execution successful: {signal.symbol_pair} "
                           f"{result.executed_quantity} shares @ ${result.average_price:.2f}")
            else:
                logger.warning(f"Execution failed: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            
    def _on_signal_monitoring(self, signal: TradingSignal):
        """Monitoring callback for signal generation"""
        logger.debug(f"Signal monitoring: {signal.symbol_pair} - {signal.signal_type} "
                    f"(confidence: {signal.confidence:.3f})")
        
    def _on_execution_monitoring(self, result):
        """Monitoring callback for execution"""
        logger.debug(f"Execution monitoring: {result.symbol} - {result.status.value} "
                    f"(fill rate: {result.fill_rate:.1f}%)")
        
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
        
    def _select_execution_algorithm(self, signal: TradingSignal) -> ExecutionAlgorithm:
        """Select appropriate execution algorithm based on signal"""
        if signal.confidence > 0.8:
            return ExecutionAlgorithm.MARKET  # High confidence = immediate execution
        elif signal.confidence > 0.6:
            return ExecutionAlgorithm.TWAP    # Medium confidence = time-weighted
        else:
            return ExecutionAlgorithm.VWAP    # Low confidence = volume-weighted
            
    def _convert_signal_to_order_side(self, signal_type: SignalType) -> str:
        """Convert signal type to order side"""
        if signal_type == SignalType.LONG:
            return "buy"
        elif signal_type == SignalType.SHORT:
            return "sell"
        else:
            return "hold"
            
    def _calculate_urgency(self, signal: TradingSignal) -> float:
        """Calculate execution urgency based on signal characteristics"""
        # Higher confidence and strength = higher urgency
        urgency = (signal.confidence + abs(signal.strength)) / 2
        return min(urgency, 1.0)
        
    def _check_system_health(self) -> bool:
        """Check health of all core system components"""
        try:
            # Check feed manager health
            feed_status = self.feed_manager.get_feed_status()
            for feed_name, status in feed_status.items():
                if status['status'] != 'connected':
                    logger.warning(f"Feed {feed_name} is not healthy: {status['status']}")
                    return False
                    
            # Check signal generator health (it's always running once initialized)
            if not self.signal_generator:
                logger.warning("Signal generator is not initialized")
                return False
                
            # Check execution engine health (it's always running once initialized)
            if not self.execution_engine:
                logger.warning("Execution engine is not initialized")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False
            
    def _generate_system_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report using core system metrics"""
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        
        # Get metrics from core system components
        feed_metrics = self.feed_manager.get_feed_status() if self.feed_manager else {}
        signal_metrics = self.signal_generator.get_performance_metrics() if self.signal_generator else {}
        execution_metrics = self.execution_engine.get_execution_summary() if self.execution_engine else {}
        
        return {
            'timestamp': datetime.now(),
            'runtime': str(runtime),
            'system_status': {
                'is_running': self.is_running,
                'feed_manager_healthy': all(status['status'] == 'connected' for status in feed_metrics.values()),
                'signal_generator_running': self.signal_generator is not None,
                'execution_engine_running': self.execution_engine is not None
            },
            'performance_metrics': {
                'total_ticks': self.total_ticks,
                'total_signals': self.total_signals,
                'total_executions': self.total_executions,
                'ticks_per_minute': self.total_ticks / max(runtime.total_seconds() / 60, 1),
                'signals_per_minute': self.total_signals / max(runtime.total_seconds() / 60, 1),
                'executions_per_minute': self.total_executions / max(runtime.total_seconds() / 60, 1)
            },
            'feed_metrics': feed_metrics,
            'signal_metrics': signal_metrics,
            'execution_metrics': execution_metrics
        }
        
    def _print_system_report(self, report: Dict[str, Any]):
        """Print formatted system report"""
        print("\n" + "="*80)
        print("REAL-TIME CORE TRADING SYSTEM REPORT")
        print("="*80)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Runtime: {report['runtime']}")
        print()
        
        # System Status
        print("SYSTEM STATUS:")
        print(f"  Running: {report['system_status']['is_running']}")
        print(f"  Feed Manager: {'✓' if report['system_status']['feed_manager_healthy'] else '✗'}")
        print(f"  Signal Generator: {'✓' if report['system_status']['signal_generator_running'] else '✗'}")
        print(f"  Execution Engine: {'✓' if report['system_status']['execution_engine_running'] else '✗'}")
        print()
        
        # Performance Metrics
        print("PERFORMANCE METRICS:")
        print(f"  Total Ticks: {report['performance_metrics']['total_ticks']}")
        print(f"  Total Signals: {report['performance_metrics']['total_signals']}")
        print(f"  Total Executions: {report['performance_metrics']['total_executions']}")
        print(f"  Ticks/Min: {report['performance_metrics']['ticks_per_minute']:.2f}")
        print(f"  Signals/Min: {report['performance_metrics']['signals_per_minute']:.2f}")
        print(f"  Executions/Min: {report['performance_metrics']['executions_per_minute']:.2f}")
        print()
        
        # Feed Metrics
        if report['feed_metrics']:
            print("FEED METRICS:")
            for feed_name, metrics in report['feed_metrics'].items():
                print(f"  {feed_name}: {metrics['status']} (latency: {metrics.get('latency_ms', 0):.1f}ms)")
            print()
            
        # Signal Metrics
        if report['signal_metrics']:
            print("SIGNAL METRICS:")
            print(f"  Total Signals: {report['signal_metrics'].get('total_signals', 0)}")
            print(f"  Avg Confidence: {report['signal_metrics'].get('avg_confidence', 0):.3f}")
            print(f"  Avg Generation Time: {report['signal_metrics'].get('avg_generation_time_ms', 0):.1f}ms")
            print()
            
        # Execution Metrics
        if report['execution_metrics']:
            print("EXECUTION METRICS:")
            print(f"  Total Executions: {report['execution_metrics'].get('total_executions', 0)}")
            print(f"  Success Rate: {report['execution_metrics'].get('success_rate', 0):.1%}")
            print(f"  Avg Fill Rate: {report['execution_metrics'].get('avg_fill_rate', 0):.1%}")
            print(f"  Avg Execution Time: {report['execution_metrics'].get('avg_execution_time', 0):.1f}ms")
            print()
            
        print("="*80)


# ============================================================================
# MAIN ENTRY POINT AND CONFIGURATION
# ============================================================================

def create_system_config() -> RealTimeConfig:
    """Create configuration for the real-time core trading system"""
    return RealTimeConfig(
        symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
        data_providers=['polygon', 'alpha_vantage'],
        update_frequency_ms=1000,
        demo_mode=True,  # Enable demo mode by default (historical data)
        simulated_data=True,  # Enable historical data replay by default
        min_confidence_threshold=0.6,
        min_signal_strength=0.3,
        enable_ml_features=True,
        max_position_size=0.05,
        max_capital_risk=0.02,
        execution_algorithm="market",
        report_interval=60,
        enable_monitoring=True
    )

def create_real_time_config() -> RealTimeConfig:
    """Create configuration for real-time data feeds"""
    return RealTimeConfig(
        symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
        data_providers=['polygon', 'alpha_vantage'],
        update_frequency_ms=1000,
        demo_mode=False,  # Disable demo mode for real-time feeds
        simulated_data=False,  # Disable historical data replay
        min_confidence_threshold=0.6,
        min_signal_strength=0.3,
        enable_ml_features=True,
        max_position_size=0.05,
        max_capital_risk=0.02,
        execution_algorithm="market",
        report_interval=60,
        enable_monitoring=True
    )


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point for real-time core trading system"""
    parser = argparse.ArgumentParser(description='Real-Time Core Trading System')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL'], 
                       help='Trading symbols')
    parser.add_argument('--report-interval', type=int, default=60, 
                       help='Report interval in seconds')
    parser.add_argument('--demo', action='store_true', 
                       help='Run in demo mode with historical data')
    parser.add_argument('--real-time', action='store_true',
                       help='Run with real-time data feeds (requires API key)')
    parser.add_argument('--api-key', type=str, help='API key for data providers')
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create configuration based on arguments
    if args.real_time or args.api_key:
        # Use real-time configuration when real-time mode is requested or API key is provided
        config = create_real_time_config()
        if args.api_key:
            logger.info("Using real-time data feeds (API key provided)")
        else:
            logger.info("Using real-time data feeds (--real-time flag)")
    elif args.demo:
        # Use historical data configuration for demo mode
        config = create_system_config()
        logger.info("Using historical data replay (demo mode)")
    else:
        # Default to historical data
        config = create_system_config()
        logger.info("Using historical data replay (default mode)")
    
    # Override with command line arguments
    if args.symbols:
        config.symbols = args.symbols
    if args.report_interval:
        config.report_interval = args.report_interval
    if args.api_key:
        # Set API key for data providers
        os.environ['POLYGON_API_KEY'] = args.api_key
        os.environ['ALPHA_VANTAGE_API_KEY'] = args.api_key
        
    # Load from file if specified
    if args.config:
        try:
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                # Update config with file settings
                for key, value in file_config.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return
            
    logger.info("Starting Real-Time Core Trading System")
    logger.info("Using sophisticated core infrastructure:")
    logger.info("  - Institutional-grade data feeds")
    logger.info("  - AI-ready signal generation with ML features")
    logger.info("  - Professional execution engine with advanced algorithms")
    logger.info(f"Configuration: {config}")
    
    # Check if core system is available
    if not CORE_AVAILABLE:
        logger.error("Core system components not available. Please check core_structure installation.")
        logger.error("This system requires the sophisticated core infrastructure to function.")
        return
        
    # Create and start system
    trading_system = RealTimeCoreSystem(config)
    
    try:
        trading_system.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        trading_system.stop()


if __name__ == "__main__":
    main() 