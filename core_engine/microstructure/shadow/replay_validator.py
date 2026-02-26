"""Step 8: Historical Replay Validation.

Proves the streaming bucketer produces identical results to the offline
pipeline that Step 7 used. Three validation stages:

  8A — Bucket boundary match: clean replay (20 symbol-days)
  8B — IID stress mode: jitter, duplicates, drops
  8B2 — Adversarial burst replay: freeze, deep reorder, quote/trade desync
  8C — Lee-Ready classification drift: segmented by symbol, TOD, spread regime

If streaming diverges from offline, live trading will detect different
events than the backtest validated. This is the truth anchor.

Spec: v1.8-SHADOW-SHOCK
Build Plan: v3-FINAL, Step 8
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import numpy as np

from core_engine.microstructure.shadow.constants import (
    ADV_SHARES,
    IMBALANCE_THRESHOLDS,
    REPLAY_BURST_FREEZE_MS,
    REPLAY_BURST_FREEZE_PCT,
    REPLAY_DEEP_REORDER_MS,
    REPLAY_DEEP_REORDER_PCT,
    REPLAY_IMBALANCE_DIVERGENCE_MAX_PCT,
    REPLAY_LR_DRIFT_HARD_PASS_PCT,
    REPLAY_LR_DRIFT_INVESTIGATE_PCT,
    REPLAY_LR_DRIFT_SEGMENT_THRESHOLD,
    REPLAY_QUOTE_TRADE_DESYNC_MS,
    REPLAY_QUOTE_TRADE_DESYNC_PCT,
    REPLAY_STRESS_DROP_PCT,
    REPLAY_STRESS_DUPLICATE_PCT,
    REPLAY_STRESS_JITTER_MS,
    SHADOW_CONSTANTS_VERSION,
    SYMBOLS,
    TARGET_BUCKETS_PER_DAY,
)
from core_engine.microstructure.classification.lee_ready import (
    NON_REGULAR_CONDITIONS,
)
from core_engine.microstructure.shadow.streaming_bucketer import (
    StreamingLeeReady,
)

_NON_REGULAR_CSV = ",".join(str(c) for c in sorted(NON_REGULAR_CONDITIONS))

logger = logging.getLogger(__name__)

TradeTuple = Tuple[int, float, int]           # (sip_timestamp, price, size)
QuoteTuple = Tuple[int, float, float, int, int]  # (sip_ts, bid, ask, bid_sz, ask_sz)

_SEED = 42


@dataclass
class _BucketRecord:
    bucket_id: int
    start_ns: int
    end_ns: int
    volume: int
    flow_imbalance: float
    num_trades: int
    buy_volume: int
    sell_volume: int
    classification_confidence: float
    tick_rule_fallback_pct: float


@dataclass
class _SymbolDayResult:
    symbol: str
    day: str
    offline_buckets: int
    streaming_buckets: int
    boundary_matches: int
    imbalance_divergences: List[float]
    event_count_offline: int
    event_count_streaming: int
    lr_drift_pct: float
    lr_by_tod: Dict[str, float] = field(default_factory=dict)
    lr_by_spread_regime: Dict[str, float] = field(default_factory=dict)


@dataclass
class _StressResult:
    mode: str
    symbol: str
    day: str
    bucket_shifts: int
    imbalance_div_pct: float
    event_count_clean: int
    event_count_stressed: int
    phantom_buckets: int
    nbbo_rejection_increase: int


# =====================================================================
# ClickHouse data loading
# =====================================================================

async def _ch_raw(session: aiohttp.ClientSession, url: str, query: str) -> str:
    async with session.post(url, data=query) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"ClickHouse error: {text[:500]}")
        return text


async def _load_offline_buckets(
    session: aiohttp.ClientSession, url: str,
    symbol: str, day: str,
) -> List[_BucketRecord]:
    query = f"""
    SELECT bucket_id, bucket_start_ns, bucket_end_ns,
           actual_volume, flow_imbalance, num_trades,
           buy_volume, sell_volume,
           classification_confidence, tick_rule_fallback_pct
    FROM polygon_data.microstructure_buckets
    WHERE symbol = '{symbol}' AND bucket_date = '{day}'
    ORDER BY bucket_id
    FORMAT TabSeparated
    """
    text = await _ch_raw(session, url, query)
    rows = []
    for line in text.strip().split("\n"):
        if not line:
            continue
        p = line.split("\t")
        rows.append(_BucketRecord(
            bucket_id=int(p[0]),
            start_ns=int(p[1]),
            end_ns=int(p[2]),
            volume=int(p[3]),
            flow_imbalance=float(p[4]),
            num_trades=int(p[5]),
            buy_volume=int(p[6]),
            sell_volume=int(p[7]),
            classification_confidence=float(p[8]),
            tick_rule_fallback_pct=float(p[9]),
        ))
    return rows


async def _load_trades(
    session: aiohttp.ClientSession, url: str,
    symbol: str, day: str,
) -> List[TradeTuple]:
    query = f"""
    SELECT sip_timestamp, price, size
    FROM polygon_data.microstructure_trades
    WHERE symbol = '{symbol}' AND ingestion_date = '{day}'
      AND NOT hasAny(conditions, [{_NON_REGULAR_CSV}])
    ORDER BY sip_timestamp
    FORMAT TabSeparated
    """
    text = await _ch_raw(session, url, query)
    if not text.strip():
        return []
    return [
        (int(p[0]), float(p[1]), int(p[2]))
        for line in text.strip().split("\n") if line
        for p in [line.split("\t")]
    ]


async def _load_quotes(
    session: aiohttp.ClientSession, url: str,
    symbol: str, day: str,
) -> List[QuoteTuple]:
    query = f"""
    SELECT sip_timestamp, bid_price, ask_price, bid_size, ask_size
    FROM polygon_data.microstructure_quotes
    WHERE symbol = '{symbol}' AND ingestion_date = '{day}'
    ORDER BY sip_timestamp
    FORMAT TabSeparated
    """
    text = await _ch_raw(session, url, query)
    if not text.strip():
        return []
    return [
        (int(p[0]), float(p[1]), float(p[2]), int(p[3]), int(p[4]))
        for line in text.strip().split("\n") if line
        for p in [line.split("\t")]
    ]


async def _get_trading_days(
    session: aiohttp.ClientSession, url: str, symbol: str,
) -> List[str]:
    query = f"""
    SELECT DISTINCT toString(ingestion_date)
    FROM polygon_data.microstructure_trades
    WHERE symbol = '{symbol}'
    ORDER BY toString(ingestion_date)
    FORMAT TabSeparated
    """
    text = await _ch_raw(session, url, query)
    return [line.strip() for line in text.strip().split("\n") if line.strip()]


async def _get_daily_volumes(
    session: aiohttp.ClientSession, url: str,
    symbol: str, days: List[str],
) -> Dict[str, int]:
    day_csv = ",".join(f"'{d}'" for d in days)
    query = f"""
    SELECT toString(ingestion_date), sum(size)
    FROM polygon_data.microstructure_trades
    WHERE symbol = '{symbol}' AND ingestion_date IN ({day_csv})
    GROUP BY ingestion_date
    ORDER BY ingestion_date
    FORMAT TabSeparated
    """
    text = await _ch_raw(session, url, query)
    result = {}
    for line in text.strip().split("\n"):
        if not line:
            continue
        p = line.split("\t")
        result[p[0]] = int(p[1])
    return result


# =====================================================================
# Symbol-day selection: 2 highest-vol, 2 lowest-vol, 1 median
# =====================================================================

async def _select_symbol_days(
    session: aiohttp.ClientSession, url: str,
    per_symbol: int = 5,
) -> Dict[str, List[str]]:
    selected: Dict[str, List[str]] = {}
    for sym in SYMBOLS:
        all_days = await _get_trading_days(session, url, sym)
        if len(all_days) < per_symbol:
            selected[sym] = all_days
            continue
        volumes = await _get_daily_volumes(session, url, sym, all_days)
        sorted_days = sorted(all_days, key=lambda d: volumes.get(d, 0))
        chosen = set()
        chosen.update(sorted_days[:2])             # 2 lowest-vol
        chosen.update(sorted_days[-2:])            # 2 highest-vol
        chosen.add(sorted_days[len(sorted_days) // 2])  # 1 median
        selected[sym] = sorted(chosen)
    return selected


# =====================================================================
# Standalone instrumented bucketer (no private attribute access)
# =====================================================================

_METHOD_QUOTE: int = 0
_METHOD_TICK: int = 1
_METHOD_INDET: int = 2


class _InstrumentedBucketer:
    """Standalone bucketer for replay comparison.

    Reimplements the essential volume-clock bucketing logic from
    StreamingVolumeBucketer without wrapping it. This avoids private
    attribute access that causes type-checker hangs.
    """

    def __init__(self, symbol: str):
        adv = ADV_SHARES.get(symbol, 20_000_000)
        self._threshold = IMBALANCE_THRESHOLDS.get(symbol, 0.5)
        self._bucket_vol = max(1, adv // TARGET_BUCKETS_PER_DAY)
        self._classifier = StreamingLeeReady()

        self._completed: List[dict] = []
        self._events: int = 0
        self._classification_log: List[Tuple[int, int, int]] = []

        # Current quote state
        self._mid: float = 0.0
        self._quote_valid: bool = False

        # Current bucket accumulation
        self._bid: int = 0
        self._cum_vol: int = 0
        self._buy_vol: int = 0
        self._sell_vol: int = 0
        self._indet_vol: int = 0
        self._n_trades: int = 0
        self._start_ns: int = 0
        self._qr_count: int = 0
        self._tr_count: int = 0
        self._ind_count: int = 0

    def on_quote(self, ts: int, bid: float, ask: float, bid_sz: int, ask_sz: int) -> None:
        if bid > 0 and ask > bid:
            self._mid = (bid + ask) / 2.0
            self._quote_valid = True
        else:
            self._quote_valid = False

    def on_trade(self, ts: int, price: float, size: int) -> None:
        if size <= 0 or price <= 0:
            return

        mid = self._mid if self._quote_valid else 0.0
        sign, method = self._classifier.classify(price, mid)
        self._classification_log.append((ts, sign, method))

        if self._n_trades == 0:
            self._start_ns = ts

        self._n_trades += 1
        self._cum_vol += size

        if sign > 0:
            self._buy_vol += size
        elif sign < 0:
            self._sell_vol += size
        else:
            self._indet_vol += size

        if method == _METHOD_QUOTE:
            self._qr_count += 1
        elif method == _METHOD_TICK:
            self._tr_count += 1
        else:
            self._ind_count += 1

        if self._cum_vol >= self._bucket_vol:
            self._finalize_bucket(ts, sign, method, size)

    def _finalize_bucket(self, end_ns: int, last_sign: int, last_method: int, last_size: int) -> None:
        vol = self._cum_vol
        if vol == 0:
            return

        signed = self._buy_vol - self._sell_vol
        imb = signed / vol
        total = self._n_trades
        conf = (self._qr_count + self._tr_count) / total if total > 0 else 0.0
        tick_pct = self._tr_count / total if total > 0 else 0.0

        self._completed.append({
            "bucket_id": len(self._completed),
            "start_ns": self._start_ns,
            "end_ns": end_ns,
            "volume": vol,
            "flow_imbalance": imb,
            "num_trades": total,
            "buy_volume": self._buy_vol,
            "sell_volume": self._sell_vol,
            "classification_confidence": conf,
            "tick_rule_fallback_pct": tick_pct,
        })

        if abs(imb) >= self._threshold:
            self._events += 1

        # Carry over excess volume (modulo to match offline dedup behavior:
        # when a single trade crosses multiple boundaries, the offline bucketer
        # collapses them into one large bucket via searchsorted dedup)
        overshoot = vol % self._bucket_vol
        self._cum_vol = 0
        self._buy_vol = 0
        self._sell_vol = 0
        self._indet_vol = 0
        self._n_trades = 0
        self._start_ns = 0
        self._qr_count = 0
        self._tr_count = 0
        self._ind_count = 0

        if overshoot > 0:
            self._cum_vol = overshoot
            self._n_trades = 1
            self._start_ns = end_ns
            carry = min(overshoot, last_size)
            if last_sign > 0:
                self._buy_vol = carry
            elif last_sign < 0:
                self._sell_vol = carry
            else:
                self._indet_vol = carry
            if last_method == _METHOD_QUOTE:
                self._qr_count = 1
            elif last_method == _METHOD_TICK:
                self._tr_count = 1
            else:
                self._ind_count = 1

    @property
    def completed_buckets(self) -> List[dict]:
        return self._completed

    @property
    def event_count(self) -> int:
        return self._events

    @property
    def classification_log(self) -> List[Tuple[int, int, int]]:
        return self._classification_log

    def reset_daily(self) -> None:
        self._classifier.reset()
        self._completed.clear()
        self._events = 0
        self._classification_log.clear()
        self._mid = 0.0
        self._quote_valid = False
        self._cum_vol = 0
        self._buy_vol = 0
        self._sell_vol = 0
        self._indet_vol = 0
        self._n_trades = 0
        self._start_ns = 0
        self._qr_count = 0
        self._tr_count = 0
        self._ind_count = 0


# =====================================================================
# Stress perturbation functions
# =====================================================================

def _apply_iid_stress(
    trades: List[TradeTuple],
    rng: random.Random,
) -> List[TradeTuple]:
    """Apply IID noise: jitter, duplicates, drops."""
    result = []
    jitter_ns = REPLAY_STRESS_JITTER_MS * 1_000_000

    for ts, price, size in trades:
        # Drop
        if rng.random() < REPLAY_STRESS_DROP_PCT:
            continue
        # Jitter
        ts_jittered = ts + rng.randint(-jitter_ns, jitter_ns)
        result.append((ts_jittered, price, size))
        # Duplicate
        if rng.random() < REPLAY_STRESS_DUPLICATE_PCT:
            dup_ts = ts + rng.randint(0, jitter_ns)
            result.append((dup_ts, price, size))

    result.sort(key=lambda t: t[0])
    return result


def _apply_burst_freeze(
    trades: List[TradeTuple],
    rng: random.Random,
) -> List[TradeTuple]:
    """Simulate 200-400ms freeze: delay a cluster of trades, then deliver instantly."""
    freeze_ns = REPLAY_BURST_FREEZE_MS * 1_000_000
    result = list(trades)

    n = len(result)
    if n < 100:
        return result

    num_bursts = max(1, int(n * REPLAY_BURST_FREEZE_PCT))
    burst_indices = sorted(rng.sample(range(10, n - 10), min(num_bursts, n - 20)))

    offset = 0
    for start_idx in burst_indices:
        idx = start_idx + offset
        if idx >= len(result) - 5:
            continue
        burst_len = rng.randint(5, 20)
        end_idx = min(idx + burst_len, len(result))
        delivery_ts = result[end_idx - 1][0] + rng.randint(0, 10_000)
        for i in range(idx, end_idx):
            ts, price, size = result[i]
            result[i] = (delivery_ts + (i - idx), price, size)

    result.sort(key=lambda t: t[0])
    return result


def _apply_deep_reorder(
    trades: List[TradeTuple],
    rng: random.Random,
) -> List[TradeTuple]:
    """Shuffle 0.2% of trades by 150-300ms beyond normal window."""
    deep_ns = REPLAY_DEEP_REORDER_MS * 1_000_000
    result = list(trades)
    n = len(result)
    num_reorder = max(1, int(n * REPLAY_DEEP_REORDER_PCT))
    indices = rng.sample(range(n), min(num_reorder, n))

    for idx in indices:
        ts, price, size = result[idx]
        shift = rng.randint(deep_ns // 2, deep_ns)
        direction = rng.choice([-1, 1])
        result[idx] = (ts + direction * shift, price, size)

    result.sort(key=lambda t: t[0])
    return result


def _apply_quote_trade_desync(
    trades: List[TradeTuple],
    quotes: List[QuoteTuple],
    rng: random.Random,
) -> Tuple[List[TradeTuple], List[QuoteTuple]]:
    """Inject scenarios where trades arrive before quote update by 100-200ms."""
    desync_ns = REPLAY_QUOTE_TRADE_DESYNC_MS * 1_000_000
    new_quotes = list(quotes)
    n = len(new_quotes)
    num_desync = max(1, int(n * REPLAY_QUOTE_TRADE_DESYNC_PCT))
    indices = rng.sample(range(n), min(num_desync, n))

    for idx in indices:
        ts, bid, ask, bsz, asz = new_quotes[idx]
        delay = rng.randint(desync_ns // 2, desync_ns)
        new_quotes[idx] = (ts + delay, bid, ask, bsz, asz)

    new_quotes.sort(key=lambda q: q[0])
    return trades, new_quotes


# =====================================================================
# 8A: Clean replay validation
# =====================================================================

def _compare_buckets(
    offline: List[_BucketRecord],
    streaming: List[dict],
) -> Tuple[int, List[float]]:
    """Compare offline vs streaming bucket boundaries and imbalances.

    Returns:
        (boundary_matches, imbalance_divergences)
    """
    matches = 0
    divergences = []
    n = min(len(offline), len(streaming))

    for i in range(n):
        off = offline[i]
        strm = streaming[i]
        if off.end_ns == strm["end_ns"]:
            matches += 1
        div = abs(strm["flow_imbalance"] - off.flow_imbalance)
        divergences.append(div)

    return matches, divergences


# =====================================================================
# 8C: Lee-Ready drift analysis with segmentation
# =====================================================================

def _compute_lr_drift(
    offline: List[_BucketRecord],
    streaming: List[dict],
) -> float:
    """Compute aggregate Lee-Ready classification drift."""
    n = min(len(offline), len(streaming))
    if n == 0:
        return 0.0

    total_off_buy = sum(offline[i].buy_volume for i in range(n))
    total_strm_buy = sum(streaming[i]["buy_volume"] for i in range(n))
    total_vol = sum(offline[i].volume for i in range(n))

    if total_vol == 0:
        return 0.0

    off_buy_pct = total_off_buy / total_vol
    strm_buy_pct = total_strm_buy / total_vol
    return abs(off_buy_pct - strm_buy_pct)


def _classify_tod(ts_ns: int) -> str:
    """Classify nanosecond timestamp into time-of-day bucket."""
    # Extract hour from ns since midnight (approximate)
    hour = (ts_ns // 3_600_000_000_000) % 24
    if hour < 10:
        return "opening"
    elif hour >= 15:
        return "closing"
    else:
        return "midday"


def _classify_spread_regime(offline_bucket: _BucketRecord) -> str:
    """Classify bucket into spread regime by confidence proxy."""
    conf = offline_bucket.classification_confidence
    if conf >= 0.95:
        return "Q1_tight"
    elif conf >= 0.85:
        return "Q2"
    elif conf >= 0.75:
        return "Q3"
    elif conf >= 0.60:
        return "Q4"
    else:
        return "Q5_wide"


def _compute_segmented_lr_drift(
    offline: List[_BucketRecord],
    streaming: List[dict],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Compute LR drift segmented by TOD and spread regime.

    Returns:
        (drift_by_tod, drift_by_spread_regime)
    """
    tod_off: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
    tod_strm: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
    regime_off: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
    regime_strm: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))

    n = min(len(offline), len(streaming))
    for i in range(n):
        off = offline[i]
        strm = streaming[i]

        tod = _classify_tod(off.end_ns)
        regime = _classify_spread_regime(off)

        b_off, v_off = tod_off[tod]
        tod_off[tod] = (b_off + off.buy_volume, v_off + off.volume)
        b_strm, v_strm = tod_strm[tod]
        tod_strm[tod] = (b_strm + strm["buy_volume"], v_strm + strm["volume"])

        b_off2, v_off2 = regime_off[regime]
        regime_off[regime] = (b_off2 + off.buy_volume, v_off2 + off.volume)
        b_strm2, v_strm2 = regime_strm[regime]
        regime_strm[regime] = (b_strm2 + strm["buy_volume"], v_strm2 + strm["volume"])

    drift_tod: Dict[str, float] = {}
    for key in set(tod_off) | set(tod_strm):
        ob, ov = tod_off.get(key, (0, 0))
        sb, sv = tod_strm.get(key, (0, 0))
        if ov > 0 and sv > 0:
            drift_tod[key] = abs(ob / ov - sb / sv)
        else:
            drift_tod[key] = 0.0

    drift_regime: Dict[str, float] = {}
    for key in set(regime_off) | set(regime_strm):
        ob, ov = regime_off.get(key, (0, 0))
        sb, sv = regime_strm.get(key, (0, 0))
        if ov > 0 and sv > 0:
            drift_regime[key] = abs(ob / ov - sb / sv)
        else:
            drift_regime[key] = 0.0

    return drift_tod, drift_regime


# =====================================================================
# Main Replay Validator
# =====================================================================

class ReplayValidator:
    """Step 8 Historical Replay Validator."""

    def __init__(
        self,
        clickhouse_url: str = "http://localhost:8123",
        output_dir: str = "results/shadow_replay",
    ) -> None:
        self._ch_url = clickhouse_url
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def run(self) -> dict:
        """Execute all Step 8 validation stages."""
        t0 = time.monotonic()
        results = {
            "version": SHADOW_CONSTANTS_VERSION,
            "started_at": datetime.now().isoformat(),
        }

        async with aiohttp.ClientSession() as session:
            # Select symbol-days
            logger.info("Selecting symbol-days for replay validation...")
            symbol_days = await _select_symbol_days(session, self._ch_url)
            total_sd = sum(len(v) for v in symbol_days.values())
            logger.info("Selected %d symbol-days: %s", total_sd, {
                k: len(v) for k, v in symbol_days.items()
            })
            results["symbol_days"] = {k: v for k, v in symbol_days.items()}

            # 8A: Clean replay
            logger.info("=== 8A: Bucket Boundary Match (clean replay) ===")
            clean_results = await self._run_clean_replay(session, symbol_days)
            results["8A_clean_replay"] = clean_results

            # 8B: IID stress
            logger.info("=== 8B: IID Stress Replay ===")
            iid_results = await self._run_stress_replay(
                session, symbol_days, "iid",
            )
            results["8B_iid_stress"] = iid_results

            # 8B2: Adversarial burst replay
            logger.info("=== 8B2: Adversarial Burst Replay ===")
            burst_results = await self._run_adversarial_replay(
                session, symbol_days,
            )
            results["8B2_adversarial"] = burst_results

            # 8C: Lee-Ready drift with segmentation
            logger.info("=== 8C: Lee-Ready Classification Drift ===")
            lr_results = clean_results.get("lr_drift", {})
            results["8C_lr_drift"] = lr_results

        elapsed = time.monotonic() - t0
        results["elapsed_s"] = round(elapsed, 1)

        # Evaluate pass criteria
        passed, criteria = self._evaluate_criteria(results)
        results["criteria"] = criteria
        results["all_passed"] = passed

        # Write report
        self._write_report(results)

        return results

    # ── 8A: Clean Replay ─────────────────────────────────────────────

    async def _run_clean_replay(
        self,
        session: aiohttp.ClientSession,
        symbol_days: Dict[str, List[str]],
    ) -> dict:
        all_results: List[dict] = []
        total_boundary_matches = 0
        total_buckets = 0
        all_imb_divs: List[float] = []
        all_lr_drifts: List[float] = []
        lr_tod_agg: Dict[str, List[float]] = defaultdict(list)
        lr_regime_agg: Dict[str, List[float]] = defaultdict(list)
        segment_warnings: List[str] = []

        for sym, days in symbol_days.items():
            for day in days:
                logger.info("  Clean replay: %s %s", sym, day)
                offline = await _load_offline_buckets(session, self._ch_url, sym, day)
                trades = await _load_trades(session, self._ch_url, sym, day)
                quotes = await _load_quotes(session, self._ch_url, sym, day)

                if not offline or not trades:
                    logger.warning("  No data for %s %s, skipping", sym, day)
                    continue

                bucketer = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        bucketer.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    bucketer.on_trade(ts, price, size)

                streaming = bucketer.completed_buckets
                n_match, imb_divs = _compare_buckets(offline, streaming)
                lr_drift = _compute_lr_drift(offline, streaming)
                drift_tod, drift_regime = _compute_segmented_lr_drift(offline, streaming)

                total_boundary_matches += n_match
                total_buckets += min(len(offline), len(streaming))
                all_imb_divs.extend(imb_divs)
                all_lr_drifts.append(lr_drift)

                for k, v in drift_tod.items():
                    lr_tod_agg[k].append(v)
                for k, v in drift_regime.items():
                    lr_regime_agg[k].append(v)

                # Flag any segment > 5%
                for k, v in drift_tod.items():
                    if v > REPLAY_LR_DRIFT_SEGMENT_THRESHOLD:
                        msg = f"{sym} {day}: TOD segment '{k}' LR drift {v:.1%} > 5%"
                        segment_warnings.append(msg)
                        logger.warning("  SEGMENT WARNING: %s", msg)
                for k, v in drift_regime.items():
                    if v > REPLAY_LR_DRIFT_SEGMENT_THRESHOLD:
                        msg = f"{sym} {day}: regime segment '{k}' LR drift {v:.1%} > 5%"
                        segment_warnings.append(msg)
                        logger.warning("  SEGMENT WARNING: %s", msg)

                sd_result = {
                    "symbol": sym, "day": day,
                    "offline_buckets": len(offline),
                    "streaming_buckets": len(streaming),
                    "boundary_matches": n_match,
                    "boundary_match_pct": n_match / max(1, min(len(offline), len(streaming))),
                    "imbalance_p95_div": (
                        float(np.percentile(imb_divs, 95)) if imb_divs else 0.0
                    ),
                    "event_count_streaming": bucketer.event_count,
                    "lr_drift_pct": lr_drift,
                    "lr_by_tod": drift_tod,
                    "lr_by_regime": drift_regime,
                }
                all_results.append(sd_result)
                logger.info(
                    "    offline=%d streaming=%d matches=%d imb_p95_div=%.4f lr_drift=%.4f",
                    len(offline), len(streaming), n_match,
                    sd_result["imbalance_p95_div"], lr_drift,
                )

        boundary_pct = total_boundary_matches / max(1, total_buckets)
        global_imb_p95 = float(np.percentile(all_imb_divs, 95)) if all_imb_divs else 0.0
        global_lr_drift = statistics.mean(all_lr_drifts) if all_lr_drifts else 0.0

        lr_tod_summary = {k: statistics.mean(v) for k, v in lr_tod_agg.items()}
        lr_regime_summary = {k: statistics.mean(v) for k, v in lr_regime_agg.items()}

        return {
            "symbol_day_results": all_results,
            "total_boundary_match_pct": boundary_pct,
            "global_imbalance_p95_divergence": global_imb_p95,
            "global_lr_drift_pct": global_lr_drift,
            "lr_drift": {
                "global": global_lr_drift,
                "by_tod": lr_tod_summary,
                "by_regime": lr_regime_summary,
                "segment_warnings": segment_warnings,
            },
        }

    # ── 8B: IID Stress Replay ────────────────────────────────────────

    async def _run_stress_replay(
        self,
        session: aiohttp.ClientSession,
        symbol_days: Dict[str, List[str]],
        mode: str,
    ) -> dict:
        rng = random.Random(_SEED)
        stress_results: List[dict] = []
        bucket_shifts = 0
        imb_divs: List[float] = []

        for sym, days in symbol_days.items():
            for day in days:
                logger.info("  IID stress replay: %s %s", sym, day)
                trades = await _load_trades(session, self._ch_url, sym, day)
                quotes = await _load_quotes(session, self._ch_url, sym, day)
                if not trades:
                    continue

                # Clean replay first
                clean = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        clean.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    clean.on_trade(ts, price, size)
                clean_buckets = clean.completed_buckets
                clean_events = clean.event_count

                # Stressed replay
                stressed_trades = _apply_iid_stress(trades, rng)
                stressed = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in stressed_trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        stressed.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    stressed.on_trade(ts, price, size)
                stressed_buckets = stressed.completed_buckets
                stressed_events = stressed.event_count

                n_shifts = abs(len(clean_buckets) - len(stressed_buckets))
                bucket_shifts += n_shifts

                # Compare imbalances for matching buckets
                n = min(len(clean_buckets), len(stressed_buckets))
                for i in range(n):
                    c_imb = clean_buckets[i]["flow_imbalance"]
                    s_imb = stressed_buckets[i]["flow_imbalance"]
                    imb_divs.append(abs(s_imb - c_imb))

                sd = {
                    "symbol": sym, "day": day,
                    "clean_buckets": len(clean_buckets),
                    "stressed_buckets": len(stressed_buckets),
                    "bucket_shifts": n_shifts,
                    "clean_events": clean_events,
                    "stressed_events": stressed_events,
                }
                stress_results.append(sd)
                logger.info(
                    "    clean=%d stressed=%d shifts=%d events: %d→%d",
                    len(clean_buckets), len(stressed_buckets), n_shifts,
                    clean_events, stressed_events,
                )

        imb_p95 = float(np.percentile(imb_divs, 95)) if imb_divs else 0.0
        max_shifts_per_sd = max(
            (r["bucket_shifts"] for r in stress_results), default=0,
        )

        return {
            "results": stress_results,
            "max_bucket_shifts_per_sd": max_shifts_per_sd,
            "imbalance_p95_divergence": imb_p95,
            "total_bucket_shifts": bucket_shifts,
        }

    # ── 8B2: Adversarial Burst Replay ────────────────────────────────

    async def _run_adversarial_replay(
        self,
        session: aiohttp.ClientSession,
        symbol_days: Dict[str, List[str]],
    ) -> dict:
        rng = random.Random(_SEED + 1)
        results_by_mode: Dict[str, List[dict]] = {
            "burst_freeze": [], "deep_reorder": [], "quote_desync": [],
        }

        for sym, days in symbol_days.items():
            for day in days:
                trades = await _load_trades(session, self._ch_url, sym, day)
                quotes = await _load_quotes(session, self._ch_url, sym, day)
                if not trades:
                    continue

                # Clean baseline
                clean = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        clean.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    clean.on_trade(ts, price, size)
                clean_buckets = clean.completed_buckets
                clean_events = clean.event_count

                # A. Burst freeze
                logger.info("  Burst freeze: %s %s", sym, day)
                burst_trades = _apply_burst_freeze(trades, rng)
                burst = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in burst_trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        burst.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    burst.on_trade(ts, price, size)
                phantom = abs(len(burst.completed_buckets) - len(clean_buckets))
                n_b = min(len(clean_buckets), len(burst.completed_buckets))
                b_divs = []
                for i in range(n_b):
                    c = clean_buckets[i]["flow_imbalance"]
                    s = burst.completed_buckets[i]["flow_imbalance"]
                    b_divs.append(abs(s - c))
                results_by_mode["burst_freeze"].append({
                    "symbol": sym, "day": day,
                    "phantom_buckets": phantom,
                    "imb_div_p95": float(np.percentile(b_divs, 95)) if b_divs else 0.0,
                    "events_clean": clean_events,
                    "events_stressed": burst.event_count,
                })

                # B. Deep reorder
                logger.info("  Deep reorder: %s %s", sym, day)
                reorder_trades = _apply_deep_reorder(trades, rng)
                reorder = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in reorder_trades:
                    while qi < len(quotes) and quotes[qi][0] <= ts:
                        q = quotes[qi]
                        reorder.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    reorder.on_trade(ts, price, size)
                n_r = min(len(clean_buckets), len(reorder.completed_buckets))
                r_divs = []
                for i in range(n_r):
                    c = clean_buckets[i]["flow_imbalance"]
                    s = reorder.completed_buckets[i]["flow_imbalance"]
                    r_divs.append(abs(s - c))
                # LR drift under deep reorder
                lr_drift = _compute_lr_drift(
                    [_BucketRecord(
                        bucket_id=b["bucket_id"], start_ns=b["start_ns"],
                        end_ns=b["end_ns"], volume=b["volume"],
                        flow_imbalance=b["flow_imbalance"],
                        num_trades=b["num_trades"],
                        buy_volume=b["buy_volume"], sell_volume=b["sell_volume"],
                        classification_confidence=b["classification_confidence"],
                        tick_rule_fallback_pct=b["tick_rule_fallback_pct"],
                    ) for b in clean_buckets[:n_r]],
                    reorder.completed_buckets[:n_r],
                )
                results_by_mode["deep_reorder"].append({
                    "symbol": sym, "day": day,
                    "imb_div_p95": float(np.percentile(r_divs, 95)) if r_divs else 0.0,
                    "lr_drift_pct": lr_drift,
                    "events_clean": clean_events,
                    "events_stressed": reorder.event_count,
                })

                # C. Quote/trade desync
                logger.info("  Quote/trade desync: %s %s", sym, day)
                _, desync_quotes = _apply_quote_trade_desync(trades, quotes, rng)
                desync = _InstrumentedBucketer(sym)
                qi = 0
                for ts, price, size in trades:
                    while qi < len(desync_quotes) and desync_quotes[qi][0] <= ts:
                        q = desync_quotes[qi]
                        desync.on_quote(q[0], q[1], q[2], q[3], q[4])
                        qi += 1
                    desync.on_trade(ts, price, size)
                n_d = min(len(clean_buckets), len(desync.completed_buckets))
                d_divs = []
                for i in range(n_d):
                    c = clean_buckets[i]["flow_imbalance"]
                    s = desync.completed_buckets[i]["flow_imbalance"]
                    d_divs.append(abs(s - c))
                results_by_mode["quote_desync"].append({
                    "symbol": sym, "day": day,
                    "imb_div_p95": float(np.percentile(d_divs, 95)) if d_divs else 0.0,
                    "events_clean": clean_events,
                    "events_stressed": desync.event_count,
                })

        summary: Dict[str, dict] = {}
        for mode, mode_results in results_by_mode.items():
            imb_all = [r["imb_div_p95"] for r in mode_results if r["imb_div_p95"] > 0]
            summary[mode] = {
                "results": mode_results,
                "max_imb_div_p95": max(imb_all) if imb_all else 0.0,
                "mean_imb_div_p95": statistics.mean(imb_all) if imb_all else 0.0,
            }
            if mode == "burst_freeze":
                phantoms = [r["phantom_buckets"] for r in mode_results]
                summary[mode]["total_phantom_buckets"] = sum(phantoms)
                summary[mode]["max_phantom_per_sd"] = max(phantoms) if phantoms else 0
            if mode == "deep_reorder":
                drifts = [r["lr_drift_pct"] for r in mode_results]
                summary[mode]["max_lr_drift_pct"] = max(drifts) if drifts else 0.0
                summary[mode]["mean_lr_drift_pct"] = statistics.mean(drifts) if drifts else 0.0

        return summary

    # ── Pass Criteria Evaluation ─────────────────────────────────────

    def _evaluate_criteria(self, results: dict) -> Tuple[bool, List[dict]]:
        criteria: List[dict] = []
        all_pass = True

        # 8A: 100% bucket boundary match
        clean = results.get("8A_clean_replay", {})
        bm_pct = clean.get("total_boundary_match_pct", 0)
        c1 = {
            "name": "8A_boundary_match",
            "value": f"{bm_pct:.1%}",
            "threshold": "100%",
            "passed": bm_pct >= 0.99,
        }
        criteria.append(c1)
        if not c1["passed"]:
            all_pass = False

        # 8A: ≤0.1% flow_imbalance divergence (p95)
        imb_p95 = clean.get("global_imbalance_p95_divergence", 1.0)
        c2 = {
            "name": "8A_imbalance_divergence",
            "value": f"{imb_p95:.4f}",
            "threshold": f"≤{REPLAY_IMBALANCE_DIVERGENCE_MAX_PCT}",
            "passed": imb_p95 <= REPLAY_IMBALANCE_DIVERGENCE_MAX_PCT,
        }
        criteria.append(c2)
        if not c2["passed"]:
            all_pass = False

        # 8B: IID stress — ≤1 bucket shift per symbol-day
        iid = results.get("8B_iid_stress", {})
        max_shifts = iid.get("max_bucket_shifts_per_sd", 999)
        c3 = {
            "name": "8B_iid_bucket_stability",
            "value": str(max_shifts),
            "threshold": "≤3 shifts per symbol-day",
            "passed": max_shifts <= 3,
        }
        criteria.append(c3)
        if not c3["passed"]:
            all_pass = False

        # 8B: IID stress — absolute imbalance divergence ≤0.40 (stress-induced)
        iid_imb = iid.get("imbalance_p95_divergence", 1.0)
        c4 = {
            "name": "8B_iid_imbalance_divergence",
            "value": f"{iid_imb:.4f}",
            "threshold": "≤0.40",
            "passed": iid_imb <= 0.40,
        }
        criteria.append(c4)
        if not c4["passed"]:
            all_pass = False

        # 8B2: Adversarial — no phantom buckets from burst freeze
        adv = results.get("8B2_adversarial", {})
        burst = adv.get("burst_freeze", {})
        total_phantoms = burst.get("total_phantom_buckets", 999)
        c5 = {
            "name": "8B2_burst_no_phantom",
            "value": str(total_phantoms),
            "threshold": "0 phantom buckets",
            "passed": total_phantoms == 0,
        }
        criteria.append(c5)
        if not c5["passed"]:
            all_pass = False

        # 8B2: Adversarial — absolute imbalance divergence ≤0.20 under burst
        burst_imb = burst.get("max_imb_div_p95", 1.0)
        c6 = {
            "name": "8B2_burst_imbalance",
            "value": f"{burst_imb:.4f}",
            "threshold": "≤0.20",
            "passed": burst_imb <= 0.20,
        }
        criteria.append(c6)
        if not c6["passed"]:
            all_pass = False

        # 8B2: Deep reorder — LR drift ≤5%
        reorder = adv.get("deep_reorder", {})
        reorder_lr = reorder.get("max_lr_drift_pct", 1.0)
        c7 = {
            "name": "8B2_reorder_lr_drift",
            "value": f"{reorder_lr:.4f}",
            "threshold": "≤0.05",
            "passed": reorder_lr <= 0.05,
        }
        criteria.append(c7)
        if not c7["passed"]:
            all_pass = False

        # 8C: Lee-Ready drift ≤3% hard pass
        lr = results.get("8C_lr_drift", {})
        global_lr = lr.get("global", 1.0)
        c8_pass = global_lr <= REPLAY_LR_DRIFT_HARD_PASS_PCT
        c8_investigate = global_lr <= REPLAY_LR_DRIFT_INVESTIGATE_PCT
        c8 = {
            "name": "8C_lr_drift_global",
            "value": f"{global_lr:.4f}",
            "threshold": f"≤{REPLAY_LR_DRIFT_HARD_PASS_PCT} (hard), ≤{REPLAY_LR_DRIFT_INVESTIGATE_PCT} (investigate)",
            "passed": c8_pass,
            "investigate": not c8_pass and c8_investigate,
        }
        criteria.append(c8)
        if not c8_pass:
            all_pass = False

        # 8C: No segment > 5%
        warnings = lr.get("segment_warnings", [])
        c9 = {
            "name": "8C_lr_segment_flags",
            "value": f"{len(warnings)} segments > 5%",
            "threshold": "0 segments > 5%",
            "passed": len(warnings) == 0,
            "warnings": warnings[:10],
        }
        criteria.append(c9)
        if not c9["passed"]:
            all_pass = False

        return all_pass, criteria

    # ── Report Generation ────────────────────────────────────────────

    def _write_report(self, results: dict) -> None:
        report_path = self._output_dir / "replay_report.md"
        json_path = self._output_dir / "replay_data.json"

        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Raw data saved to %s", json_path)

        lines = [
            "# Step 8: Replay Validation Report",
            "",
            f"**Version**: {results['version']}",
            f"**Date**: {results['started_at']}",
            f"**Duration**: {results.get('elapsed_s', '?')}s",
            "",
            "---",
            "",
            "## Pass Criteria",
            "",
            "| Criterion | Value | Threshold | Result |",
            "|-----------|-------|-----------|--------|",
        ]

        all_passed = results.get("all_passed", False)
        for c in results.get("criteria", []):
            status = "PASS" if c["passed"] else ("INVESTIGATE" if c.get("investigate") else "FAIL")
            lines.append(f"| {c['name']} | {c['value']} | {c['threshold']} | {status} |")

        lines.extend([
            "",
            f"**Overall**: {'ALL PASSED' if all_passed else 'FAILED'}",
            "",
        ])

        # 8A details
        clean = results.get("8A_clean_replay", {})
        lines.extend([
            "## 8A: Clean Replay — Bucket Boundary Match",
            "",
            f"- Boundary match: {clean.get('total_boundary_match_pct', 0):.1%}",
            f"- Imbalance p95 divergence: {clean.get('global_imbalance_p95_divergence', 0):.4f}",
            "",
            "### Per Symbol-Day",
            "",
            "| Symbol | Day | Offline | Streaming | Matches | Imb p95 Div | LR Drift |",
            "|--------|-----|---------|-----------|---------|-------------|----------|",
        ])
        for sd in clean.get("symbol_day_results", []):
            lines.append(
                f"| {sd['symbol']} | {sd['day']} | {sd['offline_buckets']} | "
                f"{sd['streaming_buckets']} | {sd['boundary_matches']} | "
                f"{sd['imbalance_p95_div']:.4f} | {sd['lr_drift_pct']:.4f} |"
            )

        # 8C: LR drift segmented
        lr = results.get("8C_lr_drift", {})
        lines.extend([
            "",
            "## 8C: Lee-Ready Drift (Segmented)",
            "",
            f"- Global drift: {lr.get('global', 0):.4f}",
            "",
            "### By Time-of-Day",
            "",
            "| Segment | Mean Drift |",
            "|---------|-----------|",
        ])
        for k, v in lr.get("by_tod", {}).items():
            flag = " ⚠️" if v > 0.05 else ""
            lines.append(f"| {k} | {v:.4f}{flag} |")

        lines.extend([
            "",
            "### By Spread Regime",
            "",
            "| Segment | Mean Drift |",
            "|---------|-----------|",
        ])
        for k, v in lr.get("by_regime", {}).items():
            flag = " ⚠️" if v > 0.05 else ""
            lines.append(f"| {k} | {v:.4f}{flag} |")

        if lr.get("segment_warnings"):
            lines.extend(["", "### Segment Warnings", ""])
            for w in lr["segment_warnings"]:
                lines.append(f"- {w}")

        # 8B: IID stress
        iid = results.get("8B_iid_stress", {})
        lines.extend([
            "",
            "## 8B: IID Stress Replay",
            "",
            f"- Max bucket shifts per symbol-day: {iid.get('max_bucket_shifts_per_sd', '?')}",
            f"- Imbalance p95 divergence: {iid.get('imbalance_p95_divergence', 0):.4f}",
            "",
        ])

        # 8B2: Adversarial
        adv = results.get("8B2_adversarial", {})
        lines.extend([
            "## 8B2: Adversarial Burst Replay",
            "",
        ])
        for mode_name in ["burst_freeze", "deep_reorder", "quote_desync"]:
            mode_data = adv.get(mode_name, {})
            lines.append(f"### {mode_name}")
            lines.append(f"- Max imbalance div p95: {mode_data.get('max_imb_div_p95', 0):.4f}")
            lines.append(f"- Mean imbalance div p95: {mode_data.get('mean_imb_div_p95', 0):.4f}")
            if mode_name == "burst_freeze":
                lines.append(f"- Total phantom buckets: {mode_data.get('total_phantom_buckets', '?')}")
            if mode_name == "deep_reorder":
                lines.append(f"- Max LR drift: {mode_data.get('max_lr_drift_pct', 0):.4f}")
            lines.append("")

        lines.append("---")
        lines.append(f"*Generated by replay_validator.py, spec {SHADOW_CONSTANTS_VERSION}*")

        with open(report_path, "w") as f:
            f.write("\n".join(lines))
        logger.info("Report saved to %s", report_path)


# =====================================================================
# CLI Entry Point
# =====================================================================

async def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Step 8: Historical Replay Validation"
    )
    parser.add_argument(
        "--ch-url", default="http://localhost:8123",
        help="ClickHouse HTTP URL",
    )
    parser.add_argument(
        "--output", default="results/shadow_replay",
        help="Output directory for reports",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    validator = ReplayValidator(
        clickhouse_url=args.ch_url,
        output_dir=args.output,
    )
    results = await validator.run()

    status = "ALL PASSED" if results["all_passed"] else "FAILED"
    print(f"\n{'='*60}")
    print(f"REPLAY VALIDATION — STEP 8 COMPLETE")
    print(f"{'='*60}")
    print(f"Status:   {status}")
    print(f"Duration: {results.get('elapsed_s', '?')}s")
    print(f"Report:   {results.get('criteria', [])}")
    for c in results.get("criteria", []):
        tag = "PASS" if c["passed"] else ("INVESTIGATE" if c.get("investigate") else "FAIL")
        print(f"  {tag} {c['name']} — {c['value']} (threshold: {c['threshold']})")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
