"""
Phase 0: Decision Dashboard Visualization
===========================================

6 charts that let a PM understand the edge in under 3 minutes.

Chart 1: PS Distribution (state detection)
Chart 2: Quintile Return Staircase (monotonicity)
Chart 3: MAE vs PS Percentile (THE chart that exposes fake alpha)
Chart 4: Regime Invariance (cross-regime stability)
Chart 5: Parameter Robustness (graceful degradation)
Chart 6: Decision Summary (binary verdict)
"""

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def generate_decision_charts(
    all_data: Dict[str, pd.DataFrame],
    results: Dict[str, Any],
    output_dir: Path,
) -> None:
    """Generate the 6-chart decision dashboard."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.gridspec as gridspec
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available — skipping chart generation")
        return

    fig = plt.figure(figsize=(20, 14))
    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3)

    # Combine equity symbols
    equity = [s for s in all_data if s not in ["SPY", "QQQ"]]
    if not equity:
        logger.warning("No equity symbols for charts")
        return
    combined = pd.concat([all_data[s] for s in equity], ignore_index=True)

    # ── Chart 1: PS Distribution ──
    ax1 = fig.add_subplot(gs[0, 0])
    ps = combined["ps"].dropna()
    if len(ps) > 0:
        ax1.hist(ps, bins=80, density=True, alpha=0.7, color="steelblue", edgecolor="none")
        ax1.axvline(ps.quantile(0.8), color="red", linestyle="--", label="80th pctile")
        ax1.axvline(ps.median(), color="orange", linestyle=":", label="median")
        ax1.legend(fontsize=8)
    ax1.set_title("PS Distribution (State Detection)", fontweight="bold", fontsize=10)
    ax1.set_xlabel("Propagation Score")
    ax1.set_ylabel("Density")

    # ── Chart 2: Quintile Staircase ──
    ax2 = fig.add_subplot(gs[0, 1])
    table = results.get("T03_conditional_returns", {}).get("table", {})
    if table:
        means = [table.get(f"Q{q}", {}).get("mean_bps", 0) for q in range(1, 6)]
        colors = ["#d32f2f" if m < 0 else "#388e3c" for m in means]
        ax2.bar(range(1, 6), means, color=colors, edgecolor="black", linewidth=0.5)
        ax2.axhline(0, color="black", linewidth=0.5)
        ax2.set_xticks(range(1, 6))
        ax2.set_xticklabels(["Q1\n(weak)", "Q2", "Q3", "Q4", "Q5\n(strong)"])
    ax2.set_xlabel("PS Quintile")
    ax2.set_ylabel("Forward Return (bps, net)")
    ax2.set_title("Quintile Monotonicity", fontweight="bold", fontsize=10)

    # ── Chart 3: MAE vs PS (THE chart) ──
    ax3 = fig.add_subplot(gs[0, 2])
    mae_data = results.get("T05_left_tail", {}).get("mae_by_quintile", {})
    if mae_data:
        p95_values = [mae_data.get(f"Q{q}", {}).get("p95_mae_bps", 0) for q in range(1, 6)]
        mean_values = [mae_data.get(f"Q{q}", {}).get("mean_mae_bps", 0) for q in range(1, 6)]
        ax3.plot(range(1, 6), p95_values, "o-", color="#d32f2f", linewidth=2, markersize=8, label="95th pctile MAE")
        ax3.plot(range(1, 6), mean_values, "s--", color="#1565c0", linewidth=1.5, markersize=6, label="Mean MAE")
        ax3.legend(fontsize=8)
        ax3.set_xticks(range(1, 6))
    ax3.set_xlabel("PS Quintile")
    ax3.set_ylabel("MAE (bps)")
    ax3.set_title("Left-Tail Improvement", fontweight="bold", fontsize=10)

    # ── Chart 4: Regime Invariance ──
    ax4 = fig.add_subplot(gs[1, 0])
    regime_data = results.get("T07_regime_invariance", {}).get("by_regime", {})
    regime_colors = {"low_vol": "#1565c0", "mid_vol": "#f9a825", "high_vol": "#d32f2f"}
    for regime in ["low_vol", "mid_vol", "high_vol"]:
        rd = regime_data.get(regime, {})
        if "quintile_means" in rd:
            ax4.plot(
                range(1, 6),
                rd["quintile_means"],
                "o-",
                label=regime.replace("_", " ").title(),
                color=regime_colors.get(regime, "gray"),
                linewidth=1.5,
            )
    ax4.axhline(0, color="black", linewidth=0.5)
    ax4.set_xlabel("PS Quintile")
    ax4.set_ylabel("Forward Return (bps)")
    ax4.set_title("Regime Invariance", fontweight="bold", fontsize=10)
    ax4.legend(fontsize=8)

    # ── Chart 5: Parameter Robustness ──
    ax5 = fig.add_subplot(gs[1, 1])
    param_results = results.get("T08_parameter_robustness", {})
    ws_keys = sorted([k for k in param_results if k.startswith("window_set_")])
    if ws_keys:
        q5_q1s = [param_results[k].get("q5_minus_q1", 0) for k in ws_keys]
        labels = [str(param_results[k].get("windows", "?")) for k in ws_keys]
        colors = ["#388e3c" if v > 0 else "#d32f2f" for v in q5_q1s]
        ax5.barh(range(len(q5_q1s)), q5_q1s, color=colors, edgecolor="black", linewidth=0.5)
        ax5.set_yticks(range(len(labels)))
        ax5.set_yticklabels(labels, fontsize=8)
        ax5.axvline(0, color="black", linewidth=0.5)
    ax5.set_xlabel("Q5-Q1 Spread (bps)")
    ax5.set_title("Parameter Robustness", fontweight="bold", fontsize=10)

    # ── Chart 6: Decision Summary ──
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")

    from .run import generate_decision_page

    decision = generate_decision_page(results)
    lines = ["DECISION PAGE", "\u2500" * 30, ""]
    for k, v in decision.items():
        if v in ("YES", "PASS"):
            icon = "\u25cf"  # filled circle
        elif v in ("NO", "FAIL"):
            icon = "\u25cb"  # hollow circle
        else:
            icon = " "
        lines.append(f"{icon} {k}: {v}")

    text = "\n".join(lines)
    ax6.text(
        0.05,
        0.95,
        text,
        transform=ax6.transAxes,
        fontsize=9,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="#f5f5f5", alpha=0.8),
    )

    output_path = Path(output_dir) / "phase0_decision_dashboard.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Dashboard saved to: {output_path}")
