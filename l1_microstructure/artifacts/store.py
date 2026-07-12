"""Disk-backed artifact persistence for successor-package research workflows."""

from __future__ import annotations

import json
import os
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

        payload_bytes = json.dumps(
            self._json_value(payload),
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        payload_hash = sha256(payload_bytes).hexdigest()
        manifest = asdict(metadata)
        manifest["payload_hash"] = payload_hash
        manifest["payload_format"] = "json"

        self._atomic_write(artifact_dir / "payload.json", payload_bytes)
        self._atomic_write(
            artifact_dir / "metadata.json",
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"),
        )

    def load(self, artifact_id: str) -> dict[str, Any]:
        artifact_dir = self.root_path / artifact_id
        payload_path = artifact_dir / "payload.json"
        if not payload_path.exists():
            raise ValueError(
                f"artifact {artifact_id} uses the retired pickle format; "
                "migrate it explicitly with migrate_legacy_pickle"
            )
        payload_bytes = payload_path.read_bytes()
        manifest = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
        expected_hash = manifest.get("payload_hash")
        if expected_hash is not None:
            actual_hash = sha256(payload_bytes).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(f"artifact payload hash mismatch for {artifact_id}")
        payload = json.loads(payload_bytes)
        if not isinstance(payload, dict):
            raise ValueError(f"artifact payload must be an object for {artifact_id}")
        return payload

    def migrate_legacy_pickle(self, artifact_id: str, *, trusted: bool = False) -> None:
        """Convert one explicitly trusted legacy pickle artifact to JSON."""
        if not trusted:
            raise ValueError("legacy pickle migration requires trusted=True")
        import pickle

        artifact_dir = self.root_path / artifact_id
        payload_path = artifact_dir / "payload.pkl"
        if not payload_path.exists():
            raise ValueError(f"legacy payload does not exist for {artifact_id}")
        payload = pickle.loads(payload_path.read_bytes())
        metadata = self.load_metadata(artifact_id)
        self.save(metadata, payload)

    @classmethod
    def _json_value(cls, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): cls._json_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._json_value(item) for item in value]
        item = getattr(value, "item", None)
        if callable(item):
            return cls._json_value(item())
        isoformat = getattr(value, "isoformat", None)
        if callable(isoformat):
            return isoformat()
        raise TypeError(f"artifact value is not JSON serializable: {type(value).__name__}")

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, path)

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
