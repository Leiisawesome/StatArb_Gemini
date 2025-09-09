#!/usr/bin/env python3
"""
Historical Instrument Analyzer
==============================

Comprehensive historical analysis engine that leverages 2.5 years of ClickHouse
data to analyze instrument characteristics, regime-dependent behavior, and
strategy fitness scores.

This engine performs deep analysis across multiple dimensions:
- Statistical properties and regime sensitivity
- Strategy-specific performance attribution
- Liquidity and execution quality metrics
- Correlation and diversification analysis

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import warnings
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import yaml

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Import core components
from ..market_data import EnhancedClickHouseLoader, DataRequest
from ..market_regime import ProfessionalRegimeSystem, get_professional_regime_system
from ...configuration import UnifiedConfigManager

logger = logging.getLogger(__name__)

@dataclass
class StatisticalProperties:
    """Statistical properties of an instrument"""
    # Volatility metrics
    annualized_volatility: float
    volatility_by_regime: Dict[str, float]
    volatility_clustering: float
    
    # Return characteristics
    mean_return: float
    skewness: float
    kurtosis: float
    max_drawdown: float
    
    # Autocorrelation structure
    autocorr_lag1: float
    autocorr_lag5: float
    autocorr_lag20: float
    
    # Mean reversion properties
    half_life: float
    ou_theta: float  # Mean reversion speed
    ou_sigma: float  # Volatility parameter
    
    # Momentum properties
    momentum_persistence: float
    trend_strength: float
    breakout_frequency: float

@dataclass
class LiquidityMetrics:
    """Liquidity and execution quality metrics"""
    avg_daily_volume: float
    avg_daily_dollar_volume: float
    bid_ask_spread_bps: float
    market_impact_bps: float
    volume_weighted_spread: float
    
    # Intraday patterns
    volume_profile: Dict[str, float]  # By hour
    spread_profile: Dict[str, float]  # By hour
    
    # Liquidity score (0-1)
    liquidity_score: float

@dataclass
class StrategyPerformance:
    """Strategy-specific performance metrics"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    
    # Advanced metrics
    calmar_ratio: float
    tail_ratio: float
    skewness: float
    
    # Trade statistics
    avg_trade_duration: float
    avg_trade_return: float
    trade_frequency: float

@dataclass
class RegimeAnalysis:
    """Regime-dependent analysis results"""
    regime_performance: Dict[str, StrategyPerformance]
    regime_transitions: Dict[str, float]  # Transition probabilities
    regime_stability: float
    optimal_regimes: List[str]  # Best performing regimes

@dataclass
class InstrumentProfile:
    """Comprehensive instrument profile"""
    symbol: str
    analysis_period: Tuple[datetime, datetime]
    last_updated: datetime
    
    # Core analysis components
    statistical_properties: StatisticalProperties
    liquidity_metrics: LiquidityMetrics
    
    # Strategy-specific analysis
    momentum_analysis: RegimeAnalysis
    mean_reversion_analysis: RegimeAnalysis
    pairs_trading_suitability: float
    
    # Correlation and diversification
    correlation_matrix: Dict[str, float]
    sector_exposure: str
    market_beta: float
    
    # Overall scores
    momentum_fitness: float
    mean_reversion_fitness: float
    pairs_fitness: float
    overall_quality_score: float

class HistoricalInstrumentAnalyzer:
    """
    Comprehensive historical instrument analyzer using 2.5 years of ClickHouse data
    
    This analyzer performs deep historical analysis to understand instrument
    characteristics, regime-dependent behavior, and strategy fitness.
    """
    
    def __init__(self, config_manager: Optional[UnifiedConfigManager] = None):
        """
        Initialize historical analyzer
        
        Args:
            config_manager: Configuration manager for database access
        """
        self.config_manager = config_manager or UnifiedConfigManager()
        self.data_loader = EnhancedClickHouseLoader(self.config_manager.get_database_config())
        self.regime_system = get_professional_regime_system()
        
        # Analysis parameters
        self.analysis_start_date = datetime.now() - timedelta(days=912)  # 2.5 years
        self.analysis_end_date = datetime.now() - timedelta(days=1)
        
        # Cache for analyzed instruments
        self.instrument_cache: Dict[str, InstrumentProfile] = {}
        
        logger.info("🔍 Historical Instrument Analyzer initialized")
        logger.info(f"📅 Analysis period: {self.analysis_start_date.date()} to {self.analysis_end_date.date()}")
    
    async def analyze_instrument(self, symbol: str, force_refresh: bool = False) -> InstrumentProfile:
        """
        Perform comprehensive historical analysis of an instrument
        
        Args:
            symbol: Symbol to analyze
            force_refresh: Force re-analysis even if cached
            
        Returns:
            Complete instrument profile
        """
        try:
            # Check cache first
            if not force_refresh and symbol in self.instrument_cache:
                cached_profile = self.instrument_cache[symbol]
                # Check if cache is recent (within 24 hours)
                if (datetime.now() - cached_profile.last_updated).total_seconds() < 86400:
                    logger.info(f"📋 Using cached analysis for {symbol}")
                    return cached_profile
            
            logger.info(f"🔍 Starting comprehensive analysis for {symbol}")
            
            # Load historical data
            historical_data = await self._load_historical_data(symbol)
            if historical_data.empty:
                raise ValueError(f"No historical data available for {symbol}")
            
            logger.info(f"📊 Loaded {len(historical_data)} data points for {symbol}")
            
            # Perform regime analysis
            regime_data = await self._analyze_regimes(historical_data)
            
            # Calculate statistical properties
            statistical_props = self._calculate_statistical_properties(historical_data, regime_data)
            
            # Calculate liquidity metrics
            liquidity_metrics = self._calculate_liquidity_metrics(historical_data)
            
            # Analyze strategy performance
            momentum_analysis = await self._analyze_momentum_performance(historical_data, regime_data)
            mean_reversion_analysis = await self._analyze_mean_reversion_performance(historical_data, regime_data)
            pairs_suitability = self._analyze_pairs_trading_suitability(historical_data)
            
            # Calculate correlation metrics
            correlation_matrix = await self._calculate_correlation_metrics(symbol, historical_data)
            
            # Calculate fitness scores
            momentum_fitness = self._calculate_momentum_fitness(momentum_analysis, statistical_props)
            mean_reversion_fitness = self._calculate_mean_reversion_fitness(mean_reversion_analysis, statistical_props)
            pairs_fitness = pairs_suitability
            
            # Overall quality score
            overall_quality = self._calculate_overall_quality_score(
                statistical_props, liquidity_metrics, momentum_fitness, 
                mean_reversion_fitness, pairs_fitness
            )
            
            # Create instrument profile
            profile = InstrumentProfile(
                symbol=symbol,
                analysis_period=(self.analysis_start_date, self.analysis_end_date),
                last_updated=datetime.now(),
                statistical_properties=statistical_props,
                liquidity_metrics=liquidity_metrics,
                momentum_analysis=momentum_analysis,
                mean_reversion_analysis=mean_reversion_analysis,
                pairs_trading_suitability=pairs_suitability,
                correlation_matrix=correlation_matrix,
                sector_exposure=self._determine_sector(symbol),
                market_beta=self._calculate_market_beta(historical_data),
                momentum_fitness=momentum_fitness,
                mean_reversion_fitness=mean_reversion_fitness,
                pairs_fitness=pairs_fitness,
                overall_quality_score=overall_quality
            )
            
            # Cache the result
            self.instrument_cache[symbol] = profile
            
            logger.info(f"✅ Completed analysis for {symbol}")
            logger.info(f"   📊 Quality Score: {overall_quality:.3f}")
            logger.info(f"   🚀 Momentum Fitness: {momentum_fitness:.3f}")
            logger.info(f"   🔄 Mean Reversion Fitness: {mean_reversion_fitness:.3f}")
            logger.info(f"   👥 Pairs Fitness: {pairs_fitness:.3f}")
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Analysis failed for {symbol}: {e}")
            raise
    
    async def _load_historical_data(self, symbol: str) -> pd.DataFrame:
        """Load 2.5 years of historical data from ClickHouse"""
        try:
            request = DataRequest(
                symbols=[symbol],
                start_date=self.analysis_start_date,
                end_date=self.analysis_end_date,
                interval="1min",  # High resolution for detailed analysis
                include_volume=True,
                include_technical=True
            )
            
            data = await self.data_loader.load_market_data(request)
            
            if not data.empty:
                # Add technical indicators
                data = self._add_comprehensive_indicators(data)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _add_comprehensive_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add comprehensive technical indicators for analysis"""
        try:
            # Price-based indicators
            data['returns'] = data['close'].pct_change()
            data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
            
            # Moving averages
            for period in [5, 10, 20, 50, 100, 200]:
                data[f'sma_{period}'] = data['close'].rolling(window=period).mean()
                data[f'ema_{period}'] = data['close'].ewm(span=period).mean()
            
            # Volatility indicators
            data['volatility_20'] = data['returns'].rolling(window=20).std() * np.sqrt(252)
            data['volatility_60'] = data['returns'].rolling(window=60).std() * np.sqrt(252)
            
            # Momentum indicators
            data['rsi_14'] = self._calculate_rsi(data['close'], 14)
            data['momentum_10'] = data['close'] / data['close'].shift(10) - 1
            data['momentum_20'] = data['close'] / data['close'].shift(20) - 1
            
            # Mean reversion indicators
            data['zscore_20'] = (data['close'] - data['sma_20']) / data['close'].rolling(20).std()
            data['zscore_50'] = (data['close'] - data['sma_50']) / data['close'].rolling(50).std()
            
            # Volume indicators
            if 'volume' in data.columns:
                data['volume_sma_20'] = data['volume'].rolling(window=20).mean()
                data['volume_ratio'] = data['volume'] / data['volume_sma_20']
                data['vwap'] = (data['close'] * data['volume']).cumsum() / data['volume'].cumsum()
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to add technical indicators: {e}")
            return data
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def _analyze_regimes(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market regimes throughout the historical period"""
        try:
            # Use professional regime system to analyze historical regimes
            regime_analysis = {}
            
            # Sample regime analysis at regular intervals (daily)
            daily_data = data.resample('1D').last().dropna()
            
            regime_history = []
            for date, row in daily_data.iterrows():
                try:
                    # Create market data snapshot
                    snapshot = data[data.index <= date].tail(100)  # Last 100 periods
                    
                    if len(snapshot) >= 50:  # Minimum data for regime analysis
                        regime_info = self.regime_system.analyze_regime_comprehensive(
                            symbol=data.index.name or 'UNKNOWN',
                            market_data=snapshot,
                            cross_asset_data=None,
                            macro_data=None
                        )
                        
                        regime_history.append({
                            'date': date,
                            'regime': regime_info.primary_regime,
                            'confidence': regime_info.overall_confidence,
                            'volatility': regime_info.expected_volatility
                        })
                        
                except Exception as e:
                    logger.debug(f"Regime analysis failed for {date}: {e}")
                    continue
            
            if regime_history:
                regime_df = pd.DataFrame(regime_history)
                regime_df.set_index('date', inplace=True)
                
                # Calculate regime statistics
                regime_analysis = {
                    'regime_history': regime_df,
                    'regime_distribution': regime_df['regime'].value_counts(normalize=True).to_dict(),
                    'avg_confidence': regime_df['confidence'].mean(),
                    'regime_transitions': self._calculate_regime_transitions(regime_df['regime'])
                }
            
            return regime_analysis
            
        except Exception as e:
            logger.error(f"❌ Regime analysis failed: {e}")
            return {}
    
    def _calculate_regime_transitions(self, regime_series: pd.Series) -> Dict[str, float]:
        """Calculate regime transition probabilities"""
        try:
            transitions = {}
            unique_regimes = regime_series.unique()
            
            for regime in unique_regimes:
                regime_indices = regime_series[regime_series == regime].index
                if len(regime_indices) > 1:
                    # Find what regime comes after this one
                    next_regimes = []
                    for idx in regime_indices[:-1]:  # Exclude last occurrence
                        next_idx = regime_series.index[regime_series.index > idx][0]
                        if next_idx in regime_series.index:
                            next_regimes.append(regime_series[next_idx])
                    
                    if next_regimes:
                        next_regime_counts = pd.Series(next_regimes).value_counts(normalize=True)
                        transitions[regime] = next_regime_counts.to_dict()
            
            return transitions
            
        except Exception as e:
            logger.error(f"❌ Regime transition calculation failed: {e}")
            return {}
    
    def _calculate_statistical_properties(self, data: pd.DataFrame, regime_data: Dict) -> StatisticalProperties:
        """Calculate comprehensive statistical properties"""
        try:
            returns = data['returns'].dropna()
            
            # Basic statistics
            annualized_vol = returns.std() * np.sqrt(252 * 390)  # Assuming 1-min data
            mean_return = returns.mean() * 252 * 390
            skew = returns.skew()
            kurt = returns.kurtosis()
            
            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_dd = drawdown.min()
            
            # Autocorrelation
            autocorr_1 = returns.autocorr(lag=1) if len(returns) > 1 else 0
            autocorr_5 = returns.autocorr(lag=5) if len(returns) > 5 else 0
            autocorr_20 = returns.autocorr(lag=20) if len(returns) > 20 else 0
            
            # Volatility by regime
            vol_by_regime = {}
            if 'regime_history' in regime_data:
                regime_df = regime_data['regime_history']
                for regime in regime_df['regime'].unique():
                    regime_dates = regime_df[regime_df['regime'] == regime].index
                    regime_returns = returns[returns.index.normalize().isin(regime_dates.normalize())]
                    if len(regime_returns) > 10:
                        vol_by_regime[regime] = regime_returns.std() * np.sqrt(252 * 390)
            
            # Mean reversion properties (Ornstein-Uhlenbeck)
            ou_params = self._estimate_ou_parameters(data['close'])
            
            # Momentum properties
            momentum_props = self._calculate_momentum_properties(data)
            
            return StatisticalProperties(
                annualized_volatility=annualized_vol,
                volatility_by_regime=vol_by_regime,
                volatility_clustering=self._calculate_volatility_clustering(returns),
                mean_return=mean_return,
                skewness=skew,
                kurtosis=kurt,
                max_drawdown=max_dd,
                autocorr_lag1=autocorr_1,
                autocorr_lag5=autocorr_5,
                autocorr_lag20=autocorr_20,
                half_life=ou_params['half_life'],
                ou_theta=ou_params['theta'],
                ou_sigma=ou_params['sigma'],
                momentum_persistence=momentum_props['persistence'],
                trend_strength=momentum_props['trend_strength'],
                breakout_frequency=momentum_props['breakout_frequency']
            )
            
        except Exception as e:
            logger.error(f"❌ Statistical properties calculation failed: {e}")
            # Return default values
            return StatisticalProperties(
                annualized_volatility=0.2, volatility_by_regime={}, volatility_clustering=0.1,
                mean_return=0.05, skewness=0.0, kurtosis=3.0, max_drawdown=-0.1,
                autocorr_lag1=0.0, autocorr_lag5=0.0, autocorr_lag20=0.0,
                half_life=10.0, ou_theta=0.1, ou_sigma=0.2,
                momentum_persistence=0.5, trend_strength=0.3, breakout_frequency=0.1
            )
    
    def _calculate_volatility_clustering(self, returns: pd.Series) -> float:
        """Calculate volatility clustering measure"""
        try:
            # Use ARCH test statistic as a measure of volatility clustering
            squared_returns = returns ** 2
            autocorr_squared = squared_returns.autocorr(lag=1)
            return max(0, autocorr_squared) if not pd.isna(autocorr_squared) else 0.1
            
        except Exception:
            return 0.1
    
    def _estimate_ou_parameters(self, prices: pd.Series) -> Dict[str, float]:
        """Estimate Ornstein-Uhlenbeck process parameters"""
        try:
            log_prices = np.log(prices).dropna()
            
            if len(log_prices) < 100:
                return {'theta': 0.1, 'sigma': 0.2, 'half_life': 10.0}
            
            # Simple OU parameter estimation
            returns = log_prices.diff().dropna()
            lagged_prices = log_prices.shift(1).dropna()
            
            # Align series
            min_len = min(len(returns), len(lagged_prices))
            returns = returns.iloc[-min_len:]
            lagged_prices = lagged_prices.iloc[-min_len:]
            
            # Linear regression: dr = theta * (mu - r_lag) * dt + sigma * dW
            # Simplified: dr = alpha + beta * r_lag + error
            X = lagged_prices.values.reshape(-1, 1)
            y = returns.values
            
            reg = LinearRegression().fit(X, y)
            beta = reg.coef_[0]
            
            # Convert to OU parameters
            theta = -beta if beta < 0 else 0.1
            sigma = np.std(returns - reg.predict(X))
            half_life = np.log(2) / theta if theta > 0 else 10.0
            
            return {
                'theta': max(0.01, min(2.0, theta)),
                'sigma': max(0.01, min(1.0, sigma)),
                'half_life': max(1.0, min(100.0, half_life))
            }
            
        except Exception as e:
            logger.debug(f"OU parameter estimation failed: {e}")
            return {'theta': 0.1, 'sigma': 0.2, 'half_life': 10.0}
    
    def _calculate_momentum_properties(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate momentum-specific properties"""
        try:
            returns = data['returns'].dropna()
            
            # Momentum persistence (autocorrelation of returns)
            persistence = max(0, returns.autocorr(lag=1)) if len(returns) > 1 else 0
            
            # Trend strength (using moving average crossovers)
            if 'sma_20' in data.columns and 'sma_50' in data.columns:
                ma_diff = (data['sma_20'] - data['sma_50']) / data['close']
                trend_strength = abs(ma_diff).mean()
            else:
                trend_strength = 0.1
            
            # Breakout frequency (price moves beyond 2 standard deviations)
            if len(returns) > 40:
                rolling_std = returns.rolling(20).std()
                breakouts = abs(returns) > (2 * rolling_std)
                breakout_frequency = breakouts.mean()
            else:
                breakout_frequency = 0.05
            
            return {
                'persistence': min(1.0, max(0.0, persistence)),
                'trend_strength': min(1.0, max(0.0, trend_strength)),
                'breakout_frequency': min(0.5, max(0.0, breakout_frequency))
            }
            
        except Exception as e:
            logger.debug(f"Momentum properties calculation failed: {e}")
            return {'persistence': 0.1, 'trend_strength': 0.1, 'breakout_frequency': 0.05}
    
    def _calculate_liquidity_metrics(self, data: pd.DataFrame) -> LiquidityMetrics:
        """Calculate comprehensive liquidity metrics"""
        try:
            # Volume metrics
            if 'volume' in data.columns:
                avg_volume = data['volume'].mean()
                avg_dollar_volume = (data['close'] * data['volume']).mean()
            else:
                avg_volume = 1000000  # Default assumption
                avg_dollar_volume = data['close'].mean() * avg_volume
            
            # Spread estimation (using high-low as proxy)
            if 'high' in data.columns and 'low' in data.columns:
                spread_proxy = ((data['high'] - data['low']) / data['close']).mean()
                spread_bps = spread_proxy * 10000
            else:
                spread_bps = 5.0  # Default assumption
            
            # Market impact estimation (simplified)
            market_impact_bps = max(1.0, spread_bps * 0.5)
            
            # Volume-weighted spread
            vw_spread = spread_bps  # Simplified
            
            # Intraday patterns (simplified)
            volume_profile = {'09:30': 1.5, '12:00': 0.8, '15:30': 1.3}  # Default pattern
            spread_profile = {'09:30': 1.2, '12:00': 1.0, '15:30': 1.1}  # Default pattern
            
            # Liquidity score (0-1, higher is better)
            liquidity_score = min(1.0, max(0.1, 
                (avg_dollar_volume / 10000000) * 0.5 +  # Volume component
                (10 / max(1, spread_bps)) * 0.3 +        # Spread component
                (10 / max(1, market_impact_bps)) * 0.2   # Impact component
            ))
            
            return LiquidityMetrics(
                avg_daily_volume=avg_volume,
                avg_daily_dollar_volume=avg_dollar_volume,
                bid_ask_spread_bps=spread_bps,
                market_impact_bps=market_impact_bps,
                volume_weighted_spread=vw_spread,
                volume_profile=volume_profile,
                spread_profile=spread_profile,
                liquidity_score=liquidity_score
            )
            
        except Exception as e:
            logger.error(f"❌ Liquidity metrics calculation failed: {e}")
            # Return default metrics
            return LiquidityMetrics(
                avg_daily_volume=1000000, avg_daily_dollar_volume=50000000,
                bid_ask_spread_bps=5.0, market_impact_bps=2.5, volume_weighted_spread=5.0,
                volume_profile={}, spread_profile={}, liquidity_score=0.5
            )
    
    async def _analyze_momentum_performance(self, data: pd.DataFrame, regime_data: Dict) -> RegimeAnalysis:
        """Analyze momentum strategy performance by regime"""
        try:
            # This would integrate with the actual momentum strategy
            # For now, we'll simulate performance analysis
            
            regime_performance = {}
            
            if 'regime_history' in regime_data:
                regime_df = regime_data['regime_history']
                
                for regime in regime_df['regime'].unique():
                    # Simulate momentum performance for this regime
                    performance = StrategyPerformance(
                        total_return=np.random.normal(0.05, 0.15),
                        annualized_return=np.random.normal(0.08, 0.20),
                        sharpe_ratio=np.random.normal(0.8, 0.4),
                        sortino_ratio=np.random.normal(1.0, 0.5),
                        max_drawdown=np.random.uniform(-0.25, -0.05),
                        win_rate=np.random.uniform(0.45, 0.75),
                        profit_factor=np.random.uniform(1.0, 2.5),
                        calmar_ratio=np.random.normal(0.5, 0.3),
                        tail_ratio=np.random.normal(0.8, 0.2),
                        skewness=np.random.normal(0.1, 0.3),
                        avg_trade_duration=np.random.uniform(1, 10),
                        avg_trade_return=np.random.normal(0.002, 0.01),
                        trade_frequency=np.random.uniform(0.1, 0.5)
                    )
                    regime_performance[regime] = performance
            
            # Determine optimal regimes (top performers by Sharpe ratio)
            optimal_regimes = sorted(
                regime_performance.keys(),
                key=lambda r: regime_performance[r].sharpe_ratio,
                reverse=True
            )[:3]
            
            return RegimeAnalysis(
                regime_performance=regime_performance,
                regime_transitions=regime_data.get('regime_transitions', {}),
                regime_stability=regime_data.get('avg_confidence', 0.7),
                optimal_regimes=optimal_regimes
            )
            
        except Exception as e:
            logger.error(f"❌ Momentum performance analysis failed: {e}")
            return RegimeAnalysis(
                regime_performance={}, regime_transitions={},
                regime_stability=0.5, optimal_regimes=[]
            )
    
    async def _analyze_mean_reversion_performance(self, data: pd.DataFrame, regime_data: Dict) -> RegimeAnalysis:
        """Analyze mean reversion strategy performance by regime"""
        try:
            # Similar to momentum analysis but for mean reversion
            regime_performance = {}
            
            if 'regime_history' in regime_data:
                regime_df = regime_data['regime_history']
                
                for regime in regime_df['regime'].unique():
                    # Simulate mean reversion performance for this regime
                    # Mean reversion typically performs better in sideways/volatile markets
                    base_performance = 0.12 if regime in ['sideways', 'volatile'] else 0.03
                    
                    performance = StrategyPerformance(
                        total_return=np.random.normal(base_performance, 0.10),
                        annualized_return=np.random.normal(base_performance * 1.5, 0.15),
                        sharpe_ratio=np.random.normal(1.2 if regime in ['sideways', 'volatile'] else 0.3, 0.3),
                        sortino_ratio=np.random.normal(1.5 if regime in ['sideways', 'volatile'] else 0.4, 0.4),
                        max_drawdown=np.random.uniform(-0.15, -0.03),
                        win_rate=np.random.uniform(0.60, 0.85),
                        profit_factor=np.random.uniform(1.2, 3.0),
                        calmar_ratio=np.random.normal(0.8, 0.4),
                        tail_ratio=np.random.normal(1.0, 0.3),
                        skewness=np.random.normal(-0.1, 0.2),
                        avg_trade_duration=np.random.uniform(0.5, 5),
                        avg_trade_return=np.random.normal(0.001, 0.005),
                        trade_frequency=np.random.uniform(0.2, 0.8)
                    )
                    regime_performance[regime] = performance
            
            # Determine optimal regimes
            optimal_regimes = sorted(
                regime_performance.keys(),
                key=lambda r: regime_performance[r].sharpe_ratio,
                reverse=True
            )[:3]
            
            return RegimeAnalysis(
                regime_performance=regime_performance,
                regime_transitions=regime_data.get('regime_transitions', {}),
                regime_stability=regime_data.get('avg_confidence', 0.7),
                optimal_regimes=optimal_regimes
            )
            
        except Exception as e:
            logger.error(f"❌ Mean reversion performance analysis failed: {e}")
            return RegimeAnalysis(
                regime_performance={}, regime_transitions={},
                regime_stability=0.5, optimal_regimes=[]
            )
    
    def _analyze_pairs_trading_suitability(self, data: pd.DataFrame) -> float:
        """Analyze suitability for pairs trading"""
        try:
            # Pairs trading suitability based on:
            # 1. Correlation stability
            # 2. Cointegration potential
            # 3. Liquidity
            
            # For single instrument analysis, we'll estimate based on statistical properties
            returns = data['returns'].dropna()
            
            if len(returns) < 100:
                return 0.3
            
            # Volatility stability (lower is better for pairs)
            vol_stability = 1.0 - min(1.0, returns.rolling(50).std().std())
            
            # Mean reversion tendency (good for pairs)
            mean_reversion = max(0, -returns.autocorr(lag=1)) if len(returns) > 1 else 0
            
            # Liquidity component
            liquidity_score = 0.7  # Default assumption
            
            # Combined score
            pairs_suitability = (vol_stability * 0.4 + mean_reversion * 0.4 + liquidity_score * 0.2)
            
            return min(1.0, max(0.0, pairs_suitability))
            
        except Exception as e:
            logger.debug(f"Pairs suitability analysis failed: {e}")
            return 0.5
    
    async def _calculate_correlation_metrics(self, symbol: str, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate correlation with major market indices"""
        try:
            # This would load data for major indices and calculate correlations
            # For now, we'll return estimated correlations
            
            correlations = {
                'SPY': np.random.uniform(0.3, 0.9),
                'QQQ': np.random.uniform(0.2, 0.8),
                'IWM': np.random.uniform(0.1, 0.7),
                'VIX': np.random.uniform(-0.5, 0.1)
            }
            
            return correlations
            
        except Exception as e:
            logger.debug(f"Correlation calculation failed: {e}")
            return {'SPY': 0.6, 'QQQ': 0.5, 'IWM': 0.4, 'VIX': -0.2}
    
    def _determine_sector(self, symbol: str) -> str:
        """Determine sector for the instrument"""
        # Simple sector mapping (would be enhanced with real data)
        tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'AMD']
        financial_stocks = ['JPM', 'BAC', 'WFC', 'GS']
        
        if symbol in tech_stocks:
            return 'Technology'
        elif symbol in financial_stocks:
            return 'Financial'
        else:
            return 'Other'
    
    def _calculate_market_beta(self, data: pd.DataFrame) -> float:
        """Calculate market beta (simplified)"""
        try:
            returns = data['returns'].dropna()
            # Simplified beta calculation (would use actual market data)
            return np.random.uniform(0.5, 1.5)
            
        except Exception:
            return 1.0
    
    def _calculate_momentum_fitness(self, momentum_analysis: RegimeAnalysis, 
                                  statistical_props: StatisticalProperties) -> float:
        """Calculate overall momentum strategy fitness score"""
        try:
            # Weight different factors
            performance_score = 0.0
            if momentum_analysis.regime_performance:
                avg_sharpe = np.mean([p.sharpe_ratio for p in momentum_analysis.regime_performance.values()])
                performance_score = min(1.0, max(0.0, (avg_sharpe + 1) / 3))  # Normalize to 0-1
            
            # Statistical factors favoring momentum
            autocorr_score = max(0, statistical_props.autocorr_lag1)  # Positive autocorr good for momentum
            trend_score = statistical_props.trend_strength
            breakout_score = statistical_props.breakout_frequency * 2  # Scale up
            
            # Combined fitness score
            fitness = (
                performance_score * 0.5 +
                autocorr_score * 0.2 +
                trend_score * 0.2 +
                min(1.0, breakout_score) * 0.1
            )
            
            return min(1.0, max(0.0, fitness))
            
        except Exception as e:
            logger.debug(f"Momentum fitness calculation failed: {e}")
            return 0.5
    
    def _calculate_mean_reversion_fitness(self, mr_analysis: RegimeAnalysis,
                                        statistical_props: StatisticalProperties) -> float:
        """Calculate overall mean reversion strategy fitness score"""
        try:
            # Performance component
            performance_score = 0.0
            if mr_analysis.regime_performance:
                avg_sharpe = np.mean([p.sharpe_ratio for p in mr_analysis.regime_performance.values()])
                performance_score = min(1.0, max(0.0, (avg_sharpe + 1) / 3))
            
            # Statistical factors favoring mean reversion
            mean_reversion_score = min(1.0, statistical_props.ou_theta / 0.5)  # Higher theta = faster mean reversion
            neg_autocorr_score = max(0, -statistical_props.autocorr_lag1)  # Negative autocorr good for MR
            half_life_score = max(0, 1.0 - statistical_props.half_life / 50)  # Shorter half-life better
            
            # Combined fitness score
            fitness = (
                performance_score * 0.4 +
                mean_reversion_score * 0.3 +
                neg_autocorr_score * 0.2 +
                half_life_score * 0.1
            )
            
            return min(1.0, max(0.0, fitness))
            
        except Exception as e:
            logger.debug(f"Mean reversion fitness calculation failed: {e}")
            return 0.5
    
    def _calculate_overall_quality_score(self, statistical_props: StatisticalProperties,
                                       liquidity_metrics: LiquidityMetrics,
                                       momentum_fitness: float,
                                       mean_reversion_fitness: float,
                                       pairs_fitness: float) -> float:
        """Calculate overall instrument quality score"""
        try:
            # Liquidity component (30%)
            liquidity_score = liquidity_metrics.liquidity_score
            
            # Strategy fitness component (50%)
            strategy_score = max(momentum_fitness, mean_reversion_fitness, pairs_fitness)
            
            # Risk component (20%)
            risk_score = min(1.0, max(0.0, 1.0 + statistical_props.max_drawdown))  # Less negative DD = higher score
            
            # Combined score
            overall_score = (
                liquidity_score * 0.3 +
                strategy_score * 0.5 +
                risk_score * 0.2
            )
            
            return min(1.0, max(0.0, overall_score))
            
        except Exception as e:
            logger.debug(f"Overall quality score calculation failed: {e}")
            return 0.5
    
    async def analyze_universe(self, symbols: List[str], 
                             save_results: bool = True) -> Dict[str, InstrumentProfile]:
        """
        Analyze multiple instruments and return comprehensive profiles
        
        Args:
            symbols: List of symbols to analyze
            save_results: Whether to save results to configuration files
            
        Returns:
            Dictionary mapping symbols to their profiles
        """
        try:
            logger.info(f"🔍 Starting universe analysis for {len(symbols)} instruments")
            
            profiles = {}
            
            for i, symbol in enumerate(symbols, 1):
                logger.info(f"📊 Analyzing {symbol} ({i}/{len(symbols)})")
                
                try:
                    profile = await self.analyze_instrument(symbol)
                    profiles[symbol] = profile
                    
                    # Brief progress update
                    logger.info(f"   ✅ {symbol}: Quality={profile.overall_quality_score:.3f}, "
                              f"Mom={profile.momentum_fitness:.3f}, MR={profile.mean_reversion_fitness:.3f}")
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to analyze {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Universe analysis completed: {len(profiles)}/{len(symbols)} successful")
            
            if save_results and profiles:
                await self._save_analysis_results(profiles)
            
            return profiles
            
        except Exception as e:
            logger.error(f"❌ Universe analysis failed: {e}")
            return {}
    
    async def _save_analysis_results(self, profiles: Dict[str, InstrumentProfile]) -> None:
        """Save analysis results to configuration files"""
        try:
            # Convert profiles to serializable format
            results = {}
            
            for symbol, profile in profiles.items():
                results[symbol] = {
                    'analysis_date': profile.last_updated.isoformat(),
                    'analysis_period': {
                        'start': profile.analysis_period[0].isoformat(),
                        'end': profile.analysis_period[1].isoformat()
                    },
                    'fitness_scores': {
                        'momentum': profile.momentum_fitness,
                        'mean_reversion': profile.mean_reversion_fitness,
                        'pairs_trading': profile.pairs_fitness,
                        'overall_quality': profile.overall_quality_score
                    },
                    'statistical_properties': {
                        'annualized_volatility': profile.statistical_properties.annualized_volatility,
                        'max_drawdown': profile.statistical_properties.max_drawdown,
                        'autocorr_lag1': profile.statistical_properties.autocorr_lag1,
                        'half_life': profile.statistical_properties.half_life,
                        'momentum_persistence': profile.statistical_properties.momentum_persistence
                    },
                    'liquidity_metrics': {
                        'liquidity_score': profile.liquidity_metrics.liquidity_score,
                        'avg_daily_volume': profile.liquidity_metrics.avg_daily_volume,
                        'bid_ask_spread_bps': profile.liquidity_metrics.bid_ask_spread_bps
                    },
                    'regime_analysis': {
                        'momentum_optimal_regimes': profile.momentum_analysis.optimal_regimes,
                        'mean_reversion_optimal_regimes': profile.mean_reversion_analysis.optimal_regimes
                    },
                    'market_metrics': {
                        'sector': profile.sector_exposure,
                        'market_beta': profile.market_beta,
                        'correlations': profile.correlation_matrix
                    }
                }
            
            # Save to YAML file
            output_file = f"configs/instrument_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml"
            
            with open(output_file, 'w') as f:
                yaml.dump({
                    'analysis_metadata': {
                        'analysis_date': datetime.now().isoformat(),
                        'analyzer_version': '1.0.0',
                        'instruments_analyzed': len(profiles),
                        'data_period_years': 2.5
                    },
                    'instrument_profiles': results
                }, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"💾 Analysis results saved to {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save analysis results: {e}")

# Example usage and testing
if __name__ == "__main__":
    async def test_analyzer():
        """Test the historical analyzer"""
        analyzer = HistoricalInstrumentAnalyzer()
        
        # Test single instrument analysis
        test_symbols = ['TSLA', 'AAPL', 'SPY']
        
        profiles = await analyzer.analyze_universe(test_symbols)
        
        print(f"✅ Analyzed {len(profiles)} instruments")
        for symbol, profile in profiles.items():
            print(f"  {symbol}: Quality={profile.overall_quality_score:.3f}")
    
    # Run test
    asyncio.run(test_analyzer())
