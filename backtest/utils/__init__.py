"""
Experiment Suite Utilities
===========================

Shared utilities for experiment orchestration.

Author: StatArb_Gemini Core Engine
"""

from .config_loader import load_config, save_config
from datetime import datetime
from typing import Any, Dict


def trade_timestamp_key(trade: Dict[str, Any]):
    """
    Extract a comparable timestamp key from a trade dict.

    Shared utility for sorting trade lists deterministically (M4 fix —
    was duplicated in smoke_test.py and base_experiment.py).
    """
    ts = trade.get('timestamp')
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return ts
    return ts


__all__ = [
    'load_config',
    'save_config',
    'trade_timestamp_key',
]
