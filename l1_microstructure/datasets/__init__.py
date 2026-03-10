"""Dataset-building contracts and implementations for transition and state panels."""

from .interfaces import DatasetSlice, TransitionDatasetBuilder
from .builders import PipelineTransitionDatasetBuilder

__all__ = ["DatasetSlice", "PipelineTransitionDatasetBuilder", "TransitionDatasetBuilder"]