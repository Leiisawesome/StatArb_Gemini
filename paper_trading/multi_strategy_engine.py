#!/usr/bin/env python3
"""
Multi-Strategy Live Trading Engine
==================================

Advanced live trading engine that coordinates multiple strategies simultaneously.
Handles portfolio allocation, risk management, and strategy coordination.

Phase 2B: Multi-Strategy Deployment

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import json
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paper_trading.config.paper_trading_config_manager import PaperTradingConfigManager
from paper_trading.strategy_bridge import (
    MomentumStrategyBridge, 
    MeanReversionStrategyBridge, 
    PairsTradingStrategyBridge,
    LiveTradingSignal,
    SignalType
)
from core_structure.components.broker_integration.ibkr import IBKRClient
from core_structure.components.broker_integration.ibkr_config import IBKRSetupHelper
from core_structure.infrastructure import Order, OrderType, OrderSide, TimeInForce

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_strategy_live_trading.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class StrategyAllocation:
    """Portfolio allocation for each strategy"""
    strategy_id: str
    allocation_pct: float  # Percentage of total portfolio
    max_positions: int
    symbols: List[str]
    enabled: bool = True

@dataclass
class PortfolioState:
    """Current portfolio state across all strategies"""
    total_capital: float
    available_capital: float
    allocated_capital: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)  # strategy_id -> {symbol: quantity}
    unrealized_pnl: Dict[str, float] = field(default_factory=dict)
    realized_pnl: Dict[str, float] = field(default_factory=dict)

@dataclass
class MultiStrategySession:
    """Multi-strategy trading session tracking"""
    session_id: str
    start_time: datetime
    strategies: List[str]
    total_signals: int = 0
    total_orders: int = 0
    strategy_performance: Dict[str, Dict] = field(default_factory=dict)
    portfolio_value_history: List[Dict] = field(default_factory=list)

class MultiStrategyLiveEngine:
    """
    Advanced live trading engine for multiple strategies
    
    Features:
    - Concurrent strategy execution
    - Portfolio allocation management
    - Risk coordination across strategies
    - Position conflict resolution
    - Real-time performance tracking
    """
    
    def __init__(self, use_simulated_data: bool = False):
        self.use_simulated_data = use_simulated_data
        self.config_manager = PaperTradingConfigManager()
        self.config = self.config_manager.get_paper_trading_config()
        
        # Strategy management
        self.strategy_bridges: Dict[str, object] = {}
        self.strategy_allocations: Dict[str, StrategyAllocation] = {}
        
        # Portfolio management
        self.portfolio = PortfolioState(
            total_capital=100000.0,  # $100k starting capital
            available_capital=100000.0
        )
        
        # Session tracking
        self.current_session: Optional[MultiStrategySession] = None
        self.session_stats = {
            'signals_generated': 0,
            'orders_executed': 0,
            'strategies_active': 0
        }
        
        # IBKR integration
        self.client: Optional[IBKRClient] = None
        self.connected = False
        
        # Coordination
        self.symbol_locks: Dict[str, str] = {}  # symbol -> strategy_id (prevents conflicts)
        self.last_signal_time: Dict[str, datetime] = {}
        
        # Simulated data
        self.simulated_prices: Dict[str, float] = {
            'SPY': 580.0,
            'QQQ': 480.0,
            'GLD': 240.0,
            'GDX': 32.0,
            'IWM': 220.0,
            'EFA': 85.0
        }
        
        self.logger = logger
    
    async def initialize(self):
        """Initialize the multi-strategy engine"""
        
        self.logger.info("🚀 Initializing Multi-Strategy Live Trading Engine")
        
        if self.use_simulated_data:
            self.logger.info("🧪 Using simulated market data for testing")
        
        # Initialize IBKR connection
        await self._initialize_broker()
        
        # Setup strategy allocations
        self._setup_strategy_allocations()
        
        # Initialize strategy bridges
        await self._initialize_strategies()
        
        self.logger.info("✅ Multi-Strategy Engine initialized successfully")
    
    def _setup_strategy_allocations(self):
        """Setup portfolio allocations for each strategy"""
        
        # Define strategy allocations
        allocations = [
            StrategyAllocation(
                strategy_id="momentum_v1",
                allocation_pct=0.4,  # 40% of portfolio
                max_positions=3,
                symbols=['SPY', 'QQQ', 'IWM']
            ),
            StrategyAllocation(
                strategy_id="mean_reversion_v1", 
                allocation_pct=0.3,  # 30% of portfolio
                max_positions=2,
                symbols=['SPY', 'QQQ']
            ),
            StrategyAllocation(
                strategy_id="pairs_trading_v1",
                allocation_pct=0.3,  # 30% of portfolio
                max_positions=1,  # 1 pair = 2 positions
                symbols=['GLD', 'GDX']
            )
        ]
        
        for allocation in allocations:
            self.strategy_allocations[allocation.strategy_id] = allocation
            allocated_capital = self.portfolio.total_capital * allocation.allocation_pct
            self.portfolio.allocated_capital[allocation.strategy_id] = allocated_capital
            
            self.logger.info(f"📊 {allocation.strategy_id}: ${allocated_capital:,.0f} "
                           f"({allocation.allocation_pct*100:.0f}%) - {allocation.symbols}")
    
    async def _initialize_broker(self):
        """Initialize IBKR broker connection"""
        
        try:
            # Create IBKR client
            ibkr_config = IBKRSetupHelper.create_paper_trading_config()
            self.client = IBKRClient(ibkr_config)
            
            # Connect
            self.logger.info("🔌 Connecting to IBKR for order execution...")
            await self.client.connect()
            self.connected = True
            
            self.logger.info("✅ Connected to IBKR for multi-strategy trading")
            
        except Exception as e:
            self.logger.error(f"❌ IBKR connection failed: {e}")
            self.connected = False
    
    async def _initialize_strategies(self):
        """Initialize all strategy bridges"""
        
        self.logger.info("🧠 Initializing strategy bridges...")
        
        # Create strategy configs for each strategy
        from paper_trading.config.paper_trading_config_manager import LiveStrategyConfig
        
        # Initialize Momentum Strategy
        if "momentum_v1" in self.strategy_allocations:
            momentum_config = LiveStrategyConfig(
                strategy_id="momentum_v1_multi",
                enable_strategy=True,
                max_positions=self.strategy_allocations["momentum_v1"].max_positions,
                signal_frequency="30s",
                max_drawdown=0.05
            )
            self.strategy_bridges["momentum_v1"] = MomentumStrategyBridge(
                strategy_config=momentum_config,
                broker_client=self.client,
                config_manager=self.config_manager
            )
            self.logger.info("✅ Momentum strategy bridge initialized")
        
        # Initialize Mean Reversion Strategy  
        if "mean_reversion_v1" in self.strategy_allocations:
            mean_reversion_config = LiveStrategyConfig(
                strategy_id="mean_reversion_v1_multi",
                enable_strategy=True,
                max_positions=self.strategy_allocations["mean_reversion_v1"].max_positions,
                signal_frequency="30s",
                max_drawdown=0.05
            )
            self.strategy_bridges["mean_reversion_v1"] = MeanReversionStrategyBridge(
                strategy_config=mean_reversion_config,
                broker_client=self.client,
                config_manager=self.config_manager
            )
            self.logger.info("✅ Mean Reversion strategy bridge initialized")
        
        # Initialize Pairs Trading Strategy
        if "pairs_trading_v1" in self.strategy_allocations:
            pairs_config = LiveStrategyConfig(
                strategy_id="pairs_trading_v1_multi",
                enable_strategy=True,
                max_positions=self.strategy_allocations["pairs_trading_v1"].max_positions,
                signal_frequency="30s",
                max_drawdown=0.05
            )
            self.strategy_bridges["pairs_trading_v1"] = PairsTradingStrategyBridge(
                strategy_config=pairs_config,
                broker_client=self.client,
                config_manager=self.config_manager
            )
            self.logger.info("✅ Pairs Trading strategy bridge initialized")
        
        self.session_stats['strategies_active'] = len(self.strategy_bridges)
        self.logger.info(f"🎯 {len(self.strategy_bridges)} strategies active")
    
    async def start_multi_strategy_session(self, duration_minutes: int = 60):
        """Start multi-strategy trading session"""
        
        session_id = f"multi_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = MultiStrategySession(
            session_id=session_id,
            start_time=datetime.now(),
            strategies=list(self.strategy_bridges.keys())
        )
        
        self.logger.info("🎯 Starting Multi-Strategy Trading Session")
        self.logger.info(f"   Session ID: {session_id}")
        self.logger.info(f"   Strategies: {', '.join(self.current_session.strategies)}")
        self.logger.info(f"   Duration: {duration_minutes} minutes")
        self.logger.info(f"   Total Capital: ${self.portfolio.total_capital:,.0f}")
        
        if self.use_simulated_data:
            self.logger.info("   🧪 Market data: SIMULATED")
        else:
            self.logger.info("   📊 Market data: LIVE IBKR")
        
        # Start main trading loop
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        try:
            while datetime.now() < end_time:
                await self._execute_trading_cycle()
                await asyncio.sleep(30)  # 30-second intervals
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Multi-strategy session interrupted by user")
        
        await self._finalize_session()
    
    async def _execute_trading_cycle(self):
        """Execute one trading cycle across all strategies"""
        
        try:
            # Update simulated prices if needed
            if self.use_simulated_data:
                self._update_simulated_prices()
            
            # Generate signals from all strategies concurrently
            signal_tasks = []
            for strategy_id, bridge in self.strategy_bridges.items():
                allocation = self.strategy_allocations[strategy_id]
                if allocation.enabled:
                    task = self._generate_strategy_signals(strategy_id, bridge, allocation.symbols)
                    signal_tasks.append(task)
            
            # Wait for all signals
            all_signals = await asyncio.gather(*signal_tasks, return_exceptions=True)
            
            # Process signals with coordination
            for strategy_id, signals in zip(self.strategy_bridges.keys(), all_signals):
                if isinstance(signals, Exception):
                    self.logger.error(f"❌ Signal generation error for {strategy_id}: {signals}")
                    continue
                
                if signals:
                    await self._process_coordinated_signals(strategy_id, signals)
            
            # Update portfolio state
            await self._update_portfolio_state()
            
            # Log session status
            self._log_session_status()
            
        except Exception as e:
            self.logger.error(f"❌ Trading cycle error: {e}")
    
    async def _generate_strategy_signals(self, strategy_id: str, bridge, symbols: List[str]) -> List[LiveTradingSignal]:
        """Generate signals for a specific strategy"""
        
        try:
            # Get market data for symbols
            market_data = {}
            for symbol in symbols:
                if self.use_simulated_data:
                    # Use simulated prices
                    market_data[symbol] = {
                        'price': self.simulated_prices[symbol],
                        'bid': self.simulated_prices[symbol] * 0.9995,
                        'ask': self.simulated_prices[symbol] * 1.0005,
                        'volume': 1000000
                    }
                else:
                    # Get real market data from IBKR
                    data = await self.client.get_market_data(symbol)
                    if data:
                        market_data[symbol] = {
                            'price': data.last,
                            'bid': data.bid,
                            'ask': data.ask,
                            'volume': data.volume
                        }
            
            # Generate signals using the bridge
            signals = await bridge.generate_signals(symbols)
            return signals if signals else []
            
        except Exception as e:
            self.logger.error(f"❌ Signal generation error for {strategy_id}: {e}")
            return []
    
    async def _process_coordinated_signals(self, strategy_id: str, signals: List[LiveTradingSignal]):
        """Process signals with multi-strategy coordination"""
        
        allocation = self.strategy_allocations[strategy_id]
        
        for signal in signals:
            try:
                # Check if symbol is locked by another strategy
                if signal.symbol in self.symbol_locks:
                    locked_by = self.symbol_locks[signal.symbol]
                    if locked_by != strategy_id:
                        self.logger.warning(f"⚠️  {signal.symbol} locked by {locked_by}, skipping {strategy_id} signal")
                        continue
                
                # Check position limits for this strategy
                current_positions = len(self.portfolio.positions.get(strategy_id, {}))
                if current_positions >= allocation.max_positions:
                    self.logger.warning(f"⚠️  {strategy_id} at position limit ({allocation.max_positions})")
                    continue
                
                # Check available capital
                allocated_capital = self.portfolio.allocated_capital[strategy_id]
                position_value = signal.target_position_size * self.simulated_prices[signal.symbol]
                
                if position_value > allocated_capital * 0.8:  # Max 80% of allocated capital per position
                    self.logger.warning(f"⚠️  Position too large for {strategy_id}: ${position_value:,.0f}")
                    continue
                
                # Process the signal
                if signal.signal_type != SignalType.HOLD:
                    await self._execute_coordinated_trade(strategy_id, signal)
                    
                    # Lock the symbol for this strategy
                    self.symbol_locks[signal.symbol] = strategy_id
                    self.last_signal_time[strategy_id] = datetime.now()
                    
                    self.session_stats['signals_generated'] += 1
                    self.current_session.total_signals += 1
                    
                    self.logger.info(f"📊 {strategy_id}: {signal.symbol} {signal.signal_type.value} "
                                   f"(confidence: {signal.confidence:.2f})")
                
            except Exception as e:
                self.logger.error(f"❌ Signal processing error for {strategy_id}: {e}")
    
    async def _execute_coordinated_trade(self, strategy_id: str, signal: LiveTradingSignal):
        """Execute trade with multi-strategy coordination"""
        
        try:
            # Create order
            order_side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL
            
            order = Order(
                order_id=f"{strategy_id}_{signal.symbol}_{datetime.now().strftime('%H%M%S')}",
                symbol=signal.symbol,
                quantity=abs(int(signal.target_position_size)),
                order_type=OrderType.MARKET,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            if self.use_simulated_data:
                # Simulate order execution
                self.logger.info(f"🧪 SIMULATED ORDER: {order.symbol} {order.side.value} {order.quantity} shares")
                
                # Update simulated positions
                if strategy_id not in self.portfolio.positions:
                    self.portfolio.positions[strategy_id] = {}
                
                current_qty = self.portfolio.positions[strategy_id].get(signal.symbol, 0)
                if order.side == OrderSide.BUY:
                    new_qty = current_qty + order.quantity
                else:
                    new_qty = current_qty - order.quantity
                
                self.portfolio.positions[strategy_id][signal.symbol] = new_qty
                
                self.session_stats['orders_executed'] += 1
                self.current_session.total_orders += 1
                
            else:
                # Execute real order through IBKR
                if self.connected:
                    result = await self.client.place_order(order)
                    if result.success:
                        self.logger.info(f"✅ ORDER EXECUTED: {order.symbol} {order.side.value} {order.quantity}")
                        self.session_stats['orders_executed'] += 1
                        self.current_session.total_orders += 1
                    else:
                        self.logger.error(f"❌ ORDER FAILED: {result.error_message}")
                else:
                    self.logger.error("❌ Not connected to IBKR")
                    
        except Exception as e:
            self.logger.error(f"❌ Trade execution error: {e}")
    
    def _update_simulated_prices(self):
        """Update simulated market prices"""
        
        import random
        
        for symbol in self.simulated_prices:
            # Random walk with mean reversion
            change_pct = random.gauss(0, 0.001)  # 0.1% volatility
            self.simulated_prices[symbol] *= (1 + change_pct)
            
            # Mean reversion (prevent drift)
            if symbol == 'SPY' and self.simulated_prices[symbol] > 590:
                self.simulated_prices[symbol] *= 0.999
            elif symbol == 'SPY' and self.simulated_prices[symbol] < 570:
                self.simulated_prices[symbol] *= 1.001
    
    async def _update_portfolio_state(self):
        """Update portfolio state and calculate P&L"""
        
        total_value = 0
        
        for strategy_id, positions in self.portfolio.positions.items():
            strategy_value = 0
            
            for symbol, quantity in positions.items():
                if quantity != 0:
                    current_price = self.simulated_prices.get(symbol, 0)
                    position_value = quantity * current_price
                    strategy_value += position_value
            
            total_value += strategy_value
            
            # Update unrealized P&L (simplified)
            allocated_capital = self.portfolio.allocated_capital[strategy_id]
            self.portfolio.unrealized_pnl[strategy_id] = strategy_value - allocated_capital
        
        self.portfolio.available_capital = self.portfolio.total_capital - total_value
    
    def _log_session_status(self):
        """Log current session status"""
        
        elapsed = datetime.now() - self.current_session.start_time
        
        self.logger.info("📊 MULTI-STRATEGY SESSION STATUS:")
        self.logger.info(f"   Elapsed: {elapsed}")
        self.logger.info(f"   Total Signals: {self.current_session.total_signals}")
        self.logger.info(f"   Total Orders: {self.current_session.total_orders}")
        self.logger.info(f"   Active Strategies: {len(self.strategy_bridges)}")
        
        # Portfolio summary
        total_unrealized = sum(self.portfolio.unrealized_pnl.values())
        self.logger.info(f"   Portfolio Value: ${self.portfolio.total_capital + total_unrealized:,.0f}")
        self.logger.info(f"   Unrealized P&L: ${total_unrealized:,.0f}")
        
        # Strategy breakdown
        for strategy_id in self.strategy_bridges.keys():
            positions = len(self.portfolio.positions.get(strategy_id, {}))
            pnl = self.portfolio.unrealized_pnl.get(strategy_id, 0)
            self.logger.info(f"   {strategy_id}: {positions} positions, P&L: ${pnl:,.0f}")
    
    async def _finalize_session(self):
        """Finalize multi-strategy session"""
        
        self.logger.info("📋 MULTI-STRATEGY SESSION SUMMARY:")
        self.logger.info(f"   Session ID: {self.current_session.session_id}")
        self.logger.info(f"   Duration: {datetime.now() - self.current_session.start_time}")
        self.logger.info(f"   Total Signals: {self.current_session.total_signals}")
        self.logger.info(f"   Orders Executed: {self.current_session.total_orders}")
        
        total_unrealized = sum(self.portfolio.unrealized_pnl.values())
        self.logger.info(f"   Final Portfolio Value: ${self.portfolio.total_capital + total_unrealized:,.0f}")
        self.logger.info(f"   Total P&L: ${total_unrealized:,.0f}")
        
        if self.use_simulated_data:
            self.logger.info("   🧪 Mode: SIMULATED DATA")
        
        # Disconnect from IBKR
        if self.connected and self.client:
            await self.client.disconnect()
            self.logger.info("🔌 Disconnected from IBKR")

async def main():
    """Main function for multi-strategy deployment"""
    
    print("🚀 PHASE 2B: MULTI-STRATEGY LIVE DEPLOYMENT")
    print("=" * 60)
    print()
    print("This system deploys multiple strategies simultaneously:")
    print("• 📈 Momentum Strategy (40% allocation)")
    print("• 📉 Mean Reversion Strategy (30% allocation)")  
    print("• 🔄 Pairs Trading Strategy (30% allocation)")
    print()
    print("Features:")
    print("✅ Portfolio allocation management")
    print("✅ Strategy coordination and conflict resolution")
    print("✅ Real-time risk management")
    print("✅ Multi-strategy performance tracking")
    print()
    
    # Ask for test mode
    print("Available test modes:")
    print("1. Quick test (10 minutes)")
    print("2. Medium test (30 minutes)")
    print("3. Extended test (60 minutes)")
    print()
    
    try:
        choice = input("Select test mode (1-3) or press Enter for quick test: ").strip()
        if choice == "2":
            duration = 30
        elif choice == "3":
            duration = 60
        else:
            duration = 10
            
        print(f"Running {duration}-minute multi-strategy test...")
        
        # Initialize and run multi-strategy engine
        engine = MultiStrategyLiveEngine(use_simulated_data=True)
        await engine.initialize()
        await engine.start_multi_strategy_session(duration_minutes=duration)
        
        print("✅ Multi-strategy deployment completed successfully")
        
    except KeyboardInterrupt:
        print("\n🛑 Multi-strategy deployment interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
