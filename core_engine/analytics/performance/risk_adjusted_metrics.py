"""
Performance Engine - Risk Adjusted Metrics
Advanced risk-adjusted performance measurement and analysis
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict
import threading
from abc import ABC, abstractmethod
import scipy.stats as stats

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class RiskAdjustmentMethod(Enum):
    """Risk adjustment methods"""
    SHARPE = "sharpe"
    SORTINO = "sortino"
    CALMAR = "calmar"
    OMEGA = "omega"
    TREYNOR = "treynor"
    JENSEN_ALPHA = "jensen_alpha"
    INFORMATION_RATIO = "information_ratio"
    MODIGLIANI = "modigliani"
    RAP = "rap"  # Risk Adjusted Performance
    RACHEV = "rachev"
    KAPPA = "kappa"


class RiskMetricType(Enum):
    """Types of risk metrics"""
    VOLATILITY = "volatility"
    DOWNSIDE_DEVIATION = "downside_deviation"
    VAR = "var"
    CVAR = "cvar"
    MAX_DRAWDOWN = "max_drawdown"
    SEMI_VARIANCE = "semi_variance"
    TAIL_RATIO = "tail_ratio"
    WORST_RETURN = "worst_return"


class PerformanceBenchmark(Enum):
    """Performance benchmark types"""
    RISK_FREE = "risk_free"
    MARKET_INDEX = "market_index"
    CUSTOM_BENCHMARK = "custom_benchmark"
    MINIMUM_RETURN = "minimum_return"
    ZERO_RETURN = "zero_return"


@dataclass
class RiskAdjustedMetrics:
    """Container for risk-adjusted performance metrics"""
    
    # Classic risk-adjusted ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Market-relative metrics
    treynor_ratio: float = 0.0
    jensen_alpha: float = 0.0
    information_ratio: float = 0.0
    modigliani_ratio: float = 0.0
    
    # Advanced metrics
    rap_ratio: float = 0.0  # Risk Adjusted Performance
    rachev_ratio: float = 0.0
    kappa_3: float = 0.0  # Third moment
    kappa_4: float = 0.0  # Fourth moment
    
    # Tail risk metrics
    tail_ratio: float = 0.0
    gain_loss_ratio: float = 0.0
    pain_ratio: float = 0.0
    sterling_ratio: float = 0.0
    
    # Probabilistic metrics
    probabilistic_sharpe: float = 0.0
    deflated_sharpe: float = 0.0
    
    # Component metrics used in calculations
    excess_return: float = 0.0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Market metrics (when benchmark provided)
    beta: float = 0.0
    alpha: float = 0.0
    correlation: float = 0.0
    tracking_error: float = 0.0
    
    # Confidence intervals
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0
    
    # Metadata
    calculation_period: str = ""
    risk_free_rate: float = 0.0
    benchmark_name: str = ""
    calculation_time: datetime = field(default_factory=datetime.now)


@dataclass
class RiskAdjustedConfig:
    """Configuration for risk-adjusted metrics calculation"""
    
    # Basic settings
    risk_free_rate: float = 0.02  # 2% annual
    confidence_level: float = 0.95
    business_days_per_year: int = 252
    
    # Calculation settings
    min_periods: int = 30
    annualization_factor: Optional[float] = None  # Auto-calculate if None
    
    # Risk adjustment methods to calculate
    methods: List[RiskAdjustmentMethod] = field(default_factory=lambda: [
        RiskAdjustmentMethod.SHARPE,
        RiskAdjustmentMethod.SORTINO,
        RiskAdjustmentMethod.CALMAR,
        RiskAdjustmentMethod.OMEGA
    ])
    
    # Advanced settings
    calculate_confidence_intervals: bool = True
    calculate_probabilistic_metrics: bool = True
    omega_threshold: float = 0.0  # Return threshold for Omega ratio
    
    # Tail risk settings
    var_confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    tail_threshold: float = 0.1  # 10% for tail ratio calculation
    
    # Benchmark settings
    benchmark_type: PerformanceBenchmark = PerformanceBenchmark.RISK_FREE
    custom_benchmark_returns: Optional[pd.Series] = None


class ClassicRiskAdjustedCalculator:
    """Calculate classic risk-adjusted performance metrics"""
    
    def __init__(self, config: RiskAdjustedConfig):
        self.config = config
        
        logger.info("Classic risk-adjusted calculator initialized")
    
    def calculate_sharpe_ratio(self, returns: np.ndarray, 
                             risk_free_rate: Optional[float] = None) -> float:
        """Calculate Sharpe ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            
            # Convert annual risk-free rate to period rate
            period_rf_rate = rf_rate / self.config.business_days_per_year
            
            # Calculate excess returns
            excess_returns = returns - period_rf_rate
            
            # Calculate Sharpe ratio
            mean_excess = np.mean(excess_returns)
            std_returns = np.std(returns, ddof=1)
            
            if std_returns == 0:
                return 0.0
            
            sharpe = mean_excess / std_returns
            
            # Annualize
            annualization = self._get_annualization_factor()
            sharpe_annualized = sharpe * np.sqrt(annualization)
            
            return sharpe_annualized
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def calculate_sortino_ratio(self, returns: np.ndarray,
                              risk_free_rate: Optional[float] = None,
                              target_return: Optional[float] = None) -> float:
        """Calculate Sortino ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            target = target_return or (rf_rate / self.config.business_days_per_year)
            
            # Calculate excess returns
            excess_returns = returns - target
            mean_excess = np.mean(excess_returns)
            
            # Calculate downside deviation
            downside_returns = returns[returns < target]
            if len(downside_returns) == 0:
                return float('inf') if mean_excess > 0 else 0.0
            
            downside_deviation = np.std(downside_returns, ddof=1)
            
            if downside_deviation == 0:
                return float('inf') if mean_excess > 0 else 0.0
            
            sortino = mean_excess / downside_deviation
            
            # Annualize
            annualization = self._get_annualization_factor()
            sortino_annualized = sortino * np.sqrt(annualization)
            
            return sortino_annualized
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0
    
    def calculate_calmar_ratio(self, returns: np.ndarray) -> float:
        """Calculate Calmar ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate annualized return
            total_return = np.prod(1 + returns) - 1
            years = len(returns) / self.config.business_days_per_year
            annualized_return = (1 + total_return) ** (1 / years) - 1
            
            # Calculate maximum drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = np.min(drawdown)
            
            if max_drawdown == 0:
                return float('inf') if annualized_return > 0 else 0.0
            
            calmar = annualized_return / abs(max_drawdown)
            
            return calmar
            
        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0
    
    def calculate_omega_ratio(self, returns: np.ndarray,
                            threshold: Optional[float] = None) -> float:
        """Calculate Omega ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            threshold_return = threshold or self.config.omega_threshold
            
            # Separate gains and losses relative to threshold
            excess_returns = returns - threshold_return
            gains = excess_returns[excess_returns > 0]
            losses = excess_returns[excess_returns <= 0]
            
            # Calculate Omega ratio
            gain_sum = np.sum(gains) if len(gains) > 0 else 0.0
            loss_sum = abs(np.sum(losses)) if len(losses) > 0 else 0.0
            
            if loss_sum == 0:
                return float('inf') if gain_sum > 0 else 1.0
            
            omega = 1 + (gain_sum / loss_sum)
            
            return omega
            
        except Exception as e:
            logger.error(f"Error calculating Omega ratio: {e}")
            return 0.0
    
    def _get_annualization_factor(self) -> float:
        """Get annualization factor"""
        
        if self.config.annualization_factor:
            return self.config.annualization_factor
        else:
            return self.config.business_days_per_year


class MarketRelativeCalculator:
    """Calculate market-relative risk-adjusted metrics"""
    
    def __init__(self, config: RiskAdjustedConfig):
        self.config = config
        
        logger.info("Market-relative calculator initialized")
    
    def calculate_treynor_ratio(self, returns: np.ndarray,
                              market_returns: np.ndarray,
                              risk_free_rate: Optional[float] = None) -> Tuple[float, float]:
        """Calculate Treynor ratio and beta"""
        
        try:
            if len(returns) != len(market_returns) or len(returns) < self.config.min_periods:
                return 0.0, 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            period_rf_rate = rf_rate / self.config.business_days_per_year
            
            # Calculate excess returns
            portfolio_excess = returns - period_rf_rate
            market_excess = market_returns - period_rf_rate
            
            # Calculate beta
            beta = self._calculate_beta(portfolio_excess, market_excess)
            
            if beta == 0:
                return 0.0, beta
            
            # Calculate Treynor ratio
            mean_portfolio_excess = np.mean(portfolio_excess)
            treynor = mean_portfolio_excess / beta
            
            # Annualize
            annualization = self._get_annualization_factor()
            treynor_annualized = treynor * annualization
            
            return treynor_annualized, beta
            
        except Exception as e:
            logger.error(f"Error calculating Treynor ratio: {e}")
            return 0.0, 0.0
    
    def calculate_jensen_alpha(self, returns: np.ndarray,
                             market_returns: np.ndarray,
                             risk_free_rate: Optional[float] = None) -> Tuple[float, float, float]:
        """Calculate Jensen's alpha, beta, and R-squared"""
        
        try:
            if len(returns) != len(market_returns) or len(returns) < self.config.min_periods:
                return 0.0, 0.0, 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            period_rf_rate = rf_rate / self.config.business_days_per_year
            
            # Calculate excess returns
            portfolio_excess = returns - period_rf_rate
            market_excess = market_returns - period_rf_rate
            
            # Calculate regression
            beta = self._calculate_beta(portfolio_excess, market_excess)
            
            # Calculate alpha
            portfolio_mean = np.mean(portfolio_excess)
            market_mean = np.mean(market_excess)
            alpha = portfolio_mean - beta * market_mean
            
            # Calculate R-squared
            correlation = np.corrcoef(portfolio_excess, market_excess)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0.0
            
            # Annualize alpha
            annualization = self._get_annualization_factor()
            alpha_annualized = alpha * annualization
            
            return alpha_annualized, beta, r_squared
            
        except Exception as e:
            logger.error(f"Error calculating Jensen's alpha: {e}")
            return 0.0, 0.0, 0.0
    
    def calculate_information_ratio(self, returns: np.ndarray,
                                  benchmark_returns: np.ndarray) -> Tuple[float, float]:
        """Calculate Information ratio and tracking error"""
        
        try:
            if len(returns) != len(benchmark_returns) or len(returns) < self.config.min_periods:
                return 0.0, 0.0
            
            # Calculate excess returns (active returns)
            active_returns = returns - benchmark_returns
            
            # Calculate information ratio
            mean_active = np.mean(active_returns)
            tracking_error = np.std(active_returns, ddof=1)
            
            if tracking_error == 0:
                return 0.0, tracking_error
            
            information_ratio = mean_active / tracking_error
            
            # Annualize
            annualization = self._get_annualization_factor()
            information_ratio_annualized = information_ratio * np.sqrt(annualization)
            tracking_error_annualized = tracking_error * np.sqrt(annualization)
            
            return information_ratio_annualized, tracking_error_annualized
            
        except Exception as e:
            logger.error(f"Error calculating Information ratio: {e}")
            return 0.0, 0.0
    
    def calculate_modigliani_ratio(self, returns: np.ndarray,
                                 market_returns: np.ndarray,
                                 risk_free_rate: Optional[float] = None) -> float:
        """Calculate Modigliani-Modigliani ratio (M²)"""
        
        try:
            if len(returns) != len(market_returns) or len(returns) < self.config.min_periods:
                return 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            
            # Calculate Sharpe ratios
            portfolio_sharpe = self.calculate_sharpe_ratio(returns, rf_rate)
            market_sharpe = self.calculate_sharpe_ratio(market_returns, rf_rate)
            
            # Calculate market volatility
            market_vol = np.std(market_returns, ddof=1) * np.sqrt(self._get_annualization_factor())
            
            # Calculate M² ratio
            modigliani = (portfolio_sharpe - market_sharpe) * market_vol
            
            return modigliani
            
        except Exception as e:
            logger.error(f"Error calculating Modigliani ratio: {e}")
            return 0.0
    
    def calculate_sharpe_ratio(self, returns: np.ndarray,
                             risk_free_rate: Optional[float] = None) -> float:
        """Helper method to calculate Sharpe ratio"""
        
        calculator = ClassicRiskAdjustedCalculator(self.config)
        return calculator.calculate_sharpe_ratio(returns, risk_free_rate)
    
    def _calculate_beta(self, portfolio_excess: np.ndarray,
                       market_excess: np.ndarray) -> float:
        """Calculate beta coefficient"""
        
        try:
            covariance = np.cov(portfolio_excess, market_excess)[0, 1]
            market_variance = np.var(market_excess, ddof=1)
            
            if market_variance == 0:
                return 0.0
            
            beta = covariance / market_variance
            return beta
            
        except Exception as e:
            logger.error(f"Error calculating beta: {e}")
            return 0.0
    
    def _get_annualization_factor(self) -> float:
        """Get annualization factor"""
        
        if self.config.annualization_factor:
            return self.config.annualization_factor
        else:
            return self.config.business_days_per_year


class AdvancedRiskCalculator:
    """Calculate advanced risk-adjusted metrics"""
    
    def __init__(self, config: RiskAdjustedConfig):
        self.config = config
        
        logger.info("Advanced risk calculator initialized")
    
    def calculate_rap_ratio(self, returns: np.ndarray) -> float:
        """Calculate Risk Adjusted Performance (RAP) ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate mean return
            mean_return = np.mean(returns)
            
            # Calculate modified risk measure (combines volatility and VaR)
            volatility = np.std(returns, ddof=1)
            var_95 = np.percentile(returns, 5)  # 5% VaR
            
            # RAP risk measure
            risk_measure = volatility + abs(var_95)
            
            if risk_measure == 0:
                return 0.0
            
            rap_ratio = mean_return / risk_measure
            
            # Annualize
            annualization = self._get_annualization_factor()
            rap_annualized = rap_ratio * np.sqrt(annualization)
            
            return rap_annualized
            
        except Exception as e:
            logger.error(f"Error calculating RAP ratio: {e}")
            return 0.0
    
    def calculate_rachev_ratio(self, returns: np.ndarray,
                             alpha: float = 0.05,
                             beta: float = 0.05) -> float:
        """Calculate Rachev ratio (CVaR-based ratio)"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate CVaR for upper tail (gains)
            upper_threshold = np.percentile(returns, (1 - alpha) * 100)
            upper_tail = returns[returns >= upper_threshold]
            cvar_upper = np.mean(upper_tail) if len(upper_tail) > 0 else 0.0
            
            # Calculate CVaR for lower tail (losses)
            lower_threshold = np.percentile(returns, beta * 100)
            lower_tail = returns[returns <= lower_threshold]
            cvar_lower = np.mean(lower_tail) if len(lower_tail) > 0 else 0.0
            
            if cvar_lower == 0:
                return float('inf') if cvar_upper > 0 else 0.0
            
            rachev_ratio = cvar_upper / abs(cvar_lower)
            
            return rachev_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Rachev ratio: {e}")
            return 0.0
    
    def calculate_kappa_ratios(self, returns: np.ndarray,
                             risk_free_rate: Optional[float] = None) -> Tuple[float, float]:
        """Calculate Kappa ratios (3rd and 4th moment)"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0, 0.0
            
            rf_rate = risk_free_rate or self.config.risk_free_rate
            period_rf_rate = rf_rate / self.config.business_days_per_year
            
            excess_returns = returns - period_rf_rate
            mean_excess = np.mean(excess_returns)
            
            # Calculate higher moments
            # Third moment (related to skewness)
            below_target = excess_returns[excess_returns < 0]
            if len(below_target) > 0:
                third_moment = np.mean(below_target ** 3)
                kappa_3 = mean_excess / abs(third_moment) ** (1/3) if third_moment != 0 else 0.0
            else:
                kappa_3 = float('inf') if mean_excess > 0 else 0.0
            
            # Fourth moment (related to kurtosis)
            if len(below_target) > 0:
                fourth_moment = np.mean(below_target ** 4)
                kappa_4 = mean_excess / abs(fourth_moment) ** (1/4) if fourth_moment != 0 else 0.0
            else:
                kappa_4 = float('inf') if mean_excess > 0 else 0.0
            
            return kappa_3, kappa_4
            
        except Exception as e:
            logger.error(f"Error calculating Kappa ratios: {e}")
            return 0.0, 0.0
    
    def calculate_tail_ratio(self, returns: np.ndarray,
                           threshold: Optional[float] = None) -> float:
        """Calculate tail ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            tail_pct = threshold or self.config.tail_threshold
            
            # Calculate upper and lower tail averages
            upper_threshold = np.percentile(returns, (1 - tail_pct) * 100)
            lower_threshold = np.percentile(returns, tail_pct * 100)
            
            upper_tail = returns[returns >= upper_threshold]
            lower_tail = returns[returns <= lower_threshold]
            
            upper_avg = np.mean(upper_tail) if len(upper_tail) > 0 else 0.0
            lower_avg = np.mean(lower_tail) if len(lower_tail) > 0 else 0.0
            
            if lower_avg == 0:
                return float('inf') if upper_avg > 0 else 0.0
            
            tail_ratio = upper_avg / abs(lower_avg)
            
            return tail_ratio
            
        except Exception as e:
            logger.error(f"Error calculating tail ratio: {e}")
            return 0.0
    
    def calculate_pain_ratio(self, returns: np.ndarray) -> float:
        """Calculate pain ratio (return/pain index)"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate cumulative returns and drawdowns
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            
            # Pain index is average of squared drawdowns
            pain_index = np.mean(drawdowns ** 2)
            
            if pain_index == 0:
                return 0.0
            
            # Calculate total return
            total_return = cumulative[-1] - 1
            
            pain_ratio = total_return / pain_index
            
            return pain_ratio
            
        except Exception as e:
            logger.error(f"Error calculating pain ratio: {e}")
            return 0.0
    
    def calculate_sterling_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sterling ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate annualized return
            total_return = np.prod(1 + returns) - 1
            years = len(returns) / self.config.business_days_per_year
            annualized_return = (1 + total_return) ** (1 / years) - 1
            
            # Calculate average drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            
            avg_drawdown = np.mean(abs(drawdowns))
            
            if avg_drawdown == 0:
                return float('inf') if annualized_return > 0 else 0.0
            
            sterling_ratio = annualized_return / avg_drawdown
            
            return sterling_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Sterling ratio: {e}")
            return 0.0
    
    def calculate_probabilistic_sharpe(self, returns: np.ndarray,
                                     risk_free_rate: Optional[float] = None,
                                     benchmark_sharpe: float = 0.0) -> float:
        """Calculate probabilistic Sharpe ratio"""
        
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            # Calculate observed Sharpe ratio
            calculator = ClassicRiskAdjustedCalculator(self.config)
            observed_sharpe = calculator.calculate_sharpe_ratio(returns, risk_free_rate)
            
            # Calculate standard error of Sharpe ratio
            n = len(returns)
            sharpe_std_error = np.sqrt((1 + (observed_sharpe ** 2) / 2) / n)
            
            # Calculate z-score
            z_score = (observed_sharpe - benchmark_sharpe) / sharpe_std_error
            
            # Calculate probability that true Sharpe > benchmark Sharpe
            prob_sharpe = stats.norm.cdf(z_score)
            
            return prob_sharpe
            
        except Exception as e:
            logger.error(f"Error calculating probabilistic Sharpe ratio: {e}")
            return 0.0
    
    def _get_annualization_factor(self) -> float:
        """Get annualization factor"""
        
        if self.config.annualization_factor:
            return self.config.annualization_factor
        else:
            return self.config.business_days_per_year


class RiskAdjustedMetricsCalculator:
    """
    Comprehensive Risk-Adjusted Metrics Calculator
    
    Calculates a full suite of risk-adjusted performance metrics
    including classic ratios, market-relative measures, and advanced metrics.
    """
    
    def __init__(self, config: Optional[RiskAdjustedConfig] = None):
        """Initialize risk-adjusted metrics calculator"""
        
        self.config = config or RiskAdjustedConfig()
        
        # Component calculators
        self._classic_calculator = ClassicRiskAdjustedCalculator(self.config)
        self._market_calculator = MarketRelativeCalculator(self.config)
        self._advanced_calculator = AdvancedRiskCalculator(self.config)
        
        # Calculation cache
        self._metrics_cache: Dict[str, RiskAdjustedMetrics] = {}
        
        # Performance tracking
        self._calculation_stats = {
            'total_calculations': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'last_calculation_time': None
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Risk-adjusted metrics calculator initialized")
    
    def calculate_all_metrics(self, returns: Union[pd.Series, np.ndarray],
                            market_returns: Optional[Union[pd.Series, np.ndarray]] = None,
                            benchmark_returns: Optional[Union[pd.Series, np.ndarray]] = None,
                            identifier: str = "default") -> RiskAdjustedMetrics:
        """Calculate comprehensive risk-adjusted metrics"""
        
        try:
            with self._lock:
                self._calculation_stats['total_calculations'] += 1
                
                # Convert inputs to numpy arrays
                if isinstance(returns, pd.Series):
                    returns_array = returns.values
                else:
                    returns_array = returns
                
                market_array = None
                if market_returns is not None:
                    if isinstance(market_returns, pd.Series):
                        market_array = market_returns.values
                    else:
                        market_array = market_returns
                
                benchmark_array = None
                if benchmark_returns is not None:
                    if isinstance(benchmark_returns, pd.Series):
                        benchmark_array = benchmark_returns.values
                    else:
                        benchmark_array = benchmark_returns
                
                # Initialize metrics container
                metrics = RiskAdjustedMetrics()
                
                # Calculate classic risk-adjusted ratios
                if RiskAdjustmentMethod.SHARPE in self.config.methods:
                    metrics.sharpe_ratio = self._classic_calculator.calculate_sharpe_ratio(returns_array)
                
                if RiskAdjustmentMethod.SORTINO in self.config.methods:
                    metrics.sortino_ratio = self._classic_calculator.calculate_sortino_ratio(returns_array)
                
                if RiskAdjustmentMethod.CALMAR in self.config.methods:
                    metrics.calmar_ratio = self._classic_calculator.calculate_calmar_ratio(returns_array)
                
                if RiskAdjustmentMethod.OMEGA in self.config.methods:
                    metrics.omega_ratio = self._classic_calculator.calculate_omega_ratio(returns_array)
                
                # Calculate market-relative metrics (if market data provided)
                if market_array is not None and len(market_array) == len(returns_array):
                    if RiskAdjustmentMethod.TREYNOR in self.config.methods:
                        metrics.treynor_ratio, metrics.beta = self._market_calculator.calculate_treynor_ratio(
                            returns_array, market_array
                        )
                    
                    if RiskAdjustmentMethod.JENSEN_ALPHA in self.config.methods:
                        metrics.jensen_alpha, beta_temp, r_squared = self._market_calculator.calculate_jensen_alpha(
                            returns_array, market_array
                        )
                        if metrics.beta == 0.0:  # If not calculated above
                            metrics.beta = beta_temp
                        metrics.correlation = np.sqrt(r_squared) if r_squared >= 0 else 0.0
                    
                    if RiskAdjustmentMethod.MODIGLIANI in self.config.methods:
                        metrics.modigliani_ratio = self._market_calculator.calculate_modigliani_ratio(
                            returns_array, market_array
                        )
                
                # Calculate Information ratio (if benchmark data provided)
                if benchmark_array is not None and len(benchmark_array) == len(returns_array):
                    if RiskAdjustmentMethod.INFORMATION_RATIO in self.config.methods:
                        metrics.information_ratio, metrics.tracking_error = self._market_calculator.calculate_information_ratio(
                            returns_array, benchmark_array
                        )
                
                # Calculate advanced metrics
                if RiskAdjustmentMethod.RAP in self.config.methods:
                    metrics.rap_ratio = self._advanced_calculator.calculate_rap_ratio(returns_array)
                
                if RiskAdjustmentMethod.RACHEV in self.config.methods:
                    metrics.rachev_ratio = self._advanced_calculator.calculate_rachev_ratio(returns_array)
                
                if RiskAdjustmentMethod.KAPPA in self.config.methods:
                    metrics.kappa_3, metrics.kappa_4 = self._advanced_calculator.calculate_kappa_ratios(returns_array)
                
                # Calculate tail risk metrics
                metrics.tail_ratio = self._advanced_calculator.calculate_tail_ratio(returns_array)
                metrics.pain_ratio = self._advanced_calculator.calculate_pain_ratio(returns_array)
                metrics.sterling_ratio = self._advanced_calculator.calculate_sterling_ratio(returns_array)
                
                # Calculate component metrics
                self._calculate_component_metrics(returns_array, metrics)
                
                # Calculate probabilistic metrics
                if self.config.calculate_probabilistic_metrics:
                    metrics.probabilistic_sharpe = self._advanced_calculator.calculate_probabilistic_sharpe(returns_array)
                
                # Calculate confidence intervals
                if self.config.calculate_confidence_intervals:
                    self._calculate_confidence_intervals(returns_array, metrics)
                
                # Set metadata
                metrics.risk_free_rate = self.config.risk_free_rate
                metrics.calculation_period = f"{len(returns_array)} periods"
                metrics.calculation_time = datetime.now()
                
                # Cache results
                self._metrics_cache[identifier] = metrics
                
                self._calculation_stats['successful_calculations'] += 1
                self._calculation_stats['last_calculation_time'] = datetime.now()
                
                logger.info(f"Calculated risk-adjusted metrics for {identifier}: "
                           f"Sharpe={metrics.sharpe_ratio:.3f}, Sortino={metrics.sortino_ratio:.3f}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted metrics: {e}")
            self._calculation_stats['failed_calculations'] += 1
            return RiskAdjustedMetrics()
    
    def _calculate_component_metrics(self, returns: np.ndarray,
                                   metrics: RiskAdjustedMetrics) -> None:
        """Calculate component metrics used in ratio calculations"""
        
        try:
            # Basic statistics
            period_rf_rate = self.config.risk_free_rate / self.config.business_days_per_year
            excess_returns = returns - period_rf_rate
            
            metrics.excess_return = np.mean(excess_returns)
            metrics.volatility = np.std(returns, ddof=1)
            
            # Downside deviation
            downside_returns = returns[returns < period_rf_rate]
            metrics.downside_deviation = np.std(downside_returns, ddof=1) if len(downside_returns) > 0 else 0.0
            
            # Drawdown
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            metrics.max_drawdown = np.min(drawdowns)
            
            # VaR and CVaR
            confidence_level = self.config.confidence_level
            alpha = 1 - confidence_level
            
            metrics.var_95 = np.percentile(returns, alpha * 100)
            tail_returns = returns[returns <= metrics.var_95]
            metrics.cvar_95 = np.mean(tail_returns) if len(tail_returns) > 0 else metrics.var_95
            
            # Gain/Loss ratio
            gains = returns[returns > 0]
            losses = returns[returns < 0]
            
            avg_gain = np.mean(gains) if len(gains) > 0 else 0.0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0.0
            
            metrics.gain_loss_ratio = avg_gain / abs(avg_loss) if avg_loss != 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating component metrics: {e}")
    
    def _calculate_confidence_intervals(self, returns: np.ndarray,
                                      metrics: RiskAdjustedMetrics) -> None:
        """Calculate confidence intervals for key metrics"""
        
        try:
            # Sharpe ratio confidence interval
            n = len(returns)
            observed_sharpe = metrics.sharpe_ratio
            
            # Standard error calculation
            sharpe_std_error = np.sqrt((1 + (observed_sharpe ** 2) / 2) / n)
            
            # 95% confidence interval
            z_score = stats.norm.ppf(0.975)  # 97.5% for two-tailed
            
            margin_error = z_score * sharpe_std_error
            metrics.sharpe_ci_lower = observed_sharpe - margin_error
            metrics.sharpe_ci_upper = observed_sharpe + margin_error
            
        except Exception as e:
            logger.error(f"Error calculating confidence intervals: {e}")
    
    def get_cached_metrics(self, identifier: str) -> Optional[RiskAdjustedMetrics]:
        """Get cached metrics"""
        
        with self._lock:
            return self._metrics_cache.get(identifier)
    
    def compare_metrics(self, identifier1: str, identifier2: str) -> Dict[str, float]:
        """Compare metrics between two identifiers"""
        
        try:
            with self._lock:
                metrics1 = self._metrics_cache.get(identifier1)
                metrics2 = self._metrics_cache.get(identifier2)
                
                if not metrics1 or not metrics2:
                    logger.warning(f"Missing metrics for comparison: {identifier1}, {identifier2}")
                    return {}
                
                comparison = {
                    'sharpe_diff': metrics1.sharpe_ratio - metrics2.sharpe_ratio,
                    'sortino_diff': metrics1.sortino_ratio - metrics2.sortino_ratio,
                    'calmar_diff': metrics1.calmar_ratio - metrics2.calmar_ratio,
                    'information_ratio_diff': metrics1.information_ratio - metrics2.information_ratio,
                    'volatility_diff': metrics1.volatility - metrics2.volatility,
                    'max_drawdown_diff': metrics1.max_drawdown - metrics2.max_drawdown
                }
                
                return comparison
                
        except Exception as e:
            logger.error(f"Error comparing metrics: {e}")
            return {}
    
    def rank_metrics(self, identifiers: List[str], 
                    metric_name: str = "sharpe_ratio") -> List[Tuple[str, float]]:
        """Rank identifiers by specified metric"""
        
        try:
            with self._lock:
                rankings = []
                
                for identifier in identifiers:
                    metrics = self._metrics_cache.get(identifier)
                    if metrics:
                        metric_value = getattr(metrics, metric_name, 0.0)
                        rankings.append((identifier, metric_value))
                
                # Sort by metric value (descending)
                rankings.sort(key=lambda x: x[1], reverse=True)
                
                return rankings
                
        except Exception as e:
            logger.error(f"Error ranking metrics: {e}")
            return []
    
    def export_metrics(self, identifier: str) -> Dict[str, Any]:
        """Export metrics as dictionary"""
        
        try:
            with self._lock:
                metrics = self._metrics_cache.get(identifier)
                
                if not metrics:
                    return {}
                
                export_data = {
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'sortino_ratio': metrics.sortino_ratio,
                    'calmar_ratio': metrics.calmar_ratio,
                    'omega_ratio': metrics.omega_ratio,
                    'treynor_ratio': metrics.treynor_ratio,
                    'jensen_alpha': metrics.jensen_alpha,
                    'information_ratio': metrics.information_ratio,
                    'modigliani_ratio': metrics.modigliani_ratio,
                    'rap_ratio': metrics.rap_ratio,
                    'rachev_ratio': metrics.rachev_ratio,
                    'kappa_3': metrics.kappa_3,
                    'kappa_4': metrics.kappa_4,
                    'tail_ratio': metrics.tail_ratio,
                    'pain_ratio': metrics.pain_ratio,
                    'sterling_ratio': metrics.sterling_ratio,
                    'probabilistic_sharpe': metrics.probabilistic_sharpe,
                    'excess_return': metrics.excess_return,
                    'volatility': metrics.volatility,
                    'max_drawdown': metrics.max_drawdown,
                    'beta': metrics.beta,
                    'alpha': metrics.alpha,
                    'correlation': metrics.correlation,
                    'tracking_error': metrics.tracking_error,
                    'var_95': metrics.var_95,
                    'cvar_95': metrics.cvar_95,
                    'gain_loss_ratio': metrics.gain_loss_ratio,
                    'sharpe_ci_lower': metrics.sharpe_ci_lower,
                    'sharpe_ci_upper': metrics.sharpe_ci_upper,
                    'calculation_time': metrics.calculation_time,
                    'risk_free_rate': metrics.risk_free_rate
                }
                
                return export_data
                
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return {}
    
    def get_calculator_summary(self) -> Dict[str, Any]:
        """Get calculator summary and statistics"""
        
        with self._lock:
            return {
                'cached_metrics': len(self._metrics_cache),
                'calculation_stats': self._calculation_stats.copy(),
                'config': {
                    'risk_free_rate': self.config.risk_free_rate,
                    'confidence_level': self.config.confidence_level,
                    'min_periods': self.config.min_periods,
                    'methods': [method.value for method in self.config.methods],
                    'calculate_confidence_intervals': self.config.calculate_confidence_intervals,
                    'calculate_probabilistic_metrics': self.config.calculate_probabilistic_metrics
                }
            }
    
    def clear_cache(self, identifier: Optional[str] = None) -> None:
        """Clear cached metrics"""
        
        with self._lock:
            if identifier:
                self._metrics_cache.pop(identifier, None)
                logger.info(f"Cleared cached metrics for {identifier}")
            else:
                self._metrics_cache.clear()
                logger.info("Cleared all cached metrics")