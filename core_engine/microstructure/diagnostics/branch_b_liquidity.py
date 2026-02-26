"""
Branch B — Pessimistic Passive Liquidity Provision Simulation.

The decisive test: Can a non-colocated trader monetize predictable
spread compression after liquidity shock?

Pessimistic assumptions:
  - 100ms order entry delay
  - Last in visible queue (filled only after queue_ahead consumed)
  - Three-way exit: spread normalization OR 30s timeout OR 3bps stop-loss
  - Exit at midpoint (conservative — assumes crossing to exit)

Scope: Tier A only (MSFT, NVDA) — tightest spreads, deepest books.
If it fails here, it fails everywhere.
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
TIER_A_SYMBOLS = ["MSFT", "NVDA"]
EVENTS_PER_SYMBOL = 300
CH_CONCURRENCY = 8

# Simulation parameters
ENTRY_DELAY_MS = 100
ENTRY_DELAY_NS = ENTRY_DELAY_MS * 1_000_000
POST_WINDOW_NS = 30_000_000_000  # 30 seconds max hold
PRE_WINDOW_NS = 10_000_000_000   # 10 seconds pre-event for baseline
SPREAD_NORMAL_FACTOR = 1.05       # exit when spread ≤ 105% of baseline
STOP_LOSS_BPS = 3.0               # exit if midpoint moves against > 3 bps
TIMEOUT_S = 30                     # hard timeout


@dataclass
class TradeOutcome:
    """Outcome of one simulated liquidity provision trade."""
    symbol: str
    event_date: str
    event_imbalance: float
    event_spread_bps: float

    filled: bool = False
    fill_time_ms: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    exit_reason: str = ""
    hold_time_ms: float = 0.0
    pnl_bps: float = 0.0
    spread_at_entry: float = 0.0
    spread_at_exit: float = 0.0
    queue_ahead: int = 0
    volume_through_level: int = 0

    # Pre-event baseline
    baseline_spread_bps: float = 0.0


class BranchBLiquidity:
    """Pessimistic passive liquidity provision simulation."""

    def __init__(self):
        self._ch_url = CLICKHOUSE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("BRANCH B — PESSIMISTIC LIQUIDITY PROVISION SIMULATION")
        logger.info("Symbols: %s | Entry delay: %dms | Stop: %d bps",
                     TIER_A_SYMBOLS, ENTRY_DELAY_MS, STOP_LOSS_BPS)
        logger.info("=" * 60)

        self._session = aiohttp.ClientSession()
        try:
            events = await self._get_extreme_events()
            logger.info("Loaded %d extreme events", len(events))

            t0 = time.monotonic()
            tasks = [self._simulate_event(e) for e in events]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.monotonic() - t0

            outcomes = [r for r in results if isinstance(r, TradeOutcome)]
            errors = sum(1 for r in results if isinstance(r, Exception))
            logger.info("Processed %d events in %.1fs (%d errors)",
                        len(outcomes), elapsed, errors)

            report = self._analyze(outcomes)
            self._write_report(report, outcomes)
            return report

        finally:
            await self._session.close()

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

            # Parse date components for RTH filtering
            date_str = f[col["bucket_date"]]
            start_ns = int(f[col["bucket_start_ns"]])
            end_ns = int(f[col["bucket_end_ns"]])

            by_sym[sym].append({
                "symbol": sym,
                "date": date_str,
                "start_ns": start_ns,
                "end_ns": end_ns,
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

            logger.info("%s: %d extreme events sampled (threshold=%.3f)", sym, n, thresh)

        return events

    async def _simulate_event(self, event: dict) -> TradeOutcome:
        """Simulate one passive liquidity provision trade."""
        outcome = TradeOutcome(
            symbol=event["symbol"],
            event_date=event["date"],
            event_imbalance=event["imb"],
            event_spread_bps=event["spread"],
        )

        entry_time_ns = event["end_ns"] + ENTRY_DELAY_NS
        window_end_ns = entry_time_ns + POST_WINDOW_NS

        # Load quotes and trades in the window
        async with self._sem:
            quotes = await self._load_quotes(
                event["symbol"], event["date"],
                event["end_ns"] - PRE_WINDOW_NS, window_end_ns,
            )
            trades = await self._load_trades(
                event["symbol"], event["date"],
                entry_time_ns, window_end_ns,
            )

        if quotes is None or len(quotes["ts"]) < 10:
            return outcome
        if trades is None or len(trades["ts"]) < 5:
            return outcome

        q_ts = quotes["ts"]
        q_bid = quotes["bid"]
        q_ask = quotes["ask"]
        q_bid_sz = quotes["bid_sz"]
        q_ask_sz = quotes["ask_sz"]
        q_mid = (q_bid + q_ask) / 2.0
        q_spread = np.where(q_mid > 0, (q_ask - q_bid) / q_mid * 10000, 0)

        t_ts = trades["ts"]
        t_price = trades["price"]
        t_size = trades["size"]

        # Baseline spread (pre-event)
        pre_mask = q_ts < event["end_ns"]
        if np.sum(pre_mask) >= 3:
            pre_spread = q_spread[pre_mask]
            outcome.baseline_spread_bps = float(np.median(pre_spread[-50:]))
        else:
            outcome.baseline_spread_bps = event["spread"]

        # At entry time (100ms after event), what is the quote state?
        entry_q_idx = np.searchsorted(q_ts, entry_time_ns)
        if entry_q_idx >= len(q_ts):
            return outcome
        entry_q_idx = min(entry_q_idx, len(q_ts) - 1)

        entry_bid = q_bid[entry_q_idx]
        entry_ask = q_ask[entry_q_idx]
        entry_mid = q_mid[entry_q_idx]
        entry_spread = q_spread[entry_q_idx]
        outcome.spread_at_entry = float(entry_spread)

        if entry_bid <= 0 or entry_ask <= 0:
            return outcome

        # Determine our side: if imbalance positive (buy pressure),
        # we provide liquidity on the ASK side (sell into buyers).
        # If imbalance negative (sell pressure), provide on BID side (buy from sellers).
        imb_direction = np.sign(event["imb"])

        if imb_direction > 0:
            # Buy pressure → we SELL at the ask
            our_price = entry_ask
            our_side = "ask"
            queue_ahead = int(q_ask_sz[entry_q_idx])
        else:
            # Sell pressure → we BUY at the bid
            our_price = entry_bid
            our_side = "bid"
            queue_ahead = int(q_bid_sz[entry_q_idx])

        outcome.entry_price = float(our_price)
        outcome.queue_ahead = queue_ahead

        # Fill model: we are LAST in queue. Count volume traded at or
        # through our price level. We are filled when cumulative volume > queue_ahead.
        cum_volume = 0
        fill_time_ns = 0

        for i in range(len(t_ts)):
            if t_ts[i] < entry_time_ns:
                continue

            if our_side == "ask" and t_price[i] >= our_price:
                cum_volume += t_size[i]
            elif our_side == "bid" and t_price[i] <= our_price:
                cum_volume += t_size[i]

            if cum_volume > queue_ahead:
                fill_time_ns = t_ts[i]
                break

        outcome.volume_through_level = cum_volume

        if fill_time_ns == 0:
            outcome.filled = False
            return outcome

        outcome.filled = True
        outcome.fill_time_ms = float((fill_time_ns - entry_time_ns) / 1e6)

        # Three-way exit
        exit_price = 0.0
        exit_reason = ""
        exit_time_ns = 0

        spread_threshold = outcome.baseline_spread_bps * SPREAD_NORMAL_FACTOR
        timeout_ns = fill_time_ns + TIMEOUT_S * 1_000_000_000

        # Walk through quotes after fill
        post_fill_start = np.searchsorted(q_ts, fill_time_ns)

        for qi in range(post_fill_start, len(q_ts)):
            current_ts = q_ts[qi]
            current_mid = q_mid[qi]
            current_spread = q_spread[qi]

            if current_mid <= 0:
                continue

            # Check stop-loss: midpoint moved against us by > STOP_LOSS_BPS
            if imb_direction > 0:
                # We sold at ask. Adverse = price goes UP
                adverse_move = (current_mid - our_price) / our_price * 10000
            else:
                # We bought at bid. Adverse = price goes DOWN
                adverse_move = (our_price - current_mid) / our_price * 10000

            if adverse_move > STOP_LOSS_BPS:
                exit_price = current_mid
                exit_reason = "stop_loss"
                exit_time_ns = current_ts
                break

            # Check spread normalization
            if current_spread <= spread_threshold and current_ts > fill_time_ns + 500_000_000:
                exit_price = current_mid
                exit_reason = "spread_normal"
                exit_time_ns = current_ts
                break

            # Check timeout
            if current_ts >= timeout_ns:
                exit_price = current_mid
                exit_reason = "timeout"
                exit_time_ns = current_ts
                break

        if exit_price == 0:
            # Use last available midpoint
            exit_price = float(q_mid[-1])
            exit_reason = "end_of_data"
            exit_time_ns = int(q_ts[-1])

        outcome.exit_price = float(exit_price)
        outcome.exit_reason = exit_reason
        outcome.hold_time_ms = float((exit_time_ns - fill_time_ns) / 1e6)

        # P&L in bps
        if imb_direction > 0:
            # Sold at our_price, "exit" (covering) at exit_price
            outcome.pnl_bps = (our_price - exit_price) / our_price * 10000
        else:
            # Bought at our_price, sell at exit_price
            outcome.pnl_bps = (exit_price - our_price) / our_price * 10000

        q_exit_idx = np.searchsorted(q_ts, exit_time_ns)
        q_exit_idx = min(q_exit_idx, len(q_ts) - 1)
        outcome.spread_at_exit = float(q_spread[q_exit_idx])

        return outcome

    def _analyze(self, outcomes: List[TradeOutcome]) -> Dict[str, Any]:
        """Evaluate Branch B gates."""
        total = len(outcomes)
        filled = [o for o in outcomes if o.filled]
        not_filled = total - len(filled)

        logger.info("\n%s", "=" * 60)
        logger.info("BRANCH B RESULTS")
        logger.info("=" * 60)

        report: Dict[str, Any] = {
            "experiment": "branch_b_liquidity_provision",
            "constants_version": CONSTANTS_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": TIER_A_SYMBOLS,
            "total_events": total,
            "filled_events": len(filled),
            "fill_rate": len(filled) / max(total, 1),
            "gates": [],
            "per_symbol": {},
            "exit_reasons": {},
        }

        # B1: Fill probability > 30%
        fill_rate = len(filled) / max(total, 1)
        b1_pass = fill_rate > 0.30
        report["gates"].append({
            "id": "B1", "name": "Fill probability > 30%",
            "result": "PASS" if b1_pass else "FAIL",
            "value": fill_rate,
            "threshold": 0.30,
        })
        logger.info("B1 Fill rate: %s — %.1f%% (%d/%d)",
                     "PASS" if b1_pass else "FAIL", fill_rate * 100, len(filled), total)

        if not filled:
            report["decision"] = "TERMINATE"
            report["detail"] = "No fills. Strategy is theoretical — cannot execute."
            for gid in ["B2", "B3", "B4", "B5"]:
                report["gates"].append({"id": gid, "result": "FAIL", "value": 0, "threshold": 0})
            return report

        pnls = np.array([o.pnl_bps for o in filled])
        hold_times = np.array([o.hold_time_ms for o in filled])

        # B2: Mean spread capture > 1 bps
        mean_pnl = float(np.mean(pnls))
        b2_pass = mean_pnl > 1.0
        report["gates"].append({
            "id": "B2", "name": "Mean spread capture > 1 bps",
            "result": "PASS" if b2_pass else "FAIL",
            "value": mean_pnl,
            "threshold": 1.0,
        })
        logger.info("B2 Mean capture: %s — %.2f bps", "PASS" if b2_pass else "FAIL", mean_pnl)

        # B3: Hit rate > 55%
        hit_rate = float(np.mean(pnls > 0))
        b3_pass = hit_rate > 0.55
        report["gates"].append({
            "id": "B3", "name": "Hit rate > 55%",
            "result": "PASS" if b3_pass else "FAIL",
            "value": hit_rate,
            "threshold": 0.55,
        })
        logger.info("B3 Hit rate: %s — %.1f%%", "PASS" if b3_pass else "FAIL", hit_rate * 100)

        # B4: Net edge × daily event count > 0.5 bps/day
        events_per_day = total / 130  # 130 trading days
        daily_edge = mean_pnl * fill_rate * events_per_day
        b4_pass = daily_edge > 0.5
        report["gates"].append({
            "id": "B4", "name": "Portfolio daily edge > 0.5 bps",
            "result": "PASS" if b4_pass else "FAIL",
            "value": daily_edge,
            "threshold": 0.5,
        })
        logger.info("B4 Daily edge: %s — %.2f bps/day (%.1f events/day × %.1f%% fill × %.2f bps)",
                     "PASS" if b4_pass else "FAIL", daily_edge, events_per_day, fill_rate * 100, mean_pnl)

        # B5: Daily Sharpe ≥ 0.8 (annualized)
        daily_pnls = self._compute_daily_pnls(filled)
        if len(daily_pnls) > 5:
            daily_mean = np.mean(daily_pnls)
            daily_std = np.std(daily_pnls, ddof=1)
            daily_sharpe = daily_mean / max(daily_std, 1e-6) * math.sqrt(252)
        else:
            daily_sharpe = 0.0
        b5_pass = daily_sharpe >= 0.8
        report["gates"].append({
            "id": "B5", "name": "Annualized Sharpe ≥ 0.8",
            "result": "PASS" if b5_pass else "FAIL",
            "value": daily_sharpe,
            "threshold": 0.8,
        })
        logger.info("B5 Sharpe: %s — %.2f", "PASS" if b5_pass else "FAIL", daily_sharpe)

        # Distribution
        report["pnl_distribution"] = {
            "mean": mean_pnl,
            "median": float(np.median(pnls)),
            "std": float(np.std(pnls)),
            "p10": float(np.percentile(pnls, 10)),
            "p25": float(np.percentile(pnls, 25)),
            "p75": float(np.percentile(pnls, 75)),
            "p90": float(np.percentile(pnls, 90)),
            "skew": float(sp_stats.skew(pnls)),
            "kurtosis": float(sp_stats.kurtosis(pnls)),
            "hit_rate": hit_rate,
            "mean_hold_ms": float(np.mean(hold_times)),
            "median_hold_ms": float(np.median(hold_times)),
        }

        # Exit reason breakdown
        reasons = {}
        for o in filled:
            reasons[o.exit_reason] = reasons.get(o.exit_reason, 0) + 1
        report["exit_reasons"] = reasons

        # Per-symbol
        for sym in TIER_A_SYMBOLS:
            sym_filled = [o for o in filled if o.symbol == sym]
            sym_total = sum(1 for o in outcomes if o.symbol == sym)
            if sym_filled:
                sym_pnls = np.array([o.pnl_bps for o in sym_filled])
                report["per_symbol"][sym] = {
                    "total": sym_total,
                    "filled": len(sym_filled),
                    "fill_rate": len(sym_filled) / max(sym_total, 1),
                    "mean_pnl": float(np.mean(sym_pnls)),
                    "median_pnl": float(np.median(sym_pnls)),
                    "hit_rate": float(np.mean(sym_pnls > 0)),
                    "mean_hold_ms": float(np.mean([o.hold_time_ms for o in sym_filled])),
                    "mean_queue_ahead": float(np.mean([o.queue_ahead for o in sym_filled])),
                }

        n_pass = sum(1 for g in report["gates"] if g["result"] == "PASS")
        if n_pass >= 4:
            report["decision"] = "PROCEED"
            report["detail"] = (
                f"{n_pass}/5 gates passed. Passive liquidity provision shows edge "
                "under pessimistic assumptions. Proceed to full strategy design."
            )
        elif n_pass >= 3:
            report["decision"] = "INVESTIGATE"
            report["detail"] = (
                f"{n_pass}/5 gates passed. Partial viability detected. "
                "Targeted refinement of failing dimensions warranted."
            )
        else:
            report["decision"] = "TERMINATE"
            report["detail"] = (
                f"Only {n_pass}/5 gates passed. Passive liquidity provision is not "
                "economically viable at this resolution under pessimistic assumptions. "
                "SIP-derived imbalance data is descriptive but not tradable."
            )

        logger.info("\nDECISION: %s — %s", report["decision"], report["detail"])
        return report

    @staticmethod
    def _compute_daily_pnls(filled: List[TradeOutcome]) -> np.ndarray:
        """Aggregate filled trades into daily P&L for Sharpe computation."""
        daily: Dict[str, float] = {}
        for o in filled:
            daily[o.event_date] = daily.get(o.event_date, 0) + o.pnl_bps
        return np.array(list(daily.values())) if daily else np.array([0.0])

    async def _load_quotes(
        self, symbol: str, date: str, start_ns: int, end_ns: int
    ) -> Optional[Dict[str, np.ndarray]]:
        query = f"""
        SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
        FROM polygon_data.microstructure_quotes
        WHERE symbol = '{symbol}' AND ingestion_date = '{date}'
          AND sip_timestamp >= {start_ns} AND sip_timestamp <= {end_ns}
        ORDER BY sip_timestamp ASC
        FORMAT TSVWithNames
        """
        try:
            text = await self._ch_query(query)
        except Exception:
            return None

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return None

        n = len(lines) - 1
        ts = np.empty(n, dtype=np.int64)
        bid = np.empty(n, dtype=np.float64)
        ask = np.empty(n, dtype=np.float64)
        bid_sz = np.empty(n, dtype=np.float64)
        ask_sz = np.empty(n, dtype=np.float64)

        for i, line in enumerate(lines[1:]):
            p = line.split("\t")
            ts[i] = int(p[0])
            bid[i] = float(p[1])
            ask[i] = float(p[2])
            bid_sz[i] = float(p[3])
            ask_sz[i] = float(p[4])

        return {"ts": ts, "bid": bid, "ask": ask, "bid_sz": bid_sz, "ask_sz": ask_sz}

    async def _load_trades(
        self, symbol: str, date: str, start_ns: int, end_ns: int
    ) -> Optional[Dict[str, np.ndarray]]:
        query = f"""
        SELECT sip_timestamp, price, size
        FROM polygon_data.microstructure_trades
        WHERE symbol = '{symbol}' AND ingestion_date = '{date}'
          AND sip_timestamp >= {start_ns} AND sip_timestamp <= {end_ns}
        ORDER BY sip_timestamp ASC
        FORMAT TSVWithNames
        """
        try:
            text = await self._ch_query(query)
        except Exception:
            return None

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return None

        n = len(lines) - 1
        ts = np.empty(n, dtype=np.int64)
        price = np.empty(n, dtype=np.float64)
        size = np.empty(n, dtype=np.int64)

        for i, line in enumerate(lines[1:]):
            p = line.split("\t")
            ts[i] = int(p[0])
            price[i] = float(p[1])
            size[i] = int(p[2])

        return {"ts": ts, "price": price, "size": size}

    async def _ch_query(self, query: str) -> str:
        assert self._session is not None
        async with self._session.post(self._ch_url, data=query.encode()) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ClickHouse {resp.status}: {body[:300]}")
            return await resp.text()

    def _write_report(self, report: Dict[str, Any], outcomes: List[TradeOutcome]) -> None:
        root = Path(__file__).resolve().parents[3]
        out = root / "results" / "foundation_diagnostic" / "branch_b_liquidity_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)

        filled = [o for o in outcomes if o.filled]

        lines = [
            "# Branch B — Pessimistic Liquidity Provision Simulation",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            f"**Symbols**: {', '.join(TIER_A_SYMBOLS)}",
            f"**Entry delay**: {ENTRY_DELAY_MS}ms | **Stop-loss**: {STOP_LOSS_BPS} bps | **Timeout**: {TIMEOUT_S}s",
            f"**Queue model**: Last in visible queue (pessimistic)",
            "",
            f"## Decision: **{report.get('decision', 'N/A')}**",
            "",
            report.get("detail", ""),
            "",
            "---",
            "",
            "## Gate Results",
            "",
            "| Gate | Name | Result | Value | Threshold |",
            "|------|------|--------|-------|-----------|",
        ]
        for g in report.get("gates", []):
            lines.append(
                f"| {g['id']} | {g.get('name', '')} | **{g['result']}** | "
                f"{g['value']:.4f} | {g['threshold']:.4f} |"
            )

        if "pnl_distribution" in report:
            d = report["pnl_distribution"]
            lines.extend([
                "", "## P&L Distribution (filled trades only)", "",
                f"- **Mean**: {d['mean']:.2f} bps",
                f"- **Median**: {d['median']:.2f} bps",
                f"- **Std**: {d['std']:.2f} bps",
                f"- **P10/P90**: {d['p10']:.2f} / {d['p90']:.2f} bps",
                f"- **Skew**: {d['skew']:.2f} | **Kurtosis**: {d['kurtosis']:.2f}",
                f"- **Hit rate**: {d['hit_rate']:.1%}",
                f"- **Mean hold**: {d['mean_hold_ms']:.0f} ms | **Median hold**: {d['median_hold_ms']:.0f} ms",
            ])

        if report.get("exit_reasons"):
            lines.extend(["", "## Exit Reasons", ""])
            for reason, count in sorted(report["exit_reasons"].items()):
                pct = count / max(len(filled), 1) * 100
                reason_pnls = [o.pnl_bps for o in filled if o.exit_reason == reason]
                mean_pnl = np.mean(reason_pnls) if reason_pnls else 0
                lines.append(f"- **{reason}**: {count} ({pct:.1f}%) — mean PnL: {mean_pnl:.2f} bps")

        if report.get("per_symbol"):
            lines.extend(["", "## Per-Symbol Breakdown", "",
                          "| Symbol | Total | Filled | Fill% | Mean PnL | Median PnL | Hit Rate | Hold (ms) | Queue |",
                          "|--------|-------|--------|-------|----------|------------|----------|-----------|-------|"])
            for sym, d in sorted(report["per_symbol"].items()):
                lines.append(
                    f"| {sym} | {d['total']} | {d['filled']} | {d['fill_rate']:.1%} | "
                    f"{d['mean_pnl']:.2f} | {d['median_pnl']:.2f} | {d['hit_rate']:.1%} | "
                    f"{d['mean_hold_ms']:.0f} | {d['mean_queue_ahead']:.0f} |"
                )

        out.write_text("\n".join(lines))
        logger.info("Report: %s", out)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    tester = BranchBLiquidity()
    report = await tester.run()

    print(f"\n{'='*60}")
    print(f"BRANCH B DECISION: {report.get('decision', 'N/A')}")
    print(f"{'='*60}")
    print(report.get("detail", ""))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
