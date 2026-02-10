"""
Phase 0: Propagation Backscan — Main Runner
=============================================

Determines whether propagation is a statistically distinct, economically
tradable market state — or noise.

Run:
    python -m backtest.experiments.phase0_propagation_backscan.run

Decision within 48-72 hours of computation.
No ambiguity. No research theater.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure structured logging for Phase 0."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)


def generate_decision_page(results: Dict[str, Any]) -> Dict[str, str]:
    """
    Binary decision page. No commentary. No storytelling.

    Researchers love narratives — this eliminates them.
    """
    decision: Dict[str, str] = {}

    # State detection
    t01 = results.get("T01_state_detection", {})
    t02 = results.get("T02_temporal_clustering", {})
    decision["STATE_DETECTED"] = (
        "YES" if (t01.get("PASS", False) and t02.get("PASS", False)) else "NO"
    )

    # Statistical edge
    t06 = results.get("T06_significance", {})
    decision["STATISTICAL_EDGE"] = "PASS" if t06.get("PASS", False) else "FAIL"

    # Economic edge
    t03 = results.get("T03_conditional_returns", {})
    t10 = results.get("T10_trade_geometry", {})
    decision["ECONOMIC_EDGE"] = (
        "PASS"
        if (
            t03.get("q5_minus_q1_mean", 0) > 0
            and t10.get("mean_pnl_bps", 0) > 0
        )
        else "FAIL"
    )

    # Left tail
    t05 = results.get("T05_left_tail", {})
    decision["LEFT_TAIL_IMPROVED"] = "YES" if t05.get("PASS", False) else "NO"

    # Regime stability
    t07 = results.get("T07_regime_invariance", {})
    decision["REGIME_STABLE"] = "YES" if t07.get("PASS", False) else "NO"

    # Monotonicity
    t04 = results.get("T04_monotonicity", {})
    decision["MONOTONIC"] = "YES" if t04.get("PASS", False) else "NO"

    # Parameter robustness
    t08 = results.get("T08_parameter_robustness", {})
    decision["PARAM_ROBUST"] = "YES" if t08.get("PASS", False) else "NO"

    # Temporal stability
    t13 = results.get("T13_temporal_stability", {})
    decision["TEMPORALLY_STABLE"] = "YES" if t13.get("PASS", False) else "NO"

    # ── Kill criteria evaluation ──
    kill_criteria_passed = sum(
        [
            decision["STATISTICAL_EDGE"] == "PASS",
            decision["ECONOMIC_EDGE"] == "PASS",
            decision["TEMPORALLY_STABLE"] == "YES",
            decision["MONOTONIC"] == "YES",
            decision["LEFT_TAIL_IMPROVED"] == "YES",
        ]
    )

    decision["KILL_CRITERIA_PASSED"] = f"{kill_criteria_passed}/5"

    if kill_criteria_passed >= 5:
        decision["VERDICT"] = "PROCEED TO PHASE 1"
    elif kill_criteria_passed >= 3 and decision["LEFT_TAIL_IMPROVED"] == "YES":
        decision["VERDICT"] = "CONSIDER EXIT-ONLY DEPLOYMENT"
    else:
        decision["VERDICT"] = "TERMINATE — PROPAGATION NOT VALIDATED"

    return decision


async def run_phase0() -> Dict[str, Any]:
    """
    Main Phase 0 execution.

    Returns full results dict for programmatic access.
    """
    from core_engine.data.manager import ClickHouseDataManager

    from .config import END_DATE, START_DATE, UNIVERSE

    logger.info("=" * 80)
    logger.info("PHASE 0: PROPAGATION BACKSCAN")
    logger.info("Objective: Detect propagation state -- NOT optimize returns")
    logger.info(f"Universe: {UNIVERSE}")
    logger.info(f"Date Range: {START_DATE} to {END_DATE}")
    logger.info("=" * 80)
    logger.info("Step 0: Loading and validating data...")

    data_manager = ClickHouseDataManager()
    await data_manager.initialize()
    try:
        return await _run_phase0_core(data_manager)
    finally:
        await data_manager.stop()


async def _run_phase0_core(data_manager) -> Dict[str, Any]:
    """Core Phase 0 logic (data_manager lifecycle managed by caller)."""
    from core_engine.data.market_calendar import MarketCalendar
    from core_engine.data.rth_filter import filter_bars_to_rth

    from .config import (
        END_DATE,
        EQUITY_SYMBOLS,
        FORWARD_HORIZONS,
        MARKET_PROXY,
        OUTPUT_DIR,
        PRIMARY_HORIZON,
        START_DATE,
        UNIVERSE,
    )
    from .features import (
        compute_all_features,
        compute_forward_returns,
        compute_rps,
    )
    from .tests import (
        test_conditional_returns,
        test_cross_sectional_correlation,
        test_left_tail,
        test_monotonicity,
        test_parameter_robustness,
        test_regime_invariance,
        test_rps_validation,
        test_shock_behavior,
        test_significance,
        test_state_detection,
        test_temporal_clustering,
        test_temporal_stability,
        test_trade_geometry,
    )
    from .validation import add_session_boundaries, validate_data
    from .visualization import generate_decision_charts

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    calendar = MarketCalendar()
    all_data: Dict[str, pd.DataFrame] = {}
    validation_reports: Dict[str, Dict[str, Any]] = {}

    for symbol in UNIVERSE:
        logger.info(f"  Loading {symbol}...")
        raw = await data_manager.load_market_data(
            symbols=[symbol],
            start_time=START_DATE,
            end_time=END_DATE,
            interval="1min",
        )

        if raw is None or len(raw) == 0:
            logger.warning(f"  {symbol}: No data returned — skipping")
            continue

        filtered = filter_bars_to_rth(raw, symbol=symbol, calendar=calendar)

        try:
            report = validate_data(filtered, symbol)
            validation_reports[symbol] = report
            logger.info(
                f"  {symbol}: {report['total_bars']} bars, "
                f"{report['trading_days']} days, "
                f"missing={report['missing_rate']:.4f}"
            )
        except AssertionError as e:
            logger.error(f"  {symbol}: VALIDATION FAILED — {e}")
            continue

        filtered = add_session_boundaries(filtered)
        all_data[symbol] = filtered

    if len(all_data) < 3:
        logger.error("Insufficient symbols passed validation. Aborting.")
        return {"VERDICT": "ABORTED", "reason": "insufficient valid data"}

    # ═══════════════════════════════════════════
    # Step 1: Compute features per symbol
    # ═══════════════════════════════════════════
    logger.info("Step 1: Computing propagation features...")

    for symbol in list(all_data.keys()):
        logger.info(f"  Computing features for {symbol}...")
        try:
            all_data[symbol] = compute_all_features(all_data[symbol])
            all_data[symbol] = compute_forward_returns(
                all_data[symbol], FORWARD_HORIZONS
            )
            ps = all_data[symbol]["ps"]
            logger.info(
                f"  {symbol}: PS computed, "
                f"range [{ps.min():.3f}, {ps.max():.3f}], "
                f"NaN rate={ps.isna().mean():.3f}"
            )
        except Exception as e:
            logger.error(f"  {symbol}: Feature computation failed — {e}")
            del all_data[symbol]

    # ═══════════════════════════════════════════
    # Step 2: Cross-sectional features (RPS)
    # ═══════════════════════════════════════════
    logger.info("Step 2: Computing RPS (cross-sectional)...")

    if MARKET_PROXY in all_data:
        all_data = compute_rps(all_data, market_proxy=MARKET_PROXY)
    else:
        logger.warning(f"  Market proxy {MARKET_PROXY} not available — skipping RPS")

    # ═══════════════════════════════════════════
    # Step 3: Run test battery
    # ═══════════════════════════════════════════
    logger.info("Step 3: Running test battery (13 tests)...")

    # Combine equity symbols for main tests
    available_equity = [s for s in EQUITY_SYMBOLS if s in all_data]
    if not available_equity:
        logger.error("No equity symbols available for testing. Aborting.")
        return {"VERDICT": "ABORTED", "reason": "no equity symbols"}

    combined = pd.concat(
        [all_data[s] for s in available_equity], ignore_index=True
    )
    logger.info(f"  Combined dataset: {len(combined)} bars from {len(available_equity)} symbols")

    results: Dict[str, Any] = {}

    # T01: State detection
    results["T01_state_detection"] = test_state_detection(combined)
    _log_test("T01 State Detection", results["T01_state_detection"])

    # T02: Temporal clustering
    results["T02_temporal_clustering"] = test_temporal_clustering(combined)
    _log_test("T02 Temporal Clustering", results["T02_temporal_clustering"])

    # T03: Conditional returns
    results["T03_conditional_returns"] = test_conditional_returns(
        combined, PRIMARY_HORIZON
    )
    q5q1 = results["T03_conditional_returns"].get("q5_minus_q1_mean", "N/A")
    logger.info(f"  T03 Conditional Returns: Q5-Q1 = {q5q1}")

    # T04: Monotonicity
    results["T04_monotonicity"] = test_monotonicity(
        results["T03_conditional_returns"].get("table", {})
    )
    _log_test("T04 Monotonicity", results["T04_monotonicity"])

    # T05: Left tail (MAE)
    logger.info("  T05 Left Tail (computing MAE — this may take a few minutes)...")
    results["T05_left_tail"] = test_left_tail(combined, horizon=30)
    tail_pct = results["T05_left_tail"].get("tail_improvement_pct", "N/A")
    logger.info(f"  T05 Left Tail: {tail_pct}% improvement — {'PASS' if results['T05_left_tail']['PASS'] else 'FAIL'}")

    # T06: Statistical significance
    logger.info("  T06 Significance (block permutation — this may take a minute)...")
    results["T06_significance"] = test_significance(combined, PRIMARY_HORIZON)
    p_val = results["T06_significance"].get("p_value", "N/A")
    logger.info(f"  T06 Significance: p={p_val} — {'PASS' if results['T06_significance']['PASS'] else 'FAIL'}")

    # T07: Regime invariance
    results["T07_regime_invariance"] = test_regime_invariance(
        combined, PRIMARY_HORIZON
    )
    regimes = results["T07_regime_invariance"].get("regimes_passed", 0)
    logger.info(f"  T07 Regime Invariance: {regimes}/3 pass — {'PASS' if results['T07_regime_invariance']['PASS'] else 'FAIL'}")

    # T08: Parameter robustness (expensive)
    logger.info("  T08 Parameter Robustness (recomputing features — may take several minutes)...")
    # Use single representative symbol for efficiency
    rep_symbol = available_equity[0]
    results["T08_parameter_robustness"] = test_parameter_robustness(
        all_data[rep_symbol].copy()
    )
    _log_test("T08 Parameter Robustness", results["T08_parameter_robustness"])

    # T09: RPS validation
    results["T09_rps_validation"] = test_rps_validation(all_data, PRIMARY_HORIZON)
    idio = results["T09_rps_validation"].get("idio_mean_bps", "N/A")
    beta = results["T09_rps_validation"].get("beta_mean_bps", "N/A")
    logger.info(f"  T09 RPS: idio={idio} vs beta={beta}")

    # T10: Trade geometry
    results["T10_trade_geometry"] = test_trade_geometry(combined)
    n_trades = results["T10_trade_geometry"].get("n_trades", 0)
    _log_test(f"T10 Trade Geometry ({n_trades} trades)", results["T10_trade_geometry"])

    # T11: Shock behavior
    results["T11_shock_behavior"] = test_shock_behavior(combined)
    fsr = results["T11_shock_behavior"].get("false_signal_rate", "N/A")
    logger.info(f"  T11 Shock: false_signal_rate={fsr}")

    # T12: Cross-sectional correlation
    results["T12_cross_correlation"] = test_cross_sectional_correlation(all_data)
    mean_corr = results["T12_cross_correlation"].get("mean_ps_correlation", "N/A")
    logger.info(f"  T12 Cross-Sectional Corr: mean={mean_corr}")

    # T13: Temporal stability
    results["T13_temporal_stability"] = test_temporal_stability(
        combined, PRIMARY_HORIZON
    )
    _log_test("T13 Temporal Stability", results["T13_temporal_stability"])

    # ═══════════════════════════════════════════
    # Step 4: Decision page
    # ═══════════════════════════════════════════
    decision = generate_decision_page(results)

    elapsed = time.time() - start_time

    logger.info("")
    logger.info("=" * 80)
    logger.info("DECISION PAGE")
    logger.info("=" * 80)
    for key, value in decision.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 80)
    logger.info(f"VERDICT: {decision['VERDICT']}")
    logger.info(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    logger.info("=" * 80)

    # ═══════════════════════════════════════════
    # Step 5: Save results + charts
    # ═══════════════════════════════════════════
    output = {
        "metadata": {
            "run_timestamp": datetime.now().isoformat(),
            "universe": list(all_data.keys()),
            "date_range": f"{START_DATE} to {END_DATE}",
            "total_bars": sum(len(df) for df in all_data.values()),
            "runtime_seconds": elapsed,
        },
        "validation": validation_reports,
        "tests": results,
        "decision": decision,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"phase0_results_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info(f"Results saved to: {json_path}")

    # Charts
    try:
        generate_decision_charts(all_data, results, output_dir)
    except Exception as e:
        logger.warning(f"Chart generation failed (non-critical): {e}")

    return output


def _log_test(name: str, result: Dict[str, Any]) -> None:
    """Log test result concisely."""
    passed = result.get("PASS", False)
    logger.info(f"  {name}: {'PASS' if passed else 'FAIL'}")


def main() -> None:
    """Entry point for command-line execution."""
    _setup_logging()

    logger.info("Phase 0: Propagation Backscan")
    logger.info("Hypothesis: Markets enter a propagation state with superior trade geometry.")
    logger.info("Objective: Detect the state — NOT optimize returns.")
    logger.info("")

    result = asyncio.run(run_phase0())

    verdict = result.get("decision", result).get("VERDICT", "UNKNOWN")

    if "TERMINATE" in verdict:
        logger.info("Propagation hypothesis NOT validated. Project terminated.")
        sys.exit(1)
    elif "EXIT-ONLY" in verdict:
        logger.info("Partial validation. Proceed with exit-only deployment (Phase 3).")
        sys.exit(0)
    elif "PROCEED" in verdict:
        logger.info("Full validation. Proceed to Phase 1 (Feature Pipeline).")
        sys.exit(0)
    else:
        logger.warning(f"Unexpected verdict: {verdict}")
        sys.exit(2)


if __name__ == "__main__":
    main()
