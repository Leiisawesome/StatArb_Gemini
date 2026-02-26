"""
Branch B — Mechanism Confirmation + Conditional Correlation.

Two analytical tests requested by external quant:
1. Mechanism regression: PnL vs spread_ratio, imbalance_magnitude, volume_surge
2. High-vol conditioned correlation: does cross-symbol correlation spike in high-vol?

Plus: Intraday inventory stacking analysis (worst 5-min / 30-min rolling PnL).
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
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
ENTRY_DELAY_NS = 200 * 1_000_000
POST_WINDOW_NS = 30_000_000_000
PRE_WINDOW_NS = 10_000_000_000
SPREAD_NORMAL_FACTOR = 1.05
STOP_LOSS_BPS = 3.0
TIMEOUT_S = 30


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
    event_ns: int = 0
    filled: bool = False
    pnl_bps: float = 0.0
    hold_time_ms: float = 0.0
    exit_reason: str = ""
    spread_ratio: float = 0.0       # spread_at_entry / baseline
    imbalance_mag: float = 0.0      # |imbalance|
    volume_surge: float = 0.0       # trade volume in window / typical


class BranchBMechanism:

    def __init__(self):
        self._ch_url = CLICKHOUSE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 70)
        logger.info("BRANCH B — MECHANISM CONFIRMATION + CONDITIONAL CORRELATION")
        logger.info("=" * 70)

        self._session = aiohttp.ClientSession()
        try:
            events_raw = await self._get_extreme_events()
            tasks = [self._load_event_data(e) for e in events_raw]
            loaded = await asyncio.gather(*tasks, return_exceptions=True)
            events = [e for e in loaded if isinstance(e, EventData) and e.valid]
            logger.info("Valid events: %d", len(events))

            all_dates = sorted(set(e.date for e in events))
            results = [self._simulate(ev) for ev in events]

            report: Dict[str, Any] = {
                "experiment": "branch_b_mechanism",
                "constants_version": CONSTANTS_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            report["mechanism"] = self._mechanism_regression(results)
            report["conditional_corr"] = self._conditional_correlation(events, results, all_dates)
            report["intraday_risk"] = self._intraday_stacking(results)

            self._write_report(report)
            return report

        finally:
            await self._session.close()

    # ── Test 1: Mechanism Regression ──

    def _mechanism_regression(self, results: List[TradeResult]) -> Dict[str, Any]:
        logger.info("\n--- MECHANISM REGRESSION ---")

        filled = [r for r in results if r.filled and r.spread_ratio > 0]
        if len(filled) < 50:
            return {"error": "insufficient data"}

        y = np.array([r.pnl_bps for r in filled])
        x_spread = np.array([r.spread_ratio for r in filled])
        x_imb = np.array([r.imbalance_mag for r in filled])

        # Univariate regressions
        slope_spread, intercept_spread, r_spread, p_spread, _ = sp_stats.linregress(x_spread, y)
        slope_imb, intercept_imb, r_imb, p_imb, _ = sp_stats.linregress(x_imb, y)

        logger.info("  PnL ~ spread_ratio: slope=%.3f r=%.3f p=%.4f", slope_spread, r_spread, p_spread)
        logger.info("  PnL ~ |imbalance|:  slope=%.3f r=%.3f p=%.4f", slope_imb, r_imb, p_imb)

        # Multivariate (manual OLS with intercept)
        X = np.column_stack([
            np.ones(len(filled)),
            x_spread,
            x_imb,
        ])
        try:
            betas, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
            y_hat = X @ betas
            ss_res = np.sum((y - y_hat) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / max(ss_tot, 1e-10)

            # T-statistics
            n = len(y)
            k = X.shape[1]
            mse = ss_res / max(n - k, 1)
            var_betas = mse * np.linalg.inv(X.T @ X).diagonal()
            se_betas = np.sqrt(np.maximum(var_betas, 1e-20))
            t_stats = betas / se_betas
            p_vals = [2 * (1 - sp_stats.t.cdf(abs(t), n - k)) for t in t_stats]

            logger.info("  Multivariate R²=%.4f", r_squared)
            logger.info("  β_intercept=%.3f (t=%.2f, p=%.4f)", betas[0], t_stats[0], p_vals[0])
            logger.info("  β_spread   =%.3f (t=%.2f, p=%.4f)", betas[1], t_stats[1], p_vals[1])
            logger.info("  β_imbalance=%.3f (t=%.2f, p=%.4f)", betas[2], t_stats[2], p_vals[2])

            # Which coefficient is dominant?
            # Use standardized coefficients for comparison
            std_spread = np.std(x_spread)
            std_imb = np.std(x_imb)
            std_y = np.std(y)
            beta_std_spread = betas[1] * std_spread / std_y
            beta_std_imb = betas[2] * std_imb / std_y

            dominant = "spread_ratio" if abs(beta_std_spread) > abs(beta_std_imb) else "imbalance_mag"
            logger.info("  Standardized: β_spread=%.3f, β_imb=%.3f → DOMINANT: %s",
                        beta_std_spread, beta_std_imb, dominant)

            multi = {
                "r_squared": r_squared,
                "beta_intercept": float(betas[0]),
                "beta_spread": float(betas[1]),
                "beta_imbalance": float(betas[2]),
                "t_spread": float(t_stats[1]),
                "t_imbalance": float(t_stats[2]),
                "p_spread": float(p_vals[1]),
                "p_imbalance": float(p_vals[2]),
                "beta_std_spread": float(beta_std_spread),
                "beta_std_imb": float(beta_std_imb),
                "dominant_factor": dominant,
            }
        except Exception as e:
            logger.warning("  Multivariate failed: %s", e)
            multi = {"error": str(e)}

        # Quintile analysis: PnL by spread_ratio quintile
        quintile_edges = np.percentile(x_spread, [0, 20, 40, 60, 80, 100])
        quintiles = []
        for q in range(5):
            lo, hi = quintile_edges[q], quintile_edges[q + 1]
            if q == 4:
                mask = (x_spread >= lo) & (x_spread <= hi)
            else:
                mask = (x_spread >= lo) & (x_spread < hi)
            q_pnls = y[mask]
            if len(q_pnls) > 0:
                quintiles.append({
                    "quintile": q + 1,
                    "spread_ratio_range": f"{lo:.2f}-{hi:.2f}",
                    "n": int(np.sum(mask)),
                    "mean_pnl": float(np.mean(q_pnls)),
                    "hit_rate": float(np.mean(q_pnls > 0)),
                })
                logger.info("  Q%d (spread %.2f-%.2f): n=%d mean=%.2f hit=%.1f%%",
                            q + 1, lo, hi, int(np.sum(mask)),
                            float(np.mean(q_pnls)), float(np.mean(q_pnls > 0)) * 100)

        return {
            "n": len(filled),
            "univariate_spread": {
                "slope": float(slope_spread), "r": float(r_spread), "p": float(p_spread),
            },
            "univariate_imbalance": {
                "slope": float(slope_imb), "r": float(r_imb), "p": float(p_imb),
            },
            "multivariate": multi,
            "quintiles_by_spread_ratio": quintiles,
        }

    # ── Test 2: Conditional Correlation ──

    def _conditional_correlation(
        self, events: List[EventData], results: List[TradeResult], all_dates: List[str]
    ) -> Dict[str, Any]:
        logger.info("\n--- CONDITIONAL CORRELATION (HIGH-VOL vs LOW-VOL) ---")

        # Daily spread volatility
        date_spreads: Dict[str, List[float]] = defaultdict(list)
        for ev in events:
            date_spreads[ev.date].append(ev.spread_bps)
        date_vol = {d: float(np.std(s)) if len(s) > 1 else 0.0 for d, s in date_spreads.items()}
        vol_median = float(np.median(list(date_vol.values())))

        high_vol_dates = set(d for d, v in date_vol.items() if v >= vol_median)
        low_vol_dates = set(d for d, v in date_vol.items() if v < vol_median)

        # Build daily PnL per symbol
        sym_daily: Dict[str, Dict[str, float]] = {s: {} for s in TIER_A_SYMBOLS}
        for r in results:
            if r.filled:
                sym_daily[r.symbol][r.date] = sym_daily[r.symbol].get(r.date, 0) + r.pnl_bps

        def compute_corr(dates_set, label):
            dates_list = sorted(dates_set)
            series = {}
            for sym in TIER_A_SYMBOLS:
                series[sym] = np.array([sym_daily[sym].get(d, 0.0) for d in dates_list])

            pairs = {}
            syms = list(TIER_A_SYMBOLS)
            for i in range(len(syms)):
                for j in range(i + 1, len(syms)):
                    if len(dates_list) > 5:
                        c = float(np.corrcoef(series[syms[i]], series[syms[j]])[0, 1])
                    else:
                        c = 0.0
                    pairs[f"{syms[i]}-{syms[j]}"] = c

            mean_c = float(np.mean(list(pairs.values())))
            logger.info("  %s: mean corr = %.3f", label, mean_c)
            for pair, c in sorted(pairs.items()):
                logger.info("    %s: %.3f", pair, c)
            return {"pairs": pairs, "mean": mean_c, "n_days": len(dates_list)}

        all_corr = compute_corr(set(all_dates), "ALL")
        high_corr = compute_corr(high_vol_dates, "HIGH-VOL")
        low_corr = compute_corr(low_vol_dates, "LOW-VOL")

        spike = high_corr["mean"] - all_corr["mean"]
        logger.info("  Correlation spike in high-vol: %.3f", spike)
        logger.info("  Spike significant (>0.1): %s", "YES — RISK" if spike > 0.1 else "NO")

        return {
            "all": all_corr,
            "high_vol": high_corr,
            "low_vol": low_corr,
            "spike": spike,
            "spike_significant": spike > 0.1,
        }

    # ── Test 3: Intraday Inventory Stacking ──

    def _intraday_stacking(self, results: List[TradeResult]) -> Dict[str, Any]:
        logger.info("\n--- INTRADAY INVENTORY STACKING ---")

        filled = [r for r in results if r.filled]
        if not filled:
            return {"error": "no fills"}

        # Group events by date, sorted by timestamp
        by_date: Dict[str, List[TradeResult]] = defaultdict(list)
        for r in filled:
            by_date[r.date].append(r)

        max_concurrent = 0
        worst_5min_bps = 0.0
        worst_30min_bps = 0.0
        concurrent_counts = []

        for date, trades in by_date.items():
            trades.sort(key=lambda x: x.event_ns)

            # Estimate concurrent positions using hold time
            # Each trade occupies [event_ns, event_ns + hold_time_ms * 1e6]
            for i, t in enumerate(trades):
                concurrent = 1
                t_start = t.event_ns
                t_end = t.event_ns + t.hold_time_ms * 1e6

                for j, other in enumerate(trades):
                    if i == j:
                        continue
                    o_start = other.event_ns
                    o_end = other.event_ns + other.hold_time_ms * 1e6
                    if o_start < t_end and o_end > t_start:
                        concurrent += 1

                concurrent_counts.append(concurrent)
                max_concurrent = max(max_concurrent, concurrent)

            # Rolling window PnL
            pnl_arr = np.array([t.pnl_bps for t in trades])
            ts_arr = np.array([t.event_ns for t in trades])

            for i in range(len(trades)):
                # 5-min window (300 seconds = 300e9 ns)
                mask_5 = (ts_arr >= ts_arr[i]) & (ts_arr <= ts_arr[i] + 300e9)
                window_pnl = np.sum(pnl_arr[mask_5])
                worst_5min_bps = min(worst_5min_bps, window_pnl)

                # 30-min window
                mask_30 = (ts_arr >= ts_arr[i]) & (ts_arr <= ts_arr[i] + 1800e9)
                window_pnl_30 = np.sum(pnl_arr[mask_30])
                worst_30min_bps = min(worst_30min_bps, window_pnl_30)

        concurrent_arr = np.array(concurrent_counts)

        logger.info("  Max concurrent positions: %d", max_concurrent)
        logger.info("  Mean concurrent: %.1f", float(np.mean(concurrent_arr)))
        logger.info("  P95 concurrent: %d", int(np.percentile(concurrent_arr, 95)))
        logger.info("  Worst 5-min PnL: %.2f bps", worst_5min_bps)
        logger.info("  Worst 30-min PnL: %.2f bps", worst_30min_bps)

        return {
            "max_concurrent": max_concurrent,
            "mean_concurrent": float(np.mean(concurrent_arr)),
            "p95_concurrent": int(np.percentile(concurrent_arr, 95)),
            "worst_5min_bps": worst_5min_bps,
            "worst_30min_bps": worst_30min_bps,
        }

    # ── Simulation (same as validation, enriched with mechanism features) ──

    def _simulate(self, ev: EventData) -> TradeResult:
        result = TradeResult(symbol=ev.symbol, date=ev.date, event_ns=ev.end_ns)
        result.imbalance_mag = abs(ev.imbalance)

        entry_time_ns = ev.end_ns + ENTRY_DELAY_NS
        q_ts = ev.q_ts
        q_mid = (ev.q_bid + ev.q_ask) / 2.0
        q_spread = np.where(q_mid > 0, (ev.q_ask - ev.q_bid) / q_mid * 10000, 0)

        pre_mask = q_ts < ev.end_ns
        if np.sum(pre_mask) >= 3:
            baseline_spread = float(np.median(q_spread[pre_mask][-50:]))
        else:
            baseline_spread = ev.spread_bps

        entry_q_idx = np.searchsorted(q_ts, entry_time_ns)
        if entry_q_idx >= len(q_ts):
            return result
        entry_q_idx = min(entry_q_idx, len(q_ts) - 1)

        entry_bid = ev.q_bid[entry_q_idx]
        entry_ask = ev.q_ask[entry_q_idx]
        if entry_bid <= 0 or entry_ask <= 0:
            return result

        entry_spread = q_spread[entry_q_idx]
        result.spread_ratio = entry_spread / max(baseline_spread, 0.01)

        imb_direction = np.sign(ev.imbalance)
        if imb_direction > 0:
            our_price = entry_ask
            our_side = "ask"
            queue_ahead = int(ev.q_ask_sz[entry_q_idx])
        else:
            our_price = entry_bid
            our_side = "bid"
            queue_ahead = int(ev.q_bid_sz[entry_q_idx])

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

    # ── Report ──

    def _write_report(self, report: Dict[str, Any]) -> None:
        root = Path(__file__).resolve().parents[3]
        out = root / "results" / "foundation_diagnostic" / "branch_b_mechanism_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Branch B — Mechanism Confirmation + Deployment Readiness",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            "",
        ]

        # Mechanism regression
        m = report.get("mechanism", {})
        if "error" not in m:
            multi = m.get("multivariate", {})
            lines.extend([
                "## 1. Mechanism Regression: What Drives PnL?",
                "",
                f"N = {m['n']} filled trades",
                "",
                "### Univariate",
                "",
                f"- **PnL ~ spread_ratio**: slope={m['univariate_spread']['slope']:.3f}, "
                f"r={m['univariate_spread']['r']:.3f}, p={m['univariate_spread']['p']:.4f}",
                f"- **PnL ~ |imbalance|**: slope={m['univariate_imbalance']['slope']:.3f}, "
                f"r={m['univariate_imbalance']['r']:.3f}, p={m['univariate_imbalance']['p']:.4f}",
                "",
            ])

            if "error" not in multi:
                lines.extend([
                    "### Multivariate OLS",
                    "",
                    f"- **R²**: {multi['r_squared']:.4f}",
                    f"- **β_spread**: {multi['beta_spread']:.3f} (t={multi['t_spread']:.2f}, p={multi['p_spread']:.4f})",
                    f"- **β_imbalance**: {multi['beta_imbalance']:.3f} (t={multi['t_imbalance']:.2f}, p={multi['p_imbalance']:.4f})",
                    f"- **Standardized β_spread**: {multi['beta_std_spread']:.3f}",
                    f"- **Standardized β_imbalance**: {multi['beta_std_imb']:.3f}",
                    f"- **Dominant factor**: **{multi['dominant_factor']}**",
                    "",
                ])

            # Quintiles
            if m.get("quintiles_by_spread_ratio"):
                lines.extend([
                    "### PnL by Spread Ratio Quintile",
                    "",
                    "| Quintile | Spread Ratio | N | Mean PnL | Hit Rate |",
                    "|----------|-------------|---|----------|----------|",
                ])
                for q in m["quintiles_by_spread_ratio"]:
                    lines.append(
                        f"| Q{q['quintile']} | {q['spread_ratio_range']} | {q['n']} | "
                        f"{q['mean_pnl']:.2f} | {q['hit_rate']:.1%} |"
                    )
                lines.append("")

        # Conditional correlation
        cc = report.get("conditional_corr", {})
        if "all" in cc:
            lines.extend([
                "## 2. Conditional Correlation (Does risk concentrate in high-vol?)",
                "",
                "| Regime | Mean Pairwise Corr | N Days |",
                "|--------|--------------------|--------|",
                f"| All | {cc['all']['mean']:.3f} | {cc['all']['n_days']} |",
                f"| High-vol | {cc['high_vol']['mean']:.3f} | {cc['high_vol']['n_days']} |",
                f"| Low-vol | {cc['low_vol']['mean']:.3f} | {cc['low_vol']['n_days']} |",
                "",
                f"**Correlation spike in high-vol**: {cc['spike']:.3f} "
                f"({'SIGNIFICANT — reduce portfolio size in high-vol' if cc['spike_significant'] else 'Not significant — diversification holds'})",
                "",
            ])

            # Detail pairs
            lines.append("**Pairwise detail (high-vol only):**\n")
            for pair, c in sorted(cc["high_vol"]["pairs"].items()):
                lines.append(f"- {pair}: {c:.3f}")
            lines.append("")

        # Intraday stacking
        intra = report.get("intraday_risk", {})
        if "max_concurrent" in intra:
            lines.extend([
                "## 3. Intraday Inventory Stacking",
                "",
                f"- **Max concurrent positions**: {intra['max_concurrent']}",
                f"- **Mean concurrent**: {intra['mean_concurrent']:.1f}",
                f"- **P95 concurrent**: {intra['p95_concurrent']}",
                f"- **Worst 5-min rolling PnL**: {intra['worst_5min_bps']:.2f} bps",
                f"- **Worst 30-min rolling PnL**: {intra['worst_30min_bps']:.2f} bps",
                "",
            ])

        out.write_text("\n".join(lines))
        logger.info("Report: %s", out)

    # ── Data Loading ──

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
            logger.info("%s: %d extreme events", sym, n)
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
                ORDER BY sip_timestamp ASC FORMAT TSVWithNames
            """)
            t_text = await self._ch_safe(f"""
                SELECT sip_timestamp, price, size
                FROM polygon_data.microstructure_trades
                WHERE symbol = '{event["symbol"]}' AND ingestion_date = '{event["date"]}'
                  AND sip_timestamp >= {event["end_ns"]}
                  AND sip_timestamp <= {window_end}
                ORDER BY sip_timestamp ASC FORMAT TSVWithNames
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
    tester = BranchBMechanism()
    await tester.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
