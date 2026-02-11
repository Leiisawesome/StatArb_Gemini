"""
Pre-Trade Compliance Checker - Institutional Requirement
Ensures all trades comply with SEC regulations and internal policies BEFORE execution.

Architecture Compliance (Tier-1 Rules):
- Rule 3: Risk & Compliance Governance - Phase 7 (Pre-Trade Compliance)
  - 7 mandatory compliance checks before authorization
  - Integration with Phase 8 (Risk Authorization)
  - Feeds compliance result to CentralRiskManager

Compliance Checks (7 Mandatory per Rule 3):
1. Restricted Securities List - Internal compliance restrictions
2. Hard-to-Borrow (Reg SHO) - Share locate requirements for short sales
3. Insider Blackout Periods - Earnings blackouts, MNPI periods
4. 13D/G Filing Triggers - 5% ownership disclosure requirements
5. Pattern Day Trading Rules - 4 trades in 5 days, $25K minimum (Reg T)
6. Concentration Limits - Position concentration tracking
7. Watch List Monitoring - Compliance watch list alerts

Migration: December 2025 - Former Rule 4 Phase 7A content now Rule 3, Phase 7.

Author: Trading System Team
Date: December 6, 2025
Version: 2.0 (Rules Migration)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ComplianceViolationType(Enum):
    """Types of compliance violations"""
    RESTRICTED_SECURITY = "restricted_security"
    HARD_TO_BORROW = "hard_to_borrow"
    INSIDER_BLACKOUT = "insider_blackout"
    FILING_TRIGGER = "filing_trigger_13d_13g"
    PATTERN_DAY_TRADING = "pattern_day_trading"
    CONCENTRATION_LIMIT = "concentration_limit"
    WATCH_LIST = "watch_list"

@dataclass
class ComplianceResult:
    """
    Result of pre-trade compliance check

    Attributes:
        approved: Whether trade is compliant
        rejection_reason: Reason for rejection if not approved
        requires_manual_review: Whether manual review is needed
        compliance_checks_performed: List of checks performed
        warnings: Non-blocking warnings
        violation_type: Type of violation if rejected
    """
    approved: bool
    rejection_reason: Optional[str] = None
    requires_manual_review: bool = False
    compliance_checks_performed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    violation_type: Optional[ComplianceViolationType] = None

    def __post_init__(self):
        """Validate compliance result"""
        if not self.approved and not self.rejection_reason:
            raise ValueError("Rejection reason required when not approved")

class PreTradeComplianceChecker:
    """
    Pre-trade compliance engine (INSTITUTIONAL REQUIREMENT)

    Performs regulatory compliance checks BEFORE risk authorization.
    ALL trades must pass compliance before proceeding to risk checks.

    Integration Point: Called at start of CentralRiskManager.authorize_trading_decision()
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize compliance checker

        Args:
            config: Configuration dictionary with compliance parameters
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Restricted Securities Lists
        self.restricted_list: Set[str] = set()  # Internal restricted list
        self.watch_list: Set[str] = set()       # Compliance watch list

        # Hard-to-Borrow (HTB)
        self.hard_to_borrow: Set[str] = set()   # Current HTB list
        self.locate_cache: Dict[str, datetime] = {}  # Share locate cache (valid 1 day)

        # Insider Trading Controls
        self.blackout_periods: Dict[str, Tuple[datetime, datetime]] = {}  # symbol → (start, end)

        # Pattern Day Trading (PDT)
        self.account_type = self.config.get('account_type', 'margin')  # 'margin' or 'cash'
        self.account_equity = self.config.get('account_equity', 100000.0)
        self.pdt_threshold = 25000.0  # SEC requirement
        self.trade_history: List[Dict] = []  # Last 5 days

        # 13D/G Filing Triggers
        self.ownership_threshold = 0.05  # 5% ownership triggers filing
        self.current_ownership: Dict[str, float] = {}  # symbol → ownership %

        # Concentration Limits
        self.max_concentration = self.config.get('max_concentration', 0.20)  # 20% max per position
        self.portfolio_value = self.config.get('portfolio_value', 100000.0)

        # Statistics
        self.compliance_checks_performed = 0
        self.trades_approved = 0
        self.trades_rejected = 0
        self.rejection_reasons: Dict[str, int] = {}

        self.logger.info("✅ PreTradeComplianceChecker initialized")
        self.logger.info(f"   Account Type: {self.account_type}")
        self.logger.info(f"   Account Equity: ${self.account_equity:,.2f}")
        self.logger.info(f"   PDT Threshold: ${self.pdt_threshold:,.2f}")
        self.logger.info(f"   Max Concentration: {self.max_concentration:.1%}")

    async def check_pre_trade_compliance(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy_id: Optional[str] = None,
        account_id: Optional[str] = None
    ) -> ComplianceResult:
        """
        Perform comprehensive pre-trade compliance check

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            side: 'buy' or 'sell'
            quantity: Number of shares
            price: Expected execution price
            strategy_id: Strategy making the trade
            account_id: Trading account ID

        Returns:
            ComplianceResult with approval/rejection and reasons
        """
        self.compliance_checks_performed += 1
        checks_performed = []
        warnings = []

        try:
            self.logger.debug(f"Starting compliance checks for {symbol} {side} {quantity} @ ${price}")

            # CHECK 1: Restricted Securities List
            checks_performed.append("restricted_securities_check")
            if symbol in self.restricted_list:
                self.trades_rejected += 1
                self._record_rejection("restricted_security")
                return ComplianceResult(
                    approved=False,
                    rejection_reason=f"Security {symbol} is on internal restricted list",
                    compliance_checks_performed=checks_performed,
                    violation_type=ComplianceViolationType.RESTRICTED_SECURITY
                )

            # CHECK 2: Hard-to-Borrow (Reg SHO) - SHORT SALES ONLY
            checks_performed.append("hard_to_borrow_check")
            if side.lower() in ['sell', 'short']:
                htb_result = await self._check_hard_to_borrow(symbol, quantity)
                if not htb_result['available']:
                    self.trades_rejected += 1
                    self._record_rejection("hard_to_borrow")
                    return ComplianceResult(
                        approved=False,
                        rejection_reason=f"Security {symbol} is hard-to-borrow. Locate required.",
                        compliance_checks_performed=checks_performed,
                        violation_type=ComplianceViolationType.HARD_TO_BORROW
                    )
                elif htb_result.get('warning'):
                    warnings.append(f"HTB Warning: {htb_result['warning']}")

            # CHECK 3: Insider Blackout Periods
            checks_performed.append("insider_blackout_check")
            if symbol in self.blackout_periods:
                start, end = self.blackout_periods[symbol]
                if start <= datetime.now() <= end:
                    self.trades_rejected += 1
                    self._record_rejection("insider_blackout")
                    return ComplianceResult(
                        approved=False,
                        rejection_reason=f"Security {symbol} in blackout period until {end.strftime('%Y-%m-%d')}",
                        compliance_checks_performed=checks_performed,
                        violation_type=ComplianceViolationType.INSIDER_BLACKOUT
                    )

            # CHECK 4: 13D/G Filing Triggers (5%+ ownership)
            checks_performed.append("13d_13g_filing_check")
            if side.lower() == 'buy':
                filing_check = self._check_filing_triggers(symbol, quantity, price)
                if filing_check['requires_filing']:
                    self.trades_rejected += 1
                    self._record_rejection("filing_trigger")
                    return ComplianceResult(
                        approved=False,
                        rejection_reason=f"Trade would trigger 13D/G filing ({filing_check['new_ownership']:.2%} ownership)",
                        requires_manual_review=True,
                        compliance_checks_performed=checks_performed,
                        violation_type=ComplianceViolationType.FILING_TRIGGER
                    )
                elif filing_check.get('warning'):
                    warnings.append(filing_check['warning'])

            # CHECK 5: Pattern Day Trading Rules (Reg T)
            checks_performed.append("pattern_day_trading_check")
            pdt_check = self._check_pattern_day_trading(symbol, side)
            if not pdt_check['compliant']:
                self.trades_rejected += 1
                self._record_rejection("pattern_day_trading")
                return ComplianceResult(
                    approved=False,
                    rejection_reason=pdt_check['reason'],
                    compliance_checks_performed=checks_performed,
                    violation_type=ComplianceViolationType.PATTERN_DAY_TRADING
                )
            elif pdt_check.get('warning'):
                warnings.append(pdt_check['warning'])

            # CHECK 6: Concentration Limits
            checks_performed.append("concentration_limit_check")
            concentration_check = self._check_concentration_limits(symbol, side, quantity, price)
            if not concentration_check['compliant']:
                self.trades_rejected += 1
                self._record_rejection("concentration_limit")
                return ComplianceResult(
                    approved=False,
                    rejection_reason=concentration_check['reason'],
                    compliance_checks_performed=checks_performed,
                    violation_type=ComplianceViolationType.CONCENTRATION_LIMIT
                )
            elif concentration_check.get('warning'):
                warnings.append(concentration_check['warning'])

            # CHECK 7: Watch List Monitoring
            checks_performed.append("watch_list_check")
            if symbol in self.watch_list:
                warnings.append(f"Security {symbol} is on compliance watch list - extra scrutiny required")
                self.logger.warning(f"⚠️ Watch list alert: {symbol}")

            # ALL CHECKS PASSED
            self.trades_approved += 1
            self.logger.info(f"✅ Compliance approved: {symbol} {side} {quantity}")

            return ComplianceResult(
                approved=True,
                compliance_checks_performed=checks_performed,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"Compliance check error for {symbol}: {e}")
            self.trades_rejected += 1
            self._record_rejection("system_error")
            return ComplianceResult(
                approved=False,
                rejection_reason=f"Compliance check system error: {str(e)}",
                requires_manual_review=True,
                compliance_checks_performed=checks_performed
            )

    async def _check_hard_to_borrow(self, symbol: str, quantity: float) -> Dict:
        """
        Check if security is hard-to-borrow (Reg SHO compliance)

        For short sales, broker must have reasonable grounds to believe
        the security can be borrowed and delivered.
        """
        # Check if we have a valid locate
        if symbol in self.locate_cache:
            locate_time = self.locate_cache[symbol]
            if datetime.now() - locate_time < timedelta(days=1):
                return {'available': True, 'locate_cached': True}

        # Check HTB list
        if symbol in self.hard_to_borrow:
            return {
                'available': False,
                'reason': 'Security on hard-to-borrow list'
            }

        # In production, this would query broker API for HTB status
        # For now, assume available
        return {'available': True, 'locate_cached': False}

    def _check_filing_triggers(self, symbol: str, quantity: float, price: float) -> Dict:
        """
        Check if trade would trigger 13D or 13G filing (5%+ ownership)

        SEC requires disclosure of beneficial ownership of 5% or more
        of a voting class of equity securities.
        """
        # Get current ownership
        current_ownership = self.current_ownership.get(symbol, 0.0)

        # Calculate new ownership after trade
        # P2-2 FIX: shares_outstanding should come from market data, not be hardcoded.
        # Using a configurable default with explicit warning when using fallback.
        shares_outstanding = getattr(self, '_shares_outstanding_cache', {}).get(
            symbol,
            getattr(self.config, 'default_shares_outstanding', 1_000_000_000)
        )
        if shares_outstanding == getattr(self.config, 'default_shares_outstanding', 1_000_000_000):
            logger.debug(
                f"P2-2: Using default shares_outstanding ({shares_outstanding:,}) for {symbol} ownership calc. "
                "Wire market data provider for accurate compliance checks."
            )
        current_shares = current_ownership * shares_outstanding
        new_shares = current_shares + quantity
        new_ownership = new_shares / shares_outstanding

        if new_ownership >= self.ownership_threshold:
            return {
                'requires_filing': True,
                'current_ownership': current_ownership,
                'new_ownership': new_ownership,
                'filing_type': '13D' if new_ownership >= 0.05 else '13G'
            }

        # Warning if approaching threshold
        if new_ownership >= 0.045:  # 4.5% warning threshold
            return {
                'requires_filing': False,
                'warning': f"Approaching 5% ownership threshold: {new_ownership:.2%}"
            }

        return {'requires_filing': False}

    def _check_pattern_day_trading(self, symbol: str, side: str) -> Dict:
        """
        Check Pattern Day Trading rules (Reg T)

        A pattern day trader is someone who executes 4 or more day trades
        within 5 business days, provided the number of day trades is more
        than 6% of total trades. Requires minimum $25K equity.
        """
        # Cash accounts are exempt from PDT rules
        if self.account_type == 'cash':
            return {'compliant': True}

        # Count day trades in last 5 days
        five_days_ago = datetime.now() - timedelta(days=5)
        recent_trades = [t for t in self.trade_history if t['timestamp'] > five_days_ago]
        day_trades = self._count_day_trades(recent_trades)

        # Check if would become pattern day trader
        if day_trades >= 3:  # Would be 4th day trade
            if self.account_equity < self.pdt_threshold:
                return {
                    'compliant': False,
                    'reason': (
                        f"Pattern day trading restriction: {day_trades + 1} day trades in 5 days "
                        f"requires ${self.pdt_threshold:,.0f} equity (current: ${self.account_equity:,.0f})"
                    ),
                    'day_trades': day_trades + 1
                }

        # Warning if approaching PDT threshold
        if day_trades == 2:
            return {
                'compliant': True,
                'warning': f"Approaching PDT limit: {day_trades + 1}/4 day trades in 5 days"
            }

        return {'compliant': True, 'day_trades': day_trades}

    def _count_day_trades(self, trades: List[Dict]) -> int:
        """Count day trades (buy and sell same symbol same day)"""
        # Group trades by date and symbol
        day_trades = 0
        trades_by_day = {}

        for trade in trades:
            date = trade['timestamp'].date()
            symbol = trade['symbol']
            key = (date, symbol)

            if key not in trades_by_day:
                trades_by_day[key] = {'buys': 0, 'sells': 0}

            if trade['side'].lower() == 'buy':
                trades_by_day[key]['buys'] += 1
            else:
                trades_by_day[key]['sells'] += 1

        # Count days with both buy and sell
        for counts in trades_by_day.values():
            if counts['buys'] > 0 and counts['sells'] > 0:
                day_trades += 1

        return day_trades

    def _check_concentration_limits(self, symbol: str, side: str, quantity: float, price: float) -> Dict:
        """
        Check position concentration limits

        Prevents over-concentration in single position
        """
        if side.lower() != 'buy':
            return {'compliant': True}

        position_value = quantity * price
        concentration = position_value / self.portfolio_value

        if concentration > self.max_concentration:
            return {
                'compliant': False,
                'reason': (
                    f"Position concentration {concentration:.1%} exceeds limit {self.max_concentration:.1%} "
                    f"(${position_value:,.0f} / ${self.portfolio_value:,.0f})"
                ),
                'concentration': concentration
            }

        # Warning at 80% of limit
        if concentration > self.max_concentration * 0.8:
            return {
                'compliant': True,
                'warning': f"High concentration: {concentration:.1%} of portfolio"
            }

        return {'compliant': True}

    def _record_rejection(self, reason: str):
        """Record rejection for statistics"""
        if reason not in self.rejection_reasons:
            self.rejection_reasons[reason] = 0
        self.rejection_reasons[reason] += 1

    # Configuration Management Methods

    def add_to_restricted_list(self, symbols: List[str]):
        """Add symbols to restricted securities list"""
        self.restricted_list.update(symbols)
        self.logger.info(f"Added {len(symbols)} symbols to restricted list")

    def remove_from_restricted_list(self, symbols: List[str]):
        """Remove symbols from restricted securities list"""
        self.restricted_list.difference_update(symbols)
        self.logger.info(f"Removed {len(symbols)} symbols from restricted list")

    def add_to_watch_list(self, symbols: List[str]):
        """Add symbols to compliance watch list"""
        self.watch_list.update(symbols)
        self.logger.info(f"Added {len(symbols)} symbols to watch list")

    def set_blackout_period(self, symbol: str, start: datetime, end: datetime):
        """Set insider trading blackout period for symbol"""
        self.blackout_periods[symbol] = (start, end)
        self.logger.info(f"Blackout period set for {symbol}: {start} to {end}")

    def update_htb_list(self, htb_symbols: Set[str]):
        """Update hard-to-borrow list (typically from broker)"""
        self.hard_to_borrow = htb_symbols
        self.logger.info(f"HTB list updated: {len(htb_symbols)} securities")

    def record_trade(self, symbol: str, side: str, quantity: float, timestamp: datetime):
        """Record trade for PDT tracking"""
        self.trade_history.append({
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'timestamp': timestamp
        })

        # Keep only last 5 days
        five_days_ago = datetime.now() - timedelta(days=5)
        self.trade_history = [t for t in self.trade_history if t['timestamp'] > five_days_ago]

    # Statistics and Reporting

    def get_compliance_statistics(self) -> Dict:
        """Get compliance check statistics"""
        return {
            'checks_performed': self.compliance_checks_performed,
            'trades_approved': self.trades_approved,
            'trades_rejected': self.trades_rejected,
            'approval_rate': self.trades_approved / max(1, self.compliance_checks_performed),
            'rejection_reasons': dict(self.rejection_reasons),
            'restricted_list_size': len(self.restricted_list),
            'watch_list_size': len(self.watch_list),
            'htb_list_size': len(self.hard_to_borrow),
            'active_blackout_periods': len(self.blackout_periods)
        }

    def generate_compliance_report(self) -> str:
        """Generate compliance report"""
        stats = self.get_compliance_statistics()

        report = [
            "=" * 60,
            "PRE-TRADE COMPLIANCE REPORT",
            "=" * 60,
            f"Total Checks Performed: {stats['checks_performed']:,}",
            f"Trades Approved:        {stats['trades_approved']:,} ({stats['approval_rate']:.1%})",
            f"Trades Rejected:        {stats['trades_rejected']:,}",
            "",
            "REJECTION BREAKDOWN:",
            *[f"  - {reason}: {count}" for reason, count in stats['rejection_reasons'].items()],
            "",
            "COMPLIANCE LISTS:",
            f"  - Restricted Securities: {stats['restricted_list_size']}",
            f"  - Watch List:           {stats['watch_list_size']}",
            f"  - Hard-to-Borrow:       {stats['htb_list_size']}",
            f"  - Active Blackouts:     {stats['active_blackout_periods']}",
            "=" * 60
        ]

        return "\n".join(report)

