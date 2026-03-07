#!/usr/bin/env python3
"""Parity audit utility for Polygon historical tick streamer.

Compares streamer-emitted message payload keys against the canonical
live websocket schema used by PolygonRealtimeFeedAdapter.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

from .polygon_tick_streamer import PolygonHistoricalTickStreamer, PolygonTickStreamerConfig


LIVE_CANONICAL_DATA_KEYS: Dict[str, Set[str]] = {
    "trade": {"price", "size", "conditions", "exchange", "tape"},
    "quote": {"bid", "bid_size", "ask", "ask_size", "bid_exchange", "ask_exchange", "conditions"},
    "second_agg": {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "num_trades",
        "bar_type",
        "timestamp_start",
        "timestamp_end",
        "otc",
    },
    "minute_agg": {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "num_trades",
        "bar_type",
        "timestamp_start",
        "timestamp_end",
        "otc",
    },
}

LIVE_CANONICAL_FIELD_TYPES: Dict[str, Dict[str, Tuple[type, ...]]] = {
    "trade": {
        "price": (float,),
        "size": (int,),
        "conditions": (list,),
        "exchange": (int,),
        "tape": (int,),
    },
    "quote": {
        "bid": (float,),
        "bid_size": (int,),
        "ask": (float,),
        "ask_size": (int,),
        "bid_exchange": (int,),
        "ask_exchange": (int,),
        "conditions": (list,),
    },
    "second_agg": {
        "open": (float,),
        "high": (float,),
        "low": (float,),
        "close": (float,),
        "volume": (float,),
        "vwap": (float,),
        "num_trades": (int,),
        "bar_type": (str,),
        "timestamp_start": (str,),
        "timestamp_end": (str,),
        "otc": (bool,),
    },
    "minute_agg": {
        "open": (float,),
        "high": (float,),
        "low": (float,),
        "close": (float,),
        "volume": (float,),
        "vwap": (float,),
        "num_trades": (int,),
        "bar_type": (str,),
        "timestamp_start": (str,),
        "timestamp_end": (str,),
        "otc": (bool,),
    },
}


@dataclass
class ParityDiff:
    message_type: str
    missing_keys: List[str]
    extra_keys: List[str]
    type_mismatches: Dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.missing_keys and not self.extra_keys and not self.type_mismatches


def _type_label(type_tuple: Tuple[type, ...]) -> str:
    return " | ".join(expected_type.__name__ for expected_type in type_tuple)


def _value_matches_type(value: Any, expected_types: Tuple[type, ...]) -> bool:
    for expected_type in expected_types:
        if expected_type is bool:
            if type(value) is bool:
                return True
            continue
        if expected_type is int:
            if isinstance(value, int) and type(value) is not bool:
                return True
            continue
        if isinstance(value, expected_type):
            return True
    return False


def _build_sample_messages(strict_live_parity: bool) -> Dict[str, Dict[str, object]]:
    start = datetime(2025, 1, 2, 14, 30, 59, tzinfo=timezone.utc)
    end = start + timedelta(minutes=2)

    config = PolygonTickStreamerConfig(
        symbols=["AAPL"],
        start_time=start,
        end_time=end,
        api_key="parity-audit-dummy-key",
        playback_speed=float("inf"),
        emit_trade=True,
        emit_quote=True,
        emit_second_agg=True,
        emit_minute_agg=True,
        strict_live_parity=strict_live_parity,
        full_fidelity=True,
    )
    streamer = PolygonHistoricalTickStreamer(config)

    row = pd.Series(
        {
            "trade_price": 100.12,
            "trade_size": 25,
            "trade_exchange": 4,
            "trade_count": 3,
            "trade_tape": 2,
            "trade_sequence_number": 4242,
            "trade_conditions": [12, 37],
            "quote_bid": 100.10,
            "quote_ask": 100.14,
            "quote_bid_size": 10,
            "quote_ask_size": 12,
            "quote_bid_exchange": 8,
            "quote_ask_exchange": 9,
            "quote_conditions": [1],
            "quote_count": 2,
            "quote_age_ms": 150.0,
            "spread": 0.04,
        }
    )

    minute_state: Dict[str, Dict[str, object]] = {}
    allowed_types = {"trade", "quote", "second_agg", "minute_agg"}

    messages = []
    messages.extend(
        streamer._row_to_messages(
            symbol="AAPL",
            timestamp=start,
            row=row,
            allowed_types=allowed_types,
            minute_state=minute_state,
        )
    )
    messages.extend(
        streamer._row_to_messages(
            symbol="AAPL",
            timestamp=start + timedelta(seconds=1),
            row=row,
            allowed_types=allowed_types,
            minute_state=minute_state,
        )
    )

    by_type: Dict[str, Dict[str, object]] = {}
    for message in messages:
        by_type.setdefault(message.message_type, message.data)
    return by_type


def run_parity_audit(strict_live_parity: bool = True) -> Dict[str, ParityDiff]:
    """Compare streamer payload keys and field types to canonical live websocket schema."""
    sample = _build_sample_messages(strict_live_parity=strict_live_parity)
    diffs: Dict[str, ParityDiff] = {}

    for message_type, expected_keys in LIVE_CANONICAL_DATA_KEYS.items():
        payload = sample.get(message_type, {})
        actual_keys = set(payload.keys())
        type_mismatches: Dict[str, str] = {}

        for key, expected_types in LIVE_CANONICAL_FIELD_TYPES[message_type].items():
            if key not in payload:
                continue
            value = payload[key]
            if not _value_matches_type(value, expected_types):
                type_mismatches[key] = (
                    f"expected {_type_label(expected_types)}, got {type(value).__name__}"
                )

        diffs[message_type] = ParityDiff(
            message_type=message_type,
            missing_keys=sorted(expected_keys - actual_keys),
            extra_keys=sorted(actual_keys - expected_keys),
            type_mismatches=type_mismatches,
        )

    return diffs


def _print_report(diffs: Dict[str, ParityDiff]) -> None:
    print("Polygon Streamer Parity Audit")
    print("=" * 40)
    for message_type in ["trade", "quote", "second_agg", "minute_agg"]:
        diff = diffs[message_type]
        status = "PASS" if diff.passed else "FAIL"
        print(f"{message_type:<10} {status}")
        if diff.missing_keys:
            print(f"  missing: {diff.missing_keys}")
        if diff.extra_keys:
            print(f"  extra  : {diff.extra_keys}")
        if diff.type_mismatches:
            print(f"  types  : {diff.type_mismatches}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit streamer payload parity with live websocket schema")
    parser.add_argument(
        "--allow-enriched-replay",
        action="store_true",
        help="Audit enriched mode instead of strict live parity mode",
    )
    parser.add_argument(
        "--fail-on-diff",
        action="store_true",
        help="Return exit code 1 if any mismatch is found",
    )
    args = parser.parse_args()

    strict_mode = not args.allow_enriched_replay
    diffs = run_parity_audit(strict_live_parity=strict_mode)
    _print_report(diffs)

    has_diff = any(not diff.passed for diff in diffs.values())
    if has_diff and args.fail_on_diff:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
