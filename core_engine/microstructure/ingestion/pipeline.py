"""
Phase 1 ingestion pipeline orchestrator.

Coordinates the full ingestion workflow: download → validate → classify →
bucket → hash → verify deterministic replay.

Blueprint: v1.6-FINAL Section 1.7
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional

from core_engine.microstructure.constants import CONSTANTS_VERSION
from core_engine.microstructure.types import SymbolDayStatus, Tier

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the end-to-end Phase 1 data ingestion pipeline."""

    async def run_probe(
        self, probe_symbols: Dict[Tier, str], probe_days: int = 3
    ) -> dict:
        """
        Week 0 feasibility probe: 1 symbol per tier × 3 days.

        Runs the full pipeline at small scale to validate:
        - Polygon data quality and timestamp semantics
        - ClickHouse insert/query performance
        - Memory footprint
        - Deterministic replay
        """
        raise NotImplementedError("Step 2: implement probe pipeline")

    async def run_full_ingestion(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, List[SymbolDayStatus]]:
        """
        Full ingestion for all symbols over the date range.

        Stages:
        1. Download trades for all symbol-days
        2. Download quotes for all symbol-days
        3. Validate data quality
        4. Classify trades (Lee-Ready)
        5. Construct volume-clock buckets
        6. Compute SHA256 hashes
        7. Deterministic replay gate
        """
        raise NotImplementedError("Step 6 (Week 1): implement full ingestion")
