"""
Performance Analytics and Attribution System

Professional-grade performance analytics providing:
- Comprehensive performance metrics calculation
- Multi-factor attribution analysis
- Risk-adjusted performance measurement
- Benchmark comparison and tracking
- Sector and factor analysis
- Real-time performance monitoring

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class PerformanceFrequency(Enum):
    """Performance calculation frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class AttributionModel(Enum):
    """Attribution model types"""
    BRINSON = "brinson"
    FACTOR_MODEL = "factor_model"
    HOLDINGS_BASED = "holdings_based"
    TRANSACTION_BASED = "transaction_based"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    # Basic returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    cumulative_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    annualized_volatility: float = 0.0
    downside_deviation: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    current_drawdown: float = 0.0
    
    # Distribution metrics
    skewness: float = 0.0
    kurtosis: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Benchmark comparison
    alpha: float = 0.0
    beta: float = 0.0
    correlation: float = 0.0
    tracking_error: float = 0.0
    
    # Win/Loss metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Additional metrics
    recovery_factor: float = 0.0
    sterling_ratio: float = 0.0
    burke_ratio: float = 0.0
    
    # Metadata
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    total_periods: int = 0
    risk_free_rate: float = 0.02


@dataclass
class AttributionReport:
    """Performance attribution report"""
    total_return: float = 0.0
    benchmark_return: float = 0.0
    active_return: float = 0.0
    
    # Brinson attribution
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    
    # Factor attribution
    factor_returns: Dict[str, float] = field(default_factory=dict)
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Sector attribution
    sector_returns: Dict[str, float] = field(default_factory=dict)
    sector_weights: Dict[str, float] = field(default_factory=dict)
    sector_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Security-level attribution
    security_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Unexplained return
    unexplained_return: float = 0.0
    
    # Metadata
    attribution_model: AttributionModel = AttributionModel.BRINSON
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)


class PerformanceAnalyzer:
    """
    Comprehensive performance analytics engine
    
    Features:
    - Multi-frequency performance calculation
    - Risk-adjusted performance metrics
    - Benchmark comparison and tracking
    - Rolling performance analysis
    - Regime-based performance analysis
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize performance analyzer
        
        Args:
            risk_free_rate: Risk-free rate for calculations
        """
        self.risk_free_rate = risk_free_rate
        self.logger = logging.getLogger(__name__)
        
        # Performance cache
        self.performance_cache = {}
        self.benchmark_cache = {}
        
        # Configuration
        self.trading_days_per_year = 252
        self.confidence_level = 0.95
        
        self.logger.info("PerformanceAnalyzer initialized with institutional-grade capabilities")
    
    def calculate_performance_metrics(self, 
                                    returns: pd.Series,
                                    benchmark_returns: Optional[pd.Series] = None,
                                    frequency: PerformanceFrequency = PerformanceFrequency.DAILY) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics
        
        Args:
            returns: Return series
            benchmark_returns: Benchmark return series
            frequency: Return frequency
            
        Returns:
            PerformanceMetrics object
        """
        if len(returns) == 0:
            return PerformanceMetrics()
        
        # Convert frequency to annualization factor
        freq_map = {
            PerformanceFrequency.DAILY: 252,
            PerformanceFrequency.WEEKLY: 52,
            PerformanceFrequency.MONTHLY: 12,
            PerformanceFrequency.QUARTERLY: 4,
            PerformanceFrequency.YEARLY: 1
        }
        
        annualization_factor = freq_map[frequency]
        
        # Basic return metrics
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (annualization_factor / len(returns)) - 1
        cumulative_return = total_return
        
        # Risk metrics
        volatility = returns.std()
        annualized_volatility = volatility * np.sqrt(annualization_factor)
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(annualization_factor)
        
        # Risk-adjusted metrics
        excess_returns = returns - self.risk_free_rate / annualization_factor
        sharpe_ratio = excess_returns.mean() / volatility * np.sqrt(annualization_factor) if volatility > 0 else 0
        
        downside_excess = returns - self.risk_free_rate / annualization_factor
        sortino_ratio = (downside_excess.mean() / downside_deviation * np.sqrt(annualization_factor) 
                        if downside_deviation > 0 else 0)
        
        # Drawdown analysis
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        
        max_drawdown = drawdowns.min()
        max_drawdown_duration = self._calculate_max_drawdown_duration(drawdowns)
        current_drawdown = drawdowns.iloc[-1]
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Distribution metrics
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        var_95 = returns.quantile(1 - self.confidence_level)
        cvar_95 = returns[returns <= var_95].mean()
        
        # Benchmark comparison
        alpha, beta, correlation, tracking_error, information_ratio = 0, 0, 0, 0, 0
        
        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            # Align returns
            aligned_returns = returns.align(benchmark_returns, join='inner')
            portfolio_returns, bench_returns = aligned_returns
            
            if len(portfolio_returns) > 1:
                # Beta and alpha calculation
                covariance = np.cov(portfolio_returns, bench_returns)[0, 1]
                benchmark_variance = np.var(bench_returns)
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
                
                alpha = (portfolio_returns.mean() - self.risk_free_rate / annualization_factor) - \
                       beta * (bench_returns.mean() - self.risk_free_rate / annualization_factor)
                alpha *= annualization_factor  # Annualize alpha
                
                # Correlation and tracking error
                correlation = np.corrcoef(portfolio_returns, bench_returns)[0, 1]
                active_returns = portfolio_returns - bench_returns
                tracking_error = active_returns.std() * np.sqrt(annualization_factor)
                
                # Information ratio
                information_ratio = (active_returns.mean() / active_returns.std() * 
                                   np.sqrt(annualization_factor) if active_returns.std() > 0 else 0)
        
        # Win/Loss metrics
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]
        
        win_rate = len(winning_returns) / len(returns) * 100
        avg_win = winning_returns.mean() if len(winning_returns) > 0 else 0
        avg_loss = losing_returns.mean() if len(losing_returns) > 0 else 0
        
        profit_factor = (winning_returns.sum() / abs(losing_returns.sum()) 
                        if len(losing_returns) > 0 and losing_returns.sum() < 0 else 0)
        
        # Additional ratios
        recovery_factor = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        sterling_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        burke_ratio = annualized_return / np.sqrt((drawdowns ** 2).sum()) if len(drawdowns) > 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=cumulative_return,
            volatility=volatility,
            annualized_volatility=annualized_volatility,
            downside_deviation=downside_deviation,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            current_drawdown=current_drawdown,
            skewness=skewness,
            kurtosis=kurtosis,
            var_95=var_95,
            cvar_95=cvar_95,
            alpha=alpha,
            beta=beta,
            correlation=correlation,
            tracking_error=tracking_error,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            recovery_factor=recovery_factor,
            sterling_ratio=sterling_ratio,
            burke_ratio=burke_ratio,
            start_date=returns.index[0] if len(returns) > 0 else datetime.now(),
            end_date=returns.index[-1] if len(returns) > 0 else datetime.now(),
            total_periods=len(returns),
            risk_free_rate=self.risk_free_rate
        )
    
    def calculate_rolling_performance(self, 
                                    returns: pd.Series,
                                    window: int = 252,
                                    metrics: List[str] = None) -> pd.DataFrame:
        """
        Calculate rolling performance metrics
        
        Args:
            returns: Return series
            window: Rolling window size
            metrics: List of metrics to calculate
            
        Returns:
            DataFrame with rolling metrics
        """
        if metrics is None:
            metrics = ['sharpe_ratio', 'volatility', 'max_drawdown', 'alpha', 'beta']
        
        rolling_metrics = pd.DataFrame(index=returns.index)
        
        for metric in metrics:
            if metric == 'sharpe_ratio':
                excess_returns = returns - self.risk_free_rate / 252
                rolling_metrics[metric] = (
                    excess_returns.rolling(window).mean() / 
                    returns.rolling(window).std() * np.sqrt(252)
                )
            elif metric == 'volatility':
                rolling_metrics[metric] = returns.rolling(window).std() * np.sqrt(252)
            elif metric == 'max_drawdown':
                rolling_metrics[metric] = returns.rolling(window).apply(
                    lambda x: self._calculate_max_drawdown(x)
                )
            # Add more metrics as needed
        
        return rolling_metrics
    
    def _calculate_max_drawdown_duration(self, drawdowns: pd.Series) -> int:
        """Calculate maximum drawdown duration"""
        is_drawdown = drawdowns < 0
        drawdown_periods = []
        current_period = 0
        
        for in_drawdown in is_drawdown:
            if in_drawdown:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        return max(drawdown_periods) if drawdown_periods else 0
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown for a return series"""
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        return drawdowns.min()
    
    def generate_performance_report(self, 
                                  returns: pd.Series,
                                  benchmark_returns: Optional[pd.Series] = None,
                                  frequency: PerformanceFrequency = PerformanceFrequency.DAILY) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        metrics = self.calculate_performance_metrics(returns, benchmark_returns, frequency)
        
        report = {
            'summary': {
                'total_return': f"{metrics.total_return:.2%}",
                'annualized_return': f"{metrics.annualized_return:.2%}",
                'volatility': f"{metrics.annualized_volatility:.2%}",
                'sharpe_ratio': f"{metrics.sharpe_ratio:.2f}",
                'max_drawdown': f"{metrics.max_drawdown:.2%}",
                'win_rate': f"{metrics.win_rate:.1f}%"
            },
            'risk_metrics': {
                'volatility': metrics.annualized_volatility,
                'downside_deviation': metrics.downside_deviation,
                'var_95': metrics.var_95,
                'cvar_95': metrics.cvar_95,
                'skewness': metrics.skewness,
                'kurtosis': metrics.kurtosis
            },
            'risk_adjusted_metrics': {
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'information_ratio': metrics.information_ratio
            },
            'drawdown_analysis': {
                'max_drawdown': metrics.max_drawdown,
                'max_drawdown_duration': metrics.max_drawdown_duration,
                'current_drawdown': metrics.current_drawdown,
                'recovery_factor': metrics.recovery_factor
            },
            'benchmark_comparison': {
                'alpha': metrics.alpha,
                'beta': metrics.beta,
                'correlation': metrics.correlation,
                'tracking_error': metrics.tracking_error
            } if benchmark_returns is not None else {},
            'metadata': {
                'start_date': metrics.start_date.strftime('%Y-%m-%d'),
                'end_date': metrics.end_date.strftime('%Y-%m-%d'),
                'total_periods': metrics.total_periods,
                'frequency': frequency.value
            }
        }
        
        return report


class AttributionAnalyzer:
    """
    Performance attribution analyzer
    
    Features:
    - Brinson attribution model
    - Factor-based attribution
    - Sector and security-level attribution
    - Holdings-based attribution
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def brinson_attribution(self, 
                          portfolio_weights: pd.Series,
                          benchmark_weights: pd.Series,
                          portfolio_returns: pd.Series,
                          benchmark_returns: pd.Series) -> AttributionReport:
        """
        Calculate Brinson attribution
        
        Args:
            portfolio_weights: Portfolio weights by sector/security
            benchmark_weights: Benchmark weights by sector/security
            portfolio_returns: Portfolio returns by sector/security
            benchmark_returns: Benchmark returns by sector/security
            
        Returns:
            AttributionReport with Brinson attribution
        """
        # Align data
        common_assets = portfolio_weights.index.intersection(benchmark_weights.index)
        
        pw = portfolio_weights.reindex(common_assets, fill_value=0)
        bw = benchmark_weights.reindex(common_assets, fill_value=0)
        pr = portfolio_returns.reindex(common_assets, fill_value=0)
        br = benchmark_returns.reindex(common_assets, fill_value=0)
        
        # Calculate attribution effects
        allocation_effect = ((pw - bw) * br).sum()
        selection_effect = (bw * (pr - br)).sum()
        interaction_effect = ((pw - bw) * (pr - br)).sum()
        
        # Calculate total returns
        portfolio_return = (pw * pr).sum()
        benchmark_return = (bw * br).sum()
        active_return = portfolio_return - benchmark_return
        
        return AttributionReport(
            total_return=portfolio_return,
            benchmark_return=benchmark_return,
            active_return=active_return,
            allocation_effect=allocation_effect,
            selection_effect=selection_effect,
            interaction_effect=interaction_effect,
            attribution_model=AttributionModel.BRINSON
        )
    
    def factor_attribution(self, 
                         returns: pd.Series,
                         factor_exposures: pd.DataFrame,
                         factor_returns: pd.Series) -> AttributionReport:
        """
        Calculate factor-based attribution
        
        Args:
            returns: Portfolio returns
            factor_exposures: Factor exposures over time
            factor_returns: Factor returns
            
        Returns:
            AttributionReport with factor attribution
        """
        # Calculate factor contributions
        factor_contributions = {}
        
        for factor in factor_exposures.columns:
            if factor in factor_returns.index:
                contribution = (factor_exposures[factor] * factor_returns[factor]).sum()
                factor_contributions[factor] = contribution
        
        # Calculate unexplained return
        total_factor_contribution = sum(factor_contributions.values())
        total_return = returns.sum()
        unexplained_return = total_return - total_factor_contribution
        
        return AttributionReport(
            total_return=total_return,
            factor_contributions=factor_contributions,
            unexplained_return=unexplained_return,
            attribution_model=AttributionModel.FACTOR_MODEL
        )


class RiskAnalyzer:
    """
    Risk analysis and monitoring
    
    Features:
    - Value at Risk (VaR) calculation
    - Expected Shortfall (ES) calculation
    - Risk factor decomposition
    - Stress testing
    - Risk budget analysis
    """
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.logger = logging.getLogger(__name__)
    
    def calculate_var(self, 
                     returns: pd.Series,
                     method: str = 'historical') -> float:
        """
        Calculate Value at Risk
        
        Args:
            returns: Return series
            method: VaR method ('historical', 'parametric', 'monte_carlo')
            
        Returns:
            VaR value
        """
        if method == 'historical':
            return returns.quantile(1 - self.confidence_level)
        elif method == 'parametric':
            mean = returns.mean()
            std = returns.std()
            return mean - std * stats.norm.ppf(self.confidence_level)
        else:
            # Monte Carlo method would be implemented here
            return self.calculate_var(returns, 'historical')
    
    def calculate_expected_shortfall(self, returns: pd.Series) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        var = self.calculate_var(returns)
        return returns[returns <= var].mean()
    
    def stress_test(self, 
                   returns: pd.Series,
                   scenarios: Dict[str, float]) -> Dict[str, float]:
        """
        Perform stress testing
        
        Args:
            returns: Return series
            scenarios: Stress scenarios
            
        Returns:
            Dictionary of stress test results
        """
        results = {}
        
        for scenario_name, shock in scenarios.items():
            # Apply shock to returns
            stressed_returns = returns + shock
            
            # Calculate metrics under stress
            stressed_var = self.calculate_var(stressed_returns)
            stressed_es = self.calculate_expected_shortfall(stressed_returns)
            
            results[scenario_name] = {
                'var': stressed_var,
                'expected_shortfall': stressed_es,
                'total_impact': stressed_returns.sum()
            }
        
        return results 