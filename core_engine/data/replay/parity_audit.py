#!/usr/bin/env python3
"""Parity audit utility for Polygon historical tick streamer.

Compares streamer-emitted message payload keys against the canonical
live websocket schema used by PolygonRealtimeFeedAdapter.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set

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


@dataclass
class ParityDiff:
    message_type: str
    missing_keys: List[str]
    extra_keys: List[str]

    @property
    def passed(self) -> bool:
        return not self.missing_keys and not self.extra_keys


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
    )
    streamer = PolygonHistoricalTickStreamer(config)

    row = pd.Series(
        {
            "trade_price": 100.12,
            "trade_size": 25,
            "trade_exchange": 4,
            "trade_count": 3,
            "quote_bid": 100.10,
            "quote_ask": 100.14,
            "quote_bid_size": 10,
            "quote_ask_size": 12,
            "quote_count": 2,
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
    """Compare streamer payload keys to canonical live websocket keys."""
    sample = _build_sample_messages(strict_live_parity=strict_live_parity)
    diffs: Dict[str, ParityDiff] = {}

    for message_type, expected_keys in LIVE_CANONICAL_DATA_KEYS.items():
        payload = sample.get(message_type, {})
        actual_keys = set(payload.keys())
        diffs[message_type] = ParityDiff(
            message_type=message_type,
            missing_keys=sorted(expected_keys - actual_keys),
            extra_keys=sorted(actual_keys - expected_keys),
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
