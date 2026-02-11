"""
Redundancy Detection via Trace Analysis
=========================================

Analysis script (not a test) that examines pipeline trace JSONL output for:

1. **Duplicate Computation**: Same input_hash producing same output_hash at
   the same checkpoint across different bars (redundant recalculation).
2. **Unused Output Detection**: Fields computed at CP_N but never consumed
   by CP_N+1 (computed-but-not-read redundancy).
3. **High-Frequency Checkpoints**: Identify checkpoints that fire excessively
   relative to the number of actual trading decisions.

Usage:
    python tests/trace/analyze_redundancy.py --trace-file backtest/results/trace-smoke_test.trace.jsonl

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_trace(path: str) -> List[Dict[str, Any]]:
    """Load trace records from JSONL file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def analyze_duplicate_computation(records: List[Dict]) -> Dict[str, Any]:
    """
    Find duplicate computations: same checkpoint + same input_hash = redundant.
    """
    # Group by (checkpoint, input_hash)
    seen: Dict[str, List[Dict]] = defaultdict(list)
    for r in records:
        key = f"{r['checkpoint']}:{r['input_hash']}"
        seen[key].append(r)

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    
    report = {
        "total_records": len(records),
        "unique_computations": len(seen),
        "duplicate_groups": len(duplicates),
        "duplicate_records": sum(len(v) - 1 for v in duplicates.values()),
        "top_duplicates": [],
    }

    # Top duplicates by count
    sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
    for key, group in sorted_dups[:10]:
        cp, ihash = key.split(":", 1)
        report["top_duplicates"].append({
            "checkpoint": cp,
            "input_hash": ihash,
            "count": len(group),
            "symbols": list({r["symbol"] for r in group}),
            "components": list({r["component"] for r in group}),
        })

    return report


def analyze_checkpoint_frequency(records: List[Dict]) -> Dict[str, Any]:
    """
    Analyze checkpoint firing frequency to find disproportionate activity.
    """
    counts = Counter(r["checkpoint"] for r in records)
    total = len(records)

    freq = {}
    for cp in sorted(counts.keys()):
        count = counts[cp]
        freq[cp] = {
            "count": count,
            "pct_of_total": round(count / total * 100, 1),
        }

    # Identify checkpoints with disproportionate firing
    # CP7 (PnL) fires on every price tick, so it should be highest
    # CP0 (market data) fires per bar per symbol
    # CP2 (signals) should be much lower than CP0

    return {
        "total_records": total,
        "by_checkpoint": freq,
    }


def analyze_output_field_coverage(records: List[Dict]) -> Dict[str, Any]:
    """
    Track which output_data fields are produced at each checkpoint.
    This helps identify fields that are computed but potentially unused downstream.
    """
    from core_engine.utils.pipeline_trace import ALL_CHECKPOINTS

    output_fields_by_cp: Dict[str, Set[str]] = defaultdict(set)
    input_fields_by_cp: Dict[str, Set[str]] = defaultdict(set)

    for r in records:
        cp = r["checkpoint"]
        output_data = r.get("output_data", {})
        input_data = r.get("input_data", {})

        if isinstance(output_data, dict):
            output_fields_by_cp[cp].update(output_data.keys())
        if isinstance(input_data, dict):
            input_fields_by_cp[cp].update(input_data.keys())

    # Check which output fields from CP_N appear as input fields at CP_N+1
    consumed = {}
    for i in range(len(ALL_CHECKPOINTS) - 1):
        cp_out = ALL_CHECKPOINTS[i]
        cp_in = ALL_CHECKPOINTS[i + 1]
        produced = output_fields_by_cp.get(cp_out, set())
        needed = input_fields_by_cp.get(cp_in, set())
        overlap = produced & needed
        unused = produced - needed

        consumed[f"{cp_out}->{cp_in}"] = {
            "produced": sorted(produced),
            "consumed_by_next": sorted(overlap),
            "potentially_unused": sorted(unused),
        }

    return consumed


def main():
    parser = argparse.ArgumentParser(description="Analyze pipeline trace for redundancy")
    parser.add_argument("--trace-file", required=True, help="Path to trace JSONL file")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    records = load_trace(args.trace_file)
    print(f"Loaded {len(records)} trace records from {args.trace_file}\n")

    # Analysis 1: Duplicate computation
    dup_report = analyze_duplicate_computation(records)
    print("=" * 60)
    print("1. DUPLICATE COMPUTATION ANALYSIS")
    print("=" * 60)
    print(f"  Total records:          {dup_report['total_records']}")
    print(f"  Unique computations:    {dup_report['unique_computations']}")
    print(f"  Duplicate groups:       {dup_report['duplicate_groups']}")
    print(f"  Redundant records:      {dup_report['duplicate_records']}")
    if dup_report["top_duplicates"]:
        print("\n  Top duplicate groups:")
        for d in dup_report["top_duplicates"][:5]:
            print(f"    {d['checkpoint']} hash={d['input_hash'][:8]}... "
                  f"count={d['count']} symbols={d['symbols']}")
    print()

    # Analysis 2: Checkpoint frequency
    freq_report = analyze_checkpoint_frequency(records)
    print("=" * 60)
    print("2. CHECKPOINT FREQUENCY ANALYSIS")
    print("=" * 60)
    for cp, info in freq_report["by_checkpoint"].items():
        bar = "#" * max(1, info["count"] // 10)
        print(f"  {cp}: {info['count']:>6} ({info['pct_of_total']:>5.1f}%)  {bar}")
    print()

    # Analysis 3: Output field coverage
    field_report = analyze_output_field_coverage(records)
    print("=" * 60)
    print("3. OUTPUT FIELD COVERAGE (unused outputs between stages)")
    print("=" * 60)
    for transition, info in field_report.items():
        unused = info["potentially_unused"]
        if unused:
            print(f"\n  {transition}:")
            print(f"    Produced:         {info['produced']}")
            print(f"    Consumed by next: {info['consumed_by_next']}")
            print(f"    Potentially unused: {unused}")
    print()

    # Save full report
    full_report = {
        "duplicate_computation": dup_report,
        "checkpoint_frequency": freq_report,
        "output_field_coverage": field_report,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(full_report, f, indent=2, default=list)
        print(f"Full report saved to: {args.output}")

    return full_report


if __name__ == "__main__":
    main()
