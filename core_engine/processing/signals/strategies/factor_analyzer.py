"""
Signals Engine - Factor Analyzer
Advanced factor analysis with principal component analysis, factor modeling, and risk factor decomposition
"""

import asyncio
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
from abc import ABC, abstractmethod
from scipy import stats
from sklearn.linear_model import LinearRegression, Ridge, Lasso
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

class FactorType(Enum):
    """Factor types"""
    MARKET = "market"
    SIZE = "size"
    VALUE = "value"
    MOMENTUM = "momentum"
    QUALITY = "quality"
    VOLATILITY = "volatility"
    PROFITABILITY = "profitability"
    INVESTMENT = "investment"
    LEVERAGE = "leverage"
    LIQUIDITY = "liquidity"
    SECTOR = "sector"
    COUNTRY = "country"
    CURRENCY = "currency"
    MACRO = "macro"
    CUSTOM = "custom"

class FactorModel(Enum):
    """Factor model types"""
    SINGLE_FACTOR = "single_factor"
    MULTI_FACTOR = "multi_factor"
    FAMA_FRENCH_3 = "fama_french_3"
    FAMA_FRENCH_5 = "fama_french_5"
    CARHART_4 = "carhart_4"
    PCA_FACTOR = "pca_factor"
    STATISTICAL_FACTOR = "statistical_factor"
    FUNDAMENTAL_FACTOR = "fundamental_factor"

class RiskModel(Enum):
    """Risk model types"""
    COVARIANCE = "covariance"
    FACTOR_COVARIANCE = "factor_covariance"
    SHRINKAGE = "shrinkage"
    ROBUST = "robust"
    BAYESIAN = "bayesian"

@dataclass
class FactorDefinition:
    """Factor definition"""
    factor_id: str
    factor_type: FactorType
    name: str
    description: str

    # Calculation parameters
    calculation_method: str
    required_fields: List[str]
    lookback_period: int = 252  # Default 1 year

    # Normalization
    normalize: bool = True
    winsorize: bool = True
    winsorize_limits: Tuple[float, float] = (0.05, 0.95)

    # Grouping
    sector_neutral: bool = False
    market_cap_neutral: bool = False

    # Metadata
    created_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FactorExposure:
    """Factor exposure for a security"""
    symbol: str
    factor_id: str
    exposure: float
    z_score: float
    percentile: float

    # Quality metrics
    confidence: float
    r_squared: float

    # Timing
    calculation_date: datetime
    data_date: datetime

    # Supporting data
    raw_value: Optional[float] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None

@dataclass
class FactorReturn:
    """Factor return data"""
    factor_id: str
    date: datetime
    return_value: float

    # Risk metrics
    volatility: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    # Model fit
    t_statistic: Optional[float] = None
    p_value: Optional[float] = None

    # Attribution
    contribution: Optional[float] = None

@dataclass
class FactorModel:
    """Factor model specification"""
    model_id: str
    model_type: FactorModel
    factors: List[str]

    # Model parameters
    lookback_period: int = 252
    min_observations: int = 50
    alpha: float = 0.05  # Significance level

    # Estimation method
    estimation_method: str = "ols"  # ols, ridge, lasso, robust
    regularization_param: Optional[float] = None

    # Risk model
    risk_model: RiskModel = RiskModel.COVARIANCE

    # Update frequency
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly, quarterly

    # Model metadata
    created_date: datetime = field(default_factory=datetime.now)
    last_fitted: Optional[datetime] = None

    # Model results
    model_r_squared: Optional[float] = None
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    residual_volatility: Optional[float] = None

@dataclass
class FactorAnalysisResult:
    """Factor analysis result"""
    analysis_id: str
    analysis_date: datetime

    # Factor exposures
    exposures: Dict[str, List[FactorExposure]]

    # Factor returns
    factor_returns: Dict[str, List[FactorReturn]]

    # Risk analysis
    factor_covariance_matrix: Optional[np.ndarray] = None
    specific_risk: Dict[str, float] = field(default_factory=dict)

    # Performance attribution
    total_return: Optional[float] = None
    factor_contribution: Dict[str, float] = field(default_factory=dict)
    specific_return: Optional[float] = None

    # Model diagnostics
    model_r_squared: float = 0.0
    residual_analysis: Dict[str, Any] = field(default_factory=dict)

    # Quality metrics
    data_coverage: float = 1.0
    factor_significance: Dict[str, float] = field(default_factory=dict)

class FactorCalculator(ABC):
    """Abstract factor calculator"""

    def __init__(self, factor_definition: FactorDefinition):
        self.factor_definition = factor_definition

    @abstractmethod
    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate factor values"""

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate input data"""
        required_fields = self.factor_definition.required_fields

        if data.empty:
            return False

        missing_fields = set(required_fields) - set(data.columns)
        if missing_fields:
            logger.warning(f"Missing required fields for {self.factor_definition.factor_id}: {missing_fields}")
            return False

        return True

    def _normalize_values(self, values: pd.Series) -> pd.Series:
        """Normalize factor values"""
        if not self.factor_definition.normalize:
            return values

        # Winsorize outliers
        if self.factor_definition.winsorize:
            lower, upper = self.factor_definition.winsorize_limits
            values = values.clip(
                lower=values.quantile(lower),
                upper=values.quantile(upper)
            )

        # Z-score normalization
        return (values - values.mean()) / values.std()

class MomentumFactorCalculator(FactorCalculator):
    """Momentum factor calculator"""

    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate momentum factor"""

        if not self.validate_data(data):
            return pd.Series()

        # Price momentum (12-1 month)
        lookback = self.factor_definition.lookback_period
        prices = data['close']

        # Calculate returns
        if len(prices) < lookback:
            return pd.Series()

        # 12-month return excluding last month
        momentum_return = (prices.iloc[-22] / prices.iloc[-lookback]) - 1 if len(prices) >= lookback else 0

        # Create series with momentum value for each symbol
        momentum_series = pd.Series([momentum_return], index=[data.index[-1]])

        return self._normalize_values(momentum_series)

class ValueFactorCalculator(FactorCalculator):
    """Value factor calculator"""

    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate value factor"""

        if not self.validate_data(data):
            return pd.Series()

        # Book-to-market ratio (simplified)
        market_cap = context.get('market_cap', 1.0)
        book_value = context.get('book_value', market_cap * 0.5)  # Simplified

        # Calculate book-to-market
        book_to_market = book_value / market_cap if market_cap > 0 else 0

        # Price-to-earnings ratio
        earnings = context.get('earnings', market_cap * 0.1)  # Simplified
        pe_ratio = market_cap / earnings if earnings > 0 else 50  # Default high PE

        # Combine value metrics (inverse of PE, direct BM)
        value_score = book_to_market - (1 / pe_ratio)

        value_series = pd.Series([value_score], index=[data.index[-1]])

        return self._normalize_values(value_series)

class QualityFactorCalculator(FactorCalculator):
    """Quality factor calculator"""

    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate quality factor"""

        if not self.validate_data(data):
            return pd.Series()

        # Return on equity
        roe = context.get('roe', 0.15)  # Default 15%

        # Debt-to-equity ratio
        debt_to_equity = context.get('debt_to_equity', 0.5)  # Default 50%

        # Earnings variability (price volatility as proxy)
        price_volatility = data['close'].pct_change().std() * np.sqrt(252)
        earnings_stability = max(0, 1 - price_volatility)  # Inverse of volatility

        # Combine quality metrics
        quality_score = roe + earnings_stability - debt_to_equity

        quality_series = pd.Series([quality_score], index=[data.index[-1]])

        return self._normalize_values(quality_series)

class VolatilityFactorCalculator(FactorCalculator):
    """Volatility factor calculator"""

    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate volatility factor"""

        if not self.validate_data(data):
            return pd.Series()

        # Calculate historical volatility
        returns = data['close'].pct_change().dropna()

        if len(returns) < 20:
            return pd.Series()

        # Annualized volatility
        volatility = returns.std() * np.sqrt(252)

        volatility_series = pd.Series([volatility], index=[data.index[-1]])

        return self._normalize_values(volatility_series)

class SizeFactorCalculator(FactorCalculator):
    """Size factor calculator"""

    async def calculate_factor(
        self,
        data: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Calculate size factor"""

        if not self.validate_data(data):
            return pd.Series()

        # Market capitalization
        market_cap = context.get('market_cap', 1000000000)  # Default 1B

        # Log market cap (size factor is typically log of market cap)
        # Only calculate log for positive values to avoid invalid values
        log_market_cap = np.log(market_cap) if market_cap > 0 else np.nan

        size_series = pd.Series([log_market_cap], index=[data.index[-1]])

        return self._normalize_values(size_series)

class FactorAnalyzer:
    """
    Advanced factor analysis engine

    Provides comprehensive factor analysis including exposure calculation,
    risk decomposition, and performance attribution.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize factor analyzer"""
        self.config = config or {}

        # Factor definitions
        self._factor_definitions = {}
        self._factor_calculators = {}

        # Factor models
        self._factor_models = {}

        # Data storage
        self._factor_exposures = defaultdict(dict)  # symbol -> factor_id -> exposure
        self._factor_returns = defaultdict(list)  # factor_id -> [returns]

        # asyncio.Lock for async methods (calculate_factor_exposures, run_factor_analysis)
        self._lock = asyncio.Lock()
        # threading.Lock for sync methods (register_factor, register_factor_model,
        # _calculate_percentile, get_factor_definitions, get_factor_models,
        # get_factor_exposures, get_performance_metrics)
        self._sync_lock = threading.Lock()

        # Analysis cache
        self._analysis_cache = {}

        # Initialize default factors
        self._initialize_default_factors()

        # Performance tracking
        self._calculation_times = deque(maxlen=1000)

        logger.info("FactorAnalyzer initialized")

    def _initialize_default_factors(self) -> None:
        """Initialize default factor definitions"""

        # Momentum factor
        momentum_factor = FactorDefinition(
            factor_id="momentum_12_1",
            factor_type=FactorType.MOMENTUM,
            name="12-1 Month Momentum",
            description="12-month momentum excluding last month",
            calculation_method="price_momentum",
            required_fields=['close'],
            lookback_period=252
        )
        self.register_factor(momentum_factor, MomentumFactorCalculator(momentum_factor))

        # Value factor
        value_factor = FactorDefinition(
            factor_id="book_to_market",
            factor_type=FactorType.VALUE,
            name="Book-to-Market Ratio",
            description="Book value to market capitalization ratio",
            calculation_method="book_to_market",
            required_fields=['close'],
            lookback_period=1
        )
        self.register_factor(value_factor, ValueFactorCalculator(value_factor))

        # Quality factor
        quality_factor = FactorDefinition(
            factor_id="quality_score",
            factor_type=FactorType.QUALITY,
            name="Quality Score",
            description="Composite quality score based on profitability and stability",
            calculation_method="quality_composite",
            required_fields=['close'],
            lookback_period=252
        )
        self.register_factor(quality_factor, QualityFactorCalculator(quality_factor))

        # Volatility factor
        volatility_factor = FactorDefinition(
            factor_id="volatility",
            factor_type=FactorType.VOLATILITY,
            name="Price Volatility",
            description="Annualized price volatility",
            calculation_method="historical_volatility",
            required_fields=['close'],
            lookback_period=252
        )
        self.register_factor(volatility_factor, VolatilityFactorCalculator(volatility_factor))

        # Size factor
        size_factor = FactorDefinition(
            factor_id="market_cap",
            factor_type=FactorType.SIZE,
            name="Market Capitalization",
            description="Log of market capitalization",
            calculation_method="log_market_cap",
            required_fields=['close'],
            lookback_period=1
        )
        self.register_factor(size_factor, SizeFactorCalculator(size_factor))

        logger.info("Default factors initialized")

    def register_factor(self, factor_definition: FactorDefinition, calculator: FactorCalculator) -> None:
        """Register a factor definition and calculator"""

        with self._sync_lock:
            self._factor_definitions[factor_definition.factor_id] = factor_definition
            self._factor_calculators[factor_definition.factor_id] = calculator

        logger.info(f"Registered factor: {factor_definition.factor_id}")

    def register_factor_model(self, model: FactorModel) -> None:
        """Register a factor model"""

        with self._sync_lock:
            self._factor_models[model.model_id] = model

        logger.info(f"Registered factor model: {model.model_id}")

    async def calculate_factor_exposures(
        self,
        symbols: List[str],
        data: Dict[str, pd.DataFrame],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, FactorExposure]]:
        """Calculate factor exposures for multiple symbols"""

        context = context or {}
        results = {}

        for symbol in symbols:
            symbol_data = data.get(symbol)
            if symbol_data is not None and not symbol_data.empty:
                symbol_context = context.get(symbol, {})
                exposures = await self.calculate_exposures(symbol, symbol_data, symbol_context)
                if exposures:
                    results[symbol] = exposures

        return results

    async def calculate_exposures(
        self,
        symbol: str,
        data: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, FactorExposure]:
        """Calculate factor exposures for a single symbol"""

        start_time = time.time()
        context = context or {}
        exposures = {}

        try:
            for factor_id, calculator in self._factor_calculators.items():
                try:
                    # Calculate factor value
                    factor_values = await calculator.calculate_factor(data, context)

                    if not factor_values.empty:
                        factor_value = factor_values.iloc[0]

                        # Create factor exposure
                        exposure = FactorExposure(
                            symbol=symbol,
                            factor_id=factor_id,
                            exposure=factor_value,
                            z_score=factor_value,  # Already normalized
                            percentile=self._calculate_percentile(factor_id, factor_value),
                            confidence=0.95,  # Default confidence
                            r_squared=0.0,  # Would be calculated in regression
                            calculation_date=datetime.now(),
                            data_date=data.index[-1] if not data.empty else datetime.now(),
                            raw_value=factor_value
                        )

                        exposures[factor_id] = exposure

                        # Store in cache
                        async with self._lock:
                            if symbol not in self._factor_exposures:
                                self._factor_exposures[symbol] = {}
                            self._factor_exposures[symbol][factor_id] = exposure

                except Exception as e:
                    logger.error(f"Error calculating factor {factor_id} for {symbol}: {e}")
                    continue

            # Record calculation time
            calculation_time = (time.time() - start_time) * 1000
            self._calculation_times.append(calculation_time)

            logger.debug(f"Calculated {len(exposures)} factor exposures for {symbol} in {calculation_time:.2f}ms")

            return exposures

        except Exception as e:
            logger.error(f"Error calculating exposures for {symbol}: {e}")
            return {}

    def _calculate_percentile(self, factor_id: str, factor_value: float) -> float:
        """Calculate percentile ranking for factor value"""

        try:
            # Get historical factor values for percentile calculation
            with self._sync_lock:
                historical_values = []
                for symbol_exposures in self._factor_exposures.values():
                    if factor_id in symbol_exposures:
                        historical_values.append(symbol_exposures[factor_id].exposure)

                if len(historical_values) < 10:  # Not enough data
                    return 0.5  # Default to median

                # Calculate percentile
                percentile = stats.percentileofscore(historical_values, factor_value) / 100
                return np.clip(percentile, 0, 1)

        except Exception:
            return 0.5

    async def run_factor_analysis(
        self,
        symbols: List[str],
        returns_data: Dict[str, pd.Series],
        model_id: Optional[str] = None
    ) -> FactorAnalysisResult:
        """Run comprehensive factor analysis"""

        try:
            model = self._factor_models.get(model_id) if model_id else self._create_default_model()

            # Get factor exposures
            exposures_data = {}
            for symbol in symbols:
                async with self._lock:
                    if symbol in self._factor_exposures:
                        exposures_data[symbol] = self._factor_exposures[symbol]

            if not exposures_data:
                logger.warning("No factor exposures available for analysis")
                return self._create_empty_analysis_result()

            # Run factor model regression
            factor_returns, factor_loadings, r_squared = await self._run_factor_regression(
                symbols, returns_data, exposures_data, model
            )

            # Calculate risk decomposition
            factor_covariance, specific_risk = await self._calculate_risk_decomposition(
                symbols, factor_returns, factor_loadings
            )

            # Performance attribution
            attribution_results = await self._calculate_performance_attribution(
                symbols, returns_data, factor_returns, factor_loadings
            )

            # Create analysis result
            analysis_result = FactorAnalysisResult(
                analysis_id=f"factor_analysis_{int(time.time())}",
                analysis_date=datetime.now(),
                exposures=exposures_data,
                factor_returns={fid: factor_returns.get(fid, []) for fid in model.factors},
                factor_covariance_matrix=factor_covariance,
                specific_risk=specific_risk,
                total_return=attribution_results.get('total_return'),
                factor_contribution=attribution_results.get('factor_contribution', {}),
                specific_return=attribution_results.get('specific_return'),
                model_r_squared=r_squared,
                data_coverage=len(exposures_data) / len(symbols) if symbols else 0,
                factor_significance=self._calculate_factor_significance(factor_returns)
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Error running factor analysis: {e}")
            return self._create_empty_analysis_result()

    async def _run_factor_regression(
        self,
        symbols: List[str],
        returns_data: Dict[str, pd.Series],
        exposures_data: Dict[str, Dict[str, FactorExposure]],
        model: FactorModel
    ) -> Tuple[Dict[str, List[FactorReturn]], Dict[str, Dict[str, float]], float]:
        """Run factor model regression"""

        try:
            # Prepare data for regression
            returns_matrix = []
            exposures_matrix = []
            valid_symbols = []

            for symbol in symbols:
                if symbol in returns_data and symbol in exposures_data:
                    returns_series = returns_data[symbol]
                    if not returns_series.empty:
                        # Get latest return
                        latest_return = returns_series.iloc[-1]
                        returns_matrix.append(latest_return)

                        # Get factor exposures
                        exposures_row = []
                        for factor_id in model.factors:
                            exposure = exposures_data[symbol].get(factor_id)
                            if exposure:
                                exposures_row.append(exposure.exposure)
                            else:
                                exposures_row.append(0.0)

                        exposures_matrix.append(exposures_row)
                        valid_symbols.append(symbol)

            if len(returns_matrix) < model.min_observations:
                logger.warning("Insufficient observations for factor regression")
                return {}, {}, 0.0

            # Convert to numpy arrays
            y = np.array(returns_matrix)
            X = np.array(exposures_matrix)

            # Add intercept
            X = np.column_stack([np.ones(len(X)), X])

            # Run regression
            if model.estimation_method == "ridge" and model.regularization_param:
                reg = Ridge(alpha=model.regularization_param)
                reg.fit(X, y)
                coefficients = reg.coef_
                r_squared = reg.score(X, y)
            elif model.estimation_method == "lasso" and model.regularization_param:
                reg = Lasso(alpha=model.regularization_param)
                reg.fit(X, y)
                coefficients = reg.coef_
                r_squared = reg.score(X, y)
            else:
                # OLS regression
                reg = LinearRegression()
                reg.fit(X, y)
                coefficients = np.concatenate([[reg.intercept_], reg.coef_[1:]])
                r_squared = reg.score(X, y)

            # Extract factor returns (coefficients)
            factor_returns = {}
            factor_loadings = {}

            for i, factor_id in enumerate(model.factors):
                factor_return_value = coefficients[i + 1]  # Skip intercept

                factor_return = FactorReturn(
                    factor_id=factor_id,
                    date=datetime.now(),
                    return_value=factor_return_value,
                    volatility=0.0,  # Would calculate from time series
                    t_statistic=factor_return_value / (np.std(y) / np.sqrt(len(y))),  # Simplified
                    p_value=0.05  # Simplified
                )

                factor_returns[factor_id] = [factor_return]

                # Factor loadings for each symbol
                factor_loadings[factor_id] = {}
                for j, symbol in enumerate(valid_symbols):
                    factor_loadings[factor_id][symbol] = X[j, i + 1] * factor_return_value

            return factor_returns, factor_loadings, r_squared

        except Exception as e:
            logger.error(f"Error in factor regression: {e}")
            return {}, {}, 0.0

    async def _calculate_risk_decomposition(
        self,
        symbols: List[str],
        factor_returns: Dict[str, List[FactorReturn]],
        factor_loadings: Dict[str, Dict[str, float]]
    ) -> Tuple[Optional[np.ndarray], Dict[str, float]]:
        """Calculate risk decomposition"""

        try:
            # Calculate factor covariance matrix (simplified)
            factor_ids = list(factor_returns.keys())
            n_factors = len(factor_ids)

            if n_factors == 0:
                return None, {}

            # Create covariance matrix (simplified - would use historical data)
            factor_covariance = np.eye(n_factors) * 0.01  # 1% variance, no correlation

            # Calculate specific risk for each symbol
            specific_risk = {}
            for symbol in symbols:
                # Simplified specific risk calculation
                total_factor_variance = 0
                for factor_id in factor_ids:
                    loading = factor_loadings.get(factor_id, {}).get(symbol, 0)
                    total_factor_variance += loading ** 2 * 0.01  # Assuming 1% factor variance

                # Specific risk is residual
                specific_risk[symbol] = max(0.001, 0.02 - total_factor_variance)  # 2% total risk assumed

            return factor_covariance, specific_risk

        except Exception as e:
            logger.error(f"Error calculating risk decomposition: {e}")
            return None, {}

    async def _calculate_performance_attribution(
        self,
        symbols: List[str],
        returns_data: Dict[str, pd.Series],
        factor_returns: Dict[str, List[FactorReturn]],
        factor_loadings: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Calculate performance attribution"""

        try:
            total_return = 0
            factor_contribution = {}
            specific_return = 0

            # Calculate portfolio-level attribution
            for symbol in symbols:
                if symbol in returns_data:
                    symbol_return = returns_data[symbol].iloc[-1] if not returns_data[symbol].empty else 0
                    total_return += symbol_return / len(symbols)  # Equal weight

                    # Factor contributions
                    symbol_specific = symbol_return
                    for factor_id, loadings in factor_loadings.items():
                        if symbol in loadings:
                            factor_contrib = loadings[symbol] / len(symbols)  # Equal weight
                            factor_contribution[factor_id] = factor_contribution.get(factor_id, 0) + factor_contrib
                            symbol_specific -= factor_contrib

                    specific_return += symbol_specific / len(symbols)

            return {
                'total_return': total_return,
                'factor_contribution': factor_contribution,
                'specific_return': specific_return
            }

        except Exception as e:
            logger.error(f"Error calculating performance attribution: {e}")
            return {}

    def _calculate_factor_significance(self, factor_returns: Dict[str, List[FactorReturn]]) -> Dict[str, float]:
        """Calculate factor significance"""

        significance = {}

        for factor_id, returns_list in factor_returns.items():
            if returns_list:
                latest_return = returns_list[-1]
                # Use t-statistic and p-value for significance
                if latest_return.p_value is not None:
                    significance[factor_id] = 1 - latest_return.p_value
                else:
                    significance[factor_id] = 0.5
            else:
                significance[factor_id] = 0.0

        return significance

    def _create_default_model(self) -> FactorModel:
        """Create default factor model"""

        return FactorModel(
            model_id="default_multi_factor",
            model_type=FactorModel.MULTI_FACTOR,
            factors=list(self._factor_definitions.keys()),
            lookback_period=252,
            min_observations=20,
            estimation_method="ols",
            risk_model=RiskModel.COVARIANCE
        )

    def _create_empty_analysis_result(self) -> FactorAnalysisResult:
        """Create empty analysis result"""

        return FactorAnalysisResult(
            analysis_id=f"empty_analysis_{int(time.time())}",
            analysis_date=datetime.now(),
            exposures={},
            factor_returns={}
        )

    def get_factor_definitions(self) -> Dict[str, FactorDefinition]:
        """Get all factor definitions"""
        with self._sync_lock:
            return dict(self._factor_definitions)

    def get_factor_models(self) -> Dict[str, FactorModel]:
        """Get all factor models"""
        with self._sync_lock:
            return dict(self._factor_models)

    def get_factor_exposures(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, FactorExposure]]:
        """Get factor exposures"""
        with self._sync_lock:
            if symbol:
                return {symbol: self._factor_exposures.get(symbol, {})}
            else:
                return dict(self._factor_exposures)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""

        with self._sync_lock:
            avg_calculation_time = np.mean(self._calculation_times) if self._calculation_times else 0

            return {
                'registered_factors': len(self._factor_definitions),
                'registered_models': len(self._factor_models),
                'symbols_with_exposures': len(self._factor_exposures),
                'average_calculation_time_ms': avg_calculation_time,
                'factor_types': [fd.factor_type.value for fd in self._factor_definitions.values()]
            }