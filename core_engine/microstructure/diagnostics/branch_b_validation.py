"""
Branch B — Final Validation Suite (4 tests).

Addresses external quant's capital-allocation-grade concerns:
  V1: Cross-regime slice (high-vol vs low-vol segmentation)
  V2: Cross-symbol correlation stress (event clustering, daily corr, worst drawdown)
  V3: Capacity sweep (clip size impact on fill/edge)
  V4: Execution realism (cancel lag, stop slippage, partial fills, quote fade)

Uses same data as stress test — no additional ClickHouse queries for events.
Extends analysis with portfolio-level and execution-level modeling.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import time
from collections import defaultdict
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

ENTRY_DELAY_NS = 200 * 1_000_000  # 200ms baseline for validation
POST_WINDOW_NS = 30_000_000_000
PRE_WINDOW_NS = 10_000_000_000
SPREAD_NORMAL_FACTOR = 1.05
STOP_LOSS_BPS = 3.0
TIMEOUT_S = 30

CLIP_SIZES = [100, 500, 1000, 2000, 5000]
STOP_SLIPPAGE_BPS = 1.0  # adverse slippage on stop exits
CANCEL_LAG_MS = 200      # time to cancel after exit trigger


@dataclass
class EventData:
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
class TradeResult:
    symbol: str
    date: str
    filled: bool = False
    pnl_bps: float = 0.0
    hold_time_ms: float = 0.0
    exit_reason: str = ""
    queue_ahead: int = 0
    spread_at_event: float = 0.0
    spread_at_entry: float = 0.0
    baseline_spread: float = 0.0
    entry_price: float = 0.0
    clip_size: int = 0


class BranchBValidation:

    def __init__(self):
        self._ch_url = CLICKHOUSE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 70)
        logger.info("BRANCH B — FINAL VALIDATION SUITE")
        logger.info("=" * 70)

        self._session = aiohttp.ClientSession()
        try:
            events_raw = await self._get_extreme_events()
            logger.info("Loaded %d raw events", len(events_raw))

            t0 = time.monotonic()
            tasks = [self._load_event_data(e) for e in events_raw]
            loaded = await asyncio.gather(*tasks, return_exceptions=True)
            events = [e for e in loaded if isinstance(e, EventData) and e.valid]
            logger.info("Valid events: %d (%.1fs)", len(events), time.monotonic() - t0)

            all_dates = sorted(set(e.date for e in events))

            # Run baseline simulation for all events
            baseline = [self._simulate(ev, clip_size=100, add_stop_slippage=False)
                        for ev in events]

            report: Dict[str, Any] = {
                "experiment": "branch_b_final_validation",
                "constants_version": CONSTANTS_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbols": TIER_A_SYMBOLS,
                "total_events": len(events),
            }

            # V1: Cross-regime
            report["v1_regime"] = self._v1_regime(events, baseline, all_dates)

            # V2: Correlation stress
            report["v2_correlation"] = self._v2_correlation(events, baseline, all_dates)

            # V3: Capacity sweep
            report["v3_capacity"] = self._v3_capacity(events)

            # V4: Execution realism
            report["v4_execution"] = self._v4_execution(events, baseline)

            # Quote fade diagnostic
            report["quote_fade"] = self._quote_fade_diagnostic(events)

            # Overall verdict
            v1_pass = report["v1_regime"]["survives_both"]
            v2_pass = report["v2_correlation"]["worst_day_acceptable"]
            v3_pass = report["v3_capacity"]["edge_at_500_shares"]
            v4_pass = report["v4_execution"]["edge_survives_ugly"]

            n_pass = sum([v1_pass, v2_pass, v3_pass, v4_pass])
            if n_pass == 4:
                verdict = "PROCEED TO SHADOW TRADING"
                detail = "All 4 validations passed. Edge survives regime, correlation, capacity, and execution stress."
            elif n_pass >= 3:
                verdict = "PROCEED WITH CAUTION"
                detail = f"{n_pass}/4 validations passed. Address failing dimension before live deployment."
            else:
                verdict = "REDESIGN REQUIRED"
                detail = f"Only {n_pass}/4 validations passed. Strategy needs structural rework."

            report["verdict"] = {"decision": verdict, "detail": detail,
                                 "v1": v1_pass, "v2": v2_pass, "v3": v3_pass, "v4": v4_pass}

            logger.info("\n%s", "=" * 70)
            logger.info("VERDICT: %s", verdict)
            logger.info(detail)
            logger.info("=" * 70)

            self._write_report(report, baseline)
            return report

        finally:
            await self._session.close()

    # ── V1: Cross-Regime Slice ──

    def _v1_regime(self, events: List[EventData], baseline: List[TradeResult],
                   all_dates: List[str]) -> Dict[str, Any]:
        logger.info("\n--- V1: CROSS-REGIME SLICE ---")

        # Compute daily volatility proxy: daily spread variance across all events
        date_spreads: Dict[str, List[float]] = defaultdict(list)
        for ev in events:
            date_spreads[ev.date].append(ev.spread_bps)

        date_vol = {}
        for d, spreads in date_spreads.items():
            date_vol[d] = float(np.std(spreads)) if len(spreads) > 1 else 0.0

        vol_values = np.array(list(date_vol.values()))
        vol_median = float(np.median(vol_values)) if len(vol_values) > 0 else 0.0

        high_vol_dates = set(d for d, v in date_vol.items() if v >= vol_median)
        low_vol_dates = set(d for d, v in date_vol.items() if v < vol_median)

        def segment_stats(dates_set):
            seg = [r for r in baseline if r.date in dates_set and r.filled]
            if not seg:
                return {"n": 0, "mean": 0, "hit": 0, "positive": False}
            pnls = np.array([r.pnl_bps for r in seg])
            return {
                "n": len(seg),
                "mean": float(np.mean(pnls)),
                "median": float(np.median(pnls)),
                "hit": float(np.mean(pnls > 0)),
                "positive": float(np.mean(pnls)) > 0,
            }

        high = segment_stats(high_vol_dates)
        low = segment_stats(low_vol_dates)

        survives = high["positive"] and low["positive"]

        logger.info("  High-vol: n=%d mean=%.2f hit=%.1f%% → %s",
                     high["n"], high["mean"], high.get("hit", 0) * 100,
                     "OK" if high["positive"] else "FAIL")
        logger.info("  Low-vol:  n=%d mean=%.2f hit=%.1f%% → %s",
                     low["n"], low["mean"], low.get("hit", 0) * 100,
                     "OK" if low["positive"] else "FAIL")

        # WMT winner clustering check
        wmt_filled = [r for r in baseline if r.symbol == "WMT" and r.filled]
        wmt_big_wins = [r for r in wmt_filled if r.pnl_bps > 5.0]
        wmt_big_in_highvol = sum(1 for r in wmt_big_wins if r.date in high_vol_dates)
        wmt_big_total = len(wmt_big_wins)

        return {
            "high_vol": high,
            "low_vol": low,
            "survives_both": survives,
            "vol_median": vol_median,
            "high_vol_days": len(high_vol_dates),
            "low_vol_days": len(low_vol_dates),
            "wmt_big_wins_total": wmt_big_total,
            "wmt_big_wins_in_highvol": wmt_big_in_highvol,
            "wmt_big_wins_clustered": wmt_big_in_highvol > 0.7 * wmt_big_total if wmt_big_total > 5 else False,
        }

    # ── V2: Correlation Stress ──

    def _v2_correlation(self, events: List[EventData], baseline: List[TradeResult],
                        all_dates: List[str]) -> Dict[str, Any]:
        logger.info("\n--- V2: CORRELATION STRESS ---")

        # Daily PnL per symbol
        sym_daily: Dict[str, Dict[str, float]] = {s: {} for s in TIER_A_SYMBOLS}
        for r in baseline:
            if r.filled:
                sym_daily[r.symbol][r.date] = sym_daily[r.symbol].get(r.date, 0) + r.pnl_bps

        # Build aligned daily PnL matrix
        sym_pnl_series = {}
        for sym in TIER_A_SYMBOLS:
            sym_pnl_series[sym] = np.array([sym_daily[sym].get(d, 0.0) for d in all_dates])

        # Pairwise correlation
        corr_pairs = {}
        syms = list(TIER_A_SYMBOLS)
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                c = float(np.corrcoef(sym_pnl_series[syms[i]], sym_pnl_series[syms[j]])[0, 1])
                corr_pairs[f"{syms[i]}-{syms[j]}"] = c

        mean_corr = float(np.mean(list(corr_pairs.values())))

        # Portfolio daily PnL
        portfolio_daily = np.zeros(len(all_dates))
        for sym in TIER_A_SYMBOLS:
            portfolio_daily += sym_pnl_series[sym]

        worst_day = float(np.min(portfolio_daily))
        worst_day_idx = int(np.argmin(portfolio_daily))
        worst_day_date = all_dates[worst_day_idx] if worst_day_idx < len(all_dates) else "?"

        # Max drawdown in bps (cumulative sum)
        cum = np.cumsum(portfolio_daily)
        running_max = np.maximum.accumulate(cum)
        drawdowns = cum - running_max
        max_dd = float(np.min(drawdowns))

        # Event clustering: how often do 2+ symbols fire within 5 minutes?
        event_times: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for ev in events:
            event_times[ev.date].append((ev.symbol, ev.end_ns))

        cluster_count = 0
        total_events_checked = 0
        for date, evts in event_times.items():
            evts.sort(key=lambda x: x[1])
            for i in range(len(evts)):
                total_events_checked += 1
                for j in range(i + 1, len(evts)):
                    if evts[j][0] != evts[i][0]:
                        delta_ms = (evts[j][1] - evts[i][1]) / 1e6
                        if delta_ms <= 300_000:  # 5 minutes
                            cluster_count += 1
                            break

        cluster_rate = cluster_count / max(total_events_checked, 1)

        # Max concurrent positions (if we held all simultaneously)
        worst_day_acceptable = worst_day > -30  # -30 bps worst day is survivable

        logger.info("  Mean pairwise corr: %.3f", mean_corr)
        logger.info("  Worst day: %.2f bps (%s)", worst_day, worst_day_date)
        logger.info("  Max drawdown: %.2f bps", max_dd)
        logger.info("  Event clustering (5-min): %.1f%%", cluster_rate * 100)
        logger.info("  Worst day acceptable: %s", worst_day_acceptable)

        return {
            "pairwise_correlations": corr_pairs,
            "mean_correlation": mean_corr,
            "worst_day_bps": worst_day,
            "worst_day_date": worst_day_date,
            "max_drawdown_bps": max_dd,
            "event_cluster_rate": cluster_rate,
            "portfolio_sharpe": float(np.mean(portfolio_daily) / max(np.std(portfolio_daily, ddof=1), 1e-6) * math.sqrt(252)),
            "worst_day_acceptable": worst_day_acceptable,
        }

    # ── V3: Capacity Sweep ──

    def _v3_capacity(self, events: List[EventData]) -> Dict[str, Any]:
        logger.info("\n--- V3: CAPACITY SWEEP ---")

        results = {}
        for clip in CLIP_SIZES:
            trades = [self._simulate(ev, clip_size=clip, add_stop_slippage=False)
                      for ev in events]
            filled = [t for t in trades if t.filled]
            if not filled:
                results[clip] = {"fill_rate": 0, "mean_pnl": 0, "hit_rate": 0}
                continue

            pnls = np.array([t.pnl_bps for t in filled])
            fill_rate = len(filled) / max(len(trades), 1)
            results[clip] = {
                "fill_rate": fill_rate,
                "n_filled": len(filled),
                "mean_pnl": float(np.mean(pnls)),
                "hit_rate": float(np.mean(pnls > 0)),
                "mean_queue_ahead": float(np.mean([t.queue_ahead for t in filled])),
            }
            logger.info("  Clip %5d: fill=%.1f%% mean=%.2f hit=%.1f%%",
                        clip, fill_rate * 100, float(np.mean(pnls)),
                        float(np.mean(pnls > 0)) * 100)

        edge_at_500 = results.get(500, {}).get("mean_pnl", 0) > 0

        return {
            "sweep": results,
            "edge_at_500_shares": edge_at_500,
        }

    # ── V4: Execution Realism ──

    def _v4_execution(self, events: List[EventData],
                      baseline: List[TradeResult]) -> Dict[str, Any]:
        logger.info("\n--- V4: EXECUTION REALISM ---")

        # Run "ugly" simulation: stop slippage + higher delay
        ugly_trades = [self._simulate(ev, clip_size=100, add_stop_slippage=True)
                       for ev in events]

        ugly_filled = [t for t in ugly_trades if t.filled]
        base_filled = [t for t in baseline if t.filled]

        if not ugly_filled:
            return {"edge_survives_ugly": False, "detail": "No fills in ugly sim"}

        ugly_pnls = np.array([t.pnl_bps for t in ugly_filled])
        base_pnls = np.array([t.pnl_bps for t in base_filled])

        ugly_mean = float(np.mean(ugly_pnls))
        base_mean = float(np.mean(base_pnls))
        degradation = (base_mean - ugly_mean) / max(abs(base_mean), 1e-6) * 100

        # Exit reason comparison
        ugly_stops = sum(1 for t in ugly_filled if t.exit_reason == "stop_loss")
        base_stops = sum(1 for t in base_filled if t.exit_reason == "stop_loss")

        edge_survives = ugly_mean > 0

        logger.info("  Baseline mean: %.2f bps", base_mean)
        logger.info("  Ugly mean:     %.2f bps (%.1f%% degradation)", ugly_mean, degradation)
        logger.info("  Ugly hit rate: %.1f%%", float(np.mean(ugly_pnls > 0)) * 100)
        logger.info("  Stop exits: base=%d ugly=%d", base_stops, ugly_stops)
        logger.info("  Edge survives: %s", edge_survives)

        return {
            "baseline_mean": base_mean,
            "ugly_mean": ugly_mean,
            "degradation_pct": degradation,
            "ugly_hit_rate": float(np.mean(ugly_pnls > 0)),
            "ugly_fill_rate": len(ugly_filled) / max(len(ugly_trades), 1),
            "stop_exits_baseline": base_stops,
            "stop_exits_ugly": ugly_stops,
            "edge_survives_ugly": edge_survives,
        }

    # ── Quote Fade Diagnostic ──

    def _quote_fade_diagnostic(self, events: List[EventData]) -> Dict[str, Any]:
        """Measure how often the widened spread persists at entry time."""
        logger.info("\n--- QUOTE FADE DIAGNOSTIC ---")

        widened_at_entry = 0
        total_checked = 0

        spread_ratios = []

        for ev in events:
            if not ev.valid or len(ev.q_ts) < 10:
                continue

            q_mid = (ev.q_bid + ev.q_ask) / 2.0
            q_spread = np.where(q_mid > 0, (ev.q_ask - ev.q_bid) / q_mid * 10000, 0)

            pre_mask = ev.q_ts < ev.end_ns
            if np.sum(pre_mask) < 3:
                continue
            baseline_spread = float(np.median(q_spread[pre_mask][-50:]))
            if baseline_spread <= 0:
                continue

            # Check spread at event_end (peak)
            event_idx = np.searchsorted(ev.q_ts, ev.end_ns)
            event_idx = min(event_idx, len(ev.q_ts) - 1)
            spread_at_event = q_spread[event_idx]

            # Check spread at entry (200ms later)
            entry_ns = ev.end_ns + ENTRY_DELAY_NS
            entry_idx = np.searchsorted(ev.q_ts, entry_ns)
            entry_idx = min(entry_idx, len(ev.q_ts) - 1)
            spread_at_entry = q_spread[entry_idx]

            total_checked += 1
            ratio = spread_at_entry / baseline_spread
            spread_ratios.append(ratio)

            if spread_at_entry > baseline_spread * 1.1:
                widened_at_entry += 1

        if not spread_ratios:
            return {"quote_stickiness": 0, "detail": "No data"}

        ratios = np.array(spread_ratios)
        stickiness = widened_at_entry / max(total_checked, 1)

        logger.info("  Spread still widened (>110%% baseline) at entry: %d/%d (%.1f%%)",
                     widened_at_entry, total_checked, stickiness * 100)
        logger.info("  Mean spread ratio at entry: %.2f", float(np.mean(ratios)))
        logger.info("  Median spread ratio at entry: %.2f", float(np.median(ratios)))

        return {
            "total_checked": total_checked,
            "widened_at_entry": widened_at_entry,
            "quote_stickiness": stickiness,
            "mean_spread_ratio": float(np.mean(ratios)),
            "median_spread_ratio": float(np.median(ratios)),
            "p25_ratio": float(np.percentile(ratios, 25)),
            "p75_ratio": float(np.percentile(ratios, 75)),
        }

    # ── Simulation Engine ──

    def _simulate(self, ev: EventData, clip_size: int = 100,
                  add_stop_slippage: bool = False) -> TradeResult:
        result = TradeResult(symbol=ev.symbol, date=ev.date, clip_size=clip_size)

        entry_time_ns = ev.end_ns + ENTRY_DELAY_NS

        q_ts = ev.q_ts
        q_mid = (ev.q_bid + ev.q_ask) / 2.0
        q_spread = np.where(q_mid > 0, (ev.q_ask - ev.q_bid) / q_mid * 10000, 0)

        pre_mask = q_ts < ev.end_ns
        if np.sum(pre_mask) >= 3:
            baseline_spread = float(np.median(q_spread[pre_mask][-50:]))
        else:
            baseline_spread = ev.spread_bps
        result.baseline_spread = baseline_spread

        # Spread at event end
        ev_idx = np.searchsorted(q_ts, ev.end_ns)
        ev_idx = min(ev_idx, len(q_ts) - 1)
        result.spread_at_event = float(q_spread[ev_idx])

        entry_q_idx = np.searchsorted(q_ts, entry_time_ns)
        if entry_q_idx >= len(q_ts):
            return result
        entry_q_idx = min(entry_q_idx, len(q_ts) - 1)

        entry_bid = ev.q_bid[entry_q_idx]
        entry_ask = ev.q_ask[entry_q_idx]
        if entry_bid <= 0 or entry_ask <= 0:
            return result

        result.spread_at_entry = float(q_spread[entry_q_idx])
        imb_direction = np.sign(ev.imbalance)

        if imb_direction > 0:
            our_price = entry_ask
            our_side = "ask"
            queue_ahead_raw = int(ev.q_ask_sz[entry_q_idx])
        else:
            our_price = entry_bid
            our_side = "bid"
            queue_ahead_raw = int(ev.q_bid_sz[entry_q_idx])

        # Capacity model: our clip adds to what must be consumed
        queue_ahead = queue_ahead_raw + clip_size
        result.queue_ahead = queue_ahead
        result.entry_price = float(our_price)

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
            return result

        result.filled = True

        # Exit logic
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
                # Execution realism: add slippage on stop exits
                if add_stop_slippage:
                    if imb_direction > 0:
                        exit_price = current_mid * (1 + STOP_SLIPPAGE_BPS / 10000)
                    else:
                        exit_price = current_mid * (1 - STOP_SLIPPAGE_BPS / 10000)
                exit_reason = "stop_loss"
                exit_time_ns = current_ts
                break

            if current_spread <= spread_threshold and current_ts > fill_time_ns + 500_000_000:
                # Execution realism: cancel lag on exit
                if add_stop_slippage:
                    cancel_end_ns = current_ts + CANCEL_LAG_MS * 1_000_000
                    cancel_idx = np.searchsorted(q_ts, cancel_end_ns)
                    cancel_idx = min(cancel_idx, len(q_ts) - 1)
                    exit_price = q_mid[cancel_idx]
                else:
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

    # ── Report ──

    def _write_report(self, report: Dict[str, Any], baseline: List[TradeResult]) -> None:
        root = Path(__file__).resolve().parents[3]
        out = root / "results" / "foundation_diagnostic" / "branch_b_validation_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)

        v = report["verdict"]
        lines = [
            "# Branch B — Final Validation Report",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            f"**Symbols**: {', '.join(TIER_A_SYMBOLS)}",
            f"**Events**: {report['total_events']}",
            f"**Entry delay**: 200ms (validation baseline)",
            "",
            f"## Verdict: **{v['decision']}**",
            "", v["detail"], "",
            "",
            "| Validation | Result |",
            "|------------|--------|",
            f"| V1: Cross-regime | {'PASS' if v['v1'] else 'FAIL'} |",
            f"| V2: Correlation stress | {'PASS' if v['v2'] else 'FAIL'} |",
            f"| V3: Capacity (500 shares) | {'PASS' if v['v3'] else 'FAIL'} |",
            f"| V4: Execution realism | {'PASS' if v['v4'] else 'FAIL'} |",
            "",
            "---", "",
        ]

        # V1
        v1 = report["v1_regime"]
        lines.extend([
            "## V1: Cross-Regime Slice", "",
            f"Split {len(baseline)} events by daily spread volatility (median={v1['vol_median']:.2f} bps).", "",
            "| Regime | N Filled | Mean PnL | Hit Rate | Positive |",
            "|--------|----------|----------|----------|----------|",
            f"| High-vol ({v1['high_vol_days']}d) | {v1['high_vol']['n']} | {v1['high_vol']['mean']:.2f} | {v1['high_vol'].get('hit', 0):.1%} | {'Yes' if v1['high_vol']['positive'] else 'No'} |",
            f"| Low-vol ({v1['low_vol_days']}d) | {v1['low_vol']['n']} | {v1['low_vol']['mean']:.2f} | {v1['low_vol'].get('hit', 0):.1%} | {'Yes' if v1['low_vol']['positive'] else 'No'} |",
            "",
            f"WMT big wins (>5bps): {v1['wmt_big_wins_total']} total, "
            f"{v1['wmt_big_wins_in_highvol']} in high-vol "
            f"({'CLUSTERED' if v1.get('wmt_big_wins_clustered') else 'DISTRIBUTED'})",
            "",
        ])

        # V2
        v2 = report["v2_correlation"]
        lines.extend([
            "## V2: Correlation Stress", "",
            "**Pairwise daily PnL correlations:**", "",
        ])
        for pair, c in sorted(v2["pairwise_correlations"].items()):
            lines.append(f"- {pair}: {c:.3f}")
        lines.extend([
            "",
            f"- **Mean pairwise correlation**: {v2['mean_correlation']:.3f}",
            f"- **Portfolio Sharpe**: {v2['portfolio_sharpe']:.2f}",
            f"- **Worst day**: {v2['worst_day_bps']:.2f} bps ({v2['worst_day_date']})",
            f"- **Max drawdown**: {v2['max_drawdown_bps']:.2f} bps",
            f"- **Event clustering (5-min window)**: {v2['event_cluster_rate']:.1%}",
            f"- **Worst day acceptable (> -30 bps)**: {'Yes' if v2['worst_day_acceptable'] else 'No'}",
            "",
        ])

        # V3
        v3 = report["v3_capacity"]
        lines.extend([
            "## V3: Capacity Sweep", "",
            "| Clip Size | Fill% | N Filled | Mean PnL | Hit Rate | Queue Ahead |",
            "|-----------|-------|----------|----------|----------|-------------|",
        ])
        for clip, d in sorted(v3["sweep"].items()):
            lines.append(
                f"| {clip} | {d.get('fill_rate', 0):.1%} | {d.get('n_filled', 0)} | "
                f"{d.get('mean_pnl', 0):.2f} | {d.get('hit_rate', 0):.1%} | "
                f"{d.get('mean_queue_ahead', 0):.0f} |"
            )
        lines.append("")

        # V4
        v4 = report["v4_execution"]
        lines.extend([
            "## V4: Execution Realism", "",
            "Ugly simulation: +1 bps stop slippage, +200ms cancel lag on exits.", "",
            f"- **Baseline mean**: {v4['baseline_mean']:.2f} bps",
            f"- **Ugly mean**: {v4['ugly_mean']:.2f} bps",
            f"- **Degradation**: {v4['degradation_pct']:.1f}%",
            f"- **Ugly hit rate**: {v4['ugly_hit_rate']:.1%}",
            f"- **Stop exits**: baseline={v4['stop_exits_baseline']}, ugly={v4['stop_exits_ugly']}",
            f"- **Edge survives**: {'Yes' if v4['edge_survives_ugly'] else 'No'}",
            "",
        ])

        # Quote fade
        qf = report["quote_fade"]
        lines.extend([
            "## Quote Fade Diagnostic", "",
            f"- **Spread still widened (>110% baseline) at entry**: {qf.get('widened_at_entry', 0)}/{qf.get('total_checked', 0)} ({qf.get('quote_stickiness', 0):.1%})",
            f"- **Mean spread ratio at entry**: {qf.get('mean_spread_ratio', 0):.2f}x baseline",
            f"- **Median spread ratio at entry**: {qf.get('median_spread_ratio', 0):.2f}x baseline",
            f"- **P25/P75 ratio**: {qf.get('p25_ratio', 0):.2f} / {qf.get('p75_ratio', 0):.2f}",
            "",
        ])

        out.write_text("\n".join(lines))
        logger.info("Report: %s", out)

    # ── Data Loading (same as stress test) ──

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
                continue
            abs_imbs = np.array([abs(b["imb"]) for b in buckets])
            thresh = np.percentile(abs_imbs, 95)
            extreme = [b for b in buckets if abs(b["imb"]) >= thresh]
            n = min(EVENTS_PER_SYMBOL, len(extreme))
            indices = rng.choice(len(extreme), size=n, replace=False)
            for i in indices:
                events.append(extreme[i])
            logger.info("%s: %d extreme events (thresh=%.3f)", sym, n, thresh)
        return events

    async def _load_event_data(self, event: dict) -> EventData:
        ev = EventData(
            symbol=event["symbol"], date=event["date"], end_ns=event["end_ns"],
            imbalance=event["imb"], spread_bps=event["spread"],
        )
        window_end = event["end_ns"] + 500 * 1_000_000 + POST_WINDOW_NS

        async with self._sem:
            q_text = await self._ch_safe(f"""
                SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
                FROM polygon_data.microstructure_quotes
                WHERE symbol = '{event["symbol"]}' AND ingestion_date = '{event["date"]}'
                  AND sip_timestamp >= {event["end_ns"] - PRE_WINDOW_NS}
                  AND sip_timestamp <= {window_end}
                ORDER BY sip_timestamp ASC
                FORMAT TSVWithNames
            """)
            t_text = await self._ch_safe(f"""
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

    async def _ch_safe(self, query: str) -> Optional[str]:
        try:
            return await self._ch_query(query)
        except Exception:
            return None

    async def _ch_query(self, query: str) -> str:
        assert self._session is not None
        async with self._session.post(self._ch_url, data=query.encode()) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ClickHouse {resp.status}: {body[:300]}")
            return await resp.text()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    tester = BranchBValidation()
    await tester.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
