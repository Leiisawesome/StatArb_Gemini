"""
Analytics Engine - Attribution Analyzer
Advanced performance attribution analysis with factor and sector decomposition
"""

import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.decomposition import PCA
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class AttributionMethod(Enum):
    """Attribution analysis methods"""
    BRINSON = "brinson"
    FACTOR_MODEL = "factor_model"
    RETURNS_BASED = "returns_based"
    HOLDINGS_BASED = "holdings_based"
    MULTI_FACTOR = "multi_factor"
    RISK_MODEL = "risk_model"


class AttributionType(Enum):
    """Types of attribution analysis"""
    SECTOR = "sector"
    FACTOR = "factor"
    SECURITY = "security"
    STYLE = "style"
    GEOGRAPHIC = "geographic"
    CURRENCY = "currency"
    ASSET_CLASS = "asset_class"


class PerformanceComponent(Enum):
    """Performance attribution components"""
    ALLOCATION = "allocation"
    SELECTION = "selection"
    INTERACTION = "interaction"
    CURRENCY = "currency"
    TIMING = "timing"
    TOTAL = "total"


@dataclass
class AttributionConfig:
    """Attribution analysis configuration"""
    # Analysis settings
    attribution_method: AttributionMethod = AttributionMethod.FACTOR_MODEL
    attribution_frequency: str = "daily"
    
    # Factor model settings
    factor_model_type: str = "fama_french"  # fama_french, carhart, custom
    lookback_period: int = 252  # Trading days
    
    # Risk model settings
    risk_model_factors: List[str] = field(default_factory=lambda: [
        "market", "size", "value", "momentum", "quality", "volatility"
    ])
    
    # Sector settings
    sector_classification: str = "gics"  # gics, industry, custom
    
    # Attribution components
    enable_allocation_effect: bool = True
    enable_selection_effect: bool = True
    enable_interaction_effect: bool = True
    enable_currency_effect: bool = False
    
    # Analysis parameters
    benchmark_symbol: str = "SPY"
    confidence_level: float = 0.95
    min_observations: int = 30
    
    # Factor exposure settings
    factor_exposure_method: str = "regression"  # regression, holdings
    rolling_window: int = 60  # Days for rolling attribution


@dataclass
class AttributionResult:
    """Attribution analysis result"""
    symbol: str
    analysis_date: datetime
    attribution_method: AttributionMethod
    attribution_type: AttributionType
    
    # Performance components
    total_return: float = 0.0
    benchmark_return: float = 0.0
    active_return: float = 0.0
    
    # Attribution effects
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    currency_effect: float = 0.0
    timing_effect: float = 0.0
    
    # Factor attribution
    factor_contributions: Dict[str, float] = field(default_factory=dict)
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    factor_returns: Dict[str, float] = field(default_factory=dict)
    
    # Sector attribution
    sector_contributions: Dict[str, float] = field(default_factory=dict)
    sector_weights_portfolio: Dict[str, float] = field(default_factory=dict)
    sector_weights_benchmark: Dict[str, float] = field(default_factory=dict)
    
    # Security attribution
    security_contributions: Dict[str, float] = field(default_factory=dict)
    security_weights: Dict[str, float] = field(default_factory=dict)
    security_returns: Dict[str, float] = field(default_factory=dict)
    
    # Risk attribution
    specific_return: float = 0.0
    systematic_return: float = 0.0
    
    # Quality metrics
    r_squared: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    
    # Metadata
    analysis_period: Tuple[datetime, datetime] = field(default_factory=lambda: (datetime.now(), datetime.now()))
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class AttributionReport:
    """Comprehensive attribution report"""
    portfolio_name: str
    report_id: str
    generation_timestamp: datetime
    
    # Analysis period
    start_date: datetime
    end_date: datetime
    
    # Overall attribution
    total_attribution: AttributionResult
    
    # Time series attribution
    daily_attribution: List[AttributionResult] = field(default_factory=list)
    monthly_attribution: List[AttributionResult] = field(default_factory=list)
    
    # Factor analysis
    factor_loadings: pd.DataFrame = field(default_factory=pd.DataFrame)
    factor_importance: Dict[str, float] = field(default_factory=dict)
    
    # Sector analysis
    sector_breakdown: pd.DataFrame = field(default_factory=pd.DataFrame)
    sector_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Risk decomposition
    risk_attribution: Dict[str, float] = field(default_factory=dict)
    
    # Performance summary
    cumulative_attribution: pd.Series = field(default_factory=pd.Series)
    rolling_attribution: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Charts data
    attribution_waterfall: Dict[str, float] = field(default_factory=dict)
    factor_contribution_chart: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Summary statistics
    attribution_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Quality indicators
    model_diagnostics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class FactorModelAnalyzer:
    """Factor model-based attribution analyzer"""
    
    def __init__(self, config: AttributionConfig):
        self.config = config
        self.factor_models = {}
        self.factor_data = {}
        self._lock = threading.Lock()
    
    def build_factor_model(
        self,
        returns: pd.Series,
        factor_returns: pd.DataFrame,
        method: str = "ols"
    ) -> Dict[str, Any]:
        """Build factor model for attribution"""
        
        try:
            # Align data
            aligned_data = pd.concat([returns, factor_returns], axis=1, join='inner').dropna()
            
            if len(aligned_data) < self.config.min_observations:
                raise ValueError(f"Insufficient data: {len(aligned_data)} < {self.config.min_observations}")
            
            y = aligned_data.iloc[:, 0].values  # Portfolio returns
            X = aligned_data.iloc[:, 1:].values  # Factor returns
            factor_names = aligned_data.columns[1:].tolist()
            
            # Fit regression model
            if method == "ols":
                model = LinearRegression(fit_intercept=True)
            elif method == "ridge":
                model = Ridge(alpha=0.1, fit_intercept=True)
            else:
                model = LinearRegression(fit_intercept=True)
            
            model.fit(X, y)
            
            # Calculate model statistics
            y_pred = model.predict(X)
            residuals = y - y_pred
            
            r_squared = model.score(X, y)
            residual_std = np.std(residuals)
            
            # Factor loadings and contributions
            factor_loadings = dict(zip(factor_names, model.coef_))
            alpha = model.intercept_
            
            # Calculate factor contributions
            factor_contributions = {}
            for i, factor_name in enumerate(factor_names):
                factor_contributions[factor_name] = factor_loadings[factor_name] * np.mean(X[:, i])
            
            # Model diagnostics
            diagnostics = {
                'r_squared': r_squared,
                'alpha': alpha,
                'residual_volatility': residual_std,
                'observations': len(aligned_data),
                'factor_significance': self._test_factor_significance(X, y, model.coef_)
            }
            
            return {
                'model': model,
                'factor_loadings': factor_loadings,
                'factor_contributions': factor_contributions,
                'alpha': alpha,
                'diagnostics': diagnostics,
                'residuals': residuals,
                'factor_names': factor_names
            }
            
        except Exception as e:
            logger.error(f"Error building factor model: {e}")
            return {}
    
    def _test_factor_significance(self, X: np.ndarray, y: np.ndarray, coefficients: np.ndarray) -> Dict[str, float]:
        """Test statistical significance of factor loadings"""
        
        try:
            # Calculate t-statistics (simplified)
            n, k = X.shape
            
            # Residual sum of squares
            y_pred = X @ coefficients + np.mean(y - X @ coefficients)
            residuals = y - y_pred
            rss = np.sum(residuals ** 2)
            
            # Standard errors
            mse = rss / (n - k - 1)
            var_cov = mse * np.linalg.inv(X.T @ X)
            std_errors = np.sqrt(np.diag(var_cov))
            
            # T-statistics
            t_stats = coefficients / std_errors
            
            # P-values (approximate)
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - k - 1))
            
            return {f'factor_{i}': p_val for i, p_val in enumerate(p_values)}
            
        except Exception as e:
            logger.warning(f"Error calculating factor significance: {e}")
            return {}
    
    def calculate_factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
        period_start: datetime,
        period_end: datetime
    ) -> AttributionResult:
        """Calculate factor-based attribution"""
        
        # Filter data by period
        period_portfolio = portfolio_returns[period_start:period_end]
        period_factors = factor_returns[period_start:period_end]
        
        # Build factor model
        model_result = self.build_factor_model(period_portfolio, period_factors)
        
        if not model_result:
            return AttributionResult(
                symbol="unknown",
                analysis_date=period_end,
                attribution_method=AttributionMethod.FACTOR_MODEL,
                attribution_type=AttributionType.FACTOR
            )
        
        # Calculate attribution
        result = AttributionResult(
            symbol=period_portfolio.name or "portfolio",
            analysis_date=period_end,
            attribution_method=AttributionMethod.FACTOR_MODEL,
            attribution_type=AttributionType.FACTOR,
            analysis_period=(period_start, period_end)
        )
        
        # Performance components
        result.total_return = (1 + period_portfolio).prod() - 1
        
        # Factor contributions
        result.factor_contributions = model_result['factor_contributions']
        result.factor_exposures = model_result['factor_loadings']
        
        # Risk decomposition
        systematic_contrib = sum(result.factor_contributions.values())
        result.systematic_return = systematic_contrib
        result.specific_return = result.total_return - systematic_contrib
        
        # Model quality
        result.r_squared = model_result['diagnostics']['r_squared']
        
        return result


class SectorAttributionAnalyzer:
    """Sector-based attribution analyzer"""
    
    def __init__(self, config: AttributionConfig):
        self.config = config
        self.sector_mappings = {}
        self._default_sectors = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'AMZN'],
            'Finance': ['JPM', 'BAC', 'WFC', 'GS'],
            'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV'],
            'Energy': ['XOM', 'CVX', 'COP', 'EOG'],
            'Industrials': ['BA', 'CAT', 'GE', 'MMM']
        }
    
    def calculate_sector_attribution(
        self,
        portfolio_weights: pd.Series,
        portfolio_returns: pd.Series,
        benchmark_weights: pd.Series,
        benchmark_returns: pd.Series,
        sector_mappings: Optional[Dict[str, str]] = None
    ) -> AttributionResult:
        """Calculate sector-based attribution using Brinson model"""
        
        sector_map = sector_mappings or self._create_default_sector_mapping(portfolio_weights.index)
        
        # Aggregate by sector
        portfolio_sector_weights = self._aggregate_by_sector(portfolio_weights, sector_map)
        benchmark_sector_weights = self._aggregate_by_sector(benchmark_weights, sector_map)
        
        portfolio_sector_returns = self._calculate_sector_returns(
            portfolio_returns, portfolio_weights, sector_map
        )
        benchmark_sector_returns = self._calculate_sector_returns(
            benchmark_returns, benchmark_weights, sector_map
        )
        
        # Brinson attribution
        attribution = self._brinson_attribution(
            portfolio_sector_weights,
            benchmark_sector_weights,
            portfolio_sector_returns,
            benchmark_sector_returns
        )
        
        result = AttributionResult(
            symbol="portfolio",
            analysis_date=datetime.now(),
            attribution_method=AttributionMethod.BRINSON,
            attribution_type=AttributionType.SECTOR
        )
        
        result.allocation_effect = attribution['allocation_effect']
        result.selection_effect = attribution['selection_effect']
        result.interaction_effect = attribution['interaction_effect']
        result.sector_contributions = attribution['sector_contributions']
        result.sector_weights_portfolio = portfolio_sector_weights
        result.sector_weights_benchmark = benchmark_sector_weights
        
        return result
    
    def _create_default_sector_mapping(self, symbols: List[str]) -> Dict[str, str]:
        """Create default sector mapping"""
        
        sector_mapping = {}
        
        for symbol in symbols:
            # Simple mapping based on predefined sectors
            sector_found = False
            for sector, sector_symbols in self._default_sectors.items():
                if symbol in sector_symbols:
                    sector_mapping[symbol] = sector
                    sector_found = True
                    break
            
            if not sector_found:
                sector_mapping[symbol] = 'Other'
        
        return sector_mapping
    
    def _aggregate_by_sector(self, weights: pd.Series, sector_map: Dict[str, str]) -> Dict[str, float]:
        """Aggregate weights by sector"""
        
        sector_weights = defaultdict(float)
        
        for symbol, weight in weights.items():
            sector = sector_map.get(symbol, 'Other')
            sector_weights[sector] += weight
        
        return dict(sector_weights)
    
    def _calculate_sector_returns(
        self,
        returns: pd.Series,
        weights: pd.Series,
        sector_map: Dict[str, str]
    ) -> Dict[str, float]:
        """Calculate sector returns"""
        
        sector_returns = defaultdict(float)
        sector_weights = defaultdict(float)
        
        for symbol in returns.index.intersection(weights.index):
            sector = sector_map.get(symbol, 'Other')
            weight = weights[symbol]
            
            sector_returns[sector] += weight * returns[symbol]
            sector_weights[sector] += weight
        
        # Normalize by sector weights
        for sector in sector_returns:
            if sector_weights[sector] > 0:
                sector_returns[sector] /= sector_weights[sector]
        
        return dict(sector_returns)
    
    def _brinson_attribution(
        self,
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
        portfolio_returns: Dict[str, float],
        benchmark_returns: Dict[str, float]
    ) -> Dict[str, Any]:
        """Perform Brinson attribution analysis"""
        
        all_sectors = set(portfolio_weights.keys()) | set(benchmark_weights.keys())
        
        allocation_effect = 0.0
        selection_effect = 0.0
        interaction_effect = 0.0
        sector_contributions = {}
        
        for sector in all_sectors:
            # Weights
            wp = portfolio_weights.get(sector, 0.0)  # Portfolio weight
            wb = benchmark_weights.get(sector, 0.0)   # Benchmark weight
            
            # Returns
            rp = portfolio_returns.get(sector, 0.0)   # Portfolio sector return
            rb = benchmark_returns.get(sector, 0.0)   # Benchmark sector return
            
            # Brinson effects
            allocation = (wp - wb) * rb
            selection = wb * (rp - rb)
            interaction = (wp - wb) * (rp - rb)
            
            allocation_effect += allocation
            selection_effect += selection
            interaction_effect += interaction
            
            sector_contributions[sector] = {
                'allocation': allocation,
                'selection': selection,
                'interaction': interaction,
                'total': allocation + selection + interaction
            }
        
        return {
            'allocation_effect': allocation_effect,
            'selection_effect': selection_effect,
            'interaction_effect': interaction_effect,
            'sector_contributions': sector_contributions
        }


class AttributionAnalyzer:
    """
    Advanced Attribution Analyzer
    
    Provides comprehensive performance attribution analysis including
    factor-based, sector-based, and security-level attribution.
    """
    
    def __init__(self, config: Optional[AttributionConfig] = None):
        """Initialize attribution analyzer"""
        self.config = config or AttributionConfig()
        
        # Component analyzers
        self.factor_analyzer = FactorModelAnalyzer(self.config)
        self.sector_analyzer = SectorAttributionAnalyzer(self.config)
        
        # Attribution history
        self._attribution_history = deque(maxlen=10000)
        self._factor_models = {}
        
        # Data storage
        self._benchmark_data = {}
        self._factor_data = {}
        self._sector_mappings = {}
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info("Attribution Analyzer initialized")
    
    async def analyze_attribution(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: Optional[pd.Series] = None,
        benchmark_returns: Optional[pd.Series] = None,
        factor_returns: Optional[pd.DataFrame] = None,
        attribution_type: AttributionType = AttributionType.FACTOR,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AttributionResult:
        """Perform attribution analysis"""
        
        # Date range handling
        if start_date:
            portfolio_returns = portfolio_returns[portfolio_returns.index >= start_date]
        if end_date:
            portfolio_returns = portfolio_returns[portfolio_returns.index <= end_date]
        
        period_start = portfolio_returns.index.min() if not portfolio_returns.empty else datetime.now()
        period_end = portfolio_returns.index.max() if not portfolio_returns.empty else datetime.now()
        
        try:
            if attribution_type == AttributionType.FACTOR:
                return await self._factor_attribution(
                    portfolio_returns, factor_returns, period_start, period_end
                )
            elif attribution_type == AttributionType.SECTOR:
                return await self._sector_attribution(
                    portfolio_returns, portfolio_weights, benchmark_returns, period_start, period_end
                )
            elif attribution_type == AttributionType.SECURITY:
                return await self._security_attribution(
                    portfolio_returns, portfolio_weights, period_start, period_end
                )
            else:
                # Default to factor attribution
                return await self._factor_attribution(
                    portfolio_returns, factor_returns, period_start, period_end
                )
                
        except Exception as e:
            logger.error(f"Error in attribution analysis: {e}")
            return AttributionResult(
                symbol="error",
                analysis_date=period_end,
                attribution_method=self.config.attribution_method,
                attribution_type=attribution_type,
                analysis_period=(period_start, period_end)
            )
    
    async def _factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: Optional[pd.DataFrame],
        period_start: datetime,
        period_end: datetime
    ) -> AttributionResult:
        """Perform factor-based attribution"""
        
        if factor_returns is None:
            factor_returns = await self._get_default_factor_returns(period_start, period_end)
        
        return self.factor_analyzer.calculate_factor_attribution(
            portfolio_returns, factor_returns, period_start, period_end
        )
    
    async def _sector_attribution(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: Optional[pd.Series],
        benchmark_returns: Optional[pd.Series],
        period_start: datetime,
        period_end: datetime
    ) -> AttributionResult:
        """Perform sector-based attribution"""
        
        # Use equal weights if not provided
        if portfolio_weights is None:
            portfolio_weights = pd.Series(
                1.0 / len(portfolio_returns),
                index=portfolio_returns.index
            )
        
        # Use default benchmark if not provided
        if benchmark_returns is None:
            benchmark_returns = await self._get_benchmark_returns(period_start, period_end)
        
        # Create benchmark weights (equal weighted)
        benchmark_weights = pd.Series(
            1.0 / len(benchmark_returns),
            index=benchmark_returns.index
        )
        
        return self.sector_analyzer.calculate_sector_attribution(
            portfolio_weights,
            portfolio_returns,
            benchmark_weights,
            benchmark_returns
        )
    
    async def _security_attribution(
        self,
        portfolio_returns: pd.Series,
        portfolio_weights: Optional[pd.Series],
        period_start: datetime,
        period_end: datetime
    ) -> AttributionResult:
        """Perform security-level attribution"""
        
        result = AttributionResult(
            symbol="portfolio",
            analysis_date=period_end,
            attribution_method=AttributionMethod.HOLDINGS_BASED,
            attribution_type=AttributionType.SECURITY,
            analysis_period=(period_start, period_end)
        )
        
        # Simple security contribution calculation
        if portfolio_weights is not None:
            security_contributions = {}
            
            for symbol in portfolio_returns.index:
                weight = portfolio_weights.get(symbol, 0.0)
                return_contrib = weight * portfolio_returns[symbol]
                security_contributions[symbol] = return_contrib
            
            result.security_contributions = security_contributions
            result.total_return = sum(security_contributions.values())
        
        return result
    
    async def _get_default_factor_returns(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Get default factor returns (simplified)"""
        
        # In a real implementation, this would fetch from a data source
        # For now, create synthetic factor returns
        
        date_range = pd.date_range(start_date, end_date, freq='D')
        
        # Create synthetic factor returns
        np.random.seed(42)  # For reproducibility
        
        factor_returns = pd.DataFrame({
            'market': np.random.normal(0.0005, 0.015, len(date_range)),
            'size': np.random.normal(0.0001, 0.008, len(date_range)),
            'value': np.random.normal(0.0002, 0.010, len(date_range)),
            'momentum': np.random.normal(0.0001, 0.012, len(date_range)),
            'quality': np.random.normal(0.0003, 0.007, len(date_range)),
            'volatility': np.random.normal(-0.0001, 0.009, len(date_range))
        }, index=date_range)
        
        return factor_returns
    
    async def _get_benchmark_returns(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.Series:
        """Get benchmark returns (simplified)"""
        
        # In a real implementation, this would fetch actual benchmark data
        date_range = pd.date_range(start_date, end_date, freq='D')
        
        # Create synthetic benchmark returns
        np.random.seed(42)
        benchmark_returns = pd.Series(
            np.random.normal(0.0008, 0.012, len(date_range)),
            index=date_range,
            name=self.config.benchmark_symbol
        )
        
        return benchmark_returns
    
    async def generate_attribution_report(
        self,
        portfolio_returns: pd.Series,
        portfolio_name: str,
        portfolio_weights: Optional[pd.Series] = None,
        benchmark_returns: Optional[pd.Series] = None,
        factor_returns: Optional[pd.DataFrame] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AttributionReport:
        """Generate comprehensive attribution report"""
        
        report_id = f"{portfolio_name}_attribution_{int(time.time())}"
        
        # Determine date range
        if not start_date:
            start_date = portfolio_returns.index.min() if not portfolio_returns.empty else datetime.now()
        if not end_date:
            end_date = portfolio_returns.index.max() if not portfolio_returns.empty else datetime.now()
        
        # Initialize report
        report = AttributionReport(
            portfolio_name=portfolio_name,
            report_id=report_id,
            generation_timestamp=datetime.now(),
            start_date=start_date,
            end_date=end_date
        )
        
        try:
            # Overall attribution analysis
            report.total_attribution = await self.analyze_attribution(
                portfolio_returns,
                portfolio_weights,
                benchmark_returns,
                factor_returns,
                AttributionType.FACTOR,
                start_date,
                end_date
            )
            
            # Monthly attribution
            monthly_dates = pd.date_range(start_date, end_date, freq='M')
            
            for i in range(len(monthly_dates)):
                month_start = monthly_dates[i].replace(day=1) if i == 0 else monthly_dates[i-1]
                month_end = monthly_dates[i]
                
                monthly_attr = await self.analyze_attribution(
                    portfolio_returns,
                    portfolio_weights,
                    benchmark_returns,
                    factor_returns,
                    AttributionType.FACTOR,
                    month_start,
                    month_end
                )
                
                report.monthly_attribution.append(monthly_attr)
            
            # Factor analysis
            if factor_returns is not None:
                report.factor_loadings = self._create_factor_loadings_table(
                    portfolio_returns, factor_returns
                )
                
                report.factor_importance = self._calculate_factor_importance(
                    report.total_attribution.factor_contributions
                )
            
            # Create attribution waterfall
            report.attribution_waterfall = self._create_attribution_waterfall(
                report.total_attribution
            )
            
            # Rolling attribution
            report.rolling_attribution = self._calculate_rolling_attribution(
                portfolio_returns, factor_returns
            )
            
            # Summary statistics
            report.attribution_summary = self._create_attribution_summary(report)
            
            # Model diagnostics
            report.model_diagnostics = self._create_model_diagnostics(report)
            
            # Warnings
            report.warnings = self._generate_attribution_warnings(report)
            
            logger.info(f"Attribution report generated for {portfolio_name}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating attribution report: {e}")
            report.warnings.append(f"Report generation error: {str(e)}")
            return report
    
    def _create_factor_loadings_table(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame
    ) -> pd.DataFrame:
        """Create factor loadings table"""
        
        try:
            model_result = self.factor_analyzer.build_factor_model(portfolio_returns, factor_returns)
            
            if model_result:
                loadings_data = []
                
                for factor, loading in model_result['factor_loadings'].items():
                    contribution = model_result['factor_contributions'].get(factor, 0.0)
                    
                    loadings_data.append({
                        'Factor': factor,
                        'Loading': loading,
                        'Contribution': contribution,
                        'T_Stat': loading / 0.1  # Simplified t-stat
                    })
                
                return pd.DataFrame(loadings_data)
            
        except Exception as e:
            logger.error(f"Error creating factor loadings table: {e}")
        
        return pd.DataFrame()
    
    def _calculate_factor_importance(self, factor_contributions: Dict[str, float]) -> Dict[str, float]:
        """Calculate factor importance"""
        
        total_contribution = sum(abs(contrib) for contrib in factor_contributions.values())
        
        if total_contribution == 0:
            return {}
        
        return {
            factor: abs(contrib) / total_contribution
            for factor, contrib in factor_contributions.items()
        }
    
    def _create_attribution_waterfall(self, attribution: AttributionResult) -> Dict[str, float]:
        """Create attribution waterfall data"""
        
        waterfall = {}
        
        # Factor contributions
        for factor, contrib in attribution.factor_contributions.items():
            waterfall[f"Factor: {factor}"] = contrib
        
        # Risk components
        waterfall["Systematic Return"] = attribution.systematic_return
        waterfall["Specific Return"] = attribution.specific_return
        
        # Total
        waterfall["Total Return"] = attribution.total_return
        
        return waterfall
    
    def _calculate_rolling_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: Optional[pd.DataFrame],
        window: int = 60
    ) -> pd.DataFrame:
        """Calculate rolling attribution"""
        
        if factor_returns is None or len(portfolio_returns) < window:
            return pd.DataFrame()
        
        try:
            rolling_data = []
            
            for i in range(window, len(portfolio_returns)):
                end_idx = i
                start_idx = i - window
                
                period_returns = portfolio_returns.iloc[start_idx:end_idx]
                period_factors = factor_returns.iloc[start_idx:end_idx]
                
                model_result = self.factor_analyzer.build_factor_model(period_returns, period_factors)
                
                if model_result:
                    row_data = {
                        'Date': portfolio_returns.index[end_idx],
                        'R_Squared': model_result['diagnostics']['r_squared'],
                        'Alpha': model_result['alpha'],
                        **model_result['factor_contributions']
                    }
                    rolling_data.append(row_data)
            
            return pd.DataFrame(rolling_data).set_index('Date')
            
        except Exception as e:
            logger.error(f"Error calculating rolling attribution: {e}")
            return pd.DataFrame()
    
    def _create_attribution_summary(self, report: AttributionReport) -> Dict[str, Any]:
        """Create attribution summary statistics"""
        
        attribution = report.total_attribution
        
        return {
            'performance_summary': {
                'total_return': f"{attribution.total_return:.2%}",
                'systematic_return': f"{attribution.systematic_return:.2%}",
                'specific_return': f"{attribution.specific_return:.2%}",
                'r_squared': f"{attribution.r_squared:.2f}"
            },
            'top_factor_contributions': self._get_top_contributions(
                attribution.factor_contributions, 5
            ),
            'attribution_quality': {
                'model_fit': attribution.r_squared,
                'tracking_error': attribution.tracking_error
            }
        }
    
    def _get_top_contributions(self, contributions: Dict[str, float], top_n: int = 5) -> Dict[str, float]:
        """Get top factor contributions"""
        
        sorted_contributions = sorted(
            contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        return dict(sorted_contributions[:top_n])
    
    def _create_model_diagnostics(self, report: AttributionReport) -> Dict[str, Any]:
        """Create model diagnostics"""
        
        attribution = report.total_attribution
        
        return {
            'model_fit': {
                'r_squared': attribution.r_squared,
                'adjusted_r_squared': max(0, attribution.r_squared - 0.05)  # Simplified
            },
            'factor_significance': len([
                f for f, c in attribution.factor_contributions.items() if abs(c) > 0.001
            ]),
            'attribution_completeness': abs(
                attribution.systematic_return + attribution.specific_return - attribution.total_return
            ) < 0.001
        }
    
    def _generate_attribution_warnings(self, report: AttributionReport) -> List[str]:
        """Generate attribution analysis warnings"""
        
        warnings = []
        attribution = report.total_attribution
        
        # Model quality warnings
        if attribution.r_squared < 0.5:
            warnings.append("Low R-squared indicates poor model fit")
        
        if abs(attribution.specific_return) > abs(attribution.systematic_return):
            warnings.append("High specific risk - consider diversification")
        
        # Data quality warnings
        if len(report.monthly_attribution) < 3:
            warnings.append("Limited attribution history - results may be unstable")
        
        return warnings
    
    def get_attribution_statistics(self) -> Dict[str, Any]:
        """Get attribution analysis statistics"""
        
        with self._lock:
            return {
                'total_attributions': len(self._attribution_history),
                'factor_models_cached': len(self._factor_models),
                'analyzer_config': {
                    'attribution_method': self.config.attribution_method.value,
                    'lookback_period': self.config.lookback_period,
                    'confidence_level': self.config.confidence_level
                }
            }
    
    def cache_factor_model(self, symbol: str, model_data: Dict[str, Any]) -> None:
        """Cache factor model"""
        
        with self._lock:
            self._factor_models[symbol] = {
                'model_data': model_data,
                'timestamp': datetime.now()
            }
    
    def get_cached_factor_model(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached factor model"""
        
        with self._lock:
            cached = self._factor_models.get(symbol)
            if cached:
                # Check if cache is still fresh (24 hours)
                if (datetime.now() - cached['timestamp']).total_seconds() < 86400:
                    return cached['model_data']
                else:
                    # Remove stale cache
                    del self._factor_models[symbol]
            
            return None