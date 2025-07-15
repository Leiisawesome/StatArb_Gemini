"""
Risk Management Module for AI-Ready Statistical Arbitrage System
================================================================

This module provides comprehensive risk management capabilities with:
- Real-time risk monitoring and alerting
- Advanced risk metrics (VaR, CVaR, stress testing)
- AI-driven position sizing and risk optimization
- Multi-layer risk controls and limits
- Scenario analysis and stress testing

Key Components:
- RiskManager: Core risk management engine
- PositionSizer: Advanced position sizing algorithms
- RiskMetrics: Comprehensive risk calculation engine
- StressTester: Scenario analysis and stress testing
- RiskMonitor: Real-time risk monitoring and alerting

Author: Pro Quant Desk Trader
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)

# Risk management enums
class RiskLevel(Enum):
    """Risk tolerance levels"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class RiskMetricType(Enum):
    """Types of risk metrics"""
    VAR = "value_at_risk"
    CVAR = "conditional_var"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    DRAWDOWN = "max_drawdown"
    SHARPE = "sharpe_ratio"

class PositionSizeMethod(Enum):
    """Position sizing methods"""
    KELLY = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    EQUAL_WEIGHT = "equal_weight"
    ADAPTIVE = "adaptive"

# Core risk management components
try:
    from .risk_manager import (
        RiskManager,
        RiskConfig,
        RiskLimits,
        RiskAlert,
        RiskCheckResult
    )
    
    from .position_sizer import (
        PositionSizer,
        PositionSizeConfig,
        PositionSizeResult,
        SizingConstraints,
        KellyCriterion
    )
    
    from .risk_metrics import (
        RiskMetrics,
        VaRCalculator,
        StressTestEngine,
        CorrelationAnalyzer,
        DrawdownAnalyzer
    )
    
    from .risk_monitor import (
        RiskMonitor,
        RiskMonitorConfig,
        AlertSystem,
        RiskDashboard,
        RiskReport
    )
    
    RISK_MANAGEMENT_AVAILABLE = True
    logger.info("Risk management module loaded successfully")
    
except ImportError as e:
    logger.error(f"Failed to import risk management components: {e}")
    RISK_MANAGEMENT_AVAILABLE = False
    
    # Fallback imports for graceful degradation
    RiskManager = None
    PositionSizer = None
    RiskMetrics = None
    RiskMonitor = None

# Module configuration
DEFAULT_RISK_CONFIG = {
    'max_portfolio_var': 0.02,  # 2% daily VaR limit
    'max_position_size': 0.15,  # 15% max position size
    'max_correlation': 0.8,     # 80% max correlation
    'max_drawdown': 0.05,       # 5% max drawdown
    'var_confidence': 0.95,     # 95% VaR confidence
    'stress_test_scenarios': 10,
    'risk_check_frequency': 60, # seconds
    'alert_thresholds': {
        'warning': 0.8,   # 80% of limit
        'critical': 0.95  # 95% of limit
    }
}

def get_module_health() -> Dict[str, Any]:
    """Get risk management module health status"""
    return {
        'module_name': 'risk_management',
        'version': '1.0.0',
        'status': 'healthy' if RISK_MANAGEMENT_AVAILABLE else 'degraded',
        'components_available': RISK_MANAGEMENT_AVAILABLE,
        'last_check': datetime.now().isoformat(),
        'dependencies': ['numpy', 'pandas', 'scipy', 'scikit-learn'],
        'config': DEFAULT_RISK_CONFIG
    }

def create_risk_manager(config: Optional[Dict[str, Any]] = None) -> Optional['RiskManager']:
    """Factory function to create risk manager instance"""
    if not RISK_MANAGEMENT_AVAILABLE:
        logger.error("Risk management components not available")
        return None
    
    try:
        risk_config = {**DEFAULT_RISK_CONFIG, **(config or {})}
        return RiskManager(risk_config)
    except Exception as e:
        logger.error(f"Failed to create risk manager: {e}")
        return None

def create_position_sizer(method: PositionSizeMethod = PositionSizeMethod.KELLY,
                         config: Optional[Dict[str, Any]] = None) -> Optional['PositionSizer']:
    """Factory function to create position sizer instance"""
    if not RISK_MANAGEMENT_AVAILABLE:
        logger.error("Risk management components not available")
        return None
    
    try:
        sizer_config = {**DEFAULT_RISK_CONFIG, **(config or {})}
        return PositionSizer(method, sizer_config)
    except Exception as e:
        logger.error(f"Failed to create position sizer: {e}")
        return None

__all__ = [
    'RiskManager',
    'PositionSizer',
    'RiskMetrics',
    'RiskMonitor',
    'RiskConfig',
    'RiskLimits',
    'RiskAlert',
    'RiskCheckResult',
    'PositionSizeConfig',
    'PositionSizeResult',
    'SizingConstraints',
    'KellyCriterion',
    'VaRCalculator',
    'StressTestEngine',
    'CorrelationAnalyzer',
    'DrawdownAnalyzer',
    'RiskMonitorConfig',
    'AlertSystem',
    'RiskDashboard',
    'RiskReport',
    'RiskLevel',
    'RiskMetricType',
    'PositionSizeMethod',
    'get_module_health',
    'create_risk_manager',
    'create_position_sizer',
    'DEFAULT_RISK_CONFIG'
]

__version__ = "1.0.0" 