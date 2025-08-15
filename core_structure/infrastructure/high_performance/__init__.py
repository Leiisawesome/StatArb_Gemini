"""
High-Performance Components Framework
===================================

This module provides high-performance implementations of core engine components
designed to achieve enterprise-grade performance standards:

- Sub-millisecond market data processing
- High-throughput signal generation  
- Concurrent risk management
- Parallel execution processing
- Optimized portfolio management

Author: Pro Quant Desk Trader
"""

from .high_performance_data_manager import (
    HighPerformanceDataManager,
    DataManagerConfig,
    DataProcessingResult
)

from .high_performance_signal_generator import (
    HighPerformanceSignalGenerator,
    SignalGeneratorConfig,
    SignalGenerationResult
)

from .high_performance_risk_manager import (
    HighPerformanceRiskManager,
    RiskManagerConfig,
    RiskValidationResult
)

from .high_performance_execution_engine import (
    HighPerformanceExecutionEngine,
    ExecutionEngineConfig,
    ExecutionResult
)

from .component_integrator import (
    ComponentIntegrator,
    IntegrationConfig,
    IntegrationResult
)

__all__ = [
    'HighPerformanceDataManager',
    'DataManagerConfig',
    'DataProcessingResult',
    'HighPerformanceSignalGenerator',
    'SignalGeneratorConfig',
    'SignalGenerationResult',
    'HighPerformanceRiskManager',
    'RiskManagerConfig',
    'RiskValidationResult',
    'HighPerformanceExecutionEngine',
    'ExecutionEngineConfig',
    'ExecutionResult',
    'ComponentIntegrator',
    'IntegrationConfig',
    'IntegrationResult'
]
