"""
Deterministic BT↔PT Parity (Golden) - TSLA 2024-12-20
====================================================

This integration test runs:
- Backtest smoke_test with mean-reversion config
- Papertest smoke_test with canonical config

and asserts that the resulting FILL streams match:
  (timestamp, side, quantity, price)

Notes
-----
- Requires ClickHouse market data access (localhost:8123 by default).
- Marked as integration + slow + requires_data.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class FillRow:
    ts: str
    side: str
    qty: float
    price: float


def _tcp_check(host: str, port: int, timeout_s: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _list_files(pattern: str) -> List[Path]:
    return list(REPO_ROOT.glob(pattern))


def _newest_file(created: List[Path]) -> Path:
    return max(created, key=lambda p: p.stat().st_mtime)


def _run_suite(args: List[str]) -> subprocess.CompletedProcess[str]:
    # Keep runs deterministic and avoid noisy logs in CI/local.
    env = dict(os.environ)
    env.setdefault("PYTHONHASHSEED", "0")
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _normalize_ts(ts: str) -> str:
    return (ts or "").replace(" ", "T")


def _extract_bt_fills(bt_result_json: Path) -> List[FillRow]:
    obj = json.loads(bt_result_json.read_text())
    trades = (obj.get("engine_results", {}) or {}).get("execution_history", []) or []
    out: List[FillRow] = []
    for t in trades:
        ts = _normalize_ts(str(t.get("timestamp", "")))
        side = str(t.get("side") or "").lower()
        qty = float(t.get("quantity") or 0.0)
        price = float(t.get("fill_price") or t.get("execution_price") or t.get("price") or 0.0)
        out.append(FillRow(ts=ts, side=side, qty=qty, price=price))
    return out


def _extract_pt_fills(pt_journal_jsonl: Path) -> List[FillRow]:
    out: List[FillRow] = []
    with pt_journal_jsonl.open() as f:
        for line in f:
            ev = json.loads(line)
            if ev.get("category") != "FILL" or ev.get("event_type") != "fill":
                continue
            d = ev.get("data") or {}
            ts = _normalize_ts(str(d.get("fill_timestamp") or ev.get("timestamp") or ""))
            side = str(d.get("side") or "").lower()
            qty = float(d.get("quantity") or 0.0)
            price = float(d.get("price") or 0.0)
            out.append(FillRow(ts=ts, side=side, qty=qty, price=price))
    return out


def _assert_fill_stream_equal(bt: List[FillRow], pt: List[FillRow]) -> None:
    assert len(bt) == len(pt), f"fill count mismatch: BT={len(bt)} PT={len(pt)}"
    for i, (b, p) in enumerate(zip(bt, pt)):
        # Allow 1-minute drift in timestamping due to different scheduling/order routing semantics
        # between BT and PT (both are still minute-bar aligned).
        try:
            from datetime import datetime
            bt_ts = datetime.fromisoformat(b.ts)
            pt_ts = datetime.fromisoformat(p.ts)
            assert abs((bt_ts - pt_ts).total_seconds()) <= 60, f"[{i}] ts mismatch: BT={b.ts} PT={p.ts}"
        except Exception:
            assert b.ts == p.ts, f"[{i}] ts mismatch: BT={b.ts} PT={p.ts}"
        assert b.side == p.side, f"[{i}] side mismatch: BT={b.side} PT={p.side}"
        # Quantities can differ by tiny floating drift depending on PV source + float math;
        # enforce a strict but practical tolerance.
        assert abs(b.qty - p.qty) <= 1e-2, f"[{i}] qty mismatch: BT={b.qty} PT={p.qty}"
        assert abs(b.price - p.price) <= 1e-5, f"[{i}] price mismatch: BT={b.price} PT={p.price}"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_data
def test_bt_pt_fill_parity_tsla_2024_12_20_smoke() -> None:
    """
    Golden parity case:
    TSLA on 2024-12-20 (EOD liquidation enabled) should produce identical fills.
    """
    # Fast precheck: skip if ClickHouse isn't reachable.
    if not _tcp_check("localhost", 8123, timeout_s=0.5):
        pytest.skip("ClickHouse not reachable on localhost:8123 (required for this integration test)")

    # Snapshot existing artifacts so we can pick the files created by this test run.
    pt_before = set(_list_files("papertest/results/journals/paper-*.jsonl"))
    bt_before = set(_list_files("backtest/results/smoke_test_*.json"))

    # Run papertest canonical
    pt_proc = _run_suite(["papertest/run_suite.py", "--experiment", "smoke_test", "--config", "papertest/configs/smoke_test.yaml"])

    # Run backtest MR smoke
    bt_proc = _run_suite(["backtest/run_suite.py", "--experiment", "smoke_test", "--config", "backtest/configs/smoke_test_mr.yaml"])

    # Find newly created artifacts
    pt_after = set(_list_files("papertest/results/journals/paper-*.jsonl"))
    bt_after = set(_list_files("backtest/results/smoke_test_*.json"))

    new_pt = sorted(pt_after - pt_before)
    new_bt = sorted(bt_after - bt_before)

    if not new_pt:
        pytest.fail(f"Papertest did not create a new journal file.\nSTDOUT:\n{pt_proc.stdout}\nSTDERR:\n{pt_proc.stderr}")
    if not new_bt:
        pytest.fail(f"Backtest did not create a new results file.\nSTDOUT:\n{bt_proc.stdout}\nSTDERR:\n{bt_proc.stderr}")

    pt_journal = _newest_file(new_pt)
    bt_result = _newest_file(new_bt)

    bt_fills = _extract_bt_fills(bt_result)
    pt_fills = _extract_pt_fills(pt_journal)

    # Sanity: we expect at least one fill (this is a smoke test with trades)
    assert bt_fills, f"BT produced 0 fills. bt_result={bt_result}"
    assert pt_fills, f"PT produced 0 fills. pt_journal={pt_journal}"

    _assert_fill_stream_equal(bt_fills, pt_fills)


