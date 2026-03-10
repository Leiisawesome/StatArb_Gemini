"""Disk-backed artifact persistence for successor-package research workflows."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from .interfaces import ArtifactMetadata


class LocalArtifactStore:
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def save(self, metadata: ArtifactMetadata, payload: dict[str, Any]) -> None:
        artifact_dir = self.root_path / metadata.artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        payload_bytes = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
        payload_hash = sha256(payload_bytes).hexdigest()
        manifest = asdict(metadata)
        manifest["payload_hash"] = payload_hash
        manifest["payload_format"] = "pickle"

        (artifact_dir / "metadata.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        (artifact_dir / "payload.pkl").write_bytes(payload_bytes)

    def load(self, artifact_id: str) -> dict[str, Any]:
        artifact_dir = self.root_path / artifact_id
        payload_bytes = (artifact_dir / "payload.pkl").read_bytes()
        manifest = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
        expected_hash = manifest.get("payload_hash")
        if expected_hash is not None:
            actual_hash = sha256(payload_bytes).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"artifact payload hash mismatch for {artifact_id}")
        return pickle.loads(payload_bytes)

    def load_metadata(self, artifact_id: str) -> ArtifactMetadata:
        artifact_dir = self.root_path / artifact_id
        manifest = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
        return ArtifactMetadata(
            artifact_id=manifest["artifact_id"],
            artifact_type=manifest["artifact_type"],
            version=manifest["version"],
            created_at=manifest["created_at"],
            tags=tuple(manifest.get("tags", ())),
            payload_hash=manifest.get("payload_hash"),
            payload_format=manifest.get("payload_format"),
            metadata=dict(manifest.get("metadata", {})),
        )

    def list_metadata(self, artifact_type: str | None = None) -> list[ArtifactMetadata]:
        metadata_records: list[ArtifactMetadata] = []
        for child in sorted(self.root_path.iterdir()):
            if not child.is_dir():
                continue
            metadata_path = child / "metadata.json"
            if not metadata_path.exists():
                continue
            metadata = self.load_metadata(child.name)
            if artifact_type is not None and metadata.artifact_type != artifact_type:
                continue
            metadata_records.append(metadata)
        return metadata_records