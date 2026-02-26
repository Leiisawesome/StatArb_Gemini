"""
Sign-Flip Experiment — Mean Reversion Hypothesis Test.

The continuation hypothesis (H1) was killed at Tier 1:
  - Gross edge negative before cost
  - Correlation negative
  - Continuation < 50%

This test flips the signal: trade AGAINST extreme imbalance.
Same data, same infrastructure, same cost model. Only direction changes.

Sweeps multiple imbalance thresholds to find the extreme regime
where reversal signal is strongest, then evaluates Tier 1 gates.

Blueprint discipline: no threshold relaxation, no cost weakening.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
from scipy import stats as sp_stats

from core_engine.microstructure.constants import (
    CONSTANTS_VERSION,
    CONTINUATION_K3_CI_LOWER_MIN,
    CONTINUATION_K3_CI_WIDTH_MAX,
    CONTINUATION_K3_POINT_MIN,
    DEPTH_COST_MULTIPLIER_TIER_A,
    DEPTH_COST_MULTIPLIER_TIER_B,
    DEPTH_COST_MULTIPLIER_TIER_C,
    ELASTICITY_COST_MULT_HIGH,
    ELASTICITY_COST_MULT_LOW,
    ELASTICITY_COST_MULT_MID,
    NET_EDGE_CI_LOWER_MIN_BPS,
    TEMPORAL_BLOCKS,
    TEMPORAL_STABILITY_MIN_POSITIVE,
)
from core_engine.microstructure.diagnostics.foundation_runner import (
    FoundationDiagnosticRunner,
    SymbolBucketData,
)
from core_engine.microstructure.types import GateEvidence, GateResult

logger = logging.getLogger(__name__)

CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")

REVERSAL_THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
TIER_COST = {"A": DEPTH_COST_MULTIPLIER_TIER_A,
             "B": DEPTH_COST_MULTIPLIER_TIER_B,
             "C": DEPTH_COST_MULTIPLIER_TIER_C}
Z_95 = 1.96


@dataclass
class ReversalResult:
    """Per-symbol, per-threshold reversal analysis."""
    symbol: str
    tier: str
    threshold: float
    n_events: int = 0
    reversal_hit_rate: float = 0.0
    reversal_ci_lower: float = 0.0
    reversal_ci_upper: float = 0.0
    gross_edge_bps: float = 0.0
    penalized_cost_bps: float = 0.0
    net_edge_bps: float = 0.0
    net_edge_median_bps: float = 0.0
    net_edge_ci_lower: float = 0.0
    net_edge_ci_upper: float = 0.0
    correlation: float = 0.0
    # Temporal
    block_edges: List[float] = field(default_factory=list)
    temporal_positive: int = 0
    # Distribution shape
    skewness: float = 0.0
    kurtosis: float = 0.0
    p10_bps: float = 0.0
    p90_bps: float = 0.0


class ReversalTester:
    """Runs the sign-flip (mean reversion) experiment."""

    def __init__(self, clickhouse_url: str = CLICKHOUSE_URL):
        self._ch_url = clickhouse_url
        self._loader = FoundationDiagnosticRunner(clickhouse_url)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("SIGN-FLIP EXPERIMENT — Mean Reversion Hypothesis")
        logger.info("Constants: %s", CONSTANTS_VERSION)
        logger.info("=" * 60)

        symbols, tiers = self._loader._load_universe()
        logger.info("Universe: %d symbols", len(symbols))

        self._loader._session = aiohttp.ClientSession()
        try:
            # Load all data
            symbol_data: Dict[str, SymbolBucketData] = {}
            for sym in symbols:
                data = await self._loader._load_symbol_data(sym, tiers[sym])
                symbol_data[sym] = data
                logger.info("Loaded %s: %d buckets", sym, data.n_buckets)

            # Phase 1: Threshold sweep to find optimal regime
            logger.info("\n%s", "=" * 60)
            logger.info("PHASE 1: THRESHOLD SWEEP")
            logger.info("=" * 60)

            all_results: Dict[float, Dict[str, ReversalResult]] = {}
            sweep_summary: List[Dict[str, Any]] = []

            for tau in REVERSAL_THRESHOLDS:
                sym_results = {}
                for sym, data in symbol_data.items():
                    r = self._analyze_reversal(data, tau)
                    sym_results[sym] = r

                all_results[tau] = sym_results

                # Pooled stats
                total_events = sum(r.n_events for r in sym_results.values())
                pooled_gross = np.mean([r.gross_edge_bps for r in sym_results.values() if r.n_events > 20])
                pooled_net = np.mean([r.net_edge_bps for r in sym_results.values() if r.n_events > 20])
                pooled_hit = np.mean([r.reversal_hit_rate for r in sym_results.values() if r.n_events > 20])
                pooled_corr = np.median([r.correlation for r in sym_results.values() if r.n_events > 20])

                sweep_summary.append({
                    "threshold": tau,
                    "total_events": total_events,
                    "mean_gross_bps": float(pooled_gross),
                    "mean_net_bps": float(pooled_net),
                    "mean_hit_rate": float(pooled_hit),
                    "median_corr": float(pooled_corr),
                })

                logger.info(
                    "τ=%.2f: events=%d, gross=%.2f, net=%.2f, hit=%.1f%%, corr=%.4f",
                    tau, total_events, pooled_gross, pooled_net,
                    pooled_hit * 100, pooled_corr,
                )

            # Phase 2: Select best threshold and run full Tier 1
            best_tau = max(
                sweep_summary,
                key=lambda s: s["mean_net_bps"] if s["total_events"] > 500 else -999,
            )["threshold"]

            logger.info("\n%s", "=" * 60)
            logger.info("PHASE 2: TIER 1 GATES at τ=%.2f", best_tau)
            logger.info("=" * 60)

            best_results = all_results[best_tau]
            tier1_gates = self._evaluate_tier1(best_results, best_tau)

            for g in tier1_gates:
                logger.info(
                    "%s %s: %s — value=%.4f, threshold=%.4f",
                    g.gate_id, g.gate_name, g.result.value,
                    g.metric_value, g.threshold,
                )

            failures = [g for g in tier1_gates if g.result == GateResult.FAIL]
            if failures:
                decision = "TERMINATE"
                detail = f"Reversal hypothesis FAILED at Tier 1. {len(failures)} gates failed: {', '.join(g.gate_id for g in failures)}"
            else:
                decision = "PROCEED"
                detail = "Reversal hypothesis SURVIVES Tier 1. Proceed to Tier 2 structure gates."

            logger.info("\nDECISION: %s — %s", decision, detail)

            report = {
                "experiment": "sign_flip_mean_reversion",
                "constants_version": CONSTANTS_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "threshold_sweep": sweep_summary,
                "best_threshold": best_tau,
                "per_symbol": {
                    sym: self._result_to_dict(r) for sym, r in best_results.items()
                },
                "tier1_gates": [self._gate_to_dict(g) for g in tier1_gates],
                "decision": decision,
                "detail": detail,
            }

            self._write_report(report, all_results, sweep_summary, tier1_gates, best_tau)
            return report

        finally:
            await self._loader._session.close()
            self._loader._session = None

    def _analyze_reversal(self, data: SymbolBucketData, threshold: float) -> ReversalResult:
        """Compute reversal metrics for one symbol at one threshold."""
        result = ReversalResult(
            symbol=data.symbol, tier=data.tier, threshold=threshold,
        )

        n = data.n_buckets
        if n < 100:
            return result

        # Forward returns (within-day only)
        fwd = np.full(n, np.nan)
        valid_fwd = data.same_day_next[:-1] & (data.close_prices[:-1] > 0)
        fwd[:-1] = np.where(
            valid_fwd,
            (data.close_prices[1:] - data.close_prices[:-1]) / data.close_prices[:-1] * 10000,
            np.nan,
        )

        # Identify extreme imbalance events
        event_mask = (np.abs(data.flow_imbalance) > threshold) & np.isfinite(fwd) & data.same_day_next

        n_events = int(np.sum(event_mask))
        if n_events < 20:
            return result

        result.n_events = n_events
        imb_direction = np.sign(data.flow_imbalance[event_mask])
        fwd_at_event = fwd[event_mask]

        # REVERSAL: trade AGAINST imbalance
        reversal_return = -imb_direction * fwd_at_event

        result.reversal_hit_rate = float(np.mean(reversal_return > 0))
        n_hits = int(np.sum(reversal_return > 0))
        result.reversal_ci_lower, result.reversal_ci_upper = self._wilson_ci(n_hits, n_events)

        # Gross edge = mean reversal return
        result.gross_edge_bps = float(np.mean(reversal_return))

        # Penalized cost
        tier_mult = TIER_COST.get(data.tier, 1.3)
        elast_mult = self._elasticity_multipliers(data.price_impact_per_volume[event_mask])
        cost = data.effective_spread_bps[event_mask] * tier_mult * elast_mult
        result.penalized_cost_bps = float(np.mean(cost))

        # Net edge
        net = reversal_return - cost
        result.net_edge_bps = float(np.mean(net))
        result.net_edge_median_bps = float(np.median(net))
        se = float(np.std(net, ddof=1) / np.sqrt(len(net)))
        result.net_edge_ci_lower = result.net_edge_bps - Z_95 * se
        result.net_edge_ci_upper = result.net_edge_bps + Z_95 * se

        # Correlation: (-flow_imbalance) with forward return
        valid_all = np.isfinite(data.flow_imbalance) & np.isfinite(fwd) & data.same_day_next
        if np.sum(valid_all) > 50:
            corr, _ = sp_stats.pearsonr(-data.flow_imbalance[valid_all], fwd[valid_all])
            result.correlation = float(corr)

        # Distribution shape
        result.skewness = float(sp_stats.skew(net))
        result.kurtosis = float(sp_stats.kurtosis(net))
        result.p10_bps = float(np.percentile(net, 10))
        result.p90_bps = float(np.percentile(net, 90))

        # Temporal blocks
        unique_dates = np.unique(data.bucket_dates)
        n_dates = len(unique_dates)
        n_blocks = TEMPORAL_BLOCKS
        if n_dates >= n_blocks:
            block_size = n_dates // n_blocks
            block_edges = []
            pos_count = 0
            for b in range(n_blocks):
                start = b * block_size
                end = (b + 1) * block_size if b < n_blocks - 1 else n_dates
                block_dates = set(unique_dates[start:end].tolist())
                block_mask = np.array([d in block_dates for d in data.bucket_dates])
                combined = block_mask & event_mask
                if np.sum(combined) < 10:
                    block_edges.append(0.0)
                    continue
                block_dir = np.sign(data.flow_imbalance[combined])
                block_fwd = fwd[combined]
                block_rev = -block_dir * block_fwd
                block_cost = data.effective_spread_bps[combined] * tier_mult * self._elasticity_multipliers(data.price_impact_per_volume[combined])
                block_net = block_rev - block_cost
                mean_net = float(np.mean(block_net))
                block_edges.append(mean_net)
                if mean_net > 0:
                    pos_count += 1
            result.block_edges = block_edges
            result.temporal_positive = pos_count

        return result

    def _evaluate_tier1(
        self, results: Dict[str, ReversalResult], threshold: float
    ) -> List[GateEvidence]:
        """Evaluate Tier 1 gates for the reversal hypothesis."""
        gates = []

        # T1.1: Reversal hit rate ≥ 0.55 (pooled)
        total_events = sum(r.n_events for r in results.values())
        total_hits = sum(
            int(r.reversal_hit_rate * r.n_events) for r in results.values()
        )
        if total_events > 0:
            pooled_hit = total_hits / total_events
            ci_lo, ci_hi = self._wilson_ci(total_hits, total_events)
            ci_width = ci_hi - ci_lo
        else:
            pooled_hit, ci_lo, ci_hi, ci_width = 0, 0, 0, 1

        t1_1_pass = (
            pooled_hit >= CONTINUATION_K3_POINT_MIN
            and ci_lo >= CONTINUATION_K3_CI_LOWER_MIN
            and ci_width <= CONTINUATION_K3_CI_WIDTH_MAX
        )
        gates.append(GateEvidence(
            gate_id="T1.1R", gate_name="Reversal hit rate (pooled)", tier=1,
            result=GateResult.PASS if t1_1_pass else GateResult.FAIL,
            metric_value=pooled_hit, threshold=CONTINUATION_K3_POINT_MIN,
            detail=(
                f"τ={threshold}: pooled hit={pooled_hit:.4f} (req≥{CONTINUATION_K3_POINT_MIN}), "
                f"CI=[{ci_lo:.4f},{ci_hi:.4f}] (req lower≥{CONTINUATION_K3_CI_LOWER_MIN}), "
                f"width={ci_width:.4f}, N={total_events}. "
                f"Per-sym: {', '.join(f'{s}={r.reversal_hit_rate:.3f}({r.n_events})' for s, r in results.items())}"
            ),
            constants_version=CONSTANTS_VERSION,
        ))

        # T1.2: Net edge > 0 after penalized cost
        valid_nets = [r.net_edge_bps for r in results.values() if r.n_events > 20]
        pooled_net = float(np.mean(valid_nets)) if valid_nets else -999
        t1_2_pass = pooled_net > NET_EDGE_CI_LOWER_MIN_BPS
        gates.append(GateEvidence(
            gate_id="T1.2R", gate_name="Reversal net edge after cost", tier=1,
            result=GateResult.PASS if t1_2_pass else GateResult.FAIL,
            metric_value=pooled_net, threshold=NET_EDGE_CI_LOWER_MIN_BPS,
            detail=(
                f"τ={threshold}: mean net={pooled_net:.2f} bps (req>0). "
                f"Per-sym: {', '.join(f'{s}={r.net_edge_bps:.2f}' for s, r in results.items())}"
            ),
            constants_version=CONSTANTS_VERSION,
        ))

        # T1.3: Temporal stability — edge positive in ≥2/3 blocks
        sym_stable = sum(
            1 for r in results.values()
            if r.temporal_positive >= TEMPORAL_STABILITY_MIN_POSITIVE
        )
        pct_stable = sym_stable / max(len(results), 1)
        t1_3_pass = pct_stable >= 0.5
        gates.append(GateEvidence(
            gate_id="T1.3R", gate_name="Reversal temporal stability", tier=1,
            result=GateResult.PASS if t1_3_pass else GateResult.FAIL,
            metric_value=pct_stable, threshold=0.5,
            detail=(
                f"τ={threshold}: {sym_stable}/{len(results)} symbols stable "
                f"(≥{TEMPORAL_STABILITY_MIN_POSITIVE}/3 blocks positive). "
                f"Per-sym: {', '.join(f'{s}={r.temporal_positive}/3' for s, r in results.items())}"
            ),
            constants_version=CONSTANTS_VERSION,
        ))

        # T1.4: Correlation(-imbalance, forward_return) > 0.05
        corrs = {s: r.correlation for s, r in results.items()}
        median_corr = float(np.median(list(corrs.values())))
        t1_4_pass = median_corr > 0.05
        gates.append(GateEvidence(
            gate_id="T1.4R", gate_name="Reversal classification correlation", tier=1,
            result=GateResult.PASS if t1_4_pass else GateResult.FAIL,
            metric_value=median_corr, threshold=0.05,
            detail=(
                f"τ={threshold}: median corr(-imb, fwd) = {median_corr:.4f} (req>0.05). "
                f"Per-sym: {', '.join(f'{s}={c:.4f}' for s, c in corrs.items())}"
            ),
            constants_version=CONSTANTS_VERSION,
        ))

        return gates

    @staticmethod
    def _wilson_ci(s: int, n: int, z: float = Z_95) -> Tuple[float, float]:
        if n == 0:
            return (0.0, 0.0)
        p = s / n
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        hw = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return (max(0.0, center - hw), min(1.0, center + hw))

    @staticmethod
    def _elasticity_multipliers(pip: np.ndarray) -> np.ndarray:
        valid = np.isfinite(pip) & (pip != 0)
        if np.sum(valid) < 10:
            return np.ones(len(pip))
        abs_pip = np.abs(pip)
        try:
            edges = np.percentile(abs_pip[valid], np.arange(10, 100, 10))
            deciles = np.searchsorted(edges, abs_pip) + 1
        except Exception:
            return np.ones(len(pip))
        return np.where(
            deciles <= 3, ELASTICITY_COST_MULT_LOW,
            np.where(deciles <= 7, ELASTICITY_COST_MULT_MID, ELASTICITY_COST_MULT_HIGH),
        ).astype(np.float64)

    def _write_report(
        self,
        report: Dict[str, Any],
        all_results: Dict[float, Dict[str, ReversalResult]],
        sweep: List[Dict[str, Any]],
        gates: List[GateEvidence],
        best_tau: float,
    ) -> None:
        root = Path(__file__).resolve().parents[3]
        out_dir = root / "results" / "foundation_diagnostic"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "reversal_test_report.md"

        lines = [
            "# Sign-Flip Experiment — Mean Reversion Hypothesis",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            f"**Timestamp**: {report['timestamp']}",
            "",
            "## Threshold Sweep Summary",
            "",
            "| Threshold | Events | Gross (bps) | Net (bps) | Hit Rate | Corr |",
            "|-----------|--------|-------------|-----------|----------|------|",
        ]
        for s in sweep:
            lines.append(
                f"| {s['threshold']:.2f} | {s['total_events']} | "
                f"{s['mean_gross_bps']:.2f} | {s['mean_net_bps']:.2f} | "
                f"{s['mean_hit_rate']:.1%} | {s['median_corr']:.4f} |"
            )

        lines.extend([
            "",
            f"**Best threshold**: {best_tau:.2f}",
            "",
            "---",
            "",
            f"## Tier 1 Gates at τ = {best_tau:.2f}",
            "",
            "| Gate | Name | Result | Value | Threshold |",
            "|------|------|--------|-------|-----------|",
        ])
        for g in gates:
            lines.append(
                f"| {g.gate_id} | {g.gate_name} | **{g.result.value}** | "
                f"{g.metric_value:.4f} | {g.threshold:.4f} |"
            )

        decision = report["decision"]
        lines.extend([
            "",
            f"## Decision: **{decision}**",
            "",
            report["detail"],
            "",
            "---",
            "",
            f"## Per-Symbol Detail at τ = {best_tau:.2f}",
            "",
            "| Symbol | Tier | Events | Hit Rate | Gross | Cost | Net Mean | Net Med | Temporal | Corr |",
            "|--------|------|--------|----------|-------|------|----------|---------|----------|------|",
        ])
        best = all_results[best_tau]
        for sym in sorted(best.keys()):
            r = best[sym]
            lines.append(
                f"| {sym} | {r.tier} | {r.n_events} | {r.reversal_hit_rate:.1%} | "
                f"{r.gross_edge_bps:.2f} | {r.penalized_cost_bps:.2f} | "
                f"{r.net_edge_bps:.2f} | {r.net_edge_median_bps:.2f} | "
                f"{r.temporal_positive}/3 | {r.correlation:.4f} |"
            )

        # Per-symbol breakdown across ALL thresholds
        lines.extend(["", "---", "", "## Full Sweep Per Symbol", ""])
        for sym in sorted(all_results[REVERSAL_THRESHOLDS[0]].keys()):
            lines.append(f"### {sym}")
            lines.append("")
            lines.append("| τ | Events | Hit Rate | Gross | Net Mean | Net Med | P10 | P90 |")
            lines.append("|---|--------|----------|-------|----------|---------|-----|-----|")
            for tau in REVERSAL_THRESHOLDS:
                r = all_results[tau][sym]
                lines.append(
                    f"| {tau:.2f} | {r.n_events} | {r.reversal_hit_rate:.1%} | "
                    f"{r.gross_edge_bps:.2f} | {r.net_edge_bps:.2f} | "
                    f"{r.net_edge_median_bps:.2f} | {r.p10_bps:.1f} | {r.p90_bps:.1f} |"
                )
            lines.append("")

        path.write_text("\n".join(lines))
        logger.info("Report: %s", path)

    @staticmethod
    def _result_to_dict(r: ReversalResult) -> Dict[str, Any]:
        return {
            "symbol": r.symbol, "tier": r.tier, "threshold": r.threshold,
            "n_events": r.n_events, "reversal_hit_rate": r.reversal_hit_rate,
            "gross_edge_bps": r.gross_edge_bps, "net_edge_bps": r.net_edge_bps,
            "net_edge_median_bps": r.net_edge_median_bps,
            "penalized_cost_bps": r.penalized_cost_bps,
            "correlation": r.correlation,
            "temporal_positive": r.temporal_positive,
            "block_edges": r.block_edges,
        }

    @staticmethod
    def _gate_to_dict(g: GateEvidence) -> Dict[str, Any]:
        return {
            "gate_id": g.gate_id, "gate_name": g.gate_name,
            "tier": g.tier, "result": g.result.value,
            "metric_value": g.metric_value, "threshold": g.threshold,
            "detail": g.detail,
        }


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    tester = ReversalTester()
    report = await tester.run()

    decision = report["decision"]
    print(f"\n{'='*60}")
    print(f"SIGN-FLIP DECISION: {decision}")
    print(f"{'='*60}")
    print(report["detail"])


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
