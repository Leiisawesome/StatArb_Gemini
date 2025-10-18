"""
System Component Interfaces
==========================

Common interfaces for system components to avoid circular imports.

Includes:
- ISystemComponent: Base interface for all system components
- IRegimeAware: Interface for regime-aware components
- RegimeContext: Comprehensive regime context dataclass

Author: StatArb_Gemini Architecture Compliance
Version: 2.0.0 (Enhanced with Regime-First Support)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class ISystemComponent(ABC):
    """Interface for system components under orchestrator control"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize component"""
    
    @abstractmethod
    async def start(self) -> bool:
        """Start component operations"""
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop component operations"""
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""


@dataclass
class RegimeContext:
    """
    Comprehensive regime context for system-wide distribution
    
    This dataclass provides complete market regime information to all
    regime-aware components, enabling regime-adjusted operations across
    the entire system.
    """
    
    # === PRIMARY REGIME CLASSIFICATION ===
    primary_regime: str  # Current market regime
    regime_confidence: float  # Confidence in classification (0-1)
    regime_start_time: datetime  # When current regime began
    regime_duration_minutes: float  # How long in current regime
    
    # === MULTI-TIMEFRAME REGIME ANALYSIS ===
    timeframe_regimes: Dict[str, str] = field(default_factory=dict)  # {'5min': 'bull_low_vol', '1H': 'trending'}
    timeframe_confidences: Dict[str, float] = field(default_factory=dict)  # Confidence per timeframe
    regime_alignment_score: float = 0.0  # Cross-timeframe regime consistency (0-1)
    
    # === MARKET CONDITIONS ===
    volatility_regime: str = "normal_volatility"  # 'low_vol', 'normal_vol', 'high_vol', 'extreme_vol'
    liquidity_regime: str = "normal_liquidity"  # 'high_liquidity', 'normal', 'low_liquidity', 'crisis'
    trend_regime: str = "sideways"  # 'strong_up', 'weak_up', 'sideways', 'weak_down', 'strong_down'
    
    # === PREDICTIVE INDICATORS ===
    regime_transition_probability: float = 0.0  # Probability of regime change (0-1)
    expected_next_regime: Optional[str] = None  # Most likely next regime
    transition_timeframe: Optional[str] = None  # Expected time to transition
    
    # === STRATEGY IMPLICATIONS ===
    optimal_strategies: Dict[str, float] = field(default_factory=dict)  # {'momentum': 0.8, 'mean_reversion': 0.3}
    strategy_adjustments: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Strategy-specific parameters
    
    # === RISK IMPLICATIONS ===
    risk_multiplier: float = 1.0  # Risk scaling factor for current regime
    max_position_size_adjustment: float = 1.0  # Position size adjustment (0.5 = 50% of normal)
    leverage_adjustment: float = 1.0  # Leverage adjustment factor
    
    # === EXECUTION IMPLICATIONS ===
    execution_urgency: str = "normal"  # 'low', 'normal', 'high', 'urgent'
    recommended_execution_style: str = "ADAPTIVE"  # 'TWAP', 'VWAP', 'ADAPTIVE', etc.
    market_impact_multiplier: float = 1.0  # Expected impact vs normal conditions
    
    # === METADATA ===
    last_update: datetime = field(default_factory=datetime.now)
    analysis_version: str = "1.0.0"
    
    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if regime classification is high confidence"""
        return self.regime_confidence >= threshold
    
    def is_stable_regime(self, max_transition_prob: float = 0.3) -> bool:
        """Check if regime is stable (low transition probability)"""
        return self.regime_transition_probability <= max_transition_prob
    
    def get_strategy_weight(self, strategy_type: str) -> float:
        """Get optimal weight for strategy type in current regime"""
        return self.optimal_strategies.get(strategy_type, 0.5)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert regime context to dictionary"""
        return {
            'primary_regime': self.primary_regime,
            'regime_confidence': self.regime_confidence,
            'regime_start_time': self.regime_start_time.isoformat(),
            'regime_duration_minutes': self.regime_duration_minutes,
            'timeframe_regimes': self.timeframe_regimes,
            'timeframe_confidences': self.timeframe_confidences,
            'regime_alignment_score': self.regime_alignment_score,
            'volatility_regime': self.volatility_regime,
            'liquidity_regime': self.liquidity_regime,
            'trend_regime': self.trend_regime,
            'regime_transition_probability': self.regime_transition_probability,
            'expected_next_regime': self.expected_next_regime,
            'transition_timeframe': self.transition_timeframe,
            'optimal_strategies': self.optimal_strategies,
            'strategy_adjustments': self.strategy_adjustments,
            'risk_multiplier': self.risk_multiplier,
            'max_position_size_adjustment': self.max_position_size_adjustment,
            'leverage_adjustment': self.leverage_adjustment,
            'execution_urgency': self.execution_urgency,
            'recommended_execution_style': self.recommended_execution_style,
            'market_impact_multiplier': self.market_impact_multiplier,
            'last_update': self.last_update.isoformat(),
            'analysis_version': self.analysis_version
        }


class IRegimeAware(ABC):
    """
    Interface for components that require regime awareness
    
    Components implementing this interface receive regime context updates
    and can adapt their behavior based on current market conditions.
    
    MANDATORY for all components that need regime-adjusted operations:
    - Data processing components
    - Signal generation components
    - Strategy managers
    - Risk managers
    - Execution engines
    - Analytics components
    """
    
    @abstractmethod
    def set_regime_engine(self, regime_engine: Any) -> None:
        """
        Inject regime engine dependency
        
        Args:
            regime_engine: EnhancedRegimeEngine instance
        """
        pass
    
    @abstractmethod
    async def on_regime_change(self, new_regime_context: RegimeContext) -> None:
        """
        Handle regime change event
        
        Called when market regime changes to allow component to adapt.
        
        Args:
            new_regime_context: New regime context with updated information
        """
        pass
    
    @abstractmethod
    def get_current_regime_context(self) -> Optional[RegimeContext]:
        """
        Get current regime context
        
        Returns:
            Current RegimeContext or None if not available
        """
        pass
    
    @abstractmethod
    async def adapt_to_regime(self, regime_context: RegimeContext) -> Dict[str, Any]:
        """
        Adapt component behavior to current regime
        
        Args:
            regime_context: Current regime context
            
        Returns:
            Dictionary with adaptation details and adjustments made
        """
        pass
    
    @abstractmethod
    def validate_regime_dependency(self) -> bool:
        """
        Validate regime engine is properly configured
        
        Returns:
            True if regime engine is properly configured, False otherwise
        """
        pass
