"""
Microstructure analysis module for tick/quote-level flow alpha research.

This module implements the Phase 1 (Data Ingestion) and Phase 2 (Foundation
Diagnostics) pipeline as specified in the Flow Alpha Hypothesis Set (FAHS v1.5)
and the Implementation Blueprint v1.6-FINAL.

Sub-modules:
    ingestion       - Universe construction, bulk download, validation
    classification  - Lee-Ready trade sign classification
    bucketing       - Volume-clock bucket engine
    metrics         - Derived flow metric computation
    diagnostics     - Phase 2 gate computations (persistence, economics, etc.)
    schema          - ClickHouse DDL definitions
"""

from core_engine.microstructure.constants import CONSTANTS_VERSION

__all__ = ["CONSTANTS_VERSION"]
