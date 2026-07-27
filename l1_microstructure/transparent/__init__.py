"""Interpretable version-two statistical engine components."""

from .contracts import (
    BASELINE_ENGINE_VERSION,
    TRANSPARENT_ENGINE_VERSION,
    EngineArtifactContract,
    EngineEvaluation,
    EnginePredictionRecord,
    PromotionCheck,
    PromotionReport,
    PromotionThresholds,
    TransparentPromotionGate,
    evaluate_prediction_records,
)
from .vector import (
    STATE_VECTOR_FEATURES,
    RobustStateVectorRuntime,
    RobustStateVectorTrainer,
    StateVectorModel,
    TransitionEvidence,
)
from .edges import (
    HierarchicalDriftPosterior,
    HierarchicalTransitionModel,
    HierarchicalTransitionRuntime,
    HierarchicalTransitionTrainer,
    SufficientStatistics,
)
from .outcomes import (
    MultiHorizonOutcomeTracker,
    PendingHorizonOutcome,
    ResolvedHorizonOutcome,
)
from .regime import (
    REGIME_ORDER,
    SemiMarkovRegimeModel,
    SemiMarkovRegimePosterior,
    SemiMarkovRegimeRuntime,
    SemiMarkovRegimeTrainer,
)
from .utility import (
    ExpectedUtilityDecisionEngine,
    UtilityAlternative,
    UtilityCalibrationSample,
    UtilityDecision,
    UtilityModel,
    UtilityModelTrainer,
)
from .engine import TransparentEngineArtifacts, TransparentFrameworkUpdate, TransparentStatisticalEngine
from .shadow import ComparativeShadowRunner, ShadowComparison, ShadowReport
from .training import TransparentModelTrainer, candidate_transition_samples
from .artifacts import (
    TRANSPARENT_MANIFEST_TYPE,
    TRANSPARENT_VALIDATION_TYPE,
    TransparentArtifactBundleLoader,
    TransparentArtifactPublisher,
    TransparentArtifactSelector,
    TransparentRunManifest,
)
from .validation import (
    TransparentOOSValidationReport,
    TransparentOOSValidator,
    ValidationSplitEvidence,
    build_common_opportunity_samples,
)
from .workflow import TransparentArtifactDrivenWorkflow, TransparentWorkflowResult

__all__ = [
    "BASELINE_ENGINE_VERSION",
    "TRANSPARENT_ENGINE_VERSION",
    "EngineArtifactContract",
    "EngineEvaluation",
    "EnginePredictionRecord",
    "PromotionCheck",
    "PromotionReport",
    "PromotionThresholds",
    "TransparentPromotionGate",
    "evaluate_prediction_records",
    "STATE_VECTOR_FEATURES",
    "RobustStateVectorRuntime",
    "RobustStateVectorTrainer",
    "StateVectorModel",
    "TransitionEvidence",
    "HierarchicalDriftPosterior",
    "HierarchicalTransitionModel",
    "HierarchicalTransitionRuntime",
    "HierarchicalTransitionTrainer",
    "SufficientStatistics",
    "MultiHorizonOutcomeTracker",
    "PendingHorizonOutcome",
    "ResolvedHorizonOutcome",
    "REGIME_ORDER",
    "SemiMarkovRegimeModel",
    "SemiMarkovRegimePosterior",
    "SemiMarkovRegimeRuntime",
    "SemiMarkovRegimeTrainer",
    "ExpectedUtilityDecisionEngine",
    "UtilityAlternative",
    "UtilityCalibrationSample",
    "UtilityDecision",
    "UtilityModel",
    "UtilityModelTrainer",
    "TransparentEngineArtifacts",
    "TransparentFrameworkUpdate",
    "TransparentStatisticalEngine",
    "ComparativeShadowRunner",
    "ShadowComparison",
    "ShadowReport",
    "TransparentModelTrainer",
    "candidate_transition_samples",
    "TRANSPARENT_MANIFEST_TYPE",
    "TRANSPARENT_VALIDATION_TYPE",
    "TransparentArtifactBundleLoader",
    "TransparentArtifactPublisher",
    "TransparentArtifactSelector",
    "TransparentRunManifest",
    "TransparentOOSValidationReport",
    "TransparentOOSValidator",
    "ValidationSplitEvidence",
    "build_common_opportunity_samples",
    "TransparentArtifactDrivenWorkflow",
    "TransparentWorkflowResult",
]
