"""
Pipeline Trace - End-to-End Signal-to-PnL Tracing
==================================================

Opt-in tracing infrastructure that records a structured checkpoint at every
component boundary in the Signal-to-PnL pipeline.  When enabled
(`enable_pipeline_trace: true` in config), each checkpoint emits a
`TraceCheckpoint` record to a JSONL file.  When disabled the tracer is a
zero-cost no-op.

Checkpoints (CP0-CP7):
    CP0  Market Data Ingestion
    CP1  Feature / Indicator Enrichment
    CP2  Signal Generation
    CP3  Risk Authorization (6-Gate)
    CP4  Order Creation (OMS)
    CP5  Execution / Fill
    CP6  Position Book Update
    CP7  PnL Calculation

Design principles:
    - One `tracer.emit()` call per checkpoint (minimally invasive)
    - Deterministic hashing of inputs/outputs for chain verification
    - JSONL output aligned with EventJournal format
    - Thread-safe, singleton pattern
    - Zero overhead when disabled

Author: StatArb_Gemini Core Engine
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from core_engine.utils.fast_id import get_fast_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Checkpoint enum constants
# ---------------------------------------------------------------------------
CP0_MARKET_DATA = "CP0"
CP0r_REGIME_DETECT = "CP0r"
CP1_ENRICHMENT = "CP1"
CP1s_BAR_SLICE = "CP1s"
CP2_SIGNAL_GEN = "CP2"
CP2q_QUANTITY_SIZING = "CP2q"
CP3_RISK_AUTH = "CP3"
CP4_ORDER_CREATE = "CP4"
CP5_FILL = "CP5"
CP6_POSITION_UPDATE = "CP6"
CP7_PNL = "CP7"

# Primary checkpoints (the original CP0-CP7 funnel)
ALL_CHECKPOINTS = [
    CP0_MARKET_DATA,
    CP1_ENRICHMENT,
    CP2_SIGNAL_GEN,
    CP3_RISK_AUTH,
    CP4_ORDER_CREATE,
    CP5_FILL,
    CP6_POSITION_UPDATE,
    CP7_PNL,
]

# Sub-checkpoints for fine-grained plumbing inspection
SUB_CHECKPOINTS = [
    CP0r_REGIME_DETECT,
    CP1s_BAR_SLICE,
    CP2q_QUANTITY_SIZING,
]

# All checkpoints including sub-checkpoints
ALL_CHECKPOINTS_EXTENDED = ALL_CHECKPOINTS + SUB_CHECKPOINTS

# Checkpoint ordering map for verification
CHECKPOINT_ORDER = {cp: idx for idx, cp in enumerate(ALL_CHECKPOINTS)}


# ---------------------------------------------------------------------------
# TraceCheckpoint dataclass
# ---------------------------------------------------------------------------
@dataclass
class TraceCheckpoint:
    """A single checkpoint record in the pipeline trace."""

    trace_id: str               # Propagated through the chain for one trading decision
    checkpoint: str             # "CP0" .. "CP7"
    component: str              # e.g. "EnhancedSignalGenerator"
    method: str                 # e.g. "generate_signals"
    symbol: str                 # Ticker symbol
    timestamp: str              # ISO-8601 wall-clock time of the checkpoint
    bar_timestamp: str          # ISO-8601 bar/event timestamp being processed
    input_hash: str             # Deterministic hash of input data
    output_hash: str            # Deterministic hash of output data
    input_data: Any = None       # Sanitized input payload (small/JSON-safe)
    output_data: Any = None      # Sanitized output payload (small/JSON-safe)
    input_shape: Dict[str, Any] = field(default_factory=dict)   # e.g. {"rows": 200, "cols": 15}
    output_shape: Dict[str, Any] = field(default_factory=dict)  # e.g. {"signals": 3}
    metadata: Dict[str, Any] = field(default_factory=dict)      # Component-specific details
    elapsed_ms: float = 0.0     # Time spent inside the checkpoint

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSONL output."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic hashing helpers
# ---------------------------------------------------------------------------

def _hash_value(obj: Any) -> str:
    """Produce a deterministic hex digest for an arbitrary Python object.

    Handles DataFrame, ndarray, dict, list, and primitives.
    Returns the first 16 hex chars of SHA-256 for compactness.
    """
    h = hashlib.sha256()

    if isinstance(obj, pd.DataFrame):
        # Use column-sorted, rounded values for determinism
        try:
            # Sort columns, round floats, convert to bytes
            df_sorted = obj.reindex(sorted(obj.columns), axis=1)
            numeric_cols = df_sorted.select_dtypes(include=[np.number]).columns
            df_sorted[numeric_cols] = df_sorted[numeric_cols].round(10)
            h.update(df_sorted.to_csv(index=True).encode("utf-8"))
        except Exception:
            h.update(str(obj.shape).encode("utf-8"))
    elif isinstance(obj, pd.Series):
        try:
            h.update(obj.round(10).to_csv(index=True).encode("utf-8"))
        except Exception:
            h.update(str(len(obj)).encode("utf-8"))
    elif isinstance(obj, np.ndarray):
        h.update(np.round(obj, 10).tobytes())
    elif isinstance(obj, (dict, list)):
        h.update(json.dumps(obj, sort_keys=True, default=str).encode("utf-8"))
    elif obj is None:
        h.update(b"__none__")
    else:
        h.update(str(obj).encode("utf-8"))

    return h.hexdigest()[:16]


def _describe_shape(obj: Any) -> Dict[str, Any]:
    """Return a compact shape descriptor for an object."""
    if isinstance(obj, pd.DataFrame):
        return {"rows": len(obj), "cols": len(obj.columns), "columns": sorted(obj.columns.tolist())}
    elif isinstance(obj, pd.Series):
        return {"length": len(obj), "name": str(obj.name)}
    elif isinstance(obj, np.ndarray):
        return {"shape": list(obj.shape), "dtype": str(obj.dtype)}
    elif isinstance(obj, (list, tuple)):
        return {"length": len(obj)}
    elif isinstance(obj, dict):
        return {"keys": sorted(str(k) for k in obj.keys()), "length": len(obj)}
    else:
        return {"type": type(obj).__name__}


def _sanitize_payload(obj: Any, max_list_items: int = 50) -> Any:
    """Return a JSON-safe, size-conscious representation of input/output payloads."""
    if obj is None:
        return None

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, np.generic):
        return obj.item()

    if isinstance(obj, pd.DataFrame):
        return {"_type": "DataFrame", "shape": _describe_shape(obj)}

    if isinstance(obj, pd.Series):
        return {"_type": "Series", "shape": _describe_shape(obj)}

    if isinstance(obj, np.ndarray):
        return {"_type": "ndarray", "shape": _describe_shape(obj)}

    if isinstance(obj, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in obj.items():
            sanitized[str(key)] = _sanitize_payload(value, max_list_items=max_list_items)
        return sanitized

    if isinstance(obj, (list, tuple)):
        if len(obj) > max_list_items:
            return {"_type": type(obj).__name__, "length": len(obj)}
        return [_sanitize_payload(v, max_list_items=max_list_items) for v in obj]

    if isinstance(obj, (int, float, str, bool)):
        return obj

    return str(obj)


# ---------------------------------------------------------------------------
# PipelineTracer singleton
# ---------------------------------------------------------------------------

class PipelineTracer:
    """
    Singleton tracer that collects checkpoint records across the pipeline.

    Usage:
        tracer = PipelineTracer.get_instance()
        tracer.configure(enabled=True, output_dir="backtest/results")

        # At each checkpoint:
        tracer.emit(
            trace_id=signal_trace_id,
            checkpoint=CP2_SIGNAL_GEN,
            component="EnhancedSignalGenerator",
            method="generate_signals",
            symbol="TSLA",
            bar_timestamp=bar_ts,
            input_data=enriched_df,
            output_data=signals_list,
            metadata={"signal_count": len(signals_list)},
        )
    """

    _instance: Optional[PipelineTracer] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._enabled = False
        self._output_dir: Optional[Path] = None
        self._session_id: Optional[str] = None
        self._file = None
        self._file_lock = threading.Lock()
        self._records: List[TraceCheckpoint] = []
        self._sequence = 0
        self._stats = {
            "checkpoints_emitted": 0,
            "checkpoints_by_type": {},
        }

    @classmethod
    def get_instance(cls) -> PipelineTracer:
        """Get or create the singleton tracer instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def records(self) -> List[TraceCheckpoint]:
        """Return all collected trace records (useful for in-process verification)."""
        return list(self._records)

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def configure(
        self,
        enabled: bool = False,
        output_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Configure the tracer.

        Args:
            enabled: Whether tracing is active
            output_dir: Directory for trace JSONL output
            session_id: Session identifier for the trace file name
        """
        self._enabled = enabled
        if not enabled:
            return

        self._session_id = session_id or f"trace-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        if output_dir:
            self._output_dir = Path(output_dir)
            self._output_dir.mkdir(parents=True, exist_ok=True)
            file_path = self._output_dir / f"{self._session_id}.trace.jsonl"
            self._file = open(file_path, "w", encoding="utf-8")
            logger.info(f"PipelineTracer enabled: writing to {file_path}")
        else:
            logger.info("PipelineTracer enabled: in-memory only (no output_dir)")

        self._records.clear()
        self._sequence = 0
        self._stats = {
            "checkpoints_emitted": 0,
            "checkpoints_by_type": {},
        }

    def emit(
        self,
        trace_id: str,
        checkpoint: str,
        component: str,
        method: str,
        symbol: str,
        bar_timestamp: Any,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        elapsed_ms: float = 0.0,
    ) -> None:
        """
        Emit a trace checkpoint record.

        This is the single call site inserted at each component boundary.
        When tracing is disabled, this is an immediate return (zero cost).

        Args:
            trace_id: UUID/ID linking this checkpoint to its signal chain
            checkpoint: One of CP0..CP7
            component: Class name of the emitting component
            method: Method name where the checkpoint is emitted
            symbol: Ticker symbol being processed
            bar_timestamp: The bar/event timestamp being processed
            input_data: The data entering this checkpoint (for hashing)
            output_data: The data leaving this checkpoint (for hashing)
            metadata: Additional component-specific information
            elapsed_ms: Time spent in this processing step
        """
        if not self._enabled:
            return

        self._sequence += 1

        # Convert bar_timestamp to ISO string
        if isinstance(bar_timestamp, datetime):
            bar_ts_str = bar_timestamp.isoformat()
        else:
            bar_ts_str = str(bar_timestamp)

        record = TraceCheckpoint(
            trace_id=trace_id,
            checkpoint=checkpoint,
            component=component,
            method=method,
            symbol=symbol,
            timestamp=datetime.now(timezone.utc).isoformat(),
            bar_timestamp=bar_ts_str,
            input_hash=_hash_value(input_data),
            output_hash=_hash_value(output_data),
            input_data=_sanitize_payload(input_data),
            output_data=_sanitize_payload(output_data),
            input_shape=_describe_shape(input_data),
            output_shape=_describe_shape(output_data),
            metadata=metadata or {},
            elapsed_ms=elapsed_ms,
        )

        # Store in memory
        self._records.append(record)

        # Update stats
        self._stats["checkpoints_emitted"] += 1
        cp_counts = self._stats["checkpoints_by_type"]
        cp_counts[checkpoint] = cp_counts.get(checkpoint, 0) + 1

        # Write to file if configured
        if self._file is not None:
            with self._file_lock:
                try:
                    line = json.dumps(record.to_dict(), default=str)
                    self._file.write(line + "\n")
                    self._file.flush()
                except Exception as e:
                    logger.warning(f"PipelineTracer write error: {e}")

    def close(self) -> None:
        """Close the trace file and log summary."""
        if self._file is not None:
            with self._file_lock:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None

        if self._enabled and self._stats["checkpoints_emitted"] > 0:
            logger.info(
                f"PipelineTracer closed: {self._stats['checkpoints_emitted']} checkpoints "
                f"emitted across {self._stats['checkpoints_by_type']}"
            )

    def get_trace_for_id(self, trace_id: str) -> List[TraceCheckpoint]:
        """Get all checkpoints for a specific trace_id (trading decision chain)."""
        return [r for r in self._records if r.trace_id == trace_id]

    def get_checkpoints(self, checkpoint: str) -> List[TraceCheckpoint]:
        """Get all records for a specific checkpoint type."""
        return [r for r in self._records if r.checkpoint == checkpoint]

    def get_funnel_summary(self) -> Dict[str, int]:
        """Return checkpoint counts in pipeline order (the 'funnel')."""
        return {cp: self._stats["checkpoints_by_type"].get(cp, 0) for cp in ALL_CHECKPOINTS}

    def get_extended_funnel_summary(self) -> Dict[str, int]:
        """Return checkpoint counts including sub-checkpoints."""
        ordered = [
            CP0_MARKET_DATA, CP0r_REGIME_DETECT,
            CP1_ENRICHMENT, CP1s_BAR_SLICE,
            CP2_SIGNAL_GEN, CP2q_QUANTITY_SIZING,
            CP3_RISK_AUTH,
            CP4_ORDER_CREATE, CP5_FILL, CP6_POSITION_UPDATE, CP7_PNL,
        ]
        return {cp: self._stats["checkpoints_by_type"].get(cp, 0) for cp in ordered}

    def print_funnel(self) -> str:
        """Print a human-readable pipeline funnel summary."""
        funnel = self.get_extended_funnel_summary()
        lines = ["Pipeline Trace Funnel", "=" * 50]
        labels = {
            CP0_MARKET_DATA: "Market Data Ingestion",
            CP0r_REGIME_DETECT: "  └─ Regime Detection",
            CP1_ENRICHMENT: "Feature/Indicator Enrichment",
            CP1s_BAR_SLICE: "  └─ Bar Feature Slice (per-bar)",
            CP2_SIGNAL_GEN: "Signal Generation",
            CP2q_QUANTITY_SIZING: "  └─ Quantity Sizing",
            CP3_RISK_AUTH: "Risk Authorization (6-Gate)",
            CP4_ORDER_CREATE: "Order Creation (OMS)",
            CP5_FILL: "Execution / Fill",
            CP6_POSITION_UPDATE: "Position Book Update",
            CP7_PNL: "PnL Calculation",
        }
        for cp in funnel:
            count = funnel.get(cp, 0)
            label = labels.get(cp, cp)
            lines.append(f"  {cp}: {count:>6}  {label}")

            # Show drop-off between signal gen and risk auth
            if cp == CP2_SIGNAL_GEN and CP3_RISK_AUTH in funnel:
                cp3_count = funnel[CP3_RISK_AUTH]
                if count > 0:
                    # Gather auth vs reject from metadata
                    auth_records = self.get_checkpoints(CP3_RISK_AUTH)
                    authorized = sum(1 for r in auth_records if r.metadata.get("authorized", False))
                    rejected = len(auth_records) - authorized
                    lines.append(f"          -> {authorized} authorized / {rejected} rejected")

        lines.append("=" * 50)
        output = "\n".join(lines)
        print(output)
        return output


# ---------------------------------------------------------------------------
# Convenience: module-level access
# ---------------------------------------------------------------------------

def get_tracer() -> PipelineTracer:
    """Get the global PipelineTracer singleton."""
    return PipelineTracer.get_instance()
