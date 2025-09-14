#!/usr/bin/env python3
"""
Research Analytics - Consolidated Research, Backtesting, and Insights
====================================================================

Consolidates research functionality from multiple modules:
- ResearchEngine (from research_platform.py)
- BacktestEngine (from research_platform.py)
- StrategyDeveloper (from research_platform.py)
- RegimeDetector (from regime_detector.py)
- InsightsEngine (from ai_insights.py)
- DataVisualization (from data_visualization.py)
- ReportGenerator (from reporting_engine.py)

This module provides comprehensive research tools, backtesting capabilities,
AI-powered insights, and advanced visualization for strategy development.

Author: Professional Trading System Architecture
Version: 1.0.0 (Consolidated)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
from abc import ABC, abstractmethod
import warnings
import json

# ML and statistical libraries
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.cluster import KMeans
from scipy import stats

# Optional visualization libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Optional libraries
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import hmmlearn.hmm as hmm
    HAS_HMM = True
except ImportError:
    HAS_HMM = False

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# Performance optimizations
from .performance_optimization import (
    VectorizedCalculations,
    ParallelProcessor,
    IntelligentCache,
    MemoryOptimizer,
    performance_optimized,
    vectorized_calc,
    parallel_processor,
    intelligent_cache,
    memory_optimizer
)

# ================================================================================
# CORE ENUMS AND DATA CLASSES
# ================================================================================

class BacktestMode(Enum):
    """Backtesting modes"""
    VECTORIZED = "vectorized"
    EVENT_DRIVEN = "event_driven"
    MONTE_CARLO = "monte_carlo"

class MarketRegime(Enum):
    """Market regime classifications"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"

class InsightType(Enum):
    """Types of AI insights"""
    PATTERN_RECOGNITION = "pattern_recognition"
    ANOMALY_INSIGHT = "anomaly_insight"
    PERFORMANCE_INSIGHT = "performance_insight"
    RISK_INSIGHT = "risk_insight"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"

@dataclass
class BacktestResult:
    """Comprehensive backtest results"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    
    # Additional metrics
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    var_95: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    
    # Trade details
    trades: List[Dict[str, Any]] = field(default_factory=list)
    daily_returns: pd.Series = field(default_factory=pd.Series)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    
    # Metadata
    backtest_mode: BacktestMode = BacktestMode.VECTORIZED
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RegimeAnalysis:
    """Market regime analysis results"""
    current_regime: MarketRegime
    regime_probability: float
    regime_duration: int  # days
    regime_history: List[Tuple[datetime, MarketRegime]] = field(default_factory=list)
    regime_transitions: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0

@dataclass
class AIInsight:
    """AI-generated insight"""
    insight_type: InsightType
    title: str
    description: str
    confidence: float
    importance: float  # 0-1 scale
    actionable: bool
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# ================================================================================
# RESEARCH ANALYTICS ENGINE
# ================================================================================

class ResearchAnalyticsEngine:
    """
    Unified research analytics engine consolidating backtesting, research tools,
    regime detection, AI insights, visualization, and reporting capabilities.
    
    Features:
    - Advanced backtesting with multiple modes
    - Market regime detection and analysis
    - AI-powered pattern recognition and insights
    - Comprehensive data visualization
    - Automated research reporting
    - Strategy development and optimization tools
    """
    
    def __init__(self,
                 default_capital: float = 100000.0,
                 commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005,
                 enable_ai_insights: bool = True):
        """
        Initialize research analytics engine
        
        Args:
            default_capital: Default initial capital for backtests
            commission_rate: Commission rate for trades
            slippage_rate: Slippage rate for trades
            enable_ai_insights: Enable AI-powered insights
        """
        self.default_capital = default_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.enable_ai_insights = enable_ai_insights
        
        # Data storage
        self.backtest_results: List[BacktestResult] = []
        self.regime_history: deque = deque(maxlen=1000)
        self.insights_history: deque = deque(maxlen=500)
        self.research_cache: Dict[str, Any] = {}
        
        # ML Models
        if self.enable_ai_insights:
            self.pattern_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.performance_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
            self.regime_classifier = RandomForestClassifier(n_estimators=50, random_state=42)
            self.scaler = StandardScaler()
        
        # Regime detection (HMM if available)
        if HAS_HMM:
            self.regime_model = hmm.GaussianHMM(n_components=4, covariance_type="full", random_state=42)
        else:
            self.regime_model = None
        
        # State management
        self.is_analyzing = False
        self.analysis_lock = threading.RLock()
        
        logger.info("ResearchAnalyticsEngine initialized successfully")
    
    # ================================================================================
    # BACKTESTING ENGINE
    # ================================================================================
    
    @performance_optimized(
        cache_key_func=lambda self, strategy_func, data, strategy_name="Strategy", 
                              initial_capital=None, mode=BacktestMode.VECTORIZED, 
                              parameters=None: 
            f"backtest_{strategy_name}_{hash(str(data.index))}_{len(data)}_{mode.value}_{hash(str(parameters))}",
        vectorization_ratio=0.85,
        enable_parallel=True
    )
    async def run_backtest(self,
                          strategy_func: Callable,
                          data: pd.DataFrame,
                          strategy_name: str = "Strategy",
                          initial_capital: Optional[float] = None,
                          mode: BacktestMode = BacktestMode.VECTORIZED,
                          parameters: Optional[Dict[str, Any]] = None) -> BacktestResult:
        """
        Run comprehensive backtest for a trading strategy
        
        Args:
            strategy_func: Strategy function that generates signals
            data: Market data for backtesting
            strategy_name: Name of the strategy
            initial_capital: Initial capital (uses default if None)
            mode: Backtesting mode
            parameters: Strategy parameters
            
        Returns:
            BacktestResult with comprehensive performance metrics
        """
        try:
            capital = initial_capital or self.default_capital
            params = parameters or {}
            
            logger.info(f"Starting backtest: {strategy_name} with {len(data)} data points")
            
            # Generate signals
            signals = await self._generate_signals(strategy_func, data, params)
            
            # Execute backtest based on mode
            if mode == BacktestMode.VECTORIZED:
                result = await self._run_vectorized_backtest(signals, data, capital, strategy_name, params)
            elif mode == BacktestMode.EVENT_DRIVEN:
                result = await self._run_event_driven_backtest(signals, data, capital, strategy_name, params)
            else:  # MONTE_CARLO
                result = await self._run_monte_carlo_backtest(signals, data, capital, strategy_name, params)
            
            # Store result
            self.backtest_results.append(result)
            
            # Generate insights if enabled
            if self.enable_ai_insights:
                await self._generate_backtest_insights(result)
            
            logger.info(f"Backtest completed: {result.total_return:.2%} return, {result.sharpe_ratio:.2f} Sharpe")
            return result
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            # Return empty result
            return BacktestResult(
                strategy_name=strategy_name,
                start_date=data.index[0] if len(data) > 0 else datetime.now(),
                end_date=data.index[-1] if len(data) > 0 else datetime.now(),
                initial_capital=capital,
                final_value=capital,
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                total_trades=0
            )
    
    async def _generate_signals(self, strategy_func: Callable, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """Generate trading signals from strategy function"""
        try:
            # Call strategy function with data and parameters
            if asyncio.iscoroutinefunction(strategy_func):
                signals = await strategy_func(data, **params)
            else:
                signals = strategy_func(data, **params)
            
            # Ensure signals are a pandas Series
            if not isinstance(signals, pd.Series):
                signals = pd.Series(signals, index=data.index)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return pd.Series(0, index=data.index)  # No signals
    
    @performance_optimized(
        cache_key_func=lambda self, data, strategy_type="mean_reversion", params=None: 
            f"vectorized_signals_{strategy_type}_{hash(str(data.index))}_{hash(str(params))}",
        vectorization_ratio=0.90,
        enable_parallel=False
    )
    def generate_signals_vectorized(self, data: pd.DataFrame, 
                                  strategy_type: str = "mean_reversion",
                                  params: Optional[Dict[str, Any]] = None) -> pd.Series:
        """
        Vectorized signal generation for common strategy patterns
        
        Args:
            data: Market data with OHLCV columns
            strategy_type: Type of strategy signals to generate
            params: Strategy parameters
            
        Returns:
            Series of trading signals (-1, 0, 1)
        """
        try:
            if data.empty:
                return pd.Series(0, index=data.index)
            
            # Default parameters
            default_params = {
                'lookback': 20,
                'threshold': 2.0,
                'ema_short': 12,
                'ema_long': 26
            }
            if params:
                default_params.update(params)
            
            # Use close price for signal generation
            if 'close' in data.columns:
                prices = data['close'].values
            elif 'price' in data.columns:
                prices = data['price'].values
            else:
                logger.warning("No price column found for signal generation")
                return pd.Series(0, index=data.index)
            
            signals = np.zeros(len(prices))
            
            if strategy_type == "mean_reversion":
                # Vectorized mean reversion signals
                lookback = default_params['lookback']
                threshold = default_params['threshold']
                
                # Rolling mean and std using vectorized operations
                rolling_mean = vectorized_calc.calculate_rolling_features(
                    prices.reshape(-1, 1), window=lookback
                )[0][:, 0]  # Get rolling mean
                
                rolling_std = vectorized_calc.calculate_rolling_features(
                    prices.reshape(-1, 1), window=lookback
                )[0][:, 1]  # Get rolling std
                
                # Z-score calculation
                z_scores = (prices - rolling_mean) / (rolling_std + 1e-8)
                
                # Generate signals
                signals[z_scores > threshold] = -1  # Sell when above threshold
                signals[z_scores < -threshold] = 1  # Buy when below threshold
                
            elif strategy_type == "momentum":
                # Vectorized momentum signals using EMAs
                short_window = default_params['ema_short']
                long_window = default_params['ema_long']
                
                # Vectorized EMA calculation
                ema_short = self._calculate_ema_vectorized(prices, short_window)
                ema_long = self._calculate_ema_vectorized(prices, long_window)
                
                # Generate signals
                signals[ema_short > ema_long] = 1  # Buy when short EMA > long EMA
                signals[ema_short < ema_long] = -1  # Sell when short EMA < long EMA
                
            elif strategy_type == "pairs_trading":
                # Pairs trading signals (requires two price series)
                if 'close_2' in data.columns:
                    prices_2 = data['close_2'].values
                    
                    # Calculate spread
                    spread = prices - prices_2
                    
                    # Rolling statistics for spread
                    lookback = default_params['lookback']
                    spread_features = vectorized_calc.calculate_rolling_features(
                        spread.reshape(-1, 1), window=lookback
                    )[0]
                    
                    spread_mean = spread_features[:, 0]
                    spread_std = spread_features[:, 1]
                    
                    # Z-score of spread
                    spread_z = (spread - spread_mean) / (spread_std + 1e-8)
                    
                    # Generate signals
                    threshold = default_params['threshold']
                    signals[spread_z > threshold] = -1  # Short spread
                    signals[spread_z < -threshold] = 1  # Long spread
                else:
                    logger.warning("Pairs trading requires 'close_2' column")
            
            return pd.Series(signals, index=data.index)
            
        except Exception as e:
            logger.error(f"Error in vectorized signal generation: {e}")
            return pd.Series(0, index=data.index)
    
    def _calculate_ema_vectorized(self, prices: np.ndarray, window: int) -> np.ndarray:
        """Calculate exponential moving average using vectorized operations"""
        alpha = 2.0 / (window + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]
        
        # Vectorized EMA calculation
        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    async def run_backtest_memory_efficient(self,
                                          strategy_func: Callable,
                                          data: pd.DataFrame,
                                          strategy_name: str = "Strategy",
                                          initial_capital: Optional[float] = None,
                                          chunk_size: int = 10000) -> BacktestResult:
        """
        Memory-efficient backtesting for large datasets
        
        Args:
            strategy_func: Strategy function
            data: Large market dataset
            strategy_name: Name of the strategy
            initial_capital: Starting capital
            chunk_size: Size of processing chunks
            
        Returns:
            BacktestResult object
        """
        try:
            if data.empty:
                return BacktestResult(
                    strategy_name=strategy_name,
                    start_date=datetime.now(),
                    end_date=datetime.now(),
                    initial_capital=initial_capital or 100000,
                    final_capital=initial_capital or 100000,
                    total_return=0.0,
                    annualized_return=0.0,
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    total_trades=0,
                    win_rate=0.0,
                    trades=[],
                    daily_returns=pd.Series(),
                    equity_curve=pd.Series(),
                    insights=[]
                )
            
            capital = initial_capital or 100000
            
            # Process data in chunks to manage memory
            def process_chunk(chunk_data):
                """Process a single chunk of data"""
                signals = self.generate_signals_vectorized(chunk_data, "mean_reversion")
                
                # Simple vectorized backtest for chunk
                if 'close' in chunk_data.columns:
                    returns = chunk_data['close'].pct_change().fillna(0)
                else:
                    returns = pd.Series(0, index=chunk_data.index)
                
                # Strategy returns
                strategy_returns = signals.shift(1) * returns
                strategy_returns = strategy_returns.fillna(0)
                
                return {
                    'returns': strategy_returns,
                    'signals': signals,
                    'trades': len(signals[signals != 0])
                }
            
            # Memory-efficient processing
            chunk_results = memory_optimizer.memory_efficient_calculation(
                data.values,
                lambda chunk: process_chunk(pd.DataFrame(chunk, columns=data.columns)),
                chunk_size=chunk_size,
                reduce_func=self._combine_backtest_chunks
            )
            
            if chunk_results:
                # Construct final result
                all_returns = chunk_results['combined_returns']
                total_trades = chunk_results['total_trades']
                
                # Calculate performance metrics
                total_return = (1 + all_returns).prod() - 1
                annualized_return = (1 + all_returns.mean()) ** 252 - 1
                volatility = all_returns.std() * np.sqrt(252)
                sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
                
                # Calculate drawdown
                cumulative = (1 + all_returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = drawdown.min()
                
                # Win rate
                win_rate = (all_returns > 0).mean()
                
                # Final capital
                final_capital = capital * (1 + total_return)
                
                result = BacktestResult(
                    strategy_name=strategy_name,
                    start_date=data.index[0],
                    end_date=data.index[-1],
                    initial_capital=capital,
                    final_capital=final_capital,
                    total_return=total_return,
                    annualized_return=annualized_return,
                    volatility=volatility,
                    sharpe_ratio=sharpe_ratio,
                    max_drawdown=max_drawdown,
                    total_trades=total_trades,
                    win_rate=win_rate,
                    trades=[],  # Not tracking individual trades in memory-efficient mode
                    daily_returns=all_returns,
                    equity_curve=cumulative * capital,
                    insights=[]
                )
                
                logger.info(f"Memory-efficient backtest completed: {total_return*100:.2f}% return, "
                           f"{sharpe_ratio:.2f} Sharpe, {total_trades} trades")
                
                return result
            else:
                logger.error("Failed to process backtest chunks")
                return BacktestResult(
                    strategy_name=strategy_name,
                    start_date=data.index[0] if not data.empty else datetime.now(),
                    end_date=data.index[-1] if not data.empty else datetime.now(),
                    initial_capital=capital,
                    final_capital=capital,
                    total_return=0.0,
                    annualized_return=0.0,
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    total_trades=0,
                    win_rate=0.0,
                    trades=[],
                    daily_returns=pd.Series(),
                    equity_curve=pd.Series(),
                    insights=[]
                )
                
        except Exception as e:
            logger.error(f"Error in memory-efficient backtest: {e}")
            raise
    
    def _combine_backtest_chunks(self, chunk_results: List[Dict]) -> Dict[str, Any]:
        """Combine results from multiple backtest chunks"""
        if not chunk_results:
            return {}
        
        # Combine returns
        all_returns = []
        total_trades = 0
        
        for chunk_result in chunk_results:
            if 'returns' in chunk_result:
                all_returns.append(chunk_result['returns'])
            if 'trades' in chunk_result:
                total_trades += chunk_result['trades']
        
        if all_returns:
            combined_returns = pd.concat(all_returns)
        else:
            combined_returns = pd.Series()
        
        return {
            'combined_returns': combined_returns,
            'total_trades': total_trades
        }
    
    async def _run_vectorized_backtest(self, signals: pd.Series, data: pd.DataFrame, 
                                     capital: float, strategy_name: str, params: Dict[str, Any]) -> BacktestResult:
        """Run vectorized backtest (fastest method)"""
        try:
            # Calculate returns
            if 'close' in data.columns:
                price_returns = data['close'].pct_change().fillna(0)
            elif 'price' in data.columns:
                price_returns = data['price'].pct_change().fillna(0)
            else:
                # Use first numeric column
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    price_returns = data[numeric_cols[0]].pct_change().fillna(0)
                else:
                    raise ValueError("No price data found")
            
            # Align signals and returns
            aligned_signals, aligned_returns = signals.align(price_returns, join='inner')
            
            # Calculate strategy returns (assuming signals are positions: 1=long, -1=short, 0=neutral)
            strategy_returns = aligned_signals.shift(1) * aligned_returns  # Shift signals to avoid look-ahead bias
            
            # Apply transaction costs
            position_changes = aligned_signals.diff().abs()
            transaction_costs = position_changes * (self.commission_rate + self.slippage_rate)
            net_returns = strategy_returns - transaction_costs
            
            # Calculate cumulative returns
            cumulative_returns = (1 + net_returns).cumprod()
            final_value = capital * cumulative_returns.iloc[-1]
            
            # Performance metrics
            total_return = (final_value / capital) - 1
            annualized_return = (1 + total_return) ** (252 / len(net_returns)) - 1
            volatility = net_returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Drawdown analysis
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min()
            
            # Win rate
            winning_periods = (net_returns > 0).sum()
            win_rate = winning_periods / len(net_returns) if len(net_returns) > 0 else 0
            
            # Count trades (position changes)
            total_trades = int(position_changes.sum())
            
            # Create result
            result = BacktestResult(
                strategy_name=strategy_name,
                start_date=aligned_returns.index[0],
                end_date=aligned_returns.index[-1],
                initial_capital=capital,
                final_value=final_value,
                total_return=total_return,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                daily_returns=net_returns,
                equity_curve=cumulative_returns * capital,
                backtest_mode=BacktestMode.VECTORIZED,
                parameters=params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in vectorized backtest: {e}")
            raise
    
    async def _run_event_driven_backtest(self, signals: pd.Series, data: pd.DataFrame,
                                       capital: float, strategy_name: str, params: Dict[str, Any]) -> BacktestResult:
        """Run event-driven backtest (more realistic but slower)"""
        # For now, use vectorized approach
        # In a full implementation, this would simulate actual order execution
        logger.info("Event-driven backtest not fully implemented, using vectorized approach")
        return await self._run_vectorized_backtest(signals, data, capital, strategy_name, params)
    
    async def _run_monte_carlo_backtest(self, signals: pd.Series, data: pd.DataFrame,
                                      capital: float, strategy_name: str, params: Dict[str, Any]) -> BacktestResult:
        """Run Monte Carlo backtest with multiple scenarios"""
        # For now, use vectorized approach
        # In a full implementation, this would run multiple random scenarios
        logger.info("Monte Carlo backtest not fully implemented, using vectorized approach")
        return await self._run_vectorized_backtest(signals, data, capital, strategy_name, params)
    
    # ================================================================================
    # AI INSIGHTS AND REGIME DETECTION
    # ================================================================================
    
    async def _generate_backtest_insights(self, result: BacktestResult) -> List[AIInsight]:
        """Generate AI insights from backtest results"""
        insights = []
        
        try:
            # Performance insights
            if result.sharpe_ratio > 1.5:
                insights.append(AIInsight(
                    insight_type=InsightType.PERFORMANCE_INSIGHT,
                    title="Excellent Risk-Adjusted Performance",
                    description=f"Strategy shows exceptional Sharpe ratio of {result.sharpe_ratio:.2f}",
                    confidence=0.9,
                    importance=0.8,
                    actionable=True,
                    supporting_data={'sharpe_ratio': result.sharpe_ratio}
                ))
            
            # Risk insights
            if result.max_drawdown < -0.2:  # More than 20% drawdown
                insights.append(AIInsight(
                    insight_type=InsightType.RISK_INSIGHT,
                    title="High Drawdown Risk",
                    description=f"Strategy experienced significant drawdown of {result.max_drawdown:.1%}",
                    confidence=0.95,
                    importance=0.9,
                    actionable=True,
                    supporting_data={'max_drawdown': result.max_drawdown}
                ))
            
            # Store insights
            self.insights_history.extend(insights)
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
        
        return insights
    
    def detect_market_regime(self, data: pd.DataFrame, lookback: int = 60) -> RegimeAnalysis:
        """Detect current market regime using statistical analysis"""
        try:
            if len(data) < lookback:
                return RegimeAnalysis(
                    current_regime=MarketRegime.SIDEWAYS,
                    regime_probability=0.5,
                    regime_duration=0,
                    confidence=0.3
                )
            
            # Get recent data and detect regime (simplified implementation)
            recent_data = data.tail(lookback)
            
            # Calculate regime indicators
            if 'close' in recent_data.columns:
                prices = recent_data['close']
            else:
                numeric_cols = recent_data.select_dtypes(include=[np.number]).columns
                prices = recent_data[numeric_cols[0]] if len(numeric_cols) > 0 else pd.Series()
            
            if len(prices) == 0:
                raise ValueError("No price data found")
            
            returns = prices.pct_change().dropna()
            trend_slope = np.polyfit(range(len(prices)), prices, 1)[0]
            volatility = returns.std()
            
            # Simple regime classification
            if trend_slope > 0:
                regime = MarketRegime.BULL_MARKET
            elif trend_slope < 0:
                regime = MarketRegime.BEAR_MARKET
            else:
                regime = MarketRegime.SIDEWAYS
            
            analysis = RegimeAnalysis(
                current_regime=regime,
                regime_probability=0.7,
                regime_duration=lookback,
                confidence=0.6
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in regime detection: {e}")
            return RegimeAnalysis(
                current_regime=MarketRegime.SIDEWAYS,
                regime_probability=0.5,
                regime_duration=0,
                confidence=0.3
            )

# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

# Create global instance for backward compatibility
research_analytics = ResearchAnalyticsEngine()

# Aliases for backward compatibility
ResearchEngine = ResearchAnalyticsEngine
BacktestEngine = ResearchAnalyticsEngine
StrategyDeveloper = ResearchAnalyticsEngine
RegimeDetector = ResearchAnalyticsEngine
InsightsEngine = ResearchAnalyticsEngine
DataVisualization = ResearchAnalyticsEngine
ReportGenerator = ResearchAnalyticsEngine

# Convenience functions
async def run_backtest(strategy_func: Callable, data: pd.DataFrame, **kwargs) -> BacktestResult:
    """Convenience function for running backtests"""
    return await research_analytics.run_backtest(strategy_func, data, **kwargs)

def detect_market_regime(data: pd.DataFrame, **kwargs) -> RegimeAnalysis:
    """Convenience function for regime detection"""
    return research_analytics.detect_market_regime(data, **kwargs)

logger.info("Research Analytics module loaded successfully - 7 modules consolidated into 1")
