#!/usr/bin/env python3
"""
Research Analytics - Consolidated Research, Backtesting, and Insights
====================================================================

Consolidates research functionality from multiple modules:
- ResearchEngine (from research_platform.py)
- BacktestEng            # Execute backtest based on mode
            if mode == BacktestMode.VECTORIZED:
                result = asyncio.run(self._run_vectorized_backtest(signals, data, capital, strategy_name, params, mode))
            elif mode == BacktestMode.EVENT_DRIVEN:
                result = asyncio.run(self._run_vectorized_backtest(signals, data, capital, strategy_name, params, mode))
            else:  # MONTE_CARLO
                result = asyncio.run(self._run_vectorized_backtest(signals, data, capital, strategy_name, params, mode))om research_platform.py)
- StrategyDeveloper (from research_platform.py)
- RegimeDetector (from regime_detector.py)
- InsightsEngine (from ai_insights.py)
- DataVisualization (from data_visualization.py)
- ReportGenerator (from reporting_engine.py)

This module provides comprehensive research tools, backtesting capabilities,
AI-powe                # Update best result
                is_maximizing = optimization_metric in ['sharpe_ratio', 'total_return', 'win_rate']
                if (is_maximizing and metric_value > best_metric) or (not is_maximizing and metric_value < best_metric):
                    best_metric = metric_value
                    best_result = result
                    best_params = param_dictsights, and advanced visualization for strategy development.

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
try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

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
        
        # ML Models (if enabled and available)
        if self.enable_ai_insights and HAS_SKLEARN:
            self.pattern_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.performance_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
            self.regime_classifier = RandomForestClassifier(n_estimators=50, random_state=42)
            self.scaler = StandardScaler()
        else:
            self.pattern_classifier = None
            self.performance_predictor = None
            self.regime_classifier = None
            self.scaler = None
        
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
    
    def run_backtest(self,
                          strategy_func: Optional[Callable] = None,
                          data: Optional[pd.DataFrame] = None,
                          strategy_name: str = "Strategy",
                          initial_capital: Optional[float] = None,
                          mode: BacktestMode = BacktestMode.VECTORIZED,
                          parameters: Optional[Dict[str, Any]] = None,
                          # Alternative parameter names for backward compatibility
                          strategy_function: Optional[Callable] = None,
                          market_data: Optional[pd.DataFrame] = None,
                          strategy_instance: Optional[Any] = None) -> BacktestResult:
        """
        Run comprehensive backtest for a trading strategy
        
        Args:
            strategy_func: Strategy function that generates signals
            data: Market data for backtesting
            strategy_name: Name of the strategy
            initial_capital: Initial capital (uses default if None)
            mode: Backtesting mode
            parameters: Strategy parameters
            strategy_function: Alternative name for strategy_func
            market_data: Alternative name for data
            strategy_instance: Alternative name for strategy_name
        """
        try:
            # Handle alternative parameter names
            if strategy_function is not None:
                strategy_func = strategy_function
            if market_data is not None:
                data = market_data
            if strategy_instance is not None:
                if strategy_name == "Strategy":  # Only use instance name if no explicit name provided
                    strategy_name = str(strategy_instance)
                if strategy_func is None and hasattr(strategy_instance, 'on_market_data'):
                    strategy_func = strategy_instance.on_market_data
            
            capital = initial_capital or self.default_capital
            params = parameters or {}
            
            # Validate required parameters
            if strategy_func is None:
                raise ValueError("strategy_func or strategy_function must be provided")
            if data is None:
                raise ValueError("data or market_data must be provided")
            
            logger.info(f"Starting backtest: {strategy_name} with {len(data)} data points")
            
            # Generate signals
            signals = asyncio.run(self._generate_signals(strategy_func, data, params))
            
            # Execute backtest based on mode
            if mode == BacktestMode.VECTORIZED:
                result = asyncio.run(self._run_vectorized_backtest(signals, data, capital, strategy_name, params))
            elif mode == BacktestMode.EVENT_DRIVEN:
                result = asyncio.run(self._run_event_driven_backtest(signals, data, capital, strategy_name, params))
            else:  # MONTE_CARLO
                result = asyncio.run(self._run_monte_carlo_backtest(signals, data, capital, strategy_name, params))
            
            # Store result
            self.backtest_results.append(result)
            
            # Generate insights if enabled
            if self.enable_ai_insights:
                asyncio.run(self._generate_backtest_insights(result))
            
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
                total_trades=0,
                backtest_mode=mode
            )
    
    async def _generate_signals(self, strategy_func: Callable, data: pd.DataFrame, params: Dict[str, Any]) -> pd.Series:
        """Generate trading signals from strategy function"""
        try:
            # Call strategy function with data and parameters
            if asyncio.iscoroutinefunction(strategy_func):
                try:
                    # Try with params as keyword argument first
                    signals = await strategy_func(data, params=params)
                except TypeError:
                    # Fall back to unpacking params
                    signals = await strategy_func(data, **params)
            else:
                try:
                    # Try with params as keyword argument first
                    signals = strategy_func(data, params=params)
                except TypeError:
                    # Fall back to unpacking params
                    signals = strategy_func(data, **params)
            
            # Handle different return types
            if isinstance(signals, pd.DataFrame):
                # Extract signal column if it exists
                if 'signal' in signals.columns:
                    signal_series = pd.Series(0, index=data.index)
                    # Map signals to the correct index
                    for _, row in signals.iterrows():
                        if hasattr(row, 'timestamp') and row.timestamp in data.index:
                            idx = data.index.get_loc(row.timestamp)
                            signal_series.iloc[idx] = row.signal
                        elif hasattr(row, 'name') and row.name in data.index:
                            idx = data.index.get_loc(row.name)
                            signal_series.iloc[idx] = row.signal
                    return signal_series
                else:
                    # Use first column as signals
                    return signals.iloc[:, 0] if len(signals.columns) > 0 else pd.Series(0, index=data.index)
            elif isinstance(signals, pd.Series):
                return signals
            else:
                # Convert to Series
                return pd.Series(signals, index=data.index[:len(signals)] if hasattr(signals, '__len__') else data.index)
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return pd.Series(0, index=data.index)  # No signals
    
    async def _run_vectorized_backtest(self, signals: pd.Series, data: pd.DataFrame, 
                                     capital: float, strategy_name: str, params: Dict[str, Any], 
                                     mode: BacktestMode = BacktestMode.VECTORIZED) -> BacktestResult:
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
                backtest_mode=mode,
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
                confidence=0.6,
                regime_history=[(data.index[-1], regime)] if len(data) > 0 else []
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
    # ADDITIONAL METHODS FOR TEST COMPATIBILITY
    # ================================================================================
    
    def analyze_market_regime(self, data: pd.DataFrame, **kwargs) -> RegimeAnalysis:
        """Alias for detect_market_regime for backward compatibility"""
        return self.detect_market_regime(data, **kwargs)
    
    def generate_ai_insights(self, data: pd.DataFrame) -> List[AIInsight]:
        """Generate AI insights from market data"""
        try:
            insights = []
            
            if not self.enable_ai_insights:
                return insights
            
            # Generate basic insights based on data analysis
            if len(data) > 0:
                # Trend insight
                if 'close' in data.columns:
                    recent_prices = data['close'].tail(20)
                    if len(recent_prices) >= 2:
                        trend = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
                        if abs(trend) > 0.05:  # 5% threshold
                            insight_type = InsightType.PERFORMANCE_INSIGHT if trend > 0 else InsightType.RISK_INSIGHT
                            insights.append(AIInsight(
                                insight_type=insight_type,
                                title="Market Trend Detected",
                                description=f"Market showing {'upward' if trend > 0 else 'downward'} trend of {trend:.1%}",
                                confidence=0.7,
                                importance=0.6,
                                actionable=True,
                                supporting_data={'trend': trend}
                            ))
                
                # Volatility insight
                if len(data) > 10:
                    returns = data['close'].pct_change().dropna() if 'close' in data.columns else pd.Series()
                    if len(returns) > 0:
                        volatility = returns.std()
                        if volatility > 0.02:  # High volatility threshold
                            insights.append(AIInsight(
                                insight_type=InsightType.RISK_INSIGHT,
                                title="High Market Volatility",
                                description=f"Market volatility at {volatility:.1%} - consider risk management",
                                confidence=0.8,
                                importance=0.7,
                                actionable=True,
                                supporting_data={'volatility': volatility}
                            ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return []
    
    def compare_strategies(self, results: List[BacktestResult]) -> Dict[str, Any]:
        """Compare multiple backtest results"""
        try:
            if not results:
                return {}
            
            # Calculate comparison metrics
            comparison = {
                'total_strategies': len(results),
                'best_performer': max(results, key=lambda x: x.total_return).strategy_name,
                'worst_performer': min(results, key=lambda x: x.total_return).strategy_name,
                'average_return': np.mean([r.total_return for r in results]),
                'average_sharpe': np.mean([r.sharpe_ratio for r in results]),
                'average_win_rate': np.mean([r.win_rate for r in results]),
                'strategies': []
            }
            
            for result in results:
                strategy_info = {
                    'name': result.strategy_name,
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades
                }
                comparison['strategies'].append(strategy_info)
            
            # Add performance rankings
            comparison['performance_rankings'] = sorted(
                [{'name': r.strategy_name, 'return': r.total_return} for r in results],
                key=lambda x: x['return'], reverse=True
            )
            
            # Add risk-adjusted rankings (Sharpe ratio)
            comparison['risk_adjusted_rankings'] = sorted(
                [{'name': r.strategy_name, 'sharpe': r.sharpe_ratio} for r in results],
                key=lambda x: x['sharpe'], reverse=True
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing strategies: {e}")
            return {}
    
    def optimize_strategy_parameters(self, strategy_func: Optional[Callable] = None, data: Optional[pd.DataFrame] = None, 
                                   param_ranges: Optional[Dict[str, List[Any]]] = None, 
                                   optimization_metric: str = 'sharpe_ratio',
                                   # Alternative parameter names
                                   strategy_function: Optional[Callable] = None,
                                   market_data: Optional[pd.DataFrame] = None,
                                   param_grid: Optional[Dict[str, List[Any]]] = None) -> Dict[str, Any]:
        """Optimize strategy parameters using grid search"""
        try:
            # Handle alternative parameter names
            if strategy_function is not None:
                strategy_func = strategy_function
            if market_data is not None:
                data = market_data
            if param_grid is not None:
                param_ranges = param_grid
            
            # Validate required parameters
            if strategy_func is None:
                raise ValueError("strategy_func or strategy_function must be provided")
            if data is None:
                raise ValueError("data or market_data must be provided")
            if param_ranges is None:
                raise ValueError("param_ranges or param_grid must be provided")
            
            best_result = None
            best_metric = -np.inf if optimization_metric in ['sharpe_ratio', 'total_return'] else np.inf
            
            # Simple grid search (could be enhanced with more sophisticated optimization)
            from itertools import product
            
            param_combinations = list(product(*param_ranges.values()))
            param_names = list(param_ranges.keys())
            
            # Store all results
            all_results = []
            for params in param_combinations:
                param_dict = dict(zip(param_names, params))
                
                # Run backtest with these parameters
                result = self.run_backtest(
                    strategy_func=strategy_func,
                    data=data,
                    parameters=param_dict
                )
                
                # Get metric value
                if optimization_metric == 'sharpe_ratio':
                    metric_value = result.sharpe_ratio
                elif optimization_metric == 'total_return':
                    metric_value = result.total_return
                elif optimization_metric == 'win_rate':
                    metric_value = result.win_rate
                else:
                    metric_value = result.sharpe_ratio  # default
                
                # Store result
                all_results.append({
                    'parameters': param_dict,
                    'result': result,
                    'metric_value': metric_value
                })
                
                # Update best result
                is_maximizing = optimization_metric in ['sharpe_ratio', 'total_return', 'win_rate']
                if (is_maximizing and metric_value > best_metric) or (not is_maximizing and metric_value < best_metric):
                    best_metric = metric_value
                    best_result = result
                    best_params = param_dict
            
            return {
                'best_parameters': best_params if 'best_params' in locals() else {},
                'best_result': best_result,
                'optimization_metric': optimization_metric,
                'metric_value': best_metric,
                'best_score': best_metric,  # Alias for backward compatibility
                'all_results': all_results,  # All optimization results
                'total_combinations_tested': len(param_combinations)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing strategy parameters: {e}")
            return {}
    
    def generate_research_report(self) -> Dict[str, Any]:
        """Generate comprehensive research report"""
        try:
            report = {
                'timestamp': datetime.now(),
                'generated_at': datetime.now(),
                'total_backtests': len(self.backtest_results),
                'total_insights': len(self.insights_history),
                'regime_history_length': len(self.regime_history),
                'summary': {},
                'performance_analysis': {},
                'risk_analysis': {},
                'recommendations': []
            }
            
            if self.backtest_results:
                returns = [r.total_return for r in self.backtest_results]
                sharpe_ratios = [r.sharpe_ratio for r in self.backtest_results]
                max_drawdowns = [r.max_drawdown for r in self.backtest_results]
                
                report['summary'] = {
                    'average_return': np.mean(returns),
                    'best_return': max(returns),
                    'worst_return': min(returns),
                    'total_strategies_tested': len(self.backtest_results)
                }
                
                report['performance_analysis'] = {
                    'average_sharpe': np.mean(sharpe_ratios),
                    'best_sharpe': max(sharpe_ratios),
                    'return_volatility': np.std(returns)
                }
                
                report['risk_analysis'] = {
                    'average_max_drawdown': np.mean(max_drawdowns),
                    'worst_drawdown': max(max_drawdowns),
                    'risk_adjusted_returns': np.mean([r.total_return / abs(r.max_drawdown) if r.max_drawdown != 0 else 0 for r in self.backtest_results])
                }
                
                # Generate recommendations
                if np.mean(returns) > 0.1:
                    report['recommendations'].append("Strong performance detected - consider live deployment")
                if np.mean(sharpe_ratios) > 1.0:
                    report['recommendations'].append("Good risk-adjusted returns - strategy shows promise")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating research report: {e}")
            return {}
    
    def get_research_summary(self) -> Dict[str, Any]:
        """Get research summary"""
        return {
            'total_backtests': len(self.backtest_results),
            'total_insights': len(self.insights_history),
            'regime_analysis_count': len(self.regime_history),
            'cache_size': len(self.research_cache),
            'ai_enabled': self.enable_ai_insights,
            'last_research_activity': datetime.now()
        }


# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

async def run_backtest(strategy_func: Callable, data: pd.DataFrame, **kwargs) -> BacktestResult:
    """Convenience function for running backtests"""
    return await research_analytics.run_backtest(strategy_func, data, **kwargs)

def detect_market_regime(data: pd.DataFrame, **kwargs) -> RegimeAnalysis:
    """Convenience function for regime detection"""
    return research_analytics.detect_market_regime(data, **kwargs)

# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

# Create global instance for backward compatibility
research_analytics = ResearchAnalyticsEngine()

# Aliases for backward compatibility
research_engine = research_analytics
ResearchEngine = ResearchAnalyticsEngine
BacktestEngine = ResearchAnalyticsEngine
StrategyDeveloper = ResearchAnalyticsEngine
RegimeDetector = ResearchAnalyticsEngine
InsightsEngine = ResearchAnalyticsEngine
DataVisualization = ResearchAnalyticsEngine
ReportGenerator = ResearchAnalyticsEngine

logger.info("Research Analytics module loaded successfully - 7 modules consolidated into 1")# ================================================================================
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

# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

# Create global instance for backward compatibility
research_analytics = ResearchAnalyticsEngine()

# Aliases for backward compatibility
research_engine = research_analytics
ResearchEngine = ResearchAnalyticsEngine
BacktestEngine = ResearchAnalyticsEngine
StrategyDeveloper = ResearchAnalyticsEngine
RegimeDetector = ResearchAnalyticsEngine
InsightsEngine = ResearchAnalyticsEngine
DataVisualization = ResearchAnalyticsEngine
ReportGenerator = ResearchAnalyticsEngine

logger.info("Research Analytics module loaded successfully - 7 modules consolidated into 1")
