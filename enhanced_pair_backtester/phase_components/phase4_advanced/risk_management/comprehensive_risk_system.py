"""
Comprehensive Risk Management System
===================================

This module implements a comprehensive risk management system for multi-strategy
quantitative trading, providing real-time risk monitoring, Value-at-Risk (VaR),
stress testing, scenario analysis, and automated risk controls.

Key Features:
- Real-time risk monitoring and alerting
- Value-at-Risk (VaR) and Expected Shortfall (ES) calculations
- Stress testing and scenario analysis
- Factor risk decomposition
- Correlation risk monitoring
- Liquidity risk assessment
- Dynamic risk limits and controls
- Risk attribution and reporting

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sqlite3
import threading
import time
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict

# Statistical and risk libraries
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.covariance import EmpiricalCovariance, MinCovDet
from sklearn.ensemble import IsolationForest
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RiskMetricType(Enum):
    """Types of risk metrics"""
    VALUE_AT_RISK = "VALUE_AT_RISK"
    EXPECTED_SHORTFALL = "EXPECTED_SHORTFALL"
    MAXIMUM_DRAWDOWN = "MAXIMUM_DRAWDOWN"
    VOLATILITY = "VOLATILITY"
    BETA = "BETA"
    TRACKING_ERROR = "TRACKING_ERROR"
    INFORMATION_RATIO = "INFORMATION_RATIO"
    SHARPE_RATIO = "SHARPE_RATIO"
    CALMAR_RATIO = "CALMAR_RATIO"
    CORRELATION_RISK = "CORRELATION_RISK"
    CONCENTRATION_RISK = "CONCENTRATION_RISK"
    LIQUIDITY_RISK = "LIQUIDITY_RISK"

class RiskLevel(Enum):
    """Risk alert levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EXTREME = "EXTREME"

class StressTestType(Enum):
    """Types of stress tests"""
    HISTORICAL_SCENARIO = "HISTORICAL_SCENARIO"
    MONTE_CARLO = "MONTE_CARLO"
    FACTOR_SHOCK = "FACTOR_SHOCK"
    CORRELATION_BREAKDOWN = "CORRELATION_BREAKDOWN"
    VOLATILITY_SHOCK = "VOLATILITY_SHOCK"
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"
    BLACK_SWAN = "BLACK_SWAN"
    CUSTOM_SCENARIO = "CUSTOM_SCENARIO"

class RiskLimitType(Enum):
    """Types of risk limits"""
    PORTFOLIO_VAR = "PORTFOLIO_VAR"
    PORTFOLIO_VOLATILITY = "PORTFOLIO_VOLATILITY"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    POSITION_SIZE = "POSITION_SIZE"
    SECTOR_CONCENTRATION = "SECTOR_CONCENTRATION"
    FACTOR_EXPOSURE = "FACTOR_EXPOSURE"
    CORRELATION_LIMIT = "CORRELATION_LIMIT"
    LEVERAGE = "LEVERAGE"

@dataclass
class RiskMetric:
    """Individual risk metric"""
    metric_type: RiskMetricType
    value: float
    timestamp: datetime
    
    # Confidence levels for VaR/ES
    confidence_level: Optional[float] = None
    
    # Time horizon
    time_horizon: int = 1  # Days
    
    # Risk attribution
    component_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Historical context
    percentile_rank: Optional[float] = None
    historical_average: Optional[float] = None
    
    # Alert information
    risk_level: RiskLevel = RiskLevel.LOW
    threshold_breached: bool = False

@dataclass
class StressTestResult:
    """Stress test result"""
    test_id: str
    test_type: StressTestType
    scenario_name: str
    timestamp: datetime
    
    # Test parameters
    test_parameters: Dict[str, Any]
    
    # Results
    portfolio_pnl: float
    portfolio_return: float
    worst_case_loss: float
    
    # Component results
    component_pnl: Dict[str, float]
    component_returns: Dict[str, float]
    
    # Risk metrics under stress
    stressed_var: float
    stressed_volatility: float
    
    # Scenario details
    scenario_description: str
    probability_estimate: Optional[float] = None

@dataclass
class RiskLimit:
    """Risk limit definition"""
    limit_id: str
    limit_type: RiskLimitType
    limit_value: float
    
    # Scope
    applies_to: str  # 'PORTFOLIO', asset name, or sector
    
    # Alert thresholds
    warning_threshold: float  # Percentage of limit (e.g., 0.8 for 80%)
    breach_threshold: float = 1.0  # 100% of limit
    
    # Current status
    current_value: float = 0.0
    utilization: float = 0.0  # Percentage of limit used
    
    # Breach tracking
    last_breach: Optional[datetime] = None
    breach_count: int = 0
    
    # Action on breach
    auto_action: Optional[str] = None  # 'REDUCE_POSITION', 'HEDGE', 'ALERT_ONLY'

@dataclass
class RiskAlert:
    """Risk alert"""
    alert_id: str
    timestamp: datetime
    risk_level: RiskLevel
    
    # Alert details
    metric_type: RiskMetricType
    current_value: float
    threshold_value: float
    breach_magnitude: float
    
    # Context
    affected_positions: List[str]
    recommended_actions: List[str]
    
    # Alert lifecycle
    acknowledged: bool = False
    resolved: bool = False
    resolution_time: Optional[datetime] = None

@dataclass
class RiskReport:
    """Comprehensive risk report"""
    report_id: str
    timestamp: datetime
    
    # Portfolio overview
    portfolio_value: float
    portfolio_return: float
    portfolio_volatility: float
    
    # Risk metrics
    risk_metrics: Dict[RiskMetricType, RiskMetric]
    
    # Stress test results
    stress_test_results: List[StressTestResult]
    
    # Risk limits status
    risk_limits_status: Dict[str, RiskLimit]
    
    # Active alerts
    active_alerts: List[RiskAlert]
    
    # Risk attribution
    risk_attribution: Dict[str, float]
    
    # Recommendations
    risk_recommendations: List[str]

class VaRCalculator:
    """Value-at-Risk calculator with multiple methodologies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confidence_levels = config.get('confidence_levels', [0.95, 0.99, 0.995])
        self.time_horizons = config.get('time_horizons', [1, 5, 10])  # Days
        self.methods = config.get('methods', ['HISTORICAL', 'PARAMETRIC', 'MONTE_CARLO'])
    
    def calculate_var(self, returns: pd.DataFrame, 
                     weights: Dict[str, float],
                     confidence_level: float = 0.95,
                     time_horizon: int = 1,
                     method: str = 'HISTORICAL') -> Dict[str, Any]:
        """Calculate Value-at-Risk using specified method"""
        try:
            # Align weights with returns
            common_assets = set(returns.columns) & set(weights.keys())
            if not common_assets:
                raise ValueError("No common assets between returns and weights")
            
            aligned_returns = returns[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Calculate portfolio returns
            portfolio_returns = (aligned_returns * aligned_weights).sum(axis=1)
            
            if method == 'HISTORICAL':
                var_value = self._historical_var(portfolio_returns, confidence_level, time_horizon)
            elif method == 'PARAMETRIC':
                var_value = self._parametric_var(portfolio_returns, confidence_level, time_horizon)
            elif method == 'MONTE_CARLO':
                var_value = self._monte_carlo_var(aligned_returns, aligned_weights, confidence_level, time_horizon)
            else:
                raise ValueError(f"Unknown VaR method: {method}")
            
            # Calculate Expected Shortfall (Conditional VaR)
            es_value = self._calculate_expected_shortfall(portfolio_returns, confidence_level, time_horizon)
            
            # Component VaR
            component_var = self._calculate_component_var(
                aligned_returns, aligned_weights, confidence_level, time_horizon
            )
            
            return {
                'var': var_value,
                'expected_shortfall': es_value,
                'confidence_level': confidence_level,
                'time_horizon': time_horizon,
                'method': method,
                'component_var': component_var,
                'portfolio_volatility': portfolio_returns.std() * np.sqrt(252),
                'portfolio_return': portfolio_returns.mean() * 252
            }
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return {
                'var': 0.0,
                'expected_shortfall': 0.0,
                'confidence_level': confidence_level,
                'time_horizon': time_horizon,
                'method': method,
                'component_var': {},
                'portfolio_volatility': 0.0,
                'portfolio_return': 0.0
            }
    
    def _historical_var(self, returns: pd.Series, confidence_level: float, time_horizon: int) -> float:
        """Calculate historical VaR"""
        # Scale returns for time horizon
        scaled_returns = returns * np.sqrt(time_horizon)
        
        # Calculate percentile
        var_percentile = (1 - confidence_level) * 100
        var_value = np.percentile(scaled_returns, var_percentile)
        
        return -var_value  # Return as positive loss
    
    def _parametric_var(self, returns: pd.Series, confidence_level: float, time_horizon: int) -> float:
        """Calculate parametric VaR assuming normal distribution"""
        # Calculate mean and standard deviation
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Scale for time horizon
        scaled_mean = mean_return * time_horizon
        scaled_std = std_return * np.sqrt(time_horizon)
        
        # Calculate VaR using normal distribution
        z_score = stats.norm.ppf(1 - confidence_level)
        var_value = -(scaled_mean + z_score * scaled_std)
        
        return var_value
    
    def _monte_carlo_var(self, returns: pd.DataFrame, weights: np.ndarray, 
                        confidence_level: float, time_horizon: int, 
                        n_simulations: int = 10000) -> float:
        """Calculate Monte Carlo VaR"""
        try:
            # Estimate covariance matrix
            cov_matrix = returns.cov().values
            mean_returns = returns.mean().values
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            random_returns = np.random.multivariate_normal(
                mean_returns, cov_matrix, n_simulations
            )
            
            # Scale for time horizon
            scaled_returns = random_returns * np.sqrt(time_horizon)
            
            # Calculate portfolio returns for each scenario
            portfolio_returns = np.dot(scaled_returns, weights)
            
            # Calculate VaR
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(portfolio_returns, var_percentile)
            
            return -var_value
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo VaR: {e}")
            return self._parametric_var(
                (returns * weights).sum(axis=1), confidence_level, time_horizon
            )
    
    def _calculate_expected_shortfall(self, returns: pd.Series, 
                                    confidence_level: float, 
                                    time_horizon: int) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        # Scale returns for time horizon
        scaled_returns = returns * np.sqrt(time_horizon)
        
        # Calculate VaR threshold
        var_threshold = np.percentile(scaled_returns, (1 - confidence_level) * 100)
        
        # Calculate expected shortfall as mean of returns below VaR
        tail_returns = scaled_returns[scaled_returns <= var_threshold]
        
        if len(tail_returns) > 0:
            es_value = -tail_returns.mean()
        else:
            es_value = -var_threshold
        
        return es_value
    
    def _calculate_component_var(self, returns: pd.DataFrame, weights: np.ndarray,
                               confidence_level: float, time_horizon: int) -> Dict[str, float]:
        """Calculate component VaR for each asset"""
        try:
            component_var = {}
            
            # Calculate portfolio VaR
            portfolio_returns = (returns * weights).sum(axis=1)
            portfolio_var = self._historical_var(portfolio_returns, confidence_level, time_horizon)
            
            # Calculate marginal VaR for each asset
            for i, asset in enumerate(returns.columns):
                # Small perturbation
                epsilon = 0.001
                perturbed_weights = weights.copy()
                perturbed_weights[i] += epsilon
                perturbed_weights = perturbed_weights / perturbed_weights.sum()  # Renormalize
                
                # Calculate perturbed portfolio VaR
                perturbed_returns = (returns * perturbed_weights).sum(axis=1)
                perturbed_var = self._historical_var(perturbed_returns, confidence_level, time_horizon)
                
                # Marginal VaR
                marginal_var = (perturbed_var - portfolio_var) / epsilon
                
                # Component VaR
                component_var[asset] = weights[i] * marginal_var
            
            return component_var
            
        except Exception as e:
            logger.error(f"Error calculating component VaR: {e}")
            return {}

class StressTester:
    """Comprehensive stress testing system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.historical_scenarios = config.get('historical_scenarios', {})
        self.monte_carlo_params = config.get('monte_carlo_params', {})
        
        # Default historical scenarios
        if not self.historical_scenarios:
            self._initialize_default_scenarios()
    
    def _initialize_default_scenarios(self):
        """Initialize default historical stress scenarios"""
        self.historical_scenarios = {
            'BLACK_MONDAY_1987': {
                'date': '1987-10-19',
                'description': 'Black Monday market crash',
                'market_shock': -0.22,
                'volatility_multiplier': 3.0
            },
            'DOTCOM_CRASH_2000': {
                'date': '2000-03-10',
                'description': 'Dot-com bubble burst',
                'market_shock': -0.15,
                'volatility_multiplier': 2.5
            },
            'FINANCIAL_CRISIS_2008': {
                'date': '2008-10-15',
                'description': 'Lehman Brothers collapse',
                'market_shock': -0.18,
                'volatility_multiplier': 4.0
            },
            'FLASH_CRASH_2010': {
                'date': '2010-05-06',
                'description': 'Flash crash',
                'market_shock': -0.09,
                'volatility_multiplier': 5.0
            },
            'COVID_CRASH_2020': {
                'date': '2020-03-16',
                'description': 'COVID-19 market crash',
                'market_shock': -0.12,
                'volatility_multiplier': 3.5
            }
        }
    
    def run_stress_test(self, returns: pd.DataFrame, 
                       weights: Dict[str, float],
                       test_type: StressTestType,
                       scenario_params: Optional[Dict[str, Any]] = None) -> StressTestResult:
        """Run stress test with specified parameters"""
        try:
            if test_type == StressTestType.HISTORICAL_SCENARIO:
                return self._historical_scenario_test(returns, weights, scenario_params)
            elif test_type == StressTestType.MONTE_CARLO:
                return self._monte_carlo_stress_test(returns, weights, scenario_params)
            elif test_type == StressTestType.FACTOR_SHOCK:
                return self._factor_shock_test(returns, weights, scenario_params)
            elif test_type == StressTestType.CORRELATION_BREAKDOWN:
                return self._correlation_breakdown_test(returns, weights, scenario_params)
            elif test_type == StressTestType.VOLATILITY_SHOCK:
                return self._volatility_shock_test(returns, weights, scenario_params)
            elif test_type == StressTestType.LIQUIDITY_CRISIS:
                return self._liquidity_crisis_test(returns, weights, scenario_params)
            else:
                raise ValueError(f"Unknown stress test type: {test_type}")
                
        except Exception as e:
            logger.error(f"Error running stress test: {e}")
            return self._create_default_stress_result(test_type)
    
    def _historical_scenario_test(self, returns: pd.DataFrame, 
                                 weights: Dict[str, float],
                                 scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run historical scenario stress test"""
        try:
            scenario_name = scenario_params.get('scenario', 'FINANCIAL_CRISIS_2008') if scenario_params else 'FINANCIAL_CRISIS_2008'
            scenario = self.historical_scenarios.get(scenario_name, self.historical_scenarios['FINANCIAL_CRISIS_2008'])
            
            # Apply market shock
            market_shock = scenario['market_shock']
            volatility_multiplier = scenario['volatility_multiplier']
            
            # Calculate stressed returns
            stressed_returns = returns.copy()
            
            # Apply shock to all assets (simplified)
            for col in stressed_returns.columns:
                if col in weights:
                    # Apply market shock
                    shocked_return = market_shock
                    
                    # Add idiosyncratic shock based on asset's historical volatility
                    asset_vol = returns[col].std()
                    idiosyncratic_shock = np.random.normal(0, asset_vol * volatility_multiplier)
                    
                    total_shock = shocked_return + idiosyncratic_shock
                    stressed_returns.loc[stressed_returns.index[-1], col] = total_shock
            
            # Calculate portfolio impact
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Calculate stressed portfolio return
            stressed_portfolio_return = sum(
                weights[asset] * stressed_returns[asset].iloc[-1] 
                for asset in common_assets
            )
            
            # Calculate component impacts
            component_pnl = {}
            component_returns = {}
            
            for asset in common_assets:
                component_return = stressed_returns[asset].iloc[-1]
                component_pnl[asset] = weights[asset] * component_return * 100000  # Assuming $100k portfolio
                component_returns[asset] = component_return
            
            portfolio_pnl = sum(component_pnl.values())
            worst_case_loss = min(component_pnl.values()) if component_pnl else 0.0
            
            # Calculate stressed VaR (simplified)
            stressed_var = abs(stressed_portfolio_return) * 1.5
            stressed_volatility = returns.std().mean() * volatility_multiplier
            
            return StressTestResult(
                test_id=f"hist_{scenario_name}_{int(datetime.now().timestamp())}",
                test_type=StressTestType.HISTORICAL_SCENARIO,
                scenario_name=scenario_name,
                timestamp=datetime.now(),
                test_parameters=scenario,
                portfolio_pnl=portfolio_pnl,
                portfolio_return=stressed_portfolio_return,
                worst_case_loss=worst_case_loss,
                component_pnl=component_pnl,
                component_returns=component_returns,
                stressed_var=stressed_var,
                stressed_volatility=stressed_volatility,
                scenario_description=scenario['description']
            )
            
        except Exception as e:
            logger.error(f"Error in historical scenario test: {e}")
            return self._create_default_stress_result(StressTestType.HISTORICAL_SCENARIO)
    
    def _monte_carlo_stress_test(self, returns: pd.DataFrame, 
                                weights: Dict[str, float],
                                scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run Monte Carlo stress test"""
        try:
            n_simulations = scenario_params.get('n_simulations', 10000) if scenario_params else 10000
            confidence_level = scenario_params.get('confidence_level', 0.01) if scenario_params else 0.01  # 1% worst case
            
            # Estimate covariance matrix
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_returns = returns[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            cov_matrix = aligned_returns.cov().values
            mean_returns = aligned_returns.mean().values
            
            # Generate random scenarios
            np.random.seed(42)
            random_returns = np.random.multivariate_normal(
                mean_returns, cov_matrix, n_simulations
            )
            
            # Calculate portfolio returns for each scenario
            portfolio_returns = np.dot(random_returns, aligned_weights)
            
            # Find worst-case scenarios
            worst_case_threshold = np.percentile(portfolio_returns, confidence_level * 100)
            worst_case_return = np.min(portfolio_returns)
            
            # Calculate component contributions in worst case
            worst_case_idx = np.argmin(portfolio_returns)
            worst_case_scenario = random_returns[worst_case_idx]
            
            component_pnl = {}
            component_returns = {}
            
            for i, asset in enumerate(common_assets):
                component_return = worst_case_scenario[i]
                component_pnl[asset] = aligned_weights[i] * component_return * 100000
                component_returns[asset] = component_return
            
            portfolio_pnl = sum(component_pnl.values())
            
            return StressTestResult(
                test_id=f"mc_{int(datetime.now().timestamp())}",
                test_type=StressTestType.MONTE_CARLO,
                scenario_name="Monte Carlo Worst Case",
                timestamp=datetime.now(),
                test_parameters={'n_simulations': n_simulations, 'confidence_level': confidence_level},
                portfolio_pnl=portfolio_pnl,
                portfolio_return=worst_case_return,
                worst_case_loss=portfolio_pnl,
                component_pnl=component_pnl,
                component_returns=component_returns,
                stressed_var=abs(worst_case_threshold),
                stressed_volatility=np.std(portfolio_returns),
                scenario_description=f"Monte Carlo simulation worst {confidence_level:.1%} scenario",
                probability_estimate=confidence_level
            )
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo stress test: {e}")
            return self._create_default_stress_result(StressTestType.MONTE_CARLO)
    
    def _factor_shock_test(self, returns: pd.DataFrame, 
                          weights: Dict[str, float],
                          scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run factor shock stress test"""
        try:
            # Default factor shocks
            factor_shocks = scenario_params.get('factor_shocks', {
                'market_factor': -0.20,
                'size_factor': -0.15,
                'value_factor': -0.10
            }) if scenario_params else {
                'market_factor': -0.20,
                'size_factor': -0.15,
                'value_factor': -0.10
            }
            
            # Simplified factor model (using PCA as proxy for factors)
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_returns = returns[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Use PCA to extract factors
            pca = PCA(n_components=min(3, len(common_assets)))
            factor_returns = pca.fit_transform(aligned_returns.fillna(0))
            factor_loadings = pca.components_.T
            
            # Apply factor shocks
            shocked_factor_returns = np.zeros(factor_loadings.shape[1])
            for i, (factor_name, shock) in enumerate(factor_shocks.items()):
                if i < len(shocked_factor_returns):
                    shocked_factor_returns[i] = shock
            
            # Calculate asset returns under factor shock
            shocked_asset_returns = factor_loadings @ shocked_factor_returns
            
            # Calculate portfolio impact
            portfolio_return = np.dot(shocked_asset_returns, aligned_weights)
            
            component_pnl = {}
            component_returns = {}
            
            for i, asset in enumerate(common_assets):
                component_return = shocked_asset_returns[i]
                component_pnl[asset] = aligned_weights[i] * component_return * 100000
                component_returns[asset] = component_return
            
            portfolio_pnl = sum(component_pnl.values())
            worst_case_loss = min(component_pnl.values()) if component_pnl else 0.0
            
            return StressTestResult(
                test_id=f"factor_{int(datetime.now().timestamp())}",
                test_type=StressTestType.FACTOR_SHOCK,
                scenario_name="Factor Shock",
                timestamp=datetime.now(),
                test_parameters=factor_shocks,
                portfolio_pnl=portfolio_pnl,
                portfolio_return=portfolio_return,
                worst_case_loss=worst_case_loss,
                component_pnl=component_pnl,
                component_returns=component_returns,
                stressed_var=abs(portfolio_return) * 1.2,
                stressed_volatility=aligned_returns.std().mean() * 2.0,
                scenario_description="Systematic factor shock scenario"
            )
            
        except Exception as e:
            logger.error(f"Error in factor shock test: {e}")
            return self._create_default_stress_result(StressTestType.FACTOR_SHOCK)
    
    def _correlation_breakdown_test(self, returns: pd.DataFrame, 
                                   weights: Dict[str, float],
                                   scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run correlation breakdown stress test"""
        try:
            correlation_shock = scenario_params.get('correlation_shock', 0.8) if scenario_params else 0.8
            
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_returns = returns[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Calculate normal correlation matrix
            normal_corr = aligned_returns.corr()
            
            # Create stressed correlation matrix (increase all correlations)
            stressed_corr = normal_corr.copy()
            np.fill_diagonal(stressed_corr.values, 1.0)  # Keep diagonal as 1
            
            # Increase off-diagonal correlations
            for i in range(len(stressed_corr)):
                for j in range(len(stressed_corr)):
                    if i != j:
                        stressed_corr.iloc[i, j] = correlation_shock
            
            # Convert correlation to covariance
            std_devs = aligned_returns.std()
            stressed_cov = stressed_corr.multiply(std_devs, axis=0).multiply(std_devs, axis=1)
            
            # Generate stressed scenario
            np.random.seed(42)
            mean_returns = aligned_returns.mean().values
            stressed_returns = np.random.multivariate_normal(mean_returns, stressed_cov.values, 1)[0]
            
            # Calculate portfolio impact
            portfolio_return = np.dot(stressed_returns, aligned_weights)
            
            component_pnl = {}
            component_returns = {}
            
            for i, asset in enumerate(common_assets):
                component_return = stressed_returns[i]
                component_pnl[asset] = aligned_weights[i] * component_return * 100000
                component_returns[asset] = component_return
            
            portfolio_pnl = sum(component_pnl.values())
            worst_case_loss = min(component_pnl.values()) if component_pnl else 0.0
            
            return StressTestResult(
                test_id=f"corr_{int(datetime.now().timestamp())}",
                test_type=StressTestType.CORRELATION_BREAKDOWN,
                scenario_name="Correlation Breakdown",
                timestamp=datetime.now(),
                test_parameters={'correlation_shock': correlation_shock},
                portfolio_pnl=portfolio_pnl,
                portfolio_return=portfolio_return,
                worst_case_loss=worst_case_loss,
                component_pnl=component_pnl,
                component_returns=component_returns,
                stressed_var=abs(portfolio_return) * 1.3,
                stressed_volatility=np.sqrt(np.dot(aligned_weights, stressed_cov.values @ aligned_weights)),
                scenario_description=f"Correlation increased to {correlation_shock:.1%} across all assets"
            )
            
        except Exception as e:
            logger.error(f"Error in correlation breakdown test: {e}")
            return self._create_default_stress_result(StressTestType.CORRELATION_BREAKDOWN)
    
    def _volatility_shock_test(self, returns: pd.DataFrame, 
                              weights: Dict[str, float],
                              scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run volatility shock stress test"""
        try:
            volatility_multiplier = scenario_params.get('volatility_multiplier', 3.0) if scenario_params else 3.0
            
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_returns = returns[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Calculate shocked volatility scenario
            mean_returns = aligned_returns.mean().values
            std_returns = aligned_returns.std().values * volatility_multiplier
            
            # Generate scenario with increased volatility
            np.random.seed(42)
            shocked_returns = np.random.normal(mean_returns, std_returns)
            
            # Calculate portfolio impact
            portfolio_return = np.dot(shocked_returns, aligned_weights)
            
            component_pnl = {}
            component_returns = {}
            
            for i, asset in enumerate(common_assets):
                component_return = shocked_returns[i]
                component_pnl[asset] = aligned_weights[i] * component_return * 100000
                component_returns[asset] = component_return
            
            portfolio_pnl = sum(component_pnl.values())
            worst_case_loss = min(component_pnl.values()) if component_pnl else 0.0
            
            return StressTestResult(
                test_id=f"vol_{int(datetime.now().timestamp())}",
                test_type=StressTestType.VOLATILITY_SHOCK,
                scenario_name="Volatility Shock",
                timestamp=datetime.now(),
                test_parameters={'volatility_multiplier': volatility_multiplier},
                portfolio_pnl=portfolio_pnl,
                portfolio_return=portfolio_return,
                worst_case_loss=worst_case_loss,
                component_pnl=component_pnl,
                component_returns=component_returns,
                stressed_var=abs(portfolio_return) * 1.5,
                stressed_volatility=np.sqrt(np.dot(aligned_weights**2, std_returns**2)),
                scenario_description=f"Volatility increased by {volatility_multiplier}x across all assets"
            )
            
        except Exception as e:
            logger.error(f"Error in volatility shock test: {e}")
            return self._create_default_stress_result(StressTestType.VOLATILITY_SHOCK)
    
    def _liquidity_crisis_test(self, returns: pd.DataFrame, 
                              weights: Dict[str, float],
                              scenario_params: Optional[Dict[str, Any]]) -> StressTestResult:
        """Run liquidity crisis stress test"""
        try:
            liquidity_impact = scenario_params.get('liquidity_impact', 0.05) if scenario_params else 0.05  # 5% transaction cost
            forced_selling = scenario_params.get('forced_selling', 0.5) if scenario_params else 0.5  # 50% position liquidation
            
            common_assets = set(returns.columns) & set(weights.keys())
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Simulate forced liquidation with market impact
            liquidation_costs = {}
            remaining_positions = {}
            
            for i, asset in enumerate(common_assets):
                original_position = aligned_weights[i]
                liquidated_amount = original_position * forced_selling
                
                # Market impact cost (simplified)
                impact_cost = liquidated_amount * liquidity_impact
                liquidation_costs[asset] = impact_cost * 100000  # Portfolio value
                
                # Remaining position
                remaining_positions[asset] = original_position * (1 - forced_selling)
            
            # Total liquidation cost
            total_liquidation_cost = sum(liquidation_costs.values())
            
            # Portfolio impact
            portfolio_pnl = -total_liquidation_cost
            portfolio_return = portfolio_pnl / 100000  # As percentage
            
            return StressTestResult(
                test_id=f"liq_{int(datetime.now().timestamp())}",
                test_type=StressTestType.LIQUIDITY_CRISIS,
                scenario_name="Liquidity Crisis",
                timestamp=datetime.now(),
                test_parameters={
                    'liquidity_impact': liquidity_impact,
                    'forced_selling': forced_selling
                },
                portfolio_pnl=portfolio_pnl,
                portfolio_return=portfolio_return,
                worst_case_loss=portfolio_pnl,
                component_pnl=liquidation_costs,
                component_returns={asset: -cost/100000 for asset, cost in liquidation_costs.items()},
                stressed_var=abs(portfolio_return) * 1.2,
                stressed_volatility=0.0,  # No volatility in this scenario
                scenario_description=f"Forced liquidation of {forced_selling:.1%} of positions with {liquidity_impact:.1%} market impact"
            )
            
        except Exception as e:
            logger.error(f"Error in liquidity crisis test: {e}")
            return self._create_default_stress_result(StressTestType.LIQUIDITY_CRISIS)
    
    def _create_default_stress_result(self, test_type: StressTestType) -> StressTestResult:
        """Create default stress result when test fails"""
        return StressTestResult(
            test_id=f"default_{test_type.value}_{int(datetime.now().timestamp())}",
            test_type=test_type,
            scenario_name="Default Scenario",
            timestamp=datetime.now(),
            test_parameters={},
            portfolio_pnl=0.0,
            portfolio_return=0.0,
            worst_case_loss=0.0,
            component_pnl={},
            component_returns={},
            stressed_var=0.0,
            stressed_volatility=0.0,
            scenario_description="Default scenario due to test failure"
        )

class RiskMonitor:
    """Real-time risk monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Risk limits
        self.risk_limits: Dict[str, RiskLimit] = {}
        self._initialize_risk_limits()
        
        # Alert system
        self.active_alerts: List[RiskAlert] = []
        self.alert_callbacks: List[Callable[[RiskAlert], None]] = []
        
        # Monitoring parameters
        self.monitoring_frequency = config.get('monitoring_frequency', 60)  # seconds
        self.alert_cooldown = config.get('alert_cooldown', 300)  # seconds
        
        # Threading
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Database
        self.db_path = config.get('db_path', 'risk_monitoring.db')
        self._init_database()
        
        logger.info("Risk monitor initialized")
    
    def _initialize_risk_limits(self):
        """Initialize default risk limits"""
        default_limits = self.config.get('risk_limits', {})
        
        # Portfolio-level limits
        self.risk_limits['PORTFOLIO_VAR_95'] = RiskLimit(
            limit_id='PORTFOLIO_VAR_95',
            limit_type=RiskLimitType.PORTFOLIO_VAR,
            limit_value=default_limits.get('portfolio_var_95', 0.05),  # 5% daily VaR
            applies_to='PORTFOLIO',
            warning_threshold=0.8,
            auto_action='ALERT_ONLY'
        )
        
        self.risk_limits['PORTFOLIO_VOLATILITY'] = RiskLimit(
            limit_id='PORTFOLIO_VOLATILITY',
            limit_type=RiskLimitType.PORTFOLIO_VOLATILITY,
            limit_value=default_limits.get('portfolio_volatility', 0.20),  # 20% annual volatility
            applies_to='PORTFOLIO',
            warning_threshold=0.8,
            auto_action='ALERT_ONLY'
        )
        
        self.risk_limits['MAX_DRAWDOWN'] = RiskLimit(
            limit_id='MAX_DRAWDOWN',
            limit_type=RiskLimitType.MAX_DRAWDOWN,
            limit_value=default_limits.get('max_drawdown', 0.15),  # 15% max drawdown
            applies_to='PORTFOLIO',
            warning_threshold=0.8,
            auto_action='REDUCE_POSITION'
        )
        
        # Position-level limits
        self.risk_limits['MAX_POSITION_SIZE'] = RiskLimit(
            limit_id='MAX_POSITION_SIZE',
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=default_limits.get('max_position_size', 0.10),  # 10% max position
            applies_to='ANY_POSITION',
            warning_threshold=0.8,
            auto_action='REDUCE_POSITION'
        )
        
        # Concentration limits
        self.risk_limits['SECTOR_CONCENTRATION'] = RiskLimit(
            limit_id='SECTOR_CONCENTRATION',
            limit_type=RiskLimitType.SECTOR_CONCENTRATION,
            limit_value=default_limits.get('sector_concentration', 0.30),  # 30% max sector exposure
            applies_to='ANY_SECTOR',
            warning_threshold=0.8,
            auto_action='ALERT_ONLY'
        )
    
    def _init_database(self):
        """Initialize risk monitoring database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    confidence_level REAL,
                    time_horizon INTEGER,
                    risk_level TEXT NOT NULL,
                    threshold_breached BOOLEAN NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    risk_level TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    breach_magnitude REAL NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_time DATETIME
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_limits_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    limit_id TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    utilization REAL NOT NULL,
                    breach_count INTEGER NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Risk monitoring database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize risk database: {e}")
            raise
    
    def update_risk_metrics(self, risk_metrics: Dict[RiskMetricType, RiskMetric]):
        """Update risk metrics and check for limit breaches"""
        try:
            for metric_type, metric in risk_metrics.items():
                # Store metric
                self._store_risk_metric(metric)
                
                # Check for limit breaches
                self._check_risk_limits(metric)
            
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    def _check_risk_limits(self, metric: RiskMetric):
        """Check if risk metric breaches any limits"""
        try:
            # Map metric types to limit types
            metric_to_limit = {
                RiskMetricType.VALUE_AT_RISK: RiskLimitType.PORTFOLIO_VAR,
                RiskMetricType.VOLATILITY: RiskLimitType.PORTFOLIO_VOLATILITY,
                RiskMetricType.MAXIMUM_DRAWDOWN: RiskLimitType.MAX_DRAWDOWN,
                RiskMetricType.CONCENTRATION_RISK: RiskLimitType.SECTOR_CONCENTRATION
            }
            
            limit_type = metric_to_limit.get(metric.metric_type)
            if not limit_type:
                return
            
            # Find relevant limits
            relevant_limits = [
                limit for limit in self.risk_limits.values()
                if limit.limit_type == limit_type
            ]
            
            for limit in relevant_limits:
                # Update current value
                limit.current_value = metric.value
                limit.utilization = metric.value / limit.limit_value
                
                # Check for breach
                if metric.value > limit.limit_value * limit.breach_threshold:
                    self._handle_limit_breach(limit, metric)
                elif metric.value > limit.limit_value * limit.warning_threshold:
                    self._handle_limit_warning(limit, metric)
                
                # Store limit status
                self._store_limit_status(limit)
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
    
    def _handle_limit_breach(self, limit: RiskLimit, metric: RiskMetric):
        """Handle risk limit breach"""
        try:
            # Check cooldown
            if limit.last_breach:
                time_since_breach = (datetime.now() - limit.last_breach).total_seconds()
                if time_since_breach < self.alert_cooldown:
                    return
            
            # Create alert
            alert = RiskAlert(
                alert_id=f"breach_{limit.limit_id}_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                risk_level=RiskLevel.CRITICAL,
                metric_type=metric.metric_type,
                current_value=metric.value,
                threshold_value=limit.limit_value,
                breach_magnitude=(metric.value - limit.limit_value) / limit.limit_value,
                affected_positions=[limit.applies_to],
                recommended_actions=self._get_recommended_actions(limit, metric)
            )
            
            # Add to active alerts
            self.active_alerts.append(alert)
            self._store_alert(alert)
            
            # Update limit
            limit.last_breach = datetime.now()
            limit.breach_count += 1
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            # Auto action
            if limit.auto_action and limit.auto_action != 'ALERT_ONLY':
                self._execute_auto_action(limit, metric)
            
            logger.warning(f"Risk limit breach: {limit.limit_id} - {metric.value:.4f} > {limit.limit_value:.4f}")
            
        except Exception as e:
            logger.error(f"Error handling limit breach: {e}")
    
    def _handle_limit_warning(self, limit: RiskLimit, metric: RiskMetric):
        """Handle risk limit warning"""
        try:
            # Create warning alert
            alert = RiskAlert(
                alert_id=f"warning_{limit.limit_id}_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                risk_level=RiskLevel.HIGH,
                metric_type=metric.metric_type,
                current_value=metric.value,
                threshold_value=limit.limit_value * limit.warning_threshold,
                breach_magnitude=(metric.value - limit.limit_value * limit.warning_threshold) / (limit.limit_value * limit.warning_threshold),
                affected_positions=[limit.applies_to],
                recommended_actions=self._get_recommended_actions(limit, metric)
            )
            
            # Add to active alerts
            self.active_alerts.append(alert)
            self._store_alert(alert)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            logger.info(f"Risk limit warning: {limit.limit_id} - {metric.value:.4f} > {limit.limit_value * limit.warning_threshold:.4f}")
            
        except Exception as e:
            logger.error(f"Error handling limit warning: {e}")
    
    def _get_recommended_actions(self, limit: RiskLimit, metric: RiskMetric) -> List[str]:
        """Get recommended actions for limit breach"""
        actions = []
        
        if limit.limit_type == RiskLimitType.PORTFOLIO_VAR:
            actions.extend([
                "Reduce position sizes",
                "Increase hedging",
                "Review correlation assumptions"
            ])
        elif limit.limit_type == RiskLimitType.PORTFOLIO_VOLATILITY:
            actions.extend([
                "Reduce volatile positions",
                "Increase diversification",
                "Add low-volatility assets"
            ])
        elif limit.limit_type == RiskLimitType.MAX_DRAWDOWN:
            actions.extend([
                "Implement stop-losses",
                "Reduce leverage",
                "Consider market neutral strategies"
            ])
        elif limit.limit_type == RiskLimitType.POSITION_SIZE:
            actions.extend([
                "Reduce position size",
                "Distribute across multiple assets",
                "Implement position limits"
            ])
        elif limit.limit_type == RiskLimitType.SECTOR_CONCENTRATION:
            actions.extend([
                "Diversify across sectors",
                "Reduce sector-specific positions",
                "Add sector hedges"
            ])
        
        return actions
    
    def _execute_auto_action(self, limit: RiskLimit, metric: RiskMetric):
        """Execute automatic action for limit breach"""
        try:
            if limit.auto_action == 'REDUCE_POSITION':
                logger.info(f"Auto action: Reducing positions due to {limit.limit_id} breach")
                # In practice, this would integrate with the execution system
                
            elif limit.auto_action == 'HEDGE':
                logger.info(f"Auto action: Adding hedges due to {limit.limit_id} breach")
                # In practice, this would add appropriate hedges
            
        except Exception as e:
            logger.error(f"Error executing auto action: {e}")
    
    def _store_risk_metric(self, metric: RiskMetric):
        """Store risk metric in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_metrics 
                (timestamp, metric_type, value, confidence_level, time_horizon, 
                 risk_level, threshold_breached)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.timestamp, metric.metric_type.value, metric.value,
                metric.confidence_level, metric.time_horizon,
                metric.risk_level.value, metric.threshold_breached
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing risk metric: {e}")
    
    def _store_alert(self, alert: RiskAlert):
        """Store alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_alerts 
                (alert_id, timestamp, risk_level, metric_type, current_value,
                 threshold_value, breach_magnitude, acknowledged, resolved, resolution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id, alert.timestamp, alert.risk_level.value,
                alert.metric_type.value, alert.current_value, alert.threshold_value,
                alert.breach_magnitude, alert.acknowledged, alert.resolved,
                alert.resolution_time
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def _store_limit_status(self, limit: RiskLimit):
        """Store limit status in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_limits_status 
                (timestamp, limit_id, current_value, utilization, breach_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now(), limit.limit_id, limit.current_value,
                limit.utilization, limit.breach_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing limit status: {e}")
    
    def start_monitoring(self):
        """Start risk monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Risk monitoring already running")
            return
        
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Risk monitoring started")
    
    def stop_monitoring(self):
        """Stop risk monitoring"""
        self.stop_event.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Risk monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set():
            try:
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Sleep
                self.stop_event.wait(self.monitoring_frequency)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_frequency)
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            self.active_alerts = [
                alert for alert in self.active_alerts
                if not alert.resolved or alert.timestamp > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        try:
            for alert in self.active_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            for alert in self.active_alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolution_time = datetime.now()
                    logger.info(f"Alert resolved: {alert_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False
    
    def add_alert_callback(self, callback: Callable[[RiskAlert], None]):
        """Add callback for risk alerts"""
        self.alert_callbacks.append(callback)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            active_alerts_by_level = defaultdict(int)
            for alert in self.active_alerts:
                if not alert.resolved:
                    active_alerts_by_level[alert.risk_level.value] += 1
            
            limits_utilization = {}
            for limit_id, limit in self.risk_limits.items():
                limits_utilization[limit_id] = {
                    'utilization': limit.utilization,
                    'current_value': limit.current_value,
                    'limit_value': limit.limit_value,
                    'breach_count': limit.breach_count
                }
            
            return {
                'total_active_alerts': len([a for a in self.active_alerts if not a.resolved]),
                'alerts_by_level': dict(active_alerts_by_level),
                'limits_utilization': limits_utilization,
                'monitoring_status': 'RUNNING' if self.monitoring_thread and self.monitoring_thread.is_alive() else 'STOPPED',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk summary: {e}")
            return {}

class ComprehensiveRiskSystem:
    """
    Comprehensive risk management system that integrates VaR calculation,
    stress testing, and real-time risk monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the comprehensive risk system
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize components
        self.var_calculator = VaRCalculator(config.get('var_config', {}))
        self.stress_tester = StressTester(config.get('stress_config', {}))
        self.risk_monitor = RiskMonitor(config.get('monitor_config', {}))
        
        # Risk reports
        self.risk_reports: List[RiskReport] = []
        
        # Database
        self.db_path = config.get('db_path', 'comprehensive_risk.db')
        self._init_database()
        
        logger.info("Comprehensive risk system initialized")
    
    def _init_database(self):
        """Initialize comprehensive risk database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    portfolio_value REAL NOT NULL,
                    portfolio_return REAL NOT NULL,
                    portfolio_volatility REAL NOT NULL,
                    risk_metrics TEXT NOT NULL,
                    stress_test_results TEXT NOT NULL,
                    active_alerts_count INTEGER NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Comprehensive risk database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize comprehensive risk database: {e}")
            raise
    
    def generate_comprehensive_risk_report(self, 
                                         returns_data: pd.DataFrame,
                                         weights: Dict[str, float],
                                         portfolio_value: float) -> RiskReport:
        """Generate comprehensive risk report"""
        try:
            # Calculate VaR metrics
            var_results = {}
            for confidence_level in [0.95, 0.99]:
                var_result = self.var_calculator.calculate_var(
                    returns_data, weights, confidence_level, 1, 'HISTORICAL'
                )
                var_results[f'var_{int(confidence_level*100)}'] = var_result
            
            # Run stress tests
            stress_test_results = []
            
            stress_tests = [
                (StressTestType.HISTORICAL_SCENARIO, {'scenario': 'FINANCIAL_CRISIS_2008'}),
                (StressTestType.MONTE_CARLO, {'n_simulations': 10000, 'confidence_level': 0.01}),
                (StressTestType.VOLATILITY_SHOCK, {'volatility_multiplier': 3.0}),
                (StressTestType.CORRELATION_BREAKDOWN, {'correlation_shock': 0.8})
            ]
            
            for test_type, params in stress_tests:
                stress_result = self.stress_tester.run_stress_test(
                    returns_data, weights, test_type, params
                )
                stress_test_results.append(stress_result)
            
            # Calculate portfolio metrics
            portfolio_returns = self._calculate_portfolio_returns(returns_data, weights)
            portfolio_return = portfolio_returns.mean() * 252  # Annualized
            portfolio_volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
            
            # Create risk metrics
            risk_metrics = {}
            
            # VaR metrics
            risk_metrics[RiskMetricType.VALUE_AT_RISK] = RiskMetric(
                metric_type=RiskMetricType.VALUE_AT_RISK,
                value=var_results['var_95']['var'],
                timestamp=datetime.now(),
                confidence_level=0.95,
                time_horizon=1
            )
            
            risk_metrics[RiskMetricType.EXPECTED_SHORTFALL] = RiskMetric(
                metric_type=RiskMetricType.EXPECTED_SHORTFALL,
                value=var_results['var_95']['expected_shortfall'],
                timestamp=datetime.now(),
                confidence_level=0.95,
                time_horizon=1
            )
            
            # Portfolio metrics
            risk_metrics[RiskMetricType.VOLATILITY] = RiskMetric(
                metric_type=RiskMetricType.VOLATILITY,
                value=portfolio_volatility,
                timestamp=datetime.now()
            )
            
            risk_metrics[RiskMetricType.SHARPE_RATIO] = RiskMetric(
                metric_type=RiskMetricType.SHARPE_RATIO,
                value=portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0.0,
                timestamp=datetime.now()
            )
            
            # Calculate max drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            risk_metrics[RiskMetricType.MAXIMUM_DRAWDOWN] = RiskMetric(
                metric_type=RiskMetricType.MAXIMUM_DRAWDOWN,
                value=abs(max_drawdown),
                timestamp=datetime.now()
            )
            
            # Update risk monitor
            self.risk_monitor.update_risk_metrics(risk_metrics)
            
            # Get risk limits status
            risk_limits_status = self.risk_monitor.risk_limits
            
            # Get active alerts
            active_alerts = [alert for alert in self.risk_monitor.active_alerts if not alert.resolved]
            
            # Calculate risk attribution
            risk_attribution = self._calculate_risk_attribution(returns_data, weights)
            
            # Generate recommendations
            risk_recommendations = self._generate_risk_recommendations(
                risk_metrics, stress_test_results, active_alerts
            )
            
            # Create comprehensive report
            report = RiskReport(
                report_id=f"risk_report_{int(datetime.now().timestamp())}",
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                portfolio_return=portfolio_return,
                portfolio_volatility=portfolio_volatility,
                risk_metrics=risk_metrics,
                stress_test_results=stress_test_results,
                risk_limits_status=risk_limits_status,
                active_alerts=active_alerts,
                risk_attribution=risk_attribution,
                risk_recommendations=risk_recommendations
            )
            
            # Store report
            self.risk_reports.append(report)
            self._store_risk_report(report)
            
            logger.info(f"Comprehensive risk report generated: {report.report_id}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating comprehensive risk report: {e}")
            raise
    
    def _calculate_portfolio_returns(self, returns_data: pd.DataFrame, 
                                   weights: Dict[str, float]) -> pd.Series:
        """Calculate portfolio returns"""
        try:
            common_assets = set(returns_data.columns) & set(weights.keys())
            aligned_returns = returns_data[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            portfolio_returns = (aligned_returns * aligned_weights).sum(axis=1)
            return portfolio_returns
            
        except Exception as e:
            logger.error(f"Error calculating portfolio returns: {e}")
            return pd.Series()
    
    def _calculate_risk_attribution(self, returns_data: pd.DataFrame, 
                                  weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk attribution by asset"""
        try:
            common_assets = set(returns_data.columns) & set(weights.keys())
            aligned_returns = returns_data[list(common_assets)]
            aligned_weights = np.array([weights[asset] for asset in common_assets])
            
            # Calculate covariance matrix
            cov_matrix = aligned_returns.cov().values
            
            # Calculate portfolio variance
            portfolio_variance = aligned_weights.T @ cov_matrix @ aligned_weights
            
            # Calculate marginal contributions
            marginal_contributions = cov_matrix @ aligned_weights
            
            # Calculate risk contributions
            risk_contributions = {}
            for i, asset in enumerate(common_assets):
                risk_contrib = aligned_weights[i] * marginal_contributions[i] / portfolio_variance
                risk_contributions[asset] = risk_contrib
            
            return risk_contributions
            
        except Exception as e:
            logger.error(f"Error calculating risk attribution: {e}")
            return {}
    
    def _generate_risk_recommendations(self, risk_metrics: Dict[RiskMetricType, RiskMetric],
                                     stress_test_results: List[StressTestResult],
                                     active_alerts: List[RiskAlert]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        try:
            # VaR-based recommendations
            var_metric = risk_metrics.get(RiskMetricType.VALUE_AT_RISK)
            if var_metric and var_metric.value > 0.05:  # 5% daily VaR threshold
                recommendations.append("Consider reducing portfolio risk - VaR exceeds 5%")
            
            # Volatility-based recommendations
            vol_metric = risk_metrics.get(RiskMetricType.VOLATILITY)
            if vol_metric and vol_metric.value > 0.25:  # 25% annual volatility threshold
                recommendations.append("Portfolio volatility is high - consider diversification")
            
            # Drawdown-based recommendations
            dd_metric = risk_metrics.get(RiskMetricType.MAXIMUM_DRAWDOWN)
            if dd_metric and dd_metric.value > 0.15:  # 15% max drawdown threshold
                recommendations.append("Implement stronger stop-loss controls - drawdown is high")
            
            # Stress test-based recommendations
            for stress_result in stress_test_results:
                if stress_result.portfolio_pnl < -10000:  # $10k loss threshold
                    recommendations.append(f"Consider hedging against {stress_result.scenario_name} scenario")
            
            # Alert-based recommendations
            critical_alerts = [alert for alert in active_alerts if alert.risk_level == RiskLevel.CRITICAL]
            if critical_alerts:
                recommendations.append("Address critical risk alerts immediately")
            
            # Default recommendation
            if not recommendations:
                recommendations.append("Risk levels are within acceptable ranges")
            
        except Exception as e:
            logger.error(f"Error generating risk recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to error")
        
        return recommendations
    
    def _store_risk_report(self, report: RiskReport):
        """Store risk report in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_reports 
                (report_id, timestamp, portfolio_value, portfolio_return, portfolio_volatility,
                 risk_metrics, stress_test_results, active_alerts_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.report_id, report.timestamp, report.portfolio_value,
                report.portfolio_return, report.portfolio_volatility,
                json.dumps({k.value: v.__dict__ for k, v in report.risk_metrics.items()}, default=str),
                json.dumps([result.__dict__ for result in report.stress_test_results], default=str),
                len(report.active_alerts)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing risk report: {e}")
    
    def start_risk_monitoring(self):
        """Start real-time risk monitoring"""
        self.risk_monitor.start_monitoring()
    
    def stop_risk_monitoring(self):
        """Stop real-time risk monitoring"""
        self.risk_monitor.stop_monitoring()
    
    def get_risk_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk system summary"""
        try:
            recent_reports = self.risk_reports[-5:] if len(self.risk_reports) >= 5 else self.risk_reports
            
            return {
                'total_risk_reports': len(self.risk_reports),
                'risk_monitor_summary': self.risk_monitor.get_risk_summary(),
                'recent_reports': [
                    {
                        'report_id': report.report_id,
                        'timestamp': report.timestamp.isoformat(),
                        'portfolio_return': report.portfolio_return,
                        'portfolio_volatility': report.portfolio_volatility,
                        'active_alerts_count': len(report.active_alerts)
                    }
                    for report in recent_reports
                ],
                'available_stress_tests': [test.value for test in StressTestType],
                'risk_metrics_tracked': [metric.value for metric in RiskMetricType],
                'system_status': 'OPERATIONAL',
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk system summary: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    # Configuration for comprehensive risk system
    config = {
        'var_config': {
            'confidence_levels': [0.95, 0.99, 0.995],
            'time_horizons': [1, 5, 10],
            'methods': ['HISTORICAL', 'PARAMETRIC', 'MONTE_CARLO']
        },
        'stress_config': {
            'monte_carlo_params': {
                'n_simulations': 10000
            }
        },
        'monitor_config': {
            'monitoring_frequency': 60,
            'alert_cooldown': 300,
            'risk_limits': {
                'portfolio_var_95': 0.05,
                'portfolio_volatility': 0.20,
                'max_drawdown': 0.15,
                'max_position_size': 0.10,
                'sector_concentration': 0.30
            }
        },
        'db_path': 'comprehensive_risk_system.db'
    }
    
    # Create risk system
    risk_system = ComprehensiveRiskSystem(config)
    
    # Generate sample data
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # Generate correlated returns with some volatility clustering
    np.random.seed(42)
    returns_data = pd.DataFrame(index=dates, columns=assets)
    
    for i, asset in enumerate(assets):
        # Generate returns with volatility clustering
        base_vol = 0.02
        vol_process = [base_vol]
        
        for _ in range(len(dates)):
            # GARCH-like volatility process
            new_vol = 0.1 * base_vol + 0.8 * vol_process[-1] + 0.1 * np.random.normal(0, 0.001)**2
            vol_process.append(max(0.005, new_vol))  # Minimum volatility
        
        returns = []
        for j in range(len(dates)):
            ret = np.random.normal(0.0005, vol_process[j])
            # Add some correlation with market (first asset)
            if i > 0 and j < len(returns_data):
                market_return = returns_data.iloc[j, 0] if not pd.isna(returns_data.iloc[j, 0]) else 0
                correlation = 0.3 + 0.2 * i / len(assets)  # Increasing correlation
                ret = correlation * market_return + np.sqrt(1 - correlation**2) * ret
            returns.append(ret)
        
        returns_data[asset] = returns
    
    returns_data = returns_data.fillna(0)
    
    # Define portfolio weights
    weights = {
        'AAPL': 0.25,
        'MSFT': 0.20,
        'GOOGL': 0.20,
        'AMZN': 0.20,
        'TSLA': 0.15
    }
    
    portfolio_value = 1000000  # $1M portfolio
    
    # Add alert callback
    def alert_handler(alert: RiskAlert):
        print(f"RISK ALERT: {alert.risk_level.value} - {alert.metric_type.value}")
        print(f"  Current: {alert.current_value:.4f}, Threshold: {alert.threshold_value:.4f}")
        print(f"  Recommended actions: {', '.join(alert.recommended_actions)}")
    
    risk_system.risk_monitor.add_alert_callback(alert_handler)
    
    # Start risk monitoring
    risk_system.start_risk_monitoring()
    
    # Generate comprehensive risk report
    print("Generating comprehensive risk report...")
    risk_report = risk_system.generate_comprehensive_risk_report(
        returns_data, weights, portfolio_value
    )
    
    print(f"\n--- Risk Report Summary ---")
    print(f"Portfolio Value: ${risk_report.portfolio_value:,.0f}")
    print(f"Portfolio Return: {risk_report.portfolio_return:.2%}")
    print(f"Portfolio Volatility: {risk_report.portfolio_volatility:.2%}")
    
    print(f"\n--- Risk Metrics ---")
    for metric_type, metric in risk_report.risk_metrics.items():
        print(f"{metric_type.value}: {metric.value:.4f}")
    
    print(f"\n--- Stress Test Results ---")
    for stress_result in risk_report.stress_test_results:
        print(f"{stress_result.scenario_name}: {stress_result.portfolio_return:.2%} return")
        print(f"  Portfolio P&L: ${stress_result.portfolio_pnl:,.0f}")
    
    print(f"\n--- Risk Recommendations ---")
    for recommendation in risk_report.risk_recommendations:
        print(f"  • {recommendation}")
    
    # Get system summary
    summary = risk_system.get_risk_system_summary()
    print(f"\nRisk System Summary:")
    print(json.dumps(summary, indent=2))
    
    # Stop risk monitoring
    risk_system.stop_risk_monitoring() 