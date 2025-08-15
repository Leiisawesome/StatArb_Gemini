"""
Dynamic Portfolio Management - Template-Aware Adaptive Portfolio Management
===========================================================================

Template-inheritance-aware adaptive portfolio management that dynamically adjusts
allocation, rebalancing, and correlation limits based on performance and market conditions.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager


class PortfolioAdaptationMode(Enum):
    """Portfolio adaptation modes"""
    CONSERVATIVE = "conservative"        # Focus on capital preservation
    BALANCED = "balanced"               # Balance growth and risk
    AGGRESSIVE = "aggressive"           # Focus on growth
    CORRELATION_BASED = "correlation_based"  # Adapt based on correlations
    PERFORMANCE_BASED = "performance_based"  # Adapt based on performance


class RebalancingFrequency(Enum):
    """Portfolio rebalancing frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    DYNAMIC = "dynamic"  # Frequency adapts to conditions


@dataclass
class PortfolioParameters:
    """Portfolio management parameters"""
    cash_reserve: float = 0.1               # 10% cash reserve
    max_position_concentration: float = 0.2  # 20% max single position
    target_num_positions: int = 10         # Target number of positions
    rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.WEEKLY
    rebalancing_threshold: float = 0.05     # 5% deviation triggers rebalancing
    max_correlation: float = 0.7            # 70% max correlation between positions
    min_diversification_score: float = 0.6  # Minimum diversification score
    cash_management_strategy: str = "adaptive"  # How to manage cash
    position_sizing_method: str = "equal_weight"  # Position sizing approach


@dataclass
class PortfolioMetrics:
    """Portfolio performance and risk metrics"""
    total_value: float = 0.0
    cash_balance: float = 0.0
    invested_capital: float = 0.0
    number_of_positions: int = 0
    largest_position_pct: float = 0.0
    avg_correlation: float = 0.0
    diversification_score: float = 0.0
    portfolio_beta: float = 1.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    daily_return: float = 0.0
    cumulative_return: float = 0.0


@dataclass
class PortfolioConfig:
    """Configuration for dynamic portfolio management"""
    # Adaptation settings
    adaptation_mode: PortfolioAdaptationMode = PortfolioAdaptationMode.BALANCED
    adaptation_frequency: timedelta = timedelta(hours=4)
    min_confidence_threshold: float = 0.65
    
    # Template category portfolio rules
    category_portfolio_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_portfolio_adjustment': 0.1,    # 10% max adjustment
            'diversification_priority': 0.9,    # High diversification priority
            'rebalancing_aggressiveness': 0.4    # Conservative rebalancing
        },
        TemplateCategory.SPECIFIC: {
            'max_portfolio_adjustment': 0.2,    # 20% max adjustment
            'diversification_priority': 0.7,    # Medium diversification priority
            'rebalancing_aggressiveness': 0.7    # Moderate rebalancing
        },
        TemplateCategory.COMPOSITE: {
            'max_portfolio_adjustment': 0.3,    # 30% max adjustment
            'diversification_priority': 0.5,    # Lower diversification priority
            'rebalancing_aggressiveness': 1.0    # Aggressive rebalancing
        }
    })
    
    # Portfolio adaptation triggers
    adaptation_triggers: Dict[str, float] = field(default_factory=lambda: {
        'correlation_spike_threshold': 0.8,
        'concentration_warning_threshold': 0.25,
        'cash_reserve_low_threshold': 0.05,
        'cash_reserve_high_threshold': 0.20,
        'performance_degradation_threshold': -0.05
    })


@dataclass
class PortfolioAdaptationResult:
    """Result of portfolio management adaptation"""
    success: bool
    adapted_parameters: PortfolioParameters
    rebalancing_actions: List[Dict[str, Any]]
    adaptation_magnitude: float
    risk_improvement_estimate: float
    confidence_score: float
    adaptation_reasons: List[str]
    template_compliance: bool
    execution_time_ms: float
    error_message: Optional[str] = None


class DynamicPortfolioManagement:
    """
    Template-inheritance-aware adaptive portfolio management
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[PortfolioConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or PortfolioConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Portfolio management state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.base_portfolio_parameters = PortfolioParameters()
        self.adapted_portfolio_parameters = PortfolioParameters()
        
        # Portfolio tracking
        self.current_positions: Dict[str, Dict[str, Any]] = {}
        self.historical_positions: deque = deque(maxlen=100)
        self.portfolio_metrics_history: deque = deque(maxlen=100)
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.rebalancing_history: List[Dict[str, Any]] = []
        
        # Adaptation tracking
        self.adaptation_history: List[PortfolioAdaptationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        self.last_rebalancing_time: Optional[datetime] = None
        
        # Portfolio state
        self.current_portfolio_value: float = 100000.0
        self.cash_balance: float = 10000.0
        self.invested_capital: float = 90000.0
        
        self.logger.info("Dynamic Portfolio Management initialized")
    
    def initialize_for_template(self, template_id: str, initial_portfolio_value: float = 100000.0):
        """Initialize portfolio management for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            self.current_portfolio_value = initial_portfolio_value
            
            # Extract portfolio parameters from template
            self.base_portfolio_parameters = self._extract_template_portfolio_parameters(template_id)
            self.adapted_portfolio_parameters = PortfolioParameters(
                cash_reserve=self.base_portfolio_parameters.cash_reserve,
                max_position_concentration=self.base_portfolio_parameters.max_position_concentration,
                target_num_positions=self.base_portfolio_parameters.target_num_positions,
                rebalancing_frequency=self.base_portfolio_parameters.rebalancing_frequency,
                rebalancing_threshold=self.base_portfolio_parameters.rebalancing_threshold,
                max_correlation=self.base_portfolio_parameters.max_correlation,
                min_diversification_score=self.base_portfolio_parameters.min_diversification_score,
                cash_management_strategy=self.base_portfolio_parameters.cash_management_strategy,
                position_sizing_method=self.base_portfolio_parameters.position_sizing_method
            )
            
            # Initialize cash balance based on reserve ratio
            self.cash_balance = initial_portfolio_value * self.adapted_portfolio_parameters.cash_reserve
            self.invested_capital = initial_portfolio_value - self.cash_balance
            
            # Reset state
            self.current_positions.clear()
            self.historical_positions.clear()
            self.portfolio_metrics_history.clear()
            self.rebalancing_history.clear()
            self.adaptation_history.clear()
            self.correlation_matrix = None
            self.last_adaptation_time = None
            self.last_rebalancing_time = None
            
            self.logger.info(f"Portfolio management initialized for template {template_id} (category: {self.current_template_category.value})")
            self.logger.info(f"Initial portfolio: ${initial_portfolio_value:,.2f}, Cash: ${self.cash_balance:,.2f}, Invested: ${self.invested_capital:,.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize portfolio management: {e}")
            raise
    
    async def update_adaptive_portfolio(self, 
                                      execution_results: List[Dict[str, Any]], 
                                      market_data: Dict[str, Any]) -> Tuple[PortfolioMetrics, Dict[str, Any]]:
        """
        Update portfolio with adaptive management
        """
        try:
            if not self.current_template_id:
                raise ValueError("Portfolio management not initialized for template")
            
            start_time = datetime.now()
            
            # Update current positions from execution results
            self._update_positions_from_executions(execution_results)
            
            # Update market data and correlations
            self._update_market_correlations(market_data)
            
            # Calculate current portfolio metrics
            current_metrics = self._calculate_portfolio_metrics()
            
            # Check if portfolio adaptation is needed
            adaptation_needed, adaptation_reasons = self._check_portfolio_adaptation_triggers(current_metrics)
            
            # Perform portfolio adaptation if needed
            adaptation_result = None
            rebalancing_actions = []
            
            if adaptation_needed:
                adaptation_result = await self._perform_portfolio_adaptation(current_metrics, adaptation_reasons)
                if adaptation_result.success:
                    self.adaptation_history.append(adaptation_result)
                    self.last_adaptation_time = datetime.now()
                    rebalancing_actions.extend(adaptation_result.rebalancing_actions)
                    self.logger.info(f"Portfolio adaptation performed: {adaptation_result.risk_improvement_estimate:.2%} risk improvement")
            
            # Check if rebalancing is needed
            rebalancing_needed, rebalancing_reasons = self._check_rebalancing_triggers(current_metrics)
            
            if rebalancing_needed:
                rebalancing_actions_additional = await self._perform_portfolio_rebalancing(current_metrics, rebalancing_reasons)
                rebalancing_actions.extend(rebalancing_actions_additional)
                self.last_rebalancing_time = datetime.now()
                
                # Record rebalancing
                self.rebalancing_history.append({
                    'timestamp': datetime.now(),
                    'reasons': rebalancing_reasons,
                    'actions': rebalancing_actions_additional,
                    'portfolio_value_before': self.current_portfolio_value
                })
            
            # Update portfolio metrics history
            self.portfolio_metrics_history.append({
                'timestamp': datetime.now(),
                'metrics': current_metrics
            })
            
            # Calculate updated metrics after actions
            updated_metrics = self._calculate_portfolio_metrics()
            
            # Prepare portfolio summary
            portfolio_summary = {
                'portfolio_metrics': self._portfolio_metrics_to_dict(updated_metrics),
                'rebalancing_actions': rebalancing_actions,
                'portfolio_parameters': self._portfolio_parameters_to_dict(self.adapted_portfolio_parameters),
                'adaptation_status': {
                    'adaptation_performed': adaptation_needed,
                    'adaptation_reasons': adaptation_reasons,
                    'rebalancing_performed': rebalancing_needed,
                    'rebalancing_reasons': rebalancing_reasons,
                    'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None,
                    'last_rebalancing': self.last_rebalancing_time.isoformat() if self.last_rebalancing_time else None
                },
                'positions_summary': {
                    'total_positions': len(self.current_positions),
                    'largest_position': max([pos.get('weight', 0) for pos in self.current_positions.values()]) if self.current_positions else 0.0,
                    'cash_percentage': self.cash_balance / self.current_portfolio_value if self.current_portfolio_value > 0 else 0.0
                },
                'template_info': {
                    'template_id': self.current_template_id,
                    'template_category': self.current_template_category.value if self.current_template_category else None
                },
                'execution_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            return updated_metrics, portfolio_summary
            
        except Exception as e:
            error_msg = f"Portfolio update failed: {e}"
            self.logger.error(error_msg)
            
            # Return current metrics and error
            current_metrics = self._calculate_portfolio_metrics()
            return current_metrics, {
                'error': error_msg,
                'portfolio_metrics': self._portfolio_metrics_to_dict(current_metrics)
            }
    
    def update_position(self, symbol: str, position_data: Dict[str, Any]):
        """Update a specific position in the portfolio"""
        try:
            self.current_positions[symbol] = {
                'symbol': symbol,
                'quantity': position_data.get('quantity', 0),
                'price': position_data.get('price', 0.0),
                'value': position_data.get('value', 0.0),
                'weight': position_data.get('weight', 0.0),
                'unrealized_pnl': position_data.get('unrealized_pnl', 0.0),
                'last_updated': datetime.now()
            }
            
            # Update portfolio totals
            self._recalculate_portfolio_totals()
            
        except Exception as e:
            self.logger.error(f"Failed to update position {symbol}: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio management summary"""
        current_metrics = self._calculate_portfolio_metrics()
        
        return {
            'current_metrics': self._portfolio_metrics_to_dict(current_metrics),
            'current_parameters': self._portfolio_parameters_to_dict(self.adapted_portfolio_parameters),
            'base_parameters': self._portfolio_parameters_to_dict(self.base_portfolio_parameters),
            'positions_summary': {
                'total_positions': len(self.current_positions),
                'position_details': {symbol: pos for symbol, pos in self.current_positions.items()},
                'diversification_analysis': self._analyze_diversification(),
                'correlation_analysis': self._analyze_correlations()
            },
            'adaptation_summary': {
                'total_adaptations': len(self.adaptation_history),
                'successful_adaptations': len([a for a in self.adaptation_history if a.success]),
                'average_risk_improvement': np.mean([a.risk_improvement_estimate for a in self.adaptation_history if a.success]) if self.adaptation_history else 0.0,
                'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None
            },
            'rebalancing_summary': {
                'total_rebalancing_events': len(self.rebalancing_history),
                'last_rebalancing': self.last_rebalancing_time.isoformat() if self.last_rebalancing_time else None,
                'rebalancing_frequency_actual': self._calculate_actual_rebalancing_frequency()
            },
            'template_info': {
                'template_id': self.current_template_id,
                'template_category': self.current_template_category.value if self.current_template_category else None
            }
        }
    
    # Private helper methods
    def _extract_template_portfolio_parameters(self, template_id: str) -> PortfolioParameters:
        """Extract portfolio parameters from template and inheritance chain"""
        try:
            # Get resolved template with inheritance
            resolved_template = self.inheritance_manager.resolve_inheritance(template_id)
            if not resolved_template:
                template = self.template_registry.get_template(template_id)
                resolved_template = template if template else None
            
            if not resolved_template:
                return PortfolioParameters()  # Default parameters
            
            # Extract portfolio parameters
            portfolio_params = PortfolioParameters()
            
            # Check template parameters for portfolio settings
            if hasattr(resolved_template, 'parameters') and resolved_template.parameters:
                params = resolved_template.parameters
                
                # Map template parameters to portfolio parameters
                param_mappings = {
                    'cash_reserve': 'cash_reserve',
                    'max_position_size': 'max_position_concentration',
                    'target_positions': 'target_num_positions',
                    'max_correlation': 'max_correlation',
                    'rebalancing_threshold': 'rebalancing_threshold'
                }
                
                for template_param, portfolio_param in param_mappings.items():
                    if template_param in params:
                        value = params[template_param]
                        if hasattr(portfolio_params, portfolio_param):
                            setattr(portfolio_params, portfolio_param, float(value))
            
            # Check template components for portfolio manager settings
            if hasattr(resolved_template, 'components') and resolved_template.components:
                portfolio_config = resolved_template.components.get('portfolio_manager', {})
                
                for param_name, param_value in portfolio_config.items():
                    if hasattr(portfolio_params, param_name):
                        if param_name == 'rebalancing_frequency':
                            # Handle enum conversion
                            try:
                                setattr(portfolio_params, param_name, RebalancingFrequency(param_value))
                            except ValueError:
                                pass  # Keep default
                        else:
                            setattr(portfolio_params, param_name, param_value)
            
            # Apply template category adjustments
            category_adjustments = self._get_category_portfolio_adjustments()
            portfolio_params = self._apply_category_portfolio_adjustments(portfolio_params, category_adjustments)
            
            return portfolio_params
            
        except Exception as e:
            self.logger.error(f"Error extracting template portfolio parameters: {e}")
            return PortfolioParameters()  # Return default parameters
    
    def _get_category_portfolio_adjustments(self) -> Dict[str, float]:
        """Get portfolio parameter adjustments based on template category"""
        if self.current_template_category == TemplateCategory.BASE:
            return {
                'cash_reserve_multiplier': 1.2,         # More cash reserve
                'concentration_multiplier': 0.8,        # Lower concentration
                'target_positions_multiplier': 1.2,     # More positions (diversification)
                'correlation_multiplier': 0.9           # Lower correlation tolerance
            }
        elif self.current_template_category == TemplateCategory.SPECIFIC:
            return {
                'cash_reserve_multiplier': 1.0,         # Standard cash reserve
                'concentration_multiplier': 1.0,        # Standard concentration
                'target_positions_multiplier': 1.0,     # Standard positions
                'correlation_multiplier': 1.0           # Standard correlation
            }
        elif self.current_template_category == TemplateCategory.COMPOSITE:
            return {
                'cash_reserve_multiplier': 0.8,         # Less cash reserve
                'concentration_multiplier': 1.2,        # Higher concentration allowed
                'target_positions_multiplier': 0.8,     # Fewer positions (concentration)
                'correlation_multiplier': 1.1           # Higher correlation tolerance
            }
        else:
            return {
                'cash_reserve_multiplier': 1.0,
                'concentration_multiplier': 1.0,
                'target_positions_multiplier': 1.0,
                'correlation_multiplier': 1.0
            }
    
    def _apply_category_portfolio_adjustments(self, params: PortfolioParameters, adjustments: Dict[str, float]) -> PortfolioParameters:
        """Apply category-specific adjustments to portfolio parameters"""
        adjusted_params = PortfolioParameters(
            cash_reserve=params.cash_reserve * adjustments.get('cash_reserve_multiplier', 1.0),
            max_position_concentration=params.max_position_concentration * adjustments.get('concentration_multiplier', 1.0),
            target_num_positions=int(params.target_num_positions * adjustments.get('target_positions_multiplier', 1.0)),
            rebalancing_frequency=params.rebalancing_frequency,  # Keep frequency unchanged
            rebalancing_threshold=params.rebalancing_threshold,  # Keep threshold unchanged
            max_correlation=params.max_correlation * adjustments.get('correlation_multiplier', 1.0),
            min_diversification_score=params.min_diversification_score,  # Keep unchanged
            cash_management_strategy=params.cash_management_strategy,    # Keep unchanged
            position_sizing_method=params.position_sizing_method         # Keep unchanged
        )
        
        # Ensure values stay within reasonable bounds
        adjusted_params.cash_reserve = max(0.05, min(0.5, adjusted_params.cash_reserve))                               # 5% to 50%
        adjusted_params.max_position_concentration = max(0.05, min(0.5, adjusted_params.max_position_concentration))   # 5% to 50%
        adjusted_params.target_num_positions = max(3, min(50, adjusted_params.target_num_positions))                   # 3 to 50 positions
        adjusted_params.max_correlation = max(0.3, min(1.0, adjusted_params.max_correlation))                         # 30% to 100%
        
        return adjusted_params
    
    def _update_positions_from_executions(self, execution_results: List[Dict[str, Any]]):
        """Update current positions from execution results"""
        try:
            for execution in execution_results:
                symbol = execution.get('symbol', '')
                if not symbol:
                    continue
                
                # Get current position or create new one
                if symbol not in self.current_positions:
                    self.current_positions[symbol] = {
                        'symbol': symbol,
                        'quantity': 0,
                        'average_price': 0.0,
                        'value': 0.0,
                        'weight': 0.0,
                        'unrealized_pnl': 0.0,
                        'last_updated': datetime.now()
                    }
                
                position = self.current_positions[symbol]
                
                # Update position based on execution
                execution_quantity = execution.get('quantity', 0)
                execution_price = execution.get('price', 0.0)
                execution_side = execution.get('side', 'buy')
                
                if execution_side.lower() == 'buy':
                    # Add to position
                    old_quantity = position['quantity']
                    old_avg_price = position['average_price']
                    
                    new_quantity = old_quantity + execution_quantity
                    if new_quantity > 0:
                        new_avg_price = ((old_quantity * old_avg_price) + (execution_quantity * execution_price)) / new_quantity
                    else:
                        new_avg_price = execution_price
                    
                    position['quantity'] = new_quantity
                    position['average_price'] = new_avg_price
                    
                else:  # sell
                    # Reduce position
                    position['quantity'] = max(0, position['quantity'] - execution_quantity)
                    if position['quantity'] == 0:
                        position['average_price'] = 0.0
                
                # Update position value and weight
                current_price = execution.get('current_price', execution_price)
                position['value'] = position['quantity'] * current_price
                position['weight'] = position['value'] / self.current_portfolio_value if self.current_portfolio_value > 0 else 0.0
                position['unrealized_pnl'] = (current_price - position['average_price']) * position['quantity'] if position['average_price'] > 0 else 0.0
                position['last_updated'] = datetime.now()
                
                # Remove positions with zero quantity
                if position['quantity'] == 0:
                    del self.current_positions[symbol]
            
            # Recalculate portfolio totals
            self._recalculate_portfolio_totals()
            
        except Exception as e:
            self.logger.error(f"Error updating positions from executions: {e}")
    
    def _update_market_correlations(self, market_data: Dict[str, Any]):
        """Update correlation matrix from market data"""
        try:
            if 'correlations' in market_data and isinstance(market_data['correlations'], dict):
                # Convert correlation data to DataFrame
                correlation_data = market_data['correlations']
                symbols = list(self.current_positions.keys())
                
                if len(symbols) > 1:
                    # Create correlation matrix for current positions
                    correlation_matrix = pd.DataFrame(index=symbols, columns=symbols, dtype=float)
                    
                    for i, symbol1 in enumerate(symbols):
                        for j, symbol2 in enumerate(symbols):
                            if i == j:
                                correlation_matrix.loc[symbol1, symbol2] = 1.0
                            else:
                                # Try to get correlation from market data
                                corr_key = f"{symbol1}_{symbol2}"
                                reverse_corr_key = f"{symbol2}_{symbol1}"
                                
                                if corr_key in correlation_data:
                                    correlation_matrix.loc[symbol1, symbol2] = correlation_data[corr_key]
                                elif reverse_corr_key in correlation_data:
                                    correlation_matrix.loc[symbol1, symbol2] = correlation_data[reverse_corr_key]
                                else:
                                    # Default correlation estimate
                                    correlation_matrix.loc[symbol1, symbol2] = 0.3
                    
                    self.correlation_matrix = correlation_matrix
            
        except Exception as e:
            self.logger.error(f"Error updating market correlations: {e}")
    
    def _calculate_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate current portfolio metrics"""
        try:
            total_value = self.cash_balance
            invested_capital = 0.0
            largest_position_pct = 0.0
            num_positions = len(self.current_positions)
            
            # Calculate position values
            for position in self.current_positions.values():
                position_value = position.get('value', 0.0)
                total_value += position_value
                invested_capital += position_value
                
                position_pct = position_value / total_value if total_value > 0 else 0.0
                largest_position_pct = max(largest_position_pct, position_pct)
            
            # Update portfolio totals
            self.current_portfolio_value = total_value
            self.invested_capital = invested_capital
            
            # Calculate correlation metrics
            avg_correlation = 0.0
            if self.correlation_matrix is not None and len(self.correlation_matrix) > 1:
                # Get upper triangle of correlation matrix (excluding diagonal)
                mask = np.triu(np.ones_like(self.correlation_matrix.values, dtype=bool), k=1)
                correlations = self.correlation_matrix.values[mask]
                avg_correlation = np.mean(correlations) if len(correlations) > 0 else 0.0
            
            # Calculate diversification score
            diversification_score = self._calculate_diversification_score()
            
            # Calculate performance metrics (simplified)
            daily_return = 0.0
            cumulative_return = 0.0
            max_drawdown = 0.0
            volatility = 0.0
            sharpe_ratio = 0.0
            
            if len(self.portfolio_metrics_history) > 1:
                # Calculate returns from history
                values = [entry['metrics'].total_value for entry in self.portfolio_metrics_history]
                returns = np.diff(values) / values[:-1]
                
                daily_return = returns[-1] if len(returns) > 0 else 0.0
                cumulative_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0.0
                volatility = np.std(returns) if len(returns) > 1 else 0.0
                
                # Calculate max drawdown
                cumulative_values = np.cumprod(1 + returns)
                running_max = np.maximum.accumulate(cumulative_values)
                drawdowns = (cumulative_values - running_max) / running_max
                max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
                
                # Calculate Sharpe ratio (assuming 2% risk-free rate)
                if volatility > 0:
                    excess_return = np.mean(returns) - 0.02/252  # Daily risk-free rate
                    sharpe_ratio = excess_return / volatility * np.sqrt(252)  # Annualized
            
            return PortfolioMetrics(
                total_value=total_value,
                cash_balance=self.cash_balance,
                invested_capital=invested_capital,
                number_of_positions=num_positions,
                largest_position_pct=largest_position_pct,
                avg_correlation=avg_correlation,
                diversification_score=diversification_score,
                portfolio_beta=1.0,  # Simplified
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                daily_return=daily_return,
                cumulative_return=cumulative_return
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio metrics: {e}")
            return PortfolioMetrics()
    
    def _calculate_diversification_score(self) -> float:
        """Calculate portfolio diversification score (0-1, higher is better)"""
        try:
            if len(self.current_positions) < 2:
                return 0.0
            
            # Calculate weight concentration (Herfindahl index)
            weights = [pos.get('weight', 0.0) for pos in self.current_positions.values()]
            herfindahl_index = sum(w**2 for w in weights)
            
            # Convert to diversification score (lower concentration = higher diversification)
            concentration_score = 1.0 - herfindahl_index
            
            # Factor in number of positions
            num_positions = len(self.current_positions)
            target_positions = self.adapted_portfolio_parameters.target_num_positions
            position_score = min(1.0, num_positions / target_positions) if target_positions > 0 else 0.0
            
            # Factor in correlation (lower correlation = higher diversification)
            correlation_score = 1.0
            if self.correlation_matrix is not None:
                avg_correlation = abs(self.correlation_matrix.values.mean())
                correlation_score = 1.0 - avg_correlation
            
            # Weighted combination
            diversification_score = (concentration_score * 0.4 + 
                                   position_score * 0.3 + 
                                   correlation_score * 0.3)
            
            return max(0.0, min(1.0, diversification_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating diversification score: {e}")
            return 0.0
    
    def _recalculate_portfolio_totals(self):
        """Recalculate portfolio totals after position updates"""
        try:
            total_position_value = sum(pos.get('value', 0.0) for pos in self.current_positions.values())
            self.invested_capital = total_position_value
            self.current_portfolio_value = self.cash_balance + total_position_value
            
            # Update position weights
            for position in self.current_positions.values():
                position['weight'] = position.get('value', 0.0) / self.current_portfolio_value if self.current_portfolio_value > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error recalculating portfolio totals: {e}")
    
    def _check_portfolio_adaptation_triggers(self, metrics: PortfolioMetrics) -> Tuple[bool, List[str]]:
        """Check if portfolio adaptation is needed"""
        reasons = []
        
        try:
            # Check adaptation frequency
            if self.last_adaptation_time:
                time_since_last = datetime.now() - self.last_adaptation_time
                if time_since_last < self.config.adaptation_frequency:
                    return False, []
            
            # Check correlation spike
            if metrics.avg_correlation > self.config.adaptation_triggers['correlation_spike_threshold']:
                reasons.append("correlation_spike")
            
            # Check concentration warning
            if metrics.largest_position_pct > self.config.adaptation_triggers['concentration_warning_threshold']:
                reasons.append("high_concentration")
            
            # Check cash reserve levels
            cash_pct = metrics.cash_balance / metrics.total_value if metrics.total_value > 0 else 0.0
            if cash_pct < self.config.adaptation_triggers['cash_reserve_low_threshold']:
                reasons.append("low_cash_reserve")
            elif cash_pct > self.config.adaptation_triggers['cash_reserve_high_threshold']:
                reasons.append("high_cash_reserve")
            
            # Check performance degradation
            if metrics.daily_return < self.config.adaptation_triggers['performance_degradation_threshold']:
                reasons.append("performance_degradation")
            
            # Check diversification score
            if metrics.diversification_score < self.adapted_portfolio_parameters.min_diversification_score:
                reasons.append("low_diversification")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio adaptation triggers: {e}")
            return False, []
    
    def _check_rebalancing_triggers(self, metrics: PortfolioMetrics) -> Tuple[bool, List[str]]:
        """Check if portfolio rebalancing is needed"""
        reasons = []
        
        try:
            # Check rebalancing frequency
            if self.last_rebalancing_time:
                time_since_last = datetime.now() - self.last_rebalancing_time
                
                if self.adapted_portfolio_parameters.rebalancing_frequency == RebalancingFrequency.DAILY:
                    if time_since_last < timedelta(days=1):
                        return False, []
                elif self.adapted_portfolio_parameters.rebalancing_frequency == RebalancingFrequency.WEEKLY:
                    if time_since_last < timedelta(weeks=1):
                        return False, []
                elif self.adapted_portfolio_parameters.rebalancing_frequency == RebalancingFrequency.MONTHLY:
                    if time_since_last < timedelta(days=30):
                        return False, []
            
            # Check threshold-based rebalancing
            threshold = self.adapted_portfolio_parameters.rebalancing_threshold
            
            # Check if any position has drifted significantly
            target_weight = 1.0 / max(1, metrics.number_of_positions)  # Equal weight target
            
            for position in self.current_positions.values():
                current_weight = position.get('weight', 0.0)
                weight_deviation = abs(current_weight - target_weight)
                
                if weight_deviation > threshold:
                    reasons.append("weight_drift")
                    break
            
            # Check if cash allocation has drifted
            target_cash_pct = self.adapted_portfolio_parameters.cash_reserve
            current_cash_pct = metrics.cash_balance / metrics.total_value if metrics.total_value > 0 else 0.0
            cash_deviation = abs(current_cash_pct - target_cash_pct)
            
            if cash_deviation > threshold:
                reasons.append("cash_drift")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking rebalancing triggers: {e}")
            return False, []
    
    async def _perform_portfolio_adaptation(self, metrics: PortfolioMetrics, reasons: List[str]) -> PortfolioAdaptationResult:
        """Perform portfolio parameter adaptation"""
        try:
            start_time = datetime.now()
            
            # Create new adapted parameters
            new_params = PortfolioParameters(
                cash_reserve=self.adapted_portfolio_parameters.cash_reserve,
                max_position_concentration=self.adapted_portfolio_parameters.max_position_concentration,
                target_num_positions=self.adapted_portfolio_parameters.target_num_positions,
                rebalancing_frequency=self.adapted_portfolio_parameters.rebalancing_frequency,
                rebalancing_threshold=self.adapted_portfolio_parameters.rebalancing_threshold,
                max_correlation=self.adapted_portfolio_parameters.max_correlation,
                min_diversification_score=self.adapted_portfolio_parameters.min_diversification_score,
                cash_management_strategy=self.adapted_portfolio_parameters.cash_management_strategy,
                position_sizing_method=self.adapted_portfolio_parameters.position_sizing_method
            )
            
            # Get category rules
            category_rules = self.config.category_portfolio_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_portfolio_adjustment', 0.2)
            rebalancing_aggressiveness = category_rules.get('rebalancing_aggressiveness', 0.7)
            
            # Adapt parameters based on reasons
            adaptation_magnitude = 0.0
            rebalancing_actions = []
            
            if 'correlation_spike' in reasons:
                # Increase diversification requirements
                correlation_adjustment = min(max_adjustment, 0.1 * rebalancing_aggressiveness)
                new_params.max_correlation *= (1 - correlation_adjustment)
                new_params.min_diversification_score = min(1.0, new_params.min_diversification_score + correlation_adjustment)
                adaptation_magnitude += correlation_adjustment
                
                # Generate rebalancing actions to reduce correlation
                rebalancing_actions.extend(self._generate_correlation_reduction_actions(metrics))
            
            if 'high_concentration' in reasons:
                # Reduce maximum position concentration
                concentration_adjustment = min(max_adjustment, 0.15 * rebalancing_aggressiveness)
                new_params.max_position_concentration *= (1 - concentration_adjustment)
                adaptation_magnitude += concentration_adjustment
                
                # Generate rebalancing actions to reduce concentration
                rebalancing_actions.extend(self._generate_concentration_reduction_actions(metrics))
            
            if 'low_cash_reserve' in reasons:
                # Increase cash reserve target
                cash_adjustment = min(max_adjustment, 0.05 * rebalancing_aggressiveness)
                new_params.cash_reserve = min(0.3, new_params.cash_reserve + cash_adjustment)
                adaptation_magnitude += cash_adjustment
                
                # Generate actions to increase cash
                rebalancing_actions.append({
                    'action': 'increase_cash',
                    'target_cash_percentage': new_params.cash_reserve,
                    'reason': 'low_cash_reserve'
                })
            
            if 'high_cash_reserve' in reasons:
                # Decrease cash reserve target
                cash_adjustment = min(max_adjustment, 0.03 * rebalancing_aggressiveness)
                new_params.cash_reserve = max(0.05, new_params.cash_reserve - cash_adjustment)
                adaptation_magnitude += cash_adjustment
                
                # Generate actions to deploy cash
                rebalancing_actions.append({
                    'action': 'deploy_cash',
                    'target_cash_percentage': new_params.cash_reserve,
                    'reason': 'high_cash_reserve'
                })
            
            if 'low_diversification' in reasons:
                # Increase target number of positions
                diversification_adjustment = min(max_adjustment, 0.2 * rebalancing_aggressiveness)
                new_params.target_num_positions = min(30, int(new_params.target_num_positions * (1 + diversification_adjustment)))
                new_params.max_position_concentration *= (1 - diversification_adjustment)
                adaptation_magnitude += diversification_adjustment
                
                # Generate actions to improve diversification
                rebalancing_actions.extend(self._generate_diversification_improvement_actions(metrics))
            
            # Ensure parameters stay within bounds
            new_params = self._enforce_portfolio_parameter_bounds(new_params)
            
            # Validate template compliance
            template_compliance = self._validate_portfolio_template_compliance(new_params)
            
            if template_compliance:
                # Calculate risk improvement estimate
                risk_improvement = self._estimate_portfolio_risk_improvement(self.adapted_portfolio_parameters, new_params)
                
                # Calculate confidence score
                confidence_score = self._calculate_portfolio_adaptation_confidence(reasons, adaptation_magnitude)
                
                # Apply adaptations
                self.adapted_portfolio_parameters = new_params
                
                result = PortfolioAdaptationResult(
                    success=True,
                    adapted_parameters=new_params,
                    rebalancing_actions=rebalancing_actions,
                    adaptation_magnitude=adaptation_magnitude,
                    risk_improvement_estimate=risk_improvement,
                    confidence_score=confidence_score,
                    adaptation_reasons=reasons,
                    template_compliance=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
            else:
                result = PortfolioAdaptationResult(
                    success=False,
                    adapted_parameters=self.adapted_portfolio_parameters,
                    rebalancing_actions=[],
                    adaptation_magnitude=0.0,
                    risk_improvement_estimate=0.0,
                    confidence_score=0.0,
                    adaptation_reasons=reasons,
                    template_compliance=False,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    error_message="Template compliance validation failed"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Portfolio adaptation failed: {e}"
            self.logger.error(error_msg)
            
            return PortfolioAdaptationResult(
                success=False,
                adapted_parameters=self.adapted_portfolio_parameters,
                rebalancing_actions=[],
                adaptation_magnitude=0.0,
                risk_improvement_estimate=0.0,
                confidence_score=0.0,
                adaptation_reasons=reasons,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            )
    
    async def _perform_portfolio_rebalancing(self, metrics: PortfolioMetrics, reasons: List[str]) -> List[Dict[str, Any]]:
        """Perform portfolio rebalancing"""
        try:
            rebalancing_actions = []
            
            if 'weight_drift' in reasons:
                # Calculate target weights and generate rebalancing actions
                target_weight = 1.0 / max(1, metrics.number_of_positions) if metrics.number_of_positions > 0 else 0.0
                
                for symbol, position in self.current_positions.items():
                    current_weight = position.get('weight', 0.0)
                    weight_difference = target_weight - current_weight
                    
                    if abs(weight_difference) > self.adapted_portfolio_parameters.rebalancing_threshold:
                        action_type = 'increase_position' if weight_difference > 0 else 'decrease_position'
                        target_value = target_weight * metrics.total_value
                        
                        rebalancing_actions.append({
                            'action': action_type,
                            'symbol': symbol,
                            'current_weight': current_weight,
                            'target_weight': target_weight,
                            'target_value': target_value,
                            'reason': 'weight_drift'
                        })
            
            if 'cash_drift' in reasons:
                # Rebalance cash allocation
                target_cash_value = self.adapted_portfolio_parameters.cash_reserve * metrics.total_value
                cash_difference = target_cash_value - metrics.cash_balance
                
                if abs(cash_difference) > metrics.total_value * self.adapted_portfolio_parameters.rebalancing_threshold:
                    if cash_difference > 0:
                        # Need to raise cash
                        rebalancing_actions.append({
                            'action': 'raise_cash',
                            'amount': cash_difference,
                            'target_cash_balance': target_cash_value,
                            'reason': 'cash_drift'
                        })
                    else:
                        # Need to deploy cash
                        rebalancing_actions.append({
                            'action': 'deploy_cash',
                            'amount': abs(cash_difference),
                            'target_cash_balance': target_cash_value,
                            'reason': 'cash_drift'
                        })
            
            return rebalancing_actions
            
        except Exception as e:
            self.logger.error(f"Error performing portfolio rebalancing: {e}")
            return []
    
    # Helper methods for generating specific rebalancing actions
    def _generate_correlation_reduction_actions(self, metrics: PortfolioMetrics) -> List[Dict[str, Any]]:
        """Generate actions to reduce portfolio correlation"""
        actions = []
        
        if self.correlation_matrix is not None and len(self.correlation_matrix) > 1:
            # Find highest correlated pairs
            mask = np.triu(np.ones_like(self.correlation_matrix.values, dtype=bool), k=1)
            correlations = self.correlation_matrix.where(mask)
            
            # Find positions with highest correlations
            max_corr_idx = np.unravel_index(np.nanargmax(correlations.values), correlations.shape)
            if not np.isnan(correlations.iloc[max_corr_idx]):
                symbol1 = correlations.index[max_corr_idx[0]]
                symbol2 = correlations.columns[max_corr_idx[1]]
                correlation_value = correlations.iloc[max_corr_idx]
                
                if correlation_value > self.adapted_portfolio_parameters.max_correlation:
                    # Suggest reducing one of the correlated positions
                    actions.append({
                        'action': 'reduce_correlated_position',
                        'symbol': symbol1,
                        'correlated_with': symbol2,
                        'correlation': correlation_value,
                        'suggested_reduction': 0.3,
                        'reason': 'correlation_reduction'
                    })
        
        return actions
    
    def _generate_concentration_reduction_actions(self, metrics: PortfolioMetrics) -> List[Dict[str, Any]]:
        """Generate actions to reduce portfolio concentration"""
        actions = []
        
        # Find the largest position
        largest_position = None
        largest_weight = 0.0
        
        for symbol, position in self.current_positions.items():
            weight = position.get('weight', 0.0)
            if weight > largest_weight:
                largest_weight = weight
                largest_position = symbol
        
        if largest_position and largest_weight > self.adapted_portfolio_parameters.max_position_concentration:
            target_weight = self.adapted_portfolio_parameters.max_position_concentration
            reduction_needed = largest_weight - target_weight
            
            actions.append({
                'action': 'reduce_concentration',
                'symbol': largest_position,
                'current_weight': largest_weight,
                'target_weight': target_weight,
                'reduction_needed': reduction_needed,
                'reason': 'concentration_reduction'
            })
        
        return actions
    
    def _generate_diversification_improvement_actions(self, metrics: PortfolioMetrics) -> List[Dict[str, Any]]:
        """Generate actions to improve portfolio diversification"""
        actions = []
        
        current_positions = metrics.number_of_positions
        target_positions = self.adapted_portfolio_parameters.target_num_positions
        
        if current_positions < target_positions:
            positions_needed = target_positions - current_positions
            target_weight_per_position = 1.0 / target_positions
            
            actions.append({
                'action': 'add_positions',
                'positions_needed': positions_needed,
                'target_weight_per_position': target_weight_per_position,
                'reason': 'diversification_improvement'
            })
        
        return actions
    
    # Utility methods
    def _enforce_portfolio_parameter_bounds(self, params: PortfolioParameters) -> PortfolioParameters:
        """Ensure portfolio parameters stay within reasonable bounds"""
        bounded_params = PortfolioParameters(
            cash_reserve=max(0.05, min(0.5, params.cash_reserve)),                                   # 5% to 50%
            max_position_concentration=max(0.05, min(0.5, params.max_position_concentration)),       # 5% to 50%
            target_num_positions=max(3, min(50, params.target_num_positions)),                       # 3 to 50 positions
            rebalancing_frequency=params.rebalancing_frequency,                                       # Keep unchanged
            rebalancing_threshold=max(0.01, min(0.2, params.rebalancing_threshold)),                # 1% to 20%
            max_correlation=max(0.3, min(1.0, params.max_correlation)),                             # 30% to 100%
            min_diversification_score=max(0.1, min(1.0, params.min_diversification_score)),         # 10% to 100%
            cash_management_strategy=params.cash_management_strategy,                                 # Keep unchanged
            position_sizing_method=params.position_sizing_method                                      # Keep unchanged
        )
        
        return bounded_params
    
    def _validate_portfolio_template_compliance(self, params: PortfolioParameters) -> bool:
        """Validate portfolio parameters against template constraints"""
        try:
            # Get category rules
            category_rules = self.config.category_portfolio_rules.get(self.current_template_category, {})
            max_adjustment = category_rules.get('max_portfolio_adjustment', 0.3)
            
            # Check each parameter against base parameters
            base = self.base_portfolio_parameters
            
            # Calculate maximum allowed deviations
            checks = [
                ('cash_reserve', params.cash_reserve, base.cash_reserve),
                ('max_position_concentration', params.max_position_concentration, base.max_position_concentration),
                ('max_correlation', params.max_correlation, base.max_correlation),
                ('rebalancing_threshold', params.rebalancing_threshold, base.rebalancing_threshold)
            ]
            
            for param_name, new_value, base_value in checks:
                if base_value > 0:
                    deviation = abs((new_value - base_value) / base_value)
                    if deviation > max_adjustment:
                        self.logger.warning(f"Portfolio parameter {param_name} deviation {deviation:.2%} exceeds limit {max_adjustment:.2%}")
                        return False
            
            # Check target positions (integer check)
            positions_deviation = abs(params.target_num_positions - base.target_num_positions) / max(1, base.target_num_positions)
            if positions_deviation > max_adjustment:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating portfolio template compliance: {e}")
            return False
    
    def _estimate_portfolio_risk_improvement(self, old_params: PortfolioParameters, new_params: PortfolioParameters) -> float:
        """Estimate risk improvement from parameter changes"""
        try:
            # Calculate risk improvement for key parameters
            diversification_improvement = 0.0
            if new_params.target_num_positions > old_params.target_num_positions:
                diversification_improvement = (new_params.target_num_positions - old_params.target_num_positions) / old_params.target_num_positions
            
            concentration_improvement = 0.0
            if new_params.max_position_concentration < old_params.max_position_concentration:
                concentration_improvement = (old_params.max_position_concentration - new_params.max_position_concentration) / old_params.max_position_concentration
            
            correlation_improvement = 0.0
            if new_params.max_correlation < old_params.max_correlation:
                correlation_improvement = (old_params.max_correlation - new_params.max_correlation) / old_params.max_correlation
            
            cash_stability_improvement = 0.0
            if abs(new_params.cash_reserve - 0.1) < abs(old_params.cash_reserve - 0.1):  # 10% is ideal cash level
                cash_stability_improvement = 0.05
            
            # Weighted average of improvements
            total_risk_improvement = (diversification_improvement * 0.3 + 
                                    concentration_improvement * 0.3 + 
                                    correlation_improvement * 0.3 + 
                                    cash_stability_improvement * 0.1)
            
            return max(0.0, min(0.4, total_risk_improvement))  # Cap at 40% improvement
            
        except Exception as e:
            self.logger.error(f"Error estimating portfolio risk improvement: {e}")
            return 0.0
    
    def _calculate_portfolio_adaptation_confidence(self, reasons: List[str], adaptation_magnitude: float) -> float:
        """Calculate confidence in portfolio adaptation decision"""
        
        base_confidence = 0.75  # Base confidence for portfolio management
        
        # Adjust based on adaptation magnitude
        if adaptation_magnitude > 0.25:
            base_confidence -= 0.1  # Large changes are riskier
        elif adaptation_magnitude < 0.05:
            base_confidence -= 0.05  # Very small changes may not help
        
        # Adjust based on reasons
        reason_confidence_adjustments = {
            'correlation_spike': 0.1,       # High confidence for correlation response
            'high_concentration': 0.08,     # High confidence for concentration response
            'low_cash_reserve': 0.05,       # Medium confidence for cash management
            'high_cash_reserve': 0.03,      # Lower confidence for excess cash
            'performance_degradation': 0.05, # Medium confidence for performance triggers
            'low_diversification': 0.07     # High confidence for diversification
        }
        
        for reason in reasons:
            base_confidence += reason_confidence_adjustments.get(reason, 0.0)
        
        # Adjust based on portfolio size (larger portfolios are easier to manage)
        if len(self.current_positions) > 10:
            base_confidence += 0.05
        elif len(self.current_positions) < 5:
            base_confidence -= 0.05
        
        return max(0.1, min(1.0, base_confidence))
    
    def _analyze_diversification(self) -> Dict[str, Any]:
        """Analyze portfolio diversification"""
        try:
            num_positions = len(self.current_positions)
            target_positions = self.adapted_portfolio_parameters.target_num_positions
            
            # Calculate weight distribution
            weights = [pos.get('weight', 0.0) for pos in self.current_positions.values()]
            
            # Herfindahl index (concentration measure)
            herfindahl_index = sum(w**2 for w in weights) if weights else 0.0
            
            # Effective number of positions
            effective_positions = 1.0 / herfindahl_index if herfindahl_index > 0 else 0.0
            
            return {
                'number_of_positions': num_positions,
                'target_positions': target_positions,
                'position_gap': target_positions - num_positions,
                'herfindahl_index': herfindahl_index,
                'effective_positions': effective_positions,
                'diversification_score': self._calculate_diversification_score(),
                'largest_position_weight': max(weights) if weights else 0.0,
                'smallest_position_weight': min(weights) if weights else 0.0,
                'weight_std_dev': np.std(weights) if weights else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing diversification: {e}")
            return {}
    
    def _analyze_correlations(self) -> Dict[str, Any]:
        """Analyze portfolio correlations"""
        try:
            if self.correlation_matrix is None or len(self.correlation_matrix) < 2:
                return {
                    'average_correlation': 0.0,
                    'max_correlation': 0.0,
                    'min_correlation': 0.0,
                    'correlation_warnings': []
                }
            
            # Get upper triangle correlations (excluding diagonal)
            mask = np.triu(np.ones_like(self.correlation_matrix.values, dtype=bool), k=1)
            correlations = self.correlation_matrix.values[mask]
            
            avg_correlation = np.mean(correlations)
            max_correlation = np.max(correlations)
            min_correlation = np.min(correlations)
            
            # Find correlation warnings
            warnings = []
            threshold = self.adapted_portfolio_parameters.max_correlation
            
            for i in range(len(self.correlation_matrix)):
                for j in range(i+1, len(self.correlation_matrix)):
                    corr_value = self.correlation_matrix.iloc[i, j]
                    if corr_value > threshold:
                        symbol1 = self.correlation_matrix.index[i]
                        symbol2 = self.correlation_matrix.columns[j]
                        warnings.append({
                            'symbol1': symbol1,
                            'symbol2': symbol2,
                            'correlation': corr_value,
                            'threshold': threshold
                        })
            
            return {
                'average_correlation': avg_correlation,
                'max_correlation': max_correlation,
                'min_correlation': min_correlation,
                'correlation_matrix_size': len(self.correlation_matrix),
                'correlation_warnings': warnings,
                'high_correlation_pairs': len(warnings)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing correlations: {e}")
            return {}
    
    def _calculate_actual_rebalancing_frequency(self) -> str:
        """Calculate actual rebalancing frequency from history"""
        try:
            if len(self.rebalancing_history) < 2:
                return "insufficient_data"
            
            # Calculate average time between rebalancing events
            timestamps = [entry['timestamp'] for entry in self.rebalancing_history]
            time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            
            avg_time_diff = sum(time_diffs, timedelta()) / len(time_diffs)
            
            if avg_time_diff < timedelta(days=2):
                return "daily"
            elif avg_time_diff < timedelta(days=10):
                return "weekly"
            elif avg_time_diff < timedelta(days=45):
                return "monthly"
            else:
                return "quarterly_or_longer"
                
        except Exception as e:
            self.logger.error(f"Error calculating actual rebalancing frequency: {e}")
            return "unknown"
    
    def _portfolio_metrics_to_dict(self, metrics: PortfolioMetrics) -> Dict[str, Any]:
        """Convert portfolio metrics to dictionary for serialization"""
        return {
            'total_value': metrics.total_value,
            'cash_balance': metrics.cash_balance,
            'invested_capital': metrics.invested_capital,
            'number_of_positions': metrics.number_of_positions,
            'largest_position_pct': metrics.largest_position_pct,
            'avg_correlation': metrics.avg_correlation,
            'diversification_score': metrics.diversification_score,
            'portfolio_beta': metrics.portfolio_beta,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown,
            'volatility': metrics.volatility,
            'daily_return': metrics.daily_return,
            'cumulative_return': metrics.cumulative_return
        }
    
    def _portfolio_parameters_to_dict(self, params: PortfolioParameters) -> Dict[str, Any]:
        """Convert portfolio parameters to dictionary for serialization"""
        return {
            'cash_reserve': params.cash_reserve,
            'max_position_concentration': params.max_position_concentration,
            'target_num_positions': params.target_num_positions,
            'rebalancing_frequency': params.rebalancing_frequency.value,
            'rebalancing_threshold': params.rebalancing_threshold,
            'max_correlation': params.max_correlation,
            'min_diversification_score': params.min_diversification_score,
            'cash_management_strategy': params.cash_management_strategy,
            'position_sizing_method': params.position_sizing_method
        }
