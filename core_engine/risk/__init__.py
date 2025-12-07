"""
Enhanced Risk Management Package - Institutional Grade Risk Management
Contains comprehensive risk management components with proper separation of concerns
"""

from .manager_enhanced import EnhancedRiskManager, RiskSnapshot, RiskAlert
from .exposure_calculator import (
    ExposureCalculator, ExposureType, ExposureDirection, ExposureItem,
    ExposureBreakdown, ExposureLimit, ExposureViolation
)
from .var_calculator import (
    VarCalculator, VarMethod, RiskMeasure, VarResult, RiskMetrics,
    StressTestScenario
)
from .stress_tester import (
    StressTester, StressTestType, ShockType, MarketShock, StressScenario,
    StressTestResult, PortfolioStressResult
)
from .limit_monitor import (
    LimitMonitor, LimitType, LimitScope, LimitOperator, AlertSeverity,
    RiskLimit, LimitBreach, MonitoringMetrics
)
from .correlation_analyzer import (
    CorrelationAnalyzer, CorrelationMethod, CorrelationRegime, CorrelationResult,
    CorrelationMatrix, RegimeDetectionResult, TailDependenceResult
)

__all__ = [
    # Main risk manager
    'EnhancedRiskManager',
    'RiskSnapshot',
    'RiskAlert',

    # Exposure management
    'ExposureCalculator',
    'ExposureType',
    'ExposureDirection',
    'ExposureItem',
    'ExposureBreakdown',
    'ExposureLimit',
    'ExposureViolation',

    # VaR and risk metrics
    'VarCalculator',
    'VarMethod',
    'RiskMeasure',
    'VarResult',
    'RiskMetrics',
    'StressTestScenario',

    # Stress testing
    'StressTester',
    'StressTestType',
    'ShockType',
    'MarketShock',
    'StressScenario',
    'StressTestResult',
    'PortfolioStressResult',

    # Limit monitoring
    'LimitMonitor',
    'LimitType',
    'LimitScope',
    'LimitOperator',
    'AlertSeverity',
    'RiskLimit',
    'LimitBreach',
    'MonitoringMetrics',

    # Correlation analysis
    'CorrelationAnalyzer',
    'CorrelationMethod',
    'CorrelationRegime',
    'CorrelationResult',
    'CorrelationMatrix',
    'RegimeDetectionResult',
    'TailDependenceResult'
]