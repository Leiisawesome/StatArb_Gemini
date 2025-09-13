#!/usr/bin/env python3
"""
Historical Analytics Module
==========================

Production-ready historical market condition analytics framework
building on validated MarketCondition Analytics components.

This module provides:
- Multi-period historical regime detection
- Instrument performance ranking across market conditions  
- Backtest configuration optimization
- Historical data analysis and validation

Author: StatArb Gemini Team
Version: 1.0.0
"""

# Core data types and interfaces
from .data_types import (
    HistoricalPeriod, MarketDataset, RegimeDetectionResult,
    RegimeStats, RegimeAnalysisOutput, InstrumentScore,
    InstrumentRankings, AnalysisResults, BacktestConfig,
    BacktestSuite, AnalysisOutputPaths, RankingsOutputPaths,
    validate_historical_period, validate_market_dataset,
    validate_regime_analysis
)

# Data ingestion and management
from .data_ingestion import (
    HistoricalDataManager, DataValidationEngine
)

# Real data integration
from .real_data_loader import (
    RealHistoricalDataLoader, PredefinedHistoricalPeriods
)

# Regime analysis engine
from .regime_analyzer import (
    HistoricalRegimeAnalyzer
)

# Ranking and optimization engines
from .ranking_engine import (
    HistoricalRankingEngine, RankingAnalytics
)

# Configuration generation
from .config_generator import (
    BacktestConfigGenerator
)

# Main orchestration engine
from .engine import (
    HistoricalAnalyticsEngine, AnalyticsPipelineManager
)

# Data output and persistence
from .data_output import (
    HistoricalAnalyticsOutputManager
)

# Configuration management
from .config_manager import (
    HistoricalAnalyticsConfigManager
)

# Integration layer
from .integration import (
    BacktestingSystemIntegration,
    PaperTradingIntegration,
    SystemIntegrationManager
)

__all__ = [
    # Types
    'HistoricalPeriod', 'MarketDataset', 'RegimeDetectionResult',
    'RegimeStats', 'RegimeAnalysisOutput', 'InstrumentScore',
    'InstrumentRankings', 'AnalysisResults', 'BacktestConfig',
    'BacktestSuite', 'AnalysisOutputPaths', 'RankingsOutputPaths',
    
    # Validation functions
    'validate_historical_period', 'validate_market_dataset',
    'validate_regime_analysis',
    
    # Core engines
    'HistoricalDataManager', 'DataValidationEngine',
    'RealHistoricalDataLoader', 'PredefinedHistoricalPeriods',
    'HistoricalRegimeAnalyzer', 'HistoricalRankingEngine', 
    'RankingAnalytics', 'BacktestConfigGenerator',
    'HistoricalAnalyticsEngine', 'AnalyticsPipelineManager',
    
    # Data output and configuration
    'HistoricalAnalyticsOutputManager',
    'HistoricalAnalyticsConfigManager',
    
    # Integration layer
    'BacktestingSystemIntegration', 'PaperTradingIntegration',
    'SystemIntegrationManager'
]