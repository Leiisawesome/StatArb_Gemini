"""
Signal Validator - Comprehensive Signal Quality Assessment
=========================================================

Advanced signal validation framework for assessing trading signal quality,
market timing, statistical properties, and regime alignment.

This validator provides:
- Signal structure validation
- Market timing analysis
- Statistical property assessment
- Regime-aware validation
- Signal strength evaluation
- Cross-market consistency checks

Key Features:
- Multi-dimensional signal quality scoring
- Market regime detection and alignment
- Statistical significance testing
- Timing accuracy validation
- Signal consistency analysis

Author: StatArb_Gemini Phase 7 Strategy Validation
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import scipy.stats as stats

# Import strategy components
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType

logger = logging.getLogger(__name__)


class SignalQualityDimension(Enum):
    """Dimensions of signal quality assessment"""

    STRUCTURE = "structure"           # Signal format and completeness
    TIMING = "timing"                # Market timing accuracy
    STRENGTH = "strength"            # Signal confidence and magnitude
    CONSISTENCY = "consistency"      # Signal reliability over time
    REGIME_ALIGNMENT = "regime"      # Market regime appropriateness
    STATISTICAL_SIGNIFICANCE = "stats"  # Statistical robustness


@dataclass
class SignalQualityMetrics:
    """Comprehensive signal quality assessment"""

    # Overall quality score
    overall_score: float = 0.0

    # Dimension scores (0.0 to 1.0)
    structure_score: float = 0.0
    timing_score: float = 0.0
    strength_score: float = 0.0
    consistency_score: float = 0.0
    regime_score: float = 0.0
    statistical_score: float = 0.0

    # Detailed metrics
    signal_count: int = 0
    valid_signals: int = 0
    invalid_signals: int = 0

    # Timing metrics
    avg_timing_error: float = 0.0
    timing_accuracy: float = 0.0

    # Strength metrics
    avg_confidence: float = 0.0
    avg_strength: float = 0.0
    confidence_distribution: Dict[str, float] = field(default_factory=dict)

    # Consistency metrics
    signal_persistence: float = 0.0
    directional_accuracy: float = 0.0

    # Statistical metrics
    signal_to_noise_ratio: float = 0.0
    p_value: float = 1.0
    z_score: float = 0.0

    # Validation results
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SignalValidator:
    """
    Comprehensive signal quality validation engine

    This validator assesses trading signals across multiple dimensions
    to ensure they meet institutional quality standards.
    """

    def __init__(self):
        self.quality_thresholds = {
            SignalQualityDimension.STRUCTURE: 0.95,      # 95% structural validity
            SignalQualityDimension.TIMING: 0.70,         # 70% timing accuracy
            SignalQualityDimension.STRENGTH: 0.60,       # 60% average strength
            SignalQualityDimension.CONSISTENCY: 0.65,    # 65% consistency
            SignalQualityDimension.REGIME_ALIGNMENT: 0.75, # 75% regime alignment
            SignalQualityDimension.STATISTICAL_SIGNIFICANCE: 0.80  # 80% statistical significance
        }

        logger.info("SignalValidator initialized")

    async def validate_signal_quality(
        self,
        signals: List[StrategySignal],
        market_data: Dict[str, pd.DataFrame],
        strategy_config: Any = None
    ) -> Dict[str, Any]:
        """
        Comprehensive signal quality validation

        Args:
            signals: List of strategy signals to validate
            market_data: Market data for context and validation
            strategy_config: Optional strategy configuration

        Returns:
            Dict containing detailed validation results
        """

        if not signals:
            return self._create_empty_validation_result()

        logger.info(f"Validating {len(signals)} signals")

        try:
            # Initialize quality metrics
            quality_metrics = SignalQualityMetrics(signal_count=len(signals))

            # Validate signal structure
            structure_results = self._validate_signal_structure(signals)
            quality_metrics.structure_score = structure_results["score"]
            quality_metrics.valid_signals = structure_results["valid_count"]
            quality_metrics.invalid_signals = structure_results["invalid_count"]
            quality_metrics.validation_errors.extend(structure_results["errors"])

            # Validate signal timing
            if market_data:
                timing_results = self._validate_signal_timing(signals, market_data)
                quality_metrics.timing_score = timing_results["score"]
                quality_metrics.avg_timing_error = timing_results["avg_error"]
                quality_metrics.timing_accuracy = timing_results["accuracy"]

            # Validate signal strength
            strength_results = self._validate_signal_strength(signals)
            quality_metrics.strength_score = strength_results["score"]
            quality_metrics.avg_confidence = strength_results["avg_confidence"]
            quality_metrics.avg_strength = strength_results["avg_strength"]
            quality_metrics.confidence_distribution = strength_results["distribution"]

            # Validate signal consistency
            consistency_results = self._validate_signal_consistency(signals, market_data)
            quality_metrics.consistency_score = consistency_results["score"]
            quality_metrics.signal_persistence = consistency_results["persistence"]
            quality_metrics.directional_accuracy = consistency_results["directional_accuracy"]

            # Validate regime alignment
            if market_data:
                regime_results = self._validate_regime_alignment(signals, market_data)
                quality_metrics.regime_score = regime_results["score"]

            # Validate statistical significance
            statistical_results = self._validate_statistical_significance(signals, market_data)
            quality_metrics.statistical_score = statistical_results["score"]
            quality_metrics.signal_to_noise_ratio = statistical_results["snr"]
            quality_metrics.p_value = statistical_results["p_value"]
            quality_metrics.z_score = statistical_results["z_score"]

            # Calculate overall quality score
            quality_metrics.overall_score = self._calculate_overall_score(quality_metrics)

            # Generate validation summary
            validation_summary = self._generate_validation_summary(quality_metrics)

            logger.info(f"Signal validation completed: overall score = {quality_metrics.overall_score:.3f}")

            return {
                "total_signals": len(signals),
                "valid_signals": quality_metrics.valid_signals,
                "invalid_signals": quality_metrics.invalid_signals,
                "quality_score": quality_metrics.overall_score,
                "timing_accuracy": quality_metrics.timing_score,
                "market_alignment": quality_metrics.regime_score,
                "signal_details": [],  # Would contain per-signal details
                "quality_metrics": quality_metrics,
                "validation_summary": validation_summary,
                "recommendations": self._generate_recommendations(quality_metrics)
            }

        except Exception as e:
            logger.error(f"Signal validation failed: {e}")
            return {
                "total_signals": len(signals),
                "valid_signals": 0,
                "invalid_signals": len(signals),
                "quality_score": 0.0,
                "timing_accuracy": 0.0,
                "market_alignment": 0.0,
                "error": str(e)
            }

    def _validate_signal_structure(self, signals: List[StrategySignal]) -> Dict[str, Any]:
        """Validate signal structure and completeness"""

        valid_count = 0
        invalid_count = 0
        errors = []

        for signal in signals:
            try:
                # Check required fields
                if not self._validate_required_fields(signal):
                    invalid_count += 1
                    errors.append(f"Signal {signal.signal_id}: Missing required fields")
                    continue

                # Validate field values
                if not self._validate_field_values(signal):
                    invalid_count += 1
                    errors.append(f"Signal {signal.signal_id}: Invalid field values")
                    continue

                # Validate signal logic
                if not self._validate_signal_logic(signal):
                    invalid_count += 1
                    errors.append(f"Signal {signal.signal_id}: Invalid signal logic")
                    continue

                valid_count += 1

            except Exception as e:
                invalid_count += 1
                errors.append(f"Signal {signal.signal_id}: Validation error - {e}")

        score = valid_count / len(signals) if signals else 0.0

        return {
            "score": score,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "errors": errors[:10]  # Limit error messages
        }

    def _validate_required_fields(self, signal: StrategySignal) -> bool:
        """Validate that signal has all required fields"""

        required_fields = [
            "strategy_id", "symbol", "signal_type", "confidence",
            "strength", "timestamp"
        ]

        for field in required_fields:
            if not hasattr(signal, field):
                return False
            value = getattr(signal, field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False

        return True

    def _validate_field_values(self, signal: StrategySignal) -> bool:
        """Validate field values are within acceptable ranges"""

        # Validate signal type
        if signal.signal_type not in [SignalType.BUY, SignalType.SELL]:
            return False

        # Validate confidence range
        if not (0.0 <= signal.confidence <= 1.0):
            return False

        # Validate strength range
        if not (0.0 <= signal.strength <= 1.0):
            return False

        # Validate timestamp
        if not isinstance(signal.timestamp, datetime):
            return False

        # Validate symbol format
        if not isinstance(signal.symbol, str) or not signal.symbol.strip():
            return False

        return True

    def _validate_signal_logic(self, signal: StrategySignal) -> bool:
        """Validate signal logic and consistency"""

        # For BUY signals, we expect positive indicators
        # For SELL signals, we expect negative indicators
        # This is a basic check - more sophisticated logic would be strategy-specific

        # Check if confidence and strength are reasonably correlated
        confidence_strength_diff = abs(signal.confidence - signal.strength)
        if confidence_strength_diff > 0.8:  # Too much discrepancy
            return False

        return True

    def _validate_signal_timing(self, signals: List[StrategySignal], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate signal timing relative to market conditions"""

        if not signals or not market_data:
            return {"score": 0.5, "avg_error": 0.0, "accuracy": 0.5}

        timing_errors = []
        accurate_signals = 0

        for signal in signals:
            try:
                symbol = signal.symbol
                if symbol not in market_data:
                    continue

                df = market_data[symbol]
                signal_time = signal.timestamp

                # Find market data around signal time
                mask = (df.index >= signal_time - timedelta(minutes=5)) & \
                       (df.index <= signal_time + timedelta(minutes=5))

                nearby_data = df[mask]

                if len(nearby_data) < 3:
                    continue

                # Calculate price movement after signal
                signal_price = nearby_data.iloc[0]['close']
                future_prices = nearby_data.iloc[1:]['close']

                if len(future_prices) > 0:
                    avg_future_price = future_prices.mean()
                    price_movement = (avg_future_price - signal_price) / signal_price

                    # Expected direction
                    expected_positive = signal.signal_type == SignalType.BUY

                    # Check if movement aligns with signal direction
                    if expected_positive and price_movement > 0.001:  # 0.1% movement
                        accurate_signals += 1
                    elif not expected_positive and price_movement < -0.001:
                        accurate_signals += 1

                    timing_errors.append(abs(price_movement))

            except Exception as e:
                logger.warning(f"Timing validation error for signal {signal.signal_id}: {e}")

        avg_error = np.mean(timing_errors) if timing_errors else 0.0
        accuracy = accurate_signals / len(signals) if signals else 0.0

        # Normalize score (0.5 = random, 1.0 = perfect timing)
        score = 0.5 + (accuracy - 0.5) * 2.0
        score = max(0.0, min(1.0, score))

        return {
            "score": score,
            "avg_error": avg_error,
            "accuracy": accuracy
        }

    def _validate_signal_strength(self, signals: List[StrategySignal]) -> Dict[str, Any]:
        """Validate signal strength and confidence"""

        if not signals:
            return {"score": 0.0, "avg_confidence": 0.0, "avg_strength": 0.0, "distribution": {}}

        confidences = [s.confidence for s in signals]
        strengths = [s.strength for s in signals]

        avg_confidence = np.mean(confidences)
        avg_strength = np.mean(strengths)

        # Calculate strength score based on distribution
        # We want signals to be well-distributed, not all weak or all strong
        confidence_std = np.std(confidences)
        strength_std = np.std(strengths)

        # Ideal distribution has moderate standard deviation
        distribution_score = min(confidence_std * 4, 1.0)  # Scale to 0-1

        # Overall strength score
        strength_score = (avg_confidence + avg_strength + distribution_score) / 3.0

        # Confidence distribution analysis
        conf_bins = pd.cut(confidences, bins=[0, 0.3, 0.6, 0.8, 1.0], labels=['weak', 'moderate', 'strong', 'very_strong'])
        distribution = conf_bins.value_counts().to_dict()

        return {
            "score": strength_score,
            "avg_confidence": avg_confidence,
            "avg_strength": avg_strength,
            "distribution": {k: int(v) for k, v in distribution.items()}
        }

    def _validate_signal_consistency(self, signals: List[StrategySignal], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate signal consistency over time"""

        if len(signals) < 2:
            return {"score": 0.5, "persistence": 0.5, "directional_accuracy": 0.5}

        try:
            # Sort signals by time
            sorted_signals = sorted(signals, key=lambda s: s.timestamp)

            # Calculate signal persistence (how often consecutive signals agree)
            consecutive_agreements = 0
            total_consecutive = 0

            for i in range(1, len(sorted_signals)):
                prev_signal = sorted_signals[i-1]
                curr_signal = sorted_signals[i]

                # Only compare if same symbol and within reasonable time
                time_diff = (curr_signal.timestamp - prev_signal.timestamp).total_seconds() / 3600  # hours

                if curr_signal.symbol == prev_signal.symbol and time_diff < 24:  # Same symbol, within 24 hours
                    total_consecutive += 1
                    if curr_signal.signal_type == prev_signal.signal_type:
                        consecutive_agreements += 1

            persistence = consecutive_agreements / total_consecutive if total_consecutive > 0 else 0.5

            # Calculate directional accuracy using market data
            directional_accuracy = self._calculate_directional_accuracy(sorted_signals, market_data)

            # Overall consistency score
            consistency_score = (persistence + directional_accuracy) / 2.0

            return {
                "score": consistency_score,
                "persistence": persistence,
                "directional_accuracy": directional_accuracy
            }

        except Exception as e:
            logger.warning(f"Consistency validation error: {e}")
            return {"score": 0.5, "persistence": 0.5, "directional_accuracy": 0.5}

    def _calculate_directional_accuracy(self, signals: List[StrategySignal], market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate how well signals predict market direction"""

        if not market_data:
            return 0.5

        accurate_predictions = 0
        total_predictions = 0

        for signal in signals:
            try:
                symbol = signal.symbol
                if symbol not in market_data:
                    continue

                df = market_data[symbol]
                signal_time = signal.timestamp

                # Get price data after signal
                future_data = df[df.index > signal_time]

                if len(future_data) < 5:  # Need at least 5 data points
                    continue

                # Calculate price movement over next period
                entry_price = future_data.iloc[0]['close']
                exit_price = future_data.iloc[min(10, len(future_data)-1)]['close']  # Next 10 periods
                price_movement = (exit_price - entry_price) / entry_price

                # Check if movement matches signal direction
                expected_positive = signal.signal_type == SignalType.BUY

                if (expected_positive and price_movement > 0.001) or \
                   (not expected_positive and price_movement < -0.001):
                    accurate_predictions += 1

                total_predictions += 1

            except Exception as e:
                logger.debug(f"Directional accuracy calculation error: {e}")

        accuracy = accurate_predictions / total_predictions if total_predictions > 0 else 0.5
        return accuracy

    def _validate_regime_alignment(self, signals: List[StrategySignal], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate signal alignment with market regime"""

        if not market_data:
            return {"score": 0.5}

        try:
            # Simple regime detection
            regime_alignment_scores = []

            for signal in signals:
                symbol = signal.symbol
                if symbol not in market_data:
                    continue

                df = market_data[symbol]
                signal_time = signal.timestamp

                # Get recent market data (last 20 periods)
                recent_data = df[df.index <= signal_time].tail(20)

                if len(recent_data) < 10:
                    continue

                # Calculate regime indicators
                returns = recent_data['close'].pct_change().dropna()
                volatility = returns.std()
                trend_strength = abs(returns.mean()) / volatility if volatility > 0 else 0

                # Determine regime
                # High trend strength = trending regime
                # Low trend strength = ranging regime
                is_trending_regime = trend_strength > 0.5

                # Different signal types work better in different regimes
                # This is simplified - would be strategy-specific
                if is_trending_regime:
                    alignment_score = 0.8  # Good alignment with trending regime
                else:
                    alignment_score = 0.6  # Moderate alignment with ranging regime

                regime_alignment_scores.append(alignment_score)

            avg_alignment = np.mean(regime_alignment_scores) if regime_alignment_scores else 0.5

            return {"score": avg_alignment}

        except Exception as e:
            logger.warning(f"Regime alignment validation error: {e}")
            return {"score": 0.5}

    def _validate_statistical_significance(self, signals: List[StrategySignal], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate statistical significance of signals"""

        if len(signals) < 10:
            return {"score": 0.5, "snr": 0.0, "p_value": 1.0, "z_score": 0.0}

        try:
            # Calculate signal-to-noise ratio
            confidences = [s.confidence for s in signals]
            confidence_mean = np.mean(confidences)
            confidence_std = np.std(confidences)

            # Signal-to-noise ratio
            snr = confidence_mean / confidence_std if confidence_std > 0 else 0.0

            # Statistical significance test (t-test against random signals)
            # Null hypothesis: signals are random (confidence = 0.5)
            t_stat, p_value = stats.ttest_1samp(confidences, 0.5)

            # Z-score
            z_score = (confidence_mean - 0.5) / (confidence_std / np.sqrt(len(signals))) if confidence_std > 0 else 0.0

            # Calculate statistical score
            # Combine SNR, p-value significance, and effect size
            snr_score = min(snr / 2.0, 1.0)  # SNR of 2.0 = perfect score
            p_value_score = 1.0 - p_value  # Lower p-value = higher score
            effect_size_score = min(abs(z_score) / 3.0, 1.0)  # Z-score of 3.0 = perfect score

            statistical_score = (snr_score + p_value_score + effect_size_score) / 3.0

            return {
                "score": statistical_score,
                "snr": snr,
                "p_value": p_value,
                "z_score": z_score
            }

        except Exception as e:
            logger.warning(f"Statistical significance validation error: {e}")
            return {"score": 0.5, "snr": 0.0, "p_value": 1.0, "z_score": 0.0}

    def _calculate_overall_score(self, metrics: SignalQualityMetrics) -> float:
        """Calculate overall signal quality score"""

        dimension_scores = [
            metrics.structure_score,
            metrics.timing_score,
            metrics.strength_score,
            metrics.consistency_score,
            metrics.regime_score,
            metrics.statistical_score
        ]

        # Weighted average (structure and statistical significance are most important)
        weights = [0.25, 0.15, 0.15, 0.15, 0.15, 0.15]  # Sum to 1.0

        overall_score = sum(score * weight for score, weight in zip(dimension_scores, weights))

        return overall_score

    def _generate_validation_summary(self, metrics: SignalQualityMetrics) -> Dict[str, Any]:
        """Generate human-readable validation summary"""

        summary = {
            "overall_assessment": self._get_overall_assessment(metrics.overall_score),
            "strengths": [],
            "weaknesses": [],
            "critical_issues": []
        }

        # Assess each dimension
        dimension_assessments = {
            "Structure": (metrics.structure_score, "signal format and completeness"),
            "Timing": (metrics.timing_score, "market timing accuracy"),
            "Strength": (metrics.strength_score, "signal confidence and magnitude"),
            "Consistency": (metrics.consistency_score, "signal reliability over time"),
            "Regime Alignment": (metrics.regime_score, "market regime appropriateness"),
            "Statistical Significance": (metrics.statistical_score, "statistical robustness")
        }

        for dimension, (score, description) in dimension_assessments.items():
            threshold = self.quality_thresholds[SignalQualityDimension(dimension.lower().replace(" ", "_"))]

            if score >= threshold:
                summary["strengths"].append(f"Strong {description} ({score:.2f})")
            elif score >= threshold * 0.8:
                summary["weaknesses"].append(f"Moderate {description} ({score:.2f})")
            else:
                summary["critical_issues"].append(f"Poor {description} ({score:.2f})")

        return summary

    def _get_overall_assessment(self, score: float) -> str:
        """Get overall quality assessment"""

        if score >= 0.85:
            return "Excellent - Signals meet institutional standards"
        elif score >= 0.70:
            return "Good - Signals are acceptable with minor improvements"
        elif score >= 0.55:
            return "Fair - Signals need significant improvement"
        elif score >= 0.40:
            return "Poor - Signals require major revision"
        else:
            return "Critical - Signals are unacceptable"

    def _generate_recommendations(self, metrics: SignalQualityMetrics) -> List[str]:
        """Generate improvement recommendations"""

        recommendations = []

        if metrics.structure_score < 0.9:
            recommendations.append("Fix signal structure issues and ensure all required fields are present")

        if metrics.timing_score < 0.7:
            recommendations.append("Improve signal timing by analyzing market conditions more thoroughly")

        if metrics.strength_score < 0.6:
            recommendations.append("Enhance signal strength through better confidence scoring and filters")

        if metrics.consistency_score < 0.65:
            recommendations.append("Increase signal consistency by reducing false signals and improving persistence")

        if metrics.regime_score < 0.75:
            recommendations.append("Improve regime alignment by adapting signals to different market conditions")

        if metrics.statistical_score < 0.8:
            recommendations.append("Enhance statistical significance through better signal generation algorithms")

        if not recommendations:
            recommendations.append("Signals are of high quality - consider fine-tuning for optimal performance")

        return recommendations

    def _create_empty_validation_result(self) -> Dict[str, Any]:
        """Create empty validation result for no signals"""

        return {
            "total_signals": 0,
            "valid_signals": 0,
            "invalid_signals": 0,
            "quality_score": 0.0,
            "timing_accuracy": 0.0,
            "market_alignment": 0.0,
            "signal_details": [],
            "validation_summary": {
                "overall_assessment": "No signals to validate",
                "strengths": [],
                "weaknesses": [],
                "critical_issues": []
            },
            "recommendations": ["Generate signals before validation"]
        }