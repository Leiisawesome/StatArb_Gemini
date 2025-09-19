"""
Analytics Engine - Performance Analyzer
Advanced performance analysis with comprehensive metrics and attribution
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import json
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Performance metrics"""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    INFORMATION_RATIO = "information_ratio"
    MAXIMUM_DRAWDOWN = "maximum_drawdown"
    CALMAR_RATIO = "calmar_ratio"
    OMEGA_RATIO = "omega_ratio"
    VAR = "value_at_risk"
    CVAR = "conditional_var"
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"
    BETA = "beta"
    ALPHA = "alpha"
    TRACKING_ERROR = "tracking_error"
    TREYNOR_RATIO = "treynor_ratio"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"


class PerformancePeriod(Enum):
    """Performance calculation periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"
    CUSTOM = "custom"


class RiskFreeRateSource(Enum):
    """Risk-free rate sources"""
    TREASURY_3M = "treasury_3m"
    TREASURY_10Y = "treasury_10y"
    LIBOR = "libor"
    SOFR = "sofr"
    CUSTOM = "custom"


@dataclass
class PerformanceConfig:
    """Performance analysis configuration"""
    # Risk-free rate
    risk_free_rate_source: RiskFreeRateSource = RiskFreeRateSource.TREASURY_3M
    custom_risk_free_rate: float = 0.02  # 2% annual
    
    # Calculation parameters
    trading_days_per_year: int = 252
    confidence_level: float = 0.95  # For VaR calculations
    var_lookback_days: int = 252
    
    # Benchmark settings
    default_benchmark: str = "SPY"
    enable_benchmark_comparison: bool = True
    
    # Attribution settings
    enable_factor_attribution: bool = True
    attribution_frequency: str = "daily"
    
    # Risk metrics
    enable_downside_metrics: bool = True
    drawdown_threshold: float = 0.05  # 5%
    
    # Performance periods
    analysis_periods: List[PerformancePeriod] = field(default_factory=lambda: [
        PerformancePeriod.DAILY,
        PerformancePeriod.MONTHLY,
        PerformancePeriod.YEARLY,
        PerformancePeriod.INCEPTION
    ])


@dataclass
class PerformanceMetrics:
    """Performance metrics container"""
    symbol: str
    start_date: datetime
    end_date: datetime
    period: PerformancePeriod
    
    # Basic returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    downside_volatility: float = 0.0
    maximum_drawdown: float = 0.0
    maximum_drawdown_duration: int = 0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Risk measures
    var_95: float = 0.0
    cvar_95: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    
    # Benchmark-relative metrics
    beta: float = 0.0
    alpha: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    treynor_ratio: float = 0.0
    
    # Trading metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Additional statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Metadata
    calculation_timestamp: datetime = field(default_factory=datetime.now)
    benchmark_symbol: Optional[str] = None
    risk_free_rate: float = 0.0


@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    portfolio_name: str
    report_id: str
    generation_timestamp: datetime
    
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Overall metrics
    portfolio_metrics: PerformanceMetrics
    
    # Period breakdown
    period_metrics: Dict[PerformancePeriod, PerformanceMetrics] = field(default_factory=dict)
    
    # Position-level metrics
    position_metrics: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Rolling metrics
    rolling_sharpe: pd.Series = field(default_factory=pd.Series)
    rolling_volatility: pd.Series = field(default_factory=pd.Series)
    rolling_drawdown: pd.Series = field(default_factory=pd.Series)
    
    # Performance attribution
    factor_attribution: Dict[str, float] = field(default_factory=dict)
    sector_attribution: Dict[str, float] = field(default_factory=dict)
    
    # Risk decomposition
    risk_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Charts and visualizations data
    equity_curve: pd.Series = field(default_factory=pd.Series)
    drawdown_series: pd.Series = field(default_factory=pd.Series)
    monthly_returns: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Summary statistics
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Warnings and notes
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class RiskMetricsCalculator:
    """Advanced risk metrics calculator"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
    
    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical"
    ) -> float:
        """Calculate Value at Risk"""
        
        if returns.empty:
            return 0.0
        
        if method == "historical":
            return np.percentile(returns.dropna(), (1 - confidence_level) * 100)
        elif method == "parametric":
            return stats.norm.ppf(1 - confidence_level, returns.mean(), returns.std())
        else:
            return np.percentile(returns.dropna(), (1 - confidence_level) * 100)
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95
    ) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        
        if returns.empty:
            return 0.0
        
        var = self.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    
    def calculate_maximum_drawdown(self, returns: pd.Series) -> Tuple[float, int]:
        """Calculate maximum drawdown and duration"""
        
        if returns.empty:
            return 0.0, 0
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max
        
        # Maximum drawdown
        max_dd = drawdown.min()
        
        # Calculate duration of maximum drawdown
        max_dd_start = drawdown.idxmin()
        max_dd_series = drawdown.loc[:max_dd_start]
        
        # Find when drawdown started
        dd_start_idx = None
        for i in range(len(max_dd_series) - 1, -1, -1):
            if max_dd_series.iloc[i] == 0:
                dd_start_idx = i
                break
        
        if dd_start_idx is not None:
            duration = max_dd_start - max_dd_series.index[dd_start_idx]
            if hasattr(duration, 'days'):
                duration = duration.days
            else:
                duration = int(duration)
        else:
            duration = len(max_dd_series)
        
        return abs(max_dd), duration
    
    def calculate_downside_volatility(
        self,
        returns: pd.Series,
        minimum_acceptable_return: float = 0.0
    ) -> float:
        """Calculate downside volatility (semi-standard deviation)"""
        
        if returns.empty:
            return 0.0
        
        downside_returns = returns[returns < minimum_acceptable_return]
        
        if len(downside_returns) == 0:
            return 0.0
        
        return downside_returns.std() * np.sqrt(self.config.trading_days_per_year)
    
    def calculate_omega_ratio(
        self,
        returns: pd.Series,
        threshold: float = 0.0
    ) -> float:
        """Calculate Omega ratio"""
        
        if returns.empty:
            return 0.0
        
        excess_returns = returns - threshold
        positive_returns = excess_returns[excess_returns > 0].sum()
        negative_returns = -excess_returns[excess_returns < 0].sum()
        
        if negative_returns == 0:
            return np.inf if positive_returns > 0 else 1.0
        
        return positive_returns / negative_returns


class BenchmarkAnalyzer:
    """Benchmark comparison and beta calculation"""
    
    def __init__(self, config: PerformanceConfig):
        self.config = config
        self.benchmark_cache = {}
    
    def calculate_beta(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> Tuple[float, float]:
        """Calculate beta and alpha relative to benchmark"""
        
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0, 0.0
        
        # Align series
        aligned_data = pd.DataFrame({
            'portfolio': portfolio_returns,
            'benchmark': benchmark_returns
        }).dropna()
        
        if len(aligned_data) < 2:
            return 0.0, 0.0
        
        # Calculate beta using linear regression
        X = aligned_data['benchmark'].values.reshape(-1, 1)
        y = aligned_data['portfolio'].values
        
        reg = LinearRegression().fit(X, y)
        beta = reg.coef_[0]
        alpha = reg.intercept_
        
        # Annualize alpha
        alpha_annualized = alpha * self.config.trading_days_per_year
        
        return beta, alpha_annualized
    
    def calculate_tracking_error(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """Calculate tracking error"""
        
        if len(portfolio_returns) != len(benchmark_returns):
            return 0.0
        
        excess_returns = portfolio_returns - benchmark_returns
        return excess_returns.std() * np.sqrt(self.config.trading_days_per_year)
    
    def calculate_information_ratio(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """Calculate information ratio"""
        
        if len(portfolio_returns) != len(benchmark_returns):
            return 0.0
        
        excess_returns = portfolio_returns - benchmark_returns
        tracking_error = self.calculate_tracking_error(portfolio_returns, benchmark_returns)
        
        if tracking_error == 0:
            return 0.0
        
        excess_return_mean = excess_returns.mean() * self.config.trading_days_per_year
        return excess_return_mean / tracking_error


class TradingMetricsCalculator:
    """Trading-specific performance metrics"""
    
    def calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate (percentage of positive returns)"""
        
        if returns.empty:
            return 0.0
        
        winning_periods = len(returns[returns > 0])
        total_periods = len(returns.dropna())
        
        return winning_periods / total_periods if total_periods > 0 else 0.0
    
    def calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        
        if returns.empty:
            return 0.0
        
        positive_returns = returns[returns > 0].sum()
        negative_returns = abs(returns[returns < 0].sum())
        
        if negative_returns == 0:
            return np.inf if positive_returns > 0 else 0.0
        
        return positive_returns / negative_returns
    
    def calculate_trading_statistics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive trading statistics"""
        
        if returns.empty:
            return {}
        
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        stats = {
            'total_trades': len(returns.dropna()),
            'winning_trades': len(positive_returns),
            'losing_trades': len(negative_returns),
            'win_rate': self.calculate_win_rate(returns),
            'profit_factor': self.calculate_profit_factor(returns),
            'average_win': positive_returns.mean() if len(positive_returns) > 0 else 0.0,
            'average_loss': negative_returns.mean() if len(negative_returns) > 0 else 0.0,
            'largest_win': positive_returns.max() if len(positive_returns) > 0 else 0.0,
            'largest_loss': negative_returns.min() if len(negative_returns) > 0 else 0.0,
        }
        
        return stats


class PerformanceAnalyzer:
    """
    Advanced Performance Analyzer
    
    Comprehensive performance analysis with risk-adjusted metrics,
    benchmark comparison, and detailed attribution analysis.
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        """Initialize performance analyzer"""
        self.config = config or PerformanceConfig()
        
        # Component calculators
        self.risk_calculator = RiskMetricsCalculator(self.config)
        self.benchmark_analyzer = BenchmarkAnalyzer(self.config)
        self.trading_calculator = TradingMetricsCalculator()
        
        # Data storage
        self._performance_cache = {}
        self._benchmark_data = {}
        self._risk_free_rates = {}
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info("Performance Analyzer initialized")
    
    async def analyze_performance(
        self,
        returns: pd.Series,
        symbol: str,
        benchmark_returns: Optional[pd.Series] = None,
        period: PerformancePeriod = PerformancePeriod.INCEPTION,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """Analyze performance for a given return series"""
        
        if returns.empty:
            logger.warning(f"Empty returns series for {symbol}")
            return PerformanceMetrics(
                symbol=symbol,
                start_date=start_date or datetime.now(),
                end_date=end_date or datetime.now(),
                period=period
            )
        
        # Filter returns by date range if specified
        if start_date or end_date:
            if start_date:
                returns = returns[returns.index >= start_date]
            if end_date:
                returns = returns[returns.index <= end_date]
        
        # Determine actual date range
        actual_start = returns.index.min() if not returns.empty else (start_date or datetime.now())
        actual_end = returns.index.max() if not returns.empty else (end_date or datetime.now())
        
        # Initialize metrics
        metrics = PerformanceMetrics(
            symbol=symbol,
            start_date=actual_start,
            end_date=actual_end,
            period=period,
            risk_free_rate=self._get_risk_free_rate()
        )
        
        try:
            # Basic return metrics
            metrics.total_return = (1 + returns).prod() - 1
            
            # Annualized return
            if len(returns) > 0:
                periods_per_year = self._get_periods_per_year(returns)
                metrics.annualized_return = (1 + metrics.total_return) ** (periods_per_year / len(returns)) - 1
            
            # Volatility metrics
            metrics.volatility = returns.std() * np.sqrt(self._get_periods_per_year(returns))
            metrics.downside_volatility = self.risk_calculator.calculate_downside_volatility(returns)
            
            # Risk metrics
            metrics.maximum_drawdown, metrics.maximum_drawdown_duration = \
                self.risk_calculator.calculate_maximum_drawdown(returns)
            
            # VaR metrics
            metrics.var_95 = self.risk_calculator.calculate_var(returns, self.config.confidence_level)
            metrics.cvar_95 = self.risk_calculator.calculate_cvar(returns, self.config.confidence_level)
            
            # Distribution metrics
            metrics.skewness = returns.skew()
            metrics.kurtosis = returns.kurtosis()
            
            # Risk-adjusted return metrics
            excess_returns = returns - metrics.risk_free_rate / self._get_periods_per_year(returns)
            
            if metrics.volatility > 0:
                metrics.sharpe_ratio = excess_returns.mean() * np.sqrt(self._get_periods_per_year(returns)) / metrics.volatility
            
            if metrics.downside_volatility > 0:
                metrics.sortino_ratio = excess_returns.mean() * np.sqrt(self._get_periods_per_year(returns)) / metrics.downside_volatility
            
            if metrics.maximum_drawdown > 0:
                metrics.calmar_ratio = metrics.annualized_return / metrics.maximum_drawdown
            
            metrics.omega_ratio = self.risk_calculator.calculate_omega_ratio(returns)
            
            # Trading metrics
            trading_stats = self.trading_calculator.calculate_trading_statistics(returns)
            metrics.win_rate = trading_stats.get('win_rate', 0.0)
            metrics.profit_factor = trading_stats.get('profit_factor', 0.0)
            metrics.average_win = trading_stats.get('average_win', 0.0)
            metrics.average_loss = trading_stats.get('average_loss', 0.0)
            metrics.largest_win = trading_stats.get('largest_win', 0.0)
            metrics.largest_loss = trading_stats.get('largest_loss', 0.0)
            metrics.total_trades = int(trading_stats.get('total_trades', 0))
            metrics.winning_trades = int(trading_stats.get('winning_trades', 0))
            metrics.losing_trades = int(trading_stats.get('losing_trades', 0))
            
            # Benchmark-relative metrics
            if benchmark_returns is not None and not benchmark_returns.empty:
                metrics.benchmark_symbol = getattr(benchmark_returns, 'name', 'Benchmark')
                
                # Align returns with benchmark
                aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
                
                if len(aligned_returns) > 1:
                    metrics.beta, metrics.alpha = self.benchmark_analyzer.calculate_beta(
                        aligned_returns, aligned_benchmark
                    )
                    
                    metrics.tracking_error = self.benchmark_analyzer.calculate_tracking_error(
                        aligned_returns, aligned_benchmark
                    )
                    
                    metrics.information_ratio = self.benchmark_analyzer.calculate_information_ratio(
                        aligned_returns, aligned_benchmark
                    )
                    
                    if metrics.beta != 0:
                        metrics.treynor_ratio = (metrics.annualized_return - metrics.risk_free_rate) / metrics.beta
            
            logger.debug(f"Performance analysis completed for {symbol}: "
                        f"Return: {metrics.annualized_return:.2%}, "
                        f"Sharpe: {metrics.sharpe_ratio:.2f}, "
                        f"MaxDD: {metrics.maximum_drawdown:.2%}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing performance for {symbol}: {e}")
            return metrics
    
    def _get_periods_per_year(self, returns: pd.Series) -> float:
        """Determine periods per year based on data frequency"""
        
        if len(returns) < 2:
            return self.config.trading_days_per_year
        
        # Calculate average time difference
        time_diffs = returns.index.to_series().diff().dropna()
        avg_diff = time_diffs.mean()
        
        if avg_diff <= pd.Timedelta(days=1):
            return self.config.trading_days_per_year  # Daily
        elif avg_diff <= pd.Timedelta(weeks=1):
            return 52  # Weekly
        elif avg_diff <= pd.Timedelta(days=32):
            return 12  # Monthly
        else:
            return 4  # Quarterly or less frequent
    
    def _get_risk_free_rate(self) -> float:
        """Get current risk-free rate"""
        
        if self.config.risk_free_rate_source == RiskFreeRateSource.CUSTOM:
            return self.config.custom_risk_free_rate
        
        # In a real implementation, this would fetch from a data source
        # For now, return the custom rate
        return self.config.custom_risk_free_rate
    
    async def generate_performance_report(
        self,
        portfolio_returns: pd.Series,
        portfolio_name: str,
        position_returns: Optional[Dict[str, pd.Series]] = None,
        benchmark_returns: Optional[pd.Series] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceReport:
        """Generate comprehensive performance report"""
        
        report_id = f"{portfolio_name}_{int(time.time())}"
        
        # Determine date range
        if not start_date:
            start_date = portfolio_returns.index.min() if not portfolio_returns.empty else datetime.now()
        if not end_date:
            end_date = portfolio_returns.index.max() if not portfolio_returns.empty else datetime.now()
        
        # Initialize report
        report = PerformanceReport(
            portfolio_name=portfolio_name,
            report_id=report_id,
            generation_timestamp=datetime.now(),
            start_date=start_date,
            end_date=end_date
        )
        
        try:
            # Overall portfolio metrics
            report.portfolio_metrics = await self.analyze_performance(
                portfolio_returns,
                portfolio_name,
                benchmark_returns,
                PerformancePeriod.INCEPTION,
                start_date,
                end_date
            )
            
            # Period breakdown
            for period in self.config.analysis_periods:
                if period == PerformancePeriod.INCEPTION:
                    continue  # Already calculated above
                
                period_returns = self._get_period_returns(portfolio_returns, period)
                if not period_returns.empty:
                    period_metrics = await self.analyze_performance(
                        period_returns,
                        f"{portfolio_name}_{period.value}",
                        benchmark_returns,
                        period
                    )
                    report.period_metrics[period] = period_metrics
            
            # Position-level analysis
            if position_returns:
                for symbol, returns in position_returns.items():
                    if not returns.empty:
                        position_metrics = await self.analyze_performance(
                            returns,
                            symbol,
                            benchmark_returns,
                            PerformancePeriod.INCEPTION,
                            start_date,
                            end_date
                        )
                        report.position_metrics[symbol] = position_metrics
            
            # Rolling metrics
            report.rolling_sharpe = self._calculate_rolling_sharpe(portfolio_returns)
            report.rolling_volatility = self._calculate_rolling_volatility(portfolio_returns)
            report.rolling_drawdown = self._calculate_rolling_drawdown(portfolio_returns)
            
            # Equity curve
            report.equity_curve = (1 + portfolio_returns).cumprod()
            
            # Drawdown series
            report.drawdown_series = self._calculate_drawdown_series(portfolio_returns)
            
            # Monthly returns table
            report.monthly_returns = self._create_monthly_returns_table(portfolio_returns)
            
            # Summary statistics
            report.summary_stats = self._create_summary_statistics(report)
            
            # Add notes and warnings
            report.notes = self._generate_report_notes(report)
            report.warnings = self._generate_report_warnings(report)
            
            logger.info(f"Performance report generated for {portfolio_name}: "
                       f"Return: {report.portfolio_metrics.annualized_return:.2%}, "
                       f"Sharpe: {report.portfolio_metrics.sharpe_ratio:.2f}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report for {portfolio_name}: {e}")
            report.warnings.append(f"Report generation error: {str(e)}")
            return report
    
    def _get_period_returns(self, returns: pd.Series, period: PerformancePeriod) -> pd.Series:
        """Get returns for a specific period"""
        
        if period == PerformancePeriod.DAILY:
            return returns
        elif period == PerformancePeriod.WEEKLY:
            return returns.resample('W').apply(lambda x: (1 + x).prod() - 1)
        elif period == PerformancePeriod.MONTHLY:
            return returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        elif period == PerformancePeriod.QUARTERLY:
            return returns.resample('Q').apply(lambda x: (1 + x).prod() - 1)
        elif period == PerformancePeriod.YEARLY:
            return returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)
        else:
            return returns
    
    def _calculate_rolling_sharpe(self, returns: pd.Series, window: int = 252) -> pd.Series:
        """Calculate rolling Sharpe ratio"""
        
        if len(returns) < window:
            return pd.Series(dtype=float)
        
        risk_free_daily = self._get_risk_free_rate() / self._get_periods_per_year(returns)
        excess_returns = returns - risk_free_daily
        
        rolling_mean = excess_returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        
        return rolling_mean / rolling_std * np.sqrt(self._get_periods_per_year(returns))
    
    def _calculate_rolling_volatility(self, returns: pd.Series, window: int = 252) -> pd.Series:
        """Calculate rolling volatility"""
        
        if len(returns) < window:
            return pd.Series(dtype=float)
        
        return returns.rolling(window).std() * np.sqrt(self._get_periods_per_year(returns))
    
    def _calculate_rolling_drawdown(self, returns: pd.Series) -> pd.Series:
        """Calculate rolling drawdown"""
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        
        return (cumulative - running_max) / running_max
    
    def _calculate_drawdown_series(self, returns: pd.Series) -> pd.Series:
        """Calculate drawdown series"""
        
        return self._calculate_rolling_drawdown(returns)
    
    def _create_monthly_returns_table(self, returns: pd.Series) -> pd.DataFrame:
        """Create monthly returns table"""
        
        try:
            monthly_returns = returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
            
            # Create year-month matrix
            monthly_table = monthly_returns.to_frame('Returns')
            monthly_table['Year'] = monthly_table.index.year
            monthly_table['Month'] = monthly_table.index.month
            
            pivot_table = monthly_table.pivot_table(
                values='Returns',
                index='Year',
                columns='Month',
                aggfunc='first'
            )
            
            # Add month names as columns
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            pivot_table.columns = [month_names[i-1] for i in pivot_table.columns]
            
            # Add annual totals
            annual_returns = returns.resample('Y').apply(lambda x: (1 + x).prod() - 1)
            pivot_table['Annual'] = annual_returns.groupby(annual_returns.index.year).first()
            
            return pivot_table
            
        except Exception as e:
            logger.error(f"Error creating monthly returns table: {e}")
            return pd.DataFrame()
    
    def _create_summary_statistics(self, report: PerformanceReport) -> Dict[str, Any]:
        """Create summary statistics"""
        
        metrics = report.portfolio_metrics
        
        return {
            'performance_summary': {
                'total_return': f"{metrics.total_return:.2%}",
                'annualized_return': f"{metrics.annualized_return:.2%}",
                'volatility': f"{metrics.volatility:.2%}",
                'sharpe_ratio': f"{metrics.sharpe_ratio:.2f}",
                'maximum_drawdown': f"{metrics.maximum_drawdown:.2%}"
            },
            'risk_summary': {
                'var_95': f"{metrics.var_95:.2%}",
                'cvar_95': f"{metrics.cvar_95:.2%}",
                'skewness': f"{metrics.skewness:.2f}",
                'kurtosis': f"{metrics.kurtosis:.2f}"
            },
            'trading_summary': {
                'win_rate': f"{metrics.win_rate:.1%}",
                'profit_factor': f"{metrics.profit_factor:.2f}",
                'total_trades': metrics.total_trades
            }
        }
    
    def _generate_report_notes(self, report: PerformanceReport) -> List[str]:
        """Generate report notes"""
        
        notes = []
        metrics = report.portfolio_metrics
        
        # Performance notes
        if metrics.annualized_return > 0.15:
            notes.append("Exceptional annual return performance")
        elif metrics.annualized_return > 0.10:
            notes.append("Strong annual return performance")
        
        # Risk notes
        if metrics.sharpe_ratio > 2.0:
            notes.append("Excellent risk-adjusted returns")
        elif metrics.sharpe_ratio > 1.0:
            notes.append("Good risk-adjusted returns")
        
        # Drawdown notes
        if metrics.maximum_drawdown < 0.05:
            notes.append("Low maximum drawdown indicates good risk control")
        
        return notes
    
    def _generate_report_warnings(self, report: PerformanceReport) -> List[str]:
        """Generate report warnings"""
        
        warnings = []
        metrics = report.portfolio_metrics
        
        # Risk warnings
        if metrics.maximum_drawdown > 0.20:
            warnings.append("High maximum drawdown - review risk management")
        
        if metrics.volatility > 0.30:
            warnings.append("High volatility - consider position sizing")
        
        if metrics.sharpe_ratio < 0:
            warnings.append("Negative Sharpe ratio - strategy may need review")
        
        # Data quality warnings
        if metrics.total_trades < 30:
            warnings.append("Limited trade data - results may not be statistically significant")
        
        return warnings
    
    def cache_performance_metrics(self, symbol: str, metrics: PerformanceMetrics) -> None:
        """Cache performance metrics"""
        
        with self._lock:
            self._performance_cache[symbol] = metrics
    
    def get_cached_metrics(self, symbol: str) -> Optional[PerformanceMetrics]:
        """Get cached performance metrics"""
        
        with self._lock:
            return self._performance_cache.get(symbol)
    
    def clear_cache(self) -> None:
        """Clear performance cache"""
        
        with self._lock:
            self._performance_cache.clear()
            logger.info("Performance cache cleared")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance analysis summary"""
        
        with self._lock:
            return {
                'cached_metrics': len(self._performance_cache),
                'benchmark_data_available': len(self._benchmark_data),
                'analyzer_config': {
                    'risk_free_rate_source': self.config.risk_free_rate_source.value,
                    'trading_days_per_year': self.config.trading_days_per_year,
                    'confidence_level': self.config.confidence_level
                }
            }