"""
Event-Driven State Transition Experiment.

Bucket-level continuation (H1) and reversal (H1-R) both failed Tier 1.
The imbalance metric at ADV/200 resolution is informationally weak.

This experiment tests whether microstructure STATE TRANSITIONS are
detectable at the quote-level resolution after extreme imbalance events.

Approach:
  1. Identify top-5% extreme imbalance buckets
  2. Sample matched control buckets (40th-60th percentile)
  3. Query raw NBBO quotes in a 90-second window around each event
  4. Measure spread trajectory, midpoint change, refill speed, depth changes
  5. Compare extreme vs control (causal attribution)
  6. Evaluate whether transitions are predictable and potentially monetizable

No new data required. Pure re-analysis of existing ClickHouse data.
"""

from __future__ import annotations

import asyncio
import logging
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
from core_engine.microstructure.diagnostics.foundation_runner import (
    FoundationDiagnosticRunner,
)

logger = logging.getLogger(__name__)

CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")

EXTREME_PERCENTILE = 95
CONTROL_RANGE = (40, 60)
SAMPLE_PER_SYMBOL = 100
PRE_WINDOW_NS = 30_000_000_000
POST_WINDOW_NS = 60_000_000_000
MEASUREMENT_SECONDS = [1, 5, 10, 30, 60]
CH_CONCURRENCY = 8


@dataclass
class EventContext:
    """Bucket-level context for an extreme imbalance event."""
    symbol: str
    tier: str
    bucket_date: str
    bucket_end_ns: int
    flow_imbalance: float
    effective_spread_bps: float
    close_price: float
    classification_confidence: float
    is_extreme: bool


@dataclass
class TransitionMetrics:
    """Measured quote-level transition after an imbalance event."""
    symbol: str
    tier: str
    is_extreme: bool
    event_imbalance: float
    event_spread_bps: float

    pre_spread_bps: float = 0.0
    pre_midpoint: float = 0.0
    pre_quote_rate: float = 0.0
    pre_bid_size: float = 0.0
    pre_ask_size: float = 0.0

    # Spread at measurement points (bps)
    spread_1s: float = np.nan
    spread_5s: float = np.nan
    spread_10s: float = np.nan
    spread_30s: float = np.nan
    spread_60s: float = np.nan

    # Midpoint change from event end (bps)
    mid_change_1s: float = np.nan
    mid_change_5s: float = np.nan
    mid_change_10s: float = np.nan
    mid_change_30s: float = np.nan
    mid_change_60s: float = np.nan

    # Recovery
    spread_recovery_ms: float = np.nan
    post_quote_rate: float = 0.0

    # Depth
    bid_size_change_pct: float = np.nan
    ask_size_change_pct: float = np.nan

    n_pre_quotes: int = 0
    n_post_quotes: int = 0


class EventTransitionTester:
    """Runs the event-driven state transition experiment."""

    def __init__(self, clickhouse_url: str = CLICKHOUSE_URL):
        self._ch_url = clickhouse_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)
        self._loader = FoundationDiagnosticRunner(clickhouse_url)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("EVENT-DRIVEN STATE TRANSITION EXPERIMENT")
        logger.info("Constants: %s", CONSTANTS_VERSION)
        logger.info("=" * 60)

        symbols, tiers = self._loader._load_universe()
        self._session = aiohttp.ClientSession()

        try:
            # 1. Get extreme + control events
            events = await self._get_events(symbols, tiers)
            n_extreme = sum(1 for e in events if e.is_extreme)
            n_control = len(events) - n_extreme
            logger.info("Events: %d extreme + %d control = %d total",
                        n_extreme, n_control, len(events))

            # 2. Query quotes and compute metrics for each event
            logger.info("Querying post-event quotes (concurrency=%d)...", CH_CONCURRENCY)
            t0 = time.monotonic()
            metrics = await self._process_events(events)
            elapsed = time.monotonic() - t0
            logger.info("Processed %d events in %.1fs (%.1f events/s)",
                        len(metrics), elapsed, len(metrics) / max(elapsed, 0.1))

            # 3. Analyze
            report = self._analyze(metrics, tiers)
            self._write_report(report)
            return report

        finally:
            await self._session.close()
            self._session = None

    # ── Event selection ───────────────────────────────────────────

    async def _get_events(
        self, symbols: List[str], tiers: Dict[str, str]
    ) -> List[EventContext]:
        """Get extreme (top 5%) and control (40-60th pct) events from buckets."""
        query = """
        SELECT symbol, bucket_date, bucket_end_ns, flow_imbalance,
               effective_spread_bps, close_price, classification_confidence
        FROM polygon_data.microstructure_buckets
        ORDER BY symbol, bucket_date, bucket_id
        FORMAT TSVWithNames
        """
        text = await self._ch_query(query)
        lines = text.strip().split("\n")
        header = lines[0].split("\t")
        col = {n: i for i, n in enumerate(header)}

        # Parse all buckets
        by_symbol: Dict[str, List[dict]] = {s: [] for s in symbols}
        for line in lines[1:]:
            f = line.split("\t")
            sym = f[col["symbol"]]
            if sym not in by_symbol:
                continue
            by_symbol[sym].append({
                "date": f[col["bucket_date"]],
                "end_ns": int(f[col["bucket_end_ns"]]),
                "imb": float(f[col["flow_imbalance"]]),
                "spread": float(f[col["effective_spread_bps"]]),
                "close": float(f[col["close_price"]]),
                "conf": float(f[col["classification_confidence"]]),
            })

        events: List[EventContext] = []

        for sym in symbols:
            buckets = by_symbol[sym]
            if not buckets:
                continue

            abs_imbs = np.array([abs(b["imb"]) for b in buckets])
            extreme_thresh = np.percentile(abs_imbs, EXTREME_PERCENTILE)
            ctrl_lo = np.percentile(abs_imbs, CONTROL_RANGE[0])
            ctrl_hi = np.percentile(abs_imbs, CONTROL_RANGE[1])

            extreme_idx = [i for i, b in enumerate(buckets) if abs(b["imb"]) >= extreme_thresh]
            control_idx = [i for i, b in enumerate(buckets) if ctrl_lo <= abs(b["imb"]) <= ctrl_hi]

            rng = np.random.RandomState(42)
            n_sample = min(SAMPLE_PER_SYMBOL, len(extreme_idx))
            sampled_extreme = rng.choice(extreme_idx, size=n_sample, replace=False)

            n_ctrl = min(SAMPLE_PER_SYMBOL, len(control_idx))
            sampled_control = rng.choice(control_idx, size=n_ctrl, replace=False)

            tier = tiers[sym]
            for idx in sampled_extreme:
                b = buckets[idx]
                events.append(EventContext(
                    symbol=sym, tier=tier, bucket_date=b["date"],
                    bucket_end_ns=b["end_ns"], flow_imbalance=b["imb"],
                    effective_spread_bps=b["spread"], close_price=b["close"],
                    classification_confidence=b["conf"], is_extreme=True,
                ))
            for idx in sampled_control:
                b = buckets[idx]
                events.append(EventContext(
                    symbol=sym, tier=tier, bucket_date=b["date"],
                    bucket_end_ns=b["end_ns"], flow_imbalance=b["imb"],
                    effective_spread_bps=b["spread"], close_price=b["close"],
                    classification_confidence=b["conf"], is_extreme=False,
                ))

            logger.info("%s: %d extreme, %d control sampled (threshold=%.3f)",
                        sym, len(sampled_extreme), len(sampled_control), extreme_thresh)

        return events

    # ── Quote processing ──────────────────────────────────────────

    async def _process_events(self, events: List[EventContext]) -> List[TransitionMetrics]:
        """Query post-event quotes and compute metrics for each event."""
        tasks = [self._process_single(e) for e in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        metrics = []
        errors = 0
        for r in results:
            if isinstance(r, Exception):
                errors += 1
            elif r is not None:
                metrics.append(r)

        if errors:
            logger.warning("%d events failed to process", errors)
        return metrics

    async def _process_single(self, event: EventContext) -> Optional[TransitionMetrics]:
        """Query quotes around one event and compute transition metrics."""
        async with self._sem:
            query = f"""
            SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
            FROM polygon_data.microstructure_quotes
            WHERE symbol = '{event.symbol}'
              AND ingestion_date = '{event.bucket_date}'
              AND sip_timestamp >= {event.bucket_end_ns - PRE_WINDOW_NS}
              AND sip_timestamp <= {event.bucket_end_ns + POST_WINDOW_NS}
            ORDER BY sip_timestamp ASC
            FORMAT TSVWithNames
            """
            try:
                text = await self._ch_query(query)
            except Exception as e:
                logger.debug("Query failed for %s %s: %s", event.symbol, event.bucket_date, e)
                return None

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return None

        # Parse quotes
        n_quotes = len(lines) - 1
        ts = np.empty(n_quotes, dtype=np.int64)
        bid = np.empty(n_quotes, dtype=np.float64)
        ask = np.empty(n_quotes, dtype=np.float64)
        bid_sz = np.empty(n_quotes, dtype=np.float64)
        ask_sz = np.empty(n_quotes, dtype=np.float64)

        for i, line in enumerate(lines[1:]):
            parts = line.split("\t")
            ts[i] = int(parts[0])
            bid[i] = float(parts[1])
            ask[i] = float(parts[2])
            bid_sz[i] = float(parts[3])
            ask_sz[i] = float(parts[4])

        # Filter invalid quotes
        valid = (bid > 0) & (ask > 0) & (ask >= bid)
        if np.sum(valid) < 5:
            return None
        ts = ts[valid]
        bid = bid[valid]
        ask = ask[valid]
        bid_sz = bid_sz[valid]
        ask_sz = ask_sz[valid]

        # Compute derived
        mid = (bid + ask) / 2.0
        spread = (ask - bid) / mid * 10000.0  # bps

        # Split into pre/post
        event_ns = event.bucket_end_ns
        pre_mask = ts < event_ns
        post_mask = ts >= event_ns

        m = TransitionMetrics(
            symbol=event.symbol, tier=event.tier,
            is_extreme=event.is_extreme,
            event_imbalance=event.flow_imbalance,
            event_spread_bps=event.effective_spread_bps,
        )
        m.n_pre_quotes = int(np.sum(pre_mask))
        m.n_post_quotes = int(np.sum(post_mask))

        # Pre-event baseline
        if m.n_pre_quotes >= 3:
            pre_ts = ts[pre_mask]
            pre_spread = spread[pre_mask]
            pre_mid = mid[pre_mask]
            pre_bid_sz = bid_sz[pre_mask]
            pre_ask_sz = ask_sz[pre_mask]

            m.pre_spread_bps = float(np.median(pre_spread[-min(50, len(pre_spread)):]))
            m.pre_midpoint = float(pre_mid[-1])
            duration_s = (pre_ts[-1] - pre_ts[0]) / 1e9
            m.pre_quote_rate = len(pre_ts) / max(duration_s, 0.001)
            m.pre_bid_size = float(np.median(pre_bid_sz[-min(50, len(pre_bid_sz)):]))
            m.pre_ask_size = float(np.median(pre_ask_sz[-min(50, len(pre_ask_sz)):]))

        if m.n_post_quotes < 3:
            return m

        post_ts = ts[post_mask]
        post_spread = spread[post_mask]
        post_mid = mid[post_mask]
        post_bid_sz = bid_sz[post_mask]
        post_ask_sz = ask_sz[post_mask]

        # Post-event quote rate
        post_duration_s = (post_ts[-1] - post_ts[0]) / 1e9
        m.post_quote_rate = len(post_ts) / max(post_duration_s, 0.001)

        # Spread at measurement points
        seconds_after = (post_ts - event_ns) / 1e9
        for sec, attr in zip(MEASUREMENT_SECONDS,
                             ["spread_1s", "spread_5s", "spread_10s", "spread_30s", "spread_60s"]):
            mask = (seconds_after >= sec - 0.5) & (seconds_after <= sec + 0.5)
            if np.any(mask):
                setattr(m, attr, float(np.median(post_spread[mask])))

        # Midpoint change at measurement points (directional, in bps)
        ref_mid = m.pre_midpoint if m.pre_midpoint > 0 else post_mid[0]
        for sec, attr in zip(MEASUREMENT_SECONDS,
                             ["mid_change_1s", "mid_change_5s", "mid_change_10s",
                              "mid_change_30s", "mid_change_60s"]):
            mask = (seconds_after >= sec - 0.5) & (seconds_after <= sec + 0.5)
            if np.any(mask) and ref_mid > 0:
                mid_at = float(np.median(post_mid[mask]))
                setattr(m, attr, (mid_at - ref_mid) / ref_mid * 10000)

        # Spread recovery time: how long until spread returns to pre-event level
        if m.pre_spread_bps > 0 and len(post_spread) > 0:
            recovered = post_spread <= m.pre_spread_bps * 1.05
            if np.any(recovered):
                first_recover_idx = np.argmax(recovered)
                m.spread_recovery_ms = float((post_ts[first_recover_idx] - event_ns) / 1e6)
            else:
                m.spread_recovery_ms = 60000.0

        # Depth changes
        if m.pre_bid_size > 0 and len(post_bid_sz) > 0:
            # Use quotes 1-5 seconds after event
            depth_mask = (seconds_after >= 1) & (seconds_after <= 5)
            if np.any(depth_mask):
                m.bid_size_change_pct = float(
                    (np.median(post_bid_sz[depth_mask]) - m.pre_bid_size) / m.pre_bid_size * 100
                )
                m.ask_size_change_pct = float(
                    (np.median(post_ask_sz[depth_mask]) - m.pre_ask_size) / m.pre_ask_size * 100
                )

        return m

    # ── Analysis ──────────────────────────────────────────────────

    def _analyze(self, metrics: List[TransitionMetrics], tiers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze transition patterns: extreme vs control."""

        extreme = [m for m in metrics if m.is_extreme and m.n_post_quotes >= 3]
        control = [m for m in metrics if not m.is_extreme and m.n_post_quotes >= 3]

        logger.info("Analyzable: %d extreme, %d control", len(extreme), len(control))

        report: Dict[str, Any] = {
            "experiment": "event_driven_state_transition",
            "constants_version": CONSTANTS_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "n_extreme": len(extreme),
            "n_control": len(control),
            "gates": [],
            "spread_analysis": {},
            "midpoint_analysis": {},
            "recovery_analysis": {},
            "depth_analysis": {},
            "per_symbol": {},
            "per_tier": {},
            "decision": "",
            "detail": "",
        }

        # ── G1: Spread widening after extreme events ──────────

        def _extract(events, attr):
            return np.array([getattr(m, attr) for m in events if np.isfinite(getattr(m, attr))])

        spread_analysis = {}
        for sec, attr in zip(MEASUREMENT_SECONDS,
                             ["spread_1s", "spread_5s", "spread_10s", "spread_30s", "spread_60s"]):
            ext_vals = _extract(extreme, attr)
            ctrl_vals = _extract(control, attr)
            ext_pre = _extract(extreme, "pre_spread_bps")
            ctrl_pre = _extract(control, "pre_spread_bps")

            ext_widening = ext_vals - ext_pre[:len(ext_vals)] if len(ext_pre) >= len(ext_vals) else ext_vals
            ctrl_widening = ctrl_vals - ctrl_pre[:len(ctrl_vals)] if len(ctrl_pre) >= len(ctrl_vals) else ctrl_vals

            if len(ext_widening) > 10 and len(ctrl_widening) > 10:
                t_stat, p_val = sp_stats.ttest_ind(ext_widening, ctrl_widening, equal_var=False)
                spread_analysis[f"{sec}s"] = {
                    "extreme_mean": float(np.mean(ext_widening)),
                    "control_mean": float(np.mean(ctrl_widening)),
                    "difference": float(np.mean(ext_widening) - np.mean(ctrl_widening)),
                    "t_stat": float(t_stat),
                    "p_value": float(p_val),
                    "extreme_n": len(ext_widening),
                    "control_n": len(ctrl_widening),
                }

        report["spread_analysis"] = spread_analysis
        g1_pass = any(
            s.get("p_value", 1) < 0.05 and s.get("difference", 0) > 0.5
            for s in spread_analysis.values()
        )
        report["gates"].append({
            "id": "G1", "name": "Spread widens after extreme imbalance",
            "result": "PASS" if g1_pass else "FAIL",
            "detail": f"Significant widening at: {[k for k, v in spread_analysis.items() if v.get('p_value', 1) < 0.05]}",
        })
        logger.info("G1 Spread widening: %s", "PASS" if g1_pass else "FAIL")
        for sec, data in spread_analysis.items():
            logger.info("  %s: ext=%.2f, ctrl=%.2f, diff=%.2f, t=%.2f, p=%.4f",
                        sec, data["extreme_mean"], data["control_mean"],
                        data["difference"], data["t_stat"], data["p_value"])

        # ── G2: Midpoint trajectory is directionally biased ───

        mid_analysis = {}
        for sec, attr in zip(MEASUREMENT_SECONDS,
                             ["mid_change_1s", "mid_change_5s", "mid_change_10s",
                              "mid_change_30s", "mid_change_60s"]):
            ext_mid = _extract(extreme, attr)
            ext_imb = np.array([m.event_imbalance for m in extreme
                                if np.isfinite(getattr(m, attr))])

            if len(ext_mid) > 20 and len(ext_imb) == len(ext_mid):
                # Correlation: does imbalance direction predict midpoint change direction?
                corr, p_corr = sp_stats.pearsonr(ext_imb, ext_mid)

                # Reversal check: is midpoint moving AGAINST imbalance?
                reversal_return = -np.sign(ext_imb) * ext_mid
                mean_rev = float(np.mean(reversal_return))
                hit_rate = float(np.mean(reversal_return > 0))

                mid_analysis[f"{sec}s"] = {
                    "corr_imb_mid": float(corr),
                    "p_value": float(p_corr),
                    "mean_reversal_bps": mean_rev,
                    "reversal_hit_rate": hit_rate,
                    "n": len(ext_mid),
                }

        report["midpoint_analysis"] = mid_analysis
        g2_pass = any(
            abs(m.get("corr_imb_mid", 0)) > 0.05 and m.get("p_value", 1) < 0.05
            for m in mid_analysis.values()
        )
        report["gates"].append({
            "id": "G2", "name": "Midpoint trajectory is directionally biased",
            "result": "PASS" if g2_pass else "FAIL",
            "detail": f"Significant correlation at: {[k for k, v in mid_analysis.items() if abs(v.get('corr_imb_mid', 0)) > 0.05 and v.get('p_value', 1) < 0.05]}",
        })
        logger.info("G2 Midpoint trajectory: %s", "PASS" if g2_pass else "FAIL")
        for sec, data in mid_analysis.items():
            logger.info("  %s: corr=%.4f (p=%.4f), rev_mean=%.2f bps, rev_hit=%.1f%%",
                        sec, data["corr_imb_mid"], data["p_value"],
                        data["mean_reversal_bps"], data["reversal_hit_rate"] * 100)

        # ── G3: Spread recovery is predictable ────────────────

        ext_recovery = np.array([m.spread_recovery_ms for m in extreme if np.isfinite(m.spread_recovery_ms)])
        ext_abs_imb = np.array([abs(m.event_imbalance) for m in extreme if np.isfinite(m.spread_recovery_ms)])
        ctrl_recovery = np.array([m.spread_recovery_ms for m in control if np.isfinite(m.spread_recovery_ms)])

        recovery_analysis = {}
        if len(ext_recovery) > 20:
            recovery_analysis["extreme_median_ms"] = float(np.median(ext_recovery))
            recovery_analysis["extreme_mean_ms"] = float(np.mean(ext_recovery))
            recovery_analysis["extreme_p10_ms"] = float(np.percentile(ext_recovery, 10))
            recovery_analysis["extreme_p90_ms"] = float(np.percentile(ext_recovery, 90))

        if len(ctrl_recovery) > 20:
            recovery_analysis["control_median_ms"] = float(np.median(ctrl_recovery))
            recovery_analysis["control_mean_ms"] = float(np.mean(ctrl_recovery))

        if len(ext_recovery) > 20 and len(ext_abs_imb) == len(ext_recovery):
            corr_r, p_r = sp_stats.pearsonr(ext_abs_imb, ext_recovery)
            recovery_analysis["corr_imb_recovery"] = float(corr_r)
            recovery_analysis["p_value"] = float(p_r)

        report["recovery_analysis"] = recovery_analysis

        g3_pass = abs(recovery_analysis.get("corr_imb_recovery", 0)) > 0.10 and recovery_analysis.get("p_value", 1) < 0.05
        report["gates"].append({
            "id": "G3", "name": "Spread recovery predictable from imbalance",
            "result": "PASS" if g3_pass else "FAIL",
            "detail": f"corr(|imb|, recovery_ms) = {recovery_analysis.get('corr_imb_recovery', 0):.4f}, "
                      f"p = {recovery_analysis.get('p_value', 1):.4f}",
        })
        logger.info("G3 Recovery predictability: %s — corr=%.4f, p=%.4f",
                     "PASS" if g3_pass else "FAIL",
                     recovery_analysis.get("corr_imb_recovery", 0),
                     recovery_analysis.get("p_value", 1))

        # ── G4: Depth asymmetry after extreme events ──────────

        ext_bid_chg = _extract(extreme, "bid_size_change_pct")
        ext_ask_chg = _extract(extreme, "ask_size_change_pct")
        ctrl_bid_chg = _extract(control, "bid_size_change_pct")
        ctrl_ask_chg = _extract(control, "ask_size_change_pct")

        depth_analysis = {}
        if len(ext_bid_chg) > 20:
            depth_analysis["extreme_bid_change_pct"] = float(np.mean(ext_bid_chg))
            depth_analysis["extreme_ask_change_pct"] = float(np.mean(ext_ask_chg))
        if len(ctrl_bid_chg) > 20:
            depth_analysis["control_bid_change_pct"] = float(np.mean(ctrl_bid_chg))
            depth_analysis["control_ask_change_pct"] = float(np.mean(ctrl_ask_chg))

        # Check if depth depletion is asymmetric (imbalance-dependent)
        ext_imb_for_depth = np.array([m.event_imbalance for m in extreme if np.isfinite(m.bid_size_change_pct)])
        if len(ext_imb_for_depth) > 20 and len(ext_bid_chg) == len(ext_imb_for_depth):
            # For positive imbalance (buying pressure), expect ask side depleted more
            depth_asymmetry = np.where(ext_imb_for_depth > 0, ext_ask_chg, ext_bid_chg)
            depth_analysis["mean_depleted_side_change_pct"] = float(np.mean(depth_asymmetry))
            t_dep, p_dep = sp_stats.ttest_1samp(depth_asymmetry, 0)
            depth_analysis["depletion_t_stat"] = float(t_dep)
            depth_analysis["depletion_p_value"] = float(p_dep)

        report["depth_analysis"] = depth_analysis

        g4_pass = depth_analysis.get("depletion_p_value", 1) < 0.05 and depth_analysis.get("mean_depleted_side_change_pct", 0) < -5
        report["gates"].append({
            "id": "G4", "name": "Depth asymmetry after extreme imbalance",
            "result": "PASS" if g4_pass else "FAIL",
            "detail": f"Depleted side change: {depth_analysis.get('mean_depleted_side_change_pct', 0):.1f}%, "
                      f"p = {depth_analysis.get('depletion_p_value', 1):.4f}",
        })
        logger.info("G4 Depth asymmetry: %s", "PASS" if g4_pass else "FAIL")

        # ── Per-symbol and per-tier breakdown ─────────────────

        for sym in sorted(set(m.symbol for m in extreme)):
            sym_ext = [m for m in extreme if m.symbol == sym]
            sym_ctrl = [m for m in control if m.symbol == sym]
            sym_data = {
                "n_extreme": len(sym_ext),
                "n_control": len(sym_ctrl),
            }
            if sym_ext:
                spr_5 = [m.spread_5s for m in sym_ext if np.isfinite(m.spread_5s)]
                pre_spr = [m.pre_spread_bps for m in sym_ext if np.isfinite(m.spread_5s)]
                if spr_5 and pre_spr:
                    sym_data["spread_widening_5s"] = float(np.mean(spr_5) - np.mean(pre_spr))
                mid_5 = [m for m in sym_ext if np.isfinite(m.mid_change_5s)]
                if mid_5:
                    rev_ret = [-np.sign(m.event_imbalance) * m.mid_change_5s for m in mid_5]
                    sym_data["reversal_5s_bps"] = float(np.mean(rev_ret))
                    sym_data["reversal_5s_hit"] = float(np.mean([r > 0 for r in rev_ret]))
                rec = [m.spread_recovery_ms for m in sym_ext if np.isfinite(m.spread_recovery_ms)]
                if rec:
                    sym_data["median_recovery_ms"] = float(np.median(rec))

            report["per_symbol"][sym] = sym_data

        for tier in ["A", "B", "C"]:
            tier_ext = [m for m in extreme if m.tier == tier]
            if tier_ext:
                spr = [m.spread_5s - m.pre_spread_bps for m in tier_ext
                       if np.isfinite(m.spread_5s) and m.pre_spread_bps > 0]
                rev = [-np.sign(m.event_imbalance) * m.mid_change_5s for m in tier_ext
                       if np.isfinite(m.mid_change_5s)]
                report["per_tier"][tier] = {
                    "n": len(tier_ext),
                    "mean_spread_widening_5s": float(np.mean(spr)) if spr else 0,
                    "mean_reversal_5s_bps": float(np.mean(rev)) if rev else 0,
                    "reversal_hit_5s": float(np.mean([r > 0 for r in rev])) if rev else 0,
                }

        # ── Decision ──────────────────────────────────────────

        n_pass = sum(1 for g in report["gates"] if g["result"] == "PASS")
        if n_pass >= 3:
            report["decision"] = "PROCEED"
            report["detail"] = (
                f"{n_pass}/4 gates passed. State transitions are detectable and "
                "potentially exploitable. Proceed to event-driven strategy design."
            )
        elif n_pass >= 2:
            report["decision"] = "INVESTIGATE"
            report["detail"] = (
                f"{n_pass}/4 gates passed. Partial signal detected. "
                "Targeted investigation of passing dimensions warranted."
            )
        else:
            report["decision"] = "TERMINATE"
            report["detail"] = (
                f"Only {n_pass}/4 gates passed. Microstructure transitions at this "
                "resolution do not contain actionable information. "
                "SIP-derived data is conclusively insufficient."
            )

        logger.info("\nDECISION: %s — %s", report["decision"], report["detail"])
        return report

    # ── ClickHouse query ──────────────────────────────────────

    async def _ch_query(self, query: str) -> str:
        assert self._session is not None
        async with self._session.post(self._ch_url, data=query.encode()) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ClickHouse {resp.status}: {body[:300]}")
            return await resp.text()

    # ── Report ────────────────────────────────────────────────

    def _write_report(self, report: Dict[str, Any]) -> None:
        root = Path(__file__).resolve().parents[3]
        out_dir = root / "results" / "foundation_diagnostic"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "event_transition_report.md"

        lines = [
            "# Event-Driven State Transition Experiment",
            "",
            f"**Constants**: {report['constants_version']}",
            f"**Timestamp**: {report['timestamp']}",
            f"**Events**: {report['n_extreme']} extreme + {report['n_control']} control",
            "",
            f"## Decision: **{report['decision']}**",
            "",
            report["detail"],
            "",
            "---",
            "",
            "## Gate Results",
            "",
            "| Gate | Name | Result | Detail |",
            "|------|------|--------|--------|",
        ]
        for g in report["gates"]:
            lines.append(f"| {g['id']} | {g['name']} | **{g['result']}** | {g['detail'][:100]} |")

        lines.extend(["", "---", "", "## Spread Trajectory (Extreme vs Control)", ""])
        if report["spread_analysis"]:
            lines.append("| Time | Extreme Δ (bps) | Control Δ (bps) | Difference | t-stat | p-value |")
            lines.append("|------|-----------------|-----------------|------------|--------|---------|")
            for sec, data in sorted(report["spread_analysis"].items()):
                lines.append(
                    f"| {sec} | {data['extreme_mean']:.2f} | {data['control_mean']:.2f} | "
                    f"{data['difference']:.2f} | {data['t_stat']:.2f} | {data['p_value']:.4f} |"
                )

        lines.extend(["", "## Midpoint Trajectory After Extreme Events", ""])
        if report["midpoint_analysis"]:
            lines.append("| Time | Corr(imb, mid) | p-value | Rev Mean (bps) | Rev Hit Rate |")
            lines.append("|------|---------------|---------|----------------|--------------|")
            for sec, data in sorted(report["midpoint_analysis"].items()):
                lines.append(
                    f"| {sec} | {data['corr_imb_mid']:.4f} | {data['p_value']:.4f} | "
                    f"{data['mean_reversal_bps']:.2f} | {data['reversal_hit_rate']:.1%} |"
                )

        lines.extend(["", "## Spread Recovery", ""])
        ra = report["recovery_analysis"]
        if ra:
            for k, v in ra.items():
                lines.append(f"- **{k}**: {v:.2f}" if isinstance(v, float) else f"- **{k}**: {v}")

        lines.extend(["", "## Depth Analysis", ""])
        da = report["depth_analysis"]
        if da:
            for k, v in da.items():
                lines.append(f"- **{k}**: {v:.2f}" if isinstance(v, float) else f"- **{k}**: {v}")

        lines.extend(["", "---", "", "## Per-Symbol Breakdown", ""])
        lines.append("| Symbol | Tier | Spread Δ 5s | Rev 5s (bps) | Rev Hit | Recovery (ms) |")
        lines.append("|--------|------|-------------|--------------|---------|---------------|")
        for sym, data in sorted(report.get("per_symbol", {}).items()):
            lines.append(
                f"| {sym} | {report.get('per_symbol', {}).get(sym, {}).get('tier', '?')} | "
                f"{data.get('spread_widening_5s', 0):.2f} | "
                f"{data.get('reversal_5s_bps', 0):.2f} | "
                f"{data.get('reversal_5s_hit', 0):.1%} | "
                f"{data.get('median_recovery_ms', 0):.0f} |"
            )

        lines.extend(["", "## Per-Tier Breakdown", ""])
        lines.append("| Tier | N | Spread Δ 5s | Rev 5s (bps) | Rev Hit 5s |")
        lines.append("|------|---|-------------|--------------|------------|")
        for tier, data in sorted(report.get("per_tier", {}).items()):
            lines.append(
                f"| {tier} | {data['n']} | {data['mean_spread_widening_5s']:.2f} | "
                f"{data['mean_reversal_5s_bps']:.2f} | {data['reversal_hit_5s']:.1%} |"
            )

        path.write_text("\n".join(lines))
        logger.info("Report: %s", path)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    tester = EventTransitionTester()
    report = await tester.run()

    print(f"\n{'='*60}")
    print(f"EVENT TRANSITION DECISION: {report['decision']}")
    print(f"{'='*60}")
    print(report["detail"])
    print(f"\nGates: {sum(1 for g in report['gates'] if g['result'] == 'PASS')}/4 passed")
    for g in report["gates"]:
        print(f"  {g['id']} {g['name']}: {g['result']}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
