"""
Dead Code Audit via Coverage Analysis
=======================================

Runs the BT MOM smoke test under Python's coverage tracer and reports
which methods in the 8 checkpoint modules are reachable vs. unreachable.

Output:
- A structured report of {file, class, method, called, line} for each
  public method in the checkpoint modules.
- The report is printed to stdout and optionally saved as JSON.

This test uses `sys.settrace` / `threading.settrace` for lightweight
function-level call tracking (not full branch coverage). It does NOT
require `coverage.py` as a dependency.

Requires: ClickHouse with TSLA 1-min data for 2024-12-18 to 2024-12-20.

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import ast
import asyncio
import json
import socket
import sys
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# The 8 checkpoint modules to audit
# ---------------------------------------------------------------------------
CHECKPOINT_MODULES = [
    "backtest/engine/institutional_backtest_engine.py",
    "core_engine/processing/pipeline_orchestrator.py",
    "core_engine/trading/strategies/manager.py",
    "core_engine/system/central_risk_manager.py",
    "core_engine/system/order_management_system.py",
    "core_engine/trading/execution/fill_processor.py",
    "core_engine/trading/position_book.py",
    "core_engine/system/realtime_pnl_tracker.py",
]


def _clickhouse_available(host: str = "localhost", port: int = 8123) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# AST-based method extraction
# ---------------------------------------------------------------------------

def _extract_methods(filepath: Path) -> List[Dict[str, Any]]:
    """Extract all class methods and module-level functions from a Python file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        "file": str(filepath.relative_to(REPO_ROOT)),
                        "class": class_name,
                        "method": item.name,
                        "line": item.lineno,
                        "is_private": item.name.startswith("_") and not item.name.startswith("__"),
                        "is_dunder": item.name.startswith("__") and item.name.endswith("__"),
                    })

    # Module-level functions (only direct children of the module)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append({
                "file": str(filepath.relative_to(REPO_ROOT)),
                "class": None,
                "method": node.name,
                "line": node.lineno,
                "is_private": node.name.startswith("_"),
                "is_dunder": node.name.startswith("__") and node.name.endswith("__"),
            })

    return methods


# ---------------------------------------------------------------------------
# Function call tracer
# ---------------------------------------------------------------------------

class FunctionCallTracer:
    """
    Lightweight call tracer using sys.settrace.
    Tracks which (filename, function_name) pairs are called.
    """

    def __init__(self, target_files: Set[str]):
        self._target_files = target_files
        self._called: Set[Tuple[str, str]] = set()
        self._lock = threading.Lock()

    def _trace_calls(self, frame, event, arg):
        if event == "call":
            filename = frame.f_code.co_filename
            # Normalize path separators
            normalized = filename.replace("\\", "/")
            for target in self._target_files:
                if target in normalized:
                    func_name = frame.f_code.co_name
                    with self._lock:
                        self._called.add((target, func_name))
                    break
        return self._trace_calls

    def start(self):
        sys.settrace(self._trace_calls)
        threading.settrace(self._trace_calls)

    def stop(self):
        sys.settrace(None)
        threading.settrace(None)  # type: ignore[arg-type]

    @property
    def called_functions(self) -> Set[Tuple[str, str]]:
        return self._called.copy()


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.requires_data
@pytest.mark.slow
def test_dead_code_audit(tmp_path):
    """
    Run BT MOM smoke test with function call tracing and report uncalled methods.
    """
    if not _clickhouse_available():
        pytest.skip("ClickHouse not reachable on localhost:8123")

    # Build absolute paths for target modules
    target_files: Set[str] = set()
    for rel_path in CHECKPOINT_MODULES:
        abs_path = str((REPO_ROOT / rel_path).resolve()).replace("\\", "/")
        target_files.add(rel_path.replace("\\", "/"))

    # Extract all methods via AST
    all_methods: List[Dict[str, Any]] = []
    for rel_path in CHECKPOINT_MODULES:
        filepath = REPO_ROOT / rel_path
        if filepath.exists():
            all_methods.extend(_extract_methods(filepath))

    assert len(all_methods) > 0, "No methods extracted from checkpoint modules"

    # Set up call tracer
    tracer = FunctionCallTracer(target_files)

    # Load config and run smoke test
    from core_engine.utils.pipeline_trace import PipelineTracer
    PipelineTracer.reset_instance()

    from backtest.utils.config_loader import load_config
    config_path = str(REPO_ROOT / "backtest" / "configs" / "smoke_test_mom.yaml")
    config = load_config(config_path)
    config["enable_pipeline_trace"] = True

    from backtest.experiments.smoke_test import SmokeTest
    experiment = SmokeTest(config)

    # Start tracing, run test, stop tracing
    tracer.start()
    try:
        result = asyncio.run(experiment.run())
    finally:
        tracer.stop()

    assert result.success, f"Smoke test failed: {result.error_message}"

    # Cross-reference called functions with extracted methods
    called = tracer.called_functions
    called_method_names_by_file: Dict[str, Set[str]] = defaultdict(set)
    for file_fragment, func_name in called:
        called_method_names_by_file[file_fragment].add(func_name)

    # Build report
    report = []
    for method in all_methods:
        file_key = method["file"].replace("\\", "/")
        func_name = method["method"]

        # Check if this function was called
        was_called = False
        for fragment, names in called_method_names_by_file.items():
            if fragment in file_key or file_key in fragment:
                if func_name in names:
                    was_called = True
                    break

        method["called"] = was_called
        report.append(method)

    # Separate called vs uncalled
    called_methods = [m for m in report if m["called"]]
    uncalled_methods = [m for m in report if not m["called"]]

    # Filter out dunders and private methods for the primary report
    uncalled_public = [m for m in uncalled_methods if not m["is_dunder"]]
    uncalled_non_private = [m for m in uncalled_public if not m["is_private"]]

    # Print report
    print(f"\n{'='*80}")
    print(f"DEAD CODE AUDIT REPORT (BT MOM Smoke Test)")
    print(f"{'='*80}")
    print(f"Total methods extracted:   {len(report)}")
    print(f"Methods called:            {len(called_methods)}")
    print(f"Methods NOT called:        {len(uncalled_methods)}")
    print(f"  - Public uncalled:       {len(uncalled_non_private)}")
    print(f"  - Private uncalled:      {len(uncalled_public) - len(uncalled_non_private)}")
    print(f"Coverage rate:             {len(called_methods)/len(report)*100:.1f}%")
    print()

    # Print uncalled public methods by file
    uncalled_by_file: Dict[str, List[Dict]] = defaultdict(list)
    for m in uncalled_non_private:
        uncalled_by_file[m["file"]].append(m)

    if uncalled_by_file:
        print("UNCALLED PUBLIC METHODS:")
        print("-" * 80)
        for file, methods_list in sorted(uncalled_by_file.items()):
            print(f"\n  {file}:")
            for m in sorted(methods_list, key=lambda x: x["line"]):
                class_prefix = f"{m['class']}." if m["class"] else ""
                print(f"    L{m['line']:>5}  {class_prefix}{m['method']}")
    else:
        print("All public methods were called!")

    print(f"\n{'='*80}")

    # Save JSON report
    report_path = tmp_path / "dead_code_audit.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Full report saved to: {report_path}")

    # The test passes regardless -- this is an audit, not a gate.
    # Uncomment below to fail on high dead-code ratio:
    # dead_ratio = len(uncalled_non_private) / max(len(report), 1)
    # assert dead_ratio < 0.50, f"Dead code ratio {dead_ratio:.1%} exceeds 50%"
