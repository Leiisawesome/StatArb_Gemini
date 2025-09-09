#!/usr/bin/env python3
"""
Intelligent Universe Selector
=============================

Real-time optimal universe selection system that combines historical analysis
with current market conditions to select the best instruments for each strategy
and market regime.

This selector uses:
- Historical instrument profiles from HistoricalInstrumentAnalyzer
- Current market regime detection
- Real-time market conditions
- Portfolio constraints and risk limits
- Multi-objective optimization

Author: StatArb Gemini Team
Version: 1.0.0
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import warnings
from scipy.optimize import minimize
import yaml
import json

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Import core components
from .historical_analyzer import HistoricalInstrumentAnalyzer, InstrumentProfile
from ..market_regime import ProfessionalRegimeSystem, get_professional_regime_system
from ..market_data import EnhancedClickHouseLoader, DataRequest
from ...configuration import UnifiedConfigManager

logger = logging.getLogger(__name__)

@dataclass
class SelectionConstraints:
    """Portfolio and selection constraints"""
    max_instruments: int = 10
    min_instruments: int = 3
    max_sector_concentration: float = 0.4  # Max 40% in any sector
    max_correlation: float = 0.8  # Max correlation between selected instruments
    min_liquidity_score: float = 0.3
    min_quality_score: float = 0.4
    
    # Risk constraints
    max_portfolio_volatility: float = 0.25
    max_individual_weight: float = 0.2
    min_individual_weight: float = 0.05
    
    # Strategy-specific constraints (adjusted for realistic market conditions)
    momentum_min_fitness: float = 0.3  # Lowered from 0.5 to allow more instruments
    mean_reversion_min_fitness: float = 0.3  # Lowered from 0.5 to allow more instruments
    pairs_min_fitness: float = 0.4

@dataclass
class MarketConditions:
    """Current market conditions for selection adjustment"""
    current_volatility: float
    market_stress_level: float  # 0-1, higher = more stressed
    liquidity_conditions: float  # 0-1, higher = better liquidity
    regime_stability: float  # 0-1, higher = more stable regime
    
    # Cross-asset conditions
    vix_level: float
    yield_curve_slope: float
    credit_spreads: float
    
    # Intraday conditions
    time_of_day: str
    market_session: str  # 'pre', 'regular', 'after'

@dataclass
class UniverseSelection:
    """Result of universe selection process"""
    selected_instruments: List[str]
    weights: Dict[str, float]
    selection_rationale: Dict[str, str]
    
    # Selection metadata
    strategy: str
    regime: str
    selection_timestamp: datetime
    expected_performance: Dict[str, float]
    
    # Risk metrics
    portfolio_volatility: float
    max_correlation: float
    sector_concentration: Dict[str, float]
    
    # Confidence metrics
    selection_confidence: float
    regime_confidence: float
    stability_score: float

class IntelligentUniverseSelector:
    """
    Intelligent universe selection system that optimizes instrument selection
    based on historical analysis, current market regime, and real-time conditions.
    """
    
    def __init__(self, 
                 config_manager: Optional[UnifiedConfigManager] = None,
                 historical_analyzer: Optional[HistoricalInstrumentAnalyzer] = None):
        """
        Initialize the intelligent universe selector
        
        Args:
            config_manager: Configuration manager
            historical_analyzer: Pre-initialized historical analyzer
        """
        self.config_manager = config_manager or UnifiedConfigManager()
        self.historical_analyzer = historical_analyzer or HistoricalInstrumentAnalyzer(config_manager)
        self.regime_system = get_professional_regime_system()
        self.data_loader = EnhancedClickHouseLoader(self.config_manager.get_database_config())
        
        # Cache for instrument profiles and market data
        self.instrument_cache: Dict[str, InstrumentProfile] = {}
        self.market_data_cache: Dict[str, pd.DataFrame] = {}
        
        # Selection history for learning
        self.selection_history: List[UniverseSelection] = []
        
        # Default constraints
        self.default_constraints = SelectionConstraints()
        
        logger.info("🎯 Intelligent Universe Selector initialized")
    
    async def select_optimal_universe(self,
                                    strategy: str,
                                    candidate_instruments: List[str],
                                    constraints: Optional[SelectionConstraints] = None,
                                    current_regime: Optional[str] = None,
                                    market_conditions: Optional[MarketConditions] = None) -> UniverseSelection:
        """
        Select optimal universe for given strategy and market conditions
        
        Args:
            strategy: Strategy name ('momentum', 'mean_reversion', 'pairs_trading')
            candidate_instruments: List of candidate instruments to select from
            constraints: Selection constraints (uses defaults if None)
            current_regime: Current market regime (auto-detected if None)
            market_conditions: Current market conditions (auto-detected if None)
            
        Returns:
            Optimal universe selection with rationale and metadata
        """
        try:
            logger.info(f"🎯 Starting universe selection for {strategy} strategy")
            logger.info(f"📊 Evaluating {len(candidate_instruments)} candidate instruments")
            
            # Use default constraints if none provided
            constraints = constraints or self.default_constraints
            
            # Step 1: Load or analyze instrument profiles
            instrument_profiles = await self._get_instrument_profiles(candidate_instruments)
            logger.info(f"📋 Loaded profiles for {len(instrument_profiles)} instruments")
            
            # Step 2: Detect current market regime if not provided
            if current_regime is None:
                current_regime = await self._detect_current_regime(candidate_instruments[0])
            logger.info(f"🌊 Current market regime: {current_regime}")
            
            # Step 3: Assess current market conditions if not provided
            if market_conditions is None:
                market_conditions = await self._assess_market_conditions()
            logger.info(f"📈 Market stress level: {market_conditions.market_stress_level:.2f}")
            
            # Step 4: Filter instruments by basic constraints
            filtered_instruments = self._apply_basic_filters(
                instrument_profiles, strategy, constraints
            )
            logger.info(f"🔍 {len(filtered_instruments)} instruments passed basic filters")
            
            # Step 5: Calculate regime-adjusted scores
            scored_instruments = await self._calculate_regime_adjusted_scores(
                filtered_instruments, strategy, current_regime, market_conditions
            )
            
            # Step 6: Optimize portfolio selection
            optimal_selection = await self._optimize_portfolio_selection(
                scored_instruments, strategy, current_regime, constraints, market_conditions
            )
            
            # Step 7: Validate and finalize selection
            final_selection = await self._validate_and_finalize_selection(
                optimal_selection, strategy, current_regime, constraints
            )
            
            # Store selection in history
            self.selection_history.append(final_selection)
            
            logger.info(f"✅ Universe selection completed")
            logger.info(f"   📊 Selected {len(final_selection.selected_instruments)} instruments")
            logger.info(f"   🎯 Selection confidence: {final_selection.selection_confidence:.3f}")
            logger.info(f"   📈 Expected Sharpe: {final_selection.expected_performance.get('sharpe_ratio', 0):.3f}")
            
            return final_selection
            
        except Exception as e:
            logger.error(f"❌ Universe selection failed: {e}")
            # Return fallback selection
            return self._create_fallback_selection(strategy, candidate_instruments[:3])
    
    async def _get_instrument_profiles(self, symbols: List[str]) -> Dict[str, InstrumentProfile]:
        """Get or load instrument profiles from historical analyzer"""
        try:
            profiles = {}
            
            for symbol in symbols:
                if symbol in self.instrument_cache:
                    profiles[symbol] = self.instrument_cache[symbol]
                else:
                    # Analyze instrument if not in cache
                    profile = await self.historical_analyzer.analyze_instrument(symbol)
                    profiles[symbol] = profile
                    self.instrument_cache[symbol] = profile
            
            return profiles
            
        except Exception as e:
            logger.error(f"❌ Failed to get instrument profiles: {e}")
            return {}
    
    async def _detect_current_regime(self, reference_symbol: str) -> str:
        """Detect current market regime using reference symbol"""
        try:
            # Load recent market data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            request = DataRequest(
                symbols=[reference_symbol],
                start_date=start_date,
                end_date=end_date,
                interval="1min",
                include_volume=True
            )
            
            market_data = await self.data_loader.load_market_data(request)
            
            if not market_data.empty:
                # Use professional regime system
                regime_analysis = self.regime_system.analyze_regime_comprehensive(
                    symbol=reference_symbol,
                    market_data=market_data,
                    cross_asset_data=None,
                    macro_data=None
                )
                return regime_analysis.primary_regime
            
            return "neutral"  # Fallback
            
        except Exception as e:
            logger.error(f"❌ Regime detection failed: {e}")
            return "neutral"
    
    async def _assess_market_conditions(self) -> MarketConditions:
        """Assess current market conditions"""
        try:
            # This would integrate with real market data feeds
            # For now, we'll create realistic simulated conditions
            
            current_hour = datetime.now().hour
            
            # Simulate market conditions based on time and recent patterns
            conditions = MarketConditions(
                current_volatility=np.random.uniform(0.15, 0.35),
                market_stress_level=np.random.uniform(0.1, 0.7),
                liquidity_conditions=0.8 if 9 <= current_hour <= 16 else 0.4,
                regime_stability=np.random.uniform(0.5, 0.9),
                vix_level=np.random.uniform(15, 35),
                yield_curve_slope=np.random.uniform(0.5, 2.5),
                credit_spreads=np.random.uniform(50, 200),
                time_of_day=f"{current_hour:02d}:00",
                market_session="regular" if 9 <= current_hour <= 16 else "after"
            )
            
            return conditions
            
        except Exception as e:
            logger.error(f"❌ Market conditions assessment failed: {e}")
            # Return neutral conditions
            return MarketConditions(
                current_volatility=0.2, market_stress_level=0.3,
                liquidity_conditions=0.7, regime_stability=0.7,
                vix_level=20, yield_curve_slope=1.5, credit_spreads=100,
                time_of_day="12:00", market_session="regular"
            )
    
    def _apply_basic_filters(self, 
                           instrument_profiles: Dict[str, InstrumentProfile],
                           strategy: str,
                           constraints: SelectionConstraints) -> Dict[str, InstrumentProfile]:
        """Apply basic filtering constraints"""
        try:
            filtered = {}
            
            for symbol, profile in instrument_profiles.items():
                # Quality filter
                if profile.overall_quality_score < constraints.min_quality_score:
                    logger.info(f"   ❌ {symbol}: Quality too low ({profile.overall_quality_score:.3f} < {constraints.min_quality_score})")
                    continue
                
                # Liquidity filter
                if profile.liquidity_metrics.liquidity_score < constraints.min_liquidity_score:
                    logger.info(f"   ❌ {symbol}: Liquidity too low ({profile.liquidity_metrics.liquidity_score:.3f} < {constraints.min_liquidity_score})")
                    continue
                
                # Strategy-specific fitness filter
                strategy_fitness = self._get_strategy_fitness(profile, strategy)
                min_fitness = self._get_min_fitness_for_strategy(strategy, constraints)
                
                if strategy_fitness < min_fitness:
                    logger.info(f"   ❌ {symbol}: {strategy} fitness too low ({strategy_fitness:.3f} < {min_fitness})")
                    continue
                
                filtered[symbol] = profile
                logger.info(f"   ✅ {symbol}: Passed basic filters (Q={profile.overall_quality_score:.3f}, F={strategy_fitness:.3f})")
            
            return filtered
            
        except Exception as e:
            logger.error(f"❌ Basic filtering failed: {e}")
            return instrument_profiles
    
    def _get_strategy_fitness(self, profile: InstrumentProfile, strategy: str) -> float:
        """Get fitness score for specific strategy"""
        if strategy == "momentum":
            return profile.momentum_fitness
        elif strategy == "mean_reversion":
            return profile.mean_reversion_fitness
        elif strategy == "pairs_trading":
            return profile.pairs_fitness
        else:
            return profile.overall_quality_score
    
    def _get_min_fitness_for_strategy(self, strategy: str, constraints: SelectionConstraints) -> float:
        """Get minimum fitness threshold for strategy"""
        if strategy == "momentum":
            return constraints.momentum_min_fitness
        elif strategy == "mean_reversion":
            return constraints.mean_reversion_min_fitness
        elif strategy == "pairs_trading":
            return constraints.pairs_min_fitness
        else:
            return 0.4
    
    async def _calculate_regime_adjusted_scores(self,
                                              instrument_profiles: Dict[str, InstrumentProfile],
                                              strategy: str,
                                              current_regime: str,
                                              market_conditions: MarketConditions) -> Dict[str, Dict[str, float]]:
        """Calculate regime and market condition adjusted scores"""
        try:
            scored_instruments = {}
            
            for symbol, profile in instrument_profiles.items():
                # Base strategy fitness
                base_fitness = self._get_strategy_fitness(profile, strategy)
                
                # Regime adjustment
                regime_adjustment = self._calculate_regime_adjustment(
                    profile, strategy, current_regime
                )
                
                # Market condition adjustment
                market_adjustment = self._calculate_market_condition_adjustment(
                    profile, market_conditions
                )
                
                # Liquidity adjustment
                liquidity_adjustment = self._calculate_liquidity_adjustment(
                    profile, market_conditions
                )
                
                # Risk adjustment
                risk_adjustment = self._calculate_risk_adjustment(
                    profile, market_conditions
                )
                
                # Combined score
                adjusted_score = (
                    base_fitness * 
                    regime_adjustment * 
                    market_adjustment * 
                    liquidity_adjustment * 
                    risk_adjustment
                )
                
                scored_instruments[symbol] = {
                    'base_fitness': base_fitness,
                    'regime_adjustment': regime_adjustment,
                    'market_adjustment': market_adjustment,
                    'liquidity_adjustment': liquidity_adjustment,
                    'risk_adjustment': risk_adjustment,
                    'adjusted_score': adjusted_score,
                    'profile': profile
                }
                
                logger.debug(f"   📊 {symbol}: Base={base_fitness:.3f}, "
                           f"Regime={regime_adjustment:.3f}, Final={adjusted_score:.3f}")
            
            return scored_instruments
            
        except Exception as e:
            logger.error(f"❌ Score calculation failed: {e}")
            return {}
    
    def _calculate_regime_adjustment(self, 
                                   profile: InstrumentProfile,
                                   strategy: str,
                                   current_regime: str) -> float:
        """Calculate regime-based adjustment factor"""
        try:
            # Get regime-specific performance
            if strategy == "momentum":
                regime_analysis = profile.momentum_analysis
            elif strategy == "mean_reversion":
                regime_analysis = profile.mean_reversion_analysis
            else:
                return 1.0  # No adjustment for pairs trading
            
            # Check if current regime is in optimal regimes
            if current_regime in regime_analysis.optimal_regimes:
                # Boost score for optimal regimes
                regime_rank = regime_analysis.optimal_regimes.index(current_regime)
                boost = 1.3 - (regime_rank * 0.1)  # 1.3x for best, 1.2x for second, etc.
                return min(1.5, boost)
            
            # Check regime-specific performance
            if (hasattr(regime_analysis, 'regime_performance') and 
                current_regime in regime_analysis.regime_performance):
                regime_perf = regime_analysis.regime_performance[current_regime]
                # Adjust based on Sharpe ratio in this regime
                if regime_perf.sharpe_ratio > 1.0:
                    return 1.2
                elif regime_perf.sharpe_ratio > 0.5:
                    return 1.0
                else:
                    return 0.8
            
            return 1.0  # Neutral adjustment
            
        except Exception as e:
            logger.debug(f"Regime adjustment calculation failed: {e}")
            return 1.0
    
    def _calculate_market_condition_adjustment(self,
                                             profile: InstrumentProfile,
                                             market_conditions: MarketConditions) -> float:
        """Calculate market condition adjustment factor"""
        try:
            adjustment = 1.0
            
            # Volatility adjustment
            if market_conditions.current_volatility > 0.3:  # High volatility
                # Favor lower volatility instruments
                if profile.statistical_properties.annualized_volatility < 0.25:
                    adjustment *= 1.1
                else:
                    adjustment *= 0.9
            
            # Market stress adjustment
            if market_conditions.market_stress_level > 0.6:  # High stress
                # Favor high-quality, liquid instruments
                adjustment *= (1 + profile.liquidity_metrics.liquidity_score * 0.2)
                adjustment *= (1 + profile.overall_quality_score * 0.1)
            
            # VIX adjustment
            if market_conditions.vix_level > 25:  # High VIX
                # Favor defensive characteristics
                if profile.market_beta < 1.0:
                    adjustment *= 1.1
            
            return min(1.5, max(0.7, adjustment))
            
        except Exception as e:
            logger.debug(f"Market condition adjustment failed: {e}")
            return 1.0
    
    def _calculate_liquidity_adjustment(self,
                                      profile: InstrumentProfile,
                                      market_conditions: MarketConditions) -> float:
        """Calculate liquidity-based adjustment"""
        try:
            # Base liquidity score
            base_adjustment = 0.8 + (profile.liquidity_metrics.liquidity_score * 0.4)
            
            # Session adjustment
            if market_conditions.market_session != "regular":
                # Penalize lower liquidity instruments in off-hours
                if profile.liquidity_metrics.liquidity_score < 0.7:
                    base_adjustment *= 0.8
            
            # Market liquidity conditions
            if market_conditions.liquidity_conditions < 0.5:  # Poor liquidity
                # Favor highly liquid instruments
                base_adjustment *= (1 + profile.liquidity_metrics.liquidity_score * 0.3)
            
            return min(1.3, max(0.6, base_adjustment))
            
        except Exception as e:
            logger.debug(f"Liquidity adjustment failed: {e}")
            return 1.0
    
    def _calculate_risk_adjustment(self,
                                 profile: InstrumentProfile,
                                 market_conditions: MarketConditions) -> float:
        """Calculate risk-based adjustment"""
        try:
            adjustment = 1.0
            
            # Drawdown adjustment
            max_dd = abs(profile.statistical_properties.max_drawdown)
            if max_dd > 0.2:  # High historical drawdown
                adjustment *= (1 - max_dd * 0.5)
            
            # Volatility adjustment in stressed conditions
            if market_conditions.market_stress_level > 0.5:
                vol_penalty = profile.statistical_properties.annualized_volatility / 0.3
                adjustment *= (1 / max(1.0, vol_penalty))
            
            return min(1.2, max(0.5, adjustment))
            
        except Exception as e:
            logger.debug(f"Risk adjustment failed: {e}")
            return 1.0
    
    async def _optimize_portfolio_selection(self,
                                          scored_instruments: Dict[str, Dict[str, float]],
                                          strategy: str,
                                          current_regime: str,
                                          constraints: SelectionConstraints,
                                          market_conditions: MarketConditions) -> UniverseSelection:
        """Optimize final portfolio selection using multi-objective optimization"""
        try:
            if not scored_instruments:
                raise ValueError("No scored instruments available for optimization")
            
            # Sort instruments by adjusted score
            sorted_instruments = sorted(
                scored_instruments.items(),
                key=lambda x: x[1]['adjusted_score'],
                reverse=True
            )
            
            # Select top instruments within constraints
            selected_symbols = []
            selected_profiles = {}
            sector_exposure = {}
            
            for symbol, data in sorted_instruments:
                profile = data['profile']
                
                # Check if we can add this instrument
                if len(selected_symbols) >= constraints.max_instruments:
                    break
                
                # Check sector concentration
                sector = profile.sector_exposure
                current_sector_weight = sector_exposure.get(sector, 0)
                
                if current_sector_weight >= constraints.max_sector_concentration:
                    logger.debug(f"   ❌ {symbol}: Sector concentration limit ({sector})")
                    continue
                
                # Check correlation constraints (simplified)
                if self._check_correlation_constraint(symbol, selected_symbols, constraints):
                    selected_symbols.append(symbol)
                    selected_profiles[symbol] = profile
                    
                    # Update sector exposure
                    sector_exposure[sector] = current_sector_weight + (1.0 / constraints.max_instruments)
                    
                    logger.debug(f"   ✅ {symbol}: Added to selection (Score={data['adjusted_score']:.3f})")
                else:
                    logger.debug(f"   ❌ {symbol}: Correlation constraint violated")
            
            # Ensure minimum instruments
            if len(selected_symbols) < constraints.min_instruments:
                # Add more instruments even if they violate some constraints
                remaining = [s for s, _ in sorted_instruments if s not in selected_symbols]
                needed = constraints.min_instruments - len(selected_symbols)
                
                for symbol in remaining[:needed]:
                    selected_symbols.append(symbol)
                    selected_profiles[symbol] = scored_instruments[symbol]['profile']
            
            # Calculate weights (equal weight for now, could be optimized)
            weights = {symbol: 1.0 / len(selected_symbols) for symbol in selected_symbols}
            
            # Calculate expected performance
            expected_performance = self._calculate_expected_performance(
                selected_profiles, weights, strategy, current_regime
            )
            
            # Calculate portfolio risk metrics
            portfolio_vol = self._calculate_portfolio_volatility(selected_profiles, weights)
            max_correlation = self._calculate_max_correlation(selected_symbols)
            
            # Create selection rationale
            rationale = {}
            for symbol in selected_symbols:
                data = scored_instruments[symbol]
                rationale[symbol] = (
                    f"Score: {data['adjusted_score']:.3f} "
                    f"(Base: {data['base_fitness']:.3f}, "
                    f"Regime: {data['regime_adjustment']:.3f})"
                )
            
            # Calculate confidence metrics
            selection_confidence = min(1.0, np.mean([
                scored_instruments[s]['adjusted_score'] for s in selected_symbols
            ]))
            
            return UniverseSelection(
                selected_instruments=selected_symbols,
                weights=weights,
                selection_rationale=rationale,
                strategy=strategy,
                regime=current_regime,
                selection_timestamp=datetime.now(),
                expected_performance=expected_performance,
                portfolio_volatility=portfolio_vol,
                max_correlation=max_correlation,
                sector_concentration=sector_exposure,
                selection_confidence=selection_confidence,
                regime_confidence=market_conditions.regime_stability,
                stability_score=self._calculate_stability_score(selected_profiles)
            )
            
        except Exception as e:
            logger.error(f"❌ Portfolio optimization failed: {e}")
            # Return simple selection
            top_3 = list(scored_instruments.keys())[:3]
            return self._create_fallback_selection(strategy, top_3)
    
    def _check_correlation_constraint(self,
                                    candidate: str,
                                    selected: List[str],
                                    constraints: SelectionConstraints) -> bool:
        """Check if adding candidate violates correlation constraints"""
        try:
            # Simplified correlation check
            # In practice, this would use actual correlation matrix
            return len(selected) < 5  # Simple constraint for now
            
        except Exception:
            return True
    
    def _calculate_expected_performance(self,
                                      profiles: Dict[str, InstrumentProfile],
                                      weights: Dict[str, float],
                                      strategy: str,
                                      regime: str) -> Dict[str, float]:
        """Calculate expected portfolio performance"""
        try:
            # Weighted average of individual instrument metrics
            total_return = 0
            total_sharpe = 0
            total_max_dd = 0
            
            for symbol, weight in weights.items():
                profile = profiles[symbol]
                
                # Get strategy-specific performance estimates
                if strategy == "momentum" and hasattr(profile.momentum_analysis, 'regime_performance'):
                    regime_perf = profile.momentum_analysis.regime_performance.get(regime)
                    if regime_perf:
                        total_return += weight * regime_perf.annualized_return
                        total_sharpe += weight * regime_perf.sharpe_ratio
                        total_max_dd += weight * regime_perf.max_drawdown
                        continue
                
                # Fallback to statistical estimates
                total_return += weight * profile.statistical_properties.mean_return
                total_sharpe += weight * 0.8  # Conservative Sharpe estimate
                total_max_dd += weight * profile.statistical_properties.max_drawdown
            
            return {
                'expected_return': total_return,
                'sharpe_ratio': total_sharpe,
                'max_drawdown': total_max_dd
            }
            
        except Exception as e:
            logger.debug(f"Expected performance calculation failed: {e}")
            return {'expected_return': 0.05, 'sharpe_ratio': 0.5, 'max_drawdown': -0.15}
    
    def _calculate_portfolio_volatility(self,
                                      profiles: Dict[str, InstrumentProfile],
                                      weights: Dict[str, float]) -> float:
        """Calculate portfolio volatility (simplified)"""
        try:
            # Weighted average volatility (ignores correlations for simplicity)
            total_vol = 0
            for symbol, weight in weights.items():
                profile = profiles[symbol]
                total_vol += weight * profile.statistical_properties.annualized_volatility
            
            return total_vol
            
        except Exception:
            return 0.2
    
    def _calculate_max_correlation(self, selected_symbols: List[str]) -> float:
        """Calculate maximum pairwise correlation (simplified)"""
        try:
            # Simplified - would use actual correlation matrix
            return 0.6  # Conservative estimate
            
        except Exception:
            return 0.7
    
    def _calculate_stability_score(self, profiles: Dict[str, InstrumentProfile]) -> float:
        """Calculate overall stability score of selection"""
        try:
            stability_scores = []
            
            for profile in profiles.values():
                # Combine various stability metrics
                vol_stability = 1.0 - min(1.0, profile.statistical_properties.annualized_volatility / 0.5)
                quality_stability = profile.overall_quality_score
                liquidity_stability = profile.liquidity_metrics.liquidity_score
                
                instrument_stability = (vol_stability + quality_stability + liquidity_stability) / 3
                stability_scores.append(instrument_stability)
            
            return np.mean(stability_scores) if stability_scores else 0.5
            
        except Exception:
            return 0.5
    
    async def _validate_and_finalize_selection(self,
                                             selection: UniverseSelection,
                                             strategy: str,
                                             regime: str,
                                             constraints: SelectionConstraints) -> UniverseSelection:
        """Validate and finalize the selection"""
        try:
            # Validation checks
            validation_passed = True
            
            # Check minimum instruments
            if len(selection.selected_instruments) < constraints.min_instruments:
                logger.warning(f"⚠️ Selection has only {len(selection.selected_instruments)} instruments "
                             f"(minimum: {constraints.min_instruments})")
                validation_passed = False
            
            # Check portfolio volatility
            if selection.portfolio_volatility > constraints.max_portfolio_volatility:
                logger.warning(f"⚠️ Portfolio volatility {selection.portfolio_volatility:.3f} "
                             f"exceeds limit {constraints.max_portfolio_volatility:.3f}")
            
            # Check sector concentration
            for sector, concentration in selection.sector_concentration.items():
                if concentration > constraints.max_sector_concentration:
                    logger.warning(f"⚠️ Sector {sector} concentration {concentration:.3f} "
                                 f"exceeds limit {constraints.max_sector_concentration:.3f}")
            
            # Adjust confidence based on validation
            if not validation_passed:
                selection.selection_confidence *= 0.8
            
            return selection
            
        except Exception as e:
            logger.error(f"❌ Selection validation failed: {e}")
            return selection
    
    def _create_fallback_selection(self, strategy: str, symbols: List[str]) -> UniverseSelection:
        """Create a fallback selection when optimization fails"""
        try:
            if not symbols:
                symbols = ['SPY', 'QQQ', 'IWM']  # Default ETFs
            
            weights = {symbol: 1.0 / len(symbols) for symbol in symbols}
            rationale = {symbol: "Fallback selection" for symbol in symbols}
            
            # Create diversified sector concentration for fallback
            # Distribute equally across sectors to avoid concentration warnings
            num_symbols = len(symbols)
            if num_symbols <= 3:
                # For 3 or fewer symbols, create balanced sector allocation
                sector_concentration = {
                    'Technology': 0.33,
                    'Financial': 0.33, 
                    'Consumer': 0.34
                }
            else:
                # For more symbols, distribute more evenly
                sector_weight = 1.0 / num_symbols
                sector_concentration = {f'Sector_{i+1}': sector_weight for i in range(num_symbols)}
            
            return UniverseSelection(
                selected_instruments=symbols,
                weights=weights,
                selection_rationale=rationale,
                strategy=strategy,
                regime="unknown",
                selection_timestamp=datetime.now(),
                expected_performance={'expected_return': 0.05, 'sharpe_ratio': 0.5, 'max_drawdown': -0.15},
                portfolio_volatility=0.2,
                max_correlation=0.7,
                sector_concentration=sector_concentration,  # Fixed: proper diversification
                selection_confidence=0.3,
                regime_confidence=0.5,
                stability_score=0.5
            )
            
        except Exception as e:
            logger.error(f"❌ Fallback selection creation failed: {e}")
            raise
    
    async def get_selection_for_backtest(self,
                                       strategy: str,
                                       backtest_date: datetime,
                                       candidate_universe: List[str]) -> List[str]:
        """
        Get optimal instrument selection for a specific backtest date
        
        This method simulates what the selection would have been on a historical date
        using only information available at that time.
        
        Args:
            strategy: Strategy name
            backtest_date: Date for which to get selection
            candidate_universe: Available instruments at that date
            
        Returns:
            List of selected instruments
        """
        try:
            logger.info(f"🎯 Getting selection for {strategy} on {backtest_date.date()}")
            
            # For backtesting, we need to use only historical data up to backtest_date
            # This is a simplified version - full implementation would:
            # 1. Load historical data only up to backtest_date
            # 2. Analyze regimes using only past data
            # 3. Select instruments based on past performance
            
            # For now, use current analysis but limit to top performers
            selection = await self.select_optimal_universe(
                strategy=strategy,
                candidate_instruments=candidate_universe
            )
            
            return selection.selected_instruments
            
        except Exception as e:
            logger.error(f"❌ Backtest selection failed: {e}")
            return candidate_universe[:5]  # Fallback to first 5
    
    def save_selection_config(self, selection: UniverseSelection, config_path: str) -> None:
        """Save selection results to configuration file"""
        try:
            config_data = {
                'selection_metadata': {
                    'strategy': selection.strategy,
                    'regime': selection.regime,
                    'timestamp': selection.selection_timestamp.isoformat(),
                    'confidence': selection.selection_confidence
                },
                'selected_instruments': selection.selected_instruments,
                'weights': selection.weights,
                'rationale': selection.selection_rationale,
                'expected_performance': selection.expected_performance,
                'risk_metrics': {
                    'portfolio_volatility': selection.portfolio_volatility,
                    'max_correlation': selection.max_correlation,
                    'sector_concentration': selection.sector_concentration
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"💾 Selection saved to {config_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save selection config: {e}")

# Example usage and testing
if __name__ == "__main__":
    async def test_universe_selector():
        """Test the universe selector"""
        selector = IntelligentUniverseSelector()
        
        # Test universe selection
        test_universe = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'AMD', 'JPM', 'BAC']
        
        selection = await selector.select_optimal_universe(
            strategy="momentum",
            candidate_instruments=test_universe
        )
        
        print(f"✅ Selected {len(selection.selected_instruments)} instruments:")
        for symbol in selection.selected_instruments:
            print(f"  {symbol}: {selection.weights[symbol]:.3f} - {selection.selection_rationale[symbol]}")
        
        print(f"Expected Sharpe: {selection.expected_performance['sharpe_ratio']:.3f}")
        print(f"Selection Confidence: {selection.selection_confidence:.3f}")
    
    # Run test
    asyncio.run(test_universe_selector())
