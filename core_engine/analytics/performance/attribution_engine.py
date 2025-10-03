"""
Performance Engine - Attribution Engine
Advanced performance attribution analysis engine
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict
import threading

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class AttributionMethod(Enum):
    """Attribution analysis methods"""
    BRINSON = "brinson"
    BRINSON_FACHLER = "brinson_fachler"
    GEOMETRIC = "geometric"
    ARITHMETIC = "arithmetic"
    RISK_ADJUSTED = "risk_adjusted"


class AttributionLevel(Enum):
    """Attribution analysis levels"""
    SECTOR = "sector"
    SECURITY = "security"
    STRATEGY = "strategy"
    FACTOR = "factor"
    STYLE = "style"
    CURRENCY = "currency"


class AllocationEffect(Enum):
    """Types of allocation effects"""
    PURE_ALLOCATION = "pure_allocation"
    PURE_SELECTION = "pure_selection"
    INTERACTION = "interaction"
    TOTAL = "total"


@dataclass
class AttributionResult:
    """Attribution analysis result"""
    
    # Core attribution effects
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    total_effect: float = 0.0
    
    # Component breakdown
    component_contributions: Dict[str, float] = field(default_factory=dict)
    component_weights: Dict[str, float] = field(default_factory=dict)
    component_returns: Dict[str, float] = field(default_factory=dict)
    
    # Benchmark comparison
    benchmark_weights: Dict[str, float] = field(default_factory=dict)
    benchmark_returns: Dict[str, float] = field(default_factory=dict)
    
    # Risk attribution
    risk_contributions: Dict[str, float] = field(default_factory=dict)
    volatility_attribution: Dict[str, float] = field(default_factory=dict)
    
    # Timing information
    analysis_period: Tuple[datetime, datetime] = field(default_factory=lambda: (datetime.now(), datetime.now()))
    calculation_time: datetime = field(default_factory=datetime.now)
    
    # Metadata
    method: AttributionMethod = AttributionMethod.BRINSON
    level: AttributionLevel = AttributionLevel.SECTOR
    currency: str = "USD"


@dataclass
class AttributionConfig:
    """Attribution engine configuration"""
    
    # Analysis settings
    method: AttributionMethod = AttributionMethod.BRINSON
    level: AttributionLevel = AttributionLevel.SECTOR
    frequency: str = "daily"  # daily, weekly, monthly
    
    # Risk attribution settings
    enable_risk_attribution: bool = True
    risk_model: str = "factor_model"  # factor_model, statistical, hybrid
    
    # Factor settings
    enable_factor_attribution: bool = True
    factor_models: List[str] = field(default_factory=lambda: ["fama_french", "carhart", "custom"])
    
    # Currency settings
    base_currency: str = "USD"
    enable_currency_attribution: bool = True
    
    # Calculation settings
    minimum_weight_threshold: float = 0.001  # 0.1% minimum weight
    rebalancing_frequency: str = "monthly"
    
    # Advanced settings
    enable_geometric_linking: bool = True
    enable_smoothing: bool = False
    smoothing_window: int = 5


class BrinsonAttributionEngine:
    """Brinson attribution analysis engine"""
    
    def __init__(self, config: AttributionConfig):
        self.config = config
        
        logger.info("Brinson attribution engine initialized")
    
    def calculate_attribution(self, portfolio_weights: Dict[str, float],
                            portfolio_returns: Dict[str, float],
                            benchmark_weights: Dict[str, float],
                            benchmark_returns: Dict[str, float]) -> AttributionResult:
        """Calculate Brinson attribution effects"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.BRINSON,
                level=self.config.level
            )
            
            # Ensure all components are represented
            all_components = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
            
            # Fill missing weights/returns with zeros
            for component in all_components:
                if component not in portfolio_weights:
                    portfolio_weights[component] = 0.0
                if component not in portfolio_returns:
                    portfolio_returns[component] = 0.0
                if component not in benchmark_weights:
                    benchmark_weights[component] = 0.0
                if component not in benchmark_returns:
                    benchmark_returns[component] = 0.0
            
            # Calculate benchmark return
            benchmark_return = sum(
                benchmark_weights[c] * benchmark_returns[c] 
                for c in all_components
            )
            
            # Calculate attribution effects for each component
            allocation_effects = {}
            selection_effects = {}
            interaction_effects = {}
            
            for component in all_components:
                wp = portfolio_weights[component]
                wb = benchmark_weights[component]
                rp = portfolio_returns[component]
                rb = benchmark_returns[component]
                
                # Pure allocation effect
                allocation_effects[component] = (wp - wb) * (rb - benchmark_return)
                
                # Pure selection effect
                selection_effects[component] = wb * (rp - rb)
                
                # Interaction effect
                interaction_effects[component] = (wp - wb) * (rp - rb)
            
            # Aggregate effects
            result.allocation_effect = sum(allocation_effects.values())
            result.selection_effect = sum(selection_effects.values())
            result.interaction_effect = sum(interaction_effects.values())
            result.total_effect = result.allocation_effect + result.selection_effect + result.interaction_effect
            
            # Store component details
            result.component_weights = portfolio_weights.copy()
            result.component_returns = portfolio_returns.copy()
            result.benchmark_weights = benchmark_weights.copy()
            result.benchmark_returns = benchmark_returns.copy()
            
            # Calculate component contributions
            for component in all_components:
                total_contribution = (
                    allocation_effects[component] + 
                    selection_effects[component] + 
                    interaction_effects[component]
                )
                result.component_contributions[component] = total_contribution
            
            logger.debug(f"Calculated Brinson attribution: allocation={result.allocation_effect:.4f}, "
                        f"selection={result.selection_effect:.4f}, interaction={result.interaction_effect:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Brinson attribution calculation: {e}")
            return AttributionResult()
    
    def calculate_geometric_attribution(self, portfolio_weights: Dict[str, float],
                                      portfolio_returns: Dict[str, float],
                                      benchmark_weights: Dict[str, float],
                                      benchmark_returns: Dict[str, float]) -> AttributionResult:
        """Calculate geometric attribution (Brinson-Fachler method)"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.BRINSON_FACHLER,
                level=self.config.level
            )
            
            # Ensure all components are represented
            all_components = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
            
            # Fill missing weights/returns with zeros
            for component in all_components:
                if component not in portfolio_weights:
                    portfolio_weights[component] = 0.0
                if component not in portfolio_returns:
                    portfolio_returns[component] = 0.0
                if component not in benchmark_weights:
                    benchmark_weights[component] = 0.0
                if component not in benchmark_returns:
                    benchmark_returns[component] = 0.0
            
            # Calculate portfolio and benchmark returns
            portfolio_return = sum(
                portfolio_weights[c] * portfolio_returns[c] 
                for c in all_components
            )
            benchmark_return = sum(
                benchmark_weights[c] * benchmark_returns[c] 
                for c in all_components
            )
            
            # Geometric attribution effects
            allocation_effects = {}
            selection_effects = {}
            
            for component in all_components:
                wp = portfolio_weights[component]
                wb = benchmark_weights[component]
                rp = portfolio_returns[component]
                rb = benchmark_returns[component]
                
                # Geometric allocation effect
                allocation_effects[component] = (
                    (wp - wb) * rb / (1 + benchmark_return)
                )
                
                # Geometric selection effect
                selection_effects[component] = (
                    wb * (rp - rb) / (1 + rb)
                )
            
            # Aggregate effects
            result.allocation_effect = sum(allocation_effects.values())
            result.selection_effect = sum(selection_effects.values())
            result.interaction_effect = (
                (portfolio_return - benchmark_return) - 
                result.allocation_effect - result.selection_effect
            )
            result.total_effect = portfolio_return - benchmark_return
            
            # Store component details
            result.component_weights = portfolio_weights.copy()
            result.component_returns = portfolio_returns.copy()
            result.benchmark_weights = benchmark_weights.copy()
            result.benchmark_returns = benchmark_returns.copy()
            
            # Calculate component contributions
            for component in all_components:
                total_contribution = (
                    allocation_effects[component] + 
                    selection_effects[component]
                )
                result.component_contributions[component] = total_contribution
            
            logger.debug(f"Calculated geometric attribution: allocation={result.allocation_effect:.4f}, "
                        f"selection={result.selection_effect:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in geometric attribution calculation: {e}")
            return AttributionResult()


class FactorAttributionEngine:
    """Factor-based attribution analysis engine"""
    
    def __init__(self, config: AttributionConfig):
        self.config = config
        
        # Factor models
        self._factor_loadings: Dict[str, np.ndarray] = {}
        self._factor_returns: Dict[str, np.ndarray] = {}
        
        logger.info("Factor attribution engine initialized")
    
    def calculate_factor_attribution(self, portfolio_returns: np.ndarray,
                                   factor_exposures: Dict[str, np.ndarray],
                                   factor_returns: Dict[str, np.ndarray],
                                   specific_returns: Optional[np.ndarray] = None) -> AttributionResult:
        """Calculate factor-based attribution"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.RISK_ADJUSTED,
                level=AttributionLevel.FACTOR
            )
            
            # Validate inputs
            if len(portfolio_returns) == 0:
                logger.warning("Empty portfolio returns provided")
                return result
            
            # Calculate factor contributions
            factor_contributions = {}
            total_factor_contribution = 0.0
            
            for factor_name, exposures in factor_exposures.items():
                if factor_name in factor_returns:
                    # Calculate contribution of this factor
                    factor_rets = factor_returns[factor_name]
                    
                    if len(exposures) == len(factor_rets) == len(portfolio_returns):
                        contribution = np.mean(exposures * factor_rets)
                        factor_contributions[factor_name] = contribution
                        total_factor_contribution += contribution
            
            # Calculate specific return contribution
            if specific_returns is not None and len(specific_returns) == len(portfolio_returns):
                specific_contribution = np.mean(specific_returns)
                factor_contributions['specific'] = specific_contribution
            else:
                # Estimate specific return as residual
                total_return = np.mean(portfolio_returns)
                specific_contribution = total_return - total_factor_contribution
                factor_contributions['specific'] = specific_contribution
            
            # Store results
            result.component_contributions = factor_contributions
            result.total_effect = sum(factor_contributions.values())
            
            logger.debug(f"Calculated factor attribution with {len(factor_contributions)} factors")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in factor attribution calculation: {e}")
            return AttributionResult()
    
    def calculate_fama_french_attribution(self, portfolio_returns: np.ndarray,
                                        market_returns: np.ndarray,
                                        smb_returns: np.ndarray,
                                        hml_returns: np.ndarray,
                                        risk_free_rate: Optional[np.ndarray] = None) -> AttributionResult:
        """Calculate Fama-French 3-factor attribution"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.RISK_ADJUSTED,
                level=AttributionLevel.FACTOR
            )
            
            # Prepare excess returns
            if risk_free_rate is not None:
                excess_portfolio_returns = portfolio_returns - risk_free_rate
                excess_market_returns = market_returns - risk_free_rate
            else:
                excess_portfolio_returns = portfolio_returns
                excess_market_returns = market_returns
            
            # Prepare factor matrix
            X = np.column_stack([excess_market_returns, smb_returns, hml_returns])
            X = np.column_stack([np.ones(len(X)), X])  # Add intercept
            
            # Calculate factor loadings using regression
            try:
                betas = np.linalg.lstsq(X, excess_portfolio_returns, rcond=None)[0]
                alpha, market_beta, smb_beta, hml_beta = betas
            except np.linalg.LinAlgError:
                logger.warning("Failed to calculate factor loadings")
                return result
            
            # Calculate factor contributions
            factor_contributions = {
                'alpha': alpha,
                'market': market_beta * np.mean(excess_market_returns),
                'size': smb_beta * np.mean(smb_returns),
                'value': hml_beta * np.mean(hml_returns)
            }
            
            # Calculate explained and unexplained returns
            predicted_returns = (
                alpha + 
                market_beta * excess_market_returns + 
                smb_beta * smb_returns + 
                hml_beta * hml_returns
            )
            residuals = excess_portfolio_returns - predicted_returns
            factor_contributions['specific'] = np.mean(residuals)
            
            result.component_contributions = factor_contributions
            result.total_effect = sum(factor_contributions.values())
            
            # Store factor loadings as risk contributions
            result.risk_contributions = {
                'market_beta': market_beta,
                'size_beta': smb_beta,
                'value_beta': hml_beta
            }
            
            logger.debug(f"Calculated Fama-French attribution: alpha={alpha:.4f}, "
                        f"market={factor_contributions['market']:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Fama-French attribution calculation: {e}")
            return AttributionResult()
    
    def add_factor_data(self, factor_name: str, 
                       factor_returns: np.ndarray,
                       factor_loadings: Optional[np.ndarray] = None) -> None:
        """Add factor data for attribution analysis"""
        
        self._factor_returns[factor_name] = factor_returns
        
        if factor_loadings is not None:
            self._factor_loadings[factor_name] = factor_loadings
        
        logger.info(f"Added factor data for {factor_name}")


class RiskAttributionEngine:
    """Risk-based attribution analysis engine"""
    
    def __init__(self, config: AttributionConfig):
        self.config = config
        
        logger.info("Risk attribution engine initialized")
    
    def calculate_risk_attribution(self, portfolio_weights: np.ndarray,
                                 factor_exposures: np.ndarray,
                                 factor_covariance: np.ndarray,
                                 specific_risk: Optional[np.ndarray] = None) -> AttributionResult:
        """Calculate risk attribution"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.RISK_ADJUSTED,
                level=AttributionLevel.FACTOR
            )
            
            # Calculate portfolio factor exposures
            portfolio_exposures = portfolio_weights @ factor_exposures
            
            # Calculate factor risk contributions
            factor_risk_contrib = {}
            
            # Factor contribution to portfolio variance
            factor_variance = portfolio_exposures @ factor_covariance @ portfolio_exposures.T
            
            # Individual factor contributions
            for i, factor_name in enumerate([f"factor_{j}" for j in range(len(portfolio_exposures))]):
                # Marginal contribution to risk
                marginal_contrib = 2 * portfolio_exposures[i] * (factor_covariance[i, :] @ portfolio_exposures)
                factor_risk_contrib[factor_name] = marginal_contrib
            
            # Specific risk contribution
            if specific_risk is not None:
                specific_variance = np.sum(portfolio_weights**2 * specific_risk**2)
                factor_risk_contrib['specific'] = specific_variance
            
            # Normalize contributions
            total_risk = sum(factor_risk_contrib.values())
            if total_risk > 0:
                for factor in factor_risk_contrib:
                    factor_risk_contrib[factor] /= total_risk
            
            result.risk_contributions = factor_risk_contrib
            result.volatility_attribution = factor_risk_contrib.copy()
            
            logger.debug(f"Calculated risk attribution with {len(factor_risk_contrib)} factors")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in risk attribution calculation: {e}")
            return AttributionResult()
    
    def calculate_component_var_attribution(self, portfolio_weights: np.ndarray,
                                          component_returns: np.ndarray,
                                          confidence_level: float = 0.05) -> AttributionResult:
        """Calculate component VaR attribution"""
        
        try:
            result = AttributionResult(
                method=AttributionMethod.RISK_ADJUSTED,
                level=AttributionLevel.SECURITY
            )
            
            # Calculate portfolio returns
            portfolio_returns = component_returns @ portfolio_weights
            
            # Calculate portfolio VaR
            portfolio_var = np.percentile(portfolio_returns, confidence_level * 100)
            
            # Calculate component VaR contributions
            var_contributions = {}
            
            for i, component in enumerate([f"component_{j}" for j in range(len(portfolio_weights))]):
                # Calculate marginal VaR
                weight_perturbation = 0.001  # 0.1% perturbation
                
                # Perturbed weights
                perturbed_weights = portfolio_weights.copy()
                perturbed_weights[i] += weight_perturbation
                perturbed_weights /= np.sum(perturbed_weights)  # Renormalize
                
                # Perturbed portfolio returns
                perturbed_returns = component_returns @ perturbed_weights
                perturbed_var = np.percentile(perturbed_returns, confidence_level * 100)
                
                # Marginal VaR
                marginal_var = (perturbed_var - portfolio_var) / weight_perturbation
                
                # Component VaR contribution
                var_contributions[component] = portfolio_weights[i] * marginal_var
            
            result.risk_contributions = var_contributions
            
            logger.debug(f"Calculated component VaR attribution with {len(var_contributions)} components")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in component VaR attribution calculation: {e}")
            return AttributionResult()


class AttributionEngine:
    """
    Comprehensive Attribution Engine
    
    Provides advanced performance attribution analysis including
    Brinson attribution, factor attribution, and risk attribution.
    """
    
    def __init__(self, config: Optional[AttributionConfig] = None):
        """Initialize attribution engine"""
        
        self.config = config or AttributionConfig()
        
        # Attribution engines
        self._brinson_engine = BrinsonAttributionEngine(self.config)
        self._factor_engine = FactorAttributionEngine(self.config)
        self._risk_engine = RiskAttributionEngine(self.config)
        
        # Attribution history
        self._attribution_history: Dict[str, List[AttributionResult]] = defaultdict(list)
        
        # Performance tracking
        self._calculation_stats = {
            'total_calculations': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'last_calculation_time': None
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Attribution engine initialized")
    
    def calculate_brinson_attribution(self, portfolio_weights: Dict[str, float],
                                    portfolio_returns: Dict[str, float],
                                    benchmark_weights: Dict[str, float],
                                    benchmark_returns: Dict[str, float],
                                    method: AttributionMethod = AttributionMethod.BRINSON) -> AttributionResult:
        """Calculate Brinson attribution analysis"""
        
        try:
            with self._lock:
                self._calculation_stats['total_calculations'] += 1
                
                # Choose calculation method
                if method == AttributionMethod.BRINSON_FACHLER:
                    result = self._brinson_engine.calculate_geometric_attribution(
                        portfolio_weights, portfolio_returns,
                        benchmark_weights, benchmark_returns
                    )
                else:
                    result = self._brinson_engine.calculate_attribution(
                        portfolio_weights, portfolio_returns,
                        benchmark_weights, benchmark_returns
                    )
                
                # Store in history
                self._attribution_history['brinson'].append(result)
                
                self._calculation_stats['successful_calculations'] += 1
                self._calculation_stats['last_calculation_time'] = datetime.now()
                
                logger.info(f"Calculated Brinson attribution: total_effect={result.total_effect:.4f}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error in Brinson attribution calculation: {e}")
            self._calculation_stats['failed_calculations'] += 1
            return AttributionResult()
    
    def calculate_factor_attribution(self, portfolio_returns: Union[pd.Series, np.ndarray],
                                   factor_exposures: Dict[str, Union[pd.Series, np.ndarray]],
                                   factor_returns: Dict[str, Union[pd.Series, np.ndarray]],
                                   specific_returns: Optional[Union[pd.Series, np.ndarray]] = None) -> AttributionResult:
        """Calculate factor attribution analysis"""
        
        try:
            with self._lock:
                self._calculation_stats['total_calculations'] += 1
                
                # Convert to numpy arrays
                if isinstance(portfolio_returns, pd.Series):
                    portfolio_returns = portfolio_returns.values
                
                factor_exposures_array = {}
                for name, data in factor_exposures.items():
                    if isinstance(data, pd.Series):
                        factor_exposures_array[name] = data.values
                    else:
                        factor_exposures_array[name] = data
                
                factor_returns_array = {}
                for name, data in factor_returns.items():
                    if isinstance(data, pd.Series):
                        factor_returns_array[name] = data.values
                    else:
                        factor_returns_array[name] = data
                
                specific_returns_array = None
                if specific_returns is not None:
                    if isinstance(specific_returns, pd.Series):
                        specific_returns_array = specific_returns.values
                    else:
                        specific_returns_array = specific_returns
                
                result = self._factor_engine.calculate_factor_attribution(
                    portfolio_returns, factor_exposures_array,
                    factor_returns_array, specific_returns_array
                )
                
                # Store in history
                self._attribution_history['factor'].append(result)
                
                self._calculation_stats['successful_calculations'] += 1
                self._calculation_stats['last_calculation_time'] = datetime.now()
                
                logger.info(f"Calculated factor attribution with {len(result.component_contributions)} factors")
                
                return result
                
        except Exception as e:
            logger.error(f"Error in factor attribution calculation: {e}")
            self._calculation_stats['failed_calculations'] += 1
            return AttributionResult()
    
    def calculate_fama_french_attribution(self, portfolio_returns: Union[pd.Series, np.ndarray],
                                        market_returns: Union[pd.Series, np.ndarray],
                                        smb_returns: Union[pd.Series, np.ndarray],
                                        hml_returns: Union[pd.Series, np.ndarray],
                                        risk_free_rate: Optional[Union[pd.Series, np.ndarray]] = None) -> AttributionResult:
        """Calculate Fama-French 3-factor attribution"""
        
        try:
            with self._lock:
                self._calculation_stats['total_calculations'] += 1
                
                # Convert to numpy arrays
                portfolio_ret_array = portfolio_returns.values if isinstance(portfolio_returns, pd.Series) else portfolio_returns
                market_ret_array = market_returns.values if isinstance(market_returns, pd.Series) else market_returns
                smb_ret_array = smb_returns.values if isinstance(smb_returns, pd.Series) else smb_returns
                hml_ret_array = hml_returns.values if isinstance(hml_returns, pd.Series) else hml_returns
                
                rf_array = None
                if risk_free_rate is not None:
                    rf_array = risk_free_rate.values if isinstance(risk_free_rate, pd.Series) else risk_free_rate
                
                result = self._factor_engine.calculate_fama_french_attribution(
                    portfolio_ret_array, market_ret_array, smb_ret_array, hml_ret_array, rf_array
                )
                
                # Store in history
                self._attribution_history['fama_french'].append(result)
                
                self._calculation_stats['successful_calculations'] += 1
                self._calculation_stats['last_calculation_time'] = datetime.now()
                
                logger.info(f"Calculated Fama-French attribution: alpha={result.component_contributions.get('alpha', 0):.4f}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error in Fama-French attribution calculation: {e}")
            self._calculation_stats['failed_calculations'] += 1
            return AttributionResult()
    
    def calculate_risk_attribution(self, portfolio_weights: Union[pd.Series, np.ndarray],
                                 factor_exposures: Union[pd.DataFrame, np.ndarray],
                                 factor_covariance: Union[pd.DataFrame, np.ndarray],
                                 specific_risk: Optional[Union[pd.Series, np.ndarray]] = None) -> AttributionResult:
        """Calculate risk attribution analysis"""
        
        try:
            with self._lock:
                self._calculation_stats['total_calculations'] += 1
                
                # Convert to numpy arrays
                weights_array = portfolio_weights.values if isinstance(portfolio_weights, pd.Series) else portfolio_weights
                exposures_array = factor_exposures.values if isinstance(factor_exposures, pd.DataFrame) else factor_exposures
                covariance_array = factor_covariance.values if isinstance(factor_covariance, pd.DataFrame) else factor_covariance
                
                specific_risk_array = None
                if specific_risk is not None:
                    specific_risk_array = specific_risk.values if isinstance(specific_risk, pd.Series) else specific_risk
                
                result = self._risk_engine.calculate_risk_attribution(
                    weights_array, exposures_array, covariance_array, specific_risk_array
                )
                
                # Store in history
                self._attribution_history['risk'].append(result)
                
                self._calculation_stats['successful_calculations'] += 1
                self._calculation_stats['last_calculation_time'] = datetime.now()
                
                logger.info(f"Calculated risk attribution with {len(result.risk_contributions)} factors")
                
                return result
                
        except Exception as e:
            logger.error(f"Error in risk attribution calculation: {e}")
            self._calculation_stats['failed_calculations'] += 1
            return AttributionResult()
    
    def calculate_multi_period_attribution(self, attribution_results: List[AttributionResult],
                                         linking_method: str = "geometric") -> AttributionResult:
        """Calculate multi-period attribution linking"""
        
        try:
            if not attribution_results:
                return AttributionResult()
            
            linked_result = AttributionResult()
            
            if linking_method == "geometric":
                # Geometric linking
                total_allocation = 1.0
                total_selection = 1.0
                total_interaction = 1.0
                
                for result in attribution_results:
                    total_allocation *= (1 + result.allocation_effect)
                    total_selection *= (1 + result.selection_effect)
                    total_interaction *= (1 + result.interaction_effect)
                
                linked_result.allocation_effect = total_allocation - 1
                linked_result.selection_effect = total_selection - 1
                linked_result.interaction_effect = total_interaction - 1
                
            else:
                # Arithmetic linking
                linked_result.allocation_effect = sum(r.allocation_effect for r in attribution_results)
                linked_result.selection_effect = sum(r.selection_effect for r in attribution_results)
                linked_result.interaction_effect = sum(r.interaction_effect for r in attribution_results)
            
            linked_result.total_effect = (
                linked_result.allocation_effect + 
                linked_result.selection_effect + 
                linked_result.interaction_effect
            )
            
            # Aggregate component contributions
            all_components = set()
            for result in attribution_results:
                all_components.update(result.component_contributions.keys())
            
            for component in all_components:
                component_contrib = sum(
                    result.component_contributions.get(component, 0) 
                    for result in attribution_results
                )
                linked_result.component_contributions[component] = component_contrib
            
            logger.info(f"Calculated multi-period attribution linking for {len(attribution_results)} periods")
            
            return linked_result
            
        except Exception as e:
            logger.error(f"Error in multi-period attribution linking: {e}")
            return AttributionResult()
    
    def get_attribution_summary(self, attribution_type: str = "all") -> Dict[str, Any]:
        """Get attribution analysis summary"""
        
        try:
            with self._lock:
                summary = {
                    'calculation_stats': self._calculation_stats.copy(),
                    'config': {
                        'method': self.config.method.value,
                        'level': self.config.level.value,
                        'frequency': self.config.frequency,
                        'base_currency': self.config.base_currency
                    }
                }
                
                if attribution_type == "all" or attribution_type == "brinson":
                    brinson_results = self._attribution_history.get('brinson', [])
                    if brinson_results:
                        latest_brinson = brinson_results[-1]
                        summary['latest_brinson'] = {
                            'allocation_effect': latest_brinson.allocation_effect,
                            'selection_effect': latest_brinson.selection_effect,
                            'interaction_effect': latest_brinson.interaction_effect,
                            'total_effect': latest_brinson.total_effect,
                            'calculation_time': latest_brinson.calculation_time
                        }
                        summary['brinson_history_count'] = len(brinson_results)
                
                if attribution_type == "all" or attribution_type == "factor":
                    factor_results = self._attribution_history.get('factor', [])
                    if factor_results:
                        latest_factor = factor_results[-1]
                        summary['latest_factor'] = {
                            'component_contributions': latest_factor.component_contributions,
                            'total_effect': latest_factor.total_effect,
                            'calculation_time': latest_factor.calculation_time
                        }
                        summary['factor_history_count'] = len(factor_results)
                
                if attribution_type == "all" or attribution_type == "risk":
                    risk_results = self._attribution_history.get('risk', [])
                    if risk_results:
                        latest_risk = risk_results[-1]
                        summary['latest_risk'] = {
                            'risk_contributions': latest_risk.risk_contributions,
                            'volatility_attribution': latest_risk.volatility_attribution,
                            'calculation_time': latest_risk.calculation_time
                        }
                        summary['risk_history_count'] = len(risk_results)
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting attribution summary: {e}")
            return {}
    
    def clear_attribution_history(self, attribution_type: Optional[str] = None) -> None:
        """Clear attribution history"""
        
        with self._lock:
            if attribution_type:
                self._attribution_history.pop(attribution_type, None)
                logger.info(f"Cleared {attribution_type} attribution history")
            else:
                self._attribution_history.clear()
                logger.info("Cleared all attribution history")
    
    def export_attribution_results(self, attribution_type: str, 
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export attribution results to DataFrame"""
        
        try:
            results = self._attribution_history.get(attribution_type, [])
            
            if not results:
                return pd.DataFrame()
            
            # Filter by date if specified
            if start_date or end_date:
                filtered_results = []
                for result in results:
                    calc_time = result.calculation_time
                    if start_date and calc_time < start_date:
                        continue
                    if end_date and calc_time > end_date:
                        continue
                    filtered_results.append(result)
                results = filtered_results
            
            # Convert to DataFrame
            export_data = []
            for result in results:
                row = {
                    'calculation_time': result.calculation_time,
                    'allocation_effect': result.allocation_effect,
                    'selection_effect': result.selection_effect,
                    'interaction_effect': result.interaction_effect,
                    'total_effect': result.total_effect,
                    'method': result.method.value,
                    'level': result.level.value
                }
                
                # Add component contributions as separate columns
                for component, contribution in result.component_contributions.items():
                    row[f'contrib_{component}'] = contribution
                
                export_data.append(row)
            
            df = pd.DataFrame(export_data)
            df.set_index('calculation_time', inplace=True)
            
            logger.info(f"Exported {len(df)} {attribution_type} attribution results")
            
            return df
            
        except Exception as e:
            logger.error(f"Error exporting attribution results: {e}")
            return pd.DataFrame()