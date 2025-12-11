"""
Historical Data Replay Module
=============================

This module provides functionality to replay historical market data as
real-time streams for testing live trading components without market risk.

Components:
    - HistoricalDataReplayEngine: Core replay engine with configurable speed
    - HistoricalReplayFeedAdapter: Feed adapter integration
    - ReplayConfig: Configuration dataclass for replay settings
    - ReplaySpeed: Enum for speed multipliers (1x, 10x, 100x, INSTANT)
    - ReplayStatus: Enum for engine status tracking
    - Example usage and testing utilities

Usage:
    from core_engine.data.replay import HistoricalDataReplayEngine, ReplaySpeed

    # Create replay engine
    config = ReplayConfig(symbols=['TSLA'], start_date='2024-12-20', end_date='2024-12-20')
    engine = HistoricalDataReplayEngine(config)
    await engine.initialize()
    await engine.start_replay()

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

# Centralized configuration
from .config import (
    ReplayConfig,
    ReplaySpeed,
    DEFAULT_REPLAY_CONFIG
)

# Engine components
from .engine import (
    HistoricalDataReplayEngine,
    ReplayStatus,
    ReplayStatistics,
    create_replay_engine
)

# Adapter components
from .adapter import (
    HistoricalReplayFeedAdapter,
    create_replay_adapter
)

__all__ = [
    # Configuration
    'ReplayConfig',
    'ReplaySpeed',
    'DEFAULT_REPLAY_CONFIG',
    
    # Engine components
    'HistoricalDataReplayEngine',
    'ReplayStatus',
    'ReplayStatistics',
    'create_replay_engine',

    # Adapter components
    'HistoricalReplayFeedAdapter',
    'create_replay_adapter',
]