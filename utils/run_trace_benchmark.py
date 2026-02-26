#!/usr/bin/env python3
"""One-command two-commit smoke trace benchmark.

Workflow:
1) Validate clean git working tree
2) Resolve current and previous revisions
3) Run smoke test at each revision and snapshot trace JSONL
4) Restore original git HEAD/branch
5) Print diff report using utils/trace_compare.py

Example:
  python utils/run_trace_benchmark.py
  python utils/run_trace_benchmark.py --config backtest/configs/smoke_test_mom.yaml
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List


def run_cmd(cmd: List[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout.strip()


def resolve_rev(repo_root: Path, rev: str) -> str:
    return run_cmd(["git", "rev-parse", rev], repo_root)


def short_rev(repo_root: Path, rev: str) -> str:
    return run_cmd(["git", "rev-parse", "--short", rev], repo_root)


def ensure_clean_tree(repo_root: Path) -> None:
    status = run_cmd(["git", "status", "--porcelain"], repo_root)
    if status.strip():
        raise RuntimeError(
            "Working tree is not clean. Commit/stash changes before running benchmark.\n"
            f"Pending changes:\n{status}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run two-commit smoke trace benchmark and compare output")
    parser.add_argument("--config", default="backtest/configs/smoke_test_mom.yaml", help="Smoke test config path")
    parser.add_argument("--curr-rev", default="HEAD", help="Current revision to benchmark")
    parser.add_argument("--prev-rev", default="HEAD~1", help="Previous revision to benchmark")
    parser.add_argument("--python-exe", default=sys.executable, help="Python executable to use")
    parser.add_argument("--results-dir", default="backtest/results", help="Directory for trace snapshot output")
    parser.add_argument(
        "--report-dir",
        default="backtest/results/trace-benchmarks",
        help="Directory for machine-readable benchmark JSON reports",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / args.config
    results_dir = repo_root / args.results_dir
    report_dir = repo_root / args.report_dir
    trace_live_path = results_dir / "trace-smoke_test.trace.jsonl"

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    ensure_clean_tree(repo_root)

    curr_sha = resolve_rev(repo_root, args.curr_rev)
    prev_sha = resolve_rev(repo_root, args.prev_rev)
    curr_short = short_rev(repo_root, args.curr_rev)
    prev_short = short_rev(repo_root, args.prev_rev)

    branch_name = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    original_ref = curr_sha if branch_name == "HEAD" else branch_name

    curr_snapshot = results_dir / f"trace-smoke_test-{curr_short}.jsonl"
    prev_snapshot = results_dir / f"trace-smoke_test-{prev_short}.jsonl"
    report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"trace-diff-{curr_short}-vs-{prev_short}-{report_timestamp}.json"

    print(f"[INFO] Benchmarking curr={curr_short} prev={prev_short}")

    try:
        # Current revision run
        run_cmd(["git", "checkout", curr_sha], repo_root)
        subprocess.run(
            [args.python_exe, "-m", "backtest.experiments.smoke_test", "--config", str(config_path)],
            cwd=str(repo_root),
            check=True,
        )
        if not trace_live_path.exists():
            raise FileNotFoundError(f"Expected trace file not found after curr run: {trace_live_path}")
        shutil.copy2(trace_live_path, curr_snapshot)
        print(f"[OK] Wrote {curr_snapshot}")

        # Previous revision run
        run_cmd(["git", "checkout", prev_sha], repo_root)
        subprocess.run(
            [args.python_exe, "-m", "backtest.experiments.smoke_test", "--config", str(config_path)],
            cwd=str(repo_root),
            check=True,
        )
        if not trace_live_path.exists():
            raise FileNotFoundError(f"Expected trace file not found after prev run: {trace_live_path}")
        shutil.copy2(trace_live_path, prev_snapshot)
        print(f"[OK] Wrote {prev_snapshot}")

    finally:
        run_cmd(["git", "checkout", original_ref], repo_root)
        print(f"[INFO] Restored git ref: {original_ref}")

    # Compare snapshots via existing utility
    subprocess.run(
        [
            args.python_exe,
            str(repo_root / "utils" / "trace_compare.py"),
            "--curr",
            str(curr_snapshot),
            "--prev",
            str(prev_snapshot),
            "--curr-label",
            curr_short,
            "--prev-label",
            prev_short,
            "--json-out",
            str(report_path),
        ],
        cwd=str(repo_root),
        check=True,
    )
    print(f"[OK] Wrote JSON report {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
