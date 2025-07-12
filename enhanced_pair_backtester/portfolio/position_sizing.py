"""
Position Sizing Module for Enhanced Pair Backtesting System

This module implements advanced position sizing strategies including:
- Kelly Criterion for optimal position sizing
- Risk Parity for balanced risk allocation
- Volatility-based position sizing
- Regime-aware position sizing
- Dynamic position sizing with market conditions

Author: Enhanced Pair Backtesting System
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
from scipy.optimize import minimize_scalar
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class PositionSizeMethod(Enum):
    """Position sizing methods"""
    KELLY_CRITERION = "kelly"
    RISK_PARITY = "risk_parity"
    VOLATILITY_SCALED = "volatility_scaled"
    FIXED_FRACTIONAL = "fixed_fractional"
    REGIME_AWARE = "regime_aware"
    DYNAMIC_KELLY = "dynamic_kelly"
    MAX_DRAWDOWN = "max_drawdown"

@dataclass
class PositionSizeConfig:
    """Configuration for position sizing strategies"""
    # General parameters
    max_position_size: float = 0.3  # Maximum 30% of capital
    min_position_size: float = 0.01  # Minimum 1% of capital
    target_volatility: float = 0.15  # Target 15% annualized volatility
    
    # Kelly Criterion parameters
    kelly_fraction: float = 0.25  # Use 25% of full Kelly
    kelly_lookback: int = 252  # Days for Kelly calculation
    min_kelly_observations: int = 50  # Minimum observations for Kelly
    
    # Risk Parity parameters
    risk_budget: float = 0.02  # 2% daily risk budget
    correlation_adjustment: bool = True  # Adjust for correlation
    
    # Volatility scaling parameters
    volatility_lookback: int = 60  # Days for volatility calculation
    volatility_floor: float = 0.01  # Minimum volatility (1%)
    volatility_cap: float = 1.0  # Maximum volatility (100%)
    
    # Regime-aware parameters
    regime_multipliers: Dict[str, float] = None  # Multipliers by regime
    regime_confidence_threshold: float = 0.7  # Minimum regime confidence
    
    # Risk management parameters
    max_drawdown_limit: float = 0.15  # Maximum 15% drawdown
    concentration_limit: float = 0.5  # Maximum 50% in single position
    leverage_limit: float = 2.0  # Maximum 2x leverage
    
    # Dynamic adjustment parameters
    performance_adjustment: bool = True  # Adjust based on performance
    momentum_factor: float = 0.1  # Momentum adjustment factor
    mean_reversion_factor: float = 0.05  # Mean reversion factor
    
    def __post_init__(self):
        """Initialize default regime multipliers"""
        if self.regime_multipliers is None:
            self.regime_multipliers = {
                'MEAN_REVERTING': 1.2,  # Increase size in mean-reverting regimes
                'TRENDING': 0.8,        # Reduce size in trending regimes
                'VOLATILE': 0.5         # Significantly reduce in volatile regimes
            }

@dataclass
class PositionSizeResult:
    """Result from position sizing calculation"""
    position_size: float  # Final position size (0-1)
    method: str  # Method used
    confidence: float  # Confidence in sizing (0-1)
    risk_metrics: Dict[str, float]  # Risk metrics
    adjustments: Dict[str, float]  # Applied adjustments
    metadata: Dict[str, Any]  # Additional metadata
    
    @property
    def dollar_amount(self) -> float:
        """Convert to dollar amount given capital"""
        return self.position_size * self.metadata.get('capital', 1000000)
    
    @property
    def leverage(self) -> float:
        """Calculate leverage ratio"""
        return self.position_size / self.metadata.get('base_position', 0.1)

class PositionSizer:
    """
    Advanced position sizing system with multiple strategies
    """
    
    def __init__(self, config: PositionSizeConfig = None):
        self.config = config or PositionSizeConfig()
        self.performance_history = []
        self.position_history = []
        self.current_drawdown = 0.0
        self.peak_value = 0.0
        
        logger.info(f"Position Sizer initialized with method: {self.config}")
    
    def calculate_position_size(self, 
                              signal_strength: float,
                              signal_confidence: float,
                              expected_return: float,
                              volatility: float,
                              capital: float,
                              method: PositionSizeMethod = PositionSizeMethod.KELLY_CRITERION,
                              historical_returns: Optional[pd.Series] = None,
                              regime: Optional[str] = None,
                              regime_confidence: float = 1.0,
                              **kwargs) -> PositionSizeResult:
        """
        Calculate optimal position size using specified method
        
        Args:
            signal_strength: Signal strength (0-100)
            signal_confidence: Signal confidence (0-1)
            expected_return: Expected return
            volatility: Expected volatility
            capital: Available capital
            method: Position sizing method
            historical_returns: Historical returns for Kelly calculation
            regime: Current market regime
            regime_confidence: Confidence in regime detection
            **kwargs: Additional parameters
            
        Returns:
            PositionSizeResult with sizing recommendation
        """
        try:
            # Base position size calculation
            if method == PositionSizeMethod.KELLY_CRITERION:
                base_size = self._calculate_kelly_criterion(
                    expected_return, volatility, historical_returns
                )
            elif method == PositionSizeMethod.DYNAMIC_KELLY:
                base_size = self._calculate_dynamic_kelly(
                    expected_return, volatility, historical_returns, signal_confidence
                )
            elif method == PositionSizeMethod.RISK_PARITY:
                base_size = self._calculate_risk_parity(volatility, capital)
            elif method == PositionSizeMethod.VOLATILITY_SCALED:
                base_size = self._calculate_volatility_scaled(volatility)
            elif method == PositionSizeMethod.FIXED_FRACTIONAL:
                base_size = self._calculate_fixed_fractional(signal_strength)
            elif method == PositionSizeMethod.REGIME_AWARE:
                base_size = self._calculate_regime_aware(
                    expected_return, volatility, regime, regime_confidence
                )
            elif method == PositionSizeMethod.MAX_DRAWDOWN:
                base_size = self._calculate_max_drawdown_based(
                    expected_return, volatility, capital
                )
            else:
                raise ValueError(f"Unknown position sizing method: {method}")
            
            # Apply adjustments
            adjustments = {}
            final_size = base_size
            
            # Signal strength adjustment
            strength_adj = self._apply_signal_strength_adjustment(
                final_size, signal_strength, signal_confidence
            )
            adjustments['signal_strength'] = strength_adj / final_size if final_size > 0 else 1.0
            final_size = strength_adj
            
            # Regime adjustment
            if regime and regime_confidence > self.config.regime_confidence_threshold:
                regime_adj = self._apply_regime_adjustment(final_size, regime, regime_confidence)
                adjustments['regime'] = regime_adj / final_size if final_size > 0 else 1.0
                final_size = regime_adj
            
            # Risk management constraints
            risk_adj = self._apply_risk_constraints(final_size, capital)
            adjustments['risk_management'] = risk_adj / final_size if final_size > 0 else 1.0
            final_size = risk_adj
            
            # Performance-based adjustment
            if self.config.performance_adjustment and len(self.performance_history) > 10:
                perf_adj = self._apply_performance_adjustment(final_size)
                adjustments['performance'] = perf_adj / final_size if final_size > 0 else 1.0
                final_size = perf_adj
            
            # Final bounds check
            final_size = max(self.config.min_position_size, 
                           min(self.config.max_position_size, final_size))
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(
                final_size, volatility, expected_return, capital
            )
            
            # Calculate confidence
            confidence = self._calculate_sizing_confidence(
                method, signal_confidence, regime_confidence, risk_metrics
            )
            
            # Create result
            result = PositionSizeResult(
                position_size=final_size,
                method=method.value,
                confidence=confidence,
                risk_metrics=risk_metrics,
                adjustments=adjustments,
                metadata={
                    'capital': capital,
                    'base_position': base_size,
                    'signal_strength': signal_strength,
                    'signal_confidence': signal_confidence,
                    'expected_return': expected_return,
                    'volatility': volatility,
                    'regime': regime,
                    'regime_confidence': regime_confidence
                }
            )
            
            # Store for history
            self.position_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            # Return conservative default
            return PositionSizeResult(
                position_size=self.config.min_position_size,
                method="default",
                confidence=0.5,
                risk_metrics={'var_95': 0.0, 'expected_loss': 0.0},
                adjustments={},
                metadata={'error': str(e)}
            )
    
    def _calculate_kelly_criterion(self, expected_return: float, volatility: float,
                                 historical_returns: Optional[pd.Series] = None) -> float:
        """Calculate Kelly Criterion position size"""
        if historical_returns is not None and len(historical_returns) >= self.config.min_kelly_observations:
            # Use historical data for more accurate Kelly calculation
            returns = historical_returns.dropna()
            if len(returns) < self.config.min_kelly_observations:
                logger.warning("Insufficient historical data for Kelly calculation")
                return self.config.min_position_size
            
            # Calculate win rate and average win/loss
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            if len(positive_returns) == 0 or len(negative_returns) == 0:
                logger.warning("No positive or negative returns for Kelly calculation")
                return self.config.min_position_size
            
            win_rate = len(positive_returns) / len(returns)
            avg_win = positive_returns.mean()
            avg_loss = abs(negative_returns.mean())
            
            # Kelly formula: f* = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
            if avg_loss == 0:
                return self.config.min_position_size
            
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
        else:
            # Use expected return and volatility
            if volatility == 0:
                return self.config.min_position_size
            
            # Simplified Kelly: f* = μ / σ²
            kelly_fraction = expected_return / (volatility ** 2)
        
        # Apply Kelly fraction multiplier for safety
        kelly_position = kelly_fraction * self.config.kelly_fraction
        
        # Ensure positive and reasonable
        return max(0, min(kelly_position, self.config.max_position_size))
    
    def _calculate_dynamic_kelly(self, expected_return: float, volatility: float,
                               historical_returns: Optional[pd.Series] = None,
                               signal_confidence: float = 1.0) -> float:
        """Calculate dynamic Kelly that adjusts based on signal confidence"""
        base_kelly = self._calculate_kelly_criterion(expected_return, volatility, historical_returns)
        
        # Adjust Kelly based on signal confidence
        confidence_multiplier = 0.5 + 0.5 * signal_confidence  # Range: 0.5 to 1.0
        
        # Adjust based on recent performance
        if len(self.performance_history) > 5:
            recent_returns = pd.Series(self.performance_history[-10:])
            if recent_returns.std() > 0:
                sharpe_ratio = recent_returns.mean() / recent_returns.std()
                sharpe_multiplier = max(0.5, min(1.5, 1.0 + sharpe_ratio * 0.1))
            else:
                sharpe_multiplier = 1.0
        else:
            sharpe_multiplier = 1.0
        
        dynamic_kelly = base_kelly * confidence_multiplier * sharpe_multiplier
        
        return max(self.config.min_position_size, 
                  min(self.config.max_position_size, dynamic_kelly))
    
    def _calculate_risk_parity(self, volatility: float, capital: float) -> float:
        """Calculate risk parity position size"""
        if volatility == 0:
            return self.config.min_position_size
        
        # Risk parity: position size = risk_budget / volatility
        risk_parity_size = self.config.risk_budget / volatility
        
        # Adjust for capital
        risk_parity_size = min(risk_parity_size, capital * 0.001)  # Max 0.1% of capital per 1% volatility
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, risk_parity_size))
    
    def _calculate_volatility_scaled(self, volatility: float) -> float:
        """Calculate volatility-scaled position size"""
        # Inverse volatility scaling: higher volatility = smaller position
        vol_adjusted = max(self.config.volatility_floor, 
                          min(self.config.volatility_cap, volatility))
        
        # Target volatility scaling
        vol_scalar = self.config.target_volatility / vol_adjusted
        
        base_size = 0.1  # 10% base position
        scaled_size = base_size * vol_scalar
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, scaled_size))
    
    def _calculate_fixed_fractional(self, signal_strength: float) -> float:
        """Calculate fixed fractional position size based on signal strength"""
        # Linear scaling based on signal strength
        strength_fraction = signal_strength / 100.0  # Convert to 0-1
        
        # Scale between min and max position size
        position_range = self.config.max_position_size - self.config.min_position_size
        fixed_size = self.config.min_position_size + (strength_fraction * position_range)
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, fixed_size))
    
    def _calculate_regime_aware(self, expected_return: float, volatility: float,
                              regime: str, regime_confidence: float) -> float:
        """Calculate regime-aware position size"""
        # Start with Kelly criterion
        base_size = self._calculate_kelly_criterion(expected_return, volatility)
        
        # Apply regime multiplier
        if regime in self.config.regime_multipliers:
            regime_multiplier = self.config.regime_multipliers[regime]
            # Weight by regime confidence
            adjusted_multiplier = 1.0 + (regime_multiplier - 1.0) * regime_confidence
            regime_size = base_size * adjusted_multiplier
        else:
            regime_size = base_size
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, regime_size))
    
    def _calculate_max_drawdown_based(self, expected_return: float, 
                                    volatility: float, capital: float) -> float:
        """Calculate position size based on maximum drawdown limits"""
        if volatility == 0:
            return self.config.min_position_size
        
        # Calculate position size that limits maximum drawdown
        # Assuming 2-sigma move (95% confidence)
        max_loss_per_trade = 2 * volatility
        max_capital_loss = capital * self.config.max_drawdown_limit
        
        # Position size = max_capital_loss / max_loss_per_trade
        drawdown_size = max_capital_loss / (max_loss_per_trade * capital)
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, drawdown_size))
    
    def _apply_signal_strength_adjustment(self, position_size: float,
                                        signal_strength: float,
                                        signal_confidence: float) -> float:
        """Apply signal strength and confidence adjustments"""
        # Strength adjustment (0-100 scale)
        strength_multiplier = 0.5 + 0.5 * (signal_strength / 100.0)
        
        # Confidence adjustment (0-1 scale)
        confidence_multiplier = 0.7 + 0.3 * signal_confidence
        
        adjusted_size = position_size * strength_multiplier * confidence_multiplier
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, adjusted_size))
    
    def _apply_regime_adjustment(self, position_size: float, regime: str,
                               regime_confidence: float) -> float:
        """Apply regime-based adjustments"""
        if regime in self.config.regime_multipliers:
            regime_multiplier = self.config.regime_multipliers[regime]
            # Weight adjustment by confidence
            weighted_multiplier = 1.0 + (regime_multiplier - 1.0) * regime_confidence
            adjusted_size = position_size * weighted_multiplier
        else:
            adjusted_size = position_size
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, adjusted_size))
    
    def _apply_risk_constraints(self, position_size: float, capital: float) -> float:
        """Apply risk management constraints"""
        # Maximum drawdown constraint
        if self.current_drawdown > self.config.max_drawdown_limit * 0.8:
            # Reduce position size as we approach max drawdown
            drawdown_multiplier = 0.5
            position_size *= drawdown_multiplier
        
        # Concentration limit (if tracking multiple positions)
        # This would need to be expanded for portfolio-level risk management
        
        # Leverage limit
        if position_size > self.config.leverage_limit * 0.1:  # Assuming 10% base
            position_size = self.config.leverage_limit * 0.1
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, position_size))
    
    def _apply_performance_adjustment(self, position_size: float) -> float:
        """Apply performance-based adjustments"""
        if len(self.performance_history) < 10:
            return position_size
        
        recent_returns = pd.Series(self.performance_history[-20:])
        
        # Momentum adjustment
        if len(recent_returns) >= 5:
            momentum = recent_returns.tail(5).mean()
            momentum_adj = 1.0 + momentum * self.config.momentum_factor
            position_size *= momentum_adj
        
        # Mean reversion adjustment
        if len(recent_returns) >= 10:
            long_term_mean = recent_returns.mean()
            short_term_mean = recent_returns.tail(5).mean()
            mean_reversion = long_term_mean - short_term_mean
            reversion_adj = 1.0 + mean_reversion * self.config.mean_reversion_factor
            position_size *= reversion_adj
        
        return max(self.config.min_position_size,
                  min(self.config.max_position_size, position_size))
    
    def _calculate_risk_metrics(self, position_size: float, volatility: float,
                              expected_return: float, capital: float) -> Dict[str, float]:
        """Calculate risk metrics for the position"""
        position_value = position_size * capital
        
        # Value at Risk (95% confidence, 1-day)
        var_95 = position_value * volatility * 1.645  # 95% VaR
        
        # Expected loss
        expected_loss = position_value * max(0, -expected_return)
        
        # Maximum theoretical loss (assuming 100% loss)
        max_loss = position_value
        
        # Sharpe ratio estimate
        if volatility > 0:
            sharpe_estimate = expected_return / volatility
        else:
            sharpe_estimate = 0.0
        
        # Position heat (risk as % of capital)
        position_heat = var_95 / capital
        
        return {
            'var_95': var_95,
            'expected_loss': expected_loss,
            'max_loss': max_loss,
            'sharpe_estimate': sharpe_estimate,
            'position_heat': position_heat,
            'position_value': position_value
        }
    
    def _calculate_sizing_confidence(self, method: PositionSizeMethod,
                                   signal_confidence: float,
                                   regime_confidence: float,
                                   risk_metrics: Dict[str, float]) -> float:
        """Calculate confidence in the position sizing"""
        # Base confidence from method
        method_confidence = {
            PositionSizeMethod.KELLY_CRITERION: 0.8,
            PositionSizeMethod.DYNAMIC_KELLY: 0.85,
            PositionSizeMethod.RISK_PARITY: 0.7,
            PositionSizeMethod.VOLATILITY_SCALED: 0.6,
            PositionSizeMethod.FIXED_FRACTIONAL: 0.5,
            PositionSizeMethod.REGIME_AWARE: 0.75,
            PositionSizeMethod.MAX_DRAWDOWN: 0.7
        }.get(method, 0.5)
        
        # Adjust for signal confidence
        signal_adjustment = 0.8 + 0.2 * signal_confidence
        
        # Adjust for regime confidence
        regime_adjustment = 0.9 + 0.1 * regime_confidence
        
        # Adjust for risk metrics
        sharpe_ratio = risk_metrics.get('sharpe_estimate', 0.0)
        risk_adjustment = max(0.5, min(1.2, 1.0 + sharpe_ratio * 0.1))
        
        # Adjust for historical performance
        if len(self.performance_history) > 10:
            recent_performance = pd.Series(self.performance_history[-10:])
            if recent_performance.std() > 0:
                consistency = max(0.5, min(1.5, 1.0 / recent_performance.std()))
            else:
                consistency = 1.0
        else:
            consistency = 1.0
        
        # Combine all factors
        total_confidence = (method_confidence * signal_adjustment * 
                          regime_adjustment * risk_adjustment * consistency)
        
        return max(0.0, min(1.0, total_confidence))
    
    def update_performance(self, return_value: float):
        """Update performance history for adaptive sizing"""
        self.performance_history.append(return_value)
        
        # Keep only recent history
        if len(self.performance_history) > 252:  # Keep 1 year
            self.performance_history = self.performance_history[-252:]
        
        # Update drawdown tracking
        if len(self.performance_history) == 1:
            self.peak_value = return_value
        else:
            self.peak_value = max(self.peak_value, return_value)
        
        self.current_drawdown = (self.peak_value - return_value) / self.peak_value
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of position sizing performance"""
        if not self.position_history:
            return {}
        
        positions = [p.position_size for p in self.position_history]
        confidences = [p.confidence for p in self.position_history]
        
        return {
            'total_positions': len(positions),
            'average_position_size': np.mean(positions),
            'position_volatility': np.std(positions),
            'average_confidence': np.mean(confidences),
            'current_drawdown': self.current_drawdown,
            'peak_value': self.peak_value,
            'position_range': (min(positions), max(positions)),
            'recent_performance': self.performance_history[-10:] if len(self.performance_history) >= 10 else []
        }


def create_position_sizer(method: PositionSizeMethod = PositionSizeMethod.KELLY_CRITERION,
                         **config_kwargs) -> PositionSizer:
    """
    Create a position sizer with specified method and configuration
    
    Args:
        method: Position sizing method to use
        **config_kwargs: Configuration parameters
        
    Returns:
        Configured PositionSizer instance
    """
    config = PositionSizeConfig(**config_kwargs)
    return PositionSizer(config)


def calculate_optimal_position_size(signal_strength: float,
                                  signal_confidence: float,
                                  expected_return: float,
                                  volatility: float,
                                  capital: float,
                                  method: str = "kelly",
                                  **kwargs) -> PositionSizeResult:
    """
    Convenience function to calculate optimal position size
    
    Args:
        signal_strength: Signal strength (0-100)
        signal_confidence: Signal confidence (0-1)
        expected_return: Expected return
        volatility: Expected volatility
        capital: Available capital
        method: Position sizing method
        **kwargs: Additional parameters
        
    Returns:
        PositionSizeResult with sizing recommendation
    """
    method_enum = PositionSizeMethod(method)
    sizer = create_position_sizer(method_enum)
    
    return sizer.calculate_position_size(
        signal_strength=signal_strength,
        signal_confidence=signal_confidence,
        expected_return=expected_return,
        volatility=volatility,
        capital=capital,
        method=method_enum,
        **kwargs
    ) 