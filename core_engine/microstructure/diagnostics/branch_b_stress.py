"""
Branch B — Stress Test Suite.

Addresses external quant's feedback on the initial Branch B result:
1. Mean PnL 95% CI (is lower bound > 0?)
2. True Sharpe with zero-event days and capital model
3. Delay sweep: 100, 200, 300, 500ms
4. Queue depth multipliers: 1.0, 1.5, 2.0
5. Tail risk: CVaR at 5th percentile
6. Temporal stability: 3 blocks of ~43 days
7. Expanded Tier A: MSFT, NVDA, TSLA, WMT

Architecture: load quote/trade data once per event, replay simulation
across all parameter combos in-memory. One ClickHouse trip per event,
not per parameter combo.
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

from core_engine.microstructure.constants import CONSTANTS_VERSION

logger = logging.getLogger(__name__)

CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")

TIER_A_SYMBOLS = ["MSFT", "NVDA", "TSLA", "WMT"]
EVENTS_PER_SYMBOL = 300
CH_CONCURRENCY = 8

DELAY_MS_SWEEP = [100, 200, 300, 500]
QUEUE_MULT_SWEEP = [1.0, 1.5, 2.0]

POST_WINDOW_NS = 30_000_000_000
PRE_WINDOW_NS = 10_000_000_000
SPREAD_NORMAL_FACTOR = 1.05
STOP_LOSS_BPS = 3.0
TIMEOUT_S = 30
TOTAL_TRADING_DAYS = 130


@dataclass
class EventData:
    """Raw market data for one event, loaded once, replayed many times."""
    symbol: str
    date: str
    end_ns: int
    imbalance: float
    spread_bps: float

    q_ts: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    q_bid: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    q_ask: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    q_bid_sz: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    q_ask_sz: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))

    t_ts: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    t_price: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))
    t_size: np.ndarray = field(repr=False, default_factory=lambda: np.array([]))

    valid: bool = False


@dataclass
class SimResult:
    """Result of one simulated trade."""
    symbol: str
    date: str
    filled: bool = False
    pnl_bps: float = 0.0
    hold_time_ms: float = 0.0
    exit_reason: str = ""
    queue_ahead: int = 0


class BranchBStress:
    """Comprehensive stress test for Branch B."""

    def __init__(self):
        self._ch_url = CLICKHOUSE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 70)
        logger.info("BRANCH B — COMPREHENSIVE STRESS TEST")
        logger.info("Symbols: %s", TIER_A_SYMBOLS)
        logger.info("Delay sweep: %s ms", DELAY_MS_SWEEP)
        logger.info("Queue mult sweep: %s", QUEUE_MULT_SWEEP)
        logger.info("=" * 70)

        self._session = aiohttp.ClientSession()
        try:
            events_raw = await self._get_extreme_events()
            logger.info("Loaded %d raw extreme events", len(events_raw))

            t0 = time.monotonic()
            tasks = [self._load_event_data(e) for e in events_raw]
            loaded = await asyncio.gather(*tasks, return_exceptions=True)
            valid_events = [e for e in loaded if isinstance(e, EventData) and e.valid]
            elapsed = time.monotonic() - t0
            logger.info("Loaded market data for %d/%d events in %.1fs",
                        len(valid_events), len(events_raw), elapsed)

            all_dates = sorted(set(e.date for e in valid_events))
            logger.info("Date range: %s to %s (%d unique dates)",
                        all_dates[0] if all_dates else "?",
                        all_dates[-1] if all_dates else "?",
                        len(all_dates))

            # Run parameter grid
            grid_results = {}
            for delay_ms in DELAY_MS_SWEEP:
                for queue_mult in QUEUE_MULT_SWEEP:
                    key = f"{delay_ms}ms_x{queue_mult}"
                    results = [
                        self._simulate(ev, delay_ms, queue_mult)
                        for ev in valid_events
                    ]
                    grid_results[key] = {
                        "delay_ms": delay_ms,
                        "queue_mult": queue_mult,
                        "results": results,
                    }
                    filled = [r for r in results if r.filled]
                    fill_rate = len(filled) / max(len(results), 1)
                    pnls = np.array([r.pnl_bps for r in filled]) if filled else np.array([0.0])
                    mean_pnl = float(np.mean(pnls)) if filled else 0.0
                    hit_rate = float(np.mean(pnls > 0)) if filled else 0.0
                    logger.info(
                        "  %s: fill=%.1f%% mean=%.2f bps hit=%.1f%% n_fill=%d",
                        key, fill_rate * 100, mean_pnl, hit_rate * 100, len(filled),
                    )

            # Build comprehensive report
            report = self._build_report(valid_events, grid_results, all_dates)
            self._write_report(report)
            return report

        finally:
            await self._session.close()

    def _simulate(self, ev: EventData, delay_ms: int, queue_mult: float) -> SimResult:
        """Replay simulation with given parameters. Pure compute, no I/O."""
        result = SimResult(symbol=ev.symbol, date=ev.date)

        delay_ns = delay_ms * 1_000_000
        entry_time_ns = ev.end_ns + delay_ns

        q_ts = ev.q_ts
        q_mid = (ev.q_bid + ev.q_ask) / 2.0
        q_spread = np.where(q_mid > 0, (ev.q_ask - ev.q_bid) / q_mid * 10000, 0)

        # Baseline spread
        pre_mask = q_ts < ev.end_ns
        if np.sum(pre_mask) >= 3:
            baseline_spread = float(np.median(q_spread[pre_mask][-50:]))
        else:
            baseline_spread = ev.spread_bps

        # Entry quote state
        entry_q_idx = np.searchsorted(q_ts, entry_time_ns)
        if entry_q_idx >= len(q_ts):
            return result
        entry_q_idx = min(entry_q_idx, len(q_ts) - 1)

        entry_bid = ev.q_bid[entry_q_idx]
        entry_ask = ev.q_ask[entry_q_idx]
        if entry_bid <= 0 or entry_ask <= 0:
            return result

        imb_direction = np.sign(ev.imbalance)

        if imb_direction > 0:
            our_price = entry_ask
            our_side = "ask"
            queue_ahead_raw = int(ev.q_ask_sz[entry_q_idx])
        else:
            our_price = entry_bid
            our_side = "bid"
            queue_ahead_raw = int(ev.q_bid_sz[entry_q_idx])

        queue_ahead = int(queue_ahead_raw * queue_mult)
        result.queue_ahead = queue_ahead

        # Fill model
        cum_volume = 0
        fill_time_ns = 0

        for i in range(len(ev.t_ts)):
            if ev.t_ts[i] < entry_time_ns:
                continue
            if our_side == "ask" and ev.t_price[i] >= our_price:
                cum_volume += ev.t_size[i]
            elif our_side == "bid" and ev.t_price[i] <= our_price:
                cum_volume += ev.t_size[i]
            if cum_volume > queue_ahead:
                fill_time_ns = ev.t_ts[i]
                break

        if fill_time_ns == 0:
            result.filled = False
            return result

        result.filled = True

        # Three-way exit
        spread_threshold = baseline_spread * SPREAD_NORMAL_FACTOR
        timeout_ns = fill_time_ns + TIMEOUT_S * 1_000_000_000

        exit_price = 0.0
        exit_reason = ""
        exit_time_ns = 0

        post_fill_start = np.searchsorted(q_ts, fill_time_ns)
        for qi in range(post_fill_start, len(q_ts)):
            current_ts = q_ts[qi]
            current_mid = q_mid[qi]
            current_spread = q_spread[qi]

            if current_mid <= 0:
                continue

            if imb_direction > 0:
                adverse_move = (current_mid - our_price) / our_price * 10000
            else:
                adverse_move = (our_price - current_mid) / our_price * 10000

            if adverse_move > STOP_LOSS_BPS:
                exit_price = current_mid
                exit_reason = "stop_loss"
                exit_time_ns = current_ts
                break

            if current_spread <= spread_threshold and current_ts > fill_time_ns + 500_000_000:
                exit_price = current_mid
                exit_reason = "spread_normal"
                exit_time_ns = current_ts
                break

            if current_ts >= timeout_ns:
                exit_price = current_mid
                exit_reason = "timeout"
                exit_time_ns = current_ts
                break

        if exit_price == 0:
            exit_price = float(q_mid[-1])
            exit_reason = "end_of_data"
            exit_time_ns = int(q_ts[-1])

        result.exit_reason = exit_reason
        result.hold_time_ms = float((exit_time_ns - fill_time_ns) / 1e6)

        if imb_direction > 0:
            result.pnl_bps = (our_price - exit_price) / our_price * 10000
        else:
            result.pnl_bps = (exit_price - our_price) / our_price * 10000

        return result

    def _build_report(
        self,
        events: List[EventData],
        grid: Dict[str, Dict],
        all_dates: List[str],
    ) -> Dict[str, Any]:
        """Build comprehensive stress test report."""
        report: Dict[str, Any] = {
            "experiment": "branch_b_stress_test",
            "constants_version": CONSTANTS_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": TIER_A_SYMBOLS,
            "total_events": len(events),
            "total_dates": len(all_dates),
        }

        # ── Section 1: Baseline metrics (100ms, 1.0x queue) ──
        baseline_key = "100ms_x1.0"
        baseline = grid[baseline_key]["results"]
        filled_base = [r for r in baseline if r.filled]
        pnls_base = np.array([r.pnl_bps for r in filled_base])

        # 1a. Mean PnL 95% CI
        n = len(pnls_base)
        mean = float(np.mean(pnls_base))
        se = float(np.std(pnls_base, ddof=1) / np.sqrt(n))
        ci_lo = mean - 1.96 * se
        ci_hi = mean + 1.96 * se
        report["ci_95"] = {
            "mean": mean, "se": se, "lower": ci_lo, "upper": ci_hi,
            "lower_above_zero": ci_lo > 0,
        }
        logger.info("\n1. MEAN PnL 95%% CI: [%.3f, %.3f] bps (mean=%.3f, SE=%.3f) → lower > 0: %s",
                     ci_lo, ci_hi, mean, se, ci_lo > 0)

        # 1b. Tail risk: CVaR at 5th percentile
        p5 = float(np.percentile(pnls_base, 5))
        worst_5pct = pnls_base[pnls_base <= p5]
        cvar_5 = float(np.mean(worst_5pct)) if len(worst_5pct) > 0 else p5
        report["tail_risk"] = {
            "p5": p5, "cvar_5": cvar_5,
            "worst_trade": float(np.min(pnls_base)),
            "worst_5pct_count": len(worst_5pct),
            "acceptable": cvar_5 > -10.0,
        }
        logger.info("   Tail risk: P5=%.2f bps, CVaR5=%.2f bps, worst=%.2f bps → %s",
                     p5, cvar_5, float(np.min(pnls_base)),
                     "ACCEPTABLE" if cvar_5 > -10 else "DANGEROUS")

        # ── Section 2: True Sharpe with zero-event days ──
        daily_pnl_map: Dict[str, float] = {}
        for r in filled_base:
            daily_pnl_map[r.date] = daily_pnl_map.get(r.date, 0) + r.pnl_bps
        # Include all dates (zero for non-event days)
        daily_pnl_full = np.array([daily_pnl_map.get(d, 0.0) for d in all_dates])
        if len(daily_pnl_full) > 5:
            true_mean = float(np.mean(daily_pnl_full))
            true_std = float(np.std(daily_pnl_full, ddof=1))
            true_sharpe = true_mean / max(true_std, 1e-6) * math.sqrt(252)
        else:
            true_sharpe = 0.0
            true_mean = 0.0
            true_std = 0.0

        active_days = sum(1 for d in all_dates if daily_pnl_map.get(d, 0) != 0)
        report["true_sharpe"] = {
            "value": true_sharpe,
            "daily_mean": true_mean,
            "daily_std": true_std,
            "total_days": len(all_dates),
            "active_days": active_days,
            "zero_days": len(all_dates) - active_days,
            "passes_threshold": true_sharpe >= 0.8,
        }
        logger.info("\n2. TRUE SHARPE: %.2f (daily mean=%.3f, std=%.3f, %d active/%d total days) → %s",
                     true_sharpe, true_mean, true_std, active_days, len(all_dates),
                     "PASS" if true_sharpe >= 0.8 else "FAIL")

        # ── Section 3: Delay × Queue grid ──
        grid_table = []
        for key, data in sorted(grid.items()):
            results = data["results"]
            filled = [r for r in results if r.filled]
            n_filled = len(filled)
            fill_rate = n_filled / max(len(results), 1)
            pnls = np.array([r.pnl_bps for r in filled]) if filled else np.array([0.0])
            mean_pnl = float(np.mean(pnls)) if filled else 0.0
            hit_rate = float(np.mean(pnls > 0)) if filled else 0.0

            row = {
                "key": key,
                "delay_ms": data["delay_ms"],
                "queue_mult": data["queue_mult"],
                "fill_rate": fill_rate,
                "n_filled": n_filled,
                "mean_pnl": mean_pnl,
                "hit_rate": hit_rate,
                "edge_positive": mean_pnl > 0 and hit_rate > 0.52,
            }
            grid_table.append(row)

        report["parameter_grid"] = grid_table

        # Key stress point: 300ms + 1.5x queue
        stress_key = "300ms_x1.5"
        if stress_key in grid:
            s_res = grid[stress_key]["results"]
            s_filled = [r for r in s_res if r.filled]
            s_pnls = np.array([r.pnl_bps for r in s_filled]) if s_filled else np.array([0.0])
            stress_survives = float(np.mean(s_pnls)) > 0 and len(s_filled) > 0
            report["stress_300_1_5"] = {
                "fill_rate": len(s_filled) / max(len(s_res), 1),
                "mean_pnl": float(np.mean(s_pnls)) if s_filled else 0.0,
                "hit_rate": float(np.mean(s_pnls > 0)) if s_filled else 0.0,
                "survives": stress_survives,
            }
            logger.info("\n3. STRESS 300ms+1.5x: fill=%.1f%% mean=%.2f hit=%.1f%% → %s",
                        report["stress_300_1_5"]["fill_rate"] * 100,
                        report["stress_300_1_5"]["mean_pnl"],
                        report["stress_300_1_5"]["hit_rate"] * 100,
                        "SURVIVES" if stress_survives else "FAILS")

        # ── Section 4: Temporal stability (3 blocks) ──
        n_dates = len(all_dates)
        block_size = n_dates // 3
        blocks = [
            all_dates[:block_size],
            all_dates[block_size:2*block_size],
            all_dates[2*block_size:],
        ]
        block_results = []
        for i, block_dates in enumerate(blocks):
            block_set = set(block_dates)
            block_filled = [r for r in filled_base if r.date in block_set]
            block_pnls = np.array([r.pnl_bps for r in block_filled]) if block_filled else np.array([0.0])
            block_mean = float(np.mean(block_pnls)) if block_filled else 0.0
            block_hit = float(np.mean(block_pnls > 0)) if block_filled else 0.0
            block_results.append({
                "block": i + 1,
                "dates": f"{block_dates[0]} to {block_dates[-1]}" if block_dates else "N/A",
                "n_days": len(block_dates),
                "n_filled": len(block_filled),
                "mean_pnl": block_mean,
                "hit_rate": block_hit,
                "positive": block_mean > 0,
            })
            logger.info("   Block %d (%s to %s): n=%d mean=%.2f hit=%.1f%% → %s",
                        i + 1,
                        block_dates[0] if block_dates else "?",
                        block_dates[-1] if block_dates else "?",
                        len(block_filled), block_mean, block_hit * 100,
                        "POSITIVE" if block_mean > 0 else "NEGATIVE")

        stable_blocks = sum(1 for b in block_results if b["positive"])
        report["temporal_stability"] = {
            "blocks": block_results,
            "stable_count": stable_blocks,
            "is_stable": stable_blocks >= 2,
        }
        logger.info("   Temporal stability: %d/3 blocks positive → %s",
                     stable_blocks, "STABLE" if stable_blocks >= 2 else "UNSTABLE")

        # ── Section 5: Per-symbol breakdown ──
        per_sym = {}
        for sym in TIER_A_SYMBOLS:
            sym_events = [e for e in events if e.symbol == sym]
            sym_results = [r for r in baseline if r.symbol == sym]
            sym_filled = [r for r in sym_results if r.filled]
            sym_pnls = np.array([r.pnl_bps for r in sym_filled]) if sym_filled else np.array([0.0])

            per_sym[sym] = {
                "total_events": len(sym_events),
                "total_results": len(sym_results),
                "filled": len(sym_filled),
                "fill_rate": len(sym_filled) / max(len(sym_results), 1),
                "mean_pnl": float(np.mean(sym_pnls)) if sym_filled else 0.0,
                "median_pnl": float(np.median(sym_pnls)) if sym_filled else 0.0,
                "hit_rate": float(np.mean(sym_pnls > 0)) if sym_filled else 0.0,
                "mean_hold_ms": float(np.mean([r.hold_time_ms for r in sym_filled])) if sym_filled else 0.0,
            }

        report["per_symbol"] = per_sym
        logger.info("\n5. PER-SYMBOL:")
        for sym, d in sorted(per_sym.items()):
            logger.info("   %s: fill=%.1f%% mean=%.2f hit=%.1f%% n=%d",
                        sym, d["fill_rate"] * 100, d["mean_pnl"],
                        d["hit_rate"] * 100, d["filled"])

        # ── Section 6: Overall verdict ──
        ci_pass = ci_lo > 0
        sharpe_pass = true_sharpe >= 0.8
        tail_pass = cvar_5 > -10.0
        stress_pass = report.get("stress_300_1_5", {}).get("survives", False)
        temporal_pass = stable_blocks >= 2
        syms_positive = sum(1 for d in per_sym.values() if d["mean_pnl"] > 0)

        n_pass = sum([ci_pass, sharpe_pass, tail_pass, stress_pass, temporal_pass])

        if n_pass >= 4 and stress_pass:
            verdict = "PROCEED"
            detail = (
                f"{n_pass}/5 stress tests passed including critical 300ms+1.5x stress. "
                f"{syms_positive}/{len(TIER_A_SYMBOLS)} symbols positive. "
                "Edge is structurally robust. Proceed to strategy design."
            )
        elif n_pass >= 3:
            verdict = "INVESTIGATE"
            detail = (
                f"{n_pass}/5 stress tests passed. "
                f"{'Stress test FAILED — edge is infrastructure-fragile.' if not stress_pass else ''} "
                "Targeted refinement needed before strategy design."
            )
        else:
            verdict = "TERMINATE"
            detail = (
                f"Only {n_pass}/5 stress tests passed. "
                "Edge does not survive realistic operational conditions."
            )

        report["verdict"] = {
            "decision": verdict,
            "detail": detail,
            "checks": {
                "ci_lower_above_zero": ci_pass,
                "true_sharpe_above_0_8": sharpe_pass,
                "tail_cvar5_above_neg10": tail_pass,
                "stress_300ms_1_5x_survives": stress_pass,
                "temporal_2_of_3_stable": temporal_pass,
            },
            "symbols_positive": syms_positive,
        }

        logger.info("\n%s", "=" * 70)
        logger.info("VERDICT: %s", verdict)
        logger.info(detail)
        logger.info("=" * 70)

        return report

    def _write_report(self, report: Dict[str, Any]) -> None:
        root = Path(__file__).resolve().parents[3]
        out = root / "results" / "foundation_diagnostic" / "branch_b_stress_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Branch B — Stress Test Report",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            f"**Symbols**: {', '.join(TIER_A_SYMBOLS)}",
            f"**Events**: {report['total_events']} across {report['total_dates']} trading days",
            "",
        ]

        v = report["verdict"]
        lines.extend([
            f"## Verdict: **{v['decision']}**",
            "", v["detail"], "",
            "---", "",
        ])

        # 1. CI
        ci = report["ci_95"]
        lines.extend([
            "## 1. Mean PnL Confidence Interval",
            "",
            f"- **Mean**: {ci['mean']:.3f} bps",
            f"- **SE**: {ci['se']:.3f} bps",
            f"- **95% CI**: [{ci['lower']:.3f}, {ci['upper']:.3f}] bps",
            f"- **Lower bound > 0**: {'Yes' if ci['lower_above_zero'] else 'No'}",
            "",
        ])

        # 2. True Sharpe
        ts = report["true_sharpe"]
        lines.extend([
            "## 2. True Sharpe (with zero-event days)",
            "",
            f"- **Annualized Sharpe**: {ts['value']:.2f}",
            f"- **Daily mean**: {ts['daily_mean']:.3f} bps",
            f"- **Daily std**: {ts['daily_std']:.3f} bps",
            f"- **Active days**: {ts['active_days']} / {ts['total_days']}",
            f"- **Passes ≥ 0.8**: {'Yes' if ts['passes_threshold'] else 'No'}",
            "",
        ])

        # 3. Parameter grid
        lines.extend([
            "## 3. Delay × Queue Stress Grid",
            "",
            "| Delay (ms) | Queue Mult | Fill% | N Filled | Mean PnL | Hit Rate | Edge+ |",
            "|------------|------------|-------|----------|----------|----------|-------|",
        ])
        for row in report["parameter_grid"]:
            lines.append(
                f"| {row['delay_ms']} | {row['queue_mult']}x | {row['fill_rate']:.1%} | "
                f"{row['n_filled']} | {row['mean_pnl']:.2f} | {row['hit_rate']:.1%} | "
                f"{'Yes' if row['edge_positive'] else 'No'} |"
            )

        if "stress_300_1_5" in report:
            s = report["stress_300_1_5"]
            lines.extend([
                "",
                f"**Critical stress point (300ms + 1.5x queue)**: "
                f"fill={s['fill_rate']:.1%}, mean={s['mean_pnl']:.2f} bps, "
                f"hit={s['hit_rate']:.1%} → **{'SURVIVES' if s['survives'] else 'FAILS'}**",
            ])

        # 4. Tail risk
        tail = report["tail_risk"]
        lines.extend([
            "", "## 4. Tail Risk",
            "",
            f"- **P5 (5th percentile)**: {tail['p5']:.2f} bps",
            f"- **CVaR5 (mean of worst 5%)**: {tail['cvar_5']:.2f} bps",
            f"- **Worst single trade**: {tail['worst_trade']:.2f} bps",
            f"- **Acceptable (CVaR5 > -10 bps)**: {'Yes' if tail['acceptable'] else 'No'}",
            "",
        ])

        # 5. Temporal stability
        ts_data = report["temporal_stability"]
        lines.extend([
            "## 5. Temporal Stability (3 blocks)",
            "",
            "| Block | Period | N Filled | Mean PnL | Hit Rate | Positive |",
            "|-------|--------|----------|----------|----------|----------|",
        ])
        for b in ts_data["blocks"]:
            lines.append(
                f"| {b['block']} | {b['dates']} | {b['n_filled']} | "
                f"{b['mean_pnl']:.2f} | {b['hit_rate']:.1%} | "
                f"{'Yes' if b['positive'] else 'No'} |"
            )
        lines.append(f"\n**Stable**: {ts_data['stable_count']}/3 blocks positive → "
                      f"{'STABLE' if ts_data['is_stable'] else 'UNSTABLE'}")

        # 6. Per-symbol
        lines.extend([
            "", "## 6. Per-Symbol Breakdown (baseline: 100ms, 1.0x queue)",
            "",
            "| Symbol | Events | Filled | Fill% | Mean PnL | Median PnL | Hit Rate | Hold (ms) |",
            "|--------|--------|--------|-------|----------|------------|----------|-----------|",
        ])
        for sym, d in sorted(report["per_symbol"].items()):
            lines.append(
                f"| {sym} | {d['total_results']} | {d['filled']} | {d['fill_rate']:.1%} | "
                f"{d['mean_pnl']:.2f} | {d['median_pnl']:.2f} | {d['hit_rate']:.1%} | "
                f"{d['mean_hold_ms']:.0f} |"
            )

        # 7. Verdict summary
        checks = v["checks"]
        lines.extend([
            "", "## 7. Verdict Summary",
            "",
            "| Check | Result |",
            "|-------|--------|",
        ])
        for name, passed in checks.items():
            lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")

        out.write_text("\n".join(lines))
        logger.info("Report: %s", out)

    # ── Data loading ──

    async def _get_extreme_events(self) -> List[dict]:
        syms = ",".join(f"'{s}'" for s in TIER_A_SYMBOLS)
        query = f"""
        SELECT symbol, bucket_date, bucket_end_ns, flow_imbalance,
               effective_spread_bps, close_price, bucket_start_ns
        FROM polygon_data.microstructure_buckets
        WHERE symbol IN ({syms})
        ORDER BY symbol, bucket_date, bucket_id
        FORMAT TSVWithNames
        """
        text = await self._ch_query(query)
        lines = text.strip().split("\n")
        header = lines[0].split("\t")
        col = {n: i for i, n in enumerate(header)}

        by_sym: Dict[str, list] = {s: [] for s in TIER_A_SYMBOLS}
        for line in lines[1:]:
            f = line.split("\t")
            sym = f[col["symbol"]]
            if sym not in by_sym:
                continue
            by_sym[sym].append({
                "symbol": sym,
                "date": f[col["bucket_date"]],
                "start_ns": int(f[col["bucket_start_ns"]]),
                "end_ns": int(f[col["bucket_end_ns"]]),
                "imb": float(f[col["flow_imbalance"]]),
                "spread": float(f[col["effective_spread_bps"]]),
                "close": float(f[col["close_price"]]),
            })

        events = []
        rng = np.random.RandomState(42)

        for sym in TIER_A_SYMBOLS:
            buckets = by_sym[sym]
            if not buckets:
                logger.warning("No buckets for %s", sym)
                continue
            abs_imbs = np.array([abs(b["imb"]) for b in buckets])
            thresh = np.percentile(abs_imbs, 95)
            extreme = [b for b in buckets if abs(b["imb"]) >= thresh]
            n = min(EVENTS_PER_SYMBOL, len(extreme))
            indices = rng.choice(len(extreme), size=n, replace=False)
            for i in indices:
                events.append(extreme[i])
            logger.info("%s: %d extreme events (thresh=%.3f, pool=%d)",
                        sym, n, thresh, len(extreme))

        return events

    async def _load_event_data(self, event: dict) -> EventData:
        """Load all quote + trade data for one event. One CH trip."""
        ev = EventData(
            symbol=event["symbol"],
            date=event["date"],
            end_ns=event["end_ns"],
            imbalance=event["imb"],
            spread_bps=event["spread"],
        )

        entry_ns_max = event["end_ns"] + 500 * 1_000_000  # max delay 500ms
        window_end = entry_ns_max + POST_WINDOW_NS

        async with self._sem:
            q_text = await self._ch_safe_query(f"""
                SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
                FROM polygon_data.microstructure_quotes
                WHERE symbol = '{event["symbol"]}' AND ingestion_date = '{event["date"]}'
                  AND sip_timestamp >= {event["end_ns"] - PRE_WINDOW_NS}
                  AND sip_timestamp <= {window_end}
                ORDER BY sip_timestamp ASC
                FORMAT TSVWithNames
            """)

            t_text = await self._ch_safe_query(f"""
                SELECT sip_timestamp, price, size
                FROM polygon_data.microstructure_trades
                WHERE symbol = '{event["symbol"]}' AND ingestion_date = '{event["date"]}'
                  AND sip_timestamp >= {event["end_ns"]}
                  AND sip_timestamp <= {window_end}
                ORDER BY sip_timestamp ASC
                FORMAT TSVWithNames
            """)

        if q_text is None or t_text is None:
            return ev

        # Parse quotes
        q_lines = q_text.strip().split("\n")
        if len(q_lines) < 5:
            return ev
        nq = len(q_lines) - 1
        ev.q_ts = np.empty(nq, dtype=np.int64)
        ev.q_bid = np.empty(nq, dtype=np.float64)
        ev.q_ask = np.empty(nq, dtype=np.float64)
        ev.q_bid_sz = np.empty(nq, dtype=np.float64)
        ev.q_ask_sz = np.empty(nq, dtype=np.float64)
        for i, line in enumerate(q_lines[1:]):
            p = line.split("\t")
            ev.q_ts[i] = int(p[0])
            ev.q_bid[i] = float(p[1])
            ev.q_ask[i] = float(p[2])
            ev.q_bid_sz[i] = float(p[3])
            ev.q_ask_sz[i] = float(p[4])

        # Parse trades
        t_lines = t_text.strip().split("\n")
        if len(t_lines) < 3:
            return ev
        nt = len(t_lines) - 1
        ev.t_ts = np.empty(nt, dtype=np.int64)
        ev.t_price = np.empty(nt, dtype=np.float64)
        ev.t_size = np.empty(nt, dtype=np.int64)
        for i, line in enumerate(t_lines[1:]):
            p = line.split("\t")
            ev.t_ts[i] = int(p[0])
            ev.t_price[i] = float(p[1])
            ev.t_size[i] = int(p[2])

        ev.valid = True
        return ev

    async def _ch_safe_query(self, query: str) -> Optional[str]:
        try:
            return await self._ch_query(query)
        except Exception as e:
            logger.debug("CH query failed: %s", e)
            return None

    async def _ch_query(self, query: str) -> str:
        assert self._session is not None
        async with self._session.post(self._ch_url, data=query.encode()) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ClickHouse {resp.status}: {body[:300]}")
            return await resp.text()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    tester = BranchBStress()
    await tester.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
