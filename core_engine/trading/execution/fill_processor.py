"""
Execution Engine - Fill Processor
Sophisticated fill processing, reconciliation, and trade reporting
"""

import logging
import threading
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class FillStatus(Enum):
    """Fill processing status"""
    PENDING = "pending"
    VALIDATED = "validated"
    RECONCILED = "reconciled"
    PROCESSED = "processed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReconciliationStatus(Enum):
    """Trade reconciliation status"""
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    BROKEN = "broken"
    DISPUTED = "disputed"
    PENDING_INVESTIGATION = "pending_investigation"


class ReportingFrequency(Enum):
    """Reporting frequency options"""
    REAL_TIME = "real_time"
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class TradeExecution:
    """Complete trade execution record"""
    execution_id: str
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    execution_time: datetime  # Moved here - required fields first
    venue: str
    
    # Optional execution details with defaults
    commission: float = 0.0
    fees: float = 0.0
    settlement_date: Optional[datetime] = None
    venue_order_id: Optional[str] = None
    venue_execution_id: Optional[str] = None
    
    # Trade classification
    liquidity_flag: str = "Unknown"  # Added, Removed, Opening, Closing
    trade_type: str = "Regular"     # Regular, Block, Cross, etc.
    
    # Market data context
    bid_at_execution: Optional[float] = None
    ask_at_execution: Optional[float] = None
    midpoint_at_execution: Optional[float] = None
    
    # Performance metrics
    price_improvement: float = 0.0
    effective_spread: float = 0.0
    market_impact: float = 0.0
    implementation_shortfall: float = 0.0
    
    # Reconciliation
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.PENDING_INVESTIGATION
    counterparty: Optional[str] = None
    clearing_firm: Optional[str] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    trader_id: Optional[str] = None
    
    # Status tracking
    fill_status: FillStatus = FillStatus.PENDING
    processing_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PositionUpdate:
    """Position update from trade execution"""
    symbol: str
    account: str
    quantity_change: float
    price: float
    new_position: float
    new_avg_cost: float
    realized_pnl: float
    unrealized_pnl_change: float
    source_execution_id: str  # Moved here - required fields first
    
    # Optional fields with defaults
    update_time: datetime = field(default_factory=datetime.now)
    commission: float = 0.0
    fees: float = 0.0


@dataclass
class FillEvent:
    """Fill event data"""
    order_id: str
    symbol: str
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0


@dataclass
class FillMetrics:
    """Fill processing metrics"""
    total_fills: int = 0
    total_quantity: float = 0.0
    average_price: float = 0.0
    total_commission: float = 0.0


@dataclass
class FillValidationRule:
    """Fill validation rule"""
    rule_id: str
    rule_name: str
    description: str
    
    # Rule parameters
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_quantity: Optional[float] = None
    max_notional: Optional[float] = None
    
    # Time constraints
    market_hours_only: bool = True
    max_execution_delay: Optional[timedelta] = None
    
    # Price validation
    max_price_deviation: Optional[float] = None  # From reference price
    
    # Enabled/disabled
    enabled: bool = True
    priority: int = 1  # Higher number = higher priority


class FillValidator:
    """Validates trade fills against business rules"""
    
    def __init__(self):
        self.validation_rules = {}
        self._reference_data = {}
        self._lock = threading.Lock()
        
        # Load default validation rules
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default validation rules"""
        
        default_rules = [
            FillValidationRule(
                rule_id="price_range_check",
                rule_name="Price Range Validation",
                description="Validate fill price is within reasonable range",
                max_price_deviation=0.05,  # 5% from reference
                priority=1
            ),
            FillValidationRule(
                rule_id="quantity_limit_check",
                rule_name="Quantity Limit Validation",
                description="Validate fill quantity doesn't exceed limits",
                max_quantity=1_000_000,
                priority=2
            ),
            FillValidationRule(
                rule_id="market_hours_check",
                rule_name="Market Hours Validation",
                description="Validate execution during market hours",
                market_hours_only=True,
                priority=3
            ),
            FillValidationRule(
                rule_id="notional_limit_check",
                rule_name="Notional Limit Validation",
                description="Validate notional amount doesn't exceed limits",
                max_notional=100_000_000,  # $100M
                priority=4
            )
        ]
        
        for rule in default_rules:
            self.validation_rules[rule.rule_id] = rule
    
    def validate_fill(self, execution: TradeExecution) -> Tuple[bool, List[str]]:
        """Validate trade fill against all rules"""
        
        validation_errors = []
        
        # Sort rules by priority
        sorted_rules = sorted(
            self.validation_rules.values(),
            key=lambda x: x.priority
        )
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            errors = self._apply_validation_rule(execution, rule)
            validation_errors.extend(errors)
        
        is_valid = len(validation_errors) == 0
        return is_valid, validation_errors
    
    def _apply_validation_rule(
        self,
        execution: TradeExecution,
        rule: FillValidationRule
    ) -> List[str]:
        """Apply single validation rule"""
        
        errors = []
        
        try:
            if rule.rule_id == "price_range_check":
                errors.extend(self._validate_price_range(execution, rule))
            elif rule.rule_id == "quantity_limit_check":
                errors.extend(self._validate_quantity_limits(execution, rule))
            elif rule.rule_id == "market_hours_check":
                errors.extend(self._validate_market_hours(execution, rule))
            elif rule.rule_id == "notional_limit_check":
                errors.extend(self._validate_notional_limits(execution, rule))
            else:
                # Custom rule - would be implemented based on requirements
                pass
                
        except Exception as e:
            errors.append(f"Error applying rule {rule.rule_id}: {str(e)}")
        
        return errors
    
    def _validate_price_range(
        self,
        execution: TradeExecution,
        rule: FillValidationRule
    ) -> List[str]:
        """Validate price is within acceptable range"""
        
        errors = []
        
        if rule.max_price_deviation is None:
            return errors
        
        # Get reference price (midpoint if available, otherwise last price)
        reference_price = execution.midpoint_at_execution
        if reference_price is None:
            # Use average of bid/ask if available
            if execution.bid_at_execution and execution.ask_at_execution:
                reference_price = (execution.bid_at_execution + execution.ask_at_execution) / 2
            else:
                # No reference price available - skip validation
                return errors
        
        # Calculate price deviation
        price_deviation = abs(execution.price - reference_price) / reference_price
        
        if price_deviation > rule.max_price_deviation:
            errors.append(
                f"Price deviation {price_deviation:.2%} exceeds limit "
                f"{rule.max_price_deviation:.2%} (price: {execution.price}, "
                f"reference: {reference_price})"
            )
        
        return errors
    
    def _validate_quantity_limits(
        self,
        execution: TradeExecution,
        rule: FillValidationRule
    ) -> List[str]:
        """Validate quantity limits"""
        
        errors = []
        
        if rule.max_quantity and execution.quantity > rule.max_quantity:
            errors.append(
                f"Quantity {execution.quantity:,.0f} exceeds limit "
                f"{rule.max_quantity:,.0f}"
            )
        
        if execution.quantity <= 0:
            errors.append("Quantity must be positive")
        
        return errors
    
    def _validate_market_hours(
        self,
        execution: TradeExecution,
        rule: FillValidationRule
    ) -> List[str]:
        """Validate execution during market hours"""
        
        errors = []
        
        if not rule.market_hours_only:
            return errors
        
        # Simple market hours check (9:30 AM - 4:00 PM ET)
        execution_time = execution.execution_time
        
        # Convert to market time (assuming ET)
        market_open = execution_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = execution_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Check if weekend
        if execution_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            errors.append("Execution on weekend not allowed")
        elif execution_time < market_open or execution_time > market_close:
            errors.append(
                f"Execution outside market hours: {execution_time.strftime('%H:%M:%S')} "
                f"(market: 09:30-16:00)"
            )
        
        return errors
    
    def _validate_notional_limits(
        self,
        execution: TradeExecution,
        rule: FillValidationRule
    ) -> List[str]:
        """Validate notional amount limits"""
        
        errors = []
        
        notional = execution.quantity * execution.price
        
        if rule.max_notional and notional > rule.max_notional:
            errors.append(
                f"Notional amount ${notional:,.2f} exceeds limit "
                f"${rule.max_notional:,.2f}"
            )
        
        return errors
    
    def add_custom_rule(self, rule: FillValidationRule) -> None:
        """Add custom validation rule"""
        
        with self._lock:
            self.validation_rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove validation rule"""
        
        with self._lock:
            if rule_id in self.validation_rules:
                del self.validation_rules[rule_id]
                return True
            return False


class TradeReconciler:
    """Reconciles trades with counterparties and venues"""
    
    def __init__(self):
        self._pending_reconciliation = {}
        self._reconciled_trades = {}
        self._discrepancies = {}
        self._lock = threading.Lock()
    
    def reconcile_execution(
        self,
        our_execution: TradeExecution,
        counterparty_data: Optional[Dict[str, Any]] = None
    ) -> ReconciliationStatus:
        """Reconcile execution with counterparty data"""
        
        if counterparty_data is None:
            # No counterparty data yet - mark as unmatched
            our_execution.reconciliation_status = ReconciliationStatus.UNMATCHED
            
            with self._lock:
                self._pending_reconciliation[our_execution.execution_id] = our_execution
            
            return ReconciliationStatus.UNMATCHED
        
        # Compare our data with counterparty data
        discrepancies = self._compare_execution_data(our_execution, counterparty_data)
        
        if not discrepancies:
            # Perfect match
            our_execution.reconciliation_status = ReconciliationStatus.MATCHED
            
            with self._lock:
                self._reconciled_trades[our_execution.execution_id] = our_execution
                if our_execution.execution_id in self._pending_reconciliation:
                    del self._pending_reconciliation[our_execution.execution_id]
            
            return ReconciliationStatus.MATCHED
        
        elif self._are_discrepancies_acceptable(discrepancies):
            # Minor discrepancies - still considered matched
            our_execution.reconciliation_status = ReconciliationStatus.MATCHED
            our_execution.processing_notes.append(f"Minor discrepancies: {discrepancies}")
            
            with self._lock:
                self._reconciled_trades[our_execution.execution_id] = our_execution
            
            return ReconciliationStatus.MATCHED
        
        else:
            # Significant discrepancies - mark as broken
            our_execution.reconciliation_status = ReconciliationStatus.BROKEN
            
            with self._lock:
                self._discrepancies[our_execution.execution_id] = {
                    'execution': our_execution,
                    'counterparty_data': counterparty_data,
                    'discrepancies': discrepancies,
                    'timestamp': datetime.now()
                }
            
            return ReconciliationStatus.BROKEN
    
    def _compare_execution_data(
        self,
        our_execution: TradeExecution,
        counterparty_data: Dict[str, Any]
    ) -> List[str]:
        """Compare execution data and identify discrepancies"""
        
        discrepancies = []
        
        # Compare quantity
        cp_quantity = counterparty_data.get('quantity', 0)
        if abs(our_execution.quantity - cp_quantity) > 0.01:
            discrepancies.append(
                f"Quantity mismatch: Our {our_execution.quantity}, "
                f"CP {cp_quantity}"
            )
        
        # Compare price
        cp_price = counterparty_data.get('price', 0)
        if abs(our_execution.price - cp_price) > 0.001:
            discrepancies.append(
                f"Price mismatch: Our {our_execution.price}, "
                f"CP {cp_price}"
            )
        
        # Compare side
        cp_side = counterparty_data.get('side', '')
        expected_cp_side = 'SELL' if our_execution.side == 'BUY' else 'BUY'
        if cp_side != expected_cp_side:
            discrepancies.append(
                f"Side mismatch: Expected CP {expected_cp_side}, "
                f"Got {cp_side}"
            )
        
        # Compare symbol
        cp_symbol = counterparty_data.get('symbol', '')
        if cp_symbol != our_execution.symbol:
            discrepancies.append(
                f"Symbol mismatch: Our {our_execution.symbol}, "
                f"CP {cp_symbol}"
            )
        
        # Compare execution time (within tolerance)
        cp_time_str = counterparty_data.get('execution_time', '')
        if cp_time_str:
            try:
                cp_time = datetime.fromisoformat(cp_time_str)
                time_diff = abs((our_execution.execution_time - cp_time).total_seconds())
                if time_diff > 60:  # More than 1 minute difference
                    discrepancies.append(
                        f"Execution time mismatch: Our {our_execution.execution_time}, "
                        f"CP {cp_time} (diff: {time_diff}s)"
                    )
            except ValueError:
                discrepancies.append(f"Invalid CP execution time format: {cp_time_str}")
        
        return discrepancies
    
    def _are_discrepancies_acceptable(self, discrepancies: List[str]) -> bool:
        """Determine if discrepancies are within acceptable tolerances"""
        
        # For this example, any discrepancy is considered unacceptable
        # In practice, you might allow small price differences, timing differences, etc.
        return False
    
    def get_reconciliation_summary(self) -> Dict[str, Any]:
        """Get reconciliation summary statistics"""
        
        with self._lock:
            total_trades = (
                len(self._reconciled_trades) +
                len(self._pending_reconciliation) +
                len(self._discrepancies)
            )
            
            return {
                'total_trades': total_trades,
                'reconciled_trades': len(self._reconciled_trades),
                'pending_reconciliation': len(self._pending_reconciliation),
                'discrepancies': len(self._discrepancies),
                'reconciliation_rate': (
                    len(self._reconciled_trades) / total_trades
                    if total_trades > 0 else 0
                )
            }
    
    def get_pending_reconciliations(self) -> List[TradeExecution]:
        """Get list of trades pending reconciliation"""
        
        with self._lock:
            return list(self._pending_reconciliation.values())
    
    def get_discrepancies(self) -> List[Dict[str, Any]]:
        """Get list of trade discrepancies"""
        
        with self._lock:
            return list(self._discrepancies.values())


class PositionManager:
    """Manages position updates from trade executions"""
    
    def __init__(self):
        self._positions = defaultdict(lambda: defaultdict(float))
        self._avg_costs = defaultdict(lambda: defaultdict(float))
        self._position_history = []
        self._lock = threading.Lock()
    
    def process_execution(self, execution: TradeExecution) -> PositionUpdate:
        """Process execution and update positions"""
        
        account = execution.portfolio_id or "DEFAULT"
        symbol = execution.symbol
        
        with self._lock:
            # Get current position
            current_position = self._positions[account][symbol]
            current_avg_cost = self._avg_costs[account][symbol]
            
            # Calculate position change
            if execution.side == 'BUY':
                quantity_change = execution.quantity
            else:
                quantity_change = -execution.quantity
            
            # Calculate new position
            new_position = current_position + quantity_change
            
            # Calculate new average cost
            if new_position == 0:
                new_avg_cost = 0.0
                realized_pnl = self._calculate_realized_pnl(
                    current_position,
                    current_avg_cost,
                    quantity_change,
                    execution.price
                )
            elif (current_position > 0 and quantity_change > 0) or (current_position < 0 and quantity_change < 0):
                # Adding to position
                total_cost = (current_position * current_avg_cost) + (quantity_change * execution.price)
                new_avg_cost = total_cost / new_position if new_position != 0 else 0
                realized_pnl = 0.0
            else:
                # Reducing or flipping position
                if abs(quantity_change) <= abs(current_position):
                    # Reducing position
                    realized_pnl = self._calculate_realized_pnl(
                        current_position,
                        current_avg_cost,
                        quantity_change,
                        execution.price
                    )
                    new_avg_cost = current_avg_cost  # Avg cost doesn't change when reducing
                else:
                    # Flipping position
                    closing_quantity = -current_position
                    realized_pnl = self._calculate_realized_pnl(
                        current_position,
                        current_avg_cost,
                        closing_quantity,
                        execution.price
                    )
                    remaining_quantity = quantity_change + closing_quantity
                    new_avg_cost = execution.price  # New position starts with execution price
            
            # Update positions
            self._positions[account][symbol] = new_position
            self._avg_costs[account][symbol] = new_avg_cost
            
            # Create position update
            position_update = PositionUpdate(
                symbol=symbol,
                account=account,
                quantity_change=quantity_change,
                price=execution.price,
                new_position=new_position,
                new_avg_cost=new_avg_cost,
                realized_pnl=realized_pnl,
                unrealized_pnl_change=0.0,  # Would calculate with current market price
                source_execution_id=execution.execution_id,
                commission=execution.commission,
                fees=execution.fees
            )
            
            # Add to history
            self._position_history.append(position_update)
            
            return position_update
    
    def _calculate_realized_pnl(
        self,
        position: float,
        avg_cost: float,
        quantity_change: float,
        execution_price: float
    ) -> float:
        """Calculate realized P&L from position change"""
        
        if position == 0 or quantity_change == 0:
            return 0.0
        
        # Only calculate P&L if reducing position
        if (position > 0 and quantity_change < 0) or (position < 0 and quantity_change > 0):
            pnl_per_share = execution_price - avg_cost
            if position < 0:  # Short position
                pnl_per_share = -pnl_per_share
            
            realized_quantity = min(abs(quantity_change), abs(position))
            return pnl_per_share * realized_quantity
        
        return 0.0
    
    def get_position(self, account: str, symbol: str) -> Dict[str, float]:
        """Get current position for account and symbol"""
        
        with self._lock:
            return {
                'position': self._positions[account][symbol],
                'avg_cost': self._avg_costs[account][symbol]
            }
    
    def get_all_positions(self, account: str) -> Dict[str, Dict[str, float]]:
        """Get all positions for account"""
        
        with self._lock:
            positions = {}
            for symbol in self._positions[account]:
                if self._positions[account][symbol] != 0:
                    positions[symbol] = {
                        'position': self._positions[account][symbol],
                        'avg_cost': self._avg_costs[account][symbol]
                    }
            return positions


class TradeReporter:
    """Generates trade reports and analytics"""
    
    def __init__(self):
        self._executions = []
        self._reports_cache = {}
        self._lock = threading.Lock()
    
    def add_execution(self, execution: TradeExecution) -> None:
        """Add execution to reporting database"""
        
        with self._lock:
            self._executions.append(execution)
            # Clear cache when new data is added
            self._reports_cache.clear()
    
    def generate_execution_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> pd.DataFrame:
        """Generate execution report"""
        
        # Filter executions
        filtered_executions = self._filter_executions(
            start_date, end_date, symbol, strategy_id
        )
        
        if not filtered_executions:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for execution in filtered_executions:
            data.append({
                'execution_id': execution.execution_id,
                'order_id': execution.order_id,
                'symbol': execution.symbol,
                'side': execution.side,
                'quantity': execution.quantity,
                'price': execution.price,
                'notional': execution.quantity * execution.price,
                'commission': execution.commission,
                'fees': execution.fees,
                'venue': execution.venue,
                'execution_time': execution.execution_time,
                'liquidity_flag': execution.liquidity_flag,
                'price_improvement': execution.price_improvement,
                'effective_spread': execution.effective_spread,
                'market_impact': execution.market_impact,
                'implementation_shortfall': execution.implementation_shortfall,
                'strategy_id': execution.strategy_id,
                'fill_status': execution.fill_status.value,
                'reconciliation_status': execution.reconciliation_status.value
            })
        
        df = pd.DataFrame(data)
        
        # Add derived columns
        if not df.empty:
            df['execution_date'] = df['execution_time'].dt.date
            df['execution_hour'] = df['execution_time'].dt.hour
            df['net_amount'] = df['notional'] - df['commission'] - df['fees']
            
            # Performance metrics
            df['slippage_bps'] = df['implementation_shortfall'] * 10000
            df['market_impact_bps'] = df['market_impact'] * 10000
            df['effective_spread_bps'] = df['effective_spread'] * 10000
        
        return df
    
    def generate_performance_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate performance summary"""
        
        cache_key = f"performance_{start_date}_{end_date}"
        
        with self._lock:
            if cache_key in self._reports_cache:
                return self._reports_cache[cache_key]
        
        df = self.generate_execution_report(start_date, end_date)
        
        if df.empty:
            return {}
        
        summary = {
            'total_executions': len(df),
            'total_volume': df['quantity'].sum(),
            'total_notional': df['notional'].sum(),
            'total_commission': df['commission'].sum(),
            'total_fees': df['fees'].sum(),
            'avg_execution_size': df['quantity'].mean(),
            'avg_price_improvement_bps': df['price_improvement'].mean() * 10000,
            'avg_effective_spread_bps': df['effective_spread'].mean() * 10000,
            'avg_market_impact_bps': df['market_impact'].mean() * 10000,
            'avg_implementation_shortfall_bps': df['implementation_shortfall'].mean() * 10000,
            'fill_rate': len(df[df['fill_status'] == 'processed']) / len(df),
            'reconciliation_rate': len(df[df['reconciliation_status'] == 'matched']) / len(df)
        }
        
        # Venue breakdown
        venue_stats = df.groupby('venue').agg({
            'quantity': 'sum',
            'notional': 'sum',
            'market_impact': 'mean',
            'effective_spread': 'mean'
        }).to_dict('index')
        
        summary['venue_breakdown'] = venue_stats
        
        # Time-based statistics
        hourly_stats = df.groupby('execution_hour').agg({
            'quantity': 'sum',
            'market_impact': 'mean'
        }).to_dict('index')
        
        summary['hourly_breakdown'] = hourly_stats
        
        with self._lock:
            self._reports_cache[cache_key] = summary
        
        return summary
    
    def generate_slippage_analysis(
        self,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate detailed slippage analysis"""
        
        df = self.generate_execution_report(symbol=symbol, strategy_id=strategy_id)
        
        if df.empty:
            return {}
        
        # Calculate slippage statistics
        slippage_stats = {
            'mean_slippage_bps': df['slippage_bps'].mean(),
            'median_slippage_bps': df['slippage_bps'].median(),
            'std_slippage_bps': df['slippage_bps'].std(),
            'min_slippage_bps': df['slippage_bps'].min(),
            'max_slippage_bps': df['slippage_bps'].max(),
            'percentile_25': df['slippage_bps'].quantile(0.25),
            'percentile_75': df['slippage_bps'].quantile(0.75),
            'percentile_95': df['slippage_bps'].quantile(0.95)
        }
        
        # Slippage by venue
        venue_slippage = df.groupby('venue')['slippage_bps'].agg([
            'mean', 'median', 'std', 'count'
        ]).to_dict('index')
        
        # Slippage by order size buckets
        df['size_bucket'] = pd.cut(
            df['quantity'],
            bins=[0, 1000, 5000, 10000, 50000, float('inf')],
            labels=['<1K', '1K-5K', '5K-10K', '10K-50K', '>50K']
        )
        
        size_slippage = df.groupby('size_bucket')['slippage_bps'].agg([
            'mean', 'median', 'count'
        ]).to_dict('index')
        
        return {
            'overall_statistics': slippage_stats,
            'venue_analysis': venue_slippage,
            'size_analysis': size_slippage
        }
    
    def _filter_executions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> List[TradeExecution]:
        """Filter executions based on criteria"""
        
        with self._lock:
            filtered = self._executions.copy()
        
        if start_date:
            filtered = [e for e in filtered if e.execution_time >= start_date]
        
        if end_date:
            filtered = [e for e in filtered if e.execution_time <= end_date]
        
        if symbol:
            filtered = [e for e in filtered if e.symbol == symbol]
        
        if strategy_id:
            filtered = [e for e in filtered if e.strategy_id == strategy_id]
        
        return filtered


class FillProcessor:
    """
    Advanced Fill Processor
    
    Comprehensive fill processing with validation, reconciliation,
    position management, and sophisticated reporting capabilities.
    """
    
    def __init__(self):
        """Initialize fill processor"""
        
        # Core components
        self.validator = FillValidator()
        self.reconciler = TradeReconciler()
        self.position_manager = PositionManager()
        self.reporter = TradeReporter()
        
        # Processing queues
        self._fill_queue = asyncio.Queue()
        self._processed_fills = {}
        self._failed_fills = {}
        
        # Event callbacks
        self._fill_callbacks = []
        self._position_callbacks = []
        
        # Threading
        self._lock = threading.Lock()
        self._running = False
        self._processing_task = None
        
        # Test support attributes
        self.fill_events = []
        
        logger.info("Fill Processor initialized")
    
    def process_fill_event(self, fill_event: FillEvent) -> None:
        """Process a fill event (for testing)"""
        self.fill_events.append(fill_event)
    
    def get_fill_metrics(self, symbol: str) -> FillMetrics:
        """Get fill metrics for a symbol (for testing)"""
        symbol_fills = [f for f in self.fill_events if f.symbol == symbol]
        
        if not symbol_fills:
            return FillMetrics()
        
        total_quantity = sum(f.quantity for f in symbol_fills)
        total_commission = sum(f.commission for f in symbol_fills)
        weighted_price = sum(f.price * f.quantity for f in symbol_fills) / total_quantity
        
        return FillMetrics(
            total_fills=len(symbol_fills),
            total_quantity=total_quantity,
            average_price=weighted_price,
            total_commission=total_commission
        )
    
    async def process_fill(self, execution: TradeExecution) -> bool:
        """Process individual fill"""
        
        try:
            execution.updated_at = datetime.now()
            
            # Step 1: Validate fill
            is_valid, validation_errors = self.validator.validate_fill(execution)
            
            if not is_valid:
                execution.fill_status = FillStatus.REJECTED
                execution.processing_notes.extend(validation_errors)
                
                with self._lock:
                    self._failed_fills[execution.execution_id] = execution
                
                logger.warning(f"Fill {execution.execution_id} rejected: {validation_errors}")
                return False
            
            execution.fill_status = FillStatus.VALIDATED
            execution.processing_notes.append("Validation passed")
            
            # Step 2: Reconcile with counterparty (if data available)
            reconciliation_status = self.reconciler.reconcile_execution(execution)
            execution.processing_notes.append(f"Reconciliation status: {reconciliation_status.value}")
            
            # Step 3: Update positions
            position_update = self.position_manager.process_execution(execution)
            execution.processing_notes.append(f"Position updated: {position_update.new_position}")
            
            # Step 4: Mark as processed
            execution.fill_status = FillStatus.PROCESSED
            execution.updated_at = datetime.now()
            
            # Step 5: Add to reporting
            self.reporter.add_execution(execution)
            
            # Step 6: Store processed fill
            with self._lock:
                self._processed_fills[execution.execution_id] = execution
            
            # Step 7: Trigger callbacks
            await self._trigger_fill_callbacks(execution)
            await self._trigger_position_callbacks(position_update)
            
            logger.info(f"Fill {execution.execution_id} processed successfully")
            return True
            
        except Exception as e:
            execution.fill_status = FillStatus.REJECTED
            execution.processing_notes.append(f"Processing error: {str(e)}")
            
            with self._lock:
                self._failed_fills[execution.execution_id] = execution
            
            logger.error(f"Error processing fill {execution.execution_id}: {e}")
            return False
    
    async def process_fill_batch(self, executions: List[TradeExecution]) -> Dict[str, Any]:
        """Process batch of fills"""
        
        results = {
            'processed': 0,
            'failed': 0,
            'details': []
        }
        
        for execution in executions:
            success = await self.process_fill(execution)
            
            if success:
                results['processed'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                'execution_id': execution.execution_id,
                'success': success,
                'status': execution.fill_status.value,
                'notes': execution.processing_notes[-1] if execution.processing_notes else None
            })
        
        logger.info(f"Batch processing complete: {results['processed']} processed, {results['failed']} failed")
        return results
    
    def add_fill_callback(self, callback: Callable[[TradeExecution], None]) -> None:
        """Add callback for fill processing events"""
        self._fill_callbacks.append(callback)
    
    def add_position_callback(self, callback: Callable[[PositionUpdate], None]) -> None:
        """Add callback for position update events"""
        self._position_callbacks.append(callback)
    
    async def _trigger_fill_callbacks(self, execution: TradeExecution) -> None:
        """Trigger fill processing callbacks"""
        
        for callback in self._fill_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution)
                else:
                    callback(execution)
            except Exception as e:
                logger.error(f"Error in fill callback: {e}")
    
    async def _trigger_position_callbacks(self, position_update: PositionUpdate) -> None:
        """Trigger position update callbacks"""
        
        for callback in self._position_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(position_update)
                else:
                    callback(position_update)
            except Exception as e:
                logger.error(f"Error in position callback: {e}")
    
    def get_fill_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get fill processing status"""
        
        with self._lock:
            # Check processed fills
            if execution_id in self._processed_fills:
                execution = self._processed_fills[execution_id]
            # Check failed fills
            elif execution_id in self._failed_fills:
                execution = self._failed_fills[execution_id]
            else:
                return None
        
        return {
            'execution_id': execution_id,
            'symbol': execution.symbol,
            'side': execution.side,
            'quantity': execution.quantity,
            'price': execution.price,
            'venue': execution.venue,
            'status': execution.fill_status.value,
            'reconciliation_status': execution.reconciliation_status.value,
            'processing_notes': execution.processing_notes,
            'created_at': execution.created_at.isoformat(),
            'updated_at': execution.updated_at.isoformat()
        }
    
    def get_position_summary(self, account: str) -> Dict[str, Any]:
        """Get position summary for account"""
        
        positions = self.position_manager.get_all_positions(account)
        
        summary = {
            'account': account,
            'total_positions': len(positions),
            'long_positions': len([p for p in positions.values() if p['position'] > 0]),
            'short_positions': len([p for p in positions.values() if p['position'] < 0]),
            'positions': positions
        }
        
        return summary
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get fill processing statistics"""
        
        with self._lock:
            total_processed = len(self._processed_fills)
            total_failed = len(self._failed_fills)
            total_fills = total_processed + total_failed
        
        reconciliation_summary = self.reconciler.get_reconciliation_summary()
        
        return {
            'total_fills': total_fills,
            'processed_fills': total_processed,
            'failed_fills': total_failed,
            'success_rate': total_processed / total_fills if total_fills > 0 else 0,
            'reconciliation_summary': reconciliation_summary,
            'validation_rules': len(self.validator.validation_rules),
            'processor_status': 'running' if self._running else 'stopped'
        }
    
    def generate_daily_report(self, date: datetime) -> Dict[str, Any]:
        """Generate daily fill processing report"""
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # Execution report
        execution_df = self.reporter.generate_execution_report(start_date, end_date)
        
        # Performance summary
        performance_summary = self.reporter.generate_performance_summary(start_date, end_date)
        
        # Slippage analysis
        slippage_analysis = self.reporter.generate_slippage_analysis()
        
        # Reconciliation status
        reconciliation_summary = self.reconciler.get_reconciliation_summary()
        
        return {
            'report_date': date.strftime('%Y-%m-%d'),
            'execution_count': len(execution_df) if not execution_df.empty else 0,
            'performance_summary': performance_summary,
            'slippage_analysis': slippage_analysis,
            'reconciliation_summary': reconciliation_summary,
            'top_symbols': execution_df['symbol'].value_counts().head(10).to_dict() if not execution_df.empty else {},
            'venue_distribution': execution_df['venue'].value_counts().to_dict() if not execution_df.empty else {}
        }
    
    def start(self) -> None:
        """Start fill processor"""
        self._running = True
        logger.info("Fill Processor started")
    
    def stop(self) -> None:
        """Stop fill processor"""
        self._running = False
        logger.info("Fill Processor stopped")