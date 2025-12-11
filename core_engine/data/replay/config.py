#!/usr/bin/env python3
"""
Centralized Configuration for Historical Data Replay
====================================================

Single source of truth for replay configuration across all components.
Provides default settings and validation.

Author: StatArb_Gemini Core Engine
Version: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import time, datetime
from typing import List
from enum import Enum


class ReplaySpeed(Enum):
    """Replay speed multipliers"""
    PAUSED = 0.0
    REALTIME = 1.0
    FAST_2X = 2.0
    FAST_5X = 5.0
    FAST_10X = 10.0
    FAST_50X = 50.0
    FAST_100X = 100.0
    INSTANT = float('inf')  # Replay all data instantly


@dataclass
class ReplayConfig:
    """
    Centralized configuration for historical data replay
    
    This is the single source of truth for replay settings. Both the
    replay engine and adapter reference this configuration.
    """
    # Data source
    symbols: List[str] = field(default_factory=lambda: ["TSLA"])
    start_date: str = "2024-12-20"
    end_date: str = "2024-12-20"
    interval: str = "1min"  # 1min, 5min, 15min, 30min, 1h, 4h, 1D

    # Replay timing
    speed: ReplaySpeed = ReplaySpeed.REALTIME
    start_time: time = time(9, 30)  # 9:30 AM ET
    end_time: time = time(16, 0)    # 4:00 PM ET

    # Market hours simulation
    simulate_market_hours: bool = True
    skip_weekends: bool = True
    skip_holidays: bool = True  # TODO: Implement holiday calendar

    # Data processing
    batch_size: int = 1000  # Records to load at once
    buffer_size: int = 10000  # Internal buffer size

    # Performance
    max_concurrent_symbols: int = 10
    prefetch_multiplier: int = 2  # Load ahead by this factor

    # Feed adapter settings
    adapter_name: str = "historical-replay"

    def __post_init__(self):
        """Validate configuration"""
        if not self.symbols:
            raise ValueError("At least one symbol must be specified")

        # Validate date format
        try:
            datetime.strptime(self.start_date, "%Y-%m-%d")
            datetime.strptime(self.end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

        # Validate time format
        if not isinstance(self.start_time, time) or not isinstance(self.end_time, time):
            raise ValueError("start_time and end_time must be time objects")

        # Validate interval
        valid_intervals = ['1min', '5min', '15min', '30min', '1h', '4h', '1D']
        if self.interval not in valid_intervals:
            raise ValueError(f"Invalid interval. Must be one of: {valid_intervals}")

    @classmethod
    def create_default(cls) -> "ReplayConfig":
        """
        Create a default configuration
        
        Returns:
            ReplayConfig: Configuration with default settings
        """
        return cls()

    @classmethod
    def create_for_symbol(
        cls,
        symbol: str,
        start_date: str,
        end_date: str,
        speed: ReplaySpeed = ReplaySpeed.REALTIME
    ) -> "ReplayConfig":
        """
        Create configuration for a single symbol
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            speed: Replay speed multiplier
            
        Returns:
            ReplayConfig: Configuration for the specified symbol
        """
        return cls(
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            speed=speed
        )

    @classmethod
    def create_for_symbols(
        cls,
        symbols: List[str],
        start_date: str,
        end_date: str,
        speed: ReplaySpeed = ReplaySpeed.REALTIME,
        interval: str = "1min"
    ) -> "ReplayConfig":
        """
        Create configuration for multiple symbols
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            speed: Replay speed multiplier
            interval: Data interval
            
        Returns:
            ReplayConfig: Configuration for the specified symbols
        """
        return cls(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            speed=speed,
            interval=interval
        )

    def copy(self, **changes) -> "ReplayConfig":
        """
        Create a copy of the configuration with changes
        
        Args:
            **changes: Fields to override
            
        Returns:
            ReplayConfig: New configuration with changes applied
        """
        from dataclasses import replace
        return replace(self, **changes)


# Default configuration instance
DEFAULT_REPLAY_CONFIG = ReplayConfig.create_default()
