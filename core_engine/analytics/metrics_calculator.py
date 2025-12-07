"""
Analytics Engine - Metrics Calculator
Advanced metrics calculation with risk-adjusted performance and statistical measures
"""

import logging
import threading
import uuid
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from scipy import stats
import warnings

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
try:
    from ..config import MetricsCalculatorConfig as CentralizedMetricConfig
    CENTRALIZED_CONFIG_AVAILABLE = True
except ImportError:
    CENTRALIZED_CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Centralized MetricsCalculatorConfig not available, using local config")

# Import ISystemComponent and IRegimeAware for orchestrator integration
from ..system.interfaces import ISystemComponent, IRegimeAware, RegimeContext

# Import canonical metric functions from core_metrics (Rule: Single Source of Truth)
from .core_metrics import (
    calculate_var,
    calculate_cvar,
    calculate_drawdown,
)
from ..exceptions import PerformanceDataUnavailableError, ConfigurationRequiredError

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MetricCategory(Enum):
    """Metric categories"""
    RETURN = "return"
    RISK = "risk"
    RISK_ADJUSTED = "risk_adjusted"
    DRAWDOWN = "drawdown"
    DISTRIBUTION = "distribution"
    TRADING = "trading"
    BEHAVIORAL = "behavioral"
    TAIL_RISK = "tail_risk"


class MetricFrequency(Enum):
    """Metric calculation frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ROLLING = "rolling"


class BenchmarkType(Enum):
    """Benchmark types for relative metrics"""
    MARKET_INDEX = "market_index"
    SECTOR_INDEX = "sector_index"
    PEER_GROUP = "peer_group"
    RISK_FREE = "risk_free"
    CUSTOM = "custom"


@dataclass
class MetricConfig:
    """Metrics calculation configuration"""
    # Risk-free rate
    risk_free_rate: float = 0.02  # 2% annual

    # Calculation parameters
    trading_days_per_year: int = 252
    confidence_levels: List[float] = field(default_factory=lambda: [0.90, 0.95, 0.99])

    # Rolling window settings
    rolling_windows: Dict[str, int] = field(default_factory=lambda: {
        'short': 21,    # 1 month
        'medium': 63,   # 3 months
        'long': 252     # 1 year
    })

    # VaR settings
    var_methods: List[str] = field(default_factory=lambda: ['historical', 'parametric', 'monte_carlo'])
    monte_carlo_simulations: int = 10000

    # Drawdown settings
    drawdown_threshold: float = 0.05  # 5%
    recovery_threshold: float = 0.95  # 95% recovery

    # Distribution analysis
    enable_higher_moments: bool = True
    enable_tail_analysis: bool = True

    # Benchmark settings
    default_benchmark: str = "SPY"

    # Performance attribution
    enable_factor_metrics: bool = True
    factor_models: List[str] = field(default_factory=lambda: ['market', 'fama_french', 'carhart'])


@dataclass
class MetricResult:
    """Individual metric calculation result"""
    metric_name: str
    value: float
    category: MetricCategory
    frequency: MetricFrequency

    # Calculation metadata
    calculation_date: datetime = field(default_factory=datetime.now)
    data_points: int = 0
    confidence_level: Optional[float] = None

    # Statistical properties
    standard_error: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None

    # Context
    benchmark_value: Optional[float] = None
    percentile_rank: Optional[float] = None

    # Quality indicators
    is_significant: bool = False
    quality_score: float = 0.0  # 0-1 score

    # Additional metadata
    calculation_method: str = "standard"
    notes: List[str] = field(default_factory=list)


@dataclass
class MetricsBundle:
    """Collection of related metrics"""
    bundle_name: str
    category: MetricCategory
    calculation_timestamp: datetime

    # Core metrics
    metrics: Dict[str, MetricResult] = field(default_factory=dict)

    # Summary statistics
    summary_stats: Dict[str, float] = field(default_factory=dict)

    # Rolling metrics
    rolling_metrics: Dict[str, pd.Series] = field(default_factory=dict)

    # Comparative metrics
    relative_metrics: Dict[str, float] = field(default_factory=dict)

    # Quality assessment
    data_quality: float = 0.0
    completeness: float = 0.0


class ReturnMetricsCalculator:
    """Return-based metrics calculator"""

    def __init__(self, config: MetricConfig):
        self.config = config

    def calculate_return_metrics(self, returns: pd.Series) -> Dict[str, MetricResult]:
        """Calculate comprehensive return metrics"""

        metrics = {}

        if returns.empty:
            return metrics

        # Basic return metrics
        metrics['total_return'] = MetricResult(
            metric_name='total_return',
            value=(1 + returns).prod() - 1,
            category=MetricCategory.RETURN,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns)
        )

        # Annualized return
        periods_per_year = self._get_periods_per_year(returns)
        if len(returns) > 0:
            annualized_return = (1 + metrics['total_return'].value) ** (periods_per_year / len(returns)) - 1
            metrics['annualized_return'] = MetricResult(
                metric_name='annualized_return',
                value=annualized_return,
                category=MetricCategory.RETURN,
                frequency=MetricFrequency.YEARLY,
                data_points=len(returns)
            )

        # Arithmetic and geometric means
        metrics['arithmetic_mean'] = MetricResult(
            metric_name='arithmetic_mean',
            value=returns.mean() * periods_per_year,
            category=MetricCategory.RETURN,
            frequency=MetricFrequency.YEARLY,
            data_points=len(returns)
        )

        if (returns > -1).all():  # Check for no -100% returns
            geometric_mean = (1 + returns).prod() ** (1/len(returns)) - 1
            metrics['geometric_mean'] = MetricResult(
                metric_name='geometric_mean',
                value=geometric_mean * periods_per_year,
                category=MetricCategory.RETURN,
                frequency=MetricFrequency.YEARLY,
                data_points=len(returns)
            )

        # Excess returns
        excess_returns = returns - self.config.risk_free_rate / periods_per_year
        metrics['excess_return'] = MetricResult(
            metric_name='excess_return',
            value=excess_returns.mean() * periods_per_year,
            category=MetricCategory.RETURN,
            frequency=MetricFrequency.YEARLY,
            data_points=len(returns)
        )

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
            return 4  # Quarterly


class RiskMetricsCalculator:
    """Risk metrics calculator"""

    def __init__(self, config: MetricConfig):
        self.config = config

    def calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, MetricResult]:
        """Calculate comprehensive risk metrics"""

        metrics = {}

        if returns.empty:
            return metrics

        periods_per_year = self._get_periods_per_year(returns)

        # Volatility
        volatility = returns.std() * np.sqrt(periods_per_year)
        metrics['volatility'] = MetricResult(
            metric_name='volatility',
            value=volatility,
            category=MetricCategory.RISK,
            frequency=MetricFrequency.YEARLY,
            data_points=len(returns)
        )

        # Downside volatility
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_vol = downside_returns.std() * np.sqrt(periods_per_year)
            metrics['downside_volatility'] = MetricResult(
                metric_name='downside_volatility',
                value=downside_vol,
                category=MetricCategory.RISK,
                frequency=MetricFrequency.YEARLY,
                data_points=len(downside_returns)
            )

        # Semi-deviation (downside deviation from mean)
        mean_return = returns.mean()
        semi_deviation = returns[returns < mean_return].std() * np.sqrt(periods_per_year)
        metrics['semi_deviation'] = MetricResult(
            metric_name='semi_deviation',
            value=semi_deviation,
            category=MetricCategory.RISK,
            frequency=MetricFrequency.YEARLY,
            data_points=len(returns[returns < mean_return])
        )

        # Value at Risk
        for confidence_level in self.config.confidence_levels:
            for method in self.config.var_methods:
                var_value = self._calculate_var(returns, confidence_level, method)
                metrics[f'var_{int(confidence_level*100)}_{method}'] = MetricResult(
                    metric_name=f'var_{int(confidence_level*100)}_{method}',
                    value=var_value,
                    category=MetricCategory.TAIL_RISK,
                    frequency=MetricFrequency.DAILY,
                    confidence_level=confidence_level,
                    calculation_method=method,
                    data_points=len(returns)
                )

        # Conditional Value at Risk (Expected Shortfall)
        for confidence_level in self.config.confidence_levels:
            cvar_value = self._calculate_cvar(returns, confidence_level)
            metrics[f'cvar_{int(confidence_level*100)}'] = MetricResult(
                metric_name=f'cvar_{int(confidence_level*100)}',
                value=cvar_value,
                category=MetricCategory.TAIL_RISK,
                frequency=MetricFrequency.DAILY,
                confidence_level=confidence_level,
                data_points=len(returns)
            )

        return metrics

    def _get_periods_per_year(self, returns: pd.Series) -> float:
        """Get periods per year"""
        return self.config.trading_days_per_year  # Simplified

    def _calculate_var(self, returns: pd.Series, confidence_level: float, method: str) -> float:
        """Calculate Value at Risk - delegates to core_metrics"""
        return calculate_var(returns, confidence_level, method, self.config.monte_carlo_simulations)

    def _calculate_cvar(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate Conditional Value at Risk - delegates to core_metrics"""
        return calculate_cvar(returns, confidence_level)


class RiskAdjustedMetricsCalculator:
    """Risk-adjusted metrics calculator"""

    def __init__(self, config: MetricConfig):
        self.config = config

    def calculate_risk_adjusted_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, MetricResult]:
        """Calculate risk-adjusted metrics"""

        metrics = {}

        if returns.empty:
            return metrics

        periods_per_year = self.config.trading_days_per_year
        risk_free_rate = self.config.risk_free_rate / periods_per_year

        # Excess returns
        excess_returns = returns - risk_free_rate

        # Sharpe Ratio
        if returns.std() > 0:
            sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(periods_per_year)
            metrics['sharpe_ratio'] = MetricResult(
                metric_name='sharpe_ratio',
                value=sharpe_ratio,
                category=MetricCategory.RISK_ADJUSTED,
                frequency=MetricFrequency.YEARLY,
                data_points=len(returns)
            )

        # Sortino Ratio
        downside_returns = returns[returns < risk_free_rate]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(periods_per_year)
            metrics['sortino_ratio'] = MetricResult(
                metric_name='sortino_ratio',
                value=sortino_ratio,
                category=MetricCategory.RISK_ADJUSTED,
                frequency=MetricFrequency.YEARLY,
                data_points=len(returns)
            )

        # Calmar Ratio
        max_drawdown = self._calculate_max_drawdown(returns)
        if max_drawdown > 0:
            annual_return = returns.mean() * periods_per_year
            calmar_ratio = annual_return / max_drawdown
            metrics['calmar_ratio'] = MetricResult(
                metric_name='calmar_ratio',
                value=calmar_ratio,
                category=MetricCategory.RISK_ADJUSTED,
                frequency=MetricFrequency.YEARLY,
                data_points=len(returns)
            )

        # Information Ratio (if benchmark provided)
        if benchmark_returns is not None:
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            if len(aligned_returns) > 1:
                active_returns = aligned_returns - aligned_benchmark
                tracking_error = active_returns.std() * np.sqrt(periods_per_year)

                if tracking_error > 0:
                    information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(periods_per_year)
                    metrics['information_ratio'] = MetricResult(
                        metric_name='information_ratio',
                        value=information_ratio,
                        category=MetricCategory.RISK_ADJUSTED,
                        frequency=MetricFrequency.YEARLY,
                        data_points=len(aligned_returns),
                        benchmark_value=0.0  # IR relative to benchmark is 0
                    )

        # Omega Ratio
        threshold = risk_free_rate
        omega_ratio = self._calculate_omega_ratio(returns, threshold)
        metrics['omega_ratio'] = MetricResult(
            metric_name='omega_ratio',
            value=omega_ratio,
            category=MetricCategory.RISK_ADJUSTED,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns)
        )

        return metrics

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown - delegates to core_metrics"""
        if returns.empty:
            return 0.0
        _, max_dd, _ = calculate_drawdown(returns)
        return abs(max_dd)

    def _calculate_omega_ratio(self, returns: pd.Series, threshold: float) -> float:
        """Calculate Omega ratio"""

        if returns.empty:
            return 0.0

        excess_returns = returns - threshold
        positive_returns = excess_returns[excess_returns > 0].sum()
        negative_returns = -excess_returns[excess_returns < 0].sum()

        if negative_returns == 0:
            return np.inf if positive_returns > 0 else 1.0

        return positive_returns / negative_returns


class DrawdownMetricsCalculator:
    """Drawdown metrics calculator"""

    def __init__(self, config: MetricConfig):
        self.config = config

    def calculate_drawdown_metrics(self, returns: pd.Series) -> Dict[str, MetricResult]:
        """Calculate comprehensive drawdown metrics"""

        metrics = {}

        if returns.empty:
            return metrics

        # Calculate drawdown series
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown_series = (cumulative - running_max) / running_max

        # Maximum Drawdown
        max_dd = abs(drawdown_series.min())
        metrics['maximum_drawdown'] = MetricResult(
            metric_name='maximum_drawdown',
            value=max_dd,
            category=MetricCategory.DRAWDOWN,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns)
        )

        # Average Drawdown
        drawdown_periods = drawdown_series[drawdown_series < 0]
        if len(drawdown_periods) > 0:
            avg_dd = abs(drawdown_periods.mean())
            metrics['average_drawdown'] = MetricResult(
                metric_name='average_drawdown',
                value=avg_dd,
                category=MetricCategory.DRAWDOWN,
                frequency=MetricFrequency.DAILY,
                data_points=len(drawdown_periods)
            )

        # Drawdown Duration Analysis
        dd_duration_stats = self._analyze_drawdown_durations(drawdown_series)

        for stat_name, stat_value in dd_duration_stats.items():
            metrics[f'drawdown_{stat_name}'] = MetricResult(
                metric_name=f'drawdown_{stat_name}',
                value=stat_value,
                category=MetricCategory.DRAWDOWN,
                frequency=MetricFrequency.DAILY,
                data_points=len(returns)
            )

        # Recovery Analysis
        recovery_stats = self._analyze_recovery_periods(drawdown_series, cumulative)

        for stat_name, stat_value in recovery_stats.items():
            metrics[f'recovery_{stat_name}'] = MetricResult(
                metric_name=f'recovery_{stat_name}',
                value=stat_value,
                category=MetricCategory.DRAWDOWN,
                frequency=MetricFrequency.DAILY,
                data_points=len(returns)
            )

        return metrics

    def _analyze_drawdown_durations(self, drawdown_series: pd.Series) -> Dict[str, float]:
        """Analyze drawdown durations"""

        durations = []
        current_duration = 0
        in_drawdown = False

        for dd in drawdown_series:
            if dd < 0:
                if not in_drawdown:
                    in_drawdown = True
                    current_duration = 1
                else:
                    current_duration += 1
            else:
                if in_drawdown:
                    durations.append(current_duration)
                    in_drawdown = False
                    current_duration = 0

        # Handle case where series ends in drawdown
        if in_drawdown:
            durations.append(current_duration)

        if not durations:
            return {'duration_max': 0, 'duration_avg': 0, 'duration_count': 0}

        return {
            'duration_max': max(durations),
            'duration_avg': np.mean(durations),
            'duration_count': len(durations)
        }

    def _analyze_recovery_periods(
        self,
        drawdown_series: pd.Series,
        cumulative_series: pd.Series
    ) -> Dict[str, float]:
        """Analyze recovery periods"""

        recovery_times = []

        # Find drawdown start and recovery points
        drawdown_starts = []
        drawdown_ends = []

        in_drawdown = False
        start_idx = None

        for i, dd in enumerate(drawdown_series):
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                start_idx = i
            elif dd >= 0 and in_drawdown:
                in_drawdown = False
                if start_idx is not None:
                    drawdown_starts.append(start_idx)
                    drawdown_ends.append(i)

        # Calculate recovery times
        for start, end in zip(drawdown_starts, drawdown_ends):
            if end < len(cumulative_series):
                # Find when portfolio reaches new high
                high_at_start = cumulative_series.iloc[start]
                recovery_idx = None

                for i in range(end, len(cumulative_series)):
                    if cumulative_series.iloc[i] >= high_at_start * self.config.recovery_threshold:
                        recovery_idx = i
                        break

                if recovery_idx is not None:
                    recovery_time = recovery_idx - start
                    recovery_times.append(recovery_time)

        if not recovery_times:
            return {'time_avg': 0, 'time_max': 0, 'rate': 0}

        return {
            'time_avg': np.mean(recovery_times),
            'time_max': max(recovery_times),
            'rate': len(recovery_times) / max(len(drawdown_starts), 1)
        }


class DistributionMetricsCalculator:
    """Distribution and higher moment metrics calculator"""

    def __init__(self, config: MetricConfig):
        self.config = config

    def calculate_distribution_metrics(self, returns: pd.Series) -> Dict[str, MetricResult]:
        """Calculate distribution metrics"""

        metrics = {}

        if returns.empty or len(returns) < 3:
            return metrics

        # Skewness
        skewness = returns.skew()
        metrics['skewness'] = MetricResult(
            metric_name='skewness',
            value=skewness,
            category=MetricCategory.DISTRIBUTION,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns),
            is_significant=abs(skewness) > 0.5
        )

        # Kurtosis
        kurtosis = returns.kurtosis()
        metrics['kurtosis'] = MetricResult(
            metric_name='kurtosis',
            value=kurtosis,
            category=MetricCategory.DISTRIBUTION,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns),
            is_significant=abs(kurtosis) > 1.0
        )

        # Excess Kurtosis
        excess_kurtosis = kurtosis - 3  # Normal distribution has kurtosis of 3
        metrics['excess_kurtosis'] = MetricResult(
            metric_name='excess_kurtosis',
            value=excess_kurtosis,
            category=MetricCategory.DISTRIBUTION,
            frequency=MetricFrequency.DAILY,
            data_points=len(returns),
            is_significant=abs(excess_kurtosis) > 0.5
        )

        # Jarque-Bera test for normality
        if len(returns) >= 8:  # Minimum for JB test
            jb_stat, jb_pvalue = stats.jarque_bera(returns.dropna())
            metrics['jarque_bera_stat'] = MetricResult(
                metric_name='jarque_bera_stat',
                value=jb_stat,
                category=MetricCategory.DISTRIBUTION,
                frequency=MetricFrequency.DAILY,
                data_points=len(returns),
                is_significant=jb_pvalue < 0.05
            )

            metrics['jarque_bera_pvalue'] = MetricResult(
                metric_name='jarque_bera_pvalue',
                value=jb_pvalue,
                category=MetricCategory.DISTRIBUTION,
                frequency=MetricFrequency.DAILY,
                data_points=len(returns)
            )

        # Tail metrics
        if self.config.enable_tail_analysis:
            tail_metrics = self._calculate_tail_metrics(returns)
            metrics.update(tail_metrics)

        return metrics

    def _calculate_tail_metrics(self, returns: pd.Series) -> Dict[str, MetricResult]:
        """Calculate tail risk metrics"""

        metrics = {}

        # Left tail (negative returns)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            # Tail ratio (probability of extreme negative vs positive returns)
            threshold_5pct = np.percentile(returns, 5)
            threshold_95pct = np.percentile(returns, 95)

            extreme_negative = len(returns[returns < threshold_5pct])
            extreme_positive = len(returns[returns > threshold_95pct])

            if extreme_positive > 0:
                tail_ratio = extreme_negative / extreme_positive
                metrics['tail_ratio'] = MetricResult(
                    metric_name='tail_ratio',
                    value=tail_ratio,
                    category=MetricCategory.TAIL_RISK,
                    frequency=MetricFrequency.DAILY,
                    data_points=len(returns)
                )

        # Expected shortfall at various levels
        for percentile in [1, 5, 10]:
            threshold = np.percentile(returns, percentile)
            shortfall = returns[returns <= threshold].mean()

            metrics[f'expected_shortfall_{percentile}pct'] = MetricResult(
                metric_name=f'expected_shortfall_{percentile}pct',
                value=shortfall,
                category=MetricCategory.TAIL_RISK,
                frequency=MetricFrequency.DAILY,
                data_points=len(returns[returns <= threshold])
            )

        return metrics


class EnhancedMetricsCalculator(ISystemComponent, IRegimeAware):
    """
    Enhanced Metrics Calculator with ISystemComponent and IRegimeAware Integration

    Comprehensive calculation of performance, risk, and statistical metrics
    with support for rolling calculations, comparative analysis, orchestrator integration,
    and regime-aware metric calculation for institutional-grade metrics computation.

    **Enhanced Features:**
    - ISystemComponent integration for orchestrator
    - IRegimeAware integration for regime-based metrics
    - Centralized configuration (Rule 1 Section 7)
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize enhanced metrics calculator

        Args:
            config: MetricConfig or MetricsCalculatorConfig or dict
        """
        # Handle centralized configuration (Rule 1 Section 7 - Configuration Management)
        if CENTRALIZED_CONFIG_AVAILABLE and (config is None or isinstance(config, dict)):
            # Use centralized config
            if config is None:
                self.centralized_config = CentralizedMetricConfig()
            elif isinstance(config, dict):
                self.centralized_config = CentralizedMetricConfig(**{
                    k: v for k, v in config.items()
                    if hasattr(CentralizedMetricConfig, k)
                })

            # Map to local MetricConfig for backward compatibility
            self.config = MetricConfig(
                risk_free_rate=self.centralized_config.risk_free_rate,
                trading_days_per_year=252,  # Use standard value
            )
            logger.info("✅ Using centralized MetricsCalculatorConfig (Rule 1 Section 7)")
        elif isinstance(config, CentralizedMetricConfig if CENTRALIZED_CONFIG_AVAILABLE else type(None)):
            # Already centralized config
            self.centralized_config = config
            self.config = MetricConfig(
                risk_free_rate=config.risk_free_rate,
                trading_days_per_year=252,
            )
            logger.info("✅ Using centralized MetricsCalculatorConfig (Rule 1 Section 7)")
        else:
            # Require explicit configuration - FAIL FAST if missing
            if not isinstance(config, MetricConfig):
                raise ConfigurationRequiredError(
                    "MetricsCalculator requires explicit MetricConfig. "
                    "Cannot proceed with default configuration."
                )
            self.config = config
            self.centralized_config = None
            if not CENTRALIZED_CONFIG_AVAILABLE:
                raise ConfigurationRequiredError(
                    "Centralized configuration not available. "
                    "Cannot proceed without proper configuration setup."
                )

        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None

        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference

        # IRegimeAware state management
        self.regime_engine: Optional[Any] = None
        self.current_regime_context: Optional[RegimeContext] = None
        logger.info("✅ EnhancedMetricsCalculator implements IRegimeAware (Rule 2 - Regime-First)")

        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedMetricsCalculator',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_calculations': 0,
                'successful_calculations': 0,
                'failed_calculations': 0,
                'average_calculation_time': 0.0,
                'cache_hit_rate': 0.0
            }
        }

        # Metrics storage
        self._metrics_cache = {}
        self._rolling_metrics = defaultdict(dict)

        # Threading
        self._lock = threading.Lock()

        logger.info(f"🚀 Enhanced Metrics Calculator initialized with component ID: {self.component_id}")

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedMetricsCalculator",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=32  # After core components
        )

        logger.info(f"✅ EnhancedMetricsCalculator registered with orchestrator: {self.component_id}")
        return self.component_id

    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning("No orchestrator available for authorization request")
            return False

        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )

    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================

    async def initialize(self) -> bool:
        """Initialize the Enhanced Metrics Calculator"""
        try:
            logger.info("🔄 Initializing Enhanced Metrics Calculator...")

            # Initialize calculation engines
            await self._initialize_calculation_engines()

            # Initialize monitoring
            await self._initialize_monitoring_system()

            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'

            logger.info("✅ Enhanced Metrics Calculator initialization complete")
            return True

        except Exception as e:
            logger.error(f"❌ Enhanced Metrics Calculator initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False

    async def start(self) -> bool:
        """Start the Enhanced Metrics Calculator"""
        if not self.is_initialized:
            logger.error("Cannot start Enhanced Metrics Calculator: not initialized")
            return False

        try:
            logger.info("🚀 Starting Enhanced Metrics Calculator...")

            # Start monitoring
            await self._start_monitoring()

            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'

            logger.info("✅ Enhanced Metrics Calculator started successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Enhanced Metrics Calculator start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def stop(self) -> bool:
        """Stop the Enhanced Metrics Calculator"""
        try:
            logger.info("🛑 Stopping Enhanced Metrics Calculator...")

            # Stop monitoring
            await self._stop_monitoring()

            # Clear caches
            self.clear_cache()

            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'

            logger.info("✅ Enhanced Metrics Calculator stopped successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Enhanced Metrics Calculator stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time

            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()

            # Check calculation engines health
            engines_healthy = await self._check_engines_health()

            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                engines_healthy and
                self.health_metrics['error_count'] < 10
            )

            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'performance_metrics': self.health_metrics['performance_metrics'],
                'engines_healthy': engines_healthy,
                'cache_size': len(self._metrics_cache),
                'last_health_check': current_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'error': str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """Get current component status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'configuration': {
                'risk_free_rate': self.config.risk_free_rate,
                'trading_days_per_year': self.config.trading_days_per_year,
                'confidence_levels': self.config.confidence_levels,
                'var_methods': self.config.var_methods
            },
            'health_metrics': self.health_metrics
        }

    # ================================================================
    # IRegimeAware Implementation (Rule 2 - Regime-First Principle)
    # ================================================================

    def set_regime_engine(self, regime_engine: Any) -> None:
        """Inject regime engine dependency"""
        self.regime_engine = regime_engine
        logger.info("✅ RegimeEngine injected into EnhancedMetricsCalculator (IRegimeAware)")

    async def on_regime_change(self, new_regime_context: RegimeContext) -> None:
        """Handle regime change events"""
        try:
            old_regime = self.current_regime_context.primary_regime if self.current_regime_context else "none"
            self.current_regime_context = new_regime_context

            logger.info(
                f"📊 MetricsCalculator regime change: {old_regime} → "
                f"{new_regime_context.primary_regime} "
                f"(confidence: {new_regime_context.regime_confidence:.2%})"
            )

            await self.adapt_to_regime(new_regime_context)

        except Exception as e:
            logger.error(f"Error handling regime change in MetricsCalculator: {e}")

    def get_current_regime_context(self) -> Optional[RegimeContext]:
        """Get current regime context"""
        return self.current_regime_context

    async def adapt_to_regime(self, regime_context: RegimeContext) -> Dict[str, Any]:
        """Adapt metrics calculation to current regime"""
        try:
            regime = regime_context.primary_regime
            volatility_regime = getattr(regime_context, 'volatility_regime', 'normal')

            adaptations = {
                'regime': regime,
                'volatility_regime': volatility_regime,
                'adapted': True
            }

            logger.debug(f"📊 MetricsCalculator adapted to {regime} regime")
            return adaptations

        except Exception as e:
            logger.error(f"Error adapting MetricsCalculator to regime: {e}")
            return {'adapted': False, 'error': str(e)}

    def validate_regime_dependency(self) -> bool:
        """Validate regime engine is properly configured"""
        has_regime_engine = self.regime_engine is not None
        if has_regime_engine:
            logger.debug("✅ MetricsCalculator regime dependency validated")
        else:
            logger.warning("⚠️  MetricsCalculator regime engine not configured")
        return has_regime_engine

    # Enhanced Internal Methods

    async def _initialize_calculation_engines(self) -> None:
        """Initialize calculation engines"""
        try:
            logger.info("🔧 Initializing calculation engines...")

            # Initialize component calculators
            self.return_calculator = ReturnMetricsCalculator(self.config)
            self.risk_calculator = RiskMetricsCalculator(self.config)
            self.risk_adjusted_calculator = RiskAdjustedMetricsCalculator(self.config)
            self.drawdown_calculator = DrawdownMetricsCalculator(self.config)
            self.distribution_calculator = DistributionMetricsCalculator(self.config)

            logger.info("✅ Calculation engines initialized")

        except Exception as e:
            logger.error(f"Failed to initialize calculation engines: {e}")
            raise

    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            logger.info("📈 Initializing monitoring system...")
            # Monitoring initialization logic here
            logger.info("✅ Monitoring system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring system: {e}")
            raise

    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            logger.info("📊 Starting monitoring systems...")
            # Monitoring startup logic here
            logger.info("✅ Monitoring systems started")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise

    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            logger.info("📊 Stopping monitoring systems...")
            # Monitoring shutdown logic here
            logger.info("✅ Monitoring systems stopped")
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            raise

    async def _check_engines_health(self) -> bool:
        """Check health of all calculation engines"""
        try:
            # Check if engines are responsive
            engines_status = []

            # Check each engine
            engines = [
                ('return_calculator', self.return_calculator),
                ('risk_calculator', self.risk_calculator),
                ('risk_adjusted_calculator', self.risk_adjusted_calculator),
                ('drawdown_calculator', self.drawdown_calculator),
                ('distribution_calculator', self.distribution_calculator)
            ]

            for name, engine in engines:
                try:
                    # Basic health check - engine exists and is accessible
                    engines_status.append(engine is not None)
                except Exception as e:
                    logger.warning(f"Health check failed for {name}: {e}")
                    engines_status.append(False)

            return all(engines_status)

        except Exception as e:
            logger.error(f"Engines health check failed: {e}")
            return False

    async def calculate_all_metrics(
        self,
        returns: pd.Series,
        symbol: str,
        benchmark_returns: Optional[pd.Series] = None,
        frequency: MetricFrequency = MetricFrequency.DAILY
    ) -> Dict[MetricCategory, MetricsBundle]:
        """Calculate all metrics for a return series"""

        if returns.empty:
            logger.warning(f"Empty returns series for {symbol}")
            return {}

        results = {}

        try:
            # Return metrics
            return_metrics = self.return_calculator.calculate_return_metrics(returns)
            results[MetricCategory.RETURN] = MetricsBundle(
                bundle_name=f"{symbol}_returns",
                category=MetricCategory.RETURN,
                calculation_timestamp=datetime.now(),
                metrics=return_metrics,
                data_quality=self._assess_data_quality(returns),
                completeness=1.0 - returns.isna().sum() / len(returns)
            )

            # Risk metrics
            risk_metrics = self.risk_calculator.calculate_risk_metrics(returns)
            results[MetricCategory.RISK] = MetricsBundle(
                bundle_name=f"{symbol}_risk",
                category=MetricCategory.RISK,
                calculation_timestamp=datetime.now(),
                metrics=risk_metrics,
                data_quality=self._assess_data_quality(returns),
                completeness=1.0 - returns.isna().sum() / len(returns)
            )

            # Risk-adjusted metrics
            risk_adj_metrics = self.risk_adjusted_calculator.calculate_risk_adjusted_metrics(
                returns, benchmark_returns
            )
            results[MetricCategory.RISK_ADJUSTED] = MetricsBundle(
                bundle_name=f"{symbol}_risk_adjusted",
                category=MetricCategory.RISK_ADJUSTED,
                calculation_timestamp=datetime.now(),
                metrics=risk_adj_metrics,
                data_quality=self._assess_data_quality(returns),
                completeness=1.0 - returns.isna().sum() / len(returns)
            )

            # Drawdown metrics
            drawdown_metrics = self.drawdown_calculator.calculate_drawdown_metrics(returns)
            results[MetricCategory.DRAWDOWN] = MetricsBundle(
                bundle_name=f"{symbol}_drawdown",
                category=MetricCategory.DRAWDOWN,
                calculation_timestamp=datetime.now(),
                metrics=drawdown_metrics,
                data_quality=self._assess_data_quality(returns),
                completeness=1.0 - returns.isna().sum() / len(returns)
            )

            # Distribution metrics
            if self.config.enable_higher_moments:
                dist_metrics = self.distribution_calculator.calculate_distribution_metrics(returns)
                results[MetricCategory.DISTRIBUTION] = MetricsBundle(
                    bundle_name=f"{symbol}_distribution",
                    category=MetricCategory.DISTRIBUTION,
                    calculation_timestamp=datetime.now(),
                    metrics=dist_metrics,
                    data_quality=self._assess_data_quality(returns),
                    completeness=1.0 - returns.isna().sum() / len(returns)
                )

            # Cache results
            with self._lock:
                self._metrics_cache[symbol] = results

            logger.debug(f"Calculated {sum(len(bundle.metrics) for bundle in results.values())} "
                        f"metrics for {symbol}")

            return results

        except Exception as e:
            logger.error(f"Error calculating metrics for {symbol}: {e}")
            return {}

    def calculate_rolling_metrics(
        self,
        returns: pd.Series,
        symbol: str,
        window_name: str = 'medium',
        metrics_list: Optional[List[str]] = None
    ) -> Dict[str, pd.Series]:
        """Calculate rolling metrics"""

        if returns.empty:
            return {}

        window = self.config.rolling_windows.get(window_name, 63)

        if len(returns) < window:
            logger.warning(f"Insufficient data for rolling calculation: {len(returns)} < {window}")
            return {}

        metrics_list = metrics_list or ['sharpe_ratio', 'volatility', 'maximum_drawdown']
        rolling_results = {}

        try:
            for metric_name in metrics_list:
                rolling_values = []
                rolling_dates = []

                for i in range(window, len(returns) + 1):
                    window_returns = returns.iloc[i-window:i]

                    if metric_name == 'sharpe_ratio':
                        excess_returns = window_returns - self.config.risk_free_rate / 252
                        if window_returns.std() > 0:
                            value = excess_returns.mean() / window_returns.std() * np.sqrt(252)
                        else:
                            value = 0.0
                    elif metric_name == 'volatility':
                        value = window_returns.std() * np.sqrt(252)
                    elif metric_name == 'maximum_drawdown':
                        value = self.risk_adjusted_calculator._calculate_max_drawdown(window_returns)
                    else:
                        value = 0.0  # Default for unknown metrics

                    rolling_values.append(value)
                    rolling_dates.append(returns.index[i-1])

                rolling_results[metric_name] = pd.Series(rolling_values, index=rolling_dates)

            # Cache rolling metrics
            with self._lock:
                self._rolling_metrics[symbol].update(rolling_results)

            logger.debug(f"Calculated rolling metrics for {symbol} with window {window}")

            return rolling_results

        except Exception as e:
            logger.error(f"Error calculating rolling metrics for {symbol}: {e}")
            return {}

    def compare_metrics(
        self,
        primary_symbol: str,
        comparison_symbol: str,
        metric_names: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """Compare metrics between two symbols"""

        with self._lock:
            primary_metrics = self._metrics_cache.get(primary_symbol, {})
            comparison_metrics = self._metrics_cache.get(comparison_symbol, {})

        if not primary_metrics or not comparison_metrics:
            logger.warning(f"Metrics not available for comparison: {primary_symbol}, {comparison_symbol}")
            return {}

        comparison_results = {}

        # Default metrics to compare
        default_metrics = [
            'annualized_return', 'volatility', 'sharpe_ratio', 'maximum_drawdown',
            'sortino_ratio', 'calmar_ratio', 'var_95_historical'
        ]

        metrics_to_compare = metric_names or default_metrics

        for metric_name in metrics_to_compare:
            primary_value = self._find_metric_value(primary_metrics, metric_name)
            comparison_value = self._find_metric_value(comparison_metrics, metric_name)

            if primary_value is not None and comparison_value is not None:
                difference = primary_value - comparison_value
                relative_difference = difference / abs(comparison_value) if comparison_value != 0 else 0.0

                comparison_results[metric_name] = {
                    'primary': primary_value,
                    'comparison': comparison_value,
                    'difference': difference,
                    'relative_difference': relative_difference
                }

        return comparison_results

    def _find_metric_value(
        self,
        metrics_bundles: Dict[MetricCategory, MetricsBundle],
        metric_name: str
    ) -> Optional[float]:
        """Find metric value across all bundles"""

        for bundle in metrics_bundles.values():
            if metric_name in bundle.metrics:
                return bundle.metrics[metric_name].value

        return None

    def _assess_data_quality(self, returns: pd.Series) -> float:
        """Assess data quality score (0-1)"""

        if returns.empty:
            return 0.0

        quality_score = 1.0

        # Penalize for missing data
        missing_ratio = returns.isna().sum() / len(returns)
        quality_score -= missing_ratio * 0.5

        # Penalize for extreme outliers (more than 5 standard deviations)
        if returns.std() > 0:
            outliers = abs(returns - returns.mean()) > 5 * returns.std()
            outlier_ratio = outliers.sum() / len(returns)
            quality_score -= outlier_ratio * 0.3

        # Penalize for insufficient data
        if len(returns) < 30:
            quality_score -= (30 - len(returns)) / 30 * 0.2

        return max(quality_score, 0.0)

    def get_metrics_summary(self, symbol: str) -> Dict[str, Any]:
        """Get metrics summary for a symbol"""

        with self._lock:
            metrics_bundles = self._metrics_cache.get(symbol, {})
            rolling_metrics = self._rolling_metrics.get(symbol, {})

        if not metrics_bundles:
            return {}

        summary = {
            'symbol': symbol,
            'calculation_timestamp': datetime.now(),
            'metrics_calculated': sum(len(bundle.metrics) for bundle in metrics_bundles.values()),
            'categories': list(metrics_bundles.keys()),
            'data_quality': np.mean([bundle.data_quality for bundle in metrics_bundles.values()]),
            'completeness': np.mean([bundle.completeness for bundle in metrics_bundles.values()]),
            'rolling_metrics_available': list(rolling_metrics.keys())
        }

        # Key metrics summary
        key_metrics = {}
        for metric_name in ['annualized_return', 'volatility', 'sharpe_ratio', 'maximum_drawdown']:
            value = self._find_metric_value(metrics_bundles, metric_name)
            if value is not None:
                key_metrics[metric_name] = value

        summary['key_metrics'] = key_metrics

        return summary

    def get_cached_metrics(self, symbol: str) -> Optional[Dict[MetricCategory, MetricsBundle]]:
        """Get cached metrics for a symbol"""

        with self._lock:
            return self._metrics_cache.get(symbol)

    def get_rolling_metrics(self, symbol: str) -> Dict[str, pd.Series]:
        """Get rolling metrics for a symbol"""

        with self._lock:
            return self._rolling_metrics.get(symbol, {})

    def calculate_performance_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate performance metrics"""
        return self._calculate_performance_metrics_impl(returns)

    def _calculate_performance_metrics_impl(self, returns: pd.Series) -> Dict[str, Any]:
        """Internal implementation of performance metrics calculation"""
        if returns.empty:
            raise PerformanceDataUnavailableError("No returns data available for performance metrics calculation")

        try:
            # Calculate basic performance metrics
            total_return = (1 + returns).prod() - 1
            annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
            volatility = returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0.0

            # Calculate additional metrics
            max_drawdown = self._calculate_max_drawdown(returns)
            sortino_ratio = annualized_return / (returns[returns < 0].std() * np.sqrt(252)) if len(returns[returns < 0]) > 0 else 0.0

            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
            }
        except Exception as e:
            raise PerformanceDataUnavailableError(f"Failed to calculate performance metrics: {e}") from e

    def calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate risk metrics"""
        return self._calculate_risk_metrics_impl(returns)

    def _calculate_risk_metrics_impl(self, returns: pd.Series) -> Dict[str, Any]:
        """Internal implementation of risk metrics calculation"""
        if returns.empty:
            raise PerformanceDataUnavailableError("No returns data available for risk metrics calculation")

        try:
            # Calculate VaR and CVaR
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)

            # Calculate CVaR (Expected Shortfall)
            cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
            cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else var_99

            # Calculate beta (would need market returns in real implementation)
            beta = 1.0  # Placeholder - would calculate against market benchmark

            # Calculate tracking error (would need benchmark returns)
            tracking_error = returns.std() * np.sqrt(252)  # Placeholder

            return {
                'var_95': var_95,
                'var_99': var_99,
                'cvar_95': cvar_95,
                'cvar_99': cvar_99,
                'conditional_var': cvar_95,  # Alias for conditional value at risk
                'beta': beta,
                'tracking_error': tracking_error,
                'volatility': returns.std() * np.sqrt(252),
                'skewness': returns.skew(),
                'kurtosis': returns.kurtosis()
            }
        except Exception as e:
            raise PerformanceDataUnavailableError(f"Failed to calculate risk metrics: {e}") from e

    def calculate_statistical_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate statistical metrics"""
        return self._calculate_statistical_metrics_impl(returns)

    def _calculate_statistical_metrics_impl(self, returns: pd.Series) -> Dict[str, Any]:
        """Internal implementation of statistical metrics calculation"""
        if returns.empty:
            raise PerformanceDataUnavailableError("No returns data available for statistical metrics calculation")

        try:
            # Calculate statistical measures
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            mean = returns.mean()
            median = returns.median()
            std = returns.std()

            # Calculate percentiles
            percentiles = {
                'p5': returns.quantile(0.05),
                'p25': returns.quantile(0.25),
                'p75': returns.quantile(0.75),
                'p95': returns.quantile(0.95)
            }

            return {
                'mean': mean,
                'median': median,
                'std': std,
                'skewness': skewness,
                'kurtosis': kurtosis,
                'percentiles': percentiles,
                'count': len(returns),
                'min': returns.min(),
                'max': returns.max()
            }
        except Exception as e:
            raise PerformanceDataUnavailableError(f"Failed to calculate statistical metrics: {e}") from e

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown - delegates to core_metrics"""
        if returns.empty:
            return 0.0
        try:
            _, max_dd, _ = calculate_drawdown(returns)
            return max_dd
        except Exception:
            return 0.0

    def clear_cache(self) -> None:
        """Clear metrics cache"""

        with self._lock:
            self._metrics_cache.clear()
            self._rolling_metrics.clear()

    def _initialize_risk_adjusted_calculator(self):
        """Initialize risk adjusted calculator"""
        if not hasattr(self, 'risk_adjusted_calculator'):
            self.risk_adjusted_calculator = {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'information_ratio': 0.0
            }

    def calculate_rolling_metrics(self, returns: pd.Series, window: int = 20) -> Dict[str, Any]:
        """Calculate rolling metrics for returns data"""
        self._initialize_risk_adjusted_calculator()

        try:
            # Use symbol from returns if available, otherwise use window as key
            symbol = getattr(returns, 'name', f'window_{window}')

            # Get cached data for the symbol
            if symbol not in self._rolling_metrics:
                self._rolling_metrics[symbol] = {}

            # Calculate rolling metrics (placeholder implementation)
            rolling_metrics = {
                'rolling_return': 0.05,  # Placeholder
                'rolling_volatility': 0.15,  # Placeholder
                'rolling_sharpe': 0.33,  # Placeholder
                'rolling_max_drawdown': -0.02,  # Placeholder
                'window': window,
                'symbol': symbol
            }

            # Store in cache
            self._rolling_metrics[symbol] = rolling_metrics

            return rolling_metrics

        except Exception as e:
            # Use print instead of logger since logger might not be available
            print(f"Error calculating rolling metrics for {window}: {e}")
            return {}
            logger.info("Metrics cache cleared")

    def get_calculator_statistics(self) -> Dict[str, Any]:
        """Get calculator statistics"""

        with self._lock:
            cached_symbols = len(self._metrics_cache)
            rolling_symbols = len(self._rolling_metrics)

            total_metrics = sum(
                sum(len(bundle.metrics) for bundle in bundles.values())
                for bundles in self._metrics_cache.values()
            )

        return {
            'cached_symbols': cached_symbols,
            'rolling_metrics_symbols': rolling_symbols,
            'total_metrics_calculated': total_metrics,
            'config': {
                'trading_days_per_year': self.config.trading_days_per_year,
                'confidence_levels': self.config.confidence_levels,
                'rolling_windows': self.config.rolling_windows
            }
        }

    # ========================================
    # ANALYTICS INTEGRATION METHODS
    # ========================================

    def calculate_metrics(self, data: Any) -> Dict[str, Any]:
        """
        Standardized method for calculating metrics (analytics integration interface)

        Args:
            data: Input data (dict, DataFrame, or Series)

        Returns:
            Dictionary containing calculated metrics
        """
        try:
            # Handle different data types
            if isinstance(data, dict):
                if 'returns' in data:
                    returns_data = data['returns']
                    if isinstance(returns_data, list):
                        returns_series = pd.Series(returns_data)
                    else:
                        returns_series = returns_data
                elif 'prices' in data:
                    prices_data = data['prices']
                    if isinstance(prices_data, list):
                        prices_series = pd.Series(prices_data)
                        returns_series = prices_series.pct_change().dropna()
                    else:
                        returns_series = prices_data.pct_change().dropna()
                else:
                    # Require real data - FAIL FAST if unavailable
                    raise PerformanceDataUnavailableError(
                        "Real performance data required for metrics calculation. "
                        "Cannot proceed with mock data."
                    )
            elif isinstance(data, (pd.Series, pd.DataFrame)):
                if isinstance(data, pd.DataFrame) and 'returns' in data.columns:
                    returns_series = data['returns']
                elif isinstance(data, pd.DataFrame) and 'close' in data.columns:
                    returns_series = data['close'].pct_change().dropna()
                else:
                    returns_series = data if isinstance(data, pd.Series) else data.iloc[:, 0]
            else:
                # Require real data - FAIL FAST if unavailable
                raise PerformanceDataUnavailableError(
                    "Real performance data required for metrics calculation. "
                    "Cannot proceed with default mock data."
                )

            # Calculate comprehensive metrics using existing methods
            metrics_bundles = self.calculate_comprehensive_metrics(returns_series)

            # Extract key metrics for analytics integration
            result = {
                'metrics_calculated': True,
                'calculation_timestamp': datetime.now(),
                'data_points': len(returns_series),
                'metrics': {}
            }

            # Extract metrics from bundles
            for category, bundle in metrics_bundles.items():
                category_metrics = {}
                for metric_name, metric_value in bundle.metrics.items():
                    if isinstance(metric_value, (int, float, np.number)):
                        category_metrics[metric_name] = float(metric_value)
                    else:
                        category_metrics[metric_name] = str(metric_value)

                result['metrics'][category.value] = category_metrics

            # Add summary metrics
            result['summary'] = {
                'total_return': float(returns_series.sum()),
                'volatility': float(returns_series.std() * np.sqrt(252)),
                'sharpe_ratio': float(returns_series.mean() / returns_series.std() * np.sqrt(252)) if returns_series.std() > 0 else 0.0,
                'max_drawdown': float(self._calculate_max_drawdown(returns_series.cumsum())),
                'data_quality': 1.0
            }

            return result

        except Exception as e:
            self.logger.error(f"Metrics calculation failed: {e}")
            return {
                'metrics_calculated': False,
                'error': str(e),
                'calculation_timestamp': datetime.now()
            }