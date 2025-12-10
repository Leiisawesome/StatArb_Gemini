"""
Historical Data Replay Module
=============================

This module provides functionality to replay historical market data as
real-time streams for testing live trading components without market risk.

Components:
    - HistoricalDataReplayEngine: Core replay engine
    - HistoricalReplayFeedAdapter: Feed adapter integration
    - Example usage and testing utilities

Usage:
    from core_engine.data.replay import HistoricalDataReplayEngine, ReplaySpeed

    # Create replay engine
    engine = HistoricalDataReplayEngine(config)
    await engine.initialize()
    await engine.start_replay()

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

from .engine import (
    HistoricalDataReplayEngine,
    ReplayConfig,
    ReplaySpeed,
    ReplayStatus,
    ReplayStatistics,
    create_replay_engine
)

from .adapter import (
    HistoricalReplayFeedAdapter,
    ReplayFeedConfig,
    create_replay_adapter
)

__all__ = [
    # Engine components
    'HistoricalDataReplayEngine',
    'ReplayConfig',
    'ReplaySpeed',
    'ReplayStatus',
    'ReplayStatistics',
    'create_replay_engine',

    # Adapter components
    'HistoricalReplayFeedAdapter',
    'ReplayFeedConfig',
    'create_replay_adapter',
]