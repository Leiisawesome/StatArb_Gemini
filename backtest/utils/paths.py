from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """
    Return repository root directory, anchored from this file location.

    backtest/utils/paths.py -> backtest/utils -> backtest -> repo_root
    """
    return Path(__file__).resolve().parents[2]


def backtest_results_dir() -> Path:
    """Canonical backtest output root."""
    return repo_root() / "backtest" / "results"


def backtest_reports_dir() -> Path:
    """Canonical directory for analytics/report artifacts."""
    return backtest_results_dir() / "reports"


