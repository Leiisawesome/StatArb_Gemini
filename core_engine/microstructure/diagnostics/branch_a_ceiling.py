"""
Branch A — Latency-Sensitive Continuation Ceiling Check.

Lightweight, informational only. Time-boxed. Not decisive.

Question: At what reaction latency does continuation edge exceed
half-spread cost? What is the theoretical ceiling?

Scope: Tier A only (MSFT, NVDA), 200 extreme events per symbol.
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
from core_engine.microstructure.diagnostics.foundation_runner import FoundationDiagnosticRunner

logger = logging.getLogger(__name__)

CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
TIER_A_SYMBOLS = ["MSFT", "NVDA"]
EVENTS_PER_SYMBOL = 200
LATENCY_OFFSETS_MS = [50, 100, 200, 500, 1000, 2000, 5000]
CH_CONCURRENCY = 10


@dataclass
class LatencyResult:
    """Continuation edge at a specific entry latency."""
    latency_ms: int
    n_events: int = 0
    mean_continuation_bps: float = 0.0
    mean_half_spread_bps: float = 0.0
    mean_net_bps: float = 0.0
    hit_rate: float = 0.0
    viable: bool = False


class BranchACeiling:
    """Quick ceiling check for latency-sensitive continuation."""

    def __init__(self):
        self._ch_url = CLICKHOUSE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._sem = asyncio.Semaphore(CH_CONCURRENCY)

    async def run(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("BRANCH A — CONTINUATION CEILING CHECK")
        logger.info("Symbols: %s | Events/sym: %d", TIER_A_SYMBOLS, EVENTS_PER_SYMBOL)
        logger.info("=" * 60)

        self._session = aiohttp.ClientSession()
        try:
            events = await self._get_extreme_events()
            logger.info("Loaded %d extreme events", len(events))

            all_results: Dict[int, LatencyResult] = {}
            for lat_ms in LATENCY_OFFSETS_MS:
                tasks = [self._measure_event(e, lat_ms) for e in events]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)

                cont_bps = []
                half_spr = []
                for o in outcomes:
                    if isinstance(o, tuple) and len(o) == 2:
                        cont_bps.append(o[0])
                        half_spr.append(o[1])

                if not cont_bps:
                    all_results[lat_ms] = LatencyResult(latency_ms=lat_ms)
                    continue

                c = np.array(cont_bps)
                s = np.array(half_spr)
                net = c - s

                r = LatencyResult(
                    latency_ms=lat_ms,
                    n_events=len(c),
                    mean_continuation_bps=float(np.mean(c)),
                    mean_half_spread_bps=float(np.mean(s)),
                    mean_net_bps=float(np.mean(net)),
                    hit_rate=float(np.mean(net > 0)),
                    viable=float(np.mean(net)) > 0 and float(np.mean(net > 0)) > 0.52,
                )
                all_results[lat_ms] = r
                logger.info(
                    "  %4dms: cont=%.2f, half_spr=%.2f, net=%.2f, hit=%.1f%% %s",
                    lat_ms, r.mean_continuation_bps, r.mean_half_spread_bps,
                    r.mean_net_bps, r.hit_rate * 100,
                    "✓ VIABLE" if r.viable else "",
                )

            # Find minimum viable latency
            viable_latencies = [lat for lat, r in all_results.items() if r.viable]
            min_viable = min(viable_latencies) if viable_latencies else None

            report = {
                "experiment": "branch_a_ceiling_check",
                "constants_version": CONSTANTS_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbols": TIER_A_SYMBOLS,
                "n_events": len(events),
                "latency_results": {
                    str(k): {
                        "latency_ms": r.latency_ms,
                        "n_events": r.n_events,
                        "continuation_bps": r.mean_continuation_bps,
                        "half_spread_bps": r.mean_half_spread_bps,
                        "net_bps": r.mean_net_bps,
                        "hit_rate": r.hit_rate,
                        "viable": r.viable,
                    }
                    for k, r in sorted(all_results.items())
                },
                "min_viable_latency_ms": min_viable,
                "conclusion": (
                    f"Net positive at ≥{min_viable}ms. "
                    f"{'Feasible for non-HFT.' if min_viable and min_viable >= 500 else 'Requires sub-second infrastructure.' if min_viable else 'No viable latency found.'}"
                    if min_viable else
                    "No latency yields positive net edge. Continuation is absorbed by spread widening at all tested latencies."
                ),
            }

            self._write_report(report, all_results)
            logger.info("\nCONCLUSION: %s", report["conclusion"])
            return report

        finally:
            await self._session.close()

    async def _get_extreme_events(self) -> List[dict]:
        syms = ",".join(f"'{s}'" for s in TIER_A_SYMBOLS)
        query = f"""
        SELECT symbol, bucket_date, bucket_end_ns, flow_imbalance,
               effective_spread_bps, close_price
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
            by_sym[sym].append({
                "symbol": sym,
                "date": f[col["bucket_date"]],
                "end_ns": int(f[col["bucket_end_ns"]]),
                "imb": float(f[col["flow_imbalance"]]),
                "spread": float(f[col["effective_spread_bps"]]),
                "close": float(f[col["close_price"]]),
            })

        events = []
        rng = np.random.RandomState(42)
        for sym in TIER_A_SYMBOLS:
            buckets = by_sym[sym]
            abs_imbs = np.array([abs(b["imb"]) for b in buckets])
            thresh = np.percentile(abs_imbs, 95)
            extreme = [b for b in buckets if abs(b["imb"]) >= thresh]
            sampled = rng.choice(len(extreme), size=min(EVENTS_PER_SYMBOL, len(extreme)), replace=False)
            for i in sampled:
                events.append(extreme[i])
        return events

    async def _measure_event(self, event: dict, latency_ms: int) -> Optional[Tuple[float, float]]:
        """Measure continuation and half-spread at a specific entry latency."""
        entry_ns = event["end_ns"] + latency_ms * 1_000_000
        exit_ns = entry_ns + 5_000_000_000  # 5 second horizon

        async with self._sem:
            query = f"""
            SELECT sip_timestamp, bid_price, ask_price
            FROM polygon_data.microstructure_quotes
            WHERE symbol = '{event["symbol"]}'
              AND ingestion_date = '{event["date"]}'
              AND sip_timestamp >= {entry_ns - 100_000_000}
              AND sip_timestamp <= {exit_ns}
            ORDER BY sip_timestamp ASC
            LIMIT 500
            FORMAT TSVWithNames
            """
            try:
                text = await self._ch_query(query)
            except Exception:
                return None

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return None

        ts_arr, bid_arr, ask_arr = [], [], []
        for line in lines[1:]:
            parts = line.split("\t")
            ts_arr.append(int(parts[0]))
            bid_arr.append(float(parts[1]))
            ask_arr.append(float(parts[2]))

        ts = np.array(ts_arr)
        bid = np.array(bid_arr)
        ask = np.array(ask_arr)
        mid = (bid + ask) / 2.0
        spread_bps = (ask - bid) / mid * 10000

        # Find entry point
        entry_idx = np.searchsorted(ts, entry_ns)
        if entry_idx >= len(ts) - 5:
            return None

        entry_mid = mid[entry_idx]
        entry_half_spread = spread_bps[entry_idx] / 2.0

        # Find exit (5s after entry or end of data)
        exit_target_ns = entry_ns + 5_000_000_000
        exit_idx = np.searchsorted(ts, exit_target_ns)
        exit_idx = min(exit_idx, len(ts) - 1)
        exit_mid = mid[exit_idx]

        # Continuation = directional move in imbalance direction
        direction = np.sign(event["imb"])
        continuation_bps = direction * (exit_mid - entry_mid) / entry_mid * 10000

        return (continuation_bps, entry_half_spread)

    async def _ch_query(self, query: str) -> str:
        assert self._session is not None
        async with self._session.post(self._ch_url, data=query.encode()) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ClickHouse {resp.status}: {body[:300]}")
            return await resp.text()

    def _write_report(self, report: Dict[str, Any], results: Dict[int, LatencyResult]) -> None:
        root = Path(__file__).resolve().parents[3]
        out = root / "results" / "foundation_diagnostic" / "branch_a_ceiling_report.md"
        out.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Branch A — Continuation Ceiling Check",
            "",
            f"**Constants**: {CONSTANTS_VERSION}",
            f"**Symbols**: {', '.join(TIER_A_SYMBOLS)}",
            f"**Events**: {report['n_events']}",
            "",
            f"## Conclusion: {report['conclusion']}",
            "",
            "## Latency Sweep",
            "",
            "| Latency (ms) | N | Continuation (bps) | Half-Spread (bps) | Net (bps) | Hit Rate | Viable |",
            "|-------------|---|---------------------|-------------------|-----------|----------|--------|",
        ]
        for k, r in sorted(results.items()):
            lines.append(
                f"| {r.latency_ms} | {r.n_events} | {r.mean_continuation_bps:.2f} | "
                f"{r.mean_half_spread_bps:.2f} | {r.mean_net_bps:.2f} | "
                f"{r.hit_rate:.1%} | {'Yes' if r.viable else 'No'} |"
            )
        out.write_text("\n".join(lines))
        logger.info("Report: %s", out)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    tester = BranchACeiling()
    await tester.run()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
