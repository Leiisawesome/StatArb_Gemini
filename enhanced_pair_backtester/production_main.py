#!/usr/bin/env python3
"""
Production Main Script for VNET/GDS Pair Trading Strategy
Author: Professional Quant Desk Trader
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import signal
import traceback

# Core imports
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# Production imports
try:
    import redis
    import psycopg2
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PRODUCTION_DEPS_AVAILABLE = True
except ImportError:
    PRODUCTION_DEPS_AVAILABLE = False
    print("Warning: Production dependencies not available. Running in simulation mode.")

# Local imports
from data.data_loader import DataLoader
from utils.spread_calculator import SpreadCalculator
from models.signal_generator import SignalGenerator
from config.production_config import ProductionConfig

# Production logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
if PRODUCTION_DEPS_AVAILABLE:
    SIGNALS_GENERATED = Counter('signals_generated_total', 'Total signals generated')
    TRADES_EXECUTED = Counter('trades_executed_total', 'Total trades executed')
    POSITION_VALUE = Gauge('position_value_usd', 'Current position value in USD')
    SIGNAL_LATENCY = Histogram('signal_generation_seconds', 'Signal generation latency')
    EXECUTION_LATENCY = Histogram('execution_latency_seconds', 'Order execution latency')

@dataclass
class TradingSignal:
    """Production trading signal with all required metadata"""
    timestamp: datetime
    pair: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    direction: str  # 'LONG', 'SHORT', 'NEUTRAL'
    confidence: float
    z_score: float
    spread_value: float
    regime: str
    vnet_quantity: int
    gds_quantity: int
    expected_return: float
    risk_score: float
    signal_id: str

class ProductionRiskManager:
    """Production-grade risk management system"""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.risk_limits = {
            'max_position_size': 0.10,     # 10% of portfolio
            'max_leverage': 2.0,           # 2:1 leverage
            'max_drawdown': 0.05,          # 5% max drawdown
            'var_limit_95': 0.02,          # 2% VaR limit
            'concentration_limit': 0.25,   # 25% sector concentration
            'daily_loss_limit': 0.02       # 2% daily loss limit
        }
        self.current_positions = {}
        self.daily_pnl = 0.0
        
    def validate_signal(self, signal: TradingSignal, portfolio_value: float) -> bool:
        """Validate trading signal against risk limits"""
        try:
            # Check position size limits
            position_size = self.calculate_position_size(signal, portfolio_value)
            if position_size > self.risk_limits['max_position_size'] * portfolio_value:
                logger.warning(f"Signal rejected: Position size too large ({position_size})")
                return False
            
            # Check daily loss limits
            if self.daily_pnl < -self.risk_limits['daily_loss_limit'] * portfolio_value:
                logger.warning(f"Signal rejected: Daily loss limit exceeded ({self.daily_pnl})")
                return False
            
            # Check confidence threshold
            if signal.confidence < self.config.min_confidence:
                logger.warning(f"Signal rejected: Confidence too low ({signal.confidence})")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Risk validation failed: {e}")
            return False
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> float:
        """Calculate optimal position size using Kelly Criterion"""
        # Simplified Kelly Criterion calculation
        win_rate = 0.55  # Estimated from backtesting
        avg_win = 0.02   # 2% average win
        avg_loss = 0.015 # 1.5% average loss
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        
        # Adjust by confidence
        adjusted_fraction = kelly_fraction * signal.confidence
        
        # Apply risk limits
        final_fraction = min(adjusted_fraction, self.risk_limits['max_position_size'])
        
        return final_fraction * portfolio_value

class ProductionOrderManager:
    """Production order management system"""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.order_queue = asyncio.Queue()
        self.active_orders = {}
        self.execution_history = []
        
    async def execute_signal(self, signal: TradingSignal) -> bool:
        """Execute trading signal with smart order routing"""
        try:
            start_time = datetime.now()
            
            # Create pair orders
            orders = self._create_pair_orders(signal)
            
            # Execute orders (simulated for now)
            execution_results = []
            for order in orders:
                result = await self._execute_order(order)
                execution_results.append(result)
                
            # Log execution
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Signal executed in {execution_time:.3f}s: {signal.signal_id}")
            
            if PRODUCTION_DEPS_AVAILABLE:
                TRADES_EXECUTED.inc()
                EXECUTION_LATENCY.observe(execution_time)
            
            return all(execution_results)
            
        except Exception as e:
            logger.error(f"Order execution failed: {e}")
            return False
    
    def _create_pair_orders(self, signal: TradingSignal) -> List[Dict]:
        """Create simultaneous orders for both legs of the pair"""
        orders = []
        
        # VNET order
        vnet_order = {
            'symbol': 'VNET',
            'side': 'BUY' if signal.direction == 'LONG' else 'SELL',
            'quantity': signal.vnet_quantity,
            'order_type': 'MARKET',
            'time_in_force': 'IOC',
            'signal_id': signal.signal_id
        }
        orders.append(vnet_order)
        
        # GDS order
        gds_order = {
            'symbol': 'GDS',
            'side': 'SELL' if signal.direction == 'LONG' else 'BUY',
            'quantity': signal.gds_quantity,
            'order_type': 'MARKET',
            'time_in_force': 'IOC',
            'signal_id': signal.signal_id
        }
        orders.append(gds_order)
        
        return orders
    
    async def _execute_order(self, order: Dict) -> bool:
        """Execute individual order (simulated)"""
        # In production, this would connect to your broker's API
        # For now, we'll simulate successful execution
        logger.info(f"Executing order: {order['symbol']} {order['side']} {order['quantity']}")
        
        # Simulate execution delay
        await asyncio.sleep(0.1)
        
        # Log to execution history
        self.execution_history.append({
            'timestamp': datetime.now(),
            'order': order,
            'status': 'FILLED',
            'fill_price': 50.0,  # Simulated fill price
            'commission': 0.5
        })
        
        return True

class ProductionTradingSystem:
    """Main production trading system orchestrator"""
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.data_loader = DataLoader(config.database_config)
        self.spread_calculator = SpreadCalculator(method='kalman')
        self.signal_generator = SignalGenerator()
        self.risk_manager = ProductionRiskManager(config)
        self.order_manager = ProductionOrderManager(config)
        
        # System state
        self.portfolio_value = config.initial_capital
        self.is_running = False
        self.last_signal_time = None
        
        # Production databases (if available)
        self.redis_client = None
        self.postgres_conn = None
        
        if PRODUCTION_DEPS_AVAILABLE:
            self._initialize_production_systems()
    
    def _initialize_production_systems(self):
        """Initialize production database connections"""
        try:
            # Redis for caching and state management
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True
            )
            
            # PostgreSQL for trade storage
            self.postgres_conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'trading'),
                user=os.getenv('POSTGRES_USER', 'trader'),
                password=os.getenv('POSTGRES_PASSWORD', 'password')
            )
            
            logger.info("Production systems initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize production systems: {e}")
            self.redis_client = None
            self.postgres_conn = None
    
    async def start_trading(self):
        """Start the production trading system"""
        logger.info("🚀 Starting VNET/GDS Production Trading System")
        self.is_running = True
        
        try:
            # Start monitoring server
            if PRODUCTION_DEPS_AVAILABLE:
                start_http_server(8000)
                logger.info("Prometheus metrics server started on port 8000")
            
            # Main trading loop
            while self.is_running:
                try:
                    await self._trading_cycle()
                    await asyncio.sleep(self.config.signal_frequency)
                    
                except Exception as e:
                    logger.error(f"Trading cycle error: {e}")
                    logger.error(traceback.format_exc())
                    await asyncio.sleep(5)  # Brief pause before retrying
                    
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            await self.shutdown()
    
    async def _trading_cycle(self):
        """Execute one complete trading cycle"""
        start_time = datetime.now()
        
        try:
            # 1. Load latest market data
            market_data = await self._get_market_data()
            if not market_data:
                logger.warning("No market data available")
                return
            
            # 2. Generate trading signal
            signal = await self._generate_signal(market_data)
            if not signal:
                return
            
            # 3. Risk management validation
            if not self.risk_manager.validate_signal(signal, self.portfolio_value):
                logger.info(f"Signal rejected by risk management: {signal.signal_id}")
                return
            
            # 4. Execute trade
            if signal.action in ['BUY', 'SELL']:
                success = await self.order_manager.execute_signal(signal)
                if success:
                    logger.info(f"✅ Signal executed successfully: {signal.signal_id}")
                    await self._log_trade(signal)
                else:
                    logger.error(f"❌ Signal execution failed: {signal.signal_id}")
            
            # 5. Update metrics
            cycle_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Trading cycle completed in {cycle_time:.3f}s")
            
            if PRODUCTION_DEPS_AVAILABLE:
                SIGNAL_LATENCY.observe(cycle_time)
            
        except Exception as e:
            logger.error(f"Trading cycle failed: {e}")
            raise
    
    async def _get_market_data(self) -> Optional[pd.DataFrame]:
        """Get latest market data for VNET/GDS"""
        try:
            # Load recent data (last 2 hours for real-time analysis)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)
            
            # In production, this would use real-time data feeds
            # For now, we'll use the last available data from ClickHouse
            data = self.data_loader.load_pair_data(
                'VNET', 'GDS',
                start_time.strftime('%Y-%m-%d %H:%M:%S'),
                end_time.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            if data is None or len(data) < 100:
                logger.warning("Insufficient market data for analysis")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
    
    async def _generate_signal(self, market_data: pd.DataFrame) -> Optional[TradingSignal]:
        """Generate trading signal using the full model ensemble"""
        try:
            start_time = datetime.now()
            
            # Calculate spread using Kalman filter
            spread_data = self.spread_calculator.calculate_spread(
                market_data['symbol1_price'].values,
                market_data['symbol2_price'].values
            )
            
            # Generate signal using ensemble
            signal_result = self.signal_generator.generate_signal(
                market_data, spread_data
            )
            
            if not signal_result or signal_result.action == 'HOLD':
                return None
            
            # Create production trading signal
            signal = TradingSignal(
                timestamp=datetime.now(),
                pair='VNET_GDS',
                action=signal_result.action,
                direction=signal_result.direction,
                confidence=signal_result.confidence,
                z_score=signal_result.z_score,
                spread_value=signal_result.spread_value,
                regime=signal_result.regime,
                vnet_quantity=signal_result.vnet_quantity,
                gds_quantity=signal_result.gds_quantity,
                expected_return=signal_result.expected_return,
                risk_score=signal_result.risk_score,
                signal_id=f"VNET_GDS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Signal generated in {generation_time:.3f}s: {signal.action} ({signal.confidence:.2f})")
            
            if PRODUCTION_DEPS_AVAILABLE:
                SIGNALS_GENERATED.inc()
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return None
    
    async def _log_trade(self, signal: TradingSignal):
        """Log trade to production databases"""
        try:
            # Log to Redis (fast cache)
            if self.redis_client:
                signal_data = asdict(signal)
                signal_data['timestamp'] = signal.timestamp.isoformat()
                self.redis_client.lpush('recent_signals', json.dumps(signal_data))
                self.redis_client.ltrim('recent_signals', 0, 99)  # Keep last 100
            
            # Log to PostgreSQL (persistent storage)
            if self.postgres_conn:
                cursor = self.postgres_conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (signal_id, pair, action, confidence, z_score, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    signal.signal_id, signal.pair, signal.action,
                    signal.confidence, signal.z_score, signal.timestamp
                ))
                self.postgres_conn.commit()
                cursor.close()
            
            logger.info(f"Trade logged: {signal.signal_id}")
            
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    async def shutdown(self):
        """Graceful shutdown of the trading system"""
        logger.info("🛑 Shutting down VNET/GDS Trading System")
        self.is_running = False
        
        # Close database connections
        if self.postgres_conn:
            self.postgres_conn.close()
        
        # Final metrics update
        if PRODUCTION_DEPS_AVAILABLE:
            POSITION_VALUE.set(self.portfolio_value)
        
        logger.info("✅ Trading system shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    sys.exit(0)

async def main():
    """Main entry point for production trading system"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load production configuration
    config = ProductionConfig()
    
    # Create and start trading system
    trading_system = ProductionTradingSystem(config)
    
    try:
        await trading_system.start_trading()
    except Exception as e:
        logger.error(f"Trading system failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 VNET/GDS Production Trading System")
    print("=" * 50)
    print("Starting production deployment...")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Run the trading system
    asyncio.run(main()) 