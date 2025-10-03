"""
Position Manager for Portfolio Component
Handles position tracking, lifecycle management, and position-level operations
"""
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import logging
import threading
from collections import defaultdict

class PositionType(Enum):
    """Types of positions"""
    LONG = "long"
    SHORT = "short"
    
class PositionStatus(Enum):
    """Position status"""
    PENDING = "pending"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"

@dataclass
class Position:
    """Individual position record"""
    symbol: str
    position_type: PositionType
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    entry_time: datetime
    strategy_id: str
    position_id: str = field(default_factory=lambda: f"pos_{datetime.now().timestamp()}")
    status: PositionStatus = PositionStatus.PENDING
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def market_value(self) -> Decimal:
        """Current market value of position"""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized P&L"""
        if self.position_type == PositionType.LONG:
            return self.quantity * (self.current_price - self.entry_price)
        else:
            return self.quantity * (self.entry_price - self.current_price)
    
    @property
    def unrealized_pnl_percent(self) -> Decimal:
        """Unrealized P&L as percentage"""
        if self.entry_price == 0:
            return Decimal('0')
        
        if self.position_type == PositionType.LONG:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:
            return ((self.entry_price - self.current_price) / self.entry_price) * 100
    
    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable"""
        return self.unrealized_pnl > 0
    
    def update_price(self, new_price: Decimal):
        """Update current price"""
        self.current_price = new_price
        self.last_update = datetime.now(timezone.utc)

@dataclass
class PositionSummary:
    """Summary of positions by symbol or strategy"""
    total_positions: int
    long_positions: int
    short_positions: int
    total_market_value: Decimal
    total_unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    largest_position: Optional[str] = None
    smallest_position: Optional[str] = None

class PositionManager:
    """
    Manages all trading positions with comprehensive tracking and analysis
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Position storage
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.positions_by_symbol: Dict[str, List[str]] = defaultdict(list)
        self.positions_by_strategy: Dict[str, List[str]] = defaultdict(list)
        
        # Position history
        self.closed_positions: List[Position] = []
        self.position_history: List[Dict[str, Any]] = []
        
        # Threading
        self.positions_lock = threading.RLock()
        
        # Metrics
        self.position_metrics = {
            'total_positions_opened': 0,
            'total_positions_closed': 0,
            'total_realized_pnl': Decimal('0'),
            'winning_positions': 0,
            'losing_positions': 0,
            'average_hold_time': 0,
            'largest_win': Decimal('0'),
            'largest_loss': Decimal('0')
        }
        
        # Risk limits
        self.max_positions_per_symbol = config.get('max_positions_per_symbol', 3)
        self.max_total_positions = config.get('max_total_positions', 100)
        
        self.logger.info("Position manager initialized")
    
    def open_position(self, symbol: str, position_type: PositionType, quantity: Decimal,
                     entry_price: Decimal, strategy_id: str, **kwargs) -> Optional[str]:
        """Open a new position"""
        try:
            with self.positions_lock:
                # Check position limits
                if not self._check_position_limits(symbol):
                    self.logger.warning(f"Position limits exceeded for {symbol}")
                    return None
                
                # Create position
                position = Position(
                    symbol=symbol,
                    position_type=position_type,
                    quantity=quantity,
                    entry_price=entry_price,
                    current_price=entry_price,
                    entry_time=datetime.now(timezone.utc),
                    strategy_id=strategy_id,
                    stop_loss=kwargs.get('stop_loss'),
                    take_profit=kwargs.get('take_profit'),
                    metadata=kwargs.get('metadata', {})
                )
                
                # Store position
                self.positions[position.position_id] = position
                self.positions_by_symbol[symbol].append(position.position_id)
                self.positions_by_strategy[strategy_id].append(position.position_id)
                
                # Update position status
                position.status = PositionStatus.OPEN
                
                # Update metrics
                self.position_metrics['total_positions_opened'] += 1
                
                # Log position opening
                self._log_position_event(position, 'OPENED')
                
                self.logger.info(f"Opened {position_type.value} position {position.position_id} "
                               f"for {symbol}: {quantity} @ {entry_price}")
                
                return position.position_id
                
        except Exception as e:
            self.logger.error(f"Error opening position for {symbol}: {e}")
            return None
    
    def close_position(self, position_id: str, exit_price: Decimal, 
                      close_reason: str = "manual") -> bool:
        """Close an existing position"""
        try:
            with self.positions_lock:
                if position_id not in self.positions:
                    self.logger.warning(f"Position {position_id} not found")
                    return False
                
                position = self.positions[position_id]
                
                if position.status != PositionStatus.OPEN:
                    self.logger.warning(f"Position {position_id} is not open (status: {position.status})")
                    return False
                
                # Update position for final P&L calculation
                position.current_price = exit_price
                position.status = PositionStatus.CLOSED
                
                # Calculate realized P&L
                realized_pnl = position.unrealized_pnl
                
                # Remove from active positions
                closed_position = self.positions.pop(position_id)
                
                # Remove from tracking lists
                self.positions_by_symbol[position.symbol].remove(position_id)
                self.positions_by_strategy[position.strategy_id].remove(position_id)
                
                # Add to closed positions
                self.closed_positions.append(closed_position)
                
                # Update metrics
                self._update_close_metrics(closed_position, realized_pnl)
                
                # Log position closing
                self._log_position_event(closed_position, 'CLOSED', {
                    'exit_price': exit_price,
                    'realized_pnl': realized_pnl,
                    'close_reason': close_reason
                })
                
                self.logger.info(f"Closed position {position_id} for {position.symbol} "
                               f"@ {exit_price}, P&L: {realized_pnl}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {e}")
            return False
    
    def update_position_prices(self, price_updates: Dict[str, Decimal]):
        """Update current prices for positions"""
        try:
            with self.positions_lock:
                updated_count = 0
                
                for symbol, price in price_updates.items():
                    position_ids = self.positions_by_symbol.get(symbol, [])
                    
                    for position_id in position_ids:
                        if position_id in self.positions:
                            self.positions[position_id].update_price(price)
                            updated_count += 1
                
                if updated_count > 0:
                    self.logger.debug(f"Updated prices for {updated_count} positions")
                
        except Exception as e:
            self.logger.error(f"Error updating position prices: {e}")
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get specific position"""
        with self.positions_lock:
            return self.positions.get(position_id)
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol"""
        with self.positions_lock:
            position_ids = self.positions_by_symbol.get(symbol, [])
            return [self.positions[pid] for pid in position_ids if pid in self.positions]
    
    def get_positions_by_strategy(self, strategy_id: str) -> List[Position]:
        """Get all positions for a strategy"""
        with self.positions_lock:
            position_ids = self.positions_by_strategy.get(strategy_id, [])
            return [self.positions[pid] for pid in position_ids if pid in self.positions]
    
    def get_all_positions(self) -> List[Position]:
        """Get all active positions"""
        with self.positions_lock:
            return list(self.positions.values())
    
    def get_position_summary(self, group_by: str = 'overall') -> Union[PositionSummary, Dict[str, PositionSummary]]:
        """Get position summary, optionally grouped by symbol or strategy"""
        with self.positions_lock:
            if group_by == 'overall':
                return self._calculate_overall_summary()
            elif group_by == 'symbol':
                return self._calculate_summary_by_symbol()
            elif group_by == 'strategy':
                return self._calculate_summary_by_strategy()
            else:
                raise ValueError(f"Invalid group_by parameter: {group_by}")
    
    def get_unrealized_pnl(self, group_by: str = 'overall') -> Union[Decimal, Dict[str, Decimal]]:
        """Get unrealized P&L, optionally grouped"""
        with self.positions_lock:
            if group_by == 'overall':
                return sum(pos.unrealized_pnl for pos in self.positions.values())
            elif group_by == 'symbol':
                result = {}
                for symbol, position_ids in self.positions_by_symbol.items():
                    pnl = sum(self.positions[pid].unrealized_pnl 
                             for pid in position_ids if pid in self.positions)
                    result[symbol] = pnl
                return result
            elif group_by == 'strategy':
                result = {}
                for strategy, position_ids in self.positions_by_strategy.items():
                    pnl = sum(self.positions[pid].unrealized_pnl 
                             for pid in position_ids if pid in self.positions)
                    result[strategy] = pnl
                return result
    
    def get_net_exposure(self, symbol: str = None) -> Union[Decimal, Dict[str, Decimal]]:
        """Get net exposure by symbol or overall"""
        with self.positions_lock:
            if symbol:
                positions = self.get_positions_by_symbol(symbol)
                net_exposure = Decimal('0')
                for pos in positions:
                    if pos.position_type == PositionType.LONG:
                        net_exposure += pos.market_value
                    else:
                        net_exposure -= pos.market_value
                return net_exposure
            else:
                exposures = {}
                for symbol in self.positions_by_symbol.keys():
                    exposures[symbol] = self.get_net_exposure(symbol)
                return exposures
    
    def check_stop_loss_take_profit(self) -> List[Dict[str, Any]]:
        """Check positions against stop loss and take profit levels"""
        alerts = []
        
        with self.positions_lock:
            for position in self.positions.values():
                # Check stop loss
                if position.stop_loss:
                    if ((position.position_type == PositionType.LONG and 
                         position.current_price <= position.stop_loss) or
                        (position.position_type == PositionType.SHORT and 
                         position.current_price >= position.stop_loss)):
                        alerts.append({
                            'type': 'stop_loss',
                            'position_id': position.position_id,
                            'symbol': position.symbol,
                            'current_price': position.current_price,
                            'stop_loss': position.stop_loss
                        })
                
                # Check take profit
                if position.take_profit:
                    if ((position.position_type == PositionType.LONG and 
                         position.current_price >= position.take_profit) or
                        (position.position_type == PositionType.SHORT and 
                         position.current_price <= position.take_profit)):
                        alerts.append({
                            'type': 'take_profit',
                            'position_id': position.position_id,
                            'symbol': position.symbol,
                            'current_price': position.current_price,
                            'take_profit': position.take_profit
                        })
        
        return alerts
    
    def _check_position_limits(self, symbol: str) -> bool:
        """Check if position limits allow new position"""
        # Check per-symbol limit
        if len(self.positions_by_symbol[symbol]) >= self.max_positions_per_symbol:
            return False
        
        # Check total positions limit
        if len(self.positions) >= self.max_total_positions:
            return False
        
        return True
    
    def _calculate_overall_summary(self) -> PositionSummary:
        """Calculate overall position summary"""
        positions = list(self.positions.values())
        
        if not positions:
            return PositionSummary(0, 0, 0, Decimal('0'), Decimal('0'), Decimal('0'))
        
        long_positions = sum(1 for p in positions if p.position_type == PositionType.LONG)
        short_positions = len(positions) - long_positions
        
        total_market_value = sum(abs(p.market_value) for p in positions)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        
        unrealized_pnl_percent = Decimal('0')
        if total_market_value > 0:
            unrealized_pnl_percent = (total_unrealized_pnl / total_market_value) * 100
        
        # Find largest and smallest positions by market value
        largest_pos = max(positions, key=lambda p: abs(p.market_value))
        smallest_pos = min(positions, key=lambda p: abs(p.market_value))
        
        return PositionSummary(
            total_positions=len(positions),
            long_positions=long_positions,
            short_positions=short_positions,
            total_market_value=total_market_value,
            total_unrealized_pnl=total_unrealized_pnl,
            unrealized_pnl_percent=unrealized_pnl_percent,
            largest_position=largest_pos.position_id,
            smallest_position=smallest_pos.position_id
        )
    
    def _calculate_summary_by_symbol(self) -> Dict[str, PositionSummary]:
        """Calculate position summary by symbol"""
        summaries = {}
        
        for symbol, position_ids in self.positions_by_symbol.items():
            positions = [self.positions[pid] for pid in position_ids if pid in self.positions]
            
            if positions:
                long_positions = sum(1 for p in positions if p.position_type == PositionType.LONG)
                short_positions = len(positions) - long_positions
                
                total_market_value = sum(abs(p.market_value) for p in positions)
                total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
                
                unrealized_pnl_percent = Decimal('0')
                if total_market_value > 0:
                    unrealized_pnl_percent = (total_unrealized_pnl / total_market_value) * 100
                
                summaries[symbol] = PositionSummary(
                    total_positions=len(positions),
                    long_positions=long_positions,
                    short_positions=short_positions,
                    total_market_value=total_market_value,
                    total_unrealized_pnl=total_unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent
                )
        
        return summaries
    
    def _calculate_summary_by_strategy(self) -> Dict[str, PositionSummary]:
        """Calculate position summary by strategy"""
        summaries = {}
        
        for strategy, position_ids in self.positions_by_strategy.items():
            positions = [self.positions[pid] for pid in position_ids if pid in self.positions]
            
            if positions:
                long_positions = sum(1 for p in positions if p.position_type == PositionType.LONG)
                short_positions = len(positions) - long_positions
                
                total_market_value = sum(abs(p.market_value) for p in positions)
                total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
                
                unrealized_pnl_percent = Decimal('0')
                if total_market_value > 0:
                    unrealized_pnl_percent = (total_unrealized_pnl / total_market_value) * 100
                
                summaries[strategy] = PositionSummary(
                    total_positions=len(positions),
                    long_positions=long_positions,
                    short_positions=short_positions,
                    total_market_value=total_market_value,
                    total_unrealized_pnl=total_unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent
                )
        
        return summaries
    
    def _update_close_metrics(self, position: Position, realized_pnl: Decimal):
        """Update metrics when closing a position"""
        self.position_metrics['total_positions_closed'] += 1
        self.position_metrics['total_realized_pnl'] += realized_pnl
        
        if realized_pnl > 0:
            self.position_metrics['winning_positions'] += 1
            if realized_pnl > self.position_metrics['largest_win']:
                self.position_metrics['largest_win'] = realized_pnl
        else:
            self.position_metrics['losing_positions'] += 1
            if realized_pnl < self.position_metrics['largest_loss']:
                self.position_metrics['largest_loss'] = realized_pnl
        
        # Calculate average hold time
        hold_time = (datetime.now(timezone.utc) - position.entry_time).total_seconds()
        current_avg = self.position_metrics['average_hold_time']
        total_closed = self.position_metrics['total_positions_closed']
        
        self.position_metrics['average_hold_time'] = (
            (current_avg * (total_closed - 1) + hold_time) / total_closed
        )
    
    def _log_position_event(self, position: Position, event_type: str, extra_data: Dict[str, Any] = None):
        """Log position events for audit trail"""
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'position_id': position.position_id,
            'symbol': position.symbol,
            'position_type': position.position_type.value,
            'quantity': float(position.quantity),
            'entry_price': float(position.entry_price),
            'current_price': float(position.current_price),
            'strategy_id': position.strategy_id
        }
        
        if extra_data:
            event.update(extra_data)
        
        self.position_history.append(event)
        
        # Limit history size
        if len(self.position_history) > 10000:
            self.position_history = self.position_history[-5000:]
    
    def get_position_metrics(self) -> Dict[str, Any]:
        """Get position management metrics"""
        with self.positions_lock:
            metrics = self.position_metrics.copy()
            
            # Add current state metrics
            metrics.update({
                'active_positions': len(self.positions),
                'positions_by_symbol': {k: len(v) for k, v in self.positions_by_symbol.items()},
                'positions_by_strategy': {k: len(v) for k, v in self.positions_by_strategy.items()},
                'total_unrealized_pnl': float(self.get_unrealized_pnl()),
                'win_rate': (self.position_metrics['winning_positions'] / 
                           max(1, self.position_metrics['total_positions_closed'])) * 100
            })
            
            return metrics
    
    def cleanup(self):
        """Cleanup position manager"""
        with self.positions_lock:
            # Close any remaining positions (for emergency shutdown)
            open_positions = list(self.positions.keys())
            for position_id in open_positions:
                position = self.positions[position_id]
                self.close_position(position_id, position.current_price, "system_shutdown")
        
        self.logger.info("Position manager cleaned up")