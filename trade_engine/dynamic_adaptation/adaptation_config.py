"""
Configuration classes for dynamic parameter adaptation system.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class AdaptationMode(Enum):
    """Adaptation modes for parameter optimization."""
    CONSERVATIVE = "conservative"  # Small, gradual changes
    MODERATE = "moderate"         # Balanced adaptation
    AGGRESSIVE = "aggressive"     # Large, rapid changes
    DISABLED = "disabled"         # No adaptation


@dataclass
class AdaptationTriggers:
    """Configuration for when parameter adaptation should trigger."""
    
    # Performance-based triggers
    min_sharpe_ratio: float = 1.0
    max_drawdown_threshold: float = 0.15  # 15%
    min_win_rate: float = 0.45  # 45%
    min_profit_factor: float = 1.2
    
    # Market condition triggers
    volatility_change_threshold: float = 0.5  # 50% change
    correlation_break_threshold: float = 0.3
    volume_change_threshold: float = 0.3  # 30% change
    
    # Trade-based triggers
    min_trades_for_adaptation: int = 50
    consecutive_losses_trigger: int = 5
    consecutive_wins_trigger: int = 10
    
    # Time-based triggers
    adaptation_frequency_hours: int = 24
    min_hours_between_adaptations: int = 6


@dataclass 
class AdaptationBounds:
    """Bounds for parameter adaptation changes."""
    
    max_parameter_change_pct: float = 0.25  # 25% max change per adaptation
    min_parameter_change_pct: float = 0.05  # 5% min change to be meaningful
    adaptation_step_size: float = 0.10      # 10% step size for gradual changes


@dataclass
class AdaptationConfig:
    """Configuration for dynamic parameter adaptation."""
    
    # Core settings
    adaptation_mode: AdaptationMode = AdaptationMode.MODERATE
    enabled: bool = True
    
    # Trigger configuration
    triggers: AdaptationTriggers = None
    
    # Adaptation bounds
    bounds: AdaptationBounds = None
    
    # Performance monitoring
    performance_window_trades: int = 100
    rollback_monitoring_trades: int = 50
    
    # Safety settings
    max_adaptations_per_day: int = 4
    rollback_performance_threshold: float = -0.20  # 20% performance degradation triggers rollback
    
    # Advanced settings
    learning_rate: float = 0.1
    momentum_factor: float = 0.9
    regularization_strength: float = 0.01
    
    def __post_init__(self):
        """Initialize default values for nested dataclasses."""
        if self.triggers is None:
            self.triggers = AdaptationTriggers()
        if self.bounds is None:
            self.bounds = AdaptationBounds()
    
    def get_adaptation_step_size(self) -> float:
        """Get adaptation step size based on mode."""
        step_sizes = {
            AdaptationMode.CONSERVATIVE: 0.05,
            AdaptationMode.MODERATE: 0.10,
            AdaptationMode.AGGRESSIVE: 0.20,
            AdaptationMode.DISABLED: 0.0
        }
        return step_sizes.get(self.adaptation_mode, 0.10)
    
    def get_max_parameter_change(self) -> float:
        """Get maximum parameter change based on mode."""
        max_changes = {
            AdaptationMode.CONSERVATIVE: 0.15,
            AdaptationMode.MODERATE: 0.25,
            AdaptationMode.AGGRESSIVE: 0.40,
            AdaptationMode.DISABLED: 0.0
        }
        return max_changes.get(self.adaptation_mode, 0.25)
    
    def should_adapt(self) -> bool:
        """Check if adaptation is enabled."""
        return self.enabled and self.adaptation_mode != AdaptationMode.DISABLED
    
    def validate_config(self) -> bool:
        """Validate configuration parameters."""
        if not (0 <= self.learning_rate <= 1):
            return False
        if not (0 <= self.momentum_factor <= 1):
            return False
        if self.performance_window_trades < 10:
            return False
        if self.rollback_monitoring_trades < 10:
            return False
        return True
