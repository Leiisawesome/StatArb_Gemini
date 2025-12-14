#!/usr/bin/env python3
"""
Regime-Aware Signal Enhancer
============================

Enhances generated signals with regime context for better decision-making.

Week 3 Day 2: Adds regime awareness to signal generation pipeline.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RegimeSignalAdjustment(Enum):
    """Signal adjustment strategies based on regime"""
    AMPLIFY = "amplify"       # Increase signal confidence
    REDUCE = "reduce"          # Decrease signal confidence
    FILTER = "filter"          # Filter out signals
    MAINTAIN = "maintain"      # Keep signal unchanged

@dataclass
class RegimeAwareSignal:
    """Signal enhanced with regime context"""
    original_signal: Any
    regime: str
    regime_confidence: float
    adjustment: RegimeSignalAdjustment
    adjusted_confidence: float
    regime_compatible: bool
    adjustment_reason: str

class RegimeAwareSignalEnhancer:
    """
    Enhances trading signals with regime awareness

    Adjusts signal confidence based on market regime compatibility:
    - Momentum signals amplified in trending regimes
    - Mean reversion signals amplified in ranging regimes
    - Signals filtered in incompatible regimes
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.regime_engine = None

        # Regime compatibility matrix
        self.regime_compatibility = {
            'trending': {
                'momentum': RegimeSignalAdjustment.AMPLIFY,
                'breakout': RegimeSignalAdjustment.AMPLIFY,
                'trend_following': RegimeSignalAdjustment.AMPLIFY,
                'mean_reversion': RegimeSignalAdjustment.REDUCE,
                'stat_arb': RegimeSignalAdjustment.REDUCE
            },
            'ranging': {
                'mean_reversion': RegimeSignalAdjustment.AMPLIFY,
                'stat_arb': RegimeSignalAdjustment.AMPLIFY,
                'momentum': RegimeSignalAdjustment.REDUCE,
                'breakout': RegimeSignalAdjustment.FILTER
            },
            'high_volatility': {
                'momentum': RegimeSignalAdjustment.REDUCE,
                'mean_reversion': RegimeSignalAdjustment.REDUCE,
                'all': RegimeSignalAdjustment.REDUCE  # Reduce all signals
            },
            'low_volatility': {
                'mean_reversion': RegimeSignalAdjustment.AMPLIFY,
                'momentum': RegimeSignalAdjustment.MAINTAIN
            },
            'crisis': {
                'all': RegimeSignalAdjustment.FILTER  # Filter most signals in crisis
            }
        }

        # Adjustment multipliers
        self.adjustment_multipliers = {
            RegimeSignalAdjustment.AMPLIFY: 1.25,  # +25% confidence
            RegimeSignalAdjustment.REDUCE: 0.70,    # -30% confidence
            RegimeSignalAdjustment.FILTER: 0.0,     # Filter out
            RegimeSignalAdjustment.MAINTAIN: 1.0    # No change
        }

    def set_regime_engine(self, regime_engine: Any) -> None:
        """Set regime engine reference"""
        self.regime_engine = regime_engine
        logger.info("✅ Regime engine injected into SignalEnhancer")

    async def enhance_signals(
        self,
        signals: List[Any],
        regime_context: Optional[Dict[str, Any]] = None
    ) -> List[RegimeAwareSignal]:
        """
        Enhance signals with regime awareness

        Args:
            signals: List of trading signals from signal generator
            regime_context: Optional regime context (if not provided, fetches from engine)

        Returns:
            List of RegimeAwareSignal objects with adjusted confidence
        """
        try:
            # Get regime context if not provided
            if regime_context is None and self.regime_engine:
                try:
                    regime_analysis = await self.regime_engine.get_current_regime()
                    regime_context = {
                        'regime': regime_analysis.primary_regime.value if hasattr(regime_analysis, 'primary_regime') else 'unknown',
                        'confidence': regime_analysis.confidence if hasattr(regime_analysis, 'confidence') else 0.5,
                        'volatility': regime_analysis.volatility_regime if hasattr(regime_analysis, 'volatility_regime') else 'normal_volatility'
                    }
                except Exception as e:
                    logger.warning(f"Could not get regime context: {e}")
                    regime_context = {'regime': 'unknown', 'confidence': 0.5, 'volatility': 'normal_volatility'}
            elif regime_context is None:
                regime_context = {'regime': 'unknown', 'confidence': 0.5, 'volatility': 'normal_volatility'}

            regime = regime_context.get('regime', 'unknown')
            regime_confidence = regime_context.get('confidence', 0.5)

            enhanced_signals = []

            for signal in signals:
                # Get signal strategy type
                strategy_type = self._get_signal_strategy_type(signal)

                # Determine adjustment
                adjustment = self._determine_adjustment(regime, strategy_type)

                # Calculate adjusted confidence
                original_confidence = getattr(signal, 'confidence', 0.6)
                multiplier = self.adjustment_multipliers[adjustment]
                adjusted_confidence = original_confidence * multiplier * regime_confidence

                # Cap at 0.95
                adjusted_confidence = min(adjusted_confidence, 0.95)

                # Check if regime compatible
                regime_compatible = adjustment != RegimeSignalAdjustment.FILTER

                # Create enhanced signal
                enhanced = RegimeAwareSignal(
                    original_signal=signal,
                    regime=regime,
                    regime_confidence=regime_confidence,
                    adjustment=adjustment,
                    adjusted_confidence=adjusted_confidence,
                    regime_compatible=regime_compatible,
                    adjustment_reason=f"{strategy_type} signal in {regime} regime → {adjustment.value}"
                )

                enhanced_signals.append(enhanced)

            # Filter out incompatible signals
            compatible_signals = [s for s in enhanced_signals if s.regime_compatible]

            logger.info(
                f"✅ Enhanced {len(signals)} signals with regime '{regime}' → "
                f"{len(compatible_signals)} regime-compatible signals"
            )

            return compatible_signals

        except Exception as e:
            logger.error(f"Signal enhancement failed: {e}")
            # Return original signals wrapped
            return [
                RegimeAwareSignal(
                    original_signal=s,
                    regime='unknown',
                    regime_confidence=0.5,
                    adjustment=RegimeSignalAdjustment.MAINTAIN,
                    adjusted_confidence=getattr(s, 'confidence', 0.6),
                    regime_compatible=True,
                    adjustment_reason='Enhancement failed - using original signal'
                )
                for s in signals
            ]

    def _get_signal_strategy_type(self, signal: Any) -> str:
        """Extract strategy type from signal"""
        # Try multiple ways to get strategy type
        if hasattr(signal, 'strategy_type'):
            return signal.strategy_type
        elif hasattr(signal, 'metadata') and isinstance(signal.metadata, dict):
            return signal.metadata.get('strategy_type', 'unknown')
        elif hasattr(signal, 'signal_type'):
            # Infer from signal type
            signal_type_str = str(signal.signal_type).lower()
            if 'momentum' in signal_type_str:
                return 'momentum'
            elif 'reversion' in signal_type_str:
                return 'mean_reversion'

        return 'unknown'

    def _determine_adjustment(
        self,
        regime: str,
        strategy_type: str
    ) -> RegimeSignalAdjustment:
        """
        Determine how to adjust signal based on regime and strategy

        Returns adjustment type
        """
        # Get regime compatibility matrix
        regime_rules = self.regime_compatibility.get(regime, {})

        # Check if there's an 'all' rule for this regime
        if 'all' in regime_rules:
            return regime_rules['all']

        # Check strategy-specific rule
        if strategy_type in regime_rules:
            return regime_rules[strategy_type]

        # Default: maintain signal
        return RegimeSignalAdjustment.MAINTAIN

    def get_enhancement_stats(self, enhanced_signals: List[RegimeAwareSignal]) -> Dict[str, Any]:
        """Get statistics on signal enhancements"""
        if not enhanced_signals:
            return {}

        amplified = sum(1 for s in enhanced_signals if s.adjustment == RegimeSignalAdjustment.AMPLIFY)
        reduced = sum(1 for s in enhanced_signals if s.adjustment == RegimeSignalAdjustment.REDUCE)
        filtered = sum(1 for s in enhanced_signals if not s.regime_compatible)
        maintained = sum(1 for s in enhanced_signals if s.adjustment == RegimeSignalAdjustment.MAINTAIN)

        avg_adjustment = sum(s.adjusted_confidence / s.original_signal.confidence
                            for s in enhanced_signals
                            if hasattr(s.original_signal, 'confidence') and s.original_signal.confidence > 0) / len(enhanced_signals)

        return {
            'total_signals': len(enhanced_signals),
            'amplified': amplified,
            'reduced': reduced,
            'filtered': filtered,
            'maintained': maintained,
            'avg_adjustment_factor': avg_adjustment,
            'regime': enhanced_signals[0].regime if enhanced_signals else 'unknown'
        }

