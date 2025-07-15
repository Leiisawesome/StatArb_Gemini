"""
Comprehensive Risk Metrics Calculator for AI-Ready Statistical Arbitrage
========================================================================

This module provides advanced risk metrics calculation with:
- Value at Risk (VaR) using multiple methods
- Conditional Value at Risk (CVaR)
- Stress testing and scenario analysis
- Correlation analysis and breakdown detection
- Maximum drawdown analysis
- Real-time risk monitoring

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from scipy.optimize import minimize
import json

logger = logging.getLogger(__name__)

class VaRMethod(Enum):
    """VaR calculation methods"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    CORNISH_FISHER = "cornish_fisher"

class StressTestScenario(Enum):
    """Stress test scenarios"""
    MARKET_CRASH = "market_crash"
    INTEREST_RATE_SHOCK = "interest_rate_shock"
    VOLATILITY_SPIKE = "volatility_spike"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    SECTOR_ROTATION = "sector_rotation"
    CURRENCY_CRISIS = "currency_crisis"
    TAIL_RISK = "tail_risk"

@dataclass
class VaRResult:
    """VaR calculation result"""
    var_value: float
    confidence_level: float
    method: VaRMethod
    time_horizon: int
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CVaRResult:
    """CVaR calculation result"""
    cvar_value: float
    var_value: float
    confidence_level: float
    expected_shortfall: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class StressTestResult:
    """Stress test result"""
    scenario: StressTestScenario
    portfolio_loss: float
    loss_percentage: float
    worst_positions: List[Tuple[str, float]]
    scenario_description: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CorrelationAnalysis:
    """Correlation analysis result"""
    correlation_matrix: pd.DataFrame
    average_correlation: float
    max_correlation: float
    min_correlation: float
    correlation_clusters: List[List[str]]
    breakdown_risk: float
    timestamp: datetime = field(default_factory=datetime.now)

class VaRCalculator:
    """Value at Risk calculator with multiple methods"""
    
    def __init__(self, confidence_level: float = 0.95, time_horizon: int = 1):
        self.confidence_level = confidence_level
        self.time_horizon = time_horizon
        
    def calculate_var(self, returns: pd.Series, method: VaRMethod = VaRMethod.HISTORICAL,
                     portfolio_value: float = 1000000) -> VaRResult:
        """Calculate VaR using specified method"""
        try:
            if method == VaRMethod.HISTORICAL:
                var_value = self._historical_var(returns, portfolio_value)
            elif method == VaRMethod.PARAMETRIC:
                var_value = self._parametric_var(returns, portfolio_value)
            elif method == VaRMethod.MONTE_CARLO:
                var_value = self._monte_carlo_var(returns, portfolio_value)
            elif method == VaRMethod.CORNISH_FISHER:
                var_value = self._cornish_fisher_var(returns, portfolio_value)
            else:
                var_value = self._historical_var(returns, portfolio_value)
            
            return VaRResult(
                var_value=var_value,
                confidence_level=self.confidence_level,
                method=method,
                time_horizon=self.time_horizon
            )
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return VaRResult(
                var_value=0.0,
                confidence_level=self.confidence_level,
                method=method,
                time_horizon=self.time_horizon
            )
    
    def _historical_var(self, returns: pd.Series, portfolio_value: float) -> float:
        """Calculate historical VaR"""
        try:
            if len(returns) < 50:
                logger.warning("Insufficient data for historical VaR")
                return 0.0
            
            # Scale returns to time horizon
            scaled_returns = returns * np.sqrt(self.time_horizon)
            
            # Calculate percentile
            percentile = (1 - self.confidence_level) * 100
            var_return = np.percentile(scaled_returns, percentile)
            
            return abs(var_return * portfolio_value)
            
        except Exception as e:
            logger.error(f"Error in historical VaR: {e}")
            return 0.0
    
    def _parametric_var(self, returns: pd.Series, portfolio_value: float) -> float:
        """Calculate parametric VaR assuming normal distribution"""
        try:
            if len(returns) < 30:
                logger.warning("Insufficient data for parametric VaR")
                return 0.0
            
            # Calculate mean and std
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Scale to time horizon
            scaled_mean = mean_return * self.time_horizon
            scaled_std = std_return * np.sqrt(self.time_horizon)
            
            # Calculate VaR using normal distribution
            z_score = stats.norm.ppf(1 - self.confidence_level)
            var_return = scaled_mean + z_score * scaled_std
            
            return abs(var_return * portfolio_value)
            
        except Exception as e:
            logger.error(f"Error in parametric VaR: {e}")
            return 0.0
    
    def _monte_carlo_var(self, returns: pd.Series, portfolio_value: float,
                        n_simulations: int = 10000) -> float:
        """Calculate Monte Carlo VaR"""
        try:
            if len(returns) < 30:
                logger.warning("Insufficient data for Monte Carlo VaR")
                return 0.0
            
            # Estimate parameters
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            random_returns = np.random.normal(
                mean_return * self.time_horizon,
                std_return * np.sqrt(self.time_horizon),
                n_simulations
            )
            
            # Calculate VaR
            percentile = (1 - self.confidence_level) * 100
            var_return = np.percentile(random_returns, percentile)
            
            return abs(var_return * portfolio_value)
            
        except Exception as e:
            logger.error(f"Error in Monte Carlo VaR: {e}")
            return 0.0
    
    def _cornish_fisher_var(self, returns: pd.Series, portfolio_value: float) -> float:
        """Calculate Cornish-Fisher VaR accounting for skewness and kurtosis"""
        try:
            if len(returns) < 50:
                logger.warning("Insufficient data for Cornish-Fisher VaR")
                return 0.0
            
            # Calculate moments
            mean_return = returns.mean()
            std_return = returns.std()
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            # Scale to time horizon
            scaled_mean = mean_return * self.time_horizon
            scaled_std = std_return * np.sqrt(self.time_horizon)
            
            # Cornish-Fisher adjustment
            z = stats.norm.ppf(1 - self.confidence_level)
            cf_adjustment = (z + (z**2 - 1) * skewness / 6 + 
                           (z**3 - 3*z) * kurtosis / 24 - 
                           (2*z**3 - 5*z) * skewness**2 / 36)
            
            var_return = scaled_mean + cf_adjustment * scaled_std
            
            return abs(var_return * portfolio_value)
            
        except Exception as e:
            logger.error(f"Error in Cornish-Fisher VaR: {e}")
            return 0.0

class CVaRCalculator:
    """Conditional Value at Risk (Expected Shortfall) calculator"""
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        
    def calculate_cvar(self, returns: pd.Series, portfolio_value: float = 1000000) -> CVaRResult:
        """Calculate CVaR (Expected Shortfall)"""
        try:
            if len(returns) < 50:
                logger.warning("Insufficient data for CVaR calculation")
                return CVaRResult(
                    cvar_value=0.0,
                    var_value=0.0,
                    confidence_level=self.confidence_level,
                    expected_shortfall=0.0
                )
            
            # Calculate VaR first
            var_calculator = VaRCalculator(self.confidence_level)
            var_result = var_calculator.calculate_var(returns, VaRMethod.HISTORICAL, portfolio_value)
            var_return = var_result.var_value / portfolio_value
            
            # Calculate CVaR as mean of returns below VaR
            tail_returns = returns[returns <= -var_return]
            
            if len(tail_returns) == 0:
                # If no tail returns, use VaR as approximation
                cvar_value = var_result.var_value
                expected_shortfall = var_return
            else:
                expected_shortfall = abs(tail_returns.mean())
                cvar_value = expected_shortfall * portfolio_value
            
            return CVaRResult(
                cvar_value=cvar_value,
                var_value=var_result.var_value,
                confidence_level=self.confidence_level,
                expected_shortfall=expected_shortfall
            )
            
        except Exception as e:
            logger.error(f"Error calculating CVaR: {e}")
            return CVaRResult(
                cvar_value=0.0,
                var_value=0.0,
                confidence_level=self.confidence_level,
                expected_shortfall=0.0
            )

class StressTestEngine:
    """Comprehensive stress testing engine"""
    
    def __init__(self):
        self.scenarios = {
            StressTestScenario.MARKET_CRASH: self._market_crash_scenario,
            StressTestScenario.INTEREST_RATE_SHOCK: self._interest_rate_shock_scenario,
            StressTestScenario.VOLATILITY_SPIKE: self._volatility_spike_scenario,
            StressTestScenario.CORRELATION_BREAKDOWN: self._correlation_breakdown_scenario,
            StressTestScenario.LIQUIDITY_CRISIS: self._liquidity_crisis_scenario,
            StressTestScenario.SECTOR_ROTATION: self._sector_rotation_scenario,
            StressTestScenario.CURRENCY_CRISIS: self._currency_crisis_scenario,
            StressTestScenario.TAIL_RISK: self._tail_risk_scenario
        }
    
    def run_stress_test(self, portfolio_data: Dict[str, Any], 
                       scenario: StressTestScenario) -> StressTestResult:
        """Run specific stress test scenario"""
        try:
            scenario_function = self.scenarios.get(scenario)
            if not scenario_function:
                raise ValueError(f"Unknown scenario: {scenario}")
            
            return scenario_function(portfolio_data)
            
        except Exception as e:
            logger.error(f"Error running stress test {scenario}: {e}")
            return StressTestResult(
                scenario=scenario,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )
    
    def run_all_stress_tests(self, portfolio_data: Dict[str, Any]) -> List[StressTestResult]:
        """Run all stress test scenarios"""
        results = []
        for scenario in StressTestScenario:
            result = self.run_stress_test(portfolio_data, scenario)
            results.append(result)
        return results
    
    def _market_crash_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Market crash scenario: -20% market decline"""
        try:
            positions = portfolio_data.get('positions', {})
            total_value = portfolio_data.get('metrics', {}).get('total_value', 0)
            
            # Apply -20% shock to all positions
            shock_factor = -0.20
            total_loss = 0.0
            position_losses = []
            
            for symbol, position in positions.items():
                market_value = position.get('market_value', 0)
                position_loss = market_value * shock_factor
                total_loss += position_loss
                position_losses.append((symbol, position_loss))
            
            # Sort by worst losses
            position_losses.sort(key=lambda x: x[1])
            worst_positions = position_losses[:5]
            
            return StressTestResult(
                scenario=StressTestScenario.MARKET_CRASH,
                portfolio_loss=abs(total_loss),
                loss_percentage=abs(total_loss / total_value) if total_value > 0 else 0.0,
                worst_positions=worst_positions,
                scenario_description="Market crash: -20% decline across all positions"
            )
            
        except Exception as e:
            logger.error(f"Error in market crash scenario: {e}")
            return StressTestResult(
                scenario=StressTestScenario.MARKET_CRASH,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )
    
    def _volatility_spike_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Volatility spike scenario: 3x increase in volatility"""
        try:
            positions = portfolio_data.get('positions', {})
            total_value = portfolio_data.get('metrics', {}).get('total_value', 0)
            
            # Apply volatility shock based on position volatility
            total_loss = 0.0
            position_losses = []
            
            for symbol, position in positions.items():
                market_value = position.get('market_value', 0)
                # Assume higher volatility positions lose more
                vol_shock = -0.15  # Base 15% loss
                position_loss = market_value * vol_shock
                total_loss += position_loss
                position_losses.append((symbol, position_loss))
            
            position_losses.sort(key=lambda x: x[1])
            worst_positions = position_losses[:5]
            
            return StressTestResult(
                scenario=StressTestScenario.VOLATILITY_SPIKE,
                portfolio_loss=abs(total_loss),
                loss_percentage=abs(total_loss / total_value) if total_value > 0 else 0.0,
                worst_positions=worst_positions,
                scenario_description="Volatility spike: 3x increase in market volatility"
            )
            
        except Exception as e:
            logger.error(f"Error in volatility spike scenario: {e}")
            return StressTestResult(
                scenario=StressTestScenario.VOLATILITY_SPIKE,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )
    
    def _correlation_breakdown_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Correlation breakdown scenario: correlations go to 1"""
        try:
            positions = portfolio_data.get('positions', {})
            total_value = portfolio_data.get('metrics', {}).get('total_value', 0)
            
            # In correlation breakdown, diversification benefits disappear
            # Apply larger losses to supposedly diversified positions
            total_loss = 0.0
            position_losses = []
            
            for symbol, position in positions.items():
                market_value = position.get('market_value', 0)
                # Larger loss for positions that were supposed to be diversified
                correlation_shock = -0.12  # 12% loss
                position_loss = market_value * correlation_shock
                total_loss += position_loss
                position_losses.append((symbol, position_loss))
            
            position_losses.sort(key=lambda x: x[1])
            worst_positions = position_losses[:5]
            
            return StressTestResult(
                scenario=StressTestScenario.CORRELATION_BREAKDOWN,
                portfolio_loss=abs(total_loss),
                loss_percentage=abs(total_loss / total_value) if total_value > 0 else 0.0,
                worst_positions=worst_positions,
                scenario_description="Correlation breakdown: all correlations approach 1"
            )
            
        except Exception as e:
            logger.error(f"Error in correlation breakdown scenario: {e}")
            return StressTestResult(
                scenario=StressTestScenario.CORRELATION_BREAKDOWN,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )
    
    def _liquidity_crisis_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Liquidity crisis scenario: wide bid-ask spreads"""
        try:
            positions = portfolio_data.get('positions', {})
            total_value = portfolio_data.get('metrics', {}).get('total_value', 0)
            
            # Apply liquidity shock - assume 5% bid-ask spread
            total_loss = 0.0
            position_losses = []
            
            for symbol, position in positions.items():
                market_value = position.get('market_value', 0)
                # Liquidity shock - cost to exit position
                liquidity_shock = -0.05  # 5% cost to exit
                position_loss = market_value * liquidity_shock
                total_loss += position_loss
                position_losses.append((symbol, position_loss))
            
            position_losses.sort(key=lambda x: x[1])
            worst_positions = position_losses[:5]
            
            return StressTestResult(
                scenario=StressTestScenario.LIQUIDITY_CRISIS,
                portfolio_loss=abs(total_loss),
                loss_percentage=abs(total_loss / total_value) if total_value > 0 else 0.0,
                worst_positions=worst_positions,
                scenario_description="Liquidity crisis: 5% bid-ask spread across all positions"
            )
            
        except Exception as e:
            logger.error(f"Error in liquidity crisis scenario: {e}")
            return StressTestResult(
                scenario=StressTestScenario.LIQUIDITY_CRISIS,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )
    
    def _interest_rate_shock_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Interest rate shock: +200 basis points"""
        return self._generic_scenario(portfolio_data, StressTestScenario.INTEREST_RATE_SHOCK, 
                                    -0.08, "Interest rate shock: +200 basis points")
    
    def _sector_rotation_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Sector rotation scenario"""
        return self._generic_scenario(portfolio_data, StressTestScenario.SECTOR_ROTATION, 
                                    -0.10, "Sector rotation: major style/sector shifts")
    
    def _currency_crisis_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Currency crisis scenario"""
        return self._generic_scenario(portfolio_data, StressTestScenario.CURRENCY_CRISIS, 
                                    -0.15, "Currency crisis: major FX disruption")
    
    def _tail_risk_scenario(self, portfolio_data: Dict[str, Any]) -> StressTestResult:
        """Tail risk scenario: 4-sigma event"""
        return self._generic_scenario(portfolio_data, StressTestScenario.TAIL_RISK, 
                                    -0.25, "Tail risk: 4-sigma market event")
    
    def _generic_scenario(self, portfolio_data: Dict[str, Any], scenario: StressTestScenario,
                         shock_factor: float, description: str) -> StressTestResult:
        """Generic scenario implementation"""
        try:
            positions = portfolio_data.get('positions', {})
            total_value = portfolio_data.get('metrics', {}).get('total_value', 0)
            
            total_loss = 0.0
            position_losses = []
            
            for symbol, position in positions.items():
                market_value = position.get('market_value', 0)
                position_loss = market_value * shock_factor
                total_loss += position_loss
                position_losses.append((symbol, position_loss))
            
            position_losses.sort(key=lambda x: x[1])
            worst_positions = position_losses[:5]
            
            return StressTestResult(
                scenario=scenario,
                portfolio_loss=abs(total_loss),
                loss_percentage=abs(total_loss / total_value) if total_value > 0 else 0.0,
                worst_positions=worst_positions,
                scenario_description=description
            )
            
        except Exception as e:
            logger.error(f"Error in {scenario} scenario: {e}")
            return StressTestResult(
                scenario=scenario,
                portfolio_loss=0.0,
                loss_percentage=0.0,
                worst_positions=[],
                scenario_description=f"Error: {str(e)}"
            )

class CorrelationAnalyzer:
    """Correlation analysis and breakdown detection"""
    
    def __init__(self, lookback_period: int = 252):
        self.lookback_period = lookback_period
        
    def analyze_correlations(self, returns_data: pd.DataFrame) -> CorrelationAnalysis:
        """Comprehensive correlation analysis"""
        try:
            if len(returns_data) < 50:
                logger.warning("Insufficient data for correlation analysis")
                return CorrelationAnalysis(
                    correlation_matrix=pd.DataFrame(),
                    average_correlation=0.0,
                    max_correlation=0.0,
                    min_correlation=0.0,
                    correlation_clusters=[],
                    breakdown_risk=0.0
                )
            
            # Calculate correlation matrix
            correlation_matrix = returns_data.corr()
            
            # Calculate statistics
            correlation_values = correlation_matrix.values
            np.fill_diagonal(correlation_values, np.nan)  # Exclude diagonal
            
            avg_correlation = np.nanmean(correlation_values)
            max_correlation = np.nanmax(correlation_values)
            min_correlation = np.nanmin(correlation_values)
            
            # Identify correlation clusters
            clusters = self._identify_correlation_clusters(correlation_matrix)
            
            # Calculate breakdown risk
            breakdown_risk = self._calculate_breakdown_risk(correlation_matrix, returns_data)
            
            return CorrelationAnalysis(
                correlation_matrix=correlation_matrix,
                average_correlation=avg_correlation,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                correlation_clusters=clusters,
                breakdown_risk=breakdown_risk
            )
            
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            return CorrelationAnalysis(
                correlation_matrix=pd.DataFrame(),
                average_correlation=0.0,
                max_correlation=0.0,
                min_correlation=0.0,
                correlation_clusters=[],
                breakdown_risk=0.0
            )
    
    def _identify_correlation_clusters(self, correlation_matrix: pd.DataFrame,
                                     threshold: float = 0.7) -> List[List[str]]:
        """Identify groups of highly correlated assets"""
        try:
            clusters = []
            assets = correlation_matrix.index.tolist()
            processed = set()
            
            for asset in assets:
                if asset in processed:
                    continue
                
                # Find highly correlated assets
                highly_correlated = correlation_matrix[asset][
                    correlation_matrix[asset] >= threshold
                ].index.tolist()
                
                if len(highly_correlated) > 1:
                    clusters.append(highly_correlated)
                    processed.update(highly_correlated)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error identifying correlation clusters: {e}")
            return []
    
    def _calculate_breakdown_risk(self, correlation_matrix: pd.DataFrame, 
                                returns_data: pd.DataFrame) -> float:
        """Calculate risk of correlation breakdown"""
        try:
            # Calculate rolling correlations
            window = min(60, len(returns_data) // 4)
            rolling_corrs = []
            
            for i in range(window, len(returns_data)):
                window_data = returns_data.iloc[i-window:i]
                window_corr = window_data.corr()
                avg_corr = np.nanmean(window_corr.values[np.triu_indices_from(window_corr.values, k=1)])
                rolling_corrs.append(avg_corr)
            
            if len(rolling_corrs) < 10:
                return 0.5  # Default medium risk
            
            # Calculate volatility of correlations
            corr_volatility = np.std(rolling_corrs)
            
            # Higher volatility = higher breakdown risk
            breakdown_risk = min(1.0, corr_volatility * 5)  # Scale to 0-1
            
            return breakdown_risk
            
        except Exception as e:
            logger.error(f"Error calculating breakdown risk: {e}")
            return 0.5

class DrawdownAnalyzer:
    """Maximum drawdown analysis"""
    
    def __init__(self):
        pass
        
    def calculate_drawdown_metrics(self, portfolio_values: pd.Series) -> Dict[str, Any]:
        """Calculate comprehensive drawdown metrics"""
        try:
            if len(portfolio_values) < 2:
                return {
                    'max_drawdown': 0.0,
                    'current_drawdown': 0.0,
                    'drawdown_duration': 0,
                    'recovery_time': 0,
                    'drawdown_series': pd.Series()
                }
            
            # Calculate running maximum
            running_max = portfolio_values.expanding().max()
            
            # Calculate drawdown series
            drawdown_series = (portfolio_values - running_max) / running_max
            
            # Maximum drawdown
            max_drawdown = drawdown_series.min()
            
            # Current drawdown
            current_drawdown = drawdown_series.iloc[-1]
            
            # Drawdown duration
            drawdown_duration = self._calculate_drawdown_duration(drawdown_series)
            
            # Recovery time
            recovery_time = self._calculate_recovery_time(drawdown_series)
            
            return {
                'max_drawdown': abs(max_drawdown),
                'current_drawdown': abs(current_drawdown),
                'drawdown_duration': drawdown_duration,
                'recovery_time': recovery_time,
                'drawdown_series': drawdown_series
            }
            
        except Exception as e:
            logger.error(f"Error calculating drawdown metrics: {e}")
            return {
                'max_drawdown': 0.0,
                'current_drawdown': 0.0,
                'drawdown_duration': 0,
                'recovery_time': 0,
                'drawdown_series': pd.Series()
            }
    
    def _calculate_drawdown_duration(self, drawdown_series: pd.Series) -> int:
        """Calculate current drawdown duration"""
        try:
            # Find current drawdown period
            current_dd_start = None
            for i in range(len(drawdown_series) - 1, -1, -1):
                if drawdown_series.iloc[i] == 0:
                    current_dd_start = i + 1
                    break
            
            if current_dd_start is None:
                return len(drawdown_series)
            
            return len(drawdown_series) - current_dd_start
            
        except Exception as e:
            logger.error(f"Error calculating drawdown duration: {e}")
            return 0
    
    def _calculate_recovery_time(self, drawdown_series: pd.Series) -> int:
        """Calculate average recovery time"""
        try:
            recovery_times = []
            in_drawdown = False
            drawdown_start = None
            
            for i, dd in enumerate(drawdown_series):
                if dd < 0 and not in_drawdown:
                    # Start of drawdown
                    in_drawdown = True
                    drawdown_start = i
                elif dd == 0 and in_drawdown:
                    # End of drawdown
                    in_drawdown = False
                    if drawdown_start is not None:
                        recovery_times.append(i - drawdown_start)
            
            return int(np.mean(recovery_times)) if recovery_times else 0
            
        except Exception as e:
            logger.error(f"Error calculating recovery time: {e}")
            return 0

class RiskMetrics:
    """
    Comprehensive Risk Metrics System
    
    Provides advanced risk calculations including:
    - Value at Risk (multiple methods)
    - Conditional Value at Risk
    - Stress testing
    - Correlation analysis
    - Drawdown analysis
    """
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        
        # Initialize component calculators
        self.var_calculator = VaRCalculator(confidence_level)
        self.cvar_calculator = CVaRCalculator(confidence_level)
        self.stress_tester = StressTestEngine()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.drawdown_analyzer = DrawdownAnalyzer()
        
        logger.info(f"Risk metrics system initialized with {confidence_level:.1%} confidence")
    
    def calculate_comprehensive_risk(self, portfolio_data: Dict[str, Any],
                                   returns_data: pd.DataFrame,
                                   portfolio_values: pd.Series) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics"""
        try:
            portfolio_returns = portfolio_values.pct_change().dropna()
            portfolio_value = portfolio_data.get('metrics', {}).get('total_value', 1000000)
            
            # VaR calculations
            var_historical = self.var_calculator.calculate_var(
                portfolio_returns, VaRMethod.HISTORICAL, portfolio_value
            )
            var_parametric = self.var_calculator.calculate_var(
                portfolio_returns, VaRMethod.PARAMETRIC, portfolio_value
            )
            var_monte_carlo = self.var_calculator.calculate_var(
                portfolio_returns, VaRMethod.MONTE_CARLO, portfolio_value
            )
            
            # CVaR calculation
            cvar_result = self.cvar_calculator.calculate_cvar(portfolio_returns, portfolio_value)
            
            # Stress testing
            stress_results = self.stress_tester.run_all_stress_tests(portfolio_data)
            
            # Correlation analysis
            correlation_analysis = self.correlation_analyzer.analyze_correlations(returns_data)
            
            # Drawdown analysis
            drawdown_metrics = self.drawdown_analyzer.calculate_drawdown_metrics(portfolio_values)
            
            return {
                'var_metrics': {
                    'historical': var_historical,
                    'parametric': var_parametric,
                    'monte_carlo': var_monte_carlo
                },
                'cvar_metrics': cvar_result,
                'stress_test_results': stress_results,
                'correlation_analysis': correlation_analysis,
                'drawdown_metrics': drawdown_metrics,
                'risk_summary': {
                    'worst_var': max(var_historical.var_value, var_parametric.var_value, var_monte_carlo.var_value),
                    'expected_shortfall': cvar_result.expected_shortfall,
                    'worst_stress_loss': max([s.loss_percentage for s in stress_results]),
                    'correlation_risk': correlation_analysis.breakdown_risk,
                    'current_drawdown': drawdown_metrics['current_drawdown']
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive risk: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk metrics system summary"""
        return {
            'risk_metrics_status': 'active',
            'confidence_level': self.confidence_level,
            'available_methods': {
                'var_methods': [method.value for method in VaRMethod],
                'stress_scenarios': [scenario.value for scenario in StressTestScenario]
            },
            'components': {
                'var_calculator': 'active',
                'cvar_calculator': 'active',
                'stress_tester': 'active',
                'correlation_analyzer': 'active',
                'drawdown_analyzer': 'active'
            }
        } 