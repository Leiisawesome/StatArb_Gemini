"""Protocols for model artifact persistence and retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    artifact_id: str
    artifact_type: str
    version: str
    created_at: str
    tags: tuple[str, ...] = ()
    payload_hash: str | None = None
    payload_format: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ArtifactStore(Protocol):
    def save(self, metadata: ArtifactMetadata, payload: dict[str, Any]) -> None:
        """Persist a versioned artifact payload."""

    def load(self, artifact_id: str) -> dict[str, Any]:
        """Load a previously persisted artifact payload."""