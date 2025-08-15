"""
Market Regime Adaptation - Template-Aware Market Regime Detection and Adaptation
===============================================================================

Market regime detection and strategy adaptation with template inheritance awareness.
Provides regime-specific parameter adjustments and transition handling.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import deque

from strategy_templates.base import TemplateRegistry, TemplateCategory


class MarketRegime(Enum):
    """Market regime types"""
    BULLISH = "bullish"           # Strong upward trend
    BEARISH = "bearish"           # Strong downward trend
    SIDEWAYS = "sideways"         # Range-bound market
    HIGH_VOLATILITY = "high_vol"  # High volatility regime
    LOW_VOLATILITY = "low_vol"    # Low volatility regime
    CRISIS = "crisis"             # Crisis/panic mode
    RECOVERY = "recovery"         # Post-crisis recovery
    UNKNOWN = "unknown"           # Unidentified regime


class RegimeTransition(Enum):
    """Types of regime transitions"""
    GRADUAL = "gradual"           # Slow transition over time
    SHARP = "sharp"               # Rapid regime change
    REVERSAL = "reversal"         # Complete regime reversal
    CONSOLIDATION = "consolidation" # Moving to sideways from trend


@dataclass
class RegimeAdaptationRule:
    """Rule for adapting parameters based on regime"""
    source_regime: MarketRegime
    target_regime: MarketRegime
    parameter_adjustments: Dict[str, float]
    confidence_threshold: float = 0.7
    min_regime_duration: timedelta = timedelta(hours=2)
    adaptation_strength: float = 1.0


@dataclass
class MarketRegimeConfig:
    """Configuration for market regime detection and adaptation"""
    # Regime detection parameters
    trend_lookback_periods: int = 50
    volatility_lookback_periods: int = 20
    volume_confirmation_periods: int = 10
    
    # Regime identification thresholds
    trend_threshold: float = 0.02      # 2% for trend identification
    volatility_threshold: float = 0.25  # 25% volatility threshold
    crisis_threshold: float = -0.10     # 10% decline for crisis detection
    
    # Regime persistence requirements
    min_regime_confidence: float = 0.75
    min_regime_duration: timedelta = timedelta(minutes=30)
    regime_confirmation_periods: int = 3
    
    # Template category regime sensitivity
    regime_sensitivity: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 0.8,      # Less sensitive to regime changes
        TemplateCategory.SPECIFIC: 1.0,  # Standard sensitivity
        TemplateCategory.COMPOSITE: 1.2  # More sensitive to regime changes
    })


class MarketRegimeAdaptation:
    """
    Market regime detection and adaptation with template awareness
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[MarketRegimeConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or MarketRegimeConfig()
        
        # Market data storage
        self.price_history: deque = deque(maxlen=max(100, self.config.trend_lookback_periods * 2))
        self.volume_history: deque = deque(maxlen=max(50, self.config.volume_confirmation_periods * 2))
        self.volatility_history: deque = deque(maxlen=max(50, self.config.volatility_lookback_periods * 2))
        
        # Regime tracking
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.regime_start_time: Optional[datetime] = None
        self.regime_history: List[Tuple[datetime, MarketRegime, float]] = []
        
        # Template context
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        
        # Adaptation rules
        self.adaptation_rules = self._initialize_default_adaptation_rules()
        
        self.logger.info("Market Regime Adaptation initialized")
    
    def initialize_for_template(self, template_id: str):
        """Initialize regime adaptation for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            
            # Reset regime tracking
            self.current_regime = MarketRegime.UNKNOWN
            self.regime_confidence = 0.0
            self.regime_start_time = None
            
            self.logger.info(f"Regime adaptation initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize regime adaptation: {e}")
            raise
    
    def update_market_data(self, market_data: Dict[str, Any]) -> bool:
        """
        Update market data and detect regime changes
        Returns True if regime change detected
        """
        try:
            timestamp = datetime.now()
            
            # Extract market data
            price = market_data.get('price', 0)
            volume = market_data.get('volume', 0)
            
            if price > 0:
                self.price_history.append((timestamp, price))
            
            if volume > 0:
                self.volume_history.append((timestamp, volume))
            
            # Calculate volatility if we have enough price data
            if len(self.price_history) >= 2:
                recent_prices = [p[1] for p in list(self.price_history)[-self.config.volatility_lookback_periods:]]
                if len(recent_prices) >= self.config.volatility_lookback_periods:
                    returns = np.diff(np.log(recent_prices))
                    volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
                    self.volatility_history.append((timestamp, volatility))
            
            # Detect current regime
            new_regime, confidence = self._detect_market_regime()
            
            # Check for regime change
            regime_changed = self._update_current_regime(new_regime, confidence, timestamp)
            
            return regime_changed
            
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
            return False
    
    def get_regime_analysis(self) -> Dict[str, Any]:
        """Get comprehensive regime analysis"""
        return {
            'current_regime': self.current_regime.value,
            'regime_confidence': self.regime_confidence,
            'regime_duration': self._get_regime_duration(),
            'regime_stability': self._assess_regime_stability(),
            'transition_probability': self._calculate_transition_probabilities(),
            'regime_characteristics': self._analyze_regime_characteristics(),
            'adaptation_recommendations': self._get_adaptation_recommendations()
        }
    
    def get_regime_adaptation_parameters(self) -> Dict[str, float]:
        """Get parameter adjustments for current regime"""
        if not self.current_template_category:
            return {}
        
        # Get base adaptations for current regime
        base_adaptations = self._get_base_regime_adaptations(self.current_regime)
        
        # Apply template category sensitivity
        sensitivity = self.config.regime_sensitivity[self.current_template_category]
        
        # Scale adaptations by sensitivity and confidence
        scaled_adaptations = {}
        for param, adjustment in base_adaptations.items():
            scaled_adjustment = adjustment * sensitivity * self.regime_confidence
            scaled_adaptations[param] = scaled_adjustment
        
        return scaled_adaptations
    
    def predict_regime_transition(self, horizon_minutes: int = 60) -> Dict[str, float]:
        """Predict probability of regime transitions within time horizon"""
        if len(self.regime_history) < 5:
            return {regime.value: 1/len(MarketRegime) for regime in MarketRegime}
        
        try:
            # Analyze historical transition patterns
            transition_probs = self._calculate_transition_matrix()
            
            # Current regime persistence probability
            current_regime_duration = self._get_regime_duration()
            persistence_prob = self._calculate_persistence_probability(current_regime_duration)
            
            # Combine historical patterns with persistence
            predictions = {}
            for regime in MarketRegime:
                if regime == self.current_regime:
                    predictions[regime.value] = persistence_prob
                else:
                    transition_prob = transition_probs.get((self.current_regime, regime), 0.0)
                    predictions[regime.value] = transition_prob * (1 - persistence_prob)
            
            # Normalize probabilities
            total_prob = sum(predictions.values())
            if total_prob > 0:
                predictions = {k: v/total_prob for k, v in predictions.items()}
            
            return predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting regime transition: {e}")
            return {regime.value: 1/len(MarketRegime) for regime in MarketRegime}
    
    # Private helper methods
    def _detect_market_regime(self) -> Tuple[MarketRegime, float]:
        """Detect current market regime based on price and volume data"""
        if len(self.price_history) < self.config.trend_lookback_periods:
            return MarketRegime.UNKNOWN, 0.0
        
        try:
            # Get recent price data
            recent_prices = [p[1] for p in list(self.price_history)[-self.config.trend_lookback_periods:]]
            
            # Calculate trend indicators
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            short_ma = np.mean(recent_prices[-10:]) if len(recent_prices) >= 10 else recent_prices[-1]
            long_ma = np.mean(recent_prices[-30:]) if len(recent_prices) >= 30 else np.mean(recent_prices)
            
            # Calculate volatility
            current_volatility = 0.0
            if len(self.volatility_history) > 0:
                current_volatility = self.volatility_history[-1][1]
            
            # Volume analysis
            volume_trend = 0.0
            if len(self.volume_history) >= self.config.volume_confirmation_periods:
                recent_volumes = [v[1] for v in list(self.volume_history)[-self.config.volume_confirmation_periods:]]
                avg_volume = np.mean(recent_volumes[:-5]) if len(recent_volumes) > 5 else np.mean(recent_volumes)
                current_volume = np.mean(recent_volumes[-3:])
                volume_trend = (current_volume - avg_volume) / avg_volume if avg_volume > 0 else 0
            
            # Regime detection logic
            regime_scores = {}
            
            # Crisis detection (highest priority)
            if price_change <= self.config.crisis_threshold and current_volatility > 0.4:
                regime_scores[MarketRegime.CRISIS] = 0.9
            
            # Volatility regimes
            elif current_volatility > self.config.volatility_threshold:
                regime_scores[MarketRegime.HIGH_VOLATILITY] = 0.8
            elif current_volatility < self.config.volatility_threshold * 0.4:
                regime_scores[MarketRegime.LOW_VOLATILITY] = 0.7
            
            # Trend regimes
            elif price_change > self.config.trend_threshold and short_ma > long_ma * 1.01:
                # Bullish regime
                confidence = min(0.9, 0.5 + abs(price_change) * 2 + max(0, volume_trend) * 0.3)
                regime_scores[MarketRegime.BULLISH] = confidence
            
            elif price_change < -self.config.trend_threshold and short_ma < long_ma * 0.99:
                # Bearish regime
                confidence = min(0.9, 0.5 + abs(price_change) * 2 + max(0, volume_trend) * 0.3)
                regime_scores[MarketRegime.BEARISH] = confidence
            
            else:
                # Sideways regime
                sideways_confidence = 0.6 - abs(price_change) * 5  # Lower confidence for larger moves
                regime_scores[MarketRegime.SIDEWAYS] = max(0.3, sideways_confidence)
            
            # Recovery detection (after crisis)
            if (self.current_regime == MarketRegime.CRISIS and 
                price_change > 0.02 and current_volatility < 0.3):
                regime_scores[MarketRegime.RECOVERY] = 0.8
            
            # Return highest scoring regime
            if regime_scores:
                best_regime = max(regime_scores, key=regime_scores.get)
                best_confidence = regime_scores[best_regime]
                return best_regime, best_confidence
            else:
                return MarketRegime.UNKNOWN, 0.0
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.UNKNOWN, 0.0
    
    def _update_current_regime(self, new_regime: MarketRegime, confidence: float, timestamp: datetime) -> bool:
        """Update current regime and return True if regime changed"""
        # Check if this is a significant regime change
        if new_regime == self.current_regime:
            # Update confidence for current regime
            self.regime_confidence = max(self.regime_confidence, confidence)
            return False
        
        # Check if new regime meets confidence threshold
        if confidence < self.config.min_regime_confidence:
            return False
        
        # Check if current regime has been stable long enough
        if (self.regime_start_time and 
            timestamp - self.regime_start_time < self.config.min_regime_duration):
            return False
        
        # Record regime change
        if self.current_regime != MarketRegime.UNKNOWN:
            self.regime_history.append((timestamp, self.current_regime, self.regime_confidence))
        
        # Update to new regime
        old_regime = self.current_regime
        self.current_regime = new_regime
        self.regime_confidence = confidence
        self.regime_start_time = timestamp
        
        self.logger.info(f"Regime change detected: {old_regime.value} -> {new_regime.value} (confidence: {confidence:.3f})")
        
        return True
    
    def _get_regime_duration(self) -> timedelta:
        """Get duration of current regime"""
        if not self.regime_start_time:
            return timedelta(0)
        return datetime.now() - self.regime_start_time
    
    def _assess_regime_stability(self) -> str:
        """Assess stability of current regime"""
        duration = self._get_regime_duration()
        
        if duration < timedelta(minutes=30):
            return 'unstable'
        elif duration < timedelta(hours=2):
            return 'developing'
        elif duration < timedelta(hours=12):
            return 'stable'
        else:
            return 'entrenched'
    
    def _calculate_transition_probabilities(self) -> Dict[str, float]:
        """Calculate probabilities of transitioning to other regimes"""
        if len(self.regime_history) < 3:
            return {}
        
        # Count transitions
        transitions = {}
        for i in range(len(self.regime_history) - 1):
            from_regime = self.regime_history[i][1]
            to_regime = self.regime_history[i + 1][1]
            
            if from_regime not in transitions:
                transitions[from_regime] = {}
            if to_regime not in transitions[from_regime]:
                transitions[from_regime][to_regime] = 0
            
            transitions[from_regime][to_regime] += 1
        
        # Calculate probabilities for current regime
        if self.current_regime in transitions:
            total_transitions = sum(transitions[self.current_regime].values())
            probabilities = {}
            for target_regime, count in transitions[self.current_regime].items():
                probabilities[target_regime.value] = count / total_transitions
            return probabilities
        
        return {}
    
    def _analyze_regime_characteristics(self) -> Dict[str, Any]:
        """Analyze characteristics of current regime"""
        if len(self.price_history) < 20:
            return {}
        
        recent_prices = [p[1] for p in list(self.price_history)[-20:]]
        
        characteristics = {
            'volatility': np.std(np.diff(np.log(recent_prices))) * np.sqrt(252) if len(recent_prices) > 1 else 0,
            'trend_strength': abs((recent_prices[-1] - recent_prices[0]) / recent_prices[0]),
            'price_momentum': (recent_prices[-1] - recent_prices[-5]) / recent_prices[-5] if len(recent_prices) >= 5 else 0,
            'regime_persistence': self.regime_confidence,
            'duration_hours': self._get_regime_duration().total_seconds() / 3600
        }
        
        return characteristics
    
    def _get_adaptation_recommendations(self) -> List[str]:
        """Get adaptation recommendations for current regime"""
        recommendations = []
        
        regime_advice = {
            MarketRegime.BULLISH: [
                "Consider increasing position sizes for momentum strategies",
                "Reduce hedge ratios for trend-following positions",
                "Extend profit targets to capture larger moves"
            ],
            MarketRegime.BEARISH: [
                "Implement tighter stop-losses",
                "Consider increasing cash allocation",
                "Focus on short-term momentum strategies"
            ],
            MarketRegime.SIDEWAYS: [
                "Favor mean-reversion strategies",
                "Reduce trend-following allocations",
                "Use wider stop-losses to avoid whipsaws"
            ],
            MarketRegime.HIGH_VOLATILITY: [
                "Reduce overall position sizes",
                "Use volatility-adjusted position sizing",
                "Consider volatility-selling strategies"
            ],
            MarketRegime.LOW_VOLATILITY: [
                "May increase position sizes cautiously",
                "Consider volatility-buying strategies",
                "Focus on momentum strategies"
            ],
            MarketRegime.CRISIS: [
                "Implement emergency risk controls",
                "Reduce positions to minimum viable levels",
                "Focus on capital preservation"
            ],
            MarketRegime.RECOVERY: [
                "Gradually increase position sizes",
                "Focus on oversold bounce strategies",
                "Monitor for false recoveries"
            ]
        }
        
        return regime_advice.get(self.current_regime, ["Monitor market conditions closely"])
    
    def _get_base_regime_adaptations(self, regime: MarketRegime) -> Dict[str, float]:
        """Get base parameter adaptations for a regime"""
        adaptations = {
            MarketRegime.BULLISH: {
                'signal_threshold': -0.1,      # More aggressive signals
                'position_size_multiplier': 1.2, # Larger positions
                'stop_loss_multiplier': 1.1,   # Slightly wider stops
                'take_profit_multiplier': 1.3   # Extended targets
            },
            MarketRegime.BEARISH: {
                'signal_threshold': 0.1,       # More conservative signals
                'position_size_multiplier': 0.8, # Smaller positions
                'stop_loss_multiplier': 0.9,   # Tighter stops
                'take_profit_multiplier': 0.9   # Closer targets
            },
            MarketRegime.SIDEWAYS: {
                'signal_threshold': 0.05,      # Slightly more selective
                'position_size_multiplier': 1.0, # Standard positions
                'stop_loss_multiplier': 1.2,   # Wider stops for whipsaws
                'take_profit_multiplier': 0.8   # Quicker profits
            },
            MarketRegime.HIGH_VOLATILITY: {
                'signal_threshold': 0.15,      # Much more selective
                'position_size_multiplier': 0.6, # Much smaller positions
                'stop_loss_multiplier': 0.8,   # Tighter stops
                'take_profit_multiplier': 1.1   # Slightly extended targets
            },
            MarketRegime.LOW_VOLATILITY: {
                'signal_threshold': -0.05,     # Slightly more aggressive
                'position_size_multiplier': 1.1, # Slightly larger positions
                'stop_loss_multiplier': 1.1,   # Slightly wider stops
                'take_profit_multiplier': 1.0   # Standard targets
            },
            MarketRegime.CRISIS: {
                'signal_threshold': 0.3,       # Very conservative
                'position_size_multiplier': 0.3, # Minimal positions
                'stop_loss_multiplier': 0.7,   # Very tight stops
                'take_profit_multiplier': 0.7   # Quick profits
            },
            MarketRegime.RECOVERY: {
                'signal_threshold': 0.0,       # Standard selectivity
                'position_size_multiplier': 0.9, # Cautious position sizing
                'stop_loss_multiplier': 0.9,   # Careful stops
                'take_profit_multiplier': 1.2   # Extended targets for bounces
            }
        }
        
        return adaptations.get(regime, {})
    
    def _calculate_transition_matrix(self) -> Dict[Tuple[MarketRegime, MarketRegime], float]:
        """Calculate regime transition probability matrix"""
        transitions = {}
        
        if len(self.regime_history) < 2:
            return transitions
        
        # Count all transitions
        transition_counts = {}
        regime_counts = {}
        
        for i in range(len(self.regime_history) - 1):
            from_regime = self.regime_history[i][1]
            to_regime = self.regime_history[i + 1][1]
            
            # Count transitions
            if (from_regime, to_regime) not in transition_counts:
                transition_counts[(from_regime, to_regime)] = 0
            transition_counts[(from_regime, to_regime)] += 1
            
            # Count regime occurrences
            if from_regime not in regime_counts:
                regime_counts[from_regime] = 0
            regime_counts[from_regime] += 1
        
        # Calculate probabilities
        for (from_regime, to_regime), count in transition_counts.items():
            if regime_counts[from_regime] > 0:
                transitions[(from_regime, to_regime)] = count / regime_counts[from_regime]
        
        return transitions
    
    def _calculate_persistence_probability(self, current_duration: timedelta) -> float:
        """Calculate probability that current regime will persist"""
        # Simple exponential decay model
        # Longer regimes are more likely to continue, but with diminishing returns
        duration_hours = current_duration.total_seconds() / 3600
        
        # Base persistence probability
        base_persistence = 0.7
        
        # Decay factor (regime becomes less likely to persist over time)
        decay_rate = 0.02  # 2% per hour
        
        persistence = base_persistence * np.exp(-decay_rate * duration_hours)
        
        # Minimum persistence probability
        return max(0.1, persistence)
    
    def _initialize_default_adaptation_rules(self) -> List[RegimeAdaptationRule]:
        """Initialize default regime adaptation rules"""
        rules = []
        
        # Crisis to Recovery
        rules.append(RegimeAdaptationRule(
            source_regime=MarketRegime.CRISIS,
            target_regime=MarketRegime.RECOVERY,
            parameter_adjustments={
                'position_size_multiplier': 0.3,  # Gradual increase
                'signal_threshold': -0.1          # More opportunity-seeking
            },
            confidence_threshold=0.8,
            min_regime_duration=timedelta(hours=1)
        ))
        
        # High Vol to Low Vol
        rules.append(RegimeAdaptationRule(
            source_regime=MarketRegime.HIGH_VOLATILITY,
            target_regime=MarketRegime.LOW_VOLATILITY,
            parameter_adjustments={
                'position_size_multiplier': 0.8,  # Increase positions gradually
                'stop_loss_multiplier': 0.2       # Widen stops
            },
            confidence_threshold=0.7
        ))
        
        # Trend to Sideways
        rules.append(RegimeAdaptationRule(
            source_regime=MarketRegime.BULLISH,
            target_regime=MarketRegime.SIDEWAYS,
            parameter_adjustments={
                'signal_threshold': 0.1,          # More selective
                'take_profit_multiplier': -0.3    # Quicker profit taking
            },
            confidence_threshold=0.7
        ))
        
        return rules
