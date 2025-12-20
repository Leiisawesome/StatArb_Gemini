"""
Papertest Experiment Framework
==============================

Mirrors backtest/experiments/base_experiment.py:
- Orchestrate a papertest engine as a black box
- Config-driven execution
- Structured results and persistence
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PapertestResult:
    # Metadata
    experiment_name: str
    experiment_type: str
    run_timestamp: datetime
    duration_seconds: float

    # Engine stats / outputs (pass-through)
    engine_stats: Dict[str, Any] = field(default_factory=dict)
    replay_stats: Dict[str, Any] = field(default_factory=dict)
    risk_stats: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=dict)

    # High-level performance (best-effort; depends on broker / risk book integration)
    total_pnl: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    max_drawdown: float = 0.0

    # Status
    success: bool = True
    error_message: Optional[str] = None

    # Experiment-specific
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_name": self.experiment_name,
            "experiment_type": self.experiment_type,
            "run_timestamp": self.run_timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "engine_stats": self.engine_stats,
            "replay_stats": self.replay_stats,
            "risk_stats": self.risk_stats,
            "execution_stats": self.execution_stats,
            "performance": {
                "total_pnl": self.total_pnl,
                "realized_pnl": self.realized_pnl,
                "unrealized_pnl": self.unrealized_pnl,
                "max_drawdown": self.max_drawdown,
            },
            "custom_metrics": self.custom_metrics,
            "success": self.success,
            "error_message": self.error_message,
        }


class BasePapertestExperiment(ABC):
    def __init__(self, config: Dict[str, Any], output_dir: str = "papertest/results"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def run(self) -> PapertestResult: ...

    @abstractmethod
    def get_description(self) -> str: ...

    def print_summary(self, result: PapertestResult) -> None:
        print("\n" + "=" * 80)
        print(f"📎 PAPERTEST SUMMARY: {result.experiment_name}")
        print("=" * 80)
        print(f"Type:           {result.experiment_type}")
        print(f"Status:         {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"Duration:       {result.duration_seconds:.2f}s")
        print()
        if result.success:
            perf = result.to_dict().get("performance", {})
            print("Performance (best-effort):")
            print(f"  Total PnL:      {perf.get('total_pnl', 0.0):>12.2f}")
            print(f"  Realized PnL:   {perf.get('realized_pnl', 0.0):>12.2f}")
            print(f"  Unrealized PnL: {perf.get('unrealized_pnl', 0.0):>12.2f}")
            print(f"  Max Drawdown:   {perf.get('max_drawdown', 0.0):>12.2f}")
            if result.custom_metrics:
                print()
                print("Custom Metrics:")
                for k, v in result.custom_metrics.items():
                    print(f"  {k:<24} {v}")
        else:
            print(f"❌ Error: {result.error_message}")
        print("=" * 80)

    def save_results(self, result: PapertestResult) -> None:
        ts = result.run_timestamp.strftime("%Y%m%d_%H%M%S")
        slug = result.experiment_name.replace(" ", "_").lower()
        json_path = self.output_dir / f"{slug}_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        self.logger.info(f"Results saved to: {json_path}")


