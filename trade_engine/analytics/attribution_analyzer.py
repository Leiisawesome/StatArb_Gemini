#!/usr/bin/env python3
"""
Attribution Analyzer - ML-Powered Performance Attribution
=========================================================

Comprehensive performance attribution system with factor analysis, strategy attribution,
timing analysis, and alpha generation identification.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
import warnings
warnings.filterwarnings('ignore')

# ML and statistical libraries
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from scipy import stats
from scipy.optimize import minimize

# Optional statistical libraries
try:
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttributionType(Enum):
    """Types of performance attribution"""
    FACTOR = "factor"
    STRATEGY = "strategy"
    TIMING = "timing"
    SELECTION = "selection"
    INTERACTION = "interaction"
    ALPHA = "alpha"

class FactorCategory(Enum):
    """Factor categories for attribution"""
    MARKET = "market"
    STYLE = "style"
    SECTOR = "sector"
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    SIZE = "size"
    VOLATILITY = "volatility"
    CURRENCY = "currency"
    MACRO = "macro"

class TimingType(Enum):
    """Types of timing analysis"""
    MARKET_TIMING = "market_timing"
    SECTOR_TIMING = "sector_timing"
    FACTOR_TIMING = "factor_timing"
    VOLATILITY_TIMING = "volatility_timing"

@dataclass
class FactorAttribution:
    """Factor attribution result"""
    factor_name: str
    factor_category: FactorCategory
    attribution: float  # Contribution to returns
    exposure: float  # Factor exposure
    factor_return: float  # Factor return
    significance: float  # Statistical significance
    t_statistic: float
    p_value: float
    confidence_interval: Tuple[float, float]
    
    # Additional analysis
    explanation: str = ""
    contribution_percentage: float = 0.0

@dataclass
class StrategyAttribution:
    """Strategy attribution result"""
    strategy_id: str
    strategy_name: str
    total_return: float
    attribution: float
    weight: float
    active_return: float
    tracking_error: float
    information_ratio: float
    
    # Decomposition
    factor_attributions: Dict[str, float] = field(default_factory=dict)
    alpha_contribution: float = 0.0
    timing_contribution: float = 0.0

@dataclass
class TimingAttribution:
    """Timing attribution analysis"""
    timing_type: TimingType
    timing_skill: float  # Positive = good timing
    attribution: float  # Contribution from timing
    hit_rate: float  # Percentage of correct timing decisions
    average_magnitude: float  # Average size of timing bets
    
    # Statistical measures
    t_statistic: float
    p_value: float
    significance: str
    confidence: float

@dataclass
class AlphaAttribution:
    """Alpha generation attribution"""
    total_alpha: float
    unexplained_alpha: float  # Alpha not attributed to factors
    factor_alpha: Dict[str, float]  # Alpha from each factor
    selection_alpha: float  # Alpha from security selection
    timing_alpha: float  # Alpha from timing
    interaction_alpha: float  # Interaction effects
    
    # Quality metrics
    alpha_significance: float
    alpha_consistency: float  # Consistency over time
    alpha_decay: float  # How alpha changes over time

@dataclass
class AttributionReport:
    """Comprehensive attribution report"""
    period_start: datetime
    period_end: datetime
    portfolio_return: float
    benchmark_return: float
    active_return: float
    
    # Attribution breakdown
    factor_attributions: List[FactorAttribution]
    strategy_attributions: List[StrategyAttribution]
    timing_attributions: List[TimingAttribution]
    alpha_attribution: AlphaAttribution
    
    # Summary statistics
    explained_variance: float
    unexplained_variance: float
    attribution_r_squared: float
    total_risk: float
    active_risk: float
    
    # Analysis metadata
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    data_quality: str = "good"
    confidence_level: float = 0.95

class AttributionAnalyzer:
    """
    ML-powered performance attribution analyzer
    
    Features:
    - Factor attribution using multiple regression models
    - Strategy attribution and decomposition
    - Market timing analysis
    - Security selection attribution
    - Alpha generation analysis
    - Interactive attribution effects
    """
    
    def __init__(self,
                 attribution_window: int = 252,  # 1 year
                 min_observations: int = 60,     # Minimum data points
                 confidence_level: float = 0.95,
                 factor_models: List[str] = None):
        
        self.attribution_window = attribution_window
        self.min_observations = min_observations
        self.confidence_level = confidence_level
        
        # Factor models to use
        self.factor_models = factor_models or [
            'linear_regression',
            'ridge_regression', 
            'random_forest',
            'factor_analysis'
        ]
        
        # ML models
        self.linear_model = LinearRegression()
        self.ridge_model = Ridge(alpha=1.0)
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.factor_model = FactorAnalysis(n_components=10, random_state=42)
        self.scaler = StandardScaler()
        
        # Data storage
        self.returns_history: List[Dict[str, Any]] = []
        self.factor_data: List[Dict[str, float]] = []
        self.strategy_data: List[Dict[str, Any]] = []
        self.attribution_history: List[AttributionReport] = []
        
        # Factor definitions
        self.factor_definitions = self._initialize_factor_definitions()
        
        # State management
        self.is_analyzing = False
        self.lock = Lock()
        
        logger.info("AttributionAnalyzer initialized with ML-powered attribution models")
    
    def _initialize_factor_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize standard factor definitions"""
        return {
            'market': {
                'category': FactorCategory.MARKET,
                'description': 'Market exposure (beta)',
                'calculation': 'market_return'
            },
            'size': {
                'category': FactorCategory.SIZE,
                'description': 'Size factor (small vs large cap)',
                'calculation': 'smb_factor'
            },
            'value': {
                'category': FactorCategory.VALUE,
                'description': 'Value factor (value vs growth)',
                'calculation': 'hml_factor'
            },
            'momentum': {
                'category': FactorCategory.MOMENTUM,
                'description': 'Momentum factor',
                'calculation': 'momentum_factor'
            },
            'quality': {
                'category': FactorCategory.QUALITY,
                'description': 'Quality factor',
                'calculation': 'quality_factor'
            },
            'volatility': {
                'category': FactorCategory.VOLATILITY,
                'description': 'Low volatility factor',
                'calculation': 'volatility_factor'
            }
        }
    
    async def start_analysis(self) -> None:
        """Start attribution analysis"""
        with self.lock:
            if self.is_analyzing:
                logger.warning("Attribution analysis already running")
                return
            
            self.is_analyzing = True
            logger.info("Starting ML-powered attribution analysis")
    
    async def stop_analysis(self) -> None:
        """Stop attribution analysis"""
        with self.lock:
            self.is_analyzing = False
            logger.info("Attribution analysis stopped")
    
    def add_returns_data(self, timestamp: datetime, portfolio_return: float, 
                        benchmark_return: float, factor_returns: Dict[str, float]) -> None:
        """Add returns data for attribution analysis"""
        with self.lock:
            self.returns_history.append({
                'timestamp': timestamp,
                'portfolio_return': portfolio_return,
                'benchmark_return': benchmark_return,
                'active_return': portfolio_return - benchmark_return,
                'factor_returns': factor_returns.copy()
            })
            
            # Maintain rolling window
            if len(self.returns_history) > self.attribution_window:
                self.returns_history = self.returns_history[-self.attribution_window:]
    
    def add_strategy_data(self, timestamp: datetime, strategies: Dict[str, Dict[str, float]]) -> None:
        """Add strategy-level data for attribution"""
        with self.lock:
            self.strategy_data.append({
                'timestamp': timestamp,
                'strategies': strategies.copy()
            })
            
            # Maintain rolling window
            if len(self.strategy_data) > self.attribution_window:
                self.strategy_data = self.strategy_data[-self.attribution_window:]
    
    async def analyze_factor_attribution(self, period_days: int = 30) -> List[FactorAttribution]:
        """Analyze factor attribution using multiple ML models"""
        if len(self.returns_history) < self.min_observations:
            raise ValueError("Insufficient data for factor attribution")
        
        try:
            # Prepare data
            data = self._prepare_attribution_data(period_days)
            returns = data['active_returns']
            factors = data['factor_matrix']
            
            # Run multiple factor models
            attributions = []
            
            # 1. Linear Regression Model
            linear_attrs = await self._factor_attribution_linear(returns, factors)
            attributions.extend(linear_attrs)
            
            # 2. Ridge Regression (handles multicollinearity)
            ridge_attrs = await self._factor_attribution_ridge(returns, factors)
            attributions.extend(ridge_attrs)
            
            # 3. Random Forest (captures non-linear relationships)
            rf_attrs = await self._factor_attribution_random_forest(returns, factors)
            attributions.extend(rf_attrs)
            
            # 4. Factor Analysis (latent factors)
            fa_attrs = await self._factor_attribution_factor_analysis(returns, factors)
            attributions.extend(fa_attrs)
            
            # Ensemble and consolidate results
            consolidated_attrs = self._consolidate_factor_attributions(attributions)
            
            logger.info(f"Completed factor attribution analysis with {len(consolidated_attrs)} factors")
            return consolidated_attrs
            
        except Exception as e:
            logger.error(f"Error in factor attribution analysis: {e}")
            raise
    
    async def analyze_strategy_attribution(self, period_days: int = 30) -> List[StrategyAttribution]:
        """Analyze strategy-level attribution"""
        if len(self.strategy_data) < self.min_observations:
            raise ValueError("Insufficient strategy data for attribution")
        
        try:
            # Get recent strategy data
            recent_data = self.strategy_data[-period_days:] if period_days < len(self.strategy_data) else self.strategy_data
            
            strategy_attributions = []
            
            # Get all unique strategies
            all_strategies = set()
            for data_point in recent_data:
                all_strategies.update(data_point['strategies'].keys())
            
            for strategy_id in all_strategies:
                strategy_attribution = await self._analyze_single_strategy(strategy_id, recent_data)
                if strategy_attribution:
                    strategy_attributions.append(strategy_attribution)
            
            logger.info(f"Completed strategy attribution for {len(strategy_attributions)} strategies")
            return strategy_attributions
            
        except Exception as e:
            logger.error(f"Error in strategy attribution analysis: {e}")
            raise
    
    async def analyze_timing_attribution(self, period_days: int = 90) -> List[TimingAttribution]:
        """Analyze market timing attribution"""
        if len(self.returns_history) < self.min_observations:
            raise ValueError("Insufficient data for timing attribution")
        
        try:
            timing_attributions = []
            
            # Market timing analysis
            market_timing = await self._analyze_market_timing(period_days)
            if market_timing:
                timing_attributions.append(market_timing)
            
            # Sector timing analysis
            sector_timing = await self._analyze_sector_timing(period_days)
            if sector_timing:
                timing_attributions.append(sector_timing)
            
            # Factor timing analysis
            factor_timing = await self._analyze_factor_timing(period_days)
            if factor_timing:
                timing_attributions.append(factor_timing)
            
            # Volatility timing analysis
            vol_timing = await self._analyze_volatility_timing(period_days)
            if vol_timing:
                timing_attributions.append(vol_timing)
            
            logger.info(f"Completed timing attribution analysis with {len(timing_attributions)} timing types")
            return timing_attributions
            
        except Exception as e:
            logger.error(f"Error in timing attribution analysis: {e}")
            raise
    
    async def analyze_alpha_attribution(self, period_days: int = 60) -> AlphaAttribution:
        """Analyze alpha generation and attribution"""
        if len(self.returns_history) < self.min_observations:
            raise ValueError("Insufficient data for alpha attribution")
        
        try:
            # Prepare data
            data = self._prepare_attribution_data(period_days)
            returns = data['active_returns']
            factors = data['factor_matrix']
            
            # Factor model regression to separate alpha from factor exposure
            X = sm.add_constant(factors)
            model = sm.OLS(returns, X).fit()
            
            # Total alpha (intercept)
            total_alpha = float(model.params[0]) * 252  # Annualized
            alpha_tstat = float(model.tvalues[0])
            alpha_pvalue = float(model.pvalues[0])
            
            # Factor-specific alpha contributions
            factor_alpha = {}
            factor_names = data['factor_names']
            
            for i, factor_name in enumerate(factor_names):
                factor_loading = float(model.params[i + 1])  # +1 for constant
                factor_return = float(np.mean(factors[:, i]))
                factor_alpha[factor_name] = factor_loading * factor_return * 252
            
            # Selection alpha (unexplained by factors)
            residuals = model.resid
            unexplained_alpha = float(np.mean(residuals)) * 252
            
            # Timing alpha from timing analysis
            timing_attrs = await self.analyze_timing_attribution(period_days)
            timing_alpha = sum(attr.attribution for attr in timing_attrs)
            
            # Selection alpha (pure stock picking)
            selection_alpha = total_alpha - timing_alpha - sum(factor_alpha.values())
            
            # Alpha quality metrics
            alpha_significance = 1.0 - alpha_pvalue if alpha_pvalue < 0.05 else 0.0
            alpha_consistency = self._calculate_alpha_consistency(returns, factors)
            alpha_decay = self._calculate_alpha_decay(period_days)
            
            alpha_attribution = AlphaAttribution(
                total_alpha=total_alpha,
                unexplained_alpha=unexplained_alpha,
                factor_alpha=factor_alpha,
                selection_alpha=selection_alpha,
                timing_alpha=timing_alpha,
                interaction_alpha=0.0,  # Simplified for now
                alpha_significance=alpha_significance,
                alpha_consistency=alpha_consistency,
                alpha_decay=alpha_decay
            )
            
            logger.info(f"Completed alpha attribution: total alpha = {total_alpha:.4f}")
            return alpha_attribution
            
        except Exception as e:
            logger.error(f"Error in alpha attribution analysis: {e}")
            raise
    
    async def generate_attribution_report(self, period_days: int = 30) -> AttributionReport:
        """Generate comprehensive attribution report"""
        if len(self.returns_history) < self.min_observations:
            raise ValueError("Insufficient data for attribution report")
        
        try:
            # Get recent data
            recent_data = self.returns_history[-period_days:] if period_days < len(self.returns_history) else self.returns_history
            
            # Calculate period returns
            portfolio_returns = [d['portfolio_return'] for d in recent_data]
            benchmark_returns = [d['benchmark_return'] for d in recent_data]
            active_returns = [d['active_return'] for d in recent_data]
            
            portfolio_return = float(np.sum(portfolio_returns))
            benchmark_return = float(np.sum(benchmark_returns))
            active_return = float(np.sum(active_returns))
            
            # Run all attribution analyses
            factor_attributions = await self.analyze_factor_attribution(period_days)
            strategy_attributions = await self.analyze_strategy_attribution(period_days)
            timing_attributions = await self.analyze_timing_attribution(period_days)
            alpha_attribution = await self.analyze_alpha_attribution(period_days)
            
            # Calculate explained variance
            data = self._prepare_attribution_data(period_days)
            returns = data['active_returns']
            factors = data['factor_matrix']
            
            # Regression R-squared
            X = sm.add_constant(factors)
            model = sm.OLS(returns, X).fit()
            attribution_r_squared = float(model.rsquared)
            explained_variance = attribution_r_squared
            unexplained_variance = 1.0 - explained_variance
            
            # Risk metrics
            total_risk = float(np.std(portfolio_returns) * np.sqrt(252))
            active_risk = float(np.std(active_returns) * np.sqrt(252))
            
            # Create report
            report = AttributionReport(
                period_start=recent_data[0]['timestamp'],
                period_end=recent_data[-1]['timestamp'],
                portfolio_return=portfolio_return,
                benchmark_return=benchmark_return,
                active_return=active_return,
                factor_attributions=factor_attributions,
                strategy_attributions=strategy_attributions,
                timing_attributions=timing_attributions,
                alpha_attribution=alpha_attribution,
                explained_variance=explained_variance,
                unexplained_variance=unexplained_variance,
                attribution_r_squared=attribution_r_squared,
                total_risk=total_risk,
                active_risk=active_risk
            )
            
            # Store report
            with self.lock:
                self.attribution_history.append(report)
                if len(self.attribution_history) > 50:
                    self.attribution_history = self.attribution_history[-50:]
            
            logger.info(f"Generated attribution report: R² = {attribution_r_squared:.3f}, Active Return = {active_return:.4f}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating attribution report: {e}")
            raise
    
    def _prepare_attribution_data(self, period_days: int) -> Dict[str, Any]:
        """Prepare data for attribution analysis"""
        # Get recent data
        recent_data = self.returns_history[-period_days:] if period_days < len(self.returns_history) else self.returns_history
        
        # Extract returns and factors
        active_returns = np.array([d['active_return'] for d in recent_data])
        
        # Build factor matrix
        all_factors = set()
        for d in recent_data:
            all_factors.update(d['factor_returns'].keys())
        
        factor_names = sorted(list(all_factors))
        factor_matrix = np.zeros((len(recent_data), len(factor_names)))
        
        for i, data_point in enumerate(recent_data):
            for j, factor_name in enumerate(factor_names):
                factor_matrix[i, j] = data_point['factor_returns'].get(factor_name, 0.0)
        
        return {
            'active_returns': active_returns,
            'factor_matrix': factor_matrix,
            'factor_names': factor_names,
            'timestamps': [d['timestamp'] for d in recent_data]
        }
    
    async def _factor_attribution_linear(self, returns: np.ndarray, factors: np.ndarray) -> List[FactorAttribution]:
        """Factor attribution using linear regression"""
        try:
            # Fit linear model
            X = sm.add_constant(factors)
            model = sm.OLS(returns, X).fit()
            
            attributions = []
            factor_names = list(self.factor_definitions.keys())[:factors.shape[1]]
            
            for i, factor_name in enumerate(factor_names):
                if i < len(model.params) - 1:  # Exclude constant
                    exposure = float(model.params[i + 1])
                    factor_return = float(np.mean(factors[:, i]))
                    attribution = exposure * factor_return * 252  # Annualized
                    
                    t_stat = float(model.tvalues[i + 1])
                    p_val = float(model.pvalues[i + 1])
                    
                    # Confidence interval
                    conf_int = model.conf_int(alpha=1-self.confidence_level).iloc[i + 1]
                    
                    factor_def = self.factor_definitions.get(factor_name, {})
                    
                    attr = FactorAttribution(
                        factor_name=factor_name,
                        factor_category=factor_def.get('category', FactorCategory.STYLE),
                        attribution=attribution,
                        exposure=exposure,
                        factor_return=factor_return,
                        significance=1.0 - p_val if p_val < 0.05 else 0.0,
                        t_statistic=t_stat,
                        p_value=p_val,
                        confidence_interval=(float(conf_int.iloc[0]), float(conf_int.iloc[1])),
                        explanation=f"Linear model: {factor_def.get('description', 'Unknown factor')}"
                    )
                    attributions.append(attr)
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error in linear factor attribution: {e}")
            return []
    
    async def _factor_attribution_ridge(self, returns: np.ndarray, factors: np.ndarray) -> List[FactorAttribution]:
        """Factor attribution using Ridge regression"""
        try:
            # Fit Ridge model
            scaled_factors = self.scaler.fit_transform(factors)
            self.ridge_model.fit(scaled_factors, returns)
            
            attributions = []
            factor_names = list(self.factor_definitions.keys())[:factors.shape[1]]
            
            for i, factor_name in enumerate(factor_names):
                if i < len(self.ridge_model.coef_):
                    exposure = float(self.ridge_model.coef_[i])
                    factor_return = float(np.mean(factors[:, i]))
                    attribution = exposure * factor_return * 252
                    
                    # Simplified significance (Ridge doesn't provide p-values)
                    significance = min(1.0, abs(exposure) / np.std(factors[:, i]))
                    
                    factor_def = self.factor_definitions.get(factor_name, {})
                    
                    attr = FactorAttribution(
                        factor_name=f"{factor_name}_ridge",
                        factor_category=factor_def.get('category', FactorCategory.STYLE),
                        attribution=attribution,
                        exposure=exposure,
                        factor_return=factor_return,
                        significance=significance,
                        t_statistic=0.0,  # Not available in Ridge
                        p_value=0.1,  # Approximation
                        confidence_interval=(-abs(exposure), abs(exposure)),
                        explanation=f"Ridge model: {factor_def.get('description', 'Regularized factor')}"
                    )
                    attributions.append(attr)
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error in Ridge factor attribution: {e}")
            return []
    
    async def _factor_attribution_random_forest(self, returns: np.ndarray, factors: np.ndarray) -> List[FactorAttribution]:
        """Factor attribution using Random Forest"""
        try:
            # Fit Random Forest
            self.rf_model.fit(factors, returns)
            
            # Feature importance as factor attribution
            importances = self.rf_model.feature_importances_
            attributions = []
            factor_names = list(self.factor_definitions.keys())[:factors.shape[1]]
            
            for i, factor_name in enumerate(factor_names):
                if i < len(importances):
                    importance = float(importances[i])
                    factor_return = float(np.mean(factors[:, i]))
                    attribution = importance * factor_return * 252
                    
                    factor_def = self.factor_definitions.get(factor_name, {})
                    
                    attr = FactorAttribution(
                        factor_name=f"{factor_name}_rf",
                        factor_category=factor_def.get('category', FactorCategory.STYLE),
                        attribution=attribution,
                        exposure=importance,
                        factor_return=factor_return,
                        significance=importance,  # Importance as significance
                        t_statistic=0.0,
                        p_value=0.05 if importance > 0.1 else 0.5,
                        confidence_interval=(0.0, importance * 2),
                        explanation=f"Random Forest: {factor_def.get('description', 'Non-linear factor')}"
                    )
                    attributions.append(attr)
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error in Random Forest factor attribution: {e}")
            return []
    
    async def _factor_attribution_factor_analysis(self, returns: np.ndarray, factors: np.ndarray) -> List[FactorAttribution]:
        """Factor attribution using Factor Analysis"""
        try:
            # Fit Factor Analysis
            n_components = min(5, factors.shape[1])
            self.factor_model.n_components = n_components
            latent_factors = self.factor_model.fit_transform(factors)
            
            # Regress returns on latent factors
            model = LinearRegression().fit(latent_factors, returns)
            
            attributions = []
            
            for i in range(n_components):
                exposure = float(model.coef_[i])
                factor_return = float(np.mean(latent_factors[:, i]))
                attribution = exposure * factor_return * 252
                
                attr = FactorAttribution(
                    factor_name=f"latent_factor_{i+1}",
                    factor_category=FactorCategory.STYLE,
                    attribution=attribution,
                    exposure=exposure,
                    factor_return=factor_return,
                    significance=abs(exposure) / (np.std(latent_factors[:, i]) + 1e-6),
                    t_statistic=0.0,
                    p_value=0.1,
                    confidence_interval=(-abs(exposure), abs(exposure)),
                    explanation=f"Factor Analysis: Latent factor {i+1}"
                )
                attributions.append(attr)
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error in Factor Analysis attribution: {e}")
            return []
    
    def _consolidate_factor_attributions(self, attributions: List[FactorAttribution]) -> List[FactorAttribution]:
        """Consolidate factor attributions from multiple models"""
        # Group by base factor name (remove model suffix)
        factor_groups = {}
        
        for attr in attributions:
            base_name = attr.factor_name.split('_')[0]
            if base_name not in factor_groups:
                factor_groups[base_name] = []
            factor_groups[base_name].append(attr)
        
        # Consolidate each group
        consolidated = []
        
        for base_name, group in factor_groups.items():
            if len(group) == 1:
                consolidated.append(group[0])
            else:
                # Average the attributions
                avg_attribution = np.mean([attr.attribution for attr in group])
                avg_exposure = np.mean([attr.exposure for attr in group])
                avg_significance = np.mean([attr.significance for attr in group])
                
                # Use the first factor's metadata
                first_attr = group[0]
                
                consolidated_attr = FactorAttribution(
                    factor_name=base_name,
                    factor_category=first_attr.factor_category,
                    attribution=float(avg_attribution),
                    exposure=float(avg_exposure),
                    factor_return=first_attr.factor_return,
                    significance=float(avg_significance),
                    t_statistic=first_attr.t_statistic,
                    p_value=first_attr.p_value,
                    confidence_interval=first_attr.confidence_interval,
                    explanation=f"Ensemble of {len(group)} models"
                )
                consolidated.append(consolidated_attr)
        
        # Sort by absolute attribution
        consolidated.sort(key=lambda x: abs(x.attribution), reverse=True)
        
        return consolidated
    
    async def _analyze_single_strategy(self, strategy_id: str, strategy_data: List[Dict]) -> Optional[StrategyAttribution]:
        """Analyze attribution for a single strategy"""
        try:
            # Extract strategy performance
            strategy_returns = []
            strategy_weights = []
            
            for data_point in strategy_data:
                strategies = data_point['strategies']
                if strategy_id in strategies:
                    strategy_returns.append(strategies[strategy_id].get('return', 0.0))
                    strategy_weights.append(strategies[strategy_id].get('weight', 0.0))
                else:
                    strategy_returns.append(0.0)
                    strategy_weights.append(0.0)
            
            if not strategy_returns or all(r == 0 for r in strategy_returns):
                return None
            
            # Calculate metrics
            total_return = float(np.sum(strategy_returns))
            avg_weight = float(np.mean(strategy_weights))
            tracking_error = float(np.std(strategy_returns) * np.sqrt(252))
            
            # Calculate attribution (weight * return)
            attribution = float(np.sum([w * r for w, r in zip(strategy_weights, strategy_returns)]))
            
            # Active return (vs benchmark - simplified)
            benchmark_return = 0.0  # Would need benchmark data
            active_return = total_return - benchmark_return
            
            # Information ratio
            information_ratio = active_return / tracking_error if tracking_error > 0 else 0.0
            
            # Get strategy name (simplified)
            strategy_name = strategy_id.replace('_', ' ').title()
            
            return StrategyAttribution(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                total_return=total_return,
                attribution=attribution,
                weight=avg_weight,
                active_return=active_return,
                tracking_error=tracking_error,
                information_ratio=float(information_ratio)
            )
            
        except Exception as e:
            logger.error(f"Error analyzing strategy {strategy_id}: {e}")
            return None
    
    async def _analyze_market_timing(self, period_days: int) -> Optional[TimingAttribution]:
        """Analyze market timing skill"""
        try:
            # Simplified market timing analysis
            recent_data = self.returns_history[-period_days:]
            
            portfolio_returns = [d['portfolio_return'] for d in recent_data]
            benchmark_returns = [d['benchmark_return'] for d in recent_data]
            
            # Calculate timing based on return patterns
            timing_decisions = []
            for i in range(1, len(portfolio_returns)):
                # If portfolio outperformed when market was up, good timing
                market_up = benchmark_returns[i] > 0
                portfolio_outperformed = portfolio_returns[i] > benchmark_returns[i]
                
                if market_up and portfolio_outperformed:
                    timing_decisions.append(1)  # Good timing
                elif not market_up and not portfolio_outperformed:
                    timing_decisions.append(1)  # Good timing (avoided losses)
                else:
                    timing_decisions.append(0)  # Poor timing
            
            if not timing_decisions:
                return None
            
            hit_rate = float(np.mean(timing_decisions))
            timing_skill = hit_rate - 0.5  # Skill above random
            
            # Estimate attribution from timing
            active_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
            timing_attribution = timing_skill * np.std(active_returns) * np.sqrt(252)
            
            # Statistical significance
            n = len(timing_decisions)
            success_count = sum(timing_decisions)
            # Binomial test approximation
            z_score = (success_count - n * 0.5) / np.sqrt(n * 0.25)
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
            
            return TimingAttribution(
                timing_type=TimingType.MARKET_TIMING,
                timing_skill=timing_skill,
                attribution=float(timing_attribution),
                hit_rate=hit_rate,
                average_magnitude=float(np.mean([abs(r) for r in active_returns])),
                t_statistic=float(z_score),
                p_value=float(p_value),
                significance="significant" if p_value < 0.05 else "not significant",
                confidence=1.0 - p_value if p_value < 0.05 else 0.0
            )
            
        except Exception as e:
            logger.error(f"Error in market timing analysis: {e}")
            return None
    
    async def _analyze_sector_timing(self, period_days: int) -> Optional[TimingAttribution]:
        """Analyze sector timing skill"""
        # Simplified placeholder - would need sector-specific data
        return TimingAttribution(
            timing_type=TimingType.SECTOR_TIMING,
            timing_skill=0.0,
            attribution=0.0,
            hit_rate=0.5,
            average_magnitude=0.0,
            t_statistic=0.0,
            p_value=1.0,
            significance="not significant",
            confidence=0.0
        )
    
    async def _analyze_factor_timing(self, period_days: int) -> Optional[TimingAttribution]:
        """Analyze factor timing skill"""
        # Simplified placeholder - would need factor timing data
        return TimingAttribution(
            timing_type=TimingType.FACTOR_TIMING,
            timing_skill=0.0,
            attribution=0.0,
            hit_rate=0.5,
            average_magnitude=0.0,
            t_statistic=0.0,
            p_value=1.0,
            significance="not significant",
            confidence=0.0
        )
    
    async def _analyze_volatility_timing(self, period_days: int) -> Optional[TimingAttribution]:
        """Analyze volatility timing skill"""
        try:
            recent_data = self.returns_history[-period_days:]
            
            # Calculate rolling volatility
            returns = [d['portfolio_return'] for d in recent_data]
            volatilities = []
            
            for i in range(10, len(returns)):  # 10-day rolling window
                vol = np.std(returns[i-10:i]) * np.sqrt(252)
                volatilities.append(vol)
            
            if len(volatilities) < 10:
                return None
            
            # Analyze timing based on position sizing in different vol regimes
            # Simplified: assume good vol timing = lower returns in high vol periods
            high_vol_threshold = np.percentile(volatilities, 75)
            
            timing_quality = []
            for i, vol in enumerate(volatilities):
                if i < len(returns) - 10:
                    period_return = abs(returns[i + 10])
                    if vol > high_vol_threshold:
                        # In high vol periods, lower returns = good timing
                        timing_quality.append(1 if period_return < np.median(returns) else 0)
                    else:
                        # In low vol periods, higher returns = good timing
                        timing_quality.append(1 if period_return > np.median(returns) else 0)
            
            if not timing_quality:
                return None
            
            hit_rate = float(np.mean(timing_quality))
            timing_skill = hit_rate - 0.5
            
            return TimingAttribution(
                timing_type=TimingType.VOLATILITY_TIMING,
                timing_skill=timing_skill,
                attribution=timing_skill * 0.02,  # Simplified attribution
                hit_rate=hit_rate,
                average_magnitude=float(np.std(volatilities)),
                t_statistic=0.0,
                p_value=0.1,
                significance="moderate" if abs(timing_skill) > 0.1 else "not significant",
                confidence=abs(timing_skill) if abs(timing_skill) > 0.1 else 0.0
            )
            
        except Exception as e:
            logger.error(f"Error in volatility timing analysis: {e}")
            return None
    
    def _calculate_alpha_consistency(self, returns: np.ndarray, factors: np.ndarray) -> float:
        """Calculate alpha consistency over time"""
        try:
            # Rolling alpha calculation
            window = 30
            alphas = []
            
            for i in range(window, len(returns)):
                window_returns = returns[i-window:i]
                window_factors = factors[i-window:i]
                
                X = sm.add_constant(window_factors)
                model = sm.OLS(window_returns, X).fit()
                alpha = float(model.params[0])
                alphas.append(alpha)
            
            if len(alphas) < 2:
                return 0.0
            
            # Consistency = 1 - (std of alphas / mean absolute alpha)
            alpha_std = np.std(alphas)
            alpha_mean_abs = np.mean([abs(a) for a in alphas])
            
            consistency = 1.0 - (alpha_std / (alpha_mean_abs + 1e-6))
            return max(0.0, min(1.0, consistency))
            
        except Exception as e:
            logger.error(f"Error calculating alpha consistency: {e}")
            return 0.0
    
    def _calculate_alpha_decay(self, period_days: int) -> float:
        """Calculate alpha decay over time"""
        try:
            # Simplified: compare recent vs older alpha
            if len(self.returns_history) < period_days * 2:
                return 0.0
            
            # Recent period alpha
            recent_data = self._prepare_attribution_data(period_days)
            recent_returns = recent_data['active_returns']
            recent_factors = recent_data['factor_matrix']
            
            X_recent = sm.add_constant(recent_factors)
            model_recent = sm.OLS(recent_returns, X_recent).fit()
            recent_alpha = float(model_recent.params[0])
            
            # Older period alpha
            older_start = len(self.returns_history) - period_days * 2
            older_data = self.returns_history[older_start:older_start + period_days]
            
            if len(older_data) < 30:
                return 0.0
            
            older_returns = np.array([d['active_return'] for d in older_data])
            
            # Simple alpha decay = (recent_alpha - older_alpha) / older_alpha
            older_alpha = float(np.mean(older_returns))
            
            if abs(older_alpha) < 1e-6:
                return 0.0
            
            decay = (recent_alpha - older_alpha) / older_alpha
            return float(decay)
            
        except Exception as e:
            logger.error(f"Error calculating alpha decay: {e}")
            return 0.0
    
    def get_attribution_summary(self) -> Dict[str, Any]:
        """Get attribution analysis summary"""
        with self.lock:
            latest_report = self.attribution_history[-1] if self.attribution_history else None
            
            return {
                'is_analyzing': self.is_analyzing,
                'data_points': len(self.returns_history),
                'latest_report': latest_report,
                'reports_generated': len(self.attribution_history),
                'factor_models': self.factor_models,
                'attribution_window': self.attribution_window,
                'confidence_level': self.confidence_level
            }

# Global attribution analyzer instance
attribution_analyzer = AttributionAnalyzer()

# Export main components
__all__ = [
    'AttributionAnalyzer',
    'FactorAttribution',
    'StrategyAttribution', 
    'TimingAttribution',
    'AlphaAttribution',
    'AttributionReport',
    'AttributionType',
    'FactorCategory',
    'TimingType',
    'attribution_analyzer'
]
