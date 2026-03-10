"""Deterministic replay implementation for historical event streams."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Iterable

from l1_microstructure.events import MarketEvent
from l1_microstructure.ingest.polygon import event_sort_key

from .interfaces import ReplayCheckpoint, ReplayCursor


class DeterministicReplayEngine:
    def __init__(self):
        self._cursor = ReplayCursor(stream_id="uninitialized", speed_multiplier=1.0)

    def replay(self, events: Iterable[MarketEvent], speed_multiplier: float = 1.0) -> Iterable[MarketEvent]:
        ordered_events = sorted(events, key=event_sort_key)
        stream_id = self._stream_id_for_events(ordered_events)
        start_index = self._cursor.current_index if self._cursor.stream_id == stream_id else 0
        self._cursor = ReplayCursor(
            stream_id=stream_id,
            speed_multiplier=speed_multiplier,
            current_index=start_index,
            current_timestamp_ns=ordered_events[start_index - 1].timestamp_ns if ordered_events and start_index > 0 else 0,
        )
        for index in range(start_index, len(ordered_events)):
            event = ordered_events[index]
            self._cursor = ReplayCursor(
                stream_id=stream_id,
                speed_multiplier=speed_multiplier,
                current_index=index + 1,
                current_timestamp_ns=event.timestamp_ns,
            )
            yield event

    def checkpoint(self) -> ReplayCheckpoint:
        return ReplayCheckpoint(
            stream_id=self._cursor.stream_id,
            event_index=self._cursor.current_index,
            event_timestamp_ns=self._cursor.current_timestamp_ns,
        )

    def restore(self, checkpoint: ReplayCheckpoint) -> ReplayCursor:
        self._cursor = ReplayCursor(
            stream_id=checkpoint.stream_id,
            speed_multiplier=self._cursor.speed_multiplier,
            current_index=checkpoint.event_index,
            current_timestamp_ns=checkpoint.event_timestamp_ns,
        )
        return self._cursor

    @staticmethod
    def _stream_id_for_events(events: list[MarketEvent]) -> str:
        if not events:
            return "empty-stream"
        digest = sha1()
        digest.update(str(len(events)).encode("ascii"))
        digest.update(str(events[0].timestamp_ns).encode("ascii"))
        digest.update(str(events[-1].timestamp_ns).encode("ascii"))
        digest.update(events[0].symbol.encode("ascii"))
        return digest.hexdigest()