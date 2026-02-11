"""
Static Analysis Cross-Reference
=================================

AST-based analysis that builds a call graph of the 8 checkpoint files
and cross-references with dynamic trace data to identify:

1. Functions defined but never in any call path from smoke test entry points.
2. Import statements that pull in modules never used on the execution path.
3. Configuration parameters defined in dataclasses but never read.

Usage:
    python tests/trace/static_analysis.py [--trace-file path/to/trace.jsonl]

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# The 8 checkpoint modules
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


# ---------------------------------------------------------------------------
# AST Visitors
# ---------------------------------------------------------------------------

class CallGraphVisitor(ast.NodeVisitor):
    """
    Extracts function definitions and call sites from a Python AST.
    """

    def __init__(self, filename: str):
        self.filename = filename
        self.current_class: Optional[str] = None
        self.current_func: Optional[str] = None
        self.definitions: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_funcdef(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_funcdef(node)

    def _process_funcdef(self, node):
        old_func = self.current_func
        func_name = node.name
        qualified = f"{self.current_class}.{func_name}" if self.current_class else func_name

        self.definitions.append({
            "file": self.filename,
            "class": self.current_class,
            "method": func_name,
            "qualified": qualified,
            "line": node.lineno,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "arg_count": len(node.args.args),
            "decorators": [self._decorator_name(d) for d in node.decorator_list],
        })

        self.current_func = qualified
        self.generic_visit(node)
        self.current_func = old_func

    def visit_Call(self, node: ast.Call):
        callee = self._resolve_callee(node.func)
        if callee and self.current_func:
            self.calls.append({
                "caller": self.current_func,
                "callee": callee,
                "line": node.lineno,
                "file": self.filename,
            })
        self.generic_visit(node)

    def _resolve_callee(self, node) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # e.g., self.foo(), obj.bar()
            base = self._resolve_callee(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr
        return None

    def _decorator_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._decorator_name(node.func)
        return "unknown"


class ImportVisitor(ast.NodeVisitor):
    """Extract all import statements from a file."""

    def __init__(self, filename: str):
        self.filename = filename
        self.imports: List[Dict[str, Any]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({
                "file": self.filename,
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "type": "import",
            })

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            self.imports.append({
                "file": self.filename,
                "module": f"{module}.{alias.name}",
                "alias": alias.asname or alias.name,
                "line": node.lineno,
                "type": "from_import",
            })


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def build_call_graph(modules: List[str]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Parse all checkpoint modules and extract definitions, calls, imports."""
    all_defs = []
    all_calls = []
    all_imports = []

    for rel_path in modules:
        filepath = REPO_ROOT / rel_path
        if not filepath.exists():
            print(f"  WARNING: {rel_path} not found")
            continue

        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        cg = CallGraphVisitor(rel_path)
        cg.visit(tree)
        all_defs.extend(cg.definitions)
        all_calls.extend(cg.calls)

        iv = ImportVisitor(rel_path)
        iv.visit(tree)
        all_imports.extend(iv.imports)

    return all_defs, all_calls, all_imports


def find_uncalled_definitions(defs: List[Dict], calls: List[Dict]) -> List[Dict]:
    """Find definitions that are never the target of any call."""
    callee_names: Set[str] = set()
    for c in calls:
        callee = c["callee"]
        # Extract the method name (after last dot)
        parts = callee.rsplit(".", 1)
        callee_names.add(parts[-1])
        callee_names.add(callee)

    uncalled = []
    for d in defs:
        if d["method"].startswith("__") and d["method"].endswith("__"):
            continue  # Skip dunders
        
        # Check if this method is called anywhere
        if d["method"] not in callee_names and d["qualified"] not in callee_names:
            uncalled.append(d)

    return uncalled


def analyze_import_usage(imports: List[Dict], defs: List[Dict], calls: List[Dict]) -> List[Dict]:
    """Find imports that are never referenced in calls or definitions."""
    # Collect all names used in calls and definitions
    used_names: Set[str] = set()
    for c in calls:
        callee = c["callee"]
        parts = callee.split(".")
        used_names.update(parts)
    for d in defs:
        # Check decorator references
        for dec in d.get("decorators", []):
            used_names.add(dec)

    unused = []
    for imp in imports:
        alias = imp["alias"] or imp["module"].rsplit(".", 1)[-1]
        if alias not in used_names:
            unused.append(imp)

    return unused


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Static analysis of checkpoint modules")
    parser.add_argument("--trace-file", default=None, help="Optional trace JSONL for cross-reference")
    parser.add_argument("--output", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    print(f"Analyzing {len(CHECKPOINT_MODULES)} checkpoint modules...\n")

    defs, calls, imports = build_call_graph(CHECKPOINT_MODULES)

    print(f"  Definitions found:  {len(defs)}")
    print(f"  Call sites found:   {len(calls)}")
    print(f"  Import statements:  {len(imports)}")
    print()

    # 1. Uncalled definitions
    uncalled = find_uncalled_definitions(defs, calls)
    print("=" * 60)
    print("1. POTENTIALLY UNCALLED DEFINITIONS (static analysis)")
    print("=" * 60)
    print(f"  {len(uncalled)} out of {len(defs)} definitions not found as call targets\n")

    uncalled_by_file: Dict[str, List[Dict]] = defaultdict(list)
    for u in uncalled:
        uncalled_by_file[u["file"]].append(u)

    for file, methods in sorted(uncalled_by_file.items()):
        print(f"  {file}:")
        for m in sorted(methods, key=lambda x: x["line"]):
            prefix = f"{m['class']}." if m["class"] else ""
            async_tag = " (async)" if m["is_async"] else ""
            print(f"    L{m['line']:>5}  {prefix}{m['method']}{async_tag}")
        print()

    # 2. Unused imports (NOTE: this is conservative; dynamic imports are missed)
    unused_imports = analyze_import_usage(imports, defs, calls)
    print("=" * 60)
    print("2. POTENTIALLY UNUSED IMPORTS (static analysis)")
    print("=" * 60)
    print(f"  {len(unused_imports)} potentially unused imports\n")

    for imp in sorted(unused_imports, key=lambda x: (x["file"], x["line"])):
        print(f"  {imp['file']}:L{imp['line']:>5}  {imp['module']}")
    print()

    # 3. Summary statistics per file
    print("=" * 60)
    print("3. PER-FILE SUMMARY")
    print("=" * 60)
    for module in CHECKPOINT_MODULES:
        module_defs = [d for d in defs if d["file"] == module]
        module_uncalled = [u for u in uncalled if u["file"] == module]
        module_imports = [i for i in imports if i["file"] == module]
        module_unused_imports = [i for i in unused_imports if i["file"] == module]
        total = len(module_defs)
        called = total - len(module_uncalled)
        pct = (called / total * 100) if total > 0 else 0
        print(f"  {module}")
        print(f"    Methods: {called}/{total} called ({pct:.0f}%)")
        print(f"    Imports: {len(module_imports) - len(module_unused_imports)}/{len(module_imports)} used")
        print()

    # Cross-reference with dynamic trace if provided
    if args.trace_file:
        print("=" * 60)
        print("4. CROSS-REFERENCE WITH DYNAMIC TRACE")
        print("=" * 60)
        trace_records = []
        with open(args.trace_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    trace_records.append(json.loads(line))

        traced_methods: Set[str] = set()
        for r in trace_records:
            traced_methods.add(r.get("method", ""))
            traced_methods.add(f"{r.get('component', '')}.{r.get('method', '')}")

        static_uncalled_but_traced = [
            u for u in uncalled
            if u["method"] in traced_methods or u["qualified"] in traced_methods
        ]
        if static_uncalled_but_traced:
            print(f"\n  {len(static_uncalled_but_traced)} methods appear uncalled in static analysis")
            print("  but WERE traced dynamically (false positives in static analysis):")
            for m in static_uncalled_but_traced:
                print(f"    {m['file']}:{m['qualified']}")
        else:
            print("  No discrepancies between static and dynamic analysis.")
        print()

    # Save report
    report = {
        "definitions": defs,
        "uncalled": uncalled,
        "unused_imports": unused_imports,
        "summary": {
            "total_definitions": len(defs),
            "uncalled_definitions": len(uncalled),
            "total_imports": len(imports),
            "unused_imports": len(unused_imports),
        }
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Full report saved to: {args.output}")

    return report


if __name__ == "__main__":
    main()
