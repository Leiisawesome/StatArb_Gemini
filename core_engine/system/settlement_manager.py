"""
Settlement Manager - T+1/T+2 Settlement Tracking

Architecture Compliance (Tier-1 Rules):
- Rule 6: Operations & Recovery - Section 4 (Settlement Management)
  - T+1/T+2 settlement date calculation
  - Pending settlement tracking
  - Settlement failure detection and handling
  - Exposure calculation
  - Clearing integration (placeholder)

Key Responsibilities:
1. Track all pending settlements
2. Calculate settlement dates based on market calendar
3. Monitor for settlement failures
4. Calculate settlement exposure
5. Handle settlement failures with retry logic
6. Coordinate with clearing (future enhancement)

Integration Points:
- Rule 5 (Phase 15): Receives execution results via OMS
- Rule 6 (Reconciliation): Reports settlement status
- Rule 3 (Risk): Provides settlement exposure for risk calculations

Author: Trading System Team
Date: December 6, 2025
Version: 1.0 (Initial implementation per Rule 6, Section 4)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from collections import defaultdict

from .interfaces import ISystemComponent

logger = logging.getLogger(__name__)


class SettlementStatus(Enum):
    """Settlement lifecycle states per Rule 6"""
    PENDING = "pending"           # Trade executed, awaiting settlement
    MATCHED = "matched"           # Trade matched with counterparty
    AFFIRMED = "affirmed"         # Trade affirmed
    SETTLING = "settling"         # Settlement in progress
    SETTLED = "settled"           # Settlement complete
    FAILED = "failed"             # Settlement failed
    CANCELLED = "cancelled"       # Trade cancelled before settlement


class SettlementType(Enum):
    """Types of settlement"""
    REGULAR = "regular"           # Standard T+1/T+2
    CASH = "cash"                 # Same day (T+0)
    NEXT_DAY = "next_day"         # T+1
    EXTENDED = "extended"         # T+3 or longer


@dataclass
class SettlementRecord:
    """
    Settlement tracking record.
    
    Tracks a single trade from execution through settlement completion.
    """
    
    # Identity
    settlement_id: str
    execution_id: str
    order_id: str
    authorization_id: str = ""
    
    # Trade details
    symbol: str = ""
    side: str = ""  # 'buy' or 'sell'
    quantity: float = 0.0
    price: float = 0.0
    trade_date: date = field(default_factory=date.today)
    settlement_date: date = field(default_factory=date.today)
    settlement_type: SettlementType = SettlementType.REGULAR
    
    # Settlement state
    status: SettlementStatus = SettlementStatus.PENDING
    
    # Amounts
    gross_amount: float = 0.0
    net_amount: float = 0.0
    commission: float = 0.0
    fees: float = 0.0
    taxes: float = 0.0
    
    # Counterparty
    counterparty_id: Optional[str] = None
    clearing_broker: Optional[str] = None
    custodian: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    matched_at: Optional[datetime] = None
    affirmed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    
    # Failure tracking
    failure_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    strategy_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SettlementManager(ISystemComponent):
    """
    Settlement Manager for T+1/T+2 tracking.
    
    Implements Rule 6, Section 4: Settlement Management.
    
    Integrates with:
    - Rule 5 (Phase 15): Receives execution results
    - Rule 6 (Reconciliation): Reports settlement status
    - Rule 3 (Risk): Provides exposure data
    """
    
    # US Market holidays (simplified - should be loaded from calendar service)
    US_HOLIDAYS_2025: Set[date] = {
        date(2025, 1, 1),   # New Year's Day
        date(2025, 1, 20),  # MLK Day
        date(2025, 2, 17),  # Presidents Day
        date(2025, 4, 18),  # Good Friday
        date(2025, 5, 26),  # Memorial Day
        date(2025, 6, 19),  # Juneteenth
        date(2025, 7, 4),   # Independence Day
        date(2025, 9, 1),   # Labor Day
        date(2025, 11, 27), # Thanksgiving
        date(2025, 12, 25), # Christmas
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Settlement Manager.
        
        Args:
            config: Configuration including:
                - default_settlement_days: Default T+ days (default: 1 for T+1)
                - max_retries: Max retry attempts for failed settlements
                - failure_check_interval: Seconds between failure checks
        """
        self.config = config or {}
        
        # Settlement tracking
        self.pending_settlements: Dict[str, SettlementRecord] = {}
        self.settled_records: Dict[str, SettlementRecord] = {}  # Historical
        self.failed_settlements: Dict[str, SettlementRecord] = {}
        
        # Indices
        self.settlements_by_date: Dict[date, List[str]] = defaultdict(list)
        self.settlements_by_symbol: Dict[str, List[str]] = defaultdict(list)
        self.settlements_by_status: Dict[SettlementStatus, List[str]] = defaultdict(list)
        
        # Configuration
        self.default_settlement_days = self.config.get('default_settlement_days', 1)  # T+1
        self.max_retries = self.config.get('max_retries', 3)
        self.failure_check_interval = self.config.get('failure_check_interval', 3600)  # 1 hour
        
        # Market calendar
        self.holidays: Set[date] = self.US_HOLIDAYS_2025.copy()
        
        # Statistics
        self.stats = {
            'settlements_created': 0,
            'settlements_completed': 0,
            'settlements_failed': 0,
            'total_settled_value': 0.0,
            'pending_buy_exposure': 0.0,
            'pending_sell_exposure': 0.0
        }
        
        self._initialized = False
        self._running = False
        
        logger.info("SettlementManager initialized (Rule 6, Section 4)")
    
    # ===== ISystemComponent Implementation =====
    
    async def initialize(self) -> bool:
        """Initialize Settlement Manager"""
        try:
            # Load market calendar (placeholder)
            await self._load_market_calendar()
            
            self._initialized = True
            logger.info("Settlement Manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Settlement Manager initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start Settlement Manager operations"""
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        
        # Start background tasks
        asyncio.create_task(self._settlement_failure_monitor())
        asyncio.create_task(self._settlement_due_monitor())
        
        logger.info("Settlement Manager started")
        return True
    
    async def stop(self) -> bool:
        """Stop Settlement Manager"""
        self._running = False
        logger.info("Settlement Manager stopped")
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Settlement Manager health"""
        exposure = await self.get_settlement_exposure()
        
        return {
            'healthy': self._running,
            'pending_count': len(self.pending_settlements),
            'failed_count': len(self.failed_settlements),
            'exposure': exposure,
            'stats': self.stats
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Settlement Manager status"""
        return {
            'initialized': self._initialized,
            'running': self._running,
            'pending_settlements': len(self.pending_settlements),
            'stats': self.stats
        }
    
    # ===== Settlement Date Calculation =====
    
    def calculate_settlement_date(
        self, 
        trade_date: date, 
        symbol: str = None,
        settlement_type: SettlementType = SettlementType.REGULAR
    ) -> date:
        """
        Calculate settlement date based on trade date and instrument.
        
        Args:
            trade_date: Date of trade execution
            symbol: Trading symbol (for instrument-specific rules)
            settlement_type: Type of settlement
            
        Returns:
            Calculated settlement date
        """
        # Determine settlement days based on type
        if settlement_type == SettlementType.CASH:
            settlement_days = 0
        elif settlement_type == SettlementType.NEXT_DAY:
            settlement_days = 1
        elif settlement_type == SettlementType.EXTENDED:
            settlement_days = 3
        else:
            settlement_days = self.default_settlement_days
        
        # Add business days (skip weekends and holidays)
        current = trade_date
        days_added = 0
        
        while days_added < settlement_days:
            current += timedelta(days=1)
            if self._is_business_day(current):
                days_added += 1
        
        return current
    
    def _is_business_day(self, check_date: date) -> bool:
        """Check if date is a business day"""
        # Weekend check
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Holiday check
        if check_date in self.holidays:
            return False
        
        return True
    
    async def _load_market_calendar(self):
        """Load market calendar (placeholder for actual implementation)"""
        # In production, load from calendar service or database
        logger.info("Market calendar loaded")
    
    # ===== Settlement Tracking =====
    
    async def track_pending_settlement(
        self,
        execution_id: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        commission: float = 0.0,
        fees: float = 0.0,
        authorization_id: str = "",
        strategy_id: str = "",
        settlement_type: SettlementType = SettlementType.REGULAR
    ) -> SettlementRecord:
        """
        Create settlement tracking record after execution.
        
        Called by OMS (Rule 5, Phase 12) after order is filled.
        
        Args:
            execution_id: Execution ID from execution engine
            order_id: Order ID from OMS
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Trade quantity
            price: Execution price
            commission: Trading commission
            fees: Exchange/regulatory fees
            authorization_id: Original authorization ID
            strategy_id: Strategy that generated the trade
            settlement_type: Type of settlement
            
        Returns:
            Created SettlementRecord
        """
        trade_date = date.today()
        settlement_date = self.calculate_settlement_date(
            trade_date, symbol, settlement_type
        )
        
        # Calculate amounts
        gross = quantity * price
        net = gross + commission + fees if side == 'buy' else gross - commission - fees
        
        record = SettlementRecord(
            settlement_id=f"STL-{execution_id}",
            execution_id=execution_id,
            order_id=order_id,
            authorization_id=authorization_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            trade_date=trade_date,
            settlement_date=settlement_date,
            settlement_type=settlement_type,
            gross_amount=gross,
            net_amount=net,
            commission=commission,
            fees=fees,
            strategy_id=strategy_id,
            max_retries=self.max_retries
        )
        
        # Store record
        self.pending_settlements[record.settlement_id] = record
        self.settlements_by_date[settlement_date].append(record.settlement_id)
        self.settlements_by_symbol[symbol].append(record.settlement_id)
        self.settlements_by_status[SettlementStatus.PENDING].append(record.settlement_id)
        
        # Update stats
        self.stats['settlements_created'] += 1
        if side == 'buy':
            self.stats['pending_buy_exposure'] += net
        else:
            self.stats['pending_sell_exposure'] += net
        
        logger.info(
            f"📋 Settlement tracked: {record.settlement_id} "
            f"{symbol} {side} {quantity}@${price:.2f} "
            f"due {settlement_date}"
        )
        
        return record
    
    async def update_settlement_status(
        self,
        settlement_id: str,
        new_status: SettlementStatus,
        reason: str = None
    ) -> Optional[SettlementRecord]:
        """
        Update settlement status.
        
        Args:
            settlement_id: Settlement ID
            new_status: New status
            reason: Reason for status change
            
        Returns:
            Updated SettlementRecord or None if not found
        """
        record = self.pending_settlements.get(settlement_id)
        if not record:
            record = self.failed_settlements.get(settlement_id)
        if not record:
            logger.warning(f"Settlement not found: {settlement_id}")
            return None
        
        old_status = record.status
        record.status = new_status
        
        # Update timestamp based on status
        if new_status == SettlementStatus.MATCHED:
            record.matched_at = datetime.now()
        elif new_status == SettlementStatus.AFFIRMED:
            record.affirmed_at = datetime.now()
        elif new_status == SettlementStatus.SETTLED:
            record.settled_at = datetime.now()
        elif new_status == SettlementStatus.FAILED:
            record.failure_reason = reason
        
        # Move between collections based on status
        if new_status == SettlementStatus.SETTLED:
            if settlement_id in self.pending_settlements:
                del self.pending_settlements[settlement_id]
            self.settled_records[settlement_id] = record
            self.stats['settlements_completed'] += 1
            self.stats['total_settled_value'] += record.net_amount
            
            # Update exposure
            if record.side == 'buy':
                self.stats['pending_buy_exposure'] -= record.net_amount
            else:
                self.stats['pending_sell_exposure'] -= record.net_amount
        
        elif new_status == SettlementStatus.FAILED:
            if settlement_id in self.pending_settlements:
                del self.pending_settlements[settlement_id]
            self.failed_settlements[settlement_id] = record
            self.stats['settlements_failed'] += 1
        
        # Update status index
        if settlement_id in self.settlements_by_status.get(old_status, []):
            self.settlements_by_status[old_status].remove(settlement_id)
        self.settlements_by_status[new_status].append(settlement_id)
        
        logger.info(
            f"📝 Settlement status update: {settlement_id} "
            f"{old_status.value} → {new_status.value}"
        )
        
        return record
    
    async def confirm_settlement(self, settlement_id: str) -> Optional[SettlementRecord]:
        """
        Confirm settlement completion.
        
        Args:
            settlement_id: Settlement ID
            
        Returns:
            Updated SettlementRecord
        """
        return await self.update_settlement_status(
            settlement_id, 
            SettlementStatus.SETTLED, 
            'settlement_confirmed'
        )
    
    # ===== Exposure Calculation =====
    
    async def get_settlement_exposure(self) -> Dict[str, Any]:
        """
        Calculate total settlement exposure.
        
        Returns:
            Dictionary with exposure metrics
        """
        today = date.today()
        
        # Calculate fresh exposure from pending settlements
        buy_exposure = 0.0
        sell_exposure = 0.0
        due_today = 0
        overdue = 0
        
        for record in self.pending_settlements.values():
            if record.side == 'buy':
                buy_exposure += record.net_amount
            else:
                sell_exposure += record.net_amount
            
            if record.settlement_date == today:
                due_today += 1
            elif record.settlement_date < today:
                overdue += 1
        
        return {
            'pending_buys': buy_exposure,
            'pending_sells': sell_exposure,
            'net_exposure': buy_exposure - sell_exposure,
            'total_pending_count': len(self.pending_settlements),
            'due_today': due_today,
            'overdue': overdue,
            'failed_count': len(self.failed_settlements)
        }
    
    async def get_settlements_due_on(self, target_date: date) -> List[SettlementRecord]:
        """Get all settlements due on a specific date"""
        settlement_ids = self.settlements_by_date.get(target_date, [])
        return [
            self.pending_settlements[sid] 
            for sid in settlement_ids 
            if sid in self.pending_settlements
        ]
    
    # ===== Failure Handling =====
    
    async def check_settlement_failures(self) -> List[SettlementRecord]:
        """
        Check for failed or late settlements.
        
        Returns:
            List of failed settlement records
        """
        today = date.today()
        failures = []
        
        for record in list(self.pending_settlements.values()):
            if record.settlement_date < today:
                # Settlement is overdue
                await self._handle_settlement_failure(record, 'settlement_date_passed')
                failures.append(record)
        
        return failures
    
    async def _handle_settlement_failure(
        self, 
        record: SettlementRecord, 
        reason: str
    ):
        """Handle settlement failure"""
        logger.error(
            f"❌ Settlement failure: {record.settlement_id} "
            f"{record.symbol} due {record.settlement_date} - {reason}"
        )
        
        if record.retry_count < record.max_retries:
            # Retry settlement
            record.retry_count += 1
            record.settlement_date = self.calculate_settlement_date(
                date.today(), record.symbol
            )
            record.failure_reason = reason
            
            logger.info(
                f"🔄 Retry settlement: {record.settlement_id} "
                f"(attempt {record.retry_count}/{record.max_retries}) "
                f"new date: {record.settlement_date}"
            )
        else:
            # Max retries exceeded - escalate
            await self.update_settlement_status(
                record.settlement_id,
                SettlementStatus.FAILED,
                f"{reason} - max retries exceeded"
            )
            await self._escalate_settlement_failure(record)
    
    async def _escalate_settlement_failure(self, record: SettlementRecord):
        """Escalate settlement failure to operations team"""
        logger.critical(
            f"🚨 ESCALATION: Settlement failure - {record.settlement_id} "
            f"{record.symbol} {record.side} {record.quantity}@${record.price:.2f} "
            f"Reason: {record.failure_reason}"
        )
        # TODO: Send notification to operations team
    
    # ===== Background Tasks =====
    
    async def _settlement_failure_monitor(self):
        """Monitor for settlement failures"""
        while self._running:
            try:
                failures = await self.check_settlement_failures()
                if failures:
                    logger.warning(f"Found {len(failures)} settlement failures")
                
                await asyncio.sleep(self.failure_check_interval)
            except Exception as e:
                logger.error(f"Settlement failure monitor error: {e}")
                await asyncio.sleep(self.failure_check_interval)
    
    async def _settlement_due_monitor(self):
        """Monitor settlements due today"""
        while self._running:
            try:
                today = date.today()
                due_today = await self.get_settlements_due_on(today)
                
                if due_today:
                    logger.info(f"📅 Settlements due today: {len(due_today)}")
                    for record in due_today:
                        logger.info(
                            f"  - {record.settlement_id}: "
                            f"{record.symbol} {record.side} {record.quantity}"
                        )
                
                # Check once per hour
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Settlement due monitor error: {e}")
                await asyncio.sleep(3600)
    
    # ===== Query Methods =====
    
    async def get_pending_settlements(self) -> List[SettlementRecord]:
        """Get all pending settlements"""
        return list(self.pending_settlements.values())
    
    async def get_failed_settlements(self) -> List[SettlementRecord]:
        """Get all failed settlements"""
        return list(self.failed_settlements.values())
    
    async def get_settlement(self, settlement_id: str) -> Optional[SettlementRecord]:
        """Get settlement by ID"""
        record = self.pending_settlements.get(settlement_id)
        if not record:
            record = self.settled_records.get(settlement_id)
        if not record:
            record = self.failed_settlements.get(settlement_id)
        return record

