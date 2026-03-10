"""Dataset builders backed by the successor-package pipeline."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from l1_microstructure.config import FrameworkConfig
from l1_microstructure.events import MarketEvent
from l1_microstructure.labeling import ForwardDriftLabeler, HorizonLabelRequest
from l1_microstructure.pipeline import L1MicrostructureStateMachine

from .interfaces import DatasetSlice


class PipelineTransitionDatasetBuilder:
    def __init__(
        self,
        events: Iterable[MarketEvent],
        config: FrameworkConfig | None = None,
        labeler: ForwardDriftLabeler | None = None,
    ):
        self.events = sorted(list(events), key=lambda current: current.timestamp_ns)
        self.config = config or FrameworkConfig()
        self.labeler = labeler or ForwardDriftLabeler()

    def build_state_panel(self, symbol: str) -> DatasetSlice:
        machine = L1MicrostructureStateMachine(self.config)
        rows: list[dict[str, object]] = []
        for event in self.events:
            update = machine.on_event(event)
            if update is None or update.state.symbol != symbol:
                continue
            rows.append(
                {
                    "symbol": update.state.symbol,
                    "timestamp_ns": update.state.timestamp_ns,
                    "state_label": update.state.label,
                    "spread_norm": update.state.spread_norm,
                    "quote_pressure": update.state.quote_pressure,
                    "trade_pressure": update.state.trade_pressure,
                    "flicker_intensity": update.state.flicker_intensity,
                    "realized_volatility": update.state.realized_volatility,
                    "dominant_regime": update.regime.dominant_regime.value,
                    "regime_confidence": update.regime.confidence,
                    "expected_holding_time_ns": update.regime.expected_holding_time_ns,
                }
            )
        return DatasetSlice(name=f"{symbol}_state_panel", frame=pd.DataFrame(rows), metadata={"row_count": len(rows)})

    def build_transition_panel(self, symbol: str) -> DatasetSlice:
        machine = L1MicrostructureStateMachine(self.config)
        rows: list[dict[str, object]] = []
        symbol_events = [event for event in self.events if event.symbol == symbol]
        horizons = self.config.transition.drift_horizon_ns_values
        for event in self.events:
            prior_state = machine.previous_state
            update = machine.on_event(event)
            if update is None or update.state.symbol != symbol or update.transition_edge is None:
                continue
            for horizon_ns in horizons:
                label = self.labeler.label(
                    HorizonLabelRequest(
                        symbol=symbol,
                        horizon_ns=horizon_ns,
                        start_timestamp_ns=update.state.timestamp_ns,
                        reference_price=update.state.book.microprice,
                        metadata={"state_label": update.state.label},
                    ),
                    symbol_events,
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "timestamp_ns": update.state.timestamp_ns,
                        "from_state": update.transition_edge.from_state,
                        "to_state": update.transition_edge.to_state,
                        "regime": update.transition_edge.regime.value,
                        "transition_probability": update.diagnostic.transition_probability if update.diagnostic else None,
                        "entropy": update.diagnostic.entropy if update.diagnostic else None,
                        "alpha_score": update.diagnostic.alpha_score if update.diagnostic else None,
                        "horizon_ns": int(horizon_ns),
                        "horizon_ms": int(horizon_ns / 1_000_000),
                        "horizon_label": f"{int(horizon_ns / 1_000_000)}ms",
                        "realized_drift_bps": label.realized_drift_bps,
                        "censored": label.censored,
                        "holding_time_ns": update.state.timestamp_ns - prior_state.timestamp_ns if prior_state is not None else 0,
                    }
                )
        return DatasetSlice(
            name=f"{symbol}_transition_panel",
            frame=pd.DataFrame(rows),
            metadata={
                "row_count": len(rows),
                "horizon_count": len(horizons),
                "horizon_ns_values": tuple(int(value) for value in horizons),
            },
        )