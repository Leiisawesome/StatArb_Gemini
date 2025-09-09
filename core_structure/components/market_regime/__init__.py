#!/usr/bin/env python3
"""
Market Regime Detection Components
=================================

Professional market regime detection system for institutional trading.

Current Architecture:
- professional_regime_system.py: Main Phase 1 regime detection system
- enhanced_regime_detector.py: Enhanced regime detection capabilities  
- cross_asset_regime_system.py: Cross-asset regime confirmation
- macro_regime_analyzer.py: Macro-economic regime analysis
"""

from .professional_regime_system import (
    ProfessionalRegimeSystem,
    get_professional_regime_system,
    ProfessionalRegimeAnalysis
)

from .enhanced_regime_detector import (
    EnhancedRegimeDetector,
    EnhancedRegimeState,
    RegimeConfig
)

__all__ = [
    'ProfessionalRegimeSystem',
    'get_professional_regime_system', 
    'ProfessionalRegimeAnalysis',
    'EnhancedRegimeDetector',
    'EnhancedRegimeState',
    'RegimeConfig'
]
