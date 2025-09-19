#!/usr/bin/env python3
"""
Regime Engine Interfaces
========================

Separate interface definitions to avoid circular imports.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class RegimeType(Enum):
    """Market regime types"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRANSITIONAL = "transitional"
    UNKNOWN = "unknown"

@dataclass
class RegimeMetrics:
    """Market regime analysis metrics"""
    volatility: float = 0.0
    trend_strength: float = 0.0
    momentum_score: float = 0.0
    stress_score: float = 0.0
    volatility_percentile: float = 0.0
    momentum: float = 0.0
    volume_profile: float = 0.0
    regime_stability: float = 0.0
    confidence: float = 0.0

@dataclass
class RegimeState:
    """Current market regime state"""
    primary_regime: RegimeType = RegimeType.SIDEWAYS
    secondary_regime: Optional[RegimeType] = None
    confidence: float = 0.0
    regime_start_time: Optional[datetime] = None
    last_transition: Optional[datetime] = None
    stability_score: float = 0.0
    market_volatility: float = 0.0
    trend_strength: float = 0.0
    metrics: Optional[RegimeMetrics] = None

@dataclass
class RegimeTransition:
    """Regime state transition information"""
    from_regime: RegimeType
    to_regime: RegimeType
    transition_time: datetime
    confidence: float = 0.0
    metrics: Optional[RegimeMetrics] = None

class IRegimeSubscriber(ABC):
    """Interface for regime state subscribers"""
    
    @abstractmethod
    async def on_regime_change(self, old_regime: RegimeState, new_regime: RegimeState, transition: RegimeTransition) -> None:
        """Handle regime state changes"""
        pass
    
    @abstractmethod
    def get_subscriber_id(self) -> str:
        """Get unique subscriber identifier"""
        pass