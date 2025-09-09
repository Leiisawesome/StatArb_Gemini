#!/usr/bin/env python3
"""
Instrument Fitness Calculator
=============================

Advanced multi-factor scoring system for evaluating instrument fitness across
different strategies and market regimes. This calculator combines statistical
analysis, regime-dependent performance, and real-time market conditions to
provide comprehensive fitness scores.

Key Features:
- Multi-dimensional fitness scoring
- Regime-dependent adjustments
- Real-time market condition integration
- Strategy-specific optimization
- Risk-adjusted performance metrics

Author: StatArb Gemini Team
Version: 1.0.0
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import warnings
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
import yaml

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Import core components
from .historical_analyzer import InstrumentProfile, StatisticalProperties, LiquidityMetrics, RegimeAnalysis
from ..market_regime import ProfessionalRegimeSystem

logger = logging.getLogger(__name__)

@dataclass
class FitnessWeights:
    """Weights for different fitness components"""
    # Performance components
    historical_performance: float = 0.35
    regime_suitability: float = 0.25
    statistical_properties: float = 0.20
    
    # Risk components
    risk_metrics: float = 0.15
    liquidity_quality: float = 0.05
    
    # Strategy-specific adjustments
    momentum_bias: float = 0.0
    mean_reversion_bias: float = 0.0
    pairs_trading_bias: float = 0.0

@dataclass
class FitnessComponents:
    """Individual fitness component scores"""
    # Core components (0-1 scale)
    performance_score: float
    regime_score: float
    statistical_score: float
    risk_score: float
    liquidity_score: float
    
    # Composite scores
    raw_fitness: float
    adjusted_fitness: float
    normalized_fitness: float
    
    # Component details
    component_breakdown: Dict[str, float] = field(default_factory=dict)
    adjustment_factors: Dict[str, float] = field(default_factory=dict)

@dataclass
class FitnessRanking:
    """Fitness ranking results"""
    symbol: str
    fitness_score: float
    rank: int
    percentile: float
    
    # Detailed breakdown
    components: FitnessComponents
    strengths: List[str]
    weaknesses: List[str]
    
    # Comparative metrics
    relative_to_benchmark: float
    sector_relative: float
    strategy_suitability: str

class InstrumentFitnessCalculator:
    """
    Advanced multi-factor fitness calculator that evaluates instruments across
    multiple dimensions and provides comprehensive scoring for strategy selection.
    """
    
    def __init__(self, 
                 strategy_focus: Optional[str] = None,
                 custom_weights: Optional[FitnessWeights] = None):
        """
        Initialize fitness calculator
        
        Args:
            strategy_focus: Primary strategy to optimize for ('momentum', 'mean_reversion', 'pairs_trading')
            custom_weights: Custom weights for fitness components
        """
        self.strategy_focus = strategy_focus
        self.weights = custom_weights or self._get_default_weights(strategy_focus)
        
        # Normalization scalers
        self.performance_scaler = MinMaxScaler()
        self.risk_scaler = MinMaxScaler()
        self.statistical_scaler = StandardScaler()
        
        # Benchmark metrics for relative scoring
        self.benchmark_metrics = self._initialize_benchmark_metrics()
        
        # Fitness calculation cache
        self.fitness_cache: Dict[str, FitnessComponents] = {}
        
        logger.info(f"🧮 Fitness Calculator initialized")
        if strategy_focus:
            logger.info(f"   🎯 Strategy focus: {strategy_focus}")
        logger.info(f"   ⚖️ Weights: Perf={self.weights.historical_performance:.2f}, "
                   f"Regime={self.weights.regime_suitability:.2f}, "
                   f"Stats={self.weights.statistical_properties:.2f}")
    
    def _get_default_weights(self, strategy_focus: Optional[str]) -> FitnessWeights:
        """Get default weights based on strategy focus"""
        base_weights = FitnessWeights()
        
        if strategy_focus == "momentum":
            # Emphasize performance and regime suitability for momentum
            base_weights.historical_performance = 0.40
            base_weights.regime_suitability = 0.30
            base_weights.statistical_properties = 0.15
            base_weights.risk_metrics = 0.10
            base_weights.liquidity_quality = 0.05
            base_weights.momentum_bias = 0.1
            
        elif strategy_focus == "mean_reversion":
            # Emphasize statistical properties and risk for mean reversion
            base_weights.historical_performance = 0.30
            base_weights.regime_suitability = 0.25
            base_weights.statistical_properties = 0.25
            base_weights.risk_metrics = 0.15
            base_weights.liquidity_quality = 0.05
            base_weights.mean_reversion_bias = 0.1
            
        elif strategy_focus == "pairs_trading":
            # Emphasize statistical properties and liquidity for pairs
            base_weights.historical_performance = 0.25
            base_weights.regime_suitability = 0.20
            base_weights.statistical_properties = 0.30
            base_weights.risk_metrics = 0.15
            base_weights.liquidity_quality = 0.10
            base_weights.pairs_trading_bias = 0.1
        
        return base_weights
    
    def _initialize_benchmark_metrics(self) -> Dict[str, float]:
        """Initialize benchmark metrics for relative scoring"""
        return {
            # Performance benchmarks
            'benchmark_sharpe': 0.8,
            'benchmark_return': 0.08,
            'benchmark_max_dd': -0.15,
            
            # Risk benchmarks
            'benchmark_volatility': 0.20,
            'benchmark_beta': 1.0,
            
            # Statistical benchmarks
            'benchmark_autocorr': 0.05,
            'benchmark_half_life': 10.0,
            
            # Liquidity benchmarks
            'benchmark_volume': 1000000,
            'benchmark_spread': 5.0
        }
    
    def calculate_fitness(self, 
                         profile: InstrumentProfile,
                         current_regime: Optional[str] = None,
                         market_conditions: Optional[Dict[str, float]] = None) -> FitnessComponents:
        """
        Calculate comprehensive fitness score for an instrument
        
        Args:
            profile: Instrument profile from historical analysis
            current_regime: Current market regime for regime-specific scoring
            market_conditions: Current market conditions for real-time adjustments
            
        Returns:
            Detailed fitness components and scores
        """
        try:
            cache_key = f"{profile.symbol}_{current_regime}_{hash(str(market_conditions))}"
            
            # Check cache first
            if cache_key in self.fitness_cache:
                return self.fitness_cache[cache_key]
            
            logger.debug(f"🧮 Calculating fitness for {profile.symbol}")
            
            # Calculate individual component scores
            performance_score = self._calculate_performance_score(profile, current_regime)
            regime_score = self._calculate_regime_score(profile, current_regime)
            statistical_score = self._calculate_statistical_score(profile)
            risk_score = self._calculate_risk_score(profile)
            liquidity_score = self._calculate_liquidity_score(profile)
            
            # Calculate raw fitness using weights
            raw_fitness = (
                performance_score * self.weights.historical_performance +
                regime_score * self.weights.regime_suitability +
                statistical_score * self.weights.statistical_properties +
                risk_score * self.weights.risk_metrics +
                liquidity_score * self.weights.liquidity_quality
            )
            
            # Apply strategy-specific adjustments
            adjusted_fitness = self._apply_strategy_adjustments(
                raw_fitness, profile, current_regime
            )
            
            # Apply market condition adjustments
            if market_conditions:
                adjusted_fitness = self._apply_market_condition_adjustments(
                    adjusted_fitness, profile, market_conditions
                )
            
            # Normalize to 0-1 scale
            normalized_fitness = min(1.0, max(0.0, adjusted_fitness))
            
            # Create detailed breakdown
            component_breakdown = {
                'performance': performance_score,
                'regime_suitability': regime_score,
                'statistical_properties': statistical_score,
                'risk_metrics': risk_score,
                'liquidity_quality': liquidity_score
            }
            
            adjustment_factors = {
                'strategy_adjustment': adjusted_fitness / max(0.001, raw_fitness),
                'market_condition_adjustment': 1.0  # Would be calculated if conditions provided
            }
            
            # Create fitness components
            fitness = FitnessComponents(
                performance_score=performance_score,
                regime_score=regime_score,
                statistical_score=statistical_score,
                risk_score=risk_score,
                liquidity_score=liquidity_score,
                raw_fitness=raw_fitness,
                adjusted_fitness=adjusted_fitness,
                normalized_fitness=normalized_fitness,
                component_breakdown=component_breakdown,
                adjustment_factors=adjustment_factors
            )
            
            # Cache result
            self.fitness_cache[cache_key] = fitness
            
            logger.debug(f"   📊 {profile.symbol}: Raw={raw_fitness:.3f}, "
                        f"Adjusted={adjusted_fitness:.3f}, Final={normalized_fitness:.3f}")
            
            return fitness
            
        except Exception as e:
            logger.error(f"❌ Fitness calculation failed for {profile.symbol}: {e}")
            # Return neutral fitness
            return self._create_neutral_fitness()
    
    def _calculate_performance_score(self, 
                                   profile: InstrumentProfile,
                                   current_regime: Optional[str] = None) -> float:
        """Calculate performance-based fitness score"""
        try:
            scores = []
            
            # Strategy-specific performance
            if self.strategy_focus == "momentum":
                # Use momentum analysis
                if hasattr(profile.momentum_analysis, 'regime_performance') and current_regime:
                    regime_perf = profile.momentum_analysis.regime_performance.get(current_regime)
                    if regime_perf:
                        # Sharpe ratio component
                        sharpe_score = min(1.0, max(0.0, (regime_perf.sharpe_ratio + 1) / 3))
                        scores.append(sharpe_score * 0.4)
                        
                        # Return component
                        return_score = min(1.0, max(0.0, regime_perf.annualized_return / 0.2))
                        scores.append(return_score * 0.3)
                        
                        # Win rate component
                        win_rate_score = regime_perf.win_rate
                        scores.append(win_rate_score * 0.3)
                
                # Fallback to momentum fitness
                if not scores:
                    scores.append(profile.momentum_fitness)
                    
            elif self.strategy_focus == "mean_reversion":
                # Use mean reversion analysis
                if hasattr(profile.mean_reversion_analysis, 'regime_performance') and current_regime:
                    regime_perf = profile.mean_reversion_analysis.regime_performance.get(current_regime)
                    if regime_perf:
                        sharpe_score = min(1.0, max(0.0, (regime_perf.sharpe_ratio + 1) / 3))
                        scores.append(sharpe_score * 0.5)
                        
                        # Lower drawdown is better for mean reversion
                        dd_score = min(1.0, max(0.0, 1.0 + regime_perf.max_drawdown / 0.3))
                        scores.append(dd_score * 0.5)
                
                # Fallback to mean reversion fitness
                if not scores:
                    scores.append(profile.mean_reversion_fitness)
                    
            elif self.strategy_focus == "pairs_trading":
                # Use pairs trading suitability
                scores.append(profile.pairs_fitness)
                
            else:
                # Use overall quality score
                scores.append(profile.overall_quality_score)
            
            # Combine scores
            if scores:
                performance_score = np.mean(scores)
            else:
                performance_score = 0.5  # Neutral score
            
            return min(1.0, max(0.0, performance_score))
            
        except Exception as e:
            logger.debug(f"Performance score calculation failed: {e}")
            return 0.5
    
    def _calculate_regime_score(self, 
                              profile: InstrumentProfile,
                              current_regime: Optional[str] = None) -> float:
        """Calculate regime suitability score"""
        try:
            if not current_regime:
                return 0.7  # Neutral score when regime unknown
            
            regime_scores = []
            
            # Check momentum regime suitability
            if hasattr(profile.momentum_analysis, 'optimal_regimes'):
                if current_regime in profile.momentum_analysis.optimal_regimes:
                    regime_rank = profile.momentum_analysis.optimal_regimes.index(current_regime)
                    momentum_regime_score = 1.0 - (regime_rank * 0.2)  # 1.0, 0.8, 0.6, etc.
                else:
                    momentum_regime_score = 0.3  # Poor regime for momentum
                regime_scores.append(momentum_regime_score)
            
            # Check mean reversion regime suitability
            if hasattr(profile.mean_reversion_analysis, 'optimal_regimes'):
                if current_regime in profile.mean_reversion_analysis.optimal_regimes:
                    regime_rank = profile.mean_reversion_analysis.optimal_regimes.index(current_regime)
                    mr_regime_score = 1.0 - (regime_rank * 0.2)
                else:
                    mr_regime_score = 0.3  # Poor regime for mean reversion
                regime_scores.append(mr_regime_score)
            
            # Weight by strategy focus
            if self.strategy_focus == "momentum" and len(regime_scores) > 0:
                return regime_scores[0]
            elif self.strategy_focus == "mean_reversion" and len(regime_scores) > 1:
                return regime_scores[1]
            elif regime_scores:
                return np.mean(regime_scores)
            
            return 0.7  # Default neutral score
            
        except Exception as e:
            logger.debug(f"Regime score calculation failed: {e}")
            return 0.7
    
    def _calculate_statistical_score(self, profile: InstrumentProfile) -> float:
        """Calculate statistical properties score"""
        try:
            stats_props = profile.statistical_properties
            scores = []
            
            # Volatility score (moderate volatility preferred)
            vol_score = self._score_volatility(stats_props.annualized_volatility)
            scores.append(vol_score * 0.25)
            
            # Autocorrelation score (strategy dependent)
            autocorr_score = self._score_autocorrelation(
                stats_props.autocorr_lag1, self.strategy_focus
            )
            scores.append(autocorr_score * 0.25)
            
            # Mean reversion properties
            if self.strategy_focus == "mean_reversion":
                # Faster mean reversion is better
                mr_score = min(1.0, stats_props.ou_theta / 0.5)
                scores.append(mr_score * 0.3)
                
                # Shorter half-life is better
                half_life_score = min(1.0, max(0.0, 1.0 - stats_props.half_life / 50))
                scores.append(half_life_score * 0.2)
            
            # Momentum properties
            elif self.strategy_focus == "momentum":
                # Higher momentum persistence is better
                momentum_score = stats_props.momentum_persistence
                scores.append(momentum_score * 0.3)
                
                # Higher trend strength is better
                trend_score = stats_props.trend_strength
                scores.append(trend_score * 0.2)
            
            # Pairs trading properties
            elif self.strategy_focus == "pairs_trading":
                # Lower volatility clustering is better for pairs
                vol_clustering_score = 1.0 - min(1.0, stats_props.volatility_clustering)
                scores.append(vol_clustering_score * 0.5)
            
            # Return distribution properties
            skew_score = self._score_skewness(stats_props.skewness)
            scores.append(skew_score * 0.1)
            
            kurtosis_score = self._score_kurtosis(stats_props.kurtosis)
            scores.append(kurtosis_score * 0.1)
            
            return min(1.0, max(0.0, np.sum(scores)))
            
        except Exception as e:
            logger.debug(f"Statistical score calculation failed: {e}")
            return 0.5
    
    def _score_volatility(self, volatility: float) -> float:
        """Score volatility (moderate levels preferred)"""
        # Optimal volatility range: 15-30%
        if 0.15 <= volatility <= 0.30:
            return 1.0
        elif 0.10 <= volatility <= 0.40:
            return 0.8
        elif 0.05 <= volatility <= 0.50:
            return 0.6
        else:
            return 0.3
    
    def _score_autocorrelation(self, autocorr: float, strategy: Optional[str]) -> float:
        """Score autocorrelation based on strategy"""
        if strategy == "momentum":
            # Positive autocorrelation good for momentum
            return min(1.0, max(0.0, autocorr * 2 + 0.5))
        elif strategy == "mean_reversion":
            # Negative autocorrelation good for mean reversion
            return min(1.0, max(0.0, -autocorr * 2 + 0.5))
        else:
            # Neutral preference
            return 0.7
    
    def _score_skewness(self, skewness: float) -> float:
        """Score return distribution skewness"""
        # Slight positive skew preferred (0 to 0.5)
        if 0 <= skewness <= 0.5:
            return 1.0
        elif -0.5 <= skewness <= 1.0:
            return 0.8
        else:
            return 0.5
    
    def _score_kurtosis(self, kurtosis: float) -> float:
        """Score return distribution kurtosis"""
        # Moderate kurtosis preferred (2-5)
        if 2 <= kurtosis <= 5:
            return 1.0
        elif 1 <= kurtosis <= 7:
            return 0.8
        else:
            return 0.5
    
    def _calculate_risk_score(self, profile: InstrumentProfile) -> float:
        """Calculate risk-adjusted score"""
        try:
            risk_scores = []
            
            # Maximum drawdown score (lower is better)
            max_dd = abs(profile.statistical_properties.max_drawdown)
            dd_score = min(1.0, max(0.0, 1.0 - max_dd / 0.3))  # Normalize by 30% max DD
            risk_scores.append(dd_score * 0.4)
            
            # Volatility score (from risk perspective - lower is better)
            vol = profile.statistical_properties.annualized_volatility
            vol_risk_score = min(1.0, max(0.0, 1.0 - vol / 0.5))  # Normalize by 50% vol
            risk_scores.append(vol_risk_score * 0.3)
            
            # Beta score (closer to 1.0 is better for diversification)
            beta_score = 1.0 - min(1.0, abs(profile.market_beta - 1.0))
            risk_scores.append(beta_score * 0.2)
            
            # Tail risk score (based on skewness and kurtosis)
            skew = profile.statistical_properties.skewness
            kurt = profile.statistical_properties.kurtosis
            
            # Negative skew and high kurtosis indicate tail risk
            tail_risk = max(0, -skew) + max(0, (kurt - 3) / 5)
            tail_score = min(1.0, max(0.0, 1.0 - tail_risk))
            risk_scores.append(tail_score * 0.1)
            
            return np.sum(risk_scores)
            
        except Exception as e:
            logger.debug(f"Risk score calculation failed: {e}")
            return 0.5
    
    def _calculate_liquidity_score(self, profile: InstrumentProfile) -> float:
        """Calculate liquidity quality score"""
        try:
            # Use the pre-calculated liquidity score from the profile
            base_score = profile.liquidity_metrics.liquidity_score
            
            # Additional adjustments based on specific metrics
            adjustments = []
            
            # Volume adjustment
            if profile.liquidity_metrics.avg_daily_volume > 5000000:  # High volume
                adjustments.append(0.1)
            elif profile.liquidity_metrics.avg_daily_volume < 500000:  # Low volume
                adjustments.append(-0.2)
            
            # Spread adjustment
            if profile.liquidity_metrics.bid_ask_spread_bps < 3:  # Tight spread
                adjustments.append(0.1)
            elif profile.liquidity_metrics.bid_ask_spread_bps > 10:  # Wide spread
                adjustments.append(-0.2)
            
            # Market impact adjustment
            if profile.liquidity_metrics.market_impact_bps < 2:  # Low impact
                adjustments.append(0.05)
            elif profile.liquidity_metrics.market_impact_bps > 5:  # High impact
                adjustments.append(-0.1)
            
            adjusted_score = base_score + sum(adjustments)
            return min(1.0, max(0.0, adjusted_score))
            
        except Exception as e:
            logger.debug(f"Liquidity score calculation failed: {e}")
            return 0.5
    
    def _apply_strategy_adjustments(self, 
                                  base_fitness: float,
                                  profile: InstrumentProfile,
                                  current_regime: Optional[str] = None) -> float:
        """Apply strategy-specific adjustments to fitness score"""
        try:
            adjusted_fitness = base_fitness
            
            if self.strategy_focus == "momentum":
                # Boost for high momentum characteristics
                momentum_boost = (
                    profile.statistical_properties.momentum_persistence * 0.1 +
                    profile.statistical_properties.trend_strength * 0.1 +
                    max(0, profile.statistical_properties.autocorr_lag1) * 0.1
                )
                adjusted_fitness += momentum_boost
                
            elif self.strategy_focus == "mean_reversion":
                # Boost for mean reversion characteristics
                mr_boost = (
                    min(1.0, profile.statistical_properties.ou_theta / 0.5) * 0.1 +
                    max(0, -profile.statistical_properties.autocorr_lag1) * 0.1 +
                    (1.0 - min(1.0, profile.statistical_properties.half_life / 50)) * 0.05
                )
                adjusted_fitness += mr_boost
                
            elif self.strategy_focus == "pairs_trading":
                # Boost for pairs trading characteristics
                pairs_boost = (
                    profile.liquidity_metrics.liquidity_score * 0.1 +
                    (1.0 - profile.statistical_properties.volatility_clustering) * 0.05
                )
                adjusted_fitness += pairs_boost
            
            return adjusted_fitness
            
        except Exception as e:
            logger.debug(f"Strategy adjustment failed: {e}")
            return base_fitness
    
    def _apply_market_condition_adjustments(self,
                                          base_fitness: float,
                                          profile: InstrumentProfile,
                                          market_conditions: Dict[str, float]) -> float:
        """Apply real-time market condition adjustments"""
        try:
            adjusted_fitness = base_fitness
            
            # High volatility environment adjustments
            if market_conditions.get('market_volatility', 0.2) > 0.3:
                # Favor lower volatility instruments
                if profile.statistical_properties.annualized_volatility < 0.25:
                    adjusted_fitness += 0.05
                else:
                    adjusted_fitness -= 0.05
            
            # Market stress adjustments
            stress_level = market_conditions.get('market_stress', 0.3)
            if stress_level > 0.6:
                # Favor high-quality, liquid instruments during stress
                quality_boost = profile.overall_quality_score * 0.1
                liquidity_boost = profile.liquidity_metrics.liquidity_score * 0.05
                adjusted_fitness += quality_boost + liquidity_boost
            
            # Liquidity condition adjustments
            liquidity_conditions = market_conditions.get('liquidity_conditions', 0.7)
            if liquidity_conditions < 0.5:
                # Penalize low liquidity instruments when market liquidity is poor
                if profile.liquidity_metrics.liquidity_score < 0.6:
                    adjusted_fitness -= 0.1
            
            return adjusted_fitness
            
        except Exception as e:
            logger.debug(f"Market condition adjustment failed: {e}")
            return base_fitness
    
    def _create_neutral_fitness(self) -> FitnessComponents:
        """Create neutral fitness components for fallback"""
        return FitnessComponents(
            performance_score=0.5,
            regime_score=0.5,
            statistical_score=0.5,
            risk_score=0.5,
            liquidity_score=0.5,
            raw_fitness=0.5,
            adjusted_fitness=0.5,
            normalized_fitness=0.5,
            component_breakdown={
                'performance': 0.5,
                'regime_suitability': 0.5,
                'statistical_properties': 0.5,
                'risk_metrics': 0.5,
                'liquidity_quality': 0.5
            },
            adjustment_factors={'strategy_adjustment': 1.0, 'market_condition_adjustment': 1.0}
        )
    
    def rank_instruments(self, 
                        profiles: Dict[str, InstrumentProfile],
                        current_regime: Optional[str] = None,
                        market_conditions: Optional[Dict[str, float]] = None) -> List[FitnessRanking]:
        """
        Rank multiple instruments by fitness score
        
        Args:
            profiles: Dictionary of instrument profiles
            current_regime: Current market regime
            market_conditions: Current market conditions
            
        Returns:
            List of fitness rankings sorted by score (highest first)
        """
        try:
            logger.info(f"🏆 Ranking {len(profiles)} instruments by fitness")
            
            # Calculate fitness for all instruments
            fitness_results = {}
            for symbol, profile in profiles.items():
                fitness = self.calculate_fitness(profile, current_regime, market_conditions)
                fitness_results[symbol] = fitness
            
            # Sort by normalized fitness score
            sorted_results = sorted(
                fitness_results.items(),
                key=lambda x: x[1].normalized_fitness,
                reverse=True
            )
            
            # Create rankings
            rankings = []
            total_instruments = len(sorted_results)
            
            for rank, (symbol, fitness) in enumerate(sorted_results, 1):
                percentile = (total_instruments - rank + 1) / total_instruments
                
                # Identify strengths and weaknesses
                strengths, weaknesses = self._identify_strengths_weaknesses(fitness)
                
                # Calculate relative metrics
                benchmark_fitness = 0.6  # Assumed benchmark
                relative_to_benchmark = fitness.normalized_fitness / benchmark_fitness
                
                # Sector relative (simplified)
                sector_relative = 1.0  # Would calculate actual sector average
                
                # Strategy suitability
                strategy_suitability = self._determine_strategy_suitability(fitness)
                
                ranking = FitnessRanking(
                    symbol=symbol,
                    fitness_score=fitness.normalized_fitness,
                    rank=rank,
                    percentile=percentile,
                    components=fitness,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    relative_to_benchmark=relative_to_benchmark,
                    sector_relative=sector_relative,
                    strategy_suitability=strategy_suitability
                )
                
                rankings.append(ranking)
            
            logger.info(f"✅ Ranking completed")
            logger.info(f"   🥇 Top instrument: {rankings[0].symbol} (Score: {rankings[0].fitness_score:.3f})")
            logger.info(f"   📊 Score range: {rankings[-1].fitness_score:.3f} - {rankings[0].fitness_score:.3f}")
            
            return rankings
            
        except Exception as e:
            logger.error(f"❌ Instrument ranking failed: {e}")
            return []
    
    def _identify_strengths_weaknesses(self, fitness: FitnessComponents) -> Tuple[List[str], List[str]]:
        """Identify strengths and weaknesses from fitness components"""
        try:
            strengths = []
            weaknesses = []
            
            # Check each component against thresholds
            components = fitness.component_breakdown
            
            if components.get('performance', 0) > 0.7:
                strengths.append("Strong Historical Performance")
            elif components.get('performance', 0) < 0.4:
                weaknesses.append("Weak Historical Performance")
            
            if components.get('regime_suitability', 0) > 0.7:
                strengths.append("Excellent Regime Fit")
            elif components.get('regime_suitability', 0) < 0.4:
                weaknesses.append("Poor Regime Fit")
            
            if components.get('statistical_properties', 0) > 0.7:
                strengths.append("Favorable Statistical Properties")
            elif components.get('statistical_properties', 0) < 0.4:
                weaknesses.append("Unfavorable Statistical Properties")
            
            if components.get('risk_metrics', 0) > 0.7:
                strengths.append("Low Risk Profile")
            elif components.get('risk_metrics', 0) < 0.4:
                weaknesses.append("High Risk Profile")
            
            if components.get('liquidity_quality', 0) > 0.7:
                strengths.append("High Liquidity")
            elif components.get('liquidity_quality', 0) < 0.4:
                weaknesses.append("Low Liquidity")
            
            return strengths, weaknesses
            
        except Exception as e:
            logger.debug(f"Strength/weakness identification failed: {e}")
            return ["Analysis Available"], ["Detailed Analysis Needed"]
    
    def _determine_strategy_suitability(self, fitness: FitnessComponents) -> str:
        """Determine overall strategy suitability"""
        try:
            score = fitness.normalized_fitness
            
            if score > 0.8:
                return "Excellent"
            elif score > 0.6:
                return "Good"
            elif score > 0.4:
                return "Fair"
            else:
                return "Poor"
                
        except Exception:
            return "Unknown"
    
    def generate_fitness_report(self, 
                              rankings: List[FitnessRanking],
                              output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive fitness analysis report
        
        Args:
            rankings: List of fitness rankings
            output_path: Optional path to save report
            
        Returns:
            Report dictionary
        """
        try:
            logger.info("📋 Generating fitness analysis report")
            
            # Summary statistics
            scores = [r.fitness_score for r in rankings]
            summary_stats = {
                'total_instruments': len(rankings),
                'mean_fitness': np.mean(scores),
                'median_fitness': np.median(scores),
                'std_fitness': np.std(scores),
                'min_fitness': np.min(scores),
                'max_fitness': np.max(scores)
            }
            
            # Top performers
            top_performers = rankings[:5]
            
            # Bottom performers
            bottom_performers = rankings[-3:]
            
            # Strategy suitability distribution
            suitability_dist = {}
            for ranking in rankings:
                suit = ranking.strategy_suitability
                suitability_dist[suit] = suitability_dist.get(suit, 0) + 1
            
            # Component analysis
            component_averages = {}
            for component in ['performance', 'regime_suitability', 'statistical_properties', 'risk_metrics', 'liquidity_quality']:
                values = [r.components.component_breakdown.get(component, 0) for r in rankings]
                component_averages[component] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values)
                }
            
            # Create report
            report = {
                'report_metadata': {
                    'generation_time': datetime.now().isoformat(),
                    'strategy_focus': self.strategy_focus,
                    'total_instruments_analyzed': len(rankings)
                },
                'summary_statistics': summary_stats,
                'top_performers': [
                    {
                        'symbol': r.symbol,
                        'fitness_score': r.fitness_score,
                        'rank': r.rank,
                        'percentile': r.percentile,
                        'strengths': r.strengths,
                        'strategy_suitability': r.strategy_suitability
                    }
                    for r in top_performers
                ],
                'bottom_performers': [
                    {
                        'symbol': r.symbol,
                        'fitness_score': r.fitness_score,
                        'rank': r.rank,
                        'weaknesses': r.weaknesses
                    }
                    for r in bottom_performers
                ],
                'suitability_distribution': suitability_dist,
                'component_analysis': component_averages,
                'recommendations': self._generate_recommendations(rankings)
            }
            
            # Save report if path provided
            if output_path:
                with open(output_path, 'w') as f:
                    yaml.dump(report, f, default_flow_style=False, sort_keys=False)
                logger.info(f"💾 Fitness report saved to {output_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return {}
    
    def _generate_recommendations(self, rankings: List[FitnessRanking]) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        try:
            # Analyze top performers
            top_5 = rankings[:5]
            
            # Check if there's a clear winner
            if len(top_5) > 1 and top_5[0].fitness_score > top_5[1].fitness_score + 0.1:
                recommendations.append(
                    f"Strong recommendation: {top_5[0].symbol} shows clear superiority "
                    f"with fitness score {top_5[0].fitness_score:.3f}"
                )
            
            # Check for strategy alignment
            excellent_count = sum(1 for r in rankings if r.strategy_suitability == "Excellent")
            if excellent_count == 0:
                recommendations.append(
                    "Consider expanding candidate universe - no instruments show excellent strategy fit"
                )
            elif excellent_count > 10:
                recommendations.append(
                    f"Rich candidate pool with {excellent_count} excellent instruments - "
                    "consider additional filtering criteria"
                )
            
            # Check for diversification
            top_sectors = {}
            for r in rankings[:10]:
                # Would analyze actual sectors
                sector = "Technology"  # Simplified
                top_sectors[sector] = top_sectors.get(sector, 0) + 1
            
            max_sector_count = max(top_sectors.values()) if top_sectors else 0
            if max_sector_count > 6:
                recommendations.append(
                    "High sector concentration in top performers - consider diversification"
                )
            
            # Performance distribution analysis
            scores = [r.fitness_score for r in rankings]
            if np.std(scores) < 0.1:
                recommendations.append(
                    "Low fitness score variance - consider additional discriminating factors"
                )
            
            return recommendations
            
        except Exception as e:
            logger.debug(f"Recommendation generation failed: {e}")
            return ["Detailed analysis completed - review individual instrument scores"]

# Example usage and testing
if __name__ == "__main__":
    def test_fitness_calculator():
        """Test the fitness calculator"""
        # This would use actual instrument profiles
        logger.info("🧮 Testing Fitness Calculator")
        
        calculator = InstrumentFitnessCalculator(strategy_focus="momentum")
        
        # Test with mock profile (would use real profiles in practice)
        print("✅ Fitness Calculator test completed")
    
    # Run test
    test_fitness_calculator()
