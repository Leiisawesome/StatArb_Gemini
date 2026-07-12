"""Runtime artifact bundle helpers for successor-package replay and paper flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from l1_microstructure.calibration.interfaces import (
    ExecutionCalibrationArtifact,
    RegimeCalibrationArtifact,
    StateCalibrationArtifact,
    StateRegimeSurface,
)

from .interfaces import ArtifactMetadata
from .store import LocalArtifactStore


@dataclass(frozen=True, slots=True)
class RuntimeArtifactBundle:
    state_calibration: StateCalibrationArtifact | None = None
    regime_calibration: RegimeCalibrationArtifact | None = None
    execution_calibration: ExecutionCalibrationArtifact | None = None
    transition_model: dict[str, Any] | None = None
    artifact_ids: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    symbol: str
    trade_date: str
    created_at: str
    artifact_ids: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunQualityGate:
    minimum_fill_rate: float | None = None
    maximum_cancel_rate: float | None = None
    maximum_drift_tracking_error_bps: float | None = None
    maximum_unseen_edge_rate: float | None = None


class ArtifactBundleLoader:
    EXPECTED_VERSIONS = {
        "state_calibration": "v1",
        "regime_calibration": "v1",
        "execution_calibration": "v1",
        "transition_model": "v1",
    }

    def __init__(self, store: LocalArtifactStore):
        self.store = store

    def load_runtime_bundle(
        self,
        *,
        state_calibration_id: str | None = None,
        regime_calibration_id: str | None = None,
        execution_calibration_id: str | None = None,
        transition_model_id: str | None = None,
    ) -> RuntimeArtifactBundle:
        state_calibration = self._load_state_calibration(state_calibration_id) if state_calibration_id else None
        regime_calibration = self._load_regime_calibration(regime_calibration_id) if regime_calibration_id else None
        execution_calibration = (
            self._load_execution_calibration(execution_calibration_id) if execution_calibration_id else None
        )
        transition_model = self.store.load(transition_model_id) if transition_model_id else None
        artifact_ids = {
            key: value
            for key, value in {
                "state_calibration": state_calibration_id,
                "regime_calibration": regime_calibration_id,
                "execution_calibration": execution_calibration_id,
                "transition_model": transition_model_id,
            }.items()
            if value is not None
        }
        return RuntimeArtifactBundle(
            state_calibration=state_calibration,
            regime_calibration=regime_calibration,
            execution_calibration=execution_calibration,
            transition_model=transition_model,
            artifact_ids=artifact_ids,
        )

    def _load_state_calibration(self, artifact_id: str) -> StateCalibrationArtifact:
        self._validate_metadata(artifact_id, expected_type="state_calibration")
        payload = self.store.load(artifact_id)
        self._require_payload_keys(
            payload,
            artifact_id,
            ("symbol", "spread_quantiles", "volatility_quantiles", "flicker_baseline", "quote_pressure_scale"),
        )
        return StateCalibrationArtifact(
            symbol=str(payload["symbol"]),
            spread_quantiles=tuple(payload["spread_quantiles"]),
            volatility_quantiles=tuple(payload["volatility_quantiles"]),
            flicker_baseline=float(payload["flicker_baseline"]),
            quote_pressure_scale=float(payload["quote_pressure_scale"]),
            regime_surfaces={
                str(key): StateRegimeSurface(
                    spread_quantiles=tuple(value["spread_quantiles"]),
                    volatility_quantiles=tuple(value["volatility_quantiles"]),
                    flicker_baseline=float(value["flicker_baseline"]),
                    quote_pressure_scale=float(value["quote_pressure_scale"]),
                    sample_count=int(value.get("sample_count", 0)),
                )
                for key, value in payload.get("regime_surfaces", {}).items()
            },
            metadata=dict(payload.get("metadata", {})),
        )

    def _load_regime_calibration(self, artifact_id: str) -> RegimeCalibrationArtifact:
        self._validate_metadata(artifact_id, expected_type="regime_calibration")
        payload = self.store.load(artifact_id)
        self._require_payload_keys(payload, artifact_id, ("symbol", "regime_priors", "holding_time_seconds"))
        return RegimeCalibrationArtifact(
            symbol=str(payload["symbol"]),
            regime_priors={str(key): float(value) for key, value in payload["regime_priors"].items()},
            holding_time_seconds={str(key): float(value) for key, value in payload["holding_time_seconds"].items()},
            metadata=dict(payload.get("metadata", {})),
        )

    def _load_execution_calibration(self, artifact_id: str) -> ExecutionCalibrationArtifact:
        self._validate_metadata(artifact_id, expected_type="execution_calibration")
        payload = self.store.load(artifact_id)
        self._require_payload_keys(
            payload,
            artifact_id,
            (
                "symbol",
                "fill_probability_intercept",
                "alignment_weight",
                "spread_penalty",
                "slippage_intercept_bps",
                "spread_slippage_weight",
                "adverse_selection_weight",
                "regime_fill_multipliers",
                "regime_slippage_multipliers",
            ),
        )
        return ExecutionCalibrationArtifact(
            symbol=str(payload["symbol"]),
            fill_probability_intercept=float(payload["fill_probability_intercept"]),
            alignment_weight=float(payload["alignment_weight"]),
            spread_penalty=float(payload["spread_penalty"]),
            slippage_intercept_bps=float(payload["slippage_intercept_bps"]),
            spread_slippage_weight=float(payload["spread_slippage_weight"]),
            adverse_selection_weight=float(payload["adverse_selection_weight"]),
            regime_fill_multipliers={
                str(key): float(value) for key, value in payload["regime_fill_multipliers"].items()
            },
            regime_slippage_multipliers={
                str(key): float(value) for key, value in payload["regime_slippage_multipliers"].items()
            },
            metadata=dict(payload.get("metadata", {})),
        )

    def _validate_metadata(self, artifact_id: str, *, expected_type: str) -> ArtifactMetadata:
        metadata = self.store.load_metadata(artifact_id)
        if metadata.artifact_type != expected_type:
            raise ValueError(f"artifact {artifact_id} has type {metadata.artifact_type}, expected {expected_type}")
        expected_version = self.EXPECTED_VERSIONS.get(expected_type)
        if expected_version is not None and metadata.version != expected_version:
            raise ValueError(f"artifact {artifact_id} has version {metadata.version}, expected {expected_version}")
        if metadata.payload_format not in {None, "json"}:
            raise ValueError(f"artifact {artifact_id} uses unsupported payload format {metadata.payload_format}")
        return metadata

    @staticmethod
    def _require_payload_keys(payload: dict[str, Any], artifact_id: str, required_keys: tuple[str, ...]) -> None:
        missing = [key for key in required_keys if key not in payload]
        if missing:
            raise ValueError(f"artifact {artifact_id} is missing required keys: {missing}")


class ArtifactBundleSelector:
    REQUIRED_TYPES = ("state_calibration", "regime_calibration", "execution_calibration", "transition_model")
    MANIFEST_TYPE = "run_manifest"

    def __init__(self, store: LocalArtifactStore):
        self.store = store
        self.loader = ArtifactBundleLoader(store)

    def resolve_latest_for_symbol(self, symbol: str) -> RuntimeArtifactBundle:
        manifests = self.list_run_manifests(symbol)
        if not manifests:
            raise ValueError(f"no complete artifact bundle found for symbol {symbol}")
        manifests.sort(key=lambda manifest: (datetime.fromisoformat(manifest.created_at), manifest.run_id))
        return self.resolve_by_run_id(symbol=symbol, run_id=manifests[-1].run_id)

    def resolve_latest_passing_for_symbol(
        self,
        symbol: str,
        quality_gate: RunQualityGate | None = None,
    ) -> RuntimeArtifactBundle:
        run_manifests = self.list_run_manifests(symbol, passing_only=True, quality_gate=quality_gate)
        if not run_manifests:
            raise ValueError(f"no validation-passing run manifest found for symbol {symbol}")
        run_manifests.sort(key=lambda manifest: (datetime.fromisoformat(manifest.created_at), manifest.run_id))
        return self.resolve_by_run_id(symbol=symbol, run_id=run_manifests[-1].run_id)

    def resolve_for_symbol_on_date(self, *, symbol: str, trade_date: str) -> RuntimeArtifactBundle:
        run_manifests = [manifest for manifest in self.list_run_manifests(symbol) if manifest.trade_date == trade_date]
        if not run_manifests:
            raise ValueError(f"no run manifest found for symbol {symbol} on trade_date {trade_date}")
        run_manifests.sort(key=lambda manifest: (datetime.fromisoformat(manifest.created_at), manifest.run_id))
        return self.resolve_by_run_id(symbol=symbol, run_id=run_manifests[-1].run_id)

    def resolve_passing_for_symbol_on_date(
        self,
        *,
        symbol: str,
        trade_date: str,
        quality_gate: RunQualityGate | None = None,
    ) -> RuntimeArtifactBundle:
        run_manifests = [
            manifest
            for manifest in self.list_run_manifests(symbol, passing_only=True, quality_gate=quality_gate)
            if manifest.trade_date == trade_date
        ]
        if not run_manifests:
            raise ValueError(f"no validation-passing run manifest found for symbol {symbol} on trade_date {trade_date}")
        run_manifests.sort(key=lambda manifest: (datetime.fromisoformat(manifest.created_at), manifest.run_id))
        return self.resolve_by_run_id(symbol=symbol, run_id=run_manifests[-1].run_id)

    def resolve_by_run_id(self, *, symbol: str, run_id: str) -> RuntimeArtifactBundle:
        run_manifest = next(
            (manifest for manifest in self.list_run_manifests(symbol) if manifest.run_id == run_id),
            None,
        )
        if run_manifest is None:
            raise ValueError(f"no committed run manifest found for symbol {symbol}, run_id {run_id}")
        if run_manifest.symbol != symbol:
            raise ValueError(f"run manifest {run_id} belongs to {run_manifest.symbol}, expected {symbol}")
        missing = [
            artifact_type for artifact_type in self.REQUIRED_TYPES if artifact_type not in run_manifest.artifact_ids
        ]
        if missing:
            raise ValueError(f"incomplete artifact bundle for symbol {symbol}, run_id {run_id}: missing {missing}")
        selected: dict[str, str] = {}
        for artifact_type in self.REQUIRED_TYPES:
            artifact_id = run_manifest.artifact_ids[artifact_type]
            metadata = self.store.load_metadata(artifact_id)
            if metadata.artifact_type != artifact_type:
                raise ValueError(
                    f"run manifest artifact {artifact_id} has type {metadata.artifact_type}, expected {artifact_type}"
                )
            if metadata.metadata.get("symbol") != symbol or metadata.metadata.get("run_id") != run_id:
                raise ValueError(f"run manifest artifact {artifact_id} does not belong to {symbol}/{run_id}")
            selected[artifact_type] = artifact_id
        bundle = self.loader.load_runtime_bundle(
            state_calibration_id=selected["state_calibration"],
            regime_calibration_id=selected["regime_calibration"],
            execution_calibration_id=selected["execution_calibration"],
            transition_model_id=selected["transition_model"],
        )
        return RuntimeArtifactBundle(
            state_calibration=bundle.state_calibration,
            regime_calibration=bundle.regime_calibration,
            execution_calibration=bundle.execution_calibration,
            transition_model=bundle.transition_model,
            artifact_ids=bundle.artifact_ids,
            metadata={
                "run_id": run_id,
                "symbol": symbol,
                **run_manifest.metadata,
            },
        )

    def resolve_passing_by_run_id(
        self,
        *,
        symbol: str,
        run_id: str,
        quality_gate: RunQualityGate | None = None,
    ) -> RuntimeArtifactBundle:
        approved = any(
            manifest.run_id == run_id
            for manifest in self.list_run_manifests(symbol, passing_only=True, quality_gate=quality_gate)
        )
        if not approved:
            raise ValueError(f"run {run_id} for {symbol} is not committed and validation-approved")
        return self.resolve_by_run_id(symbol=symbol, run_id=run_id)

    def available_run_ids(self, symbol: str) -> list[str]:
        return sorted(manifest.run_id for manifest in self.list_run_manifests(symbol))

    def list_run_manifests(
        self,
        symbol: str,
        passing_only: bool = False,
        quality_gate: RunQualityGate | None = None,
    ) -> list[RunManifest]:
        manifests: list[RunManifest] = []
        for metadata in self.store.list_metadata(self.MANIFEST_TYPE):
            if metadata.metadata.get("symbol") != symbol:
                continue
            payload = self.store.load(metadata.artifact_id)
            manifest = RunManifest(
                run_id=str(payload["run_id"]),
                symbol=str(payload["symbol"]),
                trade_date=str(payload["trade_date"]),
                created_at=str(payload["created_at"]),
                artifact_ids={str(key): str(value) for key, value in payload.get("artifact_ids", {}).items()},
                metadata=dict(payload.get("metadata", {})),
            )
            if passing_only and not bool(manifest.metadata.get("validation_passed", False)):
                continue
            if quality_gate is not None and not self._passes_quality_gate(manifest, quality_gate):
                continue
            manifests.append(manifest)
        return manifests

    @staticmethod
    def _passes_quality_gate(manifest: RunManifest, quality_gate: RunQualityGate) -> bool:
        metadata = manifest.metadata
        if quality_gate.minimum_fill_rate is not None:
            fill_rate = float(metadata.get("mean_test_fill_rate", 0.0))
            if fill_rate < quality_gate.minimum_fill_rate:
                return False
        if quality_gate.maximum_cancel_rate is not None:
            cancel_rate = float(metadata.get("mean_test_cancel_rate", 0.0))
            if cancel_rate > quality_gate.maximum_cancel_rate:
                return False
        if quality_gate.maximum_drift_tracking_error_bps is not None:
            tracking_error = float(metadata.get("mean_execution_drift_tracking_error_bps", 0.0))
            if tracking_error > quality_gate.maximum_drift_tracking_error_bps:
                return False
        if quality_gate.maximum_unseen_edge_rate is not None:
            unseen_edge_rate = float(metadata.get("mean_unseen_edge_rate", 0.0))
            if unseen_edge_rate > quality_gate.maximum_unseen_edge_rate:
                return False
        return True
