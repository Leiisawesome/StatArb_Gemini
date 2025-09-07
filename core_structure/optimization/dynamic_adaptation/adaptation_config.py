"""
Adaptation Configuration Classes
===============================

Configuration classes for dynamic parameter adaptation system.

Author: Professional Trading System Architecture
Version: 2.0.0 (Core Structure Integrated)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import timedelta


class AdaptationMode(Enum):
    """Adaptation mode settings"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DISABLED = "disabled"


@dataclass
class AdaptationTriggers:
    """Triggers for parameter adaptation"""
    performance_threshold: float = -0.02  # -2% performance decline
    volatility_threshold: float = 0.15    # 15% volatility increase
    drawdown_threshold: float = 0.05      # 5% drawdown
    time_window: timedelta = field(default_factory=lambda: timedelta(hours=1))
    min_samples: int = 10


@dataclass
class AdaptationBounds:
    """Parameter bounds for adaptation"""
    parameter_bounds: Dict[str, tuple] = field(default_factory=dict)
    max_change_per_step: float = 0.1      # 10% max change per adaptation
    adaptation_cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=15))


@dataclass
class AdaptationConfig:
    """Main configuration for dynamic parameter adaptation"""
    mode: AdaptationMode = AdaptationMode.MODERATE
    triggers: AdaptationTriggers = field(default_factory=AdaptationTriggers)
    bounds: AdaptationBounds = field(default_factory=AdaptationBounds)
    
    # Adaptation behavior
    max_adaptations_per_day: int = 10
    confidence_threshold: float = 0.7
    rollback_threshold: float = -0.05     # -5% performance for rollback
    
    # Optimization settings
    optimization_method: str = "bayesian"
    max_optimization_iterations: int = 50
    convergence_tolerance: float = 1e-6
    
    # Risk management
    enable_risk_checks: bool = True
    max_position_size_change: float = 0.2  # 20% max position size change
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        
        if self.max_adaptations_per_day <= 0:
            raise ValueError("Max adaptations per day must be positive")
        
        if self.rollback_threshold > 0:
            raise ValueError("Rollback threshold should be negative (performance decline)")


# Default configurations for different modes
DEFAULT_CONFIGS = {
    AdaptationMode.CONSERVATIVE: AdaptationConfig(
        mode=AdaptationMode.CONSERVATIVE,
        triggers=AdaptationTriggers(
            performance_threshold=-0.01,  # More sensitive
            volatility_threshold=0.10,
            drawdown_threshold=0.03,
            min_samples=20
        ),
        bounds=AdaptationBounds(
            max_change_per_step=0.05,     # Smaller changes
            adaptation_cooldown=timedelta(minutes=30)
        ),
        max_adaptations_per_day=5,
        confidence_threshold=0.8
    ),
    
    AdaptationMode.MODERATE: AdaptationConfig(
        mode=AdaptationMode.MODERATE,
        # Uses default values
    ),
    
    AdaptationMode.AGGRESSIVE: AdaptationConfig(
        mode=AdaptationMode.AGGRESSIVE,
        triggers=AdaptationTriggers(
            performance_threshold=-0.03,  # Less sensitive
            volatility_threshold=0.20,
            drawdown_threshold=0.08,
            min_samples=5
        ),
        bounds=AdaptationBounds(
            max_change_per_step=0.15,     # Larger changes
            adaptation_cooldown=timedelta(minutes=5)
        ),
        max_adaptations_per_day=20,
        confidence_threshold=0.6
    )
}


def get_default_config(mode: AdaptationMode = AdaptationMode.MODERATE) -> AdaptationConfig:
    """Get default configuration for specified mode"""
    return DEFAULT_CONFIGS.get(mode, DEFAULT_CONFIGS[AdaptationMode.MODERATE])
