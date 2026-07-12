"""Lightweight public facade for the L1 microstructure framework.

Exports are resolved lazily so importing the core package does not initialize
market-data, broker, API, or console integrations.
"""

from importlib import import_module
from typing import Any


_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "ArtifactBundleLoader": (".artifacts", "ArtifactBundleLoader"),
    "ArtifactBundleSelector": (".artifacts", "ArtifactBundleSelector"),
    "ArtifactDrivenResearchWorkflow": (".workflow", "ArtifactDrivenResearchWorkflow"),
    "DeterministicReplayEngine": (".replay", "DeterministicReplayEngine"),
    "EmpiricalRegimeCalibrator": (".calibration", "EmpiricalRegimeCalibrator"),
    "EmpiricalTransitionTrainer": (".training", "EmpiricalTransitionTrainer"),
    "EventKind": (".events", "EventKind"),
    "FeatureEngine": (".features", "FeatureEngine"),
    "ForwardDriftLabeler": (".labeling", "ForwardDriftLabeler"),
    "FrameworkConfig": (".config", "FrameworkConfig"),
    "InMemoryMonitoringSink": (".monitoring", "InMemoryMonitoringSink"),
    "JsonlMonitoringSink": (".monitoring", "JsonlMonitoringSink"),
    "L1MicrostructureStateMachine": (".pipeline", "L1MicrostructureStateMachine"),
    "LocalArtifactStore": (".artifacts", "LocalArtifactStore"),
    "MassivePayloadNormalizer": (".ingest", "MassivePayloadNormalizer"),
    "MicrostructureRegime": (".regime", "MicrostructureRegime"),
    "ObservedState": (".features", "ObservedState"),
    "PipelineTransitionDatasetBuilder": (".datasets", "PipelineTransitionDatasetBuilder"),
    "QuantileStateCalibrator": (".calibration", "QuantileStateCalibrator"),
    "QuoteEvent": (".events", "QuoteEvent"),
    "RTHSessionFilter": (".ingest", "RTHSessionFilter"),
    "RegimeInferencer": (".regime", "RegimeInferencer"),
    "RegimePosterior": (".regime", "RegimePosterior"),
    "RollingValidationHarness": (".validation", "RollingValidationHarness"),
    "RunManifest": (".artifacts", "RunManifest"),
    "RuntimeArtifactBundle": (".artifacts", "RuntimeArtifactBundle"),
    "RuntimeMonitor": (".monitoring", "RuntimeMonitor"),
    "SimulatorPaperTradingRunner": (".live", "SimulatorPaperTradingRunner"),
    "SourceBackedPaperRunner": (".live", "SourceBackedPaperRunner"),
    "TradeEvent": (".events", "TradeEvent"),
    "TradeSide": (".events", "TradeSide"),
    "WorkflowArtifactIds": (".workflow", "WorkflowArtifactIds"),
    "WorkflowRunResult": (".workflow", "WorkflowRunResult"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


__all__ = [
    "DeterministicReplayEngine",
    "EmpiricalRegimeCalibrator",
    "EmpiricalTransitionTrainer",
    "EventKind",
    "FeatureEngine",
    "ForwardDriftLabeler",
    "FrameworkConfig",
    "ArtifactBundleLoader",
    "ArtifactBundleSelector",
    "ArtifactDrivenResearchWorkflow",
    "InMemoryMonitoringSink",
    "JsonlMonitoringSink",
    "L1MicrostructureStateMachine",
    "LocalArtifactStore",
    "MicrostructureRegime",
    "ObservedState",
    "PipelineTransitionDatasetBuilder",
    "MassivePayloadNormalizer",
    "QuantileStateCalibrator",
    "QuoteEvent",
    "RegimeInferencer",
    "RegimePosterior",
    "RTHSessionFilter",
    "RollingValidationHarness",
    "RunManifest",
    "RuntimeArtifactBundle",
    "RuntimeMonitor",
    "SimulatorPaperTradingRunner",
    "SourceBackedPaperRunner",
    "TradeEvent",
    "TradeSide",
    "WorkflowArtifactIds",
    "WorkflowRunResult",
]
