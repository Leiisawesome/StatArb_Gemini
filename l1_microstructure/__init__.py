"""L1 microstructure state machine framework.

This package is intentionally isolated from the legacy ``core_engine`` so the
successor architecture can be evaluated without inheriting old coupling.
"""

from .artifacts import ArtifactBundleLoader, ArtifactBundleSelector, LocalArtifactStore, RunManifest, RuntimeArtifactBundle
from .calibration import EmpiricalRegimeCalibrator, QuantileStateCalibrator
from .config import FrameworkConfig
from .datasets import PipelineTransitionDatasetBuilder
from .events import EventKind, QuoteEvent, TradeEvent, TradeSide
from .features import FeatureEngine, ObservedState
from .ingest import MassivePayloadNormalizer, RTHSessionFilter
from .labeling import ForwardDriftLabeler
from .live import SimulatorPaperTradingRunner, SourceBackedPaperRunner
from .monitoring import InMemoryMonitoringSink, JsonlMonitoringSink, RuntimeMonitor
from .pipeline import L1MicrostructureStateMachine
from .replay import DeterministicReplayEngine
from .regime import MicrostructureRegime, RegimeInferencer, RegimePosterior
from .training import EmpiricalTransitionTrainer
from .validation import RollingValidationHarness
from .workflow import ArtifactDrivenResearchWorkflow, WorkflowArtifactIds, WorkflowRunResult

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