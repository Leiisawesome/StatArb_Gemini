#!/usr/bin/env python3
"""
Unified Portfolio Bridge
========================

Bridge layer that ensures consistent portfolio management across
backtesting, paper trading, and live trading modes.

This eliminates the duplicate portfolio tracking systems and ensures
all systems use the core PortfolioManager for consistent P&L calculation.

Author: Pro Quant Desk Trader
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .portfolio_manager import PortfolioManager, Position, PortfolioMetrics
from ..execution.unified_execution_engine import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Trading mode for portfolio management"""
    BACKTESTING = "BACKTESTING"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"

@dataclass
class UnifiedPosition:
    """Unified position representation across all trading modes"""
    symbol: str
    strategy_id: str
    quantity: float
    avg_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    entry_time: datetime
    last_update: datetime
    
    # Mode-specific metadata
    position_id: Optional[str] = None
    execution_ids: List[str] = None

@dataclass
class PortfolioState:
    """Complete portfolio state snapshot"""
    timestamp: datetime
    total_value: float
    cash_balance: float
    total_pnl: float
    positions: Dict[str, UnifiedPosition]  # symbol -> position
    strategy_allocations: Dict[str, float]  # strategy_id -> allocation
    
    # Performance metrics
    total_return_pct: float
    daily_pnl: float
    unrealized_pnl: float
    realized_pnl: float

class UnifiedPortfolioBridge:
    """
    Unified Portfolio Bridge
    
    Provides consistent portfolio management interface across all trading modes.
    Eliminates duplicate portfolio tracking and ensures consistent P&L calculations.
    
    Key Features:
    - Single source of truth for portfolio state
    - Consistent P&L calculation across all modes
    - Strategy-level position tracking
    - Real-time portfolio valuation
    - Performance attribution by strategy
    - Integration with unified execution engine
    """
    
    def __init__(self, 
                 initial_capital: float,
                 trading_mode: TradingMode,
                 strategy_allocations: Optional[Dict[str, float]] = None):
        
        self.initial_capital = initial_capital
        self.trading_mode = trading_mode
        self.strategy_allocations = strategy_allocations or {}
        
        # Core portfolio manager (single source of truth)
        self.portfolio_manager = PortfolioManager(initial_capital)
        
        # Strategy-level tracking
        self.strategy_positions: Dict[str, Dict[str, UnifiedPosition]] = {}  # strategy_id -> symbol -> position
        self.strategy_pnl: Dict[str, float] = {}
        self.strategy_capital: Dict[str, float] = {}
        
        # Initialize strategy capital allocation
        self._initialize_strategy_allocations()
        
        # Current market prices
        self.current_prices: Dict[str, float] = {}
        
        # Portfolio history for performance tracking
        self.portfolio_history: List[PortfolioState] = []
        
        logger.info(f"🏦 Unified Portfolio Bridge initialized - Mode: {trading_mode.value}, "
                   f"Capital: ${initial_capital:,.0f}")
    
    def _initialize_strategy_allocations(self):
        """Initialize strategy capital allocations"""
        
        total_allocation = sum(self.strategy_allocations.values())
        if total_allocation > 0:
            # Normalize allocations to sum to 1.0
            for strategy_id in self.strategy_allocations:
                self.strategy_allocations[strategy_id] /= total_allocation
                self.strategy_capital[strategy_id] = self.initial_capital * self.strategy_allocations[strategy_id]
                self.strategy_positions[strategy_id] = {}
                self.strategy_pnl[strategy_id] = 0.0
        
        logger.info(f"Strategy allocations initialized: {self.strategy_allocations}")
    
    def update_strategy_allocations(self, allocations: Dict[str, float]):
        """Update strategy allocations and rebalance capital"""
        
        # Normalize allocations
        total_allocation = sum(allocations.values())
        if total_allocation > 0:
            normalized_allocations = {k: v / total_allocation for k, v in allocations.items()}
        else:
            normalized_allocations = allocations
        
        self.strategy_allocations = normalized_allocations
        
        # Update capital allocations based on current portfolio value
        current_portfolio_value = self.get_total_portfolio_value()
        
        for strategy_id, allocation in normalized_allocations.items():
            self.strategy_capital[strategy_id] = current_portfolio_value * allocation
            if strategy_id not in self.strategy_positions:
                self.strategy_positions[strategy_id] = {}
                self.strategy_pnl[strategy_id] = 0.0
        
        logger.info(f"Strategy allocations updated: {normalized_allocations}")
    
    def update_market_prices(self, prices: Dict[str, float]):
        """Update current market prices for portfolio valuation"""
        
        self.current_prices.update(prices)
        
        # Update portfolio manager with new prices
        for symbol, price in prices.items():
            if symbol in self.portfolio_manager.positions:
                self.portfolio_manager.positions[symbol].update_market_value(price)
        
        # Update strategy positions
        for strategy_positions in self.strategy_positions.values():
            for symbol, position in strategy_positions.items():
                if symbol in prices:
                    position.current_price = prices[symbol]
                    position.market_value = position.quantity * prices[symbol]
                    position.unrealized_pnl = (prices[symbol] - position.avg_price) * position.quantity
                    position.total_pnl = position.realized_pnl + position.unrealized_pnl
                    position.last_update = datetime.now()
    
    async def process_execution_result(self, result: ExecutionResult, strategy_id: str) -> bool:
        """
        Process execution result and update portfolio state
        
        This is the single entry point for all trade processing,
        ensuring consistent portfolio updates across all trading modes.
        """
        
        try:
            if result.status != ExecutionStatus.FILLED:
                logger.warning(f"Skipping non-filled execution: {result.execution_id} - {result.status}")
                return False
            
            # Determine trade type from execution
            trade_type = "BUY" if result.executed_quantity > 0 else "SELL"
            quantity = abs(result.executed_quantity)
            symbol = result.request_id.split('_')[1] if '_' in result.request_id else "UNKNOWN"  # Extract from request_id
            
            # Process trade through core portfolio manager
            success = self.portfolio_manager.process_trade(
                symbol=symbol,
                quantity=quantity,
                price=result.executed_price,
                trade_type=trade_type,
                timestamp=result.execution_time
            )
            
            if not success:
                logger.error(f"Portfolio manager rejected trade: {result.execution_id}")
                return False
            
            # Update strategy-level tracking
            await self._update_strategy_position(strategy_id, symbol, quantity, 
                                               result.executed_price, trade_type, result)
            
            # Record execution costs
            await self._record_execution_costs(result, strategy_id)
            
            logger.info(f"✅ Portfolio updated: {trade_type} {quantity} {symbol} @ ${result.executed_price:.4f} "
                       f"(Strategy: {strategy_id}, Cost: {result.total_cost_bps:.2f}bps)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing execution result {result.execution_id}: {e}")
            return False
    
    async def _update_strategy_position(self, strategy_id: str, symbol: str, quantity: float,
                                      price: float, trade_type: str, result: ExecutionResult):
        """Update strategy-level position tracking"""
        
        # Ensure strategy exists
        if strategy_id not in self.strategy_positions:
            self.strategy_positions[strategy_id] = {}
            self.strategy_pnl[strategy_id] = 0.0
        
        # Get or create position
        if symbol not in self.strategy_positions[strategy_id]:
            self.strategy_positions[strategy_id][symbol] = UnifiedPosition(
                symbol=symbol,
                strategy_id=strategy_id,
                quantity=0.0,
                avg_price=0.0,
                current_price=self.current_prices.get(symbol, price),
                market_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                total_pnl=0.0,
                entry_time=datetime.now(),
                last_update=datetime.now(),
                position_id=f"{strategy_id}_{symbol}",
                execution_ids=[]
            )
        
        position = self.strategy_positions[strategy_id][symbol]
        
        # Update position based on trade type
        if trade_type == "BUY":
            # Calculate new average price
            if position.quantity == 0:
                position.avg_price = price
                position.entry_time = result.execution_time
            else:
                total_cost = (position.quantity * position.avg_price) + (quantity * price)
                position.avg_price = total_cost / (position.quantity + quantity)
            
            position.quantity += quantity
            
        else:  # SELL
            if quantity > position.quantity:
                logger.warning(f"Selling more than held: {quantity} > {position.quantity} for {symbol}")
                quantity = position.quantity
            
            # Calculate realized P&L
            realized_pnl = (price - position.avg_price) * quantity
            position.realized_pnl += realized_pnl
            self.strategy_pnl[strategy_id] += realized_pnl
            
            position.quantity -= quantity
            if position.quantity == 0:
                position.avg_price = 0.0
        
        # Update market value and unrealized P&L
        current_price = self.current_prices.get(symbol, price)
        position.current_price = current_price
        position.market_value = position.quantity * current_price
        position.unrealized_pnl = (current_price - position.avg_price) * position.quantity
        position.total_pnl = position.realized_pnl + position.unrealized_pnl
        position.last_update = datetime.now()
        
        # Record execution
        if not position.execution_ids:
            position.execution_ids = []
        position.execution_ids.append(result.execution_id)
    
    async def _record_execution_costs(self, result: ExecutionResult, strategy_id: str):
        """Record execution costs for performance attribution"""
        
        # Update strategy P&L with execution costs
        total_cost = result.commission + (result.total_cost_bps / 10000.0 * result.executed_quantity * result.executed_price)
        self.strategy_pnl[strategy_id] -= total_cost
        
        logger.debug(f"Execution costs recorded: ${total_cost:.2f} for {strategy_id}")
    
    def get_portfolio_state(self) -> PortfolioState:
        """Get complete current portfolio state"""
        
        timestamp = datetime.now()
        
        # Calculate total portfolio value
        total_value = self.get_total_portfolio_value()
        
        # Get cash balance from portfolio manager
        cash_balance = self.portfolio_manager.available_capital
        
        # Calculate total P&L
        total_pnl = total_value - self.initial_capital
        
        # Collect all positions
        unified_positions = {}
        for strategy_positions in self.strategy_positions.values():
            for symbol, position in strategy_positions.items():
                if position.quantity != 0:  # Only include non-zero positions
                    unified_positions[f"{position.strategy_id}_{symbol}"] = position
        
        # Calculate performance metrics
        total_return_pct = (total_value / self.initial_capital - 1) * 100
        daily_pnl = total_pnl  # Simplified - would need session tracking for accurate daily P&L
        
        # Calculate unrealized and realized P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in unified_positions.values())
        realized_pnl = sum(self.strategy_pnl.values())
        
        return PortfolioState(
            timestamp=timestamp,
            total_value=total_value,
            cash_balance=cash_balance,
            total_pnl=total_pnl,
            positions=unified_positions,
            strategy_allocations=self.strategy_allocations.copy(),
            total_return_pct=total_return_pct,
            daily_pnl=daily_pnl,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl
        )
    
    def get_total_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        
        # Get total market value from portfolio manager
        total_market_value = self.portfolio_manager.total_market_value
        available_cash = self.portfolio_manager.available_capital
        
        return total_market_value + available_cash
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics by strategy"""
        
        strategy_performance = {}
        
        for strategy_id in self.strategy_positions.keys():
            positions = self.strategy_positions[strategy_id]
            
            # Calculate strategy metrics
            strategy_pnl = self.strategy_pnl.get(strategy_id, 0.0)
            strategy_unrealized = sum(pos.unrealized_pnl for pos in positions.values())
            strategy_total_pnl = strategy_pnl + strategy_unrealized
            
            allocated_capital = self.strategy_capital.get(strategy_id, 0.0)
            strategy_return_pct = (strategy_total_pnl / allocated_capital * 100) if allocated_capital > 0 else 0.0
            
            strategy_performance[strategy_id] = {
                'allocated_capital': allocated_capital,
                'realized_pnl': strategy_pnl,
                'unrealized_pnl': strategy_unrealized,
                'total_pnl': strategy_total_pnl,
                'return_pct': strategy_return_pct,
                'position_count': len([p for p in positions.values() if p.quantity != 0]),
                'symbols': list(positions.keys())
            }
        
        return strategy_performance
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        
        all_positions = []
        for strategy_positions in self.strategy_positions.values():
            for position in strategy_positions.values():
                if position.quantity != 0:
                    all_positions.append({
                        'strategy_id': position.strategy_id,
                        'symbol': position.symbol,
                        'quantity': position.quantity,
                        'avg_price': position.avg_price,
                        'current_price': position.current_price,
                        'market_value': position.market_value,
                        'unrealized_pnl': position.unrealized_pnl,
                        'total_pnl': position.total_pnl,
                        'return_pct': (position.unrealized_pnl / (position.avg_price * position.quantity) * 100) if position.quantity > 0 else 0.0
                    })
        
        return {
            'positions': all_positions,
            'total_positions': len(all_positions),
            'total_market_value': sum(pos['market_value'] for pos in all_positions),
            'total_unrealized_pnl': sum(pos['unrealized_pnl'] for pos in all_positions)
        }
    
    def record_portfolio_snapshot(self):
        """Record current portfolio state for history tracking"""
        
        current_state = self.get_portfolio_state()
        self.portfolio_history.append(current_state)
        
        # Keep history manageable (last 1000 snapshots)
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-1000:]
    
    def get_portfolio_history(self, hours: int = 24) -> List[PortfolioState]:
        """Get portfolio history for specified time period"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [state for state in self.portfolio_history if state.timestamp >= cutoff_time]

# Factory function for easy creation
def create_unified_portfolio(initial_capital: float, 
                           trading_mode: TradingMode,
                           strategy_allocations: Optional[Dict[str, float]] = None) -> UnifiedPortfolioBridge:
    """Create unified portfolio bridge for specified mode"""
    return UnifiedPortfolioBridge(initial_capital, trading_mode, strategy_allocations)
