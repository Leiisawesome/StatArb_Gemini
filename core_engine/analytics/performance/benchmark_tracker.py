"""
Performance Engine - Benchmark Tracker
Comprehensive benchmark tracking and relative performance analysis
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict
import threading
import yfinance as yf

# Import fail-fast exceptions
from ...exceptions import BenchmarkDataUnavailableError

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """Types of benchmarks"""
    MARKET_INDEX = "market_index"
    SECTOR_INDEX = "sector_index"
    CUSTOM_INDEX = "custom_index"
    PEER_GROUP = "peer_group"
    COMPOSITE = "composite"
    FACTOR_BASED = "factor_based"


class RebalanceFrequency(Enum):
    """Benchmark rebalancing frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class TrackingMethod(Enum):
    """Tracking error calculation methods"""
    STANDARD = "standard"
    DOWNSIDE = "downside"
    RELATIVE_VAR = "relative_var"
    INFORMATION_RATIO = "information_ratio"


@dataclass
class BenchmarkData:
    """Benchmark data container"""
    
    # Basic information
    symbol: str
    name: str
    benchmark_type: BenchmarkType
    
    # Time series data
    prices: pd.Series = field(default_factory=pd.Series)
    returns: pd.Series = field(default_factory=pd.Series)
    
    # Composition data
    constituents: Dict[str, float] = field(default_factory=dict)  # symbol -> weight
    sector_weights: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    inception_date: Optional[datetime] = None
    last_rebalance: Optional[datetime] = None
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.QUARTERLY
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    max_drawdown: float = 0.0
    
    # Custom attributes
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelativePerformanceMetrics:
    """Relative performance metrics container"""
    
    # Basic relative metrics
    excess_return: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    
    # Advanced metrics
    active_return: float = 0.0
    relative_volatility: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    r_squared: float = 0.0
    
    # Downside metrics
    downside_deviation: float = 0.0
    downside_beta: float = 0.0
    upside_capture: float = 0.0
    downside_capture: float = 0.0
    
    # Risk metrics
    relative_var: float = 0.0
    relative_cvar: float = 0.0
    maximum_adverse_excursion: float = 0.0
    
    # Timing metrics
    correlation: float = 0.0
    hit_rate: float = 0.0  # Percentage of periods outperforming benchmark
    
    # Analysis period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    calculation_time: datetime = field(default_factory=datetime.now)


@dataclass
class BenchmarkConfig:
    """Benchmark tracker configuration"""
    
    # Data settings
    default_benchmark: str = "SPY"
    data_frequency: str = "daily"  # daily, weekly, monthly
    
    # Tracking settings
    tracking_method: TrackingMethod = TrackingMethod.STANDARD
    min_tracking_periods: int = 30
    confidence_level: float = 0.95
    
    # Rebalancing
    auto_rebalance: bool = True
    rebalance_threshold: float = 0.05  # 5% drift threshold
    
    # Performance calculation
    risk_free_rate: float = 0.02
    business_days_per_year: int = 252
    
    # Data sources
    enable_live_data: bool = True
    cache_data: bool = True
    max_cache_age: timedelta = timedelta(hours=1)
    
    # Advanced settings
    enable_sector_analysis: bool = True
    enable_factor_decomposition: bool = True
    enable_peer_comparison: bool = False


class BenchmarkDataProvider:
    """Benchmark data provider with multiple sources"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self._data_cache: Dict[str, Tuple[pd.Series, datetime]] = {}
        self._composition_cache: Dict[str, Tuple[Dict[str, float], datetime]] = {}
        
        logger.info("Benchmark data provider initialized")
    
    async def get_benchmark_prices(self, symbol: str, 
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> pd.Series:
        """Get benchmark price data"""
        
        try:
            # Check cache first
            if self.config.cache_data and symbol in self._data_cache:
                cached_data, cache_time = self._data_cache[symbol]
                if datetime.now() - cache_time < self.config.max_cache_age:
                    if start_date and end_date:
                        return cached_data.loc[start_date:end_date]
                    return cached_data
            
            # Download fresh data
            if self.config.enable_live_data:
                prices = await self._download_prices_async(symbol, start_date, end_date)
            else:
                # Require real data - FAIL FAST if live data disabled
                raise BenchmarkDataUnavailableError(
                    f"Live data disabled for {symbol}. Real benchmark data required. "
                    "Cannot proceed with mock data."
                )
            
            # Cache the data
            if self.config.cache_data:
                self._data_cache[symbol] = (prices, datetime.now())
            
            logger.debug(f"Retrieved {len(prices)} price points for {symbol}")
            
            return prices
            
        except Exception as e:
            if isinstance(e, BenchmarkDataUnavailableError):
                raise
            raise BenchmarkDataUnavailableError(
                f"Error getting benchmark prices for {symbol}: {e}. "
                "Real benchmark data required."
            ) from e
    
    async def _download_prices_async(self, symbol: str,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> pd.Series:
        """Download prices asynchronously"""
        
        try:
            # Use yfinance for real data (in production, might use other sources)
            end_str = end_date.strftime('%Y-%m-%d') if end_date else None
            start_str = start_date.strftime('%Y-%m-%d') if start_date else "2020-01-01"
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_str, end=end_str)
            
            if hist.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return pd.Series(dtype=float)
            
            prices = hist['Close']
            prices.index = pd.to_datetime(prices.index)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error downloading prices for {symbol}: {e}")
            raise BenchmarkDataUnavailableError(
                f"Failed to download prices for {symbol}. Real benchmark data required."
            )
    
    
    async def get_benchmark_composition(self, symbol: str) -> Dict[str, float]:
        """Get benchmark composition (constituent weights)"""
        
        try:
            # Check cache first
            if self.config.cache_data and symbol in self._composition_cache:
                cached_data, cache_time = self._composition_cache[symbol]
                if datetime.now() - cache_time < self.config.max_cache_age:
                    return cached_data
            
            # For major indices, use predefined compositions
            composition = self._get_predefined_composition(symbol)
            
            if not composition:
                # Require real composition data - FAIL FAST if unavailable
                raise BenchmarkDataUnavailableError(
                    f"No composition data available for {symbol}. Real benchmark composition required."
                )
            
            # Cache the composition
            if self.config.cache_data:
                self._composition_cache[symbol] = (composition, datetime.now())
            
            logger.debug(f"Retrieved composition with {len(composition)} constituents for {symbol}")
            
            return composition
            
        except Exception as e:
            logger.error(f"Error getting benchmark composition for {symbol}: {e}")
            return {}
    
    def _get_predefined_composition(self, symbol: str) -> Dict[str, float]:
        """Get predefined composition for major indices"""
        
        # Sample compositions for major indices (simplified)
        compositions = {
            'SPY': {
                'AAPL': 0.065, 'MSFT': 0.055, 'AMZN': 0.030, 'GOOGL': 0.025,
                'TSLA': 0.020, 'META': 0.018, 'NVDA': 0.015, 'JPM': 0.012,
                'JNJ': 0.011, 'V': 0.010
            },
            'QQQ': {
                'AAPL': 0.120, 'MSFT': 0.100, 'AMZN': 0.055, 'GOOGL': 0.045,
                'TSLA': 0.040, 'META': 0.035, 'NVDA': 0.030, 'NFLX': 0.025,
                'ADBE': 0.020, 'INTC': 0.018
            },
            'IWM': {
                'AMC': 0.008, 'GME': 0.007, 'SIRI': 0.006, 'PLUG': 0.005,
                'FUBO': 0.004, 'CLOV': 0.004, 'WISH': 0.003, 'SENS': 0.003,
                'TLRY': 0.003, 'SNDL': 0.002
            }
        }
        
        return compositions.get(symbol, {})
    


class RelativePerformanceCalculator:
    """Calculate relative performance metrics"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        
        logger.info("Relative performance calculator initialized")
    
    def calculate_relative_metrics(self, portfolio_returns: pd.Series,
                                 benchmark_returns: pd.Series) -> RelativePerformanceMetrics:
        """Calculate comprehensive relative performance metrics"""
        
        try:
            metrics = RelativePerformanceMetrics()
            
            # Align time series
            aligned_portfolio, aligned_benchmark = portfolio_returns.align(benchmark_returns, join='inner')
            
            if len(aligned_portfolio) < self.config.min_tracking_periods:
                logger.warning(f"Insufficient data for relative performance calculation "
                             f"(need {self.config.min_tracking_periods}, got {len(aligned_portfolio)})")
                return metrics
            
            # Basic relative metrics
            excess_returns = aligned_portfolio - aligned_benchmark
            metrics.excess_return = excess_returns.mean()
            metrics.active_return = metrics.excess_return
            
            # Tracking error
            metrics.tracking_error = excess_returns.std()
            
            # Information ratio
            if metrics.tracking_error != 0:
                metrics.information_ratio = metrics.excess_return / metrics.tracking_error
                
                # Annualize
                if self.config.data_frequency == "daily":
                    metrics.information_ratio *= np.sqrt(self.config.business_days_per_year)
                elif self.config.data_frequency == "weekly":
                    metrics.information_ratio *= np.sqrt(52)
                elif self.config.data_frequency == "monthly":
                    metrics.information_ratio *= np.sqrt(12)
            
            # Beta and alpha
            metrics.beta, metrics.alpha, metrics.r_squared = self._calculate_alpha_beta(
                aligned_portfolio, aligned_benchmark
            )
            
            # Volatility metrics
            metrics.relative_volatility = aligned_portfolio.std() / aligned_benchmark.std()
            
            # Downside metrics
            metrics.downside_deviation = self._calculate_downside_deviation(excess_returns)
            metrics.downside_beta = self._calculate_downside_beta(aligned_portfolio, aligned_benchmark)
            
            # Capture ratios
            metrics.upside_capture, metrics.downside_capture = self._calculate_capture_ratios(
                aligned_portfolio, aligned_benchmark
            )
            
            # Risk metrics
            metrics.relative_var = self._calculate_relative_var(excess_returns)
            metrics.relative_cvar = self._calculate_relative_cvar(excess_returns)
            metrics.maximum_adverse_excursion = excess_returns.min()
            
            # Timing metrics
            metrics.correlation = aligned_portfolio.corr(aligned_benchmark)
            metrics.hit_rate = (excess_returns > 0).mean()
            
            # Dates
            metrics.start_date = aligned_portfolio.index[0]
            metrics.end_date = aligned_portfolio.index[-1]
            
            logger.debug(f"Calculated relative performance metrics: IR={metrics.information_ratio:.3f}, "
                        f"TE={metrics.tracking_error:.3f}, Hit Rate={metrics.hit_rate:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating relative performance metrics: {e}")
            return RelativePerformanceMetrics()
    
    def _calculate_alpha_beta(self, portfolio_returns: pd.Series,
                            benchmark_returns: pd.Series) -> Tuple[float, float, float]:
        """Calculate alpha, beta, and R-squared"""
        
        try:
            # Remove any NaN values
            valid_data = pd.DataFrame({'portfolio': portfolio_returns, 'benchmark': benchmark_returns}).dropna()
            
            if len(valid_data) < self.config.min_tracking_periods:
                return 0.0, 0.0, 0.0
            
            portfolio_clean = valid_data['portfolio']
            benchmark_clean = valid_data['benchmark']
            
            # Calculate beta
            covariance = portfolio_clean.cov(benchmark_clean)
            benchmark_variance = benchmark_clean.var()
            
            if benchmark_variance == 0:
                return 0.0, 0.0, 0.0
            
            beta = covariance / benchmark_variance
            
            # Calculate alpha
            portfolio_mean = portfolio_clean.mean()
            benchmark_mean = benchmark_clean.mean()
            risk_free_daily = self.config.risk_free_rate / self.config.business_days_per_year
            
            alpha = portfolio_mean - risk_free_daily - beta * (benchmark_mean - risk_free_daily)
            
            # Annualize alpha
            if self.config.data_frequency == "daily":
                alpha *= self.config.business_days_per_year
            elif self.config.data_frequency == "weekly":
                alpha *= 52
            elif self.config.data_frequency == "monthly":
                alpha *= 12
            
            # Calculate R-squared
            correlation = portfolio_clean.corr(benchmark_clean)
            r_squared = correlation ** 2 if not pd.isna(correlation) else 0.0
            
            return alpha, beta, r_squared
            
        except Exception as e:
            logger.error(f"Error calculating alpha/beta: {e}")
            return 0.0, 0.0, 0.0
    
    def _calculate_downside_deviation(self, excess_returns: pd.Series) -> float:
        """Calculate downside deviation of excess returns"""
        
        try:
            negative_excess = excess_returns[excess_returns < 0]
            if len(negative_excess) == 0:
                return 0.0
            
            downside_dev = negative_excess.std()
            return downside_dev
            
        except Exception as e:
            logger.error(f"Error calculating downside deviation: {e}")
            return 0.0
    
    def _calculate_downside_beta(self, portfolio_returns: pd.Series,
                               benchmark_returns: pd.Series) -> float:
        """Calculate downside beta"""
        
        try:
            # Align and clean data
            valid_data = pd.DataFrame({'portfolio': portfolio_returns, 'benchmark': benchmark_returns}).dropna()
            
            if len(valid_data) < self.config.min_tracking_periods:
                return 0.0
            
            portfolio_clean = valid_data['portfolio']
            benchmark_clean = valid_data['benchmark']
            
            # Consider only periods when benchmark had negative returns
            down_periods = benchmark_clean < 0
            
            if down_periods.sum() < 5:  # Need minimum periods
                return 0.0
            
            portfolio_down = portfolio_clean[down_periods]
            benchmark_down = benchmark_clean[down_periods]
            
            # Calculate downside beta
            covariance = portfolio_down.cov(benchmark_down)
            benchmark_variance = benchmark_down.var()
            
            if benchmark_variance == 0:
                return 0.0
            
            downside_beta = covariance / benchmark_variance
            return downside_beta
            
        except Exception as e:
            logger.error(f"Error calculating downside beta: {e}")
            return 0.0
    
    def _calculate_capture_ratios(self, portfolio_returns: pd.Series,
                                benchmark_returns: pd.Series) -> Tuple[float, float]:
        """Calculate upside and downside capture ratios"""
        
        try:
            # Align and clean data
            valid_data = pd.DataFrame({'portfolio': portfolio_returns, 'benchmark': benchmark_returns}).dropna()
            
            if len(valid_data) < self.config.min_tracking_periods:
                return 0.0, 0.0
            
            portfolio_clean = valid_data['portfolio']
            benchmark_clean = valid_data['benchmark']
            
            # Upside capture (benchmark positive periods)
            up_periods = benchmark_clean > 0
            if up_periods.sum() > 0:
                portfolio_up_avg = portfolio_clean[up_periods].mean()
                benchmark_up_avg = benchmark_clean[up_periods].mean()
                upside_capture = portfolio_up_avg / benchmark_up_avg if benchmark_up_avg != 0 else 0.0
            else:
                upside_capture = 0.0
            
            # Downside capture (benchmark negative periods)
            down_periods = benchmark_clean < 0
            if down_periods.sum() > 0:
                portfolio_down_avg = portfolio_clean[down_periods].mean()
                benchmark_down_avg = benchmark_clean[down_periods].mean()
                downside_capture = portfolio_down_avg / benchmark_down_avg if benchmark_down_avg != 0 else 0.0
            else:
                downside_capture = 0.0
            
            return upside_capture, downside_capture
            
        except Exception as e:
            logger.error(f"Error calculating capture ratios: {e}")
            return 0.0, 0.0
    
    def _calculate_relative_var(self, excess_returns: pd.Series) -> float:
        """Calculate relative Value at Risk"""
        
        try:
            if len(excess_returns) == 0:
                return 0.0
            
            alpha = 1 - self.config.confidence_level
            relative_var = excess_returns.quantile(alpha)
            
            return relative_var
            
        except Exception as e:
            logger.error(f"Error calculating relative VaR: {e}")
            return 0.0
    
    def _calculate_relative_cvar(self, excess_returns: pd.Series) -> float:
        """Calculate relative Conditional Value at Risk"""
        
        try:
            if len(excess_returns) == 0:
                return 0.0
            
            relative_var = self._calculate_relative_var(excess_returns)
            tail_returns = excess_returns[excess_returns <= relative_var]
            
            if len(tail_returns) == 0:
                return relative_var
            
            relative_cvar = tail_returns.mean()
            return relative_cvar
            
        except Exception as e:
            logger.error(f"Error calculating relative CVaR: {e}")
            return 0.0


class BenchmarkTracker:
    """
    Comprehensive Benchmark Tracker
    
    Tracks and analyzes performance relative to various benchmarks,
    provides detailed relative performance metrics and attribution.
    """
    
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """Initialize benchmark tracker"""
        
        self.config = config or BenchmarkConfig()
        
        # Core components
        self._data_provider = BenchmarkDataProvider(self.config)
        self._performance_calculator = RelativePerformanceCalculator(self.config)
        
        # Benchmark storage
        self._benchmarks: Dict[str, BenchmarkData] = {}
        self._primary_benchmark: Optional[str] = None
        
        # Performance history
        self._performance_history: Dict[str, List[RelativePerformanceMetrics]] = defaultdict(list)
        
        # Real-time tracking
        self._tracking_active: bool = False
        self._last_update: Dict[str, datetime] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Benchmark tracker initialized")
    
    async def add_benchmark(self, symbol: str, name: Optional[str] = None,
                          benchmark_type: BenchmarkType = BenchmarkType.MARKET_INDEX,
                          set_as_primary: bool = False) -> bool:
        """Add benchmark for tracking"""
        
        try:
            with self._lock:
                # Get benchmark data
                prices = await self._data_provider.get_benchmark_prices(symbol)
                
                if prices.empty:
                    logger.error(f"Failed to get data for benchmark {symbol}")
                    return False
                
                # Calculate returns
                returns = prices.pct_change().dropna()
                
                # Get composition if available
                composition = await self._data_provider.get_benchmark_composition(symbol)
                
                # Create benchmark data
                benchmark_data = BenchmarkData(
                    symbol=symbol,
                    name=name or symbol,
                    benchmark_type=benchmark_type,
                    prices=prices,
                    returns=returns,
                    constituents=composition,
                    inception_date=prices.index[0],
                    last_rebalance=datetime.now()
                )
                
                # Calculate basic performance metrics
                self._update_benchmark_metrics(benchmark_data)
                
                # Store benchmark
                self._benchmarks[symbol] = benchmark_data
                
                # Set as primary if requested or if first benchmark
                if set_as_primary or not self._primary_benchmark:
                    self._primary_benchmark = symbol
                
                logger.info(f"Added benchmark {symbol} ({name or symbol})")
                
                return True
                
        except Exception as e:
            logger.error(f"Error adding benchmark {symbol}: {e}")
            return False
    
    def _update_benchmark_metrics(self, benchmark_data: BenchmarkData) -> None:
        """Update benchmark performance metrics"""
        
        try:
            returns = benchmark_data.returns
            
            if len(returns) == 0:
                return
            
            # Total return
            benchmark_data.total_return = (1 + returns).prod() - 1
            
            # Annualized return
            years = len(returns) / self.config.business_days_per_year
            if years > 0:
                benchmark_data.annualized_return = (1 + benchmark_data.total_return) ** (1 / years) - 1
            
            # Volatility
            benchmark_data.volatility = returns.std() * np.sqrt(self.config.business_days_per_year)
            
            # Max drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            benchmark_data.max_drawdown = drawdown.min()
            
        except Exception as e:
            logger.error(f"Error updating benchmark metrics: {e}")
    
    async def calculate_relative_performance(self, portfolio_returns: Union[pd.Series, List[float]],
                                           benchmark_symbol: Optional[str] = None) -> RelativePerformanceMetrics:
        """Calculate relative performance against benchmark"""
        
        try:
            # Convert portfolio returns to Series if needed
            if isinstance(portfolio_returns, list):
                portfolio_returns = pd.Series(portfolio_returns)
            
            # Use primary benchmark if not specified
            if benchmark_symbol is None:
                benchmark_symbol = self._primary_benchmark
            
            if benchmark_symbol is None or benchmark_symbol not in self._benchmarks:
                logger.error("No valid benchmark available for relative performance calculation")
                return RelativePerformanceMetrics()
            
            # Get benchmark data
            benchmark_data = self._benchmarks[benchmark_symbol]
            benchmark_returns = benchmark_data.returns
            
            # Calculate relative performance
            metrics = self._performance_calculator.calculate_relative_metrics(
                portfolio_returns, benchmark_returns
            )
            
            # Store in history
            with self._lock:
                self._performance_history[benchmark_symbol].append(metrics)
            
            logger.info(f"Calculated relative performance vs {benchmark_symbol}: "
                       f"IR={metrics.information_ratio:.3f}, TE={metrics.tracking_error:.3f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating relative performance: {e}")
            return RelativePerformanceMetrics()
    
    async def track_multiple_benchmarks(self, portfolio_returns: Union[pd.Series, List[float]],
                                      benchmark_symbols: Optional[List[str]] = None) -> Dict[str, RelativePerformanceMetrics]:
        """Track performance against multiple benchmarks"""
        
        try:
            if benchmark_symbols is None:
                benchmark_symbols = list(self._benchmarks.keys())
            
            results = {}
            
            for symbol in benchmark_symbols:
                if symbol in self._benchmarks:
                    metrics = await self.calculate_relative_performance(portfolio_returns, symbol)
                    results[symbol] = metrics
            
            logger.info(f"Tracked performance against {len(results)} benchmarks")
            
            return results
            
        except Exception as e:
            logger.error(f"Error tracking multiple benchmarks: {e}")
            return {}
    
    def get_benchmark_data(self, symbol: str) -> Optional[BenchmarkData]:
        """Get benchmark data"""
        
        with self._lock:
            return self._benchmarks.get(symbol)
    
    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """List all tracked benchmarks"""
        
        with self._lock:
            benchmark_list = []
            
            for symbol, data in self._benchmarks.items():
                benchmark_info = {
                    'symbol': symbol,
                    'name': data.name,
                    'type': data.benchmark_type.value,
                    'inception_date': data.inception_date,
                    'total_return': data.total_return,
                    'annualized_return': data.annualized_return,
                    'volatility': data.volatility,
                    'max_drawdown': data.max_drawdown,
                    'constituents_count': len(data.constituents),
                    'is_primary': symbol == self._primary_benchmark
                }
                benchmark_list.append(benchmark_info)
            
            return benchmark_list
    
    def set_primary_benchmark(self, symbol: str) -> bool:
        """Set primary benchmark"""
        
        with self._lock:
            if symbol in self._benchmarks:
                self._primary_benchmark = symbol
                logger.info(f"Set {symbol} as primary benchmark")
                return True
            else:
                logger.error(f"Benchmark {symbol} not found")
                return False
    
    async def update_benchmark_data(self, symbol: Optional[str] = None) -> bool:
        """Update benchmark data"""
        
        try:
            symbols_to_update = [symbol] if symbol else list(self._benchmarks.keys())
            
            for sym in symbols_to_update:
                if sym not in self._benchmarks:
                    continue
                
                # Get fresh data
                prices = await self._data_provider.get_benchmark_prices(sym)
                
                if not prices.empty:
                    # Update benchmark data
                    benchmark_data = self._benchmarks[sym]
                    benchmark_data.prices = prices
                    benchmark_data.returns = prices.pct_change().dropna()
                    
                    # Update metrics
                    self._update_benchmark_metrics(benchmark_data)
                    
                    # Update timestamp
                    self._last_update[sym] = datetime.now()
                    
                    logger.debug(f"Updated data for benchmark {sym}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating benchmark data: {e}")
            return False
    
    def remove_benchmark(self, symbol: str) -> bool:
        """Remove benchmark"""
        
        try:
            with self._lock:
                if symbol not in self._benchmarks:
                    logger.warning(f"Benchmark {symbol} not found")
                    return False
                
                # Remove benchmark data
                del self._benchmarks[symbol]
                
                # Remove performance history
                if symbol in self._performance_history:
                    del self._performance_history[symbol]
                
                # Update primary benchmark if needed
                if self._primary_benchmark == symbol:
                    self._primary_benchmark = next(iter(self._benchmarks), None)
                
                logger.info(f"Removed benchmark {symbol}")
                
                return True
                
        except Exception as e:
            logger.error(f"Error removing benchmark {symbol}: {e}")
            return False
    
    def get_relative_performance_history(self, benchmark_symbol: str,
                                       start_date: Optional[datetime] = None,
                                       end_date: Optional[datetime] = None) -> List[RelativePerformanceMetrics]:
        """Get relative performance history"""
        
        with self._lock:
            history = self._performance_history.get(benchmark_symbol, [])
            
            if not history:
                return []
            
            # Filter by date if specified
            filtered_history = []
            for metrics in history:
                if start_date and metrics.calculation_time < start_date:
                    continue
                if end_date and metrics.calculation_time > end_date:
                    continue
                filtered_history.append(metrics)
            
            return filtered_history
    
    def get_tracking_summary(self) -> Dict[str, Any]:
        """Get tracking summary"""
        
        with self._lock:
            summary = {
                'total_benchmarks': len(self._benchmarks),
                'primary_benchmark': self._primary_benchmark,
                'last_updates': self._last_update.copy(),
                'benchmarks': {},
                'config': {
                    'data_frequency': self.config.data_frequency,
                    'tracking_method': self.config.tracking_method.value,
                    'min_tracking_periods': self.config.min_tracking_periods,
                    'confidence_level': self.config.confidence_level
                }
            }
            
            # Add benchmark summaries
            for symbol, data in self._benchmarks.items():
                recent_performance = []
                if symbol in self._performance_history:
                    recent_performance = self._performance_history[symbol][-5:]  # Last 5 calculations
                
                summary['benchmarks'][symbol] = {
                    'name': data.name,
                    'type': data.benchmark_type.value,
                    'total_return': data.total_return,
                    'volatility': data.volatility,
                    'max_drawdown': data.max_drawdown,
                    'recent_calculations': len(recent_performance),
                    'avg_information_ratio': np.mean([m.information_ratio for m in recent_performance]) if recent_performance else 0.0,
                    'avg_tracking_error': np.mean([m.tracking_error for m in recent_performance]) if recent_performance else 0.0
                }
            
            return summary
    
    def export_relative_performance(self, benchmark_symbol: str,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export relative performance data to DataFrame"""
        
        try:
            history = self.get_relative_performance_history(benchmark_symbol, start_date, end_date)
            
            if not history:
                return pd.DataFrame()
            
            # Convert to DataFrame
            export_data = []
            for metrics in history:
                row = {
                    'calculation_time': metrics.calculation_time,
                    'excess_return': metrics.excess_return,
                    'tracking_error': metrics.tracking_error,
                    'information_ratio': metrics.information_ratio,
                    'alpha': metrics.alpha,
                    'beta': metrics.beta,
                    'r_squared': metrics.r_squared,
                    'correlation': metrics.correlation,
                    'hit_rate': metrics.hit_rate,
                    'upside_capture': metrics.upside_capture,
                    'downside_capture': metrics.downside_capture,
                    'relative_var': metrics.relative_var,
                    'start_date': metrics.start_date,
                    'end_date': metrics.end_date
                }
                export_data.append(row)
            
            df = pd.DataFrame(export_data)
            df.set_index('calculation_time', inplace=True)
            
            logger.info(f"Exported {len(df)} relative performance records for {benchmark_symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error exporting relative performance data: {e}")
            return pd.DataFrame()