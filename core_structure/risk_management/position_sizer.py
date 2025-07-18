"""
Advanced Position Sizing System for AI-Ready Statistical Arbitrage
================================================================

This module provides sophisticated position sizing algorithms with:
- Kelly Criterion for optimal growth
- Risk Parity for balanced risk allocation
- Volatility Targeting for consistent exposure
- Adaptive sizing based on market conditions
- AI-driven optimization and learning

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy.optimize import minimize, minimize_scalar
from scipy import stats
import json

logger = logging.getLogger(__name__)

class PositionSizeMethod(Enum):
    """Position sizing methods"""
    KELLY = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    VOLATILITY_TARGET = "volatility_target"
    EQUAL_WEIGHT = "equal_weight"
    ADAPTIVE = "adaptive"
    MAX_DRAWDOWN = "max_drawdown"

@dataclass
class PositionSizeConfig:
    """Configuration for position sizing"""
    method: PositionSizeMethod = PositionSizeMethod.KELLY
    kelly_fraction: float = 0.25  # Use 25% of full Kelly
    target_volatility: float = 0.12  # 12% annual volatility
    max_position_size: float = 0.15  # 15% maximum position
    min_position_size: float = 0.01  # 1% minimum position
    lookback_period: int = 252  # Days for calculations
    confidence_threshold: float = 0.6  # Minimum confidence
    risk_free_rate: float = 0.02  # 2% risk-free rate
    
@dataclass
class SizingConstraints:
    """Position sizing constraints"""
    max_leverage: float = 2.0
    max_concentration: float = 0.25
    min_diversification: int = 5
    max_correlation: float = 0.8
    cash_buffer: float = 0.05

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    recommended_size: float
    method_used: PositionSizeMethod
    confidence: float
    risk_score: float
    kelly_size: float
    risk_parity_size: float
    volatility_target_size: float
    constraints_applied: List[str]
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)

class KellyCriterion:
    """Kelly Criterion implementation for optimal position sizing"""
    
    def __init__(self, config: PositionSizeConfig):
        self.config = config
        self.historical_performance = []
        
    def calculate_kelly_size(self, expected_return: float, volatility: float, 
                           historical_returns: Optional[pd.Series] = None) -> float:
        """Calculate Kelly optimal position size"""
        try:
            if historical_returns is not None and len(historical_returns) >= 30:
                # Use historical data for more accurate calculation
                return self._calculate_empirical_kelly(historical_returns)
            else:
                # Use theoretical Kelly formula
                return self._calculate_theoretical_kelly(expected_return, volatility)
                
        except Exception as e:
            logger.error(f"Error calculating Kelly size: {e}")
            return self.config.min_position_size
    
    def _calculate_empirical_kelly(self, returns: pd.Series) -> float:
        """Calculate Kelly using empirical win rate and win/loss ratios"""
        try:
            # Calculate win rate and average win/loss
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            if len(positive_returns) == 0 or len(negative_returns) == 0:
                return self.config.min_position_size
            
            win_rate = len(positive_returns) / len(returns)
            avg_win = positive_returns.mean()
            avg_loss = abs(negative_returns.mean())
            
            if avg_loss == 0:
                return self.config.min_position_size
            
            # Kelly formula: f* = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
            
            # Apply safety factor
            kelly_fraction = max(0, min(kelly_fraction, 1.0)) * self.config.kelly_fraction
            
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"Error in empirical Kelly calculation: {e}")
            return self.config.min_position_size
    
    def _calculate_theoretical_kelly(self, expected_return: float, volatility: float) -> float:
        """Calculate Kelly using expected return and volatility"""
        try:
            if volatility <= 0:
                return self.config.min_position_size
            
            # Theoretical Kelly: f* = μ / σ²
            kelly_fraction = expected_return / (volatility ** 2)
            
            # Apply safety factor
            kelly_fraction = max(0, min(kelly_fraction, 1.0)) * self.config.kelly_fraction
            
            return kelly_fraction
            
        except Exception as e:
            logger.error(f"Error in theoretical Kelly calculation: {e}")
            return self.config.min_position_size

class RiskParitySizer:
    """Risk Parity position sizing implementation"""
    
    def __init__(self, config: PositionSizeConfig):
        self.config = config
        
    def calculate_risk_parity_size(self, volatility: float, 
                                 portfolio_volatilities: List[float],
                                 target_risk_contribution: float = None) -> float:
        """Calculate risk parity position size"""
        try:
            if volatility <= 0:
                return self.config.min_position_size
            
            # If no target specified, use equal risk contribution
            if target_risk_contribution is None:
                n_positions = len(portfolio_volatilities) + 1  # +1 for new position
                target_risk_contribution = 1.0 / n_positions
            
            # Risk parity: position size inversely proportional to volatility
            # Adjust for target risk contribution
            risk_parity_size = target_risk_contribution / volatility
            
            # Scale to reasonable range
            risk_parity_size = max(self.config.min_position_size, 
                                 min(self.config.max_position_size, risk_parity_size))
            
            return risk_parity_size
            
        except Exception as e:
            logger.error(f"Error calculating risk parity size: {e}")
            return self.config.min_position_size

class VolatilityTargetSizer:
    """Volatility targeting position sizing"""
    
    def __init__(self, config: PositionSizeConfig):
        self.config = config
        
    def calculate_volatility_target_size(self, asset_volatility: float,
                                       portfolio_volatility: float = None) -> float:
        """Calculate position size for volatility targeting"""
        try:
            if asset_volatility <= 0:
                return self.config.min_position_size
            
            # Target volatility scaling
            vol_target_size = self.config.target_volatility / asset_volatility
            
            # If we have portfolio volatility, adjust for diversification
            if portfolio_volatility is not None and portfolio_volatility > 0:
                diversification_factor = min(1.0, self.config.target_volatility / portfolio_volatility)
                vol_target_size *= diversification_factor
            
            # Apply constraints
            vol_target_size = max(self.config.min_position_size,
                                min(self.config.max_position_size, vol_target_size))
            
            return vol_target_size
            
        except Exception as e:
            logger.error(f"Error calculating volatility target size: {e}")
            return self.config.min_position_size

class AdaptiveSizer:
    """Adaptive position sizing based on market conditions and performance"""
    
    def __init__(self, config: PositionSizeConfig):
        self.config = config
        self.performance_history = []
        self.market_regime_history = []
        
    def calculate_adaptive_size(self, base_size: float, 
                              signal_confidence: float,
                              market_regime: str,
                              recent_performance: float) -> float:
        """Calculate adaptive position size"""
        try:
            adaptive_size = base_size
            
            # Confidence adjustment
            confidence_multiplier = 0.5 + 0.5 * signal_confidence  # 0.5 to 1.0
            adaptive_size *= confidence_multiplier
            
            # Market regime adjustment
            regime_multipliers = {
                'TRENDING': 1.2,
                'MEAN_REVERTING': 1.0,
                'VOLATILE': 0.6,
                'CRISIS': 0.3,
                'RECOVERY': 1.1
            }
            
            regime_multiplier = regime_multipliers.get(market_regime, 1.0)
            adaptive_size *= regime_multiplier
            
            # Recent performance adjustment
            if recent_performance > 0.02:  # Good performance
                adaptive_size *= 1.1
            elif recent_performance < -0.02:  # Poor performance
                adaptive_size *= 0.9
            
            # Apply constraints
            adaptive_size = max(self.config.min_position_size,
                              min(self.config.max_position_size, adaptive_size))
            
            return adaptive_size
            
        except Exception as e:
            logger.error(f"Error calculating adaptive size: {e}")
            return base_size

class PositionSizer:
    """
    Advanced Position Sizing System
    
    Provides multiple position sizing algorithms with:
    - Kelly Criterion for optimal growth
    - Risk Parity for balanced allocation
    - Volatility Targeting for consistent exposure
    - Adaptive sizing based on conditions
    - Comprehensive constraint handling
    """
    
    def __init__(self, method: PositionSizeMethod = PositionSizeMethod.KELLY,
                 config: Optional[PositionSizeConfig] = None):
        """Initialize position sizer"""
        self.method = method
        self.config = config or PositionSizeConfig()
        
        # Initialize component sizers
        self.kelly_sizer = KellyCriterion(self.config)
        self.risk_parity_sizer = RiskParitySizer(self.config)
        self.volatility_sizer = VolatilityTargetSizer(self.config)
        self.adaptive_sizer = AdaptiveSizer(self.config)
        
        # Performance tracking
        self.sizing_history = []
        self.performance_feedback = []
        
        logger.info(f"Position sizer initialized with method: {method.value}")
    
    def calculate_position_size(self, 
                              expected_return: float,
                              volatility: float,
                              signal_confidence: float,
                              portfolio_state: Dict[str, Any],
                              constraints: Optional[SizingConstraints] = None,
                              historical_returns: Optional[pd.Series] = None,
                              market_regime: str = "NORMAL") -> PositionSizeResult:
        """Calculate optimal position size using specified method"""
        try:
            # Calculate sizes using different methods
            kelly_size = self.kelly_sizer.calculate_kelly_size(
                expected_return, volatility, historical_returns
            )
            
            portfolio_vols = [pos.get('volatility', 0.1) for pos in portfolio_state.get('positions', {}).values()]
            risk_parity_size = self.risk_parity_sizer.calculate_risk_parity_size(
                volatility, portfolio_vols
            )
            
            portfolio_vol = portfolio_state.get('metrics', {}).get('volatility', 0.1)
            volatility_target_size = self.volatility_sizer.calculate_volatility_target_size(
                volatility, portfolio_vol
            )
            
            # Select primary method
            if self.method == PositionSizeMethod.KELLY:
                base_size = kelly_size
                reasoning = f"Kelly criterion: {kelly_size:.3f} (fraction: {self.config.kelly_fraction})"
            elif self.method == PositionSizeMethod.RISK_PARITY:
                base_size = risk_parity_size
                reasoning = f"Risk parity: {risk_parity_size:.3f} (inverse volatility)"
            elif self.method == PositionSizeMethod.VOLATILITY_TARGET:
                base_size = volatility_target_size
                reasoning = f"Volatility target: {volatility_target_size:.3f} (target: {self.config.target_volatility:.1%})"
            elif self.method == PositionSizeMethod.EQUAL_WEIGHT:
                base_size = 1.0 / max(10, len(portfolio_state.get('positions', {})) + 1)
                reasoning = f"Equal weight: {base_size:.3f}"
            elif self.method == PositionSizeMethod.ADAPTIVE:
                # Use ensemble of methods
                base_size = (kelly_size * 0.4 + risk_parity_size * 0.3 + volatility_target_size * 0.3)
                reasoning = f"Adaptive ensemble: {base_size:.3f}"
            else:
                base_size = kelly_size
                reasoning = f"Default Kelly: {base_size:.3f}"
            
            # Apply adaptive adjustments
            recent_performance = portfolio_state.get('metrics', {}).get('daily_return', 0.0)
            adaptive_size = self.adaptive_sizer.calculate_adaptive_size(
                base_size, signal_confidence, market_regime, recent_performance
            )
            
            # Apply constraints
            final_size, constraints_applied = self._apply_constraints(
                adaptive_size, portfolio_state, constraints
            )
            
            # Calculate confidence and risk score
            confidence = self._calculate_confidence(signal_confidence, volatility, portfolio_state)
            risk_score = self._calculate_risk_score(final_size, volatility, portfolio_state)
            
            # Create result
            result = PositionSizeResult(
                recommended_size=final_size,
                method_used=self.method,
                confidence=confidence,
                risk_score=risk_score,
                kelly_size=kelly_size,
                risk_parity_size=risk_parity_size,
                volatility_target_size=volatility_target_size,
                constraints_applied=constraints_applied,
                reasoning=reasoning
            )
            
            # Record for learning
            self.sizing_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return PositionSizeResult(
                recommended_size=self.config.min_position_size,
                method_used=self.method,
                confidence=0.0,
                risk_score=1.0,
                kelly_size=0.0,
                risk_parity_size=0.0,
                volatility_target_size=0.0,
                constraints_applied=["error_fallback"],
                reasoning="Error in calculation - using minimum size"
            )
    
    def _apply_constraints(self, size: float, portfolio_state: Dict[str, Any],
                          constraints: Optional[SizingConstraints]) -> Tuple[float, List[str]]:
        """Apply position sizing constraints"""
        applied_constraints = []
        final_size = size
        
        try:
            # Default constraints
            if constraints is None:
                constraints = SizingConstraints()
            
            # Maximum position size
            if final_size > self.config.max_position_size:
                final_size = self.config.max_position_size
                applied_constraints.append("max_position_size")
            
            # Minimum position size
            if final_size < self.config.min_position_size:
                final_size = self.config.min_position_size
                applied_constraints.append("min_position_size")
            
            # Portfolio-level constraints
            portfolio_metrics = portfolio_state.get('metrics', {})
            total_value = portfolio_metrics.get('total_value', 1000000)
            
            # Leverage constraint
            current_leverage = portfolio_metrics.get('invested_capital', 0) / total_value
            if current_leverage + final_size > constraints.max_leverage:
                max_additional = constraints.max_leverage - current_leverage
                final_size = max(0, max_additional)
                applied_constraints.append("max_leverage")
            
            # Concentration constraint
            if final_size > constraints.max_concentration:
                final_size = constraints.max_concentration
                applied_constraints.append("max_concentration")
            
            # Cash buffer constraint
            cash_ratio = portfolio_metrics.get('cash', 0) / total_value
            if cash_ratio - final_size < constraints.cash_buffer:
                max_size = cash_ratio - constraints.cash_buffer
                final_size = max(0, max_size)
                applied_constraints.append("cash_buffer")
            
            return final_size, applied_constraints
            
        except Exception as e:
            logger.error(f"Error applying constraints: {e}")
            return self.config.min_position_size, ["error_constraint"]
    
    def _calculate_confidence(self, signal_confidence: float, volatility: float,
                            portfolio_state: Dict[str, Any]) -> float:
        """Calculate overall confidence in position sizing"""
        try:
            # Base confidence from signal
            confidence = signal_confidence
            
            # Adjust for volatility (lower volatility = higher confidence)
            vol_adjustment = max(0.5, 1.0 - volatility)
            confidence *= vol_adjustment
            
            # Adjust for portfolio performance
            portfolio_metrics = portfolio_state.get('metrics', {})
            sharpe_ratio = portfolio_metrics.get('sharpe_ratio', 0)
            if sharpe_ratio > 1.0:
                confidence *= 1.1
            elif sharpe_ratio < 0:
                confidence *= 0.9
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _calculate_risk_score(self, position_size: float, volatility: float,
                            portfolio_state: Dict[str, Any]) -> float:
        """Calculate risk score for the position (0-1, where 1 is highest risk)"""
        try:
            risk_score = 0.0
            
            # Size risk
            size_risk = position_size / self.config.max_position_size
            risk_score += size_risk * 0.3
            
            # Volatility risk
            vol_risk = min(1.0, volatility / 0.3)  # Normalize to 30% volatility
            risk_score += vol_risk * 0.4
            
            # Portfolio risk
            portfolio_metrics = portfolio_state.get('metrics', {})
            portfolio_var = abs(portfolio_metrics.get('var_95', 0))
            var_risk = min(1.0, portfolio_var / 0.05)  # Normalize to 5% VaR
            risk_score += var_risk * 0.3
            
            return max(0.0, min(1.0, risk_score))
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5
    
    def update_performance_feedback(self, position_id: str, realized_return: float,
                                  holding_period: timedelta) -> None:
        """Update position sizer with performance feedback"""
        try:
            feedback = {
                'position_id': position_id,
                'realized_return': realized_return,
                'holding_period': holding_period,
                'timestamp': datetime.now()
            }
            
            self.performance_feedback.append(feedback)
            
            # Keep only recent feedback
            if len(self.performance_feedback) > 100:
                self.performance_feedback = self.performance_feedback[-100:]
            
            # Update adaptive parameters based on feedback
            self._update_adaptive_parameters()
            
        except Exception as e:
            logger.error(f"Error updating performance feedback: {e}")
    
    def _update_adaptive_parameters(self) -> None:
        """Update adaptive parameters based on performance feedback"""
        try:
            if len(self.performance_feedback) < 10:
                return
            
            # Calculate recent performance statistics
            recent_returns = [f['realized_return'] for f in self.performance_feedback[-20:]]
            avg_return = np.mean(recent_returns)
            
            # Adjust Kelly fraction based on performance
            if avg_return > 0.02:  # Good performance
                self.config.kelly_fraction = min(0.5, self.config.kelly_fraction * 1.05)
            elif avg_return < -0.02:  # Poor performance
                self.config.kelly_fraction = max(0.1, self.config.kelly_fraction * 0.95)
            
            logger.info(f"Updated Kelly fraction to {self.config.kelly_fraction:.3f} based on performance")
            
        except Exception as e:
            logger.error(f"Error updating adaptive parameters: {e}")
    
    def get_sizing_summary(self) -> Dict[str, Any]:
        """Get comprehensive position sizing summary"""
        try:
            return {
                'position_sizer_status': 'active',
                'method': self.method.value,
                'configuration': {
                    'kelly_fraction': self.config.kelly_fraction,
                    'target_volatility': self.config.target_volatility,
                    'max_position_size': self.config.max_position_size,
                    'min_position_size': self.config.min_position_size,
                    'confidence_threshold': self.config.confidence_threshold
                },
                'performance_tracking': {
                    'sizing_history_count': len(self.sizing_history),
                    'performance_feedback_count': len(self.performance_feedback),
                    'avg_recent_confidence': np.mean([s.confidence for s in self.sizing_history[-10:]]) if self.sizing_history else 0.0,
                    'avg_recent_risk_score': np.mean([s.risk_score for s in self.sizing_history[-10:]]) if self.sizing_history else 0.0
                },
                'recent_sizings': [
                    {
                        'timestamp': s.timestamp.isoformat(),
                        'method': s.method_used.value,
                        'size': s.recommended_size,
                        'confidence': s.confidence,
                        'risk_score': s.risk_score
                    }
                    for s in self.sizing_history[-5:]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating sizing summary: {e}")
            return {'error': str(e)} 