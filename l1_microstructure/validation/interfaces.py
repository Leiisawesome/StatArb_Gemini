"""Protocols for research validation and robustness testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class RegimeSplitSpec:
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    label: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    passed: bool
    summary: dict[str, float]
    failures: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class ValidationHarness(Protocol):
    def run(self, dataset: pd.DataFrame, splits: list[RegimeSplitSpec]) -> ValidationReport:
        """Run OOS, regime-conditioned, and stability diagnostics."""