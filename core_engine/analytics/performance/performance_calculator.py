"""
Performance Engine - Performance Calculator
Comprehensive performance measurement and calculation engine
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict, deque
import threading

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class PerformancePeriod(Enum):
    """Performance calculation periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    YTD = "ytd"
    INCEPTION = "inception"


class ReturnType(Enum):
    """Types of returns"""
    SIMPLE = "simple"
    LOG = "log"
    EXCESS = "excess"
    CUMULATIVE = "cumulative"


class PerformanceFrequency(Enum):
    """Performance calculation frequency"""
    REAL_TIME = "real_time"
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    
    # Basic returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    cumulative_return: float = 0.0
    
    # Volatility metrics
    volatility: float = 0.0
    annualized_volatility: float = 0.0
    downside_volatility: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Distribution metrics
    skewness: float = 0.0
    kurtosis: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Win/Loss metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Trading metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Timing
    calculation_time: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Additional metrics
    alpha: float = 0.0
    beta: float = 0.0
    r_squared: float = 0.0
    tracking_error: float = 0.0


@dataclass
class PerformanceConfig:
    """Performance calculation configuration"""
    
    # Calculation settings
    frequency: PerformanceFrequency = PerformanceFrequency.DAILY
    return_type: ReturnType = ReturnType.SIMPLE
    risk_free_rate: float = 0.02  # 2% annual
    
    # Periods to calculate
    periods: List[PerformancePeriod] = field(default_factory=lambda: [
        PerformancePeriod.DAILY, PerformancePeriod.MONTHLY, 
        PerformancePeriod.QUARTERLY, PerformancePeriod.ANNUAL, 
        PerformancePeriod.YTD, PerformancePeriod.INCEPTION
    ])
    
    # Calculation parameters
    min_periods: int = 30  # Minimum periods for annualized calculations
    confidence_level: float = 0.95  # For VaR calculations
    business_days_per_year: int = 252
    
    # Benchmark settings
    benchmark_symbol: Optional[str] = "SPY"
    calculate_alpha_beta: bool = True
    
    # Advanced settings
    enable_real_time: bool = True
    cache_results: bool = True
    precision: int = 6  # Decimal places


class TimeSeriesAnalyzer:
    """Time series analysis for performance calculations"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self._cache: Dict[str, Any] = {}
        
        logger.info("Time series analyzer initialized")
    
    def calculate_returns(self, prices: Union[pd.Series, np.ndarray], 
                         return_type: Optional[ReturnType] = None) -> np.ndarray:
        """Calculate returns from price series"""
        
        try:
            if return_type is None:
                return_type = self.config.return_type
            
            if isinstance(prices, pd.Series):
                prices = prices.values
            
            if len(prices) < 2:
                return np.array([])
            
            if return_type == ReturnType.SIMPLE:
                returns = np.diff(prices) / prices[:-1]
            elif return_type == ReturnType.LOG:
                returns = np.log(prices[1:] / prices[:-1])
            else:
                returns = np.diff(prices) / prices[:-1]  # Default to simple
            
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return np.array([])
    
    def calculate_cumulative_returns(self, returns: np.ndarray, 
                                   return_type: Optional[ReturnType] = None) -> np.ndarray:
        """Calculate cumulative returns"""
        
        try:
            if return_type is None:
                return_type = self.config.return_type
            
            if len(returns) == 0:
                return np.array([])
            
            if return_type == ReturnType.LOG:
                cum_returns = np.cumsum(returns)
            else:
                cum_returns = np.cumprod(1 + returns) - 1
            
            return cum_returns
            
        except Exception as e:
            logger.error(f"Error calculating cumulative returns: {e}")
            return np.array([])
    
    def calculate_rolling_metric(self, data: np.ndarray, window: int, 
                               func: callable) -> np.ndarray:
        """Calculate rolling metric using specified function"""
        
        try:
            if len(data) < window:
                return np.array([])
            
            rolling_values = []
            for i in range(window - 1, len(data)):
                window_data = data[i - window + 1:i + 1]
                value = func(window_data)
                rolling_values.append(value)
            
            return np.array(rolling_values)
            
        except Exception as e:
            logger.error(f"Error calculating rolling metric: {e}")
            return np.array([])
    
    def calculate_drawdown(self, returns: np.ndarray) -> Tuple[np.ndarray, float, int]:
        """Calculate drawdown series, max drawdown, and max duration"""
        
        try:
            if len(returns) == 0:
                return np.array([]), 0.0, 0
            
            cum_returns = self.calculate_cumulative_returns(returns)
            running_max = np.maximum.accumulate(cum_returns)
            drawdown = (cum_returns - running_max) / (1 + running_max)
            
            max_drawdown = np.min(drawdown)
            
            # Calculate max drawdown duration
            max_duration = 0
            current_duration = 0
            
            for dd in drawdown:
                if dd < 0:
                    current_duration += 1
                    max_duration = max(max_duration, current_duration)
                else:
                    current_duration = 0
            
            return drawdown, max_drawdown, max_duration
            
        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return np.array([]), 0.0, 0
    
    def calculate_var(self, returns: np.ndarray, 
                     confidence_level: Optional[float] = None) -> float:
        """Calculate Value at Risk"""
        
        try:
            if confidence_level is None:
                confidence_level = self.config.confidence_level
            
            if len(returns) == 0:
                return 0.0
            
            alpha = 1 - confidence_level
            var = np.percentile(returns, alpha * 100)
            
            return var
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0.0
    
    def calculate_cvar(self, returns: np.ndarray, 
                      confidence_level: Optional[float] = None) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        
        try:
            if confidence_level is None:
                confidence_level = self.config.confidence_level
            
            if len(returns) == 0:
                return 0.0
            
            var = self.calculate_var(returns, confidence_level)
            cvar = np.mean(returns[returns <= var])
            
            return cvar if not np.isnan(cvar) else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating CVaR: {e}")
            return 0.0


class PerformanceCalculator:
    """
    Comprehensive Performance Calculator
    
    Calculates performance metrics, risk-adjusted returns,
    and statistical measures for trading strategies and portfolios.
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        """Initialize performance calculator"""
        
        self.config = config or PerformanceConfig()
        self.analyzer = TimeSeriesAnalyzer(self.config)
        
        # Performance data storage
        self._returns_cache: Dict[str, np.ndarray] = {}
        self._metrics_cache: Dict[str, PerformanceMetrics] = {}
        self._benchmark_returns: Optional[np.ndarray] = None
        
        # Real-time calculation
        self._real_time_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._last_calculations: Dict[str, datetime] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Performance calculator initialized")
    
    def calculate_performance(self, returns: Union[pd.Series, np.ndarray, List[float]], 
                            identifier: str = "default",
                            benchmark_returns: Optional[Union[pd.Series, np.ndarray]] = None,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        try:
            with self._lock:
                # Convert to numpy array
                if isinstance(returns, (pd.Series, list)):
                    returns_array = np.array(returns)
                else:
                    returns_array = returns
                
                # Validate data
                if len(returns_array) == 0:
                    logger.warning("Empty returns array provided")
                    return PerformanceMetrics()
                
                # Remove NaN values
                returns_array = returns_array[~np.isnan(returns_array)]
                
                if len(returns_array) == 0:
                    logger.warning("No valid returns after removing NaN values")
                    return PerformanceMetrics()
                
                # Store in cache
                self._returns_cache[identifier] = returns_array
                
                # Calculate metrics
                metrics = self._calculate_comprehensive_metrics(
                    returns_array, benchmark_returns, start_date, end_date
                )
                
                # Cache results
                if self.config.cache_results:
                    self._metrics_cache[identifier] = metrics
                
                # Update last calculation time
                self._last_calculations[identifier] = datetime.now()
                
                logger.debug(f"Calculated performance metrics for {identifier}")
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return PerformanceMetrics()
    
    def _calculate_comprehensive_metrics(self, returns: np.ndarray,
                                       benchmark_returns: Optional[np.ndarray] = None,
                                       start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        metrics = PerformanceMetrics()
        
        try:
            # Basic return metrics
            metrics.total_return = self._calculate_total_return(returns)
            metrics.cumulative_return = self._calculate_cumulative_return(returns)
            metrics.annualized_return = self._calculate_annualized_return(returns)
            
            # Volatility metrics
            metrics.volatility = self._calculate_volatility(returns)
            metrics.annualized_volatility = self._calculate_annualized_volatility(returns)
            metrics.downside_volatility = self._calculate_downside_volatility(returns)
            
            # Risk-adjusted metrics
            metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns)
            metrics.sortino_ratio = self._calculate_sortino_ratio(returns)
            metrics.calmar_ratio = self._calculate_calmar_ratio(returns)
            
            # Drawdown metrics
            drawdown_series, max_dd, max_duration = self.analyzer.calculate_drawdown(returns)
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_duration = max_duration
            metrics.current_drawdown = drawdown_series[-1] if len(drawdown_series) > 0 else 0.0
            
            # Distribution metrics
            metrics.skewness = self._calculate_skewness(returns)
            metrics.kurtosis = self._calculate_kurtosis(returns)
            metrics.var_95 = self.analyzer.calculate_var(returns)
            metrics.cvar_95 = self.analyzer.calculate_cvar(returns)
            
            # Win/Loss metrics
            metrics.win_rate = self._calculate_win_rate(returns)
            metrics.profit_factor = self._calculate_profit_factor(returns)
            metrics.avg_win = self._calculate_avg_win(returns)
            metrics.avg_loss = self._calculate_avg_loss(returns)
            
            # Trading metrics
            metrics.total_trades = len(returns)
            metrics.winning_trades = len(returns[returns > 0])
            metrics.losing_trades = len(returns[returns < 0])
            
            # Benchmark-relative metrics
            if benchmark_returns is not None and self.config.calculate_alpha_beta:
                alpha, beta, r_squared = self._calculate_alpha_beta(returns, benchmark_returns)
                metrics.alpha = alpha
                metrics.beta = beta
                metrics.r_squared = r_squared
                metrics.tracking_error = self._calculate_tracking_error(returns, benchmark_returns)
                metrics.information_ratio = self._calculate_information_ratio(returns, benchmark_returns)
            
            # Timing information
            metrics.period_start = start_date
            metrics.period_end = end_date
            metrics.calculation_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in comprehensive metrics calculation: {e}")
        
        return metrics
    
    def _calculate_total_return(self, returns: np.ndarray) -> float:
        """Calculate total return"""
        try:
            if len(returns) == 0:
                return 0.0
            
            if self.config.return_type == ReturnType.LOG:
                total_return = np.exp(np.sum(returns)) - 1
            else:
                total_return = np.prod(1 + returns) - 1
            
            return round(total_return, self.config.precision)
        except:
            return 0.0
    
    def _calculate_cumulative_return(self, returns: np.ndarray) -> float:
        """Calculate cumulative return (same as total return for final value)"""
        return self._calculate_total_return(returns)
    
    def _calculate_annualized_return(self, returns: np.ndarray) -> float:
        """Calculate annualized return"""
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            total_return = self._calculate_total_return(returns)
            
            # Determine periods per year based on frequency
            if self.config.frequency == PerformanceFrequency.DAILY:
                periods_per_year = self.config.business_days_per_year
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                periods_per_year = 52
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                periods_per_year = 12
            else:
                periods_per_year = self.config.business_days_per_year
            
            years = len(returns) / periods_per_year
            annualized_return = (1 + total_return) ** (1 / years) - 1
            
            return round(annualized_return, self.config.precision)
        except:
            return 0.0
    
    def _calculate_volatility(self, returns: np.ndarray) -> float:
        """Calculate volatility (standard deviation)"""
        try:
            if len(returns) < 2:
                return 0.0
            
            volatility = np.std(returns, ddof=1)
            return round(volatility, self.config.precision)
        except:
            return 0.0
    
    def _calculate_annualized_volatility(self, returns: np.ndarray) -> float:
        """Calculate annualized volatility"""
        try:
            volatility = self._calculate_volatility(returns)
            
            if self.config.frequency == PerformanceFrequency.DAILY:
                annualization_factor = np.sqrt(self.config.business_days_per_year)
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                annualization_factor = np.sqrt(52)
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                annualization_factor = np.sqrt(12)
            else:
                annualization_factor = np.sqrt(self.config.business_days_per_year)
            
            annualized_vol = volatility * annualization_factor
            return round(annualized_vol, self.config.precision)
        except:
            return 0.0
    
    def _calculate_downside_volatility(self, returns: np.ndarray) -> float:
        """Calculate downside volatility (semi-deviation)"""
        try:
            if len(returns) < 2:
                return 0.0
            
            downside_returns = returns[returns < 0]
            if len(downside_returns) == 0:
                return 0.0
            
            downside_vol = np.std(downside_returns, ddof=1)
            return round(downside_vol, self.config.precision)
        except:
            return 0.0
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            excess_returns = returns - (self.config.risk_free_rate / self.config.business_days_per_year)
            mean_excess = np.mean(excess_returns)
            vol = np.std(returns, ddof=1)
            
            if vol == 0:
                return 0.0
            
            # Annualize
            if self.config.frequency == PerformanceFrequency.DAILY:
                sharpe = (mean_excess / vol) * np.sqrt(self.config.business_days_per_year)
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                sharpe = (mean_excess / vol) * np.sqrt(52)
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                sharpe = (mean_excess / vol) * np.sqrt(12)
            else:
                sharpe = mean_excess / vol
            
            return round(sharpe, self.config.precision)
        except:
            return 0.0
    
    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float:
        """Calculate Sortino ratio"""
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            excess_returns = returns - (self.config.risk_free_rate / self.config.business_days_per_year)
            mean_excess = np.mean(excess_returns)
            downside_vol = self._calculate_downside_volatility(returns)
            
            if downside_vol == 0:
                return 0.0
            
            # Annualize
            if self.config.frequency == PerformanceFrequency.DAILY:
                sortino = (mean_excess / downside_vol) * np.sqrt(self.config.business_days_per_year)
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                sortino = (mean_excess / downside_vol) * np.sqrt(52)
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                sortino = (mean_excess / downside_vol) * np.sqrt(12)
            else:
                sortino = mean_excess / downside_vol
            
            return round(sortino, self.config.precision)
        except:
            return 0.0
    
    def _calculate_calmar_ratio(self, returns: np.ndarray) -> float:
        """Calculate Calmar ratio"""
        try:
            if len(returns) < self.config.min_periods:
                return 0.0
            
            annualized_return = self._calculate_annualized_return(returns)
            _, max_drawdown, _ = self.analyzer.calculate_drawdown(returns)
            
            if max_drawdown == 0:
                return 0.0
            
            calmar = annualized_return / abs(max_drawdown)
            return round(calmar, self.config.precision)
        except:
            return 0.0
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness"""
        try:
            if len(returns) < 3:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            if std_return == 0:
                return 0.0
            
            skewness = np.mean(((returns - mean_return) / std_return) ** 3)
            return round(skewness, self.config.precision)
        except:
            return 0.0
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate excess kurtosis"""
        try:
            if len(returns) < 4:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            
            if std_return == 0:
                return 0.0
            
            kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
            return round(kurtosis, self.config.precision)
        except:
            return 0.0
    
    def _calculate_win_rate(self, returns: np.ndarray) -> float:
        """Calculate win rate"""
        try:
            if len(returns) == 0:
                return 0.0
            
            winning_periods = len(returns[returns > 0])
            win_rate = winning_periods / len(returns)
            
            return round(win_rate, self.config.precision)
        except:
            return 0.0
    
    def _calculate_profit_factor(self, returns: np.ndarray) -> float:
        """Calculate profit factor"""
        try:
            positive_returns = returns[returns > 0]
            negative_returns = returns[returns < 0]
            
            if len(negative_returns) == 0:
                return float('inf') if len(positive_returns) > 0 else 0.0
            
            gross_profit = np.sum(positive_returns)
            gross_loss = abs(np.sum(negative_returns))
            
            if gross_loss == 0:
                return float('inf') if gross_profit > 0 else 0.0
            
            profit_factor = gross_profit / gross_loss
            return round(profit_factor, self.config.precision)
        except:
            return 0.0
    
    def _calculate_avg_win(self, returns: np.ndarray) -> float:
        """Calculate average winning return"""
        try:
            winning_returns = returns[returns > 0]
            if len(winning_returns) == 0:
                return 0.0
            
            avg_win = np.mean(winning_returns)
            return round(avg_win, self.config.precision)
        except:
            return 0.0
    
    def _calculate_avg_loss(self, returns: np.ndarray) -> float:
        """Calculate average losing return"""
        try:
            losing_returns = returns[returns < 0]
            if len(losing_returns) == 0:
                return 0.0
            
            avg_loss = np.mean(losing_returns)
            return round(avg_loss, self.config.precision)
        except:
            return 0.0
    
    def _calculate_alpha_beta(self, returns: np.ndarray, 
                            benchmark_returns: np.ndarray) -> Tuple[float, float, float]:
        """Calculate alpha, beta, and R-squared"""
        try:
            if len(returns) != len(benchmark_returns) or len(returns) < self.config.min_periods:
                return 0.0, 0.0, 0.0
            
            # Remove NaN values
            valid_mask = ~(np.isnan(returns) | np.isnan(benchmark_returns))
            clean_returns = returns[valid_mask]
            clean_benchmark = benchmark_returns[valid_mask]
            
            if len(clean_returns) < self.config.min_periods:
                return 0.0, 0.0, 0.0
            
            # Calculate beta
            covariance = np.cov(clean_returns, clean_benchmark)[0, 1]
            benchmark_variance = np.var(clean_benchmark, ddof=1)
            
            if benchmark_variance == 0:
                return 0.0, 0.0, 0.0
            
            beta = covariance / benchmark_variance
            
            # Calculate alpha
            portfolio_mean = np.mean(clean_returns)
            benchmark_mean = np.mean(clean_benchmark)
            risk_free_daily = self.config.risk_free_rate / self.config.business_days_per_year
            
            alpha = portfolio_mean - risk_free_daily - beta * (benchmark_mean - risk_free_daily)
            
            # Annualize alpha
            if self.config.frequency == PerformanceFrequency.DAILY:
                alpha_annualized = alpha * self.config.business_days_per_year
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                alpha_annualized = alpha * 52
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                alpha_annualized = alpha * 12
            else:
                alpha_annualized = alpha
            
            # Calculate R-squared
            correlation = np.corrcoef(clean_returns, clean_benchmark)[0, 1]
            r_squared = correlation ** 2 if not np.isnan(correlation) else 0.0
            
            return (round(alpha_annualized, self.config.precision), 
                   round(beta, self.config.precision),
                   round(r_squared, self.config.precision))
        except:
            return 0.0, 0.0, 0.0
    
    def _calculate_tracking_error(self, returns: np.ndarray, 
                                benchmark_returns: np.ndarray) -> float:
        """Calculate tracking error"""
        try:
            if len(returns) != len(benchmark_returns):
                return 0.0
            
            # Remove NaN values
            valid_mask = ~(np.isnan(returns) | np.isnan(benchmark_returns))
            clean_returns = returns[valid_mask]
            clean_benchmark = benchmark_returns[valid_mask]
            
            if len(clean_returns) < 2:
                return 0.0
            
            excess_returns = clean_returns - clean_benchmark
            tracking_error = np.std(excess_returns, ddof=1)
            
            # Annualize
            if self.config.frequency == PerformanceFrequency.DAILY:
                tracking_error *= np.sqrt(self.config.business_days_per_year)
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                tracking_error *= np.sqrt(52)
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                tracking_error *= np.sqrt(12)
            
            return round(tracking_error, self.config.precision)
        except:
            return 0.0
    
    def _calculate_information_ratio(self, returns: np.ndarray, 
                                   benchmark_returns: np.ndarray) -> float:
        """Calculate information ratio"""
        try:
            if len(returns) != len(benchmark_returns):
                return 0.0
            
            # Remove NaN values
            valid_mask = ~(np.isnan(returns) | np.isnan(benchmark_returns))
            clean_returns = returns[valid_mask]
            clean_benchmark = benchmark_returns[valid_mask]
            
            if len(clean_returns) < 2:
                return 0.0
            
            excess_returns = clean_returns - clean_benchmark
            mean_excess = np.mean(excess_returns)
            tracking_error = np.std(excess_returns, ddof=1)
            
            if tracking_error == 0:
                return 0.0
            
            information_ratio = mean_excess / tracking_error
            
            # Annualize
            if self.config.frequency == PerformanceFrequency.DAILY:
                information_ratio *= np.sqrt(self.config.business_days_per_year)
            elif self.config.frequency == PerformanceFrequency.WEEKLY:
                information_ratio *= np.sqrt(52)
            elif self.config.frequency == PerformanceFrequency.MONTHLY:
                information_ratio *= np.sqrt(12)
            
            return round(information_ratio, self.config.precision)
        except:
            return 0.0
    
    def calculate_rolling_metrics(self, returns: Union[pd.Series, np.ndarray], 
                                window: int, identifier: str = "rolling") -> pd.DataFrame:
        """Calculate rolling performance metrics"""
        
        try:
            if isinstance(returns, pd.Series):
                returns_array = returns.values
                index = returns.index
            else:
                returns_array = returns
                index = pd.date_range(start='2020-01-01', periods=len(returns_array))
            
            if len(returns_array) < window:
                logger.warning(f"Insufficient data for rolling calculation (need {window}, got {len(returns_array)})")
                return pd.DataFrame()
            
            # Calculate rolling metrics
            rolling_data = []
            
            for i in range(window - 1, len(returns_array)):
                window_returns = returns_array[i - window + 1:i + 1]
                
                metrics = self._calculate_comprehensive_metrics(window_returns)
                
                rolling_data.append({
                    'date': index[i] if i < len(index) else index[-1],
                    'total_return': metrics.total_return,
                    'annualized_return': metrics.annualized_return,
                    'volatility': metrics.volatility,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'win_rate': metrics.win_rate
                })
            
            df = pd.DataFrame(rolling_data)
            df.set_index('date', inplace=True)
            
            logger.info(f"Calculated rolling metrics with window {window} for {identifier}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating rolling metrics: {e}")
            return pd.DataFrame()
    
    def update_real_time_metrics(self, new_return: float, 
                               identifier: str = "real_time") -> PerformanceMetrics:
        """Update real-time performance metrics"""
        
        try:
            with self._lock:
                # Add new return to real-time data
                self._real_time_data[identifier].append(new_return)
                
                # Calculate metrics on recent data
                recent_returns = np.array(list(self._real_time_data[identifier]))
                
                metrics = self._calculate_comprehensive_metrics(recent_returns)
                
                # Cache for future reference
                self._metrics_cache[f"{identifier}_real_time"] = metrics
                
                return metrics
                
        except Exception as e:
            logger.error(f"Error updating real-time metrics: {e}")
            return PerformanceMetrics()
    
    def get_cached_metrics(self, identifier: str) -> Optional[PerformanceMetrics]:
        """Get cached performance metrics"""
        
        with self._lock:
            return self._metrics_cache.get(identifier)
    
    def clear_cache(self, identifier: Optional[str] = None) -> None:
        """Clear cached data"""
        
        with self._lock:
            if identifier:
                self._metrics_cache.pop(identifier, None)
                self._returns_cache.pop(identifier, None)
                self._real_time_data.pop(identifier, None)
            else:
                self._metrics_cache.clear()
                self._returns_cache.clear()
                self._real_time_data.clear()
    
    def set_benchmark(self, benchmark_returns: Union[pd.Series, np.ndarray]) -> None:
        """Set benchmark returns for relative performance calculation"""
        
        with self._lock:
            if isinstance(benchmark_returns, pd.Series):
                self._benchmark_returns = benchmark_returns.values
            else:
                self._benchmark_returns = benchmark_returns
            
            logger.info("Benchmark returns updated")
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """Get summary of calculation statistics"""
        
        with self._lock:
            return {
                'cached_metrics': len(self._metrics_cache),
                'cached_returns': len(self._returns_cache),
                'real_time_series': len(self._real_time_data),
                'last_calculations': dict(self._last_calculations),
                'config': {
                    'frequency': self.config.frequency.value,
                    'return_type': self.config.return_type.value,
                    'risk_free_rate': self.config.risk_free_rate,
                    'min_periods': self.config.min_periods,
                    'confidence_level': self.config.confidence_level
                }
            }