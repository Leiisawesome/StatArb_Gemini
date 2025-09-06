#!/usr/bin/env python3
"""
Live Trading Engine
==================

Real-time trading engine for executing strategies with IBKR paper trading.
Orchestrates signal generation, order management, and position monitoring.

Phase 2A: Single Strategy Deployment (Momentum)

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import core components
from core_structure.components.broker_integration.ibkr import IBKRClient
from core_structure.components.broker_integration.ibkr_config import IBKRSetupHelper
from core_structure.infrastructure import Order, OrderType, OrderSide, TimeInForce, OrderStatus

# Import paper trading components
from paper_trading.config.paper_trading_config_manager import PaperTradingConfigManager
from paper_trading.strategy_bridge import StrategyBridgeFactory, MomentumStrategyBridge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TradingSession:
    """Trading session information"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    strategy_name: str = ""
    total_signals: int = 0
    executed_orders: int = 0
    active_positions: int = 0
    session_pnl: float = 0.0
    status: str = "active"

@dataclass 
class LivePosition:
    """Live position tracking"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    strategy: str = ""
    
    def update_current_price(self, price: float):
        """Update current price and calculate unrealized P&L"""
        self.current_price = price
        if self.quantity != 0:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity

@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    quantity: int
    signal_time: datetime = field(default_factory=datetime.now)
    strategy: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class LiveTradingEngine:
    """
    Live trading engine for real-time strategy execution
    
    Phase 2A: Single strategy deployment with momentum strategy
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client: Optional[IBKRClient] = None
        self.config_manager = PaperTradingConfigManager()
        self.strategy_bridge: Optional[MomentumStrategyBridge] = None
        
        # Trading state
        self.is_running = False
        self.current_session: Optional[TradingSession] = None
        self.positions: Dict[str, LivePosition] = {}
        self.pending_orders: Dict[str, Order] = {}
        
        # Configuration
        self.max_position_size = 100  # Small size for Phase 2A
        self.max_total_exposure = 10000  # $10k max exposure
        self.signal_interval = 60  # Check signals every 60 seconds
        
        # Performance tracking
        self.session_stats = {
            'signals_generated': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the live trading engine"""
        try:
            self.logger.info("🚀 Initializing Live Trading Engine - Phase 2A")
            
            # Load configuration
            paper_config = self.config_manager.get_paper_trading_config()
            
            # Setup IBKR client
            ibkr_config = IBKRSetupHelper.create_paper_trading_config(
                account_id=paper_config.ibkr.account_id or "DU123456"
            )
            ibkr_config.host = paper_config.ibkr.host
            ibkr_config.port = paper_config.ibkr.port
            ibkr_config.client_id = paper_config.ibkr.client_id
            
            self.client = IBKRClient(ibkr_config)
            
            # Connect to IBKR
            self.logger.info("🔌 Connecting to IBKR...")
            connected = await self.client.connect()
            
            if not connected:
                raise Exception("Failed to connect to IBKR")
            
            self.logger.info("✅ Connected to IBKR successfully")
            
            # Initialize momentum strategy bridge
            self.logger.info("🧠 Initializing Momentum Strategy Bridge...")
            
            # Create strategy config for momentum
            from paper_trading.config.paper_trading_config_manager import LiveStrategyConfig
            strategy_config = LiveStrategyConfig(
                strategy_id="momentum_v1_phase2a",
                enable_strategy=True,
                max_positions=5,  # Max 5 positions
                signal_frequency="1min",
                max_drawdown=0.05  # 5% max drawdown for Phase 2A
            )
            
            bridge_factory = StrategyBridgeFactory()
            self.strategy_bridge = bridge_factory.create_bridge(
                strategy_type='momentum',
                strategy_config=strategy_config,
                broker_client=self.client,
                config_manager=self.config_manager
            )
            
            self.logger.info("✅ Momentum Strategy Bridge initialized")
            
            # Validate account
            account_summary = await self.client.get_account_summary()
            if not account_summary.account_id.startswith('DU'):
                raise Exception("Not a paper trading account - safety check failed")
            
            self.logger.info(f"✅ Paper trading account validated: {account_summary.account_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def start_trading_session(self, session_name: str = "momentum_test") -> bool:
        """Start a new trading session"""
        try:
            if self.is_running:
                self.logger.warning("Trading session already running")
                return False
            
            # Create new session
            session_id = f"{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_session = TradingSession(
                session_id=session_id,
                start_time=datetime.now(),
                strategy_name="momentum_v1"
            )
            
            self.is_running = True
            
            self.logger.info(f"🎯 Starting trading session: {session_id}")
            self.logger.info(f"   Strategy: Momentum")
            self.logger.info(f"   Max position size: {self.max_position_size}")
            self.logger.info(f"   Max total exposure: ${self.max_total_exposure:,}")
            self.logger.info(f"   Signal interval: {self.signal_interval}s")
            
            # Start main trading loop
            await self._run_trading_loop()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading session: {e}")
            self.is_running = False
            return False
    
    async def _run_trading_loop(self):
        """Main trading loop"""
        self.logger.info("🔄 Starting main trading loop...")
        
        try:
            while self.is_running:
                # Generate signals
                await self._process_signals()
                
                # Update positions
                await self._update_positions()
                
                # Monitor orders
                await self._monitor_orders()
                
                # Log session status
                await self._log_session_status()
                
                # Wait for next interval
                await asyncio.sleep(self.signal_interval)
                
        except Exception as e:
            self.logger.error(f"❌ Trading loop error: {e}")
        finally:
            await self._end_session()
    
    async def _process_signals(self):
        """Process trading signals from strategy"""
        try:
            if not self.strategy_bridge:
                return
            
            # Get current market data for our symbols
            symbols = ['SPY', 'QQQ']
            market_data = {}
            
            for symbol in symbols:
                try:
                    data = await self.client.get_market_data(symbol)
                    if data and data.last > 0:
                        market_data[symbol] = {
                            'price': data.last,
                            'bid': data.bid,
                            'ask': data.ask,
                            'timestamp': datetime.now()
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to get market data for {symbol}: {e}")
            
            if not market_data:
                self.logger.warning("No market data available for signal generation")
                return
            
            # Generate signals using strategy bridge
            symbols = list(market_data.keys())
            if symbols:
                try:
                    signals = await self.strategy_bridge.generate_signals(symbols)
                    
                    for signal in signals:
                        if signal.signal_type.value != 'HOLD':
                            self.session_stats['signals_generated'] += 1
                            self.current_session.total_signals += 1
                            
                            self.logger.info(f"📊 Signal generated: {signal.symbol} {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
                            
                            # Convert to dict format for processing
                            signal_dict = {
                                'action': signal.signal_type.value,
                                'confidence': signal.confidence,
                                'quantity': int(signal.target_position_size),
                                'metadata': signal.metadata
                            }
                            
                            # Process the signal
                            await self._process_trading_signal(signal.symbol, signal_dict)
                            
                except Exception as e:
                    self.logger.error(f"Signal generation error: {e}")
                    
        except Exception as e:
            self.logger.error(f"Signal processing error: {e}")
    
    async def _process_trading_signal(self, symbol: str, signal: Dict[str, Any]):
        """Process a trading signal and potentially place an order"""
        try:
            action = signal.get('action')
            confidence = signal.get('confidence', 0)
            
            # Check if we should act on this signal
            if confidence < 0.6:  # Minimum confidence threshold
                self.logger.info(f"Signal confidence too low for {symbol}: {confidence:.2f}")
                return
            
            # Calculate position size
            position_size = self._calculate_position_size(symbol, signal)
            
            if position_size == 0:
                self.logger.info(f"Position size calculated as 0 for {symbol}")
                return
            
            # Check risk limits
            if not self._check_risk_limits(symbol, position_size):
                self.logger.warning(f"Risk limits exceeded for {symbol} position size {position_size}")
                return
            
            # Create and place order
            order = self._create_order(symbol, action, position_size)
            
            if order:
                await self._place_order(order)
                
        except Exception as e:
            self.logger.error(f"Error processing trading signal for {symbol}: {e}")
    
    def _calculate_position_size(self, symbol: str, signal: Dict[str, Any]) -> int:
        """Calculate appropriate position size"""
        try:
            # Base position size (small for Phase 2A)
            base_size = min(self.max_position_size, 10)  # Very conservative
            
            # Adjust by confidence
            confidence = signal.get('confidence', 0)
            adjusted_size = int(base_size * confidence)
            
            # Check current position
            current_position = self.positions.get(symbol)
            if current_position:
                # If we already have a position, be more conservative
                adjusted_size = max(1, adjusted_size // 2)
            
            return max(1, adjusted_size)  # Minimum 1 share
            
        except Exception as e:
            self.logger.error(f"Position size calculation error: {e}")
            return 0
    
    def _check_risk_limits(self, symbol: str, position_size: int) -> bool:
        """Check if trade meets risk management criteria"""
        try:
            # Check maximum position size
            if position_size > self.max_position_size:
                return False
            
            # Check total exposure (simplified)
            current_exposure = sum(
                abs(pos.quantity * pos.current_price) 
                for pos in self.positions.values()
            )
            
            # Estimate new exposure (using approximate price)
            estimated_price = 500  # Conservative estimate for SPY/QQQ
            new_exposure = position_size * estimated_price
            
            if current_exposure + new_exposure > self.max_total_exposure:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Risk check error: {e}")
            return False
    
    def _create_order(self, symbol: str, action: str, quantity: int) -> Optional[Order]:
        """Create an order object"""
        try:
            order_id = f"momentum_{symbol}_{datetime.now().strftime('%H%M%S')}"
            
            side = OrderSide.BUY if action == 'BUY' else OrderSide.SELL
            
            order = Order(
                order_id=order_id,
                symbol=symbol,
                quantity=quantity,
                order_type=OrderType.MARKET,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            return order
            
        except Exception as e:
            self.logger.error(f"Order creation error: {e}")
            return None
    
    async def _place_order(self, order: Order):
        """Place an order with IBKR"""
        try:
            self.logger.info(f"📋 Placing order: {order.symbol} {order.side.value} {order.quantity}")
            
            # Add to pending orders
            self.pending_orders[order.order_id] = order
            
            # Place order with IBKR
            result = await self.client.place_order(order)
            
            if result and result.status != OrderStatus.REJECTED:
                self.session_stats['orders_placed'] += 1
                self.current_session.executed_orders += 1
                
                self.logger.info(f"✅ Order placed successfully: {order.order_id}")
                self.logger.info(f"   Status: {result.status}")
            else:
                self.logger.error(f"❌ Order rejected: {order.order_id}")
                # Remove from pending orders
                self.pending_orders.pop(order.order_id, None)
                
        except Exception as e:
            self.logger.error(f"Order placement error: {e}")
            # Remove from pending orders on error
            self.pending_orders.pop(order.order_id, None)
    
    async def _update_positions(self):
        """Update current positions and P&L"""
        try:
            # Get current positions from IBKR
            ibkr_positions = await self.client.get_positions()
            
            # Update our position tracking
            for pos in ibkr_positions:
                if pos.symbol in self.positions:
                    # Update existing position
                    live_pos = self.positions[pos.symbol]
                    live_pos.quantity = pos.quantity
                    
                    # Get current market price
                    try:
                        market_data = await self.client.get_market_data(pos.symbol)
                        if market_data and market_data.last > 0:
                            live_pos.update_current_price(market_data.last)
                    except:
                        pass  # Skip if market data unavailable
                        
                else:
                    # New position
                    self.positions[pos.symbol] = LivePosition(
                        symbol=pos.symbol,
                        quantity=pos.quantity,
                        entry_price=pos.average_price,
                        strategy="momentum_v1"
                    )
            
            # Remove closed positions
            symbols_to_remove = []
            for symbol, pos in self.positions.items():
                if not any(ibkr_pos.symbol == symbol for ibkr_pos in ibkr_positions):
                    symbols_to_remove.append(symbol)
            
            for symbol in symbols_to_remove:
                del self.positions[symbol]
                
        except Exception as e:
            self.logger.error(f"Position update error: {e}")
    
    async def _monitor_orders(self):
        """Monitor pending orders"""
        try:
            # Simple order monitoring - remove filled/cancelled orders
            orders_to_remove = []
            
            for order_id, order in self.pending_orders.items():
                # In a real implementation, you'd check order status with IBKR
                # For now, we'll assume orders are processed after some time
                pass
            
            for order_id in orders_to_remove:
                self.pending_orders.pop(order_id, None)
                
        except Exception as e:
            self.logger.error(f"Order monitoring error: {e}")
    
    async def _log_session_status(self):
        """Log current session status"""
        try:
            total_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            active_positions = len([pos for pos in self.positions.values() if pos.quantity != 0])
            
            self.logger.info(f"📊 Session Status:")
            self.logger.info(f"   Signals: {self.session_stats['signals_generated']}")
            self.logger.info(f"   Orders: {self.session_stats['orders_placed']}")
            self.logger.info(f"   Active Positions: {active_positions}")
            self.logger.info(f"   Unrealized P&L: ${total_pnl:.2f}")
            
            # Update session stats
            if self.current_session:
                self.current_session.active_positions = active_positions
                self.current_session.session_pnl = total_pnl
                
        except Exception as e:
            self.logger.error(f"Status logging error: {e}")
    
    async def stop_trading(self):
        """Stop the trading session"""
        self.logger.info("🛑 Stopping trading session...")
        self.is_running = False
    
    async def _end_session(self):
        """End the current trading session"""
        try:
            if self.current_session:
                self.current_session.end_time = datetime.now()
                self.current_session.status = "completed"
                
                duration = self.current_session.end_time - self.current_session.start_time
                
                self.logger.info(f"📋 Session Summary:")
                self.logger.info(f"   Session ID: {self.current_session.session_id}")
                self.logger.info(f"   Duration: {duration}")
                self.logger.info(f"   Total Signals: {self.current_session.total_signals}")
                self.logger.info(f"   Orders Executed: {self.current_session.executed_orders}")
                self.logger.info(f"   Final P&L: ${self.current_session.session_pnl:.2f}")
            
            # Disconnect from IBKR
            if self.client:
                await self.client.disconnect()
                self.logger.info("🔌 Disconnected from IBKR")
                
        except Exception as e:
            self.logger.error(f"Session end error: {e}")

async def main():
    """Main function for testing the live trading engine"""
    engine = LiveTradingEngine()
    
    try:
        # Initialize
        if not await engine.initialize():
            print("❌ Failed to initialize trading engine")
            return
        
        print("✅ Live Trading Engine initialized successfully")
        print("🎯 Ready to start Phase 2A: Momentum Strategy Test")
        print()
        print("To start trading session, run:")
        print("await engine.start_trading_session('momentum_test')")
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        await engine.stop_trading()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
