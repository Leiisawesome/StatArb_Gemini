#!/usr/bin/env python3
"""
PortfolioManager: Portfolio Tracking and Performance Management (DELEGATION ARCHITECTURE)
========================================================================================

Final component in the essential flow: Market Data -> UnifiedDataManager -> UnifiedRegimeEngine -> RiskManager -> StrategyManager -> RealTimeTradingEngine -> UnifiedExecutionEngine -> **PortfolioManager**

This manager orchestrates portfolio tracking and performance calculation by delegating
to existing sophisticated functional components instead of implementing redundant functionality.

DELEGATION ARCHITECTURE:
========================
✅ Portfolio Optimization -> PortfolioOptimizationEngine (730 lines of sophisticated optimization)
✅ Performance Metrics -> CoreAnalytics (1150 lines with vectorized calculations)
✅ Performance Monitoring -> MonitoringAnalytics (comprehensive performance tracking)
✅ Position Management -> Existing portfolio components

Key Features:
- Portfolio performance tracking via delegation
- Position consolidation through existing components
- P&L calculation using CoreAnalytics
- Performance metrics via sophisticated existing engines
- Integration with SystemOrchestrator

Author: Professional Trading System Architecture  
Version: 2.0.0 (Delegation Architecture - Eliminates Redundancy)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

# Import existing sophisticated components for delegation
try:
    from .components.signal_generation.optimization.portfolio_optimizer import (
        PortfolioOptimizationEngine, OptimizationConfig
    )
    from .analytics.core_analytics import CoreAnalytics
    from .analytics.monitoring_analytics import MonitoringAnalytics
    from .components.portfolio.portfolio_manager import PositionMetrics
    DELEGATION_IMPORTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"⚠️ Delegation imports not available: {e}")
    DELEGATION_IMPORTS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics"""
    total_return: float = 0.0
    daily_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    current_streak: int = 0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0

@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot at a point in time"""
    timestamp: datetime
    total_value: float
    cash: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    total_pnl: float
    exposure: float
    leverage: float
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class PortfolioConfig:
    """Configuration for portfolio management"""
    initial_capital: float = 1000000.0  # $1M initial capital
    max_leverage: float = 2.0  # 2x maximum leverage
    performance_calculation_frequency: int = 60  # seconds
    snapshot_retention_days: int = 365  # Keep snapshots for 1 year
    benchmark_symbol: str = "SPY"  # Benchmark for comparison
    
    # Risk limits
    max_daily_loss: float = 0.02  # 2% max daily loss
    max_position_concentration: float = 0.10  # 10% max per position
    margin_call_threshold: float = 0.25  # 25% equity threshold

class IPortfolioSubscriber(ABC):
    """Interface for portfolio subscribers"""
    
    @abstractmethod
    def on_portfolio_update(self, snapshot: PortfolioSnapshot) -> None:
        """Handle portfolio updates"""
        pass
    
    @abstractmethod
    def on_performance_update(self, metrics: PerformanceMetrics) -> None:
        """Handle performance updates"""
        pass

class PortfolioManager:
    """
    Portfolio manager that orchestrates portfolio tracking by delegating to existing
    sophisticated functional components instead of implementing redundant functionality.
    
    DELEGATION ARCHITECTURE:
    - Portfolio Optimization -> PortfolioOptimizationEngine (730 lines)
    - Performance Metrics -> CoreAnalytics (1150 lines with vectorized calculations)
    - Performance Monitoring -> MonitoringAnalytics (comprehensive tracking)
    """
    
    def __init__(self, config: Optional[PortfolioConfig] = None):
        """Initialize the portfolio manager with delegation to existing components"""
        self.config = config or PortfolioConfig()
        
        # Portfolio state (basic tracking only - complex calculations delegated)
        self.current_cash = self.config.initial_capital
        self.initial_capital = self.config.initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trades: List[Dict[str, Any]] = []
        
        # Delegate complex functionality to existing sophisticated components
        self._initialize_delegation_components()
        
        # Performance tracking state
        self.snapshots: List[PortfolioSnapshot] = []
        self.performance_metrics = PerformanceMetrics()
        
        # Market data for pricing
        self.market_prices: Dict[str, float] = {}
        
        # Subscribers
        self.subscribers: List[IPortfolioSubscriber] = []
        
        # State
        self.is_running = False
        self.performance_calculation_task: Optional[asyncio.Task] = None
        
        logger.info("💼 PortfolioManager initialized with delegation architecture")
    
    def _initialize_delegation_components(self) -> None:
        """Initialize sophisticated functional components for delegation"""
        try:
            if DELEGATION_IMPORTS_AVAILABLE:
                # Portfolio optimization engine (730 lines of sophisticated optimization)
                optimization_config = OptimizationConfig()
                self.portfolio_optimizer = PortfolioOptimizationEngine(optimization_config)
                
                # Core analytics engine (1150 lines with vectorized calculations)
                self.core_analytics = CoreAnalytics()
                
                # Monitoring analytics for performance tracking
                self.monitoring_analytics = MonitoringAnalytics()
                
                logger.info("✅ Sophisticated delegation components initialized successfully")
                logger.info("   📊 PortfolioOptimizationEngine: 730 lines of optimization logic")
                logger.info("   📈 CoreAnalytics: 1150 lines with vectorized calculations")
                logger.info("   🔍 MonitoringAnalytics: Comprehensive performance tracking")
            else:
                logger.warning("⚠️ Delegation components not available - using fallback implementations")
                self.portfolio_optimizer = None
                self.core_analytics = None
                self.monitoring_analytics = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize delegation components: {e}")
            self.portfolio_optimizer = None
            self.core_analytics = None
            self.monitoring_analytics = None
    
    async def startup(self) -> bool:
        """Start the portfolio manager"""
        try:
            logger.info("🚀 Starting PortfolioManager with delegation architecture...")
            
            # Sophisticated analytical components are already initialized and ready to use
            # No startup required for CoreAnalyticsEngine and MonitoringAnalyticsEngine
            logger.info("✅ Analytics engines ready for operation")
            
            # Create initial snapshot
            initial_snapshot = PortfolioSnapshot(
                timestamp=datetime.now(),
                total_value=self.initial_capital,
                cash=self.current_cash,
                positions_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                daily_pnl=0.0,
                total_pnl=0.0,
                exposure=0.0,
                leverage=0.0
            )
            self.snapshots.append(initial_snapshot)
            
            # Start performance calculation using delegation
            self.performance_calculation_task = asyncio.create_task(self._performance_calculation_loop())
            self.is_running = True
            
            logger.info("✅ PortfolioManager started successfully with delegation architecture")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start PortfolioManager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the portfolio manager"""
        try:
            logger.info("🛑 Shutting down PortfolioManager...")
            
            self.is_running = False
            
            if self.performance_calculation_task:
                self.performance_calculation_task.cancel()
                try:
                    await self.performance_calculation_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown delegated components
            if self.core_analytics:
                await self.core_analytics.shutdown()
            if self.monitoring_analytics:
                await self.monitoring_analytics.shutdown()
            
            logger.info("✅ PortfolioManager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to shutdown PortfolioManager: {e}")
    
    def subscribe(self, subscriber: IPortfolioSubscriber) -> None:
        """Subscribe to portfolio updates"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"📡 New portfolio subscriber added: {type(subscriber).__name__}")
    
    def unsubscribe(self, subscriber: IPortfolioSubscriber) -> None:
        """Unsubscribe from portfolio updates"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"📡 Portfolio subscriber removed: {type(subscriber).__name__}")
    
    # ================================================================================
    # REAL-TIME POSITION VALIDATION - INSTITUTIONAL RISK INTEGRATION
    # ================================================================================
    
    async def validate_trade_against_positions(self, trade_request) -> Dict[str, Any]:
        """
        Pre-execution position validation for institutional risk management
        
        This validates proposed trades against current portfolio state BEFORE execution,
        ensuring position limits and portfolio constraints are respected.
        """
        try:
            symbol = trade_request.symbol
            side = trade_request.side
            quantity = trade_request.quantity
            price = trade_request.price or self.market_prices.get(symbol, 100.0)
            
            # Calculate current portfolio value
            portfolio_value = self.get_portfolio_value()
            if portfolio_value <= 0:
                return {
                    'valid': False,
                    'reason': 'Portfolio value is zero or negative',
                    'current_portfolio_value': portfolio_value
                }
            
            # Get current position
            current_position = self.positions.get(symbol, {})
            current_quantity = current_position.get('quantity', 0.0)
            
            # Calculate proposed new position
            if side == 'BUY':
                new_quantity = current_quantity + quantity
            else:  # SELL
                new_quantity = current_quantity - quantity
            
            # Calculate position value and weight
            new_position_value = abs(new_quantity * price)
            position_weight = new_position_value / portfolio_value
            
            # Check position concentration limits (10% max per position)
            max_position_weight = 0.10
            if position_weight > max_position_weight:
                return {
                    'valid': False,
                    'reason': f'Position concentration limit exceeded: {position_weight:.1%} > {max_position_weight:.1%}',
                    'current_weight': position_weight,
                    'max_weight': max_position_weight,
                    'recommended_quantity': (portfolio_value * max_position_weight) / price
                }
            
            # Check if trade would create excessive portfolio turnover
            trade_value = quantity * price
            cash_available = self.current_cash
            
            if side == 'BUY' and trade_value > cash_available * 1.1:  # 10% buffer
                return {
                    'valid': False,
                    'reason': f'Insufficient cash for trade: {trade_value:.2f} > {cash_available:.2f}',
                    'cash_available': cash_available,
                    'trade_value': trade_value
                }
            
            # Check for position flipping (BUY when short, SELL when long) size limits
            if ((current_quantity > 0 and side == 'SELL' and quantity > current_quantity * 1.5) or
                (current_quantity < 0 and side == 'BUY' and quantity > abs(current_quantity) * 1.5)):
                return {
                    'valid': False,
                    'reason': 'Position flip size exceeds 150% of current position',
                    'current_quantity': current_quantity,
                    'proposed_quantity': quantity
                }
            
            # Calculate impact on portfolio diversification
            total_positions = len([p for p in self.positions.values() if p['quantity'] != 0])
            if total_positions < 3 and new_position_value > portfolio_value * 0.3:
                return {
                    'valid': False,
                    'reason': 'Insufficient diversification - position too large for current portfolio size',
                    'total_positions': total_positions,
                    'position_weight': position_weight
                }
            
            # All validations passed
            return {
                'valid': True,
                'reason': 'Position validation passed',
                'new_position_quantity': new_quantity,
                'new_position_value': new_position_value,
                'position_weight': position_weight,
                'portfolio_value': portfolio_value,
                'metadata': {
                    'validation_timestamp': datetime.now().isoformat(),
                    'current_positions': total_positions,
                    'cash_remaining_after_trade': cash_available - (trade_value if side == 'BUY' else -trade_value)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Position validation error for {trade_request.symbol}: {e}")
            return {
                'valid': False,
                'reason': f'Position validation system error: {str(e)}',
                'error': str(e)
            }
    
    def get_position_limits_info(self) -> Dict[str, Any]:
        """Get current position limits and utilization"""
        portfolio_value = self.get_portfolio_value()
        position_count = len([p for p in self.positions.values() if p['quantity'] != 0])
        
        # Calculate current concentration
        largest_position_value = 0.0
        if self.positions and portfolio_value > 0:
            largest_position_value = max(
                abs(pos.get('market_value', 0)) for pos in self.positions.values()
            )
        
        concentration_ratio = largest_position_value / portfolio_value if portfolio_value > 0 else 0.0
        
        return {
            'portfolio_value': portfolio_value,
            'position_count': position_count,
            'largest_position_value': largest_position_value,
            'concentration_ratio': concentration_ratio,
            'max_position_weight': 0.10,  # 10% max
            'diversification_threshold': 3,  # minimum positions for concentration rules
            'cash_available': self.current_cash,
            'limits_utilization': {
                'concentration_used': concentration_ratio,
                'concentration_limit': 0.10,
                'concentration_available': max(0.0, 0.10 - concentration_ratio)
            }
        }
    
    def update_position(self, symbol: str, quantity: float, avg_price: float, 
                       market_price: float, trade_pnl: float = 0.0) -> None:
        """Update position information (basic tracking - complex calculations delegated)"""
        try:
            # Update market price
            self.market_prices[symbol] = market_price
            
            # Update position (basic tracking)
            if symbol not in self.positions:
                self.positions[symbol] = {
                    "quantity": 0.0,
                    "avg_price": 0.0,
                    "market_value": 0.0,
                    "unrealized_pnl": 0.0,
                    "last_update": datetime.now()
                }
            
            position = self.positions[symbol]
            old_quantity = position["quantity"]
            
            # Update position data
            position["quantity"] = quantity
            position["avg_price"] = avg_price
            position["market_value"] = quantity * market_price
            position["unrealized_pnl"] = (market_price - avg_price) * quantity
            position["last_update"] = datetime.now()
            
            # Track realized P&L if position was closed/reduced
            if abs(quantity) < abs(old_quantity):
                closed_quantity = old_quantity - quantity
                realized_pnl = closed_quantity * (market_price - position["avg_price"])
                
                # Record trade for sophisticated analytics
                trade_data = {
                    "symbol": symbol,
                    "quantity": closed_quantity,
                    "entry_price": position["avg_price"],
                    "exit_price": market_price,
                    "pnl": realized_pnl,
                    "timestamp": datetime.now()
                }
                self.trades.append(trade_data)
                
                # Delegate trade analysis to sophisticated analytics
                if self.core_analytics:
                    self.core_analytics.process_trade(trade_data)
            
            # Remove position if quantity is zero
            if quantity == 0:
                self.positions.pop(symbol, None)
            
            logger.info(f"📊 Position updated: {symbol} - {quantity} @ {avg_price}")
            
        except Exception as e:
            logger.error(f"❌ Error updating position for {symbol}: {e}")
    
    def update_cash(self, amount: float, description: str = "") -> None:
        """Update cash balance"""
        try:
            self.current_cash += amount
            logger.info(f"💰 Cash updated: {amount:+.2f} - {description}")
            
        except Exception as e:
            logger.error(f"❌ Error updating cash: {e}")
    
    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """Update market prices for all positions"""
        try:
            self.market_prices.update(prices)
            
            # Update position values (basic calculations)
            for symbol, position in self.positions.items():
                if symbol in prices:
                    market_price = prices[symbol]
                    position["market_value"] = position["quantity"] * market_price
                    position["unrealized_pnl"] = (market_price - position["avg_price"]) * position["quantity"]
            
            # Delegate sophisticated market data analysis to existing components
            if self.core_analytics:
                self.core_analytics.process_market_data(prices)
            
        except Exception as e:
            logger.error(f"❌ Error updating market prices: {e}")
    
    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value (basic calculation - sophisticated metrics delegated)"""
        try:
            positions_value = sum(pos["market_value"] for pos in self.positions.values())
            total_value = self.current_cash + positions_value
            
            # Delegate sophisticated portfolio valuation to existing analytics
            if self.core_analytics:
                detailed_valuation = self.core_analytics.calculate_portfolio_value(
                    cash=self.current_cash,
                    positions=self.positions,
                    market_prices=self.market_prices
                )
                return detailed_valuation.get('total_value', total_value)
            
            return total_value
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio value: {e}")
            return self.current_cash
    
    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L (delegated to sophisticated analytics)"""
        try:
            if self.core_analytics:
                return self.core_analytics.calculate_unrealized_pnl(
                    positions=self.positions,
                    market_prices=self.market_prices
                )
            else:
                # Fallback basic calculation
                return sum(pos["unrealized_pnl"] for pos in self.positions.values())
            
        except Exception as e:
            logger.error(f"❌ Error calculating unrealized P&L: {e}")
            return 0.0
    
    def get_realized_pnl(self) -> float:
        """Calculate total realized P&L (delegated to sophisticated analytics)"""
        try:
            if self.core_analytics:
                return self.core_analytics.calculate_realized_pnl(trades=self.trades)
            else:
                # Fallback basic calculation
                return sum(trade["pnl"] for trade in self.trades)
            
        except Exception as e:
            logger.error(f"❌ Error calculating realized P&L: {e}")
            return 0.0
    
    def get_exposure(self) -> float:
        """Calculate total portfolio exposure (delegated to portfolio optimizer)"""
        try:
            if self.portfolio_optimizer:
                return self.portfolio_optimizer.calculate_exposure(
                    positions=self.positions,
                    market_prices=self.market_prices
                )
            else:
                # Fallback basic calculation
                return sum(abs(pos["market_value"]) for pos in self.positions.values())
            
        except Exception as e:
            logger.error(f"❌ Error calculating exposure: {e}")
            return 0.0
    
    def get_leverage(self) -> float:
        """Calculate current leverage (delegated to sophisticated analytics)"""
        try:
            if self.core_analytics:
                return self.core_analytics.calculate_leverage(
                    portfolio_value=self.get_portfolio_value(),
                    exposure=self.get_exposure()
                )
            else:
                # Fallback basic calculation
                portfolio_value = self.get_portfolio_value()
                if portfolio_value <= 0:
                    return 0.0
                exposure = self.get_exposure()
                return exposure / portfolio_value
            
        except Exception as e:
            logger.error(f"❌ Error calculating leverage: {e}")
            return 0.0
    
    def create_snapshot(self) -> PortfolioSnapshot:
        """Create current portfolio snapshot using delegated calculations"""
        try:
            # Use delegated sophisticated calculations instead of direct implementation
            portfolio_value = self.get_portfolio_value()
            positions_value = sum(pos["market_value"] for pos in self.positions.values())
            unrealized_pnl = self.get_unrealized_pnl()
            realized_pnl = self.get_realized_pnl()
            total_pnl = portfolio_value - self.initial_capital
            
            # Calculate daily P&L using sophisticated analytics
            daily_pnl = 0.0
            if self.core_analytics and len(self.snapshots) > 0:
                daily_pnl = self.core_analytics.calculate_daily_pnl(
                    current_value=portfolio_value,
                    previous_value=self.snapshots[-1].total_value
                )
            elif len(self.snapshots) > 0:
                yesterday_value = self.snapshots[-1].total_value
                daily_pnl = portfolio_value - yesterday_value
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.now(),
                total_value=portfolio_value,
                cash=self.current_cash,
                positions_value=positions_value,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                daily_pnl=daily_pnl,
                total_pnl=total_pnl,
                exposure=self.get_exposure(),
                leverage=self.get_leverage()
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Error creating portfolio snapshot: {e}")
            return PortfolioSnapshot(
                timestamp=datetime.now(),
                total_value=self.current_cash,
                cash=self.current_cash,
                positions_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                daily_pnl=0.0,
                total_pnl=0.0,
                exposure=0.0,
                leverage=0.0
            )
    
    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics via delegation to sophisticated analytics"""
        try:
            if self.core_analytics and len(self.snapshots) >= 2:
                # Delegate sophisticated performance calculations to existing analytics (1150 lines)
                performance_data = self.core_analytics.calculate_performance_metrics(
                    snapshots=self.snapshots,
                    trades=self.trades,
                    initial_capital=self.initial_capital
                )
                
                # Convert to PerformanceMetrics format
                return PerformanceMetrics(
                    total_return=performance_data.get('total_return', 0.0),
                    daily_return=performance_data.get('daily_return', 0.0),
                    volatility=performance_data.get('volatility', 0.0),
                    sharpe_ratio=performance_data.get('sharpe_ratio', 0.0),
                    max_drawdown=performance_data.get('max_drawdown', 0.0),
                    win_rate=performance_data.get('win_rate', 0.0),
                    profit_factor=performance_data.get('profit_factor', 0.0),
                    total_trades=performance_data.get('total_trades', 0),
                    winning_trades=performance_data.get('winning_trades', 0),
                    losing_trades=performance_data.get('losing_trades', 0),
                    avg_win=performance_data.get('avg_win', 0.0),
                    avg_loss=performance_data.get('avg_loss', 0.0),
                    largest_win=performance_data.get('largest_win', 0.0),
                    largest_loss=performance_data.get('largest_loss', 0.0)
                )
            
            else:
                # Fallback for basic metrics if sophisticated analytics not available
                return self._calculate_basic_performance_metrics()
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance metrics: {e}")
            return PerformanceMetrics()
    
    def _calculate_basic_performance_metrics(self) -> PerformanceMetrics:
        """Fallback basic performance metrics calculation"""
        try:
            if len(self.snapshots) < 2:
                return PerformanceMetrics()
            
            # Basic calculations for fallback
            values = [s.total_value for s in self.snapshots]
            returns = []
            for i in range(1, len(values)):
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)
            
            if not returns:
                return PerformanceMetrics()
            
            # Basic metrics
            total_return = (values[-1] - values[0]) / values[0]
            daily_return = np.mean(returns) if returns else 0.0
            volatility = np.std(returns) if len(returns) > 1 else 0.0
            
            # Trade statistics
            winning_trades = len([t for t in self.trades if t["pnl"] > 0])
            losing_trades = len([t for t in self.trades if t["pnl"] < 0])
            total_trades = len(self.trades)
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            return PerformanceMetrics(
                total_return=total_return,
                daily_return=daily_return,
                volatility=volatility,
                win_rate=win_rate,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades
            )
            
        except Exception as e:
            logger.error(f"❌ Error in basic performance calculation: {e}")
            return PerformanceMetrics()
    
    async def _performance_calculation_loop(self) -> None:
        """Main performance calculation loop using delegation"""
        while self.is_running:
            try:
                # Create snapshot
                snapshot = self.create_snapshot()
                self.snapshots.append(snapshot)
                
                # Calculate performance metrics via delegation to sophisticated analytics
                self.performance_metrics = self.calculate_performance_metrics()
                
                # Delegate monitoring to sophisticated monitoring analytics
                if self.monitoring_analytics:
                    await self.monitoring_analytics.process_portfolio_snapshot(snapshot)
                    await self.monitoring_analytics.process_performance_metrics(self.performance_metrics)
                
                # Maintain snapshot history
                cutoff_date = datetime.now() - timedelta(days=self.config.snapshot_retention_days)
                self.snapshots = [s for s in self.snapshots if s.timestamp > cutoff_date]
                
                # Notify subscribers
                await self._notify_portfolio_subscribers(snapshot)
                await self._notify_performance_subscribers(self.performance_metrics)
                
                await asyncio.sleep(self.config.performance_calculation_frequency)
                
            except asyncio.CancelledError:
                logger.info("💼 Performance calculation loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in performance calculation loop: {e}")
                await asyncio.sleep(1)
    
    async def _notify_portfolio_subscribers(self, snapshot: PortfolioSnapshot) -> None:
        """Notify subscribers of portfolio updates"""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_portfolio_update'):
                    if asyncio.iscoroutinefunction(subscriber.on_portfolio_update):
                        await subscriber.on_portfolio_update(snapshot)
                    else:
                        subscriber.on_portfolio_update(snapshot)
            except Exception as e:
                logger.error(f"❌ Error notifying portfolio subscriber {type(subscriber).__name__}: {e}")
    
    async def _notify_performance_subscribers(self, metrics: PerformanceMetrics) -> None:
        """Notify subscribers of performance updates"""
        for subscriber in self.subscribers:
            try:
                if hasattr(subscriber, 'on_performance_update'):
                    if asyncio.iscoroutinefunction(subscriber.on_performance_update):
                        await subscriber.on_performance_update(metrics)
                    else:
                        subscriber.on_performance_update(metrics)
            except Exception as e:
                logger.error(f"❌ Error notifying performance subscriber {type(subscriber).__name__}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current portfolio status using delegated calculations"""
        snapshot = self.create_snapshot()
        
        status = {
            "is_running": self.is_running,
            "total_value": snapshot.total_value,
            "cash": snapshot.cash,
            "positions_value": snapshot.positions_value,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "realized_pnl": snapshot.realized_pnl,
            "daily_pnl": snapshot.daily_pnl,
            "total_pnl": snapshot.total_pnl,
            "exposure": snapshot.exposure,
            "leverage": snapshot.leverage,
            "positions_count": len(self.positions),
            "trades_count": len(self.trades),
            "snapshots_count": len(self.snapshots),
            "subscribers_count": len(self.subscribers),
            "performance": self.performance_metrics.__dict__,
            "positions": {symbol: {
                "quantity": pos["quantity"],
                "avg_price": pos["avg_price"],
                "market_value": pos["market_value"],
                "unrealized_pnl": pos["unrealized_pnl"]
            } for symbol, pos in self.positions.items()},
            
            # Delegation architecture status
            "delegation_architecture": {
                "portfolio_optimizer_available": self.portfolio_optimizer is not None,
                "core_analytics_available": self.core_analytics is not None,
                "monitoring_analytics_available": self.monitoring_analytics is not None,
                "sophisticated_components_active": DELEGATION_IMPORTS_AVAILABLE
            }
        }
        
        return status

# Factory function
def create_portfolio_manager(config: Optional[PortfolioConfig] = None) -> PortfolioManager:
    """Create a PortfolioManager instance with delegation architecture"""
    return PortfolioManager(config)

# Export for SystemOrchestrator integration
__all__ = [
    'PortfolioManager', 'PortfolioConfig', 'PerformanceMetrics', 'PortfolioSnapshot',
    'IPortfolioSubscriber', 'create_portfolio_manager'
]