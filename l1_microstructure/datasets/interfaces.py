"""Protocols for building research-ready transition datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True, slots=True)
class DatasetSlice:
    name: str
    frame: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


class TransitionDatasetBuilder(Protocol):
    def build_state_panel(self, symbol: str) -> DatasetSlice:
        """Build a state-level research panel for one symbol."""

    def build_transition_panel(self, symbol: str) -> DatasetSlice:
        """Build a transition-edge panel for one symbol."""