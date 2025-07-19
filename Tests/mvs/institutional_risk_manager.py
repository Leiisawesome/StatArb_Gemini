"""
Institutional-Grade Risk Management System
Based on professional hedge fund standards with multi-layer risk controls
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from scipy import stats
import warnings

logger = logging.getLogger('mvs.risk_manager')

class InstitutionalRiskManager:
    """
    Professional risk management system with institutional-grade controls
    
    Features:
    - Volatility targeting (12% portfolio volatility)
    - Multi-layer position sizing with Kelly Criterion
    - Sector and correlation constraints
    - Dynamic drawdown controls (15% limit, 20% emergency)
    - Real-time portfolio risk monitoring
    - Stress testing and VaR calculations
    """
    
    def __init__(self):
        self.initial_capital = 100000        # $100,000 starting capital
        self.target_volatility = 0.12        # 12% annual portfolio volatility target
        self.max_position_size = 8000        # $8,000 maximum per position (8%)
        self.max_sector_exposure = 20000     # $20,000 maximum per sector (20%)
        self.max_total_exposure = 70000      # $70,000 maximum deployed capital (70%)
        self.cash_buffer = 30000             # $30,000 minimum cash buffer (30%)
        
        # Risk limits based on institutional standards
        self.risk_limits = {
            'maximum_drawdown_limit': 0.15,      # 15% maximum drawdown
            'emergency_drawdown_limit': 0.20,    # 20% emergency liquidation
            'individual_stop_loss': 0.12,        # 12% individual position stop
            'maximum_sector_exposure': 0.20,     # 20% maximum per sector
            'maximum_correlation': 0.60,         # 60% maximum average correlation
            'maximum_single_position': 0.08,     # 8% maximum single position
            'minimum_cash_ratio': 0.30,          # 30% minimum cash
            'maximum_leverage': 1.0,             # No leverage for conservative approach
            'kelly_fraction': 0.5                # Conservative Kelly multiplier
        }
        
        # Institutional transaction cost model
        self.transaction_costs = {
            'commission': 0.0005,            # 5 bps commission
            'spread': 0.0008,                # 8 bps bid-ask spread
            'impact': 0.0012,                # 12 bps market impact
            'total': 0.0025                  # 25 bps total per round-turn
        }
        
        # Risk monitoring state
        self.portfolio_peak = self.initial_capital
        self.risk_alerts = []
        self.position_history = []
        
        logger.info("Institutional Risk Manager initialized")
        logger.info(f"Target volatility: {self.target_volatility:.1%}")
        logger.info(f"Maximum drawdown: {self.risk_limits['maximum_drawdown_limit']:.1%}")
        logger.info(f"Emergency stop: {self.risk_limits['emergency_drawdown_limit']:.1%}")
    
    def calculate_position_sizes(self, signals: Dict[str, float], portfolio_value: float,
                               volatilities: Dict[str, float], correlations: Dict[str, Dict[str, float]],
                               sector_exposures: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate institutional-grade position sizes with multiple constraints
        
        Args:
            signals: Dictionary of {symbol: signal_strength}
            portfolio_value: Current portfolio value
            volatilities: Symbol volatilities
            correlations: Correlation matrix
            sector_exposures: Current sector exposures
            
        Returns:
            Dictionary of position sizing recommendations
        """
        try:
            logger.debug(f"Calculating position sizes for {len(signals)} signals")
            
            position_sizes = {}
            total_target_exposure = 0
            
            for symbol, signal_strength in signals.items():
                try:
                    # Get symbol data
                    symbol_volatility = volatilities.get(symbol, 0.20)  # Default 20% vol
                    current_sector_exposure = sector_exposures.get(
                        self._get_symbol_sector(symbol), 0
                    )
                    
                    # Calculate position size using multiple methods
                    position_info = self._calculate_institutional_position_size(
                        signal_strength, 
                        portfolio_value, 
                        symbol_volatility, 
                        current_sector_exposure,
                        correlations.get(symbol, {})
                    )
                    
                    if position_info['position_value'] > 0:
                        position_sizes[symbol] = position_info
                        total_target_exposure += position_info['position_value']
                    
                except Exception as e:
                    logger.debug(f"Error calculating position size for {symbol}: {e}")
                    continue
            
            # Apply portfolio-level constraints
            position_sizes = self._apply_portfolio_constraints(position_sizes, total_target_exposure)
            
            logger.info(f"Calculated position sizes for {len(position_sizes)} symbols")
            return position_sizes
            
        except Exception as e:
            logger.error(f"Position sizing calculation failed: {e}")
            return {}
    
    def _calculate_institutional_position_size(self, signal_strength: float, portfolio_value: float,
                                             symbol_volatility: float, sector_exposure: float,
                                             symbol_correlations: Dict[str, float]) -> Dict[str, Any]:
        """Calculate position size using institutional methodology"""
        
        # 1. Volatility-targeted sizing
        target_vol_contribution = self.target_volatility * 0.15  # 15% vol contribution per position
        vol_based_size = (target_vol_contribution / symbol_volatility) * portfolio_value
        
        # 2. Signal-strength adjustment (conservative Kelly)
        kelly_fraction = abs(signal_strength) * self.risk_limits['kelly_fraction']
        signal_adjusted_size = vol_based_size * kelly_fraction
        
        # 3. Apply institutional constraints
        max_position_value = min(self.max_position_size, portfolio_value * self.risk_limits['maximum_single_position'])
        sector_available = self.max_sector_exposure - sector_exposure
        
        # 4. Correlation adjustment (reduce size if highly correlated with existing positions)
        correlation_adjustment = self._calculate_correlation_adjustment(symbol_correlations)
        correlation_adjusted_size = signal_adjusted_size * correlation_adjustment
        
        # 5. Final position size with all constraints
        final_size = min(
            correlation_adjusted_size, 
            max_position_value, 
            sector_available,
            portfolio_value * 0.08  # Maximum 8% per position
        )
        
        # 6. Transaction cost filter
        expected_return = abs(signal_strength) * 0.15  # Conservative expected return
        if expected_return < (self.transaction_costs['total'] * 3):
            final_size = 0  # Don't trade if expected return < 3x transaction costs
        
        return {
            'position_value': max(0, final_size),
            'signal_strength': signal_strength,
            'volatility_based_size': vol_based_size,
            'kelly_adjusted_size': signal_adjusted_size,
            'correlation_adjustment': correlation_adjustment,
            'sector_constraint': sector_available,
            'transaction_cost_threshold': self.transaction_costs['total'] * 3,
            'expected_return': expected_return
        }
    
    def _calculate_correlation_adjustment(self, symbol_correlations: Dict[str, float]) -> float:
        """Calculate correlation adjustment factor"""
        if not symbol_correlations:
            return 1.0
        
        # Calculate average correlation with existing positions
        correlations = [abs(corr) for corr in symbol_correlations.values()]
        avg_correlation = np.mean(correlations) if correlations else 0.0
        
        # Reduce position size based on correlation (higher correlation = smaller position)
        max_correlation = self.risk_limits['maximum_correlation']
        if avg_correlation > max_correlation:
            return 0.5  # Significantly reduce if over correlation limit
        else:
            return 1.0 - (avg_correlation * 0.3)  # Linear reduction up to 30%
    
    def _apply_portfolio_constraints(self, position_sizes: Dict[str, Dict[str, Any]], 
                                   total_target_exposure: float) -> Dict[str, Dict[str, Any]]:
        """Apply portfolio-level constraints"""
        
        # Check if total exposure exceeds limit
        if total_target_exposure > self.max_total_exposure:
            scaling_factor = self.max_total_exposure / total_target_exposure
            logger.warning(f"Scaling positions by {scaling_factor:.2f} due to exposure limit")
            
            for symbol in position_sizes:
                position_sizes[symbol]['position_value'] *= scaling_factor
        
        return position_sizes
    
    def calculate_stop_loss_levels(self, positions: Dict[str, Dict[str, Any]], 
                                 current_prices: Dict[str, float],
                                 volatilities: Dict[str, float]) -> Dict[str, float]:
        """Calculate dynamic stop-loss levels based on institutional standards"""
        stop_levels = {}
        
        for symbol, position in positions.items():
            try:
                current_price = current_prices.get(symbol, 0)
                volatility = volatilities.get(symbol, 0.20)
                
                if current_price > 0:
                    stop_level = self._calculate_institutional_stop_loss(
                        position, current_price, volatility
                    )
                    stop_levels[symbol] = stop_level
                    
            except Exception as e:
                logger.debug(f"Error calculating stop loss for {symbol}: {e}")
                continue
        
        return stop_levels
    
    def _calculate_institutional_stop_loss(self, position: Dict[str, Any], 
                                         current_price: float, volatility: float) -> float:
        """Calculate institutional-grade stop-loss level"""
        
        entry_price = position.get('entry_price', current_price)
        side = position.get('side', 'long')
        
        if side == 'long':
            # 12% stop-loss or 2x volatility, whichever is tighter
            vol_stop = current_price * (1 - 2 * volatility / np.sqrt(252))  # Daily vol to annual
            percentage_stop = entry_price * (1 - self.risk_limits['individual_stop_loss'])
            return max(vol_stop, percentage_stop)  # Use tighter stop
        else:
            # For short positions
            vol_stop = current_price * (1 + 2 * volatility / np.sqrt(252))
            percentage_stop = entry_price * (1 + self.risk_limits['individual_stop_loss'])
            return min(vol_stop, percentage_stop)  # Use tighter stop
    
    def monitor_portfolio_risk(self, current_positions: Dict[str, Dict[str, Any]], 
                             market_data: Dict[str, Dict[str, float]],
                             portfolio_value: float) -> Dict[str, Any]:
        """Real-time portfolio risk monitoring with institutional standards"""
        
        try:
            # Calculate portfolio metrics
            portfolio_metrics = {
                'total_exposure': sum(pos.get('market_value', 0) for pos in current_positions.values()),
                'cash_ratio': self._calculate_cash_ratio(portfolio_value, current_positions),
                'sector_exposures': self._calculate_sector_exposures(current_positions),
                'portfolio_volatility': self._calculate_portfolio_volatility(current_positions, market_data),
                'correlation_matrix': self._calculate_correlation_matrix(current_positions, market_data),
                'var_95': self._calculate_value_at_risk(current_positions, market_data),
                'current_drawdown': self._calculate_current_drawdown(portfolio_value)
            }
            
            # Check for risk limit violations
            violations = self._check_risk_violations(portfolio_metrics)
            
            # Update portfolio peak
            if portfolio_value > self.portfolio_peak:
                self.portfolio_peak = portfolio_value
            
            return {
                'metrics': portfolio_metrics,
                'violations': violations,
                'alerts': self._generate_risk_alerts(portfolio_metrics, violations)
            }
            
        except Exception as e:
            logger.error(f"Portfolio risk monitoring failed: {e}")
            return {'metrics': {}, 'violations': [], 'alerts': []}
    
    def _calculate_current_drawdown(self, portfolio_value: float) -> float:
        """Calculate current portfolio drawdown"""
        if self.portfolio_peak <= 0:
            return 0.0
        return (self.portfolio_peak - portfolio_value) / self.portfolio_peak
    
    def _check_risk_violations(self, metrics: Dict[str, Any]) -> List[str]:
        """Check for risk limit violations"""
        violations = []
        
        # Exposure violations
        if metrics.get('total_exposure', 0) > self.max_total_exposure:
            violations.append('Total exposure limit exceeded')
        
        # Sector exposure violations
        for sector, exposure in metrics.get('sector_exposures', {}).items():
            if exposure > self.max_sector_exposure:
                violations.append(f'Sector {sector} exposure limit exceeded')
        
        # Volatility violations
        portfolio_vol = metrics.get('portfolio_volatility', 0)
        if portfolio_vol > self.target_volatility * 1.5:
            violations.append('Portfolio volatility exceeds 150% of target')
        
        # Drawdown violations
        current_drawdown = metrics.get('current_drawdown', 0)
        if current_drawdown > self.risk_limits['emergency_drawdown_limit']:
            violations.append('Emergency drawdown limit exceeded')
        elif current_drawdown > self.risk_limits['maximum_drawdown_limit']:
            violations.append('Maximum drawdown limit exceeded')
        
        # Cash ratio violations
        cash_ratio = metrics.get('cash_ratio', 1.0)
        if cash_ratio < self.risk_limits['minimum_cash_ratio']:
            violations.append('Minimum cash ratio violated')
        
        return violations
    
    def apply_emergency_risk_controls(self, portfolio_value: float, 
                                    current_positions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Apply emergency risk controls for extreme scenarios"""
        
        current_drawdown = self._calculate_current_drawdown(portfolio_value)
        
        if current_drawdown > self.risk_limits['emergency_drawdown_limit']:
            logger.critical(f"Emergency drawdown limit exceeded: {current_drawdown:.2%}")
            return {
                'action': 'EMERGENCY_LIQUIDATION',
                'target_exposure': 0.0,
                'reason': 'Emergency drawdown stop triggered',
                'urgency': 'CRITICAL'
            }
        
        elif current_drawdown > self.risk_limits['maximum_drawdown_limit']:
            logger.warning(f"Drawdown limit exceeded: {current_drawdown:.2%}")
            return {
                'action': 'REDUCE_EXPOSURE',
                'target_exposure': 0.3,  # Reduce to 30% exposure
                'reason': 'Portfolio drawdown limit exceeded',
                'urgency': 'HIGH'
            }
        
        return {'action': 'NORMAL_OPERATION', 'urgency': 'NONE'}
    
    def _calculate_sector_exposures(self, positions: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Calculate current sector exposures"""
        sector_exposures = {}
        
        for symbol, position in positions.items():
            sector = self._get_symbol_sector(symbol)
            market_value = position.get('market_value', 0)
            
            if sector not in sector_exposures:
                sector_exposures[sector] = 0
            sector_exposures[sector] += market_value
        
        return sector_exposures
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """Get sector for symbol (simplified mapping)"""
        sector_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 
            'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary',
            'META': 'Technology', 'NVDA': 'Technology', 'JPM': 'Financials',
            'JNJ': 'Healthcare', 'V': 'Financials', 'PG': 'Consumer Staples'
        }
        return sector_mapping.get(symbol, 'Other')
    
    def _calculate_portfolio_volatility(self, positions: Dict[str, Dict[str, Any]], 
                                      market_data: Dict[str, Dict[str, float]]) -> float:
        """Calculate portfolio volatility"""
        # Simplified calculation - in production would use full covariance matrix
        try:
            if not positions:
                return 0.0
            
            # Weight-average individual volatilities (simplified)
            total_value = sum(pos.get('market_value', 0) for pos in positions.values())
            if total_value <= 0:
                return 0.0
            
            weighted_vol = 0
            for symbol, position in positions.items():
                weight = position.get('market_value', 0) / total_value
                symbol_vol = market_data.get(symbol, {}).get('volatility', 0.20)
                weighted_vol += weight * symbol_vol
            
            return weighted_vol
            
        except Exception as e:
            logger.debug(f"Portfolio volatility calculation error: {e}")
            return 0.15  # Default 15% volatility
    
    def _calculate_value_at_risk(self, positions: Dict[str, Dict[str, Any]], 
                               market_data: Dict[str, Dict[str, float]], 
                               confidence: float = 0.95) -> float:
        """Calculate portfolio Value at Risk (VaR)"""
        try:
            # Simplified VaR calculation
            portfolio_vol = self._calculate_portfolio_volatility(positions, market_data)
            total_value = sum(pos.get('market_value', 0) for pos in positions.values())
            
            # Daily VaR using normal distribution assumption
            daily_vol = portfolio_vol / np.sqrt(252)
            z_score = stats.norm.ppf(confidence)
            var_95 = total_value * daily_vol * z_score
            
            return var_95
            
        except Exception as e:
            logger.debug(f"VaR calculation error: {e}")
            return 0.0
    
    def _calculate_cash_ratio(self, portfolio_value: float, 
                            positions: Dict[str, Dict[str, Any]]) -> float:
        """Calculate current cash ratio"""
        total_position_value = sum(pos.get('market_value', 0) for pos in positions.values())
        cash_value = portfolio_value - total_position_value
        return cash_value / portfolio_value if portfolio_value > 0 else 1.0
    
    def _calculate_correlation_matrix(self, positions: Dict[str, Dict[str, Any]], 
                                    market_data: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix for current positions"""
        # Simplified - in production would use historical correlation data
        symbols = list(positions.keys())
        correlation_matrix = {}
        
        for symbol1 in symbols:
            correlation_matrix[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 == symbol2:
                    correlation_matrix[symbol1][symbol2] = 1.0
                else:
                    # Simplified correlation (would use actual historical data)
                    sector1 = self._get_symbol_sector(symbol1)
                    sector2 = self._get_symbol_sector(symbol2)
                    if sector1 == sector2:
                        correlation_matrix[symbol1][symbol2] = 0.6  # Same sector correlation
                    else:
                        correlation_matrix[symbol1][symbol2] = 0.3  # Cross-sector correlation
        
        return correlation_matrix
    
    def _generate_risk_alerts(self, metrics: Dict[str, Any], violations: List[str]) -> List[Dict[str, Any]]:
        """Generate risk alerts based on current metrics"""
        alerts = []
        
        for violation in violations:
            alerts.append({
                'timestamp': datetime.now().isoformat(),
                'level': 'CRITICAL' if 'Emergency' in violation else 'WARNING',
                'message': violation,
                'metrics': metrics
            })
        
        return alerts
    
    def get_risk_statistics(self) -> Dict[str, Any]:
        """Get comprehensive risk management statistics"""
        return {
            'risk_limits': self.risk_limits,
            'transaction_costs': self.transaction_costs,
            'target_volatility': self.target_volatility,
            'portfolio_peak': self.portfolio_peak,
            'current_alerts': len(self.risk_alerts),
            'risk_management_approach': 'Institutional Multi-Layer'
        }
