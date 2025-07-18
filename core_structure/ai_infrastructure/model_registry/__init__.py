"""
AI Model Registry Package

This package provides comprehensive model lifecycle management for the
StatArb trading system including registration, versioning, deployment,
and monitoring capabilities.
"""

from .model_registry import (
    ModelRegistry,
    ModelStatus,
    ModelType,
    ModelMetadata
)

__all__ = [
    "ModelRegistry",
    "ModelStatus", 
    "ModelType",
    "ModelMetadata"
]
