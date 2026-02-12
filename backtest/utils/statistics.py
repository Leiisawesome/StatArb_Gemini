"""
Statistical Test Utilities for Backtest Experiments
====================================================

Reusable statistical functions extracted from experiment code.
Used by smoke_test, walk_forward_analysis, and other experiments
that need hypothesis testing or OOS validation.

Author: StatArb_Gemini Core Engine
"""

from typing import Any, Dict, List

import numpy as np


def extract_equity_returns(engine_results: Dict[str, Any]) -> List[float]:
    """
    Extract per-bar returns from engine result position history.

    Args:
        engine_results: Raw engine results dict containing summary.position_history

    Returns:
        List of per-bar fractional returns
    """
    summary = engine_results.get("summary") if engine_results else {}
    position_history = summary.get("position_history", []) if summary else []
    if not position_history:
        return []
    equities = [snap.get("equity") for snap in position_history if snap.get("equity") is not None]
    returns = []
    for i in range(1, len(equities)):
        prev = equities[i - 1]
        curr = equities[i]
        if prev and prev != 0:
            returns.append((curr - prev) / prev)
    return returns


def paired_t_test(a: List[float], b: List[float]) -> Dict[str, Any]:
    """
    Paired t-test using proper t-distribution (not normal approximation).

    Uses scipy's t-distribution with (n-1) degrees of freedom for correct
    p-values with small samples (n < 30).

    Args:
        a: First return series
        b: Second return series

    Returns:
        Dict with p_value, t_stat, n
    """
    n = min(len(a), len(b))
    if n < 2:
        return {"p_value": None, "t_stat": None, "n": n}
    diffs = np.array(a[:n]) - np.array(b[:n])
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1))
    if std_diff == 0:
        return {"p_value": 1.0, "t_stat": 0.0, "n": n}
    t_stat = mean_diff / (std_diff / np.sqrt(n))
    try:
        from scipy import stats as sp_stats
        p_value = float(2.0 * sp_stats.t.sf(abs(t_stat), df=n - 1))
    except ImportError:
        # Fallback: normal approximation if scipy unavailable
        p_value = float(2.0 * (1.0 - 0.5 * (1.0 + np.math.erf(abs(t_stat) / np.sqrt(2)))))
    return {"p_value": p_value, "t_stat": float(t_stat), "n": n}


def compute_hypothesis_tests(isolated_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute paired t-tests for hybrid vs MOM/MR strategies.

    Args:
        isolated_runs: List of per-strategy run results with engine_results

    Returns:
        Dict with test results keyed by comparison name
    """
    returns_by_name = {}
    for run in isolated_runs:
        name = str(run.get("strategy_name", "")).lower()
        returns_by_name[name] = extract_equity_returns(run.get("engine_results", {}) or {})

    hybrid = next((v for k, v in returns_by_name.items() if "hybrid" in k), None)
    mom = next((v for k, v in returns_by_name.items() if "mom" in k), None)
    mr = next((v for k, v in returns_by_name.items() if "mr" in k), None)

    results = {}
    if hybrid and mom:
        results["hybrid_vs_mom"] = paired_t_test(hybrid, mom)
    if hybrid and mr:
        results["hybrid_vs_mr"] = paired_t_test(hybrid, mr)
    return results


def compute_oos_validation(isolated_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simple train/test split validation from equity returns.

    Splits each strategy's return series in half and compares
    train-period vs test-period statistics.

    Args:
        isolated_runs: List of per-strategy run results with engine_results

    Returns:
        Dict keyed by strategy name with train/test statistics
    """
    oos = {}
    for run in isolated_runs:
        name = str(run.get("strategy_name", "")).lower()
        returns = extract_equity_returns(run.get("engine_results", {}) or {})
        if len(returns) < 4:
            continue
        split = len(returns) // 2
        train = returns[:split]
        test = returns[split:]
        oos[name] = {
            "train_mean_return": float(np.mean(train)) if train else 0.0,
            "test_mean_return": float(np.mean(test)) if test else 0.0,
            "train_std_return": float(np.std(train)) if train else 0.0,
            "test_std_return": float(np.std(test)) if test else 0.0,
            "n_train": len(train),
            "n_test": len(test),
        }
    return oos
