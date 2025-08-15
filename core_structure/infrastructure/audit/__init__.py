"""
Performance Audit and Architecture Analysis System
=================================================

This module provides comprehensive audit capabilities for the unified core engine
including performance benchmarking, bottleneck identification, and architecture
analysis for the hybrid template system.

Author: Pro Quant Desk Trader
"""

from .architecture_audit import (
    ArchitectureAudit,
    ArchitectureAuditResult,
    TemplateSystemAnalysis,
    AdaptationSystemAnalysis,
    Bottleneck
)

from .performance_benchmarking import (
    PerformanceBenchmarking,
    BenchmarkResults,
    TemplateBenchmarkResults,
    AdaptationBenchmarkResults
)

__all__ = [
    'ArchitectureAudit',
    'ArchitectureAuditResult', 
    'TemplateSystemAnalysis',
    'AdaptationSystemAnalysis',
    'Bottleneck',
    'PerformanceBenchmarking',
    'BenchmarkResults',
    'TemplateBenchmarkResults',
    'AdaptationBenchmarkResults'
]
