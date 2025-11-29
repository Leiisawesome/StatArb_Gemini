"""
Analytics Engine - Benchmark Analyzer
Advanced benchmark analysis and comparative performance evaluation
"""

import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# Import canonical metric functions from core_metrics (Rule: Single Source of Truth)
from .core_metrics import (
    calculate_drawdown,
    calculate_sharpe_ratio,
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks"""
    MARKET_INDEX = "market_index"
    SECTOR_INDEX = "sector_index"
    STYLE_INDEX = "style_index"
    PEER_GROUP = "peer_group"
    COMPOSITE = "composite"
    CUSTOM = "custom"


class ComparisonMethod(Enum):
    """Comparison methods"""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    RISK_ADJUSTED = "risk_adjusted"
    DRAWDOWN_ADJUSTED = "drawdown_adjusted"
    FACTOR_ADJUSTED = "factor_adjusted"


class AttributionMethod(Enum):
    """Attribution analysis methods"""
    REGRESSION_BASED = "regression_based"
    HOLDINGS_BASED = "holdings_based"
    RETURNS_BASED = "returns_based"
    FACTOR_MODEL = "factor_model"


@dataclass
class BenchmarkConfig:
    """Benchmark analysis configuration"""
    # Primary benchmark
    primary_benchmark: str = "SPY"
    
    # Additional benchmarks
    secondary_benchmarks: List[str] = field(default_factory=lambda: ["QQQ", "IWM", "EFA"])
    
    # Risk-free rate proxy
    risk_free_symbol: str = "^TNX"  # 10-year Treasury
    risk_free_rate: float = 0.02  # Fallback rate
    
    # Analysis settings
    comparison_methods: List[ComparisonMethod] = field(default_factory=lambda: [
        ComparisonMethod.ABSOLUTE,
        ComparisonMethod.RELATIVE,
        ComparisonMethod.RISK_ADJUSTED
    ])
    
    # Rolling analysis
    rolling_windows: Dict[str, int] = field(default_factory=lambda: {
        'short': 21,    # 1 month
        'medium': 63,   # 3 months
        'long': 252,    # 1 year
        'very_long': 504  # 2 years
    })
    
    # Statistical settings
    confidence_level: float = 0.95
    min_observations: int = 30
    
    # Factor analysis
    factor_models: List[str] = field(default_factory=lambda: [
        'market', 'fama_french_3', 'carhart_4'
    ])
    
    # Performance attribution
    attribution_methods: List[AttributionMethod] = field(default_factory=lambda: [
        AttributionMethod.REGRESSION_BASED,
        AttributionMethod.RETURNS_BASED
    ])
    
    # Advanced settings
    enable_regime_analysis: bool = True
    enable_tail_analysis: bool = True
    enable_correlation_analysis: bool = True


@dataclass
class BenchmarkData:
    """Benchmark data container"""
    symbol: str
    name: str
    benchmark_type: BenchmarkType
    
    # Price and return data
    prices: pd.Series = field(default_factory=pd.Series)
    returns: pd.Series = field(default_factory=pd.Series)
    
    # Metadata
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    currency: str = "USD"
    
    # Statistical properties
    mean_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Data quality
    data_quality_score: float = 0.0
    missing_data_pct: float = 0.0


@dataclass
class ComparisonResult:
    """Benchmark comparison result"""
    portfolio_symbol: str
    benchmark_symbol: str
    comparison_method: ComparisonMethod
    
    # Absolute metrics
    portfolio_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    
    # Risk metrics
    portfolio_volatility: float = 0.0
    benchmark_volatility: float = 0.0
    tracking_error: float = 0.0
    
    # Risk-adjusted metrics
    portfolio_sharpe: float = 0.0
    benchmark_sharpe: float = 0.0
    information_ratio: float = 0.0
    
    # Correlation and beta
    correlation: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    
    # Statistical tests
    t_statistic: float = 0.0
    p_value: float = 0.0
    is_significant: bool = False
    
    # Drawdown comparison
    portfolio_max_dd: float = 0.0
    benchmark_max_dd: float = 0.0
    
    # Additional metrics
    hit_ratio: float = 0.0  # Percentage of periods beating benchmark
    up_capture: float = 0.0  # Upside capture ratio
    down_capture: float = 0.0  # Downside capture ratio
    
    # Metadata
    analysis_period: Tuple[datetime, datetime] = field(default_factory=lambda: (datetime.now(), datetime.now()))
    data_points: int = 0


@dataclass
class FactorAnalysisResult:
    """Factor analysis result"""
    portfolio_symbol: str
    factor_model: str
    
    # Factor loadings (betas)
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    factor_loading_errors: Dict[str, float] = field(default_factory=dict)
    factor_t_stats: Dict[str, float] = field(default_factory=dict)
    
    # Model statistics
    alpha: float = 0.0
    alpha_error: float = 0.0
    alpha_t_stat: float = 0.0
    
    # Model fit
    r_squared: float = 0.0
    adjusted_r_squared: float = 0.0
    f_statistic: float = 0.0
    f_p_value: float = 0.0
    
    # Residual analysis
    residual_volatility: float = 0.0
    residual_skewness: float = 0.0
    residual_kurtosis: float = 0.0
    
    # Factor contribution
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    unexplained_return: float = 0.0


class BenchmarkDataManager:
    """Manages benchmark data"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self._benchmark_cache = {}
        self._lock = threading.Lock()
    
    def load_benchmark_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        data_source: Optional[Callable] = None
    ) -> Optional[BenchmarkData]:
        """Load benchmark data"""
        
        cache_key = f"{symbol}_{start_date.date()}_{end_date.date()}"
        
        with self._lock:
            if cache_key in self._benchmark_cache:
                return self._benchmark_cache[cache_key]
        
        try:
            # Mock data generation (replace with real data source)
            if data_source is None:
                data = self._generate_mock_benchmark_data(symbol, start_date, end_date)
            else:
                data = data_source(symbol, start_date, end_date)
            
            # Create BenchmarkData object
            benchmark_data = BenchmarkData(
                symbol=symbol,
                name=self._get_benchmark_name(symbol),
                benchmark_type=self._get_benchmark_type(symbol),
                prices=data['prices'] if 'prices' in data else pd.Series(),
                returns=data['returns'] if 'returns' in data else pd.Series(),
                start_date=start_date,
                end_date=end_date
            )
            
            # Calculate statistics
            if not benchmark_data.returns.empty:
                benchmark_data.mean_return = benchmark_data.returns.mean() * 252
                benchmark_data.volatility = benchmark_data.returns.std() * np.sqrt(252)
                
                excess_returns = benchmark_data.returns - self.config.risk_free_rate / 252
                if benchmark_data.volatility > 0:
                    benchmark_data.sharpe_ratio = excess_returns.mean() / benchmark_data.returns.std() * np.sqrt(252)
                
                benchmark_data.max_drawdown = self._calculate_max_drawdown(benchmark_data.returns)
                benchmark_data.data_quality_score = self._assess_data_quality(benchmark_data.returns)
                benchmark_data.missing_data_pct = benchmark_data.returns.isna().sum() / len(benchmark_data.returns)
            
            # Cache the data
            with self._lock:
                self._benchmark_cache[cache_key] = benchmark_data
            
            return benchmark_data
            
        except Exception as e:
            logger.error(f"Error loading benchmark data for {symbol}: {e}")
            return None
    
    def _generate_mock_benchmark_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.Series]:
        """Generate mock benchmark data for testing"""
        
        # Create date range
        dates = pd.bdate_range(start=start_date, end=end_date)
        
        # Generate mock returns based on symbol
        np.random.seed(hash(symbol) % 2**32)
        
        if symbol == "SPY":
            returns = np.random.normal(0.0008, 0.012, len(dates))  # Market returns
        elif symbol == "QQQ":
            returns = np.random.normal(0.001, 0.018, len(dates))   # Tech-heavy
        elif symbol == "IWM":
            returns = np.random.normal(0.0007, 0.015, len(dates))  # Small cap
        else:
            returns = np.random.normal(0.0005, 0.010, len(dates))  # Default
        
        returns_series = pd.Series(returns, index=dates)
        
        # Generate prices
        initial_price = 100.0
        prices = (1 + returns_series).cumprod() * initial_price
        
        return {
            'prices': prices,
            'returns': returns_series
        }
    
    def _get_benchmark_name(self, symbol: str) -> str:
        """Get benchmark name"""
        
        name_mapping = {
            'SPY': 'SPDR S&P 500 ETF',
            'QQQ': 'Invesco QQQ Trust',
            'IWM': 'iShares Russell 2000 ETF',
            'EFA': 'iShares MSCI EAFE ETF',
            'AGG': 'iShares Core Aggregate Bond ETF',
            'VTI': 'Vanguard Total Stock Market ETF'
        }
        
        return name_mapping.get(symbol, f"Benchmark {symbol}")
    
    def _get_benchmark_type(self, symbol: str) -> BenchmarkType:
        """Get benchmark type"""
        
        if symbol in ['SPY', 'VTI', 'IVV']:
            return BenchmarkType.MARKET_INDEX
        elif symbol in ['QQQ', 'XLK', 'XLF']:
            return BenchmarkType.SECTOR_INDEX
        elif symbol in ['IWM', 'IJR', 'VB']:
            return BenchmarkType.STYLE_INDEX
        else:
            return BenchmarkType.CUSTOM
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown - delegates to core_metrics"""
        if returns.empty:
            return 0.0
        _, max_dd, _ = calculate_drawdown(returns)
        return abs(max_dd)
    
    def _assess_data_quality(self, returns: pd.Series) -> float:
        """Assess data quality"""
        
        if returns.empty:
            return 0.0
        
        quality_score = 1.0
        
        # Missing data penalty
        missing_ratio = returns.isna().sum() / len(returns)
        quality_score -= missing_ratio * 0.5
        
        # Outlier penalty
        if returns.std() > 0:
            outliers = abs(returns - returns.mean()) > 3 * returns.std()
            outlier_ratio = outliers.sum() / len(returns)
            quality_score -= outlier_ratio * 0.3
        
        return max(quality_score, 0.0)


class PerformanceComparator:
    """Compares portfolio performance against benchmarks"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
    
    def compare_performance(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        portfolio_symbol: str,
        benchmark_symbol: str,
        method: ComparisonMethod = ComparisonMethod.RISK_ADJUSTED
    ) -> ComparisonResult:
        """Compare portfolio performance against benchmark"""
        
        # Align data
        aligned_portfolio, aligned_benchmark = portfolio_returns.align(
            benchmark_returns, join='inner'
        )
        
        if len(aligned_portfolio) < self.config.min_observations:
            logger.warning(f"Insufficient data for comparison: {len(aligned_portfolio)} observations")
            return ComparisonResult(
                portfolio_symbol=portfolio_symbol,
                benchmark_symbol=benchmark_symbol,
                comparison_method=method
            )
        
        result = ComparisonResult(
            portfolio_symbol=portfolio_symbol,
            benchmark_symbol=benchmark_symbol,
            comparison_method=method,
            analysis_period=(aligned_portfolio.index[0], aligned_portfolio.index[-1]),
            data_points=len(aligned_portfolio)
        )
        
        # Calculate basic metrics
        result.portfolio_return = aligned_portfolio.mean() * 252
        result.benchmark_return = aligned_benchmark.mean() * 252
        result.excess_return = result.portfolio_return - result.benchmark_return
        
        result.portfolio_volatility = aligned_portfolio.std() * np.sqrt(252)
        result.benchmark_volatility = aligned_benchmark.std() * np.sqrt(252)
        
        # Active returns
        active_returns = aligned_portfolio - aligned_benchmark
        result.tracking_error = active_returns.std() * np.sqrt(252)
        
        # Risk-adjusted metrics
        risk_free_rate = self.config.risk_free_rate / 252
        
        portfolio_excess = aligned_portfolio - risk_free_rate
        benchmark_excess = aligned_benchmark - risk_free_rate
        
        if result.portfolio_volatility > 0:
            result.portfolio_sharpe = portfolio_excess.mean() / aligned_portfolio.std() * np.sqrt(252)
        
        if result.benchmark_volatility > 0:
            result.benchmark_sharpe = benchmark_excess.mean() / aligned_benchmark.std() * np.sqrt(252)
        
        if result.tracking_error > 0:
            result.information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252)
        
        # Correlation and beta
        if len(aligned_portfolio) > 1:
            result.correlation = aligned_portfolio.corr(aligned_benchmark)
            
            if aligned_benchmark.var() > 0:
                result.beta = aligned_portfolio.cov(aligned_benchmark) / aligned_benchmark.var()
                result.alpha = (result.portfolio_return - risk_free_rate * 252) - \
                              result.beta * (result.benchmark_return - risk_free_rate * 252)
        
        # Statistical significance test
        if len(active_returns) > 1:
            result.t_statistic, result.p_value = stats.ttest_1samp(active_returns, 0)
            result.is_significant = result.p_value < (1 - self.config.confidence_level)
        
        # Drawdown analysis
        result.portfolio_max_dd = self._calculate_max_drawdown(aligned_portfolio)
        result.benchmark_max_dd = self._calculate_max_drawdown(aligned_benchmark)
        
        # Hit ratio
        outperformance = active_returns > 0
        result.hit_ratio = outperformance.sum() / len(active_returns)
        
        # Capture ratios
        result.up_capture, result.down_capture = self._calculate_capture_ratios(
            aligned_portfolio, aligned_benchmark
        )
        
        return result
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown - delegates to core_metrics"""
        if returns.empty:
            return 0.0
        _, max_dd, _ = calculate_drawdown(returns)
        return abs(max_dd)
    
    def _calculate_capture_ratios(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> Tuple[float, float]:
        """Calculate upside and downside capture ratios"""
        
        # Upside capture
        up_periods = benchmark_returns > 0
        if up_periods.sum() > 0:
            up_capture = portfolio_returns[up_periods].mean() / benchmark_returns[up_periods].mean()
        else:
            up_capture = 0.0
        
        # Downside capture
        down_periods = benchmark_returns < 0
        if down_periods.sum() > 0:
            down_capture = portfolio_returns[down_periods].mean() / benchmark_returns[down_periods].mean()
        else:
            down_capture = 0.0
        
        return up_capture, down_capture


class FactorAnalyzer:
    """Factor-based performance analysis"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
    
    def analyze_factors(
        self,
        portfolio_returns: pd.Series,
        factor_returns: Dict[str, pd.Series],
        portfolio_symbol: str,
        model_name: str = "custom"
    ) -> FactorAnalysisResult:
        """Perform factor analysis"""
        
        # Align all data
        all_data = pd.DataFrame({'portfolio': portfolio_returns})
        for factor_name, factor_series in factor_returns.items():
            all_data[factor_name] = factor_series
        
        # Drop missing values
        all_data = all_data.dropna()
        
        if len(all_data) < self.config.min_observations:
            logger.warning(f"Insufficient data for factor analysis: {len(all_data)} observations")
            return FactorAnalysisResult(
                portfolio_symbol=portfolio_symbol,
                factor_model=model_name
            )
        
        # Prepare regression data
        y = all_data['portfolio'].values
        X = all_data.drop('portfolio', axis=1).values
        factor_names = list(factor_returns.keys())
        
        # Fit regression model
        model = LinearRegression(fit_intercept=True)
        model.fit(X, y)
        
        # Calculate predictions and residuals
        y_pred = model.predict(X)
        residuals = y - y_pred
        
        # Create result object
        result = FactorAnalysisResult(
            portfolio_symbol=portfolio_symbol,
            factor_model=model_name
        )
        
        # Alpha (intercept)
        result.alpha = model.intercept_ * 252  # Annualized
        
        # Factor loadings (betas)
        for i, factor_name in enumerate(factor_names):
            result.factor_loadings[factor_name] = model.coef_[i]
        
        # Model fit statistics
        result.r_squared = r2_score(y, y_pred)
        
        n = len(y)
        k = len(factor_names)
        if n > k + 1:
            result.adjusted_r_squared = 1 - (1 - result.r_squared) * (n - 1) / (n - k - 1)
        
        # Residual analysis
        result.residual_volatility = np.std(residuals) * np.sqrt(252)
        result.residual_skewness = stats.skew(residuals)
        result.residual_kurtosis = stats.kurtosis(residuals)
        
        # Calculate standard errors and t-statistics
        self._calculate_regression_statistics(result, X, y, residuals, factor_names)
        
        # Factor contributions
        for i, factor_name in enumerate(factor_names):
            factor_return = all_data[factor_name].mean() * 252
            result.factor_contributions[factor_name] = result.factor_loadings[factor_name] * factor_return
        
        result.unexplained_return = result.alpha
        
        return result
    
    def _calculate_regression_statistics(
        self,
        result: FactorAnalysisResult,
        X: np.ndarray,
        y: np.ndarray,
        residuals: np.ndarray,
        factor_names: List[str]
    ) -> None:
        """Calculate regression statistics"""
        
        try:
            n = len(y)
            k = X.shape[1]
            
            # Residual variance
            mse = np.sum(residuals**2) / (n - k - 1)
            
            # Covariance matrix of coefficients
            XtX_inv = np.linalg.inv(X.T @ X)
            
            # Standard errors
            intercept_se = np.sqrt(mse * (1/n + np.mean(X, axis=0) @ XtX_inv @ np.mean(X, axis=0)))
            coef_se = np.sqrt(mse * np.diag(XtX_inv))
            
            # T-statistics
            result.alpha_error = intercept_se
            result.alpha_t_stat = result.alpha / (intercept_se * np.sqrt(252)) if intercept_se > 0 else 0
            
            for i, factor_name in enumerate(factor_names):
                result.factor_loading_errors[factor_name] = coef_se[i]
                if coef_se[i] > 0:
                    result.factor_t_stats[factor_name] = result.factor_loadings[factor_name] / coef_se[i]
                else:
                    result.factor_t_stats[factor_name] = 0
            
            # F-statistic
            if k > 0:
                ss_reg = np.sum((np.mean(y) - y)**2) - np.sum(residuals**2)
                ss_res = np.sum(residuals**2)
                result.f_statistic = (ss_reg / k) / (ss_res / (n - k - 1))
                result.f_p_value = 1 - stats.f.cdf(result.f_statistic, k, n - k - 1)
            
        except Exception as e:
            logger.warning(f"Error calculating regression statistics: {e}")


class RollingAnalyzer:
    """Rolling benchmark analysis"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.comparator = PerformanceComparator(config)
    
    def rolling_comparison(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        window_name: str = 'medium'
    ) -> pd.DataFrame:
        """Perform rolling benchmark comparison"""
        
        window = self.config.rolling_windows.get(window_name, 63)
        
        # Align data
        aligned_portfolio, aligned_benchmark = portfolio_returns.align(
            benchmark_returns, join='inner'
        )
        
        if len(aligned_portfolio) < window:
            logger.warning(f"Insufficient data for rolling analysis: {len(aligned_portfolio)} < {window}")
            return pd.DataFrame()
        
        # Calculate rolling metrics
        rolling_results = []
        
        for i in range(window, len(aligned_portfolio) + 1):
            window_portfolio = aligned_portfolio.iloc[i-window:i]
            window_benchmark = aligned_benchmark.iloc[i-window:i]
            
            # Calculate metrics for this window
            metrics = {
                'date': aligned_portfolio.index[i-1],
                'excess_return': (window_portfolio.mean() - window_benchmark.mean()) * 252,
                'tracking_error': (window_portfolio - window_benchmark).std() * np.sqrt(252),
                'correlation': window_portfolio.corr(window_benchmark),
                'beta': window_portfolio.cov(window_benchmark) / window_benchmark.var() if window_benchmark.var() > 0 else 0,
                'portfolio_sharpe': self._calculate_sharpe(window_portfolio),
                'benchmark_sharpe': self._calculate_sharpe(window_benchmark),
                'hit_ratio': (window_portfolio > window_benchmark).sum() / len(window_portfolio)
            }
            
            if metrics['tracking_error'] > 0:
                metrics['information_ratio'] = metrics['excess_return'] / metrics['tracking_error']
            else:
                metrics['information_ratio'] = 0
            
            rolling_results.append(metrics)
        
        return pd.DataFrame(rolling_results).set_index('date')
    
    def _calculate_sharpe(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio - delegates to core_metrics"""
        return calculate_sharpe_ratio(
            returns, 
            risk_free_rate=self.config.risk_free_rate,
            periods_per_year=252
        )


class BenchmarkAnalyzer:
    """
    Advanced Benchmark Analyzer
    
    Comprehensive benchmark analysis with performance comparison,
    factor analysis, and rolling metrics.
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize benchmark analyzer"""
        self.config = config or BenchmarkConfig()
        
        # Component analyzers
        self.data_manager = BenchmarkDataManager(self.config)
        self.comparator = PerformanceComparator(self.config)
        self.factor_analyzer = FactorAnalyzer(self.config)
        self.rolling_analyzer = RollingAnalyzer(self.config)
        
        # Analysis cache
        self._analysis_cache = {}
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info("Benchmark Analyzer initialized")
    
    async def analyze_against_benchmark(
        self,
        portfolio_returns: pd.Series,
        portfolio_symbol: str,
        benchmark_symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Comprehensive benchmark analysis"""
        
        benchmark_symbol = benchmark_symbol or self.config.primary_benchmark
        
        # Determine date range
        if start_date is None:
            start_date = portfolio_returns.index[0]
        if end_date is None:
            end_date = portfolio_returns.index[-1]
        
        try:
            # Load benchmark data
            benchmark_data = self.data_manager.load_benchmark_data(
                benchmark_symbol, start_date, end_date
            )
            
            if benchmark_data is None or benchmark_data.returns.empty:
                logger.error(f"Could not load benchmark data for {benchmark_symbol}")
                return {}
            
            results = {
                'portfolio_symbol': portfolio_symbol,
                'benchmark_symbol': benchmark_symbol,
                'analysis_timestamp': datetime.now(),
                'benchmark_info': {
                    'name': benchmark_data.name,
                    'type': benchmark_data.benchmark_type.value,
                    'data_quality': benchmark_data.data_quality_score
                }
            }
            
            # Performance comparison
            comparison_results = {}
            for method in self.config.comparison_methods:
                comparison = self.comparator.compare_performance(
                    portfolio_returns,
                    benchmark_data.returns,
                    portfolio_symbol,
                    benchmark_symbol,
                    method
                )
                comparison_results[method.value] = comparison
            
            results['performance_comparison'] = comparison_results
            
            # Rolling analysis
            if len(portfolio_returns) >= self.config.rolling_windows['medium']:
                rolling_results = {}
                for window_name in self.config.rolling_windows.keys():
                    rolling_data = self.rolling_analyzer.rolling_comparison(
                        portfolio_returns,
                        benchmark_data.returns,
                        window_name
                    )
                    if not rolling_data.empty:
                        rolling_results[window_name] = rolling_data
                
                results['rolling_analysis'] = rolling_results
            
            # Cache results
            cache_key = f"{portfolio_symbol}_{benchmark_symbol}_{start_date.date()}_{end_date.date()}"
            with self._lock:
                self._analysis_cache[cache_key] = results
            
            logger.info(f"Benchmark analysis completed for {portfolio_symbol} vs {benchmark_symbol}")
            return results
            
        except Exception as e:
            logger.error(f"Error in benchmark analysis: {e}")
            return {}
    
    async def multi_benchmark_analysis(
        self,
        portfolio_returns: pd.Series,
        portfolio_symbol: str,
        benchmark_symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze against multiple benchmarks"""
        
        benchmark_symbols = benchmark_symbols or [self.config.primary_benchmark] + self.config.secondary_benchmarks
        
        results = {}
        
        for benchmark_symbol in benchmark_symbols:
            try:
                analysis = await self.analyze_against_benchmark(
                    portfolio_returns,
                    portfolio_symbol,
                    benchmark_symbol
                )
                
                if analysis:
                    results[benchmark_symbol] = analysis
                    
            except Exception as e:
                logger.error(f"Error analyzing against {benchmark_symbol}: {e}")
                continue
        
        return results
    
    def factor_analysis(
        self,
        portfolio_returns: pd.Series,
        portfolio_symbol: str,
        custom_factors: Optional[Dict[str, pd.Series]] = None
    ) -> Dict[str, FactorAnalysisResult]:
        """Perform factor analysis"""
        
        results = {}
        
        # Use provided factors or generate standard factors
        if custom_factors:
            factor_dict = custom_factors
            model_name = "custom"
        else:
            # Generate mock factor data (replace with real factor data)
            factor_dict = self._generate_standard_factors(portfolio_returns.index)
            model_name = "standard"
        
        try:
            analysis = self.factor_analyzer.analyze_factors(
                portfolio_returns,
                factor_dict,
                portfolio_symbol,
                model_name
            )
            
            results[model_name] = analysis
            
        except Exception as e:
            logger.error(f"Error in factor analysis: {e}")
        
        return results
    
    def _generate_standard_factors(self, dates: pd.DatetimeIndex) -> Dict[str, pd.Series]:
        """Generate standard factor data (mock implementation)"""
        
        np.random.seed(42)
        
        factors = {}
        
        # Market factor (excess market return)
        market_returns = np.random.normal(0.0008, 0.012, len(dates))
        risk_free = self.config.risk_free_rate / 252
        factors['market'] = pd.Series(market_returns - risk_free, index=dates)
        
        # Size factor (SMB - Small minus Big)
        smb_returns = np.random.normal(0.0002, 0.008, len(dates))
        factors['size'] = pd.Series(smb_returns, index=dates)
        
        # Value factor (HML - High minus Low)
        hml_returns = np.random.normal(0.0001, 0.006, len(dates))
        factors['value'] = pd.Series(hml_returns, index=dates)
        
        # Momentum factor (WML - Winners minus Losers)
        wml_returns = np.random.normal(0.0003, 0.009, len(dates))
        factors['momentum'] = pd.Series(wml_returns, index=dates)
        
        return factors
    
    def get_benchmark_summary(self, benchmark_symbol: str) -> Dict[str, Any]:
        """Get benchmark summary statistics"""
        
        # Look for cached benchmark data
        with self._lock:
            for cache_key, benchmark_data in self.data_manager._benchmark_cache.items():
                if benchmark_symbol in cache_key:
                    return {
                        'symbol': benchmark_data.symbol,
                        'name': benchmark_data.name,
                        'type': benchmark_data.benchmark_type.value,
                        'mean_return': benchmark_data.mean_return,
                        'volatility': benchmark_data.volatility,
                        'sharpe_ratio': benchmark_data.sharpe_ratio,
                        'max_drawdown': benchmark_data.max_drawdown,
                        'data_quality': benchmark_data.data_quality_score,
                        'start_date': benchmark_data.start_date,
                        'end_date': benchmark_data.end_date
                    }
        
        return {}
    
    def get_analysis_summary(
        self,
        portfolio_symbol: str,
        benchmark_symbol: str
    ) -> Dict[str, Any]:
        """Get analysis summary"""
        
        with self._lock:
            # Find matching analysis in cache
            for cache_key, analysis in self._analysis_cache.items():
                if portfolio_symbol in cache_key and benchmark_symbol in cache_key:
                    
                    summary = {
                        'portfolio': portfolio_symbol,
                        'benchmark': benchmark_symbol,
                        'analysis_date': analysis['analysis_timestamp']
                    }
                    
                    # Extract key metrics from comparison
                    if 'performance_comparison' in analysis:
                        risk_adj_comparison = analysis['performance_comparison'].get('risk_adjusted')
                        if risk_adj_comparison:
                            summary.update({
                                'excess_return': risk_adj_comparison.excess_return,
                                'tracking_error': risk_adj_comparison.tracking_error,
                                'information_ratio': risk_adj_comparison.information_ratio,
                                'beta': risk_adj_comparison.beta,
                                'alpha': risk_adj_comparison.alpha,
                                'correlation': risk_adj_comparison.correlation,
                                'hit_ratio': risk_adj_comparison.hit_ratio
                            })
                    
                    return summary
        
        return {}
    
    def clear_cache(self) -> None:
        """Clear analysis cache"""
        
        with self._lock:
            self._analysis_cache.clear()
            self.data_manager._benchmark_cache.clear()
            logger.info("Benchmark analysis cache cleared")
    
    def get_analyzer_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        
        with self._lock:
            cached_analyses = len(self._analysis_cache)
            cached_benchmarks = len(self.data_manager._benchmark_cache)
        
        return {
            'cached_analyses': cached_analyses,
            'cached_benchmarks': cached_benchmarks,
            'configured_benchmarks': {
                'primary': self.config.primary_benchmark,
                'secondary': self.config.secondary_benchmarks
            },
            'analysis_capabilities': {
                'comparison_methods': [method.value for method in self.config.comparison_methods],
                'factor_models': self.config.factor_models,
                'rolling_windows': self.config.rolling_windows
            }
        }