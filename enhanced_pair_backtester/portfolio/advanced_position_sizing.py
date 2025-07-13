import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import logging
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class VolatilityRegime(Enum):
    LOW = "low_volatility"
    NORMAL = "normal_volatility"
    HIGH = "high_volatility"
    CRISIS = "crisis_volatility"

class RiskLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

@dataclass
class PositionSizingResult:
    """Result of position sizing calculation"""
    symbol_pair: str
    recommended_size: float
    max_size: float
    kelly_size: float
    risk_adjusted_size: float
    confidence: float
    regime: VolatilityRegime
    risk_metrics: Dict
    constraints_applied: List[str]

@dataclass
class PortfolioConstraints:
    """Portfolio-level constraints"""
    max_portfolio_risk: float = 0.02  # 2% max portfolio risk
    max_single_position: float = 0.1   # 10% max single position
    max_correlation_exposure: float = 0.3  # 30% max correlated exposure
    max_drawdown_limit: float = 0.05   # 5% max drawdown
    min_diversification: int = 3       # Minimum 3 positions
    max_leverage: float = 2.0          # Maximum 2x leverage

class AdvancedPositionSizer:
    """
    Advanced position sizing system with multiple optimization criteria:
    
    1. Kelly Criterion - Optimal growth sizing
    2. Risk Parity - Equal risk contribution
    3. Volatility Targeting - Consistent volatility exposure
    4. Drawdown Protection - Dynamic sizing based on drawdowns
    5. Regime Awareness - Adjust sizing based on market regime
    6. Correlation Adjustment - Account for position correlations
    """
    
    def __init__(self, 
                 base_capital: float = 1000000,
                 risk_level: RiskLevel = RiskLevel.MODERATE,
                 constraints: Optional[PortfolioConstraints] = None):
        
        self.base_capital = base_capital
        self.risk_level = risk_level
        self.constraints = constraints or PortfolioConstraints()
        self.logger = logging.getLogger(__name__)
        
        # Risk level parameters
        self.risk_params = {
            RiskLevel.CONSERVATIVE: {
                'max_position_risk': 0.005,  # 0.5% max position risk
                'kelly_fraction': 0.25,      # 25% of Kelly
                'volatility_target': 0.08,   # 8% annual volatility
                'drawdown_threshold': 0.02   # 2% drawdown threshold
            },
            RiskLevel.MODERATE: {
                'max_position_risk': 0.01,   # 1% max position risk
                'kelly_fraction': 0.5,       # 50% of Kelly
                'volatility_target': 0.12,   # 12% annual volatility
                'drawdown_threshold': 0.03   # 3% drawdown threshold
            },
            RiskLevel.AGGRESSIVE: {
                'max_position_risk': 0.02,   # 2% max position risk
                'kelly_fraction': 0.75,      # 75% of Kelly
                'volatility_target': 0.18,   # 18% annual volatility
                'drawdown_threshold': 0.05   # 5% drawdown threshold
            }
        }
        
        # Regime-based adjustments
        self.regime_adjustments = {
            VolatilityRegime.LOW: {
                'size_multiplier': 1.2,
                'max_risk_multiplier': 1.1,
                'correlation_tolerance': 1.2
            },
            VolatilityRegime.NORMAL: {
                'size_multiplier': 1.0,
                'max_risk_multiplier': 1.0,
                'correlation_tolerance': 1.0
            },
            VolatilityRegime.HIGH: {
                'size_multiplier': 0.7,
                'max_risk_multiplier': 0.8,
                'correlation_tolerance': 0.8
            },
            VolatilityRegime.CRISIS: {
                'size_multiplier': 0.4,
                'max_risk_multiplier': 0.5,
                'correlation_tolerance': 0.5
            }
        }
        
        # Track position history for drawdown calculation
        self.position_history = []
        self.pnl_history = []
        self.current_drawdown = 0.0
        
    def classify_volatility_regime(self, 
                                 volatility: float,
                                 market_stress_indicator: float = 0.0) -> VolatilityRegime:
        """Classify current volatility regime"""
        
        # Adjust volatility for market stress
        adjusted_vol = volatility * (1 + market_stress_indicator)
        
        if adjusted_vol < 0.12:
            return VolatilityRegime.LOW
        elif adjusted_vol < 0.20:
            return VolatilityRegime.NORMAL
        elif adjusted_vol < 0.35:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.CRISIS
    
    def calculate_kelly_size(self, 
                           expected_return: float,
                           volatility: float,
                           win_rate: float = 0.55,
                           avg_win: float = 0.015,
                           avg_loss: float = 0.010) -> float:
        """Calculate Kelly optimal position size"""
        
        if volatility <= 0 or avg_loss <= 0:
            return 0.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
        
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate
        
        kelly_fraction = (b * p - q) / b
        
        # Ensure Kelly fraction is positive and reasonable
        kelly_fraction = max(0.0, min(kelly_fraction, 1.0))
        
        # Convert to position size based on volatility
        # Position size = Kelly fraction / volatility
        kelly_size = kelly_fraction / volatility
        
        # Apply Kelly fraction adjustment based on risk level
        risk_params = self.risk_params[self.risk_level]
        adjusted_kelly = kelly_size * risk_params['kelly_fraction']
        
        return adjusted_kelly
    
    def calculate_volatility_target_size(self, 
                                       volatility: float,
                                       target_volatility: Optional[float] = None) -> float:
        """Calculate position size for volatility targeting"""
        
        if target_volatility is None:
            target_volatility = self.risk_params[self.risk_level]['volatility_target']
        
        if volatility <= 0:
            return 0.0
        
        # Position size = target volatility / asset volatility
        vol_target_size = target_volatility / volatility
        
        return vol_target_size
    
    def calculate_risk_parity_size(self, 
                                 volatility: float,
                                 correlation_matrix: Optional[np.ndarray] = None) -> float:
        """Calculate risk parity position size"""
        
        if volatility <= 0:
            return 0.0
        
        # Base risk parity size (inverse volatility)
        base_size = 1.0 / volatility
        
        # Adjust for correlation if provided
        if correlation_matrix is not None:
            # Simplified correlation adjustment
            avg_correlation = np.mean(correlation_matrix) if correlation_matrix.size > 1 else 0.0
            correlation_adjustment = 1.0 / (1.0 + abs(avg_correlation))
            base_size *= correlation_adjustment
        
        return base_size
    
    def calculate_drawdown_adjustment(self, 
                                    current_pnl: float = 0.0,
                                    lookback_days: int = 30) -> float:
        """Calculate position size adjustment based on recent drawdown"""
        
        # Update PnL history
        self.pnl_history.append(current_pnl)
        if len(self.pnl_history) > lookback_days:
            self.pnl_history.pop(0)
        
        if len(self.pnl_history) < 2:
            return 1.0
        
        # Calculate running maximum and current drawdown
        cumulative_pnl = np.cumsum(self.pnl_history)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdowns = (cumulative_pnl - running_max) / self.base_capital
        
        self.current_drawdown = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        
        # Drawdown adjustment
        risk_params = self.risk_params[self.risk_level]
        drawdown_threshold = risk_params['drawdown_threshold']
        
        if abs(self.current_drawdown) > drawdown_threshold:
            # Reduce position size based on drawdown severity
            adjustment = max(0.1, 1.0 - (abs(self.current_drawdown) / drawdown_threshold))
        else:
            # Slightly increase size if performing well
            adjustment = min(1.2, 1.0 + (abs(self.current_drawdown) / drawdown_threshold) * 0.1)
        
        return adjustment
    
    def calculate_correlation_adjustment(self, 
                                       existing_positions: List[Dict],
                                       new_position_correlation: float) -> float:
        """Calculate adjustment for position correlation"""
        
        if not existing_positions:
            return 1.0
        
        # Calculate total correlation exposure
        total_correlation_exposure = sum(
            pos.get('size', 0) * abs(pos.get('correlation', 0))
            for pos in existing_positions
        )
        
        # Add new position correlation
        new_correlation_exposure = abs(new_position_correlation)
        total_exposure = total_correlation_exposure + new_correlation_exposure
        
        # Apply correlation constraint
        max_correlation = self.constraints.max_correlation_exposure
        
        if total_exposure > max_correlation:
            # Reduce size to maintain correlation constraint
            adjustment = max(0.1, max_correlation / total_exposure)
        else:
            adjustment = 1.0
        
        return adjustment
    
    def apply_portfolio_constraints(self, 
                                  proposed_size: float,
                                  current_portfolio_value: float,
                                  existing_positions: List[Dict]) -> Tuple[float, List[str]]:
        """Apply portfolio-level constraints"""
        
        constraints_applied = []
        final_size = proposed_size
        
        # Maximum single position constraint
        max_single_position = self.constraints.max_single_position * current_portfolio_value
        if final_size > max_single_position:
            final_size = max_single_position
            constraints_applied.append("max_single_position")
        
        # Maximum portfolio risk constraint
        risk_params = self.risk_params[self.risk_level]
        max_position_risk = risk_params['max_position_risk'] * current_portfolio_value
        if final_size > max_position_risk:
            final_size = max_position_risk
            constraints_applied.append("max_position_risk")
        
        # Maximum leverage constraint
        total_exposure = sum(pos.get('size', 0) for pos in existing_positions) + final_size
        max_leverage_amount = self.constraints.max_leverage * current_portfolio_value
        if total_exposure > max_leverage_amount:
            adjustment = max_leverage_amount / total_exposure
            final_size *= adjustment
            constraints_applied.append("max_leverage")
        
        # Minimum position size (avoid dust positions)
        min_position_size = current_portfolio_value * 0.001  # 0.1% minimum
        if final_size < min_position_size:
            final_size = 0.0
            constraints_applied.append("min_position_size")
        
        return final_size, constraints_applied
    
    def calculate_optimal_position_size(self, 
                                      symbol_pair: str,
                                      expected_return: float,
                                      volatility: float,
                                      current_portfolio_value: float,
                                      existing_positions: Optional[List[Dict]] = None,
                                      market_regime_data: Optional[Dict] = None,
                                      correlation_data: Optional[Dict] = None) -> PositionSizingResult:
        """Calculate optimal position size using multiple methods"""
        
        if existing_positions is None:
            existing_positions = []
        
        # Classify volatility regime
        market_stress = market_regime_data.get('stress_indicator', 0.0) if market_regime_data else 0.0
        regime = self.classify_volatility_regime(volatility, market_stress)
        
        # Calculate base sizes using different methods
        kelly_size = self.calculate_kelly_size(expected_return, volatility)
        vol_target_size = self.calculate_volatility_target_size(volatility)
        risk_parity_size = self.calculate_risk_parity_size(volatility)
        
        # Calculate adjustments
        drawdown_adj = self.calculate_drawdown_adjustment()
        
        correlation = correlation_data.get('correlation', 0.0) if correlation_data else 0.0
        correlation_adj = self.calculate_correlation_adjustment(existing_positions, correlation)
        
        # Regime-based adjustment
        regime_params = self.regime_adjustments[regime]
        regime_adj = regime_params['size_multiplier']
        
        # Combine sizing methods (weighted average)
        combined_size = (
            kelly_size * 0.4 +
            vol_target_size * 0.3 +
            risk_parity_size * 0.3
        )
        
        # Apply all adjustments
        adjusted_size = combined_size * drawdown_adj * correlation_adj * regime_adj
        
        # Convert to dollar amount
        dollar_size = adjusted_size * current_portfolio_value
        
        # Apply portfolio constraints
        final_size, constraints = self.apply_portfolio_constraints(
            dollar_size, current_portfolio_value, existing_positions
        )
        
        # Calculate confidence based on regime and adjustments
        confidence = self._calculate_confidence(regime, drawdown_adj, correlation_adj)
        
        # Risk metrics
        risk_metrics = {
            'position_risk': final_size / current_portfolio_value,
            'volatility_contribution': (final_size / current_portfolio_value) * volatility,
            'correlation_exposure': correlation,
            'regime_adjustment': regime_adj,
            'drawdown_adjustment': drawdown_adj,
            'current_drawdown': self.current_drawdown
        }
        
        return PositionSizingResult(
            symbol_pair=symbol_pair,
            recommended_size=final_size,
            max_size=dollar_size,
            kelly_size=kelly_size * current_portfolio_value,
            risk_adjusted_size=adjusted_size * current_portfolio_value,
            confidence=confidence,
            regime=regime,
            risk_metrics=risk_metrics,
            constraints_applied=constraints
        )
    
    def _calculate_confidence(self, 
                            regime: VolatilityRegime,
                            drawdown_adj: float,
                            correlation_adj: float) -> float:
        """Calculate confidence score for position sizing"""
        
        # Base confidence by regime
        regime_confidence = {
            VolatilityRegime.LOW: 0.9,
            VolatilityRegime.NORMAL: 0.8,
            VolatilityRegime.HIGH: 0.6,
            VolatilityRegime.CRISIS: 0.4
        }
        
        base_confidence = regime_confidence[regime]
        
        # Adjust for drawdown (lower confidence if in drawdown)
        drawdown_confidence = min(1.0, drawdown_adj + 0.5)
        
        # Adjust for correlation (lower confidence if high correlation)
        correlation_confidence = min(1.0, correlation_adj + 0.3)
        
        # Combined confidence
        combined_confidence = base_confidence * drawdown_confidence * correlation_confidence
        
        return max(0.1, min(1.0, combined_confidence))
    
    def optimize_portfolio_allocation(self, 
                                    opportunities: List[Dict],
                                    current_portfolio_value: float,
                                    existing_positions: Optional[List[Dict]] = None) -> List[PositionSizingResult]:
        """Optimize allocation across multiple opportunities"""
        
        if existing_positions is None:
            existing_positions = []
        
        results = []
        updated_positions = existing_positions.copy()
        
        # Sort opportunities by expected Sharpe ratio
        opportunities.sort(key=lambda x: x.get('expected_return', 0) / max(x.get('volatility', 0.01), 0.01), reverse=True)
        
        for opp in opportunities:
            # Calculate position size for this opportunity
            result = self.calculate_optimal_position_size(
                symbol_pair=opp['symbol_pair'],
                expected_return=opp['expected_return'],
                volatility=opp['volatility'],
                current_portfolio_value=current_portfolio_value,
                existing_positions=updated_positions,
                market_regime_data=opp.get('regime_data'),
                correlation_data=opp.get('correlation_data')
            )
            
            results.append(result)
            
            # Update positions for next calculation
            if result.recommended_size > 0:
                updated_positions.append({
                    'symbol_pair': result.symbol_pair,
                    'size': result.recommended_size,
                    'correlation': opp.get('correlation_data', {}).get('correlation', 0.0)
                })
        
        return results
    
    def generate_position_sizing_report(self, 
                                      results: List[PositionSizingResult],
                                      current_portfolio_value: float) -> str:
        """Generate comprehensive position sizing report"""
        
        if not results:
            return "No position sizing results available."
        
        total_recommended = sum(r.recommended_size for r in results)
        total_risk = sum(r.risk_metrics['position_risk'] for r in results)
        
        report = f"""
=== ADVANCED POSITION SIZING REPORT ===
Portfolio Value: ${current_portfolio_value:,.0f}
Risk Level: {self.risk_level.value.title()}
Current Drawdown: {self.current_drawdown:.2%}

=== PORTFOLIO ALLOCATION ===
Total Recommended Allocation: ${total_recommended:,.0f} ({total_recommended/current_portfolio_value:.1%})
Total Portfolio Risk: {total_risk:.2%}
Number of Positions: {len([r for r in results if r.recommended_size > 0])}

=== INDIVIDUAL POSITIONS ===
"""
        
        for i, result in enumerate(results, 1):
            if result.recommended_size > 0:
                report += f"""
Position {i}: {result.symbol_pair}
  Recommended Size: ${result.recommended_size:,.0f} ({result.recommended_size/current_portfolio_value:.1%})
  Kelly Size: ${result.kelly_size:,.0f}
  Position Risk: {result.risk_metrics['position_risk']:.2%}
  Volatility Contribution: {result.risk_metrics['volatility_contribution']:.2%}
  Regime: {result.regime.value.replace('_', ' ').title()}
  Confidence: {result.confidence:.2f}
  Constraints Applied: {', '.join(result.constraints_applied) if result.constraints_applied else 'None'}
"""
        
        # Risk analysis
        regime_distribution = {}
        for result in results:
            regime = result.regime.value
            if regime not in regime_distribution:
                regime_distribution[regime] = 0
            regime_distribution[regime] += result.recommended_size
        
        report += "\n=== RISK ANALYSIS ===\n"
        for regime, allocation in regime_distribution.items():
            report += f"{regime.replace('_', ' ').title()}: ${allocation:,.0f} ({allocation/current_portfolio_value:.1%})\n"
        
        # Recommendations
        report += "\n=== RECOMMENDATIONS ===\n"
        if total_risk > self.constraints.max_portfolio_risk:
            report += f"⚠️  Portfolio risk ({total_risk:.2%}) exceeds maximum ({self.constraints.max_portfolio_risk:.2%})\n"
        
        if len([r for r in results if r.recommended_size > 0]) < self.constraints.min_diversification:
            report += f"⚠️  Insufficient diversification ({len([r for r in results if r.recommended_size > 0])} positions, minimum {self.constraints.min_diversification})\n"
        
        high_correlation_positions = [r for r in results if r.risk_metrics['correlation_exposure'] > 0.7]
        if high_correlation_positions:
            report += f"⚠️  High correlation exposure in {len(high_correlation_positions)} positions\n"
        
        return report

# Example usage and integration
if __name__ == "__main__":
    # Initialize position sizer
    sizer = AdvancedPositionSizer(
        base_capital=1000000,
        risk_level=RiskLevel.MODERATE
    )
    
    # Example opportunities
    opportunities = [
        {
            'symbol_pair': 'TSLA/NVDA',
            'expected_return': 0.02,
            'volatility': 0.25,
            'regime_data': {'stress_indicator': 0.1},
            'correlation_data': {'correlation': 0.3}
        },
        {
            'symbol_pair': 'QQQ/TQQQ',
            'expected_return': 0.015,
            'volatility': 0.18,
            'regime_data': {'stress_indicator': 0.0},
            'correlation_data': {'correlation': 0.1}
        },
        {
            'symbol_pair': 'TLT/TMF',
            'expected_return': 0.01,
            'volatility': 0.12,
            'regime_data': {'stress_indicator': -0.1},
            'correlation_data': {'correlation': -0.2}
        }
    ]
    
    # Optimize portfolio allocation
    results = sizer.optimize_portfolio_allocation(opportunities, 1000000)
    
    # Generate report
    report = sizer.generate_position_sizing_report(results, 1000000)
    print(report) 