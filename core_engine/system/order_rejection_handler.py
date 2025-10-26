"""
Order Rejection Handler - Intelligent Retry System
Handles broker order rejections with pattern-matching and smart retry logic.

Rejection Patterns (8 types):
1. Insufficient Margin → Reduce quantity by 50%, retry
2. Stock Halted → Wait for resumption, monitor market status
3. Price Collar Violation → Adjust price within limits, retry
4. Connection Timeout → Exponential backoff (5s, 10s, 30s)
5. Duplicate Order ID → Generate new order ID, retry
6. Market Closed → Cancel order, log for next session
7. Position Limit Reached → Escalate to risk team
8. Unknown Error → Escalate with full diagnostics

Retry Strategy:
- Max Retries: 3 per order
- Backoff: Exponential (5s, 10s, 30s)
- Modifications: Pattern-specific (quantity, price, timing)
- Escalation: After 3 failed attempts → Alert risk team

Author: Trading System Team
Date: October 25, 2025
Version: 1.0
"""

import logging
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class RejectionReason(Enum):
    """Broker rejection reasons"""
    INSUFFICIENT_MARGIN = "insufficient_margin"
    STOCK_HALTED = "stock_halted"
    PRICE_COLLAR = "price_collar_violation"
    CONNECTION_TIMEOUT = "connection_timeout"
    DUPLICATE_ORDER_ID = "duplicate_order_id"
    MARKET_CLOSED = "market_closed"
    POSITION_LIMIT = "position_limit_reached"
    UNKNOWN = "unknown_error"


class RetryAction(Enum):
    """Actions to take on rejection"""
    RETRY_REDUCED_QUANTITY = "retry_reduced_quantity"
    RETRY_ADJUSTED_PRICE = "retry_adjusted_price"
    RETRY_NEW_ORDER_ID = "retry_new_order_id"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    WAIT_AND_RETRY = "wait_and_retry"
    CANCEL_ORDER = "cancel_order"
    ESCALATE = "escalate"


@dataclass
class RejectionResolution:
    """
    Resolution for order rejection
    
    Attributes:
        action: Action to take
        modified_order: Modified order parameters (if retrying)
        wait_seconds: Seconds to wait before retry
        reason: Explanation for action
        escalate_immediately: Whether to escalate to risk team
    """
    action: RetryAction
    modified_order: Optional[Dict] = None
    wait_seconds: int = 0
    reason: str = ""
    escalate_immediately: bool = False


@dataclass
class RejectionEvent:
    """
    Record of order rejection event
    
    Attributes:
        order_id: Original order ID
        symbol: Trading symbol
        side: 'buy' or 'sell'
        quantity: Order quantity
        price: Order price
        rejection_reason: Broker rejection reason
        rejection_code: Broker rejection code
        rejection_message: Full rejection message
        timestamp: When rejection occurred
        retry_count: Number of retries attempted
        resolution: Resolution applied
        final_outcome: Final outcome after retries
    """
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    rejection_reason: RejectionReason
    rejection_code: Optional[str]
    rejection_message: str
    timestamp: datetime
    retry_count: int = 0
    resolution: Optional[RejectionResolution] = None
    final_outcome: Optional[str] = None


class OrderRejectionHandler:
    """
    Order Rejection Handler - Intelligent Retry System
    
    Analyzes broker rejection reasons and applies pattern-specific
    retry logic to maximize fill rate while preventing system issues.
    
    Integration: Called by UnifiedExecutionEngine when orders are rejected
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize rejection handler
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Retry Configuration
        self.max_retries = self.config.get('max_retries', 3)
        self.backoff_base = self.config.get('backoff_base_seconds', 5)
        self.max_backoff = self.config.get('max_backoff_seconds', 60)
        
        # Quantity Adjustment
        self.quantity_reduction_factor = self.config.get('quantity_reduction_factor', 0.5)
        
        # Price Adjustment
        self.price_adjustment_bps = self.config.get('price_adjustment_bps', 10)  # 10 bps
        
        # Pattern Matching (keyword-based)
        self.rejection_patterns = self._initialize_rejection_patterns()
        
        # State
        self.active_retries: Dict[str, RejectionEvent] = {}
        self.rejection_history: List[RejectionEvent] = []
        
        # Statistics
        self.total_rejections = 0
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.escalations = 0
        self.rejections_by_reason: Dict[RejectionReason, int] = {
            reason: 0 for reason in RejectionReason
        }
        
        self.logger.info("✅ OrderRejectionHandler initialized")
        self.logger.info(f"   Max Retries: {self.max_retries}")
        self.logger.info(f"   Backoff Base: {self.backoff_base}s")
        self.logger.info(f"   Quantity Reduction: {self.quantity_reduction_factor:.0%}")
    
    def _initialize_rejection_patterns(self) -> Dict[str, RejectionReason]:
        """
        Initialize rejection pattern matching
        
        Maps broker rejection messages (keywords) to rejection reasons
        """
        return {
            # Insufficient Margin
            'insufficient': RejectionReason.INSUFFICIENT_MARGIN,
            'margin': RejectionReason.INSUFFICIENT_MARGIN,
            'buying power': RejectionReason.INSUFFICIENT_MARGIN,
            'funds': RejectionReason.INSUFFICIENT_MARGIN,
            
            # Stock Halted
            'halted': RejectionReason.STOCK_HALTED,
            'halt': RejectionReason.STOCK_HALTED,
            'trading halt': RejectionReason.STOCK_HALTED,
            'suspended': RejectionReason.STOCK_HALTED,
            
            # Price Collar
            'collar': RejectionReason.PRICE_COLLAR,
            'limit up': RejectionReason.PRICE_COLLAR,
            'limit down': RejectionReason.PRICE_COLLAR,
            'price limit': RejectionReason.PRICE_COLLAR,
            
            # Connection Timeout
            'timeout': RejectionReason.CONNECTION_TIMEOUT,
            'timed out': RejectionReason.CONNECTION_TIMEOUT,
            'connection': RejectionReason.CONNECTION_TIMEOUT,
            'network': RejectionReason.CONNECTION_TIMEOUT,
            
            # Duplicate Order ID
            'duplicate': RejectionReason.DUPLICATE_ORDER_ID,
            'already exists': RejectionReason.DUPLICATE_ORDER_ID,
            'order id': RejectionReason.DUPLICATE_ORDER_ID,
            
            # Market Closed
            'market closed': RejectionReason.MARKET_CLOSED,
            'outside market hours': RejectionReason.MARKET_CLOSED,
            'after hours': RejectionReason.MARKET_CLOSED,
            
            # Position Limit
            'position limit': RejectionReason.POSITION_LIMIT,
            'max position': RejectionReason.POSITION_LIMIT,
            'position size': RejectionReason.POSITION_LIMIT
        }
    
    async def handle_rejection(
        self,
        order: Dict,
        rejection_reason: str,
        rejection_code: Optional[str] = None
    ) -> RejectionResolution:
        """
        Handle order rejection and determine retry strategy
        
        Args:
            order: Original order details
            rejection_reason: Broker rejection message
            rejection_code: Broker rejection code (if available)
            
        Returns:
            RejectionResolution with action and modified order
        """
        self.total_rejections += 1
        
        # Create rejection event
        event = RejectionEvent(
            order_id=order.get('order_id', str(uuid.uuid4())),
            symbol=order.get('symbol'),
            side=order.get('side'),
            quantity=order.get('quantity'),
            price=order.get('price'),
            rejection_reason=self._classify_rejection(rejection_reason),
            rejection_code=rejection_code,
            rejection_message=rejection_reason,
            timestamp=datetime.now()
        )
        
        # Update statistics
        self.rejections_by_reason[event.rejection_reason] += 1
        
        # Check retry count
        retry_count = self._get_retry_count(event.order_id)
        event.retry_count = retry_count
        
        self.logger.warning(
            f"⚠️ Order rejection: {event.symbol} {event.side} {event.quantity} @ ${event.price:.2f} | "
            f"Reason: {event.rejection_reason.value} | "
            f"Retry: {retry_count}/{self.max_retries} | "
            f"Message: {rejection_reason}"
        )
        
        # Determine resolution based on pattern
        if retry_count >= self.max_retries:
            # Max retries reached - escalate
            resolution = self._create_escalation_resolution(event)
            event.final_outcome = "max_retries_reached"
        else:
            # Apply pattern-specific resolution
            resolution = self._resolve_rejection(event, retry_count)
        
        event.resolution = resolution
        
        # Store event
        self.active_retries[event.order_id] = event
        self.rejection_history.append(event)
        
        # Keep only last 1000 events
        if len(self.rejection_history) > 1000:
            self.rejection_history = self.rejection_history[-1000:]
        
        return resolution
    
    def _classify_rejection(self, rejection_message: str) -> RejectionReason:
        """
        Classify rejection reason based on message
        
        Uses keyword matching to identify rejection type
        """
        message_lower = rejection_message.lower()
        
        for keyword, reason in self.rejection_patterns.items():
            if keyword in message_lower:
                return reason
        
        return RejectionReason.UNKNOWN
    
    def _resolve_rejection(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Resolve rejection based on pattern
        
        Applies pattern-specific retry logic
        """
        reason = event.rejection_reason
        
        if reason == RejectionReason.INSUFFICIENT_MARGIN:
            return self._resolve_insufficient_margin(event, retry_count)
        
        elif reason == RejectionReason.STOCK_HALTED:
            return self._resolve_stock_halted(event, retry_count)
        
        elif reason == RejectionReason.PRICE_COLLAR:
            return self._resolve_price_collar(event, retry_count)
        
        elif reason == RejectionReason.CONNECTION_TIMEOUT:
            return self._resolve_connection_timeout(event, retry_count)
        
        elif reason == RejectionReason.DUPLICATE_ORDER_ID:
            return self._resolve_duplicate_order_id(event, retry_count)
        
        elif reason == RejectionReason.MARKET_CLOSED:
            return self._resolve_market_closed(event, retry_count)
        
        elif reason == RejectionReason.POSITION_LIMIT:
            return self._resolve_position_limit(event, retry_count)
        
        else:  # UNKNOWN
            return self._resolve_unknown_error(event, retry_count)
    
    def _resolve_insufficient_margin(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 1: Insufficient Margin
        Resolution: Reduce quantity by 50%, retry
        """
        reduced_quantity = event.quantity * self.quantity_reduction_factor
        
        modified_order = {
            'order_id': event.order_id,
            'symbol': event.symbol,
            'side': event.side,
            'quantity': reduced_quantity,
            'price': event.price
        }
        
        return RejectionResolution(
            action=RetryAction.RETRY_REDUCED_QUANTITY,
            modified_order=modified_order,
            wait_seconds=0,  # Immediate retry
            reason=f"Reduced quantity to {reduced_quantity:.2f} ({self.quantity_reduction_factor:.0%} of original)"
        )
    
    def _resolve_stock_halted(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 2: Stock Halted
        Resolution: Wait 30 seconds, then retry (monitor market status)
        """
        return RejectionResolution(
            action=RetryAction.WAIT_AND_RETRY,
            modified_order={
                'order_id': event.order_id,
                'symbol': event.symbol,
                'side': event.side,
                'quantity': event.quantity,
                'price': event.price
            },
            wait_seconds=30,
            reason="Stock halted, waiting 30s for resumption"
        )
    
    def _resolve_price_collar(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 3: Price Collar Violation
        Resolution: Adjust price by ±10 bps (within collar), retry
        """
        # Adjust price based on side
        if event.side.lower() == 'buy':
            # For buy, reduce price by 10 bps
            adjusted_price = event.price * (1 - self.price_adjustment_bps / 10000)
        else:
            # For sell, increase price by 10 bps
            adjusted_price = event.price * (1 + self.price_adjustment_bps / 10000)
        
        modified_order = {
            'order_id': event.order_id,
            'symbol': event.symbol,
            'side': event.side,
            'quantity': event.quantity,
            'price': adjusted_price
        }
        
        return RejectionResolution(
            action=RetryAction.RETRY_ADJUSTED_PRICE,
            modified_order=modified_order,
            wait_seconds=0,
            reason=f"Adjusted price from ${event.price:.2f} to ${adjusted_price:.2f}"
        )
    
    def _resolve_connection_timeout(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 4: Connection Timeout
        Resolution: Exponential backoff (5s, 10s, 30s), retry
        """
        # Calculate exponential backoff
        wait_seconds = min(
            self.backoff_base * (2 ** retry_count),
            self.max_backoff
        )
        
        return RejectionResolution(
            action=RetryAction.RETRY_WITH_BACKOFF,
            modified_order={
                'order_id': event.order_id,
                'symbol': event.symbol,
                'side': event.side,
                'quantity': event.quantity,
                'price': event.price
            },
            wait_seconds=wait_seconds,
            reason=f"Connection timeout, exponential backoff: {wait_seconds}s"
        )
    
    def _resolve_duplicate_order_id(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 5: Duplicate Order ID
        Resolution: Generate new order ID, retry immediately
        """
        new_order_id = f"{event.order_id}_retry_{retry_count}_{uuid.uuid4().hex[:8]}"
        
        modified_order = {
            'order_id': new_order_id,
            'symbol': event.symbol,
            'side': event.side,
            'quantity': event.quantity,
            'price': event.price
        }
        
        return RejectionResolution(
            action=RetryAction.RETRY_NEW_ORDER_ID,
            modified_order=modified_order,
            wait_seconds=0,
            reason=f"Generated new order ID: {new_order_id}"
        )
    
    def _resolve_market_closed(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 6: Market Closed
        Resolution: Cancel order, log for next session
        """
        return RejectionResolution(
            action=RetryAction.CANCEL_ORDER,
            modified_order=None,
            wait_seconds=0,
            reason="Market closed - order cancelled for this session"
        )
    
    def _resolve_position_limit(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 7: Position Limit Reached
        Resolution: Escalate to risk team (cannot auto-resolve)
        """
        return RejectionResolution(
            action=RetryAction.ESCALATE,
            modified_order=None,
            wait_seconds=0,
            reason="Position limit reached - requires risk team approval",
            escalate_immediately=True
        )
    
    def _resolve_unknown_error(self, event: RejectionEvent, retry_count: int) -> RejectionResolution:
        """
        Pattern 8: Unknown Error
        Resolution: Escalate with full diagnostics
        """
        return RejectionResolution(
            action=RetryAction.ESCALATE,
            modified_order=None,
            wait_seconds=0,
            reason=f"Unknown rejection: {event.rejection_message}",
            escalate_immediately=True
        )
    
    def _create_escalation_resolution(self, event: RejectionEvent) -> RejectionResolution:
        """Create escalation resolution when max retries reached"""
        self.escalations += 1
        
        return RejectionResolution(
            action=RetryAction.ESCALATE,
            modified_order=None,
            wait_seconds=0,
            reason=f"Max retries ({self.max_retries}) reached",
            escalate_immediately=True
        )
    
    def _get_retry_count(self, order_id: str) -> int:
        """Get current retry count for order"""
        if order_id in self.active_retries:
            return self.active_retries[order_id].retry_count + 1
        return 0
    
    def record_retry_outcome(self, order_id: str, success: bool):
        """
        Record outcome of retry attempt
        
        Args:
            order_id: Order ID
            success: Whether retry was successful
        """
        self.total_retries += 1
        
        if success:
            self.successful_retries += 1
            self.logger.info(f"✅ Retry successful: {order_id}")
            
            # Remove from active retries
            if order_id in self.active_retries:
                event = self.active_retries[order_id]
                event.final_outcome = "retry_successful"
                del self.active_retries[order_id]
        else:
            self.failed_retries += 1
            self.logger.warning(f"❌ Retry failed: {order_id}")
    
    # Statistics and Reporting
    
    def get_rejection_statistics(self) -> Dict:
        """Get rejection handling statistics"""
        total_attempts = self.total_retries + self.total_rejections
        
        return {
            'total_rejections': self.total_rejections,
            'total_retries': self.total_retries,
            'successful_retries': self.successful_retries,
            'failed_retries': self.failed_retries,
            'retry_success_rate': self.successful_retries / max(1, self.total_retries),
            'escalations': self.escalations,
            'active_retries': len(self.active_retries),
            'rejections_by_reason': {
                reason.value: count 
                for reason, count in self.rejections_by_reason.items()
                if count > 0
            }
        }
    
    def generate_rejection_report(self) -> str:
        """Generate rejection handling report"""
        stats = self.get_rejection_statistics()
        
        report = [
            "=" * 60,
            "ORDER REJECTION HANDLER REPORT",
            "=" * 60,
            f"Total Rejections:      {stats['total_rejections']:,}",
            f"Total Retries:         {stats['total_retries']:,}",
            f"Successful Retries:    {stats['successful_retries']:,}",
            f"Failed Retries:        {stats['failed_retries']:,}",
            f"Retry Success Rate:    {stats['retry_success_rate']:.1%}",
            f"Escalations:           {stats['escalations']:,}",
            f"Active Retries:        {stats['active_retries']:,}",
            "",
            "REJECTIONS BY REASON:",
            *[f"  - {reason}: {count}" for reason, count in stats['rejections_by_reason'].items()],
            "=" * 60
        ]
        
        return "\n".join(report)

