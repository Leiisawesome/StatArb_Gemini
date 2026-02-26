#!/usr/bin/env python3
"""Compare two pipeline trace snapshot files.

Usage:
  python utils/trace_compare.py --curr backtest/results/trace-smoke_test-xxxxxxx.jsonl --prev backtest/results/trace-smoke_test-yyyyyyy.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cp_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        cp = str(row.get("checkpoint", "UNKNOWN"))
        out[cp] = out.get(cp, 0) + 1
    return out


def cp3_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    cp3 = [row for row in rows if row.get("checkpoint") == "CP3"]
    auth = sum(1 for row in cp3 if (row.get("output_data", {}) or {}).get("authorized") is True)
    rej = [row for row in cp3 if (row.get("output_data", {}) or {}).get("authorized") is not True]

    reasons: Dict[str, int] = {}
    ratios: List[float] = []
    edges: List[float] = []
    costs: List[float] = []

    for row in cp3:
        waterfall = ((row.get("metadata", {}) or {}).get("waterfall", []) or [])
        g6 = [gate for gate in waterfall if gate.get("gate") == "G6_cost"]
        if not g6:
            continue

        data = g6[-1].get("data", {}) or {}
        for sink, key in ((ratios, "cost_edge_ratio"), (edges, "expected_edge_bps"), (costs, "cost_bps")):
            value = data.get(key)
            if isinstance(value, (int, float)):
                sink.append(float(value))

    for row in rej:
        reason = (row.get("output_data", {}) or {}).get("rejection_reason")
        reasons[str(reason)] = reasons.get(str(reason), 0) + 1

    return {
        "cp3_count": len(cp3),
        "auth": auth,
        "rej": len(rej),
        "reasons": sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5],
        "g6_ratio_avg": (sum(ratios) / len(ratios) if ratios else None),
        "g6_edge_avg": (sum(edges) / len(edges) if edges else None),
        "g6_cost_avg": (sum(costs) / len(costs) if costs else None),
    }


def cp2_l1_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    cp2 = [row for row in rows if row.get("checkpoint") == "CP2"]

    l1_values: List[float] = []
    modes: Dict[str, int] = {}
    hits = {"entry_diag": 0, "entry_mode": 0, "expected_return_bps": 0}

    for row in cp2:
        out = row.get("output_data", {}) or {}

        entry_diag = out.get("entry_diag")
        if isinstance(entry_diag, dict) and entry_diag:
            hits["entry_diag"] += 1
            score = (entry_diag.get("L1_alignment") or {}).get("score")
            if isinstance(score, (int, float)):
                l1_values.append(float(score))

        entry_mode = out.get("entry_mode")
        if isinstance(entry_mode, str) and entry_mode:
            hits["entry_mode"] += 1
            modes[entry_mode] = modes.get(entry_mode, 0) + 1

        expected_return_bps = out.get("expected_return_bps")
        if isinstance(expected_return_bps, (int, float)):
            hits["expected_return_bps"] += 1

    def stats(values: List[float]) -> Dict[str, Any]:
        if not values:
            return {"count": 0, "avg": None, "p50": None, "min": None, "max": None}
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "p50": st.median(values),
            "min": min(values),
            "max": max(values),
        }

    return {
        "cp2_count": len(cp2),
        "hits": hits,
        "modes": modes,
        "l1": stats(l1_values),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "None"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two trace JSONL snapshots")
    parser.add_argument("--curr", required=True, type=Path, help="Current snapshot path")
    parser.add_argument("--prev", required=True, type=Path, help="Previous snapshot path")
    parser.add_argument("--curr-label", default="curr", help="Label for current snapshot")
    parser.add_argument("--prev-label", default="prev", help="Label for previous snapshot")
    args = parser.parse_args()

    curr_rows = load_jsonl(args.curr)
    prev_rows = load_jsonl(args.prev)

    curr_cp = cp_counts(curr_rows)
    prev_cp = cp_counts(prev_rows)

    curr_cp3 = cp3_stats(curr_rows)
    prev_cp3 = cp3_stats(prev_rows)

    curr_l1 = cp2_l1_stats(curr_rows)
    prev_l1 = cp2_l1_stats(prev_rows)

    print("TRACE_DIFF", args.curr_label, "vs", args.prev_label)
    print("CP_COUNTS_CURR", curr_cp)
    print("CP_COUNTS_PREV", prev_cp)
    print("CP3_CURR", curr_cp3)
    print("CP3_PREV", prev_cp3)
    print("CP2_L1_CURR", curr_l1)
    print("CP2_L1_PREV", prev_l1)

    print("DELTA_CP3_COUNT", curr_cp3["cp3_count"] - prev_cp3["cp3_count"])
    print("DELTA_AUTH", curr_cp3["auth"] - prev_cp3["auth"])
    print("DELTA_REJ", curr_cp3["rej"] - prev_cp3["rej"])

    for key in ("g6_ratio_avg", "g6_edge_avg", "g6_cost_avg"):
        a = curr_cp3[key]
        b = prev_cp3[key]
        d = None if (a is None or b is None) else (a - b)
        print("DELTA_" + key, "curr", fmt(a), "prev", fmt(b), "delta", fmt(d))

    for key in ("avg", "p50", "min", "max"):
        a = curr_l1["l1"][key]
        b = prev_l1["l1"][key]
        d = None if (a is None or b is None) else (a - b)
        print("DELTA_L1_" + key, "curr", fmt(a), "prev", fmt(b), "delta", fmt(d))

    hit_delta = {
        key: curr_l1["hits"].get(key, 0) - prev_l1["hits"].get(key, 0)
        for key in {**curr_l1["hits"], **prev_l1["hits"]}
    }
    print("DELTA_HITS", hit_delta)
    print("L1_MODES_CURR", curr_l1["modes"])
    print("L1_MODES_PREV", prev_l1["modes"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
