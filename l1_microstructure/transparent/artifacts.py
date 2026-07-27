"""Strict JSON artifact persistence and selection for v2 engine bundles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from l1_microstructure.artifacts import ArtifactMetadata, LocalArtifactStore
from l1_microstructure.calibration.interfaces import (
    ExecutionCalibrationArtifact,
    StateCalibrationArtifact,
    StateRegimeSurface,
)

from .contracts import (
    TRANSPARENT_ENGINE_VERSION,
    EngineArtifactContract,
    EngineEvaluation,
    PromotionThresholds,
    TransparentPromotionGate,
)
from .edges import HierarchicalTransitionModel
from .engine import TransparentEngineArtifacts
from .regime import SemiMarkovRegimeModel
from .utility import UtilityModel
from .vector import StateVectorModel


TRANSPARENT_MANIFEST_TYPE = "transparent_run_manifest"
TRANSPARENT_VALIDATION_TYPE = "transparent_validation_report"


@dataclass(frozen=True, slots=True)
class TransparentRunManifest:
    run_id: str
    symbol: str
    trade_date: str
    created_at: str
    engine_version: str
    artifact_ids: dict[str, str]
    metadata: dict[str, object] = field(default_factory=dict)


class TransparentArtifactPublisher:
    def __init__(self, store: LocalArtifactStore):
        self.store = store

    def publish(
        self,
        *,
        run_id: str,
        trade_date: str,
        artifacts: TransparentEngineArtifacts,
        validation_report: dict[str, object],
        created_at: str | None = None,
    ) -> TransparentRunManifest:
        if artifacts.state_calibration is None or artifacts.execution_calibration is None:
            raise ValueError("published v2 bundle requires state and execution calibration artifacts")
        _validate_validation_report(validation_report)
        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        payloads = {
            "state_calibration": asdict(artifacts.state_calibration),
            "execution_calibration": asdict(artifacts.execution_calibration),
            "state_vector_model": artifacts.state_vector_model.to_dict(),
            "semi_markov_regime_model": artifacts.semi_markov_regime_model.to_dict(),
            "hierarchical_transition_model": artifacts.hierarchical_transition_model.to_dict(),
            "utility_model": artifacts.utility_model.to_dict(),
        }
        reserved_ids = [f"{run_id}-{kind}" for kind in payloads]
        reserved_ids.extend(
            (f"{run_id}-{TRANSPARENT_VALIDATION_TYPE}", f"{run_id}-{TRANSPARENT_MANIFEST_TYPE}")
        )
        if any((self.store.root_path / artifact_id).exists() for artifact_id in reserved_ids):
            raise ValueError(f"transparent run {run_id} already exists; published runs are immutable")
        artifact_ids: dict[str, str] = {}
        for artifact_type, payload in payloads.items():
            artifact_id = f"{run_id}-{artifact_type}"
            self.store.save(
                ArtifactMetadata(
                    artifact_id=artifact_id,
                    artifact_type=artifact_type,
                    version=TRANSPARENT_ENGINE_VERSION,
                    created_at=timestamp,
                    tags=("l1_microstructure", "transparent_engine", artifacts.symbol),
                    metadata={
                        "symbol": artifacts.symbol,
                        "run_id": run_id,
                        "engine_version": TRANSPARENT_ENGINE_VERSION,
                    },
                ),
                payload,
            )
            artifact_ids[artifact_type] = artifact_id
        artifact_hashes = {
            kind: str(self.store.load_metadata(artifact_id).payload_hash)
            for kind, artifact_id in artifact_ids.items()
        }
        validation_id = f"{run_id}-{TRANSPARENT_VALIDATION_TYPE}"
        bound_validation_report = {
            **dict(validation_report),
            "run_id": run_id,
            "symbol": artifacts.symbol,
            "engine_version": TRANSPARENT_ENGINE_VERSION,
            "artifact_hashes": artifact_hashes,
        }
        self.store.save(
            ArtifactMetadata(
                artifact_id=validation_id,
                artifact_type=TRANSPARENT_VALIDATION_TYPE,
                version=TRANSPARENT_ENGINE_VERSION,
                created_at=timestamp,
                tags=("l1_microstructure", "transparent_validation", artifacts.symbol),
                metadata={
                    "symbol": artifacts.symbol,
                    "run_id": run_id,
                    "engine_version": TRANSPARENT_ENGINE_VERSION,
                },
            ),
            bound_validation_report,
        )
        artifact_ids[TRANSPARENT_VALIDATION_TYPE] = validation_id
        manifest = TransparentRunManifest(
            run_id=run_id,
            symbol=artifacts.symbol,
            trade_date=trade_date,
            created_at=timestamp,
            engine_version=TRANSPARENT_ENGINE_VERSION,
            artifact_ids=artifact_ids,
            metadata={
                "validation_passed": validation_report.get("passed") is True,
                **dict(artifacts.metadata),
            },
        )
        manifest_id = f"{run_id}-{TRANSPARENT_MANIFEST_TYPE}"
        self.store.save(
            ArtifactMetadata(
                artifact_id=manifest_id,
                artifact_type=TRANSPARENT_MANIFEST_TYPE,
                version=TRANSPARENT_ENGINE_VERSION,
                created_at=timestamp,
                tags=("l1_microstructure", "transparent_manifest", artifacts.symbol),
                metadata={
                    "symbol": artifacts.symbol,
                    "run_id": run_id,
                    "engine_version": TRANSPARENT_ENGINE_VERSION,
                },
            ),
            {
                "run_id": manifest.run_id,
                "symbol": manifest.symbol,
                "trade_date": manifest.trade_date,
                "created_at": manifest.created_at,
                "engine_version": manifest.engine_version,
                "artifact_ids": manifest.artifact_ids,
                "metadata": manifest.metadata,
            },
        )
        return manifest


class TransparentArtifactBundleLoader:
    def __init__(self, store: LocalArtifactStore):
        self.store = store

    def load(self, manifest: TransparentRunManifest) -> TransparentEngineArtifacts:
        if manifest.engine_version != TRANSPARENT_ENGINE_VERSION:
            raise ValueError(f"unsupported transparent manifest version: {manifest.engine_version}")
        contract = EngineArtifactContract.for_version(manifest.engine_version)
        versions: dict[str, str] = {}
        for artifact_type in contract.required_artifact_types:
            artifact_id = manifest.artifact_ids.get(artifact_type, "")
            if artifact_id:
                metadata = self.store.load_metadata(artifact_id)
                if metadata.artifact_type != artifact_type:
                    raise ValueError(f"v2 artifact {artifact_id} has type {metadata.artifact_type}")
                if metadata.metadata.get("symbol") != manifest.symbol or metadata.metadata.get("run_id") != manifest.run_id:
                    raise ValueError(f"v2 artifact {artifact_id} does not belong to the selected run")
                versions[artifact_type] = metadata.version
        contract.validate_manifest(manifest.artifact_ids, versions)
        payload = {kind: self.store.load(manifest.artifact_ids[kind]) for kind in contract.required_artifact_types}
        return TransparentEngineArtifacts(
            state_vector_model=StateVectorModel.from_dict(payload["state_vector_model"]),
            semi_markov_regime_model=SemiMarkovRegimeModel.from_dict(payload["semi_markov_regime_model"]),
            hierarchical_transition_model=HierarchicalTransitionModel.from_dict(
                payload["hierarchical_transition_model"]
            ),
            utility_model=UtilityModel.from_dict(payload["utility_model"]),
            state_calibration=_state_calibration(payload["state_calibration"]),
            execution_calibration=_execution_calibration(payload["execution_calibration"]),
            artifact_ids={kind: manifest.artifact_ids[kind] for kind in contract.required_artifact_types},
            metadata={"run_id": manifest.run_id, "symbol": manifest.symbol, **manifest.metadata},
        )


class TransparentArtifactSelector:
    def __init__(self, store: LocalArtifactStore):
        self.store = store
        self.loader = TransparentArtifactBundleLoader(store)

    def list_manifests(self, symbol: str, *, passing_only: bool = False) -> list[TransparentRunManifest]:
        manifests: list[TransparentRunManifest] = []
        for metadata in self.store.list_metadata(TRANSPARENT_MANIFEST_TYPE):
            if (
                metadata.version != TRANSPARENT_ENGINE_VERSION
                or metadata.metadata.get("symbol") != symbol
                or metadata.metadata.get("engine_version") != TRANSPARENT_ENGINE_VERSION
            ):
                continue
            try:
                payload = self.store.load(metadata.artifact_id)
            except (OSError, KeyError, TypeError, ValueError):
                continue
            manifest = TransparentRunManifest(
                run_id=str(payload["run_id"]),
                symbol=str(payload["symbol"]),
                trade_date=str(payload["trade_date"]),
                created_at=str(payload["created_at"]),
                engine_version=str(payload["engine_version"]),
                artifact_ids={str(key): str(value) for key, value in dict(payload["artifact_ids"]).items()},
                metadata=dict(payload.get("metadata", {})),
            )
            if (
                manifest.symbol != symbol
                or manifest.run_id != metadata.metadata.get("run_id")
                or manifest.engine_version != TRANSPARENT_ENGINE_VERSION
            ):
                continue
            if passing_only and not self._validation_approved(manifest):
                continue
            manifests.append(manifest)
        return manifests

    def resolve(self, *, symbol: str, run_id: str, passing_only: bool = True) -> TransparentEngineArtifacts:
        manifest = next(
            (item for item in self.list_manifests(symbol, passing_only=passing_only) if item.run_id == run_id),
            None,
        )
        if manifest is None:
            qualification = "validation-approved " if passing_only else ""
            raise ValueError(f"no {qualification}v2 run found for {symbol}/{run_id}")
        return self.loader.load(manifest)

    def _validation_approved(self, manifest: TransparentRunManifest) -> bool:
        if manifest.engine_version != TRANSPARENT_ENGINE_VERSION or manifest.metadata.get("validation_passed") is not True:
            return False
        artifact_id = manifest.artifact_ids.get(TRANSPARENT_VALIDATION_TYPE)
        if not artifact_id:
            return False
        try:
            metadata = self.store.load_metadata(artifact_id)
            payload = self.store.load(artifact_id)
        except (OSError, KeyError, TypeError, ValueError):
            return False
        if not (
            metadata.artifact_type == TRANSPARENT_VALIDATION_TYPE
            and metadata.version == TRANSPARENT_ENGINE_VERSION
            and metadata.metadata.get("symbol") == manifest.symbol
            and metadata.metadata.get("run_id") == manifest.run_id
            and payload.get("symbol") == manifest.symbol
            and payload.get("run_id") == manifest.run_id
            and payload.get("engine_version") == TRANSPARENT_ENGINE_VERSION
            and payload.get("passed") is True
        ):
            return False
        try:
            _validate_validation_report(payload)
        except (KeyError, TypeError, ValueError):
            return False
        expected_hashes = payload.get("artifact_hashes")
        if not isinstance(expected_hashes, dict):
            return False
        contract = EngineArtifactContract.for_version(TRANSPARENT_ENGINE_VERSION)
        try:
            actual_hashes = {
                kind: self.store.load_metadata(manifest.artifact_ids[kind]).payload_hash
                for kind in contract.required_artifact_types
            }
        except (OSError, KeyError, TypeError, ValueError):
            return False
        return expected_hashes == actual_hashes


def _state_calibration(payload: dict[str, Any]) -> StateCalibrationArtifact:
    return StateCalibrationArtifact(
        symbol=str(payload["symbol"]),
        spread_quantiles=tuple(float(value) for value in payload["spread_quantiles"]),
        volatility_quantiles=tuple(float(value) for value in payload["volatility_quantiles"]),
        flicker_baseline=float(payload["flicker_baseline"]),
        quote_pressure_scale=float(payload["quote_pressure_scale"]),
        regime_surfaces={
            str(key): StateRegimeSurface(
                spread_quantiles=tuple(float(value) for value in value["spread_quantiles"]),
                volatility_quantiles=tuple(float(value) for value in value["volatility_quantiles"]),
                flicker_baseline=float(value["flicker_baseline"]),
                quote_pressure_scale=float(value["quote_pressure_scale"]),
                sample_count=int(value.get("sample_count", 0)),
            )
            for key, value in dict(payload.get("regime_surfaces", {})).items()
        },
        metadata=dict(payload.get("metadata", {})),
    )


def _execution_calibration(payload: dict[str, Any]) -> ExecutionCalibrationArtifact:
    return ExecutionCalibrationArtifact(
        symbol=str(payload["symbol"]),
        fill_probability_intercept=float(payload["fill_probability_intercept"]),
        alignment_weight=float(payload["alignment_weight"]),
        spread_penalty=float(payload["spread_penalty"]),
        slippage_intercept_bps=float(payload["slippage_intercept_bps"]),
        spread_slippage_weight=float(payload["spread_slippage_weight"]),
        adverse_selection_weight=float(payload["adverse_selection_weight"]),
        regime_fill_multipliers={
            str(key): float(value) for key, value in dict(payload["regime_fill_multipliers"]).items()
        },
        regime_slippage_multipliers={
            str(key): float(value) for key, value in dict(payload["regime_slippage_multipliers"]).items()
        },
        metadata=dict(payload.get("metadata", {})),
    )


def _validate_validation_report(payload: dict[str, object]) -> None:
    required = {
        "passed",
        "baseline",
        "candidate",
        "promotion",
        "split_sample_counts",
        "failures",
        "thresholds",
        "opportunity_definition",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"transparent validation report is incomplete: {missing}")
    promotion = payload["promotion"]
    if not isinstance(promotion, dict) or not isinstance(promotion.get("checks"), list):
        raise ValueError("transparent validation promotion evidence is malformed")
    failures = payload["failures"]
    if not isinstance(failures, list):
        raise ValueError("transparent validation failures must be a list")
    baseline = payload["baseline"]
    candidate = payload["candidate"]
    split_counts = payload["split_sample_counts"]
    if not isinstance(baseline, dict) or not isinstance(candidate, dict) or not isinstance(split_counts, dict):
        raise ValueError("transparent validation metrics are malformed")
    if len(split_counts) < 2 or any(int(value) <= 0 for value in split_counts.values()):
        raise ValueError("transparent validation requires at least two nonempty splits")
    candidate_count = int(candidate.get("sample_count", -1))
    if candidate_count <= 0 or candidate_count != sum(int(value) for value in split_counts.values()):
        raise ValueError("transparent validation candidate samples do not align with split evidence")
    if int(baseline.get("sample_count", -1)) != candidate_count:
        raise ValueError("transparent validation baseline and candidate samples are not aligned")
    if not isinstance(payload["thresholds"], dict):
        raise ValueError("transparent validation thresholds are malformed")
    try:
        baseline_evaluation = EngineEvaluation(**baseline)
        candidate_evaluation = EngineEvaluation(**candidate)
        thresholds = PromotionThresholds(**payload["thresholds"])
    except TypeError as exc:
        raise ValueError("transparent validation metric contract is malformed") from exc
    recomputed_promotion = TransparentPromotionGate(thresholds).evaluate(
        baseline_evaluation,
        candidate_evaluation,
    ).to_dict()
    if promotion != recomputed_promotion:
        raise ValueError("transparent validation promotion evidence does not recompute")
    expected_passed = bool(recomputed_promotion["passed"]) and not failures
    if payload["passed"] is not expected_passed:
        raise ValueError("transparent validation pass status contradicts its evidence")
    if payload["opportunity_definition"] != "union_of_v1_v2_detected_transitions":
        raise ValueError("transparent validation does not use the common-opportunity contract")
