"""
Desk-Grade Experiment Suite
===========================

Clean orchestration layer for InstitutionalBacktestEngine.

Principles:
- Zero re-implementation of engine logic
- Consistent experiment interface
- Config-driven experimentation
- Structured results output

Author: StatArb_Gemini Core Engine
"""

from .base_experiment import BaseExperiment, ExperimentResult

__all__ = [
    'BaseExperiment',
    'ExperimentResult',
]

