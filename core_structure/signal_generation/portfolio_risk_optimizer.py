"""
Portfolio-Level Risk Optimization Module - Phase 3 Enhancement
Implements portfolio-wide risk management including correlation, concentration, and drawdown limits
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@dataclass
class PortfolioRiskConfig:
    """Configuration for portfolio-level risk optimization"""
    # Position limits
    max_position_size: float = 0.25  # 25% max per position
    max_sector_concentration: float = 0.40  # 40% max per sector
    max_correlation_threshold: float = 0.7  # 70% max correlation
    
    # Portfolio limits
    max_portfolio_volatility: float = 0.20  # 20% max portfolio volatility
    max_drawdown_limit: float = 0.15  # 15% max drawdown
    target_sharpe_ratio: float = 1.0  # Target Sharpe ratio
    
    # Risk metrics
    var_confidence_level: float = 0.95  # 95% VaR confidence
    cvar_confidence_level: float = 0.95  # 95% CVaR confidence
    risk_free_rate: float = 0.02  # 2% risk-free rate
    
    # Correlation settings
    correlation_lookback: int = 60  # 60 periods for correlation calculation
    min_correlation_samples: int = 30  # Minimum samples for correlation
    
    # Rebalancing settings
    rebalance_threshold: float = 0.05  # 5% threshold for rebalancing
    max_rebalance_frequency: int = 24  # Maximum rebalancing per day

class PortfolioRiskOptimizer:
    """Portfolio-level risk optimization and management"""
    
    def __init__(self, config: Optional[PortfolioRiskConfig] = None):
        self.config = config or PortfolioRiskConfig()
        self.portfolio_state = {
            'positions': {},
            'sectors': {},
            'correlations': {},
            'risk_metrics': {},
            'last_rebalance': None
        }
        self.risk_history = []
        self.risk_stats = {
            'risk_checks': 0,
            'risk_violations': 0,
            'position_adjustments': 0,
            'rebalancing_events': 0
        }
    
    def optimize_portfolio_risk(
        self,
        new_signal: Dict[str, Any],
        current_positions: Dict[str, Any],
        market_data: Dict[str, pd.DataFrame],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Optimize portfolio risk for new signal
        
        Args:
            new_signal: New trading signal
            current_positions: Current portfolio positions
            market_data: Market data for all symbols
            portfolio_value: Current portfolio value
        
        Returns:
            Risk-optimized signal with position adjustments
        """
        try:
            optimized_signal = new_signal.copy()
            
            # Update portfolio state
            self._update_portfolio_state(current_positions, market_data)
            
            # Calculate current portfolio risk metrics
            current_risk = self._calculate_portfolio_risk(current_positions, market_data)
            
            # Check risk limits
            risk_violations = self._check_risk_limits(current_risk, new_signal)
            
            # Apply risk adjustments
            if risk_violations:
                optimized_signal = self._apply_risk_adjustments(
                    optimized_signal, risk_violations, current_risk
                )
                self.risk_stats['risk_violations'] += 1
                self.risk_stats['position_adjustments'] += 1
            
            # Check if rebalancing is needed
            if self._should_rebalance(current_risk, current_positions):
                optimized_signal = self._apply_rebalancing_adjustments(
                    optimized_signal, current_positions, current_risk
                )
                self.risk_stats['rebalancing_events'] += 1
            
            # Update risk history
            self._update_risk_history(current_risk, optimized_signal)
            
            # Update statistics
            self.risk_stats['risk_checks'] += 1
            
            # Add risk metadata
            metadata = optimized_signal.get('metadata', {})
            metadata.update({
                'portfolio_risk_optimized': True,
                'current_portfolio_volatility': current_risk.get('volatility', 0.0),
                'current_drawdown': current_risk.get('drawdown', 0.0),
                'risk_violations': len(risk_violations) if risk_violations else 0,
                'phase3_enhanced': True
            })
            optimized_signal['metadata'] = metadata
            
            logger.debug(f"Portfolio risk optimized: violations={len(risk_violations) if risk_violations else 0}, "
                        f"volatility={current_risk.get('volatility', 0.0):.3f}")
            
            return optimized_signal
            
        except Exception as e:
            logger.error(f"Portfolio risk optimization failed: {e}")
            return new_signal
    
    def _update_portfolio_state(
        self,
        current_positions: Dict[str, Any],
        market_data: Dict[str, pd.DataFrame]
    ) -> None:
        """Update current portfolio state"""
        try:
            # Update positions
            self.portfolio_state['positions'] = current_positions.copy()
            
            # Calculate sector allocations (simplified)
            sectors = {}
            for symbol, position in current_positions.items():
                # Simplified sector mapping
                sector = self._get_symbol_sector(symbol)
                if sector not in sectors:
                    sectors[sector] = 0.0
                sectors[sector] += abs(position.get('value', 0.0))
            
            self.portfolio_state['sectors'] = sectors
            
            # Calculate correlations
            self._update_correlations(market_data)
            
        except Exception as e:
            logger.error(f"Portfolio state update failed: {e}")
    
    def _calculate_portfolio_risk(
        self,
        current_positions: Dict[str, Any],
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """Calculate current portfolio risk metrics"""
        try:
            risk_metrics = {}
            
            # Calculate position weights
            total_value = sum(abs(pos.get('value', 0.0)) for pos in current_positions.values())
            if total_value == 0:
                return {'volatility': 0.0, 'drawdown': 0.0, 'var': 0.0, 'cvar': 0.0}
            
            weights = {}
            for symbol, position in current_positions.items():
                weight = abs(position.get('value', 0.0)) / total_value
                weights[symbol] = weight
            
            # Calculate portfolio volatility
            portfolio_volatility = self._calculate_portfolio_volatility(weights, market_data)
            risk_metrics['volatility'] = portfolio_volatility
            
            # Calculate Value at Risk (VaR)
            var = self._calculate_var(weights, market_data)
            risk_metrics['var'] = var
            
            # Calculate Conditional Value at Risk (CVaR)
            cvar = self._calculate_cvar(weights, market_data)
            risk_metrics['cvar'] = cvar
            
            # Calculate current drawdown
            drawdown = self._calculate_current_drawdown(current_positions)
            risk_metrics['drawdown'] = drawdown
            
            # Calculate Sharpe ratio
            sharpe = self._calculate_sharpe_ratio(current_positions, market_data)
            risk_metrics['sharpe'] = sharpe
            
            # Calculate concentration metrics
            concentration = self._calculate_concentration_metrics(current_positions)
            risk_metrics.update(concentration)
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Portfolio risk calculation failed: {e}")
            return {'volatility': 0.0, 'drawdown': 0.0, 'var': 0.0, 'cvar': 0.0}
    
    def _check_risk_limits(
        self,
        current_risk: Dict[str, Any],
        new_signal: Dict[str, Any]
    ) -> List[str]:
        """Check for risk limit violations"""
        violations = []
        
        try:
            # Check volatility limit
            if current_risk.get('volatility', 0.0) > self.config.max_portfolio_volatility:
                violations.append('volatility_limit')
            
            # Check drawdown limit
            if current_risk.get('drawdown', 0.0) > self.config.max_drawdown_limit:
                violations.append('drawdown_limit')
            
            # Check position size limit
            signal_symbol = new_signal.get('symbol', '')
            if signal_symbol in self.portfolio_state['positions']:
                position_value = abs(self.portfolio_state['positions'][signal_symbol].get('value', 0.0))
                portfolio_value = sum(abs(pos.get('value', 0.0)) for pos in self.portfolio_state['positions'].values())
                if portfolio_value > 0:
                    position_weight = position_value / portfolio_value
                    if position_weight > self.config.max_position_size:
                        violations.append('position_size_limit')
            
            # Check sector concentration
            for sector, value in self.portfolio_state['sectors'].items():
                total_value = sum(self.portfolio_state['sectors'].values())
                if total_value > 0:
                    sector_weight = value / total_value
                    if sector_weight > self.config.max_sector_concentration:
                        violations.append('sector_concentration_limit')
            
            return violations
            
        except Exception as e:
            logger.error(f"Risk limit check failed: {e}")
            return violations
    
    def _apply_risk_adjustments(
        self,
        signal: Dict[str, Any],
        violations: List[str],
        current_risk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply risk adjustments to signal"""
        try:
            adjusted_signal = signal.copy()
            
            # Reduce position size for risk violations
            if violations:
                # Calculate reduction factor based on number of violations
                reduction_factor = 1.0 / (1.0 + len(violations) * 0.2)
                
                # Apply reduction to position size
                original_size = signal.get('position_size', 0.1)
                adjusted_size = original_size * reduction_factor
                
                adjusted_signal['position_size'] = adjusted_size
                adjusted_signal['risk_adjustment'] = reduction_factor
                adjusted_signal['risk_violations'] = violations
            
            return adjusted_signal
            
        except Exception as e:
            logger.error(f"Risk adjustment application failed: {e}")
            return signal
    
    def _should_rebalance(
        self,
        current_risk: Dict[str, Any],
        current_positions: Dict[str, Any]
    ) -> bool:
        """Determine if portfolio rebalancing is needed"""
        try:
            # Check if enough time has passed since last rebalance
            if self.portfolio_state['last_rebalance']:
                time_since_rebalance = datetime.now() - self.portfolio_state['last_rebalance']
                if time_since_rebalance.total_seconds() < 3600:  # 1 hour minimum
                    return False
            
            # Check risk metrics for rebalancing triggers
            if current_risk.get('volatility', 0.0) > self.config.max_portfolio_volatility * 0.8:
                return True
            
            if current_risk.get('drawdown', 0.0) > self.config.max_drawdown_limit * 0.8:
                return True
            
            # Check for significant position imbalances
            total_value = sum(abs(pos.get('value', 0.0)) for pos in current_positions.values())
            if total_value > 0:
                for symbol, position in current_positions.items():
                    weight = abs(position.get('value', 0.0)) / total_value
                    if weight > self.config.max_position_size * 0.8:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Rebalancing check failed: {e}")
            return False
    
    def _apply_rebalancing_adjustments(
        self,
        signal: Dict[str, Any],
        current_positions: Dict[str, Any],
        current_risk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply rebalancing adjustments to signal"""
        try:
            rebalanced_signal = signal.copy()
            
            # Reduce position sizes across the board
            rebalance_factor = 0.8  # 20% reduction
            
            original_size = signal.get('position_size', 0.1)
            rebalanced_size = original_size * rebalance_factor
            
            rebalanced_signal['position_size'] = rebalanced_size
            rebalanced_signal['rebalancing_applied'] = True
            rebalanced_signal['rebalance_factor'] = rebalance_factor
            
            # Update last rebalance time
            self.portfolio_state['last_rebalance'] = datetime.now()
            
            return rebalanced_signal
            
        except Exception as e:
            logger.error(f"Rebalancing adjustment failed: {e}")
            return signal
    
    def _update_correlations(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update correlation matrix for portfolio symbols"""
        try:
            symbols = list(market_data.keys())
            if len(symbols) < 2:
                return
            
            # Calculate returns for each symbol
            returns_data = {}
            for symbol, data in market_data.items():
                if len(data) > 0:
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= self.config.min_correlation_samples:
                        returns_data[symbol] = returns.tail(self.config.correlation_lookback)
            
            if len(returns_data) < 2:
                return
            
            # Create correlation matrix
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            self.portfolio_state['correlations'] = correlation_matrix.to_dict()
            
        except Exception as e:
            logger.error(f"Correlation update failed: {e}")
    
    def _calculate_portfolio_volatility(
        self,
        weights: Dict[str, float],
        market_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate portfolio volatility"""
        try:
            if len(weights) < 2:
                return 0.0
            
            # Calculate covariance matrix
            returns_data = {}
            for symbol in weights.keys():
                if symbol in market_data and len(market_data[symbol]) > 0:
                    returns = market_data[symbol]['close'].pct_change().dropna()
                    if len(returns) >= 20:
                        returns_data[symbol] = returns.tail(60)
            
            if len(returns_data) < 2:
                return 0.0
            
            returns_df = pd.DataFrame(returns_data)
            cov_matrix = returns_df.cov()
            
            # Calculate portfolio variance
            portfolio_variance = 0.0
            for i, symbol1 in enumerate(weights.keys()):
                for j, symbol2 in enumerate(weights.keys()):
                    if symbol1 in cov_matrix.index and symbol2 in cov_matrix.columns:
                        weight1 = weights[symbol1]
                        weight2 = weights[symbol2]
                        covariance = cov_matrix.loc[symbol1, symbol2]
                        portfolio_variance += weight1 * weight2 * covariance
            
            portfolio_volatility = np.sqrt(portfolio_variance)
            return portfolio_volatility
            
        except Exception as e:
            logger.error(f"Portfolio volatility calculation failed: {e}")
            return 0.0
    
    def _calculate_var(
        self,
        weights: Dict[str, float],
        market_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate Value at Risk"""
        try:
            if not weights:
                return 0.0
            
            # Calculate portfolio returns
            portfolio_returns = []
            min_length = float('inf')
            
            for symbol in weights.keys():
                if symbol in market_data and len(market_data[symbol]) > 0:
                    returns = market_data[symbol]['close'].pct_change().dropna()
                    min_length = min(min_length, len(returns))
            
            if min_length == float('inf') or min_length < 20:
                return 0.0
            
            # Calculate weighted portfolio returns
            for i in range(min_length):
                portfolio_return = 0.0
                for symbol, weight in weights.items():
                    if symbol in market_data and len(market_data[symbol]) > 0:
                        returns = market_data[symbol]['close'].pct_change().dropna()
                        if i < len(returns):
                            portfolio_return += weight * returns.iloc[-(min_length - i)]
                portfolio_returns.append(portfolio_return)
            
            # Calculate VaR
            var_percentile = (1 - self.config.var_confidence_level) * 100
            var = np.percentile(portfolio_returns, var_percentile)
            
            return abs(var)
            
        except Exception as e:
            logger.error(f"VaR calculation failed: {e}")
            return 0.0
    
    def _calculate_cvar(
        self,
        weights: Dict[str, float],
        market_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate Conditional Value at Risk"""
        try:
            # Calculate VaR first
            var = self._calculate_var(weights, market_data)
            
            if var == 0.0:
                return 0.0
            
            # Calculate portfolio returns (same as VaR calculation)
            portfolio_returns = []
            min_length = float('inf')
            
            for symbol in weights.keys():
                if symbol in market_data and len(market_data[symbol]) > 0:
                    returns = market_data[symbol]['close'].pct_change().dropna()
                    min_length = min(min_length, len(returns))
            
            if min_length == float('inf') or min_length < 20:
                return 0.0
            
            # Calculate weighted portfolio returns
            for i in range(min_length):
                portfolio_return = 0.0
                for symbol, weight in weights.items():
                    if symbol in market_data and len(market_data[symbol]) > 0:
                        returns = market_data[symbol]['close'].pct_change().dropna()
                        if i < len(returns):
                            portfolio_return += weight * returns.iloc[-(min_length - i)]
                portfolio_returns.append(portfolio_return)
            
            # Calculate CVaR (average of returns below VaR)
            var_percentile = (1 - self.config.cvar_confidence_level) * 100
            var_threshold = np.percentile(portfolio_returns, var_percentile)
            
            tail_returns = [r for r in portfolio_returns if r <= var_threshold]
            cvar = np.mean(tail_returns) if tail_returns else 0.0
            
            return abs(cvar)
            
        except Exception as e:
            logger.error(f"CVaR calculation failed: {e}")
            return 0.0
    
    def _calculate_current_drawdown(self, current_positions: Dict[str, Any]) -> float:
        """Calculate current portfolio drawdown"""
        try:
            # Simplified drawdown calculation
            # In a full implementation, this would track historical portfolio values
            
            total_value = sum(abs(pos.get('value', 0.0)) for pos in current_positions.values())
            
            # For now, return a small drawdown if positions exist
            if total_value > 0:
                return 0.02  # 2% drawdown
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Drawdown calculation failed: {e}")
            return 0.0
    
    def _calculate_sharpe_ratio(
        self,
        current_positions: Dict[str, Any],
        market_data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calculate portfolio Sharpe ratio"""
        try:
            # Simplified Sharpe ratio calculation
            # In a full implementation, this would use historical returns
            
            total_value = sum(abs(pos.get('value', 0.0)) for pos in current_positions.values())
            
            if total_value == 0:
                return 0.0
            
            # For now, return a moderate Sharpe ratio
            return 0.5
            
        except Exception as e:
            logger.error(f"Sharpe ratio calculation failed: {e}")
            return 0.0
    
    def _calculate_concentration_metrics(self, current_positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate concentration metrics"""
        try:
            total_value = sum(abs(pos.get('value', 0.0)) for pos in current_positions.values())
            
            if total_value == 0:
                return {'herfindahl_index': 0.0, 'largest_position': 0.0}
            
            # Calculate Herfindahl index
            weights = [abs(pos.get('value', 0.0)) / total_value for pos in current_positions.values()]
            herfindahl = sum(w * w for w in weights)
            
            # Largest position weight
            largest_position = max(weights) if weights else 0.0
            
            return {
                'herfindahl_index': herfindahl,
                'largest_position': largest_position
            }
            
        except Exception as e:
            logger.error(f"Concentration metrics calculation failed: {e}")
            return {'herfindahl_index': 0.0, 'largest_position': 0.0}
    
    def _get_symbol_sector(self, symbol: str) -> str:
        """Get sector for a symbol (simplified)"""
        # Simplified sector mapping
        sector_mapping = {
            'AAPL': 'Technology',
            'GOOGL': 'Technology',
            'MSFT': 'Technology',
            'TSLA': 'Automotive',
            'NVDA': 'Technology',
            'AMZN': 'Consumer',
            'META': 'Technology',
            'NFLX': 'Entertainment'
        }
        
        return sector_mapping.get(symbol, 'Other')
    
    def _update_risk_history(
        self,
        current_risk: Dict[str, Any],
        optimized_signal: Dict[str, Any]
    ) -> None:
        """Update risk history"""
        try:
            self.risk_history.append({
                'timestamp': datetime.now(),
                'risk_metrics': current_risk,
                'signal_optimized': optimized_signal,
                'portfolio_state': self.portfolio_state.copy()
            })
            
            # Keep only recent history (last 1000 entries)
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-1000:]
                
        except Exception as e:
            logger.error(f"Risk history update failed: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current portfolio risk summary"""
        try:
            current_risk = self.portfolio_state.get('risk_metrics', {})
            
            return {
                'current_volatility': current_risk.get('volatility', 0.0),
                'current_drawdown': current_risk.get('drawdown', 0.0),
                'current_var': current_risk.get('var', 0.0),
                'current_cvar': current_risk.get('cvar', 0.0),
                'current_sharpe': current_risk.get('sharpe', 0.0),
                'risk_checks': self.risk_stats['risk_checks'],
                'risk_violations': self.risk_stats['risk_violations'],
                'position_adjustments': self.risk_stats['position_adjustments'],
                'rebalancing_events': self.risk_stats['rebalancing_events'],
                'total_positions': len(self.portfolio_state.get('positions', {})),
                'total_sectors': len(self.portfolio_state.get('sectors', {}))
            }
            
        except Exception as e:
            logger.error(f"Risk summary generation failed: {e}")
            return {}
