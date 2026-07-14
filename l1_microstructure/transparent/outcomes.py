"""Leakage-safe, restartable multi-horizon transition outcome tracking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from heapq import heappop, heappush
from typing import Iterable

from l1_microstructure.features import ObservedState


@dataclass(frozen=True, slots=True)
class PendingHorizonOutcome:
    sequence: int
    symbol: str
    from_state: str
    to_state: str
    regime: str
    start_timestamp_ns: int
    resolve_timestamp_ns: int
    horizon_ns: int
    reference_price: float
    holding_time_ns: int

    def __post_init__(self) -> None:
        if self.sequence < 0 or self.start_timestamp_ns < 0:
            raise ValueError("pending outcome identity is invalid")
        if self.horizon_ns <= 0 or self.resolve_timestamp_ns != self.start_timestamp_ns + self.horizon_ns:
            raise ValueError("pending outcome horizon is inconsistent")
        if self.reference_price <= 0.0 or self.holding_time_ns < 0:
            raise ValueError("pending outcome price or holding time is invalid")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> PendingHorizonOutcome:
        return cls(
            sequence=int(payload["sequence"]),
            symbol=str(payload["symbol"]),
            from_state=str(payload["from_state"]),
            to_state=str(payload["to_state"]),
            regime=str(payload["regime"]),
            start_timestamp_ns=int(payload["start_timestamp_ns"]),
            resolve_timestamp_ns=int(payload["resolve_timestamp_ns"]),
            horizon_ns=int(payload["horizon_ns"]),
            reference_price=float(payload["reference_price"]),
            holding_time_ns=int(payload["holding_time_ns"]),
        )


@dataclass(frozen=True, slots=True)
class ResolvedHorizonOutcome:
    sequence: int
    symbol: str
    from_state: str
    to_state: str
    regime: str
    start_timestamp_ns: int
    target_timestamp_ns: int
    end_timestamp_ns: int
    horizon_ns: int
    holding_time_ns: int
    realized_drift_bps: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class MultiHorizonOutcomeTracker:
    def __init__(self, horizons_ns: Iterable[int], *, max_pending_outcomes: int = 100_000):
        horizons = tuple(sorted({int(value) for value in horizons_ns if int(value) > 0}))
        if not horizons:
            raise ValueError("multi-horizon tracker requires positive horizons")
        if max_pending_outcomes <= 0:
            raise ValueError("multi-horizon pending-outcome bound must be positive")
        self.horizons_ns = horizons
        self.max_pending_outcomes = int(max_pending_outcomes)
        self._heap: list[tuple[int, int, PendingHorizonOutcome]] = []
        self._next_sequence = 0

    @property
    def pending_count(self) -> int:
        return len(self._heap)

    def schedule(
        self,
        *,
        state: ObservedState,
        from_state: str,
        to_state: str,
        regime: str,
        holding_time_ns: int,
    ) -> tuple[PendingHorizonOutcome, ...]:
        if len(self._heap) + len(self.horizons_ns) > self.max_pending_outcomes:
            raise OverflowError("multi-horizon pending-outcome bound exceeded")
        scheduled: list[PendingHorizonOutcome] = []
        for horizon_ns in self.horizons_ns:
            pending = PendingHorizonOutcome(
                sequence=self._next_sequence,
                symbol=state.symbol,
                from_state=from_state,
                to_state=to_state,
                regime=regime,
                start_timestamp_ns=state.timestamp_ns,
                resolve_timestamp_ns=state.timestamp_ns + horizon_ns,
                horizon_ns=horizon_ns,
                reference_price=state.book.microprice,
                holding_time_ns=int(holding_time_ns),
            )
            self._next_sequence += 1
            heappush(self._heap, (pending.resolve_timestamp_ns, pending.sequence, pending))
            scheduled.append(pending)
        return tuple(scheduled)

    def resolve(self, state: ObservedState) -> tuple[ResolvedHorizonOutcome, ...]:
        resolved: list[ResolvedHorizonOutcome] = []
        deferred: list[tuple[int, int, PendingHorizonOutcome]] = []
        while self._heap and self._heap[0][0] <= state.timestamp_ns:
            entry = heappop(self._heap)
            pending = entry[2]
            if pending.symbol != state.symbol:
                deferred.append(entry)
                continue
            drift_bps = ((state.book.microprice - pending.reference_price) / pending.reference_price) * 10_000.0
            resolved.append(
                ResolvedHorizonOutcome(
                    sequence=pending.sequence,
                    symbol=pending.symbol,
                    from_state=pending.from_state,
                    to_state=pending.to_state,
                    regime=pending.regime,
                    start_timestamp_ns=pending.start_timestamp_ns,
                    target_timestamp_ns=pending.resolve_timestamp_ns,
                    end_timestamp_ns=state.timestamp_ns,
                    horizon_ns=pending.horizon_ns,
                    holding_time_ns=pending.holding_time_ns,
                    realized_drift_bps=float(drift_bps),
                )
            )
        for entry in deferred:
            heappush(self._heap, entry)
        return tuple(sorted(resolved, key=lambda item: (item.target_timestamp_ns, item.sequence)))

    def snapshot(self) -> dict[str, object]:
        pending = sorted((entry[2] for entry in self._heap), key=lambda item: item.sequence)
        return {
            "schema_version": 1,
            "horizons_ns": list(self.horizons_ns),
            "max_pending_outcomes": self.max_pending_outcomes,
            "next_sequence": self._next_sequence,
            "pending": [item.to_dict() for item in pending],
        }

    @classmethod
    def restore(cls, payload: dict[str, object]) -> MultiHorizonOutcomeTracker:
        if int(payload.get("schema_version", -1)) != 1:
            raise ValueError("unsupported multi-horizon recovery schema")
        tracker = cls(
            payload["horizons_ns"],
            max_pending_outcomes=int(payload["max_pending_outcomes"]),
        )
        tracker._next_sequence = int(payload["next_sequence"])
        if tracker._next_sequence < 0:
            raise ValueError("recovery next sequence cannot be negative")
        sequences: set[int] = set()
        for item in payload.get("pending", []):
            pending = PendingHorizonOutcome.from_dict(dict(item))
            if pending.sequence in sequences:
                raise ValueError("recovery contains duplicate pending outcome sequences")
            sequences.add(pending.sequence)
            if pending.horizon_ns not in tracker.horizons_ns:
                raise ValueError("recovery contains an unsupported outcome horizon")
            heappush(tracker._heap, (pending.resolve_timestamp_ns, pending.sequence, pending))
        if len(tracker._heap) > tracker.max_pending_outcomes:
            raise ValueError("recovery exceeds the pending-outcome bound")
        if tracker._heap and tracker._next_sequence <= max(entry[1] for entry in tracker._heap):
            raise ValueError("recovery next sequence does not follow pending outcomes")
        return tracker
