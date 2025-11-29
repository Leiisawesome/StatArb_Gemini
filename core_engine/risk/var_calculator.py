"""
Risk Management - VaR Calculator  
Value at Risk calculation using multiple methodologies with comprehensive risk metrics
"""

import logging
import threading
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque
from scipy import stats

from core_engine.exceptions import ConfigurationRequiredError
# Import canonical metric functions from core_metrics (Rule: Single Source of Truth)
from core_engine.analytics.core_metrics import calculate_max_drawdown, calculate_beta

logger = logging.getLogger(__name__)


class VarMethod(Enum):
    """VaR calculation methods"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"
    FILTERED_HISTORICAL = "filtered_historical"
    EVT = "extreme_value_theory"


class RiskMeasure(Enum):
    """Risk measure types"""
    VAR = "var"  # Value at Risk
    CVAR = "cvar"  # Conditional Value at Risk (Expected Shortfall)
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    BETA = "beta"
    TRACKING_ERROR = "tracking_error"


@dataclass
class VarResult:
    """VaR calculation result"""
    var_value: float
    confidence_level: float
    method: VarMethod
    time_horizon: int  # days
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_1d: Dict[float, float]  # confidence level -> VaR value
    cvar_1d: Dict[float, float]  # confidence level -> CVaR value
    volatility_daily: float
    volatility_annual: float
    max_drawdown: float
    beta: Optional[float] = None
    tracking_error: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StressTestScenario:
    """Stress test scenario definition"""
    name: str
    description: str
    factor_shocks: Dict[str, float]  # factor -> shock percentage
    correlation_changes: Optional[Dict[Tuple[str, str], float]] = None
    volatility_multipliers: Optional[Dict[str, float]] = None


class VarCalculator:
    """
    Comprehensive Value at Risk calculator
    
    Supports multiple VaR methodologies, risk metrics calculation,
    and stress testing capabilities for portfolio risk management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize VaR calculator"""
        self.config = config or {}
        self._lock = threading.Lock()
        self._price_cache = {}
        self._covariance_cache = {}
        self._calculation_history = deque(maxlen=1000)
        
        # Configuration parameters with proper defaults
        self.confidence_levels = self.config.get('confidence_levels', [0.95, 0.99, 0.999])
        if not self.confidence_levels:
            raise ConfigurationRequiredError("confidence_levels must be specified in VaR calculator config")
        
        self.time_horizon = self.config.get('time_horizon_days', 1)
        if not self.time_horizon or self.time_horizon <= 0:
            raise ConfigurationRequiredError("time_horizon_days must be specified and greater than 0")
        self.lookback_window = self.config.get('lookback_window_days', 252)  # 1 year
        self.min_observations = self.config.get('min_observations', 50)
        self.mc_simulations = self.config.get('monte_carlo_simulations', 10000)
        
        # Risk-free rate for Sharpe ratio calculations
        self.risk_free_rate = self.config.get('risk_free_rate_annual', 0.02)
        
        # Note: Stress testing is handled by StressTester class - no longer duplicated here
        
        logger.info("VarCalculator initialized")
    
    # Property aliases for backward compatibility with tests
    @property
    def default_confidence_levels(self) -> List[float]:
        """Alias for confidence_levels (backward compatibility)."""
        return self.confidence_levels
    
    @property
    def default_time_horizon(self) -> int:
        """Alias for time_horizon (backward compatibility)."""
        return self.time_horizon
    
    
    async def calculate_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        method: VarMethod = VarMethod.HISTORICAL,
        confidence_levels: Optional[List[float]] = None,
        time_horizon: int = 1
    ) -> Dict[float, VarResult]:
        """
        Calculate Value at Risk using specified method
        
        Args:
            returns: Return series or DataFrame of returns
            method: VaR calculation method
            confidence_levels: Confidence levels for VaR calculation
            time_horizon: Time horizon in days
            
        Returns:
            Dictionary mapping confidence levels to VaR results
        """
        if confidence_levels is None:
            confidence_levels = self.confidence_levels
        
        start_time = time.time()
        
        try:
            # Ensure we have enough data
            if len(returns) < self.min_observations:
                raise ValueError(f"Insufficient data: {len(returns)} < {self.min_observations}")
            
            # Calculate VaR based on method
            if method == VarMethod.HISTORICAL:
                var_results = await self._calculate_historical_var(returns, confidence_levels, time_horizon)
            elif method == VarMethod.PARAMETRIC:
                var_results = await self._calculate_parametric_var(returns, confidence_levels, time_horizon)
            elif method == VarMethod.MONTE_CARLO:
                var_results = await self._calculate_monte_carlo_var(returns, confidence_levels, time_horizon)
            elif method == VarMethod.CORNISH_FISHER:
                var_results = await self._calculate_cornish_fisher_var(returns, confidence_levels, time_horizon)
            elif method == VarMethod.FILTERED_HISTORICAL:
                var_results = await self._calculate_filtered_historical_var(returns, confidence_levels, time_horizon)
            else:
                raise ValueError(f"Unsupported VaR method: {method}")
            
            # Store calculation in history
            calculation_record = {
                'timestamp': datetime.now(),
                'method': method.value,
                'confidence_levels': confidence_levels,
                'time_horizon': time_horizon,
                'data_points': len(returns),
                'calculation_time': time.time() - start_time
            }
            self._calculation_history.append(calculation_record)
            
            logger.info(f"Calculated VaR using {method.value} in {time.time() - start_time:.3f}s")
            
            return var_results
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            raise
    
    async def _calculate_historical_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        confidence_levels: List[float],
        time_horizon: int
    ) -> Dict[float, VarResult]:
        """Calculate historical simulation VaR"""
        
        if isinstance(returns, pd.DataFrame):
            # For portfolio, calculate portfolio returns
            portfolio_returns = returns.sum(axis=1)
        else:
            portfolio_returns = returns
        
        # Scale returns for time horizon
        scaled_returns = portfolio_returns * np.sqrt(time_horizon)
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            quantile = 1 - confidence_level
            var_value = -np.percentile(scaled_returns, quantile * 100)
            
            var_results[confidence_level] = VarResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=VarMethod.HISTORICAL,
                time_horizon=time_horizon,
                metadata={
                    'quantile': quantile,
                    'data_points': len(scaled_returns)
                }
            )
        
        return var_results
    
    async def _calculate_parametric_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        confidence_levels: List[float],
        time_horizon: int
    ) -> Dict[float, VarResult]:
        """Calculate parametric (normal distribution) VaR"""
        
        if isinstance(returns, pd.DataFrame):
            portfolio_returns = returns.sum(axis=1)
        else:
            portfolio_returns = returns
        
        # Calculate mean and standard deviation
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        
        # Scale for time horizon
        scaled_mean = mean_return * time_horizon
        scaled_std = std_return * np.sqrt(time_horizon)
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            # Calculate z-score for confidence level
            z_score = stats.norm.ppf(1 - confidence_level)
            
            # Calculate VaR
            var_value = -(scaled_mean + z_score * scaled_std)
            
            var_results[confidence_level] = VarResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=VarMethod.PARAMETRIC,
                time_horizon=time_horizon,
                metadata={
                    'mean_return': mean_return,
                    'std_return': std_return,
                    'z_score': z_score
                }
            )
        
        return var_results
    
    async def _calculate_monte_carlo_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        confidence_levels: List[float],
        time_horizon: int
    ) -> Dict[float, VarResult]:
        """Calculate Monte Carlo simulation VaR"""
        
        if isinstance(returns, pd.DataFrame):
            portfolio_returns = returns.sum(axis=1)
        else:
            portfolio_returns = returns
        
        # Estimate distribution parameters
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        
        # Generate random simulations
        np.random.seed(42)  # For reproducibility
        simulated_returns = np.random.normal(
            mean_return * time_horizon,
            std_return * np.sqrt(time_horizon),
            self.mc_simulations
        )
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            quantile = 1 - confidence_level
            var_value = -np.percentile(simulated_returns, quantile * 100)
            
            var_results[confidence_level] = VarResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=VarMethod.MONTE_CARLO,
                time_horizon=time_horizon,
                metadata={
                    'simulations': self.mc_simulations,
                    'mean_return': mean_return,
                    'std_return': std_return
                }
            )
        
        return var_results
    
    async def _calculate_cornish_fisher_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        confidence_levels: List[float],
        time_horizon: int
    ) -> Dict[float, VarResult]:
        """Calculate Cornish-Fisher expansion VaR (accounts for skewness and kurtosis)"""
        
        if isinstance(returns, pd.DataFrame):
            portfolio_returns = returns.sum(axis=1)
        else:
            portfolio_returns = returns
        
        # Calculate moments
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        skewness = portfolio_returns.skew()
        kurtosis = portfolio_returns.kurtosis()  # Excess kurtosis
        
        # Scale for time horizon
        scaled_mean = mean_return * time_horizon
        scaled_std = std_return * np.sqrt(time_horizon)
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            # Standard normal quantile
            z = stats.norm.ppf(1 - confidence_level)
            
            # Cornish-Fisher adjustment
            z_cf = (z + 
                   (z**2 - 1) * skewness / 6 +
                   (z**3 - 3*z) * kurtosis / 24 -
                   (2*z**3 - 5*z) * skewness**2 / 36)
            
            # Calculate VaR
            var_value = -(scaled_mean + z_cf * scaled_std)
            
            var_results[confidence_level] = VarResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=VarMethod.CORNISH_FISHER,
                time_horizon=time_horizon,
                metadata={
                    'mean_return': mean_return,
                    'std_return': std_return,
                    'skewness': skewness,
                    'kurtosis': kurtosis,
                    'z_adjustment': z_cf
                }
            )
        
        return var_results
    
    async def _calculate_filtered_historical_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        confidence_levels: List[float],
        time_horizon: int
    ) -> Dict[float, VarResult]:
        """Calculate filtered historical simulation VaR (with volatility weighting)"""
        
        if isinstance(returns, pd.DataFrame):
            portfolio_returns = returns.sum(axis=1)
        else:
            portfolio_returns = returns
        
        # Calculate exponentially weighted volatility
        lambda_factor = 0.94  # Decay factor
        weights = np.array([(lambda_factor ** i) for i in range(len(portfolio_returns))])
        weights = weights[::-1]  # Reverse to give more weight to recent obs
        weights = weights / weights.sum()
        
        # Weight the returns
        weighted_returns = portfolio_returns * np.sqrt(weights[-len(portfolio_returns):])
        
        # Scale for time horizon
        scaled_returns = weighted_returns * np.sqrt(time_horizon)
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            quantile = 1 - confidence_level
            var_value = -np.percentile(scaled_returns, quantile * 100)
            
            var_results[confidence_level] = VarResult(
                var_value=var_value,
                confidence_level=confidence_level,
                method=VarMethod.FILTERED_HISTORICAL,
                time_horizon=time_horizon,
                metadata={
                    'lambda_factor': lambda_factor,
                    'weighted_observations': len(weighted_returns)
                }
            )
        
        return var_results
    
    async def calculate_comprehensive_risk_metrics(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        benchmark_returns: Optional[pd.Series] = None
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for portfolio"""
        
        start_time = time.time()
        
        try:
            if isinstance(returns, pd.DataFrame):
                portfolio_returns = returns.sum(axis=1)
            else:
                portfolio_returns = returns
            
            # Calculate VaR and CVaR for multiple confidence levels
            var_1d = {}
            cvar_1d = {}
            
            for confidence_level in self.confidence_levels:
                # Historical VaR
                quantile = 1 - confidence_level
                var_value = -np.percentile(portfolio_returns, quantile * 100)
                var_1d[confidence_level] = var_value
                
                # Conditional VaR (Expected Shortfall)
                tail_returns = portfolio_returns[portfolio_returns <= -var_value]
                cvar_value = -tail_returns.mean() if len(tail_returns) > 0 else var_value
                cvar_1d[confidence_level] = cvar_value
            
            # Volatility calculations
            volatility_daily = portfolio_returns.std()
            volatility_annual = volatility_daily * np.sqrt(252)
            
            # Maximum drawdown - using canonical core_metrics function
            max_drawdown = calculate_max_drawdown(portfolio_returns)
            
            # Beta calculation (if benchmark provided) - using canonical core_metrics function
            beta = None
            tracking_error = None
            if benchmark_returns is not None:
                beta = calculate_beta(portfolio_returns.values, benchmark_returns.values)
                tracking_error = (portfolio_returns - benchmark_returns).std() * np.sqrt(252)
            
            # Sharpe and Sortino ratios
            excess_returns = portfolio_returns - self.risk_free_rate / 252
            sharpe_ratio = excess_returns.mean() / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
            
            downside_returns = portfolio_returns[portfolio_returns < 0]
            sortino_ratio = (excess_returns.mean() / downside_returns.std() * np.sqrt(252) 
                           if len(downside_returns) > 0 and downside_returns.std() > 0 else 0)
            
            # Higher moments
            skewness = portfolio_returns.skew()
            kurtosis = portfolio_returns.kurtosis()
            
            risk_metrics = RiskMetrics(
                var_1d=var_1d,
                cvar_1d=cvar_1d,
                volatility_daily=volatility_daily,
                volatility_annual=volatility_annual,
                max_drawdown=max_drawdown,
                beta=beta,
                tracking_error=tracking_error,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                skewness=skewness,
                kurtosis=kurtosis
            )
            
            logger.info(f"Calculated comprehensive risk metrics in {time.time() - start_time:.3f}s")
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            raise
    
    # NOTE: _calculate_max_drawdown and _calculate_beta removed
    # Now using canonical functions from core_engine.analytics.core_metrics
    # This eliminates code duplication across the codebase
    
    def get_calculation_history(self) -> List[Dict[str, Any]]:
        """Get VaR calculation history"""
        with self._lock:
            return list(self._calculation_history)
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        logger.info("VarCalculator cleanup completed")