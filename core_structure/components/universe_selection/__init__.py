#!/usr/bin/env python3
"""
Intelligent Universe Selection System
====================================

Advanced instrument universe selection system that leverages 2.5 years of
historical data to optimize instrument selection for each strategy and regime.

Components:
- HistoricalInstrumentAnalyzer: Comprehensive historical analysis
- UniverseSelector: Real-time optimal universe selection
- FitnessCalculator: Multi-factor scoring system
- SelectionValidator: Performance validation and backtesting

Author: StatArb Gemini Team
Version: 1.0.0
"""

from .historical_analyzer import HistoricalInstrumentAnalyzer
from .universe_selector import IntelligentUniverseSelector
from .fitness_calculator import InstrumentFitnessCalculator
from .selection_validator import UniverseSelectionValidator

__all__ = [
    'HistoricalInstrumentAnalyzer',
    'IntelligentUniverseSelector', 
    'InstrumentFitnessCalculator',
    'UniverseSelectionValidator'
]
