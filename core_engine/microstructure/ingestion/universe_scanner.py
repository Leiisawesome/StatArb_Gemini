"""
Universe construction and tier classification.

Scans candidate symbols against liquidity guardrails and spread
characteristics to select the falsification dataset universe.

Uses existing PolygonRestService methods:
  - get_daily_bars() for 20-day volume/trade profiles
  - get_ticker_details() for sector classification
  - _fetch_paginated_v3() for spread estimation (sample quote data)

Blueprint: v1.6-FINAL Section 1.1
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml
from pathlib import Path

from core_engine.data.feeds.polygon_rest import PolygonRestService
from core_engine.microstructure.ingestion.bulk_downloader import BulkDownloader
from core_engine.microstructure.types import (
    SpreadProfile,
    Tier,
    UniverseClassification,
    VolumeProfile,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parents[2] / "config" / "catalog" / "microstructure" / "universe.yaml"

# SIC code → GICS-like sector mapping (coarse but sufficient)
SIC_SECTOR_MAP = {
    range(100, 1000): "Agriculture",
    range(1000, 1500): "Mining",
    range(1500, 1800): "Construction",
    range(2000, 4000): "Manufacturing",
    range(4000, 5000): "Transportation & Utilities",
    range(5000, 5200): "Wholesale Trade",
    range(5200, 6000): "Retail Trade",
    range(6000, 6800): "Finance",
    range(7000, 9000): "Services",
    range(9100, 9730): "Public Administration",
}

# Fallback sector mapping for known tickers
KNOWN_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "AMD": "Technology", "GOOG": "Communication Services",
    "GOOGL": "Communication Services",
    "META": "Communication Services", "AMZN": "Consumer Discretionary",
    "TSLA": "Consumer Discretionary", "NFLX": "Communication Services",
    "UBER": "Industrials", "SQ": "Financials", "COIN": "Financials",
    "SNAP": "Communication Services", "PLTR": "Industrials",
    "SHOP": "Technology", "PINS": "Communication Services",
    "LYFT": "Industrials", "HOOD": "Financials", "DASH": "Industrials",
    "SOFI": "Financials", "RBLX": "Communication Services",
    "ROKU": "Communication Services", "NET": "Technology",
    "CRWD": "Technology", "ZS": "Technology", "DDOG": "Technology",
    "MDB": "Technology", "SNOW": "Technology", "U": "Technology",
    "ABNB": "Consumer Discretionary", "DIS": "Communication Services",
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
    "WMT": "Consumer Staples", "COST": "Consumer Staples",
    "PFE": "Healthcare", "JNJ": "Healthcare", "UNH": "Healthcare",
    "XOM": "Energy", "CVX": "Energy",
}


@dataclass
class CandidateResult:
    """Evaluation results for a candidate symbol."""
    symbol: str
    sector: str = ""
    # Volume profile
    median_daily_trades: int = 0
    median_daily_dollar_volume: float = 0.0
    median_daily_volume_shares: int = 0
    adv_shares: int = 0
    # Spread profile
    median_spread_bps: float = 0.0
    spread_std_bps: float = 0.0
    median_nbbo_bid_size: float = 0.0
    median_nbbo_ask_size: float = 0.0
    # Classification
    assigned_tier: Optional[Tier] = None
    excluded: bool = False
    exclusion_reason: str = ""
    # U-shape score (not computed here, placeholder)
    ushape_score: float = 0.0


class UniverseScanner:
    """Selects and classifies symbols into liquidity tiers.

    Workflow:
    1. Fetch 20-day daily aggregates for each candidate
    2. Fetch ticker details for sector classification
    3. Sample 1 day of quote data per candidate for spread estimation
    4. Apply hard liquidity guardrails
    5. Classify surviving candidates into tiers A/B/C
    6. Enforce sector diversity (≥5 sectors)
    7. Return frozen UniverseClassification
    """

    def __init__(
        self,
        polygon_service: PolygonRestService,
        config_path: Optional[Path] = None,
    ):
        self._polygon = polygon_service
        self._config = self._load_config(config_path or CONFIG_PATH)

    @staticmethod
    def _load_config(path: Path) -> Dict:
        with open(path) as f:
            return yaml.safe_load(f)["universe"]

    async def scan_candidates(
        self,
        candidate_symbols: List[str],
        observation_start: date,
        observation_end: date,
    ) -> UniverseClassification:
        """
        Evaluate candidate symbols and produce a frozen tier classification.

        Args:
            candidate_symbols: 30-40 candidate tickers
            observation_start: Start of 20-day observation window
            observation_end: End of 20-day observation window

        Returns:
            Frozen UniverseClassification ready for downstream ingestion.
        """
        logger.info(
            "Scanning %d candidates over %s to %s",
            len(candidate_symbols), observation_start, observation_end,
        )

        # Step 1: Fetch daily aggregates and ticker details concurrently
        candidates = await self._evaluate_candidates(
            candidate_symbols, observation_start, observation_end
        )

        # Step 2: Apply hard liquidity guardrails
        survivors, excluded = self._apply_guardrails(candidates)
        logger.info(
            "Guardrails: %d survived, %d excluded", len(survivors), len(excluded)
        )

        # Step 3: Classify into tiers
        tier_assignments = self._classify_tiers(survivors)

        # Step 4: Enforce sector diversity
        tier_assignments, additional_excluded = self._enforce_diversity(
            tier_assignments, survivors
        )
        excluded.extend(additional_excluded)

        # Step 5: Build output
        spread_profiles = {}
        volume_profiles = {}
        sectors = {}

        for c in survivors:
            if c.symbol in tier_assignments:
                spread_profiles[c.symbol] = SpreadProfile(
                    symbol=c.symbol,
                    median_spread_bps=c.median_spread_bps,
                    spread_std_bps=c.spread_std_bps,
                    median_quoted_size_bid=c.median_nbbo_bid_size,
                    median_quoted_size_ask=c.median_nbbo_ask_size,
                    pct_time_locked=0.0,
                )
                volume_profiles[c.symbol] = VolumeProfile(
                    symbol=c.symbol,
                    median_daily_trades=c.median_daily_trades,
                    median_daily_dollar_volume=c.median_daily_dollar_volume,
                    median_3min_volume=c.median_daily_volume_shares / 130,
                    intraday_ushape_score=c.ushape_score,
                    adv_shares=c.adv_shares,
                )
                sectors[c.symbol] = c.sector

        classification = UniverseClassification(
            tier_assignments=tier_assignments,
            spread_profiles=spread_profiles,
            volume_profiles=volume_profiles,
            excluded_symbols=excluded,
            sectors=sectors,
            observation_start=observation_start,
            observation_end=observation_end,
            frozen=True,
        )

        selected = list(tier_assignments.keys())
        tier_summary = {}
        for sym, tier in tier_assignments.items():
            tier_summary.setdefault(tier.value, []).append(sym)

        logger.info("Universe frozen: %d symbols", len(selected))
        for t, syms in sorted(tier_summary.items()):
            logger.info("  Tier %s: %s", t, ", ".join(syms))

        n_sectors = len(set(sectors.values()))
        logger.info("  Sectors: %d (%s)", n_sectors, ", ".join(sorted(set(sectors.values()))))

        return classification

    async def _evaluate_candidates(
        self,
        symbols: List[str],
        obs_start: date,
        obs_end: date,
    ) -> List[CandidateResult]:
        """Fetch daily bars, ticker details, and sample spreads for all candidates."""

        # Fetch daily bars concurrently
        start_dt = datetime(obs_start.year, obs_start.month, obs_start.day, tzinfo=timezone.utc)
        end_dt = datetime(obs_end.year, obs_end.month, obs_end.day, tzinfo=timezone.utc)
        bar_data = await self._polygon.get_bars_multi(
            symbols, timeframe="1d", start=start_dt, end=end_dt
        )

        # Fetch ticker details concurrently
        details = await self._polygon.get_ticker_details_multi(symbols)

        # Sample spread data (1 recent day per candidate, batched)
        spread_data = await self._sample_spreads(symbols, obs_end)

        candidates = []
        for sym in symbols:
            c = CandidateResult(symbol=sym)

            # Sector from ticker details
            det = details.get(sym, {})
            c.sector = self._resolve_sector(sym, det)

            # Volume profile from daily bars
            df = bar_data.get(sym)
            if df is not None and len(df) > 0:
                trades = df["num_trades"].dropna()
                volumes = df["volume"].dropna()
                vwaps = df["vwap"].dropna()

                c.median_daily_trades = int(trades.median()) if len(trades) > 0 else 0
                c.median_daily_volume_shares = int(volumes.median()) if len(volumes) > 0 else 0
                c.adv_shares = int(volumes.mean()) if len(volumes) > 0 else 0

                if len(volumes) > 0 and len(vwaps) > 0:
                    dollar_vols = volumes * vwaps
                    c.median_daily_dollar_volume = float(dollar_vols.median())
            else:
                c.excluded = True
                c.exclusion_reason = "No daily bar data"

            # Spread from sample
            spread_info = spread_data.get(sym)
            if spread_info:
                c.median_spread_bps = spread_info["median_spread_bps"]
                c.spread_std_bps = spread_info.get("spread_std_bps", 0.0)
                c.median_nbbo_bid_size = spread_info.get("median_bid_size", 0.0)
                c.median_nbbo_ask_size = spread_info.get("median_ask_size", 0.0)

            candidates.append(c)

        return candidates

    async def _sample_spreads(
        self, symbols: List[str], ref_date: date
    ) -> Dict[str, Dict[str, float]]:
        """Sample 1 day of NBBO quotes per symbol to estimate spread profile.

        Uses a limited page count to avoid downloading millions of quotes per
        candidate. 2-3 pages of 50K quotes is sufficient for spread estimation.
        """
        results: Dict[str, Dict[str, float]] = {}
        semaphore = asyncio.Semaphore(5)

        # Use a recent trading day (ref_date minus a small buffer)
        sample_date = ref_date - timedelta(days=3)
        start_ns, end_ns = BulkDownloader._day_to_rth_ns(sample_date)

        async def fetch_one(sym: str) -> None:
            async with semaphore:
                try:
                    endpoint = f"{self._polygon.config.base_url}/v3/quotes/{sym.upper()}"
                    params = {
                        "timestamp.gte": start_ns,
                        "timestamp.lte": end_ns,
                        "order": "asc",
                        "sort": "timestamp",
                        "limit": 50000,
                    }
                    rows = await self._polygon._fetch_paginated_v3(
                        endpoint, params, max_pages=3
                    )
                    if not rows:
                        return

                    spreads_bps = []
                    bid_sizes = []
                    ask_sizes = []
                    for r in rows:
                        bid = r.get("bid_price", 0)
                        ask = r.get("ask_price", 0)
                        mid = (bid + ask) / 2.0
                        if mid > 0 and ask > bid > 0:
                            spreads_bps.append((ask - bid) / mid * 10_000)
                            bid_sizes.append(r.get("bid_size", 0))
                            ask_sizes.append(r.get("ask_size", 0))

                    if spreads_bps:
                        arr = np.array(spreads_bps)
                        results[sym] = {
                            "median_spread_bps": float(np.median(arr)),
                            "spread_std_bps": float(np.std(arr)),
                            "median_bid_size": float(np.median(bid_sizes)),
                            "median_ask_size": float(np.median(ask_sizes)),
                        }
                except Exception as e:
                    logger.warning("Spread sampling failed for %s: %s", sym, e)

        await asyncio.gather(*(fetch_one(s) for s in symbols))
        return results

    def _resolve_sector(self, symbol: str, details: Dict[str, Any]) -> str:
        """Resolve sector using modern GICS-like classification.

        Priority: curated mapping > SIC codes > description keywords.
        SIC codes map to outdated categories (e.g., semiconductors = "Manufacturing")
        so the curated mapping provides better sector diversity for portfolio analysis.
        """
        if symbol in KNOWN_SECTORS:
            return KNOWN_SECTORS[symbol]

        sic = details.get("sic_code")
        if sic:
            try:
                sic_int = int(sic)
                for rng, sector in SIC_SECTOR_MAP.items():
                    if sic_int in rng:
                        return sector
            except (ValueError, TypeError):
                pass

        desc = details.get("description", "")
        if "technology" in desc.lower() or "software" in desc.lower():
            return "Technology"
        if "financial" in desc.lower() or "bank" in desc.lower():
            return "Financials"

        return "Unknown"

    def _apply_guardrails(
        self, candidates: List[CandidateResult]
    ) -> Tuple[List[CandidateResult], List[Tuple[str, str]]]:
        """Apply hard liquidity guardrails from config."""
        filters = self._config.get("liquidity_filters", {})
        min_trades = filters.get("min_daily_trades_floor", 50_000)

        survivors = []
        excluded = []

        for c in candidates:
            if c.excluded:
                excluded.append((c.symbol, c.exclusion_reason))
                continue

            if c.median_daily_trades < min_trades:
                excluded.append((
                    c.symbol,
                    f"Median daily trades {c.median_daily_trades:,} < {min_trades:,}",
                ))
                continue

            if c.median_daily_dollar_volume <= 0:
                excluded.append((c.symbol, "No dollar volume data"))
                continue

            survivors.append(c)

        return survivors, excluded

    def _classify_tiers(
        self, candidates: List[CandidateResult]
    ) -> Dict[str, Tier]:
        """Classify candidates into tiers based on spread and volume characteristics."""
        tier_defs = self._config["tiers"]

        tier_a_max_spread = tier_defs["A"]["median_spread_bps_max"]
        tier_a_min_dv = tier_defs["A"]["min_daily_dollar_volume"]
        tier_b_max_spread = tier_defs["B"]["median_spread_bps_max"]
        tier_b_min_dv = tier_defs["B"]["min_daily_dollar_volume"]
        tier_c_max_spread = tier_defs["C"]["median_spread_bps_max"]
        tier_c_min_dv = tier_defs["C"]["min_daily_dollar_volume"]

        target_a = tier_defs["A"]["target_count"]
        target_b = tier_defs["B"]["target_count"]
        target_c = tier_defs["C"]["target_count"]

        # Score and bucket candidates
        tier_a_pool = []
        tier_b_pool = []
        tier_c_pool = []

        for c in candidates:
            spread = c.median_spread_bps
            dv = c.median_daily_dollar_volume

            if spread <= tier_a_max_spread and dv >= tier_a_min_dv:
                tier_a_pool.append(c)
            elif spread <= tier_b_max_spread and dv >= tier_b_min_dv:
                tier_b_pool.append(c)
            elif spread <= tier_c_max_spread and dv >= tier_c_min_dv:
                tier_c_pool.append(c)

        # Sort by dollar volume (descending) within each tier — prefer the most liquid
        tier_a_pool.sort(key=lambda c: c.median_daily_dollar_volume, reverse=True)
        tier_b_pool.sort(key=lambda c: c.median_daily_dollar_volume, reverse=True)
        tier_c_pool.sort(key=lambda c: c.median_daily_dollar_volume, reverse=True)

        assignments: Dict[str, Tier] = {}

        for c in tier_a_pool[:target_a]:
            assignments[c.symbol] = Tier.A
        for c in tier_b_pool[:target_b]:
            assignments[c.symbol] = Tier.B
        for c in tier_c_pool[:target_c]:
            assignments[c.symbol] = Tier.C

        return assignments

    def _enforce_diversity(
        self,
        assignments: Dict[str, Tier],
        candidates: List[CandidateResult],
    ) -> Tuple[Dict[str, Tier], List[Tuple[str, str]]]:
        """Ensure ≥5 sectors are represented. Swap symbols if needed."""
        min_sectors = self._config.get("min_sectors", 5)

        sector_map = {c.symbol: c.sector for c in candidates}
        selected_sectors = {sector_map.get(s, "Unknown") for s in assignments}

        if len(selected_sectors) >= min_sectors:
            return assignments, []

        logger.warning(
            "Only %d sectors represented, need %d. Attempting swaps.",
            len(selected_sectors), min_sectors,
        )

        # Build pool of unselected candidates by tier
        unselected = [
            c for c in candidates
            if c.symbol not in assignments and not c.excluded
        ]
        unselected_by_sector: Dict[str, List[CandidateResult]] = {}
        for c in unselected:
            unselected_by_sector.setdefault(c.sector, []).append(c)

        additional_excluded: List[Tuple[str, str]] = []
        needed = min_sectors - len(selected_sectors)
        missing_sectors = set()
        for c in unselected:
            if c.sector not in selected_sectors:
                missing_sectors.add(c.sector)

        for sector in sorted(missing_sectors):
            if len(selected_sectors) >= min_sectors:
                break

            pool = unselected_by_sector.get(sector, [])
            if not pool:
                continue

            pool.sort(key=lambda c: c.median_daily_dollar_volume, reverse=True)
            new_sym = pool[0]

            # Find a swappable symbol: must share its sector with ≥1 other selected symbol
            current_sector_counts: Dict[str, int] = {}
            for s in assignments:
                s_sector = sector_map.get(s, "Unknown")
                current_sector_counts[s_sector] = current_sector_counts.get(s_sector, 0) + 1

            swappable = [
                s for s in assignments
                if current_sector_counts.get(sector_map.get(s, ""), 0) > 1
            ]

            if not swappable:
                continue

            # Remove the weakest swappable symbol
            weakest = min(
                swappable,
                key=lambda s: next(
                    c.median_daily_dollar_volume
                    for c in candidates if c.symbol == s
                ),
            )

            del assignments[weakest]
            additional_excluded.append((weakest, f"Swapped for sector diversity ({sector})"))

            # Assign the new symbol to the appropriate tier
            if new_sym.median_spread_bps <= 3.0 and new_sym.median_daily_dollar_volume >= 500_000_000:
                assignments[new_sym.symbol] = Tier.A
            elif new_sym.median_spread_bps <= 8.0 and new_sym.median_daily_dollar_volume >= 100_000_000:
                assignments[new_sym.symbol] = Tier.B
            else:
                assignments[new_sym.symbol] = Tier.C

            selected_sectors.add(sector)
            logger.info(
                "Diversity swap: removed %s, added %s (sector: %s)",
                weakest, new_sym.symbol, sector,
            )

        return assignments, additional_excluded

    def freeze_to_yaml(
        self,
        classification: UniverseClassification,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Write the frozen classification to YAML for audit trail."""
        path = output_path or CONFIG_PATH

        config = self._load_config(path) if path.exists() else {}

        # Update tier symbol lists
        tier_syms: Dict[str, List[str]] = {"A": [], "B": [], "C": []}
        for sym, tier in sorted(classification.tier_assignments.items()):
            tier_syms[tier.value].append(sym)

        yaml_content = {
            "universe": {
                **self._config,
                "tiers": {
                    t: {
                        **self._config["tiers"][t],
                        "symbols": tier_syms[t],
                    }
                    for t in ["A", "B", "C"]
                },
                "frozen_classification": {
                    "observation_start": classification.observation_start.isoformat(),
                    "observation_end": classification.observation_end.isoformat(),
                    "frozen": True,
                    "symbols": {
                        sym: {
                            "tier": classification.tier_assignments[sym].value,
                            "sector": classification.sectors.get(sym, "Unknown"),
                            "median_spread_bps": round(
                                classification.spread_profiles[sym].median_spread_bps, 2
                            ),
                            "median_daily_trades": classification.volume_profiles[sym].median_daily_trades,
                            "median_daily_dollar_volume": round(
                                classification.volume_profiles[sym].median_daily_dollar_volume, 0
                            ),
                            "adv_shares": classification.volume_profiles[sym].adv_shares,
                        }
                        for sym in sorted(classification.tier_assignments.keys())
                    },
                    "excluded": [
                        {"symbol": sym, "reason": reason}
                        for sym, reason in classification.excluded_symbols
                    ],
                },
            }
        }

        with open(path, "w") as f:
            yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

        logger.info("Universe frozen to %s", path)
        return path
