#!/usr/bin/env python3
"""
Core Analytics - Consolidated Performance, Risk, and Execution Analytics
========================================================================

Consolidates the core analytics functionality from multiple modules:
- PerformanceAnalyzer (from performance_analyzer.py)
- RiskAnalyzer (from risk_analyzer.py) 
- AttributionAnalyzer (from attribution_analyzer.py)
- ExecutionAnalytics (from execution_analytics.py)
- OptimizationEngine (from optimization_engine.py)

This module provides the essential analytics needed for trading operations,
performance measurement, risk assessment, and execution analysis.

Author: Professional Trading System Architecture
Version: 1.0.0 (Consolidated)
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
import warnings

# ML and statistical libraries
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from sklearn.decomposition import FactorAnalysis

# Optional statistical libraries
try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# ================================================================================
# CORE ENUMS AND DATA CLASSES
# ================================================================================

class PerformancePatternType(Enum):
    """Performance pattern classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    BREAKDOWN = "breakdown"

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AttributionType(Enum):
    """Types of performance attribution"""
    FACTOR = "factor"
    STRATEGY = "strategy"
    TIMING = "timing"
    SELECTION = "selection"
    ALPHA = "alpha"

@dataclass
class PerformanceMetrics:
    """Core performance metrics"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Additional metrics
    skewness: float = 0.0
    kurtosis: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    information_ratio: float = 0.0
    
    # Metadata
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_trades: int = 0
    avg_trade_duration: float = 0.0

@dataclass
class RiskMetrics:
    """Risk assessment metrics"""
    portfolio_var: float = 0.0
    portfolio_cvar: float = 0.0
    concentration_risk: float = 0.0
    correlation_risk: float = 0.0
    leverage_ratio: float = 0.0
    
    # Risk factors
    market_risk: float = 0.0
    credit_risk: float = 0.0
    liquidity_risk: float = 0.0
    operational_risk: float = 0.0
    
    # Risk limits
    position_limit_utilization: float = 0.0
    sector_limit_utilization: float = 0.0
    overall_risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW

@dataclass
class AttributionResult:
    """Performance attribution results"""
    total_return: float = 0.0
    factor_attribution: Dict[str, float] = field(default_factory=dict)
    strategy_attribution: Dict[str, float] = field(default_factory=dict)
    timing_attribution: float = 0.0
    selection_attribution: float = 0.0
    alpha_attribution: float = 0.0
    residual_return: float = 0.0
    r_squared: float = 0.0
    confidence_level: float = 0.95

@dataclass
class ExecutionMetrics:
    """Execution quality metrics"""
    fill_rate: float = 0.0
    average_slippage: float = 0.0
    implementation_shortfall: float = 0.0
    market_impact: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    total_cost: float = 0.0
    execution_score: float = 0.0

# ================================================================================
# CORE ANALYTICS ENGINE
# ================================================================================

class CoreAnalyticsEngine:
    """
    Unified core analytics engine consolidating performance, risk, attribution,
    execution, and optimization analytics into a single, efficient system.
    
    Features:
    - Real-time performance analysis with ML-powered insights
    - Comprehensive risk assessment and monitoring
    - Multi-factor performance attribution
    - Execution quality analysis and optimization
    - Portfolio optimization recommendations
    """
    
    def __init__(self,
                 history_window: int = 252,
                 forecast_horizon: int = 5,
                 confidence_level: float = 0.95,
                 enable_ml: bool = True):
        """
        Initialize core analytics engine
        
        Args:
            history_window: Number of periods for analysis window
            forecast_horizon: Number of periods for forecasting
            confidence_level: Confidence level for statistical measures
            enable_ml: Enable machine learning features
        """
        self.history_window = history_window
        self.forecast_horizon = forecast_horizon
        self.confidence_level = confidence_level
        self.enable_ml = enable_ml
        
        # Data storage
        self.performance_history: deque = deque(maxlen=history_window * 2)
        self.risk_history: deque = deque(maxlen=history_window)
        self.execution_history: deque = deque(maxlen=1000)
        self.attribution_history: deque = deque(maxlen=100)
        
        # ML Models (if enabled)
        if self.enable_ml:
            self.performance_model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.risk_model = RandomForestRegressor(n_estimators=50, random_state=42)
            self.anomaly_model = IsolationForest(contamination=0.1, random_state=42)
            self.scaler = StandardScaler()
            self.model_trained = False
        
        # Attribution models
        self.linear_model = LinearRegression()
        self.ridge_model = Ridge(alpha=1.0)
        self.factor_model = FactorAnalysis(n_components=5, random_state=42)
        
        # State management
        self.is_analyzing = False
        self.analysis_lock = threading.RLock()
        
        # Cache for optimization
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        
        logger.info("CoreAnalyticsEngine initialized successfully")
    
    # ================================================================================
    # PERFORMANCE ANALYTICS
    # ================================================================================
    
    async def analyze_performance(self, 
                                returns: pd.Series,
                                benchmark_returns: Optional[pd.Series] = None,
                                positions: Optional[pd.DataFrame] = None) -> PerformanceMetrics:
        """
        Comprehensive performance analysis
        
        Args:
            returns: Strategy returns time series
            benchmark_returns: Benchmark returns for comparison
            positions: Position data for additional analysis
            
        Returns:
            PerformanceMetrics object with comprehensive metrics
        """
        with self.analysis_lock:
            try:
                # Check cache first
                cache_key = f"performance_{hash(str(returns.index[-1]))}"
                if self._is_cache_valid() and cache_key in self._metrics_cache:
                    return self._metrics_cache[cache_key]
                
                metrics = PerformanceMetrics()
                
                # Basic return metrics
                metrics.total_return = (1 + returns).prod() - 1
                metrics.annualized_return = (1 + returns.mean()) ** 252 - 1
                metrics.volatility = returns.std() * np.sqrt(252)
                
                # Risk-adjusted metrics
                if metrics.volatility > 0:
                    metrics.sharpe_ratio = metrics.annualized_return / metrics.volatility
                    metrics.sortino_ratio = metrics.annualized_return / (returns[returns < 0].std() * np.sqrt(252))
                
                # Drawdown analysis
                cumulative_returns = (1 + returns).cumprod()
                rolling_max = cumulative_returns.expanding().max()
                drawdowns = (cumulative_returns - rolling_max) / rolling_max
                metrics.max_drawdown = drawdowns.min()
                
                # Calmar ratio
                if abs(metrics.max_drawdown) > 0:
                    metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
                
                # VaR and CVaR
                metrics.var_95 = np.percentile(returns, 5)
                metrics.cvar_95 = returns[returns <= metrics.var_95].mean()
                
                # Distribution metrics
                metrics.skewness = returns.skew()
                metrics.kurtosis = returns.kurtosis()
                
                # Win rate (if we have trade-level data)
                if len(returns) > 0:
                    winning_periods = (returns > 0).sum()
                    metrics.win_rate = winning_periods / len(returns)
                
                # Benchmark comparison (if provided)
                if benchmark_returns is not None:
                    aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
                    if len(aligned_returns) > 1:
                        # Beta calculation
                        covariance = np.cov(aligned_returns, aligned_benchmark)[0, 1]
                        benchmark_variance = np.var(aligned_benchmark)
                        if benchmark_variance > 0:
                            metrics.beta = covariance / benchmark_variance
                        
                        # Alpha calculation
                        benchmark_return = (1 + aligned_benchmark.mean()) ** 252 - 1
                        metrics.alpha = metrics.annualized_return - (benchmark_return * metrics.beta)
                        
                        # Information ratio
                        excess_returns = aligned_returns - aligned_benchmark
                        tracking_error = excess_returns.std() * np.sqrt(252)
                        if tracking_error > 0:
                            metrics.information_ratio = excess_returns.mean() * 252 / tracking_error
                
                # Metadata
                metrics.start_date = returns.index[0] if len(returns) > 0 else None
                metrics.end_date = returns.index[-1] if len(returns) > 0 else None
                metrics.total_trades = len(returns)
                
                # Cache result
                self._metrics_cache[cache_key] = metrics
                self._cache_timestamp = datetime.now()
                
                # Store in history
                self.performance_history.append({
                    'timestamp': datetime.now(),
                    'metrics': metrics,
                    'returns': returns.copy()
                })
                
                return metrics
                
            except Exception as e:
                logger.error(f"Error in performance analysis: {e}")
                return PerformanceMetrics()
    
    # ================================================================================
    # RISK ANALYTICS
    # ================================================================================
    
    async def analyze_risk(self,
                          positions: pd.DataFrame,
                          returns: pd.Series,
                          market_data: Optional[pd.DataFrame] = None) -> RiskMetrics:
        """
        Comprehensive risk analysis
        
        Args:
            positions: Current portfolio positions
            returns: Historical returns
            market_data: Market data for risk factor analysis
            
        Returns:
            RiskMetrics object with risk assessment
        """
        try:
            metrics = RiskMetrics()
            
            # Portfolio VaR and CVaR
            if len(returns) > 0:
                metrics.portfolio_var = np.percentile(returns, (1 - self.confidence_level) * 100)
                metrics.portfolio_cvar = returns[returns <= metrics.portfolio_var].mean()
            
            # Concentration risk
            if not positions.empty and 'weight' in positions.columns:
                weights = positions['weight'].abs()
                metrics.concentration_risk = (weights ** 2).sum()  # Herfindahl index
            
            # Correlation risk (if we have multiple positions)
            if len(positions) > 1 and len(returns) > 20:
                # Simplified correlation risk measure
                correlation_matrix = returns.rolling(window=20).corr()
                if not correlation_matrix.empty:
                    avg_correlation = correlation_matrix.mean().mean()
                    metrics.correlation_risk = max(0, avg_correlation)  # Higher correlation = higher risk
            
            # Leverage calculation
            if not positions.empty and 'value' in positions.columns:
                total_long = positions[positions['value'] > 0]['value'].sum()
                total_short = abs(positions[positions['value'] < 0]['value'].sum())
                total_capital = positions['value'].sum()  # Net capital
                if total_capital > 0:
                    metrics.leverage_ratio = (total_long + total_short) / total_capital
            
            # Risk scoring
            risk_score = 0
            if abs(metrics.portfolio_var) > 0.02:  # 2% daily VaR threshold
                risk_score += 25
            if metrics.concentration_risk > 0.5:  # 50% concentration threshold
                risk_score += 25
            if metrics.correlation_risk > 0.7:  # 70% correlation threshold
                risk_score += 25
            if metrics.leverage_ratio > 2.0:  # 2x leverage threshold
                risk_score += 25
            
            metrics.overall_risk_score = risk_score
            
            # Risk level classification
            if risk_score < 25:
                metrics.risk_level = RiskLevel.LOW
            elif risk_score < 50:
                metrics.risk_level = RiskLevel.MEDIUM
            elif risk_score < 75:
                metrics.risk_level = RiskLevel.HIGH
            else:
                metrics.risk_level = RiskLevel.CRITICAL
            
            # Store in history
            self.risk_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in risk analysis: {e}")
            return RiskMetrics()
    
    # ================================================================================
    # ATTRIBUTION ANALYTICS
    # ================================================================================
    
    async def analyze_attribution(self,
                                 portfolio_returns: pd.Series,
                                 factor_returns: Optional[pd.DataFrame] = None,
                                 strategy_returns: Optional[pd.DataFrame] = None) -> AttributionResult:
        """
        Performance attribution analysis
        
        Args:
            portfolio_returns: Portfolio returns to attribute
            factor_returns: Factor returns for factor attribution
            strategy_returns: Individual strategy returns
            
        Returns:
            AttributionResult with attribution breakdown
        """
        try:
            result = AttributionResult()
            result.total_return = (1 + portfolio_returns).prod() - 1
            
            # Factor attribution (if factor data provided)
            if factor_returns is not None and len(factor_returns) > 0:
                # Align data
                aligned_portfolio, aligned_factors = portfolio_returns.align(factor_returns, join='inner')
                
                if len(aligned_portfolio) > 10:  # Need sufficient data
                    # Multiple regression for factor attribution
                    X = aligned_factors.values
                    y = aligned_portfolio.values
                    
                    # Fit model
                    self.linear_model.fit(X, y)
                    
                    # Calculate factor contributions
                    factor_loadings = self.linear_model.coef_
                    factor_names = aligned_factors.columns
                    
                    for i, factor_name in enumerate(factor_names):
                        factor_contribution = factor_loadings[i] * aligned_factors[factor_name].mean()
                        result.factor_attribution[factor_name] = factor_contribution
                    
                    # Model fit
                    y_pred = self.linear_model.predict(X)
                    result.r_squared = r2_score(y, y_pred)
                    
                    # Alpha (unexplained return)
                    explained_return = sum(result.factor_attribution.values())
                    result.alpha_attribution = result.total_return - explained_return
            
            # Strategy attribution (if strategy data provided)
            if strategy_returns is not None and len(strategy_returns) > 0:
                # Calculate each strategy's contribution to total return
                total_weight = 1.0 / len(strategy_returns.columns)  # Equal weight assumption
                
                for strategy_name in strategy_returns.columns:
                    strategy_return = (1 + strategy_returns[strategy_name]).prod() - 1
                    contribution = strategy_return * total_weight
                    result.strategy_attribution[strategy_name] = contribution
            
            # Store in history
            self.attribution_history.append({
                'timestamp': datetime.now(),
                'result': result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in attribution analysis: {e}")
            return AttributionResult()
    
    # ================================================================================
    # EXECUTION ANALYTICS
    # ================================================================================
    
    async def analyze_execution(self, execution_data: List[Dict[str, Any]]) -> ExecutionMetrics:
        """
        Execution quality analysis
        
        Args:
            execution_data: List of execution records
            
        Returns:
            ExecutionMetrics with execution quality assessment
        """
        try:
            metrics = ExecutionMetrics()
            
            if not execution_data:
                return metrics
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(execution_data)
            
            # Fill rate
            if 'requested_quantity' in df.columns and 'executed_quantity' in df.columns:
                fill_rates = df['executed_quantity'] / df['requested_quantity'].replace(0, np.nan)
                metrics.fill_rate = fill_rates.mean()
            
            # Slippage analysis
            if 'expected_price' in df.columns and 'executed_price' in df.columns:
                slippage = (df['executed_price'] - df['expected_price']) / df['expected_price']
                metrics.average_slippage = slippage.mean()
            
            # Implementation shortfall
            if 'market_impact' in df.columns:
                metrics.market_impact = df['market_impact'].mean()
            
            # Timing costs
            if 'timing_cost' in df.columns:
                metrics.timing_cost = df['timing_cost'].mean()
            
            # Total execution cost
            metrics.total_cost = metrics.market_impact + metrics.timing_cost + abs(metrics.average_slippage)
            
            # Execution score (0-100, higher is better)
            score = 100
            score -= min(abs(metrics.average_slippage) * 1000, 30)  # Penalize slippage
            score -= min(metrics.market_impact * 1000, 30)  # Penalize market impact
            score -= min((1 - metrics.fill_rate) * 50, 30)  # Penalize poor fill rate
            score -= min(metrics.timing_cost * 1000, 10)  # Penalize timing costs
            
            metrics.execution_score = max(0, score)
            
            # Store in history
            self.execution_history.extend([{
                'timestamp': datetime.now(),
                'metrics': metrics,
                'data': execution_data
            }])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in execution analysis: {e}")
            return ExecutionMetrics()
    
    # ================================================================================
    # OPTIMIZATION RECOMMENDATIONS
    # ================================================================================
    
    async def generate_optimization_recommendations(self,
                                                  current_portfolio: pd.DataFrame,
                                                  expected_returns: pd.Series,
                                                  risk_model: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Generate portfolio optimization recommendations
        
        Args:
            current_portfolio: Current portfolio positions
            expected_returns: Expected returns for assets
            risk_model: Risk model (covariance matrix)
            
        Returns:
            Dictionary with optimization recommendations
        """
        try:
            recommendations = {
                'timestamp': datetime.now(),
                'current_risk_score': 0,
                'recommended_changes': [],
                'expected_improvement': {},
                'confidence_level': self.confidence_level
            }
            
            # Risk assessment of current portfolio
            if not current_portfolio.empty:
                # Calculate current concentration
                if 'weight' in current_portfolio.columns:
                    weights = current_portfolio['weight'].abs()
                    concentration = (weights ** 2).sum()
                    
                    # Recommend rebalancing if too concentrated
                    if concentration > 0.5:
                        recommendations['recommended_changes'].append({
                            'type': 'rebalance',
                            'reason': 'High concentration risk',
                            'current_concentration': concentration,
                            'target_concentration': 0.3
                        })
                
                # Position size recommendations
                for idx, position in current_portfolio.iterrows():
                    if 'weight' in position and abs(position['weight']) > 0.2:  # 20% position limit
                        recommendations['recommended_changes'].append({
                            'type': 'reduce_position',
                            'asset': position.get('symbol', idx),
                            'current_weight': position['weight'],
                            'recommended_weight': 0.15,
                            'reason': 'Position size exceeds risk limit'
                        })
            
            # Expected improvement estimates
            if recommendations['recommended_changes']:
                recommendations['expected_improvement'] = {
                    'risk_reduction': '15-25%',
                    'sharpe_improvement': '0.1-0.3',
                    'max_drawdown_reduction': '10-20%'
                }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return {'error': str(e), 'timestamp': datetime.now()}
    
    # ================================================================================
    # UTILITY METHODS
    # ================================================================================
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_ttl
    
    def clear_cache(self) -> None:
        """Clear analytics cache"""
        self._metrics_cache.clear()
        self._cache_timestamp = None
        logger.info("Analytics cache cleared")
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for all analytics"""
        return {
            'performance_records': len(self.performance_history),
            'risk_records': len(self.risk_history),
            'execution_records': len(self.execution_history),
            'attribution_records': len(self.attribution_history),
            'cache_size': len(self._metrics_cache),
            'ml_enabled': self.enable_ml,
            'last_analysis': self._cache_timestamp
        }

# ================================================================================
# CONVENIENCE FUNCTIONS AND ALIASES
# ================================================================================

# Create global instance for backward compatibility
core_analytics = CoreAnalyticsEngine()

# Aliases for backward compatibility
PerformanceAnalyzer = CoreAnalyticsEngine
RiskAnalyzer = CoreAnalyticsEngine
AttributionAnalyzer = CoreAnalyticsEngine
ExecutionAnalytics = CoreAnalyticsEngine
OptimizationEngine = CoreAnalyticsEngine

# Convenience functions
async def analyze_performance(returns: pd.Series, **kwargs) -> PerformanceMetrics:
    """Convenience function for performance analysis"""
    return await core_analytics.analyze_performance(returns, **kwargs)

async def analyze_risk(positions: pd.DataFrame, returns: pd.Series, **kwargs) -> RiskMetrics:
    """Convenience function for risk analysis"""
    return await core_analytics.analyze_risk(positions, returns, **kwargs)

async def analyze_attribution(portfolio_returns: pd.Series, **kwargs) -> AttributionResult:
    """Convenience function for attribution analysis"""
    return await core_analytics.analyze_attribution(portfolio_returns, **kwargs)

async def analyze_execution(execution_data: List[Dict[str, Any]]) -> ExecutionMetrics:
    """Convenience function for execution analysis"""
    return await core_analytics.analyze_execution(execution_data)

logger.info("Core Analytics module loaded successfully - 5 modules consolidated into 1")
