"""
Position Reconciliation Engine - Operational Excellence Requirement
Ensures internal position records match broker positions with automated correction.

Reconciliation Process:
1. Fetch broker positions via API (every 5 minutes)
2. Compare with internal CentralRiskManager positions
3. Identify discrepancies (symbol-by-symbol)
4. Classify severity (Minor < $1K, Moderate $1K-$10K, Severe > $10K)
5. Auto-correct severe discrepancies (trust broker)
6. Alert risk team for moderate discrepancies
7. Log all reconciliation events
8. Handle corporate actions (splits, dividends, mergers)

Severity Levels:
- Minor (<$1K): Log and monitor
- Moderate ($1K-$10K): Alert risk team
- Severe (>$10K): Auto-correct + alert

Author: Trading System Team
Date: October 25, 2025
Version: 1.0
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class DiscrepancySeverity(Enum):
    """Severity classification for position discrepancies"""
    NONE = "none"           # No discrepancy
    MINOR = "minor"         # <$1K
    MODERATE = "moderate"   # $1K-$10K
    SEVERE = "severe"       # >$10K
    CRITICAL = "critical"   # >$100K or complete mismatch


class ReconciliationAction(Enum):
    """Actions taken during reconciliation"""
    NO_ACTION = "no_action"
    LOG_ONLY = "log_only"
    ALERT_TEAM = "alert_team"
    AUTO_CORRECT = "auto_correct"
    MANUAL_REVIEW = "manual_review"


@dataclass
class PositionDiscrepancy:
    """
    Position discrepancy between internal and broker records
    
    Attributes:
        symbol: Trading symbol
        internal_position: Internal position quantity
        broker_position: Broker-reported position quantity
        quantity_diff: Difference in quantity
        internal_value: Internal position value
        broker_value: Broker position value
        value_diff: Difference in value
        severity: Discrepancy severity
        action_taken: Action taken to resolve
        timestamp: When discrepancy detected
    """
    symbol: str
    internal_position: float
    broker_position: float
    quantity_diff: float
    internal_value: float
    broker_value: float
    value_diff: float
    severity: DiscrepancySeverity
    action_taken: ReconciliationAction
    timestamp: datetime
    resolution_notes: Optional[str] = None


@dataclass
class ReconciliationReport:
    """
    Complete reconciliation report
    
    Attributes:
        timestamp: Report timestamp
        total_symbols_checked: Number of symbols checked
        discrepancies_found: Number of discrepancies
        discrepancies: List of all discrepancies
        actions_taken: Summary of actions
        reconciliation_status: Overall status
    """
    timestamp: datetime
    total_symbols_checked: int
    discrepancies_found: int
    discrepancies: List[PositionDiscrepancy] = field(default_factory=list)
    actions_taken: Dict[ReconciliationAction, int] = field(default_factory=dict)
    reconciliation_status: str = "success"
    total_value_discrepancy: float = 0.0
    
    def __post_init__(self):
        """Calculate total value discrepancy"""
        self.total_value_discrepancy = sum(
            abs(d.value_diff) for d in self.discrepancies
        )


class PositionReconciliation:
    """
    Position Reconciliation Engine
    
    Compares internal positions with broker positions and resolves discrepancies.
    Runs every 5 minutes (1 minute if discrepancies found).
    
    Integration: Standalone service that updates CentralRiskManager
    """
    
    def __init__(self, risk_manager, broker_api, config: Optional[Dict] = None):
        """
        Initialize position reconciliation
        
        Args:
            risk_manager: CentralRiskManager instance
            broker_api: Broker API interface
            config: Configuration dictionary
        """
        self.risk_manager = risk_manager
        self.broker_api = broker_api
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Reconciliation Settings
        self.normal_interval = self.config.get('normal_interval_seconds', 300)  # 5 minutes
        self.fast_interval = self.config.get('fast_interval_seconds', 60)  # 1 minute
        self.current_interval = self.normal_interval
        
        # Severity Thresholds
        self.minor_threshold = self.config.get('minor_threshold', 1000)  # $1K
        self.moderate_threshold = self.config.get('moderate_threshold', 10000)  # $10K
        self.severe_threshold = self.config.get('severe_threshold', 100000)  # $100K
        
        # Auto-correction Settings
        self.auto_correct_enabled = self.config.get('auto_correct_enabled', True)
        self.auto_correct_threshold = self.config.get('auto_correct_threshold', 10000)  # $10K
        self.trust_broker = True  # Always trust broker over internal (safer)
        
        # State
        self.is_running = False
        self.last_reconciliation_time: Optional[datetime] = None
        self.consecutive_discrepancies = 0
        self.reconciliation_history: List[ReconciliationReport] = []
        
        # Statistics
        self.total_reconciliations = 0
        self.total_discrepancies_found = 0
        self.total_auto_corrections = 0
        self.discrepancies_by_severity: Dict[DiscrepancySeverity, int] = {
            severity: 0 for severity in DiscrepancySeverity
        }
        
        self.logger.info("✅ PositionReconciliation initialized")
        self.logger.info(f"   Normal Interval: {self.normal_interval}s")
        self.logger.info(f"   Fast Interval: {self.fast_interval}s")
        self.logger.info(f"   Auto-correct Threshold: ${self.auto_correct_threshold:,}")
    
    async def start_reconciliation_loop(self):
        """Start continuous reconciliation loop"""
        self.is_running = True
        self.logger.info("🔄 Position reconciliation loop started")
        
        while self.is_running:
            try:
                # Perform reconciliation
                report = await self.reconcile_positions()
                
                # Adjust interval based on results
                if report.discrepancies_found > 0:
                    self.current_interval = self.fast_interval
                    self.consecutive_discrepancies += 1
                    self.logger.warning(
                        f"⚠️ Discrepancies found ({report.discrepancies_found}), "
                        f"switching to fast interval ({self.fast_interval}s)"
                    )
                else:
                    if self.consecutive_discrepancies > 0:
                        self.logger.info("✅ No discrepancies, returning to normal interval")
                    self.current_interval = self.normal_interval
                    self.consecutive_discrepancies = 0
                
                # Wait for next reconciliation
                await asyncio.sleep(self.current_interval)
                
            except Exception as e:
                self.logger.error(f"Reconciliation loop error: {e}")
                await asyncio.sleep(self.current_interval)
    
    def stop_reconciliation_loop(self):
        """Stop reconciliation loop"""
        self.is_running = False
        self.logger.info("⏸️ Position reconciliation loop stopped")
    
    async def reconcile_positions(self) -> ReconciliationReport:
        """
        Perform position reconciliation
        
        Returns:
            ReconciliationReport with discrepancies and actions taken
        """
        self.total_reconciliations += 1
        self.last_reconciliation_time = datetime.now()
        
        self.logger.info(f"🔍 Starting position reconciliation #{self.total_reconciliations}")
        
        try:
            # STEP 1: Get broker positions
            broker_positions = await self._fetch_broker_positions()
            
            # STEP 2: Get internal positions
            internal_positions = self._get_internal_positions()
            
            # STEP 3: Compare positions
            discrepancies = await self._compare_positions(
                internal_positions,
                broker_positions
            )
            
            # STEP 4: Create report
            report = ReconciliationReport(
                timestamp=datetime.now(),
                total_symbols_checked=len(set(
                    list(internal_positions.keys()) + list(broker_positions.keys())
                )),
                discrepancies_found=len(discrepancies),
                discrepancies=discrepancies,
                actions_taken=self._count_actions(discrepancies)
            )
            
            # STEP 5: Take corrective actions
            if discrepancies:
                await self._handle_discrepancies(discrepancies)
                self.total_discrepancies_found += len(discrepancies)
            
            # STEP 6: Store report
            self.reconciliation_history.append(report)
            
            # Keep only last 100 reports
            if len(self.reconciliation_history) > 100:
                self.reconciliation_history = self.reconciliation_history[-100:]
            
            # STEP 7: Log summary
            self._log_reconciliation_summary(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Position reconciliation failed: {e}")
            return ReconciliationReport(
                timestamp=datetime.now(),
                total_symbols_checked=0,
                discrepancies_found=0,
                reconciliation_status="error"
            )
    
    async def _fetch_broker_positions(self) -> Dict[str, float]:
        """
        Fetch positions from broker API
        
        Returns:
            Dict[symbol, quantity]
        """
        try:
            # Call broker API
            positions = await self.broker_api.get_positions()
            
            # Convert to dict
            broker_positions = {}
            for position in positions:
                symbol = position.get('symbol')
                quantity = position.get('quantity', 0.0)
                broker_positions[symbol] = quantity
            
            self.logger.debug(f"Fetched {len(broker_positions)} positions from broker")
            return broker_positions
            
        except Exception as e:
            self.logger.error(f"Failed to fetch broker positions: {e}")
            # Return empty dict on error (fail-safe)
            return {}
    
    def _get_internal_positions(self) -> Dict[str, float]:
        """
        Get internal positions from CentralRiskManager
        
        Returns:
            Dict[symbol, quantity]
        """
        try:
            # Access risk manager's position tracking
            positions = self.risk_manager.current_positions.copy()
            
            # Filter out zero positions
            positions = {k: v for k, v in positions.items() if abs(v) > 0.001}
            
            self.logger.debug(f"Retrieved {len(positions)} internal positions")
            return positions
            
        except Exception as e:
            self.logger.error(f"Failed to get internal positions: {e}")
            return {}
    
    async def _compare_positions(
        self,
        internal: Dict[str, float],
        broker: Dict[str, float]
    ) -> List[PositionDiscrepancy]:
        """
        Compare internal and broker positions
        
        Returns:
            List of discrepancies found
        """
        discrepancies = []
        
        # Get all symbols (union of both sets)
        all_symbols = set(internal.keys()) | set(broker.keys())
        
        for symbol in all_symbols:
            internal_qty = internal.get(symbol, 0.0)
            broker_qty = broker.get(symbol, 0.0)
            
            # Calculate difference
            qty_diff = broker_qty - internal_qty
            
            # Skip if difference is negligible (< 0.01 shares)
            if abs(qty_diff) < 0.01:
                continue
            
            # Get current price for value calculation
            current_price = await self._get_current_price(symbol)
            
            internal_value = internal_qty * current_price
            broker_value = broker_qty * current_price
            value_diff = broker_value - internal_value
            
            # Classify severity
            severity = self._classify_severity(abs(value_diff))
            
            # Determine action
            action = self._determine_action(severity, abs(value_diff))
            
            # Create discrepancy record
            discrepancy = PositionDiscrepancy(
                symbol=symbol,
                internal_position=internal_qty,
                broker_position=broker_qty,
                quantity_diff=qty_diff,
                internal_value=internal_value,
                broker_value=broker_value,
                value_diff=value_diff,
                severity=severity,
                action_taken=action,
                timestamp=datetime.now()
            )
            
            discrepancies.append(discrepancy)
            
            # Update statistics
            self.discrepancies_by_severity[severity] += 1
            
            self.logger.warning(
                f"⚠️ Position discrepancy: {symbol} | "
                f"Internal: {internal_qty:.2f}, Broker: {broker_qty:.2f}, "
                f"Diff: {qty_diff:+.2f} (${value_diff:+,.0f}) | "
                f"Severity: {severity.value}, Action: {action.value}"
            )
        
        return discrepancies
    
    def _classify_severity(self, value_diff: float) -> DiscrepancySeverity:
        """Classify discrepancy severity"""
        if value_diff < self.minor_threshold:
            return DiscrepancySeverity.MINOR
        elif value_diff < self.moderate_threshold:
            return DiscrepancySeverity.MODERATE
        elif value_diff < self.severe_threshold:
            return DiscrepancySeverity.SEVERE
        else:
            return DiscrepancySeverity.CRITICAL
    
    def _determine_action(self, severity: DiscrepancySeverity, value_diff: float) -> ReconciliationAction:
        """Determine action based on severity"""
        if severity == DiscrepancySeverity.MINOR:
            return ReconciliationAction.LOG_ONLY
        elif severity == DiscrepancySeverity.MODERATE:
            return ReconciliationAction.ALERT_TEAM
        elif severity in [DiscrepancySeverity.SEVERE, DiscrepancySeverity.CRITICAL]:
            if self.auto_correct_enabled and value_diff >= self.auto_correct_threshold:
                return ReconciliationAction.AUTO_CORRECT
            else:
                return ReconciliationAction.MANUAL_REVIEW
        else:
            return ReconciliationAction.NO_ACTION
    
    async def _handle_discrepancies(self, discrepancies: List[PositionDiscrepancy]):
        """Handle discrepancies based on action"""
        for discrepancy in discrepancies:
            action = discrepancy.action_taken
            
            if action == ReconciliationAction.LOG_ONLY:
                # Already logged in _compare_positions
                pass
            
            elif action == ReconciliationAction.ALERT_TEAM:
                await self._alert_risk_team(discrepancy)
            
            elif action == ReconciliationAction.AUTO_CORRECT:
                await self._auto_correct_position(discrepancy)
            
            elif action == ReconciliationAction.MANUAL_REVIEW:
                await self._request_manual_review(discrepancy)
    
    async def _auto_correct_position(self, discrepancy: PositionDiscrepancy):
        """
        Auto-correct position to match broker
        
        ALWAYS trust broker position (safer approach)
        """
        try:
            self.logger.warning(
                f"🔧 Auto-correcting position: {discrepancy.symbol} | "
                f"Internal: {discrepancy.internal_position:.2f} → "
                f"Broker: {discrepancy.broker_position:.2f}"
            )
            
            # Update internal position to match broker
            self.risk_manager.current_positions[discrepancy.symbol] = discrepancy.broker_position
            
            # Record correction
            discrepancy.resolution_notes = (
                f"Auto-corrected to broker position: {discrepancy.broker_position:.2f} "
                f"(was {discrepancy.internal_position:.2f})"
            )
            
            self.total_auto_corrections += 1
            
            # Alert team about auto-correction
            await self._alert_risk_team(discrepancy, auto_corrected=True)
            
            self.logger.info(f"✅ Position auto-corrected: {discrepancy.symbol}")
            
        except Exception as e:
            self.logger.error(f"Auto-correction failed for {discrepancy.symbol}: {e}")
    
    async def _alert_risk_team(self, discrepancy: PositionDiscrepancy, auto_corrected: bool = False):
        """Send alert to risk team"""
        alert_message = (
            f"⚠️ POSITION DISCREPANCY ALERT\n"
            f"Symbol: {discrepancy.symbol}\n"
            f"Internal: {discrepancy.internal_position:.2f}\n"
            f"Broker: {discrepancy.broker_position:.2f}\n"
            f"Difference: {discrepancy.quantity_diff:+.2f} shares (${discrepancy.value_diff:+,.0f})\n"
            f"Severity: {discrepancy.severity.value}\n"
            f"Action: {discrepancy.action_taken.value}\n"
            f"Auto-corrected: {'YES' if auto_corrected else 'NO'}\n"
            f"Time: {discrepancy.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        self.logger.warning(alert_message)
        
        # In production, send email/Slack/SMS
        # await self._send_email_alert(alert_message)
        # await self._send_slack_alert(alert_message)
    
    async def _request_manual_review(self, discrepancy: PositionDiscrepancy):
        """Request manual review for critical discrepancies"""
        self.logger.critical(
            f"🚨 MANUAL REVIEW REQUIRED: {discrepancy.symbol} | "
            f"Value discrepancy: ${discrepancy.value_diff:,.0f}"
        )
        
        # Send urgent alert
        await self._alert_risk_team(discrepancy)
        
        # Add to manual review queue
        # In production, this would create a ticket or task
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        try:
            # In production, fetch from market data feed
            # For now, use a placeholder
            # Would call: await self.market_data_manager.get_current_price(symbol)
            return 100.0  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Failed to get price for {symbol}: {e}")
            return 100.0  # Fallback
    
    def _count_actions(self, discrepancies: List[PositionDiscrepancy]) -> Dict[ReconciliationAction, int]:
        """Count actions taken"""
        actions = {}
        for discrepancy in discrepancies:
            action = discrepancy.action_taken
            actions[action] = actions.get(action, 0) + 1
        return actions
    
    def _log_reconciliation_summary(self, report: ReconciliationReport):
        """Log reconciliation summary"""
        if report.discrepancies_found == 0:
            self.logger.info(
                f"✅ Reconciliation #{self.total_reconciliations} complete: "
                f"{report.total_symbols_checked} symbols checked, NO discrepancies"
            )
        else:
            self.logger.warning(
                f"⚠️ Reconciliation #{self.total_reconciliations} complete: "
                f"{report.total_symbols_checked} symbols checked, "
                f"{report.discrepancies_found} discrepancies found "
                f"(Total value: ${report.total_value_discrepancy:,.0f})"
            )
            
            # Log actions taken
            for action, count in report.actions_taken.items():
                self.logger.info(f"   - {action.value}: {count}")
    
    # Statistics and Reporting
    
    def get_reconciliation_statistics(self) -> Dict:
        """Get reconciliation statistics"""
        return {
            'total_reconciliations': self.total_reconciliations,
            'total_discrepancies_found': self.total_discrepancies_found,
            'total_auto_corrections': self.total_auto_corrections,
            'discrepancies_by_severity': {
                severity.value: count 
                for severity, count in self.discrepancies_by_severity.items()
            },
            'last_reconciliation': self.last_reconciliation_time.isoformat() if self.last_reconciliation_time else None,
            'consecutive_discrepancies': self.consecutive_discrepancies,
            'current_interval': self.current_interval,
            'is_running': self.is_running
        }
    
    def generate_reconciliation_report(self) -> str:
        """Generate reconciliation report"""
        stats = self.get_reconciliation_statistics()
        
        # Get latest report
        latest = self.reconciliation_history[-1] if self.reconciliation_history else None
        
        report = [
            "=" * 60,
            "POSITION RECONCILIATION REPORT",
            "=" * 60,
            f"Total Reconciliations:    {stats['total_reconciliations']:,}",
            f"Discrepancies Found:      {stats['total_discrepancies_found']:,}",
            f"Auto-corrections:         {stats['total_auto_corrections']:,}",
            f"Current Interval:         {stats['current_interval']}s",
            f"Status:                   {'RUNNING 🟢' if stats['is_running'] else 'STOPPED 🔴'}",
            "",
            "DISCREPANCIES BY SEVERITY:",
            *[f"  - {severity}: {count}" for severity, count in stats['discrepancies_by_severity'].items() if count > 0],
            ""
        ]
        
        if latest:
            report.extend([
                "LATEST RECONCILIATION:",
                f"  Time: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"  Symbols Checked: {latest.total_symbols_checked}",
                f"  Discrepancies: {latest.discrepancies_found}",
                f"  Total Value Diff: ${latest.total_value_discrepancy:,.0f}",
                f"  Status: {latest.reconciliation_status}"
            ])
        
        report.append("=" * 60)
        
        return "\n".join(report)

