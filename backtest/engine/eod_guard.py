"""
EOD Guard
=========

Encapsulates all end-of-day guard logic for the backtest engine.

Responsibilities:
- Parse EOD close times from strategy configurations
- Determine if the EOD guard is active for a given timestamp
- Filter pending signals at EOD (keep exits, discard entries)
- Track which dates have already been liquidated (idempotency flag)

This class is a pure logic extractor — it reads config but does NOT perform
actual liquidation (that remains in the engine, which owns risk_manager and
execution_simulator).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class EODGuard:
    """Stateful helper that centralises EOD time parsing, guard checks, and signal filtering."""

    # Signal types that are treated as exits (allowed through the EOD gate)
    _EXIT_TYPES = frozenset({
        'sell', 'long_exit', 'short_exit', 'close', 'close_long',
        'close_short', 'cover', 'flatten',
    })

    def __init__(self, config):
        """
        Args:
            config: BacktestConfig (or any object with a `strategies` attribute).
        """
        self._config = config
        self._eod_flags: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_liquidated(self, date) -> None:
        """Record that EOD liquidation has fired for *date*."""
        key = f"eod_liquidated_{date}"
        self._eod_flags[key] = True

    def already_liquidated(self, date) -> bool:
        """Return True if liquidation already happened for *date*."""
        key = f"eod_liquidated_{date}"
        return self._eod_flags.get(key, False)

    def is_active(self, timestamp) -> bool:
        """
        Return True if the EOD guard should block new entry signals.

        Two checks (matching original inline logic):
          1. Liquidation already fired today (_eod_flags set).
          2. Proactive: current bar time >= earliest eod_close_time across all
             strategies that have enable_eod_liquidation.
        """
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is not None:
            ts = ts.tz_convert('America/New_York')

        # Check 1: flag-based
        if self.already_liquidated(ts.date()):
            return True

        # Check 2: proactive time-based
        try:
            current_mins = ts.hour * 60 + ts.minute
            earliest = self._earliest_eod_minutes()
            if earliest is not None and current_mins >= earliest:
                logger.debug(
                    "EOD proactive guard: bar %s >= eod_close_time %02d:%02d",
                    ts.strftime('%H:%M'), earliest // 60, earliest % 60,
                )
                return True
        except Exception:
            pass  # Non-fatal — fall through

        return False

    def filter_signals(self, pending_signals: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Keep only EXIT signals; discard ENTRY signals.

        Returns:
            (kept_signals, discarded_count)
        """
        kept: List[Dict[str, Any]] = []
        discarded = 0
        for sig in pending_signals:
            sig_type = str(sig.get('signal_type', sig.get('side', ''))).lower()
            is_exit = sig.get('is_exit', False) or sig_type in self._EXIT_TYPES
            if is_exit:
                kept.append(sig)
            else:
                discarded += 1
        return kept, discarded

    def should_liquidate_position(
        self,
        timestamp,
        symbol: str,
        strategy_id: Optional[str],
        get_strategy_param_fn,
    ) -> bool:
        """
        Check whether a specific position should be liquidated based on its
        strategy's EOD configuration and the current time.

        Args:
            timestamp: Current bar timestamp
            symbol: Position symbol (for logging)
            strategy_id: Owning strategy (may be None)
            get_strategy_param_fn: Callable(param_name, default, strategy_id=...) -> value

        Returns:
            True if this position should be liquidated now
        """
        enable_eod = get_strategy_param_fn('enable_eod_liquidation', False, strategy_id=strategy_id)
        if not enable_eod:
            return False

        eod_time_str = get_strategy_param_fn('eod_close_time', '15:55', strategy_id=strategy_id)
        eod_hour, eod_minute = self._parse_time(eod_time_str)
        eod_time_mins = eod_hour * 60 + eod_minute

        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is not None:
            ts = ts.tz_convert('America/New_York')
        current_mins = ts.hour * 60 + ts.minute

        return current_mins >= eod_time_mins

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _earliest_eod_minutes(self) -> Optional[int]:
        """Return the earliest EOD close time (in minutes since midnight) across all strategies."""
        strategies = getattr(self._config, 'strategies', None)
        if not strategies:
            return None

        earliest = None
        for strat in strategies:
            params = strat.get('parameters', {}) if isinstance(strat, dict) else {}
            if params.get('enable_eod_liquidation', False):
                eod_str = params.get('eod_close_time', '15:55')
                h, m = self._parse_time(eod_str)
                mins = h * 60 + m
                if earliest is None or mins < earliest:
                    earliest = mins
        return earliest

    @staticmethod
    def _parse_time(time_str: str) -> Tuple[int, int]:
        """Parse 'HH:MM' -> (hour, minute) with safe fallback."""
        try:
            h, m = map(int, time_str.split(':'))
            return h, m
        except (ValueError, AttributeError):
            return 15, 55
