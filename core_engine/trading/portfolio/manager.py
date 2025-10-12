#!/usr/bin/env python3
"""
Portfolio Manager - Core Engine
===============================

Clean implementation of the portfolio manager for core_engine.
This component manages portfolio positions, P&L, and analytics.

As a supporting component in the institutional architecture:
- Tracks all portfolio positions and their P&L
- Calculates portfolio-level metrics and risk
- Provides position updates to Risk Manager
- Manages position lifecycle and reconciliation

Migration: Direct implementation using proven portfolio patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production - Portfolio)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

# Use internal core_engine types for independence
from ...type_definitions import (
    PortfolioManager as BasePortfolioManager, PortfolioConfig, PortfolioSnapshot,
    AnalyticsEngine
)

logger = logging.getLogger(__name__)

class PositionStatus(Enum):
    """Position status types"""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"
    SUSPENDED = "suspended"

class PositionType(Enum):
    """Position types"""
    LONG = "long"
    SHORT = "short"

@dataclass
class Position:
    """Portfolio position"""
    position_id: str
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    position_type: PositionType
    status: PositionStatus
    strategy: str
    entry_time: datetime
    last_update: datetime
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    market_value: float = 0.0
    cost_basis: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot at a point in time"""
    timestamp: datetime
    total_value: float
    cash_balance: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    position_count: int
    long_exposure: float
    short_exposure: float
    net_exposure: float
    gross_exposure: float
    positions: Dict[str, Position] = field(default_factory=dict)

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    information_ratio: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioManagerConfig:
    """Portfolio manager configuration"""
    initial_capital: float = 100000.0
    cash_reserve_ratio: float = 0.1  # 10% cash reserve
    position_size_limit: float = 0.1  # 10% max position size
    max_positions: int = 20
    enable_real_time_pnl: bool = True
    pnl_calculation_interval: int = 30  # seconds
    enable_risk_monitoring: bool = True
    drawdown_alert_threshold: float = 0.05  # 5% drawdown alert

class IPortfolioSubscriber:
    """Interface for portfolio event subscribers"""
    
    async def on_position_update(self, position: Position) -> None:
        """Handle position updates"""
    
    async def on_pnl_update(self, pnl_data: Dict[str, Any]) -> None:
        """Handle P&L updates"""
    
    async def on_portfolio_alert(self, alert: Dict[str, Any]) -> None:
        """Handle portfolio alerts"""

class PortfolioManager:
    """
    Core Engine Portfolio Manager
    
    This component manages the complete portfolio state:
    
    1. Tracks all positions and their P&L
    2. Calculates real-time portfolio metrics
    3. Provides position updates to Risk Manager
    4. Monitors portfolio-level risk and alerts
    5. Maintains historical portfolio performance
    
    The portfolio management includes:
    - Real-time position tracking
    - P&L calculation and attribution
    - Portfolio-level analytics
    - Risk monitoring and alerting
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = PortfolioManagerConfig(**config) if config else PortfolioManagerConfig()
        
        # Component references
        self.risk_manager: Optional[Any] = None
        self.data_manager: Optional[Any] = None
        
        # Portfolio state
        self.positions: Dict[str, Position] = {}
        self.cash_balance: float = self.config.initial_capital
        self.initial_capital: float = self.config.initial_capital
        
        # Portfolio history
        self.portfolio_snapshots: List[PortfolioSnapshot] = []
        self.daily_pnl_history: List[float] = []
        self.metrics_history: List[PortfolioMetrics] = []
        
        # Current metrics
        self.current_metrics: PortfolioMetrics = PortfolioMetrics()
        self.current_snapshot: Optional[PortfolioSnapshot] = None
        
        # Market data cache
        self.market_prices: Dict[str, float] = {}
        self.price_last_updated: Dict[str, datetime] = {}
        
        # Subscribers
        self.subscribers: List[IPortfolioSubscriber] = []
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.pnl_calculation_task: Optional[asyncio.Task] = None
        
        # Leverage existing portfolio manager
        self.portfolio_manager: Optional[BasePortfolioManager] = None
        self.analytics_engine: Optional[AnalyticsEngine] = None
        
        logger.info("💼 Portfolio Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize portfolio manager"""
        try:
            logger.info("🔄 Initializing Portfolio Manager...")
            
            # Initialize portfolio manager
            self.portfolio_manager = BasePortfolioManager(
                PortfolioConfig(
                    initial_cash=self.config.initial_capital,
                    max_position_size=1.0 / self.config.max_positions if self.config.max_positions > 0 else 0.1
                )
            )
            
            # Initialize analytics engine
            self.analytics_engine = AnalyticsEngine()
            
            # Create initial portfolio snapshot
            await self._create_initial_snapshot()
            
            self.is_initialized = True
            logger.info("✅ Portfolio Manager initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Portfolio Manager initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start portfolio manager"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Portfolio Manager not initialized")
            
            logger.info("🚀 Starting Portfolio Manager monitoring...")
            
            # Start P&L calculation loop
            if self.config.enable_real_time_pnl:
                self.pnl_calculation_task = asyncio.create_task(self._run_pnl_calculation())
            
            self.is_running = True
            logger.info("✅ Portfolio Manager started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Portfolio Manager: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop portfolio manager"""
        try:
            logger.info("🛑 Stopping Portfolio Manager...")
            
            if self.pnl_calculation_task:
                self.pnl_calculation_task.cancel()
                try:
                    await self.pnl_calculation_task
                except asyncio.CancelledError:
                    pass
                self.pnl_calculation_task = None
            
            # Create final portfolio snapshot
            await self._create_portfolio_snapshot()
            
            self.is_running = False
            logger.info("✅ Portfolio Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Portfolio Manager: {e}")
            return False
    
    # Component Integration
    def set_risk_manager(self, risk_manager: Any):
        """Set risk manager reference"""
        self.risk_manager = risk_manager
        logger.info("🔗 Risk Manager linked to Portfolio Manager")
    
    def set_data_manager(self, data_manager: Any):
        """Set data manager reference"""
        self.data_manager = data_manager
        logger.info("🔗 Data Manager linked to Portfolio Manager")
    
    def subscribe(self, subscriber: IPortfolioSubscriber):
        """Subscribe to portfolio events"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New portfolio subscriber: {type(subscriber).__name__}")
    
    # Core Portfolio Methods
    async def update_position(self, symbol: str, quantity_change: float, price: float, strategy: str, execution_id: str) -> Position:
        """Update position from execution"""
        try:
            logger.info(f"📊 Updating position: {symbol} {quantity_change:+.2f} @ {price}")
            
            # Get or create position
            position = await self._get_or_create_position(symbol, strategy)
            
            # Calculate new position values
            old_quantity = position.quantity
            new_quantity = old_quantity + quantity_change
            
            # Handle position closure
            if new_quantity == 0:
                position.status = PositionStatus.CLOSED
                realized_pnl = (price - position.entry_price) * old_quantity
                position.realized_pnl += realized_pnl
                position.total_pnl = position.realized_pnl
                
                # Update cash balance
                self.cash_balance += old_quantity * price
                
                logger.info(f"📈 Position closed: {symbol} P&L: {realized_pnl:+.2f}")
            else:
                # Update position
                if old_quantity == 0:
                    # New position
                    position.entry_price = price
                    position.cost_basis = abs(new_quantity) * price
                    position.entry_time = datetime.now()
                    position.status = PositionStatus.OPEN
                else:
                    # Existing position - calculate weighted average price
                    total_cost = position.cost_basis + abs(quantity_change) * price
                    position.cost_basis = total_cost
                    if new_quantity != 0:
                        position.entry_price = total_cost / abs(new_quantity)
                
                position.quantity = new_quantity
                position.position_type = PositionType.LONG if new_quantity > 0 else PositionType.SHORT
                
                # Update cash balance
                self.cash_balance -= quantity_change * price
            
            # Update position values
            position.current_price = price
            position.last_update = datetime.now()
            await self._calculate_position_pnl(position)
            
            # Store updated position
            self.positions[symbol] = position
            
            # Notify subscribers
            for subscriber in self.subscribers:
                await subscriber.on_position_update(position)
            
            # Update portfolio metrics
            await self._update_portfolio_metrics()
            
            logger.info(f"✅ Position updated: {symbol} qty={position.quantity} P&L={position.total_pnl:+.2f}")
            return position
            
        except Exception as e:
            logger.error(f"❌ Position update failed for {symbol}: {e}")
            raise
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)
    
    async def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
    
    async def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash_balance + positions_value
    
    async def get_portfolio_pnl(self) -> Dict[str, float]:
        """Get portfolio P&L breakdown"""
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_realized = sum(pos.realized_pnl for pos in self.positions.values())
        total_pnl = total_unrealized + total_realized
        
        return {
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_pnl,
            'return_percentage': (total_pnl / self.initial_capital) * 100
        }
    
    async def get_portfolio_exposure(self) -> Dict[str, float]:
        """Get portfolio exposure metrics"""
        long_exposure = sum(
            pos.market_value for pos in self.positions.values() 
            if pos.position_type == PositionType.LONG and pos.status == PositionStatus.OPEN
        )
        short_exposure = sum(
            abs(pos.market_value) for pos in self.positions.values() 
            if pos.position_type == PositionType.SHORT and pos.status == PositionStatus.OPEN
        )
        
        net_exposure = long_exposure - short_exposure
        gross_exposure = long_exposure + short_exposure
        portfolio_value = await self.get_portfolio_value()
        
        return {
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_exposure': gross_exposure,
            'net_exposure_ratio': net_exposure / portfolio_value if portfolio_value > 0 else 0,
            'gross_exposure_ratio': gross_exposure / portfolio_value if portfolio_value > 0 else 0
        }
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get current portfolio performance metrics"""
        return self.current_metrics
    
    # Position Management Methods
    async def _get_or_create_position(self, symbol: str, strategy: str) -> Position:
        """Get existing position or create new one"""
        if symbol in self.positions:
            return self.positions[symbol]
        
        # Create new position
        position = Position(
            position_id=str(uuid.uuid4()),
            symbol=symbol,
            quantity=0.0,
            entry_price=0.0,
            current_price=0.0,
            position_type=PositionType.LONG,
            status=PositionStatus.OPEN,
            strategy=strategy,
            entry_time=datetime.now(),
            last_update=datetime.now()
        )
        
        return position
    
    async def _calculate_position_pnl(self, position: Position):
        """Calculate position P&L"""
        if position.quantity == 0:
            position.unrealized_pnl = 0.0
            position.market_value = 0.0
        else:
            # Calculate unrealized P&L
            if position.position_type == PositionType.LONG:
                position.unrealized_pnl = (position.current_price - position.entry_price) * position.quantity
                position.market_value = position.current_price * position.quantity
            else:  # SHORT
                position.unrealized_pnl = (position.entry_price - position.current_price) * abs(position.quantity)
                position.market_value = position.current_price * position.quantity
        
        # Total P&L includes both realized and unrealized
        position.total_pnl = position.realized_pnl + position.unrealized_pnl
    
    async def _update_market_prices(self):
        """Update market prices for all positions"""
        try:
            symbols = [symbol for symbol, pos in self.positions.items() if pos.status == PositionStatus.OPEN]
            
            if symbols and self.data_manager:
                # Get real-time prices
                for symbol in symbols:
                    try:
                        market_data = await self.data_manager.get_real_time_quote(symbol)
                        if market_data and 'price' in market_data:
                            self.market_prices[symbol] = market_data['price']
                            self.price_last_updated[symbol] = datetime.now()
                            
                            # Update position current price
                            if symbol in self.positions:
                                self.positions[symbol].current_price = market_data['price']
                                await self._calculate_position_pnl(self.positions[symbol])
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get price for {symbol}: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Market price update failed: {e}")
    
    # Portfolio Analytics Methods
    async def _run_pnl_calculation(self):
        """Run continuous P&L calculation"""
        logger.info("💰 Starting continuous P&L calculation...")
        
        while self.is_running:
            try:
                # Update market prices
                await self._update_market_prices()
                
                # Calculate portfolio P&L
                pnl_data = await self.get_portfolio_pnl()
                
                # Notify subscribers
                for subscriber in self.subscribers:
                    await subscriber.on_pnl_update(pnl_data)
                
                # Check for alerts
                await self._check_portfolio_alerts(pnl_data)
                
                # Create periodic snapshots
                if datetime.now().minute % 15 == 0:  # Every 15 minutes
                    await self._create_portfolio_snapshot()
                
                await asyncio.sleep(self.config.pnl_calculation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ P&L calculation error: {e}")
                await asyncio.sleep(30)
    
    async def _update_portfolio_metrics(self):
        """Update portfolio performance metrics"""
        try:
            # Calculate basic metrics
            portfolio_value = await self.get_portfolio_value()
            pnl_data = await self.get_portfolio_pnl()
            
            # Total return
            self.current_metrics.total_return = (portfolio_value - self.initial_capital) / self.initial_capital
            
            # Add current return to daily history
            current_return = pnl_data['total_pnl'] / self.initial_capital
            self.daily_pnl_history.append(current_return)
            
            # Keep only last 252 days (1 year)
            if len(self.daily_pnl_history) > 252:
                self.daily_pnl_history = self.daily_pnl_history[-252:]
            
            # Calculate advanced metrics if we have enough history
            if len(self.daily_pnl_history) > 30:
                returns = np.array(self.daily_pnl_history)
                
                # Volatility (annualized)
                self.current_metrics.volatility = np.std(returns) * np.sqrt(252)
                
                # Sharpe ratio (assuming 0% risk-free rate)
                if self.current_metrics.volatility > 0:
                    self.current_metrics.sharpe_ratio = (np.mean(returns) * 252) / self.current_metrics.volatility
                
                # Max drawdown
                cumulative_returns = np.cumprod(1 + returns)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdowns = (cumulative_returns - running_max) / running_max
                self.current_metrics.max_drawdown = np.min(drawdowns)
                
                # Calmar ratio
                if abs(self.current_metrics.max_drawdown) > 0:
                    self.current_metrics.calmar_ratio = self.current_metrics.total_return / abs(self.current_metrics.max_drawdown)
            
            # Calculate win rate from closed positions
            closed_positions = [pos for pos in self.positions.values() if pos.status == PositionStatus.CLOSED]
            if closed_positions:
                winning_trades = [pos for pos in closed_positions if pos.realized_pnl > 0]
                self.current_metrics.win_rate = len(winning_trades) / len(closed_positions)
                
                if winning_trades:
                    self.current_metrics.avg_win = np.mean([pos.realized_pnl for pos in winning_trades])
                
                losing_trades = [pos for pos in closed_positions if pos.realized_pnl < 0]
                if losing_trades:
                    self.current_metrics.avg_loss = np.mean([abs(pos.realized_pnl) for pos in losing_trades])
                
                # Profit factor
                total_wins = sum(pos.realized_pnl for pos in winning_trades)
                total_losses = abs(sum(pos.realized_pnl for pos in losing_trades))
                if total_losses > 0:
                    self.current_metrics.profit_factor = total_wins / total_losses
            
            self.current_metrics.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"❌ Portfolio metrics update failed: {e}")
    
    async def _create_portfolio_snapshot(self):
        """Create portfolio snapshot"""
        try:
            portfolio_value = await self.get_portfolio_value()
            pnl_data = await self.get_portfolio_pnl()
            exposure_data = await self.get_portfolio_exposure()
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(),
                total_value=portfolio_value,
                cash_balance=self.cash_balance,
                total_pnl=pnl_data['total_pnl'],
                unrealized_pnl=pnl_data['unrealized_pnl'],
                realized_pnl=pnl_data['realized_pnl'],
                position_count=len([pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]),
                long_exposure=exposure_data['long_exposure'],
                short_exposure=exposure_data['short_exposure'],
                net_exposure=exposure_data['net_exposure'],
                gross_exposure=exposure_data['gross_exposure'],
                positions=self.positions.copy()
            )
            
            self.portfolio_snapshots.append(snapshot)
            self.current_snapshot = snapshot
            
            # Keep only last 1000 snapshots
            if len(self.portfolio_snapshots) > 1000:
                self.portfolio_snapshots = self.portfolio_snapshots[-1000:]
            
            logger.debug(f"📊 Portfolio snapshot created: Value={portfolio_value:.2f} P&L={pnl_data['total_pnl']:+.2f}")
            
        except Exception as e:
            logger.error(f"❌ Portfolio snapshot creation failed: {e}")
    
    async def _check_portfolio_alerts(self, pnl_data: Dict[str, float]):
        """Check for portfolio alerts"""
        try:
            # Drawdown alert
            if abs(pnl_data['return_percentage']) > self.config.drawdown_alert_threshold * 100:
                alert = {
                    'type': 'drawdown',
                    'message': f"Portfolio drawdown: {pnl_data['return_percentage']:.2f}%",
                    'severity': 'high' if abs(pnl_data['return_percentage']) > 10 else 'medium',
                    'timestamp': datetime.now(),
                    'data': pnl_data
                }
                
                # Notify subscribers
                for subscriber in self.subscribers:
                    await subscriber.on_portfolio_alert(alert)
                    
        except Exception as e:
            logger.error(f"❌ Portfolio alert check failed: {e}")
    
    async def _create_initial_snapshot(self):
        """Create initial portfolio snapshot"""
        await self._create_portfolio_snapshot()
        logger.info("📊 Initial portfolio snapshot created")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive portfolio status"""
        open_positions = [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
        closed_positions = [pos for pos in self.positions.values() if pos.status == PositionStatus.CLOSED]
        
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'cash_balance': self.cash_balance,
            'initial_capital': self.initial_capital,
            'total_positions': len(self.positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'portfolio_snapshots': len(self.portfolio_snapshots),
            'metrics_updated': self.current_metrics.last_updated,
            'components_linked': {
                'risk_manager': self.risk_manager is not None,
                'data_manager': self.data_manager is not None
            }
        }