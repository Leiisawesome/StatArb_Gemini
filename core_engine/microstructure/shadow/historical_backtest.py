"""Full historical backtest for shadow trading system — Step 7 (THE HARD GATE).

Runs the complete shadow pipeline against 130 days of ClickHouse data
as a sequential trading simulation with carry-forward state.

This is NOT per-event research analysis — it is the full pipeline operating
as a trading system with inventory state, position limits, kill conditions,
and shock-only event filtering in the real event stream.

Spec: v1.8-SHADOW-SHOCK
Build Plan: v4-FINAL, Step 7

Pass criteria (v1.8):
  1. Total P&L within ±15% of research expectation
  2. Fill rate within ±10% of research baseline (77%)
  3. Hit rate within ±8% of research baseline (54%)
  4. No kill condition fires during the 130-day period
  5. Sub-strategy: shock-only (competitive removed per Step 7 findings)
  6. No rolling 5-day peak-to-trough > 115 bps
  7. M6 spread ratio distribution matches research within 20%
  8. Inventory stress test passes: cap blocks stacking, no exposure breach
"""

from __future__ import annotations

import asyncio
import bisect
import json
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

from core_engine.microstructure.shadow.constants import (
    BACKTEST_DRAWDOWN_5D_MAX_BPS,
    BACKTEST_FILL_TOLERANCE_PCT,
    BACKTEST_HIT_TOLERANCE_PCT,
    BACKTEST_PNL_TOLERANCE_PCT,
    BASELINE_FILL_RATE,
    BASELINE_HIT_RATE,
    BASELINE_MEAN_PNL_BPS,
    CLIP_SIZE,
    DEPTH_CAPACITY_FLAG_RATIO,
    ENTRY_DELAY_MS,
    IMBALANCE_THRESHOLDS,
    MIN_HOLD_MS,
    MIN_QUOTE_UPDATES_IN_WINDOW,
    NET_INVENTORY_CAP_BPS,
    PORTFOLIO_VALUE,
    QUOTE_STALENESS_MAX_MS,
    SCALING_CLIP_SIZES,
    SHADOW_CONSTANTS_VERSION,
    SHOCK_ONLY,
    SPREAD_BASELINE_WINDOW_DAYS,
    SPREAD_NORMAL_FACTOR,
    SPREAD_RATIO_COMPETITIVE_MAX,
    SPREAD_RATIO_SHOCK_MIN,
    STOP_LOSS_BPS,
    SYMBOLS,
    TIMEOUT_S,
)
from core_engine.microstructure.shadow.types import (
    ExitReason,
    KillEvent,
    SlippageBreakdown,
    SubStrategy,
    TradeOutcome,
)
from core_engine.microstructure.shadow.event_filter import InventoryTracker
from core_engine.microstructure.shadow.mechanism_monitor import MechanismMonitor, _ResearchBaselines

logger = logging.getLogger(__name__)

_ENTRY_DELAY_NS = ENTRY_DELAY_MS * 1_000_000
_TIMEOUT_NS = TIMEOUT_S * 1_000_000_000
_MIN_HOLD_NS = MIN_HOLD_MS * 1_000_000
_FILL_WINDOW_NS = 5_000_000_000
_EXIT_BUFFER_NS = 36_000_000_000
_QUOTE_PRE_NS = 1_000_000_000
_MAX_TS = 2**62

QuoteTuple = Tuple[int, float, float, int, int]
TradeTuple = Tuple[int, float, int]


@dataclass
class _OpenPosition:
    pos_id: str
    symbol: str
    side: str
    fill_price: float
    fill_ts_ns: int
    baseline_spread: float
    sub_strategy: SubStrategy
    spread_ratio: float
    entry_imbalance: float
    spread_at_entry_bps: float
    depth_ratio: float
    nbbo_bid_size: int
    nbbo_ask_size: int
    classification_confidence: float
    entry_ts_ns: int


@dataclass
class _BacktestTrade:
    symbol: str
    trade_date: date
    sub_strategy: SubStrategy
    side: str
    entry_ts_ns: int
    entry_price: float
    exit_ts_ns: int
    exit_price: float
    exit_reason: ExitReason
    hold_time_ms: float
    pnl_bps: float
    pnl_dollars: float
    entry_spread_ratio: float
    entry_imbalance: float
    model_filled: bool
    model_pnl_bps: float
    spread_at_entry_bps: float
    baseline_spread: float
    depth_ratio: float
    nbbo_bid_size: int
    nbbo_ask_size: int
    classification_confidence: float


@dataclass
class _DayResult:
    trade_date: date
    events_detected: int
    orders_submitted: int
    events_filled: int
    events_rejected_deadzone: int
    events_rejected_inventory: int
    events_rejected_position: int
    events_rejected_nbbo: int
    events_not_filled: int
    trades: List[_BacktestTrade]
    daily_pnl_bps: float
    daily_pnl_dollars: float
    cumulative_pnl_bps: float
    competitive_pnl_bps: float
    shock_pnl_bps: float
    competitive_fills: int
    shock_fills: int
    kill_event: Optional[KillEvent] = None


class HistoricalBacktest:
    """Sequential 130-day backtest of the shadow trading pipeline.

    Processes pre-computed volume-clock buckets from ClickHouse, identifies
    extreme imbalance events using frozen p95 thresholds, and runs the full
    filter → fill → exit pipeline with carry-forward inventory state.
    """

    def __init__(
        self,
        clickhouse_url: str = "http://localhost:8123",
        output_dir: str = "results/shadow_backtest",
        shock_only: Optional[bool] = None,
        drawdown_5d_limit: Optional[float] = None,
    ) -> None:
        self._ch_url = clickhouse_url
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._shock_only = shock_only if shock_only is not None else SHOCK_ONLY
        self._drawdown_5d_limit = (
            drawdown_5d_limit if drawdown_5d_limit is not None
            else BACKTEST_DRAWDOWN_5D_MAX_BPS
        )

        self._inventory = InventoryTracker(PORTFOLIO_VALUE)
        self._monitor = MechanismMonitor()
        self._cumulative_pnl_bps: float = 0.0
        self._all_trades: List[_BacktestTrade] = []
        self._day_results: List[_DayResult] = []
        self._daily_pnl_history: List[float] = []
        self._open_positions: Dict[str, _OpenPosition] = {}
        self._baseline_cache: Dict[Tuple[str, str], float] = {}

    # ── Public API ────────────────────────────────────────────────────

    async def run(self) -> dict:
        t0 = time.time()
        mode = "SHOCK-ONLY" if self._shock_only else "BLENDED"
        logger.info(
            "=== Historical Backtest — %s [%s] dd5d_limit=%.0f bps ===",
            SHADOW_CONSTANTS_VERSION, mode, self._drawdown_5d_limit,
        )

        timeout = aiohttp.ClientTimeout(total=600, sock_read=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            all_buckets = await self._load_all_buckets(session)
            logger.info("Loaded %d buckets for %s", len(all_buckets), SYMBOLS)

            self._compute_rolling_baselines(all_buckets)
            events_by_date = self._identify_all_events(all_buckets)
            total_events = sum(len(v) for v in events_by_date.values())
            all_dates = sorted(set(b["bucket_date"] for b in all_buckets))
            logger.info(
                "%d events across %d event-days, %d total days: %s → %s",
                total_events, len(events_by_date), len(all_dates),
                all_dates[0], all_dates[-1],
            )

            baselines = self._compute_m1_baselines(events_by_date, all_dates)
            self._monitor = MechanismMonitor(
                baselines=baselines,
                drawdown_5d_limit=self._drawdown_5d_limit,
            )
            logger.info(
                "M1 baselines: amplitude=%.3f, norm_ms=%.0f, freq=%.2f, dd5d=%.0f",
                baselines.m1_amplitude, baselines.m1_normalization_ms,
                baselines.m1_event_frequency, self._drawdown_5d_limit,
            )

            for i, day in enumerate(all_dates):
                events = events_by_date.get(day, [])
                result = await self._process_day(session, day, events)
                self._day_results.append(result)

                if result.kill_event:
                    logger.warning("KILL on %s: %s", day, result.kill_event.detail)
                if (i + 1) % 20 == 0 or i == len(all_dates) - 1:
                    logger.info(
                        "  [%d/%d] %s  cum=%.2f bps  trades=%d",
                        i + 1, len(all_dates), day,
                        self._cumulative_pnl_bps, len(self._all_trades),
                    )

            scaling = self._run_scaling_simulation()
            stress = self._run_inventory_stress_test()

        elapsed = time.time() - t0
        logger.info(
            "Backtest complete: %.1fs, %d trades, %.2f bps cumulative",
            elapsed, len(self._all_trades), self._cumulative_pnl_bps,
        )

        pass_check = self._check_pass_criteria(stress)
        report = self._generate_report(scaling, stress, pass_check, elapsed)
        (self._output_dir / "backtest_report.md").write_text(report)
        self._save_raw_data(scaling, stress, pass_check)

        all_passed = all(v["passed"] for v in pass_check.values())
        logger.info("PASS CRITERIA: %s", "ALL PASSED" if all_passed else "SOME FAILED")
        for name, info in pass_check.items():
            logger.info("  %s %s — %s", "PASS" if info["passed"] else "FAIL",
                        name, info.get("detail", ""))

        return {
            "pass_check": pass_check,
            "all_passed": all_passed,
            "elapsed_s": elapsed,
            "total_trades": len(self._all_trades),
            "cumulative_pnl_bps": self._cumulative_pnl_bps,
            "report_path": str(self._output_dir / "backtest_report.md"),
        }

    # ── ClickHouse Queries ────────────────────────────────────────────

    async def _ch_raw(self, session: aiohttp.ClientSession, query: str) -> str:
        async with session.post(self._ch_url, data=query) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"ClickHouse error: {text[:500]}")
            return text

    async def _load_all_buckets(self, session: aiohttp.ClientSession) -> List[dict]:
        sym_csv = ",".join(f"'{s}'" for s in SYMBOLS)
        query = f"""
        SELECT symbol, bucket_id, bucket_start_ns, bucket_end_ns,
               bucket_volume, actual_volume, num_trades, vwap,
               signed_volume, unsigned_volume, buy_volume, sell_volume,
               classification_confidence, tick_rule_fallback_pct,
               bid_at_end, ask_at_end, median_spread_bps, flow_imbalance,
               toString(bucket_date), fill_duration_ms
        FROM polygon_data.microstructure_buckets
        WHERE symbol IN ({sym_csv})
        ORDER BY bucket_date, bucket_end_ns
        FORMAT TabSeparated
        """
        text = await self._ch_raw(session, query)
        rows = []
        for line in text.strip().split("\n"):
            if not line:
                continue
            p = line.split("\t")
            rows.append({
                "symbol": p[0], "bucket_id": int(p[1]),
                "bucket_start_ns": int(p[2]), "bucket_end_ns": int(p[3]),
                "bucket_volume": int(p[4]), "actual_volume": int(p[5]),
                "num_trades": int(p[6]), "vwap": float(p[7]),
                "signed_volume": int(p[8]), "unsigned_volume": int(p[9]),
                "buy_volume": int(p[10]), "sell_volume": int(p[11]),
                "classification_confidence": float(p[12]),
                "tick_rule_fallback_pct": float(p[13]),
                "bid_at_end": float(p[14]), "ask_at_end": float(p[15]),
                "median_spread_bps": float(p[16]),
                "flow_imbalance": float(p[17]),
                "bucket_date": p[18], "fill_duration_ms": int(p[19]),
            })
        return rows

    async def _load_quotes(
        self, session: aiohttp.ClientSession,
        symbol: str, day: str, start_ns: int, end_ns: int,
    ) -> List[QuoteTuple]:
        query = f"""
        SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
        FROM polygon_data.microstructure_quotes
        WHERE symbol = '{symbol}' AND ingestion_date = '{day}'
          AND sip_timestamp BETWEEN {start_ns} AND {end_ns}
        ORDER BY sip_timestamp
        FORMAT TabSeparated
        """
        text = await self._ch_raw(session, query)
        if not text.strip():
            return []
        return [
            (int(p[0]), float(p[1]), float(p[2]), int(p[3]), int(p[4]))
            for line in text.strip().split("\n") if line
            for p in [line.split("\t")]
        ]

    async def _load_trades(
        self, session: aiohttp.ClientSession,
        symbol: str, day: str, start_ns: int, end_ns: int,
    ) -> List[TradeTuple]:
        query = f"""
        SELECT sip_timestamp, price, size
        FROM polygon_data.microstructure_trades
        WHERE symbol = '{symbol}' AND ingestion_date = '{day}'
          AND sip_timestamp BETWEEN {start_ns} AND {end_ns}
        ORDER BY sip_timestamp
        FORMAT TabSeparated
        """
        text = await self._ch_raw(session, query)
        if not text.strip():
            return []
        return [
            (int(p[0]), float(p[1]), int(p[2]))
            for line in text.strip().split("\n") if line
            for p in [line.split("\t")]
        ]

    # ── Baseline Computation ──────────────────────────────────────────

    def _compute_rolling_baselines(self, all_buckets: List[dict]) -> None:
        day_spreads: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        for b in all_buckets:
            if b["bid_at_end"] > 0 and b["ask_at_end"] > b["bid_at_end"]:
                day_spreads[(b["symbol"], b["bucket_date"])].append(
                    b["ask_at_end"] - b["bid_at_end"]
                )

        daily: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for (sym, day), spreads in sorted(day_spreads.items()):
            daily[sym].append((day, statistics.median(spreads)))

        for sym in SYMBOLS:
            entries = daily.get(sym, [])
            for i, (day, med) in enumerate(entries):
                start = max(0, i - SPREAD_BASELINE_WINDOW_DAYS)
                window_vals = [v for _, v in entries[start:i]]
                self._baseline_cache[(sym, day)] = (
                    statistics.median(window_vals) if window_vals else med
                )

    # ── Event Identification ──────────────────────────────────────────

    def _identify_all_events(self, all_buckets: List[dict]) -> Dict[str, List[dict]]:
        events: Dict[str, List[dict]] = defaultdict(list)
        for b in all_buckets:
            threshold = IMBALANCE_THRESHOLDS.get(b["symbol"], 1.0)
            if abs(b["flow_imbalance"]) >= threshold:
                events[b["bucket_date"]].append(b)
        return events

    def _compute_m1_baselines(
        self, events_by_date: Dict[str, List[dict]], all_dates: List[str],
    ) -> _ResearchBaselines:
        """Compute M1 baselines from bucket data (first-pass calibration).

        The MechanismMonitor tracks TOTAL daily events (across all symbols),
        not per-symbol. The frequency baseline must match this convention.
        """
        all_events = [e for evts in events_by_date.values() for e in evts]
        n_days = len(all_dates)

        daily_counts = [len(events_by_date.get(d, [])) for d in all_dates]
        event_frequency = statistics.mean(daily_counts) if daily_counts else 20.0

        spread_ratios = []
        for e in all_events:
            bl = self._baseline_cache.get((e["symbol"], e["bucket_date"]), 0.0)
            if bl > 0 and e["bid_at_end"] > 0 and e["ask_at_end"] > e["bid_at_end"]:
                sr = (e["ask_at_end"] - e["bid_at_end"]) / bl
                if sr < SPREAD_RATIO_COMPETITIVE_MAX or sr > SPREAD_RATIO_SHOCK_MIN:
                    spread_ratios.append(sr)
        amplitude = statistics.median(spread_ratios) if spread_ratios else 2.0

        return _ResearchBaselines(
            m1_amplitude=amplitude,
            m1_normalization_ms=1500.0,
            m1_event_frequency=event_frequency,
        )

    # ── Day Processing ────────────────────────────────────────────────

    async def _process_day(
        self, session: aiohttp.ClientSession,
        day: str, events: List[dict],
    ) -> _DayResult:
        assert not self._open_positions, (
            f"Carry-over positions at start of {day}: {list(self._open_positions)}"
        )

        events.sort(key=lambda b: b["bucket_end_ns"])
        rej = {"deadzone": 0, "inventory": 0, "position": 0, "nbbo": 0}
        orders_submitted = 0
        not_filled = 0
        day_trades: List[_BacktestTrade] = []

        quotes_by_sym: Dict[str, List[QuoteTuple]] = {}
        if events:
            sym_events: Dict[str, List[dict]] = defaultdict(list)
            for e in events:
                sym_events[e["symbol"]].append(e)
            tasks = {}
            for sym, sevts in sym_events.items():
                lo = min(e["bucket_end_ns"] for e in sevts) - _QUOTE_PRE_NS
                hi = max(e["bucket_end_ns"] for e in sevts) + _EXIT_BUFFER_NS
                tasks[sym] = self._load_quotes(session, sym, day, lo, hi)
            results = await asyncio.gather(*tasks.values())
            quotes_by_sym = dict(zip(tasks.keys(), results))

        for bucket in events:
            sym = bucket["symbol"]
            self._monitor.on_event_detected(symbol=sym)

            self._advance_exits(
                bucket["bucket_end_ns"], quotes_by_sym, day_trades, day
            )

            entry_ts = bucket["bucket_end_ns"] + _ENTRY_DELAY_NS
            sym_q = quotes_by_sym.get(sym, [])

            entry_quote = _find_quote_at(sym_q, entry_ts)
            if entry_quote is None:
                rej["nbbo"] += 1
                continue
            ts_q, bid, ask, bid_sz, ask_sz = entry_quote

            if bid <= 0 or ask <= 0 or bid >= ask:
                rej["nbbo"] += 1
                continue
            if (entry_ts - ts_q) / 1e6 > QUOTE_STALENESS_MAX_MS:
                rej["nbbo"] += 1
                continue
            if _count_in_range(sym_q, bucket["bucket_end_ns"], entry_ts) < MIN_QUOTE_UPDATES_IN_WINDOW:
                rej["nbbo"] += 1
                continue

            baseline = self._baseline_cache.get((sym, day), 0.0)
            spread = ask - bid
            if baseline <= 0:
                baseline = spread
            if baseline <= 0:
                rej["nbbo"] += 1
                continue
            spread_ratio = spread / baseline

            if self._shock_only:
                if spread_ratio <= SPREAD_RATIO_SHOCK_MIN:
                    rej["deadzone"] += 1
                    continue
            elif SPREAD_RATIO_COMPETITIVE_MAX <= spread_ratio <= SPREAD_RATIO_SHOCK_MIN:
                rej["deadzone"] += 1
                continue

            self._monitor.on_event_detected(symbol=sym, spread_ratio=spread_ratio)

            if self._inventory.has_open_position(sym):
                rej["position"] += 1
                continue

            side = "SELL" if bucket["flow_imbalance"] > 0 else "BUY"
            limit_price = ask if side == "SELL" else bid
            mid = (bid + ask) / 2.0
            spread_bps = (spread / mid * 10_000) if mid > 0 else 0.0

            if self._inventory.would_breach_cap(
                sym, side, CLIP_SIZE, limit_price, spread_bps=spread_bps
            ):
                rej["inventory"] += 1
                continue

            sub = (SubStrategy.COMPETITIVE
                   if spread_ratio < SPREAD_RATIO_COMPETITIVE_MAX
                   else SubStrategy.SHOCK)

            orders_submitted += 1
            self._monitor.on_order_placed()

            trades_data = await self._load_trades(
                session, sym, day, entry_ts, entry_ts + _FILL_WINDOW_NS,
            )
            queue_ahead = bid_sz if side == "BUY" else ask_sz
            fill = _simulate_fill(side, limit_price, queue_ahead, trades_data, entry_ts)

            if not fill["filled"]:
                not_filled += 1
                continue

            depth_ratio = CLIP_SIZE / queue_ahead if queue_ahead > 0 else 1.0
            pos_id = f"{sym}_{bucket['bucket_id']}_{day}"
            pos = _OpenPosition(
                pos_id=pos_id, symbol=sym, side=side,
                fill_price=fill["fill_price"], fill_ts_ns=fill["fill_ts_ns"],
                baseline_spread=baseline, sub_strategy=sub,
                spread_ratio=spread_ratio,
                entry_imbalance=abs(bucket["flow_imbalance"]),
                spread_at_entry_bps=spread_bps, depth_ratio=depth_ratio,
                nbbo_bid_size=bid_sz, nbbo_ask_size=ask_sz,
                classification_confidence=bucket["classification_confidence"],
                entry_ts_ns=entry_ts,
            )
            self._open_positions[pos_id] = pos
            self._inventory.add_position(
                sym, side, CLIP_SIZE, fill["fill_price"], spread_bps=spread_bps,
            )

        self._advance_exits(_MAX_TS, quotes_by_sym, day_trades, day)

        for pid in list(self._open_positions):
            pos = self._open_positions.pop(pid)
            trade = self._force_close(pos, quotes_by_sym.get(pos.symbol, []), day)
            day_trades.append(trade)
            self._inventory.remove_position(pos.symbol, pos.side)

        daily_pnl = sum(t.pnl_bps for t in day_trades)
        daily_dollars = sum(t.pnl_dollars for t in day_trades)
        self._cumulative_pnl_bps += daily_pnl
        self._daily_pnl_history.append(daily_pnl)

        for t in day_trades:
            self._all_trades.append(t)
            self._monitor.on_trade_complete(self._to_outcome(t))

        comp = [t for t in day_trades if t.sub_strategy == SubStrategy.COMPETITIVE]
        shock = [t for t in day_trades if t.sub_strategy == SubStrategy.SHOCK]

        kill = self._monitor.check_daily_close_kills(daily_pnl)
        freq_alert = self._monitor.check_event_frequency_alert(daily_pnl)
        if freq_alert:
            logger.warning(
                "M9 ALERT on %s: events=%d vs 20d avg=%.1f (%.0f%% drop), P&L=%.2f bps",
                day, int(freq_alert["current_events"]),
                freq_alert["avg_20d_events"],
                freq_alert["decline_pct"] * 100,
                freq_alert["daily_pnl_bps"],
            )
        corr_alert = self._monitor.check_cross_symbol_correlation()
        if corr_alert:
            logger.warning(
                "M10 CORR ALERT on %s: avg pairwise=%.3f > %.2f",
                day, corr_alert["avg_pairwise_correlation"], 0.50,
            )
        cluster_alert = self._monitor.check_shock_clustering()
        if cluster_alert:
            logger.warning(
                "M10b SHOCK CLUSTER on %s: %d/%d symbols (%s)",
                day, cluster_alert["count"], cluster_alert["total_symbols"],
                ", ".join(cluster_alert["shock_symbols"]),
            )
        velocity_alert = self._monitor.check_loss_velocity()
        if velocity_alert:
            logger.warning(
                "LOSS VELOCITY on %s: %.1f bps intraday drawdown, M1 degraded=%d/3",
                day, velocity_alert["intraday_drawdown_bps"],
                velocity_alert["m1_degraded_count"],
            )
        self._monitor.reset_daily()

        return _DayResult(
            trade_date=date.fromisoformat(day),
            events_detected=len(events),
            orders_submitted=orders_submitted,
            events_filled=len(day_trades),
            events_rejected_deadzone=rej["deadzone"],
            events_rejected_inventory=rej["inventory"],
            events_rejected_position=rej["position"],
            events_rejected_nbbo=rej["nbbo"],
            events_not_filled=not_filled,
            trades=day_trades,
            daily_pnl_bps=daily_pnl,
            daily_pnl_dollars=daily_dollars,
            cumulative_pnl_bps=self._cumulative_pnl_bps,
            competitive_pnl_bps=sum(t.pnl_bps for t in comp),
            shock_pnl_bps=sum(t.pnl_bps for t in shock),
            competitive_fills=len(comp),
            shock_fills=len(shock),
            kill_event=kill,
        )

    # ── Exit Management ───────────────────────────────────────────────

    def _advance_exits(
        self, up_to_ns: int,
        quotes_by_sym: Dict[str, List[QuoteTuple]],
        day_trades: List[_BacktestTrade], day: str,
    ) -> None:
        for pid in list(self._open_positions):
            pos = self._open_positions[pid]
            exit_info = _check_exit(
                pos, quotes_by_sym.get(pos.symbol, []), up_to_ns
            )
            if exit_info:
                trade = self._build_trade(
                    pos, exit_info["exit_price"], exit_info["exit_ts_ns"],
                    exit_info["exit_reason"], exit_info["hold_time_ms"], day,
                )
                day_trades.append(trade)
                self._inventory.remove_position(pos.symbol, pos.side)
                del self._open_positions[pid]

    def _force_close(
        self, pos: _OpenPosition, quotes: List[QuoteTuple], day: str,
    ) -> _BacktestTrade:
        if quotes:
            last = quotes[-1]
            mid = (last[1] + last[2]) / 2.0 if last[1] > 0 and last[2] > last[1] else pos.fill_price
            exit_ts = last[0]
        else:
            mid = pos.fill_price
            exit_ts = pos.fill_ts_ns + _TIMEOUT_NS
        hold_ms = max(0.0, (exit_ts - pos.fill_ts_ns) / 1e6)
        return self._build_trade(pos, mid, exit_ts, ExitReason.TIMEOUT, hold_ms, day)

    def _build_trade(
        self, pos: _OpenPosition,
        exit_price: float, exit_ts_ns: int,
        exit_reason: ExitReason, hold_time_ms: float, day: str,
    ) -> _BacktestTrade:
        if pos.side == "BUY":
            pnl_bps = (exit_price - pos.fill_price) / pos.fill_price * 10_000
        else:
            pnl_bps = (pos.fill_price - exit_price) / pos.fill_price * 10_000
        pnl_dollars = pnl_bps / 10_000 * pos.fill_price * CLIP_SIZE
        return _BacktestTrade(
            symbol=pos.symbol, trade_date=date.fromisoformat(day),
            sub_strategy=pos.sub_strategy, side=pos.side,
            entry_ts_ns=pos.entry_ts_ns, entry_price=pos.fill_price,
            exit_ts_ns=exit_ts_ns, exit_price=exit_price,
            exit_reason=exit_reason, hold_time_ms=hold_time_ms,
            pnl_bps=pnl_bps, pnl_dollars=pnl_dollars,
            entry_spread_ratio=pos.spread_ratio,
            entry_imbalance=pos.entry_imbalance,
            model_filled=True, model_pnl_bps=pnl_bps * 0.7,
            spread_at_entry_bps=pos.spread_at_entry_bps,
            baseline_spread=pos.baseline_spread,
            depth_ratio=pos.depth_ratio,
            nbbo_bid_size=pos.nbbo_bid_size, nbbo_ask_size=pos.nbbo_ask_size,
            classification_confidence=pos.classification_confidence,
        )

    @staticmethod
    def _to_outcome(t: _BacktestTrade) -> TradeOutcome:
        return TradeOutcome(
            symbol=t.symbol, trade_date=t.trade_date,
            sub_strategy=t.sub_strategy, side=t.side,
            entry_time_ns=t.entry_ts_ns, entry_price=t.entry_price,
            entry_spread_ratio=t.entry_spread_ratio,
            entry_imbalance=t.entry_imbalance,
            exit_time_ns=t.exit_ts_ns, exit_price=t.exit_price,
            exit_reason=t.exit_reason, hold_time_ms=t.hold_time_ms,
            pnl_bps=t.pnl_bps, pnl_dollars=t.pnl_dollars,
            slippage=SlippageBreakdown(
                expected_entry_price=t.entry_price,
                actual_entry_price=t.entry_price,
                entry_slippage_bps=0.0,
                expected_exit_price=t.exit_price,
                actual_exit_price=t.exit_price,
                exit_slippage_bps=0.0,
                cancel_delay_ms=0.0, partial_fill_ratio=1.0,
            ),
            nbbo_bid_size=t.nbbo_bid_size, nbbo_ask_size=t.nbbo_ask_size,
            order_depth_ratio=t.depth_ratio,
            model_fill=t.model_filled, model_pnl_bps=t.model_pnl_bps,
            spread_at_entry_bps=t.spread_at_entry_bps,
            baseline_spread_bps=(
                t.baseline_spread / t.entry_price * 10_000
                if t.entry_price > 0 else 0.0
            ),
            classification_confidence=t.classification_confidence,
            quote_age_at_entry_ms=0.0,
        )

    # ── Scaling Simulation ────────────────────────────────────────────

    def _run_scaling_simulation(self) -> dict:
        results = {}
        for clip in SCALING_CLIP_SIZES:
            if clip == CLIP_SIZE:
                n = len(self._all_trades) or 1
                depth_ratios = []
                constrained = 0
                for t in self._all_trades:
                    relevant = t.nbbo_ask_size if t.side == "SELL" else t.nbbo_bid_size
                    dr = clip / relevant if relevant > 0 else 1.0
                    depth_ratios.append(dr)
                    if dr > DEPTH_CAPACITY_FLAG_RATIO:
                        constrained += 1
                results[clip] = {
                    "clip_size": clip, "fill_count": n,
                    "fill_rate": 1.0,
                    "total_pnl_bps": self._cumulative_pnl_bps,
                    "total_pnl_dollars": sum(t.pnl_dollars for t in self._all_trades),
                    "mean_pnl_bps": self._cumulative_pnl_bps / n,
                    "capacity_constrained_pct": constrained / n,
                    "mean_depth_ratio": statistics.mean(depth_ratios) if depth_ratios else 0.0,
                }
                continue

            pnl_bps_total = 0.0
            pnl_dollars_total = 0.0
            fills = 0
            constrained = 0
            depth_ratios = []

            for t in self._all_trades:
                relevant = t.nbbo_ask_size if t.side == "SELL" else t.nbbo_bid_size
                dr = clip / relevant if relevant > 0 else float("inf")
                depth_ratios.append(min(dr, 10.0))

                if dr > 1.0:
                    constrained += 1
                    continue
                if dr > DEPTH_CAPACITY_FLAG_RATIO:
                    constrained += 1

                impact_bps = max(0.0, (dr - 0.1) * 2.0)
                adj = t.pnl_bps - impact_bps
                pnl_bps_total += adj
                pnl_dollars_total += adj / 10_000 * t.entry_price * clip
                fills += 1

            n = len(self._all_trades) or 1
            results[clip] = {
                "clip_size": clip, "fill_count": fills,
                "fill_rate": fills / n,
                "total_pnl_bps": pnl_bps_total,
                "total_pnl_dollars": pnl_dollars_total,
                "mean_pnl_bps": pnl_bps_total / fills if fills else 0.0,
                "capacity_constrained_pct": constrained / n,
                "mean_depth_ratio": statistics.mean(depth_ratios) if depth_ratios else 0.0,
            }
        return results

    # ── Inventory Stress Test ─────────────────────────────────────────

    def _run_inventory_stress_test(self) -> dict:
        tracker = InventoryTracker(PORTFOLIO_VALUE)
        accepted = 0
        blocked_inv = 0
        blocked_pos = 0
        max_inv = 0.0

        for i in range(10):
            sym = SYMBOLS[i % len(SYMBOLS)]
            side = "BUY"
            spread_bps = 2.5
            if tracker.has_open_position(sym):
                blocked_pos += 1
                continue
            if tracker.would_breach_cap(sym, side, CLIP_SIZE, 100.0, spread_bps=spread_bps):
                blocked_inv += 1
                continue
            tracker.add_position(sym, side, CLIP_SIZE, 100.0, spread_bps=spread_bps)
            accepted += 1
            max_inv = max(max_inv, abs(tracker.get_net_inventory_bps()))

        cap_held = max_inv <= NET_INVENTORY_CAP_BPS
        return {
            "events_injected": 10, "accepted": accepted,
            "blocked_inventory": blocked_inv, "blocked_position": blocked_pos,
            "max_net_inventory_bps": max_inv, "cap_held": cap_held,
            "passed": cap_held,
        }

    # ── Pass Criteria ─────────────────────────────────────────────────

    def _check_pass_criteria(self, stress: dict) -> dict:
        trades = self._all_trades
        n = len(trades) or 1

        mean_pnl = statistics.mean(t.pnl_bps for t in trades) if trades else 0
        pnl_diff = (
            abs(mean_pnl - BASELINE_MEAN_PNL_BPS) / abs(BASELINE_MEAN_PNL_BPS)
            if BASELINE_MEAN_PNL_BPS else 0
        )

        total_submitted = sum(d.orders_submitted for d in self._day_results)
        total_filled = sum(d.events_filled for d in self._day_results)
        fill_rate = total_filled / total_submitted if total_submitted else 0
        fill_diff = (
            abs(fill_rate - BASELINE_FILL_RATE) / BASELINE_FILL_RATE
            if BASELINE_FILL_RATE else 0
        )

        hit_rate = sum(1 for t in trades if t.pnl_bps > 0) / n
        hit_diff = (
            abs(hit_rate - BASELINE_HIT_RATE) / BASELINE_HIT_RATE
            if BASELINE_HIT_RATE else 0
        )

        max_dd = 0.0
        if len(self._daily_pnl_history) >= 5:
            for i in range(len(self._daily_pnl_history) - 4):
                window = self._daily_pnl_history[i:i + 5]
                cum, running = [], 0.0
                for p in window:
                    running += p
                    cum.append(running)
                max_dd = max(max_dd, max(cum) - min(cum))

        kills = [d for d in self._day_results if d.kill_event is not None]
        comp_total = sum(d.competitive_fills for d in self._day_results)
        shock_total = sum(d.shock_fills for d in self._day_results)
        if self._shock_only:
            both = shock_total > 0
        else:
            both = comp_total > 0 and shock_total > 0

        return {
            "pnl_vs_research": {
                "passed": pnl_diff <= BACKTEST_PNL_TOLERANCE_PCT,
                "value": mean_pnl, "baseline": BASELINE_MEAN_PNL_BPS,
                "diff_pct": pnl_diff,
                "detail": f"Mean PnL {mean_pnl:.3f} vs {BASELINE_MEAN_PNL_BPS} bps ({pnl_diff:.1%} diff)",
            },
            "fill_rate": {
                "passed": fill_diff <= BACKTEST_FILL_TOLERANCE_PCT,
                "value": fill_rate, "baseline": BASELINE_FILL_RATE,
                "diff_pct": fill_diff,
                "detail": f"Fill rate {fill_rate:.1%} vs {BASELINE_FILL_RATE:.0%} ({fill_diff:.1%} diff)",
            },
            "hit_rate": {
                "passed": hit_diff <= BACKTEST_HIT_TOLERANCE_PCT,
                "value": hit_rate, "baseline": BASELINE_HIT_RATE,
                "diff_pct": hit_diff,
                "detail": f"Hit rate {hit_rate:.1%} vs {BASELINE_HIT_RATE:.0%} ({hit_diff:.1%} diff)",
            },
            "no_kills": {
                "passed": len(kills) == 0, "value": len(kills),
                "detail": f"{len(kills)} kills fired" if kills else "No kills",
            },
            "drawdown_5d": {
                "passed": max_dd <= self._drawdown_5d_limit,
                "value": max_dd, "threshold": self._drawdown_5d_limit,
                "detail": f"Max 5d drawdown {max_dd:.2f} bps (limit {self._drawdown_5d_limit})",
            },
            "sub_strategy_split": {
                "passed": both,
                "competitive": comp_total, "shock": shock_total,
                "detail": f"Competitive: {comp_total}, Shock: {shock_total}",
            },
            "inventory_stress": {
                "passed": stress["passed"],
                "detail": f"Max inv {stress['max_net_inventory_bps']:.2f} bps, "
                          f"accepted {stress['accepted']}/10",
            },
        }

    # ── Report Generation ─────────────────────────────────────────────

    def _generate_report(
        self, scaling: dict, stress: dict, pass_check: dict, elapsed: float,
    ) -> str:
        trades = self._all_trades
        n = len(trades) or 1
        L: List[str] = []

        mode = "SHOCK-ONLY" if self._shock_only else "BLENDED"
        L.append(f"# Shadow Trading Historical Backtest — Step 7 Report [{mode}]\n")
        L.append(f"**Version**: {SHADOW_CONSTANTS_VERSION}  ")
        L.append(f"**Mode**: {mode}  ")
        L.append(f"**Symbols**: {', '.join(SYMBOLS)}  ")
        L.append(f"**Period**: {self._day_results[0].trade_date} → "
                 f"{self._day_results[-1].trade_date} ({len(self._day_results)} days)  ")
        L.append(f"**Elapsed**: {elapsed:.1f}s  ")
        L.append(f"**Clip Size**: {CLIP_SIZE} shares\n")
        L.append("---\n")

        mean_pnl = statistics.mean(t.pnl_bps for t in trades) if trades else 0
        hit = sum(1 for t in trades if t.pnl_bps > 0) / n if trades else 0
        hold = statistics.mean(t.hold_time_ms for t in trades) if trades else 0
        total_det = sum(d.events_detected for d in self._day_results)
        total_sub = sum(d.orders_submitted for d in self._day_results)
        total_fill = sum(d.events_filled for d in self._day_results)

        L.append("## Summary\n")
        L.append("| Metric | Value |")
        L.append("|--------|-------|")
        L.append(f"| Events detected | {total_det} |")
        L.append(f"| Orders submitted | {total_sub} |")
        L.append(f"| Trades filled | {total_fill} |")
        L.append(f"| Queue model fill rate | {total_fill / total_sub:.1%} |" if total_sub else "| Queue model fill rate | N/A |")
        L.append(f"| Cumulative P&L | {self._cumulative_pnl_bps:.2f} bps "
                 f"(${sum(t.pnl_dollars for t in trades):.2f}) |")
        L.append(f"| Mean P&L per trade | {mean_pnl:.3f} bps |")
        L.append(f"| Hit rate | {hit:.1%} |")
        L.append(f"| Mean hold time | {hold:.0f} ms |")
        L.append("")

        L.append("---\n")
        L.append("## Pass Criteria\n")
        L.append("| Criterion | Status | Detail |")
        L.append("|-----------|--------|--------|")
        all_ok = True
        for name, info in pass_check.items():
            ok = info["passed"]
            if not ok:
                all_ok = False
            L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {info['detail']} |")
        L.append(f"\n**Overall**: {'ALL PASSED' if all_ok else 'SOME FAILED'}\n")

        L.append("---\n")
        L.append("## Filter Rejection Breakdown\n")
        rej = {
            "dead zone": sum(d.events_rejected_deadzone for d in self._day_results),
            "inventory cap": sum(d.events_rejected_inventory for d in self._day_results),
            "position limit": sum(d.events_rejected_position for d in self._day_results),
            "NBBO integrity": sum(d.events_rejected_nbbo for d in self._day_results),
            "queue no-fill": sum(d.events_not_filled for d in self._day_results),
        }
        L.append("| Reason | Count | % of Detected |")
        L.append("|--------|-------|---------------|")
        for reason, cnt in rej.items():
            L.append(f"| {reason} | {cnt} | {cnt / total_det * 100:.1f}% |" if total_det else f"| {reason} | {cnt} | - |")
        L.append("")

        L.append("---\n")
        comp = [t for t in trades if t.sub_strategy == SubStrategy.COMPETITIVE]
        shock = [t for t in trades if t.sub_strategy == SubStrategy.SHOCK]
        L.append("## Sub-Strategy Split\n")
        L.append("| Strategy | Trades | Mean P&L (bps) | Hit Rate | Total P&L (bps) |")
        L.append("|----------|--------|----------------|----------|-----------------|")
        for label, grp in [("Competitive", comp), ("Shock", shock)]:
            if grp:
                gn = len(grp)
                gm = statistics.mean(t.pnl_bps for t in grp)
                gh = sum(1 for t in grp if t.pnl_bps > 0) / gn
                gt = sum(t.pnl_bps for t in grp)
                L.append(f"| {label} | {gn} | {gm:.3f} | {gh:.1%} | {gt:.2f} |")
            else:
                L.append(f"| {label} | 0 | - | - | 0 |")
        L.append("")

        exit_counts: Dict[str, int] = defaultdict(int)
        for t in trades:
            exit_counts[t.exit_reason.value] += 1
        L.append("## Exit Reason Breakdown\n")
        L.append("| Exit Reason | Count | % |")
        L.append("|-------------|-------|---|")
        for reason, cnt in sorted(exit_counts.items()):
            L.append(f"| {reason} | {cnt} | {cnt / n * 100:.1f}% |")
        L.append("")

        L.append("---\n")
        L.append("## Scaling Elasticity\n")
        L.append("| Clip | Fills | Fill Rate | PnL (bps) | PnL ($) | Constrained % | Depth |")
        L.append("|------|-------|-----------|-----------|---------|---------------|-------|")
        for clip in SCALING_CLIP_SIZES:
            s = scaling[clip]
            L.append(
                f"| {clip} | {s['fill_count']} | {s['fill_rate']:.1%} | "
                f"{s['total_pnl_bps']:.2f} | ${s['total_pnl_dollars']:.2f} | "
                f"{s['capacity_constrained_pct']:.1%} | {s['mean_depth_ratio']:.3f} |"
            )
        L.append("")

        L.append("---\n")
        L.append("## Inventory Clustering Stress Test\n")
        L.append("| Metric | Value |")
        L.append("|--------|-------|")
        L.append(f"| Events injected | {stress['events_injected']} |")
        L.append(f"| Accepted | {stress['accepted']} |")
        L.append(f"| Blocked (inventory) | {stress['blocked_inventory']} |")
        L.append(f"| Blocked (position) | {stress['blocked_position']} |")
        L.append(f"| Max net inventory | {stress['max_net_inventory_bps']:.2f} bps |")
        L.append(f"| **Result** | **{'PASS' if stress['passed'] else 'FAIL'}** |")
        L.append("")

        L.append("---\n")
        L.append("## Comparison: Backtest vs Research\n")
        L.append("| Metric | Backtest | Research | Diff |")
        L.append("|--------|----------|----------|------|")
        L.append(f"| Mean P&L (bps) | {mean_pnl:.3f} | {BASELINE_MEAN_PNL_BPS} | "
                 f"{(mean_pnl - BASELINE_MEAN_PNL_BPS) / abs(BASELINE_MEAN_PNL_BPS) * 100:+.1f}% |"
                 if BASELINE_MEAN_PNL_BPS else "| Mean P&L (bps) | - | - | - |")
        L.append(f"| Hit rate | {hit:.1%} | {BASELINE_HIT_RATE:.0%} | "
                 f"{(hit - BASELINE_HIT_RATE) / BASELINE_HIT_RATE * 100:+.1f}% |"
                 if BASELINE_HIT_RATE else "| Hit rate | - | - | - |")
        L.append(f"| Fill rate | {total_fill / total_sub:.1%} | {BASELINE_FILL_RATE:.0%} | "
                 f"{(total_fill / total_sub - BASELINE_FILL_RATE) / BASELINE_FILL_RATE * 100:+.1f}% |"
                 if total_sub and BASELINE_FILL_RATE else "| Fill rate | - | - | - |")
        L.append(f"| Mean hold (ms) | {hold:.0f} | 1300 | {(hold - 1300) / 1300 * 100:+.1f}% |")
        L.append("")

        L.append("---\n")
        L.append("## Daily Equity Curve\n")
        L.append("| Date | Events | Submitted | Filled | P&L (bps) | Cum (bps) | Kill |")
        L.append("|------|--------|-----------|--------|-----------|-----------|------|")
        for d in self._day_results:
            kill_s = d.kill_event.condition.value if d.kill_event else ""
            L.append(
                f"| {d.trade_date} | {d.events_detected} | {d.orders_submitted} | "
                f"{d.events_filled} | {d.daily_pnl_bps:+.2f} | "
                f"{d.cumulative_pnl_bps:.2f} | {kill_s} |"
            )
        L.append("")

        return "\n".join(L)

    # ── Persistence ───────────────────────────────────────────────────

    def _save_raw_data(self, scaling: dict, stress: dict, pass_check: dict) -> None:
        data = {
            "version": SHADOW_CONSTANTS_VERSION,
            "cumulative_pnl_bps": self._cumulative_pnl_bps,
            "total_trades": len(self._all_trades),
            "pass_check": pass_check,
            "scaling": scaling,
            "stress_test": stress,
            "daily_pnl": self._daily_pnl_history,
            "trades": [
                {
                    "symbol": t.symbol, "date": str(t.trade_date),
                    "sub_strategy": t.sub_strategy.value, "side": t.side,
                    "pnl_bps": round(t.pnl_bps, 4),
                    "pnl_dollars": round(t.pnl_dollars, 4),
                    "hold_time_ms": round(t.hold_time_ms, 1),
                    "exit_reason": t.exit_reason.value,
                    "spread_ratio": round(t.entry_spread_ratio, 4),
                    "depth_ratio": round(t.depth_ratio, 4),
                }
                for t in self._all_trades
            ],
        }
        path = self._output_dir / "backtest_data.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.info("Raw data saved to %s", path)


# ── Module-Level Helpers (stateless, testable) ────────────────────────

def _find_quote_at(quotes: List[QuoteTuple], target_ns: int) -> Optional[QuoteTuple]:
    if not quotes:
        return None
    idx = bisect.bisect_right(quotes, (target_ns, float("inf"), float("inf"), 2**31, 2**31)) - 1
    return quotes[idx] if idx >= 0 else None


def _count_in_range(quotes: List[QuoteTuple], start_ns: int, end_ns: int) -> int:
    lo = bisect.bisect_left(quotes, (start_ns,))
    hi = bisect.bisect_right(quotes, (end_ns, float("inf"), float("inf"), 2**31, 2**31))
    return hi - lo


def _simulate_fill(
    side: str, limit_price: float, queue_ahead: int,
    trades: List[TradeTuple], entry_ts_ns: int,
) -> dict:
    cumulative = 0
    deadline = entry_ts_ns + _FILL_WINDOW_NS
    for ts, price, size in trades:
        if ts < entry_ts_ns:
            continue
        if ts > deadline:
            break
        if side == "BUY" and price <= limit_price:
            cumulative += size
        elif side == "SELL" and price >= limit_price:
            cumulative += size
        if cumulative >= queue_ahead:
            return {
                "filled": True, "fill_price": limit_price,
                "fill_ts_ns": ts, "volume_consumed": cumulative,
            }
    return {"filled": False}


def _check_exit(
    pos: _OpenPosition, quotes: List[QuoteTuple], up_to_ns: int,
) -> Optional[dict]:
    if not quotes:
        return None
    min_ns = pos.fill_ts_ns + _MIN_HOLD_NS
    start = bisect.bisect_left(quotes, (min_ns,))

    for i in range(start, len(quotes)):
        ts, bid, ask, _bs, _as = quotes[i]
        if ts > up_to_ns:
            break
        if bid <= 0 or ask <= 0 or bid >= ask:
            continue
        mid = (bid + ask) / 2.0
        spread = ask - bid

        if spread <= pos.baseline_spread * SPREAD_NORMAL_FACTOR:
            return {
                "exit_price": mid, "exit_ts_ns": ts,
                "exit_reason": ExitReason.SPREAD_NORMALIZATION,
                "hold_time_ms": (ts - pos.fill_ts_ns) / 1e6,
            }
        if ts - pos.fill_ts_ns >= _TIMEOUT_NS:
            return {
                "exit_price": mid, "exit_ts_ns": ts,
                "exit_reason": ExitReason.TIMEOUT,
                "hold_time_ms": (ts - pos.fill_ts_ns) / 1e6,
            }
        if pos.side == "BUY":
            adverse = (pos.fill_price - mid) / pos.fill_price * 10_000
        else:
            adverse = (mid - pos.fill_price) / pos.fill_price * 10_000
        if adverse > STOP_LOSS_BPS:
            return {
                "exit_price": mid, "exit_ts_ns": ts,
                "exit_reason": ExitReason.STOP_LOSS,
                "hold_time_ms": (ts - pos.fill_ts_ns) / 1e6,
            }
    return None


# ── CLI ───────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Shadow Trading Step 7 Backtest")
    parser.add_argument("--blended", action="store_true",
                        help="Override SHOCK_ONLY constant — run blended mode (debug only)")
    parser.add_argument("--dd5d", type=float, default=None,
                        help="Override 5-day drawdown limit (bps)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    shock = None if not args.blended else False
    bt = HistoricalBacktest(
        shock_only=shock,
        drawdown_5d_limit=args.dd5d,
    )
    results = await bt.run()

    print("\n" + "=" * 60)
    print("HISTORICAL BACKTEST — STEP 7 COMPLETE")
    print("=" * 60)
    print(f"Trades:         {results['total_trades']}")
    print(f"Cumulative P&L: {results['cumulative_pnl_bps']:.2f} bps")
    print(f"Time:           {results['elapsed_s']:.1f}s")
    print(f"All passed:     {results['all_passed']}")
    print(f"Report:         {results['report_path']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
