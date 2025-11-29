"""
Signals Engine - Alpha Research
Advanced alpha research framework with strategy development, backtesting, and alpha decay analysis
"""

import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
import warnings

from core_engine.processing.indicators.talib_indicators import calculate_rsi

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class AlphaType(Enum):
    """Alpha strategy types"""
    CROSS_SECTIONAL = "cross_sectional"
    TIME_SERIES = "time_series"
    FACTOR_BASED = "factor_based"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    MULTI_ASSET = "multi_asset"


class AlphaFrequency(Enum):
    """Alpha signal frequencies"""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class AlphaStatus(Enum):
    """Alpha research status"""
    RESEARCH = "research"
    DEVELOPMENT = "development"
    TESTING = "testing"
    VALIDATION = "validation"
    PRODUCTION = "production"
    RETIRED = "retired"


class BacktestMode(Enum):
    """Backtesting modes"""
    WALK_FORWARD = "walk_forward"
    EXPANDING_WINDOW = "expanding_window"
    ROLLING_WINDOW = "rolling_window"
    MONTE_CARLO = "monte_carlo"


@dataclass
class AlphaParameters:
    """Alpha strategy parameters"""
    alpha_id: str
    alpha_type: AlphaType
    frequency: AlphaFrequency
    
    # Lookback parameters
    lookback_periods: int = 20
    prediction_horizon: int = 5
    
    # Universe parameters
    universe_size: int = 500
    min_market_cap: float = 1e9  # $1B
    exclude_sectors: List[str] = field(default_factory=list)
    
    # Signal parameters
    signal_decay: float = 0.1  # Per period decay
    neutralization: List[str] = field(default_factory=list)  # sector, size, etc.
    
    # Risk parameters
    max_turnover: float = 0.2  # 20% daily turnover
    max_position_size: float = 0.02  # 2% max position
    
    # Research parameters
    research_start: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=1000))
    research_end: datetime = field(default_factory=datetime.now)
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlphaSignal:
    """Alpha signal output"""
    alpha_id: str
    symbol: str
    timestamp: datetime
    
    # Signal properties
    signal_value: float
    signal_rank: Optional[int] = None
    signal_percentile: Optional[float] = None
    
    # Confidence and quality
    confidence: float = 0.5
    quality_score: float = 1.0
    
    # Risk metrics
    expected_return: Optional[float] = None
    expected_volatility: Optional[float] = None
    beta: Optional[float] = None
    
    # Factor exposures
    factor_exposures: Dict[str, float] = field(default_factory=dict)
    
    # Attribution
    technical_component: Optional[float] = None
    fundamental_component: Optional[float] = None
    sentiment_component: Optional[float] = None
    
    # Metadata
    model_version: str = "1.0"
    data_vintage: datetime = field(default_factory=datetime.now)


@dataclass
class BacktestResult:
    """Backtesting result"""
    alpha_id: str
    backtest_id: str
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Risk-adjusted metrics
    information_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    
    # Trading metrics
    hit_rate: float
    average_holding_period: float
    turnover: float
    
    # Alpha decay analysis
    decay_half_life: Optional[float] = None
    signal_autocorrelation: Dict[int, float] = field(default_factory=dict)
    
    # Factor analysis
    market_beta: float = 0.0
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    tracking_error: float = 0.0
    
    # Time series data
    returns_series: Optional[pd.Series] = None
    positions_series: Optional[pd.DataFrame] = None
    
    # Diagnostics
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    num_periods: int = 0
    num_securities: int = 0


@dataclass
class AlphaDecayAnalysis:
    """Alpha decay analysis results"""
    alpha_id: str
    analysis_date: datetime
    
    # Decay metrics
    decay_half_life_days: float
    decay_rate_per_day: float
    optimal_holding_period: int
    
    # Autocorrelation analysis
    signal_autocorrelations: Dict[int, float]  # lag -> correlation
    return_predictability: Dict[int, float]  # horizon -> R²
    
    # Frequency analysis
    optimal_rebalance_frequency: AlphaFrequency
    frequency_performance: Dict[str, float]  # frequency -> Sharpe ratio
    
    # Regime analysis
    bull_market_decay: float
    bear_market_decay: float
    high_vol_decay: float
    low_vol_decay: float
    
    # Recommendations
    recommended_holding_period: int
    recommended_decay_adjustment: float


class AlphaStrategy(ABC):
    """Abstract alpha strategy"""
    
    def __init__(self, parameters: AlphaParameters):
        self.parameters = parameters
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
    
    @abstractmethod
    async def generate_features(
        self,
        data: Dict[str, pd.DataFrame],
        context: Dict[str, Any]
    ) -> pd.DataFrame:
        """Generate features for alpha model"""
    
    @abstractmethod
    async def fit_model(
        self,
        features: pd.DataFrame,
        returns: pd.Series,
        context: Dict[str, Any]
    ) -> None:
        """Fit alpha model"""
    
    @abstractmethod
    async def predict_alpha(
        self,
        features: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Predict alpha signals"""
    
    def validate_data(self, data: Dict[str, pd.DataFrame]) -> bool:
        """Validate input data"""
        if not data:
            return False
        
        for symbol, df in data.items():
            if df.empty or len(df) < self.parameters.lookback_periods:
                logger.warning(f"Insufficient data for {symbol}")
                return False
        
        return True


class MomentumAlphaStrategy(AlphaStrategy):
    """Momentum-based alpha strategy"""
    
    async def generate_features(
        self,
        data: Dict[str, pd.DataFrame],
        context: Dict[str, Any]
    ) -> pd.DataFrame:
        """Generate momentum features"""
        
        features_list = []
        
        for symbol, df in data.items():
            if len(df) < self.parameters.lookback_periods:
                continue
            
            prices = df['close']
            
            # Calculate momentum features
            features = {
                'symbol': symbol,
                'price_momentum_5d': (prices.iloc[-1] / prices.iloc[-6] - 1) if len(prices) >= 6 else 0,
                'price_momentum_20d': (prices.iloc[-1] / prices.iloc[-21] - 1) if len(prices) >= 21 else 0,
                'price_momentum_60d': (prices.iloc[-1] / prices.iloc[-61] - 1) if len(prices) >= 61 else 0,
                'volume_momentum': df['volume'].rolling(20).mean().iloc[-1] / df['volume'].rolling(60).mean().iloc[-1] - 1 if 'volume' in df.columns and len(df) >= 60 else 0,
                'volatility': prices.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) if len(prices) >= 20 else 0,
                'rsi': self._get_rsi_value(prices, 14),
                'price_trend': np.polyfit(range(20), prices.tail(20).values, 1)[0] if len(prices) >= 20 else 0
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list).set_index('symbol')
    
    def _get_rsi_value(self, prices: pd.Series, window: int = 14) -> float:
        """Get RSI value using canonical implementation"""
        if len(prices) < window + 1:
            return 50.0
        rsi_series = calculate_rsi(prices, window)
        return rsi_series.iloc[-1] if not rsi_series.empty and not pd.isna(rsi_series.iloc[-1]) else 50.0
    
    async def fit_model(
        self,
        features: pd.DataFrame,
        returns: pd.Series,
        context: Dict[str, Any]
    ) -> None:
        """Fit momentum model"""
        
        # Align features and returns
        aligned_features, aligned_returns = features.align(returns, join='inner', axis=0)
        
        if len(aligned_features) < 10:
            logger.warning("Insufficient data for model fitting")
            return
        
        # Scale features
        X = self.scaler.fit_transform(aligned_features.fillna(0))
        y = aligned_returns.values
        
        # Use Ridge regression for momentum model
        self.model = Ridge(alpha=1.0)
        self.model.fit(X, y)
        self.is_fitted = True
        
        logger.info(f"Momentum model fitted with R² = {self.model.score(X, y):.3f}")
    
    async def predict_alpha(
        self,
        features: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Predict momentum alpha"""
        
        if not self.is_fitted or self.model is None:
            logger.warning("Model not fitted")
            return pd.Series()
        
        # Scale features
        X = self.scaler.transform(features.fillna(0))
        
        # Predict
        predictions = self.model.predict(X)
        
        return pd.Series(predictions, index=features.index)


class MeanReversionAlphaStrategy(AlphaStrategy):
    """Mean reversion alpha strategy"""
    
    async def generate_features(
        self,
        data: Dict[str, pd.DataFrame],
        context: Dict[str, Any]
    ) -> pd.DataFrame:
        """Generate mean reversion features"""
        
        features_list = []
        
        for symbol, df in data.items():
            if len(df) < self.parameters.lookback_periods:
                continue
            
            prices = df['close']
            
            # Calculate mean reversion features
            sma_20 = prices.rolling(20).mean()
            sma_50 = prices.rolling(50).mean()
            
            features = {
                'symbol': symbol,
                'price_to_sma20': (prices.iloc[-1] / sma_20.iloc[-1] - 1) if not sma_20.empty else 0,
                'price_to_sma50': (prices.iloc[-1] / sma_50.iloc[-1] - 1) if not sma_50.empty else 0,
                'bollinger_position': self._calculate_bollinger_position(prices),
                'z_score_20d': self._calculate_z_score(prices, 20),
                'z_score_50d': self._calculate_z_score(prices, 50),
                'reversion_strength': self._calculate_reversion_strength(prices),
                'volatility_ratio': prices.pct_change().rolling(5).std().iloc[-1] / prices.pct_change().rolling(20).std().iloc[-1] if len(prices) >= 20 else 1.0
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list).set_index('symbol')
    
    def _calculate_bollinger_position(self, prices: pd.Series, window: int = 20, num_std: float = 2.0) -> float:
        """Calculate Bollinger Band position"""
        if len(prices) < window:
            return 0.5
        
        sma = prices.rolling(window).mean()
        std = prices.rolling(window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        current_price = prices.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        if current_upper == current_lower:
            return 0.5
        
        position = (current_price - current_lower) / (current_upper - current_lower)
        return np.clip(position, 0, 1)
    
    def _calculate_z_score(self, prices: pd.Series, window: int) -> float:
        """Calculate price z-score"""
        if len(prices) < window:
            return 0.0
        
        recent_prices = prices.tail(window)
        mean_price = recent_prices.mean()
        std_price = recent_prices.std()
        
        if std_price == 0:
            return 0.0
        
        return (prices.iloc[-1] - mean_price) / std_price
    
    def _calculate_reversion_strength(self, prices: pd.Series, window: int = 20) -> float:
        """Calculate mean reversion strength"""
        if len(prices) < window * 2:
            return 0.0
        
        # Calculate autocorrelation of returns
        returns = prices.pct_change().dropna()
        if len(returns) < window:
            return 0.0
        
        recent_returns = returns.tail(window)
        autocorr = recent_returns.autocorr(lag=1)
        
        # Negative autocorrelation indicates mean reversion
        return -autocorr if not np.isnan(autocorr) else 0.0
    
    async def fit_model(
        self,
        features: pd.DataFrame,
        returns: pd.Series,
        context: Dict[str, Any]
    ) -> None:
        """Fit mean reversion model"""
        
        # Align features and returns
        aligned_features, aligned_returns = features.align(returns, join='inner', axis=0)
        
        if len(aligned_features) < 10:
            logger.warning("Insufficient data for model fitting")
            return
        
        # Scale features
        X = self.scaler.fit_transform(aligned_features.fillna(0))
        y = aligned_returns.values
        
        # Use Linear regression for mean reversion
        self.model = LinearRegression()
        self.model.fit(X, y)
        self.is_fitted = True
        
        logger.info(f"Mean reversion model fitted with R² = {self.model.score(X, y):.3f}")
    
    async def predict_alpha(
        self,
        features: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Predict mean reversion alpha"""
        
        if not self.is_fitted or self.model is None:
            logger.warning("Model not fitted")
            return pd.Series()
        
        # Scale features
        X = self.scaler.transform(features.fillna(0))
        
        # Predict
        predictions = self.model.predict(X)
        
        return pd.Series(predictions, index=features.index)


class FactorAlphaStrategy(AlphaStrategy):
    """Factor-based alpha strategy"""
    
    async def generate_features(
        self,
        data: Dict[str, pd.DataFrame],
        context: Dict[str, Any]
    ) -> pd.DataFrame:
        """Generate factor-based features"""
        
        features_list = []
        
        for symbol, df in data.items():
            if len(df) < self.parameters.lookback_periods:
                continue
            
            prices = df['close']
            
            # Get factor exposures from context
            factor_exposures = context.get('factor_exposures', {}).get(symbol, {})
            
            # Calculate basic factors
            market_cap = context.get('market_data', {}).get(symbol, {}).get('market_cap', 1e9)
            
            features = {
                'symbol': symbol,
                'momentum_factor': factor_exposures.get('momentum_12_1', 0),
                'value_factor': factor_exposures.get('book_to_market', 0),
                'quality_factor': factor_exposures.get('quality_score', 0),
                'volatility_factor': factor_exposures.get('volatility', 0),
                'size_factor': np.log(market_cap) if market_cap > 0 else np.nan,
                'price_momentum': (prices.iloc[-1] / prices.iloc[-21] - 1) if len(prices) >= 21 else 0,
                'earnings_yield': context.get('fundamental_data', {}).get(symbol, {}).get('earnings_yield', 0.05),
                'debt_to_equity': context.get('fundamental_data', {}).get(symbol, {}).get('debt_to_equity', 0.5)
            }
            
            features_list.append(features)
        
        return pd.DataFrame(features_list).set_index('symbol')
    
    async def fit_model(
        self,
        features: pd.DataFrame,
        returns: pd.Series,
        context: Dict[str, Any]
    ) -> None:
        """Fit factor model"""
        
        # Align features and returns
        aligned_features, aligned_returns = features.align(returns, join='inner', axis=0)
        
        if len(aligned_features) < 10:
            logger.warning("Insufficient data for model fitting")
            return
        
        # Scale features
        X = self.scaler.fit_transform(aligned_features.fillna(0))
        y = aligned_returns.values
        
        # Use Random Forest for factor model
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X, y)
        self.is_fitted = True
        
        logger.info(f"Factor model fitted with R² = {self.model.score(X, y):.3f}")
    
    async def predict_alpha(
        self,
        features: pd.DataFrame,
        context: Dict[str, Any]
    ) -> pd.Series:
        """Predict factor alpha"""
        
        if not self.is_fitted or self.model is None:
            logger.warning("Model not fitted")
            return pd.Series()
        
        # Scale features
        X = self.scaler.transform(features.fillna(0))
        
        # Predict
        predictions = self.model.predict(X)
        
        return pd.Series(predictions, index=features.index)


class AlphaResearcher:
    """
    Advanced alpha research framework
    
    Provides comprehensive alpha research capabilities including strategy
    development, backtesting, and alpha decay analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize alpha researcher"""
        self.config = config or {}
        
        # Strategy registry
        self._strategies = {}
        self._strategy_parameters = {}
        
        # Research tracking
        self._research_results = {}
        self._backtest_results = {}
        self._decay_analyses = {}
        
        # Threading
        self._lock = threading.Lock()
        
        # Performance tracking
        self._research_times = deque(maxlen=1000)
        
        # Initialize default strategies
        self._initialize_default_strategies()
        
        logger.info("AlphaResearcher initialized")
    
    def _initialize_default_strategies(self) -> None:
        """Initialize default alpha strategies"""
        
        # Momentum strategy
        momentum_params = AlphaParameters(
            alpha_id="momentum_alpha",
            alpha_type=AlphaType.MOMENTUM,
            frequency=AlphaFrequency.DAILY,
            lookback_periods=60,
            prediction_horizon=5
        )
        self.register_strategy(momentum_params, MomentumAlphaStrategy)
        
        # Mean reversion strategy
        mean_reversion_params = AlphaParameters(
            alpha_id="mean_reversion_alpha",
            alpha_type=AlphaType.MEAN_REVERSION,
            frequency=AlphaFrequency.DAILY,
            lookback_periods=50,
            prediction_horizon=10
        )
        self.register_strategy(mean_reversion_params, MeanReversionAlphaStrategy)
        
        # Factor strategy
        factor_params = AlphaParameters(
            alpha_id="factor_alpha",
            alpha_type=AlphaType.FACTOR_BASED,
            frequency=AlphaFrequency.WEEKLY,
            lookback_periods=252,
            prediction_horizon=21
        )
        self.register_strategy(factor_params, FactorAlphaStrategy)
        
        logger.info("Default alpha strategies initialized")
    
    def register_strategy(
        self,
        parameters: AlphaParameters,
        strategy_class: type
    ) -> None:
        """Register an alpha strategy"""
        
        strategy = strategy_class(parameters)
        
        with self._lock:
            self._strategies[parameters.alpha_id] = strategy
            self._strategy_parameters[parameters.alpha_id] = parameters
        
        logger.info(f"Registered alpha strategy: {parameters.alpha_id}")
    
    async def research_alpha(
        self,
        alpha_id: str,
        data: Dict[str, pd.DataFrame],
        returns_data: Dict[str, pd.Series],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Research alpha strategy"""
        
        start_time = time.time()
        context = context or {}
        
        try:
            strategy = self._strategies.get(alpha_id)
            if not strategy:
                logger.error(f"Strategy {alpha_id} not found")
                return {}
            
            if not strategy.validate_data(data):
                logger.error(f"Data validation failed for {alpha_id}")
                return {}
            
            # Generate features
            features = await strategy.generate_features(data, context)
            
            if features.empty:
                logger.warning(f"No features generated for {alpha_id}")
                return {}
            
            # Prepare returns data
            returns_series = pd.concat(returns_data.values())
            
            # Fit model
            await strategy.fit_model(features, returns_series, context)
            
            # Generate predictions
            predictions = await strategy.predict_alpha(features, context)
            
            # Create alpha signals
            signals = []
            for symbol in predictions.index:
                signal = AlphaSignal(
                    alpha_id=alpha_id,
                    symbol=symbol,
                    timestamp=datetime.now(),
                    signal_value=predictions[symbol],
                    confidence=0.8,  # Default confidence
                    quality_score=1.0
                )
                signals.append(signal)
            
            # Rank signals
            signals.sort(key=lambda x: x.signal_value, reverse=True)
            for i, signal in enumerate(signals):
                signal.signal_rank = i + 1
                signal.signal_percentile = (len(signals) - i) / len(signals)
            
            # Calculate research metrics
            research_result = {
                'alpha_id': alpha_id,
                'timestamp': datetime.now(),
                'num_signals': len(signals),
                'signal_range': (min(s.signal_value for s in signals), max(s.signal_value for s in signals)) if signals else (0, 0),
                'model_fitted': strategy.is_fitted,
                'features_generated': len(features.columns),
                'research_time_ms': (time.time() - start_time) * 1000,
                'signals': signals
            }
            
            # Store results
            with self._lock:
                self._research_results[alpha_id] = research_result
            
            # Record research time
            self._research_times.append(research_result['research_time_ms'])
            
            logger.info(f"Alpha research completed for {alpha_id}: {len(signals)} signals generated")
            
            return research_result
            
        except Exception as e:
            logger.error(f"Error researching alpha {alpha_id}: {e}")
            return {}
    
    async def backtest_alpha(
        self,
        alpha_id: str,
        data: Dict[str, pd.DataFrame],
        returns_data: Dict[str, pd.Series],
        context: Optional[Dict[str, Any]] = None,
        mode: BacktestMode = BacktestMode.WALK_FORWARD
    ) -> BacktestResult:
        """Backtest alpha strategy"""
        
        try:
            strategy = self._strategies.get(alpha_id)
            parameters = self._strategy_parameters.get(alpha_id)
            
            if not strategy or not parameters:
                logger.error(f"Strategy {alpha_id} not found")
                return self._create_empty_backtest_result(alpha_id)
            
            context = context or {}
            
            # Prepare data for backtesting
            start_date = parameters.research_start
            end_date = parameters.research_end
            
            # Run backtest based on mode
            if mode == BacktestMode.WALK_FORWARD:
                return await self._walk_forward_backtest(alpha_id, strategy, data, returns_data, context, start_date, end_date)
            elif mode == BacktestMode.EXPANDING_WINDOW:
                return await self._expanding_window_backtest(alpha_id, strategy, data, returns_data, context, start_date, end_date)
            else:
                return await self._rolling_window_backtest(alpha_id, strategy, data, returns_data, context, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error backtesting alpha {alpha_id}: {e}")
            return self._create_empty_backtest_result(alpha_id)
    
    async def _walk_forward_backtest(
        self,
        alpha_id: str,
        strategy: AlphaStrategy,
        data: Dict[str, pd.DataFrame],
        returns_data: Dict[str, pd.Series],
        context: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> BacktestResult:
        """Perform walk-forward backtest"""
        
        # Simplified walk-forward backtest
        training_period = 252  # 1 year
        rebalance_frequency = 21  # Monthly
        
        portfolio_returns = []
        positions_history = []
        
        # Get date range
        all_dates = sorted(set().union(*[df.index for df in data.values()]))
        test_dates = [d for d in all_dates if start_date <= d <= end_date]
        
        for i, test_date in enumerate(test_dates[training_period::rebalance_frequency]):
            try:
                # Prepare training data
                train_start_idx = max(0, i - training_period)
                i + training_period
                
                train_data = {}
                train_returns = {}
                
                for symbol in data.keys():
                    symbol_data = data[symbol]
                    symbol_returns = returns_data.get(symbol, pd.Series())
                    
                    # Get training period data
                    train_mask = (symbol_data.index >= test_dates[train_start_idx]) & (symbol_data.index < test_date)
                    train_data[symbol] = symbol_data[train_mask]
                    
                    if not symbol_returns.empty:
                        train_returns[symbol] = symbol_returns[train_mask]
                
                if not train_data:
                    continue
                
                # Generate features and fit model
                features = await strategy.generate_features(train_data, context)
                if features.empty:
                    continue
                
                combined_returns = pd.concat(train_returns.values())
                await strategy.fit_model(features, combined_returns, context)
                
                # Generate test predictions
                test_data = {}
                for symbol in data.keys():
                    symbol_data = data[symbol]
                    test_mask = symbol_data.index == test_date
                    test_data[symbol] = symbol_data[test_mask]
                
                test_features = await strategy.generate_features(test_data, context)
                if test_features.empty:
                    continue
                
                predictions = await strategy.predict_alpha(test_features, context)
                
                # Calculate portfolio return for this period
                if not predictions.empty:
                    # Equal weight top/bottom quintiles (long/short)
                    sorted_predictions = predictions.sort_values(ascending=False)
                    n_positions = min(len(sorted_predictions), 20)  # Top 20 positions
                    
                    long_symbols = sorted_predictions.head(n_positions // 2).index
                    short_symbols = sorted_predictions.tail(n_positions // 2).index
                    
                    period_return = 0
                    position_count = 0
                    
                    # Long positions
                    for symbol in long_symbols:
                        if symbol in returns_data:
                            symbol_returns = returns_data[symbol]
                            return_mask = symbol_returns.index > test_date
                            if return_mask.any():
                                next_return = symbol_returns[return_mask].iloc[0] if len(symbol_returns[return_mask]) > 0 else 0
                                period_return += next_return / n_positions
                                position_count += 1
                    
                    # Short positions
                    for symbol in short_symbols:
                        if symbol in returns_data:
                            symbol_returns = returns_data[symbol]
                            return_mask = symbol_returns.index > test_date
                            if return_mask.any():
                                next_return = symbol_returns[return_mask].iloc[0] if len(symbol_returns[return_mask]) > 0 else 0
                                period_return -= next_return / n_positions  # Short position
                                position_count += 1
                    
                    portfolio_returns.append(period_return)
                    
                    # Store positions
                    positions = {}
                    for symbol in long_symbols:
                        positions[symbol] = 1.0 / n_positions
                    for symbol in short_symbols:
                        positions[symbol] = -1.0 / n_positions
                    
                    positions_history.append({
                        'date': test_date,
                        'positions': positions,
                        'return': period_return
                    })
                
            except Exception as e:
                logger.error(f"Error in backtest period {test_date}: {e}")
                continue
        
        # Calculate performance metrics
        if not portfolio_returns:
            return self._create_empty_backtest_result(alpha_id)
        
        returns_series = pd.Series(portfolio_returns)
        
        # Performance calculations
        total_return = (1 + returns_series).prod() - 1
        annualized_return = ((1 + total_return) ** (252 / len(returns_series))) - 1
        volatility = returns_series.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Calculate drawdown
        cumulative_returns = (1 + returns_series).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Additional metrics
        positive_returns = returns_series[returns_series > 0]
        hit_rate = len(positive_returns) / len(returns_series) if len(returns_series) > 0 else 0
        
        # Create backtest result
        backtest_result = BacktestResult(
            alpha_id=alpha_id,
            backtest_id=f"backtest_{alpha_id}_{int(time.time())}",
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            information_ratio=sharpe_ratio,  # Simplified
            sortino_ratio=self._calculate_sortino_ratio(returns_series),
            calmar_ratio=annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0,
            hit_rate=hit_rate,
            average_holding_period=rebalance_frequency,
            turnover=0.5,  # Estimated
            returns_series=returns_series,
            start_date=start_date,
            end_date=end_date,
            num_periods=len(returns_series),
            num_securities=len(data)
        )
        
        # Store result
        with self._lock:
            self._backtest_results[alpha_id] = backtest_result
        
        logger.info(f"Backtest completed for {alpha_id}: Sharpe = {sharpe_ratio:.3f}, Return = {annualized_return:.1%}")
        
        return backtest_result
    
    async def _expanding_window_backtest(self, *args) -> BacktestResult:
        """Placeholder for expanding window backtest"""
        return self._create_empty_backtest_result(args[0])
    
    async def _rolling_window_backtest(self, *args) -> BacktestResult:
        """Placeholder for rolling window backtest"""
        return self._create_empty_backtest_result(args[0])
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio"""
        if returns.empty:
            return 0.0
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        
        if downside_std == 0:
            return 0.0
        
        excess_return = returns.mean() * 252  # Annualized
        return excess_return / (downside_std * np.sqrt(252))
    
    async def analyze_alpha_decay(
        self,
        alpha_id: str,
        signals_history: List[AlphaSignal],
        returns_data: Dict[str, pd.Series]
    ) -> AlphaDecayAnalysis:
        """Analyze alpha decay characteristics"""
        
        try:
            if not signals_history:
                return self._create_empty_decay_analysis(alpha_id)
            
            # Group signals by timestamp
            signals_by_date = defaultdict(list)
            for signal in signals_history:
                signals_by_date[signal.timestamp.date()].extend([signal])
            
            # Calculate signal autocorrelations
            signal_autocorrs = {}
            return_predictability = {}
            
            for lag in range(1, 21):  # 1 to 20 days
                correlations = []
                
                dates = sorted(signals_by_date.keys())
                for i in range(len(dates) - lag):
                    current_date = dates[i]
                    future_date = dates[i + lag]
                    
                    current_signals = {s.symbol: s.signal_value for s in signals_by_date[current_date]}
                    future_signals = {s.symbol: s.signal_value for s in signals_by_date[future_date]}
                    
                    common_symbols = set(current_signals.keys()) & set(future_signals.keys())
                    
                    if len(common_symbols) > 5:
                        current_values = [current_signals[s] for s in common_symbols]
                        future_values = [future_signals[s] for s in common_symbols]
                        
                        correlation = np.corrcoef(current_values, future_values)[0, 1]
                        if not np.isnan(correlation):
                            correlations.append(correlation)
                
                if correlations:
                    signal_autocorrs[lag] = np.mean(correlations)
                else:
                    signal_autocorrs[lag] = 0.0
            
            # Calculate decay half-life
            decay_half_life = self._calculate_decay_half_life(signal_autocorrs)
            
            # Calculate optimal holding period
            optimal_holding_period = self._find_optimal_holding_period(signal_autocorrs, return_predictability)
            
            # Create decay analysis
            decay_analysis = AlphaDecayAnalysis(
                alpha_id=alpha_id,
                analysis_date=datetime.now(),
                decay_half_life_days=decay_half_life,
                decay_rate_per_day=np.log(0.5) / decay_half_life if decay_half_life > 0 else 0,
                optimal_holding_period=optimal_holding_period,
                signal_autocorrelations=signal_autocorrs,
                return_predictability=return_predictability,
                optimal_rebalance_frequency=AlphaFrequency.WEEKLY,  # Default
                frequency_performance={},
                bull_market_decay=decay_half_life * 0.8,  # Faster in bull markets
                bear_market_decay=decay_half_life * 1.2,  # Slower in bear markets
                high_vol_decay=decay_half_life * 0.7,     # Faster in high vol
                low_vol_decay=decay_half_life * 1.3,      # Slower in low vol
                recommended_holding_period=max(1, optimal_holding_period),
                recommended_decay_adjustment=1.0
            )
            
            # Store analysis
            with self._lock:
                self._decay_analyses[alpha_id] = decay_analysis
            
            logger.info(f"Alpha decay analysis completed for {alpha_id}: half-life = {decay_half_life:.1f} days")
            
            return decay_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing alpha decay for {alpha_id}: {e}")
            return self._create_empty_decay_analysis(alpha_id)
    
    def _calculate_decay_half_life(self, autocorrelations: Dict[int, float]) -> float:
        """Calculate decay half-life from autocorrelations"""
        
        if not autocorrelations:
            return 5.0  # Default 5 days
        
        # Find when autocorrelation drops to 50% of initial value
        initial_corr = autocorrelations.get(1, 1.0)
        target_corr = initial_corr * 0.5
        
        for lag, corr in autocorrelations.items():
            if corr <= target_corr:
                return float(lag)
        
        return 10.0  # Default if not found
    
    def _find_optimal_holding_period(
        self,
        autocorrelations: Dict[int, float],
        return_predictability: Dict[int, float]
    ) -> int:
        """Find optimal holding period"""
        
        if not autocorrelations:
            return 5
        
        # Find lag where autocorrelation becomes insignificant (<0.1)
        for lag, corr in autocorrelations.items():
            if abs(corr) < 0.1:
                return lag
        
        return 10  # Default
    
    def _create_empty_backtest_result(self, alpha_id: str) -> BacktestResult:
        """Create empty backtest result"""
        return BacktestResult(
            alpha_id=alpha_id,
            backtest_id=f"empty_{alpha_id}_{int(time.time())}",
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            information_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            hit_rate=0.0,
            average_holding_period=0.0,
            turnover=0.0
        )
    
    def _create_empty_decay_analysis(self, alpha_id: str) -> AlphaDecayAnalysis:
        """Create empty decay analysis"""
        return AlphaDecayAnalysis(
            alpha_id=alpha_id,
            analysis_date=datetime.now(),
            decay_half_life_days=5.0,
            decay_rate_per_day=0.1,
            optimal_holding_period=5,
            signal_autocorrelations={},
            return_predictability={},
            optimal_rebalance_frequency=AlphaFrequency.WEEKLY,
            frequency_performance={},
            bull_market_decay=5.0,
            bear_market_decay=5.0,
            high_vol_decay=5.0,
            low_vol_decay=5.0,
            recommended_holding_period=5,
            recommended_decay_adjustment=1.0
        )
    
    def get_research_results(self, alpha_id: Optional[str] = None) -> Dict[str, Any]:
        """Get research results"""
        with self._lock:
            if alpha_id:
                return self._research_results.get(alpha_id, {})
            else:
                return dict(self._research_results)
    
    def get_backtest_results(self, alpha_id: Optional[str] = None) -> Dict[str, BacktestResult]:
        """Get backtest results"""
        with self._lock:
            if alpha_id:
                result = self._backtest_results.get(alpha_id)
                return {alpha_id: result} if result else {}
            else:
                return dict(self._backtest_results)
    
    def get_decay_analyses(self, alpha_id: Optional[str] = None) -> Dict[str, AlphaDecayAnalysis]:
        """Get decay analyses"""
        with self._lock:
            if alpha_id:
                analysis = self._decay_analyses.get(alpha_id)
                return {alpha_id: analysis} if analysis else {}
            else:
                return dict(self._decay_analyses)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        
        with self._lock:
            avg_research_time = np.mean(self._research_times) if self._research_times else 0
            
            return {
                'registered_strategies': len(self._strategies),
                'completed_research': len(self._research_results),
                'completed_backtests': len(self._backtest_results),
                'completed_decay_analyses': len(self._decay_analyses),
                'average_research_time_ms': avg_research_time,
                'strategy_types': [params.alpha_type.value for params in self._strategy_parameters.values()]
            }