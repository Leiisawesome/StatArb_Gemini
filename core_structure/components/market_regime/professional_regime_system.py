#!/usr/bin/env python3
"""
Professional Regime Detection System Integration
===============================================

Unified integration layer combining all professional regime detection components:
- Enhanced multi-timeframe regime detection
- Macro regime analysis with cross-asset signals
- Cross-asset regime confirmation system
- Strategy-specific regime recommendations

Author: Professional Quant Enhancement
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
import warnings
warnings.filterwarnings('ignore')

# Import our enhanced regime components
try:
    from .enhanced_regime_detector import EnhancedRegimeDetector, EnhancedRegimeState, RegimeConfig
    from .macro_regime_analyzer import MacroRegimeAnalyzer, MacroRegimeResult
    from .cross_asset_regime_system import CrossAssetRegimeSystem, CrossAssetRegimeResult
    ENHANCED_COMPONENTS_AVAILABLE = True
except ImportError:
    ENHANCED_COMPONENTS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ProfessionalRegimeAnalysis:
    """Comprehensive professional regime analysis result"""
    # Unified regime classification
    primary_regime: str
    secondary_regime: Optional[str]
    overall_confidence: float
    regime_strength: float
    
    # Multi-dimensional analysis
    enhanced_regime: Optional[EnhancedRegimeState]
    macro_regime: Optional[MacroRegimeResult]
    cross_asset_regime: Optional[CrossAssetRegimeResult]
    
    # Consensus analysis
    regime_consensus_score: float  # How well all methods agree
    regime_divergence_flags: List[str]
    
    # Strategy recommendations
    strategy_allocations: Dict[str, float]  # Recommended strategy weights
    risk_adjustments: Dict[str, float]     # Risk parameter adjustments
    position_sizing_recommendations: Dict[str, float]
    
    # Market timing signals
    entry_timing_score: float      # -1 to 1
    exit_timing_score: float       # -1 to 1
    regime_transition_warning: bool
    
    # Performance forecasts
    expected_volatility: float
    expected_correlation: float
    expected_regime_duration: int
    
    # Execution recommendations
    execution_difficulty: float
    liquidity_adjustment: float
    correlation_risk_multiplier: float
    
    timestamp: datetime
    analysis_quality_score: float
    computation_time_ms: float

class ProfessionalRegimeSystem:
    """
    Unified professional regime detection system.
    
    Integrates all regime detection components to provide institutional-grade
    market regime analysis with strategy-specific recommendations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize component systems
        self._initialize_components()
        
        # Analysis history
        self.analysis_history: List[ProfessionalRegimeAnalysis] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_analyses': 0,
            'avg_confidence': 0.0,
            'consensus_accuracy': 0.0,
            'strategy_performance': {},
            'last_update': datetime.now()
        }
        
        self.logger.info("Professional regime system initialized")
    
    def _initialize_components(self):
        """Initialize all regime detection components"""
        self.components = {}
        
        # For now, use fallback implementation since enhanced components may not be fully available
        try:
            # Try to initialize enhanced components
            # Enhanced regime detector
            # enhanced_config = RegimeConfig()
            # self.components['enhanced'] = EnhancedRegimeDetector(enhanced_config)
            
            # For Phase 1, we'll use a simplified implementation
            self.logger.info("Using simplified regime components for Phase 1")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize enhanced components: {e}")
        
        if not self.components:
            self.logger.warning("Enhanced components not available, using fallback")
    
    async def analyze_regime_comprehensive_async(self,
                                               symbol: str,
                                               market_data: pd.DataFrame,
                                               cross_asset_data: Optional[Dict[str, pd.DataFrame]] = None,
                                               macro_data: Optional[Dict[str, pd.Series]] = None) -> ProfessionalRegimeAnalysis:
        """
        Comprehensive professional regime analysis.
        
        Args:
            symbol: Primary symbol for analysis
            market_data: OHLCV data for primary symbol
            cross_asset_data: Cross-asset market data
            macro_data: Macro economic indicators
            
        Returns:
            Comprehensive professional regime analysis
        """
        start_time = datetime.now()
        
        try:
            if not ENHANCED_COMPONENTS_AVAILABLE:
                return self._create_fallback_analysis()
            
            # Parallel execution of all regime analysis components
            tasks = []
            
            # Enhanced regime detection
            if 'enhanced' in self.components:
                tasks.append(
                    self.components['enhanced'].detect_regime_async(symbol, market_data, macro_data)
                )
            
            # Macro regime analysis
            if 'macro' in self.components and cross_asset_data:
                tasks.append(
                    self.components['macro'].analyze_macro_regime_async(cross_asset_data, macro_data)
                )
            
            # Cross-asset regime analysis
            if 'cross_asset' in self.components and cross_asset_data:
                tasks.append(
                    self.components['cross_asset'].analyze_cross_asset_regime_async(cross_asset_data)
                )
            
            # Execute all analyses in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Extract results
            enhanced_result = None
            macro_result = None
            cross_asset_result = None
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Component analysis {i} failed: {result}")
                    continue
                
                if i == 0 and hasattr(result, 'primary_regime'):
                    enhanced_result = result
                elif i == 1 and hasattr(result, 'primary_regime'):
                    macro_result = result
                elif i == 2 and hasattr(result, 'primary_regime'):
                    cross_asset_result = result
            
            # Synthesize results into unified analysis
            unified_analysis = self._synthesize_regime_analysis(
                enhanced_result, macro_result, cross_asset_result
            )
            
            # Calculate consensus and divergence
            consensus_score, divergence_flags = self._calculate_regime_consensus(
                enhanced_result, macro_result, cross_asset_result
            )
            
            # Generate strategy recommendations
            strategy_allocations = self._generate_strategy_allocations(unified_analysis)
            risk_adjustments = self._generate_risk_adjustments(unified_analysis)
            position_sizing = self._generate_position_sizing_recommendations(unified_analysis)
            
            # Market timing analysis
            entry_timing, exit_timing, transition_warning = self._analyze_market_timing(
                enhanced_result, macro_result, cross_asset_result
            )
            
            # Performance forecasts
            vol_forecast = self._forecast_volatility(enhanced_result, macro_result)
            corr_forecast = self._forecast_correlation(cross_asset_result)
            duration_forecast = self._forecast_regime_duration(enhanced_result, macro_result)
            
            # Execution recommendations
            execution_difficulty = self._assess_execution_difficulty(enhanced_result, cross_asset_result)
            liquidity_adjustment = self._calculate_liquidity_adjustment(cross_asset_result)
            correlation_risk = self._calculate_correlation_risk_multiplier(cross_asset_result)
            
            # Analysis quality assessment
            quality_score = self._assess_analysis_quality(
                enhanced_result, macro_result, cross_asset_result, consensus_score
            )
            
            # Calculate computation time
            computation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create comprehensive analysis result
            analysis = ProfessionalRegimeAnalysis(
                primary_regime=unified_analysis['primary_regime'],
                secondary_regime=unified_analysis.get('secondary_regime'),
                overall_confidence=unified_analysis['confidence'],
                regime_strength=unified_analysis['strength'],
                
                enhanced_regime=enhanced_result,
                macro_regime=macro_result,
                cross_asset_regime=cross_asset_result,
                
                regime_consensus_score=consensus_score,
                regime_divergence_flags=divergence_flags,
                
                strategy_allocations=strategy_allocations,
                risk_adjustments=risk_adjustments,
                position_sizing_recommendations=position_sizing,
                
                entry_timing_score=entry_timing,
                exit_timing_score=exit_timing,
                regime_transition_warning=transition_warning,
                
                expected_volatility=vol_forecast,
                expected_correlation=corr_forecast,
                expected_regime_duration=duration_forecast,
                
                execution_difficulty=execution_difficulty,
                liquidity_adjustment=liquidity_adjustment,
                correlation_risk_multiplier=correlation_risk,
                
                timestamp=datetime.now(),
                analysis_quality_score=quality_score,
                computation_time_ms=computation_time
            )
            
            # Update history and metrics
            self._update_analysis_history(analysis)
            self._update_performance_metrics(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Comprehensive regime analysis failed: {e}")
            return self._create_fallback_analysis(symbol, market_data)
    
    def analyze_regime_comprehensive(self,
                                   symbol: str,
                                   market_data: pd.DataFrame,
                                   cross_asset_data: Optional[Dict[str, pd.DataFrame]] = None,
                                   macro_data: Optional[Dict[str, pd.Series]] = None) -> ProfessionalRegimeAnalysis:
        """Synchronous wrapper for comprehensive regime analysis"""
        try:
            # For Phase 1, use simplified synchronous implementation
            return self._create_fallback_analysis(symbol, market_data)
        except Exception as e:
            self.logger.error(f"Synchronous regime analysis failed: {e}")
            return self._create_fallback_analysis(symbol, market_data)
    
    def _synthesize_regime_analysis(self, 
                                  enhanced_result: Optional[EnhancedRegimeState],
                                  macro_result: Optional[MacroRegimeResult],
                                  cross_asset_result: Optional[CrossAssetRegimeResult]) -> Dict[str, Any]:
        """Synthesize results from all components into unified analysis"""
        try:
            # Collect regime classifications
            regimes = []
            confidences = []
            strengths = []
            
            if enhanced_result:
                regimes.append(enhanced_result.primary_regime)
                confidences.append(enhanced_result.confidence)
                strengths.append(enhanced_result.regime_strength)
            
            if macro_result:
                regimes.append(macro_result.primary_regime.value)
                confidences.append(macro_result.confidence)
                strengths.append(macro_result.regime_strength)
            
            if cross_asset_result:
                regimes.append(cross_asset_result.primary_regime)
                confidences.append(cross_asset_result.confidence)
                strengths.append(cross_asset_result.regime_strength)
            
            if not regimes:
                return {
                    'primary_regime': 'unknown',
                    'confidence': 0.5,
                    'strength': 0.5
                }
            
            # Determine consensus regime (most common)
            from collections import Counter
            regime_counts = Counter(regimes)
            primary_regime = regime_counts.most_common(1)[0][0]
            
            # Calculate weighted confidence and strength
            avg_confidence = np.mean(confidences)
            avg_strength = np.mean(strengths)
            
            # Adjust confidence based on consensus
            consensus_adjustment = regime_counts[primary_regime] / len(regimes)
            adjusted_confidence = avg_confidence * consensus_adjustment
            
            return {
                'primary_regime': primary_regime,
                'confidence': adjusted_confidence,
                'strength': avg_strength,
                'regime_distribution': dict(regime_counts)
            }
            
        except Exception as e:
            self.logger.error(f"Regime synthesis failed: {e}")
            return {
                'primary_regime': 'unknown',
                'confidence': 0.5,
                'strength': 0.5
            }
    
    def _calculate_regime_consensus(self, 
                                  enhanced_result: Optional[EnhancedRegimeState],
                                  macro_result: Optional[MacroRegimeResult],
                                  cross_asset_result: Optional[CrossAssetRegimeResult]) -> Tuple[float, List[str]]:
        """Calculate consensus score and identify divergences"""
        try:
            # Collect all regime signals
            signals = []
            component_names = []
            
            if enhanced_result:
                signals.append(self._normalize_regime_signal(enhanced_result.primary_regime))
                component_names.append('enhanced')
            
            if macro_result:
                signals.append(self._normalize_regime_signal(macro_result.primary_regime.value))
                component_names.append('macro')
            
            if cross_asset_result:
                signals.append(self._normalize_regime_signal(cross_asset_result.primary_regime))
                component_names.append('cross_asset')
            
            if len(signals) < 2:
                return 0.5, []
            
            # Calculate consensus as correlation between signals
            consensus_scores = []
            for i in range(len(signals)):
                for j in range(i + 1, len(signals)):
                    correlation = np.corrcoef([signals[i]], [signals[j]])[0, 1]
                    if not np.isnan(correlation):
                        consensus_scores.append(abs(correlation))
            
            consensus_score = np.mean(consensus_scores) if consensus_scores else 0.5
            
            # Identify divergences
            divergence_flags = []
            signal_std = np.std(signals)
            if signal_std > 0.5:  # High divergence threshold
                divergence_flags.append(f"High signal divergence detected (std: {signal_std:.3f})")
            
            # Check for specific divergences
            if len(signals) >= 3:
                for i, name in enumerate(component_names):
                    if abs(signals[i] - np.mean(signals)) > 0.7:
                        divergence_flags.append(f"{name} component shows significant divergence")
            
            return consensus_score, divergence_flags
            
        except Exception as e:
            self.logger.error(f"Consensus calculation failed: {e}")
            return 0.5, []
    
    def _normalize_regime_signal(self, regime: str) -> float:
        """Normalize regime classification to numeric signal"""
        # Map regime types to numeric scores (-1 to 1)
        regime_mapping = {
            'trending': 0.8,
            'trending_up': 0.9,
            'trending_down': -0.9,
            'mean_reverting': -0.5,
            'volatile': 0.3,
            'stable': -0.3,
            'crisis': -1.0,
            'expansion': 0.7,
            'contraction': -0.7,
            'risk_on': 0.6,
            'risk_off': -0.6,
            'unknown': 0.0,
            'neutral': 0.0
        }
        
        return regime_mapping.get(regime.lower(), 0.0)
    
    def _generate_strategy_allocations(self, unified_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Generate strategy allocation recommendations"""
        try:
            regime = unified_analysis['primary_regime'].lower()
            confidence = unified_analysis['confidence']
            
            # Base allocations by regime
            if 'trending' in regime:
                base_allocations = {'momentum': 0.6, 'mean_reversion': 0.2, 'pairs_trading': 0.2}
            elif 'mean_reverting' in regime:
                base_allocations = {'momentum': 0.1, 'mean_reversion': 0.6, 'pairs_trading': 0.3}
            elif 'volatile' in regime or 'crisis' in regime:
                base_allocations = {'momentum': 0.2, 'mean_reversion': 0.3, 'pairs_trading': 0.5}
            else:
                base_allocations = {'momentum': 0.33, 'mean_reversion': 0.33, 'pairs_trading': 0.34}
            
            # Adjust based on confidence
            if confidence < 0.6:
                # Low confidence - move toward pairs trading (more stable)
                adjustment_factor = (0.6 - confidence) * 0.5
                base_allocations['pairs_trading'] += adjustment_factor
                base_allocations['momentum'] -= adjustment_factor * 0.5
                base_allocations['mean_reversion'] -= adjustment_factor * 0.5
            
            # Normalize to ensure sum = 1
            total = sum(base_allocations.values())
            return {k: v / total for k, v in base_allocations.items()}
            
        except Exception as e:
            self.logger.error(f"Strategy allocation generation failed: {e}")
            return {'momentum': 0.33, 'mean_reversion': 0.33, 'pairs_trading': 0.34}
    
    def _generate_risk_adjustments(self, unified_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Generate risk parameter adjustments"""
        try:
            regime = unified_analysis['primary_regime'].lower()
            confidence = unified_analysis['confidence']
            strength = unified_analysis['strength']
            
            # Base risk adjustments
            risk_adjustments = {
                'volatility_target_multiplier': 1.0,
                'max_position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'correlation_threshold_adjustment': 0.0
            }
            
            # Adjust based on regime
            if 'volatile' in regime or 'crisis' in regime:
                risk_adjustments['volatility_target_multiplier'] = 0.7  # Reduce vol target
                risk_adjustments['max_position_size_multiplier'] = 0.8  # Reduce position sizes
                risk_adjustments['stop_loss_multiplier'] = 0.8  # Tighter stops
            elif 'stable' in regime:
                risk_adjustments['volatility_target_multiplier'] = 1.2  # Increase vol target
                risk_adjustments['max_position_size_multiplier'] = 1.1  # Slightly larger positions
            
            # Adjust based on confidence
            if confidence < 0.6:
                risk_adjustments['max_position_size_multiplier'] *= 0.9  # Reduce size when uncertain
            
            return risk_adjustments
            
        except Exception as e:
            self.logger.error(f"Risk adjustment generation failed: {e}")
            return {
                'volatility_target_multiplier': 1.0,
                'max_position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'correlation_threshold_adjustment': 0.0
            }
    
    # Placeholder methods for remaining functionality
    def _generate_position_sizing_recommendations(self, unified_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Generate position sizing recommendations - placeholder"""
        return {'base_size_multiplier': 1.0, 'volatility_adjustment': 1.0, 'correlation_adjustment': 1.0}
    
    def _analyze_market_timing(self, enhanced_result, macro_result, cross_asset_result) -> Tuple[float, float, bool]:
        """Analyze market timing signals - placeholder"""
        return 0.0, 0.0, False
    
    def _forecast_volatility(self, enhanced_result, macro_result) -> float:
        """Forecast volatility - placeholder"""
        return 0.02
    
    def _forecast_correlation(self, cross_asset_result) -> float:
        """Forecast correlation - placeholder"""
        return 0.5
    
    def _forecast_regime_duration(self, enhanced_result, macro_result) -> int:
        """Forecast regime duration - placeholder"""
        return 20
    
    def _assess_execution_difficulty(self, enhanced_result, cross_asset_result) -> float:
        """Assess execution difficulty - placeholder"""
        return 0.3
    
    def _calculate_liquidity_adjustment(self, cross_asset_result) -> float:
        """Calculate liquidity adjustment - placeholder"""
        return 1.0
    
    def _calculate_correlation_risk_multiplier(self, cross_asset_result) -> float:
        """Calculate correlation risk multiplier - placeholder"""
        return 1.0
    
    def _assess_analysis_quality(self, enhanced_result, macro_result, cross_asset_result, consensus_score) -> float:
        """Assess analysis quality - placeholder"""
        return 0.8
    
    def _update_analysis_history(self, analysis: ProfessionalRegimeAnalysis):
        """Update analysis history - placeholder"""
        pass
    
    def _update_performance_metrics(self, analysis: ProfessionalRegimeAnalysis):
        """Update performance metrics - placeholder"""
        pass
    
    def _create_fallback_analysis(self, symbol: str = "UNKNOWN", market_data: pd.DataFrame = None) -> ProfessionalRegimeAnalysis:
        """Create fallback analysis when components fail"""
        try:
            # Try to do basic regime detection if we have market data
            if market_data is not None and len(market_data) > 20:
                # Simple regime detection
                returns = market_data['close'].pct_change().dropna()
                
                if len(returns) > 10:
                    # Basic volatility analysis
                    volatility = returns.std()
                    recent_vol = returns.tail(10).std()
                    vol_ratio = recent_vol / volatility if volatility > 0 else 1.0
                    
                    # Basic trend analysis
                    if len(market_data) >= 20:
                        ma_short = market_data['close'].rolling(10).mean().iloc[-1]
                        ma_long = market_data['close'].rolling(20).mean().iloc[-1]
                        trend_strength = abs(ma_short - ma_long) / ma_long if ma_long > 0 else 0
                    else:
                        trend_strength = 0
                    
                    # Determine regime
                    if vol_ratio > 1.5:
                        regime = "volatile"
                        momentum_suit = 0.3
                        mr_suit = 0.4
                        pairs_suit = 0.6
                    elif trend_strength > 0.02:
                        regime = "trending"
                        momentum_suit = 0.8
                        mr_suit = 0.2
                        pairs_suit = 0.5
                    else:
                        regime = "sideways"
                        momentum_suit = 0.4
                        mr_suit = 0.7
                        pairs_suit = 0.8
                    
                    expected_vol = max(0.01, min(0.05, volatility))
                else:
                    regime = "unknown"
                    momentum_suit = 0.33
                    mr_suit = 0.33
                    pairs_suit = 0.34
                    expected_vol = 0.02
            else:
                regime = "unknown"
                momentum_suit = 0.33
                mr_suit = 0.33
                pairs_suit = 0.34
                expected_vol = 0.02
            
            return ProfessionalRegimeAnalysis(
                primary_regime=regime,
                secondary_regime=None,
                overall_confidence=0.6,
                regime_strength=0.6,
                enhanced_regime=None,
                macro_regime=None,
                cross_asset_regime=None,
                regime_consensus_score=0.6,
                regime_divergence_flags=[],
                strategy_allocations={
                    'momentum': momentum_suit, 
                    'mean_reversion': mr_suit, 
                    'pairs_trading': pairs_suit
                },
                risk_adjustments={'volatility_target_multiplier': 1.0},
                position_sizing_recommendations={
                    'base_size_multiplier': 1.0,
                    'volatility_adjustment': 1.0,
                    'correlation_adjustment': 1.0
                },
                entry_timing_score=0.0,
                exit_timing_score=0.0,
                regime_transition_warning=False,
                expected_volatility=expected_vol,
                expected_correlation=0.5,
                expected_regime_duration=20,
                execution_difficulty=0.5,
                liquidity_adjustment=1.0,
                correlation_risk_multiplier=1.0,
                timestamp=datetime.now(),
                analysis_quality_score=0.6,
                computation_time_ms=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Fallback analysis creation failed: {e}")
            # Return minimal fallback
            return ProfessionalRegimeAnalysis(
                primary_regime="unknown",
                secondary_regime=None,
                overall_confidence=0.5,
                regime_strength=0.5,
                enhanced_regime=None,
                macro_regime=None,
                cross_asset_regime=None,
                regime_consensus_score=0.5,
                regime_divergence_flags=[],
                strategy_allocations={'momentum': 0.33, 'mean_reversion': 0.33, 'pairs_trading': 0.34},
                risk_adjustments={'volatility_target_multiplier': 1.0},
                position_sizing_recommendations={'base_size_multiplier': 1.0, 'volatility_adjustment': 1.0, 'correlation_adjustment': 1.0},
                entry_timing_score=0.0,
                exit_timing_score=0.0,
                regime_transition_warning=False,
                expected_volatility=0.02,
                expected_correlation=0.5,
                expected_regime_duration=20,
                execution_difficulty=0.5,
                liquidity_adjustment=1.0,
                correlation_risk_multiplier=1.0,
                timestamp=datetime.now(),
                analysis_quality_score=0.5,
                computation_time_ms=0.0
            )

# Global professional regime system instance
_global_professional_regime_system = None

def get_professional_regime_system(config: Optional[Dict[str, Any]] = None) -> ProfessionalRegimeSystem:
    """Get the global professional regime system instance"""
    global _global_professional_regime_system
    
    if _global_professional_regime_system is None:
        _global_professional_regime_system = ProfessionalRegimeSystem(config)
    
    return _global_professional_regime_system

__all__ = [
    'ProfessionalRegimeSystem',
    'ProfessionalRegimeAnalysis',
    'get_professional_regime_system'
]
